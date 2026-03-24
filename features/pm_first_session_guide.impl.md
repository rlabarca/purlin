# Implementation Notes: pm_first_session_guide

## Implementation Summary

The PM First Session Guide is implemented as behavioral instructions in `instructions/PM_BASE.md`, Sections 7.0, 7.0a, and 7.1. There is no standalone script or tool -- the PM agent follows these instruction sections during its startup protocol.

## Files Modified

- `instructions/PM_BASE.md` -- Section 7.1 (Figma MCP Availability Check): Completed the Figma MCP setup flow by adding the `claude mcp add` server registration step and the Claude restart step before the `/mcp` authentication steps. The flow now matches Section 4 (Figma MCP Setup).
- `tests/pm_first_session_guide/test_pm_startup.py` -- Fixed pre-existing test assertion that expected literal `tools/cdd/status.sh` but PM_BASE.md uses the `{tools_root}` template variable. Changed assertion to match on `cdd/status.sh --startup pm` which is present regardless of `tools_root` resolution.

## Discoveries

**[CLARIFICATION]** The test `test_pm_base_runs_startup_briefing` had a pre-existing failure due to matching against the resolved path `tools/cdd/status.sh` when PM_BASE.md uses the template variable form `{tools_root}/cdd/status.sh`. Fixed the assertion to match the substring `cdd/status.sh --startup pm` which is stable across both forms. (Severity: INFO)
