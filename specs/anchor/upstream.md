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
- RULE-3: With no `--name`, the anchor is named after the file the `--path` names
- RULE-4: Tracking fields the source itself carried are stripped before the copy is written, so a copy of a copy holds one `> Source:` and one `> Pinned:`, both this project's
- RULE-5: A `--path` the source does not hold writes no anchor copy and reports the path it could not read
- RULE-6: A source that begins with `-`, or that names the `ext::` transport, is refused before any process starts and nothing is written
- RULE-7: A source that is a readable text file rather than a repository is copied in whole as an anchor carrying a note and no rules, pinned by the hash of its text, so rewording the source moves the pin
- RULE-8: `sync --check` writes no file: it reports each anchor as current or behind and carries both the pinned sha and the source's head sha
- RULE-9: `sync --check` exits 0 when every pin is current, 1 when a pin is behind, and 2 when a named anchor does not exist or a source cannot be read
- RULE-10: `--json` prints the whole answer as one JSON object carrying `checked`, `behind` and `anchors`, one row per anchor; without it each anchor behind gets a line naming it and the `purlin:anchor sync <name>` that fixes it
- RULE-11: `sync <name>` rewrites the copy from the source at its new head, advances `> Pinned:`, and reports the rule delta as added, removed and changed ids plus a one-line summary
- RULE-12: A source whose rules did not move reports no rule changes and still advances the pin
- RULE-14: `sync` with no name covers every anchor whose source is a repository and no others, so a free-text anchor is never fetched
- RULE-15: One run reaches each distinct source once, however many anchors are pinned to it
- RULE-21: `--help` names `add` and `sync`, and a call with no arguments exits 2 naming `--project-root`
- RULE-22: Every file `add` and `sync` write lies under the project root they were given
- RULE-23: A sync keeps every `> Note:` line the local copy carried, in order, beside the tracking fields it rewrites, because a note is the consumer's own text

## Proof

- PROOF-1 (RULE-1): The anchor `no_eval`, with the rules `RULE-1` and `RULE-2`, is published in another repository and added to a project from `specs/no_eval.md`; the answer reads `added`, the two lines after the copy's title are `> Source: <the repository> specs/no_eval.md` and `> Pinned: <the published sha>`, and with those lines taken out the copy reads exactly as the author's file
- PROOF-25 (RULE-1): The published anchor is added from the command line as `add <the repository> --path specs/no_eval.md --name no_eval`; it exits 0 and prints `no_eval: written to specs/_anchors/no_eval.md, pinned <the published sha's first 7 characters>`
- PROOF-2 (RULE-2): An anchor is added from a repository whose head is on the branch `main`; the pin is the head commit's full 40-character sha, and the copy's text above `## Rules` holds no `main`
- PROOF-3 (RULE-3): An anchor is added from `specs/no_secrets.md` with no name given; the answer names it `no_secrets`, and `specs/_anchors/` then holds `no_secrets.md` alone
- PROOF-4 (RULE-4): A published anchor whose own text carries `> Source: git@example.com:other.git a.md` and `> Pinned: deadbeef` is added; the copy holds one `> Source:` line, naming this project's source, one `> Pinned:` line, naming the published sha, and `deadbeef` appears nowhere in it
- PROOF-5 (RULE-5): An anchor is added from `specs/absent.md`, a path the repository does not hold; the answer reads `error` with the message `specs/absent.md is not in the source`, and `specs/_anchors/` stays empty
- PROOF-6 (RULE-6): An anchor is added from the source `--upload-pack=touch <a marker file>`; the answer reads `error` with the message `source rejected: begins with "-"`, `specs/_anchors/` stays empty, the marker file does not exist, and no process was started
- PROOF-26 (RULE-6): An anchor is added from the source `ext::sh -c touch% <a marker file>`; the answer reads `error` with the message `source rejected: names an ext:: transport`, `specs/_anchors/` stays empty, the marker file does not exist, and no process was started
- PROOF-27 (RULE-6): The published anchor is added from its repository on disk; a `git` process is started, and `specs/_anchors/` then holds `no_eval.md`
- PROOF-7 (RULE-7): The file `policy.txt` in the project, holding `Every refund is countersigned by a second person.`, is added as the anchor `refunds`; the answer reads `no_rules`, and the copy carries that sentence, a `> Note:` line beginning `the source is free text`, a `## Rules` and a `## Proof` heading, and no `RULE-` line
- PROOF-24 (RULE-7): The text file is added as the anchor `refunds`, then added again with its text unchanged; both answers carry the same pin
- PROOF-28 (RULE-7): The text file is added as the anchor `refunds`, reworded to `Every refund over 100.00 is countersigned by a second person.` and added again; the pin differs from the first, the copy's `> Pinned:` line carries the new pin and not the old one, and the copy carries the new sentence
- PROOF-29 (RULE-7): A text file named by its full path, which reads like the address of a repository on disk, is added as the anchor `refunds`; the answer reads `no_rules`, the copy carries the file's sentence, and no process was started
- PROOF-8 (RULE-8): An anchor is pinned and a new version of it is published; `sync --check` reports the row `behind`, with the first sha as `pinned` and the new one as `remote_sha`, counts 1 behind, and leaves every file in the project byte for byte as it was
- PROOF-9 (RULE-9): An anchor is pinned to its source's head; `sync --check` exits 0 and prints `no_eval: the pin is current.`
- PROOF-30 (RULE-9): An anchor is pinned and a new version is published; the script run as `sync --check` exits 1
- PROOF-31 (RULE-9): `sync absent --check --json` runs in a project with no anchor named `absent`; it exits 2, and the row reads `error` with the message `no anchor named absent carries a git source`
- PROOF-32 (RULE-9): An anchor is pinned and its source repository is then deleted; `sync --check --json` exits 2, and the row reads `error`
- PROOF-10 (RULE-10): An anchor is pinned to its source's head; `sync --check --json` exits 0 and prints one line, an object whose `checked` is true, `behind` is 0 and `anchors` holds one row reading `current`
- PROOF-33 (RULE-10): An anchor is pinned and a new version is published; `sync --check --json` exits 1 and prints an object whose `checked` is true, `behind` is 1 and `anchors` holds one row with the first sha as `pinned` and the new one as `remote_sha`
- PROOF-34 (RULE-10): An anchor is pinned and a new version is published; `sync --check` exits 1 and prints the one line `no_eval: the pin <first sha7> is behind its source, now <new sha7>. Run purlin:anchor sync no_eval.`
- PROOF-11 (RULE-11): A new version of `no_eval` rewords `RULE-2` and adds `RULE-3`, and `sync no_eval` runs; the row reads `synced`, `previous` the old sha, `pinned` the new one, the rule changes added `RULE-3` and changed `RULE-2`, the summary `RULE-2 changed, RULE-3 added`, and the copy carries the new pin and `- RULE-3: No compile() in source files`
- PROOF-35 (RULE-11): A new version of `no_eval` deletes `RULE-2`, and `sync no_eval` runs; the rule changes read removed `RULE-2` and nothing added or changed, the summary reads `RULE-2 removed`, and the copy holds no `RULE-2` line
- PROOF-36 (RULE-11): A new version of `no_eval` rewords `RULE-2` and adds `RULE-3`, and `sync no_eval` runs from the command line; it exits 0 and prints `no_eval: RULE-2 changed, RULE-3 added. Pin advanced from <old sha7> to <new sha7>.`
- PROOF-12 (RULE-12): A new version of `no_eval` changes only a sentence of its description, and `sync no_eval` runs; the summary reads `no rule changes`, no rule is listed as added, removed or changed, and the copy's pin moves to the new sha
- PROOF-14 (RULE-14): Two anchors are pinned from one repository, a third, `refunds`, is added from a text file, and a new version is published; `sync` with no name returns rows for exactly `no_eval` and `no_secrets`, and no process it starts names the text file
- PROOF-15 (RULE-15): Two anchors are pinned from the same repository; `sync --check` returns two rows, and exactly one process it starts names that repository
- PROOF-21 (RULE-21): `--help` exits 0 and its text names the commands `add` and `sync`
- PROOF-37 (RULE-21): The script is run with no arguments at all from inside a project; it exits 2 and prints text naming `--project-root`
- PROOF-22 (RULE-22): An anchor is added, a new version is published and the anchor is synced; the folder around the project still holds exactly its four entries, `policies.git`, `policies_work`, `project` and `project.git`
- PROOF-23 (RULE-23): An anchor's copy carries the notes `run the setup script first` and `the pin moves on each release` under its tracking lines; after a new version is published and the anchor is synced, the copy carries the new pin and both `> Note:` lines, each once and in that order
