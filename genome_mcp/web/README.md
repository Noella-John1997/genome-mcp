# `web/` — the browser app

`app.py` builds a FastAPI app (`create_app()`), started with `genome-mcp web`.

| Endpoint | What it does |
| --- | --- |
| `GET /` | The web page |
| `POST /api/upload` | Upload a `.vcf` / `.vcf.gz` (max 20 MB) → session id. Deleted after 30 minutes. |
| `GET /api/{session}/overview` | QC, findings, pharmacogenomics, APOE and gene list in one call |
| `GET /api/{session}/gene/{gene}` | Variants in one gene |
| `GET /api/{session}/lookup?q=rs…` | One variant |
| `POST /api/{session}/ask` | Plain-English question → routed to a tool → `{tool, args, result}` |
| `GET /api/{session}/report.md` | Download the markdown report |
| `GET /health`, `GET /docs` | Health check and Swagger docs |

Use `demo` as the session id for the bundled synthetic sample. The Ask box uses the **same router
and the same tool functions** as the MCP server, and the page shows the tool call — a visual
explanation of what an AI agent does over MCP.

- [`static/`](static/) — the HTML, CSS and JS files.
