from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from .llm_loop_classification import discover_loops_with_llm
from ..llm.client import LLMClient


def compute_loops(
    parsed: Dict,
    out_path: Path,
    connections: Optional[Dict] = None,
    variables_data: Optional[Dict] = None,
    llm_client: Optional[LLMClient] = None,
    *,
    max_loops: int = 25,
    max_length: int = 8,
) -> Dict:
    """Discover balancing and reinforcing feedback loops using LLM."""

    # Default structure
    loops: Dict = {
        "balancing": [],
        "reinforcing": [],
        "notes": [],
    }

    # Check if we have the data we need
    if not connections:
        loops["notes"].append("No connection data supplied; loop discovery skipped.")
        out_path.write_text(json.dumps(loops, indent=2), encoding="utf-8")
        return loops

    if not llm_client:
        loops["notes"].append("No LLM client provided; loop discovery skipped.")
        out_path.write_text(json.dumps(loops, indent=2), encoding="utf-8")
        return loops

    if not variables_data:
        loops["notes"].append("No variable data provided; loop discovery skipped.")
        out_path.write_text(json.dumps(loops, indent=2), encoding="utf-8")
        return loops

    # Use LLM to discover loops by their behavioral characteristics
    try:
        loops = discover_loops_with_llm(
            connections_data=connections,
            variables_data=variables_data,
            llm_client=llm_client
        )
    except Exception as e:
        loops["notes"].append(f"LLM loop discovery failed: {str(e)}")

    # Write results to file
    out_path.write_text(json.dumps(loops, indent=2), encoding="utf-8")
    return loops
