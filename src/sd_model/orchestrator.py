from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from .config import load_config
from .paths import first_mdl_file, for_project
from .pipeline.loops import compute_loops
from .pipeline.theory_validation import validate_against_theories
from .pipeline.verify_citations import verify_citations
from .pipeline.improve import propose_improvements
from .pipeline.apply_patch import apply_model_patch
from .llm.client import LLMClient
from .pipeline.llm_extraction import infer_variable_types, infer_connections
from .provenance.store import log_event
from .validation.schema import validate_json_schema


def run_pipeline(project: str, apply_patch: bool = False) -> Dict:
    """Run the full analysis pipeline for a project."""
    cfg = load_config()
    paths = for_project(cfg, project)
    paths.ensure()

    mdl_path = first_mdl_file(paths)
    if mdl_path is None:
        raise FileNotFoundError(f"No .mdl file found in {paths.mdl_dir}")

    client = LLMClient()

    variables_data = infer_variable_types(mdl_path, client)
    connections_data = infer_connections(mdl_path, variables_data, client)

    variables_path = paths.artifacts_dir / "variables_llm.json"
    connections_llm_path = paths.artifacts_dir / "connections_llm.json"
    variables_path.write_text(json.dumps(variables_data, indent=2), encoding="utf-8")
    connections_llm_path.write_text(json.dumps(connections_data, indent=2), encoding="utf-8")

    # Build compatibility artifacts
    id_to_name = {int(v["id"]): v["name"] for v in variables_data.get("variables", [])}
    parsed = {
        "variables": [v["name"] for v in variables_data.get("variables", [])],
        "equations": {},
    }
    paths.parsed_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")

    connections_named = []
    for edge in connections_data.get("connections", []):
        from_name = id_to_name.get(int(edge.get("from", -1)))
        to_name = id_to_name.get(int(edge.get("to", -1)))
        if not from_name or not to_name:
            continue
        polarity = str(edge.get("polarity", "UNDECLARED")).upper()
        if polarity == "POSITIVE":
            relationship = "positive"
        elif polarity == "NEGATIVE":
            relationship = "negative"
        else:
            relationship = "unknown"
        connections_named.append(
            {
                "from_var": from_name,
                "to_var": to_name,
                "relationship": relationship,
            }
        )

    paths.connections_path.write_text(json.dumps({"connections": connections_named}, indent=2), encoding="utf-8")

    log_event(paths.db_dir / "provenance.sqlite", "parsed", {"variables": len(parsed["variables"])})

    loops = compute_loops(parsed, paths.loops_path)
    log_event(paths.db_dir / "provenance.sqlite", "loops", {})

    tv = validate_against_theories(
        connections_path=paths.connections_path,
        theories_dir=paths.theories_dir,
        bib_path=paths.references_bib_path,
        out_path=paths.theory_validation_path,
    )
    # Validate JSON against schema when available
    try:
        validate_json_schema(tv, load_config().schemas_dir / "theory_validation.schema.json")
    except Exception:
        # Non-fatal; surface during CLI runs if needed
        pass
    log_event(paths.db_dir / "provenance.sqlite", "theory_validation", tv.get("summary", {}))

    try:
        _ = verify_citations(
            [paths.theory_validation_path, paths.model_improvements_path],
            bib_path=paths.references_bib_path,
        )
    except Exception:
        pass

    improvements = propose_improvements(
        theory_validation_path=paths.theory_validation_path,
        feedback_path=paths.feedback_json_path,
        out_path=paths.model_improvements_path,
    )
    try:
        validate_json_schema(
            improvements, load_config().schemas_dir / "model_improvements.schema.json"
        )
    except Exception:
        pass
    log_event(paths.db_dir / "provenance.sqlite", "improve", {"count": len(improvements.get("improvements", []))})

    try:
        _ = verify_citations(
            [paths.theory_validation_path, paths.model_improvements_path],
            bib_path=paths.references_bib_path,
        )
    except Exception:
        pass

    patched_file = None
    if apply_patch:
        out_copy_path = paths.artifacts_dir / f"{mdl_path.stem}_patched.mdl"
        patched_file = apply_model_patch(mdl_path, paths.model_improvements_path, out_copy_path)
        log_event(paths.db_dir / "provenance.sqlite", "apply_patch", {"output": str(patched_file)})

    return {
        "parsed": str(paths.parsed_path),
        "loops": str(paths.loops_path),
        "connections": str(paths.connections_path),
        "variables_llm": str(variables_path),
        "connections_llm": str(connections_llm_path),
        "theory_validation": str(paths.theory_validation_path),
        "improvements": str(paths.model_improvements_path),
        "patched": str(patched_file) if patched_file else None,
    }
