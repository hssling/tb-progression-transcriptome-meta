$ErrorActionPreference = "Stop"

if (-not (Get-Command kaggle -ErrorAction SilentlyContinue)) {
  Write-Error "Kaggle CLI not found. Install with: python -m pip install kaggle"
}

if (-not $env:KAGGLE_USERNAME -or -not $env:KAGGLE_KEY) {
  Write-Error "Set KAGGLE_USERNAME and KAGGLE_KEY environment variables."
}

kaggle kernels push -p .
Write-Host "Kaggle kernel push requested."
