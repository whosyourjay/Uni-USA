"""The country exports test-taker ability; comparison supplies the cohort."""

import random
import unittest

from uniusa import scales


class ScaleTest(unittest.TestCase):
    def test_the_two_linear_transforms_are_inverses_above_the_nontaker_floor(self):
        rng = random.Random(20260823)
        for _ in range(500):
            share = rng.uniform(0.4, 1.0)
            taker = rng.uniform(0.0, 100.0)
            cohort = scales.cohort_percentile(taker, share)
            self.assertAlmostEqual(scales.test_taker_percentile(cohort, share), taker)

    def test_everyone_below_the_test_pool_maps_to_its_floor(self):
        self.assertEqual(scales.test_taker_percentile(10.0, 0.75), 0.0)


if __name__ == "__main__":
    unittest.main()
