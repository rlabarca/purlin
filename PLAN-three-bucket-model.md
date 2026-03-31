# Three-Bucket File Model: Spec, Code, Other

## Context

Agents bypass Purlin skills and directly edit files. We want simple rules that push agents through skills while keeping a smooth, efficient experience.

## Terminology

- **Spec file** = a file in `features/` — feature specifications, companion `.impl.md` files, `.discoveries.md` sidecars, anchors, invariants. These are authoritative design artifacts. Modified through spec skills (purlin:spec, purlin:anchor, purlin:discovery, etc.) or purlin:build (for .impl.md companions).
- **Code file** = everything outside `features/` that isn't explicitly excepted. Source code, tests, scripts, hooks, agents, skill definitions, references, templates. Modified through purlin:build.
- **Other file** = paths classified as neither spec nor code — docs, README, LICENSE, config dotfiles. Freely editable without a skill. Shown informationally only. No feature tracking needed.
- **System files** = `.purlin/`, `.claude/` — always writable, not project content.
- **Active skill marker** = `.purlin/runtime/active_skill` — set by skills to authorize writes.

## What Can and Cannot Be Tracked

| Bucket | Tracked against features? | How? | When it fails |
|--------|--------------------------|------|---------------|
| **Spec** | Always | Path maps directly: `features/<cat>/<stem>.md` | Never — deterministic |
| **Code** | When skills used | Build writes `.impl.md` companions; `tests/<stem>/` and `skills/<name>/` map by convention; commit scope fallback | Rare — write guard blocks all code writes without a skill |
| **Other** | Never | Not connected to any feature | By design — these don't need tracking |

**Untracked code is rare if the hook logic is right.** The write guard blocks all code writes without a skill. Reclassification via `purlin:classify add` requires explicit user confirmation — agents cannot self-reclassify. `purlin:spec-code-audit` catches any remaining gaps.

---

## Write Guard (write-guard.sh)

### Decision Tree

```
1. .purlin/* or .claude/*                   → ALLOW (system files)
2. features/_invariants/i_*                 → existing INVARIANT bypass lock (unchanged)
3. features/*                               → check active_skill marker
                                               present → ALLOW
                                               absent  → BLOCK (use spec skill)
4. path matches write_exceptions            → ALLOW (OTHER — freely editable)
5. everything else                          → check active_skill marker
                                               present → ALLOW
                                               absent  → BLOCK (use purlin:build)
```

### Block Messages

**Spec file blocked (step 3):**
```
BLOCKED: features/auth/login.md is a spec file. To modify specs, invoke the
appropriate skill: purlin:spec (create/update specs), purlin:anchor (anchor
nodes), purlin:discovery (QA findings), purlin:propose (spec change proposals),
purlin:tombstone (retire features), purlin:infeasible (mark infeasible). The
skill will set the write marker and handle companion files automatically.
```

**Code file blocked (step 5):**
```
BLOCKED: src/auth.ts is a code file. To modify code, invoke purlin:build — it
will find the right feature, set the write marker, and track companion files
automatically.
```

**No escape hatch.** There is no `echo X > active_skill` bypass, and the error message does not suggest reclassification. The only way to write spec or code files is through a skill. Reclassification (`purlin:classify add`) requires explicit user confirmation via `AskUserQuestion`. This ensures every change is tracked through companion files and the sync system.

### Exception Matching

Write guard reads `write_exceptions` from `.purlin/config.json`:
- Trailing `/` = directory prefix: `"docs/"` matches `docs/anything`
- No trailing `/` = exact filename at project root: `"README.md"`
- Evaluated at step 4, before the code gate

---

## Active Skill Marker

File: `.purlin/runtime/active_skill`

**Set ONLY by skills** at start, cleared at end:
```bash
mkdir -p .purlin/runtime && echo "build" > .purlin/runtime/active_skill  # start
rm -f .purlin/runtime/active_skill                                        # end
```

Write guard checks: file exists and non-empty → ALLOW.

**Agents MUST NOT set this marker directly.** The marker is a skill-internal
mechanism. Invoking the skill is the only authorized path — it handles the
marker lifecycle, companion file tracking, and format compliance automatically.

Lifecycle:
- Set by each writing skill at start
- Cleared by skill at end
- Cleared by `session-init-identity.sh` on session start (stale cleanup)
- One skill at a time per session; worktrees have separate runtime dirs

---

## purlin:classify Skill (New)

Manages `write_exceptions` — paths classified as OTHER.

### Subcommands

| Subcommand | Description |
|---|---|
| `add <path>` | Add path/prefix to OTHER list (requires user confirmation) |
| `remove <path>` | Remove from OTHER list |
| `list` | Show all current exceptions |

### Storage

`.purlin/config.json`:
```json
{
  "write_exceptions": [
    "docs/",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    ".gitignore",
    ".gitattributes"
  ]
}
```

### MCP Tool Update

Update `config_engine.py:classify_file()` to return `"OTHER"` for paths matching `write_exceptions`, checked before the CODE catch-all. All callers (write-guard, scan_engine, whats-different) get OTHER support automatically.

### Seeding

`purlin:init` seeds default exceptions when creating a project.

---

## Format Specifications

All file format specs live in `references/formats/` for easy discovery:

| Format | File | Used By |
|--------|------|---------|
| Regular features | `references/formats/feature_format.md` | `purlin:spec`, `purlin:spec-from-code`, `purlin:spec-catch-up` |
| Anchor nodes | `references/formats/anchor_format.md` | `purlin:anchor`, `purlin:spec` (anchor creation) |
| Companion files | `references/formats/companion_format.md` | `purlin:build`, `purlin:spec-code-audit` |
| Invariant files | `references/formats/invariant_format.md` | `purlin:invariant` |
| Invariant: arch | `references/formats/invariant_type_arch.md` | `purlin:invariant` (arch_* type) |
| Invariant: design | `references/formats/invariant_type_design.md` | `purlin:invariant` (design_* type) |
| Invariant: ops | `references/formats/invariant_type_ops.md` | `purlin:invariant` (ops_* type) |
| Invariant: policy | `references/formats/invariant_type_policy.md` | `purlin:invariant` (policy_* type) |
| Invariant: prodbrief | `references/formats/invariant_type_prodbrief.md` | `purlin:invariant` (prodbrief_* type) |

Skills load these automatically. The agent definition (`agents/purlin.md`) points
agents to `references/formats/` so they know where to find format specs when
routing to a skill.

---

## .impl.md Companion Role

See `references/formats/companion_format.md` for the canonical format.

With the three-bucket model, companions serve two purposes:

1. **Deviation tracking** — [DEVIATION], [DISCOVERY], [INFEASIBLE] tags that gate completion and need PM acknowledgment. This is the escalation mechanism.

2. **Code-to-feature mapping** — The companion connects arbitrary code files to their feature. Build is encouraged (not required) to maintain a `## Code Files` section:

```markdown
## Code Files
- src/auth/login.ts
- src/auth/session.ts
- src/middleware/auth_guard.ts
```

When this section exists, reverse lookup finds the feature instantly. When it doesn't, lookup falls back to other signals. Over time, companions accumulate code file references through normal build usage, making lookup increasingly reliable.

**Build behavior:** When build touches code files, it appends them to `## Code Files` if the section exists. If the section doesn't exist and the companion already has content, build adds the section. For new companions, build always creates it.

---

## purlin:build: Smart Feature Resolution (Detailed)

This is the critical workflow. When an engineer says "make this change," build must efficiently find the right feature spec.

### Config: auto_create_features

`.purlin/config.json`:
```json
{
  "agents": {
    "purlin": {
      "auto_create_features": false
    }
  }
}
```

When `true`: If reverse lookup finds no match, build auto-creates a feature spec (generated from code context — inferred requirements, scenarios based on what the code does) and proceeds. No prompt.

When `false` (default): Build asks the engineer to pick an existing feature, create a new one, or continue one-off.

### Current Behavior (What Changes)

1. **With argument:** Resolve `features/**/<arg>.md` → implement (unchanged)
2. **Without argument:** Run purlin:status → pick highest-priority item (unchanged)
3. **Spec not found:** Currently offers to create. **NEW: runs reverse lookup first.**

### New: Reverse Lookup

When the engineer's request targets specific code or describes a change (not a feature by name), build resolves the feature through reverse lookup.

**Resolution cascade (fast → slow, first confident match wins):**

#### Signal 1: Path Convention (instant)
- `tests/<stem>/` → feature `<stem>`
- `skills/<name>/` → feature `purlin_<name>`

Confidence: DETERMINISTIC. No confirmation needed.

#### Signal 2: Companion Code Files Section (fast grep)
Search `## Code Files` sections in `.impl.md` companions:
```bash
grep -r "src/auth" features/**/*.impl.md
```
If found: the companion's feature stem is the match.

Confidence: HIGH — explicit mapping. No confirmation needed (unless multiple matches).

#### Signal 3: Commit Scope History (git log)
Search recent commits touching this file for conventional scopes:
```bash
git log --oneline -20 -- src/auth/login.ts
```
Extract scope from `feat(auth_login):` patterns. Most frequent scope matching a known feature stem: match.

Confidence: MEDIUM — confirm with engineer if not obvious.

#### Signal 4: Spec Content Search (scan cache)
Use `purlin_scan` cached data to search feature names, scenario titles, and requirement text for keywords matching the engineer's request.

"Add timeout to login" → scan finds auth_login spec has `#### Scenario: Login timeout handling`

Confidence: LOW-MEDIUM — always confirm with engineer. Present top 3 candidates.

### Resolution Flow Examples

**High-confidence match (no prompt needed):**
```
Engineer: "Fix the login timeout test"

Build reverse lookup:
  Signal 1: tests/auth_login/test_timeout.py → auth_login ✓ (deterministic)

Build proceeds against auth_login. No prompt.
```

**Medium-confidence match (confirm):**
```
Engineer: "Add a 30-second timeout to the login flow"

Build reverse lookup:
  Signal 1: Not test/skills → skip
  Signal 2: auth_login.impl.md lists src/auth/login.ts → MATCH

Build: "This belongs to feature 'auth_login'. Proceeding."
(Single high-confidence match → state it and proceed, don't ask)
```

**Low-confidence / ambiguous (ask):**
```
Engineer: "Fix the error handling in the webhook retry logic"

Build reverse lookup:
  Signal 3: commits touch webhook_delivery and error_handling
  Signal 4: both specs mention "retry"

Build: "Multiple features match:
  1. webhook_delivery — has retry scenarios
  2. error_handling — covers error patterns
  Which one?"
```

**No match (auto_create_features = false):**
```
Engineer: "Add a rate limiter middleware"

Build reverse lookup: no match across all signals

Build: "No existing feature matches 'rate limiter'.
  1. Attach to an existing spec (pick from list)
  2. Create a new spec
  3. Continue as one-off (no feature tracking)"
```

**No match (auto_create_features = true):**
```
Engineer: "Add a rate limiter middleware"

Build reverse lookup: no match

Build: "Creating feature spec 'rate_limiter'..."
→ Generates spec from context:
  - Infers requirements from what the code will do
  - Generates scenarios from the engineer's description
  - Places in appropriate category folder
→ Proceeds to implement against new spec

(Engineer can refine the spec later or PM can review it)
```

### Spec + Build Chaining

When the engineer's request implies both spec and code changes:

```
Engineer: "The login timeout should be configurable. Update the spec and build it."

1. Build detects spec change intent ("update the spec")
2. Reverse lookup finds: auth_login
3. Build chains: purlin:spec auth_login → purlin:build auth_login
4. Marker transitions: "spec" → "build"
```

---

## Skills Requiring Detailed Changes

### 1. purlin:build (HIGH IMPACT — feature resolution + marker + companions)

**Changes to Step 0 (Pre-Flight):**

A. **Add active_skill marker at skill start:**
```bash
mkdir -p .purlin/runtime && echo "build" > .purlin/runtime/active_skill
```

B. **Replace Spec Existence Check with Smart Feature Resolution:**

Current (Step 0, first bullet):
> If a feature name was provided as argument, verify the spec exists. If NOT: offer to create one.

New:
> **Feature Resolution (mandatory before any writes):**
> 1. If a feature name was provided → resolve via `features/**/<name>.md` (existing)
> 2. If no feature name but specific file(s) targeted → run Reverse Lookup Cascade (Signals 1-4)
> 3. If no feature name and no specific file → run purlin:status, pick highest-priority item (existing)
> 4. If high-confidence match → state it and proceed. If ambiguous → ask engineer to confirm.
> 5. If no match + `auto_create_features: true` → generate spec from context and proceed
> 6. If no match + `auto_create_features: false` → offer: attach to existing, create spec, or one-off

C. **FORBIDDEN pre-scan scope clarification:**
> "Grep the feature's CODE files for FORBIDDEN patterns. Exclude paths classified as OTHER in write_exceptions."

D. **Companion Code Files section (Step 2):**
> When writing code files, maintain `## Code Files` section in the companion:
> - If companion has `## Code Files` → append new files not already listed
> - If companion exists but no `## Code Files` → add the section with all files touched
> - If creating new companion → always include `## Code Files`
> This section is the primary mechanism for reverse lookup and should list every file the feature's implementation touches.

E. **Add active_skill marker cleanup at skill end:**
```bash
rm -f .purlin/runtime/active_skill
```

### 2. purlin:spec-code-audit (HIGH IMPACT — OTHER exclusion)

**Step 0.5.1 (Enumerate Code Files):**

Current: Globs code extensions, excludes hardcoded directories.

New — add to exclusion logic:
```
Read write_exceptions from .purlin/config.json.
After globbing code files, filter out any path matching write_exceptions.
These are OTHER files — they don't need feature specs and aren't code.
```

Add to preamble text:
> "Code files = all project files outside features/ that are not classified as OTHER. OTHER files (docs, README, config dotfiles) are excluded from the audit entirely — they don't need feature specs."

**Step 0.5.3 (Classify Unowned Files):**

Before labeling a file as "orphaned," check: does it match write_exceptions? If yes → skip. Only CODE files can be orphans.

**Step D.1 (Orphan Scanning):**

Same: exclude OTHER files from orphan classification.

**Subagent Protocol (Phase 1 deep scan):**

Add to each subagent's prompt payload:
> "Exclude these OTHER patterns from your analysis: [write_exceptions list]"

**Report Output — Add OTHER section:**
```
OTHER files (not audited — no spec required):
  docs/ (8 files), README.md, CHANGELOG.md, LICENSE
```

This shows completeness — the audit isn't ignoring files, it's correctly scoping them.

### 3. purlin:whats-different (MEDIUM-HIGH IMPACT — OTHER grouping)

**Step 2 (Gather and Classify):**

Current: Groups files as CODE, SPEC, QA, IMPL by path heuristics.

New: Use `classify_file()` for each changed file (now returns OTHER). Group into sections:

```
SPEC changes:
  notification_system: updated retry_count requirement

CODE changes:
  scripts/payment.py: error handling refactor (+28/-12)
  tests/notification/test_retry.py: new test file

Other changes:
  docs/api-guide.md: updated webhook section
  README.md: version bump
```

"Other changes" section is purely informational — no sync drift, no feature mapping, no action items.

**Role Briefing — Collapse OTHER:**

When role is specified (pm/engineer/qa), OTHER changes shown at bottom, brief:
```
Also changed (not tracked): docs/api-guide.md, README.md (+2 more)
```

Not highlighted, not actionable — just FYI.

### 4. purlin:status (LOW IMPACT — informational OTHER section)

**Add to output format:**

When session has OTHER file edits (from sync_state unclassified_writes):
```
Other files changed this session: docs/guide.md, README.md
```

Shown at bottom. No priority, no work items. Just visibility.

### 5. config_engine.py (MEDIUM IMPACT — OTHER classification)

**classify_file() — Add OTHER check:**

Insert before the CODE catch-all patterns:
```python
# --- OTHER (write exceptions from config) ---
exceptions = _read_write_exceptions()
for pattern in exceptions:
    if pattern.endswith('/'):
        if path.startswith(pattern):
            return 'OTHER'
    elif basename == pattern or path == pattern:
        return 'OTHER'
```

This is the canonical change. All callers automatically get OTHER support.

**Add helper:**
```python
def _read_write_exceptions():
    """Read write_exceptions from .purlin/config.json."""
    config = resolve_config()
    return config.get('write_exceptions', [])
```

### 6. scan_engine.py (LOW IMPACT — unclassified writes count)

**classify_work_items() — Add other_files_changed:**

Read sync_state.json, count `unclassified_writes`. Return in the classified result:
```python
classified["other_files_changed"] = len(
    sync_state.get("unclassified_writes", [])
)
```

### 7. purlin_server.py (LOW IMPACT — MCP tool update)

**handle_purlin_classify():**

Already returns classification from `classify_file()`. No change needed — it will automatically return "OTHER" once config_engine is updated.

### Skills NOT Needing Changes

| Skill | Why |
|---|---|
| spec-catch-up | Uses sync ledger timestamps, no file classification |
| complete | Checks scan outcomes, not files |
| find | Feature-level sync status, not file-level |
| smoke | Reads feature specs and test files |
| verify | Executes tests and checklists |
| resume | Checkpoint restore and work discovery |
| regression | Test fixture I/O |
| unit-test | Test file I/O |
| discovery | Writes to features/ (already spec-gated) |
| propose | Writes to features/ (already spec-gated) |
| tombstone | Writes to features/ (already spec-gated) |
| fixture | Test fixture management |
| anchor | Writes to features/ (already spec-gated) |
| infeasible | Writes to features/ (already spec-gated) |

### All Skills Needing Marker Protocol

These skills write files and need `active_skill` marker set/clear added:

**Spec writers (write to features/):**
- purlin:spec — `echo "spec"`
- purlin:spec-catch-up — `echo "spec-catch-up"`
- purlin:anchor — `echo "anchor"`
- purlin:discovery — `echo "discovery"`
- purlin:propose — `echo "propose"`
- purlin:tombstone — `echo "tombstone"`
- purlin:spec-from-code — `echo "spec-from-code"`
- purlin:spec-code-audit — `echo "spec-code-audit"` (writes both spec and code)
- purlin:infeasible — `echo "infeasible"`

**Code writers (write outside features/):**
- purlin:build — `echo "build"`
- purlin:unit-test — `echo "unit-test"`
- purlin:regression — `echo "regression"`
- purlin:smoke — `echo "smoke"`
- purlin:fixture — `echo "fixture"`
- purlin:toolbox — `echo "toolbox"`
- purlin:verify — `echo "verify"` (writes tests + discoveries)

**Already has bypass protocol (add marker too):**
- purlin:invariant — `echo "invariant"` (plus existing bypass lock for invariant files)

---

## User Experience Walkthroughs

### Engineer: "Make this change" (typical workflow)

```
Engineer: "Add a 30-second timeout to the login flow"

→ Agent thinks: "I need to edit src/auth/login.ts"
→ Write guard blocks: "Use purlin:build"
→ Agent invokes purlin:build

Build pre-flight:
  1. Reverse lookup for "login timeout":
     - Signal 3: auth_login.impl.md references src/auth/login.ts → MATCH
  2. "This belongs to feature 'auth_login'. Proceeding."
  3. Reads auth_login spec → understands requirements
  4. Sets marker → writes code → updates .impl.md
  5. Sync tracks changes against auth_login

Result: Code change properly tracked, connected to spec.
```

### Engineer: "Modify specs to meet these new requirements"

```
Engineer: "We need to support batch webhooks. Update the spec and build it."

→ Agent detects: spec change + code change needed
→ Agent invokes purlin:spec webhook_delivery
  → Spec skill sets marker → updates spec → clears marker
→ Agent invokes purlin:build webhook_delivery
  → Build sets marker → implements against updated spec → clears marker

Result: Spec updated first, then code built against it. Both tracked.
```

### Engineer: "Fix this utility function" (no clear feature)

```
Engineer: "The date formatter in src/utils/format.ts is broken for UTC dates"

→ Write guard blocks → Agent invokes purlin:build

Build pre-flight:
  1. Reverse lookup for src/utils/format.ts:
     - Signal 3: No impl files reference it
     - Signal 5: git log shows it was last touched in feat(date_handling): → MATCH
  2. "This maps to feature 'date_handling'. Proceed?"
  3. Engineer confirms → Build proceeds against date_handling spec

Result: Bug fix tracked against the right feature.
```

### Engineer: "Add a completely new utility" (no feature exists)

```
Engineer: "Add a rate limiter middleware"

→ Write guard blocks → Agent invokes purlin:build

Build pre-flight:
  1. Reverse lookup: no match across all 6 signals
  2. Build presents:
     "No existing feature matches 'rate limiter'.

     1. Create a new spec → purlin:spec rate_limiter
     2. Attach to an existing spec (closest: api_gateway, auth_middleware)
     3. Continue as one-off (no feature tracking)"

  3. Engineer: "Create the spec"
     → purlin:spec rate_limiter invoked → spec created
     → Build resumes against rate_limiter

  Result: New spec created, code tracked from day one.
```

### Engineer: "Update the README"

```
→ Write guard step 4: README.md in write_exceptions → ALLOW
→ Edit proceeds directly, no skill needed
→ Status shows: "Other files changed: README.md" (informational)
```

### PM: "Add retry requirements to webhook spec"

```
→ Write guard step 3: features/ path → check marker → BLOCKED
→ Agent invokes purlin:spec webhook_delivery
→ Spec sets marker → writes spec → clears marker
→ Status: webhook_delivery sync_status becomes spec_ahead
→ Engineer sees: "spec ahead — needs implementation"
```

### PM: "What needs my attention?"

```
/status pm

PM Work (4 items):
  ● incomplete_spec: user_preferences — Missing requirements section
  ● unacknowledged_deviations: payment_gateway — 1 deviation needs ack
  ● intent_drift: search_indexer — "relevance scoring diverges from spec"
  ○ spec_ahead: webhook_delivery — spec updated, awaiting implementation

Other files changed this session: docs/api-guide.md
```

### Engineer: "/whats-different engineer"

```
Changes since last session (14h ago, 8 commits):

SPEC changes (affects your code):
  webhook_delivery: retry requirements added — code needs updating
  notification_system: added retry_count requirement

CODE changes:
  src/auth/login.ts: timeout fix (+12/-3)
  tests/auth_login/test_timeout.py: new test

Companion updates:
  auth_login.impl.md: timeout implementation notes

Also changed (not tracked): docs/api-guide.md, README.md

Sync drift:
  auth_login: synced ✓
  webhook_delivery: spec ahead — needs implementation
```

### QA: "/status qa"

```
QA Work (3 items):
  ● regression_fail: payment_gateway — regression FAIL
  ● regression_stale: notification_system — Run purlin:regression to update
  ● testing: webhook_delivery — TESTING with QA scenarios defined
```

### spec-code-audit catches remaining gaps

```
/purlin:spec-code-audit

Feature Coverage:
  auth_login: 4 code files, spec synced ✓
  webhook_delivery: spec ahead, 0 code files yet
  payment_gateway: 3 code files, code ahead — needs spec update

Orphaned Code (CODE files with no feature mapping):
  src/utils/legacy_helper.ts — no feature (create spec or classify as OTHER?)

OTHER files (not audited — no spec required):
  docs/ (8 files), README.md, CHANGELOG.md, LICENSE
```

---

## Implementation Order

### Phase 1: Core Infrastructure
1. **config_engine.py** — Add `_read_write_exceptions()`, add OTHER to `classify_file()`
2. **write-guard.sh** — Three-bucket decision tree + active_skill marker check
3. **session-init-identity.sh** — Clear stale active_skill marker

### Phase 2: Classification Skill
4. **skills/classify/SKILL.md** — New skill: add/remove/list write_exceptions
5. **purlin:init** — Seed default write_exceptions

### Phase 3: Build Smart Resolution
6. **skills/build/SKILL.md** — Active_skill marker + reverse lookup cascade (Signals 1-4) + `## Code Files` companion protocol + auto_create_features support + spec-then-build chaining
7. **config_engine.py** — Add `auto_create_features` config key (default: false)

### Phase 4: Other Skill Markers
8. **skills/spec/SKILL.md** — Marker protocol
9. **All other writing skills** — Marker set/clear (17 skills listed above)

### Phase 5: Classification-Aware Skills
10. **skills/spec-code-audit/SKILL.md** — Exclude OTHER from code inventory, orphan scan, subagent prompts. Add OTHER section to report.
11. **skills/whats-different/SKILL.md** — Use classify_file() in Step 2. Add OTHER group. Collapse in role briefings.
12. **skills/status/SKILL.md** — Add informational OTHER section to output

### Phase 6: Supporting Infrastructure
13. **scripts/mcp/scan_engine.py** — Add other_files_changed count
14. **agents/purlin.md** — Define three-bucket model in vocabulary (Section 2.0). Strengthen routing rules (Sections 4.1, 4.5). Add: "When asked to make changes, purlin:build will find the right feature. The write guard ensures skills are used."

### Phase 7: Spec + Tests
15. **features/framework_core/purlin_sync_system.md** — Document three-bucket model, active_skill marker, write_exceptions, reverse lookup, auto_create_features
16. **tests/purlin_sync_system/test_write_guard.sh** — Comprehensive test cases
17. **references/file_classification.json** — Add OTHER classification rules
18. **references/file_classification.md** — Update docs

## Critical Files

| File | Change | Priority |
|---|---|---|
| `scripts/mcp/config_engine.py` | OTHER in classify_file(), write_exceptions reader | P1 |
| `hooks/scripts/write-guard.sh` | Three-bucket decision tree + active_skill check | P1 |
| `hooks/scripts/session-init-identity.sh` | Stale marker cleanup | P1 |
| `skills/classify/SKILL.md` | New skill (create) | P2 |
| `skills/build/SKILL.md` | Marker + reverse lookup cascade + spec chaining | P3 |
| `skills/spec/SKILL.md` | Marker protocol | P4 |
| `skills/spec-code-audit/SKILL.md` | OTHER exclusion (Steps 0.5.1, 0.5.3, D.1, subagents, report) | P5 |
| `skills/whats-different/SKILL.md` | OTHER group + role briefing collapse | P5 |
| `skills/status/SKILL.md` | Informational OTHER section | P5 |
| `scripts/mcp/scan_engine.py` | other_files_changed count | P6 |
| `agents/purlin.md` | Three-bucket vocabulary + routing rules | P6 |
| `features/framework_core/purlin_sync_system.md` | Spec docs | P7 |
| `tests/purlin_sync_system/test_write_guard.sh` | Tests | P7 |
| `references/file_classification.json` | OTHER rules | P7 |
| `references/file_classification.md` | Docs update | P7 |
| 17 SKILL.md files | Marker set/clear (2 lines each) | P4 |

## Test Plan

### Write Guard
1. `.purlin/config.json` → ALLOW (system)
2. `features/_invariants/i_ext.md` → INVARIANT block (unchanged)
3. `features/auth/login.md` no marker → BLOCK (spec)
4. `features/auth/login.md` marker="spec" → ALLOW
5. `features/auth/login.impl.md` no marker → BLOCK (in features/)
6. `features/auth/login.impl.md` marker="build" → ALLOW
7. `src/auth.ts` no marker → BLOCK (code)
8. `src/auth.ts` marker="build" → ALLOW
9. `docs/guide.md` no marker, `docs/` excepted → ALLOW (OTHER)
10. `docs/guide.md` no marker, not excepted → BLOCK (code)
11. `README.md` excepted → ALLOW
12. No escape hatch — blocked writes require invoking the correct skill

### Classification
13. `classify_file("docs/guide.md")` with exception → "OTHER"
14. `classify_file("src/auth.ts")` → "CODE"
15. `classify_file("features/auth/login.md")` → "SPEC"

### Integration
16. purlin:classify add (requires user confirmation)/list/remove
17. Build reverse lookup: test/ path → correct feature
18. Build reverse lookup: impl reference → correct feature
19. Build reverse lookup: no match → offers create/attach/one-off
20. Full skill lifecycle: invoke → marker set → writes pass → marker cleared
21. Session-start clears stale marker
