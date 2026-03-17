from __future__ import annotations

from pathlib import Path
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.optimize import nnls
from scipy.spatial.distance import squareform
from sklearn.decomposition import PCA

from run_advanced_tb_analysis import cohort_center, load_cohort, shared_gene_matrix


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "omicsclaw_extensions"

CELL_MARKERS: dict[str, list[str]] = {
    "Monocyte": ["LILRB1", "CTSS", "FCGR3A", "MS4A7", "TYMP"],
    "Neutrophil": ["CXCR1", "CXCR2", "FCGR3B", "CSF3R", "CEACAM8"],
    "T_cell": ["CD3D", "CD3E", "IL7R", "LTB", "TRBC1"],
    "B_cell": ["CD79A", "MS4A1", "CD79B", "BANK1", "HLA-DRA"],
    "NK_cell": ["NKG7", "GNLY", "KLRD1", "PRF1", "CTSW"],
    "Platelet": ["PPBP", "PF4", "GNG11", "TUBB1", "SDPR"],
}


def load_shared_centered_matrix() -> tuple[pd.DataFrame, pd.DataFrame]:
    bundles = [load_cohort(cohort_id) for cohort_id in ["GSE107994", "GSE193777"]]
    expr, meta = shared_gene_matrix(bundles)
    centered = cohort_center(expr, meta)
    return centered, meta


def positive_gene_scale(expr: pd.DataFrame) -> pd.DataFrame:
    scaled = expr.copy()
    for col in scaled.columns:
        series = scaled[col]
        span = series.max() - series.min()
        if span == 0:
            scaled[col] = 0.0
        else:
            scaled[col] = (series - series.min()) / span
    return scaled


def run_nnls_deconvolution(expr: pd.DataFrame, meta: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    marker_union = sorted({gene for genes in CELL_MARKERS.values() for gene in genes if gene in expr.columns})
    expr_pos = positive_gene_scale(expr[marker_union])
    signature = pd.DataFrame(0.0, index=marker_union, columns=list(CELL_MARKERS))
    for celltype, genes in CELL_MARKERS.items():
        overlap = [gene for gene in genes if gene in marker_union]
        signature.loc[overlap, celltype] = 1.0

    coeffs = []
    for sample_idx, sample_id in enumerate(meta["sample_id"]):
        y = expr_pos.iloc[sample_idx].to_numpy(float)
        coef, _ = nnls(signature.to_numpy(float), y)
        total = coef.sum()
        if total > 0:
            coef = coef / total
        row = {
            "sample_id": sample_id,
            "cohort_id": meta.iloc[sample_idx]["cohort_id"],
            "progressor": int(meta.iloc[sample_idx]["progressor"]),
        }
        row.update({name: coef[i] for i, name in enumerate(signature.columns)})
        coeffs.append(row)
    coef_df = pd.DataFrame(coeffs)
    coef_df.to_csv(OUT_DIR / "nnls_celltype_scores.csv", index=False)

    summary_rows = []
    for celltype in signature.columns:
        prog = coef_df.loc[coef_df["progressor"] == 1, celltype]
        non = coef_df.loc[coef_df["progressor"] == 0, celltype]
        _, pval = stats.ttest_ind(prog, non, equal_var=False, nan_policy="omit")
        summary_rows.append(
            {
                "cell_type": celltype,
                "mean_progressor": prog.mean(),
                "mean_nonprogressor": non.mean(),
                "delta_progressor_minus_nonprogressor": prog.mean() - non.mean(),
                "ttest_pvalue": pval,
            }
        )
    summary_df = pd.DataFrame(summary_rows).sort_values("ttest_pvalue").reset_index(drop=True)
    summary_df.to_csv(OUT_DIR / "nnls_celltype_summary.csv", index=False)

    means = coef_df.groupby("progressor")[list(signature.columns)].mean().T
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(signature.columns))
    ax.bar(x - 0.18, means[0].to_numpy(), width=0.36, label="Non-progressor")
    ax.bar(x + 0.18, means[1].to_numpy(), width=0.36, label="Progressor")
    ax.set_xticks(x)
    ax.set_xticklabels(signature.columns, rotation=30, ha="right")
    ax.set_ylabel("Mean normalized NNLS fraction")
    ax.set_title("Immune cell-type composition scores by progressor status")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "nnls_celltype_barplot.png", dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(11, 6))
    axes = axes.flatten()
    for i, celltype in enumerate(signature.columns):
        prog = coef_df.loc[coef_df["progressor"] == 1, celltype].to_numpy()
        non = coef_df.loc[coef_df["progressor"] == 0, celltype].to_numpy()
        axes[i].boxplot([non, prog], widths=0.6)
        axes[i].set_xticklabels(["Non", "Prog"])
        axes[i].set_title(celltype)
    fig.suptitle("NNLS deconvolution scores")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "nnls_celltype_boxplots.png", dpi=220)
    plt.close(fig)
    return coef_df, summary_df


def scale_free_fit(connectivity: np.ndarray) -> float:
    k = connectivity[connectivity > 0]
    if len(k) < 10:
        return float("nan")
    hist, edges = np.histogram(k, bins=min(15, max(5, len(k) // 20)))
    centers = (edges[:-1] + edges[1:]) / 2
    mask = (hist > 0) & (centers > 0)
    if mask.sum() < 3:
        return float("nan")
    x = np.log10(centers[mask])
    y = np.log10(hist[mask] / hist[mask].sum())
    r = np.corrcoef(x, y)[0, 1]
    return float(r * r)


def run_coexpression(expr: pd.DataFrame, meta: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    top_genes = expr.var(axis=0).sort_values(ascending=False).head(3000).index.tolist()
    sub_expr = expr[top_genes]
    corr = sub_expr.corr(method="spearman").clip(lower=0)
    np.fill_diagonal(corr.values, 0.0)

    soft_rows = []
    best_power = 6
    best_score = -1.0
    for power in range(1, 9):
        adjacency = corr.pow(power)
        connectivity = adjacency.sum(axis=0).to_numpy()
        fit = scale_free_fit(connectivity)
        soft_rows.append({"power": power, "scale_free_r2": fit, "mean_connectivity": connectivity.mean()})
        if not math.isnan(fit) and fit > best_score:
            best_score = fit
            best_power = power
    pd.DataFrame(soft_rows).to_csv(OUT_DIR / "coexpression_soft_threshold.csv", index=False)

    adjacency = corr.pow(best_power)
    distance = 1 - corr
    np.fill_diagonal(distance.values, 0.0)
    condensed = squareform(distance.to_numpy(), checks=False)
    tree = linkage(condensed, method="average")
    raw_labels = fcluster(tree, t=7, criterion="maxclust")
    assignments = pd.DataFrame({"gene": top_genes, "raw_module": raw_labels})
    module_sizes = assignments["raw_module"].value_counts().to_dict()
    assignments["module"] = assignments["raw_module"].map(
        lambda m: f"M{m}" if module_sizes.get(m, 0) >= 25 else "gray"
    )
    assignments = assignments.loc[:, ["gene", "module"]].sort_values(["module", "gene"]).reset_index(drop=True)
    assignments.to_csv(OUT_DIR / "coexpression_module_assignments.csv", index=False)

    bayes_genes = pd.read_csv(ROOT / "results" / "advanced_analysis" / "bayesian_gene_meta.csv").head(30)["gene"].tolist()
    eigengene_rows = []
    summary_rows = []
    hub_rows = []
    overlap_rows = []
    for module in sorted(assignments["module"].unique()):
        if module == "gray":
            continue
        genes = assignments.loc[assignments["module"] == module, "gene"].tolist()
        mod_expr = sub_expr[genes]
        pc1 = PCA(n_components=1, random_state=42).fit_transform(mod_expr.to_numpy(float))[:, 0]
        prog = pc1[meta["progressor"].to_numpy() == 1]
        non = pc1[meta["progressor"].to_numpy() == 0]
        _, pval = stats.ttest_ind(prog, non, equal_var=False, nan_policy="omit")
        for sample_id, cohort_id, progressor, score in zip(meta["sample_id"], meta["cohort_id"], meta["progressor"], pc1, strict=False):
            eigengene_rows.append(
                {
                    "sample_id": sample_id,
                    "cohort_id": cohort_id,
                    "progressor": int(progressor),
                    "module": module,
                    "eigengene": score,
                }
            )
        summary_rows.append(
            {
                "module": module,
                "n_genes": len(genes),
                "mean_progressor": float(np.mean(prog)),
                "mean_nonprogressor": float(np.mean(non)),
                "delta_progressor_minus_nonprogressor": float(np.mean(prog) - np.mean(non)),
                "ttest_pvalue": float(pval),
            }
        )
        overlap = sorted(set(genes) & set(bayes_genes))
        overlap_rows.append(
            {
                "module": module,
                "n_signature_overlap": len(overlap),
                "signature_genes": "; ".join(overlap),
            }
        )
        intramod = adjacency.loc[genes, genes].sum(axis=1).sort_values(ascending=False)
        for gene, k in intramod.head(10).items():
            hub_rows.append({"module": module, "gene": gene, "intramodular_connectivity": float(k)})

    eigengene_df = pd.DataFrame(eigengene_rows)
    summary_df = pd.DataFrame(summary_rows).sort_values("ttest_pvalue").reset_index(drop=True)
    hub_df = pd.DataFrame(hub_rows)
    overlap_df = pd.DataFrame(overlap_rows)
    eigengene_df.to_csv(OUT_DIR / "coexpression_module_eigengenes.csv", index=False)
    summary_df.to_csv(OUT_DIR / "coexpression_module_summary.csv", index=False)
    hub_df.to_csv(OUT_DIR / "coexpression_hub_genes.csv", index=False)
    overlap_df.to_csv(OUT_DIR / "coexpression_module_signature_overlap.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ordered = summary_df.sort_values("delta_progressor_minus_nonprogressor", ascending=True)
    colors = ["#b2182b" if x > 0 else "#2166ac" for x in ordered["delta_progressor_minus_nonprogressor"]]
    ax.barh(ordered["module"], ordered["delta_progressor_minus_nonprogressor"], color=colors)
    ax.set_xlabel("Progressor minus non-progressor eigengene mean")
    ax.set_ylabel("Module")
    ax.set_title(f"Module-trait association summary (soft power={best_power})")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "coexpression_module_trait_barplot.png", dpi=220)
    plt.close(fig)

    top_modules = summary_df.head(4)["module"].tolist()
    plot_df = eigengene_df[eigengene_df["module"].isin(top_modules)].copy()
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    axes = axes.flatten()
    for i, module in enumerate(top_modules):
        prog = plot_df[(plot_df["module"] == module) & (plot_df["progressor"] == 1)]["eigengene"].to_numpy()
        non = plot_df[(plot_df["module"] == module) & (plot_df["progressor"] == 0)]["eigengene"].to_numpy()
        axes[i].boxplot([non, prog], widths=0.6)
        axes[i].set_xticklabels(["Non", "Prog"])
        axes[i].set_title(module)
    fig.suptitle("Top coexpression module eigengenes by progressor status")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "coexpression_module_boxplots.png", dpi=220)
    plt.close(fig)
    return assignments, summary_df, hub_df


def build_literature_note() -> None:
    lines = [
        "# OmicsClaw-Informed Value Additions",
        "",
        "## Rationale",
        "This extension layer was motivated by OmicsClaw bulk-RNA resources for deconvolution, coexpression, enrichment, and literature support.",
        "The present repository already contained pathway enrichment and the new Bayesian/PCA/factor analysis layer, so the main additive analyses were deconvolution and coexpression.",
        "",
        "## Cohorts worth auditing next",
        "- GSE79362: prospectively validated adolescent risk-signature cohort and still the highest-value target for full shared-gene remapping.",
        "- GSE107993: paired Leicester non-progressor companion dataset from the same phenotypic heterogeneity study and potentially useful for expansion once harmonization details are checked carefully.",
        "- GSE117435: single-cell supportive resource that may help interpret monocyte-T-cell interface biology, but not a direct replacement for bulk progression validation.",
        "",
        "## Why these additions matter",
        "- Deconvolution helps test whether the progression signal partly reflects shifts in myeloid and lymphoid composition.",
        "- Coexpression modules help move the interpretation from isolated genes to coordinated biological programs.",
        "- Literature-led cohort expansion is the main requirement for stronger generalization claims.",
    ]
    (OUT_DIR / "omicsclaw_literature_note.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_summary_report(cell_summary: pd.DataFrame, module_summary: pd.DataFrame, hub_df: pd.DataFrame) -> None:
    top_cell = cell_summary.iloc[0]
    top_mod = module_summary.iloc[0]
    top_hubs = ", ".join(hub_df[hub_df["module"] == top_mod["module"]].head(5)["gene"].tolist())
    overlap_df = pd.read_csv(OUT_DIR / "coexpression_module_signature_overlap.csv")
    overlap_row = overlap_df[overlap_df["module"] == top_mod["module"]]
    overlap_text = ""
    if not overlap_row.empty:
        overlap_text = overlap_row.iloc[0]["signature_genes"]
    lines = [
        "# OmicsClaw Extension Report",
        "",
        "## Deconvolution",
        f"- The most progressor-associated NNLS cell-type score was {top_cell['cell_type']} with delta {top_cell['delta_progressor_minus_nonprogressor']:.3f} and p={top_cell['ttest_pvalue']:.3e}.",
        "- These estimates should be interpreted as marker-based composition proxies rather than absolute leukocyte fractions.",
        "",
        "## Coexpression",
        f"- The strongest module-trait signal was {top_mod['module']} with {int(top_mod['n_genes'])} genes, delta {top_mod['delta_progressor_minus_nonprogressor']:.3f}, and p={top_mod['ttest_pvalue']:.3e}.",
        f"- Leading hub genes in {top_mod['module']} were {top_hubs}.",
        f"- Top-module overlap with the Bayesian signature: {overlap_text if overlap_text else 'none among the current top 30 Bayesian genes'}.",
        "- The module results are intended as WGCNA-style program summaries, not as formal causal network estimates.",
        "",
        "## Integration with existing advanced analysis",
        "- The deconvolution and coexpression layers are consistent with the existing interpretation that progression is a coordinated host-response state involving myeloid regulation and tissue-remodeling biology.",
        "- These outputs provide stronger biological context for a future expanded manuscript, especially if additional cohorts can be harmonized into the shared-gene space.",
    ]
    (OUT_DIR / "omicsclaw_extension_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    expr, meta = load_shared_centered_matrix()
    _, cell_summary = run_nnls_deconvolution(expr, meta)
    _, module_summary, hub_df = run_coexpression(expr, meta)
    build_literature_note()
    build_summary_report(cell_summary, module_summary, hub_df)
    print(f"OmicsClaw-style extension outputs written to {OUT_DIR}")


if __name__ == "__main__":
    main()
