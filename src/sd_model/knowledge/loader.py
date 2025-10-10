from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from .types import FeedbackItem, Theory


def load_theories(theories_dir: Path) -> List[Theory]:
    """Scan a directory for theory files (`.yml` or `theories.csv`).

    Supports both YAML files (one theory per file) and CSV format.
    CSV can be in theories_dir or its parent (knowledge/) directory.
    """
    items: List[Theory] = []
    if not theories_dir.exists():
        return items

    # Check for theories.csv - first in parent (knowledge/), then in theories_dir
    csv_path = theories_dir.parent / "theories.csv"
    if not csv_path.exists():
        csv_path = theories_dir / "theories.csv"

    if csv_path.exists():
        try:
            import csv
        except Exception as e:  # pragma: no cover
            raise RuntimeError("csv module required but not found.") from e

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get('name'):
                    continue
                # CSV format: name, description, focus_area, citations
                data = {
                    'theory_name': row.get('name', ''),
                    'citation_key': row.get('citations', '').split(';')[0].strip() if row.get('citations') else '',
                    'expected_connections': [],
                    'description': row.get('description', ''),
                    'focus_area': row.get('focus_area', '')
                }
                try:
                    items.append(Theory(**data))
                except Exception as e:
                    raise ValueError(f"Invalid theory in CSV: {row}: {e}")
        return items

    # Fall back to YAML files
    try:
        import yaml  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "PyYAML is required to load theories but was not found."
        ) from e

    for path in sorted(theories_dir.glob("*.yml")):
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw) or {}
        # Be resilient to null/omitted expected_connections
        if data.get("expected_connections") is None:
            data["expected_connections"] = []
        try:
            items.append(Theory(**data))
        except Exception as e:
            raise ValueError(f"Invalid theory file: {path}: {e}")
    return items


def load_bibliography(bib_path: Path) -> Dict[str, dict]:
    """Load a BibTeX file and return a dict keyed by citation IDs.

    Uses `bibtexparser` if available. Raises if the file does not exist.
    """
    if not bib_path.exists():
        raise FileNotFoundError(f"references.bib not found: {bib_path}")

    try:
        import bibtexparser  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "bibtexparser is required to load bibliography but was not found."
        ) from e

    text = bib_path.read_text(encoding="utf-8")
    db = bibtexparser.loads(text)
    # Each entry has a 'ID' (or 'entry_key' depending on parser version) and fields
    entries = {}
    for entry in db.entries:
        key = entry.get("ID") or entry.get("entry_key")
        if not key:
            # Skip entries without explicit key
            continue
        entries[str(key)] = entry
    return entries


def load_feedback(feedback_path: Path) -> List[FeedbackItem]:
    """Load and validate feedback JSON array into `FeedbackItem` models.

    If the file does not exist, returns an empty list.
    """
    if not feedback_path.exists():
        return []
    try:
        data = json.loads(feedback_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid JSON in feedback file: {feedback_path}: {e}")

    if not isinstance(data, list):
        raise ValueError(
            f"Feedback file must contain a JSON array of objects: {feedback_path}"
        )

    items: List[FeedbackItem] = []
    for obj in data:
        try:
            items.append(FeedbackItem(**obj))
        except Exception as e:
            raise ValueError(f"Invalid feedback item in {feedback_path}: {e}")
    return items


def load_research_questions(rq_path: Path) -> List[str]:
    """Load research questions from RQ.txt file.

    Each line is treated as a separate research question.
    Empty lines and leading/trailing whitespace are ignored.

    If the file does not exist, returns an empty list.
    """
    if not rq_path.exists():
        return []
    with open(rq_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines() if line.strip()]
