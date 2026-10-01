# Coverage review: did the weight pass remove too many protections?

Read-only review of `main` at `cb9431982`, 2026-10-01. Nothing was run: every finding is read from
the specs, the code and the tests. The items marked *read, not reproduced* should be reproduced
before a rule is written for them.

## Verdict

**No, the pass itself removed few protections; the gaps that matter were never rules.** Of 381
things the pass took away (363 rule ids and 18 clauses dropped from reworded rules), 143 were
wording, cosmetic or repeats, 33 are moot by a later decision, 194 are still held by a kept or
later rule, and 11 are protections nothing holds today. Of those 11 only one is high risk (a
marker inside a string is not a marker). The larger finding is from reading the code: 58 refusing
or not-counting cases in the sign-off, the evidence, the run and the audit have no proof in the
refusing direction, and seventeen of the items below are holes in the product that need a code change, not only missing proofs. They sit
in the two places Purlin exists for: **the sign-off** (the status reads `signed` from any tag,
a package is trusted by its stored fingerprint, a slow result is re-stamped as taken on this
version) and **the audit's `strong`** (a test that cannot run in the copy reads `caught`; a
`claude` that answers nothing counts as the model having run). The run, the evidence writer,
setup and the dashboard are well covered.

Adding everything below is **22 rules and 51 proofs** (410 to 432 rules, 820 to 871 proofs), with
5 kept rules reworded. Two more (one rule, two proofs) wait on an owner answer.

## Counts

Part 1, what the pass removed (363 rule ids plus 18 dropped clauses):

| Class | Core (states, evidence, sign-off, package, audit) | Run, reports, drift, formats, server | Setup, upgrade, anchors, dashboard, skills | Total |
|---|---:|---:|---:|---:|
| (a) wording, cosmetic, repeat | 32 | 34 | 77 | 143 |
| (b) moot by a later decision | 2 | 29 | 2 | 33 |
| (c) protection nothing covers | 6 | 3 | 2 | 11 |
| (d) covered by a named rule | 57 | 90 | 47 | 194 |

Part 2, refusing and not-counting cases read out of the code:

| Area | Cases | Proven in the refusing direction | Not proven |
|---|---:|---:|---:|
| Sign-off and package | 66 | 38 | 28 |
| Evidence and run | 65 | 51 | 14 |
| Audit | 39 | 23 | 16 |

The known open items: all five are **confirmed**. The stop's line for another machine has no
proof; the upgrade's workflow removal has no proof; `write_could_not_run` has no caller; a tracked
file under `.purlin/` is not a changed file to the sign-off; a slow NUnit `[TestCase]` runs after
`Left out` is printed (its result is true and counts; only the line is wrong). Also confirmed:
decision 120's last note at the hand-check stop is not built, not ruled and not proven in
`sign.py`; only the status and the dashboard show it.

## Proposed rules, in priority order

`RULE-N` and `PROOF-N` take the spec's next numbers. "Code" means the product must change before
the proof can pass; the others pass on today's code.

### Tier 1: the sign-off or the evidence can be wrong and nobody sees it

**1. The status reads `signed` only where a sign-off counts** (`states`, beside RULE-59). Code.
`facts.py:42-61` reads any `signed/*` tag; `signatures.load_signoffs` and `counts` are called by
no command, so RULE-20, RULE-97 and RULE-108 are proven on a function nothing uses. `git tag
signed/9.9.9` by hand reads as signed. 1 rule, 2 proofs.
- RULE-N: The sign-off reads `signed <version>` only where `signed/<version>` names a commit holding the package for that version and at least one sign-off that counts; otherwise it reads `not signed`, and the status warns with one line naming the tag and why
- PROOF-N (RULE-N): A project with committed evidence that passes carries the tag `signed/9.9.9`, written by hand with `git tag`, and no file under `.purlin/evidence/package/`; the sign-off reads `not signed`, and the warnings hold one line naming `signed/9.9.9`
- PROOF-N (RULE-N): The walk signs `2.1.0`, then a commit made with no signature changes the sign-off file's note; the sign-off reads `not signed`

**2. A package is trusted by its content, not its stored fingerprint** (`signatures`, RULE-108
reworded). Code. `signatures.py:55-69` and `sign.py:439` read the `fingerprint` field; a commit
that changes `"failed"` to `"passed"` and leaves the field alone keeps every sign-off counting,
and a second signer signs the edited content. 0 rules, 1 proof.
- RULE-108: A sign-off counts only while its `package_hash` equals the fingerprint computed over the package `HEAD` holds for its version, and a later sign-off is refused, with one line and nothing written, where that package does not match its own fingerprint
- PROOF-N (RULE-108): The walk signs `2.1.0`, then the committed package's first `"passed"` is changed to `"failed"` with `fingerprint` left as it was, and committed; the sign-off no longer counts, and a second signer's walk prints one line beginning `No sign-off:` naming `.purlin/evidence/package/2.1.0.json`, and exits 1

**3. A kept slow result is not re-stamped as taken on this version** (`run_script`, narrowing
RULE-106). Code, and an owner decision; *read, not reproduced*. `purlin_run.py:758-796`: a named
run copies the slow pass from the section on disk and writes a section with this run's commit,
machine and person, so the sign-off takes an integration result as run on the version being
signed. 1 rule, 1 proof.
- RULE-N: A result kept for a slow proof counts for the status alone: a section holding one names the commit the slow test last ran on, so the sign-off refuses it until `purlin:test --all` runs on the version being signed
- PROOF-N (RULE-N): `--all --test --commit` passes `feat`'s slow `PROOF-2`; `README.md`, which no scope names, is changed and committed; `--feature feat --test --commit` runs; `purlin:sign --show` exits 1 naming `feat` as a result not taken on this version of the code

**4. A rule never run, a slow proof not run and a rule with no result on its system stop the
sign-off** (`signatures` RULE-102, proofs only). `sign.py:310-338`; PROOF-206 shows a failing rule
alone. 0 rules, 2 proofs.
- PROOF-N (RULE-102): `login RULE-2` has `PROOF-2` tagged `@env(windows)`, and the committed evidence holds results for Linux/Unix alone, all passing; the walk prints only one line beginning `No sign-off: 1 rule does not pass at` and naming `login RULE-2`, and exits 1
- PROOF-N (RULE-102): `login RULE-2` has `PROOF-2` tagged `@slow`, and the committed evidence was written by `purlin:test` with no `--all`, every other rule passing; the walk prints only one line beginning `No sign-off: 1 rule does not pass at` and naming `login RULE-2`, and exits 1

**5. A marker inside a string or a here document is not a marker** (`reports`; restores old
RULE-2, the one high-risk rule the pass removed). The code still does it
(`markers.py:368-391, 415-583`), with no rule. Without it a fixture string holding a marker ties
to the next test and a rule reads `passed` on a test that never showed it. 1 rule, 1 proof.
- RULE-N: A marker-shaped line inside a string of a test file, or inside a here document of a shell file, is not a marker and ties nothing
- PROOF-N (RULE-N): A Python test file holds `# purlin: login PROOF-1` on line 2, inside a triple-quoted string, and `# purlin: login PROOF-2` as a comment on line 5 above the passing `test_ok`; one marker is read, `PROOF-2` at line 5, and the evidence holds no `pass` for `PROOF-1`

### Tier 2: the audit says `strong` with nothing behind it, or can touch the person's code

**6. The test is run in the copy before a bug is planted** (`planted_bug`). Code.
`targeted_break.py:197-306`: the copy holds no ignored file (`node_modules`, a built file) and
there is no baseline run, so a test that cannot run there reads `caught` for every bug and the
rule reads `strong`. 1 rule, 1 proof.
- RULE-N: The proof's test is run in the copy before the bug is planted; where it does not pass there, no bug is planted and the result reads `not made` with the reason `the test does not pass in a copy of the project`
- PROOF-N (RULE-N): The test of `PROOF-1` reads `data/built.json`, a file git ignores; the model answers `file: src/age.py`, `before:` `return days`, `after:` `return 0`; the result reads `not made` with the reason `the test does not pass in a copy of the project`, not `caught`

**7. A `claude` that answers nothing is the model not reached** (`ai_audit`, extending RULE-39 or
new). Code. `ai_audit.py:352-367`: exit 0 with empty or non-JSON output counts as reached, the bug
reads `not made`, the rule is written `strong`. This defeats decision 117. 1 rule, 1 proof.
- RULE-N: An answer from `claude` that is empty, or whose JSON reports an error, is the model not reached, with the reason `claude gave no answer`
- PROOF-N (RULE-N): `claude` exits `0` and prints nothing at every call, and no spot test fires on the test of `RULE-2`; no audit entry is written for `RULE-2` and the audit prints `The model could not be reached: claude gave no answer. 1 rule stays not audited. Run purlin:audit again.`

**8. The model's reading is inside the before-and-after check** (`planted_bug` RULE-6 widened).
Code. `audit_run.py:364`: `claude -p` runs in the project folder with the person's own tool
permissions; only the planted bug is guarded. The planted bug itself cannot change the project:
every write goes into the temp copy. 1 rule, 1 proof.
- RULE-N: When a file of the project changes while the model reads a rule, the audit stops with one line naming the file, writes no audit entry and exits 1
- PROOF-N (RULE-N): The `claude` asked to read `RULE-2` appends a line to `src/login.py` in the project; the audit prints one line beginning `The audit stopped: src/login.py changed`, exits `1`, and `.purlin/evidence/local/login.json` holds the bytes it held before

**9. A bug planted in the proof's own test file is not applied** (`planted_bug`, extending
RULE-12). Code. Only where a `> Scope:` reaches a test file. 1 rule, 1 proof.
- RULE-N: A change to a file that holds one of the proof's tests is not applied and reads `not made`
- PROOF-N (RULE-N): The feature's `> Scope:` names `tests/test_age.py` and the model answers `file: tests/test_age.py`, `before:` `assert age(s) == 90`, `after:` `assert age(s) == 0`; the result reads `not made` and the test of `PROOF-1` is not run

### Tier 3: the sign-off's own walk

**10. A hand check's stop shows the last note** (`signatures`; decisions 110 and 120, not built).
Code. `sign.py:638-656`. 1 rule, 1 proof.
- RULE-N: A hand check's stop shows each note of the newest sign-off holding one for that rule, as `noted at the sign-off of <version> by <signer>, <n> commits since: <note>`, and no such line before any sign-off
- PROOF-N (RULE-N): `quinn.qa@labconnect.example` signed `0.1.0` with the note `the tube is red` at `login RULE-2`; four commits later the walk for `0.2.0` shows at that stop `noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, 4 commits since: the tube is red`

**11. A tag git could not write is written by the next run** (`signatures`; the pass dropped the
clause from RULE-121). Code; *read, not reproduced*. `sign.py:875-882`, then `:467`: the commit is
made, the tag fails, and a rerun is refused as already signed, so the tag is never written.
1 rule, 1 proof.
- RULE-N: Where the sign-off's commit is made and git cannot write `signed/<version>`, the command prints one line naming the tag and git's reason and exits 1, and the next `purlin:sign` writes the tag on that commit and adds no second sign-off
- PROOF-N (RULE-N): With git unable to write the tag, the first sign-off of `2.1.0` makes its commit, prints a line beginning `No tag: git could not write signed/2.1.0:` and exits 1; with the cause removed, `purlin:sign` run again exits 0, `signed/2.1.0` names that commit, and no commit was added

**12. The settings file is part of the project** (`package` RULE-33 reworded; `signatures`
RULE-102; `evidence_writer`). Code, and one owner decision settles all three.
`package.py:74` and `purlin_run.py:855` skip everything under `.purlin/`, so a changed `tests`
command ends no result, is not a changed file to the sign-off, and a run under it reads clean.
Decision 100 lists what is not the project: results, signatures, the package. 1 rule, 3 proofs.
- package RULE-33, its last words changed to: `... changes only files under .purlin/evidence/`
- PROOF-N (package RULE-33): The tests run and are committed at `<c>`, then a commit changes the `tests` command in `.purlin/config.json`; `purlin:sign` prints only one line beginning `No sign-off: these results were not taken on this version of the code` and exits 1
- PROOF-N (signatures RULE-102): With committed evidence that passes, `.purlin/config.json` is changed and not committed; the walk prints only `No sign-off: 1 file is changed and not committed. Commit it or set it aside, then run purlin:sign again.` and exits 1
- RULE-N (evidence_writer): A run made while `.purlin/config.json` differs from the commit writes its section with `dirty` true
- PROOF-N (RULE-N): In a git checkout whose spec and test are committed, the `tests` command in `.purlin/config.json` is edited and not committed; `--all --test` writes a section whose `dirty` is true

**13. A spec mistake and a stale test comment stop the sign-off** (`signatures`). The code refuses
(`sign.py:320-332`, decisions 102 and 105); no rule says so. 1 rule, 1 proof.
- RULE-N: The command refuses, with one line, nothing written and exit 1, while a spec holds a rule or proof number twice or a merge-conflict line, and while a test comment is to be corrected
- PROOF-N (RULE-N): `specs/auth/login.md` holds two lines numbered `RULE-2`; the walk prints one line beginning `No sign-off:` and naming `login RULE-2`, writes no file and exits 1

**14. A sign-off is read as `HEAD` holds it** (`signatures`). Code. `signatures.py:91` reads the
working tree and `payload.py:771-810` shows every note, so a note typed into the file by hand
reads on the status as a signer's. 1 rule, 1 proof.
- RULE-N: A sign-off is read as `HEAD` holds it: a file not tracked, or changed and not committed, does not count, and no note of a sign-off that does not count is shown
- PROOF-N (RULE-N): After `quinn.qa@labconnect.example` signs `0.1.0` with the note `the tube is red`, the file's note is edited to `the tube is blue` and not committed; `login RULE-2`'s strong cell carries no reason holding `the tube is blue`

**15. Two signers whose addresses share a name each keep a sign-off** (`signatures`). Code.
`signatures.py:38-42`: the file is named by the part before `@`, so `jane@labs.org` is refused as
having signed after `jane@acme.com`. 1 rule, 1 proof.
- RULE-N: Two signers whose addresses differ each keep a sign-off of one version, and the first signer's file is left as it was
- PROOF-N (RULE-N): `jane@acme.com` signs `2.1.0`, then `jane@labs.org` signs it; the folder `2.1.0.signoffs` holds two files, one reading signer `jane@acme.com` and one `jane@labs.org`, and the first file's bytes are unchanged

### Tier 4: the collaboration, setup and anchors

**16. A section taken over uncommitted changes is cleared by running again**
(`evidence_writer`, RULE-31 amended). Code. `evidence.py:274-277`: `dirty` is left out of the
comparison, so the sign-off's advice to run again changes nothing and the person is stuck.
0 rules, 1 proof.
- RULE-31, add: `A section whose dirty differs from the one on disk replaces it`
- PROOF-N (RULE-31): `--all --test` runs while `notes.txt` is written and not added to git, and the section's `dirty` is true; `notes.txt` is deleted and `--all --test` runs again on the same commit; the section's `dirty` is false

**17. Why a rule stayed not audited is recorded, or the reader goes** (`ai_audit`). Code.
`scripts/run/evidence.py:491` has no caller; `states` PROOF-71 passes on a file the test writes
itself. Wire it (below) or delete the function, the reader and PROOF-71. 1 rule, 1 proof.
- RULE-N: When the model cannot be reached for a rule, the audit records the cause under `.purlin/runtime/`, and the status gives it as the rule's reason until an audit reads the rule; nothing about it enters the evidence
- PROOF-N (RULE-N): `claude` exits `1` at every call and the audit reads `login RULE-2`, which passes; afterwards `RULE-2`'s strong cell reads `not audited` with a reason starting `the AI audit could not run:`, and `.purlin/evidence/local/login.json` holds no audit entry for `RULE-2`

**18. The upgrade removes only the workflow 0.9.5 wrote** (`init/update`; restores old RULE-15).
`update.py:496-522` deletes every workflow whose text holds `.proofs-`. 1 rule, 1 proof.
- RULE-N: The update removes a workflow under `.github/workflows/` only where it wrote 0.9.5's proof files, backs it up first, and leaves every other workflow as it was
- PROOF-N (RULE-N): The sample 0.9.5 project holds `purlin-proofs.yml`, which commits `*.proofs-*.json`, and `ci.yml` running `pytest`; after the update with `--yes` the first is gone with a backup holding its bytes, `ci.yml` is byte for byte as it was, and the output holds `removed 1 workflow that committed proof files`

**19. The upgrade leaves a remote anchor's source and pin alone** (`init/update`; restores the
clause of old RULE-24). Code: `FIGMA_SOURCE_RE` at `update.py:57` is `Source:.*figma`, so
`acme/figma-tokens.git` loses its source and pin today. 1 rule, 1 proof.
- RULE-N: An anchor whose `> Source:` is a git address keeps its `> Source:` and `> Pinned:` lines through the update, byte for byte
- PROOF-N (RULE-N): An anchor whose `> Source:` is `https://github.com/acme/figma-tokens.git specs/tokens.md` with a `> Pinned:` sha of 40 characters is exactly what it was after the update with `--yes`, and no backup is written beside it

**20. `purlin:anchor add` writes only under the project and never over an anchor** (`upstream`).
Code; not caused by the pass. `upstream.py:175` joins `--name` unchecked (`--name ../../x` writes
outside the project); `:305` overwrites the project's own anchor of the same name. 1 rule,
2 proofs.
- PROOF-N (RULE-22): The published anchor is added with `--name ../../outside`; it exits 2, the answer reads `error`, `specs/_anchors/` stays empty and no `outside.md` exists under the folder around the project
- RULE-N: `add` refuses a name an anchor in the project already holds, writes nothing and names `purlin:anchor sync <name>`
- PROOF-N (RULE-N): With `specs/_anchors/no_eval.md` holding the project's own rule `No eval in scripts`, the published anchor is added as `no_eval`; it exits 2, the answer reads `error`, and the file holds exactly its text from before

**21. A test whose source cannot be found is named** (`plain_checks`). Code. `audit_run.py:217`
passes over it in silence. 1 rule, 1 proof.
- RULE-N: A marked test whose source cannot be found is named once, as `<file>::<test>: its source was not found, so the spot tests did not read it.`
- PROOF-N (RULE-N): The evidence names `test_renamed_away` for `PROOF-1`, which `tests/test_login.py` no longer holds; the audit prints `tests/test_login.py::test_renamed_away: its source was not found, so the spot tests did not read it.` exactly once

### Tier 5: proofs to add under rules that exist (no new rule, 21 proofs)

Each rule says the thing; no proof shows the refusing direction. The full text of each proof is in
the appendix section named.

| Rule | The case with no proof | Appendix |
|---|---|---|
| `signatures` RULE-126 | a weak hand check's stop ends on the audit's findings (old RULE-116, removed by the pass) | B, C1 |
| `signatures` RULE-126 | the stop's two lines for a second system run on another machine (known item) | E, G11 |
| `states` RULE-16 | a hand check the audit found weak reads `weak` (old RULE-111, removed by the pass) | B, C2 |
| `signatures` RULE-111 | an answers file without `sign: true`, or with `"sign": "yes"`, signs nothing | E, G6 |
| `package` RULE-33 | a result from a commit `HEAD` does not descend from | E, G10 |
| `package` RULE-22 | `--check` on a package rewritten with `\r\n` | E, G13 |
| `signatures` RULE-125 | a `.purlin/config.json` that cannot be read (old RULE-67; add the case to the list) | B, C4 |
| `run_script` RULE-100 | a run that selects nothing exits 1 over failing evidence | F, U4 |
| `run_script` RULE-12 | `--ci` exits 1 when a tagged test fails | F, U5 |
| `evidence_writer` RULE-19 | `--commit` leaves an unrelated changed file out | F, U6b |
| `reports` RULE-33 | a marker naming a rule that has proofs (old RULE-19) | C, item 3 |
| `states` RULE-9 | a current `ci` failure beside a newer `local` pass reads `failed` | F, U8 |
| `run_script` RULE-98 | `--project-root ''` exits 2 (old RULE-41) | C, item 2 |
| `planted_bug` RULE-6 | a stopped audit leaves the evidence file's bytes as they were | G, F |
| `ai_audit` RULE-36 | a changed test plants the bug again | G, G |
| `ai_audit` RULE-43 | the bug answered and the reading not; a kept survived bug with the model unreached (2 proofs) | G, I |
| `ai_audit` RULE-33 | a rule whose every bug was `not made` reads `strong` (prove as written, or change: owner) | G, C |
| `evidence` RULE-16 | both sources hold a matching audit entry, the later answers (old RULE-28; add the clause) | B, C5 |
| `ai_audit` (scope) | the request to the model holds no file outside the scope | G, L |
| `planted_bug` RULE-1 | the project's bytes are unchanged after a test runs past its limit | G, N |

### Part 3: the skills (4 rules, 4 proofs, all in `instructions/purlin_agent`)

Nothing is broken today: every path, flag, command name, commit subject and quoted refusal in the
ten skills and the agent definition matches the scripts and references. Only the init skill has a
proof of that kind. Mechanical and not covered:

- RULE-N: Every path under `scripts/`, `references/`, `templates/`, `skills/` or `docs/` that a skill or the agent definition names is a file or folder in the repository
- PROOF-N: Each such path read out of the ten `SKILL.md` files and `agents/purlin.md` exists; the same check on a copy of the sign skill naming `scripts/review/signoff.py` lists that path
- RULE-N: Every flag a skill writes on a line that runs a script is one that script takes
- PROOF-N: Each `--flag` on a line of a `SKILL.md` naming a `scripts/**/*.py` is in that script's `--help`; the same check on a copy of the test skill passing `--remote` to `purlin_run.py` lists `--remote`
- RULE-N: The answers file the sign skill shows is one `purlin:sign --answers` walks without a refusal about the file
- PROOF-N: The JSON block under `Step 5` of `skills/sign/SKILL.md`, written to `.purlin/runtime/signoff-answers.json` in a project whose hand checks are `accession_screen RULE-1` and `sample_age RULE-6`, is walked with `--answers`; it exits 0 and the sign-off holds the note `the tube is red`
- RULE-N: No skill, agent definition or reference names a path under `dev/`, `/dev/null` aside
- PROOF-N: No line of `skills/*/SKILL.md`, `agents/purlin.md` or `references/**/*.md` holds `dev/` once every `/dev/null` is set aside; the same check on a copy of the build skill naming `dev/test_x.py` lists that line

Judgment, for the on-demand real-skills check and no proof: whether `purlin:spec`'s rules say what
the requirement meant; whether `purlin:build`'s code meets the rules and each comment sits on the
right test; which features `purlin:spec-from-code` finds; the audit's reading and the bug it
picks; how `purlin:sign` puts each stop to the person; which next command a skill suggests.

## Questions for the owner

1. **Slow results (item 3).** Is a slow pass carried by a named run a result "taken on this exact
   version" for the sign-off, or must `purlin:test --all` run on the version being signed?
2. **The settings file (item 12).** Does a change to `.purlin/config.json` end results and a
   sign-off, as any project file does?
3. **`strong` with no bug planted** (`ai_audit` RULE-33). Should a rule for which the model
   planted no bug read `strong`, or stay not audited?
4. **An old `strong` after the model could not be reached** (appendix G, J). Keep the earlier
   entry, or remove it? If removed: 1 rule, 1 proof more.
5. **Why not audited (item 17).** Wire `write_could_not_run`, or delete it with its reader?
6. **A `key::` literal as the signing key** (appendix B, C6) and **the NUnit line** (appendix F,
   U9): keep and prove, or delete the code. Neither is counted above.

## Totals

| | New rules | Rules reworded | Proofs |
|---|---:|---:|---:|
| Tiers 1 to 4 (items 1 to 21) | 18 | 3 (`signatures` 108, `package` 33, `evidence_writer` 31) | 26 |
| Tier 5 | 0 | 2 (`signatures` 125, `evidence` 16) | 21 |
| Part 3 | 4 | 0 | 4 |
| **Total** | **22** | **5** | **51** |

Restored from the pass: items 5, 11, 18, 19 and seven of the Tier 5 proofs. Everything else was
never a rule. Seventeen items need a code change first: 1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16,
17 (if wired), 19, 20, 21.

---

# Appendices

The slice reports as written, with every removed rule classed and every case listed.

- A. Part 1, counts and classes: core specs (then its (c) items, B)
- C. Part 1: run, reports, host, drift, formats, server, summary
- D. Part 1: setup, upgrade, anchors, dashboard, instructions, skills
- E. Part 2: the sign-off and the package (66 cases, gaps G0 to G13)
- F. Part 2: the evidence and the run (65 cases, gaps U1 to U10)
- G. Part 2: the audit (39 cases, gaps A to N)
- H. Part 3: the skills



---

## Appendix A and B. Part 1: core specs

# Part 1, core specs: what the weight pass removed

Slice: `mcp/states`, `mcp/evidence`, `run/evidence_writer`, `review/signatures`, `export/package`,
`review/ai_audit`, `review/plain_checks`, `review/planted_bug`. 89 rule ids removed, plus 8 kept
rules whose new wording dropped a clause. Checked against today's specs and proofs at HEAD and
the code under `scripts/`.

## 1. Counts

| Spec | removed | (a) | (b) | (c) | (d) | clauses dropped (class) |
|---|---|---|---|---|---|---|
| mcp/states | 31 | 18 | 0 | 1 | 12 | 0 |
| mcp/evidence | 14 | 3 | 0 | 1 | 10 | 1 (a) |
| run/evidence_writer | 6 | 1 | 1 | 0 | 4 | 2 (1 d, 1 a) |
| review/signatures | 16 | 3 | 0 | 2 | 11 | 3 (1 a, 2 c) |
| export/package | 2 | 0 | 0 | 0 | 2 | 1 (a) |
| review/ai_audit | 16 | 2 | 1 | 0 | 13 | 1 (a) |
| review/plain_checks | 1 | 0 | 0 | 0 | 1 | 0 |
| review/planted_bug | 3 | 0 | 0 | 0 | 3 | 0 |
| **Total** | **89** | **27** | **2** | **4** | **56** | **8: 5 a, 2 c, 1 d** |

Six (c) items in all: 4 removed rules and 2 dropped clauses. Two of the six are "rule exists, no
proof for this case".

## 2. One line per removed rule

### mcp/states
- RULE-57 (d): states RULE-117, PROOF-66 shows a failing local section beside a passing `ci` one.
- RULE-44 (d): states RULE-117, PROOF-53 shows `partial`, its reasons, bucket and flag.
- RULE-11 (d): states RULE-118, PROOF-13 shows `waiting`, not `weak`.
- RULE-15 (d): states RULE-118, PROOF-71 shows `not audited` with the could-not-run reason.
- RULE-25 (a): the rollup's key list, shape only; RULE-27 and RULE-48 hold what matters.
- RULE-26 (d): states RULE-119, PROOF-30 counts anchor rules once in the summary.
- RULE-80 (a): one payload key's source; decision 120 takes the host address out anyway.
- RULE-82 (a): payload key for the system words; display detail.
- RULE-84 (a): payload shape of a proof entry; RULE-71 covers each proof's result.
- RULE-32 (d): states RULE-120, the data file reads back as the payload.
- RULE-36 (a): table cell wording; RULE-121 and RULE-49 keep the columns.
- RULE-39 (a): wording of the no-specs message; RULE-122 names the case.
- RULE-79 (d): states RULE-122, PROOF-212 shows the unreadable settings sentence.
- RULE-41 (a): one advice line for a 0.9.5 key; wording.
- RULE-91 (d): states RULE-59, PROOF-170 shows `1.10.0` beating `1.9.0` and `beta`.
- RULE-62 (a): the `incomplete` payload flags; evidence RULE-6 keeps the reason.
- RULE-64 (a): wording of the no-scope line; RULE-122 names the case.
- RULE-66 (d): states RULE-118, PROOF-139 shows `no proof` and `left` `no_proof`.
- RULE-70 (a): the dashboard's sample payloads match the builder; a fixture check.
- RULE-72 (a): one table cell's wording.
- RULE-87 (a): payload shape; every `left` value is proven by the rule that sets it.
- RULE-92 (d): states RULE-120, the data file holds the run's results.
- RULE-93 (a): wording of the settings problem lines; RULE-122 names the case.
- RULE-94 (a): wording of the uncommitted-spec line; informative.
- RULE-95 (d): states RULE-122, PROOF-231 and PROOF-234 show the pin behind and rejected.
- RULE-97 (d): states RULE-119, PROOF-238 shows a feature's row counting its own rules.
- RULE-99 (a): the `Anchors` and `Specs` lines of the table; RULE-121 holds them.
- RULE-105 (a): wording of the scope-finds-nothing line; decision 113 reworded it (RULE-123).
- RULE-106 (a): payload shape; every cell rule already yields both cells.
- RULE-111 (**c**): RULE-16 says "unless its audit reads `weak`"; no proof shows that case.
- RULE-114 (a): an informative reason on a rule not yet audited again; decides nothing.

### mcp/evidence
- RULE-4 (d): evidence RULE-34, PROOF-32.
- RULE-9 (a): an internal error type for a name no spec defines.
- RULE-10 (d): evidence RULE-15, PROOF-55 and PROOF-57 name the parts that differ.
- RULE-12 (d): evidence RULE-35, PROOF-18 and PROOF-52.
- RULE-13 (d): evidence RULE-35, PROOF-19; states RULE-42 too.
- RULE-19 (a): display words for a system; states RULE-6 and RULE-9 use them.
- RULE-21 (d): evidence RULE-34, PROOF-32 edits without committing.
- RULE-22 (d): evidence RULE-2 holds the `> Description:` clause.
- RULE-24 (d): evidence RULE-34, PROOF-7 (a folder).
- RULE-25 (d): evidence RULE-34, PROOF-8 (a glob).
- RULE-26 (a): test files under `node_modules`, `bin`, `obj`; an edge, `mutants` gone (109).
- RULE-28 (**c**): two sources holding a matching audit entry; no rule today says which wins.
- RULE-29 (d): run_script RULE-101, PROOF-91 selects with `no run on <System> yet`.
- RULE-33 (d): run_script RULE-55, PROOF-90 selects the anchor after any edit.
- RULE-17 clause "`local` winning a tie" (a): a tie on `at` to the second, no user meets.

### run/evidence_writer
- RULE-7 (d): evidence_writer RULE-31, PROOF-91.
- RULE-10 (d): evidence_writer RULE-32, PROOF-10 and PROOF-39.
- RULE-21 (d): evidence_writer RULE-32, PROOF-38 shows `Evidence unchanged.` and no commit.
- RULE-11 (b): decision 112 cut runs outside a git repository.
- RULE-18 (a): an optional `notes` field; ai_audit RULE-38 and states RULE-61 read it.
- RULE-28 (d): evidence_writer RULE-31, PROOF-92 and PROOF-60.
- RULE-2 clause, all-`@manual` reads `passed` (d): evidence_writer RULE-30, PROOF-21, PROOF-24.
- RULE-13 clause, the template names no pattern (a): reworded to the behaviour in a set-up project.

### review/signatures
- RULE-21 (d): signatures RULE-20, "any key and whoever its author".
- RULE-22 (a): `--help` exits 0.
- RULE-67 (**c**): an unreadable settings file stops the sign-off; no rule or proof in any spec for `sign.py`.
- RULE-77 (a): an unknown option exits 2.
- RULE-79 (d): signatures RULE-125, PROOF-162 shows no commit and no sign-off file left.
- RULE-81 (a): `--project-root` not a directory exits 2.
- RULE-83 (d): signatures RULE-126 ("each proof with its tag").
- RULE-101 (d): signatures RULE-126, PROOF-200.
- RULE-103 (d): signatures RULE-127, PROOF-209.
- RULE-104 (d): signatures RULE-126, PROOF-211.
- RULE-112 (d): signatures RULE-127, PROOF-227, for a person's run; the remote-runner form is moot (decision 119) and gone from `sign.py`. No proof shows a second run line, from another machine or the source `ci`.
- RULE-113 (d): signatures RULE-110, PROOF-228.
- RULE-116 (**c**): RULE-126 names the audit's findings at a weak hand check's stop; no proof shows them.
- RULE-117 (d): signatures RULE-127, PROOF-232.
- RULE-119 (d): signatures RULE-106, PROOF-235.
- RULE-123 (d): signatures RULE-126, PROOF-242.
- RULE-60 clause, a `key::` literal (**c**, low): code still reads it, no rule or proof.
- RULE-102 clause, the order of the refusals (a): each refusal is proven alone (RULE-102, 124, 125).
- RULE-121 clause, `No tag: git could not write …` (**c**): the code still does it, no rule.

### export/package
- RULE-30 (d): package RULE-5, PROOF-63.
- RULE-31 (d): package RULE-2, PROOF-2 and PROOF-22 read `tag` `signed/beta`.
- RULE-23 clause "cannot be built" (a): no separate case from "cannot be written".

### review/ai_audit
- RULE-5 (d): ai_audit RULE-38, PROOF-98 and PROOF-38.
- RULE-7 (d): ai_audit RULE-39, PROOF-23.
- RULE-8 (d): ai_audit RULE-40, PROOF-34.
- RULE-9 (a): the shape of a `@manual` proof's entry in what the audit reads.
- RULE-10 (d): ai_audit RULE-40, PROOF-35.
- RULE-13 (d): ai_audit RULE-41, PROOF-74 and PROOF-76.
- RULE-14 (d): ai_audit RULE-42, PROOF-33.
- RULE-16 (d): ai_audit RULE-38, PROOF-38.
- RULE-17 (d): ai_audit RULE-42, PROOF-29, PROOF-87, PROOF-111.
- RULE-18 (d): ai_audit RULE-39, PROOF-24.
- RULE-19 (d): ai_audit RULE-39, PROOF-25.
- RULE-21 (d): ai_audit RULE-41, PROOF-81, every file under `.purlin/` keeps its bytes.
- RULE-29 (d): ai_audit RULE-41 (exit 2 for a root that is not a folder).
- RULE-30 (a): one sentence of the prompt; wording sent to a model.
- RULE-32 (b): decision 112, four calls at once is no longer a rule.
- RULE-34 (d): ai_audit RULE-38; evidence_writer RULE-12 lists `explanation`.
- RULE-2 clause, "asks for what was observed" (a): prompt wording; RULE-38 holds that the answer sets no verdict.

### review/plain_checks
- RULE-8 (d): plain_checks RULE-1 to RULE-6 each carry their own "is not flagged" case.

### review/planted_bug
- RULE-4 (d): planted_bug RULE-12, PROOF-5.
- RULE-9 (d): planted_bug RULE-12, PROOF-10.
- RULE-11 (d): planted_bug RULE-12, PROOF-15 (`README.md`, outside the scope).

## 3. The (c) items

### C1. A weak hand check shows the audit's findings at its stop (signatures, old RULE-116). Risk: high
- Old rule: "A hand check whose audit reads weak ends its stop on `What the audit found`, `  Weak.` and each finding".
- Today: `signatures` RULE-126 names it in words ("the audit's findings where it found the rule weak"). Its three proofs (200, 211, 242) show a tied test, the question and nothing to check. Rule exists, no proof for this case.
- What breaks unnoticed: the signer types a note at a hand check without seeing that the audit found the rule's tested proof weak. Decision 105 (N1) required it.
- Code: still does it, `scripts/review/sign.py:142` and `:653` (`render_stop`).
- Proposed: no new rule; one proof under RULE-126.
- Proof: `- PROOF-N (RULE-126): `login RULE-2` has `PROOF-2` marked `@manual` and `PROOF-3` tested, and the audit found it weak with the finding `PROOF-3 reads the status alone.`; its stop ends on `What the audit found`, `  Weak.` and `  PROOF-3 reads the status alone.`, before the question`

### C2. A hand check the audit found weak reads `weak` in the status (states, old RULE-111). Risk: medium
- Old rule: "A rule with a `@manual` proof whose audit reads `weak` reads `weak` in its strong cell, its reasons the audit's findings then `checked at sign-off`, and its `left` is `to_strengthen`".
- Today: `states` RULE-16 says "unless its audit reads `weak`". Its one proof (PROOF-19) shows the case before any audit. Rule exists, no proof for this case.
- What breaks unnoticed: a weak test under a hand check reads `checked at sign-off`, is not counted weak, and drops out of `Left to do` and the package's `audit` count.
- Code: still does it, in `scripts/mcp/purlin/` states code (the strong cell).
- Proposed: no new rule; one proof under RULE-16.
- Proof: `- PROOF-N (RULE-16): A rule has `PROOF-1` marked `@manual` and `PROOF-2` whose test passes, and its audit entry for the current hashes reads `weak` with the finding `PROOF-2 reads the status alone.`; the strong cell reads `weak`, its reasons that finding then `checked at sign-off`, and its `left` is `to_strengthen``

### C3. A tag git cannot write is said, and the command fails (signatures, old RULE-121 clause). Risk: medium
- Old clause: "where git cannot write the tag prints `No tag: git could not write signed/<version>: <git's message>.`"
- Today: no rule in any spec. RULE-120 covers only the tag being written.
- What breaks unnoticed: the first sign-off's commit is made, the tag is not, and the command reads as a success. Decision 106: the tag is how anyone finds what was signed.
- Code: still does it, `scripts/review/sign.py:99` and `:880-882`, exit 1 after the commit.
- Proposed rule: `- RULE-N: Where git cannot write `signed/<version>` after the first sign-off's commit, the command keeps the commit, prints one line naming the tag and git's own message, and exits 1`
- Proof: `- PROOF-N (RULE-N): With a file at `.git/refs/tags/signed`, so git can write no tag under it, the walk for `2.1.0` is answered yes; the sign-off commit is made, no tag `signed/2.1.0` exists, a line begins `No tag: git could not write signed/2.1.0:`, and it exits 1`

### C4. An unreadable settings file stops the sign-off (signatures, old RULE-67). Risk: low
- Old rule: "A `.purlin/config.json` that cannot be read stops the command before it reads or writes anything else: it prints `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`, writes nothing and exits 1".
- Today: `states` RULE-122, `ai_audit` RULE-41 and `run_script` hold it for their own commands; nothing holds it for `sign.py`.
- What breaks unnoticed: a sign-off over a project whose test settings cannot be read, so the tests the package ties to each proof may be read wrongly or the command fails with a traceback.
- Code: still does it, `scripts/review/sign.py:1049-1054`.
- Proposed: add the case to RULE-125's list ("…, or a `.purlin/config.json` that cannot be read").
- Proof: `- PROOF-N (RULE-125): With `.purlin/config.json` holding `{"version": "0.10.0",`, the walk prints only `.purlin/config.json cannot be read: Expecting property name enclosed in double quotes at line 1. Fix the file by hand; nothing ran and nothing was saved.`, adds no commit and exits 1`

### C5. Where both sources hold a matching audit entry, the later one answers (evidence, old RULE-28). Risk: low
- Old rule: "Where both sources hold a matching audit entry, the later `at` wins, and the entry names its source".
- Today: `evidence` RULE-16 covers one source only; no rule says which of two wins.
- What breaks unnoticed: an older `strong` entry under `ci` answers in place of a later `weak` one under `local`, for the same hashes. Rare: `purlin:audit` writes under `local`.
- Code: still does it, `scripts/mcp/purlin/evidence.py:232-253`.
- Proposed: extend RULE-16 with "; where both sources hold one, the later `at` answers".
- Proof: `- PROOF-N (RULE-16): Both files hold an entry for RULE-1 with the hashes `r`, `p` and `t`: `ci` reads `strong` at `2026-09-01T00:00:00Z` and `local` reads `weak` at `2026-09-02T00:00:00Z`; asked for RULE-1 with those hashes, the reader returns the `weak` entry, naming the source `local``

### C6. A `key::` literal as the signing key (signatures, old RULE-60 clause). Risk: low
- Old clause: the key fingerprint is read from "… or a `key::` literal".
- Today: RULE-60 names the two path forms only.
- What breaks unnoticed: little. A signer whose `user.signingkey` is a literal would be told `No key to sign with`, which is loud. It is here because the code kept the behaviour and the spec dropped it.
- Code: still does it, `scripts/mcp/purlin/signatures.py:236` and `:278-279`.
- Proposed: either restore the four words in RULE-60 with one proof, or delete the three lines of code (clean release). Proof if kept: `- PROOF-N (RULE-60): With `user.signingkey` set to `key::` followed by the text of an ed25519 public key, the key fingerprint a sign-off would record reads what `ssh-keygen -l` prints for that key`

## Notes outside the slice
- `signatures` RULE-127 has no proof with two run lines (a second machine or the source `ci`); the known open item stands. The remote-runner wording of old RULE-112 is gone from the code.
- `signatures` RULE-126 does not name the last note decision 120 requires at a hand check's stop; `states` RULE-116 covers it for the status only.


---

## Appendix C. Part 1: run, reports, host, drift, formats, server, summary

# Part 1, slice: run, reports, host, drift, renumber, specs, schema_spec_format, config_engine, server, summary

## Counts

| Spec | a | b | c | d | total |
|---|---|---|---|---|---|
| run/run_script | 8 | 2 | 1 | 15 | 26 |
| run/reports | 5 | 0 | 2 | 12 | 19 |
| run/host | 0 | 24 | 0 | 1 | 25 |
| mcp/drift | 4 | 0 | 0 | 13 | 17 |
| spec/renumber | 1 | 0 | 0 | 0 | 1 |
| mcp/specs | 2 | 0 | 0 | 4 | 6 |
| mcp/schema_spec_format | 6 | 1 | 0 | 19 | 26 |
| mcp/config_engine | 1 | 0 | 0 | 7 | 8 |
| mcp/server | 0 | 2 | 0 | 12 | 14 |
| mcp/summary | 7 | 0 | 0 | 7 | 14 |
| **all** | 34 | 29 | 3 | 90 | 156 |

Counts include reworded rules that dropped a clause, marked `(clause)`. (a) correctly removed, (b) moot by a later decision, (c) candidate to restore, (d) covered by a named rule.

## Every removed rule

### run/run_script

- RULE-1: (d) command-line shape kept as run_script RULE-98 (PROOF-1, 235); --remote parts moot (119)
- RULE-2: (d) unknown feature refused by RULE-98 PROOF-2; the not-a-directory half has words only
- RULE-9: (d) run_script RULE-8, PROOF-9: unselected feature's marker is not named
- RULE-71: (a) edge case; states RULE-122 still reports no specs found
- RULE-15: (d) run_script RULE-99, PROOF-171 keeps the run log
- RULE-21: (d) mcp/evidence RULE-27, PROOF-25 reads an unknown system as linux
- RULE-40: (d) run_script RULE-99, PROOF-58 and PROOF-171
- RULE-41: (c) RULE-98 covers it in words; no proof for the empty value
- RULE-43: (b) mutation testing cut, decision 109; --ignore=mutants leftover, decision 120
- RULE-56: (d) merged into run_script RULE-101, PROOF-94, 91, 93
- RULE-78: (a) wording of the Skipped line, kept in RULE-101 PROOF-91
- RULE-57: (d) run_script RULE-100, PROOF-95 and 96
- RULE-85: (d) run_script RULE-100, PROOF-257 commits exactly the three files
- RULE-61: (a) wording of the suggestion, kept in RULE-102 PROOF-126
- RULE-62: (a) wording, kept in RULE-102 PROOF-127
- RULE-64: (a) advice wording, RULE-102 PROOF-134 keeps one case
- RULE-65: (d) run_script RULE-103, PROOF-137 writes nothing
- RULE-66: (d) run_script RULE-103, PROOF-138
- RULE-68: (d) evidence_writer RULE-19 and RULE-32, PROOF-50, 49, 10
- RULE-80: (d) reports RULE-34, PROOF-18 and 114, exit 1
- RULE-81: (d) reports RULE-35, PROOF-20 and 88
- RULE-82: (a) order of progress lines, cosmetic
- RULE-84: (b) doctest switch cut by decision 112
- RULE-70: (d) run_script RULE-103, PROOF-224
- RULE-8 (clause): (a) dropped only the five-listed limit and plural wording
- RULE-67 (clause): (a) dropped exact line wording; PROOF-139 and 212 keep the behaviour

### run/reports

- RULE-2: (c) no rule or proof today; markers.py still skips strings and here documents
- RULE-5: (d) reports RULE-33, PROOF-5: reads missing, exits 1
- RULE-13: (d) reports RULE-33, PROOF-13: ambiguous case counted for none
- RULE-18: (d) reports RULE-34, PROOF-18
- RULE-19: (c) RULE-33 covers both; the rule-that-has-proofs half has no proof
- RULE-20: (d) reports RULE-35, PROOF-20 and 88
- RULE-21: (d) reports RULE-36, PROOF-28; a helper, not a protection
- RULE-22: (a) near-miss detail, merged into RULE-36
- RULE-23: (a) near-miss detail, merged into RULE-36
- RULE-24: (d) reports RULE-36, PROOF-35 and 37
- RULE-25: (a) merged into RULE-37; bash is an implementation detail
- RULE-26: (d) reports RULE-37, PROOF-84
- RULE-27: (d) reports RULE-37, PROOF-86
- RULE-28: (d) reports RULE-37, PROOF-87
- RULE-29: (d) reports RULE-35, PROOF-108
- RULE-30: (a) near-miss detail, merged into RULE-36
- RULE-31: (d) reports RULE-34, PROOF-114: unreadable report exits 1
- RULE-3 (clause): (a) no-suite marker reading only informs the status; a run with no suite stops (RULE-102)
- RULE-16 (clause): (d) moved to run_script RULE-58, PROOF-191 and 193

### run/host

- RULE-5: (b) remote runner removed, decision 119
- RULE-6: (b) decision 119
- RULE-7: (b) decision 119
- RULE-36: (b) purlin:test --remote removed, decision 119
- RULE-38: (b) decision 119
- RULE-17: (b) runner templates removed, decision 119
- RULE-39: (b) decision 119
- RULE-18: (b) decision 119
- RULE-41: (b) cut by decision 112, then 119
- RULE-19: (b) decision 119
- RULE-20: (b) consumer runner fixture, decision 119
- RULE-24: (d) path is `/`-built in evidence.py:96; evidence_writer RULE-32 PROOF-39 (no Windows proof)
- RULE-32: (b) API commit and its retries removed, decision 119; --ci merge kept by run_script RULE-12 PROOF-117
- RULE-28: (b) run/ branches removed, decision 119; --ci commits only with --commit (evidence_writer RULE-33)
- RULE-37: (b) decision 119
- RULE-33: (b) decision 119
- RULE-34: (b) decision 119
- RULE-35: (b) decision 119
- RULE-42: (b) decision 119
- RULE-43: (b) decision 119
- RULE-44: (b) decision 119
- RULE-45: (b) decision 119
- RULE-46: (b) decision 119
- RULE-47: (b) decision 119
- RULE-48: (b) decision 119

### mcp/drift

- RULE-5: (a) wording of the first line; PROOF-9, 10 keep it
- RULE-12: (a) grouped network check, dropped by decision 112
- RULE-13: (d) drift RULE-10, PROOF-17
- RULE-18: (d) drift RULE-42, PROOF-27
- RULE-19: (a) serialisation detail
- RULE-21: (d) drift RULE-40, PROOF-58
- RULE-23: (d) drift RULE-42, PROOF-49
- RULE-26: (d) drift RULE-40, PROOF-61
- RULE-27: (d) drift RULE-41, PROOF-66
- RULE-28: (d) drift RULE-43, PROOF-67
- RULE-29: (d) drift RULE-43, PROOF-68
- RULE-30: (d) drift RULE-43, PROOF-69
- RULE-36: (d) drift RULE-31, PROOF-85
- RULE-37: (d) drift RULE-2, PROOF-86
- RULE-38: (a) role views removed by decision 109; nothing left to protect
- RULE-39: (d) drift RULE-41, PROOF-88
- RULE-32 (clause): (d) fetches nothing: drift RULE-41, PROOF-74

### spec/renumber

- RULE-10: (a) where the moved line lands in the file, cosmetic

### mcp/specs

- RULE-3: (a) parsing detail no user meets
- RULE-7: (d) specs RULE-22, PROOF-24
- RULE-8: (d) specs RULE-22, PROOF-9
- RULE-14: (d) schema_spec_format RULE-7, PROOF-49
- RULE-18: (d) specs RULE-22, PROOF-25
- RULE-21: (a) edge case; states RULE-122 reports no specs found

### mcp/schema_spec_format

- RULE-2: (d) schema_spec_format RULE-41, PROOF-14 and 69
- RULE-4: (d) states RULE-1, PROOF-1: no test, no proof written
- RULE-8: (a) description continuation, cosmetic
- RULE-11: (a) > Note: is free text, nothing counts on it
- RULE-12: (a) heading case, an edge no user meets (specs.py:164 still does it)
- RULE-14: (b) replaced by the one information line, decision 113
- RULE-16: (d) schema_spec_format RULE-38, PROOF-2
- RULE-17: (d) schema_spec_format RULE-39, PROOF-46
- RULE-18: (d) schema_spec_format RULE-38 in words, RULE-3 PROOF-17 shows it is not read
- RULE-20: (a) doubled tag, edge case
- RULE-21: (a) two @env tags, edge case
- RULE-22: (d) schema_spec_format RULE-40, PROOF-28
- RULE-23: (d) schema_spec_format RULE-40, PROOF-29
- RULE-24: (d) schema_spec_format RULE-10 PROOF-38; specs RULE-22
- RULE-26: (d) schema_spec_format RULE-41 and RULE-42, PROOF-62
- RULE-28: (d) schema_spec_format RULE-42, PROOF-66
- RULE-29: (d) schema_spec_format RULE-41, PROOF-69 (a page reading, not the code)
- RULE-30: (d) schema_spec_format RULE-38, PROOF-71
- RULE-31: (d) schema_spec_format RULE-38 in words (same path as > Requires:)
- RULE-33: (d) schema_spec_format RULE-32, PROOF-76
- RULE-34: (d) schema_spec_format RULE-38, PROOF-78
- RULE-35: (d) schema_spec_format RULE-39, PROOF-81
- RULE-36: (d) schema_spec_format RULE-39, PROOF-82
- RULE-37: (a) order of the reasons, wording
- RULE-7 (clause): (d) specs RULE-11 PROOF-34; schema_spec_format RULE-38 PROOF-49
- RULE-32 (clause): (d) schema_spec_format RULE-38 names the warning

### mcp/config_engine

- RULE-1: (d) config_engine RULE-21, PROOF-28
- RULE-2: (d) config_engine RULE-21, PROOF-18
- RULE-3: (d) config_engine RULE-21, PROOF-30
- RULE-7: (d) config_engine RULE-4, PROOF-7
- RULE-9: (d) config_engine RULE-8, PROOF-8
- RULE-13: (d) config_engine RULE-21, PROOF-28 and 30 name how it was found
- RULE-15: (d) config_engine RULE-14, PROOF-35
- RULE-14 (clause): (a) the list of causes is wording; PROOF-32, 33 keep two

### mcp/server

- RULE-3: (d) server RULE-35, PROOF-3
- RULE-4: (d) server RULE-35 in words (unknown method proven, PROOF-127)
- RULE-10: (d) server RULE-36 in words; same refusal path as PROOF-151
- RULE-23: (d) server RULE-35, PROOF-125
- RULE-24: (d) server RULE-35, PROOF-127
- RULE-25: (b) reversed by decision 115: server RULE-37 refuses a call naming no root
- RULE-26: (d) server RULE-36 in words
- RULE-27: (d) server RULE-7, PROOF-141
- RULE-28: (d) server RULE-36 in words
- RULE-29: (d) server RULE-36, PROOF-151
- RULE-30: (d) server RULE-36, PROOF-155
- RULE-33: (d) server RULE-36, PROOF-164
- RULE-34: (b) role views removed, decision 109
- RULE-9 (clause): (d) failed save: config_engine RULE-10, PROOF-26 and 27

### mcp/summary

- RULE-1: (a) wording, kept in summary RULE-22
- RULE-12: (d) summary RULE-22, PROOF-4
- RULE-2: (a) singular wording, RULE-22 PROOF-5
- RULE-13: (a) singular wording
- RULE-3: (a) plural wording
- RULE-4: (d) summary RULE-23, PROOF-8, 40, 29
- RULE-5: (d) summary RULE-23, PROOF-8
- RULE-6: (a) a kind with no rule has no line, cosmetic
- RULE-7: (a) cosmetic
- RULE-9: (d) summary RULE-22 counts passed cells; states owns the hand-check cell
- RULE-10: (a) system names, wording; --remote moot (119)
- RULE-14: (d) summary RULE-8, PROOF-23 and 33
- RULE-16: (d) summary RULE-23, PROOF-40
- RULE-17: (d) summary RULE-22, PROOF-43

## The (c) items, ranked

### 1. reports RULE-2: a marker inside a string or a here document (risk: high)

- **Old rule (specs/run/reports.md):** "A marker-shaped line inside a Python string or inside a shell here document is not a marker". It had two proofs (old PROOF-2, PROOF-41).
- **Today's specs:** no rule and no proof names a string or a here document. `reports` RULE-1 says only "one whole-line comment", and its PROOF-27 covers a marker after code on the same line, not one inside a string.
- **What breaks unnoticed:** a test file that writes a fixture holding a marker line (Purlin's own tests do this throughout) would have that line read as a marker and tied to the next test declared. That test's pass then counts as a proof it never carried out, so a rule reads `passed` with no test of it. Nothing prints.
- **Code:** still does it, unprotected. `scripts/mcp/purlin/markers.py:33` (the contract), `:368-391` (here documents), `:415-583` (strings stepped over and blanked).
- **Proposed rule (reports, next id RULE-38):**
  `- RULE-38: A marker-shaped line inside a string of a test file, or inside a here document of a shell file, is not a marker and ties nothing`
- **Proposed proof (next id PROOF-119):**
  `- PROOF-119 (RULE-38): A Python test file holds `# purlin: login PROOF-1` on line 2, inside a triple-quoted string, and `# purlin: login PROOF-2` as a comment on line 5 above the passing `test_ok`; one marker is read, `PROOF-2` at line 5, and the evidence holds no `pass` for `PROOF-1``

### 2. run_script RULE-41: `--project-root` with an empty value (risk: medium; rule exists, no proof for this case)

- **Old rule (specs/run/run_script.md):** "`--project-root` with an empty value exits 2 naming the flag, rather than resolving to the working directory and running there".
- **Today's specs:** `run_script` RULE-98 says the command line names "a `--project-root` that is a directory" and each refusal exits 2. Its three proofs (PROOF-1, 2, 235) cover the missing mode, an unknown feature and `--help`. No proof starts the run with an empty or a non-directory root.
- **What breaks unnoticed:** a caller whose variable did not get set (`--project-root "$ROOT"`) would run, write evidence and, with `--commit`, commit in whatever checkout it was started in. In a worktree set-up (decision 115) that is another checkout's evidence.
- **Code:** still refuses. `scripts/run/purlin_run.py:289-296` (empty value), `:1129-1133` (not a directory).
- **Proposed:** no new rule; one proof under RULE-98 (next id PROOF-281):
  `- PROOF-281 (RULE-98): Started in a Purlin project as `--all --test --project-root ''`, the run exits 2, prints `purlin: --project-root needs a directory, not an empty value.`, and writes nothing under that project's `.purlin/``

### 3. reports RULE-19, second half: a marker naming a rule that has proofs (risk: low; rule exists, no proof for this case)

- **Old rule (specs/run/reports.md):** "... and one naming a rule that has proofs as `<file>:<line> names <feature> <RULE-N>, which has proofs; a comment names one of its proofs. ...`; either exits the run 1 whatever its tests did".
- **Today's specs:** `reports` RULE-33 names the case. Its proofs (PROOF-5, 19, 13) cover no test following, a feature no spec has, and an ambiguous case. No proof anywhere holds `which has proofs`.
- **What breaks unnoticed:** if such a marker began to count, a test marked with a rule's id would pass every proof of that rule at once, the proofs' own tests unwritten.
- **Code:** still refuses. `scripts/mcp/purlin/markers.py:944-953` (`RULE_HAS_PROOFS`, "ties no result to any rule").
- **Proposed:** no new rule; one proof under RULE-33 (next id PROOF-120, or PROOF-119 if item 1 is not taken):
  `- PROOF-120 (RULE-33): `login`'s `RULE-1` has `PROOF-1`, and a passing test on line 3 is marked `purlin: login RULE-1`; the run prints `tests/test_login.py:3 names login RULE-1, which has proofs; a comment names one of its proofs. Correct the comment, or run purlin:build to repair it.`, exits 1, and the evidence holds no `pass` under `RULE-1``

### Noted, not classed (c)

- `run/host` RULE-24 (evidence paths handed to git with `/` on Windows): the path is built with `/` in `scripts/mcp/purlin/evidence.py:96-98` and the removal is proven on POSIX by `evidence_writer` RULE-32 PROOF-39. There is no `@env(windows)` proof of a removed evidence file reaching the commit. Low risk; one Windows proof would close it.
- `schema_spec_format` RULE-41's proof of never reusing a deleted proof's number (PROOF-69) reads the format page, not the code. `renumber` RULE-7 PROOF-9 does exercise the raised `> Highest-Proof:` line.
- `server` RULE-36 lists five refused writes and proves three (`version`, a `tests` that is not a list, another key). All five share one refusal path; left as (d).

Total this slice would add: 1 rule and 3 proofs.


---

## Appendix D. Part 1: setup, upgrade, anchors, dashboard, instructions, skills

# Part 1 slice: anchors, setup, upgrade, dashboard, instructions, skills

Classes: (a) wording, cosmetic or a repeat; (b) moot, a later decision removed it; (c) a protection
no rule or proof covers today; (d) a protection a kept or later rule covers.

## 1. Counts

| Spec | Removed | a | b | c | d |
|------|--------:|--:|--:|--:|--:|
| `_anchors/security_no_dangerous_patterns` | 0 | 0 | 0 | 0 | 0 |
| `anchor/upstream` | 15 | 8 | 0 | 0 | 7 |
| `init/scaffold` | 16 | 8 | 1 | 0 | 7 |
| `init/update` | 23 | 8 | 0 | 1 | 14 |
| `dashboard/purlin_report` | 25 | 17 | 1 | 0 | 7 |
| `instructions/install` | 1 | 1 | 0 | 0 | 0 |
| `instructions/purlin_agent` | 4 | 3 | 0 | 0 | 1 |
| `instructions/purlin_docs` | 1 | 1 | 0 | 0 | 0 |
| `instructions/purlin_output` | 0 | 0 | 0 | 0 | 0 |
| `instructions/purlin_version` | 2 | 1 | 0 | 0 | 1 |
| `skills/skill_*` (10 specs, 4 each) | 40 | 30 | 0 | 0 | 10 |
| **Total** | **127** | **77** | **2** | **1** | **47** |

Beside the 127 removed ids: 1 dropped clause is class (c) (`update` RULE-24, the git source that
stays), and 2 gaps the pass did not cause were found while checking (`upstream` RULE-22, section 4).
The security anchor lost no rule and no proof.

## 2. One line per removed rule

### anchor/upstream
- RULE-5, d: `upstream` RULE-39, PROOF-5 kept: a path the source lacks writes nothing.
- RULE-9, d: `upstream` RULE-37 holds the three exit codes, three proofs.
- RULE-12, d: `upstream` RULE-11, PROOF-12 kept: no rule change, pin still advances.
- RULE-15, a: one fetch per source is speed, not a protection.
- RULE-21, a: `--help` wording.
- RULE-24, d: `upstream` RULE-39, PROOF-42 kept: a file with no rule is refused.
- RULE-26, d: `upstream` RULE-37.
- RULE-27, d: `upstream` RULE-37.
- RULE-28, a: wording of one line, merged into RULE-38.
- RULE-29, a: usage message.
- RULE-30, a: wording of the count line after `add`.
- RULE-31, d: `upstream` RULE-39, PROOF-54 kept.
- RULE-32, a: wording, merged into RULE-38.
- RULE-33, a: wording of the empty case.
- RULE-34, a: usage message.

### init/scaffold
- RULE-19, d: `scaffold` RULE-20: the appended block is there once.
- RULE-22, d: `scaffold` RULE-21, PROOF-22.
- RULE-23, d: `scaffold` RULE-21, PROOF-23.
- RULE-31, d: `scaffold` RULE-82, PROOF-31: not a git repository, folder left empty.
- RULE-34, a: closing lines, cut by decision 112.
- RULE-48, d: `scaffold` RULE-20: an existing `tests` setting is kept.
- RULE-50, a: merged into RULE-83.
- RULE-51, a: no `specs/_anchors/` folder, cosmetic.
- RULE-63, d: `scaffold` RULE-82, PROOF-128: unreadable settings, nothing written.
- RULE-69, a: wording of the commit lines; the commit itself is RULE-68.
- RULE-71, a: merged into RULE-68.
- RULE-72, d: `scaffold` RULE-82, PROOF-161: refused commit leaves files staged.
- RULE-73, a: comments in the `.gitignore` block.
- RULE-74, b: decision 114 rewrites the page with its data (`purlin_report` RULE-76).
- RULE-79, a: merged into RULE-83.
- RULE-80, a: merged into RULE-83.
- Clauses dropped from kept rules: RULE-47 "a second run keeps it", d (RULE-20); RULE-36 the audit
  and `run/*` branch steps, b (decisions 109 and 119); RULE-18 "skipped", RULE-8 "not named", a.

### init/update
- RULE-1, a: shape of the pending list.
- RULE-4, d: `update` RULE-51, PROOF-4.
- RULE-8, d: `update` RULE-53, PROOF-8.
- RULE-13, d: `update` RULE-52, PROOF-129; the regex is anchored to the line end (`update.py:50`).
- RULE-15, **c**: the workflow removal is named in RULE-53 and no proof exercises it. See 3.1.
- RULE-16, d: `update` RULE-53, PROOF-81: a file of another name is left alone.
- RULE-20, a: closing lines.
- RULE-23, d: `update` RULE-52, PROOF-129.
- RULE-24, d for the removal (`update` RULE-52, PROOF-24); its clause "a git `> Source:` and its
  `> Pinned:` stay" is **c**. See 3.2.
- RULE-27, a: the no-scope advice, cut by decision 112.
- RULE-28, d: `update` RULE-54, PROOF-28.
- RULE-30, d: `update` RULE-29 carries the clause.
- RULE-31, d: `update` RULE-54, PROOF-31.
- RULE-33, d: `update` RULE-53, PROOF-34.
- RULE-34, a: deleting Purlin's own old cache folder protects nothing.
- RULE-36, d: `update` RULE-35 carries the clause.
- RULE-40, d: `update` RULE-51, PROOF-116.
- RULE-41, a: wording of the pending list.
- RULE-42, a: wording and indent.
- RULE-43, a: wording of the commit line.
- RULE-44, d: `update` RULE-51, PROOF-151.
- RULE-45, a: wording; the backup itself is RULE-7.
- RULE-46, d: `update` RULE-52, PROOF-153; the advice line is wording.
- Clauses dropped from kept rules: RULE-7 "a second run does not write the copy again", d
  (RULE-5: a second run changes nothing); RULE-29 and RULE-35 "each backed up first", d (RULE-7,
  PROOF-71); RULE-21 the `auto` value, a.

### dashboard/purlin_report
- RULE-1, a: same bytes on two builds.
- RULE-4, a: merged into RULE-3.
- RULE-6, a: merged into RULE-3.
- RULE-21, d: `purlin_report` RULE-20: no data file, one notice.
- RULE-23, a: where the docs screenshots come from.
- RULE-25, a: merged into RULE-10.
- RULE-31, d: `purlin_report` RULE-17: one box per system, pass or fail.
- RULE-33, a: column alignment.
- RULE-34, a: 13 pixel minimum.
- RULE-35, a: merged into RULE-75.
- RULE-42, d: `purlin_report` RULE-41: nothing writes the data in the background.
- RULE-43, a: the `no scope` label.
- RULE-45, a: merged into RULE-75.
- RULE-49, a: merged into RULE-75.
- RULE-50, a: the colour of `waiting`.
- RULE-51, a: merged into RULE-8.
- RULE-52, a: merged into RULE-10.
- RULE-56, a: merged into RULE-8.
- RULE-57, d: `purlin_report` RULE-22: the uncommitted-changes notice.
- RULE-58, a: merged into RULE-12.
- RULE-59, a: merged into RULE-37.
- RULE-60, d: `purlin_report` RULE-22: every warning drawn whole.
- RULE-70, d: `purlin_report` RULE-9: `Strong` only where the audit read.
- RULE-72, d: `purlin_report` RULE-7: the two facts as the payload gives them.
- RULE-73, b: decisions 115 and 117 replaced it (`purlin_report` RULE-77).
- Clauses dropped: RULE-39 "the model that read the rule and the date", a; RULE-2 the 1200-line
  limit, a.

### instructions
- `install` RULE-6, a: a statement about the test, not the product.
- `purlin_agent` RULE-2, a: merged into RULE-18 (`purlin:test --remote` is b, decision 119).
- `purlin_agent` RULE-3, d: `purlin_output` RULE-4.
- `purlin_agent` RULE-6, a: line limit, cut by decision 112.
- `purlin_agent` RULE-7, a: merged into RULE-18.
- `purlin_docs` RULE-14, a: the page count, changed by decision 109.
- `purlin_version` RULE-11, a: an edge no user meets.
- `purlin_version` RULE-13, d: `purlin_version` RULE-1 and RULE-14 catch a bad `VERSION` after
  the write.

### skills (the same four in each of the 10 specs)
- Line limit, a (10): cut by decision 112.
- No emoji, d (10): `purlin_output` RULE-4.
- Commands named, a (10): merged into the spec's one rule.
- Files named, a (10): merged into the spec's one rule.

## 3. The (c) items

### 3.1 The upgrade deletes any workflow that holds the text `.proofs-` (risk: medium)

- **Old rule** (`init/update` RULE-15): "The workflow v0.9.5 wrote, which committed proof files back
  beside the specs, is removed, and the update writes no runner file in its place". Its proof,
  PROOF-15, went with it.
- **Today**: RULE-53 names "the workflow that committed proof files"; none of its three proofs
  touches a workflow, and no proof ever showed another workflow is left alone.
- **Code still does it**: `scripts/init/update.py:496-522`. `_detect_workflows` takes every
  `.yml` or `.yaml` under `.github/workflows/` whose text holds `.proofs-` (`WORKFLOW_MARKER`,
  line 53); `_apply_workflows` backs it up, untracks it and deletes it, then prints
  `removed 1 workflow that committed proof files`. The known open item is confirmed.
- **What breaks unnoticed**: a change to the marker or the folder walk deletes a project's own CI
  workflow in the upgrade commit. Today a project's own workflow that merely mentions `.proofs-`
  is deleted too; the `.bak` copy is the only trace.
- **Proposed rule** (`init/update`): The update removes a workflow under `.github/workflows/` only
  where it wrote 0.9.5's proof files, backs it up first, and leaves every other workflow as it was.
- **Proof**: The sample 0.9.5 project holds `purlin-proofs.yml`, which commits `*.proofs-*.json`,
  and `ci.yml` running `pytest`; after the update with `--yes` the first is gone with a backup
  beside it holding its bytes, `ci.yml` is byte for byte as it was, and the output holds
  `removed 1 workflow that committed proof files`.

### 3.2 The upgrade must leave a remote anchor's source and pin alone (risk: medium)

- **Old clause** (`init/update` RULE-24): "a git `> Source:` and its `> Pinned:` stay". Its proof,
  PROOF-102, went; RULE-52 no longer says it.
- **Code still does it**: `scripts/init/update.py:56-57, 216-240`. `FIGMA_SOURCE_RE` is
  `^>\s*Source:.*figma`, case ignored, so a git source whose address holds the word, as in
  `https://github.com/acme/figma-tokens.git`, loses `> Source:` and `> Pinned:`.
- **What breaks unnoticed**: a remote anchor becomes a local one in the upgrade commit. It is never
  reported as behind its source again, and its rules stop following the other team's.
- **Proposed rule** (`init/update`): An anchor whose `> Source:` is a git address keeps its
  `> Source:` and `> Pinned:` lines through the update, byte for byte.
- **Proof**: An anchor whose `> Source:` is `https://github.com/acme/policies.git specs/no_eval.md`
  with a `> Pinned:` sha of 40 characters is exactly what it was after the update with `--yes`,
  and no backup is written beside it.
- A second case, the address `https://github.com/acme/figma-tokens.git`, fails on today's code and
  is a bug to fix with the rule.

## 4. Found while checking, not caused by the pass

### 4.1 `purlin:anchor add --name` is not held under the project (risk: medium)

- **Rule exists, no proof for this case**: `upstream` RULE-22, "Every file `add` and `sync` write
  lies under the project root they were given". Its one proof is the happy path.
- **Code**: `scripts/anchor/upstream.py:175-176` joins `--name` into the path unchecked, so
  `--name ../../x` writes `x.md` outside `specs/_anchors/`, and outside the project with more
  `..`. `read_source_file` (lines 146-154) joins `--path` the same way.
- **Proposed proof** (under RULE-22): The published anchor is added with `--name ../../outside`;
  it exits 2, the answer reads `error`, `specs/_anchors/` stays empty and no `outside.md` exists
  anywhere under the folder around the project.
- This needs a code change: the name is refused unless it is letters, digits and `_`.

### 4.2 `add` overwrites an anchor of the same name (risk: medium)

- **No rule.** `scripts/anchor/upstream.py:305` writes the copy with no check for a file already
  there, so `add ... --name security` replaces the project's own anchor `security`, its rules and
  its `> Note:` lines, with no word said.
- **Proposed rule** (`anchor/upstream`): `add` refuses a name an anchor in the project already
  holds, writes nothing and names `purlin:anchor sync <name>`.
- **Proof**: With `specs/_anchors/no_eval.md` holding the project's own rule `No eval in scripts`,
  the published anchor is added as `no_eval`; it exits 2, the answer reads `error`, and the file
  holds exactly its text from before.
- This needs a code change.


---

## Appendix E. Part 2: the sign-off and the package

# Part 2 slice: the sign-off and the package

Read in full: `scripts/review/sign.py` (1063 lines), `scripts/mcp/purlin/signatures.py` (302),
`scripts/export/package.py` (867); also `scripts/mcp/purlin/facts.py` and
`payload.py:771-810`, where the sign-off is read back. Specs: `specs/review/signatures.md`
(23 rules, highest RULE-128, PROOF-248), `specs/export/package.md` (23 rules, highest RULE-37,
PROOF-76). Tests: `dev/test_signatures.py`, `dev/test_export.py`. No test was run.

"Refusing direction shown" means the proof gives the bad input and asserts the refusal. Every
refusal test in `dev/test_signatures.py` goes through `run_main` (line 192), which asserts `HEAD`
did not move, so "nothing committed" is shown wherever a refusal proof exists.

## 1. Every case

| # | Where | What happens | Rule / proof | Refusing direction shown |
|---|-------|--------------|--------------|--------------------------|
| 1 | sign.py:419, 202-222 | Tracked file outside `.purlin/` changed: refuse, exit 1 | RULE-102 / PROOF-244, 245 | yes |
| 2 | sign.py:220 | A tracked file under `.purlin/` (config, package, sign-off) changed and not committed: not counted, no refusal | none | no (gap G9) |
| 3 | sign.py:210 | `git status` fails: counted as 0 changed files, the sign-off goes on (fails open) | none | no (low) |
| 4 | sign.py:205 | Untracked file: not counted | RULE-102 / PROOF-248 | yes (allowing direction) |
| 5 | sign.py:423, package.py:182 | Evidence under `local/` or `ci/` written, not committed: refuse | RULE-102 / PROOF-223 | yes |
| 6 | sign.py:427 | No version stated or named: refuse | RULE-125 / PROOF-243 | yes |
| 7 | sign.py:434 | `signed/<v>` on a commit HEAD does not descend from: refuse | RULE-124 / PROOF-224 | yes |
| 8 | sign.py:437 | Code changed since `signed/<v>`: refuse | RULE-124 / PROOF-225 | yes |
| 9 | sign.py:439 | Later sign-off: the package committed at HEAD is taken as it is, never rebuilt and never checked against its fingerprint | none | no (gap G3) |
| 10 | sign.py:443-445, package.py:315, 217 | Package cannot be built (no commit yet, checkout fails): one line, exit 1 | RULE-23 covers "cannot be written" only | no (low) |
| 11 | sign.py:446, package.py:633 | A result not taken on this code: refuse | RULE-102 / PROOF-226 (`ci`), package RULE-33 / PROOF-68 (`local`) | yes |
| 12 | package.py:163 | A result taken on a commit HEAD does not descend from: `same_code` false | none | no (gap G10) |
| 13 | package.py:177 | A result section with no `commit`: `same_code` false | none | no (gap G10) |
| 14 | package.py:74, 170 | Commits that change only `.purlin/**`, `.purlin/config.json` included, leave `same_code` true | RULE-33 / PROOF-67 (evidence file only) | the config case is not shown (gap G8) |
| 15 | sign.py:450, package.py:662 | Results taken while files were changed: refuse | RULE-102 / PROOF-246 | yes |
| 16 | sign.py:453 | A rule with no test: refuse, names `purlin:build` | RULE-128 / PROOF-247 | yes |
| 17 | sign.py:457, 320 | A rule that fails (`to_fix`): refuse | RULE-102 / PROOF-206 | yes |
| 18 | sign.py:320 | A rule never run (`to_test`), a slow proof not run (`to_run_slow`), a rule with no result on its `@env` system (`to_test_remote`): refuse | RULE-102 "a rule does not pass" | no proof for any of the three (gap G4) |
| 19 | sign.py:320-332 | A spec with a number written twice or a conflict line (`to_repair`), a test comment to correct (`to_correct`): refuse | none in signatures.md | no (gap G5) |
| 20 | sign.py:461, 225 | Host's copy holds commits HEAD lacks: refuse | RULE-124 / PROOF-207 | yes |
| 21 | sign.py:230-242 | Detached HEAD or no upstream: no check; ahead of host goes on | RULE-121 / PROOF-238 | yes (allowing) |
| 22 | sign.py:467, 480 | Signer already signed this package: refuse | RULE-125 / PROOF-208 | yes |
| 23 | sign.py:474, signatures.py:38 | Two signers whose addresses give one slug (`jane@acme.com`, `jane@labs.org`; `a.b@` and `a-b@`): the second is told the first "has already signed" under the second's own address, or overwrites the first's file on another package | none | no (gap G7) |
| 24 | sign.py:715, 951 | No SSH key: exit 1, the set-up lines | RULE-17, RULE-60 / PROOF-21, 95, 118 | yes |
| 25 | sign.py:291 | `ssh-keygen` named only while the key file does not exist | RULE-17 / PROOF-95 | yes |
| 26 | sign.py:676 | `--show` needs no key, writes nothing | RULE-110 / PROOF-220, 228 | yes |
| 27 | sign.py:772 | `stop` at a hand check: nothing written, exit 0 | RULE-109 / PROOF-218 | yes |
| 28 | sign.py:667, 772 | End of input at a hand check reads as stop | RULE-109 | not shown (low, same path) |
| 29 | sign.py:745 | Any answer but yes: nothing signed, exit 0 | RULE-109 / PROOF-219 | yes |
| 30 | sign.py:956 | `--answers` file missing or not JSON: refuse | RULE-111 names only "no answer" | no (low) |
| 31 | sign.py:960 | A stop with no answer in the file: refuse | RULE-111 / PROOF-222 | yes |
| 32 | sign.py:938 | Answers file without `sign: true`: nothing signed | RULE-109 in words | no proof through `--answers` (gap G6) |
| 33 | sign.py:935 | Answers file answering `stop`: stopped | RULE-109 | not shown (low) |
| 34 | sign.py:847 | Package cannot be written: one line, no commit, no tag | package RULE-23 / PROOF-52 | yes |
| 35 | sign.py:859 | Sign-off file cannot be written: taken back, exit 1 | none | no (low) |
| 36 | sign.py:865 | git refuses the commit: files taken back, exit 1 | RULE-125 / PROOF-162 | yes |
| 37 | sign.py:875-882 | The commit is made and git cannot write the tag: `No tag: ...`, exit 1; a second run is then refused as "already signed", so the tag is never written | none | no (gap G2) |
| 38 | sign.py:883 | Later sign-off: tag stays | RULE-118, 120 / PROOF-234, 237 | yes |
| 39 | sign.py:515-526 | Per system, a current result is shown before one not current, `ci` before `local` | none | no (gap G11) |
| 40 | sign.py:621-635 | The stop's result line per system, naming the machine; `runner`, then `an unnamed machine` as fallbacks | RULE-126 / PROOF-242 (one system, this machine) | another machine or a second system is not shown (gap G11) |
| 41 | sign.py:652-655 | A weak rule's findings at its hand-check stop | RULE-126 in words | no proof (gap G11) |
| 42 | sign.py:638-656 | The stop shows the last note, its version and commits since | not built, no rule | no (gap G1) |
| 43 | sign.py:1038, 1025-1028 | Bad command line: exit 2 | none | no (wording, none proposed) |
| 44 | sign.py:1051 | Settings file cannot be read: exit 1 | config_engine RULE-14; no proof through `sign.py` | no (low) |
| 45 | signatures.py:129 | Sign-off file not tracked: does not count | RULE-20 in words | no proof (folded into G12) |
| 46 | signatures.py:133 | Last commit touching the file unsigned: does not count | RULE-20 / PROOF-96 | yes |
| 47 | signatures.py:136 | Signature does not verify: does not count | RULE-97 / PROOF-192 | yes |
| 48 | signatures.py:120 | Any key, any author counts | RULE-20 / PROOF-97 | yes (allowing) |
| 49 | signatures.py:199 | Key deleted since: still counts | RULE-97 / PROOF-193 | yes (allowing) |
| 50 | signatures.py:206-213 | A signature that is not SSH goes to `git verify-commit` | none | no (low) |
| 51 | signatures.py:100 | `package_hash` differs from the committed package's `fingerprint` field, or no package at HEAD: does not count | RULE-108 / PROOF-217 | yes for the field changed; the stored field is never recomputed (gap G3) |
| 52 | signatures.py:91-96 | A sign-off file that is not a JSON object is skipped in silence | none | no (low) |
| 53 | signatures.py:91, 131 | The file's content is read from the working tree while the commit is judged from history: a sign-off edited and not committed still counts with the edited content | none | no (gap G12) |
| 54 | signatures.py:72, 120 | `load_signoffs` and `counts` are called by no product code, only by the tests | RULE-20, 97, 108 | proven, and used by nothing (gap G0) |
| 55 | facts.py:42-61 | `Sign-off: signed <v> at <sha>` is read from any `signed/*` tag on HEAD's history: the tag's signature is not verified, no package and no sign-off need exist | states RULE-59 / PROOF-168 to 170 | no (gap G0) |
| 56 | payload.py:771-810 | Hand-check notes are read from every sign-off file in the working tree, counting or not | states RULE-116 | no (gap G12) |
| 57 | package.py:825 | `--check`: not UTF-8 JSON | package RULE-22 / PROOF-45 | yes |
| 58 | package.py:826 | `--check`: wrong schema | RULE-22 / PROOF-46 | yes |
| 59 | package.py:803, 830 | `--check`: a top-level key the format does not name | none | no (gap G13) |
| 60 | package.py:832 | `--check`: a key missing or out of order | none | no (gap G13) |
| 61 | package.py:837 | `--check`: stored fingerprint differs from the content's | RULE-9 / PROOF-17; signatures RULE-122 / PROOF-241 | yes |
| 62 | package.py:840 | `--check`: fingerprint matches, bytes not canonical (CRLF, other indent) | none | no (gap G13) |
| 63 | package.py:851 | `--check`: file cannot be read | none | no (low) |
| 64 | package.py:132-151 | `commit` steps back over package-only commits | RULE-3 / PROOF-30 | yes |
| 65 | package.py:316 | Uncommitted evidence named in `warnings` | none; unreachable through `sign.py`, which refuses first (case 5) | n/a |
| 66 | package.py:201-223 | The temporary checkout is removed | RULE-1 / PROOF-1 (after a sign-off) | not shown after a refusal (low) |

66 cases; 38 have a proof in the direction that matters; 28 do not. Of the 28, 13 are low
(3, 10, 28, 30, 33, 35, 43, 44, 50, 52, 63, 65, 66) and get no proposal: each is a second door
into a path already proven, or wording. The other 15 fold into the gaps G0 to G13 below.

## 2. The gaps, ranked

### G0. Nothing reads whether a sign-off counts (high)

- Where: `signatures.py:72-106, 120-138` are called only from `dev/test_signatures.py`;
  `facts.py:42-61` decides the `Sign-off:` line from the tag alone; `sign.py` never verifies an
  earlier sign-off or the tag's signature.
- What happens: `git tag signed/9.9.9` typed by anyone, unsigned, with no package and no
  sign-off file, makes the status, the dashboard and the last line read
  `signed 9.9.9 at <sha7>`. A sign-off whose commit is unsigned, or whose signature fails, or
  that signs another package, changes nothing a person sees. RULE-20, RULE-97 and RULE-108 are
  proven on a function no command calls.
- What breaks unnoticed: the one fact Purlin exists to state. Decision 102 kept "the signing
  commit's signature is verified, not only present"; decision 120 says a receiving system takes
  the signed commit as the record. Purlin itself does not take it.
- Proposed rule (states.md, beside RULE-59, or summary.md RULE-20): `The sign-off reads
  signed <version> only where signed/<version> names a commit holding the package for that
  version and at least one sign-off that counts; otherwise it reads not signed, and the status
  warns with one line naming the tag and why`
- Proof: `A project with committed evidence that passes carries the tag signed/9.9.9, written
  by hand with git tag, and no file under .purlin/evidence/package/; signoff.word reads
  not signed, and the warnings hold one line naming signed/9.9.9 and that no sign-off that
  counts stands under it`
- Second proof: `The walk signs 2.1.0, then the sign-off's commit is rewritten with one byte of
  its signature block changed; signoff.word reads not signed`

### G1. The hand-check stop does not show the last note (high: a decision not built)

- Where: `sign.py:638-656` (`render_stop`). It prints the rule, proofs, tied tests, results and
  the audit's findings. The note is in the package under the rule's `statuses.strong.reasons`
  (states RULE-116, `payload.py:771`), and the stop never prints it.
- Decisions 110 and 120 require it. No rule in `signatures.md` names it (RULE-126 lists what
  the stop shows, without the note); `skills/sign/SKILL.md` does not name it either.
- What breaks unnoticed: the signer re-checks by hand with no sight of what the last signer
  saw, at which version, or how much changed since.
- Proposed rule (signatures.md): `A hand check's stop shows, under Last note, each note of the
  newest sign-off holding one for that rule, as noted at the sign-off of <version> by <signer>,
  <at this commit | 1 commit since | <n> commits since>: <note>, and shows no such head before
  any sign-off`
- Proof: `quinn.qa@labconnect.example signed 0.1.0 with the note the tube is red at
  login RULE-2; four commits later the walk for 0.2.0 shows at that stop
  noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, 4 commits since: the tube is red`

### G2. A tag git could not write is never written (high)

- Where: `sign.py:875-882`, then `sign.py:467` on the next run.
- What happens: the signed commit is made, `git tag -s` fails (a hook, a tag signing setting,
  a full disk), the command prints `No tag: ...` and exits 1. Run again, `first` is true, the
  rebuilt package has the same fingerprint, and the signer is refused with `has already signed
  <version> over this package; nothing was written.` No Purlin command writes the tag after
  that. No rule and no proof names the tag failure at all.
- What breaks unnoticed: a signed version whose status reads `not signed` for good, with advice
  that leads nowhere.
- Proposed rule (signatures.md): `Where the sign-off's commit is made and git cannot write
  signed/<version>, the command prints one line naming the tag and git's reason and exits 1,
  and the next purlin:sign by any signer writes the tag on that commit and adds no second
  sign-off for one who already signed`
- Proof: `With tag.gpgSign pointing at a program that exits 1, the first sign-off of 2.1.0
  makes its commit, prints No tag: git could not write signed/2.1.0: and exits 1; with the
  setting removed, purlin:sign run again exits 0, signed/2.1.0 names that commit, and no
  commit was added`

### G3. A committed package is trusted by its stored fingerprint, never by its content (high)

- Where: `signatures.py:55-69` reads the `fingerprint` field; `sign.py:439, 400-408` takes the
  committed package for a later sign-off without `check_bytes` and without rebuilding it.
- What happens: after the first sign-off, a commit edits the package's content (`"failed"` to
  `"passed"`, a rule removed) and leaves `fingerprint` alone. Every earlier sign-off still
  counts (`package_hash` equals the field), the status still reads `signed <v> at <sha7>` (the
  commit touched only `.purlin/`), and a second signer is walked through the edited content and
  signs it. Only `--check`, run by hand, sees it. PROOF-217 changes the field and so shows the
  other direction only.
- Proposed rule (signatures.md, replacing RULE-108's words): `A sign-off counts only while its
  package_hash equals the fingerprint computed over the package HEAD holds for its version, and
  a later sign-off is refused, with one line and nothing written, where that package does not
  match its own fingerprint`
- Proof: `The walk signs 2.1.0, then the committed package's first "passed" is changed to
  "failed" with fingerprint left as it was, and committed; the sign-off no longer counts, and a
  second signer's walk prints only one line beginning No sign-off: and naming
  .purlin/evidence/package/2.1.0.json, and exits 1`

### G4. Three refusals of "a rule does not pass" have no proof (high)

- Where: `sign.py:310-338` with `summary.BLOCKING` (`summary.py:84`). PROOF-206 shows a
  failing rule only.
- Not shown: a rule never run (`to_test`), a slow proof never run (`to_run_slow`, decision
  118: "met only after every slow proof has passed"), a rule tagged `@env(windows)` with no
  Windows result (`to_test_remote`, decision 119: "the sign-off counting a result only when
  taken on the version being signed").
- What breaks unnoticed: a change to the blocking kinds or to a rule's `left` lets a version be
  signed with its Windows rules or its integration tests never run. These are the two cases
  the signer is least able to see.
- Add to RULE-102 (no new rule; "a rule does not pass" already covers them), two proofs:
- Proof: `login RULE-2 has PROOF-2 tagged @env(windows), and the committed evidence holds
  results for Linux/Unix alone, all passing; the walk prints only one line beginning
  No sign-off: 1 rule does not pass at <sha7>: login RULE-2. and exits 1`
- Proof: `login RULE-2 has PROOF-2 tagged @slow, and the committed evidence was written by
  purlin:test with no --all, every other rule passing; the walk prints only one line beginning
  No sign-off: 1 rule does not pass at <sha7>: login RULE-2. and exits 1`

### G5. A spec mistake and a stale test comment stop the sign-off, with no rule (medium)

- Where: `sign.py:320-332`. Decision 102: "Signing that feature and writing a tag are refused
  until the spec is fixed"; decision 105: a test left on a reworded proof is to be corrected.
- No rule in `signatures.md` names either; RULE-102's list stops at "a rule does not pass".
- Proposed rule: `The command refuses, with one line, nothing written and exit 1, while a spec
  holds a rule or proof number twice or a merge-conflict line, and while a test comment is to
  be corrected`
- Proof: `specs/auth/login.md holds two lines numbered RULE-2, over committed evidence taken
  before the second was added to no covered file; the walk prints one line beginning
  No sign-off: and naming login RULE-2, writes no file and exits 1`

### G6. An agent's answers file that does not say `sign: true` signs nothing: no proof (medium)

- Where: `sign.py:938`. PROOF-221 gives `sign` true; nothing shows the file without it.
- What breaks unnoticed: `given = 'y' if answers.get('sign') is True` loosened to a truthy
  test, or defaulted, and an agent signs for a person who never said yes.
- Add to RULE-111, one proof: `An answers file gives login RULE-2 a note and holds no sign
  key; --answers prints Nothing was signed., exits 0 and adds no commit and no file; the same
  file with "sign": "yes", a string, gives the same`

### G7. Two signers, one slug (medium)

- Where: `signatures.py:38-42`, `sign.py:474-489`. The slug is the local part alone.
- What happens: after `jane@acme.com` signs, `jane@labs.org` is refused with
  `jane@labs.org has already signed 2.1.0 over this package`, which is false; `already_signed`
  compares the package hash and not the signer.
- Proposed rule: `Two signers whose addresses differ each keep a sign-off of one version: a
  second signer whose slug is taken by another address is not refused as having signed, and
  the first sign-off's file is left as it was`
- Proof: `jane@acme.com signs 2.1.0, then jane@labs.org signs it; the folder
  2.1.0.signoffs holds two files, one reading signer jane@acme.com and one jane@labs.org, and
  the first file's bytes are unchanged`

### G8. A change to `.purlin/config.json` does not end a result (medium)

- Where: `package.py:74, 154-172`; `facts.py:89-97` reads the same function.
- What happens: results are taken, then a commit changes the `tests` commands in
  `.purlin/config.json`. `same_code` stays true, the sign-off goes ahead, and after a sign-off
  the status still reads `signed <v> at <sha7>`. Decision 100: "The project is every tracked
  file but the records Purlin itself writes: the results of a run, the signatures and the
  evidence package." The settings file is not one of them. RULE-33 as written ("only files
  under `.purlin/`") allows it; PROOF-67 shows an evidence file only.
- Proposed change to package RULE-33: `... changes only files under .purlin/evidence/`, with
  the proof: `The tests run and are committed at <c>, then a commit changes the tests command
  in .purlin/config.json; purlin:sign prints only one line beginning No sign-off: these
  results were not taken on this version of the code and exits 1`

### G9. A tracked file under `.purlin/` changed and not committed (low to medium; confirmed)

- Where: `sign.py:220`; `package.py:193-197` counts only `.json` under `evidence/local/` and
  `evidence/ci/`.
- What it lets through: an uncommitted edit to `.purlin/config.json`, to a committed package,
  or to another signer's sign-off file. The package is built from a checkout of the commit
  (`package.py:319`) and a later sign-off reads `HEAD:`'s package (`sign.py:402`), so what is
  signed is the committed state; the harm is limited to G12 below and to a signer who believes
  the settings they see are the ones signed.
- Proposed (one proof under RULE-102, widening its first cause to every tracked file but
  evidence, which has its own refusal): `With committed evidence that passes,
  .purlin/config.json is changed and not committed; the walk prints only No sign-off: 1 file
  is changed and not committed. Commit it or set it aside, then run purlin:sign again. and
  exits 1`

### G10. A result from a commit HEAD does not hold, or with no commit (medium)

- Where: `package.py:163, 177`. PROOF-226 and PROOF-68 show an ancestor followed by a code
  change. A result taken on another branch's commit, or a section carrying no `commit`, has no
  proof.
- Add to package RULE-33, one proof: `login's committed results name a commit on another
  branch, which HEAD does not descend from, the two trees holding the same files; every result
  reads same_code false and purlin:sign prints only one line beginning No sign-off: these
  results were not taken on this version of the code`

### G11. What the stop shows for a second system, another machine and a weak rule (medium; known item 1)

- Where: `sign.py:515-526, 621-635, 652-655`. PROOF-242 shows one line, Linux/Unix, the local
  machine. Nothing shows a `ci` result from another machine in a stop or in the overview, the
  preference for a current result over one out of date, or the audit's findings under a weak
  hand check (decision 105, N1).
- Add to RULE-126, two proofs:
- `login RULE-2, a hand check, has PROOF-3 tagged @env(windows), run under the source ci on
  the machine build-7; its stop holds the two lines Linux/Unix: passed on dana-laptop and
  Windows: passed on build-7, in that order`
- `login RULE-2 is a hand check audited weak with the finding PROOF-3 reads the status alone.;
  its stop ends on What the audit found and that finding`

### G12. A sign-off file edited and not committed still counts, and its notes are shown (medium)

- Where: `signatures.py:91` reads the working tree, `:131` judges the last commit;
  `payload.py:771-810` shows every note of every file, counting or not, tracked or not.
- What breaks unnoticed: a note typed into the file by hand reads on the status and the
  dashboard as `noted at the sign-off of 0.1.0 by quinn.qa@...`.
- Proposed rule (signatures.md): `A sign-off is read as HEAD holds it: a file not tracked, or
  changed and not committed, does not count, and no note of a sign-off that does not count is
  shown`
- Proof: `After quinn.qa@labconnect.example signs 0.1.0 with the note the tube is red, the
  file's note is edited to the tube is blue and not committed; the sign-off does not count, and
  login RULE-2's strong cell carries no reason holding the tube is blue`

### G13. Three branches of the fingerprint check (low to medium)

- Where: `package.py:803-806, 832-834, 840-842`.
- Not shown: a package with an added top-level key, with a key removed or reordered, and one
  whose content matches while its bytes do not (rewritten with CRLF or another indent, the
  likely accident on Windows).
- Add to package RULE-22, one proof: `A signed package is rewritten with every \n as \r\n and
  checked with purlin:sign --check; it exits 1 and prints only The package does not match its
  fingerprint: the fingerprint matches the content, but the bytes are not in the canonical
  form.`

Totals proposed: 6 new rules (G0, G1, G2, G5, G7, G12), 2 rules reworded (G3 signatures
RULE-108, G8 package RULE-33), 16 proofs.

## 3. The six known items

1. **The walk's line for a result from another machine: confirmed, no proof.** `sign.py:621-635`;
   PROOF-242 shows one system on the local machine. The overview (PROOF-232) and the run line
   (PROOF-227) are also local only. Package RULE-32 / PROOF-66 proves the `runs` entry for
   `build-7`, not the line the signer reads. See G11.
2. **A tracked file under `.purlin/` is not a changed file: confirmed**, `sign.py:220`. What is
   signed is still the committed state, so the direct harm is small. The larger form of the
   same choice is `package.py:74`: a committed change to `.purlin/config.json` ends no result
   and no sign-off (G8).
3. **Decision 120's last note at the stop: not built, not ruled, not proven.** The status and
   dashboard show it (states RULE-116, PROOF-276, 277); `render_stop` does not, and no rule in
   `signatures.md` asks for it. See G1.
4. **The bundled rules.** RULE-102: all five causes have a proof (244/245, 223, 226, 246, 206).
   RULE-124: all three (224, 225, 207). RULE-125: all three (243, 208, 162). What is missing
   is under RULE-102's "a rule does not pass": only a failing rule is shown, not a rule never
   run, a slow proof not run, or a rule with no result on its system (G4); and the spec-mistake
   and stale-comment refusals have no rule (G5).
5. **Key deleted, and the key guard: both present.** RULE-97 / PROOF-193 (still counts after
   the key is deleted); RULE-17 / PROOF-95 (`ssh-keygen` is not named while
   `~/.ssh/id_ed25519` exists; Purlin only prints commands and writes no key).
6. **Tampering.**
   - Package edited after signing: caught by `--check` (PROOF-17, 241). Not caught by whether
     a sign-off counts, by the status, or by a later sign-off, when the `fingerprint` field is
     left alone (G3).
   - Sign-off file edited after its commit: committed unsigned, it stops counting (the path of
     PROOF-96); edited and not committed, it still counts and its note is shown (G12).
   - Sign-off copied from another version: does not count, `package_hash` differs (RULE-108,
     the direction PROOF-217 shows). The file's own `version` and `signer` are never compared
     with its folder, its name or its commit; by decisions 48 and 52 who signed is recorded,
     not checked.
   - Tag moved or re-pointed: `purlin:sign` refuses a tag off HEAD's history or with code
     changed since (PROOF-224, 225). The status verifies nothing: any `signed/*` tag, unsigned
     and hand-made, reads as signed (G0). RULE-89 / PROOF-178 proves the tag Purlin writes is
     signed, and nothing reads that signature back.
   - An unsigned commit touching the sign-off later: does not count (`signatures.py:131-134`),
     and nothing a person sees changes, since nothing calls it (G0).
   - `package_hash` matching while the evidence underneath is not HEAD's: allowed by design
     for evidence-only commits after the tag (states PROOF-169), and a later signer signs the
     committed package without it being rebuilt or checked (G3).


---

## Appendix F. Part 2: the evidence and the run

# Part 2 slice: the run and the evidence

Read in full: `scripts/run/evidence.py`, `scripts/mcp/purlin/evidence.py`, `scripts/run/purlin_run.py`.
Read in part, where a decision is made: `scripts/mcp/purlin/states.py` (the passed cell),
`scripts/mcp/purlin/frameworks.py` (`leave_out`), `scripts/export/package.py`
(`only_records_between`, `off_code`, `taken_dirty`). Nothing was run; every finding is from reading
the code and the proof lines. Specs checked: `specs/run/evidence_writer.md`, `run_script.md`,
`reports.md`, `specs/mcp/evidence.md`, `states.md`, plus greps of `ai_audit.md` and `signatures.md`.

Short names: EW = evidence_writer, RS = run_script, RP = reports, EV = mcp/evidence, ST = states.

## 1. Every case

"Refusing shown" = a proof shows the not-counting, refusing or failing direction, not only the happy path.

### When evidence is ignored, out of date, kept or dropped

| # | File:line | What happens | Rule / proof | Refusing shown |
|---|-----------|--------------|--------------|----------------|
| 1 | mcp/evidence.py:152 | File is not JSON: ignored, one warning | EV RULE-35 / PROOF-18 | yes |
| 2 | mcp/evidence.py:156 | File is JSON but not an object: ignored, one warning | EV RULE-35 / none for this arm | no (low, same code path as 1) |
| 3 | mcp/evidence.py:160 | Another `schema`: ignored, one warning | EV RULE-35 / PROOF-52 | yes |
| 4 | mcp/evidence.py:164 | `source` disagrees with its folder: ignored | EV RULE-35 / PROOF-19; ST RULE-42 / PROOF-50 | yes |
| 5 | mcp/evidence.py:188 | A `platforms` key other than the three systems is skipped | EV RULE-14 / PROOF-20 | yes |
| 6 | mcp/evidence.py:197 | Section out of date where a fingerprint part differs; all three where it stores none | EV RULE-15 / PROOF-55, 57 | yes |
| 7 | mcp/evidence.py:248 | Audit entry answers only while its three hashes match | EV RULE-16 / PROOF-58; ST PROOF-160 | yes |
| 8 | mcp/evidence.py:290 | A proof reads the worst of its tests | EV RULE-20 / PROOF-28, 29; EW PROOF-25 | yes |
| 9 | mcp/evidence.py:256, 272 | The could-not-run file is read for the strong cell's reason | ST RULE-118 / PROOF-71 (file written by the test's own hand) | reader only; see U1 |
| 10 | states.py:312 | Newest section that speaks is not current: `out of date`, counts nothing | ST RULE-7, RULE-45 / PROOF-9, 119, 54; RS RULE-20 | yes |
| 11 | states.py:334-361 | Two systems disagree: `partial`, not met | ST RULE-117 / PROOF-53, 66 | yes |
| 12 | states.py:341, 479-501, 579 | Two current sections for the SAME system, `local` and `ci`, disagree: `platforms` takes the newer, but any current failing section makes the rule `failed` | none | no; see U8 |
| 13 | states.py:616 | `@env` proof proved only by that system's section | ST RULE-6 / PROOF-8 | yes |
| 14 | states.py:197, run/evidence.py:195 | `nothing to check:` skip passes on an anchor, reads `not run` elsewhere | EW RULE-29 / PROOF-93, 94; ST RULE-115 / PROOF-274, 278; RS PROOF-274 | yes |
| 15 | mcp/evidence.py:57 | Only a reason starting exactly `nothing to check:` counts | EW RULE-29 words it; no proof of a near miss (`nothing to check here`) | no (low) |
| 16 | ST (payload) | Test reports under `.purlin/runtime/reports/` are not read as evidence | ST RULE-4 / PROOF-7 | yes |
| 17 | run/evidence.py:296, 377 | Writer: a file it cannot read, or of another schema or source, is started afresh | none directly (EW RULE-23, 26 cover the merge cases) | no (low) |
| 18 | run/evidence.py:407 | Same results, same fingerprint, same machine, only records committed since: file left byte for byte | EW RULE-31 / PROOF-91, 92, 60 | yes |
| 19 | run/evidence.py:274-277 | `dirty` is left out of that comparison, so a kept section keeps its old `dirty` | none | no; see U3 |
| 20 | run/evidence.py:274 | Another `machine` replaces the section | EW RULE-17 / PROOF-43 | yes |
| 21 | run/evidence.py:349; purlin_run.py:922-947 | Conflicted file written afresh; audit entries kept only where three hashes are current | EW RULE-26 / PROOF-88, 89 | yes |
| 22 | run/evidence.py:518 | Entries of rules the spec no longer has are dropped | EW RULE-5 / PROOF-5 | yes |
| 23 | run/evidence.py:586 | Evidence of a feature no spec defines is deleted, both sources | EW RULE-6 / PROOF-6, 39 | yes |
| 24 | run/evidence.py:485 | A repeated audit entry keeps its `at`; one that differs replaces it | EW RULE-14 / PROOF-14, 64, 65 | yes |
| 25 | run/evidence.py:95-129 | Rule word: failed, no test, not run, passed | EW RULE-2 / PROOF-18, 77, 25 | yes |
| 26 | run/evidence.py:113 | All-`@manual` rule reads `passed`; manual beside a failure stays `failed` | EW RULE-30 / PROOF-21, 24 | yes |
| 27 | run/evidence.py:255 | Rule with no proof, marked by its own id | EW RULE-15 / PROOF-15, 72 | yes |
| 28 | purlin_run.py:758-796 | A left-out slow test keeps the result of the section being replaced, where the fingerprint is the same | RS RULE-106 / PROOF-279, 280 | partly; see U2 |
| 29 | purlin_run.py:841-857 | `dirty` is true for any change outside `.purlin/`, untracked files included; a changed `.purlin/config.json` is not counted | EW RULE-1 / PROOF-17 (tracked source file only) | no for the settings file; see U6 |

### What a run starts and leaves out

| # | File:line | What happens | Rule / proof | Refusing shown |
|---|-----------|--------------|--------------|----------------|
| 30 | purlin_run.py:1165 | No feature named: runs what changed, skips the rest | RS RULE-55, 101 / PROOF-88 to 94 | yes |
| 31 | purlin_run.py:1502 | Nothing selected: no test, no evidence; exit 1 where the standing evidence holds a failure | RS RULE-100 / PROOF-95, 96, 257, all exit 0 | no; see U4 |
| 32 | purlin_run.py:1186-1207 | Narrow run hands only marked files; a suite with none is not started | RS RULE-58 / PROOF-191, 193 | yes |
| 33 | purlin_run.py:1190, 688 | `@slow` left out unless `--all` or `--ci` | RS RULE-104 / PROOF-275, 276 | yes |
| 34 | frameworks.py:375-378 | A command that cannot leave a test out: the slow test is started and counts | RS RULE-105 / PROOF-278 | yes |
| 35 | frameworks.py:401-405 | dotnet: every slow test is called held, whatever its attribute | RS RULE-105 / PROOF-277 (one `[Fact]`-style name) | no; see U9 |
| 36 | purlin_run.py:559 | pytest exit 5 with the deselect option is not a failure | none | n/a (safe: a marker with no result is still named missing) |
| 37 | purlin_run.py:326, run/evidence.py:115 | `@env` for another system: `not run` here, never missing | RS RULE-10 / PROOF-10, 115; EW PROOF-29 | yes |
| 38 | run/evidence.py:111 | `@manual`: nothing to run | EW RULE-30 | yes |
| 39 | purlin_run.py:1176 | `--ci` answers only for proofs tagged for this system | RS RULE-12 / PROOF-12, 117, 209 | exit 0 only; see U5 |
| 40 | purlin_run.py:1557 | Only `--audit` audits | RS RULE-75 / PROOF-102 | yes |

### Refusals, warnings and exits

| # | File:line | What happens | Rule / proof | Refusing shown |
|---|-----------|--------------|--------------|----------------|
| 41 | purlin_run.py:303-310, 1121 | Wrong command line: exit 2 | RS RULE-98 / PROOF-1 | yes (one shape; `--all` with `--feature` has none, low) |
| 42 | purlin_run.py:289, 1130 | `--project-root` empty or not a directory: exit 2 | RS RULE-98 names it / none | no (low; see U10) |
| 43 | purlin_run.py:1160 | Unknown feature: exit 2 | RS RULE-98 / PROOF-2 | yes |
| 44 | purlin_run.py:1373 | No settings, unreadable settings, 0.9.5 project: exit 1, nothing written | RS RULE-103 / PROOF-137, 138, 224 | yes |
| 45 | purlin_run.py:1150 | No test command: exit 1 | RS RULE-102 / PROOF-126, 127 | yes |
| 46 | purlin_run.py:1148 | A bad `tests` entry is left out, the run carries on | RP RULE-35 / PROOF-20, 88, 108 | yes |
| 47 | purlin_run.py:551, 565 | Old report deleted; no report or unreadable report: missing evidence, exit 1 | RP RULE-17, 34 / PROOF-17, 18, 114 | yes |
| 48 | purlin_run.py:449, 538, 556 | Timeout: missing evidence, exit 1 | RS RULE-79 / PROOF-242 (pytest; the `exit` suite's `on <path>` arm has none, low) | yes |
| 49 | purlin_run.py:1242-1253 | Marker with no passing or failing result: named missing, exit 1 | RS RULE-8 / PROOF-244, 9, 274 | yes |
| 50 | purlin_run.py:1262 | Marker no test follows: named, exit 1, `missing` | RP RULE-33 / PROOF-5 | yes |
| 51 | purlin_run.py:1268 | Marker naming a feature or proof no spec has: exit 1 | RP RULE-33 / PROOF-19 | yes |
| 52 | purlin_run.py:1268 | Marker naming a RULE that has proofs: exit 1, result not read | RP RULE-33 words it / none | no; see U7 |
| 53 | reports (tie) | Report case matching two tests counts for neither | RP RULE-33 / PROOF-13 | yes |
| 54 | purlin_run.py:1317 | A failing test exits 1 and is not called missing | RS RULE-5 / PROOF-5 | yes |
| 55 | purlin_run.py:1098, 1317 | A spec writing a number twice or holding a conflict line: exit 1 after every test ran | RS RULE-87 / PROOF-261 (the number arm) | yes |
| 56 | purlin_run.py:1277 | Stale test comment printed, no exit code | RS RULE-96 / PROOF-271 | yes |
| 57 | purlin_run.py:1562 | `--audit` exits as its tests do, or 1 where the audit stopped | RS RULE-48 / PROOF-87, 109 (the stopped arm belongs to the audit slice) | yes for the tests |
| 58 | purlin_run.py:1345 | `--ci` exits 1 only on a tagged test failing or missing | RS RULE-12 / PROOF-209 | no; see U5 |

### What a run writes and commits

| # | File:line | What happens | Rule / proof | Refusing shown |
|---|-----------|--------------|--------------|----------------|
| 59 | purlin_run.py:1348 | Writes evidence, commits nothing without `--commit` | EW RULE-9 / PROOF-9 | yes |
| 60 | run/evidence.py:621 | First commit: specs, marked tests, settings, by path | EW RULE-19 / PROOF-50, 49; RS PROOF-257 | no proof that a changed file outside those is left out; see U6b |
| 61 | run/evidence.py:675 | Second commit: `local/` and removals; never pushes | EW RULE-32 / PROOF-10, 39, 38 | yes |
| 62 | run/evidence.py:692 | `--ci --commit`: `ci/` alone, never pushes | EW RULE-33 / PROOF-95, 96 | yes |
| 63 | purlin_run.py:1348 | `--test` writes nothing under `ci/`, nothing under `specs/` | RS RULE-17, RULE-3 / PROOF-17, 113 | yes |
| 64 | run/evidence.py:713-720 | git refusing the commit (a hook, a signing failure) prints `there is no git repository to commit it to` and the exit code is unchanged | none | no (low; the status still lists the evidence as to commit) |
| 65 | run/evidence.py:491 | `write_could_not_run` writes the reasons file | none; no caller | see U1 |

65 cases. 51 have a rule and a proof that shows the refusing direction. 14 do not: 10 are written up
below (U1 to U10, two of them holding two cases), and cases 2, 15, 17, 36, 64 are noted as low and
left without a proposal because a rule there would pin detail, not protect anything.

## 2. Cases with no proof, or none in the refusing direction

Ranked. High = a result could count, or be attributed, when it should not, unnoticed.

### U1. Nothing records why a rule stayed not audited (medium)
- `scripts/run/evidence.py:491` `write_could_not_run` has no caller anywhere under `scripts/`
  (grep: only its definition). The readers are live: `mcp/purlin/evidence.py:256, 272`,
  `payload.py:202, 513`, `states.py:689`.
- What happens: when the model cannot be reached the audit prints its one line (ai_audit RULE-43,
  PROOF-108 to 110) and writes no entry. `.purlin/runtime/audit_could_not_run.json` is never
  written, so the status always reads `no audit has run on this code`, never
  `the AI audit could not run: <why>`. ST PROOF-71 passes because the test writes the file itself.
- What breaks unnoticed: a signer reading `not audited` cannot tell "nobody ran it" from "it was
  run and the model was down"; half of ST RULE-118 is unreachable in the product.
- Either wire it or delete it (the clean-release decision 44 argues for one of the two). To wire:
  - Rule (ai_audit): `When the model cannot be reached for a rule, the audit records the cause for that rule under .purlin/runtime/, and the status gives it as the rule's reason until an audit reads the rule; nothing about it enters the evidence`
  - Proof: ``claude` exits with the code 1 at every call and the audit reads `login` `RULE-2`, which passes; afterwards `RULE-2`'s strong cell reads `not audited` with a reason starting `the AI audit could not run:`, and `.purlin/evidence/local/login.json` holds no `audit` entry for `RULE-2``

### U2. A kept slow result is re-stamped with this run's commit, machine and person (high)
- `scripts/run/purlin_run.py:758-796` with `scripts/run/evidence.py:162-252`.
- What happens: `purlin:test <feature>` leaves the slow test out, copies its `pass` from the
  section on disk when the fingerprint matches, and writes a new section whose `commit`, `at`,
  `dirty`, `machine`, `runner` and `email` are this run's. The fingerprint covers only that
  feature's spec, scope and tests.
- What breaks unnoticed: the sign-off counts a result only where the section's commit is the
  version being signed (`package.same_code`). After a commit that changes a file outside the
  feature's scope, a named run stamps the old slow pass with the new commit, so the sign-off
  takes a slow (integration) result as taken on this version when its test last ran on an earlier
  one; and a pass first taken on `build-1` by one person is recorded as run on `build-2` by
  another. Decision 106 and 107 ("taken on this exact version"), decision 105 ("who ran it").
  Not confirmed by running; the sign-off side should be checked by the sign-off slice.
- Rule (run_script, narrowing RULE-106): `A result kept for a slow proof counts for the status alone: a section holding one names the commit the slow test last ran on for that proof, so the sign-off refuses it until purlin:test --all runs on the version being signed`
- Proof: `In a git checkout, `--all --test --commit` passes `feat`'s slow PROOF-2; `README.md`, which no scope names, is changed and committed; `--feature feat --test --commit` runs; `purlin:sign --show` exits 1 naming `feat` as a result not taken on this version of the code`
- If the owner instead accepts the re-stamp, the rule to write is the opposite one, and the docs
  should say a slow result is carried while its feature is unchanged. It is a decision, not only a proof.

### U3. A section taken over uncommitted changes cannot be cleared by running again (medium)
- `scripts/run/evidence.py:274-277, 407-410`: `dirty` is left out of `_same_observation`.
- What happens: a run with an untracked or changed file outside the feature's scope writes
  `dirty: true`. The file is removed, the run is made again on the same commit: same results,
  same fingerprint, same machine, same commit, so the section is left as it was, `dirty: true`
  included. The sign-off refuses ("a result was taken while files were changed") and names the
  run, which changes nothing. The way out is a commit that touches a project file or deleting
  the evidence file, and nothing says so.
- What breaks unnoticed: a person stuck at the sign-off, which decision 104 counts as a failure
  of the collaboration. The reverse also holds: a clean section stays `dirty: false` when the
  same run is repeated over an uncommitted change outside scope, harmless because the sign-off
  refuses changed files itself.
- Rule (evidence_writer, amending RULE-31): `A section whose `dirty` differs from the one on disk replaces it`
- Proof: `In a git checkout, `--all --test` runs while `notes.txt` is written and not added to git, and the section's `dirty` is true; `notes.txt` is deleted and `--all --test` runs again on the same commit; the section's `dirty` is false`

### U4. A run that selects nothing must exit 1 over failing evidence (medium)
- `scripts/run/purlin_run.py:1511-1513`, `failed_rules` at 1083.
- What happens: with nothing to run, the exit code is 1 where any rule reads `failed` on the
  evidence it stands on. RS RULE-100 says so; PROOF-95, 96 and 257 all end in exit 0.
- What breaks unnoticed: `purlin:test` run a second time after a failing run would read green to
  an agent or a pipeline that checks the exit code.
- Add a proof to RS RULE-100: `In a git checkout whose one marked test fails, `--all --test` exits 1; with nothing changed, `--test` with no feature named prints `Nothing to run`, starts no suite, and exits 1`

### U5. `--ci` must exit 1 when a tagged test fails or does not run (medium)
- `scripts/run/purlin_run.py:1311-1314, 1345`.
- What happens: RS RULE-12 says exit 1 when a test tied to a tagged proof failed or could not
  run. PROOF-12, 117 and 209 all show exit 0; PROOF-171 uses a failing script but asserts only
  the log.
- What breaks unnoticed: a project's own Windows job goes green while its tagged test failed.
  The evidence still records `fail`, so the status is right; only the job's colour lies.
- Add a proof to RS RULE-12: `feat`'s PROOF-2 is tagged for this machine's system and its test fails; `--all --ci` exits 1, and `.purlin/evidence/ci/feat.json` lists PROOF-2 as `fail` and reads `RULE-1` `failed``

### U6. Results taken under an uncommitted test command read as clean (medium)
- `scripts/run/purlin_run.py:855`: every path under `.purlin/` is skipped, `.purlin/config.json`
  included. The fingerprint (`mcp/purlin/fingerprint.py:320`) covers spec, code and tests, not
  the `tests` setting.
- What happens: a run made with an edited, uncommitted `tests` command writes `dirty: false`,
  and editing the command afterwards puts no evidence out of date.
- What breaks unnoticed: the committed evidence does not say which command produced it; a
  command changed to run fewer files would still be caught as missing markers, one changed to a
  script that writes a canned report would not. `--commit` does commit the settings first, so the
  hand-off path is safe; the plain `purlin:test` then `git commit` path is not.
- Rule (evidence_writer): `A run made while `.purlin/config.json` differs from the commit writes its section with `dirty` true`
- Proof: `In a git checkout whose spec and test are committed, the `tests` command in `.purlin/config.json` is edited and not committed; `--all --test` writes a section whose `dirty` is true`
- Same root as the sign-off item "a tracked file under `.purlin/` other than evidence is not
  counted as a changed file"; one decision settles both.

### U6b. `--commit` never commits a file outside the specs, marked tests and settings (medium)
- `scripts/run/evidence.py:644-647` commits by path, which is right; no proof holds it.
  EW PROOF-10 and RS PROOF-257 have nothing else changed in the tree; only the `--ci` proof
  (EW PROOF-95) carries an unrelated edit.
- What breaks unnoticed: a change to `git add --all` without paths would commit a person's
  unfinished source under `purlin: specs, tests and settings`, and the evidence would then read
  clean over code nobody reviewed.
- Add a proof to EW RULE-19: `In a git checkout where the spec `feat` and `src/other.py` are both edited and not committed, `--all --test --commit` commits `specs/a/feat.md` and not `src/other.py`, which git status still lists as changed, and the section's `dirty` is true`

### U7. A test marked with a rule's id where the rule has proofs (low to medium)
- `scripts/run/purlin_run.py:1268` (`reports.marker_problems`); `run/evidence.py:204-217` reads
  a rule's own marker only where it has no proof.
- RP RULE-33 names the case; PROOF-5, 19 and 13 cover the other three.
- What breaks unnoticed: if the refusal went, a test marked `login RULE-1` would be silently
  ignored, or worse read as proving every proof of the rule.
- Add a proof to RP RULE-33: ``login`'s `RULE-1` has `PROOF-1`, whose marked test passes, and a second passing test is marked `purlin: login RULE-1`; the run exits 1 and prints one line naming that comment's file and line, and the evidence lists no entry whose `id` is `RULE-1``

### U8. Two current sections for one system, `local` and `ci`, that disagree (low to medium)
- `scripts/mcp/purlin/states.py:341, 479-501, 579-596`.
- What happens: `platforms` shows the newer section's word, but `_failing_where` reads every
  current section, so a failure in either source makes the rule `failed`. The direction is safe.
  ST PROOF-66 is two systems; PROOF-54 is an out-of-date section.
- What breaks unnoticed: a change making the newer section win outright would let a local pass
  hide a current `ci` failure on the same code.
- Add a proof to ST RULE-9: `A rule's one proof fails in a current `ci` section from `linux` dated `2026-09-01T00:00:00Z` and passes in a current `local` section from `linux` dated `2026-09-02T00:00:00Z`; the passed cell reads `failed` with the reason `failing: Linux/Unix, ci``

### U9. A slow NUnit `[TestCase]` runs anyway and is named as left out (low)
- `scripts/mcp/purlin/frameworks.py:401-405`; `purlin_run.py:647, 731-745`.
- See answer 2 below. No result is wrong; one printed line is.
- Add a proof to RS RULE-105 only if the owner wants the line right: `A slow test declared under `[TestCase(1)]` in a dotnet suite is started, and the run prints `Started 1 slow test in the dotnet suite: its command gives Purlin no way to leave one test out.` and no `Left out` line`

### U10. `--project-root` empty or not a directory (low)
- `scripts/run/purlin_run.py:289-296, 1130`. RS RULE-98 names it; no proof.
- What breaks unnoticed: an empty value would run against the folder the caller happened to be
  in and write evidence there, which in a worktree is another checkout (decision 115).
- Add a proof to RS RULE-98: `Started as `--all --test --project-root ''`, the run exits 2, prints `purlin: --project-root needs a directory, not an empty value.`, and writes nothing under the working directory`

Total proposed here: 3 new rules (U1, U2, U6), 1 rule amended (U3), and 10 proofs (one each for
U1 to U8 and U6b, U10), 11 with the optional U9.

## 3. The seven known items

1. **Why a rule stayed not audited.** Confirmed. `write_could_not_run` exists
   (`scripts/run/evidence.py:491`) and nothing calls it; `scripts/review/` never names it or the
   file. The reading half is live and has a proof (ST RULE-118, PROOF-71) whose test writes the
   file by hand. No rule covers the writing. See U1.
2. **A slow NUnit `TestCase`.** Confirmed by reading, not by running. For dotnet, `leave_out`
   returns every slow test as held and adds `--filter 'FullyQualifiedName!=Ns.Class.Method'`
   (`frameworks.py:401-405`). NUnit names each `[TestCase]` row with its arguments,
   `Ns.Class.Method(1)`, so the exact comparison leaves none out and the test runs. The run has
   already printed `Left out 1 slow proof`. The result is then tied and written as `pass` or
   `fail`: `purlin_run.py:647` clears `held` once the test has a result, so the evidence is true
   and the result counts. xUnit `[Theory]` rows share the method's name and are left out. The
   other tools: pytest `--deselect` is exact; vitest, jest and go start a slow test whose title
   or name another test shares, and say so; an `exit` suite's file is simply not run; an unknown
   command starts it and says so. Only the dotnet arm claims a hold it cannot make.
3. **A crash before a report, or a report that cannot be read.** Ruled out. The report is
   deleted before the suite starts (`purlin_run.py:551`, RP RULE-17, PROOF-17); with no readable
   report the suite's outcomes are empty, every marker reads `not run`, the evidence writes
   `missing`, the run prints `Evidence is missing` and exits 1 (RP RULE-34, PROOF-18, 114). The
   new section differs from the old one, so it replaces it and no old pass survives
   (`evidence.py:407`). The one way an old pass survives a run is the slow carry-over, U2.
4. **A marker naming a proof that does not exist; two tests on one proof.** Ruled out. The first
   exits 1 with a line (RP RULE-33, PROOF-19). The second reads the worst test at the writer
   (EW PROOF-3, 25) and the reader (EV RULE-20, PROOF-28, 29). The sibling case, a rule's id on
   a rule that has proofs, has no proof: U7.
5. **Zero tests collected.** Ruled out as a way to pass. A marker with no case in the report is
   named missing and exits 1 (RS RULE-8; RP PROOF-79). A project with no markers names nothing
   missing and every rule reads `no test` (RS RULE-7, PROOF-7). pytest's exit 5 is forgiven only
   when Purlin itself deselected tests (`purlin_run.py:559`), and missing markers still fail the
   run; that arm has no proof and needs none.
6. **Evidence for a deleted or renamed spec.** Ruled out. Every run that reaches the write
   deletes both sources' files and says so (EW RULE-6, PROOF-6), and `--commit` commits the
   removals (PROOF-39). A run that selects nothing does not prune, which loses nothing: the
   status reads specs, not evidence files.
7. **Two machines disagreeing on one rule and one system.** Within one source there is one
   section per system, so the later run replaces the earlier (EW RULE-17, PROOF-43) and a merge
   of the two conflicts and is rewritten by the next run (EW RULE-23, 26). Across `local` and
   `ci` both sections can be current: any failure wins and the rule reads `failed`
   (`states.py:341, 579`). The behaviour is safe and has no proof: U8.


---

## Appendix G. Part 2: the audit

# Part 2, slice: the audit (`audit_run.py`, `plain_checks.py`, `targeted_break.py`)

Read in full: `scripts/review/audit_run.py`, `targeted_break.py`, `plain_checks.py`; the helpers in
`scripts/review/ai_audit.py` (`is_read`, `ask_model`, `audit_all`, `ask_for_bug`, `bug_prompt`,
`break_key`), `scripts/run/evidence.py` (`audit_entry`, `merge_audit`, `_same_audit`,
`write_could_not_run`), `scripts/mcp/purlin/evidence.py` (`audit_entry`, `could_not_run`),
`scripts/mcp/purlin/states.py:675-692`, `scripts/run/purlin_run.py:1546-1562`. Specs:
`specs/review/ai_audit.md`, `plain_checks.md`, `planted_bug.md`, `specs/mcp/states.md`.
Nothing was run. Items marked "inferred" were read from the code and not exercised.

## 1. Every case

| # | file:line | What happens | Rule / proof | Failing direction shown |
|---|-----------|--------------|--------------|-------------------------|
| 1 | audit_run.py:359 | verdict `weak` when a spot test fired or a bug survived, else `strong` | ai_audit RULE-33; PROOF-95, 96, 97 | yes |
| 2 | audit_run.py:359, 307 | every bug `not made` (model said `no break:`, garbage, wrong file) and no spot finding: `strong`, with `no bug was planted` printed | RULE-33 ("caught or not made") | **no**: no proof holds `not made` then `strong`, none holds the printed line |
| 3 | audit_run.py:375-379 | model unreached and not weak: no entry, `not audited` | RULE-43; PROOF-108, 110 | yes |
| 4 | audit_run.py:375, 384 | model unreached, spot test fired: `weak`, model `unknown` | RULE-43; PROOF-109 | yes |
| 5 | audit_run.py:283-286, 375 | model unreached, a kept bug survived: `weak` | RULE-43 (clause) | **no proof** of this clause |
| 6 | audit_run.py:295-297, 373 | mixed reach: bug call answered, reading not (or the reverse): no entry; the bug results of this run are thrown away | RULE-43 ("for a planted bug or for its reading") | **no**: all three proofs fail every call |
| 7 | audit_run.py:375-379 with evidence.py:451 (`merge_audit` only adds) | a rule read again (`--all`, or code changed) with the model unreached gets no new entry, but its earlier entry stays in the evidence; the audit prints `not audited` and `stays not audited` while the status and the share line (audit_run.py:436) still read the old `strong` | none | **no** (inferred) |
| 8 | ai_audit.py:352-367 | `claude` exits 0 with empty output, non-JSON output, or JSON with no `result` (no look at `is_error`): counted as reached; a bug reads `not made`, the reading is empty, the rule is written `strong` | none (RULE-39 lists only three unreachable causes) | **no** |
| 9 | targeted_break.py:197-200, 274-306 | `caught` is "anything but all pass": failure, collection or import error, timeout, a test file no suite claims (:287), no result found (:306) | planted_bug RULE-3 says "fails"; PROOF-3 a failing test | **no**: no proof for error or timeout verdicts, and no baseline run in the copy before the bug |
| 10 | targeted_break.py:259-267 | the copy leaves out ignored files (`node_modules`, `.venv`, built output, local config) and symlinks; a test that needs them fails in the copy with or without the bug, so every bug reads `caught` | RULE-1 states how the copy is made | **no**: nothing shows the test passes in the copy unbroken |
| 11 | targeted_break.py:171-173 | the change must be in a scope file; nothing refuses a scope file that holds the proof's own test, so "breaking" the test reads `caught` | RULE-12, PROOF-15 (outside scope) | **no** for a test file inside the scope |
| 12 | targeted_break.py:169, 224-229 | absolute path, `..`, or a path that resolves outside the copy: `not made`, nothing written | RULE-5; PROOF-6 | yes |
| 13 | targeted_break.py:161-164, 183-189 | no change named, `no break:`, not found, found twice, unchanged: `not made`, test not run | RULE-12; PROOF-5, 10, 15 | yes |
| 14 | targeted_break.py:106-113, 313-359 | status and file hashes before and after each bug; a difference raises `ProjectChanged`, the audit prints the line and exits 1 before any entry is written | RULE-6; PROOF-7, 13 | partly: PROOF-7 does not show that no audit entry was written |
| 15 | audit_run.py:364-365 | the model's reading (`claude -p`, cwd the project, no tool limit) runs with **no** before-and-after check; only the planted bug is guarded | none | **no** |
| 16 | targeted_break.py:174, 201-202 | the copy is a `purlin-break-*` temp folder, removed in `finally` on pass, fail, timeout, exception, Ctrl-C | RULE-7; PROOF-8, 14 | yes for fail and timeout; none for `survived` or an exception (low) |
| 17 | targeted_break.py:174 | a hard kill leaves the copy in the temp folder; nothing removes leftovers on the next run. The project is untouched: it is only read | none | no (low) |
| 18 | targeted_break.py:176, audit_run.py:360 | an `OSError` while copying, or git taking over 120 s, is not caught: a traceback, nothing written, copy removed | none | no (low) |
| 19 | targeted_break.py:251-256, 315 | outside a git repository `git ls-files` and `git status` fail: the copy is empty, every bug reads `not made`, and the guard sees nothing | none (decision 112 cut runs outside git) | no (low) |
| 20 | audit_run.py:281-287 | kept bug: same test source and same code part, no new bug | RULE-36; PROOF-100 | kept direction only: **no proof** that a changed test or changed code plants again |
| 21 | evidence.py:484-487 (`_same_audit` leaves out `breaks`, `commit`) | after a code change, a re-read with the same verdict keeps the old entry, old `commit` and old `break_key`: the rule is read and its bug planted again on every later audit (inferred) | none | no (cost, not safety) |
| 22 | audit_run.py:269 | anchor: no bug, verdict from spot tests | RULE-37; PROOF-102 | yes |
| 23 | audit_run.py:276, ai_audit.py:124 | `@manual` proof: no bug; rule read only if another proof has a test | RULE-1, RULE-35 | yes |
| 24 | ai_audit.py:130-141, audit_run.py:110-127 | which rules are read: passing, tested, no current entry or code changed, or `--all` | RULE-1; PROOF-4, 103, 51 | yes. A rule whose test fails is not read: PROOF-104 |
| 25 | audit_run.py:124-125 | a feature whose scope names nothing: code never reads as changed | none | no (low) |
| 26 | audit_run.py:217 | a test whose source cannot be found is skipped by the spot tests, with no line saying so | ai_audit RULE-40 (shows none) | **no**: the skip is silent |
| 27 | plain_checks.py:432-434 | a Python test the syntax tree cannot locate: checks 1 to 5 return nothing, silently | none | no (low) |
| 28 | plain_checks.py:118, 123 | language not read for a check: `(check, None)`, one line per check and language | RULE-7; PROOF-28 | yes |
| 29 | plain_checks.py:486-492, 796-823 | check 1 and its exemptions | RULE-1; PROOF-1, 3, 4 | yes |
| 30 | plain_checks.py:508-534, 825-855 | check 2 | RULE-2; PROOF-9, 10, 11 | yes |
| 31 | plain_checks.py:536-549, 857-875 | check 3 | RULE-3; PROOF-13, 14, 17 | yes |
| 32 | plain_checks.py:577-593, 907-922 | check 4 | RULE-4; PROOF-18, 19, 20 | yes |
| 33 | plain_checks.py:633-638, 955-960 | check 5 | RULE-5; PROOF-22, 23, 24 | yes |
| 34 | plain_checks.py:276-296 | check 6: fires only when the file holds none of the backticked values; one of several is enough, anywhere in the file | RULE-6; PROOF-25, 26, 27 | yes (the edge is by design) |
| 35 | ai_audit.py:428-445, audit_run.py:271 | sent to the model for a bug: every file the scope reaches, in full, plus the tests' source; nothing outside the scope | ai_audit RULE-2 covers the reading's prompt only | **no rule** for the bug's request (true by construction) |
| 36 | audit_run.py:407, 467 | writes `.purlin/runtime/audit_run.json` | none (not evidence) | n/a |
| 37 | purlin_run.py:1559-1562 | exit code: the tests', or 1 when stopped; weak or unreached never changes it | run_script RULE-48 | yes |
| 38 | evidence.py:491 | `write_could_not_run` has no caller; states.py:689 and states PROOF-71 read a file nothing writes | states RULE-118 / PROOF-71 (reader only) | **no** |
| 39 | audit_run.py:232-240 | a survived bug with no relevance check: an irrelevant change that survives makes the rule `weak` | RULE-2, RULE-33 | by design; measured, not ruled (decision 116) |

39 cases; 16 with no proof or no failing-direction proof (2, 5, 6, 7, 8, 9, 10, 11, 14, 15, 17-19 as one, 20, 21, 26, 35, 38; 25 and 27 noted, no rule proposed).

## 2. The uncovered cases, ranked

### High

**A. A test that cannot run in the copy reads `caught`, so the rule reads `strong`** (cases 9, 10).
`targeted_break.py:197-200`, `:274-306`, `:259-267`. The copy holds no ignored file and no symlink,
and there is no run of the test in the copy before the bug goes in. A JavaScript project
(`node_modules` ignored), a Python project needing a built file, or a test timing out, gets
`caught` for every bug: strong for tests that were never shown to notice anything. This needs a
code change, not only a proof.
- Rule (planted_bug): `The proof's test is run in the copy before the bug is planted; where it does not pass there, no bug is planted and the result reads `not made` with the reason `the test does not pass in a copy of the project``
- Proof: `The test of `PROOF-1` reads `data/built.json`, a file git ignores; the model answers `file: src/age.py`, `before:` `return days`, `after:` `return 0`; the result reads `not made` with the reason `the test does not pass in a copy of the project`, not `caught``
- With it, decide case 2: such a rule should not read `strong` (see C).

**B. `claude` answering nothing counts as the model having run** (case 8). `ai_audit.py:352-367`.
Exit 0 with empty or non-JSON output, or an error body, is "reached": the bug reads `not made`,
the explanation is empty, the rule is written `strong`. Decision 117 says strong means the model
part ran.
- Rule (ai_audit, extend RULE-39 or new): `An answer from `claude` that is empty, or whose JSON reports an error, is the model not reached, with the reason `claude gave no answer``
- Proof: ``claude` exits `0` and prints nothing at every call, and no spot test fires on the test of `RULE-2`; no audit entry is written for `RULE-2` and the audit prints `The model could not be reached: claude gave no answer. 1 rule stays not audited. Run purlin:audit again.``

**C. A rule for which no bug was ever planted reads `strong`** (case 2). `audit_run.py:359`.
RULE-33 says so on purpose, but no proof holds it, and with B and A it is how a strong verdict
appears with no evidence behind it. Either prove it as written or change it; a question for the
owner. Proof as written, added to RULE-33:
- `No spot test fires on the test of `RULE-2` and the model answers `no break: the proof names no value the code computes`; the audit entry reads `strong` with the planted bug of `PROOF-2` recorded as `not made`, and the audit prints `  PROOF-2: no bug was planted: the proof names no value the code computes.``

**D. The model's reading is not guarded against changing the project** (case 15).
`audit_run.py:364-365`, `ai_audit.py:340`. `claude -p` runs in the project folder with whatever
tool permissions the person's settings allow, fed test and code text; only the planted bug's call
sits inside the before-and-after check. A reading that edits a file leaves the person's code
changed and the audit says nothing.
- Rule (planted_bug RULE-6 widened, or ai_audit): `When a file of the project changes while the model reads a rule, the audit stops with the same line, writes no audit entry and exits 1`
- Proof: `The `claude` asked to read `RULE-2` appends a line to `src/login.py` in the project; the audit prints `The audit stopped: src/login.py changed while a break ran. Nothing in the project was written by the audit.`, exits `1`, and `.purlin/evidence/local/login.json` holds the bytes it held before`

**E. A bug planted in the proof's own test file reads `caught`** (case 11).
`targeted_break.py:171-173`. Only when a `> Scope:` reaches a test file.
- Rule (planted_bug, extend RULE-12): `A change to a file that holds one of the proof's tests is not applied and reads `not made``
- Proof: `The feature's `> Scope:` names `tests/test_age.py` and the model answers `file: tests/test_age.py`, `before:` `assert age(s) == 90`, `after:` `assert age(s) == 0`; the result reads `not made` and the test of `PROOF-1` is not run`

### Medium

**F. A stopped audit writes no entry: not shown** (case 14). `audit_run.py:360-362`. Add to RULE-6:
- `Bugs for `PROOF-1` and `PROOF-2` are planted and the second changes `src/age.py` in the project; the audit exits `1` and `.purlin/evidence/local/age.json` holds the bytes it held before`

**G. A changed test or changed code plants the bug again: not shown** (case 20).
`audit_run.py:281-287`. If the key stopped changing, an old `caught` would stand for new code.
Add to RULE-36:
- `A bug planted for `PROOF-2` was caught; the body of its test changes from `== 401` to `== 403`; the model is asked for a bug for `PROOF-2` exactly `1` time, and the entry's `break_key` differs from the one before`

**H. Nothing records why a rule stayed not audited** (case 38). `evidence.py:491` has no caller;
`states.py:689` and states PROOF-71 read a file no code writes, so the reason shows only in the
audit's own output. Either call it from `audit_run.run` or delete the reader and PROOF-71.
- Rule (ai_audit): `For each rule the model could not be reached for, the audit records the reason under `.purlin/runtime/`, and the status shows it until the rule is audited`
- Proof: ``claude` exits `1` at every call and the audit reads `RULE-2`; afterwards the status of `login` shows `RULE-2` as `not audited` with the reason `the AI audit could not run: claude exited with an error``

**I. Reaching the model for one call and not the other** (case 6), and **a kept survived bug with
the model unreached** (case 5). Add to RULE-43:
- `The bug for `PROOF-2` is answered and caught, then `claude` exits `1` for the reading of `RULE-2`; no audit entry is written and the audit prints `login RULE-2   not audited``
- `A bug kept for `PROOF-2` reads `survived`, and `claude` exits `1` at every call; the audit entry of `RULE-2` reads `weak` with the finding `PROOF-2: the test still passes when src/login.py:12 reads "return 200"``

**J. A rule read again with the model unreached keeps its old `strong`** (case 7, inferred).
The audit prints `stays not audited` while the evidence, the status and the share line read the
earlier entry. A question for the owner: is the earlier entry still the answer after the code
changed? If not:
- Rule (ai_audit): `A rule read again for which the model could not be reached has its earlier audit entry removed`
- Proof: ``RULE-2` carries an entry reading `strong`; `src/login.py` changes, and `claude` exits `1` at every call; afterwards `.purlin/evidence/local/login.json` holds no audit entry for `RULE-2``

**K. A test whose source cannot be found is passed over by the spot tests in silence** (case 26).
`audit_run.py:217`.
- Rule (plain_checks): `A marked test whose source cannot be found is named once, as `<file>::<test>: its source was not found, so the spot tests did not read it.``
- Proof: `The evidence names `test_renamed_away` for `PROOF-1`, which `tests/test_login.py` no longer holds; the audit prints `tests/test_login.py::test_renamed_away: its source was not found, so the spot tests did not read it.` exactly once`

### Low

- **L. Only scope files go to the model** (case 35), true by construction. Proof for ai_audit:
  `The project holds `.env` with `KEY=s3cret` and the scope of `login` names `src/login.py` alone; the request for a bug for `PROOF-2` holds the text of `src/login.py` and does not hold `s3cret``
- **M. An entry kept as "the same" keeps its old `commit` and `break_key`** (case 21, inferred):
  after a code change the rule is read, and its bug planted, on every audit. A cost bug; check and
  fix in `_same_audit`, no rule needed.
- **N. Leftover copy after a hard kill; tracebacks on a copy error; no guard outside git** (cases
  17, 18, 19). The project is never written, so no rule proposed. A proof for RULE-1 on the
  failure path costs little: `The test of `PROOF-1` runs past its limit with the bug in place; afterwards every file of the project holds the same bytes as before`
- `.bats` is called shell by `audit_run.language_of` and not by `plain_checks`; wording only.

## 3. The six known items

1. **Decision 117, strong only when the model ran.** Ruled (ai_audit RULE-43) and proven in both
   directions for a `claude` that fails every call (PROOF-108, 109, 110). Not proven: a mixed
   reach, the kept-survived clause, and a `claude` that exits 0 with nothing (B), which defeats
   the rule.
2. **Why a rule stayed not audited.** Confirmed. `write_could_not_run` (`scripts/run/evidence.py:491`)
   has no caller; the reader (`scripts/mcp/purlin/evidence.py:256`, `states.py:689`) and states
   PROOF-71 exercise a file nothing writes.
3. **Could the person's code be left changed.** Not by the planted bug: the change is written only
   through `_write_in` (`targeted_break.py:232`), which refuses any path resolving outside the
   temp copy; the project is only read. A kill mid-bug leaves the project as it was and a stray
   `purlin-break-*` folder. The before-and-after check (RULE-6, PROOF-7) detects and reports, it
   does not restore. PROOF-1 compares bytes and `git status` on the plain path only; no proof does
   on the timeout or stopped path. The open hole is D: the model's reading call is outside the
   check.
4. **A test run that errors is read as `caught`.** Confirmed, and by design in the module's
   docstring (`targeted_break.py:20`): error, not collected, timeout, no suite all read `caught`,
   hence `strong`. Wrong whenever the test cannot run in the copy at all (A).
5. **A test already red.** A rule whose passed cell is not `passed` is not read (`ai_audit.py:139`;
   PROOF-104), so no verdict. But a test green in the project and red in the copy gets `caught`
   for every bug (A); there is no baseline run.
6. **Decision 120, a spot-test finding makes the rule weak whatever the bug shows.** Ruled
   (RULE-33) and proven (PROOF-95: finding plus a caught bug reads `weak`).

Totals proposed here: 7 new rules (A, B, D, E, H, K, and J if the owner says yes) and 16 proofs
(one each for those 7, plus C, F, G, I twice, L, N; C and J wait on an answer).


---

## Appendix H. Part 3: the skills

# Part 3: the specs with almost no rules

Each `skill_*` spec holds one rule: a fixed list of commands and paths the skill's text must
hold. That is a string check. It does not show that what a skill tells the agent to run exists.

## Checked by hand today, all passing

- Every `scripts/`, `references/`, `skills/`, `docs/` and `templates/` path named in the ten
  `SKILL.md` files and `agents/purlin.md` exists.
- Every `--flag` on a line that runs a script is one that script takes: `scaffold.py`,
  `purlin_run.py`, `sign.py`, `upstream.py`, `renumber.py`, `markers.py`, `wording.py`.
- The ten `name:` values match the ten commands in `references/purlin_commands.md`.
- The four commit subjects the skills quote match `references/commit_conventions.md`.
- The refusals the sign skill quotes are the strings in `scripts/review/sign.py`.
- No skill or the agent definition names a path under `dev/` or this repository's `specs/`.

Nothing is broken today. Only the init skill has a proof of this kind (`skill_init` PROOF-24, its
flags against `--help`); the other nine and the agent definition have none.

## Mechanical and not covered

| Part | Skills | Covered today |
|------|--------|---------------|
| Every repository path the text names exists | all ten, the agent | no; the fixed lists cover 2 to 6 paths each |
| Every flag on a script line is one the script takes | anchor, audit, build, sign, spec, test | init only |
| The answers file the sign skill shows is one `sign.py --answers` accepts | sign | no; `signatures` PROOF-221 uses its own file |
| `scripts/mcp/purlin/wording.py`, which the build skill runs: its lines and its count line | build | no rule for the command; `drift` and `states` cover the same data elsewhere |
| A commit subject a skill quotes is a row of `commit_conventions.md` | anchor, init, sign | no |
| No path under `dev/` or this repository's `specs/` in a skill, the agent or a reference | all | no; CLAUDE.md says review holds it |
| The skill's `name:` is a command of `purlin_commands.md` | all | `install` RULE-3 and RULE-4 cover presence, not the match |

Already covered by the scripts' own specs: `markers.py --near-misses` (`reports` RULE-36),
`renumber.py` (`renumber`, 9 rules), `scaffold.py`, `sign.py`, `upstream.py`, `purlin_run.py`.
`.purlin/runtime/spec-from-code.json` is read by no script, so its shape is the model's own.

## Judgment, for the on-demand real-skills check

- `purlin:spec`: whether the rules say what the requirement meant, are atomic, and each proof is one
  case with exact values.
- `purlin:build`: whether the code meets the rules, each test shows its proof, and the comment sits
  on the right test.
- `purlin:spec-from-code`: which features it finds, where it draws their borders, which rules the
  code implies.
- `purlin:audit`: the model's reading and the planted bug it picks.
- `purlin:sign`: how it puts each stop to the person and carries their words into the answers file.
- `purlin:drift`, `purlin:status`, `purlin:anchor`, `purlin:init`: which `→ Run:` line it picks and
  how it words what it found.
- The agent definition: routing a person's words to a command.

## Proposed rules, pass or fail, no model

All four belong in `instructions/purlin_agent`, one home, not once per skill. 4 rules, 4 proofs.

1. **Rule**: Every path under `scripts/`, `references/`, `templates/`, `skills/` or `docs/` that a
   skill or the agent definition names is a file or folder in the repository.
   **Proof**: Each path of those five folders read out of the ten `SKILL.md` files and
   `agents/purlin.md` exists; the same check on a copy of the sign skill naming
   `scripts/review/signoff.py` lists that path.
2. **Rule**: Every flag a skill writes on a line that runs a script is one that script takes.
   **Proof**: Each `--flag` on a line of a `SKILL.md` naming a `scripts/**/*.py` is in that
   script's `--help` or its source; the same check on a copy of the test skill passing
   `--remote` to `purlin_run.py` lists `--remote`.
3. **Rule**: The answers file the sign skill shows is one `purlin:sign --answers` walks without a
   refusal about the file.
   **Proof**: The JSON block under `Step 5` of `skills/sign/SKILL.md`, written to
   `.purlin/runtime/signoff-answers.json` in a project whose hand checks are
   `accession_screen RULE-1` and `sample_age RULE-6`, is walked with `--answers`; it exits 0 and
   the sign-off holds the note `the tube is red`.
4. **Rule**: No skill, agent definition or reference names a path under `dev/`, `/dev/null` aside.
   **Proof**: No line of `skills/*/SKILL.md`, `agents/purlin.md` or `references/**/*.md` holds
   `dev/` once every `/dev/null` is set aside; the same check on a copy of the build skill naming
   `dev/test_x.py` lists that line.

The wording command the build skill runs (`wording.py`) is better given one rule in `drift`, its
home, than here: it prints one line per comment, then `<n> test comments to correct.` or
`No test comment to correct.`, and exits 0.
