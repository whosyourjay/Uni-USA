#!/usr/bin/env python3
"""Shared parsers and scale conversions for professional-school outputs."""

import csv
import re
import zipfile
from math import exp, log
from collections import defaultdict
from xml.etree import ElementTree

from uniusa import pathways, school_distributions
from uniusa.paths import ROOT

SOURCES = ROOT / "sources"

XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def xlsx_column(reference):
    """Zero-based column number from an A1-style cell reference."""
    letters = re.match(r"[A-Z]+", reference).group()
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - ord("A") + 1
    return value - 1


def shared_strings(archive):
    """The shared-string table in an XLSX archive, including rich text."""
    try:
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [
        "".join(node.text or "" for node in item.iter(XLSX_NS + "t"))
        for item in root.findall(XLSX_NS + "si")
    ]


def cell_value(cell, strings):
    kind = cell.get("t")
    value = cell.find(XLSX_NS + "v")
    if kind == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(XLSX_NS + "t"))
    if value is None or value.text is None:
        return ""
    if kind == "s":
        return strings[int(value.text)]
    return value.text


def xlsx_rows(path, sheet="xl/worksheets/sheet1.xml"):
    """Yield rows from a simple XLSX worksheet using only the standard library."""
    with zipfile.ZipFile(path) as archive:
        strings = shared_strings(archive)
        root = ElementTree.fromstring(archive.read(sheet))
    for xml_row in root.iter(XLSX_NS + "row"):
        cells = {
            xlsx_column(cell.get("r")): cell_value(cell, strings)
            for cell in xml_row.findall(XLSX_NS + "c")
        }
        if not cells:
            yield []
            continue
        yield [cells.get(index, "") for index in range(max(cells) + 1)]


def numeric(value):
    """Float from a spreadsheet field, or None for suppressed/missing values."""
    value = str(value or "").strip().replace(",", "").replace("%", "")
    if value in {"", "-", "—", "N/A", "NA"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def interpolate_points(points, x):
    """Linear interpolation over (x, y) pairs, flat beyond either end."""
    points = sorted(points)
    if x <= points[0][0]:
        return points[0][1]
    for (low_x, low_y), (high_x, high_y) in zip(points, points[1:]):
        if x <= high_x:
            if high_x == low_x:
                return high_y
            return low_y + (x - low_x) * (high_y - low_y) / (high_x - low_x)
    return points[-1][1]


def interpolate(table, score):
    """Linearly interpolate a percentile lookup keyed by integer score."""
    return interpolate_points(table.items(), float(score))


def spread_rounded_percentiles(table):
    """Break ties created by whole-percentile publication without inventing shape.

    Scores printed at percentile `p` divide the rounding interval for `p`
    evenly.  Thus five scores printed as 100 occupy the five equal slices of
    99.5--100 rather than all collapsing onto the maximum.
    """
    groups = defaultdict(list)
    for score, percentile in table.items():
        groups[percentile].append(score)
    result = {}
    for percentile, scores in groups.items():
        low = 0.0 if percentile < 1 else percentile - 0.5
        high = 100.0 if percentile == 100 else percentile + 0.5
        width = (high - low) / len(scores)
        for index, score in enumerate(sorted(scores)):
            result[score] = low + (index + 0.5) * width
    return result


def school_candidates(path=None):
    """Names and undergraduate cohort medians from the canonical school output.

    The same table also lists the law and medical schools scored from these
    rows, so those are dropped before they can feed their own origins.
    """
    rows = pathways.bachelor_rows(pathways.read_tsv(path or ROOT / "schools.tsv"))
    return [
        (row["school"], {
            "school": row["school"],
            "ability": school_distributions.estimated_percentile(row),
            "bachelors": numeric(row.get("bachelors")),
        })
        for row in rows
        if school_distributions.estimated_percentile(row) is not None
    ]


def bachelor_origins(path=None):
    """The observed distribution of bachelor graduates over institution scores."""
    return [
        candidate | {"applicants": candidate["bachelors"]}
        for _, candidate in school_candidates(path)
        if candidate["bachelors"] and candidate["bachelors"] > 0
    ]


MIDDLE_ABILITY = 50.0


def application_gradient(rows, floor=1e-5):
    """How fast the professional-application rate climbs with school ability.

    Sitting a professional entrance test gets steadily more common as the
    undergraduate school gets stronger.  Where applicant counts are published
    the climb can be measured, and a pipeline with no feeder table of its own
    can borrow the slope instead of pretending every graduate applies.
    """
    points = [
        (float(row["ability"]),
         log(max(row["applicants"] / float(row["bachelors"]), floor)),
         float(row["bachelors"]))
        for row in rows
        if numeric(row.get("ability")) is not None
        and numeric(row.get("bachelors")) and row["applicants"] > 0
    ]
    total = sum(weight for _, _, weight in points)
    mean_ability = sum(ability * weight for ability, _, weight in points) / total
    mean_rate = sum(rate * weight for _, rate, weight in points) / total
    covariance = sum(
        weight * (ability - mean_ability) * (rate - mean_rate)
        for ability, rate, weight in points
    )
    variance = sum(
        weight * (ability - mean_ability) ** 2 for ability, _, weight in points
    )
    return covariance / variance


def applicant_origins(rows, gradient, total=1.0):
    """Split `total` test takers over schools by graduates and that gradient.

    Only relative weights matter downstream, so `total` defaults to one and the
    column reads as each school's share of the taker pool.
    """
    weighted = [
        (row, float(row["bachelors"])
         * exp(gradient * (float(row["ability"]) - MIDDLE_ABILITY)))
        for row in rows
    ]
    scale = total / sum(weight for _, weight in weighted)
    return [row | {"applicants": weight * scale} for row, weight in weighted]


def origin_mixture(origins, distributions=None):
    """Mixture of undergraduate school CDFs weighted by the applicants each sends."""
    distributions = distributions or school_distributions.distributions_by_name()
    components = tuple(
        (distributions[row["school"]], row["applicants"])
        for row in origins
        if row["school"] in distributions
    )
    return school_distributions.DistributionMixture(components)


def write_tsv(path, rows):
    rows = list(rows)
    if not rows:
        raise ValueError(f"No rows to write to {path}")
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=rows[0], delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
