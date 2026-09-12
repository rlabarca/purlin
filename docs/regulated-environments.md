# Purlin in Regulated Environments

## What You Need to Know

Purlin is a development tool, not a compliance system. It writes structured artifacts that your
QMS or compliance pipeline can read: specs, proof files and verification receipts. It does not
replace either.

What Purlin provides is machine-readable evidence that named rules were proved by named tests at
a named commit. What it does not provide is legally binding signatures, tamper-proof audit
trails or document control.

Purlin does not satisfy FDA 21 CFR Part 11, HIPAA, SOC2 or any similar framework on its own.
What it gives your compliance infrastructure is something concrete to validate. Not "tests
passed", but "these rules were proved by these tests at this commit". Every statement below
names the mechanism behind it, so a validation record can cite the mechanism rather than the
claim. The commands are the ones in [references/purlin_commands.md](../references/purlin_commands.md);
`purlin:verify` is the only one that issues a receipt.

---

## What Purlin Is NOT

- **Not a QMS.** Purlin does not manage document control, change control or approval workflows.
- **Not a signature system.** `@manual` stamps and `git config user.email` are developer conveniences, not legally binding electronic signatures. GPG-signed commits prove key possession, not identity or intent. Nothing Purlin issues is signed verification: the `vhash` is a change detector, not a token, and no key is involved anywhere in it.
- **Not tamper-evident.** Everything Purlin produces lives in the git repository, which is mutable. `git push --force` can erase any receipt, and a receipt rewritten in place reads exactly like one that was earned.
- **Not an audit trail.** Git history is a development log, not an immutable compliance record.
- **Not a test quality gate.** Purlin proves that a test executed and passed. It does not prove
  that the test contains meaningful assertions. An agent can write `assert True` and produce a
  valid proof. The two quality gauges measure exactly that and are worth recording in your QMS
  evidence, but both are advisory: neither blocks a receipt. `purlin:audit` reports them, and
  nothing reads them as a gate. A regulated team still enforces independent human review of test
  logic, through CODEOWNERS or a QMS-managed review, before accepting any proof artifact.

---

## What Purlin Produces

| Artifact | Location | What it holds | How compliance uses it |
|---|---|---|---|
| **Spec files** | `specs/<category>/<name>.md` | Numbered rules (`RULE-N`) defining required behaviour | Input to a requirements traceability matrix |
| **Proof files** | `specs/<category>/<name>.proofs-*.json` | Test results linked to rules, one file per tier and platform | Evidence of verification, read by the QMS |
| **Verification receipts** | `specs/<category>/<name>.receipt.json`, plus the `verify: [Complete:all] vhash=...` commit | The rules, proofs, manual stamps and run evidence behind one feature at one commit | The primary machine-readable artifact; the commit message gives the ledger a timeline |
| **Manual proof stamps** | `@manual(email, date, sha)` in the spec | The record that a named person checked a rule on a named day | A starting point. The QMS must re-authenticate and countersign |
| **Anchor files** | `specs/_anchors/*.md` | External constraints with a `> Pinned:` version | Source-of-truth tracking for external standards |
| **Run marker** | `.purlin/runtime/test_run.json` | What ran, when, at which commit, and what it skipped | Proof that the evidence came from an observed run |

These are inputs to your compliance pipeline, not the pipeline itself. The receipt shape is a
versioned contract: `references/formats/receipt_format.md` carries a `Format-Version:` line and
the receipt carries `vhash_version`, currently `2`. Pin the version you validated against and
re-read that file when it moves.

---

## The Two Gauges, and What Each Pass Does

`purlin:audit` measures two separate things and says which mode it chose.

**Proof Design** (`purlin:audit --design`) asks whether the claim is provable. It reads the rule
and the proof description, never any test code, and grades each description PROVABLE, LOOSE,
UNPROVABLE or STRUCTURAL. Be exact about which half is reproducible.
Pass D1 is deterministic; Pass D2 is an LLM pass. D1 is the grep-and-parse grading in
`scripts/audit/static_checks.py --check-proof-design`, reproducible on any machine with no model
call. D2 is the judgement about whether the description matches the rule, which is a model
reading prose.

**Proof Integrity** (`purlin:audit`) asks whether the claim is proven. It reads test code. Pass 1
is deterministic static analysis in `scripts/audit/static_checks.py`: `assert True`, no
assertions, logic mirroring, mocking the thing under test, a bare `except: pass`. Any Pass 1
failure is HOLLOW and cannot be overridden. Pass 2 is the LLM pass that classifies each proof as
structural or behavioural and then judges semantic alignment, returning STRONG, WEAK or EXCLUDED.

Both gauges are cached, and the cache is the part a regulated reader has to trust. A grade is
keyed by `resolve_proof_inputs`, which reads the rule text, the proof description and the graded
test function's source out of the project, together with the proof's own `<feature>\0<proof_id>`
identity (`static_checks` RULE-38). The writer discards whatever key a caller supplied and
re-keys every entry through that one function, so a stored key always describes project state
rather than text a caller pasted. Editing one character inside the graded test function changes
the key; editing a different function in the same file does not (`static_checks` RULE-40). Every
stored entry carries `auditor` as `{name, command}`, read from `.purlin/config.json` at write
time, so a reader can see that a whole gauge came from one tool (`static_checks` RULE-39).

---

## Where a Result Comes From

A proof entry says a test passed. The run marker says a run happened.

Every proof plugin writes or merges `.purlin/runtime/test_run.json` at the moment it writes its
proof files (`proof_common` RULE-19), so a consumer project with no sweep script of its own still
issues receipts that name a run. The marker records `at`, `commit`, `sweep` (the writer's name,
such as `pytest_purlin`, or `dev/run_tests.sh` for this repository's own sweep), the files the run collected, the counts, `ok`, and one
entry per contributing run. Runs at the same commit merge; a different commit starts a new
marker, because a count carried across commits would describe two trees. The issuer copies it
into the receipt as `evidence.test_run`, and a receipt issued with no marker carries
`evidence.test_run: null`, which means the receipt records proof files rather than an observed
run.

The receipt also records which proof file each entry came from, the commit that last wrote it and
whether the recorded run executed it. A file that no recorded run executed and no runner
committed is evidence with no witness, and the issuer refuses the feature rather than writing a
receipt over it.

Two staleness signals sit beside that. A counted `@manual` stamp stops counting the moment one
commit touches a path in the spec's `> Scope:`, and the rule reads `MANUAL PROOF STALE`
(`sync_status` RULE-5). Every counted stamp also enters the verification hash, so re-stamping
with a new email, date or commit moves the feature's `vhash` and stales the receipt issued
against the old stamp (`sync_status` RULE-59). Separately, a VERIFIED feature whose scope has
been committed to since the tests behind its receipt ran prints `EVIDENCE OLDER THAN CODE` with
the number of commits and the run's commit (`sync_status` RULE-60). It warns and never blocks,
and the payload carries it for the dashboard to render.

---

## Where a Result Was Produced

A proof can depend on three different things, and each has its own mechanism. The rule set has a
single home, [references/remote_verification.md](../references/remote_verification.md), section
"Platforms, environments and prerequisites", which carries the question that decides which one an
id is. What matters for a validation record is what each mechanism records.

A **platform** is an entry in the `platforms` registry in `.purlin/config.json` with an `os`. A
proof tagged `@on(<id>)` is evidence only when it was observed there. `purlin:test` runs the
suite locally with `PURLIN_PLATFORM=<id>` when the host satisfies the id, and otherwise
dispatches the entry's runner and pulls back what the runner committed. Provenance is read from
the commit, not from the entry: `sync_status` reads the `Purlin-Runner:` trailer for the runner
identity and the `Purlin-Platform:` trailer for the platform the runner was told it was, and says
`trailer says <id>` when the filename and the trailer disagree. A proof with no result on its
platform reads `AWAITING RUNNER`, leaves the coverage denominator rather than failing, and the
receipt that is still issued records the gap as platform-partial.

An **environment** is a registry entry with `kind: "environment"` and no `os`, such as
`figma-mcp`. Nothing a machine reports about itself can show that an MCP server or a CLI answers
there, so an environment is satisfied only by a person or a runner setting `PURLIN_PLATFORM` to
that id by hand and committing the result with a `Purlin-Runner:` trailer. Every surface calls it
an environment and the awaiting state reads "awaiting an environment run".

A **prerequisite** is a toolchain the run needs in order to execute, such as php or dotnet. It is
never registered and never appears in `@on(...)`. The committed proof entry is kept rather than
deleted when a marked test is skipped (`proof_common` RULE-18), and the run marker records every
such skip under `skipped_proofs` as `{feature, id, test_file, test_name, reason}`, which the
receipt carries in `evidence.test_run`. The report then shows the entry as inherited from the
commit that last proved it, with the reason, rather than as fresh.

---

## Enforcement Layers

Purlin's one gate is the coverage check inside `purlin:verify`; the pre-push hook, your own CI
test run and the required CI gate job `scripts/ci/verify_gate.py --check` are the layers above
it, each described once in [references/hard_gates.md](../references/hard_gates.md), "Enforcement
Layers". For a regulated environment no layer there is sufficient alone, because every one of
them proves that tests ran and passed and none proves that the tests are meaningful, so your QMS
verifies test quality independently.

---

## Keeping the Installation Qualified

Three mechanisms decide what a validated workstation actually runs.

`scripts/init/scaffold.py` is the deterministic half of `purlin:init`. The skill asks the
questions; the script writes `.purlin/config.json`, copies the selected plugin from
`scripts/proof/` byte for byte, writes the runner wiring and the git hooks, and prints one line
per path it wrote, kept, copied or linked. It never writes a proof entry, never writes a receipt
and never commits.

`purlin:init --update` migrates a project after the plugin moves under it. It reads what is
pending from the project's own contents rather than from the `version` field, shows the delta and
asks before writing. `scripts/update/migrate.py` owns the migration ids:
`legacy-tier-windows`, `legacy-proof-file`, `legacy-marker`, `plugin-copies-stale`,
`config-fields-missing`, `receipt-v1` and `legacy-mcp`. The first three rewrite the retired
platform tier tag, its proof files and its plugin markers to the `@on(<id>)` form.
`plugin-copies-stale` replaces each `.purlin/plugins/` copy with the installed plugin's file.
`receipt-v1` only prints a directive, because a receipt is a claim that tests ran and an update
never writes one. `purlin:init --update --check` reports what is pending and writes nothing,
which is what a CI preflight runs, so a runner never proves anything with stale plugin copies.

The git hooks are the third. The pre-push hook (`specs/hooks/pre_push_hook.md`) has three modes
set with `purlin:init --pre-push`: `warn` blocks a FAILING proof, `strict` blocks anything not
VERIFIED, and `off` prints one line saying it is off and reads nothing. Its fail path is explicit:
when it cannot resolve the plugin root it has no evidence to read, so `warn` prints a WARNING and
allows the push while `strict` exits 1, rather than reporting a pass it did not earn. Any mode
can be bypassed with `git push --no-verify`, which is why enforcement for a regulated project
lives in branch protection rather than in a hook. The pre-commit hook
(`specs/hooks/pre_commit_hook.md`) is fail-open by design: it exits 0 on every path so it can
never block a commit, and every path that gives up says so out loud, because a silent skip reads
exactly like a hook that worked. The plugin's own refresh hook
(`specs/hooks/refresh_digest_hook.md`) is registered async, runs after a tool call or a turn,
decides from file mtimes whether anything the digest reports changed, regenerates only then, and
never blocks, never prints and never reaches the network. No Claude Code hook gates anything.

---

## Mutation Checks, the Authoring Standard

A mutation check breaks the behaviour a proof covers, watches that proof fail, and restores the
code before the commit. It is the authoring twin of Proof Integrity: a proof that still passes
against broken code proves nothing, and neither a static check nor an LLM grade can see it,
because both read the test and the rule rather than running one against the other.

It is opt-in, from `mutation_checks` in `.purlin/config.json`, and `purlin:init --mutation-checks on`
turns it on. When it is on, every new or amended proof is mutation-checked before the commit that
carries it and the mutation is recorded in the commit body, so a reviewer can re-run it. The three
steps and the rule that a surviving mutation is a finding rather than a formality are in
[references/spec_quality_guide.md](../references/spec_quality_guide.md#mutation-check). For a
regulated project this is the cheapest evidence that a proof is discriminating, and it is the one
check the two gauges cannot supply.

---

## How a Regulated Pipeline Would Use Purlin

In a compliant architecture Purlin runs inside a larger system, and trust lives outside the
repository:

```
Developer or agent
    |
  Purlin (writes specs, code, tests, proof files)
    |
  Git repository (untrusted: mutable, writable by agents)
    |
  CI/CD pipeline (pulls from git, applies external policy)
    |
  External compliance infrastructure:
    - Policy vault (compliance rules, not in the repo, not editable by agents)
    - Identity provider (Okta or SAML, MFA-backed approvals)
    - QMS or compliance ledger (immutable audit trail, external to git)
    - Approved-test registry (test hashes stored outside the repo)
```

### Policy lives outside the repo

Compliance rules, required verification levels and approval requirements are enforced by the
CI/CD infrastructure, never by a config file the agent can edit. `.purlin/config.json`'s
`remote_verification` field declares which bar a project holds itself to; branch protection
marking `scripts/ci/verify_gate.py --check` a required job is what enforces it.

### Approvals come from an identity provider

Human approvals go through MFA-backed authentication, not `git config user.email` and not a GPG
key. A `@manual` stamp is coverage, not an approval.

### The audit trail lives outside git

Receipts are ingested into an immutable external ledger. Git history is a convenient view, not
the compliance record.

### Approved test hashes live outside the repo

Approved test hashes belong in the external QMS or ledger, never in a file inside the repo where
the agent can edit them. Purlin ships no such file and reads none: the registry in the diagram
above is something your compliance infrastructure owns.

---

## Integration Points (not extensions)

These are not Purlin features to switch on with a config flag. They are the interfaces where
Purlin's output meets external compliance infrastructure, and your compliance team builds and
owns them. Each names the mechanism it attaches to, starting with `purlin:init`.

### Pinned Plugin Version and Interpreter

A regulated deployment pins the plugin by tag and never installs it from a branch head. On a
workstation the thing that resolves the plugin is the marketplace entry the installation guide
documents: `claude plugin marketplace add https://github.com/rlabarca/purlin.git --scope project`
writes that entry into the project's `.claude/settings.json`, and `claude plugin marketplace update`
later moves it to whatever the default branch holds at the moment it runs, which is not a version
a change record can cite. So add the marketplace from a URL your change control holds at the
validated release tag, and read back which release is installed from the `version` field of
`.claude-plugin/plugin.json`. Neither the marketplace entry nor `plugin.json` carries a ref field
of its own, so the tag is held by your process and not by a Purlin config flag. In CI the tag is
explicit: the workflow examples install the tooling with `git clone --depth 1 --branch v<VERSION>`
and point `PURLIN_PLUGIN_ROOT` at that clone (see
[references/remote_verification.md](../references/remote_verification.md)). Both must name the
same tag, because a proof result records nothing about which plugin produced it.

A regulated deployment runs Python 3.11 or newer. That is the tested floor rather than a syntax
limit: every workflow under `.github/workflows/` pins `python-version: '3.11'`, so 3.11 is the
only interpreter this repository's proof results have been produced on.
[docs/installation-guide.md](installation-guide.md) states a lower prerequisite for everyday
development (`Python 3.8+`), which stays true there. A validated environment holds the higher
floor so that the interpreter named in the qualification record is the one the evidence came from.

### Requirements Traceability

`RULE-N` lines in specs and `PROOF-N` entries in proof files are a machine-readable traceability
matrix. A compliance tool parses `specs/**/*.md` for rules and `specs/**/*.proofs-*.json` for
results and generates the traceability documentation your QMS requires.

### Verification Evidence

Your CI pipeline can recompute the `vhash` and compare it against the one in the committed
receipt, to see whether the developer's local state matches what CI reads, before the CI runner
performs its own clean-room run. The local `vhash` is evidence that the developer ran the tests.
The CI run is the evidence that the tests pass in a trusted environment. Be precise about what
the number carries; the contract is `references/formats/receipt_format.md`.

#### What the vhash binds

Version 2 of the vhash (`vhash_version: 2`; the receipt's own `Format-Version` moves independently) hashes these fields, `\x00`-separated so no value can be forged across a
boundary:

| Bound | Why it is in the hash |
|---|---|
| The **rule text** of every active rule, whitespace-normalised | Rewording a rule after it was proved changes the hash, so the receipt goes stale instead of silently covering the new wording |
| The **feature** each proof belongs to | `PROOF-1` under an anchor and `PROOF-1` under a feature are different claims |
| The **proof id** and the **rule** it proves | Re-pointing a proof at a different rule changes the hash |
| The proof's **status** | A `fail` that later reads `pass` is a different receipt |
| The proof's **tier** | A rule proved only at `unit` is not one proved at `e2e` |
| The proof's **platform** | A result from `windows-2022` and one from `macos-14` are separate evidence, and an `@on` proof binds the platform it was proved on |
| The proof's **test file** and **test name** | Pointing a proof at a different test changes the hash, so the receipt names the test it was earned by |
| Every counted **manual stamp**: feature, proof id, rule, email, date and commit | A stamp that moves, changes hands or is re-dated changes the hash |

#### What it does not bind

| Not bound | Consequence |
|---|---|
| The **content of the test code** | The named test can be rewritten to `assert True` and the hash does not move. Only the two quality gauges and human review look inside a test |
| **Who ran it** | The receipt records a git author and a `Purlin-Runner:` trailer where a runner committed one. Neither is authenticated |
| **When it ran** | The receipt carries a timestamp the machine that wrote it supplied |
| **That the test is meaningful** | See "Not a test quality gate" above. A passing proof is a claim about execution, never about relevance |
| **The runner's honesty** | A remote result is trusted because the workflow file and the branch protection around it are trusted, not because anything in the receipt proves where the bytes came from |

A vhash is a change detector. It answers "is this receipt still about the code and rules in front
of me?" and nothing else. The run marker beside it, `evidence.test_run`, is what says a run
happened at all.

### Human Approval Workflow

When `@manual` stamps are required, the compliant flow is:

1. Purlin flags the rule as needing manual verification (`purlin:status` shows `MANUAL PROOF NEEDED`)
2. The human performs the verification
3. Instead of `purlin:verify --manual`, which only writes a markdown stamp, the human approves
   through the QMS, which authenticates with MFA, records intent and issues an approval token
4. The QMS or the CI pipeline injects that token into the spec file or a locked artifact, which
   Purlin reads to satisfy the coverage check, stopping the `MANUAL PROOF NEEDED` directives
5. CI validates the QMS token before accepting the manual proof

Be precise about what a `@manual` stamp is worth on its own. It counts toward coverage
(`sync_status` RULE-5) and it enters the verification hash (`sync_status` RULE-59), so it is
tracked. It records that the named person said they checked the rule on the named day, against
the code as it stood at the named commit, and it stops counting the moment a commit touches the
spec's `> Scope:`. Nothing authenticates the name, so the stamp is an audit trail entry rather
than an approval. The QMS token in step 4 is what carries authentication and intent.

### Proof Quality Auditing

For a regulated team, additional audit criteria can be appended from a compliance-controlled
repository. Built-in criteria always apply, and additional criteria only add stricter checks:

```json
{
  "audit_criteria": "git@github.com:acme/compliance-qa-standards.git#audit_criteria.md",
  "audit_criteria_pinned": "a1b2c3d4"
}
```

The compliance team owns and versions that file. Developers cannot weaken the standards that
judge their tests. `purlin:init --sync-audit-criteria` pulls updates and writes the commit it read
into the cached copy as its first line, `<!-- purlin-criteria-sha: <sha> -->`.

The pin is enforced rather than recorded. `load_criteria` in `scripts/audit/static_checks.py`
reads that header on every audit and compares it to `audit_criteria_pinned`; a missing cache, a
missing header or a different commit raises an error naming what was found and what was pinned,
and the audit stops (`static_checks` RULE-41). There is no fall back to the built-in criteria,
because a project graded against a standard it did not pin reads exactly like one graded
correctly.

For teams worried about shared-model bias, Purlin experimentally supports cross-model auditing:
configure Gemini, GPT or any CLI-accessible LLM as the auditor while Claude remains the
implementer, so the auditor's biases are independent from the builder's. The feature is
experimental, because external LLM response formats vary.

```json
{ "audit_llm": "gemini -m pro -p \"{prompt}\"", "audit_llm_name": "Gemini Pro" }
```

`audit_llm` is executable configuration, not a label: it is the command the audit shells out to,
so the compliance team pins it the same way it pins the criteria file. `audit_llm_name` is the
name stamped on every grade the audit writes, it reaches every cache entry as `auditor`
(`static_checks` RULE-39), and it appears in the digest as `audit_summary.auditors` with a count,
so a reader can see that a whole gauge came from one tool. `purlin:status` warns, and never
blocks, when the configured command is not on PATH, when it carries no `{prompt}` placeholder, or
when a name is configured with no command.

Cross-model auditing is an improvement over same-model auditing, but both are LLM judgment.
Neither replaces human code review for critical systems. In a regulated environment a human
reviews the audit report as part of QA, rather than treating it as a final authority.

### External Anchor Validation

An anchor's `> Pinned:` SHA records which version of an external standard is in use. Your CI
pipeline compares that SHA against the authoritative source with `purlin:anchor sync --check-only`
and fails the build when an anchor is behind. That is enforced by CI policy, not by Purlin config.

---

## The Bottom Line

Purlin's rule-proof model is a good foundation for regulated development, because it produces the
structured artifacts a compliance system needs. The trust boundary has to sit outside the
repository. `purlin:verify` is the compiler. Your QMS, identity provider and CI/CD infrastructure
are the compliance system.

Talk to your compliance team about reading Purlin's output into your existing quality management
infrastructure.
