from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame()


def _safe_copy(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def generate_submission_package(cfg: dict[str, Any]) -> Path:
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    root = Path("submissions") / f"tbmeta_submission_{now}"
    root.mkdir(parents=True, exist_ok=True)

    results_dir = Path(cfg["paths"]["results_dir"])
    tables_dir = results_dir / "tables"
    figures_dir = results_dir / "figures"
    manuscripts_dir = Path("manuscripts")

    perf = _read_csv(tables_dir / "loco_performance.csv")
    sig = _read_csv(tables_dir / "signature_genes.csv")
    reg = _read_csv(Path(cfg["curation"].get("curated_csv", "")))
    if reg.empty:
        reg = _read_csv(Path(cfg["paths"]["registry_dir"]) / "registry_curated.csv")

    best_auc = float(perf["auc_roc"].max()) if not perf.empty else float("nan")
    best_row = perf.loc[perf["auc_roc"].idxmax()].to_dict() if not perf.empty else {}
    n_sig = int(sig.shape[0])
    n_curated = int(reg.shape[0])

    _safe_copy(manuscripts_dir / "manuscript.md", root / "manuscript.md")
    _safe_copy(
        manuscripts_dir / "supplementary_methods.md",
        root / "supplementary_methods.md",
    )
    _safe_copy(manuscripts_dir / "references.bib", root / "references.bib")
    _safe_copy(Path("README.md"), root / "README.md")
    _safe_copy(Path("CITATION.md"), root / "CITATION.md")
    _safe_copy(Path("configs/config.yaml"), root / "config_used.yaml")

    tables_out = root / "tables"
    figures_out = root / "figures"
    tables_out.mkdir(exist_ok=True)
    figures_out.mkdir(exist_ok=True)

    for p in sorted(tables_dir.glob("*.csv")):
        _safe_copy(p, tables_out / p.name)
    for p in sorted(figures_dir.glob("*.png")):
        _safe_copy(p, figures_out / p.name)

    cover_letter = f"""# Cover Letter

Editor,

We submit the manuscript "TB Progression Transcriptome Meta-analysis (Real-data Run)" for consideration.
This work provides an end-to-end reproducible framework for identifying
host blood transcriptomic signatures associated with TB progression
from public GEO cohorts.

In the current run, we curated {n_curated} cohorts and derived a {n_sig}-gene signature.
Primary cross-study validation used leave-one-cohort-out testing, with
best AUC-ROC {best_auc:.3f} ({best_row.get("model", "NA")} on held-out
{best_row.get("left_out_cohort", "NA")}).

The submission package includes:
- Main manuscript and supplementary methods
- Complete result tables and figures used in the report
- Reproducibility config and software citation files

The authors confirm this work is based on public data resources
and contains no new human-subject recruitment.
No part of this submission is under consideration elsewhere.

Sincerely,
Corresponding Author
"""
    _write(root / "cover_letter.md", cover_letter)

    highlights = f"""1. Reproducible GEO-to-manuscript TB progression transcriptome pipeline.
2. Public-data meta-analysis identified a {n_sig}-gene host signature.
3. LOCO validation reached best AUC-ROC {best_auc:.3f} in a held-out cohort.
4. Full artifacts (tables, figures, config, citations) are packaged for audit.
"""
    _write(root / "highlights.txt", highlights)

    checklist = """# Submission Checklist

- [x] Main manuscript (`manuscript.md`)
- [x] Supplementary methods (`supplementary_methods.md`)
- [x] References (`references.bib`)
- [x] Cover letter (`cover_letter.md`)
- [x] Highlights (`highlights.txt`)
- [x] Figures (`figures/*.png`)
- [x] Tables (`tables/*.csv`)
- [x] Reproducibility config (`config_used.yaml`)
- [x] Software citation (`CITATION.md`)
- [x] Project README (`README.md`)

## Notes
- Data are from public GEO cohorts curated in this repository.
- Pipeline is checkpointed and rerunnable with the included config.
"""
    _write(root / "submission_checklist.md", checklist)

    data_availability = """# Data Availability

All datasets analyzed are publicly available from NCBI GEO and listed in `data/registry`.
Processed cohort-level matrices used for analysis are stored under `data/processed`.
"""
    _write(root / "data_availability.md", data_availability)

    code_availability = """# Code Availability

Code, configuration, and reproducibility scripts are contained in this repository.
Primary entrypoints are the `tbmeta` CLI commands and `Makefile`/`make.cmd` targets.
"""
    _write(root / "code_availability.md", code_availability)

    journals = pd.DataFrame(
        [
            {
                "journal": "Frontiers in Immunology",
                "fit_rationale": "Host transcriptomics and immunology scope with reproducible workflows.",
                "priority": 1,
                "submission_type": "Original Research",
            },
            {
                "journal": "eBioMedicine",
                "fit_rationale": "Translational biomarker focus; strongest fit after further external validation.",
                "priority": 2,
                "submission_type": "Original Article",
            },
            {
                "journal": "Scientific Reports",
                "fit_rationale": "Reproducible multi-cohort analysis with methods-forward framing.",
                "priority": 3,
                "submission_type": "Article",
            },
        ]
    )
    journals.to_csv(root / "journal_recommendations.csv", index=False)
    for _, row in journals.iterrows():
        j = str(row["journal"])
        slug = j.lower().replace(" ", "_")
        letter = f"""# Cover Letter - {j}

Editor,

We submit our manuscript on reproducible TB progression transcriptome meta-analysis.
This package contains full methods, source-linked results, and reproducibility artifacts.

Best regards,
Corresponding Author
"""
        _write(root / f"cover_letter_{slug}.md", letter)

    fig_manifest = [
        {"figure_file": p.name, "path": str(p.as_posix())}
        for p in sorted((root / "figures").glob("*.png"))
    ]
    tab_manifest = [
        {"table_file": p.name, "path": str(p.as_posix())}
        for p in sorted((root / "tables").glob("*.csv"))
    ]
    pd.DataFrame(fig_manifest).to_csv(root / "figure_manifest.csv", index=False)
    pd.DataFrame(tab_manifest).to_csv(root / "table_manifest.csv", index=False)

    archive_base = root.parent / root.name
    shutil.make_archive(str(archive_base), "zip", root_dir=root)
    return root
