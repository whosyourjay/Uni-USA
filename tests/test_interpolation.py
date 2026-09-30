"""Compare all score adapters with exact rational interpolation."""

from fractions import Fraction
import random
import unittest

from uniusa import calibrate_tests
from uniusa.professional import common


def rational_value(points, value):
    """Independent two-endpoint weighted mean, with held boundaries."""
    if value <= points[0][0]:
        return points[0][1]
    if value >= points[-1][0]:
        return points[-1][1]
    left, right = next((a, b) for a, b in zip(points, points[1:])
                       if a[0] <= value <= b[0])
    x, lx, ly, rx, ry = map(Fraction, (value, *left, *right))
    return float(((rx - x) * ly + (x - lx) * ry) / (rx - lx))


class InterpolationTests(unittest.TestCase):
    def test_random_tables_match_exact_interpolation(self):
        rng = random.Random(3701)
        for case in range(250):
            xs = sorted(rng.sample(range(-1000, 2000), rng.randint(1, 40)))
            points = [(x, rng.uniform(-100, 100)) for x in xs]
            shuffled = rng.sample(points, len(points))
            table = dict(shuffled)
            probes = [*xs, xs[0] - 10, xs[-1] + 10]
            probes.extend(rng.uniform(xs[0], xs[-1]) for _ in range(20))
            for value in probes:
                with self.subTest(case=case, value=value):
                    expected = rational_value(points, value)
                    results = (
                        calibrate_tests.interpolate(table, value),
                        common.interpolate(table, value),
                        common.interpolate_points(iter(shuffled), value),
                    )
                    for result in results:
                        self.assertAlmostEqual(result, expected, places=10)

    def test_empty_tables_and_nan_never_become_percentiles(self):
        for interpolate in (calibrate_tests.interpolate, common.interpolate):
            with self.subTest(adapter=interpolate.__module__):
                with self.assertRaises(ValueError):
                    interpolate({}, 10)
                with self.assertRaises(ValueError):
                    interpolate({0: 0, 100: 100}, float("nan"))
        with self.assertRaises(ValueError):
            common.interpolate_points(iter(()), 10)
        with self.assertRaises(ValueError):
            common.interpolate_points([(0, 0), (100, 100)], float("nan"))


if __name__ == "__main__":
    unittest.main()
