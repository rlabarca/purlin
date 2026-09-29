# Anchor: schema_spec_format

> Description: The spec format: the two sections every spec carries, the rule and proof
>   grammar, the metadata fields, the `@manual` tag and the `@env` tag, and
>   the values this release refuses rather than reads. Every surface that reads a spec
>   reads it through one parser, so a spec means the same thing to the status table, the
>   dashboard and the evidence file. The `specs` feature, which is that parser, requires
>   this anchor.
> Type: schema
> Scope: scripts/mcp/purlin/specs.py, references/formats/spec_format.md, references/formats/anchor_format.md
> Stack: python/stdlib, one regex parser in scripts/mcp/purlin/specs.py

## Rules

- RULE-1: A spec carries two sections, `## Rules` and `## Proof`, and the format names no third
- RULE-2: Rule ids read `RULE-N`; the author assigns them in increasing order and never reuses one, so a retired rule leaves its number vacant and a gap in the sequence is reported as nothing
- RULE-3: A proof line reads `PROOF-N (RULE-N)`, and names several rules as `PROOF-N (RULE-A, RULE-B)` when one flow drives all of them; a list item under `## Proof` of any other form is not read as a proof
- RULE-4: A rule that no proof line names carries an empty proof list, and while no test marked with the rule's own id answers it, its passed cell reads `no test` with the reason `no proof written`, so a spec cannot claim evidence it does not have
- RULE-5: `> Requires:` is a comma-separated list of spec names whose rules are counted with this spec's own and carry the label `required`
- RULE-6: `> Scope:` is a comma-separated list of file paths, parsed into a list in the order written
- RULE-7: The file name is the spec's name, whatever its first line says; a first line `# Anchor: <name>` makes a spec an anchor wherever it is kept; a first line `# Feature: <other>` or `# Anchor: <other>` naming another feature is warned of
- RULE-8: `> Description:` takes continuation lines that begin with `>` and are not themselves a `> Field:` line, so the next field's value never reaches the description
- RULE-9: A proof line carries at most one `@manual` tag and at most one `@env` tag, in either order, read off the end of the line
- RULE-10: `@env` takes `windows`, `macos` or `linux` and nothing else; any other value is returned in the unknown list and sets no environment, so a proof is never treated as owned by an operating system the release cannot name
- RULE-11: `> Note:` is free text addressed to whoever reads the spec; the parser ignores it, it never reaches the description or displaces `> Source:`, and a spec may carry more than one
- RULE-12: The two section headings are matched without regard to case, so `## rules` and `## PROOF` are read as `## Rules` and `## Proof`
- RULE-13: Two specs with one file name in different folders are warned of: only one is read, and the warning names both files, the one read, and the `git mv` that renames the other
- RULE-14: A `> Scope:` entry that finds no file git tracks is warned of, naming the spec, the entry and `purlin:spec`, where the spec's other entries reach files; a spec none of whose entries finds a file is reported only as naming no files
- RULE-15: A spec carrying a heading the format does not name still parses, its rules are still read, and nothing is reported about the extra heading
- RULE-16: A line under `## Rules` carrying no id is reported as a warning saying it is not numbered
- RULE-17: A rule number written twice is warned of, and the rule is read once, with the text of its second line
- RULE-18: A list item under `## Proof` that is not a proof line is warned of
- RULE-19: The code part of the spec's fingerprint hashes exactly the files `> Scope:` names, so an edit to any other file leaves it unchanged and a code change is told from a rule change
- RULE-20: A second `@manual` on a proof line reads as one
- RULE-21: Of two `@env` tags on a proof line, the last written is the environment and the earlier is returned in the unknown list
- RULE-22: A trailing at-word that is not `@manual`, `@env` or a bare `@windows`, and carries no value in brackets, is not a tag and stops the reading
- RULE-23: A tag that follows a list connector (a comma, `and`, `or`) is not a tag, so a description whose prose ends in an at-word is left whole
- RULE-24: A bare `@windows` and any other at-word carrying a value in brackets are returned in the unknown list and set no environment; a `@manual` carrying a value still reads as `@manual`

## Proof

- PROOF-1 (RULE-1): The spec format reference, under its heading `## Required sections`, names exactly two sections, `## Rules` and `## Proof`, and no third
- PROOF-13 (RULE-15): A spec carrying a heading `## What it does` above its `## Rules` is read: the status report names the spec, carries no `WARNING` and never mentions `What it does`, and the spec's rules read exactly `RULE-1`
- PROOF-2 (RULE-16): A spec at `specs/test/test_feat.md` whose rules hold `RULE-1` and the line `- some constraint without RULE-N prefix` is reported with the warning `WARNING: 1 line under ## Rules in specs/test/test_feat.md is not numbered`, which then gives the form `- RULE-N: <text>` and ends `Run purlin:spec test_feat.`
- PROOF-14 (RULE-2): A spec whose rules are `RULE-1`, `RULE-3` and `RULE-20`, each with a proof, is reported with no `WARNING`, and its rules read exactly `RULE-1`, `RULE-3` and `RULE-20`, in that order
- PROOF-45 (RULE-16): A spec at `specs/test/test_feat.md` whose rules hold `RULE-1` and two lines with no id is reported with the warning `WARNING: 2 lines under ## Rules in specs/test/test_feat.md are not numbered`
- PROOF-46 (RULE-17): A spec at `specs/test/login.md` whose rules read `RULE-1`, `RULE-2: Old text` and `RULE-2: New text` is reported with `login: RULE-2 is written twice; the second is read. Run purlin:spec login.`, and its rules read exactly `RULE-1` and `RULE-2`, with `RULE-2` reading `New text`
- PROOF-15 (RULE-3): In a spec holding `RULE-1`, `RULE-2` and `RULE-3`, the line `PROOF-1 (RULE-1): One rule` is read as a proof of `RULE-1` alone, and `PROOF-1` is the one proof of `RULE-1`
- PROOF-16 (RULE-3): In a spec holding `RULE-1`, `RULE-2` and `RULE-3`, the line `PROOF-2 (RULE-2, RULE-3): One flow drives both` is read as a proof of `RULE-2` and `RULE-3`, and `PROOF-2` is the one proof of each
- PROOF-17 (RULE-3): In a spec holding `RULE-1`, `RULE-2` and `RULE-3`, the line `PROOF-3: No rule named`, which names no rule in brackets, is not read as a proof: the spec has no proof `PROOF-3`
- PROOF-47 (RULE-18): A spec at `specs/test/login.md` whose `## Proof` holds the line `- PROOF-7 shows the lockout` is reported with `login: a line under ## Proof cannot be read: - PROOF-7 shows the lockout. Run purlin:spec login.`
- PROOF-48 (RULE-18): A spec at `specs/test/login.md` whose `## Proof` holds an unreadable line of 90 characters is reported with the warning quoting only the line's first 60 characters, `- PROOF-8 shows that a locked account stays locked for fifte`
- PROOF-4 (RULE-4): A spec holding `RULE-1` and an empty `## Proof` section, with no test, is read: `RULE-1` carries no proof, and its passed cell reads `no test` with the one reason `no proof written`
- PROOF-18 (RULE-4): A spec holding `RULE-1` and the line `PROOF-1 (RULE-1)`, with no test, is read: `RULE-1` carries the one proof `PROOF-1`, and its passed cell reads `no test` without the reason `no proof written`
- PROOF-19 (RULE-4): At the gate `passed`, a spec holding `RULE-1` and no proof line, whose one test is marked `purlin: feat RULE-1` and passes in a test run, is read: `RULE-1` carries no proof, and its passed cell reads `passed` with no reason
- PROOF-5 (RULE-5): A feature carrying `> Requires: base` and one rule of its own is read beside an anchor `base` that holds `RULE-1`; among the feature's rules, those labelled `required` are exactly `RULE-1` of `base`
- PROOF-20 (RULE-5): A feature carrying `> Requires: other, base` and one rule of its own, where `other` holds `RULE-1` and `RULE-2` and `base` holds `RULE-1`, has its rules read in this order: its own `RULE-1` labelled `own`, then `RULE-1` and `RULE-2` of `other` and `RULE-1` of `base`, each labelled `required`
- PROOF-21 (RULE-5): A feature carrying `> Requires: base, ghost` and one rule of its own, where `base` holds `RULE-1` and no spec is named `ghost`, has exactly two rules, its own `RULE-1` and `RULE-1` of `base`; `ghost` adds none
- PROOF-6 (RULE-6): A spec carrying `> Scope: src/alpha.py, src/zeta.py` is read with a scope of exactly two paths, `src/alpha.py` then `src/zeta.py`
- PROOF-22 (RULE-6): A spec carrying `> Scope: src/zeta.py, src/alpha.py` is read with a scope of exactly two paths in the order written, `src/zeta.py` then `src/alpha.py`, not sorted
- PROOF-23 (RULE-19): In a project tracking `src/app.py` and `src/other.py`, a spec scoped `src/app.py` keeps the code part of its fingerprint unchanged when `src/other.py` is edited
- PROOF-24 (RULE-19): In a project tracking `src/app.py` and `src/other.py`, the code part of the fingerprint of a spec scoped `src/app.py` changes when `src/app.py` is edited
- PROOF-49 (RULE-7): A spec at `specs/test/login.md` whose first line reads `# Feature: checkout` is read as the feature `login`, and is reported with `login: the first line names checkout, but the file is login.md, so it is read as login. Run purlin:spec login.`
- PROOF-50 (RULE-7): A spec at `specs/test/login.md` whose first line reads `Login rules`, neither form, is read as the feature `login`, and the status report carries no line about its first line
- PROOF-51 (RULE-7): A spec at `specs/test/base.md` whose first line reads `# Anchor: base` is read as an anchor, though it is kept outside `specs/_anchors/`
- PROOF-8 (RULE-8): A spec whose metadata reads `> Description: First line`, then the continuation `>   second line`, then `> Scope: src/`, is read with a description holding `First line` and `second line` and not `src/`, and a scope of exactly `src/`
- PROOF-9 (RULE-9): The proof text `Check it by hand @manual` is read as `@manual`, with no operating system, no tag it does not read, and the text `Check it by hand`
- PROOF-25 (RULE-9): The proof text `Lock the file @manual @env(windows)` is read as `@manual` on `windows`, with no tag it does not read, and the text `Lock the file`
- PROOF-26 (RULE-9): The proof text `Lock the file @env(windows) @manual`, the same two tags in the other order, is read exactly as `Lock the file @manual @env(windows)` is: `@manual` on `windows`, the text `Lock the file`, no tag it does not read
- PROOF-56 (RULE-9): A spec's proof line reads `Lock a file; verify a second open fails @manual @env(windows)`; once the spec is read, the proof is manual, to be proved on `windows`, and its text is `Lock a file; verify a second open fails`
- PROOF-27 (RULE-22): The proof text `Grep the file; verify present @smoke` is read whole, `@smoke` included, not `@manual`, with no operating system and no tag it does not read
- PROOF-28 (RULE-22): The proof text `Lock the file @manual @smoke` is read whole: `@smoke` stops the reading, so the `@manual` before it stays in the text, and the proof is not `@manual`, with no operating system
- PROOF-57 (RULE-22): A spec's proof line reads `Call login and verify 200 @smoke`; once the spec is read, the proof's text is that whole line, `@smoke` included, the proof is not manual, and the spec has no unknown tag
- PROOF-29 (RULE-23): The proof text `Check the documented tags @manual, @env`, whose last at-word follows a comma, is read whole, not `@manual`, with no operating system and no tag it does not read
- PROOF-30 (RULE-23): The proof text `Accepts either @env or @manual`, whose last at-word follows `or`, is read whole, not `@manual`, with no operating system and no tag it does not read
- PROOF-31 (RULE-23): The proof text `Check the format lists @manual, @env and @windows`, whose last at-word follows `and`, is read whole, not `@manual`, with no operating system and no tag it does not read
- PROOF-32 (RULE-21): The proof text `Lock the file @env(linux) @env(macos)` is read on `macos`, the last written, not `@manual`, with the text `Lock the file` and one tag it does not read, `@env(linux)`
- PROOF-33 (RULE-20): The proof text `Lock the file @manual @manual` is read as `@manual`, with no operating system, the text `Lock the file` and no tag it does not read
- PROOF-34 (RULE-23): A spec whose proof line ends `delete it, and read the refusal, one line each @env(linux)`, with a comma and `and` earlier in its prose, is read on `linux`, not `@manual`, with its text ending `read the refusal, one line each`
- PROOF-35 (RULE-9): A spec whose proof text quotes the tags `@env(macos) @manual` in backticks mid-sentence and ends in plain words is read not `@manual`, with no operating system, and with its last words kept
- PROOF-10 (RULE-10): The proof text `Lock the file @env(windows)` is read on `windows`, not `@manual`, with the text `Lock the file` and no tag it does not read
- PROOF-36 (RULE-10): The proof text `Lock the file @env(macos)` is read on `macos`, not `@manual`, with the text `Lock the file` and no tag it does not read
- PROOF-37 (RULE-10): The proof text `Lock the file @env(linux)` is read on `linux`, not `@manual`, with the text `Lock the file` and no tag it does not read
- PROOF-38 (RULE-10): The proof text `Lock the file @env(windows-2022)` is read with the text `Lock the file`, not `@manual`, with no operating system and one tag it does not read, `@env(windows-2022)`
- PROOF-39 (RULE-10): The proof text `Lock the file @env(ubuntu-24.04)` is read with the text `Lock the file`, not `@manual`, with no operating system and one tag it does not read, `@env(ubuntu-24.04)`
- PROOF-40 (RULE-10): The proof text `Lock the file @env(Windows)`, with a capital `W`, is read with the text `Lock the file`, not `@manual`, with no operating system and one tag it does not read, `@env(Windows)`
- PROOF-41 (RULE-24): The proof text `Lock the file @windows` is read with the text `Lock the file`, not `@manual`, with no operating system and one tag it does not read, `@windows`
- PROOF-42 (RULE-24): The proof text `Lock the file @manual(2024-01-01)` is read with the text `Lock the file`, as `@manual`, with no operating system and one tag it does not read, `@manual(...)`
- PROOF-43 (RULE-24): The proof text `Lock the file @smoke(x)` is read with the text `Lock the file`, not `@manual`, with no operating system and one tag it does not read, `@smoke(...)`
- PROOF-11 (RULE-11): An anchor carrying `> Description: Local policy`, two `> Note:` lines and `> Source: ./vendor/policy.git` is read with the description `Local policy`, the source `./vendor/policy.git` and its `RULE-1`, and the words of neither note appear anywhere in what is read
- PROOF-12 (RULE-12): A spec whose headings read `## rules` and `## PROOF`, holding `RULE-1` and `PROOF-1 (RULE-1)`, is read as a spec with a rules section: its rules read exactly `RULE-1`, and `PROOF-1` is the one proof of `RULE-1`
- PROOF-44 (RULE-12): A spec whose headings read `## Rule` and `## Proofs`, each one letter off, is read with no rules section, no rules and no proofs
- PROOF-52 (RULE-13): A project holding `specs/auth/login.md` and `specs/admin/login.md` is reported with `specs/auth/login.md and specs/admin/login.md are both named login; only specs/auth/login.md is read. Rename one: git mv specs/admin/login.md specs/admin/<new name>.md`
- PROOF-53 (RULE-14): In a project whose git tracks `src/app.py`, a spec `login` scoped `src/app.py, src/gone.py` is reported with `login: > Scope: names src/gone.py, which finds no file in git. Run purlin:spec login.`
- PROOF-54 (RULE-14): In a project whose git tracks `src/app.py` and not `src/new.py`, which is on the disk, a spec `login` scoped `src/app.py, src/new.py` is reported with `login: > Scope: names src/new.py, which finds no file in git. Run purlin:spec login.`
- PROOF-55 (RULE-14): In a project whose git tracks `src/app.py`, a spec `login` scoped `src/gone.py` alone is reported with `1 spec names no files, so its tests run every time: login.` and with no line saying `which finds no file in git`
