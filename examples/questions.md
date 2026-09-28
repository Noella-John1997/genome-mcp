# Example questions

Try these with `genome-mcp ask "..."` (offline router) or in Claude Desktop / any MCP client.

| Question | Tool it uses |
| --- | --- |
| Give me an overview of this VCF | `vcf_summary` |
| Do I carry anything in BRCA1? | `gene_variants` |
| Am I a carrier for any disease? | `clinically_relevant` |
| What is rs113993960? | `lookup_variant` |
| Is warfarin or clopidogrel a concern for me? | `pharmacogenomics` |
| What is my APOE status? | `apoe_genotype` |
| Show variants in chr7:117000000-118000000 | `query_region` |
| Write me a full report | `genome_report` |

With an LLM client (Claude Desktop or `--llm`), you can ask follow-ups in plain English, e.g.
"Explain the CFTR result like I'm 15, and tell me whether my partner should get tested."
