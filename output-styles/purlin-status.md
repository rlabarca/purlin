# Purlin Status Output Style

Formats scan results into a structured, readable status report organized by mode.

## Format

```
## Project Status

**Branch:** <branch> | **Features:** <total> | **Scan:** <timestamp>

### Engineer Work
| Priority | Feature | Status | Action |
|----------|---------|--------|--------|
| 1 | feature_name | TODO | Implement from spec |

### PM Work
| Priority | Feature | Status | Action |
|----------|---------|--------|--------|
| 1 | feature_name | SPEC_MODIFIED | Review spec changes |

### QA Work
| Priority | Feature | Status | Action |
|----------|---------|--------|--------|
| 1 | feature_name | TESTING | Verify scenarios |
```
