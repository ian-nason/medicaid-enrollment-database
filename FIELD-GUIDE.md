# Field guide

Start longitudinal analyses from **one** of `monthly_updated` or `monthly_preliminary`. The source has 5,559 state/month groups with both versions. Pooling them duplicates observations and mixes different reporting completeness. The view names select report type consistently; neither guesses a "best available" mixed series.

`201309` is the baseline average over July–September 2013. Its `reporting_month` is deliberately NULL. `baseline_enrollment` makes those 51 records available without placing an average on a monthly axis. Two states have missing baseline totals. No monthly records are imputed across the October 2013–May 2017 gap.

Enrollment is generally a month-end stock. Applications, eligibility determinations and calls are flows. Do not add a stock across months, sum applications with enrolled people, or interpret the registry's 11,264 total rows as people. Field definitions are descriptive records and the three views overlap their parent table.

All source footnotes are retained verbatim. They disclose differences such as inclusion of limited benefits, retroactive enrollment, any-time-in-month counts, household rather than person units, renewals, other benefit programs, and system limitations. Raw numeric zeros survive unchanged, including 218 child-enrollment records whose note says the state cannot provide data because of system limitations. Those zeros should not automatically be interpreted as no enrolled children. Blank numeric values remain NULL; the build does not replace or reclassify a source zero.

The CHIP and "child enrollment" indicators can include adults in some states. Adult enrollment and operational measures have shorter or incomplete reporting coverage; their missingness is not evidence of no activity. An abandonment rate of 0.05 is a proportion (5%), not 0.05%. It is not rescaled.

`state_expanded_medicaid` is CMS's reported status for the period. It is not a full legislative treatment-date or eligibility-policy database. A causal design needs independently validated policy timing, reporting changes and appropriate comparison assumptions. State aggregates support descriptive comparisons and policy covariates; they do not identify individual treatment effects.

State postal abbreviations are strings. Join to annual county datasets only after choosing and documenting temporal alignment and aggregation; a state-month record does not have county-level variation. No synthetic county allocation or FIPS crosswalk is added.

All source cells round-trip through the normalized types: field names and raw headers are recorded in `field_definitions`, and source record positions are retained. Integer values are nonnegative, exact BIGINTs; rates retain up to six decimal places. A new unknown token or duplicate key is a build failure, not an automatic NULL or row deletion.
