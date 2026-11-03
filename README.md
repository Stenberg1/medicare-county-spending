# Medicare Spending Across US Counties

Why does Medicare spend more per person in some counties than others? This project looks at standardized Medicare spending per beneficiary across about 3,000 US counties from 2014 to 2024, and how it relates to income, poverty, and rurality.

**Write-up with interactive charts:** [gstenberg.org/medicare](https://gstenberg.org/medicare)

![Python](https://img.shields.io/badge/Python-3.14-blue) ![DuckDB](https://img.shields.io/badge/SQL-DuckDB-yellow) ![statsmodels](https://img.shields.io/badge/stats-statsmodels-lightgrey) ![Plotly](https://img.shields.io/badge/charts-Plotly-purple)

**[County explorer](https://medicare-county-spending-lcjbh9guvrrpwwaejzdwks.streamlit.app/):** pick any county and compare it with the 10 counties most like it (`app/explorer.py`, built with Streamlit).

## Key findings

- **Spending grew about 37%** per beneficiary from 2014 to 2024 (nominal), at the same pace in metro and rural counties.
- **Richer counties do not spend more.** In 2024, higher-income counties spent slightly less per beneficiary, especially among rural counties.
- **Rural counties spend about $620 less** per beneficiary than comparable metro counties, after controlling for income, poverty, age, Medicaid enrollment, and Medicare Advantage share ($860 less when weighting by beneficiaries).
- **Poverty, not income, carries the signal:** each additional point of poverty rate is associated with about $89 more per beneficiary.
- **Outlier:** Miller County, GA spent $29,853 per beneficiary in 2024, more than twice the national average, with skilled nursing facility spending about 10 times the national level.

- **More than half the variation is unexplained, and it is regional and persistent.** Florida, Oklahoma, Texas, and Mississippi spend $1,500 to $2,100 more per beneficiary than the model predicts; Hawaii, Alaska, Oregon, and Washington spend $2,000 to $3,700 less. A county's unexplained spending in 2014 to 2018 correlates 0.88 with 2020 to 2024.
- **More spending does not buy better outcomes.** Counties in the top fifth of unexplained spending have an 18.8% 30-day readmission rate vs. 16.1% in the bottom fifth. Each extra $1,000 per beneficiary goes with about 0.6 points more readmissions and 30 more ER visits per 1,000, robust to weighting, non-hospital spending only, and county fixed effects.

These are associations across counties, not causal effects.

## Regression

County-year panel, 2014 to 2024. Outcome: standardized Medicare spending per beneficiary. Year fixed effects; standard errors clustered by state (50 clusters).

| | OLS | Weighted by beneficiaries |
|---|---:|---:|
| Rural (vs. metro) | −616*** | −858*** |
| Poverty rate (pp) | 89*** | 77** |
| Median income ($10K) | −82 | −90 |
| Average age (years) | 257*** | 309*** |
| Dual-eligible share (pp) | 34** | 34** |
| Medicare Advantage share (pp) | 1 | 12 |
| N (county-years) | 32,366 | 32,366 |
| R² | 0.42 | 0.47 |

\*\*\* p<0.01, \*\* p<0.05. Full output in [notebooks/04_regression.ipynb](notebooks/04_regression.ipynb).

## Data

| Source | Used for | File |
|---|---|---|
| [CMS Medicare Geographic Variation, by National, State & County](https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-geographic-comparisons/medicare-geographic-variation-by-national-state-county) (2014 to 2024) | spending, beneficiaries, age, dual eligibility, MA share | `data/2014-2024-Medicare-data.csv` (not in repo, 57 MB) |
| [Census SAIPE](https://www.census.gov/programs-surveys/saipe.html), via the Census API | median household income, poverty rate | pulled by notebook 01 |
| [USDA Rural-Urban Continuum Codes 2023](https://www.ers.usda.gov/data-products/rural-urban-continuum-codes) | metro (codes 1 to 3) vs. rural (4 to 9) | `data/rucc_2023.csv` |
| [Census 2023 cartographic boundaries](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html) | county map | `data/counties_2023.geojson` |

**Sample:** counties with at least 500 Original Medicare beneficiaries (smaller counties have very noisy averages), 50 states, US territories excluded. 32,699 county-years across 3,011 counties. Over 99.7% of rows match the income and rurality data; the exceptions are Connecticut before its 2022 switch to planning regions and one Alaska area that was split in 2019.

## County explorer: how similar counties are chosen

Counties are matched on income, poverty, average age, dual-eligible share, Medicare Advantage share, and rural-urban code, **never on spending**, so the comparison asks: among counties like this one, does it spend more or less? Each variable is converted to a z-score within its year, and the similar counties are those with the smallest Euclidean distance across the six z-scores (equal weights).

## Repository

```
notebooks/
  01_build_database.ipynb   load CMS data, clean, pull Census income/poverty
  02_merge.ipynb            reshape RUCC, merge everything, check match rates
  03_charts.ipynb           exploratory charts; exports the website charts
  04_regression.ipynb       OLS and weighted regressions, robustness checks, unexplained spending, outcomes
  05_export_app_data.ipynb  z-scores for matching; writes app/data/*.parquet
  plot_style.py             shared chart colors and fonts
app/
  explorer.py               Streamlit county explorer
  data/                     the app's data (small Parquet files, committed)
scripts/
  make_county_geojson.py    builds the county map file from Census shapefiles
site/medicare/              the project web page and its interactive charts
data/                       input files (see table above)
```

## Reproduce

1. Clone the repo and create an environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Download the CMS Geographic Variation file (national, state, and county, 2014 to 2024) as CSV and save it as `data/2014-2024-Medicare-data.csv`.
3. Get a free [Census API key](https://api.census.gov/data/key_signup.html) and create a file named `.env` in the project folder:
   ```
   CENSUS_API_KEY=your_key_here
   ```
4. Run the notebooks in order, 01 to 05. They build `medicare.duckdb`, write the website charts to `site/medicare/charts/`, and export the explorer's data to `app/data/`.
5. Start the county explorer:
   ```bash
   streamlit run app/explorer.py
   ```

DuckDB allows only one program to write to the database at a time, so close the connection (`con.close()`) in one notebook before running the next.

**Optional, for contributors:** `.gitattributes` strips outputs from `03_charts.ipynb` on commit, because its embedded map makes it about 7 MB after a run. To turn that on in your clone, run once from the project folder:

```bash
git config filter.strip-notebook-output.clean '.venv/bin/jupyter nbconvert --to notebook --ClearOutputPreprocessor.enabled=True --ClearMetadataPreprocessor.enabled=True --stdin --stdout --log-level=ERROR'
git config filter.strip-notebook-output.smudge cat
```
