#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test different waypoint formats to figure out what Vensim actually expects.
"""

from pathlib import Path

# Read a real Vensim file and show all arrow formats
mdl_files = [
    "projects/sd_test/mdl/test.mdl",
    "projects/sd_test/mdl/enhanced/latest/test_enhanced.mdl",
    "tests/test_archetype_enhanced.mdl"
]

print("="*60)
print("ANALYZING VENSIM ARROW FORMATS")
print("="*60)

for mdl_file in mdl_files:
    path = Path(mdl_file)
    if not path.exists():
        continue

    print(f"\n\nFile: {mdl_file}")
    print("-"*60)

    content = path.read_text(encoding='utf-8')
    lines = content.split('\n')

    # Find arrows with waypoints (not 0,0)
    found_waypoints = False
    for i, line in enumerate(lines, 1):
        if line.startswith('1,'):
            # Check if it has waypoints
            if '1|(' in line and '1|(0,0)|' not in line:
                found_waypoints = True
                parts = line.split(',')
                arrow_id = parts[1] if len(parts) > 1 else '?'
                from_id = parts[2] if len(parts) > 2 else '?'
                to_id = parts[3] if len(parts) > 3 else '?'

                print(f"\nLine {i}: Arrow {arrow_id}: {from_id}→{to_id}")
                print(f"  Full line: {line[:120]}...")

                # Extract the waypoint part
                if ',,1|(' in line:
                    waypoint_section = line.split(',,')[1] if ',,' in line else ''
                    print(f"  Waypoint section: {waypoint_section}")

    if not found_waypoints:
        print("  (No curved arrows found in this file)")

print("\n" + "="*60)
print("HYPOTHESIS: ")
print("="*60)
print("""
Looking at the MDL rules, the format should be:
  ...,,...|(<x1>,<y1>)|(<x2>,<y2>)|...

But we're generating:
  ...,,1|(<x1>,<y1>)|1|(<x2>,<y2>)|...

The "1|" prefix might be wrong! Let me check the actual format...
""")
