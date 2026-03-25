# Feature: Release Audit Automation

> Label: "Tool: Release Audit Automation"
> Category: "Release Process"
> Prerequisite: features/policy_release.md
> Prerequisite: features/policy_critic.md
> Prerequisite: features/test_fixture_repo.md

[TODO]

## 1. Overview

Extracts deterministic check logic from release step agent instructions into standalone scripts that can run unattended. Each script reuses existing tool infrastructure (e.g., `graph.py` for cycle/orphan detection, `status.sh` for feature status) and produces structured JSON output. Tests use fixture repo tags with deliberate issues (cycles, broken links, stale paths, safety violations) to verify detection accuracy.

This converts ~26 of ~31 release process manual scenarios from "an agent reads instructions and does it" to "a script runs and reports results." The 5 scenarios that remain manual are interactive user-approval workflows where detection is tested but the decision stays human.

---

## 2. Requirements

### 2.1 Script Locations

All scripts are consumer-facing (in `tools/release/`), submodule-safe:

| Script | Covers |
|--------|--------|
| `tools/release/verify_dependency_integrity.py` | Cycle detection, broken links, reverse reference audit |
| `tools/release/verify_zero_queue.py` | Zero-queue mandate enforcement |
| `tools/release/submodule_safety_audit.py` | Submodule safety contract checks (7 categories) |
| `tools/release/doc_consistency_check.py` | README/documentation staleness detection |
| `tools/release/instruction_audit.py` | Override-base consistency checks |
| `tools/release/critic_consistency_check.py` | Critic terminology and routing rule consistency |

### 2.2 Shared Output Format

Every script MUST produce structured JSON to stdout:

```json
{
  "step": "<release-step-id>",
  "status": "PASS" | "FAIL" | "WARNING",
  "findings": [
    {
      "severity": "CRITICAL" | "WARNING" | "INFO",
      "category": "<check-category>",
      "file": "<file-path>",
      "line": <line-number-or-null>,
      "message": "<human-readable description>"
    }
  ],
  "summary": "<one-line summary>"
}
```

- `status: "PASS"` -- zero CRITICAL or WARNING findings.
- `status: "FAIL"` -- one or more CRITICAL findings (release blocked).
- `status: "WARNING"` -- warnings only, no critical (release proceeds with acknowledgment).
- Scripts exit 0 on PASS/WARNING, exit 1 on FAIL.

### 2.3 Submodule Safety

- All scripts use `PURLIN_PROJECT_ROOT` as the primary project root detection, with directory-climbing fallback.
- No artifacts written inside `tools/`.
- Config file access wrapped in `try/except` with fallback defaults.
- No CWD-relative path assumptions.

### 2.4 verify_dependency_integrity.py

**Reuses:** `tools/cdd/graph.py` for graph construction and cycle detection.

**Checks:**
1. **Graph freshness:** Compare `dependency_graph.json` mtime against most recently modified feature file. If stale, regenerate via `status.sh --graph`.
2. **Cycle detection:** Run graph cycle check. Report cycle path if found.
3. **Broken links:** For each `> Prerequisite:` link, verify target file exists in `features/`.
4. **Reverse reference audit:** For each parent-child relationship, scan parent body for child filename references. Report structural reversals (CRITICAL) and example coupling (WARNING).

**Automates scenarios from:** `release_verify_dependency_integrity.md` (7 of 7 scenarios).

### 2.5 verify_zero_queue.py

**Reuses:** `tools/cdd/status.sh` JSON output for per-feature role status.

**Checks:**
1. Run `status.sh` and parse JSON output.
2. For each feature, verify `architect: "DONE"`, `builder: "DONE"`, and `qa` in `["CLEAN", "N/A"]`.
3. Report blocking features with their specific failing role column.

**Automates scenarios from:** `release_verify_zero_queue.md` (4 of 4 scenarios).

### 2.6 submodule_safety_audit.py

**Checks (7 categories):**
1. **PURLIN_PROJECT_ROOT check:** Scan Python tools for `os.environ.get('PURLIN_PROJECT_ROOT')` or equivalent. Flag tools that perform directory climbing without checking the env var first.
2. **Climbing priority:** Verify climbing order checks further path before nearer path.
3. **Artifact write location:** Scan for file write operations targeting paths inside `tools/`. Flag `.pid`, `.log`, `.json` writes not under `.purlin/runtime/` or `.purlin/cache/`.
4. **Unguarded json.load:** Scan for `json.load()` calls on config files without surrounding `try/except`.
5. **CWD-relative paths:** Scan for `os.getcwd()` usage or bare relative paths in file operations.
6. **Hardcoded project-root assumptions:** Scan for hardcoded paths like `/tools/` or assumptions about the working directory structure.
7. **Instruction file path references:** Verify path references in instruction files resolve correctly.

**Automates scenarios from:** `release_submodule_safety_audit.md` (4 of 5 deterministic scenarios). The 1 remaining scenario (WARNING finding confirmed by user) stays manual because it requires user judgment.

### 2.7 doc_consistency_check.py

**Checks:**
1. **Feature coverage:** Cross-reference `features/*.md` file list against README.md content. Identify features not mentioned.
2. **Stale references:** Scan README.md for file paths, command names, and config options. Verify each exists in the current codebase.
3. **Removed functionality:** Check for references to tombstoned features or deleted files.

**Output includes:** List of stale references (auto-fixable) and coverage gaps (require user decision).

**Automates scenarios from:** `release_doc_consistency_check.md` (4 of 7 deterministic detection scenarios). The 3 interactive scenarios (user approves/declines additions, prohibited auto-create) stay manual.

### 2.8 instruction_audit.py

**Checks:**
1. **Override presence:** Verify all 4 `.purlin/*_OVERRIDES.md` files exist.
2. **Contradiction scan:** For each override rule, check against base layer for direct negations (keyword matching + structural analysis).
3. **Stale path references:** Scan override files for file path references. Verify each resolves.
4. **Terminology consistency:** Check for deprecated terms across all instruction files.

**Automates scenarios from:** `instruction_audit.md` (3 of 4 scenarios). The 1 remaining scenario (unresolvable base-layer conflict) stays manual because it requires human decision on how to resolve.

### 2.9 critic_consistency_check.py

**Checks:**
1. **Deprecated terminology:** Scan Critic-related files for "quality gate" (should be "coordination engine") and other deprecated terms from the terminology table.
2. **Routing rule consistency:** Cross-reference routing rules between `policy_critic.md` and `HOW_WE_WORK_BASE.md` Section 7.5. Flag discrepancies.
3. **Missing mandates:** Verify all Critic mandates referenced in instruction files have corresponding implementation.
4. **README Critic section:** Verify `## The Critic` section in README.md matches current Critic behavior.

**Automates scenarios from:** `release_critic_consistency_check.md` (4 of 4 scenarios).

### 2.10 release_framework_doc_consistency.py (Optional Extension)

**Note:** This overlaps with `doc_consistency_check.py` and `instruction_audit.py`. If the overlap is sufficient, this script MAY be omitted and its checks folded into the other two. Engineer mode makes this determination during implementation.

**Would automate scenarios from:** `release_framework_doc_consistency.md` (4 of 4 scenarios, all deterministic detection).

### 2.11 Fixture Tags for Testing

Each script is tested against fixture repo states that contain deliberate issues:

| Tag | Contains |
|-----|----------|
| `main/release_verify_deps/clean-graph` | Valid dependency graph, no issues |
| `main/release_verify_deps/cycle-in-prerequisites` | Features with circular prerequisite links |
| `main/release_verify_deps/broken-link` | Feature with prerequisite pointing to nonexistent file |
| `main/release_verify_deps/reverse-reference` | Parent feature body-referencing child |
| `main/release_zero_queue/all-clean` | All features DONE/CLEAN |
| `main/release_zero_queue/builder-todo` | Feature with builder: TODO |
| `main/release_zero_queue/qa-open-items` | Feature with qa: HAS_OPEN_ITEMS |
| `main/release_submodule_safety/clean` | All tools submodule-safe |
| `main/release_submodule_safety/missing-env-check` | Python tool without PURLIN_PROJECT_ROOT check |
| `main/release_submodule_safety/artifact-in-tools` | Script writing .pid inside tools/ |
| `main/release_submodule_safety/unguarded-json-load` | Bare json.load without try/except |
| `main/release_doc_consistency/clean-docs` | README matches current features |
| `main/release_doc_consistency/stale-reference` | README references deleted file |
| `main/release_critic_consistency/clean` | All Critic files consistent |
| `main/release_critic_consistency/deprecated-term` | File using "quality gate" |
| `main/release_instruction_audit/clean` | All overrides consistent with base |
| `main/release_instruction_audit/contradiction` | Override negating base rule |
| `main/release_instruction_audit/stale-path` | Override referencing deleted file |

### 2.12 Scenarios That Remain Manual

The following ~5 scenarios require human judgment and stay manual:

1. **Submodule safety WARNING confirmed by user** (`release_submodule_safety_audit.md`) -- detection is automated, user confirmation is not.
2. **Coverage gaps: user approves some additions** (`release_doc_consistency_check.md`) -- detection is automated, selection is not.
3. **Coverage gaps: user declines all additions** (`release_doc_consistency_check.md`) -- detection is automated, decision is not.
4. **New major section prohibited without confirmation** (`release_doc_consistency_check.md`) -- the prohibition is a process rule, not a check.
5. **Audit blocked by unresolvable base-layer conflict** (`instruction_audit.md`) -- requires human decision on resolution path.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Dependency integrity script detects cycle

    Given the fixture tag "main/release_verify_deps/cycle-in-prerequisites" is checked out
    And the fixture contains features with circular prerequisite links
    When `verify_dependency_integrity.py` is run against the fixture
    Then the output JSON has status "FAIL"
    And findings contain a CRITICAL entry with the cycle path
    And the script exits with status 1

#### Scenario: Dependency integrity script passes on clean graph

    Given the fixture tag "main/release_verify_deps/clean-graph" is checked out
    When `verify_dependency_integrity.py` is run against the fixture
    Then the output JSON has status "PASS"
    And findings array is empty
    And the script exits with status 0

#### Scenario: Dependency integrity detects broken prerequisite link

    Given the fixture tag "main/release_verify_deps/broken-link" is checked out
    When `verify_dependency_integrity.py` is run against the fixture
    Then the output JSON has status "FAIL"
    And findings contain a CRITICAL entry with the source file and missing target

#### Scenario: Dependency integrity detects reverse reference

    Given the fixture tag "main/release_verify_deps/reverse-reference" is checked out
    When `verify_dependency_integrity.py` is run against the fixture
    Then findings contain a CRITICAL entry for the structural reversal
    And the parent and child file names are identified

#### Scenario: Zero queue script reports blocking features

    Given the fixture tag "main/release_zero_queue/builder-todo" is checked out
    When `verify_zero_queue.py` is run against the fixture
    Then the output JSON has status "FAIL"
    And findings identify the specific feature and failing role column

#### Scenario: Zero queue script passes when all features are done

    Given the fixture tag "main/release_zero_queue/all-clean" is checked out
    When `verify_zero_queue.py` is run against the fixture
    Then the output JSON has status "PASS"
    And the summary reports the total feature count

#### Scenario: Submodule safety detects missing env var check

    Given the fixture tag "main/release_submodule_safety/missing-env-check" is checked out
    When `submodule_safety_audit.py` is run against the fixture
    Then the output JSON has status "FAIL"
    And findings contain a CRITICAL entry identifying the Python tool file

#### Scenario: Submodule safety detects artifact written inside tools

    Given the fixture tag "main/release_submodule_safety/artifact-in-tools" is checked out
    When `submodule_safety_audit.py` is run against the fixture
    Then findings contain a CRITICAL entry identifying the script and write target

#### Scenario: Submodule safety passes on clean codebase

    Given the fixture tag "main/release_submodule_safety/clean" is checked out
    When `submodule_safety_audit.py` is run against the fixture
    Then the output JSON has status "PASS"

#### Scenario: Critic consistency detects deprecated terminology

    Given the fixture tag "main/release_critic_consistency/deprecated-term" is checked out
    When `critic_consistency_check.py` is run against the fixture
    Then the output JSON has status "FAIL"
    And findings identify the file and deprecated term

#### Scenario: Doc consistency detects stale reference

    Given the fixture tag "main/release_doc_consistency/stale-reference" is checked out
    When `doc_consistency_check.py` is run against the fixture
    Then findings contain a WARNING or CRITICAL entry identifying the stale reference

#### Scenario: Instruction audit detects contradiction

    Given the fixture tag "main/release_instruction_audit/contradiction" is checked out
    When `instruction_audit.py` is run against the fixture
    Then findings contain a CRITICAL entry identifying the conflicting override and base rules

#### Scenario: Instruction audit detects stale path

    Given the fixture tag "main/release_instruction_audit/stale-path" is checked out
    When `instruction_audit.py` is run against the fixture
    Then findings contain a WARNING entry identifying the override file and stale path

#### Scenario: All scripts produce valid JSON output

    Given any release audit script is run
    When the script completes
    Then stdout contains valid JSON parseable by python3 json.loads
    And the JSON contains "step", "status", "findings", and "summary" keys

### Manual Scenarios (Human Verification Required)

None.
