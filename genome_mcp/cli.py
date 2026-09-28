"""`genome-mcp` command line."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="genome-mcp", description="Ask your genome, via MCP")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="run the MCP server over stdio")
    s.add_argument("--vcf", help="VCF file (default: bundled synthetic demo sample)")
    s.add_argument("--live", action="store_true", help="also query Ensembl live for rsIDs")

    a = sub.add_parser("ask", help="ask a question (starts the server and acts as an MCP client)")
    a.add_argument("question")
    a.add_argument("--vcf")
    a.add_argument("--llm", action="store_true", help="let an LLM choose tools (needs OPENAI_API_KEY)")

    r = sub.add_parser("report", help="print a markdown report")
    r.add_argument("--vcf")
    r.add_argument("--out", help="write to a file instead of stdout")

    sm = sub.add_parser("summary", help="QC summary as JSON")
    sm.add_argument("--vcf")

    g = sub.add_parser("gene", help="variants in one gene as JSON")
    g.add_argument("gene")
    g.add_argument("--vcf")

    sub.add_parser("verify-snapshot", help="re-check the bundled annotation table against Ensembl (internet)")

    args = p.parse_args(argv)

    if args.cmd == "serve":
        from .server.mcp_server import run_stdio
        run_stdio(args.vcf, args.live)
        return 0
    if args.cmd == "ask":
        from .agent import ask
        print(asyncio.run(ask(args.question, args.vcf, args.llm)))
        return 0
    if args.cmd == "verify-snapshot":
        return _verify_snapshot()

    from .service import DEMO_VCF, GenomeService
    svc = GenomeService(args.vcf or DEMO_VCF)
    if args.cmd == "report":
        text = svc.report()
        if args.out:
            open(args.out, "w", encoding="utf-8").write(text)
            print(f"wrote {args.out}")
        else:
            print(text)
    elif args.cmd == "summary":
        print(json.dumps(svc.summary(), indent=2))
    elif args.cmd == "gene":
        print(json.dumps(svc.gene_variants(args.gene), indent=2))
    return 0


def _verify_snapshot() -> int:
    from .annotation import ClinVarSnapshot, LiveAnnotator
    live, bad = LiveAnnotator(), 0
    for a in ClinVarSnapshot().all():
        try:
            e = live.ensembl_rsid(a.rsid)
        except Exception as ex:
            print(f"  ?  {a.rsid:<12} could not check: {ex}")
            continue
        alleles = (e["alleles"] or "").split("/")
        # Ensembl writes indels without the VCF anchor base, and 'start' is 1 after it.
        pos_ok = e["pos"] in (a.pos, a.pos + 1)
        allele_ok = a.alt[-1:] in "".join(alleles) or len(a.ref) != len(a.alt)
        ok = str(e["chrom"]) == a.chrom and pos_ok and allele_ok
        bad += not ok
        print(f"  {'OK' if ok else 'XX'} {a.rsid:<12} snapshot {a.chrom}:{a.pos} {a.ref}>{a.alt} | "
              f"Ensembl {e['chrom']}:{e['pos']} {e['alleles']} | {', '.join(e['clinical_significance'])}")
    print("all good" if not bad else f"{bad} mismatches — fix data/clinvar_snapshot.tsv")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
