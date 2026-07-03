#!/usr/bin/env python3
"""
CDP Bridge MCP vs Playwright MCP — LLM Tool Call Comparison

Loads cdp-bridge MCP and Playwright MCP separately,
and tests the efficiency difference of LLM completing tasks with the same user query.

Comparison dimensions:
  - Tool call count
  - Wall clock time
  - Token consumption (input / output)
  - API call rounds

Usage:
  python eval_mcp_compare.py                          # All test cases
  python eval_mcp_compare.py --query "search weather today"  # Single custom query
  python eval_mcp_compare.py --cdp-only                # Test CDP Bridge only
  python eval_mcp_compare.py --playwright-only         # Test Playwright only
  python eval_mcp_compare.py --dry-run                 # Start and list tools only

Dependencies:
  - CDP Bridge: Chrome is running and extension is connected
  - Playwright MCP: npx @playwright/mcp
  - LLM API: Anthropic-compatible interface (ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL)
"""

import subprocess
import json
import time
import sys
import os
import argparse
import threading
import queue
import urllib.request
import urllib.error
import re
import datetime
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path

# ── LLM API Configuration ─────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get(
    "ANTHROPIC_API_KEY",
    "sk-xxx",
)
ANTHROPIC_BASE_URL = os.environ.get(
    "ANTHROPIC_BASE_URL",
    "https://api.deepseek.com/anthropic",
)
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro")

# ── MCP Service Configuration ─────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# CDP Bridge: HTTP mode (requires service to be running, e.g. mcp-server-cdp-bridge)
CDP_BRIDGE_URL = os.environ.get("CDP_BRIDGE_URL", "http://localhost:8000/mcp")
# Fallback: stdio mode (auto-starts subprocess)
CDP_BRIDGE_CMD_FALLBACK = ["uv", "run", "cdp-bridge@latest"]
CDP_BRIDGE_CWD = str(PROJECT_ROOT)

PLAYWRIGHT_MCP_CMD = ["npx", "-y", "@playwright/mcp", "--headless"]
PLAYWRIGHT_MCP_CWD = None  # Use current working directory

# ── MCP Protocol Timeouts ─────────────────────────────────────────────────

MCP_INIT_TIMEOUT = 30
MCP_TOOL_TIMEOUT = 30
LLM_TIMEOUT = 60
MAX_TOOL_ROUNDS = 20  # Prevent infinite loops


# ═══════════════════════════════════════════════════════════════════════════
# MCP Client — Communicates with MCP service via stdio JSON-RPC
# ═══════════════════════════════════════════════════════════════════════════

class MCPClient:
    def __init__(self, name: str, cmd: list[str], cwd: str | None = None,
                 env: dict | None = None):
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.env = env
        self.proc: subprocess.Popen | None = None
        self._id = 0
        self._pending: dict[int, queue.Queue] = {}
        self._reader_thread: threading.Thread | None = None
        self.tools: dict[str, Any] = {}
        self._startup_errors: list[str] = []

    def start(self) -> bool:
        full_env = os.environ.copy()
        if self.env:
            full_env.update(self.env)

        try:
            self.proc = subprocess.Popen(
                self.cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.cwd,
                env=full_env,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError as e:
            print(f"  [{self.name}] Failed to start: {e}")
            return False

        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

        # stderr collection thread
        def _read_stderr():
            assert self.proc and self.proc.stderr
            for line in self.proc.stderr:
                self._startup_errors.append(line.strip())
                if len(self._startup_errors) > 50:
                    self._startup_errors.pop(0)

        threading.Thread(target=_read_stderr, daemon=True).start()

        init_result = self._call("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "eval-compare", "version": "1.0"},
        })
        if init_result is None:
            print(f"  [{self.name}] Initialization timed out")
            return False

        self._send_notification("notifications/initialized", {})

        tools_result = self._call("tools/list", {})
        if tools_result:
            for t in tools_result.get("tools", []):
                self.tools[t["name"]] = t
            print(f"  [{self.name}] Connected, {len(self.tools)} tools")

        return True

    def call_tool(self, tool_name: str, arguments: dict) -> tuple[dict | None, float]:
        if tool_name not in self.tools:
            return {"_skipped": True, "_reason": f"Tool {tool_name} does not exist"}, 0

        t0 = time.perf_counter()
        result = self._call("tools/call", {"name": tool_name, "arguments": arguments})
        elapsed = time.perf_counter() - t0

        if result is None:
            return {"_error": "timeout"}, elapsed
        return result, elapsed

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _send(self, payload: dict):
        if self.proc and self.proc.stdin:
            line = json.dumps(payload, ensure_ascii=False)
            self.proc.stdin.write(line + "\n")
            self.proc.stdin.flush()

    def _send_notification(self, method: str, params: dict):
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _call(self, method: str, params: dict) -> dict | None:
        req_id = self._next_id()
        q: queue.Queue = queue.Queue()
        self._pending[req_id] = q
        self._send({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        timeout = MCP_INIT_TIMEOUT if method == "initialize" else MCP_TOOL_TIMEOUT
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return None
        finally:
            self._pending.pop(req_id, None)

    def _read_loop(self):
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            req_id = msg.get("id")
            if req_id is not None and req_id in self._pending:
                if "result" in msg:
                    self._pending[req_id].put(msg["result"])
                elif "error" in msg:
                    self._pending[req_id].put({"_error": msg["error"]})


# ═══════════════════════════════════════════════════════════════════════════
# MCP Client HTTP — Communicates with remote MCP service via HTTP
# ═══════════════════════════════════════════════════════════════════════════

class MCPClientHTTP:
    """Communicates with MCP service via HTTP Streamable transport (no subprocess required)."""

    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url.rstrip("/")
        self.tools: dict[str, Any] = {}
        self._id = 0
        self._session_id: str | None = None
        # Bypass system proxy, direct connection to local MCP service
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def start(self) -> bool:
        init_result = self._call("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "eval-compare", "version": "1.0"},
        })
        if init_result is None:
            print(f"  [{self.name}] Initialization timed out")
            return False

        self._send_notification("notifications/initialized", {})

        tools_result = self._call("tools/list", {})
        if tools_result:
            for t in tools_result.get("tools", []):
                self.tools[t["name"]] = t
            print(f"  [{self.name}] Connected, {len(self.tools)} tools")

        return True

    def call_tool(self, tool_name: str, arguments: dict) -> tuple[dict | None, float]:
        if tool_name not in self.tools:
            return {"_skipped": True, "_reason": f"Tool {tool_name} does not exist"}, 0

        t0 = time.perf_counter()
        result = self._call("tools/call", {"name": tool_name, "arguments": arguments})
        elapsed = time.perf_counter() - t0

        if result is None:
            return {"_error": "timeout"}, elapsed
        return result, elapsed

    def stop(self):
        pass  # HTTP mode does not manage processes

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _send_notification(self, method: str, params: dict):
        self._post({"jsonrpc": "2.0", "method": method, "params": params})

    def _call(self, method: str, params: dict) -> dict | None:
        req_id = self._next_id()
        payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        timeout = MCP_INIT_TIMEOUT if method == "initialize" else MCP_TOOL_TIMEOUT
        return self._post(payload, timeout=timeout)

    def _post(self, payload: dict, timeout: int = MCP_TOOL_TIMEOUT) -> dict | None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(self.url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        if self._session_id:
            req.add_header("Mcp-Session-Id", self._session_id)

        try:
            with self._opener.open(req, timeout=timeout) as resp:
                # Save session ID
                sid = resp.headers.get("Mcp-Session-Id")
                if sid:
                    self._session_id = sid

                raw = resp.read().decode("utf-8")
                return self._parse_response(raw)

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            print(f"    [{self.name}] HTTP {e.code}: {error_body[:300]}")
            return None
        except Exception as e:
            print(f"    [{self.name}] Request failed: {e}")
            return None

    def _parse_response(self, raw: str) -> dict | None:
        """Parse HTTP response: direct JSON or SSE stream."""
        raw = raw.strip()

        # SSE format (text/event-stream)
        if raw.startswith("event:") or raw.startswith("data:"):
            for line in raw.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    data = line[5:].strip()
                    try:
                        msg = json.loads(data)
                        if "result" in msg:
                            return msg["result"]
                        elif "error" in msg:
                            return {"_error": msg["error"]}
                    except json.JSONDecodeError:
                        continue
            return None

        # Direct JSON response
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            print(f"    [{self.name}] Non-JSON response: {raw[:200]}")
            return None

        if "result" in msg:
            return msg["result"]
        elif "error" in msg:
            return {"_error": msg["error"]}
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Anthropic-compatible API — Message interface with tool use support
# ═══════════════════════════════════════════════════════════════════════════

def convert_mcp_tool_to_anthropic(mcp_tool: dict) -> dict:
    """Convert MCP tool definition to Anthropic tool format."""
    input_schema = mcp_tool.get("inputSchema", {}) or mcp_tool.get("input_schema", {})
    return {
        "name": mcp_tool["name"],
        "description": mcp_tool.get("description", "")[:1024],
        "input_schema": {
            "type": input_schema.get("type", "object"),
            "properties": input_schema.get("properties", {}),
            "required": input_schema.get("required", []),
        },
    }


def call_anthropic(
    messages: list[dict],
    tools: list[dict] | None,
    system: str = "",
    max_tokens: int = 4096,
) -> tuple[dict | None, float]:
    """Call Anthropic-compatible API with tool use support."""
    url = f"{ANTHROPIC_BASE_URL}/v1/messages"

    body: dict[str, Any] = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        body["system"] = system
    if tools:
        body["tools"] = tools

    data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("x-api-key", ANTHROPIC_API_KEY)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("content-type", "application/json")

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            elapsed = time.perf_counter() - t0
            return result, elapsed
    except urllib.error.HTTPError as e:
        elapsed = time.perf_counter() - t0
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"    [LLM] HTTP {e.code}: {error_body[:500]}")
        return None, elapsed
    except Exception as e:
        elapsed = time.perf_counter() - t0
        print(f"    [LLM] Request failed: {e}")
        return None, elapsed


def extract_text_from_content(content: list | str | None) -> str:
    """Extract plain text from Anthropic response content."""
    if isinstance(content, str):
        return content
    if not content:
        return ""
    texts = []
    for block in content:
        if isinstance(block, dict):
            if block.get("type") == "text":
                texts.append(block.get("text", ""))
        elif isinstance(block, str):
            texts.append(block)
    return " ".join(texts)


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ToolCallRecord:
    tool_name: str
    arguments: dict
    elapsed: float
    success: bool
    summary: str = ""


@dataclass
class RunResult:
    mcp_name: str
    query: str
    rounds: int = 0
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    api_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_elapsed: float = 0.0
    success: bool = False
    final_text: str = ""
    error: str = ""


# ═══════════════════════════════════════════════════════════════════════════
# Tool Call Loop
# ═══════════════════════════════════════════════════════════════════════════

def run_tool_loop(
    mcp: MCPClient,
    query: str,
    system_prompt: str = "",
) -> RunResult:
    """
    Run tool call loop:
    1. Send user query + tools to LLM
    2. LLM returns text or tool_use
    3. If tool_use, execute via MCP and feed result back to LLM
    4. Repeat until LLM returns plain text or max rounds reached
    """
    result = RunResult(mcp_name=mcp.name, query=query)
    t_start = time.perf_counter()

    tools = [convert_mcp_tool_to_anthropic(t) for t in mcp.tools.values()]
    if not tools:
        result.error = "MCP has no available tools"
        return result

    messages: list[dict] = [{"role": "user", "content": query}]

    for round_num in range(1, MAX_TOOL_ROUNDS + 1):
        result.rounds = round_num
        result.api_calls += 1

        response, llm_elapsed = call_anthropic(
            messages=messages,
            tools=tools,
            system=system_prompt,
        )

        if response is None:
            result.error = f"Round {round_num} API call failed"
            break

        # Accumulate tokens
        usage = response.get("usage", {})
        result.total_input_tokens += usage.get("input_tokens", 0)
        result.total_output_tokens += usage.get("output_tokens", 0)

        # Check stop_reason
        stop_reason = response.get("stop_reason", "")
        content = response.get("content", [])

        # Extract tool_use and text
        tool_use_blocks = []
        text_blocks = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "tool_use":
                    tool_use_blocks.append(block)
                elif block.get("type") == "text":
                    text_blocks.append(block.get("text", ""))

        # No tool_use → task complete
        if not tool_use_blocks:
            result.final_text = " ".join(text_blocks)
            result.success = True
            break

        # Build assistant message (containing tool_use and optional text)
        assistant_content: list[dict] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    assistant_content.append({"type": "text", "text": block.get("text", "")})
                elif block.get("type") == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block["id"],
                        "name": block["name"],
                        "input": block.get("input", {}),
                    })
        messages.append({"role": "assistant", "content": assistant_content})

        # Build tool_result message
        tool_results: list[dict] = []
        for tu_block in tool_use_blocks:
            tool_name = tu_block["name"]
            tool_id = tu_block["id"]
            tool_input = tu_block.get("input", {})

            # Execute tool
            mcp_result, tool_elapsed = mcp.call_tool(tool_name, tool_input)
            ok = mcp_result is not None and "_error" not in mcp_result and not mcp_result.get("_skipped")

            # Extract text for feedback to LLM
            result_text = _extract_tool_result_text(mcp_result)

            summary = _summarize_tool_result(tool_name, mcp_result, ok)
            result.tool_calls.append(ToolCallRecord(
                tool_name=tool_name,
                arguments=tool_input,
                elapsed=tool_elapsed,
                success=ok,
                summary=summary,
            ))

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": result_text[:8000],  # Truncate overly long content
            })

        messages.append({"role": "user", "content": tool_results})

    result.total_elapsed = time.perf_counter() - t_start
    return result


def _extract_tool_result_text(result: dict | None) -> str:
    """Extract text from MCP tool return value for LLM feedback."""
    if result is None:
        return "[Tool call timed out]"
    if "_error" in result:
        err = result["_error"]
        if isinstance(err, dict):
            return f"[Tool error: {err.get('message', str(err))[:300]}]"
        return f"[Tool error: {str(err)[:300]}]"
    if result.get("_skipped"):
        return f"[Tool skipped: {result.get('_reason', '')}]"

    # MCP content format
    content = result.get("content", [])
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict):
                t = item.get("text", "")
                if t:
                    texts.append(t)
        return "\n".join(texts)[:8000]
    if isinstance(content, str):
        return content[:8000]

    # Other formats
    return json.dumps(result, ensure_ascii=False)[:8000]


def _summarize_tool_result(tool_name: str, result: dict | None, ok: bool) -> str:
    if result is None:
        return "Timeout"
    if result.get("_skipped"):
        return f"Skipped: {result.get('_reason', '')[:50]}"
    if "_error" in result:
        err = result["_error"]
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        return f"Error: {msg[:60]}"
    if not ok:
        return "Failed"
    content = result.get("content", [])
    if isinstance(content, list):
        total_len = sum(len(json.dumps(c, ensure_ascii=False)) for c in content)
        return f"Returned {total_len:,} chars"
    if isinstance(content, str):
        return f"Returned {len(content):,} chars"
    return f"Complete"


# ═══════════════════════════════════════════════════════════════════════════
# Report Output
# ═══════════════════════════════════════════════════════════════════════════

def print_comparison(results: list[RunResult]) -> None:
    """Console comparison output."""
    print("\n" + "=" * 72)
    print("  Comparison Results")
    print("=" * 72)

    header = f"{'Metric':<22} {'CDP Bridge':>20} {'Playwright':>20}"
    print(header)
    print("-" * 72)

    cdps = [r for r in results if r.mcp_name == "CDP Bridge"]
    pws = [r for r in results if r.mcp_name == "Playwright"]

    for cdpr, pwr in zip(cdps, pws):
        label = cdpr.query[:40] + ("..." if len(cdpr.query) > 40 else "")
        print(f"\n  [{label}]")
        _print_row("Status", "✓ Success" if cdpr.success else f"✗ {cdpr.error[:30]}",
                    "✓ Success" if pwr.success else f"✗ {pwr.error[:30]}")
        _print_row("API Call Rounds", str(cdpr.api_calls), str(pwr.api_calls))
        _print_row("Tool Calls", str(len(cdpr.tool_calls)), str(len(pwr.tool_calls)))
        _print_row("Input Tokens", f"{cdpr.total_input_tokens:,}", f"{pwr.total_input_tokens:,}")
        _print_row("Output Tokens", f"{cdpr.total_output_tokens:,}", f"{pwr.total_output_tokens:,}")
        _print_row("Total Tokens", f"{cdpr.total_input_tokens + cdpr.total_output_tokens:,}",
                    f"{pwr.total_input_tokens + pwr.total_output_tokens:,}")
        _print_row("Total Time", f"{cdpr.total_elapsed:.1f}s", f"{pwr.total_elapsed:.1f}s")

        # Tool-level time breakdown
        cdp_tool_time = sum(tc.elapsed for tc in cdpr.tool_calls)
        pw_tool_time = sum(tc.elapsed for tc in pwr.tool_calls)
        _print_row("  Tool Execution Time", f"{cdp_tool_time:.1f}s", f"{pw_tool_time:.1f}s")
        _print_row("  LLM Time", f"{cdpr.total_elapsed - cdp_tool_time:.1f}s",
                    f"{pwr.total_elapsed - pw_tool_time:.1f}s")

        # Tool call details
        if cdpr.tool_calls:
            tools_cdp = ", ".join(f"{tc.tool_name}({tc.elapsed:.1f}s)" for tc in cdpr.tool_calls)
            print(f"    CDP Bridge tools: {tools_cdp}")
        if pwr.tool_calls:
            tools_pw = ", ".join(f"{tc.tool_name}({tc.elapsed:.1f}s)" for tc in pwr.tool_calls)
            print(f"    Playwright tools:  {tools_pw}")

    print("-" * 72)

    # Average comparison
    if cdps and pws:
        avg_cdp_rounds = sum(r.api_calls for r in cdps) / len(cdps)
        avg_pw_rounds = sum(r.api_calls for r in pws) / len(pws)
        avg_cdp_tools = sum(len(r.tool_calls) for r in cdps) / len(cdps)
        avg_pw_tools = sum(len(r.tool_calls) for r in pws) / len(pws)
        avg_cdp_tokens = sum(r.total_input_tokens + r.total_output_tokens for r in cdps) / len(cdps)
        avg_pw_tokens = sum(r.total_input_tokens + r.total_output_tokens for r in pws) / len(pws)
        avg_cdp_time = sum(r.total_elapsed for r in cdps) / len(cdps)
        avg_pw_time = sum(r.total_elapsed for r in pws) / len(pws)

        print(f"\n  {'Average Metrics':<22} {'CDP Bridge':>20} {'Playwright':>20}")
        print(f"  {'─'*22} {'─'*20} {'─'*20}")
        _print_row("API Rounds", f"{avg_cdp_rounds:.1f}", f"{avg_pw_rounds:.1f}")
        _print_row("Tool Calls", f"{avg_cdp_tools:.1f}", f"{avg_pw_tools:.1f}")
        _print_row("Tokens", f"{avg_cdp_tokens:,.0f}", f"{avg_pw_tokens:,.0f}")
        _print_row("Time", f"{avg_cdp_time:.1f}s", f"{avg_pw_time:.1f}s")

    print("=" * 72)


def _print_row(label: str, left: str, right: str):
    print(f"  {label:<22} {left:>20} {right:>20}")


def write_report(
    output_path: str,
    results: list[RunResult],
    cdp_tools: dict | None,
    pw_tools: dict | None,
) -> None:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md: list[str] = []

    md.append("# CDP Bridge vs Playwright — MCP Comparison Report")
    md.append("")
    md.append(f"**Test Time**: {now}")
    md.append(f"**LLM Model**: {ANTHROPIC_MODEL}")
    md.append(f"**API**: {ANTHROPIC_BASE_URL}")
    md.append("")

    # Tool list
    if cdp_tools:
        md.append("## 1. CDP Bridge Tool List")
        md.append("")
        md.append("| Tool Name | Description |")
        md.append("|--------|------|")
        for name, info in sorted(cdp_tools.items()):
            desc = info.get("description", "")[:120]
            md.append(f"| `{name}` | {desc} |")
        md.append("")

    if pw_tools:
        md.append("## 2. Playwright MCP Tool List")
        md.append("")
        md.append("| Tool Name | Description |")
        md.append("|--------|------|")
        for name, info in sorted(pw_tools.items()):
            desc = info.get("description", "")[:120]
            md.append(f"| `{name}` | {desc} |")
        md.append("")

    # Comparison table
    md.append("## 3. Comparison Results")
    md.append("")
    md.append("| Query | MCP | Status | API Rounds | Tool Calls | Input Tokens | Output Tokens | Total Tokens | Time |")
    md.append("|------|-----|------|---------|---------|----------|----------|---------|------|")

    for r in results:
        query_short = r.query[:50] + ("..." if len(r.query) > 50 else "")
        total_tokens = r.total_input_tokens + r.total_output_tokens
        status = "✓" if r.success else "✗"
        md.append(
            f"| {query_short} | {r.mcp_name} | {status} | {r.api_calls} | {len(r.tool_calls)} | "
            f"{r.total_input_tokens:,} | {r.total_output_tokens:,} | {total_tokens:,} | "
            f"{r.total_elapsed:.1f}s |"
        )
    md.append("")

    # Tool call details
    md.append("## 4. Tool Call Details")
    md.append("")
    for r in results:
        md.append(f"### {r.mcp_name} — `{r.query[:60]}`")
        md.append("")
        if r.tool_calls:
            md.append("| # | Tool | Arguments | Time | Status | Summary |")
            md.append("|---|------|------|------|------|------|")
            for i, tc in enumerate(r.tool_calls, 1):
                args_short = json.dumps(tc.arguments, ensure_ascii=False)[:80]
                status = "✓" if tc.success else "✗"
                md.append(f"| {i} | `{tc.tool_name}` | `{args_short}` | {tc.elapsed:.2f}s | {status} | {tc.summary[:50]} |")
        else:
            md.append("*(No tool calls)*")
        md.append("")
        if r.final_text:
            md.append(f"**LLM Final Output**: {r.final_text[:300]}")
        md.append("")

    content = "\n".join(md)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\nReport saved to: {output_path}")


# ═══════════════════════════════════════════════════════════════════════════
# Default Test Cases
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_QUERIES = [
    "Open Xiaohongshu and tell me the title of the first article on the homepage",
    "Browse https://www.runoob.com/numpy/numpy-tutorial.html and tell me about numpy bitwise operations in this tutorial site",
]


# ═══════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description="CDP Bridge vs Playwright MCP — LLM Tool Call Comparison"
    )
    p.add_argument("--query", type=str, nargs="*",
                   help="Custom test query (can be multiple)")
    p.add_argument("--cdp-only", action="store_true",
                   help="Test CDP Bridge MCP only")
    p.add_argument("--playwright-only", action="store_true",
                   help="Test Playwright MCP only")
    p.add_argument("--dry-run", action="store_true",
                   help="Start MCP service and list tools only")
    p.add_argument("--system-prompt", type=str, default="",
                   help="Custom system prompt")
    return p.parse_args()


def start_mcp_stdio(name: str, cmd: list[str], cwd: str | None) -> MCPClient | None:
    """Start MCP service in stdio mode (as subprocess)."""
    client = MCPClient(name, cmd, cwd=cwd)
    if client.start():
        return client
    client.stop()
    return None


def start_mcp_http(name: str, url: str) -> MCPClientHTTP | None:
    """Connect to MCP service in HTTP mode (service already running)."""
    client = MCPClientHTTP(name, url)
    if client.start():
        return client
    client.stop()
    return None


def main():
    args = parse_args()

    queries = args.query if args.query else DEFAULT_QUERIES
    test_cdp = not args.playwright_only
    test_pw = not args.cdp_only

    print("=" * 72)
    print("  CDP Bridge vs Playwright — MCP Comparison")
    print(f"  Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  LLM: {ANTHROPIC_MODEL}")
    print(f"  API: {ANTHROPIC_BASE_URL}")
    print(f"  Test CDP Bridge: {'Yes' if test_cdp else 'No'}")
    print(f"  Test Playwright: {'Yes' if test_pw else 'No'}")
    print(f"  Query count: {len(queries)}")
    print("=" * 72)

    cdp_client: MCPClient | MCPClientHTTP | None = None
    pw_client: MCPClient | MCPClientHTTP | None = None

    # ── Start MCP Service ──
    if test_cdp:
        print(f"\nConnecting to CDP Bridge (HTTP): {CDP_BRIDGE_URL}")
        cdp_client = start_mcp_http("CDP Bridge", CDP_BRIDGE_URL)
        if not cdp_client:
            # Fallback: try stdio mode
            print(f"  HTTP connection failed, trying stdio: {' '.join(CDP_BRIDGE_CMD_FALLBACK)}")
            cdp_client = start_mcp_stdio("CDP Bridge", CDP_BRIDGE_CMD_FALLBACK, CDP_BRIDGE_CWD)
        if not cdp_client:
            print("  CDP Bridge startup failed")

    if test_pw:
        print(f"\nStarting Playwright MCP: {' '.join(PLAYWRIGHT_MCP_CMD)}")
        pw_client = start_mcp_stdio("Playwright", PLAYWRIGHT_MCP_CMD, PLAYWRIGHT_MCP_CWD)
        if not pw_client:
            print("  Playwright MCP startup failed")

    # ── dry-run ──
    if args.dry_run:
        for client, label in [(cdp_client, "CDP Bridge"), (pw_client, "Playwright")]:
            if client:
                print(f"\n{label} tools ({len(client.tools)}):")
                for name, info in sorted(client.tools.items()):
                    desc = info.get("description", "")[:120]
                    print(f"  - {name}: {desc}")
        for c in [cdp_client, pw_client]:
            if c:
                c.stop()
        return

    # ── Execute Tests ──
    results: list[RunResult] = []
    system_prompt = args.system_prompt or (
        "You are a browser operation assistant. Use the provided tools to complete the user's task."
        "Give a concise summary after completing the task. If a tool call fails, try other methods."
    )

    for i, query in enumerate(queries):
        print(f"\n{'─'*72}")
        print(f"  Query {i+1}/{len(queries)}: {query}")
        print(f"{'─'*72}")

        clients_to_test = []
        if cdp_client:
            clients_to_test.append(cdp_client)
        if pw_client:
            clients_to_test.append(pw_client)

        for client in clients_to_test:
            print(f"\n  [{client.name}] Starting execution...")
            result = run_tool_loop(client, query, system_prompt)
            results.append(result)

            # Brief output
            status = "✓" if result.success else "✗"
            total_tokens = result.total_input_tokens + result.total_output_tokens
            print(f"  [{client.name}] {status} "
                  f"API:{result.api_calls} rounds "
                  f"Tools:{len(result.tool_calls)} calls "
                  f"Tokens:{total_tokens:,} "
                  f"Time:{result.total_elapsed:.1f}s")
            if result.error:
                print(f"    error: {result.error}")
            if result.final_text:
                print(f"    result: {result.final_text[:150]}")

    # ── Output Comparison ──
    if results:
        print_comparison(results)

        report_dir = Path(__file__).resolve().parent
        report_path = report_dir / "eval_compare_report.md"
        write_report(
            str(report_path),
            results,
            cdp_client.tools if cdp_client else None,
            pw_client.tools if pw_client else None,
        )

    # ── Cleanup ──
    print(f"\nCleaning up...")
    for c in [cdp_client, pw_client]:
        if c:
            c.stop()
    print("  All MCP services stopped")


if __name__ == "__main__":
    main()