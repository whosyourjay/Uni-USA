# TODO

The endpoint is the age-18 ability distribution of an institution's bachelor's graduates. Evidence is built separately per year and averaged at the end.

## Score what we already count

- [x] Medical and law schools, ranked in `schools.tsv` beside the undergraduate rows
- [x] Weight law's origin pool by an application rate that climbs with school ability
- [ ] Replace the borrowed medical slope with a real law-applicant undergraduate feeder table
- [ ] Refit the application slope without AAMC's 50-applicant truncation, which flattens it and makes law conservative
- [ ] Match the remaining 5.4% of applicants in AAMC's published feeder table; origins below its 50-applicant threshold are also absent
- [ ] Estimate within-school selection into medical applications; school CDFs currently treat applicants like the full bachelor class
- [ ] Score GRE and JD-Next law entrants and add osteopathic medical schools
- [ ] The 324 schools whose median graduate transferred in or sent no score
- [ ] Recruited-athlete and audition entrants, counted today but carrying no ability
- [ ] Open-admission entrants, from origin populations rather than the eligibility floor; their direct graduates are ~1.9% of awards
- [ ] Replace the SAT/ACT exchangeability assumption using dual-reporting institutions
- [ ] Measure dual takers per year instead of scaling the 2017 concordance sample
- [ ] `ability_pool_ratio` counts seats only at the 1,280 schools reporting a bar, so its denominator runs low; test-optional years shrink it further

## Class rank

- [ ] The source gives no rank-reporting share, so a school that ranks few students looks weak
- [ ] 49 source names miss the IPEDS directory (Saint John's MN vs NY, SUNY campuses)
- [ ] Some published years are typos: Harvey Mudd fall 2023 reads 2/15/83

## Transfers

- [x] Deal the stack-ranked origin-median pool to destinations by selectivity
- [ ] Replace the deal with real origin-by-destination counts, starting with state systems
- [x] Predict test-sparse origins from enrollment, completion, and admission policy
- [ ] Rank the 1,133 destinations whose freshmen send no scores with the same features; they sit below every scored school today, which sets the slice for 30% of transfer graduates
- [ ] Only 17 two-year origins send scores, so the whole level's 3.2-point lift rests on them
- [ ] Separate the two-year level gap into its clock and its transfer-before-completion half; the eight-year outcome window widens the gap instead of closing it
- [ ] Completion at a small private two-year measures program length, not ability; those origins now predict high
- [ ] Update transfer ability with observed transfer GPA distributions, not minimum GPA
- [ ] Rank California community colleges against UC's published transfer GPA, the one external check available

## Graduates, not entrants

- [ ] Relate entry ability to completion per route, calibrated to each school's eight-year rate
- [ ] Check schools with low completion, very high transfer shares, or small cohorts

## Deferred

- Associate's degree ranking, and the certificate and associate institutions behind it
- Major-specific admission thresholds at open universities
- Split Carnegie Mellon into its separately admitted colleges when college-level data exists
- Unique eventual bachelor recipients instead of the annual award/population bridge
