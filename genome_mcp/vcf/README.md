# `vcf/` — reading VCF files

## A VCF line, explained

```
#CHROM  POS        ID          REF  ALT  QUAL  FILTER  INFO   FORMAT    DEMO_SAMPLE
chr17   43124027   rs80357914  ACT  A    520   PASS    DP=36  GT:DP:GQ  0/1:36:99
```

- On chromosome 17 at position 43,124,027 the reference has `ACT`; this person has `A` → a 2-base **deletion**.
- `FILTER=PASS` → the variant caller trusts it.
- `GT=0/1` → one copy of the reference (`0`) and one of the ALT (`1`): **heterozygous**.

## `parser.py`

- `VCFReader(path, sample=None)` — reads the header, then **streams** variants (constant memory; `.vcf.gz` supported).
- Multi-allelic lines (`ALT=A,T`) are split into one `Variant` per ALT, with `alt_copies` counted for each.
- `Variant` properties: `kind` (SNV / insertion / deletion / MNV), `zygosity`, `alt_copies`, `passed`, `key` (`chrom:pos:ref:alt`).
- `"chr17"` and `"17"` are treated as the same chromosome.

## `stats.py`

`summarize(reader)` returns counts and two QC ratios bioinformaticians check first:

- **Ts/Tv** — transitions (A↔G, C↔T) ÷ transversions. Whole genomes ≈ 2.0–2.1, exomes ≈ 3.0. Much lower suggests false positives.
- **Het/Hom-alt** — usually 1.5–2.0; unusual values can hint at contamination or consanguinity.

Reference-only calls (`0/0`) are not counted as variants.
