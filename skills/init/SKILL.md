---
name: init
description: Set a project up for Purlin, and change the gate later
---

# purlin:init

Set a project up for spec-driven development, and change the one setting later when the team
or the obligations change.

**Paths.** Every `references/`, `templates/`, `hooks/` and `scripts/` path below is inside the
plugin and is reached through `${CLAUDE_PLUGIN_ROOT}`. A project carries none of them. When
`python3` is not on PATH, run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" <script>
[args]`, which resolves the interpreter and execs it.

## The one question

Ask the person one question and nothing else: **what must be true before CI lets a change
merge?** There are three answers. That answer is the **gate**.

| Gate | Who it fits | What CI requires before merge | Approvals |
|------|-------------|-------------------------------|-----------|
| `tested` | one developer | every rule has a passing tagged test | none |
| `recorded` | a team of PM, designers, engineers and QA | every rule has a CI-written record at this commit, with the test strength at or above `min_strength` | advisory: anyone, by `purlin:approve` or pull request review |
| `approved` | the same team under GxP or a similar obligation | everything `recorded` requires, plus a current approval on every high and medium rule, in a signed commit by someone on the approver list | required: the approver list decides who |

The answer sets three defaults, each of which you can change afterwards: `ai_review_at` is
never, high, medium; `min_strength` is 50, 70, 80; risk and origin tags are optional,
optional, required.

## The two honest exceptions

Init asks nothing else. It reads the language and the test framework from the tree, the git
host from the remote URL, and it edits config files the way a `conftest.py` or a jest config
is already edited. Two questions remain because no answer can be read from anywhere:

1. An empty repository has nothing to detect, so init asks which language the project will be.
2. `approved` needs names, so init asks for the approver emails.

## Run it

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --project-root . --gate <level>
```

Pass `--dry-run` to print every file init would write or edit and write none of them. Read the
printed list back to the person before running it for real on a project that already has code.

| Flag | What it does |
|------|--------------|
| `--gate <level>` | Sets the gate, at setup or later. Raising adds what is missing and asks before each write. Lowering changes the setting and deletes nothing |
| `--update` | Brings a project set up by an older Purlin to the installed one. See below |
| `--ci` | Writes the CI workflow under `tested`, where it is otherwise skipped |
| `--ci --upstream-check` | Adds a scheduled job that opens a pull request or an issue when an anchor pin falls behind |
| `--add <language>` | Adds a second language: its test framework, its proof plugin, its breaks engine |
| `--dry-run` | Prints the plan and writes nothing |

Raising the gate is additive. `--gate recorded` on a project set up as `tested` writes the CI
workflow, creates `designs/` if it is missing, and prints the branch rules; it asks before
each write and touches nothing else. `--gate approved` on top of that asks for the approver
emails and lists the rules with no risk or origin tag. Lowering the gate rewrites the setting
in `.purlin/config.json` and deletes nothing: the workflow, the records and the approvals all
stay where they are, and CI simply stops requiring them.

`--add <language>` is for a repository with, say, a Python service and a TypeScript client:
init detects the second framework, installs its proof plugin beside the first, adds its breaks
engine, and records both in `.purlin/config.json`. One `purlin:verify` then runs both.

## What init writes

It writes `.purlin/config.json` with the gate, the language, the git host, the test framework
and the derived defaults; `specs/` for the two-section specs; and `.purlin/records/` with a
README saying that `purlin:verify` writes the files in it and that nobody edits them by hand.
It installs the proof plugin for the detected framework and the breaks engine for the
language, writing `[tool.mutmut]` into `pyproject.toml` when that file exists and `[mutmut]`
into `setup.cfg` otherwise. It adds a `.gitignore` block for `.purlin/runtime/`, which is
where test runs put their proof files, and copies the dashboard page so it opens from disk. It
offers a `pre-push` hook that runs `purlin:test --quick`, and installs the Claude Code hook
that refreshes the local dashboard data. It creates `designs/` with a README when the gate is
`recorded` or `approved`. Under those two gates it also writes the CI workflow. It ends by
printing every file it wrote or edited, one per line.

The config it writes looks like this, and every key after `gate` has a default the gate
implies:

```json
{
  "version": "0.10.0",
  "gate": "recorded",
  "language": "python",
  "test_framework": "pytest",
  "git_host": "github",
  "min_strength": 70,
  "ai_review_at": "high",
  "mutation_engine": "mutmut",
  "approvers": []
}
```

Read and change it with the `purlin_config` tool rather than editing the file, so a key that
the installed Purlin no longer reads is reported instead of silently kept.

## Who commits the record

The gate decides which record counts, and the label comes from git rather than from the file.
A record whose last commit was made through the git host's API by the CI identity is labelled
`ci`; one a person committed is `developer`; one that is not committed at all is `local`.
Under `tested`, a `ci` or a `developer` record counts, so the developer's own
`purlin:verify` is enough. Under `recorded` and `approved`, only `ci` counts, so the developer
stops committing records the moment the gate is raised and CI writes them instead.

## What each gate brings

Under every gate, init creates the records folder and its retention rule, documents the
approval path, and leaves risk, origin and criterion tags optional. `purlin:verify` creates
the records folder again if it is ever missing, so a project that skipped it is not stuck.

Under `recorded` and `approved`, init also writes `designs/` and the CI workflow
(`purlin.yml`), because the gate cannot be met without a CI run that writes records. When
`specs/` carries `@env(windows)`, `@env(macos)` or `@env(linux)` proofs, the workflow gets a
matrix with one job per operating system named, each running the same verify and writing its
own record. When no proof carries a tag, there is one job.

Under `approved`, init asks for the approver emails, writes them to `approvers` in
`.purlin/config.json`, prints the commit-signing setup, and lists every rule that still has no
risk or origin tag so `purlin:spec <name>` can tag them in one pass. Without an approver list,
the gate cannot be met: `sync_status` prints `→ approver list missing: run purlin:init --gate
approved` and the CI gate exits 1.

Anchor pins, the upstream-check job and the dashboard artifact are added on demand, never by
default. When a piece is missing later, the tool that needs it says so: `purlin:drift` reports
a pin behind, `purlin:status` says the gate cannot be met without a workflow, `purlin:verify`
says the breaks engine is unavailable and runs the AI review one level lower, and the review
list shows the rules waiting on an approval.

## The branch rules

Init prints these; the git host enforces them. Purlin never changes a repository's settings.

**GitHub**, three rulesets so each bypass stays narrow:

1. Require a pull request and require status checks, with the Actions app as the only bypass
   actor.
2. Restrict file paths on `.purlin/records/**` and `specs/**/*.approvals/*.ci.json`, with the
   Actions app as the only bypass actor, so a person cannot push a record or a CI approval.
3. Block force pushes and restrict deletions, with no bypass actor at all.

Under `tested`, print only the third.

**Azure DevOps**: give the build service alone Contribute on those same paths through branch
security, and turn off force push and delete.

## Commit signing under `approved`

An approval counts when the commit that added it is signed, when its author email is on the
approver list as of that commit, and when that author is not the author of the commit that
last touched the test. Print this once per approver:

```bash
git config gpg.format ssh
git config user.signingkey ~/.ssh/id_ed25519.pub
git config commit.gpgsign true
```

Then tell them to upload the same public key to the git host as a signing key, so the host
shows the commit as Verified. No git-host reviewer setting and no owners file is needed, now
or later.

The approver list lives in `.purlin/config.json` and changes by pull request like any other
file, so git history records who could approve and when. Add and remove people at any time; an
approval is judged against the list as it stood in the commit that added it.

## What CI runs

A project has no copy of Purlin in it. The workflow init writes therefore clones Purlin at a
pinned tag and runs `purlin:verify --ci` from that checkout, so the runner runs the same
verify a developer runs locally, at a version that changes only when someone edits the
workflow. The job writes its record through the git host's API, auto-approves the low-risk
rules, writes the review briefs, posts the rollup as a pull request comment, and publishes the
dashboard page and its data as the `purlin-dashboard` build artifact linked from that comment.

On a pull request from a fork the API token cannot write, so verify runs, the comment posts,
no commit is made, and the job says so in the comment.

## Bringing an older project forward

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --update --project-root .
```

`--update` detects the older layout and offers each change separately. It untracks and deletes
the proof files and the verification files that used to be committed, untracks the committed
dashboard data, rewrites the hooks, retires the config keys that no longer exist, asks the
gate question once, and rewrites an operating-system tag to `@env(...)` only where the
intended system is unambiguous. Every write asks first and every file it replaces is backed up
next to the original. While the update is pending, `sync_status` opens with
`→ Run: purlin:init --update`.

## When you are done

Say what was written, then name the next step from the state, not from a script:

- No specs yet: `→ Next: purlin:spec "<one sentence about what the software must do>"`.
- Specs but no tests: `→ Next: purlin:build <name>`.
- Code but no specs: `→ Next: purlin:spec-from-code`.
- Gate raised to `approved` with untagged rules: name them and point at `purlin:spec <name>`.
