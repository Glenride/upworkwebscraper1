## Relevant Files

- `Dockerfile` – Container image definition for the FastAPI scraper UI.
- `.dockerignore` – Excludes large or secret files from the build context.
- `docker/entrypoint.sh` – Wrapper script to run migrations/setup before starting Uvicorn (optional but planned).
- `fly.toml` – Fly.io application configuration, including volumes and service definition.
- `deploy/README.md` – Deployment runbook with platform, Cloudflare, and operational procedures.
- `deploy/cleanup-script.py` – Optional helper to prune old artifacts on the host.
- `config/settings.py` – May require tweaks to read additional environment variables (e.g., PORT, storage paths).
- `README.md` – Update with containerized deployment instructions.

### Notes

- Unit tests remain under `web-scraper-python/tests/` and should be run inside the container image (`pytest`).
- Use `docker compose run --rm app pytest` (if compose file added) or `docker run --rm -it image pytest` after building to validate.

## Tasks

- [ ] 1.0 Containerize the scraper UI
  - [ ] 1.1 Inventory runtime dependencies and confirm they are listed in `requirements.txt`
  - [ ] 1.2 Create a production-ready `Dockerfile` (multi-stage build, installs system deps, runs Uvicorn bound to `$PORT`)
  - [ ] 1.3 Add `.dockerignore` to shrink the build context and protect secrets
  - [ ] 1.4 Implement `docker/entrypoint.sh` to apply env defaults, ensure directories exist, and launch the app
  - [ ] 1.5 Update `README.md` with local Docker build/run/test commands

- [ ] 2.0 Prepare free-tier hosting configuration
  - [ ] 2.1 Author `fly.toml` for Fly.io (app name placeholder, 256MB machine, volume mount, health checks)
  - [ ] 2.2 Document alternative instructions for Render/Railway in `deploy/README.md` (not full configs, but adaptation notes)
  - [ ] 2.3 Verify image size < Fly.io free limits and note trade-offs (e.g., disabling puppeteer features if necessary)

- [ ] 3.0 Configure persistence, secrets, and cleanup
  - [ ] 3.1 Define Fly volume (or equivalent) for `ui_runs.db` + `output/` and document attach/mount steps
  - [ ] 3.2 Document environment variable management (Fly secrets, Render env vars) and secure handling of `.env`
  - [ ] 3.3 Provide `deploy/cleanup-script.py` or command snippet to prune oversized deliverables periodically
  - [ ] 3.4 Confirm app can read/write to mounted storage inside container (manual test instructions)

- [ ] 4.0 Integrate with Cloudflare
  - [ ] 4.1 Document DNS setup (proxied A/AAAA or CNAME) and SSL mode for the chosen platform
  - [ ] 4.2 Include optional Cloudflare Tunnel walkthrough for local/dev testing
  - [ ] 4.3 Note caching headers and recommend bypass for dynamic endpoints while caching static assets

- [ ] 5.0 Produce deployment runbook & operational guide
  - [ ] 5.1 Draft `deploy/README.md` covering initial deploy, redeploys, scaling, and rollback steps
  - [ ] 5.2 Add section on health checks, log inspection (`fly logs`, platform equivalents), and troubleshooting
  - [ ] 5.3 List post-deploy validation checklist (run scrape, download zip, view preview modal) and rollback plan
