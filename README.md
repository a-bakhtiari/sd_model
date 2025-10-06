SD Model: Modular Architecture (WIP)

This repository analyzes and improves system dynamics (Vensim MDL) models for open-source communities through a literature- and theory-driven pipeline.

Status: baseline committed and modular scaffolding in progress.

High-level Workflow
- Parse MDL → connections (signed graph)
- Find and interpret feedback loops (LLM)
- Validate against theories/literature
- Generate improvements and MDL patch guidance
- Optionally simulate scenarios and feed results back

See `docs/architecture.md` for the new layout and planned modules.

