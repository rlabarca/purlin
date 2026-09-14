# Purlin commands

Thirteen skills, no permission system. Seven are the core loop; six support it. This page is
the one home of the skill one-liners: the frontmatter `description` of `skills/<name>/SKILL.md`,
the README table and the `agents/purlin.md` table all carry the sentence in the Purpose column
below, and nothing repeats it in its own words.

Plain language reaches every command. The syntax here is canonical, never required: "run the
tests" reaches `purlin:test` and "what needs reviewing" reaches `purlin:review`. Every command
ends by naming the next step, computed from the state it found.

## Core

| Command | Purpose | Who runs it, and when |
|---------|---------|------------------------|
| `purlin:spec <name>` | Scaffold or edit a feature spec in the 2-section format | An engineer's agent, or a PM or QA in Claude Code, at intake and whenever a rule turns out to be wrong |
| `purlin:build [name]` | Inject a spec's rules into context, then implement them | An engineer, on every change. With no name it reads the state |
| `purlin:test [feature]` | Run the tagged tests and print the state of every rule | An engineer, constantly. Seconds; tests only |
| `purlin:verify [feature]` | Run the tests and the breaks, then write the record | An engineer locally; CI on every push and pull request |
| `purlin:review [feature]` | Walk the review list one brief at a time | QA, or an engineer acting as QA |
| `purlin:approve <feature> [RULE-N]` | Approve a rule, a feature or a batch as a signed commit | Anyone on the approver list |
| `purlin:drift [role]` | Report what changed since the last record, by role | Everyone, at session start and before a release |

## Supporting

| Command | Purpose | Who runs it, and when |
|---------|---------|------------------------|
| `purlin:init` | Initialize a project for Purlin | An engineer, once. One question |
| `purlin:anchor <cmd>` | Create and manage anchor specs, local or pinned from elsewhere | An engineer, or a PM in Claude Code |
| `purlin:status` | Show every rule's state and the project's test strength | Anyone with a checkout, any time |
| `purlin:find [name]` | Find a spec by name and show its rules' states | An engineer, to locate one |
| `purlin:rename <old> <new>` | Rename a feature across specs, tests, approvals and records | An engineer |
| `purlin:spec-from-code [dir]` | Reverse-engineer 2-section specs from existing code | An engineer, once, on a codebase that predates Purlin |

## Syntax

```
Purlin
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Specifying
  ──────
  purlin:spec <name>              Scaffold or edit a feature spec
  purlin:spec <name> --resolve    Reconcile rule ids after a merge conflict
  purlin:spec-from-code [dir]     Reverse-engineer specs from existing code
  purlin:find [name]              Find a spec, or list them all

  Building
  ──────
  purlin:build [name]             Implement a spec's rules and their tests
  purlin:test [feature ...]       Run the tagged tests, unit tier
  purlin:test --all               Run every tier

  Proving
  ──────
  purlin:verify [feature ...]     Tests, breaks, and a record
  purlin:verify --remote          Push, wait for CI, pull the records it wrote
  purlin:verify --tag <name>      Pin this state as validated/<name>
  purlin:review [feature] [RULE-N]  Walk the review list
  purlin:approve <feature> [RULE-N ...]  Approve, as a signed commit
  purlin:approve --batch          Approve everything currently approvable

  Reporting
  ──────
  purlin:status                   Every rule's state, and the test strength
  purlin:drift [pm|design|qa|eng] What changed that the specs have not caught up with
  purlin:drift --since <N|date>   A window other than since the last record

  Project
  ──────
  purlin:init                     One question: what must be true before merge
  purlin:init --gate <level>      Raise or lower the gate afterwards
  purlin:init --ci                Add the workflow under the tested gate
  purlin:init --add <language>    Wire another language's test framework
  purlin:init --update            Bring the project up to the installed plugin
  purlin:anchor create <name>     A local anchor
  purlin:anchor add <url> --path <file>   Pin an anchor from another repository
  purlin:anchor sync [name|--all] [--check]   Advance a pin
  purlin:anchor propose <name>    Draft the change where the anchor lives
  purlin:rename <old> <new>       Rename a feature everywhere

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## What each command writes

| Command | Writes |
|---------|--------|
| `purlin:spec`, `purlin:spec-from-code` | `specs/<category>/<name>.md` |
| `purlin:build` | Code, test files, and the commit carrying the changeset |
| `purlin:test` | `.purlin/runtime/proofs/` only, which is not committed |
| `purlin:verify` | `.purlin/records/<feature>/<timestamp>-<commit7>-<runner>.json`, and the tag under `--tag` |
| `purlin:review` | Proof lines in a spec when a case is added; approval files through `purlin:approve` |
| `purlin:approve` | `specs/<category>/<feature>.approvals/<RULE-N>.<hash8>.<slug>.json`, in a signed commit |
| `purlin:init` | `.purlin/`, `specs/`, the test wiring, and the workflow when the gate needs one |
| `purlin:anchor` | `specs/_anchors/<name>.md`, and `designs/<anchor>/` on a sync |
| `purlin:rename` | Specs, markers, approval directories, record directories |
| `purlin:status`, `purlin:find`, `purlin:drift` | Nothing |

## Path resolution

Every `references/`, `templates/`, `scripts/` and `agents/` path a skill or an agent names is
relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`: `references/purlin_commands.md` means
`${CLAUDE_PLUGIN_ROOT}/references/purlin_commands.md`. The paths are written bare because the
reader is the agent, which resolves them once.

Everything else is relative to the project root: `specs/`, `designs/`, `.purlin/`, and the
project's own source and test files. A consumer project carries no `references/`, no `scripts/`
and no `templates/` of its own, so the two roots never collide over one path. A shell script
that needs the same answer outside a skill resolves it the way the hook shims do, from the two
install locations `docs/getting-started.md` names.

## Pending migrations

When `sync_status` opens with a pending-migrations advisory, stop before doing the skill's work,
print the advisory and its directive, and ask whether to run `purlin:init --update` now. A spec
written against a reading the installed plugin has moved on from is written against an answer
the next release drops.

The advisory names one migration per line with its count and the files it counted, and ends with
`→ Run: purlin:init --update`. `purlin:init --update --check` prints the same list as JSON and
writes nothing, which is what a preflight in CI runs.
