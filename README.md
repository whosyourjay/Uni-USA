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

## Freshman admission paths

The 2023 admissions cross-section is unsuitable for the ability model: pandemic-era test-optional policies and permanent test-blind policies leave an enormous unscored remainder. Fall 2019 is the last pre-COVID entering class. Its routes currently look like this:

| Route | How it works | Fall 2019 people observed | Share of all first-time entrants | Institution-level score coverage |
|---|---|---:|---:|---|
| SAT | Applicant submits SAT; the institution reports enrolled-student reading/writing and math 25th–75th percentiles | 846,219 submitters | 43.52% | 1,167 institutions; 846,098 submitters with both section bars |
| ACT | Applicant submits ACT; the institution reports the enrolled-student composite 25th–75th percentiles | 673,606 submitters | 34.64% | 1,201 institutions; 673,599 submitters with a composite bar |
| Open admission | Institution accepts any applicant for all or most first-time undergraduate entry; credential checks and selective-program gates may remain | 339,523 entrants | 17.46% | No institution-level admission cutoff; GPA/tests may still inform placement |
| Guaranteed rank admission | Published class-rank eligibility | UT Austin benchmark: at least 75% of Texas-resident freshman spaces; top 6% rule | Not a national share | Rank threshold; major placement still reviewed |
| Recruited athletics | Coach-supported admission with academic eligibility or an institution-specific floor | Harvard benchmark: 9.5% of admits | Not a national share | Separate route adjustment; UCLA athlete GPA benchmark below |
| Audition or portfolio | Performance or work sample is a material admission gate | At most 88,931 entrants exposed to an institution reporting it required | At most 4.57% | Exposure ceiling, not a route count |
| Service-academy nomination | Nomination plus academic, physical, and medical selection | 3,696 domestic entrants at four academies | 0.19% | Academy SAT/ACT bars plus nonacademic screens |

SAT and ACT are deliberately separate rows and separate native-scale models. They are not additive: the same entrant can submit both, so their counts must not be summed and there will be no SAT-only, ACT-only, or every-test-subset rows. The SAT route has its two section bars as columns on one institution-route row. [`derived/freshman_test_routes.tsv`](derived/freshman_test_routes.tsv) is the canonical route table; one Harvard row is SAT and the next is ACT. [`derived/freshman_test_route_ability.tsv`](derived/freshman_test_route_ability.tsv) contains the component-level calibration machinery.

Early decision and early action are not separate routes. They are application rounds layered over SAT, ACT, guaranteed admission, recruited athletics, or another substantive path. The Harvard count establishes the scale of early timing—935 of 1,950 admits—but supplies neither an early-round cutoff nor a separate academic distribution. If round-specific academic distributions become available, they can adjust the underlying route; the observed early admit rate alone cannot identify such an adjustment because the applicant pools differ. Legacy status is likewise a preference overlay, not an ability-measurement route. Both are classified as overlays in [`derived/admission_benchmarks.tsv`](derived/admission_benchmarks.tsv).

The IPEDS values are enrolled-student quartiles, not binding admission cutoffs. For this project's endpoint that is useful: they describe the people whose ability distribution must ultimately be propagated into graduates. The reconstruction places 25%, 50%, and 25% of each institution-route's mass in the three bounded intervals defined by the native scale and its two reported quartiles. It does not invent an unpublished median or add marginal SAT section quantiles as though they were a total-score cutoff.

Test policy is a coverage audit, not the admission-route table. Of 1,944,624 first-time entrants, 1,291,303 (66.40%) attended institutions requiring a test, 100,883 (5.19%) institutions recommending it, 139,753 (7.19%) institutions considering but not requiring it, and 72,845 (3.75%) selective institutions neither requiring nor recommending it. Open admission accounts for 339,523 (17.46%); the remaining 317 people are a difference between IPEDS reporting frames. These categories partition entrants but do not measure ability.

The criteria used inside applications also overlap and are therefore kept out of the route counts. [`derived/freshman_admission_considerations.tsv`](derived/freshman_admission_considerations.tsv) records GPA, rank, school record, college-preparatory curriculum, recommendations, formal competencies/portfolios, English tests, and other tests as required, recommended, considered, or neither. We will use those fields to identify and adjust particular routes, not collapse everyone into a “transcript/GPA and institution-specific review” residual.

The special-channel figures are scale checks with deliberately different denominators, not numbers to add. Harvard's early program was nonbinding, so 935 / 1,950 measures timing, not the causal size of an early preference. The Harvard applicant study reports recruited athletes as 9.5% and legacies as 14% of admitted students across six cycles. At UCLA, the athlete committee admitted about 98% of reviewed cases in 2017–18 through 2019–20; in 2019–20 admitted athletes averaged 3.74 GPA versus 4.15 for the bottom quartile of all admits. That is direct evidence that the institution-wide SAT/ACT distribution cannot simply be assigned to recruited athletes. [`derived/admission_benchmarks.tsv`](derived/admission_benchmarks.tsv) retains each item's classification, numerator, denominator, count concept, overlap warning, and source.

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
3. **Applicants without usable SAT or ACT evidence.** Test-policy categories are only a coverage audit. This group must be separated into actual mechanisms—guaranteed rank/GPA admission, ordinary academic review, recruited athletics, auditions/portfolios, service-academy nominations, and other named channels—before route-specific calibration.
4. **Open admission.** This 17.46% path is not essay-only or GPA-based selection. IPEDS defines it as accepting any applicant for all or most entering first-time undergraduates. A school may still verify a diploma or equivalent and use transcripts or tests for placement; particular programs may have separate gates. The acceptance threshold can therefore be treated as the eligibility floor, but the entrant distribution cannot be placed at that floor. For the first scored pass, leave it unscored. Open-admission institutions award 170,220 (8.97%) of current domestic bachelor's degrees, but only an estimated 36,611 (1.93% of all domestic bachelor's awards) belong to their no-prior-college component; an estimated 131,026 belong to the transfer component and will be modeled from transfer origins. [`derived/open_admission_endpoint.tsv`](derived/open_admission_endpoint.tsv) makes this deferral explicit.

The active pass will first produce one endpoint-year estimate from these national tables. Additional admissions vintages and a longitudinal transfer bridge are recorded as later upgrades rather than blocking this estimate.

## Reproduction

Downloaded inputs and generated tables stay local and are ignored by Git. [`sources/README.md`](sources/README.md) lists the complete Census/IPEDS files and their official URLs; `fetch_sources.py` pins every SHA-256 digest.

```sh
python3 fetch_sources.py
python3 pathways.py
python3 ability.py
python3 special_routes.py
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
- `derived/open_admission_endpoint.tsv`
- `derived/admission_benchmarks.tsv`
- `derived/graduate_pathways_by_level.tsv`
