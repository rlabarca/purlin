# Lane `words`, decision 103

Branch `lane/d103-words`, made from `origin/d103/base` at `e5f82d0`. Files written: the ones section
4 L9 gives, and nothing else.

## Highest lines after the work

| Spec | Highest-Rule | Highest-Proof |
|------|--------------|---------------|
| `specs/instructions/purlin_agent.md` | 17 (was 16) | 48 (was 47) |
| `specs/instructions/purlin_version.md` | 16, unchanged | 38, unchanged: no line names per-rule signing |

## Tests

- `dev/test_purlin_agent.py`: 10 passed before, 11 passed after (PROOF-48's test is new).
- Text tests beside it, run whole after the work: `dev/test_vocabulary.py` and every
  `dev/test_skill_*.py`: 255 passed with `test_purlin_agent.py`.
- `bash dev/run_tests.sh --fast`, after: 2206 passed, 5 failed, 1 error, 9 skipped. Before (a
  run that started on `e5f82d0` while this lane's first edits landed): 2204 passed, 6 failed,
  1 error. The after-run's failures:
  - `dev/test_purlin_docs.py`, two tests: listed below, one waiting on lane `counting`, one a
    link in lane `docs`'s page.
  - `dev/test_signatures.py::TestTheMachines` (2 tests) and
    `dev/test_tag.py::TestTheTag::test_the_tag_is_signed_with_the_key_the_settings_name`: the
    cloud container's git configuration names its own signing program
    (`environment-runner code-sign`), which the tests' signed commits reach; failed identically
    before this lane's work. Lane `signoff` and `release` own these files.
  - `dev/test_states.py::TestStatusTable::test_the_table_and_the_dashboard_show_the_same_cells`
    errors: the pip `playwright` wants `chromium_headless_shell-1243`, which `/opt/pw-browsers`
    lacks (section 5). Same before.

## Rules and proofs, `purlin_agent`

- Reworded: RULE-2 (the loop is `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:test`,
  `purlin:test --release`, `purlin:sign`; `purlin:audit` leaves the chain and is named as a
  tool), RULE-3 (a sign-off, not a signature, in NEVERs 1 and 2), RULE-5 (the two cells `passed`
  and `strong`), RULE-7 (a rename moves three places: the signature directory is gone).
- Proofs reworded: PROOF-2, PROOF-3, PROOF-5, PROOF-7, PROOF-11 (the summary is C3's
  `40 rules. 35 pass their tests. The audit found 30 strong and 2 weak.`).
- New: RULE-17, PROOF-48: the agent says nothing is signed while the specs change, that
  `purlin:test --release` tags `passed/<version>` at `passed`, and that the first sign-off
  writes `signed/<version>`.
- Deleted: none.
- Deliberate break: ` 30 are strong.` put back in the agent's summary example;
  `TestLeftToDo::test_it_says_every_run_ends_on_left_to_do` (PROOF-11) failed; restored with
  `git checkout -- agents/purlin.md`; 11 passed.

## What each file now says

- `references/hard_gates.md`: the lead of section 7; "The two gates" (C1, the two cells, the
  audit and the breaks as tools, test strength as `strength 84%`); "When a version is finished"
  (C3's summary, the eight kinds with a column for which stop a release, the three last lines);
  "The release" (C5's checks in order with their lines, the version, the package, the tag at
  `passed`, C13's hand-check line, `READY_TO_SIGN` at `signed`); "Which evidence counts" (the
  evidence at the release commit, either source); the runner section (a `passed/*` tag starts no
  run); "When a sign-off counts" (C6, and the walk in one paragraph); "What the tags mean" (both
  tags, the message). "The three steps", "When a signature counts", "CI writes no signature
  file", the not-applying and hand-check-binding sentences and the `min_strength` table are
  gone.
- `references/glossary.md`: `gate`, `release`, `sign-off`, `hand check`, `strong` in section 7's
  words; `evidence package`, `tag`, `version`, `cell`, `summary`, `Left to do` and the chain
  rewritten to two cells; `step`, `signature`, `audit hash`, `counting signature`,
  `does not apply` and the deleted kinds gone.
- `references/purlin_commands.md`: the Core rows for `purlin:test` (gains `--release`) and
  `purlin:sign`; the syntax block's `Releasing` group; what each writes; the gate section; the
  exit codes of `purlin_run.py` and `sign.py` (C8); the release and sign-off refusals.
- `references/commit_conventions.md`: `sign(<version>): <signer email>` replaces both `sign(...)`
  rows; the package row names `purlin:test --release`; "The release commit", "The sign-off
  commit" and "The tags" (both).
- `agents/purlin.md`: 132 lines of 135.
- `CLAUDE.md`: step 3 and the two rows, as section 4 gives them, with machine text in backticks.
- `README.md`: two gates, the release run, the Core rows as the reference gives them, the finished
  run's last line.
- `RELEASE_NOTES.md` 0.10.0: section 7's seven lines, the format numbers of C14; decision 102's
  entries (ended signatures, the hand check's binding, signing refused, the tag refused, the
  signing walk) replaced; `--does-not-apply`, `min_strength`, `strong` as a gate, the unscoped
  signature, per-rule signing and the upgrade's `strong` default replaced.

## Words chosen that section 7 does not give

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

## Calls left

- `CLAUDE.md`'s `package_format.md` row still says `purlin:export and purlin:sign write`; the
  plan gives this lane only the two rows, so it is left. It should read
  `purlin:export and purlin:test --release`.
- `CLAUDE.md` line 34 names "signature" in the list of parsings that bump a format; left, since
  the sign-off is still `signature_format.md`.

## Failures in files this lane does not own

- `dev/test_purlin_docs.py::TestLinks::test_every_relative_link_names_a_file_and_a_heading`:
  `docs/how-purlin-works.md` links `../references/hard_gates.md#the-three-steps`, a section
  decision 103 deletes. Lane `docs` owns the page. Also stale, in pages the test does not read:
  `docs/running-and-evidence.md` links `#when-a-signature-counts` and
  `#what-signedversion-means`; the sections are now `#when-a-sign-off-counts` and
  `#what-the-tags-mean`.
- Text naming sections that are gone: `references/spec_quality_guide.md` (lane `skills`) and
  `references/review_criteria.md` (lane `run`) cite `hard_gates.md`, "The three steps";
  `skills/audit/SKILL.md` cites "under the gate table" for strength, now under "The two gates".

## Tests that fail only because another lane has not merged

- `dev/test_purlin_docs.py::TestQuotedLines::test_the_confirmed_runs_lines_are_printed_by_it`:
  the README's finished run now quotes
  `Nothing left to do. To release a version: purlin:test --release` (C3), which the run prints
  once lane `counting` merges.
