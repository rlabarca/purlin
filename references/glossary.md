# Glossary

> The one list of the words this repository uses for its own concepts. A term here is the
> spelling every doc, skill, agent definition and reference uses; the third column names the
> file that defines it, which is where a definition is edited and where a reader is sent.
> Nothing on this page is a definition of its own: a second definition is a second answer the
> first time one of the two is edited.

## Canonical terms

| Term | What it means | Where the authority lives |
|------|---------------|---------------------------|
| spec | A feature's contract: `> Description:` and the two sections `## Rules` and `## Proof` | `references/formats/spec_format.md` |
| rule | One `- RULE-N:` line: a constraint that must hold | `references/formats/spec_format.md` |
| proof | One `- PROOF-N (RULE-M):` line: the blueprint for the test that shows the rule holds | `references/formats/spec_format.md` |
| proof marker | The per-framework annotation a test carries so a run can be attributed to a proof | `references/formats/proofs_format.md` |
| proof file | The `<feature>.proofs-<tier>.json` a plugin emits beside the spec | `references/formats/proofs_format.md` |
| tier | What kind of test a proof is: unit, `@integration`, `@e2e` or `@manual` | `references/formats/spec_format.md` |
| platform | Where a proof must be proved, declared with `@on(<platform-id>)`, and one of the three membership categories | `references/remote_verification.md` |
| anchor spec | A cross-cutting contract at `specs/_anchors/<name>.md` that other features name in `> Requires:` | `references/formats/anchor_format.md` |
| upstream-owned anchor | An anchor carrying a `> Source:`: its rules come from outside and are changed at that source, never here | `references/formats/anchor_format.md` |
| receipt | The `<feature>.receipt.json` `purlin:verify` writes when every rule of a feature has a passing proof | `references/formats/receipt_format.md` |
| vhash | The hash a receipt carries, and the list of segments it is computed over | `references/formats/receipt_format.md` |
| digest | `.purlin/report-data.js`: the whole project's state as one generated file, rebuilt by `sync_status` | `docs/dashboard-guide.md` |
| dashboard | `purlin-report.html` at the project root, which renders the digest in a browser | `docs/dashboard-guide.md` |
| drift | Committed change that the specs have not caught up with, classified by category and significance | `references/drift_criteria.md` |
| Proof Design | The gauge that grades a proof description with no test code: is this provable at all? | `references/audit_criteria.md` |
| Proof Integrity | The gauge that grades the test behind a proof: does it prove what the rule says? | `references/audit_criteria.md` |
| the eight grade names | `PROVABLE`, `LOOSE`, `UNPROVABLE` and `STRUCTURAL` for Proof Design; `STRONG`, `WEAK`, `HOLLOW` and `EXCLUDED` for Proof Integrity | `references/audit_criteria.md` |
| the statuses | `VERIFIED`, `PASSING`, `PARTIAL`, `FAILING` and `UNTESTED`, the five readings a feature can have | `references/hard_gates.md` |
| the hard gate | The one gate the framework enforces: `purlin:verify` issues no receipt until every rule has a passing proof | `references/hard_gates.md` |
| the CI gate job | Layer 3: the job branch protection marks required, which runs `scripts/ci/verify_gate.py --check` | `references/hard_gates.md` |
| pre-push mode | Layer 1's setting, `warn`, `strict` or `off`, chosen with `purlin:init --set pre_push` | `references/hard_gates.md` |
| remote verification | The loop that gets a platform-declared proof proved on a host this one is not, and the config field that declares the bar | `references/remote_verification.md` |
| pending migration | A reading the installed plugin has moved on from, reported by `sync_status` and cleared by `purlin:init --update` | `references/purlin_commands.md` |
| mutation check | Break the behaviour, watch that one proof fail, restore: the check that catches a proof passing against broken code | `references/spec_quality_guide.md` |
| `pm`, `eng`, `qa` | The three role tokens, and the only three: product, engineering and quality | `skills/drift/SKILL.md` |

## Retired terms

Every row below is a banned string of the repository's prose lint, and this section is the one
place in the shipped prose where the retired spelling may still be written. The lint reads its
rows from this table, so a row added here is enforced from that moment and a row removed here
stops being enforced: there is no second list to keep in step.

| Retired term | Use instead | Why |
|---|---|---|
| `3-section format` | `2-section format` | A spec and an anchor carry `## Rules` and `## Proof`. There is no third section, and there has not been one since the format contracts dropped it |
| `## What it does` | the `> Description:` continuation lines | Nothing ever parsed the section, so what it held was prose no tool and no proof could reach |
| `anchor file` | `anchor spec` | An anchor is a spec: it carries rules, proofs and a status, and `sync_status` reads it as one. Calling it a file says it is something else that happens to sit nearby |
| `.anchor.md` | `specs/_anchors/<name>.md` | `sync_status` reads that one directory and that one suffix. A file named the other way is one nothing loads and nothing reports |
| `specs/schema/` | `specs/_anchors/` | There is no `schema/` category. A routing list that names one writes a cross-cutting contract to a path nothing reads |
| `toolkit` | `the Purlin plugin` | Purlin is one Claude Code plugin with skills, an MCP server and proof plugins, not a collection a reader assembles |
| `platform tier` | `platform` | A tier says what kind of test a proof is and a platform says where it must be proved. The two are independent axes, and the compound name collapses them into one |
| `read-only` | `writes no code and no test files`, or `upstream-owned` for an anchor with a `> Source:` | It meant three different things on three pages: a skill that writes nothing at all, a gate that writes receipts and caches but never touches code, and an anchor owned by somebody else. Each has its own words now |
| `dev` as a role token | `eng` | The tools declared `pm, dev, qa` while every guide and every workflow said `eng`, so a reader who copied one spelling got an argument the other surface did not know |
| `/purlin:` | `purlin:` | A skill is invoked as `purlin:<name>`. The leading slash is a Claude Code slash-command spelling that nothing else here uses |
| `--mcp` | nothing; `purlin:init` wires the server | The flag described itself as redundant and did nothing a plain init did not already do |
| `--list-plugins` | `ls .purlin/plugins/` | A flag that shells out to a directory listing is a second name for a command the reader already has |
| `--criteria` | the `audit_criteria` config field | The flag bypassed the criteria SHA pin, so an audit run through it could not say which criteria it graded against |
| `--anchor` | `purlin:anchor create` | Pure delegation to another skill, which is the skill the reader should be told about |
| `--review` | Step 6 of `purlin:spec` | The review it named is mandatory in the step anyway, so the flag was a way to ask for what already happens |
| `--resume` | nothing; the skill always resumes | The behaviour was unconditional, so the flag turned nothing on |
| `--local` | `--platform none` | The old spelling of skipping the remote path. It still runs and prints one line naming its replacement until 0.12.0 |
| `(confirmed)` | no tag at all | A rule with no tag is already accepted, so confirming one meant deleting its `(assumed)` tag rather than writing a second one nothing read |

## Skill one-liners

Every skill has exactly one purpose sentence, and it is the Purpose cell of the Quick Reference
table in `references/purlin_commands.md#quick-reference`. The frontmatter `description` of
`skills/<name>/SKILL.md`, the README Skills table, the `agents/purlin.md` Skills table and the
first sentence of the matching bullet in `docs/index.md` all carry that same sentence.

They are not copied here. A sixth copy of a one-liner is a sixth thing to edit and the one a
reader is most likely to meet stale.
