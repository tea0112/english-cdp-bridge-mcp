# CDP Bridge Core Package

## Symbols at a Glance

| Symbol | Type | Line | Role |
|-------|------|------|------|
| `Session` | class | TMWebDriver.py:18 | Per-tab state: id, info, url, type, ws_client/http_queue, reconnect() |
| `UserContext` | class | TMWebDriver.py:47 | Per-token isolation: sessions, results, acks, default_session_id, latest_session_id |
| `TokenManager` | class | TMWebDriver.py:71 | allowed_tokens set validation; get_context() lazy-creates UserContext |
| `TMWebDriver` | class | TMWebDriver.py:100 | Session manager; is_remote detection via socket.connect_ex((host, port+1)); starts WS server and HTTP server on port+1 |
| `execute_js()` | method | TMWebDriver.py:299 | Primary JS exec; 15s timeout; ACK tracking distinguishes "not delivered" vs "no result"; auto-switches to latest active session if target died |
| `_remote_cmd()` | method | TMWebDriver.py:364 | POSTs to remote /link; uses requests.Session(trust_env=False); raises ConnectionError if master unreachable |
| `mcp` | FastMCP | server.py:11 | Server instance, 9 tools |
| `configure_driver()` | func | server.py:19 | Singleton pattern; creates TMWebDriver once |
| `current_token` | ContextVar | server.py:13 | Set by TokenAuthMiddleware; read by _get_token() in tools |
| `TokenAuthMiddleware` | class | middleware.py:7 | Extracts Bearer token from auth header; validates against allowed_tokens; skips /health /favicon |

## Key Patterns

**Remote mode detection**: `socket.connect_ex((host, port+1)) == 0` at TMWebDriver.__init__. If remote host reachable, all execute_js calls proxy to `http://host:port+1/link` via `_remote_cmd()`.

**HTTP long-polling fallback**: Extension connects via HTTP to `port+1` (default 18766) when WS fails. Bottle app handles `/api/longpoll` (5s poll window) and `/api/result`.

**Session reconnect**: `Session.reconnect(client, info)` replaces ws_client or http_queue on the same session_id. Old connection marked disconnected.

**Token isolation**: In multi_user mode, each token maps to its own UserContext via TokenManager.get_context(). All sessions/results/acks are isolated.

**execute_js ACK tracking**: Line 341-342 checks if exec_id entered ctx.acks. Line 347-354 uses this to distinguish: no ACK = "script may not have been delivered"; ACK but no result = "delivered but no result".

**Remote execute_js**: POSTs to remote /link with cmd=execute_js, sessionId, code, timeout, token. Remote returns JSON with 'r' key.

**browser_execute_js / browser_scan**: Call `importlib.reload(simphtml)` before running to pick up embedded JS updates.

**Tab ID normalization**: `_normalize_tab_id()` converts tab_id string to int. Session.id stored as string.

## Anti-Patterns (Local)

- Do NOT call `socket.connect_ex()` yourself to check reachability; use `TMWebDriver.is_remote` after configure_driver()
- Do NOT send messages directly to `session.ws_client`; use `execute_js()` which handles ACK tracking and timeout
- Do NOT import TMWebDriver before `configure_driver()` is called; driver is None until then
- Do NOT assume HTTP long-poll will return within 5s; extension re-polls if no message available

## Extension Bridge Protocol (background.js side)

- Sends `ext_ready` / `tabs_update` on connect and tab changes
- Receives `{id, code, tabId}` payloads, responds with `{type: "ack", id}` then `{type: "result", id, result, newTabs}`
- WebSocket auto-reconnect handled by extension, not Python side