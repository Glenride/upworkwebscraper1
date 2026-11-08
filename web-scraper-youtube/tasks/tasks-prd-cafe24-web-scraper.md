## Relevant Files

- `web-scraper-python/scrape.py` - Current scraping script to review for reuse or refactor into modular pipeline.
- `web-scraper-python/requirements.txt` - Existing Python dependencies; extend to cover Playwright, Pillow, OpenCV, proxy libraries.
- `web-scraper-python/docker/` (new) - Dockerfile and entrypoint to containerize the MVP.
- `web-scraper-python/config/` (new) - Runtime configuration files (proxy credentials, schedule settings, template metadata).
- `web-scraper-python/templates/` (new) - Storage for supplier/policy template images.
- `web-scraper-python/tests/` (new) - Automated test suite for scraping, parsing, and image processing components.

### Notes

- Align new modules with existing project structure to avoid duplication; prefer extending `web-scraper-python`.
- Use pytest for unit/integration tests and include fixtures for sample Cafe24 pages and images.
- Configure logging in JSON format to simplify ingest into client tooling.

## Tasks

- [ ] 1.0 Establish MVP project infrastructure and configuration
  - [ ] 1.1 Audit existing `web-scraper-python` codebase to identify reusable components and gaps
  - [ ] 1.2 Create project Dockerfile, entrypoint script, and environment variable schema
  - [ ] 1.3 Define directory layout for inputs, outputs, templates, and logs
  - [ ] 1.4 Implement settings module loading `.env` / config files without mutating production secrets
  - [ ] 1.5 Add pre-commit hooks or linting configuration consistent with project standards

- [ ] 2.0 Implement client URL intake, manual trigger, and daily scheduling
  - [ ] 2.1 Build CLI interface that accepts input URL list (CSV/JSON) and output path parameters
  - [ ] 2.2 Implement validation for provided URLs (format, duplicates, empties)
  - [ ] 2.3 Add manual run command with configurable run ID/timestamped output folder
  - [ ] 2.4 Integrate lightweight scheduler (cron-compatible script or APScheduler) for daily execution
  - [ ] 2.5 Document run commands and scheduling setup in README

- [ ] 3.0 Build Cafe24 scraping pipeline with required Shopify data mapping and anti-scraping controls
  - [ ] 3.1 Research existing Cafe24 markup to confirm selectors and dynamic content points
  - [ ] 3.2 Implement Scrapy spiders/services to fetch product pages with retry and proxy rotation
  - [ ] 3.3 Add Playwright fallback workflow for pages requiring JavaScript rendering
  - [ ] 3.4 Normalize extracted fields to Shopify mapping table (handle, vendor, inventory, options, etc.)
  - [ ] 3.5 Persist bilingual content as structured data (e.g., `description_ko`, `description_en`)
  - [ ] 3.6 Capture anti-scraping telemetry (IP bans, CAPTCHA triggers) in `logs/anti_scraping.log`
  - [ ] 3.7 Write unit tests for parsing/mapping functions using saved HTML fixtures

- [ ] 4.0 Implement automated detail image processing and asset management
  - [ ] 4.1 Download main and gallery images with deterministic naming linked to SKU/handle
  - [ ] 4.2 Implement template matching + cropping pipeline using OpenCV and Pillow
  - [ ] 4.3 Handle low-confidence matches by logging, skipping crop, and flagging in QA report
  - [ ] 4.4 Store supplier template and metadata (`config/image_template.json`) with checksum verification
  - [ ] 4.5 Write automated tests covering crop success, failure, and multi-match scenarios with sample images

- [ ] 5.0 Generate Shopify-ready outputs and execution reporting
  - [ ] 5.1 Assemble Shopify CSV/Excel output including bilingual considerations
  - [ ] 5.2 Zip image assets into structured archive (`images/<handle>_*.jpg`)
  - [ ] 5.3 Produce execution summary (JSON/CSV) capturing run stats, failures, and flagged products
  - [ ] 5.4 Validate CSV by performing dry-run import against Shopify test environment (if available)
  - [ ] 5.5 Implement automated tests verifying CSV schema and data integrity for sample products

- [ ] 6.0 Perform QA validation and prepare Dockerized deployment package
  - [ ] 6.1 Execute end-to-end run on sample dataset (≥10 products) and review outputs
  - [ ] 6.2 Document QA findings, manual follow-ups, and mitigation steps
  - [ ] 6.3 Finalize Docker image build, tag, and push workflow (if registry provided)
  - [ ] 6.4 Draft deployment & operations guide covering scheduling, config updates, and troubleshooting
  - [ ] 6.5 Ensure all tests pass in CI and provide summary to client
