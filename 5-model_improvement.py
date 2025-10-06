"""
Step 5: Generate model improvements based on theory validation
"""

import json
import requests
import os

def load_validation_results(filepath='theory_validation.json'):
    """Load the validation results from Step 4"""
    with open(filepath, 'r') as f:
        return json.load(f)

def generate_improvements(validation_results, connections, api_key):
    """Generate specific model improvements based on validation findings"""
    
    prompt = f"""Based on theory validation of an open-source community system dynamics model, generate specific improvements.

VALIDATION FINDINGS:
- Average theory alignment: {validation_results['average_alignment']}/10
- Theories applied: {', '.join([v['theory'] for v in validation_results['theory_validations']])}

CONSISTENTLY MISSING CONNECTIONS:
{json.dumps(validation_results.get('consistent_missing', []), indent=2)}

CONSISTENTLY PROBLEMATIC CONNECTIONS:
{json.dumps(validation_results.get('consistent_issues', []), indent=2)}

CURRENT MODEL STATS:
- Total connections: {len(connections)}
- Variables include: Contributors, Knowledge, PRs, Issues, Reputation

TASK: Generate concrete improvements to the model.

OUTPUT FORMAT (JSON):
{{
    "priority_additions": [
        {{
            "from": "Source Variable",
            "to": "Target Variable", 
            "relationship": "positive/negative",
            "rationale": "Why this is critical based on theory",
            "expected_impact": "How this improves the model"
        }}
    ],
    "recommended_removals": [
        {{
            "from": "Source",
            "to": "Target",
            "reason": "Why this should be removed or modified"
        }}
    ],
    "new_variables_needed": [
        {{
            "name": "Variable Name",
            "type": "stock/flow/auxiliary",
            "purpose": "What this represents",
            "connects_to": ["List of variables it should connect to"]
        }}
    ],
    "structural_changes": [
        {{
            "change": "Description of structural modification",
            "justification": "Theory-based reasoning"
        }}
    ],
    "implementation_order": ["Step 1", "Step 2", "Step 3"],
    "expected_improvement": "Overall expected impact on model quality"
}}"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4
    }
    
    response = requests.post("https://api.deepseek.com/v1/chat/completions",
                            headers=headers, json=data)
    
    content = response.json()['choices'][0]['message']['content']
    
    if '```' in content:
        content = content.split('```json')[-1].split('```')[0]
    
    return json.loads(content)

def create_implementation_script(improvements):
    """Create a script that could be used to update the MDL file"""
    
    script = {
        "additions": [],
        "removals": [],
        "new_variables": []
    }
    
    # Format additions for easy implementation
    for addition in improvements.get('priority_additions', []):
        script['additions'].append({
            'command': f"Add connection: {addition['from']} → {addition['to']} ({addition['relationship']})",
            'mdl_fragment': f"{addition['to']} = A FUNCTION OF(..., {'-' if addition['relationship']=='negative' else ''}{addition['from']})",
            'rationale': addition['rationale']
        })
    
    # Format new variables
    for new_var in improvements.get('new_variables_needed', []):
        connections_str = ', '.join(new_var.get('connects_to', []))
        script['new_variables'].append({
            'command': f"Create variable: {new_var['name']}",
            'mdl_fragment': f"{new_var['name']} = A FUNCTION OF({connections_str})",
            'type': new_var['type'],
            'purpose': new_var['purpose']
        })
    
    return script

def generate_updated_connections(current_connections, improvements):
    """Generate what the new connections list would look like"""
    
    updated = current_connections.copy()
    
    # Add new connections
    for addition in improvements.get('priority_additions', []):
        updated.append({
            'from': addition['from'],
            'to': addition['to'],
            'relationship': addition['relationship']
        })
    
    # Remove problematic connections (mark them rather than delete)
    for removal in improvements.get('recommended_removals', []):
        for conn in updated:
            if conn['from'] == removal['from'] and conn['to'] == removal['to']:
                conn['marked_for_review'] = True
                conn['removal_reason'] = removal['reason']
    
    return updated

def main():
    # Load previous results
    validation_results = load_validation_results('theory_validation.json')
    
    with open('connections.json', 'r') as f:
        connections_data = json.load(f)
        connections = connections_data['connections']
    
    # Get API key
    api_key = os.environ.get('DEEPSEEK_API_KEY', 'sk-2596158a01b542618d82ce61b6182810')
    
    print("Generating model improvements based on theory validation...")
    
    # Generate improvements
    improvements = generate_improvements(validation_results, connections, api_key)
    
    # Create implementation guidance
    implementation_script = create_implementation_script(improvements)
    
    # Generate updated connections
    updated_connections = generate_updated_connections(connections, improvements)
    
    # Prepare final output
    output = {
        'improvements': improvements,
        'implementation_script': implementation_script,
        'statistics': {
            'additions_proposed': len(improvements.get('priority_additions', [])),
            'removals_suggested': len(improvements.get('recommended_removals', [])),
            'new_variables': len(improvements.get('new_variables_needed', [])),
            'total_connections_after': len(updated_connections)
        },
        'updated_connections': updated_connections
    }
    
    # Save everything
    with open('model_improvements.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n📊 Improvement Summary:")
    print(f"Additions proposed: {output['statistics']['additions_proposed']}")
    print(f"Removals suggested: {output['statistics']['removals_suggested']}")
    print(f"New variables needed: {output['statistics']['new_variables']}")
    
    print(f"\n🎯 Implementation Order:")
    for i, step in enumerate(improvements.get('implementation_order', []), 1):
        print(f"{i}. {step}")
    
    print(f"\n💾 Saved to model_improvements.json")
    print("\nNext: Review improvements and decide which to implement in Vensim")

if __name__ == "__main__":
    main()