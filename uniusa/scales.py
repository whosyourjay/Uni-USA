"""Convert between the native SAT/ACT-taker scale and an age cohort."""

from functools import lru_cache

from uniability import cohort_to_pool, pool_to_cohort, read_scales

from uniusa import pathways

ASSESSMENT = pathways.ROOT / "assessment-pool.tsv"


@lru_cache(maxsize=1)
def assessment_scale(path=ASSESSMENT):
    return read_scales(pathways.read_tsv(path), "US")["pooled"]


def assessment_share(path=ASSESSMENT):
    return assessment_scale(path).share(pathways.load_population())


def test_taker_percentile(cohort_percentile, share=None):
    """Invert the assumption that every non-taker sits below every taker."""
    if cohort_percentile == "":
        return ""
    share = assessment_share() if share is None else share
    return cohort_to_pool(cohort_percentile, share)


def cohort_percentile(taker_percentile, share=None):
    """Place a test-taker percentile above the non-taking population."""
    if taker_percentile == "":
        return ""
    share = assessment_share() if share is None else share
    return pool_to_cohort(taker_percentile, share)
