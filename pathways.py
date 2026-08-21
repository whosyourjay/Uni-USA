#!/usr/bin/env python3
"""Build final-bachelor institution weights and graduate pathway mixtures."""

import csv
import io
import re
import zipfile
from collections import defaultdict
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).parent
SOURCES = ROOT / "sources"
DERIVED = ROOT / "derived"
COMPLETION_YEARS = tuple(range(2014, 2024))
COMPLETION_SOURCES = {year: f"C{year}_A.zip" for year in COMPLETION_YEARS}
LATEST_COMPLETIONS = COMPLETION_SOURCES[COMPLETION_YEARS[-1]]
AWARD_TABLE = DERIVED / "first_major_awards.tsv"
SCHOOL_YEAR_TABLE = DERIVED / "school_bachelors_by_year.tsv"
MAJOR_MEAN_TABLE = DERIVED / "major_bachelor_means.tsv"
AWARD_COLUMNS = {
    "unitid": int,
    "cip_code": str,
    "award_level": int,
    "awards_all": int,
    "awards_domestic": int,
}
SCHOOL_YEAR_COLUMNS = {
    "year": int, "unitid": int, "awards_all": int, "awards_domestic": int,
}
MAJOR_MEAN_COLUMNS = {"unitid": int, "cip_code": str, "mean_domestic": float}
ENTRY_LEVELS = {4: "first_time", 19: "transfer"}
OM_COHORTS = {10: "direct_full_time", 20: "direct_part_time",
              30: "transfer_full_time", 40: "transfer_part_time"}
LEVEL_NAMES = {1: "four-or-more-year", 2: "two-to-four-year", 3: "under-two-year"}
CONTROL_NAMES = {1: "public", 2: "private nonprofit", 3: "private for-profit"}
NAME_ALIASES = {"st": "saint", "univ": "university"}
EDGE_WORDS = {"the", "suny", "cuny"}
EXCLUDED_WORDS = {"digital", "online"}
MAIN_CAMPUS = "main campus"


def number(value):
    value = (value or "").strip()
    return int(value) if value not in {"", "."} else 0


def normalize_school(name):
    """Institution name reduced to the words that identify it.

    Sources spell the same institution with `St.` or `Saint`, with a leading or
    trailing `The`, and with or without a `(SUNY)` style system tag.
    """
    name = name.lower().replace("&", " and ")
    words = [
        NAME_ALIASES.get(word, word)
        for word in re.sub(r"[^a-z0-9]+", " ", name).split()
    ]
    while words and words[0] in EDGE_WORDS:
        words.pop(0)
    while words and words[-1] in EDGE_WORDS:
        words.pop()
    return " ".join(words)


def match_name(name, candidates):
    """The one `(name, value)` candidate an institution name picks out.

    An exactly matching name wins, then a single longer name that extends it,
    then a near match that clearly beats its runner-up.  Anything ambiguous
    returns None rather than guessing between two institutions.
    """
    normalized = normalize_school(name)
    pairs = [(normalize_school(label), value) for label, value in candidates]
    exact = [value for label, value in pairs if label == normalized]
    if len(exact) == 1:
        return exact[0]
    extended = [
        (label, value) for label, value in pairs
        if label.startswith(normalized + " ") and not EXCLUDED_WORDS & set(label.split())
    ]
    flagship = [value for label, value in extended if label.endswith(MAIN_CAMPUS)]
    if len(extended) == 1 or len(flagship) == 1:
        return flagship[0] if flagship else extended[0][1]
    scored = sorted(
        (
            (SequenceMatcher(None, normalized, label).ratio(), index)
            for index, (label, _) in enumerate(pairs)
        ),
        reverse=True,
    )
    if scored[0][0] >= 0.94 and scored[0][0] - scored[1][0] >= 0.03:
        return pairs[scored[0][1]][1]
    return None


def zip_values(filename, member=None):
    """Yield the header row and then each value row of a zipped CSV."""
    with zipfile.ZipFile(SOURCES / filename) as archive:
        if member is None:
            names = [name for name in archive.namelist()
                     if name.lower().endswith(".csv") and "_rv." not in name.lower()]
            if len(names) != 1:
                raise ValueError(f"Expected one primary CSV in {filename}: {names}")
            member = names[0]
        with archive.open(member) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
            yield from csv.reader(text)


def zip_rows(filename, member=None):
    values = zip_values(filename, member)
    header = next(values)
    for row in values:
        yield dict(zip(header, row))


def read_tsv(path, columns=None):
    """Read a TSV into dicts, converting the columns named in `columns`."""
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.reader(source, delimiter="\t")
        header = next(reader)
        casts = [(columns or {}).get(name) for name in header]
        return [
            {
                name: cast(value) if cast else value
                for name, cast, value in zip(header, casts, row)
            }
            for row in reader
        ]


def is_stale(path, sources):
    """Whether a derived table is missing or older than any source it reads."""
    if not path.exists():
        return True
    stamp = path.stat().st_mtime
    return any(
        (SOURCES / source).exists() and (SOURCES / source).stat().st_mtime > stamp
        for source in sources
    )


def preprocessed_rows(path, source, build, columns):
    """Read a derived table, rebuilding it whenever its source is newer."""
    if is_stale(path, (source,)):
        write_tsv(path, build())
    return read_tsv(path, columns)


def build_award_rows(source=None):
    """First-major award counts, the only completions rows the model uses."""
    values = zip_values(source or LATEST_COMPLETIONS)
    index = {name: position for position, name in enumerate(next(values))}
    major = index["MAJORNUM"]
    picked = [index[name] for name in
              ("UNITID", "CIPCODE", "AWLEVEL", "CTOTALT", "CNRALT")]
    rows = []
    for row in values:
        if number(row[major]) != 1:
            continue
        unitid, cip, level, total, foreign = (row[position] for position in picked)
        rows.append({
            "unitid": number(unitid),
            "cip_code": cip.strip(),
            "award_level": number(level),
            "awards_all": number(total),
            "awards_domestic": number(total) - number(foreign),
        })
    return rows


@lru_cache(maxsize=1)
def first_major_awards():
    return tuple(preprocessed_rows(
        AWARD_TABLE, LATEST_COMPLETIONS, build_award_rows, AWARD_COLUMNS
    ))


def bachelor_major_awards():
    """Per-major bachelor's awards, excluding the CIP 99 institution totals."""
    return [
        row for row in first_major_awards()
        if row["award_level"] == 5 and row["cip_code"] != "99"
    ]


def build_bachelor_tables():
    """Annual institution totals and mean per-major awards over every year."""
    schools, totals, years = [], defaultdict(int), defaultdict(int)
    for year, source in COMPLETION_SOURCES.items():
        for row in build_award_rows(source):
            if row["award_level"] != 5:
                continue
            if row["cip_code"] == "99":
                schools.append({
                    "year": year,
                    "unitid": row["unitid"],
                    "awards_all": row["awards_all"],
                    "awards_domestic": row["awards_domestic"],
                })
                years[row["unitid"]] += 1
            elif row["awards_domestic"] > 0:
                totals[(row["unitid"], row["cip_code"])] += row["awards_domestic"]
    majors = [
        {"unitid": unitid, "cip_code": cip, "mean_domestic": total / years[unitid]}
        for (unitid, cip), total in sorted(totals.items())
        if years[unitid]
    ]
    return schools, majors


@lru_cache(maxsize=1)
def bachelor_tables():
    """Cached multi-year bachelor's tables, preprocessed from the IPEDS zips."""
    paths = (SCHOOL_YEAR_TABLE, MAJOR_MEAN_TABLE)
    sources = tuple(COMPLETION_SOURCES.values())
    if any(is_stale(path, sources) for path in paths):
        for path, rows in zip(paths, build_bachelor_tables()):
            write_tsv(path, rows)
    return (
        tuple(read_tsv(SCHOOL_YEAR_TABLE, SCHOOL_YEAR_COLUMNS)),
        tuple(read_tsv(MAJOR_MEAN_TABLE, MAJOR_MEAN_COLUMNS)),
    )


def mean_bachelors():
    """Mean annual domestic bachelor's awards over the years each school reports."""
    totals, years = defaultdict(int), defaultdict(int)
    for row in bachelor_tables()[0]:
        totals[row["unitid"]] += row["awards_domestic"]
        years[row["unitid"]] += 1
    return {unitid: total / years[unitid] for unitid, total in totals.items()}


def mean_major_bachelors():
    """Mean annual domestic awards for each institution and CIP code."""
    return bachelor_tables()[1]


def load_population():
    path = SOURCES / "nc-est2023-agesex-res.csv"
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if number(row["SEX"]) == 0 and number(row["AGE"]) == 18:
                return number(row["POPESTIMATE2023"])
    raise ValueError("Census age-18 row not found")


def load_directory():
    return {number(row["UNITID"]): row for row in zip_rows("HD2023.zip")}


def load_completions():
    completions = {}
    for row in first_major_awards():
        if row["cip_code"] == "99" and row["award_level"] == 5:
            unitid = row["unitid"]
            if unitid in completions:
                raise ValueError(f"Duplicate bachelor's total for {unitid}")
            completions[unitid] = {
                "bachelors_all": row["awards_all"],
                "bachelors_domestic": row["awards_domestic"],
            }
    return completions


def load_outcomes():
    outcomes = defaultdict(dict)
    for row in zip_rows("OM2023.zip"):
        cohort = number(row["OMCHRT"])
        if cohort in OM_COHORTS:
            outcomes[number(row["UNITID"])][cohort] = {
                "cohort": number(row["OMACHRT"]),
                "bachelors": number(row["OMBACH8"]),
            }
    return outcomes


def load_enrollment():
    enrollment = defaultdict(dict)
    for row in zip_rows("EFFY2024.zip"):
        level = number(row["EFFYALEV"])
        if level in ENTRY_LEVELS:
            total = number(row["EFYTOTLT"])
            enrollment[number(row["UNITID"])][level] = {
                "all": total,
                "domestic": total - number(row["EFYNRALT"]),
            }
    return enrollment


def om_sum(outcomes, unitid, cohorts, field):
    return sum(outcomes.get(unitid, {}).get(code, {}).get(field, 0) for code in cohorts)


def graduate_rows(directory, completions, outcomes, enrollment):
    rows = []
    for unitid, awards in completions.items():
        if awards["bachelors_domestic"] <= 0:
            continue
        institution = directory.get(unitid, {})
        direct_bach = om_sum(outcomes, unitid, (10, 20), "bachelors")
        transfer_bach = om_sum(outcomes, unitid, (30, 40), "bachelors")
        direct_cohort = om_sum(outcomes, unitid, (10, 20), "cohort")
        transfer_cohort = om_sum(outcomes, unitid, (30, 40), "cohort")
        route_total = direct_bach + transfer_bach
        row = {
            "unitid": unitid,
            "institution": institution.get("INSTNM", ""),
            "state": institution.get("STABBR", ""),
            "institution_level": LEVEL_NAMES.get(number(institution.get("ICLEVEL")), "unknown"),
            "control": CONTROL_NAMES.get(number(institution.get("CONTROL")), "unknown"),
            **awards,
            "direct_bachelors_8yr": direct_bach,
            "transfer_bachelors_8yr": transfer_bach,
            "transfer_share_bachelors_8yr": transfer_bach / route_total if route_total else "",
            "direct_entering_cohort": direct_cohort,
            "transfer_entering_cohort": transfer_cohort,
            "direct_bachelor_rate_8yr": direct_bach / direct_cohort if direct_cohort else "",
            "transfer_bachelor_rate_8yr": transfer_bach / transfer_cohort if transfer_cohort else "",
        }
        for level, label in ENTRY_LEVELS.items():
            values = enrollment.get(unitid, {}).get(level, {"all": 0, "domestic": 0})
            row[label + "_entrants_all"] = values["all"]
            row[label + "_entrants_domestic"] = values["domestic"]
        rows.append(row)
    return sorted(rows, key=lambda row: (row["institution"], row["unitid"]))


def cohort_pathway_rows(population, rows):
    domestic = sum(row["bachelors_domestic"] for row in rows)
    direct = sum(row["direct_bachelors_8yr"] for row in rows)
    transfer = sum(row["transfer_bachelors_8yr"] for row in rows)
    if domestic > population:
        raise ValueError("Bachelor flow exceeds the age-18 population")
    if direct + transfer == 0:
        raise ValueError("No graduate route observations")

    # First subtract the bachelor flow from the complete age-18 population. Then
    # split only the bachelor portion using the Outcome Measures graduate mix.
    no_bachelor = population - domestic
    transfer_estimate = round(domestic * transfer / (direct + transfer))
    direct_estimate = domestic - transfer_estimate
    values = [
        ("No bachelor's degree", no_bachelor, "residual"),
        ("Bachelor's, no prior college on entry to final institution", direct_estimate,
         "IPEDS Outcome Measures route share"),
        ("Bachelor's, prior college before final institution", transfer_estimate,
         "IPEDS Outcome Measures route share"),
    ]
    return [
        {
            "path": path,
            "people": people,
            "share_age18": people / population,
            "construction": construction,
        }
        for path, people, construction in values
    ]


def level_rows(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["institution_level"]].append(row)
    output = []
    for level in ("four-or-more-year", "two-to-four-year", "under-two-year", "unknown"):
        group = groups[level]
        if not group:
            continue
        direct = sum(row["direct_bachelors_8yr"] for row in group)
        transfer = sum(row["transfer_bachelors_8yr"] for row in group)
        output.append({
            "institution_level": level,
            "institutions": len(group),
            "bachelors_domestic": sum(row["bachelors_domestic"] for row in group),
            "om_direct_bachelors": direct,
            "om_transfer_bachelors": transfer,
            "om_transfer_share_bachelors": transfer / (direct + transfer) if direct + transfer else "",
        })
    return output


def write_tsv(path, rows):
    rows = list(rows)
    path.parent.mkdir(exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter="\t",
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    population = load_population()
    completions = load_completions()
    rows = graduate_rows(load_directory(), completions, load_outcomes(), load_enrollment())
    write_tsv(DERIVED / "institution_graduates.tsv", rows)
    write_tsv(DERIVED / "cohort_pathways.tsv",
              cohort_pathway_rows(population, rows))
    write_tsv(DERIVED / "graduate_pathways_by_level.tsv", level_rows(rows))
    print(f"wrote {len(rows):,} bachelor-awarding institutions to {DERIVED}")


if __name__ == "__main__":
    main()
