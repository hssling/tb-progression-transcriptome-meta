PYTHON ?= python

.PHONY: setup lint test demo discover curate download preprocess analyze dashboard manuscript citations submission openclaw-check hf-space kaggle all clean

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	ruff check src tests
	black --check src tests
	mypy src/tbmeta

test:
	pytest -q

demo:
	tbmeta all --config configs/config.yaml --mode demo --force

discover:
	tbmeta discover --config configs/config.yaml

curate:
	tbmeta curate --config configs/config.yaml

download:
	tbmeta download --config configs/config.yaml

preprocess:
	tbmeta preprocess --config configs/config.yaml

analyze:
	tbmeta analyze --config configs/config.yaml

manuscript:
	tbmeta manuscript --config configs/config.yaml

citations:
	tbmeta citations --config configs/config.yaml

submission:
	tbmeta submission --config configs/config.yaml

openclaw-check:
	tbmeta openclaw-check --config configs/config.yaml

hf-space:
	powershell -ExecutionPolicy Bypass -File scripts/publish_hf_space.ps1

kaggle:
	powershell -ExecutionPolicy Bypass -File scripts/publish_kaggle.ps1

all:
	tbmeta all --config configs/config.yaml

clean:
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['.pytest_cache','.mypy_cache','.ruff_cache','build','dist']]; [shutil.rmtree(str(p), ignore_errors=True) for p in pathlib.Path('src').glob('*.egg-info')]"
