from __future__ import annotations

from datetime import datetime
from pathlib import Path
import textwrap
import zipfile

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "submission_ready" / "bmc_personalized_medicine_20260317"
REPO_URL = "https://github.com/hssling/tb-progression-transcriptome-meta"

AUTHOR = {
    "name": "Dr. Siddalingaiah H S, MD",
    "department": "Department of Community Medicine",
    "institution": "Shridevi Institute of Medical Sciences & Research Hospital",
    "city": "Tumkur",
    "state": "Karnataka",
    "country": "India",
    "email": "hssling@yahoo.com",
    "orcid": "0000-0002-4771-8285",
}

TITLE = (
    "A reproducible multi-cohort transcriptomic meta-analysis identifies "
    "host blood biomarkers associated with tuberculosis progression"
)
RUNNING_TITLE = "TB progression transcriptomic meta-analysis"


def set_default_style(doc: Document) -> None:
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(11)
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    doc.add_heading(text, level=level)


def add_para(doc: Document, text: str = "", bold: bool = False, center: bool = False) -> None:
    p = doc.add_paragraph()
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = bold


def add_table_from_df(
    doc: Document,
    df: pd.DataFrame,
    caption: str,
    round_map: dict[str, int] | None = None,
    max_rows: int | None = None,
) -> None:
    add_para(doc, caption, bold=True)
    if max_rows is not None:
        df = df.head(max_rows)
    if round_map:
        df = df.copy()
        for col, digits in round_map.items():
            if col in df.columns:
                df[col] = df[col].map(lambda value: f"{value:.{digits}f}" if pd.notna(value) else "")
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = "Table Grid"
    for idx, col in enumerate(df.columns):
        table.cell(0, idx).text = str(col)
    for row in df.itertuples(index=False):
        cells = table.add_row().cells
        for idx, value in enumerate(row):
            cells[idx].text = str(value)
    doc.add_paragraph("")


def add_picture(doc: Document, path: Path, caption: str, width: float = 6.0) -> None:
    if not path.exists():
        return
    doc.add_picture(str(path), width=Inches(width))
    p = doc.paragraphs[-1]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_para(doc, caption, center=True)


def load_inputs() -> dict[str, pd.DataFrame]:
    return {
        "dataset_summary": pd.read_csv(ROOT / "R_pipeline" / "output" / "dataset_summary.csv"),
        "meta_gene_list": pd.read_csv(ROOT / "submission_package" / "Tables" / "meta_gene_list.csv"),
        "validation_summary": pd.read_csv(ROOT / "R_pipeline" / "output" / "validation_summary.csv"),
        "loco_performance": pd.read_csv(ROOT / "results" / "tables" / "loco_performance.csv"),
        "pathway_enrichment": pd.read_csv(ROOT / "R_pipeline" / "output" / "pathway_enrichment_R.csv"),
        "lasso_signature": pd.read_csv(ROOT / "R_pipeline" / "output" / "lasso_signature.csv"),
        "pipeline_timings": pd.read_csv(ROOT / "submission_package" / "Tables" / "pipeline_timings.csv"),
    }


def build_title_page() -> Path:
    doc = Document()
    set_default_style(doc)
    add_para(doc, TITLE, bold=True, center=True)
    add_para(doc, "", center=True)
    add_para(doc, AUTHOR["name"], center=True)
    add_para(
        doc,
        (
            f'{AUTHOR["department"]}, {AUTHOR["institution"]}, '
            f'{AUTHOR["city"]}, {AUTHOR["state"]}, {AUTHOR["country"]}'
        ),
        center=True,
    )
    add_para(doc, f'ORCID: {AUTHOR["orcid"]}', center=True)
    add_para(doc, f'Correspondence: {AUTHOR["email"]}', center=True)
    add_para(doc, f"Running title: {RUNNING_TITLE}", center=True)
    add_para(doc, "Keywords: tuberculosis, incipient tuberculosis, transcriptomics, biomarker, meta-analysis", center=True)
    doc.add_page_break()
    add_heading(doc, "Declarations", 1)
    sections = {
        "Author details": (
            f'{AUTHOR["name"]}, {AUTHOR["department"]}, {AUTHOR["institution"]}, '
            f'{AUTHOR["city"]}, {AUTHOR["state"]}, {AUTHOR["country"]}.'
        ),
        "Funding": "No external funding was received for this study.",
        "Competing interests": "The author declares that there are no competing interests.",
        "Author contributions": (
            "Siddalingaiah H S conceived the study, curated the analysis framework, "
            "reviewed the computational outputs, drafted the manuscript, and approved the final version."
        ),
        "Availability of data and materials": (
            "Public-source cohort identifiers, generated summary tables, figures, manuscript assets, and "
            f"submission documentation are available in the project repository ({REPO_URL}). "
            "Primary transcriptomic studies were obtained from NCBI GEO."
        ),
        "Code availability": (
            "The reproducible codebase for discovery, harmonization, meta-analysis, reporting, and submission-asset "
            f"generation is available at {REPO_URL}."
        ),
        "Ethics approval and consent to participate": (
            "This work used de-identified publicly available transcriptomic datasets and did not involve new patient recruitment. "
            "Additional institutional ethics review was therefore not required for the present secondary analysis."
        ),
        "Consent for publication": "Not applicable.",
        "Acknowledgements": "The author acknowledges the original investigators who deposited the GEO datasets used in this analysis.",
    }
    for heading, text in sections.items():
        add_heading(doc, heading, 2)
        add_para(doc, text)
    out_path = OUT_DIR / "01_Title_Page_and_Declarations.docx"
    doc.save(out_path)
    return out_path


def build_main_article(data: dict[str, pd.DataFrame]) -> Path:
    doc = Document()
    set_default_style(doc)
    add_para(doc, TITLE, bold=True, center=True)
    add_para(doc, AUTHOR["name"], center=True)
    add_para(doc, "", center=True)

    add_heading(doc, "Abstract", 1)
    abstract = textwrap.dedent(
        """
        Background: Blood transcriptomic signatures are promising tools for identifying people at risk of progression from latent Mycobacterium tuberculosis infection to active disease, but reproducibility across cohorts and assay platforms remains a persistent limitation.

        Methods: Public blood transcriptomic datasets relevant to tuberculosis progression were curated from GEO. Three primary cohorts were processed, harmonized, and summarized, with two cohorts contributing directly comparable binary labels for leave-one-cohort-out validation. Random-effects meta-analysis was combined with stability-guided feature ranking and three classifiers: elastic net, linear support vector machine, and a simple gene-set score.

        Results: The analysis prioritised a 25-gene progression-associated signature. Top-ranked genes included MILR1, VSIG4, CCR2, CD36, FZD5, AQP1, and IRAK3. The best leave-one-cohort-out result was obtained by the gene-set-score model in GSE107994 (AUC-ROC 0.914; AUC-PR 0.828). Mean AUC-ROC values were 0.884 for the gene-set-score model, 0.838 for linear SVM, and 0.780 for elastic net. Enrichment analysis implicated angiogenesis-linked immune remodeling, phagocytosis, leukocyte-mediated immunity, and myeloid activation.

        Conclusions: A reproducible public-data workflow can recover a coherent host blood signature associated with tuberculosis progression, but the present evidence base remains constrained by limited harmonized progression cohorts and pending cross-platform validation in microarray studies. The current package is positioned as a reproducible biomarker-discovery resource suitable for a methods-forward translational journal.
        """
    ).strip()
    for paragraph in abstract.split("\n\n"):
        add_para(doc, paragraph)

    add_heading(doc, "Introduction", 1)
    intro_paragraphs = [
        (
            "Tuberculosis remains a major infectious disease challenge, and the transition from latent infection to active disease "
            "is the most actionable window for preventive intervention. Host blood transcriptomics has emerged as a practical non-sputum "
            "approach for identifying this transition, but published signatures often degrade when they are applied outside the discovery cohort."
        ),
        (
            "The central problem is not only biological heterogeneity but also inconsistent cohort definitions, platform effects, feature mapping, "
            "and data leakage during validation. Public datasets remain valuable for addressing this problem if they are reprocessed within a single "
            "transparent workflow and judged with genuinely external validation."
        ),
        (
            "This study therefore aimed to assemble a reproducible TB progression transcriptomic workflow spanning cohort identification, preprocessing, "
            "harmonization, gene-level meta-analysis, pathway analysis, and leave-one-cohort-out model assessment. The objective was not to make a "
            "premature clinical claim, but to generate a transparent and submission-ready biomarker-discovery resource anchored to real public data."
        ),
    ]
    for paragraph in intro_paragraphs:
        add_para(doc, paragraph)

    add_heading(doc, "Methods", 1)
    method_sections = {
        "Study design and data sources": (
            "The workflow queried public GEO studies relevant to host blood transcriptomic signatures of TB progression or related incipient disease states. "
            "Eligible studies were human whole-blood or PBMC transcriptomic datasets with usable phenotype annotations, processed expression matrices or count data, "
            "and progression-relevant cohort structure."
        ),
        "Cohort curation": (
            "The current submission package retains three primary downloaded and processed datasets: GSE107994, GSE193777, and GSE79362. "
            "Microarray cohorts GSE19491, GSE37250, and GSE39940 were retained as identified candidates for future expansion but were not yet carried through the same validation path."
        ),
        "Preprocessing and harmonization": (
            "RNA-seq matrices were normalized and harmonized to gene-level features. Duplicate mappings were collapsed conservatively, and datasets were restricted to shared gene space. "
            "The reporting package documents the current common-feature analysis table rather than claiming a broader harmonization than the available labels support."
        ),
        "Meta-analysis": (
            "Per-gene effects were combined using a random-effects framework. Genes were ranked by absolute meta z-score, with false-discovery adjustment retained for prioritization. "
            "This package reports the top progression-associated genes directly from the exported meta-analysis table."
        ),
        "Model development and validation": (
            "Model assessment used leave-one-cohort-out validation to avoid within-cohort leakage. Three approaches were assessed: elastic net logistic regression, linear SVM, and a gene-set score. "
            "Performance was summarized using AUC-ROC, AUC-PR, and Brier score."
        ),
        "Pathway analysis": (
            "The leading genes were evaluated against Gene Ontology biological-process enrichment outputs from the R reporting pipeline. Enrichment statements in this manuscript are restricted to terms present in the exported results."
        ),
    }
    for heading, text in method_sections.items():
        add_heading(doc, heading, 2)
        add_para(doc, text)

    add_heading(doc, "Results", 1)
    add_heading(doc, "Curated cohort set", 2)
    add_para(
        doc,
        "The curated registry identified six relevant public studies, of which three were processed as primary cohorts in the current run. "
        "These three studies capture geographically distinct designs, including the Leicester cohort, a South Indian household-contact cohort, and the ACS prospective cohort."
    )
    cohort_table = data["dataset_summary"].loc[
        data["dataset_summary"]["Status"].str.contains("Primary", na=False),
        ["GEO_ID", "Platform", "Total_Samples", "Groups", "PMID"],
    ]
    add_table_from_df(doc, cohort_table, "Table 1. Primary cohorts carried into the current submission package.")

    add_heading(doc, "Progression-associated genes", 2)
    add_para(
        doc,
        "The meta-analysis prioritised genes involved in innate immune regulation, phagocytic activity, leukocyte signaling, and vascular-remodeling programs. "
        "MILR1 was the top-ranked signal, followed by VSIG4, CCR2, CD36, and FZD5. IRAK3 remained within the leading progression-associated set and supports an interpretation of altered innate immune control."
    )
    gene_table = data["meta_gene_list"].loc[:, ["gene", "meta_effect", "meta_z", "meta_fdr", "i2"]]
    add_table_from_df(
        doc,
        gene_table,
        "Table 2. Top 15 progression-associated genes from the random-effects meta-analysis.",
        round_map={"meta_effect": 3, "meta_z": 3, "meta_fdr": 3, "i2": 1},
        max_rows=15,
    )

    add_heading(doc, "Cross-cohort validation", 2)
    add_para(
        doc,
        "Cross-cohort performance was strongest for the gene-set-score model, which achieved the best held-out discrimination in GSE107994. "
        "Linear SVM showed the most balanced calibration among the three tested approaches, whereas the gene-set-score model traded calibration for stronger ranking performance."
    )
    perf_table = data["loco_performance"].copy()
    add_table_from_df(
        doc,
        perf_table,
        "Table 3. Leave-one-cohort-out model performance.",
        round_map={"auc_roc": 3, "auc_pr": 3, "brier": 3},
    )

    add_heading(doc, "Functional interpretation", 2)
    add_para(
        doc,
        "Enrichment analysis highlighted regulation of angiogenesis, vasculature development, immune effector processes, leukocyte degranulation, myeloid activation, and phagocytosis. "
        "These results support a host-response pattern that blends inflammatory recruitment with regulatory remodeling rather than a single-axis interferon signal."
    )
    pathway_table = data["pathway_enrichment"].loc[:, ["ID", "Description", "GeneRatio", "p.adjust", "geneID"]]
    add_table_from_df(
        doc,
        pathway_table,
        "Table 4. Representative enriched biological processes among leading progression-associated genes.",
        round_map={"p.adjust": 4},
        max_rows=12,
    )

    add_heading(doc, "Discussion", 1)
    discussion_paragraphs = [
        (
            "The main contribution of this work is not only the proposed gene list, but the conversion of a heterogeneous public-data problem into a transparent, reproducible submission package. "
            "The signature is dominated by genes linked to phagocytic handling, immune-cell trafficking, and regulatory myeloid signaling, which is plausible for an incipient TB state."
        ),
        (
            "MILR1, VSIG4, CCR2, CD36, FZD5, AQP1, and IRAK3 form a coherent biological core. Rather than claiming definitive clinical readiness, the present evidence supports these genes as a candidate module for external assay development and prospective follow-up."
        ),
        (
            "The limitations are material. Only two cohorts currently support the binary validation framework, cross-platform microarray validation remains pending, and the Brier scores indicate that discrimination is stronger than probability calibration. "
            "These points are surfaced directly because they matter for journal fit and for the framing of translational claims."
        ),
        (
            "For those reasons, the manuscript is framed for a methods-forward biomarker-discovery submission rather than a high-claim clinical diagnostic paper. "
            "That positioning is also what makes BMC Personalized Medicine an appropriate first target."
        ),
    ]
    for paragraph in discussion_paragraphs:
        add_para(doc, paragraph)

    add_heading(doc, "Conclusions", 1)
    add_para(
        doc,
        "A reproducible public-data workflow identified a biologically coherent host blood signature associated with TB progression risk and generated a complete manuscript package from the available outputs. "
        "The signature is promising for follow-up, but broader harmonized cohort coverage and external validation remain necessary before stronger translational claims are warranted."
    )

    add_heading(doc, "Figures", 1)
    figure_dir = ROOT / "R_pipeline" / "figures"
    add_picture(
        doc,
        figure_dir / "forest_plot.png",
        "Figure 1. Forest-style summary plot of progression-associated transcriptomic effects across included cohorts.",
    )
    add_picture(
        doc,
        figure_dir / "roc_combined.png",
        "Figure 2. Combined ROC comparison across the evaluated validation models.",
    )
    add_picture(
        doc,
        figure_dir / "heatmap_signature.png",
        "Figure 3. Heatmap of the leading gene signature across the harmonized cohort set.",
    )
    add_picture(
        doc,
        figure_dir / "go_bp_dotplot.png",
        "Figure 4. Gene Ontology biological-process enrichment profile for the leading signature genes.",
    )

    add_heading(doc, "Declarations", 1)
    declaration_items = [
        ("Ethics approval and consent to participate", "No new human participants were enrolled. The analysis used de-identified public data only."),
        ("Consent for publication", "Not applicable."),
        ("Availability of data and materials", f"All generated submission assets, manuscript sources, figures, and tabular outputs are documented in the Git repository: {REPO_URL}."),
        ("Code availability", f"The full codebase used to prepare this analysis is maintained at {REPO_URL}."),
        ("Competing interests", "The author declares no competing interests."),
        ("Funding", "No external funding was received."),
        ("Author contributions", "Siddalingaiah H S performed the study design, analysis oversight, manuscript preparation, and final approval."),
    ]
    for heading, text in declaration_items:
        add_heading(doc, heading, 2)
        add_para(doc, text)

    add_heading(doc, "References", 1)
    references = [
        "Zak DE, Penn-Nicholson A, Scriba TJ, et al. A blood RNA signature for tuberculosis disease risk: a prospective cohort study. Lancet. 2016;387:2312-2322.",
        "Singhania A, Verma R, Graham CM, et al. A modular transcriptional signature identifies phenotypic heterogeneity of human tuberculosis infection. Nature Communications. 2018;9:2308.",
        "Rajamanickam A, Munisankar S, Dolla CK, et al. Host blood-based biosignatures for subclinical tuberculosis in household contacts. Scientific Reports. 2023;13:1085.",
        "Ritchie ME, Phipson B, Wu D, et al. limma powers differential expression analyses for RNA-sequencing and microarray studies. Nucleic Acids Research. 2015;43:e47.",
        "The tb-progression-transcriptome-meta repository. Available at: https://github.com/hssling/tb-progression-transcriptome-meta.",
    ]
    for ref in references:
        add_para(doc, ref)

    out_path = OUT_DIR / "02_Main_Article.docx"
    doc.save(out_path)
    return out_path


def build_supplement(data: dict[str, pd.DataFrame]) -> Path:
    doc = Document()
    set_default_style(doc)
    add_para(doc, "Supplementary Information", bold=True, center=True)
    add_para(doc, TITLE, center=True)

    add_heading(doc, "Supplementary Methods", 1)
    supplement_text = [
        "The computational workflow combined Python-based project orchestration with an R-based downstream reporting layer. The package preserved exported cohort summaries, meta-analysis tables, LOCO validation metrics, pathway enrichment results, and manuscript assets in version-controlled form.",
        "Primary processed cohorts were the Leicester cohort (GSE107994), the Southern India household-contact cohort (GSE193777), and the ACS cohort (GSE79362). Candidate microarray cohorts remained catalogued for future harmonization.",
        "The current supplementary file emphasises reproducibility inventory rather than restating every package dependency already captured in the repository.",
    ]
    for paragraph in supplement_text:
        add_para(doc, paragraph)

    add_heading(doc, "Supplementary Table S1. Stability-ranked minimal signature", 1)
    add_table_from_df(
        doc,
        data["lasso_signature"].loc[:, ["rank", "gene", "stability", "meta_z"]],
        "Stability-guided ranking of minimal signature candidates.",
        round_map={"stability": 2, "meta_z": 3},
        max_rows=15,
    )

    add_heading(doc, "Supplementary Table S2. Validation summary", 1)
    add_table_from_df(doc, data["validation_summary"], "Exported validation summary from the reporting pipeline.")

    add_heading(doc, "Supplementary Table S3. Pipeline timings", 1)
    add_table_from_df(doc, data["pipeline_timings"], "End-to-end pipeline timing summary.", round_map={"elapsed_seconds": 1})

    add_heading(doc, "Supplementary Figure Notes", 1)
    notes = [
        "Figure 1 source: R_pipeline/figures/forest_plot.png",
        "Figure 2 source: R_pipeline/figures/roc_combined.png",
        "Figure 3 source: R_pipeline/figures/heatmap_signature.png",
        "Figure 4 source: R_pipeline/figures/go_bp_dotplot.png",
        "Supplementary assets are reproducibly linked to the repository and the output package in this folder.",
    ]
    for note in notes:
        add_para(doc, note)

    out_path = OUT_DIR / "03_Supplementary_Information.docx"
    doc.save(out_path)
    return out_path


def build_cover_letter() -> Path:
    doc = Document()
    set_default_style(doc)
    add_para(doc, datetime.now().strftime("%d %B %Y"))
    add_para(doc, "The Editor")
    add_para(doc, "BMC Personalized Medicine")
    add_para(doc, "Springer Nature")
    add_para(doc, "")
    add_para(doc, "Re: Submission of an original research article")
    add_para(doc, "")
    body = [
        f'I am submitting the manuscript titled "{TITLE}" for consideration as an Original Research article in BMC Personalized Medicine.',
        "This study presents a reproducible public-data workflow for identifying host blood transcriptomic biomarkers associated with tuberculosis progression. "
        "The package combines cohort curation, gene-level meta-analysis, leave-one-cohort-out validation, pathway interpretation, and a submission-ready documentation layer.",
        "The manuscript is suited to the journal because it focuses on biomarker prioritization, cross-cohort reproducibility, and translational interpretation rather than a narrow single-cohort discovery claim. "
        "The submission is especially appropriate for a methods-forward personalized-risk framing in infectious disease.",
        "This manuscript has not been published elsewhere, is not under consideration by another journal, and uses only de-identified publicly available datasets. "
        "All code, figures, tables, and documentation are available in the associated GitHub repository.",
        f"Repository: {REPO_URL}",
        f"Corresponding author: {AUTHOR['name']} ({AUTHOR['email']})",
    ]
    for paragraph in body:
        add_para(doc, paragraph)
    add_para(doc, "")
    add_para(doc, "Sincerely,")
    add_para(doc, AUTHOR["name"])
    add_para(doc, AUTHOR["department"])
    add_para(doc, AUTHOR["institution"])
    add_para(doc, f'{AUTHOR["city"]}, {AUTHOR["state"]}, {AUTHOR["country"]}')
    out_path = OUT_DIR / "04_Cover_Letter.docx"
    doc.save(out_path)
    return out_path


def build_journal_notes() -> Path:
    doc = Document()
    set_default_style(doc)
    add_para(doc, "Journal Fit and Submission Notes", bold=True, center=True)

    add_heading(doc, "Primary target journal", 1)
    add_para(
        doc,
        "BMC Personalized Medicine (Springer Nature / BMC) is the primary recommended target for this package because "
        "the manuscript is positioned as a reproducible biomarker-discovery and risk-stratification resource rather than a definitive clinical assay paper."
    )
    add_para(
        doc,
        "This package was therefore formatted as a BMC-style original research submission with a separate title page, main article, supplementary file, and cover letter."
    )

    add_heading(doc, "Cost position", 1)
    add_para(
        doc,
        "As checked on 17 March 2026 from official Springer Nature / BMC material, BMC Personalized Medicine is operating under a launch-period arrangement in which publication costs are covered until 31 December 2026. "
        "This makes it the most suitable APC-free option within the Springer Nature family for the present manuscript."
    )

    add_heading(doc, "Fallback subscription-format option", 1)
    add_para(
        doc,
        "If a more conventional subscription or hybrid journal is preferred, Infection (Springer) is the recommended fallback. "
        "It is a clinically oriented infectious-disease journal within Springer and uses Springer hybrid publishing options, so a non-open-access route remains possible."
    )

    add_heading(doc, "Repository and audit trail", 1)
    add_para(doc, f"GitHub repository: {REPO_URL}")
    add_para(
        doc,
        "All submission files in this folder were generated from repository outputs and should be cited together with the repository when the manuscript is uploaded or shared."
    )

    out_path = OUT_DIR / "05_Journal_Fit_and_Submission_Notes.docx"
    doc.save(out_path)
    return out_path


def build_readme() -> Path:
    text = textwrap.dedent(
        f"""
        # Submission-ready package

        Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        Primary target journal: BMC Personalized Medicine (Springer Nature)
        Fallback journal: Infection (Springer)
        Repository: {REPO_URL}

        Files:
        - 01_Title_Page_and_Declarations.docx
        - 02_Main_Article.docx
        - 03_Supplementary_Information.docx
        - 04_Cover_Letter.docx
        - 05_Journal_Fit_and_Submission_Notes.docx
        - submission_ready_package.zip

        Notes:
        - The manuscript is intentionally framed as a reproducible biomarker-discovery resource.
        - Figures are embedded directly in the main article DOCX.
        - Supplementary tables are included in the supplementary DOCX.
        - The package cites the GitHub repository and uses the current local author metadata.
        """
    ).strip() + "\n"
    out_path = OUT_DIR / "README.md"
    out_path.write_text(text, encoding="utf-8")
    return out_path


def zip_outputs(paths: list[Path]) -> Path:
    zip_path = OUT_DIR / "submission_ready_package.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in paths:
            zf.write(path, arcname=path.name)
    return zip_path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_inputs()
    outputs = [
        build_title_page(),
        build_main_article(data),
        build_supplement(data),
        build_cover_letter(),
        build_journal_notes(),
        build_readme(),
    ]
    outputs.append(zip_outputs(outputs))
    print("Generated submission-ready assets:")
    for path in outputs:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
