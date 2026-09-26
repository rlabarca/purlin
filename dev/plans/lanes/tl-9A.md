# Lane 9A: the guard sees across line breaks, the scope hash reads git, the counts test stops chasing itself

Plan: `dev/plans/three-levels.md` (Part A, decisions 23 to 27). Rules:
`dev/plans/lanes/tl-_rules.md` (in full). Worktree `/Users/richlabarca/LocalCode/purlin-wt/9A`,
branch `lane/9A` off `lane/8B`. **Do not push. Do not open a pull request.** Your work stays
committed on your branch.

Nine defects, each with its fix. One commit per numbered group is fine; every commit green.

## 1. Stale words the guard could not see

Lane 8B found these by scanning paragraphs with line breaks collapsed:

- `skills/sign/SKILL.md` near line 45: "its `strong` cell reads `needs a person`" becomes the
  three words the code emits, `manual test`, `manual audit` or `held`.
- `designs/README.md`: "stales the approvals of that anchor's rules" becomes signatures.
- `scripts/mcp/purlin/specs.py`: the docstring line "does not stale the approvals that bind
  it" is rewritten (signatures), not marked; the marker is for detection code only.
- `scripts/mcp/purlin/drift.py` near line 16, `scripts/run/purlin_run.py` near line 1033,
  `tools/QA/purlin-qa-report.md`: "rules that need a person" in prose becomes "rules on the
  review list" (then `bash dev/pack_tools.sh` for the QA archive).
- `scripts/run/records.py` `write_record` docstring: `purlin-record/1` becomes
  `purlin-record/2`.

Then make the guard see what 8B saw: in `dev/test_vocabulary.py`, match each pattern against
the file's text with every run of whitespace including newlines collapsed to one space (keep
the per-line pass for the `MARKED` and `ALLOWED_PHRASES` logic; add the collapsed pass and
report the line number of the first character of the hit). Add a test in
`dev/test_vocabulary.py` or beside it that a two-line fixture spelling `needs a\nperson` is
caught. Run the guard over the tree and fix whatever else it now finds.

## 2. The scope hash reads git, not the disk

`scripts/mcp/purlin/specs.py` `scope_tree` walks a scoped directory with `os.walk`, so an
untracked file a test left on one machine changes the hash on that machine alone; on this Mac
every `records` rule read `code changed` for a fixture directory CI had dirtied. Change the
directory branch to list tracked files only: `git ls-files -- <dir>` from the project root,
sorted, falling back to the walk when git is unavailable. A scoped file named directly keeps
today's behaviour. The spec that pins `scope_tree` (find it: `grep -rn "scope tree\|scope_tree"
specs/`) gets its rule reworded and a proof that an untracked file under a scoped directory
does not change the hash; the test goes beside the existing scope-tree tests.

## 3. `remote_url` is emitted

`dev/fixtures/report/team.json` and `regulated.json` carry `remote_url`, and
`scripts/report/src/app.js` `webRemote()` turns it into file links on the git host, but
`scripts/mcp/purlin/payload.py` never writes it. Emit it: `git remote get-url origin`, or null
with no remote, as the top-level key `remote_url`. Add it to `solo.json` as null. Update the
payload's docstring, `specs/mcp/states.md` or the payload's spec (whichever pins the top-level
keys; `grep -rn "generated_by" specs/`), and lane 1A's fixture-contract test so the key set
still matches.

## 4. The counts test stops chasing itself

`dev/test_purlin_version.py` RULE-9 compares the counts line in `RELEASE_NOTES.md` against
`.purlin/runtime/last_sweep.json`, which the previous sweep wrote. In a fresh checkout the
first sweep skips the test, the record then reads one lower than the true count, and the
second sweep fails; the fix has been to seed the file by hand. Redesign so the comparison is
made by the sweep itself, after it knows its own counts: `dev/run_tests.sh` gains one last
suite, `Counts line`, that reads the line from `RELEASE_NOTES.md` and compares it with the
counts the sweep just accumulated (including this suite as passed), prints both and fails the
sweep on a mismatch; a mismatch names the line to write. The pytest test keeps leg (a), that
the sweep's writer produces the record, and drops the self-comparison; RULE-9's proof moves to
a shell proof marker on the new suite (the shell plugin's marker form is in
`references/formats/proofs_format.md`). `specs/instructions/purlin_version.md` RULE-9 and its
proofs follow; `CLAUDE.md` "Releasing" and `dev/plans/TODO-0.10.0.md` item 29 say the new
shape in one sentence. Prove it end to end: a fresh clone of your worktree into a temporary
directory, `bash dev/run_tests.sh --fast` twice, both green, no hand seeding.

## Acceptance

```
pytest dev/test_vocabulary.py dev/test_mcp_server.py dev/test_purlin_version.py dev/test_records.py dev/test_skills.py
bash dev/run_tests.sh      (green, and the new Counts line suite in its output)
git clone -q . /tmp/purlin-9a-clone && cd /tmp/purlin-9a-clone && bash dev/run_tests.sh --fast && bash dev/run_tests.sh --fast   (both green)
```

Report in the DONE shape of `tl-_rules.md` with the spec maxima per touched spec, the test
delta, what the widened guard found beyond the list above, and decisions.
