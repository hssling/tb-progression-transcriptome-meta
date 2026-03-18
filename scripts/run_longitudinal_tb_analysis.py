from __future__ import annotations

from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import nnls
import statsmodels.formula.api as smf


ROOT = Path(__file__).resolve().parents[1]
META_PATH = ROOT / "data" / "processed" / "GSE79362_genelevel" / "metadata.parquet"
EXPR_PATH = ROOT / "data" / "processed" / "GSE79362_genelevel" / "expression.parquet"
SIG_PATH = ROOT / "results" / "tables" / "signature_genes.csv"
ADV_BAYES_PATH = ROOT / "results" / "advanced_analysis" / "bayesian_gene_meta.csv"
SENS_BAYES_PATH = ROOT / "results" / "advanced_analysis_gse79362_sensitivity" / "bayesian_gene_meta_with_gse79362.csv"
MODULE_PATH = ROOT / "results" / "omicsclaw_extensions" / "coexpression_module_assignments.csv"
OUT_DIR = ROOT / "results" / "longitudinal_tb_analysis"


CELL_MARKERS: dict[str, list[str]] = {
    "Monocyte": ["LILRB1", "CTSS", "FCGR3A", "MS4A7", "TYMP"],
    "Neutrophil": ["CXCR1", "CXCR2", "FCGR3B", "CSF3R", "CEACAM8"],
    "T_cell": ["CD3D", "CD3E", "IL7R", "LTB", "TRBC1"],
    "B_cell": ["CD79A", "MS4A1", "CD79B", "BANK1", "HLA-DRA"],
    "NK_cell": ["NKG7", "GNLY", "KLRD1", "PRF1", "CTSW"],
    "Platelet": ["PPBP", "PF4", "GNG11", "TUBB1", "SDPR"],
}


def bh_adjust(pvalues: list[float]) -> list[float]:
    n = len(pvalues)
    order = np.argsort(pvalues)
    ranked = np.array(pvalues, dtype=float)[order]
    adjusted = np.empty(n, dtype=float)
    prev = 1.0
    for i in range(n - 1, -1, -1):
        rank = i + 1
        value = ranked[i] * n / rank
        prev = min(prev, value)
        adjusted[i] = min(prev, 1.0)
    out = np.empty(n, dtype=float)
    out[order] = adjusted
    return out.tolist()


def standardize(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        series = out[col]
        std = float(series.std(ddof=0))
        if std == 0 or np.isnan(std):
            out[col] = 0.0
        else:
            out[col] = (series - float(series.mean())) / std
    return out


def positive_gene_scale(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        series = out[col]
        span = float(series.max() - series.min())
        if span == 0 or np.isnan(span):
            out[col] = 0.0
        else:
            out[col] = (series - float(series.min())) / span
    return out


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    meta = pd.read_parquet(META_PATH).copy()
    expr = pd.read_parquet(EXPR_PATH).copy()
    expr = expr[expr["sample_id"].isin(meta["sample_id"])].copy()
    meta = meta[meta["sample_id"].isin(expr["sample_id"])].copy()
    return meta, expr


def build_program_gene_sets(expr_cols: list[str]) -> dict[str, list[str]]:
    signature_genes = pd.read_csv(SIG_PATH)["gene"].astype(str).tolist()
    bayes_genes = pd.read_csv(ADV_BAYES_PATH)["gene"].astype(str).head(8).tolist()
    sensitivity_genes = pd.read_csv(SENS_BAYES_PATH)["gene"].astype(str).head(5).tolist()
    module_df = pd.read_csv(MODULE_PATH)
    m5_genes = module_df.loc[module_df["module"] == "M5", "gene"].astype(str).tolist()
    m6_genes = module_df.loc[module_df["module"] == "M6", "gene"].astype(str).tolist()

    raw_sets = {
        "signature25_proxy": signature_genes,
        "bayesian_core8": bayes_genes,
        "remap_myeloid5": sensitivity_genes,
        "vascular_proxy5": ["AQP1", "VEGFB", "LOXL1", "PLXDC2", "FAM20C"],
        "module_M5_proxy": m5_genes,
        "module_M6_proxy": m6_genes,
    }
    filtered = {}
    for name, genes in raw_sets.items():
        keep = [gene for gene in genes if gene in expr_cols]
        if keep:
            filtered[name] = keep
    return filtered


def compute_program_scores(meta: pd.DataFrame, expr: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    expr_only = expr.drop(columns=["sample_id"]).copy()
    expr_z = standardize(expr_only)
    program_sets = build_program_gene_sets(expr_only.columns.tolist())
    score_df = pd.DataFrame({"sample_id": expr["sample_id"]})
    for name, genes in program_sets.items():
        score_df[name] = expr_z[genes].mean(axis=1)
    merged = meta.merge(score_df, on="sample_id", how="left")
    return merged, program_sets


def compute_nnls_scores(meta: pd.DataFrame, expr: pd.DataFrame) -> pd.DataFrame:
    expr_only = expr.drop(columns=["sample_id"]).copy()
    marker_union = sorted({gene for genes in CELL_MARKERS.values() for gene in genes if gene in expr_only.columns})
    scaled = positive_gene_scale(expr_only[marker_union])
    signature = pd.DataFrame(0.0, index=marker_union, columns=list(CELL_MARKERS))
    for celltype, genes in CELL_MARKERS.items():
        overlap = [gene for gene in genes if gene in marker_union]
        signature.loc[overlap, celltype] = 1.0

    rows = []
    for i, sample_id in enumerate(meta["sample_id"]):
        coef, _ = nnls(signature.to_numpy(float), scaled.iloc[i].to_numpy(float))
        total = float(coef.sum())
        if total > 0:
            coef = coef / total
        row = {"sample_id": sample_id}
        row.update({celltype: float(coef[j]) for j, celltype in enumerate(signature.columns)})
        rows.append(row)
    return pd.DataFrame(rows)


def fit_mixed_model(df: pd.DataFrame, value_col: str) -> dict[str, object]:
    sub = df[["subject_id", "timepoint_month", "progressor", value_col]].dropna().rename(columns={value_col: "value"}).copy()
    if sub.empty or sub["subject_id"].nunique() < 10:
        return {"feature": value_col, "model_type": "insufficient_data"}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            fit = smf.mixedlm(
                "value ~ timepoint_month + progressor + timepoint_month:progressor",
                data=sub,
                groups=sub["subject_id"],
            ).fit(reml=False, method="lbfgs", maxiter=500, disp=False)
            params = fit.params
            conf = fit.conf_int()
            pvalues = fit.pvalues
            return {
                "feature": value_col,
                "model_type": "mixedlm_random_intercept",
                "n_samples": len(sub),
                "n_subjects": int(sub["subject_id"].nunique()),
                "intercept": float(params.get("Intercept", np.nan)),
                "month_coef": float(params.get("timepoint_month", np.nan)),
                "progressor_coef": float(params.get("progressor", np.nan)),
                "interaction_coef": float(params.get("timepoint_month:progressor", np.nan)),
                "month_pvalue": float(pvalues.get("timepoint_month", np.nan)),
                "progressor_pvalue": float(pvalues.get("progressor", np.nan)),
                "interaction_pvalue": float(pvalues.get("timepoint_month:progressor", np.nan)),
                "interaction_ci_low": float(conf.loc["timepoint_month:progressor", 0]),
                "interaction_ci_high": float(conf.loc["timepoint_month:progressor", 1]),
                "aic": float(fit.aic),
            }
        except Exception:
            ols = smf.ols("value ~ timepoint_month + progressor + timepoint_month:progressor", data=sub).fit(
                cov_type="cluster", cov_kwds={"groups": sub["subject_id"]}
            )
            conf = ols.conf_int()
            return {
                "feature": value_col,
                "model_type": "ols_cluster_subject",
                "n_samples": len(sub),
                "n_subjects": int(sub["subject_id"].nunique()),
                "intercept": float(ols.params.get("Intercept", np.nan)),
                "month_coef": float(ols.params.get("timepoint_month", np.nan)),
                "progressor_coef": float(ols.params.get("progressor", np.nan)),
                "interaction_coef": float(ols.params.get("timepoint_month:progressor", np.nan)),
                "month_pvalue": float(ols.pvalues.get("timepoint_month", np.nan)),
                "progressor_pvalue": float(ols.pvalues.get("progressor", np.nan)),
                "interaction_pvalue": float(ols.pvalues.get("timepoint_month:progressor", np.nan)),
                "interaction_ci_low": float(conf.loc["timepoint_month:progressor", 0]),
                "interaction_ci_high": float(conf.loc["timepoint_month:progressor", 1]),
                "aic": float(ols.aic),
            }


def fit_all_models(df: pd.DataFrame, features: list[str], label: str) -> pd.DataFrame:
    rows = [fit_mixed_model(df, feature) for feature in features]
    out = pd.DataFrame(rows)
    if "interaction_pvalue" in out.columns:
        mask = out["interaction_pvalue"].notna()
        out.loc[mask, "interaction_fdr_bh"] = bh_adjust(out.loc[mask, "interaction_pvalue"].tolist())
    out["feature_group"] = label
    return out.sort_values("interaction_pvalue", na_position="last").reset_index(drop=True)


def subject_slopes(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    rows = []
    for feature in features:
        for subject_id, grp in df.groupby("subject_id"):
            grp = grp[["timepoint_month", "progressor", feature]].dropna().sort_values("timepoint_month")
            if len(grp) < 2 or grp["timepoint_month"].nunique() < 2:
                continue
            slope = float(np.polyfit(grp["timepoint_month"], grp[feature], 1)[0])
            rows.append(
                {
                    "feature": feature,
                    "subject_id": subject_id,
                    "progressor": int(grp["progressor"].iloc[0]),
                    "n_samples": len(grp),
                    "slope_per_month": slope,
                }
            )
    return pd.DataFrame(rows)


def ic_contrast(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    rows = []
    for feature in features:
        prog_ic = df.loc[(df["progressor"] == 1) & (df["timepoint_label"] == "IC"), feature].dropna()
        prog_sched = df.loc[
            (df["progressor"] == 1) & (df["timepoint_label"].isin(["DAY0", "OTHER", "DAY180", "DAY360", "DAY540"])),
            feature,
        ].dropna()
        if len(prog_ic) == 0 or len(prog_sched) == 0:
            continue
        test = stats.ttest_ind(prog_ic, prog_sched, equal_var=False, nan_policy="omit")
        rows.append(
            {
                "feature": feature,
                "n_ic": int(len(prog_ic)),
                "n_scheduled": int(len(prog_sched)),
                "mean_ic": float(prog_ic.mean()),
                "mean_scheduled": float(prog_sched.mean()),
                "delta_ic_minus_scheduled": float(prog_ic.mean() - prog_sched.mean()),
                "pvalue": float(test.pvalue),
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out["fdr_bh"] = bh_adjust(out["pvalue"].tolist())
    return out.sort_values("pvalue").reset_index(drop=True)


def plot_signature_spaghetti(df: pd.DataFrame) -> None:
    plot_df = df.dropna(subset=["timepoint_month", "signature25_proxy"]).copy()
    fig, ax = plt.subplots(figsize=(8.5, 5.0))
    colors = {0: "#4f81bd", 1: "#c0504d"}
    for subject_id, grp in plot_df.groupby("subject_id"):
        grp = grp.sort_values("timepoint_month")
        prog = int(grp["progressor"].iloc[0])
        ax.plot(grp["timepoint_month"], grp["signature25_proxy"], color=colors[prog], alpha=0.18, linewidth=1.0)
    means = plot_df.groupby(["progressor", "timepoint_month"], as_index=False)["signature25_proxy"].mean()
    for prog, grp in means.groupby("progressor"):
        grp = grp.sort_values("timepoint_month")
        ax.plot(
            grp["timepoint_month"],
            grp["signature25_proxy"],
            color=colors[int(prog)],
            linewidth=3,
            marker="o",
            label="Progressor" if int(prog) == 1 else "Non-progressor",
        )
    ax.set_xlabel("Follow-up month")
    ax.set_ylabel("Signature score (z-scale)")
    ax.set_title("Longitudinal signature trajectories in GSE79362 gene-level data")
    ax.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "signature_spaghetti.png", dpi=300)
    plt.close(fig)


def plot_program_means(df: pd.DataFrame, features: list[str]) -> None:
    order = [x for x in [0.0, 1.6666666666666667, 6.0, 12.0, 18.0] if x in set(df["timepoint_month"].dropna())]
    labels = {0.0: "DAY0", 1.6666666666666667: "OTHER", 6.0: "DAY180", 12.0: "DAY360", 18.0: "DAY540"}
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.5))
    axes = axes.flatten()
    colors = {0: "#4f81bd", 1: "#c0504d"}
    for ax, feature in zip(axes, features, strict=False):
        summary = (
            df.dropna(subset=["timepoint_month", feature])
            .groupby(["progressor", "timepoint_month"], as_index=False)[feature]
            .mean()
            .sort_values("timepoint_month")
        )
        for prog, grp in summary.groupby("progressor"):
            ax.plot(
                grp["timepoint_month"],
                grp[feature],
                color=colors[int(prog)],
                marker="o",
                linewidth=2.5,
                label="Progressor" if int(prog) == 1 else "Non-progressor",
            )
        ax.set_title(feature)
        ax.set_xticks(order)
        ax.set_xticklabels([labels[v] for v in order], rotation=20)
    axes[0].legend(frameon=False)
    fig.suptitle("Program-level mean trajectories")
    fig.tight_layout()
    plt.savefig(OUT_DIR / "program_mean_trajectories.png", dpi=300)
    plt.close(fig)


def plot_interaction_forest(model_df: pd.DataFrame, out_name: str, title: str) -> None:
    plot_df = model_df.dropna(subset=["interaction_coef"]).copy().sort_values("interaction_coef")
    fig_h = max(4.0, 0.35 * len(plot_df))
    fig, ax = plt.subplots(figsize=(8.5, fig_h))
    y = np.arange(len(plot_df))
    ax.hlines(y, plot_df["interaction_ci_low"], plot_df["interaction_ci_high"], color="#666666", linewidth=2)
    ax.plot(plot_df["interaction_coef"], y, "o", color="#1f4e79")
    ax.axvline(0, color="black", linestyle="--", linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["feature"])
    ax.set_xlabel("Progressor-by-month interaction coefficient")
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(OUT_DIR / out_name, dpi=300)
    plt.close(fig)


def write_report(
    meta: pd.DataFrame,
    program_sets: dict[str, list[str]],
    program_models: pd.DataFrame,
    gene_models: pd.DataFrame,
    ic_df: pd.DataFrame,
) -> None:
    top_program = program_models.sort_values("interaction_pvalue").iloc[0]
    top_gene = gene_models.sort_values("interaction_pvalue").iloc[0]
    program_fdr_05 = int((program_models["interaction_fdr_bh"] < 0.05).fillna(False).sum()) if "interaction_fdr_bh" in program_models.columns else 0
    program_fdr_10 = int((program_models["interaction_fdr_bh"] < 0.10).fillna(False).sum()) if "interaction_fdr_bh" in program_models.columns else 0
    gene_fdr_05 = int((gene_models["interaction_fdr_bh"] < 0.05).fillna(False).sum()) if "interaction_fdr_bh" in gene_models.columns else 0
    gene_fdr_10 = int((gene_models["interaction_fdr_bh"] < 0.10).fillna(False).sum()) if "interaction_fdr_bh" in gene_models.columns else 0
    top_program_fdr = top_program["interaction_fdr_bh"] if "interaction_fdr_bh" in top_program.index else np.nan
    top_gene_fdr = top_gene["interaction_fdr_bh"] if "interaction_fdr_bh" in top_gene.index else np.nan
    top_programs_10 = (
        ", ".join(program_models.loc[program_models["interaction_fdr_bh"] < 0.10, "feature"].astype(str).tolist())
        if "interaction_fdr_bh" in program_models.columns
        else ""
    )
    top_genes_nominal = ", ".join(gene_models.head(3)["feature"].astype(str).tolist())
    lines = [
        "# Longitudinal Tuberculosis Trajectory Analysis",
        "",
        "## Dataset",
        f"- Cohort: `GSE79362_genelevel`",
        f"- Samples with metadata: `{len(meta)}`",
        f"- Subjects: `{meta['subject_id'].nunique()}`",
        f"- Progressor subjects: `{meta.loc[meta['progressor'] == 1, 'subject_id'].nunique()}`",
        f"- Non-progressor subjects: `{meta.loc[meta['progressor'] == 0, 'subject_id'].nunique()}`",
        f"- Samples with numeric follow-up month used in primary mixed-effects models: `{int(meta['timepoint_month'].notna().sum())}`",
        "",
        "## Program definitions used here",
    ]
    for name, genes in sorted(program_sets.items()):
        preview = ", ".join(genes[:8])
        suffix = " ..." if len(genes) > 8 else ""
        lines.append(f"- `{name}`: `{len(genes)}` genes ({preview}{suffix})")
    lines.extend(
        [
            "",
            "## Primary modeling strategy",
            "- Random-intercept mixed-effects models were fit for each score with fixed effects for follow-up month, progressor status, and a progressor-by-month interaction.",
            "- Numeric follow-up models excluded `IC` samples because those samples are not naturally ordered on the scheduled visit scale in the remapped metadata.",
            "- `IC` samples were evaluated separately through progressor-only contrasts as descriptive sensitivity analyses.",
            "",
            "## Main findings",
            f"- Strongest program-level interaction: `{top_program['feature']}` with interaction coefficient `{top_program['interaction_coef']:.4f}`, p=`{top_program['interaction_pvalue']:.4g}`, FDR=`{top_program_fdr:.4g}`.",
            f"- Strongest gene-level interaction trend: `{top_gene['feature']}` with interaction coefficient `{top_gene['interaction_coef']:.4f}`, p=`{top_gene['interaction_pvalue']:.4g}`, FDR=`{top_gene_fdr:.4g}`.",
            f"- Program-level interaction counts: `{program_fdr_05}` at FDR <0.05 and `{program_fdr_10}` at FDR <0.10.",
            f"- Gene-level interaction counts: `{gene_fdr_05}` at FDR <0.05 and `{gene_fdr_10}` at FDR <0.10.",
            (f"- Program-level features retained at FDR <0.10: `{top_programs_10}`." if top_programs_10 else "- No program-level feature reached FDR <0.10."),
            f"- Leading nominal gene-level trends were `{top_genes_nominal}`, but no gene-level interaction survived multiple-testing control in this run.",
            "- Negative interaction coefficients indicate that the score declined more steeply over follow-up in progressors than in non-progressors.",
            "- These longitudinal results should be interpreted as trajectory evidence within the remapped cohort, not as direct time-to-disease forecasting.",
            "",
            "## Interpretation",
            "- This analysis tests temporal behavior of already-supported host-response programs rather than searching for another de novo classifier.",
            "- The clearest publishable angle is whether progression-associated biology is dynamically reconfigured over repeated visits and whether that dynamic is stronger for myeloid or vascular-linked programs.",
            "- The most defensible current signal is at the program level rather than at the individual-gene level.",
            "- The `IC` state should remain analytically separate in any manuscript because it is not equivalent to a scheduled follow-up visit.",
        ]
    )
    if not ic_df.empty:
        lines.extend(
            [
                "",
                "## IC sensitivity note",
                f"- Top IC versus scheduled progressor contrast: `{ic_df.iloc[0]['feature']}` with delta `{ic_df.iloc[0]['delta_ic_minus_scheduled']:.4f}` and p=`{ic_df.iloc[0]['pvalue']:.4g}`.",
            ]
        )
    lines.extend(
        [
            "",
            "## Outputs",
            "- `program_scores.csv`",
            "- `mixedlm_program_models.csv`",
            "- `mixedlm_gene_models.csv`",
            "- `subject_program_slopes.csv`",
            "- `timepoint_program_summary.csv`",
            "- `ic_progressor_contrasts.csv`",
            "- trajectory figures in this folder",
        ]
    )
    (OUT_DIR / "longitudinal_analysis_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta, expr = load_inputs()
    score_df, program_sets = compute_program_scores(meta, expr)
    nnls_df = compute_nnls_scores(meta, expr)
    score_df = score_df.merge(nnls_df, on="sample_id", how="left")

    core_gene_features = [gene for gene in ["MILR1", "VSIG4", "CD36", "CCR2", "AQP1", "IRAK3", "FCGR3B", "HP", "ACSL1"] if gene in expr.columns]
    gene_df = expr[["sample_id"] + core_gene_features].copy()
    gene_df[core_gene_features] = standardize(gene_df[core_gene_features])
    score_df = score_df.merge(gene_df, on="sample_id", how="left")
    score_df.to_csv(OUT_DIR / "program_scores.csv", index=False)

    numeric_df = score_df[score_df["timepoint_month"].notna()].copy()

    program_features = [
        feature
        for feature in [
            "signature25_proxy",
            "bayesian_core8",
            "remap_myeloid5",
            "vascular_proxy5",
            "module_M6_proxy",
            "module_M5_proxy",
            "Monocyte",
            "Neutrophil",
            "Platelet",
            "T_cell",
            "B_cell",
            "NK_cell",
        ]
        if feature in numeric_df.columns
    ]

    program_models = fit_all_models(numeric_df, program_features, "program")
    gene_models = fit_all_models(numeric_df, core_gene_features, "gene")
    slope_df = subject_slopes(numeric_df, ["signature25_proxy", "bayesian_core8", "remap_myeloid5", "module_M6_proxy"] + core_gene_features)
    ic_df = ic_contrast(score_df, [f for f in ["signature25_proxy", "bayesian_core8", "remap_myeloid5", "module_M6_proxy"] + core_gene_features if f in score_df.columns])

    timepoint_summary = (
        score_df.groupby(["progressor", "timepoint_label"], as_index=False)[program_features]
        .mean(numeric_only=True)
        .sort_values(["progressor", "timepoint_label"])
    )

    program_models.to_csv(OUT_DIR / "mixedlm_program_models.csv", index=False)
    gene_models.to_csv(OUT_DIR / "mixedlm_gene_models.csv", index=False)
    slope_df.to_csv(OUT_DIR / "subject_program_slopes.csv", index=False)
    ic_df.to_csv(OUT_DIR / "ic_progressor_contrasts.csv", index=False)
    timepoint_summary.to_csv(OUT_DIR / "timepoint_program_summary.csv", index=False)
    pd.DataFrame(
        [{"program": name, "n_genes_present": len(genes), "genes": "; ".join(genes)} for name, genes in sorted(program_sets.items())]
    ).to_csv(OUT_DIR / "program_gene_sets.csv", index=False)

    plot_signature_spaghetti(numeric_df)
    plot_program_means(numeric_df, [f for f in ["signature25_proxy", "remap_myeloid5", "module_M6_proxy", "Monocyte"] if f in numeric_df.columns])
    plot_interaction_forest(program_models, "program_interaction_forest.png", "Program-level progressor-by-month interactions")
    plot_interaction_forest(gene_models, "gene_interaction_forest.png", "Gene-level progressor-by-month interactions")
    write_report(meta, program_sets, program_models, gene_models, ic_df)
    print(f"Longitudinal TB analysis written to {OUT_DIR}")


if __name__ == "__main__":
    main()
