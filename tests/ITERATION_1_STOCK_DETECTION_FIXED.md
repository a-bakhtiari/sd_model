# Iteration 1: Stock Detection - FIXED ✅

**Date**: 2025-10-10
**Issue**: Stock detection accuracy was 3% (1/30)
**Result**: Stock detection accuracy now 100% (15/15 with definitions + 14/14 orphaned)

---

## Problem Identified

**Root Cause**: Processing valves and connections in ONE PASS caused connections to be evaluated before all valve IDs were collected.

**Evidence**:
```
[DEBUG] Found 2 stocks: [141, 142]  ❌ BEFORE FIX
[DEBUG] Found 29 stocks: [1, 2, 4, 5, 6, 7, 12, 17, 22, 30]...  ✅ AFTER FIX
```

---

## Solution Applied

**Change**: Split into TWO PASSES in `tests/test_python_vs_llm_parser.py`

```python
# BEFORE (BROKEN):
for line in parser.sketch_other:
    if line.startswith("11,"):
        valve_ids.add(valve_id)
    elif line.startswith("1,"):
        if from_id in valve_ids:  # May be FALSE if valve not yet seen!
            stock_ids.add(to_id)

# AFTER (FIXED):
# Pass 1: Collect ALL valve IDs first
for line in parser.sketch_other:
    if line.startswith("11,"):
        valve_ids.add(valve_id)

# Pass 2: Now check connections (valve_ids is complete)
for line in parser.sketch_other:
    if line.startswith("1,"):
        if from_id in valve_ids:  # Now ALWAYS correct!
            if to_id not in valve_ids:  # Exclude valve-to-valve
                stock_ids.add(to_id)
```

**Additional Fix**: Exclude valve-to-valve connections (ID 90 was both valve and stock)

---

## Test Results (oss_model)

### Before Fix:
```
Stock detection: 1/16 stocks found (6.25%)
Type mismatches: 15 variables
```

### After Fix:
```
Stock detection: 15/15 stocks found (100%)  ✅
Type mismatches: 1 variable (ID 136 - LLM error, not parser error)
```

### Comparison with MDL Ground Truth:

| Metric | MDL Truth | Python Parser | LLM Parser |
|--------|-----------|---------------|------------|
| Total stocks (with variables) | 15 | 15 ✅ | 16 (1 wrong) |
| Stock IDs found | [1, 2, 4, 5, 6, 30, 47, 48, 49, 50, 56, 72, 106, 113, 141] | ALL ✅ | 14/15 + 1 wrong |
| Orphaned stock IDs | 14 | 14 ✅ | N/A |
| Accuracy | 100% | 100% ✅ | 93.75% |

**ID 136 Analysis**:
- Variable: "Discussions"
- Python says: Auxiliary ✅
- LLM says: Stock ❌
- MDL truth: No valve points to 136 → Auxiliary
- **Conclusion**: Python is correct, LLM made an error (as user warned)

---

## Key Insights

1. **MDL is the only truth**: LLM can make errors (missed ID 136 classification)
2. **Order matters**: Must collect all IDs before checking relationships
3. **Valve-to-valve exists**: Some valves point to other valves (ID 90)
4. **Orphaned IDs exist**: 14 stock IDs referenced in connections but no `10,` definition

---

## Remaining Issues

1. ✅ **Stock Detection**: FIXED (100% accuracy)
2. ⚠️  **Connection Extraction**: Missing 5 connections (valve-mediated)
3. ⚠️  **Polarity Detection**: 3 polarity differences

---

## Next Steps

**Iteration 2**: Fix connection extraction
- Handle valve-mediated connections (variable → valve → stock → flow)
- Resolve valve IDs to flow variable IDs
- Merge equation dependencies with sketch connections

**Iteration 3**: Fix polarity detection
- Check field[6]=43 for positive markers
- Handle negative signs in equations (`-Variable`)
- Preserve polarity through valve resolution

---

## Files Modified

- `tests/test_python_vs_llm_parser.py`: Fixed stock detection logic (lines 89-123)
- `tests/debug_stock_detection.py`: Created debug script
- `tests/debug_which_stocks_have_vars.py`: Created analysis script
- `tests/MDL_GROUND_TRUTH.md`: Documented ground truth analysis
