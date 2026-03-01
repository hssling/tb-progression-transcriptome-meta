from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def random_effects_meta(effects: np.ndarray, variances: np.ndarray) -> tuple[float, float, float]:
    w = 1.0 / np.clip(variances, 1e-12, None)
    fixed = np.sum(w * effects) / np.sum(w)
    q = np.sum(w * (effects - fixed) ** 2)
    df = max(len(effects) - 1, 1)
    c = np.sum(w) - (np.sum(w**2) / np.sum(w))
    tau2 = max((q - df) / max(c, 1e-12), 0.0)
    wr = 1.0 / (np.clip(variances, 1e-12, None) + tau2)
    mu = np.sum(wr * effects) / np.sum(wr)
    se = np.sqrt(1.0 / np.sum(wr))
    i2 = max((q - df) / max(q, 1e-12), 0.0) * 100.0
    return float(mu), float(se), float(i2)


def meta_analyze_gene_effects(de_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for gene, sub in de_df.groupby("gene"):
        effects = sub["effect_size"].to_numpy(float)
        variances = 1.0 / np.clip((sub["n_prog"] + sub["n_nonprog"]).to_numpy(float), 1, None)
        if len(effects) < 2:
            continue
        mu, se, i2 = random_effects_meta(effects, variances)
        z = mu / max(se, 1e-12)
        rows.append(
            {
                "gene": gene,
                "meta_effect": mu,
                "meta_se": se,
                "meta_z": z,
                "i2": i2,
                "n_cohorts": len(sub),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["abs_meta_z"] = out["meta_z"].abs()
    out = out.sort_values("abs_meta_z", ascending=False).reset_index(drop=True)
    return out


def leave_one_cohort_out_meta(de_df: pd.DataFrame) -> pd.DataFrame:
    cohorts = sorted(de_df["cohort_id"].unique())
    rows = []
    for c in cohorts:
        sub = de_df[de_df["cohort_id"] != c]
        meta = meta_analyze_gene_effects(sub)
        if meta.empty:
            continue
        top = meta.head(1).iloc[0]
        rows.append({"left_out": c, "top_gene": top["gene"], "top_meta_z": float(top["meta_z"])})
    return pd.DataFrame(rows)


def plot_forest_top_genes(de_df: pd.DataFrame, meta_df: pd.DataFrame, out_file: str | Path, top_n: int = 8) -> None:
    top = meta_df.head(top_n)["gene"].tolist()
    sub = de_df[de_df["gene"].isin(top)]
    if sub.empty:
        return

    fig, ax = plt.subplots(figsize=(8, max(4, top_n * 0.6)))
    ypos = 0
    yticks = []
    ylabels = []
    for gene in top:
        gsub = sub[sub["gene"] == gene]
        for _, r in gsub.iterrows():
            ax.scatter(r["effect_size"], ypos, color="tab:blue", s=20)
            yticks.append(ypos)
            ylabels.append(f"{gene} ({r['cohort_id']})")
            ypos += 1
        m = meta_df[meta_df["gene"] == gene].iloc[0]
        ax.scatter(m["meta_effect"], ypos, color="tab:red", marker="D", s=30)
        yticks.append(ypos)
        ylabels.append(f"{gene} (meta)")
        ypos += 1

    ax.axvline(0, color="gray", linestyle="--", linewidth=1)
    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=8)
    ax.set_xlabel("Effect size (Hedges g)")
    ax.set_title("Forest-style plot for top meta-analysis genes")
    fig.tight_layout()
    Path(out_file).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_file, dpi=220)
    plt.close(fig)
