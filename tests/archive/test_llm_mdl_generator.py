"""Test: LLM-Based MDL Generator

This test uses an LLM to generate a complete, valid MDL file by:
1. Reading the original MDL file
2. Loading theory enhancement changes (JSON)
3. Prompting LLM to apply changes while preserving equations
4. Validating and saving the result
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, '.')

from src.sd_model.llm.client import LLMClient


def create_mdl_generation_prompt(original_mdl: str, changes: dict) -> str:
    """Create comprehensive prompt for LLM to generate modified MDL."""

    # Count changes for summary
    model_changes = changes.get("model_changes", [])
    add_vars = sum(1 for c in model_changes if c["operation"] == "add_variable")
    remove_vars = sum(1 for c in model_changes if c["operation"] == "remove_variable")
    add_conns = sum(1 for c in model_changes if c["operation"] == "add_connection")
    remove_conns = sum(1 for c in model_changes if c["operation"] == "remove_connection")
    modify_conns = sum(1 for c in model_changes if c["operation"] == "modify_connection")

    prompt = f"""You are a Vensim MDL file generator. Your task is to apply theory enhancement changes to an existing System Dynamics model while preserving all equations and structure.

# ORIGINAL MDL FILE

```
{original_mdl}
```

# CHANGES TO APPLY

```json
{json.dumps(changes, indent=2)}
```

# CHANGES SUMMARY
- Add variables: {add_vars}
- Remove variables: {remove_vars}
- Add connections: {add_conns}
- Remove connections: {remove_conns}
- Modify connections: {modify_conns}

# MDL FILE FORMAT

An MDL file has two main sections:

## 1. EQUATION SECTION (before sketch)
Format:
```
Variable Name = A FUNCTION OF( Dependency1, Dependency2, -Dependency3 )
	~	units
	~	description
	|
```
- Use negative sign (-) for negative relationships
- Preserve multi-line equations (\ continuation)
- Keep exact spacing and formatting

## 2. SKETCH SECTION (after "\\\\\\---/// Sketch information")
Format:
```
10,id,Name,x,y,width,height,type,flags...
```
- `10,` lines define variables with positions
- `1,` lines define connections/arrows
- Names with special chars must be quoted

# OPERATION INSTRUCTIONS

## ADD_VARIABLE
1. **Equation section**: Add new equation block with dependencies from add_connection operations
   ```
   NewVariable = A FUNCTION OF( )
   	~	units_from_json
   	~	description_from_json
   	|
   ```

2. **Sketch section**: Add new `10,` line with position and GREEN border color
   ```
   10,NEW_ID,"Variable Name",x,y,width,height,type,3,0,2,-1,1,0,0,0-0-0,0-255-0,|||0-0-0,0,0,0,0,0,0
   ```
   - Use next available ID
   - type: 3=Stock, 8=Auxiliary
   - Green border: `0-255-0`

## REMOVE_VARIABLE
1. **Equation section**: DELETE the entire equation block
2. **Sketch section**: DELETE the `10,` line
3. **Update dependencies**: Remove from ALL other equations that reference it
4. **Remove connections**: Delete all `1,` lines involving this variable ID

## ADD_CONNECTION
1. **Find target variable** (the "to" variable)
2. **Update its equation**: Add source variable to dependencies
   - Positive relationship: `Variable`
   - Negative relationship: `-Variable`
3. **Sketch section**: Add new `1,` line with GREEN color marker
   ```
   1,FROM_ID,TO_ID,1,0,0,0,0,192,0,-1--1--1,,1|(0,0)|
   ```

## REMOVE_CONNECTION
1. **Find target variable equation**
2. **Remove source** from its dependencies
3. **Sketch section**: Delete corresponding `1,` line

## MODIFY_CONNECTION
1. **Find target variable equation**
2. **Update relationship**:
   - positive: `Variable` (no minus)
   - negative: `-Variable` (with minus)
3. **Sketch section**: Update `1,` line to mark with ORANGE color (comment: modified)

# CRITICAL REQUIREMENTS

1. **PRESERVE ALL CONTENT**: Keep every equation exactly as-is except for changes
2. **MAINTAIN EQUATIONS**: Don't replace with placeholders - keep actual dependencies
3. **VALID SYNTAX**: Output must be valid Vensim MDL
4. **COLOR CODING**:
   - Green (0-255-0): Added variables
   - Orange (255-165-0): Modified (use comments to mark modified connections)
5. **DEPENDENCIES**: Update equations when connections change
6. **ID MANAGEMENT**: Use sequential IDs for new variables (start from max+1)
7. **QUOTES**: Quote variable names with special characters in sketch section

# VALIDATION CHECKLIST

Before outputting, verify:
- [ ] All original equations preserved (unless variable removed)
- [ ] New variables have equations (even if simple)
- [ ] Connection changes reflected in equations
- [ ] Sketch section has correct IDs and positions
- [ ] Green borders on new variables
- [ ] No syntax errors (balanced quotes, proper commas)
- [ ] Simulation variables (FINAL TIME, etc.) preserved

# OUTPUT FORMAT

Return ONLY the complete modified MDL file. No explanations, no JSON, no markdown code blocks.
Start with: {{UTF-8}}
End with: ///---\\\\\\

# EXAMPLE OPERATION

**Original equation:**
```
Core Developer = A FUNCTION OF( Promotion Rate, -Developer's Turnover )
```

**Change: add_connection from "New Variable" to "Core Developer" (positive)**

**Modified equation:**
```
Core Developer = A FUNCTION OF( Promotion Rate, -Developer's Turnover, New Variable )
```

Now, apply ALL changes from the JSON to the original MDL file. Output the complete modified MDL file.
"""
    return prompt


def test_llm_mdl_generation():
    """Test LLM-based MDL generation."""

    print("="*80)
    print("LLM-BASED MDL GENERATOR TEST")
    print("="*80)

    repo_root = Path(".")

    # Input files
    mdl_path = repo_root / "projects" / "oss_model" / "mdl" / "untitled.mdl"
    enhancement_json_path = repo_root / "tests" / "theory_enhancement_mdl.json"
    output_mdl_path = repo_root / "tests" / "enhanced_model_llm.mdl"

    # 1. Load original MDL
    print(f"\n1. Loading original MDL: {mdl_path}")
    if not mdl_path.exists():
        print(f"   ✗ Error: MDL file not found")
        return

    original_mdl = mdl_path.read_text(encoding="utf-8")
    print(f"   ✓ Loaded ({len(original_mdl)} characters)")

    # 2. Load enhancement JSON
    print(f"\n2. Loading enhancement JSON: {enhancement_json_path}")
    if not enhancement_json_path.exists():
        print(f"   ✗ Error: Enhancement JSON not found")
        return

    enhancement_data = json.loads(enhancement_json_path.read_text(encoding="utf-8"))
    print(f"   ✓ Loaded {len(enhancement_data.get('model_changes', []))} changes")

    # Show summary
    summary = enhancement_data.get("summary", {})
    print(f"\n   Summary:")
    print(f"     Variables to add: {summary.get('additions', {}).get('variables', 0)}")
    print(f"     Variables to remove: {summary.get('removals', {}).get('variables', 0)}")
    print(f"     Connections to add: {summary.get('additions', {}).get('connections', 0)}")
    print(f"     Connections to remove: {summary.get('removals', {}).get('connections', 0)}")
    print(f"     Connections to modify: {summary.get('modifications', {}).get('connections', 0)}")

    # 3. Create prompt
    print(f"\n3. Creating LLM prompt...")
    prompt = create_mdl_generation_prompt(original_mdl, enhancement_data)
    print(f"   ✓ Prompt created ({len(prompt)} characters)")

    # 4. Call LLM
    print(f"\n4. Calling LLM (DeepSeek)...")
    print(f"   This may take 2-5 minutes due to large output...")
    client = LLMClient(provider="deepseek")

    # Use higher max_tokens and timeout for full MDL file generation
    response = client.complete(prompt, temperature=0.1, max_tokens=8000, timeout=300)

    print(f"   ✓ Received response ({len(response)} characters)")

    # 5. Validate and save
    print(f"\n5. Validating response...")

    # Check if response looks like MDL
    if not response.startswith("{UTF-8}"):
        print(f"   ⚠ Warning: Response doesn't start with {{UTF-8}}")
        print(f"   First 100 chars: {response[:100]}")

    if "\\\\\\---/// Sketch information" not in response:
        print(f"   ✗ Error: No sketch section found in response")
        return

    # Count variables in output
    sketch_vars = response.count("\n10,")
    print(f"   ✓ Found {sketch_vars} variables in sketch section")

    # 6. Save output
    print(f"\n6. Saving to: {output_mdl_path}")
    output_mdl_path.write_text(response, encoding="utf-8")
    print(f"   ✓ Saved successfully")

    # 7. Final validation
    print(f"\n7. Final validation:")

    # Count original variables
    original_vars = original_mdl.count("\n10,")
    expected_change = (
        summary.get('additions', {}).get('variables', 0) -
        summary.get('removals', {}).get('variables', 0)
    )
    expected_vars = original_vars + expected_change

    print(f"   Original variables: {original_vars}")
    print(f"   Expected change: {expected_change:+d}")
    print(f"   Expected total: {expected_vars}")
    print(f"   Actual total: {sketch_vars}")

    if sketch_vars == expected_vars:
        print(f"   ✓ Variable count matches!")
    else:
        print(f"   ⚠ Variable count mismatch (diff: {sketch_vars - expected_vars:+d})")

    # Check for placeholders
    if "A FUNCTION OF( )" in response:
        empty_count = response.count("A FUNCTION OF( )")
        total_equations = response.split("\\\\\\---///")[0].count(" = A FUNCTION OF")
        print(f"   ⚠ Found {empty_count}/{total_equations} empty equations")
    else:
        print(f"   ✓ No empty placeholder equations")

    # Check for color coding
    if "0-255-0" in response:
        green_count = response.count("0-255-0")
        print(f"   ✓ Found {green_count} green-colored items (additions)")
    else:
        print(f"   ⚠ No green color codes found")

    print("\n" + "="*80)
    print("✅ TEST COMPLETED!")
    print(f"Enhanced MDL file: {output_mdl_path}")
    print("Next step: Open in Vensim to verify functionality")
    print("="*80)


if __name__ == "__main__":
    test_llm_mdl_generation()
