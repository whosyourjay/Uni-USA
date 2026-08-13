"""Shared institution-level freshman score helpers."""

from statistics import median

import ability
import calibrate_tests


def route_lookup(institutions):
    bases = [
        {
            "unitid": row["unitid"],
            "institution": row["institution"],
            "state": row["state"],
            "bachelors_domestic": 0,
            "direct_bachelors_8yr": 0,
            "transfer_bachelors_8yr": 0,
            "transfer_share_bachelors_8yr": "",
            "direct_bachelor_rate_8yr": "",
        }
        for row in institutions
    ]
    evidence = ability.ability_evidence_rows(bases, ability.load_admissions())
    components = ability.test_component_rows(evidence)
    percentiles = calibrate_tests.component_percentile_rows(components)
    return {
        (row["unitid"], row["route"]): round(
            row["estimated_route_central_test_taker_percentile"], 3
        )
        for row in calibrate_tests.route_percentile_rows(percentiles)
    }


def route_fields(unitid, routes):
    sat = routes.get((unitid, "SAT"), "")
    act = routes.get((unitid, "ACT"), "")
    values = [value for value in (sat, act) if value != ""]
    labels = [name for name, value in (("SAT", sat), ("ACT", act)) if value != ""]
    return {
        "freshman_score": round(median(values), 3) if values else "",
        "sat_taker_percentile_2019": sat,
        "act_taker_percentile_2019": act,
        "freshman_score_basis": "median of " + " and ".join(labels) if labels else "",
    }
