from __future__ import annotations
from pathlib import Path
from typing import Optional
import sqlite3
import typer
from sd_model.pipeline.parse import parse_mdl
from sd_model.pipeline.loops import compute_loops
from sd_model.pipeline.interpret import interpret_loops as interpret_loops_pipeline
from sd_model.pipeline.theory_validation import validate_model as validate_model_pipeline
from sd_model.pipeline.improve import improve_model as improve_model_pipeline
from sd_model.config import settings
from sd_model.paths import (
    connections_path as p_connections,
    loops_path as p_loops,
    loops_interpreted_path as p_loops_i,
    theory_validation_path as p_val,
    model_improvements_path as p_impr,
    mdl_dir,
    provenance_db_path,
    knowledge_theories_csv as p_theories,
)

app = typer.Typer(help="SD Model CLI: parse, analyze, validate, improve")


@app.command()
def parse(mdl: Path = typer.Argument(Path("untitled.mdl"), help="Path to .mdl file"),
          out: Optional[Path] = typer.Option(None, help="Output connections JSON (defaults to project path)"),
          project: Optional[str] = typer.Option(None, help="Project name"),
          model: Optional[str] = typer.Option(None, help="LLM model name (default from config)")):
    out_path = out or p_connections(project)
    data = parse_mdl(mdl, out_path, api_key=None, model=model or settings.model_name)
    typer.echo(f"Extracted {len(data.get('connections', []))} connections → {out_path}")


@app.command()
def loops(connections: Optional[Path] = typer.Option(None, help="Input connections JSON (defaults to project path)"),
          out: Optional[Path] = typer.Option(None, help="Output loops JSON (defaults to project path)"),
          project: Optional[str] = typer.Option(None)):
    in_path = connections or p_connections(project)
    out_path = out or p_loops(project)
    result = compute_loops(in_path, out_path)
    typer.echo(f"Found {result['total_loops']} loops → {out_path}")


@app.command("interpret")
def interpret_loops(loops_path: Optional[Path] = typer.Option(None),
                    out: Optional[Path] = typer.Option(None),
                    project: Optional[str] = typer.Option(None),
                    model: Optional[str] = typer.Option(None)):
    in_path = loops_path or p_loops(project)
    out_path = out or p_loops_i(project)
    result = interpret_loops_pipeline(in_path, out_path, api_key=None, model=model or settings.model_name)
    typer.echo(f"Interpreted loops saved → {out_path}")


@app.command("validate-theory")
def validate_theory(connections: Optional[Path] = typer.Option(None),
                    loops_path: Optional[Path] = typer.Option(None),
                    theories_csv: Optional[Path] = typer.Option(None),
                    out: Optional[Path] = typer.Option(None),
                    project: Optional[str] = typer.Option(None),
                    model: Optional[str] = typer.Option(None)):
    in_conn = connections or p_connections(project)
    in_loops = loops_path or p_loops_i(project)
    in_theories = theories_csv or p_theories(project)
    out_path = out or p_val(project)
    result = validate_model_pipeline(in_conn, in_loops, in_theories, out_path, api_key=None, model=model or settings.model_name)
    typer.echo(f"Theory validation saved → {out_path} (avg={result.get('average_alignment', 0):.1f})")


@app.command("improve")
def improve_model(connections: Optional[Path] = typer.Option(None),
                  validation: Optional[Path] = typer.Option(None),
                  out: Optional[Path] = typer.Option(None),
                  project: Optional[str] = typer.Option(None),
                  model: Optional[str] = typer.Option(None)):
    in_conn = connections or p_connections(project)
    in_val = validation or p_val(project)
    out_path = out or p_impr(project)
    result = improve_model_pipeline(in_val, in_conn, out_path, api_key=None, model=model or settings.model_name)
    typer.echo(f"Improvements saved → {out_path}")


@app.command("run-all")
def run_all(mdl: Optional[Path] = typer.Option(None),
            theories_csv: Optional[Path] = typer.Option(None),
            project: Optional[str] = typer.Option(None)):
    """Run full pipeline: parse → loops → interpret → validate-theory → improve."""
    mdl_path = mdl or (mdl_dir(project) / "untitled.mdl")
    out_conn = p_connections(project)
    out_loops = p_loops(project)
    out_loops_i = p_loops_i(project)
    out_val = p_val(project)
    out_impr = p_impr(project)

    data = parse_mdl(mdl_path, out_conn, api_key=None, model=settings.model_name)
    typer.echo(f"Parsed {len(data.get('connections', []))} connections → {out_conn}")
    loops_res = compute_loops(out_conn, out_loops)
    typer.echo(f"Found {loops_res.get('total_loops', 0)} loops → {out_loops}")
    inter = interpret_loops_pipeline(out_loops, out_loops_i, api_key=None, model=settings.model_name)
    typer.echo(f"Interpreted loops → {out_loops_i}; insights present: {bool(inter.get('system_insights'))}")
    val = validate_model_pipeline(out_conn, out_loops_i, theories_csv or p_theories(project), out_val, api_key=None, model=settings.model_name)
    typer.echo(f"Theory validation → {out_val}; average alignment: {val.get('average_alignment', 'n/a')}")
    imp = improve_model_pipeline(out_val, out_conn, out_impr, api_key=None, model=settings.model_name)
    typer.echo(f"Improvements → {out_impr}; +{imp.get('statistics', {}).get('additions_proposed', 0)} additions, new vars {imp.get('statistics', {}).get('new_variables', 0)}")


provenance_app = typer.Typer(help="Inspect provenance database")


@provenance_app.command("stats")
def prov_stats(project: Optional[str] = typer.Option(None)):
    db = provenance_db_path(project)
    con = sqlite3.connect(db)
    cur = con.cursor()
    rows = cur.execute("select kind,count(*) from artifacts group by kind").fetchall()
    typer.echo(f"DB: {db}")
    for kind, cnt in rows:
        typer.echo(f"{kind}: {cnt}")
    total_conn = cur.execute("select count(*) from connections").fetchone()[0]
    total_loops = cur.execute("select count(*) from loops").fetchone()[0]
    typer.echo(f"connections rows: {total_conn}")
    typer.echo(f"loops rows: {total_loops}")
    con.close()


@provenance_app.command("list")
def prov_list(project: Optional[str] = typer.Option(None), kind: Optional[str] = typer.Option(None), limit: int = typer.Option(20)):
    db = provenance_db_path(project)
    con = sqlite3.connect(db)
    cur = con.cursor()
    if kind:
        rows = cur.execute("select id, kind, path, created_at from artifacts where kind=? order by created_at desc limit ?", (kind, limit)).fetchall()
    else:
        rows = cur.execute("select id, kind, path, created_at from artifacts order by created_at desc limit ?", (limit,)).fetchall()
    typer.echo(f"DB: {db}")
    for r in rows:
        typer.echo(f"id={r[0]} kind={r[1]} created_at={r[3]} path={r[2]}")
    con.close()


@provenance_app.command("evidence")
def prov_evidence(project: Optional[str] = typer.Option(None), artifact_id: int = typer.Argument(...)):
    db = provenance_db_path(project)
    con = sqlite3.connect(db)
    cur = con.cursor()
    rows = cur.execute("select id, source, confidence, note, created_at from evidence where item_type='artifact' and item_id=? order by created_at desc", (artifact_id,)).fetchall()
    typer.echo(f"DB: {db}")
    for r in rows:
        typer.echo(f"evidence_id={r[0]} source={r[1]} conf={r[2]} created_at={r[4]}\n  note={r[3]}")
    con.close()


@provenance_app.command("diff-connections")
def prov_diff_connections(project: Optional[str] = typer.Option(None), a: int = typer.Argument(...), b: int = typer.Argument(...)):
    db = provenance_db_path(project)
    con = sqlite3.connect(db)
    cur = con.cursor()
    def fetch(artifact_id: int):
        return set(x[0] for x in cur.execute("select source||'→'||target||' ('||sign||')' from connections where artifact_id=?", (artifact_id,)).fetchall())
    A = fetch(a)
    B = fetch(b)
    added = B - A
    removed = A - B
    typer.echo(f"Added ({len(added)}):")
    for x in sorted(list(added))[:20]:
        typer.echo(f"  {x}")
    typer.echo(f"Removed ({len(removed)}):")
    for x in sorted(list(removed))[:20]:
        typer.echo(f"  {x}")
    con.close()


app.add_typer(provenance_app, name="provenance")


def main():
    app()


if __name__ == "__main__":
    main()
