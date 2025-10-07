from __future__ import annotations

import json
from pathlib import Path
from typing import List

from flask import Flask, jsonify, render_template, send_from_directory

from .config import load_config
from .paths import for_project
from .orchestrator import run_pipeline


def create_app() -> Flask:
    cfg = load_config()
    templates_path = Path(__file__).parent / "templates"
    app = Flask(
        __name__, template_folder=str(templates_path), static_folder=str(templates_path)
    )

    @app.route("/")
    def index():
        # Light UI shell; the template fetches project list via JS call
        return render_template("index.html")

    @app.route("/projects")
    def list_projects():
        projects: List[str] = []
        if cfg.projects_dir.exists():
            for p in sorted(cfg.projects_dir.iterdir()):
                if p.is_dir():
                    projects.append(p.name)
        return jsonify({"projects": projects})

    @app.route("/run-pipeline/<project>")
    def run_pipeline_route(project: str):
        try:
            result = run_pipeline(project=project, apply_patch=False)
            return jsonify({"status": "ok", "artifacts": result})
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500

    @app.route("/artifacts/<project>")
    def artifacts_list(project: str):
        paths = for_project(cfg, project)
        if not paths.artifacts_dir.exists():
            return jsonify({"files": []})
        files = [p.name for p in sorted(paths.artifacts_dir.glob("*.json"))]
        return jsonify({"files": files})

    @app.route("/artifacts/<project>/<filename>")
    def get_artifact(project: str, filename: str):
        paths = for_project(cfg, project)
        return send_from_directory(paths.artifacts_dir, filename)

    return app


def run(host: str = "127.0.0.1", port: int = 5000, debug: bool = True) -> None:
    app = create_app()
    app.run(host=host, port=port, debug=debug)
