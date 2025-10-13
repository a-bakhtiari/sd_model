# Vensim MDL — Surgical Parse/Edit Rules

**Purpose:** Enable parsing MDL files and making surgical edits (add/remove/update variables)

## Sections & Markers

```
{UTF-8}                     ; optional file header
...                         ; equations
\\\---/// Sketch information - do not modify anything except names
V<ver> <text>
*View <n>
$<view-params>
...
///---\                      ; end of sketch
```

**Header Line Details:**

- **`\\\---///` line:** Marks the beginning of sketch information. This line is repeated for each view in the model. Only the beginning `\\\---///` is significant; the rest can be any text (typically "Sketch information - do not modify anything except names").

- **`V<ver>` line:** Version code for format compatibility. Vensim versions 3, 4, and 5 all use `V300`. Vensim checks this to ensure the sketch information is in the expected format. Only the version code itself (e.g., `V300`) is significant.

- **`*View <name>` line:** Names the view. You can use any name you want, subject to a **30-character limit**.

- **`$<view-params>` line:** Defines view default settings (fonts, colors, zoom). See detailed format below.

## View Default Settings (`$` line)

The `$` line defines default font and color settings for the view. When font and color are not set for a specific object, these defaults are used.

**Format:**
```
$iniarrow,n2,face|size|attributes|color|shape|arrow|fill|background|ppix,ppiy,zoom,tf
```

**Field Descriptions:**

- **`iniarrow`:** Color of initial arrows in R-G-B format (e.g., `192-192-192`) or `0` for default
- **`n2`:** Reserved number (16-bit integer); must be `0`
- **`face`:** Font face name (e.g., `Times New Roman`)
- **`size`:** Font size in points (e.g., `12`)
- **`attributes`:** Font attributes, one or more of:
  - `B` = Bold
  - `U` = Underline
  - `S` = Strike-through
  - `I` = Italic
  - (leave empty for no attributes)
- **`color`:** Font color in R-G-B format (e.g., `0-0-0` for black)
- **`shape`:** Border color for shapes in R-G-B format
- **`arrow`:** Arrow color in R-G-B format (e.g., `0-0-255` for blue)
- **`fill`:** Fill color for shapes in R-G-B format; `-1--1--1` means no fill
- **`background`:** Background color for the sketch in R-G-B format; `-1--1--1` means use normal window background
- **`ppix`:** Pixels per inch in X direction on the display where model was last edited
- **`ppiy`:** Pixels per inch in Y direction on the display where model was last edited
- **`zoom`:** Zoom percentage for displaying the view (e.g., `100` for 100%; `5` means fit to screen)
- **`tf`:** Template flag
  - `0` = normal view
  - `1` = don't use template
  - `3` = is the template view

**Example:**
```
$192-192-192,0,Times New Roman|12||0-0-0|0-0-0|0-0-255|-1--1--1|-1--1--1|96,96,100,0
```
This defines: gray initial arrows, Times New Roman 12pt font, black text, black shapes, blue arrows, no fill, default background, 96 DPI, 100% zoom, normal view.

## Equation Blocks

**Structure (exact 4-line unit):**
```
<varname> = <expression>
~	<units-or-blank>
~	<doc-or-blank>
|
```

- Keep `~` line order; terminate with `|`
- `A FUNCTION OF(...)` accepted as expression

## Quoting Names

**Unquoted allowed:** letters, digits, spaces, underscores, hyphens, apostrophes

**Require double quotes if name contains:**
- Comma `,`
- Parentheses `()`
- Vertical bar `|`
- Double quote `"`
- Leading/trailing spaces
- Newlines

**Example:** `"Explicit Knowledge Transfer (Documentation, Contributor's Guides)"`

## Dependency Syntax

```
A FUNCTION OF( Var1, -Var2, Var3 )
```

- Comma-separated variable names
- Prefix `-` for negative relationship (no prefix or `+` for positive)
- Quote names with special chars (same rules as above)
- Whitespace/newlines inside `(...)` allowed
- Multiline: use `\` at end of line for continuation

## Sketch Records — Line Types

**CSV format with possible wrapped lines:**
- One record per object/connection
- Continuation lines start with `,`
- Only fields shown below are relevant; preserve others as-is

### `10,` — Variable node

```
10,<id>,<name>,<x>,<y>,<w>,<h>,<font_face>,<font_size>,<border_style>,...
```

- Field 2: `<id>` - unique integer
- Field 3: `<name>` - must exactly match equation variable name (including quotes)
- Field 4-5: `<x>,<y>` - pixel coordinates
- Field 6-7: `<w>,<h>` - width, height in pixels

### `1,` — Connection (arrow/link)

```
1,<id>,<from_id>,<to_id>,<dx>,<dy>,<angle>,<thickness>,<dash>,<alpha>,<curv>,...
...[,<label>],...|(<x,y>)[(<x,y>)...]|
```

- `<from_id>` and `<to_id>` reference existing variable/node IDs
- Final `|...|` holds bend-point coordinates; keep intact

### `11,` — Flow (rate valve)

```
11,<id>,<glyph_code>,<x>,<y>,<w>,<h>,...
```

- Positional glyph; no name field
- Keep IDs stable

### `12,` — Cloud (source/sink)

```
12,<id>,<cloud_code>,<x>,<y>,<w>,<h>,...
```

- Positional icon; no name field
- Keep IDs stable

## Colors

**Format:** `<r>-<g>-<b>` where each component (R, G, B) ranges from 0 to 255

**Default/Special Value:** `-1--1--1`
- In `$` line: Indicates "use default color" (system default)
- For `fill` in `$` line: Means no fill (transparent)
- For `background` in `$` line: Means use normal window background

**Usage Locations:**
- In the `$` view settings line (initial arrows, font, shape, arrow, fill, background colors)
- In individual sketch records (e.g., `10,` variable nodes can specify custom colors)

**Common colors:**
- Black: `0-0-0`
- White: `255-255-255`
- Red: `255-0-0`
- Green (additions): `0-255-0`
- Blue: `0-0-255`
- Orange (modifications): `255-165-0`
- Gray: `192-192-192`

**Important:** When editing sketch lines, change only the RGB token; do not alter field counts or positions

## Parsing Workflow

1. **Variables:** Scan equation blocks; collect `<varname>`
2. **Map to IDs:** In `10,` lines, match field 3 `<name>` to `<varname>`; store `<id>`
3. **Dependencies:** From equation expressions:
   - If `A FUNCTION OF(...)`, extract referenced names (and sign)
   - Else, parse normal expression as needed
4. **Edges:** In `1,` lines, use `<from_id>` → `<to_id>` to build graph

## Surgical Edits — Templates

### Add Variable

**Equation section:**
```
<New Var> = A FUNCTION OF()
~
~
|
```

**Sketch section:**
- Insert a `10,` record
- Choose unique `<id>` (max existing ID + 1)
- Set `<name>` to `<New Var>` (with quotes if needed)
- Pick reasonable `<x>,<y>,<w>,<h>` from position spec

**Optional connections:**
```
1,<new_link_id>,<id(Dep)>,<id(New Var)>,0,0,0,0,0,0,0,...|(<x,y>)|
```

### Update Equation (dependencies only)

Edit inside `A FUNCTION OF( ... )`:
- Add/remove variable names
- Adjust `+/-` prefix for relationship
- **Do not rename the LHS** `<varname>`

Mirror changes in `1,` links if maintaining visual connections.

### Remove Variable

1. Delete its 4-line equation block
2. Delete its `10,` record (matching `<name>`)
3. Delete all `1,` records where `<from_id>` or `<to_id>` equals removed ID
4. Remove from other equations' dependencies
5. Leave unrelated `11,`/`12,` records intact

## Integrity Rules

- Keep record ordering and field counts; never drop trailing commas/fields
- Preserve continuation structure and `|(<x,y>)...|` path segments
- Names must remain consistent between equations and `10,` records
- IDs are unique integers within the sketch
- Every equation needs matching `10,` line (and vice versa)

## Common Gotchas

- **Equation ↔ Sketch sync:** Every equation needs matching `10,` line (and vice versa)
- **Unique IDs:** IDs must be unique integers, typically sequential
- **Field counts:** Don't change number of fields in sketch lines when editing
- **Quote consistency:** Quotes in sketch must match equation exactly
- **Dependencies:** When removing variable, update all equations that reference it



Here is the details from vensim's documentation:

When models are stored in .mdl format the sketch information is appended at the end.  This information is not intended for user modification, but a brief overview of its structure is useful.  Consider the following model:



The sketch information for this appears as:

\\\---/// Sketch information - do not modify anything except names

V300  Do not put anything below this section - it will be ignored

*View 1

$192-192-192,0,Times New Roman|12||0-0-0|0-0-0|0-0-255|-1--1--1|-1--1--1|96,96,100,0

10,1,Population,275,69,40,20,3,3,0,0,0,0,0,0

12,2,48,91,71,8,8,0,3,0,0,-1,0,0,0

1,3,5,1,4,0,0,22,0,0,0,-1--1--1,,1|(204,71)|

1,4,5,2,100,0,0,22,0,0,0,-1--1--1,,1|(130,71)|

11,5,48,167,71,6,8,34,3,0,0,1,0,0,0

10,6,births,167,90,19,11,40,3,0,0,-1,0,0,0

12,7,48,487,70,8,8,0,3,0,0,-1,0,0,0

1,8,10,7,4,0,0,22,0,0,0,-1--1--1,,1|(441,70)|

1,9,10,1,100,0,0,22,0,0,0,-1--1--1,,1|(353,70)|

11,10,48,397,70,6,8,34,3,0,0,1,0,0,0

10,11,deaths,397,89,22,11,40,3,0,0,-1,0,0,0

10,12,birth rate,99,118,29,11,8,3,0,0,0,0,0,0

10,13,average lifetime,508,104,49,11,8,3,0,0,0,0,0,0

1,14,12,6,0,0,0,0,0,64,0,-1--1--1,,1|(130,104)|

1,15,13,11,0,0,0,0,0,64,0,-1--1--1,,1|(445,95)|

12,16,0,269,22,37,9,8,4,0,0,-1,0,0,0

Comment

1,17,1,5,1,0,0,0,0,64,0,-1--1--1,,1|(203,31)|

1,18,1,10,1,0,0,0,0,64,0,-1--1--1,,1|(349,27)|

The first line beginning \\\ marks the beginning of sketch information.  This line is repeated for each view.  Only the beginning \\\---/// is significant.

The second line beginning V300 is a version code.  Vensim versions 5,4 and 3 all use the same version code (300).  Vensim tests this to be sure the information will be in the expected format.  Only the version code itself (V300) is significant.

The third line beginning with a * names the view.  You can use any name you want subject to the length limitation of 30 characters.

The fourth line beginning $ defines the views default font and color settings for the view (when font and color are not set for a specific object the defaults are used).  This is in the format

$iniarrow,n2,face|size|attributes|color|shape|arrow|fill|background|ppix,ppiy,zoom,tf

With

•	iniarrow the color of initial arrows  or 0.
•	n2 a reserved number (16 bit integer) must be 0.
•	face the name of the font face as in Times New Roman.
•	size the size in points of the font.
•	attributes  one or more of BUSI for bold underline strike-through and italic.
•	color the color of the font.  This and all the colors that follow are in R-G-B format where each of R, G, and B ranges from 0 to 255.  The color -1--1--1 is used to indicate a default color.
•	shape the color of shapes.
•	arrow the color of arrows.
•	fill the fill color for shapes. -1--1--1 is used to indicate no fill.
•	background the background color for the sketch. -1--1--1 is used to indicate that a normal window background should be used.
•	ppix the number of pixels per inch in the x direction on the display the model was last edited with.
•	ppiy the number of pixels per inch in the y direction on the display the model was last edited with.
•	zoom the percentage zoom for displaying the view (5 percent means fit to screen)
•	tf the template flag 0 is normal, 1 means don’t use the template and 3 means it is the template view.