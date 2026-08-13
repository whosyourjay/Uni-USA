# U.S. bachelor-graduate ability

The goal is to estimate the distribution of academic ability at age 18 conditional on the bachelor's degree a person eventually receives:

`ability | final bachelor's institution`

The denominator is every U.S. resident at age 18, including people who never attend college. The unit being ranked is the **final degree institution**, not the institution of first admission.

## Population and weights

The institution universe comes from actual 2022–23 IPEDS bachelor's completions. It does not start with a sector, ranking, or “four-year college” filter.

| Quantity | Count/share |
|---|---:|
| U.S. resident population age 18, July 1, 2023 | 4,357,485 |
| Bachelor's degrees, all citizenships | 1,985,289 |
| Bachelor's degrees, less nonresident aliens | 1,897,543 |
| Domestic bachelor flow / age-18 population | 43.55% |
| **Preliminary no-bachelor constant** | **56.45 percentile points** |
| Institutions awarding at least one bachelor's | 2,445 |
| Institutions awarding at least one domestic bachelor's | 2,356 |

The 56.45-point constant is the final-degree analogue of the cohort rescaling in the Taiwan, Vietnam, and Thailand projects. If a within-graduate ability percentile is `p`, its first cohort-scale approximation is

`56.45 + 0.4355 p`.

This is a flow-to-cohort approximation. The numerator is degrees awarded during one year, not unique members of the current age-18 cohort: graduates are older, a person can receive more than one bachelor's, and some people complete much later. “Domestic” means the IPEDS total less nonresident aliens. These are the next corrections to estimate; they are explicit rather than hidden in the ranking.

Almost every actual bachelor's award comes from an institution IPEDS classifies as four-or-more-year: only one domestic award in this file falls outside that classification. That is an empirical result of using final degrees, not a filter. Low-prestige, open-admission, online, specialized, and transfer-serving universities remain in the 2,356-institution table.

## Pathways to the final institution

A transfer is an event, so annual first-time and transfer-in counts cannot be added nationally: the same person may first enter one institution and later enter another. IPEDS Outcome Measures provides the useful partition. It follows all degree-seeking students who entered an institution in 2015–16 and records the highest degree they earned **at that institution** by 2023.

| Route into final institution | Bachelor's graduates in the cohort | Share |
|---|---:|---:|
| First-time at that institution | 1,065,088 | 57.78% |
| Prior postsecondary experience before entering it | 778,249 | 42.22% |

The second row is the transfer component in the model. IPEDS calls it “non-first-time entering”; transfer credit is not required. Institutions with a usable route estimate account for 99.79% of current domestic bachelor's awards.

The route mixture varies too much to substitute a national constant. Among the 2015–16 entering cohorts who earned a bachelor's there within eight years, the transfer share is 0.24% at Harvard, 0.83% at Stanford, 29.85% at Berkeley, 35.63% at UCLA, 35.04% at Columbia, and 91.11% at the University of Phoenix-Arizona. These are pathway shares, not ability estimates.

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

1. **Direct graduates.** Use the institution's SAT/ACT distribution for the entry cohorts that produced the graduates, not 2023 test-optional admissions. Convert test scores onto an all-age-18 scale, then correct entrants to graduates using first-time completion selection.
2. **Transfer graduates.** A final institution's freshman scores do not describe this group. Use a national longitudinal bachelor-recipient sample to estimate pre-college ability differences between direct and transfer graduates by destination type, then apply institution-specific transfer shares. Transfer-dominant institutions without a meaningful freshman intake will necessarily have wider uncertainty.
3. **Missing tests.** SAT/ACT submitters are selected even before test-optional admission. Submission rates and the joint SAT/ACT national distributions must enter the model; unreported students cannot simply receive the reported median.

The next source should therefore be one longitudinal source chosen for this exact bridge—Baccalaureate and Beyond or Beginning Postsecondary Students—not a collection of school anecdotes. Institution admissions data then locate named universities within the resulting route-specific scale.

## Reproduction

Downloaded inputs and generated tables stay local and are ignored by Git. [`sources/README.md`](sources/README.md) lists the nine complete Census/IPEDS files and their official URLs; `fetch_sources.py` pins every SHA-256 digest.

```sh
python3 fetch_sources.py
python3 pathways.py
python3 -m unittest -v
```

Primary generated tables:

- `derived/national_graduates.tsv`
- `derived/institution_graduates.tsv`
- `derived/graduate_pathways_by_level.tsv`
