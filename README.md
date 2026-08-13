# United States university graduate ability

Ranks U.S. universities and majors by the estimated age-18 academic ability of
their bachelor's graduates. Nothing here reflects research output or reputation.

First pass: 2,356 institutions and 64,314 institution-major pairs, using 2022–23
degrees, fall 2019 admissions data, and 2023 transfer outcomes. The current score
is a rough test-taker percentile proxy; converting it to the full age-18 scale is
still in progress.

Known limitations and planned work live in `TODO.md`.

## Admission paths

The endpoint is the final bachelor's institution, so transfer status is defined
when a student enters that institution. These rows partition the age-18 population.

| Path | How it works | People | Share | Ability evidence |
| --- | --- | ---: | ---: | --- |
| No bachelor's | No degree in the annual flow | 2,459,942 | 56.45% | Bottom mass |
| Freshman | No prior college at final school | 1,096,408 | 25.16% | SAT/ACT at final school |
| Transfer | Prior college at final school | 801,135 | 18.39% | Freshman score at origin |
| **Total** |  | **4,357,485** | **100.00%** |  |

The degree flow is 1,897,543 domestic bachelor's awards, defined as all IPEDS
awards less nonresident aliens. The freshman/transfer split comes from the
2015–16 Outcome Measures cohorts that completed a bachelor's by 2023. Annual
degrees are a provisional bridge to the 2023 age-18 population, not a literal
cohort count.

SAT and ACT remain separate evidence routes because their test-taking populations
differ. A student may submit both, so test submissions are not admission paths
and are not added in the table. Open admission, class rank, athletics, portfolios,
and military selection operate inside the freshman path.

## Outputs

- `schools.tsv` — 2,356 final institutions, ranked where a rough score is available
- `majors.tsv` — 64,314 institution-major pairs; major scores currently inherit
  the institution score
- `derived/transfer_origin_scores.tsv` — origin scores and transfer-out weights
- `derived/transfer_score.tsv` — pooled transfer score and coverage by origin type
- `derived/institution_graduates.tsv` — degree weights and destination transfer shares

Downloaded sources and generated tables stay local and out of Git.

## Coverage

Fall 2019 SAT or ACT score bars cover 1,224 institutions awarding 1,499,079
domestic bachelor's degrees, 79.0% of the degree flow. Adding the pooled transfer
component gives a provisional score to 2,201 institutions covering 1,892,900
degrees, 99.76% of the flow.

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

An institution's freshman score is the median of its available SAT and ACT route
centers. The SAT center averages the reading/writing and math median percentile
ranks; the ACT center uses the composite median percentile rank. Both use
percentiles among actual test takers.

The pooled transfer score is the transfer-out-weighted median of origin-school
freshman scores. Unscored origins use their institution-type median. This first
pass gives `65.626`.

For final institution `y`, the rough score is

`score_y = (1 - transfer_share_y) freshman_score_y + transfer_share_y transfer_score`.

`transfer_share_y` comes from the direct and transfer entrants who eventually
earned a bachelor's at `y`; it supplies the final mixture count without changing
either group's ability distribution.

If a component is missing, `ability_coverage` records the represented mixture
weight. A major currently inherits its final institution's score because IPEDS
does not publish major-specific freshman test bars.

The final age-18 scale will first rank bachelor recipients on a common ability
scale, then prepend the no-bachelor mass. If `p` is a percentile among bachelor
recipients, the preliminary conversion is `56.45 + 0.4355 p`.

## Sources

`sources/README.md` lists the fixed Census, IPEDS, College Board, ACT, and CIP
inputs. `fetch_sources.py` pins each file by SHA-256.

## Rebuild

```sh
python3 fetch_sources.py
python3 pathways.py
python3 ability.py
python3 calibrate_tests.py
python3 special_routes.py
python3 origins.py
python3 transfer.py
python3 outputs.py
```
