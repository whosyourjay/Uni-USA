"""A missing display name must not crash an otherwise completed export."""

from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch

from uniusa import intake_ability


class IntakeCliTest(unittest.TestCase):
    def test_numeric_unitid_is_a_valid_display_fallback(self):
        row = {"school": "", "unitid": 123456, "status": "", "bachelors": 250,
               "submitters": 300, "median_percentile": 90}
        output = io.StringIO()
        with patch.object(intake_ability, "school_rows", return_value=[row]), \
                patch.object(intake_ability, "cohort_reach", return_value=.5), \
                patch.object(intake_ability.pathways, "write_tsv") as writer, \
                redirect_stdout(output):
            intake_ability.main()
        writer.assert_called_once_with(intake_ability.OUTPUT, [row])
        self.assertIn("123456", output.getvalue())
