-- Compare the same report type across months. Enrollment is a stock.
SELECT reporting_month, SUM(total_medicaid_and_chip_enrollment) AS reported_enrollment,
       COUNT(total_medicaid_and_chip_enrollment) AS states_reporting,
       COUNT(*) FILTER (WHERE total_medicaid_and_chip_enrollment_footnotes IS NOT NULL) AS states_with_notes
FROM monthly_updated
GROUP BY reporting_month
ORDER BY reporting_month DESC
LIMIT 12;

-- Latest preliminary observations, with their footnotes visible.
SELECT state_abbreviation, total_medicaid_enrollment, total_chip_enrollment,
       total_medicaid_and_chip_enrollment_footnotes
FROM monthly_preliminary
WHERE reporting_period = '202607'
ORDER BY state_abbreviation
LIMIT 5;

-- Baseline values are a three-month average, not a September monthly count.
SELECT state_abbreviation, total_medicaid_and_chip_enrollment,
       total_medicaid_and_chip_enrollment_footnotes
FROM baseline_enrollment
ORDER BY state_abbreviation;
