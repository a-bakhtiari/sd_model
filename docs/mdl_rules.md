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

**Format:** `<r>-<g>-<b>` where each is 0-255

**Default:** `-1--1--1`

**Common colors:**
- Green border (additions): `0-255-0`
- Orange border (modifications): `255-165-0`
- Red border: `255-0-0`

**In sketch lines:** Change only the RGB token; do not alter field counts

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
