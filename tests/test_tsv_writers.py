"""Keep country output formats intact when using the shared writer."""

import contextlib
import csv
import io
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from uniusa import export_joint_scores, pathways, route_ability
from uniusa.professional import common


class TsvWriterTests(unittest.TestCase):
    def test_country_writer_formats(self):
        rng = random.Random(9421)
        values = ["", None, 0, False, 7.25, "東京", "a\tb", 'a"b', "a\r\nb"]
        writers = [(pathways.write_tsv, "\n"), (export_joint_scores.write, "\n"),
                   (common.write_tsv, "\r\n")]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "nested" / "table.tsv"
            for write, newline in writers:
                for case in range(60):
                    columns = rng.sample(["name", "seats", "ability"], 3)
                    rows = [{key: rng.choice(values) for key in columns}
                            for _ in range(rng.randint(1, 20))]
                    reference = io.StringIO(newline="")
                    writer = csv.DictWriter(reference, columns, delimiter="\t",
                                            lineterminator=newline)
                    writer.writeheader()
                    writer.writerows(rows)
                    with self.subTest(writer=write, case=case):
                        write(target, iter(rows))
                        self.assertEqual(target.read_bytes(),
                                         reference.getvalue().encode("utf-8"))

    def test_route_export_keeps_explicit_header_even_without_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "routes.tsv"
            with patch.object(route_ability, "TARGET", target), \
                    patch.object(route_ability, "rows", return_value=iter(())), \
                    contextlib.redirect_stdout(io.StringIO()):
                route_ability.main()
            self.assertEqual(target.read_bytes(),
                             ("\t".join(route_ability.FIELDS) + "\n").encode())
