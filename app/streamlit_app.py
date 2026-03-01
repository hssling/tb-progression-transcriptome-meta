from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="TB Meta", layout="wide")
st.title("TB Progression Transcriptome Meta-analysis")

REG = Path("data/registry/registry_curated.csv")
TABLES = Path("results/tables")
FIGS = Path("results/figures")
PROCESSED = Path("data/processed")


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


tabs = st.tabs(["Registry", "Cohort QC", "Meta-analysis", "Signature performance", "Gene explorer", "Downloads"])

with tabs[0]:
    st.subheader("Registry")
    reg = read_csv(REG)
    st.dataframe(reg, use_container_width=True)

with tabs[1]:
    st.subheader("Cohort QC")
    cohorts = [p.name for p in PROCESSED.iterdir() if p.is_dir()] if PROCESSED.exists() else []
    st.write(f"Processed cohorts: {len(cohorts)}")
    for c in cohorts:
        m = PROCESSED / c / "metadata.parquet"
        e = PROCESSED / c / "expression.parquet"
        if m.exists() and e.exists():
            meta = pd.read_parquet(m)
            expr = pd.read_parquet(e)
            st.write({"cohort": c, "n_samples": len(meta), "n_genes": len(expr.columns) - 1})

with tabs[2]:
    st.subheader("Meta-analysis")
    st.dataframe(read_csv(TABLES / "meta_analysis.csv"), use_container_width=True)
    forest = FIGS / "forest_top_genes.png"
    if forest.exists():
        st.image(str(forest))

with tabs[3]:
    st.subheader("Signature performance")
    st.dataframe(read_csv(TABLES / "loco_performance.csv"), use_container_width=True)
    for p in sorted(FIGS.glob("roc_*.png")):
        st.image(str(p))
    for p in sorted(FIGS.glob("pr_*.png")):
        st.image(str(p))
    for p in sorted(FIGS.glob("calibration_*.png")):
        st.image(str(p))

with tabs[4]:
    st.subheader("Gene explorer")
    sig = read_csv(TABLES / "signature_genes.csv")
    if sig.empty:
        st.info("Run `tbmeta analyze` first.")
    else:
        gene = st.selectbox("Gene", sig["gene"].tolist())
        st.dataframe(sig[sig["gene"] == gene])

with tabs[5]:
    st.subheader("Downloads")
    for p in sorted(TABLES.glob("*.csv")):
        st.download_button(label=f"Download {p.name}", data=p.read_bytes(), file_name=p.name)
