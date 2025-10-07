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

Web UI (one command)
- Streamlit UI with everything wired up:
  - `streamlit run streamlit_app.py`
  - If using a venv: `.venv/bin/streamlit run streamlit_app.py`
  - Then open the browser (Streamlit prints the URL). Select a project, optionally toggle “Apply patch”, click “Run Pipeline,” and view artifacts inline.

Alternative launchers
- Streamlit via CLI: `python -m src.sd_model.cli ui --framework streamlit`
- Flask API UI: `python -m src.sd_model.cli ui` then visit http://127.0.0.1:5000
