# Decision 122: what the real-skills check found; the build plan

Written by the planning agent on 2026-10-01, read only, against local `main` at `8d55f7010`
(`purlin: evidence at 9a44727`) while an audit run was in progress there: 39 specs, 433 rules,
910 proofs, the last sweep at 906 passed and 9 skipped. Every file, function, rule id and count
below was read in that tree. Nothing was run in the repository. Two things were run outside it,
in a scratch folder: the transcripts of the QA check were unpacked and read, and one signed
commit was made with a `gpg.ssh.program` that signs with another key (section 2.6).

Sources: decision 122's direction for findings 1 to 13 and 17; the owner's second instruction,
"Don't track any costs or number of calls"; the QA report `qa-real-skills.md` and its
transcripts on `origin/qa/0.10.0-report`.

## 0. What changes, in eight sentences

1. **Names.** A spec's name holds letters, digits, `_` and `-`. The test comment, the upgrade
   from 0.9.5 and `purlin:anchor add --name` read the same name. A name with any other
   character is warned of, with the `git mv` that fixes it.
2. **Hand checks.** A rule checked by hand alone reads `checked at sign-off` until a sign-off
   that counts notes it, and is counted neither as passing nor as failing. A note written on
   other wording says so, on the status, the dashboard and at the stop.
3. **Setup.** `purlin:init --yes` commits setup's files whenever they are on disk and not
   committed, whichever run wrote them.
4. **A collision.** `renumber.py` resolves the conflict git left in a spec, where both sides
   only added lines, then renumbers, in one run. Drift says when a merge is not finished.
5. **The status and drift have a script each**, and the skills name the tool as a session
   lists it. The tools refuse Purlin's own folder.
6. **The sign-off.** A missing tag no longer reads `not signed` where the sign-off files
   count. The key that signed is read from the commit. The answers file signs only with the
   signer's address typed in it.
7. **Confirmations.** Renumbering, the `tests` setting and the sign-off do nothing by default:
   each needs a typed answer or a flag.
8. **No cost and no call count.** The audit prints neither and records neither.

Decision 44 binds: what goes is deleted outright with its tests. No compatibility reader.

## 1. The count

| | Now | Added | Deleted | Reworded | After |
|---|---|---|---|---|---|
| Specs | 39 | 0 | 0 | 18 touched | 39 |
| Rules | 433 | 15 | 1 | 30 | 447 |
| Proofs | 910 | 53 | 1 | 16 | 962 |

The numbers assumed are each spec's `> Highest-*` on `main` at `8d55f7010`:

| Spec | Highest-Rule now, after | Highest-Proof now, after | Rules added | Rules reworded | Proofs added | Proofs reworded |
|---|---|---|---|---|---|---|
| `schema_spec_format` | 42, 43 | 87, 91 | 43 | 7 | 88 to 91 | |
| `reports` | 39, 39 | 123, 125 | | 1, 36 | 124, 125 | |
| `upstream` | 41, 41 | 64, 65 | | | 65 | |
| `update` | 56, 56 | 167, 168 | | | 168 | |
| `scaffold` | 83, 83 | 173, 176 | | 67, 70 | 174 to 176 | |
| `renumber` | 10, 13 | 14, 21 | 11, 12, 13 | 9 | 15 to 21 | 12 |
| `drift` | 43, 45 | 88, 90 | 44, 45 | | 89, 90 | 49 |
| `server` | 37, 41 | 169, 177 | 38, 39, 40, 41 | 7 | 170 to 177 | 168 |
| `run_script` | 106, 107 | 286, 289 | 107 | 102 | 287 to 289 | |
| `evidence_writer` | 33, 33 | 98, 98 | | 30 | | 21 |
| `ai_audit` | 45, 45 | 124, 124 | | | | |
| `signatures` | 135, 136 | 268, 275 | 136 | 50, 111, 126, 127, 129, 130 | 269 to 275 | 221, 232, 251, 264 |
| `package` | 37, 37 | 81, 83 | | 11, 29 | 82, 83 | |
| `states` | 126, 127 | 294, 299 | 127 | 23, 27, 59, 81, 109, 121 | 295 to 299 | 31, 264, 294 |
| `summary` | 24, 25 | 57, 60 | 25 | 20, 22 | 58 to 60 | |
| `purlin_report` | 78, 78 | 243, 247 | | 8, 9, 44, 71 | 244 to 247 | 8, 40, 167, 243 |
| `purlin_agent` | 23, 24 | 54, 55 | 24 | | 55 | |
| `skill_drift` | 15, 15 | 46, 46 | | 15 | | 46 |

`ai_audit` loses RULE-45 and PROOF-121. Its `> Highest-*` lines stay: a number is never used
again.

**Against the QA report's findings.**

| Finding | Here |
|---|---|
| 1, a hyphen in a name | `-` is allowed in the test comment. 0.9.5's pytest mark took any string as its feature, so a project being upgraded may hold such names; refusing them would strand it (section 2.1) |
| 2a, an old note on new wording | built: `states` RULE-127, `signatures` RULE-129 |
| 2b, one reworded rule ends the whole feature | not built: not a small change. The docs say it plainly. Question 1 |
| 3, setup commits nothing | `--yes` commits what is on disk and not committed: `scaffold` RULE-70 |
| 4, the conflict needs a hand edit | `renumber.py` resolves it: `renumber` RULE-12, 13; drift RULE-44, 45 |
| 5, the tools are not found | a script each, and the tool's full name in the skills: `server` RULE-39 to 41, `purlin_agent` RULE-24 |
| 6, pointed at the plugin | `server` RULE-7, RULE-38 |
| 7, the tag is missing after a pull | the sign-off files answer: `signatures` RULE-130 |
| 8, where a tag goes | the skill shows it and checks the saved spec; the warning says why: `schema_spec_format` RULE-43, `server` RULE-41 |
| 9, an unchecked hand check reads `passed` | `states` RULE-109, `summary` RULE-22, 25 |
| 10, confirmations skipped | three move into a script (section 2.8); the rest are marked `Stop and ask` |
| 11, a plain request | every skill's `description` is rewritten (section 6.9); the docs say to name the command |
| 12, the key recorded | `signatures` RULE-136. The report's `git log --format=%GF` prints nothing in a checkout with no allowed-signers file; the key is read with `ssh-keygen` instead (section 2.6) |
| 13, no status after `Nothing to run` | **already holds.** `purlin_run._nothing_to_run` prints the status, `run_script` RULE-100 says so and PROOF-95 proves it. The transcript `d5-test` shows the status printed; the session rewrote it as a table. Fixed in the skill's words only |
| 16, `9 of 9` against `9 of 10` | one count: `states` RULE-121, `package` RULE-29 |
| 16, the project named `remote` | no code. The name is read from a manifest first; the docs say so (section 6.10) |
| 16, `PASSING` counts the hand check | with 9 |
| 17, an anchor saved unseen | the anchor skill prints and asks (section 6.8) |
| 18, `__pycache__/` | in the block setup writes: `scaffold` RULE-67 |
| 14, 15, and 18's other two notes | left out (section 10) |

## 2. What each finding becomes

### 2.1 A spec's name (finding 1)

`specs.py` takes a name from the file name, any characters. `markers._BODY_RE` reads
`(?P<feature>\w+)`. So `sample-age` is a spec and can never be tied to a test.

0.9.5 marked a test with `@pytest.mark.proof("my_feature", "PROOF-1", "RULE-1")`: the feature
is a string, any string. `update.py` reads those marks with `\w+` too, so the upgrade would
leave a hyphenated project's marks unread. Refusing `-` strands those projects. Allowing it
strands nobody.

- **The one place** is `references/formats/spec_format.md`, "Location": a name holds letters,
  digits, `_` and `-`, and does not start with `-`. `marker_format.md`, the spec skill, the
  anchor skill and the agent definition point there.
- **One pattern**, `specs.NAME = r'\w[\w-]*'`, read by the marker reader, the near-miss check,
  `upstream.py`'s `--name` and `update.py`'s five 0.9.5 patterns.
- **A name with any other character** is still read, so nothing vanishes, and is warned of in
  one line with the `git mv` that renames it. The spec skill checks a saved spec and reports
  that line (2.5).
- **The near miss names the cause.** A comment whose feature holds another character has no
  fix, and its `why` says what a name holds.
- `renumber.py` already escapes the name; `sync_status`, drift and the evidence paths take it
  as it is. No change there.

### 2.2 A hand check (findings 2a, 9, 16)

Today `states._passed_cell` reads a rule whose every proof is `@manual` as `passed`, current
and counted, whatever happened. That is why the reworded RULE-7 was the one rule still passing.

**The words.**

| The rule | Passed cell | Strong cell |
|---|---|---|
| every proof `@manual`, no sign-off has noted it | `checked at sign-off`, reason `no sign-off has checked it yet` | `checked at sign-off` |
| every proof `@manual`, noted by a sign-off that counts, on the wording as it is | `passed`, reason the note's line | `checked at sign-off`, the note's line |
| every proof `@manual`, noted, and the rule or the proof reworded since | `checked at sign-off`, reasons `the rule's wording changed since its last note`, then the note's line | the same |
| a `@manual` proof beside tested proofs | as its tests make it | `checked at sign-off`, with the same reasons, unless the audit reads `weak`, `spot-checked` or `out of date` |

**What `Tests: met` requires**, as `summary` RULE-25: every rule that has a test passes it on
the committed evidence. A rule reading `checked at sign-off` in its passed cell is counted
under no kind of work and never stops `met`. Otherwise no project with a hand check could
reach the sign-off (decision 108).

**The counts.** The sentence reads `10 rules. 9 pass their tests. 1 is checked at sign-off.`
The `Tests` cell reads `9 of 10 · 1 by hand`. The `Passing` box reads `9`, in the pass tone
once every rule passes or is checked at sign-off. The walk's overview reads
`10 rules on Linux/Unix: 9 pass their tests, 1 has a hand check.`

**One denominator for the audit** (finding 16): the rules that pass their tests and have a
tested proof, which is what `summary.audit_counts` counts and `ai_audit` RULE-35 says. The
status's `Strong` cell, the dashboard's `Strong` cell and box, and the package's `audit` take
it. Today the table divides by every rule and the package counts a hand check as
`not_audited`.

**Whether a note is on today's wording** needs no new field. A sign-off names its version, and
`HEAD` holds that version's package, which holds each rule's `text` and each proof's `text`.
`signatures.hand_notes` compares them with the spec as it is, white space runs read as one
space. It reads the rule's text and the text of each of its `@manual` proofs.

**The run's own word.** `scripts/run/evidence.py`, `rule_word`, writes `passed` for a rule
whose proofs are all `@manual`. It writes `checked at sign-off`. The package reads that word
whatever the section holds, so no old section misleads it.

### 2.3 Rewording one rule ends the whole feature (finding 2b): not built

A section stores one `spec` hash over every rule and proof line of the spec
(`fingerprint.spec_hash`). To end only the changed rule:

- `fingerprint.py`: a hash per rule, over its line and its proofs' lines;
- `scripts/run/evidence.py`: the section stores them, and `_same_observation` compares them;
- `scripts/mcp/purlin/evidence.py`: `checked_sections` names the rules out of date, not only
  the parts;
- `states._passed_cell`, `payload.py`, `package._results`, `purlin_run.keep_slow_results`;
- `evidence_format.md` to version 13; about 6 rules and 12 proofs in four specs.

That is a lane of its own, and it changes less than it seems. The next `purlin:test` still
runs every test file that carries the feature's comments, so every rule gets a new result
anyway. The sign-off still asks for `purlin:test --all --commit` after any change to a spec.
The only difference is what the status says between the edit and the next run:
`1 rule to test` in place of `10 rules to test`.

This plan does not build it. The docs say so plainly (section 6.10). Question 1 puts it to the
owner.

### 2.4 Setup's commit (finding 3)

`scaffold.main` commits `plan.files`, the files this run wrote. A second run writes none, so
`--yes` commits nothing. It commits setup's own files that git does not ignore and does not
hold as they stand: `.purlin/config.json`, `.gitignore` and `.purlin/evidence/README.md`,
written by this run or kept from an earlier one. The question is asked while there is such a
file. A `.gitignore` the project already tracked is committed whole, with the block setup
added; the printed list names it.

### 2.5 A saved spec is checked (finding 8)

- The spec skill shows a tag at the end of the proof line, with two examples.
- After it saves, it runs `purlin_status.py --spec <name>` and reports each mistake before it
  says `Spec saved`.
- `specs.spec_mistakes` prints an unread proof line whole. `PROOF_LINE_SHOWN` cut it at 60
  characters, mid-word. The line gives one of two reasons: a tag stands before the rule ids, or
  the line is not `- PROOF-N (RULE-N): <text>`.

### 2.6 The sign-off (findings 7, 10, 12)

**The tag is a pointer** (finding 7). A sign-off counts when the commit that added its file is
signed and verifies, and its `package_hash` matches the package `HEAD` holds
(`signatures.load_signoffs`). None of that reads a tag. So where this checkout holds no
`signed/<version>` tag at all, and `HEAD` holds that version's package and a sign-off of it
that counts, the status reads `signed <version>`, at the commit that added the first such
sign-off, and prints one line naming `git fetch --tags`.

This keeps decision 121's rule: the status reads `signed` only where a sign-off counts. What
121 added stays: a tag that names a commit with no package is passed over with its warning,
and so is a tag whose sign-off does not count.

**The key that signed** (finding 12). Checked in a scratch repository, git 2.x on macOS: a
commit made with `user.signingkey` naming key A and `gpg.ssh.program` set to a script that
signs with key B carries B's signature. `git log --format=%GF` printed nothing and
`gpg.ssh.allowedSignersFile needs to be configured`. `ssh-keygen -Y check-novalidate -n git
-s <signature>` over the commit's payload printed
`Good "git" signature with ED25519 key SHA256:WAMalB/...`, B's fingerprint. `signatures.py`
already runs that command to verify (`_verifies`); it now reads the fingerprint from it.

After the sign-off's commit, `sign._sign` compares that fingerprint with
`signatures.key_fingerprint`. On a difference it moves the branch back to the commit it stood
at, restores the files, writes no tag, prints one line and exits 1.

**The last question** (finding 10). `--answers` signs only where `sign` holds the signer's
address, as the question names it. `true`, `yes` and another address sign nothing. The walk
at a terminal asks `[y/N]` itself, as now.

### 2.7 The tools and their scripts (findings 5, 6)

- **Two scripts**, `scripts/run/purlin_status.py` and `scripts/run/purlin_drift.py`. Each
  takes `--project-root`, answers what the tool answers, and refuses as the tool refuses.
  `purlin_status.py --spec <name>` prints only that spec's mistakes.
- **One refusal**, `project.refusal(project_root, started_in)`, used by the server and both
  scripts: no `.purlin/config.json`, or Purlin's own folder.
- **Purlin's own folder** is the folder two levels above `scripts/mcp`, compared by real path.
  A root that is that folder, or under it, is refused unless the server, or the script, was
  started in it, under it, or in another checkout of the same repository (the same
  `git rev-parse --git-common-dir`). So this repository still reads its own status: from its
  checkout when the plugin is loaded from it, and from a worktree of it. A session in any other
  project is refused. A plugin installed from the marketplace is a copy with no shared git
  folder, so no session's project is ever in it.
- **The skills** name `mcp__plugin_purlin_purlin__sync_status` and
  `mcp__plugin_purlin_purlin__drift`, say to load a deferred tool with ToolSearch, and give
  the script as the fallback. The status skill says never to read `.purlin/report-data.js` as
  the status.

### 2.8 Every confirmation, and where it lives

No script can know that a person said yes. What a script can do is nothing by default: it asks
on its input, takes the end of input as no, and goes on only with a typed answer or a named
flag. A model that skips the question must then pass the flag itself, and the transcript shows
it.

| Skill | Confirmation | Protects | After this round |
|---|---|---|---|
| `init` | `Commit the files setup wrote? [y/N]` | the project's history | in `scaffold.py`, as now; `--yes` |
| `init --update` | each migration, and `Remove <path>? [y/N]` | the project's files | in `update.py`, as now |
| `spec` | the drafted rules, before saving | what the spec says | skill text, `Stop and ask`: no script writes a spec |
| `spec` | `Do it? [y/N]` before renumbering | spec lines and test comments | **in `renumber.py`**; `--yes` |
| `spec` | which side of a conflicting line survives | a person's rule | skill text, `Stop and ask`; the script leaves that conflict and names it |
| `spec-from-code` | the list of features, before any spec | the specs written | skill text, `Stop and ask` |
| `build`, `spec-from-code` | a marker added above an existing test | which test shows a proof | skill text; a wrong one shows in the diff |
| `build` | a near-miss comment's fix | a test comment | skill text; `markers.py` only lists |
| `build`, `test` | the `tests` setting | what command a run starts | **in `purlin_run.py`**; `--write-tests`. A command of the person's own is still written with the `purlin_config` tool, after `Stop and ask` |
| `test` | starting the project's run on another system | a push | skill text, `Stop and ask` |
| `test` | writing that run's setup files, and committing them | the project's files | skill text, `Stop and ask` |
| `sign` | each hand check's note | the record of what was seen | in `sign.py`: a stop with no answer refuses. That the words are the person's is skill text, `Stop and ask` |
| `sign` | the last question | the signature | **in `sign.py`**: the signer's address, typed |
| `sign` | running the command a refusal names | commits of evidence | skill text, `Stop and ask` |
| `sign` | deleting a tag; running the key commands; writing `VERSION` | the repository | skill text, `Stop and ask` |
| `sign`, every skill | pushing | the host | never done: the agent definition's third NEVER |
| `anchor` | the drafted rules, before saving | what the anchor says | skill text, `Stop and ask` (new) |
| `audit`, `drift`, `status` | none | | |

`Stop and ask` is one mark, the same in every skill: the agent prints the question, ends its
turn and acts only on the person's answer.

### 2.9 No cost and no call count

- `audit_run.CALLS_ONE`, `CALLS_MANY`, `COST`, `EXPERIMENTAL`, `RUNTIME_PATH` and
  `write_costs` go. Nothing else reads `.purlin/runtime/audit_run.json`, so the file goes.
- `ai_audit._cost`, `cost_usd`, `seconds` and `spent` go, from `ask_model`, `_call`,
  `audit_one` and `audit_all`. `dev/fake_claude.py` loses `cost`.
- `ai_audit` RULE-45 and PROOF-121 go, with the test.
- The call is untouched: `ai_audit.COMMAND`, `SYSTEM_PROMPT`, one call per rule, four at once.
- Every sentence that names a cost or a count of calls goes (section 6.7).

"One model call for the rule" stays where a page lists the audit's steps: it says how the
audit works and counts nothing. Question 2 asks whether that reading is right.

## 3. The specs, word for word

Each lane writes the rules and proofs of the specs it owns, spec first. A reworded rule or
proof keeps its number. `as now` means the words on `main` stand.

### `schema_spec_format` (lane `setup`)

`> Highest-Rule: 43`, `> Highest-Proof: 91`.

- RULE-7: The file name is the spec's name, whatever its first line says, and a name holds letters, digits, `_` and `-` and does not start with `-`; a spec whose name holds any other character is still read, and warned of in one line naming the `git mv` that renames its file
- RULE-43: A list item under `## Proof` that cannot be read is quoted whole in its warning, with the reason: a tag standing before the rule ids goes at the end of the line, and any other line is not `- PROOF-N (RULE-N): <text>`

- PROOF-88 (RULE-7): A project holding `specs/intake/sample.age.md` is reported with `sample.age: the name holds a character other than letters, digits, _ and -, so no test comment can name it. Rename the file: git mv specs/intake/sample.age.md specs/intake/sample_age.md`
- PROOF-89 (RULE-7): A spec at `specs/intake/sample-age.md` holding one rule is read as the feature `sample-age`, and the status carries no warning naming it
- PROOF-90 (RULE-43): `login`'s proofs hold `- PROOF-7 @manual (RULE-7): A rejection message for an aged sample is clear to a technician`; the status carries `login: a line under ## Proof cannot be read, because a tag goes at the end of the line: "- PROOF-7 @manual (RULE-7): A rejection message for an aged sample is clear to a technician". Run purlin:spec login.`
- PROOF-91 (RULE-43): `login`'s proofs hold `- PROOF-7: no rule named`; the status carries ``login: a line under ## Proof cannot be read, because a proof line reads `- PROOF-N (RULE-N): <text>`: "- PROOF-7: no rule named". Run purlin:spec login.``

### `reports` (lane `setup`)

`> Highest-Proof: 125`.

- RULE-1: A marker is one whole-line comment, `purlin: <feature> PROOF-<n>` or `purlin: <feature> RULE-<n>`, the feature any name a spec may hold, after any of `#`, `//`, `--`, `;`, `%` and `'`, or inside a one-line `/* */` or `<!-- -->`; a `purlin:` comment of any other shape ties nothing
- RULE-36: as now, with this clause before `a marker naming what a spec has`: `a comment whose feature holds a character no spec's name may hold has no fix, and its why names the characters a name holds;`

- PROOF-124 (RULE-1): `specs/intake/sample-age.md` has `PROOF-1`, and `tests/test_age.py` holds `# purlin: sample-age PROOF-1` above the passing `test_age`; the run prints `Markers: 1 tied to a test, 0 not tied.`, and the evidence lists `PROOF-1` as `pass`
- PROOF-125 (RULE-36): A test file carrying `# purlin: sample.age PROOF-1` is listed with no fix, and its why reads `` `sample.age` holds a character a spec's name cannot: a name holds letters, digits, `_` and `-`. ``

### `upstream`, `update` (lane `setup`)

`upstream`, `> Highest-Proof: 65`:

- PROOF-65 (RULE-22): The published anchor is added with `--name sample-age`; it exits 0, and `specs/_anchors/sample-age.md` holds its rules

`update`, `> Highest-Proof: 168`:

- PROOF-168 (RULE-29): A test file carrying the 0.9.5 mark `@pytest.mark.proof("sample-age", "PROOF-1", "RULE-1")` carries after the update with `--yes` `# purlin: sample-age PROOF-1` where the mark was, and the output holds `rewrote 1 marker in tests/test_age.py as comments`

### `scaffold` (lane `setup`)

`> Highest-Proof: 176`.

- RULE-67: A new project's `.gitignore` keeps out what a run writes locally: `/purlin-report.html`, `.purlin/runtime/` and `__pycache__/`
- RULE-70: The commit carries only setup's own files that git does not ignore and does not hold as they stand, whether this run wrote them or an earlier one did: a file the project had already staged stays staged and out of it

- PROOF-174 (RULE-70): A git project with no commit yet is set up with nothing to answer from, then set up again with `--yes`; the second run prints `Committed <sha7>, the files setup wrote:`, then `  .purlin/config.json`, `  .gitignore` and `  .purlin/evidence/README.md`, and the project has one commit, `chore(init): set up Purlin`
- PROOF-175 (RULE-70): A project whose one commit holds `README.md` and a `.gitignore` reading `node_modules/` is set up with nothing to answer from, then again with `--yes`; the commit the second run makes holds exactly `.gitignore`, `.purlin/config.json` and `.purlin/evidence/README.md`
- PROOF-176 (RULE-67): A new project set up has a `.gitignore` holding the line `__pycache__/`

### `renumber` (lane `collision`)

`> Highest-Rule: 13`, `> Highest-Proof: 21`. The Description's second sentence reads: `It
first resolves a conflict git left in the spec where both sides only added lines, then plans
the edits to the spec and to the test comments of this checkout, the line not already on the
default branch moving, prints the plan, asks, and makes it only on a yes.`

- RULE-9: A rule that moves takes with it each proof line naming it that is not on the default branch's copy, and a run answered yes makes the edits in the working tree and commits nothing
- RULE-11: A run without `--dry-run` prints the plan, then asks `Do it? [y/N] `: `y`, `yes` or `--yes` makes the edits, and any other answer, an empty one or the end of input changes no file and ends on `Nothing is changed.`
- RULE-12: A conflict git left in the spec, whose two sides only add rule lines, proof lines or `> Highest-` lines, is resolved in the same plan and the same run, before the renumbering: both sides' lines are kept, a line both sides hold once, and of two `> Highest-` lines of one kind the higher stays
- RULE-13: A conflict in which a side changes or removes a line of the version both sides started from, or holds any other kind of line, or for which git holds no such version, is left as it is and named with its line and why

- PROOF-12 (RULE-9): After the merge of PROOF-2, a run with `--yes` ends `Renumbered in login: 1 spec line and 1 test comment. Nothing is committed.`; HEAD names the commit it named before, and git lists the spec and `tests/test_b.py` as changed and not committed
- PROOF-15 (RULE-11): After the merge of PROOF-2, a run with neither `--dry-run` nor `--yes` and nothing to answer from prints the plan, then `Do it? [y/N] `, ends `Nothing is changed.`, exits 0, and the spec and every test file read byte for byte as before
- PROOF-16 (RULE-11): After the merge of PROOF-2, a run answered `y` on its input ends `Renumbered in login: 1 spec line and 1 test comment. Nothing is committed.`
- PROOF-17 (RULE-12): `main` and the branch `qa/login` each add a `RULE-9` line to `login`, `A` and `B`, and the merge stops on them at line 20; the dry run prints `login: the conflict at line 20 keeps both sides: 1 line from HEAD and 1 from qa/login.`, and after a run with `--yes` the spec holds no conflict line, `RULE-9: A` and `RULE-10: B`
- PROOF-18 (RULE-12): The same merge leaves `> Highest-Proof: 9` on `HEAD`'s side of a conflict at line 6 and `> Highest-Proof: 10` on the branch's; the dry run prints `login: the conflict at line 6 takes > Highest-Proof: 10, the higher of 9 and 10.`, and after a run with `--yes` the spec holds one `> Highest-Proof:` line
- PROOF-19 (RULE-12): A merge leaves one conflict in `login`, each side adding a proof under a number of its own; a run with `--yes` ends `Resolved 1 conflict in login. Nothing is committed.`, the spec holds both proofs and no conflict line, and git still lists the spec as not merged
- PROOF-20 (RULE-13): `main` rewords `RULE-2` to `A2` and the branch to `B2`, and the merge stops on that line at line 18; the plan prints `login: the conflict at line 18 is left: both sides changed RULE-2. Resolve it by hand, then run purlin:spec login again.`, and after a run with `--yes` those lines read as before
- PROOF-21 (RULE-13): A conflict at line 3 of `login` holds a `> Description:` line on each side; the plan prints `login: the conflict at line 3 is left: it holds a line that is not a rule, a proof or a > Highest- line. Resolve it by hand, then run purlin:spec login again.`

### `drift` (lane `collision`)

`> Highest-Rule: 45`, `> Highest-Proof: 90`.

- RULE-44: While a merge is in progress and not committed, the view's second line says so and what to do, and `merge_in_progress` is true
- RULE-45: Where a rule written twice moves, the view names each proof that follows it to the new number

- PROOF-49 (RULE-42): After a pull, the view carries exactly `anchors_behind`, `comments_changed`, `default_branch`, `lines`, `merge_in_progress`, `numbers_twice`, `proofs_added`, `proofs_changed`, `proofs_moved`, `rules_added`, `rules_changed` and `rules_removed`
- PROOF-89 (RULE-44): A merge of a branch stops on a conflict in `specs/auth/login.md` and is not committed; the view's second line reads `A merge is in progress and is not committed, so the range above stops before it. Resolve it and commit, then run purlin:drift again.`, and `merge_in_progress` is true
- PROOF-90 (RULE-45): After a merge, `login` writes `RULE-2` twice, the branch's with its proof `PROOF-3`; the view holds, directly after the line naming `RULE-2`, `login: PROOF-3 will name RULE-3.`

### `server` (lane `run`)

`> Scope:` gains `scripts/mcp/purlin/project.py`, `scripts/run/purlin_status.py` and
`scripts/run/purlin_drift.py`. `> Highest-Rule: 41`, `> Highest-Proof: 177`. The Description
gains: `A script prints the status and another the drift report, for a session that does not
have the tools.`

- RULE-7: A tool called on a root holding no `.purlin/config.json` answers only `No Purlin project root at <root>: .purlin/config.json is not there. Run purlin:init.`, one whose settings file cannot be read answers only what is wrong and what to do, and neither reports or writes anything there
- RULE-38: A tool called on the plugin's own folder, or a folder under it, is refused with one line and reports nothing, unless the server was started in that folder, under it, or in another checkout of the same repository
- RULE-39: `scripts/run/purlin_status.py --project-root <dir>` prints the status the `sync_status` tool answers for that folder and exits 0, and where the tool would refuse it prints only that refusal and exits 1
- RULE-40: `scripts/run/purlin_drift.py --project-root <dir>` prints the lines of the view the `drift` tool answers, one per line, takes `--since` as the tool does, and refuses as the tool refuses
- RULE-41: `purlin_status.py --spec <name>` prints only the warnings that name that spec and exits 1, or one line counting its rules and proofs and saying no mistake was found, and exits 0

- PROOF-168 (RULE-7): A client calls `sync_status` with `project_root` naming an empty folder; the answer is exactly `No Purlin project root at <that folder>: .purlin/config.json is not there. Run purlin:init.`
- PROOF-170 (RULE-38): A copy of the plugin holds `.purlin/config.json` and the spec `login`; its server is started in another workspace, and a client calls `sync_status` naming the copy; the answer is exactly `<the copy> is Purlin's own folder, not your project. Pass the top folder of the git checkout you are working in.`
- PROOF-171 (RULE-38): That copy's server is started in the copy, and a client calls `sync_status` naming the copy; the answer opens `Purlin status:` and names `login`
- PROOF-172 (RULE-38): That copy is a git repository with a second checkout made by `git worktree add`; its server is started in the second checkout, and a client calls `sync_status` naming the copy; the answer opens `Purlin status:` and names `login`
- PROOF-173 (RULE-39): In a project with the spec `login`, `purlin_status.py --project-root <dir>` prints exactly the text `sync_status` answers for that folder, and exits 0
- PROOF-174 (RULE-39): In an empty folder, `purlin_status.py --project-root <dir>` prints only `No Purlin project root at <dir>: .purlin/config.json is not there. Run purlin:init.` and exits 1
- PROOF-175 (RULE-41): `login` carries `> Requires: api`; `purlin_status.py --project-root <dir> --spec login` prints only `login: > Requires: is not read, because every anchor covers the whole project. Run purlin:spec login.` and exits 1
- PROOF-176 (RULE-41): `login` holds 2 rules and 3 proofs and no mistake; `purlin_status.py --project-root <dir> --spec login` prints only `login: 2 rules and 3 proofs read. No mistake found.` and exits 0
- PROOF-177 (RULE-40): After a pull that adds `RULE-3` to `login`, `purlin_drift.py --project-root <dir>` prints the line naming the range, then `1 rule added: login RULE-3.`, and exits 0

### `run_script` (lane `run`)

`> Highest-Rule: 107`, `> Highest-Proof: 289`.

- RULE-102: as now, its opening reading `With the `tests` setting empty the run prints `No test command is set`` and, in place of `the run writes nothing and exits 1`, ending `and unless the question of RULE-107 is answered yes it writes nothing and exits 1`
- RULE-107: After a suggested `tests` setting the run asks `Write this tests setting to .purlin/config.json? [y/N] `: `y`, `yes` or `--write-tests` writes the suggested entries as the `tests` setting, prints `Wrote the tests setting to .purlin/config.json.` and runs the tests; any other answer, an empty one or the end of input writes nothing

- PROOF-287 (RULE-107): In a project whose `tests` setting is empty and that holds a `conftest.py` and one marked passing test, `--all --test` with nothing to answer from prints `Write this tests setting to .purlin/config.json? [y/N] ` last, leaves `.purlin/config.json` byte for byte as it was, and exits 1
- PROOF-288 (RULE-107): That project run as `--all --test --write-tests` prints no question, prints `Wrote the tests setting to .purlin/config.json.` and then `Markers: 1 tied to a test, 0 not tied.`; `tests` holds pytest's entry alone, and it exits 0
- PROOF-289 (RULE-107): That project run as `--all --test` and answered `y` on its input writes pytest's entry as the `tests` setting, runs the test and exits 0

Finding 13 adds nothing here: RULE-100 and PROOF-95 hold it.

### `evidence_writer` (lane `run`)

- RULE-30: A rule whose proofs are all `@manual` reads `checked at sign-off` in a run's section, because no run was ever going to observe one, and a `@manual` proof beside a proof whose test failed leaves the rule `failed`
- PROOF-21 (RULE-30): A run in which a rule's one proof is `@manual` and tied to no test writes a section reading the rule `checked at sign-off`

### `ai_audit` (lane `run`)

RULE-45 and PROOF-121 are deleted, with the test
`test_the_calls_are_counted_first_and_their_cost_printed_after`. No other line changes.

### `signatures` (lane `signoff`)

`> Highest-Rule: 136`, `> Highest-Proof: 275`.

- RULE-50: A sign-off records the signer's email as git holds it, git's `user.name` as the signer's name, and the fingerprint of the key that signed its commit
- RULE-111: `--answers FILE` walks with the answers the file gives, printing each after its question, refuses with nothing written when a stop has no answer, and signs only where the file's `sign` holds the signer's email address, as the last question names it
- RULE-126: A hand check's stop shows the rule, each proof with its tag and the tests tied to it, the results on each system with any proof that found nothing to check and its reason, or `No test runs for this rule: you check it here.` where its every proof is `@manual`, the audit's findings where it found the rule weak, and asks what the person saw
- RULE-127: as now, its middle reading `then an overview counting per system the rules that pass their tests, a rule checked by hand alone not among them, and the hand checks`
- RULE-129: as now, with this clause before `where no sign-off has noted the rule`: `where the rule's or the proof's wording changed since that note, one line saying so stands above it;`
- RULE-130: The sign-off reads `signed <version>` only where a sign-off of that version counts and either `signed/<version>` names a commit holding its package, or this checkout holds no tag of that name, where it is read at the commit that added the sign-off, with one line naming `git fetch --tags`; a tag that names no such commit is passed over, with one warning naming the tag and why
- RULE-136: After the sign-off's commit is made the command reads the key that signed it, and where that is not the key `user.signingkey` names it takes the commit back, writes no tag, exits 1 and prints one line naming both keys and the usual cause

- PROOF-221 (RULE-111): With `login RULE-2` a hand check and an answers file giving it `note` with `the lockout page read 401` and `sign` holding `jane@acme.com`, the signer's address, `--answers` prints that note after the stop's question, exits 0, and the sign-off carries that note
- PROOF-232 (RULE-127): Over 19 rules on Linux/Unix, 18 that pass their tests and 1 checked by hand alone, with 17 audited strong and 1 weak, the overview prints `  19 rules on Linux/Unix: 18 pass their tests, 1 has a hand check.` and `  The audit: 17 strong, 1 weak.`
- PROOF-251 (RULE-129): Before any sign-off, `--show` ends the stop of `login RULE-2`, whose one proof is `@manual`, on `Results` and `  No test runs for this rule: you check it here.`, with no line `Last note`
- PROOF-264 (RULE-111): An answers file gives `login RULE-2` a note and holds `"sign": true`; `--answers .purlin/runtime/signoff-answers.json` ends `Nothing was signed: "sign" in .purlin/runtime/signoff-answers.json must hold jane@acme.com, typed by the person signing.`, exits 0 and adds no commit and no file
- PROOF-269 (RULE-136): `user.signingkey` names Quinn's key, and `gpg.ssh.program` names a program that signs with another key; the walk answered yes prints one line beginning `No sign-off: the commit was signed with the key ending ...` and naming the last 4 characters of both keys, exits 1, `HEAD` names the commit it named before, and no `signed/2.1.0` exists
- PROOF-270 (RULE-136): After that refusal the checkout holds no sign-off file and no package file for `2.1.0`, and `git status --porcelain` prints nothing
- PROOF-271 (RULE-111): An answers file holds `"sign": "quinn@acme.com"` where the signer is `jane@acme.com`; `--answers` ends on the `Nothing was signed:` line naming `jane@acme.com`, and adds no commit and no file
- PROOF-272 (RULE-129): Quinn signs `0.1.0` with a note at the hand check `login RULE-2`; `RULE-2`'s text is then reworded and committed with new results; `--show --version 0.2.0` prints under `Last note` first `  The rule's wording changed since this note.`, then the note's line
- PROOF-273 (RULE-129): After the same sign-off the `@manual` proof of `login RULE-2` is reworded, the rule left as it was, and new results committed; the stop prints under `Last note` first `  The proof's wording changed since this note.`
- PROOF-274 (RULE-130): Quinn signs `0.1.0`, and the tag `signed/0.1.0` is then deleted from the checkout, as a pull that fetched no tag leaves it; the sign-off reads `signed 0.1.0 at <sha7>`, the sign-off's commit, and the warnings hold one line starting `signed/0.1.0 is not in this checkout:` and ending `Run git fetch --tags, or purlin:sign if no one wrote the tag.`
- PROOF-275 (RULE-130): With that tag deleted, a commit made with no signature then changes the sign-off file's note; the sign-off reads `not signed`

### `package` (lane `signoff`)

`> Highest-Proof: 83`.

- RULE-11: Each rule carries each result with its operating system, source, time, commit, runner and machine, and a rule whose every proof is `@manual` reads `checked at sign-off` there, never `passed`
- RULE-29: The package carries `audit`, the five counts `strong`, `weak`, `spot_checked`, `out_of_date` and `not_audited` as `purlin:status` gives them, over the rules that pass their tests and have a tested proof, and `hand_checks`, one entry per rule with a `@manual` proof naming its feature, rule and proofs

- PROOF-82 (RULE-29): 3 rules pass their tests, 2 found `strong` by the audit and 1 never read, and a fourth rule's one proof is `@manual`; the package's `audit` reads `{"strong": 2, "weak": 0, "spot_checked": 0, "out_of_date": 0, "not_audited": 1}`
- PROOF-83 (RULE-11): `login RULE-2`'s one proof is `@manual`, and its feature's committed section reads `RULE-2` `passed`; in the package each result of `RULE-2` reads `checked at sign-off`

### `states` (lane `surfaces`)

`> Highest-Rule: 127`, `> Highest-Proof: 299`.

- RULE-23: A rule's bucket is exactly one of `untested`, `failing`, `partial`, `by_hand` and `passed`: `failing` where its passed cell reads `failed`, `partial` where it reads `partial`, `by_hand` where it reads `checked at sign-off`, `passed` where it reads `passed`, and `untested` where it reads any other word, a rule no proof line names included
- RULE-27: as now, with `schema version 16`
- RULE-59: `signoff` carries `word`, `version`, `commit` and `since` for the newest version whose sign-off counts, found by its `signed/*` tag on HEAD or an ancestor of it, or by its sign-off files where this checkout holds no such tag, numbered versions compared as numbers, `word` reading as the status's `Sign-off:` line does, and `word` reads `not signed` where there is none
- RULE-81: as now, its opening reading `` `summary` carries `steps`, holding `passed` and `by_hand`, `audit` and `sentence`; ``
- RULE-109: A rule whose every proof is `@manual` reads `checked at sign-off` in its passed cell, with the reason `no sign-off has checked it yet`, until a sign-off that counts holds a note for it on the rule's and the proof's wording as they are; then it reads `passed`, with that note as its reason; its strong cell reads `checked at sign-off` throughout
- RULE-121: The status table shows one row per spec under `Spec`, `Rules`, `Proofs` and `Tests`, with `Strong` added where any rule has an audit entry and `Proofs` left out where no spec writes a proof line; `Tests` reads `<passed> of <rules>` and appends `· <k> by hand`, `· <k> partial` and `· <k> failing`; `Strong` reads `<strong> of <n>`, `<n>` the spec's rules that pass their tests and have a tested proof, and is empty where it has none; where the project has an anchor, the anchors' rows stand under the line `Anchors` and every other spec's under `Specs`
- RULE-127: Where the rule's text, or the text of one of its `@manual` proofs, changed since the newest sign-off noted it, each cell reading `checked at sign-off` carries, before the note, `the rule's wording changed since its last note` or `the proof's wording changed since its last note`

- PROOF-31 (RULE-27): as now, with `schema_version` 16
- PROOF-264 (RULE-109): A rule whose one proof is `@manual`, with no test marked, nothing run and no sign-off, reads `checked at sign-off` in its passed cell with the one reason `no sign-off has checked it yet`, `checked at sign-off` in its strong cell, and the bucket `by_hand`
- PROOF-294 (RULE-121): Over a spec of two rules whose tests pass, the audit finds `RULE-2` strong and never reads `RULE-1`, and `RULE-2`'s test then fails; the status report's header still ends with `Strong`, and the spec's `Strong` cell reads `0 of 1`
- PROOF-295 (RULE-109): After `quinn.qa@labconnect.example` signs `0.1.0` at HEAD with the note `the tube is red` on a rule whose one proof is `@manual`, its passed cell reads `passed` with the one reason `noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, at this commit: the tube is red`
- PROOF-296 (RULE-127): A rule checked by hand alone was noted at the sign-off of `0.1.0`, 1 commit ago, and its text was reworded since; its passed cell reads `checked at sign-off` with the reasons `the rule's wording changed since its last note` and then `noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, 1 commit since: the tube is red`
- PROOF-297 (RULE-127): A rule has `PROOF-1` marked `@manual` and `PROOF-2` whose test passes, noted at the sign-off of `0.1.0`, and `PROOF-1` was reworded since; its passed cell reads `passed`, and its strong cell reads `checked at sign-off` with the first reason `the proof's wording changed since its last note`
- PROOF-298 (RULE-121): A spec of 3 rules, 2 that pass their tests and 1 whose one proof is `@manual`, reads `2 of 3 · 1 by hand` in its `Tests` cell
- PROOF-299 (RULE-121): A spec of 10 rules, 9 that pass their tests and are found strong and 1 whose one proof is `@manual`, reads `9 of 9` in its `Strong` cell

### `summary` (lane `surfaces`)

`> Highest-Rule: 25`, `> Highest-Proof: 60`.

- RULE-20: as now, its third line reading `` and `Sign-off: ` followed by, for the newest version whose sign-off counts, found by its `signed/*` tag on HEAD or an ancestor of it or by its sign-off files where this checkout holds no such tag, `` and the rest as now
- RULE-22: The sentence reads `<N> rules. <p> pass their tests.`, `1 rule.` and `1 passes its tests.` for a count of one, then ` <h> are checked at sign-off.`, `1 is checked at sign-off.` for one, where a passed cell reads `checked at sign-off`, counting each rule once under the spec that owns it; where a rule that passes has an audit entry it adds ` The audit found <s> of <n> rules strong (<p>%): <s> strong`, then `, <n> weak`, `, <n> spot-checked`, `, <n> out of date` and `, <n> not audited`, each only where not zero
- RULE-25: A rule whose passed cell reads `checked at sign-off` is counted under no kind of work and not among the rules that pass, so the tests read `met` where every rule that has a test passes it on the committed evidence, whether or not anyone has checked that rule

- PROOF-58 (RULE-22): 10 rules, 9 that pass their tests and 1 whose one proof is `@manual` and that no sign-off has noted, read `10 rules. 9 pass their tests. 1 is checked at sign-off.`
- PROOF-59 (RULE-25): Over those 10 rules on committed evidence, the status's second line reads `Tests: met`, it holds no `Left to do:` line, and its last line reads `Every rule passes its tests on the committed evidence. To sign it: purlin:sign`
- PROOF-60 (RULE-22): 9 rules pass their tests and are found strong, and a tenth has one `@manual` proof; the sentence reads `10 rules. 9 pass their tests. 1 is checked at sign-off. The audit found 9 of 9 rules strong (100%): 9 strong.`

### `purlin_report` (lane `surfaces`)

`> Highest-Proof: 247`.

- RULE-8: as now, with `` `Passing`, counting the rules whose tests pass, with the project's rule count beneath it as `<n> RULES TOTAL`, in the pass tone once every rule passes or reads `checked at sign-off`; and `Strong`, wherever a rule has an audit entry, counting the rules it found strong, in the pass tone once it equals the `<n>` of the `Audit` box ``
- RULE-9: as now, with `` `Tests` `<passed> of <rules>`, then `<k> by hand`, `<k> partial` and `<k> failing`; `Strong` `<s> of <n>`, `<n>` the spec's rules that pass their tests and have a tested proof ``
- RULE-44: as now, its list of statuses ending `` `not run`, `out of date` and `checked at sign-off` ``
- RULE-71: as now, ending `` and above that note, where the rule's or the proof's wording changed since it, `the rule's wording changed since its last note` or `the proof's wording changed since its last note` ``

- PROOF-8 (RULE-8): as now, with `whose 11 rules pass their tests 7 times` and `` `Passing` 7 ``
- PROOF-40 (RULE-9): as now, with `` `Strong` `2 of 3` ``
- PROOF-167 (RULE-55): as now, with `7 rows carry `PASSED``
- PROOF-243 (RULE-9): as now, with `` login's `Strong` cell reads `0 of 1` ``
- PROOF-244 (RULE-15): Open the regulated sample's invoice `RULE-3`, whose one proof is `@manual` and which no sign-off has noted; its passed row reads `CHECKED AT SIGN-OFF` in the neutral tone with the reason `no sign-off has checked it yet`, and its row on the board carries no `PASSED` badge
- PROOF-245 (RULE-9): Open the board with the regulated sample; invoice's `Tests` cell reads `2 of 3 · 1 by hand` and its `Strong` cell `1 of 2`
- PROOF-246 (RULE-71): Open the regulated sample's invoice `RULE-3` after its note of `0.1.0` is marked as written before the rule was reworded; above the note the screen reads `the rule's wording changed since its last note`
- PROOF-247 (RULE-8): Open the board with the regulated sample after every rule but invoice `RULE-3` is given a passing test; the `Passing` box reads `10` in the pass tone

The fixture `regulated.json` holds invoice `RULE-3` with the one proof `PROOF-4`, `@manual`:
its passed word becomes `checked at sign-off`, so `summary.steps` reads `passed` 7 and
`by_hand` 1. The lane reports any other proof whose count that moves.

### `purlin_agent`, `skill_drift` (lane `words`)

`purlin_agent`, `> Highest-Rule: 24`, `> Highest-Proof: 55`:

- RULE-24: Every skill that names `sync_status` names the tool as a session lists it, `mcp__plugin_purlin_purlin__sync_status`, and the script that prints the same status, `scripts/run/purlin_status.py`
- PROOF-55 (RULE-24): Each `SKILL.md` holding `sync_status` holds `mcp__plugin_purlin_purlin__sync_status` and `scripts/run/purlin_status.py`; the same check on a copy of the build skill with the script's line taken out lists `build does not name scripts/run/purlin_status.py`

`skill_drift`:

- RULE-15: The skill names the commands `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:anchor sync` and `git fetch`, and the files `references/drift_criteria.md` and `scripts/run/purlin_drift.py`
- PROOF-46 (RULE-15): The drift skill names `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:anchor sync`, `git fetch`, `references/drift_criteria.md` and `scripts/run/purlin_drift.py`

No rule holds a skill's wording for findings 8, 10, 11 and 17 (decision 112 cut such rules).
The four checks of `dev/skill_checks.py` still hold them in place: every path a skill names
exists, every flag is one its script takes, and the sign skill's answers file is walked.

## 4. The code, by file and function

### 4.1 The reproductions that come first

Each fix starts with its proof's test, written and run before any code changes. The lane
records the failing output in its report.

| Finding | The failing test | What it shows on `main`'s code |
|---|---|---|
| 1 | `reports` PROOF-124 | the comment is not read as a marker: no test is tied, and `PROOF-1` has no `pass` |
| 1, the upgrade | `update` PROOF-168 | the mark is left as it was and no `rewrote` line is printed |
| 2a | `signatures` PROOF-272, `states` PROOF-296 | the note is shown with no line above it; the passed cell reads `passed` |
| 3 | `scaffold` PROOF-174 | the second run prints seven `kept` lines and makes no commit |
| 4 | `renumber` PROOF-17, PROOF-18, and the collaboration test with one collision left as git's conflict | the conflict lines stay, with a stale `> Highest-Proof:` on one side |
| 5 | `server` PROOF-173 | no such script |
| 6 | `server` PROOF-170 | the answer is the copy's status table |
| 7 | `signatures` PROOF-274 | the sign-off reads `not signed` |
| 8 | `schema_spec_format` PROOF-90 | the line is cut after 60 characters and gives no reason |
| 9, 16 | `states` PROOF-264 as reworded, `summary` PROOF-58, `states` PROOF-299 | `passed`; `10 pass their tests`; `9 of 10` |
| 10 | `renumber` PROOF-15; `run_script` PROOF-287; `signatures` PROOF-264 as reworded, seen by the coordinator before the base commit | the run renumbers unasked; no question is printed; `"sign": true` signs |
| 12 | `signatures` PROOF-269 | `Signed 2.1.0 as ... with the key ending ...` naming the configured key, exit 0 |
| 13 | none | already holds |
| 11, 17, and the skill half of 8 and 10 | none: a skill's wording has no test | section 8, step 9 runs the real sessions again |

### 4.2 Lane `setup`

| File, function | Change |
|---|---|
| `scripts/mcp/purlin/specs.py`, `NAME`, `name_ok(name)` (new) | `NAME = r'\w[\w-]*'`; `name_ok` is true where the whole name matches it |
| `specs.py`, `spec_mistakes`, `NAME_REFUSED` (new) | one line per spec whose name `name_ok` refuses, after the `SAME_NAME` lines; the new name is the old with each other character, and a leading `-`, written `_` |
| `specs.py`, `spec_mistakes`, `PROOF_LINE_UNREAD`, `TAG_AT_END`, `NOT_A_PROOF_LINE` (new) | the line is quoted whole; the reason is `TAG_AT_END` where `@manual`, `@slow` or `@env(` stands between `PROOF-N` and `(`, else `NOT_A_PROOF_LINE`; `PROOF_LINE_SHOWN` still cuts the conflict line alone |
| `scripts/mcp/purlin/markers.py`, `_BODY_RE` | the feature is `specs.NAME` |
| `markers.py`, `_LOOSE_BODY_RE`, `near_miss`, `NAME_CHARACTERS` (new) | the loose feature is `\S+`; a feature `specs.name_ok` refuses answers `(None, why)` with `NAME_CHARACTERS` |
| `scripts/anchor/upstream.py`, `_NAME_RE`, `NAME_REFUSED` | the name is `specs.NAME`, matched whole; the line reads `letters, digits, _ and - alone` |
| `scripts/init/update.py`, `PYTEST_ARGS_RE`, `TITLE_TAG_RE`, `TRAIT_RE`, `SHELL_CALL_RE`, `SQL_MARK_RE` | each feature group reads `[\w-]+` |
| `scripts/init/scaffold.py`, `main`, `to_commit` | `to_commit` is handed every file the plan named, kept or written; it answers those git lists as new or changed and does not ignore; the module's docstring says the question is asked `while one of its files is on disk and not committed` |
| `templates/gitignore.purlin` | gains `# Python's bytecode cache, never committed` and `__pycache__/` |

### 4.3 Lane `collision`

| File, function | Change |
|---|---|
| `scripts/spec/renumber.py`, `conflicts(lines, base)` (new) | each conflict as `{start, ours, theirs, labels, kind, why}`; `kind` is `both`, `highest` or `left` (K6); `base` is `git show :1:<spec>`, or None |
| `renumber.py`, `resolve(lines)` (new) | the spec's lines with each `both` and `highest` conflict resolved, each kept line with the number it has on disk |
| `renumber.py`, `plan` | reads the spec, resolves it in memory, parses the result with `specs._parse_spec` and plans the renumbering over it; every line number it prints is the line's on disk; `lines` opens with the conflict lines |
| `renumber.py`, `_moves` | takes the spec's lines in place of reading the file; reads `entry['follows']` from `drift.numbers_twice` |
| `renumber.py`, `apply` | writes the resolved lines, then the edits |
| `renumber.py`, `run`, `main` | `--yes`; without it and without `--dry-run` the run asks `ASK` on its input; `NOT_DONE` on any other answer; `RESOLVED` before `DONE`, or `RESOLVED_ALONE` where nothing is renumbered |
| `scripts/mcp/purlin/drift.py`, `merge_in_progress(project_root)` (new) | true where `git rev-parse -q --verify MERGE_HEAD` answers |
| `drift.py`, `compute_drift`, `VIEW_KEYS`, `MERGE_LINE` | the view gains `merge_in_progress`; `MERGE_LINE` is the view's second line where it is true |
| `drift.py`, `numbers_twice`, `PROOF_WILL_NAME` | an entry for a rule gains `follows`, `[{proof, line}]`, the proofs naming it that are not on the default branch's copy; drift prints `PROOF_WILL_NAME` for each, after the entry's own line |
| `dev/test_collaboration.py` | `renumber` is run with `--yes`; one collision is left as git's conflict and resolved by the script |

### 4.4 Lane `signoff`

| File, function | Change |
|---|---|
| `scripts/mcp/purlin/signatures.py`, `signed_with(project_root, sha)` (new) | the `SHA256:` fingerprint `ssh-keygen -Y check-novalidate` names for the commit's signature, or None; `_verifies` is built on the same call |
| `signatures.py`, `hand_notes(project_root, features=None)` | fills `changed` (K2): for the sign-off whose note is shown, the rule's text and each `@manual` proof's text in `HEAD`'s package of that version against the spec as it is |
| `signatures.py`, `standing_by_files(project_root, version)` (new) | `(commit, '')` where this checkout holds no tag `signed/<version>`, `HEAD` holds the version's package and a sign-off of it counts: the commit that added the oldest such sign-off; else `(None, why)` |
| `scripts/mcp/purlin/facts.py`, `signoff_fact`, `TAG_NOT_HERE` | the versions read are those of the tags on `HEAD` and those of the `.signoffs` folders `HEAD` holds, newest first; a version with no tag in this checkout is answered by `standing_by_files`, and adds `TAG_NOT_HERE` to `warnings` |
| `scripts/review/sign.py`, `_sign`, `WRONG_KEY` | after `_commit`: `signed_with(sha)` against `key_fingerprint`; on a difference `git reset -q --soft <info['head']>`, `_take_back`, `WRONG_KEY`, exit 1, before any tag |
| `sign.py`, `answers_ask`, `SIGN_ASK_TYPED`, `NOT_SIGNED_ANSWERS` | the question an answers file is asked reads `SIGN_ASK_TYPED`; a `sign` that is not the address ends on `NOT_SIGNED_ANSWERS` |
| `sign.py`, `result_lines`, `NO_TEST_RUNS` | a rule whose every proof is `@manual` prints `NO_TEST_RUNS` alone under `Results` |
| `sign.py`, `render_stop`, `NOTE_CHANGED` | under `Last note`, the line for the stop's `changed` before the notes |
| `scripts/export/package.py`, `_results` | a rule whose every proof is `@manual` carries `result` `checked at sign-off` |
| `package.py`, `audit_counts` | a rule is counted under its strong word only where that is one of the five; no other rule is counted |

### 4.5 Lane `surfaces`

| File, function | Change |
|---|---|
| `scripts/mcp/purlin/states.py`, `_passed_cell`, `NOT_CHECKED`, `HAND_CHANGED` | the three rows of section 2.2 for a rule whose proofs are all `@manual` |
| `states.py`, `_strong_cell` | waits only where the passed word is neither `passed` nor `checked at sign-off`; a hand check's reasons open with the `HAND_CHANGED` lines |
| `states.py`, `BUCKETS`, `_bucket`, `_flags` | the bucket `by_hand`; the flag `by_hand` |
| `scripts/mcp/purlin/payload.py`, `SCHEMA_VERSION`, `_rule_entry` | 16; hands `hand_changed` to `rule_cells` |
| `scripts/mcp/purlin/summary.py`, `steps`, `sentence`, `rule_kind`, `BY_HAND_ONE`, `BY_HAND_MANY` | `steps` answers `{'passed', 'by_hand'}`; the sentence's third part; `rule_kind` answers None for a passed word of `checked at sign-off` |
| `scripts/mcp/purlin/board.py`, `passing`, `tests_cell`, `strong_cell`, `audited_rules(rollup)` (new) | `passing` leaves `by_hand` out; `· <k> by hand`; `<strong> of <n>`, `n` the sum of the rollup's five audit flags, `''` where it is 0 |
| `scripts/report/src/app.js`, `board.js`, `rule.js` | `SCHEMA` 16; `WORDS.by_hand`; `testsCell`, `strongCell` and the two boxes of `statStrip` read as `board.py` does; `checked at sign-off` takes the neutral tone in the passed row |
| `dev/fixtures/report/{regulated,team,solo}.json` | schema 16, `steps.by_hand`, each rollup's `by_hand`, invoice `RULE-3`'s passed cell |

### 4.6 Lane `run`

| File, function | Change |
|---|---|
| `scripts/mcp/purlin/project.py`, `refusal(project_root, started_in)`, `plugin_root()`, `same_repository(a, b)` (new) | K5 |
| `scripts/mcp/purlin/server.py`, `handle_request`, `main`, `NO_PROJECT_HERE` | one call to `project.refusal(call_root, STARTED_IN)`; `STARTED_IN` is `resolve_project_root()`'s answer when the server starts; the line ends `Run purlin:init.` |
| `scripts/run/purlin_status.py` (new) | `--project-root DIR` (default `.`), `--spec NAME`, `--help`; K5 |
| `scripts/run/purlin_drift.py` (new) | `--project-root DIR`, `--since N-or-date`, `--json`, `--help`; K5 |
| `scripts/run/purlin_run.py`, `parse_args`, `main`, `USAGE`, `WRITE_QUESTION`, `WROTE_TESTS` | `--write-tests`; after `no_test_command_lines` printed a suggestion, the question; on yes `config_engine.update_config(root, 'tests', entries)`, `WROTE_TESTS`, and the run goes on with the suites read again |
| `scripts/run/evidence.py`, `rule_word` | `checked at sign-off` where no proof of the rule can run |
| `scripts/review/audit_run.py`, `scripts/review/ai_audit.py`, `dev/fake_claude.py` | section 2.9 |

## 5. The base commit, the lanes and their contracts

All local. No cloud session. Nothing is pushed by a lane.

### 5.1 The order

1. **The base commit, by the coordinator, on `main`**, once the audit run there has finished
   and committed. This plan as `dev/plans/d122-plan.md`; decision 122 in
   `dev/plans/three-levels.md`; and two seams, changed once and then frozen.
   `bash dev/run_tests.sh` is run after it and stays at 0 failed.
2. **Six lanes in parallel**:
   `git worktree add /Users/richlabarca/LocalCode/purlin-wt/d122-<lane> -b lane/d122-<lane> main`.
3. **Integration** (section 8).

| Seam | File | What |
|---|---|---|
| B1 | `scripts/review/sign.py` | `answers_ask(answers, out, email)` answers yes only where `sign` is a string equal to `email`, case and outer spaces set aside; `walk_with_answers` hands it `info['email']`. Before the change the coordinator runs `signatures` PROOF-264's case with `"sign": true` once and records that it signs |
| B1 | `dev/test_signatures.py`, `dev/test_collaboration.py`, `dev/test_init_scaffold.py`, `dev/test_report_refresh.py`, `skills/sign/SKILL.md`, `docs/sign-off.md` | each `'sign': True` and `"sign": true` becomes the signer's address of that test or example; the skill's block reads `"sign": "quinn.qa@labconnect.example"`, the signer `dev/test_purlin_agent.py` already uses |
| B2 | `scripts/mcp/purlin/signatures.py`, `payload.py`, `scripts/review/sign.py` | `hand_notes` answers K2's shape with `changed` always `[]`; `payload._feature_entry` hands `notes` on as today and `changed` as `hand_changed`; `sign.plan` gives each stop `last_notes` and `changed` |

### 5.2 The lanes

| Lane | Owns, and writes nothing else | Acceptance |
|---|---|---|
| `setup` | `scripts/mcp/purlin/specs.py`, `scripts/mcp/purlin/markers.py`, `scripts/anchor/upstream.py`, `scripts/init/update.py`, `scripts/init/scaffold.py`, `templates/gitignore.purlin`; `specs/mcp/schema_spec_format.md`, `specs/run/reports.md`, `specs/anchor/upstream.md`, `specs/init/update.md`, `specs/init/scaffold.md`; `references/formats/spec_format.md`, `references/formats/marker_format.md`; `dev/test_schema_spec_format.py`, `dev/test_specs_reader.py`, `dev/test_reports.py`, `dev/test_upstream.py`, `dev/test_init_update.py`, `dev/test_init_scaffold.py` | its five reproductions fail first, then pass; its six test files pass |
| `collision` | `scripts/spec/renumber.py`, `scripts/mcp/purlin/drift.py`; `specs/spec/renumber.md`, `specs/mcp/drift.md`, `specs/workflow/collaboration.md`; `dev/test_renumber.py`, `dev/test_drift.py`, `dev/test_collaboration.py` | `renumber` PROOF-17 and PROOF-18 fail first; the collaboration test resolves one collision with no hand edit of a conflict line; its three test files pass |
| `signoff` | `scripts/review/sign.py`, `scripts/mcp/purlin/signatures.py`, `scripts/mcp/purlin/facts.py`, `scripts/export/package.py`; `specs/review/signatures.md`, `specs/export/package.md`; `references/formats/package_format.md`, `references/formats/signature_format.md`; `dev/test_signatures.py`, `dev/test_export.py`, `dev/sign_project.py` | `signatures` PROOF-269, 272 and 274 fail first; its two test files pass |
| `surfaces` | `scripts/mcp/purlin/states.py`, `payload.py`, `summary.py`, `board.py`, `status.py`, `report_data.py`; `scripts/report/src/*`; `dev/fixtures/report/*.json`; `specs/mcp/states.md`, `specs/mcp/summary.md`, `specs/dashboard/purlin_report.md`; `dev/test_states.py`, `dev/test_summary.py`, `dev/test_backing_tests.py`, `dev/test_failing.py`, `dev/test_purlin_report.py`, `dev/test_purlin_report_board_layout.py`, `dev/test_report_refresh.py`, `dev/mcp_project.py` | its test files pass; the page was looked at with Playwright from the `.venv`, in both themes, at 390, 768, 1024, 1280 and 1500 pixels, with a hand check not yet noted and one whose wording changed on screen, and no value wraps |
| `run` | `scripts/mcp/purlin/server.py`, `scripts/mcp/purlin/project.py`, `scripts/run/purlin_status.py`, `scripts/run/purlin_drift.py`, `scripts/run/purlin_run.py`, `scripts/run/evidence.py`, `scripts/review/audit_run.py`, `scripts/review/ai_audit.py`, `dev/fake_claude.py`; `specs/mcp/server.md`, `specs/run/run_script.md`, `specs/run/evidence_writer.md`, `specs/review/ai_audit.md`; `references/formats/evidence_format.md`; `dev/test_mcp_server.py`, `dev/test_run_script.py`, `dev/test_evidence_writer.py`, `dev/test_ai_audit.py`, `dev/run_project.py` | `server` PROOF-170 fails first; its four test files pass with no real `claude`; `git grep -n -i -E 'cost_usd|total_cost|audit_run\.json|CALLS_|EXPERIMENTAL' -- scripts dev/fake_claude.py dev/test_ai_audit.py` is empty |
| `words` | `README.md`, every page under `docs/`, `skills/*/SKILL.md`, `agents/purlin.md`, every file under `references/` that is not under `formats/`, `RELEASE_NOTES.md`, `CLAUDE.md`, `dev/plans/deck/build_deck.py`; `specs/skills/*.md`, `specs/instructions/purlin_agent.md`, `specs/instructions/purlin_docs.md`; `dev/test_skill_*.py`, `dev/test_purlin_docs.py`, `dev/test_purlin_agent.py`, `dev/skill_checks.py` | every line is section 6's; its test files pass but `purlin_agent` PROOF-51 and PROOF-52, which wait on the scripts and flags of lanes `run` and `collision` and are named in its report |

Merge order: `setup`, `run`, `collision`, `signoff`, `surfaces`, `words`, each `--no-ff`. No two
lanes own one file, so any order merges clean; `words` goes last because its two waiting tests
clear on the others.

**The lane prompt** is the brief of decision 121 (`d121-lane-brief.md`), with: this plan and
the QA report in place of the review; decisions 100 to 122; `d122` in every path and branch;
the report at `dev/plans/d122-reports/<lane>.md`. Its "Notes from the base commit" hold the two
seams above and no red test. Three traps hold: never `git checkout -- specs/`; no generated
file is staged (`scripts/report/purlin-report.html`, `.purlin/evidence/**`,
`.purlin/report-data.js`, `docs/images/*.png`); no dollar figure and no count of model calls in
any line a lane writes.

### 5.3 Contracts, word for word

**K1. A spec's name** (`setup`; `words` quotes).

```python
# scripts/mcp/purlin/specs.py
NAME = r'\w[\w-]*'          # letters, digits and _, then those and -

def name_ok(name):
    """True where the whole name matches NAME."""

NAME_REFUSED = ('%s: the name holds a character other than letters, digits, _ and -, so '
                'no test comment can name it. Rename the file: git mv %s %s')  # name, path, new path
PROOF_LINE_UNREAD = '%s: a line under ## Proof cannot be read, because %s: "%s". Run purlin:spec %s.'
TAG_AT_END = 'a tag goes at the end of the line'
NOT_A_PROOF_LINE = 'a proof line reads `- PROOF-N (RULE-N): <text>`'

# scripts/mcp/purlin/markers.py
NAME_CHARACTERS = ("`%s` holds a character a spec's name cannot: a name holds letters, "
                   "digits, `_` and `-`")
```

**K2. A hand check's notes** (base B2 shapes; `signoff` fills; `surfaces` and `sign.py` read).

```python
# scripts/mcp/purlin/signatures.py
def hand_notes(project_root, features=None):
    """`{(feature, rule): {'notes': [line, ...], 'changed': [...]}}` from the newest
    sign-off that counts and holds a note on each rule. `notes` are `states.HAND_NOTE`
    lines. `changed` names what was reworded since that sign-off's package was built,
    `'rule'` then `'proof'`: the rule's text, and the text of each of its `@manual`
    proofs, are compared, white space runs read as one space, with the package HEAD
    holds for that version; a rule or proof the package does not hold counts as
    changed. `features` is `specs.scan_specs`' answer; None reads it."""
```

`states.rule_cells` takes `hand_notes`, the list of lines, and `hand_changed`, the list.

**K3. The passed cell's word for a hand check** (`surfaces` writes; `signoff` and `run` read).

```python
# scripts/mcp/purlin/states.py
CHECKED_AT_SIGNOFF = 'checked at sign-off'      # as now
NOT_CHECKED = 'no sign-off has checked it yet'
HAND_CHANGED = {'rule': "the rule's wording changed since its last note",
                'proof': "the proof's wording changed since its last note"}
BUCKETS = ('untested', 'failing', 'partial', 'by_hand', 'passed')
```

`summary.steps` answers `{'passed': p, 'by_hand': h}`. A section's `rules` word and a package
result's `result` read `checked at sign-off` for a rule whose proofs are all `@manual`. The
package's `steps` stays `{'passed': p}`.

**K4. The audit's one count** (`surfaces`, `signoff`). `summary.audit_counts` is the count: a
rule whose passed cell reads `passed`, under its strong cell's word where that is one of the
five. `board.strong_cell` and the dashboard's `strongCell` read `<strong> of <n>` over one
spec's rules, `n` the sum of the five. `package.audit_counts` counts the same rules.

**K5. The tools' refusals and the two scripts** (`run`; `words` quotes).

```python
# scripts/mcp/purlin/project.py
NO_PROJECT_HERE = ('No Purlin project root at %s: .purlin/config.json is not there. '
                   'Run purlin:init.')
PLUGIN_FOLDER = ("%s is Purlin's own folder, not your project. Pass the top folder of "
                 "the git checkout you are working in.")

def refusal(project_root, started_in):
    """The one line to answer in place of the work, or None. PLUGIN_FOLDER where
    `project_root` is `plugin_root()` or under it, unless `started_in` is that
    folder, under it, or `same_repository(started_in, plugin_root())`; then
    NO_PROJECT_HERE where it holds no `.purlin/config.json`; then
    `config_engine.config_problem`'s sentence. Paths are compared by real path."""
```

```
purlin_status.py [--project-root DIR] [--spec NAME]
purlin_drift.py  [--project-root DIR] [--since N-or-date] [--json]
```

`started_in` is the working directory for a script. `purlin_status.py` prints
`status.sync_status(root)` and exits 0, or the refusal and exits 1; a wrong command line exits
2. With `--spec NAME` it prints each of the payload's warnings that opens `NAME: ` or names
the spec's path, and exits 1; or `SPEC_CLEAN` and exits 0; or `NOT_A_SPEC` and exits 1.

```python
SPEC_CLEAN = '%s: %s and %s read. No mistake found.'   # login, '2 rules', '3 proofs'
NOT_A_SPEC = '%s: no spec of this checkout has that name. Run purlin:status to see its specs.'
```

`purlin_drift.py` prints `view.lines`, one per line, and exits 0; `--json` prints the tool's
answer; a `since` drift refuses prints `<error>: <reason>` and exits 2.

**K6. The renumbering** (`collision`; `words` quotes).

```
renumber.py <feature> [--dry-run | --yes] [--project-root DIR]
```

```python
ASK = 'Do it? [y/N] '
NOT_DONE = 'Nothing is changed.'
KEEPS_BOTH = '%s: the conflict at line %d keeps both sides: %s from %s and %s from %s.'   # '1 line', HEAD, '2 lines', qa/login
TAKES_HIGHER = '%s: the conflict at line %d takes > Highest-%s: %d, the higher of %d and %d.'
LEFT = '%s: the conflict at line %d is left: %s. Resolve it by hand, then run purlin:spec %s again.'
LEFT_BOTH_CHANGED = 'both sides changed %s'                 # RULE-2
LEFT_REMOVED = 'a side removes %s'                          # RULE-2
LEFT_OTHER_LINE = 'it holds a line that is not a rule, a proof or a > Highest- line'
LEFT_NO_BASE = 'git holds no version both sides started from'
RESOLVED = 'Resolved %s in %s.'                             # '3 conflicts', login
RESOLVED_ALONE = 'Resolved %s in %s. Nothing is committed.'
```

A side's label is the text after git's `<<<<<<< ` and `>>>>>>> `. A conflict is `both` where
every line of each side is blank, or a rule or proof line whose id the starting version does
not hold, or holds with the same text; `highest` where each side is one `> Highest-` line of
one kind; else `left`. A resolved `both` holds the first side's lines, then the second's that
the first does not hold. The run stages nothing.

**K7. Drift's two lines** (`collision`; `words` quotes).

```python
MERGE_LINE = ('A merge is in progress and is not committed, so the range above stops '
              'before it. Resolve it and commit, then run purlin:drift again.')
PROOF_WILL_NAME = '%s: %s will name %s.'                    # login, PROOF-3, RULE-3
```

**K8. The `tests` setting** (`run`; `words` quotes).

```python
WRITE_QUESTION = 'Write this tests setting to .purlin/config.json?'   # asked as '%s [y/N] '
WROTE_TESTS = 'Wrote the tests setting to .purlin/config.json.'
```

**K9. The sign-off's lines** (`signoff`; `words` quotes).

```python
SIGN_ASK_TYPED = 'Sign the evidence package for %s as %s? Type that address to sign: '
NOT_SIGNED_ANSWERS = 'Nothing was signed: "sign" in %s must hold %s, typed by the person signing.'
WRONG_KEY = ('No sign-off: the commit was signed with %s, not the key this checkout names, '
             'ending ...%s, so it was taken back and no tag was written. A global '
             'gpg.ssh.program or signing key is the usual cause. Run git config '
             'gpg.ssh.program ssh-keygen, then purlin:sign again.')
KEY_ENDING = 'the key ending ...%s'       # the first %s of WRONG_KEY, or NO_SSH_KEY
NO_SSH_KEY = 'no SSH key this checkout can read'
NO_TEST_RUNS = '  No test runs for this rule: you check it here.'
NOTE_CHANGED = {('rule',): "  The rule's wording changed since this note.",
                ('proof',): "  The proof's wording changed since this note.",
                ('rule', 'proof'): "  The rule's and the proof's wording changed since this note."}

# scripts/mcp/purlin/facts.py
TAG_NOT_HERE = ('%s is not in this checkout: the sign-off of %s at %s is read from its '
                'files. Run git fetch --tags, or purlin:sign if no one wrote the tag.')
```

A key's ending is the last 4 characters of its fingerprint, as `SIGNED_AS` prints it.

## 6. Lines a person reads

### 6.1 The status, a test run, the dashboard

```
10 rules. 9 pass their tests. 1 is checked at sign-off.
10 rules. 8 pass their tests. 2 are checked at sign-off.
sample_age  10     11      9 of 10 · 1 by hand   9 of 9
sample.age: the name holds a character other than letters, digits, _ and -, so no test comment can name it. Rename the file: git mv specs/intake/sample.age.md specs/intake/sample_age.md
login: a line under ## Proof cannot be read, because a tag goes at the end of the line: "- PROOF-7 @manual (RULE-7): A rejection message for an aged sample is clear to a technician". Run purlin:spec login.
login: a line under ## Proof cannot be read, because a proof line reads `- PROOF-N (RULE-N): <text>`: "- PROOF-7: no rule named". Run purlin:spec login.
signed/0.1.0 is not in this checkout: the sign-off of 0.1.0 at f099b41 is read from its files. Run git fetch --tags, or purlin:sign if no one wrote the tag.
Write this tests setting to .purlin/config.json? [y/N]
Wrote the tests setting to .purlin/config.json.
```

A cell's reasons: `no sign-off has checked it yet`, `the rule's wording changed since its last
note`, `the proof's wording changed since its last note`. The dashboard's passed row reads
`CHECKED AT SIGN-OFF`; a `Tests` cell reads `2 of 3 · 1 by hand`.

A near miss's `why`: `` `sample.age` holds a character a spec's name cannot: a name holds
letters, digits, `_` and `-`. ``

### 6.2 The tools and their scripts

```
No Purlin project root at /work/empty: .purlin/config.json is not there. Run purlin:init.
/home/user/purlin is Purlin's own folder, not your project. Pass the top folder of the git checkout you are working in.
login: 2 rules and 3 proofs read. No mistake found.
login: no spec of this checkout has that name. Run purlin:status to see its specs.
```

### 6.3 Setup

No new line. `Commit the files setup wrote? [y/N] ` is asked while one of setup's files is on
disk and not committed, and `Committed e1a0b21, the files setup wrote:` follows a yes.

### 6.4 A collision

```
login: the conflict at line 6 takes > Highest-Proof: 10, the higher of 9 and 10.
login: the conflict at line 20 keeps both sides: 1 line from HEAD and 1 from qa/login.
login: the conflict at line 18 is left: both sides changed RULE-2. Resolve it by hand, then run purlin:spec login again.
login: the conflict at line 18 is left: a side removes RULE-2. Resolve it by hand, then run purlin:spec login again.
login: the conflict at line 3 is left: it holds a line that is not a rule, a proof or a > Highest- line. Resolve it by hand, then run purlin:spec login again.
login: the conflict at line 18 is left: git holds no version both sides started from. Resolve it by hand, then run purlin:spec login again.
Do it? [y/N]
Nothing is changed.
Resolved 3 conflicts in login.
Resolved 1 conflict in login. Nothing is committed.
A merge is in progress and is not committed, so the range above stops before it. Resolve it and commit, then run purlin:drift again.
login: PROOF-3 will name RULE-3.
```

### 6.5 The sign-off

```
  10 rules on Linux/Unix: 9 pass their tests, 1 has a hand check.
  No test runs for this rule: you check it here.
Last note
  The rule's wording changed since this note.
  noted at the sign-off of 0.1.0 by pat.product@labconnect.example, 3 commits since: I read the SST and EDTA rejection messages myself; both are clear.
Sign the evidence package for 0.1.0 as quinn.qa@labconnect.example? Type that address to sign:
Nothing was signed: "sign" in .purlin/runtime/signoff-answers.json must hold quinn.qa@labconnect.example, typed by the person signing.
No sign-off: the commit was signed with the key ending ...8kuw, not the key this checkout names, ending ...JJ8w, so it was taken back and no tag was written. A global gpg.ssh.program or signing key is the usual cause. Run git config gpg.ssh.program ssh-keygen, then purlin:sign again.
```

`Signed 0.1.0 as quinn.qa@labconnect.example with the key ending ...JJ8w.` stays, and is now
read from the commit.

### 6.6 Anchors

```
no_eval: not added. --name takes letters, digits, _ and - alone. Run purlin:anchor add <source> --path <path> --name no_eval.
```

### 6.7 The audit, with no cost and no count

The audit prints one block per rule it read, then the share:

```
login RULE-2   weak
  tests/test_login.py::test_wrong_password: the test checks nothing.
  PROOF-2: the test still passes when src/auth.py:12 reads "return 200"
login RULE-3   spot-checked
  The spot tests found nothing. No bug was planted: PROOF-3 needs Windows, and this machine is macOS.
The audit found 4 of 6 rules strong (66%): 4 strong, 1 weak, 1 spot-checked.
```

What goes, by file:

- `skills/audit/SKILL.md`: `Before the first call the audit prints how many model calls it will make, one for each rule it reads. After the last it prints what the run cost.`; the first and the cost line of Step 2's block; `What the model cost is also written to .purlin/runtime/audit_run.json, which git ignores.` Step 2 opens: `The audit prints one block per rule it read, then the share, and the run ends on the status, as every run does:`
- `docs/audit.md`: the table's heading `Cost` reads `What it takes`; its last row's middle cell reads `**No AI for the spot tests, then one AI call per changed rule and one test run per changed proof**`; the sentence after it reads `Purlin takes the last row.`
- `docs/running-and-evidence.md`: `It prints each rule with what it found, and last the share of rules it found strong:`, then the block above.
- `references/review_criteria.md`, "What the audit reports": the bullets `How many model calls it will make` and `What the model was asked and what it cost` go, and so does `What the model cost is written to .purlin/runtime/audit_run.json, which git ignores.` The owner's text under "Heuristic spot tests" is not touched.
- `references/purlin_commands.md`, the `purlin:audit` row: `What the model cost goes to .purlin/runtime/audit_run.json, which is not committed.` goes.
- `RELEASE_NOTES.md`, 0.10.0: `The audit prints how many model calls it will make, and ends on what they cost and on` reads `The audit ends on`.
- `dev/plans/handoff.md`: its new top section holds no dollar figure and no count of calls, and the older sections' figures are taken out.

### 6.8 The skills

**In every skill that asks the person something** (`init`, `spec`, `spec-from-code`, `build`,
`test`, `sign`, `anchor`), one sentence after its "Paths" paragraph:

```
A line marked **Stop and ask** is a question for the person: print it, end your turn, and act only on their answer. Never answer it yourself.
```

**The status, in `spec`, `status`, `build` and `spec-from-code`**, in place of `Call
sync_status`:

````
Get the status from the tool `mcp__plugin_purlin_purlin__sync_status`, passing `project_root`:
the top folder of the git checkout you are working in. Where the session lists it as a
deferred tool, load it with ToolSearch first. Where the session does not have it, run the
script, which prints the same status:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_status.py" --project-root .
```

Never read `.purlin/report-data.js` or `purlin-report.html` as the status: they hold what the
last command saw.
````

`drift`, `test`, `audit` and `sign` read `when the status opens with a pending-migrations
advisory`, and `init` reads `the status prints`, so only the four skills above hold
`sync_status`. `references/purlin_commands.md` gains the section "The tools and their scripts",
the one home of the two names and the two scripts.

**`status`** gains, under Step 1: `` `No Purlin project root at <folder>: .purlin/config.json
is not there. Run purlin:init.` means this folder is not set up. Say so and name
`purlin:init`. Never pass another folder to get an answer. `` Step 2 opens: `Print the status
as the tool or the script printed it. Never rebuild it as a table of your own.`

**`drift`**, Step 1:

````
Call the tool `mcp__plugin_purlin_purlin__drift` with `project_root`, and `since` where the
person gave `--since`. Where the session lists it as a deferred tool, load it with ToolSearch
first. Where the session does not have it, run the script, which prints the view's lines:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_drift.py" --project-root . [--since <N or date>]
```
````

"When to run it" gains: `` Run mid-merge, drift says `A merge is in progress and is not
committed`: its range stops before the merge. `` "A number written twice" gains:
`` `<feature>: PROOF-n will name RULE-m.` names a proof that follows a moved rule. ``

**`spec`.** Step 3: `Decide the feature name and the category folder:
specs/<category>/<name>.md, never specs/<name>.md. references/formats/spec_format.md says what
a name may hold.` Step 6: `Print each rule with its proofs under it. **Stop and ask** whether
to change any. Change what the person asks and print them again.` Step 7:

````
7. Save the spec when the person is satisfied, then check it:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_status.py" --project-root . --spec <name>
```

It prints each mistake Purlin sees in the spec, or `<name>: <n> rules and <m> proofs read. No
mistake found.` Fix every mistake and run it again. Only then commit the spec on its own and
name `purlin:build` as the next step. This skill never starts building.
````

"Proofs" gains, before `Tag a proof @manual`:

```
A tag stands at the end of the proof line, after the text, never before the rule ids:

- PROOF-7 (RULE-7): A technician reads the rejection message and finds it clear @manual
- PROOF-8 (RULE-8): A batch of 500 samples is taken in; every sample has a result @slow
```

"After a merge conflict", whole:

```
Two branches that took the same number before either merged leave a spec with one id twice,
often inside a conflict git could not merge. The number already on the default branch keeps
it; the rule or proof from the branch not yet merged moves to the next free number.

Do not edit git's conflict lines yourself. The renumbering resolves them: where both sides
only added lines it keeps both sides, it takes the higher `> Highest-` line, and then it
renumbers. Run it as "Renumbering" says.

A conflict it prints as `is left` is one it will not decide, such as one line both sides
changed. Show the person both versions. **Stop and ask** which survives. Edit that conflict
alone, and run the renumbering again.

Then stage the spec and the test files and commit. Where a merge is in progress, that commit
finishes it. Tell the person whose line moved, so the test comments on their branch move with
it. A moved rule's audit is read again.

Two branches that advanced the same anchor pin resolve to the newer sha.
```

"Renumbering", from `Otherwise ask exactly:` on:

````
Otherwise **Stop and ask**, exactly:

```
Do it? [y/N]
```

On yes, run it with `--yes`:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/spec/renumber.py" <name> --yes
```

It makes the edits, commits nothing, and ends on `Renumbered in <name>: ...` or `Resolved <n>
conflicts in <name>. Nothing is committed.` On anything else, renumber nothing. Run without
`--yes` the script asks the same question itself and, with nobody at a terminal, changes
nothing.
````

**`build`.** "Running them": `where no test command is set it prints a suggestion and asks
before it writes one, so write no entry yourself and never edit .purlin/config.json by hand.`

**`test`**, Step 1 gains after `Nothing to run`: `The status follows it, as after every run.`
Step 2's `Suggested tests setting` row ends: `**Stop and ask** once. On yes, run Step 1 again
with --write-tests: it writes the suggested entries and runs. Where the person chose a command
of their own, write that array as the tests setting with the purlin_config tool, then run Step
1 again.` Step 5's two questions are marked `**Stop and ask**`. Step 6 gains: `Show the
run's last lines as it printed them.`

**`sign`.** Step 2, in place of `Run what a refusal names only when the person asks.`:
`**Stop and ask** before you run what a refusal names. Show the refusal, ask whether to run
that command, and run it only on a yes.` Step 4 ends:

```
After the last stop, **Stop and ask**, in these words:
`Sign the evidence package for <version> as <email>? Type that address to sign:`
Write what the person typed, as they typed it, as `sign` in the answers file. The script signs
only where it is the signer's address. Never write the address yourself.
```

Step 4's table and Step 3's offer are marked `**Stop and ask**`. Step 5's block reads
`"sign": "quinn.qa@labconnect.example"`. Step 2's list of refusals gains the `WRONG_KEY` line
of 6.5, and Step 7's table the row `` `No sign-off: the commit was signed with` | `→ Run: git
config gpg.ssh.program ssh-keygen, then purlin:sign` ``. Step 4 gains: `` Where a stop shows
`The rule's wording changed since this note.`, say so to the person: the note was written
about other words. ``

**`anchor`**, "create", after its first paragraph:

```
1. Write what was asked and no more: one rule when one is asked for.
2. Draft each rule and its proofs to `references/spec_quality_guide.md`, "A good anchor". A
   proof a test cannot settle is tagged `@manual` or is not written.
3. Print each rule with its proofs under it. **Stop and ask** whether to change any. Change
   what the person asks and print them again.
4. On their yes, write the file and check it, as `purlin:spec` checks a saved spec.
5. Commit it with the `anchor(<name>): create` prefix.
```

The `add` section's `in letters, digits and _` reads `in the characters a spec's name may
hold`.

**`init`.** `Ask the person the question yourself.` reads `**Stop and ask** the question
yourself.` The flag table's `--yes` row reads `Commits setup's files that are not committed
yet, without asking`. `A second run writes no file: what is there is kept.` gains: `With
--yes it commits what the first run wrote.`

**`agents/purlin.md`.** `Call sync_status` reads `Get the status, with the tool
mcp__plugin_purlin_purlin__sync_status or the script scripts/run/purlin_status.py,`. The hand
check's line reads `A **hand check** is a proof marked @manual. Its rule reads checked at
sign-off until a sign-off notes it: a person looks at it in the sign-off walk.` "Renaming a
feature" gains: `references/formats/spec_format.md says what a name may hold.`

### 6.9 The ten descriptions

Each is what Claude Code matches a request against.

| Skill | `description` |
|---|---|
| `spec` | `Write or change a spec: turn a requirement into rules and proofs, or add, sharpen, reword or remove a rule, a case or a proof of an existing spec. Use it for any change to a file under specs/, instead of editing the file by hand` |
| `status` | `Show where the project stands: whether the tests are met, whether it is signed, each rule's two cells, and what is left to do` |
| `build` | `Write the code and the marked tests for a spec's rules, fix a failing rule, strengthen a weak test, and commit the changeset` |
| `test` | `Run the project's marked tests and record the results as evidence; with --all --commit, the hand-off before a sign-off` |
| `audit` | `Check how much the tests are worth: heuristic spot tests and one planted bug per proof, written into the evidence` |
| `drift` | `Report what a pull, a merge, a rebase or a checkout changed in the rules, the proofs and the tests, and name a number two branches both took` |
| `init` | `Set a project up for Purlin, or bring a project Purlin 0.9.5 set up to this version` |
| `sign` | `Sign off a version: build the evidence package from the committed evidence, walk its hand checks with a person, and sign it in a signed commit; also check a package against its fingerprint` |
| `anchor` | `Write rules that hold across the whole project as an anchor, pull an anchor from another repository, and keep its pin current` |
| `spec-from-code` | `Write the specs for a codebase that has none, from the code and the tests it already has` |

### 6.10 The docs and the references

- `docs/working-together.md`, in place of `Adding a case is plain language. Say "it should also reject an expired token" to purlin:spec.`: `` To add or change a rule, a case or a proof, name the command: `purlin:spec login: it should also reject an expired token`. A request typed without the command may not reach it, and the agent may then edit the file by hand. ``
- `docs/working-together.md` and `docs/specs-and-anchors.md`, "A number taken twice", the `purlin:spec` bullet: `` `purlin:spec` resolves the conflict git left, where both sides only added lines, and shows a dry run of the renumbering. It asks `Do it? [y/N]`. A line both sides changed is left for you to choose. `` And one bullet more: `` Drift run before the merge is committed says `A merge is in progress and is not committed`. ``
- `docs/running-and-evidence.md`, "Out of date", and `docs/specs-and-anchors.md`, after the spec format: `A change to a spec, even to one rule's words, puts every rule of that spec out of date. Its results are held under one fingerprint of the whole spec. purlin:test runs that spec's tests again.`
- `docs/specs-and-anchors.md`, "Judgment calls": `` A rule checked by hand alone reads `checked at sign-off` and is counted as neither passing nor failing: `10 rules. 9 pass their tests. 1 is checked at sign-off.` It never stops the tests reading `met`. Once a sign-off notes it, it reads `passed`, with the note. Reword the rule or the proof and it reads `checked at sign-off` again, with `the rule's wording changed since its last note`. `` The spec format's section gains: `A name holds letters, digits, _ and -.`
- `docs/sign-off.md`: the answers block reads `"sign": "quinn.qa@labconnect.example"`, with `The script signs only where sign holds the signer's own address, typed by the person signing.`; "What is recorded" gains `The key recorded is the key that signed the commit. Where another key signed it, as a global gpg.ssh.program can cause, the sign-off is taken back and names both keys.` and `After a git pull the tag may be missing: a pull fetches no tags. The status then reads the sign-off from its files and names git fetch --tags.`; the refusal table gains the wrong-key row.
- `docs/getting-started.md`: after the first status, `The project's name is read from pyproject.toml, package.json or a .csproj file, then from the remote's name, then from the folder's.`; the `Nothing to run` block shows the status under it; the setup step says `purlin:init --yes commits setup's files whenever they are not committed yet.`
- `docs/dashboard.md`: the passed row's words gain `checked at sign-off`; the `Tests` cell gains `· 1 by hand`; the `Strong` cell reads `<strong> of <n>`, `the rules that pass their tests and have a tested proof`.
- `references/evidence_and_signoff.md`: "The two facts" gains summary RULE-25's sentence in plain words; "A hand check" takes the three rows of section 2.2; "When a sign-off counts" gains the two sentences of `docs/sign-off.md` on the key and the tag.
- `references/glossary.md`: the `passed` row's words gain `checked at sign-off`; the **hand check** entry reads `a proof marked @manual, which no test runs. A rule checked by hand alone reads checked at sign-off until a sign-off that counts notes it, and is counted neither as passing nor as failing.`; a new entry `**name**: a spec's name, its file name without .md, in letters, digits, _ and -.`
- `references/spec_quality_guide.md`, the cell table: a row `` | passed | `checked at sign-off` | Every proof of the rule is `@manual`, and no sign-off has noted it on its wording as it is. | Nothing to run. A person checks it in `purlin:sign`. | ``
- `references/drift_criteria.md`: the two lines of K7 and what each is built from.
- `references/purlin_commands.md`: "The tools and their scripts"; "Stops", the one home of `Stop and ask`; the `purlin:spec` row gains `resolves a conflict in the spec where both sides only added lines`; the `purlin:test` row reads `On the first run it writes the tests entry once you answer yes, or with --write-tests.`
- `references/supported_frameworks.md`: after the suggestion block, the question and `--write-tests`.
- `references/formats/*`: section 7; each by its own lane.
- `RELEASE_NOTES.md`, 0.10.0, "What is new" gains:

```
- **A spec's name may hold `-`.** A test comment, the upgrade from 0.9.5 and an anchor's name
  read it. A name with any other character is warned of, with the rename.
- **A hand check reads `checked at sign-off` until someone signs.** It is counted neither as
  passing nor as failing, and it says so when its wording changed since its last note.
- **`purlin:spec` resolves a merge conflict in a spec** where both sides only added lines, then
  renumbers. It asks first.
- **The status and drift have a script each**, for a session that does not load the tools.
- **The sign-off records the key that signed**, and reads a sign-off whose tag was not fetched.
- **Three questions are asked by the scripts themselves**: before renumbering, before the
  `tests` setting is written, and before signing.
```

- `dev/plans/deck/build_deck.py`: the `manual` slide's row on what a hand check reads takes `checked at sign-off, and not counted as passing, until someone signs`; the `together` slide's collision row reads `purlin:spec resolves the conflict and renumbers. It asks first.` The coordinator publishes it.
- `CLAUDE.md`: no change.

## 7. Formats

| File | Now | After | Why |
|---|---|---|---|
| `spec_format.md` | 23 | **24** | "Location" says what a name may hold, and that a tag ends the proof line; a consumer that checks names needs it |
| `marker_format.md` | 4 | **5** | the feature of a marker may hold `-`; the near miss with no fix for a name's characters |
| `evidence_format.md` | 11 | **12** | a section's `rules` word gains `checked at sign-off`. `schema` stays `purlin-evidence/2` |
| `package_format.md` | 11 | **12** | a result's `result` and `statuses.passed.word` gain `checked at sign-off`; `audit` counts only the rules that pass and have a tested proof. `schema` stays `purlin-package/4` |
| `signature_format.md` | 16 | 16 | `key_fingerprint` reads `the key that signed the sign-off's commit`: wording only |
| `anchor_format.md` | 12 | 12 | not touched |

Each is changed in the same commit as its code. The dashboard's data goes from schema 15 to 16:
`summary.steps` gains `by_hand`, each rollup gains `by_hand`.

## 8. Integration, local, one agent

1. Merge `setup`, `run`, `collision`, `signoff`, `surfaces`, `words` into `main`, in that
   order, `--no-ff`.
2. `bash dev/run_tests.sh` to 0 failed. Expected, if nothing else moved: about 958 passed and
   9 skipped (906, less the 1 deleted test, plus 53).
3. `python3 scripts/run/purlin_run.py --test --all --commit` to the clean state: 39 specs, 447
   rules, 962 proofs, 962 test comments tied, no rule `failed`, `partial` or `no test`, no test
   comment to correct. Purlin's own specs hold no `@manual` proof, so no count of its own
   moves.
4. The check of every `dev/test_*` against its proof, as decision 121's integration ran it:
   `0 gone`.
5. The greps, each empty:
   ```
   git grep -n -i -E 'cost_usd|total_cost|audit_run\.json|EXPERIMENTAL|The audit reads [0-9<]|was asked [0-9<]|how many (model|AI) calls|what (the run|they|the model) cost' -- . ':!dev/plans' ':!.purlin'
   git grep -n -E '\$[0-9<]' -- docs skills references agents README.md RELEASE_NOTES.md dev/plans/deck dev/plans/handoff.md
   git grep -n -E '"sign": true|purlin:init there|letters, digits and _' -- . ':!dev/plans' ':!.purlin'
   git grep -n -E 'Call `?sync_status' -- skills agents
   ```
6. Two reproductions by hand, once each, in a scratch project: the QA check's collision
   (section 6 of its report) ends with `renumber.py sample-age --yes` and no hand edit; and
   `purlin:init`, then `--yes`, in a repository with no commit, ends on `Committed`.
7. The dashboard: `python3 dev/build_report.py`, then looked at with Playwright from the
   `.venv`, both themes, at 390, 768, 1024, 1280 and 1500 pixels, on the regulated sample:
   `CHECKED AT SIGN-OFF` in the passed row, `2 of 3 · 1 by hand`, a note under changed
   wording. No value wraps, and `purlin_report` PROOF-66 and PROOF-104 pass. The two doc
   screenshots are retaken with `dev/capture_doc_screenshots.py`.
8. Steps 2 and 3 again.
9. **The real sessions, again**, on the owner's word and not as a proof (decision 104): the
   QA check's setup, the smallest model, five turns. A plain `Sharpen the sample-age spec: add
   a boundary case` loads `purlin:spec`. `purlin:build sample-age` ties its tests. The forced
   collision ends with no hand edit. `yes` to setup's question commits. `purlin:status` in a
   folder not set up names `purlin:init` and no other folder. What it finds goes to
   `dev/plans/d122-reports/real-skills-2.md`, with no cost in it.
10. The real Windows run, once: `python3 dev/windows_run.py`. No new proof is tagged
    `@env(windows)`; the run proves the tagged ones over the changed code.
11. `dev/plans/handoff.md` gains a top section: what was built, the numbers of steps 2, 3 and
    10, the formats, and what is left for the owner. `main` stays local: no push, no tag, no
    sign-off.

## 9. Questions for the owner

Two. No lane waits on either: the plan builds the recommended answer.

1. **When someone rewords one rule, should the other rules of that spec keep their test
   results?** Today any change to a spec, even one word of one rule, makes every rule of that
   spec read `out of date` until its tests run again. In the QA check, product reworded one
   rule of ten and the status read `8 rules to test`.
   - **A. No: a change to a spec reruns that spec's tests** (recommended, and what this plan
     builds). The docs say so in one plain sentence. Consequence: after a small edit the status
     shows more work than the edit seems to deserve. One `purlin:test` clears it, in the time
     that spec's tests take.
   - **B. Yes: only the changed rule goes out of date.** Consequence: the evidence file's format
     changes again, about seven source files and four specs change, about 6 rules and 12
     proofs are added, and it needs a lane of its own in a later round. What you gain is the
     status between the edit and the next run reading `1 rule to test`. The next `purlin:test`
     still runs every test of that spec, because tests run by file, and a sign-off still needs
     `purlin:test --all --commit` after any change to a spec.

2. **Is "one model call for each rule", said where a page lists how the audit works, a call
   count?** You asked that nothing track or mention a cost or a number of calls. The audit's
   two printed lines, the file that recorded them and every sentence about them are removed.
   The pages that list the audit's three steps still say the second step is one model call
   for the rule.
   - **A. It stays** (recommended): it says how the audit works and counts nothing. It is in
     the audit skill's steps, `docs/audit.md`, `docs/running-and-evidence.md`,
     `references/review_criteria.md`, the release notes and one slide.
   - **B. It goes too.** Those six places say `the model is asked for a small bug for each
     proof and for its reading`, with no number. Consequence: a reader no longer learns that
     the audit asks once per rule. The audit itself does not change.

## 10. Calls this plan makes

- `-` is allowed in a name, and no other new character. A name with another character is
  warned of, not refused: the spec is still read, so nothing a project holds disappears.
- A hand check that a counting sign-off noted on today's wording reads `passed`, with the note
  as its reason, and is counted among the rules that pass. Before that, and after a rewording,
  it reads `checked at sign-off` and is counted in neither.
- The last line stays `Every rule passes its tests on the committed evidence. To sign it:
  purlin:sign` beside an unchecked hand check. A hand check has no test to pass, and the line
  is quoted in four specs and nine pages, skills and references.
- The run's section writes `checked at sign-off` for such a rule, so the raw evidence says
  what the status says. The evidence format's version moves for one new word.
- A missing tag reads `signed`, with one line, where the sign-off files count. A sign-off made
  in a checkout that never fetched the tag would write a second tag of the same name; the
  line's `git fetch --tags` is what prevents it. `sign.py`'s refusals are not changed for it.
- The key that signed is read with `ssh-keygen`, not with `git log --format=%GF`, which needs
  an allowed-signers file.
- Purlin's own folder is refused unless the server or the script was started in it or in a
  checkout of the same repository. No marker file is added.
- The status and drift scripts are two new files under `scripts/run/`, beside `purlin_run.py`.
  `status.py` and `drift.py` gain no command line.
- `purlin_status.py --spec` reads the status's own warnings, so a saved spec is checked by the
  code that checks every spec.
- `renumber.py` stages nothing. The person's commit finishes the merge.
- A conflict is resolved only where git still holds the version both sides started from
  (`git show :1:<spec>`). After `git add`, or in a file committed with conflict lines in it,
  every conflict is left and named.
- `--yes` commits a `.gitignore` the project already tracked, whole, when setup's block in it
  is not committed.
- The `tests` setting may still be written with the `purlin_config` tool, for a command of the
  person's own. A hand edit of `.purlin/config.json` cannot be stopped by a script; a wrong one
  is named by the run, as today.
- No rule pins a skill's wording. The real sessions of step 9 are the check.
- `docs/audit.md`'s table keeps its three rows. Its heading no longer reads `Cost`.

Left out, and why:

- **Finding 14, a spot test for `assert r is not None`**: the owner left it out. The planted
  bug found that test.
- **Finding 15, drift pairing a rename**: the owner left it out. Allowing `-` removes the
  rename the QA check had to make.
- **Finding 18, the agent definition offered only as a subagent, and a small model for
  `purlin:build`**: outside Purlin's own scope. The routing that definition holds is now in
  the ten descriptions.
- **Per-rule staleness**: question 1.
- **A slow proof with a real model for finding 11**: decision 104 keeps real sessions out of
  proofs.
- **The `Audit` box reading `0 of 0 strong`** while every result is out of date: true as
  written, and it clears on the next run.

## 11. Where this plan depends on decision 121

1. **`signatures` RULE-130** was written by decision 121 for a tag typed by hand. It is
   reworded, and its two proofs, PROOF-252 and PROOF-253, stand as they are.
2. **`signatures.hand_notes`** was moved to `signatures.py` by 121's base commit. Seam B2
   changes its shape once.
3. **The audit's counts**, `summary.AUDIT_WORDS` and `audit_line`, are 121's and are not
   changed. `package.audit_counts` and `board.strong_cell` are brought to them.
4. **`ai_audit` RULE-45** and `audit_run.EXPERIMENTAL` are 121's, and go.
5. **The numbers.** 433 rules and 910 proofs are counted after 121's integration, at
   `8d55f7010`.
