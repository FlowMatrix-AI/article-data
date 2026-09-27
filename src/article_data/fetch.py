"""Fetch raw sources by recorded URL and verify them against a recorded checksum.

Nothing here is committed: ``raw/`` is gitignored and rebuilt by ``article-data fetch``.
Each source records the URL it was pulled from, the SHA-256 of the bytes we got, and
the licence. A checksum mismatch is an error, not a warning: a silently changed
upstream file is exactly the case this exists to catch.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import requests

from article_data.paths import RAW

CHUNK = 1 << 20


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    filename: str
    sha256: str
    licence: str
    group: str
    md5: str | None = None  # publisher-stated checksum where one exists (figshare)

    def path(self, raw_dir: Path = RAW) -> Path:
        return raw_dir / self.group / self.filename


_EIA861 = "https://www.eia.gov/electricity/data/eia861/zip/f8612024.zip"
_ACS = "https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/"
_FIGSHARE = "https://ndownloader.figshare.com/files/"

# EAGLE-I archive, figshare article 24237376 v4 (doi:10.6084/m9.figshare.24237376.v4).
# (file id, year, figshare md5, sha256 of the bytes we downloaded)
_EAGLEI_YEARS = [
    (
        42547717,
        2014,
        "c7bfcf4b7fd26292f8d8801a26e8c52f",
        "f292a9f99066ac686df69767c535b218e70b4d4e748840ec620eda3340f914c9",
    ),
    (
        42547822,
        2015,
        "774d837e6a0d4f20aab5c82448538d37",
        "49de89b3427d564efbd9c80183caf4e9777966f7e319d4b30d682c1c0d064505",
    ),
    (
        42547825,
        2016,
        "8e4e85e81db474a708278aabef1198ec",
        "2c1b364a3b06aee56326174c4644750ea86ba9be4585c5e40eeb7835431bfc9c",
    ),
    (
        42547828,
        2017,
        "4faaeeb3b3e8e2d13d0e9238617ce3ce",
        "47479c4fd645ec69685447f90baa51f08a85e776cedf612279b3e41c13147c8d",
    ),
    (
        42547879,
        2018,
        "726543e4a392e220108b035ba4c52e43",
        "85e0a864aa272e75892e181f1da4754ed78f7bf0bef75a279d8ab381baa7db70",
    ),
    (
        42547885,
        2019,
        "0ff77af0106486eb7bdc6c5051bd916a",
        "4cc277a138b326bd0e1f203558539a9422b40dacdf439e3d5b58ee71d7462d27",
    ),
    (
        42547894,
        2020,
        "3b1e76e7ff0445da2b9a2fe4819c0e88",
        "2a20b62e5245b1b9d4fcedc1bdbaf691bb1e17f75094975c8c6cb854f52e721a",
    ),
    (
        42547891,
        2021,
        "b5a5912be793ca22dddcc73ca2c3379d",
        "e3e7ac40a40d92d92488501881ab381b8931833e486941424ac55ea20ffde319",
    ),
    (
        42547897,
        2022,
        "0cd04f23ac90ec4ec20ce3a63dcfa25a",
        "ff8b58ae30fcbaf290f820bcd4f1420e536994bc9f0a87bb80991130478461b0",
    ),
    (
        44574907,
        2023,
        "4ef3f9290884b4151a43333d28f67369",
        "c028f42dae8522ecfb787ad0b6461cfc809bb04856eef20cb389e486d5657f7e",
    ),
    (
        53581661,
        2024,
        "13183facf56c196c061a238303c87973",
        "d5d75ea4ef3943446aaf0623e9b451cb4e7796d20cc379de9cf497106ebab2e6",
    ),
    (
        62164877,
        2025,
        "cd2feb1282a42fb048cb6885398bc1cc",
        "4148a4a3b26e58024403cef98ccb324d1656f476613d6afff4451e33faf468c9",
    ),
]

SOURCES: dict[str, Source] = {
    "eia861_2024": Source(
        name="eia861_2024",
        url=_EIA861,
        filename="f8612024.zip",
        sha256="77ce49c60ac5a6bad50c442fc401aad5404a21da875dc5cbaba353af5ede54de",
        licence="US EIA, public domain",
        group="eia861",
    ),
    "acs2023_b25075": Source(
        name="acs2023_b25075",
        url=_ACS + "data/5YRData/acsdt5y2023-b25075.dat",
        filename="acsdt5y2023-b25075.dat",
        sha256="892f28cee110dd38d4416e13ec8e584cf6311b507f3c5d77d1ca8cb093504a09",
        licence="US Census Bureau, public domain",
        group="acs",
    ),
    "acs2023_b25032": Source(
        name="acs2023_b25032",
        url=_ACS + "data/5YRData/acsdt5y2023-b25032.dat",
        filename="acsdt5y2023-b25032.dat",
        sha256="93ddacf8fd0459117e0392ff96e9539c645bdeac4337b0be90a3fb950810fd6e",
        licence="US Census Bureau, public domain",
        group="acs",
    ),
    "acs2023_geos": Source(
        name="acs2023_geos",
        url=_ACS + "documentation/Geos20235YR.txt",
        filename="Geos20235YR.txt",
        sha256="f019d5c157e2f4083b2d5e8af116825d7b129cfe57e6fa65b6e6ce615cb564b1",
        licence="US Census Bureau, public domain",
        group="acs",
    ),
}
SOURCES.update(
    {
        f"eaglei_{year}": Source(
            name=f"eaglei_{year}",
            url=f"{_FIGSHARE}{fid}",
            filename=f"eaglei_outages_{year}.csv",
            sha256=sha,
            md5=md5,
            licence="ORNL EAGLE-I via figshare, CC BY 4.0",
            group="eaglei",
        )
        for fid, year, md5, sha in _EAGLEI_YEARS
    }
)

GROUPS: dict[str, list[str]] = {
    "eia861": ["eia861_2024"],
    "acs": ["acs2023_b25075", "acs2023_b25032", "acs2023_geos"],
    "eaglei": [f"eaglei_{y}" for _, y, _, _ in _EAGLEI_YEARS],
}


class ChecksumMismatch(RuntimeError):
    pass


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def resolve(names: list[str]) -> list[Source]:
    """Expand group names and source names into sources; unknown names raise."""
    out: list[Source] = []
    for name in names:
        if name in GROUPS:
            out.extend(SOURCES[n] for n in GROUPS[name])
        elif name in SOURCES:
            out.append(SOURCES[name])
        else:
            raise KeyError(f"unknown source {name!r}; known: {sorted(SOURCES)} or {sorted(GROUPS)}")
    return out


def fetch(source: Source, raw_dir: Path = RAW, *, force: bool = False) -> Path:
    """Download ``source`` unless a verified copy is already present.

    Streams to ``<file>.part`` and renames only after the checksum matches, so a
    partial or tampered download never sits under the final name.
    """
    dest = source.path(raw_dir)
    if dest.exists() and not force:
        if sha256_of(dest) == source.sha256:
            return dest
        dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    with requests.get(source.url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with part.open("wb") as f:
            for chunk in r.iter_content(CHUNK):
                f.write(chunk)
    got = sha256_of(part)
    if got != source.sha256:
        part.unlink()
        raise ChecksumMismatch(f"{source.name}: sha256 {got} != recorded {source.sha256}")
    part.replace(dest)
    return dest
