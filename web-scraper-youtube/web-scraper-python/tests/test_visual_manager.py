from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

from api.visual_manager import VisualRunManager
from api.visual_store import VisualRunStore
from config import Settings


class DummyVisualStore(VisualRunStore):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(tmp_path / "visual.db")
        self.create_run = MagicMock()
        self.mark_running = MagicMock()
        self.mark_succeeded = MagicMock()
        self.mark_failed = MagicMock()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    config = Settings(input_urls_path=tmp_path / "urls.csv")
    config.output_root = tmp_path / "output"
    config.visual_output_root = tmp_path / "visual-output"
    config.visual_default_max_urls = 5
    config.visual_output_root.mkdir(parents=True, exist_ok=True)
    return config


@pytest_asyncio.fixture
async def manager(settings: Settings, tmp_path: Path):
    store = DummyVisualStore(tmp_path)
    instance = VisualRunManager(settings=settings, store=store)
    yield instance
    instance.shutdown()


@pytest.mark.asyncio
async def test_enqueue_run_validates_urls(manager: VisualRunManager) -> None:
    with pytest.raises(ValueError):
        await manager.enqueue_run(urls=["", "   "], source="textarea", input_label="manual")


@pytest.mark.asyncio
async def test_enqueue_run_truncates(settings: Settings, tmp_path: Path) -> None:
    store = DummyVisualStore(tmp_path)
    manager = VisualRunManager(settings=settings, store=store)

    try:
        run_id = await manager.enqueue_run(
            urls=[f"https://example.com/{i}" for i in range(10)],
            source="textarea",
            input_label="manual",
            max_urls=3,
        )
    finally:
        manager.shutdown()

    assert store.create_run.called
    args, kwargs = store.create_run.call_args
    assert kwargs["url_count"] == 3
    assert run_id


@pytest.mark.asyncio
async def test_execute_run_success(settings: Settings, tmp_path: Path, monkeypatch) -> None:
    store = DummyVisualStore(tmp_path)
    manager = VisualRunManager(settings=settings, store=store)

    tasks = []
    original_create_task = asyncio.create_task

    def track_task(coro):
        task = original_create_task(coro)
        tasks.append(task)
        return task

    monkeypatch.setattr("api.visual_manager.asyncio.create_task", track_task)

    def fake_capture_pages(urls, output_dir, proxy_url=None):
        screenshot = output_dir / "page.png"
        text_file = output_dir / "page.txt"
        screenshot.write_bytes(b"fake")
        text_file.write_text("hello", encoding="utf-8")
        return [
            SimpleNamespace(
                url="https://example.com",
                status="succeeded",
                screenshot_path=screenshot,
                text_path=text_file,
                text_excerpt="hello",
                error=None,
            )
        ]

    def fake_write_summary(output_dir: Path, results):
        summary_path = output_dir / "summary.json"
        summary_path.write_text("{}", encoding="utf-8")
        return summary_path

    def fake_prepare_archive(self, output_dir: Path) -> Path:
        archive = output_dir / "deliverables.zip"
        archive.write_bytes(b"zip")
        return archive

    monkeypatch.setattr("api.visual_manager.capture_pages", fake_capture_pages)
    monkeypatch.setattr("api.visual_manager.write_summary", fake_write_summary)
    monkeypatch.setattr(VisualRunManager, "_prepare_archive", fake_prepare_archive, raising=True)

    try:
        run_id = await manager.enqueue_run(
            urls=["https://example.com"],
            source="textarea",
            input_label="manual",
        )
        if tasks:
            await asyncio.gather(*tasks)
    finally:
        manager.shutdown()

    store.mark_running.assert_called_once_with(run_id)
    store.mark_failed.assert_not_called()
    store.mark_succeeded.assert_called_once()

    _, kwargs = store.mark_succeeded.call_args
    output_dir = kwargs["output_dir"]
    summary_path = kwargs["summary_path"]
    archive_path = kwargs["archive_path"]
    assert output_dir.exists()
    assert summary_path.exists()
    assert archive_path.exists()


@pytest.mark.asyncio
async def test_execute_run_handles_failure(settings: Settings, tmp_path: Path, monkeypatch) -> None:
    store = DummyVisualStore(tmp_path)
    manager = VisualRunManager(settings=settings, store=store)

    tasks = []
    original_create_task = asyncio.create_task

    def track_task(coro):
        task = original_create_task(coro)
        tasks.append(task)
        return task

    monkeypatch.setattr("api.visual_manager.asyncio.create_task", track_task)

    def explode(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("api.visual_manager.capture_pages", explode)

    try:
        run_id = await manager.enqueue_run(
            urls=["https://example.com"],
            source="textarea",
            input_label="manual",
        )
        if tasks:
            await asyncio.gather(*tasks)
    finally:
        manager.shutdown()

    store.mark_running.assert_called_once_with(run_id)
    store.mark_succeeded.assert_not_called()
    store.mark_failed.assert_called_once()

    called_run_id, error_message = store.mark_failed.call_args[0]
    assert called_run_id == run_id
    assert "boom" in error_message
