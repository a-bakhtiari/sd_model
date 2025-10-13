# SISO (Single-Input, Single-Output) Process Architecture

## Design Principle

**Each process module MUST have EXACTLY ONE input and EXACTLY ONE output.**

This creates the cleanest possible pipeline architecture where:
- Each process transforms ONE input into ONE output
- Information flows in a clean linear pipeline: A → B → C → D
- Process boundaries are crystal clear
- No ambiguity about data flow
- Easiest to understand, maintain, and debug

---

## SISO Pattern

```
Process A:
  Input: (external source or previous process)
  Internal: Stocks, Flows, Auxiliaries
  Output: "Process A Result" → ONE downstream process

Process B:
  Input: "Process A Result" → ONE input variable
  Internal: Processing logic
  Output: "Process B Result" → ONE downstream process

Process C:
  Input: "Process B Result" → ONE input variable
  Internal: Processing logic
  Output: "Process C Result" → ONE downstream process
```

**Result**: Clean pipeline A → B → C

---

## SECI Example

### Linear Pipeline with Feedback Loop

```
Socialization:
  Input: External newcomers
  Output Hub: "Tacit Knowledge Base"
  → Connects to: Externalization (ONE)

Externalization:
  Input: "Tacit Knowledge Base" → "Knowledge Articulation Rate"
  Output Hub: "Articulated Knowledge"
  → Connects to: Combination (ONE)

Combination:
  Input: "Articulated Knowledge" → "Knowledge Integration Rate"
  Output Hub: "Integrated Knowledge Systems"
  → Connects to: Internalization (ONE)

Internalization:
  Input: "Integrated Knowledge Systems" → "Knowledge Application Rate"
  Output Hub: "Internalized Expertise"
  → Connects to: Socialization (ONE) [feedback loop]

Result: Socialization → Externalization → Combination → Internalization → back to Socialization

Perfect SECI knowledge spiral with clean SISO architecture!
```

---

## SISO Rules

### ✅ Required

1. **Each process has EXACTLY ONE output hub**
   - Typically the main Stock
   - Represents "what this process produces"

2. **Each process receives from EXACTLY ONE upstream**
   - Create ONE input variable (Flow or Auxiliary)
   - If no upstream, it's a source process (external input)

3. **Each output connects to EXACTLY ONE downstream**
   - From your output hub
   - To ONE other process's input variable

4. **Linear pipeline preferred**
   - A → B → C → D
   - Last process can loop back to first (feedback)

### ❌ Prohibited

1. **No one-to-many**
   - Process A output → Process B and Process C ❌
   - Choose ONE primary downstream

2. **No many-to-one**
   - Process A and Process B → Process C ❌
   - Each process has ONE input source

3. **No scattered connections**
   - Multiple random connections between processes ❌

4. **No isolated processes**
   - Every process must connect to the pipeline ❌

---

## Benefits

### 1. Maximum Clarity

Question: "Where does Process B get its input?"
Answer: "From Process A's output hub" (unambiguous!)

Question: "Where does Process B send its output?"
Answer: "To Process C's input" (crystal clear!)

### 2. Linear Reasoning

```
A → B → C → D

To understand what D does, trace backwards:
D receives from C
C receives from B
B receives from A

Simple linear trace!
```

### 3. Easy Debugging

If something breaks:
- Check the ONE input source
- Check the ONE output destination
- No complex many-to-many to untangle

### 4. Clean Diagrams

```
Perfect pipeline:
[A] → [B] → [C] → [D]
         ↑______________|  (feedback loop)

NOT:
      ↗[B]↘
[A]<        >[D]  (messy!)
      ↘[C]↗
```

### 5. Modular Replacement

Want to replace Process B?
- Disconnect from A's output
- Disconnect from C's input
- Insert new Process B'
- Two connections, done!

---

## Exception: Hub Process

**ONLY IF** Step 1 explicitly designates a "coordinating hub process" (e.g., "Community Core Development" that provides context to all others), it MAY have multiple outputs.

**Example**:
```
Community Core (Hub Process):
  Input: Collective contributions from processes
  Outputs:
    → Socialization context
    → Externalization standards
    → Combination criteria
    → Internalization guidance

This is the ONLY exception to SISO!
Default to strict SISO unless clearly indicated as hub.
```

---

## Implementation Checklist

When implementing Step 2:

- [ ] Each process has EXACTLY ONE output hub identified
- [ ] Each process (except source) has EXACTLY ONE input source
- [ ] Each inter-cluster connection is ONE-to-ONE
- [ ] Pipeline forms a clean linear flow (with optional feedback)
- [ ] No one-to-many connections (except designated hub process)
- [ ] No many-to-one inputs
- [ ] All processes connected (no isolated modules)

---

## Anti-Patterns

### ❌ Fan-Out (One-to-Many Output)

```
Process A:
  Output Hub: "Knowledge Base"
    → Process B
    → Process C  ❌ Wrong!
    → Process D

Problem: Which process is the primary consumer?
Solution: Choose ONE primary downstream (e.g., B), make it SISO
```

### ❌ Fan-In (Many-to-One Input)

```
Process D:
  Inputs:
    ← Process A  ❌ Wrong!
    ← Process B
    ← Process C

Problem: Multiple input sources, unclear data flow
Solution: Choose ONE primary input source, make it SISO
```

### ❌ Spaghetti

```
A ↔ B
↕ ⤢ ↕
D ↔ C

Problem: Every process connects to every other (N² complexity)
Solution: Linear pipeline A → B → C → D
```

---

## Summary

**SISO = Single-Input, Single-Output**

- Each process: ONE input ← ONE process
- Each process: ONE output → ONE process
- Result: Clean linear pipeline
- Exception: ONE hub process (if explicitly needed)

**Benefits**: Maximum clarity, easy debugging, clean diagrams, modular design

**Implementation**: Identify output hubs → Map linear pipeline → Create ONE-to-ONE connections

**Result**: Beautiful, maintainable, understandable system dynamics model!
