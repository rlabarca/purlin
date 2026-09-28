# Feature: drift

> Description: What moved since the evidence was last written. Drift reads
>   git for the commits and the changed files, classifies each file against
>   the specs' scope lines, checks every anchor pin against its source, and
>   adds what the payload already knows about the cells and the signatures.
>   Three role views come out of the same data, because a PM, QA and an
>   engineer ask different questions of it.
> Scope: scripts/mcp/purlin/drift.py
> Stack: python/stdlib, json, re, subprocess (list-only)

## Rules

- RULE-1: A `since` argument is accepted only as a commit count of digits or a `YYYY-MM-DD` date; any other value is refused with the error `rejected since` and a reason naming both accepted forms, and no subprocess starts [bar: strong]
- RULE-2: With no argument the anchor is the last commit touching `.purlin/evidence/`, then the most recent tag, then the commit that added `.purlin/config.json`; a project with no evidence history and 30 commits or more gets a `spec-from-code` recommendation instead of a diff of everything [bar: strong]
- RULE-3: Every changed file is classified exactly once, as one of CHANGED_SPECS, TESTS_CHANGED, CHANGED_BEHAVIOR, NO_IMPACT or NEW_BEHAVIOR [bar: strong]
- RULE-4: A changed file under `skills/`, `agents/` or `.claude/agents/` that no spec scopes is NEW_BEHAVIOR and never NO_IMPACT: those directories hold behaviour even though the files are markdown [bar: strong]
- RULE-5: A `> Scope:` entry ending in `/` matches every file under that directory [bar: strong]
- RULE-6: Every changed file's line count is read from a single numbered-stat diff taken over the whole range, so the number of git calls does not grow with the number of files [bar: strong]
- RULE-7: The report carries `since`, `commits`, `files`, `spec_changes`, `broken_scopes`, `pins`, `rule_details`, `summary`, `review_list` and `roles` [bar: strong]
- RULE-8: `broken_scopes` names every spec whose `> Scope:` points at a path that is no longer on disk, and the paths that are gone [bar: strong]
- RULE-9: `spec_changes` names, per changed spec, the rule ids the range added and the rule ids it removed [bar: strong]
- RULE-10: A pinned anchor whose source has moved past the pin is reported `behind` with the remote's short sha; an anchor naming a source and no pin is `unpinned`; a source that cannot be read is `error` with the reason; an anchor still at its pin is not reported at all [bar: strong]
- RULE-11: A `> Source:` value is refused before any process starts when it begins with `-`, names an `ext::` or an `fd::` transport, or carries a NUL byte or a newline, and the refusal names which of those it was [bar: strong]
- RULE-12: One remote listing per source per run: an anchor repository serving six anchors is reached once [bar: strong]
- RULE-13: A pin row names the anchor's own spec name, never the repository path and never the file inside it [bar: strong]
- RULE-14: The three role views `pm`, `qa` and `eng` are present on every report, each carrying its own keys: pins behind for the PM; signatures stale, the length of the review list, the length of the sign list, the rules with a manual test, the rules reading `unsettled` and the rules reading `not audited` for QA; files touched, rules affected, tests missing, pins behind and the rules whose evidence is out of date for the engineer [bar: strong]
- RULE-15: A role argument narrows the answer to `since`, `role`, `view` and `commits`, and nothing else [bar: strong]
- RULE-16: `rule_details` carries, per spec with a changed scope file, the spec path, the changed files, the total rule count, how many meet the gate, the ids whose spec status is `drafted` and the rules in rule-number order, each description cut to 200 characters on a word boundary and suffixed with an ellipsis when cut [bar: strong]
- RULE-17: The report is serialized with no indentation and no space after a separator, because its only reader is a model paying by the token [bar: strong]

## Proof

- PROOF-1 (RULE-1): Drift is asked for the changes since `--output=/tmp/x`; the answer is the error `rejected since`, its reason names both accepted forms, digits only and a `YYYY-MM-DD` date, and no command was run against the repository. Asked for the changes since `2` instead, the same project answers with a list of commits
- PROOF-2 (RULE-1): Drift is asked for the changes since `--output=/tmp/x` in a project; the report reads the error `rejected since`
- PROOF-3 (RULE-2): Drift is asked for the changes with no starting point, in three projects. In one whose latest evidence was committed last, it starts at that commit and describes it as `last evidence`. In one with no evidence, tagged `v1.0.0` one commit back, it starts at `v1.0.0`. In one with neither, set up by `purlin:init` 2 commits back, it starts at the setup commit and reads `since purlin:init (2 commits)`; 30 commits later it gives no range and recommends `spec-from-code` instead
- PROOF-4 (RULE-3): One commit changes a spec, a test file, a source file that spec covers, `README.md` and a source file no spec covers; the report files them as `CHANGED_SPECS`, `TESTS_CHANGED`, `CHANGED_BEHAVIOR`, `NO_IMPACT` and `NEW_BEHAVIOR`, one category each
- PROOF-5 (RULE-4): One commit adds `skills/build/SKILL.md`, `agents/reviewer.md` and `.claude/agents/helper.md`, which no spec covers; the report files all 3 as `NEW_BEHAVIOR` and none as `NO_IMPACT`
- PROOF-6 (RULE-5): A spec covers the folder `src/api/`, and a commit changes `src/api/login.js`; the report files that file as `CHANGED_BEHAVIOR` under that spec
- PROOF-7 (RULE-6): One commit adds 12 files of different lengths; the report gives each of the 12 its lines added and removed in the form `+N -M`, each equal to what git reports for that file on its own, and git was asked for line counts once, not 12 times
- PROOF-8 (RULE-7): After one committed change, the report carries exactly the 10 keys `since`, `commits`, `files`, `spec_changes`, `broken_scopes`, `pins`, `rule_details`, `summary`, `review_list` and `roles`
- PROOF-9 (RULE-8): A spec covers `src/thing.py` and `src/gone.py`, and `src/gone.py` is not on disk; `broken_scopes` holds exactly one entry, naming that spec and the missing path `src/gone.py`
- PROOF-10 (RULE-9): A committed change adds `RULE-2` to an anchor; `spec_changes` holds exactly one entry for that anchor, and its added rules include `RULE-2`
- PROOF-11 (RULE-10): An anchor is pinned to its source's first commit, and the source then gains a second commit; `pins` holds exactly one row for that anchor reading `behind`, with a `remote_sha` of 7 characters that is the start of the new commit's sha
- PROOF-12 (RULE-10): An anchor that carries rules of its own is pinned to its source's first commit, and the source then gains a second commit; exactly 1 row for that anchor reads `behind`
- PROOF-13 (RULE-11): The anchor sources `--upload-pack=/bin/echo`, `ext::sh -c id` and `fd::7` are each refused, with the reasons `begins with "-"`, `names an ext:: transport` and `names an fd:: transport`; `https://github.com/acme/p.git` is accepted with no reason
- PROOF-14 (RULE-12): The same pinned source is checked 3 times in one run; the remote is listed once
- PROOF-15 (RULE-13): The anchor `local_security`, copied from the file `constraints.md` in another repository, falls behind its source; the row reading `behind` names `local_security`, and names neither that repository's path nor `constraints.md`
- PROOF-16 (RULE-14): A commit changes `src/login.py`, which the spec `login` covers; the report's roles are exactly `eng`, `pm` and `qa`, the engineer's files touched include `src/login.py`, and its missing tests read exactly `login/RULE-1` and `login/RULE-2`
- PROOF-17 (RULE-15): Drift is asked for the `qa` view; the answer's role reads `qa` and its view carries exactly `manual`, `not_audited`, `review_list_size`, `sign_list_size`, `signatures_stale` and `unsettled`
- PROOF-18 (RULE-16): The feature `ledger` has 4 rules of its own, one of them 600 characters long and named by no proof, and requires an anchor of 3 rules; the other 3 own rules and all 3 anchor rules pass, and a commit changes every file the features cover. The `ledger` entry of `rule_details` reads 7 rules in total, 6 meeting the gate, `RULE-4` the only rule no proof names, and the spec path `specs/ledger/ledger.md`; it lists exactly its own 4 rules in rule-number order, the 600-character rule comes back as its first 200 characters followed by ` ...`, 204 characters in all, and two further runs in fresh processes give byte-identical details
- PROOF-19 (RULE-17): After one committed change, the report text holds no line break followed by two spaces and no colon followed by a space, reads back as a report carrying `since`, `commits`, `files`, `spec_changes`, `pins`, `rule_details` and `roles`, and is shorter than the same report laid out with an indent of 2
- PROOF-20 (RULE-10): An anchor that names a source and no pin reads `unpinned` with no remote sha; one whose source is a path where no repository exists reads `error` with a reason; one whose source has not moved past its pin gets no row at all
