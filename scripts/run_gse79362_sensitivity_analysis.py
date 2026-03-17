from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import shutil

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from run_advanced_tb_analysis import (
    cohort_center,
    load_cohort,
    parse_characteristics,
    run_pca,
    shared_gene_matrix,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "advanced_analysis_gse79362_sensitivity"


@dataclass
class CohortBundle:
    cohort_id: str
    expression: pd.DataFrame
    metadata: pd.DataFrame


def load_gse79362_genelevel() -> CohortBundle:
    expr = pd.read_parquet(ROOT / "data" / "processed" / "GSE79362_genelevel" / "expression.parquet")
    meta = pd.read_parquet(ROOT / "data" / "processed" / "GSE79362_genelevel" / "metadata.parquet").copy()
    parsed = meta["characteristics"].map(parse_characteristics)
    meta["age_years"] = pd.to_numeric(parsed.map(lambda row: row.get("age")), errors="coerce")
    meta["sex"] = parsed.map(lambda row: row.get("gender"))
    meta["group"] = parsed.map(lambda row: row.get("group"))
    return CohortBundle("GSE79362", expr, meta)


def select_earliest_subject_sample(meta: pd.DataFrame) -> pd.DataFrame:
    priority = {"DAY0": 0, "OTHER": 1, "DAY180": 2, "DAY360": 3, "DAY540": 4, "IC": 5}
    ordered = meta.copy()
    ordered["tp_priority"] = ordered["timepoint_label"].map(lambda x: priority.get(str(x), 9))
    ordered = ordered.sort_values(["subject_id", "tp_priority", "sample_id"]).copy()
    return ordered.drop_duplicates("subject_id", keep="first").drop(columns=["tp_priority"])


def filter_bundle(bundle: CohortBundle, keep_meta: pd.DataFrame) -> CohortBundle:
    keep_ids = keep_meta["sample_id"].tolist()
    expr = bundle.expression[bundle.expression["sample_id"].isin(keep_ids)].copy()
    expr = expr.set_index("sample_id").loc[keep_ids].reset_index()
    return CohortBundle(bundle.cohort_id, expr, keep_meta.copy())


def compute_de(expr: pd.DataFrame, meta: pd.DataFrame, cohort_id: str) -> pd.DataFrame:
    genes = [c for c in expr.columns if c != "sample_id"]
    prog_mask = meta["progressor"].to_numpy() == 1
    non_mask = ~prog_mask
    rows = []
    for gene in genes:
        prog = pd.to_numeric(expr.loc[prog_mask, gene], errors="coerce").to_numpy(float)
        non = pd.to_numeric(expr.loc[non_mask, gene], errors="coerce").to_numpy(float)
        prog = prog[~np.isnan(prog)]
        non = non[~np.isnan(non)]
        if len(prog) < 3 or len(non) < 3:
            continue
        _, pvalue = stats.ttest_ind(prog, non, equal_var=False, nan_policy="omit")
        pooled_sd = math.sqrt((((len(prog) - 1) * np.var(prog, ddof=1)) + ((len(non) - 1) * np.var(non, ddof=1))) / max(len(prog) + len(non) - 2, 1))
        effect = 0.0 if pooled_sd == 0 else (np.mean(prog) - np.mean(non)) / pooled_sd
        log2fc = np.log2(np.mean(prog) + 1) - np.log2(np.mean(non) + 1)
        rows.append(
            {
                "cohort_id": cohort_id,
                "gene": gene,
                "effect_size": effect,
                "log2fc": log2fc,
                "pvalue": pvalue,
                "n_prog": int(prog_mask.sum()),
                "n_nonprog": int(non_mask.sum()),
            }
        )
    return pd.DataFrame(rows)


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bayesian_meta_local(de_df: pd.DataFrame, top_n: int = 30) -> pd.DataFrame:
    rows = []
    for gene, sub in de_df.groupby("gene"):
        if len(sub) < 2:
            continue
        effects = sub["effect_size"].to_numpy(float)
        variances = 1.0 / np.clip((sub["n_prog"] + sub["n_nonprog"]).to_numpy(float), 1, None)
        fixed_weights = 1.0 / variances
        fixed_mean = np.sum(fixed_weights * effects) / np.sum(fixed_weights)
        q = np.sum(fixed_weights * (effects - fixed_mean) ** 2)
        df = len(effects) - 1
        c = np.sum(fixed_weights) - np.sum(fixed_weights**2) / np.sum(fixed_weights)
        tau2 = max((q - df) / max(c, 1e-12), 0.0)
        post_var = 1.0 / np.sum(1.0 / (variances + tau2))
        post_mean = post_var * np.sum(effects / (variances + tau2))
        post_sd = math.sqrt(post_var)
        rows.append(
            {
                "gene": gene,
                "posterior_mean": post_mean,
                "posterior_sd": post_sd,
                "ci95_low": post_mean - 1.96 * post_sd,
                "ci95_high": post_mean + 1.96 * post_sd,
                "post_prob_positive": normal_cdf(post_mean / max(post_sd, 1e-12)),
                "tau2": tau2,
                "n_cohorts": len(sub),
            }
        )
    out = pd.DataFrame(rows)
    out["posterior_abs_mean"] = out["posterior_mean"].abs()
    out = out.sort_values(["post_prob_positive", "posterior_abs_mean"], ascending=[False, False]).reset_index(drop=True)
    return out.head(top_n)


def write_report(primary_overlap: int, threeway_overlap: int, subset_meta: pd.DataFrame, bayes: pd.DataFrame) -> None:
    top = bayes.head(10)
    lines = [
        "# GSE79362 Sensitivity Remap Report",
        "",
        "## Cohort remap",
        f"- Gene-level remap of GSE79362 yielded {threeway_overlap} genes overlapping the shared GSE107994/GSE193777 space.",
        f"- The original two-cohort shared-gene layer had {primary_overlap} genes.",
        f"- Subject-level sensitivity selection retained {len(subset_meta)} samples from {subset_meta['subject_id'].nunique()} subjects.",
        f"- Progressor count in the sensitivity subset: {int(subset_meta['progressor'].sum())}; non-progressor count: {int((1 - subset_meta['progressor']).sum())}.",
        "",
        "## Top Bayesian genes after adding GSE79362 sensitivity cohort",
    ]
    for row in top.itertuples(index=False):
        lines.append(f"- {row.gene}: posterior mean {row.posterior_mean:.3f}, 95% CI [{row.ci95_low:.3f}, {row.ci95_high:.3f}]")
    lines += [
        "",
        "## Interpretation",
        "- GSE79362 can be brought into the shared-gene space at the gene level by aggregating junctions to genes.",
        "- Because the accession contains repeated measurements and incident samples, the one-subject-one-sample earliest-available sensitivity subset is appropriate for exploratory triangulation, not for replacing the primary two-cohort analysis.",
    ]
    (OUT_DIR / "gse79362_sensitivity_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    b1 = load_cohort("GSE107994")
    b2 = load_cohort("GSE193777")
    b3 = load_gse79362_genelevel()
    subset_meta = select_earliest_subject_sample(b3.metadata)
    b3 = filter_bundle(b3, subset_meta)

    two_expr, _ = shared_gene_matrix([b1, b2])
    primary_overlap = two_expr.shape[1]
    expr, meta = shared_gene_matrix([b1, b2, b3])
    threeway_overlap = expr.shape[1]
    centered = cohort_center(expr, meta)
    run_pca(expr, meta, "gse79362_sensitivity_raw")
    run_pca(centered, meta, "gse79362_sensitivity_centered")
    for suffix in ["raw_scores.csv", "raw_pca.png", "centered_scores.csv", "centered_pca.png"]:
        src = ROOT / "results" / "advanced_analysis" / f"gse79362_sensitivity_{suffix}"
        if src.exists():
            shutil.copy2(src, OUT_DIR / src.name)

    base_de = pd.read_csv(ROOT / "results" / "tables" / "within_cohort_de.csv")
    gse79362_de = compute_de(b3.expression, b3.metadata, "GSE79362")
    all_de = pd.concat([base_de, gse79362_de], ignore_index=True)
    all_de = all_de[all_de["cohort_id"].isin(["GSE107994", "GSE193777", "GSE79362"])].copy()
    all_de = all_de[all_de["gene"].isin(set(expr.columns))].copy()
    all_de.to_csv(OUT_DIR / "within_cohort_de_with_gse79362.csv", index=False)
    bayes = bayesian_meta_local(all_de, top_n=30)
    bayes.to_csv(OUT_DIR / "bayesian_gene_meta_with_gse79362.csv", index=False)

    write_report(primary_overlap, threeway_overlap, subset_meta, bayes)
    print(f"GSE79362 sensitivity outputs written to {OUT_DIR}")


if __name__ == "__main__":
    main()
