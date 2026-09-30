# Feature: purlin_agent

> Description: What `agents/purlin.md` must say. The agent definition is the only text every
>   Purlin session loads before it does anything, so it carries the core loop, the four things
>   the agent never does, and the table that routes a plain-language request to a command.
> Scope: agents/purlin.md
> Stack: markdown, Claude Code agent definition
> Highest-Rule: 16
> Highest-Proof: 47

## Rules

- RULE-1: The agent definition opens with a frontmatter block carrying `name: purlin`, a non-empty `description` and an `effort` value
- RULE-2: The agent definition states the core loop once, as `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:audit`, `purlin:sign`, in that order
- RULE-3: The agent definition carries four numbered NEVERs, and they are: evidence or a signature is never written by hand; no signature is ever written on a person's behalf; the agent never pushes, never writes a tag itself, never opens a pull request and never deletes or rewrites a remote branch, except the run branch `purlin:test --remote` owns; and nothing is called by a name other than the one `references/glossary.md` gives it, and no emoji is written anywhere
- RULE-4: The agent definition's routing table gives at least one row for each of the three roles, Product, Developer and QA, and a row for no other role, and every `purlin:` command it names, read without the words and flags that follow it, is one of the commands `references/purlin_commands.md` lists
- RULE-5: The agent definition says to call `sync_status` before answering any question about state, and the paragraph that says so names the three steps `passed`, `strong` and `signed` and says `out of date` means the spec, the code or the tests moved since the run
- RULE-6: The agent definition is at most 135 lines
- RULE-7: The agent definition says what carries a feature's name and moves together, in one commit, on a rename: the spec file and its `# Feature:` line, the `> Requires:` entries, the marker comments, the signature directory and the evidence files, moved with `git mv`, then `sync_status` to find what was missed
- RULE-8: The agent definition says that every run ends on the summary and `Left to do`, that the first line of `Left to do` is the next step, and that a finished project ends on `Nothing left to do.`
- RULE-16: Where the agent definition first says to call `sync_status`, it says to set `project_root` to the project root, the top folder of the git checkout

## Proof

- PROOF-1 (RULE-1): The agent definition opens with a line reading `---`, and the block between it and the next `---` line carries `name: purlin`, a `description:` with text after it and an `effort:` with a value after it; nothing is reported
- PROOF-2 (RULE-2): Exactly one fenced block of the agent definition names `purlin:drift`, the chain `purlin:drift →` appears once in the whole file, and that block names `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:audit` and `purlin:sign`, in that order; nothing is reported
- PROOF-3 (RULE-3): `Four NEVERs` lists four numbered items: `Never write evidence or a signature by hand`; `Never sign on a person's behalf`; `Never push, never write a tag yourself, never open a pull request, never delete or rewrite a remote branch`, save `purlin:test --remote`; ``Never call a thing by a name other than the one `references/glossary.md` gives it``, and `No emoji anywhere`
- PROOF-4 (RULE-4): In the agent definition's table whose first column is headed `Role`, `Product`, `Developer` and `QA` each have a row and no other role has one, and every `purlin:` command a row names, read without what follows it such as `add` or `--gate <gate>`, has a row in `references/purlin_commands.md`; nothing is reported
- PROOF-5 (RULE-5): The agent definition carries a sentence opening "Call `sync_status`" and ending "before you answer any question about state.", and the paragraph holding it names ``` `passed`, `strong` and `signed` ``` and says ``` `out of date` means the spec, the code or the tests moved since the run ```
- PROOF-6 (RULE-6): The agent definition, counted line by line, is at most 135 lines long; nothing is reported
- PROOF-38 (RULE-6): A copy of the agent definition padded with lines of prose to exactly 135 lines is not refused
- PROOF-7 (RULE-7): Read with each line break as a space, the section headed `Renaming a feature` carries `specs/<category>/<name>.md`, `# Feature:`, `> Requires:`, `purlin: <name> PROOF-<n>`, `.signatures/`, `.purlin/evidence/<source>/<name>.json`, `moves them together in one commit`, `git mv`, then `sync_status` after it, and `a reference it cannot resolve is one the rename missed`
- PROOF-11 (RULE-8): Read with each line break as a space, one paragraph of the agent definition carries the summary `40 rules. 35 pass their tests. 30 are strong. 20 are signed.`, the words ``The first line of `Left to do` is the next step`` and `Nothing left to do.`
- PROOF-47 (RULE-16): Read with each line break as a space, the first `` `sync_status` `` in the agent definition is followed directly by ``with `project_root` set to the project root, the top folder of the git checkout``
