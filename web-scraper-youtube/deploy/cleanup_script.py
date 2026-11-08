#!/usr/bin/env python3
"""Utility script to prune old run artifacts to conserve disk space."""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List


@dataclass(order=True)
class RunArtifact:
    updated_at: datetime
    path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="web-scraper-python/output",
        type=Path,
        help="Directory containing run artifact folders",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=5,
        help="Number of most recent run directories to keep (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without removing it",
    )
    return parser.parse_args()


def discover_runs(output_dir: Path) -> List[RunArtifact]:
    artifacts: List[RunArtifact] = []
    if not output_dir.exists():
        return artifacts
    for child in output_dir.iterdir():
        if not child.is_dir():
            continue
        updated_at = datetime.fromtimestamp(child.stat().st_mtime)
        artifacts.append(RunArtifact(updated_at, child))
    artifacts.sort(reverse=True)
    return artifacts


def prune_runs(artifacts: Iterable[RunArtifact], keep: int, dry_run: bool) -> None:
    for index, artifact in enumerate(artifacts):
        if index < keep:
            continue
        if dry_run:
            print(f"[dry-run] Would remove {artifact.path}")
        else:
            print(f"Removing {artifact.path}")
            shutil.rmtree(artifact.path, ignore_errors=True)


def main() -> None:
    args = parse_args()
    runs = discover_runs(args.output_dir)
    if len(runs) <= args.keep:
        print("Nothing to prune")
        return
    prune_runs(runs, args.keep, args.dry_run)


if __name__ == "__main__":
    main()
