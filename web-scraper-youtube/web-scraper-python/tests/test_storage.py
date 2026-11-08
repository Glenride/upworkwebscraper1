import tempfile
from pathlib import Path

import pytest

from api.storage import RunStatus, RunStore


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    return tmp_path / "runs.db"


def test_initialize_creates_table(temp_db: Path) -> None:
    store = RunStore(temp_db)
    store.initialize()

    assert temp_db.exists()


def test_create_and_retrieve_run(temp_db: Path) -> None:
    store = RunStore(temp_db)
    store.initialize()

    store.create_run(run_id="123", input_path=Path("/tmp/input.csv"), input_filename="input.csv", source="upload")
    record = store.get_run("123")

    assert record is not None
    assert record.id == "123"
    assert record.status == RunStatus.QUEUED
    assert record.input_filename == "input.csv"
    assert record.source == "upload"


def test_mark_transitions(temp_db: Path) -> None:
    store = RunStore(temp_db)
    store.initialize()
    store.create_run(run_id="abc", input_path=Path("/tmp/foo.csv"), input_filename="foo.csv", source="upload")

    store.mark_running("abc")
    assert store.get_run("abc").status == RunStatus.RUNNING

    output_dir = Path("/tmp/output")
    csv_path = output_dir / "shopify.csv"
    csv_path_str = str(csv_path)
    store.mark_succeeded(
        "abc",
        output_dir=output_dir,
        csv_path=csv_path,
        summary_path=None,
        images_zip_path=None,
        screenshots_zip_path=None,
        archive_path=None,
        log_path=None,
    )
    record = store.get_run("abc")
    assert record.status == RunStatus.SUCCEEDED
    assert record.csv_path == csv_path

    store.mark_failed("abc", "boom")
    assert store.get_run("abc").status == RunStatus.FAILED
