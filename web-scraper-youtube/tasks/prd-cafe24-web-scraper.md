# Cafe24 Product Data Scraper & Image Editor — MVP PRD

## 1. Introduction / Overview
Build a Python-based MVP scraper that ingests a provided list of Cafe24 product URLs, extracts Shopify-ready product data (including multilingual descriptions), and automatically processes long detail images to remove supplier policy blocks. The MVP must allow both manual on-demand runs and a daily scheduled execution, delivering CSV/Excel data and cropped images for Shopify import.

## 2. Goals
1. Deliver a reliable scraping workflow that successfully extracts required Shopify fields for 200–300 Cafe24 products.
2. Automate image refinement so each detail image has supplier information removed without manual editing.
3. Package data and assets into Shopify-ready formats (CSV/Excel + image archive) and run inside a Dockerized environment for client deployment.
4. Provide logging and reporting that enable the client to validate run quality and manually address any flagged records.

## 3. User Stories
- As a data team member, I want to run the scraper on-demand so I can refresh product data before bulk uploads.
- As an operations manager, I want the scraper to execute daily so new or updated products are captured automatically.
- As a Shopify merchandiser, I want the delivered CSV and image assets to import without manual cleanup so I can list products quickly.

## 4. Functional Requirements
1. **URL Intake**: Accept a CSV/JSON list of Cafe24 product URLs provided by the client.
2. **Scheduling & Manual Trigger**: Support both CLI-triggered runs and a configurable daily schedule (e.g., cron or workflow runner).
3. **Data Extraction**: Scrape each product page for all mandatory Shopify columns (handle, product type, vendor, tags, pricing, inventory, options, descriptions, etc.) and output in UTF-8.
4. **Multilingual Capture**: When both Korean and English content are present, store both versions (e.g., separate fields or structured JSON) and choose the appropriate version for Shopify fields.
5. **Image Download**: Download primary and gallery images at highest available resolution, storing them locally with deterministic filenames.
6. **Detail Image Processing**: Download the long detail image, identify shared supplier content via OpenCV template matching, crop it out, and save the processed image.
7. **Template Input**: Allow operators to supply the latest supplier/policy template image when available; fall back to previously supplied sample if no update is provided.
8. **Data Packaging**: Generate a Shopify-ready CSV (and optional Excel) and zip archive containing main/processed images.
9. **Execution Report**: Emit a run summary (successes, failures, anti-scraping events, missing template matches) in JSON/CSV for QA review.
10. **Error Handling & Retries**: Queue failed URLs for automatic retry (minimum two attempts) and clearly mark any unresolved failures in the run report.

## 5. Non-Goals (Out of Scope)
- Discovering product URLs by crawling Cafe24 category pages (assumes client-supplied URLs).
- Building a UI dashboard; MVP remains CLI/workflow driven.
- Permanent cloud storage integration; assets remain on the execution host for manual transfer.
- Automatic template generation—client must provide updated supplier/header samples when changes occur.

## 6. Design Considerations (Optional)
- Provide simple CLI flags or environment variables for run configuration (input file path, schedule toggle, output directories).
- Log formatting should align with existing client tooling (JSON lines preferred if compatible).

## 7. Technical Considerations (Optional)
- Implement within a Docker image compatible with the client’s infrastructure (Linux/Ubuntu host).
- Anti-scraping measures per instructions.md: rotating residential proxies (provider TBD), user-agent spoofing, Playwright fallback, and optional CAPTCHA solver integration.
- Store assets/output under a configurable local path (default `./output/<timestamp>`).
- Template assets reside under `assets/templates/` within the repo; ensure checksum validation before use.

## 8. Success Metrics
- ≥99% accuracy across required Shopify fields as validated by spot checks and import tests.
- <5% of products requiring manual cleanup per run (data or image issues).
- Daily automated run completes within agreed proxy/CAPTCHA usage limits and without cumulative failures.

## 9. Open Questions
1. Confirm proxy and CAPTCHA providers plus usage budgets for the MVP deployment.
2. Decide on the exact data structure for storing bilingual content in the Shopify CSV or ancillary files.
3. Determine retention policy for generated artifacts on the local filesystem.
