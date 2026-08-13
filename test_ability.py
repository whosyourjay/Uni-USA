"""Regression checks for the fall-2019 freshman ability evidence."""

import unittest

import ability
import pathways
import special_routes


class AbilityEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graduates = pathways.graduate_rows(
            pathways.load_directory(),
            pathways.load_completions(),
            pathways.load_outcomes(),
            pathways.load_enrollment(),
        )
        cls.admissions = ability.load_admissions()
        cls.rows = ability.ability_evidence_rows(cls.graduates, cls.admissions)

    def row(self, name):
        return next(row for row in self.rows if row["institution"] == name)

    def test_pre_covid_score_coverage(self):
        coverage = ability.evidence_coverage(self.rows)
        self.assertEqual(len(self.rows), 2_356)
        self.assertEqual(coverage["institutions"], 1_224)
        self.assertEqual(coverage["bachelors_domestic"], 1_499_079)
        self.assertEqual(coverage["direct_bachelors_8yr"], 929_866)

    def test_harvard_score_evidence(self):
        row = self.row("Harvard University")
        self.assertEqual(row["test_evidence_2019"], "SAT and ACT")
        self.assertEqual(row["test_policy_2019"], "required")
        self.assertEqual((row["satvr25_2019"], row["satvr75_2019"]),
                         (710, 770))
        self.assertEqual((row["satmt25_2019"], row["satmt75_2019"]),
                         (750, 800))
        self.assertEqual((row["actcm25_2019"], row["actcm75_2019"]),
                         (33, 35))
        self.assertEqual(row["test_coverage_lower_2019"], 0.71)
        self.assertEqual(row["test_coverage_upper_2019"], 1)

    def test_pre_covid_uc_has_test_evidence(self):
        row = self.row("University of California-Berkeley")
        self.assertEqual(row["test_policy_2019"], "required")
        self.assertEqual(row["test_evidence_2019"], "SAT and ACT")
        self.assertGreater(row["transfer_share_bachelors_8yr"], 0.25)

    def test_test_coverage_bounds(self):
        for row in self.rows:
            lower = row["test_coverage_lower_2019"]
            upper = row["test_coverage_upper_2019"]
            if lower != "":
                self.assertGreaterEqual(lower, 0)
                self.assertLessEqual(lower, upper)
                self.assertLessEqual(upper, 1)

    def test_sat_and_act_are_the_only_test_route_rows(self):
        routes = ability.freshman_test_route_rows(self.rows)
        self.assertEqual({row["route"] for row in routes}, {"SAT", "ACT"})
        harvard = [row for row in routes if row["institution"] == "Harvard University"]
        self.assertEqual([row["route"] for row in harvard], ["SAT", "ACT"])
        self.assertEqual(harvard[0]["submitters_2019"], 1_172)
        self.assertEqual(harvard[1]["submitters_2019"], 743)
        self.assertEqual(harvard[0]["sat_reading_writing_q25_2019"], 710)
        self.assertEqual(harvard[0]["act_composite_q25_2019"], "")
        self.assertEqual(harvard[1]["sat_reading_writing_q25_2019"], "")
        self.assertEqual(harvard[1]["act_composite_q25_2019"], 33)

    def test_national_test_counts_are_nonexclusive(self):
        paths = ability.admission_path_rows(
            self.graduates,
            self.admissions,
            ability.load_characteristics(),
            ability.load_fall_enrollment(),
        )
        total = sum(row["fall_first_time_entrants_2019"] for row in paths)
        routes = {
            row["route"]: row
            for row in ability.national_test_route_rows(self.rows, total)
        }
        self.assertEqual(set(routes), {"SAT", "ACT"})
        self.assertEqual(routes["SAT"]["submitters_2019"], 846_219)
        self.assertEqual(routes["ACT"]["submitters_2019"], 673_606)
        self.assertTrue(all(row["additive"].startswith("no:") for row in routes.values()))

    def test_additive_admission_paths(self):
        rows = ability.admission_path_rows(
            self.graduates,
            self.admissions,
            ability.load_characteristics(),
            ability.load_fall_enrollment(),
        )
        by_path = {row["path"]: row for row in rows}
        self.assertEqual(sum(row["fall_first_time_entrants_2019"] for row in rows),
                         1_944_624)
        self.assertEqual(
            by_path["Selective: admission test required"]
            ["fall_first_time_entrants_2019"],
            1_291_303,
        )
        self.assertEqual(by_path["Open admission"]["fall_first_time_entrants_2019"],
                         339_523)
        self.assertEqual(
            by_path["IPEDS reporting reconciliation"]
            ["fall_first_time_entrants_2019"],
            317,
        )

    def test_admission_considerations(self):
        rows = ability.consideration_rows(self.graduates, self.admissions)
        by_basis = {row["basis"]: row for row in rows}
        self.assertEqual(len(rows), 9)
        self.assertEqual(by_basis["Secondary-school GPA"]["required_enrolled"],
                         1_388_305)
        self.assertEqual(by_basis["Admission tests"]["required_enrolled"],
                         1_291_303)

    def test_interquartile_distribution(self):
        self.assertEqual(ability.interquartile_cdf(200, 200, 400, 600, 800), 0)
        self.assertEqual(ability.interquartile_cdf(400, 200, 400, 600, 800), 0.25)
        self.assertEqual(ability.interquartile_cdf(500, 200, 400, 600, 800), 0.50)
        self.assertEqual(ability.interquartile_cdf(600, 200, 400, 600, 800), 0.75)
        self.assertEqual(ability.interquartile_cdf(800, 200, 400, 600, 800), 1)

    def test_test_component_distributions(self):
        rows = ability.test_component_rows(self.rows)
        coverage = ability.test_route_coverage(rows)
        self.assertGreater(coverage["SAT"]["institutions"], 1_000)
        self.assertGreater(coverage["ACT"]["institutions"], 900)
        harvard_sat = [
            row for row in rows
            if row["institution"] == "Harvard University" and row["route"] == "SAT"
        ]
        self.assertEqual({row["component"] for row in harvard_sat},
                         {"reading and writing", "math"})

    def test_special_route_benchmarks_keep_denominators(self):
        rows = special_routes.benchmark_rows(
            self.graduates,
            self.admissions,
            ability.load_fall_enrollment(),
        )
        academies = next(
            row for row in rows if row["route"] == "Service-academy nomination"
        )
        self.assertEqual(academies["numerator"], 3_696)
        self.assertEqual(academies["denominator"], 1_944_624)
        early = next(row for row in rows if row["route"] == "Early action")
        self.assertEqual((early["numerator"], early["denominator"]), (935, 1_950))
        athletics = [row for row in rows if row["route"] == "Recruited athletics"]
        self.assertEqual({row["measure"] for row in athletics}, {
            "share of admitted students",
            "admit rate among committee-reviewed athlete cases",
        })


if __name__ == "__main__":
    unittest.main()
