#!/usr/bin/env python3
"""Read College Transitions' entering-class tables into class-rank distributions.

The page lists the top-tenth, top-quarter and top-half shares of one entering
class for several hundred selective institutions.  Archived captures reach back
to fall 2017, so the same page supplies one cross-section per entering year.
These are the cumulative bins of Common Data Set section C10, so the
distribution math in `cds_c10` applies unchanged.  Captures from fall 2022 on
key each row by unitID; older ones are matched to IPEDS by name.
"""

import re
from functools import lru_cache

from uniusa import cds_c10, cds_documents, pathways


RANK_FIELDS = ("top_10_pct", "top_25_pct", "top_50_pct")
RANK_HEADER = re.compile(r"top (10|25|50)%")
YEAR_TEXT = re.compile(r"enrolling in Fall (\d{4})")
OUTPUT = pathways.DERIVED / "entering_class_rank.tsv"


def cell_percentage(text):
    """Read a `19%` cell, dropping the asterisk marking a stale year."""
    text = text.replace("*", "").replace("%", "").strip()
    return float(text) if text.replace(".", "", 1).isdigit() else None


def visible_text(path):
    """Page text with scripts, styles and tags removed."""
    body = re.sub(
        r"<(script|style).*?</\1>", " ",
        path.read_text(encoding="utf-8", errors="ignore"), flags=re.S | re.I,
    )
    return " ".join(re.sub(r"<[^>]+>", " ", body).split())


def entering_year(path):
    """The fall a capture describes, which is not the fall it was captured."""
    match = YEAR_TEXT.search(visible_text(path))
    if not match:
        raise ValueError(f"{path.name} does not state its entering year")
    return int(match.group(1))


def header_fields(header):
    """Column index of the institution, unitid and rank shares, by field name.

    Column names drift across captures: `Rank Top 10%` became `HS Rank (Top
    10%)`, and one capture carries a byte-order mark on `Institution`.
    """
    fields = {}
    for index, cell in enumerate(header):
        label = cell["text"].lstrip("﻿").strip().lower()
        rank = RANK_HEADER.search(label)
        if rank:
            fields[f"top_{rank.group(1)}_pct"] = index
        elif label in {"institution", "unitid"}:
            fields["school" if label == "institution" else "unitid"] = index
    missing = {"school", *RANK_FIELDS} - set(fields)
    if missing:
        raise ValueError(f"Entering-class table is missing {sorted(missing)}")
    return fields


def page_rows(path):
    """Rank shares one capture reports, before any unitid is resolved."""
    header, *body = cds_documents.table_rows(path)
    fields = header_fields(header)
    year = entering_year(path)
    output = []
    for cells in body:
        if len(cells) < len(header):
            continue
        school = cells[fields["school"]]["text"]
        if not school:
            continue
        unitid = cells[fields["unitid"]]["text"] if "unitid" in fields else ""
        output.append({
            "unitid": int(unitid) if unitid.isdigit() else None,
            "school": school,
            "entering_year": year,
            "stale": any("*" in cells[fields[f]]["text"] for f in RANK_FIELDS),
            **{field: cell_percentage(cells[fields[field]]["text"])
               for field in RANK_FIELDS},
        })
    return output


def unitid_by_name(rows):
    """Name to unitid, learned from the captures that publish a unitID column.

    Names no capture keys are matched against the IPEDS directory, which lists
    the same institutions under longer official names.
    """
    directory = [
        (entry["INSTNM"], unitid)
        for unitid, entry in pathways.load_directory().items()
    ]
    lookup = {
        pathways.normalize_school(name): unitid for name, unitid in directory
    }
    lookup.update({
        pathways.normalize_school(row["school"]): row["unitid"]
        for row in rows if row["unitid"]
    })
    for name in {row["school"] for row in rows}:
        if pathways.normalize_school(name) not in lookup:
            unitid = pathways.match_name(name, directory)
            if unitid is not None:
                lookup[pathways.normalize_school(name)] = unitid
    return lookup


@lru_cache(maxsize=None)
def source_rows():
    """One row per institution and entering year, across every capture.

    Later captures win, so a year the site restated arrives in its final form.
    """
    pages = [page_rows(path) for path in cds_documents.entering_class_paths()]
    lookup = unitid_by_name([row for page in pages for row in page])
    rows = {}
    for page in pages:
        for row in page:
            unitid = row["unitid"] or lookup.get(
                pathways.normalize_school(row["school"])
            )
            if unitid is not None:
                rows[(unitid, row["entering_year"])] = {**row, "unitid": unitid}
    return tuple(rows[key] for key in sorted(rows))


def rank_values(source):
    """Complete one row's five cumulative bins, or None if C10 cannot close.

    A handful of published rows fall rather than rise across the bins, which is
    a typo on the page and not a distribution.
    """
    shares = [source[field] for field in RANK_FIELDS]
    if any(share is None for share in shares) or shares != sorted(shares):
        return None
    return cds_c10.complete_rank_values({
        **{key: None for key in cds_c10.RANK_LABELS},
        **dict(zip(RANK_FIELDS, shares)),
    })


def scored_rows():
    """One row per institution and year, with statistics where the bins close."""
    output = []
    for source in source_rows():
        values = rank_values(source)
        statistics = dict(zip(cds_c10.STATISTIC_FIELDS, [""] * 4))
        if values is not None:
            statistics = cds_c10.distribution_statistics(values)
        output.append({
            "unitid": source["unitid"],
            "school": source["school"],
            "entering_year": source["entering_year"],
            **{key: "" if value is None else value
               for key, value in (values or source).items()
               if key in cds_c10.RANK_LABELS},
            **{key: round(value, 3) if value != "" else ""
               for key, value in statistics.items()},
            "stale_year": source["stale"],
        })
    return output


def rank_lookup():
    """Scored rows keyed by institution and entering year."""
    return {
        (row["unitid"], row["entering_year"]): row
        for row in scored_rows()
        if row["class_rank_mean"] != ""
    }


def school_history(unitid):
    """One school's scored rows, most recent entering year first."""
    return sorted(
        (row for key, row in rank_lookup().items() if key[0] == unitid),
        key=lambda row: -row["entering_year"],
    )


def main():
    fetched = cds_documents.fetch_entering_class_snapshots()
    if fetched:
        print(f"fetched {len(fetched)} archived captures")
    rows = scored_rows()
    pathways.write_tsv(OUTPUT, rows)
    scored = [row for row in rows if row["class_rank_mean"] != ""]
    years = sorted({row["entering_year"] for row in rows})
    print(
        f"{len(rows):,} institution-years listed across fall {years[0]}-{years[-1]}; "
        f"{len(scored):,} scored for {len({row['unitid'] for row in scored}):,} "
        f"institutions"
    )


if __name__ == "__main__":
    main()
