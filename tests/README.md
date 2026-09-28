# `tests/`

```bash
pytest -q
```

| File | What it checks |
| --- | --- |
| `test_vcf.py` | Header parsing, multi-allelic split, zygosity for every genotype, variant types, `.vcf.gz`, bad files, Ts/Tv and het/hom maths, region queries |
| `test_genes_annotation.py` | Gene index lookups and flanks, snapshot lookups, every snapshot variant falls in its gene |
| `test_service.py` | Clinically relevant findings on the demo, risk-factor filter, low-quality calls ignored, **all APOE combinations**, lookup, report |
| `test_mcp.py` | Tools are listed and callable through an in-memory MCP session, the question router, and a **real stdio end-to-end** `ask` |
| `test_web.py` | Web API: page loads, demo overview (APOE, carrier interpretation), Ask routing, upload + gene + report, bad uploads rejected, unknown session |
| `conftest.py` | `make_vcf` fixture that writes tiny VCFs for tests |
