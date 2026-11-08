# Web Scrapers

This repo now houses two coordinated scrapers for the Cafe24 → Shopify pipeline:

1. **Python pipeline (`web-scraper-python/`)** – loads URLs, downloads product data + images, transforms to Shopify CSV, and writes run summaries.
2. **Node.js Puppeteer workflow (`web-scraper-node/`)** – loads the same URL list and captures full page/detail screenshots for QA or marketing assets.

Both tools rely on the shared `urls.csv` file stored at the repository root.

## Visual QA (Screenshots + Text Extraction)

The FastAPI UI now exposes a **Visual QA** tab that captures full-page Chromium screenshots and extracted body text for arbitrary URLs. Runs are queued via the new `VisualRunManager` and stored alongside the existing Cafe24 pipeline history.

### Requirements

- Playwright runtime with Chromium browser assets:

  ```bash
  pip install --user -r web-scraper-python/requirements.txt
  /Users/dvaughnhouse/Library/Python/3.10/bin/playwright install chromium
  ```

- Environment variables (see `.env`):

  ```
  SCRAPER_VISUAL_OUTPUT_ROOT=/absolute/path/to/visual_output
  SCRAPER_VISUAL_MAX_URLS=50          # default cap per run
  SCRAPER_VISUAL_MAX_IMAGES=10        # optional image cap (future use)

  WORKOS_CLIENT_ID=...
  WORKOS_API_KEY=...
  WORKOS_CONNECTION_ID=...            # or WORKOS_ORGANIZATION_ID
  WORKOS_REDIRECT_URI=https://app.example.com/visual/callback
  SCRAPER_SESSION_SECRET=super-secret
  ```

### Usage

- Navigate to `http://localhost:8001/` and select the **Visual QA** tab.
- If WorkOS SSO is configured, complete the login handshake before submitting jobs.
- Paste URLs or upload a CSV (one URL per row). Submit to enqueue.
- Polling updates the run list with download links for:
  - `summary.json` previews (via modal)
  - Raw artifacts (`/visual/runs/{id}/files/...`)
  - `deliverables.zip` bundles

## Python Pipeline

### Install / activate

```bash
cd web-scraper-python
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Populate a `.env.local` (or `.env`) with configuration—minimum:

```
SCRAPER_INPUT_URLS=/absolute/path/to/urls.csv
```

### Run a scrape

```bash
cd web-scraper-python
../.venv/bin/python scrape.py --env-file ../.env.local --run-id <run-name>

# optional: automatically trigger Puppeteer screenshots
# ../.venv/bin/python scrape.py --env-file ../.env.local --run-id <run-name> --enable-puppeteer
```

Outputs land in `web-scraper-python/output/<run-name>/` and include:

- `shopify_import.csv` – Shopify-ready rows
- `run_summary.json` – success/failure counts
- `images/` – downloaded images (when available)
- `screenshots/` – Puppeteer output when enabled

### Docker (optional)

The FastAPI UI is container-ready. Build and run locally:

```bash
docker build -t cafe24-scraper -f web-scraper-python/docker/Dockerfile .
docker run --rm -it \
  -e SCRAPER_INPUT_URLS=/data/urls.csv \
  -v $(pwd)/urls.csv:/data/urls.csv:ro \
  -v $(pwd)/web-scraper-python/output:/data/output \
  -v $(pwd)/web-scraper-python/logs:/data/logs \
  -v $(pwd)/web-scraper-python/ui_runs.db:/data/ui_runs.db \
  -p 8001:8000 \
  cafe24-scraper
```

See `deploy/README.md` for Fly.io + Cloudflare deployment steps.

## Node.js Puppeteer Screenshots

### Install

```bash
cd web-scraper-node
npm install
```

### Capture screenshots

```bash
cd web-scraper-node
node scrape.js \
  --input ../urls.csv \
  --output ../web-scraper-python/output/screenshots \
  --width 1440 \
  --height 900
```

The script reads the same CSV, visits each product page, and saves:

- `<slug>-full.png` – full page screenshot
- `<slug>-detail.png` – cropped detail/product section screenshot

## Suggested Integration Flow

1. Update `urls.csv` with the product pages to scrape.
2. Run the Python pipeline to collect structured data and raw images.
   - Add `--enable-puppeteer` to have the Python runner invoke the Node workflow automatically.
3. Run the Puppeteer workflow manually when debugging or capturing alternate viewport sizes.
4. Package `output/<run-id>/` plus `output/screenshots/` for QA or Shopify import.
