from __future__ import annotations

from pathlib import Path
import shutil
import zipfile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "submission_ready" / "advanced_tb_systems_20260317"
OUT_DIR = ROOT / "submission_ready" / "bmc_med_genomics_advanced_20260318"
REPO_URL = "https://github.com/hssling/tb-progression-transcriptome-meta"


def set_style(doc: Document) -> None:
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    style.paragraph_format.line_spacing = 1.5
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)


def add_paragraph(doc: Document, text: str, bold: bool = False, center: bool = False) -> None:
    p = doc.add_paragraph()
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = bold


def build_journal_note() -> Path:
    doc = Document()
    set_style(doc)
    add_paragraph(doc, "BMC Medical Genomics Submission Notes", bold=True, center=True)
    add_paragraph(doc, "Target journal: BMC Medical Genomics")
    add_paragraph(doc, "Target article type: Research article")
    add_paragraph(doc, "")
    add_paragraph(doc, "Why this journal fits", bold=True)
    for line in [
        "The manuscript is a genomics-focused original research article centered on host blood transcriptomics, cross-cohort harmonization, biomarker biology, and reproducible secondary analysis.",
        "The article uses IMRAD structure, includes declarations required by BMC journals, and provides explicit data and code availability statements.",
        "The expanded article length is compatible with a full research article format and is not constrained to the shorter limits typical of some specialty TB journals.",
    ]:
        doc.add_paragraph(line, style="List Bullet")
    add_paragraph(doc, "")
    add_paragraph(doc, "Package contents", bold=True)
    for line in [
        "01_BMC_Title_Page.docx",
        "02_BMC_Main_Manuscript.docx",
        "03_BMC_Cover_Letter.docx",
        "04_BMC_Supplementary_Methods_and_Figures.docx",
        "05_BMC_OmicsClaw_Extensions.docx",
        "06_BMC_Submission_Notes.docx",
    ]:
        doc.add_paragraph(line, style="List Bullet")
    add_paragraph(doc, "")
    add_paragraph(doc, "Official sources checked on March 18, 2026", bold=True)
    for line in [
        "Journal homepage: https://bmcmedgenomics.biomedcentral.com/",
        "Submission guidelines: https://bmcmedgenomics.biomedcentral.com/submission-guidelines/preparing-your-manuscript",
        "Editorial policies: https://www.biomedcentral.com/getpublished/editorial-policies",
        "Research article guidance: https://bmcmedgenomics.biomedcentral.com/submission-guidelines/preparing-your-manuscript/research-article",
    ]:
        doc.add_paragraph(line, style="List Bullet")
    add_paragraph(doc, "")
    add_paragraph(doc, "Repository", bold=True)
    add_paragraph(doc, REPO_URL)
    out = OUT_DIR / "06_BMC_Submission_Notes.docx"
    doc.save(out)
    return out


def build_cover_letter() -> Path:
    doc = Document()
    set_style(doc)
    add_paragraph(doc, "Cover Letter", bold=True, center=True)
    add_paragraph(doc, "Dear Editors of BMC Medical Genomics,")
    add_paragraph(
        doc,
        "Please consider our manuscript, "
        "\"Bayesian and systems-level reanalysis of public tuberculosis progression transcriptomes reveals latent host-response programs,\" "
        "as a Research article."
    )
    add_paragraph(
        doc,
        "This manuscript presents an expanded systems-level reanalysis of public tuberculosis progression transcriptomic cohorts. "
        "The study combines Bayesian synthesis, latent factor analysis, pathway modeling, marker-based deconvolution, coexpression analysis, "
        "and sensitivity expansion through remapping of a junction-level RNA-sequencing cohort. The work is positioned as a genomics-focused "
        "biological and methodological contribution rather than as a clinical deployment paper."
    )
    add_paragraph(
        doc,
        "All data analyzed are publicly available, and the analytical code and generated outputs are available in the accompanying repository. "
        "The manuscript is not under consideration elsewhere."
    )
    add_paragraph(doc, "Sincerely,")
    add_paragraph(doc, "Siddalingaiah H S, MD")
    out = OUT_DIR / "03_BMC_Cover_Letter.docx"
    doc.save(out)
    return out


def copy_package_files() -> None:
    mapping = {
        "01_Title_Page.docx": "01_BMC_Title_Page.docx",
        "02_Manuscript.docx": "02_BMC_Main_Manuscript.docx",
        "04_Supplementary_Methods_and_Figures.docx": "04_BMC_Supplementary_Methods_and_Figures.docx",
        "06_OmicsClaw_Extensions.docx": "05_BMC_OmicsClaw_Extensions.docx",
        "03_Highlights.docx": "07_BMC_Highlights.docx",
        "validation_report.txt": "validation_report.txt",
        "internal_review_log.md": "internal_review_log.md",
    }
    for src_name, dst_name in mapping.items():
        src = SRC_DIR / src_name
        if src.exists():
            shutil.copy2(src, OUT_DIR / dst_name)


def build_readme() -> Path:
    text = "\n".join(
        [
            "# BMC Medical Genomics Advanced Submission Package",
            "",
            "Source manuscript package: submission_ready/advanced_tb_systems_20260317",
            "Target journal: BMC Medical Genomics",
            "Article type: Research article",
            f"Repository: {REPO_URL}",
            "",
            "This package repackages the expanded advanced manuscript for BMC Medical Genomics using current official journal guidance checked on March 18, 2026.",
        ]
    )
    out = OUT_DIR / "README.md"
    out.write_text(text + "\n", encoding="utf-8")
    return out


def zip_package() -> None:
    zip_path = OUT_DIR / "bmc_med_genomics_advanced_submission_package.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(OUT_DIR.iterdir()):
            if path == zip_path:
                continue
            zf.write(path, arcname=path.name)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    copy_package_files()
    build_cover_letter()
    build_journal_note()
    build_readme()
    zip_package()
    print(f"BMC Medical Genomics package written to {OUT_DIR}")


if __name__ == "__main__":
    main()
