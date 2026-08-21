"""Fuzz checks for weighted ability-distribution inversion."""

import random
import unittest

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


if __name__ == "__main__":
    unittest.main()
