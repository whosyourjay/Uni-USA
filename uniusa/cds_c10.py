"""Read Common Data Set section C10 and turn it into rank percentiles.

C10 reports the same five cumulative class-rank bins at every institution.
Spreading each bin's mass uniformly gives a CDF over rank percentile, which
yields q25, median, q75, and a mean.
"""

import re
import unicodedata


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
STATISTIC_FIELDS = (
    "class_rank_q25", "class_rank_median", "class_rank_q75", "class_rank_mean",
)
C10_FIELDS = (*RANK_LABELS, "rank_reporting_pct", *STATISTIC_FIELDS)
EMPTY_C10 = {field: "" for field in C10_FIELDS}


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


def extract_c10(text):
    block = c10_block(normalize_extracted_text(text))
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
    statistics = {key: "" for key in STATISTIC_FIELDS}
    if consistent:
        statistics = distribution_statistics(values)
    return {
        **values,
        "rank_reporting_pct": reporting_percentage(block),
        **statistics,
    }
