"""Age-18 ability distributions for graduates of each undergraduate school."""

from collections import defaultdict
from dataclasses import dataclass
from statistics import fmean

from uniusa import ability, calibrate_tests, intake_ability, pathways
from uniusa import sat_seat_ratio


@dataclass(frozen=True)
class CohortYearDistribution:
    """One entering year's graduate distribution under the current route model."""

    routes: dict
    entrants: int
    submitters: int
    direct_share: float

    def cdf(self, percentile):
        above = intake_ability.intake_above(
            percentile, self.routes, self.submitters
        )
        survival = self.direct_share * above / self.entrants
        return min(1.0, max(0.0, 1 - survival))


@dataclass(frozen=True)
class SchoolDistribution:
    """A school CDF averaged over the admission years it reports."""

    years: tuple

    def cdf(self, percentile):
        return fmean(year.cdf(percentile) for year in self.years)


@dataclass(frozen=True)
class DistributionMixture:
    """Weighted mixture of school CDFs with numerical inverse."""

    components: tuple

    @property
    def weight(self):
        return sum(weight for _, weight in self.components)

    def cdf(self, percentile):
        if not self.components:
            raise ValueError("Ability mixture has no school distributions")
        return sum(
            distribution.cdf(percentile) * weight
            for distribution, weight in self.components
        ) / self.weight

    def quantile(self, probability, steps=24):
        """Age-18 percentile at a mixture probability, by bisection."""
        if not 0 <= probability <= 1:
            raise ValueError("Quantile probability must lie between zero and one")
        if probability <= self.cdf(0.0):
            return 0.0
        low, high = 0.0, 100.0
        for _ in range(steps):
            middle = (low + high) / 2
            if self.cdf(middle) < probability:
                low = middle
            else:
                high = middle
        return (low + high) / 2


def direct_shares(path=pathways.ROOT / "schools.tsv"):
    """Non-transfer graduate shares keyed by IPEDS institution id."""
    unitids = {
        row["INSTNM"]: unitid for unitid, row in pathways.load_directory().items()
    }
    shares = {}
    for row in pathways.read_tsv(path):
        unitid = unitids.get(row["school"])
        if unitid is None or row.get("transfer_share", "") == "":
            continue
        shares[unitid] = min(
            1.0, max(0.0, 1 - float(row["transfer_share"]))
        )
    return shares


def year_distributions(year, shares):
    """Usable school distributions for one admission year."""
    sat_table = calibrate_tests.load_sat_total_user_percentiles(year)
    act_counts, _ = calibrate_tests.load_act_composite_percentiles(
        calibrate_tests.nearest_act_year(year)
    )
    rows = {}
    for unitid, admission in ability.load_admissions(year).items():
        if unitid not in shares:
            continue
        routes = intake_ability.school_routes(
            admission, year, sat_table, act_counts
        )
        entrants = pathways.number(admission.get("ENRLT"))
        if not routes or entrants <= 0:
            continue
        rows[unitid] = CohortYearDistribution(
            routes=routes,
            entrants=entrants,
            submitters=intake_ability.distinct_submitters(routes, entrants),
            direct_share=shares[unitid],
        )
    return rows


def school_distributions(years=sat_seat_ratio.YEARS):
    """School ability CDFs keyed by IPEDS institution id."""
    shares = direct_shares()
    grouped = defaultdict(list)
    for year in years:
        for unitid, distribution in year_distributions(year, shares).items():
            grouped[unitid].append(distribution)
    return {
        unitid: SchoolDistribution(tuple(distributions))
        for unitid, distributions in grouped.items()
    }


def distributions_by_name(years=sat_seat_ratio.YEARS):
    """School ability CDFs keyed by canonical institution name."""
    directory = pathways.load_directory()
    return {
        directory[unitid]["INSTNM"]: distribution
        for unitid, distribution in school_distributions(years).items()
        if unitid in directory
    }
