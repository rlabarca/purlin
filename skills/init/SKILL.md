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
purlin:init --list-plugins              List proof plugins
purlin:init --sync-audit-criteria       Sync external audit criteria
purlin:init --audit-llm                 Change audit LLM (default/external)
purlin:init --pre-push                  Change pre-push mode (warn/strict/off)
purlin:init --report                    Toggle HTML dashboard report (on/off)
purlin:init --digest                    Change digest mode (auto/warn/off)
purlin:init --mutation-checks on|off    Change the mutation-check setting
purlin:init --update                    Bring the project up to the installed plugin
purlin:init --update --check            Report what is pending; write nothing
purlin:init --update --platform-id <id> What a legacy @windows tag becomes (default: windows)
purlin:init --update --mutation-checks on|off
                                        Answer the mutation-check question during the update
purlin:init --mcp                       Run only the MCP step of --update
```

Each `--flag` runs ONLY that step, not the full init.

**Who does what.** This skill asks the questions; `scripts/init/scaffold.py` writes the files, exactly as `scripts/update/migrate.py` performs `--update`. The script handles the full init and the `--force` re-run (Steps 1, 2, 4, 5, 5b, 7 and 7a), and takes `--pre-push`, `--digest`, `--report` and `--mutation-checks` as answers. The single-step flags of the same names, `--add-plugin`, `--list-plugins`, `--sync-audit-criteria` and `--audit-llm` stay agent-driven; `--update` is `scripts/update/migrate.py` (Step 5d) and `--mcp` is its MCP step (Step 5c).

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
  [--remote-verification <required|optional|off>] [--force] [--dry-run]
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

Config template fields (from `templates/config.json`), plus the optional `platforms` field that init never writes:

| Field | Default | Description |
|-------|---------|-------------|
| `version` | from `VERSION` | Purlin framework version, stamped from `${CLAUDE_PLUGIN_ROOT}/VERSION` at init; never a literal in this table |
| `test_framework` | `"auto"` | Detected test framework(s) |
| `spec_dir` | `"specs"` | Directory containing specs |
| `pre_push` | `"warn"` | Pre-push hook mode (`warn`, `strict` or `off`); any other value blocks every push |
| `remote_verification` | `"off"` | Declared remote-verification mode (`required`, `optional`, `off`). A declaration, not the enforcement; see `references/remote_verification.md`. Init writes the default and does not ask: setup is offered when `purlin:test` finds a proof declared `@on(<platform-id>)` for a platform this host does not satisfy |
| `mutation_checks` | `false` | Whether every new or amended proof is mutation-checked before the commit that carries it (Step 7d). Asked, never defaulted silently; what the check is worth and what it costs is stated once in `references/spec_quality_guide.md` § Mutation check |
| `report` | `true` | HTML dashboard report generation |
| `digest` | `"auto"` | Digest generation mode (`auto`, `warn`, or `off`) |
| `platforms` | not set (optional; not written by init) | Registry for `@on(...)` proof tags: `{"<id>": {"os": windows\|macos\|linux, "version", "distro", "arch", "runner", "label"}}`. The family ids `windows`, `macos`, `linux` are built in; an entry pins a version or attaches a runner. Written by `purlin:test`'s setup offer with consent, or by hand; see `references/drift_criteria.md` |

## Step 3 — Detect Test Framework

**Print `DETECTING CODEBASE` before scanning.** Framework detection scans multiple files across the project and can take noticeable time — the user must see that work is happening:

```
DETECTING CODEBASE
Scanning project files for test frameworks...
```

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

If **on** (default): pass `--report on`. The scaffolder writes `"report": true` and symlinks `purlin-report.html` at the project root to the installed plugin's `scripts/report/purlin-report.html`, so the dashboard tracks plugin updates instead of going stale as a copy; it copies the file only when the link cannot be made, and its plan says which. Print: `Dashboard: purlin-report.html (open in browser after running purlin:status)`

If **off**: pass `--report off`. No dashboard is created, and an existing one is never deleted.

When called via `purlin:init --report`, ONLY this step runs. Read the current config, show the current setting, and ask to toggle:

```
Dashboard report is currently: on
  [on]  Keep enabled
  [off] Disable
```

After changing, update `"report"` in `.purlin/config.json`. If turning on, copy the HTML file to project root. If turning off, do NOT delete an existing HTML file (the user may want to keep it).

## Step 5c — MCP Server (plugin-bundled) + Legacy Migration

The Purlin MCP server (`sync_status`, `purlin_config`, and `drift` tools) is bundled with the plugin: `.claude-plugin/plugin.json` declares it under `mcpServers` with `${CLAUDE_PLUGIN_ROOT}`, which Claude Code resolves to the installed plugin path on every launch. It registers automatically wherever the plugin is enabled and tracks plugin updates. Do NOT create a `purlin` entry in the project's `.mcp.json` — a project-scope entry takes precedence over the plugin-provided server and pins a versioned cache path that silently goes stale on the next plugin update.

**Legacy migration (pre-0.9.4 projects):** If `.mcp.json` exists at the project root, read it as JSON. If it has a `purlin` key under `mcpServers`:

1. Remove the `purlin` key. Preserve ALL other server entries unchanged.
2. If `mcpServers` is now empty and the file contains nothing else, delete `.mcp.json`. Otherwise write the file back without the `purlin` entry.
3. Print: `Removed legacy purlin entry from .mcp.json — the MCP server is now provided by the plugin. Run /reload-plugins (or restart the session) to pick it up.`

If `.mcp.json` has no `purlin` entry (or doesn't exist), print: `MCP server: bundled with plugin (sync_status, purlin_config, drift).`

When called via `purlin:init --mcp`, ONLY this step runs. `--mcp` is the MCP step of `--update` (Step 5d) under its own name: `--update` runs it as one of its migrations (`legacy-mcp`), and `--mcp` runs that step alone, which is what an existing project needs after a plugin update when nothing else is pending.

## Step 5d — Update

`purlin:init --update` brings an already-initialized project up to the installed plugin. It is
the one command for "the plugin moved, this project has not": there is no separate update skill,
and `--mcp` (Step 5c) is one of its steps.

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
Pending migrations: 4 (Purlin 0.10.0)

RENAMING:
  specs/audit/static_checks.proofs-windows.json
    -> specs/audit/static_checks.proofs-unit@windows-2022.json   (git mv; platform stamped)

UPDATING:
  specs/audit/static_checks.md          2 proof tags @windows -> @unit @on(windows-2022)
  dev/test_windows_native.py            2 markers, windows tier -> tier unit, on(windows-2022)
  .purlin/plugins/pytest_purlin.py      replaced with the installed plugin's copy
  .purlin/config.json                   remote_verification="off", version=0.10.0

KEEPING (unchanged):
  specs/audit/static_checks.receipt.json   a receipt is a claim that tests ran
  every other proof file, spec and test

ASKING:
  mutation_checks                       not backfilled; see Step 7d

DIRECTIVES (nothing is written for these):
  receipt-v1   -> Run: purlin:verify
  legacy-mcp   -> Run: purlin:init --mcp (then /reload-plugins)
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

**7. Commit.** `chore(update): migrate to <VERSION> (<ids>)`, with the applied ids in the
parentheses (see `references/commit_conventions.md`).

**8. Idempotent.** Run `--check` again. It reports nothing pending apart from the two directives
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

Write the chosen mode to `.purlin/config.json` as `"pre_push": "warn"`, `"pre_push": "strict"` or `"pre_push": "off"`. Any other value makes the hook block every push until it is corrected: a typo must not disable enforcement invisibly.

When called via `purlin:init --pre-push`, ONLY the mode selection above runs (no hook installation). The hook install below happens during the full init flow, inside the scaffolder.

The scaffolder installs `.git/hooks/pre-push` as a symlink to the installed
plugin's `scripts/hooks/pre-push.sh`, and copies the file only when the link
cannot be made (a consumer project with no local framework checkout). A hook
file that already exists is kept, whether or not it is Purlin's: an existing
hook is someone's, and init does not overwrite it. Its plan line says which of
the three happened. Print: `Installed git pre-push hook (proof coverage check).`

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

Write the chosen mode to `.purlin/config.json` as `"digest": "auto"` (or `"warn"` or `"off"`).

When called via `purlin:init --digest`, run the mode selection above AND the hook installation below. Also remove `.purlin/report-data.js` from `.gitignore` if present. This makes `--digest` a complete setup command for existing projects — the user runs one command and gets the full digest feature.

The scaffolder installs `.git/hooks/pre-commit` by the same symlink-then-copy
rule as the pre-push hook, and keeps an existing hook of either kind. At
`"digest": "off"` it installs no pre-commit hook at all and says so: the mode
that disables the digest should not leave a hook behind to read it. Print:
`Installed git pre-commit hook (project digest).`

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

When called via `purlin:init --mutation-checks on|off`, ONLY this step runs: read the current
value, show it, and write the new one, exactly as `--pre-push` does for its mode.

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

4. **Validate the plugin** after copying:

   | Language | Must contain |
   |----------|-------------|
   | Python (`.py`) | `proofs` and `json` |
   | JavaScript (`.js`) | `proofs` and `JSON` |
   | TypeScript (`.ts`) | `proofs` and `JSON` |
   | C header (`.h`) | `purlin_proof` function |
   | PHP (`.php`) | `proofs` and `json_encode` |
   | Shell (`.sh`) | `purlin_proof` function |
   | Java (`.java`) | `proofs` and `Proof` |

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

## Subcommand: --list-plugins

```
purlin:init --list-plugins
```

List all files in `.purlin/plugins/`. For built-in plugins, look up the framework name from `references/supported_frameworks.md` (match the plugin filename to the "Plugin file" column). Label anything not in that reference as `custom`.

```
Installed proof plugins:
  .purlin/plugins/pytest_purlin.py (Python/pytest)
  .purlin/plugins/jest_purlin.js (JavaScript/Jest)
  .purlin/plugins/my_go_plugin.py (custom)
```

If `.purlin/plugins/` doesn't exist or is empty: `No proof plugins installed. Run purlin:init to set up.`

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
