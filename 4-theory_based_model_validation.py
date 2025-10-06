"""
Step 4: Validate model against theories using LLM
"""

import json
import requests
import os
import pandas as pd

def load_theories(filepath='theories.txt'):
    """Load theories from file (txt or excel)"""
    if filepath.endswith('.xlsx'):
        df = pd.read_excel(filepath)
        # Assume columns: theory_name, description, focus_area
        theories = df.to_dict('records')
    else:
        # For testing, create sample theories
        theories = [
            {
                "name": "Communities of Practice (Wenger)",
                "description": "Learning happens through participation in communities where practitioners share knowledge through legitimate peripheral participation, moving from periphery to core through engagement, imagination, and alignment",
                "focus_area": "knowledge_transfer"
            },
            {
                "name": "Nonaka's SECI Model",
                "description": "Knowledge creation through four modes: Socialization (tacit to tacit), Externalization (tacit to explicit), Combination (explicit to explicit), and Internalization (explicit to tacit)",
                "focus_area": "knowledge_conversion"
            }
        ]
    return theories

def validate_with_theory(connections, loops, theory, api_key):
    """Validate model against a specific theory"""
    
    prompt = f"""Analyze this system dynamics model against {theory['name']}.

THEORY BACKGROUND:
{theory['description']}

MODEL CONNECTIONS:
{json.dumps(connections[:20], indent=2)}  # Sample for token limits

KEY FEEDBACK LOOPS:
{json.dumps(loops[:5], indent=2)}  # Top loops

ANALYSIS TASKS:
1. Which connections align well with this theory?
2. Which connections contradict or are unsupported by this theory?
3. What connections are MISSING that the theory would predict?
4. Rate the overall model alignment with this theory (1-10)

OUTPUT FORMAT (JSON):
{{
    "theory": "{theory['name']}",
    "aligned_connections": [
        {{
            "connection": {{"from": "X", "to": "Y"}},
            "explanation": "Why this aligns with the theory"
        }}
    ],
    "problematic_connections": [
        {{
            "connection": {{"from": "X", "to": "Y"}},
            "issue": "Why this contradicts or lacks support"
        }}
    ],
    "missing_connections": [
        {{
            "suggested": {{"from": "X", "to": "Y", "relationship": "positive/negative"}},
            "rationale": "Why theory predicts this connection"
        }}
    ],
    "alignment_score": 7,
    "recommendations": "Specific improvements based on this theory"
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
        "temperature": 0.3
    }
    
    response = requests.post("https://api.deepseek.com/v1/chat/completions",
                            headers=headers, json=data)
    
    content = response.json()['choices'][0]['message']['content']
    
    if '```' in content:
        content = content.split('```json')[-1].split('```')[0]
    
    return json.loads(content)

def synthesize_validations(all_validations):
    """Combine insights from all theory validations"""
    
    synthesis = {
        "theories_applied": len(all_validations),
        "average_alignment": sum(v['alignment_score'] for v in all_validations) / len(all_validations),
        "consistent_issues": [],
        "consistent_missing": [],
        "theory_validations": all_validations
    }
    
    # Find patterns across theories
    all_missing = []
    all_problematic = []
    
    for validation in all_validations:
        all_missing.extend(validation.get('missing_connections', []))
        all_problematic.extend(validation.get('problematic_connections', []))
    
    # Identify frequently mentioned issues
    # (In production, would do more sophisticated deduplication)
    synthesis['consistent_missing'] = all_missing[:3]  # Top missing connections
    synthesis['consistent_issues'] = all_problematic[:3]  # Top problematic
    
    return synthesis

def main():
    # Load inputs
    with open('connections.json', 'r') as f:
        connections = json.load(f)['connections']
    
    with open('loops_interpreted.json', 'r') as f:
        loops_data = json.load(f)
        loops = loops_data.get('enhanced_loops', loops_data.get('loops', []))
    
    # Load theories
    theories = load_theories('theories.txt')  # or theories.xlsx
    
    # Get API key
    api_key = os.environ.get('DEEPSEEK_API_KEY', "sk-2596158a01b542618d82ce61b6182810")
    
    print(f"Validating model against {len(theories)} theories...")
    
    # Validate against each theory
    all_validations = []
    for theory in theories:
        print(f"\nValidating against: {theory['name']}")
        validation = validate_with_theory(connections, loops, theory, api_key)
        all_validations.append(validation)
        
        # Show summary
        print(f"  Alignment score: {validation['alignment_score']}/10")
        print(f"  Missing connections: {len(validation.get('missing_connections', []))}")
        print(f"  Problematic connections: {len(validation.get('problematic_connections', []))}")
    
    # Synthesize findings
    synthesis = synthesize_validations(all_validations)
    
    # Save results
    with open('theory_validation.json', 'w') as f:
        json.dump(synthesis, f, indent=2)
    
    print(f"\n📊 Overall Results:")
    print(f"Average alignment score: {synthesis['average_alignment']:.1f}/10")
    print(f"\n🔍 Key findings:")
    print("Consistently missing connections:")
    for missing in synthesis['consistent_missing'][:2]:
        print(f"  - {missing['suggested']['from']} → {missing['suggested']['to']}")
    
    print(f"\n✅ Saved detailed analysis to theory_validation.json")

if __name__ == "__main__":
    main()