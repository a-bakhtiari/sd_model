from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html

from .config import load_config
from .paths import first_mdl_file, for_project
from .llm.client import LLMClient
from .pipeline.llm_extraction import infer_variable_types, infer_connections
from .pipeline.loops import compute_loops
from .pipeline.theory_validation import validate_against_theories
from .pipeline.verify_citations import verify_citations


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


def _ensure_stage1(project: str) -> Dict[str, Path]:
    cfg = load_config()
    paths = for_project(cfg, project)
    paths.ensure()
    mdl = first_mdl_file(paths)
    if not mdl:
        raise FileNotFoundError(f"No .mdl file found in {paths.mdl_dir}")

    client = LLMClient()
    variables_data = infer_variable_types(mdl, client)
    connections_data = infer_connections(mdl, variables_data, client)

    variables_path = paths.artifacts_dir / "variables_llm.json"
    connections_llm_path = paths.artifacts_dir / "connections_llm.json"
    variables_path.write_text(json.dumps(variables_data, indent=2), encoding="utf-8")
    connections_llm_path.write_text(json.dumps(connections_data, indent=2), encoding="utf-8")

    id_to_name = {int(v["id"]): v["name"] for v in variables_data.get("variables", [])}

    parsed = {
        "variables": [v["name"] for v in variables_data.get("variables", [])],
        "equations": {},
    }
    paths.parsed_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")

    connections_named = []
    for edge in connections_data.get("connections", []):
        from_name = id_to_name.get(int(edge.get("from", -1)))
        to_name = id_to_name.get(int(edge.get("to", -1)))
        if not from_name or not to_name:
            continue
        polarity = str(edge.get("polarity", "UNDECLARED")).upper()
        if polarity == "POSITIVE":
            relationship = "positive"
        elif polarity == "NEGATIVE":
            relationship = "negative"
        else:
            relationship = "unknown"
        connections_named.append(
            {
                "from_var": from_name,
                "to_var": to_name,
                "relationship": relationship,
            }
        )

    paths.connections_path.write_text(json.dumps({"connections": connections_named}, indent=2), encoding="utf-8")

    compute_loops(parsed, paths.loops_path)
    validate_against_theories(
        connections_path=paths.connections_path,
        theories_dir=paths.theories_dir,
        bib_path=paths.references_bib_path,
        out_path=paths.theory_validation_path,
    )
    try:
        verify_citations(
            [paths.theory_validation_path, paths.model_improvements_path],
            bib_path=paths.references_bib_path,
        )
    except Exception:
        pass

    return {
        "parsed": paths.parsed_path,
        "connections": paths.connections_path,
        "theory_validation": paths.theory_validation_path,
        "artifacts_dir": paths.artifacts_dir,
        "db_path": paths.db_dir / "provenance.sqlite",
        "variables_llm": variables_path,
        "connections_llm": connections_llm_path,
    }


@st.cache_data(show_spinner=False)
def load_stage1(project: str) -> Dict:
    refs = _ensure_stage1(project)
    parsed = json.loads(refs["parsed"].read_text(encoding="utf-8"))
    cons = json.loads(refs["connections"].read_text(encoding="utf-8"))
    tv = json.loads(refs["theory_validation"].read_text(encoding="utf-8"))
    variables_llm = json.loads(refs["variables_llm"].read_text(encoding="utf-8"))
    connections_llm = json.loads(refs["connections_llm"].read_text(encoding="utf-8"))
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
def _cached_mermaid_diagram(selected: str, edges: Tuple[Tuple[str, str, str], ...], type_pairs: Tuple[Tuple[str, str], ...]) -> str:
    cons = {
        "connections": [
            {"from_var": e[0], "to_var": e[1], "relationship": e[2]}
            for e in edges
        ]
    }
    var_types = dict(type_pairs)
    return _mermaid_diagram(cons, selected, var_types)


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


def _node_markup(label: str, node_type: str) -> Tuple[str, str]:
    safe = _escape_label(label)
    node_type = (node_type or "aux").lower()
    if node_type == "stock":
        return f"[{safe}]", "stock"
    if node_type in {"aux", "auxiliary"}:
        return f"(({safe}))", "aux"
    if node_type == "parameter":
        return f"([{safe}])", "parameter"
    return "", "flow"


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

    def polarity(rel: str) -> str:
        rel = (rel or "").lower()
        if rel.startswith("pos") or rel.startswith("increase"):
            return "positive"
        if rel.startswith("neg") or rel.startswith("decrease"):
            return "negative"
        return "unknown"

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

    def arrow_segment(rel: str, label: str) -> str:
        pol = polarity(rel)
        label = _escape_label((label or "").strip())
        if pol == "positive":
            value = (label + " (+)").strip() or "(+)"
            return f' -- "{value}" --> '
        if pol == "negative":
            value = (label + " (-)").strip() or "(-)"
            return f' -- "{value}" --> '
        value = label or " "
        return f' -. "{value}" .-> '

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
                pol = polarity(rel)
                seg = arrow_segment(rel, source)
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
            seg = arrow_segment(rel, "")
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
                seg = arrow_segment(rel, target)
                lines.append(f"  {center_id}{seg}{cloud_id}")
                continue
            dst_id = ensure_node(target)
            if not dst_id:
                continue
            seg = arrow_segment(rel, "")
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
    dashboard_tab, stage2_tab, stage3_tab = st.tabs(["Dashboard", "Stage 2", "Stage 3"])

    with dashboard_tab:
        # Auto-sync Stage 1 artifacts on first load per project
        synced_key = f"stage1_synced::{project}"
        autorun = st.session_state.get(synced_key) is None
        if autorun:
            with st.spinner("Syncing Stage 1 artifacts..."):
                try:
                    st.session_state[synced_key] = True
                    st.cache_data.clear()
                    _ = load_stage1(project)
                except Exception as e:
                    st.session_state[synced_key] = False
                    st.error(f"Sync error: {e}")

        col_sync, _ = st.columns([1, 3])
        if col_sync.button("Sync Stage 1 Artifacts"):
            with st.spinner("Syncing..."):
                try:
                    st.cache_data.clear()
                    data = load_stage1(project)
                    st.success("Synced.")
                except Exception as e:
                    st.error(f"Sync error: {e}")

        # Load current data
        try:
            data = load_stage1(project)
        except Exception as e:
            st.error(str(e))
            return

        parsed = data["parsed"]
        cons = data["connections"]
        tv = data["theory_validation"]
        variables_llm = data.get("variables_llm", {"variables": []})
        connections_llm = data.get("connections_llm", {"connections": []})
        id_to_name = {int(v["id"]): v["name"] for v in variables_llm.get("variables", [])}
        name_to_type = {v["name"]: v.get("type", "Auxiliary") for v in variables_llm.get("variables", [])}
        _artifact_cards(parsed, cons, tv)

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

            diagram_col, selector_col = st.columns([3, 1])
            search_key = f"var_search::{project}"
            radio_key = f"var_radio::{project}"

            with selector_col:
                st.markdown(
                    """
                    <style>
                      .variable-panel .stRadio div[role='radiogroup'] {
                        max-height: 320px;
                        overflow-y: auto;
                        padding-right: 6px;
                      }
                      .variable-panel .stRadio label {
                        display: block;
                        border: 1px solid #e5e7eb;
                        border-radius: 6px;
                        padding: 6px 10px;
                        margin-bottom: 6px;
                        cursor: pointer;
                      }
                      .variable-panel .stRadio label:hover {
                        background: #f3f4f6;
                      }
                      .variable-panel .stRadio input[type="radio"] {
                        display: none;
                      }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown("<div class='variable-panel'>", unsafe_allow_html=True)
                search_value = st.text_input(
                    "Search variables",
                    value=st.session_state.get(search_key, ""),
                    key=search_key,
                )
                if search_value:
                    filtered = [
                        v for v in variables if search_value.lower() in v.lower()
                    ]
                else:
                    filtered = variables

                type_filter = st.selectbox(
                    "Filter by type",
                    ["All", "Stock", "Auxiliary", "Parameter"],
                    key=f"type_filter::{project}"
                )
                if type_filter != "All":
                    filtered = [
                        v for v in filtered
                        if var_types.get(v, "Auxiliary").lower() == type_filter.lower()
                    ]
                if not filtered:
                    st.warning("No variables match the search.")
                    filtered = variables

                current_sel = st.session_state[vkey]
                if current_sel not in filtered:
                    current_sel = filtered[0]

                default_selection = st.session_state.get(radio_key, current_sel)
                if default_selection not in filtered:
                    default_selection = current_sel

                sel_var = st.radio(
                    "Variables",
                    filtered,
                    index=filtered.index(default_selection),
                    key=radio_key,
                    label_visibility="collapsed",
                    format_func=lambda v: var_labels.get(v, v),
                )
                st.session_state[vkey] = sel_var

                sel_type = var_types.get(sel_var, "Auxiliary")
                st.markdown(f"**Type:** {sel_type}")
                st.markdown("</div>", unsafe_allow_html=True)

            with diagram_col:
                edges_tuple = tuple(
                    (
                        row.get("from_var", ""),
                        row.get("to_var", ""),
                        row.get("relationship", "unknown"),
                    )
                    for row in cons.get("connections", [])
                )
                type_pairs = tuple(sorted(var_types.items()))
                diagram_code = _cached_mermaid_diagram(sel_var, edges_tuple, type_pairs)
                container_id, _ = _sanitize_node(f"{project}_{sel_var}_diagram")
                diagram_html = f"""
                <style>
                  .mermaid-wrapper {{
                    background: #fdfaf3;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    padding: 1.2rem;
                  }}
                </style>
                <div id='{container_id}' class='mermaid-wrapper'>
                  <div class='mermaid'>
                  {diagram_code}
                  </div>
                </div>
                <script type=\"module\">
                  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
                  mermaid.initialize({{ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' }});
                  mermaid.run({{ nodes: document.querySelectorAll('#{container_id} .mermaid') }});
                </script>
                """
                html(diagram_html, height=520)

        st.subheader("Theories & Expected Links (for selected variable)")
        theory_count = tv.get("summary", {}).get("theory_count", 0)
        if theory_count == 0:
            st.info("No theories found. Add YAML files under knowledge/theories/ to enable coverage.")
        else:
            # Filter confirmed/missing by selected variable
            if variables:
                sel_var = st.session_state.get(f"selected_var::{project}", variables[0])
                conf = [r for r in tv.get("confirmed", []) if r.get("from_var") == sel_var or r.get("to_var") == sel_var]
                miss = [r for r in tv.get("missing", []) if r.get("from_var") == sel_var or r.get("to_var") == sel_var]
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Confirmed links", len(conf))
                with c2:
                    st.metric("Missing links", len(miss))
                if conf:
                    st.markdown("**Confirmed links**")
                    for r in conf:
                        st.markdown(f"- {r.get('theory')}: {r.get('from_var')} → {r.get('to_var')} ({r.get('relationship')})")
                else:
                    st.markdown("*No confirmed links for this variable.*")

                if miss:
                    st.markdown("**Missing links**")
                    for r in miss:
                        st.markdown(f"- {r.get('theory')}: {r.get('from_var')} → {r.get('to_var')} ({r.get('relationship')})")
                else:
                    st.markdown("*No missing links for this variable.*")

        st.subheader("Provenance – Last 5 Events")
        prov_df = _last_provenance_events(Path(data["db_path"]))
        st.dataframe(prov_df, use_container_width=True, hide_index=True)

    with stage2_tab:
        st.subheader("Feedback Loops")
        loops_path = Path(data["artifacts_dir"]) / "loops.json"
        loops_data = json.loads(loops_path.read_text(encoding="utf-8")) if loops_path.exists() else {}
        loop_rows = [
            {"Type": loop_type.title(), "Description": loop}
            for loop_type, values in loops_data.items()
            if loop_type in {"balancing", "reinforcing"} and isinstance(values, list)
            for loop in values
        ]
        loop_df = pd.DataFrame(loop_rows, columns=["Type", "Description"])
        loop_notes = loops_data.get("notes", [])

        lc1, lc2, lc3 = st.columns(3)
        with lc1:
            bal_count = int((loop_df["Type"] == "Balancing").sum()) if not loop_df.empty else 0
            st.metric("Balancing loops", bal_count)
        with lc2:
            rein_count = int((loop_df["Type"] == "Reinforcing").sum()) if not loop_df.empty else 0
            st.metric("Reinforcing loops", rein_count)
        with lc3:
            st.metric("Notes", len(loop_notes))

        if loop_df.empty:
            st.info("Loop detection is currently minimal. Extend `pipeline/loops.py` to populate balancing/reinforcing loops.")
        else:
            st.dataframe(loop_df, use_container_width=True, hide_index=True)

        if loop_notes:
            st.caption("Loop notes")
            for note in loop_notes:
                st.markdown(f"- {note}")

        st.subheader("Theory Alignment")
        tv_value = data.get("theory_validation")
        if isinstance(tv_value, dict):
            tv_data = tv_value
        else:
            tv_data = json.loads(Path(tv_value).read_text(encoding="utf-8"))
        summary = tv_data.get("summary", {})
        metrics = [
            ("Confirmed", summary.get("confirmed_count", 0)),
            ("Contradicted", summary.get("contradicted_count", 0)),
            ("Missing", summary.get("missing_count", 0)),
            ("Novel", summary.get("novel_count", 0)),
            ("Theories", summary.get("theory_count", 0)),
        ]
        metric_cols = st.columns(len(metrics))
        for col, (label, val) in zip(metric_cols, metrics):
            with col:
                st.metric(label, val)

        st.markdown("**Missing links**")
        missing_df = pd.DataFrame(tv_data.get("missing", []))
        if missing_df.empty:
            st.write("None.")
        else:
            fcol1, fcol2 = st.columns(2)
            with fcol1:
                var_filter = st.text_input("Filter by variable", key="missing_var")
            with fcol2:
                theory_filter = st.text_input("Filter by theory", key="missing_theory")
            filt = missing_df
            if var_filter:
                mask = filt["from_var"].str.contains(var_filter, case=False, na=False) | filt["to_var"].str.contains(var_filter, case=False, na=False)
                filt = filt[mask]
            if theory_filter:
                filt = filt[filt["theory"].str.contains(theory_filter, case=False, na=False)]
            st.dataframe(filt, use_container_width=True, hide_index=True)

        st.markdown("**Confirmed links**")
        confirmed_df = pd.DataFrame(tv_data.get("confirmed", []))
        if confirmed_df.empty:
            st.write("None.")
        else:
            st.dataframe(confirmed_df, use_container_width=True, hide_index=True)

    with stage3_tab:
        st.info("Placeholder for Step 3. We will flesh this out next.")


if __name__ == "__main__":
    main()
