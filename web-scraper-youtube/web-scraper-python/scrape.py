"""CLI entrypoint for the Cafe24 scraper MVP."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import Settings, load_settings
from scraper.pipeline import PipelineSettings, run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cafe24 product scraper MVP runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--env-file", default=".env", help="Path to .env file for configuration overrides")
    parser.add_argument("--input", help="Path to client-supplied product URL list (CSV or JSON)")
    parser.add_argument("--output-root", help="Base directory for scraper outputs")
    parser.add_argument("--logs-root", help="Directory to store run logs")
    parser.add_argument("--templates-root", help="Directory containing supplier/policy template images")
    parser.add_argument("--run-id", help="Optional run identifier; defaults to timestamp if not provided")
    parser.add_argument("--enable-puppeteer", action="store_true", help="Capture screenshots via Puppeteer after scraping")
    parser.add_argument("--puppeteer-script", help="Path to Puppeteer capture script (scrape.js)")
    parser.add_argument("--puppeteer-bin", help="Node.js binary to invoke for Puppeteer runs")
    parser.add_argument("--puppeteer-output", help="Directory for Puppeteer screenshots")
    parser.add_argument("--no-zip", action="store_true", help="Disable packaging of images/screenshots into zip archives")
    parser.add_argument("--zip-images-name", help="Filename for compressed images archive")
    parser.add_argument("--zip-screenshots-name", help="Filename for compressed screenshots archive")
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run as a scheduler instead of executing a single scrape",
    )
    parser.add_argument("--cron", help="Cron expression for scheduled runs")
    return parser.parse_args()


def resolve_settings(args: argparse.Namespace) -> Settings:
    """Load settings and apply CLI overrides."""

    settings = load_settings(args.env_file)

    overrides = {}
    if args.input:
        overrides["input_urls_path"] = Path(args.input)
    if args.output_root:
        overrides["output_root"] = Path(args.output_root)
    if args.logs_root:
        overrides["logs_root"] = Path(args.logs_root)
    if args.templates_root:
        overrides["templates_root"] = Path(args.templates_root)
    if args.enable_puppeteer:
        overrides["puppeteer_enabled"] = True
    if args.puppeteer_script:
        overrides["puppeteer_script"] = Path(args.puppeteer_script)
    if args.puppeteer_bin:
        overrides["puppeteer_bin"] = Path(args.puppeteer_bin)
    if args.puppeteer_output:
        overrides["puppeteer_output_dir"] = Path(args.puppeteer_output)
    if args.no_zip:
        overrides["zip_outputs"] = False
    if args.zip_images_name:
        overrides["zip_images_name"] = args.zip_images_name
    if args.zip_screenshots_name:
        overrides["zip_screenshots_name"] = args.zip_screenshots_name
    if args.cron:
        overrides["schedule_cron"] = args.cron
        overrides["schedule_enabled"] = True
    elif args.schedule:
        overrides["schedule_enabled"] = True

    if overrides:
        settings = replace(settings, **overrides)

    _validate_settings(settings)
    return settings


def _validate_settings(settings: Settings) -> None:
    if not settings.input_urls_path.exists():
        raise FileNotFoundError(f"Input URLs file does not exist: {settings.input_urls_path}")
    settings.output_root.mkdir(parents=True, exist_ok=True)
    settings.logs_root.mkdir(parents=True, exist_ok=True)
    settings.templates_root.mkdir(parents=True, exist_ok=True)


def run_once(settings: Settings, run_id: Optional[str] = None) -> Path:
    """Execute a single scraper run and return the output directory."""

    run_identifier = run_id or datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    run_output_dir = settings.output_root / run_identifier
    run_output_dir.mkdir(parents=True, exist_ok=True)

    configure_logging(settings, run_identifier)
    logging.info("Starting Cafe24 scraper MVP run", extra={"run_id": run_identifier})
    logging.info("Input URLs path: %s", settings.input_urls_path)
    logging.info("Output directory: %s", run_output_dir)

    pipeline_settings = PipelineSettings(
        input_path=settings.input_urls_path,
        output_dir=run_output_dir,
        templates_dir=settings.templates_root,
        proxy_url=settings.proxy_url,
        captcha_key=settings.captcha_api_key,
        detail_template_name=settings.detail_template_name,
        zip_outputs=settings.zip_outputs,
        zip_images_name=settings.zip_images_name,
        zip_screenshots_name=settings.zip_screenshots_name,
    )

    result = run_pipeline(pipeline_settings)
    logging.info(
        "Pipeline complete: %s successes, %s failures",
        len(result.records),
        len(result.failures),
    )
    logging.info("CSV written to: %s", result.csv_path)
    logging.info("Summary written to: %s", result.summary_path)

    _maybe_run_puppeteer(settings, run_output_dir)

    return run_output_dir


def configure_logging(settings: Settings, run_id: str) -> None:
    log_file = settings.logs_root / f"scraper-{run_id}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
        force=True,
    )


def run_scheduler(settings: Settings) -> None:
    cron_expr = settings.schedule_cron
    scheduler = BlockingScheduler()
    trigger = CronTrigger.from_crontab(cron_expr)
    scheduler.add_job(run_once, trigger, args=[settings])

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    logging.info("Scheduler started with cron: %s", cron_expr)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Scheduler shutdown requested")
        scheduler.shutdown()


def main() -> None:
    args = parse_args()
    settings = resolve_settings(args)

    if args.schedule or settings.schedule_enabled:
        run_scheduler(settings)
    else:
        run_once(settings, run_id=args.run_id)
        # Allow time for asynchronous logging handlers to flush.
        time.sleep(0.25)


def _maybe_run_puppeteer(settings: Settings, run_output_dir: Path) -> None:
    if not settings.puppeteer_enabled:
        return

    script_path = settings.puppeteer_script or Path(__file__).resolve().parent.parent / "web-scraper-node" / "scrape.js"
    if not script_path.exists():
        logging.warning("Puppeteer script not found; skipping screenshot capture", extra={"script": str(script_path)})
        return

    node_bin = settings.puppeteer_bin or Path("node")
    output_dir = settings.puppeteer_output_dir or (run_output_dir / "screenshots")

    cmd = [
        str(node_bin),
        str(script_path),
        "--input",
        str(settings.input_urls_path),
        "--output",
        str(output_dir),
    ]

    logging.info("Launching Puppeteer screenshot capture", extra={"command": " ".join(cmd)})

    try:
        subprocess.run(cmd, check=True, cwd=script_path.parent)
    except (OSError, subprocess.CalledProcessError) as exc:
        logging.error("Puppeteer capture failed", extra={"error": str(exc)})


if __name__ == "__main__":
    main()