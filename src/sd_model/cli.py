from pathlib import Path
import typer
from sd_model.pipeline.parse import parse_mdl
from sd_model.pipeline.loops import compute_loops
from sd_model.pipeline.interpret import interpret_loops as interpret_loops_pipeline
from sd_model.pipeline.theory_validation import validate_model as validate_model_pipeline
from sd_model.pipeline.improve import improve_model as improve_model_pipeline
from sd_model.config import settings

app = typer.Typer(help="SD Model CLI: parse, analyze, validate, improve")


@app.command()
def parse(mdl: Path = typer.Argument(Path("untitled.mdl"), help="Path to .mdl file"),
          out: Path = typer.Option(Path("connections.json"), help="Output connections JSON"),
          model: str | None = typer.Option(None, help="LLM model name (default from config)")):
    data = parse_mdl(mdl, out, api_key=None, model=model or settings.model_name)
    typer.echo(f"Extracted {len(data.get('connections', []))} connections → {out}")


@app.command()
def loops(connections: Path = typer.Option(Path("connections.json"), help="Input connections JSON"),
          out: Path = typer.Option(Path("loops.json"), help="Output loops JSON")):
    result = compute_loops(connections, out)
    typer.echo(f"Found {result['total_loops']} loops → {out}")


@app.command("interpret")
def interpret_loops(loops_path: Path = typer.Option(Path("loops.json")),
                    out: Path = typer.Option(Path("loops_interpreted.json")),
                    model: str | None = typer.Option(None)):
    result = interpret_loops_pipeline(loops_path, out, api_key=None, model=model or settings.model_name)
    typer.echo(f"Interpreted loops saved → {out}")


@app.command("validate-theory")
def validate_theory(connections: Path = typer.Option(Path("connections.json")),
                    loops_path: Path = typer.Option(Path("loops_interpreted.json")),
                    theories_csv: Path = typer.Option(Path("knowledge/theories.csv")),
                    out: Path = typer.Option(Path("theory_validation.json")),
                    model: str | None = typer.Option(None)):
    result = validate_model_pipeline(connections, loops_path, theories_csv, out, api_key=None, model=model or settings.model_name)
    typer.echo(f"Theory validation saved → {out} (avg={result.get('average_alignment', 0):.1f})")


@app.command("improve")
def improve_model(connections: Path = typer.Option(Path("connections.json")),
                  validation: Path = typer.Option(Path("theory_validation.json")),
                  out: Path = typer.Option(Path("model_improvements.json")),
                  model: str | None = typer.Option(None)):
    result = improve_model_pipeline(validation, connections, out, api_key=None, model=model or settings.model_name)


@app.command("run-all")
def run_all(mdl: Path = typer.Option(Path("untitled.mdl")),
            theories_csv: Path = typer.Option(Path("knowledge/theories.csv"))):
    """Run full pipeline: parse → loops → interpret → validate-theory → improve."""
    data = parse_mdl(mdl, Path("connections.json"), api_key=None, model=settings.model_name)
    typer.echo(f"Parsed {len(data.get('connections', []))} connections")
    loops = compute_loops(Path("connections.json"), Path("loops.json"))
    typer.echo(f"Found {loops.get('total_loops', 0)} loops")
    inter = interpret_loops_pipeline(Path("loops.json"), Path("loops_interpreted.json"), api_key=None, model=settings.model_name)
    typer.echo(f"Interpreted loops; insights: {bool(inter.get('system_insights'))}")
    val = validate_model_pipeline(Path("connections.json"), Path("loops_interpreted.json"), theories_csv, Path("theory_validation.json"), api_key=None, model=settings.model_name)
    typer.echo(f"Average alignment: {val.get('average_alignment', 'n/a')}")
    imp = improve_model_pipeline(Path("theory_validation.json"), Path("connections.json"), Path("model_improvements.json"), api_key=None, model=settings.model_name)
    typer.echo(f"Improvements: +{imp.get('statistics', {}).get('additions_proposed', 0)} / new vars {imp.get('statistics', {}).get('new_variables', 0)}")
    typer.echo(f"Improvements saved → {out}")


def main():
    app()


if __name__ == "__main__":
    main()
