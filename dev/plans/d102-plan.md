# Decision 102: the answers to the QA and product check

Written by the planning agent on 2026-09-30, against `d102/base` at `ac4a55b`. It builds decision
102 of `three-levels.md` and nothing else, answering findings F1 to F13 of
`sanity-qa-product.md`. Eight lanes run at once, each a cloud session on Linux on a branch
`lane/d102-<lane>` made from `d102/base`, each owning files no other lane writes. One integration
agent then merges them on the owner's Mac. Section 2 is the contract: every lane builds to it and
none chooses. Section 8 holds the one question decision 102 leaves open.

## 1. Rules for every lane

`d100-plan.md` section 1 applies as written, with these names and changes.

- **Branch and scratch.** Lane `<lane>` works in its own cloud session's clone, on branch
  `lane/d102-<lane>` made from `origin/d102/base`, with a scratch folder of its own. It writes only
  the files section 4 gives it. It cannot see the other lanes: where it calls what another lane
  builds, it calls it exactly as section 2 names it, and the tests that need it fail until that
  lane merges (each lane's section lists them).
- **Environment (Linux, section 5).** First:
  `apt-get update -q && apt-get install -y -q openssh-client sqlite3`, then
  `python3 -m venv .venv && .venv/bin/pip install -q pytest playwright`, then
  `export PATH=$PWD/.venv/bin:$PATH`. A lane runs its own test files whole with
  `.venv/bin/python -m pytest <files> -q`, then `bash dev/run_tests.sh --fast`. It never runs the
  full sweep.
- **Frozen:** `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
  `dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`. None
  needs a change in this plan. A lane that needs a helper writes it in its own test file.
- **No generated file is staged:** `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`, `docs/images/*.png`,
  `dev/plans/deck/*.png`.
- **Proofs.** Every proof written or rewritten holds one case in at most 60 words and has a marked
  test of its own. New rules and proofs take the numbers section 4 gives, which are the next free
  ones after each spec's `> Highest-Rule:` / `> Highest-Proof:` at `ac4a55b`, and raise those
  lines. A number is never reused. A proof names what a person sees or a file holds, never a
  function inside the code (decision 98).
- **Clean release** (decision 44): what this plan retires is deleted outright: the advice to
  rename signature files, the sentence "No message is printed for it", the reading of a
  signature commit by its header alone. No test that a removed thing is absent, nothing added to
  `dev/test_vocabulary.py`. `RELEASE_NOTES.md` is the one place history is kept.
- **Formats.** A change to a format's parsing or emission updates its file under
  `references/formats/` in the same commit, with the number C12 gives.
- **Instruction lengths** (decision 80, `phase3-plan.md` section 1): status 100, test 120, build
  130, init 250, audit 105, sign 185, export 90, spec 210, spec-from-code 130, drift 150, anchor
  160, agent 135. Status sits at 100 today, sign at 179, build at 128: every line added there
  cuts one.
- **Deliberate break.** Each lane breaks its most important change on purpose (named in its
  section), sees its own test fail, then restores the file with `git checkout -- <that file>`,
  never `git checkout -- specs/`. The break runs only under a test that uses
  `dev/fake_claude.py` or no model, with no real `claude` on `PATH`, and reaches no git host,
  `gh`, `az` or network service: every repository a test makes is local, and a "host" is a bare
  repository on disk.
- **A call no decision makes and this plan does not make:** build the rest, leave that thing as
  it is, report it.
- **Commits** on the lane branch with the prefixes of `references/commit_conventions.md`, each
  ending with the attribution lines the session gives. Push the lane branch
  (`git push -u origin lane/d102-<lane>`) and nothing else: no tag, no pull request, no push to
  `d102/base` or `main`, no `purlin:audit`, no `purlin:sign`, no real `claude`.
- **Report** (in the last message and in `dev/plans/lanes/d102-<lane>.md`, committed on the lane
  branch): each spec's `> Highest-Rule:` and `> Highest-Proof:` after the work; tests before and
  after; every rule and proof deleted or reworded; every call left; every word chosen that
  section 7 does not give; every failure in a file it does not own; every test that fails only
  because another lane has not merged.

## 2. Contracts

What two lanes share, fixed word for word. `<...>` is filled in. Filled examples use the sample
project of `sanity-qa-product.md` (`sample_age`, `quinn.qa@labconnect.example`).

### C1. What the spec reader gives, lane `reader`

In `scripts/mcp/purlin/specs.py`, each spec's dict from `scan_specs` gains:

| Key | What it holds |
|---|---|
| `doubled_proofs` | each proof id written on more than one proof line, in the order first written; `[]` otherwise. Like a rule id, a proof id written twice is read once, with the text of its last line |
| `doubled_lines` | `{id: [{'line': <1-based line in the file>, 'text': <the rule's text, or the proof's text with its tags split off as `proofs[id]['text']` holds it>}, ...]}` for every id in `doubled_rules` and `doubled_proofs`, one entry per line in file order |
| `conflict_lines` | `[[<1-based line>, <the line as written, stripped>], ...]` for every line that `CONFLICT_RE` matches, anywhere in the file, in file order |
| `highest_rule`, `highest_proof` | the number on `> Highest-Rule:` / `> Highest-Proof:` as an int, or None where the line is absent or holds no number |

```python
# A line git leaves in a file whose merge stopped on a conflict: seven of one
# marker character at the start of the line, then a space or the line's end.
CONFLICT_RE = re.compile(r'^(?:<{7}|={7}|>{7}|\|{7})(?:[ \t].*)?$')

DOUBLED_REASON = '%s is written twice in the spec'
CONFLICT_REASON = 'the spec holds a line left from a merge conflict'

def broken_reasons(info):
    """Why every rule of this spec reads `failed`, or [] when nothing does.

    One `DOUBLED_REASON` per id of `doubled_rules`, then one per id of
    `doubled_proofs`, each in the order first written, then `CONFLICT_REASON`
    once where `conflict_lines` is not empty."""
```

A line of eight `=` is not a conflict line. Nothing else about how a spec is read changes: a spec
holding conflict lines is read as today, both sides' lines included.

### C2. The warnings, lane `reader`

Constants in `scripts/mcp/purlin/specs.py`. `spec_mistakes` returns, after its
`RULE_WRITTEN_TWICE` lines and before its `PROOF_LINE_UNREAD` lines, every `PROOF_WRITTEN_TWICE`
line (by feature, then in the order first written), then one conflict line per spec (by feature):

```
PROOF_WRITTEN_TWICE = '%s: %s is written twice; the second is read. Run purlin:spec %s.'
CONFLICT_ONE  = '%s: 1 line is left from a merge conflict, at line %d: %s. Run purlin:spec %s.'
CONFLICT_MANY = '%s: %d lines are left from a merge conflict, the first at line %d: %s. Run purlin:spec %s.'
```

The quoted line is the first conflict line, cut to `PROOF_LINE_SHOWN` (60) characters. Filled in:

```
sample_age: PROOF-4 is written twice; the second is read. Run purlin:spec sample_age.
sample_age: 1 line is left from a merge conflict, at line 14: =======. Run purlin:spec sample_age.
sample_age: 3 lines are left from a merge conflict, the first at line 14: <<<<<<< HEAD. Run purlin:spec sample_age.
```

They print wherever the spec mistakes print: the status, every test run, the dashboard's
warnings.

### C3. A spec that holds a number twice or a conflict line reads `failed`, lane `counting`

This amends decision 94's "nothing is refused" for these two mistakes alone, and applies to a rule
number written twice as to a proof number (decision 102's "a number written twice").

- `states.rule_cells(inp, cfg)` takes `spec_broken`: `specs.broken_reasons(info)` of the rule's
  own spec. Where it is not empty, before any signature is read (a `does_not_apply` signature
  included), the passed cell reads `failed` with `reasons` exactly `spec_broken`, `current` and
  `counts` true, `source` the one the evidence would give or None; the strong and signed cells
  read `waiting` as for any failed rule; `flags.failing` is true.
- The rule's `left` is `to_repair`, before every other kind.
- `summary.KINDS` gains, first, `('to_repair', 'spec to repair', 'specs to repair', 'purlin:spec')`,
  counting **specs**: `1 spec to repair: purlin:spec`, `2 specs to repair: purlin:spec`.
- The payload's feature entry gains `broken`: the list `broken_reasons` gives, `[]` otherwise.
- The tests still run and print: nothing is skipped because a spec is broken.

### C4. An ended signature, lane `counting`

A signature **ended** when it is the rule's newest counting signature by `timestamp`, it no longer
binds, no counting signature binds the rule, and it carries no `does_not_apply` (that case is
`to_confirm`, decision 101). In `scripts/mcp/purlin/states.py`:

```
ENDED = 'the signature by %s ended because %s'
ENDED_LINE = '%s %s: the signature by %s ended because %s.'
CAUSE_RULE    = "the rule's wording changed"
CAUSE_PROOF   = "a proof's wording changed"
CAUSE_TEST    = 'a test file behind it changed: %s'        # the rule's test files now, sorted, joined ', '
CAUSE_CODE    = 'a file its spec names changed'
CAUSE_PROJECT = 'a file of the project changed'            # an anchor's rule
CAUSE_AUDIT   = 'what the audit found changed'
CAUSE_MACHINE = 'the results on %s now come from %s, not %s'  # System word, machine now, machine signed
CAUSE_GONE    = '%s has no results any more'                # System word
```

Each field of the signature is compared with the rule's current one, in the order `rule_hash`,
`proof_hash`, `test_hash`, `code_hash`, `audit_hash`, then each system the signature's `machines`
names, sorted; every one that differs gives its cause, joined `; `. For a hand check (C8) only
`rule_hash` and `proof_hash` are compared.

- The signed cell of such a rule reads `unsigned` with the one reason `ENDED` filled in, for
  example `the signature by quinn.qa@labconnect.example ended because a test file behind it changed: tests/test_age.py`.
- The payload's rule entry gains `ended`: `{"signer": ..., "causes": [...], "line": <ENDED_LINE filled in>}`, or null.
- `summary.ended_lines(payload)` returns every rule's `ended.line`, by feature and then rule
  number, at every gate. The status prints them as a block of their own, after the pins block
  and before `Uncommitted spec changes:`; every test run and audit prints them there too, since
  they end on the status. Drift's `qa` view prints them (C7).

```
sample_age RULE-2: the signature by quinn.qa@labconnect.example ended because a test file behind it changed: tests/test_age.py.
```

### C5. The status line for a spec whose files do not exist yet, lane `counting`

`status.incomplete_line(names)` keeps its words and is printed for the specs with no `> Scope:`
line alone (the upgrade calls it for those). The specs whose `> Scope:` finds no file get
`status.unfound_line(names)`, printed right after it:

```
1 spec's > Scope: finds no file in git yet, so its tests run every time: sample_age. Commit the files it names, or run purlin:spec sample_age to correct it.
2 specs' > Scope: lines find no file in git yet, so their tests run every time: sample_age, stability. Commit the files they name, or run purlin:spec with each name to correct them.
```

### C6. The payload, schema 12, lane `counting`

`SCHEMA_VERSION = 12`: the feature's `broken` (C3), the rule's `ended` (C4), the kind `to_repair`
(C3). Nothing else changes. The dashboard's fixtures are schema 12 payloads (lane `dashboard`).

### C7. Drift, lane `drift`

Drift reads only this checkout: it never fetches, pulls or reaches the host.

- **The default branch** is `git symbolic-ref --quiet refs/remotes/origin/HEAD` with
  `refs/remotes/` cut, else the first of `origin/main`, `origin/master` that exists, else none.
  **Its age** is now less the time of the newest entry of that ref's reflog
  (`git reflog show -1 --format=%ct refs/remotes/<ref>`), else less the modification time of
  `FETCH_HEAD`, else unknown. Words: under 60 s `under a minute`, then whole `<n> minute(s)`,
  `<n> hour(s)`, `<n> day(s)`, rounded down.
- **Every view** (`pm`, `eng`, `qa`), after its own lines and before the uncommitted-specs line,
  gains, for every spec of this checkout: one line per number written twice, then one line per
  test comment whose proof's wording changed since the comment was written, then, where any line
  of the first kind was printed, the age line.
- **A number written twice**: the line whose text equals that id's text on the default branch's
  copy of the spec keeps the number; the other moves to the next free number,
  `max(highest, every number in the spec) + 1` of its kind. Four lines:

```
sample_age: PROOF-4 is written twice. The line on origin/main keeps PROOF-4; renumber the other to PROOF-7 and move its test comments with it: "<its text>".
sample_age: PROOF-7 is written twice, and neither line is on origin/main. The one that reaches origin/main first keeps PROOF-7; renumber the other to PROOF-8 and move its test comments with it.
sample_age: PROOF-4 is written twice on origin/main itself. Renumber the second to PROOF-7 and move its test comments with it: "<its text>".
sample_age: PROOF-4 is written twice, and this checkout has no copy of a default branch to say which line keeps it. Renumber the one not yet merged to PROOF-7 and move its test comments with it.
```

- **The age line**, one of:

```
origin/main was last fetched 3 days ago, and drift does not fetch. Run git fetch, then purlin:drift again.
origin/main has no record of when it was last fetched, and drift does not fetch. Run git fetch, then purlin:drift again.
```

- **A test comment whose proof's wording changed.** The comments read are those naming a proof
  whose text differs between the range's two ends, and those in a test file the range changed.
  For each, `git blame` gives the commit that last wrote the comment's line; the proof's text in
  the spec at that commit is compared with its text now. Where they differ:

```
tests/test_age.py:14 names sample_age PROOF-4, whose wording changed since the comment was written in a1b2c3d: it read "<old>" and now reads "<new>". Check the test still shows it, or run purlin:build sample_age.
tests/test_age.py:14 names sample_age PROOF-4, whose wording changed since the comment was written in a1b2c3d: it read "<old>" and now reads "<new>". Its old wording is now PROOF-6: move the comment there.
```

  The second is used where a proof of the same spec now holds the old text exactly.
- **Proofs added, changed and moved**, in the `pm` and `qa` views, after the rule lines in `pm`
  and first in `qa`. A proof **moved** when its text at the range's start is, unchanged, under
  another id of the same spec at its end; an id whose text differs is **changed**, and one absent
  at the start and not a move is **added**. Texts are quoted whole.

```
2 proofs added: sample_age PROOF-5, PROOF-6; stability PROOF-3.
sample_age PROOF-1 changed: it read "<old>" and now reads "<new>".
sample_age PROOF-4 moved to PROOF-6.
```

  One count line for added, as the rule lines count; one line each for changed and moved.
- **The `qa` view** also prints `summary.ended_lines(payload)` (C4), after the test-files line and
  before the lines of `Left to do`.
- JSON keys: every view gains `numbers_twice`, `comments_changed` and `default_branch`
  (`{"ref": ..., "age_seconds": <int or null>}` or null); `pm` and `qa` gain `proofs_added`
  (`{feature: [ids]}`), `proofs_changed` (`[{feature, id, old, new}]`) and `proofs_moved`
  (`[{feature, from, to}]`); `qa` gains `signatures_ended` (the lines).

### C8. A hand check's signature, lane `signing`

A signature whose `test_hash_kind` is `manual` is bound to the rule's and its proofs' wording
alone. `signatures.signed_hash(entry)`: where `entry.get('test_hash_kind') == 'manual'`, lines 4
to 7 (`test_hash`, `code_hash`, `audit_hash`, `machines`) are each the empty string; otherwise
unchanged. `is_current` reads the kind from the rule's current entry. The file still records
every field. Every other signature is bound as now: editing another test in the same file, or
re-running the same tests on another computer, still ends it. Signature format 13.

### C9. A signature commit that verifies, lane `signing`

A signature counts when the last commit touching its file carries a signature header **and that
signature verifies**: an SSH signature when `ssh-keygen -Y check-novalidate -n git -s <sig>`
accepts the commit's payload (the commit object without its `gpgsig` header), which needs no list
of allowed signers; an OpenPGP one when `git verify-commit <sha>` exits 0. Reasons, `counts`'
second answer:

```
NOT_SIGNED   = 'the commit that added it is not signed'                           # as now
NOT_VERIFIED = 'the signature on the commit that added it does not verify'
```

The key is not compared with the signer, and the author is not read (decisions 48 and 52).

### C10. Signing and the tag refused, lane `signing`

In `scripts/review/sign.py`, read from `specs.broken_reasons` of each spec (C1):

```
SPEC_REFUSED = '%s is not signed: %s. Run purlin:spec %s, then purlin:sign again.'
NO_TAG_SPEC  = 'No tag: %s cannot be counted: %s. Run purlin:spec %s, then purlin:sign.'
NO_TAG_BEHIND = ('No tag: %s holds %s that %s does not, as this checkout last fetched it. '
                 'Pull, run purlin:test --commit, then purlin:sign.')
REFUSED_SPEC = 'spec'      # joins MUST_FIX
REFUSED_BEHIND = 'behind'  # joins MUST_FIX
```

The reasons are joined `; `. Filled in:

```
sample_age is not signed: PROOF-4 is written twice in the spec. Run purlin:spec sample_age, then purlin:sign again.
No tag: sample_age cannot be counted: PROOF-4 is written twice in the spec. Run purlin:spec sample_age, then purlin:sign.
No tag: origin/main holds 1 commit that 8de0b6e does not, as this checkout last fetched it. Pull, run purlin:test --commit, then purlin:sign.
```

- `sign.py <feature> [RULE-N ...]`, with or without `--note` or `--does-not-apply`, naming a
  feature whose spec is broken prints `SPEC_REFUSED` once, writes nothing, commits nothing, exits
  1. `--all` and the walk never reach such a rule (its `left` is `to_repair`).
- `tag_if_met` at the gate `signed`, in this order: a `NO_TAG_SPEC` line per broken spec by name,
  then the summary ending, `REFUSED_SPEC`; then the checks of today up to the committed evidence;
  then `NO_TAG_BEHIND`, `REFUSED_BEHIND`; then the version and the rest as today. Nothing fetches.
- **The ref `NO_TAG_BEHIND` reads** is settled by the owner's answer to Q1 (section 8). Under the
  recommended answer it is the checked-out branch's upstream (`git rev-parse --abbrev-ref
  @{upstream}`), else `origin/<branch>` where that exists, else no check; `%s commit(s)` is
  `git rev-list --count HEAD..<ref>` and the check fires when it is above 0. Under the other
  answers, lane `signing` calls `drift.default_branch(project_root)` (C7), and its tests of this
  item fail until lane `drift` merges.

### C11. The walk shows each proof's tied test, lane `signing`

`render_row` prints, under each proof line that is not `@manual`, one line per test the rule
entry's proof lists (`proof['tests']`, `file::name`), or one line saying there is none:

```
Proof
  PROOF-1: A sample received at 10:30 UTC-5, collected at 14:00 UTC, has an age of `90` minutes
    tied to tests/test_age.py::test_age_at_receipt
  PROOF-4: A sample collected before the spring-forward change ... has an age of `60` minutes
    tied to no test
```

### C12. Format and schema numbers

| File | Now | After | Why |
|---|---|---|---|
| `references/formats/spec_format.md` | 21 | 21 | wording only: what a number written twice and a conflict line do, and who keeps a number after a collision |
| `references/formats/signature_format.md` | 12 | 13 | a hand check's signature is made over lines 1 to 3 alone (C8); a signature counts only when its commit's signature verifies (C9) |
| `references/formats/package_format.md` | 5 | 6 | the kind `to_repair` in `left` (C3) |
| `references/formats/evidence_format.md` | 7 | 7 | wording only: a re-run over a file left conflicted keeps audit entries whose hashes still match |
| `references/formats/marker_format.md` | 3 | 3 | unchanged |
| `references/formats/anchor_format.md` | 11 | 11 | unchanged |
| payload `schema_version` | 11 | 12 | C6 |

`specs/review/signatures.md` RULE-9 says `signature format 13`.

### C13. Pytest from a plain tests folder, lane `run`

`frameworks.py`'s pytest detector also answers yes where a folder `tests/` at the root holds,
at any depth, a file named `test_*.py`. `references/supported_frameworks.md`'s pytest row reads
`` `conftest.py` or `pytest.ini` at the root, `[tool.pytest` in `pyproject.toml`, or a file named `test_*.py` under `tests/` ``.

## 3. Findings to lanes

| Finding | Decision 102's answer | Lane |
|---|---|---|
| F1 proof id twice | warned of, rules `failed`, signing and tag refused | reader, counting, signing, run, dashboard |
| F2 collision recipe | the number on the default branch keeps it; drift names both sides; no signature renaming | drift, skills, words |
| F3 walk shows no test | each proof's tied test | signing, skills |
| F4 who signs, walk tags | not changed (decisions 48, 52) | none |
| F5 silent, broad endings | one line per ended signature; a hand check bound to wording alone | counting, signing, drift, words |
| F6 conflict markers | warned of, rules `failed`, signing and tag refused | reader, counting, signing |
| F7 changed proofs unseen | drift's proofs added, changed, moved, and changed comments | drift |
| F8 evidence conflicts | re-run keeps matching audits; docs say who commits and where | run, words |
| F9 tag off the branch | refused when the host copy moved past | signing |
| F10 risk | no level; the quality guide and a QA page teach it | skills, words |
| F11 new spec blocks release | release branch, taught by the docs | words |
| F12 smaller faults | the real cause in the status; the commit's signature verified; plain `tests/test_*.py` | counting, signing, run |
| F13 doc gaps | the `> Highest-Proof:` example; a QA page; who commits evidence | words |

## 4. The lanes

Every file that changes has exactly one owner. Ownership follows `phase3-plan.md` section 4 and
`d100-plan.md` section 4.

| Lane | Owns |
|---|---|
| L1 `reader` | `scripts/mcp/purlin/specs.py`; `references/formats/spec_format.md`; `specs/mcp/specs.md`; `specs/mcp/schema_spec_format.md`; `dev/test_specs_reader.py`; `dev/test_schema_spec_format.py` |
| L2 `counting` | `scripts/mcp/purlin/{states,payload,status,summary,board}.py`; `specs/mcp/{states,summary}.md`; `dev/test_{states,summary,backing_tests,failing}.py`; `skills/status/SKILL.md`; `specs/skills/skill_status.md`; `dev/test_skill_status.py` |
| L3 `drift` | `scripts/mcp/purlin/drift.py`; `specs/mcp/drift.md`; `dev/test_drift.py`; `references/drift_criteria.md`; `skills/drift/SKILL.md`; `specs/skills/skill_drift.md`; `dev/test_skill_drift.py` |
| L4 `signing` | `scripts/review/sign.py`; `scripts/mcp/purlin/signatures.py`; `specs/review/signatures.md`; `dev/test_signatures.py`; `dev/test_tag.py`; `references/formats/signature_format.md`; `scripts/export/package.py`; `specs/export/package.md`; `dev/test_export.py`; `references/formats/package_format.md` |
| L5 `run` | `scripts/run/purlin_run.py`; `scripts/run/evidence.py`; `scripts/mcp/purlin/frameworks.py`; `specs/run/{run_script,evidence_writer}.md`; `dev/test_{run_script,evidence_writer}.py`; `references/formats/evidence_format.md`; `references/supported_frameworks.md` |
| L6 `dashboard` | `scripts/report/src/**`; `scripts/mcp/purlin/report_data.py`; `dev/build_report.py`; `specs/dashboard/purlin_report.md`; `dev/test_purlin_report.py`; `dev/test_purlin_report_board_layout.py`; `dev/test_report_refresh.py`; `dev/fixtures/report/*.json`; `docs/dashboard.md` |
| L7 `skills` | `skills/{spec,sign}/SKILL.md`; `specs/skills/{skill_spec,skill_sign}.md`; `dev/test_skill_{spec,sign}.py`; `references/spec_quality_guide.md` |
| L8 `words` | `references/{glossary,purlin_commands,hard_gates}.md`; `RELEASE_NOTES.md`; `README.md`; `docs/{index,specs-and-anchors,team-workflow,working-together,review-and-signing,running-and-evidence,regulated-workflow}.md`; the new `docs/qa-guide.md`; `specs/instructions/purlin_docs.md`; `dev/test_purlin_docs.py` |

No lane: the markers module, the evidence reader (`scripts/mcp/purlin/evidence.py`), the
fingerprint, mutation, host and remote, scaffold, update, settings, the anchor tools, the audit
reader, the other skills and `agents/purlin.md`. None has work under decision 102. A failure the
sweep finds there is integration's.

### L1 `reader`

Builds C1 and C2. `references/formats/spec_format.md` (stays 21) says, in "Rules format" and
"Proof format", that a rule or proof number written twice, and a line left from a merge conflict,
are warned of and make every rule of the spec read `failed` until fixed, and gains in its id
paragraph the collision sentence of section 7 (row "The collision rule").

`specs/mcp/schema_spec_format.md` (R34 P80; next RULE-35, PROOF-81):
- RULE-35: A proof number written twice is warned of, and the proof is read once, with the text
  of its second line. PROOF-81: a spec `login` with `PROOF-4 (RULE-1)` and `PROOF-4 (RULE-2)`
  prints `login: PROOF-4 is written twice; the second is read. Run purlin:spec login.`
- RULE-36: A line left from a merge conflict is warned of with its line number. PROOF-82: one
  `=======` line at line 12 prints the singular line of C2. PROOF-83: a hunk `<<<<<<< HEAD` at
  line 9, `=======`, `>>>>>>> main` prints the plural line naming 3 lines, line 9 and
  `<<<<<<< HEAD`. PROOF-84: a line of eight `=` prints no such line.
- RULE-37: The reasons a spec's rules fail are named in order. PROOF-85: a spec writing `RULE-2`
  twice, `PROOF-4` twice and holding `=======` gives `RULE-2 is written twice in the spec`,
  `PROOF-4 is written twice in the spec`, `the spec holds a line left from a merge conflict`.

`specs/mcp/specs.md` (R21 P43): no rule changes unless a reader test breaks; then one proof per
fix from RULE-22, PROOF-44.

Break on purpose: stop adding to `doubled_proofs`; PROOF-81's test fails.

Tests that may fail only because another lane has not merged: none.

### L2 `counting`

Builds C3 (states, payload, summary), C4, C5, C6. `board.py` only where the `Tests` cell needs no
change (a broken spec's rules count as `failing`, so it reads `0 of 5 · 5 failing` with no new
word). The status skill takes no new line unless a proof quotes the table's ending; at its
ceiling it cuts one for any line it adds.

`specs/mcp/states.md` (R101 P247; next RULE-102, PROOF-248):
- RULE-102: Every rule of a spec that writes a number twice or holds a line left from a merge
  conflict reads `failed`, with the reasons naming each. PROOF-248: `login`, whose tests pass,
  writes `PROOF-2` twice: each of its two rules reads `failed` with the one reason
  `PROOF-2 is written twice in the spec`. PROOF-249: `login` holding `>>>>>>> main` reads
  `failed` with `the spec holds a line left from a merge conflict`. PROOF-250: in the same
  project, `export`, whose spec is sound and whose tests pass, reads `passed`. PROOF-251: a rule
  of the broken `login` that a counting signature binds reads `failed`, and its signed cell is
  not met.
- RULE-103: A signature that ended gives its cause in the signed cell. PROOF-252: signed, then
  its test file edited: `unsigned` with
  `the signature by jane@acme.com ended because a test file behind it changed: tests/test_login.py`.
  PROOF-253: the rule's text edited: `... ended because the rule's wording changed`. PROOF-254:
  the macOS results now from `quinn-laptop` where it was signed over `jane-laptop`:
  `... ended because the results on macOS now come from quinn-laptop, not jane-laptop`.
- RULE-104: The status prints one line per ended signature. PROOF-255: the status holds
  `login RULE-1: the signature by jane@acme.com ended because the rule's wording changed.`
  PROOF-256: a rule whose newer signature binds it prints no such line.
- RULE-105: The status names a spec whose `> Scope:` finds no file apart from one with no
  `> Scope:` line. PROOF-257: `sample_age` with `> Scope: src/age.py` and no such file prints C5's
  singular line. PROOF-258: two such specs print C5's plural line. PROOF-259: a spec with no
  `> Scope:` line still prints `1 spec names no files, so its tests run every time: ...`.
- The schema rule, if one names `11`, says `12`.

`specs/mcp/summary.md` (R15 P39; next RULE-16, PROOF-40): RULE-16, `to_repair` is the first line
of `Left to do` and counts specs. PROOF-40: one broken spec of three rules reads
`1 spec to repair: purlin:spec` as the first line. PROOF-41: two broken specs read
`2 specs to repair: purlin:spec`.

`specs/skills/skill_status.md` (R11 P35): changes only where a proof quotes a changed line.

Break on purpose: stop passing `spec_broken` to `rule_cells`; PROOF-248's test fails. Then drop
`CAUSE_TEST`; PROOF-252's test fails.

Tests that may fail only because another lane has not merged: PROOF-248 to PROOF-251, PROOF-40,
PROOF-41 (they read `broken_reasons`, lane `reader`).

### L3 `drift`

Builds C7 and `drift.default_branch(project_root)` → `'origin/main'`-shaped string or None,
`drift.fetched_age(project_root, ref)` → seconds or None. The drift skill says what the new lines
mean and that drift never fetches, within its ceiling (150; it is at 75).
`references/drift_criteria.md` gives the new lines to each view and the default-branch and age
rules of C7.

`specs/mcp/drift.md` (R27 P66; next RULE-28, PROOF-67):
- RULE-28: `pm` and `qa` name the proofs added. PROOF-67: a pull adding `PROOF-5` and `PROOF-6`
  to `login` prints `2 proofs added: login PROOF-5, PROOF-6.` in both views.
- RULE-29: They name each proof changed, with both texts. PROOF-68: `PROOF-1`'s `150` made `90`
  prints `login PROOF-1 changed: it read "<old>" and now reads "<new>".`
- RULE-30: They name each proof moved. PROOF-69: the text of `PROOF-4` now under `PROOF-6` prints
  `login PROOF-4 moved to PROOF-6.`
- RULE-31: Every view names a number written twice and the line that moves. PROOF-70: after a
  merge, `origin/main`'s `PROOF-4` text `A` and the branch's `B` print C7's first form, keeping
  the line `A`, moving `B` to the next free number. PROOF-71: neither text on `origin/main`
  prints the second form. PROOF-72: a checkout with no remote prints the fourth form.
- RULE-32: Where it names one, it says how old its copy of the default branch is and does not
  fetch. PROOF-73: `origin/main`'s newest reflog entry three days old prints
  `origin/main was last fetched 3 days ago, and drift does not fetch. Run git fetch, then purlin:drift again.`
  PROOF-74: after another clone pushes to the bare host, drift leaves `origin/main` where it was.
- RULE-33: Every view names a test comment whose proof's wording changed since it was written.
  PROOF-75: a comment written when `PROOF-4` read `A`, now `B`, prints C7's first comment form.
  PROOF-76: with `A` now `PROOF-6`, the second form. PROOF-77: a comment whose proof is unchanged
  prints nothing.
- RULE-34: `qa` prints each ended signature. PROOF-78: after a test file edit, `qa` holds
  C4's line for that rule.

`specs/skills/skill_drift.md` (R10 P36; next RULE-11, PROOF-37): RULE-11, the skill says drift
reads only this checkout and names how old its copy of the default branch is (PROOF-37); RULE-12,
it says what to do with a number written twice (PROOF-38).

Break on purpose: take the default branch's text as the one that moves; PROOF-70's test fails.

Tests that may fail only because another lane has not merged: PROOF-70 to PROOF-72 (they read
`doubled_lines`, lane `reader`); PROOF-78 (`summary.ended_lines`, lane `counting`).

### L4 `signing`

Builds C8, C9, C10, C11, signature format 13 (C8, C9, and the "Current" table gains
`A hand check's signature: its rule's or a proof's wording changed | no longer current` and
`A hand check's signature: the code, a test or the machines changed | still current`; the
sentence "No message is printed for it." becomes `The status and every test run print one line
naming the rule, the signer and why it ended.`), package format 6 (the `to_repair` row of the
kinds table: `1 spec to repair`, `<n> specs to repair`, `purlin:spec`).

`specs/review/signatures.md` (R95 P189; next RULE-96, PROOF-190):
- RULE-9 reworded: `signature format 13`.
- RULE-96: A hand check's signature is bound to the wording of its rule and proofs alone.
  PROOF-190: a rule whose one proof is `@manual`, signed; then a file its spec names is edited:
  the rule still reads `signed`. PROOF-191: then its proof's wording is edited: `unsigned`.
- RULE-97: A signature counts only when the signature on its commit verifies. PROOF-192: a
  signature file whose commit is rewritten with one byte of its `gpgsig` block changed reads
  `unsigned` with `the signature on the commit that added it does not verify`. PROOF-193: a
  signed commit whose key file has since been deleted still counts.
- RULE-98: Naming a feature whose spec writes a number twice or holds a conflict line signs
  nothing. PROOF-194: `purlin:sign login RULE-1`, `login` writing `PROOF-2` twice, prints C10's
  first line, writes no file, makes no commit, exits 1. PROOF-195: `purlin:sign login` the same.
- RULE-99: The tag is refused while a spec is broken. PROOF-196: at `signed`, a broken `login`
  prints `No tag: login cannot be counted: PROOF-2 is written twice in the spec. Run purlin:spec login, then purlin:sign.`
  and exits 1.
- RULE-100: The tag is refused while the branch's copy on the host holds commits the checkout
  lacks. PROOF-197: a clone whose `origin/main`, fetched, is one commit ahead prints C10's third
  line and writes no tag. PROOF-198: HEAD ahead of `origin/main` by an unpushed commit is tagged.
  PROOF-199: another clone's push this clone has not fetched does not stop the tag.
- RULE-101: The walk shows each proof's tied test. PROOF-200: a stop shows
  `    tied to tests/test_login.py::test_valid_credentials_return_200` under `PROOF-1`.
  PROOF-201: a proof no test backs shows `    tied to no test`.

`specs/export/package.md` (R27 P59; next RULE-28, PROOF-60): RULE-28, a package's `left` names a
broken spec as `to_repair`. PROOF-60: `purlin:export` of a project with a broken `login` lists
`{"kind": "to_repair", "count": 1, "text": "1 spec to repair", "command": "purlin:spec"}`.

Break on purpose: sign a hand check over all seven lines; PROOF-190's test fails. Then read the
header without verifying; PROOF-192's test fails.

Tests that may fail only because another lane has not merged: PROOF-194 to PROOF-196 and
PROOF-60 (`broken_reasons`, lane `reader`; the kind, lane `counting`).

### L5 `run`

Builds C13; the run exits 1 when any spec under `specs/` is broken, after running every test and
printing as today; the audit reads no rule of a broken spec; and, in `scripts/run/evidence.py`, a
write over an evidence file that is not valid JSON reads each side of its conflict hunks (the
lines before `=======` and after `>>>>>>>` make one side, the rest the other), keeps from both
every `audit.rules` entry whose `rule_hash`, `proof_hash` and `test_hash` equal the rule's
current ones (the newer `at` where both hold one), and the newer `audit.mutation`. The evidence
format says so in one sentence (stays 7).

`specs/run/run_script.md` (R86 P260; next RULE-87, PROOF-261):
- RULE-87: A test run exits 1 while a spec writes a number twice or holds a conflict line, after
  running its tests. PROOF-261: `--test --all` where `login`'s tests pass and it writes `PROOF-2`
  twice writes `login`'s results and exits 1.
- RULE-88: A plain `tests/test_*.py` project is suggested pytest. PROOF-262: a project with an
  empty `tests` setting holding only `tests/test_cart.py` prints
  `Suggested for pytest: python3 -m pytest --ignore=mutants {files} --junitxml={report}`.
  PROOF-263: one holding only `tests/helpers.py` prints no pytest suggestion.
- RULE-89: The audit reads no rule of a broken spec. PROOF-264: `--audit` over a broken `login`
  makes no model call for it.

`specs/run/evidence_writer.md` (R25 P87; next RULE-26, PROOF-88): RULE-26, a write over an
evidence file left conflicted keeps each audit entry whose hashes still match. PROOF-88: both
sides hold `RULE-1`'s current audit entry; after `--test` the file parses and holds it.
PROOF-89: an entry whose rule text changed since is not kept.

Break on purpose: drop the audit entries recovered from a conflicted file; PROOF-88's test fails.

Tests that may fail only because another lane has not merged: PROOF-261 and PROOF-264
(`broken_reasons`, lane `reader`).

### L6 `dashboard`

Schema 12 fixtures (C6): the team sample gains a spec writing a proof twice, whose rules carry
`failed` with the reason and `left: to_repair`, and a rule whose signature ended; `filters.js`
gains `to_repair: 'To repair'`. The rule's page shows the signed cell's `ENDED` reason where it
shows a cell's reasons, and the failed reason likewise, with no new element. `docs/dashboard.md`
names the `To repair` button where it lists the buttons.

`specs/dashboard/purlin_report.md` (R65 P214; next RULE-66, PROOF-215):
- RULE-66: A spec to repair has its filter button. PROOF-215: the team sample shows `To repair`;
  pressing it leaves exactly that spec's rules.
- RULE-67: A rule whose signature ended says why on its page. PROOF-216: its signed panel reads
  `the signature by <signer> ended because a test file behind it changed: <file>`.
- RULE-68: A rule of a broken spec says why on its page. PROOF-217: its passed panel reads
  `PROOF-2 is written twice in the spec`.

Break on purpose: drop `to_repair` from the short labels; PROOF-215's test fails.

Tests that may fail only because another lane has not merged: none (the fixtures are fixed JSON).
If the browser cannot start in the cloud (section 5), the lane leaves the browser tests to
integration and says so.

### L7 `skills`

- `skills/spec/SKILL.md` "After a merge conflict" is replaced by section 7's paragraph (row "The
  spec skill"). The advice to rename signature files goes.
- `skills/sign/SKILL.md` gains, within 185 lines: the walk shows each proof's tied test; a
  feature whose spec writes a number twice or holds a conflict line is refused; a hand check's
  signature ends only when the wording of its rule or proofs changes; the tag is refused while
  the branch's copy on the host holds commits this checkout lacks; sign a version on a release
  branch. It cuts what it adds beyond the ceiling.
- `references/spec_quality_guide.md` gains the paragraph of section 7 (row "The quality guide").

Next free ids: `skill_spec` RULE-25, PROOF-55; `skill_sign` RULE-25, PROOF-54.
- `skill_spec`: RULE-25, the skill says the number already on the default branch keeps it and the
  branch's rule or proof moves (PROOF-55); RULE-26, it says a moved rule needs a new audit and a
  new signature (PROOF-56); RULE-27, it says to take out every line left from the conflict
  (PROOF-57); RULE-28, the quality guide says a computation or data flow a mistake would harm
  gets a proof per boundary and look and feel is not a rule (PROOF-58).
- `skill_sign`: RULE-25, the skill says the walk shows each proof's tied test (PROOF-54);
  RULE-26, that a broken spec is refused (PROOF-55); RULE-27, that a hand check's signature ends
  only on a change of wording (PROOF-56); RULE-28, the tag refusal and the release branch
  (PROOF-57, PROOF-58).

Break on purpose: put the rename advice back; PROOF-55's test fails (it reads the sentence that
keeps the default branch's number).

Tests that may fail only because another lane has not merged: none.

### L8 `words`

Section 7's lines into the references and docs:
- `docs/specs-and-anchors.md`: the example spec's `> Highest-Proof:` reads the highest proof it
  holds; "After a merge conflict" says the collision rule and drops the rename advice.
- `docs/team-workflow.md`: the collision rule, the release branch, who commits evidence.
- `docs/working-together.md`: the QA row points at `docs/qa-guide.md`; drift names changed proofs
  and ended signatures.
- `docs/review-and-signing.md`: the walk's tied test, the ended-signature line, the hand check's
  binding, the verified commit, the two tag refusals, the release branch; the consequences F13
  names (a signature covers the test files and the machines; re-running on another computer ends
  it).
- `docs/running-and-evidence.md`: who commits evidence and on which branch; a re-run after a
  conflict keeps the audits that still match; plain `tests/test_*.py`.
- `docs/regulated-workflow.md`: the release branch.
- `docs/qa-guide.md`, new, `From criteria to a signature`: a QA person's criteria to proof lines
  (`purlin:spec`), what the developer adds, the walk, the signature, what ends one, drift after a
  pull, risk (pointing at the quality guide's paragraph, not restating it). Every statement is
  held by a rule the lane names in its report.
- `docs/index.md`: the QA table's first row is the new page.
- `references/hard_gates.md`: the hand check's binding, the verified commit, the two tag
  refusals. `references/glossary.md`: `release branch`, `to repair`. `references/purlin_commands.md`:
  `purlin:sign` refuses a broken spec and a tag behind its host copy; `purlin:drift` names
  numbers written twice and never fetches.
- `RELEASE_NOTES.md` 0.10.0: section 7's release-notes lines; the format numbers of C12.
- `dev/test_purlin_docs.py`: the "no-tool" sample's test file becomes `tests/cart_check.rb`, so
  no tool Purlin knows claims it once lane `run` merges (C13). `specs/instructions/purlin_docs.md`
  (R12 P17) changes only where a proof quotes a changed line.

Break on purpose: none in code; the lane runs `dev/test_purlin_docs.py` and greps its files for
`signature filenames`, `incoming one` and `> Highest-Proof: 2` (each empty).

Tests that may fail only because another lane has not merged: none (PROOF-8's sample holds no
`test_*.py`).

## 5. Linux notes

Each lane runs in a cloud container: Linux, Python 3.11, git 2.43, Node 22 and Go present;
`ssh-keygen` and `sqlite3` only after the `apt-get` of section 1; no dotnet, no macOS, no
mutmut or Stryker unless installed; Chromium at `/opt/pw-browsers`.

| Lane | Needs what the cloud may lack | Left to integration |
|---|---|---|
| `reader` | nothing | nothing |
| `counting` | `ssh-keygen` for tests that sign commits (`mcp_project.sign_commits`) | nothing, once installed |
| `drift` | nothing (bare repositories on disk) | nothing |
| `signing` | `ssh-keygen` with `-Y` (OpenSSH 8.2 or later; 9.6 installs); git ssh signing | nothing, once installed |
| `run` | `sqlite3` for two tests of `dev/test_run_script.py`; the dotnet suggestion tests use a stand-in, not dotnet | tests skipped for `platform.system() != 'Windows'`; any that need dotnet 8 or a real mutation engine |
| `dashboard` | a browser: `dev/browser_launch.py` tries the bundled Chromium, then `/usr/bin/chromium`; if the pip `playwright` does not match `/opt/pw-browsers/chromium-1194`, pass `executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome'` in the lane's own test run only, never in the committed helper | every browser test, if none starts |
| `skills` | nothing | nothing |
| `words` | nothing; the sample runs pytest from the `.venv` | nothing |

No lane's tests need macOS or dotnet 8 for their new proofs. The full sweep and the dashboard
look at five widths run on the Mac.

## 6. Merge order and integration

### Merge order

`reader`, `counting`, `drift`, `signing`, `run`, `dashboard`, `skills`, `words`. Each by
fast-forward: integration rebases the lane branch on the merged line, reruns its files and
`--fast`, then fast-forwards `d102/base` to it.

Why: `reader`'s C1 is read by `counting`, `drift`, `signing` and `run`. `counting`'s
`summary.ended_lines` is read by `drift`. `drift` goes before `signing` so that, under either
answer to Q1, `signing` can call `drift.default_branch`. `run` changes what the docs sample
detects, so `words` goes after it. `dashboard` reads only fixed fixtures; `skills` and `words`
describe what the others built, so they come last.

Expected red between merges, and only these: the tests each lane's section lists as waiting for
another lane, until that lane merges; from the `run` merge until `words` merges, PROOF-8 of
`dev/test_purlin_docs.py` (the sample's `tests/test_cart.py` is then detected as pytest); any
test of `dev/test_init_scaffold.py` or `dev/test_skill_init.py` whose project holds a
`tests/test_*.py` and expects no pytest (C13), which integration corrects to the contract.

### The integration agent's job (alone, on the Mac, after every lane merged)

1. Merge in the order above; resolve each failure a lane reported in a file it does not own, to
   the contracts. No frozen file changes.
2. `export PATH=/opt/homebrew/opt/dotnet@8/bin:$PWD/.venv/bin:$PATH`; `bash dev/run_tests.sh`:
   0 failed. Never edit a number to make it pass.
3. `python3 dev/build_report.py`; commit `scripts/report/purlin-report.html` once.
4. Look at the dashboard with playwright from the `.venv`, headless, dark and light, at 1500,
   1280, 1024, 768 and 390 pixels: the `To repair` button on a sample with a broken spec, the
   ended reason on a rule's page, no value broken inside itself, neutral text at least 7 to 1.
   The two docs screenshots are retaken only if the board they show changed.
5. Greps over `scripts/`, `skills/`, `agents/`, `references/`, `docs/`, `templates/`,
   `README.md` and `dev/test_*.py`, each empty outside `RELEASE_NOTES.md`: `signature filenames`,
   `incoming one`, `No message is printed for it`, `schema_version.: 11`.
6. `python3 scripts/run/purlin_run.py --test --all`: `Markers: <n> tied to a test, 0 not tied.`,
   no rule `failed`, `partial` or `no test`, no spec to repair, no warning. Then the same with
   `--commit`.
7. Write `dev/plans/d102-interfaces.md`: what was built where it differs from the contracts,
   every word a lane chose that section 7 does not give, the ids, the test counts, and section 7
   copied under "Words chosen for the owner to read".
8. Update `dev/plans/handoff.md`: "Where the tree is", "What is left" (decision 102 built; the
   remote run on Windows for any new `@env(windows)` proof, none planned here), and section 7's
   words under "Words for the owner to read".

## 7. Lines a person reads, chosen

In the shape of decisions 94 to 101. The owner reads these and says which to change.

| Where | What it says |
|---|---|
| A proof written twice (C2) | `sample_age: PROOF-4 is written twice; the second is read. Run purlin:spec sample_age.` |
| A line left from a merge conflict (C2) | `sample_age: 1 line is left from a merge conflict, at line 14: =======. Run purlin:spec sample_age.`; `sample_age: 3 lines are left from a merge conflict, the first at line 14: <<<<<<< HEAD. Run purlin:spec sample_age.` |
| The failed cells' reasons (C3) | `PROOF-4 is written twice in the spec`; `RULE-4 is written twice in the spec`; `the spec holds a line left from a merge conflict` |
| `Left to do` (C3) | `1 spec to repair: purlin:spec`; `2 specs to repair: purlin:spec`; the dashboard button `To repair` |
| Signing refused (C10) | `sample_age is not signed: PROOF-4 is written twice in the spec. Run purlin:spec sample_age, then purlin:sign again.` |
| The tag refused, a broken spec (C10) | `No tag: sample_age cannot be counted: PROOF-4 is written twice in the spec. Run purlin:spec sample_age, then purlin:sign.` |
| The tag refused, the host moved (C10) | `No tag: origin/main holds 1 commit that 8de0b6e does not, as this checkout last fetched it. Pull, run purlin:test --commit, then purlin:sign.` (`2 commits` for more) |
| A signature ended (C4) | `sample_age RULE-2: the signature by quinn.qa@labconnect.example ended because a test file behind it changed: tests/test_age.py.`; the causes `the rule's wording changed`, `a proof's wording changed`, `a test file behind it changed: <files>`, `a file its spec names changed`, `a file of the project changed`, `what the audit found changed`, `the results on macOS now come from quinn-laptop, not vm`, `Windows has no results any more`, joined `; `; the cell reason `the signature by <signer> ended because <causes>` |
| The walk (C11) | `    tied to tests/test_age.py::test_age_at_receipt`; `    tied to no test` |
| A signature that does not verify (C9) | `the signature on the commit that added it does not verify` |
| The status, files not there yet (C5) | `1 spec's > Scope: finds no file in git yet, so its tests run every time: sample_age. Commit the files it names, or run purlin:spec sample_age to correct it.`; `2 specs' > Scope: lines find no file in git yet, so their tests run every time: sample_age, stability. Commit the files they name, or run purlin:spec with each name to correct them.` |
| Drift, a number written twice (C7) | `sample_age: PROOF-4 is written twice. The line on origin/main keeps PROOF-4; renumber the other to PROOF-7 and move its test comments with it: "<text>".`; `sample_age: PROOF-7 is written twice, and neither line is on origin/main. The one that reaches origin/main first keeps PROOF-7; renumber the other to PROOF-8 and move its test comments with it.`; `sample_age: PROOF-4 is written twice on origin/main itself. Renumber the second to PROOF-7 and move its test comments with it: "<text>".`; `sample_age: PROOF-4 is written twice, and this checkout has no copy of a default branch to say which line keeps it. Renumber the one not yet merged to PROOF-7 and move its test comments with it.` |
| Drift, the age (C7) | `origin/main was last fetched 3 days ago, and drift does not fetch. Run git fetch, then purlin:drift again.`; `origin/main has no record of when it was last fetched, and drift does not fetch. Run git fetch, then purlin:drift again.` |
| Drift, a test comment (C7) | `tests/test_age.py:14 names sample_age PROOF-4, whose wording changed since the comment was written in a1b2c3d: it read "<old>" and now reads "<new>". Check the test still shows it, or run purlin:build sample_age.`; the ending `Its old wording is now PROOF-6: move the comment there.` |
| Drift, proofs (C7) | `2 proofs added: sample_age PROOF-5, PROOF-6; stability PROOF-3.`; `sample_age PROOF-1 changed: it read "<old>" and now reads "<new>".`; `sample_age PROOF-4 moved to PROOF-6.` |
| The collision rule (spec format, docs) | `When two branches take the same number, the number already on the default branch keeps it, and the rule or proof from the branch not yet merged moves to the next free number. A moved rule needs a new audit and a new signature; its old signature ends and stays on disk.` |
| The spec skill, "After a merge conflict" | `Two branches that took the same number before either merged leave a spec with one id twice, and git may merge one of the two lines outside the conflict. The number already on the default branch keeps it; the rule or proof from the branch not yet merged moves to the next free number. Run purlin:drift after the merge: it names every number written twice and which line moves. A moved rule needs a new audit and a new signature. Tell the person whose line moved, so the test comments on their branch move with it. When the conflict is two different texts on the same line, show both versions, ask which survives, and say which signatures that answer ends. Take out every line git left from the conflict: while one stays, every rule of the spec reads failed.` |
| The quality guide, "Where the risk is" | `Every rule at the gate is asked the same things, so the weight of a risk goes into its proofs. A computation or a data flow a mistake would harm gets a proof per boundary: each edge of a range, each time zone and change of clock, each unit, each hand-off from one feature to the next. Look and feel is not a rule; a person judges it outside Purlin.` |
| A hand check's signature (format, hard gates, docs) | `A hand check's signature is made over the rule's and its proofs' wording alone: a change to the code, a test or the machines does not end it, and a change to that wording does. Every other signature covers the rule's test files whole and the machine each system's results came from, so editing another test in the same file, or running the same tests on another computer, ends it.` |
| A verified commit (hard gates, format) | `A signature counts when the commit that added it is signed and that signature verifies over the commit. The key is not compared with the signer.` |
| Who commits evidence (docs) | `Whoever runs purlin:test --commit or purlin:audit --commit commits the evidence, on the branch they are on: it describes that branch's code. When a merge conflicts in .purlin/evidence/, take either side and run purlin:test --commit: the file is written again, keeping each audit result whose rule, proof and test are unchanged. The evidence a version is signed on is committed on its release branch.` |
| The release branch (docs, glossary) | `Sign a version on a release branch, such as release/1.2.0, cut from the default branch once its specs are done. New specs land on the default branch and wait for the next version; a fix lands on the release branch and is merged back.`; glossary `**release branch**: the branch a version is signed and tagged on, cut from the default branch once that version's specs are done.` |
| The QA page | title `From criteria to a signature`; lead `For a QA person who turns acceptance criteria into proofs and signs the rules they cover.` |
| The frameworks reference (C13) | `` `conftest.py` or `pytest.ini` at the root, `[tool.pytest` in `pyproject.toml`, or a file named `test_*.py` under `tests/` `` |
| `RELEASE_NOTES.md` 0.10.0 | `**A number written twice or a line left from a merge conflict fails the spec.** Every rule of that spec reads failed with the reason, signing it and the tag are refused, and Left to do reads 1 spec to repair: purlin:spec.`; `**Drift reads your checkout after a merge.** It names each number written twice and which line moves, each test comment whose proof's wording changed, and the proofs added, changed and moved; it says how old your copy of the default branch is and never fetches.`; `**Every signature that ends says why**, one line naming the rule, the signer and the cause. A hand check's signature is bound to the wording alone.`; `**A signature counts only when its commit's signature verifies.**`; `**The tag is refused while the branch's copy on the host holds commits the checkout lacks.**`; `**The signing walk shows each proof's tied test.**`; `**A plain tests/test_*.py project is suggested pytest.**`; the format numbers of C12 |

## 8. Questions for the owner

**Q1. Which branch must a tag keep up with?**

Root: decision 102 says two things that meet here. A version is signed on a release branch, and
a tag is refused when the default branch on the host has moved past the commit being tagged. On
a release branch the default branch always moves on (new specs land there and wait for the next
version), so read literally the second would refuse every tag on a release branch.

- **(a) The branch being tagged, recommended.** The tag is refused when that branch's copy on the
  host holds commits this checkout lacks. On the default branch this is exactly the default
  branch; on `release/1.2.0` it is `origin/release/1.2.0`. Consequence: the release branch works
  as the docs teach, and the F9 case (tagging main while main moved) is refused.
- **(b) The default branch always.** Consequence: a tag on a release branch is refused as soon as
  anything lands on the default branch, so the release branch the docs teach cannot be tagged
  without first merging the default branch into it, bringing in the next version's specs.
- **(c) The default branch, only when tagging on it.** On any other branch nothing is checked.
  Consequence: the F9 case is refused on main, but two people tagging the same release branch
  are not warned.

**Answered by the owner, 2026-09-30: (a), the branch being tagged.** Every lane builds to (a).

## 9. Calls this plan makes

Not questions: each follows from decision 102 or the findings, and the owner may reverse any.

- "A number written twice" covers rule numbers as well as proof numbers: a rule written twice,
  which today is only warned of, now also fails its spec.
- The test run exits 1 while any spec under `specs/` is broken, whichever features it ran.
- `Left to do` counts broken specs, not their rules, under a kind of its own, `to_repair`, first,
  with the command `purlin:spec`; `to_fix` would have sent the person to `purlin:build`.
- A signature ended is reported while it stays the rule's newest counting one and nothing binds,
  at every gate; one that never counted is not reported, and one signed as not applying keeps
  decision 101's `to_confirm` line instead.
- Every cause that differs is named, joined `; `. The cause names the rule's test files, not the
  one file that changed, because a signature records one hash over them all.
- A hand check is a signature whose `test_hash_kind` is `manual`: every proof is `@manual` or has
  no test. A rule mixing a hand check with tested proofs is bound as now.
- Verifying a commit does not compare its key with the key the signature file names: this
  repository's fixtures record none, and decisions 48 and 52 keep who signed a matter for the
  system of record.
- Drift prints its new lines in every view where they concern everyone (a number twice, a changed
  comment), and the proofs added, changed and moved in `pm` and `qa`, as F7 asked. A proof
  removed is not listed, as the decision names three kinds.
- The evidence a version is signed on is committed on its release branch; the docs name no role
  that alone commits evidence.
- The signing walk shows each test's name, not its body.
- Old signature files are not removed (F12 called them harmless), and the docs are not changed
  for `gpg.ssh.allowedSignersFile` (F13), which decision 102 does not name.
