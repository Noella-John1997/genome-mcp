"""Live lookups against public REST APIs (needs internet).

* Ensembl REST  - positions (GRCh38), alleles, clinical significance per rsID
* MyVariant.info - aggregated ClinVar records by HGVS id

Results are cached on disk in .cache/ so repeated questions are instant and
we stay polite to free public services.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx

ENSEMBL = "https://rest.ensembl.org"
MYVARIANT = "https://myvariant.info/v1"


class LiveAnnotator:
    def __init__(self, cache_dir: str | Path = ".cache", timeout: float = 15.0,
                 client: httpx.Client | None = None):
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.client = client or httpx.Client(timeout=timeout, headers={"Accept": "application/json"})

    def _get(self, url: str, params: dict | None = None) -> dict:
        key = hashlib.sha1((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
        f = self.cache / f"{key}.json"
        if f.exists():
            return json.loads(f.read_text())
        r = self.client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        f.write_text(json.dumps(data))
        return data

    def ensembl_rsid(self, rsid: str) -> dict:
        """Return {'rsid', 'chrom', 'pos', 'alleles', 'clinical_significance', 'consequence'} on GRCh38."""
        d = self._get(f"{ENSEMBL}/variation/human/{rsid}", {"content-type": "application/json"})
        grch38 = [m for m in d.get("mappings", []) if m.get("assembly_name") == "GRCh38"
                  and "_" not in str(m.get("seq_region_name"))]
        m = grch38[0] if grch38 else {}
        return {
            "rsid": rsid, "chrom": m.get("seq_region_name"), "pos": m.get("start"),
            "alleles": m.get("allele_string"),
            "clinical_significance": d.get("clinical_significance", []),
            "consequence": d.get("most_severe_consequence"), "source": "Ensembl REST (live)",
        }

    def myvariant_clinvar(self, chrom: str, pos: int, ref: str, alt: str) -> dict:
        """SNVs only (HGVS for indels needs normalisation)."""
        hgvs = f"chr{chrom}:g.{pos}{ref}>{alt}"
        d = self._get(f"{MYVARIANT}/variant/{hgvs}", {"assembly": "hg38", "fields": "clinvar,dbsnp.rsid"})
        cv = d.get("clinvar") or {}
        rcv = cv.get("rcv", [])
        rcv = rcv if isinstance(rcv, list) else [rcv]
        return {
            "hgvs": hgvs, "rsid": (d.get("dbsnp") or {}).get("rsid"), "gene": (cv.get("gene") or {}).get("symbol"),
            "significance": sorted({r.get("clinical_significance") for r in rcv if r.get("clinical_significance")}),
            "conditions": sorted({(r.get("conditions") or {}).get("name") for r in rcv
                                  if isinstance(r.get("conditions"), dict) and r["conditions"].get("name")}),
            "source": "MyVariant.info / ClinVar (live)",
        }
