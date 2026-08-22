"""Pure distribution machinery for combining admission-score routes."""

from statistics import NormalDist


NORMAL = NormalDist()
IQR_Z = 2 * NORMAL.inv_cdf(0.75)
QUARTILE_MODEL = "normal"
SOLVE_STEPS = 60


def uniform_share(percentile, low, high):
    """Share at or above a percentile when each quartile spreads evenly."""
    if percentile >= 100:
        return 0.0
    if percentile >= high:
        return 0.25 * (100 - percentile) / (100 - high)
    if percentile >= low:
        return 0.25 + 0.5 * (high - percentile) / (high - low)
    if percentile <= 0:
        return 1.0
    return 0.75 + 0.25 * (low - percentile) / low


def normal_share(percentile, low, high):
    """Share at or above a percentile under a normal pinned to both bars."""
    if not 0 < percentile < 100:
        return 1.0 if percentile <= 0 else 0.0
    low_z, high_z = NORMAL.inv_cdf(low / 100), NORMAL.inv_cdf(high / 100)
    sigma = (high_z - low_z) / IQR_Z
    if sigma <= 0:
        return 0.0
    center = (low_z + high_z) / 2
    return 1 - NORMAL.cdf((NORMAL.inv_cdf(percentile / 100) - center) / sigma)


def route_share(percentile, low, high, model=None):
    if high <= low:
        return None
    if (model or QUARTILE_MODEL) == "normal":
        return normal_share(percentile, low, high)
    return uniform_share(percentile, low, high)


def distinct_submitters(routes, entrants):
    """Entrants sending at least one score, capped by the entering class."""
    sent = sum(route["n"] for route in routes.values())
    return min(sent, entrants) if entrants > 0 else sent


def intake_above(percentile, routes, submitters):
    """Enrolled score-submitters at or above a cohort percentile."""
    weighted, sent = 0.0, 0
    for route in routes.values():
        share = route_share(percentile, route["low"], route["high"])
        if share is None:
            continue
        weighted += route["n"] * share
        sent += route["n"]
    if not sent:
        return None
    return submitters * weighted / sent


def empirical_share_above(percentile, distribution):
    """Weighted share of an empirical distribution at or above a percentile."""
    total = sum(weight for _, weight in distribution)
    if not total:
        return None
    return sum(
        weight for score, weight in distribution if score >= percentile
    ) / total


def graduate_above(
    percentile,
    routes,
    submitters,
    entrants,
    graduates,
    transfers,
    transfer_distribution,
):
    """Final graduates above a common ability bar."""
    if entrants <= 0 or graduates <= 0:
        return None
    freshman = intake_above(percentile, routes, submitters)
    transfer_share = empirical_share_above(percentile, transfer_distribution)
    if freshman is None or (transfers > 0 and transfer_share is None):
        return None
    direct = max(0.0, graduates - transfers)
    return direct * freshman / entrants + transfers * (transfer_share or 0.0)


def solve_percentile(target, routes, submitters):
    """Percentile leaving a target number of score-submitters above it."""
    if intake_above(0.0, routes, submitters) is None or submitters < target:
        return None
    low, high = 0.0, 100.0
    for _ in range(SOLVE_STEPS):
        middle = (low + high) / 2
        if intake_above(middle, routes, submitters) >= target:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def solve_graduate_median(
    routes,
    submitters,
    entrants,
    graduates,
    transfers,
    transfer_distribution,
):
    """Final-enrollee Q50 on the common cohort-percentile scale."""
    target = graduates / 2
    inputs = (
        routes,
        submitters,
        entrants,
        graduates,
        transfers,
        transfer_distribution,
    )
    available = graduate_above(0.0, *inputs)
    if available is None or available < target:
        return None
    low, high = 0.0, 100.0
    for _ in range(SOLVE_STEPS):
        middle = (low + high) / 2
        if graduate_above(middle, *inputs) >= target:
            low = middle
        else:
            high = middle
    return (low + high) / 2
