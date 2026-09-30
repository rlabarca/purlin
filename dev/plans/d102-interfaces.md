# Decision 102: what was built

The plan is `d102-plan.md`. Eight lanes built it in cloud sessions on Linux, each on
`lane/d102-<lane>` from `d102/base`, and one integration merged them into `d102/base` by
fast-forward on the owner's Mac on 2026-09-30, in the order reader, counting, drift, signing,
run, dashboard, skills, words. Each lane's own report is `dev/plans/lanes/d102-<lane>.md`. This
file says where the build differs from the contracts, the ids each spec now stands at, the test
counts, and every word a lane chose that section 7 does not give.

## Where the build differs from the contracts

- **Reader (C1, C2).** As the contracts give it. A proof id written twice under two rules still
  lists the id in `proofs_by_rule` under both rules, while `proofs[id]['rules']` holds the last
  line's rules alone; the spec reads `failed` until it is fixed. `spec_format.md` stays at 21.
- **Counting (C3 to C6).**
  - The signed cell keeps `waiting` (RULE-73, PROOF-94) when a signature ended and the strong
    cell is not met: `ENDED` replaces the reason only where the cell reads `unsigned`. The ended
    line prints in the status at every gate either way.
  - Where a newer signature binds but does not count, the cell keeps that signature's reason
    (RULE-22), not `ENDED`.
  - Where the newest counting signature no longer binds and no compared field differs (a
    `signed_hash` made under an older binding), no ended line and no reason print.
  - A rule of a broken spec still computes and prints `ended`; its strong cell reads `waiting`
    with `waiting for its tests to pass`, its signed cell `waiting` with `waiting for the audit`.
  - The kind compared for a hand check comes from the rule's current `test_hash_kind`, else the
    signature's; `payload.py` passes `test_hash_kind` into `rule_cells`.
  - `CAUSE_TEST` for a rule that names no test file reads `a test file behind it changed: none`.
- **Drift (C7).**
  - The age reads the reflog entry's own time (`git reflog show -1 --date=unix --format=%gd`),
    not `%ct`, which is the time of the commit the entry points at.
  - Several numbers written twice in one spec each take the next number after the one before.
    With more than two lines under one id, the first line that is not the keeper moves. "The
    default branch writes it twice too" quotes the checkout's last line under that id. A spec
    absent on the default branch takes the second form ("neither line is on").
  - A proof moved and then reworded is listed as moved and as changed. A move target must be an
    id that did not already hold that text at the range's start.
  - Test comments are read with `git blame` on the working tree; a line not yet committed is
    skipped, and so is a comment whose proof is absent now or at the blamed commit.
  - The age line prints only beside a number written twice and a default branch; `default_branch`
    is in the JSON of every view.
  - JSON shapes: `numbers_twice` `[{feature, id, to, text, line}]`; `comments_changed`
    `[{file, line, feature, id, commit, old, new, now_under, text}]`.
  - `references/drift_criteria.md` went from Criteria-Version 10 to 11. PROOF-49 held three cases;
    its `eng` and `qa` keys moved to the new PROOF-79 and PROOF-80.
- **Signing (C8 to C11), under the owner's answer (a).**
  - `is_current` takes the kind from the rule's current entry, or from its proofs where the
    entry carries none. A signature made under format 12 over a hand check ends once, on upgrade.
  - An SSH block is checked with `ssh-keygen -Y check-novalidate`, any other with
    `git verify-commit`. The `gpgsig` header is read among the headers alone
    (`gpgsig-sha256` for a 64-character id).
  - A broken spec is refused before the key check. A detached HEAD skips the check against the
    host copy; the host copy is `@{upstream}`, else `origin/<branch>`, else no check.
  - PROOF-201 differs from the plan: a proof with no test cannot be a walk stop at `signed`, so
    the proof gives `RULE-2` an untested `PROOF-3` and the test renders its stop.
  - RULE-6, RULE-61 and RULE-90 now begin "A signature that is not a hand check's"; RULE-20
    says the commit's signature verifies. PROOF-179's anchor proof is no longer `@manual`.
- **Run (C13 and the run's part of C3).**
  - `--test` and `--audit` exit 1 on a broken spec after every test has run and printed; `--ci`
    does not (RULE-12: it exits on its tests alone). `--audit` reads no rule of a broken spec.
  - A conflicted evidence file's recovery keeps audit entries alone; another system's sections
    are written again by that system's next run. The evidence format stays at 7.
  - RULE-11 and RULE-69 of `run_script` reworded so they do not contradict RULE-87.
- **Dashboard.** The ended signature is in the regulated sample (login `RULE-2`, by
  `sam@acme.com`), not the team sample: the team sample's gate is `strong`, where no signed cell
  shows. The team sample gained the spec `refund` (2 rules, `PROOF-2` written twice). The rule's
  screen already draws every reason in its row, so neither reason needed code.
- **Skills.** `skills/sign/SKILL.md` stands at 184 of 185 lines: the `Left to do` example of
  Step 2 became one inline example and Step 7 dropped the `Signed 8 rules as ...` line. The
  release-branch sentence is section 7's first alone. The quality guide's `Manual proofs`
  paragraph no longer says a scope change ends a hand check's signature.
- **Words.** `docs/qa-guide.md` is new, first under QA in `docs/index.md`, with a pointer from
  `README.md`. `docs/team-workflow.md` gained `Releasing a version`.
- **At integration**, six commits beyond the lanes, then the page rebuilt (`979bd73cc`); the two
  docs screenshots, retaken, came out byte for byte the same, so they were not committed:
  - `spec(schema_spec_format)`: RULE-14's tail and PROOF-55 quote C5's line, which the status
    now prints for a `> Scope:` that finds no file.
  - `test(drift)`: PROOF-78's test runs the tests and the audit again after the edit, as the
    states tests of C4 do; otherwise the ended line also names the audit and `macOS has no
    results any more`, as C4 says it must.
  - `test(drift)`: the role test reads the default branch's age once, as it already read the
    reflog once; two reads a moment apart straddled a second under load.
  - `test(states)`: PROOF-82's full payload carries a signature on `RULE-2` made over wording it
    no longer has, so the builder writes `ended` as the schema 12 fixtures do.
  - `chore`: the three `getattr` stand-ins for C1 and C4 are direct calls, and
    `scripts/run/evidence.py` reads conflict lines with `specs.CONFLICT_RE` (one pattern).
  - `docs`: `docs/getting-started.md` adds `no file named test_*.py under tests/` to the no-tool
    case (C13); `docs/how-purlin-works.md` says an ended signature prints a line and a hand
    check is bound to wording alone.
- No frozen file changed.

## Ids

| Spec | Highest-Rule | Highest-Proof |
|---|---|---|
| `specs/mcp/schema_spec_format.md` | 37 (was 34) | 85 (was 80) |
| `specs/mcp/specs.md` | 21 | 43 |
| `specs/mcp/states.md` | 105 (was 101) | 259 (was 247) |
| `specs/mcp/summary.md` | 16 (was 15) | 41 (was 39) |
| `specs/skills/skill_status.md` | 11 | 35 |
| `specs/mcp/drift.md` | 34 (was 27) | 80 (was 66) |
| `specs/skills/skill_drift.md` | 12 (was 10) | 38 (was 36) |
| `specs/review/signatures.md` | 101 (was 95) | 201 (was 189) |
| `specs/export/package.md` | 28 (was 27) | 60 (was 59) |
| `specs/run/run_script.md` | 89 (was 86) | 264 (was 260) |
| `specs/run/evidence_writer.md` | 26 | 89 |
| `specs/dashboard/purlin_report.md` | 68 (was 65) | 217 (was 214) |
| `specs/skills/skill_spec.md` | 28 (was 24) | 58 (was 54) |
| `specs/skills/skill_sign.md` | 28 (was 24) | 58 (was 53) |
| `specs/instructions/purlin_docs.md` | 12 | 17 |

Nothing deleted. Reworded: schema_spec_format RULE-14, PROOF-55; states RULE-20, RULE-27,
RULE-64, PROOF-31, PROOF-72, PROOF-96; skill_status PROOF-24; drift PROOF-49; signatures
RULE-6, RULE-9, RULE-20, RULE-61, RULE-90, PROOF-13, PROOF-179; run_script RULE-11, RULE-69;
purlin_report PROOF-20, PROOF-94, PROOF-213; skill_spec RULE-17, PROOF-46; skill_sign RULE-5,
PROOF-5.

Formats: `signature_format.md` 13, `package_format.md` 6, payload `schema_version` 12,
`spec_format.md` 21, `evidence_format.md` 7, `drift_criteria.md` Criteria-Version 11.

## Test counts

- Full sweep on `d102/base` at `979bd73cc`, `bash dev/run_tests.sh`: **2411 passed, 3 skipped in
  887.54s**, `>>> All Pytest Tests: PASSED`, `Suites: 5 passed, 0 failed`; the four shell suites
  passed. The 3 skips are the Windows-only tests. Before decision 102 the `--fast` sweep on the
  Mac read 2154 passed, 3 skipped.
- Each lane's `--fast` on the Mac after its rebase: reader 2159 passed; counting 2171 passed, 2
  failed; drift 2186, 3 failed; signing 2200, 2 failed; run 2204, 4 failed; dashboard 2207, 1
  failed; skills 2216, 1 failed; words 2217 passed. Every failure was one the plan expects between
  merges (states PROOF-82 and PROOF-96 until dashboard; purlin_docs PROOF-8 from run until
  words), except drift's role test, which straddled a second under load and is fixed at
  integration. The macOS-only, dotnet and browser tests the lanes could not run pass here.
- `python3 scripts/run/purlin_run.py --test --all`: `Markers: 2453 tied to a test, 0 not tied.`,
  `Ran pytest, shell on 36 features.`, `87 proofs need Windows; this machine is macOS. Run
  purlin:test --remote.`, then `957 rules. 870 pass their tests. 0 are strong. 0 are signed.`
  and `Left to do:` / `  87 rules to test on Windows: purlin:test --remote` / `  870 rules to
  audit: purlin:audit`. No rule reads `failed`, `partial` or `no test`, no spec to repair,
  and no warning prints. With `--commit` the same lines and `Evidence committed.`.
- Lane test files, before and after, as each lane reported: reader 72 to 77 (schema_spec_format)
  and 40 to 40 (specs reader); counting 259 to 273; drift 77 to 93; signing 197 to 210; run 286
  to 292; dashboard 198 to 201; skills 53 to 62; words 10 to 10.

## Words chosen by a lane, word for word

### reader

- RULE-35 `A proof number written twice is warned of, and the proof is read once, with the text of its second line`; RULE-36 `A line left from a merge conflict is warned of with its line number`; RULE-37 `The reasons a spec's rules fail are named in order: each rule number written twice, then each proof number written twice, then a line left from a merge conflict`.
- `spec_format.md`: `A line left from a merge conflict, one opening with seven <, =, > or | followed by a space or the line's end, is warned of with its line number, and every rule of the spec reads failed, with the reason ..., until it is taken out. A line of eight = is not one. The spec is otherwise read as written, both sides' lines included.`; `... until one of the two lines is renumbered.`; `A line left from a merge conflict fails the spec wherever it stands in the file, as "Rules format" says.`

### counting

- `none`: the file list of `CAUSE_TEST` for a rule that names no test file, giving `a test file behind it changed: none`.
- The status skill's closing table adds `<n> specs to repair` to its `purlin:spec` row.

### drift

- Drift criteria: the section `### Every view`, its paragraphs and its case table.
- The skill: `Drift reads only this checkout: it never fetches, pulls or reaches the host. When it names a number written twice it also says how old this checkout's copy of the default branch is. If that copy is old, run git fetch, then run drift again.`
- The skill, `A number written twice`: `The line already on the default branch keeps the number; the other line moves to the number drift names. Renumber that line with purlin:spec <feature>, move the test comments that name it, and tell the person whose line moved so the comments on their branch move with it.`
- The skill's closing rows: `A proof added, changed or moved` → `→ Run: purlin:build <feature>`; `A signature that ended` → `→ Run: purlin:sign`; `A number written twice` → `→ Run: purlin:spec <feature>`; `A test comment whose proof's wording changed` → `→ Run: purlin:build <feature>`; `How old the copy of the default branch is` → `→ Run git fetch, then purlin:drift again.`

### signing

- No printed line beyond section 7. The rule wording in `specs/review/signatures.md` and `specs/export/package.md` is the lane's own.

### run

- No printed line. The texts of run_script RULE-87 to RULE-89 and evidence_writer RULE-26 and their proofs follow section 4.

### dashboard

- RULE-66 `A spec that writes a number twice or holds a line left from a merge conflict is a spec to repair, and To repair is a filter button where the payload lists the kind to_repair; choosing it leaves that spec's rules alone`; RULE-67 `A rule whose signature ended says on its screen who signed it and why the signature ended`; RULE-68 `A rule of a spec to repair says on its screen why its tests' result does not count`.
- `docs/dashboard.md`: `1 spec to repair is To repair, which shows the rules of each spec that writes a number twice or holds a line left from a merge conflict`; `Every rule of a spec to repair reads failed in its passed row with the reason, such as PROOF-2 is written twice in the spec, whatever its tests found. A rule whose signature ended reads unsigned in its signed row with the cause, ...`.
- The fixture `refund`: `A refund returns the amount paid to the card it came from.`, `A refund of an order already refunded is refused.` and their proofs.

### skills

- Sign skill, Step 3: `Under each proof that is not @manual it shows the test tied to it, ... or     tied to no test: read that test before you answer.`
- Step 4: `A feature whose spec writes a number twice or holds a line left from a merge conflict is refused too: the script prints <SPEC_REFUSED filled for login>, writes nothing and exits 1. The walk and --all never reach its rules.`
- Step 5's table, the first row's ends cell: `the commit that added it is not signed`; `the signature on the commit that added it does not verify`.
- Step 6: `It exits 1 too on a broken spec, <NO_TAG_SPEC filled>, and while the branch's copy on the host, as last fetched, holds commits this checkout lacks: <NO_TAG_BEHIND filled>. It never fetches.`
- Step 7's rows: `No tag: <feature> cannot be counted:` or `<feature> is not signed:` → `→ Run: purlin:spec <feature>`; `No tag: <ref> holds <n> commit(s) that <sha> does not` → `→ Pull, then run: purlin:test --commit`.
- The quality guide's stuck row: `passed` | `failed`, with `<RULE-N or PROOF-N> is written twice in the spec` or `the spec holds a line left from a merge conflict` | `The spec writes a number twice or holds a line git left from a merge conflict, so every rule of it reads failed whatever its tests show.` | `purlin:spec: renumber the line from the branch not yet merged, or take out the conflict lines.`
- The `unsigned` row gains `A signature that ended says so: the signature by <signer> ended because <cause>.`

### words

- Headings: `Releasing a version` (`docs/team-workflow.md`); `Your criteria become proofs`, `What the developer adds`, `The walk`, `The signature`, `What ends a signature`, `Drift after a pull`, `Where the risk is` (`docs/qa-guide.md`), with its opening paragraph naming the five steps.
- `tied to no test means no test carries that proof out yet.`
- `Read the cause, look at what changed, and sign again when the rule still holds.`
- `On release/1.2.0 the tag keeps up with origin/release/1.2.0.`; `On a release branch the ref is that release branch's, so the default branch moving on does not stop the tag.`
- `A hand check is a rule whose every proof is @manual or has no test.`; `The walk names each test; open the file to read its body.`
- `Move the test comments that name the moved id with it.` (`docs/specs-and-anchors.md`)
- `references/hard_gates.md`: `**Purlin refuses nothing a person does, with one exception.**`
- The glossary's `to repair` definition and the `to_repair` row's "When it applies".
- `docs/index.md`'s description of the QA page; `README.md`'s pointer line.
- The regulated flowchart's nodes `a spec to repair?`, `No tag: a feature cannot be counted`, `the branch on the host holds commits you lack?`, `No tag: pull, then purlin:test --commit`.
- `RELEASE_NOTES.md`: `A version is signed on a release branch...` and `When two branches take the same number...`.

### integration

- `docs/getting-started.md`: `... no [tool.pytest section in pyproject.toml and no file named test_*.py under tests/, it prints:`
- `docs/how-purlin-works.md`: `A change to any of the six ends it: the status prints one line naming the rule, the signer and why it ended, its cell reads unsigned, and the rule is left to do as to sign. A hand check's signature is made over the rule's and its proofs' wording alone.`

## Words chosen for the owner to read

Section 7 of `d102-plan.md`, as it was built:

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

