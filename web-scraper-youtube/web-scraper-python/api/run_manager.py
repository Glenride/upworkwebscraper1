"""Run orchestration logic for the scraper UI."""

from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

from config import Settings
from scrape import configure_logging
from scraper.pipeline import PipelineResult, PipelineSettings, run_pipeline

from .storage import RunStatus, RunStore


class RunManager:
    """Coordinates scraper runs and background execution."""

    def __init__(
        self,
        *,
        settings: Settings,
        store: RunStore,
        executor: Optional[ThreadPoolExecutor] = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.executor = executor or ThreadPoolExecutor(max_workers=1)

    async def enqueue_run(self, *, input_path: Path, source: str) -> str:
        """Persist and dispatch a run using the provided input file."""

        resolved_path = input_path.resolve()
        if not resolved_path.exists():
            raise FileNotFoundError(f"Input file not found: {resolved_path}")

        run_id = uuid.uuid4().hex
        self.store.create_run(
            run_id=run_id,
            input_path=resolved_path,
            input_filename=resolved_path.name,
            source=source,
            status=RunStatus.QUEUED,
        )

        asyncio.create_task(self._run_background(run_id, resolved_path))
        return run_id

    async def _run_background(self, run_id: str, input_path: Path) -> None:
        self.store.mark_running(run_id)
        pipeline_settings = self._build_pipeline_settings(input_path)

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                self.executor,
                self._execute_pipeline,
                run_id,
                pipeline_settings,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logging.exception("Run failed", extra={"run_id": run_id})
            self.store.mark_failed(run_id, str(exc))
            return

        # mark archive as pending while zipping large directories
        pending_archive = pipeline_settings.output_dir / "deliverables.zip"
        self.store.set_archive_path(run_id, pending_archive)
        try:
            archive_path = await loop.run_in_executor(
                self.executor,
                self._prepare_archive,
                pipeline_settings.output_dir,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logging.exception("Failed to prepare deliverables archive", extra={"run_id": run_id})
            self.store.mark_failed(run_id, f"Archive failed: {exc}")
            return
        self.store.set_archive_path(run_id, archive_path)
        log_path = self.settings.logs_root / f"scraper-{run_id}.log"
        self.store.mark_succeeded(
            run_id,
            output_dir=pipeline_settings.output_dir,
            csv_path=result.csv_path,
            summary_path=result.summary_path,
            images_zip_path=result.images_zip,
            screenshots_zip_path=result.screenshots_zip,
            archive_path=archive_path,
            log_path=log_path,
        )

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)

    def _execute_pipeline(self, run_id: str, settings: PipelineSettings) -> PipelineResult:
        configure_logging(self.settings, run_id)
        return run_pipeline(settings)

    def _build_pipeline_settings(self, input_path: Path) -> PipelineSettings:
        run_output_dir = self.settings.output_root / uuid.uuid4().hex
        run_output_dir.mkdir(parents=True, exist_ok=True)
        return PipelineSettings(
            input_path=input_path,
            output_dir=run_output_dir,
            templates_dir=self.settings.templates_root,
            proxy_url=self.settings.proxy_url,
            captcha_key=self.settings.captcha_api_key,
            detail_template_name=self.settings.detail_template_name,
            zip_outputs=self.settings.zip_outputs,
            zip_images_name=self.settings.zip_images_name,
            zip_screenshots_name=self.settings.zip_screenshots_name,
        )

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

        copy_file("shopify_import.csv")
        copy_file("run_summary.json")

        if not (output_dir / "images.zip").exists():
            copy_dir("images")
        else:
            copy_file("images.zip")

        if not (output_dir / "screenshots.zip").exists():
            copy_dir("screenshots")
        else:
            copy_file("screenshots.zip")

        archive_base = output_dir.parent / f"{output_dir.name}-deliverables"
        temp_archive = Path(shutil.make_archive(str(archive_base), "zip", root_dir=bundle_root))
        shutil.rmtree(bundle_root, ignore_errors=True)

        final_archive = output_dir / "deliverables.zip"
        if final_archive.exists():
            final_archive.unlink()
        shutil.move(str(temp_archive), final_archive)
        return final_archive


def configure_manager(settings: Settings, store_factory: Callable[[Path], RunStore]) -> RunManager:
    store = store_factory(settings.ui_database_path)
    store.initialize()
    return RunManager(settings=settings, store=store)
