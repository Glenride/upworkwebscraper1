from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from .storage import RunStatus


@dataclass
class VisualRunRecord:
    id: str
    status: RunStatus
    source: str
    input_label: str
    url_count: int
    input_path: Optional[Path]
    output_dir: Optional[Path]
    summary_path: Optional[Path]
    archive_path: Optional[Path]
    error: Optional[str]
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status.value,
            "source": self.source,
            "input_label": self.input_label,
            "url_count": self.url_count,
            "input_path": str(self.input_path) if self.input_path else None,
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "summary_path": str(self.summary_path) if self.summary_path else None,
            "archive_path": str(self.archive_path) if self.archive_path else None,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class VisualRunStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS visual_runs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    input_label TEXT NOT NULL,
                    url_count INTEGER NOT NULL,
                    input_path TEXT,
                    output_dir TEXT,
                    summary_path TEXT,
                    archive_path TEXT,
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
        source: str,
        input_label: str,
        url_count: int,
        input_path: Optional[Path],
    ) -> None:
        timestamp = datetime.utcnow().isoformat()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO visual_runs (
                        id, status, source, input_label, url_count,
                        input_path, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        RunStatus.QUEUED.value,
                        source,
                        input_label,
                        url_count,
                        str(input_path) if input_path else None,
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
        summary_path: Path,
        archive_path: Path,
    ) -> None:
        self._update_fields(
            run_id,
            status=RunStatus.SUCCEEDED,
            output_dir=str(output_dir),
            summary_path=str(summary_path),
            archive_path=str(archive_path),
            error=None,
        )

    def mark_failed(self, run_id: str, error: str) -> None:
        self._update_fields(run_id, status=RunStatus.FAILED, error=error)

    def set_archive_path(self, run_id: str, archive_path: Optional[Path]) -> None:
        self._update_fields(run_id, archive_path=str(archive_path) if archive_path else None)

    def list_runs(self, limit: int = 20) -> Iterable[VisualRunRecord]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM visual_runs ORDER BY datetime(created_at) DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_run(self, run_id: str) -> Optional[VisualRunRecord]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM visual_runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _update_fields(self, run_id: str, **fields: object) -> None:
        assignments = []
        values: list[object] = []
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
                    f"UPDATE visual_runs SET {', '.join(assignments)} WHERE id = ?",
                    values,
                )
                conn.commit()

    def _row_to_record(self, row: sqlite3.Row) -> VisualRunRecord:
        return VisualRunRecord(
            id=row["id"],
            status=RunStatus(row["status"]),
            source=row["source"],
            input_label=row["input_label"],
            url_count=int(row["url_count"]),
            input_path=Path(row["input_path"]) if row["input_path"] else None,
            output_dir=Path(row["output_dir"]) if row["output_dir"] else None,
            summary_path=Path(row["summary_path"]) if row["summary_path"] else None,
            archive_path=Path(row["archive_path"]) if row["archive_path"] else None,
            error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
