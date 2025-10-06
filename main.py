import logging
from pathlib import Path

from sd_model.pipeline.parse import parse_mdl
from sd_model.pipeline.loops import compute_loops
from sd_model.pipeline.interpret import interpret_loops
from sd_model.pipeline.theory_validation import validate_model
from sd_model.pipeline.improve import improve_model
from sd_model.config import settings
from sd_model.paths import (
    p_connections,
    p_loops,
    p_loops_i,
    p_val,
    p_impr,
    mdl_dir,
)


def main():
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    logging.info("Starting full SD_model pipeline")

    # Paths
    project = settings.project_name
    mdl = mdl_dir(project) / "untitled.mdl"

    # Step 1: Parse
    logging.info("Step 1: Parsing MDL → connections.json")
    parse_mdl(mdl_path=mdl, out_path=p_connections(project), api_key=settings.deepseek_api_key, model=settings.model_name)

    # Step 2: Loops
    logging.info("Step 2: Computing loops → loops.json")
    compute_loops(connections_path=p_connections(project), out_path=p_loops(project))

    # Step 3: Interpret
    logging.info("Step 3: Interpreting loops → loops_interpreted.json")
    interpret_loops(loops_path=p_loops(project), out_path=p_loops_i(project), api_key=settings.deepseek_api_key, model=settings.model_name)

    # Step 4: Theory validation
    logging.info("Step 4: Theory validation → theory_validation.json")
    validate_model(connections_path=p_connections(project), loops_path=p_loops_i(project), theories_csv=Path("knowledge/theories.csv"), out_path=p_val(project), api_key=settings.deepseek_api_key, model=settings.model_name)

    # Step 5: Improvements
    logging.info("Step 5: Improvements → model_improvements.json")
    improve_model(validation_path=p_val(project), connections_path=p_connections(project), out_path=p_impr(project), api_key=settings.deepseek_api_key, model=settings.model_name)

    logging.info("Pipeline complete. Artifacts ready in project root.")


if __name__ == "__main__":
    main()
