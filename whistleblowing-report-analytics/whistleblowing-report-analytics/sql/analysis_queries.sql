-- analysis_queries.sql
-- Key business questions on the whistleblowing dataset, in plain SQLite.
-- Load the CSV first:
--   sqlite3 whistleblowing.db
--   .mode csv
--   .import --skip 1 data/whistleblowing_reports.csv reports

-- 1. KPI snapshot: volume, anonymity, resolution rate, avg resolution time
SELECT
  COUNT(*) AS total_reports,
  ROUND(100.0 * SUM(reporting_type = 'Anonymous') / COUNT(*), 1) AS pct_anonymous,
  ROUND(100.0 * SUM(status = 'Resolved') / COUNT(*), 1) AS pct_resolved,
  ROUND(AVG(CASE WHEN status = 'Resolved' THEN resolution_days END), 1) AS avg_resolution_days
FROM reports;

-- 2. Which categories get reported most, and how anonymous is each?
SELECT
  category,
  COUNT(*) AS reports,
  ROUND(100.0 * SUM(reporting_type = 'Anonymous') / COUNT(*), 1) AS pct_anonymous
FROM reports
GROUP BY category
ORDER BY reports DESC;

-- 3. Do critical cases get resolved faster? (resolved cases only)
SELECT
  severity,
  COUNT(*) AS n_resolved,
  ROUND(AVG(resolution_days), 1) AS avg_days,
  MIN(resolution_days) AS fastest_days,
  MAX(resolution_days) AS slowest_days
FROM reports
WHERE status = 'Resolved'
GROUP BY severity;

-- 4. SLA check: % of High/Critical cases breaching 30 days
SELECT
  ROUND(100.0 * SUM(resolution_days > 30) / COUNT(*), 1) AS sla_breach_pct,
  COUNT(*) AS serious_cases
FROM reports
WHERE status = 'Resolved' AND severity IN ('High', 'Critical');

-- 5. SLA breach by department — where is the process failing?
SELECT
  department,
  COUNT(*) AS serious_cases,
  ROUND(100.0 * SUM(resolution_days > 30) / COUNT(*), 1) AS breach_pct
FROM reports
WHERE status = 'Resolved' AND severity IN ('High', 'Critical')
GROUP BY department
ORDER BY breach_pct DESC;

-- 6. Monthly report volume trend
SELECT
  substr(report_date, 1, 7) AS month,
  COUNT(*) AS reports
FROM reports
GROUP BY month
ORDER BY month;

-- 7. Reports per department (raw counts — normalize by headcount in the notebook)
SELECT
  department,
  COUNT(*) AS reports,
  ROUND(100.0 * SUM(reporting_type = 'Anonymous') / COUNT(*), 1) AS pct_anonymous
FROM reports
GROUP BY department
ORDER BY reports DESC;
