# Source bundle

These are the fixed source tables used by the analysis. The files are downloaded locally and ignored by Git; only this manifest is tracked. The SAT history compilation is the one non-publisher-hosted input and is labeled below.

| File | Publisher | Coverage | URL |
|---|---|---|---|
| `nc-est2023-agesex-res.csv` | U.S. Census Bureau | July 1, 2023 resident population by single year of age and sex | <https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/national/asrh/nc-est2023-agesex-res.csv> |
| `HD2023.zip` | NCES IPEDS | Fall 2023 institutional directory | <https://nces.ed.gov/ipeds/datacenter/data/HD2023.zip> |
| `ADM2019.zip` | NCES IPEDS | Fall 2019 first-year admissions, test policy, and submitted-test summaries | <https://nces.ed.gov/ipeds/datacenter/data/ADM2019.zip> |
| `ADM2019_Dict.zip` | NCES IPEDS | Definitions and code values for 2019 admissions considerations | <https://nces.ed.gov/ipeds/datacenter/data/ADM2019_Dict.zip> |
| `ADM2017.zip`, `ADM2018.zip` | NCES IPEDS | Earlier redesigned-SAT admissions bars used only for the selective-school stability check | <https://nces.ed.gov/ipeds/datacenter/data/ADM2017.zip> |
| `IC2019.zip` | NCES IPEDS | Fall 2019 institutional characteristics, including open-admission status | <https://nces.ed.gov/ipeds/datacenter/data/IC2019.zip> |
| `IC2019_Dict.zip` | NCES IPEDS | Data dictionary for the preceding file | <https://nces.ed.gov/ipeds/datacenter/data/IC2019_Dict.zip> |
| `EF2019A.zip` | NCES IPEDS | Fall 2019 enrollment by undergraduate entry status | <https://nces.ed.gov/ipeds/datacenter/data/EF2019A.zip> |
| `EF2019A_Dict.zip` | NCES IPEDS | Data dictionary for the preceding file | <https://nces.ed.gov/ipeds/datacenter/data/EF2019A_Dict.zip> |
| `EFFY2024.zip` | NCES IPEDS | Unduplicated enrollment from July 1, 2023 through June 30, 2024 | <https://nces.ed.gov/ipeds/datacenter/data/EFFY2024.zip> |
| `EFFY2024_Dict.zip` | NCES IPEDS | Data dictionary for the preceding file | <https://nces.ed.gov/ipeds/datacenter/data/EFFY2024_Dict.zip> |
| `C2023_A.zip` | NCES IPEDS | 2022–23 completions by institution, award level, field, residency, race, and sex | <https://nces.ed.gov/ipeds/datacenter/data/C2023_A.zip> |
| `C2023_A_Dict.zip` | NCES IPEDS | Data dictionary for the preceding file | <https://nces.ed.gov/ipeds/datacenter/data/C2023_A_Dict.zip> |
| `OM2023.zip` | NCES IPEDS | Eight-year outcomes for the 2015–16 entering cohort, split by first-time status | <https://nces.ed.gov/ipeds/datacenter/data/OM2023.zip> |
| `OM2023_Dict.zip` | NCES IPEDS | Data dictionary for the preceding file | <https://nces.ed.gov/ipeds/datacenter/data/OM2023_Dict.zip> |
| `GR2023.zip` | NCES IPEDS | Transfer-out counts for first-time, full-time cohorts at origin institutions | <https://nces.ed.gov/ipeds/datacenter/data/GR2023.zip> |
| `GR2023_Dict.zip` | NCES IPEDS | Data dictionary for the preceding file | <https://nces.ed.gov/ipeds/datacenter/data/GR2023_Dict.zip> |
| `SAT-national-percentiles.html` | College Board | SAT section-score percentiles; the calculation uses only the User Group columns based on actual test takers | <https://research.collegeboard.org/reports/sat-suite/understanding-scores/sat> |
| `sat-percentile-1600.csv` | Historical SAT table compilation | Annual College Board SAT-user percentile tables; used to recover the 2019 table and spread each rounded percentile interval across its score buckets | <https://docs.google.com/spreadsheets/d/e/2PACX-1vRVCIukssgc3z5-8GpH3achzkJhbxD0TID_q8Xa-1oZIsF_NMy-U5exxEUr8EZi2Q/pubhtml#gid=273576492> |
| `2017-total-group-sat-report.pdf`–`2019-total-group-sat-report.pdf` | College Board | Annual redesigned-SAT test-taker totals used in the q25-bar/seat diagnostic | <https://reports.collegeboard.org/sat-suite-program-results/data-archive> |
| `2018-act-national-profile.pdf` | ACT | Exact ACT composite score frequencies for the 2018 tested graduating class, Table 2.1 | <https://www.act.org/content/dam/act/unsecured/documents/cccr2018/P_99_999999_N_S_N00_ACT-GCPR_National.pdf> |
| `CIP2020-browse.html` | NCES IPEDS | Complete 2020 Classification of Instructional Programs code and title list | <https://nces.ed.gov/ipeds/cipcode/browse.aspx?y=56> |

Run `python3 fetch_sources.py` to verify or restore the local copies. The downloader pins the SHA-256 digest of every input. `calibrate_tests.py` uses `pdftotext -layout` to parse the ACT table.
