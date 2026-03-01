$ErrorActionPreference = "Stop"

if (-not $env:HF_TOKEN) {
  Write-Error "Set HF_TOKEN environment variable."
}

$spaceId = $env:HF_SPACE_ID
if (-not $spaceId) {
  Write-Error "Set HF_SPACE_ID (e.g., username/tbmeta-space)."
}

$spaceUrl = "https://user:$($env:HF_TOKEN)@huggingface.co/spaces/$spaceId"
if (Test-Path ".hf_space_tmp") {
  Remove-Item ".hf_space_tmp" -Recurse -Force
}
git clone $spaceUrl ".hf_space_tmp"
Copy-Item "deploy/huggingface_space/*" ".hf_space_tmp/" -Recurse -Force
Push-Location ".hf_space_tmp"
git add .
if (-not (git diff --cached --quiet)) {
  git commit -m "Update space app" | Out-Null
  git push
  Write-Host "Hugging Face Space pushed."
} else {
  Write-Host "No changes to push to Hugging Face Space."
}
Pop-Location
