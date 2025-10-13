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

The pipeline has **granular feature control** - run only the features you need!

**Foundation (always runs):**
- Parse MDL → extract variables & connections
- Generate connection descriptions

**Optional Features:**

```bash
# 1. Foundation only (fastest - just parsing and descriptions)
python main.py --project oss_model

# 2. With feedback loops
python main.py --project oss_model --loops

# 3. With citations (for connections)
python main.py --project oss_model --citations

# 4. Theory-based model enhancement (single-call approach)
python main.py --project oss_model --theory-enhancement

# 5. Theory enhancement with decomposed 3-step approach (recommended)
#    Step 1: Strategic planning → Step 2: Concrete generation → Step 3: Positioning
python main.py --project oss_model --theory-enhancement --decomposed-theory

# 6. Theory enhancement with full relayout (reposition ALL variables)
python main.py --project oss_model --theory-enhancement --decomposed-theory --full-relayout

# 7. Archetype detection (detect system archetypes and suggest patterns)
python main.py --project oss_model --archetype-detection

# 8. Research question analysis
python main.py --project oss_model --rq-analysis

# 9. Discover new relevant theories
python main.py --project oss_model --theory-discovery

# 10. Gap analysis (find unsupported connections)
python main.py --project oss_model --citations --gap-analysis

# 11. Paper discovery for gaps
python main.py --project oss_model --citations --gap-analysis --discover-papers

# 12. Run ALL optional features
python main.py --project oss_model --all

# 13. Run all model improvement features
python main.py --project oss_model --improve-model

# 14. Save versioned run for later comparison
python main.py --project oss_model --all --save-run "baseline-v1"

# 15. Apply MDL patch automatically (use with theory-enhancement)
python main.py --project oss_model --theory-enhancement --apply-patch
```

**Common Workflows:**

```bash
# Quick analysis: loops + citations
python main.py --project oss_model --loops --citations

# Full verification: citations + gap analysis + papers
python main.py --project oss_model --citations --gap-analysis --discover-papers

# Model improvement with decomposed theory enhancement (recommended)
python main.py --project oss_model --theory-enhancement --decomposed-theory --full-relayout --rq-analysis --theory-discovery

# Complete analysis (everything)
python main.py --project oss_model --all --save-run "complete-analysis"
```

**Advanced CLI (alternative):**
```bash
# Same flags work with CLI module
python -m sd_model.cli run --project oss_model --loops --citations --save-run baseline
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
