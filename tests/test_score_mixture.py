"""The shared interval solver must preserve reconstructed US score mixtures."""

import random
import unittest

from uniusa import ability, calibrate_tests


def bisection_median(rows):
    """Independent reference: the previous US quartile-CDF calculation."""
    total = sum(row["submitters_2019"] for row in rows)
    lower = min(row["score_scale_min"] for row in rows)
    upper = max(row["score_scale_max"] for row in rows)
    for _ in range(80):
        middle = (lower + upper) / 2
        mass = 0
        for row in rows:
            anchors = [row[key] for key in (
                "score_scale_min", "score_q25_2019", "score_q75_2019", "score_scale_max")]
            for lo, hi, share in zip(anchors, anchors[1:], (.25, .5, .25)):
                cdf = float(middle >= hi) if lo == hi else max(0, min(1, (middle - lo) / (hi - lo)))
                mass += row["submitters_2019"] * share * cdf
        if mass < total / 2:
            lower = middle
        else:
            upper = middle
    return (lower + upper) / 2


class ScoreMixtureTests(unittest.TestCase):
    def test_random_mixtures_match_the_previous_cdf_inversion(self):
        rng = random.Random(21703)
        keys = ("score_scale_min", "score_q25_2019", "score_q75_2019", "score_scale_max")
        for _ in range(250):
            rows = []
            for _ in range(rng.randrange(1, 16)):
                row = dict(zip(keys, sorted(rng.randrange(37) for _ in keys)))
                row["submitters_2019"] = rng.randrange(1, 5000)
                rows.append(row)
            self.assertAlmostEqual(calibrate_tests.mixture_median(rows), bisection_median(rows), places=10)

    def test_tied_quartiles_retain_their_point_mass(self):
        self.assertEqual(ability.interquartile_intervals(1, 30, 30, 36),
                         ((1, 30, .25), (30, 30, .5), (30, 36, .25)))
        self.assertEqual(ability.interquartile_cdf(30, 1, 30, 30, 36), .75)
        self.assertEqual(ability.interquartile_cdf(36, 1, 30, 30, 36), 1)
        with self.assertRaisesRegex(ValueError, "Non-monotone"):
            ability.interquartile_intervals(1, 30, 29, 36)

    def test_empty_mixture_still_fails(self):
        with self.assertRaisesRegex(ValueError, "no submitters"):
            calibrate_tests.mixture_median([])


if __name__ == "__main__":
    unittest.main()
