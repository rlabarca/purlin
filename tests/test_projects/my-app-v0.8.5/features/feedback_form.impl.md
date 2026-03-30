# Implementation Notes: feedback_form

## Approach

**[CLARIFICATION]** `> Web Test: TBD` / `> Web Start: TBD` — resolved to `http://localhost:3000` and `npm run dev` after building the server. Updated spec metadata per bright-line rule. (Severity: INFO)

**[AUTONOMOUS]** `tests.json` written via inline `writeResults()` called in the `after()` hook of the `node:test` suite (not via pytest/jest). Direct execution: `node --test tests/feedback_form/test_feedback_form.js`. (Severity: WARN)

**[CLARIFICATION]** Scenarios S2/S3/S4 are client-side behaviors. Validated by testing the exported pure functions (`validateIssueType`, `validateFileSize`, `createDefaultState`) using a dual-mode CommonJS/browser pattern in `public/app.js`. Server also enforces the limits as a safety net. (Severity: INFO)

**[CLARIFICATION]** S4 "no data is saved" is verified by asserting feedback.json does not grow when no POST is made. The DOM reset behavior (field clearing) is covered by the manual visual scenario. (Severity: INFO)

**[AUTONOMOUS]** Multer upgraded from v1.4.5-lts.2 to v2.1.1 due to published vulnerabilities in v1. API is compatible. (Severity: WARN)

**[CLARIFICATION]** Submit/Cancel button color updated per spec commit `68e0213`: Submit bg+border and Cancel border changed from `--color-danger`/`--color-neutral-800` to `--color-supplementary-purple-500` (#681f95). New CSS token added to `:root`. Prior STALE discovery in sidecar (about danger red) is now superseded by this spec change. (Severity: INFO)

## File Layout

- `server.js` — Express app + POST /feedback with multer v2 disk storage
- `public/index.html` — Full modal HTML
- `public/styles.css` — Design tokens + modal CSS (brief.json / Token Map)
- `public/app.js` — Client-side validation (dual-mode: browser + node)
- `tests/feedback_form/test_feedback_form.js` — node:test suite, 14 tests

## Test Quality Audit

| Test | Deletion Check | AP Issues | Value Assertion |
|------|---------------|-----------|----------------|
| S1-status-200 | ✅ Would fail (no route) | None | `=== 200` |
| S1-feedback-json | ✅ Would fail (no write) | None | entry found, issueType |
| S1-timestamp | ✅ Would fail (no entry) | None | ISO 8601 parse |
| S1-attachment-path | ✅ Would fail (no entry) | None | starts with 'uploads' |
| S2-validate-empty | ✅ Would fail (fn deleted) | None | `=== false` |
| S2-validate-null | ✅ Would fail (fn deleted) | None | `=== false` |
| S2-validate-valid | ✅ Would fail (fn deleted) | None | `=== true` |
| S2-server-rejects | ✅ Would fail (no 400) | None | `=== 400`, count stable |
| S3-client-oversize | ✅ Would fail (fn deleted) | None | `=== false` |
| S3-client-at-limit | ✅ Would fail (fn deleted) | None | `=== true` |
| S3-client-under-limit | ✅ Would fail (fn deleted) | None | `=== true` |
| S3-server-rejects-oversize | ✅ Would fail (no limit) | None | `=== 400` |
| S4-default-state | ✅ Would fail (fn deleted) | None | empty string + null |
| S4-no-data-saved | ✅ Would fail (if POST snuck in) | None | count stable |
