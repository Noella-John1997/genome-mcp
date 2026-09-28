import pytest

from genome_mcp.service import GenomeService


@pytest.fixture(scope="module")
def svc():
    return GenomeService()


def test_clinically_relevant_on_demo(svc):
    res = svc.clinically_relevant()
    genes = [f["annotation"]["gene"] for f in res["findings"]]
    assert set(genes) == {"BRCA1", "CFTR", "HFE", "APOE"}
    assert res["findings"][-1]["annotation"]["gene"] == "APOE"  # risk factor ranked last
    assert "carrier" in res["interpretation_note"]
    assert "disclaimer" in res


def test_exclude_risk_factors(svc):
    genes = [f["annotation"]["gene"] for f in svc.clinically_relevant(include_risk_factors=False)["findings"]]
    assert "APOE" not in genes


def test_pharmacogenomics_ignores_low_quality(svc):
    rows = {r["rsid"]: r for r in svc.pharmacogenomics()["results"]}
    assert "low-quality" in rows["rs1799853"]["status"]
    assert rows["rs9923231"]["copies_of_variant"] == 2
    assert rows["rs3918290"]["copies_of_variant"] == 0


def test_apoe_demo_is_e3_e4(svc):
    assert svc.apoe()["genotype"] == "e3/e4"


@pytest.mark.parametrize("gt4,gt2,expected", [
    ("0/0", "0/0", "e3/e3"), ("1/1", "0/0", "e4/e4"), ("0/0", "0/1", "e2/e3"),
    ("0/0", "1/1", "e2/e2"), ("0/1", "0/1", "e2/e4")])
def test_apoe_combinations(make_vcf, gt4, gt2, expected):
    p = make_vcf(f"19\t44908684\trs429358\tT\tC\t50\tPASS\t.\tGT\t{gt4}",
                 f"19\t44908822\trs7412\tC\tT\t50\tPASS\t.\tGT\t{gt2}")
    assert GenomeService(p).apoe()["genotype"] == expected


def test_apoe_missing_sites_assumed_reference(make_vcf):
    res = GenomeService(make_vcf("1\t10\t.\tA\tG\t50\tPASS\t.\tGT\t0/1")).apoe()
    assert res["genotype"] == "e3/e3" and len(res["assumptions"]) == 2


def test_lookup_reports_genotype(svc):
    res = svc.lookup("rs80357914")
    assert res["in_sample"]["zygosity"] == "heterozygous"
    assert res["annotation"]["significance"] == "Pathogenic"


def test_unknown_gene(svc):
    assert "error" in svc.gene_variants("NOTAGENE")


def test_report_markdown(svc):
    md = svc.report()
    assert md.startswith("# Genome report") and "| BRCA1 |" in md and "e3/e4" in md
