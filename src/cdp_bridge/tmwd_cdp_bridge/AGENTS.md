# Chrome Extension — tmwd_cdp_bridge

**Domain:** MV3 service worker + WebSocket bridge to Python CDP backend

## Components

### background.js
Service worker, WebSocket client, CDP debugger.
- `chrome.alarms.create("probe", {delayInMinutes: 0.0014})` for ~5s reconnect
- `connectWS()` → `isServerAlive()` → `wsBridge.send(JSON.stringify({type: "ext_ready", ...}))`
- `ext_ready` payload: `{type, version, token, tabs, ext_id}`
- `tabs_update` sent on `chrome.tabs.onUpdated` (status === "complete")
- Message types: `ext_ready`, `tabs_update`, `ack`, `result`, `error`
- CDP commands routed via `handleExtMessage()`: `cdp`, `batch`, `tabs`, `management`, `contentSettings`

### content.js
In-page badge "CDP Bridge connected", TID DOM element, MutationObserver.
- `chrome.runtime.sendMessage({type: "ext_tabs_update", tab})` to background
- TID element: `document.getElementById(`tid_${tid}`)` used for DOM identification

### popup.html/js
Connection config UI — host, port, token saved to `chrome.storage.local`.
- Reads `config.js` for TID on load

### manifest.json
MV3. Permissions: `debugger`, `scripting`, `tabs`, `alarms`.
- `host_permissions`: `<all_urls>`
- Content script runs in `MAIN` world (not isolated)

### config.js
TID auto-generated on first run. Gitignored. Not committed.

### disable_dialogs.js
CSP stripping via `declarativeNetRequest` rule ID 9999.

## Extension ↔ Backend Protocol

```
Connect:  WS open → {type: "ext_ready", version, token, tabs[], ext_id}
Tab update: {type: "tabs_update", tabId, url, title}
ACK: {type: "ack", seq}
Result: {type: "result", seq, data}
Error: {type: "error", seq, message}
```

## WebSocket Lifecycle

```
WS disconnect → scheduleProbe(5s) → isServerAlive() → connectWS()
```

## No `print()` — stderr only via console methods.