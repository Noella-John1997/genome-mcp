# `genome_mcp/` - the package

| File / folder | Purpose |
| --- | --- |
| `service.py` | **The brain.** `GenomeService` answers every question (summary, region, gene, lookup, clinically relevant, pharmacogenomics, APOE, report). Pure Python, easy to test. |
| `cli.py` | The `genome-mcp` command |
| `__init__.py` | Version and the medical `DISCLAIMER` attached to every answer |
| `vcf/` | Reads VCF files |
| `genes/` | Gene name ↔ coordinates |
| `annotation/` | What is known about a variant (offline snapshot + live APIs) |
| `server/` | Exposes `GenomeService` methods as MCP tools |
| `agent/` | An MCP client that asks the server questions |
| `data/` | Bundled demo data |

**Design choice:** MCP code is a thin wrapper. All logic lives in `service.py`, so the same code
powers the CLI, the MCP server and the tests.
