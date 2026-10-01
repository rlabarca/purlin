# Feature: schema_spec_format

> Description: The spec format: the two sections every spec carries, the rule and proof
>   grammar, the metadata fields, the `@manual`, `@slow` and `@env` tags, and
>   the mistakes it warns of. Every surface that reads a spec
>   reads it through one parser, so a spec means the same thing to the status table, the
>   dashboard and the evidence file.
> Scope: scripts/mcp/purlin/specs.py, scripts/mcp/purlin/fingerprint.py, references/formats/spec_format.md, references/formats/anchor_format.md
> Stack: python/stdlib, one regex parser in scripts/mcp/purlin/specs.py
> Highest-Rule: 42
> Highest-Proof: 87

## Rules

- RULE-1: A spec carries two sections, `## Rules` and `## Proof`, and the format names no third
- RULE-3: A proof line reads `PROOF-N (RULE-N)`, and names several rules as `PROOF-N (RULE-A, RULE-B)` when one flow drives all of them; a list item under `## Proof` of any other form is not read as a proof
- RULE-6: `> Scope:` is a comma-separated list of file paths, parsed into a list in the order written
- RULE-7: The file name is the spec's name, whatever its first line says
- RULE-9: A proof line carries at most one `@manual` tag, at most one `@slow` tag and at most one `@env` tag, in any order, read off the end of the line; `@slow` says the proof's test takes a long time
- RULE-10: `@env` takes `windows`, `macos` or `linux` and nothing else; any other value is returned in the unknown list and sets no environment, so a proof is never treated as owned by an operating system the release cannot name
- RULE-40: Only `@manual`, `@slow` or `@env(...)` at the end of a proof line is read as a tag, and not when it follows a comma, `and` or `or`; any other trailing at-word with no value in brackets, a bare `@windows` apart, stops the reading, so the proof's text stays whole and the proof is neither manual, slow nor tied to a system
- RULE-13: Two specs with one file name in different folders are warned of: only one is read, and the warning names both files, the one read, and the `git mv` that renames the other
- RULE-15: A spec carrying a heading the format does not name still parses, its rules are still read, and nothing is reported about the extra heading
- RULE-19: The code part of a feature spec's fingerprint hashes exactly the files `> Scope:` names, so an edit to any other file leaves it unchanged and a code change is told from a rule change
- RULE-32: A `> Scope:` line on an anchor is not read: an anchor's scope is empty, because an anchor covers the whole project
- RULE-38: Each mistake that leaves a spec readable is warned of in one line naming the spec, what is wrong and `Run purlin:spec <name>.`, and the faulty line alone is not read: a line under `## Rules` with no id, a list item under `## Proof` that is not a proof line, a first line naming another feature, a `> Requires:` or `> Global:` line, a `> Scope:` line on an anchor, and a proof tagged both `@slow` and `@manual`, which is read as `@manual` alone; a pinned anchor's copy carrying such lines is instead warned of once, naming its source's owners as the ones to take them out
- RULE-39: A rule or proof number written twice is warned of, naming the number and `purlin:spec`, and read once, with the text of its second line; a line left from a merge conflict is warned of with its line number
- RULE-41: Rule and proof numbers are never reused: `> Highest-Rule:` and `> Highest-Proof:` record the highest number the spec has ever held, a new rule or proof takes one more than the highest of that line and every number the spec holds, and a gap in the numbers is reported as nothing
- RULE-42: `> Stack:`, `> Highest-Rule:` and `> Highest-Proof:` change no part of a spec's fingerprint and no rule or proof count
- RULE-27: The spec format page opens with the line `> Format-Version: <n>`, `<n>` a whole number

## Proof

- PROOF-1 (RULE-1): The spec format reference, under its heading `## Required sections`, names exactly two sections, `## Rules` and `## Proof`, and no third
- PROOF-16 (RULE-3): In a spec holding `RULE-1`, `RULE-2` and `RULE-3`, the line `PROOF-2 (RULE-2, RULE-3): One flow drives both` is read as a proof of `RULE-2` and `RULE-3`, and `PROOF-2` is the one proof of each
- PROOF-17 (RULE-3): In a spec holding `RULE-1`, `RULE-2` and `RULE-3`, the line `PROOF-3: No rule named`, which names no rule in brackets, is not read as a proof: the spec has no proof `PROOF-3`
- PROOF-6 (RULE-6): A spec carrying `> Scope: src/alpha.py, src/zeta.py` is read with a scope of exactly two paths, `src/alpha.py` then `src/zeta.py`
- PROOF-49 (RULE-7): A spec at `specs/test/login.md` whose first line reads `# Feature: checkout` is read as the feature `login`, and is reported with `login: the first line names checkout, but the file is login.md, so it is read as login. Run purlin:spec login.`
- PROOF-26 (RULE-9): The proof text `Lock the file @env(windows) @manual`, the same two tags in the other order, is read exactly as `Lock the file @manual @env(windows)` is: `@manual` on `windows`, the text `Lock the file`, no tag it does not read
- PROOF-9 (RULE-9): The proof text `Check it by hand @manual` is read as `@manual`, with no operating system, no tag it does not read, and the text `Check it by hand`
- PROOF-86 (RULE-9): The proof text `Check out a cart of three items @slow @env(linux)` is read as slow, on `linux`, not `@manual`, with the text `Check out a cart of three items` and no tag it does not read
- PROOF-10 (RULE-10): The proof text `Lock the file @env(windows)` is read on `windows`, not `@manual`, with the text `Lock the file` and no tag it does not read
- PROOF-38 (RULE-10): The proof text `Lock the file @env(windows-2022)` is read with the text `Lock the file`, not `@manual`, with no operating system and one tag it does not read, `@env(windows-2022)`
- PROOF-28 (RULE-40): The proof text `Lock the file @manual @smoke` is read whole: `@smoke` stops the reading, so the `@manual` before it stays in the text, and the proof is not `@manual`, with no operating system
- PROOF-29 (RULE-40): The proof text `Check the documented tags @manual, @env`, whose last at-word follows a comma, is read whole, not `@manual`, with no operating system and no tag it does not read
- PROOF-52 (RULE-13): A project holding `specs/auth/login.md` and `specs/admin/login.md` is reported with `specs/auth/login.md and specs/admin/login.md are both named login; only specs/auth/login.md is read. Rename one: git mv specs/admin/login.md specs/admin/<new name>.md`
- PROOF-13 (RULE-15): A spec carrying a heading `## What it does` above its `## Rules` is read: the status report names the spec, carries no line containing `is not numbered` and never mentions `What it does`, and the spec's rules read exactly `RULE-1`
- PROOF-23 (RULE-19): In a project tracking `src/app.py` and `src/other.py`, a spec scoped `src/app.py` keeps the code part of its fingerprint unchanged when `src/other.py` is edited
- PROOF-24 (RULE-19): In a project tracking `src/app.py` and `src/other.py`, the code part of the fingerprint of a spec scoped `src/app.py` changes when `src/app.py` is edited
- PROOF-76 (RULE-32): An anchor `security` carrying `> Scope: src/app.py, src/db.py` is read with an empty scope, naming no path
- PROOF-2 (RULE-38): A spec at `specs/test/test_feat.md` whose rules hold `RULE-1` and the line `- some constraint without RULE-N prefix` is reported with the warning line ``test_feat: 1 line under ## Rules is not numbered; a rule is `- RULE-N: <text>`. Run purlin:spec test_feat.``
- PROOF-71 (RULE-38): A feature `login` carrying `> Requires: api` is reported with `login: > Requires: is not read, because every anchor covers the whole project. Run purlin:spec login.`
- PROOF-78 (RULE-38): The pinned anchor `security_baseline`, its `> Source:` `https://github.com/acme/policies.git specs/baseline.md`, carries `> Scope: src/`; the status report carries `security_baseline: its source, https://github.com/acme/policies.git, carries > Scope:, which Purlin does not read on an anchor, so the line is read as nothing. Ask the owners of https://github.com/acme/policies.git to take it out, then run purlin:anchor sync security_baseline.`
- PROOF-87 (RULE-38): A spec `checkout` whose `PROOF-2` ends `@manual @slow` is reported with `checkout: PROOF-2 is tagged @slow and @manual; a hand check has no test to leave out, so it is read as @manual. Run purlin:spec checkout.`, and its `PROOF-2` is read as `@manual` and not slow
- PROOF-46 (RULE-39): A spec at `specs/test/login.md` whose rules read `RULE-1`, `RULE-2: Old text` and `RULE-2: New text` is reported with `login: RULE-2 is written twice; the second is read. Run purlin:spec login.`, and its rules read exactly `RULE-1` and `RULE-2`, with `RULE-2` reading `New text`
- PROOF-81 (RULE-39): A spec `login` whose `## Proof` holds `PROOF-4 (RULE-1): Old text` and `PROOF-4 (RULE-2): New text` is reported with `login: PROOF-4 is written twice; the second is read. Run purlin:spec login.`, and its one `PROOF-4` reads `New text`
- PROOF-82 (RULE-39): A spec `login` holding one line `=======`, at line 12, is reported with `login: 1 line is left from a merge conflict, at line 12: =======. Run purlin:spec login.`
- PROOF-14 (RULE-41): A spec whose rules are `RULE-1`, `RULE-3` and `RULE-20`, each with a proof, is reported with no line containing `is not numbered`, and its rules read exactly `RULE-1`, `RULE-3` and `RULE-20`, in that order
- PROOF-69 (RULE-41): The spec format page says a spec whose `> Highest-Proof:` reads `12`, and whose `PROOF-10` to `PROOF-12` were deleted, gives its next proof `PROOF-13`
- PROOF-62 (RULE-42): A spec carrying `> Highest-Rule: 12` has the same fingerprint, all three parts, as the same spec with that line taken out
- PROOF-66 (RULE-42): The `> Stack:` of a spec is rewritten from `python/stdlib` to `node/express`; all three parts of its fingerprint equal the ones taken before
- PROOF-64 (RULE-27): The first line of the spec format page reads `> Format-Version: ` followed by a whole number and nothing else
