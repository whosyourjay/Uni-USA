#!/usr/bin/env python3
"""Build pre-COVID freshman-admission paths and test evidence.

The final-institution weights remain the 2022-23 domestic bachelor's awards.
Fall 2019 is the admissions baseline: it is the last entering class unaffected
by pandemic-era test-optional and test-blind changes, and it overlaps naturally
with the students completing bachelor's degrees four years later.
"""

from functools import lru_cache

from uniusa import pathways

ROOT = pathways.ROOT
DERIVED = pathways.DERIVED
ADMISSION_YEAR = 2019
SAT_FIELDS = ("SATVR25", "SATVR75", "SATMT25", "SATMT75")
ACT_FIELDS = ("ACTCM25", "ACTCM75")
CONSIDERATIONS = {
    "ADMCON1": "Secondary-school GPA",
    "ADMCON2": "Secondary-school rank",
    "ADMCON3": "Secondary-school record",
    "ADMCON4": "College-preparatory program",
    "ADMCON5": "Recommendations",
    "ADMCON6": "Formal competencies or portfolio",
    "ADMCON7": "Admission tests",
    "ADMCON8": "English-proficiency test",
    "ADMCON9": "Other test",
}
CONSIDERATION_STATUS = {
    1: "required",
    2: "recommended",
    5: "considered but not required",
    3: "neither required nor recommended",
}
ADMISSION_PATHS = {
    1: (
        "Selective: admission test required",
        "SAT or ACT distribution where published; other required tests remain explicit",
    ),
    2: (
        "Selective: admission test recommended",
        "Test evidence when submitted plus separately reported school criteria",
    ),
    5: (
        "Selective: admission test considered but not required",
        "Test evidence when submitted plus separately reported school criteria",
    ),
    3: (
        "Selective: admission test neither required nor recommended",
        "Separately reported school-record and other criteria; no common admission test",
    ),
}
TEST_COMPONENTS = (
    ("SAT", "reading and writing", "satvr", 200, 800, "SAT section 200-800"),
    ("SAT", "math", "satmt", 200, 800, "SAT section 200-800"),
    ("ACT", "composite", "actcm", 1, 36, "ACT composite 1-36"),
)


def present(row, fields):
    return all(pathways.number(row.get(field)) > 0 for field in fields)


@lru_cache(maxsize=None)
def load_admissions(year=ADMISSION_YEAR):
    return {
        pathways.number(row["UNITID"]): row
        for row in pathways.zip_rows(f"ADM{year}.zip")
    }


def load_characteristics():
    return {
        pathways.number(row["UNITID"]): row
        for row in pathways.zip_rows("IC2019.zip")
    }


def load_fall_enrollment():
    """Fall first-time degree/certificate-seeking undergraduates."""
    return {
        pathways.number(row["UNITID"]): {
            "all": pathways.number(row["EFTOTLT"]),
            "domestic": (
                pathways.number(row["EFTOTLT"])
                - pathways.number(row["EFNRALT"])
            ),
        }
        for row in pathways.zip_rows("EF2019A.zip")
        if pathways.number(row["EFALEVEL"]) == 4
    }


def evidence_label(has_sat, has_act):
    if has_sat and has_act:
        return "SAT and ACT"
    if has_sat:
        return "SAT only"
    if has_act:
        return "ACT only"
    return "none"


def policy_label(admission):
    return CONSIDERATION_STATUS.get(
        pathways.number(admission.get("ADMCON7")), "not reported"
    )


def ability_evidence_rows(graduates, admissions):
    output = []
    for graduate in graduates:
        admission = admissions.get(graduate["unitid"], {})
        has_sat = present(admission, SAT_FIELDS)
        has_act = present(admission, ACT_FIELDS)
        sat_share = pathways.number(admission.get("SATPCT")) / 100
        act_share = pathways.number(admission.get("ACTPCT")) / 100

        # SAT and ACT reporters can overlap. These are sharp bounds using only
        # IPEDS submitter counts; they are diagnostics, not a third route.
        coverage_min = max(sat_share, act_share)
        coverage_max = min(1, sat_share + act_share)
        enrolled = pathways.number(admission.get("ENRLT"))
        sat_submitters = pathways.number(admission.get("SATNUM"))
        act_submitters = pathways.number(admission.get("ACTNUM"))
        neither_lower = max(0, enrolled - sat_submitters - act_submitters)
        neither_upper = max(0, enrolled - max(sat_submitters, act_submitters))
        row = {
            "unitid": graduate["unitid"],
            "institution": graduate["institution"],
            "state": graduate["state"],
            "bachelors_domestic_2023": graduate["bachelors_domestic"],
            "direct_bachelors_8yr": graduate["direct_bachelors_8yr"],
            "transfer_bachelors_8yr": graduate["transfer_bachelors_8yr"],
            "transfer_share_bachelors_8yr": graduate["transfer_share_bachelors_8yr"],
            "direct_bachelor_rate_8yr": graduate["direct_bachelor_rate_8yr"],
            "test_evidence_2019": evidence_label(has_sat, has_act),
            "test_policy_2019": policy_label(admission) if admission else "not reported",
            "first_time_enrolled_2019": enrolled,
            "sat_submitters_2019": sat_submitters,
            "sat_share_2019": sat_share if admission else "",
            "act_submitters_2019": act_submitters,
            "act_share_2019": act_share if admission else "",
            "test_coverage_lower_2019": coverage_min if admission else "",
            "test_coverage_upper_2019": coverage_max if admission else "",
            "neither_sat_nor_act_lower_2019": neither_lower if admission else "",
            "neither_sat_nor_act_upper_2019": neither_upper if admission else "",
        }
        for field in SAT_FIELDS + ACT_FIELDS:
            row[field.lower() + "_2019"] = pathways.number(admission.get(field)) or ""
        output.append(row)
    return output


def freshman_test_route_rows(evidence):
    """One institution-route row for SAT and one for ACT.

    SAT section bars are columns on the SAT row, not separate routes.  The
    component-level reconstruction below is only calibration machinery.
    """
    output = []
    for row in evidence:
        if row["first_time_enrolled_2019"] == 0:
            continue
        common = {
            "unitid": row["unitid"],
            "institution": row["institution"],
            "state": row["state"],
            "first_time_enrolled_2019": row["first_time_enrolled_2019"],
            "test_policy_2019": row["test_policy_2019"],
            "sat_reading_writing_q25_2019": "",
            "sat_reading_writing_q75_2019": "",
            "sat_math_q25_2019": "",
            "sat_math_q75_2019": "",
            "act_composite_q25_2019": "",
            "act_composite_q75_2019": "",
        }
        for route, count_field, share_field, fields, thresholds in (
            (
                "SAT", "sat_submitters_2019", "sat_share_2019", SAT_FIELDS,
                {
                    "sat_reading_writing_q25_2019": row["satvr25_2019"],
                    "sat_reading_writing_q75_2019": row["satvr75_2019"],
                    "sat_math_q25_2019": row["satmt25_2019"],
                    "sat_math_q75_2019": row["satmt75_2019"],
                },
            ),
            (
                "ACT", "act_submitters_2019", "act_share_2019", ACT_FIELDS,
                {
                    "act_composite_q25_2019": row["actcm25_2019"],
                    "act_composite_q75_2019": row["actcm75_2019"],
                },
            ),
        ):
            if not all(row[field.lower() + "_2019"] != "" for field in fields):
                continue
            output.append({
                **common,
                "route": route,
                "submitters_2019": row[count_field],
                "share_of_institution_entrants_2019": row[share_field],
                "score_scale": (
                    "SAT sections 200-800" if route == "SAT" else "ACT composite 1-36"
                ),
                **thresholds,
            })
    return output


def national_test_route_rows(evidence, all_first_time):
    """National SAT and ACT evidence counts; the two rows may overlap."""
    rows = [row for row in evidence if row["first_time_enrolled_2019"] > 0]
    selective = sum(row["first_time_enrolled_2019"] for row in rows)
    values = (
        ("SAT", sum(row["sat_submitters_2019"] for row in rows)),
        ("ACT", sum(row["act_submitters_2019"] for row in rows)),
    )
    return [{
        "route": route,
        "submitters_2019": count,
        "share_selective_reporting_pool": count / selective,
        "share_all_first_time_entrants": count / all_first_time,
        "additive": "no: the same entrant may submit SAT and ACT",
    } for route, count in values]


def admission_path_rows(graduates, admissions, characteristics, enrollment):
    """Construct additive fall-2019 entry paths, including open admission."""
    unitids = {row["unitid"] for row in graduates}
    all_first_time = sum(
        enrollment.get(unitid, {}).get("all", 0) for unitid in unitids
    )
    output = []
    accounted = 0
    for code, (path, measure) in ADMISSION_PATHS.items():
        matching = [
            admissions[unitid] for unitid in unitids
            if unitid in admissions
            and pathways.number(admissions[unitid].get("ADMCON7")) == code
        ]
        people = sum(pathways.number(row.get("ENRLT")) for row in matching)
        accounted += people
        output.append({
            "path": path,
            "institutions": len(matching),
            "fall_first_time_entrants_2019": people,
            "share_all_first_time_entrants": people / all_first_time,
            "ability_evidence": measure,
            "source": "IPEDS ADM2019 admission-test consideration",
        })

    open_unitids = [
        unitid for unitid in unitids
        if pathways.number(characteristics.get(unitid, {}).get("OPENADMP")) == 1
    ]
    open_people = sum(
        enrollment.get(unitid, {}).get("all", 0) for unitid in open_unitids
    )
    accounted += open_people
    output.append({
        "path": "Open admission",
        "institutions": len(open_unitids),
        "fall_first_time_entrants_2019": open_people,
        "share_all_first_time_entrants": open_people / all_first_time,
        "ability_evidence": (
            "No institution-level selection cutoff; transcripts or tests may be "
            "used for placement or selective-program entry"
        ),
        "source": (
            "IPEDS IC2019 open-admission definition/status and EF2019A enrollment"
        ),
    })

    difference = all_first_time - accounted
    if difference < 0:
        raise ValueError("Admission paths exceed fall first-time enrollment")
    output.append({
        "path": "IPEDS reporting reconciliation",
        "institutions": "",
        "fall_first_time_entrants_2019": difference,
        "share_all_first_time_entrants": difference / all_first_time,
        "ability_evidence": "None; difference between ADM and EF reporting frames",
        "source": "Calculated residual",
    })
    return output


def consideration_rows(graduates, admissions):
    """Entrant-weight the non-exclusive bases used by selective institutions."""
    graduate_ids = {row["unitid"] for row in graduates}
    rows = [row for unitid, row in admissions.items() if unitid in graduate_ids]
    enrolled = sum(pathways.number(row.get("ENRLT")) for row in rows)
    output = []
    for field, basis in CONSIDERATIONS.items():
        result = {
            "basis": basis,
            "reporting_institutions": len(rows),
            "first_time_enrolled_reporting_universe_2019": enrolled,
        }
        for code, status in CONSIDERATION_STATUS.items():
            matching = [row for row in rows if pathways.number(row.get(field)) == code]
            slug = status.replace(" ", "_")
            result[slug + "_institutions"] = len(matching)
            result[slug + "_enrolled"] = sum(
                pathways.number(row.get("ENRLT")) for row in matching
            )
        output.append(result)
    return output


def open_admission_endpoint_rows(graduates, characteristics, enrollment):
    """Measure how much of the final endpoint depends on open-admission entry.

    The graduate split is the institution's Outcome Measures route share applied
    to current domestic bachelor's awards, as in pathways.py.  It prevents the
    much larger open-admission entrant count from being mistaken for unresolved
    mass in the final bachelor distribution.
    """
    open_rows = [
        row for row in graduates
        if pathways.number(
            characteristics.get(row["unitid"], {}).get("OPENADMP")
        ) == 1
    ]
    split_rows = [
        row for row in open_rows
        if row["transfer_share_bachelors_8yr"] != ""
    ]
    national_bachelors = sum(row["bachelors_domestic"] for row in graduates)
    open_bachelors = sum(row["bachelors_domestic"] for row in open_rows)
    direct = sum(
        row["bachelors_domestic"] * (1 - row["transfer_share_bachelors_8yr"])
        for row in split_rows
    )
    transfer = sum(
        row["bachelors_domestic"] * row["transfer_share_bachelors_8yr"]
        for row in split_rows
    )
    return [{
        "path": "Open admission",
        "institutions": len(open_rows),
        "fall_first_time_entrants_2019": sum(
            enrollment.get(row["unitid"], {}).get("all", 0)
            for row in open_rows
        ),
        "domestic_bachelors_2023": open_bachelors,
        "share_domestic_bachelors_2023": open_bachelors / national_bachelors,
        "estimated_direct_bachelors_2023": direct,
        "share_national_bachelors_direct_open": direct / national_bachelors,
        "estimated_transfer_bachelors_2023": transfer,
        "share_national_bachelors_transfer_open": transfer / national_bachelors,
        "bachelors_without_route_split_2023": open_bachelors - direct - transfer,
        "temporary_model_treatment": (
            "leave direct component unscored; model transfer component from its "
            "origin mixture"
        ),
    }]


def interval_cdf(value, lower, upper):
    """CDF of a uniform interval, including a possible point mass."""
    if upper == lower:
        return float(value >= upper)
    if value <= lower:
        return 0.0
    if value >= upper:
        return 1.0
    return (value - lower) / (upper - lower)


def interquartile_cdf(value, scale_min, q25, q75, scale_max):
    """A bounded distribution matching the two 2019 IPEDS quartiles.

    The lower tail, middle half, and upper tail are uniform within their
    intervals. This avoids inventing a normal tail or an unpublished median.
    """
    anchors = (scale_min, q25, q75, scale_max)
    if any(left > right for left, right in zip(anchors, anchors[1:])):
        raise ValueError(f"Non-monotone score anchors: {anchors}")
    masses = (0.25, 0.50, 0.25)
    return sum(
        mass * interval_cdf(value, left, right)
        for mass, (left, right) in zip(masses, zip(anchors, anchors[1:]))
    )


def test_component_rows(evidence):
    """Build route-specific distributions without merging SAT and ACT."""
    output = []
    for row in evidence:
        for route, component, prefix, scale_min, scale_max, scale in TEST_COMPONENTS:
            values = tuple(row[f"{prefix}{q}_2019"] for q in (25, 75))
            if any(value == "" for value in values):
                continue
            if not scale_min <= values[0] <= values[1] <= scale_max:
                continue
            submitters = row[f"{route.lower()}_submitters_2019"]
            if submitters <= 0:
                continue
            output.append({
                "unitid": row["unitid"],
                "institution": row["institution"],
                "state": row["state"],
                "route": route,
                "component": component,
                "submitters_2019": submitters,
                "score_scale": scale,
                "score_scale_min": scale_min,
                "score_q25_2019": values[0],
                "score_q75_2019": values[1],
                "score_scale_max": scale_max,
            })

    for row in output:
        row["distribution"] = "25%, 50%, 25% uniform mass across quartile intervals"
    return output


def test_route_coverage(rows):
    output = {}
    for route in ("SAT", "ACT"):
        route_rows = [row for row in rows if row["route"] == route]
        # SAT has two component rows per institution; count it once.
        by_unitid = {row["unitid"]: row for row in route_rows}
        output[route] = {
            "institutions": len(by_unitid),
            "submitters": sum(row["submitters_2019"] for row in by_unitid.values()),
        }
    return output


def evidence_coverage(rows):
    covered = [row for row in rows if row["test_evidence_2019"] != "none"]
    return {
        "institutions": len(covered),
        "bachelors_domestic": sum(row["bachelors_domestic_2023"] for row in covered),
        "direct_bachelors_8yr": sum(row["direct_bachelors_8yr"] for row in covered),
    }


def main():
    graduates = pathways.graduate_rows(
        pathways.load_directory(),
        pathways.load_completions(),
        pathways.load_outcomes(),
        pathways.load_enrollment(),
    )
    admissions = load_admissions()
    enrollment = load_fall_enrollment()
    rows = ability_evidence_rows(graduates, admissions)
    characteristics = load_characteristics()
    paths = admission_path_rows(graduates, admissions, characteristics, enrollment)
    all_first_time = sum(row["fall_first_time_entrants_2019"] for row in paths)
    pathways.write_tsv(DERIVED / "institution_ability_evidence.tsv", rows)
    pathways.write_tsv(
        DERIVED / "freshman_test_routes.tsv", freshman_test_route_rows(rows)
    )
    pathways.write_tsv(DERIVED / "national_test_routes.tsv",
                       national_test_route_rows(rows, all_first_time))
    pathways.write_tsv(DERIVED / "freshman_admission_paths.tsv", paths)
    pathways.write_tsv(
        DERIVED / "open_admission_endpoint.tsv",
        open_admission_endpoint_rows(graduates, characteristics, enrollment),
    )
    pathways.write_tsv(DERIVED / "freshman_admission_considerations.tsv",
                       consideration_rows(graduates, admissions))
    component_rows = test_component_rows(rows)
    pathways.write_tsv(DERIVED / "freshman_test_route_ability.tsv", component_rows)
    coverage = evidence_coverage(rows)
    print(
        f"wrote {len(rows):,} institutions; fall-2019 tests cover "
        f"{coverage['bachelors_domestic']:,} current domestic bachelor's awards"
    )


if __name__ == "__main__":
    main()
