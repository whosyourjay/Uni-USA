#!/usr/bin/env python3
"""Turn a class-rank distribution into a national ability estimate.

National ability is standard normal. A high school's mean carries variance
`between`, so rank inside a class is driven by the residual `1 - between`.
Writing `shrink = sqrt(1 - between)`, a student at national z sits at
within-school z with mean `shrink * z`, and class rank percentile is the normal
CDF of that. This is why a school can put 99% of its class in the top tenth
without any of them being near the national 99.9th percentile, and why spreading
that 99% evenly across the top decile understates the class badly.

Only the top-decile anchor identifies a school. The top-quarter anchor saturates
at 100% for every selective school, so solving both anchors for a per-school
spread reads a rounding difference as signal. The cut that "top tenth" marks and
the rank spread are fitted across school-years instead, by regressing the
cohort-scale medians from `intake_ability` on the reported share.
"""

import math
from collections import defaultdict
from functools import lru_cache
from statistics import NormalDist, fmean, median

from uniusa import entering_class, intake_ability

NORMAL = NormalDist()
BETWEEN_SCHOOL_VARIANCE = 0.28
OUTLIER_GAP = 15.0
RANK_COLUMNS = ("class_rank_percentile", "class_rank_outlier_years")
MIN_SPREAD = 1e-6


def shrink_factor(between=BETWEEN_SCHOOL_VARIANCE):
    return math.sqrt(1 - between)


def class_spread(within_school_sd, between=BETWEEN_SCHOOL_VARIANCE):
    """National-scale spread of one entering class behind a within-school sd."""
    variance = (within_school_sd**2 - between) / shrink_factor(between) ** 2
    return math.sqrt(variance) if variance > 0 else 0.0


def rank_spread(probit, fit):
    """Within-school rank spread of the class reporting one top-decile share.

    A class that lands few of its students in their schools' top tenth spans a
    wider band of ranks, so the spread widens as the reported share falls.
    """
    return fit["spread_base"] + fit["spread_slope"] * probit


def spread_peak(fit):
    """Probit at which a varying spread turns implied ability back down."""
    if not fit["spread_slope"]:
        return None
    return -fit["spread_base"] / (2 * fit["spread_slope"])


def monotone_probit(probit, fit):
    """Probit held inside the branch where implied ability rises with the share."""
    peak = spread_peak(fit)
    if peak is None:
        return probit
    return max(probit, peak) if fit["spread_slope"] > 0 else min(probit, peak)


def national_ability(top_10, fit):
    """National z implied by the share of a class in its high schools' top tenth."""
    if not 0 < top_10 < 1:
        return None
    probit = monotone_probit(NORMAL.inv_cdf(top_10), fit)
    return (fit["top_decile_cut"] + rank_spread(probit, fit) * probit) / shrink_factor()


def rank_share(national_z, fit):
    """Top-decile share a class centered at `national_z` would report."""
    offset = fit["top_decile_cut"] - shrink_factor() * national_z
    base, slope = fit["spread_base"], fit["spread_slope"]
    if not slope:
        return NORMAL.cdf(-offset / base)
    discriminant = base**2 - 4 * slope * offset
    if discriminant < 0:
        return None
    return NORMAL.cdf((-base + math.sqrt(discriminant)) / (2 * slope))


def solve_normal(normal, size, tolerance=1e-9):
    """Solve the normal equations, resting collinear features at zero.

    Features that repeat a direction the others already span leave no pivot to
    divide by.  Nothing chooses between the coefficients they could share, so
    those stay at zero and the directions the design does determine still fit.
    """
    scale = max((abs(value) for row in normal for value in row[:size]), default=0.0)
    pivots = {}
    row = 0
    for column in range(size):
        candidates = range(row, size)
        best = max(candidates, key=lambda index: abs(normal[index][column]),
                   default=None)
        if best is None or abs(normal[best][column]) <= tolerance * scale:
            continue
        normal[row], normal[best] = normal[best], normal[row]
        for other in range(size):
            if other != row:
                factor = normal[other][column] / normal[row][column]
                for index in range(column, size + 1):
                    normal[other][index] -= factor * normal[row][index]
        pivots[column] = row
        row += 1
    return [
        normal[pivots[column]][size] / normal[pivots[column]][column]
        if column in pivots else 0.0
        for column in range(size)
    ]


def least_squares(designs, targets):
    """Coefficients, residual spread and r2 of an ordinary least-squares fit."""
    size = len(designs[0])
    normal = [
        [sum(row[i] * row[j] for row in designs) for j in range(size)] + [
            sum(row[i] * target for row, target in zip(designs, targets))
        ]
        for i in range(size)
    ]
    coefficients = solve_normal(normal, size)
    residuals = [
        target - sum(c * x for c, x in zip(coefficients, design))
        for design, target in zip(designs, targets)
    ]
    mean = sum(targets) / len(targets)
    total = sum((target - mean) ** 2 for target in targets)
    error = sum(residual**2 for residual in residuals)
    freedom = len(targets) - size
    return {
        "coefficients": coefficients,
        "residual_sd": math.sqrt(error / freedom) if freedom > 0 else 0.0,
        "r2": 1 - error / total if total else 0.0,
    }


def regression(xs, ys):
    """Least-squares slope, intercept and residual spread."""
    fit = least_squares([[1, x] for x in xs], ys)
    intercept, slope = fit["coefficients"]
    return {"slope": slope, "intercept": intercept, **fit}


def constrained_rank_fit(probits, targets):
    """Quadratic rank fit, falling back when its central spread is impossible."""
    quadratic = least_squares(
        [[1, probit, probit**2] for probit in probits], targets
    )
    if quadratic["coefficients"][1] > 0:
        return quadratic
    linear = least_squares([[1, probit] for probit in probits], targets)
    if linear["coefficients"][1] > 0:
        intercept, spread = linear["coefficients"]
        return linear | {"coefficients": [intercept, spread, 0.0]}
    constant = least_squares([[1] for _ in probits], targets)
    return constant | {"coefficients": [constant["coefficients"][0], MIN_SPREAD, 0.0]}


def fit_rank_scale(rows, between=BETWEEN_SCHOOL_VARIANCE):
    """Least-squares map from the top-decile probit onto cohort ability.

    Regressing ability on the reported share, rather than the reverse, leaves
    the estimate unbiased at every share.  The intercept carries the cut that
    "top tenth" actually marks: schools rank generously and only some students
    report a rank, so the fitted cut sits well above the national 90th
    percentile.  The two remaining terms carry a rank spread that widens as the
    reported share falls, which a single spread misses at both ends.
    """
    probits = [NORMAL.inv_cdf(row["top_10_pct"] / 100) for row in rows]
    raw = constrained_rank_fit(probits, [row["cohort_z"] for row in rows])
    shrink = shrink_factor(between)
    cut, base, slope = (value * shrink for value in raw["coefficients"])
    return {
        "top_decile_cut": cut,
        "spread_base": base,
        "spread_slope": slope,
        "class_sd": class_spread(base, between),
        "residual_sd": raw["residual_sd"],
        "r2": raw["r2"],
    }


@lru_cache(maxsize=None)
def cohort_year_percentiles():
    """Cohort-scale graduate medians, keyed by institution and entering year."""
    return intake_ability.year_percentiles()


def cohort_percentiles(percentiles=None):
    """Cohort-scale graduate medians per institution, over the years it reports."""
    collected = defaultdict(list)
    percentiles = cohort_year_percentiles() if percentiles is None else percentiles
    for (unitid, _), percentile in percentiles.items():
        collected[unitid].append(percentile)
    return {unitid: round(fmean(values), 3) for unitid, values in collected.items()}


def usable_share(row):
    """Whether a reported top-decile share identifies the class at all."""
    return row["top_10_pct"] != "" and 0 < row["top_10_pct"] < 100


def fitting_rows(rank_rows, percentiles):
    """School-years carrying both an identifying share and a measured median."""
    output = []
    for row in rank_rows:
        percentile = percentiles.get((row["unitid"], row["entering_year"]))
        if percentile is None or not usable_share(row):
            continue
        output.append({
            "unitid": row["unitid"],
            "school": row["school"],
            "entering_year": row["entering_year"],
            "top_10_pct": row["top_10_pct"],
            "cohort_percentile": percentile,
            "cohort_z": NORMAL.inv_cdf(percentile / 100),
        })
    return output


def implied_percentile(top_10, fit):
    """Cohort percentile the fitted scale reads out of a top-decile share."""
    return 100 * NORMAL.cdf(national_ability(top_10 / 100, fit))


def rank_summary(observations, gap=OUTLIER_GAP):
    """One school's median implied percentile, and the years that stray from it.

    A few published rows are typos rather than classes, so the median carries
    the school and the years it disagrees with are named instead of averaged in.
    """
    center = median(percentile for _, percentile in observations)
    return dict(zip(RANK_COLUMNS, (
        round(center, 3),
        " ".join(
            str(year) for year, percentile in sorted(observations)
            if abs(percentile - center) > gap
        ),
    )))


def rank_percentiles(rank_rows=None, percentiles=None):
    """Cohort percentile implied by each school's top-decile share.

    The scale is fitted on the school-years that pair a reported share with a
    measured median, then applied to every year any school reports.
    """
    if rank_rows is None:
        rank_rows = list(entering_class.rank_lookup().values())
    percentiles = cohort_year_percentiles() if percentiles is None else percentiles
    fit = fit_rank_scale(fitting_rows(rank_rows, percentiles))
    implied = defaultdict(list)
    for row in rank_rows:
        if usable_share(row):
            implied[row["unitid"]].append((
                row["entering_year"], implied_percentile(row["top_10_pct"], fit)
            ))
    return {unitid: rank_summary(rows) for unitid, rows in implied.items()}, fit


def bucket_bias(rows, count=5):
    """Mean rank-implied minus measured percentile, by top-decile bucket."""
    rows = sorted(rows, key=lambda row: row["top_10_pct"])
    size = math.ceil(len(rows) / count)
    for start in range(0, len(rows), size):
        bucket = rows[start:start + size]
        gaps = [row["rank_percentile"] - row["cohort_percentile"] for row in bucket]
        yield {
            "low": bucket[0]["top_10_pct"],
            "high": bucket[-1]["top_10_pct"],
            "n": len(bucket),
            "bias": sum(gaps) / len(gaps),
            "spread": math.sqrt(sum(gap**2 for gap in gaps) / len(gaps)),
        }


def main():
    rank_rows = list(entering_class.rank_lookup().values())
    percentiles = cohort_year_percentiles()
    rows = fitting_rows(rank_rows, percentiles)
    implied, fit = rank_percentiles(rank_rows, percentiles)
    for row in rows:
        row["rank_percentile"] = implied_percentile(row["top_10_pct"], fit)
    years = sorted({row["entering_year"] for row in rows})
    print(f"{len(rank_rows):,} school-years report a class-rank distribution; "
          f"{len(rows):,} across fall {years[0]}-{years[-1]} also carry a "
          f"cohort-scale median")
    print(f"between-school variance {BETWEEN_SCHOOL_VARIANCE}; fitted top-decile "
          f"cut {fit['top_decile_cut']:.3f} (national "
          f"{100 * NORMAL.cdf(fit['top_decile_cut']):.1f}th); rank spread "
          f"{fit['spread_base']:.3f}{fit['spread_slope']:+.3f} per probit; "
          f"r2 {fit['r2']:.3f}")
    frame = regression(
        [row["cohort_z"] for row in rows],
        [NORMAL.inv_cdf(row["rank_percentile"] / 100) for row in rows],
    )
    print(f"cohort z -> rank z: {frame['slope']:.3f}x + {frame['intercept']:.3f} "
          f"(residual sd {frame['residual_sd']:.3f})")
    flagged = [
        unitid for unitid, summary in implied.items()
        if summary["class_rank_outlier_years"]
    ]
    print(f"{len(implied):,} schools scored on the median of their years; "
          f"{len(flagged):,} carry a year more than {OUTLIER_GAP:.0f} points off it")
    print(f"\n{'top 10% bucket':>16} {'n':>5} {'bias':>8} {'rms':>8}")
    for bucket in bucket_bias(rows):
        print(f"{bucket['low']:>7.0f}-{bucket['high']:<8.0f} {bucket['n']:>5} "
              f"{bucket['bias']:>8.2f} {bucket['spread']:>8.2f}")


if __name__ == "__main__":
    main()
