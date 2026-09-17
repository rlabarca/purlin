# Feature: specs

> Description: One walk of `specs/` turns every spec file into a feature
>   dictionary. This is where the rule tags, the proof tiers, the `@env`
>   operating system, the anchor source and pin, the two text hashes a
>   signature binds and the scope tree a record carries are all read. Every
>   other surface reads what this module returns rather than the markdown.
> Scope: scripts/mcp/purlin/specs.py
> Stack: python/stdlib, re, hashlib, subprocess (list-only)

## Rules

- RULE-1: A rule line's `[risk: ...]`, `[origin: ...]` and `[criterion: ...]` tags are read off the end of the line one at a time in any order, and the text that remains is the claim alone [risk: high] [origin: eng]
- RULE-2: A rule naming no tag takes `risk` `low` and `origin` `eng`, and carries no `criterion` key at all [risk: medium] [origin: eng]
- RULE-3: The rule and proof text hashes normalise runs of whitespace to one space, so reflowing or retagging a line returns the hash it already had [risk: high] [origin: eng]
- RULE-4: A proof line's trailing `@<name>` that is not `@env` is the tier, and a proof naming no tier is tier `unit` [risk: medium] [origin: eng]
- RULE-5: `@env` takes `windows`, `macos` and `linux` and nothing else; any other value is read as no operating system at all and is listed as an unknown tag [risk: high] [origin: eng]
- RULE-6: At most one `@env` per proof: the trailing one is the one read and the earlier one is listed as an unknown tag rather than merged with it [risk: medium] [origin: eng]
- RULE-7: Tags this release does not read (the retired operating-system tag `@env` replaced, a bare `@windows` used as a tier, a stamped `@manual(...)` carrying an email, a date and a sha) and the retired fields `> Visual-Reference:` and `> Visual-Hash:` are ignored rather than refused, and every spec carrying one lists it under `unknown_tags` [risk: medium] [origin: eng]
- RULE-8: The unknown-tag warning is one line naming at most five carrying files and counting the rest, and is absent when no spec carries such a tag [risk: low] [origin: eng]
- RULE-9: A `> Source:` value is read three ways: a git URL followed by a path in that repository gives the two separately, a comma-separated or glob-bearing value gives the file globs, and anything else comes back whole as the source rather than split on its first word [risk: medium] [origin: eng]
- RULE-10: A `> Path:` line supplies the path in the source repository when `> Source:` carries the URL alone [risk: low] [origin: eng]
- RULE-11: A spec is an anchor when its path lies under an `_anchors/` directory or its first line opens `# Anchor:`, and an anchor carries its `> Source:` and its `> Pinned:` sha [risk: medium] [origin: eng]
- RULE-12: The scope tree is a sha256 over each scoped file's git blob id written beside its path in sorted order; a scope entry naming a directory expands to the files under it, and a path git cannot hash contributes an empty id instead of raising [risk: high] [origin: eng]
- RULE-13: A feature must prove its own rules, the rules of every spec it requires and of everything those require in turn, and the rules of every anchor carrying `> Global: true`, labelled `own`, `required` and `global`; an anchor proves its own rules and nothing else [risk: high] [origin: eng]
- RULE-14: Every spec is keyed by its filename stem, and a file that cannot be read or decoded is skipped while the rest of the scan still answers [risk: medium] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Parse a spec whose RULE-1 line ends `[risk: high] [origin: pm] [criterion: US-12]`; verify the parsed text is exactly `Valid credentials return 200 with a session token` with no bracket left in it, and that the rule's metadata is exactly `{"risk": "high", "origin": "pm", "criterion": "US-12"}` @integration
- PROOF-2 (RULE-1): Call the rule tag splitter on `Tokens expire [origin: qa] [risk: medium]` and `Tokens expire [risk: medium] [origin: qa]`; verify both return the text `Tokens expire` and the same metadata, so the order the tags are written in changes nothing
- PROOF-3 (RULE-2): Parse a rule line carrying no tag; verify its metadata is exactly `{"risk": "low", "origin": "eng"}` and that no `criterion` key is present @integration
- PROOF-4 (RULE-3): Call the rule text hash on `Tokens expire after 24 hours`, then call it on the text left by splitting `Tokens  expire   after 24 hours [risk: high]`; verify the two hashes are equal, so neither a doubled space nor a tag changes the rule text hash a signature binds
- PROOF-5 (RULE-4): Parse a proof line ending `@unit @env(windows)`; verify the tier is `unit` and the operating system is `windows`, and that a proof line with no tag at all comes back at tier `unit` @integration
- PROOF-6 (RULE-5): Call the proof tag splitter on `x @env(windows)`, `x @env(macos)` and `x @env(linux)` and verify each returns its own value; then call it on `x @env(bsd)` and verify the operating system is none and the unknown tags are exactly `["@env(bsd)"]` @integration
- PROOF-7 (RULE-6): Split `Lock it @env(macos) @env(windows)`; verify the operating system read is `windows` and the unknown tags are exactly `["@env(macos)"]`, so the second tag is refused rather than merged
- PROOF-8 (RULE-7): Write one spec whose proof line ends with the retired operating-system tag naming `windows-2022`, and a second carrying `> Visual-Reference:` and a stamped `@manual(a@b.c, 2026-03-31, abc1234)`; scan them and verify the first proof reads no operating system and lists exactly that one retired tag, and that the second proof still parses at tier `manual` while listing the stamp and `> Visual-Reference:` @integration
- PROOF-9 (RULE-8): Scan the two specs above and read the warning; verify it is a single line naming `specs/auth/login.md` and `specs/auth/legacy.md` and carrying no newline, and that a scan of specs carrying no such tag returns no warning at all @integration
- PROOF-10 (RULE-9): Parse `https://github.com/acme/p.git specs/no_eval.md` and verify it returns that URL with the path `specs/no_eval.md` and no globs; parse `designs/checkout/*.png, designs/checkout/*.pdf` and verify it returns those two globs and no source; parse `--upload-pack=/bin/echo` and verify the whole string comes back as the source, so a value that has to be refused is refused whole
- PROOF-11 (RULE-10): Write an anchor whose `> Source:` is the URL `https://github.com/acme/p.git` alone and whose `> Path:` reads `specs/no_eval.md`; scan it and verify the parsed path is `specs/no_eval.md` while the source is the URL alone @integration
- PROOF-12 (RULE-11): Write `specs/_anchors/policy.md` opening `# Anchor: policy` with `> Source: https://github.com/acme/p.git specs/no_eval.md` and `> Pinned: abc1234def`; scan it and verify it is marked an anchor, that the source is that URL, the path `specs/no_eval.md` and the pin `abc1234def` @integration
- PROOF-13 (RULE-12): Call the scope tree over `src/login.py`; verify it is 64 characters, write that file afresh and verify the tree changes, and call it on an empty scope and verify it is still 64 characters rather than an error @integration
- PROOF-14 (RULE-13): Write anchor `api` with one rule, global anchor `security` with one rule and feature `login` with two own rules and `> Requires: api`; call the rule reference walk for `login` and verify it returns exactly `login/RULE-1 own`, `login/RULE-2 own`, `api/RULE-1 required` and `security/RULE-1 global` in that order; call it for `security` and verify it returns that anchor's own rule alone @integration
- PROOF-15 (RULE-14): Write `specs/auth/login.md` and a second file whose bytes are not valid UTF-8; scan the directory and verify the result holds the key `login` and no key for the undecodable file, and that scanning a project with no `specs/` directory returns an empty result rather than raising @integration
