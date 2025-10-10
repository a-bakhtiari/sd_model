"""Utilities for managing MDL enhancement versions and metadata."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def generate_theory_abbreviations(theories: List[Dict]) -> str:
    """Generate abbreviated theory names for folder naming.

    Args:
        theories: List of theory dictionaries with 'theory_name' key

    Returns:
        Underscore-separated abbreviations (e.g., "CoP_SECI_SocCap")
    """
    abbreviations = []

    for theory in theories:
        name = theory.get("theory_name", "Unknown")

        # Extract meaningful parts and abbreviate
        if "Communities of Practice" in name or "Wenger" in name:
            abbreviations.append("CoP")
        elif "SECI" in name or "Nonaka" in name:
            abbreviations.append("SECI")
        elif "Social Capital" in name:
            abbreviations.append("SocCap")
        elif "Organizational Learning" in name:
            abbreviations.append("OrgLearn")
        elif "Knowledge Management" in name:
            abbreviations.append("KM")
        elif "Network" in name:
            abbreviations.append("Network")
        else:
            # Fallback: use first 3-4 chars of first significant word
            words = [w for w in name.split() if len(w) > 3]
            if words:
                abbreviations.append(words[0][:4].title())
            else:
                abbreviations.append("Theory")

    # Remove duplicates while preserving order
    seen = set()
    unique_abbr = []
    for abbr in abbreviations:
        if abbr not in seen:
            seen.add(abbr)
            unique_abbr.append(abbr)

    return "_".join(unique_abbr) if unique_abbr else "Enhanced"


def create_enhancement_folder(
    mdl_dir: Path,
    theory_enh_data: Dict
) -> Path:
    """Create timestamped enhancement folder.

    Args:
        mdl_dir: Base MDL directory (e.g., projects/oss_model/mdl)
        theory_enh_data: Theory enhancement JSON data

    Returns:
        Path to the created enhancement folder
    """
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Extract theories from enhancement data
    theories = []
    for missing in theory_enh_data.get("missing_from_theories", []):
        theories.append({"theory_name": missing.get("theory_name", "")})

    # Generate theory abbreviations
    theory_abbr = generate_theory_abbreviations(theories)

    # Create folder name
    folder_name = f"{timestamp}_{theory_abbr}"

    # Create the enhanced directory and subfolder
    enhanced_dir = mdl_dir / "enhanced"
    enhancement_folder = enhanced_dir / folder_name

    enhancement_folder.mkdir(parents=True, exist_ok=True)

    return enhancement_folder


def create_enhancement_log(
    theory_enh_data: Dict,
    mdl_summary: Dict,
    original_mdl_name: str,
    artifacts_dir: Path
) -> Dict:
    """Create detailed enhancement log metadata.

    Args:
        theory_enh_data: Theory enhancement JSON data
        mdl_summary: Summary from apply_theory_enhancements
        original_mdl_name: Name of original MDL file
        artifacts_dir: Path to artifacts directory

    Returns:
        Dictionary containing enhancement log metadata
    """
    # Extract theory information
    theories_applied = []

    for missing in theory_enh_data.get("missing_from_theories", []):
        theory_name = missing.get("theory_name", "Unknown")

        # Count variables and connections for this theory
        sd_impl = missing.get("sd_implementation", {})
        vars_count = len(sd_impl.get("new_variables", []))
        conns_count = len(sd_impl.get("new_connections", []))

        theories_applied.append({
            "name": theory_name,
            "element_added": missing.get("missing_element", ""),
            "why_important": missing.get("why_important", ""),
            "variables_added": vars_count,
            "connections_added": conns_count
        })

    # Build log structure
    log = {
        "timestamp": datetime.now().isoformat(),
        "original_mdl": original_mdl_name,
        "theories_applied": theories_applied,
        "summary": {
            "total_variables_added": mdl_summary.get("variables_added", 0),
            "total_connections_added": mdl_summary.get("connections_added", 0),
            "total_theories": len(theories_applied)
        },
        "source_artifacts": {
            "theory_enhancement": str(artifacts_dir / "theory" / "theory_enhancement.json"),
            "theory_enhancement_mdl": str(artifacts_dir / "theory" / "theory_enhancement_mdl.json")
        },
        "mdl_generation_details": mdl_summary
    }

    return log


def update_latest_symlink(enhanced_dir: Path, target_folder: Path) -> None:
    """Create or update 'latest' symlink to point to most recent enhancement.

    Args:
        enhanced_dir: Base enhanced directory (e.g., projects/oss_model/mdl/enhanced)
        target_folder: Folder to point to (just the folder name, not full path)
    """
    latest_link = enhanced_dir / "latest"

    # Remove existing symlink if it exists
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()

    # Create new symlink (relative path for portability)
    try:
        os.symlink(target_folder.name, latest_link, target_is_directory=True)
    except OSError:
        # On Windows or systems without symlink support, just skip
        pass


def save_enhancement(
    mdl_dir: Path,
    artifacts_dir: Path,
    theory_enh_data: Dict,
    mdl_summary: Dict,
    enhanced_mdl_content: str,
    original_mdl_name: str
) -> Path:
    """Save enhanced MDL with metadata to timestamped folder.

    Args:
        mdl_dir: Base MDL directory
        artifacts_dir: Artifacts directory for source references
        theory_enh_data: Theory enhancement JSON data
        mdl_summary: Summary from MDL generation
        enhanced_mdl_content: Content of enhanced MDL file
        original_mdl_name: Name of original MDL file

    Returns:
        Path to saved enhanced MDL file
    """
    # Create enhancement folder
    enhancement_folder = create_enhancement_folder(mdl_dir, theory_enh_data)

    # Save enhanced MDL
    mdl_filename = f"{Path(original_mdl_name).stem}_enhanced.mdl"
    enhanced_mdl_path = enhancement_folder / mdl_filename
    enhanced_mdl_path.write_text(enhanced_mdl_content, encoding="utf-8")

    # Create and save log
    log = create_enhancement_log(
        theory_enh_data,
        mdl_summary,
        original_mdl_name,
        artifacts_dir
    )
    log_path = enhancement_folder / "enhancement_log.json"
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")

    # Update latest symlink
    update_latest_symlink(mdl_dir / "enhanced", enhancement_folder)

    return enhanced_mdl_path
