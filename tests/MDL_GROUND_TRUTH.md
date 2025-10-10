# MDL Ground Truth Analysis

**Generated**: 2025-10-10
**Source**: `projects/oss_model/mdl/untitled.mdl`

## Key Finding: LLM Results Are NOT Ground Truth!

The **MDL file itself** is the only source of truth. Comparison reveals:

| Source | Stocks Detected | Accuracy |
|--------|----------------|----------|
| MDL (Truth) | 30 | 100% (by definition) |
| LLM Parser | 16 | 53% ❌ |
| Python Parser | 1 | 3% ❌ |

**Conclusion**: Both LLM and Python parsers are missing stocks. The user was right - "LLM results sometimes miss a link or two".

---

## MDL Structure (oss_model)

**From analysis script** (`tests/analyze_mdl_ground_truth.py`):

```
Variables (10, lines):     44
Valves (11, lines):        21
Connections (1, lines):    75
```

### Variable Type Distribution

**Stocks** (30 total):
Variables that receive arrows FROM valves (11, IDs)

```
Stock IDs: [1, 2, 4, 5, 6, 7, 12, 17, 22, 30, 31, 36, 42, 47, 48, 49, 50,
            51, 56, 65, 72, 81, 87, 90, 106, 113, 118, 128, 141, 142]
```

Known stock names:
- 1: New Contributors
- 2: Core Developer
- 4: Source Code
- 5: User Base
- 6: Project Reputation
- 30: Community Health
- 47: New Pull request
- 48: Open Issues
- 49: Project's Implicit Knowledge
- 50: Projects's Explicit Knowledge
- 56: Pull Request Under review
- 72: Experienced Contributors
- 106: Searchable Knowledge Base
- 113: Closed Issues
- 141: hi

(Others show as "UNKNOWN" - may be orphaned IDs)

**Flows** (21 total):
Valve IDs that control flow into stocks

```
Flow Valve IDs: [10, 15, 20, 25, 34, 39, 45, 54, 59, 63, 68, 75, 79, 84,
                 90, 100, 104, 121, 125, 131, 143]
```

**Auxiliaries** (44 - 30 stocks = 14):
Variables that are neither stocks nor flows

---

## Connection Analysis

**Total Connections**: 75 (1, lines)

Breakdown:
- **Valve → Stock**: 42 connections (these define stocks)
- **Variable → Valve**: TBD
- **Variable → Variable**: 25 connections (excluding valves)

### Polarity Markers

**Positive polarity** (field[6]=43): 8 connections

```
27 → 6: Software Quality and Features → Project Reputation
45 → 90: Valve45 → Valve90
93 → 79: Implicit Knowledge Transfer (Mentorship) → Valve79
2 → 93: Core Developer → Implicit Knowledge Transfer (Mentorship)
48 → 54: Open Issues → Valve54
106 → 50: Searchable Knowledge Base → Projects's Explicit Knowledge
6 → 138: Project Reputation → Joining Rate
30 → 6: Community Health → Project Reputation
```

---

## Fixes Needed in Python Parser

### Issue #1: Stock Detection (CRITICAL)

**Current bug**: Only detects 1 stock out of 30 (3% accuracy)

**Root cause**:
```python
# tests/test_python_vs_llm_parser.py:95-110
if from_id in valve_ids:
    valve_to_stock[from_id] = [to_id]  # OVERWRITES previous entries!
```

**Fix**:
```python
if from_id in valve_ids:
    valve_to_stock.setdefault(from_id, []).append(to_id)
```

**Expected result after fix**: Detect all 30 stocks

### Issue #2: Variable Counting

The MDL has some "UNKNOWN" variables - these are IDs referenced in connections but without corresponding `10,` variable definitions. The parser needs to handle these gracefully.

### Issue #3: Connection Resolution

Need to properly resolve valve-mediated connections and not skip them entirely.

---

## Testing Strategy

1. **Fix stock detection** → Test → Should find 30 stocks
2. **Fix connection resolution** → Test → Should handle all 75 connections
3. **Fix polarity detection** → Test → Should capture 8 positive markers
4. **Compare with MDL truth** (NOT LLM!) → Should match 100%

---

## Commands to Run

```bash
# Analyze MDL ground truth
python tests/analyze_mdl_ground_truth.py projects/oss_model/mdl/untitled.mdl

# Run parser test
python tests/test_python_vs_llm_parser.py --project oss_model

# Compare results
# Python should match MDL, not LLM!
```

---

## Important Notes

- ✅ **MDL file = ground truth** (not LLM!)
- ❌ **LLM missed 14 stocks** (detected 16/30 = 53%)
- ❌ **Python missed 29 stocks** (detected 1/30 = 3%)
- 🎯 **Goal**: Python parser → 100% match with MDL
