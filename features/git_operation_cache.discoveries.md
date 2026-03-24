# User Testing Discoveries: Git Operation Cache

### [BUG] H6: cached_git_status() dead code (Discovered: 2026-03-23)
- **Observed Behavior:** `cached_git_status()` is defined in serve.py but has zero callers; critic.py calls git status directly, bypassing the cache entirely.
- **Expected Behavior:** Code that calls git status should use the cached version to benefit from the operation cache.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** Wired `cached_git_status()` into serve.py (startup briefing + `get_git_status()`) and added `_cached_git_status_output()` to critic.py that shares the same cache file.
- **Source:** Spec-code audit (deep mode). See git_operation_cache.impl.md for full context.

### [DISCOVERY] M29: Hash hit test doesn't verify file I/O path (Discovered: 2026-03-23)
- **Observed Behavior:** The hash hit test mocks `run_command` but does not verify the actual file read mechanism used to retrieve cached results.
- **Expected Behavior:** The test should verify the complete I/O path including how cached results are read from the file system on a cache hit.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** Added `builtins.open` wrapping mock and assertion that the spec file is read from disk during hash comparison.
- **Source:** Spec-code audit (deep mode). See git_operation_cache.impl.md for full context.

### [DISCOVERY] M30: Single batch test missing call count assertion (Discovered: 2026-03-23)
- **Observed Behavior:** The single batch test does not assert the number of subprocess calls made.
- **Expected Behavior:** Spec requires "exactly 2 subprocess calls" for a single batch operation; the test should assert this count.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** Added counting wrapper and `assertEqual(impl_calls, 1)` / `assertEqual(feat_calls, 1)` assertions.
- **Source:** Spec-code audit (deep mode). See git_operation_cache.impl.md for full context.
