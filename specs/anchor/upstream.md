# Feature: upstream

> Description: The anchor tool's upstream half. A project pins an anchor that
>   another repository publishes, sees when that pin falls behind, pulls the new
>   version in one step, and sends a local edit back as a patch. A pin is always
>   a commit, never a branch, so what a project is holding is one sha a reader
>   can check out. Nothing here reaches the network on its own account: every
>   source is a git url the caller named, and a source that is free text rather
>   than a repository is copied in as a drafted anchor instead.
> Scope: scripts/anchor/upstream.py
> Stack: python/stdlib, git plumbing over subprocess, no third-party package

## Rules

- RULE-1: `add <source> --path <file>` writes the anchor to `specs/_anchors/<name>.md` with the author's body unchanged under its title, and adds `> Source: <source> <file>` and `> Pinned: <sha>` [risk: high] [origin: eng]
- RULE-2: The pin `add` writes is the source's head commit as a full 40-character sha, and no branch name reaches the copy [risk: high] [origin: eng]
- RULE-3: With no `--name`, the anchor is named after the file the `--path` names [risk: low] [origin: eng]
- RULE-4: Tracking fields the source itself carried are stripped before the copy is written, so a copy of a copy holds one `> Source:` and one `> Pinned:`, both this project's [risk: medium] [origin: eng]
- RULE-5: A `--path` the source does not hold writes no file and reports the path it could not read [risk: medium] [origin: eng]
- RULE-6: A source that begins with `-`, or that names the `ext::` transport, is refused before any process starts and nothing is written [risk: high] [origin: eng]
- RULE-7: A source that is a readable text file rather than a repository is copied in whole as a drafted anchor carrying a note and no rules, pinned by the hash of its text, so rewording the source moves the pin [risk: medium] [origin: eng]
- RULE-8: `sync --check` writes no file: it reports each anchor as current or behind and carries both the pinned sha and the source's head sha [risk: high] [origin: eng]
- RULE-9: `sync --check` exits 0 when every pin is current, 1 when a pin is behind, and 2 when a named anchor does not exist or a source cannot be read [risk: high] [origin: eng]
- RULE-10: `--json` prints the whole answer as one JSON object carrying `checked`, `behind` and a row per anchor; without it the lines name the anchor behind and the `purlin:anchor sync <name>` that fixes it [risk: medium] [origin: eng]
- RULE-11: `sync <name>` rewrites the copy from the source at its new head, advances `> Pinned:`, and reports the rule delta as added, removed and changed ids plus a one-line summary [risk: high] [origin: eng]
- RULE-12: A source whose rules did not move reports no rule changes and still advances the pin [risk: low] [origin: eng]
- RULE-13: A sync copies every design file the source's text names into `designs/<anchor>/`, and creates no directory when the source names none [risk: medium] [origin: eng]
- RULE-14: `sync` with no name covers every anchor whose source is a repository and no others, so a free-text anchor is never fetched [risk: medium] [origin: eng]
- RULE-15: One run reaches each distinct source once, however many anchors are pinned to it [risk: low] [origin: eng]
- RULE-16: `propose <name>` writes the difference between the local copy and the source to `.purlin/runtime/anchors/<name>.patch` as a patch against the source's own path, and the project's tracking fields never reach it [risk: high] [origin: eng]
- RULE-17: The patch is taken against the pin rather than the source's head, so a rule the source added after the pin is never proposed back to it [risk: high] [origin: eng]
- RULE-18: A copy that matches its pin proposes nothing and says there is nothing to propose [risk: low] [origin: eng]
- RULE-19: `propose` prints the commands that carry the patch upstream, ending with the one the source's git host takes: `gh pr create` for GitHub and `az repos pr create` for Azure DevOps [risk: medium] [origin: eng]
- RULE-20: An anchor that names a source and carries no pin cannot be proposed: the run reports the missing pin and exits 2 [risk: medium] [origin: eng]
- RULE-21: `--help` names `add`, `sync` and `propose`, and a call with no arguments exits 2 naming `--project-root` [risk: low] [origin: eng]
- RULE-22: Every file the module writes lies under the project root it was given [risk: high] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Publish `# Anchor: no_eval` with two rules to a bare repository, then run `add` against a fresh project with `--path specs/no_eval.md --name no_eval`; verify the copy at `specs/_anchors/no_eval.md` begins `# Anchor: no_eval`, holds `> Source: <the repository> specs/no_eval.md` and `> Pinned: <the published sha>`, and still carries the line `- RULE-1: No eval() in source files [risk: high]` exactly as the author wrote it @integration
- PROOF-2 (RULE-2): Run `add` against a published anchor; verify the pin returned equals `git rev-parse HEAD` in the source, that it is 40 characters long, and that the text above `## Rules` in the copy contains no occurrence of `main` @integration
- PROOF-3 (RULE-3): Run `add` with `--path specs/no_secrets.md` and no `--name`; verify the result names the anchor `no_secrets` and that `specs/_anchors/no_secrets.md` exists @integration
- PROOF-4 (RULE-4): Publish an anchor whose own text already carries `> Source: git@example.com:other.git a.md` and `> Pinned: deadbeef`, run `add` on it, and verify the copy holds exactly one `> Source:` line, exactly one `> Pinned:` line, and no occurrence of `deadbeef` @integration
- PROOF-5 (RULE-5): Run `add` with `--path specs/absent.md` against a source that has no such file; verify the result reports an error naming `specs/absent.md` and that no file was written at `specs/_anchors/no_eval.md` @integration
- PROOF-6 (RULE-6): Run `add` with the source `--upload-pack=/bin/echo` and again with the source `ext::sh -c touch`; verify the first is refused with a message containing `begins with "-"`, the second with a message naming the `ext:: transport`, and that no anchor file was written either time @integration
- PROOF-7 (RULE-7): Write a text file holding the single sentence `Every refund is approved by a second person.` and run `add` on it with `--name refunds`; verify the result reads `drafted`, that the copy carries that sentence, the free-text note, a `## Rules` and a `## Proof` heading and no `RULE-` line at all, and that adding the same unchanged file twice returns the same pin. Hand the same absolute path and the repository path to the free-text test and verify it answers true for the file and false for the repository @integration
- PROOF-8 (RULE-8): Pin an anchor, publish a new version of it, read the copy's bytes, then run `sync --check`; verify the row reads `behind`, that its `pinned` is the first sha and its `remote_sha` the new one, that `behind` counts 1, and that the copy's bytes are unchanged @integration
- PROOF-9 (RULE-9): Run `sync --check` on a current pin and verify the exit code is 0 and the row reads `current`; publish a new version and verify the exit code is 1; run `sync --check` naming an anchor that does not exist and verify the row reads `error` and the exit code is 2; delete the source repository from disk and verify an unreachable source is also an error at exit code 2 @integration
- PROOF-10 (RULE-10): Run `sync --check --json` from the command line on a current pin and verify exit 0 with `behind` 0 in the parsed object; publish a new version and verify exit 1 with `checked` true, `behind` 1 and the first row's `remote_sha` equal to the new sha; run `sync --check` without `--json` and verify exit 1 with `is behind its source` and `purlin:anchor sync no_eval` in the printed lines @integration
- PROOF-11 (RULE-11): Pin an anchor, publish a version that reworded RULE-2 and added RULE-3, then run `sync no_eval`; verify the row reads `synced`, that `previous` is the old sha and `pinned` the new one, that the rule delta reads added `RULE-3`, removed nothing and changed `RULE-2`, that the summary reads `RULE-2 changed, RULE-3 added`, and that the copy now carries the new `> Pinned:` line and the line `- RULE-3: No compile() in source files [risk: medium]`. Publish instead a version with RULE-2 deleted and verify the delta reports it removed and the summary reads `RULE-2 removed`. Run the same sync from the command line and verify the printed lines carry the summary @integration
- PROOF-12 (RULE-12): Publish a version that changed only a sentence of prose, run `sync no_eval`, and verify the summary reads `no rule changes` while the pin differs from the one before @integration
- PROOF-13 (RULE-13): Publish a version whose text names `designs/checkout/cart.png`, run `sync no_eval`, and verify the row lists `designs/no_eval/cart.png` and that the file at that path in the project holds the source file's bytes. Publish a version naming no design, sync again, and verify the row lists no design and that no `designs` directory exists in the project @integration
- PROOF-14 (RULE-14): Pin two anchors from one repository, add a third from a text file, then run `sync` with no name; verify the rows name exactly the two repository-sourced anchors and not the free-text one @integration
- PROOF-15 (RULE-15): Pin two anchors from the same repository, count every call the module makes to read a remote head, run `sync --check`, and verify two rows came back from exactly 1 call, naming that repository @integration
- PROOF-16 (RULE-16): Pin an anchor, add `- RULE-9: No pickle imports [risk: low]` to the local copy, then run `propose no_eval`; verify the result reads `written` and names `.purlin/runtime/anchors/no_eval.patch`, and that the patch holds `+- RULE-9: No pickle imports [risk: low]`, the header lines `--- a/specs/no_eval.md` and `+++ b/specs/no_eval.md`, and no `> Pinned:` or `> Source:` line @integration
- PROOF-17 (RULE-17): Pin an anchor, add a local rule, then publish a version upstream that adds RULE-3; run `propose no_eval` and verify the patch carries `+- RULE-9: No pickle imports [risk: low]` and no occurrence of `RULE-3`, which the source already holds @integration
- PROOF-18 (RULE-18): Pin an anchor and run `propose no_eval` without editing the copy; verify the result reads `empty` and that the rendered lines contain `nothing to propose` @integration
- PROOF-19 (RULE-19): Run `propose` on an edited copy and verify the printed commands include `git checkout -b purlin/no_eval`, `gh pr create` and `az repos pr create`; then build the commands for `https://github.com/acme/policies.git` and verify the last is exactly `gh pr create --fill`, and for `https://dev.azure.com/acme/_git/policies` and verify the last begins `az repos pr create` @integration
- PROOF-20 (RULE-20): Write an anchor carrying a `> Source:` line and no `> Pinned:` line, run `propose` on it, and verify the result is an error whose text contains `no pin` and whose exit code is 2 @integration
- PROOF-21 (RULE-21): Run the module with `--help` and verify exit 0 with `add`, `sync` and `propose` in the output; run it with no arguments at all and verify exit 2 with `--project-root` in the output @integration
- PROOF-22 (RULE-22): Run `add` and then `sync` against a project directory, and verify the parent directory of that project still holds exactly the four entries it held before: the two bare repositories, the anchor checkout and the project @integration
