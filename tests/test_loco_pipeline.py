import numpy as np
import pandas as pd

from tbmeta.modeling.evaluate import loco_evaluation


def _cohort(cid: str, n: int, p: int, seed: int):
    rng = np.random.default_rng(seed)
    y = rng.binomial(1, 0.4, size=n)
    x = rng.normal(0, 1, size=(n, p))
    x[:, :5] += y[:, None] * 1.0
    expr = pd.DataFrame(x, columns=[f"G{i}" for i in range(p)])
    expr.insert(0, "sample_id", [f"{cid}_{i}" for i in range(n)])
    meta = pd.DataFrame({"sample_id": expr["sample_id"], "progressor": y})
    return expr, meta


def test_loco_pipeline_runs_on_synthetic_data():
    cohorts = {
        "A": _cohort("A", 40, 30, 1),
        "B": _cohort("B", 35, 30, 2),
        "C": _cohort("C", 45, 30, 3),
    }
    perf, models = loco_evaluation(
        cohorts,
        selected_genes=[f"G{i}" for i in range(15)],
        model_names=["elastic_net", "gene_set_score"],
    )
    assert not perf.empty
    assert "auc_roc" in perf.columns
    assert len(models) == 2
