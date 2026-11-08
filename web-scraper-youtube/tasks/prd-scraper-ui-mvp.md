# Cafe24 Scraper UI MVP — PRD

## 1. Introduction / Overview
Build a lightweight web interface that allows internal operators to upload or select a Cafe24 product URL CSV, trigger the existing Python scraping pipeline, and download a bundled archive of Shopify-ready deliverables. The UI should surface minimal status feedback and a link to the generated zip, while relying on the established scraping workflow for data processing.

## 2. Goals
1. Provide a simple UI flow to launch a scraper run using the client-supplied URL CSV.
2. Allow operators to monitor run progress and see whether it succeeded or failed.
3. Deliver a downloadable archive containing the CSV, summary report, images, and other assets produced by the scraper.
4. Prepare the implementation for deployment behind Cloudflare tooling without committing to a specific hosting topology yet.

## 3. User Stories
- As an operations specialist, I want to upload a CSV file and start a scrape so I can generate Shopify-ready deliverables without the CLI.
- As an operations specialist, I want to see when a run finishes (or fails) so I know when the download is available or if I need to retry.
- As an operations specialist, I want to download the generated zip so I can hand it off to downstream teams.

## 4. Functional Requirements
1. **CSV Intake UI**: The interface must accept a CSV file upload or allow selection of the repository-managed `urls.csv`, validating header format before submission.
2. **Run Trigger**: Provide a "Start Run" action that invokes the existing Python pipeline (`scrape.py` / `run_pipeline`) with the supplied CSV and a generated run ID.
3. **Run Status Feedback**: Display run state (queued, running, succeeded, failed) and expose console/log snippets or error messages when available.
4. **Deliverable Packaging**: After completion, present download links for the generated Shopify CSV, run summary, and the zipped images/screenshots (leveraging existing zip outputs when enabled).
5. **Run History (Minimal)**: Persist the most recent N runs (timestamp, run ID, status, output paths) so operators can retrieve past deliverables during the same deployment lifecycle.
6. **Auth Constraint**: Limit access to trusted users (basic HTTP auth or token gate) to prevent public triggering while keeping implementation lightweight.
7. **Configuration Awareness**: Respect existing environment-driven settings (templates directory, proxy, captcha key) without exposing secrets in the UI; reflect read-only values where helpful (e.g., output root).
8. **Error Handling**: Surface retriable errors (e.g., missing template) and provide a "Retry" option that reuses the same CSV and run parameters.

## 5. Non-Goals (Out of Scope)
- Advanced scheduling or cron management via the UI (manual runs only for the MVP).
- Multi-tenant user management or fine-grained permissions beyond a single shared credential/token.
- Editing scraper configuration, templates, or proxy settings in the UI.
- Real-time log streaming beyond periodic status polling/refresh.
- Cloudflare deployment automation (tunneling/CDN setup documented but not implemented).

## 6. Design Considerations (Optional)
- Favor a single-page layout with clearly separated sections for "Upload CSV", "Run Status", and "Recent Runs".
- Use existing brand-neutral styling (e.g., Tailwind or a minimalist component library) to speed delivery while keeping custom CSS minimal.
- Provide clear empty-state messaging (no runs yet, run completed, run failed) and disable actions while a run is in progress.

## 7. Technical Considerations (Optional)
- Reuse the Python stack: build a FastAPI (or Flask) backend that wraps the existing pipeline and exposes REST endpoints for run submission, status polling, and artifact retrieval.
- Serve a lightweight frontend (e.g., FastAPI templates + HTMX or a minimal React/Vite bundle) that can be hosted alongside the backend or on Cloudflare Pages with API calls routed through Cloudflare Tunnel/Zero Trust to the backend.
- Store transient run metadata/output references in sqlite (for local) or PostgreSQL (for prod) to persist recent history; align with environments (dev/test/prod) by using configurable database URLs.
- Ensure runs execute asynchronously (ThreadPool/ProcessPool or task queue) so the HTTP request returns immediately with a run ID.
- Package deliverables using existing zip outputs from the pipeline; if `zip_outputs` is disabled, create a zip wrapper post-run for UI downloads.
- Expose an authenticated API (shared secret, API token, or Cloudflare Access policy) to meet the auth constraint without complex user management.
- Prepare Docker assets to deploy the backend on compatible infrastructure (e.g., container behind Cloudflare Tunnel) while the frontend can live on Cloudflare Pages or the same container.

## 8. Success Metrics
- Operators can complete a CSV upload → run trigger → download zip flow end-to-end without CLI access.
- 100% of successful runs expose working download links within the UI.
- Basic auth/token gating prevents unauthenticated access during internal testing.
- Operators report no more than 1 retry per 10 runs due to UI flow issues (excluding scraper-level failures).

## 9. Open Questions
1. Should the CSV always be uploaded through the UI, or can the UI reference a shared, pre-synced `urls.csv` stored server-side?
2. What is the acceptable maximum CSV size for uploads, and should we enforce file size limits client-side?
3. Which authentication mechanism is preferred for MVP (HTTP basic auth, bearer token, Cloudflare Access integration)?
4. What retention period is required for past runs and artifacts (e.g., auto-delete after N days to manage storage)?
5. Do we need to surface partial progress (per-URL updates) or is high-level run status sufficient for the MVP?
