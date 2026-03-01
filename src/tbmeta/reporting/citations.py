from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import requests

SOFTWARE_BIB = [
    (
        "geoparse",
        "GeoParser: Python library to access GEO data",
        "2018",
        "https://geoparse.readthedocs.io/",
    ),
    (
        "gseapy",
        "GSEApy: Gene Set Enrichment Analysis in Python",
        "2023",
        "https://gseapy.readthedocs.io/",
    ),
]


def _fetch_pubmed(pmid: str) -> dict[str, str]:
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    r = requests.get(url, params={"db": "pubmed", "id": pmid, "retmode": "json"}, timeout=30)
    r.raise_for_status()
    j = r.json().get("result", {}).get(str(pmid), {})
    return {
        "title": j.get("title", ""),
        "year": str(j.get("pubdate", "")).split(" ")[0],
        "journal": j.get("fulljournalname", ""),
    }


def _fetch_doi(doi: str) -> dict[str, str]:
    url = f"https://api.crossref.org/works/{doi}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    msg = r.json().get("message", {})
    title = (msg.get("title") or [""])[0]
    year = str((msg.get("issued", {}).get("date-parts", [[None]])[0][0]) or "NA")
    journal = (msg.get("container-title") or [""])[0]
    return {"title": title, "year": year, "journal": journal}


def _bibtex_entry(key: str, title: str, year: str, journal: str = "", doi: str = "") -> str:
    parts = [f"@article{{{key},", f"  title = {{{title}}},", f"  year = {{{year}}},"]
    if journal:
        parts.append(f"  journal = {{{journal}}},")
    if doi:
        parts.append(f"  doi = {{{doi}}},")
    parts.append("}")
    return "\n".join(parts)


def generate_bibliography(cfg: dict[str, Any]) -> Path:
    reg_path = Path(cfg["paths"]["registry_dir"]) / "registry_curated.csv"
    out_bib = Path(cfg["citations"]["output_bib"])
    out_bib.parent.mkdir(parents=True, exist_ok=True)

    entries: list[str] = []
    if reg_path.exists():
        reg = pd.read_csv(reg_path)
        for pmid in reg["pmid"].dropna().astype(str).unique().tolist():
            try:
                md = _fetch_pubmed(pmid)
                entries.append(
                    _bibtex_entry(
                        key=f"pmid{pmid}",
                        title=md["title"] or f"PubMed {pmid}",
                        year=md["year"] or "NA",
                        journal=md["journal"],
                    )
                )
            except Exception:
                entries.append(_bibtex_entry(key=f"pmid{pmid}", title=f"PubMed {pmid}", year="NA"))
        if "doi" in reg.columns:
            for doi in reg["doi"].dropna().astype(str).unique().tolist():
                try:
                    md = _fetch_doi(doi)
                    key = doi.replace("/", "_").replace(".", "_")
                    entries.append(
                        _bibtex_entry(
                            key=f"doi_{key}",
                            title=md["title"] or doi,
                            year=md["year"],
                            journal=md["journal"],
                            doi=doi,
                        )
                    )
                except Exception:
                    key = doi.replace("/", "_").replace(".", "_")
                    entries.append(_bibtex_entry(key=f"doi_{key}", title=doi, year="NA", doi=doi))

        for gse in reg["gse_id"].dropna().astype(str).unique().tolist():
            entries.append(
                "\n".join(
                    [
                        f"@misc{{{gse},",
                        f"  title = {{{gse} dataset, NCBI GEO}},",
                        "  year = {NA},",
                        f"  howpublished = {{https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gse}}},",
                        "}",
                    ]
                )
            )

    for key, title, year, url in SOFTWARE_BIB:
        entries.append(
            "\n".join(
                [
                    f"@misc{{{key},",
                    f"  title = {{{title}}},",
                    f"  year = {{{year}}},",
                    f"  howpublished = {{{url}}},",
                    "}",
                ]
            )
        )

    out_bib.write_text("\n\n".join(entries) + "\n", encoding="utf-8")
    return out_bib
