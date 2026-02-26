# Implementation Notes: CDD Remote Collaboration

**[CLARIFICATION]** The test for "REMOTE Section Always Rendered in Dashboard HTML" uses `serve.generate_html()` — the function name in serve.py is `generate_html`, not `generate_dashboard_html`. The original test had a name mismatch that was corrected. (Severity: INFO)

**[CLARIFICATION]** The `import re` statement in `_handle_remote_collab_create` is placed inside the method body rather than at module top level. This follows the existing pattern in serve.py where `re` is imported locally in handlers that use it. (Severity: INFO)

**[CLARIFICATION]** The collapsed heading for REMOTE COLLABORATION uses a `data-collapsed-text` / `data-expanded` attribute pattern with `applyRCHeadingState()` JS function, mirroring the existing ISOLATED TEAMS heading swap pattern (`applyIsolationHeadingState()`). (Severity: INFO)

**[CLARIFICATION]** The `start_auto_fetch()` call is placed in the `if __name__ == "__main__"` block alongside `start_file_watcher()`. The daemon thread only runs when the server is started directly, not during test imports. (Severity: INFO)

**[CLARIFICATION]** The `remote_collab_sessions` API uses local perspective for `sync_state` (AHEAD = local ahead, BEHIND = local behind), matching `compute_remote_sync_state()`. The spec's Section 2.8 delete modal references displayed state labels (remote perspective), so the JS modal maps: API `BEHIND` → data loss warning (remote has extra commits), API `AHEAD`/`SAME` → standard confirmation. (Severity: INFO)

**[CLARIFICATION]** Session sync state data is embedded as `window._rcSessionsData` in a `<script>` tag within the `_remote_collab_section_html` output. This allows the delete confirmation modal to read per-session sync state without an additional server request, as specified in Section 2.8. The data refreshes with each 5-second HTML poll cycle. (Severity: INFO)

**[CLARIFICATION]** The delete confirmation modal follows the Kill Isolation Modal pattern (inline `style="display:none"` overlay, positioned fixed with `z-index:200`), not the Feature Detail Modal pattern (CSS class-based `.modal-overlay`). Both are valid CDD modal patterns. (Severity: INFO)

**[CLARIFICATION]** Panel alignment fix: Row 1 (session dropdown) and Row 2 (sync badge) share the same parent flex container, ensuring consistent left-edge alignment per spec Section 2.3. The `<select>` element gets `margin:0` to normalize browser defaults. Vertical gap between rows increased from 6px to 14px to create clear visual separation between the Disconnect and Check Remote buttons. (Severity: INFO)

## Pruned Discoveries

BUG — IN FLIGHT empty state rendered without section label or column headers in active session view; fixed by always rendering the IN FLIGHT section headers.
SPEC_DISPUTE — IN FLIGHT table removed from Remote Collaboration section entirely; accepted by Architect since isolation branches are never pushed to remote per policy invariant 2.5; CONTRIBUTORS + sync badge provide all meaningful signals.
BUG — Sync badge never appeared when local main branch absent (e.g., cloned from collab branch); fixed by detecting missing local main in `compute_remote_sync_state()` and returning `sync_state: "NO_MAIN"` with guidance message.
BUG — Active session panel rendered controls across three rows instead of two; fixed by reorganizing HTML so Row 1 = dropdown + branch ref + Disconnect, Row 2 = sync badge + annotation + last check + Check Remote.
INTENT_DRIFT — Sync state annotation was ambiguous about perspective (e.g., "1 ahead"); fixed to use remote-perspective framing ("Remote is N behind/ahead of local main") per spec Section 2.3.
