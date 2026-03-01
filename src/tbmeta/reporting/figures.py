from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tbmeta.modeling.evaluate import ModelResult, calibration_table, curve_tables, decision_curve


def save_performance_outputs(model_results: dict[str, ModelResult], results_dir: str | Path) -> None:
    out_tables = Path(results_dir) / "tables"
    out_figs = Path(results_dir) / "figures"
    out_tables.mkdir(parents=True, exist_ok=True)
    out_figs.mkdir(parents=True, exist_ok=True)

    for name, res in model_results.items():
        roc_df, pr_df = curve_tables(res.y_true, res.y_score)
        cal_df = calibration_table(res.y_true, res.y_score)
        dca_df = decision_curve(res.y_true, res.y_score)

        roc_df.to_csv(out_tables / f"roc_{name}.csv", index=False)
        pr_df.to_csv(out_tables / f"pr_{name}.csv", index=False)
        cal_df.to_csv(out_tables / f"calibration_{name}.csv", index=False)
        dca_df.to_csv(out_tables / f"decision_curve_{name}.csv", index=False)

        fig, ax = plt.subplots(figsize=(4.5, 4.5))
        ax.plot(roc_df["fpr"], roc_df["tpr"], label=name)
        ax.plot([0, 1], [0, 1], "k--", linewidth=1)
        ax.set_xlabel("FPR")
        ax.set_ylabel("TPR")
        ax.set_title(f"ROC - {name}")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_figs / f"roc_{name}.png", dpi=220)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(4.5, 4.5))
        ax.plot(pr_df["recall"], pr_df["precision"], label=name)
        ax.set_xlabel("Recall")
        ax.set_ylabel("Precision")
        ax.set_title(f"PR - {name}")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_figs / f"pr_{name}.png", dpi=220)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(4.5, 4.5))
        ax.plot(cal_df["mean_pred"], cal_df["frac_pos"], marker="o", label=name)
        ax.plot([0, 1], [0, 1], "k--", linewidth=1)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Observed")
        ax.set_title(f"Calibration - {name}")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_figs / f"calibration_{name}.png", dpi=220)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(4.5, 4.5))
        ax.plot(dca_df["threshold"], dca_df["net_benefit"], label=name)
        ax.axhline(0, color="k", linestyle="--", linewidth=1)
        ax.set_xlabel("Threshold")
        ax.set_ylabel("Net benefit")
        ax.set_title(f"Decision curve - {name}")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_figs / f"dca_{name}.png", dpi=220)
        plt.close(fig)


def save_shap_like_importance(signature_df: pd.DataFrame, out_file: str | Path) -> None:
    if signature_df.empty:
        pd.DataFrame(columns=["gene", "importance"]).to_csv(out_file, index=False)
        return
    imp = signature_df[["gene", "meta_z"]].copy()
    imp["importance"] = np.abs(imp["meta_z"])
    imp[["gene", "importance"]].sort_values("importance", ascending=False).to_csv(out_file, index=False)
