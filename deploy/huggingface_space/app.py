from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import streamlit as st


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "tables"
FIGS = ROOT / "results" / "figures"


def _run_pipeline() -> tuple[int, str]:
    cmd = ["tbmeta", "all", "--config", "configs/config.yaml", "--force"]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + "\n" + p.stderr).strip()


st.set_page_config(page_title="TB Meta Dashboard", layout="wide")
st.title("TB Progression Transcriptome Meta-analysis")
st.caption("Hugging Face Space wrapper for results exploration and reruns.")

if st.button("Run Full Pipeline"):
    with st.spinner("Running pipeline..."):
        code, logs = _run_pipeline()
    if code == 0:
        st.success("Pipeline completed.")
    else:
        st.error(f"Pipeline failed with code {code}.")
    st.text_area("Logs", logs, height=320)

st.subheader("Key Tables")
for name in ["loco_performance.csv", "signature_genes.csv", "pathway_enrichment.csv", "window_sensitivity.csv"]:
    p = RESULTS / name
    if p.exists():
        st.markdown(f"- `{name}`")

st.subheader("Figures")
if FIGS.exists():
    for fig in sorted(FIGS.glob("*.png")):
        st.image(str(fig), caption=fig.name)
else:
    st.info("No figure outputs found yet.")
