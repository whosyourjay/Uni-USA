#!/usr/bin/env python3
"""Fuzz checks for dealing the stack-ranked transfer pool to destinations."""

import random
import unittest

from uniusa import transfer


def random_pool(rng):
    return sorted(
        ((round(rng.uniform(10, 100), 3), float(rng.randint(1, 5000)))
         for _ in range(rng.randint(1, 60))),
        reverse=True,
    )


def random_seats(rng):
    return [
        rng.choice([0.0, round(rng.uniform(0.01, 900), 3)])
        for _ in range(rng.randint(1, 80))
    ]


class TransferPoolTests(unittest.TestCase):
    def test_dealing_conserves_the_pool(self):
        """Every transfer lands somewhere, so the seat-weighted mean is the pool mean."""
        rng = random.Random(20260815)
        for _ in range(500):
            pool, seats = random_pool(rng), random_seats(rng)
            if not sum(seats):
                continue
            taken = list(transfer.deal_pool(pool, seats))
            supply = sum(weight for _, weight in pool)
            dealt = sum(
                slice["transfer_score"] * count
                for slice, count in zip(taken, seats) if count
            )
            expected = sum(score * weight for score, weight in pool) / supply
            self.assertAlmostEqual(dealt / sum(seats), expected, 3)

    def test_earlier_destinations_take_the_better_slice(self):
        """Dealing from the top means no school outscores the one served before it."""
        rng = random.Random(4)
        for _ in range(500):
            pool, seats = random_pool(rng), random_seats(rng)
            if not sum(seats):
                continue
            scores = [
                slice["transfer_score"]
                for slice, count in zip(transfer.deal_pool(pool, seats), seats)
                if count
            ]
            for earlier, later in zip(scores, scores[1:]):
                self.assertGreaterEqual(earlier, later - 1e-6)

    def test_a_slice_stays_inside_its_own_range(self):
        """A slice mean cannot sit outside the origin scores it was drawn from."""
        rng = random.Random(9)
        for _ in range(500):
            pool, seats = random_pool(rng), random_seats(rng)
            if not sum(seats):
                continue
            for slice, count in zip(transfer.deal_pool(pool, seats), seats):
                if not count:
                    self.assertEqual(slice["transfer_score"], "")
                    continue
                self.assertLessEqual(slice["pool_bottom"], slice["transfer_score"])
                self.assertLessEqual(slice["transfer_score"], slice["pool_top"])

    def test_distribution_preserves_each_slice_mean(self):
        rng = random.Random(23)
        for _ in range(500):
            pool, seats = random_pool(rng), random_seats(rng)
            if not sum(seats):
                continue
            for slice, count in zip(transfer.deal_pool(pool, seats), seats):
                if not count:
                    self.assertEqual(slice["distribution"], ())
                    continue
                total = sum(weight for _, weight in slice["distribution"])
                mean = sum(
                    score * weight for score, weight in slice["distribution"]
                ) / total
                self.assertAlmostEqual(mean, slice["transfer_score"], places=3)


if __name__ == "__main__":
    unittest.main()
