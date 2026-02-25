# Implementation Notes: CDD Remote Collaboration

**[CLARIFICATION]** The test for "REMOTE Section Always Rendered in Dashboard HTML" uses `serve.generate_html()` — the function name in serve.py is `generate_html`, not `generate_dashboard_html`. The original test had a name mismatch that was corrected. (Severity: INFO)

**[CLARIFICATION]** The `import re` statement in `_handle_remote_collab_create` is placed inside the method body rather than at module top level. This follows the existing pattern in serve.py where `re` is imported locally in handlers that use it. (Severity: INFO)

**[CLARIFICATION]** The collapsed heading for REMOTE COLLABORATION uses a `data-collapsed-text` / `data-expanded` attribute pattern with `applyRCHeadingState()` JS function, mirroring the existing ISOLATED TEAMS heading swap pattern (`applyIsolationHeadingState()`). (Severity: INFO)

**[CLARIFICATION]** The `start_auto_fetch()` call is placed in the `if __name__ == "__main__"` block alongside `start_file_watcher()`. The daemon thread only runs when the server is started directly, not during test imports. (Severity: INFO)
