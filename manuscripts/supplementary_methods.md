# Supplementary Methods

## Reproducibility
- Single YAML config controls discovery, preprocessing, modeling, and reporting.
- Checkpoint files are written after each pipeline stage to support resume.
- Raw and processed data are separated under `data/raw` and `data/processed`.
- This run used `project.seed=42` and `analysis.random_state=42`.
- Runtime mode: `full` with resume=`True`.

## Cohort Summary
| cohort_id   |   n_samples |   n_progressor |   n_nonprogressor |
|:------------|------------:|---------------:|------------------:|
| GSE107993   |         138 |              0 |               138 |
| GSE107994   |         175 |             53 |               122 |
| GSE107995   |           0 |              0 |                 0 |
| GSE117435   |          85 |              0 |                85 |
| GSE193777   |         126 |             34 |                92 |
| GSE29190    |           9 |              0 |                 9 |
| GSE79362    |           0 |              0 |                 0 |


## Signature Gene List (Top 25)
| gene     |   meta_z |   stability |
|:---------|---------:|------------:|
| MILR1    |  19.8964 |        1    |
| FZD5     |  19.3547 |        1    |
| AQP1     |  19.2684 |        1    |
| CRISPLD2 |  19.1992 |        1    |
| FAM20C   |  18.3592 |        1    |
| IRAK3    |  17.4712 |        1    |
| SPTB     |  17.0318 |        1    |
| HAUS4    |  16.8281 |        1    |
| MARCO    |  16.7267 |        1    |
| SLC39A11 |  16.6518 |        1    |
| TMEM144  |  16.649  |        1    |
| LOXL1    |  16.6479 |        1    |
| STS      |  16.5501 |        1    |
| POMGNT1  | -16.3515 |        1    |
| LTK      | -16.3657 |        1    |
| ALOX15   | -17.0619 |        1    |
| SIGLEC8  | -17.4263 |        1    |
| MARCKSL1 | -18.4072 |        1    |
| CDH24    | -18.5556 |        1    |
| PLD4     | -19.3182 |        1    |
| CD44     |  16.2799 |        0.97 |
| PTGDR2   | -16.2105 |        0.91 |
| EPN2     | -16.1422 |        0.89 |
| CHTF18   | -16.117  |        0.85 |
| VEGFB    | -15.8116 |        0.39 |


## Model-level LOCO Metrics
| left_out_cohort   | model          |   auc_roc |   auc_pr |    brier |
|:------------------|:---------------|----------:|---------:|---------:|
| GSE107994         | elastic_net    |  0.894525 | 0.835153 | 0.272487 |
| GSE107994         | linear_svm     |  0.871018 | 0.814007 | 0.140125 |
| GSE107994         | gene_set_score |  0.914321 | 0.828106 | 0.697143 |
| GSE193777         | elastic_net    |  0.664642 | 0.355259 | 0.730159 |
| GSE193777         | linear_svm     |  0.805307 | 0.66891  | 0.24135  |
| GSE193777         | gene_set_score |  0.85454  | 0.753387 | 0.730159 |


## Additional Analyses
- Cohort-level random splits are optional sanity checks and not primary validation.
- Subgroup analyses (sex, age, HIV status) run when metadata are available.
- Pathway enrichment output may be empty when input gene symbols are unresolved or insufficient.
