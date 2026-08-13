# Source bundle

These are the complete official tables used by `pathways.py`, not a scraped sample. The files are downloaded locally and ignored by Git; only this manifest is tracked.

| File | Publisher | Coverage | URL |
|---|---|---|---|
| `nc-est2023-agesex-res.csv` | U.S. Census Bureau | July 1, 2023 resident population by single year of age and sex | <https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/national/asrh/nc-est2023-agesex-res.csv> |
| `HD2023.zip` | NCES IPEDS | Fall 2023 institutional directory | <https://nces.ed.gov/ipeds/datacenter/data/HD2023.zip> |
| `ADM2019.zip` | NCES IPEDS | Fall 2019 first-year admissions, test policy, and submitted-test summaries | <https://nces.ed.gov/ipeds/datacenter/data/ADM2019.zip> |
| `ADM2019_Dict.zip` | NCES IPEDS | Definitions and code values for 2019 admissions considerations | <https://nces.ed.gov/ipeds/datacenter/data/ADM2019_Dict.zip> |
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

Run `python3 fetch_sources.py` to verify or restore the local copies. The downloader pins the SHA-256 digest of every input.
