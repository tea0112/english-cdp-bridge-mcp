# PROJECT KNOWLEDGE BASE

**Generated:** 2026-07-03
**Commit:** (run `git rev-parse HEAD` for hash)
**Branch:** (run `git branch --show-current`)

## OVERVIEW

CDP Bridge MCP bridges LLM clients to a **real browser** (Chrome/Chromium) the user already has open — with login state, cookies, and page rendering preserved. NOT a headless automation tool. Python + FastMCP + Chrome extension WebSocket/CDP.

Stack: Python 3.10+, FastMCP, BeautifulSoup4, simple-websocket-server, bottle.

## STRUCTURE

```
./
├── src/cdp_bridge/        # Main package
│   ├── __init__.py        # CLI entry: main(), configure_driver(), extension_path()
│   ├── __main__.py        # python -m cdp_bridge fallback entry
│   ├── server.py           # FastMCP instance + 9 @mcp.tool() async functions
│   ├── TMWebDriver.py      # Session management, WebSocket/HTTP bridging, execute_js
│   ├── simphtml.py         # Browser HTML optimization (embedded JS + BeautifulSoup)
│   ├── middleware.py       # TokenAuthMiddleware for streamable-http
│   ├── sop/                # Standard Operation docs
│   │   ├── tmwebdriver_sop.md      # quirks, CDP, isTrusted limitations
│   │   └── vue3_component_sop.md   # Vue3 component JS manipulation via vnode
│   └── tmwd_cdp_bridge/    # Chrome extension (MV3)
│       ├── background.js   # WS client + CDP bridge + auto-reconnect ~5s
│       ├── content.js      # In-page indicator badge + TID DOM element
│       ├── popup.html/js   # Connection config UI
│       └── manifest.json
├── scripts/
│   └── sync-version.py     # Sync version pyproject.toml ↔ manifest.json
├── doc/
│   └── README_EN.md       # English-only README
├── reports/               # Benchmark/eval artifacts (one-off)
├── pyproject.toml         # setuptools src/ layout, 2 console scripts
└── CLAUDE.md              # Developer guidance (this project has no AGENTS.md convention)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add MCP tool | `server.py` | Decorate with `@mcp.tool()` — wraps sync code with `asyncio.to_thread()` |
| Change session/WS logic | `TMWebDriver.py` | Session class, WebSocket/HTTP bridging, execute_js timeout handling |
| HTML optimization | `simphtml.py` | `optHTML()` embedded JS, BeautifulSoup post-processing |
| Browser extension | `tmwd_cdp_bridge/` | background.js (WS+CDP), content.js (badge), popup.html |
| Token auth / multi-user | `middleware.py` + `__init__.py` | `TokenAuthMiddleware`, `_run_with_token_middleware()` |
| Version sync | `scripts/sync-version.py` | CLI: `sync-version.py [--publish-version VER] [--check]` |
| Vue3 component ops | `sop/vue3_component_sop.md` | vnode → findCompByEl → proxy method call |
| CDP/SOP details | `sop/tmwebdriver_sop.md` | isTrusted, CDP click, file upload, iframe |

## CODE MAP

| Symbol | Type | Location | Refs | Role |
|--------|------|----------|------|------|
| `mcp` | FastMCP | server.py:11 | 2 | Server instance — 9 tools |
| `configure_driver()` | func | server.py:19 | 2 | Creates/singleton TMWebDriver |
| `get_driver()` | func | server.py:25 | 1 | Legacy compat |
| `browser_get_tabs` | tool | server.py:55 | 0 | Tab list + active tab |
| `browser_scan` | tool | server.py:70 | 0 | Simplified HTML + tab list |
| `browser_execute_js` | tool | server.py:107 | 0 | JS exec + DOM diff |
| `browser_switch_tab` | tool | server.py:130 | 0 | MCP-side tab switch |
| `browser_focus_tab` | tool | server.py:154 | 0 | chrome.tabs.update (brings to front) |
| `browser_batch` | tool | server.py:192 | 0 | Multi-command via ext bridge |
| `browser_wait` | tool | server.py:211 | 0 | Poll JS condition |
| `browser_navigate` | tool | server.py:259 | 0 | Navigate active tab |
| `browser_screenshot` | tool | server.py:276 | 0 | PNG base64 |
| `browser_save_image` | tool | server.py:299 | 0 | Save screenshot to PNG |
| `TMWebDriver` | class | TMWebDriver.py:100 | 2 | Session + token manager |
| `execute_js()` | method | TMWebDriver.py:299 | 10 | Primary JS execution |
| `simphtml.get_html()` | func | simphtml.py | 2 | Simplified HTML for LLM |
| `simphtml.execute_js_rich()` | func | simphtml.py | 1 | JS exec + DOM change diff |

## CONVENTIONS

- **Logs → stderr**: Use `log()` in TMWebDriver.py and `log()` in simphtml.py. NEVER `print()` — stdout is MCP JSON-RPC protocol; `print()` corrupts the stream causing `Transport closed` errors.
- **execute_js reload**: `browser_execute_js` calls `importlib.reload(simphtml)` before each call so embedded JS updates take effect without service restart.
- **Session ID = tab ID** (string). `default_session_id` marks the active target tab.
- **15s ACK tracking**: `execute_js()` distinguishes "script not delivered" (no ACK) from "delivered but no result" (ACK received).
- **No tests, no lint, no CI/CD** — project ships as-is.
- **`src/` layout only**: all packages under `src/cdp_bridge/`.

## ANTI-PATTERNS (THIS PROJECT)

- **NEVER** `print()` to stdout — MCP protocol breaks.
- **NEVER** call `mcp.run()` directly in normal startup — go through `main()` in `__init__.py` which handles driver config + transport mode.
- **NEVER** edit `manifest.json` version manually — use `scripts/sync-version.py`.
- Do NOT use `selenium` or `playwright` vocabulary — this is a bridge to the user's real browser, not an automation driver.

## UNIQUE STYLES

- Tab ID is a Chrome tab ID (integer as string) — not an internal session UUID.
- Multi-user isolation: `streamable-http` mode with `TokenManager` per-token contexts, Bearer token in `Authorization` header.
- `browser_scan` + `browser_execute_js` both call `importlib.reload(simphtml)` before use to pick up embedded JS updates.
- Extension reconnect: `background.js` auto-probes WS every ~5s via `chrome.alarms` (survives MV3 suspension).
- `browser_focus_tab` uses `chrome.tabs.update` + `chrome.windows.update` (NOT CDP `Target.activateTarget` which is blocked in MV3).
- File upload via `DataTransfer` API in JS (no CDP `DOM.setFileInputFiles` — that method has nodeId issues in this bridge).

## COMMANDS

```bash
# Install dev deps
uv sync

# Run as MCP stdio service (primary)
uv run cdp-bridge

# Or via console script (after uv sync / pip install)
cdp-bridge
# or
python -m cdp_bridge

# Get extension directory for manual browser loading
uv run cdp-bridge --help  # has extension_path subcommand
cdp-bridge-extension-path

# streamable-http mode
uv run cdp-bridge --transport streamable-http --port 8000 --ws-port 18765

# Sync version (dev)
python scripts/sync-version.py
python scripts/sync-version.py --check
python scripts/sync-version.py --publish-version 0.1.22

# Build PyPI package
uv build
```

## NOTES

- `simphtml.py` contains ~500 lines of embedded JS for `optHTML()` and `findMainList()` — this is injected into the browser page, not run in Python.
- `TMWebDriver.py` uses a bottle-based HTTP server on `port+1` for the HTTP long-polling fallback (`:18766` by default).
- Extension loads at `chrome://extensions/` → "Load unpacked" → select `src/cdp_bridge/tmwd_cdp_bridge/`.
- First WS connection after extension load may show `ERR_CONNECTION_REFUSED` — extension auto-reconnects in ~5s.

## Repository Map

A full codemap is available at `codemap.md` in the project root.

Before working on any task, read `codemap.md` to understand:
- Project architecture and entry points
- Directory responsibilities and design patterns
- Data flow and integration points between modules

For deep work on a specific folder, also read that folder's `codemap.md`.