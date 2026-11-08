## Relevant Files

- `api/templates/index.html` – Add navigation and UI for the new screenshot/text scraper page.
- `api/app.py` – Register new routes, authentication guards (WorkOS), and template rendering.
- `api/run_manager.py` – Reference for run orchestration; new module will mirror structure.
- `api/visual_runner.py` – New module to manage screenshot/text runs (creation, status updates).
- `api/storage.py` – Extend schema for new run type if needed (separate table or status fields).
- `scraper/visual/` – New package housing headless browser logic (Playwright/Puppeteer wrapper, text extraction utilities).
- `tests/` – Add coverage for new runner, storage updates, and API endpoints (pytest).
- `config/settings.py` – Extend settings for visual scraper output root, WorkOS keys, and batch limits.
- `deploy/README.md` – Document additional env vars and deployment considerations (browser deps, auth).

### Notes

- Keep Python/Node separation clear if reusing Puppeteer—consider Playwright for single-language stack.
- WorkOS needs environment variables (client ID, secret, redirect); ensure they are injected securely.

## Tasks

- [ ] 1.0 Update UI navigation and layout
  - [ ] 1.1 Add tab or sidebar entry for "Visual QA" scraper in `index.html`
  - [ ] 1.2 Create dedicated section with URL input, CSV upload, and run list styled consistently
  - [ ] 1.3 Update preview modal to support screenshot thumbnails + text snippet display

- [ ] 2.0 Implement backend routes & auth
  - [ ] 2.1 Add FastAPI routes (`/visual`, `/visual/runs`, etc.) with WorkOS SSO protection
  - [ ] 2.2 Integrate WorkOS client credentials and session validation middleware
  - [ ] 2.3 Wire run creation endpoint to enqueue visual scraper jobs and reuse status polling JSON format

- [ ] 3.0 Build visual scraper runner
  - [ ] 3.1 Choose headless engine (Playwright or Node Puppeteer) and implement screenshot capture + DOM text extraction
  - [ ] 3.2 Create `VisualRunManager` mirroring `RunManager` for queueing, background execution, artifact bundling
  - [ ] 3.3 Ensure deliverables zip contains text files, screenshots, and summary without bloated archives
  - [ ] 3.4 Support configurable batch size and concurrency limits via settings

- [ ] 4.0 Persist and expose run data
  - [ ] 4.1 Extend `RunStore` or add new tables to track visual runs separately
  - [ ] 4.2 Update API responses to include screenshot/text metadata for modal rendering
  - [ ] 4.3 Provide cleanup utilities (optional) to prune old artifacts and maintain storage health

- [ ] 5.0 Validation & docs
  - [ ] 5.1 Add pytest coverage for visual runner success/failure paths and storage changes
  - [ ] 5.2 Update `deploy/README.md` with new env vars (WorkOS secrets, batch limits, browser deps)
  - [ ] 5.3 Smoke-test via local run and document workflow in README (usage + auth setup)
