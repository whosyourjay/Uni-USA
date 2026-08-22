import random
import unittest
from math import exp

from uniusa.professional import common as professional


def planted_rows(rng, gradient, count):
    """Schools whose application rate follows `gradient` exactly."""
    rows = []
    for _ in range(count):
        ability = rng.uniform(1.0, 99.0)
        bachelors = rng.uniform(50.0, 20_000.0)
        rate = exp(-4.0 + gradient * (ability - professional.MIDDLE_ABILITY))
        rows.append({
            "ability": ability,
            "bachelors": bachelors,
            "applicants": rate * bachelors,
        })
    return rows


class TestApplicationGradient(unittest.TestCase):
    def test_recovers_the_slope_it_was_generated_from(self):
        """A rate built from one slope must fit back to that slope."""
        for seed in range(300):
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                gradient = rng.uniform(-0.1, 0.1)
                rows = planted_rows(rng, gradient, rng.randint(3, 40))
                self.assertAlmostEqual(
                    professional.application_gradient(rows), gradient, places=6
                )

    def test_ignores_schools_with_nothing_to_measure(self):
        """Rows missing ability, graduates, or applicants carry no weight."""
        for seed in range(300):
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                gradient = rng.uniform(-0.1, 0.1)
                rows = planted_rows(rng, gradient, rng.randint(3, 20))
                blanks = [
                    {"ability": "", "bachelors": 100.0, "applicants": 10.0},
                    {"ability": 50.0, "bachelors": 0.0, "applicants": 10.0},
                    {"ability": 50.0, "bachelors": 100.0, "applicants": 0},
                ]
                rng.shuffle(blanks)
                self.assertAlmostEqual(
                    professional.application_gradient(rows + blanks),
                    gradient,
                    places=6,
                )


class TestApplicantOrigins(unittest.TestCase):
    def test_shares_sum_to_the_total_and_climb_with_ability(self):
        """The split conserves the pool and never favours the weaker school."""
        for seed in range(300):
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                gradient = rng.uniform(0.0, 0.2)
                total = rng.uniform(1.0, 1e6)
                rows = [
                    {"ability": rng.uniform(1.0, 99.0),
                     "bachelors": rng.uniform(50.0, 20_000.0)}
                    for _ in range(rng.randint(2, 30))
                ]
                split = professional.applicant_origins(rows, gradient, total)
                self.assertAlmostEqual(
                    sum(row["applicants"] for row in split) / total, 1.0, places=9
                )
                rates = sorted(
                    (row["ability"], row["applicants"] / row["bachelors"])
                    for row in split
                )
                for (_, lower), (_, higher) in zip(rates, rates[1:]):
                    self.assertLessEqual(lower, higher + 1e-12)

    def test_the_total_only_scales_the_split(self):
        """Doubling the pool doubles every school and reorders nothing."""
        for seed in range(300):
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                gradient = rng.uniform(-0.2, 0.2)
                rows = [
                    {"ability": rng.uniform(1.0, 99.0),
                     "bachelors": rng.uniform(50.0, 20_000.0)}
                    for _ in range(rng.randint(2, 30))
                ]
                factor = rng.uniform(1.0, 1e5)
                one = professional.applicant_origins(rows, gradient)
                many = professional.applicant_origins(rows, gradient, factor)
                for single, scaled in zip(one, many):
                    self.assertAlmostEqual(
                        scaled["applicants"] / factor, single["applicants"], places=9
                    )


class TestInterpolatePoints(unittest.TestCase):
    def test_passes_through_its_points_and_flattens_outside_them(self):
        """Interpolation reproduces every knot and never extrapolates past one."""
        for seed in range(300):
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                xs = rng.sample(range(-500, 500), rng.randint(2, 25))
                points = [(float(x), rng.uniform(-50.0, 50.0)) for x in sorted(xs)]
                for x, y in points:
                    self.assertAlmostEqual(
                        professional.interpolate_points(points, x), y, places=9
                    )
                low, high = points[0], points[-1]
                self.assertEqual(
                    professional.interpolate_points(points, low[0] - 1e6), low[1]
                )
                self.assertEqual(
                    professional.interpolate_points(points, high[0] + 1e6), high[1]
                )

    def test_stays_between_the_points_it_sits_between(self):
        """Between two knots the value never leaves their range."""
        for seed in range(300):
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                xs = sorted(rng.sample(range(-500, 500), rng.randint(2, 25)))
                points = [(float(x), rng.uniform(-50.0, 50.0)) for x in xs]
                for (low_x, low_y), (high_x, high_y) in zip(points, points[1:]):
                    x = rng.uniform(low_x, high_x)
                    value = professional.interpolate_points(points, x)
                    self.assertGreaterEqual(value, min(low_y, high_y) - 1e-9)
                    self.assertLessEqual(value, max(low_y, high_y) + 1e-9)


if __name__ == "__main__":
    unittest.main()
