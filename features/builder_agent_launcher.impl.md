# Implementation Notes: Builder Agent Launcher

*   **Permission Bypass:** The Builder launcher uses `--dangerouslySkipPermissions` (or equivalent `bypass_permissions` config) to enable autonomous code execution without per-tool approval prompts. This is intentional -- the Builder needs unrestricted tool access for implementation work. The spec's original "no --allowedTools" phrasing was imprecise; the intent is that the Builder has full tool access, not that it uses the default restricted set.
*   **QA Mode:** When `qa_mode: true` is set in the resolved config, the launcher passes the QA mode flag. The Builder then operates in a verification-focused mode per `builder_qa_mode.md`.
