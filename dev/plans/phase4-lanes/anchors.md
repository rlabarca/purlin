# Lane `anchors` (phase 4, fan-out 1)

You are lane `anchors` of phase 4 of Purlin 0.10.0: sanity check 3 applied, with the owner's
answers of decision 98. Purlin is a Claude Code plugin for spec-driven development that uses
itself. This brief is complete in itself; the files below are where its words come from. No
reviewer follows you: you check your own work with the self-check at the end and report.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/p4-anchors`, branch `p4/anchors`, created
  from `main` after P1 merged:
  `git -C /Users/richlabarca/LocalCode/purlin worktree add /Users/richlabarca/LocalCode/purlin-wt/p4-anchors -b p4/anchors main`.
- Scratch folder: `<the scratchpad directory your session gives>/p4-anchors`.
  Nothing of yours goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`,
   `references/glossary.md`.
2. `dev/plans/three-levels.md` decisions 94 to 98 (decision 98 holds the answers of sanity check
   3); a later decision amends an earlier one.
3. `dev/plans/phase4-plan.md` sections 1, 4 (your row), 5, 6 and 11, and
   `dev/plans/phase4-contracts.md` whole: every line you print or quote is there, word for word.
4. `sanity-3.md` section 6 items 4, 20 and 34; section 7 fault 7; section 8 items 7 and 15;
   section 11 questions 7 and 8; section 5 rows 27 and 29.
5. `references/formats/spec_format.md` whole and `specs/_anchors/schema_spec_format.md`.

Section references such as "§6 item 5" are to `dev/plans/sanity-3.md`; "A<n>" is the owner's
answer <n> of decision 98; K-numbers are sections of the contracts.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/mcp/purlin/specs.py`
- `scripts/mcp/purlin/fingerprint.py`
- `scripts/mcp/purlin/evidence.py`
- `specs/mcp/specs.md`
- `specs/mcp/evidence.md`
- `specs/_anchors/*.md`
- `dev/test_specs_reader.py`
- `dev/test_schema_spec_format.py`
- `dev/test_security.py`
- `dev/test_fingerprint.py`
- `dev/test_evidence_reader.py`
- `references/formats/spec_format.md`
- `dev/test_e2e_required_rules.sh`

## The work

Build every item. Each names its source and the change; where it names a contract, the contract
is the words.

1. **`> Requires:` names anchors only** (A8; K2.2 anchors-1; call 3). `specs.rule_refs`
   follows a name only where it names an anchor, and through anchors transitively; a feature
   spec named there adds no rule, and a name no spec carries adds none, as today.
   `fingerprint`'s `spec` part covers the anchors a feature requires, transitively, and every
   global anchor; its module docstring and the docstring near line 378 say so.
   `specs.spec_mistakes` adds anchors-1 after the five lines of decision 97. Rules:
   schema_spec_format RULE-5 reads "`> Requires:` is a comma-separated list of anchor names,
   the project's own or pinned, whose rules are counted with this spec's own and carry the label
   `required`"; a new rule says a name that is a feature's spec is warned of and its rules do
   not apply, with three proofs (a feature naming a feature spec prints anchors-1 exactly; that
   feature proves none of the named spec's rules; an anchor naming a feature spec is warned of
   under the anchor's name). specs RULE-13 reads "... the rules of every anchor it requires and
   of every anchor those require in turn ..."; PROOF-37 becomes `login` requiring the anchor
   `api`, which requires the anchor `base`; PROOF-38 keeps its case with `base` an anchor.
   evidence PROOF-4's fixture makes `orders` an anchor under `specs/_anchors/`. Run
   `dev/test_e2e_required_rules.sh`: its `login` requires an anchor and holds.
2. **`> Highest-Rule:`** (A7; K4.1; call 4). A new schema_spec_format rule:
   "`> Highest-Rule: <n>` records the highest rule number the spec has ever held; it
   changes no fingerprint and no rule count", with three proofs: a spec with rules 1 to 3 and
   `> Highest-Rule: 12` reads exactly three rules; its fingerprint is the one it has with
   the line taken out; a `> Description:` above the line reads the same as with no such line.
   The parser needs no new field; change it only if a proof fails.
3. **Spec format 19** (K4.1 whole; CLAUDE.md "Format reference versioning"):
   `> Format-Version: 19` in the commit that changes `specs.py` for item 1, with the
   template, the two table rows, the "Rules format" sentence, "Requires behaviour", the example
   proofs at lines 138-139, 157-158 and 193-194 rewritten to the quality guide (§8 item 15), and
   `Windows: no run yet`.
4. **The unread-tags line** (§6 item 20; K2.2 anchors-2). specs PROOF-9 and PROOF-27 quote it
   whole.
5. **The selection reason** (§6 item 4; fault 7; K2.2 anchors-3). `fingerprint.NO_RUN_YET` is
   filled with `evidence.os_word(os_name)`. A new proof in `specs/mcp/evidence.md` under the
   rule that gives the selection reasons (add one if none holds it): a feature with no evidence,
   on this machine, is selected with `no run on <System> yet`, the test naming the
   running system's word. Lane `run` adjusts run_script PROOF-91 (K6).
6. **Ignored evidence files** (§6 item 34; K2.2 anchors-4 to anchors-7). evidence PROOF-18, 51,
   52 and 19 quote the new lines; one new proof that a file under `ci/` gets
   `Run purlin:test --remote to write it again.`
7. **The security anchor** (the orchestrator's ruling; plan section 12).
   `specs/_anchors/security_no_dangerous_patterns.md`:
   `> Scope: scripts/**/*.py, scripts/**/*.sh, scripts/**/*.js`, and the
   Description's two changes of section 12. Its rules and proofs stay. The status of this
   repository then prints none of the three `finds no file in git` lines.
8. **`> Format-Version: N`** (§5 row 27). A schema_spec_format rule, "The spec format page
   opens with the line `> Format-Version: <n>`, `<n>` a whole number", and one proof
   reading the page.
9. **`> Stack:`** (§5 row 29). A schema_spec_format rule, "`> Stack:` is read as one line
   and changes no fingerprint", with two proofs: the value read is the line's text; two specs
   differing only in `> Stack:` have the same fingerprint.
10. **`> Highest-Rule:`** (K4.2) in `specs/mcp/specs.md`, `specs/mcp/evidence.md` and both
    anchors under `specs/_anchors/`.

**You produce** for other lanes: anchors-1 to anchors-7 (K2.2); spec format 19 (K4.1); the
narrowed `> Requires:`.

**You consume**: core-7 (K6: schema_spec_format PROOF-55 and its test quote it after `core`
merged).

## How to number, split and write proofs (contracts K7)

- A new id is one more than the highest the spec has ever held: the larger of its
  `> Highest-Rule:` and the highest of its own `RULE-`/`PROOF-` ids in
  `git log -p --follow -- <spec>` (its own lines only, not ids a proof or another
  spec names). A deleted number is never reused. Every spec you own carries
  `> Highest-Rule: <n>` after its last other `>` line, raised with every rule you add.
- Every proof you write or reword holds one case (one starting situation, one action, what is
  seen) in at most 60 words; a list of like inputs sharing one action and one kind of result is
  one case. It names no source file, no test and no test framework; a library's public names and
  error types may appear. It has a test of its own with `# purlin: <feature> PROOF-<n>`
  (in the file's comment syntax) directly above it.
- A statement of `sanity-3.md` section 5 gets a rule and one proof per line or case, each
  quoting the printed line character for character as the code prints it after your change.
- Split a rule of yours where its text states two claims whose proofs fall into groups each
  showing one: the first claim keeps the id, each other claim takes a new id, proofs keep their
  ids and text and only their `(RULE-N)` changes. List each split.
- Delete outright what is retired: no test that a removed thing is absent, nothing added to
  `dev/test_vocabulary.py`.
- A format you change updates its file under `references/formats/` in the same commit, with the
  Format-Version K4 names (none but the spec format changes number).

## How to test

```
export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH
cd /Users/richlabarca/LocalCode/purlin-wt/p4-anchors
.venv/bin/python -m pytest dev/test_specs_reader.py dev/test_schema_spec_format.py dev/test_security.py dev/test_fingerprint.py dev/test_evidence_reader.py -q
bash dev/test_e2e_required_rules.sh
bash dev/run_tests.sh --fast
```

If `.venv` is missing in the worktree, use
`/Users/richlabarca/LocalCode/purlin/.venv/bin/python`. Do not run the full sweep; integration
runs it once. A failure in a test file you do not own: check the contracts' K6. If K6 predicts
it, leave it; otherwise report the test, its assertion and the value it saw. Never edit that
file.

## Limits

- Commit on `p4/anchors` only, with the prefixes of `references/commit_conventions.md`, each
  message ending with the attribution lines your session gives. Push nothing, tag nothing, open
  no pull request.
- Run no `purlin:audit` and no `purlin:sign`; never start the real `claude` program, a real git
  host, `gh`, `az` or any network service.
- Stage no generated file: `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`,
  `.github/workflows/purlin.yml`, `docs/images/**`.
- Keep each skill and `agents/purlin.md` within its line ceiling (status 100, test 120, build
  130, init 250, audit 105, sign 185, export 90, spec 210, spec-from-code 130, drift 150, anchor
  160, agent 135): a change cuts as many lines as it adds.
- A call no decision or contract makes: build the rest, leave that thing as it is, report it. A
  word a person reads that the contracts do not give: do not choose it; leave the line as it is
  and report it.
- Do not touch `/Users/richlabarca/LocalCode/purlin-wt/winfix-1`, `docs/` or `README.md`.
- Before you finish: `git rebase main`, rerun your files and `--fast`, fix your own files
  where a lane merged earlier changed a result K6 predicts.

## Self-check (run it, then report each result)

1. Every proof you wrote or reworded: one case, at most 60 words (count them), and a test of its
   own with its marker directly above it. List any that fails.
2. Every printed line you built or quote: character for character as K2 and K3 give it. Grep
   your files for each old form in K2 for your lane; none remains.
3. No generated file is staged: `git diff --cached --name-only main` names none of
   `scripts/report/purlin-report.html`, `purlin-report.html`, `.purlin/evidence/**`,
   `.purlin/tests.md`, `.purlin/report-data.js`, `.github/workflows/purlin.yml`,
   `docs/images/**`.
4. No id reused: for each spec you own, every RULE and PROOF id you added is above the highest
   that spec had ever held before you began (K7), and its `> Highest-Rule:` is its highest
   rule number now.
5. Break each of these on purpose, one at a time, run its test, see it fail, then restore the
   file with `git checkout -- <file>` (never `git checkout -- specs/`): (a)
   let `rule_refs` follow a feature spec again: the "proves none of the named spec's rules"
   proof fails; (b) drop anchors-1 from `spec_mistakes`: its proof fails; (c) print the `local/`
   fix for a file under `ci/`: the new `ci/` proof fails.

## Report, as your final message

- The branch and its commits (sha and subject).
- For each spec you own: its highest RULE and PROOF id, its `> Highest-Rule:`, and its rule
  and proof counts before and after.
- Tests in your files before and after, and the `--fast` result.
- Each item of "The work": done, or left and why.
- Every split, as
  `<spec> RULE-<old> -> RULE-<a> (<claim>), RULE-<b> (<claim>)`, and every
  proof deleted, moved or re-pointed.
- Every word a person reads that you had to write and the contracts did not give.
- Every failure in a file you do not own.
- The self-check: each of its five results, and for the breaks, the test that failed.
