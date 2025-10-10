SD Model: Citation-Driven Research Companion for System Dynamics


This repository analyzes and improves system dynamics (Vensim MDL) models for open-source communities through a **literature-driven, citation-verified pipeline** with integrated paper discovery.

**Status:** ✅ Core system complete with citation verification, gap analysis, and paper discovery!

## 🌟 New Features
- **Citation Verification** - Verify all theory citations via Semantic Scholar API
- **Gap Analysis** - Identify connections lacking literature support
- **Paper Discovery** - Find relevant papers to support unsupported connections
- **Interactive UI** - Streamlit interface with Citation Verification and Paper Discovery tabs

High-level Workflow
- Parse MDL → connections (signed graph)
- Find and interpret feedback loops (LLM)
- **Validate against theories/literature with citation verification** ✨
- **Discover papers for unsupported connections** ✨
- Generate improvements and MDL patch guidance
- Iterate: add citations, refine model, repeat

See `docs/architecture.md` for the new layout and planned modules.

## Quick Start

### 1. Install and Configure
```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and set:
#   - DEEPSEEK_API_KEY (for LLM analysis)
#   - SEMANTIC_SCHOLAR_API_KEY (for citation verification)
```

### 2. Run Pipeline

**Simple usage:**
```bash
# Basic run (enables model improvement by default)
python main.py --project oss_model

# Save this run for later comparison
python main.py --project oss_model --save-run "baseline-model"

# With citation verification
python main.py --project oss_model --verify-citations

# Full features: verification + paper discovery + versioned run
python main.py --project oss_model --verify-citations --discover-papers --save-run "v1-complete"
```

**Advanced CLI (alternative):**
```bash
# Same functionality via CLI module
python -m sd_model.cli run --project oss_model --save-run baseline
```

### 3. Launch Interactive UI
```bash
# Launch Streamlit UI
python -m sd_model.cli ui --framework streamlit

# Then open browser and explore:
#   - Dashboard: Overview of model
#   - Stage 2: Feedback loops with theory alignment
#   - Citation Verification: Verify citations, view coverage
#   - Paper Discovery: Find papers for gaps
```

## 📚 Documentation

- **[CITATION_SYSTEM_SUMMARY.md](CITATION_SYSTEM_SUMMARY.md)** - Complete guide to the citation verification system
- **[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)** - Detailed implementation status
- **[docs/architecture.md](docs/architecture.md)** - System architecture

## Alternative Launchers
- Flask API UI: `python -m src.sd_model.cli ui` then visit http://127.0.0.1:5000
