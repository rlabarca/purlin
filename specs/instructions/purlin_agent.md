# Feature: purlin_agent

> Description: What `agents/purlin.md` must say. The agent definition is the only text every
>   Purlin session loads before it does anything, so it carries the core loop, the four things
>   the agent never does, and the table that routes a plain-language request to a command.
> Scope: agents/purlin.md
> Stack: markdown, Claude Code agent definition

## Rules

- RULE-1: `agents/purlin.md` opens with a frontmatter block carrying `name: purlin`, a non-empty `description` and an `effort` value [bar: strong]
- RULE-2: The agent states the core loop once, as `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:audit`, `purlin:sign`, in that order [bar: strong]
- RULE-3: The agent carries four numbered NEVERs, and they are: a proof file, a record or a signature is never written by hand, no signature is ever written on a person's behalf, nothing is pushed and no pull request is opened except the run branch `purlin:test --remote` owns, and a retired term is never used [bar: strong]
- RULE-4: The routing table gives at least one row for each of the four roles PM, Designer, Engineer and QA, and every `purlin:` command it names is one of the commands `references/purlin_commands.md` lists [bar: strong]
- RULE-5: The agent says to call `sync_status` before answering any question about state, and names the two spec statuses `drafted` and `ready`, the three evidence levels `passed`, `strong` and `signed`, and the `out of date` word that means the spec, the code or the tests moved since the run [bar: strong]
- RULE-6: The whole of `agents/purlin.md` is at most 135 lines [bar: passed]
- RULE-7: The agent says what carries a feature's name and moves together on a rename: the spec file and its `# Feature:` line, the `> Requires:` entries, the proof markers, the signature directory and the evidence files, then `sync_status` to find what was missed [bar: strong]

## Proof

- PROOF-1 (RULE-1): Read `agents/purlin.md`; verify the file opens with `---`, and that the frontmatter carries `name: purlin`, a `description:` whose value is not empty, and an `effort:` line. Deleting the `effort:` line fails naming the field
- PROOF-2 (RULE-2): Read `agents/purlin.md`; find the fenced block holding `purlin:drift` and verify the offsets of `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:audit` and `purlin:sign` inside it increase in that order. Moving `purlin:test` after `purlin:audit` fails on the offset comparison
- PROOF-3 (RULE-3): Read the `## Four NEVERs` section of `agents/purlin.md`; verify it holds exactly four items numbered `1.` to `4.`, and that between them they name `proof file`, `record`, `signature`, `sign on a person's behalf`, `Never push`, `pull request`, `remote branch`, `purlin:test --remote` and `retired term`, one assertion per token so the failure names the missing one. Deleting the fourth item fails on the count, reporting three
- PROOF-4 (RULE-4): Parse the routing table of `agents/purlin.md`; verify its first column carries at least one row each for `PM`, `Designer`, `Engineer` and `QA`, and that every `purlin:<name>` the table names is one of the command names. Changing a row to route to `purlin:release`, which is not one of them, fails naming `purlin:release`
- PROOF-5 (RULE-5): Read `agents/purlin.md` with its line wrapping collapsed; verify it carries the sentence "Call `sync_status` before you answer any question about state." and each of the words `drafted`, `ready`, `passed`, `strong`, `signed` and `out of date` in backticks, one assertion per word. Dropping `strong` from the list fails naming `strong`
- PROOF-6 (RULE-6): Read `agents/purlin.md` and count its lines; verify the count is at most 135. Appending prose until the file passes 135 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-7 (RULE-7): Read the `## Renaming a feature` section of `agents/purlin.md` with its line wrapping collapsed; verify it carries `# Feature:`, `> Requires:`, `feature-name token`, `.signatures/`, `.purlin/evidence/<source>/<name>.json`, `git mv` and `sync_status`, one assertion per literal. Deleting the `> Requires:` clause fails naming it
