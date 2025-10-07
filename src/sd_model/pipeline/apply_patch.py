from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Dict, List


def apply_model_patch(mdl_path: Path, improvements_path: Path, out_copy_path: Path) -> Path:
    """Create a copy of the original .mdl and append new variables and connections.

    We use a conservative, append-only approach compatible with many Vensim-style
    models. Each new variable is added with a minimal equation. Connections are
    appended as comment annotations to avoid breaking existing structure.
    """
    text = mdl_path.read_text(encoding="utf-8", errors="ignore")
    data = json.loads(improvements_path.read_text(encoding="utf-8"))

    lines: List[str] = []
    lines.append("\n\\\\\\\\ SIMPLIFIED_PATCH_START")
    lines.append(
        f"\\ Patch applied: {datetime.utcnow().isoformat()}Z from {improvements_path.name}"
    )

    for op in data.get("improvements", []):
        kind = op.get("operation")
        if kind == "add_variable":
            name = op.get("name", "New_Variable")
            eq = op.get("equation", "0")
            comment = op.get("comment", "")
            # Vensim-like: Variable = Equation ~ Units ~| Comment
            lines.append(f"{name} = {eq} ~ dimensionless ~| {comment}")
        elif kind == "add_connection":
            src = op.get("from", "")
            dst = op.get("to", "")
            rel = op.get("relationship", "unknown")
            comment = op.get("comment", "")
            # Represent connections as comments to avoid graph section fiddling
            lines.append(f"\\ link: {src} -> {dst} ({rel}) | {comment}")
        else:
            lines.append(f"\\ unsupported operation: {json.dumps(op)}")

    lines.append("\\\\\\\\ SIMPLIFIED_PATCH_END\n")

    out_copy_path.write_text(text + "\n" + "\n".join(lines), encoding="utf-8")
    return out_copy_path

