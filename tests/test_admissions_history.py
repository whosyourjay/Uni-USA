"""The older admissions component must not change the main ranking's years."""

import unittest
from unittest.mock import patch

from uniusa import ability, scores


class AdmissionsHistoryTest(unittest.TestCase):
    def test_component_changes_in_2014(self):
        for year, name in ((2009, "IC2009.zip"), (2013, "IC2013.zip"),
                           (2014, "ADM2014.zip"), (2023, "ADM2023.zip")):
            with self.subTest(year=year), patch.object(ability.pathways, "zip_rows") as read:
                read.return_value = [{"UNITID": "110404", "ENRLT": "252"}]
                # Bypass the process-wide source cache so this test is isolated.
                self.assertEqual(ability.load_admissions.__wrapped__(year)[110404]["ENRLT"], "252")
                read.assert_called_once_with(name)

    def test_ranking_period_stays_unchanged(self):
        self.assertEqual(scores.ADMISSION_YEARS, tuple(range(2014, 2024)))
        self.assertEqual(scores.SAT_ADMISSION_YEARS, tuple(range(2016, 2024)))


if __name__ == "__main__":
    unittest.main()
