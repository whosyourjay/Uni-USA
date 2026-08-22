#!/usr/bin/env python3
"""Visualize the modeled age-18 ability distribution of MD applicants."""

from html import escape
import subprocess

from uniusa import pathways
from uniusa.professional import medicine

OUTPUT = pathways.DERIVED / "medical-applicants.svg"
PNG_OUTPUT = pathways.DERIVED / "medical-applicants.png"
BANDS = (
    ("0–50", 0, 50),
    ("50–75", 50, 75),
    ("75–90", 75, 90),
    ("90–95", 90, 95),
    ("95–99", 95, 99),
    ("99–99.5", 99, 99.5),
    ("99.5–99.9", 99.5, 99.9),
    ("99.9–100", 99.9, 100),
)
QUANTILES = (50, 75, 90, 95, 99)


def applicant_summary():
    origins = medicine.feeder_rows()
    mixture = medicine.applicant_mixture(origins)
    bands = [
        (label, 100 * (mixture.cdf(high) - mixture.cdf(low)))
        for label, low, high in BANDS
    ]
    quantiles = [
        (quantile, mixture.quantile(quantile / 100))
        for quantile in QUANTILES
    ]
    coverage = mixture.weight / sum(row["applicants"] for row in origins)
    return mixture, bands, quantiles, coverage


def bar_svg(label, share, index, maximum):
    left, top, width, height = 94, 190, 790, 405
    gap = 13
    bar_width = (width - gap * (len(BANDS) - 1)) / len(BANDS)
    x = left + index * (bar_width + gap)
    bar_height = height * share / maximum
    y = top + height - bar_height
    color = "#94a3b8" if index == 0 else "#2563eb"
    return f"""
      <rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}"
            rx="6" fill="{color}"/>
      <text x="{x + bar_width / 2:.1f}" y="{y - 11:.1f}" text-anchor="middle"
            class="value">{share:.1f}%</text>
      <text x="{x + bar_width / 2:.1f}" y="{top + height + 29:.1f}" text-anchor="middle"
            class="band">{escape(label)}</text>"""


def quantile_svg(quantile, ability, index):
    y = 254 + index * 67
    return f"""
      <text x="985" y="{y}" class="quantile">{quantile}th applicant percentile</text>
      <text x="1280" y="{y}" text-anchor="end" class="ability">{ability:.3f}</text>
      <line x1="985" y1="{y + 17}" x2="1280" y2="{y + 17}" stroke="#dbeafe"/>"""


def render(mixture, bands, quantiles, coverage):
    maximum = max(share for _, share in bands) * 1.12
    bars = "".join(
        bar_svg(label, share, index, maximum)
        for index, (label, share) in enumerate(bands)
    )
    ladder = "".join(
        quantile_svg(quantile, ability, index)
        for index, (quantile, ability) in enumerate(quantiles)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="820"
      viewBox="0 0 1400 820">
    <style>
      text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #172033; }}
      .title {{ font-size: 35px; font-weight: 700; }}
      .subtitle {{ font-size: 18px; fill: #526079; }}
      .section {{ font-size: 19px; font-weight: 650; }}
      .value {{ font-size: 16px; font-weight: 650; }}
      .band {{ font-size: 14px; fill: #526079; }}
      .quantile {{ font-size: 16px; fill: #526079; }}
      .ability {{ font-size: 23px; font-weight: 700; fill: #1d4ed8; }}
      .note {{ font-size: 15px; fill: #64748b; }}
    </style>
    <rect width="1400" height="820" fill="#f8fafc"/>
    <text x="70" y="70" class="title">Estimated age-18 ability of U.S. MD applicants</text>
    <text x="70" y="105" class="subtitle">AAMC feeder weights; school Q50 and observed SAT/ACT interquartile spread</text>
    <text x="70" y="158" class="section">Share of applicants by age-18 percentile band</text>
    <line x1="94" y1="595" x2="884" y2="595" stroke="#94a3b8"/>
    {bars}
    <rect x="945" y="158" width="380" height="422" rx="18" fill="#ffffff" stroke="#dbeafe"/>
    <text x="985" y="209" class="section">Applicant distribution cutoffs</text>
    {ladder}
    <text x="70" y="754" class="note">Coverage: {mixture.weight:,.0f} applicants with matched undergraduate estimates</text>
    <text x="70" y="779" class="note">({coverage:.1%} of applicants in AAMC's published feeder table).</text>
    </svg>"""


def main():
    mixture, bands, quantiles, coverage = applicant_summary()
    OUTPUT.write_text(render(mixture, bands, quantiles, coverage), encoding="utf-8")
    subprocess.run(
        ["magick", str(OUTPUT), str(PNG_OUTPUT)],
        check=True,
    )
    print(f"wrote {OUTPUT} and {PNG_OUTPUT}: {mixture.weight:,.0f} modeled applicants")


if __name__ == "__main__":
    main()
