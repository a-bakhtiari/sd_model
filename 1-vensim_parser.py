"""
Use DeepSeek API to parse MDL file and generate connections JSON
"""

import json
import requests
import os

def parse_mdl_with_deepseek(mdl_path, api_key):
    """
    Send MDL file to DeepSeek for parsing
    """
    with open(mdl_path, 'r') as f:
        mdl_content = f.read()
    
    prompt = f"""Extract all variable dependencies from this Vensim MDL file.

WHAT TO LOOK FOR:
Lines that follow this pattern:
VariableName = A FUNCTION OF(dep1, dep2, -dep3, dep4)

HOW TO PARSE:
1. The variable BEFORE the "=" is the TARGET (where the arrow points TO)
2. Variables inside "A FUNCTION OF(...)" are SOURCES (where arrows come FROM)
3. If a source starts with "-" it's a NEGATIVE relationship
4. If a source has no "-" it's a POSITIVE relationship

EXAMPLE:
If you see: Open Issues = A FUNCTION OF(Feedback, Issue Creation Rate, -Issue Resolution Rate)
You create THREE connections:
- Feedback → Open Issues (positive)
- Issue Creation Rate → Open Issues (positive)  
- Issue Resolution Rate → Open Issues (negative)

OUTPUT RULES:
1. Return ONLY valid JSON, no explanations
2. For negative relationships: remove the "-" from the source name but mark relationship as "negative"
3. Ignore anything after the sketch section (after \\\---///)
4. Some definitions span multiple lines - include all dependencies until the closing ")"

JSON FORMAT:
{{
    "connections": [
        {{"from": "Source Variable Name", "to": "Target Variable Name", "relationship": "positive"}},
        {{"from": "Another Source", "to": "Another Target", "relationship": "negative"}}
    ]
}}

MDL FILE CONTENT:
{mdl_content}"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0
    }
    
    response = requests.post("https://api.deepseek.com/v1/chat/completions", 
                            headers=headers, json=data)
    
    content = response.json()['choices'][0]['message']['content']
    
    # Remove markdown if present
    if '```' in content:
        content = content.split('```json')[-1].split('```')[0]
    
    return json.loads(content)

def main():
    mdl_path = "/Users/alibakhtiari/Desktop/Thesis/SD_model/untitled.mdl"
    api_key = os.environ.get('DEEPSEEK_API_KEY', "sk-2596158a01b542618d82ce61b6182810")
    
    # Get parsed data
    result = parse_mdl_with_deepseek(mdl_path, api_key)
    
    # Save to file
    with open('connections.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Saved {len(result['connections'])} connections to connections.json")

if __name__ == "__main__":
    main()