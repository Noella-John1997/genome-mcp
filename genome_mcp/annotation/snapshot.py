"""Offline annotation from a small bundled ClinVar-style table."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from ..vcf.parser import Variant, normalize_chrom

DEFAULT_SNAPSHOT = Path(__file__).resolve().parents[1] / "data" / "clinvar_snapshot.tsv"


@dataclass(frozen=True)
class Annotation:
    rsid: str
    chrom: str
    pos: int
    ref: str
    alt: str
    gene: str
    change: str
    significance: str
    condition: str
    category: str       # disease | risk | pharmacogenomic | trait
    source: str = "offline snapshot"

    def to_dict(self) -> dict:
        return asdict(self)


class ClinVarSnapshot:
    def __init__(self, path: str | Path = DEFAULT_SNAPSHOT):
        self.by_key: dict[str, Annotation] = {}
        self.by_rsid: dict[str, Annotation] = {}
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            rsid, chrom, pos, ref, alt, gene, change, sig, cond, cat = line.split("\t")
            a = Annotation(rsid, normalize_chrom(chrom), int(pos), ref, alt, gene, change, sig, cond, cat)
            self.by_key[f"{a.chrom}:{a.pos}:{a.ref}:{a.alt}"] = a
            self.by_rsid[rsid] = a

    def __len__(self) -> int:
        return len(self.by_key)

    def for_variant(self, v: Variant) -> Annotation | None:
        # Match on exact allele first (safest), then fall back to rsID.
        return self.by_key.get(v.key) or (self.by_rsid.get(v.rsid) if v.rsid else None)

    def lookup(self, query: str) -> Annotation | None:
        """Query by 'rs123' or 'chrom:pos:ref:alt'."""
        q = query.strip()
        if q.lower().startswith("rs"):
            return self.by_rsid.get(q.lower())
        parts = q.split(":")
        if len(parts) == 4:
            parts[0] = normalize_chrom(parts[0])
            return self.by_key.get(":".join(parts))
        return None

    def all(self) -> list[Annotation]:
        return list(self.by_key.values())
