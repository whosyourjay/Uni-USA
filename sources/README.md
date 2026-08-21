# Source bundle

These are the fixed source tables used by the analysis. The files are downloaded locally and ignored by Git; only this manifest is tracked. The SAT history compilation is the one non-publisher-hosted input and is labeled below.

| File | Publisher | Coverage | URL |
|---|---|---|---|
| `nc-est2023-agesex-res.csv` | U.S. Census Bureau | July 1, 2023 resident population by single year of age and sex | <https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/national/asrh/nc-est2023-agesex-res.csv> |
| `HD2023.zip` | NCES IPEDS | Fall 2023 institutional directory | <https://nces.ed.gov/ipeds/datacenter/data/HD2023.zip> |
| `ADM2019.zip` | NCES IPEDS | Fall 2019 first-year admissions, test policy, and submitted-test summaries | <https://nces.ed.gov/ipeds/datacenter/data/ADM2019.zip> |
| `ADM2019_Dict.zip` | NCES IPEDS | Definitions and code values for 2019 admissions considerations | <https://nces.ed.gov/ipeds/datacenter/data/ADM2019_Dict.zip> |
| `ADM2014.zip`–`ADM2018.zip`, `ADM2020.zip`–`ADM2023.zip` | NCES IPEDS | Additional annual SAT/ACT score quartiles averaged into school ability estimates | <https://nces.ed.gov/ipeds/datacenter/data/ADM2014.zip> |
| `IC2019.zip` | NCES IPEDS | Fall 2019 institutional characteristics, including open-admission status | <https://nces.ed.gov/ipeds/datacenter/data/IC2019.zip> |
| `IC2019_Dict.zip` | NCES IPEDS | Data dictionary for the preceding file | <https://nces.ed.gov/ipeds/datacenter/data/IC2019_Dict.zip> |
| `EF2019A.zip` | NCES IPEDS | Fall 2019 enrollment by undergraduate entry status | <https://nces.ed.gov/ipeds/datacenter/data/EF2019A.zip> |
| `EF2019A_Dict.zip` | NCES IPEDS | Data dictionary for the preceding file | <https://nces.ed.gov/ipeds/datacenter/data/EF2019A_Dict.zip> |
| `EFFY2024.zip` | NCES IPEDS | Unduplicated enrollment from July 1, 2023 through June 30, 2024 | <https://nces.ed.gov/ipeds/datacenter/data/EFFY2024.zip> |
| `EFFY2024_Dict.zip` | NCES IPEDS | Data dictionary for the preceding file | <https://nces.ed.gov/ipeds/datacenter/data/EFFY2024_Dict.zip> |
| `C2023_A.zip` | NCES IPEDS | 2022–23 completions by institution, award level, field, residency, race, and sex | <https://nces.ed.gov/ipeds/datacenter/data/C2023_A.zip> |
| `C2023_A_Dict.zip` | NCES IPEDS | Data dictionary for the preceding file | <https://nces.ed.gov/ipeds/datacenter/data/C2023_A_Dict.zip> |
| `C2014_A.zip`–`C2022_A.zip` | NCES IPEDS | Earlier completions years averaged into the school and major award means | <https://nces.ed.gov/ipeds/datacenter/data/C2014_A.zip> |
| `OM2023.zip` | NCES IPEDS | Eight-year outcomes for the 2015–16 entering cohort, split by first-time status | <https://nces.ed.gov/ipeds/datacenter/data/OM2023.zip> |
| `OM2023_Dict.zip` | NCES IPEDS | Data dictionary for the preceding file | <https://nces.ed.gov/ipeds/datacenter/data/OM2023_Dict.zip> |
| `GR2023.zip` | NCES IPEDS | Transfer-out counts for first-time, full-time cohorts at origin institutions | <https://nces.ed.gov/ipeds/datacenter/data/GR2023.zip> |
| `GR2023_Dict.zip` | NCES IPEDS | Data dictionary for the preceding file | <https://nces.ed.gov/ipeds/datacenter/data/GR2023_Dict.zip> |
| `SAT-national-percentiles.html` | College Board | SAT section-score percentiles; the calculation uses only the User Group columns based on actual test takers | <https://research.collegeboard.org/reports/sat-suite/understanding-scores/sat> |
| `sat-percentile-1600.csv` | Historical SAT table compilation | Annual College Board SAT-user percentile tables; used to recover the 2019 table and spread each rounded percentile interval across its score buckets | <https://docs.google.com/spreadsheets/d/e/2PACX-1vRVCIukssgc3z5-8GpH3achzkJhbxD0TID_q8Xa-1oZIsF_NMy-U5exxEUr8EZi2Q/pubhtml#gid=273576492> |
| `2017-total-group-sat-report.pdf`–`2019-total-group-sat-report.pdf` | College Board | Annual redesigned-SAT test-taker totals used in the q25-bar/seat diagnostic | <https://reports.collegeboard.org/sat-suite-program-results/data-archive> |
| `2018-act-national-profile.pdf` | ACT | Exact ACT composite score frequencies for the 2018 tested graduating class, Table 2.1 | <https://www.act.org/content/dam/act/unsecured/documents/cccr2018/P_99_999999_N_S_N00_ACT-GCPR_National.pdf> |
| `CIP2020-browse.html` | NCES IPEDS | Complete 2020 Classification of Instructional Programs code and title list | <https://nces.ed.gov/ipeds/cipcode/browse.aspx?y=56> |
| `common-data-set-repository.html`, `cds-2019/` | Institution-published Common Data Sets, indexed by College Transitions | Standardized 2019–20 C10 freshman class-rank distributions | <https://www.collegetransitions.com/dataverse/common-data-set-repository/> |
| `aba-law-2024.xlsx` | American Bar Association | 2024 first-year class counts, test counts, and LSAT/GRE/JD-Next quartiles | <https://www.abarequireddisclosures.org/Disclosure509.aspx> |
| `lsat-percentiles-2021-2024.pdf` | Law School Admission Council | Exact LSAT percent-below ranks | <https://www.lsac.org/data-research/data/lsat-percentiles> |
| `mcat-percentiles-2024.txt` | Association of American Medical Colleges, mirrored by Harvard | Extracted 2024 MCAT total-score percentile table | <https://adamshouse.harvard.edu/resource/2024mcatpercentilespdf> |
| `aamc-medical-feeders-2023.txt` | Association of American Medical Colleges | Table A-2 undergraduate institutions supplying at least 50 MD applicants, 2023–24 | <https://www.aamc.org/media/35691/download?attachment=> |
| `aamc-medical-matriculants-2023.txt` | Association of American Medical Colleges | Table A-1 MD matriculants by medical school, 2023–24 | <https://www.aamc.org/media/35686/download?attachment=> |
| `medical-school-mcat.html` | Inspira Advantage, transcribed from AAMC MSAR | School-level median MCAT scores | <https://www.inspiraadvantage.com/blog/gpa-and-mcat-scores-for-all-medical-schools> |

Run `python3 fetch_sources.py` to verify or restore the local copies. The downloader pins the SHA-256 digest of every input. `calibrate_tests.py` uses `pdftotext -layout` to parse the ACT table.
Run `python3 class_rank.py --fetch` separately to collect and parse the fixed 20-school class-rank sample.
