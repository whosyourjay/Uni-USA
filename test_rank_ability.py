#!/usr/bin/env python3
"""Fuzz and regression checks for the class-rank ability model."""

import random
import unittest

import rank_ability as model


class RankAbilityTests(unittest.TestCase):
    def test_top_decile_round_trip(self):
        """Ability -> top-decile share -> ability must return the same z."""
        random.seed(20260814)
        for _ in range(2000):
            national_z = random.uniform(-3.0, 3.5)
            class_sd = random.uniform(0.0, 1.5)
            between = random.uniform(0.05, 0.6)
            share = model.predicted_top_decile(national_z, class_sd, between)
            if not 0 < share < 1:
                continue
            recovered = model.national_ability(share, class_sd, between)
            self.assertAlmostEqual(national_z, recovered, places=6)

    def test_ability_rises_with_top_decile_share(self):
        """A larger top-decile share can never imply a weaker class."""
        random.seed(7)
        for _ in range(2000):
            class_sd = random.uniform(0.0, 1.5)
            low, high = sorted(random.uniform(0.01, 0.999) for _ in range(2))
            if low == high:
                continue
            self.assertLessEqual(
                model.national_ability(low, class_sd),
                model.national_ability(high, class_sd),
            )

    def test_saturated_anchor_does_not_reach_the_model(self):
        """Solving both anchors read 100% top-quarter rounding as real spread."""
        self.assertIsNone(model.national_ability(1.0, 0.3))
        self.assertIsNone(model.national_ability(0.0, 0.3))

    def test_fitted_spread_is_real(self):
        """A degenerate fit must not hand back a complex or negative spread."""
        random.seed(11)
        rows = [
            {"top_10_pct": random.uniform(50, 99), "taker_z": random.uniform(1.5, 2.6)}
            for _ in range(12)
        ]
        spread = model.fit_class_spread(rows)
        self.assertGreaterEqual(spread["class_sd"], 0.0)
        self.assertGreater(spread["within_school_sd"], 0.0)


if __name__ == "__main__":
    unittest.main()
