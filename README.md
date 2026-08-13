# U.S. undergraduate ability distributions

The eventual goal is to estimate the distribution of pre-college ability conditional on the bachelor's degree a person obtained. The denominator is **every U.S. resident at age 18**, including people who never attend college. This first stage quantifies how students arrive at four-year institutions; it does not yet estimate ability.

## Pathway model

U.S. admission categories overlap, so one additive list of “admission types” would double-count people. We use three separate dimensions.

1. **Entry route**, a partition of new arrivals at a four-year institution:
   - first-time undergraduate;
   - transfer-in undergraduate.
2. **Application plan**, a partition within first-year admission when institutions disclose it:
   - binding early decision;
   - nonbinding early action or restrictive early action;
   - regular or rolling admission.
3. **Selection flags**, which overlap and therefore cannot be added:
   - ordinary holistic review;
   - recruited athlete;
   - legacy, development, or faculty-child preference;
   - statutory or guaranteed admission;
   - access programs such as QuestBridge;
   - audition, portfolio, or program-specific review.

IPEDS measures the first dimension comprehensively. Common Data Sets can measure binding early-decision admits at many schools, but not a clean EA/RD partition. Institutions almost never publish mutually exclusive counts for the third dimension: for example, a recruited athlete can also be a legacy and an early applicant.

## National calibration

The source period is fall 2023 through June 2024. “Domestic” means the IPEDS total less nonresident aliens; it does not mean U.S. citizen only.

| Quantity | Count/share |
|---|---:|
| U.S. resident population age 18, July 1, 2023 | 4,357,485 |
| First-time entrants at four-year degree-granting institutions | 2,353,982 |
| First-time entrants, less nonresident aliens | 2,262,366 |
| Preliminary first-time flow / age-18 population | 51.92% |
| **Preliminary bottom constant** | **48.08 percentile points** |
| Transfer entrants at four-year institutions | 1,615,553 |
| Transfer entrants, less nonresident aliens | 1,574,419 |
| Transfer share of domestic new arrivals | 41.03% |

The 48.08-point constant implements the proposed shortcut: first compute percentiles among domestic first-time four-year entrants, then place that distribution above residents who do not enter a four-year institution. It is only a **flow-to-cohort approximation**. The IPEDS numerator contains first-time students of every age, while the Census denominator is one exact age. Later work should estimate an age correction and separate delayed entry from permanent non-entry.

Transfers are not an adjustment at the margin. The annual flow into four-year institutions is 1.57 million domestic transfer students, compared with 2.26 million domestic first-time students. Because the target is the *final bachelor's institution*, the full model must retain both institutions:

`pre-college ability → initial institution → transfer selection → degree institution`

Continuing students are excluded from new-entry counts. Students who earned college credit while still in high school remain first-time students under the IPEDS definition.

## Entry route by freshman selectivity

The admission-rate bands use 2023 IPEDS first-year applications and admissions. They are descriptive, not an ability ordering: applicant self-selection, multiple applications, open admission, specialized schools, and test-optional policies all matter.

| First-year admit rate | Institutions | Domestic first-time | Share of age 18 | Domestic transfer | Transfer share of new arrivals |
|---|---:|---:|---:|---:|---:|
| 0–10% | 35 | 41,986 | 0.96% | 10,004 | 19.24% |
| 10–20% | 45 | 60,184 | 1.38% | 13,201 | 17.99% |
| 20–50% | 202 | 226,137 | 5.19% | 111,836 | 33.09% |
| Over 50% | 1,447 | 1,370,250 | 31.45% | 802,337 | 36.93% |
| Not reported or open | 703 | 563,809 | 12.94% | 637,041 | 53.05% |

The ≤10% aggregate hides two different systems. UCLA, Columbia, and Northeastern alone account for 6,092 of the band’s 10,004 domestic transfer entrants. Across the other ≤10% institutions reporting at least 500 first-year applications, transfers are 8.50% of new domestic arrivals. Thus freshman scores may be a tolerable first approximation at many elite private schools, but not at transfer-heavy public flagships or a few structurally unusual private universities.

The raw institution table is [`derived/institution_pathways.tsv`](derived/institution_pathways.tsv); [`derived/ultraselective_pathways.tsv`](derived/ultraselective_pathways.tsv) is the complete ≤10% subset. The cutoff is deliberately mechanical. It retains conservatories and anomalous tiny application counts rather than silently redefining “top.”

## Comparison with the other country projects

The Gaokao, Taiwan, Vietnam, and Thailand repositories mainly measure initial placement. University-to-university transfer exists in Taiwan and Vietnam but is peripheral to the national admission mechanism; changing universities after Gaokao placement is especially rare. Thailand's TCAS rounds also describe initial entry, although its larger measurement problem is that most seats use judgment-based criteria that are not comparable across programs.

The U.S. is different because community-college-to-university transfer is a mass route. An ability distribution attached to the degree institution therefore cannot simply reuse that institution's freshman SAT/ACT distribution.

## What can be measured next

- **First-time entry:** IPEDS supplies applications, admissions, enrolled counts, and SAT/ACT quartiles among score submitters. Test-optional selection means the score distributions need a missing-data model.
- **Binding early decision:** the Common Data Set reports ED applications and admits at participating schools. Since ED is binding, ED admits approximate ED entrants, subject to released commitments and nonmatriculation. EA entrant counts are not standardized.
- **Transfers:** IPEDS supplies transfer-in counts but not origin institutions. A transition model will need longitudinal student data or state/university transfer reports, plus transfer GPA and prior-test anchors where available.
- **Special preferences:** use them as overlapping likelihood shifts or school-specific mixtures only when a court record, statute, or institution publishes a real count. They cannot form national additive pathways.

## Reproduction

The checked-in source bundle contains only five complete official files: one Census population table, the IPEDS directory, admissions, 12-month enrollment, and its dictionary. URLs and coverage are in [`sources/README.md`](sources/README.md).

```sh
python3 fetch_sources.py
python3 pathways.py
python3 -m unittest -v
```

Generated tables:

- `derived/national_pathways.tsv`
- `derived/selectivity_pathways.tsv`
- `derived/institution_pathways.tsv`
- `derived/ultraselective_pathways.tsv`
