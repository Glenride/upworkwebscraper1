# PRD: Multi-Platform Screenshot & Text Capture Scraper UI

## Overview
Add a new page within the scraper UI that lets operators run a "visual QA" workflow: capture full-page screenshots of arbitrary product URLs (not limited to Cafe24) and extract visible text for review. The feature should mirror the existing run experience (queue, status updates, modal previews, deliverables download) while focusing on image capture + text extraction rather than structured Shopify output.

## Goals
- Enable operators to submit any set of URLs and receive both screenshots and extracted text per page.
- Produce downloadable artifacts (zip archive) and in-app previews similar to the current Cafe24 runs.
- Support multiple platforms (Cafe24, Shopify, generic HTML) by falling back to headless browser capture and DOM text extraction.
- Integrate WorkOS authentication for access control to the new page.

## User Stories
- As an operations team member, I can paste a list of product URLs and trigger a job that returns screenshots and text summaries for quick QA review.
- As an operator, I can preview each result within the modal UI (screenshot thumbnail + extracted text) before downloading the zip.
- As an operator, I can switch between small manual runs and larger batch inputs by uploading a CSV.
- As an operator, I must authenticate via WorkOS SSO before accessing the visual QA page.

## Functional Requirements
1. Add a new navigation entry and page in the UI dedicated to the screenshot/text scraper, preserving the existing run list behavior (status table, polling, modal preview).
2. Accept both manual URL input (textarea) and CSV upload (same format as current pipeline) with a tunable limit per run (default 50, configurable via environment variable) and display warnings for larger batches.
3. Trigger a backend job that uses a headless browser (Puppeteer/Playwright) to render each URL, capture full-page screenshots, and extract text (basic DOM text nodes). Store outputs under a dedicated run directory.
4. Write per-run artifacts: `text/<slug>.txt`, `screenshots/<slug>.png`, plus an aggregated JSON summary. Bundle them into `deliverables.zip` for download.
5. Update the preview modal to display (a) screenshot thumbnail (or link) and (b) extracted text snippet with expand/collapse controls.
6. Surface errors (network fail, blocked resource, etc.) per URL in both run summary and UI, without blocking the rest of the run.
7. Integrate WorkOS authentication for the entire new page (redirect to SSO), while keeping the existing Cafe24 page behind basic auth until the broader auth story is aligned.

## Non-Goals
- Replacing or modifying the existing Cafe24 data pipeline.
- Performing OCR on images; rely on DOM text extraction only.
- Implementing long-term storage beyond current output directory + deliverables zip.
- Handling authentication for the legacy page (remains on basic auth for now).

## Design Considerations
- Follow the newly redesigned UI styling (Inter font, Atlassian-style components) for consistent look and feel.
- Consider a tabbed interface or sidebar to switch between Cafe24 pipeline and screenshot scraper.
- Provide immediate feedback when a URL fails (mark row with warning icon).
- For large batches, consider showing progress indicators or chunked updates to avoid long spinner-only states.

## Technical Considerations
- Introduce a headless browser runner (likely Playwright for Python or reusing existing Node Puppeteer workflow). Evaluate resource impact when running locally or on Fly.io; ensure configurable concurrency.
- Use a service layer analogous to `RunManager` with separate queue/executor to avoid interference with data pipeline runs.
- Implement WorkOS auth using their FastAPI integration (middleware validating JWT/session); store redirect URLs securely.
- Ensure archives stay small by bundling only screenshots/text files (reuse recent deliverables fix pattern).
- Make run output directory configurable via new settings keys (e.g., `SCRAPER_VISUAL_OUTPUT_ROOT`).

## Success Metrics
- 100% of reachable URLs produce a screenshot and text file in the deliverables zip.
- Screenshot preview loads in modal within 5 seconds for typical runs (<20 URLs).
- Error handling surfaces failed URLs with descriptive messages in summary and UI.
- WorkOS SSO required before accessing the new page.

## Open Questions
- Preferred headless browser stack (Playwright vs. existing Node Puppeteer script). Can we reuse `web-scraper-node` code? 
- Maximum batch size tolerance on local deployments—should we enforce hard limits or queueing?
- Should text extraction include basic formatting (headings, lists) or just raw concatenated text?
- Do we need retention/cleanup policies distinct from Cafe24 runs?
