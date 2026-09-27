<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&height=190&section=header&text=Whistleblowing%20Report%20Analytics&fontSize=40&fontColor=ffffff&animation=fadeIn" />

<div align="center">

[![Typing SVG](https://readme-typing-svg.demolab.com?font=Fira+Code&size=21&pause=1200&color=2E86AB&center=true&vCenter=true&width=900&lines=Can+we+see+where+trust+breaks+down...;...before+it+becomes+a+headline%3F)](https://git.io/typing-svg)

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-F37626?style=for-the-badge&logo=jupyter&logoColor=white)

</div>

---

### 🎯 Why this project

> Veremark's second product is an **end-to-end encrypted whistleblowing platform**.
> This project mirrors the exact analytics a data analyst there would own —
> report intake trends, triage performance, and SLA compliance.

### ⚡ Key findings

<div align="center">

[![Findings](https://readme-typing-svg.demolab.com?font=Fira+Code&size=19&duration=2500&pause=800&color=C73E1D&center=true&vCenter=true&width=1000&lines=%F0%9F%95%B5+56%25+of+reports+filed+anonymously+%E2%80%94+Harassment+77%25+vs+Safety+42%25;%E2%9A%A1+Critical+cases+close+in+12+days+vs+71+for+Low;%F0%9F%94%A5+Operations%3A+151+reports+per+100+employees;+safety-culture+signal;%F0%9F%90%A2+Median+resolution+crept+36+%E2%86%92+44+days+%E2%80%94+backlog+forming;%E2%9A%A0%EF%B8%8F+31%25+of+High%2FCritical+cases+breach+the+30-day+SLA)](https://git.io/typing-svg)

</div>

---

### 📊 Dataset

`data/whistleblowing_reports.csv` — **800 synthetic reports, Sep 2025 → Aug 2026.**

| column | description |
|---|---|
| `report_id` | R-0001 … |
| `report_date` / `assigned_date` / `resolved_date` | intake → triage → resolution |
| `category` | Harassment, Safety Violation, Fraud/Misconduct, Discrimination, Retaliation, Other |
| `department` / `region` | Engineering, Sales, Operations, Support, Finance, HR · India, UK, US, Philippines |
| `reporting_type` | Anonymous / Named |
| `severity` | Low, Medium, High, Critical |
| `status` | Resolved, In Review, Open, Dismissed |
| `resolution_days` / `follow_up_count` | derived |

Generated with `generate_data.py` (seed `42`, fully reproducible) — including a few
dirty rows (duplicates, impossible durations, missing severity) so the cleaning step is real.

> 🔒 **Privacy note:** the data is synthetic and all analysis is **aggregate-only** —
> no individual reporter can be identified, which is how real whistleblowing analytics must work.

---

### 📈 Dashboard

Open **`dashboard/whistleblowing_dashboard.html`** — KPI cards + 5 interactive Plotly charts.

<details>
<summary>🛠️ Rebuild it</summary>

```bash
python3 dashboard/build_dashboard.py
```

</details>

---

### 🗄️ SQL

Two flavors, same 7 business questions:

- `sql/analysis_queries.sql` — SQLite
- `sql/mysql_whistleblowing_analysis.sql` — MySQL 8+ / MariaDB, step-by-step:
  load → sanity checks → clean → KPIs → the 5 questions. Tested on MariaDB 10.11.

<details>
<summary>▶️ Run them</summary>

```bash
# SQLite
sqlite3 whistleblowing.db
.mode csv
.import --skip 1 data/whistleblowing_reports.csv reports
.read sql/analysis_queries.sql

# MySQL / MariaDB (edit the CSV path at the top of the file first)
mysql -u root -p --local-infile=1 < sql/mysql_whistleblowing_analysis.sql
```

</details>

---

### 🔁 Reproduce

```bash
pip install -r requirements.txt
python3 generate_data.py            # rebuild the dataset (seed 42)
```

### 🗂️ Files

```
whistleblowing-report-analytics/
├── data/
│   └── whistleblowing_reports.csv
├── notebooks/
│   └── analysis.ipynb              # full EDA, executed with outputs
├── dashboard/
│   ├── whistleblowing_dashboard.html
│   └── build_dashboard.py
├── sql/
│   ├── analysis_queries.sql
│   └── mysql_whistleblowing_analysis.sql
├── visuals/                        # the 5 charts
├── requirements.txt
├── generate_data.py
└── README.md
```

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&height=120&section=footer" />
