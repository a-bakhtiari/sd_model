Architecture (planned)

Layers
- IO: parse Vensim MDL, load/save artifacts
- Graph: build signed digraph, enumerate loops
- LLM: provider abstraction, prompt cache
- Knowledge: theory catalog + rules
- Validation: theory alignment, evidence scoring
- Improvement: proposals + MDL patch fragments
- Provenance: evidence, decisions, citations
- Simulation: scenarios + adapters
- Review: feedback intake + triage

Layout
- src/sd_model/* subpackages
- knowledge/theories.csv
- schemas/*.json for artifact validation
- projects/<name> for per-project artifacts

CLI (scaffold)
- sd parse | loops | interpret | validate-theory | improve

