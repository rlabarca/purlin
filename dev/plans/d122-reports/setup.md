# Lane `setup`: report

Branch `lane/d122-setup`, cut from `main` at `e02c9b4f5`. Decision 122's part for a spec's name
(finding 1), setup's commit (finding 3), the unread proof line (finding 8) and `__pycache__/`
(finding 18). Only the lane's own files were changed.

## What was built

| File | Change |
|---|---|
| `scripts/mcp/purlin/specs.py` | `NAME = r'\w[\w-]*'` and `name_ok(name)`. `spec_mistakes` adds one `NAME_REFUSED` line per spec whose name `name_ok` refuses, after the `SAME_NAME` lines, with the `git mv` to the name with each other character, and a leading `-`, written `_`. An unread proof line is quoted whole with `TAG_AT_END` or `NOT_A_PROOF_LINE`. `PROOF_LINE_SHOWN` cuts the conflict line alone. |
| `scripts/mcp/purlin/markers.py` | `_BODY_RE`'s feature is `specs.NAME`. `_LOOSE_BODY_RE`'s feature is `\S+`, and `near_miss` answers `(None, why)` with `NAME_CHARACTERS` for a feature `specs.name_ok` refuses. |
| `scripts/anchor/upstream.py` | `_NAME_RE` is `specs.NAME`, matched whole. `NAME_REFUSED` reads `letters, digits, _ and - alone`. |
| `scripts/init/update.py` | The feature group of `PYTEST_ARGS_RE`, `TITLE_TAG_RE`, `TRAIT_RE`, `SHELL_CALL_RE` and `SQL_MARK_RE` is `specs.NAME`. |
| `scripts/init/scaffold.py` | `Plan.files` holds every file the plan named, kept or written. `to_commit` answers those git lists as new or changed and does not ignore. The docstring says the question is asked `while one of its files is on disk and not committed`. |
| `templates/gitignore.purlin` | Gains `# Python's bytecode cache, never committed` and `__pycache__/`. |
| `references/formats/spec_format.md` | `> Format-Version:` 23 to 24. "Location" says what a name holds and shows the warning. "Proof format" says a tag ends the line and shows the two warnings. |
| `references/formats/marker_format.md` | `> Format-Version:` 4 to 5. The feature is any name a spec may hold. The near miss with no fix for a name's characters. |

Contract K1 is built word for word: `NAME`, `name_ok`, `NAME_REFUSED`, `PROOF_LINE_UNREAD`,
`TAG_AT_END`, `NOT_A_PROOF_LINE` in `specs.py`, and `NAME_CHARACTERS` in `markers.py`.

## Rules and proofs, word for word

### `schema_spec_format`

Reworded:

- RULE-7: The file name is the spec's name, whatever its first line says, and a name holds letters, digits, `_` and `-` and does not start with `-`; a spec whose name holds any other character is still read, and warned of in one line naming the `git mv` that renames its file

Added:

- RULE-43: A list item under `## Proof` that cannot be read is quoted whole in its warning, with the reason: a tag standing before the rule ids goes at the end of the line, and any other line is not `- PROOF-N (RULE-N): <text>`
- PROOF-88 (RULE-7): A project holding `specs/intake/sample.age.md` is reported with `sample.age: the name holds a character other than letters, digits, _ and -, so no test comment can name it. Rename the file: git mv specs/intake/sample.age.md specs/intake/sample_age.md`
- PROOF-89 (RULE-7): A spec at `specs/intake/sample-age.md` holding one rule is read as the feature `sample-age`, and the status carries no warning naming it
- PROOF-90 (RULE-43): `login`'s proofs hold `- PROOF-7 @manual (RULE-7): A rejection message for an aged sample is clear to a technician`; the status carries `login: a line under ## Proof cannot be read, because a tag goes at the end of the line: "- PROOF-7 @manual (RULE-7): A rejection message for an aged sample is clear to a technician". Run purlin:spec login.`
- PROOF-91 (RULE-43): `login`'s proofs hold `- PROOF-7: no rule named`; the status carries ``login: a line under ## Proof cannot be read, because a proof line reads `- PROOF-N (RULE-N): <text>`: "- PROOF-7: no rule named". Run purlin:spec login.``

### `reports`

Reworded:

- RULE-1: A marker is one whole-line comment, `purlin: <feature> PROOF-<n>` or `purlin: <feature> RULE-<n>`, the feature any name a spec may hold, after any of `#`, `//`, `--`, `;`, `%` and `'`, or inside a one-line `/* */` or `<!-- -->`; a `purlin:` comment of any other shape ties nothing
- RULE-36: `markers.py --near-misses --project-root <dir>` prints one JSON array of `{"file", "line", "text", "fix", "why"}`, one entry for each comment, in a file a suite's globs match, that is nearly a marker: `purlin` misspelled by one letter, in capitals or with no space after the colon, `PROOF` or `RULE` in lower case, or a feature or id one character from exactly one that exists, whose fix is the marker it meant; a `purlin:` comment that names no id has no fix; a comment whose feature holds a character no spec's name may hold has no fix, and its why names the characters a name holds; a marker naming what a spec has, or one character from two that exist, is not listed

Added:

- PROOF-124 (RULE-1): `specs/intake/sample-age.md` has `PROOF-1`, and `tests/test_age.py` holds `# purlin: sample-age PROOF-1` above the passing `test_age`; the run prints `Markers: 1 tied to a test, 0 not tied.`, and the evidence lists `PROOF-1` as `pass`
- PROOF-125 (RULE-36): A test file carrying `# purlin: sample.age PROOF-1` is listed with no fix, and its why reads `` `sample.age` holds a character a spec's name cannot: a name holds letters, digits, `_` and `-`. ``

### `upstream`

Added:

- PROOF-65 (RULE-22): The published anchor is added with `--name sample-age`; it exits 0, and `specs/_anchors/sample-age.md` holds its rules

### `update`

Added:

- PROOF-168 (RULE-29): A test file carrying the 0.9.5 mark `@pytest.mark.proof("sample-age", "PROOF-1", "RULE-1")` carries after the update with `--yes` `# purlin: sample-age PROOF-1` where the mark was, and the output holds `rewrote 1 marker in tests/test_age.py as comments`

### `scaffold`

Reworded:

- RULE-67: A new project's `.gitignore` keeps out what a run writes locally: `/purlin-report.html`, `.purlin/runtime/` and `__pycache__/`
- RULE-70: The commit carries only setup's own files that git does not ignore and does not hold as they stand, whether this run wrote them or an earlier one did: a file the project had already staged stays staged and out of it

Added:

- PROOF-174 (RULE-70): A git project with no commit yet is set up with nothing to answer from, then set up again with `--yes`; the second run prints `Committed <sha7>, the files setup wrote:`, then `  .purlin/config.json`, `  .gitignore` and `  .purlin/evidence/README.md`, and the project has one commit, `chore(init): set up Purlin`
- PROOF-175 (RULE-70): A project whose one commit holds `README.md` and a `.gitignore` reading `node_modules/` is set up with nothing to answer from, then again with `--yes`; the commit the second run makes holds exactly `.gitignore`, `.purlin/config.json` and `.purlin/evidence/README.md`
- PROOF-176 (RULE-67): A new project set up has a `.gitignore` holding the line `__pycache__/`

Nothing was deleted. Every rule, proof and reworded line above is the plan's, section 3, word for
word.

## `> Highest-*`, before and after

| Spec | Highest-Rule | Highest-Proof | Rules | Proofs |
|---|---|---|---|---|
| `schema_spec_format` | 42, 43 | 87, 91 | 16, 17 | 29, 33 |
| `reports` | 39, 39 | 123, 125 | 22, 22 | 49, 51 |
| `upstream` | 41, 41 | 64, 65 | 18, 18 | 33, 34 |
| `update` | 56, 56 | 167, 168 | 17, 17 | 44, 45 |
| `scaffold` | 83, 83 | 173, 176 | 14, 14 | 32, 35 |

One rule and 11 proofs added, 5 rules reworded, 11 tests added. Each new proof is tied to its
test: `markers.tied_ids` holds all 11.

## What was seen failing first

Each test was written and run on `main`'s code before the code changed.

| Proof | What it showed on `main`'s code |
|---|---|
| `reports` PROOF-124 | `sample-age RULE-1 has no test for PROOF-1. Run purlin:build sample-age.`; no `Markers:` line; no `pass` |
| `reports` PROOF-125 | the why read `The comment names no <feature> PROOF-<n> or <feature> RULE-<n>.` |
| `update` PROOF-168 | the line stayed `@pytest.mark.proof("sample-age", "PROOF-1", "RULE-1")` |
| `scaffold` PROOF-174 | the second run printed seven `kept` lines and made no commit |
| `scaffold` PROOF-175 | the same seven `kept` lines; `HEAD~1` did not exist |
| `scaffold` PROOF-176 | the `.gitignore` held no `__pycache__/` |
| `schema_spec_format` PROOF-88 | no line named `sample.age` |
| `schema_spec_format` PROOF-90 | the line was cut at 60 characters and gave no reason |
| `schema_spec_format` PROOF-91 | `login: a line under ## Proof cannot be read: - PROOF-7: no rule named. Run purlin:spec login.` |
| `upstream` PROOF-65 | exit 2, `not added. --name takes letters, digits and _ alone. Run purlin:anchor add <source> --path <path> --name sample_age.` |

`schema_spec_format` PROOF-89 passed before the change: `specs.py` already read a hyphenated
file name. It holds what the fix must not break.

## Lines a person reads that this lane chose

The plan gives every printed line. These are the lane's own, all in files it owns:

- `specs/init/scaffold.md`, `> Description:`: `It asks one question, whether it may commit its
  own files that are not committed yet, and commits only those.` It read `the files it wrote`.
- `templates/gitignore.purlin`: `# Python's bytecode cache, never committed` is the plan's.
- `references/formats/spec_format.md`, "Location":
  - `A name holds letters, digits, _ and -, and does not start with -. This section is the one
    home of what a name holds: a test comment, an anchor's --name and the upgrade from 0.9.5 read
    the same name.`
  - `A spec whose name holds any other character is still read, and no test comment can name it.
    The status warns of it in one line, with the git mv that renames its file. The new name is
    the old one with each such character, and a leading -, written _:` then the plan's line.
- `references/formats/spec_format.md`, "Proof format":
  - `A tag stands at the end of the proof line, after the text, never before the rule ids:` with
    the two examples of section 6.8.
  - `A list item under ## Proof of any other form is not read as a proof. The status warns of it
    in one line that quotes the line whole and gives the reason. Where @manual, @slow or @env(
    stands between PROOF-N and the rule ids:` then the plan's line, `For any other line:` and the
    plan's line.
  - `at most one of each, in any order, at the end of the line`.
- `references/formats/marker_format.md`:
  - `The feature is any name a spec may hold, as spec_format.md, "Location", says: sample-age is
    one.`
  - the `fix` row: `the marker it meant, or null where the comment cannot be read or its feature
    holds a character no spec's name may hold`.
  - `A comment whose feature holds a character no spec's name may hold has no fix, and its why
    names the characters a name holds: for # purlin: sample.age PROOF-1 it reads` then the plan's
    line.

## Calls this lane made that the plan did not

1. **`update.py` reads `specs.NAME`, not `[\w-]+`.** Section 2.1 says one pattern, read by
   `update.py`'s five patterns; section 4.2 says each group reads `[\w-]+`. The two differ only
   for a name that starts with `-`, which no spec may have. The lane took 2.1, so there is one
   pattern.
2. **Where a tag counts as standing before the rule ids.** `TAG_AT_END` is given where `@manual`,
   `@slow` or `@env(` follows `PROOF-N` with only white space between. A line such as
   `- PROOF-7: read the @manual (see the guide)` holds `@manual` before its first `(` and is no
   misplaced tag; it gets `NOT_A_PROOF_LINE`.
3. **`Plan.files` holds kept files too.** The plan says `to_commit` is handed every file the plan
   named. The lane changed what `Plan.files` holds, since nothing else reads it.
4. **The comment above `specs.NAME`** reads ``a letter, a digit or `_`, then those and `-` ``.
   Contract K1's comment, `letters, digits and _, then those and -`, would be found by the
   integration grep for `letters, digits and _`, which must be empty.
5. **A near miss whose `PROOF` or `RULE` word cannot be read keeps the reason it had**, whatever
   its feature holds. The name's characters are named only once the id is read.

## Left, or waiting on another lane

- **Lane `words`.** `skills/anchor/SKILL.md` still says `in letters, digits and _`; section 6.8
  rewrites it. The integration grep for `letters, digits and _` finds nothing in this lane's
  files.
- **For the coordinator.** `references/formats/spec_format.md`, "The manual tag", says a hand
  check `reads checked at sign-off in its strong cell`. That stays true. Once lane `surfaces`
  lands, the passed cell reads `checked at sign-off` too until a sign-off notes it. Section 7
  gives this page no change for it, so the lane made none.
- **A `.gitignore` or `.purlin/config.json` with a person's own uncommitted edit** is now asked
  about and committed by setup, whole, as section 10 says for `.gitignore`. No proof holds the
  `config.json` case.
- Nothing else is left. No file of another lane was needed.

## Acceptance

- The six test files of the lane, with `dev/test_mcp_server.py`, after `git rebase main`
  (`main` had not moved): `236 passed, 6 skipped in 120.85s`.
- `bash dev/run_tests.sh --fast`: `1 failed, 845 passed, 9 skipped in 948.56s`. The one failure
  was the lane's own: `dev/test_mcp_server.py`, `test_the_package_imports_nothing_outside_the_standard_library`,
  which reads any line opening `from` as an import, found a docstring line of
  `specs.spec_mistakes` that opened with that word. The docstring was rewrapped, and that test
  file passes in the run above. The whole sweep was not run a second time after that one-line
  change to a docstring.
- No failure waits on another lane.
