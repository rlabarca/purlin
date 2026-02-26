# Implementation Notes: CDD Remote Collaboration

**[CLARIFICATION]** The test for "REMOTE Section Always Rendered in Dashboard HTML" uses `serve.generate_html()` — the function name in serve.py is `generate_html`, not `generate_dashboard_html`. The original test had a name mismatch that was corrected. (Severity: INFO)

**[CLARIFICATION]** The `import re` statement in `_handle_remote_collab_create` is placed inside the method body rather than at module top level. This follows the existing pattern in serve.py where `re` is imported locally in handlers that use it. (Severity: INFO)

**[CLARIFICATION]** The collapsed heading for REMOTE COLLABORATION uses a `data-collapsed-text` / `data-expanded` attribute pattern with `applyRCHeadingState()` JS function, mirroring the existing ISOLATED TEAMS heading swap pattern (`applyIsolationHeadingState()`). (Severity: INFO)

**[CLARIFICATION]** The `start_auto_fetch()` call is placed in the `if __name__ == "__main__"` block alongside `start_file_watcher()`. The daemon thread only runs when the server is started directly, not during test imports. (Severity: INFO)

**[CLARIFICATION]** The `remote_collab_sessions` API uses local perspective for `sync_state` (AHEAD = local ahead, BEHIND = local behind), matching `compute_remote_sync_state()`. The spec's Section 2.8 delete modal references displayed state labels (remote perspective), so the JS modal maps: API `BEHIND` → data loss warning (remote has extra commits), API `AHEAD`/`SAME` → standard confirmation. (Severity: INFO)

**[CLARIFICATION]** Session sync state data is embedded as `window._rcSessionsData` in a `<script>` tag within the `_remote_collab_section_html` output. This allows the delete confirmation modal to read per-session sync state without an additional server request, as specified in Section 2.8. The data refreshes with each 5-second HTML poll cycle. (Severity: INFO)

**[CLARIFICATION]** The delete confirmation modal follows the Kill Isolation Modal pattern (inline `style="display:none"` overlay, positioned fixed with `z-index:200`), not the Feature Detail Modal pattern (CSS class-based `.modal-overlay`). Both are valid CDD modal patterns. (Severity: INFO)
