#!/usr/bin/env python3
"""Fetch and score 2019-20 Common Data Set class-rank distributions.

College Transitions maintains a centralized index of institution-published
Common Data Set files.  Section C10 uses the same five cumulative rank bins at
every institution.  This script downloads a fixed 20-school sample, extracts
C10, and estimates q25, median, q75, and mean class-rank percentiles with
uniform mass inside each published bin.
"""

import argparse
import csv
import hashlib
import html
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import unicodedata
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import zipfile

import ability
import pathways


ROOT = Path(__file__).parent
REPOSITORY_URL = (
    "https://www.collegetransitions.com/dataverse/"
    "common-data-set-repository/"
)
REPOSITORY_HTML = pathways.SOURCES / "common-data-set-repository.html"
CDS_DIRECTORY = pathways.SOURCES / "cds-2019"
YEAR_COLUMN = 6
SCHOOL_TABLE = ROOT / "schools.tsv"
RANK_LABELS = {
    "top_10_pct": (
        r"Percent in top tenth of high school graduating class",
        r"Top 10%",
    ),
    "top_25_pct": (
        r"Percent in top quarter of high school graduating class",
        r"Top 25%",
    ),
    "top_50_pct": (
        r"Percent in top half of high school graduating class",
        r"Top 50%",
    ),
    "bottom_50_pct": (
        r"Percent in bottom half of high school graduating class",
        r"Bottom 50%",
    ),
    "bottom_25_pct": (
        r"Percent in bottom quarter of high school graduating class",
        r"Bottom 25%",
    ),
}
LOCAL_SOURCE_OVERRIDES = {
    "Carnegie Mellon University": pathways.SOURCES / "cds-2019-carnegie-mellon.pdf",
    "Harvey Mudd College": pathways.SOURCES / "cds-2019-harvey-mudd.pdf",
}


class RepositoryParser(HTMLParser):
    """Read the year columns from the repository's HTML table."""

    def __init__(self):
        super().__init__()
        self.in_table = False
        self.row = None
        self.cell = None
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "table" and attributes.get("id") == "footable_22584":
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.row = []
        elif self.row is not None and tag == "td":
            self.cell = {"text": [], "href": ""}
        elif self.cell is not None and tag == "a":
            self.cell["href"] = attributes.get("href", "")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self.cell is not None:
            self.cell["text"] = " ".join("".join(self.cell["text"]).split())
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row:
            self.rows.append(self.row)
            self.row = None
        elif tag == "table" and self.in_table:
            self.in_table = False


def unwrap_repository_url(url):
    url = html.unescape(url)
    if urlparse(url).netloc == "www.google.com":
        url = parse_qs(urlparse(url).query).get("q", [""])[0]
    return unquote(url)


def repository_rows(path=REPOSITORY_HTML):
    parser = RepositoryParser()
    parser.feed(path.read_text(encoding="utf-8"))
    output = []
    for cells in parser.rows:
        if len(cells) <= YEAR_COLUMN:
            continue
        url = unwrap_repository_url(cells[YEAR_COLUMN]["href"])
        if url.startswith("https://"):
            output.append({"repository_school": cells[0]["text"], "source_url": url})
    return output


def fetch_repository_index():
    REPOSITORY_HTML.parent.mkdir(exist_ok=True)
    request = Request(REPOSITORY_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        data = response.read()
    partial = REPOSITORY_HTML.with_suffix(".html.part")
    partial.write_bytes(data)
    partial.replace(REPOSITORY_HTML)


def document_id(url):
    match = re.search(r"/(?:file/)?d/([^/]+)", urlparse(url).path)
    return match.group(1) if match else hashlib.sha256(url.encode()).hexdigest()[:20]


def direct_download_url(url):
    parsed = urlparse(url)
    identifier = document_id(url)
    if parsed.netloc == "drive.google.com":
        query = urlencode({"id": identifier, "export": "download", "confirm": "t"})
        return "https://drive.usercontent.google.com/download?" + query
    if parsed.netloc == "docs.google.com" and "/spreadsheets/" in parsed.path:
        return f"https://docs.google.com/spreadsheets/d/{identifier}/export?format=xlsx"
    if parsed.netloc == "docs.google.com" and "/document/" in parsed.path:
        return f"https://docs.google.com/document/d/{identifier}/export?format=docx"
    return url


def file_extension(data):
    if data.startswith(b"%PDF"):
        return ".pdf"
    if data.startswith(b"PK"):
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(data)) as archive:
            names = archive.namelist()
        if any(name.startswith("xl/") for name in names):
            return ".xlsx"
        if any(name.startswith("word/") for name in names):
            return ".docx"
    return ".html"


def local_stem(row):
    slug = re.sub(r"[^a-z0-9]+", "-", row["repository_school"].lower()).strip("-")
    return f"{slug}--{document_id(row['source_url'])}"


def existing_document(row):
    override = LOCAL_SOURCE_OVERRIDES.get(row["repository_school"])
    if override is not None and override.exists():
        return override
    matches = list(CDS_DIRECTORY.glob(local_stem(row) + ".*"))
    return matches[0] if matches else None


def fetch_document(row):
    existing = existing_document(row)
    if existing is not None:
        return existing
    request = Request(direct_download_url(row["source_url"]), headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        data = response.read()
    extension = file_extension(data)
    target = CDS_DIRECTORY / (local_stem(row) + extension)
    partial = target.with_suffix(target.suffix + ".part")
    partial.write_bytes(data)
    partial.replace(target)
    return target


def fetch_all(rows, workers=16):
    CDS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    failures = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        jobs = {executor.submit(fetch_document, row): row for row in rows}
        completed = 0
        for job in as_completed(jobs):
            row = jobs[job]
            try:
                job.result()
            except Exception as error:
                failures[row["repository_school"]] = str(error)
            completed += 1
            print(f"fetched {completed}/{len(rows)}", end="\r", flush=True)
    print()
    return failures


def pdf_text(path):
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def xlsx_text(path):
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in root.findall(namespace + "si")]
        lines = []
        sheets = sorted(name for name in archive.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name))
        for sheet in sheets:
            root = ET.fromstring(archive.read(sheet))
            for row in root.iter(namespace + "row"):
                values = []
                for cell in row.findall(namespace + "c"):
                    value = cell.find(namespace + "v")
                    if value is None:
                        values.append("".join(cell.itertext()))
                    elif cell.get("t") == "s":
                        values.append(shared[int(value.text)])
                    else:
                        values.append(value.text or "")
                lines.append("\t".join(values))
    return "\n".join(lines)


def docx_text(path):
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    lines = []
    for node in root.iter():
        if node.tag in {namespace + "p", namespace + "tr"}:
            text = " ".join("".join(node.itertext()).split())
            if text:
                lines.append(text)
    return "\n".join(lines)


def document_text(path):
    if path.suffix == ".pdf":
        return pdf_text(path)
    if path.suffix == ".xlsx":
        return xlsx_text(path)
    if path.suffix == ".docx":
        return docx_text(path)
    return path.read_text(encoding="utf-8", errors="ignore")


def normalize_extracted_text(text):
    """Repair common PDF ligature breaks without changing numeric data."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[‐‑‒–—]", "-", text)
    replacements = {
        r"\bfirst-\s*me\b": "first-time",
        r"\bgradua\s+ng\b": "graduating",
        r"\bbo\s+om\b": "bottom",
        r"\bsubmi\s+ed\b": "submitted",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def document_identity_matches(school, text):
    """Reject repository links that point to a different institution."""
    return normalize_school(school) in normalize_school(text[:6000])


def c10_block(text):
    start = None
    for section in re.finditer(r"^\s*C10[.:]?", text, flags=re.MULTILINE):
        sample = text[section.start():section.start() + 1500]
        if re.search(r"Percent in top tenth|Top\s+10%", sample, re.IGNORECASE):
            start = section.start()
            break
    if start is None:
        return ""
    end_match = re.search(r"\bC11\b", text[start + 1:])
    end = start + 1 + end_match.start() if end_match else start + 2500
    return text[start:end]


def percentage_after_label(block, labels):
    """Read a value on its label's line without stealing the 100% note."""
    for raw_line in block.splitlines():
        line = " ".join(raw_line.split())
        line = re.sub(r"Top half \+.*$", "", line, flags=re.IGNORECASE)
        line = re.sub(r"bottom half\s*=\s*100%.*$", "", line, flags=re.IGNORECASE)
        for label in labels:
            match = re.search(
                label + r"\s*[:_]*\s*(\d+(?:\.\d+)?)\s*%?",
                line,
                flags=re.IGNORECASE,
            )
            if match:
                return float(match.group(1))
    return None


def reporting_percentage(block):
    normalized = " ".join(block.split())
    patterns = (
        r"Percent(?:age)? of (?:total )?first-time, first-year.*?"
        r"(?:submitted|had).*?high school.*?class rank[_\s:]*"
        r"(\d+(?:\.\d+)?)\s*%?",
        r"Percent(?:age)? of (?:total )?first-time, first-year.*?"
        r"students who submitted high school\s+(\d+(?:\.\d+)?)\s*%\s+class rank",
        r"Percent(?:age)? of (?:total )?first-time, first-year.*?students\s+"
        r"(\d+(?:\.\d+)?)\s*%\s+who submitted high school class rank",
        r"students who submitted\s+(\d+(?:\.\d+)?)\s*%?\s*"
        r"high school class rank",
        r"students who submitted high school class rank\s*:?\s*"
        r"(\d+(?:\.\d+)?)\s*%?",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    for raw_line in block.splitlines():
        line = " ".join(raw_line.split())
        match = re.search(
            r"Percent(?:age)? of (?:total )?first-time, first-year.*?students\s+"
            r"(\d+(?:\.\d+)?)\s*%",
            line,
            flags=re.IGNORECASE,
        )
        if match:
            return float(match.group(1))
    return None


def complete_rank_values(values):
    """Fill only complements or boundaries logically implied by C10."""
    values = dict(values)
    if values["top_50_pct"] is None and values["bottom_50_pct"] is not None:
        values["top_50_pct"] = 100 - values["bottom_50_pct"]
    if values["bottom_50_pct"] is None and values["top_50_pct"] is not None:
        values["bottom_50_pct"] = 100 - values["top_50_pct"]
    if (
        values["top_50_pct"] is None
        and values["bottom_50_pct"] is None
        and values["top_25_pct"] == 100
    ):
        values["top_50_pct"] = 100
        values["bottom_50_pct"] = 0
    if values["bottom_25_pct"] is None and values["bottom_50_pct"] == 0:
        values["bottom_25_pct"] = 0
    return values


def cdf_anchors(values):
    """Convert cumulative top-rank shares to an ability-percentile CDF."""
    anchors = [(0.0, 0.0)]
    if values["bottom_25_pct"] is not None:
        anchors.append((25.0, values["bottom_25_pct"]))
    anchors.extend((
        (50.0, values["bottom_50_pct"]),
        (75.0, 100 - values["top_25_pct"]),
        (90.0, 100 - values["top_10_pct"]),
        (100.0, 100.0),
    ))
    for (_, lower), (_, upper) in zip(anchors, anchors[1:]):
        if lower > upper + 1.1:
            raise ValueError(f"Invalid C10 cumulative distribution: {values}")
    return [(score, max(0.0, min(100.0, cdf))) for score, cdf in anchors]


def distribution_quantile(anchors, probability):
    target = 100 * probability
    for (lower_score, lower_cdf), (upper_score, upper_cdf) in zip(anchors, anchors[1:]):
        if target <= upper_cdf and upper_cdf > lower_cdf:
            fraction = (target - lower_cdf) / (upper_cdf - lower_cdf)
            return lower_score + fraction * (upper_score - lower_score)
    return 100.0


def distribution_statistics(values):
    anchors = cdf_anchors(values)
    mean = sum(
        (upper_cdf - lower_cdf) * (lower_score + upper_score) / 2
        for (lower_score, lower_cdf), (upper_score, upper_cdf)
        in zip(anchors, anchors[1:])
    ) / 100
    return {
        "class_rank_q25": distribution_quantile(anchors, 0.25),
        "class_rank_median": distribution_quantile(anchors, 0.50),
        "class_rank_q75": distribution_quantile(anchors, 0.75),
        "class_rank_mean": mean,
    }


def extract_c10(path):
    block = c10_block(normalize_extracted_text(document_text(path)))
    if not block:
        return None
    values = complete_rank_values({
        key: percentage_after_label(block, labels)
        for key, labels in RANK_LABELS.items()
    })
    required = ("top_10_pct", "top_25_pct", "top_50_pct", "bottom_50_pct")
    complete = not any(values[key] is None for key in required)
    consistent = complete and abs(
        values["top_50_pct"] + values["bottom_50_pct"] - 100
    ) <= 1.1
    statistics = {
        key: ""
        for key in ("class_rank_q25", "class_rank_median", "class_rank_q75", "class_rank_mean")
    }
    if consistent:
        statistics = distribution_statistics(values)
    return {
        **values,
        "rank_reporting_pct": reporting_percentage(block),
        **statistics,
    }


def normalize_school(name):
    name = name.lower().replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", name).split())


def top_sample_rows(rows, count=10):
    """Top freshman-score schools, then top nonduplicate ability schools."""
    rows = list(rows)
    freshman = sorted(
        (row for row in rows if row["freshman_score"] != ""),
        key=lambda row: (-float(row["freshman_score"]), row["school"]),
    )[:count]
    used = {row["school"] for row in freshman}
    ability_rows = sorted(
        (
            row for row in rows
            if row["ability"] != "" and row["school"] not in used
        ),
        key=lambda row: (-float(row["ability"]), row["school"]),
    )[:count]
    return freshman + ability_rows


def top_sample_from_tsv(path=SCHOOL_TABLE):
    with path.open(encoding="utf-8", newline="") as source:
        return top_sample_rows(csv.DictReader(source, delimiter="\t"))


def target_repository_rows(repository, targets):
    by_name = {normalize_school(row["repository_school"]): row for row in repository}
    return [
        by_name[normalize_school(target["school"])]
        for target in targets
        if normalize_school(target["school"]) in by_name
    ]


def match_school(name, graduates):
    normalized = normalize_school(name)
    exact = [row for row in graduates if normalize_school(row["institution"]) == normalized]
    if len(exact) == 1:
        return exact[0]
    prefixed = [
        row for row in graduates
        if normalize_school(row["institution"]).startswith(normalized + " ")
    ]
    on_campus = [
        row for row in prefixed
        if not {"digital", "online"} & set(normalize_school(row["institution"]).split())
    ]
    if len(on_campus) == 1:
        return on_campus[0]
    candidates = sorted(
        ((SequenceMatcher(None, normalized, normalize_school(row["institution"])).ratio(), row) for row in graduates),
        key=lambda pair: pair[0],
        reverse=True,
    )
    if candidates[0][0] >= 0.94 and candidates[0][0] - candidates[1][0] >= 0.03:
        return candidates[0][1]
    return None


def score_lookup(graduates, target_unitids, repository=None):
    """Return parsed C10 results keyed by matched IPEDS institution."""
    if repository is None:
        repository = repository_rows()
    output = {}
    for source in repository:
        path = existing_document(source)
        text = document_text(path) if path is not None else ""
        valid_source = path is not None and (
            source["repository_school"] in LOCAL_SOURCE_OVERRIDES
            or document_identity_matches(source["repository_school"], text)
        )
        result = extract_c10(path) if valid_source else None
        if result is None:
            continue
        school = match_school(source["repository_school"], graduates)
        if (
            school is not None
            and school["unitid"] in target_unitids
            and result["class_rank_mean"] != ""
        ):
            output[school["unitid"]] = result
    return output


def scored_rows(repository, graduates, admissions):
    output = []
    for source in repository:
        path = existing_document(source)
        text = document_text(path) if path is not None else ""
        valid_source = path is not None and (
            source["repository_school"] in LOCAL_SOURCE_OVERRIDES
            or document_identity_matches(source["repository_school"], text)
        )
        result = extract_c10(path) if valid_source else None
        school = match_school(source["repository_school"], graduates)
        admission = admissions.get(school["unitid"], {}) if school else {}
        reporting = result.get("rank_reporting_pct") if result else None
        entrants = pathways.number(admission.get("ENRLT"))
        if path is None:
            status = "download failed"
        elif not valid_source:
            status = "source identity mismatch"
        elif result is None:
            status = "downloaded; C10 unavailable"
        elif result["class_rank_mean"] == "":
            status = "partial C10; insufficient for mean"
        else:
            status = "scored"
        output.append({
            "unitid": school["unitid"] if school else "",
            "school": school["institution"] if school else source["repository_school"],
            "repository_school": source["repository_school"],
            "cds_year": "2019-20",
            **(result or {key: "" for key in (*RANK_LABELS, "rank_reporting_pct", "class_rank_q25", "class_rank_median", "class_rank_q75", "class_rank_mean")}),
            "rank_reporting_freshmen_estimate": (
                entrants * reporting / 100 if entrants and reporting is not None else ""
            ),
            "bachelors_2023": school["bachelors_domestic"] if school else "",
            "source_url": source["source_url"],
            "source_file": str(path.relative_to(ROOT)) if path else "",
            "status": status,
        })
    return output


def load_graduates():
    return pathways.graduate_rows(
        pathways.load_directory(),
        pathways.load_completions(),
        pathways.load_outcomes(),
        pathways.load_enrollment(),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    if args.fetch and not REPOSITORY_HTML.exists():
        fetch_repository_index()
    all_repository = repository_rows()
    targets = top_sample_from_tsv()
    repository = target_repository_rows(all_repository, targets)
    failures = fetch_all(repository, args.workers) if args.fetch else {}
    fetched = len(repository) - len(failures) if args.fetch else 0
    rows = scored_rows(repository, load_graduates(), ability.load_admissions())
    indexed = {normalize_school(row["repository_school"]) for row in repository}
    for target in targets:
        if normalize_school(target["school"]) not in indexed:
            rows.append({
                "unitid": "",
                "school": target["school"],
                "repository_school": "",
                "cds_year": "2019-20",
                **{key: "" for key in (*RANK_LABELS, "rank_reporting_pct", "class_rank_q25", "class_rank_median", "class_rank_q75", "class_rank_mean")},
                "rank_reporting_freshmen_estimate": "",
                "bachelors_2023": target["bachelors"],
                "source_url": "",
                "source_file": "",
                "status": "not indexed for 2019-20",
            })
    pathways.write_tsv(pathways.DERIVED / "class_rank.tsv", rows)
    scored = [row for row in rows if row["status"] == "scored"]
    matched = [row for row in scored if row["unitid"] != ""]
    bachelors = sum(row["bachelors_2023"] for row in matched)
    print(
        f"targeted {len(targets):,}; indexed {len(repository):,}; "
        f"fetched this run {fetched:,}; "
        f"scored {len(scored):,}; matched {len(matched):,} institutions with "
        f"{bachelors:,.0f} domestic bachelor's awards"
    )
    if failures:
        print(f"download failures: {len(failures):,}")


if __name__ == "__main__":
    main()
