# Feature: specs

> Description: One walk of `specs/` turns every spec file into a feature
>   dictionary. This is where the rule text, the `@manual` tag, the `@env`
>   operating system, the anchor source and pin, and the two text hashes an
>   audit entry binds are all read. Every other surface reads what this module
>   returns rather than the markdown.
> Scope: scripts/mcp/purlin/specs.py
> Stack: python/stdlib, re, hashlib
> Highest-Rule: 22
> Highest-Proof: 43

## Rules

- RULE-22: The tags and fields 0.9.5 wrote that the format does not carry (a bare `@windows`, a stamped `@manual(...)`, `> Visual-Reference:` and `> Visual-Hash:`) are ignored rather than refused, a stamped `@manual(...)` still reading as `@manual`, and the status carries one warning naming at most five carrying files, counting the rest, and `purlin:init --update`
- RULE-9: A `> Source:` value is read two ways: a git URL followed by a path in that repository gives the two separately, and anything else comes back whole as the source rather than split on its first word
- RULE-10: A `> Path:` line supplies the path in the source repository when `> Source:` carries the URL alone
- RULE-11: A spec is an anchor when its path lies under an `_anchors/` directory or its first line opens `# Anchor:`, and an anchor carries its `> Source:` and its `> Pinned:` sha
- RULE-17: The rule and proof text hashes normalise runs of whitespace to one space, so reflowing a line returns the hash it already had
- RULE-20: A spec file that cannot be read or decoded is skipped while the rest of the scan still answers

## Proof

- PROOF-24 (RULE-22): A spec's proof line reads `Look at it @manual(a@b.c, 2026-03-31, abc1234)`; the spec is read rather than refused, the proof's text is `Look at it`, the proof is manual, and the spec's unknown tags are exactly `@manual(...)`
- PROOF-25 (RULE-22): A spec carrying `> Visual-Reference: ./mock.png` and the one rule `It renders` is read rather than refused, with exactly that rule, and its unknown tags are exactly `> Visual-Reference:`
- PROOF-9 (RULE-22): A project holds `specs/auth/login.md`, whose proof ends with a bare `@windows`, and `specs/auth/mockup.md`, whose proof ends `@manual(a@b.c, 2026-03-31, abc1234)`; the status report carries exactly one warning, `2 spec files carry tags this release does not read (@manual(...), @windows); they are ignored: specs/auth/login.md, specs/auth/mockup.md. Run purlin:init --update to remove them.`
- PROOF-10 (RULE-9): An anchor carrying `> Source: https://github.com/acme/p.git specs/no_eval.md` is read with the source `https://github.com/acme/p.git` and the path `specs/no_eval.md`
- PROOF-31 (RULE-9): An anchor carrying `> Source: --upload-pack=touch x specs/a.md`, whose first word is not a git URL, is read with the source `--upload-pack=touch x specs/a.md` whole and no path, rather than split on a space
- PROOF-11 (RULE-10): An anchor carrying `> Source: https://github.com/acme/p.git`, the URL alone, and `> Path: specs/no_eval.md` is read with the source `https://github.com/acme/p.git` and the path `specs/no_eval.md`
- PROOF-12 (RULE-11): The spec `specs/_anchors/policy.md`, opening `# Anchor: policy` and carrying `> Source: https://github.com/acme/p.git specs/no_eval.md` and `> Pinned: abc1234def`, is read as an anchor with the source `https://github.com/acme/p.git`, the path `specs/no_eval.md` and the pin `abc1234def`
- PROOF-33 (RULE-11): The spec `specs/_anchors/ruleset.md`, opening `# Feature: ruleset`, is read as an anchor, by its folder alone
- PROOF-34 (RULE-11): The spec `specs/schema/shared.md`, opening `# Anchor: shared`, is read as an anchor, by its first line alone
- PROOF-19 (RULE-17): The rule `Tokens expire after 24 hours`, written again broken across a line break after `expire`, gives the same rule text hash
- PROOF-17 (RULE-17): The rule `Tokens expire after 12 hours`, one word changed from `Tokens expire after 24 hours`, gives a different rule text hash
- PROOF-39 (RULE-20): A project holds `specs/auth/login.md` and `specs/auth/broken.md`, whose bytes are not valid UTF-8; it reads as the one spec `login`, with no `broken`
