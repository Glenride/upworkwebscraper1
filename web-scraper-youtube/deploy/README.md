# Deployment Runbook: Docker + Cloudflare

## Overview
This guide explains how to package the existing scraper UI into a Docker image, deploy it on a free-tier friendly platform (Fly.io baseline), and place Cloudflare in front for HTTPS and protection. No application code changes are required beyond the container packaging already added.

## 1. Prerequisites
- Docker CLI installed locally.
- Fly.io CLI (`fly`) installed and authenticated (free hobby plan).
- Cloudflare account with a domain you control.
- Copy of `.env`/`.env.local` with required secrets (`SCRAPER_INPUT_URLS`, etc.). Do **not** commit secrets; load them into the platform at deploy time.

Optional:
- `python3` for running helper cleanup scripts.

## 2. Build & test locally
```bash
# From repo root
docker build -t cafe24-scraper:latest -f web-scraper-python/docker/Dockerfile .

# Run locally with bind-mounted data (adjust paths as needed)
docker run --rm -it \
  -e SCRAPER_INPUT_URLS=/data/urls.csv \
  -v $(pwd)/urls.csv:/data/urls.csv:ro \
  -v $(pwd)/web-scraper-python/output:/data/output \
  -v $(pwd)/web-scraper-python/logs:/data/logs \
  -v $(pwd)/web-scraper-python/ui_runs.db:/data/ui_runs.db \
  -p 8001:8000 \
  cafe24-scraper:latest

# Then visit http://localhost:8001
```

### Running tests inside the container
```bash
docker run --rm -it cafe24-scraper:latest pytest tests/test_run_manager.py
```

## 3. Fly.io deployment
1. **Create app & volume** (replace `my-scraper`):
   ```bash
   fly launch --no-deploy --copy-config --name my-scraper
   fly volumes create scraper_data --size 1 --region iad
   ```
2. **Set secrets** (load your `.env` entries):
   ```bash
   fly secrets set SCRAPER_INPUT_URLS=/data/urls.csv SCRAPER_UI_USERNAME=... SCRAPER_UI_PASSWORD=...
   ```
   Upload required files (e.g., `urls.csv`) to the volume by using a `fly ssh console` session or via initial deployment with mounted file.
3. **Deploy**:
   ```bash
   fly deploy --config fly.toml
   ```
4. **Verify**:
   ```bash
   fly status
   fly logs
   ```
   Visit `https://<fly-app>.fly.dev` to confirm the UI loads. Run a scrape and ensure archives land on the mounted volume.

### Render / Railway notes
- Both platforms accept Dockerfiles. Use environment variables and persistent disks equivalent to Fly volume above.
- Ensure the service listens on the platform-provided `$PORT` (entrypoint already respects this).
- Configure persistent storage (Render: add disk; Railway: volume plugin).

## 4. Cloudflare configuration
1. Add an orange-cloud proxied DNS record (`A`/`AAAA` or `CNAME`) pointing to the Fly domain (e.g., `my-scraper.fly.dev`).
2. Set SSL/TLS mode to **Full**.
3. (Optional) Use **Cloudflare Tunnel** for staging by running `cloudflared tunnel` targeting the Fly app.
4. Create a page rule or cache rule to **bypass cache** for `/runs*` endpoints while allowing caching for static assets (CSS/JS) if needed.
5. Enable rate limiting or WAF rules if exposing beyond internal users.

## 5. Operations
- **Logs:** `fly logs` or platform equivalent.
- **Health:** Fly HTTP check hits `/healthz`; confirm status is `ok`.
- **Cleanup:** Run `python deploy/cleanup_script.py --keep 5` via SSH to prune old runs when storage tight.
- **Updates:**
  ```bash
  docker build -t cafe24-scraper:latest -f web-scraper-python/docker/Dockerfile .
  fly deploy --config fly.toml
  ```
- **Rollback:** Deploy the previous image (`fly deploy --image <image-id>`).

## 6. Validation checklist
- [ ] Visit Cloudflare-proxied domain and see UI over HTTPS.
- [ ] Start a scrape; confirm run transitions to **succeeded/failed** appropriately.
- [ ] Download deliverables zip successfully.
- [ ] Preview modal loads data while served through Cloudflare.
- [ ] Logs accessible and cleanup script works on host.

Keep this runbook up to date as the infrastructure evolves.
