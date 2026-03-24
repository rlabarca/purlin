# User Testing Discoveries: PM First Session Guide

### [BUG] Figma MCP setup flow incomplete (Discovered: 2026-03-23)
- **Observed Behavior:** Current PM_BASE only describes the CLI command (claude mcp add) without the restart or /mcp authentication steps.
- **Expected Behavior:** Should be three steps: (1) run claude mcp add to configure, (2) restart Claude, (3) use /mcp to authenticate.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (LOW). See pm_first_session_guide.impl.md for context.
