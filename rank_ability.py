#!/usr/bin/env python3
"""Turn a C10 class-rank distribution into a national ability estimate.

National ability is standard normal. A high school's mean carries variance
`between`, so rank inside a class is driven by the residual `1 - between`.
Writing `shrink = sqrt(1 - between)`, a student at national z sits at
within-school z with mean `shrink * z` and variance `between`, and class rank
percentile is the normal CDF of that. This is why a school can put 99% of its
class in the top tenth without any of them being near the national 99.9th
percentile, and why spreading that 99% evenly across the top decile understates
the class badly.

Only the top-decile anchor identifies a school. The top-quarter anchor saturates
at 100% for every selective school, so solving both anchors for a per-school
spread reads a rounding difference as signal. The class spread is fitted once
across schools instead, by requiring the rank-implied ability to track published
test percentiles one-for-one.
"""

import csv
import math
from statistics import NormalDist

import class_rank
import pathways

NORMAL = NormalDist()
BETWEEN_SCHOOL_VARIANCE = 0.28
TOP_DECILE_CUT = NORMAL.inv_cdf(0.90)
SCHOOL_TABLE = class_rank.ROOT / "schools.tsv"


def shrink_factor(between=BETWEEN_SCHOOL_VARIANCE):
    return math.sqrt(1 - between)


def within_school_sd(class_sd, between=BETWEEN_SCHOOL_VARIANCE):
    """Spread of within-school z across one entering class."""
    return math.sqrt(shrink_factor(between) ** 2 * class_sd**2 + between)


def predicted_top_decile(national_z, class_sd, between=BETWEEN_SCHOOL_VARIANCE):
    """Share of a class centered at `national_z` ranking in its top tenth."""
    mean = shrink_factor(between) * national_z
    return 1 - NORMAL.cdf((TOP_DECILE_CUT - mean) / within_school_sd(class_sd, between))


def national_ability(top_10, class_sd, between=BETWEEN_SCHOOL_VARIANCE):
    """National z implied by the share of a class in its high schools' top tenth."""
    if not 0 < top_10 < 1:
        return None
    spread = within_school_sd(class_sd, between)
    return (TOP_DECILE_CUT + spread * NORMAL.inv_cdf(top_10)) / shrink_factor(between)


def regression(xs, ys):
    """Least-squares slope, intercept and residual spread."""
    n = len(xs)
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    spread = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / spread
    intercept = mean_y - slope * mean_x
    residuals = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    total = sum((y - mean_y) ** 2 for y in ys)
    return {
        "slope": slope,
        "intercept": intercept,
        "residual_sd": math.sqrt(sum(r**2 for r in residuals) / (n - 2)),
        "r2": 1 - sum(r**2 for r in residuals) / total if total else 0.0,
    }


def fit_class_spread(rows, between=BETWEEN_SCHOOL_VARIANCE):
    """Class spread that makes rank-implied ability move one-for-one with test z.

    Rank-implied z is affine in the probit of the top-decile share, so the
    regression slope scales with the within-school spread and inverts directly.
    """
    raw = regression(
        [row["taker_z"] for row in rows],
        [NORMAL.inv_cdf(row["top_10_pct"] / 100) for row in rows],
    )
    shrink = shrink_factor(between)
    spread = shrink / raw["slope"]
    variance = (spread**2 - between) / shrink**2
    return {
        "class_sd": math.sqrt(variance) if variance > 0 else 0.0,
        "within_school_sd": spread,
        "probit_slope": raw["slope"],
        "r2": raw["r2"],
    }


def load_school_percentiles(path=SCHOOL_TABLE):
    with open(path, encoding="utf-8", newline="") as handle:
        return {row["school"]: row for row in csv.DictReader(handle, delimiter="\t")}


def fitting_rows(rank_rows, schools):
    """Schools with a usable top-decile share and a published test percentile."""
    output = []
    for row in rank_rows:
        school = schools.get(row["school"])
        if school is None or not school.get("sat_taker_percentile"):
            continue
        if row["top_10_pct"] == "":
            continue
        top_10 = float(row["top_10_pct"])
        if not 0 < top_10 < 100:
            continue
        taker = float(school["sat_taker_percentile"])
        output.append({
            "school": row["school"],
            "top_10_pct": top_10,
            "rank_reporting_pct": row["rank_reporting_pct"],
            "taker_percentile": taker,
            "taker_z": NORMAL.inv_cdf(taker / 100),
        })
    return output


def main():
    rank_rows = pathways.read_tsv(class_rank.RANK_TABLE, class_rank.RANK_TABLE_COLUMNS)
    rows = fitting_rows(rank_rows, load_school_percentiles())
    fit = fit_class_spread(rows)
    for row in rows:
        row["national_z"] = national_ability(row["top_10_pct"] / 100, fit["class_sd"])
        row["national_percentile"] = 100 * NORMAL.cdf(row["national_z"])
    print(f"{'school':<38} {'top10':>6} {'rank%':>6} {'taker':>7} {'rank->nat':>10}")
    for row in sorted(rows, key=lambda row: -row["national_z"]):
        reporting = row["rank_reporting_pct"] or "--"
        print(f"{row['school'][:38]:<38} {row['top_10_pct']:>6} {reporting:>6} "
              f"{row['taker_percentile']:>7.2f} {row['national_percentile']:>10.2f}")
    frame = regression(
        [row["taker_z"] for row in rows], [row["national_z"] for row in rows]
    )
    print(f"\nbetween-school variance {BETWEEN_SCHOOL_VARIANCE}; "
          f"fitted class sd {fit['class_sd']:.3f}; "
          f"top-decile probit vs taker z r2 {fit['r2']:.3f}")
    print(f"taker z -> national z: {frame['slope']:.3f}x + {frame['intercept']:.3f} "
          f"(residual sd {frame['residual_sd']:.3f})")


if __name__ == "__main__":
    main()
