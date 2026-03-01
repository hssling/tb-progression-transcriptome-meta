from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        cfg: dict[str, Any] = yaml.safe_load(f)
    return cfg


def ensure_dirs(cfg: dict[str, Any]) -> None:
    for key in [
        "raw_data",
        "registry_dir",
        "processed_data",
        "results_dir",
        "logs_dir",
        "checkpoint_dir",
        "cache_dir",
    ]:
        Path(cfg["paths"][key]).mkdir(parents=True, exist_ok=True)
    Path("results/tables").mkdir(parents=True, exist_ok=True)
    Path("results/figures").mkdir(parents=True, exist_ok=True)
    Path("results/models").mkdir(parents=True, exist_ok=True)
    Path("manuscripts").mkdir(parents=True, exist_ok=True)
