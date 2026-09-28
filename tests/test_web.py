from fastapi.testclient import TestClient

from genome_mcp.service import DEMO_VCF
from genome_mcp.web import create_app

client = TestClient(create_app())


def test_index():
    assert "genome-mcp" in client.get("/").text


def test_demo_overview():
    o = client.get("/api/demo/overview").json()
    assert o["summary"]["sample"] == "DEMO_SAMPLE"
    assert o["apoe"]["genotype"] == "e3/e4"
    cftr = [f for f in o["findings"]["findings"] if f["annotation"]["gene"] == "CFTR"][0]
    assert "Carrier" in cftr["interpretation"]


def test_ask_routes_to_tool():
    d = client.post("/api/demo/ask", json={"question": "Do I carry anything in BRCA1?"}).json()
    assert d["tool"] == "gene_variants" and d["result"]["gene"] == "BRCA1"


def test_upload_and_query():
    r = client.post("/api/upload", files={"file": ("me.vcf", DEMO_VCF.read_bytes(), "text/plain")})
    sid = r.json()["session_id"]
    assert client.get(f"/api/{sid}/gene/CFTR").json()["count"] >= 1
    assert client.get(f"/api/{sid}/report.md").text.startswith("# Genome report")


def test_upload_rejects_bad_files():
    assert client.post("/api/upload", files={"file": ("x.txt", b"hi", "text/plain")}).status_code == 400
    assert client.post("/api/upload", files={"file": ("x.vcf", b"not a vcf", "text/plain")}).status_code == 400


def test_unknown_session():
    assert client.get("/api/nope/overview").status_code == 404
