"""The genome 'brain': plain Python functions that answer questions about a VCF.

Both the MCP server and the CLI call these, so they are easy to unit test
without any MCP machinery.
"""
from __future__ import annotations

from pathlib import Path

from . import DISCLAIMER
from .annotation import ClinVarSnapshot, LiveAnnotator
from .genes import GeneIndex
from .vcf import VCFReader, summarize
from .vcf.parser import Variant

SIGNIFICANCE_RANK = {"pathogenic": 3, "likely pathogenic": 2, "risk factor": 1}
RECESSIVE = {"CFTR", "HFE", "HBB"}               # two faulty copies needed to be affected
DOMINANT = {"BRCA1", "BRCA2", "TP53", "MLH1", "LDLR"}  # one faulty copy raises risk
DEMO_VCF = Path(__file__).resolve().parent / "data" / "demo_sample.vcf"


class GenomeService:
    def __init__(self, vcf_path: str | Path = DEMO_VCF, sample: str | None = None,
                 live: bool = False, cache_dir: str | Path = ".cache"):
        self.genes = GeneIndex()
        self.snapshot = ClinVarSnapshot()
        self.live = LiveAnnotator(cache_dir) if live else None
        self.load(vcf_path, sample)

    # ---------------------------------------------------------------- helpers
    def load(self, vcf_path: str | Path, sample: str | None = None) -> dict:
        self.reader = VCFReader(vcf_path, sample)
        self.vcf_path = str(vcf_path)
        return {"loaded": self.vcf_path, "sample": self.reader.sample, "samples": self.reader.samples}

    def _describe(self, v: Variant) -> dict:
        d = v.to_dict()
        d["genes"] = [g.name for g in self.genes.at(v.chrom, v.pos)]
        ann = self.snapshot.for_variant(v)
        d["annotation"] = ann.to_dict() if ann else None
        return d

    @staticmethod
    def _carried(v: Variant) -> bool:
        return (v.alt_copies or 0) > 0

    # ---------------------------------------------------------------- queries
    def summary(self) -> dict:
        return {**summarize(self.reader), "file": self.vcf_path, "disclaimer": DISCLAIMER}

    def region(self, chrom: str, start: int, end: int, pass_only: bool = True, limit: int = 200) -> dict:
        vs = [self._describe(v) for v in self.reader.region(chrom, start, end, pass_only) if self._carried(v)]
        return {"region": f"{chrom}:{start}-{end}", "count": len(vs), "variants": vs[:limit],
                "truncated": len(vs) > limit}

    def gene_variants(self, gene: str, pass_only: bool = True) -> dict:
        g = self.genes.get(gene)
        if g is None:
            return {"error": f"unknown gene {gene!r}", "known_genes": self.genes.names()}
        res = self.region(g.chrom, g.start - 5000, g.end + 5000, pass_only)
        return {"gene": g.name, "location": f"chr{g.chrom}:{g.start}-{g.end} ({g.strand})",
                "why_it_matters": g.note, **res, "disclaimer": DISCLAIMER}

    def lookup(self, query: str) -> dict:
        """rsID or chrom:pos:ref:alt -> what is known + whether this sample carries it."""
        ann = self.snapshot.lookup(query)
        carried = None
        for v in self.reader:
            if (query.lower().startswith("rs") and v.id == query.lower()) or v.key == _norm_key(query):
                carried = {"genotype": v.genotype, "zygosity": v.zygosity, "filter": v.filter}
                break
        out = {"query": query, "annotation": ann.to_dict() if ann else None,
               "in_sample": carried or "not found in VCF (either reference or not sequenced)"}
        if self.live and query.lower().startswith("rs"):
            try:
                out["live"] = self.live.ensembl_rsid(query.lower())
            except Exception as e:  # network errors must not break the tool
                out["live_error"] = f"{type(e).__name__}: {e}"
        out["disclaimer"] = DISCLAIMER
        return out

    def clinically_relevant(self, include_risk_factors: bool = True, pass_only: bool = True) -> dict:
        hits = []
        for v in self.reader:
            if not self._carried(v) or (pass_only and not v.passed):
                continue
            ann = self.snapshot.for_variant(v)
            if not ann or ann.category not in ("disease", "risk"):
                continue
            rank = max((r for k, r in SIGNIFICANCE_RANK.items() if k in ann.significance.lower()), default=0)
            if rank == 0 or (rank == 1 and not include_risk_factors):
                continue
            hits.append({**self._describe(v), "rank": rank, "interpretation": _interpret(ann.gene, ann.category, v)})
        hits.sort(key=lambda h: -h["rank"])
        carrier_note = ("Heterozygous pathogenic variants in recessive-disease genes (e.g. CFTR, HFE, HBB) usually "
                        "mean 'carrier', not 'affected'. BRCA1/BRCA2 are dominant: one copy raises cancer risk.")
        return {"count": len(hits), "findings": hits, "interpretation_note": carrier_note, "disclaimer": DISCLAIMER}

    def pharmacogenomics(self, pass_only: bool = True) -> dict:
        rows = []
        for v in self.reader:
            ann = self.snapshot.for_variant(v)
            if not ann or ann.category != "pharmacogenomic":
                continue
            if pass_only and not v.passed:
                rows.append({"rsid": ann.rsid, "gene": ann.gene, "status": f"low-quality call ({v.filter}), ignored"})
                continue
            copies = v.alt_copies or 0
            rows.append({"rsid": ann.rsid, "gene": ann.gene, "change": ann.change, "genotype": v.genotype,
                         "copies_of_variant": copies, "effect": ann.condition if copies else "no variant allele (typical)",
                         "zygosity": v.zygosity})
        return {"results": rows, "note": "Drug dosing depends on combined star-alleles and clinical context "
                                         "(see CPIC guidelines).", "disclaimer": DISCLAIMER}

    def apoe(self) -> dict:
        """APOE e2/e3/e4 from two SNPs.

        rs429358 C  -> e4 marker ; rs7412 T -> e2 marker.
        Haplotypes: e2 = (T, T), e3 = (T, C), e4 = (C, C) at (rs429358, rs7412).
        Unphased data: count marker copies and assume the most common combination.
        """
        sites = {v.id: v for v in self.reader if v.id in ("rs429358", "rs7412")}
        missing = [r for r in ("rs429358", "rs7412") if r not in sites]
        n4 = sites["rs429358"].alt_copies if "rs429358" in sites else 0
        n2 = sites["rs7412"].alt_copies if "rs7412" in sites else 0
        if n4 is None or n2 is None:
            return {"genotype": "unknown (no-call at an APOE site)", "disclaimer": DISCLAIMER}
        alleles = ["e4"] * n4 + ["e2"] * n2
        alleles += ["e3"] * (2 - len(alleles))
        genotype = "/".join(sorted(alleles[:2], key=lambda a: int(a[1])))
        meaning = {
            "e3/e3": "Most common genotype; average risk.",
            "e3/e4": "One e4 copy: increased risk of late-onset Alzheimer disease vs e3/e3 (roughly 2-3x).",
            "e4/e4": "Two e4 copies: substantially increased risk (roughly 8-12x vs e3/e3).",
            "e2/e3": "e2 is associated with lower Alzheimer risk; linked to type III hyperlipoproteinemia when e2/e2.",
            "e2/e2": "Lower Alzheimer risk; risk of type III hyperlipoproteinemia.",
            "e2/e4": "Mixed; risk close to e3/e4. (Could also be the rare e1/e3; phasing needed.)",
        }.get(genotype, "")
        return {"genotype": genotype, "meaning": meaning,
                "assumptions": [f"{m} not present in VCF, assumed reference" for m in missing],
                "disclaimer": DISCLAIMER}

    def report(self) -> str:
        """Markdown report combining everything above."""
        s = self.summary()
        cr = self.clinically_relevant()
        pgx = self.pharmacogenomics()
        ap = self.apoe()
        lines = [f"# Genome report — {s['sample']}", "", f"> {DISCLAIMER}", "",
                 "## Quality control", "",
                 f"| Metric | Value |", "| --- | --- |",
                 f"| Variants | {s['variants']} |", f"| Passing filters | {s['pass_filter']} |",
                 f"| Ts/Tv ratio | {s['ts_tv_ratio']} |", f"| Het/Hom-alt ratio | {s['het_hom_ratio']} |",
                 f"| Types | {', '.join(f'{k}: {v}' for k, v in s['by_type'].items())} |", "",
                 "## Clinically relevant findings", ""]
        if cr["findings"]:
            lines += ["| Gene | Variant | Change | Genotype | Significance | Condition |", "| --- | --- | --- | --- | --- | --- |"]
            for f in cr["findings"]:
                a = f["annotation"]
                lines.append(f"| {a['gene']} | {a['rsid']} | {a['change']} | {f['zygosity']} | {a['significance']} | {a['condition']} |")
            lines += ["", f"_{cr['interpretation_note']}_", ""]
        else:
            lines += ["None found in the curated set.", ""]
        lines += ["## Pharmacogenomics", "", "| Gene | Variant | Copies | Effect |", "| --- | --- | --- | --- |"]
        for r in pgx["results"]:
            lines.append(f"| {r['gene']} | {r['rsid']} | {r.get('copies_of_variant', '-')} | {r.get('effect', r.get('status'))} |")
        lines += ["", "## APOE", "", f"**{ap['genotype']}** — {ap.get('meaning', '')}", ""]
        return "\n".join(lines)


def _interpret(gene: str, category: str, v: Variant) -> str:
    """One plain-language sentence a non-specialist can understand."""
    two = (v.alt_copies or 0) >= 2
    if category == "risk":
        return "A risk factor: it changes the odds, it does not decide the outcome."
    if gene in RECESSIVE:
        return ("Two copies: consistent with being affected — confirm clinically." if two else
                "Carrier (one copy): usually healthy, but children could inherit it; partner testing is often offered.")
    if gene in DOMINANT:
        return "One copy is enough to raise risk: genetic counselling and confirmatory testing are recommended."
    return "Discuss with a genetic counsellor."


def _norm_key(q: str) -> str:
    parts = q.split(":")
    if len(parts) == 4 and parts[0].lower().startswith("chr"):
        parts[0] = parts[0][3:]
    return ":".join(parts)
