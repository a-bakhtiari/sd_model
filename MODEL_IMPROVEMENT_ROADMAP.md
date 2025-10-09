# Model Improvement & Development Roadmap (Step 8)

**Status**: Architecture defined, implementation pending
**Purpose**: Transform SD model analysis into actionable PhD research guidance

---

## Current Pipeline Overview (Steps 1-7) ✅

1. **Parse MDL** → Extract variables and connections from Vensim model
2. **Infer Polarity** → LLM-based polarity detection (DeepSeek)
3. **Find Feedback Loops** → NetworkX loop detection with classification
4. **Generate Descriptions** → Natural language descriptions (connections & loops)
5. **Find Citations** → LLM (GPT-5) suggests 3+ papers per connection/loop
6. **Verify Citations** → Semantic Scholar API validates citations + enriches metadata
7. **CSV Export** → Complete metadata export for analysis

---

## Step 8: Model Improvement Architecture

**Core Philosophy**: Single comprehensive LLM analysis → Multiple specialized outputs

### Input Files
- `projects/{project}/knowledge/theories.csv` - Intentionally used theories
- `projects/{project}/knowledge/RQ.txt` - Research questions
- Existing artifacts (connections, loops, citations, descriptions)

### Output Directory
```
projects/{project}/artifacts/model_improvement/
├── core_analysis.json              # Single LLM analysis (cached)
├── theory_enhancement.json         # Missing theory elements
├── rq_theory_alignment.json        # Alignment evaluation
├── rq_refinement.json              # RQ improvement suggestions
├── theory_suggestions.json         # New theory recommendations
├── improvement_summary.csv         # Quick reference
└── improvement_report.md           # Human-readable report
```

---

## Module Architecture

### Module 1: Core Analysis Engine
**File**: `src/sd_model/pipeline/model_analysis.py`
**Purpose**: Single comprehensive LLM analysis (cost optimization)

**LLM**: GPT-5 (reasoning model for complex multi-perspective analysis)

**Inputs**:
- Current SD model (variables, connections, loops)
- `theories.csv` (intentionally used theories)
- `RQ.txt` (research questions)
- Connection/loop descriptions & citations

**Output**: Rich analysis object
```json
{
  "model_summary": {
    "variable_count": 45,
    "connection_count": 89,
    "loop_count": 12,
    "primary_stocks": ["Contributors", "Reputation", "..."],
    "dominant_dynamics": "community growth feedback loops"
  },
  "theory_coverage": {
    "utilized_theories": ["Communities of Practice", "SECI Model"],
    "coverage_by_theory": {...},
    "underutilized_aspects": [...]
  },
  "rq_alignment": {
    "rq_1_coverage": "poor - AI not modeled",
    "rq_2_coverage": "partial - intervention points exist",
    "gaps": [...]
  },
  "model_theory_gaps": [...],
  "opportunities": [...]
}
```

**Caching**: Hash-keyed cache (model + theories + RQs) to avoid re-analysis

---

### Module 2: Theory Enhancement Suggester
**File**: `src/sd_model/pipeline/theory_enhancement.py`
**Purpose**: Identify missing elements from existing theories + general improvements

**Features**:
1. **Missing Theory Elements**: What's missing from theories you already use
2. **Theory Applications**: Underutilized aspects of current theories
3. **SD Implementation**: Concrete variable/connection additions

**Output Structure**:
```json
{
  "missing_from_theories": [
    {
      "theory_name": "Communities of Practice",
      "missing_elements": ["legitimate peripheral participation flow"],
      "why_important": "Model shows joining but not progression mechanism",
      "how_to_add": "Add intermediate 'Peripheral Contributors' stock",
      "sd_implementation": {
        "new_variables": ["Peripheral Contributors", "Progression Rate"],
        "new_connections": [
          {"from": "New Contributors", "to": "Peripheral Contributors", "relationship": "positive"},
          {"from": "Peripheral Contributors", "to": "Active Contributors", "relationship": "positive"}
        ]
      },
      "expected_impact": "Better model contributor lifecycle"
    }
  ],
  "theory_applications": [
    {
      "theory": "SECI Model",
      "underutilized_aspect": "Internalization phase (explicit → tacit)",
      "current_use": "Only models documentation (externalization)",
      "suggestion": "Model how documentation becomes contributor skills",
      "implementation": {...}
    }
  ],
  "general_improvements": [...]
}
```

---

### Module 3: RQ-Theory-Model Alignment Evaluator
**File**: `src/sd_model/pipeline/rq_theory_alignment.py`
**Purpose**: Evaluate fit between research questions, theories, and model

**Features**:
1. Per-RQ alignment scoring (1-10)
2. Specific issues identification
3. Theory recommendations (add/remove/modify)
4. Model addition suggestions

**Output Structure**:
```json
{
  "rq_1": {
    "rq": "What is the career path of software developers in OSS...",
    "alignment_score": 7,
    "issues": [
      "Career path modeled via stock progression",
      "Dynamics affecting path are present (feedback, skills, etc.)"
    ],
    "strengths": ["Strong progression modeling", "Clear feedback loops"],
    "recommendations": {
      "theories_to_add": ["Career Development Theory", "Skill Acquisition Models"],
      "theories_to_remove": [],
      "model_additions": [
        "Add explicit career stages as stocks",
        "Model skill milestones affecting progression"
      ]
    }
  },
  "rq_2": {...},
  "overall_assessment": {
    "model_rq_fit": "good",
    "theory_rq_fit": "moderate",
    "critical_gaps": [],
    "actionable_steps": [...]
  }
}
```

**Special Detection**: Flags mismatches (e.g., "RQs mention AI but model has no AI variables")

---

### Module 4: Research Question Refiner
**File**: `src/sd_model/pipeline/rq_refinement.py`
**Purpose**: Suggest improved RQ formulations based on model capabilities

**LLM**: GPT-5 (creativity + rigor needed)

**Features**:
1. Identify RQ issues (too broad, unmeasurable, etc.)
2. Generate refined versions
3. Suggest new RQs based on model insights
4. PhD-worthiness assessment

**Output Structure**:
```json
{
  "current_rqs": ["RQ1...", "RQ2...", "RQ3..."],
  "refinement_suggestions": [
    {
      "rq_number": 1,
      "original": "What is the career path of developers in OSS...",
      "issues": [
        "Broad - doesn't specify which aspects of career path",
        "Doesn't specify contributor types"
      ],
      "refined_versions": [
        {
          "version": "How do feedback mechanisms between contribution quality and community recognition affect the progression rate from peripheral to core contributors in OSS?",
          "rationale": "More specific, focuses on modelable dynamics, aligns with Communities of Practice theory",
          "sd_modelability": "high",
          "phd_worthiness": 8,
          "theoretical_contribution": "Links social learning theory with OSS dynamics"
        },
        {
          "version": "What intervention points in the skill acquisition-contribution-recognition loop can accelerate contributor progression in OSS communities?",
          "rationale": "Action-oriented (interventions), clear SD leverage points",
          "sd_modelability": "high",
          "phd_worthiness": 7
        }
      ]
    }
  ],
  "new_rq_suggestions": [
    {
      "suggested_rq": "What feedback loops emerge between contributor skill levels and project knowledge base growth?",
      "based_on_model": "Model has both skill and knowledge stocks with connections",
      "phd_worthiness": 7,
      "originality": "Understudied in OSS literature"
    }
  ]
}
```

---

### Module 5: Adjacent Theory Discovery
**File**: `src/sd_model/pipeline/theory_discovery.py`
**Purpose**: Recommend new theories (direct + slightly out-of-box)

**LLM**: GPT-5 + **Semantic Scholar API** (search for papers)

**Adjacency Levels**:
- **Direct**: Clearly relevant to current model/RQs
- **Adjacent**: Slightly different angle, creative connection
- **Exploratory**: Cross-domain inspiration (calculated risk)

**Output Structure**:
```json
{
  "high_relevance": [
    {
      "theory_name": "Legitimate Peripheral Participation (Lave & Wenger)",
      "key_citation": "Lave & Wenger 1991",
      "relevance_to_rqs": "Directly addresses contributor progression from periphery to core",
      "relevance_to_model": "Can model progression stages as stocks",
      "adjacency_level": "direct",
      "phd_contribution": "Apply LPP framework to OSS - some prior work but room for SD modeling",
      "semantic_scholar_results": {
        "paper_id": "...",
        "citation_count": 45000,
        "recent_oss_applications": 12
      }
    }
  ],
  "adjacent_opportunities": [
    {
      "theory_name": "Distributed Cognition",
      "key_citation": "Hutchins 1995",
      "why_adjacent": "Treats tools as cognitive artifacts extending capabilities",
      "novel_angle": "Model OSS tools/docs as cognitive infrastructure",
      "risk_level": "medium",
      "potential_payoff": "high",
      "phd_contribution": "Novel application - cognition usually individual-focused, OSS is collective"
    }
  ],
  "cross_domain_inspiration": [
    {
      "theory": "Medical Automation & Skill Retention (aviation psychology)",
      "parallel": "Like pilots with autopilot, do devs lose skills with better tools/AI?",
      "transfer_potential": "Model skill atrophy loops in tool-heavy environments",
      "risk_level": "high",
      "rationale": "Provocative angle, high originality if done well"
    }
  ],
  "phd_assessment": {
    "novelty_score": 8,
    "rigor_score": 7,
    "impact_score": 8,
    "feasibility_score": 6,
    "overall_worthiness": 7.3,
    "committee_appeal": "Strong interdisciplinary contribution"
  }
}
```

**PhD-Worthiness Scoring**:
- **Novelty** (1-10): Literature gap score from S2 API query
- **Rigor** (1-10): Can it be modeled in SD? Measurable?
- **Impact** (1-10): Citation velocity, real-world relevance
- **Feasibility** (1-10): Can complete in PhD timeline?

---

## Design Decisions

### 1. Bundled vs Standalone
**Decision**: **Hybrid**
- Core Analysis: Always runs (single LLM call)
- Outputs: Independently toggleable via CLI flags

**Rationale**:
- PhD workflow is iterative
- Bundle core analysis for cost savings
- Allow selective feature use

### 2. LLM Strategy
**Core Analysis**: GPT-5 (reasoning model for complexity)
**Theory Discovery**: GPT-5 + Semantic Scholar
**RQ Refinement**: GPT-5
**Enhancement Suggestions**: Reuse core analysis (minimal LLM)

**Cost Optimization**:
- Cache core analysis (keyed by model hash)
- Only re-run if model/theories/RQs change

### 3. Output Formats
- **JSON**: Machine-readable, version-controllable
- **CSV**: Quick review (Excel/Sheets)
- **Markdown**: Thesis-ready, human-readable

---

## CLI Integration

```bash
# Run all improvement features
python -m src.sd_model.cli run --project oss_model --improve-model

# Run specific features
python -m src.sd_model.cli run --project oss_model \
  --improve-model \
  --improvement-features theory_enhancement,rq_alignment

# Interactive UI (Streamlit)
python -m src.sd_model.cli ui --framework streamlit
# → New "Model Development" tab
```

**New CLI Flags**:
- `--improve-model`: Enable Step 8
- `--improvement-features FEATURES`: Comma-separated list (optional)
  - `theory_enhancement`
  - `rq_alignment`
  - `rq_refinement`
  - `theory_discovery`
  - `all` (default)

---

## Current Gap Example (To Be Detected)

**RQ Analysis** (from `RQ.txt`):
- RQ1: "career path of software developers in OSS from novice periphery to core developer"
- RQ2: "interventions to make this process smooth"
- RQ3: "prevent system failure and vulnerabilities"

**Model Analysis** (from current artifacts):
- ✅ Variables: Progression modeled (New Contributors, etc.)
- ✅ Connections: Career path dynamics present
- ✅ Loops: Feedback mechanisms identified

**Theory Analysis** (from `theories.csv`):
- Current: Communities of Practice, SECI Model
- ✅ Good fit for RQ1 (career progression)
- ⚠️ RQ3 (system vulnerabilities) not well-supported

**Expected Output** (from Module 3):
```json
{
  "rq_1": {
    "alignment_score": 8,
    "issues": [],
    "recommendations": {
      "theories_to_add": ["Legitimate Peripheral Participation"],
      "model_additions": ["Explicit progression stages as stocks"]
    }
  },
  "rq_3": {
    "alignment_score": 4,
    "issues": [
      "RQ asks about 'system failure' but model has no failure mechanisms",
      "No theories addressing system resilience/fragility"
    ],
    "recommendations": {
      "theories_to_add": ["System Resilience Theory", "Organizational Failure Modes"],
      "model_additions": [
        "Add system stress variables",
        "Model contributor burnout/attrition loops",
        "Add quality degradation mechanisms"
      ]
    }
  }
}
```

---

## Implementation Tracker

### Phase 1: Setup ⬜
- [ ] Create `src/sd_model/pipeline/model_analysis.py`
- [ ] Create `src/sd_model/pipeline/theory_enhancement.py`
- [ ] Create `src/sd_model/pipeline/rq_theory_alignment.py`
- [ ] Create `src/sd_model/pipeline/rq_refinement.py`
- [ ] Create `src/sd_model/pipeline/theory_discovery.py`
- [ ] Add CSV/TXT loaders for `theories.csv` and `RQ.txt`
- [ ] Update `paths.py` with improvement artifact paths
- [ ] Update `orchestrator.py` with Step 8 integration
- [ ] Add CLI flags to `cli.py`

### Phase 2: Core Analysis Engine ⬜
- [ ] Design comprehensive LLM prompt
- [ ] Implement hash-based caching
- [ ] GPT-5 integration
- [ ] Test with oss_model project
- [ ] Validate JSON output structure

### Phase 3: Specialized Generators ⬜
- [ ] Module 2: Theory Enhancement
- [ ] Module 3: RQ-Theory Alignment (with gap detection)
- [ ] Module 4: RQ Refinement
- [ ] Module 5: Theory Discovery (S2 API integration)
- [ ] CSV summary generator
- [ ] Markdown report generator

### Phase 4: Integration & Testing ⬜
- [ ] End-to-end test with oss_model
- [ ] Verify outputs are actionable
- [ ] Test caching behavior
- [ ] Test selective feature flags

### Phase 5: UI Integration ⬜
- [ ] Add "Model Development" tab to Streamlit UI
- [ ] Implement toggles for each module
- [ ] Display results with visualizations
- [ ] Export buttons for artifacts

### Phase 6: Documentation ⬜
- [ ] Update README.md
- [ ] Create MODULE_IMPROVEMENT_GUIDE.md
- [ ] Add examples to docs/

---

## Notes & Considerations

### PhD Workflow Integration
This system should support iterative PhD research:
1. **Initial modeling** → Identify what you modeled
2. **RQ evaluation** → Are your RQs answerable?
3. **Theory alignment** → Right theoretical foundation?
4. **Gap identification** → What's missing?
5. **Refinement** → Improve model/RQs/theories
6. **Repeat** → Iterate until coherent

### Future Enhancements
- **Interactive refinement**: Chat-based RQ refinement loop
- **Citation network analysis**: Map theory connections via S2 API
- **Automated patch generation**: Not just suggest, but generate MDL patches
- **Intervention simulator**: Test suggested interventions in model
- **Literature review assistant**: Auto-generate lit review sections

### Known Limitations
- LLM suggestions need human validation (research judgment)
- Theory discovery limited to S2 API coverage
- PhD-worthiness scores are heuristic (not committee consensus)
- Cross-domain suggestions may be too creative (manage risk)

---

**Last Updated**: 2025-10-08
**Next Review**: After Module 1 implementation
