from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

from api.run_manager import RunManager
from api.storage import RunStatus
from config import Settings
from scraper.pipeline import PipelineResult, PipelineSettings


class DummyResult:
    def __init__(self, csv_path: Path) -> None:
        self.csv_path = csv_path
        self.summary_path = csv_path.with_name("run_summary.json")
        self.images_zip = csv_path.with_name("images.zip")
        self.screenshots_zip = None


@pytest_asyncio.fixture
async def run_manager(tmp_path: Path) -> RunManager:
    settings = Settings(input_urls_path=tmp_path / "urls.csv")
    settings.output_root = tmp_path / "output"
    settings.logs_root = tmp_path / "logs"
    settings.templates_root = tmp_path / "templates"
    settings.output_root.mkdir()
    settings.logs_root.mkdir()
    settings.templates_root.mkdir()

    def store_factory(path: Path):
        store = MagicMock()
        store.initialize = MagicMock()
        store.create_run = MagicMock()
        store.mark_running = MagicMock()
        store.mark_succeeded = MagicMock()
        store.mark_failed = MagicMock()
        store.set_archive_path = MagicMock()
        store.list_runs = MagicMock(return_value=[])
        store.get_run = MagicMock(return_value=None)
        return store

    manager = RunManager(settings=settings, store=store_factory(settings.ui_database_path))

    async def fake_run_background(*args, **kwargs):
        return None

    manager._run_background = fake_run_background  # type: ignore
    yield manager
    manager.shutdown()


@pytest.mark.asyncio
async def test_enqueue_run_missing_file(tmp_path: Path, run_manager: RunManager) -> None:
    missing_path = tmp_path / "missing.csv"
    with pytest.raises(FileNotFoundError):
        await run_manager.enqueue_run(input_path=missing_path, source="upload")


@pytest.mark.asyncio
async def test_enqueue_run_calls_store(tmp_path: Path, run_manager: RunManager) -> None:
    input_file = tmp_path / "urls.csv"
    input_file.write_text("url\nhttps://example.com")
    await run_manager.enqueue_run(input_path=input_file, source="upload")
    run_manager.store.create_run.assert_called_once()


@pytest.mark.asyncio
async def test_run_background_sets_archive_path(tmp_path: Path) -> None:
    settings = Settings(input_urls_path=tmp_path / "urls.csv")
    settings.output_root = tmp_path / "output"
    settings.logs_root = tmp_path / "logs"
    settings.templates_root = tmp_path / "templates"
    settings.output_root.mkdir()
    settings.logs_root.mkdir()
    settings.templates_root.mkdir()

    store = MagicMock()
    store.set_archive_path = MagicMock()
    store.mark_running = MagicMock()
    store.mark_failed = MagicMock()
    store.mark_succeeded = MagicMock()

    manager = RunManager(settings=settings, store=store)

    output_dir = settings.output_root / "run"
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "shopify_import.csv"
    result = DummyResult(csv_path)

    def exec_pipeline(run_id, pipeline_settings):
        pipeline_settings.output_dir.mkdir(exist_ok=True)
        csv_path.write_text("Handle,Title\n")
        return result

    manager._execute_pipeline = exec_pipeline  # type: ignore
    manager._build_pipeline_settings = MagicMock(  # type: ignore
        return_value=PipelineSettings(
            input_path=tmp_path / "input.csv",
            output_dir=output_dir,
            templates_dir=settings.templates_root,
            proxy_url=None,
            captcha_key=None,
            detail_template_name=settings.detail_template_name,
            zip_outputs=settings.zip_outputs,
            zip_images_name=settings.zip_images_name,
            zip_screenshots_name=settings.zip_screenshots_name,
        )
    )

    input_path = tmp_path / "input.csv"
    input_path.write_text("url\nhttps://example.com")

    await manager._run_background("abc", input_path)

    assert store.set_archive_path.call_count == 2
    pending_call, final_call = store.set_archive_path.call_args_list
    assert pending_call.args[0] == "abc"
    assert pending_call.args[1].name == "deliverables.zip"
    assert pending_call.args[1].parent == output_dir
    assert final_call.args[1].name == "deliverables.zip"
    assert final_call.args[1].parent == output_dir
    store.mark_succeeded.assert_called_once()


@pytest.mark.asyncio
async def test_run_background_handles_archive_failure(tmp_path: Path) -> None:
    settings = Settings(input_urls_path=tmp_path / "urls.csv")
    settings.output_root = tmp_path / "output"
    settings.logs_root = tmp_path / "logs"
    settings.templates_root = tmp_path / "templates"
    settings.output_root.mkdir()
    settings.logs_root.mkdir()
    settings.templates_root.mkdir()

    store = MagicMock()
    store.set_archive_path = MagicMock()
    store.mark_running = MagicMock()
    store.mark_failed = MagicMock()
    store.mark_succeeded = MagicMock()

    manager = RunManager(settings=settings, store=store)

    output_dir = settings.output_root / "run"
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "shopify_import.csv"
    result = DummyResult(csv_path)

    def exec_pipeline(run_id, pipeline_settings):
        pipeline_settings.output_dir.mkdir(exist_ok=True)
        csv_path.write_text("Handle,Title\n")
        return result

    manager._execute_pipeline = exec_pipeline  # type: ignore
    manager._build_pipeline_settings = MagicMock(  # type: ignore
        return_value=PipelineSettings(
            input_path=tmp_path / "input.csv",
            output_dir=output_dir,
            templates_dir=settings.templates_root,
            proxy_url=None,
            captcha_key=None,
            detail_template_name=settings.detail_template_name,
            zip_outputs=settings.zip_outputs,
            zip_images_name=settings.zip_images_name,
            zip_screenshots_name=settings.zip_screenshots_name,
        )
    )

    manager._prepare_archive = MagicMock(side_effect=RuntimeError("zip failed"))  # type: ignore

    input_path = tmp_path / "input.csv"
    input_path.write_text("url\nhttps://example.com")

    await manager._run_background("abc", input_path)

    store.set_archive_path.assert_called_once()
    store.mark_failed.assert_called_once()
    args, _ = store.mark_failed.call_args
    assert args[0] == "abc"
    assert "Archive failed" in args[1]
    store.mark_succeeded.assert_not_called()
