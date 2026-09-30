# Lane `skills` of decision 102: report

Branch `lane/d102-skills`, made from `origin/d102/base` at `24cf528`. Files written: the lane's
own, `skills/{spec,sign}/SKILL.md`, `specs/skills/{skill_spec,skill_sign}.md`,
`dev/test_skill_{spec,sign}.py`, `references/spec_quality_guide.md`, and this report.

## Highest lines after the work

| Spec | `> Highest-Rule:` | `> Highest-Proof:` |
|---|---|---|
| `specs/skills/skill_spec.md` | 24 → 28 | 54 → 58 |
| `specs/skills/skill_sign.md` | 24 → 28 | 53 → 58 |

New: `skill_spec` RULE-25 to RULE-28, PROOF-55 to PROOF-58; `skill_sign` RULE-25 to RULE-28,
PROOF-54 to PROOF-58. Every new proof has a marked test of its own and is at most 60 words.

## Tests

- `dev/test_skill_spec.py` and `dev/test_skill_sign.py`: 53 passed before, 62 passed after
  (skill_spec 25 → 29, skill_sign 28 → 33).
- `bash dev/run_tests.sh --fast`: 2150 passed, 12 skipped, 3 failed, 1 error. The same four fail
  on `origin/d102/base` untouched (checked in a worktree), so none comes from this lane. They are
  listed under "Failures in files this lane does not own".
- Deliberate break: the rename advice put back in `skills/spec/SKILL.md` in place of the
  sentence that keeps the default branch's number; `test_the_number_on_the_default_branch_keeps_it`
  (PROOF-55) failed; the file was restored with `git checkout -- skills/spec/SKILL.md` and both
  files pass again.

## Rules and proofs reworded (none deleted)

- `skill_spec` RULE-17 and PROOF-46: were "keep both rules, give the incoming one the next free
  number, moving its test markers and signature filenames"; now the skill says to run
  `purlin:drift`, which names every number written twice and which line moves, and to tell the
  person whose line moved.
- `skill_sign` RULE-5 and PROOF-5: the first condition is now "The last commit that touched the
  file is signed, with any key, and that signature verifies" (C9).

## Line ceilings

`skills/sign/SKILL.md` 179 → 184 (ceiling 185; its ceiling test pads a copy to exactly 185, so
184 is the most it can hold). To fit, the `Left to do` example block in Step 2 became one inline
example, `3 rules to sign: purlin:sign`, and the `Signed 8 rules as ...` line left Step 7's
example, since Step 5 already shows it. `skills/spec/SKILL.md` 168 → 173 (ceiling 210).

## Words chosen that section 7 does not give

Sign skill:
- Step 3: "Under each proof that is not `@manual` it shows the test tied to it, ... or
  `    tied to no test`: read that test before you answer." The example tied line uses PROOF-200's
  `tests/test_login.py::test_valid_credentials_return_200`.
- Step 4: "A feature whose spec writes a number twice or holds a line left from a merge conflict
  is refused too: the script prints `<SPEC_REFUSED filled for login>`, writes nothing and exits 1.
  The walk and `--all` never reach its rules."
- Step 5 table: the ends-cell of the first row reads both reasons,
  `the commit that added it is not signed`; `the signature on the commit that added it does not verify`.
- Step 6: "It exits 1 too on a broken spec, `<NO_TAG_SPEC filled>`, and while the branch's copy on
  the host, as last fetched, holds commits this checkout lacks: `<NO_TAG_BEHIND filled>`. It never
  fetches." The release-branch sentence is section 7's first sentence alone; its second
  ("New specs land on the default branch ...") was left out for the ceiling.
- Step 7, two closing rows: `No tag: <feature> cannot be counted:` or `<feature> is not signed:`
  → `→ Run: purlin:spec <feature>`; `No tag: <ref> holds <n> commit(s) that <sha> does not` →
  `→ Pull, then run: purlin:test --commit`.

Spec skill: section 7's paragraph word for word, with `purlin:drift` and `failed` set in code as
`references/writing_style.md` asks of machine text.

Quality guide, beyond section 7's "Where the risk is" (placed under "Writing proofs", after "At
least one failure case or boundary"):
- A stuck row: `passed` | `failed`, with `<RULE-N or PROOF-N> is written twice in the spec` or
  `the spec holds a line left from a merge conflict` | "The spec writes a number twice or holds a
  line git left from a merge conflict, so every rule of it reads `failed` whatever its tests
  show." | "`purlin:spec`: renumber the line from the branch not yet merged, or take out the
  conflict lines."
- The `unsigned` row gains "A signature that ended says so:
  `the signature by <signer> ended because <cause>`."
- "Manual proofs": "keep the rule's `> Scope:` tight: when a scope file changes, the signature
  ends and someone must look again" was no longer true under C8; it is replaced by the first
  sentence of section 7's hand-check row.

## Calls left

- `docs/specs-and-anchors.md` and `docs/team-workflow.md` still carry "incoming one" and
  "signature filenames"; they are lane `words`'s.
- The sign skill says nothing of the ended-signature line (C4); section 4 does not ask it to.

## Failures in files this lane does not own

All four fail the same way on `origin/d102/base`; the cause is this cloud container:
- `dev/test_tag.py::TestTheTag::test_the_tag_is_signed_with_the_key_the_settings_name`: the
  container's `/root/.gitconfig` sets `gpg.ssh.program /tmp/code-sign`, which supports only
  `-Y sign`, so `git tag -v` fails.
- `dev/test_signatures.py::TestTheMachines::test_a_new_system_ends_nothing` and
  `::test_a_system_it_names_that_is_gone_ends_it`: they expect the running machine to record
  `macos`; this one records `linux`.
- `dev/test_states.py::TestStatusTable::test_the_table_and_the_dashboard_show_the_same_cells`
  (error at setup): the pip `playwright` looks for `chromium_headless_shell-1243`, absent under
  `/opt/pw-browsers`.

## Tests that fail only because another lane has not merged

None.
