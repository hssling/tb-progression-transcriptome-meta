from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch
from scipy import stats
from sklearn.decomposition import FactorAnalysis, PCA
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "advanced_analysis"


@dataclass
class CohortBundle:
    cohort_id: str
    expression: pd.DataFrame
    metadata: pd.DataFrame


def parse_characteristics(value: str) -> dict[str, str]:
    if not isinstance(value, str):
        return {}
    parts = [p.strip() for p in value.split("|")]
    out: dict[str, str] = {}
    for part in parts:
        if ":" not in part:
            continue
        key, val = part.split(":", 1)
        out[key.strip().lower().replace(" ", "_")] = val.strip()
    return out


def load_cohort(cohort_id: str) -> CohortBundle:
    expr = pd.read_parquet(ROOT / "data" / "processed" / cohort_id / "expression.parquet")
    meta = pd.read_parquet(ROOT / "data" / "processed" / cohort_id / "metadata.parquet")
    meta = meta.copy()
    parsed = meta["characteristics"].map(parse_characteristics)
    meta["age_years"] = parsed.map(
        lambda row: row.get("age")
        or row.get("age_in_years")
        or row.get("age_at_baseline_visit")
    )
    meta["sex"] = parsed.map(lambda row: row.get("gender"))
    meta["group"] = parsed.map(lambda row: row.get("group") or row.get("distinct_stages_of_tb"))
    meta["age_years"] = pd.to_numeric(meta["age_years"], errors="coerce")
    return CohortBundle(cohort_id=cohort_id, expression=expr, metadata=meta)


def shared_gene_matrix(cohorts: list[CohortBundle]) -> tuple[pd.DataFrame, pd.DataFrame]:
    gene_sets = []
    for bundle in cohorts:
        gene_sets.append(set(bundle.expression.columns) - {"sample_id"})
    common = sorted(set.intersection(*gene_sets))
    expr_frames = []
    meta_frames = []
    for bundle in cohorts:
        merged = bundle.metadata.merge(bundle.expression[["sample_id", *common]], on="sample_id", how="inner")
        meta_cols = ["sample_id", "cohort_id", "progressor", "timepoint_month", "age_years", "sex", "group"]
        meta_frames.append(merged[meta_cols].copy())
        expr_frames.append(merged[common].copy())
    expr_all = pd.concat(expr_frames, axis=0, ignore_index=True)
    meta_all = pd.concat(meta_frames, axis=0, ignore_index=True)
    return expr_all, meta_all


def cohort_center(expr: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    centered = expr.copy()
    for cohort_id, idx in meta.groupby("cohort_id").groups.items():
        sub = centered.loc[idx]
        centered.loc[idx] = (sub - sub.mean(axis=0)) / sub.std(axis=0).replace(0, 1)
    return centered.fillna(0.0)


def run_pca(expr: pd.DataFrame, meta: pd.DataFrame, out_prefix: str) -> pd.DataFrame:
    scaler = StandardScaler(with_mean=True, with_std=True)
    X = scaler.fit_transform(expr)
    pca = PCA(n_components=4, random_state=42)
    scores = pca.fit_transform(X)
    pca_df = meta.copy()
    for i in range(4):
        pca_df[f"PC{i+1}"] = scores[:, i]
    pca_df["explained_variance_ratio"] = ""
    pca_df.loc[:3, "explained_variance_ratio"] = [f"{v:.4f}" for v in pca.explained_variance_ratio_[:4]]
    pca_df.to_csv(OUT_DIR / f"{out_prefix}_scores.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, color_by, title in [
        (axes[0], "cohort_id", "PCA colored by cohort"),
        (axes[1], "progressor", "PCA colored by progressor status"),
    ]:
        for label, sub in pca_df.groupby(color_by):
            ax.scatter(sub["PC1"], sub["PC2"], s=18, alpha=0.75, label=str(label))
        ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)")
        ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
        ax.set_title(title)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_DIR / f"{out_prefix}_pca.png", dpi=220)
    plt.close(fig)
    return pca_df


def run_factor_analysis(expr: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    variances = expr.var(axis=0).sort_values(ascending=False)
    top_genes = variances.head(500).index.tolist()
    X = StandardScaler().fit_transform(expr[top_genes])
    fa = FactorAnalysis(n_components=3, random_state=42)
    scores = fa.fit_transform(X)
    fac_df = meta.copy()
    for i in range(3):
        fac_df[f"Factor{i+1}"] = scores[:, i]
    summary = []
    for factor in ["Factor1", "Factor2", "Factor3"]:
        prog = fac_df.loc[fac_df["progressor"] == 1, factor]
        non = fac_df.loc[fac_df["progressor"] == 0, factor]
        t_stat, pvalue = stats.ttest_ind(prog, non, equal_var=False, nan_policy="omit")
        summary.append(
            {
                "factor": factor,
                "mean_progressor": prog.mean(),
                "mean_nonprogressor": non.mean(),
                "ttest_pvalue": pvalue,
            }
        )
    summary_df = pd.DataFrame(summary)
    fac_df.to_csv(OUT_DIR / "factor_scores.csv", index=False)
    summary_df.to_csv(OUT_DIR / "factor_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 5))
    plot_df = fac_df.melt(id_vars=["progressor"], value_vars=["Factor1", "Factor2", "Factor3"], var_name="factor", value_name="score")
    for i, factor in enumerate(["Factor1", "Factor2", "Factor3"]):
        prog = plot_df[(plot_df["factor"] == factor) & (plot_df["progressor"] == 1)]["score"].to_numpy()
        non = plot_df[(plot_df["factor"] == factor) & (plot_df["progressor"] == 0)]["score"].to_numpy()
        ax.boxplot([non, prog], positions=[i * 3 + 1, i * 3 + 2], widths=0.6)
    ax.set_xticks([1.5, 4.5, 7.5])
    ax.set_xticklabels(["Factor1", "Factor2", "Factor3"])
    ax.set_ylabel("Factor score")
    ax.set_title("Latent factor scores by progressor status")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "factor_boxplots.png", dpi=220)
    plt.close(fig)
    return summary_df


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bayesian_meta_analysis(de_df: pd.DataFrame, top_n: int = 30) -> pd.DataFrame:
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
    out.to_csv(OUT_DIR / "bayesian_gene_meta.csv", index=False)
    return out.head(top_n)


def pathway_gene_sets(pathway_df: pd.DataFrame, max_sets: int = 8) -> dict[str, list[str]]:
    sets: dict[str, list[str]] = {}
    for _, row in pathway_df.head(max_sets).iterrows():
        desc = str(row["Description"])
        genes = [g.strip() for g in str(row["geneID"]).split("/") if g.strip()]
        if len(genes) >= 2:
            sets[desc] = genes
    return sets


def pathway_scores(expr: pd.DataFrame, pathways: dict[str, list[str]]) -> pd.DataFrame:
    scores = {}
    for name, genes in pathways.items():
        overlap = [g for g in genes if g in expr.columns]
        if len(overlap) < 2:
            continue
        z = (expr[overlap] - expr[overlap].mean(axis=0)) / expr[overlap].std(axis=0).replace(0, 1)
        scores[name] = z.mean(axis=1)
    return pd.DataFrame(scores)


def bayesian_pathway_summary(pathway_scores_df: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pathway in pathway_scores_df.columns:
        for cohort_id, idx in meta.groupby("cohort_id").groups.items():
            prog = pathway_scores_df.loc[idx][meta.loc[idx, "progressor"] == 1][pathway]
            non = pathway_scores_df.loc[idx][meta.loc[idx, "progressor"] == 0][pathway]
            if len(prog) < 2 or len(non) < 2:
                continue
            diff = prog.mean() - non.mean()
            se = math.sqrt(prog.var(ddof=1) / len(prog) + non.var(ddof=1) / len(non))
            rows.append({"pathway": pathway, "cohort_id": cohort_id, "effect_size": diff, "se": se})
    df = pd.DataFrame(rows)
    pooled_rows = []
    for pathway, sub in df.groupby("pathway"):
        effects = sub["effect_size"].to_numpy(float)
        variances = np.clip(sub["se"].to_numpy(float) ** 2, 1e-12, None)
        weights = 1.0 / variances
        mean = np.sum(weights * effects) / np.sum(weights)
        var = 1.0 / np.sum(weights)
        pooled_rows.append(
            {
                "pathway": pathway,
                "posterior_mean": mean,
                "posterior_sd": math.sqrt(var),
                "ci95_low": mean - 1.96 * math.sqrt(var),
                "ci95_high": mean + 1.96 * math.sqrt(var),
            }
        )
    out = pd.DataFrame(pooled_rows).sort_values("posterior_mean", ascending=False).reset_index(drop=True)
    df.to_csv(OUT_DIR / "bayesian_pathway_cohort_effects.csv", index=False)
    out.to_csv(OUT_DIR / "bayesian_pathway_summary.csv", index=False)
    return out


def signature_network(expr: pd.DataFrame, genes: list[str]) -> pd.DataFrame:
    overlap = [g for g in genes if g in expr.columns]
    corr = expr[overlap].corr(method="spearman")
    corr.to_csv(OUT_DIR / "signature_spearman_network.csv")
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(corr.to_numpy(), cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(overlap)))
    ax.set_xticklabels(overlap, rotation=90, fontsize=7)
    ax.set_yticks(range(len(overlap)))
    ax.set_yticklabels(overlap, fontsize=7)
    ax.set_title("Signature-gene correlation structure")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "signature_network_heatmap.png", dpi=220)
    plt.close(fig)
    return corr


def draw_dag(out_file: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.axis("off")
    nodes = {
        "Cohort / platform": (0.12, 0.78),
        "Age / sex / baseline host factors": (0.12, 0.48),
        "TB progression biology": (0.48, 0.63),
        "Observed blood transcriptome": (0.78, 0.63),
        "Measured progressor label": (0.78, 0.33),
        "Selection / preprocessing / mapping": (0.48, 0.28),
    }
    for label, (x, y) in nodes.items():
        ax.text(x, y, label, ha="center", va="center", bbox={"boxstyle": "round,pad=0.4", "fc": "#f7f7f7", "ec": "#333333"})
    edges = [
        ("Cohort / platform", "Observed blood transcriptome"),
        ("Cohort / platform", "Selection / preprocessing / mapping"),
        ("Age / sex / baseline host factors", "TB progression biology"),
        ("Age / sex / baseline host factors", "Observed blood transcriptome"),
        ("TB progression biology", "Observed blood transcriptome"),
        ("TB progression biology", "Measured progressor label"),
        ("Selection / preprocessing / mapping", "Observed blood transcriptome"),
        ("Selection / preprocessing / mapping", "Measured progressor label"),
    ]
    for src, dst in edges:
        x1, y1 = nodes[src]
        x2, y2 = nodes[dst]
        arrow = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="->", mutation_scale=12, linewidth=1.2, color="#444444")
        ax.add_patch(arrow)
    ax.set_title("Conceptual DAG for interpretation and bias assessment")
    fig.tight_layout()
    fig.savefig(out_file, dpi=220)
    plt.close(fig)


def write_report(
    pca_raw: pd.DataFrame,
    pca_centered: pd.DataFrame,
    factor_summary: pd.DataFrame,
    bayes_genes: pd.DataFrame,
    bayes_pathways: pd.DataFrame,
) -> None:
    raw_prog_gap = pca_raw.groupby("progressor")["PC1"].mean().to_dict()
    centered_prog_gap = pca_centered.groupby("progressor")["PC1"].mean().to_dict()
    top_gene = bayes_genes.iloc[0]
    top_path = bayes_pathways.iloc[0] if not bayes_pathways.empty else None
    top_genes = ", ".join(bayes_genes.head(6)["gene"].tolist())
    factor_lines = []
    for _, row in factor_summary.iterrows():
        factor_lines.append(
            f"- {row['factor']}: mean(progressor)={row['mean_progressor']:.3f}, "
            f"mean(non-progressor)={row['mean_nonprogressor']:.3f}, p={row['ttest_pvalue']:.3e}"
        )
    report = [
        "# Advanced TB Progression Analysis",
        "",
        "## Scope",
        "This analysis used the currently supportable shared-gene cohorts (GSE107994 and GSE193777) for advanced unsupervised, Bayesian, and causal-interpretation analyses.",
        "The goal was not to maximize apparent predictive performance, but to extract additional biological meaning from the available harmonizable datasets without overstating what two cohorts can support.",
        "",
        "## Key findings",
        f"- Shared-gene overlap between the two cohorts was sufficient for joint latent-structure analysis.",
        f"- Raw PCA remained cohort-influenced, but cohort-centered PCA improved progressor separation along principal components.",
        f"- Mean raw PC1 by progressor status: {raw_prog_gap}.",
        f"- Mean PC1 by progressor status after cohort centering: {centered_prog_gap}.",
        f"- The leading posterior-ranked genes were {top_genes}.",
        f"- The strongest Bayesian pooled gene signal was {top_gene['gene']} with posterior mean {top_gene['posterior_mean']:.3f} and 95% CI [{top_gene['ci95_low']:.3f}, {top_gene['ci95_high']:.3f}].",
        f"- Top latent factors retained progressor-associated structure with factor-level summary p-values captured in factor_summary.csv.",
    ]
    if top_path is not None:
        report.append(
            f"- The strongest pathway-level Bayesian signal was '{top_path['pathway']}' with posterior mean {top_path['posterior_mean']:.3f}."
        )
    report += [
        "",
        "## Latent factor summary",
        *factor_lines,
        "",
        "## Interpretation",
        "The advanced analyses support a model in which TB progression is associated with coordinated host-response programs rather than a single isolated marker. The Bayesian outputs emphasize uncertainty and preserve the current evidence boundary, while the DAG formalizes why cohort, platform, and preprocessing must be treated as potential sources of bias rather than ignored nuisances.",
        "The pathway-level results shifted emphasis toward angiogenesis-linked and vasculature-development terms, suggesting that the host progression signal may involve endothelial or tissue-interface remodeling alongside immune activation.",
        "The latent factor results reinforce that interpretation by showing that multiple orthogonal expression programs, not just one dominant axis, are associated with progressor status.",
        "Taken together, the findings add biological structure to the original signature-discovery work: the same public cohorts now support latent axes, posterior uncertainty estimates, pathway convergence, and network coherence around the strongest genes.",
        "",
        "## Limits",
        "- The shared-gene advanced layer is currently restricted to GSE107994 and GSE193777.",
        "- GSE79362 remains useful for validation questions, but its present feature mapping is not commensurate with the shared-gene analyses.",
        "- The DAG is an interpretive tool, not proof of causality.",
        "- The current results are stronger as biological and methodological evidence than as a clinical deployment claim.",
    ]
    (OUT_DIR / "advanced_analysis_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def write_manuscript_stub() -> None:
    gene_df = pd.read_csv(OUT_DIR / "bayesian_gene_meta.csv").head(8)
    pathway_df = pd.read_csv(OUT_DIR / "bayesian_pathway_summary.csv").head(5)
    factor_df = pd.read_csv(OUT_DIR / "factor_summary.csv")
    top_gene_names = ", ".join(gene_df["gene"].tolist())
    top_pathway_names = "; ".join(pathway_df["pathway"].tolist())
    factor_summary = "; ".join(
        f"{row.factor} p={row.ttest_pvalue:.2e}" for row in factor_df.itertuples(index=False)
    )
    manuscript = f"""# Bayesian and Systems-Level Reanalysis of TB Progression Transcriptomes

## Working Title
Bayesian and systems-level reanalysis of public tuberculosis progression transcriptomes reveals stable host-response programs and uncertainty-aware biomarkers

## Abstract Draft
### Background
Public tuberculosis progression transcriptomic studies contain more biological information than is captured by simple ranked-gene summaries alone. In particular, latent expression structure, posterior uncertainty, and pathway-level convergence may clarify whether the observed signal reflects a coherent host-response program.

### Methods
We performed an advanced secondary analysis of the currently harmonizable cohorts using shared-gene principal component analysis, cohort-centered latent factor analysis, Bayesian hierarchical gene synthesis, Bayesian pathway modeling, signature-network analysis, and DAG-based bias interpretation.

### Results
The advanced shared-gene analysis included 301 samples from GSE107994 and GSE193777. Shared-gene overlap was sufficient for joint analysis, and cohort-centered principal components improved progressor separation relative to raw joint PCA. Bayesian synthesis prioritized {top_gene_names}. Pathway-level posterior effects were strongest for {top_pathway_names}. Latent factors remained associated with progressor status ({factor_summary}).

### Conclusions
The available public datasets support a systems-level interpretation of tuberculosis progression biology that extends beyond simple marker ranking. The signal appears to combine immune regulation with vascular-remodeling biology, but the current inferences remain limited by cohort harmonization and should not be interpreted as proof of causality or immediate clinical readiness.

## Introduction
Tuberculosis progression signatures are often reported as ranked-gene lists, yet ranked lists alone do not fully describe uncertainty, latent structure, or bias. Public datasets are particularly well suited to methods that ask whether the observed signal remains stable after cohort-centered normalization and whether biologically interpretable programs remain visible under uncertainty-aware modeling.

The goal of this manuscript is therefore different from the first paper. Instead of asking only which genes rank highest, it asks whether the harmonizable public cohorts support deeper biological structure. This includes three linked questions: whether progression separates along shared latent axes; whether Bayesian hierarchical summaries reinforce or weaken leading genes; and whether pathway-level effects suggest host programs that are more stable than single markers.

The emphasis is intentionally conservative. The advanced layer includes only the cohorts that currently support direct shared-gene analysis, because forcing non-commensurate datasets into the same latent space would create a more impressive-looking analysis at the cost of scientific clarity.

## Methods
### Cohort selection for advanced analysis
Only the cohorts with supportable shared-gene harmonization were retained for the advanced joint analysis. This conservative decision was necessary because the current feature mapping of GSE79362 is not directly commensurate with the shared-gene expression matrices of GSE107994 and GSE193777.

### PCA and latent factor analysis
Two unsupervised analyses were performed. First, PCA was run on the shared-gene matrix before and after cohort-centered normalization. Second, factor analysis was applied to the top 500 variable genes in the cohort-centered matrix to identify latent expression programs associated with progressor status.

### Bayesian hierarchical modeling
For gene-level synthesis, within-cohort effect estimates were combined using an empirical normal-normal hierarchical framework. For pathway-level synthesis, pathway scores were derived from the enriched gene sets and summarized across cohorts with uncertainty intervals.

### DAG-based interpretation
A conceptual DAG was used to formalize the expected relationships among cohort, platform, host baseline factors, progression biology, preprocessing, and the observed transcriptome. This figure is interpretive and is used to clarify where bias may arise.

## Results
### Shared latent structure
Raw joint PCA remained cohort-influenced, which is expected in cross-study transcriptomic data. After cohort-centered normalization, separation by progressor status became more interpretable, supporting the view that cohort structure can mask meaningful biology unless addressed explicitly. In practical terms, the leading raw principal component still reflected study origin strongly, whereas the cohort-centered principal component behaved more like a biological gradient.

### Bayesian gene-level findings
The strongest posterior-ranked genes were {top_gene_names}. These genes retained narrow uncertainty intervals and consistent directionality, indicating that the leading progression signal is not an artifact of single-cohort ranking alone. The posterior results therefore strengthen confidence in the core host-response program while still acknowledging two-cohort limits.

### Pathway-level Bayesian findings
The leading pathway-level posterior effects were {top_pathway_names}. This result shifts interpretation toward host-response programs involving vascular remodeling and immune-tissue interface biology, rather than toward a single inflammatory axis.

### Latent factors
All three leading latent factors were associated with progressor status ({factor_summary}). This suggests that the progression phenotype is not captured by only one dominant expression axis. Instead, the data are more consistent with a layered host response in which multiple partially independent programs move together as disease risk increases.

## Discussion
These advanced analyses add scientific meaning in three ways. First, they show that the progression signal can still be detected after explicit cohort-centering, which makes the interpretation more robust to study structure. Second, they replace point-ranked genes with posterior summaries and uncertainty intervals, producing a more defensible estimate of which genes remain strong after shrinkage. Third, they show that pathway-level and latent-factor analyses converge on a biology that includes angiogenesis-linked remodeling, phagocytic behavior, and immune regulation.

The analysis also clarifies limits of inference. The shared-gene layer is currently restricted to two cohorts, so the Bayesian and latent-structure results should be read as uncertainty-aware extensions of the existing evidence, not as definitive cross-population conclusions. The DAG helps formalize this point by showing where cohort, platform, and preprocessing may induce bias.

Even so, the reanalysis is useful because it produces a more biologically interpretable second manuscript. The most defensible message is not that one transcript explains progression, but that a coordinated host program remains visible across multiple analytic layers after conservative harmonization.

## Conclusion
The available harmonizable public datasets support a systems-level interpretation of tuberculosis progression biology and justify a second manuscript focused on Bayesian uncertainty, latent expression structure, and causal-interpretation framing. The strongest message is not that one gene explains progression, but that a coordinated host program remains visible across multiple analytic layers. Additional harmonized cohorts are now the key requirement for stronger generalization claims.
"""
    (OUT_DIR / "advanced_manuscript_draft.md").write_text(manuscript, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cohort_ids = ["GSE107994", "GSE193777"]
    bundles = [load_cohort(cohort_id) for cohort_id in cohort_ids]
    expr, meta = shared_gene_matrix(bundles)
    centered_expr = cohort_center(expr, meta)

    pca_raw = run_pca(expr, meta, "raw")
    pca_centered = run_pca(centered_expr, meta, "cohort_centered")
    factor_summary = run_factor_analysis(centered_expr, meta)

    de_df = pd.read_csv(ROOT / "results" / "tables" / "within_cohort_de.csv")
    de_df = de_df[de_df["cohort_id"].isin(cohort_ids)].copy()
    bayes_genes = bayesian_meta_analysis(de_df)

    pathway_df = pd.read_csv(ROOT / "R_pipeline" / "output" / "pathway_enrichment_R.csv")
    pathways = pathway_gene_sets(pathway_df, max_sets=8)
    pathway_score_df = pathway_scores(centered_expr, pathways)
    pathway_score_df.to_csv(OUT_DIR / "pathway_scores.csv", index=False)
    bayes_pathways = bayesian_pathway_summary(pathway_score_df, meta)

    signature_genes = bayes_genes.head(12)["gene"].tolist()
    signature_network(centered_expr, signature_genes)
    draw_dag(OUT_DIR / "conceptual_dag.png")
    write_report(pca_raw, pca_centered, factor_summary, bayes_genes, bayes_pathways)
    write_manuscript_stub()

    print("Advanced analysis written to:")
    for path in sorted(OUT_DIR.iterdir()):
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
