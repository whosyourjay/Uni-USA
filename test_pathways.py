#!/usr/bin/env python3
"""Regression checks for the fixed 2023 pathway source bundle."""

import unittest

import pathways


class PathwayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.population = pathways.load_population()
        cls.directory = pathways.load_directory()
        cls.admissions = pathways.load_admissions()
        cls.enrollment = pathways.load_enrollment()
        cls.rows = pathways.institution_rows(
            cls.directory, cls.admissions, cls.enrollment
        )

    def test_fixed_source_totals(self):
        self.assertEqual(self.population, 4_357_485)
        first = [
            pathways.level_counts(self.enrollment, unitid, 4)
            for unitid in self.directory
        ]
        transfer = [
            pathways.level_counts(self.enrollment, unitid, 19)
            for unitid in self.directory
        ]
        self.assertEqual(sum(pair[0] for pair in first), 2_353_982)
        self.assertEqual(sum(r["first_time_domestic"] for r in self.rows), 2_262_366)
        self.assertEqual(sum(pair[0] for pair in transfer), 1_615_553)
        self.assertEqual(sum(r["transfer_domestic"] for r in self.rows), 1_574_419)

    def test_routes_partition_new_arrivals(self):
        for row in self.rows:
            share = row["transfer_share_new_domestic"]
            self.assertGreaterEqual(share, 0)
            self.assertLessEqual(share, 1)

    def test_selectivity_bands_cover_rows(self):
        bands = pathways.band_rows(self.rows, self.population)
        self.assertEqual(sum(row["institutions"] for row in bands), len(self.rows))
        self.assertEqual(sum(row["first_time_domestic"] for row in bands), 2_262_366)
        self.assertEqual(sum(row["transfer_domestic"] for row in bands), 1_574_419)


if __name__ == "__main__":
    unittest.main()
