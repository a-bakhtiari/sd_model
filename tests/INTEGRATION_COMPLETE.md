# Recreation Mode Integration - Complete! ✅

## What Was Implemented

### 1. Side-by-Side Layout
- Original model stays on LEFT (X: 0-2000)
- Theory model appears on RIGHT (X: 3000+)
- User can manually delete old variables in Vensim if desired
- Simple, pragmatic approach

### 2. Grid-Based Positioning
- NO expensive LLM Step 3 repositioning
- Fast, deterministic grid layout
- Variables organized by process clusters
- 5 columns per cluster, clean spacing

### 3. LLM Cluster Spatial Positioning
- Step 2 now outputs `cluster_positions`: `{"Process Name": [row, col]}`
- LLM suggests high-level 2D grid based on inter-cluster connections
- Connected clusters positioned near each other → shorter arrows
- 2-3 columns, multiple rows
- Fallback to vertical stacking if cluster_positions missing

## How to Use

### Command Line
```bash
# Recreation mode (side-by-side with grid positioning)
python main.py --project sd_test --theory-enhancement --decomposed-theory --recreate-model

# Regular enhancement mode (adds to existing model)
python main.py --project sd_test --theory-enhancement --decomposed-theory
```

### What Happens

**Step 1: Strategic Planning**
- Identifies theories, creates process narratives
- Maps inter-cluster connections (feeds_into, receives_from, feedback_loop)

**Step 2: Concrete Generation** (NEW!)
- Generates variables and connections for each process
- **Outputs cluster_positions** based on inter-cluster connections
- Example: `{"Socialization": [0,0], "Externalization": [0,1], ...}`

**Step 3: MDL Creation**
- If `--recreate-model`: Creates side-by-side layout (original left, theory right)
- Uses cluster_positions for 2D grid (connected clusters near each other)
- Grid layout: 1500px × 800px per cluster
- Variables within cluster: 5-column grid, 250px × 150px spacing

## Test Files

### Visual Verification Tests
1. **test_recreation_visual.mdl** - Vertical stacking (fallback)
2. **test_recreation_cluster_positioning.mdl** - 2D grid layout (new)

### Test Scripts
```bash
# Run both tests
python3 tests/test_recreation_visual.py
python3 tests/test_recreation_cluster_positioning.py
```

## Example Output Structure

```
DIAGRAM LAYOUT (recreation mode):
┌────────────────────┬────────────────────────────────────┐
│ ORIGINAL MODEL     │    THEORY MODEL (GRID)             │
│ (X: 0-2000)        │    (X: 3000+)                      │
│                    │                                    │
│ 9 original vars    │  ┌─────────────┬─────────────┐    │
│ stay untouched     │  │ Cluster A   │ Cluster B   │    │
│                    │  │ (Row 0,     │ (Row 0,     │    │
│                    │  │  Col 0)     │  Col 1)     │    │
│                    │  ├─────────────┼─────────────┤    │
│                    │  │ Cluster C   │ Cluster D   │    │
│                    │  │ (Row 1,     │ (Row 1,     │    │
│                    │  │  Col 0)     │  Col 1)     │    │
│                    │  └─────────────┴─────────────┘    │
└────────────────────┴────────────────────────────────────┘
```

## Benefits

✅ **Original model preserved** - Can compare old vs new side-by-side
✅ **Fast execution** - No expensive LLM repositioning (Step 3 skipped)
✅ **Connection-aware layout** - Connected clusters positioned adjacently
✅ **Clear visual flow** - 2D grid with shorter arrows between related clusters
✅ **Backward compatible** - Old JSON files without cluster_positions use vertical fallback
✅ **User control** - Can manually delete old variables after verification

## Files Changed

1. `src/sd_model/pipeline/theory_concretization.py`
   - Added cluster_positions to Step 2 JSON output schema
   - Brief LLM instruction: "Place connected processes near each other"

2. `src/sd_model/mdl_creator.py`
   - Reads cluster_positions from Step 2 output
   - Calculates 2D grid layout (row/col → pixel coordinates)
   - Fallback to vertical stacking if cluster_positions missing

3. `src/sd_model/mdl_text_patcher.py`
   - Already calls mdl_creator.create_mdl_from_scratch() when recreate_mode=True
   - No changes needed - integration automatic!

## Current Status

🟢 **COMPLETE AND INTEGRATED**

- Step 2 prompt updated ✅
- Grid layout implemented ✅
- Tests created ✅
- Visually verified ✅
- Integrated to main workflow ✅
- Backward compatible ✅

Ready to use with: `python main.py --project PROJECT --theory-enhancement --decomposed-theory --recreate-model`
