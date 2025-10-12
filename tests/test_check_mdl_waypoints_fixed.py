#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIXED VERSION: Check if waypoints are actually present in the generated MDL file.

Bug fix: Waypoints contain commas, so we need to join the parts back together.
"""

from pathlib import Path
import re


def analyze_mdl_waypoints(mdl_path):
    """Analyze waypoints in an MDL file."""
    print(f"\nAnalyzing: {mdl_path}")
    print("="*60)

    if not Path(mdl_path).exists():
        print(f"✗ File not found: {mdl_path}")
        return

    content = Path(mdl_path).read_text(encoding='utf-8')
    lines = content.split('\n')

    # Find all arrow lines (Type 1)
    arrows = []
    for i, line in enumerate(lines, 1):
        if line.startswith('1,'):
            parts = line.split(',')
            if len(parts) > 3:
                try:
                    arrow_id = int(parts[1])
                    from_id = int(parts[2])
                    to_id = int(parts[3])

                    # Find waypoint section - everything after part 13 that contains "1|("
                    # Need to JOIN parts because waypoints contain commas!
                    waypoint_parts = parts[13:]
                    waypoint_section = ','.join(waypoint_parts) if waypoint_parts else None

                    # Parse waypoints from the full section
                    waypoints = []
                    if waypoint_section:
                        # Extract all coordinates from format: 1|(x1,y1)|1|(x2,y2)|...
                        coords = re.findall(r'\((\d+),(\d+)\)', waypoint_section)
                        waypoints = [(int(x), int(y)) for x, y in coords]
                        # Filter out (0,0) which means no waypoint
                        waypoints = [w for w in waypoints if w != (0, 0)]

                    arrows.append({
                        'line': i,
                        'arrow_id': arrow_id,
                        'from_id': from_id,
                        'to_id': to_id,
                        'waypoints': waypoints,
                        'waypoint_section': waypoint_section[:100] if waypoint_section else None  # Truncate for display
                    })
                except (ValueError, IndexError) as e:
                    pass

    print(f"\nTotal arrows found: {len(arrows)}")

    # Categorize arrows
    with_waypoints = [a for a in arrows if len(a['waypoints']) > 0]
    without_waypoints = [a for a in arrows if len(a['waypoints']) == 0]

    print(f"  With waypoints (curved): {len(with_waypoints)}")
    print(f"  Without waypoints (straight): {len(without_waypoints)}")

    if with_waypoints:
        print(f"\n✓ Arrows WITH waypoints (curved):")
        for arrow in with_waypoints[:10]:  # Show first 10
            print(f"  Line {arrow['line']}: Arrow {arrow['from_id']}→{arrow['to_id']} - {len(arrow['waypoints'])} waypoints")
            for wp in arrow['waypoints']:
                print(f"    Waypoint at: {wp}")

    if without_waypoints:
        print(f"\n○ Arrows WITHOUT waypoints (straight):")
        count_shown = 0
        for arrow in without_waypoints:
            if count_shown < 10:
                print(f"  Line {arrow['line']}: Arrow {arrow['from_id']}→{arrow['to_id']} - straight line")
                count_shown += 1

    # Summary
    if len(with_waypoints) == 0 and len(arrows) > 0:
        print(f"\n⚠ WARNING: No waypoints found!")
        print(f"  All {len(arrows)} arrows are straight lines.")
    elif len(with_waypoints) > 0:
        percent = (len(with_waypoints) / len(arrows)) * 100
        print(f"\n✓ Edge routing IS working!")
        print(f"  {len(with_waypoints)} out of {len(arrows)} arrows have waypoints ({percent:.1f}%)")

    return {
        'total': len(arrows),
        'with_waypoints': len(with_waypoints),
        'without_waypoints': len(without_waypoints)
    }


if __name__ == '__main__':
    print("="*60)
    print("MDL WAYPOINT ANALYZER (FIXED VERSION)")
    print("Checks if waypoints are actually in the generated MDL files")
    print("="*60)

    # Check the latest enhanced MDL file
    latest_mdl = Path("projects/sd_test/mdl/enhanced/latest/test_enhanced.mdl")

    if latest_mdl.exists():
        results = analyze_mdl_waypoints(latest_mdl)
    else:
        print(f"\n✗ Latest MDL not found at: {latest_mdl}")
        print(f"\nSearching for recent MDL files...")

        enhanced_dir = Path("projects/sd_test/mdl/enhanced")
        if enhanced_dir.exists():
            mdl_files = sorted(enhanced_dir.glob("*/test*.mdl"), key=lambda p: p.stat().st_mtime, reverse=True)
            if mdl_files:
                print(f"\nFound {len(mdl_files)} MDL files. Checking most recent:")
                results = analyze_mdl_waypoints(mdl_files[0])
            else:
                print("No MDL files found")

    print("\n" + "="*60)
    print("To run: python3 tests/test_check_mdl_waypoints_fixed.py")
    print("="*60)
