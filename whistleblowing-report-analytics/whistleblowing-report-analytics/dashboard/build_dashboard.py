"""
build_dashboard.py — builds dashboard/whistleblowing_dashboard.html
(standalone Plotly dashboard, plotly.js via CDN).
Run from the project root: python3 dashboard/build_dashboard.py
"""
import json
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "whistleblowing_reports.csv"
OUT = ROOT / "dashboard" / "whistleblowing_dashboard.html"

df = pd.read_csv(DATA).drop_duplicates().copy()
for c in ["report_date", "assigned_date", "resolved_date"]:
    df[c] = pd.to_datetime(df[c], errors="coerce")
calc = (df["resolved_date"] - df["assigned_date"]).dt.days
df["resolution_days"] = np.where(df["status"] == "Resolved", calc, np.nan)
df["severity"] = df["severity"].fillna("Unknown")
df["report_month"] = df["report_date"].dt.to_period("M").astype(str)
resolved = df[df["status"] == "Resolved"].copy()

# ---- KPIs ----
serious = resolved[resolved["severity"].isin(["High", "Critical"])]
kpis = {
    "Total reports": f"{len(df)}",
    "Anonymous share": f"{(df['reporting_type'] == 'Anonymous').mean():.0%}",
    "Median resolution": f"{resolved['resolution_days'].median():.0f} days",
    "SLA breach (High/Critical)": f"{(serious['resolution_days'] > 30).mean():.0%}",
}

# ---- chart data ----
trend = df.groupby(["report_month", "category"]).size().unstack(fill_value=0).sort_index()
anon_by_cat = (df.groupby("category")["reporting_type"]
                 .apply(lambda s: (s == "Anonymous").mean() * 100)
                 .sort_values(ascending=False))
order = ["Critical", "High", "Medium", "Low", "Unknown"]
med_by_sev = resolved.groupby("severity")["resolution_days"].median().reindex(order).round(0)
headcount = {"Engineering": 250, "Sales": 180, "Operations": 150,
             "Customer Support": 120, "Finance": 60, "HR": 40}
dept_rate = (df["department"].value_counts() / pd.Series(headcount) * 100).sort_values(ascending=False).round(1)
breach_dept = (serious.assign(b=serious["resolution_days"] > 30)
                      .groupby("department")["b"].mean().mul(100).round(1)
                      .sort_values(ascending=False))

payload = {
    "kpis": kpis,
    "months": trend.index.tolist(),
    "trend": {c: trend[c].tolist() for c in trend.columns},
    "anon_cat": anon_by_cat.index.tolist(),
    "anon_val": anon_by_cat.values.tolist(),
    "sev": [s for s in order if s in med_by_sev.index],
    "sev_val": [float(med_by_sev[s]) for s in order if s in med_by_sev.index],
    "dept": dept_rate.index.tolist(),
    "dept_val": dept_rate.values.tolist(),
    "bdept": breach_dept.index.tolist(),
    "bdept_val": breach_dept.values.tolist(),
}

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Whistleblowing Report Analytics</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; background: #f4f6fa; color: #1f2937; padding: 24px; }
  h1 { font-size: 26px; margin-bottom: 4px; }
  .sub { color: #6b7280; margin-bottom: 20px; }
  .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 20px; }
  .kpi { background: #fff; border-radius: 12px; padding: 16px 18px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
  .kpi .label { font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: .04em; }
  .kpi .value { font-size: 28px; font-weight: 700; margin-top: 4px; }
  .kpi.alert .value { color: #c73e1d; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .card { background: #fff; border-radius: 12px; padding: 10px 10px 2px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
  .card.full { grid-column: 1 / -1; }
  .card h3 { font-size: 15px; padding: 8px 10px 0; }
  .note { color: #6b7280; font-size: 12px; margin-top: 16px; }
  @media (max-width: 800px) { .grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<h1>Whistleblowing Report Analytics</h1>
<p class="sub">12 months of reports &middot; Sep 2025 &ndash; Aug 2026 &middot; synthetic data</p>
<div class="kpis" id="kpis"></div>
<div class="grid">
  <div class="card full"><h3>Monthly reports by category</h3><div id="c-trend"></div></div>
  <div class="card"><h3>Anonymous share by category</h3><div id="c-anon"></div></div>
  <div class="card"><h3>Median resolution (days) by severity</h3><div id="c-sev"></div></div>
  <div class="card"><h3>Reports per 100 employees by department</h3><div id="c-dept"></div></div>
  <div class="card"><h3>SLA breach (&gt;30d) on High/Critical by department</h3><div id="c-breach"></div></div>
</div>
<p class="note">30-day SLA applies to High/Critical cases. Department headcounts are stated assumptions. Data: <code>data/whistleblowing_reports.csv</code>.</p>
<script>
const D = __PAYLOAD__;
const kpiEl = document.getElementById('kpis');
Object.entries(D.kpis).forEach(([label, value], i) => {
  const div = document.createElement('div');
  div.className = 'kpi' + (label.includes('breach') ? ' alert' : '');
  div.innerHTML = `<div class="label">${label}</div><div class="value">${value}</div>`;
  kpiEl.appendChild(div);
});
const layout = (extra={}) => Object.assign({margin:{t:30,r:20,b:60,l:60}, height:340,
  paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)', font:{family:'inherit'}}, extra);

Plotly.newPlot('c-trend', Object.keys(D.trend).map(k =>
  ({x: D.months, y: D.trend[k], name: k, type: 'scatter', mode: 'lines+markers', stackgroup: 'one'})),
  layout({legend:{orientation:'h', y:-0.25}}));

Plotly.newPlot('c-anon', [{x: D.anon_cat, y: D.anon_val, type: 'bar', marker:{color:'#A23B72'}}],
  layout({yaxis:{title:'% anonymous'}}));

Plotly.newPlot('c-sev', [{x: D.sev, y: D.sev_val, type: 'bar',
  marker:{color:['#C73E1D','#F18F01','#2E86AB','#6A994E','#9ca3af']}}],
  layout({yaxis:{title:'days'}}));

Plotly.newPlot('c-dept', [{x: D.dept, y: D.dept_val, type: 'bar', marker:{color:'#2E86AB'}}],
  layout({yaxis:{title:'per 100 employees'}}));

Plotly.newPlot('c-breach', [{x: D.bdept, y: D.bdept_val, type: 'bar', marker:{color:'#C73E1D'}}],
  layout({yaxis:{title:'% breached'}}));
</script>
</body>
</html>"""
html = html.replace("__PAYLOAD__", json.dumps(payload))
OUT.write_text(html)
print("dashboard written:", OUT, f"({OUT.stat().st_size/1024:.0f} KB)")
