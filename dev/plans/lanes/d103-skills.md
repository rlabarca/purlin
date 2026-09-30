# Lane `skills` of decision 103

Branch `lane/d103-skills`, made from `origin/d103/base` at `e5f82d0`. Built to `d103-plan.md`
section 4, L8. One agent, no subagents.

## Summary

The spec skill gains the section `Renumbering`: the helper's dry run
(`scripts/spec/renumber.py <name> --dry-run`, lane `drift`), every line it prints shown, the
question `Do it? [y/N]`, the run without `--dry-run` on yes, nothing on anything else, and a
comment on another branch named and never touched. `After a merge conflict` points there and
reads `A moved rule's audit is read again.`; its signature clauses go. The build skill points a
number written twice or a changed test comment at `Renumbering`, and its closing names the
release run; the audit step, the gate `strong` and the `@manual` row's `purlin:sign <feature>
RULE-<n>` go. The anchor skill is `counted and audited once`; the not-applying paragraph and
`back to to sign` go. spec-from-code ends on `→ Run: purlin:audit` and says
`purlin:sign signs a release`. The quality guide, the spec format (21) and the anchor format (11)
lose per-rule signing, the minimum, the `unsigned` row and the not-applying lines; the guide's
stuck table reads two cells at either gate.

## Highest lines after the work

| Spec | Highest-Rule | Highest-Proof |
|---|---|---|
| `specs/skills/skill_spec.md` | 30 | 60 |
| `specs/skills/skill_build.md` | 19 | 48 |
| `specs/skills/skill_anchor.md` | 16 | 38 (unchanged) |
| `specs/skills/skill_spec_from_code.md` | 51 | 165 (unchanged) |
| `specs/mcp/schema_spec_format.md` | 37 | 85 (unchanged) |

## Rules and proofs

- `skill_spec`: deleted RULE-9 and PROOF-30 (a spec naming no files: its rules signed and their
  signatures not counting). Reworded RULE-26 and PROOF-56 to `A moved rule's audit is read
  again.` New RULE-29 with PROOF-59 (the dry run, `Do it? [y/N]`, the run on yes) and RULE-30 with
  PROOF-60 (a comment on another branch named, never touched).
- `skill_build`: reworded RULE-3 and PROOF-3 (the empty `Left to do` reads `Nothing left to do.`
  with `→ Run: purlin:test --release`; every outcome has its `→`). New RULE-19 with PROOF-48 (a
  number written twice goes to `Renumbering`).
- `skill_anchor`: deleted RULE-16 and PROOF-38 (signed as not applying). No new rule was needed.
- `skill_spec_from_code`: reworded RULE-3 and PROOF-3 (the third step is `→ Run: purlin:audit`).
- `schema_spec_format`: no proof quotes the collision sentence; nothing changed.
- `specs/anchor/upstream.md` and `specs/_anchors/security_no_dangerous_patterns.md`: no line names
  per-rule signing (`countersigned` in upstream PROOF-41 and PROOF-44 is sample text); unchanged.

## Tests

Own files, run whole (`test_skill_spec`, `test_skill_build`, `test_skill_anchor`,
`test_skill_spec_from_code`, `test_schema_spec_format`): 171 passed before, 172 passed after.
By file: spec 29 → 30, build 16 → 17, anchor 18 → 17, spec_from_code 31 → 31, schema 77 → 77.

`bash dev/run_tests.sh --fast`: 2208 passed, 9 skipped, 3 failed, 1 error, none in a file this
lane owns (next section).

Deliberate break: `Do it? [y/N]` dropped from `skills/spec/SKILL.md`; PROOF-59's test, `test_renumbering_shows_the_dry_run_and_asks`, failed (1 failed, 29 passed). Restored with
`git checkout -- skills/spec/SKILL.md`.

## Calls left

- `references/formats/spec_format.md`, the `> Scope:` row: its Required column still reads
  `At the gate signed` and its text `Below signed it is optional`, though under decision 103 a
  spec naming no files blocks nothing at either gate (only the sentence about its rules' signatures
  went). Making the field optional is a structural change the plan fixes at format 21, so it is
  left for the owner.
- The quality guide's `manual test` row keeps the reason `manual proof`, which C2 does not list.
- Whether a passing rule with no proof reads `no proof` in its strong cell at the gate `passed`
  too: the guide and the spec format now say it reads so, with no gate named; lane `counting`
  decides.

## Words chosen that section 7 does not give

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

## Failures in files this lane does not own

Each comes from the cloud container, not from this lane's edits:

- `dev/test_tag.py::TestTheTag::test_the_tag_is_signed_with_the_key_the_settings_name`: the
  container's global `gpg.ssh.program` is `/tmp/code-sign`, which cannot verify (`git tag -v`
  exits 1). It passes with `GIT_CONFIG_GLOBAL=/dev/null`.
- `dev/test_signatures.py::TestTheMachines::test_a_new_system_ends_nothing` and
  `test_a_system_it_names_that_is_gone_ends_it`: they expect the machine's system to be `macos`,
  and this host is Linux. Lane `signoff` deletes them anyway (the per-rule machine binding goes).
- `dev/test_states.py::TestStatusTable::test_the_table_and_the_dashboard_show_the_same_cells`
  (error): the pip `playwright` looks for `chromium_headless_shell-1243`, which `/opt/pw-browsers`
  does not hold.

## Tests that fail only because another lane has not merged

None.
