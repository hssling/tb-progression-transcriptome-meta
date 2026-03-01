@echo off
set TARGET=%1
if "%TARGET%"=="" set TARGET=all

if "%TARGET%"=="setup" (
  python -m pip install --upgrade pip
  python -m pip install -e ".[dev]"
  goto :eof
)
if "%TARGET%"=="demo" (
  tbmeta all --config configs/config.yaml --mode demo --force
  goto :eof
)
if "%TARGET%"=="all" (
  tbmeta all --config configs/config.yaml
  goto :eof
)
if "%TARGET%"=="dashboard" (
  tbmeta dashboard --config configs/config.yaml
  goto :eof
)
if "%TARGET%"=="openclaw-check" (
  tbmeta openclaw-check --config configs/config.yaml
  goto :eof
)
if "%TARGET%"=="discover" (
  tbmeta discover --config configs/config.yaml
  goto :eof
)
if "%TARGET%"=="curate" (
  tbmeta curate --config configs/config.yaml
  goto :eof
)
if "%TARGET%"=="download" (
  tbmeta download --config configs/config.yaml
  goto :eof
)
if "%TARGET%"=="preprocess" (
  tbmeta preprocess --config configs/config.yaml
  goto :eof
)
if "%TARGET%"=="analyze" (
  tbmeta analyze --config configs/config.yaml
  goto :eof
)
if "%TARGET%"=="manuscript" (
  tbmeta manuscript --config configs/config.yaml
  goto :eof
)
if "%TARGET%"=="citations" (
  tbmeta citations --config configs/config.yaml
  goto :eof
)
if "%TARGET%"=="submission" (
  tbmeta submission --config configs/config.yaml
  goto :eof
)
if "%TARGET%"=="hf-space" (
  powershell -ExecutionPolicy Bypass -File scripts/publish_hf_space.ps1
  goto :eof
)
if "%TARGET%"=="kaggle" (
  powershell -ExecutionPolicy Bypass -File scripts/publish_kaggle.ps1
  goto :eof
)
if "%TARGET%"=="test" (
  pytest
  goto :eof
)
if "%TARGET%"=="lint" (
  ruff check src tests
  black --check src tests
  mypy src/tbmeta
  goto :eof
)

echo Unknown target: %TARGET%
exit /b 1
