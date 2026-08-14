# TODO

The endpoint is the age-18 ability distribution conditional on the institution that ultimately awards the bachelor's degree. Work on one endpoint cross-section first: 2023 population, 2022–23 degrees, fall 2019 freshman-admission evidence, and the transfer information available in 2023. Fall 2019 is the final pre-COVID entering class and the conventional four-year predecessor of the 2022–23 graduating class.

Each item ends with a concrete intermediate output. Historical extensions remain deferred until the current cross-section works.

## 1. Separate and score freshman-admission routes

- [ ] Estimate the share of minor routes in the top 10+10 schools: Athletics, audition, Automatic class-rank

- [ ] GPA/rank (is this different from Automatic class-rank guarantee?) where SAT/ACT are not available. Defer this task if it requires individual school pdfs

- [ ] Get data on major-specific thresholds for open universities

- [ ] Link the separate SAT-taker and ACT-taker percentile scales to the age-18 ability population. Account for selection into each testing population and use dual-reporting institutions as a consistency check, not as license to merge route counts.

- [ ] Replace the unscored selective remainder with named mechanisms and ordinary academic review. Treat required/recommended/considered/neither as coverage metadata, not as the ability routes and not as a generic no-test bucket.

- [ ] Model the 17.46% open-admission entrant path from eligible origin populations and observed enrollment selection. For the first scored pass, leave its direct-graduate component explicitly unscored rather than equating entrants with the eligibility floor. This defers about 1.93% of current domestic bachelor's awards; most degrees awarded by open-admission institutions belong to the separately modeled transfer component.

- [ ] Expand the actual selection-channel benchmarks into national route weights. Replace portfolio exposure with actual program counts and obtain recruited-athlete and automatic class-rank counts outside the benchmark institutions. Estimate early-round or legacy adjustments only where academic distributions identify them; never turn either overlay into a route count. Keep an unknown residual where no national count exists.

- [ ] Weight institutions by current first-time domestic entrants to construct the national freshman pool, then validate by hiding score-reporting institutions. Report error separately for selective, broad-access, test-blind, and open-admission schools.

**Outputs:** `derived/freshman_admission_paths.tsv`, `derived/freshman_test_routes.tsv`, `derived/freshman_test_route_ability.tsv`, `derived/freshman_test_component_percentiles.tsv`, `derived/freshman_test_route_percentiles.tsv`, `derived/national_test_route_percentiles.tsv`, `derived/open_admission_endpoint.tsv`, `derived/admission_benchmarks.tsv`, and `derived/first_time_entrant_ability.tsv` (common-scale distributions with route-specific components).

## 2. Extend the origin-school model beyond bachelor's institutions

The existing final-institution table contains bachelor's-awarding institutions. Transfer origins instead include community colleges, other two-year institutions, four-year institutions, and schools whose students rarely receive a bachelor's there.

- [ ] Fit a separate broad-access model for community colleges and other test-sparse origins. Use only nationally comparable predictors and make its uncertainty wider than directly observed test distributions.

- [ ] Extend `schools.tsv` and `majors.tsv` to the certificate and associate institutions represented in the national pathway table, without treating a credential count as a unique age-18 person.

- [ ] Check state and system effects. A single national community-college value is unlikely to describe both universal-access systems and systems that divert different portions of high-school graduates into two-year colleges.

**Output:** `derived/origin_institution_ability.tsv`, covering every plausible starting institution and reporting the share of the origin pool directly measured, imputed, or still unknown.

## 3. Estimate transfer flows into each final institution

For final institution `y`, the first transfer approximation is

`F_transfer,y(a) = sum_x w(x -> y) F_origin,x(a)`.

The desired weights are transfers who eventually graduate from `y`, not merely transfer applications or one year's entrants.

- [ ] Locate systematic origin-by-destination transfer counts. Inventory national, state-system, institutional-research, articulation, and public records before collecting one-off university anecdotes.

- [ ] Record exactly what each count measures: applicants, admits, enrolled transfers, credits accepted, or eventual graduates.

- [ ] Distinguish community-college transfers, lateral four-year transfers, reverse transfers, international origins, and unknown origins.

- [ ] Handle multiple transfers. The immediately preceding institution is not necessarily where the student entered higher education or where age-18 ability was first observed.

- [ ] Convert transfer-entrant flows to transfer-graduate weights using destination- and route-specific completion rates. Keep an explicit unknown-origin residual rather than reallocating it invisibly.

- [ ] Compare the resulting destination totals with the IPEDS Outcome Measures transfer-graduate shares already in `derived/institution_graduates.tsv`.

**Output:** `derived/transfer_origin_destination.tsv`, with origin, final institution, count concept, graduation-adjusted weight, source coverage, and uncertainty.

## 4. Audit paths not represented by the simple direct/transfer split

- [ ] Reconcile IPEDS definitions. “First-time” can include dual-enrollment credit, while “non-first-time” means prior postsecondary attendance and does not necessarily mean accepted transfer credit.

- [ ] Quantify adult first-time students, returning students, part-time entrants, online institutions, military pathways, non-degree starters, and students entering through branch campuses.

- [ ] Check whether second bachelor's degrees and multiple awards materially inflate the annual bachelor flow relative to unique graduates.

- [ ] Measure institutions missing a usable Outcome Measures split and retain an unknown-route component where necessary.

- [ ] Keep nonresident aliens, migration, delayed completion, and the flow-to-cohort approximation visible. Do not silently treat annual awards as a literal cohort.

**Output:** a route-reconciliation table whose rows exhaust the bachelor flow and state which routes enter the ability model, are approximated, or remain unknown.

## 5. Update transfer ability using college performance

Origin-school ability is a prior. Transfer GPA and completed coursework provide additional evidence, but they occur after age 18 and raw GPAs are not comparable across institutions or majors.

- [ ] Collect transfer-admit or transfer-enrollee GPA distributions, not just minimum GPA requirements. Prefer system-wide standardized releases and Common Data Set fields before bespoke pages.

- [ ] Collect transferable credits, prerequisite completion, source institution, intended major, and associate-degree/articulation status where available.

- [ ] Normalize GPA for source institution, course level and field, credits attempted, and grading environment. Treat published minimum GPAs as eligibility gates rather than observed ability distributions.

- [ ] Estimate a GPA likelihood conditional on the origin-school ability prior. Where paired pre-college scores and college records are unavailable, show sensitivity rather than assigning a precise correction.

- [ ] Apply the GPA evidence as an update to each origin mixture. Do not replace age-18 ability with college GPA.

**Output:** `derived/transfer_ability.tsv`, giving each final institution's transfer distribution before and after the GPA update and showing how much of the update is data versus pooled assumption.

## 6. Select entrants into final graduates

Neither the freshman nor transfer entrant distribution is yet the distribution of eventual graduates. Completion is selective with respect to preparation.

- [ ] Estimate the relationship between entry ability and bachelor's completion separately for first-time and transfer routes.

- [ ] Calibrate that selection to each institution's route-specific eight-year completion rate rather than applying one national graduation bonus.

- [ ] Test sensitivity for institutions with low completion, very high transfer shares, or small Outcome Measures cohorts.

**Output:** route-specific ability distributions among graduates, with the entrant-to-graduate shift reported explicitly.

## 7. Produce the final institution distributions

- [ ] Mix direct and transfer graduate distributions using each final institution's graduate route share.

- [ ] Weight institutions by domestic bachelor's awards to construct the national bachelor-recipient distribution.

- [ ] Convert every institution distribution to percentiles among bachelor recipients, then prepend the no-bachelor mass from the pathway table to obtain the requested all-age-18 scale.

- [ ] Publish medians and intervals only at the precision supported by route coverage, test coverage, transfer origins, GPA evidence, and completion adjustment.

- [ ] Run leave-one-source-out and assumption sensitivity checks; identify institutions whose apparent rank is mostly imputation.

**Output:** `derived/institution_ability.tsv`, answering “given a bachelor's from institution `y`, what was this person's age-18 ability distribution?”

## Deferred

- [ ] Split Carnegie Mellon into its separately admitted undergraduate colleges when comparable college-level SAT/ACT/rank data are available; leave Harvey Mudd institution-wide because students enter before declaring a major.
- Align admissions evidence to historical entering cohorts and estimate multiple cohort-years separately before aggregation.
- Replace the annual award/population bridge with unique eventual bachelor recipients from a synthetic cohort, including late completion, repeat bachelor's degrees, migration, and residency differences.
- Calibrate transfer and completion adjustments with Baccalaureate and Beyond or Beginning Postsecondary Students microdata.
