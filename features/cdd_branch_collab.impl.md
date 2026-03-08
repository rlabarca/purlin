# Implementation Notes: CDD Branch Collaboration

**[CLARIFICATION]** The test for "BRANCH Section Always Rendered in Dashboard HTML" uses `serve.generate_html()` -- the function name in serve.py is `generate_html`, not `generate_dashboard_html`. The original test had a name mismatch that was corrected. (Severity: INFO)

**[CLARIFICATION]** The `import re` statement in `_handle_branch_collab_create` is placed inside the method body rather than at module top level. This follows the existing pattern in serve.py where `re` is imported locally in handlers that use it. (Severity: INFO)

**[CLARIFICATION]** The collapsed heading for BRANCH COLLABORATION uses a `data-collapsed-text` / `data-expanded` attribute pattern with `applyBCHeadingState()` JS function, mirroring the existing ISOLATED TEAMS heading swap pattern (`applyIsolationHeadingState()`). (Severity: INFO)

**[CLARIFICATION]** The `start_auto_fetch()` call is placed in the `if __name__ == "__main__"` block alongside `start_file_watcher()`. The daemon thread only runs when the server is started directly, not during test imports. (Severity: INFO)

**[CLARIFICATION]** The `branch_collab_branches` API uses local perspective for `sync_state` (AHEAD = local ahead, BEHIND = local behind), matching `compute_remote_sync_state()`. The JS modal maps: API `BEHIND` -> data loss warning (remote has extra commits), API `AHEAD`/`SAME` -> standard confirmation. (Severity: INFO)

**[CLARIFICATION]** Branch sync state data is embedded as `window._bcBranchesData` in a `<script>` tag within the `_branch_collab_section_html` output. This allows the UI to read per-branch sync state without an additional server request. The data refreshes with each 5-second HTML poll cycle. (Severity: INFO)

**[CLARIFICATION]** Panel alignment fix: Row 1 (branch dropdown) and Row 2 (sync badge) share the same parent flex container, ensuring consistent left-edge alignment per spec Section 2.3. The `<select>` element gets `margin:0` to normalize browser defaults. Vertical gap between rows increased from 6px to 14px to create clear visual separation between the Leave and Check Remote buttons. (Severity: INFO)

**[DISCOVERY]** ~~The spec (Section 2.4) hardcodes `main` in two places: create step 4 says `git branch <name> main` and disconnect step 2 says `git checkout main`. This breaks when the user starts a branch collab from a non-main branch. Fixed in code to use `HEAD` for branch creation and store/restore the pre-session branch for leave. The spec needs Architect update to replace hardcoded `main` references with dynamic base branch semantics.~~ **ACKNOWLEDGED** -- Spec updated: create uses HEAD, leave reads stored base branch from `.purlin/runtime/branch_collab_base_branch` (defaults to `main` if absent).

**[CLARIFICATION]** The spec references `--purlin-fg` for the EMPTY badge color, but this CSS custom property is not defined in the design token system (`design_visual_standards.md`). Used `--purlin-primary` instead, which is the defined token for primary/heading text color and achieves the same "normal text" visual intent. (Severity: INFO)

**[DISCOVERY]** The spec (Section 2.5) defines EMPTY detection as requiring BOTH directions to be zero: `git log main..<branch>` AND `git log <branch>..main` must both return zero lines. This only works when the branch tip is identical to main — it breaks when main moves ahead after the branch was created (branch has no unique commits but main has progressed). Fixed to check only one direction: if `git log main..<branch>` returns zero lines, the branch has no unique work = EMPTY. Also removed the non-spec `NO_LOCAL` state for remote-only branches; when a remote-only branch is not EMPTY, sync is now computed against main using `origin/<branch>`. The spec's EMPTY detection criteria needs Architect update to reflect the one-directional check. (Severity: HIGH)

## Pruned Discoveries

BUG -- IN FLIGHT empty state rendered without section label or column headers in active session view; fixed by always rendering the IN FLIGHT section headers.
SPEC_DISPUTE -- IN FLIGHT table removed from Branch Collaboration section entirely; accepted by Architect since isolation branches are never pushed to remote per policy invariant 2.5; CONTRIBUTORS + sync badge provide all meaningful signals.
BUG -- Sync badge never appeared when local main branch absent (e.g., cloned from collab branch); fixed by detecting missing local main in `compute_remote_sync_state()` and returning `sync_state: "NO_MAIN"` with guidance message.
BUG -- Active branch panel rendered controls across three rows instead of two; fixed by reorganizing HTML so Row 1 = dropdown + branch ref + Leave, Row 2 = sync badge + annotation + last check + Check Remote.
INTENT_DRIFT -- Sync state annotation was ambiguous about perspective (e.g., "1 ahead"); fixed to use remote-perspective framing ("Remote is N behind/ahead of local") per spec Section 2.3.
BUG -- Leave button appeared visually near Check Remote due to insufficient vertical margin between Row 1 and Row 2; fixed by increasing gap from 6px to 14px.
INTENT_DRIFT -- Branch dropdown and sync badge lacked left-edge alignment; spec updated to mandate horizontal alignment of Row 1 and Row 2 left edges; verified passing after flex container and margin fix.
