#!/usr/bin/env python3
"""Regression tests for the common-Q50 candidate-pool ratio."""

import random
import unittest

from uniusa import ability_pool


class AbilityPoolTests(unittest.TestCase):
    def test_ratio_uses_q50_tail_and_all_cumulative_seats(self):
        ratios = ability_pool.ratios(
            {1: 99.0, 2: 98.0},
            {1: 100.0, 2: 400.0},
            1_000_000,
        )
        self.assertEqual(ratios[1], 100.0)
        self.assertEqual(ratios[2], 40.0)

    def test_tied_medians_share_one_denominator(self):
        ratios = ability_pool.ratios(
            {1: 99.0, 2: 99.0},
            {1: 100.0, 2: 300.0},
            1_000_000,
        )
        self.assertEqual(ratios, {1: 25.0, 2: 25.0})

    def test_random_ratios_match_the_definition(self):
        rng = random.Random(20260822)
        for _ in range(500):
            count = rng.randint(1, 100)
            medians = {unitid: rng.uniform(1, 99.9) for unitid in range(count)}
            seats = {unitid: rng.uniform(1, 5000) for unitid in range(count)}
            population = rng.uniform(1e5, 1e8)
            ratios = ability_pool.ratios(medians, seats, population)
            for unitid, median in medians.items():
                cumulative = sum(
                    seats[other]
                    for other, other_median in medians.items()
                    if other_median >= median
                )
                expected = population * (1 - median / 100) / cumulative
                self.assertAlmostEqual(ratios[unitid], expected, places=2)


if __name__ == "__main__":
    unittest.main()
