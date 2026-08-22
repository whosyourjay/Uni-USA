"""Age-18 ability distributions for graduates of each undergraduate school."""

from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property
from statistics import fmean

from uniusa import ability, calibrate_tests, intake_ability, intake_curve, pathways
from uniusa import test_counts


@dataclass(frozen=True)
class CohortYearDistribution:
    """One entering year's graduate distribution under the current route model."""

    routes: dict
    entrants: int
    submitters: int
    direct_share: float
    transfer_distribution: tuple = ()

    def cdf(self, percentile):
        above = intake_ability.intake_above(
            percentile, self.routes, self.submitters
        )
        survival = self.direct_share * above / self.entrants
        transfer_above = intake_curve.empirical_share_above(
            percentile, self.transfer_distribution
        )
        survival += (1 - self.direct_share) * (transfer_above or 0.0)
        return min(1.0, max(0.0, 1 - survival))


@dataclass(frozen=True)
class SchoolDistribution:
    """A school CDF averaged over the admission years it reports."""

    years: tuple

    def cdf(self, percentile):
        return fmean(year.cdf(percentile) for year in self.years)


@dataclass
class DistributionMixture:
    """Weighted mixture of school CDFs with numerical inverse."""

    components: tuple
    steps: int = 200

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

    @cached_property
    def grid(self):
        """The mixture CDF sampled evenly across the percentile scale."""
        return tuple(
            (step * 100 / self.steps, self.cdf(step * 100 / self.steps))
            for step in range(self.steps + 1)
        )

    def bracket(self, probability):
        """The sampled interval holding a mixture probability."""
        for (low, _), (high, high_cdf) in zip(self.grid, self.grid[1:]):
            if high_cdf >= probability:
                return low, high
        return self.grid[-1][0], 100.0

    def quantile(self, probability, steps=20):
        """Age-18 percentile at a mixture probability, bisected inside its bracket."""
        if not 0 <= probability <= 1:
            raise ValueError("Quantile probability must lie between zero and one")
        low, high = self.bracket(probability)
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


def year_distributions(year, shares, transfer_scores=None):
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
            transfer_distribution=intake_ability.cohort_transfer_distribution(
                (transfer_scores or {}).get(unitid), year
            ),
        )
    return rows


def school_distributions(years=test_counts.YEARS):
    """School ability CDFs keyed by IPEDS institution id."""
    shares = direct_shares()
    transfer_scores = intake_ability.default_transfer_scores()
    grouped = defaultdict(list)
    for year in years:
        for unitid, distribution in year_distributions(
            year, shares, transfer_scores
        ).items():
            grouped[unitid].append(distribution)
    return {
        unitid: SchoolDistribution(tuple(distributions))
        for unitid, distributions in grouped.items()
    }


def distributions_by_name(years=test_counts.YEARS):
    """School ability CDFs keyed by canonical institution name."""
    directory = pathways.load_directory()
    return {
        directory[unitid]["INSTNM"]: distribution
        for unitid, distribution in school_distributions(years).items()
        if unitid in directory
    }
