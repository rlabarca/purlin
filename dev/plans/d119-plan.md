# Decision 119: the remote runner goes; the build plan

Written by the planning agent on 2026-10-01, read only, and recounted against local `main` at
`6932cf30c`: decision 118 is committed, the tree is clean, 39 specs, 423 rules, 860 proofs. The
owner's three answers are folded in (section 9).

**The decision.** Purlin runs the tests where you are. It starts no run on another machine,
drives no pipeline and adds no file for a git host to a project. A project's run on another
system is that project's own setup, written for it by the AI on request. Purlin keeps the
`@env(<system>)` tag, the evidence from more than one machine, the status line
`22 rules to test on Windows`, the dashboard's per-system boxes and the sign-off's check that a
result was taken on the version being signed.

Decision 44 binds: what goes is deleted outright with its tests and fixtures, no compatibility
reader, no test that a removed thing is absent, no table of removed words.

## 0. What a run on another system is, after this

One line in the project's own pipeline, on the other system:

```
python3 <purlin>/scripts/run/purlin_run.py --ci --commit
```

then the pipeline's own `git push`. `--ci` is what is left of today's `--ci` arm:

| Kept | Gone |
|---|---|
| It starts only the tests of the proofs tagged `@env` for this machine's system, and exits on those alone | The commit through the git host's REST API, its retries, its pauses and its merge (`host.py`) |
| It writes this system's section of `.purlin/evidence/ci/<feature>.json`, each rule with its own result | The run-branch rule: it now writes on whatever branch it runs |
| The source `ci`, one file per feature per source | `machine` reading `remote runner, <System>`, and the field `hostname` |
| It starts slow tests like `--all` (decision 118) and calls no model | The checkout check of `ci.py` |

New: `--commit` is accepted with `--ci`. It makes one ordinary git commit of the files under
`.purlin/evidence/ci/`, as `purlin: evidence at <sha7>`, under the git identity the pipeline
set. Purlin never pushes. A `ci` section now has the same fields as a `local` one: `machine` is
the host's name, `email` is the checkout's git email, `runner` is its slug.

Why only the tagged proofs, and not an ordinary whole run: `dev/plans/windows-untagged-failures.txt`
records 78 of this repository's 1,979 tests failing on Windows with no rule tagged for them. A
whole run there would turn those rules `partial`. The settled meaning of `@env` holds: an
untagged proof is proven where a person is.

## 1. The count

| | Now | Goes | Reworded | Added | After |
|---|---|---|---|---|---|
| Specs | 39 | 1 (`host`) | 15 | 1 (`windows_run`) | 39 |
| Rules | 423 | 17 | 24 | 4 | 410 |
| Proofs | 860 | 46 | 37 | 6 | 820 |

Per spec:

| Spec | Rules gone | Rules reworded | Rules added | Proofs gone | Proofs reworded | Proofs added |
|---|---|---|---|---|---|---|
| `host` (deleted whole) | 15: 55, 8, 49, 40, 50, 27, 56, 22, 12, 51, 30, 31, 52, 53, 54 | | | all 42 | | |
| `run_script` | 97 | 98, 8, 10, 96, 59, 17, 12 | | 272, 273 | 10, 12, 117, 17 | |
| `evidence_writer` | | 1, 3, 16, 17, 27 | 33 | 44 | 78 | 95, 96 |
| `evidence` | | 35 | | | 19 | |
| `summary` | | 23 | | | 8, 33, 56 | |
| `package` | | 32 | | | 25, 66, 67 | |
| `signatures` | | | | | 226 | |
| `scaffold` | 81 | | | 173 | | |
| `update` | | 53 | | | | |
| `skill_test` | | 23 | | | 55, 52 | |
| `skill_status` | | 16 | | | 37 | |
| `skill_sign` | | 35 | | | 63 | |
| `purlin_agent` | | 18 | | | (49's test list changes, its words do not) | |
| `windows_run` (new) | | | 1, 2, 3 | | | 1, 2, 3, 4 |

Reworded for "remote anchor" alone (answer 2): 4 rules and 20 proofs.

| Spec | Rules reworded | Proofs reworded |
|---|---|---|
| `upstream` | 8, 36 | 8, 48, 9, 30, 32, 34, 57, 33, 11, 45, 60 |
| `drift` | 10 | 17, 40, 20, 42, 44, 56, 88 |
| `schema_spec_format` | 38 | 78 |
| `states` | | 231 |

`purlin_report` and `specs` are not touched.

**Proofs tagged `@env(windows)`.** 22 now. `host PROOF-117` and `PROOF-118` go with their spec.
20 stay: `upstream` 3 (46, 48, 50), `package` 1 (39), `scaffold` 3 (130, 132, 136), `update` 3
(117, 118, 120), `config_engine` 2 (38, 39), `evidence` 3 (71, 84, 75), `server` 2 (159, 160),
`states` 1 (218), `ai_audit` 1 (82), `run_script` 1 (229).

**Code.**

| Deleted (6) | `scripts/run/remote.py`, `scripts/run/host.py`, `scripts/run/workflow.py`, `scripts/run/ci.py`, `templates/purlin.yml`, `templates/purlin.azure-pipelines.yml` |
|---|---|
| Changed (9) | `scripts/run/purlin_run.py`, `scripts/run/evidence.py`, `scripts/mcp/purlin/evidence.py`, `scripts/mcp/purlin/summary.py`, `scripts/export/package.py`, `scripts/review/sign.py`, `scripts/init/update.py`, `scripts/init/scaffold.py` (docstring), `templates/evidence-readme.md` |
| Moved (2) | `.github/workflows/purlin.yml` to `.github/workflows/windows.yml` (`git mv`, trimmed); the GitHub half of `scripts/run/remote.py` to `dev/windows_run.py` (new file, salvaged) |

**Tests.** 46 test functions deleted, 18 rewritten, 6 added; and each test under the 20 proofs reworded for "remote anchor" is changed with its proof, in lane `anchors`.

| | Files |
|---|---|
| Deleted whole (4 files, 42 tests) | `dev/test_host.py` (31), `dev/test_remote.py` (7), `dev/test_consumer_ci.py` (3), `dev/test_host_pathspec.py` (1) |
| Deleted in place (4) | `dev/test_run_script.py`: the tests of PROOF-272 and 273; `dev/test_evidence_writer.py`: PROOF-44; `dev/test_init_scaffold.py`: PROOF-173 |
| Rewritten (18) | `dev/test_run_script.py` 4 (PROOF-10, 12, 117, 17) and its helpers `evidence_run`, `commit_files`, `go`, `_ci`; `dev/test_evidence_writer.py` 1 (78) and `_section`; `dev/test_evidence_reader.py` 1 (19); `dev/test_summary.py` 3; `dev/test_export.py` 3 and `section`; `dev/test_signatures.py` 1 and `section`; `dev/test_skill_test.py` 2; `dev/test_skill_status.py` 1; `dev/test_skill_sign.py` 1; `dev/test_purlin_agent.py` 1 |
| Added (6) | `dev/test_evidence_writer.py` 2 (95, 96); `dev/test_windows_run.py`, new, 4 |
| Other `dev/` | `dev/manual/check_azure_remote.py` deleted, `dev/manual/README.md` loses its row and paragraph; `dev/mcp_project.py` and `dev/sign_project.py` changed once in the base commit; `dev/fixtures/report/{regulated,team,solo}.json` reworded; `dev/fixtures/consumer-ci/` (untracked, a `__pycache__` only) removed from disk |

**Docs, skills, references, templates, formats (36 files).**
Docs (11): `README.md` and every page under `docs/`: the 9 the removal changes
(`running-and-evidence.md`, `getting-started.md`, `working-together.md`, `how-purlin-works.md`,
`sign-off.md`, `index.md`, `specs-and-anchors.md`, `upgrading.md`, `README.md`) and, for the
plain-language pass alone, `audit.md` and `dashboard.md`.
Skills (5): `test`, `build`, `status`, `sign`, `init`. Agent (1): `agents/purlin.md`.
References (6): `purlin_commands.md`, `evidence_and_signoff.md`, `glossary.md`,
`commit_conventions.md`, `spec_quality_guide.md`, `writing_style.md`. Formats (3): `evidence_format.md`,
`package_format.md`, `marker_format.md`. Templates (3): two deleted, `evidence-readme.md`
changed. Also `CLAUDE.md`, `RELEASE_NOTES.md`, `dev/plans/three-levels.md`, `dev/plans/handoff.md`,
`dev/plans/deck/build_deck.py`, `dev/manual/README.md`, `docs/images/*.png` (retaken).

## 2. The specs, word for word

Written by the coordinator in the base commit (section 3). No lane edits a file under `specs/`.

### `specs/run/host.md`: deleted.

### `run_script`

Description, its second sentence: `` `purlin:test` runs it as `--test`, `purlin:audit` as `--audit`, and a project's own run on another system as `--ci`, which runs only the tests of the proofs tagged for that machine's own system. ``

- RULE-98: The command line names exactly one of `--test`, `--audit` and `--ci`, at most one of `--all` and `--feature`, only features a spec under `specs/` has, and a `--project-root` that is a directory. Each refusal exits 2 and prints one `purlin:` line naming what is wrong and, where there is one, the command to run instead, and a command line of the wrong shape also prints the usage line; `--help` or `-h` prints the usage line and exits 0
- RULE-8: as now, its last clause reading: under `--ci` only the markers of the proofs tagged `@env` for this machine's system count
- RULE-10: A proof the spec tags `@env` for another operating system is not counted here and is never reported missing; the run prints one line per such system, `1 proof needs <system>; this machine is <system>. Run purlin:test on <system>.` or `<n> proofs need <system>; this machine is <system>. Run purlin:test on <system>.`, each system as `Windows`, `macOS` or `Linux/Unix`, counting only the proofs a test is tied to, and a proof tagged for this one is counted like any other
- RULE-96: as now, opening `Every `--test` and `--audit` run prints`
- RULE-59: `--all` runs every feature whatever its evidence says, and `--ci` with no feature named runs every feature that has a proof tagged for this machine's system
- RULE-17: `--test` and `--audit` write nothing under `.purlin/evidence/ci/`; only `--ci` writes there
- RULE-12: `--ci` covers only the features that have a proof tagged `@env` for this machine's system and writes, for each, this system's section of `.purlin/evidence/ci/<feature>.json`, listing those proofs alone and the rules they prove, on whatever branch it runs, and prints `Evidence written to .purlin/evidence/ci/<feature>.json.`, or `to .purlin/evidence/ci/ for <n> features.` where several ran; it writes nothing under `.purlin/evidence/local/`, and exits 1 when a test tied to one of those proofs failed or could not run and 0 otherwise, whatever else it found, a test tied to no such proof included
- RULE-97: deleted, with PROOF-272 and PROOF-273
- PROOF-10 (RULE-10): as now, its printed line reading `1 proof needs <that system>; this machine is <this system>. Run purlin:test on <that system>.`
- PROOF-12 (RULE-12): In a git checkout, `--all --ci` over one proof tagged for this machine's system writes `.purlin/evidence/ci/feat.json` with one section, for that system, whose `machine` is this machine's host name and whose `RULE-1` reads `passed`, prints `Evidence written to .purlin/evidence/ci/feat.json.`, writes nothing under `.purlin/evidence/local/`, makes no commit, and exits 0
- PROOF-117 (RULE-12): When `.purlin/evidence/ci/feat.json` on disk holds only another system's section, `--all --ci` leaves that section as it was and adds this machine's beside it
- PROOF-17 (RULE-17): In a git checkout, `--all --test --commit` prints `Evidence committed.` and writes nothing under `.purlin/evidence/ci/`

`> Highest-Rule: 106` and `> Highest-Proof: 280` stay.

### `evidence_writer`

Description gains: `` A project's own run on another system, `--ci`, writes that system's section of `.purlin/evidence/ci/<feature>.json` the same way and, with `--commit`, commits those files alone. ``

- RULE-1: as now, with `in a `local` section the `email` RULE-27 gives` reading `the `email` RULE-27 gives`
- RULE-3: as now, with `the runner's own system` reading `this machine's own system`
- RULE-16: Each section names where its tests ran: `machine` reads the host's name, or `unknown` where the host reports none, under either source
- RULE-17: A section that differs from the one on disk in its `machine` alone replaces it
- RULE-27: Every section carries `email`, the `git config user.email` of the checkout the run was made in, or `unknown` where git has none; it is kept and never compared
- RULE-33 (new): With `--commit` a `--ci` run makes one commit, carrying the files under `.purlin/evidence/ci/` and any evidence file the run removed and nothing else, under the git identity set in that checkout, with the subject `purlin: evidence at <sha7>` naming HEAD when the run started, and prints `Evidence committed.`; where nothing is new it prints `Evidence unchanged.` and makes no commit; it never pushes
- PROOF-44: deleted
- PROOF-78 (RULE-16): In a git checkout whose git email is `runner@example.com`, the section a `--all --ci` run writes holds exactly `commit`, `dirty`, `at`, `runner`, `email`, `machine`, `fingerprint`, `rules` and `proofs`, its `machine` this machine's host name and its `email` `runner@example.com`
- PROOF-95 (RULE-33): In a git checkout whose git name is `Runner` and email `runner@example.com`, with one proof tagged for this machine's system and an edit to `README.md` not committed, `--all --ci --commit` prints `Evidence committed.`; the newest commit, authored by `Runner`, reads `purlin: evidence at <sha7>`, naming HEAD before the run, and changes exactly `.purlin/evidence/ci/feat.json`
- PROOF-96 (RULE-33): In a git checkout whose `main` has been pushed to a remote on disk, `--all --ci --commit` made a second time prints `Evidence unchanged.` and adds no commit, and the remote's `main` is still the commit pushed before

`> Highest-Rule: 33`, `> Highest-Proof: 96`.

### `evidence`

- RULE-35: as now, ending `naming its path, what is wrong and how to write it again`
- PROOF-19 (RULE-35): as now, the warning reading `.purlin/evidence/ci/login.json names the source "local" but sits in ci/; it is ignored. Start the run that wrote it again.`

### `summary`

- RULE-23: as now, with `` `rules to test on <systems>`, `run purlin:test on <systems>`, the same systems named in both places ``
- PROOF-8: as now, ending `the fifth `  2 rules to test on Windows: run purlin:test on Windows``
- PROOF-33: as now, ending `ends the status on `  1 rule to test on Windows: run purlin:test on Windows``
- PROOF-56: as now, ending `then `  1 rule to test on Windows: run purlin:test on Windows``

### `package`

- RULE-32: The package carries `runs`, one entry per group of counted results sharing a source, a system, who ran them and a machine, local first and then by system, each naming `by`, the email its sections record, `machine`, `os`, `source`, `at`, `commit` and the count of `rules`
- PROOF-25 (RULE-11): In a signed project one of whose results sits under the source `ci`, written on the machine `build-7` by `runner@example.com`, `RULE-2`'s one result reads source `ci`, `passed`, runner `runner`, the time `2026-09-13T12:00:00Z`, current, this machine's operating system, the machine `build-7` and the full sha of the commit the tests ran at
- PROOF-66 (RULE-32): Beside Dana's local run, `PROOF-3` tagged `@env(windows)` ran under the source `ci` on the machine `build-7` as `runner@example.com`; `runs` holds two entries, the local one first, then one reading `by` `runner@example.com`, `machine` `build-7`, `source` `ci`, `os` `windows` and `rules` `1`
- PROOF-67 (RULE-33): The tests run and are committed at `<c>`, then a commit changes only `.purlin/evidence/ci/login.json`, the results a run on another system committed; the project is signed and every result in its package reads `same_code` `true`

### `signatures`

- PROOF-226 (RULE-102): `audit`'s Windows results, under the source `ci`, were taken before a commit that changed `src/audit.py`, and every other result was taken at `HEAD`; the walk prints only `No sign-off: these results were not taken on this version of the code, <sha7>: audit on Windows. Run purlin:test on Windows, then purlin:sign.` and exits 1

### `scaffold`, `update`

- `scaffold`: the Description ends `installs no git hook.` in place of the clause on the runner file. RULE-81 and PROOF-173 are deleted (a test that a removed thing is absent).
- `update` RULE-53: as now, without its last clause `, and no runner file is written`.

### `skill_test`, `skill_status`, `skill_sign`, `purlin_agent`

- `skill_test` Description, last sentence: `Its hand-off is `purlin:test --all --commit`; for a proof tagged for another system it points at the one reference that says what a project sets up.`
- `skill_test` RULE-23: `skills/test/SKILL.md` names the command `purlin:test --all --commit` and the paths `scripts/run/purlin_run.py`, `.purlin/evidence/local/<feature>.json`, `.purlin/config.json` and `references/evidence_and_signoff.md`
- `skill_test` PROOF-55: Checking the `purlin:test` skill file as shipped for the command `purlin:test --all --commit` and the paths `scripts/run/purlin_run.py`, `.purlin/evidence/local/<feature>.json`, `.purlin/config.json` and `references/evidence_and_signoff.md` reports nothing
- `skill_test` PROOF-52: A copy of the skill file with every `references/evidence_and_signoff.md` taken out is reported as `test does not name references/evidence_and_signoff.md`
- `skill_status` RULE-16 and PROOF-37: as now, without `` `purlin:test --remote`, ``
- `skill_sign` RULE-35 and PROOF-63: as now, without `` `purlin:test --remote`, `` (PROOF-63: `` `purlin:test --all --commit` and `git push origin` ``)
- `purlin_agent` RULE-18: as now, without `` `purlin:test --remote`, ``

### "Remote anchor" in place of "pinned anchor" (answer 2)

In the 4 rules and 20 proofs section 1 lists, and in each spec's Description, the kind is
called a remote anchor: `a pinned anchor` reads `a remote anchor`, `a pinned rule` reads `a
remote anchor's rule`, `a pinned copy` reads `a remote anchor's copy`, `a pinned source` reads
`a remote anchor's source`. Nothing else in those lines changes. The field `> Pinned:`, the
keys `pinned` and `pinned_sha`, the status `unpinned` and the noun in `the pin 1a2b3c4 is
behind its source` stay: a remote anchor's copy is pinned to one version of its source, and
the pin is that version.

### `specs/instructions/windows_run.md` (new)

```
# Feature: windows_run

> Description: How this repository proves its own rules tagged `@env(windows)`. It is this
>   project's own setup, as any project's would be: one workflow file for GitHub and one script
>   the owner starts from a Mac. Purlin ships neither.
> Scope: dev/windows_run.py, .github/workflows/windows.yml
> Stack: python/stdlib (subprocess, json), git, the GitHub CLI
> Highest-Rule: 3
> Highest-Proof: 4

## Rules

- RULE-1: `dev/windows_run.py` pushes this commit to the run branch `run/<branch>-<sha7>` on `origin`, waits on the run the `windows.yml` workflow starts for that branch, then pulls the commit that run made with `git pull --ff-only`, deletes the run branch and prints the status, after a red run as after a green one, and exits 1 when the run failed
- RULE-2: `dev/windows_run.py` refuses before anything is pushed, says what is wrong and how to fix it, and exits 1, when the checkout is on no branch or holds uncommitted changes, and when `gh` is not installed
- RULE-3: `.github/workflows/windows.yml` starts on a push to a `run/` branch and on nothing else, holds the one job `windows-latest`, runs `scripts/run/purlin_run.py --ci --commit`, and then pushes that commit to the branch it ran on, whether the tests passed or not

## Proof

- PROOF-1 (RULE-1): On the branch `feature-x` at HEAD `4f1c2ab…`, with `gh` on the search path and GitHub registering run `987`, `dev/windows_run.py` starts `git push origin HEAD:refs/heads/run/feature-x-4f1c2ab`, `gh run watch 987 --exit-status`, `git pull --ff-only origin run/feature-x-4f1c2ab` and `git push origin --delete run/feature-x-4f1c2ab`, in that order, ends its output with the status table, and exits 0
- PROOF-2 (RULE-1): When `gh run watch` exits 1, `dev/windows_run.py` prints `The run failed on GitHub. The table below is what came back.`, still starts the pull and then the delete of the run branch, ends its output with the status table, and exits 1
- PROOF-3 (RULE-2): With one file in the tree that is not committed, `dev/windows_run.py` exits 1, prints exactly `This checkout has changes that are not committed, so a run would prove something other than what is here. Commit them, then run python3 dev/windows_run.py again.`, and starts no push
- PROOF-4 (RULE-3): `.github/workflows/windows.yml` triggers on a `push` of `branches: ['run/**']` alone, names `windows-latest` and no other system, holds a step that runs `scripts/run/purlin_run.py" --ci --commit` or the same without the quote, and after it a step under `if: always()` that pushes `HEAD` to the branch the run was started for
```

## 3. The order, and the lanes

All local. No cloud session. Nothing is pushed by a lane.

1. **Decision 118's agent finishes**: its uncommitted work is committed on `main`, the sweep is green.
2. **The docs, first** (the owner's order). The coordinator commits the new section of
   `references/writing_style.md` (section 4) on `main`, since it is the docs lanes' standing
   rule. Then lane `docs-a` runs alone, in a worktree from `main`, and is merged before anything
   else, so the owner can read the pages the removal changes against the slides.
3. **The base commit, by the coordinator**, on `main`: this plan as `dev/plans/d119-plan.md`; the owner's three answers under decision 119's entry in `dev/plans/three-levels.md`, which is already written and is not rewritten; every spec change of section 2, after recounting each `> Highest-*`; `CLAUDE.md` (section 4); the two shared helpers, changed once and then frozen: `dev/mcp_project.py` and `dev/sign_project.py` write a `ci` section with `machine` `build-7`, `email` `runner@example.com`, `runner` `runner` and no `hostname`. The sweep is red after it in the tests section 1 lists. That is expected.
4. **Six lanes in parallel**, `run`, `surfaces`, `words`, `own`, `anchors` and `docs-b`, each `git worktree add /Users/richlabarca/LocalCode/purlin-wt/d119-<lane> -b lane/d119-<lane> main`.
5. **Integration** (section 8), then the reading pass, then this repository's own Windows run.

Seven lanes: `docs-a` first and alone, then six together.

| Lane | Owns, and writes nothing else | Acceptance |
|---|---|---|
| `docs-a` | `README.md`, `docs/running-and-evidence.md`, `docs/getting-started.md`, `docs/how-purlin-works.md`, `docs/index.md`, `docs/specs-and-anchors.md`, `docs/sign-off.md`, `docs/working-together.md`, `docs/upgrading.md` | the removal's words are section 4's; the new content and the plain-language pass are done on each page (section 4, "The docs"); "remote anchor" on every page, 9 places (`specs-and-anchors.md` 5, `working-together.md` 3, `index.md` 1); `python -m pytest dev/test_purlin_docs.py -q` passes; `install PROOF-1` still holds; the greps of section 8 are empty over its files |
| `docs-b` | `docs/audit.md`, `docs/dashboard.md` | the plain-language pass alone; `purlin_docs PROOF-17`, `21` and `22` still hold |
| `run` | `scripts/run/purlin_run.py`, `scripts/run/evidence.py`, `scripts/mcp/purlin/evidence.py`; deletes `scripts/run/{remote,host,workflow,ci}.py`, `templates/purlin.yml`, `templates/purlin.azure-pipelines.yml`; `templates/evidence-readme.md`; `references/formats/evidence_format.md`, `references/formats/marker_format.md`; `dev/test_run_script.py`, `dev/test_evidence_writer.py`, `dev/test_evidence_reader.py`; deletes `dev/test_host.py`, `dev/test_remote.py`, `dev/test_consumer_ci.py`, `dev/test_host_pathspec.py` | its three test files pass; `python -m pytest dev/test_init_scaffold.py -q -k readme` passes (the template is compared byte for byte); every proof of `run_script`, `evidence_writer` and `evidence` has a test comment; d115-plan appendix A's script prints `0 gone, 0 reworded` for its files |
| `surfaces` | `scripts/mcp/purlin/summary.py`, `scripts/export/package.py`, `scripts/review/sign.py`, `scripts/init/update.py`, `scripts/init/scaffold.py`; `references/formats/package_format.md`; `dev/test_summary.py`, `dev/test_export.py`, `dev/test_signatures.py`, `dev/test_init_scaffold.py`; `dev/fixtures/report/regulated.json`, `team.json`, `solo.json` | its four test files pass but the tests waiting on `run` (named in its report); `dev/test_purlin_report*.py` and `dev/test_states.py` still pass; appendix A's script prints `0 gone, 0 reworded` |
| `words` (also the references' prose in the plain words of section 4, and "remote anchor" in `glossary.md` 2, `spec_quality_guide.md` 1 and `RELEASE_NOTES.md` 1) | `skills/test/SKILL.md`, `skills/build/SKILL.md`, `skills/status/SKILL.md`, `skills/sign/SKILL.md`, `skills/init/SKILL.md`, `agents/purlin.md`, `references/purlin_commands.md`, `references/evidence_and_signoff.md`, `references/glossary.md`, `references/commit_conventions.md`, `references/spec_quality_guide.md`, `RELEASE_NOTES.md`; `dev/test_skill_test.py`, `dev/test_skill_status.py`, `dev/test_skill_sign.py`, `dev/test_purlin_agent.py` | `python -m pytest dev/test_skill_*.py dev/test_purlin_agent.py dev/test_purlin_output.py -q` passes; every line is section 4's; no skill, agent or reference line names a path under `dev/` or this repository's `specs/` |
| `anchors` | `scripts/anchor/upstream.py` (10), `scripts/mcp/purlin/drift.py` (6), `scripts/mcp/purlin/specs.py` (3), `skills/anchor/SKILL.md` (4), `references/formats/anchor_format.md` (3), `dev/test_drift.py` (5), `dev/test_upstream.py`, `dev/test_upstream_notes.py` (4), `dev/test_e2e_anchor_authority.sh` (12), `dev/test_e2e_external_refs.sh` (6), `dev/test_schema_spec_format.py` (1), `dev/test_states.py` (5), `dev/test_purlin_report.py` (1), `dev/test_specs_reader.py` | every "pinned" that names the kind reads "remote", in a printed line, a comment, a test name and a docstring alike; the field `> Pinned:`, the keys, `unpinned` and `the pin` stay; each test under a reworded proof is changed with it; its test files pass and appendix A's script prints `0 gone, 0 reworded` |
| `own` | `dev/windows_run.py` (new), `dev/test_windows_run.py` (new), `.github/workflows/windows.yml` (`git mv` from `purlin.yml`), `.github/workflows/version-check.yml` only if it names the old file, `dev/manual/README.md`; deletes `dev/manual/check_azure_remote.py` | `python -m pytest dev/test_windows_run.py -q` passes with the network off; every proof of `windows_run` has a test comment |

Merge order: `docs-a` (step 2), then `run`, `surfaces`, `words`, `own`, `anchors`, `docs-b`. No two lanes own one file,
so any order merges clean; `run` goes first because the others' waiting tests clear on it.

**The lane prompt** is section 11 of `dev/plans/d115-plan.md`, with: this plan in place of that
one; decisions 100 to 119; `main` in place of `d115/base` and no fetch; the report at
`dev/plans/d119-reports/<lane>.md`; "push nothing"; and appendix A's script used as written.
Two traps from earlier lanes hold: never `git checkout -- specs/`, and no generated file is
staged (`scripts/report/purlin-report.html`, `.purlin/evidence/**`, `docs/images/*.png`).

### Contracts, word for word

**K1. The command line** (`run`; read by `words`, `docs`, `own`).

```python
USAGE = (
    'Usage: purlin_run.py [--feature NAME ... | --all] (--test | --ci) '
    '[--commit] [--arm-timeout SECONDS] [--project-root DIR]\n'
    '       purlin_run.py [--feature NAME ... | --all] --audit [--commit] '
    '[--arm-timeout SECONDS] [--project-root DIR]')
NEEDS_ONE = '1 proof needs %s; this machine is %s. Run purlin:test on %s.'
NEEDS_MANY = '%d proofs need %s; this machine is %s. Run purlin:test on %s.'
```

`--remote` and `--commit-runner` are no longer read: each gets the existing
`unknown argument <token>` refusal. `Args.remote`, `Args.commit_runner`, `REMOTE_IS_A_TEST`,
`COMMIT_IS_A_PERSONS`, `COMMIT_RUNNER_IS_REMOTE`, `_remote()` and the `host` imports go.
`--commit` is accepted with all three actions.

**K2. The `--ci` arm** (`run`). `_ci(project_root, args, features, sections, log, os_name, started)`:
write the log, `write_sections(..., 'ci')`, prune, print `written_line(paths, 'ci')`, and with
`args.commit` call `evidence_writer.commit_ci(project_root, started, removed)`. It makes no
first commit of specs, tests or settings. `tagged_here`, the `remote_proofs` selection and
`SlowPlan() if args.all or args.action == 'ci'` stay as they are.

**K3. A section** (`run`; read by `surfaces` through the frozen helpers).

```python
# scripts/run/evidence.py
def build_section(info, entries_by_proof, host_os, commit, dirty, runner,
                  fingerprint, at=None, machine=None, only=None): ...
def commit_ci(project_root, head_sha, removed=()):
    """Commit the `ci/` files and what the run removed, as
    `purlin: evidence at <sha7 of head_sha>`. Prints COMMITTED or UNCHANGED."""
```

`hostname` goes from `build_section`, from the comparison's ignored keys and from every
section written. `email` is added to every section, whatever the source. `runner_name` is the
email's slug under every action; `machine_name` is `platform.node() or 'unknown'` under every
action. `merge_for_host` goes.

**K4. The reader's warning** (`run`): `REWRITE_CI = 'Start the run that wrote it again.'`

**K5. The status** (`surfaces`): the command beside `rules to test on <systems>` is
`run purlin:test on <systems>`, the words the line already names its systems with. The kind's key stays `to_test_remote`: it names where the test must run,
and renaming it would change the payload and the package for no reader's gain.

**K6. The package and the sign-off** (`surfaces`): `_by(entry)` answers the section's `email`,
or `unknown`, under both sources; `REMOTE_RUNNER` and `RUN_REMOTE_LINE` go, and `run_lines`
prints `RUN_LINE` for every run. `RUN_AGAIN = {'local': 'purlin:test --all --commit', 'ci': 'purlin:test on %s'}`, the `%s` filled with the systems of the `ci` results named.

**K7. The upgrade** (`surfaces`): `_apply_workflows` prints
`removed %d workflow%s that committed proof files` and nothing after it.

**K8. This repository's own run** (`own`): the file names `dev/windows_run.py` and
`.github/workflows/windows.yml`, the run branch `run/<branch>-<sha7>`, and the printed lines of
section 6.

## 4. Lines a person reads

### The status, a test run, the sign-off

```
  22 rules to test on Windows: run purlin:test on Windows
1 proof needs Windows; this machine is macOS. Run purlin:test on Windows.
3 proofs need Windows; this machine is macOS. Run purlin:test on Windows.
No sign-off: these results were not taken on this version of the code, 1cf829e: audit on Windows. Run purlin:test on Windows, then purlin:sign.
Tests run by runner@example.com on build-7 at 2026-10-01 12:17 UTC on 1cf829e: 20 rules on Windows.
.purlin/evidence/ci/login.json names the source "local" but sits in ci/; it is ignored. Start the run that wrote it again.
removed 1 workflow that committed proof files
```

After the build this repository's own status ends `20 rules to test on Windows: run purlin:test on Windows`.

### `skills/test/SKILL.md`, Step 5, whole

```
## Step 5: another operating system

A proof tagged `@env(windows)`, `@env(macos)` or `@env(linux)` runs only on that operating system.
On a machine that does not match, the run prints one line per system, `<n> proofs need <System>;
this machine is <System>. Run purlin:test on <System>.` An untagged proof runs anywhere. A system
that is neither Windows nor macOS is `linux`, shown as `Linux/Unix`. A rule reads `partial` where
two systems that each ran disagree.

Purlin runs the tests where you are and starts no run anywhere else. When the run prints that
line, look in the project for its own setup for that system: a workflow or pipeline file that
runs `scripts/run/purlin_run.py --ci`.

- **There is one.** Say how this project starts it, as its own files say, and ask whether to
  start it. Start it only on a yes. When it has finished, `git pull` brings the results back and
  `purlin:status` shows them.
- **There is none.** Say so and offer to write it: `No setup in this project runs the tests on
  <System>. I can write one for <git host>: a file that runs the tagged tests there and returns
  the results through git, and a way to start it. Write it? [y/N]`. Read the git host from
  `origin`; where it names none, or the person wants another, ask which. On yes, write it as
  `references/evidence_and_signoff.md`, "A run on another system" says, show the files, and
  commit them only when the person says so. The files are the project's own: Purlin ships none
  and changes none later.
```

The usage block loses its two `--remote` lines, and Step 6's table loses its `Commit it and run`
row. `skills/build/SKILL.md`: `the run counts such proofs in one line per system; `skills/test/SKILL.md`, Step 5 says what to do then`,
and `- A proof needs another operating system: name it, then do as `skills/test/SKILL.md`, Step 5 says`.
`skills/status/SKILL.md`: `| `<n> rules to test on <systems>` | `→ On <systems>: purlin:test`, then as `skills/test/SKILL.md`, Step 5 says |`.
`skills/sign/SKILL.md`: the run line `Tests run by a remote runner at ...` sentence goes; the
quoted refusal ends `Run purlin:test --all --commit and purlin:test on Windows, then purlin:sign.`;
line 80 reads `` `purlin:test on <System>` for another system's ``; the table row names
`purlin:test --all --commit`, `purlin:test --commit` or `purlin:test on <System>`.
`skills/init/SKILL.md`: the paragraph `Setup writes no runner file. ...` goes.

### `references/evidence_and_signoff.md`: "Where a runner runs" becomes

```
## A run on another system

**Purlin runs the tests where you are.** It starts no run on another machine, drives no pipeline
and adds no file for a git host to a project. A project needs a run somewhere else for one
reason: a proof in `specs/` is tagged `@env` for a system the machines at hand are not.

**Which machine proves which proof.** An untagged proof is proven by `purlin:test` on any
machine. A proof tagged `@env(<system>)` is proven only by a run on that system: `purlin:test`
on a person's machine of that system, or the project's own run there.

**The project's own run** is a file for its git host, written for that project and kept in it,
usually by the agent on request. Whatever the git host, it does five things:

1. It runs on the system the proofs are tagged for, on a full checkout of the commit to prove.
2. It installs what the project's tests need, and fetches Purlin at the version
   `.purlin/config.json` names.
3. It sets a git name and email, then runs
   `python3 <purlin>/scripts/run/purlin_run.py --ci --commit`. That run starts only the tests of
   the proofs tagged for its system, writes that system's section of
   `.purlin/evidence/ci/<feature>.json` for each feature it covered, and commits those files
   alone as `purlin: evidence at <sha7>`. It exits 1 only when one of those tests failed or
   could not run.
4. It pushes that commit to the branch it ran on, after a failed run as after a passing one, in
   a way that starts no further run.
5. Where it covers two systems, their jobs run one after the other, each on the branch as the
   one before left it.

How a run starts is the project's choice: by hand from a desk, on a push, on a schedule. The
results come back with `git pull`, and count on the same terms as any other result (above).
```

The same file's other lines: the `to_test_remote` row's command is `purlin:test on <System>`; lines 94
to 105 read that a run on another system writes its own section under `.purlin/evidence/ci/`
and commits it with `--commit`, and that `machine` is the host's name under both sources; lines
115 to 119 read `` `purlin:test --all --commit` for this machine's results, `purlin:test on <System>` for another system's ``.

### The other references, the agent, `CLAUDE.md`

- `references/purlin_commands.md`: the syntax is `purlin:test [feature ...] [--all] [--commit] [--arm-timeout <seconds>]`; line 13 reads `No Purlin command pushes.`; line 20 reads `` `purlin:test --all` starts every test, slow ones included. ``; lines 25 to 32 read `` The hand-off is `purlin:test --all --commit`, and the project's own run for the proofs tagged for another system (`references/evidence_and_signoff.md`, "A run on another system"); that run is `scripts/run/purlin_run.py --ci --commit`, which a pipeline runs and nobody types. Both sources count. ``; the two `--remote` usage lines and the three refusal lines (149 to 151) go; the `--ci` exit row reads `the tests tied to the proofs tagged for this machine's system passed`.
- `references/glossary.md`: `pinned anchor` reads `**remote anchor**: a local copy of an anchor another repository owns. The copy is pinned to one version of its source, the commit `> Pinned:` names.`, and the table row reads `anchor, remote anchor`. `remote runner`, `remote run`, `run branch` and `runner file` go. `git host` reads `**git host**: where a project's repository is kept, such as GitHub or Azure DevOps. Purlin calls none; a project's own run on another system is written for the one it uses.` Line 64 reads `the project's own run for the proofs tagged for another system`; lines 69 to 71 read `machine` as the host's name and `ci` as `a project's own run on another system`.
- `references/commit_conventions.md`: the row and the example `ci: the Purlin runner for ...` go; the evidence row's last cell reads `` `purlin:test --commit`, `purlin:audit --commit`, and a project's own run on another system ``; lines 70 and 71 read `A run on another system commits its own files under `.purlin/evidence/ci/` with the same subject, under the git identity its checkout sets.`
- `references/spec_quality_guide.md`: the pointer `"Where a runner runs"` reads `"A run on another system"`; the stuck-rule row's fix reads `` Run `purlin:test` on that system, or start the project's own run there, or drop the `@env` tag if any operating system could show it. `` It also gains the paragraph below.
- `agents/purlin.md`: line 40 `Every step runs on the person's own machine.` stays and its second sentence goes; line 53 reads `the project's own run does the same for a proof tagged for another system`; line 91's exception goes, so the line reads that no Purlin command pushes; the two table rows read `| Developer | "prove it on Windows too" | `skills/test/SKILL.md`, Step 5 |` and `` `purlin:test --all --commit`, and the project's own run where a proof is tagged for another system ``.
- `CLAUDE.md` (base commit): line 49 reads `The anchor, local and remote`; line 53 ends `written by `purlin:test`, `purlin:audit` and a project's own run on another system`; line 86 reads `` 3. Run `purlin:test --all --commit` and `python3 dev/windows_run.py`, then `purlin:sign`. ``

### `references/spec_quality_guide.md`, "Writing proofs": one new point, first

Placed after `Each point below carries a pair: a poor proof, and the one that replaces it.`

```
### Pass or fail

A proof a test carries out is pass or fail: the test checks an exact result, like the message
`Account locked`.

A judgment call is not. "It looks good" and "it is easy to use" are for a person to decide; a
test cannot decide them, and neither can an AI. Tag such a proof `@manual`: no test runs for
it, `purlin:sign` stops there, and a person checks it and writes what they saw. Or leave it
out: not everything needs a rule.

A test may ask a model a question with one right answer, such as which commands it offers
after an install.

- Poor: "A model reads the error messages and finds them friendly."
- Good: "A wrong password shows the message `Wrong email or password`." and, where the tone
  matters, "Read the error messages against the brand voice guide @manual".
```

Checked in the tree: `skills/spec/SKILL.md` (lines 108 to 116) and `docs/sign-off.md` (line 41)
say only when to tag `@manual`, and `docs/specs-and-anchors.md` (line 129) names the guide as the
one home. The skill only points at the guide and does not change. The two doc pages change as
"The docs" below says: the judgment-calls words go into `docs/specs-and-anchors.md`, and
`docs/sign-off.md` points there.

### `references/writing_style.md`: a new section, after "The rules"

```
## Short and plain

Purlin's slides are the model. A doc page may say more than a slide, and it says it the same way.

- One idea in a sentence. Two ideas are two sentences.
- The concrete example before the abstract statement, or in place of it.
- Where a slide covers the same thing, the page uses the slide's words for it.
- A page says what the reader needs for the next thing they do. Detail few readers need goes
  last, or on the page a link names.
- Nothing true that a reader needs is cut, and every statement is what the code does.

- Before: "It names what is done, what is seen and the value that settles it, such as the
  message `Account locked`."
- After: "A test checks an exact result, like the message `Account locked`."
```

### The docs (lane `docs-a`, and `docs-b` for the two pages left)

**The model is the deck.** Each docs lane reads every slide in `dev/plans/deck/build_deck.py`
first: its rows, lead, closing and notes. Where a page covers what a slide covers, it uses the
slide's words for the same thing. A slide's headline may be a question; a page's heading stays
a statement (`references/writing_style.md`).

**The plain-language pass covers every page**, not only the lines the removal changes. Each
page is read against the slides and `references/writing_style.md`. A convoluted sentence is
rewritten: short, one idea, second person, the example first, no stacked clauses. Nothing true
that a reader needs is removed, and every statement is checked against the code before it is
kept (decision 64). Each lane lists in its report every statement it found the code does not
hold.

**New content, in the slides' words:**

| Slide | Page and place | What the page says |
|---|---|---|
| `manual`, judgment calls | `docs/specs-and-anchors.md`, where `@manual` is described (line 147 on), as `### Judgment calls` | A proof is pass or fail: a test checks an exact result, like the message `Account locked`. A judgment call is not: "It looks good." "It is easy to use." A test cannot decide these, and neither can an AI. Tag it `@manual`; no test runs for it. `purlin:sign` stops there; a person checks it and writes what they saw. Not everything needs a rule: look and feel can stay outside Purlin. `docs/sign-off.md` line 41 points here and repeats none of it |
| `remote`, other platforms | `docs/running-and-evidence.md`, `## Testing on another system`, below | the slide's lead, four rows and closing, then the example |
| `slow`, slow tests | `docs/specs-and-anchors.md`, decision 118's section | the same facts in the slide's words: mark it once; `purlin:test` skips every slow test; `purlin:test --all` runs everything; every status says when one is due, `1 slow proof to run: purlin:test --all`; the tests are fully `met` only after every slow test has passed |
| `anchors`, shared rules | `docs/specs-and-anchors.md`, the anchors section | the two kinds: in this project, or owned elsewhere; under the second, `Kept in step` (`purlin:anchor sync` updates your copy; the status says when the source has moved on) and `Read-only` (your copy is never edited in your project; a change is made at the source). The second kind is a remote anchor; the page says once: `Your copy is pinned to one version of its source.` |

**What a proof reads from these pages**, so a rewrite does not break one silently:

- `install PROOF-1` and `dev/test_install.py`: the fenced shell lines under "Install" in `README.md` and under step 1 of `docs/getting-started.md`, the same in both, and the address `https://github.com/rlabarca/purlin.git`. Leave them as they are.
- `purlin_docs PROOF-17`: every relative link under `docs/` names a file and a heading that exist. A reworded heading changes its anchor; fix every link to it in the same commit.
- `purlin_docs PROOF-21` and `PROOF-22`: `docs/audit.md` cites Inozemtseva and Holmes, Just et al., Petrović et al., Foster et al. and LLMorpheus, each by an `https://` link, and lists each again under the heading `Sources`.
- `purlin_docs PROOF-24`: exactly 1 paragraph of `docs/working-together.md` names a worktree, and it names each checkout's own results and dashboard, merging and `purlin:status`.
- The two screenshots in `docs/dashboard.md` are generated; the page's image links stay.
- For lane `words`: `run_script PROOF-133` reads the seven entries of `references/supported_frameworks.md` word for word, and `ai_audit PROOF-11` sends `references/review_criteria.md` to the model byte for byte, so neither file is in the plain-language pass. Each `skill_*` spec and `purlin_agent RULE-18` lists names a skill or the agent must keep.

`docs/running-and-evidence.md`: the section `## When a project has a runner` and its three
subsections are replaced by:

````
## Testing on another system

Purlin runs your tests where you are. Reaching another platform is your project's own setup,
and Purlin keeps the evidence. Purlin itself only works locally. It drives no remote pipeline
and adds none to your repository.

| | |
|---|---|
| Say where it must hold | Tag the proof `@env(windows)`. Every status then lists it: `22 rules to test on Windows` |
| Ask the AI to set it up | It writes what your project needs for your git host, GitHub or Azure DevOps. The files live in your project and are yours to change. |
| Run it your way | How a run starts is up to your project: from your desk, on a push or on a schedule. The results come back through git. |
| Purlin tracks the results | Each result records the machine and the system it ran on, for every rule, like a result from your own machine. |

### One example: GitHub, started from your desk

A workflow a project can copy to `.github/workflows/windows.yml`:

```yaml
name: windows
on:
  workflow_dispatch:
permissions:
  contents: write
jobs:
  windows:
    runs-on: windows-latest
    timeout-minutes: 90
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Get Purlin
        shell: bash
        run: git clone --depth 1 --branch v0.10.0 https://github.com/rlabarca/purlin "$RUNNER_TEMP/purlin"
      - name: Install what the tests need
        shell: bash
        run: python3 -m pip install pytest
      - name: Run the tests tagged for Windows
        shell: bash
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          python3 "$RUNNER_TEMP/purlin/scripts/run/purlin_run.py" --ci --commit
      - name: Return the evidence
        if: always()
        shell: bash
        run: git push origin "HEAD:${{ github.ref_name }}"
```

Use the tag of the Purlin version in your `.purlin/config.json`, and install what your own test
command needs. Start it from your desk, on a branch you have pushed:

```
gh workflow run windows.yml --ref "$(git branch --show-current)"
gh run watch
git pull
```

GitHub starts a workflow by hand only once its file is on the default branch.

### What that run does

`purlin_run.py --ci` is the run script `purlin:test` runs, in the form a pipeline uses. It
starts only the tests tied to the proofs tagged for the system it is on, slow ones included,
and writes that system's section of `.purlin/evidence/ci/<feature>.json` for each feature it
covered: each rule's word, each proof's result, the commit, the time, the machine's name and
the git email set there. `--commit` commits those files alone, as `purlin: evidence at <sha7>`.
It never pushes; the workflow's last step does. It exits 1 only when one of those tests failed
or could not run, and a failed run's results come back too. No audit runs there.

The commit that comes back changes only files under `.purlin/`, so its results were taken on
the same version of the code as yours, and both count for a sign-off.

### Azure DevOps, or any other git host

Ask: `set up a Windows run for this project on Azure DevOps`. The agent writes the pipeline
file for that host, which does the same things as the example, and tells you how to start it.
On another machine with another git host, ask again and pick. The five things every such file
does are in [evidence_and_signoff.md](../references/evidence_and_signoff.md).
````

Its other lines: line 8 loses the sentence on `purlin:test --remote`; the usage block loses
its `--remote` line; the `Left to do` table row reads `| `1 rule to test on Windows` | `run purlin:test on Windows` | yes |`;
"Proofs for another operating system" quotes the new `needs` line and `1 rule to test on Windows: run purlin:test on Windows`;
the `<source>` row reads `` `ci` for a project's own run on another system ``; "The source is the
folder" reads `written by a project's own run on another system`; the hand-off block reads
`purlin:test --all --commit`, then `and your project's run on any other system a proof is tagged for`;
"Who pushes" ends `No Purlin command pushes.`

The other pages:

- `README.md` line 26 and `docs/getting-started.md` line 23: the sentence on the runner file goes; the bullet ends `after a command ends.` The `Tests` row reads `` `purlin:test --all --commit`, and your project's own run for a proof tagged for another operating system ``; the command row is `purlin:test [feature ...] [--all] [--commit] [--arm-timeout <seconds>]`.
- `docs/getting-started.md` line 212: `including how a project tests on another operating system.`
- `docs/how-purlin-works.md`: line 53 reads `No command pushes.`; line 63 reads `` and your project's own run for a proof tagged for another operating system ``; the table row reads `` `purlin:test`, `purlin:audit`, a project's own run on another system ``; the section `## When a project has a runner` becomes `## Testing on another system`, four sentences: the slide's lead and closing, then `A proof tagged `@env(windows)` is proven only by a run on Windows, which your project sets up for itself; [running-and-evidence.md](running-and-evidence.md#testing-on-another-system) has one worked example.`; line 143 reads `1 rule to test on Windows: run purlin:test on Windows`.
- `docs/sign-off.md`: wherever it lists what the developer runs, `the run on Windows included` (the sign-off slide's words); lines 53 to 58 read `The developer runs every test, on their machine and through the project's own run for any other operating system, and commits the results that come back:` with the block holding `purlin:test --all --commit` alone; the refusal row quotes `Run purlin:test on Windows, then purlin:sign.`; the sentence on `Tests run by a remote runner` goes.
- `docs/working-together.md` line 69: `and your project's own run where a proof is tagged for another operating system.`
- `docs/index.md`: the row ends `which results count for a sign-off, and testing on another system`.
- `docs/specs-and-anchors.md`: line 200 reads `` `@slow` may stand with `@env(...)`, and a run on that system runs the slow tests of the proofs it proves. ``; lines 217 and 218 read `and your project's own run on that system proves it. [running-and-evidence.md](running-and-evidence.md#testing-on-another-system) says how that run is made.`
- `docs/upgrading.md`: the paragraph `**The runner.**` goes.

### `templates/evidence-readme.md`

```
.purlin/evidence/local/<feature>.json   a person's own run
.purlin/evidence/ci/<feature>.json      this project's own run on another system
```

`A run on your own machine writes `local/`, and `--commit` commits it under your own git identity. A run your project makes on another system writes `ci/` and commits it there.`

### The release notes entry (0.10.0, under "What is new")

Replaces lines 18, 47, 98 to 100, 111 and 210; the formats line reads `evidence 9` and `package 10`.

```
- **The hand-off is run and commit**: purlin:test --all --commit, and your project's own run for any other system.
- **Purlin runs the tests where you are.** A proof tagged `@env(<os>)` for a system your machine
  is not is listed by every status, as `22 rules to test on Windows: run purlin:test on Windows`. Reaching
  that system is your project's own setup: ask the AI, and it writes a file for your git host,
  GitHub or Azure DevOps, that runs `scripts/run/purlin_run.py --ci --commit` there and returns
  the results through git. Purlin ships no such file, starts no run on another machine and
  pushes nothing.
```

`purlin:init --update` section, line 210: the sentence `It writes no runner file.` goes.

## 5. Formats

| File | Now | After | Why |
|---|---|---|---|
| `evidence_format.md` | 8 | **9** | `hostname` is removed; `email` is on every section; `machine` is the host's name under both sources; `runner` is always the email's slug. "The two folders", the `ci` paragraph, the last bullet of "How a writer merges" and the last paragraph of "The two commits" are rewritten to section 0. `schema` stays `purlin-evidence/2`: a reader that ignores `hostname` reads both |
| `package_format.md` | 9 | **10** | `by` is always an email or `unknown`; `machine` is always a host's name; `runner` is always a slug; the `to_test_remote` row's command is `purlin:test on <System>` |
| `marker_format.md` | 4 | 4 | one clause reworded (`a `--ci` run selects the proofs tagged for its system`) |
| `anchor_format.md` | 12 | 12 | wording only: `pinned anchor` reads `remote anchor` in 3 places, the heading `Editing a pinned anchor` reads `Editing a remote anchor`; the field `> Pinned:` keeps its name |
| `spec_format.md`, `signature_format.md` | | | not touched |

Each is changed in the same commit as its code. The dashboard's data stays at schema 14: no key
changes.

## 6. This repository's own Windows run

| File | What it is | Salvaged from |
|---|---|---|
| `.github/workflows/windows.yml` | Starts on a push to `run/**` alone. One job, `windows-latest`, 90 minutes. Steps: checkout with `fetch-depth: 0` and `persist-credentials: true`; Python 3.11; "Set up the test framework"; set the git name and email, then `python3 scripts/run/purlin_run.py --ci --commit`; then, under `if: always()`, `git push origin "HEAD:${GITHUB_REF_NAME}"` | `.github/workflows/purlin.yml`: the trigger, the permissions, the timeout, checkout, Python and the framework step as they are. The "Locate Purlin" step and the `GITHUB_TOKEN` env of the test step go |
| `dev/windows_run.py` | The start script: push, wait, pull, delete, print the status | `scripts/run/remote.py`: `run_branch_name`, `_push`, `find_run`, `_github`, `_bring_back`, `_delete`, `_dirty`, `_branch`, `_have`, `_environment`, `_run`, `_capture`, `_table`, and the lines `NOT_ON_A_BRANCH`, `NOT_COMMITTED`, `PUSH_FAILED`, `NO_RUN_FOUND`, the `gh` line of `NO_PROGRAM`, `FAILED_ON_HOST`, with `purlin:test --remote` reading `python3 dev/windows_run.py`, `the git host` reading `GitHub` and `WORKFLOW = 'windows.yml'`. Not carried: `ensure_runner`, every Azure DevOps function and line, the `workflow` import |
| `dev/test_windows_run.py` | Four tests, one per proof of `windows_run` | The GitHub round-trip tests of `dev/test_host.py` (those of `host PROOF-24`, `68`, `63`, `142`) |
| `specs/instructions/windows_run.md` | 3 rules, 4 proofs (section 2) | `host` RULE-12, 51 and 53, their GitHub halves |

The owner starts it from the Mac, on a committed tree: `python3 dev/windows_run.py`. It prints
`Pushing main as run/main-<sha7>.`, waits with `gh run watch`, runs
`git pull --ff-only origin run/main-<sha7>`, deletes the run branch and prints the status. The
evidence returns as the one commit the runner made, `purlin: evidence at <sha7>`, which changes
only `.purlin/evidence/ci/`. `main` itself is never pushed by it.

No test needs the network: the four tests stand a recording `gh` and `git` in for the real ones,
as the tests they come from do, and PROOF-4 reads the workflow file. Nothing in `dev/run_tests.sh`
or a `purlin:test` run reaches GitHub. Azure DevOps code is deleted, with
`dev/manual/check_azure_remote.py` (answer 1).

The 16 files under `.purlin/evidence/ci/` in this repository were written by the old arm and
read `machine` `remote runner, Windows`. They are left as they are: `host.json` is removed by
the first run after the build, and the first Windows run rewrites the rest.

## 7. The upgrade from 0.9.5

0.9.5 shipped no runner file and wrote none into a project (`git ls-tree v0.9.5`: its
`templates/` holds `config.json` and `gitignore.purlin` alone).

- **Still taken out:** a workflow under `.github/workflows/` whose text holds `.proofs-`, which
  committed 0.9.5's proof files beside the specs. It is backed up, untracked and removed, as
  now. Only its printed line changes (K7).
- **Left alone:** every other workflow or pipeline file, whatever its name, including a
  `.github/workflows/purlin.yml` or `purlin.azure-pipelines.yml` an unreleased 0.10 build wrote.
  The upgrade is from 0.9.5 only (decision 109); this repository's own such file is renamed by
  hand in lane `own`.
- **Nothing is written** for a git host, and no test says so.
- `config_engine`'s `UPGRADE_KEYS` keeps `ci`: it is a 0.9.5 setting the upgrade takes out.

## 8. Integration, local, one agent

1. Merge `run`, `surfaces`, `words`, `own` into `main`, in that order, `--no-ff`.
2. `bash dev/run_tests.sh` to 0 failed. Expected, if nothing else moved: about 815 passed and 9
   skipped (854 less 45 deleted tests that ran, plus 6; `host PROOF-117` leaves the skipped).
3. `python3 scripts/run/purlin_run.py --test --all --commit` to the clean state: 39 specs, 410
   rules, 820 proofs, 820 test comments tied, no rule `failed`, `partial` or `no test`, no test
   comment to correct, and `Left to do` reading the Windows line alone. The run removes
   `.purlin/evidence/local/host.json` and `.purlin/evidence/ci/host.json`.
4. Appendix A's script of `dev/plans/d115-plan.md` over every `dev/test_*`: `0 gone, 0 reworded`.
5. The greps, each empty:
   ```
   git grep -n -i -E -e '--remote|commit[-_]runner|remote runner|remote runs?([^a-z]|$)|runner file|run branch|purlin\.yml|purlin\.azure-pipelines|run_remote|ensure_runner|hostname' -- . \
     ':!dev/plans' ':!.purlin/evidence' ':!dev/windows_run.py' ':!dev/test_windows_run.py' \
     ':!.github/workflows' ':!specs/instructions/windows_run.md' ':!dev/fixtures/upgrade-0.9.5' \
     ':!scripts/report/purlin-report.html' ':!RELEASE_NOTES.md' \
     ':!dev/fixtures/reports/vitest/vitest.xml'
   git grep -n -i -E 'pinned (anchor|rule|copy|source)' -- . ':!dev/plans' ':!dev/fixtures/upgrade-0.9.5' ':!.purlin'
   sed -n '/^## Unreleased/,/^## 0\.9\.5/p' RELEASE_NOTES.md | grep -n -i -E -e '--remote|remote runner|runner file'
   git grep -n -E 'dev/|specs/(run|mcp|init|review|export|skills|instructions)/' -- skills agents references
   ```
   Changed at integration, 2026-10-01. `dev/fixtures/reports/vitest/vitest.xml` is left out of
   the first grep: its `hostname` is an attribute vitest writes into its own report, and the
   fixture is that report as the tool wrote it. `remote run\b` reads `remote runs?([^a-z]|$)`:
   git on macOS does not read `\b` under `-E`, so the first form matched nothing. The fourth
   grep prints one line that is not a path, `< /dev/null` in `skills/init/SKILL.md`.
6. The screenshots are retaken with `dev/capture_doc_screenshots.py` where a fixture's words
   show in one.
7. `dev/plans/deck/build_deck.py`, line 156: `the remote run for Windows included` reads `the
   run on Windows included`, and the live deck with it. Nothing else in the deck changes: the
   closing `It drives no remote pipeline and adds none to your repository.` is the owner's own,
   and its notes already say `remote anchor`.
8. **The reading pass, last, one agent.** Not a proof and in no spec (the owner, 2026-10-01).
   It is also the one reader for the docs lanes: one word for each thing across every page,
   as `references/glossary.md` has it.
   It reads, in this order: `references/glossary.md`; `references/purlin_commands.md`; the
   other references and the six formats; `agents/purlin.md`; each skill, `spec`, `build`,
   `test`, `audit`, `status`, `sign`, `drift`, `init`, `anchor`, `spec-from-code`; `README.md`
   and the docs in `docs/index.md`'s order; `CLAUDE.md`; `templates/`; the 0.10.0 section of
   `RELEASE_NOTES.md`. It reads each against the ones before it and against the code: the
   run script's command line, `sign.py`'s, setup's, and the lines the scripts print. It looks
   for a command or flag no script accepts, a path that is not there, a heading pointed at
   that is not there, a quoted line the code does not print, a statement of something removed,
   and two places telling a person or the AI to do different things for the same case. It
   fixes what is real, in one commit, `docs: the reading pass after decision 119`, and lists
   everything it found, fixed or not, in `dev/plans/d119-reports/reading.md`. It edits no spec;
   a finding that needs one is listed. One finding already made: `CLAUDE.md` cites
   `purlin_version` RULE-8, which that spec no longer carries.
9. Steps 2 and 3 again after the reading pass.
10. This repository's own Windows run, once, by the coordinator: `python3 dev/windows_run.py`.
    It pushes a run branch and uses the network; nothing else here does.
11. `dev/plans/handoff.md` gains a top section: what was built, the numbers of steps 2, 3 and
    10, the formats, the reading pass's list, and what is left for the owner.

## 9. Questions for the owner

None. The three asked are answered (2026-10-01):

1. Purlin's own Windows check is GitHub only. All Azure DevOps code and the hand-run Azure
   check go.
2. The word is "remote anchor" everywhere, 104 places in 25 files, each owned by one lane
   (section 3). The docs and the glossary say once that the copy is pinned to one version of
   its source.
3. The status line reads `22 rules to test on Windows: run purlin:test on Windows`, and every
   other line names the system the same way. The sign-off slide and the docs say `the run on
   Windows included`.

## 10. Calls this plan makes

- The run on the other system answers for the proofs tagged for it, not for every test (section 0).
- A `ci` section has the same fields as a `local` one, so `Tests run by ...` is one line for both.
- A plain `purlin:test` on a Windows machine and the project's own run there both clear the line `run purlin:test on Windows`.
- The payload's and the package's key `to_test_remote` keeps its name.
- A project's own run commits with ordinary git under the identity it sets; nothing is signed by a git host.
- Two systems in one pipeline run one after the other; Purlin merges nothing between jobs.
- This repository's own run gets a small spec, 3 rules and 4 proofs, as `purlin_version` covers `dev/bump_version.sh`.
- The specs are written by the coordinator in the base commit; `CLAUDE.md` changes there too.
- Old `ci` evidence in this repository is left for the next Windows run to rewrite.

## 11. Where this plan depends on decision 118's work

Decision 118 is committed and `main` is clean, so nothing waits on it. Three things of its
making are relied on or reworded:

1. `run_script` RULE-104, `` `--all` and `--ci` start it like any other ``, and `SlowPlan() if args.all or args.action == 'ci'` stay.
2. `summary` PROOF-56 is reworded; RULE-24 is not.
3. Its sentences naming the remote run are reworded: `docs/specs-and-anchors.md` line 200 and `references/purlin_commands.md` line 20; its formats line in `RELEASE_NOTES.md` moves to `evidence 9` and `package 10`.

The sweep's numbers (854 passed, 10 skipped) are its handoff's and were not rerun here.
