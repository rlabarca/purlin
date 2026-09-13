---
name: init
description: Initialize a project for Purlin
---

Set up a project for spec-driven development. Creates `.purlin/`, `specs/`, detects the test framework, and scaffolds the proof plugin.

**Pending migrations:** see `references/purlin_commands.md#pending-migrations`. `purlin:init --update` (Step 5d) is what clears them.

## Usage

```
purlin:init                             Full setup (all steps)
purlin:init --force                     Re-run full setup
purlin:init --add-plugin <source>       Add a proof plugin
purlin:init --sync-audit-criteria       Sync external audit criteria
purlin:init --audit-llm                 Change audit LLM (default/external)
purlin:init --set <key> <value>         Change one setting: pre_push, report,
                                        digest, mutation_checks, quality_gate
purlin:init --ci [github]               Write the CI workflow that runs the gate
purlin:init --update                    Bring the project up to the installed plugin
purlin:init --update --check            Report what is pending; write nothing
purlin:init --update --platform-id <id> What a legacy @windows tag becomes (default: windows)
purlin:init --update --mutation-checks on|off
                                        Answer the mutation-check question during the update
```

Each `--flag` runs ONLY that step, not the full init.

**Who does what.** This skill asks the questions; `scripts/init/scaffold.py` writes the files, exactly as `scripts/update/migrate.py` performs `--update`. The script handles the full init, the `--force` re-run (Steps 1, 2, 4, 5, 5b, 7 and 7a) and the single-step re-answers: it takes one long flag per setting as an answer, and `purlin:init --set <key> <value>` asks that one setting's own question and then runs the script with `--force` and the single flag the key maps to (the mapping is the table under **Single-step re-answers** in Step 2). `--ci` is a seventh answer the script takes, asked the same way and written the same way (see **Subcommand: --ci**). `--add-plugin`, `--sync-audit-criteria` and `--audit-llm` stay agent-driven; `--update` is `scripts/update/migrate.py` (Step 5d), whose MCP migration is Step 5c.

## Step 1 — Pre-flight

- **Git check (mandatory):** Run `git rev-parse --git-dir`. If it fails, the project is not a git repository. Print: `"Purlin requires git. Run 'git init' first."` Stop. Do NOT proceed without git — proofs, receipts, manual stamps, drift detection, and the pre-push hook all depend on git.
- If `.purlin/config.json` exists and `--force` is not set: "Project already initialized. Use `--force` to re-initialize." Stop.
- If it exists and `--force` is set: proceed. The scaffolder keeps every key the existing `config.json` carries that this run does not re-answer (`platforms`, `audit_criteria`, `audit_llm` among them), and keeps every plugin copy, wiring file, hook and dashboard already on disk.

The scaffolder re-checks all three: it prints the same git line and exits 2 without git, and exits 1 naming `--force` on an already-initialized project. Asking first is what keeps the user from watching a command fail; the script refusing is what keeps a half-initialized project from existing.

## Step 2 — Scaffold the Project

Ask the questions in Steps 3, 5b, 7, 7a and 7d first, then run the scaffolder
once with the answers. It writes every file init creates and prints one line
per path:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" \
  --project-root . \
  --test-framework <auto|id|id,id> \
  --pre-push <warn|strict|off> \
  --digest <auto|warn|off> \
  --report <on|off> \
  --mutation-checks <on|off> \
  [--remote-verification <required|optional|off>] \
  [--quality-gate <off|deterministic>] [--force] [--dry-run]
```

```
.purlin/
  config.json         # from templates/config.json, version from VERSION
  plugins/            # the selected frameworks' proof plugins
specs/
  _anchors/           # anchor specs go here
```

Every value above is an answer the user gave. The script decides nothing that
was asked: it reads `templates/config.json`, writes the answers over it, stamps
`version` from `${CLAUDE_PLUGIN_ROOT}/VERSION`, and never writes a proof entry,
a receipt or a commit. `--dry-run` prints the same plan and writes nothing,
which is what to run when the user wants to see the plan before agreeing to it.

**Single-step re-answers.** `purlin:init --set <key> <value>` changes one
setting on a project that is already initialized. Ask only that setting's own
question, then run the scaffolder with `--force` and the one flag the key maps
to. These five keys and no others:

| `--set` key | Values | What this skill runs |
|---|---|---|
| `pre_push` | `warn`, `strict`, `off` | `scaffold.py --force --pre-push <value>` |
| `report` | `on`, `off` | `scaffold.py --force --report <value>` |
| `digest` | `auto`, `warn`, `off` | `scaffold.py --force --digest <value>` |
| `mutation_checks` | `on`, `off` | `scaffold.py --force --mutation-checks <value>` |
| `quality_gate` | `off`, `deterministic` | `scaffold.py --force --quality-gate <value>` |

The five keys were once five `purlin:init` flags of their own. Those spellings
still run and each prints one line naming the `--set` key that replaced it;
all five are removed in 0.12.0. The scaffolder keeps its long flags either way:
the script's interface is not this skill's.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" \
  --project-root . --force --pre-push <warn|strict|off>
```

One flag, one field: the run rewrites that key of `.purlin/config.json` and
leaves every other key and every other file in the project byte-identical.
`--test-framework` left off is the value the project already recorded, not
`auto`, so a lone re-answer never re-detects the frameworks or re-copies a
plugin. This paragraph is the only place the procedure is stated: the step that
asks each question points here rather than repeating the invocation, because
five copies of one procedure are five things to keep in step. Do NOT hand-edit
`.purlin/config.json` for one of these: the scaffolder owns that file, and a
config edited by hand is how a key gets dropped, reordered or written in the
wrong type. The four audit fields that Steps 7b and 7c fill in
(`audit_criteria`, `audit_criteria_pinned`, `audit_llm` and `audit_llm_name`)
are the one exception, because the scaffolder takes no flag for any of them and
the answers only exist after those two steps have asked their questions. Every
other key belongs to the scaffolder, and no other step writes that file.

**Setting the quality gate on an existing project.** `purlin:init --set
quality_gate <off|deterministic>` is one of the re-answers above. The mode is a
declaration and `purlin:init --ci` is what makes it do anything: the workflow that subcommand writes is the job that reads
`quality_gate` on every push, and a project with no CI job has set a field
nothing runs. Offer `--ci` when the user sets the gate to `deterministic`. Do not
ask about the quality gate during a full init and do not pass
`--quality-gate` on the Step 2 invocation unless the user asked for it:
`quality_gate` is not a template field, so a project that never answered it
carries no such key, and `purlin:init --update` neither backfills it nor asks
about it.

Every config field's default, the command that writes it and the readers that consult it are
listed once, in `references/drift_criteria.md` § Config Field Ownership: read that table rather
than a second copy here. It covers the template fields and the optional `platforms` and
`quality_gate` fields a full init never writes.

## Step 3 — Detect Test Framework

**Print `DETECTING CODEBASE` before scanning.** Framework detection scans multiple files across the project and can take noticeable time, so the user must see that work is happening; the sample below opens with that line.

Read `references/supported_frameworks.md` for the complete framework list, detection heuristics, and plugin file mappings. That file is the single source of truth — do NOT hardcode framework names here. The complete list spans BOTH the **Built-in Plugins** table and the **Additional Plugins (manual setup)** table — present every framework from both. Check project files for ALL matching frameworks using the detection columns in that reference.

**Always present the framework selection list to the user**, even when auto-detection succeeds. Build the list dynamically from `references/supported_frameworks.md` so every shipped plugin (built-in and manual-setup) is offered. Pre-select detected frameworks with `[x]`, show undetected as `[ ]`. Always include `other` as the last option for custom plugins. This lets the user confirm, add, or remove frameworks before scaffolding.

When one or more frameworks are detected:

```
DETECTING CODEBASE
Scanning project files for test frameworks...

Test frameworks (detected frameworks are pre-selected):
  [x] <detected framework>    — <detection reason>
  [ ] <other framework>
  ...
  [ ] other

Confirm selection, or change? [enter to confirm]
```

When no framework is detected, do NOT silently default to shell. Show the list with nothing pre-selected:

```
DETECTING CODEBASE
Scanning project files for test frameworks...

No test framework detected.

Test frameworks (select one or more):
  [ ] <framework>
  ...
  [ ] other

Which framework(s)? You can select multiple, e.g.: pytest, jest
```

If the user selects "other", suggest `purlin:init --add-plugin` to install a custom proof plugin.

Pass the selection to the scaffolder as `--test-framework`: one id, a comma-separated list (`pytest,jest`), or `auto` to record `auto` and let the scaffolder install the plugin for every framework its detection matches. When nothing is detected and the user selects nothing, `auto` installs no plugin and says so: shell is scaffolded because it was chosen, never as a silent fallback.

## Step 4 — Proof Plugins and Test Wiring

The scaffolder installs the plugin file `references/supported_frameworks.md`
registers for each selected framework into `.purlin/plugins/`, byte-identical
to the installed plugin's `scripts/proof/` copy, and installs all of them when
several were selected.

For a framework listed under **Additional Plugins (manual setup)** (e.g. xUnit), `purlin:init` does not auto-wire it — after the plugin file is copied, print the framework's setup steps from its section in `references/formats/proofs_format.md` and direct the user to complete the wiring manually.

For the three frameworks it does wire, the scaffolder writes the file below
**only when the project has no file of that name**, and reports `kept` when it
has one: a project's own test configuration is never rewritten by init.

| Framework | File | What it contains |
|-----------|------|------------------|
| pytest | `conftest.py` | `.purlin/plugins` appended to `sys.path`, then `pytest_plugins = ["pytest_purlin"]`. `.purlin` is not an importable package name, so a dotted `.purlin.plugins.pytest_purlin` raises before any test runs |
| jest | `jest.config.js` | `reporters: ['default', '.purlin/plugins/jest_purlin.js']` |
| vitest | `vitest.config.ts` | `reporters: ['default', '.purlin/plugins/vitest_purlin.ts']` (Vitest loads `.ts` reporters natively via Vite — no Jest config) |

When the project already has one of those files, tell the user which line to
add; the scaffolder's plan says which files it kept.

## Step 5 — .gitignore

The scaffolder appends `templates/gitignore.purlin` to the project's
`.gitignore`, entry by entry, skipping any entry the file already carries so a
re-init never duplicates one. That template is the single source for the
block: read it rather than restating its entries here.

**Note:** `.purlin/report-data.js` is NOT gitignored — it is the project digest and should be committed. If upgrading from a prior version, remove any existing `.purlin/report-data.js` entry from `.gitignore`.

## Step 5b — Dashboard Report

The HTML dashboard is enabled by default. Ask the user:

```
HTML dashboard report:
  [on]  Generate purlin-report.html — open in browser for live coverage (default)
  [off] Disable dashboard report generation
```

If **on** (default): pass `--report on`. The scaffolder writes `"report": true` and copies the installed plugin's `scripts/report/purlin-report.html` to `purlin-report.html` at the project root. It is a copy on every host and a symlink on none: the only path a plugin install can be linked at is version-pinned, so the link would break on the first plugin update. `purlin:init --update` refreshes the copy. Print: `Dashboard: purlin-report.html (open in browser after running purlin:status)`

If **off**: pass `--report off`. No dashboard is created, and an existing one is never deleted.

When called via `purlin:init --set report <on|off>`, ONLY this step runs. Read the current config, show the current setting, and ask to toggle:

```
Dashboard report is currently: on
  [on]  Keep enabled
  [off] Disable
```

After changing, run the re-answer of Step 2, **Single-step re-answers**. It links `purlin-report.html` when the answer is on and the file is absent, and never deletes an existing dashboard when the answer is off (the user may want to keep it).

## Step 5c — MCP Server (plugin-bundled) + Legacy Migration

The Purlin MCP server (`sync_status`, `purlin_config`, and `drift` tools) is bundled with the plugin: `.claude-plugin/plugin.json` declares it under `mcpServers` with `${CLAUDE_PLUGIN_ROOT}`, which Claude Code resolves to the installed plugin path on every launch. It registers automatically wherever the plugin is enabled and tracks plugin updates. Do NOT create a `purlin` entry in the project's `.mcp.json` — a project-scope entry takes precedence over the plugin-provided server and pins a versioned cache path that silently goes stale on the next plugin update.

**Legacy migration (pre-0.9.4 projects):** If `.mcp.json` exists at the project root, read it as JSON. If it has a `purlin` key under `mcpServers`:

1. Remove the `purlin` key. Preserve ALL other server entries unchanged.
2. If `mcpServers` is now empty and the file contains nothing else, delete `.mcp.json`. Otherwise write the file back without the `purlin` entry.
3. Print: `Removed legacy purlin entry from .mcp.json — the MCP server is now provided by the plugin. Run /reload-plugins (or restart the session) to pick it up.`

If `.mcp.json` has no `purlin` entry (or doesn't exist), print: `MCP server: bundled with plugin (sync_status, purlin_config, drift).`

## Step 5d — Update

`purlin:init --update` brings an already-initialized project up to the installed plugin. It is
the one command for "the plugin moved, this project has not": there is no separate update skill,
and the legacy `.mcp.json` migration (Step 5c) is one of its steps.

Detection is content-based, never version-based. A project may have been initialized by any
version, edited by hand, or half-migrated already, so what is on disk is the only honest input
and the `version` field is not consulted to decide what to do.

**1. Check.** Run the detector, which writes nothing:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update/migrate.py" --check --project-root .
```

It prints JSON: `{"project_root": ..., "pending": [{"id", "count", "summary", "files"}, ...]}`,
and every entry names the files it counted. This is the same list `sync_status` prints as its
pending-migrations advisory, from the same detector. If `pending` is empty, print
`Project is up to date with Purlin <VERSION>.` and stop.

When called as `purlin:init --update --check`, stop here: report and change nothing.

**2. Show the delta before asking.** Present it in the shape `skills/spec/SKILL.md` Step 7c uses,
per file, so the user reads what will change before consenting:

```
Pending migrations: 8 (Purlin 0.10.0)

RENAMING:
  specs/audit/static_checks.proofs-windows.json
    -> specs/audit/static_checks.proofs-unit@windows-2022.json   (git mv; platform stamped)

UPDATING:
  specs/audit/static_checks.md          2 proof tags @windows -> @unit @on(windows-2022)
  dev/test_windows_native.py            2 markers, windows tier -> tier unit, on(windows-2022)
  .purlin/plugins/pytest_purlin.py      replaced with the installed plugin's copy
                                        (previous bytes kept at
                                         pytest_purlin.py.local-3f9a1c04.bak)
  .purlin/config.json                   remote_verification="off", version=0.10.0
  .purlin/hooks/pre-commit              rewritten from the installed plugin
  .git/hooks/pre-commit                 a dangling symlink, replaced by the delegator
  purlin-report.html                    refreshed from the installed dashboard
  .purlin/report-data.js                rebuilt at the current digest schema

KEEPING (unchanged):
  specs/audit/static_checks.receipt.json   a receipt is a claim that tests ran
  .purlin/config.json  quality_gate        optional, not a template field: never
                                           backfilled and never asked
  every other proof file, spec and test

ASKING:
  mutation_checks                       not backfilled; see Step 7d

DIRECTIVES (nothing is written for these):
  receipt-v1   -> Run: purlin:verify
  legacy-mcp   -> Run: purlin:init --update (then /reload-plugins)
```

Name the provenance loss explicitly for every renamed platform proof file: the commit that
carried the old name still exists, but the report reads provenance per current filename, so the
file reports `runner not recorded` until the runner next commits it under the new name. The
rename does not delete evidence; it moves the record, and `git mv` keeps its history.

**3. Ask.** Use `AskUserQuestion` to get consent before any write. Nothing is written before the
answer: no rewrite, no rename, no copy, no config edit.

**4. Apply.** Run the migrations the user approved:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update/migrate.py" --apply <id> [<id> ...] \
  --project-root . --platform-id <id> [--mutation-checks on|off]
```

`--platform-id` is what a legacy `@windows` tag, proof file and marker become; it defaults to
`windows` (the OS family id), and a project with a registered platform passes that id instead.
The script never writes a proof entry and never writes a receipt: `receipt-v1` and `legacy-mcp`
print directives only. When `mutation_checks` is absent from the config, ask the Step 7d question
and pass the answer as `--mutation-checks on|off`; the update never writes that field silently.

`--update` writes no workflow file and registers no platform. Both belong to `purlin:test`'s
consent path, which is the one place a runner is discovered and offered.

**5. Re-run the tests whose markers changed.** A marker rewrite changes which file a plugin
writes, and only a plugin may write a proof file. For every feature whose markers were rewritten,
run `purlin:test <feature>` so the plugin emits the scoped file itself.

**6. Print the receipt directive.** `-> Run: purlin:verify`. The update never issues a receipt,
and `purlin:verify` declines to issue while any `legacy-*` migration is pending, so this is the
step that closes the loop.

**7. Re-sync the pinned audit criteria.** If `.purlin/config.json` has `audit_criteria` set, run
the `--sync-audit-criteria` step (below) now, before committing. The cached criteria at
`.purlin/cache/additional_criteria.md` and the sha in `audit_criteria_pinned` are what
`purlin:audit` grades against, and a project that pinned external criteria and then updated is one
whose criteria have usually moved too. With `audit_criteria` unset, say so in one line and move on.

**8. Commit.** `chore(update): migrate to <VERSION> (<ids>)`, with the applied ids in the
parentheses (see `references/commit_conventions.md`).

**9. Idempotent.** Run `--check` again. It reports nothing pending apart from the two directives
the script does not apply, and a second `--update` changes nothing.

## Step 6 — Confirmation

Print the scaffolder's plan verbatim: it is one line per path, each beginning
`wrote`, `kept`, `copied`, `linked` or `skipped`, so it says what was created
and what was left alone without the tree being inspected a second time. Then:

```
Project initialized for Purlin.

Test framework: <detected>
Proof plugin: .purlin/plugins/<name>
Dashboard: on (open purlin-report.html in browser)
Digest: auto (regenerated on every commit)

Next steps:
  purlin:spec <topic>    — create your first spec
  purlin:status          — see rule coverage
```

## Step 7 — Install Git Pre-push Hook

Install the Purlin pre-push hook so `git push` checks proof coverage before code reaches the remote.

The hook has three modes, set in `.purlin/config.json` under `"pre_push"`:
- **`"warn"`** (default): blocks on FAILING proofs, reports PARTIAL, UNTESTED and unreceipted coverage without blocking
- **`"strict"`**: blocks on anything not VERIFIED (requires verification receipt)
- **`"off"`**: the hook prints one line naming the mode and exits; no tests run and no coverage is checked

Ask the user which mode they want:
```
Pre-push hook mode:
  [warn]   Block on FAILING, allow PASSING and PARTIAL (default)
  [strict] Block on anything not VERIFIED (requires verification receipt)
  [off]    Run nothing and check nothing
```

Pass the answer to the scaffolder as `--pre-push <mode>`. Any other value makes the hook block every push until it is corrected: a typo must not disable enforcement invisibly, which is why the flag takes `warn`, `strict` and `off` and nothing else.

When called via `purlin:init --set pre_push <mode>`, ONLY the mode selection above runs, followed by the re-answer of Step 2, **Single-step re-answers**. No hook is installed by that run beyond the one it keeps; the hook install below happens during the full init flow, inside the same scaffolder.

The scaffolder installs the hook in two parts. The body is the generated shim
`.purlin/hooks/pre-push`, tracked in git because it names no machine and no
plugin version: it resolves the installed plugin at run time and runs that
plugin's `scripts/hooks/pre-push.sh`, so a plugin update changes the hook and
nothing in the project is rewritten. The file git runs is a three-line
delegator to that shim, written into the hooks directory git reads
(`core.hooksPath` when the repository sets one, the common hooks directory
otherwise, so a linked worktree gets a hook that runs).

Every path ends in one of five outcomes, each a plan line: the shim is `wrote`
or `kept`; the delegator is `wrote` into a free slot, `kept` when Purlin's
delegator is already there, and `skipped` when the slot holds anything else.
A hook that is already there is someone's and init never writes over it: the
plan line prints the one line to add to it instead. When husky, lefthook or the
pre-commit framework owns the repository's hooks, the plan names the manager
and the file to paste that line into. Read the plan lines back to the user when
one of them says `skipped`. Print: `Installed git pre-push hook (proof coverage
check).`

## Step 7a — Pre-commit Hook (Project Digest)

Install the Purlin pre-commit hook so `git commit` automatically regenerates the project digest (coverage + drift data in `.purlin/report-data.js`). The digest is committed to the repo so non-engineer stakeholders (QA, PM, compliance) can access project status without running Purlin tools.

The digest has three modes, set in `.purlin/config.json` under `"digest"`:
- **`"auto"`** (default) — regenerate digest before every commit, auto-stage the file
- **`"warn"`** — warn if the digest is stale, don't regenerate or block
- **`"off"`** — disable the pre-commit hook entirely

Ask the user which mode they want:

```
Project digest (auto-generates coverage + drift data for stakeholders):
  [auto] Regenerate on every commit — always up-to-date (default)
  [warn] Warn if digest is stale, don't auto-regenerate
  [off]  Disable digest hook

NOTE: Digest generation runs coverage scan and drift only.
It NEVER triggers an audit — cached audit data is included.
Run purlin:audit separately when you want fresh audit scores.
```

Pass the answer to the scaffolder as `--digest <mode>`, which takes `auto`, `warn` and `off`.

When called via `purlin:init --set digest <mode>`, ask the mode above and then run the re-answer of Step 2, **Single-step re-answers**: that one run also installs the pre-commit hook below when the project has none. Also remove `.purlin/report-data.js` from `.gitignore` if present, so one command leaves an existing project with the whole digest feature rather than half of it.

The scaffolder installs `.purlin/hooks/pre-commit` and its delegator by the
same rule as the pre-push hook, with the same five outcomes, and never writes
over a hook that is already there. At `"digest": "off"` it writes neither the
shim nor the delegator and says so: the mode that disables the digest should
not leave a hook behind to read it. Print: `Installed git pre-commit hook
(project digest).`

## Step 7b — Audit Criteria

Ask the user which audit criteria to use:

```
Audit criteria:
  [default] Use Purlin's built-in audit criteria only
  [additional] Add team-specific criteria from a git-hosted file
               (appended to built-in — does not replace defaults)
```

If **default**: no config change needed — `purlin:audit` loads built-in criteria via `load_criteria()`.

If **additional**: ask for the git URL and file path (e.g., `git@github.com:acme/quality-standards.git#audit_criteria.md`). Set `audit_criteria` and `audit_criteria_pinned` in `.purlin/config.json`:

```json
{
  "audit_criteria": "git@github.com:acme/quality-standards.git#audit_criteria.md",
  "audit_criteria_pinned": "<current remote HEAD sha>"
}
```

Clone the repo to a temp directory, read the file at HEAD, **save to `.purlin/cache/additional_criteria.md`**, record the commit SHA as `audit_criteria_pinned`, then clean up. The `load_criteria()` function in `static_checks.py` reads this cached file and appends it to the built-in criteria.

**The cached file's first line must be `<!-- purlin-criteria-sha: <sha> -->`, naming the commit
the file was read at**, followed by the file's own content. `load_criteria()` compares that sha
to `audit_criteria_pinned` and refuses to grade anything when the two disagree; without the
header line the cache is a file with no provenance and an audit cannot say what standard it
applied.

## Step 7c — Audit LLM Configuration

Ask the user which LLM should perform proof audits:

```
Audit LLM:
  [default] Claude audits (same model — fastest, independent context)
  [external] Use a different LLM for cross-model auditing (experimental)
```

If **default**: no config change. The auditor runs in an independent context.

If **external**: ask for the CLI command:

```
Enter the command to call your external LLM.
Use {prompt} where the audit prompt should go.

Examples:
  gemini -m pro -p "{prompt}"
  openai chat -m gpt-4o "{prompt}"
  ollama run llama3 "{prompt}"

Command:
```

After the user enters the command:

1. **Test it:** shell out with a simple test prompt — replace `{prompt}` with `"Respond with exactly: PURLIN_AUDIT_OK"` and run the command.
2. **Check the response** contains `PURLIN_AUDIT_OK`.
3. **If it works:** save to `.purlin/config.json`:
   ```json
   {
     "audit_llm": "gemini -m pro -p \"{prompt}\"",
     "audit_llm_name": "Gemini Pro"
   }
   ```
   Print: `Audit LLM configured: Gemini Pro ✓`
4. **If it fails:** print the error and ask the user to try again or skip.

This step is also callable independently via `purlin:init --audit-llm`.

## Step 7d — Mutation Checks

A mutation check is the practice of breaking the behaviour a proof covers, watching that proof
fail, and restoring the code before committing. It is the only check that catches a proof which
passes against broken code, and it is off by default because it costs real time and tokens.

Print the value statement **before** the question, quoting it from
`references/spec_quality_guide.md` § Mutation check ("What it is worth"). That section is the one
source for this text; do not restate it here in different words.

Then ask:

```
Mutation checks:
  [off] Write proofs and move on (default)
  [on]  Every new or amended proof is mutation-checked before the commit that carries it
```

Pass the answer to the scaffolder as `--mutation-checks on|off`, which writes `"mutation_checks": true` or `"mutation_checks": false`.

When called via `purlin:init --set mutation_checks on|off`, ONLY this step runs: read the
current value, show it, and run the re-answer of Step 2, **Single-step re-answers**.

`purlin:init --update` asks this same question when `mutation_checks` is absent from the config,
and passes the answer to the migration script as `--mutation-checks on|off`. It is the one config
field the update never backfills from the template: a setting that doubles the cost of writing a
proof is a decision the project makes, not a default it inherits.

What reads the field: `purlin:build` requires the check before the commit when it is true and
prints one line saying the check is off when it is false; `purlin:audit` may ask an author to
name the mutation they ran and caps a proof whose author cannot name one at WEAK
(`references/audit_criteria.md` § Pass 2).

## Step 8 — Commit

Commit per `references/commit_conventions.md`:

```
git commit -m "chore: initialize purlin project"
```

---

## Subcommand: --ci

```
purlin:init --ci [github]
```

Writes `.github/workflows/purlin-verify-gate.yml`: the verification gate this
plugin runs on itself, in the form a project that clones the tooling needs.
`github` is the only provider for now and is the default when none is given.

### Steps

1. **Ask first, with `AskUserQuestion`.** A workflow file spends the project's
   CI minutes and is read as policy by everyone on the team, so it is never
   written without consent. Ask one question, `Write the Purlin CI workflow?`,
   with the two options `Write it` and `Not now`, and summarize what lands in
   exactly these two lines:

   ```
   .github/workflows/purlin-verify-gate.yml: on a push or PR touching specs/**,
     .purlin/config.json or .github/workflows/**, clones Purlin at PURLIN_REF
     and runs scripts/ci/verify_gate.py --check.
   PURLIN_REF is pinned to the installed version; change that one line to move
     the job to another release. An existing file at that path is never touched.
   ```

2. **On `Not now`, stop.** Say nothing was written.

3. **On `Write it`, run the scaffolder:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" \
     --project-root . --force --ci github
   ```

   Print the plan line the run emitted. `wrote` means the workflow is there;
   `kept` means the project already had a file at that path and the run left
   its bytes alone, which is what to report rather than offering to overwrite
   it.

4. **Tell the user what is left to do.** The job is a check, not a gate, until
   branch protection marks it required; `references/hard_gates.md` states which
   layer that is. A project that also wants the quality gauges to decide sets
   `quality_gate` with `purlin:init --set quality_gate deterministic`.

---

## Subcommand: --add-plugin

```
purlin:init --add-plugin <source>
```

Source can be:
- A local file path: `./my_proof_plugin.py` or `/path/to/plugin.sh`
- A git URL: `git@github.com:someone/purlin-go-proof.git` or `https://...`

### Steps

1. **Verify `.purlin/plugins/` exists.** If not, tell the user to run `purlin:init` first and stop.

2. **If source is a local file path:**
   - Verify the file exists
   - Copy it to `.purlin/plugins/`
   - Print: `Added proof plugin: .purlin/plugins/<filename>`

3. **If source is a git URL:**
   - Clone to a temp directory: `git clone <url> /tmp/purlin-plugin-install`
   - Look for proof plugin files (`*.py`, `*.js`, `*.sh`, `*.java` in the repo root or a `plugin/` directory)
   - If one file found: copy to `.purlin/plugins/`
   - If multiple found: list them and ask the user which to install
   - Clean up the temp directory: `rm -rf /tmp/purlin-plugin-install`
   - Print: `Added proof plugin: .purlin/plugins/<filename>`

4. **Validate the plugin** after copying. The pattern every language's plugin file must
   contain is listed once, in `references/proof_plugin_contract.md` § C, under **What a
   plugin file must contain**: look up the row for the copied file's extension and check it.

   If validation fails, warn but still install:
   ```
   ⚠ This file doesn't look like a standard proof plugin.
   It should read test markers and write .proofs-*.json files.
   See references/formats/proofs_format.md for the schema.
   ```

5. **Print next steps:**
   ```
   Plugin installed. To use it:
   1. Add proof markers to your tests using the plugin's marker syntax
   2. Run your tests — the plugin emits .proofs-*.json files
   3. purlin:status shows coverage
   ```

---

## Subcommand: --sync-audit-criteria

```
purlin:init --sync-audit-criteria
```

Syncs the additional team criteria file to the latest version.

### Steps

1. Read `.purlin/config.json`. If `audit_criteria` is not set: `"No external audit criteria configured. Using built-in defaults."` Stop.

2. Parse the git URL and file path from `audit_criteria` (format: `git@host:org/repo.git#path/to/file.md`).

3. Clone the repo to a temp directory: `git clone <url> /tmp/purlin-audit-criteria-sync`

4. Get the current remote HEAD SHA: `git rev-parse HEAD`

5. Compare to `audit_criteria_pinned` in config:
   - If same: `"Audit criteria up to date."` Clean up and stop.
   - If different: read the file at HEAD, **save to `.purlin/cache/additional_criteria.md` with `<!-- purlin-criteria-sha: <new SHA> -->` as its first line** followed by the file's content, update `audit_criteria_pinned` in config to the new SHA, print `"Audit criteria updated: <old SHA> → <new SHA>"`
   - If same: still rewrite the cached file with its header line when the header is missing or names a different sha, because `load_criteria()` reads the header and not the config alone, and a cache without one makes every audit exit 2

6. Clean up: `rm -rf /tmp/purlin-audit-criteria-sync`
