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
    "ADM2014.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/ADM2014.zip",
        "357eb2ad58f03b1085dbfc2a2a8f8ae00785dd3d8b5a40f612f66ced883256dc",
    ),
    "ADM2015.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/ADM2015.zip",
        "3d1a9f2c71d9cf4cffa3f00e0c9170daf7a7dc5691523e082a055c02ae34c8de",
    ),
    "ADM2016.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/ADM2016.zip",
        "e76aade20b306b7462bce392d4bed11ef2210c05174a6ef9bd40e6be555b7345",
    ),
    "ADM2019.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/ADM2019.zip",
        "908034d862377d3214f1e0395cdb34dd041049682c553d1fb391f9eda8196aa5",
    ),
    "ADM2019_Dict.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/ADM2019_Dict.zip",
        "c21b76d466305e7fb4fe82fd3403cd247c607a3558de3ef7fc66d457a396137c",
    ),
    "ADM2020.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/ADM2020.zip",
        "0cae5b25c7b973d4ad428a5442888a80968b2980201220cdcb1e9dab1162f696",
    ),
    "ADM2021.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/ADM2021.zip",
        "786b1343a2e407fc102cfbda11f1517456917bac221b1dca9232b60ee453db7e",
    ),
    "ADM2022.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/ADM2022.zip",
        "31cbfa5e68289525bff60e65b1094c610473ecc02d601461ae3875f854e2fde7",
    ),
    "ADM2023.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/ADM2023.zip",
        "670ecc7c4313f044dcdf740a42ef10c6d2927eb9f890fb405e3569c8442aca27",
    ),
    "ADM2017.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/ADM2017.zip",
        "3e92d1853aca4363ce89abeba8b0ef0237a6bc7b4a07b436d5ae5f38b61ac649",
    ),
    "ADM2018.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/ADM2018.zip",
        "0dffbbc32e2d15dd533ad704482af383be2ee3d4c1de038bc55aecedc2639359",
    ),
    "IC2019.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/IC2019.zip",
        "5f90c01bef16c0b058930c568a12dd068779399fdca76f45acbf2a758e652563",
    ),
    "IC2019_Dict.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/IC2019_Dict.zip",
        "69ba91d4d52840e5433e54dc2f825dad25d05768f707e399ae57961136297947",
    ),
    "EF2019A.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/EF2019A.zip",
        "6ad08d19451a5a777acff44623f992a250a730fc30388da73b1b74be418b3c24",
    ),
    "EF2019A_Dict.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/EF2019A_Dict.zip",
        "13974d784f123de116866c09bf002c6e6ade44367aad8548bcd115598d9f05cd",
    ),
    "EFFY2024.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/EFFY2024.zip",
        "fff28cbfaecbddd871f64dc958abbbd967f750ead7c699506efb47dc2ce8366f",
    ),
    "EFFY2024_Dict.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/EFFY2024_Dict.zip",
        "bf199f8d452ea53c02f0365489aeb7c99eaf51cf5774d6cb5306467ba8e1f981",
    ),
    "C2023_A_Dict.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/C2023_A_Dict.zip",
        "2738d0a2675f475e1c2bc92a63e7cea92b3caf5210d80f19eaf6a5523919f2e2",
    ),
    "OM2023.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/OM2023.zip",
        "60a619776e8da60542c9a728b2c2122bcdef6825c76b5b36a40ab243a5d0b504",
    ),
    "OM2023_Dict.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/OM2023_Dict.zip",
        "97009ef1706981902925a589b0804e20ce78a63489471093f463b3e99ca03852",
    ),
    "GR2023.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/GR2023.zip",
        "f00c7140d4dbbb056043689aa82835eec5f6101b907b047a2933372505fa54bd",
    ),
    "GR2023_Dict.zip": (
        "https://nces.ed.gov/ipeds/datacenter/data/GR2023_Dict.zip",
        "3af73a2b952262771f9a935e03d44f699c18cd3b00f01f713dfa298e48298f88",
    ),
    "SAT-national-percentiles.html": (
        "https://research.collegeboard.org/reports/sat-suite/"
        "understanding-scores/sat",
        "c88392bdaf865dac481a0c195e7339d645d177dc1f46462ef856d29305a18eea",
    ),
    "sat-percentile-1600.csv": (
        "https://docs.google.com/spreadsheets/d/e/"
        "2PACX-1vRVCIukssgc3z5-8GpH3achzkJhbxD0TID_q8Xa-1oZIsF_NMy-"
        "U5exxEUr8EZi2Q/pub?gid=273576492&single=true&output=csv",
        "ad23e1bb584e85e95702257a26d4b94178f25ca354e1e72206802338d579f35e",
    ),
    "2017-total-group-sat-report.pdf": (
        "https://reports.collegeboard.org/media/pdf/"
        "2017-total-group-sat-suite-assessments-annual-report.pdf",
        "938bc65a2a9fa11f82ba68c7bd28b64b1206585349bc9fa30883cf5b10b6e827",
    ),
    "2018-total-group-sat-report.pdf": (
        "https://reports.collegeboard.org/media/pdf/"
        "2018-total-group-sat-suite-assessments-annual-report.pdf",
        "250c8e6c92158f3efb4c6c19ef993f0723013ed9d94725e5dedd01b218f45c51",
    ),
    "2019-total-group-sat-report.pdf": (
        "https://reports.collegeboard.org/media/pdf/"
        "2019-total-group-sat-suite-assessments-annual-report.pdf",
        "55a088435042d9eb22dc0246b02624ae8e8218b82d84608ffe429887f3b0f1de",
    ),
    "2018-act-national-profile.pdf": (
        "https://www.act.org/content/dam/act/unsecured/documents/cccr2018/"
        "P_99_999999_N_S_N00_ACT-GCPR_National.pdf",
        "a8e819602d03be5897358456644aefbffd22207a138c67f8f0560573fa9fb3f2",
    ),
    "CIP2020-browse.html": (
        "https://nces.ed.gov/ipeds/cipcode/browse.aspx?y=56",
        "f4963a49fbb1b34b9e3eb2549ca59c36f69fbf676031edbc2c3fb95512d8223d",
    ),
}
COMPLETION_DIGESTS = {
    2014: "7e04c402ce870a9073e99aafc13eae1ae07d9d97eecf36689d9c42db1996d4c8",
    2015: "c1d54e7b5896ca3db2a5fadca00c149f76f2d2189e57749e8f4db716a266b489",
    2016: "7213f0b6521e9e1161acd6be867c4510b0256655c53c42f7f24fb4acdd3d4b4b",
    2017: "616eabf28a7e94beaf975d35d5f3aa5a446cc26195e5c5dcd1e8de68c0a69df4",
    2018: "24d100007bc3ff4a20aa43e447e8dac564db7118e81be264d803e694968cc9e3",
    2019: "ee267e2204f9bc8e356eee2bfe9496d8f764ae95ca9f14b850d4699c3e8df77e",
    2020: "f36abd6c3bc5b1bbd94bdc864d07fd60db3069522a58cfde4671b4280376ca05",
    2021: "69317e2afe7ad52f46bbf651f2408b8f5ae2ead5c74206b63554d6f0f1373244",
    2022: "f81b8390d1758ac710b85a1d5a7af51372770335a02c0d06802a46d3a068126c",
    2023: "651d95b6405bb86c6c14884ed54225a27492199d21d8acd63cda2581aa60838a",
}
SOURCES.update({
    name: (f"https://nces.ed.gov/ipeds/datacenter/data/{name}", digest)
    for year, digest in COMPLETION_DIGESTS.items()
    for name in (f"C{year}_A.zip",)
})


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
