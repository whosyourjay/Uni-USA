#!/usr/bin/env python3
"""Score transfers by their origin school, then deal them to destinations.

Every transfer carries the median ability of the school they left, measured
where its freshmen send scores and predicted from enrollment and completion
where they do not.  Stacking that national pool from strongest to weakest and
dealing it to destinations from the most selective down replaces one national
average with the slice of the pool each school could plausibly attract.
Destinations whose freshmen send no test scores have no measured selectivity and
sit below the schools that do.
"""

from collections import defaultdict
from functools import lru_cache

from uniusa import origin_model, origins, pathways, scores


def load_transfer_out():
    return {
        unitid: totals["transfers"]
        for unitid, totals in origin_model.graduation_counts().items()
        if totals["transfers"] > 0
    }


def weighted_mean(rows, field):
    total = sum(row["transfer_out_domestic"] for row in rows)
    return sum(row[field] * row["transfer_out_domestic"] for row in rows) / total


def weighted_median(rows, field):
    return pathways.weighted_median(
        rows, lambda row: row["transfer_out_domestic"], lambda row: row[field]
    )


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

    score_origins(rows, directory)
    return sorted(rows, key=lambda row: (-row["transfer_out_domestic"], row["origin_id"]))


def score_origins(rows, directory):
    """Give every origin a score: observed, predicted, or its type's median."""
    predictions, _ = origin_model.predicted_scores(
        rows, origin_model.feature_table([row["origin_id"] for row in rows], directory)
    )
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
        if row["freshman_score"] != "":
            row["transfer_origin_score"] = row["freshman_score"]
            row["score_kind"] = "observed freshman score"
        elif row["origin_id"] in predictions:
            row["transfer_origin_score"] = round(predictions[row["origin_id"]], 3)
            row["score_kind"] = "predicted from enrollment and completion"
        else:
            row["transfer_origin_score"] = fallbacks.get(
                row["origin_type"], global_fallback
            )
            row["score_kind"] = "origin-type median imputation"


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


def origin_pool(rows):
    """The national transfer pool as (origin score, transfers) blocks, best first."""
    return sorted(
        (
            (row["transfer_origin_score"], float(row["transfer_out_domestic"]))
            for row in rows
        ),
        reverse=True,
    )


def deal_pool(pool, seats, epsilon=1e-9):
    """Mean and range of the pool slice each destination takes, in the order given.

    Seats count transfers graduating years later, so they are rescaled onto the
    pool, which counts transfers leaving their origin.  A destination asking for
    no seats takes no slice.
    """
    total_seats = sum(seats)
    scale = sum(weight for _, weight in pool) / total_seats if total_seats else 0
    index, remaining = 0, pool[0][1]
    for demand in seats:
        wanted, taken, carried, edges = demand * scale, 0.0, 0.0, []
        while wanted - taken > epsilon and index < len(pool):
            score, _ = pool[index]
            amount = min(wanted - taken, remaining)
            edges = [edges[0] if edges else score, score]
            carried += score * amount
            taken += amount
            remaining -= amount
            if remaining <= epsilon:
                index += 1
                remaining = pool[index][1] if index < len(pool) else 0.0
        yield {
            "transfer_score": round(carried / taken, 3) if taken else "",
            "pool_top": edges[0] if edges else "",
            "pool_bottom": edges[1] if edges else "",
        }


def destination_seats(institution_rows, graduates):
    """Every destination's transfer graduates, most selective school first."""
    lookup = scores.route_lookup(graduates)
    seats, direct, unselected = defaultdict(float), defaultdict(float), defaultdict(float)
    for row in institution_rows:
        if row["route"] == "Transfer":
            seats[row["unitid"]] += row["estimated_bachelors"]
            continue
        direct[row["unitid"]] += row["estimated_bachelors"]
        if row["route"] == "Open admission":
            unselected[row["unitid"]] += row["estimated_bachelors"]
    rows = [
        {
            "unitid": unitid,
            "seats": round(count, 3),
            "freshman_score": scores.route_fields(unitid, lookup)["freshman_score"],
            "open_share": round(
                unselected[unitid] / direct[unitid] if direct[unitid] else 1.0, 6
            ),
        }
        for unitid, count in seats.items()
    ]
    rows.sort(key=lambda row: (
        row["freshman_score"] == "",
        -(row["freshman_score"] or 0),
        row["open_share"],
        row["unitid"],
    ))
    return rows


def destination_scores(institution_rows, graduates):
    """Transfer score each destination inherits from its slice of the pool."""
    rows = destination_seats(institution_rows, graduates)
    pool = origin_pool(build_transfer_tables()[0])
    return {
        row["unitid"]: {**row, **taken}
        for row, taken in zip(rows, deal_pool(pool, [row["seats"] for row in rows]))
    }


@lru_cache(maxsize=None)
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
