#!/usr/bin/env python3
"""Build 2023 freshman-admission route and ability evidence."""

from pathlib import Path

import pathways

ROOT = Path(__file__).parent
DERIVED = ROOT / "derived"
SAT_FIELDS = ("SATVR25", "SATVR50", "SATVR75", "SATMT25", "SATMT50", "SATMT75")
ACT_FIELDS = ("ACTCM25", "ACTCM50", "ACTCM75")
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
    "ADMCON10": "Work experience",
    "ADMCON11": "Personal statement or essay",
    "ADMCON12": "Legacy status",
}
CONSIDERATION_STATUS = {
    1: "required",
    5: "considered if submitted",
    3: "not considered",
}


def present(row, fields):
    return all(pathways.number(row.get(field)) > 0 for field in fields)


def load_admissions():
    return {
        pathways.number(row["UNITID"]): row
        for row in pathways.zip_rows("ADM2023.zip")
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


def score_quantiles(admission, route):
    def value(field):
        raw = admission.get(field)
        return raw if isinstance(raw, int) else pathways.number(raw)

    if route == "SAT":
        return tuple(
            value(f"SATVR{q}") + value(f"SATMT{q}")
            for q in (25, 50, 75)
        )
    if route == "ACT":
        return tuple(
            value(f"ACTCM{q}")
            for q in (25, 50, 75)
        )
    return (0, 0, 0)


def ability_evidence_rows(graduates, admissions):
    output = []
    for graduate in graduates:
        admission = admissions.get(graduate["unitid"], {})
        has_sat = present(admission, SAT_FIELDS)
        has_act = present(admission, ACT_FIELDS)
        sat_share = pathways.number(admission.get("SATPCT")) / 100
        act_share = pathways.number(admission.get("ACTPCT")) / 100

        # SAT and ACT reporters can overlap. These bounds are identifiable from
        # IPEDS without assuming how many entrants sent both tests.
        coverage_min = max(sat_share, act_share)
        coverage_max = min(1, sat_share + act_share)
        enrolled = pathways.number(admission.get("ENRLT"))
        sat_submitters = pathways.number(admission.get("SATNUM"))
        act_submitters = pathways.number(admission.get("ACTNUM"))
        # The two submitter counts overlap by an unknown amount.  These are the
        # sharp bounds on entrants with neither score, institution by institution.
        no_test_lower = max(0, enrolled - sat_submitters - act_submitters)
        no_test_upper = max(0, enrolled - max(sat_submitters, act_submitters))
        row = {
            "unitid": graduate["unitid"],
            "institution": graduate["institution"],
            "state": graduate["state"],
            "bachelors_domestic": graduate["bachelors_domestic"],
            "direct_bachelors_8yr": graduate["direct_bachelors_8yr"],
            "transfer_bachelors_8yr": graduate["transfer_bachelors_8yr"],
            "transfer_share_bachelors_8yr": graduate["transfer_share_bachelors_8yr"],
            "direct_bachelor_rate_8yr": graduate["direct_bachelor_rate_8yr"],
            "test_evidence_2023": evidence_label(has_sat, has_act),
            "test_policy_2023": policy_label(admission) if admission else "not reported",
            "first_time_enrolled_2023": enrolled,
            "sat_submitters_2023": sat_submitters,
            "sat_share_2023": sat_share if admission else "",
            "act_submitters_2023": act_submitters,
            "act_share_2023": act_share if admission else "",
            "test_coverage_lower_2023": coverage_min if admission else "",
            "test_coverage_upper_2023": coverage_max if admission else "",
            "no_reported_test_lower_2023": no_test_lower if admission else "",
            "no_reported_test_upper_2023": no_test_upper if admission else "",
        }
        for field in SAT_FIELDS + ACT_FIELDS:
            row[field.lower() + "_2023"] = pathways.number(admission.get(field)) or ""
        row["sat_total_median_2023"] = (
            pathways.number(admission["SATVR50"])
            + pathways.number(admission["SATMT50"])
            if has_sat else ""
        )
        row["act_composite_median_2023"] = (
            pathways.number(admission["ACTCM50"])
            if has_act else ""
        )
        output.append(row)
    return output


def freshman_route_rows(evidence):
    """Keep SAT and ACT as separate, non-exclusive measurement routes."""
    output = []
    for row in evidence:
        if row["first_time_enrolled_2023"] == 0:
            continue
        common = {
            "unitid": row["unitid"],
            "institution": row["institution"],
            "state": row["state"],
            "first_time_enrolled_2023": row["first_time_enrolled_2023"],
            "test_policy_2023": row["test_policy_2023"],
        }
        for route, count_field, share_field, fields in (
            ("SAT", "sat_submitters_2023", "sat_share_2023", SAT_FIELDS),
            ("ACT", "act_submitters_2023", "act_share_2023", ACT_FIELDS),
        ):
            if not all(row[field.lower() + "_2023"] != "" for field in fields):
                continue
            q25, q50, q75 = score_quantiles(
                {field: row[field.lower() + "_2023"] for field in fields}, route
            )
            output.append({
                **common,
                "route": route,
                "route_count_lower_2023": row[count_field],
                "route_count_upper_2023": row[count_field],
                "route_share_reported_2023": row[share_field],
                "score_scale": "SAT 400-1600" if route == "SAT" else "ACT 1-36",
                "score_q25_2023": q25,
                "score_q50_2023": q50,
                "score_q75_2023": q75,
            })
        output.append({
            **common,
            "route": "No reported SAT/ACT",
            "route_count_lower_2023": row["no_reported_test_lower_2023"],
            "route_count_upper_2023": row["no_reported_test_upper_2023"],
            "route_share_reported_2023": "",
            "score_scale": "none",
            "score_q25_2023": "",
            "score_q50_2023": "",
            "score_q75_2023": "",
        })
    return output


def national_route_rows(evidence):
    rows = [row for row in evidence if row["first_time_enrolled_2023"] > 0]
    enrolled = sum(row["first_time_enrolled_2023"] for row in rows)
    values = (
        ("SAT", sum(row["sat_submitters_2023"] for row in rows),
         sum(row["sat_submitters_2023"] for row in rows)),
        ("ACT", sum(row["act_submitters_2023"] for row in rows),
         sum(row["act_submitters_2023"] for row in rows)),
        ("No reported SAT/ACT",
         sum(row["no_reported_test_lower_2023"] for row in rows),
         sum(row["no_reported_test_upper_2023"] for row in rows)),
    )
    return [{
        "route": route,
        "first_time_enrolled_reporting_universe": enrolled,
        "people_lower": lower,
        "people_upper": upper,
        "share_lower": lower / enrolled,
        "share_upper": upper / enrolled,
        "additive": "no: SAT and ACT may overlap",
    } for route, lower, upper in values]


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
            "first_time_enrolled_reporting_universe": enrolled,
        }
        for code, status in CONSIDERATION_STATUS.items():
            matching = [row for row in rows if pathways.number(row.get(field)) == code]
            slug = status.replace(" ", "_")
            result[slug + "_institutions"] = len(matching)
            result[slug + "_enrolled"] = sum(
                pathways.number(row.get("ENRLT")) for row in matching
            )
        usable = result["required_enrolled"] + result["considered_if_submitted_enrolled"]
        result["required_or_considered_share"] = usable / enrolled if enrolled else ""
        output.append(result)
    return output


def evidence_coverage(rows):
    covered = [row for row in rows if row["test_evidence_2023"] != "none"]
    return {
        "institutions": len(covered),
        "bachelors_domestic": sum(row["bachelors_domestic"] for row in covered),
        "direct_bachelors_8yr": sum(row["direct_bachelors_8yr"] for row in covered),
    }


def main():
    graduates = pathways.graduate_rows(
        pathways.load_directory(),
        pathways.load_completions(),
        pathways.load_outcomes(),
        pathways.load_enrollment(),
    )
    rows = ability_evidence_rows(graduates, load_admissions())
    pathways.write_tsv(DERIVED / "institution_ability_evidence.tsv", rows)
    pathways.write_tsv(DERIVED / "freshman_ability_routes.tsv",
                       freshman_route_rows(rows))
    pathways.write_tsv(DERIVED / "national_freshman_routes.tsv",
                       national_route_rows(rows))
    pathways.write_tsv(DERIVED / "freshman_admission_considerations.tsv",
                       consideration_rows(graduates, load_admissions()))
    coverage = evidence_coverage(rows)
    print(
        f"wrote {len(rows):,} institutions; 2023 tests cover "
        f"{coverage['bachelors_domestic']:,} current domestic bachelor's awards"
    )


if __name__ == "__main__":
    main()
