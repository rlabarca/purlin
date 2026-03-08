# CDD Internals

> **Reference file.** Loaded on demand when understanding how automated test results map to CDD dashboard columns.
> Stub location: HOW_WE_WORK_BASE Section 8.

## Automated Test Status in the CDD Dashboard

Automated test results are NOT reported as a separate column. They are surfaced through the existing Builder and QA role columns:

*   **Builder column:** `DONE` means the spec is structurally complete and no open BUGs exist (automated tests passed). `FAIL` means `tests/<feature>/tests.json` exists with `status: "FAIL"` (automated tests failed).
*   **QA column:** `CLEAN` requires `tests/<feature>/tests.json` to exist with `status: "PASS"` (automated tests exist and passed). `N/A` means no `tests.json` exists (no automated test coverage).

In short: Builder `DONE` implies automated tests passed. QA `CLEAN` vs `N/A` signals whether automated test coverage exists at all. There is no separate "test status" indicator -- automated test health is embedded in the role status model.
