from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from tbmeta.data.schemas import validate_registry_schema
from tbmeta.utils.logging import get_logger


def auto_curate(df: pd.DataFrame, min_samples_preferred: int = 30) -> pd.DataFrame:
    out = df.copy()
    out["status"] = out["status"].fillna("candidate")
    out["reason_skipped"] = out["reason_skipped"].fillna("")

    low_n = out["n_samples"].fillna(0).astype(int) < min_samples_preferred
    out.loc[low_n & (out["status"] == "candidate"), "status"] = "small_n"

    non_human = ~out["organism"].fillna("").str.contains("Homo sapiens|human", case=False, regex=True)
    out.loc[non_human, ["status", "reason_skipped"]] = ["skipped", "non_human"]

    text = (out["title"].fillna("") + " " + out.get("summary", pd.Series([""] * len(out))).fillna("")).str.lower()
    blood_like = text.str.contains("blood|pbmc|peripheral blood", case=False, regex=True)
    progress_like = text.str.contains(
        "progress|non-progress|incident|risk|latent|household|contact", case=False, regex=True
    )
    out.loc[(blood_like & progress_like) & (out["status"] != "skipped"), "status"] = "candidate"
    out.loc[(~blood_like) & (out["status"] != "skipped"), "status"] = "needs_review"

    return out


def run_curation(cfg: dict[str, Any]) -> pd.DataFrame:
    logger = get_logger("tbmeta.curation", Path(cfg["paths"]["logs_dir"]) / "curate.log")
    reg_dir = Path(cfg["paths"]["registry_dir"])
    raw_csv = reg_dir / "registry_raw.csv"
    curated_csv = reg_dir / "registry_curated.csv"

    override = cfg["curation"].get("curated_csv")
    if override:
        df = pd.read_csv(override)
        validate_registry_schema(df)
        df.to_csv(curated_csv, index=False)
        logger.info("Using user curated registry: %s", override)
        return df

    df = pd.read_csv(raw_csv)
    df = auto_curate(df, int(cfg["curation"]["min_samples_preferred"]))
    validate_registry_schema(df)
    df.to_csv(curated_csv, index=False)
    logger.info("Curated %d datasets", len(df))
    return df
