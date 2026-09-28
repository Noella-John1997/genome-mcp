import asyncio
import json

from mcp.shared.memory import create_connected_server_and_client_session

from genome_mcp.agent import ask, route_question
from genome_mcp.server import build_server

EXPECTED_TOOLS = {"load_vcf", "vcf_summary", "query_region", "gene_variants", "lookup_variant",
                  "clinically_relevant", "pharmacogenomics", "apoe_genotype", "genome_report"}


def test_mcp_tools_listed_and_callable():
    async def run():
        server, _ = build_server()
        async with create_connected_server_and_client_session(server._mcp_server) as client:
            names = {t.name for t in (await client.list_tools()).tools}
            assert EXPECTED_TOOLS <= names
            res = await client.call_tool("gene_variants", {"gene": "CFTR"})
            data = json.loads(res.content[0].text)
            assert data["gene"] == "CFTR" and data["count"] >= 1
    asyncio.run(run())


def test_router():
    assert route_question("what is rs1800562?") == ("lookup_variant", {"query": "rs1800562"})
    assert route_question("Am I at risk for Alzheimer's?")[0] == "apoe_genotype"
    assert route_question("Is warfarin safe for me?")[0] == "pharmacogenomics"
    assert route_question("anything in my BRCA2 gene") == ("gene_variants", {"gene": "BRCA2"})
    assert route_question("show chr7:117000000-118000000")[0] == "query_region"
    assert route_question("am I a carrier of any disease?")[0] == "clinically_relevant"
    assert route_question("hello")[0] == "vcf_summary"


def test_ask_over_stdio_end_to_end():
    out = asyncio.run(ask("What is my APOE status?"))
    assert "apoe_genotype" in out and "e3/e4" in out
