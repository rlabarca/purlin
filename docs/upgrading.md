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

While a migration is pending, `purlin:status` carries `→ Run: purlin:init --update`, and a test
run stops, writes nothing and exits 1:

```
This project was set up by an older Purlin and not upgraded, so nothing ran. Run purlin:init --update.
```

## What the update does

The update first lists the pending migrations, each with its id and what it does. Then it asks
before each one: `Apply <id>, which will <what it does>? [y/N]`.

- `y` or `yes` applies it.
- Any other answer declines it, an empty one included. A declined migration is reported as
  `skipped <id>` and stays pending. The others still run.

The migrations run in this order:

| Migration | What it changes |
|-----------|-----------------|
| `design-refs` | removes each spec's design reference: its Figma `> Source:` with its `> Pinned:`, and its `> Visual-Reference:` and `> Visual-Hash:` lines |
| `anchor-lines` | removes `> Requires:` and `> Global:` from every spec and `> Scope:` from every anchor, since every anchor covers the whole project |
| `os-tags` | rewrites the Windows tag 0.9.5 wrote at the end of a proof line to `@env(windows)` |
| `kind-tags` | drops the tag naming the kind of test from every proof line |
| `untracked-files` | deletes the proof and run files 0.9.5 committed beside the specs and its cache folder, and untracks the dashboard data, which stays on disk and is named in `.gitignore` |
| `hooks` | deletes the pre-commit and pre-push hooks 0.9.5 installed, and leaves a hook another tool wrote |
| `config` | writes `.purlin/config.json` holding `version` and `tests` alone, and names every other key it removes |
| `evidence` | creates `.purlin/evidence/` with its README; a README the project wrote itself is kept |
| `dashboard` | replaces a `purlin-report.html` at the project root that is a link or is not the page the plugin ships; a project with no page there is left without one |
| `workflows` | removes the workflow 0.9.5 wrote to commit proof files |
| `markers` | rewrites each 0.9.5 marker in the project's tests as one comment above the same test |
| `plugins` | removes the test plugins 0.9.5 copied into the project and the wiring that loaded them |

Only the migrations the project needs are listed. A project with no hook from 0.9.5 has no
`hooks` migration pending.

**The settings.** The settings file ends with exactly two keys: `version`, this release, and
`tests`. The `tests` setting is written from the test frameworks the old settings named. A
framework nothing in the tree runs is dropped, with a line saying so. Settings that already
carry `tests` keep it. Each key this release does not read is taken out and named:

```
  removed from .purlin/config.json: digest, pre_push, report, spec_dir
  wrote the tests setting: pytest
```

**The markers.** Each marker 0.9.5's plugins read becomes one comment above the same test,
`# purlin: <feature> PROOF-<n>`, in the file's own comment syntax. Every other line stays as it
was:

```
  rewrote 2 markers in tests/test_login.py as comments
```

Some markers cannot be placed above one test, such as one that covers a whole module. The
upgrade leaves such a marker as it was, and names it by file and line with what to do:

```
  left tests/test_module.py:3 as it was: write the marker as a comment above each test by hand
```

**Backups.** Before a migration rewrites a file, it copies the file beside it as
`<name>.local-<sha8>.bak`. The eight characters are the start of the SHA-256 of the file's
bytes. The backups are the only files the run leaves uncommitted.

**One commit.** Everything the run applied lands in one commit,
`chore(update): migrate to <VERSION> (<ids>)`, naming every migration applied. A run that
applies nothing makes no commit.

`--yes` asks nothing and applies every pending migration.

## When it refuses

Each refusal names what is wrong and what fixes it, and changes nothing more.

| What it prints | Exit |
|---|---|
| `There is no .purlin/ under <folder>, so there is nothing to update. Run purlin:init first.` | 2 |
| `.purlin/config.json cannot be read: <the reader's message> at line <n>. Fix the file by hand; nothing ran and nothing was saved.` | 1 |
| `The changes are staged and not committed: <git's own message>` where git refuses the commit | the changes stay staged |

## After the upgrade

Run `purlin:test --all --commit`. The evidence 0.9.5 kept is gone with its files, so every rule
reads `not run` until its tests run under this release.

From there the loop is the one [getting-started.md](getting-started.md) walks.
[how-purlin-works.md](how-purlin-works.md) is the model in one page.
