# Lane `words`, decision 119

Branch `lane/d119-words`, cut from `main` at `49ca1c26e`. Nothing pushed.

## Tests

`python3 -m pytest dev/test_skill_*.py dev/test_purlin_agent.py dev/test_purlin_output.py -q`

| | Passed | Failed | Skipped |
|---|---|---|---|
| Before | 27 | 0 | 0 |
| After | 27 | 0 | 0 |

The 14 test files under `dev/` that read a skill, the agent or a reference: 115 passed before,
115 after. No test waits on another lane.

- Deleted: 0. Added: 0.
- Rewritten, 4:
  - `skill_test PROOF-55`, `test_the_shipped_skill_file_names_its_command_and_four_paths`: one
    command, four paths, `references/evidence_and_signoff.md` among them.
  - `skill_test PROOF-52`, `test_a_copy_without_the_evidence_and_signoff_reference_is_reported`.
  - `skill_status PROOF-37`, `test_the_status_skill_names_each_of_its_six_commands`.
  - `skill_sign PROOF-63`, `test_the_sign_skill_holds_each_of_its_seven_commands`.
- `purlin_agent PROOF-49`: its list loses `purlin:test --remote`; its words did not change.
- Appendix A's script over the four test files: `0 gone, 0 reworded, 9 right as they stand.`
- The break: every `references/evidence_and_signoff.md` taken out of `skills/test/SKILL.md`
  failed the tests of `skill_test PROOF-55` and `PROOF-52`; restored with `git checkout --`.

## The greps of plan section 8, over this lane's files

All empty, with one hit that is not a finding: `skills/init/SKILL.md:28` holds `< /dev/null`,
which the fourth grep reads as a path under `dev/`. The line was there before and is not a path
into this repository.

## Lines chosen here, word for word

The plan gave the place and not the whole sentence for these.

- `skills/test/SKILL.md`, opening: "The hand-off to a sign-off is `purlin:test --all --commit`,
  and the project's own run for the proofs tagged for another operating system (Step 5)."
- `skills/sign/SKILL.md`, after the walk's example: "There is one `Tests run by` line per run
  the results come from, this machine's first. The audit's line shows only where the audit read
  a rule."
- `skills/init/SKILL.md`: "Setup sets up no signing: `purlin:sign` checks for a key to sign with
  and, when there is none, shows the commands that set one up." (The runner paragraph's second
  half, kept; "either" dropped with the sentence it answered.)
- `agents/purlin.md`, NEVER 3: "No Purlin command pushes." in place of the exception.
- `references/purlin_commands.md`: "No Purlin command pushes. Every push is yours: a sign-off
  ends on a line starting `Push`, with the `git push origin` command, and pushing is your act."
  And, under the folder sentence: "the project's own run on another system writes its section
  under `.purlin/evidence/ci/`. Both sources count."
- `references/purlin_commands.md`, "What each command writes", `purlin:test`: the row ends at
  the `tests` entry sentence; everything on `--remote` is gone and nothing replaces it.
- `references/evidence_and_signoff.md`: "A run on another system writes its own section under
  `.purlin/evidence/ci/` and commits it with `--commit`."; "`ci`, written by a project's own run
  on another system"; "the machine, which is the host's name under both sources."; "A result
  from a run on another system counts on the same terms."; "every test, here and through the
  project's own run for any other system, then the commit of the results that come back."
- `references/glossary.md`, evidence: "the **machine** it ran on, the host's name."
- `references/spec_quality_guide.md`: "in a remote anchor the tag is written in its source."
  and "on a remote anchor's rule it is never allowed".
- `RELEASE_NOTES.md`, line 47: "Your project's own run on another system writes
  `.purlin/evidence/ci/<feature>.json`."; line 111 (`purlin:test --remote` with no `gh`) is
  deleted outright; "A remote anchor is copied as its source holds it."

Everything else is plan section 4, word for word.

## Differences from the plan

- "Remote anchor" counts: `glossary.md` 2 (as planned), `spec_quality_guide.md` 2 (the plan
  says 1: the checklist's third line and the line on narrowing a proof), `RELEASE_NOTES.md` 1.
- `spec_quality_guide.md` line 91, "an anchor other projects pull", stays: it speaks of the
  source, not of the copy.
- Two test functions were renamed with their proofs (`PROOF-55`, `PROOF-63`) so that the test
  itself changes after the proof's rewording; their lists sit above the function.

## Open, not decided here

1. `agents/purlin.md` NEVER 3 says the agent never pushes. `skills/test/SKILL.md` Step 5 says
   the agent starts the project's own run on a yes. Where a project's run starts on a push,
   starting it is a push by the agent, with the person's yes. No decision says which line
   holds. Both are written as the plan has them.
2. `skills/sign/SKILL.md` and `skills/status/SKILL.md` show `purlin:test on <System>` where a
   command is expected. It is the plan's wording and is an instruction, not a command line the
   run script reads.
3. The plain-language pass over the references went as far as the lines section 4 names. The
   other prose of the five references was not rewritten.

## Failures in files this lane does not own

None seen.
