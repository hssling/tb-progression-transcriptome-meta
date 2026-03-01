from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_fixed

from tbmeta.data.schemas import validate_registry_schema
from tbmeta.utils.logging import get_logger

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def _get(url: str, params: dict[str, Any], timeout: int = 40) -> dict[str, Any]:
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _search_gse(term: str, email: str, tool: str, retmax: int) -> list[str]:
    payload = _get(
        f"{EUTILS_BASE}/esearch.fcgi",
        {
            "db": "gds",
            "term": f"({term}) AND gse[ETYP]",
            "retmode": "json",
            "retmax": retmax,
            "email": email,
            "tool": tool,
        },
    )
    return payload.get("esearchresult", {}).get("idlist", [])


def _summary(ids: list[str], email: str, tool: str) -> list[dict[str, Any]]:
    if not ids:
        return []
    payload = _get(
        f"{EUTILS_BASE}/esummary.fcgi",
        {
            "db": "gds",
            "id": ",".join(ids),
            "retmode": "json",
            "email": email,
            "tool": tool,
        },
    )
    out: list[dict[str, Any]] = []
    result = payload.get("result", {})
    for gid in result.get("uids", []):
        rec = result.get(gid, {})
        acc = rec.get("accession", "")
        if not str(acc).startswith("GSE"):
            continue
        out.append(
            {
                "gse_id": acc,
                "title": rec.get("title", ""),
                "organism": rec.get("taxon", ""),
                "platform": rec.get("gpl", ""),
                "n_samples": rec.get("n_samples", 0),
                "pmid": rec.get("pubmedids", [None])[0],
                "summary": rec.get("summary", ""),
                "supplementary_files": "",
            }
        )
    return out


def _heuristic_status(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        text = f"{r['title']} {r.get('summary', '')}".lower()
        ok_org = "homo sapiens" in str(r["organism"]).lower() or "human" in text
        blood_like = any(k in text for k in ["blood", "pbmc", "whole blood"])
        progress_like = any(k in text for k in ["progress", "incident", "risk", "household", "latent"])
        status = "candidate" if ok_org and blood_like and progress_like else "needs_review"
        reason = "" if status == "candidate" else "heuristics_not_met"
        rows.append({**r.to_dict(), "status": status, "reason_skipped": reason})
    return pd.DataFrame(rows)


def synthetic_registry() -> pd.DataFrame:
    df = pd.DataFrame(
        [
            {
                "gse_id": "SYNTH_COHORT_A",
                "title": "Synthetic TB progression cohort A",
                "organism": "Homo sapiens",
                "platform": "SYNTH_MICROARRAY",
                "n_samples": 80,
                "pmid": None,
                "summary": "Synthetic baseline blood expression progression labels",
                "supplementary_files": "",
                "status": "candidate",
                "reason_skipped": "",
            },
            {
                "gse_id": "SYNTH_COHORT_B",
                "title": "Synthetic TB progression cohort B",
                "organism": "Homo sapiens",
                "platform": "SYNTH_RNASEQ",
                "n_samples": 70,
                "pmid": None,
                "summary": "Synthetic longitudinal PBMC progression labels",
                "supplementary_files": "",
                "status": "candidate",
                "reason_skipped": "",
            },
        ]
    )
    return df


def run_discovery(cfg: dict[str, Any], mode: str = "full") -> pd.DataFrame:
    logger = get_logger("tbmeta.discovery", Path(cfg["paths"]["logs_dir"]) / "discover.log")
    out_raw = Path(cfg["paths"]["registry_dir"]) / "registry_raw.csv"
    cache_json = Path(cfg["paths"]["cache_dir"]) / "discover_cache.json"

    if mode == "demo" or not cfg["discovery"]["enabled"]:
        df = synthetic_registry()
        df.to_csv(out_raw, index=False)
        validate_registry_schema(df)
        return df

    if cache_json.exists():
        logger.info("Loading discovery cache from %s", cache_json)
        data = json.loads(cache_json.read_text(encoding="utf-8"))
        df = pd.DataFrame(data)
        df = _heuristic_status(df)
        df.to_csv(out_raw, index=False)
        validate_registry_schema(df)
        return df

    terms = cfg["discovery"]["query_terms"]
    email = cfg["discovery"]["email"]
    tool = cfg["discovery"]["tool"]
    max_gse = int(cfg["discovery"]["max_gse"])
    delay = float(cfg["discovery"]["rate_limit_seconds"])

    all_records: list[dict[str, Any]] = []
    try:
        for term in terms:
            ids = _search_gse(term, email, tool, max_gse)
            if ids:
                all_records.extend(_summary(ids, email, tool))
            time.sleep(delay)
    except Exception as exc:
        logger.warning("Discovery failed (%s), using synthetic fallback", exc)
        df = synthetic_registry()
        df.to_csv(out_raw, index=False)
        validate_registry_schema(df)
        return df

    if not all_records:
        df = synthetic_registry()
    else:
        df = pd.DataFrame(all_records).drop_duplicates(subset=["gse_id"])
        df = _heuristic_status(df)

    cache_json.parent.mkdir(parents=True, exist_ok=True)
    cache_json.write_text(df.to_json(orient="records"), encoding="utf-8")
    out_raw.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_raw, index=False)
    validate_registry_schema(df)
    logger.info("Discovered %d candidate datasets", len(df))
    return df
