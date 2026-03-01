import pandas as pd
import pytest

from tbmeta.data.schemas import REQUIRED_REGISTRY_COLUMNS, validate_registry_schema


def test_registry_schema_validates_required_columns():
    row = {c: "x" for c in REQUIRED_REGISTRY_COLUMNS}
    row["n_samples"] = 50
    df = pd.DataFrame([row])
    validate_registry_schema(df)


def test_registry_schema_raises_on_missing_column():
    row = {c: "x" for c in REQUIRED_REGISTRY_COLUMNS if c != "status"}
    row["n_samples"] = 50
    df = pd.DataFrame([row])
    with pytest.raises(ValueError):
        validate_registry_schema(df)
