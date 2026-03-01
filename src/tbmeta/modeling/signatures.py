from __future__ import annotations

import numpy as np
import pandas as pd


def select_signature_genes(meta_df: pd.DataFrame, top_n: int = 25, random_state: int = 42) -> pd.DataFrame:
    if meta_df.empty:
        return pd.DataFrame(columns=["gene", "meta_z", "stability"])

    rng = np.random.default_rng(random_state)
    m = meta_df.copy().head(max(top_n * 3, top_n))
    # Simple bootstrap stability from meta-z noise perturbations.
    counts = {g: 0 for g in m["gene"]}
    for _ in range(100):
        noise = rng.normal(0, 0.2, size=len(m))
        idx = np.argsort(-(np.abs(m["meta_z"].to_numpy() + noise)))[:top_n]
        for g in m.iloc[idx]["gene"]:
            counts[g] += 1

    sig = m[["gene", "meta_z"]].copy()
    sig["stability"] = sig["gene"].map(lambda g: counts[g] / 100)
    sig = sig.sort_values(["stability", "meta_z"], ascending=[False, False]).head(top_n)
    return sig.reset_index(drop=True)
