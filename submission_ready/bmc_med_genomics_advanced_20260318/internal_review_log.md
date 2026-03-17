# Internal Review Note

Review pass 1
- Checked that all numerical claims in the manuscript match files in `results/advanced_analysis`.
- Confirmed that cohort counts, progressor counts, posterior means, factor p values, pathway terms, deconvolution deltas, and coexpression module statistics match generated outputs.
- Identified gaps: sparse method references for deconvolution/coexpression, NA demographic fields in Table 1, and p-value rendering that rounded small values to zero.
- Removed language that would imply causal proof or clinical readiness.

Review pass 2
- Checked sequential appearance of Table 1 to Table 4 and Figure 1 to Figure 4 in the manuscript text.
- Checked that the DAG is placed in the supplementary document, not in the main article as if it were an estimated causal model.
- Checked that the conclusions remain aligned with the two-cohort evidence boundary.
- Confirmed that age and sex are now parsed from metadata, platform is reported in Table 1, and extension summaries include FDR columns.
