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
from .pipeline.theory_validation import validate_against_theories
from .pipeline.verify_citations import verify_citations
from .pipeline.improve import propose_improvements
from .pipeline.apply_patch import apply_model_patch
from .pipeline.citation_verification import verify_all_citations, generate_connection_citation_table, verify_llm_generated_citations
from .pipeline.gap_analysis import identify_gaps
from .pipeline.paper_discovery import suggest_papers_for_gaps
from .pipeline.csv_export import generate_connections_csv, generate_loops_csv
from .pipeline.theory_enhancement import run_theory_enhancement
from .pipeline.rq_alignment import run_rq_alignment
from .pipeline.rq_refinement import run_rq_refinement
from .pipeline.theory_discovery import run_theory_discovery
from .llm.client import LLMClient
from .pipeline.llm_extraction import infer_variable_types, infer_connections, extract_diagram_style
from .provenance.store import log_event
from .validation.schema import validate_json_schema
from .external.semantic_scholar import SemanticScholarClient
from .knowledge.loader import load_research_questions, load_theories

logger = logging.getLogger(__name__)


def run_pipeline(
    project: str,
    apply_patch: bool = False,
    verify_cit: bool = False,
    discover_papers: bool = False,
    improve_model: bool = False
) -> Dict:
    """Run the full analysis pipeline for a project.

    Args:
        project: Project name
        apply_patch: Whether to apply model patches
        verify_cit: Whether to verify citations via Semantic Scholar
        discover_papers: Whether to run paper discovery for gaps
        improve_model: Whether to run model improvement modules (Step 8)
    """
    logger.info(f"Starting pipeline for project: {project}")
    cfg = load_config()
    paths = for_project(cfg, project)
    paths.ensure()

    logger.info(f"Looking for .mdl file in {paths.mdl_dir}")
    mdl_path = first_mdl_file(paths)
    if mdl_path is None:
        raise FileNotFoundError(f"No .mdl file found in {paths.mdl_dir}")
    logger.info(f"Found MDL file: {mdl_path.name}")

    logger.info("Initializing LLM client")
    client = LLMClient()

    logger.info("Extracting variables from MDL file...")
    variables_data = infer_variable_types(mdl_path, client)
    logger.info(f"✓ Found {len(variables_data.get('variables', []))} variables")

    logger.info("Extracting connections from MDL file...")
    connections_data = infer_connections(mdl_path, variables_data, client)
    logger.info(f"✓ Found {len(connections_data.get('connections', []))} connections")

    variables_path = paths.artifacts_dir / "variables_llm.json"
    connections_llm_path = paths.artifacts_dir / "connections_llm.json"
    diagram_style_path = paths.artifacts_dir / "diagram_style.json"

    variables_path.write_text(json.dumps(variables_data, indent=2), encoding="utf-8")
    connections_llm_path.write_text(json.dumps(connections_data, indent=2), encoding="utf-8")

    # Extract and save diagram style configuration
    style_data = extract_diagram_style(mdl_path)
    diagram_style_path.write_text(json.dumps(style_data, indent=2), encoding="utf-8")

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
    loop_descriptions_path = paths.artifacts_dir / "loop_descriptions.json"
    loop_descriptions = generate_loop_descriptions(
        loops_data=loops,
        llm_client=client,
        out_path=loop_descriptions_path,
        domain_context="open source software development"
    )
    logger.info(f"✓ Generated {len(loop_descriptions.get('descriptions', []))} loop descriptions")
    log_event(paths.db_dir / "provenance.sqlite", "loop_descriptions", {"count": len(loop_descriptions.get("descriptions", []))})

    # Generate connection descriptions
    logger.info("Generating connection descriptions...")
    connection_descriptions_path = paths.artifacts_dir / "connection_descriptions.json"
    descriptions = generate_connection_descriptions(
        connections_data={"connections": connections_named},
        variables_data=variables_data,
        llm_client=client,
        out_path=connection_descriptions_path
    )
    logger.info(f"✓ Generated {len(descriptions.get('descriptions', []))} connection descriptions")
    log_event(paths.db_dir / "provenance.sqlite", "connection_descriptions", {"count": len(descriptions.get("descriptions", []))})

    # Find citations for connections
    logger.info("Finding citations for connections...")
    connection_citations_path = paths.artifacts_dir / "connection_citations.json"
    conn_citations = find_connection_citations(
        connections_data={"connections": connections_named},
        descriptions_data=descriptions,
        llm_client=client,
        out_path=connection_citations_path
    )
    logger.info(f"✓ Found {len(conn_citations.get('citations', []))} connection citations")
    log_event(paths.db_dir / "provenance.sqlite", "connection_citations", {"count": len(conn_citations.get("citations", []))})

    # Find citations for loops
    logger.info("Finding citations for loops...")
    loop_citations_path = paths.artifacts_dir / "loop_citations.json"
    loop_cites = find_loop_citations(
        loops_data=loops,
        descriptions_data=loop_descriptions,
        llm_client=client,
        out_path=loop_citations_path
    )
    logger.info(f"✓ Found {len(loop_cites.get('citations', []))} loop citations")
    log_event(paths.db_dir / "provenance.sqlite", "loop_citations", {"count": len(loop_cites.get("citations", []))})

    # Verify LLM-generated connection citations
    logger.info("Verifying connection citations via Semantic Scholar...")
    from .external.semantic_scholar import SemanticScholarClient
    s2_client = SemanticScholarClient()
    connection_citations_verified_path = paths.artifacts_dir / "connection_citations_verified.json"
    connection_citations_debug_path = paths.artifacts_dir / "connection_citations_verification_debug.txt"
    verified_conn_citations = verify_llm_generated_citations(
        citations_path=connection_citations_path,
        output_path=connection_citations_verified_path,
        s2_client=s2_client,
        llm_client=client,
        debug_path=connection_citations_debug_path,
        verbose=False  # Don't print to console during pipeline run
    )
    summary = verified_conn_citations.get("summary", {})
    logger.info(f"✓ Verified {summary.get('verified', 0)}/{summary.get('total', 0)} connection citations")
    log_event(
        paths.db_dir / "provenance.sqlite",
        "connection_citations_verified",
        verified_conn_citations.get("summary", {})
    )

    # Verify LLM-generated loop citations
    logger.info("Verifying loop citations via Semantic Scholar...")
    loop_citations_verified_path = paths.artifacts_dir / "loop_citations_verified.json"
    loop_citations_debug_path = paths.artifacts_dir / "loop_citations_verification_debug.txt"
    verified_loop_citations = verify_llm_generated_citations(
        citations_path=loop_citations_path,
        output_path=loop_citations_verified_path,
        s2_client=s2_client,
        llm_client=client,
        debug_path=loop_citations_debug_path,
        verbose=False  # Don't print to console during pipeline run
    )
    loop_summary = verified_loop_citations.get("summary", {})
    logger.info(f"✓ Verified {loop_summary.get('verified', 0)}/{loop_summary.get('total', 0)} loop citations")
    log_event(
        paths.db_dir / "provenance.sqlite",
        "loop_citations_verified",
        verified_loop_citations.get("summary", {})
    )

    logger.info("Validating model against theories...")
    tv = validate_against_theories(
        connections_path=paths.connections_path,
        theories_dir=paths.theories_dir,
        bib_path=paths.references_bib_path,
        out_path=paths.theory_validation_path,
    )
    tv_summary = tv.get("summary", {})
    logger.info(f"✓ Theory validation: {tv_summary.get('theory_count', 0)} theories, "
                f"{tv_summary.get('confirmed_count', 0)} confirmed, "
                f"{tv_summary.get('novel_count', 0)} novel connections")
    # Validate JSON against schema when available
    try:
        validate_json_schema(tv, load_config().schemas_dir / "theory_validation.schema.json")
    except Exception:
        # Non-fatal; surface during CLI runs if needed
        pass
    log_event(paths.db_dir / "provenance.sqlite", "theory_validation", tv.get("summary", {}))

    try:
        _ = verify_citations(
            [paths.theory_validation_path, paths.model_improvements_path],
            bib_path=paths.references_bib_path,
        )
    except Exception:
        pass

    improvements = propose_improvements(
        theory_validation_path=paths.theory_validation_path,
        feedback_path=paths.feedback_json_path,
        out_path=paths.model_improvements_path,
    )
    try:
        validate_json_schema(
            improvements, load_config().schemas_dir / "model_improvements.schema.json"
        )
    except Exception:
        pass
    log_event(paths.db_dir / "provenance.sqlite", "improve", {"count": len(improvements.get("improvements", []))})

    try:
        _ = verify_citations(
            [paths.theory_validation_path, paths.model_improvements_path],
            bib_path=paths.references_bib_path,
        )
    except Exception:
        pass

    # Citation verification (on-demand) - OLD SYSTEM, kept for compatibility
    citations_verified_path = paths.artifacts_dir / "citations_verified.json"
    gap_analysis_path = paths.artifacts_dir / "gap_analysis.json"
    paper_suggestions_path = paths.artifacts_dir / "paper_suggestions.json"

    if verify_cit:
        # s2_client already initialized above for LLM citation verification
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
            out_path=paths.artifacts_dir / "connection_citations_legacy.json",
        )
        log_event(
            paths.db_dir / "provenance.sqlite",
            "verify_citations",
            {
                "total": len(verified_cits),
                "verified": sum(1 for v in verified_cits.values() if v.verified),
            },
        )

        # Gap analysis (using new connection citations)
        gaps = identify_gaps(connection_citations_path, gap_analysis_path)
        log_event(
            paths.db_dir / "provenance.sqlite",
            "gap_analysis",
            {"unsupported": len(gaps.get("unsupported_connections", []))},
        )

        # Paper discovery (optional, enabled by separate flag)
        if discover_papers:
            suggestions = suggest_papers_for_gaps(
                gaps_path=gap_analysis_path,
                s2_client=s2_client,
                llm_client=client,
                out_path=paper_suggestions_path,
                limit_per_gap=5,
            )
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

    # Generate CSV exports
    connections_csv_path = paths.artifacts_dir / "connections_export.csv"
    loops_csv_path = paths.artifacts_dir / "loops_export.csv"

    conn_csv_rows = generate_connections_csv(
        connections_path=paths.connections_path,
        descriptions_path=connection_descriptions_path,
        variables_path=variables_path,
        citations_path=connection_citations_verified_path,
        output_path=connections_csv_path,
    )
    log_event(paths.db_dir / "provenance.sqlite", "csv_export_connections", {"rows": conn_csv_rows})

    loop_csv_rows = generate_loops_csv(
        loops_path=paths.loops_path,
        descriptions_path=loop_descriptions_path,
        citations_path=loop_citations_verified_path,
        output_path=loops_csv_path,
    )
    log_event(paths.db_dir / "provenance.sqlite", "csv_export_loops", {"rows": loop_csv_rows})

    # Step 8: Model Improvement & Development (optional)
    if improve_model:
        logger.info("=" * 60)
        logger.info("Starting Model Improvement & Development modules...")
        logger.info("=" * 60)

        # Load research questions
        logger.info("Loading research questions...")
        rqs = load_research_questions(paths.rq_txt_path)
        logger.info(f"✓ Loaded {len(rqs)} research questions")

        # Load theories (convert to dict list for compatibility)
        logger.info("Loading theories...")
        theories_objs = load_theories(paths.theories_dir)
        theories = [{"name": t.theory_name, "description": t.description, "focus_area": t.focus_area} for t in theories_objs]
        logger.info(f"✓ Loaded {len(theories)} theories")

        # Module 2: Theory Enhancement
        logger.info("Running Theory Enhancement module...")
        try:
            theory_enh = run_theory_enhancement(
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

            # Apply theory enhancements to MDL
            if "error" not in theory_enh and len(theory_enh.get('theories', [])) > 0:
                logger.info("Applying theory enhancements to MDL...")
                try:
                    from .mdl_text_patcher import apply_theory_enhancements

                    enhanced_mdl_path = paths.artifacts_dir / f"{mdl_path.stem}_enhanced.mdl"

                    mdl_summary = apply_theory_enhancements(
                        mdl_path,
                        theory_enh,
                        enhanced_mdl_path,
                        add_colors=True,
                        use_llm_layout=True,
                        llm_client=client
                    )

                    logger.info(f"✓ MDL Enhancement complete: {mdl_summary['variables_added']} vars, {mdl_summary['connections_added']} conns")
                    log_event(paths.db_dir / "provenance.sqlite", "mdl_enhancement", mdl_summary)
                except Exception as e:
                    logger.error(f"✗ MDL Enhancement failed: {e}")
                    logger.exception("Full traceback:")
                    enhanced_mdl_path = None
            else:
                enhanced_mdl_path = None

        except Exception as e:
            logger.error(f"✗ Theory Enhancement failed: {e}")
            logger.exception("Full traceback:")
            # Write empty result so file exists
            paths.theory_enhancement_path.write_text(
                json.dumps({"error": str(e), "theories": []}, indent=2), encoding="utf-8"
            )
            enhanced_mdl_path = None

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

        # Module 5: Theory Discovery
        logger.info("Running Theory Discovery module...")
        try:
            theory_disc = run_theory_discovery(
                rqs=rqs,
                current_theories=theories,
                rq_alignment=rq_align
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
    return {
        "parsed": str(paths.parsed_path),
        "loops": str(paths.loops_path),
        "connections": str(paths.connections_path),
        "variables_llm": str(variables_path),
        "connections_llm": str(connections_llm_path),
        "connection_descriptions": str(connection_descriptions_path),
        "connection_citations": str(connection_citations_path),
        "connection_citations_verified": str(connection_citations_verified_path),
        "loop_citations": str(loop_citations_path),
        "loop_citations_verified": str(loop_citations_verified_path),
        "theory_validation": str(paths.theory_validation_path),
        "improvements": str(paths.model_improvements_path),
        "citations_verified": str(citations_verified_path) if verify_cit else None,
        "gap_analysis": str(gap_analysis_path) if verify_cit else None,
        "paper_suggestions": str(paper_suggestions_path) if (verify_cit and discover_papers) else None,
        "patched": str(patched_file) if patched_file else None,
        "connections_csv": str(connections_csv_path),
        "loops_csv": str(loops_csv_path),
        "theory_enhancement": str(paths.theory_enhancement_path) if improve_model else None,
        "enhanced_mdl": str(enhanced_mdl_path) if (improve_model and 'enhanced_mdl_path' in locals() and enhanced_mdl_path) else None,
        "rq_alignment": str(paths.rq_alignment_path) if improve_model else None,
        "rq_refinement": str(paths.rq_refinement_path) if improve_model else None,
        "theory_discovery": str(paths.theory_discovery_path) if improve_model else None,
    }
