# Feature: upstream

> Description: The anchor tool's upstream half. A project pins an anchor that
>   another repository publishes, sees when that pin falls behind, pulls the new
>   version in one step. The status and drift check a pin against its source and
>   pull nothing; only `purlin:anchor sync` pulls. A pin is always
>   a commit, never a branch, so what a project is holding is one sha a reader
>   can check out. Nothing here reaches the network on its own account: every
>   source is a git url the caller named, and an anchor's source is a spec in
>   Purlin's format kept in a git repository.
> Scope: scripts/anchor/upstream.py
> Stack: python/stdlib, git plumbing over subprocess, no third-party package
> Highest-Rule: 41
> Highest-Proof: 65

## Rules

- RULE-1: `add <source> --path <file>` writes the anchor to `specs/_anchors/<name>.md` with the author's body unchanged under its title, and adds `> Source: <source> <file>` and `> Pinned: <sha>`
- RULE-2: The pin `add` writes is the source's head commit as a full 40-character sha, and no branch name reaches the copy
- RULE-3: With no `--name`, the anchor is named after the file the `--path` names
- RULE-4: Tracking fields the source itself carried are stripped before the copy is written, so a copy of a copy holds one `> Source:` and one `> Pinned:`, both this project's
- RULE-39: `add` writes nothing when no `--path` is given, when the source does not hold the `--path`, or when the source is not a spec in Purlin's format kept in a git repository, whether a file on disk, a description in words or a file in a repository holding no rule, and says what is wrong and, where there is one, the command that fixes it
- RULE-6: A source that begins with `-`, or that names the `ext::` transport, is refused before any process starts and nothing is written
- RULE-22: Every file `add` and `sync` write lies under the project root they were given
- RULE-8: `sync --check` writes no file: it reports each anchor as current or behind and carries both the pinned sha and the source's head sha
- RULE-37: `sync --check` exits 0 when every pin is current, 1 when a pin is behind, and 2 when a named anchor does not exist or a source cannot be read
- RULE-38: Without `--json`, `sync --check` gives each anchor one line naming it and its state, and each anchor that is not current also the command that fixes it: one behind, one that names a source and no pin, and one whose source cannot be read
- RULE-10: `--json` prints the whole answer as one JSON object carrying `checked`, `behind` and `anchors`, one row per anchor
- RULE-11: `sync <name>` rewrites the copy from the source at its new head, advances `> Pinned:`, and reports the rule delta as added, removed and changed ids plus a one-line summary
- RULE-23: A sync keeps every `> Note:` line the local copy carried, in order, beside the tracking fields it rewrites, because a note is the consumer's own text
- RULE-35: `sync <name>` makes no commit: the anchor copy whose pin it advances is left changed and not committed
- RULE-25: `sync --check`, `sync <name>` and `sync` with no name report an anchor whose `> Source:` names no repository as `error` with the line `<name>: its source, <source>, is not a spec in Purlin's format kept in a git repository, so it cannot be checked. Run purlin:spec <name> to take out its > Source: and > Pinned: lines and keep it as this project's own anchor.`, start no process for it, write nothing and exit 2
- RULE-36: The check the status and drift make of a remote anchor reads its source's head and pulls nothing: the anchor copy is left byte for byte as it was, whether its pin is current or behind
- RULE-40: `add` refuses a name an anchor in the project already holds, writes nothing and names `purlin:anchor sync <name>`
- RULE-41: `add` and `sync` read no file outside the fetched source: `add` refuses a `--path` that is absolute or holds `..` before anything is fetched, and a path that leads out of the source by a link reads as not in the source

## Proof

- PROOF-1 (RULE-1): The anchor `no_eval`, with the rules `RULE-1` and `RULE-2`, is published in another repository and added to a project from `specs/no_eval.md`; the answer reads `added`, the two lines after the copy's title are `> Source: <the repository> specs/no_eval.md` and `> Pinned: <the published sha>`, and with those lines taken out the copy reads exactly as the author's file
- PROOF-46 (RULE-1): On Windows, the anchor `no_eval` is added from another repository's `specs/no_eval.md`; the answer reads `added`, the copy carries `> Source:` and `> Pinned:` lines naming that repository and its sha, and no downloaded file is left under `.purlin/runtime/anchors/` @env(windows)
- PROOF-2 (RULE-2): An anchor is added from a repository whose head is on the branch `main`; the pin is the head commit's full 40-character sha, and the copy's text above `## Rules` holds no `main`
- PROOF-3 (RULE-3): An anchor is added from `specs/no_secrets.md` with no name given; the answer names it `no_secrets`, and `specs/_anchors/` then holds `no_secrets.md` alone
- PROOF-4 (RULE-4): A published anchor whose own text carries `> Source: git@example.com:other.git a.md` and `> Pinned: deadbeef` is added; the copy holds one `> Source:` line, naming this project's source, one `> Pinned:` line, naming the published sha, and `deadbeef` appears nowhere in it
- PROOF-54 (RULE-39): The published repository is added as the anchor `no_eval` with no `--path`; it exits 2, prints `no_eval: no path into the source; pass --path`, and `specs/_anchors/` stays empty
- PROOF-5 (RULE-39): An anchor is added from `specs/absent.md`, a path the repository does not hold; the answer reads `error` with the message `specs/absent.md is not in the source`, and `specs/_anchors/` stays empty
- PROOF-42 (RULE-39): The anchor `refunds` is added from `docs/refunds.md` in another repository, a file holding prose and no rule; it exits 2 and prints `refunds: not added. docs/refunds.md is not a spec in Purlin's format kept in a git repository. Run purlin:anchor create refunds to write its rules in this project.`, `specs/_anchors/` is not created, and `.purlin/runtime/anchors/` holds no file
- PROOF-6 (RULE-6): An anchor is added from the source `--upload-pack=touch <a marker file>`; the answer reads `error` with the message `source rejected: begins with "-"`, `specs/_anchors/` stays empty, the marker file does not exist, and no process was started
- PROOF-26 (RULE-6): An anchor is added from the source `ext::sh -c touch% <a marker file>`; the answer reads `error` with the message `source rejected: names an ext:: transport`, `specs/_anchors/` stays empty, the marker file does not exist, and no process was started
- PROOF-27 (RULE-6): The published anchor is added from its repository on disk; a `git` process is started, and `specs/_anchors/` then holds `no_eval.md`
- PROOF-22 (RULE-22): An anchor is added, a new version is published and the anchor is synced; the folder around the project still holds exactly its four entries, `policies.git`, `policies_work`, `project` and `project.git`
- PROOF-8 (RULE-8): An anchor is pinned and a new version of it is published; `sync --check` reports the row `behind`, with the first sha as `pinned` and the new one as `remote_sha`, counts 1 behind, and leaves every file in the project byte for byte as it was
- PROOF-48 (RULE-8): On Windows, an anchor is pinned and a new version of it is published; `sync --check` reports the row `behind` with both shas, counts 1 behind, and leaves every file in the project byte for byte as it was @env(windows)
- PROOF-9 (RULE-37): An anchor is pinned to its source's head; `sync --check` exits 0 and prints the one line `no_eval: the pin is current. Run purlin:status no_eval to see its rules.`
- PROOF-30 (RULE-37): An anchor is pinned and a new version is published; the script run as `sync --check` exits 1
- PROOF-32 (RULE-37): An anchor is pinned and its source repository is then deleted; `sync --check --json` exits 2, and the row reads `error`
- PROOF-34 (RULE-38): An anchor is pinned and a new version is published; `sync --check` exits 1 and prints the one line `no_eval: the pin <first sha7> is behind its source, now <new sha7>. Run purlin:anchor sync no_eval.`
- PROOF-55 (RULE-38): The anchor `loose` carries a `> Source:` naming the published repository and no `> Pinned:` line; `sync --check` prints the one line `loose: names a source and no pin. Run purlin:anchor sync loose.`
- PROOF-57 (RULE-38): An anchor is pinned and its source repository is then deleted; `sync --check` exits 2 and prints the one line `no_eval: the source could not be read (<git's message>). Check its > Source: line, then run purlin:anchor sync no_eval.`
- PROOF-33 (RULE-10): An anchor is pinned and a new version is published; `sync --check --json` exits 1 and prints an object whose `checked` is true, `behind` is 1 and `anchors` holds one row with the first sha as `pinned` and the new one as `remote_sha`
- PROOF-11 (RULE-11): A new version of `no_eval` rewords `RULE-2` and adds `RULE-3`, and `sync no_eval` runs; the row reads `synced`, `previous` the old sha, `pinned` the new one, the rule changes added `RULE-3` and changed `RULE-2`, the summary `RULE-2 changed, RULE-3 added`, and the copy carries the new pin and `- RULE-3: No compile() in source files`
- PROOF-12 (RULE-11): A new version of `no_eval` changes only a sentence of its description, and `sync no_eval` runs; the summary reads `no rule changes`, no rule is listed as added, removed or changed, and the copy's pin moves to the new sha
- PROOF-50 (RULE-11): On Windows, a new version of `no_eval` rewords `RULE-2` and adds `RULE-3`, and `sync no_eval` runs; the row reads `synced`, the summary `RULE-2 changed, RULE-3 added`, and the copy carries the new pin with no carriage return @env(windows)
- PROOF-23 (RULE-23): An anchor's copy carries the notes `run the setup script first` and `the pin moves on each release` under its tracking lines; after a new version is published and the anchor is synced, the copy carries the new pin and both `> Note:` lines, each once and in that order
- PROOF-59 (RULE-35): An added `no_eval` is committed, a new version is published, and `sync no_eval` advances the pin; HEAD is the commit it was before, and git reads the anchor copy as changed and not committed
- PROOF-43 (RULE-25): The anchor `refunds` carries `> Source: policy.txt`, a file in the project; `sync --check` exits 2 and prints the one line the rule names, with `refunds` as the name and `policy.txt` as the source, starts no process, and changes no file
- PROOF-45 (RULE-25): Two anchors are pinned from one repository, a third, `refunds`, carries `> Source: policy.txt`, a file in the project, and a new version is published; `sync` with no name exits 2, the two remote anchors read `synced`, `refunds` reads `error`, no process it starts names `policy.txt`, and the copy of `refunds` is unchanged
- PROOF-60 (RULE-36): The anchor `no_eval` is pinned, a new version of it is published, and the status is read; it prints `no_eval: the pin <first sha7> is behind its source, now <new sha7>. Run purlin:anchor sync no_eval.`, and `specs/_anchors/no_eval.md` is byte for byte as it was
- PROOF-61 (RULE-22): The published anchor is added with `--name ../../outside`; it exits 2, the answer reads `error`, `specs/_anchors/` stays empty and no `outside.md` exists under the folder around the project
- PROOF-65 (RULE-22): The published anchor is added with `--name sample-age`; it exits 0, and `specs/_anchors/sample-age.md` holds its rules
- PROOF-62 (RULE-40): With `specs/_anchors/no_eval.md` holding the project's own rule `No eval in scripts`, the published anchor is added as `no_eval`; it exits 2, the answer reads `error`, and the file holds exactly its text from before
- PROOF-63 (RULE-41): The folder around the project holds `private_notes.md`, a spec in Purlin's format, and the published anchor is added with `--path ../../../../../private_notes.md`, which names that file from the fetched source; it exits 2, the answer reads `error`, and `specs/_anchors/` stays empty
- PROOF-64 (RULE-41): The published anchor is added with `--path` naming `private_notes.md` by its absolute path; it exits 2, the answer's error reads `not added. --path takes a path inside the source, with no .. and no leading /. Run purlin:anchor add <source> --path <path> --name private_notes.`, and `specs/_anchors/` stays empty
