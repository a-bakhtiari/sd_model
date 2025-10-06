from __future__ import annotations
import json
from pathlib import Path
from sd_model.llm.client import LLMClient
from sd_model.validation.schema import validate_json
from sd_model.provenance.store import init_db, add_artifact, add_evidence
from sd_model.config import settings
import hashlib


INTERPRET_PROMPT = """Analyze these feedback loops from an open-source software community system dynamics model.

CONTEXT: This model represents dynamics of open-source projects including contributors, knowledge transfer, reputation, and development processes.

LOOPS DATA:
{loops_json}

TASK: For each loop, provide:
1. A descriptive name (e.g., "Reputation-Growth Loop")
2. What this loop means in real-world terms
3. Whether it helps or hinders project sustainability
4. Which loop is likely most influential in system behavior

OUTPUT FORMAT (JSON):
{
  "interpreted_loops": [
    {
      "loop_nodes": ["list", "of", "nodes"],
      "name": "Descriptive Loop Name",
      "type": "R or B",
      "meaning": "What happens in this loop in real-world terms",
      "impact": "positive/negative/mixed for project sustainability",
      "explanation": "Why this loop matters"
    }
  ],
  "dominant_loops": ["Names of 3 most influential loops"],
  "system_insights": "Overall pattern these loops reveal about the system"
}

Focus on practical implications for open-source project management.
"""


def combine_analysis(loops_data: dict, interpretations: dict) -> dict:
    enhanced_loops = []
    for loop in loops_data.get("loops", []):
        for interp in interpretations.get("interpreted_loops", []):
            if set(loop["nodes"]) == set(interp.get("loop_nodes", [])):
                enhanced = {
                    **loop,
                    "name": interp.get("name"),
                    "meaning": interp.get("meaning"),
                    "impact": interp.get("impact"),
                    "explanation": interp.get("explanation"),
                }
                enhanced_loops.append(enhanced)
                break
    return {
        "total_loops": loops_data.get("total_loops", 0),
        "summary": loops_data.get("summary", {}),
        "enhanced_loops": enhanced_loops,
        "dominant_loops": interpretations.get("dominant_loops", []),
        "system_insights": interpretations.get("system_insights", ""),
    }


def interpret_loops(loops_path: Path, out_path: Path, api_key: str | None = None, model: str | None = None,
                    provenance_db: Path | None = None) -> dict:
    loops_data = json.loads(Path(loops_path).read_text())
    # Avoid .format() because template contains many braces; simple token replace
    prompt = INTERPRET_PROMPT.replace("{loops_json}", json.dumps(loops_data.get("loops", []), indent=2))

    client = LLMClient(api_key=api_key, model=model)
    content = client.chat(prompt, temperature=0.3)
    interpretations = json.loads(content)

    final = combine_analysis(loops_data, interpretations)

    # Validate
    validate_json(final, Path("schemas/loops_interpreted.schema.json"))

    out_path.write_text(json.dumps(final, indent=2))

    # Provenance
    db_path = Path(provenance_db or settings.provenance_db)
    if db_path:
        init_db(db_path)
        sha = hashlib.sha256(out_path.read_bytes()).hexdigest()
        artifact_id = add_artifact(db_path, kind="loops_interpreted", path=str(out_path), sha256=sha)
        si = final.get("system_insights", "")
        if si:
            add_evidence(db_path, item_type="artifact", item_id=artifact_id,
                         source="interpret_llm", ref=None, confidence=None, note=si)
    return final
