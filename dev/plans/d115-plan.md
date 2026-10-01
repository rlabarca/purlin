# Decisions 100 to 116: the build plan

Written by the planning agent on 2026-10-01 against local `main` at `20a054551`. The specs under
`specs/` describe decisions 100 to 115: 39 specs, 414 rules, 831 proofs. The code and the tests
describe decision 103. This plan makes the code and the tests meet the specs, in the two rounds
decision 116 set, with 11 lanes in the cloud and 4 on this Mac.

Where two decisions differ, the later one holds. Everything a decision cuts is deleted outright
(decision 44): its code, tests, fixtures, docs lines and settings, with no test that a removed
thing is absent. `RELEASE_NOTES.md` alone keeps history, and the upgrade from 0.9.5 keeps what
it needs.

**No lane edits a file under `specs/`.** The specs are written. A lane that cannot build to a
proof as worded builds the rest, leaves that proof, and reports it. Section 9 lists the four
places where the specs disagree with a decision or with each other; the base commit of section
1 corrects them before any lane starts.

## 0. The numbers this plan is cut from

Counted in the tree at `20a054551` with the script of appendix A.

| What | Count |
|---|---|
| Specs, rules, proofs | 39, 414, 831 |
| Test comments in `dev/test_*` | 2,290 |
| Right as they stand | 412 |
| Naming a proof or a spec no spec has (the "about 1,600") | 1,621: 1,496 a proof that is gone, 125 a spec that is gone |
| Naming a proof whose wording changed after the test last changed | 257 |
| Proofs no test comment names | 162 |

No file under `dev/`, `scripts/`, `skills/`, `docs/`, `references/` or `agents/` changed since
`7f776cc84^`, the commit before the specs were rewritten.

## 1. The base commit, before any lane

The coordinator makes one commit on local `main`, alone and first, then pushes `main` as
`d115/base`. Every round 1 lane branches from it. It holds five things and nothing else.

**1. This plan**, `dev/plans/d115-plan.md`.

**2. The spec corrections of section 9**, as written there, under the subject
`spec: the corrections the build plan found (d115-plan section 9)`.

**3. The stubs**, each with the docstring section 3 gives it, so every lane can import what
another lane fills:

| File | What the stub holds | Filled by |
|---|---|---|
| `scripts/mcp/purlin/project.py` | `project_name(project_root)` answering the folder's name | `states` |
| `scripts/mcp/purlin/wording.py` | K4's constants; `stale_comments` answering `[]`; `test_last_change` answering `None`; the command line printing `No test comment to correct.` and exiting 0 | `states` |
| `scripts/mcp/purlin/facts.py` | K6's constants; `tests_fact` answering `not met`; `signoff_fact` answering `{'word': 'not signed', 'version': None, 'commit': None, 'since': None}` | `states` |
| `scripts/export/package.py` | added beside what is there: `only_records_between` and `same_code` answering `False`; `project_version` copied from `release.py`; `time_words`; `run_lines` answering `[]` | `signoff` |
| `scripts/review/audit_run.py` | `run(...)` answering `0` | `audit` |
| `scripts/review/plain_checks.py` | `CHECKS`; `check(...)` answering `[]` | `spot` |
| `scripts/review/targeted_break.py` | `break_proof(...)` answering `{'result': 'not made', 'why': 'not built yet'}` | `spot` |

**4. The shared test helpers, changed once and then frozen** (K16): `dev/run_project.py`,
`dev/mcp_project.py`, `dev/sign_project.py` and `dev/fake_claude.py` lose every gate, mutation
and strength argument and write a settings file of `version` and `tests` alone.

**5. This repository's own `.purlin/config.json`**, set to `version` and `tests` (decision 109:
"this repository's own settings are fixed by hand once").

The sweep after the base commit is red in every test that passes `gate=` or `strength=` to a
helper. That is expected (decision 116), and each lane clears it in the files it owns.

## 2. The lanes

Fifteen lanes. Each owns files no other lane writes. A cloud lane is one cloud session that sees
only GitHub, on Linux, at `d115/base`; its branch is `lane/d115-<lane>` and it pushes nothing
else. A local lane runs on this Mac in a worktree
`/Users/richlabarca/LocalCode/purlin-wt/d115-<lane>` on the same branch name.

| Lane | Round | Where | Planned spend | Builds to |
|---|---|---|---|---|
| `evidence` | 1 | cloud | $7 | `evidence_writer`, `evidence`, `reports` |
| `states` | 1 | cloud | $9 | `states`, `summary` |
| `signoff` | 1 | cloud | $9 | `signatures`, `package` |
| `spot` | 1 | cloud | $5 | `plain_checks`, `planted_bug` |
| `audit` | 1 | cloud | $6 | `ai_audit` |
| `run` | 1 | cloud | $8 | `run_script` |
| `remote` | 2 | cloud | $6 | `host` |
| `anchors` | 2 | cloud | $7 | `upstream`, `drift`, `renumber`, `security_no_dangerous_patterns` |
| `setup` | 2 | cloud | $8 | `scaffold`, `update` |
| `mcp` | 2 | cloud | $6 | `server`, `config_engine`, `specs`, `schema_spec_format`, `purlin_version`, `purlin_output` |
| `words` | 2 | cloud | $7 | the ten `skill_*` specs, `purlin_agent` |
| `dashboard` | 2 | local | none | `purlin_report` |
| `docs` | 2 | local | none | `purlin_docs`, `install` |
| `team` | 2, after the merges | local | none | `collaboration` |
| `deck` | 2, after the merges | local | none | no spec |

**Planned cloud spend: $78 of the $80** decision 116 allows: $44 in round 1, $34 in round 2.
The coordinator reads the balance after round 1. If round 1 spent more than $46, `words` runs
locally; if more than $52, `mcp` runs locally as well. Both are text and deletions and need
nothing a cloud session has that this Mac lacks.

### What a cloud session may lack

| Lane | What it needs that a cloud Linux session may not have | What happens |
|---|---|---|
| every cloud lane | the full git history, for appendix A's script | the lane runs `git fetch --unshallow origin` where `git rev-parse --is-shallow-repository` answers `true` |
| `evidence` | `dotnet`, `go`, `npm` for the report fixtures of `dev/test_reports.py` | those tests skip themselves where the tool is absent; integration runs them on the Mac |
| `states` | playwright, for `states PROOF-58` in `dev/test_states.py` | `importorskip` skips it; it also waits for round 2's dashboard; integration runs it |
| `signoff` | `ssh-keygen` and a git that makes SSH-signed commits | the lane checks both first; where either is missing it stops and reports, and the lane runs locally |
| `setup` | `npm`, `dotnet` for `scaffold PROOF-94` and `PROOF-95`; macOS for the seven proofs tagged `@env(macos)` (`scaffold PROOF-36`, `37`, `93`, `94`, `95`, `119`; `update PROOF-31`) | the tests run on Linux where they can and skip where a tool is absent; integration runs them on the Mac, which is where their evidence counts |
| `mcp` | Python 3.9, for `purlin_output PROOF-4` and `PROOF-5` | the tests skip where no 3.9 is found; integration runs them |
| `dashboard` | playwright from `.venv`, and a person's eyes | local lane |
| `docs` | the real `claude` program, for `install` | local lane |
| `team` | every lane merged | local lane, after the round 2 merges |
| any lane | Windows, for the proofs tagged `@env(windows)` | not part of this build; `purlin:test --remote` after it, as `handoff.md` lists |

### What each lane owns

A glob covers new files of the same shape. "Deletes" means `git rm`, whole.

**Round 1**

- **`evidence`** owns `scripts/run/evidence.py`, `scripts/run/reports.py`,
  `scripts/mcp/purlin/{evidence,fingerprint,markers}.py`,
  `references/formats/{evidence_format,marker_format}.md`,
  `dev/test_{evidence_writer,evidence_reader,fingerprint,reports}.py`, `dev/fixtures/reports/**`.
- **`states`** owns `scripts/mcp/purlin/{states,payload,status,summary,board,facts,project,wording}.py`,
  `dev/test_{states,summary,backing_tests,failing}.py`. It may add `dev/test_wording.py`.
- **`signoff`** owns `scripts/review/sign.py`, `scripts/mcp/purlin/signatures.py`,
  `scripts/export/package.py`, `references/formats/{package_format,signature_format}.md`,
  `dev/test_{signatures,export}.py`. Deletes `scripts/export/release.py`, `dev/test_tag.py`.
- **`spot`** owns `scripts/review/{plain_checks,targeted_break}.py`, new
  `dev/test_plain_checks.py`, new `dev/test_planted_bug.py`.
- **`audit`** owns `scripts/review/{audit_run,ai_audit,marked_tests}.py`,
  `references/review_criteria.md` (every section but "Heuristic spot tests", which is the
  owner's official text and is not changed), `dev/test_{ai_audit,ai_audit_tests_named}.py`.
- **`run`** owns `scripts/run/purlin_run.py`, `scripts/mcp/purlin/frameworks.py`,
  `references/supported_frameworks.md`, `dev/test_run_script.py`, the root `conftest.py`.
  Deletes `dev/test_mutation_adapters.py`, `dev/fixtures/mutation/**`, `setup.cfg`.

**Round 2**

- **`remote`** owns `scripts/run/{host,remote,workflow,ci}.py`, `templates/purlin.yml`,
  `templates/purlin.azure-pipelines.yml`, `.github/workflows/purlin.yml`,
  `dev/test_{host,remote,host_pathspec,consumer_ci}.py`, `dev/fixtures/consumer-ci/**`.
- **`anchors`** owns `scripts/anchor/upstream.py`, `scripts/mcp/purlin/drift.py`,
  `scripts/spec/renumber.py`, `references/drift_criteria.md`,
  `references/formats/anchor_format.md`,
  `dev/test_{upstream,upstream_notes,drift,renumber,security}.py`,
  `dev/test_e2e_anchor_{authority,rules}.sh`, `dev/test_e2e_external_refs.sh`,
  `dev/setup-external-refs.sh`.
- **`setup`** owns `scripts/init/{scaffold,update}.py`,
  `templates/{config.json,gitignore.purlin,evidence-readme.md}`,
  `dev/test_init_{scaffold,update}.py`, `dev/test_init_e2e_wiring.sh`,
  `dev/fixtures/upgrade-0.9.5/**`. Deletes `scripts/run/mutation/**`, whose last importer is
  `scaffold.py`.
- **`mcp`** owns `scripts/mcp/config_engine.py`, `scripts/mcp/purlin/{server,specs,__init__}.py`,
  `references/formats/spec_format.md`, `dev/bump_version.sh`,
  `.github/workflows/version-check.yml`,
  `dev/test_{mcp_server,config_engine,specs_reader,schema_spec_format,purlin_version,purlin_output}.py`.
  Deletes `scripts/mcp/purlin/gate.py`, whose last importers are `server.py` and `scaffold.py`.
- **`words`** owns `skills/*/SKILL.md`, `agents/purlin.md`, `dev/skill_checks.py`,
  `dev/test_skill_*.py`, `dev/test_purlin_agent.py`,
  `references/{glossary,purlin_commands,commit_conventions,spec_quality_guide,rule_examples,writing_style}.md`,
  new `references/evidence_and_signoff.md`, `RELEASE_NOTES.md`, `CLAUDE.md`. Deletes
  `skills/export/`, `dev/test_skill_export.py`, `references/hard_gates.md`,
  `dev/test_vocabulary.py` (it carries no test comment and is a table of retired words, which
  decision 44 rules out).
- **`dashboard`** owns `scripts/report/src/**`, `scripts/mcp/purlin/report_data.py`,
  `dev/build_report.py`, `dev/capture_doc_screenshots.py`, `dev/browser_launch.py`,
  `dev/test_purlin_report.py`, `dev/test_purlin_report_board_layout.py`,
  `dev/test_report_refresh.py`, `dev/fixtures/report/*.json`. Deletes
  `scripts/report/src/filters.js`.
- **`docs`** owns `docs/*.md`, `README.md`, `dev/test_purlin_docs.py`, new `dev/test_install.py`.
- **`team`** owns new `dev/test_collaboration.py`.
- **`deck`** owns `dev/plans/deck/*.py`.

**No lane owns**, and no lane changes: every file under `specs/`; `dev/run_tests.sh`,
`dev/suites.py`, `dev/windows_skip.sh`, `dev/conftest.py`, the four helpers of K16,
`dev/manual/**`, `scripts/purlin_python.sh`, `scripts/mcp/purlin/console.py`,
`.claude-plugin/*`, `VERSION`, `requirements.txt`, `.gitattributes`, `.gitignore`, and every
generated file: `scripts/report/purlin-report.html`, `purlin-report.html`,
`.purlin/evidence/**`, `.purlin/report-data.js`, `.purlin/tests.md`, `docs/images/*.png`,
`dev/plans/deck/*.png`. A failure in one of these is integration's.

Each lane also owns its own report, `dev/plans/d115-reports/<lane>.md`.

### What each lane does, and its acceptance

Every lane's acceptance is the same four checks on the files it owns, and never the full sweep:

1. `python -m pytest <its own test files> -q`: nothing fails but the tests it lists as waiting.
2. Appendix A's script over its own test files prints `0 gone, 0 reworded`.
3. Every proof of its specs has a test comment, counted by
   `grep -c "purlin: <feature> PROOF-" <its test files>` against the spec.
4. The greps of K15 over its own files find nothing.

**`evidence`.** K2 and K3: the section's `email`; retention over the same code
(`package.only_records_between`); `nothing to check`; each report format's skip reason
(`Case.reason`); the audit entry's `breaks` and `explanation`; `audit.mutation`, the table
`.purlin/tests.md` and its writer gone. Formats: evidence 8, marker 4. Waits: `evidence_writer
PROOF-91`, `PROOF-92` (on `signoff`'s `only_records_between`), `PROOF-54` (on `audit`).

**`states`.** K4, K5, K6: `wording.py` and `project.py` and `facts.py` filled; the two facts;
the status's opening lines and last line; the kinds of work and which block; payload schema 14;
the hand check reading `checked at sign-off` with its last note; the spec-ahead line as
information; `gate`, strength and every gate-conditional line gone from the six modules it owns.
Waits: `states PROOF-274`, `PROOF-278` (on `evidence`); `states PROOF-58` (round 2,
`dashboard`); `summary PROOF-50` and `states PROOF-169` (on `signoff`'s `only_records_between`).

**`signoff`.** K7, K8: the package, format 8, schema `purlin-package/4`; `same_code`;
`runs`; `authors` from git; `purlin:sign` building the package, refusing, walking hand checks
alone, signing, tagging; `--version`, `--show`, `--answers`, `--check`. Formats: package 8,
signature 15. Waits: `package PROOF-72` and `signatures PROOF-242` (on `evidence`);
`package PROOF-75` (on `states`' `test_last_change`); `package PROOF-69` (on `states`'
`project_name`).

**`spot`.** K9's two new modules: the six heuristic spot tests exactly as
`references/review_criteria.md`, "Heuristic spot tests", gives them; one planted bug per proof,
in a copy of the project. Waits: none.

**`audit`.** K9's order, verdict, entry, share and cost file in `audit_run.py`; `ai_audit.py` as
the model's reading and the planted bug's request; `references/review_criteria.md` below the
spot tests rewritten to say what the model is now sent and what it decides (nothing).
Waits: `ai_audit PROOF-95`, `PROOF-96`, `PROOF-98`, `PROOF-106` (on `spot`).

**`run`.** K10: `--release` and every mutation flag gone; `--audit` calling
`audit_run.run`; the section's `commit` (K2); the test comments to correct printed after
`Markers:`; `--remote` and `--commit-runner` handed to `remote.run_remote`. Waits:
`run_script PROOF-271` (on `states`); `PROOF-87` (on `spot` and `audit`); `PROOF-274` (on
`evidence`); `PROOF-272`, `PROOF-273` (round 2, `remote`).

**`remote`.** K11: `ensure_runner`; both templates and this repository's own runner file start
on a push to `run/**` alone; `workflow.py`'s gate reasons gone; the host read from the remote
each time. Waits: none.

**`anchors`.** K12's drift: one view, no role; the stale test comments read from `wording.py`;
the status and drift check an anchor's source and pull nothing; anchor format 12; drift
criteria 13; the security anchor's tests cut to the eight rules it holds. Waits: none.

**`setup`.** K1's setup and upgrade halves: one question; a settings file of `version` and
`tests`; no runner file, no mutation config, no gate; the upgrade from 0.9.5 only. Merged
before `mcp`. Waits: none.

**`mcp`.** K1's settings half and K12's server half: the refusal of a call naming no
`project_root`; the settings tool holding `version` and `tests`; the warning for any other key;
`gate.py` deleted; spec format 22. Merged after `setup`.

**`words`.** Each skill says what its spec's one rule names and what the code now does, and
nothing of a gate, a release step, mutation, export, drift roles or `.purlin/tests.md`; every
skill and the agent pass `project_root` on each tool call (K12); the agent's sentence on
worktrees; `dev/skill_checks.py` gains `must_name` (K16) and loses what no kept test calls;
`references/hard_gates.md` becomes `references/evidence_and_signoff.md`, the one home of the two
facts, which evidence counts for a sign-off, when a sign-off counts and what `signed/<version>`
means; `CLAUDE.md`'s two tables and its "Releasing a new version" step 3 follow;
`RELEASE_NOTES.md` 0.10.0 in section 6's words.

**`dashboard`.** K13: the two boxes; the header line of `purlin_report RULE-77`; the
information lines; the page written with its data; the filter buttons, the live age, the
reload, the links to the git host, the unfolded rule and the tabs gone; fixtures at schema 14.
Its acceptance adds the look of section 7.

**`docs`.** The pages decision 109 lists: `how-purlin-works.md`, `getting-started.md`,
`specs-and-anchors.md`, `running-and-evidence.md`, `working-together.md`, `sign-off.md` (new,
from `review-and-signing.md`, `qa-guide.md` and `regulated-workflow.md`), `upgrading.md`
(renamed from `raising-the-gate-and-upgrading.md`, 0.9.5 only), `dashboard.md`, `audit.md` and
`index.md`. Deletes `review-and-signing.md`, `qa-guide.md`, `regulated-workflow.md`,
`team-workflow.md`, `spec-from-code.md`, `raising-the-gate-and-upgrading.md`. The paragraph of
`purlin_docs RULE-16`. `README.md`. `dev/test_install.py`, the five proofs of `install`, with
the real `claude` found past the fake that `dev/conftest.py` puts first on the path, and
skipped with `claude is not installed here` where there is none.

**`team`.** `collaboration PROOF-1`, one test, as `d105-plan.md` L18 walks it, with these
changes: the status opens on K6's three lines; the sign-off is K8's; no audit and no model;
under 120 seconds. It starts after every other lane is merged.

**`deck`.** `build_deck.py` checked slide by slide against what was built; a slide that says
something the build made untrue is corrected. The live slides are read first, since the owner
edits them.

## 3. Contracts

What one lane produces and another consumes. No lane chooses any of it. Filled examples use
`labconnect`, `dana.dev@labconnect.example` on `dana-laptop`, version `0.1.0`, `HEAD` at
`1cf829e`. Where a spec fixes words, the spec is quoted and holds over this section.

### K1. Settings and the project's name (`mcp`, `setup`, `states`)

- `.purlin/config.json` holds `version` and `tests` alone (`config_engine RULE-20`,
  `scaffold RULE-83`, `update RULE-50`).
- From round 1 on, no module reads `gate`, `mutation_engine`, `audit_parallel`, `ci` or
  `project_name`. Round 1 lanes stop importing `scripts/mcp/purlin/gate.py`; `mcp` deletes it.
- `config_engine.KNOWN_KEYS = ('version', 'tests')`.
- The warning for any other key, from `config_engine`, carried in the payload's `warnings`:
  `.purlin/config.json carries %s, which this version does not read. Run purlin:init --update.`
  (keys joined `, `, in the file's order) where the upgrade has a step for every key named, else
  ending `Remove it from .purlin/config.json.`
- The settings tool's refusal: `%s is not a setting; .purlin/config.json holds version and tests. Nothing was saved.`

```python
def project_name(project_root):
    """The project's name, read each time and never written. The first found of: `name`
    under `[project]`, then under `[tool.poetry]`, in pyproject.toml; `name` in
    package.json; the first root `*.csproj` file's name without `.csproj`; the last
    segment of `git remote get-url origin` without `.git`; the folder's name."""
```

### K2. The evidence file, format 8 (`evidence` writes; `states`, `signoff`, `audit`, `run` read)

Schema stays `purlin-evidence/2` (`evidence RULE-35`). Decision 116: the format does not change
for conflicts; `evidence_writer RULE-23` and `RULE-26` hold as written.

- **A section** holds exactly `commit`, `dirty`, `at`, `runner`, `email`, `machine`,
  `fingerprint`, `rules`, `proofs`; a `ci` section holds `hostname` as well and no `email`.
- **`commit`** names the code the section describes: `HEAD` after the run's own commit of the
  specs, tests and settings where `--commit` made one, else `HEAD` when the run started
  (`run_script RULE-95`). `run` hands it to `build_section`, whose signature stays.
- **`email`** is `git config user.email`, or `unknown`.
- **Retention**: a section that saw the same results over the same fingerprint on the same
  machine leaves the file byte for byte as it was only where
  `package.only_records_between(project_root, <its commit>, <the new commit>)` holds.
- **A proof entry** holds `id`, `rule`, `result`, `env`, `manual`, `test`, and `reason` where
  the result is `nothing to check`. `result` is `pass`, `fail`, `missing`, `not run` or
  `nothing to check`.
- **`audit`** holds `rules` alone. Each entry:

```json
{"rule_hash": "...", "proof_hash": "...", "test_hash": "...",
 "verdict": "strong",
 "findings": ["tests/test_age.py::test_age: the test checks nothing."],
 "breaks": {"PROOF-1": {"file": "src/age.py", "line": 12, "before": "return days",
                        "after": "return 0", "result": "caught", "why": "",
                        "break_key": "<64 hex>"}},
 "explanation": ["The test calls age and reads no result."],
 "model": "claude-fake-1", "criteria": "<64 hex>", "at": "2026-10-01T12:05:00Z",
 "commit": "<40 hex>"}
```

  `verdict` is `strong` or `weak`. `notes` is written only where the model gave some. An
  anchor's entry has `breaks` `{}`. Two entries are the same when their three hashes,
  `verdict`, `findings`, `model` and `criteria` are (`evidence_writer RULE-14`).

```python
# scripts/run/evidence.py
def audit_entry(rule, found, commit, at=None):
    """`found` holds verdict, findings, breaks, explanation, model, criteria, notes."""
def merge_audit(data, source, feature, spec_path, entries, rule_ids): ...
def write_audit(project_root, source, feature, info, entries): ...
def kept_audits(sides, current):
    """The entries a write over a conflicted file keeps: `{rule: entry}`."""
```

  `render_table`, `write_table`, `newest_sections` and `counts` go with `.purlin/tests.md`.
- `scripts/mcp/purlin/evidence.py`: `mutation(loaded)` goes; `proof_results(section)` answers
  `{proof: {'result': ..., 'reason': ...}}`, with `reason` only where one was given.

### K3. A skipped test's reason, and nothing to check (`evidence`; read by `states`, `signoff`, `run`, `dashboard`)

- `reports.Case` gains `reason`, the text `reports RULE-32` gives for each format, `None`
  where there is none. `Case(name, outcome, classname='', file=None, package=None, reason=None)`.
- `purlin_run.marker_results` entries become `{status, test_file, test_name, line, reason}`.
- A proof whose every tied case skipped with a reason starting exactly `nothing to check:`
  reads `nothing to check`, its `reason` the text after `nothing to check: `. In an anchor's
  section its rule reads `passed`; in any other spec's section `not run`
  (`evidence_writer RULE-29`).
- Such a marker of an anchor is not missing evidence (`run_script RULE-8`).

```python
# scripts/mcp/purlin/states.py
NOTHING_TO_CHECK = '%s: %s'                                       # PROOF-3, the reason
# scripts/mcp/purlin/status.py
NOTHING_LINE = '%s %s passes with nothing to check here: %s.'     # anchor, RULE-N, reason
```

### K4. A test comment to correct (`states` fills; `run`, `anchors`, `signoff`, `words` read)

`scripts/mcp/purlin/wording.py`:

```python
STALE = ('%s:%d names %s %s, whose wording changed after the test was last changed in %s: '
         'it read "%s" and now reads "%s". ')
STALE_BUILD = ('Run purlin:build %s to make the test show it; the line clears once the test '
               'changes.')
STALE_MOVE = 'Its old wording is now %s: move the comment there.'

def stale_comments(project_root, features, scanned=None):
    """One entry per test comment naming a proof whose wording, at the commit that last
    changed the test, differs from its wording now. A test is last changed at the newest
    commit git blame names for the lines below its comment down to the test's last line,
    or for any line of its file when the file is run whole. A test with an uncommitted
    line is never named. By file, then line.
    Each: {'file','line','feature','id','commit' (sha7),'old','new','now_under','text'}."""

def test_last_change(project_root, path, marker_line, end_line):
    """`(sha, author email)` of that commit, or None."""
```

The command line the build skill names:
`python3 scripts/mcp/purlin/wording.py [--project-root DIR] [--file PATH ...]` prints each
entry's `text`, one per line, then `<n> test comments to correct.`, `1 test comment to
correct.` or `No test comment to correct.`, and exits 0.

Cost: one `git blame --porcelain` per marked test file and per spec, cached; the status here at
most 3 seconds slower than at `20a054551`.

Readers: the payload (each `text` in `warnings`, counted under `to_correct`); the run, after its
`Markers:` line; drift, for the proofs or files its range changed; the renumber helper, which
moves a comment to `now_under`; the package's `authors`.

### K5. The audit's key for a rule's tests (`states`)

`test_hash` is the sha256 of the sorted lines `<file> <test name> <sha256 of the test's
source>`, one per test tied to the rule's proofs, the source as `markers` bounds it with line
ends read as `\n`. A test of an `exit` suite, or one not found by its name, gives
`<file> <test name> <blob id>`. `test_hash_kind` reads `test`, `file`, `manual` or `none`
(`states RULE-110`). An audit entry written before this stops answering.

### K6. The two facts, the status and the payload (`states`; read by every surface)

`scripts/mcp/purlin/facts.py`:

```python
TESTS_MET = 'met'
TESTS_NOT_MET = 'not met'
SIGNED_AT = 'signed %s at %s'                 # version, sha7 of the tagged commit
SIGNED_SINCE = 'signed %s, %d commits since'  # 'signed 0.1.0, 1 commit since' for one
NOT_SIGNED = 'not signed'

def tests_fact(payload):
    """`met` when no entry of `left` is of a kind in summary.BLOCKING, else `not met`."""

def signoff_fact(project_root):
    """{'word','version','commit','since'} for the newest signed/* tag on HEAD or an
    ancestor of it, numbered versions compared as numbers: SIGNED_AT where
    package.only_records_between(tag commit, HEAD), else SIGNED_SINCE with the count of
    commits from the tag to HEAD; word NOT_SIGNED and the rest None where there is none."""
```

**The status's opening lines** (`summary RULE-20`):

```
Purlin status: labconnect, plugin 0.10.0
Tests: not met
Sign-off: signed 0.1.0, 4 commits since
```

**The kinds of work**, in `summary.KINDS`' order (`summary RULE-23`):

| Kind | One, many | Command | Blocks |
|---|---|---|---|
| `to_repair` | `spec to repair`, `specs to repair` | `purlin:spec` | yes |
| `no_proof` | `rule to write a proof for`, `rules to write a proof for` | `purlin:spec` | no |
| `to_correct` | `test comment to correct`, `test comments to correct` | `purlin:build` | yes |
| `to_fix` | `rule to fix`, `rules to fix` | `purlin:build` | yes |
| `no_test` | `rule to write a test for`, `rules to write a test for` | `purlin:build` | yes |
| `to_test` | `rule to test`, `rules to test` | `purlin:test` | yes |
| `to_test_remote` | `rule to test on %s`, `rules to test on %s` | `purlin:test --remote` | yes |
| `to_commit` | `feature whose results are not committed`, `features whose results are not committed` | `purlin:test --commit` | yes |
| `to_strengthen` | `rule to strengthen`, `rules to strengthen` | `purlin:build` | no |

`summary.BLOCKING` is every kind marked yes. `to_commit` is counted as section 8's answer to
Q1 says.

```python
# scripts/mcp/purlin/summary.py
AUDIT_SHARE = 'The audit found %d of %d rules strong (%d%%).'
LAST_LINE = 'Every rule passes its tests on the committed evidence. To sign it: purlin:sign'
def left(features, here_os, corrections=0, uncommitted=()): ...
def last_line(left_items, signoff): ...        # LAST_LINE or None (summary RULE-18)
# scripts/mcp/purlin/states.py
CHECKED_AT_SIGNOFF = 'checked at sign-off'
HAND_NOTE = 'noted at the sign-off of %s by %s, %s: %s'
# version, signer, 'at this commit' | '1 commit since' | '4 commits since', the note
EARLIER_WEAK = 'the last audit, before the rule or its tests changed, found it weak: %s'
# scripts/mcp/purlin/status.py
NOT_WRITTEN_ONE = ('%s: 1 file its scope names is not written yet: %s. Run purlin:build %s, '
                   'or correct the path with purlin:spec %s.')
NOT_WRITTEN_MANY = ('%s: %d files its scope names are not written yet: %s. Run purlin:build '
                    '%s, or correct the path with purlin:spec %s.')
```

`NOTHING_LEFT`, `TO_RELEASE`, `TO_RELEASE_SIGNED`, `RELEASE`, `AUDIT_FOUND`, `STRENGTH`,
`NOT_MEASURED`, `NO_SCORE`, `COULD_NOT_DECIDE` and `payload.release_tag` go.

**The payload, schema 14**, written by `payload.build_payload(project_root,
generated_by='sync_status', config=None)`, whose signature stays. Its eighteen top-level keys
beside `schema_version`:

`generated_at`, `generated_by`, `project`, `version`, `branch`, `commit`, `dirty`, `summary`,
`features`, `left`, `met`, `signoff`, `last_line`, `os_words`, `evidence`, `remote_url`,
`information`, `warnings`.

- `branch`: `git rev-parse --abbrev-ref HEAD`, or `null` on a detached `HEAD`.
- `commit`: the full sha of `HEAD`.
- `met`: `tests_fact`'s answer as a boolean. `signoff`: `signoff_fact`'s dict.
- `information`: the lines of `states RULE-123`, one per spec. `warnings`: every other line,
  K1's and K4's among them.
- `summary` holds `steps`, `audit` and `sentence`. A feature entry and a rule entry carry no
  `test_strength`. A rule's `audit` holds `verdict`, `findings`, `notes`, `explanation`,
  `breaks`, `model`, `at`, `commit`, `path`, or is `null`.
- Gone: `gate`, `finished`, `tag`.

The status prints each `information` line where it printed the per-file warning before, and
`sync_status` prints K3's `NOTHING_LINE` lines after the table.

### K7. The same version of the code, and the package (`signoff`; read by `evidence`, `states`)

```python
# scripts/export/package.py
SCHEMA = 'purlin-package/4'
TOP_LEVEL = ('schema', 'met', 'rules', 'steps', 'audit', 'left', 'purlin_version',
             'project', 'version', 'tag', 'commit', 'runs', 'features', 'hand_checks',
             'warnings', 'fingerprint')

def only_records_between(project_root, older, newer):
    """True when `older` is `newer`, or an ancestor of it from which every commit up
    to `newer` changes only paths under `.purlin/`."""

def same_code(project_root, section_commit, head=None):
    """only_records_between(section_commit, head or HEAD); False for an empty commit."""

def project_version(project_root):
    """The VERSION file, package.json, pyproject.toml or the first root *.csproj, in
    that order; None where none states a version."""

def build(project_root, version): ...          # called by purlin:sign alone
def check_file(path): ...                      # called by purlin:sign --check FILE
def time_words(at): ...                        # '2026-10-01 12:17 UTC'
def run_lines(package): ...                    # K8's run lines, local first
def off_code(package, project_root): ...       # [(system words, source, [features])]
```

- `package.py` keeps no command line of its own. `purlin:export` and `release.py` go.
- `tag` is `signed/<version>`. `commit` is `HEAD`, stepping back over any commit that changed
  nothing but files under `.purlin/evidence/package/` (`package RULE-3`).
- `runs`, one per group of counted results sharing a source, a system, who ran them and a
  machine, local first, then by system:

```json
"runs": [{"by": "dana.dev@labconnect.example", "machine": "dana-laptop", "os": "linux",
          "source": "local", "at": "2026-10-01T12:17:13Z", "commit": "<40 hex>", "rules": 19}]
```

  A `ci` group reads `by` `a remote runner`.
- Each result gains `same_code` and `nothing_to_check`, a list of `{"proof", "reason"}`.
- A rule's audit carries no `strength`. `hand_checks[].checked` reads `in the sign-offs`.
- `project` is `project.project_name(project_root)`.
- Each rule gains `authors` (`package RULE-37`, and the owner's answer of 2026-10-01: the first
  person to write the wording, followed through a renumber):

```json
"authors": {"rule": {"written_by": "pat.product@labconnect.example", "commit": "<40 hex>"},
            "proofs": [{"id": "PROOF-1", "written_by": "...", "written_commit": "...",
                        "changed_by": "...", "changed_commit": "..."}],
            "tests": [{"file": "tests/test_login.py", "name": "test_valid_credentials_return_200",
                       "changed_by": "...", "changed_commit": "..."}]}
```

  `written` is the oldest commit whose diff adds the line's words, whatever id they stood
  under; `changed` is the commit `git blame` names for the line now; a test's `changed` is
  `wording.test_last_change`. Addresses are git's author emails.
- A result counts for a sign-off when its section is current, not `dirty`, and `same_code`
  holds. The status keeps counting a result while nothing its feature covers changed
  (decision 107).

### K8. The sign-off (`signoff`; read by `words`, `docs`, `team`, `setup`)

`sign.py [--version <version>] [--show | --answers FILE | --check FILE] [--project-root DIR]`.
Exit 0 signed, shown, checked and matching, stopped, or declined; 1 refused or not matching;
2 a command line of the wrong shape. `--release` goes.

**Refusals**, in this order, one line each, nothing written, exit 1:

```python
NO_SIGNOFF_WORK = ('No sign-off: the working tree holds changes that are not committed. '
                   'Commit them, run purlin:test --all --commit, then purlin:sign.')
NO_SIGNOFF_EVIDENCE = ('No sign-off: the evidence is written and not committed. Run '
                       'purlin:test --commit, then purlin:sign.')
NO_VERSION = ('No version: nothing in this project states one. Run purlin:sign --version '
              '<version>, or write it to a VERSION file.')
NO_SIGNOFF_ELSEWHERE = ('No sign-off: %s is at %s, which this checkout does not hold. '
                        'Pull, then run purlin:sign.')
NO_SIGNOFF_MOVED = ('No sign-off: %s is at %s, and the code has changed since. To sign this '
                    'code, name a new version: purlin:sign --version <version>.')
NO_SIGNOFF_NOT_THIS_CODE = ('No sign-off: these results were not taken on this version of '
                            'the code, %s: %s. Run %s, then purlin:sign.')
NO_SIGNOFF_FAILING = ('No sign-off: %s at %s: %s. Run purlin:status to see what is left, '
                      'then purlin:sign.')
NO_SIGNOFF_BEHIND = ('No sign-off: %s holds %s that %s does not, as this checkout last '
                     'fetched it. Pull, then run purlin:sign.')
ALREADY_SIGNED = '%s has already signed %s over this package; nothing was written.'
NOT_MADE = 'The sign-off commit was not made: %s. Nothing was signed; run purlin:sign again.'
```

`NO_SIGNOFF_NOT_THIS_CODE` fills `HEAD`'s sha7, then `sample_age, stability on Linux/Unix;
visit_window on Windows`, then `purlin:test --all --commit`, `purlin:test --remote` or both
joined ` and `. `--show` needs no key; the walk and `--answers` print the `No key to sign with`
block of `signatures RULE-17` after the refusals and before their first line.

**The walk** stops only at hand checks (`signatures RULE-114`):

```
Tests run by dana.dev@labconnect.example on dana-laptop at 2026-10-01 12:17 UTC on 1cf829e: 19 rules on Linux/Unix.
Signing 0.1.0 at 1cf829e.
  19 rules on Linux/Unix: 19 pass their tests, 1 has a hand check.
  The audit: 17 strong, 1 weak, 1 not audited.
The audit's findings: 1 weak. list / go on:
```

```python
RUN_LINE = 'Tests run by %s on %s at %s on %s: %s on %s.'
RUN_REMOTE_LINE = 'Tests run by a remote runner at %s on %s: %s on %s.'
OVERVIEW = 'Signing %s at %s.'
OVERVIEW_RULES = '  %s on %s: %s, %s.'   # '1 has a hand check' | '2 have a hand check' | 'no hand check'
OVERVIEW_AUDIT = '  The audit: %d strong, %d weak, %d not audited.'   # left out where no rule was audited
AUDIT_ASK = "The audit's findings: %s. list / go on: "                # asked only where a rule reads weak
AUDIT_LIST = '  %s %s   %s'                                           # feature, RULE-N, one finding per line
AUDIT_AGAIN = 'go on: '
STOP_HEAD = '%s %s   hand check'
HAND_ASK = '%s %s   what did you see, in one line, or Enter for no note, or stop: '
NO_NOTE = 'no note'
STOPPED = ('Stopped at %s %s: nothing was signed. After the fix, run purlin:test --all '
           '--commit, then purlin:sign.')
SIGN_ASK = 'Sign the evidence package for %s as %s? [y/N] '
NOT_SIGNED = 'Nothing was signed.'
SIGNED_AS = 'Signed %s as %s with the key ending ...%s.'
TAGGED = 'Tagged %s at %s.'
SIGNED_PUSH = 'Push the branch and the tag: git push origin %s %s'
TAG_STAYS = '%s stays at %s; this sign-off is added after it. Push it: git push origin %s'
SHOW_NEXT = 'Answer each stop, then run purlin:sign --answers <file>.'
MATCHES = 'The package matches its fingerprint.'
NO_MATCH = 'The package does not match its fingerprint: %s.'
```

On a detached `HEAD` the branch is left out of both push lines. `--answers` takes
`{"audit": "list" | "go on", "stops": {"<feature> RULE-N": {"answer": "note", "note": "..."} |
{"answer": "stop"}}, "sign": true}`; an empty `note` is recorded as `no note`.

**Signing.** The first sign-off of a version is one signed commit, `sign(<version>): <email>`,
carrying `.purlin/evidence/package/<version>.json` and
`.purlin/evidence/package/<version>.signoffs/<signer slug>.json`, and `signed/<version>` is
written on it with the message `Signed <version>.\n\nCommit: <the package's commit>\n`. A later
sign-off adds its own file alone. After it signs, `purlin:sign` calls `report_data.refresh`
(`purlin_report RULE-41`).

**The sign-off file, format 15**: `package_hash` is the fingerprint of the package `HEAD`
holds for the version; `shown` holds `overview`, `runs`, `hand_checks` (each stop walked) and
`audit_list_opened`; `notes` holds every note typed; no answer word. `one_by_one` and `in_list`
go.

`signatures.py` keeps `load_signoffs`, `counts`, `key_fingerprint`, `signer_slug`,
`signoffs_dir`, `package_rel` and `committed_fingerprint` with today's signatures. Moved into
`sign.py` or `package.py` from `release.py`: `tag_exists`, `write_tag`, `uncommitted_work`,
`behind_host`, `behind_words`, `NO_TAG_GIT`.

### K9. The audit (`audit`, `spot`; called by `run`)

`purlin:audit` runs when a person asks; nothing waits on it. `purlin_run.py --audit` runs the
tests as now, then calls:

```python
# scripts/review/audit_run.py   (lane audit)
def run(project_root, features, selected, again=False, out=None):
    """For each rule the audit reads (ai_audit RULE-1; `again` reads every passing rule):
    the spot tests, then one planted bug per proof that needs one, then the model's
    reading. Writes one audit.rules entry per rule read, through evidence.write_audit;
    writes .purlin/runtime/audit_run.json; prints the findings, the cost line and, last,
    the share. Returns 0, or 1 when a planted bug stopped it (planted_bug RULE-6)."""

# scripts/review/plain_checks.py   (lane spot, no model)
CHECKS = ('The test checks nothing', 'The check cannot fail', 'The test swallows the error',
          'The test checks the code against itself', 'The test replaces what it is testing',
          'The test never checks the result the proof expects')
NOT_READ = '%s is not read in %s tests.'                 # check, 'shell'
def check(project_root, feature, proof, test):
    """[(check, finding)] for one tied test, from its source and the proof's words.
    `proof` is {'id', 'text'}; `test` is {'file', 'name', 'source'}. A check the test's
    language cannot be read for is given as (check, None)."""

# scripts/review/targeted_break.py   (lane spot)
STOPPED = ('The audit stopped: %s changed while a break ran. Nothing in the project was '
           'written by the audit.')
SURVIVED = '%s: the test still passes when %s:%d reads "%s"'   # PROOF-N, file, line, the changed line
class ProjectChanged(Exception): ...                    # carries the path; audit_run prints STOPPED
def break_proof(project_root, feature, proof, tests, scope_files, ask):
    """One planted bug for one proof. `tests` is the proof's own tied tests. `ask(request)`
    is given {'feature','rule','rule_text','proof','proof_text','tests','files'} and
    answers the model's text, or raises ModelUnreachable(reason).
    Returns {'proof','file','line','before','after','result','why','finding'}:
    result 'caught' | 'survived' | 'not made'; finding is SURVIVED filled, or None."""

# scripts/review/ai_audit.py   (lane audit)
AUDIT_PARALLEL = 4
class ModelUnreachable(Exception): ...
def ask_for_bug(project_root, request): ...   # the `ask` audit_run hands break_proof
def break_key(test_source_hash, code_part): ...   # sha256 of the two, joined by a line feed
```

- **The model's answer to the planted bug's request** is exactly

  ```
  file: src/age.py
  before:
  <the exact lines>
  after:
  <the lines>
  ```

  or `no break: <why>`. Anything else is `not made`, `why` `the answer named no change`.
- **Where the bug is planted.** A copy of the project made from
  `git ls-files -co --exclude-standard -z` under `tempfile.mkdtemp(prefix='purlin-break-')`.
  The change is an exact replacement of `before` with `after` that must match once, in a file
  the feature's `> Scope:` reaches. Every write goes through one function that refuses a path
  not under the copy. The proof's own tests run there through their suite's own `run` command,
  read with `markers.read_suites`, `purlin_run.run_suite` and `purlin_run.marker_results`,
  whose signatures `run` and `evidence` keep. The copy is removed in a `finally`.
- **What the result reads.** `survived` only when every one of the proof's own tests reads
  `pass` with the bug in place. Any other outcome, a failure, an error, a test that could not
  be collected or one that ran past its limit, reads `caught` (decision 110: "a test that still
  passes is weak"). `--arm-timeout` bounds the run.
- **The guard.** Before and after each bug the module takes `git status --porcelain -z` and
  the hash of every file it lists; a difference raises `ProjectChanged`.
- **Which proofs.** One bug per proof whose `break_key` differs from the one its last entry
  holds, or that has none. No bug for an anchor's proof or a `@manual` proof.
- **The verdict** (`ai_audit RULE-33`): `weak` when a spot test fires on one of the rule's
  tests or a planted bug survived; else `strong`. The model's reading is asked once per rule,
  after the spot tests and the bugs, sets no verdict, and is stored as `explanation`; `notes:`
  lines are stored as `notes`. `undecided` and `settled:` go.
- **The cost, so the measuring of decision 116 can be done.** `audit_run.run` writes
  `.purlin/runtime/audit_run.json`, which git ignores:

  ```json
  {"at": "2026-10-01T12:05:00Z", "commit": "<40 hex>", "calls": 31, "cost_usd": 1.87,
   "seconds": 412,
   "rules": {"login RULE-2": {"calls": 3, "cost_usd": 0.19, "seconds": 41,
                              "breaks": {"PROOF-2": "survived"}}}}
  ```

  `cost_usd` is the sum of `total_cost_usd` in each answer of `claude -p --output-format json`,
  and `null` where an answer carried none. The planted bugs themselves are in the evidence
  (`breaks`), so a person can read each one and say whether it was relevant.
  `ai_audit.py`'s own reading and asking still write nothing under `.purlin/`
  (`ai_audit RULE-12`).
- **No real model in a test.** Every test of `spot` and `audit` installs its own
  `dev/fake_claude.py` with the answers it needs and asserts `shutil.which('claude')` resolves
  under its own `tmp_path` before the first call.

### K10. The run's command line (`run`)

```
Usage: purlin_run.py [--feature NAME ... | --all] (--test [--remote [--commit-runner]] [--commit] | --ci) [--arm-timeout SECONDS] [--project-root DIR]
       purlin_run.py [--feature NAME ... | --all] --audit [--commit] [--arm-timeout SECONDS] [--project-root DIR]
```

- Exit 0, 1 or 2 as `run_script RULE-98`, `RULE-103`, `RULE-102`, `RULE-11`, `RULE-48` and
  `RULE-12` say. A test comment to correct changes no exit code (`run_script RULE-96`); it
  makes `Tests: not met`.
- `--release` goes, with `RELEASE_RUNS_ALL` and `_release`.
- `--audit`: after the tests, `audit_run.run(project_root, features, selected,
  again=args.all, out=...)`; the run's exit code is the tests' (`run_script RULE-48`), or 1
  where `audit_run.run` answered 1.
- `--remote`: `remote.run_remote(project_root, args)`, where `args.commit_runner` is true for
  `--commit-runner`. Everything `run_script RULE-97` prints is printed by `remote` (K11).
- `--commit-runner` without `--remote` exits 2:
  `purlin: --commit-runner belongs to --test --remote. Run purlin:test --remote --commit-runner`.
- After the `Markers:` line, each `wording.stale_comments` entry's `text`.
- The root `conftest.py` keeps `collect_ignore = ['dev/fixtures']` and its first paragraph,
  and loses everything about mutmut.

### K11. The runner, written on first need (`remote`)

```python
RUNNER_WRITTEN = 'Purlin wrote %s, the runner for %s, to run the proofs tagged for %s:'
RUNNER_NEXT = 'Commit it and run: purlin:test --remote --commit-runner'
RUNNER_COMMITTED = 'Committed %s, the runner for %s.'

def ensure_runner(project_root, commit=False, out=None):
    """`(path, written)`. With no runner file for origin's git host: write it, print
    RUNNER_WRITTEN, the file, RUNNER_NEXT. With commit=True: commit the file alone as
    `ci: the Purlin runner for <GitHub|Azure DevOps>` and print RUNNER_COMMITTED."""

def run_remote(project_root, args=None): ...
```

`run_remote` calls `ensure_runner` first. Where it wrote the file and `args.commit_runner` is
false, it pushes nothing and returns 0. The host is `workflow.host_of(project_root)`, read from
the remote each time. Both templates and `.github/workflows/purlin.yml` start on a push to
`run/**` alone (`host RULE-53`).

### K12. Drift and the tools (`anchors`, `mcp`; read by `words`)

- `drift` takes no role. The report carries exactly `since` and `view`; the view carries
  exactly `anchors_behind`, `comments_changed`, `default_branch`, `lines`, `numbers_twice`,
  `proofs_added`, `proofs_changed`, `proofs_moved`, `rules_added`, `rules_changed` and
  `rules_removed` (`drift RULE-42`). The MCP `drift` tool loses its `role` argument.
- `references/drift_criteria.md`: `> Criteria-Version: 13`, one view.
- Every tool call names `project_root`. A call that names none is refused
  (`server RULE-37`): `<tool> needs project_root: pass the top folder of the git checkout you
  are working in.` Every skill and the agent definition pass it on each call, and every test
  that calls a tool through the server passes it.

### K13. The dashboard's data and its page (`dashboard`; called by `states`, `run`, `signoff`)

`report_data.refresh(project_root, data=None, generated_by='sync_status')` keeps its signature.
From round 2 it also writes `<project_root>/purlin-report.html` where that file is absent or
its bytes differ from the plugin's `scripts/report/purlin-report.html`
(`purlin_report RULE-76`). The page reads schema 14 and K6's keys. The header line is built
from `branch`, the first 7 characters of `commit`, and `generated_at`.

### K14. Formats

| File | Now | After | Why | Lane |
|---|---|---|---|---|
| `evidence_format.md` | 7 | 8 | a section's `commit` is its code; `email`; retention over the same code; `test_hash` per test; `audit.mutation` gone; `nothing to check` and `reason`; an audit entry's `breaks` and `explanation`; `undecided` gone; the table gone | `evidence` |
| `marker_format.md` | 3 | 4 | each report format's skip reason; `nothing to check:` | `evidence` |
| `package_format.md` | 7 | 8 | `met` for `state`; `gate`, `mutation_engine`, `strength` gone; `runs`; `same_code`; `nothing_to_check`; `authors`; written and checked by `purlin:sign`; schema `purlin-package/4` | `signoff` |
| `signature_format.md` | 14 | 15 | `shown` holds `overview`, `runs`, `hand_checks`, `audit_list_opened`; `no note`; the package in the same commit | `signoff` |
| `anchor_format.md` | 11 | 12 | "for every X in the project, Y holds"; the `nothing to check:` skip; the status and drift check the source and do not pull | `anchors` |
| `spec_format.md` | 21 | 22 | `> Scope:` and every proof rule stated without a gate; `@manual` reads `checked at sign-off`; a scope naming a file not yet written | `mcp` |
| payload `schema_version` | 13 | 14 | K6 | `states` |
| `drift_criteria.md` | 12 | 13 | one view | `anchors` |

Each is bumped in the same commit as the code that changes the parsing or the emission, as
`CLAUDE.md` says. `CLAUDE.md`'s own format table and one-home table are `words`'.

### K15. Deleted outright

Each lane greps its own files for these and leaves none outside `RELEASE_NOTES.md`; the
upgrade keeps what a 0.9.5 project needs.

- **The gate (108):** `gate.py`, the `gate` setting, `--gate`, setup's gate question,
  `GATE_*`, `NOT_A_GATE*`, `STRONG_RETIRED`, `AT_PASSED`, every line that depends on a gate,
  the dashboard's `gate:` chip, `references/hard_gates.md`.
- **The release step (106):** `release.py`, `dev/test_tag.py`, `--release`, `passed/<version>`,
  the package's `state`.
- **`.purlin/tests.md` (106)**, its writer and every mention.
- **Mutation testing (109):** `scripts/run/mutation/**`, `dev/test_mutation_adapters.py`,
  `dev/fixtures/mutation/**`, `setup.cfg`, `mutation_engine`, `--mutation`, the setup question,
  the mutmut config setup writes, `--ignore=mutants` in a suggested command, every strength
  line and reason, `audit.mutation`.
- **`purlin:export` (109):** `skills/export/`, `dev/test_skill_export.py`, `package.py`'s
  command line.
- **Settings `audit_parallel`, `ci`, `project_name` (109).**
- **Drift's roles (109)**, their views, and every line the status already prints.
- **The walk's stops for weak and unaudited rules, and the strong list (109).**
- **Setup's runner file and the runner's run on a pushed `signed/*` tag (109).**
- **The upgrade's steps for a 0.10 build (109).**
- **Dashboard (109):** the filter buttons, the live age and the reload, the links to the git
  host, a rule unfolded under its row, the tabs, `Data from <time>` (decision 115's header line
  holds in its place).
- **The audit's `settled:` line, `undecided`, and test strength shown to the model (110).**
- **Decision 101's `does not apply` (103).**

One suggested command still holds the word: `run_script PROOF-126`, `PROOF-221` and `PROOF-262`
fix `python3 -m pytest --ignore=mutants {files} --junitxml={report}`. The proofs hold; `run`
builds to them and lists it in its report for the owner.

### K16. The helpers, frozen after the base commit

| Helper | After the base commit |
|---|---|
| `dev/run_project.py` | `_project(tmp_path, tests=None)`, `_pytest_project(tmp_path, body=None)`; the settings hold `version` and `tests` |
| `dev/mcp_project.py` | `Project(spec=SPEC, extra_config=None)`; `evidence(...)` takes no `strength` and writes no `audit.mutation` |
| `dev/sign_project.py` | `Project(spec=SPEC, config=None)`, `signing_project(signer='jane@acme.com')`; no import of `gate`; `evidence(...)` takes no `strength` |
| `dev/fake_claude.py` | `DEFAULT_ANSWER = 'no break: the fake model plants no bug'`; `install`, `calls`, `most_at_once` as they are |
| `dev/conftest.py` | as it is |
| `dev/skill_checks.py` (owned by `words`) | gains `must_name(skill, commands=(), paths=())`, a list of problems each reading `<skill> does not name <x>`, as `skill_audit PROOF-56` and `skill_status PROOF-38` quote |

A lane that needs another helper writes it in its own test file.

## 4. Tests: delete, rewrite, add

Counts are test comments, from appendix A's script at `20a054551`. "Gone" names a proof or a
spec no spec has. "Reworded" names a proof whose wording changed after the test last changed.
"To add" is a proof no comment names.

| Lane | Files | Gone | Reworded | To add |
|---|---|---|---|---|
| `evidence` | `test_evidence_writer.py` 53, `test_evidence_reader.py` 16, `test_fingerprint.py` 28, `test_reports.py` 72 | 169 | 13 | 7: `evidence_writer` 90 to 94; `reports` 115, 117 |
| `states` | `test_states.py` 105, `test_summary.py` 20, `test_backing_tests.py` 2, `test_failing.py` 2 | 129 | 40 | 16: `states` 265, 266, 269, 270, 271, 274, 276 to 280; `summary` 48, 50, 52, 53, 54 |
| `signoff` | `test_signatures.py` 30, `test_export.py` 27; `test_tag.py` deleted whole (16) | 57 | 46 | 30: `signatures` 223 to 230, 232 to 238, 240 to 243; `package` 65 to 72, 74, 75, 76 |
| `spot` | new files | 0 | 0 | 33: every proof of `plain_checks` (20) and `planted_bug` (13) |
| `audit` | `test_ai_audit.py` 54, `test_ai_audit_tests_named.py` 3 | 57 | 13 | 10: `ai_audit` 95 to 100, 102, 103, 104, 106 |
| `run` | `test_run_script.py` 161; `test_mutation_adapters.py` deleted whole (90) | 161 | 19 | 5: `run_script` 270 to 274 |
| `remote` | `test_host.py` 31, `test_host_pathspec.py` 3, `test_remote.py` 13, `test_consumer_ci.py` 32 | 79 | 23 | 4: `host` 140 to 143 |
| `anchors` | `test_upstream.py` 20, `test_drift.py` 49, `test_security.py` 68 | 137 | 28 | 7: `upstream` 60; `drift` 82 to 86, 88 |
| `setup` | `test_init_scaffold.py` 111, `test_init_update.py` 108, `test_init_e2e_wiring.sh` 1 | 220 | 31 | 5: `scaffold` 171, 172, 173; `update` 162, 163 |
| `mcp` | `test_mcp_server.py` 28, `test_config_engine.py` 20, `test_specs_reader.py` 18, `test_schema_spec_format.py` 50, `test_purlin_version.py` 16, `test_purlin_output.py` 1 | 133 | 11 | 11: `server` 164, 166 to 169; `config_engine` 45, 48 to 51; `purlin_output` 7 |
| `words` | the ten `test_skill_*.py` kept, 208; `test_purlin_agent.py` 11; `test_skill_export.py` deleted whole (16) | 219 | 4 | 16: `skill_audit` 56, 59; `skill_build` 51; `skill_drift` 43, 46; `skill_sign` 63, 64; `skill_spec` 62; `skill_spec_from_code` 167; `skill_status` 37, 38, 39; `skill_test` 52, 55; `purlin_agent` 49, 50 |
| `dashboard` | `test_purlin_report.py` 106, `test_purlin_report_board_layout.py` 15, `test_report_refresh.py` 4 | 125 | 28 | 9: `purlin_report` 223, 225, 227 to 233 |
| `docs` | `test_purlin_docs.py` 10 | 10 | 1 | 8: `purlin_docs` 21, 22, 24; `install` 1 to 5 |
| `team` | new file | 0 | 0 | 1: `collaboration` 1 |
| Total | | 1,496 | 257 | 162 |

The 122 comments in the three files deleted whole are the rest of the 1,621; 3 more are sample
text inside `test_purlin_docs.py` and go with the tests that hold them.

**How a lane works through a comment that is gone.** A test whose every comment is gone is
looked at once: where it shows, as it is or with a change, a proof of the lane's specs that has
no test, it is changed to show that proof and given that proof's comment; otherwise it is
deleted, with any helper only it used. A test that also carries a comment that is right keeps
that comment and loses the gone one. No test is kept for a proof no spec holds, and none is
written to show that a removed thing is absent.

## 5. The test comments to correct

1,621 comments name something no spec has, and 257 name a proof whose wording changed after the
test last changed. Section 4's table gives each lane its share.

**How a lane finds them.** It saves appendix A's script in its scratch folder and runs it over
the test files it owns, at the start and before its last commit:

```
python3 <scratch>/comments.py dev/test_states.py dev/test_summary.py
```

Each line names the file, the line, the feature, the proof, and `gone` or `reworded` with the
commit the test last changed in and the wording the proof had then. The last line counts them.
At the end it must print `0 gone, 0 reworded`.

**The rule.** The test is changed to show the proof. The proof is never reworded to fit the
test, and no lane changes a file under `specs/`.

For each reworded comment the lane reads the test against the proof as written now:

- **Shows it.** The test already does what the proof says and checks the values it names. The
  test is changed so it states it: its name, its docstring or an assertion carries the proof's
  values. A change to the test's own lines clears the comment.
- **Does not show it.** The test is fixed: the starting situation, the action and each value the
  proof names are what the test sets up, does and asserts.
- **Moved.** The old wording now stands under another id of the same spec: the comment is moved
  there, and the id it left is treated as a proof to add.

Each lane lists every one in its report as
`<file>:<line> <feature> <PROOF-N> stated | fixed | moved`, with one line on what changed for
each `fixed`.

**Checked by integration**, in each round: appendix A's script over every `dev/test_*` file
that round's lanes own prints `0 gone, 0 reworded`; `git diff --stat d115/base..HEAD -- specs/`
names nothing after the base commit; a reviewer agent that fixed none of them reads every
`fixed` diff and every tenth `stated` against its proof and lists each it disagrees with, and
those are fixed before the sweep.

## 6. Lines a person reads

No emoji. Name first, fix last, exact numbers, as `references/writing_style.md` and decisions
94 to 115 have them.

### Fixed by a spec, quoted

| Where | What it says | Held by |
|---|---|---|
| The dashboard's header | `main at a1b2c3d, written 06:42 EDT` in a browser set to `America/New_York`, `written 10:42 UTC` in one set to `UTC`; its hover `2026-10-01 06:42 EDT (10:42 UTC)` | `purlin_report RULE-77`, `PROOF-232` |
| A tool call that names no folder | `sync_status needs project_root: pass the top folder of the git checkout you are working in.` | `server RULE-37`, `PROOF-166` |
| A spec ahead of its code | `states: 3 files its scope names are not written yet: facts.py, project.py, wording.py. Run purlin:build states, or correct the path with purlin:spec states.` and `login: 1 file its scope names is not written yet: src/gone.py. Run purlin:build login, or correct the path with purlin:spec login.` | `states RULE-123`, `PROOF-279`, `PROOF-280` |
| The two facts, in the terminal | `Tests: met`, `Tests: not met`, `Sign-off: signed 0.1.0 at a1b2c3d`, `Sign-off: signed 0.1.0, 4 commits since`, `Sign-off: signed 0.1.0, 1 commit since`, `Sign-off: not signed` | `summary RULE-20` |
| The two facts, on the dashboard | the boxes `Tests` reading `met` or `not met`, and `Sign-off` reading `signed 0.1.0 at a1b2c3d`, `signed 0.1.0, 4 commits since` or `not signed` | `purlin_report RULE-7` |
| The status's first line | `Purlin status: labconnect, plugin 0.10.0` | `summary PROOF-48` |
| The status's last line | `Every rule passes its tests on the committed evidence. To sign it: purlin:sign` | `summary RULE-18` |
| Results not committed | `1 feature whose results are not committed: purlin:test --commit`, `2 features whose results are not committed: purlin:test --commit` | `summary RULE-21` |
| The sentence | `50 rules. 50 pass their tests. The audit found 42 of 50 rules strong (84%).` | `summary PROOF-43` |
| The walk's opening line | `Tests run by dana.dev@labconnect.example on dana-laptop at 2026-10-01 12:17 UTC on 1cf829e: 19 rules on Linux/Unix.` | `signatures PROOF-227` |
| The walk's next lines | `Signing 0.1.0 at 1cf829e.`; `  19 rules on Linux/Unix: 19 pass their tests, 1 has a hand check.`; `  The audit: 17 strong, 1 weak, 1 not audited.`; `The audit's findings: 1 weak. list / go on: ` | `signatures PROOF-209`, `PROOF-232`, `RULE-115` |
| A hand check's stop | `login RULE-2   hand check`; `login RULE-2   what did you see, in one line, or Enter for no note, or stop: `; `  Linux/Unix: passed on dana-laptop; nothing to check for PROOF-3: this project has no screens` | `signatures PROOF-211`, `PROOF-242` |
| A hand check, everywhere else | `checked at sign-off`; `noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, 4 commits since: the tube is red` | `states RULE-16`, `RULE-116` |
| The sign-off's refusals | `No sign-off: the evidence is written and not committed. Run purlin:test --commit, then purlin:sign.`; `No sign-off: these results were not taken on this version of the code, <sha7>: audit on Windows. Run purlin:test --remote, then purlin:sign.`; `No sign-off: 1 rule does not pass at <sha7>: login RULE-2. Run purlin:status to see what is left, then purlin:sign.`; `No sign-off: signed/2.1.0 is at <sha7>, which this checkout does not hold. Pull, then run purlin:sign.`; `No sign-off: signed/2.1.0 is at <sha7>, and the code has changed since. To sign this code, name a new version: purlin:sign --version <version>.`; `No sign-off: origin/main holds 1 commit that <sha7> does not, as this checkout last fetched it. Pull, then run purlin:sign.` | `signatures PROOF-223`, `226`, `206`, `224`, `225`, `207` |
| After a sign-off | `Signed 0.1.0 as jane@acme.com with the key ending ...<4 characters>.`; `Tagged signed/0.1.0 at <sha7>.`; `Push the branch and the tag: git push origin main signed/0.1.0`; `signed/0.1.0 stays at e0deb2e; this sign-off is added after it. Push it: git push origin main` | `scaffold PROOF-119`, `signatures PROOF-236`, `233`, `234` |
| Checking a package | `The package matches its fingerprint.`; `The package does not match its fingerprint: the file is not UTF-8 JSON.` | `signatures RULE-122`, `package PROOF-45` |
| A test comment to correct | `tests/test_login.py:1 names login PROOF-4, whose wording changed after the test was last changed in <sha7>: it read "A" and now reads "B". Run purlin:build login to make the test show it; the line clears once the test changes.`; ending instead `Its old wording is now PROOF-6: move the comment there.` | `drift PROOF-75`, `PROOF-76` |
| Nothing to check | `security_no_dangerous_patterns RULE-3 passes with nothing to check here: this project has no screens.` | `states RULE-115` |
| The spot tests' findings | the six lines of `references/review_criteria.md`, "Heuristic spot tests", as `tests/test_age.py::test_age: the test checks nothing.`; `The test replaces what it is testing is not read in shell tests.` | `plain_checks RULE-1` to `RULE-7` |
| A planted bug | `PROOF-1: the test still passes when src/age.py:12 reads "return 0"`; `The audit stopped: src/age.py changed while a break ran. Nothing in the project was written by the audit.` | `planted_bug RULE-2`, `RULE-6` |
| The audit's last line | `The audit found 4 of 5 rules strong (80%).` | `ai_audit RULE-35` |
| The runner | `Purlin wrote .github/workflows/purlin.yml, the runner for GitHub, to run the proofs tagged for Windows:`; `Commit it and run: purlin:test --remote --commit-runner`; `Committed .github/workflows/purlin.yml, the runner for GitHub.` | `run_script RULE-97`, `host RULE-54` |
| Settings | `.purlin/config.json carries gate, mutation_engine, which this version does not read. Run purlin:init --update.`; `.purlin/config.json carries colour, which this version does not read. Remove it from .purlin/config.json.`; `gate is not a setting; .purlin/config.json holds version and tests. Nothing was saved.` | `config_engine PROOF-50`, `51`, `server PROOF-164` |
| Setup | `Commit the files setup wrote? [y/N] `; the commit `chore(init): set up Purlin` | `scaffold RULE-83`, `RULE-68` |
| A pulled anchor's stray line | `security_baseline: its source, https://github.com/acme/policies.git, carries > Scope:, which Purlin does not read on an anchor, so the line is read as nothing. Ask the owners of https://github.com/acme/policies.git to take it out, then run purlin:anchor sync security_baseline.` | `schema_spec_format PROOF-78` |

### Words chosen for the owner to read

No spec fixes these. Each lane uses them as written and lists any other line it had to choose
in its report.

| Where | What it says | Lane |
|---|---|---|
| The dashboard's header on a detached `HEAD` | `detached at a1b2c3d, written 06:42 EDT` | `dashboard` |
| The dashboard, a spec ahead of its code | the line of `states RULE-123`, whole, as a notice in the neutral tone, below the warnings and above the boxes; no heading | `dashboard` |
| The audit's cost, the line before its last | `The model was asked 31 times for 12 rules: $1.87 in all, $0.16 a rule.`; for one, `The model was asked 1 time for 1 rule: $0.16 in all, $0.16 a rule.`; left out where no answer carried a cost | `audit` |
| A planted bug that could not be made | `PROOF-1: no bug was planted: the proof names no value the code computes.`, printed and not a finding | `audit` |
| The model not reached for a planted bug | `not made`, with the `why` `claude is not on PATH`, `claude exited with an error` or `claude timed out after 300 s` | `spot`, `audit` |
| `--commit-runner` alone | `purlin: --commit-runner belongs to --test --remote. Run purlin:test --remote --commit-runner` | `run` |
| The sign-off with uncommitted work | `No sign-off: the working tree holds changes that are not committed. Commit them, run purlin:test --all --commit, then purlin:sign.` | `signoff` |
| The install test with no `claude` | `claude is not installed here` | `docs` |
| The agent definition, worktrees (`purlin_agent RULE-19`) | `After you merge work from a worktree, run purlin:status in the main checkout, so its status and dashboard describe the merged work.` | `words` |
| The agent definition and each skill, the folder | `Pass project_root on every Purlin tool call: the top folder of the git checkout you are working in.` | `words` |
| `docs/working-together.md`, the paragraph of `purlin_docs RULE-16` | `Each checkout of a repository, a worktree included, has its own results, its own status and its own dashboard. Nothing is shared until the work is merged. After you merge work from a worktree, run purlin:status in the main checkout: that brings its status and dashboard up to date.` | `docs` |
| `references/writing_style.md`, the two sentence shapes that name a gate | `*Evidence*: what a run leaves behind for each feature, one file per source.` and `Run it at the start of a session and before a sign-off.` | `words` |
| `references/writing_style.md`, "Every output says what to do next" | its last sentence becomes `A command's ending names the command to run next; a project whose tests are met ends on purlin:sign.` | `words` |
| `CLAUDE.md`, "Releasing a new version", step 3 | `Run purlin:test --all --commit and purlin:test --remote, then purlin:sign. The first sign-off writes the signed tag signed/<version>.` | `words` |
| `RELEASE_NOTES.md` 0.10.0 | `**Two facts, no gate.** The status and the dashboard say whether the tests are met on the committed evidence, and whether this code is signed.`; `**The hand-off is run and commit**: purlin:test --all --commit, and purlin:test --remote for other systems.`; `**purlin:sign builds the evidence package and signs it**, at any time, in any project; it stops only at hand checks, whose note is optional, and refuses results not taken on this code.`; `**An anchor rule with nothing to check passes, and says so.**`; `**A test comment whose proof was reworded is caught** until the test changes.`; `**The audit runs heuristic spot tests, then plants one bug per changed proof** in a copy of the project and sees whether the proof's own test catches it; it reports the share of rules it found strong. Run it by hand; nothing blocks on it.`; `**The evidence package records who wrote and last changed each rule, proof and test**, from git.`; `**The dashboard names the branch and commit its data describes**, and its page is written with its data.`; `**A Purlin tool call names its folder**; a call that names none is refused with the fix.`; `**Cut:** mutation testing, purlin:export, the gate, the release step, .purlin/tests.md, drift's role views, setup's questions but one, and most settings.`; then K14's format numbers | `words` |

## 7. Integration, local, one agent

`export PATH=/opt/homebrew/opt/dotnet@8/bin:$PWD/.venv/bin:$PATH` throughout. No tag, no
`purlin:audit`, no `purlin:sign` against this repository. Never edit a number to make a sweep
green.

### Merging

Lanes own disjoint files, so a rebase never conflicts. For each lane, in the round's order:
`git rebase <the merged line> lane/d115-<lane>`, rerun that lane's own test files, then
`git merge --ff-only lane/d115-<lane>`.

- **Round 1 order:** `evidence`, `states`, `signoff`, `spot`, `audit`, `run`. The evidence
  shape is read by all; `wording.py`, `project.py` and the facts by `signoff` and `run`;
  `only_records_between` by `evidence` and `states`; the spot tests and the planted bug by
  `audit`; `audit_run` by `run`.
- **Round 2 order:** `remote`, `anchors`, `setup`, `mcp`, `words`, `dashboard`, `docs`, then
  `team` and `deck`. `mcp` deletes `gate.py` after `setup` stops importing it.

### Round 1

1. Merge in order. After each merge run the tests that lane listed as waiting on a lane now
   merged; fix what fails, to the contracts, in a commit of its own.
2. Section 5's three checks over round 1's files.
3. `bash dev/run_tests.sh`. **The target is 0 failed in the files round 1 owns**, but the
   tests that wait for round 2: `run_script PROOF-272` and `PROOF-273`, `states PROOF-58`,
   and any test of round 1 that sets a project up through `scaffold.py` and reads its settings
   file, each named in `round1.md`. Failures in files round 2 owns are expected (decision 116: a red sweep is acceptable
   until the build lands); they are listed by file and count in `dev/plans/d115-reports/round1.md`,
   which round 2's lanes read.
4. On the Mac, the tests that skipped in the cloud: `dev/test_reports.py` with `dotnet`, `go`
   and `npm`; `dev/test_signatures.py` and `dev/test_export.py` whole.
5. `git rm .purlin/tests.md`. Delete the untracked folders `scripts/ci`, `scripts/hooks`,
   `scripts/proof`.
6. Fast-forward `d115/base` to the merged line and push it. Round 2's lanes branch from there.
   Report the cloud spend so far, and apply section 2's rule for a short budget.

**What a round 2 lane may assume from round 1**, all merged in `d115/base`: K2's evidence
file; K3's reasons; `wording.py`, `project.py` and `facts.py` working; the status's opening
lines, kinds of work and last line; payload schema 14 with its eighteen keys;
`package.only_records_between` and `same_code`; `purlin:sign` with `--version`, `--show`,
`--answers` and `--check`; `purlin_run.py` with no `--release`, with `--commit-runner`, and
with `--audit` calling `audit_run.run`; `report_data.refresh` still called by `purlin:status`,
`purlin:test`, `purlin:audit` and `purlin:sign`. A round 2 lane may not assume: that
`gate.py` or `scripts/run/mutation/` is gone; that `server.py` refuses a call with no
`project_root`; that the settings warning of K1 is printed.

### Round 2

1. Merge `remote`, `anchors`, `setup`, `mcp`, `words`, `dashboard`, `docs`, as round 1's
   step 1.
2. Start `team` and `deck` on the merged line; merge them.
3. `dev/run_tests.sh` holds `dev/test_install.py` out of the default sweep and runs it with
   `--install`, since it starts the real `claude` and makes one model call (decision 111: as
   cheap as possible, and rerun only when what it covers changed). Integration makes that edit,
   and drops any mention of a deleted file from `dev/run_tests.sh` and `dev/suites.py`.
4. Section 5's three checks over every `dev/test_*` file.
5. K15's greps over `scripts/`, `skills/`, `agents/`, `references/`, `docs/`, `templates/`,
   `README.md`, `CLAUDE.md` and `dev/test_*`, empty outside `RELEASE_NOTES.md`,
   `scripts/init/update.py` and its test: `gate`, `--release`, `passed/`, `tests.md`,
   `mutation`, `mutmut`, `stryker`, `min_strength`, `audit_parallel`, `purlin:export`,
   `does not apply`, `settled:`, `purlin-package/3`, `hard_gates`.
6. `python3 dev/build_report.py`; commit the built page once.
7. `bash dev/run_tests.sh`: **0 failed**. Then `bash dev/run_tests.sh --install` once.
8. The Mac-only proofs, read in that sweep's output as run and passed, not skipped: the seven
   tagged `@env(macos)`; the `dotnet`, `npm` and `go` fixtures; the Python 3.9 proofs; the
   playwright tests.
9. The spot tests over this repository's own tests, with no model: every finding read, the
   test fixed or the check narrowed, both counts reported (the owner's wording in
   `d105-plan.md` section 7).
10. `python3 scripts/run/purlin_run.py --test --all`: `0 not tied`; no rule `failed`,
    `partial` or `no test`; no spec to repair; no test comment to correct; no warning; only
    rules to test on Windows left. Then the same with `--commit`.
11. **The dashboard, looked at** with playwright from `.venv`, headless, in the dark and the
    light theme, at 1500, 1024 and 390 pixels wide, on this repository's own data and on the
    three fixtures: the two boxes; the header line `<branch> at <commit>, written <hh:mm> <zone>`;
    `Back to the board`; the information notices; nothing of K15; no value split across two
    lines; no sideways scroll; neutral text at least 7 to 1.
12. `python3 dev/capture_doc_screenshots.py`: the two screenshots retaken from the rebuilt
    page; commit them.
13. The deck: read the live slides, render with `build_deck.py`, run `check_deck.py` and
    `check_overlap.py`, commit the pictures. Publishing waits for the owner.
14. `dev/plans/handoff.md`: decisions 100 to 116 built; the numbers of steps 7 and 10; the
    cloud spend; every line a lane chose, gathered from the reports; anything left unbuilt;
    what is left: the real-skills QA check on a fresh LabConnect-style project (decision 116),
    the measuring of the planted-bug audit against $0.10 a rule and 1 in 5 irrelevant
    (decision 116), the remote run on Windows, the owner's review.

### What only integration does

The base commit; every file section 2 lists under "No lane owns"; the generated dashboard page;
the doc screenshots; the deck's pictures; the Mac-only and tool-dependent proofs; the install
test's one real model call; the spot tests over this repository's own tests; `--test --all
--commit`; `handoff.md`.

## 8. Questions for the owner

**Q1. When does Purlin remind you to commit your test results?**

What it is for. The tests read `met` only when every rule passes on results that are committed.
So results a run wrote and nobody has committed yet are one more thing left to do, shown as a
line under `Left to do` with the command that commits them: `1 feature whose results are not
committed: purlin:test --commit`. The specs disagree on when that line shows. The rule for the
list says it shows whenever results are written and not committed. Six examples of a test run
say the list ends on the work still left on the rules, such as `1 rule to fix: purlin:build`,
with no reminder after it, though that run's results are not committed either. Both cannot be
built.

- **(a) Only when it is the last thing in the way, recommended.** The reminder shows once every
  rule passes its tests and nothing but the commit stops the tests reading `met`. While a rule
  fails, has no test or waits for a run, the list names that work alone. Consequence: the list
  stays short while you are fixing things, and the reminder arrives when it is the next step.
  The six examples stand as written, and one rule gains the words "once no other work stops the
  tests being met". The tests read `not met` until the commit, as now.
- **(b) After every run whose results are not committed.** The reminder shows beside whatever
  else is left. Consequence: every run without `--commit` ends on one more line, also while a
  test is failing, and the six examples are reworded to end on it.

The plan is written to (a). Under (b), the base commit rewords `run_script PROOF-5`, `PROOF-7`,
`PROOF-9`, `PROOF-103`, `PROOF-105` and `PROOF-109` in place of `summary RULE-21`.

No other question. Section 10 lists the calls the plan made and the decision each rests on.

## 9. Where the specs disagree, and the base commit's corrections

| Where | What disagrees | The correction |
|---|---|---|
| `states RULE-27` and `PROOF-31` against `purlin_report RULE-77` and `PROOF-233`, and `states RULE-123` and `PROOF-280` | The payload is fixed at sixteen keys, none of them a branch or a list of information lines. The dashboard's header needs the branch the data was written for (decision 115), and a spec ahead of its code must show "among the information, not among the warnings" (decision 113). | `states RULE-27` names eighteen keys, adding `branch` after `version` and `information` before `warnings`; `PROOF-31` reads "the eighteen". |
| `schema_spec_format RULE-38` against `states RULE-123`, `PROOF-280` and decision 113 | `RULE-38` still lists "a `> Scope:` entry finding no file in git where another entry does" among the mistakes warned of with `Run purlin:spec <name>.` Decision 113 replaced that warning with one line of information naming `purlin:build` first. | That clause is taken out of `schema_spec_format RULE-38`. |
| `summary RULE-21` and `RULE-23` against `run_script PROOF-5`, `7`, `9`, `103`, `105`, `109` | Q1 of section 8. | Under (a): `summary RULE-21` gains "once no other work stops the tests being met". Under (b): the six proofs are reworded. |
| `purlin_report RULE-76` against `update RULE-54` | `RULE-76` writes the page "where the project's copy differs from the plugin's" and says nothing of a project with no page. The page is ignored by git, so every fresh clone has none. `update RULE-54` says a project with no page is not given one, by the upgrade. | No spec change. K13 reads an absent page as differing, so the first `purlin:status` in a fresh clone writes it; `update RULE-54` holds for the upgrade alone. |

Also noted, with nothing to correct: `host RULE-54` and `run_script RULE-97` hold the same
behaviour in two specs, so `host PROOF-140`, `141`, `143` and `run_script PROOF-272`, `273` are
proven twice, by two lanes; `run_script PROOF-126`, `221` and `262` fix a suggested pytest
command that still carries `--ignore=mutants`, a leftover of the cut mutation testing, which
the owner may want taken out of those three proofs.

## 10. Calls this plan makes

- **The round 1 sweep is not 0 failed.** Round 2's test files still describe decision 103
  against a core that has moved, so they fail until round 2 (decision 116: red is acceptable
  until the build lands, and no test is skipped). Round 1's own files reach 0 failed but the
  waits for round 2 that section 7 names.
- **`d115/base` moves once**, to round 1's merged line, so round 2 builds on the core.
- **One lane for the package and the sign-off.** Every proof of `package` is shown through
  `purlin:sign`, so two lanes would each wait on the other.
- **`wording.py`, `project.py` and `facts.py` are `states`'**, because `states`' `> Scope:`
  names all three; `drift.py`, which also reads `wording.py`, is round 2's.
- **`gate.py` and `scripts/run/mutation/` outlive round 1**, as dead code with one importer
  each, because `scaffold.py` imports both and setup is round 2's (decision 116).
- **A planted bug's test that errors, cannot be collected or runs past its limit reads
  `caught`** (decision 110: only a test that still passes is weak).
- **The audit's cost is written to a runtime file and one printed line**, and nothing is added
  to the evidence for it (decision 116: the build makes the measuring possible; the measuring
  is after).
- **The install test is held out of the default sweep** and run by `purlin:test` when its scope
  changed, by `--test --all`, and by `bash dev/run_tests.sh --install` (decision 111).
- **`dev/test_vocabulary.py` is deleted**: it carries no test comment and is a table of retired
  words (decision 44), and `purlin_output RULE-1` and `RULE-4` hold the one project-wide rule
  against emoji (decisions 109 and 112).
- **`Data from <time>` is not built**: decision 115's header line names the time, and no rule
  of `purlin_report` holds the older line.
- **The dashboard, the docs, the three-person test and the deck are local lanes**: each needs
  something a cloud session lacks.
- **`references/hard_gates.md` becomes `references/evidence_and_signoff.md`**, the name
  `purlin_agent RULE-18` already uses.

## 11. The lane prompt

The text each lane's session is given. `<lane>`, `<round>`, `<specs>`, `<owns>` and `<waits>`
are filled from sections 2 and 4.

```
You are the lane `<lane>` of the build of Purlin 0.10.0, decisions 100 to 116. Purlin is a
Claude Code plugin for spec-driven development that uses itself. You know nothing but this
repository at the branch `d115/base` and this prompt.

The specs under `specs/` are written and describe the product as decided. The code and the
tests are behind them. Your job: make the code and the tests you own meet your specs.

READ FIRST, in this order
1. `dev/plans/d115-plan.md`, whole. Sections 2 to 6 are your contract. Where a spec fixes
   words, the spec holds.
2. `dev/plans/three-levels.md`, decisions 100 to 116 (search `100. **`; they end before the
   line starting `44. **`), then decision 44. Later decisions win.
3. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`,
   `references/commit_conventions.md`.
4. Your specs, every rule and proof: <specs>.
5. For round 2: `dev/plans/d115-reports/round1.md`.

YOU OWN, and write nothing else
<owns>
and your report, `dev/plans/d115-reports/<lane>.md`.

SET UP
- `git switch -c lane/d115-<lane> origin/d115/base`.
- Where `git rev-parse --is-shallow-repository` answers `true`: `git fetch --unshallow origin`.
- `python3 -m pip install pytest`.
- A scratch folder outside the repository, yours alone. Save appendix A's script there.

DO, in this order
1. Run appendix A's script over your test files. Work through section 4's row for your lane:
   the comments that are gone, the ones reworded, the proofs to add.
2. Build the code to your specs and to section 3's contracts, word for word. Where you call
   what another lane fills, call it as section 3 names it; its stub is in the tree.
3. Change each format file section K14 gives you in the same commit as its code, with K14's
   number.
4. Break your most important change on purpose once, see its test fail, and restore it with
   `git checkout -- <that file>`. Never `git checkout -- specs/`.
5. Check your acceptance (section 2): your own test files pass but the tests waiting on
   <waits>; appendix A's script prints `0 gone, 0 reworded` for your files; every proof of
   your specs has a test comment; K15's greps over your files find nothing.
6. Write your report, commit it, push your branch.

RULES THAT HOLD THROUGHOUT
- No file under `specs/` changes. The test is changed to show the proof; a proof is never
  reworded to fit a test. A proof you cannot build to as worded: build the rest, leave it,
  report it.
- Write only the files you own. A failure in a file you do not own is reported, not fixed.
- Push only `lane/d115-<lane>`. No other branch, no tag, no pull request.
- No `purlin:audit` and no `purlin:sign` against this repository. Do not run
  `bash dev/run_tests.sh` or `purlin_run.py --test --all`: the full sweep is integration's.
  Run `python -m pytest <your test files> -q`, one process at a time.
- No real `claude` in a test: `dev/conftest.py` puts a fake first on the path, and a test that
  needs an answer installs its own `dev/fake_claude.py`. No network in a test: a git host is a
  bare repository on disk.
- A clean release (decision 44): what a decision cut is deleted outright, with its tests and
  fixtures. No compatibility reader, no test that a removed thing is absent, no table of
  removed words. The upgrade from 0.9.5 keeps what it needs.
- Never edit a number to make a test pass.
- A skipped test is not a passed test. Where a tool your tests need is absent (`dotnet`, `go`,
  `npm`, playwright, Python 3.9, `ssh-keygen`), say which tests skipped; integration runs them.
- Stage no generated file: `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/report-data.js`, `docs/images/*.png`.
- One proof, one case, one marked test: the comment `# purlin: <feature> PROOF-<n>` directly
  above it. A proof names what a person sees or a file holds, and its test asserts each value
  the proof names.
- Every line a person reads is as section 6 has it. No emoji anywhere. A line you have to
  choose is name first, fix last, plain and declarative, with exact numbers; list it in your
  report.
- A call no decision, spec or contract makes: build the rest, leave it, report it. Do not
  decide it.
- Commits follow `references/commit_conventions.md`, and each ends with the attribution lines
  your own session gives; where it gives none, `Co-Authored-By: Claude Opus 5.5
  <noreply@anthropic.com>`.
- Do not edit `dev/plans/three-levels.md`, `dev/plans/handoff.md` or this plan.

YOUR REPORT, `dev/plans/d115-reports/<lane>.md`, committed on your branch
- Tests: `python -m pytest <your files> -q` before your first change and after your last, as
  passed, failed and skipped; each test that skipped for a missing tool; each test waiting on
  another lane, by proof.
- Section 4's row, as you found it and as you leave it: comments gone, reworded and added, and
  the last line appendix A's script prints for your files.
- Every reworded comment, as `<file>:<line> <feature> <PROOF-N> stated | fixed | moved`, with
  one line on what changed for each `fixed`.
- Every test deleted, by name, in one list.
- Every line a person reads that you chose, word for word, and where it prints.
- Every difference from section 3's contracts, and why.
- Anything left unbuilt, any proof you could not build to as worded, any call left open, any
  failure in a file you do not own.
- What the session cost, if you can read it.
Then stop.
```

## Appendix A. The script that finds the comments to work through

Saved as `comments.py` in a lane's scratch folder, never committed, run from the repository
root with test files as its arguments. Over every `dev/test_*` file at `20a054551` it prints
`1621 gone, 257 reworded, 412 right as they stand.`

```python
"""Which test comments in the files named need work. Run from the repository root:
python3 <scratch>/comments.py dev/test_a.py dev/test_b.py
Prints one line per comment that is not right as it stands, then the counts."""
import ast, collections, os, re, subprocess, sys

def git(*args):
    return subprocess.run(('git',) + args, capture_output=True, text=True).stdout

def proofs(text):
    found = {}
    for line in text.splitlines():
        m = re.match(r'- (PROOF-\d+) \([^)]*\)[^:]*: (.*)', line)
        if m:
            found[m.group(1)] = ' '.join(m.group(2).split())
    return found

NOW = {os.path.basename(p)[:-3]: proofs(open(p, encoding='utf-8').read())
       for p in git('ls-files', 'specs').split()}
THEN, WHEN = {}, {}

def at(commit, feature):
    if (commit, feature) not in THEN:
        paths = [p for p in git('ls-tree', '-r', '--name-only', commit, 'specs').split()
                 if os.path.basename(p) == feature + '.md']
        THEN[commit, feature] = proofs(git('show', commit + ':' + paths[0])) if paths else {}
    return THEN[commit, feature]

def when(commit):
    if commit not in WHEN:
        WHEN[commit] = int(git('show', '-s', '--format=%ct', commit).strip())
    return WHEN[commit]

counts = collections.Counter()
for path in sys.argv[1:]:
    text = open(path, encoding='utf-8').read()
    lines = text.splitlines()
    shas = [l.split()[0] for l in git('blame', '--line-porcelain', path).splitlines()
            if re.match(r'^[0-9a-f]{40} \d+ \d+', l)]
    tests = []
    if path.endswith('.py'):
        tests = sorted((n.lineno, n.end_lineno) for n in ast.walk(ast.parse(text))
                       if isinstance(n, ast.FunctionDef) and n.name.startswith('test'))
    for number, line in enumerate(lines, 1):
        m = re.match(r'\s*(?:#|//|--)\s*purlin: ([a-z_0-9]+) (PROOF-\d+|RULE-\d+)\s*$', line)
        if not m:
            continue
        feature, proof = m.groups()
        if feature not in NOW or proof not in NOW[feature]:
            counts['gone'] += 1
            print('%s:%d %s %s  gone: no spec has it' % (path, number, feature, proof))
            continue
        after = [t for t in tests if t[0] > number]
        last = after[0][1] if after else len(lines)
        span = range(number, last + 1) if tests else range(1, len(lines) + 1)
        commit = max((shas[i - 1] for i in span if i <= len(shas)), key=when)
        old = at(commit, feature).get(proof)
        if old != NOW[feature][proof]:
            counts['reworded'] += 1
            print('%s:%d %s %s  reworded since %s: it read "%s"'
                  % (path, number, feature, proof, commit[:7], old))
        else:
            counts['right'] += 1
print('%d gone, %d reworded, %d right as they stand.'
      % (counts['gone'], counts['reworded'], counts['right']))
```

A comment that marks a rule with no proof, `purlin: <feature> RULE-<n>`, is read as gone by
this script; a lane that owns one checks it by hand against `reports RULE-1`. A test with a
line not yet committed is blamed to no commit, so the script is run on committed work.
