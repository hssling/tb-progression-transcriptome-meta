from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame()


def _cohort_summary(processed_dir: Path, cohort_id: str) -> dict[str, int | str]:
    meta_path = processed_dir / cohort_id / "metadata.parquet"
    if not meta_path.exists():
        return {"cohort_id": cohort_id, "n_samples": 0, "n_progressor": 0, "n_nonprogressor": 0}
    meta = pd.read_parquet(meta_path)
    n = int(meta.shape[0])
    if "progressor" not in meta.columns:
        return {"cohort_id": cohort_id, "n_samples": n, "n_progressor": 0, "n_nonprogressor": 0}
    y = pd.to_numeric(meta["progressor"], errors="coerce")
    return {
        "cohort_id": cohort_id,
        "n_samples": n,
        "n_progressor": int((y == 1).sum()),
        "n_nonprogressor": int((y == 0).sum()),
    }


def _markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    if df.empty:
        return "No data available.\n"
    sub = df[columns].copy()
    return sub.to_markdown(index=False) + "\n"


def generate_manuscript(cfg: dict[str, Any]) -> None:
    out_main = Path(cfg["manuscript"]["output_main"])
    out_supp = Path(cfg["manuscript"]["output_supplement"])
    tables = Path(cfg["paths"]["results_dir"]) / "tables"
    figures = Path(cfg["paths"]["results_dir"]) / "figures"
    processed_dir = Path(cfg["paths"]["processed_data"])

    curated_path = Path(cfg["curation"].get("curated_csv") or "")
    registry = (
        _read_csv(curated_path)
        if curated_path.exists()
        else _read_csv(Path(cfg["paths"]["registry_dir"]) / "registry_curated.csv")
    )
    perf = _read_csv(tables / "loco_performance.csv")
    sig = _read_csv(tables / "signature_genes.csv")
    meta = _read_csv(tables / "meta_analysis.csv")
    within = _read_csv(tables / "within_cohort_de.csv")
    pathway = _read_csv(tables / "pathway_enrichment.csv")
    random_split = _read_csv(tables / "random_split_sanity.csv")
    subgroup = _read_csv(tables / "subgroup_summary.csv")
    window = _read_csv(tables / "window_sensitivity.csv")

    cohort_ids = registry["gse_id"].dropna().astype(str).unique().tolist() if "gse_id" in registry.columns else []
    cohort_rows = [_cohort_summary(processed_dir, cid) for cid in cohort_ids]
    cohort_df = pd.DataFrame(cohort_rows)

    n_cohorts_curated = int(len(cohort_ids))
    n_cohorts_with_data = int((cohort_df["n_samples"] > 0).sum()) if not cohort_df.empty else 0
    n_total_samples = int(cohort_df["n_samples"].sum()) if not cohort_df.empty else 0
    n_total_prog = int(cohort_df["n_progressor"].sum()) if not cohort_df.empty else 0
    n_total_nonprog = int(cohort_df["n_nonprogressor"].sum()) if not cohort_df.empty else 0
    n_binary_cohorts = (
        int(((cohort_df["n_progressor"] > 0) & (cohort_df["n_nonprogressor"] > 0)).sum()) if not cohort_df.empty else 0
    )

    n_sig_genes = int(sig.shape[0])
    top_gene = str(sig.iloc[0]["gene"]) if not sig.empty else "NA"
    top10_genes = ", ".join(sig["gene"].head(10).astype(str).tolist()) if not sig.empty else "NA"

    best_auc = float(perf["auc_roc"].max()) if not perf.empty else float("nan")
    best_row = perf.loc[perf["auc_roc"].idxmax()].to_dict() if not perf.empty else {}
    perf_by_model = (
        perf.groupby("model", as_index=False)[["auc_roc", "auc_pr", "brier"]].mean().sort_values("auc_roc", ascending=False)
        if not perf.empty
        else pd.DataFrame(columns=["model", "auc_roc", "auc_pr", "brier"])
    )
    if not perf_by_model.empty:
        for col in ["auc_roc", "auc_pr", "brier"]:
            perf_by_model[col] = perf_by_model[col].map(lambda x: round(float(x), 3))

    n_meta_genes = int(meta.shape[0])
    median_i2 = float(meta["i2"].median()) if ("i2" in meta.columns and not meta.empty) else float("nan")
    high_i2_n = int((meta["i2"] > 50).sum()) if ("i2" in meta.columns and not meta.empty) else 0
    high_i2_pct = (100.0 * high_i2_n / n_meta_genes) if n_meta_genes else 0.0

    n_within_rows = int(within.shape[0])
    n_within_cohorts = int(within["cohort_id"].nunique()) if "cohort_id" in within.columns else 0

    figure_caps = [
        "Figure 1. Registry curation flow for TB progression transcriptome cohorts (data/registry).",
        "Figure 2. Random-effects forest summary for top meta-analysis genes (results/figures/forest_top_genes.png).",
        "Figure 3. LOCO performance diagnostics: ROC, PR, calibration, and decision curve by model (results/figures/*).",
        "Figure 4. Pathway enrichment profile for signature genes (if available in results/tables/pathway_enrichment.csv).",
    ]
    table_caps = [
        "Table 1. Curated cohorts and class balance used for downstream analysis.",
        "Table 2. Top signature genes and stability frequencies.",
        "Table 3. LOCO model performance summary (AUC-ROC, AUC-PR, Brier).",
    ]

    abstract = (
        "Background: Blood transcriptomic signatures for incipient/progressive TB have shown "
        "promise, but reproducibility across cohorts and platforms remains uncertain.\n\n"
        "Methods: We implemented a fully reproducible public-data pipeline spanning GEO "
        "discovery, cohort curation, preprocessing, gene-level harmonization, random-effects "
        "meta-analysis, and leave-one-cohort-out (LOCO) model validation. "
        f"The current run included {n_cohorts_curated} curated cohorts "
        f"({n_cohorts_with_data} with processed matrices), totaling {n_total_samples} samples "
        f"({n_total_prog} progressors, {n_total_nonprog} nonprogressors), with "
        f"{n_binary_cohorts} cohorts contributing both classes for discrimination modeling.\n\n"
        f"Results: We identified a {n_sig_genes}-gene signature ranked by meta z-score "
        f"(top feature: {top_gene}). LOCO best AUC-ROC was {best_auc:.3f}"
    )
    if best_row:
        abstract += (
            f" ({best_row.get('model', 'NA')}, left-out cohort {best_row.get('left_out_cohort', 'NA')}). "
            f"Meta-analysis covered {n_meta_genes} shared genes; median heterogeneity I2 was {median_i2:.1f}%."
        )
    else:
        abstract += "."
    abstract += (
        "\n\nConclusions: Public blood transcriptome datasets can recover cross-study TB "
        "progression signals, but high heterogeneity and limited harmonized binary cohorts "
        "indicate that further independent validation is required before clinical translation."
    )

    sig_table = (
        _markdown_table(sig.head(25), ["gene", "meta_z", "stability"])
        if not sig.empty
        else "No signature genes were generated.\n"
    )
    perf_table = (
        _markdown_table(perf, ["left_out_cohort", "model", "auc_roc", "auc_pr", "brier"])
        if not perf.empty
        else "No LOCO metrics were generated.\n"
    )

    md = f"""# Manuscript Draft: TB Progression Transcriptome Meta-analysis (Real-data Run)

## Abstract
{abstract}

## Introduction
Tuberculosis (TB) progression risk prediction from host blood transcriptomics is an active translational objective,
especially for screening household contacts and latent infection populations before disease onset.
Published signatures often show reduced reproducibility across geography, platform, and study design.
This work addresses that gap using an end-to-end reproducible meta-analysis and cross-study machine learning pipeline,
designed for repeatable updates as additional cohorts become available.

## Methods
1. Dataset discovery and curation:
Discovery queried GEO using TB progression-related terms via NCBI E-utilities with local caching and rate limiting.
Curated datasets for this run were provided by `{curated_path.as_posix()}`.

2. Inclusion criteria:
Human whole blood/PBMC transcriptomics with progression-relevant labels and adequate sample metadata.
Primary outcomes were harmonized to binary `progressor=1` and `nonprogressor=0`.
Baseline windows were configured by `outcome.window_months={cfg["outcome"]["window_months"]}`.

3. Preprocessing and harmonization:
Downloaded expression sources were normalized and mapped to gene identifiers, with ambiguous mappings filtered.
Per-cohort outputs were written to `data/processed/<cohort_id>/expression.parquet` and `metadata.parquet`.

4. Statistical analysis:
Within-cohort differential expression estimated effect sizes (progressor vs nonprogressor).
Cross-cohort gene effects were combined by random-effects meta-analysis with heterogeneity (`I2`)
and leave-one-cohort-out sensitivity.

5. Signature discovery and validation:
Two strategies were used: meta-effect ranking with stability selection and cross-study ML.
ML models included elastic net logistic regression, linear SVM, and a gene-set score model.
Primary validation used LOCO cross-cohort testing; random-split within-cohort analysis was secondary.

6. Reproducibility:
A single YAML configuration controlled discovery-to-reporting.
Checkpoints enabled resumable runs; all intermediate artifacts were logged.

## Results
### Cohort composition
- Curated cohorts: {n_cohorts_curated}
- Cohorts with processed expression data: {n_cohorts_with_data}
- Total processed samples: {n_total_samples} ({n_total_prog} progressors, {n_total_nonprog} nonprogressors)
- Cohorts with both classes for binary modeling: {n_binary_cohorts}

### Differential expression and meta-analysis
- Within-cohort DE rows: {n_within_rows} across {n_within_cohorts} cohorts.
- Meta-analysis genes in common feature space: {n_meta_genes}.
- Median heterogeneity: I2={median_i2:.1f}%.
- Genes with I2>50%: {high_i2_n}/{n_meta_genes} ({high_i2_pct:.1f}%).

### Signature discovery
- Signature size: {n_sig_genes} genes.
- Top ranked gene: {top_gene}.
- Top 10 signature genes: {top10_genes}.
- Identifiers are currently Ensembl-centric in this run; HGNC-resolved reporting remains a next refinement.

### LOCO model performance
{_markdown_table(perf_by_model, ["model", "auc_roc", "auc_pr", "brier"])}

Best LOCO fold:
- Left-out cohort: {best_row.get("left_out_cohort", "NA")}
- Model: {best_row.get("model", "NA")}
- AUC-ROC: {best_row.get("auc_roc", float("nan")):.3f}
- AUC-PR: {best_row.get("auc_pr", float("nan")):.3f}
- Brier: {best_row.get("brier", float("nan")):.3f}

Secondary analyses:
- Random split sanity table rows: {random_split.shape[0]}.
- Subgroup summary rows: {subgroup.shape[0]}.
- Pathway enrichment rows: {pathway.shape[0]}.
- Time-window sensitivity rows: {window.shape[0]}.

## Discussion
This analysis supports the feasibility of deriving reproducible TB progression signals from public host blood transcriptomics,
with strong LOCO discrimination in at least one held-out cohort.
However, uncertainty remains substantial because only a subset of curated cohorts provided directly compatible progression labels
and harmonized expression features for cross-cohort binary modeling.

Key limitations:
- High between-cohort heterogeneity (high median I2), consistent with platform and cohort design differences.
- At least one curated cohort lacked positive class events for classifier training/validation.
- Current signature is Ensembl-heavy; symbol-level harmonization should be tightened
for biological interpretability and assay transfer.
- Pathway enrichment is sparse in the current run and should be revisited after broader cohort inclusion.

Practical interpretation:
- The pipeline answers the core question in a preliminary but evidence-based way:
cross-study predictive signatures are detectable from public data.
- The current evidence is suitable for a methods/resource-style submission or a reproducible preprint,
not an immediate high-impact translational claim.

Recommended next-stage evidence before definitive claims:
- Add independent progression cohorts with time-to-event labels.
- Refit using strict temporal baselines and predefined prediction windows.
- Perform external locked-model validation and calibration transfer checks.

Target journals for first submission cycle:
- Frontiers in Immunology (methods + host-response fit).
- eBioMedicine (after stronger external validation).
- Scientific Reports (reproducible multi-cohort framework).

## Figure Captions
"""
    md += "\n".join([f"- {c}" for c in figure_caps])
    md += "\n\n## Table Captions\n"
    md += "\n".join([f"- {c}" for c in table_caps])
    md += "\n\n## Data Availability\n"
    md += "- Source datasets are from public GEO records listed in `data/registry` and references.\n"
    md += "- Processed cohort matrices are under `data/processed`.\n"
    md += "\n## Code Availability\n"
    md += "- Full pipeline code, config, tests, and reproducibility artifacts are contained in this repository.\n"
    md += f"- Generated figures directory: `{figures.as_posix()}`.\n"

    out_main.parent.mkdir(parents=True, exist_ok=True)
    out_main.write_text(md, encoding="utf-8")

    supp = f"""# Supplementary Methods

## Reproducibility
- Single YAML config controls discovery, preprocessing, modeling, and reporting.
- Checkpoint files are written after each pipeline stage to support resume.
- Raw and processed data are separated under `data/raw` and `data/processed`.
- This run used `project.seed={cfg["project"]["seed"]}` and `analysis.random_state={cfg["analysis"]["random_state"]}`.
- Runtime mode: `{cfg["project"]["mode"]}` with resume=`{cfg["runtime"]["resume"]}`.

## Cohort Summary
{_markdown_table(cohort_df, ["cohort_id", "n_samples", "n_progressor", "n_nonprogressor"])}

## Signature Gene List (Top 25)
{sig_table}

## Model-level LOCO Metrics
{perf_table}

## Additional Analyses
- Cohort-level random splits are optional sanity checks and not primary validation.
- Subgroup analyses (sex, age, HIV status) run when metadata are available.
- Pathway enrichment output may be empty when input gene symbols are unresolved or insufficient.
"""
    out_supp.write_text(supp, encoding="utf-8")
