#!/usr/bin/env python3
"""Fuzz checks for the graduate-median intake curve."""

import random
import unittest

from uniusa import intake_ability as model


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
        for _ in range(2000):
            graduates, entrants = rng.uniform(1, 9000), rng.uniform(1, 9000)
            self.assertAlmostEqual(
                model.graduate_target(graduates, 0.0, entrants), entrants / 2
            )

    def test_transfers_in_push_the_median_down(self):
        """Weak transfers displace freshmen, so more entrants sit above."""
        rng = random.Random(37)
        for _ in range(2000):
            graduates, entrants = rng.uniform(1, 9000), rng.uniform(1, 9000)
            first, second = sorted(rng.uniform(0, 0.49) * graduates for _ in range(2))
            self.assertLessEqual(
                model.graduate_target(graduates, first, entrants),
                model.graduate_target(graduates, second, entrants) + 1e-9,
            )

    def test_no_target_once_transfers_take_half_the_degrees(self):
        rng = random.Random(41)
        for _ in range(1000):
            graduates, entrants = rng.uniform(1, 9000), rng.uniform(1, 9000)
            transfers = graduates * rng.uniform(0.5, 1.0)
            self.assertIsNone(
                model.graduate_target(graduates, transfers, entrants)
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
