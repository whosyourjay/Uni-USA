#!/usr/bin/env python3
"""Estimate a pooled transfer score from transfer-out origin institutions."""

from collections import defaultdict

from uniusa import origins, pathways, scores


TRANSFER_TYPES = {4, 33}


def load_transfer_out():
    output = {}
    for row in pathways.zip_rows("GR2023.zip"):
        if pathways.number(row["GRTYPE"]) not in TRANSFER_TYPES:
            continue
        unitid = pathways.number(row["UNITID"])
        domestic = pathways.number(row["GRTOTLT"]) - pathways.number(row["GRNRALT"])
        if domestic > 0:
            output[unitid] = domestic
    return output


def weighted_mean(rows, field):
    total = sum(row["transfer_out_domestic"] for row in rows)
    return sum(row[field] * row["transfer_out_domestic"] for row in rows) / total


def weighted_median(rows, field):
    total = sum(row["transfer_out_domestic"] for row in rows)
    cumulative = 0
    for row in sorted(rows, key=lambda row: row[field]):
        cumulative += row["transfer_out_domestic"]
        if cumulative >= total / 2:
            return row[field]
    raise ValueError("Empty weighted median")


def transfer_origin_rows(directory, transfers):
    bases = [
        {
            "unitid": unitid,
            "institution": directory.get(unitid, {}).get("INSTNM", ""),
            "state": directory.get(unitid, {}).get("STABBR", ""),
        }
        for unitid in transfers
    ]
    routes = scores.route_lookup(bases)
    rows = []
    for base in bases:
        unitid = base["unitid"]
        route = scores.route_fields(unitid, routes)
        rows.append({
            "origin_id": unitid,
            "origin": base["institution"],
            "state": base["state"],
            "origin_type": origins.origin_type(directory.get(unitid, {})),
            "transfer_out_domestic": transfers[unitid],
            **route,
        })

    observed = defaultdict(list)
    for row in rows:
        if row["freshman_score"] != "":
            observed[row["origin_type"]].append(row)
    all_observed = [row for values in observed.values() for row in values]
    global_fallback = weighted_median(all_observed, "freshman_score")
    fallbacks = {
        category: weighted_median(values, "freshman_score")
        for category, values in observed.items()
    }
    for row in rows:
        if row["freshman_score"] == "":
            row["transfer_origin_score"] = fallbacks.get(
                row["origin_type"], global_fallback
            )
            row["score_kind"] = "origin-type median imputation"
        else:
            row["transfer_origin_score"] = row["freshman_score"]
            row["score_kind"] = "observed freshman score"
    return sorted(rows, key=lambda row: (-row["transfer_out_domestic"], row["origin_id"]))


def summary_rows(rows):
    groups = defaultdict(list)
    groups["All origins"] = rows
    for row in rows:
        groups[row["origin_type"]].append(row)
    output = []
    for category in ("All origins",) + origins.ORIGIN_ORDER:
        values = groups[category]
        if not values:
            continue
        total = sum(row["transfer_out_domestic"] for row in values)
        measured = sum(
            row["transfer_out_domestic"]
            for row in values
            if row["score_kind"] == "observed freshman score"
        )
        output.append({
            "origin_type": category,
            "institutions": len(values),
            "transfer_out_domestic": total,
            "measured_transfer_out_domestic": measured,
            "measured_share": measured / total,
            "weighted_mean_freshman_score": round(
                weighted_mean(values, "transfer_origin_score"), 3
            ),
            "weighted_median_freshman_score": round(
                weighted_median(values, "transfer_origin_score"), 3
            ),
        })
    return output


def build_transfer_tables():
    rows = transfer_origin_rows(pathways.load_directory(), load_transfer_out())
    return rows, summary_rows(rows)


def main():
    rows, summary = build_transfer_tables()
    pathways.write_tsv(pathways.DERIVED / "transfer_origin_scores.tsv", rows)
    pathways.write_tsv(pathways.DERIVED / "transfer_score.tsv", summary)
    total = summary[0]
    print(
        f"weighted {total['transfer_out_domestic']:,} transfer-outs; "
        f"median freshman score {total['weighted_median_freshman_score']:.3f}"
    )


if __name__ == "__main__":
    main()
