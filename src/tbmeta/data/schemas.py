from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

REQUIRED_REGISTRY_COLUMNS = [
    "gse_id",
    "title",
    "organism",
    "platform",
    "n_samples",
    "pmid",
    "status",
    "reason_skipped",
]


def validate_columns(df: pd.DataFrame, cols: Iterable[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def validate_registry_schema(df: pd.DataFrame) -> None:
    validate_columns(df, REQUIRED_REGISTRY_COLUMNS)
