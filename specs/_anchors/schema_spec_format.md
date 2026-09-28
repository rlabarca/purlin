# Anchor: schema_spec_format

> Description: The spec format at Format-Version 11: the two sections every spec carries,
>   the rule and proof grammar, the metadata fields, the rule tags, the `@manual` tag and the
>   `@env` tag, and the values this release refuses rather than reads. Every surface that
>   reads a spec reads it through one parser, so a spec means the same thing to the status
>   table, the record and the review brief.
> Type: schema
> Scope: scripts/mcp/purlin/specs.py, references/formats/spec_format.md, references/formats/anchor_format.md
> Stack: python/stdlib, one regex parser in scripts/mcp/purlin/specs.py

## Rules

- RULE-1: A spec carries two sections, `## Rules` and `## Proof`, and the format names no third; a spec carrying a heading the format does not name still parses, its rules are still read, and nothing is reported about the extra heading [bar: strong]
- RULE-2: Rule ids read `RULE-N`, are assigned in increasing order and are never reused, so a retired rule leaves its number vacant and a gap in the sequence is reported as nothing; a line under `## Rules` carrying no id is reported as a warning saying it is not numbered [bar: strong]
- RULE-3: A proof line reads `PROOF-N (RULE-N)`, and names several rules as `PROOF-N (RULE-A, RULE-B)` when one flow drives all of them [bar: strong]
- RULE-4: A rule that no proof line names has the spec status `drafted` and carries an empty proof list, so a spec cannot claim evidence it does not have [bar: strong]
- RULE-5: `> Requires:` is a comma-separated list of spec names whose rules are counted with this spec's own and carry the label `required` [bar: strong]
- RULE-6: `> Scope:` is a comma-separated list of file paths, parsed into a list in the order written, because a record hashes exactly those files to tell a code change from a rule change [bar: strong]
- RULE-7: A first-level heading reads `# Feature: <name>` for a feature spec and `# Anchor: <name>` for an anchor [bar: passed]
- RULE-8: `> Description:` takes continuation lines that begin with `>` and are not themselves a `> Field:` line, so the next field's value never reaches the description [bar: passed]
- RULE-9: A proof line carries at most one `@manual` tag and at most one `@env` tag, in either order, read off the end of the line; any other trailing at-word is not a tag and stops the reading, and a tag that follows a list connector (a comma, `and`, `or`) is not a tag either, so a description whose prose ends in an at-word is left whole [bar: strong]
- RULE-10: `@env` takes `windows`, `macos` or `linux` and nothing else; any other value, and any tag this release stopped reading, is returned in the unknown list and sets no environment, so a proof is never treated as owned by an operating system the release cannot name [bar: strong]
- RULE-11: `> Note:` is free text addressed to whoever reads the spec; the parser ignores it, it never reaches the description or displaces `> Source:`, and a spec may carry more than one [bar: passed]

## Proof

- PROOF-1 (RULE-1): Read `references/formats/spec_format.md`, find the block under its `## Required sections` heading and verify it names both `## Rules` and `## Proof`; grep both format files for the retired third heading `What it does` and verify zero matches; then write a spec that carries that heading between its metadata and its `## Rules`, run `sync_status` over it, and verify the report names the spec, that the built payload lists its rules as exactly `["RULE-1"]`, and that the report carries zero warnings
- PROOF-2 (RULE-2): Write a spec whose `## Rules` holds the line `- some constraint without RULE-N prefix` beside `RULE-1`, run `sync_status`, and verify the report carries `WARNING` and the words `not numbered`; then write a second spec whose rules are `RULE-1`, `RULE-3` and `RULE-20`, each with a proof, and verify the report carries zero warnings and the payload lists exactly those three ids in that order
- PROOF-3 (RULE-3): Read every file under `specs/` and, for each line under its `## Proof` heading that starts a list item, verify it matches `PROOF-\d+ \(RULE-\d+\)`; a line that does not fails naming the file and the line
- PROOF-4 (RULE-4): Write a spec holding `RULE-1` and an empty `## Proof` section, build the payload, and verify `RULE-1` reads an empty proof list and the spec status `drafted`
- PROOF-5 (RULE-5): Write an anchor `base` holding `RULE-1` and a feature spec carrying `> Requires: base`, build the payload for the feature, and verify the rules labelled `required` are exactly `[("base", "RULE-1")]`
- PROOF-6 (RULE-6): Write a spec carrying `> Scope: scripts/mcp/purlin/specs.py, src/app.py`, scan the specs, and verify the parsed scope equals the two-item list in that order; run `sync_status` and verify it names both that spec and an anchor whose scope overlaps it
- PROOF-7 (RULE-7): Read every file under `specs/` and verify each first-level heading begins `# Feature: ` or `# Anchor: `; a heading matching neither fails, naming the file and the heading
- PROOF-8 (RULE-8): Write a spec whose description is `First line` with the continuation `second line`, followed by `> Scope: src/`; scan the specs and verify the description carries both lines and that `src/` is absent from it, while the scope parses as the one-item list `["src/"]`
- PROOF-9 (RULE-9): Call the tag splitter with `Check it by hand @manual`, `Lock the file @manual @env(windows)`, `Lock the file @env(macos) @manual`, `Lock the file @env(linux)`, `Grep the file; verify present @smoke` and a description whose prose ends in a list of at-words after a comma; verify whether each is manual and its environment, that the `@smoke` case and the prose case each return the description whole, not manual, with an empty environment and an empty unknown list, and that the two orders of the same pair of tags return identical tuples
- PROOF-10 (RULE-10): Call the tag splitter with `@env(windows)`, `@env(macos)` and `@env(linux)` and verify each sets that environment with an empty unknown list; call it with `@env(windows-2022)`, `@env(ubuntu-24.04)` and `@env(Windows)` and verify each sets no environment and returns exactly one unknown naming the rejected value; call it with the retired scope tag and verify it sets no environment, is not manual and is returned as unknown
- PROOF-11 (RULE-11): Write an anchor carrying `> Description: Local policy`, two `> Note:` lines and `> Source: ./dev/external-refs/policy.git`; scan the specs and verify the description equals `Local policy`, the source equals that path, the text of either note is absent from every parsed value of the spec, and `RULE-1` still parses
