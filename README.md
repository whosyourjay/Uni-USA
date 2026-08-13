# U.S. bachelor-graduate ability

The goal is to estimate the distribution of academic ability at age 18 conditional on the bachelor's degree a person eventually receives:

`ability | final bachelor's institution`

The denominator is every U.S. resident at age 18, including people who never attend college. The unit being ranked is the **final degree institution**, not the institution of first admission.

This pass uses one outcome year and one admissions baseline. Final-institution weights are 2022–23 bachelor's awards, the population denominator is 2023, and transfer shares come from the Outcome Measures release available in 2023. Freshman admission evidence is **fall 2019**, the last entering class wholly before COVID-era test-optional and test-blind changes. It is also the conventional four-year predecessor of the 2022–23 graduating class. Later and earlier admissions vintages are deferred in [`TODO.md`](TODO.md).

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

## Freshman paths into the institution

The 2023 admissions cross-section is unsuitable for the ability model: widespread pandemic-era test-optional policies and permanent test-blind policies make an enormous unscored remainder. The fall-2019 baseline produces the following **additive** decomposition of all 1,944,624 first-time degree-seeking entrants at institutions that currently award bachelor's degrees.

| Admission path | Fall 2019 entrants | Share of all first-time entrants | Ability evidence |
|---|---:|---:|---|
| Selective: admission test required | 1,291,303 | 66.40% | Required test; institution-level SAT and/or ACT distributions where published |
| Selective: admission test recommended | 100,883 | 5.19% | Submitted test where observed, plus the institution's enumerated school criteria |
| Selective: admission test considered but not required | 139,753 | 7.19% | Submitted test where observed, plus the institution's enumerated school criteria |
| Selective: admission test neither required nor recommended | 72,845 | 3.75% | School criteria enumerated separately; no common admission test |
| Open admission | 339,523 | 17.46% | No subjective selection cutoff; estimate the entrant distribution from origin populations |

Only 16.13% are in the three selective paths without a required common test. A 317-person (0.02%) difference between the admissions and fall-enrollment reporting frames is retained in the generated reconciliation table rather than assigned to a path.

SAT and ACT remain distinct, non-exclusive measurement routes. Among the complete entrant universe, 846,219 submitted SAT scores (43.52%) and 673,606 submitted ACT scores (34.64%). The same student can appear in both figures, so these two counts must not be added and there are no SAT-only, ACT-only, or test-subset rows. IPEDS 2019 publishes the 25th and 75th percentile of each SAT section and the ACT composite. [`derived/freshman_test_route_ability.tsv`](derived/freshman_test_route_ability.tsv) reconstructs each native-scale distribution without inventing an unpublished median or adding marginal SAT section quantiles as though they were total-score quantiles.

The policy paths above are additive, but the criteria used inside selective review are not. [`derived/freshman_admission_considerations.tsv`](derived/freshman_admission_considerations.tsv) separately records GPA, rank, school record, college-preparatory curriculum, recommendations, formal competencies/portfolios, English tests, and other tests as required, recommended, considered, or neither. That table exposes the remaining subjective mechanisms instead of compressing them into a “transcript/GPA and institution-specific review” bucket.

Transfer is not in this freshman table. It contributes an estimated 801,135 final graduates, or 18.39% of the age-18 population, and is modeled from origin institutions, transfer GPA/coursework, and destination-specific completion rather than from the final institution's freshman distribution.

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

1. **No-prior-college graduates.** `ability.py` retains SAT and ACT as separate native-scale routes, including each route's two published quartiles and submitter count. At least one complete fall-2019 test distribution is available at institutions producing 1,499,079 (79.00%) of current domestic bachelor's awards. The current reconstruction puts 25%, 50%, and 25% uniform mass in the three bounded intervals defined by the scale endpoints and the reported quartiles. A later common ability scale will cross-calibrate the two routes; it will not collapse the route labels or count dual submitters twice.
2. **Transfer graduates.** A final institution's freshman scores do not describe this group. Use a national longitudinal bachelor-recipient sample to estimate pre-college ability differences between direct and transfer graduates by destination type, then apply institution-specific transfer shares. Transfer-dominant institutions without a meaningful freshman intake will necessarily have wider uncertainty.
3. **Selective paths without a required test.** These are now isolated as 16.13% of first-time entrants, split by recommended, considered, and neither-required-nor-recommended policy. They require school-record calibration and explicit special-channel adjustments; they cannot simply receive a test-submitter distribution.
4. **Open admission.** This 17.46% path is not subjective admission. Its age-18 ability distribution must be estimated from the eligible origin population and actual enrollment selection, with wider uncertainty than a published score distribution.

The active pass will first produce one endpoint-year estimate from these national tables. Additional admissions vintages and a longitudinal transfer bridge are recorded as later upgrades rather than blocking this estimate.

## Reproduction

Downloaded inputs and generated tables stay local and are ignored by Git. [`sources/README.md`](sources/README.md) lists the complete Census/IPEDS files and their official URLs; `fetch_sources.py` pins every SHA-256 digest.

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
- `derived/freshman_admission_paths.tsv`
- `derived/freshman_test_routes.tsv`
- `derived/national_test_routes.tsv`
- `derived/freshman_test_route_ability.tsv`
- `derived/freshman_admission_considerations.tsv`
- `derived/graduate_pathways_by_level.tsv`
