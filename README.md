# tb-progression-transcriptome-meta

End-to-end, reproducible, agentic pipeline to discover public TB progression transcriptomic cohorts, harmonize RNA-seq/microarray data, run meta-analysis + cross-study ML, and auto-generate figures, dashboard outputs, citations, and manuscript drafts.

## Quickstart

```bash
make setup
make demo
make all
```

- `make demo` always runs offline using synthetic cohorts.
- `make all` uses `configs/config.yaml` defaults (resume enabled).

## CLI

```bash
tbmeta discover --config configs/config.yaml
tbmeta curate --config configs/config.yaml
tbmeta download --config configs/config.yaml
tbmeta preprocess --config configs/config.yaml
tbmeta analyze --config configs/config.yaml
tbmeta manuscript --config configs/config.yaml
tbmeta citations --config configs/config.yaml
tbmeta submission --config configs/config.yaml
tbmeta dashboard --config configs/config.yaml
tbmeta openclaw-check --config configs/config.yaml
tbmeta all --config configs/config.yaml
```

## Repository Structure

- `src/tbmeta/`: Python package
- `pipelines/`: pipeline entry wrappers
- `scripts/`: utility scripts
- `app/`: Streamlit app
- `data/raw`: downloaded/raw cohort files
- `data/registry`: discovery + curated registry CSVs
- `data/processed`: harmonized cohort parquet objects
- `results/tables|figures|models|logs`: analysis outputs and logs/checkpoints
- `manuscripts/`: auto-generated manuscript drafts
- `tests/`: unit tests

## Single Config Control

All settings are in [configs/config.yaml](/d:/research-automation/TB%20multiomics/tb%20progression%20transcriptomic/configs/config.yaml):

- discovery query terms + rate limits
- curation thresholds + manual override CSV
- preprocess options + outcome window/baseline strategy
- model list and LOCO settings
- runtime resume/checkpoint behavior
- optional OpenClaw integration settings (`openclaw.*`)

## OpenClaw Setup

```bash
python -m pip install openclaw
tbmeta openclaw-check --config configs/config.yaml
```

Optional config keys in [configs/config.yaml](/d:/research-automation/TB%20multiomics/tb%20progression%20transcriptomic/configs/config.yaml):
- `openclaw.enabled`
- `openclaw.endpoint`
- `openclaw.endpoint_env`
- `openclaw.provider`
- `openclaw.model`
- `openclaw.openai_api_key_env`
- `openclaw.api_key_env`
- `openclaw.timeout_seconds`

Environment-first setup:
```bash
copy .env.example .env
# set OPENAI_API_KEY (and optionally OPENCLAW_ENDPOINT / OPENCLAW_API_KEY)
tbmeta openclaw-check --config configs/config.yaml
```

## Inclusion Criteria Encoded

- Human host blood/PBMC transcriptomics
- Progression-relevant outcome labels or incident TB mapping
- Metadata needed for baseline and outcome harmonization
- Microarray and RNA-seq supported
- Registry includes `status` and `reason_skipped` for explicit failures

## Expected Outputs

- Registry: `data/registry/registry_raw.csv`, `data/registry/registry_curated.csv`
- Processed cohort objects: `data/processed/<cohort_id>/expression.parquet`, `metadata.parquet`
- DE + meta-analysis: `results/tables/within_cohort_de.csv`, `meta_analysis.csv`
- Sensitivity: `results/tables/meta_leave_one_cohort_out.csv`
- Signature + interpretability: `results/tables/signature_genes.csv`, `shap_like_importance.csv`
- Performance: LOCO/random split tables + ROC/PR/calibration/DCA plots
- Enrichment: `results/tables/pathway_enrichment.csv`, `pathway_dotplot.png`
- Manuscripts: `manuscripts/manuscript.md`, `manuscripts/supplementary_methods.md`
- References: `manuscripts/references.bib`
- Submission bundle: `submissions/tbmeta_submission_<timestamp>.zip`

## Custom Cohort List

Option 1: provide a curated CSV and set in config:

```yaml
curation:
  curated_csv: path/to/my_registry.csv
```

Option 2: run `tbmeta discover`, manually edit `data/registry/registry_curated.csv`, then continue from `tbmeta download`.

## Common Failure Modes

- Missing GEO expression matrix: downloader falls back to supplementary/synthetic mode and records skip reason.
- Missing platform annotation or unmappable probes: cohort is flagged/partially processed with mapping report.
- Incomplete metadata: heuristics parse `characteristics`; unresolved samples are excluded and logged.
- Limited internet in CI/laptops: `--mode demo` is fully offline and testable.

## Ethical Note

This project uses public de-identified datasets for research automation and method development only. It does not provide clinical diagnosis or treatment recommendations.

## Development

```bash
pre-commit install
make lint
make test
```

## CI/CD

- `.github/workflows/ci.yml`: lint + tests on push/PR
- `.github/workflows/weekly.yml`: scheduled weekly pipeline run (demo by default, full if secret present)
- `.github/workflows/pages.yml`: publish result bundle to GitHub Pages
- `.github/workflows/hf-space.yml`: sync Streamlit Space assets (requires `HF_TOKEN`, `HF_SPACE_ID`)
- `.github/workflows/kaggle.yml`: push Kaggle notebook kernel (requires `KAGGLE_USERNAME`, `KAGGLE_KEY`)

## External Compute

- Hugging Face Space assets: `deploy/huggingface_space/`
- Kaggle kernel assets: `kaggle/kernel-metadata.json`, `kaggle/notebook/tbmeta_kaggle_training.ipynb`
- Helper scripts:
  - `scripts/publish_hf_space.ps1`
  - `scripts/publish_kaggle.ps1`
