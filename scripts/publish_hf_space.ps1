$ErrorActionPreference = "Stop"

if (-not (Get-Command huggingface-cli -ErrorAction SilentlyContinue)) {
  Write-Error "huggingface-cli not found. Install with: python -m pip install huggingface_hub"
}

if (-not $env:HF_TOKEN) {
  Write-Error "Set HF_TOKEN environment variable."
}

$spaceId = $env:HF_SPACE_ID
if (-not $spaceId) {
  Write-Error "Set HF_SPACE_ID (e.g., username/tbmeta-space)."
}

huggingface-cli login --token $env:HF_TOKEN
huggingface-cli repo create $spaceId --type space --space_sdk streamlit --yes
git clone "https://huggingface.co/spaces/$spaceId" ".hf_space_tmp"
Copy-Item "deploy/huggingface_space/*" ".hf_space_tmp/" -Recurse -Force
Push-Location ".hf_space_tmp"
git add .
git commit -m "Update space app" | Out-Null
git push
Pop-Location
Write-Host "Hugging Face Space pushed."
