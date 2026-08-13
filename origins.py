#!/usr/bin/env python3
"""Build the complete recent first-time postsecondary origin universe."""

from collections import defaultdict

import pathways
import scores


ORIGIN_ORDER = (
    "Four-or-more-year institution",
    "Public associate-degree institution (community-college proxy)",
    "Nonpublic associate-degree institution",
    "Two-to-four-year certificate/diploma institution",
    "Less-than-two-year institution",
    "Directory unmatched",
)


def origin_type(directory_row):
    level = pathways.number(directory_row.get("ICLEVEL"))
    control = pathways.number(directory_row.get("CONTROL"))
    highest = pathways.number(directory_row.get("HLOFFER"))
    if level == 1:
        return ORIGIN_ORDER[0]
    if level == 2 and highest == 3 and control == 1:
        return ORIGIN_ORDER[1]
    if level == 2 and highest == 3:
        return ORIGIN_ORDER[2]
    if level == 2 and highest == 4:
        return ORIGIN_ORDER[3]
    if level == 3:
        return ORIGIN_ORDER[4]
    return ORIGIN_ORDER[5]


def origin_rows(directory, enrollment):
    rows = []
    for unitid, levels in enrollment.items():
        entrants = levels.get(4, {"all": 0, "domestic": 0})
        if entrants["domestic"] <= 0:
            continue
        institution = directory.get(unitid, {})
        rows.append({
            "ability": "",
            "origin_id": unitid,
            "origin": institution.get("INSTNM", ""),
            "state": institution.get("STABBR", ""),
            "origin_type": origin_type(institution),
            "control": pathways.CONTROL_NAMES.get(
                pathways.number(institution.get("CONTROL")), "unknown"
            ),
            "first_time_entrants_domestic_2023_24": entrants["domestic"],
            "first_time_entrants_all_2023_24": entrants["all"],
        })

    bases = [
        {
            "unitid": row["origin_id"],
            "institution": row["origin"],
            "state": row["state"],
        }
        for row in rows
    ]
    routes = scores.route_lookup(bases)
    for row in rows:
        row.update(scores.route_fields(row["origin_id"], routes))
        row["ability"] = row["freshman_score"]
        row["ability_status"] = (
            "freshman SAT/ACT proxy" if row["ability"] != "" else "unscored"
        )
    return sorted(
        rows,
        key=lambda row: (
            -row["first_time_entrants_domestic_2023_24"], row["origin_id"]
        ),
    )


def pathway_rows(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["origin_type"]].append(row)
    total = sum(row["first_time_entrants_domestic_2023_24"] for row in rows)
    output = []
    for category in ORIGIN_ORDER:
        values = grouped[category]
        if not values:
            continue
        domestic = sum(
            row["first_time_entrants_domestic_2023_24"] for row in values
        )
        output.append({
            "origin_type": category,
            "institutions": len(values),
            "first_time_entrants_domestic_2023_24": domestic,
            "share_domestic_first_time_entrants": domestic / total,
            "first_time_entrants_all_2023_24": sum(
                row["first_time_entrants_all_2023_24"] for row in values
            ),
            "entrants_at_origins_with_sat_evidence": sum(
                row["first_time_entrants_domestic_2023_24"]
                for row in values
                if row["sat_taker_percentile_2019"] != ""
            ),
            "entrants_at_origins_with_act_evidence": sum(
                row["first_time_entrants_domestic_2023_24"]
                for row in values
                if row["act_taker_percentile_2019"] != ""
            ),
        })
    return output


def main():
    rows = origin_rows(pathways.load_directory(), pathways.load_enrollment())
    summary = pathway_rows(rows)
    pathways.write_tsv(pathways.DERIVED / "origin_institution_ability.tsv", rows)
    pathways.write_tsv(pathways.DERIVED / "origin_pathways.tsv", summary)
    print(
        f"wrote {len(rows):,} origin institutions with "
        f"{sum(row['first_time_entrants_domestic_2023_24'] for row in rows):,} "
        "domestic first-time entrants"
    )


if __name__ == "__main__":
    main()
