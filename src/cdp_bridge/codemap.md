# cdp_bridge — codemap

## Responsibility

Bridges MCP clients to a real Chrome/Chromium browser via a bundled MV3 extension. Exposes 9 browser-automation tools (`browser_get_tabs`, `browser_scan`, `browser_execute_js`, `browser_switch_tab`, `browser_focus_tab`, `browser_batch`, `browser_wait`, `browser_navigate`, `browser_screenshot`). Supports stdio and streamable-http transports with per-token session isolation for multi-user and multi-Profile scenarios.

## Design

**Token isolation**: `TokenManager` maps token string -> `UserContext` (sessions, results, acks queues). Single-user mode uses a hardcoded `__default__` context. Each token is fully isolated.

**Session as tab**: `Session` class (session_id, info, ws_client/http_queue, type). Session.id is a Chrome tab ID (int as string). `default_session_id` on `UserContext` marks the active tab for MCP-side operations.

**Connection types**: Extension connects via WebSocket (`ext_ws`) on port 18765 or HTTP long-polling fallback on port+1 (18766). `session.type` determines delivery path in `execute_js()`.

**Remote mode**: If `socket.connect_ex((host, port+1)) == 0` at init, TMWebDriver proxies all `execute_js` calls to `http://host:port+1/link` via POST.

**execute_js ACK tracking**: Uses `ctx.acks` set to distinguish "script not delivered" (no ack) from "delivered but no result" (ack received, timed out). Timeout defaults to 15s.

**Embedded JS**: `simphtml.py` contains two large raw-JS strings (`js_optHTML` ~325 lines, `js_findMainList` ~265 lines) injected into the page via `execute_js`. These are hot-reloaded via `importlib.reload(simphtml)` before each `browser_execute_js` or `browser_scan` call so changes take effect without service restart.

**HTML pipeline**: `get_html()` calls `js_optHTML` in browser -> receives simplified DOM -> BeautifulSoup post-processing (`optimize_html_for_tokens`) -> optional `findMainList` truncation -> `smart_truncate` to maxchars budget.

## Flow

```
MCP tool call (server.py)
  -> _get_token() reads current_token ContextVar
  -> asyncio.to_thread(_run) [sync TMWebDriver call]
     -> TMWebDriver.execute_js(code, token=token)
        -> get_context(token) -> UserContext
        -> resolve session by default_session_id
        -> deliver payload: ws_client.send_message() [ext_ws] or http_queue.put() [http]
        -> poll ctx.results / ctx.acks every 0.2s until exec_id appears or timeout
        -> return {data, newTabs?}
```

**Extension bridge**:
```
background.js connects WS -> TMWebDriver._register_client()
  -> on tabs_update: registers/updates Session per tab
  -> on ack: writes exec_id to ctx.acks
  -> on result: writes to ctx.results with {success, data, newTabs}
```

**browser_scan flow**:
```
server.browser_scan()
  -> importlib.reload(simphtml)
  -> simphtml.get_html(driver, cutlist=True, token=token)
     -> driver.execute_js(js_findMainList) -> list candidates
     -> driver.execute_js(js_optHTML) -> simplified HTML
     -> BeautifulSoup: optimize_html_for_tokens()
     -> cutlist truncation via findMainList selectors
     -> smart_truncate() to maxchars
```

## Integration

- **Depends on**: `mcp` (FastMCP), `simple_websocket_server`, `bottle`, `beautifulsoup4`, `requests`, `uvicorn`
- **Extension side**: `tmwd_cdp_bridge/background.js` — WS client, CDP bridge, auto-reconnect ~5s
- **Consumers**: MCP clients (Claude Desktop, Codex, OpenCode, any MCP-compatible client)
- **Entry points**: `cdp_bridge` console script, `python -m cdp_bridge`, `uvx cdp-bridge@latest`
