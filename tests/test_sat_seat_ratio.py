#!/usr/bin/env python3
"""Fuzz the q25 bar to ability-pool ratio against random admissions rows."""

import random
import unittest

from uniusa import calibrate_tests, sat_seat_ratio


class PoolRatioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sat_table = calibrate_tests.load_sat_total_user_percentiles(2019)
        cls.act_counts = sat_seat_ratio.national_act_counts(2019)
        cls.sat_takers = sat_seat_ratio.national_sat_takers(2019)

    def pools(self, admission):
        return sat_seat_ratio.route_pools(
            admission, self.sat_table, self.sat_takers, self.act_counts
        )

    def test_random_bars_stay_bounded_and_monotone(self):
        random.seed(20260814)
        for _ in range(2_000):
            reading = random.randrange(200, 801, 10)
            math = random.randrange(200, 801, 10)
            composite = random.randint(1, 36)
            admission = {
                "SATVR25": str(reading),
                "SATMT25": str(math),
                "ACTCM25": str(composite),
                "SATNUM": str(random.randint(1, 5_000)),
                "ACTNUM": str(random.randint(1, 5_000)),
                "ENRLT": str(random.randint(1, 20_000)),
            }
            pools = self.pools(admission)
            self.assertEqual(set(pools), {"sat", "act"})
            self.assertLessEqual(pools["sat"]["pool"], self.sat_takers)
            self.assertLessEqual(pools["act"]["pool"], sum(self.act_counts.values()))
            for route in pools.values():
                self.assertGreaterEqual(route["pool"], 0)
                self.assertGreater(route["seats"], 0)
            self.assertGreater(sat_seat_ratio.pool_ratio(pools), 0)

            higher = self.pools({
                **admission,
                "SATMT25": str(min(800, math + 100)),
                "ACTCM25": str(min(36, composite + 3)),
            })
            self.assertLessEqual(higher["sat"]["pool"], pools["sat"]["pool"])
            self.assertLessEqual(higher["act"]["pool"], pools["act"]["pool"])

    def test_missing_or_zero_routes_drop_out(self):
        self.assertEqual(self.pools({}), {})
        self.assertEqual(
            self.pools({"SATVR25": "600", "SATMT25": "600", "SATNUM": "0"}), {}
        )
        self.assertIsNone(sat_seat_ratio.pool_ratio({}))
        act_only = self.pools({"ACTCM25": "30", "ACTNUM": "100"})
        self.assertEqual(set(act_only), {"act"})
        self.assertAlmostEqual(act_only["act"]["seats"], 75)

    def test_ratio_is_pool_per_seat(self):
        pools = self.pools({
            "SATVR25": "700", "SATMT25": "750", "SATNUM": "400",
            "ACTCM25": "33", "ACTNUM": "200",
        })
        expected = (pools["sat"]["pool"] + pools["act"]["pool"]) / (
            0.75 * 400 + 0.75 * 200
        )
        self.assertAlmostEqual(sat_seat_ratio.pool_ratio(pools), expected)


class ClaimedSeatTests(unittest.TestCase):
    """Seats at a bar or above must not depend on how ties happen to sort."""

    def pools(self, count, bars):
        return {
            unitid: {
                "act": {
                    "bar": random.choice(bars),
                    "pool": random.uniform(1, 1e6),
                    "seats": random.uniform(0.75, 5_000),
                }
            }
            for unitid in range(count)
        }

    def test_random_bars_accumulate_downward(self):
        random.seed(20260815)
        for _ in range(300):
            pools = self.pools(random.randint(1, 60), range(1, 37))
            claimed = sat_seat_ratio.claimed_seats(pools)["act"]
            total = sum(school["act"]["seats"] for school in pools.values())
            ranked = sorted(pools, key=lambda unitid: -pools[unitid]["act"]["bar"])
            self.assertAlmostEqual(claimed[ranked[-1]], total)
            for higher, lower in zip(ranked, ranked[1:]):
                self.assertLessEqual(claimed[higher], claimed[lower] + 1e-9)
                if pools[higher]["act"]["bar"] == pools[lower]["act"]["bar"]:
                    self.assertAlmostEqual(claimed[higher], claimed[lower])

    def test_ties_share_one_total(self):
        random.seed(20260815)
        pools = self.pools(40, [30])
        claimed = sat_seat_ratio.claimed_seats(pools)["act"]
        self.assertEqual(len(set(claimed.values())), 1)

    def test_ratio_divides_by_seats_at_or_above(self):
        pools = {
            1: {"act": {"bar": 34, "pool": 1_000.0, "seats": 100.0}},
            2: {"act": {"bar": 30, "pool": 8_000.0, "seats": 300.0}},
        }
        claimed = sat_seat_ratio.claimed_seats(pools)
        self.assertAlmostEqual(
            sat_seat_ratio.cumulative_pool_ratio(pools[2], claimed, 2), 8_000 / 400
        )


if __name__ == "__main__":
    unittest.main()
