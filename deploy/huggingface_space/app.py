from __future__ import annotations

from pathlib import Path
import subprocess
import shutil

import streamlit as st


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results" / "tables"
FIGS = ROOT / "results" / "figures"
HAS_TBMETA = shutil.which("tbmeta") is not None


def _run_pipeline() -> tuple[int, str]:
    if not HAS_TBMETA:
        return 127, "tbmeta CLI is not installed in this Space image."
    cmd = ["tbmeta", "all", "--config", "configs/config.yaml", "--force"]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + "\n" + p.stderr).strip()


st.set_page_config(page_title="TB Meta Dashboard", layout="wide")
st.title("TB Progression Transcriptome Meta-analysis")
st.caption("Hugging Face Space wrapper for artifact exploration.")

if HAS_TBMETA and st.button("Run Full Pipeline"):
    with st.spinner("Running pipeline..."):
        code, logs = _run_pipeline()
    if code == 0:
        st.success("Pipeline completed.")
    else:
        st.error(f"Pipeline failed with code {code}.")
    st.text_area("Logs", logs, height=320)
elif not HAS_TBMETA:
    st.info("This Space is running in artifact-view mode. Pipeline execution is disabled.")

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
