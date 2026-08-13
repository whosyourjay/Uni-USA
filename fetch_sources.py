#!/usr/bin/env python3
"""Download the small, fixed source bundle used by the USA pathway analysis."""

import hashlib
from pathlib import Path
from urllib.request import urlopen

SOURCES = {
    "nc-est2023-agesex-res.csv": (
        "https://www2.census.gov/programs-surveys/popest/datasets/"
        "2020-2023/national/asrh/nc-est2023-agesex-res.csv",
        "6e28235ceb27beaf630dc1d98370c41c66e5a1cab7eb6f657a70ed7446c1b67a",
    ),
    "HD2023.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/HD2023.zip",
        "e11d35af6f50fbe2f51d8ddd5a9d4f49860abbab7d73beae1f8524f13ad8945b",
    ),
    "ADM2023.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/ADM2023.zip",
        "670ecc7c4313f044dcdf740a42ef10c6d2927eb9f890fb405e3569c8442aca27",
    ),
    "EFFY2024.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/EFFY2024.zip",
        "fff28cbfaecbddd871f64dc958abbbd967f750ead7c699506efb47dc2ce8366f",
    ),
    "EFFY2024_Dict.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/EFFY2024_Dict.zip",
        "bf199f8d452ea53c02f0365489aeb7c99eaf51cf5774d6cb5306467ba8e1f981",
    ),
}


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def download(name, url, expected, directory):
    target = directory / name
    if target.exists() and digest(target) == expected:
        print(f"ok       {name}")
        return
    partial = target.with_suffix(target.suffix + ".part")
    print(f"download {name}")
    with urlopen(url) as response, partial.open("wb") as output:
        for block in iter(lambda: response.read(1024 * 1024), b""):
            output.write(block)
    actual = digest(partial)
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch for {name}: {actual}")
    partial.replace(target)


def main():
    directory = Path(__file__).parent / "sources"
    directory.mkdir(exist_ok=True)
    for name, (url, expected) in SOURCES.items():
        download(name, url, expected, directory)


if __name__ == "__main__":
    main()
