from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict

from .config import load_config
from .paths import first_mdl_file, for_project
from .pipeline.loops import compute_loops
from .pipeline.connection_descriptions import generate_connection_descriptions
from .pipeline.connection_citations import find_connection_citations
from .pipeline.loop_descriptions import generate_loop_descriptions
from .pipeline.loop_citations import find_loop_citations
from .pipeline.apply_patch import apply_model_patch
from .pipeline.citation_verification import verify_all_citations, generate_connection_citation_table, verify_llm_generated_citations
from .pipeline.gap_analysis import identify_gaps
from .pipeline.paper_discovery import suggest_papers_for_gaps
from .pipeline.csv_export import generate_connections_csv, generate_loops_csv
from .pipeline.theory_enhancement import run_theory_enhancement as execute_theory_enhancement
from .pipeline.rq_alignment import run_rq_alignment
from .pipeline.rq_refinement import run_rq_refinement
from .pipeline.theory_discovery import run_theory_discovery as execute_theory_discovery
from .pipeline.archetype_detection import detect_archetypes
from .llm.client import LLMClient
from .parsers import extract_variables, extract_connections
from .pipeline.llm_extraction import extract_diagram_style
from .provenance.store import log_event
from .validation.schema import validate_json_schema
from .external.semantic_scholar import SemanticScholarClient
from .knowledge.loader import load_research_questions, load_theories

logger = logging.getLogger(__name__)


def run_pipeline(
    project: str,
    # Core optional features
    run_loops: bool = False,
    run_citations: bool = False,
    # Model improvement features
    run_theory_enhancement: bool = False,
    run_archetype_detection: bool = False,
    run_rq_analysis: bool = False,
    run_theory_discovery: bool = False,
    run_gap_analysis: bool = False,
    discover_papers: bool = False,
    # Other options
    apply_patch: bool = False,
    save_run: Optional[str] = None
) -> Dict:
    """Run the analysis pipeline for a project with granular feature control.

    Foundation (always runs):
        - Parse MDL → extract variables & connections
        - Generate connection descriptions

    Args:
        project: Project name

        # Core optional features
        run_loops: Find feedback loops and generate loop descriptions
        run_citations: Generate and verify citations for connections/loops via Semantic Scholar

        # Model improvement features
        run_theory_enhancement: Suggest theory-based enhancements and generate enhanced MDL
        run_rq_analysis: Run research question alignment and refinement
        run_theory_discovery: Discover relevant theories for the model
        run_gap_analysis: Identify unsupported connections (requires run_citations)
        discover_papers: Find papers for unsupported connections (requires run_gap_analysis)

        # Other options
        apply_patch: Whether to apply model patches
        save_run: Optional run name to save artifacts in timestamped folder
    """
    logger.info(f"Starting pipeline for project: {project}")
    cfg = load_config()

    # Generate run ID if save_run is enabled
    run_id = None
    if save_run is not None:
        from .run_metadata import generate_run_id
        run_id = generate_run_id(save_run if save_run else None)
        logger.info(f"Versioned run mode enabled: {run_id}")

    paths = for_project(cfg, project, run_id=run_id)
    paths.ensure()

    logger.info(f"Looking for .mdl file in {paths.mdl_dir}")
    mdl_path = first_mdl_file(paths)
    if mdl_path is None:
        raise FileNotFoundError(f"No .mdl file found in {paths.mdl_dir}")
    logger.info(f"Found MDL file: {mdl_path.name}")

    logger.info("Extracting variables from MDL file (Python parser)...")
    variables_data = extract_variables(mdl_path)
    logger.info(f"✓ Found {len(variables_data.get('variables', []))} variables")

    logger.info("Extracting connections from MDL file (Python parser)...")
    connections_data = extract_connections(mdl_path, variables_data)
    logger.info(f"✓ Found {len(connections_data.get('connections', []))} connections")

    logger.info("Initializing LLM client for downstream tasks...")
    client = LLMClient()

    paths.parsed_variables_path.write_text(json.dumps(variables_data, indent=2), encoding="utf-8")
    paths.parsed_connections_path.write_text(json.dumps(connections_data, indent=2), encoding="utf-8")

    # Extract and save diagram style configuration
    style_data = extract_diagram_style(mdl_path)
    paths.diagram_style_path.write_text(json.dumps(style_data, indent=2), encoding="utf-8")

    # Build compatibility artifacts
    id_to_name = {int(v["id"]): v["name"] for v in variables_data.get("variables", [])}
    parsed = {
        "variables": [v["name"] for v in variables_data.get("variables", [])],
        "equations": {},
    }
    paths.parsed_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")

    connections_named = []
    for idx, edge in enumerate(connections_data.get("connections", [])):
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
            relationship = "undeclared"
        connections_named.append(
            {
                "id": f"C{idx+1:02d}",  # Python generates sequential ID
                "from_var": from_name,
                "to_var": to_name,
                "relationship": relationship,
            }
        )

    paths.connections_path.write_text(json.dumps({"connections": connections_named}, indent=2), encoding="utf-8")

    log_event(paths.db_dir / "provenance.sqlite", "parsed", {"variables": len(parsed["variables"])})

    # Optional: Feedback loops
    loops = None
    loop_descriptions = None
    if run_loops:
        logger.info("Computing feedback loops...")
        loops = compute_loops(
            parsed,
            paths.loops_path,
            connections=connections_data,
            variables_data=variables_data,
            llm_client=client
        )
        logger.info(f"✓ Found {len(loops.get('loops', []))} feedback loops")
        log_event(paths.db_dir / "provenance.sqlite", "loops", {})

        # Generate loop descriptions
        logger.info("Generating loop descriptions...")
        loop_descriptions = generate_loop_descriptions(
            loops_data=loops,
            llm_client=client,
            out_path=paths.loop_descriptions_path,
            domain_context="open source software development"
        )
        logger.info(f"✓ Generated {len(loop_descriptions.get('descriptions', []))} loop descriptions")
        log_event(paths.db_dir / "provenance.sqlite", "loop_descriptions", {"count": len(loop_descriptions.get("descriptions", []))})

    # Generate connection descriptions
    logger.info("Generating connection descriptions...")
    descriptions = generate_connection_descriptions(
        connections_data={"connections": connections_named},
        variables_data=variables_data,
        llm_client=client,
        out_path=paths.connection_descriptions_path
    )
    logger.info(f"✓ Generated {len(descriptions.get('descriptions', []))} connection descriptions")
    log_event(paths.db_dir / "provenance.sqlite", "connection_descriptions", {"count": len(descriptions.get("descriptions", []))})

    # Optional: Find citations for connections
    conn_citations = None
    if run_citations:
        logger.info("Finding citations for connections...")
        conn_citations = find_connection_citations(
            connections_data={"connections": connections_named},
            descriptions_data=descriptions,
            llm_client=client,
            out_path=paths.connection_citations_path
        )
        logger.info(f"✓ Found {len(conn_citations.get('citations', []))} connection citations")
        log_event(paths.db_dir / "provenance.sqlite", "connection_citations", {"count": len(conn_citations.get("citations", []))})

    # Optional: Find citations for loops (requires both run_citations and run_loops)
    loop_cites = None
    if run_citations and run_loops:
        logger.info("Finding citations for loops...")
        loop_cites = find_loop_citations(
            loops_data=loops,
            descriptions_data=loop_descriptions,
            llm_client=client,
            out_path=paths.loop_citations_path
        )
        logger.info(f"✓ Found {len(loop_cites.get('citations', []))} loop citations")
        log_event(paths.db_dir / "provenance.sqlite", "loop_citations", {"count": len(loop_cites.get("citations", []))})

    # Optional: Verify LLM-generated citations via Semantic Scholar
    verified_conn_citations = None
    verified_loop_citations = None
    if run_citations:
        from .external.semantic_scholar import SemanticScholarClient
        s2_client = SemanticScholarClient()

        logger.info("Verifying connection citations via Semantic Scholar...")
        verified_conn_citations = verify_llm_generated_citations(
            citations_path=paths.connection_citations_path,
            output_path=paths.connection_citations_verified_path,
            s2_client=s2_client,
            llm_client=client,
            debug_path=paths.connection_citations_verification_debug_path,
            verbose=False  # Don't print to console during pipeline run
        )
        summary = verified_conn_citations.get("summary", {})
        logger.info(f"✓ Verified {summary.get('verified', 0)}/{summary.get('total', 0)} connection citations")
        log_event(
            paths.db_dir / "provenance.sqlite",
            "connection_citations_verified",
            verified_conn_citations.get("summary", {})
        )

        # Verify loop citations (if they exist)
        if run_loops:
            logger.info("Verifying loop citations via Semantic Scholar...")
            verified_loop_citations = verify_llm_generated_citations(
                citations_path=paths.loop_citations_path,
                output_path=paths.loop_citations_verified_path,
                s2_client=s2_client,
                llm_client=client,
                debug_path=paths.loop_citations_verification_debug_path,
                verbose=False  # Don't print to console during pipeline run
            )
            loop_summary = verified_loop_citations.get("summary", {})
            logger.info(f"✓ Verified {loop_summary.get('verified', 0)}/{loop_summary.get('total', 0)} loop citations")
            log_event(
                paths.db_dir / "provenance.sqlite",
                "loop_citations_verified",
                verified_loop_citations.get("summary", {})
            )

    # Citation verification (on-demand) - OLD SYSTEM, kept for compatibility
    citations_verified_path = paths.improvements_dir / "citations_verified.json"
    paper_suggestions_path = paths.improvements_dir / "paper_suggestions.json"

    # Optional: Gap analysis (identify unsupported connections)
    gaps = None
    if run_gap_analysis:
        # Gap analysis requires citations to be generated first
        if not run_citations:
            logger.warning("Gap analysis requires --citations flag, skipping...")
        else:
            # Legacy citation verification system (kept for compatibility)
            from .external.semantic_scholar import SemanticScholarClient
            s2_client = SemanticScholarClient()

            verified_cits = verify_all_citations(
                theories_dir=paths.theories_dir,
                bib_path=paths.references_bib_path,
                s2_client=s2_client,
                out_path=citations_verified_path,
            )
            # Note: connection_citations_path now generated by LLM-based citation finder above
            connection_cits_legacy = generate_connection_citation_table(
                connections_path=paths.connections_path,
                theories_dir=paths.theories_dir,
                verified_citations_path=citations_verified_path,
                loops_path=paths.loops_path,
                out_path=paths.connections_dir / "connection_citations_legacy.json",
            )
            log_event(
                paths.db_dir / "provenance.sqlite",
                "verify_citations",
                {
                    "total": len(verified_cits),
                    "verified": sum(1 for v in verified_cits.values() if v.verified),
                },
            )

            # Perform gap analysis
            logger.info("Identifying unsupported connections...")
            gaps = identify_gaps(paths.connection_citations_path, paths.gap_analysis_path)
            logger.info(f"✓ Found {len(gaps.get('unsupported_connections', []))} unsupported connections")
            log_event(
                paths.db_dir / "provenance.sqlite",
                "gap_analysis",
                {"unsupported": len(gaps.get("unsupported_connections", []))},
            )

    # Optional: Paper discovery for unsupported connections
    suggestions = None
    if discover_papers:
        if not run_gap_analysis:
            logger.warning("Paper discovery requires --gap-analysis flag, skipping...")
        elif gaps is None:
            logger.warning("No gap analysis results available, skipping paper discovery...")
        else:
            from .external.semantic_scholar import SemanticScholarClient
            s2_client = SemanticScholarClient()

            logger.info("Discovering papers for unsupported connections...")
            suggestions = suggest_papers_for_gaps(
                gaps_path=paths.gap_analysis_path,
                s2_client=s2_client,
                llm_client=client,
                out_path=paper_suggestions_path,
                limit_per_gap=5,
            )
            logger.info(f"✓ Found {len(suggestions.get('suggestions', []))} paper suggestions")
            log_event(
                paths.db_dir / "provenance.sqlite",
                "paper_discovery",
                {"suggestions": len(suggestions.get("suggestions", []))},
            )

    patched_file = None
    if apply_patch:
        out_copy_path = paths.artifacts_dir / f"{mdl_path.stem}_patched.mdl"
        patched_file = apply_model_patch(mdl_path, paths.model_improvements_path, out_copy_path)
        log_event(paths.db_dir / "provenance.sqlite", "apply_patch", {"output": str(patched_file)})

    # Generate CSV exports (only if citations are generated and verified)
    conn_csv_rows = None
    if run_citations:
        conn_csv_rows = generate_connections_csv(
            connections_path=paths.connections_path,
            descriptions_path=paths.connection_descriptions_path,
            variables_path=paths.parsed_variables_path,
            citations_path=paths.connection_citations_verified_path,
            output_path=paths.connections_export_path,
        )
        log_event(paths.db_dir / "provenance.sqlite", "csv_export_connections", {"rows": conn_csv_rows})

    loop_csv_rows = None
    if run_citations and run_loops:
        loop_csv_rows = generate_loops_csv(
            loops_path=paths.loops_path,
            descriptions_path=paths.loop_descriptions_path,
            citations_path=paths.loop_citations_verified_path,
            output_path=paths.loops_export_path,
        )
        log_event(paths.db_dir / "provenance.sqlite", "csv_export_loops", {"rows": loop_csv_rows})

    # Step 8: Model Improvement & Development (optional)
    # Initialize result variables
    theory_enh = None
    enhanced_mdl_path = None
    archetype_enh = None
    archetype_mdl_path = None
    rq_align = None
    rq_refine = None
    theory_disc = None

    # Run model improvement modules if any are requested
    if run_theory_enhancement or run_archetype_detection or run_rq_analysis or run_theory_discovery:
        logger.info("=" * 60)
        logger.info("Starting Model Improvement & Development modules...")
        logger.info("=" * 60)

        # Load research questions if needed
        rqs = None
        if run_rq_analysis or run_theory_discovery:
            logger.info("Loading research questions...")
            rqs = load_research_questions(paths.rq_txt_path)
            logger.info(f"✓ Loaded {len(rqs)} research questions")

        # Load theories if needed
        theories = None
        if run_theory_enhancement or run_rq_analysis or run_theory_discovery:
            logger.info("Loading theories...")
            theories_objs = load_theories(paths.theories_dir)
            theories = [{"name": t.theory_name, "description": t.description, "focus_area": t.focus_area} for t in theories_objs]
            logger.info(f"✓ Loaded {len(theories)} theories")

        # Module 2: Theory Enhancement (optional)
        if run_theory_enhancement:
            logger.info("Running Theory Enhancement module...")
            try:
                theory_enh = execute_theory_enhancement(
                    theories=theories,
                    variables=variables_data,
                    connections={"connections": connections_named},
                    loops=loops
                )
                if "error" in theory_enh:
                    logger.warning(f"Theory Enhancement returned error: {theory_enh.get('error')}")
                paths.theory_enhancement_path.write_text(
                    json.dumps(theory_enh, indent=2), encoding="utf-8"
                )
                # Count from new format
                theory_count = len(theory_enh.get('theories', []))
                total_vars = sum(len(t.get('additions', {}).get('variables', [])) for t in theory_enh.get('theories', []))
                total_conns = sum(len(t.get('additions', {}).get('connections', [])) for t in theory_enh.get('theories', []))
                logger.info(f"✓ Theory Enhancement complete: {theory_count} theories, {total_vars} variables, {total_conns} connections")
                log_event(paths.db_dir / "provenance.sqlite", "theory_enhancement", {})

                # Always generate enhanced MDL file when theory enhancement runs
                # Check if any theories have additions, modifications, or removals
                has_changes = any(
                    len(t.get('additions', {}).get('variables', [])) > 0 or
                    len(t.get('additions', {}).get('connections', [])) > 0 or
                    len(t.get('modifications', {}).get('variables', [])) > 0 or
                    len(t.get('modifications', {}).get('connections', [])) > 0 or
                    len(t.get('removals', {}).get('variables', [])) > 0 or
                    len(t.get('removals', {}).get('connections', [])) > 0
                    for t in theory_enh.get('theories', [])
                )
                if "error" not in theory_enh and has_changes:
                    logger.info("Applying theory enhancements to MDL...")
                    try:
                        from .mdl_text_patcher import apply_theory_enhancements
                        from .mdl_enhancement_utils import save_enhancement

                        # Generate enhanced MDL in memory first
                        temp_mdl_path = paths.artifacts_dir / f"{mdl_path.stem}_temp.mdl"

                        mdl_summary = apply_theory_enhancements(
                            mdl_path,
                            theory_enh,
                            temp_mdl_path,
                            add_colors=True,
                            use_llm_layout=True,
                            llm_client=client
                        )

                        # Read the generated MDL content
                        enhanced_mdl_content = temp_mdl_path.read_text(encoding="utf-8")

                        # Save with versioning and metadata
                        enhanced_mdl_path = save_enhancement(
                            mdl_dir=paths.mdl_dir,
                            artifacts_dir=paths.artifacts_dir,
                            theory_enh_data=theory_enh,
                            mdl_summary=mdl_summary,
                            enhanced_mdl_content=enhanced_mdl_content,
                            original_mdl_name=mdl_path.name
                        )

                        # Clean up temp file
                        temp_mdl_path.unlink()

                        logger.info(f"✓ MDL Enhancement complete: {mdl_summary['variables_added']} vars, {mdl_summary['connections_added']} conns")
                        logger.info(f"✓ Enhanced MDL saved to: {enhanced_mdl_path}")
                        log_event(paths.db_dir / "provenance.sqlite", "mdl_enhancement", mdl_summary)
                    except Exception as e:
                        logger.error(f"✗ MDL Enhancement failed: {e}")
                        logger.exception("Full traceback:")
                        enhanced_mdl_path = None

            except Exception as e:
                logger.error(f"✗ Theory Enhancement failed: {e}")
                logger.exception("Full traceback:")
                # Write empty result so file exists
                paths.theory_enhancement_path.write_text(
                    json.dumps({"error": str(e), "theories": []}, indent=2), encoding="utf-8"
                )

        # Module 2.5: Archetype Detection (optional)
        if run_archetype_detection:
            logger.info("Running Archetype Detection module...")
            try:
                # Determine which MDL to analyze (theory-enhanced if available, otherwise original)
                current_mdl_path = enhanced_mdl_path if enhanced_mdl_path else mdl_path

                # Re-extract variables and connections from the current MDL
                # (This ensures we analyze theory enhancements if they were applied)
                logger.info(f"Extracting structure from: {current_mdl_path.name}")
                current_vars = extract_variables(current_mdl_path)
                current_conns = extract_connections(current_mdl_path, current_vars)

                # Detect archetypes
                archetype_enh = detect_archetypes(current_vars, current_conns, client)

                if "error" in archetype_enh:
                    logger.warning(f"Archetype Detection returned error: {archetype_enh.get('error')}")

                # Save archetype enhancement JSON
                paths.archetype_enhancement_path.write_text(
                    json.dumps(archetype_enh, indent=2), encoding="utf-8"
                )

                # Log summary
                archetype_count = len(archetype_enh.get('archetypes', []))
                total_vars = sum(len(a.get('additions', {}).get('variables', [])) for a in archetype_enh.get('archetypes', []))
                total_conns = sum(len(a.get('additions', {}).get('connections', [])) for a in archetype_enh.get('archetypes', []))
                logger.info(f"✓ Archetype Detection complete: {archetype_count} archetypes, {total_vars} variables, {total_conns} connections")
                log_event(paths.db_dir / "provenance.sqlite", "archetype_detection", {})

                # Apply archetype enhancements to MDL if any archetypes found
                has_changes = any(
                    len(a.get('additions', {}).get('variables', [])) > 0 or
                    len(a.get('additions', {}).get('connections', [])) > 0
                    for a in archetype_enh.get('archetypes', [])
                )

                if "error" not in archetype_enh and has_changes:
                    logger.info("Applying archetype enhancements to MDL...")
                    try:
                        from .mdl_text_patcher import apply_theory_enhancements
                        from .mdl_enhancement_utils import save_enhancement

                        # Prepare archetype data in theory enhancement format
                        archetype_for_patcher = {"theories": archetype_enh['archetypes']}

                        # Generate enhanced MDL in memory first
                        temp_archetype_path = paths.artifacts_dir / f"{current_mdl_path.stem}_archetype_temp.mdl"

                        mdl_summary = apply_theory_enhancements(
                            current_mdl_path,
                            archetype_for_patcher,
                            temp_archetype_path,
                            add_colors=True,
                            use_llm_layout=True,
                            llm_client=client
                        )

                        # Read the generated MDL content
                        archetype_mdl_content = temp_archetype_path.read_text(encoding="utf-8")

                        # Save with versioning and metadata
                        # Determine base name for archetype-enhanced file
                        if enhanced_mdl_path:
                            # If theory enhancement ran, this is the final combined enhancement
                            base_name = f"{mdl_path.stem}_theory_archetype_enhanced"
                        else:
                            # Only archetype enhancement
                            base_name = f"{mdl_path.stem}_archetype_enhanced"

                        archetype_mdl_path = save_enhancement(
                            mdl_dir=paths.mdl_dir,
                            artifacts_dir=paths.artifacts_dir,
                            theory_enh_data=archetype_enh,
                            mdl_summary=mdl_summary,
                            enhanced_mdl_content=archetype_mdl_content,
                            original_mdl_name=base_name + ".mdl"
                        )

                        # Clean up temp file
                        temp_archetype_path.unlink()

                        logger.info(f"✓ Archetype MDL Enhancement complete: {mdl_summary['variables_added']} vars, {mdl_summary['connections_added']} conns")
                        logger.info(f"✓ Archetype-enhanced MDL saved to: {archetype_mdl_path}")
                        log_event(paths.db_dir / "provenance.sqlite", "archetype_mdl_enhancement", mdl_summary)
                    except Exception as e:
                        logger.error(f"✗ Archetype MDL Enhancement failed: {e}")
                        logger.exception("Full traceback:")
                        archetype_mdl_path = None

            except Exception as e:
                logger.error(f"✗ Archetype Detection failed: {e}")
                logger.exception("Full traceback:")
                # Write empty result so file exists
                paths.archetype_enhancement_path.write_text(
                    json.dumps({"error": str(e), "archetypes": []}, indent=2), encoding="utf-8"
                )

        # Module 3 & 4: RQ Alignment and Refinement (optional)
        if run_rq_analysis:
            # Module 3: RQ Alignment
            logger.info("Running RQ Alignment module...")
            try:
                rq_align = run_rq_alignment(
                    rqs=rqs,
                    theories=theories,
                    variables=variables_data,
                    connections={"connections": connections_named},
                    loops=loops
                )
                if "error" in rq_align:
                    logger.warning(f"RQ Alignment returned error: {rq_align.get('error')}")
                paths.rq_alignment_path.write_text(
                    json.dumps(rq_align, indent=2), encoding="utf-8"
                )
                # Count RQ keys (rq_1, rq_2, etc.)
                rq_count = sum(1 for k in rq_align.keys() if k.startswith('rq_'))
                logger.info(f"✓ RQ Alignment complete: analyzed {rq_count} research questions")
                log_event(paths.db_dir / "provenance.sqlite", "rq_alignment", {})
            except Exception as e:
                logger.error(f"✗ RQ Alignment failed: {e}")
                logger.exception("Full traceback:")
                rq_align = {"error": str(e), "overall_assessment": {}, "actionable_steps": []}
                paths.rq_alignment_path.write_text(
                    json.dumps(rq_align, indent=2), encoding="utf-8"
                )

            # Module 4: RQ Refinement
            logger.info("Running RQ Refinement module...")
            try:
                rq_refine = run_rq_refinement(
                    rqs=rqs,
                    rq_alignment=rq_align,
                    variables=variables_data,
                    connections={"connections": connections_named},
                    loops=loops
                )
                if "error" in rq_refine:
                    logger.warning(f"RQ Refinement returned error: {rq_refine.get('error')}")
                paths.rq_refinement_path.write_text(
                    json.dumps(rq_refine, indent=2), encoding="utf-8"
                )
                refinement_count = len(rq_refine.get('refinement_suggestions', []))
                new_rq_count = len(rq_refine.get('new_rq_suggestions', []))
                logger.info(f"✓ RQ Refinement complete: {refinement_count} refinements, {new_rq_count} new RQ suggestions")
                log_event(paths.db_dir / "provenance.sqlite", "rq_refinement", {})
            except Exception as e:
                logger.error(f"✗ RQ Refinement failed: {e}")
                logger.exception("Full traceback:")
                paths.rq_refinement_path.write_text(
                    json.dumps({"error": str(e), "refinement_suggestions": [], "new_rq_suggestions": []}, indent=2), encoding="utf-8"
                )

        # Module 5: Theory Discovery (optional)
        if run_theory_discovery:
            logger.info("Running Theory Discovery module...")
            try:
                theory_disc = execute_theory_discovery(
                    rqs=rqs,
                    current_theories=theories,
                    variables=variables_data,
                    connections={"connections": connections_named}
                )
                if "error" in theory_disc:
                    logger.warning(f"Theory Discovery returned error: {theory_disc.get('error')}")
                paths.theory_discovery_path.write_text(
                    json.dumps(theory_disc, indent=2), encoding="utf-8"
                )
                high_rel_count = len(theory_disc.get('high_relevance', []))
                adjacent_count = len(theory_disc.get('adjacent_opportunities', []))
                cross_domain_count = len(theory_disc.get('cross_domain_inspiration', []))
                total_theories = high_rel_count + adjacent_count + cross_domain_count
                logger.info(f"✓ Theory Discovery complete: {total_theories} theories ({high_rel_count} high-relevance, {adjacent_count} adjacent, {cross_domain_count} cross-domain)")
                log_event(paths.db_dir / "provenance.sqlite", "theory_discovery", {})
            except Exception as e:
                logger.error(f"✗ Theory Discovery failed: {e}")
                logger.exception("Full traceback:")
                paths.theory_discovery_path.write_text(
                    json.dumps({"error": str(e), "high_relevance": [], "adjacent_opportunities": [], "cross_domain_inspiration": []}, indent=2), encoding="utf-8"
                )

        logger.info("=" * 60)
        logger.info("Model Improvement & Development modules completed!")
        logger.info("=" * 60)

    logger.info("")
    logger.info("🎉 Pipeline completed successfully!")
    logger.info(f"Artifacts saved to: {paths.artifacts_dir}")

    result = {
        "parsed": str(paths.parsed_path),
        "loops": str(paths.loops_path),
        "connections": str(paths.connections_path),
        "variables": str(paths.parsed_variables_path),
        "connection_descriptions": str(paths.connection_descriptions_path),
        "connection_citations": str(paths.connection_citations_path),
        "connection_citations_verified": str(paths.connection_citations_verified_path),
        "loop_citations": str(paths.loop_citations_path),
        "loop_citations_verified": str(paths.loop_citations_verified_path),
        "citations_verified": str(citations_verified_path) if run_citations else None,
        "gap_analysis": str(paths.gap_analysis_path) if run_gap_analysis else None,
        "paper_suggestions": str(paper_suggestions_path) if discover_papers else None,
        "patched": str(patched_file) if patched_file else None,
        "connections_csv": str(paths.connections_export_path),
        "loops_csv": str(paths.loops_export_path),
        "theory_enhancement": str(paths.theory_enhancement_path) if run_theory_enhancement else None,
        "enhanced_mdl": str(enhanced_mdl_path) if (run_theory_enhancement and enhanced_mdl_path) else None,
        "archetype_enhancement": str(paths.archetype_enhancement_path) if run_archetype_detection else None,
        "archetype_mdl": str(archetype_mdl_path) if (run_archetype_detection and archetype_mdl_path) else None,
        "rq_alignment": str(paths.rq_alignment_path) if run_rq_analysis else None,
        "rq_refinement": str(paths.rq_refinement_path) if run_rq_analysis else None,
        "theory_discovery": str(paths.theory_discovery_path) if run_theory_discovery else None,
    }

    # Save run metadata if versioning is enabled
    if run_id:
        from .run_metadata import create_run_metadata, save_run_metadata, update_latest_symlink

        pipeline_args = {
            "run_loops": run_loops,
            "run_citations": run_citations,
            "run_theory_enhancement": run_theory_enhancement,
            "run_archetype_detection": run_archetype_detection,
            "run_rq_analysis": run_rq_analysis,
            "run_theory_discovery": run_theory_discovery,
            "run_gap_analysis": run_gap_analysis,
            "discover_papers": discover_papers,
            "apply_patch": apply_patch,
        }

        metadata = create_run_metadata(
            run_id=run_id,
            project=project,
            artifacts_dir=paths.artifacts_dir,
            pipeline_args=pipeline_args,
            pipeline_result=result
        )

        metadata_path = save_run_metadata(paths.artifacts_dir, metadata)
        logger.info(f"Run metadata saved to: {metadata_path}")

        # Update latest symlink
        base_artifacts_dir = cfg.projects_dir / project / "artifacts"
        update_latest_symlink(base_artifacts_dir, run_id)
        logger.info(f"Updated 'latest' symlink to point to: {run_id}")

    return result
