from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def hedges_g(x1: np.ndarray, x0: np.ndarray) -> float:
    n1, n0 = len(x1), len(x0)
    if n1 < 2 or n0 < 2:
        return 0.0
    s1 = np.var(x1, ddof=1)
    s0 = np.var(x0, ddof=1)
    pooled = np.sqrt(((n1 - 1) * s1 + (n0 - 1) * s0) / (n1 + n0 - 2) + 1e-12)
    d = (np.mean(x1) - np.mean(x0)) / pooled
    j = 1 - (3 / (4 * (n1 + n0) - 9))
    return float(j * d)


def within_cohort_de(cohort_id: str, expr: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    y = meta.set_index("sample_id").loc[expr["sample_id"], "progressor"].values
    genes = [c for c in expr.columns if c != "sample_id"]
    rows = []
    x = expr.set_index("sample_id")

    for g in genes:
        v = x[g].values
        v1 = v[y == 1]
        v0 = v[y == 0]
        if len(v1) < 2 or len(v0) < 2:
            continue
        g_eff = hedges_g(v1, v0)
        t, p = stats.ttest_ind(v1, v0, equal_var=False)
        rows.append(
            {
                "cohort_id": cohort_id,
                "gene": g,
                "effect_size": g_eff,
                "log2fc": float(np.mean(v1) - np.mean(v0)),
                "pvalue": float(p),
                "n_prog": int(len(v1)),
                "n_nonprog": int(len(v0)),
            }
        )
    return pd.DataFrame(rows)


def save_within_cohort_de(all_de: pd.DataFrame, results_dir: str | Path) -> None:
    out = Path(results_dir) / "tables" / "within_cohort_de.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    all_de.to_csv(out, index=False)
