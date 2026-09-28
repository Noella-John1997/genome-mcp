# `annotation/` — what is known about a variant

## `snapshot.py` — offline, always available

`ClinVarSnapshot` loads `data/clinvar_snapshot.tsv`: ~15 well-known variants with gene, protein change,
significance, condition/drug and a category (`disease`, `risk`, `pharmacogenomic`, `trait`).

Matching is done on the exact allele (`chrom:pos:ref:alt`) first, then on rsID. Exact-allele matching
matters: a different ALT at the same position can have a completely different meaning.

## `live.py` — online, optional

`LiveAnnotator` queries free public APIs and caches every response in `.cache/`:

| Method | Source | Returns |
| --- | --- | --- |
| `ensembl_rsid("rs1800562")` | Ensembl REST | GRCh38 position, alleles, clinical significance, consequence |
| `myvariant_clinvar(chrom, pos, ref, alt)` | MyVariant.info | ClinVar significance and conditions (SNVs) |

Turn it on with `genome-mcp serve --live`. `genome-mcp verify-snapshot` uses it to re-check the offline table.
