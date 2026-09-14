# Feature: purlin_agent

> Description: What `agents/purlin.md` must say. The agent definition is the only text every
>   Purlin session loads before it does anything, so it carries the core loop, the five things
>   the agent never does, and the table that routes a plain-language request to a command.
> Scope: agents/purlin.md
> Stack: markdown, Claude Code agent definition

## Rules

- RULE-1: `agents/purlin.md` opens with a frontmatter block carrying `name: purlin`, a non-empty `description` and an `effort` value [risk: medium] [origin: eng]
- RULE-2: The agent states the core loop once, as `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:verify`, push, in that order [risk: medium] [origin: eng]
- RULE-3: The agent carries five numbered NEVERs, and they are: a rule owned by another origin is never edited silently, a proof file, a record or an approval is never written by hand, a rule whose test you wrote is never approved, a push never skips verify under `recorded` or `approved`, and a retired term is never used [risk: high] [origin: eng]
- RULE-4: The routing table gives at least one row for each of the four roles PM, Designer, Engineer and QA, and every `purlin:` command it names is one of the thirteen `references/purlin_commands.md` lists [risk: medium] [origin: eng]
- RULE-5: The agent says to call `sync_status` before answering any question about state, and names all seven rule states, Drafted, Proof ready, Tested, Recorded, Reviewed, Approved and Stale, together with the re-verify pending flag [risk: high] [origin: eng]
- RULE-6: The whole of `agents/purlin.md` is at most 120 lines [risk: low] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read `agents/purlin.md`; verify the file opens with `---`, and that the frontmatter carries `name: purlin`, a `description:` whose value is not empty, and an `effort:` line. Deleting the `effort:` line fails naming the field
- PROOF-2 (RULE-2): Read `agents/purlin.md`; find the fenced block holding `purlin:drift` and verify the offsets of `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:verify` and `push` inside it increase in that order. Moving `purlin:test` after `purlin:verify` fails on the offset comparison
- PROOF-3 (RULE-3): Read the `## Five NEVERs` section of `agents/purlin.md`; verify it holds exactly five items numbered `1.` to `5.`, and that between them they name `origin`, `proof file`, `record`, `approval`, `approve a rule whose test you wrote`, `verify`, `recorded`, `approved` and `retired term`, one assertion per token so the failure names the missing one. Deleting the fifth item fails on the count, reporting four
- PROOF-4 (RULE-4): Parse the routing table of `agents/purlin.md`; verify its first column carries at least one row each for `PM`, `Designer`, `Engineer` and `QA`, and that every `purlin:<name>` the table names is one of the thirteen command names. Changing a row to route to `purlin:release`, which is not one of them, fails naming `purlin:release`
- PROOF-5 (RULE-5): Read `agents/purlin.md` with its line wrapping collapsed; verify it carries the sentence "Call `sync_status` before you answer any question about state." and each of the seven state names `Drafted`, `Proof ready`, `Tested`, `Recorded`, `Reviewed`, `Approved` and `Stale` together with the phrase `re-verify pending`, one assertion per name. Dropping `Reviewed` from the list fails naming `Reviewed`
- PROOF-6 (RULE-6): Read `agents/purlin.md` and count its lines; verify the count is at most 120. Appending prose until the file passes 120 lines fails, and the failure reports the count it found beside the ceiling
