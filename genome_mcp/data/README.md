# `data/` — bundled data

| File | What it is |
| --- | --- |
| `demo_sample.vcf` | **Synthetic** VCF (not a real person), GRCh38, one sample `DEMO_SAMPLE`: 22 lines including well-known pathogenic, risk and drug-response variants, benign filler, two `LowQual` calls, a multi-allelic site and reference (`0/0`) calls |
| `genes_grch38.tsv` | 16 clinically important genes with approximate GRCh38 spans and a one-line explanation |
| `clinvar_snapshot.tsv` | ~15 curated variants with significance and condition/drug, from public ClinVar / PharmGKB summaries |

All values are for learning and demos. Run `genome-mcp verify-snapshot` (internet needed) to compare
the snapshot with Ensembl, and never use this data for clinical decisions.
