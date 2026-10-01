# Decision 121, lane `setup`: report

Branch `lane/d121-setup`, cut from `main` at `fe512e267`. Three commits of work and this report.
Nothing was pushed, tagged, audited or signed, and no full sweep was run.

| Commit | What |
|---|---|
| `efc40fc32` | `fix(update)`: the Figma pattern, `update` RULE-55, RULE-56, PROOF-164, PROOF-165 |
| `54a19c551` | `fix(upstream)`: the two refusals of `add`, `upstream` RULE-40, PROOF-61, PROOF-62 |
| `9f1c6f957` | `test(purlin_agent)`: the four checks, `purlin_agent` RULE-20 to RULE-23, PROOF-51 to PROOF-54 |

## Test numbers

`python3 -m pytest dev/test_init_update.py dev/test_upstream.py dev/test_purlin_agent.py -q`

| File | Before | After |
|---|---|---|
| `dev/test_init_update.py` | 37 passed, 3 skipped | 39 passed, 3 skipped |
| `dev/test_upstream.py` | 25 passed | 27 passed |
| `dev/test_purlin_agent.py` | 2 passed | 6 passed |
| All three | 64 passed, 3 skipped | 72 passed, 3 skipped |

`dev/test_skill_*.py`, which import `dev/skill_checks.py`: 19 passed, as before.

Spec maxima, each as the plan gives it: `update` 56 and 165, `upstream` 40 and 62,
`purlin_agent` 23 and 54. The tree's numbers before matched the plan's (54 and 163, 39 and 60,
19 and 50). 7 rules and 8 proofs added, none reworded, none deleted.

## 1. The upgrade and a git source that holds the word `figma` (a fault)

**Seen failing first.** PROOF-165's test, run on `main`'s code, failed: the update printed
`removed the design reference from specs/_anchors/tokens.md: > Source:, > Pinned:` and wrote
`specs/_anchors/tokens.md.local-53bb1349.bak`.

**Changed.** `scripts/init/update.py`, `FIGMA_SOURCE_RE`: `^>\s*Source:\s*\S*figma\.com/`, case
ignored, as the plan gives it. Only an address at `figma.com` is a Figma source.

- RULE-56: An anchor whose `> Source:` is a git address keeps its `> Source:` and `> Pinned:` lines through the update, byte for byte
- PROOF-165 (RULE-56): An anchor whose `> Source:` is `https://github.com/acme/figma-tokens.git specs/tokens.md` with a `> Pinned:` sha of 40 characters is exactly what it was after the update with `--yes`, and no backup is written beside it

Test: `test_an_anchor_from_a_git_address_holding_figma_is_left_as_it_was`.

## 2. The upgrade's workflow removal has a proof (a missing proof, no fault)

**Changed.** No code, as the plan says. The test passes on `main`'s code. Broken on purpose once
(`_detect_workflows` taking every workflow), it failed; restored.

- RULE-55: The update removes a workflow under `.github/workflows/` only where it wrote 0.9.5's proof files, backs it up first, and leaves every other workflow as it was
- PROOF-164 (RULE-55): The sample 0.9.5 project holds `purlin-proofs.yml`, which commits `*.proofs-*.json`, and `ci.yml` running `pytest`; after the update with `--yes` the first is gone with a backup holding its bytes, `ci.yml` is byte for byte as it was, and the output holds `removed 1 workflow that committed proof files`

Test: `test_only_the_workflow_that_committed_proof_files_is_removed`.

**The fixture is not changed.** `dev/fixtures/upgrade-0.9.5/` holds one workflow,
`windows-proofs.yml`. Adding `purlin-proofs.yml` beside it would make two removed workflows and
change the line every other test reads. The test renames the fixture's workflow to
`purlin-proofs.yml` in its own copy of the project, writes its text and `ci.yml`, and commits
both before the update.

**Left open.** The review's second remark stands: `_detect_workflows` takes any workflow whose
text holds `.proofs-`, so a project's own workflow that only mentions a proof file is removed
too, with its backup. The plan says "no change: one proof", so it is not built. RULE-55's "only
where it wrote 0.9.5's proof files" is held by the marker alone.

## 3. `purlin:anchor add --name` (two faults)

**Seen failing first.** Both tests failed on `main`'s code with `(0, 'added')` where `(2,
'error')` is expected. `--name ../../outside` wrote `outside.md` at the project's root; the
taken name `no_eval` was written over.

**Changed.** `scripts/anchor/upstream.py`, `add`: the name is checked first, before the source
is looked at, fetched or anything is written. `NAME_REFUSED`, `NAME_TAKEN` and `_NAME_RE`
(`[A-Za-z0-9_]+`, the whole name) are new. The module's docstring gains one sentence.

- RULE-40: `add` refuses a name an anchor in the project already holds, writes nothing and names `purlin:anchor sync <name>`
- PROOF-61 (RULE-22): The published anchor is added with `--name ../../outside`; it exits 2, the answer reads `error`, `specs/_anchors/` stays empty and no `outside.md` exists under the folder around the project
- PROOF-62 (RULE-40): With `specs/_anchors/no_eval.md` holding the project's own rule `No eval in scripts`, the published anchor is added as `no_eval`; it exits 2, the answer reads `error`, and the file holds exactly its text from before

Tests: `test_a_name_that_leads_out_of_the_anchor_folder_is_refused`,
`test_a_name_an_anchor_already_holds_is_refused`.

**Lines a person reads**, the plan's section 6.4:

```
../../outside: not added. --name takes letters, digits and _ alone. Run purlin:anchor add <source> --path <path> --name outside.
no_eval: not added. specs/_anchors/no_eval.md already holds an anchor of that name. Run purlin:anchor sync no_eval to update it, or add it under another --name.
```

**A call this lane made.** The plan's first line opens and ends on `no_eval`. A refused name
cannot be both. The line opens on the name as given and ends on that name with every other
character taken out (`../../outside` gives `outside`, `no-eval` gives `no_eval`), so the command
it ends on can be run. `<source>` and `<path>` are printed as the plan writes them, not filled
in. A name with no letter or digit in it, such as `..`, ends on `--name source`, the existing
default of `_default_name`.

**Left open.**

- `NAME_TAKEN` names `purlin:anchor sync <name>`, as RULE-40 says. Where the anchor already
  there is the project's own, with no `> Source:`, that command answers `no anchor named
  no_eval carries a git source`. The second half of the line, `or add it under another --name`,
  is the fix that works there.
- `read_source_file` joins `--path` unchecked, as the review notes. The plan gives it no item;
  it reads a file and writes none. Not changed.

## 4. The four checks on the skills (`purlin_agent`)

**Changed.** `specs/instructions/purlin_agent.md`: `> Scope: agents/purlin.md, skills/,
references/`, and the Description gains `It also holds four checks on what every skill, the
agent definition and the references tell an agent to run.`

- RULE-20: Every path under `scripts/`, `references/`, `templates/`, `skills/` or `docs/` that a skill or the agent definition names is a file or folder in the repository
- RULE-21: Every flag a skill writes on a line that runs a script is one that script takes
- RULE-22: The answers file the sign skill shows is one `purlin:sign --answers` walks without a refusal about the file
- RULE-23: No skill, agent definition or reference names a path under `dev/`, `/dev/null` aside
- PROOF-51 (RULE-20): Each such path read out of the ten `SKILL.md` files and `agents/purlin.md` exists; the same check on a copy of the sign skill naming `scripts/review/signoff.py` lists that path
- PROOF-52 (RULE-21): Each `--flag` on a line of a `SKILL.md` naming a `scripts/**/*.py` is in that script's `--help`; the same check on a copy of the test skill passing `--remote` to `purlin_run.py` lists `--remote`
- PROOF-53 (RULE-22): The JSON block under `Step 5` of `skills/sign/SKILL.md`, written to `.purlin/runtime/signoff-answers.json` in a project whose hand checks are `accession_screen RULE-1` and `sample_age RULE-6`, is walked with `--answers`; it exits 0 and the sign-off holds the note `the tube is red`
- PROOF-54 (RULE-23): No line of `skills/*/SKILL.md`, `agents/purlin.md` or `references/**/*.md` holds `dev/` once every `/dev/null` is set aside; the same check on a copy of the build skill naming `dev/test_x.py` lists that line

**`dev/skill_checks.py`**, new readers. Each takes text, so a test reads a skill as it stands
and a changed copy the same way:

| Function | What it answers |
|---|---|
| `skill_files()`, `reference_files()` | every `skills/*/SKILL.md`, every `references/**/*.md`, read from disk when called |
| `named_paths(text)` | each path under the five folders, once; a `#section` and a closing full stop are cut; a path holding `<`, `*`, `{` or `[` names no one file and is left out |
| `absent_paths(text)` | those that are no file or folder in the repository |
| `script_flags(script)` | every `--flag` in the script's `--help`, and in each subcommand's `--help` where it has subcommands (`upstream.py add`, `sync`) |
| `passed_flags(text)`, `unknown_flags(text)` | each `(script, flag)` written after a `scripts/**/*.py` on one line; those the script does not take |
| `dev_paths(text)` | each line holding `dev/` once `/dev/null` is set aside |
| `json_block_under(text, heading)` | the first `json` block under a heading, parsed |

**`dev/test_purlin_agent.py`**, four tests, one per proof. PROOF-53 builds a real project of two
specs, runs `purlin_run.py --all --test --commit` on it, makes a throwaway key with
`sign_project.signing_key`, and runs `sign.py --answers` as a child process. No model and no
network. The file takes about 2 seconds.

**They pass on `main`'s skills now**: 11 files read for paths and flags, 27 for `dev/`, nothing
listed. Integration runs `python3 -m pytest dev/test_purlin_agent.py -q` again after lane
`words` merges.

**Each check was seen to fail once**, on the skills changed on purpose and then restored with
`git checkout -- skills references`:

| Changed | The check listed |
|---|---|
| `skills/audit/SKILL.md` naming `references/audit_criteria.md` | `{'skills/audit/SKILL.md': ['references/audit_criteria.md']}` |
| `skills/audit/SKILL.md` passing `--deep` to `purlin_run.py` | `{'skills/audit/SKILL.md': [('scripts/run/purlin_run.py', '--deep')]}` |
| `skills/sign/SKILL.md` with `"sign": "yes"` | the walk exits 0 with no sign-off written |
| `references/glossary.md` gaining `See dev/run_tests.sh.` | `{'references/glossary.md': ['See dev/run_tests.sh.']}` |

**Nothing in a skill is flagged today.** What the readers found on `main`, for whoever reads a
failure after `words` merges:

- Flags passed: `upstream.py` `--path`, `--all`, `--check`, `--json`; `purlin_run.py` `--audit`,
  `--test`, `--ci`, `--project-root`; `wording.py` `--project-root`; `markers.py`
  `--near-misses`, `--project-root`; `scaffold.py` `--project-root`, `--update`; `sign.py`
  `--show`, `--answers`, `--check`, `--version`, `--project-root`; `renumber.py` `--dry-run`.
- The one `dev/` in the 27 files is `< /dev/null` in `skills/init/SKILL.md`, line 27.

**Limits, stated.**

- A flag is checked only on a line that names a `scripts/**/*.py`, after the script's path. A
  flag in prose with no script on its line, such as `purlin:test --all`, is a command's flag
  and is not checked.
- `sign.py` and `purlin_run.py` parse their own arguments; their `--help` prints the docstring
  or a usage line. `markers.py --help` prints its usage and exits 2. The reader takes the flags
  from whatever `--help` prints, on either stream, whatever the exit code.
- PROOF-51 asserts 11 files. An eleventh skill changes the proof's "ten" and that number.
- RULE-23's check is the text `dev/`. A word ending in `dev/`, such as a folder named
  `webdev/`, would be listed.

## Edits needed in files this lane does not own

1. **`skills/anchor/SKILL.md` and `references/purlin_commands.md` (lane `words`).** Neither
   names `--name`, and the two new refusals do. Line 50 of the skill reads
   `upstream.py" add <git-url> --path <file>`. Proposed: `add <git-url> --path <file> [--name
   <name>]`, and under it one sentence: `` `--name` takes letters, digits and `_` alone. A name
   an anchor in the project already holds is refused: run `purlin:anchor sync <name>` to update
   it, or add it under another `--name`. `` The flag check passes either way: `--name` is in
   `upstream.py add --help`.
2. **`CLAUDE.md` (lane `words`)**, as the plan's section 6.7 already gives it: `` `purlin_agent`
   RULE-23 checks the `dev/` half of this line across those files; the review of each change
   holds the `specs/` half. `` The rule and its proof are now in the tree.
3. **`references/formats/anchor_format.md`** (no lane of this decision owns it). It does not
   describe `add`'s name. No change is needed for the format: the file `add` writes has not
   changed, so `> Format-Version:` stays.

## Left open, in one place

- The marker `.proofs-` still decides which workflow goes (item 2).
- `NAME_TAKEN` names `purlin:anchor sync` for a local anchor too (item 3).
- The opening name of `NAME_REFUSED` is the name as given, not the plan's `no_eval` (item 3).
- `--path` is not held under the fetched checkout (item 3).
