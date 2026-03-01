from __future__ import annotations

from pathlib import Path

import typer

from tbmeta.config import ensure_dirs, load_config
from tbmeta.data.curation import run_curation
from tbmeta.data.discovery import run_discovery
from tbmeta.data.download import run_download
from tbmeta.data.preprocess import run_preprocess
from tbmeta.integrations.openclaw_adapter import OpenClawSettings, healthcheck
from tbmeta.pipeline import run_analysis
from tbmeta.reporting.citations import generate_bibliography
from tbmeta.reporting.manuscript import generate_manuscript
from tbmeta.reporting.submission import generate_submission_package
from tbmeta.utils.checkpoint import mark_completed, should_skip
from tbmeta.utils.logging import get_logger

app = typer.Typer(help="TB progression transcriptome meta-analysis pipeline")


def _cfg(path: str):
    cfg = load_config(path)
    ensure_dirs(cfg)
    return cfg


def _run_step(cfg, step: str, force: bool, fn):
    logger = get_logger("tbmeta.cli", Path(cfg["paths"]["logs_dir"]) / "pipeline.log")
    if should_skip(bool(cfg["runtime"]["resume"]), force, cfg["paths"]["checkpoint_dir"], step):
        logger.info("Skipping step %s (checkpoint found)", step)
        return
    fn()
    mark_completed(cfg["paths"]["checkpoint_dir"], step)


@app.command()
def discover(config: str = typer.Option("configs/config.yaml"), mode: str = typer.Option("full"), force: bool = False):
    cfg = _cfg(config)
    _run_step(cfg, "discover", force, lambda: run_discovery(cfg, mode=mode))


@app.command()
def curate(config: str = typer.Option("configs/config.yaml"), force: bool = False):
    cfg = _cfg(config)
    _run_step(cfg, "curate", force, lambda: run_curation(cfg))


@app.command()
def download(config: str = typer.Option("configs/config.yaml"), mode: str = typer.Option("full"), force: bool = False):
    cfg = _cfg(config)
    _run_step(cfg, "download", force, lambda: run_download(cfg, mode=mode))


@app.command()
def preprocess(config: str = typer.Option("configs/config.yaml"), force: bool = False):
    cfg = _cfg(config)
    _run_step(cfg, "preprocess", force, lambda: run_preprocess(cfg))


@app.command()
def analyze(config: str = typer.Option("configs/config.yaml"), force: bool = False):
    cfg = _cfg(config)
    _run_step(cfg, "analyze", force, lambda: run_analysis(cfg))


@app.command()
def manuscript(config: str = typer.Option("configs/config.yaml"), force: bool = False):
    cfg = _cfg(config)
    _run_step(cfg, "manuscript", force, lambda: generate_manuscript(cfg))


@app.command()
def citations(config: str = typer.Option("configs/config.yaml"), force: bool = False):
    cfg = _cfg(config)
    _run_step(cfg, "citations", force, lambda: generate_bibliography(cfg))


@app.command()
def submission(config: str = typer.Option("configs/config.yaml"), force: bool = False):
    cfg = _cfg(config)
    _run_step(cfg, "submission", force, lambda: generate_submission_package(cfg))


@app.command()
def dashboard(config: str = typer.Option("configs/config.yaml")):
    cfg = _cfg(config)
    import sys

    import streamlit.web.cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        "app/streamlit_app.py",
        "--server.address",
        str(cfg["dashboard"]["host"]),
        "--server.port",
        str(cfg["dashboard"]["port"]),
    ]
    raise SystemExit(stcli.main())


@app.command("openclaw-check")
def openclaw_check(config: str = typer.Option("configs/config.yaml")):
    cfg = _cfg(config)
    settings = OpenClawSettings.from_config(cfg)
    report = healthcheck(settings)
    typer.echo(report)


@app.command()
def all(
    config: str = typer.Option("configs/config.yaml"),
    mode: str = typer.Option("full", help="full|demo"),
    force: bool = typer.Option(False, help="Ignore checkpoints and rerun all steps"),
):
    cfg = _cfg(config)
    _run_step(cfg, "discover", force, lambda: run_discovery(cfg, mode=mode))
    _run_step(cfg, "curate", force, lambda: run_curation(cfg))
    _run_step(cfg, "download", force, lambda: run_download(cfg, mode=mode))
    _run_step(cfg, "preprocess", force, lambda: run_preprocess(cfg))
    _run_step(cfg, "analyze", force, lambda: run_analysis(cfg))
    _run_step(cfg, "manuscript", force, lambda: generate_manuscript(cfg))
    _run_step(cfg, "citations", force, lambda: generate_bibliography(cfg))
    _run_step(cfg, "submission", force, lambda: generate_submission_package(cfg))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
