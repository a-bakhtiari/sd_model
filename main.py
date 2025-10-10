#!/usr/bin/env python3
"""Main entry point for SD Model pipeline - simplified interface."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from src.sd_model.orchestrator import run_pipeline


def setup_logging() -> None:
    """Configure logging for console output."""
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = []
    root_logger.addHandler(handler)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="SD Model Analysis Pipeline - Simplified Interface",
        epilog="Example: python main.py --project oss_model --save-run baseline"
    )

    parser.add_argument(
        "--project",
        required=False,
        help="Project name under projects/ (can also use SD_PROJECT env var)"
    )
    parser.add_argument(
        "--improve-model",
        action="store_true",
        default=True,
        help="Run model improvement modules (theory enhancement, RQ alignment, etc.) [default: enabled]"
    )
    parser.add_argument(
        "--no-improve-model",
        dest="improve_model",
        action="store_false",
        help="Skip model improvement modules"
    )
    parser.add_argument(
        "--verify-citations",
        action="store_true",
        help="Verify citations via Semantic Scholar"
    )
    parser.add_argument(
        "--discover-papers",
        action="store_true",
        help="Search for papers for unsupported connections"
    )
    parser.add_argument(
        "--apply-patch",
        action="store_true",
        help="Automatically apply patch to .mdl file"
    )
    parser.add_argument(
        "--save-run",
        nargs="?",
        const="",
        metavar="NAME",
        help="Save artifacts to timestamped folder (optionally with custom name)"
    )

    args = parser.parse_args()

    # Get project from args or env var
    project = args.project or os.getenv("SD_PROJECT")
    if not project:
        parser.error("--project required (or set SD_PROJECT environment variable)")

    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info(f"Starting SD Model Pipeline for project: {project}")

    try:
        result = run_pipeline(
            project=project,
            apply_patch=args.apply_patch,
            verify_cit=args.verify_citations,
            discover_papers=args.discover_papers,
            improve_model=args.improve_model,
            save_run=args.save_run,
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("Pipeline output files:")
        logger.info("=" * 60)
        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
