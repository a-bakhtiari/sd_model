from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import List

from .config import load_config
from .knowledge.loader import load_bibliography, load_feedback, load_theories
from .paths import for_project
from .server import run as run_server
from .orchestrator import run_pipeline
import os
import sys
import subprocess


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with a clean format for terminal output."""
    level = logging.DEBUG if verbose else logging.INFO

    # Create formatter with timestamp and level
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Configure root logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Set up the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = []  # Clear any existing handlers
    root_logger.addHandler(handler)


def cmd_run(args: argparse.Namespace) -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    # Handle convenience flags
    if args.all:
        args.loops = True
        args.citations = True
        args.verify_citations = True
        args.theory_enhancement = True
        args.archetype_detection = True
        args.rq_analysis = True
        args.theory_discovery = True

    if args.improve_model:
        args.theory_enhancement = True
        args.archetype_detection = True
        args.rq_analysis = True
        args.theory_discovery = True

    # Handle dependencies
    # Citations always auto-enable verification (no point in unverified citations)
    if args.citations:
        args.verify_citations = True

    if args.verify_citations and not args.citations:
        args.citations = True

    # Validate --step requires --decomposed-theory
    if hasattr(args, 'step') and args.step and not args.decomposed_theory:
        logger.error("--step requires --decomposed-theory flag")
        return

    # Auto-enable theory enhancement when using decomposed-theory
    if args.decomposed_theory:
        args.theory_enhancement = True

    result = run_pipeline(
        project=args.project,
        # Core optional features
        run_loops=args.loops,
        run_citations=args.citations,
        verify_cit=args.verify_citations,
        # Model improvement features
        run_theory_enhancement=args.theory_enhancement,
        use_full_relayout=args.full_relayout,
        recreate_from_theory=args.recreate_model if hasattr(args, 'recreate_model') else False,
        use_decomposed_theory=args.decomposed_theory if hasattr(args, 'decomposed_theory') else False,
        theory_step=args.step if hasattr(args, 'step') else None,
        resume_run=args.resume_run if hasattr(args, 'resume_run') else None,
        run_archetype_detection=args.archetype_detection,
        run_rq_analysis=args.rq_analysis,
        run_theory_discovery=args.theory_discovery,
        # Other options
        apply_patch=args.apply_patch,
        save_run=args.save_run,
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("Pipeline output files:")
    logger.info("=" * 60)
    print(json.dumps(result, indent=2))


def cmd_knowledge_validate(args: argparse.Namespace) -> None:
    cfg = load_config()
    paths = for_project(cfg, args.project)
    errs: List[str] = []

    # Theories
    try:
        _ = load_theories(paths.theories_dir)
    except Exception as e:
        errs.append(f"Theories error: {e}")

    # Bibliography
    try:
        _ = load_bibliography(paths.references_bib_path)
    except Exception as e:
        errs.append(f"Bibliography error: {e}")

    # Feedback (optional)
    try:
        _ = load_feedback(paths.feedback_json_path)
    except Exception as e:
        errs.append(f"Feedback error: {e}")

    if errs:
        print("Knowledge validation failed:")
        for e in errs:
            print(" -", e)
    else:
        print("Knowledge validation OK.")


def cmd_ui(args: argparse.Namespace) -> None:
    framework = args.framework
    if framework == "streamlit":
        # Launch Streamlit app via module to respect the current interpreter/venv
        app_path = Path(__file__).parent / "ui_streamlit.py"
        port = os.getenv("SD_UI_PORT", "8501")
        cmd = [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(port)]
        subprocess.run(cmd, check=True)
    else:
        run_server()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sd", description="SD Model CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    # sd run
    p_run = sub.add_parser("run", help="Run the analysis pipeline")
    p_run.add_argument("--project", required=True, help="Project name under projects/")

    # Core optional features
    p_run.add_argument("--loops", action="store_true", help="Find feedback loops and generate loop descriptions")
    p_run.add_argument("--citations", action="store_true", help="Generate LLM-based citations for connections/loops")
    p_run.add_argument("--verify-citations", action="store_true", help="Verify citations via Semantic Scholar")

    # Model improvement features
    p_run.add_argument("--theory-enhancement", action="store_true", help="Suggest theory-based model enhancements and generate enhanced MDL file")
    p_run.add_argument("--full-relayout", action="store_true", help="Use full relayout (reposition ALL variables) instead of incremental placement")
    p_run.add_argument("--recreate-model", action="store_true", help="Recreate model from scratch using ONLY theory-generated variables (discards existing model)")
    p_run.add_argument("--decomposed-theory", action="store_true", help="Use decomposed 3-step theory enhancement (strategic planning → concrete generation → positioning)")
    p_run.add_argument("--step", type=int, choices=[1, 2], help="Run specific step only (1=planning, 2=concretization). Requires --decomposed-theory. Default: run both steps")
    p_run.add_argument("--resume-run", type=str, metavar="RUN_ID", help="Resume from existing run_id (for Step 2). Auto-detects latest Step 1 if not specified")
    p_run.add_argument("--archetype-detection", action="store_true", help="Detect system archetypes and suggest missing loops/variables")
    p_run.add_argument("--rq-analysis", action="store_true", help="Run research question alignment and refinement")
    p_run.add_argument("--theory-discovery", action="store_true", help="Discover relevant theories for the model")

    # Convenience flags
    p_run.add_argument("--all", action="store_true", help="Run all optional features")
    p_run.add_argument("--improve-model", action="store_true", help="Run all model improvement features")

    # Other options
    p_run.add_argument("--apply-patch", action="store_true", help="Automatically apply patch to .mdl")
    p_run.add_argument("--save-run", nargs="?", const="", metavar="NAME",
        help="Save artifacts to timestamped folder (optionally with custom name)")

    p_run.set_defaults(func=cmd_run)

    # sd knowledge validate
    p_kv = sub.add_parser("knowledge", help="Knowledge base operations")
    sub_kv = p_kv.add_subparsers(dest="kcmd", required=True)
    p_kv_val = sub_kv.add_parser("validate", help="Validate theories/bib/feedback files")
    p_kv_val.add_argument("--project", required=True)
    p_kv_val.set_defaults(func=cmd_knowledge_validate)

    # sd ui
    p_ui = sub.add_parser("ui", help="Launch a web UI (Flask or Streamlit)")
    p_ui.add_argument("--framework", choices=["flask", "streamlit"], default="flask")
    p_ui.set_defaults(func=cmd_ui)

    return p


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
