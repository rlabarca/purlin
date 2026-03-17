# Implementation Notes: Release Checklist — Dashboard Section

*   The drag-to-reorder implementation MUST be consistent with any drag/drop library or pattern already used in the CDD Dashboard. If none exists, the HTML5 Drag and Drop API is the default. Do not introduce a new dependency without confirming with the Architect.
*   The `POST /release-checklist/config` endpoint writes directly to `.purlin/release/config.json`. The server MUST handle concurrent writes gracefully (e.g., the user rapidly toggling checkboxes); debouncing on the frontend is preferred over server-side locking for this use case.
*   The `purlin-section-states` localStorage key already exists (per `cdd_status_monitor.md`). The RELEASE CHECKLIST section's key within that object SHOULD be `release-checklist`.
*   The Step Detail Modal pattern references the Feature Detail Modal. If the Feature Detail Modal does not yet exist as an independent component, the Builder should implement the modal as a reusable component and refactor the Feature Detail Modal to use it.
*   **Refresh Stability:** Uses `refreshReleaseChecklist()` called from `refreshStatus()` after innerHTML replacement. Fetches `/release-checklist`, compares against `rcStepsCache`, and only updates changed rows (reorder via DOM reappend, enabled state via checkbox+dimming diff). A `rcPendingSave` flag prevents refresh overwrites during in-flight `POST /release-checklist/config` requests — same pattern as the agents section's `pendingWrites` mechanism. Badge updates use shared `rcUpdateBadge()` function.
*   **Drag Snap-Back Fix (2026-02-22):** BUG resolved — root cause was `refreshStatus()` replacing `status-view` innerHTML (including release checklist rows) from server-rendered HTML. When `rcPendingSave` was true, `refreshReleaseChecklist()` returned early, leaving the old server-rendered order in the DOM. Two-part fix: (1) `refreshStatus()` now saves and restores `rc-tbody` innerHTML when `rcPendingSave` is true, so the optimistic DOM survives the full-page refresh. (2) `rcPersistConfig()` optimistically updates `rcStepsCache` from the current DOM before sending the POST, so subsequent refreshes see the cache matching the server's new order and skip redundant DOM updates.
*   **QA Verification (2026-02-22):** All 8 scenarios and 17 visual items PASS. Bugs resolved: LOCAL/GLOBAL badge width parity (min-width 52px), disabled row dimming, drag-to-reorder implementation, drag snap-back race condition with `rcPendingSave` guard.

### Visual Spec Discrepancy -- 2026-03-17

[DISCOVERY] Visual spec says "8pt larger" for step detail modal title but design_modal_standards anchor says 4pt — **ACKNOWLEDGED**

**Source:** Phase 5 implementation review
**Severity:** LOW
**Details:** The visual spec line `"Step detail modal title renders at a font size 8pt larger than the modal body text, per design_modal_standards"` references design_modal_standards which states "Modal titles MUST render 4 points larger than the modal's default body font size." Current implementation correctly follows design_modal_standards (18px title - 14px body = 4pt). The "8pt" in the visual spec appears to be a transcription error. The anchor is authoritative; no code change needed.
**Suggested fix:** Architect should update the visual spec line to say "4pt" to match design_modal_standards.
