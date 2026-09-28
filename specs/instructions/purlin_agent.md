# Feature: purlin_agent

> Description: What `agents/purlin.md` must say. The agent definition is the only text every
>   Purlin session loads before it does anything, so it carries the core loop, the four things
>   the agent never does, and the table that routes a plain-language request to a command.
> Scope: agents/purlin.md
> Stack: markdown, Claude Code agent definition

## Rules

- RULE-1: `agents/purlin.md` opens with a frontmatter block carrying `name: purlin`, a non-empty `description` and an `effort` value
- RULE-2: The agent states the core loop once, as `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:audit`, `purlin:sign`, in that order
- RULE-3: The agent carries four numbered NEVERs, and they are: evidence or a signature is never written by hand, no signature is ever written on a person's behalf, nothing is pushed and no pull request is opened except the run branch `purlin:test --remote` owns, and nothing is called by a name other than the one `references/glossary.md` gives it
- RULE-4: The routing table gives at least one row for each of the three roles, Product, Developer and QA, and a row for no other role, and every `purlin:` command it names is one of the commands `references/purlin_commands.md` lists
- RULE-5: The agent says to call `sync_status` before answering any question about state, and names the reason `no proof written`, the three evidence levels `passed`, `strong` and `signed`, and the `out of date` word that means the spec, the code or the tests moved since the run
- RULE-6: The whole of `agents/purlin.md` is at most 135 lines [level: passed]
- RULE-7: The agent says what carries a feature's name and moves together on a rename: the spec file and its `# Feature:` line, the `> Requires:` entries, the marker comments, the signature directory and the evidence files, then `sync_status` to find what was missed

## Proof

- PROOF-1 (RULE-1): The agent definition opens with a line reading `---`, and the block between it and the next `---` line carries `name: purlin`, a `description:` with text after it and an `effort:` with a value after it. A name other than `purlin`, or a `description:` or an `effort:` that is empty or absent, does not meet the rule
- PROOF-2 (RULE-2): The first fenced block of the agent definition that names `purlin:drift` names, read from its start, `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:audit` and `purlin:sign`, in that order. A block naming `purlin:test` after `purlin:audit`, or leaving any of the six out, does not meet the rule
- PROOF-3 (RULE-3): The agent definition has a section whose heading carries `NEVER`, and it holds exactly four numbered items; between them the items carry `evidence`, `signature`, `sign on a person's behalf`, `Never push`, `pull request`, `remote branch`, `purlin:test --remote` and `references/glossary.md`. A section of three numbered items or of five does not meet the rule, and neither does one that names `references/glossary.md` nowhere
- PROOF-4 (RULE-4): In the agent definition's routing table, the table whose first column is headed `Role`, the roles are `Product`, `Developer` and `QA`, each on at least one row, and no other; every `purlin:` command a row names is one of the eleven, `purlin:anchor`, `purlin:audit`, `purlin:build`, `purlin:drift`, `purlin:export`, `purlin:init`, `purlin:sign`, `purlin:spec`, `purlin:spec-from-code`, `purlin:status` and `purlin:test`. A row for `Manager`, a row that routes to `purlin:release`, or a table with no `QA` row does not meet the rule
- PROOF-5 (RULE-5): Read with each line break as a space, the agent definition carries the sentence "Call `sync_status` before you answer any question about state." and each of `no proof written`, `passed`, `strong`, `signed` and `out of date` in backticks. A definition that names `strong` in backticks nowhere, or words that sentence any other way, does not meet the rule
- PROOF-6 (RULE-6): Read `agents/purlin.md` and count its lines; verify the count is at most 135. Appending prose until the file passes 135 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-7 (RULE-7): Read with each line break as a space, the section of the agent definition headed `Renaming a feature` carries `# Feature:`, `> Requires:`, `purlin: <name> PROOF-<n>`, `.signatures/`, `.purlin/evidence/<source>/<name>.json`, `git mv` and `sync_status`. A section that leaves out `> Requires:`, or a definition with no section of that heading, does not meet the rule
