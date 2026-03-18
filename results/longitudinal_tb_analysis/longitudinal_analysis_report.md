# Longitudinal Tuberculosis Trajectory Analysis

## Dataset
- Cohort: `GSE79362_genelevel`
- Samples with metadata: `264`
- Subjects: `107`
- Progressor subjects: `33`
- Non-progressor subjects: `74`
- Samples with numeric follow-up month used in primary mixed-effects models: `248`

## Program definitions used here
- `bayesian_core8`: `5` genes (VSIG4, CD36, CCR2, ASGR2, CRISPLD2)
- `module_M5_proxy`: `1496` genes (AAGAB, AAK1, AATF, ABCB1, ABCD2, ABHD12, ABHD14B, ABHD15 ...)
- `module_M6_proxy`: `551` genes (ABHD5, ABLIM3, ACO2, ACOT9, ACRBP, ACTG1, ACTR1A, ACVRL1 ...)
- `remap_myeloid5`: `5` genes (FCGR3B, HP, ACSL1, ANXA5, SERINC2)
- `signature25_proxy`: `21` genes (CRISPLD2, FAM20C, IRAK3, SPTB, HAUS4, MARCO, SLC39A11, TMEM144 ...)
- `vascular_proxy5`: `4` genes (VEGFB, LOXL1, PLXDC2, FAM20C)

## Primary modeling strategy
- Random-intercept mixed-effects models were fit for each score with fixed effects for follow-up month, progressor status, and a progressor-by-month interaction.
- Numeric follow-up models excluded `IC` samples because those samples are not naturally ordered on the scheduled visit scale in the remapped metadata.
- `IC` samples were evaluated separately through progressor-only contrasts as descriptive sensitivity analyses.

## Main findings
- Strongest program-level interaction: `vascular_proxy5` with interaction coefficient `-0.0218`, p=`0.009186`, FDR=`0.05873`.
- Strongest gene-level interaction trend: `ACSL1` with interaction coefficient `-0.0330`, p=`0.05673`, FDR=`0.176`.
- Program-level interaction counts: `0` at FDR <0.05 and `5` at FDR <0.10.
- Gene-level interaction counts: `0` at FDR <0.05 and `0` at FDR <0.10.
- Program-level features retained at FDR <0.10: `vascular_proxy5, remap_myeloid5, Neutrophil, Platelet, module_M6_proxy`.
- Leading nominal gene-level trends were `ACSL1, FCGR3B, VSIG4`, but no gene-level interaction survived multiple-testing control in this run.
- Negative interaction coefficients indicate that the score declined more steeply over follow-up in progressors than in non-progressors.
- These longitudinal results should be interpreted as trajectory evidence within the remapped cohort, not as direct time-to-disease forecasting.

## Interpretation
- This analysis tests temporal behavior of already-supported host-response programs rather than searching for another de novo classifier.
- The clearest publishable angle is whether progression-associated biology is dynamically reconfigured over repeated visits and whether that dynamic is stronger for myeloid or vascular-linked programs.
- The most defensible current signal is at the program level rather than at the individual-gene level.
- The `IC` state should remain analytically separate in any manuscript because it is not equivalent to a scheduled follow-up visit.

## IC sensitivity note
- Top IC versus scheduled progressor contrast: `HP` with delta `-0.3337` and p=`0.1383`.

## Outputs
- `program_scores.csv`
- `mixedlm_program_models.csv`
- `mixedlm_gene_models.csv`
- `subject_program_slopes.csv`
- `timepoint_program_summary.csv`
- `ic_progressor_contrasts.csv`
- trajectory figures in this folder
