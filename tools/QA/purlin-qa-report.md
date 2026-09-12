---
name: purlin-qa-report
description: Fetches and analyzes a Purlin project digest from a git repository URL to produce a triaged QA report. Use when the user provides a repo URL and asks about QA status, test coverage, verification readiness, proof quality, or what needs manual testing. Produces an HTML artifact with color-coded severity sections.
---

# Purlin QA Report

Analyze a Purlin project digest and produce a triaged QA report. The user provides a git repository URL (and optionally a branch or tag), and you fetch the project digest, analyze it, and produce a clear, visual report of QA concerns.

## Step 1 — Clone the Repo and Read the Digest

The user provides a repo URL and optionally a branch or tag:
- `https://github.com/org/project` (defaults to `main`)
- `https://github.com/org/repo` branch `release/2.0`
- `git@github.com:org/project.git` tag `v1.2.0`

### 1a. Ensure git is available

```bash
git --version 2>/dev/null || echo "Git not found"
```

### 1b. Sparse-clone only the digest file

Clone just `.purlin/report-data.js` to minimize download size. Prefer `gh repo clone`, which takes
the credential from the `gh` keyring and never puts one on the command line:

```bash
gh repo clone <org>/<repo> /tmp/purlin-qa-digest -- \
  --depth 1 \
  --filter=blob:none \
  --sparse \
  --branch <branch-or-tag>

cd /tmp/purlin-qa-digest
git sparse-checkout set .purlin
```

Without `gh`, use a plain clone of the `https://<HOST>/<org>/<repo>.git` URL with the same four
flags and let the machine's configured credential helper supply the secret. Either way the URL
carries no credential.

If no branch/tag was specified, omit `--branch` (defaults to the repo's default branch).

### 1c. Handle auth failures

If the clone fails, work through authentication — do not give up.

| Error message | Likely cause |
|---|---|
| `Authentication failed` / `could not read Username` | HTTPS with no credentials stored |
| `Permission denied (publickey)` | SSH key not set up |
| `Repository not found` | Wrong URL, or no read access |

**Never put a credential in a URL.** A URL that carries a username and a secret before the `@`
is written into the shell history, into the clone's own config file, and into the process table
where any other account on the machine can read it; it is also the form that survives a
copy-paste into a ticket. Hand the secret to a credential store instead, so it is never an
argument.

**HTTPS with a Personal Access Token (PAT):**

Ask the user to generate a PAT with read-only repo access:
- **GitHub**: Settings → Developer settings → Personal access tokens → `repo` scope
- **Bitbucket**: Personal settings → App passwords → `Repositories: Read`
- **GitLab**: User settings → Access Tokens → `read_repository`

Then have them store it once and retry the clone from 1b unchanged:
```bash
gh auth login                                      # GitHub: stores it in the gh keyring
git config --global credential.helper osxkeychain  # any host, macOS
# git config --global credential.helper libsecret  # any host, Linux
```

After `gh auth login`, `gh repo clone` needs nothing further. For the credential-helper route the
first clone prompts once for the username and the PAT and the helper remembers both.

**SSH key:**

Check for existing keys and guide the user to add one if needed:
```bash
ls ~/.ssh/id_*.pub 2>/dev/null || echo "No SSH keys found."
```

### 1d. Read the digest

```bash
cat /tmp/purlin-qa-digest/.purlin/report-data.js
```

If the file doesn't exist, tell the user: "This repo doesn't have a Purlin digest. The development team needs to run `purlin:init --digest` and commit."

### 1e. Clean up

```bash
rm -rf /tmp/purlin-qa-digest
```

## Step 2 — Parse the Digest

The digest is a JavaScript variable assignment: `const PURLIN_DATA = {...};`. Strip the prefix and trailing semicolon to get JSON. The data contains:

| Field | What it means |
|-------|---------------|
| `timestamp` | When this digest was generated (ISO 8601) |
| `git_sha` | The commit this data was generated against |
| `summary` | Feature counts: total, verified, passing, partial, failing, untested |
| `features[]` | Array of every feature and anchor with rules, proofs, status, audit data |
| `audit_summary` | Overall proof quality. Report `weighted` and `assessed` separately, never one as the other: `assessed` is the score over the proofs that were actually graded, `weighted` counts every ungraded proof against the score. A project with three graded proofs out of ninety can show `assessed` 100 and `weighted` 3, and only the pair says which. Report `audit_summary.coverage` as `measured` of `total` beside them, so the reader sees how much of the project the score rests on, plus the strong/weak/hollow counts |
| `audit_summary.auditors` | Who or what produced the assessments, when present. Absent on digests written before auditor identity was recorded, so read it defensively and say "not recorded" rather than inventing one |
| `drift` | What changed since last verification: commits, files, spec changes |
| `anchors_summary` | Anchor counts: total, with external source, global |
| `platform_testing` | True when some proof declares a platform it must be proved on |
| `platforms` | `registry`, `host`, `host_id`, `local`, `remote`, `errors` and `summary`, one summary row per declared platform with its feature counts, proof counts, per-platform Proof Integrity and when it was last proved |
| `summary.held_by_platform` | Features that would read VERIFIED but for a platform that has not run. `summary.verified_here` is the count with no platform in the picture |

**`uncommitted`**: report it whenever it is non-empty, naming the files. The old advice was to
disregard the field, on the reasoning that a pre-commit hook wrote the digest, so everything must
have been committed. That reasoning does not hold. A non-empty `uncommitted` in a committed digest means one
of exactly three things, and each is worth a line in the report:

1. The project's `digest` config is set to `warn` or `off`, so the hook did not refuse the commit.
2. The commit was made with `PURLIN_SKIP_DIGEST=1`, which bypasses the hook.
3. The pre-commit hook hit one of its fail-open paths (no Python, no server, an unreadable
   config) and let the commit through rather than blocking it.

In all three the digest describes a tree that is not the committed tree, so every count in it may
be stale. Say which files, and say that the numbers below them are measured against a tree that
differs from the commit.

Each feature has:
- `status`: VERIFIED (all rules proved on every declared platform and a receipt matches), PASSING (every rule proved, and either no current receipt or a declared platform that has not run), PARTIAL (some rules proved, none failing), FAILING (a proof failed), UNTESTED (no proofs). A receipt is a record that tests ran, not an approval by a person. Never describe a feature, a release or a project as approved, cleared or compliant on the strength of one
- `rules[]`: Each rule has `id`, `description`, `status` (PASS/FAIL/NONE), and `proofs[]`
- `audit`: Per-feature integrity score and proof-level assessments (STRONG/WEAK/HOLLOW)
- `type`: "feature" or "anchor" (cross-cutting constraint like security policy)
- `platforms`: one record per platform the feature's proofs declare, each with `declared`, `proved`, `failed`, `awaiting`, a `status` of FAILING, AWAITING, PASSING or VERIFIED, `receipted`, and the commit and runner that proved it
- `platform_complete`: false when a declared platform has no result. This is what holds an otherwise complete feature at PASSING
- `awaiting_runner[]`: `{id, tier, platform}` for every proof waiting on a platform
- `vhash`: the verification hash of the feature's current rules and proofs, or null when the
  feature is not fully proved. Report it next to the receipt: the pair is what makes a VERIFIED
  claim checkable by someone who did not run the tests
- `receipt.vhash_version`: the hash format the receipt was issued under. A receipt at version 1
  predates the current formula, so its `stale` flag says nothing about the code; report it as
  "issued under an older hash format, re-verify to compare"
- `receipt.test_run_commit`: the commit whose test run the receipt rests on. When it differs from
  `git_sha`, the receipt was issued against code that is no longer the tip; report both shas
- `evidence_stale`: true when the proof files behind the receipt are older than the code they
  cover. Recent digests carry it; older ones do not, so read it defensively and omit the line
  rather than reporting false

Report `git_sha` in the header of every report. It is the commit every number in the digest was
measured against, and without it the report cannot be tied back to a state of the repository.

## Triage Priority

Analyze the digest in this order. Skip any section that has zero items.

### 1. BROKEN — Features with FAILING status
These are actively broken. Extract the specific rules with FAIL status and their proof details (test file, test name). This is the only true blocker.

### 2. CHANGED WITHOUT COVERAGE — Drift blind spots
From `drift.files`, find entries with category `CHANGED_BEHAVIOR` or `NEW_BEHAVIOR`. Cross-reference with `drift.proof_status` — if the associated feature is PARTIAL or UNTESTED, the changed code has no test coverage. Also check `drift.drift_flags` for features with only structural proofs (grep/file-exists checks) whose code changed.

This is the highest-value QA insight: code shipped that nobody verified.

### 3. SUSPICIOUS TESTS — HOLLOW proofs
From each feature's `audit` data (or `audit_summary`), identify proofs rated HOLLOW. These are tests that exist but assert nothing meaningful — they create false confidence. Show the proof description and what makes it hollow if available.

If `audit_summary` is null, note: "No audit data available — run purlin:audit for proof quality assessment."

### 4. MANUAL TESTS
This section always appears if any manual proofs exist — it is not skipped even when all stamps are current. Scan all features for proofs with `@manual` stamps in the spec's `## Proof` section. For each manual proof, show:

- Feature name and rule description (what behavior is being verified)
- Who verified it, when, and at what commit (`@manual(email, date, sha)`)
- Whether it's **current** (no code changes to the feature since the stamp) or **stale** (drift shows changed files for this feature since the stamp date)

Group into two subsections: **Stale** (needs re-verification — code changed since last manual check) and **Current** (verified and up to date). Stale items come first.

If no manual proofs exist at all, skip this section.

### 5. COVERAGE GAPS — PARTIAL and UNTESTED features
List features that are PARTIAL (some rules have no proofs) or UNTESTED (no proofs at all). For PARTIAL features, list the specific rules with NONE status — these are the gaps.

### 6. EXTERNAL POLICY DRIFT
From `drift.external_anchor_drift`, list any anchors with `status: "stale"`. These are security/compliance policies that updated upstream but haven't been synced. Flag the anchor name, what it enforces, and the pin mismatch.

### 7. PLATFORM GAPS
Only when `platform_testing` is true. For each feature with a non-empty `awaiting_runner`, name
the platform, the proof ids and the rules they cover. Report these as a gap in evidence and never
as a failure: an awaiting proof warns and never blocks, its rule leaves the coverage denominator
rather than failing, and `purlin:test` dispatches a runner for it. Say what is true and no more:
the feature is not verified on that platform. Use `platforms.summary` for the roll-up, so the
report states how many features each platform covers and how many it has proved.

### 8. READY FOR VERIFICATION
List PASSING features whose `platform_complete` is true and that have no current receipt: these
need a `purlin:verify` run. Exclude every feature held at PASSING only because a declared
platform has not run, and list those under Platform Gaps instead: they have nothing left to do
here, and reporting them as ready would ask for a verification that cannot change their status.

## Output Format

Write a complete HTML file into the current project directory and open it in the browser. Do NOT put HTML in the chat — the chat gets a text summary only.

### Step 1: Determine the file path

The filename uses the format `YYMMDD-<projectname>-qa-report.html` where:
- `YYMMDD` is today's date (e.g., `260414` for April 14, 2026)
- `<projectname>` is the `project` field from the digest (lowercase, hyphens for spaces)

Write the file into the project's working directory (the directory the Claude Code session is running in).

```bash
# Example: writing to project directory
cat > 260414-payments-qa-report.html << 'HTMLEOF'
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>QA Report: {project}</title></head>
<body>
  <!-- full report content here -->
</body>
</html>
HTMLEOF
```

### Step 2: Open it in the browser

```bash
open 260414-payments-qa-report.html    # macOS
# xdg-open 260414-payments-qa-report.html  # Linux
```

### Step 3: Print a text summary to chat

After writing and opening the file, print a brief summary to the chat (3-5 lines max). Example:

> **QA Report: payments** (digest from 2 hours ago, commit abc1234)
>
> No failures. 2 features have code changes without updated tests. 5 tests flagged as suspicious. 4 manual tests (2 stale). 3 features ready for verification.
>
> Full report: `260414-payments-qa-report.html`

### HTML structure guide

The HTML file should contain these sections. Skip any section that has zero items, EXCEPT Manual Tests which always appears when manual proofs exist.

- **Header**: project name, git SHA, and a **Data Sources** block showing when each data source was last updated. Display all timestamps in the user's local timezone (convert from UTC). The three sources are:

  | Source | Timestamp field | What it tells you |
  |--------|----------------|-------------------|
  | Coverage (status) | `timestamp` | When the coverage scan ran — this is the digest generation time |
  | Audit | `audit_summary.last_audit` | When proof quality was last assessed. May be days older than status. Show "not available" if `audit_summary` is null. Beside it print `weighted`% and `assessed`% as two numbers, `audit_summary.coverage.measured` of `.total` measured, and `audit_summary.auditors` when the digest carries it |
  | Drift | `drift.since` | The anchor point drift is measured from (e.g., "last verification (6 days ago)") |

  Format example in the header:
  ```
  Data freshness:
    Coverage: Apr 14, 2026 2:52 PM EDT
    Audit:    Apr 10, 2026 8:05 AM EDT (4 days ago)
    Drift:    since last verification (6 days ago)
  ```

  If audit is significantly older than coverage (>24h), highlight it in amber — audit scores may not reflect recent changes. If audit is null, highlight in red.

- **Freshness warning**: if the digest `timestamp` is more than 24 hours old, show a warning banner: "This digest is {age} old. Ask the team to commit to refresh it."
- **Uncommitted-tree warning**: if `uncommitted` is non-empty, show a banner naming the files and
  the three ways it can be non-empty (Step 2), because every count below it was measured against a
  tree that differs from the commit
- **Summary bar**: colored cards showing VERIFIED / PASSING / PARTIAL / FAILING / UNTESTED counts, plus integrity % if audit data exists
- **Red section (Broken)**: FAILING features with specific rule descriptions and test file paths
- **Orange section (Changed Without Coverage)**: drift items where code changed but tests are missing
- **Yellow section (Suspicious Tests)**: tests that exist but don't verify the behavior, with descriptions of what's wrong
- **Purple section (Manual Tests)**: all manual proofs grouped into Stale (needs re-check) and Current subsections, showing who verified, when, and what behavior
- **Blue section (Coverage Gaps)**: PARTIAL and UNTESTED features with the specific rules that need tests
- **Green section (Ready for Verification)**: PASSING features with every declared platform proved, awaiting a verification run
- **Footer**: Purlin version, digest timestamp, `git_sha`, and for each VERIFIED feature its
  `vhash`, its receipt's `vhash_version` and `test_run_commit`, and `evidence_stale` when the
  digest carries it. These are what let a reader check the claim instead of trusting the badge

### Theme

The QA report must match the Purlin dashboard's dark theme. Before generating the HTML, read the CSS variables from the project's `scripts/report/purlin-report.html` (it was cloned in Step 1 — expand the sparse checkout to include it if needed: `git sparse-checkout add scripts/report`). Extract the `:root` and `[data-theme="dark"]` CSS blocks and use them in the generated HTML.

The dark theme defaults (use these if the dashboard file is unavailable):

```css
:root {
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-mono: "SF Mono", "Fira Code", "Cascadia Code", "JetBrains Mono", Consolas, monospace;
  --green: #22c55e;
  --green-dim: rgba(34, 197, 94, 0.15);
  --amber: #f59e0b;
  --amber-dim: rgba(245, 158, 11, 0.15);
  --red: #ef4444;
  --red-dim: rgba(239, 68, 68, 0.15);
  --blue: #3b82f6;
  --blue-dim: rgba(59, 130, 246, 0.15);
  --teal: #2dd4bf;
}
body {
  background: #0f172a;
  color: #e2e8f0;
}
```

Apply the dark theme by default (`data-theme="dark"` on `<html>`). Use the dashboard's card background (`#1e293b`) for section cards and summary cards. Use the dashboard's border color (`#334155`) for borders. Use the dashboard's secondary text color (`#94a3b8`) for muted text.

Section border colors: red (`--red`), orange (#f97316), yellow (`--amber`), purple (#a855f7), blue (`--blue`), green (`--green`). Section card backgrounds should use a subtle tinted version of the card background, not white.

## Rules for the Report

1. **Skip empty sections.** If nothing is FAILING, don't show the red section at all. The user should only see sections that need attention. Exception: the Manual Tests section always appears when manual proofs exist, even if all stamps are current.

2. **Be specific.** Don't say "feature X is PARTIAL." Say "feature X: RULE-3 (rate limiting returns 429) and RULE-7 (timeout after 30s) have no tests."

3. **Show next actions.** Each section should end with what QA should do: "Ask engineering to fix these tests" / "Run manual verification for these features" / "Run purlin:verify to issue receipts."

4. **Freshness first.** If the digest is more than 24 hours old, show a warning banner at the top: "This digest is {age} old. Ask the team to commit to refresh it."

5. **Anchors are special.** Security and compliance anchors with stale external references should always surface — even if all their rules pass. A stale pin means the rules themselves may be outdated.

6. **Counts in headers.** Every section header includes the count so QA can gauge scope at a glance.

7. **Claim only what the data says.** The report describes test evidence and nothing else. No
   field in the digest records a human judgment, so the report never declares a project
   compliant, approved, cleared or certified, and never states a compliance verdict of any kind:
   a receipt records that tests ran, not that a person accepted the result. Report VERIFIED as
   "all rules proved on every declared platform and a receipt matches" and let the reader draw
   the conclusion.

8. **No jargon.** Don't say "HOLLOW proof" — say "test exists but doesn't verify the behavior." Don't say "drift flag" — say "code changed since last verification." Translate Purlin concepts into QA language.

## Example Interactions

**User:** "QA status for https://github.com/acme/payments"

You fetch `.purlin/report-data.js` from `main`, parse it, and respond with a brief text summary followed by the HTML artifact: "3 features are ready for verification. No failures. 2 features have code changes without updated tests — those are your priority. Proof quality is at 84% but 5 tests are suspicious."

**User:** "Same repo but check the release/2.0 branch"

You fetch from `release/2.0` instead and produce a fresh report.

**User:** "Compare main to release/2.0"

You fetch both digests and highlight differences: new features, status changes, coverage regressions.

**User:** "Tell me more about the suspicious tests"

A focused breakdown of just the HOLLOW proofs — what each test claims to do, why the audit flagged it, and what a real test would look like.

**User:** "What do I need to manually verify?"

Just the manual proof section — features with @manual stamps, whether they're current or stale, and the specific behavior to verify.

**User:** "Is the security policy enforced?"

Filter to anchors with type `security`. Show their rules, proof status, and whether the external reference is current or stale.
