# Implementation Notes: Git Operation Cache

*   **Section 2.1 (Persistent Status Commit Cache):** Cache stored at `.purlin/cache/status_commit_cache.json` with `git_head` metadata for invalidation. Uses atomic writes (tempfile + os.replace) for crash safety. Cache entries include `spec_content_hash` (SHA-256) for Section 2.2 hash-based comparison. The `_best_hash` internal field tracks commit hash for deterministic tiebreaking (cleaned before return, same pattern as `_best_ts`).
*   **Section 2.2 (Hash-Based Content Comparison):** `_compute_spec_hash()` strips the Discoveries section before hashing using the existing `strip_discoveries_section()` function. When the persistent cache contains a `spec_content_hash` for a feature, `spec_content_unchanged()` compares against the current file hash — avoiding `git show` entirely on cache hit. Falls back to the original `git show` path when cache has no hash entry or on any error.
*   **Section 2.3 (Batched Diff Extraction):** Added `_DIFF_BATCH_SIZE = 50` constant and `_batched_diff()` helper to `extract_whats_different.py`. Splits batched diff output by `diff --git` header lines. Binary files are detected and skipped gracefully. The existing `_extract_decisions_from_diff()` was refactored to collect file paths by category, then issue one batched diff call per category instead of N per-file calls.
### Audit Finding -- 2026-03-23

**[DISCOVERY]** cached_git_status() is dead code
**Source:** /pl-spec-code-audit --deep (H6)
**Severity:** HIGH
**Details:** `cached_git_status()` is defined in `serve.py:239` but has zero callers in production code. `serve.py` uses `run_command("git status --porcelain")` directly at lines 1140 and 1385. `critic.py` calls `subprocess.run(['git', 'status', '--porcelain'])` directly at line 2135. The shared cache mechanism specified in §2.4 is not connected to any consumer.
**Suggested fix:** Wire `cached_git_status()` into the hot paths in both `serve.py` and `critic.py`, or remove it and update the spec to reflect direct calls.

*   **Section 2.4 (Shared Git Status Cache):** Cache stored at `.purlin/cache/git_status_cache.json` with 10-second TTL. `cached_git_status()` replaces direct `git status --porcelain` calls in the hot path. Cache includes a timestamp for TTL validation. Uses the same atomic write pattern as the status commit cache.
