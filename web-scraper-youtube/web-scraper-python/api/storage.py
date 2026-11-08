"""Persistence layer for scraper UI run metadata."""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional


class RunStatus(str, Enum):
    """Lifecycle states for a scraper run."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class RunRecord:
    """Serialized representation of a scraper run for UI consumption."""

    id: str
    status: RunStatus
    input_path: Path
    input_filename: str
    source: str
    output_dir: Optional[Path]
    csv_path: Optional[Path]
    summary_path: Optional[Path]
    images_zip_path: Optional[Path]
    screenshots_zip_path: Optional[Path]
    archive_path: Optional[Path]
    log_path: Optional[Path]
    error: Optional[str]
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status.value,
            "input_path": str(self.input_path),
            "input_filename": self.input_filename,
            "source": self.source,
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "csv_path": str(self.csv_path) if self.csv_path else None,
            "summary_path": str(self.summary_path) if self.summary_path else None,
            "images_zip_path": str(self.images_zip_path) if self.images_zip_path else None,
            "screenshots_zip_path": str(self.screenshots_zip_path) if self.screenshots_zip_path else None,
            "archive_path": str(self.archive_path) if self.archive_path else None,
            "log_path": str(self.log_path) if self.log_path else None,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class RunStore:
    """Lightweight SQLite-backed persistence for scraper runs."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    input_path TEXT NOT NULL,
                    input_filename TEXT NOT NULL,
                    source TEXT NOT NULL,
                    output_dir TEXT,
                    csv_path TEXT,
                    summary_path TEXT,
                    images_zip_path TEXT,
                    screenshots_zip_path TEXT,
                    archive_path TEXT,
                    log_path TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def create_run(
        self,
        *,
        run_id: str,
        input_path: Path,
        input_filename: str,
        source: str,
        status: RunStatus = RunStatus.QUEUED,
    ) -> None:
        timestamp = datetime.utcnow().isoformat()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO runs (
                        id, status, input_path, input_filename, source,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        status.value,
                        str(input_path),
                        input_filename,
                        source,
                        timestamp,
                        timestamp,
                    ),
                )
                conn.commit()

    def mark_running(self, run_id: str) -> None:
        self._update_fields(run_id, status=RunStatus.RUNNING)

    def mark_succeeded(
        self,
        run_id: str,
        *,
        output_dir: Path,
        csv_path: Optional[Path],
        summary_path: Optional[Path],
        images_zip_path: Optional[Path],
        screenshots_zip_path: Optional[Path],
        archive_path: Optional[Path],
        log_path: Optional[Path],
    ) -> None:
        self._update_fields(
            run_id,
            status=RunStatus.SUCCEEDED,
            output_dir=str(output_dir),
            csv_path=str(csv_path) if csv_path else None,
            summary_path=str(summary_path) if summary_path else None,
            images_zip_path=str(images_zip_path) if images_zip_path else None,
            screenshots_zip_path=str(screenshots_zip_path) if screenshots_zip_path else None,
            archive_path=str(archive_path) if archive_path else None,
            log_path=str(log_path) if log_path else None,
            error=None,
        )

    def mark_failed(self, run_id: str, error: str) -> None:
        self._update_fields(run_id, status=RunStatus.FAILED, error=error)

    def set_archive_path(self, run_id: str, archive_path: Optional[Path]) -> None:
        path_str = str(archive_path) if archive_path else None
        self._update_fields(run_id, archive_path=path_str)

    def set_error(self, run_id: str, error: Optional[str]) -> None:
        self._update_fields(run_id, error=error)

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def list_runs(self, limit: int = 20) -> Iterable[RunRecord]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY datetime(created_at) DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def _update_fields(self, run_id: str, **fields: Optional[str | RunStatus]) -> None:
        assignments = []
        values: list[Optional[str]] = []
        for key, value in fields.items():
            if isinstance(value, RunStatus):
                value = value.value
            assignments.append(f"{key} = ?")
            values.append(value)
        assignments.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(run_id)

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    f"UPDATE runs SET {', '.join(assignments)} WHERE id = ?",
                    values,
                )
                conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _row_to_record(self, row: sqlite3.Row) -> RunRecord:
        return RunRecord(
            id=row["id"],
            status=RunStatus(row["status"]),
            input_path=Path(row["input_path"]),
            input_filename=row["input_filename"],
            source=row["source"],
            output_dir=Path(row["output_dir"]) if row["output_dir"] else None,
            csv_path=Path(row["csv_path"]) if row["csv_path"] else None,
            summary_path=Path(row["summary_path"]) if row["summary_path"] else None,
            images_zip_path=Path(row["images_zip_path"]) if row["images_zip_path"] else None,
            screenshots_zip_path=Path(row["screenshots_zip_path"]) if row["screenshots_zip_path"] else None,
            archive_path=Path(row["archive_path"]) if row["archive_path"] else None,
            log_path=Path(row["log_path"]) if row["log_path"] else None,
            error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
