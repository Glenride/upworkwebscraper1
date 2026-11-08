"""Run orchestration for visual QA screenshot/text jobs."""

from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable, Optional, Tuple

from config import Settings

from .storage import RunStatus
from .visual_store import VisualRunStore
from scraper.visual.capture import capture_pages, write_summary


class VisualRunManager:
    """Coordinates visual QA runs. Screenshot/text extraction to be implemented."""

    def __init__(
        self,
        *,
        settings: Settings,
        store: VisualRunStore,
        executor: Optional[ThreadPoolExecutor] = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.executor = executor or ThreadPoolExecutor(max_workers=1)

    async def enqueue_run(
        self,
        *,
        urls: Iterable[str],
        source: str,
        input_label: str,
        input_path: Optional[Path] = None,
        max_urls: Optional[int] = None,
    ) -> str:
        url_list = [url.strip() for url in urls if url.strip()]
        if not url_list:
            raise ValueError("At least one URL is required for a visual QA run")

        effective_limit = max_urls or self.settings.visual_default_max_urls
        effective_limit = max(1, effective_limit)
        bounded_urls = url_list[:effective_limit]
        if len(url_list) > effective_limit:
            logging.warning(
                "Visual QA input truncated",
                extra={"max_urls": effective_limit, "provided": len(url_list)},
            )

        run_id = uuid.uuid4().hex
        self.store.create_run(
            run_id=run_id,
            source=source,
            input_label=input_label,
            url_count=len(bounded_urls),
            input_path=input_path,
        )

        asyncio.create_task(self._run_background(run_id, bounded_urls))
        return run_id

    async def _run_background(self, run_id: str, urls: list[str]) -> None:
        self.store.mark_running(run_id)
        loop = asyncio.get_running_loop()
        try:
            output_dir, summary_path, archive_path = await loop.run_in_executor(
                self.executor,
                self._execute_run,
                run_id,
                urls,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logging.exception("Visual QA placeholder failed", extra={"run_id": run_id})
            self.store.mark_failed(run_id, f"Visual runner failed: {exc}")
            return

        self.store.mark_succeeded(
            run_id,
            output_dir=output_dir,
            summary_path=summary_path,
            archive_path=archive_path,
        )

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)

    def _execute_run(self, run_id: str, urls: list[str]) -> Tuple[Path, Path, Path]:
        output_root = self.settings.visual_output_root
        output_root.mkdir(parents=True, exist_ok=True)
        output_dir = output_root / run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        logging.info("Starting visual QA capture", extra={"run_id": run_id, "url_count": len(urls)})
        results = capture_pages(urls, output_dir, proxy_url=self.settings.proxy_url)
        summary_path = write_summary(output_dir, results)

        success_count = sum(1 for item in results if item.status == "succeeded")
        failure_count = len(results) - success_count
        logging.info(
            "Visual QA capture finished",
            extra={
                "run_id": run_id,
                "success_count": success_count,
                "failure_count": failure_count,
            },
        )

        archive_path = self._prepare_archive(output_dir)
        return output_dir, summary_path, archive_path

    def _prepare_archive(self, output_dir: Path) -> Path:
        bundle_root = output_dir.parent / f"{output_dir.name}-bundle"
        if bundle_root.exists():
            shutil.rmtree(bundle_root)
        bundle_root.mkdir(parents=True, exist_ok=True)

        def copy_file(name: str) -> None:
            source = output_dir / name
            if source.exists():
                shutil.copy2(source, bundle_root / name)

        def copy_dir(name: str) -> None:
            source = output_dir / name
            if source.exists() and any(source.iterdir()):
                shutil.copytree(source, bundle_root / name)

        copy_file("summary.json")
        copy_dir("text")
        copy_dir("screenshots")

        archive_base = output_dir.parent / f"{output_dir.name}-deliverables"
        temp_archive = Path(shutil.make_archive(str(archive_base), "zip", root_dir=bundle_root))
        shutil.rmtree(bundle_root, ignore_errors=True)

        final_archive = output_dir / "deliverables.zip"
        if final_archive.exists():
            final_archive.unlink()
        shutil.move(str(temp_archive), final_archive)
        return final_archive


def configure_visual_manager(settings: Settings, store: VisualRunStore) -> VisualRunManager:
    store.initialize()
    return VisualRunManager(settings=settings, store=store)
