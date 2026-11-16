# Data Dictionary

Source: CMS Medicaid/CHIP Performance Indicator dataset.
Use monthly_updated or monthly_preliminary consistently; baseline_enrollment contains July-September 2013 averages.
Methodology: https://www.medicaid.gov/medicaid/national-medicaid-chip-program-information/medicaid-chip-enrollment-data/methodology-about-medicaid-chip-enrollment-report

## enrollment

State/reporting-period/report-type records. 201309 is a Jul-Sep 2013 baseline average; preliminary and updated observations must not be pooled.

Source file: `pi-dataset-october-2026-release.csv`
Rows: 11,220

| Column | Type | Nulls | Example | Join |
|--------|------|-------|---------|------|
| state_abbreviation | VARCHAR | 0.0% | AK | US postal abbreviation; combine with period and report type for source grain |
| state_name | VARCHAR | 0.0% | Alabama |  |
| reporting_period | VARCHAR | 0.0% | 201309 | YYYYMM source code; 201309 means Jul-Sep 2013 baseline average |
| state_expanded_medicaid | VARCHAR | 0.0% | N |  |
| preliminary_updated | VARCHAR | 0.0% | P |  |
| final_report | VARCHAR | 0.0% | N |  |
| new_applications_submitted_to_medicaid_and_chip_agencies | BIGINT | 0.5% | 0 |  |
| new_applications_submitted_to_medicaid_and_chip_agencies_footnotes | VARCHAR | 75.4% | Count is of individuals as opposed to applications |  |
| applications_for_financial_assistance_submitted_to_the_state_based_marketplace | BIGINT | 0.5% | 0 |  |
| applications_for_financial_assistance_submitted_to_the_state_based_marketplace_footnotes | VARCHAR | 97.5% | Does Not Include All Medicaid Applications Received By the SBM; Includes Dupl... |  |
| total_applications_for_financial_assistance_submitted_at_state_level | BIGINT | 0.5% | 0 |  |
| total_applications_for_financial_assistance_submitted_at_state_level_footnotes | VARCHAR | 72.1% | Count is of individuals as opposed to applications |  |
| individuals_determined_eligible_for_medicaid_at_application | BIGINT | 0.5% | 0 |  |
| individuals_determined_eligible_for_medicaid_at_application_footnotes | VARCHAR | 73.3% | Count is of Households, Not Individuals |  |
| individuals_determined_eligible_for_chip_at_application | BIGINT | 0.5% | 0 |  |
| individuals_determined_eligible_for_chip_at_application_footnotes | VARCHAR | 90.9% | Count is of Households, Not Individuals |  |
| total_medicaid_and_chip_determinations | BIGINT | 0.5% | 0 |  |
| total_medicaid_and_chip_determinations_footnotes | VARCHAR | 81.9% | Count is of Households, Not Individuals |  |
| medicaid_and_chip_child_enrollment | BIGINT | 0.5% | 0 |  |
| medicaid_and_chip_child_enrollment_footnotes | VARCHAR | 89.0% | Does Not Include All Full-Benefit Child Medicaid enrollees |  |
| total_medicaid_and_chip_enrollment | BIGINT | 0.0% | 0 |  |
| total_medicaid_and_chip_enrollment_footnotes | VARCHAR | 89.8% | Does Not Include All Full-Benefit Medicaid enrollees |  |
| total_medicaid_enrollment | BIGINT | 0.5% | 0 |  |
| total_medicaid_enrollment_footnotes | VARCHAR | 89.9% | Does Not Include All Full-Benefit Medicaid enrollees |  |
| total_chip_enrollment | BIGINT | 0.5% | 0 |  |
| total_chip_enrollment_footnotes | VARCHAR | 92.5% | Does Not Include All CHIP enrollees |  |
| total_medicaid_adult_enrollment | BIGINT | 77.7% | 0 |  |
| total_medicaid_adult_enrollment_footnotes | VARCHAR | 97.4% | Includes Individuals Enrolled At Any Time in Month (Not a Point-in-Time Count) |  |
| total_medicaid_and_chip_determinations_processed_in_less_than_24_hours | BIGINT | 39.5% | 0 |  |
| total_medicaid_and_chip_determinations_processed_in_less_than_24_hours_footnotes | VARCHAR | 89.0% | Determinations conducted in less than 24 hours are reported under the 1-7 day... |  |
| total_medicaid_and_chip_determinations_processed_between_24_hours_and_7_days | BIGINT | 39.5% | 0 |  |
| total_medicaid_and_chip_determinations_processed_between_24_hours_and_7_days_footnotes | VARCHAR | 89.0% | Determinations conducted in less than 24 hours are reported under the 1-7 day... |  |
| total_medicaid_and_chip_determinations_processed_between_8_days_and_30_days | BIGINT | 39.5% | 0 |  |
| total_medicaid_and_chip_determinations_processed_between_8_days_and_30_days_footnotes | VARCHAR | 89.0% | Does not include all MAGI determinations on applications |  |
| total_medicaid_and_chip_determinations_processed_between_31_days_and_45_days | BIGINT | 39.5% | 0 |  |
| total_medicaid_and_chip_determinations_processed_between_31_days_and_45_days_footnotes | VARCHAR | 88.7% | Does not include all MAGI determinations on applications |  |
| total_medicaid_and_chip_determinations_processed_in_more_than_45_days | BIGINT | 39.5% | 0 |  |
| total_medicaid_and_chip_determinations_processed_in_more_than_45_days_footnotes | VARCHAR | 89.0% | Does not include all MAGI determinations on applications |  |
| total_call_center_volume | BIGINT | 64.0% | 100021 |  |
| total_call_center_volume_footnotes | VARCHAR | 66.0% | Did not report data because of technical reasons |  |
| average_call_center_wait_time | BIGINT | 63.9% | 0 |  |
| average_call_center_wait_time_footnotes | VARCHAR | 64.5% | Call centers offer callbacks |  |
| average_call_center_abandonment_rate | DECIMAL(12,6) | 64.0% | 0.000000 |  |
| average_call_center_abandonment_rate_footnotes | VARCHAR | 64.5% | Callbacks are included |  |
| source_row_number | BIGINT | 0.0% | 1 |  |
| reporting_month | DATE | 0.5% | 2017-06-01 | Month start for monthly rows only; NULL for baseline |
| is_baseline | BOOLEAN | 0.0% | false |  |

## field_definitions

Pinned CMS definitions and exact source headers for the 44 source fields; descriptive rows, not enrollment observations.

Source file: `source-dictionary.json`
Rows: 44

| Column | Type | Nulls | Example | Join |
|--------|------|-------|---------|------|
| ordinal | INTEGER | 0.0% | 1 |  |
| column_name | VARCHAR | 0.0% | applications_for_financial_assistance_submitted_to_the_state_based_marketplace |  |
| source_header | VARCHAR | 0.0% | Applications for Financial Assistance Submitted to the State Based Marketplace |  |
| source_type | VARCHAR | 0.0% | integer |  |
| duckdb_type | VARCHAR | 0.0% | BIGINT |  |
| description | VARCHAR | 0.0% | A point-in-time count of the number of children enrolled in Medicaid and the ... |  |
