#!/usr/bin/env python3
"""Predict the entering ability of origins whose own entrants send no scores.

Every institution reports enrollment, completion, and admission policy, so those
cover the community colleges and open-admission universities that report no test
scores.  Fitting them against the four-year institutions that do report a score
replaces one median per origin type with a prediction per school.

Four-year predictions stand on their own, since the fit is trained on four-year
schools measuring bachelor's completion.  Completion carries most of the fit and
means something else at a two-year school, so the fit only orders those schools
and the level stays on the median their own scored peers support.  Putting both
levels on the outcome-measure clock, which fixes the window at eight years, does
not close that gap: it widens it, because the same file counts the part-time and
returning entrants who make up most of a community college.
"""

from collections import defaultdict
from math import log
from statistics import median

from uniusa import origins, pathways, rank_ability


COHORT_TYPES = {2, 29}
COMPLETER_TYPES = {3, 30}
TRANSFER_TYPES = {4, 33}
UNDERGRADUATE_LEVEL = 2
FULL_TIME_UNDERGRADUATE_LEVEL = 22
FOUR_YEAR = origins.ORIGIN_ORDER[0]
FOUR_YEAR_LEVEL = 1
MINIMUM_ANCHOR_ORIGINS = 5
FEATURE_COLUMNS = (
    "completion_rate",
    "transfer_out_rate",
    "full_time_share",
    "log_undergraduates",
    "open_admission",
    "is_public",
)
SCORE_RANGE = (0.0, 100.0)


def graduation_counts():
    """Cohort, completer, and transfer-out totals per institution."""
    counts = defaultdict(lambda: defaultdict(float))
    for row in pathways.zip_rows("GR2023.zip"):
        kind = pathways.number(row["GRTYPE"])
        domestic = pathways.number(row["GRTOTLT"]) - pathways.number(row["GRNRALT"])
        totals = counts[pathways.number(row["UNITID"])]
        if kind in COHORT_TYPES:
            totals["cohort"] += domestic
        elif kind in COMPLETER_TYPES:
            totals["completers"] += domestic
        elif kind in TRANSFER_TYPES:
            totals["transfers"] += domestic
    return counts


def award_counts():
    """Entrants and eight-year award holders per institution, on one clock.

    Graduation rates run on each level's own normal time, so a two-year school
    is judged at three years and a four-year school at six.  Outcome measures
    fix the window at eight years for everyone and count the part-time and
    returning entrants the graduation cohorts leave out.
    """
    counts = defaultdict(lambda: defaultdict(float))
    for row in pathways.zip_rows("OM2023.zip"):
        if pathways.number(row["OMCHRT"]) not in pathways.OM_COHORTS:
            continue
        totals = counts[pathways.number(row["UNITID"])]
        totals["entrants"] += pathways.number(row["OMACHRT"])
        totals["awarded"] += pathways.number(row["OMAWDN8"])
    return counts


def enrollment_counts():
    """Undergraduate head counts, all students and full-time, per institution."""
    counts = defaultdict(lambda: defaultdict(float))
    for row in pathways.zip_rows("EF2019A.zip"):
        level = pathways.number(row["EFALEVEL"])
        if level in (UNDERGRADUATE_LEVEL, FULL_TIME_UNDERGRADUATE_LEVEL):
            counts[pathways.number(row["UNITID"])][level] += pathways.number(
                row["EFTOTLT"]
            )
    return counts


def open_admission_flags():
    return {
        pathways.number(row["UNITID"]): pathways.number(row["OPENADMP"]) == 1
        for row in pathways.zip_rows("IC2019.zip")
    }


def institution_features(unitid, directory, graduation, awards, enrollment,
                         open_admission):
    """One origin's features, or None without both enrollment and a cohort."""
    students = enrollment.get(unitid, {})
    undergraduates = students.get(UNDERGRADUATE_LEVEL, 0)
    totals = graduation.get(unitid, {})
    cohort = totals.get("cohort", 0)
    entrants = awards.get(unitid, {}).get("entrants", 0)
    if undergraduates <= 0 or cohort <= 0:
        return None
    return {
        "completion_rate": totals.get("completers", 0) / cohort,
        "award_rate": awards[unitid]["awarded"] / entrants if entrants else "",
        "transfer_out_rate": totals.get("transfers", 0) / cohort,
        "full_time_share": students.get(FULL_TIME_UNDERGRADUATE_LEVEL, 0)
        / undergraduates,
        "log_undergraduates": log(undergraduates),
        "open_admission": float(open_admission.get(unitid, False)),
        "is_public": float(
            pathways.number(directory.get(unitid, {}).get("CONTROL")) == 1
        ),
        "level": pathways.number(directory.get(unitid, {}).get("ICLEVEL")),
    }


def feature_table(unitids, directory):
    """Features for every requested origin that reports enrollment and a cohort."""
    graduation = graduation_counts()
    awards = award_counts()
    enrollment = enrollment_counts()
    open_admission = open_admission_flags()
    table = {}
    for unitid in unitids:
        features = institution_features(
            unitid, directory, graduation, awards, enrollment, open_admission
        )
        if features is not None:
            table[unitid] = features
    return table


def design_row(features, columns):
    return [1.0] + [features[column] for column in columns]


def fit_origin_scores(rows, table, columns=FEATURE_COLUMNS):
    """Least-squares fit of the freshman score on four-year scored origins."""
    trained = [
        row for row in rows
        if row["origin_type"] == FOUR_YEAR
        and row["freshman_score"] != ""
        and row["origin_id"] in table
    ]
    fit = rank_ability.least_squares(
        [design_row(table[row["origin_id"]], columns) for row in trained],
        [row["freshman_score"] for row in trained],
    )
    return {**fit, "trained_origins": len(trained)}


def raw_prediction(features, fit, columns=FEATURE_COLUMNS):
    low, high = SCORE_RANGE
    predicted = sum(
        weight * value
        for weight, value in zip(fit["coefficients"], design_row(features, columns))
    )
    return min(max(predicted, low), high)


def level_offsets(rows, table, fit, columns=FEATURE_COLUMNS):
    """Shift per institutional level, since completion means its own thing there.

    Four-year schools train the fit and take no shift.  A two-year school is
    judged on associate degrees in three years rather than bachelor's degrees in
    six, and loses its strongest students to transfer before either, so its
    scored peers set where that whole level sits.  Levels with too few scored
    schools to anchor keep the fit's own level.
    """
    scored = defaultdict(list)
    for row in rows:
        features = table.get(row["origin_id"])
        if features is not None and row["freshman_score"] != "":
            scored[features["level"]].append(row)
    offsets = defaultdict(float)
    for level, members in scored.items():
        if level == FOUR_YEAR_LEVEL or len(members) < MINIMUM_ANCHOR_ORIGINS:
            continue
        weight = lambda row: row["transfer_out_domestic"]
        offsets[level] = pathways.weighted_median(
            members, weight, lambda row: row["freshman_score"]
        ) - pathways.weighted_median(
            members, weight,
            lambda row: raw_prediction(table[row["origin_id"]], fit, columns)
        )
    return offsets


def predicted_scores(rows, table, columns=FEATURE_COLUMNS):
    """Predicted freshman score per origin, with the fit that produced them."""
    fit = fit_origin_scores(rows, table, columns)
    offsets = level_offsets(rows, table, fit, columns)
    low, high = SCORE_RANGE
    predictions = {}
    for row in rows:
        features = table.get(row["origin_id"])
        if features is None:
            continue
        shifted = raw_prediction(features, fit, columns) + offsets[features["level"]]
        predictions[row["origin_id"]] = min(max(shifted, low), high)
    return predictions, fit


def reporting_rows(rows, table):
    """Median covariate of scored against unscored origins, per level.

    The fit claims unscored four-year schools sit well below the ones that
    report, so these are the observed numbers that claim rests on.
    """
    groups = defaultdict(lambda: defaultdict(list))
    for row in rows:
        features = table.get(row["origin_id"])
        if features is None:
            continue
        kind = "scored" if row["freshman_score"] != "" else "unscored"
        groups[features["level"]][kind].append(features)
    output = []
    for level in sorted(groups):
        for kind, members in sorted(groups[level].items()):
            output.append({
                "level": level,
                "reporting": kind,
                "origins": len(members),
                **{
                    column: round(median(row[column] for row in members), 4)
                    for column in FEATURE_COLUMNS
                },
            })
    return output


def model_rows(rows, table, predictions):
    return [
        {
            "origin_id": row["origin_id"],
            "origin": row["origin"],
            "state": row["state"],
            "origin_type": row["origin_type"],
            "transfer_out_domestic": row["transfer_out_domestic"],
            "freshman_score": row["freshman_score"],
            "predicted_score": round(predictions[row["origin_id"]], 3),
            **{
                column: round(table[row["origin_id"]][column], 4)
                for column in FEATURE_COLUMNS
            },
        }
        for row in rows
        if row["origin_id"] in predictions
    ]


def clock_rows(rows, table):
    """What each completion measure costs, judged by the shift it leaves behind.

    A measure that means the same thing at every level needs no level shift, so
    the size of that shift says how much of the gap was the clock.
    """
    shared = {
        unitid: features for unitid, features in table.items()
        if features["award_rate"] != ""
    }
    kept = [row for row in rows if row["origin_id"] in shared]
    output = []
    for measure in (("completion_rate",), ("award_rate",),
                    ("completion_rate", "award_rate")):
        columns = measure + tuple(
            column for column in FEATURE_COLUMNS
            if column not in ("completion_rate", "award_rate")
        )
        fit = fit_origin_scores(kept, shared, columns)
        offsets = level_offsets(kept, shared, fit, columns)
        output.append({
            "completion_measure": " + ".join(measure),
            "r2": round(fit["r2"], 4),
            "residual_sd": round(fit["residual_sd"], 3),
            "two_year_offset": round(offsets[2], 3),
        })
    return output


def main():
    from uniusa import transfer

    rows, _ = transfer.build_transfer_tables()
    table = feature_table([row["origin_id"] for row in rows], pathways.load_directory())
    predictions, fit = predicted_scores(rows, table)
    pathways.write_tsv(
        pathways.DERIVED / "origin_model.tsv", model_rows(rows, table, predictions)
    )
    pathways.write_tsv(
        pathways.DERIVED / "origin_reporting.tsv", reporting_rows(rows, table)
    )
    pathways.write_tsv(
        pathways.DERIVED / "origin_clock.tsv", clock_rows(rows, table)
    )
    offsets = level_offsets(rows, table, fit)
    print(
        f"fit {fit['trained_origins']:,} four-year origins: r2 {fit['r2']:.3f}, "
        f"residual {fit['residual_sd']:.2f}; predicted {len(predictions):,} origins; "
        f"level offsets {dict(offsets)}"
    )


if __name__ == "__main__":
    main()
