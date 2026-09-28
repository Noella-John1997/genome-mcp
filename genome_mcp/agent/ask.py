"""A tiny MCP *client* agent: ask a question in plain English.

It starts the genome MCP server as a subprocess (stdio), lists its tools,
and then either:

* offline mode (default): routes the question to a tool with simple rules, or
* LLM mode (--llm): gives the tool list to an OpenAI-compatible model and
  lets it call tools in a loop (function calling) until it can answer.

This is the same thing Claude Desktop does when you add the server there.
"""
from __future__ import annotations

import json
import os
import re
import sys

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

KNOWN_GENES = ["APOE", "BRCA1", "BRCA2", "CFTR", "CYP2C19", "CYP2C9", "DPYD", "HBB", "HFE",
               "LDLR", "MCM6", "MLH1", "MTHFR", "SLCO1B1", "TP53", "VKORC1"]


def route_question(q: str) -> tuple[str, dict]:
    """Pick a tool + arguments for a question, without an LLM."""
    low = q.lower()
    if m := re.search(r"\brs\d+\b", low):
        return "lookup_variant", {"query": m.group(0)}
    if "apoe" in low or "alzheimer" in low:
        return "apoe_genotype", {}
    if re.search(r"drug|medic|pharmaco|warfarin|clopidogrel|statin|dose", low):
        return "pharmacogenomics", {}
    for g in KNOWN_GENES:
        if re.search(rf"\b{g.lower()}\b", low):
            return "gene_variants", {"gene": g}
    if m := re.search(r"chr?(\w+):(\d+)-(\d+)", low):
        return "query_region", {"chrom": m.group(1), "start": int(m.group(2)), "end": int(m.group(3))}
    if re.search(r"report", low):
        return "genome_report", {}
    if re.search(r"pathogenic|disease|risk|carrier|cancer|worry|health", low):
        return "clinically_relevant", {}
    return "vcf_summary", {}


def _server_params(vcf: str | None) -> StdioServerParameters:
    args = ["-m", "genome_mcp.cli", "serve"] + (["--vcf", vcf] if vcf else [])
    return StdioServerParameters(command=sys.executable, args=args)


def _text(result) -> str:
    return "\n".join(getattr(c, "text", "") for c in result.content)


async def _llm_loop(session: ClientSession, question: str) -> str:
    tools = (await session.list_tools()).tools
    oa_tools = [{"type": "function", "function": {"name": t.name, "description": t.description or "",
                                                  "parameters": t.inputSchema}} for t in tools]
    messages = [{"role": "system", "content": "You answer questions about the user's genome using the tools. "
                 "Explain simply, distinguish carrier from affected, and always add the disclaimer."},
                {"role": "user", "content": question}]
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("GENOME_MCP_LLM_MODEL", "gpt-4o-mini")
    async with httpx.AsyncClient(timeout=60) as http:
        for _ in range(6):
            r = await http.post(f"{base}/chat/completions",
                                headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                                json={"model": model, "messages": messages, "tools": oa_tools})
            r.raise_for_status()
            msg = r.json()["choices"][0]["message"]
            messages.append(msg)
            if not msg.get("tool_calls"):
                return msg.get("content") or ""
            for call in msg["tool_calls"]:
                args = json.loads(call["function"]["arguments"] or "{}")
                res = await session.call_tool(call["function"]["name"], args)
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": _text(res)})
    return "Stopped after 6 tool rounds."


async def ask(question: str, vcf: str | None = None, use_llm: bool = False) -> str:
    async with stdio_client(_server_params(vcf)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if use_llm:
                return await _llm_loop(session, question)
            tool, args = route_question(question)
            res = await session.call_tool(tool, args)
            body = _text(res)
            try:
                body = json.dumps(json.loads(body), indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                pass
            return f"[tool: {tool} {args}]\n{body}"
