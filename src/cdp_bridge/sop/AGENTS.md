# SOP — Standard Operation Procedures

Canonical references for browser automation quirks and Vue3 component handling. **Consult before working on CDP or Vue3 automation.**

## Files

| File | Purpose |
|------|---------|
| `tmwebdriver_sop.md` | CDP quirks, limitations, isTrusted bypass, click lifecycle, iframe, auto-reconnect |
| `vue3_component_sop.md` | Vue3 vnode traversal, proxy method calls, v-model, Date handling |

## Critical Rules

### isTrusted=false

CDP bypasses all browser security events. If automation is blocked, use Vue3 vnode method call instead — it runs inside the app's event system and is fully trusted.

### CDP Click Sequence

CDP `Input.dispatchMouseEvent` alone is insufficient. Use:
```
mouseMoved → wait 50-100ms → mousePressed → wait 50-100ms → mouseReleased
```
Each step requires explicit `type: "mouseMoved"|"mousePressed"|"mouseReleased"`.

### First Attach Coordinate Shift

Chrome shows an infobar on first CDP connection. This shifts page coordinates. **Measure all positions AFTER the first attach.**

### File Upload

Use DataTransfer API in JavaScript. **Never** use CDP `DOM.setFileInputFiles` — it has known nodeId issues.

### vnode Method Call

Traverse: `vnode → findCompByEl(el) → proxy`. This bypasses isTrusted and viewport constraints. Preferred over CDP for Vue3 apps.

### browser_batch

Prefer `browser_batch` over passing raw JSON strings to CDP. The bridge handles command routing and error recovery.

### Auto-Reconnect

Extension auto-probes WebSocket every ~5s via `chrome.alarms`. Survives MV3 service worker suspension.

## Quick Reference

```
vnode traversal:  vnode → findCompByEl(el) → proxy method call
click sequence:    mouseMoved → wait 50-100ms → mousePressed → wait 50-100ms → mouseReleased
file upload:       DataTransfer API (JavaScript)
isTrusted bypass:  vnode method call
tab ID:            Chrome tab ID (string, not UUID)
```