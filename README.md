# COVID-19 Analytics & Power BI Data Studio

Python ETL → Power BI star schema (31 DAX measures) → static web dashboard.

## Run locally
    pip install pandas numpy
    python python_etl/etl_pipeline.py      # regenerates CSVs + web_dashboard/data/
    cd web_dashboard && python -m http.server 8080
Open http://localhost:8080

## Deploy on Vercel
1. Push this whole folder to the root of a GitHub repo (keep `vercel.json` at the top).
2. Vercel → Add New Project → import repo → Framework Preset: **Other**. Leave Build Command empty.
3. Deploy. `vercel.json` serves `web_dashboard/` and falls back to `index.html`, so no 404s.
