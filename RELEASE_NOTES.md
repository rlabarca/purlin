# Release Notes

## Unreleased — 0.10.0

For a project running 0.9.5. One command moves it forward, and the rest of this page says what
that command changes.

0.10.0 replaces two grading scores and one ladder of seven states with three evidence levels, moves the evidence into the repository, and gives each level one command. The
whole loop runs on one machine, at every gate: nothing needs a new service, a hosted anything or
a setting on the git host. The evidence is files in git, and the marker that a version met the
gate is a signed tag a person pushes.

### What a 0.9.5 user does

```
purlin:init --update
```

The update reads what the project actually contains rather than its `version` field, shows the
list of changes, and asks before each one. Every file it rewrites is backed up beside the
original as `<name>.local-<sha8>.bak`, and one commit carries the whole run.
`purlin:init --update --check` prints the pending list and writes nothing, which is what a
preflight runs. Until the update runs, every skill opens with `→ Run: purlin:init --update`.

What it does to a 0.9.5 project, step by step:

- **Design references.** 0.9.5 let a spec point at a Figma file and carry a picture's
  fingerprint. The update deletes each spec's `> Visual-Reference:` and `> Visual-Hash:` lines,
  a `> Source:` that names Figma and the `> Pinned:` timestamp that goes with it, and prints one
  line per spec naming what it removed. A git `> Source:` and its `> Pinned:` stay.
- **Tags on proof lines.** A trailing `@windows` becomes `@env(windows)`, and the kind of test
  (`@unit`, `@integration`, `@e2e`) is dropped: `purlin:test` runs every tagged test.
- **Files beside the specs.** The run files and the proof files 0.9.5 committed beside each spec
  are untracked and deleted. The committed dashboard data and the cache are untracked, left on
  disk and added to `.gitignore`.
- **Git hooks.** The pre-commit and pre-push hooks 0.9.5 installed are removed. Nothing runs at
  commit time or at push time. A hook another tool wrote is left alone.
- **Settings.** `.purlin/config.json` is rewritten with `version`, `gate`, `mutation_engine`,
  `min_strength`, `audit_parallel` (4), `tests`, `ci` and `trust`. Every key 0.9.5 wrote that
  this release does not read is dropped and named in one line: `spec_dir`, `pre_push`,
  `report`, `digest`, `sql_engine`, `audit_criteria`, `audit_criteria_pinned`, `audit_llm` and
  `audit_llm_name`, whichever the file carried. `test_framework` becomes `tests`: one entry per
  framework it named, each running your own test command with the flag that writes a report
  (xunit becomes `dotnet`, run as `dotnet test --logger trx`). A framework the tree cannot run
  is dropped and named.
- **Three questions.** The gate question, defaulting to `strong` where `pre_push` was `strict`
  and to `passed` otherwise. The mutation question, `Measure test strength by breaking the code
  on purpose?`, asked only where an engine exists for the project's frameworks, defaulting to
  no: 0.9.5 had no such setting. A yes writes `mutation_engine: auto` and the gate's
  `min_strength` and says to run `purlin:init` to wire the engine. The trust question,
  defaulting to yes.
- **The evidence folder.** `.purlin/evidence/` is created with one README saying what the
  folder holds. Every run writes its evidence there from now on.
- **Workflows.** The workflow that committed Windows proof files is removed. One `purlin.yml`
  is offered in its place only where a spec names another operating system or you answered no
  to the trust question.
- **Markers become comments.** Every marker a 0.9.5 plugin read becomes one comment above the
  same test, in the file's own comment syntax: `# purlin: login PROOF-1` above a pytest test,
  `// purlin: login PROOF-1` above a Jest, Vitest or C# test, `-- purlin: login PROOF-1` in a
  SQL file. The pytest decorator, the tag in a Jest or Vitest title, the xUnit trait and the
  SQL comment are rewritten in place; a shell script's harness calls become comments at its
  top and the calls themselves no-ops. One line per file says how many it rewrote. A shell or
  SQL test file is now one test that passes when it exits 0, so a script that recorded a
  failure through the harness must now exit non-zero. A module-wide `pytestmark` is named by
  file and line and left for you to move.
- **The plugins go.** No plugin is installed in your tests any more: Purlin runs your own test
  command and reads the report it writes, JUnit XML, the TRX `dotnet test` writes or the JSON
  `go test -json` writes. The update removes the plugin copies 0.9.5 put under `.purlin/`, the
  `pytest_plugins` line it wrote into `conftest.py`, and the reporter it added to
  `jest.config.js`, `vitest.config.ts` or `package.json`. A `.csproj` that compiles the xUnit
  logger is named for you to edit by hand. Jest needs `jest-junit` added to write its report:
  `npm install --save-dev jest-junit`.
- **Specs with no `> Scope:` line** are named, `2 specs have no > Scope: line: a, b. Run
  purlin:spec <name> to add one.`, and changed by nothing. The line is optional below `signed`
  and required at `signed`.

Nothing about a level tag, a signature or the queue is migrated: 0.9.5 had none.

The evidence a person wrote under 0.9.5 does not carry forward. Those files bound hashes this
release computes differently, so the update drops them rather than converting them into
something nobody attested to; they stay in git history, and `purlin:sign` walks the queue
afterwards.

### What changed, by concept

**The three levels.** A rule has up to three cells, each of which reads one word and carries
its reasons. A rule no proof line names reads `no test` in its passed cell, with the reason
`no proof written`.

| Level | The question | Words the cell can read |
|-------|--------------|-------------------------|
| passed | did every tagged test for this rule pass? | `passed`, `partial`, `failed`, `no test`, `not run`, `out of date` |
| strong | are those tests worth trusting? | `strong`, `weak`, `not audited`, `manual test` |
| signed | did a person say the rule, the proof and the test belong together? | `signed`, `unsigned`, `stale` |

A cell exists only at or below the project's gate. Above the gate it is absent, not empty, which
is why raising the gate is what makes a column, a tile or a filter appear.

**The gate.** One project setting, `gate` in `.purlin/config.json`, with three values named for
the word the last cell reads when it is met: `passed`, `strong` and `signed`. `purlin:init` asks
one question about it, **what must be true of every rule before a version is proven?**, and an
unmarked rule takes the gate as its level. Mutation testing is a question of its own, asked only
where an engine exists and off by default; with it on, `min_strength` is null, 70 and 80 at the
three gates.
`purlin:init --gate <value>` changes it later; raising adds what is missing, lowering deletes
nothing.

**The whole loop runs on one machine.** `purlin:spec`, `purlin:build`, `purlin:test`,
`purlin:audit`, `purlin:sign`, `git push`. A project at `signed` on one laptop with no CI
anywhere is the ordinary case, at every gate. Evidence counts whoever wrote it.

**Three commands, one per level.** `purlin:test` runs the tagged tests and writes the evidence.
`purlin:audit` runs the tests, the breaks where mutation testing is on, then the AI audit, and
writes what it found into the same evidence. `purlin:sign` walks the queue one
rule at a time when given no rule, signs or notes a rule when given one, and closes by writing
the tag. `purlin:verify`, `purlin:review` and `purlin:approve`
are gone, not aliased.

**The tag is the marker.** When every rule meets the gate, `purlin:sign` writes the signed tag
`signed/<version>` over the commit, with the key the signer signs commits with, taking the name from the `VERSION` file or from
`--release <name>`, and prints `Run: git push origin signed/<version>`. No tag is written while
any rule falls short, or while a feature's evidence is written and not committed, so the tag
is the claim. A tag holds the whole tree, so the code, every
evidence file and every signature are pinned together under one name. `purlin:audit --tag`
and the `record/<name>` tags are gone with it, and nothing else pins the evidence.

**The evidence package.** `purlin:export` writes `.purlin/evidence/package/<version>.json`, one
data file holding every rule's words, proofs, tests, results, audit findings, signatures and
statuses, with a fingerprint of its own bytes, and `purlin:sign` commits it into the commit the
tag names. It is handed to a regulated system of record, which holds the authority to sign the
version off; Purlin makes no claim of compliance.

**A push is free.** Any branch, any time, and nothing runs when you make one. The pre-push hook
is removed and `purlin:init` installs no git hook; the rule that an agent never pushes is an
instruction in `agents/purlin.md`. No branch rule is printed and none is asked for.

**Trust.** `purlin:init` asks `Do you trust your own machine for the tests and the signing?
[y/n]` and writes `trust: local` or `trust: remote`. Under `local`, the default, this machine's
runs are the evidence from end to end. Under `remote`, `purlin:sign` refuses a rule with a test
whose feature has no current `ci` section, so `purlin:test --remote` runs first.

**A remote runner exists for two reasons and no other**: a proof is tagged `@env` for an
operating system this machine is not, or trust is `remote`. With neither, `purlin:init` writes
no workflow at any gate. Where one exists, it starts on a push of a `signed/**` tag and on a
push to a `run/*` branch, and on nothing else: no pull request run, no run on a branch, no
comment and no dashboard artifact. The job is named `purlin`. The tag run reruns the tagged
tests on a clean machine, recomputes every committed signature against the tagged code, checks
that every file under `.purlin/evidence/ci/` was committed by the runner's own identity, and
ends with the gate check. No breaks and no AI audit run on a runner.

**Evidence.** Every run writes `.purlin/evidence/<source>/<feature>.json`, one file per
feature per source: one section per operating system with each proof's result, the commit, the
time and a fingerprint of the spec, the covered code and the tests, and once audited, the test
strength and what the audit found per rule. The folder is the source:
`.purlin/evidence/local/` is anyone's, `.purlin/evidence/ci/` is a remote runner's, and a file
whose own `source` field disagrees with its folder is ignored with a warning. Both count at
every gate.

**The table.** Every run renders `.purlin/tests.md` again from every evidence file, one row per
feature, so a teammate reads your run on the git host without running anything.

**Written, and committed when you ask.** `purlin:test` and `purlin:audit` write the evidence
and the table and commit nothing. `purlin:test --commit` and `purlin:audit --commit` commit them
as `purlin: evidence at <sha7>`, and neither ever pushes. A remote runner always commits its own
operating system's section, because its evidence exists nowhere else.

**Out of date.** A pass counts only while the section's fingerprint matches the tree. When the
spec, the covered code or the tests change, the passed cell reads `out of date`, naming what
changed, whoever made the run and whether or not it was committed; the next run clears it.

**A run covers what the change touched.** 0.9.5's `purlin:test` ran every test every time.
Now, with no feature named, it runs a feature only when that feature has no run on this
operating system, when its spec, its covered code or its tests changed since its newest run,
when an untracked file sits under its `> Scope:` or beside its tests, or when its spec names no
files. Before it runs anything it prints what it selected and why, `Selected 2 of 34 features:
login (code changed since a1b2c3d), invoice (no run on macos yet).`, and what it skipped; each
test framework is then given only the test files of those features, except `dotnet test`,
which runs its whole suite. With nothing selected it prints `Nothing to run: every feature's
spec, code and tests match its evidence. purlin:test --all runs them anyway.` and runs no test.
`purlin:test --all` runs every feature, `purlin:test <feature>` runs the ones named, and
`purlin:audit` runs its tests on the same selection. An anchor's rules count in the spec of
every feature that requires it, so editing an anchor runs those features.

**`> Scope:` is required at `signed`.** Below `signed` a spec with no `> Scope:` line, or one
that names no file that exists, has its tests run and its rules read as usual; the cost is that
Purlin cannot tell which code belongs to it, so every run includes it, and `purlin:status`
names it: `1 spec names no files, so its tests run every time: export.` At `signed`,
`purlin:sign` refuses its rules, `sign: export names no files in > Scope:, so a signature cannot
be tied to the code it governs. Run: purlin:spec export`, no tag is written, and the gate check
lists it under `Incomplete`. Anchors never need one. `purlin:spec` writes the line on every
spec it creates and `purlin:build` keeps it current in the commit that changes the code. The
tag's refusal also names each feature whose evidence is out of date, `No tag: login is out of
date (code changed since a1b2c3d).`

**Platforms.** A rule's passed cell carries one entry per operating system a counting run
covered. The cell reads `partial` when the tests passed on some and failed or did not run on
others, which is not met, and `partial` has its own tile and filter at every gate. Test strength
is platform independent.

**The AI audit.** `purlin:audit` calls the model itself: one `claude -p --output-format json`
call per rule, with the prompt on stdin, 300 seconds each, `audit_parallel` calls at once (a
setting from 1 to 16, 4 by default). Before the first call it prints
`AI audit: <n> rules to read, <k> at a time.` and carries on without asking. It reads the rules
with a passing test whose text, proof or test changed since their last audit, and skips the
rest; `purlin:audit --all` reads them again. A rule whose level is `passed` is not read under a
higher gate. The answer is recorded per rule as a `verdict`: `strong` where the model settled
and found nothing, `weak` with each finding as a sentence, and `undecided` where it could not
decide, which reads `weak` with the reason `the AI audit could not decide: <its sentence>` and is
build work. **It recommends nothing.** A finding blocks at `strong` and above. Each entry names
the model that answered and the sha256 of `references/review_criteria.md` as it was sent. Where
the model cannot be reached, nothing is written: the rule reads `not audited` with the reason
`the AI audit could not run: <why>`, the run prints one line per cause, exits 1 at `strong` and
above, and the next audit tries again. At the gate `passed` the audit reads every rule with a
passing test, writes what it found, and blocks nothing.

**The free checks are removed; the AI audit is the one judge of test quality.** Nothing scans the
proof text or the test body before the audit. `references/review_criteria.md` lists what the AI
audit looks for when it reads each proof beside the source of its test, and the audit writes what
it observed in plain sentences; an audit that settled and still observed a gap proves the rule
`weak` with that sentence as the reason. The brief's layers are `test strength` and `AI audit`.
At `passed` nothing reads test quality at all.

**A rule's level.** A rule may be marked `[level: passed]`, `[level: strong]` or
`[level: signed]`, meaning what the gate means: its tests; its tests and the audit; its tests,
the audit and a signature. A rule with no tag takes the project's gate, and the gate is the
ceiling: a mark above it is read as the gate, and `purlin:status` says how many rules carry
one. The level decides which cells block the rule, whether the AI audit runs on it, and whether
it needs a signature, which it does exactly when its level is `signed`. `purlin:spec` writes no
level tag at `passed`. `risk` and `ai_review_at` are gone.

**Signatures.** One file per signature,
`specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json`, so two signatures
never conflict. It binds the hashes of the rule text, the proof text and the test body, and
what the audit found: the strength, the `verdict` and the findings, and neither the model nor
the criteria. A re-audit that finds something different stales the signature, and the run
prints `<n> signatures went stale: their audit findings changed.` It records the rule's level and
does not lock it, so marking a rule differently stales nothing. Signing is logged, not
policed: under `signed` a signature counts when the commit that added it is signed and verifies
and its bound hashes still match, whoever signed, whoever last committed to the test file and on
whatever branch carries it. No setting names the people who may sign. Each signature records the machine it was made on
and that machine's operating system beside the signer and the time, and hashes neither. A
`--note` is the one line a signer writes for a rule reading `manual test`.
`purlin:sign` signs nothing over evidence that is written and not committed: it names the
feature and `purlin:test --commit`. A reviewer who finds the test does not prove the proof adds
the missing case as a proof line, which is the walk's `case` answer.

**No machine writes a signature file, ever.** A signature directory holds only files a person
wrote.

**One queue.** The queue is the one list of the rules that wait on a person, and each row says
what it needs: a `hand check`, a rule reading `manual test` at `strong` and above,
which a person signs with a note; or a `signature`, a rule whose level is `signed` and whose
tests and audit are met. `purlin:sign` walks it, `purlin:status` counts it as
`Queue: <n> rules. <h> hand checks, <s> signatures.`, and the dashboard shows it on its Queue
tab. A weak rule is build work and stays on the board, and so is a rule reading `not audited`.

**The gate check.** `scripts/ci/verify_gate.py` becomes `scripts/ci/gate_check.py`, its log
prefix `gate:`, its sections `Not passed (n)`, `Partial (n)`, `Weak (n)`, `Not audited (n)`,
`Queue (n)`, and its JSON key `result` in place of `verdict`.
`purlin:sign` runs it before it writes a tag, and a runner runs it as the last step of every run.

**Breaks engines.** Mutation testing is optional. Where it is on, `purlin:audit` breaks the code
on purpose at `strong` and above, for each feature with a rule it reads, and reports the share of
those breaks the tests caught as the **test strength**, an integer percent, which must also
reach `min_strength`. Three engines ship, chosen by `mutation_engine` in the config: mutmut for
Python, Stryker for JavaScript and TypeScript, and Stryker.NET for C#. With `mutation_engine`
`none`, or for SQL and Bash, which have no engine, no breaks run and a rule the audit found sound
reads `strong` with the reason `no mutation score measured`.

**`@env`.** A proof that can only be proved on one operating system carries `@env(windows)`,
`@env(macos)` or `@env(linux)`. Those three are the whole vocabulary. Where a project has a
runner, `purlin:init` reads the tags and writes a matrix to match. On a host that does not match,
the test is skipped and the passed cell reads `not run` with `<os>: no run yet`;
`purlin:test --remote` pushes a run branch, finds the run by that branch, waits on it and pulls
the evidence back.

**The dashboard.** One HTML page on the design tokens, with no framework and no build step. It
keeps the board, the tiles, the filters and the rule screen, and its tiles, columns and filters
scale with the gate. At `passed` it shows each rule's text, its tests and one status: `passed`,
`failed`, `partial`, `no test`, `not run` or `out of date`. At `strong` it adds the `Strong`
column, the audit's findings on each rule's screen and a Queue tab of the rules that wait on a
person; at `signed` it adds the `Signed` column and each signature's signer, time, machine and
operating system. A spec with no `> Scope:` line reads `<name> · no scope`. The top bar carries
the gate, the signed tag this commit holds from `strong` up, and how old the data is. It opens
from disk; nothing is published and no artifact is uploaded.

**Nothing runs in the background.** 0.9.5 rewrote the page's data after every tool call and
every turn, through a Claude Code hook. The hook and its `digest` setting are gone:
`purlin:status`, `purlin:test`, `purlin:audit` and `purlin:sign` write `.purlin/report-data.js`
as they finish, and nothing else does. An edit you make with no Purlin command leaves the page
as it was until you run one.

**Formats.** The spec, proofs and anchor formats change wording only. The evidence format, the
signature format (from `approval_format.md`), the payload schema and
`references/drift_criteria.md` each carry a `> Format-Version:` line; a tool that parses any of
them should read that line rather than a number written in prose.

### The words that were retired

Every one of these is gone from the code, the skills, the references, the docs and every line of
output, in any casing:

| Retired | What says it now |
|---------|------------------|
| `tested`, the gate value | `passed` |
| `recorded`, the gate value | `strong` |
| `approved`, the gate value | `signed` |
| `approve`, `approval`, `approvals` | `sign`, `signature`, `signatures` |
| `approver`, `approvers` | `signer`; no config key names who may sign |
| `verified`, `verify` as a command name | the cell's own word; `purlin:audit` for the run |
| `verdict`, the four verdicts | what the brief reports: the strength, the observations, settled |
| `Reviewed`, the state | the strong cell's word |
| `re-verify pending` | the passed cell reading `out of date` |
| `Proof ready` | the passed cell; a rule with no proof reads `no proof written` |
| `lowest state`, `seven states` | the three cells |
| `auto-approval` | nothing: no machine writes a signature file |
| `review queue` | queue |
| `purlin:verify`, `purlin:review`, `purlin:approve` | `purlin:audit`, `purlin:sign` |
| `verify_gate`, `verify-gate:` | `gate_check`, `gate:` |
| `validated/<name>` and `record/<name>` tags | `signed/<version>`, which `purlin:sign` writes |
| `needs a person` | `manual test`, naming the work. The one surviving use is the queue's header |
| `risk`, `[risk: ...]`, `ai_review_at` | the **level**, `[level: ...]` with the gate's own words |
| `manual audit` | `not audited` |
| `not required` | removed: a rule whose level is below `signed` needs no signature, and its signed cell reads `signed` or `unsigned` |
| the source `developer` | the folder: `local/` or `ci/` |
| `happy_path_only` and the other free-check names | the sentence the audit wrote about what it observed |
| free scan, hint | the AI audit's observations |
| `pre_push`, the pre-push hook | nothing: a push is free and no hook runs |
| `signers`, the signer list, `signer list missing` | nothing: a signature names its signer, and `purlin:init --update` drops the key |
| the protected branch | nothing: a signature counts on whatever commit carries it |
| the self-signing check, `the signer last touched the test` | nothing: git names both authors |
| `purlin_run.py --quick` | `purlin_run.py --test`, the arm `purlin:test` runs; `--quick` exits 2 |

`audit` is un-retired and means one thing: the level 2 run. An audit proves a rule strong or
weak. The grading scores the earlier `purlin:audit` produced stay retired.
`references/glossary.md` lists each word and the spelling it replaced.

### What was removed

Gone in 0.10.0: the two LLM grading scores and the skill and agent that produced them; the
runner registry and its per-runner proof files, replaced by `@env` and the runner matrix; the
committed evidence files, replaced by `.purlin/evidence/`; the committed proof files, which are now runtime
state under `.purlin/runtime/` and are not committed at all; the committed dashboard data; the
pre-push hook and every branch rule Purlin used to print; the pull request comment and the
dashboard artifact; the design-tool importer, the visual hash and the live design-tool
connection; the signer
list, the check that a signer did not last commit to the test, and the check that a signing
commit is on the protected branch, so a signature counts on a signed commit whose hashes match
and init's workflow prerequisites are a remote and a known host; and C and PHP support, so a
project that used either keeps its proofs only by writing a custom proof plugin. Several flags
went with them. The free checks went too: `scripts/review/static_checks.py`, its `--sweep`,
`scripts/mcp/purlin/checks.py`, and the `rules_without_a_negative_case` key of
`purlin:drift qa`, which reports what changed and what is waiting and judges nothing. A
`@manual` proof stays: it has no test, its strong cell reads
`manual test`, and its evidence is a signature carrying a one-line note.

Also gone, each without a replacement:

- `.purlin/config.local.json`, the per-person settings file laid over `.purlin/config.json`. A
  project has one settings file, committed, and the `purlin_config` tool writes to it.
- `purlin:anchor propose`. A change to a pinned rule is a pull request against the anchor's
  source repository, and `purlin:anchor sync` brings it back once it merges.
- `purlin:init --upstream-check`, the weekly job that opened an issue when an anchor pin fell
  behind, and the `issues: write` permission it needed. `purlin:drift` still reports a pin
  behind, and `purlin:anchor sync --check` exits 1 on one.
- `tools/`: the PM and QA skills for Claude Desktop and their packed `.skill` archives. A PM or
  QA person works in Claude Code on the repository, or through a pull request.
- `purlin:rename`. `agents/purlin.md` says what carries a feature's name and moves together
  in one commit.
- The upgrade steps for layouts 0.9.5 never shipped: the gate value renames, the signer key,
  the `[risk: ...]` rule tag, the scope tag and its runner registry, the pre-commit and
  pre-push shims under `.purlin/hooks/`, the stale `purlin.yml`, and moving records into
  source folders. `purlin:init --update` reads what 0.9.5 left and nothing else.
- The reader that mapped the `[risk: ...]` rule tag. An old spelling is not recognised, and the
  tag stays in the rule text.
- `purlin:spec --resolve` and `scripts/mcp/purlin/ids.py`. Ids are still allocated against
  `origin/main`; a duplicate after a merge is renumbered by hand.
- `purlin:find`. `purlin:status <name>` shows one spec's rules and their cells.
- `scripts/report/scan.py`, which printed a repository's rollup from its URL without a
  checkout. `.purlin/tests.md`, which `purlin:test` commits, is what a reader without a checkout
  reads on the git host.
- The kind of test on a proof line is gone: `@integration`, `@e2e` and `@unit`, the `--tier`
  flag of `purlin_run.py`, the `tier` field of a proof file and `PURLIN_PROOF_TIER`.
  `purlin:test` runs every marked test of the features it runs, and `purlin:init --update`
  drops the tag from a 0.9.5 proof line.
- The proof plugins, for pytest, Jest, Vitest, xUnit, shell and SQL, the proof files they
  wrote under `.purlin/runtime/`, the `test_framework` and `sql_engine` settings, and the
  wiring init wrote into a project's test configuration. A proof is optional at the gate
  `passed`, where a test marked with a rule's own id is that rule's evidence, and required
  from `strong` up, where a rule with a test and no proof reads `no proof`.
- A rule names no owner and no upstream criterion: `[origin: ...]` and `[criterion: ...]` are
  no longer tags, the payload and the brief carry neither, init stops listing rules without an
  owner at `signed`, and `purlin:drift` loses `criteria_without_rules`, `pm_rules_changed`,
  `engineer_added_rules` and `tags_missing`.
- The tie between a design and a spec is gone: the `designs/` folder and README init wrote, the
  design anchor and its `> Source:` of local file globs, `design_hash` in a signature, the
  design layer of the brief, the `CHANGED_DESIGNS` kind and the `design` view of
  `purlin:drift`, and the copying of designs by `purlin:anchor sync`.

### The 0.10.0 line that never shipped

An earlier 0.10.0 development line added two LLM grading scores, one for proof descriptions and
one for test bodies, together with a skill and an agent to produce them. A later one added a
seven-state ladder. Neither was released, and 0.10.0 as it ships has neither. What a person needs
before signing a rule is a brief: the test strength from the evidence, and what the AI audit
observed where the rule's level asks for one. `references/review_criteria.md` holds those criteria.

## 0.9.5 — Windows-scoped proof checks & C# support

### Fixed

- **`purlin:audit` now runs on Windows.** The audit toolchain shells out to `scripts/audit/static_checks.py`, which was unusable on Windows for three independent reasons, each fixed here (issue #3):
  - **`import fcntl` crashed the module on load.** `fcntl` is POSIX-only, so *every* subcommand (`--read-cache`, `--load-criteria`, `--check-proof-file`, Pass 1, `--write-cache`, `--prune-cache`) died with `ModuleNotFoundError` before doing any work. `fcntl` is now imported under `try/except ImportError` behind a `_HAS_FCNTL` flag, and the audit-cache lock goes through `_lock_exclusive`/`_unlock` helpers that use `fcntl.flock` on POSIX and `msvcrt.locking` on Windows — preserving the exclusive read→merge→write serialization that keeps concurrent subagent writers from clobbering each other (`static_checks` RULE-25/RULE-29).
  - **Text I/O assumed UTF-8.** ~16 `open()` calls omitted `encoding=`, so on a Windows cp1252/ASCII locale they raised `UnicodeDecodeError` reading the tool's own UTF-8 files (e.g. `references/audit_criteria.md`). Every text-mode `open()` now specifies `encoding='utf-8'` (`static_checks` RULE-30).
  - **`--load-criteria` printed non-ASCII to a non-UTF-8 console.** Even after the read fix, the criteria text (which contains `✓`/`⚠` glyphs) raised `UnicodeEncodeError` on an ASCII stdout. `static_checks.py` now reconfigures stdout/stderr to UTF-8 at startup (`static_checks` RULE-30).

### Added

- **Deterministic Pass-1 coverage for C#/.NET tests.** Pass 1 previously recognized only pytest/Jest/Shell markers, so xUnit/NUnit/MSTest tests carrying `[Trait("PurlinProof", "feature:PROOF-N:RULE-N:tier")]` produced zero proofs and the structural checker silently no-op'd on `.cs` files. The new `check_csharp` analyzer parses those trait markers, locates each `[Fact]`/`[Theory]` method body via a C#-aware brace/string scanner, and runs assert-true / no-assertion detection — recognizing xUnit `Assert.*`, NUnit `Assert.That`, MSTest `Assert.*`, FluentAssertions `.Should()`, and Playwright fluent assertions (`Expect(...)`/`Assertions.Expect(...)` chained to a `To*Async()` matcher) as assertions (`static_checks` RULE-31). A bare `Expect(x)` with no matcher chain is still flagged `no_assertions`. The dispatch was extracted into `analyze_test_file()` and now routes `.cs`. `references/supported_frameworks.md` documents the new coverage. To keep this broader structural acceptance from masking weak tests, the Pass-2 audit criteria gained a "presence/visibility-only assertion" WEAK check (`references/audit_criteria.md` → Criteria-Version 17).
- **Portable interpreter guidance in `purlin:audit`.** `skills/audit/SKILL.md` documents a `python3 → python → py -3` fallback for invoking `static_checks.py`, since stock Windows does not put `python3` on PATH (`skill_audit` RULE-15).
- **`purlin:audit` reaches C# tests even when `test_file` is empty.** Under `dotnet test`, `TestCase.CodeFilePath` is often null (no surfaced source info), so the xUnit logger emits proof entries with a blank `test_file` — which previously blocked the audit skill from locating the `.cs` code to scan (Pass 1) or read (Pass 2). `static_checks.py` now exposes `--resolve-source <test_name>`, which derives the declaring type from the fully-qualified `test_name` and locates its `.cs` file (skipping `bin`/`obj`), and `skills/audit/SKILL.md` uses it as a fallback (`static_checks` RULE-32, `skill_audit` RULE-16). Populating `test_file` natively still requires `RunConfiguration.CollectSourceInformation=true` with full PDBs — now documented.

### Testing

- New proofs: `static_checks` PROOF-44/45 (AST structural guards — no unconditional `fcntl` import; `encoding='utf-8'` on every text-mode `open()`), PROOF-46–49 (C# assert-true / no-assertion / multi-framework assertion recognition / `.cs` dispatch), PROOF-50 (Windows lock path driven through an injected fake `msvcrt`, `@integration`), PROOF-51 (full CLI pipeline via real subprocess, `@e2e`), PROOF-52 (the cp1252 failure reproduced by running `--load-criteria` under `PYTHONUTF8=0`/`LC_ALL=C`, `@e2e`); `skill_audit` PROOF-15. PROOF-55 covers the Playwright assertion recognition (and the bare-`Expect` negative). Windows behavior is now verified for real on a `windows-latest` GitHub Actions runner — `.github/workflows/windows-proofs.yml` runs PROOF-53 (native `msvcrt` lock path, `_HAS_FCNTL` genuinely False) and PROOF-54 (`--load-criteria` under the native console codec) in the dedicated `@windows` proof tier and commits the results back — in addition to the host simulation (fake `msvcrt`) and ASCII-locale subprocess repro. Independent audit of the new proofs: STRONG at 100% integrity, 0 WEAK/HOLLOW.

## 0.9.4 — Plugin-bundled MCP server & e2e proof quality

### Fixed

- **MCP server no longer version-pinned in consumer projects.** `purlin:init` wrote a project-level `.mcp.json` entry with an absolute path into the versioned plugin cache (`~/.claude/plugins/cache/purlin/purlin/<version>/scripts/mcp/purlin_server.py`). Project-scope `.mcp.json` takes precedence over plugin-provided servers and old cache directories stick around, so every plugin update silently stranded the project on the previous release's server — fresh data, stale code, no error (this is exactly how a 0.9.3 project kept rendering dashboards with 0.9.1 logic). The server is now bundled with the plugin itself: `.claude-plugin/plugin.json` declares it under `mcpServers` with `${CLAUDE_PLUGIN_ROOT}`, which Claude Code resolves to the installed plugin path on every launch, so the server always tracks the installed version (`skill_init` RULE-38/39). Init no longer writes a `purlin` entry into the project's `.mcp.json`; it removes the legacy entry while preserving any other MCP servers in the file (`skill_init` RULE-40).

  **Upgrading an existing project:** after updating the plugin, run `purlin:init --mcp` once (new flag — runs only the migration step) to remove the stale entry, then `/reload-plugins` (or restart the session).

- **`sync_status` flags the legacy entry automatically.** When the project's `.mcp.json` defines a `purlin` server pinned to a plugin-cache path, every status report opens with an advisory naming the pinned path and a `→ Run: purlin:init --mcp` directive — so pre-0.9.4 projects surface the migration on their first status call instead of relying on release notes (`sync_status` RULE-38). Dev checkouts (purlin entries pointing outside the plugin cache) are exempt.

### Added

- **E2E proofs must be observable flows.** Reverse-engineering UI-heavy codebases with `purlin:spec-from-code` produced implementation-coupled proofs tagged `@e2e` ("Assert `config.ts` AES-decrypts...", "Assert `loginRedirect` uses scope X") — satisfiable without launching the app, steering builders into unit-style tests that audit WEAK/HOLLOW. The quality guide now has a canonical **"E2E proof descriptions (observable flows)"** section (`references/spec_quality_guide.md`): `@e2e` proofs read as arrange → act → observe through the real running app, never name source files or internal functions, observe data contracts at the boundary they cross (outbound request, rendered output, storage state after a real flow), and stay tool-agnostic — executable by Playwright, Cypress, an MCP-driven browser, or screenshot + vision (`purlin_references` RULE-13).
- **E2E Proof Tier Integrity audit criteria.** `references/audit_criteria.md` (Criteria-Version 16) adds two Pass 2 WEAK criteria at HIGH priority applying to ALL `@e2e` proofs, not just design anchors: **tier mismatch** (test tagged `@e2e` never drives a browser/renderer/full stack — or the converse, a render/flow test with no tier tag) and **source-constant assertion** (asserting a config constant where the rule describes runtime behavior) (`purlin_references` RULE-14). The version bump does not invalidate audit caches — the cache key excludes the criteria version.
- **E2E runner reality check in `purlin:spec-from-code`.** Phase 1 records an `e2e_capable` flag; when a category's generated proofs include `@e2e` and no e2e runner is detected, the skill warns in the category review block and the Phase 4 summary instead of silently emitting unrunnable proofs (`skill_spec_from_code` RULE-32). `references/supported_frameworks.md` gains an **"End-to-end (browser) proofs"** section documenting interim proof emission through the existing Vitest/Jest markers or shell `purlin_proof` wrappers (`purlin_references` RULE-15).

### Changed

- **`purlin:spec-from-code` enforces proof quality at generation time.** The step 7 tier review now runs an inverse check — every `@e2e` description must match its tag or be rewritten/retagged (`skill_spec_from_code` RULE-30) — and step 11 validation rejects proof descriptions naming source files or internal symbols (`skill_spec_from_code` RULE-31). `purlin:spec` applies the same observable-flow check in Validate-Before-Commit (`skill_spec` RULE-8).

### Testing

- New proofs: `skill_spec_from_code` PROOF-42..45, `skill_spec` PROOF-9, `purlin_references` PROOF-13/14/15 (grep guards over the skill and reference text). Independent audit of the new proofs: 0 WEAK/HOLLOW (all structural documentation guards, excluded from integrity scoring); 3 advisory regex-precision findings applied before commit. Full suite 372 passed, 40/40 features VERIFIED.
- `skill_init` PROOF-40/41 now parse `.claude-plugin/plugin.json` directly (asserting `mcpServers.purlin` uses `python3` with `${CLAUDE_PLUGIN_ROOT}` args) and PROOF-42 verifies the legacy `.mcp.json` migration instructions, replacing the old greps for project-level `.mcp.json` creation.

## 0.9.3 — Dashboard visibility before tests exist

Quality-of-life release fixing the "empty dashboard" experience after `purlin:spec-from-code`: a freshly specced project now shows its full rule set and coverage plan in `purlin-report.html` before a single test has run.

### Added

- **Planned proofs in the dashboard.** The report data (`.purlin/report-data.js`) now includes the `PROOF-N` entries declared in each spec's `## Proof` section that have no executed result yet — status `"planned"`, tier parsed from the proof's `@tag` (default unit), empty test location (`report_data` RULE-8). The dashboard renders them greyed with a "not run" tag in the Proof column instead of a bare dash (`purlin_report` RULE-33), so the intended coverage plan is visible immediately after spec generation. Planned proofs are display-only: proved/total counts, vhash, rule status, and feature status are computed from executed proofs exactly as before (`report_data` RULE-22). Proof results are still written only when tests run (`purlin:unit-test` / `purlin:build` / `purlin:verify`).

### Changed

- **Category sections are expanded by default.** Previously every category started collapsed, so a project with many small categories looked like it had no specs at all. Categories now render expanded; collapsing one is remembered per browser via localStorage (`purlin_report` RULE-20, persistence unchanged per RULE-21).
- **`purlin:spec-from-code` no longer creates single-spec folders.** A new Phase 2 taxonomy step merges single-feature categories into the closest related category, or — when nothing fits — places the spec directly at `specs/<name>.md` with no folder (`skill_spec_from_code` RULE-29). Uncategorized specs display under "other" in the dashboard.
- **Docs and skill wording aligned with actual behavior.** PASSING criteria say "all rules" (matching `_determine_status`); verify receipt format documented as `features=N/T`; installation/testing/lifecycle guides corrected (committed digest, real GitHub Actions example, shell plugin path); spec-from-code guide documents the post-generation build lifecycle; lifecycle PM diagram regenerated.

### Testing

- New proofs: planned-proof emission and dedup against executed results including required/global anchor rules (`report_data` PROOF-22), coverage isolation (PROOF-23), greyed "not run" rendering with no audit tag (`purlin_report` PROOF-33, Playwright), and the single-spec folder ban (`skill_spec_from_code` PROOF-41). Dashboard PROOF-19/20/21 updated for the expanded-by-default behavior. Independent audit of the changed proofs: 5 STRONG, 0 WEAK/HOLLOW.

## 0.9.2 — .NET test support (xUnit)

Incremental release adding .NET to the supported test ecosystems, backed by a refactor of the proof-plugin specs.

### Added

- **xUnit/.NET proof plugin.** `scripts/proof/xunit_purlin.cs` is a custom `dotnet test` logger (`ITestLoggerWithParameters`, FriendlyName `purlin`) that collects proof traits in-process — no `.trx` post-parsing — and emits feature-scoped proof JSON per the shared proof-plugin contract. Mark tests with a trait:

  ```csharp
  [Fact]
  [Trait("PurlinProof", "feature_name:PROOF-1:RULE-1:unit")]
  public void ValidLogin() { ... }
  ```

  Because the marker is a test trait rather than a parsed title string, NUnit `[Category]`/`[Property]` and MSTest `[TestProperty]` surface the same way — the logger covers C#, F#, and VB.NET test projects. Run with `dotnet test --logger purlin -- RunConfiguration.CollectSourceInformation=true`. Setup is manual for now (the .NET test platform only discovers loggers from assemblies named `*TestLogger.dll`) — see `references/formats/proofs_format.md` for wiring steps. Proven by an integration suite that drives a real `dotnet test --logger purlin` run; independent audit: 6/6 STRONG.

- **`purlin:init` presents every shipped framework.** The framework selection list now covers all shipped plugins — pytest, Jest, Vitest, C, PHP, SQL, Shell, and xUnit (plus "other") — instead of only the auto-detected subset (`skill_init` RULE-48). Frameworks that need manual wiring (xUnit) print their setup steps after the plugin file is copied.

### Changed

- **Proof-plugin specs split per framework.** The monolithic `proof_plugins` spec is gone, replaced by one spec per plugin (`proof_plugins_pytest`, `_jest`, `_vitest`, `_shell`, `_c`, `_php`, `_sql`, `_xunit`) plus a `proof_common` anchor that holds the shared contract: feature-scoped overwrite, tier file naming, marker→JSON field mapping. Proof markers were re-homed to their per-plugin specs.
- `references/supported_frameworks.md` is now Format-Version 5: adds an **Additional Plugins (manual setup)** section for shipped-but-not-auto-scaffolded plugins (currently xUnit).

### Testing

- New integration proofs drive the compiled xUnit logger through a real `dotnet test` run (`dev/test_multilang_proof_plugins.py::TestXUnitProofPlugin`).
- Strengthened existing proofs: C plugin proofs regenerated from a real `gcc` run, Vitest RULE-1 marker parse now asserted inline, pytest "call phase only" boundary proved, and three audit-pipeline proofs recorded from a full-suite run.

## 0.9.1 — Vitest reporter & JS/TS audit fixes

Bug-fix release addressing two reported issues in JavaScript/TypeScript proof handling.

### Fixed

- **Vitest reporter silently emitted zero proofs on Vitest 2.x+ (#1).** `scripts/proof/vitest_purlin.ts` collected proofs in `onTaskUpdate`, whose pack shape changed in Vitest 2 (`[id, result, meta]`, where `result` lacks `name`/`file`), so the marker regex never matched and tests passed with no `.proofs-*.json` written. The reporter now collects in `onFinished(files)` via a recursive file→suite→test walk — the hook whose shape is stable across Vitest 2.x–4.x — mapping `result.state` to pass/fail, skipping unrun tasks, and resolving `test_file` from the file task's `filepath`.
- **All Vitest projects now scaffold the native `vitest_purlin.ts`.** Vitest never calls Jest's `onTestResult`/`onRunComplete` hooks, so the previous "Vitest → `jest_purlin.js`" mapping was also silently broken. Vitest loads `.ts` reporters natively via Vite, so one reporter covers both JS and TS projects.
- **`check_js` audit regex misfired on common Vitest patterns (#2).** `scripts/audit/static_checks.py::check_js()` used a lazy `(.*?)\}\s*\)` body matcher that truncated at the first inner `}` (options objects, destructured params, type assertions) and a `[^"']*` title class that dropped titles containing apostrophes. Replaced with a stdlib brace-balancing tokenizer that tracks string/template/regex literals and comments.
- **Claude plugin manifest version lagged the release.** `.claude-plugin/plugin.json` — the version consumers install against via the plugin marketplace — was left at `0.9.0`. It now reads `0.9.1`, and a new guard (`purlin_version` RULE-5 / PROOF-5) asserts the manifest version stays in lockstep with the `VERSION` file, joining the existing `templates/config.json` check so this can't silently recur.

### Testing

- PROOF-29 was strengthened to actually drive the compiled reporter via a synthetic Vitest 2.x+ task tree (the old proof only ran `tsc` + `node` on hand-built JSON and never invoked the reporter). New regression proofs cover the exact issue #2 repro.
- Docs aligned: `references/supported_frameworks.md` (Format-Version 3), `references/formats/proofs_format.md`, and `docs/testing-workflow-guide.md` now describe the native Vitest reporter and tested version range.

## 0.9.0 — Rule-Proof Runtime

Complete redesign. Purlin v0.9.0 replaces the v1 system (35 skills, 5 agents, 8 hooks, 8 MCP tools) with a minimal rule-proof runtime.

### What Changed

**Specs replace features.** The `features/` directory and its companion files (`.impl.md`, scenarios, Given/When/Then) are gone. Specs live in `specs/<category>/<name>.md` using a 3-section format: `## What it does`, `## Rules`, `## Proof`. Rules are numbered (`RULE-N`), proofs map to rules (`PROOF-N (RULE-N)`).

**Proofs replace tests.json.** Test runners emit `*.proofs-*.json` files next to specs. Proof markers in tests: `@pytest.mark.proof("feature", "PROOF-1", "RULE-1")` for pytest, `[proof:feature:PROOF-1:RULE-1:tier]` in Jest test titles, `purlin_proof()` for shell.

**`sync_status` replaces `purlin_scan`.** One MCP tool reads specs and proof files, diffs them, reports coverage with `→` directives that tell the agent exactly what to do.

**Verification is new.** `purlin:verify` runs all tests, issues receipts for features with 100% rule coverage. `vhash = sha256(sorted RULE IDs + sorted proof IDs/statuses)`.

**12 skills** (down from 35). All optional — no skill invocation required to write any file.

**2 hard gates** (down from 8). Invariant write protection + proof coverage for receipts.

**2 MCP tools:** `sync_status`, `purlin_config`.

**2 hooks:** `PreToolUse` gate for invariants, `SessionStart` for cleanup.

**1 agent** (down from 5). No modes, no role-based permissions.

### Key Differences from v1

| v1 | v0.9.0 |
|----|--------|
| `features/<category>/<name>.md` | `specs/<category>/<name>.md` |
| Scenarios (Given/When/Then) | Rules (RULE-N) + Proofs (PROOF-N) |
| `tests/<feature>/tests.json` | `specs/<category>/<feature>.proofs-<tier>.json` |
| 3 modes (PM, Engineer, QA) | 1 agent, no modes |
| `purlin_scan` + `purlin_status` | `sync_status` |
| Role-based permissions | No permissions (skills are optional) |
| 35 skills | 12 skills |
| Write guard with file classifications | Gate hook for invariants only |

### New in v0.9.0

- **Invariants with external sources:** `> Source:` + `> Pinned:` metadata. Git-sourced and Figma-sourced. Auto-sync with `purlin:invariant sync`.
- **Manual proof stamps:** `@manual(email, date, commit_sha)` in spec's `## Proof` section. Staleness detection via `> Scope:` file tracking.
- **Verification receipts:** `*.receipt.json` files with `vhash` and commit SHA. `--audit` mode for CI.
- **Feature-scoped proof overwrite:** Each test run replaces only its feature's entries in the proof file, preserving others.

### Tier Rename (0.9.0)

- `default` → `unit` (isolated logic, controlled inputs)
- `slow` → `integration` (real dependencies — DB, APIs, filesystem)
- `e2e` and `manual` unchanged
- Rename your proof files: `*.proofs-default.json` → `*.proofs-unit.json`
- Update pytest markers: `@pytest.mark.slow` → `@pytest.mark.integration`
- Update jest markers: tier segment in `[proof:...]` tag
- Update shell env var: `PURLIN_PROOF_TIER=slow` → `PURLIN_PROOF_TIER=integration`

### MCP Server Spec Split (0.9.0)

- `specs/mcp/mcp_server.md` (34 rules) split into 4 focused specs:
  - `mcp_transport.md` (7 rules) — JSON-RPC transport
  - `sync_status.md` (15 rules) — rule coverage reporting
  - `drift.md` (11 rules) — structured change summary
  - `purlin_config.md` (1 rule) — config read/write
- Tool names: `sync_status`, `purlin_config`, `drift`

### Teammate Spawning Now Invisible (0.9.0)

- "team up" / "create a purlin team" removed as user-facing concept
- Teammates are automatically spawned by verify and audit
- Auditor, builder, reviewer still exist as agents — just no longer user-managed

### Migration

Keep your old `features/` directory — `purlin:spec-from-code` detects it and migrates your existing specs to the new 3-section format. Old scenarios and rules are used as primary input for generating new-format specs, so you don't lose the work you've already done. Remove only the non-spec artifacts (`rm -rf .purlin/ pl-* *.sh`), then run `purlin:init` followed by `purlin:spec-from-code`.
