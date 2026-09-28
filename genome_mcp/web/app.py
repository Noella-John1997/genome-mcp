"""Web app: explore a VCF in the browser and ask questions in plain English.

    genome-mcp web      ->  http://127.0.0.1:8000

The "Ask" box uses the same question router and the same tool functions as
the MCP server, and shows which tool was called — so the page doubles as a
visual explanation of how an AI agent uses MCP tools.

Uploads are kept in a temp folder for 30 minutes, then deleted.
"""
from __future__ import annotations

import shutil
import tempfile
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import DISCLAIMER
from ..agent.ask import route_question
from ..service import DEMO_VCF, GenomeService

STATIC = Path(__file__).with_name("static")
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
SESSION_TTL = 30 * 60
MAX_SESSIONS = 50


class AskBody(BaseModel):
    question: str = Field(..., min_length=2, max_length=300)


def _dispatch(svc: GenomeService, tool: str, args: dict):
    table = {
        "vcf_summary": lambda: svc.summary(),
        "query_region": lambda: svc.region(args["chrom"], args["start"], args["end"]),
        "gene_variants": lambda: svc.gene_variants(args["gene"]),
        "lookup_variant": lambda: svc.lookup(args["query"]),
        "clinically_relevant": lambda: svc.clinically_relevant(),
        "pharmacogenomics": lambda: svc.pharmacogenomics(),
        "apoe_genotype": lambda: svc.apoe(),
        "genome_report": lambda: {"markdown": svc.report()},
    }
    return table[tool]()


def create_app() -> FastAPI:
    tmp_root = Path(tempfile.mkdtemp(prefix="genome-mcp-"))
    demo = GenomeService(DEMO_VCF)
    sessions: dict[str, dict] = {}

    app = FastAPI(title="genome-mcp", description="Ask your genome — web + MCP")
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    def _gc() -> None:
        now = time.time()
        for sid in [k for k, v in sessions.items() if now - v["ts"] > SESSION_TTL]:
            shutil.rmtree(sessions.pop(sid)["dir"], ignore_errors=True)

    def svc_for(sid: str) -> GenomeService:
        if sid == "demo":
            return demo
        _gc()
        s = sessions.get(sid)
        if not s:
            raise HTTPException(404, "session expired — upload the file again")
        s["ts"] = time.time()
        return s["svc"]

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/health")
    def health():
        return {"ok": True, "sessions": len(sessions)}

    @app.post("/api/upload")
    async def upload(file: UploadFile = File(...)):
        _gc()
        name = (file.filename or "upload.vcf").lower()
        if not (name.endswith(".vcf") or name.endswith(".vcf.gz")):
            raise HTTPException(400, "please upload a .vcf or .vcf.gz file")
        if len(sessions) >= MAX_SESSIONS:
            raise HTTPException(503, "server busy, try again in a few minutes")
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "file larger than 20 MB — use the CLI for big files")
        sid = uuid.uuid4().hex
        d = tmp_root / sid
        d.mkdir()
        path = d / ("sample.vcf.gz" if name.endswith(".gz") else "sample.vcf")
        path.write_bytes(data)
        try:
            svc = GenomeService(path)
            svc.summary()  # parse once to validate the whole file
        except Exception as e:
            shutil.rmtree(d, ignore_errors=True)
            raise HTTPException(400, f"could not read VCF: {e}")
        sessions[sid] = {"svc": svc, "dir": d, "ts": time.time()}
        return {"session_id": sid, "sample": svc.reader.sample, "filename": file.filename}

    @app.get("/api/{sid}/overview")
    def overview(sid: str):
        svc = svc_for(sid)
        return {"summary": svc.summary(), "findings": svc.clinically_relevant(),
                "pgx": svc.pharmacogenomics(), "apoe": svc.apoe(),
                "genes": [{"name": g, "note": svc.genes.get(g).note} for g in svc.genes.names()],
                "disclaimer": DISCLAIMER}

    @app.get("/api/{sid}/gene/{gene}")
    def gene(sid: str, gene: str):
        return svc_for(sid).gene_variants(gene)

    @app.get("/api/{sid}/lookup")
    def lookup(sid: str, q: str):
        return svc_for(sid).lookup(q)

    @app.post("/api/{sid}/ask")
    def ask(sid: str, body: AskBody):
        svc = svc_for(sid)
        tool, args = route_question(body.question)
        return {"tool": tool, "args": args, "result": _dispatch(svc, tool, args)}

    @app.get("/api/{sid}/report.md")
    def report(sid: str):
        svc = svc_for(sid)
        return PlainTextResponse(svc.report(), media_type="text/markdown",
                                 headers={"Content-Disposition": f'attachment; filename="{svc.reader.sample}_report.md"'})

    return app


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn
    uvicorn.run(create_app(), host=host, port=port)
