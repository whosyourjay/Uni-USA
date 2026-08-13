#!/usr/bin/env python3
"""Convert fall-2019 IPEDS SAT and ACT bars to test-taker percentiles.

The routes stay separate.  SAT percentiles use College Board's *User Group*
columns (actual SAT takers), never its nationally representative columns.  ACT
percentiles use the exact composite-score frequencies for ACT-tested 2018 high
school graduates, the nearest complete official frequency table to the fall
2019 admissions baseline.

IPEDS publishes q25 and q75 but no median.  Under ability.py's three-segment
distribution, the median raw score is the midpoint of q25 and q75.  For SAT we
convert the two section medians independently and average their percentile
ranks; adding marginal section quantiles would not recover a total-score
quantile.  ACT uses the composite median directly.
"""

from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess

import ability
import pathways


ROOT = Path(__file__).parent
SAT_PERCENTILES = ROOT / "sources" / "SAT-national-percentiles.html"
ACT_PROFILE = ROOT / "sources" / "2018-act-national-profile.pdf"


def percentile_number(value):
    """Turn an official rounded/censored percentile cell into a number."""
    value = value.strip()
    if value == "99+":
        return 99.5
    if value == "1-":
        return 0.5
    return float(value.rstrip("%"))


class SectionPercentileParser(HTMLParser):
    """Extract rows from College Board's section-score percentile table."""

    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.cell = []
        self.row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if (
            tag == "table"
            and attributes.get("summary") == "Percentiles for Section Scores"
        ):
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.in_row = True
            self.row = []
        elif self.in_row and tag in {"th", "td"}:
            self.in_cell = True
            self.cell = []

    def handle_data(self, data):
        if self.in_cell:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if self.in_cell and tag in {"th", "td"}:
            self.row.append(" ".join("".join(self.cell).split()))
            self.in_cell = False
        elif self.in_row and tag == "tr":
            if self.row:
                self.rows.append(self.row)
            self.in_row = False
        elif self.in_table and tag == "table":
            self.in_table = False


def load_sat_user_percentiles(path=SAT_PERCENTILES):
    """Return component -> score -> percentile among recent SAT users.

    The official table has five columns: score, nationally representative ERW,
    user ERW, nationally representative Math, and user Math.  Selecting columns
    2 and 4 is intentional and regression-tested.
    """
    parser = SectionPercentileParser()
    parser.feed(path.read_text(encoding="utf-8"))
    output = {"reading and writing": {}, "math": {}}
    for row in parser.rows:
        if len(row) != 5 or not row[0].isdigit():
            continue
        score = int(row[0])
        output["reading and writing"][score] = percentile_number(row[2])
        output["math"][score] = percentile_number(row[4])
    if any(set(table) != set(range(200, 801, 10)) for table in output.values()):
        raise ValueError("Incomplete College Board SAT section percentile table")
    return output


def act_profile_text(path=ACT_PROFILE):
    """Extract layout-preserving text from the official ACT PDF."""
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError("pdftotext is required to parse the ACT profile") from error
    return result.stdout


def load_act_composite_percentiles(path=ACT_PROFILE):
    """Return exact score frequencies and CDFs among ACT-tested graduates."""
    text = act_profile_text(path)
    start = text.index("Table 2.1. ACT Score Distributions")
    end = text.index("Avg (SD)", start)
    counts = {}
    for line in text[start:end].splitlines():
        values = re.findall(r"(?<![.\d])\d[\d,]*(?![.\d])", line)
        if len(values) < 11:
            continue
        score = int(values[0].replace(",", ""))
        if not 1 <= score <= 36:
            continue
        # score; then N/CP pairs for English, Math, Reading, Science,
        # Composite, STEM, and ELA. Composite N is numeric field 9.
        counts[score] = int(values[9].replace(",", ""))
    if set(counts) != set(range(1, 37)):
        raise ValueError("Incomplete ACT composite frequency table")
    total = sum(counts.values())
    if total != 1_914_817:
        raise ValueError(f"Unexpected ACT profile total: {total:,}")
    running = 0
    percentiles = {}
    for score in sorted(counts):
        running += counts[score]
        percentiles[score] = 100 * running / total
    return counts, percentiles


def interpolate(table, value):
    """Linearly interpolate a monotone score-to-percentile lookup."""
    scores = sorted(table)
    if value <= scores[0]:
        return table[scores[0]]
    if value >= scores[-1]:
        return table[scores[-1]]
    lower = max(score for score in scores if score <= value)
    upper = min(score for score in scores if score >= value)
    if lower == upper:
        return table[lower]
    fraction = (value - lower) / (upper - lower)
    return table[lower] + fraction * (table[upper] - table[lower])


def component_percentile_rows(component_rows, sat_tables=None, act_table=None):
    """Attach test-taker q25, modeled median, and q75 percentiles."""
    if sat_tables is None:
        sat_tables = load_sat_user_percentiles()
    if act_table is None:
        _, act_table = load_act_composite_percentiles()
    output = []
    for row in component_rows:
        table = sat_tables[row["component"]] if row["route"] == "SAT" else act_table
        median_score = (row["score_q25_2019"] + row["score_q75_2019"]) / 2
        output.append({
            **row,
            "estimated_median_score_2019": median_score,
            "test_taker_percentile_q25": interpolate(
                table, row["score_q25_2019"]
            ),
            "test_taker_percentile_median": interpolate(table, median_score),
            "test_taker_percentile_q75": interpolate(
                table, row["score_q75_2019"]
            ),
            "percentile_population": (
                "SAT user group: actual SAT scores in the past three school years"
                if row["route"] == "SAT"
                else "ACT-tested 2018 high school graduates"
            ),
        })
    return output


def route_percentile_rows(component_rows):
    """Produce one percentile row per institution and test route."""
    grouped = defaultdict(list)
    for row in component_rows:
        grouped[(row["unitid"], row["route"])].append(row)

    output = []
    for (unitid, route), rows in grouped.items():
        expected = 2 if route == "SAT" else 1
        if len(rows) != expected:
            continue
        by_component = {row["component"]: row for row in rows}
        first = rows[0]
        result = {
            "unitid": unitid,
            "institution": first["institution"],
            "state": first["state"],
            "route": route,
            "submitters_2019": first["submitters_2019"],
            "estimated_route_central_test_taker_percentile": sum(
                row["test_taker_percentile_median"] for row in rows
            ) / len(rows),
            "percentile_population": first["percentile_population"],
            "route_statistic": (
                "mean of ERW and Math modeled-median percentile ranks"
                if route == "SAT"
                else "modeled-median ACT composite percentile rank"
            ),
        }
        for component, slug in (
            ("reading and writing", "sat_reading_writing"),
            ("math", "sat_math"),
            ("composite", "act_composite"),
        ):
            row = by_component.get(component)
            result[f"{slug}_estimated_median_score"] = (
                row["estimated_median_score_2019"] if row else ""
            )
            result[f"{slug}_median_test_taker_percentile"] = (
                row["test_taker_percentile_median"] if row else ""
            )
        output.append(result)
    return sorted(output, key=lambda row: (row["unitid"], row["route"]))


def mixture_median(rows):
    """Median of submitter-weighted reconstructed score distributions."""
    total = sum(row["submitters_2019"] for row in rows)
    if total <= 0:
        raise ValueError("Score mixture has no submitters")

    def cdf(value):
        return sum(
            row["submitters_2019"]
            * ability.interquartile_cdf(
                value,
                row["score_scale_min"],
                row["score_q25_2019"],
                row["score_q75_2019"],
                row["score_scale_max"],
            )
            for row in rows
        ) / total

    lower = min(row["score_scale_min"] for row in rows)
    upper = max(row["score_scale_max"] for row in rows)
    for _ in range(80):
        midpoint = (lower + upper) / 2
        if cdf(midpoint) < 0.5:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2


def national_route_percentile_rows(component_rows, sat_tables, act_table):
    """Summarize the score-reporting enrolled-submitter mixtures by route."""
    output = []
    for route in ("SAT", "ACT"):
        rows = [row for row in component_rows if row["route"] == route]
        grouped = defaultdict(list)
        for row in rows:
            grouped[row["component"]].append(row)
        component_results = {}
        for component, values in grouped.items():
            raw_median = mixture_median(values)
            table = sat_tables[component] if route == "SAT" else act_table
            component_results[component] = {
                "raw": raw_median,
                "percentile": interpolate(table, raw_median),
            }
        result = {
            "route": route,
            "submitters_with_score_bars_2019": sum(
                row["submitters_2019"]
                for row in next(iter(grouped.values()))
            ),
            "estimated_route_central_test_taker_percentile": sum(
                value["percentile"] for value in component_results.values()
            ) / len(component_results),
            "percentile_population": (
                "SAT user group: actual SAT scores in the past three school years"
                if route == "SAT"
                else "ACT-tested 2018 high school graduates"
            ),
            "mixture": (
                "IPEDS score-bar institutions weighted by enrolled submitters"
            ),
        }
        for component, slug in (
            ("reading and writing", "sat_reading_writing"),
            ("math", "sat_math"),
            ("composite", "act_composite"),
        ):
            value = component_results.get(component)
            result[f"{slug}_mixture_median_score"] = value["raw"] if value else ""
            result[f"{slug}_mixture_median_test_taker_percentile"] = (
                value["percentile"] if value else ""
            )
        output.append(result)
    return output


def score_table_rows(sat_tables, act_counts, act_table):
    """Make the parsed official lookups inspectable without tracking data."""
    output = []
    for component, table in sat_tables.items():
        for score, percentile in sorted(table.items()):
            output.append({
                "route": "SAT",
                "component": component,
                "score": score,
                "test_taker_percentile": percentile,
                "test_takers_at_score": "",
                "source": "College Board SAT User Group Percentiles",
            })
    for score, percentile in sorted(act_table.items()):
        output.append({
            "route": "ACT",
            "component": "composite",
            "score": score,
            "test_taker_percentile": percentile,
            "test_takers_at_score": act_counts[score],
            "source": "ACT Profile Report, graduating class 2018, Table 2.1",
        })
    return output


def main():
    graduates = pathways.graduate_rows(
        pathways.load_directory(),
        pathways.load_completions(),
        pathways.load_outcomes(),
        pathways.load_enrollment(),
    )
    evidence = ability.ability_evidence_rows(graduates, ability.load_admissions())
    components = ability.test_component_rows(evidence)
    sat_tables = load_sat_user_percentiles()
    act_counts, act_table = load_act_composite_percentiles()
    percentiles = component_percentile_rows(components, sat_tables, act_table)
    routes = route_percentile_rows(percentiles)
    pathways.write_tsv(
        pathways.DERIVED / "test_taker_score_percentiles.tsv",
        score_table_rows(sat_tables, act_counts, act_table),
    )
    pathways.write_tsv(
        pathways.DERIVED / "freshman_test_component_percentiles.tsv", percentiles
    )
    pathways.write_tsv(
        pathways.DERIVED / "freshman_test_route_percentiles.tsv", routes
    )
    pathways.write_tsv(
        pathways.DERIVED / "national_test_route_percentiles.tsv",
        national_route_percentile_rows(components, sat_tables, act_table),
    )
    print(
        f"scored {len(routes):,} institution-routes on separate SAT and ACT "
        "test-taker percentile scales"
    )


if __name__ == "__main__":
    main()
