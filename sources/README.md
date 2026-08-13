# Source bundle

These are the complete official tables used by `pathways.py`, not a scraped sample.

| File | Publisher | Coverage | URL |
|---|---|---|---|
| `nc-est2023-agesex-res.csv` | U.S. Census Bureau | July 1, 2023 resident population by single year of age and sex | <https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/national/asrh/nc-est2023-agesex-res.csv> |
| `HD2023.zip` | NCES IPEDS | Fall 2023 institutional directory | <https://nces.ed.gov/ipeds/datacenter/data/HD2023.zip> |
| `ADM2023.zip` | NCES IPEDS | Fall 2023 first-year admissions and submitted-test summaries | <https://nces.ed.gov/ipeds/datacenter/data/ADM2023.zip> |
| `EFFY2024.zip` | NCES IPEDS | Unduplicated enrollment from July 1, 2023 through June 30, 2024 | <https://nces.ed.gov/ipeds/datacenter/data/EFFY2024.zip> |
| `EFFY2024_Dict.zip` | NCES IPEDS | Data dictionary for the preceding file | <https://nces.ed.gov/ipeds/datacenter/data/EFFY2024_Dict.zip> |

Run `python3 fetch_sources.py` to verify the checked-in copies or restore them. The downloader pins the SHA-256 digest of every input.
