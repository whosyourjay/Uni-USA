# United States university graduate ability

Ranks U.S. universities and majors by the estimated age-18 academic ability of
their bachelor's graduates. Nothing here reflects research output or reputation.

First pass: 2,356 institutions and 64,314 institution-major pairs, using 2022–23
degrees, fall 2019 admissions data, and 2023 transfer outcomes. The current score
is a rough test-taker percentile proxy; converting it to the full age-18 scale is
still in progress.

Known limitations and planned work live in `TODO.md`.

## Admission paths

These mutually exclusive rows cover the full age-18-sized annual flow. Lower
credentials are kept instead of being buried in `No bachelor's`. Within the
bachelor rows, anyone who transfers is removed from their original freshman
route and appears only in `Transfer`.

| Path | People | Share of age 18 |
| --- | ---: | ---: |
| No postsecondary award | 426,832 | 9.80% |
| Certificate under 12 weeks | 104,149 | 2.39% |
| Certificate, 12 weeks–1 year | 501,753 | 11.51% |
| Certificate, 1–2 years | 453,093 | 10.40% |
| Associate's degree | 950,699 | 21.82% |
| Certificate, 2–4 years | 23,416 | 0.54% |
| SAT | 505,227 | 11.59% |
| ACT | 409,306 | 9.39% |
| Open admission | 41,181 | 0.95% |
| Automatic class-rank guarantee | 5,492 | 0.13% |
| Recruited athletics | 157 | <0.01% |
| Audition or portfolio | 9,776 | 0.22% |
| Service-academy nomination | 3,076 | 0.07% |
| GPA/rank | 122,193 | 2.80% |
| Transfer | 801,135 | 18.39% |
| **Total** | **4,357,485** | **100.00%** |

Credential counts are 2022–23 IPEDS awards less nonresident aliens. The residual
is calculated only after subtracting certificates, associate's degrees, and
bachelor's degrees from the 2023 age-18 population. These annual awards can
include older recipients and multiple awards; they are a flow bridge, not a
literal age-18 cohort.

The bachelor flow is 1,897,543. Its freshman/transfer split uses the 2015–16
Outcome Measures cohorts that completed a bachelor's by 2023.

Within each institution, SAT and ACT submissions are fractionally de-overlapped
without creating test-subset rows. The resulting freshman-route mix is applied
only to graduates not assigned to `Transfer`. The unresolved row currently
contains ordinary transcript/GPA/rank review. The automatic-rank row applies the
UT benchmark—75% of Texas freshman spaces—to UT's estimated non-transfer
graduates. The athletics row applies Harvard's 9.5% benchmark only to Harvard.
The audition row counts non-transfer graduates at institutions reporting formal
competency or portfolio as required; its underlying freshman exposure ceiling is
88,931. These are explicit first proxies, not national measurements. Early
rounds and legacy are overlays, not routes.

## Outputs

- `schools.tsv` — 2,356 final institutions, ordered by rough ability
- `majors.tsv` — 64,314 institution-major pairs; major scores currently inherit
  the institution score
- `derived/final_admission_paths.tsv` — the exhaustive national table above
- `derived/institution_final_routes.tsv` — the same mutually exclusive routes
  at each final institution
- `derived/transfer_origin_scores.tsv` — origin scores and transfer-out weights
- `derived/transfer_score.tsv` — pooled transfer score and coverage by origin type

Downloaded sources and generated tables stay local and out of Git.

## Coverage

Fall 2019 SAT or ACT score bars cover 1,224 institutions awarding 1,499,079
domestic bachelor's degrees. The currently scored route mass—SAT, ACT,
automatic rank, service academies, and the pooled transfer proxy—is 1,684,016
bachelor's recipients, 88.75% of the bachelor flow. At least one measured
component gives a provisional score to 2,308 institutions covering 1,896,350
degrees; `ability_coverage` prevents a tiny transfer component from being
mistaken for full coverage.

IPEDS reports 301,856 domestic transfer-outs from the relevant first-time,
full-time cohorts. Origin schools with a measured freshman score account for
55.7% of them. Missing origins receive the weighted median for their institution
type; direct measurement covers only 1.0% of public associate-college transfer-outs.

This is a pooled national transfer estimate. IPEDS transfer-out counts exclude
students who complete at the origin before transferring and do not identify the
destination. Destination-specific origin matrices, starting with public state
systems, will replace the pool as they are added.

## Method

The first pass has three population snapshots:

1. age 18, before college assignment;
2. freshman entry, after students sort into origin institutions;
3. transfer entry, after one possible reassignment to the final institution.

Graduation does not change the score distribution. Final degree counts weight
institutions, but the model makes no ability adjustment for differential dropout.
It also treats the reported transfer origin as the only transfer.

The SAT center averages the transformed percentiles of the published total-score
q25 and q75 anchors; the ACT center does the same with its composite anchors.
Both use percentiles among actual test takers. Within each rounded SAT percentile
label, its implied interval is divided evenly among the score buckets. SAT and
ACT remain separate routes throughout the final mixture.

Across institutions with complete score bars, the SAT mixture contains 846,098
submitters and has center 72.09; the ACT mixture contains 673,599 and has center
76.26.

The pooled transfer score is the transfer-out-weighted median of origin-school
freshman scores. Unscored origins use their institution-type median. This first
pass gives `65.626`.

For each final institution, Outcome Measures estimates the transfer-graduate
share. Those estimates are scaled together to the national 801,135 transfer
total. The remaining graduates are divided among mutually exclusive freshman
routes using the institution's enrolled SAT and ACT submission counts. When the
two counts overlap, they are proportionally rescaled rather than creating a
third test-subset route. The institution score is the count-weighted mean of the
route scores that have been measured.

If a component is missing, `ability_coverage` records the represented mixture
weight. A major currently inherits its final institution's score because IPEDS
does not publish major-specific freshman test bars.

The final age-18 scale must place certificate and associate recipients as well as
bachelor's recipients. The earlier shortcut of prepending one 56.45-point
`no bachelor` mass is no longer used.

## Sources

`sources/README.md` lists the fixed Census, IPEDS, College Board, ACT, and CIP
inputs. `fetch_sources.py` pins each file by SHA-256.

## Rebuild

```sh
python3 fetch_sources.py
python3 pathways.py
python3 ability.py
python3 calibrate_tests.py
python3 sat_seat_ratio.py
python3 special_routes.py
python3 origins.py
python3 transfer.py
python3 final_routes.py
python3 outputs.py
```
