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
        "variables_llm": paths.variables_llm_path,
        "connections_llm": paths.connections_llm_path,
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
        "flowchart LR",
        "  classDef muted fill:#f3f4f6,color:#6b7280,font-size:11px",
        "  classDef stock fill:#dbeafe,color:#1e3a8a,stroke:#3b82f6,stroke-width:2px,font-size:13px",
        "  classDef aux fill:#ffffff,color:#1f2937,stroke:#6b7280,stroke-width:2px,font-size:13px",
        "  classDef parameter fill:#fef9c3,color:#78350f,stroke:#f59e0b,stroke-width:2px,font-size:13px",
        "  classDef center stroke:#3b82f6,stroke-width:3px",
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
        width: 100%;
      }}
      .mermaid-wrapper svg {{
        max-width: 100%;
        height: auto;
      }}
    </style>
    <div id='{container_id}' class='mermaid-wrapper'>
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
    html(diagram_html, height=450)


def _mermaid_diagram(cons: Dict, selected: str, var_types: Dict[str, str]) -> str:
    df = _df_connections(cons)
    if df.empty or not selected:
        return "flowchart LR\\n  empty((No data)):::muted"

    lines = [
        "flowchart LR",
        "  classDef muted fill:#f3f4f6,color:#6b7280,font-size:11px",
        "  classDef stock fill:#dbeafe,color:#1e3a8a,stroke:#3b82f6,stroke-width:2px,font-size:13px",
        "  classDef aux fill:#ffffff,color:#1f2937,stroke:#6b7280,stroke-width:2px,font-size:13px",
        "  classDef parameter fill:#fef9c3,color:#78350f,stroke:#f59e0b,stroke-width:2px,font-size:13px",
        "  classDef center stroke:#3b82f6,stroke-width:3px",
        "  classDef cloud fill:#eff6ff,color:#3b82f6,stroke:#93c5fd,stroke-width:2px,font-size:11px,stroke-dasharray:4 4,padding:5px",
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


def _build_connections_dataframe(artifacts_dir: Path) -> pd.DataFrame:
    """Build comprehensive connections dataframe from artifacts.

    Combines connection data with descriptions, variable types, and verified citations.
    Returns one row per connection-citation pair (connections without citations get one row).
    """
    def load_json_safe(path: Path) -> dict:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    # Load all data sources
    connections_data = load_json_safe(artifacts_dir / "connections" / "connections.json")
    descriptions_data = load_json_safe(artifacts_dir / "connections" / "connection_descriptions.json")
    variables_data = load_json_safe(artifacts_dir / "parsing" / "variables_llm.json")
    citations_data = load_json_safe(artifacts_dir / "connections" / "connection_citations_verified.json")

    # Build lookup dictionaries
    descriptions = {d["id"]: d["description"] for d in descriptions_data.get("descriptions", [])}
    variables = {v["name"]: v["type"] for v in variables_data.get("variables", [])}
    citations = {c["connection_id"]: c for c in citations_data.get("citations", [])}

    rows = []

    for conn in connections_data.get("connections", []):
        conn_id = conn.get("id")
        from_var = conn.get("from_var", "")
        to_var = conn.get("to_var", "")
        relationship = conn.get("relationship", "")
        description = descriptions.get(conn_id, "")
        from_type = variables.get(from_var, "Unknown")
        to_type = variables.get(to_var, "Unknown")

        # Get citations for this connection
        citation_info = citations.get(conn_id)

        if citation_info and citation_info.get("papers"):
            # One row per citation
            for paper in citation_info.get("papers", []):
                s2_match = paper.get("semantic_scholar_match", {})
                rows.append({
                    "From": from_var,
                    "To": to_var,
                    "Relationship": relationship,
                    "From Type": from_type,
                    "To Type": to_type,
                    "Description": description,
                    "Citation": paper.get("title", ""),
                    "URL": s2_match.get("url", ""),
                })
        else:
            # No citations - single row
            rows.append({
                "From": from_var,
                "To": to_var,
                "Relationship": relationship,
                "From Type": from_type,
                "To Type": to_type,
                "Description": description,
                "Citation": "",
                "URL": "",
            })

    return pd.DataFrame(rows)


def _build_loops_dataframe(artifacts_dir: Path) -> pd.DataFrame:
    """Build comprehensive loops dataframe from artifacts.

    Combines loop data with descriptions and verified citations.
    Returns one row per loop-citation pair (loops without citations get one row).
    """
    def load_json_safe(path: Path) -> dict:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    # Load all data sources
    loops_data = load_json_safe(artifacts_dir / "loops" / "loops.json")
    descriptions_data = load_json_safe(artifacts_dir / "loops" / "loop_descriptions.json")
    citations_data = load_json_safe(artifacts_dir / "loops" / "loop_citations_verified.json")

    # Collect all loops
    all_loops = []
    for loop_type in ["reinforcing", "balancing", "undetermined"]:
        for loop in loops_data.get(loop_type, []):
            loop["loop_type"] = loop_type
            all_loops.append(loop)

    descriptions = {d["id"]: d["description"] for d in descriptions_data.get("descriptions", [])}
    citations = {c["loop_id"]: c for c in citations_data.get("citations", [])}

    rows = []

    for loop in all_loops:
        loop_id = loop.get("id")
        loop_type = loop.get("loop_type", "")

        # Format edges as a path string
        edges = loop.get("edges", [])
        loop_path = " → ".join([e.get("from_var", "") for e in edges] + [edges[0].get("from_var", "")] if edges else [])

        description = descriptions.get(loop_id, "")

        # Get citations for this loop
        citation_info = citations.get(loop_id)

        if citation_info and citation_info.get("papers"):
            # One row per citation
            for paper in citation_info.get("papers", []):
                s2_match = paper.get("semantic_scholar_match", {})
                rows.append({
                    "Type": loop_type.capitalize(),
                    "Path": loop_path,
                    "Description": description,
                    "Citation": paper.get("title", ""),
                    "URL": s2_match.get("url", ""),
                })
        else:
            # No citations - single row
            rows.append({
                "Type": loop_type.capitalize(),
                "Path": loop_path,
                "Description": description,
                "Citation": "",
                "URL": "",
            })

    return pd.DataFrame(rows)


def _build_chat_context(artifacts_dir: Path) -> str:
    """Build lightweight chat context with model structure.

    Returns system prompt text with variables and connections.
    """
    def load_json_safe(path: Path) -> dict:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    # Load minimal data
    variables_data = load_json_safe(artifacts_dir / "parsing" / "variables_llm.json")
    connections_data = load_json_safe(artifacts_dir / "connections" / "connections.json")
    descriptions_data = load_json_safe(artifacts_dir / "connections" / "connection_descriptions.json")

    # Build context
    variables = variables_data.get("variables", [])
    connections = connections_data.get("connections", [])
    descriptions = {d["id"]: d["description"] for d in descriptions_data.get("descriptions", [])}

    # Group variables by type
    stocks = [v["name"] for v in variables if v.get("type") == "Stock"]
    flows = [v["name"] for v in variables if v.get("type") == "Flow"]
    auxiliaries = [v["name"] for v in variables if v.get("type") == "Auxiliary"]

    # Build system prompt
    context = f"""You are an expert System Dynamics assistant helping a researcher understand and improve their SD model of open-source software communities.

MODEL OVERVIEW:
- Total Variables: {len(variables)}
- Connections: {len(connections)}
- Focus: OSS community dynamics, contributor development, knowledge management

VARIABLES:
Stocks ({len(stocks)}): {", ".join(stocks) if stocks else "None"}
Flows ({len(flows)}): {", ".join(flows) if flows else "None"}
Auxiliaries ({len(auxiliaries)}): {", ".join(auxiliaries) if auxiliaries else "None"}

CONNECTIONS:
"""

    # Add connections with descriptions
    for conn in connections[:50]:  # Limit to first 50
        conn_id = conn.get("id", "")
        from_var = conn.get("from_var", "")
        to_var = conn.get("to_var", "")
        rel = conn.get("relationship", "")
        desc = descriptions.get(conn_id, "")

        context += f"\n- {from_var} → {to_var} ({rel})"
        if desc:
            context += f"\n  {desc}"

    if len(connections) > 50:
        context += f"\n\n... and {len(connections) - 50} more connections"

    context += """

YOUR ROLE:
- Answer questions about the model structure and variables
- Suggest improvements or new connections
- Discuss System Dynamics concepts in the context of OSS communities
- Help the researcher understand their model better
- Be conversational, helpful, and concise

When suggesting new variables or connections, explain the SD rationale and how they fit the OSS community context."""

    return context


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
    dashboard_tab, stage2_tab, data_tables_tab, theory_tab, rq_tab, chat_tab = st.tabs([
        "Connection Explorer",
        "Loop Explorer",
        "Data Tables",
        "Theory Development",
        "Research Questions",
        "Chat"
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
                # Render diagram with Mermaid
                connections_list = cons.get("connections", [])
                edges = tuple((c["from_var"], c["to_var"], c["relationship"]) for c in connections_list)
                type_pairs = tuple(var_types.items())
                mermaid_code = _cached_mermaid_diagram(sel_var, edges, type_pairs)
                _render_mermaid(mermaid_code, f"connection_{sel_var}")

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
                    "loop": loop.get("loop", ""),  # Add the loop path
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
                # Show loop path - try to get from loop field or construct from variables
                loop_path = selected_loop.get("loop", "")
                if not loop_path:
                    # Fallback: construct from variables
                    variables = selected_loop.get("variables", [])
                    if variables:
                        loop_path = " → ".join(variables)

                if loop_path:
                    st.info(f"**Loop Path:**\n\n{loop_path}")

                # Show description above diagram
                loop_desc = loop_desc_map.get(selected_loop_id)
                if loop_desc:
                    st.write(loop_desc)

                # Render loop diagram with Mermaid
                theory_status = {
                    "theory_matched": selected_loop.get("theory_matched", []),
                    "novel": selected_loop.get("novel_edges", []),
                }
                mermaid_code = _loop_mermaid(selected_loop["edges"], name_to_type, theory_status)
                _render_mermaid(mermaid_code, f"loop_{selected_loop_id}")

    with data_tables_tab:
        st.markdown("### 📊 Data Tables")
        st.caption("Interactive tables with comprehensive connection and loop metadata")

        # Load existing artifacts
        try:
            artifacts_dir = Path(data["artifacts_dir"])
        except:
            st.error("Failed to load artifacts directory")
            st.info("💡 Make sure you've run the pipeline first to generate artifacts.")
            st.stop()

        # Connections Data Table
        st.markdown("#### 🔗 Connections Table")
        st.markdown("All connections with descriptions, variable types, and verified citations.")

        try:
            df_connections = _build_connections_dataframe(artifacts_dir)

            if df_connections.empty:
                st.info("No connections data available yet. Run the pipeline to generate data.")
            else:
                # Add filtering options
                filter_col1, filter_col2 = st.columns(2)
                with filter_col1:
                    relationship_filter = st.multiselect(
                        "Filter by Relationship",
                        options=sorted(df_connections["Relationship"].unique()),
                        default=sorted(df_connections["Relationship"].unique()),
                        key=f"conn_rel_filter::{project}"
                    )
                with filter_col2:
                    type_filter = st.multiselect(
                        "Filter by Variable Type",
                        options=sorted(set(df_connections["From Type"].unique()) | set(df_connections["To Type"].unique())),
                        default=sorted(set(df_connections["From Type"].unique()) | set(df_connections["To Type"].unique())),
                        key=f"conn_type_filter::{project}"
                    )

                # Apply filters
                filtered_df = df_connections[
                    (df_connections["Relationship"].isin(relationship_filter)) &
                    ((df_connections["From Type"].isin(type_filter)) | (df_connections["To Type"].isin(type_filter)))
                ]

                # Display metrics
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                with metric_col1:
                    # Count unique connections by From+To combination
                    unique_conns = filtered_df.groupby(['From', 'To']).ngroups
                    st.metric("Total Connections", unique_conns)
                with metric_col2:
                    # Count connections that have at least one citation
                    cited_conns = len(filtered_df[filtered_df["Citation"] != ""].groupby(['From', 'To']))
                    st.metric("Connections with Citations", cited_conns)
                with metric_col3:
                    st.metric("Total Citations", len(filtered_df[filtered_df["Citation"] != ""]))

                # Display dataframe with clickable URLs
                st.dataframe(
                    filtered_df,
                    column_config={
                        "URL": st.column_config.LinkColumn("Semantic Scholar URL"),
                    },
                    use_container_width=True,
                    height=400
                )

                # Export button
                csv_data = filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Filtered Data as CSV",
                    data=csv_data,
                    file_name=f"{project}_connections_filtered.csv",
                    mime="text/csv",
                    key=f"download_conn::{project}"
                )
        except Exception as e:
            st.error(f"Error loading connections data: {e}")
            st.info("Make sure the pipeline has completed successfully and all artifacts are generated.")

        # Loops Data Table
        st.markdown("---")
        st.markdown("#### 🔄 Loops Table")
        st.markdown("All feedback loops with descriptions and verified citations.")

        try:
            df_loops = _build_loops_dataframe(artifacts_dir)

            if df_loops.empty:
                st.info("No loops data available yet. Run the pipeline to generate data.")
            else:
                # Add filtering options
                type_filter = st.multiselect(
                    "Filter by Loop Type",
                    options=sorted(df_loops["Type"].unique()),
                    default=sorted(df_loops["Type"].unique()),
                    key=f"loop_type_filter::{project}"
                )

                # Apply filters
                filtered_df = df_loops[df_loops["Type"].isin(type_filter)]

                # Display metrics
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                with metric_col1:
                    # Count unique loops by Path
                    unique_loops = filtered_df.groupby('Path').ngroups
                    st.metric("Total Loops", unique_loops)
                with metric_col2:
                    # Count loops that have at least one citation
                    cited_loops = len(filtered_df[filtered_df["Citation"] != ""].groupby('Path'))
                    st.metric("Loops with Citations", cited_loops)
                with metric_col3:
                    st.metric("Total Citations", len(filtered_df[filtered_df["Citation"] != ""]))

                # Display dataframe with clickable URLs
                st.dataframe(
                    filtered_df,
                    column_config={
                        "URL": st.column_config.LinkColumn("Semantic Scholar URL"),
                    },
                    use_container_width=True,
                    height=400
                )

                # Export button
                csv_data = filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Filtered Data as CSV",
                    data=csv_data,
                    file_name=f"{project}_loops_filtered.csv",
                    mime="text/csv",
                    key=f"download_loop::{project}"
                )
        except Exception as e:
            st.error(f"Error loading loops data: {e}")
            st.info("Make sure the pipeline has completed successfully and all artifacts are generated.")

    with chat_tab:
        st.markdown("### 💬 Model Chat Assistant")
        st.caption("Ask questions about your SD model structure, variables, and connections")

        # Load artifacts
        try:
            artifacts_dir = Path(data["artifacts_dir"])
        except:
            st.error("Failed to load artifacts directory")
            st.info("💡 Make sure you've run the pipeline first to generate artifacts.")
            st.stop()

        # Build context (cached)
        context_key = f"chat_context::{project}"
        if context_key not in st.session_state:
            try:
                st.session_state[context_key] = _build_chat_context(artifacts_dir)
            except Exception as e:
                st.error(f"Failed to build chat context: {e}")
                st.stop()

        # Initialize chat history
        messages_key = f"chat_messages::{project}"
        if messages_key not in st.session_state:
            st.session_state[messages_key] = []

        # LLM provider selection
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            provider = st.selectbox(
                "LLM Provider",
                ["deepseek", "openai"],
                key=f"chat_provider::{project}",
                help="Select which LLM provider to use for the chat"
            )
        with col2:
            if provider == "deepseek":
                model = st.text_input("Model", value="deepseek-chat", key=f"chat_model::{project}")
            else:
                model = st.text_input("Model", value="gpt-4o", key=f"chat_model::{project}")
        with col3:
            if st.button("🗑️ Clear Chat", key=f"clear_chat::{project}"):
                st.session_state[messages_key] = []
                st.rerun()

        # Show what the assistant knows
        with st.expander("📋 Model Context (what the assistant knows)", expanded=False):
            st.markdown(st.session_state[context_key])

        # Display chat messages
        st.markdown("---")
        for msg in st.session_state[messages_key]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        if user_input := st.chat_input("Ask me anything about your SD model..."):
            # Add user message to history
            st.session_state[messages_key].append({"role": "user", "content": user_input})

            # Display user message
            with st.chat_message("user"):
                st.markdown(user_input)

            # Get assistant response with streaming
            with st.chat_message("assistant"):
                try:
                    # Initialize LLM client
                    llm_client = LLMClient(model=model, provider=provider)

                    # Build messages for API
                    api_messages = [{"role": "system", "content": st.session_state[context_key]}]
                    api_messages.extend(st.session_state[messages_key])

                    # Stream response
                    response = st.write_stream(llm_client.chat_stream(api_messages, temperature=0.7))

                    # Save response to history
                    st.session_state[messages_key].append({"role": "assistant", "content": response})

                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {str(e)}\n\nPlease check your API keys in the .env file."
                    st.error(error_msg)
                    st.session_state[messages_key].append({"role": "assistant", "content": error_msg})

    with theory_tab:
        st.markdown("### 🔬 Theory Development")
        st.caption("Enhance existing theories and discover new theoretical perspectives")

        cfg = load_config()
        paths = for_project(cfg, project)

        # Load theory enhancement results
        theory_enh_path = paths.theory_enhancement_path
        theory_disc_path = paths.theory_discovery_path

        if not theory_enh_path.exists() and not theory_disc_path.exists():
            st.warning("⚠️ No theory development results found. Run the pipeline with `--improve-model` flag.")
            st.code("python -m sd_model.cli run --project " + project + " --improve-model", language="bash")
        else:
            # Theory Enhancement Section
            if theory_enh_path.exists():
                theory_enh = json.loads(theory_enh_path.read_text(encoding="utf-8"))

                st.markdown("#### 📊 Theory Enhancement Suggestions")
                st.caption("Missing elements from your current theories and implementation suggestions")

                missing_elements = theory_enh.get("missing_from_theories", [])
                if missing_elements:
                    for i, element in enumerate(missing_elements):
                        with st.expander(f"🔸 {element.get('theory_name', 'Unknown')}: {element.get('missing_element', 'N/A')}", expanded=(i == 0)):
                            st.markdown(f"**Why Important:** {element.get('why_important', 'N/A')}")
                            st.markdown(f"**How to Add:** {element.get('how_to_add', 'N/A')}")

                            # SD Implementation details
                            sd_impl = element.get("sd_implementation", {})
                            new_vars = sd_impl.get("new_variables", [])
                            new_conns = sd_impl.get("new_connections", [])

                            if new_vars:
                                st.markdown("**New Variables:**")
                                for var in new_vars:
                                    st.markdown(f"- **{var.get('name')}** ({var.get('type')}): {var.get('description')}")

                            if new_conns:
                                st.markdown("**New Connections:**")
                                for conn in new_conns:
                                    st.markdown(f"- {conn.get('from')} → {conn.get('to')} ({conn.get('relationship')}): {conn.get('rationale')}")

                            st.info(f"💡 **Expected Impact:** {element.get('expected_impact', 'N/A')}")

                # General improvements
                improvements = theory_enh.get("general_improvements", [])
                if improvements:
                    st.markdown("#### 🔧 General Model Improvements")
                    for imp in improvements:
                        impact = imp.get("impact", "unknown")
                        emoji = "🔴" if impact == "high" else "🟡" if impact == "medium" else "🟢"
                        with st.expander(f"{emoji} {imp.get('description', 'N/A')}", expanded=False):
                            st.markdown(f"**Type:** {imp.get('improvement_type', 'N/A')}")
                            st.markdown(f"**Implementation:** {imp.get('implementation', 'N/A')}")
                            st.markdown(f"**Impact:** {impact.upper()}")

            st.markdown("---")

            # Theory Discovery Section
            if theory_disc_path.exists():
                theory_disc = json.loads(theory_disc_path.read_text(encoding="utf-8"))

                st.markdown("#### 🌟 New Theory Recommendations")
                st.caption("Theories to consider adding to your research framework")

                # High relevance theories
                high_rel = theory_disc.get("high_relevance", [])
                if high_rel:
                    st.markdown("**🎯 High Relevance (Direct)**")
                    for theory in high_rel:
                        risk = theory.get("risk", "unknown")
                        reward = theory.get("reward", "unknown")
                        risk_emoji = "🟢" if risk == "low" else "🟡" if risk == "medium" else "🔴"
                        reward_emoji = "🔴" if reward == "high" else "🟡" if reward == "medium" else "🟢"

                        with st.expander(f"{theory.get('theory_name', 'Unknown')} ({theory.get('key_citation', 'N/A')})"):
                            st.markdown(f"**Description:** {theory.get('description', 'N/A')}")
                            st.markdown(f"**Relevance to RQs:** {theory.get('relevance_to_rqs', 'N/A')}")
                            st.markdown(f"**Relevance to Model:** {theory.get('relevance_to_model', 'N/A')}")
                            st.markdown(f"**PhD Contribution:** {theory.get('phd_contribution', 'N/A')}")

                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Risk", risk.upper(), help=f"{risk_emoji} Assessment")
                            with col2:
                                st.metric("Reward", reward.upper(), help=f"{reward_emoji} Potential")

                # Adjacent opportunities
                adjacent = theory_disc.get("adjacent_opportunities", [])
                if adjacent:
                    st.markdown("**🔄 Adjacent Opportunities**")
                    for theory in adjacent:
                        with st.expander(f"{theory.get('theory_name', 'Unknown')}"):
                            st.markdown(f"**Why Adjacent:** {theory.get('why_adjacent', 'N/A')}")
                            st.markdown(f"**Novel Angle:** {theory.get('novel_angle', 'N/A')}")
                            st.markdown(f"**Contribution:** {theory.get('phd_contribution', 'N/A')}")

                # Cross-domain inspiration
                cross_domain = theory_disc.get("cross_domain_inspiration", [])
                if cross_domain:
                    st.markdown("**🌐 Cross-Domain Inspiration**")
                    st.caption("Provocative ideas from other fields - higher risk but potentially high impact")
                    for theory in cross_domain:
                        with st.expander(f"{theory.get('theory', 'Unknown')} (from {theory.get('source_domain', 'N/A')})"):
                            st.markdown(f"**Parallel:** {theory.get('parallel', 'N/A')}")
                            st.markdown(f"**Transfer Potential:** {theory.get('transfer_potential', 'N/A')}")
                            st.markdown(f"**Rationale:** {theory.get('rationale', 'N/A')}")

                # PhD Strategy
                strategy = theory_disc.get("phd_strategy", {})
                if strategy:
                    st.markdown("#### 🎓 PhD Strategy")
                    recommended = strategy.get("recommended_theories", [])
                    if recommended:
                        st.success(f"**Top Recommendations:** {', '.join(recommended)}")
                    st.info(f"**Rationale:** {strategy.get('rationale', 'N/A')}")
                    st.markdown(f"**Integration Strategy:** {strategy.get('integration_strategy', 'N/A')}")

    with rq_tab:
        st.markdown("### 📋 Research Questions Development")
        st.caption("Evaluate and refine your research questions")

        cfg = load_config()
        paths = for_project(cfg, project)

        # Load RQ results
        rq_align_path = paths.rq_alignment_path
        rq_refine_path = paths.rq_refinement_path

        if not rq_align_path.exists() and not rq_refine_path.exists():
            st.warning("⚠️ No RQ development results found. Run the pipeline with `--improve-model` flag.")
            st.code("python -m sd_model.cli run --project " + project + " --improve-model", language="bash")
        else:
            # RQ Alignment Section
            if rq_align_path.exists():
                rq_align = json.loads(rq_align_path.read_text(encoding="utf-8"))

                st.markdown("#### 📊 RQ-Theory-Model Alignment")
                st.caption("How well can your current theories and model answer your research questions?")

                # Overall assessment
                overall = rq_align.get("overall_assessment", {})
                if overall:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        fit = overall.get("model_rq_fit", "unknown")
                        color = "🟢" if fit in ["good", "excellent"] else "🟡" if fit == "moderate" else "🔴"
                        st.metric("Model-RQ Fit", fit.upper(), help=f"{color} Assessment")
                    with col2:
                        fit = overall.get("theory_rq_fit", "unknown")
                        color = "🟢" if fit in ["good", "excellent"] else "🟡" if fit == "moderate" else "🔴"
                        st.metric("Theory-RQ Fit", fit.upper(), help=f"{color} Assessment")
                    with col3:
                        fit = overall.get("coherence", "unknown")
                        color = "🟢" if fit in ["good", "excellent"] else "🟡" if fit == "moderate" else "🔴"
                        st.metric("Coherence", fit.upper(), help=f"{color} Assessment")
                    with col4:
                        fit = overall.get("phd_viability", "unknown")
                        color = "🟢" if fit in ["good", "excellent"] else "🟡" if fit == "moderate" else "🔴"
                        st.metric("PhD Viability", fit.upper(), help=f"{color} Assessment")

                    if overall.get("summary"):
                        st.info(f"**Summary:** {overall.get('summary')}")

                # Individual RQ assessments
                st.markdown("#### 🔍 Individual RQ Assessments")
                for i in range(1, 4):
                    rq_data = rq_align.get(f"rq_{i}", {})
                    if not rq_data:
                        continue

                    score = rq_data.get("alignment_score", 0)
                    theory_score = rq_data.get("theory_fit", {}).get("score", 0)
                    model_score = rq_data.get("model_fit", {}).get("score", 0)

                    score_emoji = "🔴" if score < 4 else "🟡" if score < 7 else "🟢"

                    with st.expander(f"{score_emoji} RQ{i}: Score {score}/10 (Theory: {theory_score}/10, Model: {model_score}/10)", expanded=(i == 1)):
                        # Theory fit
                        theory_fit = rq_data.get("theory_fit", {})
                        st.markdown(f"**Theory Assessment:** {theory_fit.get('assessment', 'N/A')}")
                        theory_gaps = theory_fit.get("gaps", [])
                        if theory_gaps:
                            st.markdown("**Theory Gaps:**")
                            for gap in theory_gaps:
                                st.markdown(f"- {gap}")

                        # Model fit
                        model_fit = rq_data.get("model_fit", {})
                        st.markdown(f"**Model Assessment:** {model_fit.get('assessment', 'N/A')}")
                        model_gaps = model_fit.get("gaps", [])
                        if model_gaps:
                            st.markdown("**Model Gaps:**")
                            for gap in model_gaps:
                                st.markdown(f"- {gap}")

                        # Critical issues
                        issues = rq_data.get("critical_issues", [])
                        if issues:
                            st.markdown("**Critical Issues:**")
                            for issue in issues:
                                severity = issue.get("severity", "unknown")
                                emoji = "🔴" if severity in ["critical", "high"] else "🟡" if severity == "medium" else "🟢"
                                st.warning(f"{emoji} {issue.get('issue', 'N/A')} (Severity: {severity})")

                        # Recommendations
                        recs = rq_data.get("recommendations", {})
                        theories_to_add = recs.get("theories_to_add", [])
                        if theories_to_add:
                            st.markdown("**Recommended Theories to Add:**")
                            for theory in theories_to_add:
                                st.markdown(f"- **{theory.get('theory', 'Unknown')}**: {theory.get('why', 'N/A')}")

                        model_additions = recs.get("model_additions", [])
                        if model_additions:
                            st.markdown("**Recommended Model Additions:**")
                            for addition in model_additions:
                                st.markdown(f"- {addition}")

                # Actionable steps
                steps = rq_align.get("actionable_steps", [])
                if steps:
                    st.markdown("#### ✅ Actionable Steps")
                    for step in steps:
                        impact = step.get("impact", "unknown")
                        effort = step.get("effort", "unknown")
                        emoji = "🔴" if impact == "high" else "🟡" if impact == "medium" else "🟢"
                        effort_emoji = "🟢" if effort == "low" else "🟡" if effort == "medium" else "🔴"

                        st.markdown(f"{emoji} **{step.get('step', 'N/A')}**")
                        st.caption(f"Impact: {impact.upper()} | Effort: {effort.upper()} {effort_emoji}")
                        st.caption(f"Rationale: {step.get('rationale', 'N/A')}")

            st.markdown("---")

            # RQ Refinement Section
            if rq_refine_path.exists():
                rq_refine = json.loads(rq_refine_path.read_text(encoding="utf-8"))

                st.markdown("#### ✨ RQ Refinement Suggestions")
                st.caption("Improved formulations of your research questions")

                # Overall strategy
                strategy = rq_refine.get("overall_strategy", {})
                if strategy:
                    approach = strategy.get("recommended_approach", "unknown")
                    st.success(f"**Recommended Strategy:** {approach.upper()}")
                    st.info(f"**Reasoning:** {strategy.get('reasoning', 'N/A')}")
                    st.caption(f"**Trade-offs:** {strategy.get('trade_offs', 'N/A')}")

                # Refinement suggestions per RQ
                refinements = rq_refine.get("refinement_suggestions", [])
                if refinements:
                    st.markdown("#### 🔄 Refined Versions")
                    for ref in refinements:
                        rq_num = ref.get("rq_number", 0)
                        original = ref.get("original", "N/A")

                        with st.expander(f"RQ{rq_num}: {original[:80]}...", expanded=(rq_num == 1)):
                            # Issues
                            issues = ref.get("issues", [])
                            if issues:
                                st.markdown("**Issues with Current Formulation:**")
                                for issue in issues:
                                    st.markdown(f"- {issue}")

                            # Refined versions
                            refined_versions = ref.get("refined_versions", [])
                            if refined_versions:
                                st.markdown("**Refined Versions:**")
                                for i, version in enumerate(refined_versions):
                                    phd_score = version.get("phd_worthiness", 0)
                                    score_emoji = "🔴" if phd_score < 4 else "🟡" if phd_score < 7 else "🟢"

                                    st.markdown(f"**Option {i+1}** {score_emoji} (PhD-worthiness: {phd_score}/10)")
                                    st.info(version.get("version", "N/A"))
                                    st.caption(f"**Rationale:** {version.get('rationale', 'N/A')}")
                                    st.caption(f"**SD Modelability:** {version.get('sd_modelability', 'N/A')} | **Theoretical Grounding:** {version.get('theoretical_grounding', 'N/A')}")
                                    st.caption(f"**Contribution:** {version.get('contribution', 'N/A')}")
                                    st.markdown("---")

                            # Recommendation
                            recommendation = ref.get("recommendation", "")
                            if recommendation:
                                st.success(f"**Recommendation:** {recommendation}")

                # New RQ suggestions
                new_rqs = rq_refine.get("new_rq_suggestions", [])
                if new_rqs:
                    st.markdown("#### 💡 New RQ Suggestions")
                    st.caption("Based on your model's capabilities and insights")
                    for rq in new_rqs:
                        phd_score = rq.get("phd_worthiness", 0)
                        score_emoji = "🔴" if phd_score < 4 else "🟡" if phd_score < 7 else "🟢"

                        with st.expander(f"{score_emoji} {rq.get('suggested_rq', 'N/A')[:80]}... (PhD-worthiness: {phd_score}/10)"):
                            st.info(rq.get("suggested_rq", "N/A"))
                            st.markdown(f"**Based on Model:** {rq.get('based_on_model', 'N/A')}")
                            st.markdown(f"**Theoretical Basis:** {rq.get('theoretical_basis', 'N/A')}")
                            st.markdown(f"**Originality:** {rq.get('originality', 'N/A')}")
                            st.markdown(f"**Rationale:** {rq.get('rationale', 'N/A')}")



if __name__ == "__main__":
    main()
