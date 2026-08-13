"""End-to-end regressions for the canonical endpoint tables."""

from collections import Counter
import unittest

import outputs


class CanonicalOutputRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schools, cls.majors = outputs.build_tables()

    def test_school_and_major_weights_reconcile(self):
        self.assertEqual(len(self.schools), 2_356)
        self.assertEqual(len(self.majors), 64_314)
        self.assertEqual(
            sum(row["bachelors"] for row in self.schools), 1_897_543
        )
        self.assertEqual(
            sum(row["bachelors"] for row in self.majors), 1_897_543
        )
        majors_by_school = Counter()
        for row in self.majors:
            majors_by_school[row["school_id"]] += row["bachelors"]
        self.assertEqual(
            {row["school_id"]: row["bachelors"] for row in self.schools},
            majors_by_school,
        )

    def test_fixed_school_and_major_records(self):
        harvard = next(
            row for row in self.schools if row["school"] == "Harvard University"
        )
        self.assertEqual(harvard["school_id"], 166027)
        self.assertEqual(harvard["bachelors"], 1_654)
        self.assertEqual(harvard["sat_taker_percentile_2019"], 97.25)
        self.assertEqual(harvard["act_taker_percentile_2019"], 99.025)
        computer_science = next(
            row
            for row in self.majors
            if row["school_id"] == 166027 and row["cip_code"] == "11.0701"
        )
        self.assertEqual(computer_science["major"], "Computer Science")
        self.assertEqual(computer_science["bachelors"], 130)

    def test_partial_evidence_is_not_final_ability(self):
        self.assertTrue(all(row["ability"] == "" for row in self.schools))
        self.assertTrue(all(row["rank"] == "" for row in self.schools))
        self.assertTrue(all(row["ability"] == "" for row in self.majors))
        self.assertTrue(all(row["rank"] == "" for row in self.majors))


if __name__ == "__main__":
    unittest.main()
