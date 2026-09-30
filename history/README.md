# Historical entering classes

`nyu-grossman.tsv` is a transcription of NYU's own entering-class counts and
median MCAT scores, checked on 2026-10-01. Each row links the original source
and identifies the relevant heading or page. The 2021–2023, 2025 and 2026 HTML
sources are pinned in `fetch_sources.py`. The three PDF transcriptions were
checked against indexed publisher text; direct downloads currently return 503,
so those PDFs are linked, not claimed to be in the local source bundle.

Years mean **entry**, not graduation. In particular the Class of 2028 entered
in 2025, following the switch to a three-year curriculum. Counts use the full
published incoming class (including MD/PhD and, where reported, oral surgery).
NYU Long Island is a different school and is excluded. NYU School of Medicine
was renamed NYU Grossman School of Medicine; this is one continuous institution.
The 2017 annual report's count of 119 is used with its MCAT median, rather than
mixing in the ceremony announcement's count of 120. Uncollected 2019–2020
observations are absent, not interpolated. An accepted-class profile is not a
substitute for an entering-class profile.

The comparison report holds the medical leader in **Top universities** fixed
(currently NYU Grossman); it does not claim to have collected all-year histories
for every medical school. `compare/history/sources.py` converts each MCAT using
the identical score knot in the generated `medical-schools.tsv`. This reuses
the existing 2024 MCAT percentile / 2023 applicant-origin calibration without
refitting, approximating it, or confusing MCAT-test-taker percentiles with the
report's native U.S. scale. Unknown score knots fail rather than extrapolate.

For the undergraduate history, `compare` explicitly requests IPEDS 2009–2023.
`uniusa.ability.load_admissions` reads the IC component through 2013 and ADM
thereafter. It uses the existing ACT calculation before the comparable redesigned
SAT years (2016 onward). The main U.S. ranking's averaging window is unchanged.
