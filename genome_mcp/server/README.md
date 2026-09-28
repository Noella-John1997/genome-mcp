# `server/` - the MCP server

`mcp_server.py` uses the official MCP Python SDK (`FastMCP`). Each `@mcp.tool()` function becomes a
tool that clients discover with `list_tools` and run with `call_tool`. The function's **docstring is
the description the LLM reads**, and its type hints become the JSON schema for the arguments - so
they are written carefully.

- `build_server(vcf_path, live)` → `(FastMCP server, GenomeService)`; used by tests too.
- `run_stdio()` → runs over **stdio**, the transport Claude Desktop and most MCP clients use.
- Server `instructions` tell the model to always pass on the disclaimer and to explain carrier vs affected.

## What MCP is

MCP is like USB-C for AI tools: one standard plug. A **server** offers tools, resources and prompts;
a **client** (inside an AI app) connects, lists them and calls them with JSON-RPC messages. The same
server works in Claude Desktop, Cursor, VS Code and custom agents without changes.
