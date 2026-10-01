---
name: init
description: Set a project up for Purlin
---

# purlin:init

Set a project up for spec-driven development. **Paths.** Every `references/`, `templates/` and
`scripts/` path below is inside the plugin and is reached through `${CLAUDE_PLUGIN_ROOT}`; a
project carries none of them. Pass `project_root` on every Purlin tool call: the top folder of
the git checkout you are working in.

## The one question

Setup asks one question and nothing else: `Commit the files setup wrote? [y/N]`. The default is
no; a yes commits them in one commit, `chore(init): set up Purlin`. It asks nothing about how the
tests run or what the project is called: the first `purlin:test` suggests the test commands, and
the project's name is read from the project's own files each time it is needed.

## Run it

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --project-root .
```

Ask the person the question yourself. Pass `--yes` when they say yes to the commit; otherwise run
the script with its input empty, `< /dev/null`, so the question takes its default.

| Flag | What it does |
|------|--------------|
| `--project-root <dir>` | The top folder of the git checkout to set up |
| `--yes` | Commits the files setup wrote without asking |
| `--update` | Brings a project Purlin 0.9.5 set up to the installed version. See below |

A second run writes no file: what is there is kept.

## What setup writes

It writes `.purlin/` and `specs/`; `.purlin/config.json`; a block in `.gitignore`; and
`.purlin/evidence/` with one README saying what the folder holds. The folder for anchors,
`specs/_anchors/`, is made when the first anchor is written. It installs nothing in the project's
tests, and adds no git hook, no background job and no pipeline. The `.gitignore` block covers `.purlin/runtime/`, where a run's reports
land, `.purlin/report-data.js`, and `purlin-report.html`, the dashboard page, which opens from
disk. `.purlin/evidence/` stays tracked. It prints every file it wrote, kept or copied, one per
line, then asks its question.

The settings file holds two keys and no other; `version` is the plugin's `VERSION` file:

```json
{
  "version": "<the plugin's VERSION file>",
  "tests": []
}
```

`tests` starts empty. The first `purlin:test` suggests a command for each test tool it recognises,
each with the flag that writes the report Purlin reads, and writes them together once the person
agrees. `references/supported_frameworks.md` shows every entry, and
`references/formats/marker_format.md` is the contract. Read and change the file with the
`purlin_config` tool rather than by hand, so a key the installed Purlin does not read is reported
instead of kept.

Setup sets up no signing: `purlin:sign` checks for a key to sign with and, when there is none,
shows the commands that set one up.

## The refusals

Each names what is wrong and what fixes it, and writes nothing more:

- `This is not a git repository. Run git init, then purlin:init.`, exit 2.
- `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`, exit 1.
- `The files setup wrote are staged and not committed: <git's own message>`, where git refused
  the commit: fix what git named and commit them.

## Bringing a 0.9.5 project forward

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --update --project-root .
```

`--update` reads the layout Purlin 0.9.5 leaves in a project and lists each pending migration
with the files it touches. It asks before each one, with a question ending `[y/N]`, and a
declined one is left pending. Between them the migrations:

- rewrite or remove each line 0.9.5 wrote into a spec that this version does not read;
- remove the files 0.9.5 kept that this version does not use, and its two git hooks;
- rewrite `.purlin/config.json` to `version` and `tests`, writing `tests` from the frameworks
  the old settings named and naming every key they drop;
- write `.purlin/evidence/` with its README;
- replace the dashboard page at the project root;
- rewrite each 0.9.5 marker as one comment above the same test;
- remove the wiring 0.9.5 put in the project's test configuration.

Every file it rewrites is backed up beside the original as `<name>.local-<sha8>.bak`. It
commits what it applied in one commit, `chore(update): migrate to <version> (<migrations>)`.
While a migration is pending `sync_status` prints `→ Run: purlin:init --update` above its
summary, and a test run stops and names it.

## When you are done

Say what was written. The script ends on the lines `purlin:status` ends on, or, with no spec yet,
on `No specs found under specs/.` and the command that writes the first one. Name the next step
from what the tree shows:

- No specs and no code: `→ Run: purlin:spec "<one sentence about what the software must do>"`.
- Code but no specs: `→ Run: purlin:spec-from-code`.
- Specs but no tests: `→ Run: purlin:build <name>`.
- Specs and marked tests: `→ Run: purlin:test`, which suggests the test commands on its first run.
