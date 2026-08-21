# United States university graduate ability

Ranks U.S. universities and majors by the estimated age-18 academic ability of
their bachelor's graduates. Nothing here reflects research output or reputation.

First pass: 2,356 institutions and 64,314 institution-major pairs, using 2022–23
degrees, fall 2019 admission-route counts, fall 2014–2023 test-score bars, and
2023 transfer outcomes. The current score is a rough test-taker percentile proxy;
converting it to the full age-18 scale is still in progress.

Known limitations and planned work live in `TODO.md`.

## Repository layout

- Root Python files are commands for generating outputs, fetching inputs, and
  inspecting evidence.
- `uniusa/` contains the reusable undergraduate model and parsers;
  `uniusa/professional/` contains the law and medicine extensions.
- `tests/` contains regression and fuzz checks, while `assets/` contains the
  static evidence-report template.
- `sources/` and `derived/` are respectively local inputs and generated
  intermediates. Only their documentation is committed.

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

- `schools.tsv` — 2,356 final institutions, ordered by `cohort_median`
- `majors.tsv` — 85,711 institution-major pairs; major scores currently inherit
  the institution score
- `derived/final_admission_paths.tsv` — the exhaustive national table above
- `derived/institution_final_routes.tsv` — the same mutually exclusive routes
  at each final institution
- `derived/transfer_origin_scores.tsv` — origin scores and transfer-out weights
- `derived/transfer_score.tsv` — pooled transfer score and coverage by origin type
- `derived/route_ability.tsv` — route allocations on the school ability scale
- `derived/graduate_median_ability.tsv` — each school's graduate-median ability as
  a percentile of the age-18 cohort
- `law-schools.tsv` — 2024 ABA entering classes scored from LSAT quartiles
- `medical-schools.tsv` — MD schools scored from median MCAT and 2023 matriculants

`bachelors` is the mean annual domestic award count over the completions years
2014–2023, counting only the years an institution reports. Major rows average
the same way and then rescale onto that school mean, which absorbs the 0.2% of
awards filed under CIP codes retired before the CIP2020 taxonomy. `satnum_pct`
and `actnum_pct` give the enrolled SAT and ACT submitters as a percentage of the
entering class, averaged over the admission years 2014–2023 in which a school
reports at least one submitter. IPEDS never counts students who submitted
neither test, so `no_test_pct` averages the leftover share of each entering
class, `max(0, ENRLT - SAT - ACT) / ENRLT`. A year with no reported submitter is
missing data rather than a class without scores, which leaves all three columns
blank for the 899 schools that never report. Students who sent both tests appear
in each submitter count, so the three percentages need not sum to 100.

`ability_pool_ratio` asks how many students nationally could clear a school's
published bar for each seat at that bar or above. A q25 bar sits above three
quarters of that route's submitters, so the seats it competes for are
`0.75 * SATNUM` and `0.75 * ACTNUM`. The SAT pool is the national test-taker
total times the share scoring above the school's `SATVR25 + SATMT25`; the ACT
pool sums the composite frequencies at or above `ACTCM25`. Each year sums both
pools and both seat counts before dividing, and the column averages that ratio
over 2017–2019, the years with published national SAT taker totals.

The denominator counts every seat behind a bar at least as high, running each
route down its own bar order, so a student who clears a school's bar is measured
against everywhere else they could have gone. Schools sharing a bar share a
total, which matters because the ACT composite is a coarse integer: 178 schools
posted a 19 in 2019. Dividing by a school's own seats instead made the ratio
scale with how few seats it has, which put Harvey Mudd at 464 against
Princeton's 141; against seats at that bar or above they read 29 and 8. Caltech
holds the highest SAT and ACT bar of the 1,280 schools with one, so nothing
sits above it and its ratio is unchanged.

Downloaded sources and generated tables stay local and out of Git.

Run `python3 outputs.py --schools-only` to regenerate `schools.tsv`, then
`python3 professional_outputs.py` to regenerate both professional-school files.
Run `python3 viz_medical_applicants.py` for the applicant-distribution chart.

## Professional schools

Law converts each school's LSAT q25, median, and q75 to exact LSAT-taker
percentiles, maps each rank onto the bachelor-weighted distribution of
undergraduate school ability, and averages the three results. This is a
provisional bridge: ABA supplies the destination counts and LSAT bars, but no
recent public origin-by-undergraduate-school table. `lsat_share` shows how much
of the entering class supplied an LSAT; GRE and JD-Next entrants remain unscored.

Medicine maps the median MCAT rank onto the AAMC applicant-weighted mixture of
undergraduate-school ability distributions. Each school CDF reconstructs its
SAT/ACT submitter distribution from the published q25 and q75 bars, with the
current no-score and transfer assumptions, so high-performing applicants are
not capped at their undergraduate school's median.
AAMC's table covers the 39,763 applicants from institutions supplying at least
50 applicants, or 75.6% of all 52,577 applicants. We match an undergraduate
school to 94.6% of that published mass and have usable school distributions for
93.3%. Whole-number MCAT percentile ties are spread evenly within their
rounding intervals. The school MCAT table is a secondary transcription of MSAR
because AAMC does not publish a free bulk school-level score table.

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

`schools.tsv` records one SAT center averaged across available fall 2016–2023
observations and one ACT center averaged across fall 2014–2023. Its
`freshman_score` gives the available SAT and ACT route means equal weight. Both
tests use the annual national taker distribution nearest the admission year; ACT
published a graduating-class profile for 2018 and 2020–2025 but never for 2019.
Schools are ordered by `cohort_median`, the age-18 percentile below; the 1,369
schools without one hold their old `freshman_score` order beneath the ranked
head.

## Graduate median on the cohort scale

`intake_ability.py` places schools on the age-18 population rather than on test
takers. The SAT and ACT together are taken to cover the top of the cohort, so
their reach is `SAT + ACT - dual takers` over the 4,357,485-person age-18
population: 69.5% in 2017, 75.8% in 2018 and 77.1% in 2019, as school-day SAT
testing pulled in students who would not otherwise have sat either test. A score
beating share `s` of its own test's takers lands at cohort percentile
`100 * (1 - s * reach)`.

Only one year's dual-taker count exists: College Board and ACT matched about
600,000 of them in the 2017 graduating class for their concordance study. Later
years scale that count by the product of the two taker pools, which holds the
2017 association between sitting one test and sitting the other. Everything else
in this section is computed separately for each admission year and averaged only
at the end.

The reach puts all four published bars — SAT and ACT quartiles — on one axis.
Each route's submitters are given a normal pinned to its two bars, so ability
interpolates between quartiles in standard deviations rather than in percentile
points. IPEDS counts a dual submitter under both tests, but dual submitters clear
a bar at the same rate as the whole submitting group, so the overlap cancels from
the submitter-weighted share and only the distinct head count survives. That head
count is `min(SATNUM + ACTNUM, ENRLT)`; students who sent neither test are placed
below every bar.

The curve counts entrants while the median counts graduates, which the transfer
model bridges. Transfers in enter as the school's weakest students, so the median
graduate is a freshman unless transfers take more than half the degrees. Leaving
is independent of ability, so the freshmen who stay keep the entering class's
distribution and the median graduate's quantile among direct graduates is its
quantile among entrants. The median is therefore read at
`entrants * (bachelors / 2) / direct graduates`, using the same transfer counts
as `derived/institution_final_routes.tsv`.

Of 1,368 schools, 1,044 get a median. Transfers take more than half the degrees
at 280, and at 44 the median graduate sent no score; both are left blank. Another
231 have a median that falls outside every published quartile, where the answer
rests on an assumed tail. Setting `QUARTILE_MODEL = "uniform"` spreads each
quartile evenly across percentile points instead, which reads about one
percentile lower at the median school and much lower outside the bars.

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

Slow inputs are preprocessed once into `derived/`, then read back on later runs:
`first_major_awards.tsv` for the latest completions archive,
`school_bachelors_by_year.tsv` and `major_bachelor_means.tsv` for the ten-year
award means, and `class_rank.tsv` for the parsed Common Data Set C10 tables.
Each rebuilds itself when a source is newer or when a needed school is missing,
so no manual invalidation step is required.

To regenerate only `schools.tsv` from the downloaded sources, without rewriting
either majors table:

```sh
python3 outputs.py --schools-only
```

To rebuild every intermediate table and both canonical outputs:

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
python3 intake_ability.py
python3 outputs.py
```

`python3 school_evidence.py "<name>"` prints one school's admission counts,
survey answers, and Common Data Set class-rank history. `python3 rank_ability.py`
fits the class-rank model: national ability is standard normal, a high school's
mean carries `BETWEEN_SCHOOL_VARIANCE` of it, and class rank is the normal CDF of
the remaining within-school position. Only the top-decile anchor identifies a
school, because the top-quarter anchor saturates at 100% wherever the model is
worth running. The class spread is fitted once across schools with both a C10 and
a published test percentile.

`python3 viz_test_evidence.py` renders `test_evidence.html` from
`test_evidence_template.html`, charting how test-score evidence at the top of the
ranking broke in 2021.
