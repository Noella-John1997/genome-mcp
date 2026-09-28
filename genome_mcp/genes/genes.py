"""Gene coordinate lookups (gene name <-> genomic region)."""
from __future__ import annotations

import bisect
from dataclasses import dataclass
from pathlib import Path

from ..vcf.parser import normalize_chrom

DEFAULT_GENES = Path(__file__).resolve().parents[1] / "data" / "genes_grch38.tsv"


@dataclass(frozen=True)
class Gene:
    name: str
    chrom: str
    start: int
    end: int
    strand: str
    note: str


class GeneIndex:
    """Genes sorted by start per chromosome, so 'which gene is at chr17:43,124,027?'
    is a binary search instead of a scan. (Real tools use interval trees.)"""

    def __init__(self, path: str | Path = DEFAULT_GENES):
        self.by_name: dict[str, Gene] = {}
        self.by_chrom: dict[str, list[Gene]] = {}
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            name, chrom, start, end, strand, note = line.split("\t")
            g = Gene(name.upper(), normalize_chrom(chrom), int(start), int(end), strand, note)
            self.by_name[g.name] = g
            self.by_chrom.setdefault(g.chrom, []).append(g)
        for genes in self.by_chrom.values():
            genes.sort(key=lambda g: g.start)
        self._starts = {c: [g.start for g in gs] for c, gs in self.by_chrom.items()}

    def get(self, name: str) -> Gene | None:
        return self.by_name.get(name.upper())

    def at(self, chrom: str, pos: int, flank: int = 5000) -> list[Gene]:
        """Genes overlapping pos, allowing `flank` bp for promoters/enhancers."""
        c = normalize_chrom(chrom)
        genes = self.by_chrom.get(c, [])
        i = bisect.bisect_right(self._starts.get(c, []), pos + flank)
        return [g for g in genes[:i] if g.start - flank <= pos <= g.end + flank]

    def names(self) -> list[str]:
        return sorted(self.by_name)
