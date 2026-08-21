"""Regression checks for bugs previously found in the medicine parser."""

import tempfile
import unittest
from pathlib import Path

import medicine


class MedicineParserRegressionTest(unittest.TestCase):
    def test_sort_arrows_are_not_part_of_column_names(self):
        html = """<table id="medSchoolTable"><thead><tr>
        <th>Medical School <span>▲▼</span></th>
        <th>Median MCAT Score <span>▲▼</span></th></tr></thead>
        <tbody><tr><td>Example Medical School</td><td>512</td></tr></tbody></table>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.html"
            path.write_text(html, encoding="utf-8")
            row = next(medicine.medical_school_rows(path))
        self.assertEqual(row["Medical School"], "Example Medical School")
        self.assertEqual(row["Median MCAT Score"], "512")

    def test_cuny_is_not_discarded_as_a_system_prefix(self):
        candidates = ["CUNY School of Medicine", "New York Medical College"]
        self.assertEqual(
            medicine.match_medical_school("CUNY", candidates),
            "CUNY School of Medicine",
        )

    def test_bare_state_name_prefers_its_state_university(self):
        candidates = [
            "Medical College of Wisconsin",
            "University of Wisconsin School of Medicine and Public Health",
        ]
        self.assertEqual(
            medicine.match_medical_school("Wisconsin", candidates),
            candidates[1],
        )


if __name__ == "__main__":
    unittest.main()
