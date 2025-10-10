# Artifact Organization

As of the latest update, artifacts are organized by **operation** into subdirectories within each project's `artifacts/` folder.

## Directory Structure

```
projects/{project_name}/artifacts/
├── parsing/              # Initial MDL extraction
│   ├── parsed.json
│   ├── variables_llm.json
│   ├── connections_llm.json
│   └── diagram_style.json
│
├── connections/          # Connection analysis
│   ├── connections.json
│   ├── connection_descriptions.json
│   ├── connection_citations.json
│   ├── connection_citations_verified.json
│   ├── connection_citations_verification_debug.txt
│   └── connections_export.csv
│
├── loops/                # Loop analysis
│   ├── loops.json
│   ├── loop_descriptions.json
│   ├── loop_citations.json
│   ├── loop_citations_verified.json
│   ├── loop_citations_verification_debug.txt
│   └── loops_export.csv
│
├── theory/               # Theory operations
│   ├── theory_validation.json
│   ├── theory_enhancement.json
│   ├── theory_enhancement_mdl.json
│   └── theory_discovery.json
│
├── research_questions/   # RQ operations
│   ├── rq_alignment.json
│   └── rq_refinement.json
│
└── improvements/         # Model improvements
    ├── gap_analysis.json
    └── model_improvements.json
```

## Benefits

1. **Easier Navigation**: Related artifacts are grouped together by operation
2. **Better Debugging**: All files for a specific operation are in one place
3. **Clearer Pipeline**: Folder structure mirrors the processing stages
4. **Easier Sharing**: Can export/share entire operation results as a unit

## Migration

If you have an older project with flat artifact structure, use the migration script:

```bash
# Dry run to see what would be moved
python scripts/migrate_artifacts.py --dry-run

# Migrate all projects
python scripts/migrate_artifacts.py

# Migrate specific project only
python scripts/migrate_artifacts.py --project oss_model
```

## Accessing Artifacts in Code

All artifact paths are defined in `src/sd_model/paths.py` via the `ProjectPaths` dataclass:

```python
from src.sd_model.config import load_config
from src.sd_model.paths import for_project

cfg = load_config()
paths = for_project(cfg, "my_project")

# Access artifacts via named attributes
parsed_data = json.loads(paths.parsed_path.read_text())
connections_data = json.loads(paths.connections_path.read_text())
loops_data = json.loads(paths.loops_path.read_text())
theory_validation = json.loads(paths.theory_validation_path.read_text())
```

## Pipeline Operations

The artifacts map to these pipeline stages:

1. **Parsing** (`parsing/`): MDL file extraction → variables, connections, diagram style
2. **Loop Detection** (`loops/`): Feedback loop identification and analysis
3. **Connection Analysis** (`connections/`): Descriptions and citation finding
4. **Theory Validation** (`theory/`): Compare model against existing theories
5. **Research Questions** (`research_questions/`): RQ alignment and refinement
6. **Improvements** (`improvements/`): Gap analysis and suggested improvements

## Notes

- The `ProjectPaths.ensure()` method automatically creates all subdirectories
- Subdirectory paths are available as attributes: `parsing_dir`, `connections_dir`, etc.
- Legacy flat structure is no longer supported in new pipeline runs
