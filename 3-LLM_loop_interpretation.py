"""
Step 3: Use LLM to interpret the meaning of loops
"""

import json
import requests
import os

def load_loops(filepath='loops.json'):
    """Load loops from JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)

def interpret_loops_with_llm(loops_data, api_key):
    """Send loops to LLM for interpretation"""
    
    prompt = f"""Analyze these feedback loops from an open-source software community system dynamics model.

CONTEXT: This model represents dynamics of open-source projects including contributors, knowledge transfer, reputation, and development processes.

LOOPS DATA:
{json.dumps(loops_data['loops'], indent=2)}

TASK: For each loop, provide:
1. A descriptive name (e.g., "Reputation-Growth Loop")
2. What this loop means in real-world terms
3. Whether it helps or hinders project sustainability
4. Which loop is likely most influential in system behavior

OUTPUT FORMAT (JSON):
{{
    "interpreted_loops": [
        {{
            "loop_nodes": ["list", "of", "nodes"],
            "name": "Descriptive Loop Name",
            "type": "R or B",
            "meaning": "What happens in this loop in real-world terms",
            "impact": "positive/negative/mixed for project sustainability",
            "explanation": "Why this loop matters"
        }}
    ],
    "dominant_loops": ["Names of 3 most influential loops"],
    "system_insights": "Overall pattern these loops reveal about the system"
}}

Focus on practical implications for open-source project management."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3  # Lower for more focused analysis
    }
    
    response = requests.post("https://api.deepseek.com/v1/chat/completions", 
                            headers=headers, json=data)
    
    content = response.json()['choices'][0]['message']['content']
    
    # Remove markdown if present
    if '```' in content:
        content = content.split('```json')[-1].split('```')[0]
    
    return json.loads(content)

def combine_analysis(loops_data, interpretations):
    """Combine original loops with interpretations"""
    
    # Match interpretations to original loops
    enhanced_loops = []
    
    for loop in loops_data['loops']:
        # Find matching interpretation
        for interp in interpretations['interpreted_loops']:
            if set(loop['nodes']) == set(interp['loop_nodes']):
                enhanced = {
                    **loop,
                    'name': interp['name'],
                    'meaning': interp['meaning'],
                    'impact': interp['impact'],
                    'explanation': interp['explanation']
                }
                enhanced_loops.append(enhanced)
                break
    
    return {
        'total_loops': loops_data['total_loops'],
        'summary': loops_data['summary'],
        'enhanced_loops': enhanced_loops,
        'dominant_loops': interpretations.get('dominant_loops', []),
        'system_insights': interpretations.get('system_insights', '')
    }

def main():
    # Load loops from Step 2
    loops_data = load_loops('loops.json')
    
    # Get API key
    api_key = os.environ.get('DEEPSEEK_API_KEY', 'sk-2596158a01b542618d82ce61b6182810')
    
    print(f"Sending {loops_data['total_loops']} loops to LLM for interpretation...")
    
    # Get interpretations
    interpretations = interpret_loops_with_llm(loops_data, api_key)
    
    # Combine with original data
    final_analysis = combine_analysis(loops_data, interpretations)
    
    # Save enhanced analysis
    with open('loops_interpreted.json', 'w') as f:
        json.dump(final_analysis, f, indent=2)
    
    print(f"\n✅ Loop interpretation complete!")
    print(f"\n📊 Key Insights:")
    print(f"System pattern: {final_analysis.get('system_insights', 'N/A')}")
    
    print(f"\n🔝 Dominant loops:")
    for loop_name in final_analysis.get('dominant_loops', [])[:3]:
        print(f"  - {loop_name}")
    
    print(f"\n💾 Saved to loops_interpreted.json")

if __name__ == "__main__":
    main()