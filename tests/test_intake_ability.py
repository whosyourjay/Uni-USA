#!/usr/bin/env python3
"""Fuzz checks for the graduate-median intake curve."""

import random
import unittest

from uniusa import intake_curve as model


def random_routes(rng, count=None):
    routes = {}
    for name in rng.sample(["sat", "act"], count or rng.choice([1, 2])):
        low = rng.uniform(0.5, 98.0)
        routes[name] = {
            "n": rng.randint(1, 5000),
            "low": low,
            "high": rng.uniform(low + 0.2, 99.9),
        }
    return routes


class QuartileShapeTests(unittest.TestCase):
    def test_shares_hit_the_reported_quartiles(self):
        """Both models must reproduce the bars they were pinned to."""
        rng = random.Random(20260814)
        for _ in range(2000):
            low = rng.uniform(0.5, 98.0)
            high = rng.uniform(low + 0.2, 99.9)
            for shape in (model.uniform_share, model.normal_share):
                self.assertAlmostEqual(shape(low, low, high), 0.75, places=6)
                self.assertAlmostEqual(shape(high, low, high), 0.25, places=6)

    def test_shares_fall_monotonically_within_the_unit_interval(self):
        rng = random.Random(7)
        for _ in range(2000):
            low = rng.uniform(0.5, 98.0)
            high = rng.uniform(low + 0.2, 99.9)
            first, second = sorted(rng.uniform(-5, 105) for _ in range(2))
            for shape in (model.uniform_share, model.normal_share):
                above, below = shape(first, low, high), shape(second, low, high)
                self.assertGreaterEqual(above + 1e-9, below)
                self.assertTrue(0.0 <= below <= above <= 1.0)


class TransferModelTests(unittest.TestCase):
    def test_uniform_leaving_keeps_the_entering_median(self):
        """Without transfers in, the median graduate is the median entrant."""
        rng = random.Random(31)
        for _ in range(1000):
            routes = random_routes(rng)
            entrants = rng.uniform(1, 9000)
            submitters = model.distinct_submitters(routes, entrants)
            self.assertAlmostEqual(
                model.solve_graduate_median(
                    routes, submitters, entrants, entrants, 0.0, ()
                ),
                model.solve_percentile(entrants / 2, routes, submitters),
            )

    def test_transfer_ability_moves_the_final_median(self):
        """The old all-transfers-are-weak shortcut must not survive."""
        rng = random.Random(37)
        for _ in range(500):
            routes = random_routes(rng)
            entrants = graduates = rng.uniform(500, 9000)
            transfers = graduates * rng.uniform(0.1, 0.45)
            submitters = model.distinct_submitters(routes, entrants)
            weak = model.solve_graduate_median(
                routes, submitters, entrants, graduates, transfers, ((1.0, 1.0),)
            )
            strong = model.solve_graduate_median(
                routes, submitters, entrants, graduates, transfers, ((99.9, 1.0),)
            )
            if weak is not None and strong is not None:
                self.assertGreaterEqual(strong + 1e-9, weak)

    def test_transfer_majority_can_identify_the_median(self):
        routes = {"sat": {"n": 100, "low": 70.0, "high": 90.0}}
        median = model.solve_graduate_median(
            routes, 100, 100, 100, 70, ((80.0, 1.0),)
        )
        self.assertAlmostEqual(median, 80.0)

    def test_missing_transfer_distribution_is_not_silently_weakened(self):
        routes = {"sat": {"n": 100, "low": 70.0, "high": 90.0}}
        self.assertIsNone(
            model.solve_graduate_median(routes, 100, 100, 100, 20, ())
        )


class IntakeCurveTests(unittest.TestCase):
    def test_solved_median_leaves_the_target_above_it(self):
        """Whatever the solver returns must satisfy the equation it solved."""
        rng = random.Random(11)
        for _ in range(1000):
            routes = random_routes(rng)
            submitters = rng.randint(1, 8000)
            target = submitters * rng.uniform(0.01, 0.99)
            solved = model.solve_percentile(target, routes, submitters)
            self.assertIsNotNone(solved)
            self.assertAlmostEqual(
                model.intake_above(solved, routes, submitters), target, places=3
            )

    def test_no_median_when_the_class_is_too_small(self):
        """A target above the whole submitting group has no solution."""
        rng = random.Random(13)
        for _ in range(500):
            routes = random_routes(rng)
            submitters = rng.randint(1, 8000)
            target = submitters * rng.uniform(1.01, 4.0)
            self.assertIsNone(model.solve_percentile(target, routes, submitters))

    def test_overlap_cancels_out_of_a_single_route(self):
        """One route's curve must not depend on how many students it counts."""
        rng = random.Random(17)
        for _ in range(500):
            routes = random_routes(rng, count=1)
            name = next(iter(routes))
            submitters = rng.randint(1, 8000)
            percentile = rng.uniform(0, 100)
            first = model.intake_above(percentile, routes, submitters)
            routes[name]["n"] *= rng.randint(2, 9)
            self.assertAlmostEqual(
                first, model.intake_above(percentile, routes, submitters), places=9
            )


if __name__ == "__main__":
    unittest.main()
