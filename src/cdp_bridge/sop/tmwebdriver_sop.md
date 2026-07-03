# TMWebDriver SOP

- Use `browser_scan`/`browser_execute_js` directly. This file only documents quirks and pitfalls.
- Low-level: `../TMWebDriver.py` controls the user's real browser via a Chrome extension (preserves login state/Cookies)
- Not Selenium/Playwright; preserves the user's browser login state

## Common Features
- ⚠ When using `await` in `browser_execute_js`, you **must explicitly `return`** to get the return value (the underlying async wrapper returns null without a return statement)
- ✅ `browser_scan` automatically pierces same-origin iframes; cross-origin iframes require CDP or postMessage (see section below)

## Limitations (isTrusted)
- JS events have `isTrusted=false`; sensitive operations (like file uploads/some buttons) may be blocked; for these scenarios prefer the **CDP bridge**
- ⚠ JS-clicking a button can't open new tab → might be browser popup blocker, try CDP click instead
- Vue3 custom components (Select/Dropdown): ⭐ Prefer vnode instance call (no viewport restrictions) → see **vue3_component_sop**; CDP coordinate click only suitable for few visible options
- File upload: ⭐ Prefer **DataTransfer API** (pure JS, no CDP dependency): `new File([content],name,{type}) → new DataTransfer().items.add(file) → input.files=dt.files → dispatch input+change`; CDP `DOM.setFileInputFiles` has invalid nodeId across calls in the tmwd bridge environment, not recommended; fallback ljqCtrl physical click
- When converting to physical coordinates: `physX = (screenX + rectCenterX) * dpr`, `physY = (screenY + chromeH + rectCenterY) * dpr`; where `chromeH = outerHeight - innerHeight`

## Navigation
- `browser_scan` only reads the current page without navigating; use `browser_navigate` or `browser_execute_js` + `location.href='url'` to switch sites

## Google Image Search
- Class names are obfuscated, avoid hardcoding; use `[role=button]` div to click results
- `browser_scan` filters sidebars; after popup, use JS: text via `document.body.innerText`, large images traverse img and take src by `naturalWidth` max
- "Visit" links: iterate a to find href where `textContent.includes('Visit')`
- Thumbnails: `img[src^="data:image"]` extract directly; large image src may be truncated, use `return img.src`

## Chrome Download PDF
Scenario: PDF link previews in browser instead of downloading
```js
fetch('PDF_URL').then(r=>r.blob()).then(b=>{
  const a=document.createElement('a');
  a.href=URL.createObjectURL(b);
  a.download='filename.pdf';
  a.click();
});
```
Note: Requires same-origin or CORS allowed; for cross-origin, navigate to target domain first, then execute

## Chrome Background Tab Throttling
- `setTimeout` in background tabs gets delayed by Chrome intensive throttling to ≥1min/per execution; avoid relying on setTimeout polling in extension scripts
- Some SPA pages need CDP `Page.bringToFront` to switch to foreground before loading data

## CDP Bridge (tmwd_cdp_bridge extension) ⭐ Preferred
Extension path: `assets/tmwd_cdp_bridge/` (needs installation, includes debugger permission)
⚠ TID convention identifier: auto-generated on first run to `assets/tmwd_cdp_bridge/config.js` (gitignored), extension references via manifest
Prefer using MCP tools: `browser_batch`. When necessary also use `browser_execute_js` script passing JSON string directly (tool layer auto-identifies object format, goes WS→background.js cmd routing)
```js
browser_batch commands='[{"cmd":"cdp","method":"Page.bringToFront","params":{}}]'
browser_batch commands='[{"cmd":"cdp","method":"DOM.getDocument","params":{"depth":1}}]'
browser_execute_js script='{"cmd":"contentSettings","type":"automaticDownloads","setting":"allow"}'
browser_execute_js script='{"cmd": "tabs"}'
// Return value is directly JSON result
```
Communication methods: ⭐MCP dedicated tools (preferred) | JSON string direct pass | TID DOM method (TID element+MutationObserver, browser_scan/browser_execute_js underlying dependency)
Single command: `{cmd:'tabs'}` | `{cmd:'cookies'}` | `{cmd:'cdp', tabId:N, method:'...', params:{...}}` | `{cmd:'management', method:'list|reload|disable|enable', extId:'...'}`
- management: list returns all extension info; reload/disable/enable need extId
- contentSettings: `{cmd:'contentSettings', type:'automaticDownloads', pattern:'https://*/*', setting:'allow'}`
  - Bypass Chrome "download multiple files" dialog (this dialog blocks entire browser JS execution)
  - type options: automaticDownloads/popups/notifications etc; setting: allow/block/ask
  - ⚠ CDP's Browser.setDownloadBehavior is unavailable in extensions (chrome.debugger is tab-level only), this is the alternative
- ⭐batch mixing: `{cmd:'batch', commands:[{cmd:'cookies'},{cmd:'tabs'},{cmd:'cdp',...},...]}`
  - Returns `{ok:true, results:[...]}`; one request multiple commands, CDP lazy attach reuses session
  - Sub-commands automatically inherit outer batch's tabId (e.g. cookies command can correctly get current page URL)
  - `$N.path` references the Nth result field (0-indexed), e.g. `"nodeId":"$2.root.nodeId"`
  - ⚠ When a preceding batch command fails, subsequent `$N` references silently become undefined; check ok status of each item in results array
  - Typical file upload: getDocument(**depth:1**) → querySelector(`input[type=file]`) → setFileInputFiles
  - Philosophy:
    - Keep nodeId source consistent within the same chain; don't mix querySelector paths with performSearch paths
    - After upload, frontend framework may not be aware; dispatch `input`/`change` events via JS when needed
    - Before upload check `input.accept`; with multiple inputs, use accept/parent container semantics to differentiate
    - When waiting for elements, prefer `DOM.performSearch('input[type=file]')` for lightweight polling
    - Core of transient input is **shortening the discovery→setFileInputFiles time window**: prioritize completing in same batch; if not possible use DOM event listening; monkey patching only as fallback
  - ⚠ tabId: CDP defaults to sender.tab.id (current injection page), cross-tab needs explicit tabId or first query tabs in batch
- ⭐ Cross-tab doesn't need foreground: specify tabId to operate on background tab

## CDP Click Full Lifecycle (✅ Verified)
- Generic click needs **three-event sequence**: mouseMoved → mousePressed → mouseReleased (50-100ms interval)
  - Omitting mouseMoved breaks hover-dependent components like MUI Tooltip/Ant Design Dropdown
  - ⚠ autofill release is special: only mousePressed needed (see autofill section below)
- ⭐**Coordinate system conclusion**: In stable state CDP coordinates = `getBoundingClientRect()` coordinates, **no correction needed**
  - ⚠**First attach trap**: When CDP debugger first attaches, Chrome pops up infobar ("Chrome is being controlled by automated test", ~20px tall), page content is pushed down
  - If measuring coordinates before attach and sending clicks after attach → coordinate offset! (root cause of Currency dropdown failure before)
  - ✅**Solution**: Ensure coordinate measurement happens after CDP is stably attached (i.e., after infobar has appeared, then getBoundingClientRect)
  - Practice: Before first CDP operation, send a harmless `mouseMoved(0,0)` to warm up; after that coordinates are stable
- ⭐**Dropdown (Vue3 oxd-select etc) CDP operation flow**:
  1. Get select element rect → CDP click to open dropdown
  2. Get option element rect → CDP click to select (option is dynamic DOM, can only measure after opening)
  - Verified: CDP click works on custom dropdowns, no isTrusted issue
  - ⚠**Limitation**: When options are many and bottom options extend beyond viewport, CDP coordinates can't reach → in this case prefer vnode solution (see vue3_component_sop)
- Coordinate correction (when page has transform:scale/zoom):
  ```js
  var scale = window.visualViewport ? window.visualViewport.scale : 1;
  var zoom = parseFloat(getComputedStyle(document.documentElement).zoom) || 1;
  var realX = x * zoom; var realY = y * zoom;
  ```
- CDP click on iframe elements: coordinates need composition `finalX = iframeRect.x + elRect.x`
  - Cross-origin iframe can't get contentDocument:
  - ⚠`Target.getTargets`/`Target.attachToTarget` return "Not allowed" in CDP bridge (chrome.debugger permission limitation)
  - ⭐**Verified solution**: `Page.getFrameTree` to find iframe frameId → `Page.createIsolatedWorld({frameId})` to get contextId → `Runtime.evaluate({expression, contextId})` executes JS in iframe
  - Batch chained reference: `$0.frameTree.childFrames` iterates to find url-matching frame, `$1.executionContextId` passed to evaluate
  - postMessage relay only works when content script is already injected into iframe; third-party payment iframes usually have no injection

## CDP Text Input (Unverified, BBS#23)
- `insertText` is fast but no key events; controlled components need to supplement dispatch `input` event
- For full keyboard simulation use `dispatchKeyEvent` to dispatch each key

## CDP DOM Domain Piercing closed Shadow DOM (Unverified, BBS#24/#25)
- `DOM.getDocument({depth:-1, pierce:true})` pierces all Shadow boundaries (including closed)
- `DOM.querySelector({nodeId, selector})` locates → `DOM.getBoxModel({nodeId})` gets coordinates
- getBoxModel returns content box eight values [x1,y1,...x4,y4], center uses **four-point average**: centerX=sum(x)/4, centerY=sum(y)/4
  - ⚠ Cannot simplify to diagonal average — when element has transform:rotate/skew, four points are not a rectangle
- querySelector **cannot write compound selectors across Shadow boundaries**; need to do in steps: find host first, then find child elements in its shadow
- ⚠ nodeId becomes invalid after DOM changes → use `backendNodeId` for more stability, or re-call getDocument to refresh


## Autofill Acquisition and Login
Detection: browser_scan output inputs with `data-autofilled="true"`, value shows as protected hint (not actual value, Chrome security protection requires click to release)
- ⚠**Prerequisite: must first CDP `Page.bringToFront` to switch tab to foreground**, Chrome only releases autofill protection in foreground tab, background tab physical click is invalid
- ⭐**One-click release and login**: bringToFront → mousePressed click any field (no release needed, one release affects entire page) → wait 500ms → dispatch input/change events → click login

## Captcha/Page Visual Screenshot
- ⭐ Preferred CDP screenshot: `Page.captureScreenshot`(format:'png')→returns base64, no need for foreground/background tab, full page HD
- Captcha canvas/img: JS `canvas.toDataURL()` directly get base64 is cleanest

## simphtml and TMWebDriver Debugging
- simphtml debugging must use `code_run` to inject JS into real browser (Python side can't simulate DOM)
- `d=TMWebDriver()`, `d.set_session('url_pattern')`, `d.execute_js(code)` → returns `{'data': value}`
- simphtml: `str(simphtml.optimize_html_for_tokens(html))` — returns BS4 Tag, need str()