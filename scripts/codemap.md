# scripts/

## sync-version.py

Single-file script. Reads version from `pyproject.toml` (regex `version = "x.y.z"`), compares against `manifest.json`, and syncs the latter from the former.

### Flow

```
main()
  ├─ --publish-version <ver>  → write_pyproject_version() + write_manifest_version()
  ├─ --check                  → read both, compare, exit 1 on mismatch
  └─ (default)                → read both, overwrite manifest from pyproject if mismatch
```

### Key functions

| Function | Role |
|---|---|
| `read_version_pyproject()` | Regex extract `version = "..."` from pyproject.toml |
| `read_version_manifest()` | JSON load and return `data["version"]` |
| `write_manifest_version()` | JSON load, set `version`, write back 2-space indent |
| `write_pyproject_version()` | Regex substitute `version = "..."` line |

### File targets

- **Source**: `pyproject.toml` (project root)
- **Target**: `src/cdp_bridge/tmwd_cdp_bridge/manifest.json`
