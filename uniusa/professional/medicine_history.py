"""Historical MCAT estimates using freshman cohorts four years earlier.

This is the freshman-score history model, not the present-day graduate/transfer
model. Applicant-origin weights remain the observed 2023 AAMC weights. Use a
common set of feeder schools across years so missing scores do not change the
composition of the calibration population.
"""

from statistics import median

from uniability.xlsx import rows as xlsx_rows
from uniusa import ability, calibrate_tests, pathways, school_distributions
from uniusa.intake_curve import IQR_Z
from uniusa.professional import common, medicine


FRESHMAN_LAG = 4
STUDY_SOURCE = common.SOURCES / "nyu-medicine-2006-2014.xlsx"
STUDY_URL = "https://doi.org/10.1371/journal.pone.0227108.s003"


def study_observations(path=STUDY_SOURCE, years=(2013, 2014)):
    """Aggregate published de-identified NYU study cohorts, not whole classes.

    The paper describes these as matriculation cohorts; its workbook calls the
    cohort field 'Application year'. The supplied percentiles already refer to
    the old MCAT, so do not feed them into the new 472–528 score table.
    """
    records = iter(xlsx_rows(path, sheet="xl/worksheets/sheet2.xml"))
    header = next(records)
    grouped = {year: [] for year in years}
    for values in records:
        row = dict(zip(header, values))
        year = int(row["Application year"])
        value = common.numeric(row["MCAT total percentile"])
        if year in grouped and value is not None:
            if not 0 < value < 100:
                raise ValueError(f"Invalid historical MCAT percentile: {value}")
            grouped[year].append(value)
    for year, values in grouped.items():
        if not values:
            raise ValueError(f"No observed NYU MCAT percentiles for {year}")
        yield {
            "entry_year": year, "school": "NYU Grossman School of Medicine",
            "mcat_percentile": median(values), "students": len(values),
            "source_url": STUDY_URL,
            "coverage": "Published NYU research cohort; not the full entering class",
        }


def freshman_distributions(year):
    """Annual school CDFs on the same test-taker scale as freshman history.

    Centers follow the existing mean-of-quartiles / median-of-routes rule.
    Normal-in-z spreads use that year's reported interquartile ranges. SAT
    tables are annual (CR + Math before 2016); the ACT reference stays fixed at
    2018, as in the undergraduate history. No current school median is reused.
    """
    sat = calibrate_tests.load_sat_total_user_percentiles(year)
    _, act = calibrate_tests.load_act_composite_percentiles()
    directory = pathways.load_directory()
    normal = school_distributions.NORMAL
    epsilon = school_distributions.MIN_PERCENTILE

    def z(value):
        return normal.inv_cdf(min(100 - epsilon, max(epsilon, value)) / 100)

    distributions = {}
    for unitid, row in ability.load_admissions(year).items():
        if unitid not in directory or pathways.number(row.get("ENRLT")) <= 0:
            continue
        routes = []
        for table, count_field, fields in (
            (sat, "SATNUM", (("SATVR25", "SATMT25"), ("SATVR75", "SATMT75"))),
            (act, "ACTNUM", (("ACTCM25",), ("ACTCM75",))),
        ):
            count = pathways.number(row.get(count_field))
            raw = [[pathways.number(row.get(field)) for field in edge] for edge in fields]
            if count <= 0 or not all(value > 0 for edge in raw for value in edge):
                continue
            low, high = [calibrate_tests.interpolate(table, sum(edge)) for edge in raw]
            if not low < high:
                continue
            routes.append(((low + high) / 2, (z(high) - z(low)) / IQR_Z, count))
        if routes:
            center = median(route[0] for route in routes)
            spread = sum(width * n for _, width, n in routes) / sum(n for _, _, n in routes)
            distributions[directory[unitid]["INSTNM"]] = (
                school_distributions.NormalSchoolDistribution(center, spread)
            )
    if not distributions:
        raise ValueError(f"No freshman score distributions for {year}")
    return distributions


def cohort_mixtures(entry_years, origins=None):
    """Return entry-year -> lagged mixture and its fixed feeder coverage."""
    origins = medicine.feeder_rows() if origins is None else origins
    years = sorted(set(int(year) for year in entry_years))
    distributions = {year: freshman_distributions(year - FRESHMAN_LAG) for year in years}
    common_schools = set.intersection(*(set(table) for table in distributions.values()))
    panel = [row for row in origins if row["school"] in common_schools]
    if not panel:
        raise ValueError("No common medical feeder schools across historical cohorts")
    coverage = sum(row["applicants"] for row in panel) / sum(row["applicants"] for row in origins)
    mixtures = {
        year: medicine.applicant_mixture(panel, table)
        for year, table in distributions.items()
    }
    return mixtures, {"feederSchools": len(panel), "feederCoverage": coverage,
                      "feederWeightYear": 2023, "actReferenceYear": 2018}


def estimate_observations(observations):
    """Keep entry dates untouched; lag only the underlying freshman inputs."""
    observations = list(observations)
    mixtures, metadata = cohort_mixtures(row["entry_year"] for row in observations)
    table = medicine.mcat_percentiles()
    points = []
    for row in observations:
        year = int(row["entry_year"])
        score = common.numeric(row.get("median_mcat"))
        percentile = common.numeric(row.get("mcat_percentile"))
        if percentile is None:
            if score is None or not min(table) <= score <= max(table):
                raise ValueError("MCAT needs an observed percentile or a supported new-scale score")
            percentile = common.interpolate(table, score)
        if not 0 < percentile < 100:
            raise ValueError(f"Invalid MCAT percentile: {percentile}")
        point = {
            "year": year, "ability": mixtures[year].quantile(percentile / 100),
            "seats": float(row["students"]), "school": row["school"],
            "freshmanYear": year - FRESHMAN_LAG, "mcatPercentile": percentile,
            "sourceUrl": row["source_url"],
            "coverage": row.get("coverage", "Published full entering class"),
        }
        if score is not None:
            point["mcat"] = score
        points.append(point)
    return points, metadata
