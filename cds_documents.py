"""Locate, download, and read the text of institution-published Common Data Sets.

College Transitions maintains a centralized index of CDS files.  Each row links
one institution and year to a document hosted somewhere else, usually Google
Drive.  Everything here stops at plain text; nothing interprets the contents.
"""

import hashlib
import html
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from io import BytesIO
import re
import subprocess
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import zipfile

import pathways


REPOSITORY_URL = (
    "https://www.collegetransitions.com/dataverse/"
    "common-data-set-repository/"
)
REPOSITORY_HTML = pathways.SOURCES / "common-data-set-repository.html"
REPOSITORY_TABLE_ID = "footable_22584"
ENTERING_CLASS_HTML = pathways.SOURCES / "entering-class-statistics.html"
ENTERING_CLASS_TABLE_ID = "footable_22840"
CDS_YEAR_COLUMNS = {
    "2024-25": 1,
    "2023-24": 2,
    "2022-23": 3,
    "2021-22": 4,
    "2020-21": 5,
    "2019-20": 6,
    "2018-19": 7,
    "2017-18": 8,
}
CDS_YEAR = "2019-20"
LOCAL_SOURCE_OVERRIDES = {
    "Carnegie Mellon University": pathways.SOURCES / "cds-2019-carnegie-mellon.pdf",
    "Harvey Mudd College": pathways.SOURCES / "cds-2019-harvey-mudd.pdf",
}


class TableParser(HTMLParser):
    """Read one identified HTML table into rows of `{"text", "href"}` cells."""

    CELLS = ("td", "th")

    def __init__(self, table_id):
        super().__init__()
        self.table_id = table_id
        self.in_table = False
        self.row = None
        self.cell = None
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "table" and attributes.get("id") == self.table_id:
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.row = []
        elif self.row is not None and tag in self.CELLS:
            self.cell = {"text": [], "href": ""}
        elif self.cell is not None and tag == "a":
            self.cell["href"] = attributes.get("href", "")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"].append(data)

    def handle_endtag(self, tag):
        if tag in self.CELLS and self.cell is not None:
            self.cell["text"] = " ".join("".join(self.cell["text"]).split())
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row:
            self.rows.append(self.row)
            self.row = None
        elif tag == "table" and self.in_table:
            self.in_table = False


def table_rows(path, table_id):
    parser = TableParser(table_id)
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    return parser.rows


def unwrap_repository_url(url):
    url = html.unescape(url)
    if urlparse(url).netloc == "www.google.com":
        url = parse_qs(urlparse(url).query).get("q", [""])[0]
    return unquote(url)


def cds_directory(year=CDS_YEAR):
    return pathways.SOURCES / f"cds-{year[:4]}"


def repository_rows(path=REPOSITORY_HTML, year=CDS_YEAR):
    column = CDS_YEAR_COLUMNS[year]
    output = []
    for cells in table_rows(path, REPOSITORY_TABLE_ID):
        if len(cells) <= column:
            continue
        url = unwrap_repository_url(cells[column]["href"])
        if url.startswith("https://"):
            output.append({
                "repository_school": cells[0]["text"],
                "source_url": url,
                "cds_year": year,
            })
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
    directory = cds_directory(row.get("cds_year", CDS_YEAR))
    matches = list(directory.glob(local_stem(row) + ".*"))
    return matches[0] if matches else None


def fetch_document(row):
    existing = existing_document(row)
    if existing is not None:
        return existing
    request = Request(
        direct_download_url(row["source_url"]), headers={"User-Agent": "Mozilla/5.0"}
    )
    with urlopen(request, timeout=30) as response:
        data = response.read()
    extension = file_extension(data)
    directory = cds_directory(row.get("cds_year", CDS_YEAR))
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (local_stem(row) + extension)
    partial = target.with_suffix(target.suffix + ".part")
    partial.write_bytes(data)
    partial.replace(target)
    return target


def fetch_all(rows, workers=16):
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
            shared = [
                "".join(node.itertext()) for node in root.findall(namespace + "si")
            ]
        lines = []
        sheets = sorted(
            name for name in archive.namelist()
            if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)
        )
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
