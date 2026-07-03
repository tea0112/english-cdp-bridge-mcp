# CDP Bridge vs Playwright — MCP Comparative Evaluation Report

**Test Time**: 2026-06-23 01:55:06
**LLM Model**: deepseek-v4-pro
**API**: https://api.deepseek.com/anthropic

## 1. CDP Bridge Tools List

| Tool | Description |
|--------|------|
| `browser_batch` | Run multiple extension/CDP commands in one request.

Args:
    commands: Command objects supported by the extension, suc |
| `browser_execute_js` | Execute JavaScript in the browser and capture results plus DOM changes.

Args:
    script: JavaScript code to execute (o |
| `browser_focus_tab` | Bring a Chrome tab to the foreground: activate the tab AND focus its window.

Unlike browser_switch_tab (which only chan |
| `browser_get_tabs` | Get all open browser tabs with their IDs, URLs, and titles. |
| `browser_navigate` | Navigate the active tab to a URL.

Args:
    url: The URL to navigate to.
 |
| `browser_scan` | Get simplified HTML content of the active tab plus tab list. The HTML is optimized for LLM consumption (stripped of scri |
| `browser_screenshot` | Take a screenshot of the active tab (returns base64 PNG).

Args:
    tab_id: Optional tab ID to screenshot. Uses active  |
| `browser_switch_tab` | Switch the active MCP browser tab without changing the visible Chrome tab.

Args:
    tab_id: The tab ID to switch to (f |
| `browser_wait` | Wait until JavaScript condition returns a truthy value.

Args:
    condition_js: JavaScript expression or script. The re |
| `save_screenshot` | Save base64 screenshot data to PNG file.

Args:
    screenshot_json_str_or_file: JSON output from browser_screenshot too |

## 2. Playwright MCP Tools List

| Tool | Description |
|--------|------|
| `browser_click` | Perform click on a web page |
| `browser_close` | Close the page |
| `browser_console_messages` | Returns all console messages |
| `browser_drag` | Perform drag and drop between two elements |
| `browser_drop` | Drop files or MIME-typed data onto an element, as if dragged from outside the page. At least one of "paths" or "data" mu |
| `browser_evaluate` | Evaluate JavaScript expression on page or element |
| `browser_file_upload` | Upload one or multiple files |
| `browser_fill_form` | Fill multiple form fields |
| `browser_handle_dialog` | Handle a dialog |
| `browser_hover` | Hover over element on page |
| `browser_navigate` | Navigate to a URL |
| `browser_navigate_back` | Go back to the previous page in the history |
| `browser_network_request` | Returns full details (headers and body) of a single network request, or a single part if `part` is set. Use the number f |
| `browser_network_requests` | Returns a numbered list of network requests since loading the page. Use browser_network_request with the number to get f |
| `browser_press_key` | Press a key on the keyboard |
| `browser_resize` | Resize the browser window |
| `browser_run_code_unsafe` | Run a Playwright code snippet. Unsafe: executes arbitrary JavaScript in the Playwright server process and is RCE-equival |
| `browser_select_option` | Select an option in a dropdown |
| `browser_snapshot` | Capture accessibility snapshot of the current page, this is better than screenshot |
| `browser_tabs` | List, create, close, or select a browser tab. |
| `browser_take_screenshot` | Take a screenshot of the current page. You can't perform actions based on the screenshot, use browser_snapshot for actio |
| `browser_type` | Type text into editable element |
| `browser_wait_for` | Wait for text to appear or disappear or a specified time to pass |

## 3. Comparison Results

| Query | MCP | Status | API Rounds | Tool Calls | Input Tokens | Output Tokens | Total Tokens | Duration |
|------|-----|------|---------|---------|----------|----------|---------|------|
| Open Xiaohongshu and tell me the title of the first article on the homepage | CDP Bridge | ✓ | 3 | 2 | 3,668 | 322 | 3,990 | 6.1s |
| Open Xiaohongshu and tell me the title of the first article on the homepage | Playwright | ✗ | 20 | 20 | 13,691 | 3,057 | 16,748 | 114.2s |
| Browse https://www.runoob.com/numpy/numpy-tutorial.htm... | CDP Bridge | ✓ | 6 | 5 | 6,544 | 1,472 | 8,016 | 22.4s |
| Browse https://www.runoob.com/numpy/numpy-tutorial.htm... | Playwright | ✓ | 10 | 9 | 11,834 | 1,758 | 13,592 | 35.5s |

## 4. Tool Call Details

### CDP Bridge — `Open Xiaohongshu and tell me the title of the first article on the homepage`

| # | Tool | Args | Duration | Status | Summary |
|---|------|------|------|------|------|
| 1 | `browser_navigate` | `{"url": "https://www.xiaohongshu.com"}` | 0.42s | ✓ | Returned 109 chars |
| 2 | `browser_wait` | `{"condition_js": "document.querySelector('.note-item') || document.querySelector` | 0.41s | ✓ | Returned 14,855 chars |

**LLM Final Output**: The title of the first article on the Xiaohongshu homepage is:

**「Argentina vs Austria — Sabitzer's shot blocked in the 23rd minute」**

This article is from user 「**World Cup Moments**」, it's content with video, and currently has 10 likes.

### Playwright — `Open Xiaohongshu and tell me the title of the first article on the homepage`

| # | Tool | Args | Duration | Status | Summary |
|---|------|------|------|------|------|
| 1 | `browser_navigate` | `{"url": "https://www.xiaohongshu.com"}` | 6.69s | ✓ | Returned 664 chars |
| 2 | `browser_navigate` | `{"url": "https://m.xiaohongshu.com"}` | 2.20s | ✓ | Returned 662 chars |
| 3 | `browser_snapshot` | `{}` | 0.00s | ✓ | Returned 825 chars |
| 4 | `browser_click` | `{"target": "e12", "element": "Return to homepage button"}` | 2.05s | ✓ | Returned 656 chars |
| 5 | `browser_navigate` | `{"url": "https://www.xiaohongshu.com/explore"}` | 2.34s | ✓ | Returned 672 chars |
| 6 | `browser_navigate` | `{"url": "https://www.baidu.com/s?wd=%E5%B0%8F%E7%BA%A2%E4%B9%A6%E9%A6%96%E9%A1%B` | 1.06s | ✓ | Returned 975 chars |
| 7 | `browser_navigate` | `{"url": "https://www.bing.com/search?q=%E5%B0%8F%E7%BA%A2%E4%B9%A6+%E9%A6%96%E9%` | 0.64s | ✓ | Returned 407 chars |
| 8 | `browser_snapshot` | `{}` | 0.03s | ✓ | Returned 13,519 chars |
| 9 | `browser_navigate` | `{"url": "https://cn.bing.com/search?q=%E5%B0%8F%E7%BA%A2%E4%B9%A6+%E4%BB%8A%E6%9` | 0.32s | ✓ | Returned 539 chars |
| 10 | `browser_navigate` | `{"url": "https://www.google.com/search?q=site:xiaohongshu.com+%E9%A6%96%E9%A1%B5` | 5.57s | ✓ | Returned 801 chars |
| 11 | `browser_navigate` | `{"url": "https://duckduckgo.com/?q=%E5%B0%8F%E7%BA%A2%E4%B9%A6+%E9%A6%96%E9%A1%B` | 3.46s | ✓ | Returned 548 chars |
| 12 | `browser_snapshot` | `{}` | 0.02s | ✓ | Returned 10,862 chars |
| 13 | `browser_press_key` | `{"key": "Escape"}` | 0.02s | ✓ | Returned 118 chars |
| 14 | `browser_snapshot` | `{}` | 0.02s | ✓ | Returned 10,862 chars |
| 15 | `browser_click` | `{"target": "e133", "element": "Close menu button"}` | 5.03s | ✓ | Returned 1,084 chars |
| 16 | `browser_evaluate` | `{"function": "() => {\n  // Close the side menu if open\n  const closeBtn = docu` | 2.33s | ✓ | Returned 452 chars |
| 17 | `browser_take_screenshot` | `{"type": "png"}` | 0.09s | ✓ | Returned 357,941 chars |
| 18 | `browser_run_code_unsafe` | `{"code": "async (page) => {\n  // Close side menu\n  const closeBtn = page.locat` | 30.00s | ✗ | Error: timeout |
| 19 | `browser_evaluate` | `{"function": "() => {\n  // Close side menu\n  const closeBtn = document.querySe` | 6.04s | ✓ | Returned 974 chars |
| 20 | `browser_navigate` | `{"url": "https://www.sogou.com/web?query=%E5%B0%8F%E7%BA%A2%E4%B9%A6+%E9%A6%96%E` | 0.35s | ✓ | Returned 528 chars |


### CDP Bridge — `Browse https://www.runoob.com/numpy/numpy-tutorial.html and tell me about`

| # | Tool | Args | Duration | Status | Summary |
|---|------|------|------|------|------|
| 1 | `browser_navigate` | `{"url": "https://www.runoob.com/numpy/numpy-tutorial.html"}` | 0.43s | ✓ | Returned 130 chars |
| 2 | `browser_scan` | `{"text_only": true}` | 0.83s | ✓ | Returned 6,273 chars |
| 3 | `browser_execute_js` | `{"script": "\n// Find the \"NumPy Bitwise\" link\nconst links = document.querySelectorAll('a'` | 2.67s | ✓ | Returned 240 chars |
| 4 | `browser_navigate` | `{"url": "https://www.runoob.com/numpy/numpy-binary-operators.html"}` | 0.41s | ✓ | Returned 138 chars |
| 5 | `browser_scan` | `{"text_only": true}` | 0.82s | ✓ | Returned 8,075 chars |

**LLM Final Output**: Successfully retrieved all content from the NumPy bitwise operations page. Below is a summary of the **NumPy Bitwise Operations** content from this tutorial site:

---

## 📘 NumPy Bitwise Operations (Runoob Tutorial)

**Page URL**：`https://www.runoob.com/numpy/numpy-binary-operators.html`

### Overview
Bitwise operations are calculations that directly manipulate numbers at the binary bit level. NumPy provides vectorized bitwise operations through functions prefixed with `bitwise_`, which perform better than Python's native bitwise operators on arrays.

### Six Bitwise Operations Functions

| Operation | Function | Operator | Description |
|------|------|--------|--

### Playwright — `Browse https://www.runoob.com/numpy/numpy-tutorial.html and tell me about`

| # | Tool | Args | Duration | Status | Summary |
|---|------|------|------|------|------|
| 1 | `browser_navigate` | `{"url": "https://www.runoob.com/numpy/numpy-tutorial.html"}` | 4.02s | ✓ | Returned 315 chars |
| 2 | `browser_snapshot` | `{}` | 0.03s | ✓ | Returned 26,807 chars |
| 3 | `browser_click` | `{"target": "ref=e78", "element": "NumPy Bitwise Operations nav link"}` | 0.00s | ✓ | Returned 124 chars |
| 4 | `browser_navigate` | `{"url": "https://www.runoob.com/numpy/numpy-binary-operators.html"}` | 2.11s | ✓ | Returned 332 chars |
| 5 | `browser_snapshot` | `{}` | 0.05s | ✓ | Returned 38,895 chars |
| 6 | `browser_evaluate` | `{"function": "() => window.scrollTo(0, 0)"}` | 6.05s | ✓ | Returned 139 chars |
| 7 | `browser_take_screenshot` | `{"fullPage": true, "type": "png"}` | 0.38s | ✓ | Returned 429,778 chars |
| 8 | `browser_snapshot` | `{"boxes": true}` | 0.04s | ✓ | Returned 51,527 chars |
| 9 | `browser_evaluate` | `{"function": "() => {\n  const mainContent = document.querySelector('.article-bo` | 0.55s | ✓ | Returned 5,291 chars |

**LLM Final Output**: I have fully retrieved the content of the NumPy bitwise operations page. Below is a detailed summary of **NumPy Bitwise Operations** from this tutorial:

---

## NumPy Bitwise Operations (NumPy Binary Operators)

### Overview
Bitwise operations are a class of operations that manipulate numbers at the binary bit level, directly operating on individual bits of binary numbers. NumPy provides a series of bitwise operation functions prefixed with **`bitwise_`**, allowing element-wise bit manipulation on arrays with vectorized processing and better performance than Python's native bitwise operators.

---

### Six Bitwise Operations Functions

| Operation | Function | Description |
|------|------|------|
| **Bitwise AND** | 
