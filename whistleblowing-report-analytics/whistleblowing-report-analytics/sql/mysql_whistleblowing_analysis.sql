-- =====================================================================
-- mysql_whistleblowing_analysis.sql
-- Whistleblowing Report Analytics — step-by-step analysis in MySQL 8+ / MariaDB
--
-- Covers the full analyst workflow: load -> sanity checks -> clean ->
-- KPIs -> the 5 business questions. Every query below was tested on MariaDB.
--
-- HOW TO RUN
--   1. Point @csv_path at your copy of data/whistleblowing_reports.csv
--   2. mysql -u root -p --local-infile=1 < sql/mysql_whistleblowing_analysis.sql
--      (the server needs local_infile=ON: SET GLOBAL local_infile = 1;)
-- =====================================================================

-- ---------------------------------------------------------------------
-- STEP 0 — setup: database + raw staging table (no keys, we check dirt first)
-- ---------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS whistleblowing;
USE whistleblowing;

DROP TABLE IF EXISTS reports_raw;
CREATE TABLE reports_raw (
  report_id       VARCHAR(10),
  report_date     DATE,
  assigned_date   DATE,
  resolved_date   DATE,
  category        VARCHAR(30),
  department      VARCHAR(30),
  region          VARCHAR(30),
  reporting_type  VARCHAR(12),
  severity        VARCHAR(12),
  status          VARCHAR(12),
  resolution_days INT,
  follow_up_count INT
);

-- -- -- EDIT the file path below to point at your CSV -- --
-- (the server needs local_infile=ON:  SET GLOBAL local_infile = 1;)
LOAD DATA LOCAL INFILE '/home/hatch/workspace/your_files/whistleblowing-report-analytics/data/whistleblowing_reports.csv'
INTO TABLE reports_raw
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(report_id, @rd, @ad, @resd, category, department, region,
 reporting_type, @sev, status, @rdays, follow_up_count)
SET
  report_date     = NULLIF(@rd, ''),
  assigned_date   = NULLIF(@ad, ''),
  resolved_date   = NULLIF(@resd, ''),
  severity        = NULLIF(@sev, ''),
  resolution_days = NULLIF(@rdays, '');

-- ---------------------------------------------------------------------
-- STEP 1 — sanity checks: what is wrong with this data?
-- ---------------------------------------------------------------------
-- 1a. row count
SELECT COUNT(*) AS raw_rows FROM reports_raw;

-- 1b. exact duplicate rows
SELECT COUNT(*) AS duplicate_rows FROM (
  SELECT report_id, report_date, assigned_date, resolved_date, category,
         department, region, reporting_type, severity, status,
         resolution_days, follow_up_count, COUNT(*) AS c
  FROM reports_raw
  GROUP BY report_id, report_date, assigned_date, resolved_date, category,
           department, region, reporting_type, severity, status,
           resolution_days, follow_up_count
  HAVING c > 1
) d;

-- 1c. impossible durations (resolved before assigned)
SELECT COUNT(*) AS negative_durations
FROM reports_raw WHERE resolution_days < 0;

-- 1d. missing values per column
SELECT
  SUM(report_date IS NULL)    AS missing_report_date,
  SUM(assigned_date IS NULL)  AS missing_assigned_date,
  SUM(severity IS NULL)       AS missing_severity,
  SUM(status IS NULL)         AS missing_status
FROM reports_raw;

-- 1e. value mixes
SELECT status, COUNT(*) AS n FROM reports_raw GROUP BY status;
SELECT severity, COUNT(*) AS n FROM reports_raw GROUP BY severity;

-- ---------------------------------------------------------------------
-- STEP 2 — clean: dedupe, recompute durations from dates, fix negatives
--   Decisions (same as the notebook):
--   * exact duplicates dropped
--   * resolution_days recomputed as DATEDIFF(resolved, assigned) — dates win
--   * negative / impossible durations -> NULL
--   * missing severity kept as 'Unknown' (0.5% of rows)
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS reports;
CREATE TABLE reports AS
SELECT
  report_id,
  report_date,
  assigned_date,
  resolved_date,
  category,
  department,
  region,
  reporting_type,
  COALESCE(severity, 'Unknown') AS severity,
  status,
  CASE
    WHEN status = 'Resolved'
     AND resolved_date IS NOT NULL
     AND assigned_date IS NOT NULL
     AND DATEDIFF(resolved_date, assigned_date) >= 0
    THEN DATEDIFF(resolved_date, assigned_date)
    ELSE NULL
  END AS resolution_days,
  follow_up_count,
  DATE_FORMAT(report_date, '%Y-%m') AS report_month
FROM (SELECT DISTINCT * FROM reports_raw) d;

SELECT COUNT(*) AS clean_rows FROM reports;
SELECT MIN(report_date) AS from_date, MAX(report_date) AS to_date FROM reports;

-- ---------------------------------------------------------------------
-- STEP 3 — KPI snapshot: the one table a manager reads first
-- ---------------------------------------------------------------------
SELECT
  COUNT(*) AS total_reports,
  ROUND(100 * AVG(reporting_type = 'Anonymous'), 1) AS pct_anonymous,
  ROUND(100 * AVG(status = 'Resolved'), 1)          AS pct_resolved,
  ROUND(100 * AVG(severity IN ('High', 'Critical')), 1) AS pct_high_critical
FROM reports;

SELECT ROUND(AVG(resolution_days), 1) AS avg_resolution_days
FROM reports WHERE status = 'Resolved';

-- ---------------------------------------------------------------------
-- STEP 4 — Q1: reports by category + anonymous share
--   Hypothesis: sensitive issues are only reported anonymously.
-- ---------------------------------------------------------------------
SELECT
  category,
  COUNT(*) AS reports,
  ROUND(100 * AVG(reporting_type = 'Anonymous'), 1) AS pct_anonymous
FROM reports
GROUP BY category
ORDER BY reports DESC;

-- ---------------------------------------------------------------------
-- STEP 5 — Q2: do critical cases get resolved faster?
--   Median via window functions (no PERCENTILE_CONT in MariaDB).
-- ---------------------------------------------------------------------
WITH ranked AS (
  SELECT
    severity,
    resolution_days,
    ROW_NUMBER() OVER (PARTITION BY severity ORDER BY resolution_days) AS rn,
    COUNT(*)     OVER (PARTITION BY severity) AS n
  FROM reports
  WHERE status = 'Resolved' AND resolution_days IS NOT NULL
)
SELECT
  severity,
  COUNT(*) AS n_resolved,
  ROUND(AVG(CASE WHEN rn IN (FLOOR((n + 1) / 2), CEIL((n + 1) / 2))
                 THEN resolution_days END), 1) AS median_days,
  ROUND(AVG(resolution_days), 1) AS avg_days
FROM ranked
GROUP BY severity;

-- ---------------------------------------------------------------------
-- STEP 6 — Q3: where do reports cluster?
--   Raw counts mislead — normalize by headcount (stated assumptions).
-- ---------------------------------------------------------------------
WITH headcount(department, employees) AS (
  SELECT 'Engineering', 250 UNION ALL
  SELECT 'Sales', 180 UNION ALL
  SELECT 'Operations', 150 UNION ALL
  SELECT 'Customer Support', 120 UNION ALL
  SELECT 'Finance', 60 UNION ALL
  SELECT 'HR', 40
)
SELECT
  r.department,
  COUNT(*) AS reports,
  h.employees,
  ROUND(100.0 * COUNT(*) / h.employees, 1) AS reports_per_100_employees
FROM reports r
JOIN headcount h USING (department)
GROUP BY r.department, h.employees
ORDER BY reports_per_100_employees DESC;

SELECT region, COUNT(*) AS reports
FROM reports GROUP BY region ORDER BY reports DESC;

-- ---------------------------------------------------------------------
-- STEP 7 — Q4: trend — is reporting rising, and is resolution keeping up?
-- ---------------------------------------------------------------------
SELECT report_month AS month, COUNT(*) AS reports
FROM reports
GROUP BY report_month
ORDER BY report_month;

-- resolution time by quarter: is a backlog forming?
SELECT
  CONCAT(YEAR(report_date), 'Q', QUARTER(report_date)) AS quarter,
  COUNT(*) AS resolved_cases,
  ROUND(AVG(resolution_days), 1) AS avg_days
FROM reports
WHERE status = 'Resolved' AND resolution_days IS NOT NULL
GROUP BY quarter
ORDER BY quarter;

-- ---------------------------------------------------------------------
-- STEP 8 — Q5: SLA — what share of High/Critical cases breach 30 days?
-- ---------------------------------------------------------------------
SELECT
  COUNT(*) AS serious_cases,
  ROUND(100 * AVG(resolution_days > 30), 1) AS sla_breach_pct
FROM reports
WHERE status = 'Resolved' AND severity IN ('High', 'Critical');

SELECT
  department,
  COUNT(*) AS serious_cases,
  ROUND(100 * AVG(resolution_days > 30), 1) AS breach_pct
FROM reports
WHERE status = 'Resolved' AND severity IN ('High', 'Critical')
GROUP BY department
ORDER BY breach_pct DESC;

SELECT
  region,
  COUNT(*) AS serious_cases,
  ROUND(100 * AVG(resolution_days > 30), 1) AS breach_pct
FROM reports
WHERE status = 'Resolved' AND severity IN ('High', 'Critical')
GROUP BY region
ORDER BY breach_pct DESC;
