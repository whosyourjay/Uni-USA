#!/usr/bin/env python3
"""Fuzz and regression checks for the class-rank ability model."""

import random
import unittest

import rank_ability as model


def random_fit(rng):
    return {
        "top_decile_cut": rng.uniform(0.5, 1.8),
        "spread_base": rng.uniform(0.3, 1.5),
        "spread_slope": rng.uniform(-0.4, 0.4),
    }


def linear_rows(rng, intercept, slope, noise, count):
    """Schools whose cohort ability really is linear in the top-decile probit."""
    rows = []
    for _ in range(count):
        share = rng.uniform(5.0, 99.0)
        probit = model.NORMAL.inv_cdf(share / 100)
        rows.append({
            "top_10_pct": share,
            "cohort_z": intercept + slope * probit + rng.gauss(0, noise),
        })
    return rows


class RankAbilityTests(unittest.TestCase):
    def test_top_decile_round_trip(self):
        """Share -> ability -> share must return the same share.

        Shares past the peak of a varying spread are held back to it, and no
        longer identify a class, so they round trip to the peak instead.
        """
        rng = random.Random(20260814)
        for _ in range(2000):
            fit = random_fit(rng)
            share = rng.uniform(0.01, 0.99)
            probit = model.NORMAL.inv_cdf(share)
            if model.monotone_probit(probit, fit) != probit:
                continue
            back = model.rank_share(model.national_ability(share, fit), fit)
            self.assertAlmostEqual(share, back, 5)

    def test_ability_rises_with_top_decile_share(self):
        """A larger top-decile share can never imply a weaker class."""
        rng = random.Random(7)
        for _ in range(2000):
            fit = random_fit(rng)
            low, high = sorted(rng.uniform(0.01, 0.999) for _ in range(2))
            self.assertLessEqual(
                model.national_ability(low, fit),
                model.national_ability(high, fit),
            )

    def test_saturated_share_does_not_reach_the_model(self):
        """Solving both anchors read 100% top-quarter rounding as real spread."""
        rng = random.Random(3)
        for _ in range(2000):
            share = rng.choice([0.0, 1.0, rng.uniform(-2, 0), rng.uniform(1, 3)])
            self.assertIsNone(model.national_ability(share, random_fit(rng)))

    def test_fitted_spread_is_real(self):
        """A degenerate fit must not hand back a complex or negative spread."""
        rng = random.Random(11)
        for _ in range(200):
            rows = linear_rows(rng, rng.uniform(0, 2), rng.uniform(0.1, 1.2), 0.4, 12)
            fit = model.fit_rank_scale(rows)
            self.assertGreaterEqual(fit["class_sd"], 0.0)
            self.assertGreater(fit["spread_base"], 0.0)

    def test_fit_is_unbiased_across_the_share_range(self):
        """Regressing the share on ability left every bucket biased upward.

        The tolerance is loose because reading the bias off percentiles rather
        than z adds a curvature term; the bug this guards against ran to +6.
        """
        rng = random.Random(5)
        for _ in range(20):
            intercept, slope = rng.uniform(0, 2), rng.uniform(0.3, 1.2)
            rows = linear_rows(rng, intercept, slope, 0.4, 4000)
            fit = model.fit_rank_scale(rows)
            for row in rows:
                row["rank_percentile"] = 100 * model.NORMAL.cdf(
                    model.national_ability(row["top_10_pct"] / 100, fit)
                )
                row["cohort_percentile"] = 100 * model.NORMAL.cdf(row["cohort_z"])
            for bucket in model.bucket_bias(rows):
                self.assertLess(abs(bucket["bias"]), 3.0)


if __name__ == "__main__":
    unittest.main()
