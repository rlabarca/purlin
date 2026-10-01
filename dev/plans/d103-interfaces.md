# Decision 103: what was built

The plan is `d103-plan.md`. Ten lanes built it in cloud sessions on Linux, each on
`lane/d103-<lane>` from `d103/base` at `e5f82d0`, and one integration merged them into
`d103/base` on the owner's Mac on 2026-09-30, in the order settings, counting, drift, release,
signoff, run, dashboard, skills, words, docs. No two lanes wrote the same file, so each rebase
was clean and each merge a fast-forward. Each lane's own report is
`dev/plans/lanes/d103-<lane>.md`. This file says where the build differs from the contracts, the
ids each spec now stands at, the test counts, and every word a lane chose that section 7 does
not give.

## Where the build differs from the contracts

### Calls the lanes made where a contract is silent

- **settings.** The upgrade prints `The gate strong is now passed; ...` only when the gate chosen
  is `passed`; a person who answers `signed` is not told. RULE-77 overlaps RULE-1 and PROOF-5,
  RULE-78 overlaps RULE-5; section 4 asked for each.
- **counting.** The payload's rule entry also drops `applies_to`, `code_hash` and `audit_hash`.
  `summary` keeps its older counts beside C4's keys. The strong cell shows `strength <p>%` only
  while `mutation_engine` is not `none`; `undecided` still reads `weak`; `no mutation score
  measured` stays as the reason with the breaks off. `board.columns_for` and `row_cells` take
  `audited`; the `Strong` column shows at either gate where the audit found a rule strong or
  weak. `payload.signed_tag` is now `payload.release_tag` (`signed/` wins over `passed/` at one
  version). `test_hash_kind` moved into `payload.py`.
- **drift.** `numbers_twice` entries gain `case` and `moves`; new `default_spec`, `spec_at`,
  `comment_reworded`, `text_of`. With no default branch no proof line follows a moved rule. A
  comment written in a commit already in HEAD's history is not named as on another branch.
- **release.** `only_signoffs_since(root, commit)` takes no version and reads `commit..HEAD`.
  `uncommitted_work` returns a bool. `TAGGED` names HEAD after the package commit; the tag's
  message names the commit the package describes. `package.commit()` lost `signed`; a plain
  `git commit` signs where `commit.gpgsign` is on. `package.py`'s own `NO_VERSION` still names
  `purlin:export --release`, which still exists. PROOF-3, 12, 13 and 15 of `release.md` differ
  from section 4 in their setup (the lane report says how).
- **signoff.** `NO_VERSION` is checked third (gate, uncommitted work, version, package, moved,
  failing, behind, already signed, key), because the package refusal names the version. The sha
  in `NO_SIGNOFF_MOVED` and `OVERVIEW` is the commit that added the package. A later sign-off
  writes the tag when `signed/<version>` does not yet exist. `ALREADY_SIGNED` compares the
  signer's file at HEAD with the package's fingerprint; a sign-off over an earlier package of the
  same version is written over. The overview counts over rules that are not hand checks. An
  empty or unknown answer asks again; end of input stops; an empty line at the strong list is
  `go on`. `--show` checks the key. A sign-off commit git refuses leaves no file behind.
- **run.** Under `--release` the status table and its last line print before the release's
  lines, so a passing release reads `Nothing left to do. To release a version: purlin:test
  --release`, then `Evidence package committed`, `Tagged ...` and the push line. Left for the
  owner. `--release` beside `--feature`, `--audit`, `--ci` or `--remote` exits 2. The test
  skill's `Exit codes:` line is unchanged.
- **dashboard.** The tag chip shows at `signed` alone, as before. One predicate,
  `summary.audit.strong + weak > 0`, decides the `Strong` box, column, badge, cell row and
  Audit panel. RULE-45 still mentions solid badges, of which none remains. `feature.incomplete`
  still draws `<name> · no scope` (RULE-43), though the kind `no_scope` is gone. RULE-71 has
  one more proof than the plan named (PROOF-222, at `passed`).
- **skills.** `references/formats/spec_format.md`'s `> Scope:` row still reads required at the
  gate `signed`, though no kind waits on it now; making it optional is structural and left for
  the owner. The quality guide keeps the reason `manual proof`.
- **words.** `CLAUDE.md`'s `package_format.md` row still says `purlin:export and purlin:sign
  write`; it should read `purlin:export and purlin:test --release`. Integration left it:
  `CLAUDE.md` changes are the owner's.
- **docs.** `docs/specs-and-anchors.md` no longer says what a project does with a pinned
  anchor's rule that does not apply. `docs/raising-the-gate-and-upgrading.md` describes the
  upgrade without its two literal lines. The deck's slide `strong` is now `audit`.

### What integration changed

- `scripts/spec/renumber.py`: macOS `git grep -E` does not read `\b`, so a comment on another
  branch was never named there (renumber PROOF-12 failed on the Mac alone). The id now ends on
  `([^0-9]|$)`.
- `scripts/review/ai_audit.py`: C12 deletes `NOT_A_RULE` and `not_a_rule` from `sign.py`, which
  `ai_audit.py` imported; both now live in `ai_audit.py`, their one reader (ai_audit RULE-13),
  word for word.
- `specs/run/run_script.md` PROOF-11 and PROOF-95 and their tests: they quoted the bare
  `Nothing left to do.`; they now read C3's `Nothing left to do. To release a version:
  purlin:test --release`. `dev/test_e2e_anchor_rules.sh` the same.
- `specs/dashboard/purlin_report.md` PROOF-59 and its test: the sign-off names `--release
  1.0.0`, since the project states no version and C8 refuses without one.
- `dev/fixtures/report/*.json`: `applies_to`, `code_hash` and `audit_hash` taken out of every
  rule, as the builder no longer writes them (states PROOF-82, PROOF-96).
- `dev/test_states.py`: the test still marked for deleted states PROOF-194 deleted (the run
  named it as a comment no spec has).
- The frozen helpers, as section 6 step 2 gives them (`chore: the frozen helpers follow decision
  103`). Beyond the plan: `mcp_project.py` loses its now-unused `signatures` import, and
  `sign_project.py` its `signatures` and `specs` imports. `_listed` stays: `dev/test_states.py`
  imports it.
- `references/writing_style.md`, which no lane owned: the gate `strong` and `to sign` taken out
  of its three example lines. `skills/sign/SKILL.md`'s `description` is now the command
  reference's purpose sentence, `Walk what a person has to look at in a release, then sign its
  evidence package in a signed commit`. `dev/fixtures/consumer-ci/tests/test_greeting.py`'s
  docstring reads `passed` for `strong`.
- `dev/plans/deck/build_deck.py`: the anchors slide's closing line wrapped past the 920-pixel
  limit after lane `docs`; it now reads `<b>An anchor's rules count like any other:</b> tested
  and audited in every project, and signed with the release.` Every slide fits.
- `scripts/report/purlin-report.html` was rebuilt and is committed once, inside
  `fix(purlin_report): the sign-off in PROOF-59 names its version` (a test rebuilt it in the
  checkout and that commit took it); `python3 dev/build_report.py` afterwards changes nothing.
  The two docs screenshots were retaken and committed.

## Ids

| Spec | Highest-Rule | Highest-Proof |
|---|---|---|
| `specs/dashboard/purlin_report.md` | 71 | 222 |
| `specs/export/package.md` | 31 | 64 |
| `specs/export/release.md` (new) | 12 | 16 |
| `specs/init/scaffold.md` | 78 | 170 |
| `specs/init/update.md` | 49 | 161 |
| `specs/instructions/purlin_agent.md` | 17 | 48 |
| `specs/instructions/purlin_docs.md` | 13 | 18 |
| `specs/mcp/config_engine.md` | 18 | 44 |
| `specs/mcp/drift.md` | 34 | 80 |
| `specs/mcp/evidence.md` | 33 | 85 |
| `specs/mcp/server.md` | 32 | 163 |
| `specs/mcp/states.md` | 109 | 264 |
| `specs/mcp/summary.md` | 19 | 47 |
| `specs/review/ai_audit.md` | 31 | 93 |
| `specs/review/signatures.md` | 111 | 222 |
| `specs/run/evidence_writer.md` | 26 | 89 |
| `specs/run/host.md` | 45 | 139 |
| `specs/run/mutation.md` | 37 | 100 |
| `specs/run/run_script.md` | 94 | 269 |
| `specs/skills/skill_anchor.md` | 16 | 38 |
| `specs/skills/skill_audit.md` | 25 | 52 |
| `specs/skills/skill_build.md` | 19 | 48 |
| `specs/skills/skill_drift.md` | 13 | 39 |
| `specs/skills/skill_export.md` | 14 | 36 |
| `specs/skills/skill_init.md` | 85 | 96 |
| `specs/skills/skill_sign.md` | 31 | 62 |
| `specs/skills/skill_spec.md` | 30 | 60 |
| `specs/skills/skill_spec_from_code.md` | 51 | 165 |
| `specs/skills/skill_status.md` | 12 | 36 |
| `specs/skills/skill_test.md` | 21 | 50 |
| `specs/spec/renumber.md` (new) | 9 | 12 |

Formats as C14 gives them: signature 14, package 7, evidence 7, spec 21, anchor 11, marker 3;
payload `schema_version` 13; drift criteria 12. Integration added no rule and no proof.

## Test counts

- Full sweep at `d103/base` before the evidence commit, `bash dev/run_tests.sh`: `2246 passed, 3
  skipped in 658.25s`, `>>> All Pytest Tests: PASSED`, `Suites: 5 passed, 0 failed`. The sweep
  of decision 102 had 2411 passed: decision 103 deletes per-rule signing, the gate `strong` and
  the retired kinds with their tests. The 3 skips are the Windows-only tests.
- `python3 scripts/run/purlin_run.py --test --all`, then with `--commit` (`447578d05 purlin:
  evidence at 73a3ada`): `Markers: 2287 tied to a test, 0 not tied.`, `Ran pytest, shell on 38
  features.`, `84 proofs need Windows; this machine is macOS. Run purlin:test --remote.`,
  `921 rules. 837 pass their tests.`, and `Left to do:` / `  84 rules to test on Windows:
  purlin:test --remote`. No rule `failed`, `partial` or `no test`, no spec to repair, no
  warning. 84 rules wait for Windows, which has not been run since decision 100.
- Each lane's own files, run whole after its merge on the Mac, before integration's fixes:
  settings 9 failed (each waiting for counting, release, signoff), counting 3 failed (waiting
  for dashboard), drift 1 failed (renumber PROOF-12, macOS only, fixed), release 128 passed,
  signoff 67 passed, run 1 collection error (`not_a_rule`, fixed) and then 2 failed (PROOF-11,
  PROOF-95, fixed), dashboard 1 failed (PROOF-59, fixed), skills 95 passed, words 11 passed,
  docs 11 passed. `--fast` ran after the settings merge (178 failed, 98 errors, every one
  expected by section 6); the per-merge `--fast` runs after it were stopped in favour of the
  full sweep on the merged line, which the lanes' disjoint files allow.
- Not run on the Mac by any lane before: the browser suites, dotnet 8 and the `@env(macos)`
  proofs; all pass here.

## Words chosen by a lane, word for word

Copied from each lane's report, section "Words chosen that section 7 does not give". Integration
chose one more line, the anchors slide's closing above.

### Lane `settings`


- The init skill's gate table: `| Gate | What a release asks | The tag |`, rows
  `every rule's tests pass` / `purlin:test --release writes passed/<version>, unsigned` and
  `every rule's tests pass, and a person signs each release` / `the first purlin:sign over the
  evidence package writes signed/<version>`; then `A person pushes the tag.` and `At either gate
  the AI audit and mutation testing are tools a person runs with purlin:audit; nothing waits on
  them.`
- The init skill: `Under signed, a release needs a sign-off over its evidence package`, and the
  update paragraph's `reading a gate of strong as passed and taking out min_strength`.
- `gate.py` names the retired-keys line `RETIRED_LINE`; its text is decision 102's, unchanged.

### Lane `counting`


- The status skill, Step 2: `` `Strong` only where the audit found a rule strong or weak. It is the
  dashboard's board as text. ``
- The status skill, Step 2: `` `Strong` reads `<n> of <rules>` the audit found strong, then
  `· <strength>%` where measured. ``
- The status skill, Step 3: `The sentence counts the rules that pass their tests, then what the
  audit found where it read any.` and `When nothing is left, one line naming the release step
  follows the sentence instead.`
- The status skill, renumbering (RULE-12):
  ``Where a warning says a number is written twice, follow `Renumbering` in `skills/spec/SKILL.md`.``
- The status skill's closing table, the signed row: `` `... purlin:test --release, then
  purlin:sign` `` with `` `→ Run: purlin:test --release`, then `purlin:sign` ``.
- The status skill's closing table, the release row: `` `→ Run: git push origin <tag>` ``.
- `states.py` keeps `no mutation score measured` as the one reason of a strong cell with nothing
  measured and the breaks off.

### Lane `drift`


- The helper, exit 1: `<feature>: no spec of this checkout has that name. Run purlin:status to see its specs.`
- Drift criteria, `qa`: `After those lines the view prints the lines of Left to do that stop a
  release, in the words the status prints them, such as 2 rules to fix: purlin:build and 1 spec
  to repair: purlin:spec. Each is left out at zero, and no other line of Left to do is printed: a
  rule to strengthen or to write a proof for stops no release.`
- Drift criteria, a number written twice: `purlin:spec makes the edit, and moves the test comments, when you say yes to its plan.`
- Drift criteria, `mutation_engine`: `purlin:init, which asks at the gate signed whether to break
  the code on purpose, and purlin:init --mutation at either gate`; `none turns mutation testing
  off, so no breaks run; any other value runs them when purlin:audit runs, and nothing waits on
  them`.
- Drift skill: `purlin:drift qa   Proofs and tests changed, and what stops a release`; `To
  renumber it and move the test comments that name it, follow Renumbering in purlin:spec: it
  shows the plan and asks before anything changes.`; `A test comment whose proof's wording
  changed moves the same way: follow Renumbering in purlin:spec.`; the rows `A line of Left to
  do | → Run: the command that line names` and `→ Run: purlin:spec <feature> where its old
  wording is now another id, else → Run: purlin:build <feature>`; `→ Nothing changed that the
  specs or the tests need. Run: purlin:status`.

### Lane `release`


- When only test comments block a release, the first slot of `NO_RELEASE_FAILING` reads
  `1 test comment does not count` (`<n> test comments do not count`), and the third reads
  `1 test comment to correct`.
- The export skill: `purlin:export writes the package at any time, at any gate, and releases
  nothing. A version is released by purlin:test --release, which commits the evidence and the
  package and tags passed/<version> at the gate passed; at signed the first purlin:sign tags it.`
- The export skill's state row: `finished`: `No line of left stops a release: every rule's tests
  pass, and a weak rule or one with no proof may still be listed`. Its mismatch directive:
  `→ Run: git show <the release tag>:.purlin/evidence/package/<version>.json`.
- Package format 7's prose on the state, the hand checks and the sign-offs beside the package.

### Lane `signoff`


- `OTHER_PACKAGE = 'it signs another evidence package than the one committed'`, the reason a
  sign-off does not count when its `package_hash` is not the committed fingerprint.
- `NO_SOURCE = "      the test's source was not found"` is C8's; the machine fallback
  `an unnamed machine` is chosen.
- The command-line errors: `--answers needs the file that holds them.`,
  `--release needs the version to sign.`, `unexpected argument <x>`,
  `--show and --answers are two steps; name one.`, and the usage line
  `Usage: sign.py [--show | --answers FILE] [--release NAME] [--project-root DIR]`.
- `--help`'s first line: `Sign a release's evidence package, as a signed commit.`
- The skill's closing table: `→ Run: purlin:build <feature>, then purlin:test --release` after a
  stop; `→ Run: purlin:sign when the person is ready` after `Nothing was signed.`;
  `→ Ask the person about that stop, then run: purlin:sign --answers <file>`;
  `→ Ask another person to run: purlin:sign`; `→ Fix what git named, then run: purlin:sign`;
  `→ Fix what git named, then write the tag: git tag -s signed/<version>`.
- The skill's description: `Sign a release's evidence package after walking what a person has to
  look at, as a signed commit`.

### Lane `run`


- The refusal: `purlin: --release runs every test here and commits it, so it takes no --feature, --audit, --ci or --remote. Run purlin:test --release.`
- The script's usage line: `purlin_run.py --release [VERSION] [--arm-timeout SECONDS] [--project-root DIR]`.
- `references/review_criteria.md`: the section `What the audit holds back`, opening `Nothing.
  The AI audit and the breaks are tools at either gate: purlin:audit runs them when a person
  asks, and neither a gate nor a release waits on them.`; `A weak finding does not stop a
  release.`; the sign-off walk's stop at a weak or unaudited rule, in C8's words.
- The audit skill: `The audit and the breaks are tools at either gate: nothing waits on them,
  and a weak rule never stops a release.`; `What the audit found never sets the code: a weak
  rule, or one the model could not be reached for, is listed, not failed.`; the gate table's
  rows `Runs the tests, the breaks where mutation_engine is not none, and the AI audit; what
  they find holds nothing back` and `The same as passed. Evidence either source wrote counts
  here too; the sign-off walk shows what the audit found`.
- The test skill: the `--release` sentence after `Exit codes:`, and the closing rows
  `→ Run: purlin:test --release`, `A line beginning No release:` → `→ Run: <the command it
  names>, or say what git refused`, and `→ Run: git push origin <tag>`.

### Lane `dashboard`


- A `@manual` proof at `passed`: `Checked by hand. A release at the gate passed lists it as not checked.`
- The `no signed tag` hover: `This commit carries no signed tag. The first purlin:sign after purlin:test --release writes signed/<version>, and a person pushes it.`
- The Audit panel's strength: `Test strength 86%.` (the audit's own `STRENGTH_LINE`, C2).
- RULE-69: `The board carries no Signed column at either gate: a sign-off covers a release's evidence package, not a rule`.

### Lane `skills`


- Spec skill, `Renumbering`: `Where drift, the status, purlin:build or this skill finds a number
  written twice, or a test comment whose proof's wording changed since it was marked, run the dry
  run first`; `It reads this checkout alone, fetches nothing and changes nothing. Show every line
  it prints: ...`; `Where it prints <name>: nothing to renumber., say so and ask nothing.
  Otherwise ask exactly:`; `On yes, run the same command without --dry-run. It makes the edits,
  commits nothing, and ends on Renumbered in <name>: ...; commit the spec and the test files with
  the spec(<name>): prefix. On anything else, renumber nothing. A comment on another branch is
  named, never touched: tell the person whose branch it is which id to move it to there.`
- Spec skill: `Move it as "Renumbering" says.`; Reconciling's third thing, `numbers written twice
  or test comments whose proof's wording changed since they were marked`; Ids, `Renumbering by
  hand would silently repoint every test comment that already names the old id, so a number moves
  only as "Renumbering" below says.`; `@manual`, `a person checks it in the sign-off walk of
  purlin:sign and types what they saw.`
- Build skill: `A number written twice in a spec, or a test comment whose proof's wording changed,
  moves as purlin:spec's "Renumbering" says, after the person answers Do it? [y/N].`; `Never write
  evidence or a sign-off by hand. purlin:test and purlin:audit write the evidence, purlin:test
  --release the evidence package, and purlin:sign a sign-off.`; closing rows `Left to do is empty:
  Nothing left to do., and to release a version → Run: purlin:test --release, then at the gate
  signed purlin:sign` and `A rule to strengthen: add the case the audit's finding names, → Run:
  purlin:build <feature>`.
- Anchor skill: `whose Left to do names the rules the change left to test or fix.`
- spec-from-code: `3. With every rule passing and the team wanting to know what its tests are
  worth: → Run: purlin:audit.`
- Quality guide: `Every rule carries two cells at either gate: passed, which a release waits on,
  and strong, what the AI audit found, which nothing waits on. A strong cell reading waiting waits
  on the passed cell, whose row says what moves both.`; the rows `the audit's word, with strength
  N%` and `the audit's word, with strength not measured: <reason>`; `manual test`: `Nothing before
  the release. At the gate signed the sign-off walk of purlin:sign asks what the person saw.`;
  `not audited`: `Nothing waits on it.` and `purlin:audit, when you want one`; the hand check,
  `At the gate signed a person checks it in the sign-off walk of purlin:sign and types what they
  saw, and the sign-off records that note. At the gate passed the release lists it as not
  checked.`
- Spec format: the `@manual` row and `required at signed, where a rule with no proof counts under
  Left to do as a rule to write a proof for`.
- Anchor format: `the results of a run, the evidence package and its sign-offs under
  .purlin/evidence/, and the table .purlin/tests.md. Any change to the project ends an anchor's
  results. At the gate signed its rules are signed as part of the release, with every other rule.`

### Lane `words`


- `purlin:sign`'s purpose sentence, in the command reference and the README:
  `Walk what a person has to look at in a release, then sign its evidence package in a signed commit`.
  Lane `signoff` writes `skills/sign/SKILL.md`'s `description`; the reference says the two carry
  the same sentence, and no test checks it. Integration makes them one.
- The syntax block's sign lines: `Walk the release's stops, then sign its evidence package`,
  `The same, for the version named`, `The overview and every stop, asking nothing`,
  `The walk, with the answers a file gives`, under a new group `Releasing`.
- The Core `purlin:test` row's command cell: `purlin:test [feature ...] [--all] [--release [<version>]] [--arm-timeout <seconds>]`.
- `hard_gates.md` headings: `The two gates`, `The release`, `When a sign-off counts`,
  `What the tags mean`; the table column `Stops a release`.
- The agent's routing rows: "release this version", "tag the release" → `purlin:test --release`;
  "what needs my eyes?" → `purlin:status`, and at a release `purlin:sign`; "add a case ...",
  "this test does not prove it" → `purlin:spec`; "sign off the release" → `purlin:sign`;
  "ask for a sign-off on releases" → `purlin:init --gate <gate>`.
- The agent's NEVER 2 adds `In the walk, every answer and every note is the person's own.`
- The glossary's `scope` now reads optional at both gates (the unscoped-signature rule it held
  is C12's).
- The README's section heading `Releasing, and when a team wants more`.

### Lane `docs`


- Page titles: `The release and the sign-off` (review-and-signing), `From criteria to a sign-off`
  (qa-guide). The index rows are reworded to match.
- Deck: the slide id `strong` becomes `audit`, eyebrow `A tool at either gate`, headline
  `The audit: check that the tests are good`, closing `Nothing waits on the audit. A weak rule is
  listed to strengthen, and it never stops a release.` The `passed` slide gains a fourth row,
  `purlin:test --release`. The deck's pictures are not rebuilt. `slide-strong.png` is stale and
  `slide-audit.png` is new. The `passed` slide may now pass `check_deck.py`'s 920-pixel limit.
- `docs/raising-the-gate-and-upgrading.md` describes C15 without its two literal lines. It says a
  gate this release does not offer is written as `passed`, keeping `mutation_engine`, and each
  unread key is taken out with `removed from .purlin/config.json: <key>`. This keeps the literal
  `min_strength` and the gate `strong` out of `docs/`, for section 6 step 6's grep.
- `docs/specs-and-anchors.md` no longer says `> Scope:` is required at `signed`, because the kind
  `no_scope` is deleted (C3). The paragraph on a pinned anchor's rule that does not apply is
  deleted with nothing in its place. What a project does with such a rule is not stated anywhere
  now.
- The links to `hard_gates.md` that named deleted sections (`#when-a-signature-counts`,
  `#what-signedversion-means`, `#the-three-steps`, `#when-a-version-is-finished`) now name the
  file alone. Three links to `#where-a-runner-runs-and-when-a-project-has-one` stay. If lane
  `words` renames that heading, they break.
- `docs/regulated-workflow.md` shows a sample export package that begins with
  `purlin-package/3`, `steps: {passed}`, `audit: {not_audited, strong, weak}`, and a `left` of
  `to_fix` and `to_strengthen`. This follows C4 and C7; lane `release` owns the real shape.
- The words for the strong cell's table in `docs/team-workflow.md` are this lane's.


## Words chosen for the owner to read

Section 7 of `d103-plan.md`, as built.


| Where | What it says |
|---|---|
| The gate warning (C1) | `"strong" is no longer a gate: it reads as passed, and the audit stays a tool you run. Run purlin:init --update.`; `"gold" is not accepted for gate in .purlin/config.json; it takes passed or signed. Reading it as passed; set it with purlin:init --gate <gate>.`; `.purlin/config.json still carries min_strength, which this release does not read. Run purlin:init --update.` |
| The settings tool (C1) | `"gold" is not accepted for gate; it takes passed or signed. Nothing was saved.`; `min_strength is not read by this release; nothing was saved.` |
| Setup (C16) | `passed  every rule's tests pass`; `signed  every rule's tests pass, and a person signs each release`; `"gold" is not accepted for gate; it takes passed or signed. Reading it as passed.` |
| The upgrade (C15) | `The gate strong is now passed; the audit stays a tool you run with purlin:audit.`; `removed from .purlin/config.json: min_strength` |
| The sentence (C3) | `40 rules. 35 pass their tests.`; `40 rules. 35 pass their tests. The audit found 30 strong and 2 weak.` |
| The last line (C3) | `Nothing left to do. To release a version: purlin:test --release`; `Nothing left to do. To release a version: purlin:test --release, then purlin:sign`; `Nothing left to do. Push the tag to release it: git push origin passed/1.2.0` |
| The strong cell (C2) | `strength 84%`; `strength not measured: mutmut is not installed: run "pip install mutmut"` as a reason, the word staying the audit's |
| The audit's prompt (C2) | `Test strength 84%.` |
| The release run (C5) | `No release: 2 rules do not pass at 8de0b6e: sample_age RULE-2; stability RULE-1. Run purlin:status to see what is left, then purlin:test --release.`; `No release: sample_age cannot be counted: PROOF-4 is written twice in the spec. Run purlin:spec sample_age, then purlin:test --release.`; `No release: the working tree holds changes that are not committed, so the results do not describe a commit. Commit them, then run purlin:test --release.`; `No release: origin/release/1.2.0 holds 1 commit that 8de0b6e does not, as this checkout last fetched it. Pull, then run purlin:test --release.`; `No version: nothing in this project states one. Run purlin:test --release <version>, or write it to a VERSION file.`; `No release: passed/1.2.0 is already written. Run purlin:test --release <version> to name another.`; `No release: the evidence package was not committed: <why>.`; `Evidence package committed: .purlin/evidence/package/1.2.0.json.`; `Tagged passed/1.2.0 at 3c9d2e1.`; `Run purlin:sign to sign it; the first signature writes signed/1.2.0.`; the usage line `purlin:test --release [<version>]  Run every test, commit the evidence and the package, and tag the release at the gate passed` |
| A hand check at `passed` (C13, under Q1's (a)) | `2 rules are checked by hand, and the gate passed records no hand check: accession_screen RULE-1, sample_age RULE-6. The package lists them as not checked.` |
| The tag's message (C5) | `Released at the gate passed.` / `Released at the gate signed.`, then `Commit: <sha>` and `Gate: <gate>` |
| The walk's refusals (C8) | `Nothing is signed at the gate passed: purlin:test --release tags the release unsigned. To sign releases, run purlin:init --gate signed.`; `No sign-off: the working tree holds changes that are not committed. Commit them, then run purlin:test --release.`; `No sign-off: no evidence package for 1.2.0 is committed at 8de0b6e. Run purlin:test --release.`; `No sign-off: the evidence package for 1.2.0 describes 3c9d2e1, and 8de0b6e has changed since. Run purlin:test --release.`; `No sign-off: 1 rule does not pass at 8de0b6e: sample_age RULE-2. Run purlin:status to see what is left, then purlin:test --release.`; `No sign-off: origin/release/1.2.0 holds 1 commit that 8de0b6e does not, as this checkout last fetched it. Pull, then run purlin:sign.`; `quinn.qa@labconnect.example has already signed 1.2.0 over this package; nothing was written.` |
| The overview (C8) | `Signing 1.2.0: .purlin/evidence/package/1.2.0.json, at 3c9d2e1.`; `  40 rules on Linux/Unix and Windows: 38 pass their tests, 2 are checked by hand.`; `  The audit: 30 strong, 2 weak, 6 not audited.`; `  10 stops: 2 hand checks, 2 weak, 6 not audited.`; `  No stops: nothing is checked by hand, weak or not audited.` |
| The strong list (C8) | `30 rules the audit found strong. list / walk / go on: `; `walk / go on: `; `  sample_age RULE-2, RULE-3` |
| A stop (C8) | the head `sample_age RULE-1   weak` (or `not audited`, `hand check`, `strong`); `Rule`, `Proof`, `    tied to tests/test_age.py::test_age_at_receipt`, the body six spaces in, `      the test's source was not found`; `Results`, `  Windows: passed on remote runner, Windows`; `What the audit found` |
| A stop's answers (C8) | `sample_age RULE-1   continue / note / stop: `; `Your note, in one line: `; `accession_screen RULE-1   what did you see, in one line, or stop: ` |
| Stopping (C8) | `Stopped at sample_age RULE-1: nothing was signed. After the fix, run purlin:test --release, then purlin:sign.` |
| The signature (C8) | `Sign the evidence package for 1.2.0 as quinn.qa@labconnect.example? [y/N] `; `Nothing was signed.`; `Signed 1.2.0 as quinn.qa@labconnect.example with the key ending ...4f2a.`; `Tagged signed/1.2.0 at 8de0b6e.`; `signed/1.2.0 stays at 8de0b6e; this sign-off is added after it. Push it: git push`; `Sign-offs of 1.2.0: quinn.qa@labconnect.example, pat.product@labconnect.example.`; `The sign-off commit was not made: <git's message>. Nothing was signed; run purlin:sign again.` |
| The agent's walk (C9) | `Answer each stop, then run purlin:sign --answers <file>.`; `No sign-off: sample_age RULE-1 has no answer in .purlin/runtime/signoff-answers.json. Answer every stop, then run purlin:sign --answers .purlin/runtime/signoff-answers.json again.`; `No sign-off: <file> cannot be read: <cause>.` |
| The sign-off commit (C6) | `sign(1.2.0): quinn.qa@labconnect.example` |
| The renumbering helper (C10) | `sample_age: PROOF-4 at line 14 becomes PROOF-7: "<text>".`; `... Neither line is on origin/main, so the later one moves.`; `... This checkout has no copy of a default branch, so the later one moves.`; `sample_age: PROOF-6 at line 22 now names RULE-5.`; `tests/test_age.py:22 names sample_age PROOF-4 and moves to PROOF-7.`; `tests/test_age.py:14 names sample_age PROOF-4 and moves to PROOF-6, where its old wording is now.`; `tests/test_age.py:30 names sample_age PROOF-4 and is not committed, so it is not changed: check which proof it means.`; `sample_age: > Highest-Proof: 6 becomes 7.`; `origin/qa/age-proofs names sample_age PROOF-4 at tests/test_age.py:18, which this checkout does not change. If it means the line that moves, move it to PROOF-7 on that branch.`; `Nothing is changed: this is a dry run.`; `Renumbered in sample_age: 1 spec line and 1 test comment. Nothing is committed.`; `sample_age: nothing to renumber.`; the question `Do it? [y/N]` |
| The dashboard (C13) | `Checked by hand when a release is signed, in the walk of purlin:sign.` |
| The spec format and skill, the collision rule (skills) | `When two branches take the same number, the number already on the default branch keeps it, and the rule or proof from the branch not yet merged moves to the next free number. A moved rule's audit is read again; purlin:spec renumbers it and its test comments when you say yes.` |
| The glossary (words) | `**gate**: the one project setting, passed or signed. passed: every rule's tests pass on the evidence committed at the release commit. signed: the same, and at least one person signs the evidence package.`; `**release**: a commit, its evidence package and a tag, made by purlin:test --release on a release branch.`; `**sign-off**: one person's signature over a release's evidence package, a file in a signed commit; the first writes signed/<version>, and later ones are added beside it.`; `**hand check**: a proof marked @manual, which no test runs; at the gate signed a person checks it in the sign-off walk and types what they saw.`; `**strong**: what the AI audit found a rule's tests to be. A tool: nothing waits on it.` |
| `references/hard_gates.md`, lead (words) | `Purlin creates evidence and enforces no policy about who signs. A release is refused only while a rule's tests do not pass at the release commit, a spec cannot be read, the working tree holds uncommitted changes, or the branch's copy on the host holds commits the checkout lacks.` |
| The QA page (docs) | the sections `The sign-off` and `What the package records`; the lead `For a QA person who turns acceptance criteria into proofs and signs the release they cover.` |
| `RELEASE_NOTES.md` 0.10.0 (words) | `**Two gates.** passed: every rule's tests pass at the release commit. signed: the same, and a person signs the evidence package. The gate strong is gone; purlin:init --update reads it as passed.`; `**A release is a commit, a package and a tag.** purlin:test --release runs every test, commits the evidence and the package, and at passed tags passed/<version>. At signed the first purlin:sign writes signed/<version>; later sign-offs are added and the tag does not move.`; `**Nothing is signed while specs change.** Left to do lists only work: proofs and tests to write, tests to fix, rules to strengthen where the audit ran.`; `**The audit and mutation testing are tools.** Nothing waits on them; min_strength is gone.`; `**The sign-off walk shows what to look at.** Each hand check, each weak rule and each rule never audited, with its proofs, its tests' names and bodies, its results and the audit's finding; the rest in a list. The sign-off records what was shown and every note typed.`; `**purlin:spec renumbers a number written twice when you say yes**, with a dry run first.`; the format numbers of C14 |

