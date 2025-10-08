from __future__ import annotations

import argparse
import json
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


def cmd_run(args: argparse.Namespace) -> None:
    result = run_pipeline(
        project=args.project,
        apply_patch=args.apply_patch,
        verify_cit=args.verify_citations,
        discover_papers=args.discover_papers,
    )
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
    p_run.add_argument(
        "--apply-patch", action="store_true", help="Automatically apply patch to .mdl"
    )
    p_run.add_argument(
        "--verify-citations", action="store_true", help="Verify citations via Semantic Scholar"
    )
    p_run.add_argument(
        "--discover-papers", action="store_true", help="Search for papers for unsupported connections"
    )
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
