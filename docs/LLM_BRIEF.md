Purpose

- Give an LLM a precise, end-to-end picture of the current project so it can propose a better architecture, richer functionality, and improved workflows.
- Capture what exists (code, data flow, artifacts, schemas, provenance, CLI), why we chose it, and where it struggles.
- Provide enough context, contracts, and constraints so redesign proposals are grounded and safe to implement iteratively.

What The Project Does

- Converts a Vensim `.mdl` system dynamics model into signed causal connections, analyzes feedback loops, interprets them into plain-language insights, validates the model against domain theories/literature, and proposes theory-backed improvements. Each run records artifacts and evidence for traceability.

Core Flow

- Parse MDL → `connections.json`
- Compute Loops (R/B polarity) → `loops.json`
- Interpret Loops with LLM → `loops_interpreted.json`
- Validate Against Theories → `theory_validation.json`
- Propose Improvements → `model_improvements.json`
- Record artifacts + evidence → SQLite provenance database

Each output is JSON-schema validated before being saved and logged.

Project Structure

- Code (shared engine)
  - `src/sd_model/cli.py` (CLI commands; includes provenance inspection)
  - `src/sd_model/config.py` (loads `.env`, settings)
  - `src/sd_model/paths.py` (project-aware paths for mdl, artifacts, db, knowledge)
  - `src/sd_model/llm/client.py` (DeepSeek client; JSON-only responses)
  - `src/sd_model/graph/*` (graph builder and loop analysis)
  - `src/sd_model/pipeline/*` (parse, loops, interpret, theory_validation, improve)
  - `src/sd_model/validation/schema.py` (JSON Schema validator)
  - `src/sd_model/provenance/store.py` (SQLite tables + insert helpers)
- Data (per project; iteration scope)
  - `projects/<project>/mdl/` (Vensim `.mdl` sources)
  - `projects/<project>/artifacts/` (JSON outputs per step)
  - `projects/<project>/knowledge/theories.csv` (project-specific theory catalog)
  - `projects/<project>/db/provenance.sqlite` (artifact/evidence log)
- Shared assets
  - `schemas/*.schema.json` (contracts for artifacts)
  - `docs/*` (architecture notes and diagram)
  - `legacy/*` (original root scripts preserved)
  - `main.py` (orchestrates the full loop with logging)

This layout separates the reusable engine from project-specific data and iteration history, enabling multiple projects and clean provenance.

Artifacts and Contracts

- `connections.json` (schemas/connections.schema.json)
  - Each edge: `{ "from": str, "to": str, "relationship": "positive"|"negative" }`
- `loops.json` (schemas/loops.schema.json)
  - For each cycle: `nodes`, `edges` with `relationship`, `negative_edges` count, `type` ∈ R|B
  - Summary: counts and min/max loop length
- `loops_interpreted.json` (schemas/loops_interpreted.schema.json)
  - `enhanced_loops`: loop + `{ name, meaning, impact, explanation }`
  - `system_insights`: plain text synthesis
- `theory_validation.json` (schemas/theory_validation.schema.json)
  - `theory_validations`: per-theory lists of aligned/problematic/missing connections, `alignment_score`
  - `average_alignment`, `consistent_missing`, `consistent_issues`
- `model_improvements.json` (schemas/model_improvements.schema.json)
  - `improvements`: additions/removals/new variables/structural changes
  - `implementation_script`: MDL fragments to add connections/variables
  - `updated_connections`: input connections plus marked removals

Schemas enforce structure across steps and produce immediate, localized failures when LLM outputs drift.

Provenance Model

- SQLite schema (`src/sd_model/provenance/store.py`)
  - `artifacts(id, kind, path, sha256, created_at)`
  - `connections(artifact_id, source, target, sign)`
  - `loops(artifact_id, nodes_json, loop_type, length)`
  - `evidence(item_type, item_id, source, ref, confidence, note, created_at)`
- Current evidence recorded:
  - Interpret step: `system_insights` as evidence note
  - Theory validation: `average_alignment` mapped to confidence ∈ [0,1]
- CLI to inspect (sd provenance …)
  - `stats`, `list`, `evidence`, `diff-connections`

This gives research-grade traceability: every output, row, and key note has an audit trail.

How Steps Work (Implementation Detail + Rationale)

- Parse (`src/sd_model/pipeline/parse.py`)
  - Prompt instructs LLM to extract “A FUNCTION OF(…,-dep)” patterns, remove `-` signs but preserve negative polarity.
  - Uses `replace` instead of `format` to avoid brace collisions in JSON examples.
  - LLM client strips ``` fences if present; expects valid JSON; temperature low (deterministic outputs).
  - Rationale: LLM handles fuzzy parsing of multi-line MDL definitions better than regex; schemas protect downstream.

- Loops (`src/sd_model/pipeline/loops.py`)
  - Builds `networkx.DiGraph` with `relationship` attribute on edges.
  - Uses parity of negative edges to classify R/B (even→R, odd→B).
  - Rationale: Simple and fast; good first-order signal for feedback reinforcement vs balancing.

- Interpret (`src/sd_model/pipeline/interpret.py`)
  - Sends loop structures (as JSON lists of nodes/edges) to LLM for names, meaning, and sustainability impact.
  - Merges interpretations back into structural loops by matching `set(nodes)`.
  - Rationale: LLM excels at language and context; we confine it to interpretation, not structure.

- Theory Validation (`src/sd_model/pipeline/theory_validation.py`)
  - Loads `projects/<project>/knowledge/theories.csv` (name, description, focus_area, citations).
  - Asks LLM to: align/contradict/missing/predict connections and score alignment.
  - Synthesizes patterns across theories: `average_alignment`, `consistent_missing`, `consistent_issues`.
  - Rationale: Ground the model in established theory with explainable, structured outputs.

- Improve (`src/sd_model/pipeline/improve.py`)
  - Asks LLM to propose prioritized connections and variables given validation gaps.
  - Emits simplified MDL fragments to guide edits, and a suggested sequence (`implementation_order`).
  - Rationale: Turn critique into actionable, theory-backed structural changes.

Design Decisions and Why

- JSON Schema validation before saving: LLM outputs can drift or include markdown. Schemas give deterministic contracts and clear failures, enabling safe composition.
- SQLite provenance per project: Lightweight, versionable, and easy to diff/query; co-locates with project artifacts for packaging and review.
- Per-project knowledge: Different models can have different theories/sources; place catalogs under each project for isolation and auditability.
- Modular pipelines: Each step is small, testable, and replaceable; prevents cross-step coupling and eases refactors.

Assumptions and Constraints

- Vensim `.mdl` definitions follow “A FUNCTION OF(…)” convention in the relevant sections; we ignore sketch sections.
- Polarity is binary (positive/negative); no magnitude estimation.
- Loop importance is not computed structurally (no loop gain/sensitivity); LLM interpretation suggests dominance qualitatively.
- No automatic MDL rewriting/simulation yet; improvements are suggested as MDL fragments and left for human implementation.
- API keys are loaded from `.env`; all networked steps use DeepSeek chat completions with JSON-only outputs.

Current Pain Points / Known Limitations

- MDL parsing is LLM-dependent; could be made deterministic for many patterns.
- Loop analysis is structural only; no dynamic/quantitative insights (e.g., dominance, gain).
- Theory validation and improvements rely on LLM consistency; no citation-verification pipeline yet.
- No automatic MDL patcher or simulation integration (PySD/Vensim) to close the behavior loop.
- Prompt robustness: JSON brace collisions required manual `.replace`; need prompt templating library.
- No caching/backoff for LLM calls; no retry-on-schema-failure repair step.
- Schemas have no versioning; artifacts don’t embed schema metadata.

Extension Points the LLM Can Improve

- Parsing
  - Add deterministic parser for MDL “A FUNCTION OF” with robust multiline handling; use LLM only for ambiguous fragments.
  - Extract variable types (stock, flow, auxiliary) from `.mdl` or through heuristics; enrich `connections.json` with `type_from`/`type_to`.

- Loop Analysis
  - Add loop ranking metrics (centrality, edge betweenness, structural import).
  - Detect loop families and overlaps; compute minimal cycle bases.

- Interpretation
  - Multi-pass interpretation: draft → critique (adjudicate) → final; record both steps with confidence.
  - Calibrate “impact on sustainability” rubric and map to numeric evidence score.

- Theory Validation + Knowledge
  - Expand `knowledge/` to include relationships with expected polarity and strength; let validation be partly rule-based, not solely LLM.
  - Add citation store (CSL-JSON) and require LLM to attach citation IDs for every claim; add a post-check that verifies references exist.

- Improvements and Patching
  - Generate a concrete MDL patch and apply it programmatically (with backups).
  - Provide a reversible “preview diff” before applying to `.mdl`.

- Simulation Loop
  - Integrate PySD/Vensim: run baseline and scenario experiments automatically; collect behavior metrics; feed mismatches back as evidence.

- Provenance and Reporting
  - Embed schema id/version in each artifact; store in DB.
  - Add `sd provenance report` to export markdown summaries (artifacts + evidence + diff) for reviewers.

- CLI/UX
  - `sd project init <name> --mdl path` to scaffold `mdl/`, `artifacts/`, `db/`, `knowledge/` and copy the `.mdl`.
  - `sd cache` for LLM result caching; `sd retry` for schema-repair loops.

Quality Gates / Invariants

- All artifacts must validate against schemas before write.
- Every LLM call that produces an artifact must:
  - Use deterministic settings (low temperature)
  - Strip markdown fences
  - On schema failure: retry/repair or fail with actionable error
- Every artifact must be recorded in provenance with sha256; evidence should be added when available.
- Project-local paths only; root remains clean of project artifacts and DB.

Key Files to Inspect

- CLI entrypoint: `src/sd_model/cli.py`
- Orchestrator: `main.py`
- Config: `src/sd_model/config.py`
- Project paths: `src/sd_model/paths.py`
- LLM client: `src/sd_model/llm/client.py`
- Parse step: `src/sd_model/pipeline/parse.py`
- Loop step: `src/sd_model/pipeline/loops.py`
- Interpret step: `src/sd_model/pipeline/interpret.py`
- Theory validation: `src/sd_model/pipeline/theory_validation.py`
- Improvement: `src/sd_model/pipeline/improve.py`
- Validation helper: `src/sd_model/validation/schema.py`
- Provenance store: `src/sd_model/provenance/store.py`
- Schemas: `schemas/*.schema.json`
- Project example: `projects/oss_model/*`

What We Want From The Redesign LLM

- Propose a revised architecture and module boundaries that:
  - Reduce LLM dependence where deterministic parsing is feasible
  - Add layered validation (schema + semantic checks)
  - Introduce loop ranking and simulation hooks
  - Add citation-aware theory validation with verifiability
  - Provide robust prompt templates and retries with schema repair
  - Implement project initialization and reporting workflows
- Provide an incremental migration plan:
  - Stepwise PRs, minimal breakage, adapters for old artifacts, tests

Success Criteria

- Same (or better) outputs for existing `.mdl` with fewer manual fixes
- Stronger guarantees: schema + semantic validations
- Clearer, faster workflows for new projects
- Traceable, citation-backed validations
- Ready-to-apply MDL patch suggestions and optional simulation runs
