# Spec-Code Sync Guide

How specs and code stay in sync through companion files, decision tags, and enforcement gates.

---

## The Core Idea

Specs and code drift apart. PM writes the spec, Engineer builds the code, and implementation always reveals things the spec didn't anticipate. The question isn't whether drift happens — it's whether drift is **visible**.

Purlin's answer: the **companion file** (`features/<name>.impl.md`). Every code change gets documented there. The companion file is Engineer-owned and updated in the same commit as the code. It captures reality *now*, even when the spec won't be updated until PM catches up.

```
Spec (PM intent) + Companion (Engineer reality) = Complete picture
```

If you read a feature's spec and its companion file together, you know exactly what was intended, what was built, and where they differ.

---

## The Companion File Commit Covenant

Every Engineer code commit for a feature **must** include a companion file update. No exceptions. No "this matches the spec exactly, so I'll skip it."

The minimum entry is one `[IMPL]` line:

```markdown
**[IMPL]** Built webhook retry logic per spec requirement 3.2
```

If the change deviates from the spec, use the appropriate deviation tag instead:

```markdown
**[DEVIATION]** Used exponential backoff instead of linear (spec says linear,
but exponential prevents thundering herd under load) (Severity: HIGH)
```

### Batching

Multiple rapid commits for the same feature (implement + test + fix) can batch their entries into a single companion update with the last commit. The gate fires at build completion, not per-commit.

---

## Decision Tags

When documenting work in the companion file, use the tag that matches the situation:

| Tag | Severity | When to Use | PM Reviews? |
|-----|----------|-------------|-------------|
| `[IMPL]` | NONE | Implemented as the spec says. | No |
| `[CLARIFICATION]` | INFO | Interpreted ambiguous spec language. | No |
| `[AUTONOMOUS]` | WARN | Spec was silent — filled the gap with judgment. | Yes |
| `[DEVIATION]` | HIGH | Intentionally diverged from what the spec says. | Yes |
| `[DISCOVERY]` | HIGH | Found a requirement the spec didn't state. | Yes |
| `[INFEASIBLE]` | CRITICAL | Cannot implement as specified — work halts. | Yes |

**Format:** `**[TAG]** <description> (Severity: <level>)` — omit the severity line for `[IMPL]`.

`[IMPL]` is the everyday tag. It's lightweight, doesn't require PM review, and doesn't appear in the Active Deviations table. The higher-severity tags surface as PM action items in `purlin:status`.

---

## The Active Deviations Table

Companion files have a structured table at the top for deviations that PM needs to review:

```markdown
# Implementation Notes: Webhook Delivery

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| Linear backoff | Exponential backoff | DEVIATION | PENDING |
| (silent on priority) | Defaults to NORMAL | DISCOVERY | PENDING |
```

PM reviews these via `purlin:status` and marks each as:

- **ACCEPTED** — PM agrees with the deviation.
- **REJECTED** — PM overrules; Engineer follows the spec.
- **Clarification requested** — PM needs more context.

`[IMPL]` entries live in the prose body below the table, not in the table itself.

---

## Enforcement and Detection

Companion file enforcement works at two levels: a **session-level gate** that blocks mode switches, and **scan-based detection** that surfaces feature-level debt in `purlin:status`.

### Session-Level Gate: Mode Switch

The hard enforcement point. When switching out of Engineer mode, the `purlin_mode` tool checks whether code files were modified during the session without any companion files being written:

- Code files modified + zero companion files written → **blocked** (when switching to QA or default mode).
- **Engineer→PM switches are exempt** — updating specs is a natural part of engineer work. Companion debt persists until resolved.
- The engineer must write at least one companion file with `[IMPL]` entries, or run `purlin:spec-code-audit` to reconcile.
- This is project-agnostic — it tracks file writes, not file-to-feature mappings. Works for any language or project structure.
- The gate resets after a successful non-PM mode switch.

### Build Advisory: Step 4 Pre-check

Before committing a status tag, `purlin:build` checks whether the companion file was updated:

- If no new entries: **warns** (not blocks). Recommends writing `[IMPL]` entries.
- The mode switch gate provides the hard enforcement — the build check is an early reminder.

### Scan Detection: Feature-Level Debt

`purlin:status` includes companion debt as Engineer action items. The scan uses three signals to detect which features have stale or missing companions:

1. **Test directory commits:** `git log` on `tests/<stem>/` — catches code changes in test files.
2. **Status tag timestamps:** If a feature was tagged (Complete, Testing, etc.), the tag timestamp represents "code work happened." Compares against companion file modification time.
3. **Session debt:** The FileChanged hook tracks code changes in real-time. Uncommitted changes and in-progress work are captured here.

This catches features that were implemented but never got companion entries, regardless of where the code lives.

### Session Save (`purlin:resume save`)

Before writing a checkpoint:

- Same session-level companion debt check as the mode switch gate.
- **Warning only** (not blocking) — session saves during crashes shouldn't lose work.

---

## Three Ways to Escalate to PM

| Situation | What to Do | Blocking? |
|-----------|------------|-----------|
| Spec is impossible to implement | `purlin:infeasible feature-name` | Yes — work halts |
| Implementation differs from spec | Add a `[DEVIATION]` row to the companion table | No — build continues |
| Spec should be changed proactively | `purlin:propose topic` | No — suggestion only |

---

## How PM Reviews Deviations

1. PM runs `purlin:status` and sees unacknowledged deviations listed as action items.
2. PM reads the companion file's Active Deviations table.
3. For each entry, PM either:
   - Accepts (marks `[ACKNOWLEDGED]`, deviation stands).
   - Rejects (marks `[ACKNOWLEDGED]`, updates spec to override).
   - Requests clarification from Engineer.
4. Over time, acknowledged entries are pruned from the companion file as PM absorbs them into the spec.

---

## The Spec-Code Audit (Reconciliation Tool)

`purlin:spec-code-audit` serves two purposes: detection and **bulk reconciliation**.

**Detection** — uses companion entries as a structured index:

- **Companion debt** — code without entries is flagged HIGH severity.
- **Impl-to-spec tracing** — `[IMPL]` references map code back to spec requirements.
- **Stale notes** — code modified since the last companion entry is flagged MEDIUM.
- **Coverage completeness** — features with only `[IMPL]` entries (no deviations) are deprioritized in deep comparison, since they signal spec-aligned implementation.

**Reconciliation** — when companion debt has accumulated across multiple features, the audit's Phase 3 writes companion entries in bulk:

- For each feature with debt: reads the spec and implementation, writes `[IMPL]` entries documenting what was built.
- Uses deviation tags (`[DEVIATION]`, `[DISCOVERY]`) where code doesn't match spec.
- Commits all companion updates together.
- This is the recommended path when `purlin:status` shows multiple features with companion debt.

---

## Day-to-Day Workflow

**As an Engineer:**

1. Read the spec before building.
2. Read the companion file for prior decisions.
3. Build the feature.
4. For each commit batch, write companion entries:
   - `[IMPL]` for work that matches the spec.
   - Deviation tags for anything else.
5. The mode switch gate blocks if you haven't written any companion files. If debt accumulates, run `purlin:spec-code-audit` to catch up in bulk.

**As a PM:**

1. Check `purlin:status` for unacknowledged deviations.
2. Read the companion file's Active Deviations table.
3. Accept, reject, or request clarification for each entry.
4. Update the spec to absorb accepted deviations when ready.

---

## Quick Reference

| You want to... | What to do |
|----------------|------------|
| Document spec-aligned work | `**[IMPL]** <what you built>` in the companion file |
| Record a deviation | Add a row to the Active Deviations table with the appropriate tag |
| Escalate something impossible | `purlin:infeasible feature-name` |
| Suggest a spec change | `purlin:propose topic` |
| Check for companion debt | `purlin:status` (scan detects it automatically) |
| Reconcile debt in bulk | `purlin:spec-code-audit` (writes companion entries for all features with debt) |
| Review deviations (PM) | `purlin:status` then read the companion file |
