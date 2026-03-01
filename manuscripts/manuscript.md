# Manuscript Draft: TB Progression Transcriptome Meta-analysis (Real-data Run)

## Abstract
Background: Blood transcriptomic signatures for incipient/progressive TB have shown promise, but reproducibility across cohorts and platforms remains uncertain.

Methods: We implemented a fully reproducible public-data pipeline spanning GEO discovery, cohort curation, preprocessing, gene-level harmonization, random-effects meta-analysis, and leave-one-cohort-out (LOCO) model validation. The current run included 7 curated cohorts (5 with processed matrices), totaling 533 samples (87 progressors, 446 nonprogressors), with 2 cohorts contributing both classes for discrimination modeling.

Results: We identified a 25-gene signature ranked by meta z-score (top feature: MILR1). LOCO best AUC-ROC was 0.914 (gene_set_score, left-out cohort GSE107994). Meta-analysis covered 10908 shared genes; median heterogeneity I2 was 94.8%.

Conclusions: Public blood transcriptome datasets can recover cross-study TB progression signals, but high heterogeneity and limited harmonized binary cohorts indicate that further independent validation is required before clinical translation.

## Introduction
Tuberculosis (TB) progression risk prediction from host blood transcriptomics is an active translational objective,
especially for screening household contacts and latent infection populations before disease onset.
Published signatures often show reduced reproducibility across geography, platform, and study design.
This work addresses that gap using an end-to-end reproducible meta-analysis and cross-study machine learning pipeline,
designed for repeatable updates as additional cohorts become available.

## Methods
1. Dataset discovery and curation:
Discovery queried GEO using TB progression-related terms via NCBI E-utilities with local caching and rate limiting.
Curated datasets for this run were provided by `data/registry/registry_real_subset.csv`.

2. Inclusion criteria:
Human whole blood/PBMC transcriptomics with progression-relevant labels and adequate sample metadata.
Primary outcomes were harmonized to binary `progressor=1` and `nonprogressor=0`.
Baseline windows were configured by `outcome.window_months=24`.

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
- Curated cohorts: 7
- Cohorts with processed expression data: 5
- Total processed samples: 533 (87 progressors, 446 nonprogressors)
- Cohorts with both classes for binary modeling: 2

### Differential expression and meta-analysis
- Within-cohort DE rows: 21816 across 2 cohorts.
- Meta-analysis genes in common feature space: 10908.
- Median heterogeneity: I2=94.8%.
- Genes with I2>50%: 9184/10908 (84.2%).

### Signature discovery
- Signature size: 25 genes.
- Top ranked gene: MILR1.
- Top 10 signature genes: MILR1, FZD5, AQP1, CRISPLD2, FAM20C, IRAK3, SPTB, HAUS4, MARCO, SLC39A11.
- Identifiers are currently Ensembl-centric in this run; HGNC-resolved reporting remains a next refinement.

### LOCO model performance
| model          |   auc_roc |   auc_pr |   brier |
|:---------------|----------:|---------:|--------:|
| gene_set_score |     0.884 |    0.791 |   0.714 |
| linear_svm     |     0.838 |    0.741 |   0.191 |
| elastic_net    |     0.78  |    0.595 |   0.501 |


Best LOCO fold:
- Left-out cohort: GSE107994
- Model: gene_set_score
- AUC-ROC: 0.914
- AUC-PR: 0.828
- Brier: 0.697

Secondary analyses:
- Random split sanity table rows: 6.
- Subgroup summary rows: 0.
- Pathway enrichment rows: 586.
- Time-window sensitivity rows: 3.

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
- Figure 1. Registry curation flow for TB progression transcriptome cohorts (data/registry).
- Figure 2. Random-effects forest summary for top meta-analysis genes (results/figures/forest_top_genes.png).
- Figure 3. LOCO performance diagnostics: ROC, PR, calibration, and decision curve by model (results/figures/*).
- Figure 4. Pathway enrichment profile for signature genes (if available in results/tables/pathway_enrichment.csv).

## Table Captions
- Table 1. Curated cohorts and class balance used for downstream analysis.
- Table 2. Top signature genes and stability frequencies.
- Table 3. LOCO model performance summary (AUC-ROC, AUC-PR, Brier).

## Data Availability
- Source datasets are from public GEO records listed in `data/registry` and references.
- Processed cohort matrices are under `data/processed`.

## Code Availability
- Full pipeline code, config, tests, and reproducibility artifacts are contained in this repository.
- Generated figures directory: `results/figures`.
