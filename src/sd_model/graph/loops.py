import networkx as nx


def simple_cycles_with_polarity(G: nx.DiGraph):
    cycles = list(nx.simple_cycles(G))
    results = []
    for cycle in cycles:
        neg = 0
        edges = []
        for i in range(len(cycle)):
            s = cycle[i]
            t = cycle[(i + 1) % len(cycle)]
            rel = G.edges[s, t].get("relationship", "positive")
            if rel == "negative":
                neg += 1
            edges.append({"from": s, "to": t, "relationship": rel})
        results.append({
            "nodes": cycle,
            "edges": edges,
            "negative_edges": neg,
            "type": "R" if neg % 2 == 0 else "B",
            "length": len(cycle),
        })
    return results

