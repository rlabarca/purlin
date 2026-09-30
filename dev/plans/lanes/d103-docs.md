# Lane `docs` of decision 103: report

Branch `lane/d103-docs`, from `origin/d103/base` at `e5f82d0`.

## Summary

Every page the lane owns now describes what C1 to C13 build, in section 7's words.
`docs/review-and-signing.md` is rewritten as the release and sign-off page. It covers the
release run and its refusals, a hand check at `passed` (Q1 (a)), the walk with its overview,
strong list, stops and answers, the signature, several signers, the agent's `--show` /
`--answers`, what a sign-off records, when it counts, and a table of both tags.
`docs/qa-guide.md` ends on the sign-off walk, with sections `The sign-off` and
`What the package records`. The flowchart in `docs/regulated-workflow.md` ends on
`purlin:test --release`, `purlin:sign`, `signed/<version>`. `docs/team-workflow.md` is rewritten
for either gate with the audit as a tool, and its `Releasing a version` names the release run.
`docs/raising-the-gate-and-upgrading.md` gives the two gates, setup's C16 choices, six settings
keys, and the mutation question at `signed` alone. `docs/running-and-evidence.md`,
`docs/how-purlin-works.md`, `docs/getting-started.md`, `docs/index.md`, `docs/spec-from-code.md`,
`docs/specs-and-anchors.md` and `docs/working-together.md` no longer have any per-rule signing,
ended signature, not-applying, `strong` gate or `min_strength` line. The deck builder's slide
`strong` is now `audit` ("A tool at either gate"), and the slide `signed` is the release sign-off.

The plan's grep over the lane's files is empty for `--note`, `does not apply`, `ended because`,
`to sign` (as a kind), `min_strength`, and every C12 name. `strong` remains only as the audit's
word. Every relative link on all 13 docs pages resolves.

## Ids

- `specs/instructions/purlin_docs.md`: `> Highest-Rule: 13`, `> Highest-Proof: 18` (from 12 / 17).
  New: RULE-13 (the release page names both tags a release writes, each with the command that
  writes it), PROOF-18 (the page's table of tags has a row for `passed/<version>` naming
  `purlin:test --release` and one for `signed/<version>` naming `purlin:sign`), with its marked
  test `TestReleasePage` in `dev/test_purlin_docs.py`. `> Scope:` and `> Description:` also name
  `docs/review-and-signing.md`.
- Deleted or reworded: none. No proof quoted a deleted line.

## Tests

- `dev/test_purlin_docs.py`: before 10 passed; after 11, of which 10 pass and 1 waits on lane
  `counting` (below).
- Deliberate break: removed the `signed/<version>` row from `docs/review-and-signing.md`; PROOF-18's
  test failed (`['signed/<version>: purlin:sign'] != []`); restored with
  `git checkout -- docs/review-and-signing.md`; it passed again.
- `bash dev/run_tests.sh --fast`: 4 failed, 2207 passed, 9 skipped, 1 error. Apart from PROOF-5,
  every failure is in a file this lane does not own and comes from the cloud container (below).

## Waiting for another lane

- PROOF-5 (`test_the_confirmed_runs_lines_are_printed_by_it`) needs lane `counting`.
  `docs/getting-started.md` quotes C3's last line,
  `Nothing left to do. To release a version: purlin:test --release`, under the `confirmed-run`
  sample. Today's run prints `Nothing left to do.`. It passes once `counting` merges.

## Failures in files the lane does not own

- `README.md` (lane `words`): its `confirmed-run` sample quotes `Nothing left to do.`, so PROOF-5
  fails at README.md once `counting` merges unless `words` changes it to C3's line.
- `dev/test_tag.py::TestTheTag::test_the_tag_is_signed_with_the_key_the_settings_name` fails
  because of the container. Its global git config sets `gpg.ssh.program=/tmp/code-sign`, which
  refuses `git tag -v`.
- `dev/test_signatures.py::TestTheMachines` has 2 failures. They expect `macos` as the machine's
  system and read `linux` here.
- `dev/test_states.py::TestStatusTable::test_the_table_and_the_dashboard_show_the_same_cells`
  errors because the browser does not launch.
- `references/writing_style.md` still has two lines with the gate `strong`: "which closes a
  finished project at the gates `passed` and `strong`" and the definition shape
  "`passed`, `strong` or `signed`". No lane owns it, so it is left to integration.

## Calls left, and words chosen that section 7 does not give

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
