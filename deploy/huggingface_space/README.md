---
title: tbmeta-space
emoji: 🧬
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: 1.40.0
app_file: app.py
python_version: "3.11"
pinned: false
---

# Hugging Face Space Setup

1. Create a new Space (`Streamlit`) in your Hugging Face account.
2. Push these files to the Space root:
- `app.py`
- `requirements.txt`
3. Default publish mode copies generated `results/` and `manuscripts/` for artifact viewing.
4. Optional: include full repository + `tbmeta` install if you want in-Space pipeline execution.
5. Set optional secrets in Space settings:
- `OPENAI_API_KEY`
- `OPENCLAW_API_KEY`
6. Launch the Space.

Note:
- Free CPU Spaces may be slow for full runs.
- For heavy runs, execute pipeline in CI/Kaggle and use Space primarily as a dashboard.
