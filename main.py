from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from src.sd_model.orchestrator import run_pipeline as run_pipeline_impl


# Expose the orchestrator's function under the same name for compatibility
run_pipeline = run_pipeline_impl


if __name__ == "__main__":
    # Allow quick manual run for a project set via env var for convenience
    import os
    project = os.getenv("SD_PROJECT")
    if not project:
        raise SystemExit("Set SD_PROJECT env var or use CLI via src/sd_model/cli.py")
    print(json.dumps(run_pipeline(project), indent=2))
