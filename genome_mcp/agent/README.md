# `agent/` — an MCP client

`ask.py` shows the *client* side of MCP:

1. Starts the server as a subprocess (`python -m genome_mcp.cli serve`) and connects over **stdio**.
2. `initialize` → `list_tools`.
3. Answers the question in one of two ways:

| Mode | How it works | Needs |
| --- | --- | --- |
| Offline (default) | `route_question()` uses keyword rules to pick one tool | nothing |
| `--llm` | Sends the tool list to an OpenAI-compatible model as function definitions and loops: model asks for a tool → client calls it on the MCP server → result goes back → … until the model answers (max 6 rounds) | `OPENAI_API_KEY` |

The LLM mode is the same loop Claude Desktop runs internally.
