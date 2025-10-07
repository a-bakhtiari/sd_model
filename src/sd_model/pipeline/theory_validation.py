from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

from ..knowledge.loader import load_bibliography, load_theories
from ..knowledge.types import Theory


@dataclass
class Edge:
    src: str
    dst: str
    rel: str


def _as_edges(connections_json: Dict) -> Set[Tuple[str, str, str]]:
    edges = set()
    for c in connections_json.get("connections", []):
        edges.add((c.get("from_var", ""), c.get("to_var", ""), c.get("relationship", "unknown")))
    return edges


def _theory_edges(theory: Theory) -> Set[Tuple[str, str, str]]:
    return set(
        (e.from_var, e.to_var, e.relationship) for e in theory.expected_connections
    )


def validate_against_theories(
    connections_path: Path,
    theories_dir: Path,
    bib_path: Path,
    out_path: Path,
) -> Dict:
    """Analyze model connections against structured theories.

    The output contains where the model confirms theory, contradicts, or misses
    expected links, and lists novel links present in the model not covered by any
    theory. Attempts to include citation_key where applicable.
    """
    connections_json = json.loads(connections_path.read_text(encoding="utf-8"))
    model_edges = _as_edges(connections_json)
    theories = load_theories(theories_dir)
    bibliography = {}
    try:
        bibliography = load_bibliography(bib_path)
    except Exception:
        # Bibliography may be missing during early iterations; proceed with empty.
        bibliography = {}

    confirmed = []
    contradicted = []
    missing = []
    novel = []

    # For each theory, compute matches and gaps
    theory_all_edges = set()
    for th in theories:
        t_edges = _theory_edges(th)
        theory_all_edges |= t_edges
        model_pairs = {(s, d) for (s, d, r) in model_edges}
        for (s, d, rel) in t_edges:
            if (s, d) in model_pairs:
                confirmed.append(
                    {
                        "from_var": s,
                        "to_var": d,
                        "relationship": rel,
                        "theory": th.theory_name,
                        "citation_key": th.citation_key,
                    }
                )
            else:
                missing.append(
                    {
                        "from_var": s,
                        "to_var": d,
                        "relationship": rel,
                        "theory": th.theory_name,
                        "citation_key": th.citation_key,
                    }
                )

    # Contradicted: same variables with different relationship
    model_pairs = {(s, d) for (s, d, r) in model_edges}
    theory_pairs = {(s, d) for (s, d, r) in theory_all_edges}
    shared_pairs = model_pairs & theory_pairs
    for s, d in sorted(shared_pairs):
        # Treat 'unknown' as neutral (neither confirming nor contradicting)
        model_rels = {r for (ss, dd, r) in model_edges if ss == s and dd == d and r != "unknown"}
        theory_rels = {r for (ss, dd, r) in theory_all_edges if ss == s and dd == d}
        if model_rels and theory_rels and model_rels.isdisjoint(theory_rels):
            contradicted.append(
                {
                    "from_var": s,
                    "to_var": d,
                    "model_relationships": sorted(model_rels),
                    "theory_relationships": sorted(theory_rels),
                    "citation_key": None,
                }
            )

    # Novel: model edges not predicted by any theory
    for s, d, r in sorted(model_edges - theory_all_edges):
        novel.append({"from_var": s, "to_var": d, "relationship": r, "citation_key": None})

    summary = {
        "theory_count": len(theories),
        "model_edge_count": len(model_edges),
        "confirmed_count": len(confirmed),
        "contradicted_count": len(contradicted),
        "missing_count": len(missing),
        "novel_count": len(novel),
    }

    result = {
        "summary": summary,
        "confirmed": confirmed,
        "contradicted": contradicted,
        "missing": missing,
        "novel": novel,
        "bibliography_loaded": bool(bibliography),
    }
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
