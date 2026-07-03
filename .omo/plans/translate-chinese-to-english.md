# translate-chinese-to-english - Work Plan

## TL;DR (For humans)
<!-- Fill this LAST, after the detailed plan below is written, so it summarizes the REAL plan. -->
<!-- Plain English for a non-engineer: NO file paths, NO todo numbers, NO wave/agent/tool names. -->

**What you'll get:** Every Chinese text string in the codebase — documentation, code comments, embedded JS logs, Python strings, extension UI labels, and evaluation scripts — replaced with English equivalents. The repo becomes fully English.

**Why this approach:** Straight in-place substitution per file; no logic touched. All 15 files are independent so they parallelize cleanly. The user confirmed: replace `README.md` (English counterpart already at `doc/README_EN.md`), translate all debug `console.log` strings, and include the `reports/` directory.

**What it will NOT do:** Change any code logic, function signatures, API behavior, or file structure. Only strings, comments, log messages, UI labels, and documentation text are translated.

**Effort:** Medium
**Risk:** Low — string-only changes, no behavioral changes
**Decisions to sanity-check:** None remaining — all decisions made during planning.

Your next move: approve to begin execution. Full execution detail follows below.

---

> TL;DR (machine): Medium effort, Low risk, translate all Chinese strings in 15 files across docs/code/extension/eval

## Scope
### Must have
- Translate `README.md` from Chinese to English in-place (English version already exists at `doc/README_EN.md`)
- Translate `CLAUDE.md` from Chinese to English in-place
- Translate `src/cdp_bridge/sop/vue3_component_sop.md` — all Chinese SOP text → English
- Translate `src/cdp_bridge/sop/tmwebdriver_sop.md` — all Chinese SOP text → English
- Translate `src/cdp_bridge/simphtml.py` — Chinese in embedded JS `console.log` strings + Python `log()` import-error message + comment strings
- Translate `src/cdp_bridge/TMWebDriver.py` — Chinese `_tlog()` log messages
- Translate `src/cdp_bridge/__init__.py` — Chinese comments
- Translate `scripts/sync-version.py` — Chinese docstring + print messages + comments
- Translate `tmwd_cdp_bridge/manifest.json` — Chinese `description` field
- Translate `tmwd_cdp_bridge/popup.html` — "Token (http模式下的用户标识)" label + "保存连接配置" button
- Translate `tmwd_cdp_bridge/background.js` — Chinese comments
- Translate `tmwd_cdp_bridge/content.js` — "CDP Bridge 已连接" title + popup messages
- Translate `reports/V-001-2026-06-22/eval_mcp_compare.py` — all Chinese print labels and inline comments
- Translate `reports/V-001-2026-06-22/eval_compare_report.md` — Chinese evaluation report text
- Translate `doc/README_EN.md` — "中文" link text → "Chinese"

### Must NOT have (guardrails, anti-slop, scope boundaries)
- Do NOT change any code logic, function bodies, or variable names
- Do NOT change any file paths, structure, or gitignore entries
- Do NOT touch `pyproject.toml`, `uv.lock`, or any build configuration files
- Do not translate content inside string literals that are user-generated (e.g., scraped page content) — only translate project-authored strings

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: none — no behavior changes; verification is structural
- After each file edit: run `grep -P "[\x{4e00}-\x{9fff}]"` on that file to confirm zero remaining Chinese characters
- Final pass: run `grep -rP "[\x{4e00}-\x{9fff}]"` on the entire repo and confirm zero matches
- Evidence: per-file grep output saved as `.omo/evidence/task-<N>-translate-chinese-to-english.txt`

## Execution strategy
### Parallel execution waves
> 15 files, 3 waves of 5 each (Wave 1 docs, Wave 2 source code, Wave 3 extension + reports). No cross-file dependencies.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| T1-T5 | none | T6-T10 | within wave |
| T6-T10 | none | T11-T15 | within wave |
| T11-T15 | none | final | within wave |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [ ] 1. Translate README.md (Chinese → English in-place)
  What to do / Must NOT do: Replace every Chinese text segment with English equivalent. Do NOT change markdown structure, links, or code blocks. Preserve the bilingual link at the top.
  Parallelization: Wave 1 | Blocked by: none | Blocks: none
  References (executor has NO interview context - be exhaustive): README.md lines 17–446 (full file)
  Acceptance criteria (agent-executable): `grep -oP "[\x{4e00}-\x{9fff}]" README.md | wc -l` returns 0
  QA scenarios: happy — file reads as clean English prose; failure — `grep -oP "[\x{4e00}-\x{9fff}]"` returns any non-empty match
  Evidence: .omo/evidence/task-1-translate-chinese-to-english.txt
  Commit: Y | docs: translate README.md to English

- [ ] 2. Translate CLAUDE.md (Chinese → English in-place)
  What to do / Must NOT do: Replace every Chinese text segment with English equivalent. Do NOT change the JSON schema content or command examples.
  Parallelization: Wave 1 | Blocked by: none | Blocks: none
  References (executor has NO interview context - be exhaustive): CLAUDE.md lines 5–49 (full file)
  Acceptance criteria (agent-executable): `grep -oP "[\x{4e00}-\x{9fff}]" CLAUDE.md | wc -l` returns 0
  QA scenarios: happy — file reads as clean English; failure — `grep -oP "[\x{4e00}-\x{9fff}]"` returns any non-empty match
  Evidence: .omo/evidence/task-2-translate-chinese-to-english.txt
  Commit: Y | docs: translate CLAUDE.md to English

- [ ] 3. Translate src/cdp_bridge/sop/vue3_component_sop.md (Chinese → English)
  What to do / Must NOT do: Translate all Chinese text. Do NOT change code examples, function signatures, or markdown headings structure.
  Parallelization: Wave 1 | Blocked by: none | Blocks: none
  References (executor has NO interview context - be exhaustive): src/cdp_bridge/sop/vue3_component_sop.md lines 1–163 (full file)
  Acceptance criteria (agent-executable): `grep -oP "[\x{4e00}-\x{9fff}]" src/cdp_bridge/sop/vue3_component_sop.md | wc -l` returns 0
  QA scenarios: happy — SOP reads as clean English; failure — Chinese chars remain
  Evidence: .omo/evidence/task-3-translate-chinese-to-english.txt
  Commit: Y | docs: translate vue3_component_sop.md to English

- [ ] 4. Translate src/cdp_bridge/sop/tmwebdriver_sop.md (Chinese → English)
  What to do / Must NOT do: Translate all Chinese text. Do NOT change code examples or markdown structure.
  Parallelization: Wave 1 | Blocked by: none | Blocks: none
  References (executor has NO interview context - be exhaustive): src/cdp_bridge/sop/tmwebdriver_sop.md (full file, ~99+ lines with Chinese)
  Acceptance criteria (agent-executable): `grep -oP "[\x{4e00}-\x{9fff}]" src/cdp_bridge/sop/tmwebdriver_sop.md | wc -l` returns 0
  QA scenarios: happy — SOP reads as clean English; failure — Chinese chars remain
  Evidence: .omo/evidence/task-4-translate-chinese-to-english.txt
  Commit: Y | docs: translate tmwebdriver_sop.md to English

- [ ] 5. Translate reports/V-001-2026-06-22/eval_compare_report.md (Chinese → English)
  What to do / Must NOT do: Translate all Chinese text in the evaluation report. Do NOT change table structure, metric names, or numeric data.
  Parallelization: Wave 1 | Blocked by: none | Blocks: none
  References (executor has NO interview context - be exhaustive): reports/V-001-2026-06-22/eval_compare_report.md (full file)
  Acceptance criteria (agent-executable): `grep -oP "[\x{4e00}-\x{9fff}]" reports/V-001-2026-06-22/eval_compare_report.md | wc -l` returns 0
  QA scenarios: happy — report reads as clean English; failure — Chinese chars remain
  Evidence: .omo/evidence/task-5-translate-chinese-to-english.txt
  Commit: Y | docs: translate eval_compare_report.md to English

- [ ] 6. Translate src/cdp_bridge/simphtml.py (Chinese strings/logs/comments)
  What to do / Must NOT do: Translate Chinese in: (a) Python import-error `log()` messages, (b) embedded JS `console.log` strings (e.g. '覆盖', '子元素', '无法序列化'), (c) Chinese strings in `rr['suggestion']` values. Do NOT change any Python logic, function names, or JS logic.
  Parallelization: Wave 2 | Blocked by: none | Blocks: none
  References (executor has NO interview context - be exhaustive): src/cdp_bridge/simphtml.py — line 7 (import error), lines 27/149/167/175/182-192/210/235/239/339/354/369/372/419/423/430/442/446-584/671-673/700/750-877 (embedded JS + Python strings)
  Acceptance criteria (agent-executable): `grep -oP "[\x{4e00}-\x{9fff}]" src/cdp_bridge/simphtml.py | wc -l` returns 0
  QA scenarios: happy — no Chinese chars; failure — Chinese chars remain in JS strings or Python
  Evidence: .omo/evidence/task-6-translate-chinese-to-english.txt
  Commit: Y | code: translate simphtml.py strings to English

- [ ] 7. Translate src/cdp_bridge/TMWebDriver.py (Chinese _tlog messages)
  What to do / Must NOT do: Translate Chinese log messages in `_tlog()` calls. Do NOT change any logic, WebSocket handling, or function behavior.
  Parallelization: Wave 2 | Blocked by: none | Blocks: none
  References (executor has NO interview context - be exhaustive): src/cdp_bridge/TMWebDriver.py — line 319 ("会话 {id} 未连接，自动切换"), line 322 ("会话ID {id} 未连接"), line 378 ("TMWebDriver master未运行"), lines 411-414 (multiple Chinese log strings)
  Acceptance criteria (agent-executable): `grep -oP "[\x{4e00}-\x{9fff}]" src/cdp_bridge/TMWebDriver.py | wc -l` returns 0
  QA scenarios: happy — no Chinese chars; failure — Chinese chars remain in log output
  Evidence: .omo/evidence/task-7-translate-chinese-to-english.txt
  Commit: Y | code: translate TMWebDriver.py Chinese log messages to English

- [ ] 8. Translate src/cdp_bridge/__init__.py (Chinese comments)
  What to do / Must NOT do: Translate Chinese comments about FastMCP DNS rebinding protection. Do NOT change any code logic or function behavior.
  Parallelization: Wave 2 | Blocked by: none | Blocks: none
  References (executor has NO interview context - be exhaustive): src/cdp_bridge/__init__.py — lines 57, 62 (Chinese comments)
  Acceptance criteria (agent-executable): `grep -oP "[\x{4e00}-\x{9fff}]" src/cdp_bridge/__init__.py | wc -l` returns 0
  QA scenarios: happy — no Chinese comments; failure — Chinese chars remain
  Evidence: .omo/evidence/task-8-translate-chinese-to-english.txt
  Commit: Y | code: translate __init__.py Chinese comments to English

- [ ] 9. Translate scripts/sync-version.py (Chinese docstring + print messages)
  What to do / Must NOT do: Translate Chinese docstring, print error messages, and comments. Do NOT change Python logic or file I/O behavior.
  Parallelization: Wave 2 | Blocked by: none | Blocks: none
  References (executor has NO interview context - be exhaustive): scripts/sync-version.py — lines 2-6 (docstring), lines 23, 48, 68, 75 (print/comment strings)
  Acceptance criteria (agent-executable): `grep -oP "[\x{4e00}-\x{9fff}]" scripts/sync-version.py | wc -l` returns 0
  QA scenarios: happy — no Chinese chars; failure — Chinese chars remain in output or docstring
  Evidence: .omo/evidence/task-9-translate-chinese-to-english.txt
  Commit: Y | code: translate sync-version.py strings to English

- [ ] 10. Translate reports/V-001-2026-06-22/eval_mcp_compare.py (Chinese labels + comments)
  What to do / Must NOT do: Translate all Chinese print labels, f-string content, and inline comments. Do NOT change any API call logic, test queries, or evaluation behavior.
  Parallelization: Wave 2 | Blocked by: none | Blocks: none
  References (executor has NO interview context - be exhaustive): reports/V-001-2026-06-22/eval_mcp_compare.py — Chinese labels in _print_row calls, Chinese strings in print statements (description, help, etc.), Chinese in markdown report builder
  Acceptance criteria (agent-executable): `grep -oP "[\x{4e00}-\x{9fff}]" reports/V-001-2026-06-22/eval_mcp_compare.py | wc -l` returns 0
  QA scenarios: happy — no Chinese chars in output; failure — Chinese chars remain in print output
  Evidence: .omo/evidence/task-10-translate-chinese-to-english.txt
  Commit: Y | code: translate eval_mcp_compare.py strings to English

- [ ] 11. Translate tmwd_cdp_bridge/manifest.json (Chinese description)
  What to do / Must NOT do: Translate Chinese description field to English. Do NOT change any JSON structure, keys, or version numbers.
  Parallelization: Wave 3 | Blocked by: none | Blocks: none
  References (executor has NO interview context - be exhaustive): tmwd_cdp_bridge/manifest.json line 5 (description field)
  Acceptance criteria (agent-executable): `grep -oP "[\x{4e00}-\x{9fff}]" tmwd_cdp_bridge/manifest.json | wc -l` returns 0
  QA scenarios: happy — manifest description in English; failure — Chinese chars remain
  Evidence: .omo/evidence/task-11-translate-chinese-to-english.txt
  Commit: Y | ext: translate manifest.json description to English

- [ ] 12. Translate tmwd_cdp_bridge/popup.html (Chinese UI labels)
  What to do / Must NOT do: Translate "Token (http模式下的用户标识)" label to "Token (http mode user identifier)" and "保存连接配置" button to "Save connection config". Do NOT change any HTML structure, CSS classes, or JS references.
  Parallelization: Wave 3 | Blocked by: none | Blocks: none
  References (executor has NO interview context - be exhaustive): tmwd_cdp_bridge/popup.html — line 42 (Token label), line 44 (save button)
  Acceptance criteria (agent-executable): `grep -oP "[\x{4e00}-\x{9fff}]" tmwd_cdp_bridge/popup.html | wc -l` returns 0
  QA scenarios: happy — no Chinese chars; failure — Chinese label/button text remains
  Evidence: .omo/evidence/task-12-translate-chinese-to-english.txt
  Commit: Y | ext: translate popup.html Chinese UI text to English

- [ ] 13. Translate tmwd_cdp_bridge/background.js (Chinese comments)
  What to do / Must NOT do: Translate Chinese comments (插件页面交互事件 → "Extension page interaction events", 业务事件 → "Business logic events"). Do NOT change any JS logic or WebSocket handling.
  Parallelization: Wave 3 | Blocked by: none | Blocks: none
  References (executor has NO interview context - be exhaustive): tmwd_cdp_bridge/background.js — lines 62, 75 (Chinese comments), line 200 (cannot-serialize error string)
  Acceptance criteria (agent-executable): `grep -oP "[\x{4e00}-\x{9fff}]" tmwd_cdp_bridge/background.js | wc -l` returns 0
  QA scenarios: happy — no Chinese chars; failure — Chinese chars remain
  Evidence: .omo/evidence/task-13-translate-chinese-to-english.txt
  Commit: Y | ext: translate background.js Chinese comments to English

- [ ] 14. Translate tmwd_cdp_bridge/content.js (Chinese status messages)
  What to do / Must NOT do: Translate "CDP Bridge 已连接" badge title → "CDP Bridge connected", and the popup notice title/message. Do NOT change any DOM manipulation, badge CSS, or event handling logic.
  Parallelization: Wave 3 | Blocked by: none | Blocks: none
  References (executor has NO interview context - be exhaustive): tmwd_cdp_bridge/content.js — line 14 (d.title), line 40 (notice title), line 77 (会话活跃 notice text)
  Acceptance criteria (agent-executable): `grep -oP "[\x{4e00}-\x{9fff}]" tmwd_cdp_bridge/content.js | wc -l` returns 0
  QA scenarios: happy — no Chinese chars; failure — Chinese chars remain
  Evidence: .omo/evidence/task-14-translate-chinese-to-english.txt
  Commit: Y | ext: translate content.js Chinese strings to English

- [ ] 15. Translate doc/README_EN.md (Chinese link text)
  What to do / Must NOT do: Change the link text "中文" to "Chinese" in the bilingual nav at the top of the English README. Do NOT change the URL or link structure.
  Parallelization: Wave 3 | Blocked by: none | Blocks: none
  References (executor has NO interview context - be exhaustive): doc/README_EN.md line 21 ("中文" link text)
  Acceptance criteria (agent-executable): `grep -oP "[\x{4e00}-\x{9fff}]" doc/README_EN.md | wc -l` returns 0
  QA scenarios: happy — link text is "Chinese"; failure — link still reads "中文"
  Evidence: .omo/evidence/task-15-translate-chinese-to-english.txt
  Commit: Y | docs: translate README_EN.md Chinese link text to English

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit
- [ ] F2. Code quality review
- [ ] F3. Real manual QA
- [ ] F4. Scope fidelity

## Commit strategy
- Each todo is committed individually (Y in Commit column)
- Commit type: `docs` for documentation files, `code` for Python source, `ext` for Chrome extension files
- Summary format: `translate <file> to English`
- Example: `docs: translate README.md to English`

## Success criteria
- `grep -rP "[\x{4e00}-\x{9fff}]"` across the entire repo returns zero matches
- Every file that previously contained Chinese reads as clean English prose or code comments
- No code logic, API behavior, file structure, or URL has changed
- All 15 todos show Commit: Y with evidence files in `.omo/evidence/`
