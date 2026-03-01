from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import requests

from tbmeta.data.synthetic import generate_synthetic_cohorts
from tbmeta.utils.logging import get_logger


def _download_url(url: str, out_file: Path, timeout: int = 120) -> bool:
    try:
        r = requests.get(url, timeout=timeout)
        if not r.ok:
            return False
        out_file.write_bytes(r.content)
        return True
    except Exception:
        return False


def _download_supplementary_files(gse, out_dir: Path, logger, cfg: dict[str, Any]) -> list[Path]:
    urls = gse.metadata.get("supplementary_file", [])
    max_mb = float(cfg.get("download", {}).get("max_supplementary_mb", 120))
    skip_keywords = [str(k).lower() for k in cfg.get("download", {}).get("skip_keywords", [])]
    files: list[Path] = []
    for raw_url in urls:
        url = str(raw_url).replace("ftp://ftp.ncbi.nlm.nih.gov", "https://ftp.ncbi.nlm.nih.gov")
        name = url.split("/")[-1]
        if not name:
            continue
        lname = name.lower()
        if any(k in lname for k in skip_keywords):
            logger.info("Skipping supplementary file by keyword: %s", name)
            continue
        try:
            h = requests.head(url, timeout=30, allow_redirects=True)
            sz = float(h.headers.get("Content-Length", "0")) / (1024 * 1024)
            if sz > max_mb:
                logger.info("Skipping oversized supplementary file %s (%.1f MB)", name, sz)
                continue
        except Exception:
            pass
        out_file = out_dir / name
        if out_file.exists() and out_file.stat().st_size > 0:
            files.append(out_file)
            continue
        ok = _download_url(url, out_file)
        if ok:
            files.append(out_file)
        else:
            logger.warning("Supplementary download failed: %s", url)
    return files


def _read_expression_file(path: Path) -> pd.DataFrame | None:
    lname = path.name.lower()
    if lname.endswith(".xlsx") or lname.endswith(".xls"):
        xls = pd.ExcelFile(path)
        if not xls.sheet_names:
            return None
        return pd.read_excel(path, sheet_name=xls.sheet_names[0])
    if lname.endswith(".txt") or lname.endswith(".tsv") or lname.endswith(".txt.gz") or lname.endswith(".tsv.gz"):
        return pd.read_csv(path, sep="\t", compression="infer")
    if lname.endswith(".csv") or lname.endswith(".csv.gz"):
        return pd.read_csv(path, compression="infer")
    return None


def _norm_text(s: str) -> str:
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


def _build_metadata_from_samples(sample_names: list[str], cohort_id: str, platform_type: str, gse=None) -> pd.DataFrame:
    title_to_chars: dict[str, str] = {}
    norm_title_to_chars: dict[str, str] = {}
    if gse is not None:
        for _gsm_id, gsm in gse.gsms.items():
            title = str(gsm.metadata.get("title", [""])[0])
            chars = " | ".join(gsm.metadata.get("characteristics_ch1", []))
            title_to_chars[title] = chars
            norm_title_to_chars[_norm_text(title)] = chars

    characteristics = []
    norm_titles = list(norm_title_to_chars.keys())
    for s in sample_names:
        chars = title_to_chars.get(s)
        if chars is None:
            ns = _norm_text(s)
            chars = norm_title_to_chars.get(ns)
            if chars is None and norm_titles:
                # Fuzzy fallback for cases like sample code embedded in long title.
                for nt in norm_titles:
                    if ns and (ns in nt or nt in ns):
                        chars = norm_title_to_chars[nt]
                        break
        if chars is None:
            chars = s
        characteristics.append(chars if chars else s)

    return pd.DataFrame(
        {
            "sample_id": sample_names,
            "cohort_id": cohort_id,
            "characteristics": characteristics,
            "title": sample_names,
            "platform_type": platform_type,
        }
    )


def _try_supplementary_expression(gse, gse_id: str, out_dir: Path, logger, cfg: dict[str, Any]) -> bool:
    files = _download_supplementary_files(gse, out_dir, logger, cfg)
    if not files:
        return False

    priorities = sorted(
        files,
        key=lambda p: (
            0 if "expression" in p.name.lower() else 1,
            0 if "normalized" in p.name.lower() or "edger" in p.name.lower() else 1,
            0 if p.suffix.lower() in {".xlsx", ".xls"} else 1,
        ),
    )
    for f in priorities:
        df = _read_expression_file(f)
        if df is None or df.empty or df.shape[1] < 5:
            continue
        first_col = str(df.columns[0])
        df = df.rename(columns={first_col: "probe_id"}).copy()
        df["probe_id"] = df["probe_id"].astype(str)
        df = df[df["probe_id"].str.lower() != "nan"]
        if df.empty or len(df.columns) < 3:
            continue

        value_cols = [c for c in df.columns if c != "probe_id"]
        numeric = {}
        keep_cols: list[str] = []
        for c in value_cols:
            s = pd.to_numeric(df[c], errors="coerce")
            frac = float(s.notna().mean())
            if frac >= 0.8:
                keep_cols.append(c)
                numeric[c] = s
        if len(keep_cols) < 5:
            continue

        cols = {"probe_id": df["probe_id"]}
        cols.update({c: numeric[c] for c in keep_cols})
        expr = pd.DataFrame(cols)
        expr = expr[expr[keep_cols].notna().mean(axis=1) >= 0.8].copy()
        if expr.empty:
            continue

        expr.to_parquet(out_dir / "expression_raw.parquet", index=False)
        sample_cols = [str(c) for c in keep_cols]
        platform_type = "rnaseq" if any(k in f.name.lower() for k in ["count", "rnaseq", "edger"]) else "microarray"
        meta = _build_metadata_from_samples(sample_cols, gse_id, platform_type=platform_type, gse=gse)
        meta.to_parquet(out_dir / "metadata_raw.parquet", index=False)
        logger.info("Parsed supplementary expression for %s from %s", gse_id, f.name)
        return True
    return False


def _try_geo_download(gse_id: str, out_dir: Path, logger, cfg: dict[str, Any]) -> bool:
    try:
        import GEOparse  # type: ignore

        gse = GEOparse.get_GEO(geo=gse_id, destdir=str(out_dir), silent=True)
        try:
            table = gse.pivot_samples("VALUE")
        except Exception:
            table = None
        if table is not None and not table.empty:
            expr = table.reset_index()
            if "ID_REF" in expr.columns:
                expr = expr.rename(columns={"ID_REF": "probe_id"})
            elif "probe_id" not in expr.columns:
                expr = expr.rename(columns={expr.columns[0]: "probe_id"})
            expr.to_parquet(out_dir / "expression_raw.parquet", index=False)

            meta_rows = []
            for gsm_name, gsm in gse.gsms.items():
                chars = " | ".join(gsm.metadata.get("characteristics_ch1", []))
                meta_rows.append(
                    {
                        "sample_id": gsm_name,
                        "cohort_id": gse_id,
                        "characteristics": chars,
                        "title": gsm.metadata.get("title", [""])[0],
                        "platform_type": "microarray",
                    }
                )
            pd.DataFrame(meta_rows).to_parquet(out_dir / "metadata_raw.parquet", index=False)
            return True

        return _try_supplementary_expression(gse, gse_id, out_dir, logger, cfg)
    except Exception as exc:
        logger.warning("GEO download failed for %s: %s", gse_id, exc)
        return False


def run_download(cfg: dict[str, Any], mode: str = "full") -> pd.DataFrame:
    logger = get_logger("tbmeta.download", Path(cfg["paths"]["logs_dir"]) / "download.log")
    reg = pd.read_csv(Path(cfg["paths"]["registry_dir"]) / "registry_curated.csv")
    raw_dir = Path(cfg["paths"]["raw_data"])

    if mode == "demo":
        cids = generate_synthetic_cohorts(raw_dir, seed=int(cfg["project"]["seed"]))
        logger.info("Generated synthetic cohorts: %s", cids)
        return reg

    downloaded = 0
    for idx, row in reg.iterrows():
        gse = str(row["gse_id"])
        cdir = raw_dir / gse
        cdir.mkdir(parents=True, exist_ok=True)

        if row.get("status") in {"skipped", "needs_review"}:
            reg.at[idx, "reason_skipped"] = row.get("reason_skipped") or "not_curated"
            continue

        ok = False
        if cfg["download"]["allow_geo"] and gse.startswith("GSE"):
            ok = _try_geo_download(gse, cdir, logger, cfg)

        if not ok and mode == "demo" and cfg["download"]["synthetic_if_missing"]:
            generate_synthetic_cohorts(raw_dir, seed=int(cfg["project"]["seed"]))
            ok = True

        if ok:
            reg.at[idx, "status"] = "downloaded"
            downloaded += 1
        else:
            reg.at[idx, "status"] = "skipped"
            reg.at[idx, "reason_skipped"] = "download_failed_or_unsupported_format"

    reg.to_csv(Path(cfg["paths"]["registry_dir"]) / "registry_curated.csv", index=False)
    logger.info("Downloaded/synthesized cohorts: %d", downloaded)
    return reg
