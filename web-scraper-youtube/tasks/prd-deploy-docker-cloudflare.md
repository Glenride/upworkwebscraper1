# Deployment PRD: Docker-Based Scraper UI Behind Cloudflare

## Overview
Deploy the existing FastAPI scraper UI without modifying its functionality. Package the application in Docker, host it on a free-tier friendly provider, and front it with Cloudflare for SSL and basic protections. The deployment must remain low-cost while preserving the current ability to launch scrapes, monitor runs, and download artifacts.

## Goals
- Containerize the current FastAPI scraper UI so it can run consistently in any environment.
- Deploy the container on a free-tier capable platform with persistent storage for run metadata and deliverables.
- Configure Cloudflare in front of the deployment for HTTPS termination and optional caching.
- Provide simple operational scripts/documentation for starting, stopping, and updating the service.

## User Stories
- As an operator, I can deploy the scraper UI to a free-tier host and keep it running reliably behind Cloudflare.
- As an operator, I can access the deployed UI via HTTPS using my existing domain.
- As an operator, I can retrieve generated deliverables and logs from the deployed environment without losing data across restarts.

## Functional Requirements
1. Provide a Dockerfile that installs dependencies, copies the app, and launches Uvicorn with environment variables sourced at runtime.
2. Supply configuration (e.g., `fly.toml` or equivalent) for a free-tier host, assuming Fly.io as the primary target while documenting Render/Railway alternatives.
3. Ensure persistent storage for `ui_runs.db` and `web-scraper-python/output/` via mounted volume or documented object storage workflow.
4. Document Cloudflare setup: DNS, proxy mode, SSL/TLS mode, and optional Cloudflare Tunnel instructions.
5. Provide deployment runbook covering initial deploy, environment variable management, data backup/cleanup, and update procedure.
6. Add health-check endpoint or configuration to allow the platform to verify the service status.
7. Ensure logs are accessible (stdout/err) and document how to fetch them from the host platform.

## Non-Goals
- Refactoring application code or changing scraper behavior.
- Implementing CI/CD pipelines beyond basic manual instructions.
- Providing automated scaling or multi-region deployments.
- Implementing advanced monitoring or alerting solutions.

## Design Considerations
- UI should remain unchanged; only the deployment packaging and infrastructure are in scope.
- Modal preview and recent-run status features must function identically post-deployment.

## Technical Considerations
- Target: Fly.io free hobby tier (256MB VM) with option to adapt to Render/Railway if limits exceeded.
- Uvicorn should bind to `0.0.0.0` on a configurable port (`PORT` env var) for compatibility with hosts.
- Handle disk usage by documenting periodic cleanup of large deliverables to stay within free-tier storage caps.
- `.env` secrets must be loaded via platform environment variables and never committed.

## Success Metrics
- Successful deployment reachable via HTTPS through Cloudflare.
- Persistent data survives container restarts on the chosen platform.
- End-to-end scrape run completes on the deployed environment without errors.
- Deployment steps reproducible using documented runbook.

## Open Questions
- Final choice of free-tier provider if Fly.io limits are insufficient.
- Required level of access control (e.g., Cloudflare Access, HTTP Basic Auth) for public exposure.
- Long-term storage strategy for large deliverable archives beyond free-tier limits.
