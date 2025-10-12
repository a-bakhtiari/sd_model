"""
Test script for archetype detection module.
Run this standalone to verify archetype detection works before integrating into main pipeline.
"""
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sd_model.pipeline.archetype_detection import detect_archetypes
from src.sd_model.llm.client import LLMClient
from src.sd_model.paths import for_project
from src.sd_model.config import load_config


def test_archetype_detection(project_name: str = "oss_model"):
    """Test archetype detection on a project."""

    print(f"\n{'='*60}")
    print(f"Testing Archetype Detection on: {project_name}")
    print(f"{'='*60}\n")

    # Get project paths
    cfg = load_config()
    paths = for_project(cfg, project_name)

    # Load variables and connections
    print("Loading model data...")
    variables_path = paths.parsing_dir / "variables.json"
    connections_path = paths.parsing_dir / "connections.json"

    if not variables_path.exists():
        print(f"❌ Variables file not found: {variables_path}")
        return

    if not connections_path.exists():
        print(f"❌ Connections file not found: {connections_path}")
        return

    variables = json.loads(variables_path.read_text(encoding="utf-8"))
    connections = json.loads(connections_path.read_text(encoding="utf-8"))

    # Convert connections from ID-based to name-based format
    # (archetype detection expects connection format with from_var/to_var names)
    vars_by_id = {v['id']: v for v in variables.get('variables', [])}

    name_based_connections = []
    for conn in connections.get('connections', []):
        from_id = conn.get('from')
        to_id = conn.get('to')

        if from_id in vars_by_id and to_id in vars_by_id:
            from_var = vars_by_id[from_id]['name']
            to_var = vars_by_id[to_id]['name']
            polarity = conn.get('polarity', 'UNDECLARED').lower()

            # Map polarity
            if polarity == 'positive':
                relationship = 'positive'
            elif polarity == 'negative':
                relationship = 'negative'
            else:
                relationship = 'undeclared'

            name_based_connections.append({
                'from_var': from_var,
                'to_var': to_var,
                'relationship': relationship
            })

    connections_formatted = {
        'connections': name_based_connections
    }

    print(f"✓ Loaded {len(variables.get('variables', []))} variables")
    print(f"✓ Loaded {len(name_based_connections)} connections")

    # Initialize LLM client
    print("\nInitializing LLM client...")
    client = LLMClient(provider="deepseek")

    # Run archetype detection
    print("\nRunning archetype detection (this may take a moment)...")
    result = detect_archetypes(variables, connections_formatted, client)

    # Check for errors
    if "error" in result:
        print(f"\n❌ Error during archetype detection:")
        print(f"   {result['error']}")
        if "raw_response" in result:
            print(f"\nRaw LLM response:")
            print(result['raw_response'][:500] + "..." if len(result['raw_response']) > 500 else result['raw_response'])
        return

    # Display results
    print("\n" + "="*60)
    print("ARCHETYPE DETECTION RESULTS")
    print("="*60 + "\n")

    archetypes = result.get('archetypes', [])

    print(f"📊 Summary:")
    print(f"   - Archetypes detected: {len(archetypes)}")
    total_vars = sum(len(a.get('additions', {}).get('variables', [])) for a in archetypes)
    total_conns = sum(len(a.get('additions', {}).get('connections', [])) for a in archetypes)
    print(f"   - Total variables suggested: {total_vars}")
    print(f"   - Total connections suggested: {total_conns}")

    if not archetypes:
        print("\n⚠️  No archetypes detected.")
        return

    # Display each archetype
    for i, archetype in enumerate(archetypes, 1):
        name = archetype.get('name', 'Unknown')
        rationale = archetype.get('rationale', 'No rationale provided')
        additions = archetype.get('additions', {})

        print(f"\n{'─'*60}")
        print(f"Archetype #{i}: {name}")
        print(f"{'─'*60}")
        print(f"\n📝 Rationale:\n   {rationale}\n")

        # Variables to add
        vars_to_add = additions.get('variables', [])
        if vars_to_add:
            print(f"➕ Variables to add ({len(vars_to_add)}):")
            for var in vars_to_add:
                print(f"   • {var['name']} ({var['type']})")
                print(f"     └─ {var.get('description', 'No description')}")
                if 'rationale' in var:
                    print(f"     └─ Rationale: {var['rationale']}")

        # Connections to add
        conns_to_add = additions.get('connections', [])
        if conns_to_add:
            print(f"\n➕ Connections to add ({len(conns_to_add)}):")
            for conn in conns_to_add:
                rel = conn['relationship']
                arrow = "→ +" if rel == 'positive' else "→ −" if rel == 'negative' else "→"
                print(f"   • {conn['from']} {arrow} {conn['to']}")
                if 'rationale' in conn:
                    print(f"     └─ {conn['rationale']}")

    # Save results
    output_path = Path(__file__).parent / "archetype_detection_results.json"
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n✅ Results saved to: {output_path}")

    # Also create a simplified suggestions file
    suggestions = {
        "archetypes": [
            {
                "name": a.get('name'),
                "variables_count": len(a.get('additions', {}).get('variables', [])),
                "connections_count": len(a.get('additions', {}).get('connections', []))
            }
            for a in archetypes
        ]
    }

    suggestions_path = Path(__file__).parent / "archetype_suggestions.json"
    suggestions_path.write_text(json.dumps(suggestions, indent=2), encoding="utf-8")
    print(f"✅ Summary saved to: {suggestions_path}")

    print("\n" + "="*60)
    print("Test complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Allow project name as command-line argument
    project = sys.argv[1] if len(sys.argv) > 1 else "oss_model"
    test_archetype_detection(project)
