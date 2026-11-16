# CMS Medicaid and CHIP enrollment

National state-level application, eligibility, enrollment and call-center indicators from CMS, frozen to the **October 30, 2026 release**. The Datapond id is `medicaid-enrollment`. The artifact was built November 3 and its source identity and complete cell reconciliation were rechecked November 16, 2026.

The 4,528,149-byte source CSV produces a 3,944,448-byte DuckDB file. There are **11,220 state/period/report records** and **44 field-definition records** in two data tables (11,264 stored rows in total), plus three views. Counts are observations and definitions, not unique people.

## Coverage and units

All 50 states and DC are represented. Monthly records span **June 2017–July 2026**: preliminary data through July 2026 and updated data through June 2026. The source also contains 51 baseline rows coded `201309`, representing **average enrollment in July–September 2013**. It contains no monthly series for October 2013–May 2017. Connecticut and Maine have NULL total baseline enrollment.

CMS describes enrollment as a month-end stock of people eligible for comprehensive benefits, subject to the retained state footnotes. Applications, determinations, processing times and call-center metrics have different units. Do not sum enrollment across months or combine the preliminary and updated versions of the same month. CMS says only report types of the same kind should be compared over time; even those may have state methodology breaks. See the [official methodology](https://www.medicaid.gov/medicaid/national-medicaid-chip-program-information/medicaid-chip-enrollment-data/methodology-about-medicaid-chip-enrollment-report).

| Table/view | Rows | Grain and use |
|---|---:|---|
| `enrollment` | 11,220 | Primary key: `state_abbreviation`, `reporting_period`, `preliminary_updated`. Every source value retained, with explicit types. |
| `field_definitions` | 44 | One CMS field definition, exact CSV header and type mapping per source column. |
| `monthly_updated` (view) | 5,559 | Updated monthly reports only; baseline excluded. Appropriate starting point for consistent historical comparisons. |
| `monthly_preliminary` (view) | 5,610 | Preliminary monthly reports only; baseline excluded. Includes the newest month. |
| `baseline_enrollment` (view) | 51 | July–September 2013 average, not a September monthly observation. |

All 44 source columns map to their CMS machine names. `reporting_period` remains a six-character string. Three derived columns are added: `source_row_number` (one-based data record position), `reporting_month` (first day of the month, NULL for baseline), and `is_baseline`. Integer indicators use BIGINT; the call-abandonment proportion uses DECIMAL(12,6). Only empty cells become NULL. Headers may differ from the pinned dictionary only by case or surrounding whitespace. Unexpected schema, numeric, date or key changes abort the build.

The database includes standard Datapond `_metadata` and `_columns` tables. Source version, URL, file and SHA-256 are embedded in `_metadata`. [DICTIONARY.md](DICTIONARY.md) reports every data column's type, null rate and example. [FIELD-GUIDE.md](FIELD-GUIDE.md) explains analytical limitations.

## Query the database

The following examples run against the delivered local file and do not require publication.

```python
import duckdb
con = duckdb.connect("artifacts-release/medicaid-enrollment.duckdb", read_only=True,
                     config={"threads": 1, "memory_limit": "128MiB"})
print(con.sql("""
  SELECT state_abbreviation, total_medicaid_enrollment, total_chip_enrollment,
         total_medicaid_and_chip_enrollment_footnotes
  FROM monthly_preliminary
  WHERE reporting_period = '202607'
  ORDER BY state_abbreviation LIMIT 5
""").fetchall())
con.close()
```

```r
library(DBI)
con <- dbConnect(duckdb::duckdb(config=list(threads="1", memory_limit="128MiB")),
                 dbdir="artifacts-release/medicaid-enrollment.duckdb", read_only=TRUE)
dbGetQuery(con, "SELECT state_abbreviation, total_medicaid_enrollment,
  total_chip_enrollment, total_medicaid_and_chip_enrollment_footnotes
  FROM monthly_preliminary WHERE reporting_period='202607'
  ORDER BY state_abbreviation LIMIT 5")
dbDisconnect(con, shutdown=TRUE)
```

The real released **Python datapond 0.1.5** and **R datapond 0.1.0** clients are additionally exercised by `run_smoke.py` against a loopback-only HTTP range server and temporary registry. The tests use the intended id, remote attachment, dictionary discovery, counts, baseline handling and the official July total. Since these releases lack startup configuration arguments, the smoke harness adapts only their real DuckDB connection defaults to one thread and 128 MiB; query results and HTTP operations are not mocked. The Python HTTP extension is cached in the workspace. R uses its existing extension installation.

## Rebuild and validate

Install the pinned dependencies in `pyproject.toml` with uv. From this repository:

```sh
uv sync
uv run python build_database.py --download --out artifacts-new
uv run pytest test_build.py -q --basetemp test-tmp
```

`--download` reuses a matching cached CSV. Otherwise it fetches only the locked official URL, with a 32 MiB decoded-byte cap, 15/30-second request timeouts and a 90-second transfer-loop cap. The pinned checksum must match before ingestion. `source-lock.json` also pins the official dataset metadata and dictionary. Hashes refer to the saved decoded CSV, while HTTP Content-Length can describe the compressed transfer representation.

Builds require a new output directory, use one DuckDB thread, 256 MiB memory, no spill, a 100,000-source-row ceiling and at least 256 MiB free disk. DuckDB's memory setting is not a total process-memory limit. Failed partial outputs are retained; they are never promoted to the final `.duckdb` name. An existing artifact is never replaced. The manifest records all 21 data checks, per-column null counts, exact file size and SHA-256. Synthetic integration tests cover baseline semantics, report versions, footnotes, NULL versus zero, duplicate keys, invalid values, changed hashes/schema, existing outputs and download limits.

CMS sources can revise values within a release. A future refresh must review a new metadata snapshot and checksum rather than silently accepting changed bytes. Compare content and coverage before rebuilding; the source is monthly, and Datapond rebuilds remain manual.

## Source, provenance and reuse

- [CMS dataset](https://data.medicaid.gov/dataset/6165f45b-ca93-5bb5-9d06-db29c692a360), official API metadata in `source-metadata.json`: modified October 30, 2026 at 18:00 UTC; monthly cadence.
- [Pinned October CSV](https://download.medicaid.gov/data/pi-dataset-october-2026-release.csv), retrieved November 3, 2026. SHA-256: `ff5f49d7f01b620b6ac1f3e93fff6e453266471391948cd5a4efada800cfdb06`.
- [Official dictionary](https://data.medicaid.gov/api/1/metastore/schemas/data-dictionary/items/7d80cfd8-3266-4c55-8436-948b7c55b9dd), saved unmodified as `source-dictionary.json`.
- The official metadata explicitly links to [U.S. government works](https://www.usa.gov/government-works). Data are public domain; attribution to CMS is appropriate. No CMS endorsement is implied. The [Data.gov catalog](https://catalog.data.gov/dataset/state-medicaid-and-chip-applications-eligibility-determinations-and-enrollment-data) independently includes the same license but lagged one release when checked.
- [CMS July highlights](https://www.medicaid.gov/medicaid/program-information/medicaid-and-chip-enrollment-data/report-highlights) provide independent totals: 72,946,510 total, 65,742,057 Medicaid, 7,204,453 CHIP. All three reconcile exactly to this file.

Recommended citation: Centers for Medicare & Medicaid Services, State Medicaid and CHIP Applications, Eligibility Determinations, and Enrollment Data, October 2026 release, retrieved November 3, 2026; Datapond local conversion, with source and artifact checksums from the manifest.

## Hosted artifact

The database, dictionary, source lock and build manifest are hosted at [Hugging Face](https://huggingface.co/datasets/Nason/medicaid-enrollment-database). The catalog pins an immutable release revision. Source releases are monthly; rebuilds are manual.
