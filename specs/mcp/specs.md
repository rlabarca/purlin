# Feature: specs

> Description: One walk of `specs/` turns every spec file into a feature
>   dictionary. This is where the rule text, the `@manual` tag, the `@env`
>   operating system, the anchor source and pin, and the two text hashes a
>   signature binds are all read. Every other surface reads what this module
>   returns rather than the markdown.
> Requires: schema_spec_format
> Scope: scripts/mcp/purlin/specs.py
> Stack: python/stdlib, re, hashlib

## Rules

- RULE-3: A rule's text is everything after its id, bracketed text at the end included, and the rule and proof text hashes normalise runs of whitespace to one space, so reflowing a line returns the hash it already had
- RULE-4: A proof line's trailing `@manual` marks a proof no test settles; any other trailing `@<name>` that is not `@env` is not a tag, so reading stops there and the word stays in the proof text
- RULE-5: `@env` takes `windows`, `macos` and `linux` and nothing else; any other value is read as no operating system at all and is listed as an unknown tag
- RULE-6: At most one `@env` per proof: the trailing one is the one read and the earlier one is listed as an unknown tag rather than merged with it
- RULE-7: The tags 0.9.5 wrote that the format does not carry (a bare `@windows`, a stamped `@manual(...)` carrying an email, a date and a sha) and its fields `> Visual-Reference:` and `> Visual-Hash:` are ignored rather than refused, and every spec carrying one lists it under `unknown_tags`
- RULE-8: The unknown-tag warning is one line naming at most five carrying files and counting the rest, and is absent when no spec carries such a tag
- RULE-9: A `> Source:` value is read two ways: a git URL followed by a path in that repository gives the two separately, and anything else comes back whole as the source rather than split on its first word
- RULE-10: A `> Path:` line supplies the path in the source repository when `> Source:` carries the URL alone
- RULE-11: A spec is an anchor when its path lies under an `_anchors/` directory or its first line opens `# Anchor:`, and an anchor carries its `> Source:` and its `> Pinned:` sha
- RULE-13: A feature must prove its own rules, the rules of every spec it requires and of everything those require in turn, and the rules of every anchor carrying `> Global: true`, labelled `own`, `required` and `global`; an anchor proves its own rules and nothing else
- RULE-14: Every spec is keyed by its filename stem, and a file that cannot be read or decoded is skipped while the rest of the scan still answers

## Proof

- PROOF-1 (RULE-3): A spec's rule line reads `Tokens expire [owner: qa]`; once the spec is read, the rule's text is exactly `Tokens expire [owner: qa]`, the bracket included
- PROOF-2 (RULE-3): The rule texts `Tokens expire [owner: qa]` and `Tokens expire` give two different rule text hashes
- PROOF-3 (RULE-3): The proof `Wait 24 hours; verify 401`, written again with doubled spaces and a line break, gives the same proof text hash
- PROOF-4 (RULE-3): The rule `Tokens expire after 24 hours`, written again with doubled and tripled spaces, and again broken across a line break after `expire`, gives the same rule text hash each time
- PROOF-5 (RULE-4): A proof line ending `@manual @env(windows)` is read as manual, to be proved on `windows`; the proof line `Call login and verify 200`, with no tag, comes back whole and not manual; `Call login and verify 200 @smoke` comes back with `@smoke` still in its text and not manual; `x @manual @smoke` comes back whole, both words in its text, and not manual, because reading stops at `@smoke` before `@manual` is reached
- PROOF-6 (RULE-5): The proof lines `x @env(windows)`, `x @env(macos)` and `x @env(linux)` are each read with that operating system; `x @env(bsd)` is read with no operating system at all, and its unknown tags are exactly `@env(bsd)`; a spec whose one proof line ends `@env(bsd)` is read with that proof on no operating system and the spec's `unknown_tags` exactly `@env(bsd)`
- PROOF-7 (RULE-6): The proof line `Lock it @env(macos) @env(windows)` is read with the operating system `windows`, the trailing tag, and its unknown tags are exactly `@env(macos)`, so the earlier tag is listed rather than merged with the later one
- PROOF-8 (RULE-7): Two specs are read: `login`, whose proof line ends with a bare `@windows`, and `mockup`, which carries `> Visual-Reference: ./mock.png` and a proof line ending `@manual(a@b.c, 2026-03-31, abc1234)`; both are read rather than refused, the `login` proof has no operating system and that spec's `unknown_tags` are exactly `@windows`, and the `mockup` proof still reads manual while that spec's `unknown_tags` are exactly `@manual(...)` and `> Visual-Reference:`. A third spec, `swatch`, carrying `> Visual-Hash: 9f86d081`, is read with its rule `It renders` and its `unknown_tags` exactly `> Visual-Hash:`
- PROOF-9 (RULE-8): Scan the two specs above and read the warning; verify it is a single line naming `specs/auth/login.md` and `specs/auth/mockup.md` and carrying no newline, and that a scan of specs carrying no such tag returns no warning at all
- PROOF-10 (RULE-9): The source `https://github.com/acme/p.git specs/no_eval.md` is read as the repository `https://github.com/acme/p.git` and the path `specs/no_eval.md`; the source `./policies` comes back whole as the source with no path, and so does `--upload-pack=/bin/echo`; `./policies specs/no_eval.md` and `--upload-pack=touch x specs/a.md`, whose first words are not git URLs, each come back whole as the source with no path rather than split on the space
- PROOF-11 (RULE-10): Write an anchor whose `> Source:` is the URL `https://github.com/acme/p.git` alone and whose `> Path:` reads `specs/no_eval.md`; scan it and verify the parsed path is `specs/no_eval.md` while the source is the URL alone
- PROOF-12 (RULE-11): The spec `specs/_anchors/policy.md`, opening `# Anchor: policy` and carrying `> Source: https://github.com/acme/p.git specs/no_eval.md` and `> Pinned: abc1234def`, is read as an anchor with the source `https://github.com/acme/p.git`, the path `specs/no_eval.md` and the pin `abc1234def`. Either condition alone is enough: `specs/_anchors/ruleset.md`, opening `# Feature: ruleset`, and `specs/schema/shared.md`, opening `# Anchor: shared`, are each read as an anchor, while `specs/auth/login.md`, opening `# Feature: login`, is not
- PROOF-14 (RULE-13): The anchor `api` has one rule, the anchor `security` carries `> Global: true` and one rule, and the feature `login` has two rules and `> Requires: api`; the rules `login` must prove are exactly `login` RULE-1 `own`, `login` RULE-2 `own`, `api` RULE-1 `required` and `security` RULE-1 `global`, in that order, and the rules `security` must prove are its own RULE-1 alone, labelled `own`. Once `api` carries `> Requires: base` and the feature `base` has one rule, `login` must prove exactly `login` RULE-1 and RULE-2 `own`, `api` RULE-1 `required`, `base` RULE-1 `required` and `security` RULE-1 `global`, in that order, while `api`, an anchor that requires `base`, must prove its own RULE-1 alone
- PROOF-15 (RULE-14): A project holds `specs/auth/login.md` and `specs/auth/sign_up.md`, both titled `# Feature: login`, and `specs/auth/broken.md`, whose bytes are not valid UTF-8; its specs are read as `login` and `sign_up`, keyed by file name rather than title, with `sign_up` at `specs/auth/sign_up.md`, and no `broken`. A project with no `specs/` folder reads as no specs at all rather than an error. On a system where file permissions can refuse a read, a project holding `login` and `specs/auth/locked.md` with no read permission reads as `login` alone
- PROOF-17 (RULE-3): The rule `Tokens expire after 12 hours`, one word changed from `Tokens expire after 24 hours`, gives a different rule text hash
- PROOF-18 (RULE-3): The proof `Wait 12 hours; verify 401`, one word changed from `Wait 24 hours; verify 401`, gives a different proof text hash
