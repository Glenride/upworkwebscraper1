"""FastAPI application exposing the scraper UI and API."""

from __future__ import annotations

import csv
import io
import json
import secrets
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from config import Settings, load_settings

from .run_manager import RunManager, configure_manager
from .storage import RunStore, RunStatus
from .visual_manager import VisualRunManager, configure_visual_manager
from .visual_store import VisualRunStore

TEMPLATE_DIR = Path(__file__).parent / "templates"
UPLOAD_DIR_NAME = "ui_uploads"


security = HTTPBasic(auto_error=False)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or load_settings()
    templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

    def store_factory(db_path: Path) -> RunStore:
        return RunStore(db_path)

    manager = configure_manager(settings, store_factory)

    visual_store = VisualRunStore(settings.ui_database_path)
    visual_manager = configure_visual_manager(settings, visual_store)

    app = FastAPI(title="Cafe24 Scraper UI", version="0.1.0")
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret or "scraper-session-secret")

    app.state.settings = settings
    app.state.manager = manager
    app.state.visual_manager = visual_manager
    app.state.visual_store = visual_store
    app.state.templates = templates

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        manager.shutdown()
        visual_manager.shutdown()

    def get_settings() -> Settings:
        return settings

    def get_manager() -> RunManager:
        return manager

    def get_store() -> RunStore:
        return manager.store

    def get_visual_manager() -> VisualRunManager:
        return visual_manager

    def get_visual_store() -> VisualRunStore:
        return visual_store

    def require_basic_auth(
        credentials: Optional[HTTPBasicCredentials] = Depends(security),
        settings: Settings = Depends(get_settings),
    ) -> None:
        username = settings.ui_basic_auth_username
        password = settings.ui_basic_auth_password
        if not username or not password:
            return None
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        if not secrets.compare_digest(credentials.username, username) or not secrets.compare_digest(
            credentials.password, password
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    @app.get("/healthz", response_class=JSONResponse)
    async def healthcheck() -> dict:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def index(
        request: Request,
        settings: Settings = Depends(get_settings),
        store: RunStore = Depends(get_store),
        auth=Depends(require_basic_auth),
    ) -> HTMLResponse:
        runs = list(store.list_runs())
        default_input = settings.input_urls_path
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "runs": runs,
                "default_input": default_input,
                "visual_default_max": settings.visual_default_max_urls,
            },
        )

    @app.post("/runs", response_class=RedirectResponse)
    async def create_run(
        request: Request,
        use_default: str = Form("default"),
        upload: Optional[UploadFile] = File(None),
        manager: RunManager = Depends(get_manager),
        settings: Settings = Depends(get_settings),
        auth=Depends(require_basic_auth),
    ) -> RedirectResponse:
        if use_default not in {"default", "upload"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid input selection")

        source = "default"
        input_path = settings.input_urls_path

        if use_default == "upload":
            if upload is None or upload.filename is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV upload required")
            if not upload.filename.lower().endswith(".csv"):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV uploads supported")
            upload_dir = settings.output_root / UPLOAD_DIR_NAME
            upload_dir.mkdir(parents=True, exist_ok=True)
            dest_name = f"{uuid.uuid4().hex}_{upload.filename}"
            dest_path = upload_dir / dest_name
            contents = await upload.read()
            dest_path.write_bytes(contents)
            input_path = dest_path
            source = "upload"

        run_id = await manager.enqueue_run(input_path=input_path, source=source)
        return RedirectResponse(url=f"/?triggered={run_id}", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/runs", response_class=JSONResponse)
    async def list_runs(store: RunStore = Depends(get_store), auth=Depends(require_basic_auth)) -> list[dict]:
        return [run.to_dict() for run in store.list_runs()]

    @app.get("/runs/{run_id}", response_class=JSONResponse)
    async def get_run(run_id: str, store: RunStore = Depends(get_store), auth=Depends(require_basic_auth)) -> dict:
        record = store.get_run(run_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        return record.to_dict()

    @app.get("/runs/{run_id}/download")
    async def download_run(run_id: str, store: RunStore = Depends(get_store), auth=Depends(require_basic_auth)):
        record = store.get_run(run_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        if record.status != RunStatus.SUCCEEDED or not record.archive_path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Run archive unavailable")
        archive_path = Path(record.archive_path)
        if not archive_path.exists():
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Archive no longer exists")
        return FileResponse(archive_path, filename=archive_path.name)

    @app.get("/runs/{run_id}/preview", response_class=JSONResponse)
    async def preview_run(
        run_id: str,
        limit: int = 3,
        store: RunStore = Depends(get_store),
        auth=Depends(require_basic_auth),
    ) -> dict:
        if limit <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Limit must be positive")

        record = store.get_run(run_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        if record.status != RunStatus.SUCCEEDED or not record.csv_path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Run results unavailable")

        csv_path = Path(record.csv_path)
        if not csv_path.exists():
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Run CSV no longer exists")

        previews = _load_preview_rows(csv_path, limit)
        return {"run_id": run_id, "records": previews, "total": len(previews)}

    @app.get("/runs/{run_id}/log")
    async def download_log(run_id: str, store: RunStore = Depends(get_store), auth=Depends(require_basic_auth)):
        record = store.get_run(run_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        if not record.log_path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Log unavailable")
        log_path = Path(record.log_path)
        if not log_path.exists():
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Log file removed")
        return FileResponse(log_path, filename=log_path.name, media_type="text/plain")

    def _parse_visual_urls(data: str) -> list[str]:
        return [line.strip() for line in data.splitlines() if line.strip()]

    def _read_uploaded_urls(contents: bytes) -> list[str]:
        try:
            decoded = contents.decode("utf-8")
        except UnicodeDecodeError:
            decoded = contents.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(decoded))
        urls = []
        for row in reader:
            if not row:
                continue
            urls.extend(cell.strip() for cell in row if cell.strip())
        return urls

    @app.post("/visual/runs", response_class=RedirectResponse)
    async def create_visual_run(
        request: Request,
        use_textarea: str = Form("false"),
        urls_text: str = Form(""),
        max_urls: Optional[int] = Form(None),
        upload: Optional[UploadFile] = File(None),
        visual_manager: VisualRunManager = Depends(get_visual_manager),
        auth=Depends(require_basic_auth),
    ) -> RedirectResponse:
        urls: list[str] = []
        source = "textarea" if use_textarea == "true" else "upload"
        input_label = "manual"
        input_path: Optional[Path] = None

        if source == "textarea":
            urls = _parse_visual_urls(urls_text)
        else:
            if not upload or not upload.filename:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV upload required")
            if not upload.filename.lower().endswith(".csv"):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV uploads supported")
            contents = await upload.read()
            urls = _read_uploaded_urls(contents)
            input_label = upload.filename
            upload_dir = Path(request.app.state.settings.output_root) / UPLOAD_DIR_NAME
            upload_dir.mkdir(parents=True, exist_ok=True)
            dest = upload_dir / f"{uuid.uuid4().hex}_{upload.filename}"
            dest.write_bytes(contents)
            input_path = dest

        if not urls:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No URLs provided")

        limit: Optional[int] = None
        if max_urls is not None:
            try:
                limit = max(1, int(max_urls))
            except (TypeError, ValueError):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid max URLs value")

        run_id = await visual_manager.enqueue_run(
            urls=urls,
            source=source,
            input_label=input_label,
            input_path=input_path,
            max_urls=limit,
        )

        return RedirectResponse(url=f"/?visual=1&triggered={run_id}", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/visual/runs", response_class=JSONResponse)
    async def list_visual_runs(
        store: VisualRunStore = Depends(get_visual_store),
        auth=Depends(require_basic_auth),
    ) -> list[dict]:
        return [run.to_dict() for run in store.list_runs()]

    @app.get("/visual/runs/{run_id}", response_class=JSONResponse)
    async def get_visual_run(
        run_id: str,
        store: VisualRunStore = Depends(get_visual_store),
        auth=Depends(require_basic_auth),
    ) -> dict:
        record = store.get_run(run_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        return record.to_dict()

    @app.get("/visual/runs/{run_id}/download")
    async def download_visual_archive(
        run_id: str,
        store: VisualRunStore = Depends(get_visual_store),
        auth=Depends(require_basic_auth),
    ):
        record = store.get_run(run_id)
        if not record or record.status != RunStatus.SUCCEEDED or not record.archive_path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archive unavailable")
        archive_path = Path(record.archive_path)
        if not archive_path.exists():
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Archive removed")
        return FileResponse(archive_path, filename=archive_path.name)

    @app.get("/visual/runs/{run_id}/summary", response_class=JSONResponse)
    async def get_visual_summary(
        run_id: str,
        store: VisualRunStore = Depends(get_visual_store),
        auth=Depends(require_basic_auth),
    ) -> dict:
        record = store.get_run(run_id)
        if not record or record.status != RunStatus.SUCCEEDED or not record.summary_path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Summary unavailable")
        summary_path = Path(record.summary_path)
        if not summary_path.exists():
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Summary removed")
        return json.loads(summary_path.read_text(encoding="utf-8"))

    @app.get("/visual/runs/{run_id}/files/{relative_path:path}")
    async def get_visual_artifact(
        run_id: str,
        relative_path: str,
        store: VisualRunStore = Depends(get_visual_store),
        auth=Depends(require_basic_auth),
    ):
        record = store.get_run(run_id)
        if not record or not record.output_dir:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        output_dir = Path(record.output_dir)
        target_path = (output_dir / relative_path).resolve()
        if not str(target_path).startswith(str(output_dir.resolve())):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid artifact path")
        if not target_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact missing")
        return FileResponse(target_path)

    return app


app = create_app()


def _load_preview_rows(csv_path: Path, limit: int) -> List[dict]:
    previews: List[dict] = []
    seen_handles: set[str] = set()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            handle = row.get("Handle") or ""
            if handle in seen_handles:
                continue
            previews.append(
                {
                    "handle": handle,
                    "title": row.get("Title") or "",
                    "body_html": row.get("Body (HTML)") or "",
                }
            )
            seen_handles.add(handle)
            if len(previews) >= limit:
                break
    return previews
