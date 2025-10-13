# Cluster Spatial Positioning Test

## Summary
Added LLM-based cluster positioning to Step 2 so connected clusters are positioned near each other in the diagram (shorter arrows, clearer flow).

## Changes

### 1. Step 2 Prompt Updated
**File**: `src/sd_model/pipeline/theory_concretization.py`

Added `cluster_positions` to JSON output schema:
```json
{
  "processes": [...],
  "cluster_positions": {
    "Process Name 1": [0, 0],
    "Process Name 2": [0, 1],
    "Process Name 3": [1, 0]
  }
}
```

**LLM instruction**:
- Format: `{"Process Name": [row, col]}` - simple grid coordinates
- Place connected processes near each other (same row or adjacent) for shorter arrows
- Use 2-3 columns, multiple rows as needed

### 2. Grid Layout Implementation
**File**: `src/sd_model/mdl_creator.py`

Reads `cluster_positions` from Step 2 and calculates pixel coordinates:
- **CLUSTER_WIDTH** = 1500px (horizontal space per cluster)
- **CLUSTER_HEIGHT** = 800px (vertical space per cluster)
- **Base position**: `(X_OFFSET + col*1500, 100 + row*800)`
- **Variables within cluster**: 5-column grid, 250px × 150px spacing

Fallback: If `cluster_positions` missing (old JSON files), uses vertical stacking.

## Test Files

### Test 1: Vertical Stacking (Original)
**File**: `tests/test_recreation_visual.mdl`
- No cluster_positions → vertical stacking
- 5 clusters stacked top to bottom
- Simple but may have long arrows between clusters

### Test 2: 2D Grid Positioning (New)
**File**: `tests/test_recreation_cluster_positioning.mdl`
- Manually added cluster_positions to simulate LLM output
- 2×3 grid layout: 2 columns, 3 rows
- Connected clusters positioned adjacently

**Expected positions**:
```
Row 0 (Y ~100):
  - Knowledge Socialization    (X ~3000, Col 0)
  - Knowledge Externalization  (X ~4500, Col 1)

Row 1 (Y ~900):
  - Knowledge Combination      (X ~3000, Col 0)
  - Knowledge Internalization  (X ~4500, Col 1)

Row 2 (Y ~1700):
  - Community Core Development (X ~3000, Col 0)
```

## Visual Verification

1. **Open both test files in Vensim**:
   - `test_recreation_visual.mdl` (vertical stacking)
   - `test_recreation_cluster_positioning.mdl` (2D grid)

2. **Compare layouts**:
   - Vertical: All clusters in single column (may have long arrows)
   - 2D Grid: Clusters spread across 2 columns (shorter arrows between connected clusters)

3. **Check cluster grouping**:
   - Each cluster's 9 variables should be in tight 5-column grid
   - Variables within cluster: X spacing ~250px, Y spacing ~150px
   - Clusters should have ~1500px horizontal, ~800px vertical separation

## Integration to Main Workflow

Once you verify the 2D grid layout looks good:

1. **Future Step 2 runs will include cluster_positions** automatically (LLM will suggest positions based on inter-cluster connections from Step 1)

2. **Old JSON files will still work** (fallback to vertical stacking if cluster_positions missing)

3. **No changes needed to main workflow** - it will automatically use cluster_positions if present

## Re-run Tests

```bash
# Original vertical stacking test
python3 tests/test_recreation_visual.py

# New 2D grid positioning test
python3 tests/test_recreation_cluster_positioning.py
```

## Next Steps

1. ✅ Visually verify `test_recreation_cluster_positioning.mdl` in Vensim
2. ⏳ If layout looks good, run main workflow to test with fresh LLM-generated cluster_positions
3. ⏳ Compare diagram readability: vertical stacking vs. connection-aware 2D grid
