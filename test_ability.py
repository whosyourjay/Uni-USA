#!/usr/bin/env python3
"""Regression checks for 2023 direct ability evidence."""

import unittest

import ability
import pathways


class AbilityEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        graduates = pathways.graduate_rows(
            pathways.load_directory(),
            pathways.load_completions(),
            pathways.load_outcomes(),
            pathways.load_enrollment(),
        )
        cls.rows = ability.ability_evidence_rows(
            graduates, ability.load_admissions()
        )

    def row(self, name):
        return next(row for row in self.rows if row["institution"] == name)

    def test_current_score_coverage(self):
        coverage = ability.evidence_coverage(self.rows)
        self.assertEqual(len(self.rows), 2_356)
        self.assertEqual(coverage["institutions"], 1_059)
        self.assertEqual(coverage["bachelors_domestic"], 1_285_958)
        self.assertEqual(coverage["direct_bachelors_8yr"], 822_070)

    def test_harvard_score_evidence(self):
        row = self.row("Harvard University")
        self.assertEqual(row["test_evidence_2023"], "SAT and ACT")
        self.assertEqual(row["sat_total_median_2023"], 1_550)
        self.assertEqual(row["act_composite_median_2023"], 35)
        self.assertEqual(row["test_coverage_lower_2023"], 0.52)
        self.assertEqual(row["test_coverage_upper_2023"], 0.74)

    def test_transfer_dominant_test_missing_example(self):
        row = self.row("University of California-Berkeley")
        self.assertEqual(row["test_evidence_2023"], "none")
        self.assertEqual(row["sat_total_median_2023"], "")
        self.assertGreater(row["transfer_share_bachelors_8yr"], 0.25)

    def test_test_coverage_bounds(self):
        for row in self.rows:
            lower = row["test_coverage_lower_2023"]
            upper = row["test_coverage_upper_2023"]
            if lower != "":
                self.assertGreaterEqual(lower, 0)
                self.assertLessEqual(lower, upper)
                self.assertLessEqual(upper, 1)

    def test_routes_are_not_test_subsets(self):
        routes = ability.freshman_route_rows(self.rows)
        self.assertEqual(
            {row["route"] for row in routes},
            {"SAT", "ACT", "No reported SAT/ACT"},
        )
        harvard = [row for row in routes if row["institution"] == "Harvard University"]
        self.assertEqual([row["route"] for row in harvard],
                         ["SAT", "ACT", "No reported SAT/ACT"])
        self.assertEqual(harvard[0]["score_q50_2023"], 1_550)
        self.assertEqual(harvard[1]["score_q50_2023"], 35)
        self.assertEqual(harvard[2]["route_count_lower_2023"], 427)
        self.assertEqual(harvard[2]["route_count_upper_2023"], 783)

    def test_national_route_counts_keep_overlap_visible(self):
        routes = {row["route"]: row for row in ability.national_route_rows(self.rows)}
        self.assertEqual(routes["SAT"]["people_lower"], 369_411)
        self.assertEqual(routes["ACT"]["people_lower"], 316_572)
        self.assertEqual(routes["No reported SAT/ACT"]["people_lower"], 989_991)
        self.assertEqual(routes["No reported SAT/ACT"]["people_upper"], 1_130_419)
        self.assertTrue(all(row["additive"].startswith("no:") for row in routes.values()))

    def test_admission_considerations(self):
        graduates = pathways.graduate_rows(
            pathways.load_directory(),
            pathways.load_completions(),
            pathways.load_outcomes(),
            pathways.load_enrollment(),
        )
        rows = ability.consideration_rows(graduates, ability.load_admissions())
        by_basis = {row["basis"]: row for row in rows}
        self.assertEqual(len(rows), 12)
        self.assertEqual(by_basis["Secondary-school GPA"]["required_enrolled"],
                         1_462_637)
        self.assertEqual(by_basis["Admission tests"]["required_enrolled"], 138_656)
        self.assertEqual(by_basis["Legacy status"]["required_enrolled"], 0)


if __name__ == "__main__":
    unittest.main()
