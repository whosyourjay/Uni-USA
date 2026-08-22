#!/usr/bin/env python3
"""Fuzz checks for ranking professional schools inside the bachelor table."""

import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import outputs
from uniusa import pathways
from uniusa.professional import common as professional


PROGRAMS = (pathways.BACHELOR_PROGRAM, "MD", "JD")


def random_table(rng):
    """A school table mixing bachelor rows with the rows scored from them."""
    rows = []
    for index in range(rng.randint(2, 60)):
        program = rng.choice(PROGRAMS)
        bachelor = program == pathways.BACHELOR_PROGRAM
        rows.append({
            "school": f"School {index}",
            "program": program,
            "cohort_median": round(rng.uniform(1, 100), 3),
            "ability": round(rng.uniform(1, 100), 3) if bachelor else "",
            "bachelors": round(rng.uniform(1, 9000), 3) if bachelor else "",
            "school_id": index + 1 if bachelor else 0,
            "freshman_score": round(rng.uniform(1, 100), 2) if bachelor else "",
        })
    return rows


class ProfessionalMergeTests(unittest.TestCase):
    def test_professional_rows_never_feed_their_own_origins(self):
        """A law or medical row in the table must not become a bachelor origin."""
        rng = random.Random(20260822)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "schools.tsv"
            for _ in range(200):
                rows = random_table(rng)
                pathways.write_tsv(path, rows)
                names = {name for name, _ in professional.school_candidates(path)}
                for row in rows:
                    if row["program"] != pathways.BACHELOR_PROGRAM:
                        self.assertNotIn(row["school"], names)
                origins = professional.bachelor_origins(path)
                self.assertTrue(all(origin["applicants"] > 0 for origin in origins))

    def test_merging_keeps_every_row_and_orders_by_the_shared_scale(self):
        """One list, sorted by cohort median, whatever program a row came from."""
        rng = random.Random(3)
        for _ in range(200):
            schools = [
                row for row in random_table(rng)
                if row["program"] == pathways.BACHELOR_PROGRAM
            ]
            professional_rows = [
                row for row in random_table(rng)
                if row["program"] != pathways.BACHELOR_PROGRAM
            ]
            blank = {column: "" for column in outputs.SCHOOL_COLUMNS}
            combined = outputs.assign_ranks(
                [{**blank, **row, "rank": ""} for row in schools + professional_rows],
                lambda row: (row["school_id"], row["school"]),
            )
            self.assertEqual(len(combined), len(schools) + len(professional_rows))
            medians = [row["cohort_median"] for row in combined]
            for earlier, later in zip(medians, medians[1:]):
                self.assertGreaterEqual(earlier, later)

    def test_fast_merge_replaces_professionals_without_touching_bachelors(self):
        blank = {column: "" for column in outputs.SCHOOL_COLUMNS}
        bachelor = blank | {
            "school": "Bachelor School",
            "program": pathways.BACHELOR_PROGRAM,
            "cohort_median": 80,
            "bachelors": 100,
        }
        medical = blank | {
            "school": "Medical School",
            "program": "MD",
            "cohort_median": 90,
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "schools.tsv"
            pathways.write_tsv(path, [bachelor])
            with patch.object(outputs, "professional_rows", return_value=[medical]):
                counts = outputs.merge_existing_professional_tables(path)
            rows = pathways.read_tsv(path)
        self.assertEqual(counts, (1, 1))
        self.assertEqual([row["school"] for row in rows],
                         ["Medical School", "Bachelor School"])


if __name__ == "__main__":
    unittest.main()
