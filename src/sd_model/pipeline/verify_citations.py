from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Set

from ..knowledge.loader import load_bibliography


def _iter_citation_keys(obj) -> Iterable[str]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "citation_key" and isinstance(v, str):
                yield v
            else:
                yield from _iter_citation_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_citation_keys(v)


def verify_citations(artifact_paths: List[Path], bib_path: Path) -> Dict:
    """Verify that all `citation_key` values in the given artifacts exist in the bibliography.

    Raises a ValueError if any citation_key is missing to enforce verifiability.
    """
    bib = load_bibliography(bib_path)
    found: Set[str] = set()
    missing: Set[str] = set()

    for p in artifact_paths:
        if not p.exists():
            # Skip silently to allow flexible pipelines
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        for key in _iter_citation_keys(data):
            if key in bib:
                found.add(key)
            else:
                missing.add(key)

    report = {"found": sorted(found), "missing": sorted(missing)}
    if missing:
        # Halt pipeline with a clear error
        raise ValueError(
            f"Missing citation keys not found in bibliography: {sorted(missing)}"
        )
    return report

