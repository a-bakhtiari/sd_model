from __future__ import annotations
import json
import networkx as nx


def load_connections(path: str | None = "connections.json"):
    with open(path, "r") as f:
        data = json.load(f)
    return data["connections"]


def build_signed_digraph(connections):
    G = nx.DiGraph()
    for c in connections:
        G.add_edge(c["from"], c["to"], relationship=c.get("relationship", "positive"))
    return G

