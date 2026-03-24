# User Testing Discoveries: CDD Status Monitor

### [BUG] H3: CDD_PORT env var priority chain (Discovered: 2026-03-23)
- **Observed Behavior:** serve.py never reads the CDD_PORT environment variable; start.sh passes --port directly. The spec-defined priority chain (CDD_PORT env var > config > default) is not implemented.
- **Expected Behavior:** Port selection should follow the priority chain: CDD_PORT environment variable takes highest priority, then config file value, then default port.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (deep mode). See cdd_status_monitor.impl.md for full context.

### [BUG] M6: delivery_plan_gating fully_delivered_features (Discovered: 2026-03-23)
- **Observed Behavior:** The `fully_delivered_features` field is always an empty array; the code never computes which features are eligible.
- **Expected Behavior:** `fully_delivered_features` should be computed by identifying features that have completed all delivery phases.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (deep mode). See cdd_status_monitor.impl.md for full context.

### [BUG] Undocumented API fields in /status.json (Discovered: 2026-03-23)
- **Observed Behavior:** Fields category, complete_ts, verification_effort, branch_collab, branch_collab_branches appear in API but not in spec Section 2.4 schema.
- **Expected Behavior:** All API fields should be documented in spec Section 2.4 schema.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (LOW). See cdd_status_monitor.impl.md for context.

### [BUG] Non-behavioral spec edits trigger unnecessary lifecycle resets (Discovered: 2026-03-24)
- **Scenario:** Lifecycle reset detection
- **Observed Behavior:** A formatting-only spec edit (`spec(release_record_version_notes): fix scenario format for Critic parsing`) reset the feature lifecycle to TODO, forcing full re-verification despite no behavioral changes. The CDD only exempts `[QA-Tags]` commits from lifecycle reset.
- **Expected Behavior:** Extend `_only_qa_tag_commits_since()` in `serve.py` to also exempt `[Spec-FMT]` commits. The function should treat `[Spec-FMT]` identically to `[QA-Tags]` — if all commits since the last status commit contain either tag (or a combination), the lifecycle is preserved. Rename the function to reflect the broader scope (e.g., `_only_exempt_commits_since`). Add unit tests mirroring the existing `[QA-Tags]` test cases.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** Renamed `_only_qa_tag_commits_since()` to `_only_exempt_commits_since()`, added `[Spec-FMT]` check alongside `[QA-Tags]`, updated both callers and comments, added 2 new tests (Spec-FMT only, mixed QA-Tags+Spec-FMT).

### [BUG] Git status clean filter uses substring match instead of prefix match (Discovered: 2026-03-24)
- **Observed Behavior:** `get_workspace_json()` (serve.py ~line 1163) and `get_git_status()` (serve.py ~line 1412) filter `.purlin/` paths using a substring match (`'.purlin/' in line`). This silently hides files like `tests/.purlin/` from the clean/dirty calculation, reporting the workspace as "clean" when untracked files exist outside the project root `.purlin/` directory.
- **Expected Behavior:** All git status filter points should use prefix-based filtering consistent with `_get_dirty_files()` (serve.py ~line 1926), which correctly uses `path.startswith('.purlin/')`. The substring match in `get_workspace_json()` and `get_git_status()` should be replaced with equivalent prefix logic applied to the parsed file path (column 4+ of porcelain output), not the raw line.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** User-reported. Branch join blocked on `tests/.purlin/` while CDD status reported clean.
