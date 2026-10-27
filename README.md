# web_research — keyless web research MCP

A web research MCP server that needs **no API keys**. Search runs through the
DuckDuckGo HTML endpoint; fetching falls through multiple backends until one
succeeds.

## Tools

| Tool | What it does |
|---|---|
| `web_search(query, n=10)` | DuckDuckGo HTML search — titles, URLs, snippets. No key. |
| `fetch_url(url, timeout=25)` | Fetch one URL through the multi-backend chain: httpx → undici (Node) → playwright |
| `web_research(question, depth=3, per_round=6)` | Iterative research loop: search, fetch, refine, summarize across rounds |
| `providers()` | Report which fetch backends are available right now |
| `note_observation(observation, source_url, source_kind)` | Log a research finding with provenance |

## Install

```bash
git clone <this repo> && cd web_research
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
(cd node-deps && npm install)   # undici fallback backend
```

## Configure (any MCP client)

```json
{
  "mcpServers": {
    "web_research": {
      "command": "/path/to/web_research/.venv/bin/python",
      "args": ["/path/to/web_research/mcp_server.py"]
    }
  }
}
```

A Rust sibling of this server ships inside
[openklawc](https://github.com/ksohos333/openklawc) (`crates/mcp-web-research`).

## License

[MIT](LICENSE)
