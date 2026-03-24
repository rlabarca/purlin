# Implementation Notes: Web Test Command

*   **No Manual Scenarios (Intentional):** This feature automates the execution of Manual Scenarios and Visual Spec checks via Playwright MCP. It has no manual scenarios of its own because the feature's behavior is fully testable through automated scenarios exercising the skill's logic.
*   **Playwright MCP Dependency:** The skill depends on the `@playwright/mcp` npm package being available via `npx`. Auto-setup creates an MCP server entry via `claude mcp add`. A session restart is required after MCP server addition since Claude Code loads MCP servers at startup.
*   **Skill File Ownership:** Shared between Builder and QA. The Architect role guard in the skill file prevents accidental invocation by the Architect.
*   **Instruction File Updates (Section 2.13):** The Builder MUST update 7 instruction files to reference `/pl-web-test`. These are listed exhaustively in the spec to ensure nothing is missed.
*   **Rename History:**
    *   (2026-03-15) Renamed from `/pl-web-verify` to `/pl-aft-web`. `> Web Testable:` -> `> AFT Web:`, `> Web Start:` -> `> AFT Start:`.
    *   (2026-03-18) Renamed from `/pl-aft-web` to `/pl-web-test`. `> AFT Web:` -> `> Web Test:`, `> AFT Start:` -> `> Web Start:`. AFT taxonomy removed.

BUG -- Playwright MCP was not running headless; skill now detects headed configuration and instructs user to reconfigure with --headless flag before proceeding.
DISCOVERY -- Skill used hardcoded port from > Web Test: metadata; now reads .purlin/runtime/cdd.port for dynamic port resolution, validates server liveness, and starts server via /pl-cdd if not running.

**[CLARIFICATION]** QA_BASE.md test assertion relaxed: the spec says "Add brief reference in Section 5.4" but QA_BASE.md doesn't have a Section 5.4 subsection -- the visual verification protocol (including Section 5.4.7) is in the on-demand loaded `visual_verification_protocol.md`. Test verifies `/pl-web-test` appears in authorized commands instead. (Severity: INFO)

### Audit Finding -- 2026-03-19

[DISCOVERY] No unit tests for port resolution, auto-start, or Playwright detection logic — Acknowledged

**Source:** /pl-spec-code-audit --deep (item #24)
**Severity:** MEDIUM
**Details:** The spec defines specific behaviors for dynamic port resolution (reading `.purlin/runtime/cdd.port`), auto-starting the CDD server via `/pl-cdd`, and detecting/configuring Playwright MCP. These are implemented in the skill command file as agent instructions, but no automated tests verify these code paths. The existing tests focus on command file structure and keyword presence.
**Suggested fix:** Add test scenarios that verify: (a) port resolution reads from `.purlin/runtime/cdd.port` and falls back correctly, (b) server auto-start is triggered when the port file is missing or server is not responding, (c) Playwright MCP detection logic (checking for `@playwright/mcp` availability). These could be structural tests verifying the command file contains the required logic references, consistent with the existing test pattern for agent skills.

**[DISCOVERY] [ACKNOWLEDGED]** STALE verdict discovery format test too shallow
**Source:** /pl-spec-code-audit --deep (M25)
**Severity:** MEDIUM
**Details:** The test `test_stale_not_recorded_as_bug_discovery` only checks that the word "STALE" appears in the command file. It does not validate the 6-field discovery format, sidecar file creation, or the distinct STALE commit message pattern (`discovery(scope): [STALE] web-test findings for PM re-ingestion`).
**Suggested fix:** Add assertions for all 6 required STALE discovery fields and the commit message format.

