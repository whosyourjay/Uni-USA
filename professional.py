#!/usr/bin/env python3
"""Shared parsers and scale conversions for professional-school outputs."""

import csv
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree

import pathways

ROOT = Path(__file__).parent
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


def interpolate(table, score):
    """Linearly interpolate a percentile lookup keyed by integer score."""
    score = float(score)
    if score <= min(table):
        return table[min(table)]
    if score >= max(table):
        return table[max(table)]
    low, high = int(score), int(score) + 1
    return table[low] + (score - low) * (table[high] - table[low])


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
    """Names and undergraduate cohort medians from the canonical school output."""
    rows = pathways.read_tsv(path or ROOT / "schools.tsv")
    return [
        (row["school"], {
            "school": row["school"],
            "ability": numeric(row["cohort_median"]) or numeric(row.get("ability")),
            "bachelors": numeric(row.get("bachelors")),
        })
        for row in rows
        if numeric(row.get("cohort_median")) is not None
        or numeric(row.get("ability")) is not None
    ]


def bachelor_origins(path=None):
    """The observed distribution of bachelor graduates over institution scores."""
    return [
        candidate | {"applicants": candidate["bachelors"]}
        for _, candidate in school_candidates(path)
        if candidate["bachelors"] and candidate["bachelors"] > 0
    ]


def weighted_quantile(rows, quantile, value="ability", weight="applicants"):
    """Observed value at a weighted quantile, ignoring rows without a value."""
    valid = sorted(
        (float(row[value]), float(row[weight]))
        for row in rows
        if row.get(value) not in {None, ""} and float(row.get(weight, 0)) > 0
    )
    total = sum(row_weight for _, row_weight in valid)
    target = min(1.0, max(0.0, quantile)) * total
    cumulative = 0.0
    for row_value, row_weight in valid:
        cumulative += row_weight
        if cumulative >= target:
            return row_value
    return valid[-1][0] if valid else None


def write_tsv(path, rows):
    rows = list(rows)
    if not rows:
        raise ValueError(f"No rows to write to {path}")
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=rows[0], delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
