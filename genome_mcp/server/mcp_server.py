"""The MCP server.

MCP (Model Context Protocol) is an open standard that lets AI apps (Claude
Desktop, Cursor, VS Code, your own agent) discover and call *tools* on a
server. Here each tool is one question you can ask about a genome.

Run over stdio (what desktop apps expect):
    genome-mcp serve --vcf path/to/sample.vcf
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..service import DEMO_VCF, GenomeService


def build_server(vcf_path: str | None = None, live: bool = False) -> tuple[FastMCP, GenomeService]:
    svc = GenomeService(vcf_path or DEMO_VCF, live=live)
    mcp = FastMCP("genome-mcp", log_level="WARNING", instructions=(
        "Tools to explore one person's genetic variants from a VCF file (GRCh38). "
        "Always pass on the disclaimer: results are educational, not a diagnosis. "
        "Explain carrier status vs affected status clearly and in plain language."))

    @mcp.tool()
    def load_vcf(path: str, sample: str | None = None) -> dict:
        """Load a different VCF file (optionally choose a sample column)."""
        return svc.load(path, sample)

    @mcp.tool()
    def vcf_summary() -> dict:
        """QC overview: variant counts, types, per-chromosome counts, Ts/Tv and het/hom ratios."""
        return svc.summary()

    @mcp.tool()
    def query_region(chrom: str, start: int, end: int, pass_only: bool = True) -> dict:
        """Variants the sample carries between start and end (1-based, inclusive) on a chromosome."""
        return svc.region(chrom, start, end, pass_only)

    @mcp.tool()
    def gene_variants(gene: str, pass_only: bool = True) -> dict:
        """Variants in or near a gene (e.g. BRCA1, CFTR, APOE) with any known annotation."""
        return svc.gene_variants(gene, pass_only)

    @mcp.tool()
    def lookup_variant(query: str) -> dict:
        """Look up one variant by rsID (rs80357914) or chrom:pos:ref:alt (17:43124027:ACT:A)."""
        return svc.lookup(query)

    @mcp.tool()
    def clinically_relevant(include_risk_factors: bool = True) -> dict:
        """Pathogenic / likely pathogenic / risk-factor variants the sample carries."""
        return svc.clinically_relevant(include_risk_factors)

    @mcp.tool()
    def pharmacogenomics() -> dict:
        """How the sample's variants may affect common drugs (warfarin, clopidogrel, statins, 5-FU)."""
        return svc.pharmacogenomics()

    @mcp.tool()
    def apoe_genotype() -> dict:
        """APOE e2/e3/e4 genotype and what it means for Alzheimer disease risk."""
        return svc.apoe()

    @mcp.tool()
    def genome_report() -> str:
        """A full markdown report: QC, findings, pharmacogenomics, APOE."""
        return svc.report()

    @mcp.resource("genome://genes")
    def list_genes() -> str:
        """Genes this server knows coordinates for."""
        return "\n".join(f"{g}: {svc.genes.get(g).note}" for g in svc.genes.names())

    return mcp, svc


def run_stdio(vcf_path: str | None = None, live: bool = False) -> None:
    mcp, _ = build_server(vcf_path, live)
    mcp.run()  # stdio transport
