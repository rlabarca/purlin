> Criteria-Version: 3

# Drift criteria

How the `drift` tool classifies a changed file, which config field belongs to which command,
and what each of the four role views reports. The tool does the deterministic half; the
`purlin:drift` skill reads the diff and does the judgement half.

## File classification

The tool classifies each changed file in this order. The first match wins.

| Order | Category | Match |
|-------|----------|-------|
| 1 | CHANGED_SPECS | The path starts with `specs/` and ends with `.md` |
| 2 | CHANGED_DESIGNS | The path starts with `designs/` |
| 3 | TESTS_ADDED | The path matches a test pattern, below |
| 4 | CHANGED_BEHAVIOR | The path is in some spec's `> Scope:`, exactly or by prefix |
| 5 | NO_IMPACT | The path matches a documentation or config pattern and is not in a behavioural directory |
| 6 | NEW_BEHAVIOR | Everything else: code with no spec behind it |

**Test patterns.** The path contains any of `test_`, `_test.`, `.test.`, `tests/`.

**No-impact patterns.** `docs/`, `assets/`, `templates/`, `references/`, `.gitignore`,
`LICENSE`, `README.md`, `RELEASE_NOTES.md`, `.mcp.json`, `settings.json`, and any `.md` file
outside a behavioural directory.

**Behavioural directories**, excluded from that `.md` catch-all because what they hold decides
what the agent does: `skills/`, `agents/`, `.claude/agents/`. A file there that no spec scopes
is NEW_BEHAVIOR, not NO_IMPACT.

**Scope matching.** `> Scope: src/api/handler.py` matches that one path. `> Scope: src/api/`,
with the trailing slash, matches every path beneath it. That is how a spec scopes a directory
without listing every file in it.

## Significance

The category is where the skill starts. The diff decides what it means.

| Significance | What changed | Who cares |
|--------------|--------------|-----------|
| Behavioural | What the software does: a new capability, a changed rule, a removed one | PM, engineer, QA |
| Structural | How it is organised: a rename, a move, a refactor, a dependency bump | Engineer |
| Operational | How it runs: CI, container, environment | Engineer, QA |
| Documentation | Prose only | PM when it faces a user |
| Trivial | Whitespace, formatting, generated files | Nobody |

A file the tool calls CHANGED_BEHAVIOR may be structural, and a config file may be operational.
Read the diff before you report.

## Behavioural gap

A feature whose files changed and whose rules have no passing test has nothing standing behind
the change. The tool precomputes this: each CHANGED_BEHAVIOR entry carries `behavioral_gap`,
true when the spec has rules and none of them is Tested. The top-level `drift_flags` array
lists every such feature, and the skill surfaces those first.

## Broken scope

When a spec's `> Scope:` names a file or a directory that is no longer on disk, something was
deleted or renamed and the spec was not told. The tool checks every scope path against the
filesystem — exact paths with `os.path.exists`, prefix paths with `os.path.isdir` — and lists
each spec with a missing path in `broken_scopes`. If it was renamed, `purlin:rename` fixes both
sides; if it was deleted on purpose, `purlin:spec` updates the spec.

## Rules behind the change

For every spec with changed behaviour files, the tool returns `rule_details`: the rule list,
each rule's state, the changed files, and the counts. The skill reads the diff against those
rule descriptions and sorts each rule into one of four:

- **Covered**: the rule describes behaviour that did not change, or changed compatibly.
- **Potentially stale**: the rule describes behaviour the diff altered.
- **Untested**: the rule has no passing test, whatever changed.
- **Missing**: the diff shows behaviour no rule describes.

The state in `rule_details` is the state before this change was tested. A feature reading
"6 of 6 Recorded" after behavioural code changed still needs a look: those records were taken
against the old behaviour.

## Pins behind

For every anchor carrying a `> Source:`, drift runs one cached `git ls-remote` against that
source and compares its `> Pinned:` sha.

| Condition | What to report |
|-----------|----------------|
| The pin equals the source head | Nothing |
| The pin is behind | `anchor <name> is N commits behind its pin: RULE-3 changed, RULE-6 added` and `→ Run: purlin:anchor sync <name>` |
| The source is unreachable | `→ source unreachable; check the URL in the anchor` |
| A `> Source:` with no `> Pinned:` | `→ Run: purlin:anchor sync <name> to pin it` |

Drift never advances a pin on its own. A change that came from somewhere else gets read before
it is adopted.

## The four role views

Each view is a filter over the same data, not a different computation.

| Role | What it reports |
|------|-----------------|
| `pm` | Criteria with no rule carrying them, rules tagged `origin: pm` whose text changed, rules an engineer added, pins behind |
| `design` | Design files that changed, and rules tagged `origin: design` that went Stale because a mock was re-exported |
| `qa` | Approvals gone Stale, how long the review list is, rules whose every proof asserts a success path |
| `eng` | Files touched and the rules behind them, rules with no test, risk or origin tags the gate requires and the spec lacks, pins behind, rules flagged `re-verify pending` |

`re-verify pending` appears in the `eng` view as information and never in the `qa` view: the
code changed, the approval stands, and CI clears it on the next run.

## Config field ownership

`.purlin/config.json`, and which command owns each field.

| Field | Written by | Read by | Default |
|-------|-----------|---------|---------|
| `version` | `purlin:init` | The dashboard header | From the `VERSION` file |
| `gate` | `purlin:init`, `purlin:init --gate` | `sync_status`, `scripts/ci/verify_gate.py`, every skill that names a next step | `tested` |
| `min_strength` | `purlin:init` | `purlin:verify`, `scripts/ci/verify_gate.py` | 50, 70 or 80, from the gate |
| `approvers` | By pull request, hand-edited | `scripts/review/approve.py`, `sync_status`, `scripts/ci/verify_gate.py` | Not set; required under `approved` |
| `ai_review_at` | `purlin:init` | `purlin:review` | never, high or medium, from the gate |
| `test_framework` | `purlin:init` | `scripts/run/purlin_run.py` | `auto` |
| `mutation_engine` | `purlin:init` | `scripts/run/purlin_run.py` | Not set; test strength reads `n/a` without one |
| `git_host` | `purlin:init`, from the remote URL | `purlin:verify --remote`, `purlin:init --ci` | Detected |
| `sql_engine` | `purlin:init` | The SQL proof plugin | Not set |

`purlin:init` is the only command that writes config unprompted. Every other command reads. A
field that is absent or set to `auto` leaves the reader to its own fallback. This table must
name every field `templates/config.json` carries: a field written into new projects but absent
here has no recorded owner, which is how one went unlisted through four releases.

## Project root ownership

No config field names the project root, because the root is what the reader of the config had to
find first. `PURLIN_PROJECT_ROOT` owns that question: it is read before anything else, and a
directory it names that exists wins over the `.purlin/` marker a climb from the working
directory would otherwise find. With the variable unset the climb answers, and with no marker
anywhere above the working directory the working directory itself is returned, which is a guess
and is reported as one. Set the variable in the project's `.claude/settings.json` under `env`
when the workspace is not at the repository root; the tools also take a `project_root` argument
that overrides it for one call. Every tool says which directory it looked at and which of the
three mechanisms chose it.
