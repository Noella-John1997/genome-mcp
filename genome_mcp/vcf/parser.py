"""A small, dependency-free VCF reader.

VCF (Variant Call Format) is a tab-separated text file. Header lines start
with '##' (metadata) and '#CHROM' (column names). Every other line is one
variant: where it is (CHROM, POS), what changed (REF -> ALT), how confident
the caller is (QUAL, FILTER) and each sample's genotype (GT).

For big real-world files use pysam/cyvcf2 (C-backed, indexed). This reader
streams line by line, so memory stays flat even for multi-GB files.
"""
from __future__ import annotations

import gzip
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


def normalize_chrom(chrom: str) -> str:
    """'chr17' and '17' mean the same chromosome; store without the prefix."""
    c = str(chrom)
    return c[3:] if c.lower().startswith("chr") else c


@dataclass
class Variant:
    chrom: str
    pos: int                  # 1-based position of the first REF base
    id: str
    ref: str
    alt: str                  # one ALT allele (multi-allelic lines are split)
    qual: float | None
    filter: str
    info: dict[str, str] = field(default_factory=dict)
    genotype: str = "./."     # e.g. "0/1"
    sample_fields: dict[str, str] = field(default_factory=dict)
    alt_index: int = 1        # which ALT this is in the original line (1-based)

    @property
    def key(self) -> str:
        return f"{self.chrom}:{self.pos}:{self.ref}:{self.alt}"

    @property
    def rsid(self) -> str | None:
        return self.id if self.id.startswith("rs") else None

    @property
    def kind(self) -> str:
        if len(self.ref) == 1 and len(self.alt) == 1:
            return "SNV"
        return "insertion" if len(self.alt) > len(self.ref) else "deletion" if len(self.alt) < len(self.ref) else "MNV"

    @property
    def passed(self) -> bool:
        return self.filter in ("PASS", ".")

    @property
    def alt_copies(self) -> int | None:
        """How many copies of THIS alt allele the sample carries (0, 1 or 2)."""
        alleles = self.genotype.replace("|", "/").split("/")
        if any(a == "." for a in alleles):
            return None
        return sum(1 for a in alleles if a == str(self.alt_index))

    @property
    def zygosity(self) -> str:
        alleles = self.genotype.replace("|", "/").split("/")
        if any(a == "." for a in alleles):
            return "no call"
        n = self.alt_copies or 0
        if n == 0:
            return "homozygous reference" if len(set(alleles)) == 1 else "heterozygous (other allele)"
        if n == len(alleles):
            return "homozygous alternate"
        return "heterozygous"

    def to_dict(self) -> dict:
        return {"chrom": self.chrom, "pos": self.pos, "id": self.id, "ref": self.ref, "alt": self.alt,
                "type": self.kind, "qual": self.qual, "filter": self.filter, "genotype": self.genotype,
                "zygosity": self.zygosity, "depth": self.sample_fields.get("DP")}


class VCFReader:
    def __init__(self, path: str | Path, sample: str | None = None):
        self.path = Path(path)
        self.meta: list[str] = []
        self.samples: list[str] = []
        self._sample_idx = 0
        self._read_header()
        if sample:
            if sample not in self.samples:
                raise ValueError(f"sample {sample!r} not in VCF (have {self.samples})")
            self._sample_idx = self.samples.index(sample)

    @property
    def sample(self) -> str | None:
        return self.samples[self._sample_idx] if self.samples else None

    def _open(self) -> io.TextIOBase:
        if self.path.suffix == ".gz":
            return io.TextIOWrapper(gzip.open(self.path, "rb"), encoding="utf-8")
        return self.path.open(encoding="utf-8")

    def _read_header(self) -> None:
        with self._open() as f:
            for line in f:
                if line.startswith("##"):
                    self.meta.append(line.rstrip("\n"))
                elif line.startswith("#CHROM"):
                    cols = line.rstrip("\n").split("\t")
                    self.samples = cols[9:]
                    return
                else:
                    break
        raise ValueError(f"{self.path} is not a valid VCF (no #CHROM header line)")

    @property
    def reference(self) -> str | None:
        for m in self.meta:
            if m.startswith("##reference="):
                return m.split("=", 1)[1]
        return None

    def __iter__(self) -> Iterator[Variant]:
        with self._open() as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                yield from self._parse_line(line.rstrip("\n"))

    def _parse_line(self, line: str) -> Iterator[Variant]:
        cols = line.split("\t")
        if len(cols) < 8:
            raise ValueError(f"malformed VCF line: {line[:80]}")
        chrom, pos, vid, ref, alts, qual, filt, info = cols[:8]
        info_d: dict[str, str] = {}
        for item in info.split(";"):
            if item and item != ".":
                k, _, v = item.partition("=")
                info_d[k] = v or "true"
        gt, sf = "./.", {}
        if len(cols) > 9:
            fmt = cols[8].split(":")
            vals = cols[9 + self._sample_idx].split(":")
            sf = dict(zip(fmt, vals))
            gt = sf.get("GT", "./.")
        for i, alt in enumerate(alts.split(","), start=1):
            yield Variant(normalize_chrom(chrom), int(pos), vid, ref, alt,
                          None if qual == "." else float(qual), filt, info_d, gt, sf, i)

    def region(self, chrom: str, start: int, end: int, pass_only: bool = False) -> list[Variant]:
        c = normalize_chrom(chrom)
        return [v for v in self if v.chrom == c and start <= v.pos <= end and (v.passed or not pass_only)]
