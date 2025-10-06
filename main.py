import logging
from pathlib import Path

from sd_model.pipeline.parse import parse_mdl
from sd_model.pipeline.loops import compute_loops
from sd_model.pipeline.interpret import interpret_loops
from sd_model.pipeline.theory_validation import validate_model
from sd_model.pipeline.improve import improve_model
from sd_model.config import settings


def main():
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    logging.info("Starting full SD_model pipeline")

    # Paths
    mdl = Path("untitled.mdl")

    # Step 1: Parse
    logging.info("Step 1: Parsing MDL → connections.json")
    parse_mdl(mdl_path=mdl, out_path=Path("connections.json"), api_key=settings.deepseek_api_key, model=settings.model_name)

    # Step 2: Loops
    logging.info("Step 2: Computing loops → loops.json")
    compute_loops(connections_path=Path("connections.json"), out_path=Path("loops.json"))

    # Step 3: Interpret
    logging.info("Step 3: Interpreting loops → loops_interpreted.json")
    interpret_loops(loops_path=Path("loops.json"), out_path=Path("loops_interpreted.json"), api_key=settings.deepseek_api_key, model=settings.model_name)

    # Step 4: Theory validation
    logging.info("Step 4: Theory validation → theory_validation.json")
    validate_model(connections_path=Path("connections.json"), loops_path=Path("loops_interpreted.json"), theories_csv=Path("knowledge/theories.csv"), out_path=Path("theory_validation.json"), api_key=settings.deepseek_api_key, model=settings.model_name)

    # Step 5: Improvements
    logging.info("Step 5: Improvements → model_improvements.json")
    improve_model(validation_path=Path("theory_validation.json"), connections_path=Path("connections.json"), out_path=Path("model_improvements.json"), api_key=settings.deepseek_api_key, model=settings.model_name)

    logging.info("Pipeline complete. Artifacts ready in project root.")


if __name__ == "__main__":
    main()
