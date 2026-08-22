#!/usr/bin/env python3
"""Score U.S. MD schools and bridge MCAT rank through applicant origins."""

import re
from html.parser import HTMLParser

from uniusa import pathways, scales, school_distributions
from uniusa.professional import common as professional

SCHOOL_SOURCE = professional.SOURCES / "medical-school-mcat.html"
MCAT_SOURCE = professional.SOURCES / "mcat-percentiles-2024.txt"
FEEDER_SOURCE = professional.SOURCES / "aamc-medical-feeders-2023.txt"
COUNT_SOURCE = professional.SOURCES / "aamc-medical-matriculants-2023.txt"
FEEDER_OUTPUT = pathways.DERIVED / "medical_feeders.tsv"
COUNT_OUTPUT = pathways.DERIVED / "medical_school_counts.tsv"
OUTPUT = professional.ROOT / "medical-schools.tsv"
FEEDER_ALIASES = {
    "University of Minnesota": "University of Minnesota-Twin Cities",
    "Louisiana St University and Agricultural and Mechanical Col": (
        "Louisiana State University and Agricultural & Mechanical College"
    ),
    "Penn State University Park": "Pennsylvania State University-Main Campus",
    "University of Puerto Rico-Rio Piedras Campus": (
        "University of Puerto Rico-Rio Piedras"
    ),
    "University of Puerto Rico-Mayaguez Campus": "University of Puerto Rico-Mayaguez",
    "Indiana University-Purdue University-Indianapolis": "Indiana University-Indianapolis",
    "Kent State University Kent Campus": "Kent State University at Kent",
}
MEDICAL_STOP_WORDS = {
    "at", "college", "medicine", "medical", "of", "school", "the", "university",
}
MEDICAL_EXPANSIONS = {
    "bu": "boston university", "cal": "california", "cuny": "city university new york",
    "fiu": "florida international university", "lsu": "louisiana state university",
    "mc": "medical college", "med": "medical", "mu": "medical university",
    "penn": "pennsylvania", "rw": "robert wood", "tcu": "texas christian university",
    "u": "university", "uc": "university california",
    "ucf": "university central florida", "ucla": "university california los angeles",
    "usf": "university south florida", "ut": "university texas",
    "uthealth": "university texas health",
}


class TableParser(HTMLParser):
    def __init__(self, table_id):
        super().__init__()
        self.table_id = table_id
        self.in_table = self.in_cell = False
        self.row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table" and attrs.get("id") == self.table_id:
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.row = []
        elif self.in_table and tag in {"th", "td"}:
            self.in_cell = True
            self.row.append("")

    def handle_data(self, data):
        if self.in_cell:
            self.row[-1] += data

    def handle_endtag(self, tag):
        if self.in_table and tag in {"th", "td"}:
            self.in_cell = False
        elif self.in_table and tag == "tr" and self.row:
            self.rows.append([value.strip() for value in self.row])
        elif self.in_table and tag == "table":
            self.in_table = False


def medical_school_rows(path=SCHOOL_SOURCE):
    parser = TableParser("medSchoolTable")
    parser.feed(path.read_text(encoding="utf-8"))
    raw_header, *values = parser.rows
    header = [value.replace("▲▼", "").strip() for value in raw_header]
    for row in values:
        yield dict(zip(header, row))


def mcat_percentiles(path=MCAT_SOURCE):
    """Total-score ranks from the downloaded extraction of AAMC's 2024 PDF."""
    text = path.read_text(encoding="utf-8")
    pairs = re.findall(r"\b(4(?:7[2-9]|[89]\d)|5(?:[01]\d|2[0-8]))\s+(<1|\d{1,3})\b", text)
    table = {int(score): 0.5 if rank == "<1" else float(rank)
             for score, rank in pairs}
    if set(table) != set(range(472, 529)):
        raise ValueError(f"Expected MCAT scores 472-528, found {len(table)}")
    return professional.spread_rounded_percentiles(table)


def feeder_variants(name, city):
    """Mechanical spelling variants between the AAMC and IPEDS directories."""
    yield name
    yield f"{name}-{city}"
    yield f"{name}-{city} Campus"
    for suffix in (f"-{city}", " Main Campus"):
        if name.endswith(suffix):
            yield name[:-len(suffix)]
    if name.startswith("State University of New York at "):
        yield name.removeprefix("State University of New York at ") + " University"
    if name.startswith("City University of New York "):
        yield "CUNY " + name.removeprefix("City University of New York ")
    if name == "College of William & Mary":
        yield "William & Mary"


def candidate_index(candidates):
    grouped = {}
    duplicates = set()
    for name, value in candidates:
        normalized = pathways.normalize_school(name)
        if normalized in grouped:
            duplicates.add(normalized)
        grouped[normalized] = value
    return {name: value for name, value in grouped.items() if name not in duplicates}


def match_feeder(name, city, candidates, exact):
    alias = FEEDER_ALIASES.get(name)
    if alias:
        match = exact.get(pathways.normalize_school(alias))
        if match:
            return match
    for variant in feeder_variants(name, city):
        match = exact.get(pathways.normalize_school(variant))
        if match:
            return match
    return pathways.match_name(name, candidates)


def feeder_rows(path=FEEDER_SOURCE):
    candidates = professional.school_candidates()
    exact = candidate_index(candidates)
    rows = []
    text = path.read_text(encoding="utf-8")
    records = re.findall(
        r"^\*\*(.+), ([^,]+), ([A-Z]{2})\*\*([\d,]+)$", text, re.MULTILINE
    )
    if len(records) < 100:
        raise ValueError(f"Expected the full AAMC feeder table, found {len(records)} rows")
    for source_name, city, _, applicants in records:
        match = match_feeder(source_name, city, candidates, exact)
        rows.append({
            "source_institution": source_name,
            "applicants": int(applicants.replace(",", "")),
            "school": match["school"] if match else "",
            "ability": match["ability"] if match else "",
            "bachelors": match["bachelors"] if match else "",
        })
    return rows


def medical_count_rows(path=COUNT_SOURCE):
    """AAMC first-year matriculants by abbreviated medical-school name."""
    text = path.read_text(encoding="utf-8")
    pattern = (
        r"^(?:\*\*[A-Z]{2}\*\*\*\*|\*{6})(.+?)\*\*([\d,]+)"
        r"(?:\s+\d+(?:\.\d+)?){4}\s+([\d,]+)"
    )
    rows = [
        {"aamc_school": name, "applications": int(applications.replace(",", "")),
         "students": int(students.replace(",", ""))}
        for name, applications, students in re.findall(pattern, text, re.MULTILINE)
    ]
    if len(rows) < 150:
        raise ValueError(f"Expected the full AAMC school table, found {len(rows)} rows")
    return rows


def medical_tokens(name):
    tokens = re.sub(r"[^a-z0-9]+", " ", name.lower()).split()
    expanded = []
    for token in tokens:
        expanded.extend(MEDICAL_EXPANSIONS.get(token, token).split())
    return set(expanded) - MEDICAL_STOP_WORDS


def match_medical_school(name, candidates):
    """Unique token match from AAMC's abbreviations to full MSAR-style names."""
    if len(name.split()) <= 2:
        expanded = pathways.match_name("University of " + name, [
            (candidate, candidate) for candidate in candidates
        ])
        if expanded:
            return expanded
    source = medical_tokens(name)
    scored = []
    for candidate in candidates:
        target = medical_tokens(candidate)
        common = len(source & target)
        coverage = common / len(source) if source else 0
        precision = common / len(target) if target else 0
        scored.append((coverage + precision / 4, coverage, candidate))
    scored.sort(reverse=True)
    best, runner_up = scored[:2]
    if best[1] < 0.75 or best[0] - runner_up[0] < 0.08:
        return ""
    return best[2]


def matched_count_rows(school_names):
    rows = []
    for row in medical_count_rows():
        school = match_medical_school(row["aamc_school"], school_names)
        rows.append(row | {"school": school})
    return rows


def applicant_mixture(origins, distributions=None):
    """AAMC applicant-weighted mixture of undergraduate school CDFs."""
    return professional.origin_mixture(origins, distributions)


def score_row(row, table, mixture, ability_cache=None):
    mcat = professional.numeric(row.get("Median MCAT Score"))
    percentile = professional.interpolate(table, mcat) if mcat else None
    ability_cache = {} if ability_cache is None else ability_cache
    if percentile is not None and percentile not in ability_cache:
        ability_cache[percentile] = mixture.quantile(percentile / 100)
    ability = ability_cache.get(percentile)
    return {
        "school": row["Medical School"],
        "ability": round(ability, 3) if ability is not None else "",
        "mcat": round(mcat, 1) if mcat is not None else "",
        "mcat_taker_percentile": round(percentile, 3) if percentile is not None else "",
    }


def school_rows(origins, counts, mixture=None):
    table = mcat_percentiles()
    mixture = mixture or applicant_mixture(origins)
    ability_cache = {}
    rows = [
        score_row(row, table, mixture, ability_cache)
        for row in medical_school_rows()
    ]
    for row in rows:
        row["students"] = counts.get(row["school"], "")
    rows = [
        {key: row[key] for key in ("school", "ability", "students", "mcat",
                                   "mcat_taker_percentile")}
        for row in rows
    ]
    rows.sort(key=lambda row: (row["ability"] == "", -(row["ability"] or 0)))
    return rows


def main():
    origins = feeder_rows()
    distributions = school_distributions.distributions_by_name()
    professional.write_tsv(FEEDER_OUTPUT, (
        row | {"distribution_available": row["school"] in distributions}
        for row in origins
    ))
    mixture = applicant_mixture(origins, distributions)
    medical_names = [row["Medical School"] for row in medical_school_rows()]
    count_rows = matched_count_rows(medical_names)
    professional.write_tsv(COUNT_OUTPUT, count_rows)
    counts = {row["school"]: row["students"] for row in count_rows if row["school"]}
    rows = school_rows(origins, counts, mixture)
    for row in rows:
        row["test_taker_ability"] = (
            round(scales.test_taker_percentile(row["ability"]), 3)
            if row["ability"] != "" else ""
        )
    professional.write_tsv(OUTPUT, rows)
    matched = sum(row["applicants"] for row in origins if row["ability"] != "")
    total = sum(row["applicants"] for row in origins)
    counted = sum(row["students"] for row in count_rows if row["school"])
    all_students = sum(row["students"] for row in count_rows)
    print(f"{OUTPUT.name}: {len(rows)} MD schools; feeder match {matched}/{total}; "
          f"distribution mass {mixture.weight:.0f}; matriculant match "
          f"{counted}/{all_students}")


if __name__ == "__main__":
    main()
