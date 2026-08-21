# TODO

The endpoint is the age-18 ability distribution of an institution's bachelor's graduates. Evidence is built separately per year and averaged at the end.

## Score what we already count

- [x] Medical and law schools
- [ ] Replace the law all-bachelor origin proxy with a recent law-applicant undergraduate feeder table
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

- [ ] Every transfer takes one pooled national score; find origin-by-destination counts
- [ ] Fit a broad-access model for community colleges and other test-sparse origins
- [ ] Update transfer ability with observed transfer GPA distributions, not minimum GPA

## Graduates, not entrants

- [ ] Relate entry ability to completion per route, calibrated to each school's eight-year rate
- [ ] Check schools with low completion, very high transfer shares, or small cohorts

## Deferred

- Associate's degree ranking, and the certificate and associate institutions behind it
- Major-specific admission thresholds at open universities
- Split Carnegie Mellon into its separately admitted colleges when college-level data exists
- Unique eventual bachelor recipients instead of the annual award/population bridge
