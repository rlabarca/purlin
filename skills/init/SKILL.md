---
name: init
description: Set a project up for Purlin, or bring a project Purlin 0.9.5 set up to this version
---

# purlin:init

Set a project up for spec-driven development. **Paths.** Every `references/`, `templates/` and
`scripts/` path below is inside the plugin and is reached through `${CLAUDE_PLUGIN_ROOT}`; a
project carries none of them. Pass `project_root` on every Purlin tool call: the top folder of
the git checkout you are working in.

A line marked **Stop and ask** is a question for the person: print it, end your turn, and act
only on their answer. Never answer it yourself.

## The one question

Setup asks one question and nothing else: `Commit the files setup wrote? [y/N]`. The default is
no; a yes commits them in one commit, `chore(init): set up Purlin`. It asks nothing about how the
tests run or what the project is called: the first `purlin:test` suggests the test commands, and
the project's name is read from the project's own files each time it is needed.

## Run it

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --project-root .
```

**Stop and ask** the question yourself. Pass `--yes` when they say yes to the commit; otherwise run
the script with its input empty, `< /dev/null`, so the question takes its default.

| Flag | What it does |
|------|--------------|
| `--project-root <dir>` | The top folder of the git checkout to set up |
| `--yes` | Commits setup's files that are not committed yet, without asking |
| `--update` | Brings a project Purlin 0.9.5 set up to the installed version. See below |

A second run writes no file: what is there is kept. With `--yes` it commits what the first run
wrote.

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

`--update` reads the layout Purlin 0.9.5 leaves in a project. It asks before each migration, and
you put each of its questions to the person. Three steps:

1. **List.** Run it with its input empty, so every question takes its default, no, and nothing
   changes:

   ```bash
   sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --update --project-root . < /dev/null
   ```

   It prints each pending migration with its id, what it does and the files it touches, and
   under `config` the command it proposes for each test tool with the project's own command it
   was read from.

2. **Stop and ask** the person about each migration listed and each proposed test command:
   whether to apply the migration, by what it does, and whether the command is the one the
   project uses. Take a corrected command word for word.

3. **Apply.** Pass each answer as a flag, so the script asks nothing:

   ```bash
   sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --update --project-root . --apply <id>,<id> --test-command "pytest=<command>"
   ```

| Flag | What it does |
|------|--------------|
| `--apply <id>[,<id>...]` | Applies exactly the migrations the person said yes to, and leaves the others pending |
| `--test-command <tool>=<command>` | Writes the command the person gave for that test tool, in place of the one proposed; once per tool |
| `--yes` | Applies every pending migration and uses each proposed command, when the person said yes to all of it |

A migration can leave work for a later one. Where the run ends on `→ Run: purlin:init --update`,
do the three steps again.

Between them the migrations:

- rewrite or remove each line 0.9.5 wrote into a spec that this version does not read;
- remove the files 0.9.5 kept that this version does not use, and its two git hooks;
- name each workflow that names a proof file. `--yes` and `--apply` remove none: each is kept and
  named, and the person removes it by hand;
- rewrite `.purlin/config.json` to `version` and `tests`, writing `tests` from the frameworks
  the old settings named, with the command the project runs each test tool by, and naming every
  key they drop;
- write `.purlin/evidence/` with its README;
- replace the dashboard page at the project root;
- give each proof numbered with a letter, such as `PROOF-7b`, the next free number in its spec;
- rewrite each 0.9.5 marker as one comment above the same test;
- remove what loaded 0.9.5's test plugins from the project's test configuration.

Every file it rewrites is first copied to `.purlin/runtime/update-backup/`, which git ignores.
It commits what it applied in one commit, `chore(update): migrate to <version> (<migrations>)`.
It prints one line of totals for each migration, then `Purlin left these for you:` with the
files that still hold text 0.9.5 used, and last `These need you:` with the lines the person has
to act on. Read those two parts to the person as they are. While a migration is pending the
status prints `→ Run: purlin:init --update`, and a test run stops and names it.

## When you are done

Say what was written. The script ends on the lines `purlin:status` ends on, or, with no spec yet,
on `No specs found under specs/.` and the command that writes the first one. Name the next step
from what the tree shows:

- No specs and no code: `→ Run: purlin:spec "<one sentence about what the software must do>"`.
- Code but no specs: `→ Run: purlin:spec-from-code`.
- Specs but no tests: `→ Run: purlin:build <name>`.
- Specs and marked tests: `→ Run: purlin:test`, which suggests the test commands on its first run.
