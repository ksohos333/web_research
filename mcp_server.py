#!/usr/bin/env python3
"""
mcp_server.py — MCP server wrapping web_research.py.

Exposes tools:
    fetch_url(url, timeout)               — multi-backend fetch, returns {url, status, title, markdown, text, links, error, backend}
    web_search(query, n)                  — DuckDuckGo HTML search, returns {query, engine, items: [{url, title, snippet}]}
    web_research(question, depth, per_round) — multi-step research loop, returns evidence trail
    providers()                          — which fetch backends are present

stdio JSON-RPC transport. Wired into opencode via ~/.config/opencode/opencode.json.

Required env (set by opencode MCP config):
    WEB_RESEARCH_PY  — absolute path to web_research.py
    WEB_RESEARCH_PYTHON — absolute path to the python interpreter (defaults to argv[0]'s sibling)
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("web_research")

WEB_RESEARCH_PYTHON = Path(__file__).resolve().parent / ".venv" / "bin" / "python"

DEFAULT_TIMEOUT = 60


def _run(args: list[str], timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Run web_research.py with given args; return parsed JSON dict (or error wrapper)."""
    env = os.environ.copy()
    py = os.environ.get("WEB_RESEARCH_PYTHON", str(WEB_RESEARCH_PYTHON))
    script = os.environ.get("WEB_RESEARCH_PY")
    if not script:
        script = str(Path.home() / ".local" / "bin" / "web_research.py")
    if not Path(script).exists():
        return {"error": f"web_research.py not found at {script}"}
    if not Path(py).exists():
        return {"error": f"interpreter not found at {py}"}
    try:
        proc = subprocess.run(
            [py, script, *args],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"timeout after {timeout}s", "args": args}
    if proc.returncode != 0 and not proc.stdout.strip():
        return {
            "error": f"exit {proc.returncode}",
            "stderr": proc.stderr.strip()[-500:],
            "args": args,
        }
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return {
            "error": f"non-json output: {e}",
            "stdout_head": proc.stdout[:300],
            "stderr_tail": proc.stderr.strip()[-300:],
            "args": args,
        }


@mcp.tool()
def fetch_url(url: str, timeout: float = 25.0) -> dict:
    """Fetch one URL through the multi-backend fetcher (httpx → undici → playwright, if provisioned).

    Returns dict with: url, final_url, status, backend, fetched_at, title, markdown, text, links, notes, error.
    """
    res = _run(["fetch", url, "--timeout", str(int(timeout))], timeout=int(timeout * 2 + 30))
    if "error" in res and "url" not in res:
        res["url"] = url
    return res


@mcp.tool()
def web_search(query: str, n: int = 10) -> dict:
    """DuckDuckGo HTML search. No API key. Returns {query, engine, items: [{url, title, snippet}]}.

    n: max results to return (default 10).
    """
    return _run(["search", query, "-n", str(int(n))])


@mcp.tool()
def web_research(question: str, depth: int = 3, per_round: int = 6) -> dict:
    """Multi-step research loop: search → fetch top hits → extract follow-up sub-questions from titles → iterate.

    Returns the full evidence trail with rounds[].query, rounds[].results (search), and rounds[].fetches (each with url/status/backend/title/content).
    The calling LLM writes the actual prose from this structured trail.
    """
    return _run(
        ["research", question, "--depth", str(int(depth)), "--per-round", str(int(per_round))],
        timeout=120,
    )


@mcp.tool()
def providers() -> dict:
    """Show which fetch backends are available right now (httpx / undici / playwright)."""
    return _run(["providers"])


@mcp.tool()
def note_observation(observation: str, source_url: Optional[str] = None,
                     source_kind: str = "user") -> dict:
    """
    Tool the calling LLM can use to ATTACH a mark-of-observation to its own answer.
    Use this from a future session's prompt rules: whenever you're about to state a
    fact, call this with what was observed + how you observed it (user-claim, retrieval,
    prior knowledge, etc.). Returns the recorded note.
    """
    return {
        "recorded_at": time.time(),
        "source_kind": source_kind,
        "source_url": source_url,
        "observation": observation,
    }


if __name__ == "__main__":
    mcp.run()
