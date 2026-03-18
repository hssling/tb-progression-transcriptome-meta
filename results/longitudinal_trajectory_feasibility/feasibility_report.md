# Longitudinal Trajectory Feasibility Report

## Recommendation
The most feasible high-impact next manuscript is a longitudinal trajectory analysis centered on `GSE79362_genelevel`, with the two harmonized baseline cohorts used for external triangulation rather than forced pooled modeling.

## Why this path is feasible
- `GSE79362_genelevel` contains `264` samples from `107` subjects.
- `73` subjects have repeat samples, including `32` progressors and `41` non-progressors.
- The cohort includes `33` progressor subjects and `74` non-progressor subjects.
- `21` of the current signature genes are already present in the remapped gene-level matrix, which supports immediate trajectory scoring without new wet-lab work.

## Preliminary signal checks
- Baseline-like (`DAY0` + `OTHER`) signature-score difference between progressors and non-progressors was not significant in this quick audit (Welch p=0.284).
- Across all samples with a numeric month value, the signature score showed a modest negative correlation with follow-up month (Spearman rho=-0.157, p=0.0134).
- The negative month-score correlation was stronger among progressors (rho=-0.289, p=0.00834) than among non-progressors (rho=-0.092, p=0.24).
- Subject-level signature-score slopes were more negative on average in progressors than non-progressors, but this quick comparison was not yet statistically significant (Welch p=0.438).

## Scientific angle
This opens a more novel question than another static biomarker paper: whether a progression-associated host-response program is temporally dynamic within subjects and whether repeated blood RNA measurements show different trajectories in progressors and non-progressors.

## Immediate paper concept
`Longitudinal dynamics of a tuberculosis progression host-response program in a prospective blood RNA-sequencing cohort`

## Core analyses for the full manuscript
1. Mixed-effects modeling of signature score versus follow-up month with a progressor-by-time interaction.
2. Gene-level random-slope models for the strongest progression genes and for the remap-sensitive myeloid genes such as `FCGR3B`, `HP`, and `ACSL1`.
3. Module-level and pathway-level trajectory analysis to test whether myeloid and vascular programs evolve differently over follow-up.
4. Sensitivity analyses that separate `DAY0`, scheduled follow-up visits, and `IC` samples rather than collapsing them prematurely.
5. External triangulation using `GSE107994` and `GSE193777` only as fixed-time external reference cohorts, not as longitudinal substitutes.

## Important limits
- The current month field is follow-up timing, not a validated exact time-to-disease measure. Any manuscript should avoid language that implies confirmed months-to-TB unless the original cohort metadata support that directly.
- `IC` samples need separate handling because they are not naturally ordered with the scheduled follow-up visits in the remapped metadata.
- This feasibility layer supports a longitudinal host-response paper, but not yet a definitive clinical forecasting paper.

## Files generated here
- `cohort_summary.csv`
- `timepoint_distribution.csv`
- `subject_repeat_summary.csv`
- `signature_score_summary.csv`
- `subject_signature_slopes.csv`
- `timepoint_distribution_by_progressor.png`
- `signature_score_by_timepoint.png`

## Bottom line
Among the currently available local datasets, the longitudinal `GSE79362_genelevel` route is the most feasible combination of novelty, biological depth, and manuscript potential. It is stronger as a dynamics-and-mechanism paper than as a new classification paper.
