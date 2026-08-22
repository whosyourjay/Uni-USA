"""Convert between the native SAT/ACT-taker scale and an age cohort."""

from functools import lru_cache

from uniusa import pathways

ASSESSMENT = pathways.ROOT / "assessment-pool.tsv"


@lru_cache(maxsize=1)
def assessment_share(path=ASSESSMENT):
    rows = list(pathways.read_tsv(path))
    if len(rows) != 1:
        raise ValueError(f"Expected one assessment-pool row, found {len(rows)}")
    return min(float(rows[0]["B"]) / pathways.load_population(), 1.0)


def test_taker_percentile(cohort_percentile, share=None):
    """Invert the assumption that every non-taker sits below every taker."""
    if cohort_percentile == "":
        return ""
    share = assessment_share() if share is None else share
    return max(0.0, 100.0 * (1.0 - (1.0 - float(cohort_percentile) / 100.0) / share))


def cohort_percentile(taker_percentile, share=None):
    """Place a test-taker percentile above the non-taking population."""
    if taker_percentile == "":
        return ""
    share = assessment_share() if share is None else share
    return 100.0 * (1.0 - (1.0 - float(taker_percentile) / 100.0) * share)
