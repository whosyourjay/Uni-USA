"""Candidate-pool size behind each school's final-enrollee median."""

from itertools import groupby


def ratios(medians, seats, population):
    """Candidates above Q50 per cumulative bachelor seat at Q50 or higher."""
    ranked = sorted(
        (
            (median, unitid, seats.get(unitid, 0.0))
            for unitid, median in medians.items()
            if median != "" and seats.get(unitid, 0.0) > 0
        ),
        reverse=True,
    )
    output, cumulative = {}, 0.0
    for median, tied in groupby(ranked, key=lambda row: row[0]):
        tied = list(tied)
        cumulative += sum(count for _, _, count in tied)
        ratio = population * (1 - median / 100) / cumulative
        for _, unitid, _ in tied:
            output[unitid] = round(ratio, 2)
    return output
