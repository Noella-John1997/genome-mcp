"""Quality-control numbers a bioinformatician looks at first."""
from __future__ import annotations

from collections import Counter

from .parser import VCFReader

TRANSITIONS = {("A", "G"), ("G", "A"), ("C", "T"), ("T", "C")}


def summarize(reader: VCFReader) -> dict:
    """Counts, Ts/Tv and het/hom ratios.

    Ts/Tv (transition/transversion ratio): ~2.0-2.1 for whole genomes and
    ~3.0 for exomes. Far lower usually means many false-positive calls.
    Het/Hom-alt ratio: ~1.5-2.0 in most human samples; unusual values can hint
    at contamination or consanguinity.
    """
    total = passed = ts = tv = het = hom = nocall = 0
    types: Counter = Counter()
    chroms: Counter = Counter()
    for v in reader:
        if v.alt_copies == 0:
            continue  # reference call: not a variant in this sample
        total += 1
        chroms[v.chrom] += 1
        types[v.kind] += 1
        if v.passed:
            passed += 1
        if v.kind == "SNV":
            if (v.ref, v.alt) in TRANSITIONS:
                ts += 1
            else:
                tv += 1
        z = v.zygosity
        if z == "heterozygous":
            het += 1
        elif z == "homozygous alternate":
            hom += 1
        elif z == "no call":
            nocall += 1
    return {
        "sample": reader.sample, "reference": reader.reference, "variants": total,
        "pass_filter": passed, "by_type": dict(types),
        "by_chromosome": dict(sorted(chroms.items(), key=lambda kv: (len(kv[0]), kv[0]))),
        "ts_tv_ratio": round(ts / tv, 2) if tv else None,
        "het_hom_ratio": round(het / hom, 2) if hom else None,
        "heterozygous": het, "homozygous_alt": hom, "no_calls": nocall,
    }
