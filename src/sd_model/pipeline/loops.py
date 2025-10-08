from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

import networkx as nx

LoopEdge = Tuple[str, str, str]


def _canonical_cycle(nodes: Sequence[str]) -> Tuple[str, ...]:
    """Rotate a cycle so comparisons are consistent across enumerations."""
    if not nodes:
        return tuple()
    min_index = min(range(len(nodes)), key=lambda idx: nodes[idx].lower())
    return tuple(nodes[(min_index + i) % len(nodes)] for i in range(len(nodes)))


def _describe_cycle(nodes: Sequence[str]) -> str:
    if not nodes:
        return ""
    ordered = list(nodes) + [nodes[0]]
    return " → ".join(ordered)


def _load_edges(connections: Optional[Dict]) -> List[LoopEdge]:
    edges: List[LoopEdge] = []
    if not isinstance(connections, dict):
        return edges
    for conn in connections.get("connections", []):
        src = str(conn.get("from_var", "")).strip()
        dst = str(conn.get("to_var", "")).strip()
        rel = str(conn.get("relationship", "") or "").strip().lower()
        if not src or not dst:
            continue
        if rel not in {"positive", "negative"}:
            rel = "unknown"
        edges.append((src, dst, rel))
    return edges


def compute_loops(
    parsed: Dict,
    out_path: Path,
    connections: Optional[Dict] = None,
    *,
    max_loops: int = 25,
    max_length: int = 8,
) -> Dict:
    """Detect balancing and reinforcing feedback loops from signed connections."""
    loops: Dict[str, List[Dict]] = {
        "balancing": [],
        "reinforcing": [],
        "undetermined": [],
        "notes": [],
    }

    edges = _load_edges(connections)
    if not edges:
        # Preserve the artifact contract, but explain why detection was skipped.
        if parsed.get("variables"):
            loops["notes"].append("No connection data supplied; loop detection skipped.")
        else:
            loops["notes"].append("Model contains no variables; loop detection skipped.")
        out_path.write_text(json.dumps(loops, indent=2), encoding="utf-8")
        return loops

    graph = nx.DiGraph()
    for src, dst, rel in edges:
        graph.add_edge(src, dst, relationship=rel)

    seen: Set[Tuple[str, ...]] = set()
    loop_counter = 0

    for cycle in nx.simple_cycles(graph):
        if len(cycle) < 2:
            continue
        if len(cycle) > max_length:
            loops["notes"].append(
                f"Skipped loop {_describe_cycle(cycle)} (>{max_length} variables)."
            )
            continue

        canonical = _canonical_cycle(cycle)
        if canonical in seen:
            continue
        seen.add(canonical)

        cycle_edges = []
        negative_edges = 0
        has_unknown = False
        for idx, src in enumerate(canonical):
            dst = canonical[(idx + 1) % len(canonical)]
            rel = graph[src][dst].get("relationship", "unknown")
            if rel == "negative":
                negative_edges += 1
            elif rel != "positive":
                has_unknown = True
            cycle_edges.append(
                {
                    "from_var": src,
                    "to_var": dst,
                    "relationship": rel,
                }
            )

        if has_unknown:
            bucket = "undetermined"
        else:
            bucket = "reinforcing" if negative_edges % 2 == 0 else "balancing"

        loop_counter += 1
        loop_id = f"L{loop_counter:02d}"
        loops[bucket].append(
            {
                "id": loop_id,
                "variables": list(canonical),
                "edges": cycle_edges,
                "length": len(canonical),
                "negative_edges": negative_edges,
                "polarity": bucket,
                "description": _describe_cycle(canonical),
            }
        )

        if loop_counter >= max_loops:
            loops["notes"].append(f"Truncated loop detection after {max_loops} loops.")
            break

    out_path.write_text(json.dumps(loops, indent=2), encoding="utf-8")
    return loops
