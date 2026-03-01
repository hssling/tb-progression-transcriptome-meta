from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests

_VALID_GENE = re.compile(r"^[A-Za-z0-9\-\.]{2,20}$")


def normalize_gene_symbol(symbol: str) -> str:
    s = (symbol or "").strip().upper()
    s = s.replace(" ", "")
    if s.startswith("ENSG") and "." in s:
        s = s.split(".", 1)[0]
    return s


def load_hgnc_ensembl_mapping(cache_path: str | Path) -> dict[str, str]:
    cp = Path(cache_path)
    cp.parent.mkdir(parents=True, exist_ok=True)
    if not cp.exists():
        url = "https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt"
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        cp.write_bytes(r.content)

    df = pd.read_csv(cp, sep="\t", dtype=str, low_memory=False)
    if "ensembl_gene_id" not in df.columns or "symbol" not in df.columns:
        return {}
    sub = df[["ensembl_gene_id", "symbol"]].dropna().copy()
    sub["ensembl_gene_id"] = sub["ensembl_gene_id"].map(normalize_gene_symbol)
    sub["symbol"] = sub["symbol"].map(normalize_gene_symbol)
    sub = sub[(sub["ensembl_gene_id"] != "") & (sub["symbol"] != "")]
    sub = sub.drop_duplicates("ensembl_gene_id")
    return dict(zip(sub["ensembl_gene_id"], sub["symbol"], strict=False))


def harmonize_gene_name(name: str, ensembl_to_symbol: dict[str, str] | None = None) -> str:
    n = normalize_gene_symbol(name)
    if n.startswith("ENSG") and ensembl_to_symbol:
        return ensembl_to_symbol.get(n, n)
    return n


def map_probes_to_genes(
    expression_df: pd.DataFrame,
    annotation_df: pd.DataFrame,
    probe_col: str = "probe_id",
    gene_col: str = "gene_symbol",
    drop_ambiguous: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ann = annotation_df.copy()
    ann[gene_col] = ann[gene_col].fillna("").map(normalize_gene_symbol)
    ann = ann[ann[gene_col].map(lambda x: bool(_VALID_GENE.match(x)))]

    if drop_ambiguous:
        # Remove probes with multiple genes like "A///B" or "A;B".
        ann = ann[~ann[gene_col].str.contains(r"///|;|,|\|")]

    merged = expression_df.merge(ann[[probe_col, gene_col]], on=probe_col, how="inner")
    value_cols = [c for c in merged.columns if c not in {probe_col, gene_col}]
    gene_level = merged.groupby(gene_col, as_index=False)[value_cols].mean()

    report = pd.DataFrame(
        {
            "n_input_probes": [len(expression_df)],
            "n_mapped_probes": [len(merged)],
            "n_unique_genes": [gene_level[gene_col].nunique()],
        }
    )
    return gene_level, report
