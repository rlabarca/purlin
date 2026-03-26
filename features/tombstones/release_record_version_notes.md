# Feature: Record Version & Release Notes

> Label: "Release Step: Record Version & Release Notes"
> Category: "Release Process"
> Prerequisite: features/policy_release.md
> Prerequisite: features/release_checklist_core.md

## 1. Overview

This feature defines the `purlin.record_version_notes` release step: the final step in the release checklist. It collects candidate release notes from git history, presents them to PM mode for confirmation and editing, gathers the version number, and records both in the `## Releases` section of `README.md`.

## 2. Requirements

### 2.1 Tag Discovery

PM mode determines the most recent release tag by running `git tag --sort=-v:refname | head -1`. If no tags exist, all commits are treated as new.

### 2.2 Commit Candidate Collection

PM mode collects commit summaries since the last tag by running `git log <last-tag>..HEAD --oneline --no-merges` (or `git log --oneline --no-merges` if no tags exist). Each commit line is treated as a release notes candidate.

### 2.3 Suggestion Synthesis

PM mode synthesizes a concise bulleted suggestion list from the candidate commits, grouping by theme where meaningful (features, fixes, process changes). The list is presented as a starting point, not a final result.

### 2.4 User Confirmation

PM mode presents the suggestions to the user:

> "Suggested release notes since `<last-tag>` — paste any you would like to include, edit freely, or write your own:"

PM mode then asks the user for:

1. The new version number (e.g., `v1.2.0`)
2. Their confirmed release notes (free text)

The user may copy from suggestions, combine entries, or write entirely custom notes.

### 2.5 README.md Recording

PM mode inserts a new entry into `README.md` under the `## Releases` heading (creating the heading if absent). Entry format:

```
### <version> — <YYYY-MM-DD>

<confirmed release notes text>
```

New entries are prepended at the top of the `## Releases` section (most recent first).

### 2.6 Step Metadata

| Field | Value |
|-------|-------|
| ID | `purlin.record_version_notes` |
| Friendly Name | `Record Version & Release Notes` |
| Code | null |
| Agent Instructions | See Sections 2.1–2.5 above. |

### 2.7 Regression Testing

Regression tests verify the architect agent correctly generates release notes.
- **Approach:** Agent behavior harness (`claude --print` with fixtures)
- **Scenarios covered:** No-tags handling, prior-tag changelog, clean-state negative tests
- **Fixture tags:** See Integration Test Fixture Tags section

---

## 3. Scenarios

### Unit Tests

None. All verification is manual (PM-executed release step).

### QA Scenarios

#### Scenario: No prior release tags @manual

    Given the repository has no git tags
    When PM mode executes the purlin.record_version_notes step
    Then PM mode presents commit candidates from the full git log
    And asks the user for version number and release notes
    And inserts the new entry into README.md under ## Releases

#### Scenario: Prior release tag exists @manual

    Given the repository has a most-recent tag of v1.0.0
    When PM mode executes the purlin.record_version_notes step
    Then PM mode presents only commits after v1.0.0 as candidates
    And asks the user for the new version number and confirmed notes
    And inserts the new entry at the top of the ## Releases section

#### Scenario: User writes custom notes @manual

    Given PM mode presents suggested release notes from git history
    When the user provides their own text rather than selecting from suggestions
    Then PM mode uses the user-provided text verbatim in the README.md entry

#### Scenario: README.md lacks Releases heading @manual

    Given README.md does not contain a ## Releases section
    When PM mode records the version notes
    Then PM mode creates the ## Releases heading in README.md
    And inserts the new entry beneath it

## Regression Guidance
- Tag discovery: correct handling of no-tags-exist case (all commits treated as new)
- User-provided notes used verbatim (not modified by synthesis)
- Missing ## Releases heading auto-created in README.md
