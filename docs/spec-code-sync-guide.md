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

## Enforcement Gates

Four gates ensure companion files stay current. All are **mechanical** — they check whether the file changed, not whether the engineer's judgment was correct.

### Gate 1: Build Completion (`purlin:build` Step 4)

Before committing a status tag (`[Complete]` or `[Ready for Verification]`):

- Were code commits made for this feature during the session?
- Does the companion file have new entries?
- If no new entries: **blocked.** Write at least `[IMPL]` entries first.

### Gate 2: Mode Switch

Before switching out of Engineer mode:

- Were code commits made for any feature without companion updates?
- If companion debt exists: **blocked.** No skip option. Write the entries.

### Gate 3: Session Save (`purlin:resume save`)

Before writing a checkpoint:

- Same companion debt check as Gate 2.
- **Warning only** (not blocking) — session saves during crashes shouldn't lose work.

### Gate 4: Scan (Background)

The scan compares code commit timestamps against companion file timestamps:

- If code is newer than the companion: flagged as `companion_debt`.
- `purlin:status` routes it to Engineer action items.
- Catches debt from manual git commits, session crashes, or anything Gates 1-3 missed.

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

## The Spec-Code Audit

`purlin:spec-code-audit` uses companion entries as a structured index:

- **Companion debt** — code without entries is flagged HIGH severity.
- **Impl-to-spec tracing** — `[IMPL]` references map code back to spec requirements.
- **Stale notes** — code modified since the last companion entry is flagged MEDIUM.
- **Coverage completeness** — features with only `[IMPL]` entries (no deviations) are deprioritized in deep comparison, since they signal spec-aligned implementation.

---

## Day-to-Day Workflow

**As an Engineer:**

1. Read the spec before building.
2. Read the companion file for prior decisions.
3. Build the feature.
4. For each commit batch, write companion entries:
   - `[IMPL]` for work that matches the spec.
   - Deviation tags for anything else.
5. The gates handle the rest — you'll be reminded if you forget.

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
| Review deviations (PM) | `purlin:status` then read the companion file |
