#!/usr/bin/env python3
"""Cross-calibrate the SAT and ACT institution routes without merging them.

IPEDS reports two SAT section distributions and one ACT composite distribution.
Each score is first placed in its own national enrolled-submitter pool by
ability.py.  This script then fits the same one-component measurement model used
in the Taiwan project on institution/quartile observations:

    pool_percentile = intercept_measurement + slope_measurement * component

The fitted lines put all three measurements on one latent scale.  SAT retains
its own estimate (from its two section measurements), ACT retains its estimate,
and institutions reporting both retain the ACT-minus-SAT disagreement.
"""

from collections import defaultdict
from math import sqrt

import ability
import pathways


MEASUREMENT = {
    ("SAT", "reading and writing"): "SAT reading/writing",
    ("SAT", "math"): "SAT math",
    ("ACT", "composite"): "ACT composite",
}


def weighted_mean(values):
    total = sum(weight for _, weight in values)
    if total <= 0:
        raise ValueError("weighted mean has no mass")
    return sum(value * weight for value, weight in values) / total


def normalize_components(components, weights):
    mean = weighted_mean([(value, weights[key]) for key, value in components.items()])
    variance = weighted_mean([
        ((value - mean) ** 2, weights[key])
        for key, value in components.items()
    ])
    if variance <= 0:
        raise ValueError("ability component has no variance")
    sd = sqrt(variance)
    return {key: (value - mean) / sd for key, value in components.items()}


def regression(observations, components):
    """Fit one weighted line per measurement."""
    grouped = defaultdict(list)
    for row in observations:
        grouped[row["measurement"]].append(row)
    output = {}
    for measurement, rows in grouped.items():
        x_mean = weighted_mean([
            (components[row["key"]], row["weight"]) for row in rows
        ])
        y_mean = weighted_mean([(row["value"], row["weight"]) for row in rows])
        covariance = sum(
            row["weight"]
            * (components[row["key"]] - x_mean)
            * (row["value"] - y_mean)
            for row in rows
        )
        variance = sum(
            row["weight"] * (components[row["key"]] - x_mean) ** 2
            for row in rows
        )
        if variance <= 0:
            raise ValueError(f"no component variance for {measurement}")
        slope = covariance / variance
        if slope <= 0:
            raise ValueError(f"nonpositive loading for {measurement}: {slope}")
        output[measurement] = {
            "intercept": y_mean - slope * x_mean,
            "slope": slope,
        }
    return output


def calibration_observations(component_rows):
    rows = []
    for row in component_rows:
        measurement = MEASUREMENT[(row["route"], row["component"])]
        for quartile in (25, 75):
            rows.append({
                "key": (row["unitid"], quartile),
                "unitid": row["unitid"],
                "quartile": quartile,
                "measurement": measurement,
                "value": row[f"route_pool_percentile_q{quartile}"],
                "raw_weight": row["submitters_2019"],
            })

    measurements_by_key = defaultdict(set)
    for row in rows:
        measurements_by_key[row["key"]].add(row["measurement"])
    linked = [
        row for row in rows
        if len(measurements_by_key[row["key"]]) >= 2
    ]

    # Give each measurement equal total influence; within a measurement, keep
    # the IPEDS submitter weights.  SAT therefore does not get twice ACT's
    # influence merely because it has two published sections.
    totals = defaultdict(float)
    for row in linked:
        totals[row["measurement"]] += row["raw_weight"]
    for row in linked:
        row["weight"] = row["raw_weight"] / totals[row["measurement"]]
    return linked


def fit_component(component_rows, tolerance=1e-10, max_iterations=1_000):
    observations = calibration_observations(component_rows)
    grouped = defaultdict(list)
    for row in observations:
        grouped[row["key"]].append(row)

    measurement_moments = {}
    for measurement in set(row["measurement"] for row in observations):
        rows = [row for row in observations if row["measurement"] == measurement]
        mean = weighted_mean([(row["value"], row["weight"]) for row in rows])
        variance = weighted_mean([
            ((row["value"] - mean) ** 2, row["weight"]) for row in rows
        ])
        measurement_moments[measurement] = (mean, sqrt(variance))

    components = {
        key: weighted_mean([
            (
                (row["value"] - measurement_moments[row["measurement"]][0])
                / measurement_moments[row["measurement"]][1],
                row["weight"],
            )
            for row in rows
        ])
        for key, rows in grouped.items()
    }
    key_weights = {
        key: sum(row["weight"] for row in rows) for key, rows in grouped.items()
    }
    components = normalize_components(components, key_weights)

    for iteration in range(1, max_iterations + 1):
        parameters = regression(observations, components)
        updated = {}
        for key, rows in grouped.items():
            numerator = sum(
                row["weight"]
                * parameters[row["measurement"]]["slope"]
                * (row["value"] - parameters[row["measurement"]]["intercept"])
                for row in rows
            )
            denominator = sum(
                row["weight"] * parameters[row["measurement"]]["slope"] ** 2
                for row in rows
            )
            updated[key] = numerator / denominator
        updated = normalize_components(updated, key_weights)
        change = max(abs(updated[key] - components[key]) for key in components)
        components = updated
        if change < tolerance:
            break
    else:
        raise RuntimeError("test-route calibration did not converge")

    parameters = regression(observations, components)
    for measurement, parameter in parameters.items():
        rows = [row for row in observations if row["measurement"] == measurement]
        error = sum(
            row["weight"]
            * (
                row["value"]
                - parameter["intercept"]
                - parameter["slope"] * components[row["key"]]
            ) ** 2
            for row in rows
        ) / sum(row["weight"] for row in rows)
        parameter["rmse_pool_percentile_points"] = sqrt(error)
        parameter["observations"] = len(rows)
    return {
        "components": components,
        "parameters": parameters,
        "iterations": iteration,
        "observations": observations,
    }


def calibrated_value(row, quartile, parameters):
    measurement = MEASUREMENT[(row["route"], row["component"])]
    parameter = parameters[measurement]
    return (
        row[f"route_pool_percentile_q{quartile}"] - parameter["intercept"]
    ) / parameter["slope"]


def route_rows(component_rows, fit):
    """Return separate SAT and ACT estimates on the fitted common component."""
    grouped = defaultdict(list)
    for row in component_rows:
        grouped[(row["unitid"], row["route"])].append(row)

    output = []
    for (unitid, route), rows in grouped.items():
        expected = 2 if route == "SAT" else 1
        if len(rows) != expected:
            continue
        first = rows[0]
        result = {
            "unitid": unitid,
            "institution": first["institution"],
            "state": first["state"],
            "route": route,
            "submitters_2019": first["submitters_2019"],
        }
        for component in ("reading_and_writing", "math", "composite"):
            for quartile in (25, 75):
                result[f"{component}_pool_percentile_q{quartile}"] = ""
        for quartile in (25, 75):
            values = [
                calibrated_value(row, quartile, fit["parameters"])
                for row in rows
            ]
            result[f"common_component_q{quartile}"] = sum(values) / len(values)
            for row in rows:
                slug = row["component"].replace(" ", "_")
                result[f"{slug}_pool_percentile_q{quartile}"] = row[
                    f"route_pool_percentile_q{quartile}"
                ]
        output.append(result)

    by_unitid = defaultdict(dict)
    for row in output:
        by_unitid[row["unitid"]][row["route"]] = row
    for routes in by_unitid.values():
        if set(routes) != {"SAT", "ACT"}:
            continue
        for quartile in (25, 75):
            gap = (
                routes["ACT"][f"common_component_q{quartile}"]
                - routes["SAT"][f"common_component_q{quartile}"]
            )
            routes["SAT"][f"act_minus_sat_q{quartile}"] = gap
            routes["ACT"][f"act_minus_sat_q{quartile}"] = gap
    for row in output:
        for quartile in (25, 75):
            row.setdefault(f"act_minus_sat_q{quartile}", "")
    return sorted(output, key=lambda row: (row["unitid"], row["route"]))


def parameter_rows(fit):
    return [
        {
            "measurement": measurement,
            **parameter,
            "iterations": fit["iterations"],
            "model": (
                "route-pool percentile = intercept + slope * common component"
            ),
        }
        for measurement, parameter in sorted(fit["parameters"].items())
    ]


def disagreement_rows(routes):
    paired = defaultdict(dict)
    for row in routes:
        paired[row["unitid"]][row["route"]] = row
    output = []
    for quartile in (25, 75):
        rows = [
            values for values in paired.values()
            if set(values) == {"SAT", "ACT"}
        ]
        weights = [
            min(values["SAT"]["submitters_2019"], values["ACT"]["submitters_2019"])
            for values in rows
        ]
        gaps = [values["SAT"][f"act_minus_sat_q{quartile}"] for values in rows]
        total = sum(weights)
        output.append({
            "quartile": quartile,
            "paired_institutions": len(rows),
            "weighted_mean_act_minus_sat": sum(
                gap * weight for gap, weight in zip(gaps, weights)
            ) / total,
            "weighted_rmse_act_minus_sat": sqrt(sum(
                gap ** 2 * weight for gap, weight in zip(gaps, weights)
            ) / total),
            "scale": "common component units (linked-observation weighted SD = 1)",
        })
    return output


def main():
    graduates = pathways.graduate_rows(
        pathways.load_directory(),
        pathways.load_completions(),
        pathways.load_outcomes(),
        pathways.load_enrollment(),
    )
    evidence = ability.ability_evidence_rows(graduates, ability.load_admissions())
    components = ability.test_component_rows(evidence)
    fit = fit_component(components)
    routes = route_rows(components, fit)
    pathways.write_tsv(
        pathways.DERIVED / "test_calibration_parameters.tsv", parameter_rows(fit)
    )
    pathways.write_tsv(
        pathways.DERIVED / "freshman_test_route_common_scale.tsv", routes
    )
    disagreements = disagreement_rows(routes)
    pathways.write_tsv(
        pathways.DERIVED / "test_route_disagreement.tsv", disagreements
    )
    print(
        f"calibrated {len(routes):,} institution-routes; "
        f"{disagreements[0]['paired_institutions']:,} institutions report both"
    )


if __name__ == "__main__":
    main()
