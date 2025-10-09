from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple
import base64

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html
import graphviz

from .config import load_config
from .paths import for_project
from .llm.client import LLMClient
from .pipeline.citation_verification import verify_all_citations, generate_connection_citation_table
from .pipeline.gap_analysis import identify_gaps, suggest_search_queries_llm
from .pipeline.paper_discovery import search_papers_for_connection
from .pipeline.theory_assistant import create_theory_from_paper, save_theory_yaml, add_paper_to_bibliography
from .external.semantic_scholar import SemanticScholarClient


MERMAID_SCRIPT = """
<script type=\"module\">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  window.mermaid = mermaid;
</script>
"""


def list_projects() -> List[str]:
    cfg = load_config()
    projects: List[str] = []
    if cfg.projects_dir.exists():
        for p in sorted(cfg.projects_dir.iterdir()):
            if p.is_dir():
                projects.append(p.name)
    return projects


def _load_existing_artifacts(project: str) -> Dict[str, Path]:
    """Load existing artifacts without running the pipeline."""
    cfg = load_config()
    paths = for_project(cfg, project)

    # Return paths to existing artifacts
    return {
        "parsed": paths.parsed_path,
        "connections": paths.connections_path,
        "theory_validation": paths.theory_validation_path,
        "artifacts_dir": paths.artifacts_dir,
        "db_path": paths.db_dir / "provenance.sqlite",
        "variables_llm": paths.artifacts_dir / "variables_llm.json",
        "connections_llm": paths.artifacts_dir / "connections_llm.json",
    }


@st.cache_data(show_spinner=False)
def load_stage1(project: str) -> Dict:
    """Load existing artifacts from disk (does not run pipeline)."""
    refs = _load_existing_artifacts(project)

    # Load JSON files with error handling
    def safe_load(path: Path, default=None):
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return default if default is not None else {}

    parsed = safe_load(refs["parsed"])
    cons = safe_load(refs["connections"])
    tv = safe_load(refs["theory_validation"])
    variables_llm = safe_load(refs["variables_llm"])
    connections_llm = safe_load(refs["connections_llm"])

    return {
        "parsed": parsed,
        "connections": cons,
        "theory_validation": tv,
        "variables_llm": variables_llm,
        "connections_llm": connections_llm,
        "artifacts_dir": str(refs["artifacts_dir"]),
        "db_path": str(refs["db_path"]),
    }


def _df_connections(cons: Dict) -> pd.DataFrame:
    rows = cons.get("connections", [])
    return pd.DataFrame(rows, columns=["from_var", "to_var", "relationship"]).fillna("")


def _df_theories(tv: Dict) -> Tuple[pd.DataFrame, pd.DataFrame]:
    # Reconstruct per-theory from confirmed+missing using (theory, citation_key)
    confirmed = tv.get("confirmed", [])
    missing = tv.get("missing", [])
    merged = confirmed + missing
    # Theory summary
    summary_rows = {}
    for r in merged:
        key = (r.get("theory"), r.get("citation_key"))
        summary_rows.setdefault(key, 0)
        summary_rows[key] += 1
    th_rows = [
        {"theory_name": k[0], "citation_key": k[1], "expected_links": v}
        for k, v in summary_rows.items()
    ]
    df_theories = pd.DataFrame(th_rows, columns=["theory_name", "citation_key", "expected_links"]).sort_values("theory_name")
    # Expected connections table
    exp_rows = [
        {
            "theory": r.get("theory"),
            "from_var": r.get("from_var"),
            "to_var": r.get("to_var"),
            "relationship": r.get("relationship"),
            "status": "present" if r in confirmed else "missing",
        }
        for r in merged
    ]
    df_expected = pd.DataFrame(exp_rows, columns=["theory", "from_var", "to_var", "relationship", "status"])
    return df_theories, df_expected


@st.cache_data(show_spinner=False)
def _connection_graphviz(selected_var: str, connections: List[Dict], var_types: Dict[str, str]) -> graphviz.Digraph:
    """Generate Graphviz diagram for connection explorer with SD conventions."""
    # Check if selected is a Flow (can't be center node)
    selected_type = var_types.get(selected_var, "Auxiliary").lower()
    if selected_type == "flow":
        # Return error diagram
        dot = graphviz.Digraph()
        dot.attr(bgcolor='#fdfaf3')
        dot.node('error', 'Flow variables\nare shown on arrows,\nnot as nodes', shape='box', style='rounded,filled', fillcolor='#fee2e2', color='#dc2626')
        return dot

    dot = graphviz.Digraph(engine='dot')
    dot.attr(bgcolor='#fdfaf3', rankdir='LR', overlap='false', splines='true')
    dot.attr('node', fontname='Arial', fontsize='12', style='filled')
    dot.attr('edge', fontname='Arial', fontsize='7', labelfloat='true')

    # Find all edges involving selected variable
    incoming = [c for c in connections if c.get("to_var") == selected_var]
    outgoing = [c for c in connections if c.get("from_var") == selected_var]

    # Cloud counter for flows
    cloud_counter = 0

    # Add center node
    if selected_type == "stock":
        dot.node(selected_var, selected_var, shape='box', fillcolor='#dbeafe', color='#3b82f6', penwidth='2.5')
    elif selected_type == "parameter":
        dot.node(selected_var, selected_var, shape='box', style='rounded,filled', fillcolor='#fef9c3', color='#f59e0b', penwidth='2.5')
    else:  # auxiliary
        dot.node(selected_var, selected_var, shape='ellipse', fillcolor='#ffffff', color='#6b7280', penwidth='2.5')

    nodes_added = {selected_var}

    # Process incoming edges
    for c in incoming:
        src = c.get("from_var")
        rel = c.get("relationship", "unknown").lower()
        src_type = var_types.get(src, "Auxiliary").lower()

        if src_type == "flow":
            # Flow as edge label with cloud node
            cloud_counter += 1
            cloud_id = f"cloud_{cloud_counter}"
            dot.node(cloud_id, '', shape='circle', width='0.25', height='0.25', fillcolor='#eff6ff', color='#93c5fd', style='dashed,filled')

            # Flow direction: if negative, stock drains to cloud; if positive, cloud feeds stock
            polarity = "−" if rel == "negative" else "+"
            if rel == "negative":
                dot.edge(selected_var, cloud_id, label=f"{src} ({polarity})", color='#3b82f6', penwidth='1.5', arrowhead='odot')
            else:
                dot.edge(cloud_id, selected_var, label=f"{src} ({polarity})", color='#3b82f6', penwidth='1.5')
        else:
            # Regular node
            if src not in nodes_added:
                if src_type == "stock":
                    dot.node(src, src, shape='box', fillcolor='#dbeafe', color='#3b82f6', penwidth='2')
                elif src_type == "parameter":
                    dot.node(src, src, shape='box', style='rounded,filled', fillcolor='#fef9c3', color='#f59e0b', penwidth='2')
                else:
                    dot.node(src, src, shape='ellipse', fillcolor='#ffffff', color='#6b7280', penwidth='2')
                nodes_added.add(src)

            polarity = "−" if rel == "negative" else "+"
            if rel == "negative":
                dot.edge(src, selected_var, label=polarity, color='#3b82f6', penwidth='1.5', arrowhead='odot')
            else:
                dot.edge(src, selected_var, label=polarity, color='#3b82f6', penwidth='1.5')

    # Process outgoing edges
    for c in outgoing:
        dst = c.get("to_var")
        rel = c.get("relationship", "unknown").lower()
        dst_type = var_types.get(dst, "Auxiliary").lower()

        if dst_type == "flow":
            # Flow as edge label with cloud node
            cloud_counter += 1
            cloud_id = f"cloud_{cloud_counter}"
            dot.node(cloud_id, '', shape='circle', width='0.25', height='0.25', fillcolor='#eff6ff', color='#93c5fd', style='dashed,filled')

            # Flow direction
            polarity = "−" if rel == "negative" else "+"
            if rel == "negative":
                dot.edge(cloud_id, selected_var, label=f"{dst} ({polarity})", color='#3b82f6', penwidth='1.5', arrowhead='odot')
            else:
                dot.edge(selected_var, cloud_id, label=f"{dst} ({polarity})", color='#3b82f6', penwidth='1.5')
        else:
            # Regular node
            if dst not in nodes_added:
                if dst_type == "stock":
                    dot.node(dst, dst, shape='box', fillcolor='#dbeafe', color='#3b82f6', penwidth='2')
                elif dst_type == "parameter":
                    dot.node(dst, dst, shape='box', style='rounded,filled', fillcolor='#fef9c3', color='#f59e0b', penwidth='2')
                else:
                    dot.node(dst, dst, shape='ellipse', fillcolor='#ffffff', color='#6b7280', penwidth='2')
                nodes_added.add(dst)

            polarity = "−" if rel == "negative" else "+"
            if rel == "negative":
                dot.edge(selected_var, dst, label=polarity, color='#3b82f6', penwidth='1.5', arrowhead='odot')
            else:
                dot.edge(selected_var, dst, label=polarity, color='#3b82f6', penwidth='1.5')

    return dot

def _cached_mermaid_diagram(selected: str, edges: Tuple[Tuple[str, str, str], ...], type_pairs: Tuple[Tuple[str, str], ...]) -> str:
    cons = {
        "connections": [
            {"from_var": e[0], "to_var": e[1], "relationship": e[2]}
            for e in edges
        ]
    }
    var_types = dict(type_pairs)
    return _mermaid_diagram(cons, selected, var_types)


def _loop_graphviz(loop_edges: List[Dict[str, str]], var_types: Dict[str, str], theory_status: Dict | None = None) -> graphviz.Digraph:
    """Generate Graphviz diagram for a feedback loop with SD conventions."""
    dot = graphviz.Digraph(engine='circo')  # Circular layout for feedback loops
    dot.attr(bgcolor='#fdfaf3', overlap='false', splines='true')
    dot.attr('node', fontname='Arial', fontsize='12', style='filled')
    dot.attr('edge', fontname='Arial', fontsize='7', labelfloat='true')

    # Build theory lookup
    edge_theory_map = {}
    edge_novel_set = set()
    if theory_status:
        for edge, theory_name, _ in theory_status.get("theory_matched", []):
            key = (edge.get("from_var"), edge.get("to_var"))
            edge_theory_map[key] = theory_name
        for edge in theory_status.get("novel", []):
            key = (edge.get("from_var"), edge.get("to_var"))
            edge_novel_set.add(key)

    # Add nodes (skip flows - they'll be on edges)
    nodes_added = set()
    cloud_counter = 0
    cloud_nodes = {}

    for edge in loop_edges:
        for var_name in [edge.get("from_var", ""), edge.get("to_var", "")]:
            if not var_name or var_name in nodes_added:
                continue

            node_type = var_types.get(var_name, "Auxiliary").lower()

            if node_type == "flow":
                # Skip - flows become edge labels with clouds
                continue
            elif node_type == "stock":
                dot.node(var_name, var_name, shape='box', fillcolor='#dbeafe', color='#3b82f6', penwidth='2')
            elif node_type == "parameter":
                dot.node(var_name, var_name, shape='box', style='rounded,filled', fillcolor='#fef9c3', color='#f59e0b', penwidth='2')
            else:  # auxiliary
                dot.node(var_name, var_name, shape='ellipse', fillcolor='#ffffff', color='#6b7280', penwidth='2')

            nodes_added.add(var_name)

    # Add edges (handle flows specially)
    for edge in loop_edges:
        src = edge.get("from_var", "")
        dst = edge.get("to_var", "")
        rel = edge.get("relationship", "unknown").lower()

        if not src or not dst:
            continue

        src_type = var_types.get(src, "Auxiliary").lower()
        dst_type = var_types.get(dst, "Auxiliary").lower()

        # Handle flows in edges
        if src_type == "flow" or dst_type == "flow":
            # Create cloud node for flow
            cloud_counter += 1
            cloud_id = f"flow_cloud_{cloud_counter}"
            dot.node(cloud_id, '', shape='circle', width='0.25', height='0.25', fillcolor='#eff6ff', color='#93c5fd', style='dashed,filled')

            polarity = "−" if rel == "negative" else "+"

            if src_type == "flow":
                # Flow from cloud to dst
                flow_name = src
                actual_dst = dst
                if rel == "negative":
                    dot.edge(actual_dst, cloud_id, label=f"{flow_name} ({polarity})", color='#3b82f6', penwidth='1.5', arrowhead='odot')
                else:
                    dot.edge(cloud_id, actual_dst, label=f"{flow_name} ({polarity})", color='#3b82f6', penwidth='1.5')
            else:  # dst_type == "flow"
                # Flow from src to cloud
                flow_name = dst
                actual_src = src
                if rel == "negative":
                    dot.edge(cloud_id, actual_src, label=f"{flow_name} ({polarity})", color='#3b82f6', penwidth='1.5', arrowhead='odot')
                else:
                    dot.edge(actual_src, cloud_id, label=f"{flow_name} ({polarity})", color='#3b82f6', penwidth='1.5')
        else:
            # Regular edge between non-flow nodes
            edge_key = (src, dst)

            # Polarity label
            polarity = "−" if rel == "negative" else "+"

            # Edge styling - all blue with polarity
            if rel == "negative":
                edge_attrs = {'color': '#3b82f6', 'penwidth': '1.5', 'arrowhead': 'odot'}
            else:
                edge_attrs = {'color': '#3b82f6', 'penwidth': '1.5'}

            # Build label with polarity
            label = polarity

            dot.edge(src, dst, label=label, **edge_attrs)

    return dot

def _loop_mermaid(loop_edges: List[Dict[str, str]], var_types: Dict[str, str], theory_status: Dict | None = None) -> str:
    """Generate Mermaid diagram for a feedback loop with optional theory indicators.

    Args:
        loop_edges: List of edge dictionaries with from_var, to_var, relationship
        var_types: Variable name to type mapping
        theory_status: Optional dict with 'theory_matched' and 'novel' edge lists
    """
    if not loop_edges:
        return "flowchart TD\n  empty((Loop edges missing)):::muted"

    lines = [
        "flowchart TD",
        "  classDef muted fill:#f3f4f6,color:#6b7280,font-size:12px",
        "  classDef stock fill:#eef2ff,color:#1e1b4b,stroke:#4338ca,stroke-width:2px,font-size:14px",
        "  classDef aux fill:#ffffff,color:#1f2937,stroke:#111827,stroke-width:2px,font-size:14px",
        "  classDef parameter fill:#fef3c7,color:#78350f,stroke:#b45309,stroke-width:2px,font-size:14px",
        "  classDef center stroke:#1d4ed8,stroke-width:3px",
        "  classDef theory_edge stroke:#10b981,stroke-width:3px",
        "  classDef novel_edge stroke:#f59e0b,stroke-width:2px,stroke-dasharray:5 5",
    ]

    # Build edge theory lookup if provided
    edge_theory_map = {}
    edge_novel_set = set()
    if theory_status:
        for edge, theory_name, _ in theory_status.get("theory_matched", []):
            key = (edge.get("from_var"), edge.get("to_var"), edge.get("relationship"))
            edge_theory_map[key] = theory_name
        for edge in theory_status.get("novel", []):
            key = (edge.get("from_var"), edge.get("to_var"), edge.get("relationship"))
            edge_novel_set.add(key)

    nodes_added: set[str] = set()

    def ensure_node(name: str) -> str | None:
        node_id, label = _sanitize_node(name)
        if node_id in nodes_added:
            return node_id
        node_type = var_types.get(name, "Auxiliary")
        shape, cls = _node_markup(label, node_type)
        if not shape:
            return None
        lines.append(f"  {node_id}{shape}")
        lines.append(f"  class {node_id} {cls}")
        nodes_added.add(node_id)
        return node_id

    first_node_id: str | None = None
    for edge in loop_edges:
        src = edge.get("from_var", "")
        dst = edge.get("to_var", "")
        rel = edge.get("relationship", "unknown")
        src_id = ensure_node(src)
        dst_id = ensure_node(dst)
        if not src_id or not dst_id:
            continue
        if first_node_id is None:
            first_node_id = src_id

        # Create edge with optional theory annotation
        edge_key = (src, dst, rel)
        if edge_key in edge_theory_map:
            theory_label = f" [{edge_theory_map[edge_key][:20]}]"
            lines.append(f"  {src_id}{_arrow_segment(rel, theory_label)}{dst_id}")
        elif edge_key in edge_novel_set:
            lines.append(f"  {src_id}{_arrow_segment(rel, ' [Novel]')}{dst_id}")
        else:
            lines.append(f"  {src_id}{_arrow_segment(rel)}{dst_id}")

    if first_node_id:
        lines.append(f"  class {first_node_id} center")
    else:
        return "flowchart LR\n  empty((Loop nodes missing)):::muted"

    return "\n".join(lines)


@st.cache_data(show_spinner=False)
def _classify_loop_api(
    edges: Tuple[Tuple[str, str, str], ...],
    variables: Tuple[str, ...],
    description: str,
) -> Dict[str, str]:
    """Call the LLM client to classify a loop's polarity."""
    allowed = {"reinforcing", "balancing", "undetermined"}

    client = LLMClient()
    if not client.enabled:
        return {
            "type": "undetermined",
            "reason": "LLM client disabled; classification unavailable.",
            "source": "disabled",
        }

    edges_text = "\n".join(
        f"- {src} → {dst} ({rel})"
        for src, dst, rel in edges
    )
    vars_text = ", ".join(variables) if variables else "N/A"
    prompt = (
        "You are a system dynamics analyst. Classify the feedback loop type.\n"
        "Return JSON with keys: type (reinforcing|balancing|undetermined) and reason.\n"
        "If you are unsure, choose undetermined.\n"
        f"Variables (ordered): {vars_text}\n"
        f"Loop edges:\n{edges_text}\n"
        f"Loop context: {description or 'n/a'}"
    )
    response = client.complete(prompt)

    parsed: Dict[str, str] = {}
    if response:
        try:
            parsed = json.loads(response)
        except Exception:
            try:
                start = response.find("{")
                end = response.rfind("}")
                if start != -1 and end != -1 and end > start:
                    parsed = json.loads(response[start : end + 1])
            except Exception:
                parsed = {}

    loop_type = str(parsed.get("type", "")).strip().lower()
    if loop_type not in allowed:
        return {
            "type": "undetermined",
            "reason": f"Unexpected response: {response[:160]}",
            "source": "invalid_response",
        }

    reason = (
        str(parsed.get("reason") or parsed.get("rationale") or parsed.get("explanation") or "")
        .strip()
    )

    return {
        "type": loop_type,
        "reason": reason,
        "source": "api",
    }


def _match_loop_edges_to_theories(loop_edges: List[Dict], theory_validation: Dict) -> Dict:
    """Match loop edges to theory validation data.

    Returns:
        {
            "theory_matched": [(edge, theory_name, citation_key), ...],
            "novel": [edge, ...],
            "coverage_pct": 0-100,
            "theories_applied": [theory_name, ...]
        }
    """
    confirmed = theory_validation.get("confirmed", [])
    novel = theory_validation.get("novel", [])

    theory_matched = []
    novel_edges = []
    theories_applied = set()

    for edge in loop_edges:
        from_var = edge.get("from_var", "")
        to_var = edge.get("to_var", "")
        relationship = edge.get("relationship", "")

        # Check if this edge is theory-confirmed
        match = None
        for conf in confirmed:
            if (conf.get("from_var") == from_var and
                conf.get("to_var") == to_var and
                conf.get("relationship") == relationship):
                match = conf
                break

        if match:
            theory_name = match.get("theory", "Unknown")
            citation_key = match.get("citation_key", "")
            theories_applied.add(theory_name)
            theory_matched.append((edge, theory_name, citation_key))
        else:
            # Check if it's a novel connection
            is_novel = any(
                n.get("from_var") == from_var and
                n.get("to_var") == to_var and
                n.get("relationship") == relationship
                for n in novel
            )
            if is_novel:
                novel_edges.append(edge)

    total_edges = len(loop_edges)
    coverage_pct = int((len(theory_matched) / total_edges * 100)) if total_edges > 0 else 0

    return {
        "theory_matched": theory_matched,
        "novel": novel_edges,
        "coverage_pct": coverage_pct,
        "theories_applied": sorted(list(theories_applied)),
    }


@st.cache_data(show_spinner=False)
def _enhanced_loop_analysis_llm(
    edges_tuple: Tuple[Tuple[str, str, str], ...],
    variables_tuple: Tuple[str, ...],
    description: str,
    theory_matches: Tuple[Tuple[str, str], ...],  # (theory_name, citation_key)
    novel_count: int,
    loop_type: str,
) -> Dict[str, str]:
    """Generate comprehensive loop analysis with theory context."""
    client = LLMClient()
    if not client.enabled:
        return {
            "behavioral_explanation": "LLM analysis unavailable (client disabled).",
            "system_impact": "unknown",
            "key_insight": "Enable LLM client for detailed analysis.",
            "intervention": "",
        }

    edges_text = "\n".join(f"- {src} → {dst} ({rel})" for src, dst, rel in edges_tuple)
    vars_text = ", ".join(variables_tuple) if variables_tuple else "N/A"

    theory_text = ""
    if theory_matches:
        theory_list = "\n".join(f"- {name} ({citation})" for name, citation in theory_matches)
        theory_text = f"\n\nTheory Support ({len(theory_matches)} edges confirmed):\n{theory_list}"

    novel_text = f"\n\nNovel Connections: {novel_count} edges are not predicted by current theories." if novel_count > 0 else ""

    prompt = f"""You are analyzing a feedback loop in an open-source software (OSS) community model.

Loop Description: {description}
Loop Type: {loop_type}
Variables: {vars_text}

Edges:
{edges_text}{theory_text}{novel_text}

Please provide a comprehensive analysis in JSON format with these keys:
1. "behavioral_explanation": 2-3 sentences explaining how this loop behaves and what dynamics it creates
2. "system_impact": One word - "positive", "negative", or "mixed"
3. "key_insight": One concise sentence capturing the most important takeaway
4. "intervention": Optional - suggest where to intervene if this loop is problematic (or empty string)

Return ONLY valid JSON."""

    response = client.complete(prompt, temperature=0.3)

    # Parse JSON response
    try:
        return json.loads(response)
    except Exception:
        try:
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                return json.loads(response[start:end+1])
        except Exception:
            pass

    # Fallback
    return {
        "behavioral_explanation": f"This {loop_type} loop involves {len(variables_tuple)} variables and creates feedback dynamics in the system.",
        "system_impact": "mixed",
        "key_insight": "Detailed analysis requires LLM with valid JSON output.",
        "intervention": "",
    }


def _normalize_loops(raw: Dict) -> Dict[str, List[Dict]]:
    normalized = {
        "balancing": [],
        "reinforcing": [],
        "undetermined": [],
        "notes": [],
    }
    if not isinstance(raw, dict):
        return normalized

    for bucket in ("balancing", "reinforcing", "undetermined"):
        values = raw.get(bucket, [])
        bucket_items: List[Dict] = []
        if isinstance(values, list):
            for idx, entry in enumerate(values):
                if isinstance(entry, dict):
                    loop_dict = {
                        "id": entry.get("id") or f"{bucket[:1].upper()}-{idx + 1}",
                        "description": entry.get("description") or "",
                        "variables": entry.get("variables") or [],
                        "edges": entry.get("edges") or [],
                        "length": entry.get("length") or len(entry.get("variables") or []),
                        "negative_edges": entry.get("negative_edges"),
                        "polarity": entry.get("polarity") or bucket,
                    }
                else:
                    text = str(entry)
                    loop_dict = {
                        "id": f"{bucket[:1].upper()}-{idx + 1}",
                        "description": text,
                        "variables": [],
                        "edges": [],
                        "length": 0,
                        "negative_edges": None,
                        "polarity": bucket,
                    }
                bucket_items.append(loop_dict)
        normalized[bucket] = bucket_items

    notes = raw.get("notes", [])
    if isinstance(notes, list):
        normalized["notes"] = [str(n) for n in notes]
    elif notes:
        normalized["notes"] = [str(notes)]

    return normalized


def _sanitize_node(name: str) -> Tuple[str, str]:
    cleaned = name.strip()
    cleaned = (
        cleaned.replace("\"", "")
        .replace("'", "")
        .replace("\n", " ")
        .replace("[", "(")
        .replace("]", ")")
        .replace("{", "(")
        .replace("}", ")")
    )
    cleaned = " ".join(cleaned.split())
    identifier = "node_" + "_".join(
        ch.lower() if ch.isalnum() else "_" for ch in cleaned
    )
    identifier = "_".join(filter(None, identifier.split("_"))) or "node"
    return identifier, cleaned


def _escape_label(text: str) -> str:
    stripped = text.replace("(", "").replace(")", "")
    return stripped.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _relationship_polarity(rel: str) -> str:
    rel = (rel or "").lower()
    if rel.startswith("pos") or rel.startswith("increase"):
        return "positive"
    if rel.startswith("neg") or rel.startswith("decrease"):
        return "negative"
    return "unknown"


def _arrow_segment(rel: str, label: str = "") -> str:
    polarity = _relationship_polarity(rel)
    label = _escape_label((label or "").strip())
    if polarity == "positive":
        value = (label + " (+)").strip() or "(+)"
        return f' -- "{value}" --> '
    if polarity == "negative":
        value = (label + " (-)").strip() or "(-)"
        return f' -- "{value}" --> '
    value = label or " "
    return f' -. "{value}" .-> '


def _node_markup(label: str, node_type: str) -> Tuple[str, str]:
    safe = _escape_label(label)
    node_type = (node_type or "aux").lower()
    if node_type == "stock":
        return f"[{safe}]", "stock"
    if node_type in {"aux", "auxiliary"}:
        return f"(({safe}))", "aux"
    if node_type == "parameter":
        return f"([{safe}])", "parameter"
    if node_type == "flow":
        return f"(({safe}))", "aux"  # Render flows like auxiliary variables
    return f"(({safe}))", "aux"  # Default fallback


def _render_mermaid(diagram_code: str, container_key: str, *, height: int = 520) -> None:
    container_id, _ = _sanitize_node(container_key)
    diagram_html = f"""
    <style>
      .mermaid-wrapper {{
        background: #fdfaf3;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.5rem;
      }}
    </style>
    <div id='{container_id}' class='mermaid-wrapper' style='height: {height}px; overflow: auto;'>
      <div class='mermaid'>
      {diagram_code}
      </div>
    </div>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' }});
      mermaid.run({{ nodes: document.querySelectorAll('#{container_id} .mermaid') }});
    </script>
    """
    html(diagram_html, height=height + 10)


def _mermaid_diagram(cons: Dict, selected: str, var_types: Dict[str, str]) -> str:
    df = _df_connections(cons)
    if df.empty or not selected:
        return "flowchart LR\\n  empty((No data)):::muted"

    lines = [
        "flowchart LR",
        "  classDef muted fill:#f3f4f6,color:#6b7280,font-size:12px",
        "  classDef stock fill:#eef2ff,color:#1e1b4b,stroke:#4338ca,stroke-width:2px,font-size:14px",
        "  classDef aux fill:#ffffff,color:#1f2937,stroke:#111827,stroke-width:2px,font-size:14px",
        "  classDef parameter fill:#fef3c7,color:#78350f,stroke:#b45309,stroke-width:2px,font-size:14px",
        "  classDef center stroke:#1d4ed8,stroke-width:3px",
        "  classDef cloud fill:#f0f9ff,color:#0369a1,stroke:#0ea5e9,stroke-width:2px,font-size:12px,stroke-dasharray:4 4,padding:6px",
    ]

    nodes_added: set[str] = set()
    cloud_nodes: Dict[str, str] = {}
    cloud_counter = 0

    def ensure_node(name: str) -> str | None:
        node_id, label = _sanitize_node(name)
        if node_id in nodes_added:
            return node_id
        node_type = var_types.get(name, "Auxiliary")
        shape, cls = _node_markup(label, node_type)
        if not shape:
            return None
        lines.append(f"  {node_id}{shape}")
        lines.append(f"  class {node_id} {cls}")
        nodes_added.add(node_id)
        return node_id

    def ensure_cloud(key: str) -> str:
        nonlocal cloud_counter
        if key not in cloud_nodes:
            cloud_counter += 1
            cloud_id = f"cloud_{cloud_counter}"
            lines.append(f"  {cloud_id}(( )):::cloud")
            cloud_nodes[key] = cloud_id
        return cloud_nodes[key]

    selected_type = var_types.get(selected, "Auxiliary").lower()
    if selected_type == "flow":
        return "flowchart LR\\n  note[Flow variables are shown on arrows, not as nodes.]:::muted"

    center_id = ensure_node(selected)
    if not center_id:
        return "flowchart LR\\n  note[Unable to render this variable]:::muted"
    lines.append(f"  class {center_id} center")

    incoming = df[df["to_var"] == selected]
    if incoming.empty:
        placeholder = ensure_cloud(f"{selected}_incoming")
        lines.append(f'  {placeholder} -. " " .-> {center_id}')
    else:
        for _, row in incoming.iterrows():
            source = row["from_var"]
            src_type = var_types.get(source, "Auxiliary").lower()
            rel = row["relationship"]
            if src_type == "flow":
                pol = _relationship_polarity(rel)
                seg = _arrow_segment(rel, source)
                if pol == "negative":
                    cloud_id = ensure_cloud(f"{source}_sink")
                    lines.append(f"  {center_id}{seg}{cloud_id}")
                else:
                    cloud_id = ensure_cloud(f"{source}_source")
                    lines.append(f"  {cloud_id}{seg}{center_id}")
                continue
            src_id = ensure_node(source)
            if not src_id:
                continue
            seg = _arrow_segment(rel, "")
            lines.append(f"  {src_id}{seg}{center_id}")

    outgoing = df[df["from_var"] == selected]
    if outgoing.empty:
        placeholder = ensure_cloud(f"{selected}_outgoing")
        lines.append(f'  {center_id} -. " " .-> {placeholder}')
    else:
        for _, row in outgoing.iterrows():
            target = row["to_var"]
            dst_type = var_types.get(target, "Auxiliary").lower()
            rel = row["relationship"]
            if dst_type == "flow":
                cloud_id = ensure_cloud(f"{target}_sink")
                seg = _arrow_segment(rel, target)
                lines.append(f"  {center_id}{seg}{cloud_id}")
                continue
            dst_id = ensure_node(target)
            if not dst_id:
                continue
            seg = _arrow_segment(rel, "")
            lines.append(f"  {center_id}{seg}{dst_id}")

    return "\n".join(lines)


def _artifact_cards(parsed: Dict, cons: Dict, tv: Dict) -> None:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Variables", f"{len(parsed.get('variables', []))}")
    with c2:
        st.metric("Connections", f"{len(cons.get('connections', []))}")
    with c3:
        th_count = tv.get("summary", {}).get("theory_count", 0)
        st.metric("Theories", f"{th_count}")
    with c4:
        bib = tv.get("bibliography_loaded", False)
        st.metric("Bibliography", "Loaded" if bib else "Missing")


def _last_provenance_events(db_path: Path, limit: int = 5) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame(columns=["ts", "event", "payload"])  # empty
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT ts, event, payload FROM provenance ORDER BY ts DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
    finally:
        conn.close()
    return pd.DataFrame(rows, columns=["ts", "event", "payload"])


def main() -> None:
    st.set_page_config(page_title="SD Model Pipeline", layout="wide")
    st.title("System Dynamics Model – Pipeline")

    st.markdown(MERMAID_SCRIPT, unsafe_allow_html=True)

    projects = list_projects()
    if not projects:
        st.warning("No projects found in projects/.")
        return

    # Persist last selected project in session
    if "project" not in st.session_state:
        st.session_state["project"] = projects[0]
    project = st.selectbox("Project", projects, index=projects.index(st.session_state["project"]))
    st.session_state["project"] = project

    # Tabs
    dashboard_tab, stage2_tab, citation_tab, discovery_tab, stage3_tab = st.tabs([
        "Connection Explorer",
        "Loop Explorer",
        "Citation Verification",
        "Paper Discovery",
        "Stage 3"
    ])

    with dashboard_tab:
        # Load existing artifacts (no pipeline execution)
        try:
            data = load_stage1(project)
        except Exception as e:
            st.error(f"Failed to load artifacts: {e}")
            st.info("💡 Make sure you've run the pipeline first to generate artifacts.")
            return

        parsed = data["parsed"]
        cons = data["connections"]
        tv = data["theory_validation"]
        variables_llm = data.get("variables_llm", {"variables": []})
        connections_llm = data.get("connections_llm", {"connections": []})
        id_to_name = {int(v["id"]): v["name"] for v in variables_llm.get("variables", [])}
        name_to_type = {v["name"]: v.get("type", "Auxiliary") for v in variables_llm.get("variables", [])}

        st.subheader("Connections Explorer")
        df_conn = _df_connections(cons)
        connected = sorted(set(df_conn["from_var"]).union(df_conn["to_var"]))
        var_types = {var: name_to_type.get(var, "Auxiliary") for var in connected}
        var_labels = {
            var: f"{var} ({var_types.get(var, 'Auxiliary')})" for var in connected
        }
        variables = [
            v for v in connected
            if name_to_type.get(v) and var_types.get(v, "auxiliary").lower() != "flow"
        ]

        if not variables:
            st.info("No connected variables to display yet.")
        else:
            vkey = f"selected_var::{project}"
            if vkey not in st.session_state or st.session_state[vkey] not in variables:
                st.session_state[vkey] = variables[0]

            selector_col, diagram_col = st.columns([1, 3])

            with selector_col:
                current_sel = st.session_state.get(vkey, variables[0])
                if current_sel not in variables:
                    current_sel = variables[0]

                sel_var = st.selectbox(
                    "Select variable (type to search)",
                    variables,
                    index=variables.index(current_sel) if current_sel in variables else 0,
                    key=f"var_select::{project}",
                    format_func=lambda v: var_labels.get(v, v),
                )
                st.session_state[vkey] = sel_var

                sel_type = var_types.get(sel_var, "Auxiliary")
                st.caption(f"**Type:** {sel_type}")

            with diagram_col:
                # Render diagram with Graphviz
                connections_list = cons.get("connections", [])
                dot = _connection_graphviz(sel_var, connections_list, var_types)
                st.graphviz_chart(dot, use_container_width=True)

    with stage2_tab:
        # Load theory validation data for integration
        tv_value = data.get("theory_validation")
        if isinstance(tv_value, dict):
            tv_data = tv_value
        else:
            tv_data = json.loads(Path(tv_value).read_text(encoding="utf-8"))

        st.subheader("Loop Explorer")
        loops_path = Path(data["artifacts_dir"]) / "loops.json"
        loops_raw = json.loads(loops_path.read_text(encoding="utf-8")) if loops_path.exists() else {}
        loops_data = _normalize_loops(loops_raw)
        loop_notes = loops_data.get("notes", [])

        # Load loop descriptions
        loop_descriptions_path = Path(data["artifacts_dir"]) / "loop_descriptions.json"
        loop_desc_map = {}
        if loop_descriptions_path.exists():
            desc_data = json.loads(loop_descriptions_path.read_text(encoding="utf-8"))
            for item in desc_data.get("descriptions", []):
                loop_desc_map[item["id"]] = item["description"]

        variables_llm = data.get("variables_llm", {"variables": []})
        name_to_type = {
            v.get("name"): v.get("type", "Auxiliary")
            for v in variables_llm.get("variables", [])
            if isinstance(v, dict) and v.get("name")
        }

        type_order = {"reinforcing": 0, "balancing": 1, "undetermined": 2}
        loop_entries: List[Dict] = []
        for bucket_key, _label in (
            ("reinforcing", "Reinforcing"),
            ("balancing", "Balancing"),
            ("undetermined", "Undetermined"),
        ):
            for loop in loops_data[bucket_key]:
                edges_list = loop.get("edges") or []
                edges_tuple = tuple(
                    (
                        str(edge.get("from_var", "")).strip(),
                        str(edge.get("to_var", "")).strip(),
                        str(edge.get("relationship", "unknown")).strip().lower(),
                    )
                    for edge in edges_list
                    if edge.get("from_var") and edge.get("to_var")
                )
                if not edges_tuple:
                    edges_tuple = tuple(
                        (
                            str(edge.get("from_var", "")).strip(),
                            str(edge.get("to_var", "")).strip(),
                            str(edge.get("relationship", "unknown")).strip().lower(),
                        )
                        for edge in edges_list
                    )
                variables_tuple = tuple(loop.get("variables", []))

                # Use existing classification from loops.json (no LLM call)
                api_type = bucket_key  # Already classified: reinforcing/balancing/undetermined

                # Match loop edges to theories
                theory_match = _match_loop_edges_to_theories(edges_list, tv_data)

                entry = {
                    "id": loop.get("id") or f"{bucket_key[:1].upper()}{len(loop_entries) + 1:02d}",
                    "description": loop.get("description", ""),
                    "variables": list(loop.get("variables", [])),
                    "edges": edges_list,
                    "edges_tuple": edges_tuple,
                    "length": loop.get("length") or len(loop.get("variables") or []),
                    "negative_edges": loop.get("negative_edges"),
                    "api_type": api_type,
                    "classification_reason": loop.get("description", ""),  # Use existing description
                    "classification_source": "loops_json",  # From pre-computed loops.json
                    "theory_coverage": theory_match.get("coverage_pct", 0),
                    "theory_matched": theory_match.get("theory_matched", []),
                    "novel_edges": theory_match.get("novel", []),
                    "theories_applied": theory_match.get("theories_applied", []),
                }
                loop_entries.append(entry)

        if not loop_entries:
            st.info("No feedback loops detected yet.")
        else:
            loop_entries_sorted = sorted(
                loop_entries,
                key=lambda e: (type_order.get(e["api_type"], 3), e["id"]),
            )
            loop_ids = [entry["id"] for entry in loop_entries_sorted]
            loop_key = f"selected_loop::{project}"
            if loop_key not in st.session_state or st.session_state[loop_key] not in loop_ids:
                st.session_state[loop_key] = loop_ids[0]

            selector_col, diagram_col = st.columns([1, 3])

            with selector_col:
                # Build label map
                label_map = {}
                for entry in loop_entries_sorted:
                    label_map[entry["id"]] = f"{entry['id']} · {entry['api_type'].title()}"

                current_loop = st.session_state.get(loop_key, loop_entries_sorted[0]["id"])
                if current_loop not in loop_ids:
                    current_loop = loop_entries_sorted[0]["id"]

                selected_loop_id = st.selectbox(
                    "Select loop (type to search)",
                    loop_ids,
                    index=loop_ids.index(current_loop) if current_loop in loop_ids else 0,
                    key=f"loop_select::{project}",
                    format_func=lambda loop_id: label_map.get(loop_id, loop_id),
                )
                st.session_state[loop_key] = selected_loop_id

                selected_loop = next(
                    (entry for entry in loop_entries if entry["id"] == selected_loop_id),
                    loop_entries_sorted[0],
                )

                loop_type = selected_loop.get("api_type", "").title()
                st.caption(f"**Type:** {loop_type}")

            with diagram_col:
                # Render loop diagram with Graphviz
                theory_status = {
                    "theory_matched": selected_loop.get("theory_matched", []),
                    "novel": selected_loop.get("novel_edges", []),
                }
                dot = _loop_graphviz(selected_loop["edges"], name_to_type, theory_status)

                # Render as SVG
                st.graphviz_chart(dot, use_container_width=True)

                # Show description below diagram
                loop_desc = loop_desc_map.get(selected_loop_id)
                if loop_desc:
                    st.markdown(f"**Description:** {loop_desc}")

    with citation_tab:
        st.markdown("### 📚 Citation Verification")
        st.caption("Verify theory citations via Semantic Scholar API and map connections to supporting literature")

        cfg = load_config()
        paths = for_project(cfg, project)

        citations_verified_path = paths.artifacts_dir / "citations_verified.json"
        connection_citations_path = paths.artifacts_dir / "connection_citations.json"

        # Check if verification has been run
        if not citations_verified_path.exists():
            st.info("Citation verification has not been run yet. Click the button below to verify all citations.")

            if st.button("🔍 Verify All Citations", type="primary"):
                with st.spinner("Verifying citations via Semantic Scholar API..."):
                    try:
                        s2_client = SemanticScholarClient()

                        # Verify citations
                        verified_cits = verify_all_citations(
                            theories_dir=paths.theories_dir,
                            bib_path=paths.references_bib_path,
                            s2_client=s2_client,
                            out_path=citations_verified_path,
                        )

                        # Generate connection-citation table
                        loops_path = paths.artifacts_dir / "loops.json"
                        connection_cits = generate_connection_citation_table(
                            connections_path=paths.connections_path,
                            theories_dir=paths.theories_dir,
                            verified_citations_path=citations_verified_path,
                            loops_path=loops_path,
                            out_path=connection_citations_path,
                        )

                        st.success(f"✅ Verified {len(verified_cits)} citations successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Verification failed: {str(e)}")
        else:
            # Load verification results
            verified_data = json.loads(citations_verified_path.read_text(encoding="utf-8"))
            connection_cits_data = json.loads(connection_citations_path.read_text(encoding="utf-8"))

            # Display summary metrics
            st.markdown("#### Verification Status")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Citations", verified_data.get("total_citations", 0))
            with col2:
                verified_count = verified_data.get("verified_count", 0)
                st.metric("Verified", verified_count, delta=None)
            with col3:
                unverified_count = verified_data.get("unverified_count", 0)
                st.metric("Unverified", unverified_count, delta=None if unverified_count == 0 else f"-{unverified_count}")
            with col4:
                verification_pct = int((verified_count / verified_data.get("total_citations", 1)) * 100)
                st.metric("Verification %", f"{verification_pct}%")

            # Connection citation summary
            st.markdown("---")
            st.markdown("#### Connection Citation Coverage")
            summary = connection_cits_data.get("summary", {})
            cc1, cc2, cc3, cc4 = st.columns(4)
            with cc1:
                st.metric("Total Connections", summary.get("total_connections", 0))
            with cc2:
                st.metric("Verified", summary.get("verified", 0), help="Connections with verified citations")
            with cc3:
                st.metric("Unverified", summary.get("unverified", 0), help="Connections with unverified citations")
            with cc4:
                st.metric("Unsupported", summary.get("unsupported", 0), help="Connections with no citations")

            # Re-verify button
            if st.button("🔄 Re-verify Citations"):
                with st.spinner("Re-verifying..."):
                    try:
                        s2_client = SemanticScholarClient()
                        verified_cits = verify_all_citations(
                            theories_dir=paths.theories_dir,
                            bib_path=paths.references_bib_path,
                            s2_client=s2_client,
                            out_path=citations_verified_path,
                        )
                        loops_path = paths.artifacts_dir / "loops.json"
                        connection_cits = generate_connection_citation_table(
                            connections_path=paths.connections_path,
                            theories_dir=paths.theories_dir,
                            verified_citations_path=citations_verified_path,
                            loops_path=loops_path,
                            out_path=connection_citations_path,
                        )
                        st.success("✅ Re-verification complete!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Re-verification failed: {str(e)}")

            # Citation details table
            st.markdown("---")
            st.markdown("#### Citation Details")

            citations = verified_data.get("citations", {})
            citation_rows = []
            for key, cit in citations.items():
                citation_rows.append({
                    "Citation Key": key,
                    "Status": "✅ Verified" if cit.get("verified") else "❌ Unverified",
                    "Title": cit.get("title", "N/A")[:60] + ("..." if len(cit.get("title", "")) > 60 else ""),
                    "Year": cit.get("year", "N/A"),
                    "Citations": cit.get("citation_count", "N/A"),
                    "Authors": ", ".join(cit.get("authors", [])[:2]) + ("..." if len(cit.get("authors", [])) > 2 else ""),
                })

            citation_df = pd.DataFrame(citation_rows)

            # Filter options
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                status_filter = st.selectbox(
                    "Filter by status",
                    ["All", "Verified", "Unverified"],
                    key="citation_status_filter"
                )
            with filter_col2:
                search_filter = st.text_input(
                    "Search citations",
                    key="citation_search"
                )

            # Apply filters
            filtered_df = citation_df.copy()
            if status_filter == "Verified":
                filtered_df = filtered_df[filtered_df["Status"] == "✅ Verified"]
            elif status_filter == "Unverified":
                filtered_df = filtered_df[filtered_df["Status"] == "❌ Unverified"]

            if search_filter:
                mask = (
                    filtered_df["Citation Key"].str.contains(search_filter, case=False, na=False) |
                    filtered_df["Title"].str.contains(search_filter, case=False, na=False) |
                    filtered_df["Authors"].str.contains(search_filter, case=False, na=False)
                )
                filtered_df = filtered_df[mask]

            st.dataframe(filtered_df, use_container_width=True, hide_index=True)

            # Connection-Citation mapping
            st.markdown("---")
            st.markdown("#### Connection-Citation Mapping")
            st.caption("View which connections are supported by which papers")

            connections = connection_cits_data.get("connections", [])
            conn_rows = []
            for conn in connections:
                status_emoji = "✅" if conn.get("status") == "verified" else "⚠️" if conn.get("status") == "unverified" else "❌"
                conn_rows.append({
                    "Status": status_emoji,
                    "From": conn.get("from_var", ""),
                    "To": conn.get("to_var", ""),
                    "Relationship": conn.get("relationship", ""),
                    "Citations": ", ".join(conn.get("verified_citations", [])) or "None",
                    "Theories": ", ".join(conn.get("theories", [])) or "None",
                    "In Loops": ", ".join(conn.get("in_loops", [])) or "None",
                })

            conn_df = pd.DataFrame(conn_rows)

            # Connection filters
            cf1, cf2, cf3 = st.columns(3)
            with cf1:
                conn_status_filter = st.selectbox(
                    "Filter by status",
                    ["All", "Verified", "Unverified", "Unsupported"],
                    key="conn_status_filter"
                )
            with cf2:
                conn_search = st.text_input("Search connections", key="conn_search")
            with cf3:
                loop_filter = st.text_input("Filter by loop ID", key="loop_filter")

            # Apply connection filters
            filtered_conn_df = conn_df.copy()
            if conn_status_filter != "All":
                status_map = {"Verified": "✅", "Unverified": "⚠️", "Unsupported": "❌"}
                filtered_conn_df = filtered_conn_df[filtered_conn_df["Status"] == status_map[conn_status_filter]]

            if conn_search:
                mask = (
                    filtered_conn_df["From"].str.contains(conn_search, case=False, na=False) |
                    filtered_conn_df["To"].str.contains(conn_search, case=False, na=False)
                )
                filtered_conn_df = filtered_conn_df[mask]

            if loop_filter:
                filtered_conn_df = filtered_conn_df[
                    filtered_conn_df["In Loops"].str.contains(loop_filter, case=False, na=False)
                ]

            st.dataframe(filtered_conn_df, use_container_width=True, hide_index=True)

    with discovery_tab:
        st.markdown("### 🔍 Paper Discovery")
        st.caption("Search Semantic Scholar for papers to support unsupported or weak connections")

        cfg = load_config()
        paths = for_project(cfg, project)

        connection_citations_path = paths.artifacts_dir / "connection_citations.json"
        gap_analysis_path = paths.artifacts_dir / "gap_analysis.json"

        # Check if citation verification has been run
        if not connection_citations_path.exists():
            st.warning("⚠️ Please run Citation Verification first before discovering papers.")
        else:
            # Run gap analysis if not already done
            if not gap_analysis_path.exists():
                with st.spinner("Analyzing gaps in citation coverage..."):
                    try:
                        gaps = identify_gaps(connection_citations_path, gap_analysis_path)
                        st.success("Gap analysis complete!")
                    except Exception as e:
                        st.error(f"Gap analysis failed: {str(e)}")
                        st.stop()

            # Load gap analysis
            gaps_data = json.loads(gap_analysis_path.read_text(encoding="utf-8"))

            # Display gap summary
            st.markdown("#### Gap Analysis Summary")
            summary = gaps_data.get("summary", {})
            g1, g2, g3, g4 = st.columns(4)
            with g1:
                st.metric("Unsupported", summary.get("unsupported_connections", 0), help="No citations at all")
            with g2:
                st.metric("Unverified", summary.get("unverified_connections", 0), help="Citations not found in S2")
            with g3:
                st.metric("Weak", summary.get("weak_connections", 0), help="< 2 verified citations")
            with g4:
                st.metric("Weak Loops", summary.get("weak_loops", 0), help="< 50% citation coverage")

            # Gap selection
            st.markdown("---")
            st.markdown("#### Search for Papers")

            unsupported = gaps_data.get("unsupported_connections", [])
            if not unsupported:
                st.info("🎉 No unsupported connections found! All connections have at least one citation.")
            else:
                # Connection selector
                gap_options = [
                    f"{conn['from_var']} → {conn['to_var']} ({conn['relationship']})"
                    for conn in unsupported[:50]  # Limit to first 50
                ]

                selected_gap_str = st.selectbox(
                    "Select unsupported connection to find papers for:",
                    gap_options,
                    key="gap_selector"
                )

                selected_idx = gap_options.index(selected_gap_str)
                selected_conn = unsupported[selected_idx]

                # Generate search queries
                st.markdown("##### Suggested Search Queries")
                if st.button("💡 Generate Search Queries (LLM)"):
                    with st.spinner("Generating search queries..."):
                        try:
                            client = LLMClient()
                            queries = suggest_search_queries_llm(selected_conn, client)
                            st.session_state[f"queries_{project}_{selected_idx}"] = queries
                        except Exception as e:
                            st.error(f"Query generation failed: {str(e)}")

                # Display queries
                queries_key = f"queries_{project}_{selected_idx}"
                if queries_key in st.session_state:
                    queries = st.session_state[queries_key]
                    for i, query in enumerate(queries):
                        st.code(query, language=None)

                # Search button
                st.markdown("---")
                if st.button("🔎 Search Semantic Scholar", type="primary"):
                    with st.spinner("Searching for relevant papers..."):
                        try:
                            s2_client = SemanticScholarClient()
                            client = LLMClient()

                            papers = search_papers_for_connection(
                                connection=selected_conn,
                                s2_client=s2_client,
                                llm_client=client,
                                limit=10
                            )

                            st.session_state[f"papers_{project}_{selected_idx}"] = papers
                            st.success(f"Found {len(papers)} relevant papers!")
                        except Exception as e:
                            st.error(f"Search failed: {str(e)}")

                # Display results
                papers_key = f"papers_{project}_{selected_idx}"
                if papers_key in st.session_state:
                    papers = st.session_state[papers_key]

                    st.markdown("---")
                    st.markdown("#### Search Results")

                    for i, paper in enumerate(papers):
                        with st.expander(f"📄 {paper.title} ({paper.year or 'N/A'})"):
                            st.markdown(f"**Authors:** {', '.join(paper.authors[:3])}{('...' if len(paper.authors) > 3 else '')}")
                            st.markdown(f"**Year:** {paper.year or 'N/A'}")
                            st.markdown(f"**Citations:** {paper.citation_count}")
                            st.markdown(f"**Relevance Score:** {paper.relevance_score:.2f}")

                            if paper.abstract:
                                st.markdown(f"**Abstract:** {paper.abstract[:300]}...")

                            if paper.url:
                                st.markdown(f"[View on Semantic Scholar]({paper.url})")

                            # Add to theory button (placeholder for now)
                            st.markdown("---")
                            st.caption("💡 Future: Add button to create new theory from this paper or add to existing theory")

    with stage3_tab:
        st.info("Placeholder for Step 3. We will flesh this out next.")


if __name__ == "__main__":
    main()
