"""National SAT and ACT population counts used by the intake model."""

from functools import lru_cache
import re
import subprocess

from uniusa import calibrate_tests, pathways


YEARS = (2017, 2018, 2019)


@lru_cache(maxsize=None)
def national_sat_takers(year):
    path = pathways.SOURCES / f"{year}-total-group-sat-report.pdf"
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    compact = "".join(result.stdout.split())
    counts = re.findall(r"\d{1,3}(?:,\d{3}){2}", compact)
    if not counts:
        raise ValueError(f"Could not find SAT test-taker count in {path.name}")
    total = int(counts[0].replace(",", ""))
    if not 1_000_000 < total < 3_000_000:
        raise ValueError(f"Implausible SAT test-taker count: {total:,}")
    return total


@lru_cache(maxsize=None)
def national_act_counts(year):
    counts, _ = calibrate_tests.load_act_composite_percentiles(
        calibrate_tests.nearest_act_year(year)
    )
    return counts
