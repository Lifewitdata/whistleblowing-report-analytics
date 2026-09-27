"""
generate_data.py — synthetic whistleblowing report dataset for Veremark-style analytics.

Simulates 12 months of reports on an end-to-end-encrypted whistleblowing
platform: report intake, triage (assign), and resolution.

Patterns baked in (so the analysis has real signal to find):
  - Harassment & Retaliation are filed anonymously far more often than Safety reports
  - Critical-severity cases get triaged and resolved faster
  - Operations has the highest per-employee report rate (safety culture signal)
  - Resolution times got worse in mid-2026 as report volume grew (backlog)
  - A few dirty rows (dupes, negative durations, missing severity) so cleaning is real

Run: python3 generate_data.py
Writes: data/whistleblowing_reports.csv
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

N = 800
START = np.datetime64("2025-09-01")

# --- report dates: 12 months, gentle growth + volume spike in Feb 2026 (policy change) ---
months = np.arange(12)
month_w = np.array([1.00, 1.05, 1.02, 0.95, 0.90, 1.10, 1.35, 1.30, 1.25, 1.20, 1.15, 1.10])
month_w = month_w / month_w.sum()
report_month = rng.choice(months, size=N, p=month_w)
report_day = rng.integers(0, 30, size=N)
report_date = (START + (report_month * 30 + report_day).astype("timedelta64[D]")).astype("datetime64[D]")

# --- category ---
cats = ["Harassment", "Safety Violation", "Fraud/Misconduct",
        "Discrimination", "Retaliation", "Other"]
cat_p = [0.22, 0.20, 0.18, 0.12, 0.08, 0.20]
category = rng.choice(cats, size=N, p=cat_p)

# --- reporting type: anonymity depends on category ---
anon_p = {"Harassment": 0.75, "Retaliation": 0.70, "Discrimination": 0.60,
          "Fraud/Misconduct": 0.55, "Other": 0.45, "Safety Violation": 0.40}
reporting_type = np.array([
    "Anonymous" if rng.random() < anon_p[c] else "Named" for c in category
])

# --- department: Operations is over-represented (safety signal) ---
depts = ["Engineering", "Sales", "Operations", "Customer Support", "Finance", "HR"]
dept_p = [0.24, 0.18, 0.28, 0.16, 0.08, 0.06]
department = rng.choice(depts, size=N, p=dept_p)

# --- region ---
regions = ["India", "UK", "US", "Philippines"]
region = rng.choice(regions, size=N, p=[0.45, 0.20, 0.20, 0.15])

# --- severity: base mix, harassment/retaliation skew higher ---
sev_levels = ["Low", "Medium", "High", "Critical"]
sev_p = np.array([0.30, 0.40, 0.22, 0.08])
severity = []
for c in category:
    p = sev_p.copy()
    if c in ("Harassment", "Retaliation"):
        p = np.array([0.15, 0.35, 0.35, 0.15])  # skew worse
    severity.append(rng.choice(sev_levels, p=p))
severity = np.array(severity)

# --- status: critical cases more likely resolved ---
status = []
for s in severity:
    if s == "Critical":
        status.append(rng.choice(["Resolved", "In Review", "Open", "Dismissed"],
                                 p=[0.85, 0.10, 0.03, 0.02]))
    else:
        status.append(rng.choice(["Resolved", "In Review", "Open", "Dismissed"],
                                 p=[0.74, 0.12, 0.09, 0.05]))
status = np.array(status)

# --- resolution time (days): faster for critical, slower when backlog grows ---
# backlog factor: reports filed later in the year wait longer
med = {"Critical": 10, "High": 18, "Medium": 32, "Low": 55}
res_days = np.zeros(N)
for i in range(N):
    base = rng.lognormal(mean=np.log(med[severity[i]]), sigma=0.7)
    backlog = 1 + 0.35 * (report_month[i] / 11)          # +35% by Aug 2026
    if department[i] == "Engineering":
        backlog *= 1.15                                  # eng triage bottleneck
    if reporting_type[i] == "Anonymous":
        backlog *= 1.10                                  # harder to follow up
    res_days[i] = min(base * backlog, 180)

# --- dates ---
triage_lag = rng.integers(0, 4, size=N)
assigned_date = report_date + triage_lag.astype("timedelta64[D]")
resolved_date = pd.Series([pd.NaT] * N)
res_days_int = np.round(res_days).astype(int)
mask = status == "Resolved"
resolved_date[mask] = (assigned_date[mask] + res_days_int[mask].astype("timedelta64[D]"))

follow_up_count = np.clip((res_days_int // 15 + rng.integers(0, 2, size=N)), 0, 6)

df = pd.DataFrame({
    "report_id": [f"R-{i:04d}" for i in range(1, N + 1)],
    "report_date": report_date.astype(str),
    "assigned_date": assigned_date.astype(str),
    "resolved_date": resolved_date.astype(str),
    "category": category,
    "department": department,
    "region": region,
    "reporting_type": reporting_type,
    "severity": severity,
    "status": status,
    "resolution_days": np.where(mask, res_days_int, np.nan),
    "follow_up_count": follow_up_count,
})

# --- inject realistic dirt: 3 duplicate rows, 5 negative durations, 4 missing severity ---
dupes = df.sample(3, random_state=7)
df = pd.concat([df, dupes], ignore_index=True)

neg_idx = rng.choice(df.index[df["status"] == "Resolved"], 5, replace=False)
df.loc[neg_idx, "resolved_date"] = (
    pd.to_datetime(df.loc[neg_idx, "assigned_date"]) - pd.to_timedelta(rng.integers(1, 10, 5), unit="D")
).dt.strftime("%Y-%m-%d")
df.loc[neg_idx, "resolution_days"] = -rng.integers(1, 10, 5)

miss_idx = rng.choice(df.index, 4, replace=False)
df.loc[miss_idx, "severity"] = np.nan

df = df.sample(frac=1, random_state=99).reset_index(drop=True)  # shuffle

df.to_csv("data/whistleblowing_reports.csv", index=False)
print(f"wrote data/whistleblowing_reports.csv: {df.shape[0]} rows x {df.shape[1]} cols")
print(df["status"].value_counts().to_string())
print("duplicated rows:", df.duplicated().sum())
print("negative resolution_days:", (df["resolution_days"] < 0).sum())
print("missing severity:", df["severity"].isna().sum())
