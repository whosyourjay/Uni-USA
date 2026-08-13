#!/usr/bin/env python3
"""Regression checks for the fixed final-graduate source bundle."""

import unittest

import pathways


class GraduatePathwayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.population = pathways.load_population()
        cls.directory = pathways.load_directory()
        cls.completions = pathways.load_completions()
        cls.outcomes = pathways.load_outcomes()
        cls.enrollment = pathways.load_enrollment()
        cls.rows = pathways.graduate_rows(
            cls.directory, cls.completions, cls.outcomes, cls.enrollment
        )

    def test_fixed_source_totals(self):
        self.assertEqual(self.population, 4_357_485)
        self.assertEqual(len(self.completions), 2_445)
        self.assertEqual(
            sum(values["bachelors_all"] for values in self.completions.values()),
            1_985_289,
        )
        self.assertEqual(len(self.rows), 2_356)
        self.assertEqual(sum(row["bachelors_domestic"] for row in self.rows), 1_897_543)

    def test_graduate_routes(self):
        direct = sum(row["direct_bachelors_8yr"] for row in self.rows)
        transfer = sum(row["transfer_bachelors_8yr"] for row in self.rows)
        self.assertEqual(direct, 1_065_088)
        self.assertEqual(transfer, 778_249)
        for row in self.rows:
            share = row["transfer_share_bachelors_8yr"]
            if share != "":
                self.assertGreaterEqual(share, 0)
                self.assertLessEqual(share, 1)

    def test_universe_comes_from_actual_bachelors(self):
        levels = {row["institution_level"] for row in self.rows}
        self.assertIn("two-to-four-year", levels)
        self.assertEqual(
            sum(row["bachelors_domestic"] for row in self.rows
                if row["institution_level"] != "four-or-more-year"),
            1,
        )

    def test_national_bridge(self):
        metrics = {
            row["metric"]: row["value"]
            for row in pathways.national_rows(
                self.population, self.rows, self.completions
            )
        }
        self.assertAlmostEqual(metrics["bachelors_share_age18"], 0.4354674772)
        self.assertAlmostEqual(metrics["om_transfer_share_bachelors"], 0.4221957244)


if __name__ == "__main__":
    unittest.main()
