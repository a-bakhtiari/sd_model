"""
Step 2: Find loops in the system dynamics model using networkx
"""

import json
import networkx as nx

def load_connections(filepath='connections.json'):
    """Load connections from JSON file"""
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data['connections']

def build_graph(connections):
    """Build directed graph from connections"""
    G = nx.DiGraph()
    
    for conn in connections:
        # Add edge with relationship type as attribute
        G.add_edge(conn['from'], conn['to'], 
                   relationship=conn['relationship'])
    
    return G

def find_all_loops(G):
    """Find all cycles in the graph"""
    cycles = list(nx.simple_cycles(G))
    return cycles

def analyze_loop(G, cycle):
    """Analyze a single loop - count positive and negative edges"""
    edges = []
    negative_count = 0
    
    for i in range(len(cycle)):
        source = cycle[i]
        target = cycle[(i + 1) % len(cycle)]
        
        edge_data = G.edges[source, target]
        edges.append({
            'from': source,
            'to': target,
            'relationship': edge_data['relationship']
        })
        
        if edge_data['relationship'] == 'negative':
            negative_count += 1
    
    # Determine loop polarity
    # Even number of negative edges = Reinforcing (R)
    # Odd number of negative edges = Balancing (B)
    loop_type = 'R' if negative_count % 2 == 0 else 'B'
    
    return {
        'nodes': cycle,
        'edges': edges,
        'negative_edges': negative_count,
        'type': loop_type,
        'length': len(cycle)
    }

def main():
    # Load connections
    connections = load_connections('connections.json')
    
    # Build graph
    G = build_graph(connections)
    print(f"Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    
    # Find all loops
    cycles = find_all_loops(G)
    print(f"\nFound {len(cycles)} loops in the model")
    
    # Analyze each loop
    loops_data = []
    for cycle in cycles:
        loop_info = analyze_loop(G, cycle)
        loops_data.append(loop_info)
    
    # Sort by length for easier viewing
    loops_data.sort(key=lambda x: x['length'])
    
    # Save all loops
    output = {
        'total_loops': len(loops_data),
        'loops': loops_data,
        'summary': {
            'reinforcing_loops': sum(1 for l in loops_data if l['type'] == 'R'),
            'balancing_loops': sum(1 for l in loops_data if l['type'] == 'B'),
            'shortest_loop': min(l['length'] for l in loops_data) if loops_data else 0,
            'longest_loop': max(l['length'] for l in loops_data) if loops_data else 0
        }
    }
    
    with open('loops.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    # Print summary
    print(f"\n📊 Loop Summary:")
    print(f"- Reinforcing (R) loops: {output['summary']['reinforcing_loops']}")
    print(f"- Balancing (B) loops: {output['summary']['balancing_loops']}")
    print(f"- Shortest loop: {output['summary']['shortest_loop']} nodes")
    print(f"- Longest loop: {output['summary']['longest_loop']} nodes")
    
    # Show a few examples
    print(f"\n🔄 Example loops:")
    for i, loop in enumerate(loops_data[:3]):
        print(f"\nLoop {i+1} ({loop['type']}, {loop['length']} nodes):")
        path = " → ".join(loop['nodes']) + f" → {loop['nodes'][0]}"
        print(f"  {path}")
    
    print(f"\n✅ Saved all {len(loops_data)} loops to loops.json")

if __name__ == "__main__":
    main()