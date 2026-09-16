# Feature: drift

> Description: What moved since the evidence was last written. Drift reads
>   git for the commits and the changed files, classifies each file against
>   the specs' scope lines, checks every anchor pin against its source, and
>   adds what the payload already knows about the cells and the signatures.
>   Four role views come out of the same data, because a PM, a designer, QA
>   and an engineer ask different questions of it.
> Scope: scripts/mcp/purlin/drift.py
> Stack: python/stdlib, json, re, subprocess (list-only)

## Rules

- RULE-1: A `since` argument is accepted only as a commit count of digits or a `YYYY-MM-DD` date; any other value is refused with the error `rejected since` and a reason naming both accepted forms, and no subprocess starts [risk: high] [origin: eng]
- RULE-2: With no argument the anchor is the last commit touching `.purlin/records/`, then the most recent tag, then the commit that added `.purlin/config.json`; a project with no verification history and 30 commits or more gets a `spec-from-code` recommendation instead of a diff of everything [risk: medium] [origin: eng]
- RULE-3: Every changed file is classified exactly once, as one of CHANGED_SPECS, CHANGED_DESIGNS, TESTS_CHANGED, CHANGED_BEHAVIOR, NO_IMPACT or NEW_BEHAVIOR [risk: high] [origin: eng]
- RULE-4: A changed file under `skills/`, `agents/` or `.claude/agents/` that no spec scopes is NEW_BEHAVIOR and never NO_IMPACT: those directories hold behaviour even though the files are markdown [risk: medium] [origin: eng]
- RULE-5: A `> Scope:` entry ending in `/` matches every file under that directory [risk: medium] [origin: eng]
- RULE-6: Every changed file's line count is read from a single numbered-stat diff taken over the whole range, so the number of git calls does not grow with the number of files [risk: medium] [origin: eng]
- RULE-7: The report carries `since`, `commits`, `files`, `spec_changes`, `broken_scopes`, `pins`, `rule_details`, `summary`, `review_list` and `roles` [risk: high] [origin: eng]
- RULE-8: `broken_scopes` names every spec whose `> Scope:` points at a path that is no longer on disk, and the paths that are gone [risk: medium] [origin: eng]
- RULE-9: `spec_changes` names, per changed spec, the rule ids the range added and the rule ids it removed [risk: medium] [origin: eng]
- RULE-10: A pinned anchor whose source has moved past the pin is reported `behind` with the remote's short sha; an anchor naming a source and no pin is `unpinned`; a source that cannot be read is `error` with the reason; an anchor still at its pin is not reported at all [risk: high] [origin: eng]
- RULE-11: A `> Source:` value is refused before any process starts when it begins with `-`, names an `ext::` or an `fd::` transport, or carries a NUL byte or a newline, and the refusal names which of those it was [risk: high] [origin: eng]
- RULE-12: One remote listing per source per run: an anchor repository serving six anchors is reached once [risk: medium] [origin: eng]
- RULE-13: A pin row names the anchor's own spec name, never the repository path and never the file inside it [risk: medium] [origin: eng]
- RULE-14: The four role views `pm`, `design`, `qa` and `eng` are present on every report, each carrying its own keys: criteria without rules, pm-owned rules changed, engineer-added rules and pins behind for the PM; designs changed and design rules whose signature went stale for the designer; signatures stale, the length of the review list, the rules that need a person and the rules with no negative case for QA; files touched, rules affected, tests missing, tags missing, pins behind and the rules whose code changed for the engineer [risk: high] [origin: eng]
- RULE-15: A role argument narrows the answer to `since`, `role`, `view` and `commits`, and nothing else [risk: medium] [origin: eng]
- RULE-16: `rule_details` carries, per spec with a changed scope file, the spec path, the changed files, the total rule count, how many meet the gate, the ids whose spec status is `drafted` and the rules in rule-number order, each description cut to 200 characters on a word boundary and suffixed with an ellipsis when cut [risk: medium] [origin: eng]
- RULE-17: The report is serialized with no indentation and no space after a separator, because its only reader is a model paying by the token [risk: medium] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Call drift with `since` set to `--output=/tmp/x` while `subprocess.run` is wrapped by a capturing spy; verify the returned JSON carries `error` `rejected since`, that the reason names both a commit count and a `YYYY-MM-DD` date, and that the spy captured zero calls. As a control, call it with `since` `2` and verify a `commits` list comes back and the spy did capture calls @integration
- PROOF-2 (RULE-1): Call drift over a temporary project with `since` set to `--output=/tmp/x`; verify the parsed report's `error` reads exactly `rejected since` @integration
- PROOF-3 (RULE-2): Build three repositories. In the first, commit a file under `.purlin/records/`; call the anchor resolver with no argument and verify the ref is that commit's sha and the description opens `last record`. In the second, commit no record, tag `v1.0.0` and commit once more; verify the ref is `v1.0.0`. In the third, commit `.purlin/config.json` first and 2 commits after it; verify the ref is that first commit with the description `since purlin:init (2 commits)`, then add 30 more commits and verify no ref comes back and the answer is the recommendation `spec-from-code` @integration
- PROOF-4 (RULE-3): Commit a changed spec, a changed test file, a changed scoped source file, a file under `designs/`, a new `README.md` and a new file no spec scopes; run drift and verify the six entries read CHANGED_SPECS, TESTS_CHANGED, CHANGED_BEHAVIOR, CHANGED_DESIGNS, NO_IMPACT and NEW_BEHAVIOR, one category each @integration
- PROOF-5 (RULE-4): Commit a new file at each of `skills/build/SKILL.md`, `agents/reviewer.md` and `.claude/agents/helper.md`, none of them scoped by any spec; run drift and verify all 3 come back NEW_BEHAVIOR and none comes back NO_IMPACT @integration
- PROOF-6 (RULE-5): Write a spec whose scope is `src/api/` and commit a change to `src/api/login.js`; run drift and verify that file is CHANGED_BEHAVIOR and names that spec @integration
- PROOF-7 (RULE-6): Commit 12 files of differing length in one commit, then run drift with `since` `1` while `subprocess.run` is wrapped by a capturing spy; verify exactly 1 captured call carries the numbered-stat flag, that all 12 file entries carry a line count matching `^\+\d+ -\d+$`, and that each value equals the numbered stat taken for that path on its own @integration
- PROOF-8 (RULE-7): Run drift over a committed change and verify the parsed report carries all 10 named keys @integration
- PROOF-9 (RULE-8): Write a spec whose `> Scope:` names `src/gone.py`, a path that is not on disk; run drift and verify `broken_scopes` holds exactly one entry naming that spec and the missing path `src/gone.py` @integration
- PROOF-10 (RULE-9): Add a rule to a committed anchor file and commit it; run drift and verify `spec_changes` holds exactly one entry for that anchor whose added rule ids carry `RULE-2` @integration
- PROOF-11 (RULE-10): Create a bare repository, pin an anchor to its first commit, push a second commit to it and run drift; verify `pins` holds exactly one entry for that anchor with status `behind` and a `remote_sha` of 7 characters that opens the new head sha @integration
- PROOF-12 (RULE-10): Create a bare repository holding an anchor that carries local rules of its own, pin it to the first commit, push a second commit and run drift; verify exactly 1 entry for that anchor comes back with status `behind` @integration
- PROOF-13 (RULE-11): Run the source check over the values `--upload-pack=/bin/echo`, `ext::sh -c id` and `fd::7`; verify each is refused with the reason `begins with "-"`, `names an ext:: transport` and `names an fd:: transport`, and that `https://github.com/acme/p.git` is accepted with an empty reason
- PROOF-14 (RULE-12): Check the same pinned source 3 times through one cache while `subprocess.run` is wrapped by a capturing spy; verify exactly 1 captured call lists the remote @integration
- PROOF-15 (RULE-13): Create a bare repository holding `constraints.md`, pin the anchor `local_security` to its first commit, advance the remote and run drift; verify the entry that is behind names the anchor `local_security` and names neither the repository path nor `constraints.md` @integration
- PROOF-16 (RULE-14): Commit a change to a scoped source file and run drift with `since` `1`; verify the roles are exactly `design`, `eng`, `pm` and `qa`, that the engineer's files touched carry `src/login.py` and that its missing tests read `login/RULE-1` and `login/RULE-2` @integration
- PROOF-17 (RULE-15): Run drift with the role `qa`; verify the report's role reads `qa` and that its view carries exactly the keys `approvals_stale`, `review_list_size` and `rules_without_a_negative_case` @integration
- PROOF-18 (RULE-16): Give the feature `ledger` 4 own rules, one of them 600 characters long and unproved, and a required anchor holding 3 rules, with passing proofs for the other 3 own rules and all 3 anchor rules; commit a change to every scope file and run drift. Verify `rule_details` for `ledger` reads 7 total rules with `RULE-4` the only drafted one, 6 meeting the gate and the spec path `specs/ledger/ledger.md`, that its rules list holds exactly 4 entries in rule-number order, that the 600-character description comes back as 204 characters ending in an ellipsis with its opening clause intact, and that two further runs in fresh processes return byte-identical details @integration
- PROOF-19 (RULE-17): Run drift over a committed change and verify the returned string carries neither a newline followed by two spaces nor a colon followed by a space, that it parses back to an object carrying every key, and that its length is strictly less than the same object re-serialized with an indent of 2 @integration
- PROOF-20 (RULE-10): Run the pin check for an anchor naming a source and no pin at all and verify the status reads `unpinned` with no remote sha; run it for one whose source is a local path that is not a repository and verify the status reads `error` carrying the reason git gave; run it for one whose source has not moved past its pin and verify no row is reported for it @integration
