#!/usr/bin/env python3
"""Quantify selection routes and overlays that IPEDS test fields do not identify.

The rows deliberately retain unlike denominators.  A national entrant count, a
single-school share of admits, and a route admit rate are useful scale checks,
but they are not additive estimates of the national freshman population.
"""

from uniusa import ability, pathways

SERVICE_ACADEMY_UNITIDS = {
    128328: "United States Air Force Academy",
    164155: "United States Naval Academy",
    197027: "United States Merchant Marine Academy",
    197036: "United States Military Academy",
}

HARVARD_EARLY_SOURCE = (
    "https://news.harvard.edu/gazette/story/2018/12/"
    "935-admitted-early-to-harvard-college-class-of-23/"
)
HARVARD_TOTAL_SOURCE = (
    "https://news.harvard.edu/gazette/story/2019/03/"
    "harvard-college-admits-1950-to-class-of-23/"
)
HARVARD_PREFERENCE_SOURCE = (
    "https://projects.iq.harvard.edu/files/pegroup/files/"
    "arcidiacono_et_al_legacy.pdf"
)
UT_AUTOMATIC_SOURCE = (
    "https://catalog.utexas.edu/archive/2018-19/general-information/"
    "admission/undergraduate-admission/"
)
UC_AUDIT_SOURCE = (
    "https://information.auditor.ca.gov/reports/2019-113/sections.html"
)
ACADEMY_SOURCE = "https://www.congress.gov/crs-product/IF11788"


BENCHMARKS = (
    {
            "item": "Service-academy nomination",
            "classification": "selection route",
            "benchmark": "Four nomination-based federal service academies",
            "cohort": "fall 2019",
            "numerator": "",
            "denominator": "",
            "rate": "",
            "measure": "domestic first-time entrants / all first-time entrants",
            "ability_evidence": (
                "Academy SAT/ACT bars plus nomination, academic, physical, and "
                "medical screens"
            ),
            "national_route_count": "yes",
            "additive": "yes within freshman paths",
            "source": f"IPEDS EF2019A; {ACADEMY_SOURCE}",
            "measured": "service academies",
        },
        {
            "item": "Audition or portfolio",
            "classification": "selection route",
            "benchmark": "Institutions reporting formal competency/portfolio required",
            "cohort": "fall 2019",
            "numerator": "",
            "denominator": "",
            "rate": "",
            "measure": "entrants exposed to an institution-level requirement",
            "ability_evidence": (
                "Upper exposure bound, not the number admitted through an audition "
                "or portfolio"
            ),
            "national_route_count": "no",
            "additive": "no: requirement may apply only to particular programs",
            "source": "IPEDS ADM2019 formal competencies/portfolio consideration",
            "measured": "formal competencies or portfolio",
        },
        {
            "item": "Early action",
            "classification": "application-round overlay",
            "benchmark": "Harvard Class of 2023",
            "cohort": "2018-19 admissions",
            "numerator": 935,
            "denominator": 1950,
            "rate": 935 / 1950,
            "measure": "early-action admits / all admits",
            "ability_evidence": (
                "Timing overlay; Harvard's program was nonbinding and the count does "
                "not identify a causal preference"
            ),
            "national_route_count": "no",
            "additive": "no: overlaps SAT, ACT, athletics, and other routes",
            "source": f"{HARVARD_EARLY_SOURCE}; {HARVARD_TOTAL_SOURCE}",
        },
        {
            "item": "Recruited athletics",
            "classification": "selection route",
            "benchmark": "Harvard domestic applicants, six cycles",
            "cohort": "classes entering 2014-19",
            "numerator": "",
            "denominator": "",
            "rate": 0.095,
            "measure": "share of admitted students",
            "ability_evidence": (
                "86% route admit rate; estimate route-specific score distribution "
                "rather than inheriting the institution-wide bar"
            ),
            "national_route_count": "no",
            "additive": "no: overlaps test-evidence routes and application rounds",
            "source": HARVARD_PREFERENCE_SOURCE,
        },
        {
            "item": "Recruited athletics",
            "classification": "selection route",
            "benchmark": "UCLA athlete committee",
            "cohort": "2017-18 through 2019-20",
            "numerator": "",
            "denominator": "",
            "rate": 0.98,
            "measure": "admit rate among committee-reviewed athlete cases",
            "ability_evidence": (
                "2019-20 admitted-athlete mean GPA 3.74 versus 4.15 for the "
                "bottom quartile of all admits"
            ),
            "national_route_count": "no",
            "additive": "no: this is an admit rate, not a population share",
            "source": UC_AUDIT_SOURCE,
        },
        {
            "item": "Legacy preference",
            "classification": "preference overlay",
            "benchmark": "Harvard domestic applicants, six cycles",
            "cohort": "classes entering 2014-19",
            "numerator": "",
            "denominator": "",
            "rate": 0.14,
            "measure": "share of admitted students",
            "ability_evidence": "33.6% legacy-applicant admit rate",
            "national_route_count": "no",
            "additive": "no: overlaps test, early, and other routes",
            "source": HARVARD_PREFERENCE_SOURCE,
        },
        {
            "item": "Automatic admission by high-school class rank",
            "classification": "selection route",
            "benchmark": "University of Texas at Austin",
            "cohort": "summer/fall 2019",
            "numerator": "",
            "denominator": "",
            "rate": 0.75,
            "measure": "minimum share of Texas-resident freshman spaces",
            "ability_evidence": (
                "Top 6% of high-school class determines university admission; major "
                "placement remains reviewed"
            ),
            "national_route_count": "no",
            "additive": "yes within UT's Texas-resident freshman spaces",
            "source": UT_AUTOMATIC_SOURCE,
        },
)


def measured_numerators(graduates, admissions, enrollment):
    """Entrant counts for the two benchmarks IPEDS can size directly."""
    considerations = {
        row["basis"]: row
        for row in ability.consideration_rows(graduates, admissions)
    }
    return {
        "service academies": sum(
            enrollment.get(unitid, {}).get("domestic", 0)
            for unitid in SERVICE_ACADEMY_UNITIDS
        ),
        "formal competencies or portfolio": considerations[
            "Formal competencies or portfolio"
        ]["required_enrolled"],
    }


def benchmark_rows(graduates, admissions, enrollment):
    """Fill the measured benchmarks against the national first-time entrants."""
    numerators = measured_numerators(graduates, admissions, enrollment)
    entrants = sum(
        row["fall_first_time_entrants_2019"]
        for row in ability.admission_path_rows(
            graduates, admissions, ability.load_characteristics(), enrollment
        )
    )
    rows = []
    for benchmark in BENCHMARKS:
        row = dict(benchmark)
        measured = row.pop("measured", None)
        if measured is not None:
            numerator = numerators[measured]
            row.update(
                numerator=numerator,
                denominator=entrants,
                rate=numerator / entrants,
            )
        rows.append(row)
    return rows


def main():
    graduates = pathways.graduate_rows(
        pathways.load_directory(),
        pathways.load_completions(),
        pathways.load_outcomes(),
        pathways.load_enrollment(),
    )
    rows = benchmark_rows(
        graduates, ability.load_admissions(), ability.load_fall_enrollment()
    )
    pathways.write_tsv(pathways.DERIVED / "admission_benchmarks.tsv", rows)
    print(f"wrote {len(rows)} admission-route and overlay benchmarks")


if __name__ == "__main__":
    main()
