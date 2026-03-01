from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tbmeta.data.gene_mapping import harmonize_gene_name, load_hgnc_ensembl_mapping
from tbmeta.utils.logging import get_logger


def _extract_progressor_from_text(text: str, pos_labels: list[str], neg_labels: list[str]) -> int | None:
    t = (text or "").lower()
    t_norm = t.replace("-", "").replace("_", "").replace(" ", "")
    # Check negatives first to avoid matching "progressor" inside "non-progressor".
    if any(lbl.replace("-", "").replace("_", "").replace(" ", "") in t_norm for lbl in neg_labels):
        return 0
    if any(lbl.replace("-", "").replace("_", "").replace(" ", "") in t_norm for lbl in pos_labels):
        return 1
    return None


def _normalize_expression(expr: pd.DataFrame, platform_type: str) -> pd.DataFrame:
    df = expr.copy()
    num_cols = [c for c in df.columns if c != "sample_id"]
    for c in num_cols:
        if not pd.api.types.is_numeric_dtype(df[c]):
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Remove non-numeric/annotation features and impute sparse missing values.
    keep_cols = [c for c in num_cols if df[c].notna().mean() >= 0.8]
    if not keep_cols:
        keep_cols = [c for c in num_cols if df[c].notna().sum() > 0]
    df = df[["sample_id", *keep_cols]].copy()
    for c in keep_cols:
        med = float(df[c].median()) if df[c].notna().any() else 0.0
        df[c] = df[c].fillna(med)

    num_cols = keep_cols
    x = df[num_cols].to_numpy(dtype=float)

    if platform_type == "rnaseq":
        x = np.clip(x, 0, None)
        libsize = np.clip(x.sum(axis=1), 1e-6, None)
        size_factor = libsize / np.median(libsize)
        x = x / size_factor[:, None]
        x = np.log2(x + 1.0)
    else:
        ranks = np.argsort(np.argsort(x, axis=0), axis=0)
        mean_sorted = np.mean(np.sort(x, axis=0), axis=1)
        x = mean_sorted[ranks]

    df[num_cols] = x
    return df


def _baseline_filter(meta: pd.DataFrame, strategy: str) -> pd.DataFrame:
    m = meta.copy()
    if "timepoint_month" not in m.columns:
        m["timepoint_month"] = 0

    if strategy == "earliest":
        idx = m.sort_values("timepoint_month").groupby("sample_id").head(1).index
        return m.loc[idx].reset_index(drop=True)
    if strategy == "baseline_only":
        return m[m["timepoint_month"] == m["timepoint_month"].min()].reset_index(drop=True)
    if strategy == "longitudinal_delta":
        subj_col = "participant_id" if "participant_id" in m.columns else "sample_id"
        rows = []
        for _, sub in m.sort_values("timepoint_month").groupby(subj_col):
            if len(sub) < 2:
                rows.append(sub.iloc[0].to_dict())
                continue
            first = sub.iloc[0].copy()
            last = sub.iloc[-1]
            first["timepoint_month"] = int(last["timepoint_month"])
            rows.append(first.to_dict())
        return pd.DataFrame(rows)
    return m.reset_index(drop=True)


def _load_raw_cohort(cohort_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    expr = pd.read_parquet(cohort_dir / "expression_raw.parquet")
    meta = pd.read_parquet(cohort_dir / "metadata_raw.parquet")
    return expr, meta


def preprocess_cohort(cohort_dir: Path, out_root: Path, cfg: dict[str, Any]) -> str | None:
    logger = get_logger("tbmeta.preprocess", Path(cfg["paths"]["logs_dir"]) / "preprocess.log")
    cohort_id = cohort_dir.name
    expr, meta = _load_raw_cohort(cohort_dir)

    if "sample_id" not in expr.columns:
        if "probe_id" in expr.columns:
            # GEOparse pivot format: rows probes, columns samples.
            expr = expr.set_index("probe_id").T.reset_index().rename(columns={"index": "sample_id"})
        else:
            expr = expr.reset_index().rename(columns={"index": "sample_id"})

    if "progressor" not in meta.columns:
        joined = meta.get("characteristics", pd.Series([""] * len(meta))).astype(str)
        progress = [
            _extract_progressor_from_text(
                txt,
                cfg["outcome"]["positive_labels"],
                cfg["outcome"]["negative_labels"],
            )
            for txt in joined
        ]
        meta["progressor"] = progress

    meta = meta.dropna(subset=["progressor"]).copy()
    if meta.empty:
        logger.warning("Skipping %s: no samples with resolvable progressor labels", cohort_id)
        return None
    meta["progressor"] = meta["progressor"].astype(int)

    platform = str(meta.get("platform_type", pd.Series(["microarray"])).iloc[0]).lower()
    platform = "rnaseq" if "rna" in platform else "microarray"

    expr_cols = [c for c in expr.columns if c != "sample_id"]
    ensembl_map: dict[str, str] = {}
    if bool(cfg.get("preprocess", {}).get("convert_ensembl_to_hgnc", True)):
        cache_file = Path(cfg["paths"]["cache_dir"]) / "hgnc_complete_set.txt"
        try:
            ensembl_map = load_hgnc_ensembl_mapping(cache_file)
        except Exception as exc:
            logger.warning("HGNC mapping unavailable for %s: %s", cohort_id, exc)
            ensembl_map = {}
    rename_map = {c: harmonize_gene_name(str(c), ensembl_map) for c in expr_cols}
    expr = expr.rename(columns=rename_map)
    if expr.columns.duplicated().any():
        # Collapse duplicate genes introduced by ID harmonization.
        sid = expr["sample_id"].copy()
        mat = expr.drop(columns=["sample_id"])
        mat = mat.T.groupby(level=0).mean().T
        expr = pd.concat([sid, mat], axis=1)
    expr = expr.loc[:, ~expr.columns.duplicated()]

    expr = _normalize_expression(expr, platform)
    if "timepoint_month" not in meta.columns:
        meta["timepoint_month"] = 0
    meta = _baseline_filter(meta, cfg["outcome"]["baseline_strategy"])

    merged_ids = sorted(set(expr["sample_id"]).intersection(set(meta["sample_id"])))
    if not merged_ids:
        logger.warning("Skipping %s: no overlapping sample IDs between expression and metadata", cohort_id)
        return None
    expr = expr[expr["sample_id"].isin(merged_ids)].sort_values("sample_id")
    meta = meta[meta["sample_id"].isin(merged_ids)].sort_values("sample_id")

    out_dir = out_root / cohort_id
    out_dir.mkdir(parents=True, exist_ok=True)
    expr.to_parquet(out_dir / "expression.parquet", index=False)
    meta.to_parquet(out_dir / "metadata.parquet", index=False)

    map_report = pd.DataFrame(
        [{"cohort_id": cohort_id, "platform_type": platform, "n_samples": len(meta), "n_genes": len(expr.columns) - 1}]
    )
    map_report.to_csv(out_dir / "mapping_report.csv", index=False)
    logger.info("Preprocessed %s with %d samples and %d genes", cohort_id, len(meta), len(expr.columns) - 1)
    return cohort_id


def run_preprocess(cfg: dict[str, Any]) -> list[str]:
    raw_dir = Path(cfg["paths"]["raw_data"])
    out_root = Path(cfg["paths"]["processed_data"])
    out_root.mkdir(parents=True, exist_ok=True)
    reg_path = Path(cfg["paths"]["registry_dir"]) / "registry_curated.csv"

    allowed_ids: set[str] | None = None
    if reg_path.exists():
        reg = pd.read_csv(reg_path)
        if {"gse_id", "status"}.issubset(reg.columns):
            allowed_ids = set(reg.loc[reg["status"] == "downloaded", "gse_id"].astype(str).tolist())

    cohort_ids: list[str] = []
    for cdir in sorted(raw_dir.iterdir()):
        if not cdir.is_dir():
            continue
        if allowed_ids is not None and cdir.name not in allowed_ids:
            continue
        if not (cdir / "expression_raw.parquet").exists() or not (cdir / "metadata_raw.parquet").exists():
            continue
        cid = preprocess_cohort(cdir, out_root, cfg)
        if cid is not None:
            cohort_ids.append(cid)

    return cohort_ids


def load_processed_cohorts(processed_dir: str | Path) -> dict[str, tuple[pd.DataFrame, pd.DataFrame]]:
    out: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
    for cdir in sorted(Path(processed_dir).iterdir()):
        if not cdir.is_dir():
            continue
        ep = cdir / "expression.parquet"
        mp = cdir / "metadata.parquet"
        if ep.exists() and mp.exists():
            out[cdir.name] = (pd.read_parquet(ep), pd.read_parquet(mp))
    return out


def harmonize_feature_space(cohorts: dict[str, tuple[pd.DataFrame, pd.DataFrame]]) -> tuple[dict[str, pd.DataFrame], list[str]]:
    if not cohorts:
        return {}, []

    remaining = dict(cohorts)
    common: list[str] = []
    while len(remaining) >= 2:
        gene_sets = {cid: (set(expr.columns) - {"sample_id"}) for cid, (expr, _) in remaining.items()}
        inter = set.intersection(*gene_sets.values())
        if inter:
            common = sorted(inter)
            break
        # Drop smallest feature-space cohort to avoid zero-overlap collapse.
        drop_cid = min(gene_sets, key=lambda cid: len(gene_sets[cid]))
        remaining.pop(drop_cid, None)

    if not common and len(remaining) == 1:
        only_cid, (only_expr, _) = next(iter(remaining.items()))
        common = sorted(set(only_expr.columns) - {"sample_id"})
        remaining = {only_cid: (only_expr, cohorts[only_cid][1])}

    harmonized: dict[str, pd.DataFrame] = {}
    for cid, (expr, _) in remaining.items():
        h = expr[["sample_id", *common]].copy()
        harmonized[cid] = h
    return harmonized, common
