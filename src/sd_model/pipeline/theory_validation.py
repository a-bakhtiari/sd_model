from __future__ import annotations
import csv
import json
from pathlib import Path
from statistics import mean
from sd_model.llm.client import LLMClient
from sd_model.validation.schema import validate_json
from sd_model.provenance.store import init_db, add_artifact, add_evidence
from sd_model.config import settings
from sd_model.paths import provenance_db_path
import hashlib


VALIDATE_PROMPT = """Analyze this system dynamics model against {theory_name}.

THEORY BACKGROUND:
{theory_description}

MODEL CONNECTIONS:
{connections_json}

KEY FEEDBACK LOOPS:
{loops_json}

ANALYSIS TASKS:
1. Which connections align well with this theory?
2. Which connections contradict or are unsupported by this theory?
3. What connections are MISSING that the theory would predict?
4. Rate the overall model alignment with this theory (1-10)

OUTPUT FORMAT (JSON):
{{
  "theory": "{theory_name}",
  "aligned_connections": [{{"connection": {{"from": "X", "to": "Y"}}, "explanation": "..."}}],
  "problematic_connections": [{{"connection": {{"from": "X", "to": "Y"}}, "issue": "..."}}],
  "missing_connections": [{{"suggested": {{"from": "X", "to": "Y", "relationship": "positive/negative"}}, "rationale": "..."}}],
  "alignment_score": 7,
  "recommendations": "Specific improvements based on this theory"
}}
"""


def load_theories_csv(path: Path) -> list[dict]:
    out = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out.append({
                "name": row.get("name", "").strip(),
                "description": row.get("description", "").strip(),
                "focus_area": row.get("focus_area", "").strip(),
                "citations": row.get("citations", "").strip(),
            })
    return out


def validate_with_theory(connections: list[dict], loops: list[dict], theory: dict, api_key: str | None, model: str) -> dict:
    prompt = VALIDATE_PROMPT.format(
        theory_name=theory["name"],
        theory_description=theory["description"],
        connections_json=json.dumps(connections[:20], indent=2),
        loops_json=json.dumps(loops[:5], indent=2),
    )
    client = LLMClient(api_key=api_key, model=model)
    content = client.chat(prompt, temperature=0.3)
    return json.loads(content)


def synthesize_validations(all_validations: list[dict]) -> dict:
    avg = mean(v["alignment_score"] for v in all_validations) if all_validations else 0.0
    all_missing = []
    all_problematic = []
    for v in all_validations:
        all_missing.extend(v.get("missing_connections", []))
        all_problematic.extend(v.get("problematic_connections", []))
    return {
        "theories_applied": len(all_validations),
        "average_alignment": avg,
        "consistent_issues": all_problematic[:3],
        "consistent_missing": all_missing[:3],
        "theory_validations": all_validations,
    }


def validate_model(connections_path: Path, loops_path: Path, theories_csv: Path, out_path: Path,
                   api_key: str | None = None, model: str | None = None,
                   provenance_db: Path | None = None) -> dict:
    connections = json.loads(connections_path.read_text())["connections"]
    loops_data = json.loads(loops_path.read_text())
    loops = loops_data.get("enhanced_loops", loops_data.get("loops", []))

    theories = load_theories_csv(theories_csv)

    all_validations: list[dict] = []
    for theory in theories:
        v = validate_with_theory(connections, loops, theory, api_key=api_key, model=model)
        all_validations.append(v)

    synthesis = synthesize_validations(all_validations)

    # Validate
    validate_json(synthesis, Path("schemas/theory_validation.schema.json"))

    out_path.write_text(json.dumps(synthesis, indent=2))

    # Provenance
    db_path = Path(provenance_db) if provenance_db else (Path(settings.provenance_db) if settings.provenance_db else provenance_db_path())
    if db_path:
        init_db(db_path)
        sha = hashlib.sha256(out_path.read_bytes()).hexdigest()
        artifact_id = add_artifact(db_path, kind="theory_validation", path=str(out_path), sha256=sha)
        avg = synthesis.get("average_alignment")
        add_evidence(db_path, item_type="artifact", item_id=artifact_id, source="theory_validation_llm",
                     ref=None, confidence=float(avg) / 10.0 if isinstance(avg, (int, float)) else None,
                     note="Average alignment from synthesis")
    return synthesis
