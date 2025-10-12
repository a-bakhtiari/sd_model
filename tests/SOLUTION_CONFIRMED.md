# SOLUTION CONFIRMED: Vensim Curve Format

## The Discovery

**Field 10 in the arrow line controls whether curves are displayed!**

## Arrow Line Format

```
1,<id>,<from>,<to>,<dx>,<dy>,<angle>,<thickness>,<dash>,<alpha>,<curv>,...
   1     2       3      4     5     6        7            8        9       10
```

Field 10 = `<alpha>` or curve display flag

## The Magic Values

### For CURVED arrows:
```
1,20,1,2,1,0,0,0,0,64,0,-1--1--1,,1|(400,150)|
                   ^^
                   Field 10 = 64 → CURVED
```

### For STRAIGHT arrows:
```
1,20,1,2,1,0,0,0,0,192,0,-1--1--1,,1|(400,150)|
                    ^^^
                    Field 10 = 192 → STRAIGHT
```

## Complete Requirements for Curves

To create a curved arrow in Vensim MDL:

1. **Field 5 = 1** (curve flag - optional but good practice)
2. **Field 10 = 64** (**CRITICAL** - this makes it curve!)
3. **Single control point**: `1|(x,y)|` format
4. Control point should be offset from straight line path
5. **IMPORTANT**: Flow arrows (connected to Type 11 valves) should NEVER be curved - keep them straight with field 10 = 192

## Why Our Code Didn't Work

We were generating:
```
1,20,2,17,1,0,43,0,0,192,0,-1--1--1,,1|(1600,535)|
                       ^^^
                       192 = straight!
```

We need to generate:
```
1,20,2,17,1,0,43,0,0,64,0,-1--1--1,,1|(1600,535)|
                      ^^
                      64 = curved!
```

## The Fix

In `_update_arrow_waypoints()` function:

```python
if waypoints:
    # Set field 5 to 1 (curve flag)
    parts[4] = '1'

    # Set field 10 to 64 (CRITICAL - enables curve display!)
    parts[9] = '64'  # Index 9 = field 10 (0-indexed)

    # Calculate single control point
    if len(waypoints) >= 2:
        control_x = (waypoints[0][0] + waypoints[-1][0]) / 2
        control_y = (waypoints[0][1] + waypoints[-1][1]) / 2
    else:
        control_x, control_y = waypoints[0]

    control_point = f"1|({int(control_x)},{int(control_y)})|"
    parts.append(control_point)
```

## Test Files

- ✓ `test_field10_64.mdl` - CURVED (field 10 = 64)
- ✗ `test_single_control_point.mdl` - straight (field 10 = 192)
- ✗ `test_exact_format.mdl` - straight (field 10 = 192)

## Next Steps

1. Update `src/sd_model/mdl_full_relayout.py` → `_update_arrow_waypoints()`
2. Set field 10 to 64 when applying waypoints
3. Use single control point (midpoint of path)
4. Test with full pipeline

## Additional Notes

- Field 10 might be "alpha" (transparency) in docs, but 64 vs 192 clearly controls curve display
- Single control point is sufficient for smooth curves
- Multiple waypoints `1|(x1,y1)|1|(x2,y2)|` don't create curves without field 10 = 64
