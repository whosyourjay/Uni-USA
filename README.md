# U.S. bachelor-graduate ability

The goal is to estimate the distribution of academic ability at age 18 conditional on the bachelor's degree a person eventually receives:

`ability | final bachelor's institution`

The denominator is every U.S. resident at age 18, including people who never attend college. The unit being ranked is the **final degree institution**, not the institution of first admission.

This pass is deliberately a single recent cross-section: 2023 population, 2022–23 bachelor's awards, fall 2023 admissions, and the Outcome Measures release available in 2023. Vintage alignment is deferred in [`TODO.md`](TODO.md).

## Pathways to the final degree

| Path | Estimated people | Share of all age-18 residents |
|---|---:|---:|
| No bachelor's degree | 2,459,942 | 56.45% |
| Bachelor's, no prior college on entry to final institution | 1,096,408 | 25.16% |
| Bachelor's, prior college before final institution | 801,135 | 18.39% |
| **Total** | **4,357,485** | **100.00%** |

The no-degree row is the residual after subtracting 1,897,543 domestic bachelor's awards from the 4,357,485 U.S. residents age 18. The remaining bachelor flow is split using IPEDS Outcome Measures: among 2015–16 entrants who earned a bachelor's at that institution by 2023, 57.78% had no prior college when they entered the final institution and 42.22% had prior postsecondary experience. Applying that split gives the two estimated graduate rows above; they are not separate annual headcounts.

Thus, if a within-graduate ability percentile is `p`, its preliminary all-age-18 percentile is `56.45 + 0.4355 p`. This is still a flow-to-cohort approximation: annual awards are not unique eventual graduates from the current age-18 cohort, and “domestic” currently means the IPEDS total less nonresident aliens.

A transfer is an event, so annual first-time and transfer-in counts cannot be added nationally: the same person may first enter one institution and later enter another. Outcome Measures instead partitions graduates by how they entered their final institution. Its “non-first-time entering” category does not require transferred credit. Institutions with a usable route estimate account for 99.79% of current domestic bachelor's awards.

The institution universe comes from actual 2022–23 bachelor's completions, with no sector, ranking, or “four-year college” filter. Low-prestige, open-admission, online, specialized, and transfer-serving universities remain in the 2,356-institution file.

The route mixture varies too much to substitute a national constant. Among the 2015–16 entering cohorts who earned a bachelor's there within eight years, the transfer share is 0.24% at Harvard, 0.83% at Stanford, 29.85% at Berkeley, 35.63% at UCLA, 35.04% at Columbia, and 91.11% at the University of Phoenix-Arizona. These are pathway shares, not ability estimates.

## Admission routes into the institution

The first row above is not itself an admissions route. U.S. institutions judge the same freshman through several channels, so unlike a centralized allocation system the rows below are deliberately **not additive**.

| Route | How it works | Fall 2023 enrolled submitters | Share of the reporting pool | Ability evidence |
|---|---|---:|---:|---|
| SAT | SAT submitted; institution also applies its other criteria | 369,411 | 22.12% | 25th, 50th and 75th percentiles |
| ACT | ACT submitted; institution also applies its other criteria | 316,572 | 18.96% | 25th, 50th and 75th percentiles |
| No reported SAT/ACT | Transcript/GPA and institution-specific review, or test-blind admission | 989,991–1,130,419 | 59.29%–67.70% | No common national score |
| Open admission | Published entrance requirements rather than selective review | Not yet counted | — | No comparable admission cutoff |
| Transfer | Prior-college GPA, transferable courses/credits, prerequisites and sometimes essays | 801,135 estimated final graduates | 18.39% of age 18 | Origin ability plus later college evidence |
| Other special channels | Portfolios/auditions, recruited athletics, service-academy nomination and other institutional programs | Not separately counted | — | Route-specific or none |

The first three rows cover 1,669,785 enrolled first-time students at the 1,708 bachelor's institutions in the IPEDS admissions reporting universe. A student can report both tests, but IPEDS does not publish that overlap. Therefore SAT and ACT stay as separate routes, while the no-test count is an interval: its lower end assumes no overlap and its upper end assumes maximum overlap. There are no SAT-only, ACT-only, or both-test pseudo-routes.

Non-test review is not a single mechanism. Entrant-weighting the IPEDS policies shows that secondary-school GPA was required or considered for 97.87% of this reporting pool and the school record for 97.65%. The same official table separately records rank, college-prep curriculum, recommendations, formal competencies/portfolios, English and other tests, work experience, essays, and legacy. [`derived/freshman_admission_considerations.tsv`](derived/freshman_admission_considerations.tsv) retains all of those non-exclusive bases. It does not pretend that the policy table says which criterion caused an individual admission.

[`derived/institution_graduates.tsv`](derived/institution_graduates.tsv) contains the same calculation for every final institution. Its core columns are:

- `bachelors_domestic`: the institution's additive weight in the final ranking;
- `direct_bachelors_8yr` and `transfer_bachelors_8yr`: people, from the 2015–16 entering cohort, receiving a bachelor's there by 2023;
- `transfer_share_bachelors_8yr`: the mixture weight for the transfer ability component;
- direct and transfer eight-year bachelor completion rates;
- current entry counts, retained as diagnostics but not used as graduate weights.

The cohort pathway counts and the current annual degree counts are different vintages and must not be added. Only the route *share* is carried to the current graduate weight.

## Ability model

For institution `y`, the target distribution is

`F_y(a) = (1 - t_y) F_direct,y(a) + t_y F_transfer,y(a)`,

where `t_y` is the graduate transfer share above. The national distribution then weights `F_y` by the institution's domestic bachelor's count.

The evidence has to follow that equation:

1. **No-prior-college graduates.** `ability.py` retains SAT and ACT as separate native-scale routes, including each route's quartiles and submitter count. At least one complete test distribution is available at institutions producing 1,285,958 (67.77%) of domestic bachelor's awards and 822,070 (77.18%) of observed no-prior-college graduates. A later common ability scale will cross-calibrate the two routes; it will not collapse the route labels or count dual submitters twice.
2. **Transfer graduates.** A final institution's freshman scores do not describe this group. Use a national longitudinal bachelor-recipient sample to estimate pre-college ability differences between direct and transfer graduates by destination type, then apply institution-specific transfer shares. Transfer-dominant institutions without a meaningful freshman intake will necessarily have wider uncertainty.
3. **No reported test.** SAT/ACT submitters are selected even before test-optional admission. High-school record evidence and test-policy status must enter the model; unreported students cannot simply receive a reported-test median.

The active pass will first produce a current-year estimate from these national tables. Historical cohort alignment and a longitudinal transfer bridge are recorded as later upgrades rather than blocking the cross-section.

## Reproduction

Downloaded inputs and generated tables stay local and are ignored by Git. [`sources/README.md`](sources/README.md) lists the nine complete Census/IPEDS files and their official URLs; `fetch_sources.py` pins every SHA-256 digest.

```sh
python3 fetch_sources.py
python3 pathways.py
python3 ability.py
python3 -m unittest -v
```

Primary generated tables:

- `derived/cohort_pathways.tsv`
- `derived/institution_graduates.tsv`
- `derived/institution_ability_evidence.tsv`
- `derived/freshman_ability_routes.tsv`
- `derived/national_freshman_routes.tsv`
- `derived/freshman_admission_considerations.tsv`
- `derived/graduate_pathways_by_level.tsv`
