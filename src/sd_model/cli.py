from pathlib import Path
import typer
from sd_model.pipeline.parse import parse_mdl
from sd_model.pipeline.loops import compute_loops
from sd_model.pipeline.interpret import interpret_loops as interpret_loops_pipeline
from sd_model.pipeline.theory_validation import validate_model as validate_model_pipeline
from sd_model.pipeline.improve import improve_model as improve_model_pipeline

app = typer.Typer(help="SD Model CLI: parse, analyze, validate, improve")


@app.command()
def parse(mdl: Path = typer.Argument(Path("untitled.mdl"), help="Path to .mdl file"),
          out: Path = typer.Option(Path("connections.json"), help="Output connections JSON"),
          model: str = typer.Option("deepseek-chat", help="LLM model name")):
    data = parse_mdl(mdl, out, api_key=None, model=model)
    typer.echo(f"Extracted {len(data.get('connections', []))} connections → {out}")


@app.command()
def loops(connections: Path = typer.Option(Path("connections.json"), help="Input connections JSON"),
          out: Path = typer.Option(Path("loops.json"), help="Output loops JSON")):
    result = compute_loops(connections, out)
    typer.echo(f"Found {result['total_loops']} loops → {out}")


@app.command("interpret")
def interpret_loops(loops_path: Path = typer.Option(Path("loops.json")),
                    out: Path = typer.Option(Path("loops_interpreted.json")),
                    model: str = typer.Option("deepseek-chat")):
    result = interpret_loops_pipeline(loops_path, out, api_key=None, model=model)
    typer.echo(f"Interpreted loops saved → {out}")


@app.command("validate-theory")
def validate_theory(connections: Path = typer.Option(Path("connections.json")),
                    loops_path: Path = typer.Option(Path("loops_interpreted.json")),
                    theories_csv: Path = typer.Option(Path("knowledge/theories.csv")),
                    out: Path = typer.Option(Path("theory_validation.json")),
                    model: str = typer.Option("deepseek-chat")):
    result = validate_model_pipeline(connections, loops_path, theories_csv, out, api_key=None, model=model)
    typer.echo(f"Theory validation saved → {out} (avg={result.get('average_alignment', 0):.1f})")


@app.command("improve")
def improve_model(connections: Path = typer.Option(Path("connections.json")),
                  validation: Path = typer.Option(Path("theory_validation.json")),
                  out: Path = typer.Option(Path("model_improvements.json")),
                  model: str = typer.Option("deepseek-chat")):
    result = improve_model_pipeline(validation, connections, out, api_key=None, model=model)
    typer.echo(f"Improvements saved → {out}")


def main():
    app()


if __name__ == "__main__":
    main()
