# Pipeline Run Versioning

The pipeline supports two modes for managing artifacts:

## Normal Mode (Default - Overwrites)

By default, running the pipeline overwrites artifacts in the standard location:

```bash
python -m sd_model.cli run --project sd_test
```

**Result:**
```
projects/sd_test/artifacts/
├── parsing/
├── connections/
├── loops/
├── theory/
├── research_questions/
└── improvements/
```

This is useful for:
- ✅ Quick iterations during development
- ✅ Minimal disk space usage
- ✅ Simple artifact management

---

## Versioned Mode (Saves Each Run)

Add the `--save-run` flag to save artifacts to a timestamped folder:

```bash
# Auto-generate timestamp name
python -m sd_model.cli run --project sd_test --save-run

# Custom run name
python -m sd_model.cli run --project sd_test --save-run "baseline-model"
python -m sd_model.cli run --project sd_test --save-run "after-theory-enhancement"
```

**Result:**
```
projects/sd_test/artifacts/
├── parsing/           # Latest run (still overwritten)
├── connections/
├── ...
└── runs/              # Saved versioned runs
    ├── 20251010_115840/
    │   ├── parsing/
    │   ├── connections/
    │   ├── loops/
    │   ├── theory/
    │   ├── research_questions/
    │   ├── improvements/
    │   └── run_metadata.json
    ├── 20251010_143200_baseline-model/
    │   ├── parsing/
    │   ├── ...
    │   └── run_metadata.json
    ├── 20251011_092000_after-theory-enhancement/
    │   └── ...
    └── latest -> 20251011_092000_after-theory-enhancement/
```

This is useful for:
- ✅ Tracking model evolution over time
- ✅ Comparing different runs
- ✅ Preserving important milestones
- ✅ Rollback capability
- ✅ Analyzing how enhancements affect results

---

## Run Metadata

Each versioned run includes a `run_metadata.json` file with:

```json
{
  "run_id": "20251010_115840_baseline-model",
  "project": "sd_test",
  "timestamp": "2025-10-10T11:58:40.123456",
  "artifacts_directory": "projects/sd_test/artifacts/runs/20251010_115840_baseline-model",
  "pipeline_configuration": {
    "improve_model": true,
    "verify_citations": false,
    "discover_papers": false,
    "apply_patch": false
  },
  "artifacts_generated": {
    "parsed": "path/to/parsed.json",
    "connections": "path/to/connections.json",
    "theory_enhancement": "path/to/theory_enhancement.json",
    "enhanced_mdl": "path/to/enhanced.mdl",
    ...
  },
  "summary": {
    "total_artifacts": 23
  }
}
```

---

## Enhanced MDL Versioning

Enhanced MDL files are **always versioned** and saved separately from pipeline artifacts:

```
projects/sd_test/mdl/enhanced/
├── 20251010_113305_CoP_SECI/
│   ├── test_enhanced.mdl
│   └── enhancement_log.json
├── 20251010_143200_CoP/
│   ├── test_enhanced.mdl
│   └── enhancement_log.json
└── latest -> 20251010_143200_CoP/
```

This ensures you never lose manual edits to enhanced MDL files, regardless of whether you use `--save-run` or not.

---

## Best Practices

### Use Normal Mode When:
- Rapidly iterating on model development
- Testing pipeline changes
- Working with limited disk space
- Only care about the latest results

### Use Versioned Mode When:
- Creating important milestones
- Before major model changes
- Comparing enhancement strategies
- Need audit trail for research
- Want to analyze progression over time

### Naming Conventions:
```bash
--save-run "baseline"                    # Before any changes
--save-run "CoP-enhancement"             # After adding Communities of Practice
--save-run "v1-submitted"                # Version submitted for review
--save-run "experiment-SECI-only"        # Testing specific theories
```

---

## Accessing Versioned Runs

### Via Latest Symlink:
```bash
ls projects/sd_test/artifacts/runs/latest/
```

### Specific Run:
```bash
ls projects/sd_test/artifacts/runs/20251010_143200_baseline-model/
```

### List All Runs:
```bash
ls -lt projects/sd_test/artifacts/runs/
```

---

## Disk Space Management

Versioned runs accumulate over time. To clean up:

```bash
# Remove specific run
rm -rf projects/sd_test/artifacts/runs/20251010_115840/

# Keep only last N runs (example: keep last 5)
cd projects/sd_test/artifacts/runs/
ls -t | tail -n +6 | grep -v latest | xargs rm -rf
```
