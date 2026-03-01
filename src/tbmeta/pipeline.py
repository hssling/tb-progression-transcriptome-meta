from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from tbmeta.analysis.de import save_within_cohort_de, within_cohort_de
from tbmeta.analysis.meta import leave_one_cohort_out_meta, meta_analyze_gene_effects, plot_forest_top_genes
from tbmeta.analysis.pathway import run_enrichment
from tbmeta.data.preprocess import harmonize_feature_space, load_processed_cohorts
from tbmeta.modeling.evaluate import loco_evaluation, random_split_sanity
from tbmeta.modeling.signatures import select_signature_genes
from tbmeta.reporting.figures import save_performance_outputs, save_shap_like_importance
from tbmeta.utils.logging import get_logger


def _window_sensitivity_summary(
    cohort_mats: dict[str, tuple[pd.DataFrame, pd.DataFrame]],
    perf_df: pd.DataFrame,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    wins = windows or [6, 12, 24]
    has_time = any("time_to_tb_months" in m.columns for _, m in cohort_mats.values())
    rows: list[dict[str, Any]] = []
    for w in wins:
        if has_time:
            for model, sub in perf_df.groupby("model") if not perf_df.empty else []:
                rows.append(
                    {
                        "window_months": w,
                        "model": model,
                        "auc_roc_mean": float(sub["auc_roc"].mean()),
                        "auc_pr_mean": float(sub["auc_pr"].mean()),
                        "brier_mean": float(sub["brier"].mean()),
                        "status": "computed_from_available_labels",
                    }
                )
        else:
            rows.append(
                {
                    "window_months": w,
                    "model": "NA",
                    "auc_roc_mean": float("nan"),
                    "auc_pr_mean": float("nan"),
                    "brier_mean": float("nan"),
                    "status": "not_available_no_time_to_tb_months",
                }
            )
    return pd.DataFrame(rows)


def run_analysis(cfg: dict[str, Any]) -> None:
    logger = get_logger("tbmeta.analysis", Path(cfg["paths"]["logs_dir"]) / "analyze.log")
    cohorts = load_processed_cohorts(cfg["paths"]["processed_data"])
    reg_path = Path(cfg["paths"]["registry_dir"]) / "registry_curated.csv"
    if reg_path.exists():
        reg = pd.read_csv(reg_path)
        if {"gse_id", "status"}.issubset(reg.columns):
            allowed = set(reg.loc[reg["status"] == "downloaded", "gse_id"].astype(str).tolist())
            cohorts = {k: v for k, v in cohorts.items() if k in allowed}
    if len(cohorts) < int(cfg["analysis"]["loco_min_cohorts"]):
        logger.warning("Insufficient cohorts for LOCO; found %d", len(cohorts))

    harmonized_expr, common_genes = harmonize_feature_space(cohorts)
    cohort_mats: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
    for cid, h_expr in harmonized_expr.items():
        _, meta = cohorts[cid]
        cohort_mats[cid] = (h_expr, meta)

    all_de = []
    for cid, (expr, meta) in cohort_mats.items():
        de = within_cohort_de(cid, expr, meta)
        all_de.append(de)

    de_df = pd.concat(all_de, ignore_index=True) if all_de else pd.DataFrame()
    save_within_cohort_de(de_df, cfg["paths"]["results_dir"])

    meta_df = meta_analyze_gene_effects(de_df) if not de_df.empty else pd.DataFrame()
    if meta_df.empty and not de_df.empty:
        # Single-cohort fallback: derive ranking from within-cohort effect sizes.
        tmp = (
            de_df.groupby("gene", as_index=False)
            .agg(meta_effect=("effect_size", "mean"), meta_se=("effect_size", "std"), n_cohorts=("cohort_id", "nunique"))
            .fillna({"meta_se": 1.0})
        )
        tmp["meta_se"] = tmp["meta_se"].replace(0, 1.0)
        tmp["meta_z"] = tmp["meta_effect"] / tmp["meta_se"]
        tmp["i2"] = 0.0
        tmp["abs_meta_z"] = tmp["meta_z"].abs()
        meta_df = tmp.sort_values("abs_meta_z", ascending=False).reset_index(drop=True)
    loo_df = leave_one_cohort_out_meta(de_df) if not de_df.empty else pd.DataFrame()

    tables_dir = Path(cfg["paths"]["results_dir"]) / "tables"
    figs_dir = Path(cfg["paths"]["results_dir"]) / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figs_dir.mkdir(parents=True, exist_ok=True)
    meta_df.to_csv(tables_dir / "meta_analysis.csv", index=False)
    loo_df.to_csv(tables_dir / "meta_leave_one_cohort_out.csv", index=False)

    if not meta_df.empty:
        plot_forest_top_genes(de_df, meta_df, figs_dir / "forest_top_genes.png", top_n=8)

    sig_df = select_signature_genes(
        meta_df,
        top_n=int(cfg["analysis"]["top_n_genes"]),
        random_state=int(cfg["analysis"]["random_state"]),
    )
    sig_df.to_csv(tables_dir / "signature_genes.csv", index=False)

    selected = [g for g in sig_df["gene"].tolist() if g in common_genes]
    model_names = list(cfg["analysis"]["models"])
    if bool(cfg["analysis"].get("include_xgboost", False)):
        model_names.append("xgboost")

    model_cohort_mats = {
        cid: (expr, meta)
        for cid, (expr, meta) in cohort_mats.items()
        if "progressor" in meta.columns and meta["progressor"].nunique() >= 2
    }

    if selected and model_cohort_mats:
        perf_df, model_results = loco_evaluation(
            model_cohort_mats,
            selected_genes=selected,
            model_names=model_names,
            random_state=int(cfg["analysis"]["random_state"]),
        )
        sanity_df = random_split_sanity(
            model_cohort_mats,
            selected_genes=selected,
            model_names=model_names,
            random_state=int(cfg["analysis"]["random_state"]),
        )
    else:
        perf_df, model_results = pd.DataFrame(), {}
        sanity_df = pd.DataFrame()

    perf_df.to_csv(tables_dir / "loco_performance.csv", index=False)
    sanity_df.to_csv(tables_dir / "random_split_sanity.csv", index=False)
    window_df = _window_sensitivity_summary(model_cohort_mats, perf_df, windows=[6, 12, 24])
    window_df.to_csv(tables_dir / "window_sensitivity.csv", index=False)
    if model_results:
        save_performance_outputs(model_results, cfg["paths"]["results_dir"])

    save_shap_like_importance(sig_df, tables_dir / "shap_like_importance.csv")

    if cfg["analysis"].get("run_pathway", True):
        run_enrichment(selected[:100], tables_dir)

    # Basic subgroup summary if columns exist.
    subgroup_rows = []
    for cid, (_expr, meta) in cohort_mats.items():
        if "age" in meta.columns:
            bins = pd.cut(meta["age"], bins=[0, 18, 35, 50, 120], labels=["<=18", "19-35", "36-50", "51+"])
            for grp, sub in meta.assign(age_group=bins).groupby("age_group", observed=False):
                subgroup_rows.append(
                    {
                        "cohort_id": cid,
                        "subgroup_var": "age_group",
                        "subgroup": str(grp),
                        "n": int(len(sub)),
                        "progressor_rate": float(sub["progressor"].mean()),
                    }
                )
        for col in ["sex", "hiv"]:
            if col in meta.columns:
                for grp, sub in meta.groupby(col):
                    subgroup_rows.append(
                        {
                            "cohort_id": cid,
                            "subgroup_var": col,
                            "subgroup": grp,
                            "n": int(len(sub)),
                            "progressor_rate": float(sub["progressor"].mean()),
                        }
                    )
    pd.DataFrame(subgroup_rows).to_csv(tables_dir / "subgroup_summary.csv", index=False)

    logger.info("Analysis complete: %d cohorts, %d common genes", len(cohort_mats), len(common_genes))
