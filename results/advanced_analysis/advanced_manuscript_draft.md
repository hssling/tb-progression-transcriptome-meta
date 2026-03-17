# Bayesian and Systems-Level Reanalysis of TB Progression Transcriptomes

## Working Title
Bayesian and systems-level reanalysis of public tuberculosis progression transcriptomes reveals stable host-response programs and uncertainty-aware biomarkers

## Abstract Draft
### Background
Public tuberculosis progression transcriptomic studies contain more biological information than is captured by simple ranked-gene summaries alone. In particular, latent expression structure, posterior uncertainty, and pathway-level convergence may clarify whether the observed signal reflects a coherent host-response program.

### Methods
We performed an advanced secondary analysis of the currently harmonizable cohorts using shared-gene principal component analysis, cohort-centered latent factor analysis, Bayesian hierarchical gene synthesis, Bayesian pathway modeling, signature-network analysis, and DAG-based bias interpretation.

### Results
The advanced shared-gene analysis included 301 samples from GSE107994 and GSE193777. Shared-gene overlap was sufficient for joint analysis, and cohort-centered principal components improved progressor separation relative to raw joint PCA. Bayesian synthesis prioritized MILR1, VSIG4, FZD5, CD36, CCR2, ASGR2, AQP1, CRISPLD2. Pathway-level posterior effects were strongest for angiogenesis; blood vessel development; blood vessel morphogenesis; regulation of angiogenesis; regulation of vasculature development. Latent factors remained associated with progressor status (Factor1 p=5.78e-11; Factor2 p=2.85e-09; Factor3 p=9.16e-04).

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
The strongest posterior-ranked genes were MILR1, VSIG4, FZD5, CD36, CCR2, ASGR2, AQP1, CRISPLD2. These genes retained narrow uncertainty intervals and consistent directionality, indicating that the leading progression signal is not an artifact of single-cohort ranking alone. The posterior results therefore strengthen confidence in the core host-response program while still acknowledging two-cohort limits.

### Pathway-level Bayesian findings
The leading pathway-level posterior effects were angiogenesis; blood vessel development; blood vessel morphogenesis; regulation of angiogenesis; regulation of vasculature development. This result shifts interpretation toward host-response programs involving vascular remodeling and immune-tissue interface biology, rather than toward a single inflammatory axis.

### Latent factors
All three leading latent factors were associated with progressor status (Factor1 p=5.78e-11; Factor2 p=2.85e-09; Factor3 p=9.16e-04). This suggests that the progression phenotype is not captured by only one dominant expression axis. Instead, the data are more consistent with a layered host response in which multiple partially independent programs move together as disease risk increases.

## Discussion
These advanced analyses add scientific meaning in three ways. First, they show that the progression signal can still be detected after explicit cohort-centering, which makes the interpretation more robust to study structure. Second, they replace point-ranked genes with posterior summaries and uncertainty intervals, producing a more defensible estimate of which genes remain strong after shrinkage. Third, they show that pathway-level and latent-factor analyses converge on a biology that includes angiogenesis-linked remodeling, phagocytic behavior, and immune regulation.

The analysis also clarifies limits of inference. The shared-gene layer is currently restricted to two cohorts, so the Bayesian and latent-structure results should be read as uncertainty-aware extensions of the existing evidence, not as definitive cross-population conclusions. The DAG helps formalize this point by showing where cohort, platform, and preprocessing may induce bias.

Even so, the reanalysis is useful because it produces a more biologically interpretable second manuscript. The most defensible message is not that one transcript explains progression, but that a coordinated host program remains visible across multiple analytic layers after conservative harmonization.

## Conclusion
The available harmonizable public datasets support a systems-level interpretation of tuberculosis progression biology and justify a second manuscript focused on Bayesian uncertainty, latent expression structure, and causal-interpretation framing. The strongest message is not that one gene explains progression, but that a coordinated host program remains visible across multiple analytic layers. Additional harmonized cohorts are now the key requirement for stronger generalization claims.
