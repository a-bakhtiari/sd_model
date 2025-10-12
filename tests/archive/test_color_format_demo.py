#!/usr/bin/env python3
"""Demonstrate correct color format for Vensim MDL files."""

import json
from pathlib import Path

# Example of correct color format discovered from Vensim-generated MDL
CORRECT_CONNECTION_FORMAT = "1,<id>,<from>,<to>,...,<color>,|||<label_color>,<polarity>|<points>|"
CORRECT_VARIABLE_FORMAT = "10,<id>,<name>,...,<border_color>,<fill_color>,|||<text_color>,..."

def demo():
    """Show the correct color format."""
    print("=" * 80)
    print("Vensim MDL Color Format Guide")
    print("=" * 80)

    print("\n1. CONNECTION COLOR FORMAT:")
    print("   Vensim generated: 1,24,23,1,0,0,0,0,1,192,0,251-2-128,|||0-0-0,1|(0,0)|")
    print("                                                    ^^^^^^^   ^^^^^^")
    print("                                                line color  label color")
    print("   Key: Must include |||<label_color> after the line color!")

    print("\n2. VARIABLE COLOR FORMAT:")
    print("   Vensim generated: 10,23,colored stock,...,252-102-255,0-0-0,|||0-0-0,...")
    print("                                              ^^^^^^^^^^^  ^^^^^   ^^^^^")
    print("                                           border color  fill   text color")

    print("\n3. COLOR EXAMPLES:")
    print("   - Green:   0-255-0")
    print("   - Red:     255-0-0")
    print("   - Blue:    0-0-255")
    print("   - Yellow:  255-255-0")
    print("   - Default: -1--1--1")

    print("\n4. OUR FIXED GENERATOR:")
    print("   Now generates: 1,20,2,17,1,0,43,0,0,192,0,0-255-0,|||0-0-0,1|(1653,468)|")
    print("   This matches Vensim's format! ✓")

    print("\n" + "=" * 80)
    print("The fix: Added ,|||0-0-0 after colors to match Vensim's format")
    print("=" * 80)

if __name__ == "__main__":
    demo()