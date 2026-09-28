# Feature: specs

> Description: One walk of `specs/` turns every spec file into a feature
>   dictionary. This is where the rule tags, the `@manual` tag, the `@env`
>   operating system, the anchor source and pin, and the two text hashes a
>   signature binds are all read. Every other surface reads what this module
>   returns rather than the markdown.
> Scope: scripts/mcp/purlin/specs.py
> Stack: python/stdlib, re, hashlib

## Rules

- RULE-1: A rule line's one tag is `[level: ...]`, read off the end of the line; any other bracketed text at the end is not a tag and stays in the claim
- RULE-2: A rule naming no tag carries empty metadata, with no `level` key at all
- RULE-3: The rule and proof text hashes normalise runs of whitespace to one space, so reflowing a line or changing its tag returns the hash it already had
- RULE-4: A proof line's trailing `@manual` marks a proof no test settles; any other trailing `@<name>` that is not `@env` is not a tag, so reading stops there and the word stays in the proof text
- RULE-5: `@env` takes `windows`, `macos` and `linux` and nothing else; any other value is read as no operating system at all and is listed as an unknown tag
- RULE-6: At most one `@env` per proof: the trailing one is the one read and the earlier one is listed as an unknown tag rather than merged with it
- RULE-7: The tags 0.9.5 wrote that the format does not carry (a bare `@windows`, a stamped `@manual(...)` carrying an email, a date and a sha) and its fields `> Visual-Reference:` and `> Visual-Hash:` are ignored rather than refused, and every spec carrying one lists it under `unknown_tags`
- RULE-8: The unknown-tag warning is one line naming at most five carrying files and counting the rest, and is absent when no spec carries such a tag [level: passed]
- RULE-9: A `> Source:` value is read two ways: a git URL followed by a path in that repository gives the two separately, and anything else comes back whole as the source rather than split on its first word
- RULE-10: A `> Path:` line supplies the path in the source repository when `> Source:` carries the URL alone [level: passed]
- RULE-11: A spec is an anchor when its path lies under an `_anchors/` directory or its first line opens `# Anchor:`, and an anchor carries its `> Source:` and its `> Pinned:` sha
- RULE-13: A feature must prove its own rules, the rules of every spec it requires and of everything those require in turn, and the rules of every anchor carrying `> Global: true`, labelled `own`, `required` and `global`; an anchor proves its own rules and nothing else
- RULE-14: Every spec is keyed by its filename stem, and a file that cannot be read or decoded is skipped while the rest of the scan still answers
- RULE-15: The `[level: ...]` tag is read off the end of a rule line as `passed`, `strong` or `signed`, stripped from the text the rule text hash is taken over, and carried in the rule's metadata under `level`

## Proof

- PROOF-1 (RULE-1): Parse a spec whose RULE-1 line ends `[level: signed]`; verify the parsed text is exactly `Valid credentials return 200 with a session token` with no bracket left in it, and that the rule's metadata is exactly `{"level": "signed"}`
- PROOF-2 (RULE-1): Call the rule tag splitter on `Tokens expire [owner: qa] [level: strong]`; verify the level is `strong` and the text is `Tokens expire [owner: qa]`, so bracketed text that is not a tag stays in the claim
- PROOF-3 (RULE-2): Parse a rule line carrying no tag; verify its metadata is exactly `{}`
- PROOF-4 (RULE-3): Call the rule text hash on `Tokens expire after 24 hours`, then call it on the text left by splitting `Tokens  expire   after 24 hours [level: strong]`; verify the two hashes are equal, so neither a doubled space nor a tag changes the rule text hash a signature binds
- PROOF-5 (RULE-4): Parse a proof line ending `@manual @env(windows)`; verify it reads manual with the operating system `windows`; split a description carrying no tag and verify it comes back whole and not manual; split one ending `@smoke` and verify that word stays in the text and the proof is not manual
- PROOF-6 (RULE-5): Call the proof tag splitter on `x @env(windows)`, `x @env(macos)` and `x @env(linux)` and verify each returns its own value; then call it on `x @env(bsd)` and verify the operating system is none and the unknown tags are exactly `["@env(bsd)"]`
- PROOF-7 (RULE-6): Split `Lock it @env(macos) @env(windows)`; verify the operating system read is `windows` and the unknown tags are exactly `["@env(macos)"]`, so the second tag is refused rather than merged
- PROOF-8 (RULE-7): Write one spec whose proof line ends with a bare `@windows`, and a second carrying `> Visual-Reference:` and a stamped `@manual(a@b.c, 2026-03-31, abc1234)`; scan them and verify the first proof reads no operating system and lists exactly `@windows`, and that the second proof still parses as manual while listing the stamp and `> Visual-Reference:`
- PROOF-9 (RULE-8): Scan the two specs above and read the warning; verify it is a single line naming `specs/auth/login.md` and `specs/auth/legacy.md` and carrying no newline, and that a scan of specs carrying no such tag returns no warning at all
- PROOF-10 (RULE-9): Parse `https://github.com/acme/p.git specs/no_eval.md` and verify it returns that URL with the path `specs/no_eval.md`; parse `./policies` and verify it comes back whole as the source with no path; parse `--upload-pack=/bin/echo` and verify the whole string comes back as the source with no path, so a value that has to be refused is refused whole
- PROOF-11 (RULE-10): Write an anchor whose `> Source:` is the URL `https://github.com/acme/p.git` alone and whose `> Path:` reads `specs/no_eval.md`; scan it and verify the parsed path is `specs/no_eval.md` while the source is the URL alone
- PROOF-12 (RULE-11): Write `specs/_anchors/policy.md` opening `# Anchor: policy` with `> Source: https://github.com/acme/p.git specs/no_eval.md` and `> Pinned: abc1234def`; scan it and verify it is marked an anchor, that the source is that URL, the path `specs/no_eval.md` and the pin `abc1234def`
- PROOF-14 (RULE-13): Write anchor `api` with one rule, global anchor `security` with one rule and feature `login` with two own rules and `> Requires: api`; call the rule reference walk for `login` and verify it returns exactly `login/RULE-1 own`, `login/RULE-2 own`, `api/RULE-1 required` and `security/RULE-1 global` in that order; call it for `security` and verify it returns that anchor's own rule alone
- PROOF-15 (RULE-14): Write `specs/auth/login.md` and a second file whose bytes are not valid UTF-8; scan the directory and verify the result holds the key `login` and no key for the undecodable file, and that scanning a project with no `specs/` directory returns an empty result rather than raising
- PROOF-17 (RULE-15): Parse three rule lines with the same claim, ending `[level: passed]`, `[level: strong]` and `[level: signed]`; verify each carries that value under `level`, that no bracket is left in the text, and that the three lines' rule text hashes are equal
