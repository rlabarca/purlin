# Feature: specs

> Description: One walk of `specs/` turns every spec file into a feature
>   dictionary. This is where the rule text, the `@manual` tag, the `@env`
>   operating system, the anchor source and pin, and the two text hashes a
>   signature binds are all read. Every other surface reads what this module
>   returns rather than the markdown.
> Requires: schema_spec_format
> Scope: scripts/mcp/purlin/specs.py
> Stack: python/stdlib, re, hashlib
> Highest-Rule: 21
> Highest-Proof: 43

## Rules

- RULE-3: A rule's text is everything after its id, bracketed text at the end included
- RULE-7: The tags 0.9.5 wrote that the format does not carry (a bare `@windows`, a stamped `@manual(...)` carrying an email, a date and a sha) are ignored rather than refused, and every spec carrying one lists it under `unknown_tags`
- RULE-8: The unknown-tag warning is one line naming at most five carrying files and counting the rest, and is absent when no spec carries such a tag
- RULE-9: A `> Source:` value is read two ways: a git URL followed by a path in that repository gives the two separately, and anything else comes back whole as the source rather than split on its first word
- RULE-10: A `> Path:` line supplies the path in the source repository when `> Source:` carries the URL alone
- RULE-11: A spec is an anchor when its path lies under an `_anchors/` directory or its first line opens `# Anchor:`, and an anchor carries its `> Source:` and its `> Pinned:` sha
- RULE-13: A feature must prove its own rules, the rules of every anchor it requires and of every anchor those require in turn, and the rules of every anchor carrying `> Global: true`, labelled `own`, `required` and `global`
- RULE-14: Every spec is keyed by its filename stem
- RULE-17: The rule and proof text hashes normalise runs of whitespace to one space, so reflowing a line returns the hash it already had
- RULE-18: The fields 0.9.5 wrote that the format does not carry, `> Visual-Reference:` and `> Visual-Hash:`, are ignored rather than refused, and every spec carrying one lists it under `unknown_tags`
- RULE-19: An anchor proves its own rules and nothing else
- RULE-20: A spec file that cannot be read or decoded is skipped while the rest of the scan still answers
- RULE-21: A project with no `specs/` folder has no specs

## Proof

- PROOF-1 (RULE-3): A spec holds the rule line `- RULE-1: Tokens expire [owner: qa]`; once the spec is read, the rule's text is exactly `Tokens expire [owner: qa]`, the bracket included
- PROOF-2 (RULE-3): The rule texts `Tokens expire [owner: qa]` and `Tokens expire` give two different rule text hashes
- PROOF-3 (RULE-17): The proof `Wait 24 hours; verify 401`, written again with doubled spaces and a line break, gives the same proof text hash
- PROOF-4 (RULE-17): The rule `Tokens expire after 24 hours`, written again with doubled and tripled spaces between its words, gives the same rule text hash
- PROOF-19 (RULE-17): The rule `Tokens expire after 24 hours`, written again broken across a line break after `expire`, gives the same rule text hash
- PROOF-17 (RULE-17): The rule `Tokens expire after 12 hours`, one word changed from `Tokens expire after 24 hours`, gives a different rule text hash
- PROOF-18 (RULE-17): The proof `Wait 12 hours; verify 401`, one word changed from `Wait 24 hours; verify 401`, gives a different proof text hash
- PROOF-8 (RULE-7): A spec's proof line reads `Lock a file; verify 1 open fails @windows`; the spec is read rather than refused, the proof's text is `Lock a file; verify 1 open fails`, it is to be proved on no operating system, and the spec's unknown tags are exactly `@windows`
- PROOF-24 (RULE-7): A spec's proof line reads `Look at it @manual(a@b.c, 2026-03-31, abc1234)`; the spec is read rather than refused, the proof's text is `Look at it`, the proof is manual, and the spec's unknown tags are exactly `@manual(...)`
- PROOF-25 (RULE-18): A spec carrying `> Visual-Reference: ./mock.png` and the one rule `It renders` is read rather than refused, with exactly that rule, and its unknown tags are exactly `> Visual-Reference:`
- PROOF-26 (RULE-18): A spec carrying `> Visual-Hash: 9f86d081` and the one rule `It renders` is read rather than refused, with exactly that rule, and its unknown tags are exactly `> Visual-Hash:`
- PROOF-9 (RULE-8): A project holds `specs/auth/login.md`, whose proof ends with a bare `@windows`, and `specs/auth/mockup.md`, whose proof ends `@manual(a@b.c, 2026-03-31, abc1234)`; the status report carries exactly one warning, `2 spec files carry tags this release does not read (@manual(...), @windows); they are ignored: specs/auth/login.md, specs/auth/mockup.md. Run purlin:init --update to remove them.`
- PROOF-27 (RULE-8): Seven specs, `specs/auth/a.md` to `specs/auth/g.md`, each end a proof with a bare `@windows`; the status report carries exactly one warning, `7 spec files carry tags this release does not read (@windows); they are ignored: specs/auth/a.md, specs/auth/b.md, specs/auth/c.md, specs/auth/d.md, specs/auth/e.md, and 2 more. Run purlin:init --update to remove them.`
- PROOF-28 (RULE-8): A project whose one spec carries no tag and no field the format does not carry is read; the status report carries no warning at all
- PROOF-10 (RULE-9): An anchor carrying `> Source: https://github.com/acme/p.git specs/no_eval.md` is read with the source `https://github.com/acme/p.git` and the path `specs/no_eval.md`
- PROOF-29 (RULE-9): An anchor carrying `> Source: ./policies` is read with the source `./policies` and no path
- PROOF-30 (RULE-9): An anchor carrying `> Source: ./policies specs/no_eval.md`, whose first word is not a git URL, is read with the source `./policies specs/no_eval.md` whole and no path, rather than split on the space
- PROOF-31 (RULE-9): An anchor carrying `> Source: --upload-pack=touch x specs/a.md`, whose first word is not a git URL, is read with the source `--upload-pack=touch x specs/a.md` whole and no path, rather than split on a space
- PROOF-11 (RULE-10): An anchor carrying `> Source: https://github.com/acme/p.git`, the URL alone, and `> Path: specs/no_eval.md` is read with the source `https://github.com/acme/p.git` and the path `specs/no_eval.md`
- PROOF-32 (RULE-10): An anchor carrying `> Source: https://github.com/acme/p.git specs/a.md` and `> Path: specs/b.md` is read with the path `specs/a.md`, the one its source line names, and not `specs/b.md`
- PROOF-12 (RULE-11): The spec `specs/_anchors/policy.md`, opening `# Anchor: policy` and carrying `> Source: https://github.com/acme/p.git specs/no_eval.md` and `> Pinned: abc1234def`, is read as an anchor with the source `https://github.com/acme/p.git`, the path `specs/no_eval.md` and the pin `abc1234def`
- PROOF-33 (RULE-11): The spec `specs/_anchors/ruleset.md`, opening `# Feature: ruleset`, is read as an anchor, by its folder alone
- PROOF-42 (RULE-11): On Windows, the spec `specs\_anchors\ruleset.md`, opening `# Feature: ruleset`, is read as an anchor, by its folder alone @env(windows)
- PROOF-34 (RULE-11): The spec `specs/schema/shared.md`, opening `# Anchor: shared`, is read as an anchor, by its first line alone
- PROOF-35 (RULE-11): The spec `specs/auth/login.md`, opening `# Feature: login` and lying under no `_anchors/` folder, is read as a feature and not an anchor
- PROOF-14 (RULE-13): The anchor `api` has one rule, the anchor `security` carries `> Global: true` and one rule, and the feature `login` has two rules and `> Requires: api`; `login` must prove exactly `login` RULE-1 and RULE-2 `own`, `api` RULE-1 `required` and `security` RULE-1 `global`, in that order
- PROOF-36 (RULE-19): The anchor `security` carries `> Global: true` and one rule, beside the feature `login` with two rules; `security` must prove exactly its own RULE-1, labelled `own`
- PROOF-37 (RULE-13): The feature `login` has two rules and `> Requires: api`, the anchor `api` has one rule and `> Requires: base`, and the anchor `base` has one rule; `login` must prove exactly its RULE-1 and RULE-2 `own`, `api` RULE-1 `required` and `base` RULE-1 `required`, in that order
- PROOF-38 (RULE-19): The anchor `api` has one rule and `> Requires: base`, and the anchor `base` has one rule; `api` must prove exactly its own RULE-1, labelled `own`, and nothing of `base`
- PROOF-15 (RULE-14): A project holds `specs/auth/login.md` and `specs/auth/sign_up.md`, both opening `# Feature: login`; it reads as the two specs `login` and `sign_up`, keyed by file name rather than title, with `sign_up` at `specs/auth/sign_up.md`
- PROOF-39 (RULE-20): A project holds `specs/auth/login.md` and `specs/auth/broken.md`, whose bytes are not valid UTF-8; it reads as the one spec `login`, with no `broken`
- PROOF-40 (RULE-21): A project with no `specs/` folder reads as no specs at all, rather than an error
- PROOF-41 (RULE-20): A project holds `specs/auth/login.md` and `specs/auth/locked.md`, which the operating system refuses to read; it reads as the one spec `login`
- PROOF-43 (RULE-20): On Windows, a project holds `specs/auth/login.md` and `specs/auth/locked.md`, which another program holds locked against reading; it reads as the one spec `login` @env(windows)
