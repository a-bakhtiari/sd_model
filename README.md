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

Quick start
- Install deps: `pip install -r requirements.txt`
- Copy `.env.example` to `.env` and set `DEEPSEEK_API_KEY`
- Run the whole pipeline: `PYTHONPATH=src python3 main.py`
- Or run step-by-step via CLI:
  - `PYTHONPATH=src python -m sd_model.cli parse untitled.mdl`
  - `PYTHONPATH=src python -m sd_model.cli loops`
  - `PYTHONPATH=src python -m sd_model.cli interpret`
  - `PYTHONPATH=src python -m sd_model.cli validate-theory`
  - `PYTHONPATH=src python -m sd_model.cli improve`
