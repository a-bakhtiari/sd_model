from __future__ import annotations
import json
from pathlib import Path
from sd_model.llm.client import LLMClient


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


def parse_mdl(mdl_path: Path, out_path: Path, api_key: str | None = None, model: str = "deepseek-chat") -> dict:
    mdl_text = Path(mdl_path).read_text()
    prompt = PROMPT_TEMPLATE.format(mdl_content=mdl_text)

    client = LLMClient(api_key=api_key, model=model)
    content = client.chat(prompt, temperature=0.0)
    data = json.loads(content)

    out_path.write_text(json.dumps(data, indent=2))
    return data

