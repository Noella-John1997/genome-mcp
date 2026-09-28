from genome_mcp.annotation import ClinVarSnapshot
from genome_mcp.genes import GeneIndex


def test_gene_lookup_and_position():
    gi = GeneIndex()
    assert gi.get("brca1").chrom == "17"
    assert [g.name for g in gi.at("chr17", 43124027)] == ["BRCA1"]
    assert gi.at("17", 1) == []


def test_flank_catches_promoter_variant():
    # rs9923231 sits just upstream of VKORC1
    assert "VKORC1" in [g.name for g in GeneIndex().at("16", 31096368)]


def test_snapshot_lookup_by_rsid_and_key():
    s = ClinVarSnapshot()
    assert len(s) >= 10
    assert s.lookup("rs113993960").gene == "CFTR"
    assert s.lookup("chr17:43124027:ACT:A").rsid == "rs80357914"
    assert s.lookup("nonsense") is None


def test_snapshot_variants_fall_inside_known_genes():
    gi, s = GeneIndex(), ClinVarSnapshot()
    for a in s.all():
        assert a.gene in [g.name for g in gi.at(a.chrom, a.pos)], a.rsid
