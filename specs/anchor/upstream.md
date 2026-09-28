# Feature: upstream

> Description: The anchor tool's upstream half. A project pins an anchor that
>   another repository publishes, sees when that pin falls behind, pulls the new
>   version in one step. A pin is always
>   a commit, never a branch, so what a project is holding is one sha a reader
>   can check out. Nothing here reaches the network on its own account: every
>   source is a git url the caller named, and a source that is free text rather
>   than a repository is copied in as an anchor with no rules yet instead.
> Scope: scripts/anchor/upstream.py
> Stack: python/stdlib, git plumbing over subprocess, no third-party package

## Rules

- RULE-1: `add <source> --path <file>` writes the anchor to `specs/_anchors/<name>.md` with the author's body unchanged under its title, and adds `> Source: <source> <file>` and `> Pinned: <sha>`
- RULE-2: The pin `add` writes is the source's head commit as a full 40-character sha, and no branch name reaches the copy
- RULE-3: With no `--name`, the anchor is named after the file the `--path` names [level: passed]
- RULE-4: Tracking fields the source itself carried are stripped before the copy is written, so a copy of a copy holds one `> Source:` and one `> Pinned:`, both this project's
- RULE-5: A `--path` the source does not hold writes no file and reports the path it could not read
- RULE-6: A source that begins with `-`, or that names the `ext::` transport, is refused before any process starts and nothing is written
- RULE-7: A source that is a readable text file rather than a repository is copied in whole as an anchor carrying a note and no rules, pinned by the hash of its text, so rewording the source moves the pin
- RULE-8: `sync --check` writes no file: it reports each anchor as current or behind and carries both the pinned sha and the source's head sha
- RULE-9: `sync --check` exits 0 when every pin is current, 1 when a pin is behind, and 2 when a named anchor does not exist or a source cannot be read
- RULE-10: `--json` prints the whole answer as one JSON object carrying `checked`, `behind` and a row per anchor; without it the lines name the anchor behind and the `purlin:anchor sync <name>` that fixes it
- RULE-11: `sync <name>` rewrites the copy from the source at its new head, advances `> Pinned:`, and reports the rule delta as added, removed and changed ids plus a one-line summary
- RULE-12: A source whose rules did not move reports no rule changes and still advances the pin [level: passed]
- RULE-14: `sync` with no name covers every anchor whose source is a repository and no others, so a free-text anchor is never fetched
- RULE-15: One run reaches each distinct source once, however many anchors are pinned to it [level: passed]
- RULE-21: `--help` names `add` and `sync`, and a call with no arguments exits 2 naming `--project-root` [level: passed]
- RULE-22: Every file the module writes lies under the project root it was given
- RULE-23: A sync keeps every `> Note:` line the local copy carried, in order, beside the tracking fields it rewrites, because a note is the consumer's own text [level: passed]

## Proof

- PROOF-1 (RULE-1): The anchor `# Anchor: no_eval`, with two rules, is published in another repository and added to a fresh project from `specs/no_eval.md` under the name `no_eval`; the copy at `specs/_anchors/no_eval.md` begins `# Anchor: no_eval`, carries `> Source: <the repository> specs/no_eval.md` and `> Pinned: <the published sha>`, and keeps the line `- RULE-1: No eval() in source files` exactly as the author wrote it. Added from the command line, the same anchor exits 0 and the output names `specs/_anchors/no_eval.md`
- PROOF-2 (RULE-2): An anchor is added from a source whose head is on the branch `main`; the pin is the source's head commit as a 40-character sha, and the copy's text above `## Rules` holds no `main`
- PROOF-3 (RULE-3): An anchor is added from `specs/no_secrets.md` with no name given; it is named `no_secrets` and written to `specs/_anchors/no_secrets.md`
- PROOF-4 (RULE-4): A published anchor whose own text already carries `> Source: git@example.com:other.git a.md` and `> Pinned: deadbeef` is added; the copy carries exactly one `> Source:` line and one `> Pinned:` line, and `deadbeef` appears nowhere in it
- PROOF-5 (RULE-5): An anchor is added from `specs/absent.md`, which the source does not hold; the answer is an error naming `specs/absent.md`, and no copy is written at `specs/_anchors/no_eval.md`
- PROOF-6 (RULE-6): An anchor is added from the source `--upload-pack=/bin/echo`, and again from `ext::sh -c touch`; the first is refused with a message containing `begins with "-"` and writes no copy, and the second is refused with a message naming the `ext:: transport`
- PROOF-7 (RULE-7): A text file holding the one sentence `Every refund is countersigned by a second person.` is added as the anchor `refunds`; the answer reads `no_rules`, the copy carries that sentence, the note that the anchor is free text, a `## Rules` and a `## Proof` heading and no `RULE-` line at all, and adding the unchanged file again gives the same pin. The same file is taken as free text and the source repository is not
- PROOF-8 (RULE-8): An anchor is pinned and a new version of it is published; `sync --check` reports the anchor `behind`, with the first sha as `pinned` and the new one as `remote_sha`, counts 1 behind, and leaves the copy byte for byte as it was
- PROOF-9 (RULE-9): `sync --check` exits 0 with the row reading `current` while the pin is current, and 1 once a new version is published; naming an anchor that does not exist, it exits 2 with the row reading `error`; after the source repository is deleted, it exits 2 with the row reading `error`
- PROOF-10 (RULE-10): `sync --check --json` on a current pin exits 0 and prints an object with `behind` 0; after a new version is published it exits 1 with `checked` true, `behind` 1 and the first row's `remote_sha` the new sha. Without `--json` it exits 1 and prints `is behind its source` and `purlin:anchor sync no_eval`
- PROOF-11 (RULE-11): A new version of `no_eval` rewords RULE-2 and adds RULE-3, and `sync no_eval` runs; the row reads `synced`, `previous` is the old sha and `pinned` the new one, the rule changes read added `RULE-3`, removed none and changed `RULE-2`, the summary reads `RULE-2 changed, RULE-3 added`, and the copy carries the new `> Pinned:` line and the line `- RULE-3: No compile() in source files`. A version that deletes RULE-2 instead reads removed `RULE-2`, with the summary `RULE-2 removed`. Run from the command line, the sync prints the summary
- PROOF-12 (RULE-12): A new version changes only a sentence of prose, and `sync no_eval` runs; the summary reads `no rule changes` and the pin still moves to the new version
- PROOF-14 (RULE-14): Two anchors are pinned from one repository and a third is added from a text file; `sync` with no name returns rows for exactly the two from the repository and none for the text file
- PROOF-15 (RULE-15): Two anchors are pinned from the same repository; `sync --check` returns two rows, and that repository's head was read exactly once
- PROOF-21 (RULE-21): `--help` exits 0 and names `add` and `sync`; a call with no arguments at all exits 2 and names `--project-root`
- PROOF-22 (RULE-22): `add` and then `sync` run against a project; the folder that holds the project still holds exactly the four entries it held before
- PROOF-23 (RULE-23): An anchor's copy carries the notes `run the setup script first` and `the pin moves on each release` under its tracking lines; after its source moves and the anchor is synced, the copy carries the new pin and both notes, each once and in that order
