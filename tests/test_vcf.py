import gzip

import pytest

from genome_mcp.vcf import VCFReader, summarize
from genome_mcp.service import DEMO_VCF


def test_reads_demo_header():
    r = VCFReader(DEMO_VCF)
    assert r.samples == ["DEMO_SAMPLE"]
    assert r.reference == "GRCh38"


def test_multiallelic_line_is_split(make_vcf):
    p = make_vcf("chr19\t100\t.\tG\tA,T\t50\tPASS\t.\tGT\t1/2")
    a, t = list(VCFReader(p))
    assert (a.alt, a.alt_copies, a.zygosity) == ("A", 1, "heterozygous")
    assert (t.alt, t.alt_copies) == ("T", 1)
    assert a.chrom == "19"  # 'chr' prefix normalised


@pytest.mark.parametrize("gt,copies,zyg", [
    ("0/0", 0, "homozygous reference"), ("0|1", 1, "heterozygous"),
    ("1/1", 2, "homozygous alternate"), ("./.", None, "no call")])
def test_zygosity(make_vcf, gt, copies, zyg):
    v = next(iter(VCFReader(make_vcf(f"1\t10\t.\tA\tG\t50\tPASS\t.\tGT\t{gt}"))))
    assert v.alt_copies == copies and v.zygosity == zyg


def test_variant_types(make_vcf):
    p = make_vcf("1\t1\t.\tA\tG\t1\tPASS\t.\tGT\t0/1", "1\t2\t.\tA\tAT\t1\tPASS\t.\tGT\t0/1",
                 "1\t3\t.\tACT\tA\t1\tPASS\t.\tGT\t0/1")
    assert [v.kind for v in VCFReader(p)] == ["SNV", "insertion", "deletion"]


def test_gzip_supported(tmp_path):
    p = tmp_path / "x.vcf.gz"
    with gzip.open(p, "wt") as f:
        f.write(DEMO_VCF.read_text())
    assert len(list(VCFReader(p))) == len(list(VCFReader(DEMO_VCF)))


def test_not_a_vcf(tmp_path):
    p = tmp_path / "bad.vcf"
    p.write_text("hello\n")
    with pytest.raises(ValueError):
        VCFReader(p)


def test_summary_ts_tv(make_vcf):
    p = make_vcf("1\t1\t.\tA\tG\t1\tPASS\t.\tGT\t0/1",   # transition
                 "1\t2\t.\tC\tT\t1\tPASS\t.\tGT\t1/1",   # transition
                 "1\t3\t.\tA\tC\t1\tPASS\t.\tGT\t0/1",   # transversion
                 "1\t4\t.\tA\tC\t1\tPASS\t.\tGT\t0/0")   # reference call: ignored
    s = summarize(VCFReader(p))
    assert s["variants"] == 3
    assert s["ts_tv_ratio"] == 2.0
    assert s["het_hom_ratio"] == 2.0


def test_region_query():
    r = VCFReader(DEMO_VCF)
    ids = [v.id for v in r.region("chr17", 43_000_000, 43_200_000)]
    assert "rs80357914" in ids
