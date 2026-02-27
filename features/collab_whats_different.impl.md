# Implementation Notes: What's Different? (Collaboration Digest)

DEVIATION — Summarize Impact button placement: Originally spec'd for the dashboard panel; moved inside the modal per Human Executive direction. Spec updated (Sections 2.14.1, 2.14.2, 2.14.3, scenarios, visual spec) to match implementation. Acknowledged.

**[CLARIFICATION]** Modal scroll structure: The impact section and digest body are wrapped in a single `.modal-body` scrollable container (`wd-modal-scroll`) to prevent overflow when the impact summary adds significant content. The impact section, generate button, and digest body are all children of this scroll container. (Severity: INFO)

**[CLARIFICATION]** Decision extraction diff-based parsing: `_extract_decisions_from_diff()` reads added lines (`+` prefix) from `git diff range -- file -U0` to detect new decision entries. This captures only entries added in the commit range, not pre-existing ones. The `-U0` flag suppresses context lines for clean parsing. (Severity: INFO)

**[CLARIFICATION]** Staleness invalidation dual-path: Analysis file deletion happens in both `generate_whats_different.sh` (for CLI/post-merge trigger) and `_handle_whats_different_generate()` in serve.py (for dashboard endpoint). Both paths enforce the same invariant per Section 2.14.7. (Severity: INFO)
