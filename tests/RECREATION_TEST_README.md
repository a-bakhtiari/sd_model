# Recreation Mode Visual Test

## Test File
**Location**: `tests/test_recreation_visual.mdl`

## How to Verify

1. **Open in Vensim**: Open `tests/test_recreation_visual.mdl` in Vensim

2. **Check Side-by-Side Layout**:
   - **LEFT side (X: 0-2000)**: Should show original 9 variables
     - New Contributors
     - Core Developer
     - Experienced Contributors
     - Skill up
     - Promotion Rate
     - Developer's Turnover
     - Implicit Knowledge Transfer (Mentorship)
     - Explicit Knowledge Transfer (Documentation, Contributor's Guides)
     - colored stock
   
   - **RIGHT side (X: 3000+)**: Should show 45 theory-generated variables
     - Organized in 5 columns (X: 3000, 3250, 3500, 3750, 4000)
     - Grouped by 5 process clusters vertically
     - 200px gaps between process clusters

3. **What to Look For**:
   - ✅ Original variables untouched on left
   - ✅ Theory variables in neat grid on right
   - ✅ Clear visual separation between old and new
   - ✅ Process clusters grouped together
   - ❌ NO repositioning of original variables
   - ❌ NO overlapping variables

## Process Clusters (Top to Bottom)
1. **Knowledge Socialization** (9 variables)
2. **Knowledge Externalization** (9 variables)
3. **Knowledge Combination** (9 variables)
4. **Knowledge Internalization** (9 variables)
5. **Community Spiral** (9 variables)

## Technical Details
- Grid layout: 5 columns × multiple rows
- Column spacing: 250px
- Row spacing: 150px
- Process gap: 200px
- NO LLM positioning (fast, cheap, deterministic)
- NO Step 3 expensive repositioning

## Re-run Test
```bash
python3 tests/test_recreation_visual.py
```

This will regenerate `tests/test_recreation_visual.mdl` using the existing theory JSON.
