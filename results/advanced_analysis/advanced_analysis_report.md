# Advanced TB Progression Analysis

## Scope
This analysis used the currently supportable shared-gene cohorts (GSE107994 and GSE193777) for advanced unsupervised, Bayesian, and causal-interpretation analyses.
The goal was not to maximize apparent predictive performance, but to extract additional biological meaning from the available harmonizable datasets without overstating what two cohorts can support.

## Key findings
- Shared-gene overlap between the two cohorts was sufficient for joint latent-structure analysis.
- Raw PCA remained cohort-influenced, but cohort-centered PCA improved progressor separation along principal components.
- Mean raw PC1 by progressor status: {0: 2.8636630560734133, 1: -7.043952804594372}.
- Mean PC1 by progressor status after cohort centering: {0: -13.182437129176149, 1: 32.42576489245627}.
- The leading posterior-ranked genes were MILR1, VSIG4, FZD5, CD36, CCR2, ASGR2.
- The strongest Bayesian pooled gene signal was MILR1 with posterior mean 1.229 and 95% CI [1.108, 1.351].
- Top latent factors retained progressor-associated structure with factor-level summary p-values captured in factor_summary.csv.
- The strongest pathway-level Bayesian signal was 'angiogenesis' with posterior mean 0.725.

## Latent factor summary
- Factor1: mean(progressor)=0.662, mean(non-progressor)=-0.269, p=5.780e-11
- Factor2: mean(progressor)=0.561, mean(non-progressor)=-0.228, p=2.848e-09
- Factor3: mean(progressor)=0.303, mean(non-progressor)=-0.123, p=9.161e-04

## Interpretation
The advanced analyses support a model in which TB progression is associated with coordinated host-response programs rather than a single isolated marker. The Bayesian outputs emphasize uncertainty and preserve the current evidence boundary, while the DAG formalizes why cohort, platform, and preprocessing must be treated as potential sources of bias rather than ignored nuisances.
The pathway-level results shifted emphasis toward angiogenesis-linked and vasculature-development terms, suggesting that the host progression signal may involve endothelial or tissue-interface remodeling alongside immune activation.
The latent factor results reinforce that interpretation by showing that multiple orthogonal expression programs, not just one dominant axis, are associated with progressor status.
Taken together, the findings add biological structure to the original signature-discovery work: the same public cohorts now support latent axes, posterior uncertainty estimates, pathway convergence, and network coherence around the strongest genes.

## Limits
- The shared-gene advanced layer is currently restricted to GSE107994 and GSE193777.
- GSE79362 remains useful for validation questions, but its present feature mapping is not commensurate with the shared-gene analyses.
- The DAG is an interpretive tool, not proof of causality.
- The current results are stronger as biological and methodological evidence than as a clinical deployment claim.
