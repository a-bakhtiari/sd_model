import json
import subprocess
from pathlib import Path
import typer

app = typer.Typer(help="SD Model CLI: parse, analyze, validate, improve")


@app.command()
def parse(mdl: Path = typer.Argument(..., help="Path to .mdl file"),
          out: Path = typer.Option(Path("connections.json"), help="Output connections JSON")):
    """Run the current parser script to extract connections."""
    # Bridge to existing script to avoid behavior change during scaffolding
    subprocess.check_call(["python3", "1-vensim_parser.py"])  # uses configured path inside the script
    if out != Path("connections.json") and Path("connections.json").exists():
        Path("connections.json").replace(out)
    typer.echo(f"Connections saved to {out}")


@app.command()
def loops(connections: Path = typer.Option(Path("connections.json"), help="Input connections JSON"),
          out: Path = typer.Option(Path("loops.json"), help="Output loops JSON")):
    """Run the current graph loops script."""
    subprocess.check_call(["python3", "2-graph_algorithm.py"])  # maintains existing behavior
    if out != Path("loops.json") and Path("loops.json").exists():
        Path("loops.json").replace(out)
    typer.echo(f"Loops saved to {out}")


@app.command("interpret")
def interpret_loops(loops_path: Path = typer.Option(Path("loops.json")),
                    out: Path = typer.Option(Path("loops_interpreted.json"))):
    """Run the current LLM loop interpretation script."""
    subprocess.check_call(["python3", "3-LLM_loop_interpretation.py"])  # uses env for key
    if out != Path("loops_interpreted.json") and Path("loops_interpreted.json").exists():
        Path("loops_interpreted.json").replace(out)
    typer.echo(f"Loop interpretations saved to {out}")


@app.command("validate-theory")
def validate_theory(out: Path = typer.Option(Path("theory_validation.json"))):
    """Run theory-based validation script."""
    subprocess.check_call(["python3", "4-theory_based_model_validation.py"])  # uses default theories
    if out != Path("theory_validation.json") and Path("theory_validation.json").exists():
        Path("theory_validation.json").replace(out)
    typer.echo(f"Theory validation saved to {out}")


@app.command("improve")
def improve_model(out: Path = typer.Option(Path("model_improvements.json"))):
    """Run model improvement generation script."""
    subprocess.check_call(["python3", "5-model_improvement.py"])  # reads prior artifacts
    if out != Path("model_improvements.json") and Path("model_improvements.json").exists():
        Path("model_improvements.json").replace(out)
    typer.echo(f"Improvements saved to {out}")


def main():
    app()


if __name__ == "__main__":
    main()

