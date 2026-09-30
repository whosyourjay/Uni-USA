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

The 2013 and 2014 observations come from the raw data accompanying Baron et al.,
[Signatures of medical student applicants and academic success](https://doi.org/10.1371/journal.pone.0227108)
(2020), S1 Data, released under CC BY. The pinned workbook is
`sources/nyu-medicine-2006-2014.xlsx`; `medicine_history.study_observations`
recomputes the medians from its `Raw data` sheet. The paper describes 2006–2014
matriculating cohorts (the workbook calls the field `Application year`). These
are **research samples**, not full-class profiles: 117 scored students in 2013
and 106 in 2014, with median supplied MCAT percentiles 95.7 and 97.4. Their
sample sizes supply the chart weights. No raw old-scale MCAT score is inferred,
and old-scale scores are never run through the new-scale percentile table.

The comparison report holds the medical leader in **Top universities** fixed
(currently NYU Grossman); it does not claim to have collected all-year histories
for every medical school. Every medical entry year Y is calibrated using actual
freshman admissions from Y−4: **2013 → 2009**, **2022 → 2018**, **2026 → 2022**.
The plotted date remains Y. Regenerate from `compare` with:

```sh
python -m history.build --country US
python -m pages.report --history-only-from ../Uni-Compare-Report/index.html
python publish.py --page overview
```

`uniusa.professional.medicine_history` constructs annual normal-in-z school CDFs
from freshman score centers and interquartile spreads. Centers use the existing
mean-of-quartiles / median-of-SAT-and-ACT rule; spreads weight the observed routes
by submitter counts. SAT uses annual CR+Math / ERW+Math tables; ACT retains the
fixed 2018 reference. ACT quartile cutoffs use the original medical model's
inclusive upper-tail counts: students tied at the cutoff remain in the tail.
Thus ACT 36 starts at percentile 99.8046, not 100; it must not become a
near-infinite normal-score anchor. Regression tests cover this ceiling and
verify that changing the numerical clipping epsilon cannot alter the fit.
The historical calculation does **not** reuse current
school medians or transfer estimates. Thus this freshman-based history is not
the current graduate-adjusted professional ranking.

The MCAT percentile is inverted through an applicant-weighted mixture of these
annual school CDFs, directly on the report's native U.S. test-taker scale. Later
raw MCAT scores retain the existing 2024 percentile table; the early research
data already supplies old-MCAT percentiles. The observed 2023 AAMC feeder
weights are held fixed, as historical origin counts have not been collected.
Only feeder schools with scores in every requested freshman cohort enter this
comparison: 140 schools representing 69.8% of the published applicant weights
(not 69.8% of all U.S. applicants). Keeping the panel fixed prevents changing
missing-school composition from masquerading as drift. Test-optional policies
can still change which students are represented within those schools.

Missing 2015–2016 and 2019–2020 medical observations remain missing. The
calibration cannot supply an absent school MCAT observation. A 2009 calibration
benchmark took 0.65 seconds; rebuilding the ten medical points took 7.45 seconds.

For the undergraduate history, `compare` explicitly requests IPEDS 2009–2023.
`uniusa.ability.load_admissions` reads the IC component through 2013 and ADM
thereafter. It uses the existing ACT calculation before the comparable redesigned
SAT years (2016 onward). The main U.S. ranking's averaging window is unchanged.
