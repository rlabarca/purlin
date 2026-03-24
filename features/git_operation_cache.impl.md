# Implementation Notes: Git Operation Cache

*   **Section 2.1 (Persistent Status Commit Cache):** Cache stored at `.purlin/cache/status_commit_cache.json` with `git_head` metadata for invalidation. Uses atomic writes (tempfile + os.replace) for crash safety. Cache entries include `spec_content_hash` (SHA-256) for Section 2.2 hash-based comparison. The `_best_hash` internal field tracks commit hash for deterministic tiebreaking (cleaned before return, same pattern as `_best_ts`).
*   **Section 2.2 (Hash-Based Content Comparison):** `_compute_spec_hash()` strips the Discoveries section before hashing using the existing `strip_discoveries_section()` function. When the persistent cache contains a `spec_content_hash` for a feature, `spec_content_unchanged()` compares against the current file hash — avoiding `git show` entirely on cache hit. Falls back to the original `git show` path when cache has no hash entry or on any error.
*   **Section 2.3 (Batched Diff Extraction):** Added `_DIFF_BATCH_SIZE = 50` constant and `_batched_diff()` helper to `extract_whats_different.py`. Splits batched diff output by `diff --git` header lines. Binary files are detected and skipped gracefully. The existing `_extract_decisions_from_diff()` was refactored to collect file paths by category, then issue one batched diff call per category instead of N per-file calls.
*   **Section 2.4 (Shared Git Status Cache):** Cache stored at `.purlin/cache/git_status_cache.json` with 10-second TTL. `cached_git_status()` replaces direct `git status --porcelain` calls in the hot path. Cache includes a timestamp for TTL validation. Uses the same atomic write pattern as the status commit cache.

**[DISCOVERY] [ACKNOWLEDGED]** Hash hit test doesn't verify file I/O path
**Source:** /pl-spec-code-audit --deep (M29)
**Severity:** MEDIUM
**Details:** The test calls `spec_content_unchanged()` and patches `run_command`, asserting it is not called. However, `spec_content_unchanged()` reads the local file directly (not via `run_command`). The mock proves no git subprocess was called but doesn't verify the actual file read path.
**Suggested fix:** Add an assertion that verifies the file was read from disk (e.g., mock `open` or check that the hash was computed from the local file content).

**[DISCOVERY] [ACKNOWLEDGED]** Single batch test missing subprocess call count assertion
**Source:** /pl-spec-code-audit --deep (M30)
**Severity:** MEDIUM
**Details:** The spec requires verifying "exactly 2 git diff subprocess calls are made (one per category)" for a single batch of fewer than 50 files. The test uses a counting wrapper but never asserts the call count.
**Suggested fix:** Add `assertEqual(call_count[0], 2)` to the single-batch test.
