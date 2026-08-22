"""Fuzz checks for weighted ability-distribution inversion."""

import random
import unittest

from uniusa import school_distributions as model
from uniusa.school_distributions import DistributionMixture


class LinearDistribution:
    def __init__(self, exponent):
        self.exponent = exponent

    def cdf(self, percentile):
        return (percentile / 100) ** self.exponent


class DistributionMixtureFuzzTest(unittest.TestCase):
    def test_quantile_inverts_random_mixtures(self):
        random.seed(20260822)
        for _ in range(100):
            mixture = DistributionMixture(tuple(
                (
                    LinearDistribution(random.uniform(0.25, 4)),
                    random.uniform(1, 1000),
                )
                for _ in range(random.randint(1, 12))
            ))
            probability = random.uniform(0.001, 0.999)
            percentile = mixture.quantile(probability)
            self.assertAlmostEqual(mixture.cdf(percentile), probability, places=6)


class EstimatedSchoolDistributionTest(unittest.TestCase):
    def test_normal_distribution_is_pinned_to_its_median(self):
        rng = random.Random(29)
        for _ in range(1000):
            median = rng.uniform(0.01, 99.99)
            distribution = model.NormalSchoolDistribution(
                median, rng.uniform(0.05, 3.0)
            )
            self.assertAlmostEqual(distribution.cdf(median), 0.5)
            self.assertEqual(distribution.cdf(0), 0)
            self.assertEqual(distribution.cdf(100), 1)

    def test_estimate_prefers_cohort_evidence(self):
        row = {
            "cohort_median": "88",
            "class_rank_percentile": "77",
            "ability": "66",
        }
        self.assertEqual(model.estimated_percentile(row, reach=0.8), 88)
        row["cohort_median"] = ""
        self.assertEqual(model.estimated_percentile(row, reach=0.8), 77)

    def test_taker_percentile_fallback_moves_to_cohort_scale(self):
        row = {"cohort_median": "", "class_rank_percentile": "", "ability": "75"}
        self.assertAlmostEqual(model.estimated_percentile(row, reach=0.8), 80)


if __name__ == "__main__":
    unittest.main()
