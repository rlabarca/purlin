# Feature: Git Operation Cache

> Label: "CDD: Git Operation Cache"
> Category: "CDD Dashboard"
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/critic_tool.md

[TODO]

## 1. Overview

The CDD status engine and Critic tool spawn numerous git subprocesses on every invocation: full `git log --grep` scans, per-file `git show` and `git diff` calls, and redundant `git status` invocations. This feature specifies four optimizations -- persistent status commit cache, hash-based content comparison, batched diff extraction, and shared git status results -- that reduce subprocess overhead while preserving correctness. All caches are advisory: stale or missing cache data produces correct results (just slower), never incorrect results.

---

## 2. Requirements

### 2.1 Persistent Status Commit Cache

- `build_status_commit_cache()` MUST write its results to `.purlin/cache/status_commit_cache.json` with metadata fields `generated_at` (ISO timestamp) and `git_head` (current HEAD commit hash).
- On subsequent invocations, if the cache file exists AND `git_head` matches the current HEAD AND no feature file has an mtime newer than `generated_at`, the cached result MUST be returned without spawning any `git log` subprocess.
- Cache invalidation triggers: (a) HEAD commit hash differs from `git_head` in cache, or (b) any feature file mtime is newer than `generated_at`.
- A missing or corrupt cache file MUST fall back to a full `git log` scan and write a fresh cache. No crash or error propagation.
- An empty repository (no status commits) MUST produce a valid cache file with empty entries.

### 2.2 Hash-Based Content Comparison

- `spec_content_unchanged()` MUST support hash-based comparison when the status commit cache contains a `spec_content_hash` field for the feature.
- The hash is SHA-256 of the spec content stripped of the User Testing Discoveries section (everything below `## User Testing Discoveries`).
- When `spec_content_hash` is present in cache, comparison MUST compute the local file hash and compare without spawning a `git show` subprocess.
- When `spec_content_hash` is absent (old cache format) or the cache entry is missing, the function MUST fall back to the existing `git show` full-file comparison.
- Hash computation MUST handle Unicode content correctly (UTF-8 encoding before hashing).

### 2.3 Batched Diff Extraction

- `extract_whats_different.py` MUST batch file paths into a single `git diff` call per file category (companion files, feature files) instead of issuing one `git diff` per file.
- Each batch MUST be limited to 50 file paths to avoid `ARG_MAX` limits on the command line.
- The batched output MUST be split by file and produce results identical to the per-file extraction (result equivalence).
- Files with spaces in names MUST be correctly quoted in the `git diff` command.
- Binary files in the diff range MUST be skipped gracefully without affecting text file extraction.

### 2.4 Shared Git Status Result

- `git status --porcelain` output MUST be cached at `.purlin/cache/git_status_snapshot.txt` with a 10-second TTL based on file mtime.
- Both `serve.py` and `critic.py` MUST read from this shared cache when available and fresh.
- A missing cache file triggers a fresh `git status --porcelain` call and writes the cache.
- A stale cache (mtime older than 10 seconds) triggers a fresh call and overwrites the cache.
- A truncated or partially-written cache file MUST be detected and treated as missing (fresh call).
- Path filtering (excluding `.DS_Store`, `.purlin/cache/`, etc.) MUST produce identical results regardless of whether the cached or fresh result is used.

### 2.5 Cache Safety Invariant

- All four caches are **advisory**: the system MUST produce correct results when any or all caches are missing, stale, or corrupt. Caches improve performance only; they never change behavioral outcomes.
- Cache files MUST be written atomically (write to temp file, then rename) to prevent partial reads.

### 2.6 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/git_operation_cache/fresh-repo-no-cache` | Repository with 5 features, status commits, no cache files |
| `main/git_operation_cache/populated-cache-current-head` | Same repo with valid cache file matching current HEAD |
| `main/git_operation_cache/populated-cache-stale-head` | Same repo with cache file whose git_head differs from current HEAD |
| `main/git_operation_cache/many-features-for-batching` | Repository with 60+ companion files changed on a branch vs main |
| `main/git_operation_cache/mixed-changes-branch` | Branch with added, modified, and deleted files vs main |

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Cache write on first build

    Given a repository with 5 features (2 Complete, 1 Testing, 2 TODO)
    And no status commit cache file exists
    When build_status_commit_cache() is called
    Then .purlin/cache/status_commit_cache.json is written
    And the file contains generated_at, git_head, and entries for all 5 features

#### Scenario: Cache hit when HEAD unchanged

    Given a valid status commit cache file with current HEAD hash
    When build_status_commit_cache() is called
    Then the cached result is returned
    And no git log subprocess is spawned

#### Scenario: Cache invalidation on new commit

    Given a valid status commit cache file
    And a new commit is made (HEAD changes)
    When build_status_commit_cache() is called
    Then the cache is discarded
    And a fresh git log scan runs
    And a new cache file is written with updated git_head

#### Scenario: Cache invalidation on feature file mtime change

    Given a valid status commit cache file written at time T
    And a feature file's mtime is set to after T
    And HEAD is unchanged
    When build_status_commit_cache() is called
    Then the cache is discarded and rebuilt

#### Scenario: Missing cache file triggers full scan

    Given no status commit cache file exists
    When build_status_commit_cache() is called
    Then a full git log scan runs
    And a valid cache file is written

#### Scenario: Corrupt cache file triggers full scan

    Given a cache file containing invalid JSON
    When build_status_commit_cache() is called
    Then the corrupt file is replaced with a valid cache
    And no exception propagates

#### Scenario: Empty repository produces valid cache

    Given a repository with feature files but zero status commits
    When build_status_commit_cache() is called
    Then a cache file is written with empty entries
    And all features show TODO status

#### Scenario: Cache persists across simulated restart

    Given a valid status commit cache file
    And in-memory state is cleared (simulating server restart)
    And HEAD is unchanged
    When build_status_commit_cache() is called
    Then the persisted cache is loaded without spawning a git subprocess

#### Scenario: Hash hit when spec content unchanged

    Given a feature file committed to git
    And the on-disk file is identical to the committed version
    And the cache contains spec_content_hash for this feature
    When spec_content_unchanged() is called
    Then it returns True
    And no git show subprocess is spawned

#### Scenario: Hash miss when spec content changed

    Given a feature file committed to git
    And the spec content (above Discoveries section) is edited on disk
    And the cache contains spec_content_hash for this feature
    When spec_content_unchanged() is called
    Then it returns False

#### Scenario: Hash hit when only discoveries section changed

    Given a feature file committed to git
    And only text below the User Testing Discoveries heading is edited on disk
    And the cache contains spec_content_hash for this feature
    When spec_content_unchanged() is called
    Then it returns True

#### Scenario: Fallback when no hash in cache

    Given a cache entry for the feature without spec_content_hash (old format)
    When spec_content_unchanged() is called
    Then the function falls back to git show full-file comparison
    And returns the correct result

#### Scenario: Fallback when cache entry missing entirely

    Given no cache entry for the feature
    When spec_content_unchanged() is called
    Then the function falls back to git show full-file comparison
    And returns the correct result

#### Scenario: Unicode content hashed correctly

    Given a feature file with non-ASCII characters (accented names, special characters)
    And the cache contains spec_content_hash for this feature
    When spec_content_unchanged() is called with the file unchanged on disk
    Then it returns True (hash matches)

#### Scenario: Single batch for fewer than 50 files

    Given a branch with 15 changed companion files and 8 changed feature files vs main
    When batched diff extraction runs
    Then exactly 2 git diff subprocess calls are made (one per category)
    And results match per-file extraction

#### Scenario: Multi-batch for more than 50 files

    Given a branch with 60 changed companion files vs main
    When batched diff extraction runs
    Then 2 git diff calls are made for companion files (batch of 50 + batch of 10)
    And all 60 files are correctly extracted

#### Scenario: Zero changed files skips extraction

    Given a branch identical to main
    When batched diff extraction runs
    Then zero git diff extraction calls are made
    And the discovery results are empty

#### Scenario: Mixed add/modify/delete parsed correctly

    Given a branch that adds 3 files, modifies 5 files, and deletes 2 files vs main
    When batched diff extraction runs
    Then all change types are parsed correctly from batched output
    And DEVIATION and DISCOVERY tags are extracted from added and modified companion files

#### Scenario: Result equivalence between batched and per-file extraction

    Given the same branch state
    When both batched extraction and legacy per-file extraction run
    Then their outputs are identical (same decisions, same ordering)

#### Scenario: Binary file in diff range handled gracefully

    Given a non-text file changed in the diff range alongside feature files
    When batched diff extraction runs
    Then the binary file is skipped
    And feature and companion file diffs are extracted correctly

#### Scenario: Git status cache written and reused within TTL

    Given a working tree with untracked files
    And git status is called and cached
    When git status is requested again within 10 seconds
    Then the cached result is returned
    And no git status subprocess is spawned

#### Scenario: Git status cache expired after TTL

    Given a git status cache file with mtime older than 10 seconds
    When git status is requested
    Then a fresh git status subprocess runs
    And the cache file is overwritten

#### Scenario: Git status cache missing triggers fresh call

    Given no git status cache file exists
    When git status is requested
    Then a fresh git status subprocess runs
    And a cache file is written

#### Scenario: Truncated git status cache triggers fresh call

    Given a git status cache file with truncated content
    When git status is requested
    Then the truncated file is detected
    And a fresh git status subprocess runs

#### Scenario: Git status path filtering is consistent

    Given untracked files including .DS_Store, .purlin/cache entries, and features/new.md
    When both serve.py and critic.py consumers read git status
    Then both see identical filtered results
    And .DS_Store and .purlin/cache entries are excluded

### Manual Scenarios (Human Verification Required)

None.
