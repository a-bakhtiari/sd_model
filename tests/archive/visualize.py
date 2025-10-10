import matplotlib.pyplot as plt
import matplotlib.patches as patches
import re

# The sketch information from your .mdl file
sketch_data = """
*View 1
$-1--1--1,0,|12||-1--1--1|-1--1--1|-1--1--1|-1--1--1|-1--1--1|96,96,67,2
10,1,New Contributors,1257,581,66,26,3,3,0,0,-1,0,0,0,0,0,0,0,0,0
10,2,Core Developer,1684,584,46,26,3,3,0,0,-1,0,0,0,0,0,0,0,0,0
12,3,48,1861,584,10,8,0,3,0,0,-1,0,0,0,0,0,0,0,0,0
1,4,6,2,100,0,0,22,0,192,0,-1--1--1,,1|(1757,584)|
1,5,6,3,4,0,0,22,0,192,0,-1--1--1,,1|(1823,584)|
11,6,0,1790,584,6,8,34,3,0,0,1,0,0,0,0,0,0,0,0,0
10,7,Developer's Turnover,1790,618,56,26,40,3,0,0,-1,0,0,0,0,0,0,0,0,0
10,8,Experienced Contributors,1475,584,66,26,3,3,0,0,-1,0,0,0,0,0,0,0,0,0
1,9,11,1,100,0,0,22,0,192,0,-1--1--1,,1|(1342,585)|
1,10,11,8,4,0,0,22,0,192,0,-1--1--1,,1|(1391,585)|
11,11,0,1368,585,6,8,34,3,0,0,1,0,0,0,0,0,0,0,0,0
10,12,Skill up,1368,619,46,26,40,3,0,0,-1,0,0,0,0,0,0,0,0,0
1,13,15,8,100,0,0,22,0,192,0,-1--1--1,,1|(1563,583)|
1,14,15,2,4,0,0,22,0,192,0,-1--1--1,,1|(1617,583)|
11,15,0,1591,583,6,8,34,3,0,0,1,0,0,0,0,0,0,0,0,0
10,16,Promotion Rate,1591,617,46,26,40,3,0,0,-1,1,0,0,0,0,0,0,0,0
10,17,"Implicit Knowledge Transfer (Mentorship)",1535,413,57,26,8,3,0,0,-1,0,0,0,0,0,0,0,0,0
1,18,17,11,0,0,0,0,0,192,0,-1--1--1,,1|(0,0)|
1,19,17,15,0,0,43,0,0,192,0,-1--1--1,,1|(0,0)|
1,20,2,17,1,0,43,0,0,192,0,-1--1--1,,1|(1653,468)|
10,21,"Explicit Knowledge Transfer (Documentation, Contributor's Guides)",1274,404,91,27,8,3,0,0,-1,0,0,0,0,0,0,0,0,0
1,22,21,11,0,0,0,0,0,192,0,-1--1--1,,1|(0,0)|
"""

# --- 1. Parse the sketch data ---
elements = {}
parser_regex = re.compile(r'\"[^\"]*\"|[^,]+') 

for line in sketch_data.strip().split('\n'):
    if not line or not line[0].isdigit():
        continue
    
    parts = parser_regex.findall(line)
    elem_type = int(parts[0])
    uid = int(parts[1])
    
    if elem_type == 10:
        elements[uid] = {
            'type': 'box', 'name': parts[2].strip('"'),
            'pos': (int(parts[3]), int(parts[4])),
            'size': (int(parts[5]), int(parts[6]))
        }
    elif elem_type == 11:
        elements[uid] = {
            'type': 'valve', 'pos': (int(parts[3]), int(parts[4]))
        }
    elif elem_type == 12:
         elements[uid] = {
            'type': 'cloud', 'pos': (int(parts[3]), int(parts[4]))
        }
    elif elem_type in [1, 2]:
        elements[uid] = {
            'type': 'arrow', 'from': int(parts[2]), 'to': int(parts[3])
        }

# --- 2. Setup the Matplotlib Canvas ---
fig, ax = plt.subplots(figsize=(16, 8))

# *** THIS IS THE CORRECTED SECTION ***
# Only get coordinates from elements that HAVE a 'pos' key
all_x = [v['pos'][0] for v in elements.values() if 'pos' in v]
all_y = [v['pos'][1] for v in elements.values() if 'pos' in v]

ax.set_xlim(min(all_x) - 100, max(all_x) + 100)
ax.set_ylim(min(all_y) - 100, max(all_y) + 100)
ax.invert_yaxis() 
ax.set_aspect('equal', adjustable='box')
ax.axis('off')

# --- 3. Draw all elements ---
# (This section remains unchanged)
for uid, elem in elements.items():
    if elem['type'] == 'box':
        x, y = elem['pos']
        w, h = elem['size']
        box = patches.Rectangle((x - w/2, y - h/2), w, h, linewidth=1, edgecolor='black', facecolor='white', zorder=3)
        ax.add_patch(box)
        ax.text(x, y, elem['name'], ha='center', va='center', fontsize=9, wrap=True, zorder=4)
    elif elem['type'] == 'valve':
        x, y = elem['pos']
        circle = patches.Circle((x, y), 8, linewidth=1, edgecolor='black', facecolor='white', zorder=2)
        ax.add_patch(circle)
    elif elem['type'] == 'cloud':
        x, y = elem['pos']
        ax.text(x, y, "☁", ha='center', va='center', fontsize=24, color='gray', zorder=2)
    elif elem['type'] == 'arrow':
        try:
            start_pos = elements[elem['from']]['pos']
            end_pos = elements[elem['to']]['pos']
            arrow = patches.FancyArrowPatch(start_pos, end_pos,
                                            arrowstyle='->,head_length=8,head_width=5',
                                            connectionstyle="arc3,rad=0.1",
                                            color='gray',
                                            linewidth=1.2,
                                            zorder=1)
            ax.add_patch(arrow)
        except KeyError:
            print(f"Warning: Could not draw arrow {uid}. Missing source/destination element.")

plt.title("Exact Recreation of Vensim Diagram")
plt.show()