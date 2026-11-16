---
license: other
license_name: us-government-public-domain
license_link: https://www.usa.gov/government-works
task_categories:
  - tabular-classification
  - tabular-regression
tags:
  - medicaid
  - chip
  - enrollment
  - health-policy
  - public-data
  - duckdb
pretty_name: CMS Medicaid and CHIP enrollment
size_categories:
  - 10K<n<100K
---

# CMS Medicaid and CHIP enrollment

CMS October 30, 2026 release: 11,220 state/period/report
observations and 44 field definitions. Monthly records cover June 2017-July 2026
across 50 states and DC, plus a July-September 2013 baseline average.
Preliminary and updated versions coexist and must not be pooled.
**11,264 rows across 2 tables.**

| Table | Description | Row Count | Column Count |
|---|---|---|---|
| `enrollment` | State/reporting-period/report-type records. 201309 is a Jul-Sep 2013 baseline average; preliminary and updated observations must not be pooled. | 11,220 | 47 |
| `field_definitions` | Pinned CMS definitions and exact source headers for the 44 source fields; descriptive rows, not enrollment observations. | 44 | 6 |

## Query the hosted snapshot

```sql
INSTALL httpfs; LOAD httpfs;
ATTACH 'https://huggingface.co/datasets/Nason/medicaid-enrollment-database/resolve/main/medicaid-enrollment.duckdb' AS db (READ_ONLY);

SELECT state_abbreviation, total_medicaid_and_chip_enrollment,
       total_medicaid_and_chip_enrollment_footnotes
FROM db.monthly_preliminary WHERE reporting_period = '202607'
ORDER BY state_abbreviation LIMIT 5;
```

Or with the datapond packages: `pip install datapond` / `install.packages("datapond")`.

Source identity and all 493,680 source cells rechecked November 16, 2026.
Enrollment is a month-end stock subject to retained state footnotes; source code
201309 is a July-September 2013 average and has NULL reporting_month. Monthly
updated and preliminary views remain separate. Numeric zeros with system-limit
footnotes are retained as reported, not treated as verified absence. Blank cells
become NULL. See README.md, FIELD-GUIDE.md, DICTIONARY.md and source-lock.json.
Official source: https://data.medicaid.gov/dataset/6165f45b-ca93-5bb5-9d06-db29c692a360
Pinned CSV: https://download.medicaid.gov/data/pi-dataset-october-2026-release.csv
Retrieved November 3, 2026; source CSV SHA-256:
ff5f49d7f01b620b6ac1f3e93fff6e453266471391948cd5a4efada800cfdb06.
