---
title: tbmeta-space
emoji: 🧬
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: 1.40.0
app_file: app.py
pinned: false
---

# Hugging Face Space Setup

1. Create a new Space (`Streamlit`) in your Hugging Face account.
2. Push these files to the Space root:
- `app.py`
- `requirements.txt`
3. Also include this repository content (or mount it as a submodule) so the `tbmeta` CLI and config are available.
4. Set optional secrets in Space settings:
- `OPENAI_API_KEY`
- `OPENCLAW_API_KEY`
5. Launch the Space and use the "Run Full Pipeline" button.

Note:
- Free CPU Spaces may be slow for full runs.
- For heavy runs, execute pipeline in CI/Kaggle and use Space primarily as a dashboard.
