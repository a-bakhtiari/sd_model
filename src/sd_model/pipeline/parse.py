from __future__ import annotations
import json
from pathlib import Path
from sd_model.llm.client import LLMClient
from sd_model.validation.schema import validate_json
from sd_model.provenance.store import init_db, add_artifact, record_connections
from sd_model.config import settings
import hashlib


PROMPT_TEMPLATE = """Extract all variable dependencies from this Vensim MDL file.

WHAT TO LOOK FOR:
Lines that follow this pattern:
VariableName = A FUNCTION OF(dep1, dep2, -dep3, dep4)

HOW TO PARSE:
1. The variable BEFORE the "=" is the TARGET (where the arrow points TO)
2. Variables inside "A FUNCTION OF(...)" are SOURCES (where arrows come FROM)
3. If a source starts with "-" it's a NEGATIVE relationship
4. If a source has no "-" it's a POSITIVE relationship

EXAMPLE:
If you see: Open Issues = A FUNCTION OF(Feedback, Issue Creation Rate, -Issue Resolution Rate)
You create THREE connections:
- Feedback → Open Issues (positive)
- Issue Creation Rate → Open Issues (positive)
- Issue Resolution Rate → Open Issues (negative)

OUTPUT RULES:
1. Return ONLY valid JSON, no explanations
2. For negative relationships: remove the "-" from the source name but mark relationship as "negative"
3. Ignore anything after the sketch section (after \\\---///)
4. Some definitions span multiple lines - include all dependencies until the closing ")"

JSON FORMAT:
{
  "connections": [
    {"from": "Source Variable Name", "to": "Target Variable Name", "relationship": "positive"},
    {"from": "Another Source", "to": "Another Target", "relationship": "negative"}
  ]
}

MDL FILE CONTENT:
{mdl_content}
"""


def parse_mdl(mdl_path: Path, out_path: Path, api_key: str | None = None, model: str | None = None,
              provenance_db: Path | None = None) -> dict:
    mdl_text = Path(mdl_path).read_text()
    # Avoid .format() due to braces in JSON example; do a simple token replace
    prompt = PROMPT_TEMPLATE.replace("{mdl_content}", mdl_text)

    client = LLMClient(api_key=api_key, model=model)
    content = client.chat(prompt, temperature=0.0)
    data = json.loads(content)
    # Validate against schema
    validate_json(data, Path("schemas/connections.schema.json"))

    out_path.write_text(json.dumps(data, indent=2))

    # Record provenance
    db_path = Path(provenance_db or settings.provenance_db)
    if db_path:
        init_db(db_path)
        sha = hashlib.sha256(out_path.read_bytes()).hexdigest()
        artifact_id = add_artifact(db_path, kind="connections", path=str(out_path), sha256=sha)
        record_connections(db_path, artifact_id, data.get("connections", []))
    return data
