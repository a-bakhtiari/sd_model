# SOLUTION FOUND: Vensim Curve Format

## The Problem

We were generating arrows like this:
```
1,3,1,2,0,0,0,0,0,64,0,-1--1--1,,1|(500,200)|1|(500,400)|
        ^                           ^-- Two waypoints
        |
        Field 5 = 0 (straight line)
```

But Vensim expects curves like this:
```
1,3,1,2,1,0,0,0,0,64,0,-1--1--1,,1|(485,212)|
        ^                       ^-- One control point
        |
        Field 5 = 1 (curved line!)
```

## Key Findings

1. **Field 5 is a curve flag**:
   - `0` = straight line (even with waypoints)
   - `1` = curved line (uses control point)

2. **Waypoints vs Control Points**:
   - Multiple waypoints `1|(x1,y1)|1|(x2,y2)|` create orthogonal (90-degree corner) paths
   - Single control point `1|(x,y)|` creates a smooth Bezier curve

3. **What we need to do**:
   - Set field 5 to `1` for curved arrows
   - Use a SINGLE control point, not multiple waypoints
   - Calculate the control point for a smooth curve

## Vensim Arrow Format Fields

```
1,<id>,<from>,<to>,<dx>,<dy>,<angle>,<thickness>,<dash>,<alpha>,<curv>,...
                   ^^^^
                   Field 5 = curve flag!
```

Based on user's manual edit:
- Field 5: `1` = curved line, `0` = straight line
- dx/dy might actually be "delta" offsets or curve flags

## Next Steps

1. **Update `_update_arrow_waypoints()` function**:
   - Set field 5 to `1` when waypoints are generated
   - Calculate a SINGLE control point instead of multiple waypoints
   - Use midpoint of the path as control point

2. **Control point calculation**:
   - For path from (x1,y1) to (x2,y2)
   - Simple approach: Use midpoint between source and target
   - Better approach: Use midpoint of the obstacle-avoiding path

3. **Test**:
   - Generate curves with field 5 = 1
   - Use single control point
   - Verify curves appear in Vensim

## Example Fix

Instead of:
```python
waypoint_str = '1|(' + ')|1|('.join([f"{int(x)},{int(y)}" for x, y in waypoints]) + ')|'
```

Use:
```python
# Calculate control point (midpoint of first and last waypoint)
if len(waypoints) >= 2:
    mid_x = (waypoints[0][0] + waypoints[-1][0]) / 2
    mid_y = (waypoints[0][1] + waypoints[-1][1]) / 2
    control_point = f"1|({int(mid_x)},{int(mid_y)})|"
else:
    control_point = f"1|({int(waypoints[0][0])},{int(waypoints[0][1])})|"

# Also need to set field 5 to 1!
parts[4] = '1'  # Set curve flag
```

## Test Files Created

1. `obvious_curve_test.mdl` - User manually edited to show correct curve format
2. Need to update our waypoint generation to match this format
