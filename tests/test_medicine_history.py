"""Annual medical observations retain entry dates and use lagged freshmen."""

from unittest import TestCase
from unittest.mock import Mock, patch

from uniusa import calibrate_tests
from uniusa.professional import medicine_history as history


class MedicineHistoryTest(TestCase):
    def test_early_study_reports_percentiles_not_new_scale_raw_scores(self):
        observations = list(history.study_observations())
        self.assertEqual([(r["entry_year"], r["students"], r["mcat_percentile"])
                          for r in observations], [(2013, 117, 95.7), (2014, 106, 97.4)])
        self.assertTrue(all("median_mcat" not in row for row in observations))
        self.assertTrue(all("not the full" in row["coverage"] for row in observations))

    def test_older_sat_support_is_observed_not_padded(self):
        old = calibrate_tests.load_sat_total_user_percentiles(2009)
        new = calibrate_tests.load_sat_total_user_percentiles(2019)
        self.assertEqual(set(old), set(range(410, 1601, 10)))
        self.assertEqual(set(new), set(range(400, 1601, 10)))
        self.assertEqual(calibrate_tests.rounded_percentile_interval("1\u00ad"), (0, 0.5))

    def test_year_specific_school_centers_come_from_actual_admissions(self):
        admission = {"ENRLT": "100", "ACTNUM": "100", "ACTCM25": "20", "ACTCM75": "30"}
        with patch.object(history.calibrate_tests, "load_sat_total_user_percentiles", return_value={}), \
                patch.object(history.calibrate_tests, "load_act_composite_percentiles",
                             return_value=({}, {20: 60, 30: 90})), \
                patch.object(history.pathways, "load_directory", return_value={1: {"INSTNM": "A"}}), \
                patch.object(history.ability, "load_admissions", return_value={1: admission}) as load:
            distribution = history.freshman_distributions(2009)["A"]
        load.assert_called_once_with(2009)
        self.assertEqual(distribution.median, 75)
        self.assertAlmostEqual(distribution.cdf(75), 0.5)
        self.assertGreater(distribution.spread, 0)

    def test_four_year_lag_and_common_panel_prevent_missing_school_mix_changes(self):
        origins = [{"school": name, "applicants": count} for name, count in (("A", 60), ("B", 40))]
        with patch.object(history, "freshman_distributions",
                          side_effect=[{"A": "old", "B": "old-b"}, {"A": "new"}]) as read, \
                patch.object(history.medicine, "applicant_mixture", return_value="mixture") as mix:
            result, meta = history.cohort_mixtures([2013, 2022], origins)
        self.assertEqual([call.args[0] for call in read.call_args_list], [2009, 2018])
        self.assertEqual(set(result), {2013, 2022})
        self.assertEqual(meta["feederCoverage"], 0.6)
        self.assertEqual(meta["feederSchools"], 1)
        self.assertTrue(all(call.args[0] == origins[:1] for call in mix.call_args_list))

    def test_entry_dates_do_not_shift_and_old_percentiles_bypass_new_score_table(self):
        old, new = Mock(), Mock()
        old.quantile.return_value, new.quantile.return_value = 99, 99.8
        rows = [
            {"entry_year": 2013, "mcat_percentile": 95.7, "students": 117},
            {"entry_year": 2022, "median_mcat": "522", "students": 105},
        ]
        rows = [dict(row, school="NYU", source_url="https://med.nyu.edu/") for row in rows]
        with patch.object(history, "cohort_mixtures", return_value=({2013: old, 2022: new}, {})), \
                patch.object(history.medicine, "mcat_percentiles", return_value={522: 99.1}):
            points, _ = history.estimate_observations(rows)
            self.assertEqual([p["year"] for p in points], [2013, 2022])
            self.assertEqual([p["freshmanYear"] for p in points], [2009, 2018])
            self.assertEqual([p["ability"] for p in points], [99, 99.8])
            self.assertNotIn("mcat", points[0])
            self.assertAlmostEqual(old.quantile.call_args.args[0], 0.957)
            self.assertAlmostEqual(new.quantile.call_args.args[0], 0.991)
            rows[0].pop("mcat_percentile")
            rows[0]["median_mcat"] = "36"
            with self.assertRaisesRegex(ValueError, "supported new-scale"):
                history.estimate_observations(rows)
