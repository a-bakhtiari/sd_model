#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test if edge routing is being called in the pipeline.

Trace through the exact flow from orchestrator → mdl_text_patcher → mdl_full_relayout
"""

from pathlib import Path

def check_pipeline_integration():
    """Check if full relayout with edge routing is integrated properly."""
    print("="*60)
    print("CHECKING PIPELINE INTEGRATION")
    print("="*60)

    # Check orchestrator.py
    orch_path = Path("src/sd_model/orchestrator.py")
    orch_content = orch_path.read_text()

    print("\n1. Checking orchestrator.py...")
    if "use_full_relayout" in orch_content:
        print("  ✓ use_full_relayout flag exists")
    else:
        print("  ✗ use_full_relayout flag NOT FOUND")

    if "clustering_scheme" in orch_content:
        print("  ✓ clustering_scheme handling exists")
    else:
        print("  ✗ clustering_scheme handling NOT FOUND")

    # Check mdl_text_patcher.py
    patcher_path = Path("src/sd_model/mdl_text_patcher.py")
    patcher_content = patcher_path.read_text()

    print("\n2. Checking mdl_text_patcher.py...")
    if "from .mdl_full_relayout import reposition_entire_diagram" in patcher_content:
        print("  ✓ Imports reposition_entire_diagram")
    else:
        print("  ✗ Does NOT import reposition_entire_diagram")

    if "full_relayout_flag" in patcher_content:
        print("  ✓ Uses full_relayout_flag")
    else:
        print("  ✗ Does NOT use full_relayout_flag")

    if "reposition_entire_diagram(" in patcher_content:
        print("  ✓ Calls reposition_entire_diagram()")
    else:
        print("  ✗ Does NOT call reposition_entire_diagram()")

    # Check mdl_full_relayout.py
    relayout_path = Path("src/sd_model/mdl_full_relayout.py")
    relayout_content = relayout_path.read_text()

    print("\n3. Checking mdl_full_relayout.py...")
    if "from .edge_routing import route_all_connections" in relayout_content:
        print("  ✓ Imports route_all_connections")
    else:
        print("  ✗ Does NOT import route_all_connections")

    if "waypoint_map = route_all_connections(" in relayout_content:
        print("  ✓ Calls route_all_connections()")
    else:
        print("  ✗ Does NOT call route_all_connections()")

    if "_update_arrow_waypoints(" in relayout_content:
        print("  ✓ Has _update_arrow_waypoints function")
    else:
        print("  ✗ Does NOT have _update_arrow_waypoints function")

    print("\n4. Checking if full relayout is actually used...")

    # Count occurrences
    import re

    # In orchestrator: how many times is reposition_entire_diagram called?
    orch_calls = len(re.findall(r'reposition_entire_diagram', orch_content))
    print(f"  orchestrator.py mentions 'reposition_entire_diagram': {orch_calls} times")

    # In patcher: is full_relayout actually triggered?
    patcher_if_relayout = len(re.findall(r'if full_relayout', patcher_content))
    print(f"  mdl_text_patcher.py checks 'if full_relayout': {patcher_if_relayout} times")

    # In relayout: is edge routing actually called?
    relayout_edge_calls = len(re.findall(r'route_all_connections', relayout_content))
    print(f"  mdl_full_relayout.py calls 'route_all_connections': {relayout_edge_calls} times")

    print("\n5. Checking CLI flags...")
    cli_path = Path("src/sd_model/cli.py")
    if cli_path.exists():
        cli_content = cli_path.read_text()

        if "--full-relayout" in cli_content:
            print("  ✓ --full-relayout flag exists in CLI")

            # Check if it's passed to orchestrator
            if "use_full_relayout" in cli_content:
                print("  ✓ CLI passes use_full_relayout to pipeline")
            else:
                print("  ✗ CLI does NOT pass use_full_relayout to pipeline")
        else:
            print("  ✗ --full-relayout flag NOT in CLI")

    print("\n" + "="*60)
    print("DIAGNOSIS:")
    print("="*60)

    # Hypothesis: edge routing code exists but isn't being called
    print("\nBased on the checks above, the issue is likely:")
    print("  A) Full relayout is not being triggered in the pipeline")
    print("  B) Edge routing is being called but waypoints are not being written")
    print("  C) Waypoints are being written but to wrong location/format")

    print("\nTo confirm, check the run log for these messages:")
    print("  - 'Calculating smart arrow routes to avoid overlaps...'")
    print("  - '✓ Routed X arrows with smart waypoints to avoid overlaps'")
    print("\nIf these messages DON'T appear, then full relayout is not running.")
    print("If they DO appear but waypoints are missing, then writing is broken.")


if __name__ == '__main__':
    check_pipeline_integration()
