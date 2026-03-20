# Implementation Notes: Submodule Command Path Resolution

## Tool Location

- Command files: `.claude/commands/pl-*.md`
- Tests: `tests/submodule_command_path_resolution/test_command_paths.py`

## Implementation Decisions

**[CLARIFICATION]** The spec says use `{tools_root}/` notation. The existing files (pl-cdd.md, pl-spec-code-audit.md) use `${TOOLS_ROOT}/` (shell variable notation) and `<TOOLS_ROOT>/` (angle bracket notation). Standardized on `${TOOLS_ROOT}/` across all files as it matches the shell convention and the more complete existing pattern in pl-spec-code-audit.md. (Severity: INFO)

**[CLARIFICATION]** For the resolution preamble, used a compact single-paragraph format matching the pattern from pl-spec-code-audit.md: read config, resolve root, set variable. This keeps files concise while satisfying the requirement that each file includes the resolution step. (Severity: INFO)

**[CLARIFICATION]** pl-remote-pull.md already had partial `<tools_root>` notation (line 165-167). Standardized to `${TOOLS_ROOT}/` to match all other files. (Severity: INFO)

**[CLARIFICATION]** Files that don't reference any tool subdirectory paths (pl-remote-push.md, pl-agent-config.md, pl-find.md, pl-help.md, pl-override-edit.md, pl-propose.md, pl-discovery.md, pl-design-audit.md, pl-design-ingest.md, pl-fixture.md) were left unchanged — no preamble needed since they have no tool paths to resolve. (Severity: INFO)

## Scope of Changes

22 command files updated:
- 20 files: added Path Resolution preamble + converted hardcoded `tools/` paths to `${TOOLS_ROOT}/`
- 2 files (pl-cdd.md, pl-remote-pull.md): already had partial resolution, standardized notation
- pl-build.md: added web test gate pre-check in Step 4 (Requirement 2.4)
- pl-resume.md: converted Step 5 startup briefing path (Requirement 2.3)
