# genome-mcp — "Ask your genome" through the Model Context Protocol

![python](https://img.shields.io/badge/python-3.10%2B-blue) ![MCP](https://img.shields.io/badge/MCP-server-purple) ![tests](https://img.shields.io/badge/tests-pytest-green) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

**genome-mcp** turns a VCF file (the standard output of DNA sequencing pipelines) into a set of
**MCP tools** that any AI assistant can call. Plug it into Claude Desktop, Cursor, VS Code or your
own agent and ask in plain English:

> *"Do I carry anything in BRCA1?"* · *"Am I a carrier for any disease?"* ·
> *"Is warfarin a concern for me?"* · *"What's my APOE status?"*

The model doesn't guess from memory — it calls real tools that read your file, match variants
against curated annotations, and apply genetics rules (zygosity, carrier vs affected, APOE haplotypes,
pharmacogenomics), then explains the result simply.

> ⚠️ Educational project. Not a medical device, not medical advice. The bundled sample is **synthetic**.

---

## Why this is interesting (in simple words)

- **Bioinformatics × AI agents.** Most genomics tools are command-line programs for specialists.
  MCP lets an LLM use them safely: the LLM handles language, the tools handle facts.
- **No hallucinated genetics.** Every answer comes from a tool result with the genotype, the source and a disclaimer.
- **Domain logic, not just lookups.** It knows that one copy of a CFTR variant usually means *carrier*,
  while one copy of a BRCA1 variant *raises risk*; it derives APOE ε2/ε3/ε4 from two SNPs; it ignores low-quality calls.
- **Standard protocol.** Built on the official MCP Python SDK, so it works with any MCP client.

## How it works

```
 You ──question──► MCP client (Claude Desktop / genome-mcp ask / your agent)
                          │  list_tools, call_tool   (JSON-RPC over stdio)
                          ▼
                 genome-mcp server  ── tools ───────────────────────────────┐
                          │                                                 │
       ┌──────────────────┼──────────────────┬──────────────────┐           │
       ▼                  ▼                  ▼                  ▼           │
  VCF reader        Gene index        ClinVar snapshot     Live APIs       │
  (streams .vcf,    (GRCh38 coords,   (curated pathogenic,  (Ensembl,      │
   .vcf.gz, GT,      binary search)    risk, PGx variants)   MyVariant;    │
   zygosity, QC)                                             optional)     │
                          └──────────► JSON result + disclaimer ◄──────────┘
```

## Quick start

```bash
git clone https://github.com/Noella-John1997/genome-mcp.git
cd genome-mcp
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

genome-mcp report                              # full markdown report on the demo sample
genome-mcp ask "Am I a carrier for any disease?"   # starts the MCP server and calls a tool
genome-mcp ask "What is my APOE status?"
pytest -q                                      # run the tests
```

Use your own file: add `--vcf path/to/file.vcf` (or `.vcf.gz`) to any command. Coordinates must be **GRCh38**.

### Use it from Claude Desktop

1. Find the full path of the installed command: `which genome-mcp` (Windows: `where genome-mcp`).
2. Open Claude Desktop → Settings → Developer → Edit Config, and add (see
   [`examples/claude_desktop_config.json`](examples/claude_desktop_config.json)):

```json
{
  "mcpServers": {
    "genome": {
      "command": "/full/path/to/.venv/bin/genome-mcp",
      "args": ["serve"]
    }
  }
}
```

3. Restart Claude Desktop and ask: *"Use the genome tools: do I carry anything in BRCA1?"*

### Let an LLM pick the tools from the command line

```bash
export OPENAI_API_KEY=sk-...          # any OpenAI-compatible endpoint; set OPENAI_BASE_URL to change
genome-mcp ask "Explain my pharmacogenomic results for a doctor" --llm
```

## Tools

| Tool | What it answers |
| --- | --- |
| `vcf_summary` | How many variants, which types, Ts/Tv and het/hom QC ratios |
| `query_region` | Variants in `chrom:start-end` |
| `gene_variants` | Variants in or near a gene, with annotations |
| `lookup_variant` | One variant by rsID or `chrom:pos:ref:alt` — what it is and whether you carry it |
| `clinically_relevant` | Pathogenic / risk-factor variants you carry, ranked, with carrier guidance |
| `pharmacogenomics` | Drug-response variants (warfarin, clopidogrel, statins, 5-FU) |
| `apoe_genotype` | ε2/ε3/ε4 genotype and what it means |
| `genome_report` | Everything above as a markdown report |
| `load_vcf` | Switch to another file / sample |

Resource: `genome://genes` lists the genes the server knows.

## What the demo sample shows

See [`examples/sample_report.md`](examples/sample_report.md). The synthetic sample is a heterozygous
carrier of pathogenic variants in **HFE** (hemochromatosis) and **CFTR** (cystic fibrosis), carries a
**BRCA1** frameshift, is **APOE ε3/ε4**, and has several pharmacogenomic variants. One CYP2C9 call is
marked `LowQual` — the tools skip it, as a real pipeline should.

## Commands

| Command | What it does |
| --- | --- |
| `genome-mcp serve [--vcf F] [--live]` | Run the MCP server over stdio (`--live` adds Ensembl lookups) |
| `genome-mcp ask "question" [--vcf F] [--llm]` | MCP client: routes the question to a tool, or lets an LLM choose |
| `genome-mcp report [--vcf F] [--out F]` | Markdown report |
| `genome-mcp summary` / `gene BRCA1` | JSON output for scripts |
| `genome-mcp verify-snapshot` | Re-checks every bundled annotation against Ensembl (needs internet) |

## Project layout

| Folder | What's inside |
| --- | --- |
| [`genome_mcp/`](genome_mcp/) | The package and the service layer |
| [`genome_mcp/vcf/`](genome_mcp/vcf/) | Streaming VCF parser and QC stats |
| [`genome_mcp/genes/`](genome_mcp/genes/) | Gene coordinate index |
| [`genome_mcp/annotation/`](genome_mcp/annotation/) | Offline ClinVar snapshot + live Ensembl/MyVariant clients |
| [`genome_mcp/server/`](genome_mcp/server/) | The MCP server (tools + resource) |
| [`genome_mcp/agent/`](genome_mcp/agent/) | MCP client: rule router and LLM tool-calling loop |
| [`genome_mcp/data/`](genome_mcp/data/) | Demo VCF, gene table, annotation snapshot |
| [`tests/`](tests/) | pytest suite, including an end-to-end MCP stdio test |
| [`examples/`](examples/) | Claude Desktop config, example questions, sample report |

## Genetics glossary (for non-biologists)

| Term | Meaning |
| --- | --- |
| **VCF** | Text file listing where a person's DNA differs from the reference genome |
| **GRCh38** | The current human reference genome build; positions depend on it |
| **REF / ALT** | The reference base(s) and the observed alternative |
| **Genotype (GT)** | `0/0` = two reference copies, `0/1` = one copy of the variant, `1/1` = two copies |
| **Heterozygous / homozygous** | One copy / two copies of a variant |
| **Carrier** | One copy of a variant in a *recessive* disease gene: usually healthy, can pass it on |
| **Pathogenic** | ClinVar classification: known to cause disease |
| **Pharmacogenomics** | How your genes change the way you process drugs |
| **Ts/Tv** | Transitions ÷ transversions; ~2.0–2.1 for whole genomes. (The tiny demo file gives an unrealistic value.) |

## Limitations

- The annotation snapshot is a small curated set (~15 well-known variants), not all of ClinVar.
  For real use, annotate with VEP / ANNOVAR / SnpEff or load a full ClinVar VCF.
- Indel matching is exact-allele; unnormalised indels (different left-alignment) may not match.
- APOE uses unphased data and assumes absent sites are reference.
- No CNV / structural-variant support.

## Roadmap

Full ClinVar VCF index (tabix) · VEP integration · Nextflow pipeline from FASTQ to this server ·
star-allele calling for CYP2D6 · HTTP (streamable) MCP transport.

## License

MIT — see [LICENSE](LICENSE).
