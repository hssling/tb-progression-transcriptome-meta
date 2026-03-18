# Next Research Roadmap

## Priority choice
The highest-value next paper is a longitudinal host-response manuscript built around `GSE79362_genelevel`, with `GSE107994` and `GSE193777` used for external triangulation rather than forced joint longitudinal modeling.

## Why this path wins
- It is more novel than another cross-sectional signature paper.
- It uses a dataset already remapped to gene level and already present in the repo.
- It adds temporal biology rather than only another ranking table.
- It can support a systems-biology framing and still remain scientifically conservative.

## Working manuscript concept
`Longitudinal dynamics of a tuberculosis progression host-response program in a prospective blood RNA-sequencing cohort`

## Main question
Do repeated blood transcriptomic measurements show different within-subject trajectories in progressors and non-progressors, and do those trajectories reinforce the myeloid and vascular host programs already identified in the current manuscripts?

## Secondary questions
- Are the core progression genes stable across time or concentrated at specific visits?
- Do remap-sensitive genes such as `FCGR3B`, `HP`, and `ACSL1` behave differently from the two-cohort Bayesian genes such as `MILR1`, `VSIG4`, `CD36`, and `CCR2`?
- Do pathway and module scores show coherent temporal movement even when individual genes are noisy?
- Are `IC` samples biologically distinct enough to require separate handling?

## Planned analysis sequence
1. Mixed-effects models for signature score against follow-up month with progressor interaction.
2. Gene-level mixed-effects models for top progression genes.
3. Timepoint-stratified pathway and module analyses.
4. Sensitivity models that isolate `DAY0`, scheduled follow-up visits, and `IC` samples.
5. External triangulation against the existing two-cohort baseline evidence.

## Current evidence checkpoint
See [results/longitudinal_trajectory_feasibility/feasibility_report.md](/d:/research-automation/TB%20multiomics/tb%20progression%20transcriptomic/results/longitudinal_trajectory_feasibility/feasibility_report.md).

## Not prioritized now
- Another pure classifier paper: lower novelty.
- A broad all-cohort pooled paper right now: too much heterogeneity and weak temporal metadata outside `GSE79362`.
- A causal manuscript: current data are not strong enough for causal claims.
