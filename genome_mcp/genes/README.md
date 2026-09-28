# `genes/` - gene coordinates

`GeneIndex` loads `data/genes_grch38.tsv` (gene, chromosome, start, end, strand, why it matters).

- `get("BRCA1")` → the gene's location.
- `at("17", 43124027)` → which genes cover that position. Genes are sorted by start per chromosome
  and found with **binary search** (`bisect`) - the idea behind interval trees used by real tools.
- A default **5 kb flank** catches variants in promoters/enhancers just outside a gene
  (e.g. the VKORC1 warfarin variant, the LCT enhancer inside MCM6).

Add a gene: append a tab-separated line to the TSV.
