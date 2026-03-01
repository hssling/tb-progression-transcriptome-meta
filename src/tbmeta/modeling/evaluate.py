from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC


@dataclass
class ModelResult:
    name: str
    y_true: np.ndarray
    y_score: np.ndarray


def build_model(name: str, random_state: int = 42):
    if name == "elastic_net":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        solver="saga",
                        l1_ratio=0.5,
                        max_iter=2000,
                        random_state=random_state,
                    ),
                ),
            ]
        )
    if name == "linear_svm":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LinearSVC(random_state=random_state)),
            ]
        )
    if name == "gene_set_score":
        return "gene_set_score"
    if name == "xgboost":
        try:
            from xgboost import XGBClassifier  # type: ignore
        except Exception as exc:
            raise ValueError("xgboost model requested but package is unavailable") from exc
        return XGBClassifier(
            n_estimators=120,
            max_depth=3,
            learning_rate=0.06,
            subsample=0.9,
            colsample_bytree=0.8,
            reg_lambda=1.0,
            eval_metric="logloss",
            n_jobs=1,
            random_state=random_state,
        )
    raise ValueError(f"Unknown model {name}")


def _fit_predict(
    model_name: str,
    x_tr: np.ndarray,
    y_tr: np.ndarray,
    x_te: np.ndarray,
    top_gene_idx: np.ndarray,
    random_state: int,
) -> np.ndarray:
    if model_name == "gene_set_score":
        return x_te[:, top_gene_idx].mean(axis=1)

    model = build_model(model_name, random_state=random_state)
    model.fit(x_tr, y_tr)
    if hasattr(model, "predict_proba"):
        return model.predict_proba(x_te)[:, 1]
    if model_name == "linear_svm":
        raw = model.decision_function(x_te)
        return (raw - raw.min()) / (raw.max() - raw.min() + 1e-12)
    return model.decision_function(x_te)


def loco_evaluation(
    cohort_mats: dict[str, tuple[pd.DataFrame, pd.DataFrame]],
    selected_genes: list[str],
    model_names: list[str],
    random_state: int = 42,
) -> tuple[pd.DataFrame, dict[str, ModelResult]]:
    cohorts = sorted(cohort_mats)
    rows = []
    preds: dict[str, list[np.ndarray]] = {m: [] for m in model_names}
    truths: dict[str, list[np.ndarray]] = {m: [] for m in model_names}

    if not cohorts:
        return pd.DataFrame(), {}

    for left_out in cohorts:
        train_x, train_y = [], []
        test_x = test_y = None
        for cid, (expr, meta) in cohort_mats.items():
            x = expr[selected_genes].to_numpy(float)
            y = meta.set_index("sample_id").loc[expr["sample_id"], "progressor"].to_numpy(int)
            if cid == left_out:
                test_x, test_y = x, y
            else:
                train_x.append(x)
                train_y.append(y)

        if test_x is None or test_y is None or not train_x:
            continue

        x_tr = np.vstack(train_x)
        y_tr = np.hstack(train_y)
        top_idx = np.arange(min(10, len(selected_genes)))

        for m in model_names:
            y_score = _fit_predict(m, x_tr, y_tr, test_x, top_idx, random_state)
            roc = roc_auc_score(test_y, y_score)
            pr = average_precision_score(test_y, y_score)
            brier = brier_score_loss(test_y, np.clip(y_score, 0, 1))
            rows.append(
                {
                    "left_out_cohort": left_out,
                    "model": m,
                    "auc_roc": float(roc),
                    "auc_pr": float(pr),
                    "brier": float(brier),
                }
            )
            preds[m].append(y_score)
            truths[m].append(test_y)

    summary = pd.DataFrame(rows)
    out: dict[str, ModelResult] = {}
    for m in model_names:
        if not preds[m]:
            continue
        out[m] = ModelResult(m, np.hstack(truths[m]), np.hstack(preds[m]))
    return summary, out


def calibration_table(y_true: np.ndarray, y_score: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    frac_pos, mean_pred = calibration_curve(y_true, np.clip(y_score, 0, 1), n_bins=n_bins)
    return pd.DataFrame({"mean_pred": mean_pred, "frac_pos": frac_pos})


def decision_curve(y_true: np.ndarray, y_score: np.ndarray) -> pd.DataFrame:
    thresholds = np.linspace(0.05, 0.95, 19)
    rows = []
    n = len(y_true)
    for t in thresholds:
        pred = y_score >= t
        tp = ((pred == 1) & (y_true == 1)).sum()
        fp = ((pred == 1) & (y_true == 0)).sum()
        net_benefit = (tp / n) - (fp / n) * (t / (1 - t))
        rows.append({"threshold": t, "net_benefit": float(net_benefit)})
    return pd.DataFrame(rows)


def curve_tables(y_true: np.ndarray, y_score: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    fpr, tpr, roc_t = roc_curve(y_true, y_score)
    prec, rec, pr_t = precision_recall_curve(y_true, y_score)

    if len(roc_t) < len(fpr):
        roc_t = np.r_[roc_t, np.nan]
    elif len(roc_t) > len(fpr):
        roc_t = roc_t[: len(fpr)]

    if len(pr_t) < len(prec):
        pr_t = np.r_[pr_t, np.nan]
    elif len(pr_t) > len(prec):
        pr_t = pr_t[: len(prec)]

    roc_df = pd.DataFrame({"fpr": fpr, "tpr": tpr, "threshold": roc_t})
    pr_df = pd.DataFrame({"precision": prec, "recall": rec, "threshold": pr_t})
    return roc_df, pr_df


def random_split_sanity(
    cohort_mats: dict[str, tuple[pd.DataFrame, pd.DataFrame]],
    selected_genes: list[str],
    model_names: list[str],
    random_state: int = 42,
) -> pd.DataFrame:
    rows = []
    for cid, (expr, meta) in cohort_mats.items():
        x = expr[selected_genes].to_numpy(float)
        y = meta.set_index("sample_id").loc[expr["sample_id"], "progressor"].to_numpy(int)
        if len(np.unique(y)) < 2 or len(y) < 20:
            continue
        x_tr, x_te, y_tr, y_te = train_test_split(
            x, y, test_size=0.3, stratify=y, random_state=random_state
        )
        top_idx = np.arange(min(10, len(selected_genes)))
        for m in model_names:
            y_score = _fit_predict(m, x_tr, y_tr, x_te, top_idx, random_state)
            rows.append(
                {
                    "cohort_id": cid,
                    "model": m,
                    "auc_roc": float(roc_auc_score(y_te, y_score)),
                    "auc_pr": float(average_precision_score(y_te, y_score)),
                    "brier": float(brier_score_loss(y_te, np.clip(y_score, 0, 1))),
                }
            )
    return pd.DataFrame(rows)
