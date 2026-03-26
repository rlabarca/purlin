# User Testing Discoveries: PM First Session Guide

### [BUG] Figma MCP setup flow incomplete (Discovered: 2026-03-23)
- **Observed Behavior:** Current PM_BASE only describes the CLI command (claude mcp add) without the restart or /mcp authentication steps.
- **Expected Behavior:** Should be three steps: (1) run claude mcp add to configure, (2) restart Claude, (3) use /mcp to authenticate.
- **Action Required:** Engineer
- **Status:** RESOLVED
- **Resolution:** Section 7.1 of PM_BASE.md updated to full 6-step flow matching Section 4 (Figma MCP Setup): (1) add MCP server via `claude mcp add`, (2) restart Claude, (3) type `/mcp`, (4) select figma, (5) complete browser auth, (6) come back to terminal.
- **Source:** Spec-code audit (LOW). See pm_first_session_guide.impl.md for context.
