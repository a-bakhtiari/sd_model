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

    # Core optional features
    parser.add_argument(
        "--loops",
        action="store_true",
        help="Find feedback loops and generate loop descriptions"
    )
    parser.add_argument(
        "--citations",
        action="store_true",
        help="Generate and verify citations for connections/loops via Semantic Scholar"
    )

    # Model improvement features
    parser.add_argument(
        "--theory-enhancement",
        action="store_true",
        help="Suggest theory-based model enhancements and generate enhanced MDL file"
    )
    parser.add_argument(
        "--full-relayout",
        action="store_true",
        help="Use full relayout (reposition ALL variables) instead of incremental placement"
    )
    parser.add_argument(
        "--archetype-detection",
        action="store_true",
        help="Detect system archetypes and suggest missing loops/variables"
    )
    parser.add_argument(
        "--rq-analysis",
        action="store_true",
        help="Run research question alignment and refinement"
    )
    parser.add_argument(
        "--theory-discovery",
        action="store_true",
        help="Discover relevant theories for the model"
    )
    parser.add_argument(
        "--gap-analysis",
        action="store_true",
        help="Identify unsupported connections (requires --citations or enables it automatically)"
    )
    parser.add_argument(
        "--discover-papers",
        action="store_true",
        help="Find papers for unsupported connections (requires --gap-analysis or enables it automatically)"
    )

    # Convenience flags
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all optional features"
    )
    parser.add_argument(
        "--improve-model",
        action="store_true",
        help="Run all model improvement features (theory-enhancement, rq-analysis, theory-discovery)"
    )

    # Other options
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

    # Handle convenience flags
    if args.all:
        # Enable all optional features
        args.loops = True
        args.citations = True
        args.theory_enhancement = True
        args.archetype_detection = True
        args.rq_analysis = True
        args.theory_discovery = True
        args.gap_analysis = True
        args.discover_papers = True

    if args.improve_model:
        # Enable all model improvement features
        args.theory_enhancement = True
        args.archetype_detection = True
        args.rq_analysis = True
        args.theory_discovery = True

    # Handle dependencies - auto-enable required features
    if args.gap_analysis and not args.citations:
        args.citations = True

    if args.discover_papers and not args.gap_analysis:
        args.gap_analysis = True
        if not args.citations:
            args.citations = True

    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info(f"Starting SD Model Pipeline for project: {project}")

    try:
        result = run_pipeline(
            project=project,
            # Core optional features
            run_loops=args.loops,
            run_citations=args.citations,
            verify_cit=args.citations,  # In main.py, --citations does both generation and verification
            # Model improvement features
            run_theory_enhancement=args.theory_enhancement,
            use_full_relayout=args.full_relayout,
            run_archetype_detection=args.archetype_detection,
            run_rq_analysis=args.rq_analysis,
            run_theory_discovery=args.theory_discovery,
            run_gap_analysis=args.gap_analysis,
            discover_papers=args.discover_papers,
            # Other options
            apply_patch=args.apply_patch,
            save_run=args.save_run,
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("Pipeline output files:")
        logger.info("=" * 60)
        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
