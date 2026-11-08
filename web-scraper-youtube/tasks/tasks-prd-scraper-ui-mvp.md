## Relevant Files

- `web-scraper-python/api/app.py` - FastAPI application entrypoint exposing UI and API endpoints.
- `web-scraper-python/api/run_manager.py` - Orchestrates pipeline runs and background execution.
- `web-scraper-python/api/storage.py` - Stores run metadata and artifact references.
- `web-scraper-python/api/templates/index.html` - Frontend page for CSV upload and run tracking.
- `web-scraper-python/tests/test_run_manager.py` - Tests for run orchestration and state transitions.
- `web-scraper-python/tests/test_storage.py` - Tests for persistence layer interactions.

### Notes

- Place FastAPI templates under `web-scraper-python/api/templates/` to keep concerns localized.
- Reuse the existing virtualenv and dependency management (`requirements.txt`).

## Tasks

- [ ] 1.0 Establish FastAPI backend structure and dependencies
- [ ] 2.0 Implement run orchestration, persistence, and artifact packaging
- [ ] 3.0 Build CSV upload + run status UI
- [ ] 4.0 Add authentication guard and environment configuration hooks
- [ ] 5.0 Write automated tests and update documentation
