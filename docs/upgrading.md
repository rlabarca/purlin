# Upgrading

For the developer who set a project up with Purlin 0.9.5, when this release lands.

```
purlin:init --update
```

Run it once, after the plugin updates. Its migrations read the layout Purlin 0.9.5 left and
bring the project to this release's. [RELEASE_NOTES.md](../RELEASE_NOTES.md) says what the
release changes.

A project set up with this release has nothing to upgrade, and the command says so:

```
Nothing is pending: this project is at <VERSION>.
```

Where such a project lacks a file setup writes, the same command restores it.
[A project this release set up](#a-project-this-release-set-up) shows that run.

Until a 0.9.5 project is upgraded, `purlin:status` prints only this after its first line:

```
This project was set up by Purlin 0.9.5. Nothing here counts until it is brought to <VERSION>.
→ Run: purlin:init --update
```

A test run stops, writes nothing and exits 1:

```
This project was set up by an older Purlin and not upgraded, so nothing ran. Run purlin:init --update.
```

## What the update does

The update first lists the pending migrations, each with its id, what it does and the files it
touches. Under `config` it shows the test command it proposes for each test tool. Then it asks
before each migration, each question on a line of its own:
`Apply <id>, which will <what it does>? [y/N]`.

- `y` or `yes` applies it.
- Any other answer declines it, an empty one included. A declined migration is reported as
  `skipped <id>` and stays pending. The others still run.

A run that applied nothing changes nothing and ends by saying how to apply:

```
→ Run: purlin:init --update
Nothing was applied. Add --yes to apply every migration and use each proposed test command, or --apply <id>[,<id>...] to apply the migrations named.
```

The migrations run in this order:

| Migration | What it changes |
|-----------|-----------------|
| `design-refs` | removes each spec's design reference: its Figma `> Source:` with its `> Pinned:`, and its `> Visual-Reference:` and `> Visual-Hash:` lines |
| `anchor-lines` | removes `> Requires:` and `> Global:` from every spec and `> Scope:` from every anchor, since every anchor covers the whole project |
| `os-tags` | rewrites the Windows tag 0.9.5 wrote at the end of a proof to `@env(windows)` |
| `kind-tags` | drops the tag naming the kind of test from the end of every proof |
| `untracked-files` | deletes the proof and run files 0.9.5 committed beside the specs and its cache folder, untracks the dashboard data, which stays on disk and is named in `.gitignore`, and takes out the `.gitignore` lines 0.9.5 wrote for its cache and its plugin folder |
| `hooks` | deletes the pre-commit and pre-push hooks 0.9.5 installed, and leaves a hook another tool wrote |
| `config` | writes `.purlin/config.json` holding `version` and `tests` alone, asks about the command for each test tool, and names every other key it removes |
| `evidence` | creates `.purlin/evidence/` with its README; a README the project wrote itself is kept |
| `dashboard` | replaces a `purlin-report.html` at the project root that is a link or is not the page the plugin ships; a project with no page there is left without one |
| `workflows` | asks about each workflow under `.github/workflows/` that names a proof file, and removes the ones you say yes to |
| `lettered-proofs` | gives each proof numbered with a letter, such as `PROOF-7b`, the next free number in its spec, and rewrites the marker of each test that named it |
| `markers` | rewrites each 0.9.5 marker in the project's tests as one comment above the same test, and removes each line naming what 0.9.5 used from `CLAUDE.md`, `AGENTS.md` and the files under `.claude/` |
| `plugins` | removes the test plugins 0.9.5 copied into the project and what loaded them |

Only the migrations the project needs are listed. A project with no hook from 0.9.5 has no
`hooks` migration pending.

**The settings.** The settings file ends with exactly two keys: `version`, this release, and
`tests`. The `tests` setting is written from the test frameworks the old settings named. A
framework nothing in the tree runs is dropped, with a line saying so. Settings that already
carry `tests` keep it. Each key this release does not read is taken out and named.

**The test commands.** The update looks at how the project already runs each test tool: in its
`package.json` scripts, its `Makefile` and its workflows. It proposes the command setup suggests
for the tool, started the way the project starts it, and shows both:

```
pytest: uv run --project pipeline pytest {files} --junitxml={report}
  package.json, "test:python", runs it as: uv run --project pipeline pytest pipeline/tests
Use this command for pytest? Press Enter to use it, or type the command to use instead:
```

Press Enter to use it, or type the command to use. Keep `{files}` and `{report}` in a command
you type: a run puts the test files and the report's path there.

Where several of the project's commands run one tool, the update cites the one closest to its
proposal: the one with the fewest options that run only some of the tool's tests. Where the
command it cites still carries such an option, the next line says so:

```
vitest: npx vitest run --reporter=default --reporter=junit --outputFile.junit={report} {files}
  package.json, "test", runs it as: vitest run --project unit
  The proposal leaves out --project unit, so every vitest test runs.
```

A run hands the tool the files to run, so the proposal needs no such option.
[running-and-evidence.md](running-and-evidence.md) says what each part of a test command is.

**The tags.** A proof may run over several lines, and its tags end the last of them. The update
reads a proof's line together with the lines that continue it, up to the next proof, rule,
heading or blank line. The kinds of test it drops are `@unit`, `@integration` and `@e2e`, and
every kind the project's own 0.9.5 markers name in their last field, so a project whose markers
read `[proof:cart:PROOF-1:RULE-1:browser]` loses `@browser` too. A tag followed only by a note
in brackets goes and the note stays. `@manual`, `@slow` and `@env(...)` always stay. The line of
totals counts the tags:

```
  kind-tags: dropped 438 kind-of-test tags from 49 specs: purlin:test runs every marked test
```

**The lettered proofs.** 0.9.5 allowed a proof numbered `PROOF-7b`. This release numbers a proof
with digits alone, so each lettered proof takes the next free number in its spec, and
`> Highest-Proof:` moves with it where the spec has that line. The marker of each test that
named it is rewritten, and each change is printed:

```
  lettered-proofs: renumbered 2 proofs in 1 spec and 2 markers in 2 files
    piano_roll PROOF-7b is now PROOF-23
    piano_roll PROOF-8b is now PROOF-24
```

**The markers.** Each marker 0.9.5's plugins read becomes one comment above the same test,
`# purlin: <feature> PROOF-<n>`, in the file's own comment syntax. In JavaScript and TypeScript
the comment goes above the line that opens the test, and the tag leaves the title: a tag joined
to the title with `+` goes with its `+`, so `'adds a line ' + '[proof:cart:PROOF-1:RULE-1:unit]'`
is left as `'adds a line'`.

In a Python test whose marker it rewrote, the update also removes a docstring line that holds
nothing but a 0.9.5 tag, and the docstring too where the tag was all of it. A tag inside a
sentence stays, and so does a docstring that is all its test holds:

```
  markers: rewrote 533 markers in 95 files
    removed 85 docstring lines that held only a 0.9.5 tag
```

The update then reads each file back the way a test run reads it. A marker whose test's title
cannot be read that way is named:

```
  packages/web/test/cart.test.ts:12: the title of the test under this marker cannot be read, so its result cannot be matched. Write it as one plain string.
```

Some markers cannot be placed above one test, such as one that covers a whole module. The
upgrade leaves such a marker as it was, and names it by file and line with what to do:

```
  left tests/test_module.py:3 as it was: write the marker as a comment above each test by hand
```

A marker naming a lettered proof that no spec holds is left too:

```
  left tests/test_cart.py:40 as it was: it names cart PROOF-9c, which no spec has. Write the proof with purlin:spec cart, put # purlin: cart PROOF-<n> above the test, and take the old tag out of the test's title or decorator.
```

The comment is shown in the file's own comment style, and `<n>` is the number `purlin:spec`
gives the proof.

**The agent's instructions.** In the same migration, with no question of its own, the update
removes each line that names `[proof:`, `pytest.mark.proof`, `.purlin/plugins`, `purlin:verify`
or `proofs-` from each tracked `CLAUDE.md` and `AGENTS.md`, in any folder, and each Markdown or
JSON file under `.claude/`. A list item goes whole, with the lines that continue it and the
items under it. A table row goes alone, and so does a line of a fenced code block or of the
settings between `---` lines at the top of a file; a table or a code block left empty goes. In a paragraph, the sentence that names it goes. A heading left with
nothing under it goes too. Each file is kept first under `.purlin/runtime/update-backup/`, each
line removed is in `update.log`, and one line under the totals counts them:

```
  markers: rewrote 533 markers in 95 files
    removed 4 lines that named 0.9.5 from CLAUDE.md
```

A JSON file that would no longer read as JSON, and a file of another kind under `.claude/`, is
left as it was and listed under `Purlin left these for you:`.

**The plugin's loading lines.** Every `conftest.py` in the project that loads the pytest plugin
0.9.5 copied loses the entry naming it in `pytest_plugins` and the `sys.path` line pointing at
`.purlin/plugins`. Text inside a comment or a docstring is left as it is. A `conftest.py` left
with nothing but comments, a docstring and imports nothing uses is deleted. Each file is named:

```
  plugins: removed the 3 plugin copies under .purlin/plugins/: Purlin reads the report your own test command writes
    removed conftest.py: it held only the plugin's wiring
    removed the plugin's wiring from tests/conftest.py
```

**The workflows.** 0.9.5 wrote a workflow that committed proof files. A pipeline of your own may
name a proof file too, so the update removes none on its own. For each workflow that names one
it prints the line and asks:

```
.github/workflows/purlin-proofs.yml:9 names a proof file: - run: git add '*.proofs-*.json'
Remove .github/workflows/purlin-proofs.yml? [y/N]
```

A yes keeps a copy of the file and removes it. Any other answer keeps it:

```
  .github/workflows/purlin-proofs.yml: kept. It names a proof file and may be the old Purlin workflow; remove it by hand if it is.
```

A workflow you kept holds no update pending. It is asked about again only while another
migration is pending.

**Backups.** Before a migration rewrites a file, it copies the file to
`.purlin/runtime/update-backup/`, at the file's own path under that folder. Git ignores the
folder. Delete it once the tests pass. A file the update deleted, such as a proof file beside a
spec, has no copy there: it is in git, at the commit before the update.

**One commit.** Everything the run applied lands in one commit,
`chore(update): migrate to <VERSION> (<ids>)`, naming every migration applied. A run that
applies nothing makes no commit, and the run leaves nothing uncommitted.

## Answering without typing

| Flag | What it does |
|------|--------------|
| `--yes` | asks nothing, applies every pending migration and uses each test command proposed |
| `--apply <id>[,<id>...]` | asks nothing, applies exactly the migrations named and leaves the others pending |
| `--test-command <tool>=<command>` | writes that command for the test tool, in place of the one proposed; give it once per tool |

`--yes` and `--apply` remove no workflow: each one that names a proof file is kept and named,
for you to remove by hand.

A run with `--yes` or `--apply` prints one line in place of the list of pending migrations:

```
Applying 3 migrations: anchor-lines, config, markers.
```

Answers can also be given on the command's input, one per line. Each question is then printed
on its own line with the answer taken after it.

## What you will see

The update prints one line of totals for each migration, then the commit:

```
  anchor-lines: removed the lines naming anchors from 53 specs
  config: wrote the tests setting: pytest, vitest
    pytest: uv run --project pipeline pytest {files} --junitxml={report}
    vitest: npx vitest run --reporter=default --reporter=junit --outputFile.junit={report} {files}
  markers: rewrote 533 markers in 95 files
  committed 670def1 as chore(update): migrate to <VERSION> (anchor-lines, config, markers)
```

Each file's own line is in `.purlin/runtime/update-backup/update.log`.

**The old record.** The update then says what became of it:

```
Every rule reads `not run` until the tests run again.
The `verify:` commits 0.9.5 made stay in git as the earlier record, and its receipts can be read from the commit before the upgrade, e257e2c.
Every file the update rewrote is kept as it was under .purlin/runtime/update-backup/, with each change listed in update.log there. A file it deleted is in git, at e257e2c. Delete the folder once the tests pass.
```

To read a receipt, name the commit and the file: `git show e257e2c:specs/web/cart.receipt.json`.

**What Purlin left for you.** The update lists each tracked file that still holds text 0.9.5
used, with how many of its lines do. The files that instruct an agent come first: `CLAUDE.md`,
then `AGENTS.md`, then each file under `.claude/`. The others follow, most first. It changes
none of them:

```
Purlin left these for you:
  .claude/hooks/check.sh: 1 line. Change it first: it tells the agent to write what this release does not read.
  packages/web/test/parameter_lfo.test.ts: 2 lines
  Each line counted names something 0.9.5 used: [proof:, pytest.mark.proof, .purlin/plugins, purlin:verify, proofs-. This release reads none of them.
```

At most 20 files are listed, then `and <n> more files`. A `CLAUDE.md` is listed only where
`markers` did not run. Where the lines removed told the agent to write `[proof:...]` markers,
say instead that `purlin:build` writes the markers.

**The lines that need you** come last, under `These need you:`. Each names what to do.

A test the upgrade left with its 0.9.5 marker is not counted until you rewrite it. Every status
and every run says so until none is left:

```
2 tests still carry a marker from Purlin 0.9.5, which is not read:
  tests/test_export.py:12  export RULE-3
  tests/test_lock.py:90  lock RULE-4
For each, write the proof with purlin:spec, put the comment above the test, and take the old tag out.
```

Each line names the test's file and line, then the feature and the rule its old marker names.
Over 20, the first 20 are listed and then `and <n> more`.

**The test run comes next.** A run that applied every pending migration ends on it:

```
→ Run: purlin:test --all --commit
Run it before anything else: every rule reads not run until it has.
A test that fails in that run and passes when its feature is run alone is the project's own: purlin:test <feature>.
```

A run that left a migration pending ends on `→ Run: purlin:init --update` and names each one
still pending. A test run stops until nothing is pending.

**Every rule reads `not run`.** Until that test run, `purlin:status` ends like this:

```
476 rules. 0 pass their tests.
Left to do:
  476 rules to test: purlin:test
```

**The first full run takes as long as the test suites.** `purlin:test --all --commit` runs
every test of the project.

**Lines about the project, not the upgrade.** The status and the run print notices about the
project as it stands. They were true before the upgrade too, and nothing in the upgrade is
waiting on them:

```
cart: 1 file its scope names is not written yet: src/cart/totals.py. Run purlin:build cart, or correct the path with purlin:spec cart.
1 spec names no files, so its tests run every time: patch_graph. Run purlin:spec patch_graph to add its > Scope: line.
```

A line under `Left to do` may be about the project too. This one names a comment above a test
whose proof was reworded after the test was written, which the project held before the upgrade:

```
  1 test comment to correct: purlin:build
```

A test that fails in the full run and passes when its feature is run alone, with
`purlin:test <feature>`, is a test of the project's own that does not pass every time. The
upgrade did not change it. Such a test may need more than one run alone to pass, and making it
pass every time is the project's work.

**Done, for an upgrade,** is `purlin:status` printing no `→ Run: purlin:init --update` line
and, after `purlin:test --all --commit`, a count of passing rules. A rule that still reads
`no test` or `not run` has a line under `Left to do` naming the command for it.

## A project this release set up

Purlin 0.9.5 set a project up where its settings carry no `tests` setting, or where the update
finds something 0.9.5 wrote. Every other project has nothing to upgrade. Where it lacks a file
setup writes, `purlin:status` ends with `→ Run: purlin:init --update` above its count, and the
command restores the file. It restores four:

| File | What is restored |
|------|------------------|
| `.gitignore` | the lines for `.purlin/runtime/` and `.purlin/report-data.js`, where one is missing |
| `.purlin/config.json` | `version`, where it is not this release; `tests` stays as it is |
| `.purlin/evidence/README.md` | the README, where there is none |
| `purlin-report.html` | the page the plugin ships, where the page at the project root is another |

The run lists each file with what the file is for, and asks about each:

```
2 files to restore in /work/shop:
  .gitignore: keeps .purlin/runtime/ and .purlin/report-data.js out of git: each run writes them again
  .purlin/evidence/README.md: says what the evidence folder holds

Restore .gitignore? [y/N]
Restore .purlin/evidence/README.md? [y/N]
```

A run that restored nothing ends by saying how to restore:

```
→ Run: purlin:init --update
Nothing was restored. Add --yes to restore each file.
```

With `--yes` it asks nothing. It prints one line for each file restored and the commit that
carries them, then ends as `purlin:status` ends:

```
Restoring 2 files: .gitignore, .purlin/evidence/README.md.
  restored .gitignore: keeps .purlin/runtime/ and .purlin/report-data.js out of git: each run writes them again
  restored .purlin/evidence/README.md: says what the evidence folder holds
  committed 4f0c2ab as chore(update): restore .gitignore, .purlin/evidence/README.md

8 rules. 8 pass their tests.
Left to do:
  1 feature whose results are not committed: purlin:test --commit
```

The run changes no spec, no test and no evidence, so every rule reads as it did. Its commit is
a change to the project like any other, and the ending names what that leaves to do. It keeps no
copy of a file: the commit shows each change. A file you declined is printed as
`skipped <file>`, and the ending then starts with `→ Run: purlin:init --update`.

## When it refuses

Each refusal names what is wrong and what fixes it, and changes nothing more.

| What it prints | Exit |
|---|---|
| `There is no .purlin/ under <folder>, so there is nothing to update. Run purlin:init first.` | 2 |
| `<id> is not a migration. The migrations are: <ids>.` | 2 |
| `.purlin/config.json cannot be read: <the reader's message> at line <n>. Fix the file by hand; nothing ran and nothing was saved.` | 1 |
| `The changes are staged and not committed: <git's own message>` where git refuses the commit | the changes stay staged |

## After the upgrade

Run `purlin:test --all --commit`. The evidence 0.9.5 kept is gone with its files, so every rule
reads `not run` until its tests run under this release.

From there the loop is the one [getting-started.md](getting-started.md) walks.
[how-purlin-works.md](how-purlin-works.md) is the model in one page.
