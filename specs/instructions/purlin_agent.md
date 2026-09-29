# Feature: purlin_agent

> Description: What `agents/purlin.md` must say. The agent definition is the only text every
>   Purlin session loads before it does anything, so it carries the core loop, the four things
>   the agent never does, and the table that routes a plain-language request to a command.
> Scope: agents/purlin.md
> Stack: markdown, Claude Code agent definition

## Rules

- RULE-1: `agents/purlin.md` opens with a frontmatter block carrying `name: purlin`, a non-empty `description` and an `effort` value
- RULE-2: The agent states the core loop once, as `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:audit`, `purlin:sign`, in that order
- RULE-3: The agent carries four numbered NEVERs, and they are: evidence or a signature is never written by hand; no signature is ever written on a person's behalf; the agent never pushes, never writes a tag itself, never opens a pull request and never deletes or rewrites a remote branch, except the run branch `purlin:test --remote` owns; and nothing is called by a name other than the one `references/glossary.md` gives it, and no emoji is written anywhere
- RULE-4: The routing table gives at least one row for each of the three roles, Product, Developer and QA, and a row for no other role, and every `purlin:` command it names, read without the words and flags that follow it, is one of the commands `references/purlin_commands.md` lists
- RULE-5: The agent says to call `sync_status` before answering any question about state, and the paragraph that says so names the three steps `passed`, `strong` and `signed`, says the reason `no proof written` means no proof line names the rule, and says `out of date` means the spec, the code or the tests moved since the run
- RULE-6: The whole of `agents/purlin.md` is at most 135 lines
- RULE-7: The agent says what carries a feature's name and moves together, in one commit, on a rename: the spec file and its `# Feature:` line, the `> Requires:` entries, the marker comments, the signature directory and the evidence files, moved with `git mv`, then `sync_status` to find what was missed
- RULE-8: The agent says that every run ends on the summary and `Left to do`, that the first line of `Left to do` is the next step, and that a finished project ends on `Nothing left to do.`

## Proof

- PROOF-1 (RULE-1): The agent definition opens with a line reading `---`, and the block between it and the next `---` line carries `name: purlin`, a `description:` with text after it and an `effort:` with a value after it; nothing is reported
- PROOF-16 (RULE-1): A copy of the agent definition with its `effort:` line removed is reported as carrying no effort
- PROOF-17 (RULE-1): A copy whose `effort:` line is left with no value is reported as carrying no effort
- PROOF-18 (RULE-1): A copy whose name line reads `name: helper` is reported with `helper` where `purlin` is expected
- PROOF-19 (RULE-1): A copy whose `description:` line is left with no text is reported as carrying no description
- PROOF-20 (RULE-1): A copy with a line of prose above the opening `---` is reported as not opening with a frontmatter block
- PROOF-2 (RULE-2): Exactly one fenced block of the agent definition names `purlin:drift`, the chain `purlin:drift →` appears once in the whole file, and that block names `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:audit` and `purlin:sign`, in that order; nothing is reported
- PROOF-21 (RULE-2): A copy whose block reads `purlin:audit → purlin:test` in place of `purlin:test → purlin:audit` is reported as running out of order
- PROOF-22 (RULE-2): A copy with `purlin:sign` taken out of the block is reported as not naming `purlin:sign`
- PROOF-23 (RULE-2): A copy with a second fenced block reading `purlin:drift → purlin:build` is reported as stating the core loop in 2 fenced blocks, expected 1
- PROOF-24 (RULE-2): A copy whose prose adds the sentence `The loop is purlin:drift → purlin:build.` is reported as stating the core loop 2 times, expected once
- PROOF-3 (RULE-3): `Four NEVERs` lists four numbered items: `Never write evidence or a signature by hand`; `Never sign on a person's behalf`; `Never push, never write a tag yourself, never open a pull request, never delete or rewrite a remote branch`, save `purlin:test --remote`; ``Never call a thing by a name other than the one `references/glossary.md` gives it``, and `No emoji anywhere`
- PROOF-25 (RULE-3): A copy with a fifth item, `Never guess.`, added to the section is reported as carrying 5 NEVERs, expected 4
- PROOF-26 (RULE-3): A copy with the second item deleted is reported as carrying 3 NEVERs, expected 4
- PROOF-27 (RULE-3): A copy whose first item reads `Never write evidence carelessly` is reported under NEVER 1, naming `Never write evidence or a signature by hand`
- PROOF-28 (RULE-3): A copy whose second item reads `Never guess.` is reported under NEVER 2, naming `Never sign on a person's behalf`
- PROOF-29 (RULE-3): A copy whose third item leaves out `never write a tag yourself, ` is reported under NEVER 3
- PROOF-30 (RULE-3): A copy with the `purlin:test --remote` exception moved from the third item to the fourth, so every word stays in the section, is reported under NEVER 3
- PROOF-31 (RULE-3): A copy whose fourth item names the style guide in place of `references/glossary.md` is reported as not naming `references/glossary.md`
- PROOF-32 (RULE-3): A copy whose fourth item leaves out `No emoji anywhere, including command output.` is reported under NEVER 4
- PROOF-4 (RULE-4): In the agent definition's table whose first column is headed `Role`, `Product`, `Developer` and `QA` each have a row and no other role has one, and every `purlin:` command a row names, read without what follows it such as `add` or `--gate <gate>`, has a row in `references/purlin_commands.md`; nothing is reported
- PROOF-33 (RULE-4): A copy with a row for the role `Manager` is reported as having a row for `Manager`
- PROOF-34 (RULE-4): A copy whose row routes to `purlin:release` in place of `purlin:export` is reported as routing to a command `references/purlin_commands.md` does not list
- PROOF-35 (RULE-4): A copy whose `QA` rows are all relabelled `Developer` is reported as having no `QA` row
- PROOF-36 (RULE-4): With the `purlin:export` row removed from a copy of `references/purlin_commands.md`, the agent's row that routes to `purlin:export` is reported as routing to a command that file does not list
- PROOF-5 (RULE-5): The agent definition carries the sentence "Call `sync_status` before you answer any question about state.", and the paragraph holding it names ``` `passed`, `strong` and `signed` ```, says ``` `no proof written` means no proof line names the rule ``` and ``` `out of date` means the spec, the code or the tests moved since the run ```
- PROOF-8 (RULE-5): A copy whose sentence reads `when you answer` in place of `before you answer` is refused, and the refusal names the sentence it expected
- PROOF-9 (RULE-5): A copy whose `sync_status` paragraph drops `strong` from the three steps, while `strong` stays in backticks elsewhere in the file, is refused, and the refusal names the three steps
- PROOF-10 (RULE-5): A copy that says `out of date` means the run is old is refused, and the refusal names the meaning it expected
- PROOF-37 (RULE-5): A copy that says `no proof written` means the rule has no test is refused, and the refusal names the meaning it expected
- PROOF-6 (RULE-6): The agent definition, counted line by line, is at most 135 lines long; nothing is reported
- PROOF-38 (RULE-6): A copy of the agent definition padded with lines of prose to exactly 135 lines is not refused
- PROOF-39 (RULE-6): A copy padded to 136 lines is refused, and the refusal reads `agents/purlin.md is 136 lines, ceiling 135`
- PROOF-7 (RULE-7): Read with each line break as a space, the section headed `Renaming a feature` carries `specs/<category>/<name>.md`, `# Feature:`, `> Requires:`, `purlin: <name> PROOF-<n>`, `.signatures/`, `.purlin/evidence/<source>/<name>.json`, `moves them together in one commit`, `git mv`, then `sync_status` after it, and `a reference it cannot resolve is one the rename missed`
- PROOF-40 (RULE-7): A copy whose rename section says `every entry` in place of ``every `> Requires:` entry`` is refused, naming `> Requires:`
- PROOF-41 (RULE-7): A copy whose rename section leaves out the spec file's path `specs/<category>/<name>.md` is refused, naming that path
- PROOF-42 (RULE-7): A copy whose rename section leaves out ` in one commit` is refused, naming `moves them together in one commit`
- PROOF-43 (RULE-7): A copy that says to call `sync_status`, then move files with `git mv`, is refused as calling `sync_status` before `git mv`
- PROOF-44 (RULE-7): A copy whose section is headed `Moving a feature` in place of `Renaming a feature` is refused as having no `Renaming a feature` section
- PROOF-11 (RULE-8): Read with each line break as a space, one paragraph of the agent definition carries the summary `40 rules. 35 pass their tests. 30 are strong. 20 are signed.`, the words ``The first line of `Left to do` is the next step`` and `Nothing left to do.`
- PROOF-12 (RULE-8): A copy of the agent definition that no longer says the first line of `Left to do` is the next step is refused, and the refusal names that sentence
- PROOF-45 (RULE-8): A copy whose finished project ends on `Nothing more to do.` in place of `Nothing left to do.` is refused, naming `Nothing left to do.`
- PROOF-46 (RULE-8): A copy whose summary drops `30 are strong.` is refused, naming the summary it expected
