from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def _make_cohort(cohort_id: str, n_samples: int, n_genes: int, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    genes = [f"GENE{i:04d}" for i in range(n_genes)]
    base = rng.normal(0, 1, size=(n_samples, n_genes))
    outcome = rng.binomial(1, 0.35, size=n_samples)

    # Inject signal in first 20 genes.
    signal = outcome[:, None] * rng.normal(1.0, 0.25, size=(n_samples, 20))
    base[:, :20] = base[:, :20] + signal

    expr = pd.DataFrame(base, columns=genes)
    expr.insert(0, "sample_id", [f"{cohort_id}_S{i:03d}" for i in range(n_samples)])

    months = rng.choice([0, 1, 3, 6], size=n_samples, p=[0.7, 0.1, 0.1, 0.1])
    meta = pd.DataFrame(
        {
            "sample_id": expr["sample_id"],
            "cohort_id": cohort_id,
            "progressor": outcome,
            "timepoint_month": months,
            "sex": rng.choice(["M", "F"], size=n_samples),
            "age": rng.integers(12, 65, size=n_samples),
            "hiv": rng.choice(["negative", "positive"], size=n_samples, p=[0.9, 0.1]),
            "platform_type": "rnaseq" if "B" in cohort_id else "microarray",
        }
    )
    return expr, meta


def generate_synthetic_cohorts(output_dir: str | Path, seed: int = 42) -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    specs = [("SYNTH_COHORT_A", 80, 400), ("SYNTH_COHORT_B", 70, 420), ("SYNTH_COHORT_C", 60, 380)]

    cohort_ids = []
    for cid, n, g in specs:
        expr, meta = _make_cohort(cid, n, g, rng)
        cdir = out / cid
        cdir.mkdir(parents=True, exist_ok=True)
        expr.to_parquet(cdir / "expression_raw.parquet", index=False)
        meta.to_parquet(cdir / "metadata_raw.parquet", index=False)
        cohort_ids.append(cid)
    return cohort_ids
