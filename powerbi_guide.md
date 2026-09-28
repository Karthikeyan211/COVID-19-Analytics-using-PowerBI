# Power BI Data Model Guide

## Import
Power BI Desktop → Get Data → Text/CSV → load all 5 files from `data/processed/`.

## Star schema relationships (all 1-to-Many, single direction, dimension → fact)
| From (One) | To (Many) |
|---|---|
| dim_country[CountryCode] | fact_covid_daily[CountryCode] |
| dim_country[CountryCode] | fact_vaccinations[CountryCode] |
| dim_date[DateKey] | fact_covid_daily[DateKey] |
| dim_date[DateKey] | fact_vaccinations[DateKey] |
| dim_variant[VariantID] | fact_covid_daily[VariantID] |

## Setup
1. Change `dim_date[Date]` to type Date, then Table tools → Mark as date table.
2. Sort `dim_date[MonthName]` by `dim_date[Month]`.
3. Create a table named `_Measures` and paste each measure from `dax_measures.dax`.
4. Format percentage measures as %, counts as whole numbers.
