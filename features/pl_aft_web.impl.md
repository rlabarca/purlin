# Implementation Notes: AFT Web Command

*   **No Manual Scenarios (Intentional):** This feature automates the execution of Manual Scenarios and Visual Spec checks via Playwright MCP. It has no manual scenarios of its own because the feature's behavior is fully testable through automated scenarios exercising the skill's logic.
*   **Playwright MCP Dependency:** The skill depends on the `@playwright/mcp` npm package being available via `npx`. Auto-setup creates an MCP server entry via `claude mcp add`. A session restart is required after MCP server addition since Claude Code loads MCP servers at startup.
*   **Skill File Ownership:** Shared between Builder and QA. The Architect role guard in the skill file prevents accidental invocation by the Architect.
*   **Instruction File Updates (Section 2.13):** The Builder MUST update 7 instruction files to reference `/pl-aft-web`. These are listed exhaustively in the spec to ensure nothing is missed.
*   **Rename (2026-03-15):** Renamed from `/pl-web-verify` to `/pl-aft-web` as part of the Automated Feedback Tests (AFT) pattern. `> Web Testable:` metadata renamed to `> AFT Web:`, `> Web Start:` renamed to `> AFT Start:`, `> Web Port File:` removed (port file handling is now internal to the tool).

BUG — Playwright MCP was not running headless; skill now detects headed configuration and instructs user to reconfigure with --headless flag before proceeding.
DISCOVERY — Skill used hardcoded port from > AFT Web: metadata; now reads .purlin/runtime/cdd.port for dynamic port resolution, validates server liveness, and starts server via /pl-cdd if not running.
