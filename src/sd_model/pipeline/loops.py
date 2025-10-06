from __future__ import annotations
import json
from pathlib import Path
import networkx as nx
from sd_model.graph.builder import build_signed_digraph
from sd_model.graph.loops import simple_cycles_with_polarity
from sd_model.validation.schema import validate_json
from sd_model.provenance.store import init_db, add_artifact, record_loops
import hashlib


def compute_loops(connections_path: Path, out_path: Path, provenance_db: Path | None = Path("provenance.sqlite")) -> dict:
    with open(connections_path, "r") as f:
        connections = json.load(f)["connections"]

    G: nx.DiGraph = build_signed_digraph(connections)
    cycles = simple_cycles_with_polarity(G)

    output = {
        "total_loops": len(cycles),
        "loops": cycles,
        "summary": {
            "reinforcing_loops": sum(1 for l in cycles if l["type"] == "R"),
            "balancing_loops": sum(1 for l in cycles if l["type"] == "B"),
            "shortest_loop": min((l["length"] for l in cycles), default=0),
            "longest_loop": max((l["length"] for l in cycles), default=0),
        },
    }

    # Validate against schema
    validate_json(output, Path("schemas/loops.schema.json"))

    out_path.write_text(json.dumps(output, indent=2))

    # Record provenance
    if provenance_db:
        init_db(provenance_db)
        sha = hashlib.sha256(out_path.read_bytes()).hexdigest()
        artifact_id = add_artifact(provenance_db, kind="loops", path=str(out_path), sha256=sha)
        record_loops(provenance_db, artifact_id, output.get("loops", []))
    return output
