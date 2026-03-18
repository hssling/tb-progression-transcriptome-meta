from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
META_PATH = ROOT / "data" / "processed" / "GSE79362_genelevel" / "metadata.parquet"
EXPR_PATH = ROOT / "data" / "processed" / "GSE79362_genelevel" / "expression.parquet"
SIG_PATH = ROOT / "results" / "tables" / "signature_genes.csv"
OUT_DIR = ROOT / "results" / "longitudinal_trajectory_feasibility"


def standardize_frame(df: pd.DataFrame) -> pd.DataFrame:
    return (df - df.mean()) / df.std(ddof=0).replace(0, np.nan)


def build_signature_scores(meta: pd.DataFrame, expr: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    signature_genes = pd.read_csv(SIG_PATH)["gene"].astype(str).tolist()
    present = [gene for gene in signature_genes if gene in expr.columns]
    x = expr.set_index("sample_id")[present]
    z = standardize_frame(x)
    score = z.mean(axis=1, skipna=True).rename("signature_score")
    merged = meta.merge(score, on="sample_id", how="left")
    return merged, present


def summarize_repeats(meta: pd.DataFrame) -> pd.DataFrame:
    repeat_df = (
        meta.groupby(["subject_id", "progressor"], as_index=False)
        .agg(
            n_samples=("sample_id", "size"),
            unique_timepoints=("timepoint_label", "nunique"),
            min_month=("timepoint_month", "min"),
            max_month=("timepoint_month", "max"),
        )
        .sort_values(["progressor", "n_samples", "subject_id"], ascending=[False, False, True])
    )
    repeat_df["has_repeat_samples"] = repeat_df["n_samples"] >= 2
    repeat_df["has_repeat_timepoints"] = repeat_df["unique_timepoints"] >= 2
    return repeat_df


def build_slope_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for subject_id, grp in df.groupby("subject_id"):
        grp = grp.dropna(subset=["timepoint_month", "signature_score"]).sort_values("timepoint_month")
        if len(grp) < 2 or grp["timepoint_month"].nunique() < 2:
            continue
        slope = float(np.polyfit(grp["timepoint_month"], grp["signature_score"], 1)[0])
        rows.append(
            {
                "subject_id": subject_id,
                "progressor": int(grp["progressor"].iloc[0]),
                "n_samples": len(grp),
                "min_month": float(grp["timepoint_month"].min()),
                "max_month": float(grp["timepoint_month"].max()),
                "signature_score_slope_per_month": slope,
            }
        )
    return pd.DataFrame(rows)


def make_plots(df: pd.DataFrame, timepoint_counts: pd.DataFrame) -> None:
    plt.figure(figsize=(7.0, 4.5))
    pivot = timepoint_counts.pivot(index="timepoint_label", columns="progressor_label", values="n_samples").fillna(0)
    pivot = pivot.loc[[label for label in ["DAY0", "OTHER", "DAY180", "DAY360", "DAY540", "IC"] if label in pivot.index]]
    pivot.plot(kind="bar", ax=plt.gca(), color=["#4f81bd", "#c0504d"])
    plt.ylabel("Samples")
    plt.xlabel("Timepoint label")
    plt.title("GSE79362 gene-level timepoint distribution")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "timepoint_distribution_by_progressor.png", dpi=300)
    plt.close()

    plot_df = df.dropna(subset=["signature_score"]).copy()
    plot_df["progressor_label"] = plot_df["progressor"].map({0: "Non-progressor", 1: "Progressor"})
    order = [label for label in ["DAY0", "OTHER", "DAY180", "DAY360", "DAY540", "IC"] if label in plot_df["timepoint_label"].unique()]
    fig, ax = plt.subplots(figsize=(8.0, 4.5))
    positions = np.arange(len(order))
    offsets = {"Non-progressor": -0.15, "Progressor": 0.15}
    colors = {"Non-progressor": "#4f81bd", "Progressor": "#c0504d"}
    for label in ["Non-progressor", "Progressor"]:
        series = [plot_df.loc[(plot_df["timepoint_label"] == tp) & (plot_df["progressor_label"] == label), "signature_score"].values for tp in order]
        pos = positions + offsets[label]
        bp = ax.boxplot(series, positions=pos, widths=0.25, patch_artist=True, showfliers=False)
        for patch in bp["boxes"]:
            patch.set_facecolor(colors[label])
            patch.set_alpha(0.7)
        for item in bp["medians"]:
            item.set_color("black")
    ax.set_xticks(positions)
    ax.set_xticklabels(order)
    ax.set_ylabel("Standardized signature score")
    ax.set_xlabel("Timepoint label")
    ax.set_title("Signature score by timepoint and progression status")
    ax.legend(
        handles=[
            plt.Line2D([0], [0], color=colors["Non-progressor"], lw=8),
            plt.Line2D([0], [0], color=colors["Progressor"], lw=8),
        ],
        labels=["Non-progressor", "Progressor"],
        frameon=False,
    )
    plt.tight_layout()
    plt.savefig(OUT_DIR / "signature_score_by_timepoint.png", dpi=300)
    plt.close()


def write_report(
    meta: pd.DataFrame,
    repeat_df: pd.DataFrame,
    slopes: pd.DataFrame,
    signature_df: pd.DataFrame,
    present_genes: list[str],
) -> None:
    timepoint_counts = (
        signature_df.assign(progressor_label=signature_df["progressor"].map({0: "Non-progressor", 1: "Progressor"}))
        .groupby(["timepoint_label", "progressor_label"], as_index=False)
        .agg(n_samples=("sample_id", "size"))
    )
    score_summary = (
        signature_df.groupby(["progressor", "timepoint_label"], as_index=False)
        .agg(
            n_samples=("sample_id", "size"),
            mean_signature_score=("signature_score", "mean"),
            median_signature_score=("signature_score", "median"),
        )
        .sort_values(["progressor", "timepoint_label"])
    )
    baseline_like = signature_df[signature_df["timepoint_label"].isin(["DAY0", "OTHER"])].copy()
    baseline_prog = baseline_like.loc[baseline_like["progressor"] == 1, "signature_score"]
    baseline_non = baseline_like.loc[baseline_like["progressor"] == 0, "signature_score"]
    baseline_test = stats.ttest_ind(baseline_prog, baseline_non, equal_var=False, nan_policy="omit")

    slope_test = stats.ttest_ind(
        slopes.loc[slopes["progressor"] == 1, "signature_score_slope_per_month"],
        slopes.loc[slopes["progressor"] == 0, "signature_score_slope_per_month"],
        equal_var=False,
        nan_policy="omit",
    )
    overall_corr = stats.spearmanr(signature_df["timepoint_month"], signature_df["signature_score"], nan_policy="omit")
    prog_corr = stats.spearmanr(
        signature_df.loc[signature_df["progressor"] == 1, "timepoint_month"],
        signature_df.loc[signature_df["progressor"] == 1, "signature_score"],
        nan_policy="omit",
    )
    non_corr = stats.spearmanr(
        signature_df.loc[signature_df["progressor"] == 0, "timepoint_month"],
        signature_df.loc[signature_df["progressor"] == 0, "signature_score"],
        nan_policy="omit",
    )

    lines = [
        "# Longitudinal Trajectory Feasibility Report",
        "",
        "## Recommendation",
        "The most feasible high-impact next manuscript is a longitudinal trajectory analysis centered on `GSE79362_genelevel`, with the two harmonized baseline cohorts used for external triangulation rather than forced pooled modeling.",
        "",
        "## Why this path is feasible",
        f"- `GSE79362_genelevel` contains `{len(meta)}` samples from `{meta['subject_id'].nunique()}` subjects.",
        f"- `{int((repeat_df['has_repeat_samples']).sum())}` subjects have repeat samples, including `{int(((repeat_df['has_repeat_samples']) & (repeat_df['progressor'] == 1)).sum())}` progressors and `{int(((repeat_df['has_repeat_samples']) & (repeat_df['progressor'] == 0)).sum())}` non-progressors.",
        f"- The cohort includes `{meta.loc[meta['progressor'] == 1, 'subject_id'].nunique()}` progressor subjects and `{meta.loc[meta['progressor'] == 0, 'subject_id'].nunique()}` non-progressor subjects.",
        f"- `{len(present_genes)}` of the current signature genes are already present in the remapped gene-level matrix, which supports immediate trajectory scoring without new wet-lab work.",
        "",
        "## Preliminary signal checks",
        f"- Baseline-like (`DAY0` + `OTHER`) signature-score difference between progressors and non-progressors was not significant in this quick audit (Welch p={baseline_test.pvalue:.3f}).",
        f"- Across all samples with a numeric month value, the signature score showed a modest negative correlation with follow-up month (Spearman rho={overall_corr.statistic:.3f}, p={overall_corr.pvalue:.3g}).",
        f"- The negative month-score correlation was stronger among progressors (rho={prog_corr.statistic:.3f}, p={prog_corr.pvalue:.3g}) than among non-progressors (rho={non_corr.statistic:.3f}, p={non_corr.pvalue:.3g}).",
        f"- Subject-level signature-score slopes were more negative on average in progressors than non-progressors, but this quick comparison was not yet statistically significant (Welch p={slope_test.pvalue:.3f}).",
        "",
        "## Scientific angle",
        "This opens a more novel question than another static biomarker paper: whether a progression-associated host-response program is temporally dynamic within subjects and whether repeated blood RNA measurements show different trajectories in progressors and non-progressors.",
        "",
        "## Immediate paper concept",
        "`Longitudinal dynamics of a tuberculosis progression host-response program in a prospective blood RNA-sequencing cohort`",
        "",
        "## Core analyses for the full manuscript",
        "1. Mixed-effects modeling of signature score versus follow-up month with a progressor-by-time interaction.",
        "2. Gene-level random-slope models for the strongest progression genes and for the remap-sensitive myeloid genes such as `FCGR3B`, `HP`, and `ACSL1`.",
        "3. Module-level and pathway-level trajectory analysis to test whether myeloid and vascular programs evolve differently over follow-up.",
        "4. Sensitivity analyses that separate `DAY0`, scheduled follow-up visits, and `IC` samples rather than collapsing them prematurely.",
        "5. External triangulation using `GSE107994` and `GSE193777` only as fixed-time external reference cohorts, not as longitudinal substitutes.",
        "",
        "## Important limits",
        "- The current month field is follow-up timing, not a validated exact time-to-disease measure. Any manuscript should avoid language that implies confirmed months-to-TB unless the original cohort metadata support that directly.",
        "- `IC` samples need separate handling because they are not naturally ordered with the scheduled follow-up visits in the remapped metadata.",
        "- This feasibility layer supports a longitudinal host-response paper, but not yet a definitive clinical forecasting paper.",
        "",
        "## Files generated here",
        "- `cohort_summary.csv`",
        "- `timepoint_distribution.csv`",
        "- `subject_repeat_summary.csv`",
        "- `signature_score_summary.csv`",
        "- `subject_signature_slopes.csv`",
        "- `timepoint_distribution_by_progressor.png`",
        "- `signature_score_by_timepoint.png`",
        "",
        "## Bottom line",
        "Among the currently available local datasets, the longitudinal `GSE79362_genelevel` route is the most feasible combination of novelty, biological depth, and manuscript potential. It is stronger as a dynamics-and-mechanism paper than as a new classification paper.",
    ]
    (OUT_DIR / "feasibility_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    timepoint_counts.to_csv(OUT_DIR / "timepoint_distribution.csv", index=False)
    score_summary.to_csv(OUT_DIR / "signature_score_summary.csv", index=False)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = pd.read_parquet(META_PATH).copy()
    expr = pd.read_parquet(EXPR_PATH).copy()
    signature_df, present_genes = build_signature_scores(meta, expr)
    repeat_df = summarize_repeats(signature_df)
    slopes = build_slope_table(signature_df)

    cohort_summary = pd.DataFrame(
        [
            {
                "cohort_id": "GSE79362_genelevel",
                "n_samples": len(signature_df),
                "n_subjects": signature_df["subject_id"].nunique(),
                "progressor_subjects": signature_df.loc[signature_df["progressor"] == 1, "subject_id"].nunique(),
                "nonprogressor_subjects": signature_df.loc[signature_df["progressor"] == 0, "subject_id"].nunique(),
                "subjects_with_repeat_samples": int((repeat_df["has_repeat_samples"]).sum()),
                "subjects_with_repeat_timepoints": int((repeat_df["has_repeat_timepoints"]).sum()),
                "signature_genes_present": len(present_genes),
            }
        ]
    )
    cohort_summary.to_csv(OUT_DIR / "cohort_summary.csv", index=False)
    repeat_df.to_csv(OUT_DIR / "subject_repeat_summary.csv", index=False)
    slopes.to_csv(OUT_DIR / "subject_signature_slopes.csv", index=False)

    timepoint_counts = (
        signature_df.assign(progressor_label=signature_df["progressor"].map({0: "Non-progressor", 1: "Progressor"}))
        .groupby(["timepoint_label", "progressor_label"], as_index=False)
        .agg(n_samples=("sample_id", "size"))
    )
    make_plots(signature_df, timepoint_counts)
    write_report(meta, repeat_df, slopes, signature_df, present_genes)
    print(f"Longitudinal feasibility outputs written to {OUT_DIR}")


if __name__ == "__main__":
    main()
