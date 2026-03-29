# Implementation Notes: Submodule Command Path Resolution

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|


## Tool Location

- Skill files: `skills/*/SKILL.md`
- Tests: `tests/submodule_command_path_resolution/test_command_paths.py`

## Implementation Decisions

**[CLARIFICATION]** The spec says use `{tools_root}/` notation. The existing files (skills/spec-code-audit/SKILL.md and others) use `${TOOLS_ROOT}/` (shell variable notation) and `<TOOLS_ROOT>/` (angle bracket notation). Standardized on `${TOOLS_ROOT}/` across all files as it matches the shell convention and the more complete existing pattern in skills/spec-code-audit/SKILL.md. (Severity: INFO)

**[CLARIFICATION]** For the resolution preamble, used a compact single-paragraph format matching the pattern from skills/spec-code-audit/SKILL.md: read config, resolve root, set variable. This keeps files concise while satisfying the requirement that each file includes the resolution step. (Severity: INFO)

**[CLARIFICATION]** skills/remote-pull/SKILL.md already had partial `<tools_root>` notation (line 165-167). Standardized to `${TOOLS_ROOT}/` to match all other files. (Severity: INFO)

**[CLARIFICATION]** Files that don't reference any tool subdirectory paths (skills/remote-push/SKILL.md, skills/agent-config/SKILL.md, skills/find/SKILL.md, skills/help/SKILL.md, skills/override-edit/SKILL.md, skills/propose/SKILL.md, skills/discovery/SKILL.md, skills/design-audit/SKILL.md, skills/design-ingest/SKILL.md, skills/fixture/SKILL.md) were left unchanged — no preamble needed since they have no tool paths to resolve. (Severity: INFO)

## Scope of Changes

21 skill files updated:
- 20 files: added Path Resolution preamble + converted hardcoded `tools/` paths to `${TOOLS_ROOT}/`
- 1 file (skills/remote-pull/SKILL.md): already had partial resolution, standardized notation
- skills/build/SKILL.md: added web test gate pre-check in Step 4 (Requirement 2.4)
- skills/resume/SKILL.md: converted Step 5 startup briefing path (Requirement 2.3)
