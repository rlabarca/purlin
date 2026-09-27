# Lane 14A: tags, trust, the free hook, the signature's lock, the audit's judgment

Plan: `dev/plans/three-levels.md` (in full; decision 31 is yours and overrides 26, 27, 29
and 30 where they disagree). Rules: `dev/plans/lanes/tl-_rules.md` (in full). Worktree
`/Users/richlabarca/LocalCode/purlin-wt/14A`, branch `lane/14A` off `lane/14`. **Do not push.
Do not open a pull request.** Lane 14B does the docs, skills, board words and slides in
parallel; you own code, tests, specs, formats, fixtures, and the words in references.

## What you own, by decision 31's bullets

1. **Local counts at every gate.** `records.counts_under` returns true for `local` and
   `ci` at every gate; `states.py` reads the newest counting record for the strong cell at
   `signed` too; the "preview" line in `purlin_run.py` goes. Fixtures: regulated's team-like
   local cases follow; `tl-_rules.md` items 9 and 10 follow.
2. **The pre-push hook is removed.** Delete `scripts/hooks/pre-push.sh`, the shim
   `scaffold.py` writes, the `pre_push` config key (`gate.py` `RETIRED_KEYS` gains it),
   `dev/test_pre_push_hook.py`, `specs/hooks/pre_push_hook.md` (and its rules elsewhere),
   the hook paragraph in `hard_gates.md`; `update.py` removes an installed hook with one
   line saying why. The agent-push rule stays as text in `agents/purlin.md`.
3. **The tag.** `sign.py`: with no arguments print `Review: <n> rules. Sign: <n> rules.`,
   walk Review then Sign, and when `gate_check`'s check passes over every rule write the
   annotated tag `signed/<version>` (`VERSION` file at the project root, else the config's
   `version`; `--release <name>` overrides) with a message naming the commit and the gate;
   refuse when the tag exists; print `Run: git push origin signed/<version>`. No tag while
   any rule does not meet the gate. Delete `--tag` from the audit, `tag_record`,
   `record/` in `records.py`, and the retired words join the guard (`record/`, `--tag`).
4. **CI on tags and run branches only.** `templates/purlin.yml` and the Azure template:
   `on: push: tags: ['signed/**']` and `branches: ['run/**']`; the job is `purlin`; steps:
   checkout, set up, `purlin_run.py --all --ci` (tests only, no breaks, and on a tag run
   no records written: it verifies), then `gate_check.py --check --verify`. The `--verify`
   mode: for every committed record, brief and signature, recompute the hashes against the
   tagged code and fail on a mismatch; for every `ci/` record and brief, read the commit that
   added it and require the runner's own identity (host-signed, committer the host's noreply
   address), else the file does not count. No comment posting, no artifact upload (delete
   `ci.post_pr_comment`, `publish_dashboard` and their tests); `--ci` on a run branch writes
   the `ci/` records and briefs as today. `scaffold.py` prints no branch rules; `update.py`
   rewrites an old workflow (triggers, job name, the gate step) and names it in its table.
5. **Trust.** `scaffold.py` asks `Do you trust your own machine for the tests and the
   signing? [y/n]` (default y); config `trust: local | remote`; `gate.py` carries it;
   `sign.py` under `remote` refuses a rule whose passed cell has no `ci` platform entry for
   HEAD with `sign: <feature> RULE-N has no ci test run for this commit; run purlin:test
   --remote first`; `--update` re-asks. `templates/config.json` gains the key.
6. **The signature locks the audit.** `signatures.py`: the hash set gains `audit_hash`, the
   sha256 over the brief's `strength`, `observations` (sorted) and `settled`, or the empty
   string when no brief exists; `is_current` compares it; `sign.py` writes it;
   `signature_format.md` bumps with the field and the sentence that a changed finding stales.
   Fixtures: one regulated signature stale on `audit_hash` alone.
7. **The free checks fold into the audit.** `checks.py`'s finding names leave every
   surface: no `findings` list in the payload's proofs or cells, no finding names in the
   brief's rendered text, in `status.py`, `scan.py`, the glossary or the references. The
   scans become `hints` inside `brief.py`, handed to the model prompt as plain sentences
   ("no proof of this rule names a failure or an edge case"); the model writes what it
   observed; a settled audit with observations reads `weak` with the sentence as the reason
   (already so). `ready` = at least one proof line, nothing more (`checks.blocks_ready`
   goes). `payload.py` schema 8. `review_criteria.md` loses "the free checks" as a section
   and gains "the hints the audit reads".
8. **A hold wins** in both cells (`states.py`), `tl-_rules.md` items 2 and 4 follow.
9. **`remote.py`** looks the run up by branch (`gh run list --branch <run branch> --json
   databaseId --limit 1`, retried up to 60 s) then `gh run watch <id> --exit-status`.
10. **`purlin:spec`** (`skills/spec/SKILL.md` and whatever emits the tag): no bar tag at
    `passed`; the gate's bar at `strong` and above.
11. **Dead constants** deleted: `checks.FINDINGS`, `specs.ORIGINS`, `results.RESULTS`,
    `states.SIGN_WORDS`, `records.BRIEFS_PATHSPEC`, `records.CI_RECORDS_PATHSPEC`,
    `records.CI_BRIEFS_PATHSPEC`, `update.RECORD_FLAG_WAS`, `update.RECORD_SOURCE_WAS`.
12. The job name `purlin`; `scan.py` and `status.py` say `Review list` and `Sign list`.

Tests and specs follow every item; keep every marker aligned; `dev/test_init_e2e.sh` walks
the three gates with a tag at the end and no hook; a new `dev/test_tag.py` for the tag and
the verify mode. `references/`: `glossary.md` (tag, trust, the lock, no free-check names),
`hard_gates.md` (rewritten: the gate is checked on the tag), `purlin_commands.md`,
`commit_conventions.md` (`sign(release): <name>` for the tag), `signature_format.md`,
`record_format.md` (no `record/` tag), `drift_criteria.md`.

## Acceptance

```
pytest dev/test_signatures.py dev/test_holds.py dev/test_gate_check.py dev/test_brief.py dev/test_mcp_server.py dev/test_init_scaffold.py dev/test_init_update.py dev/test_run_script.py dev/test_records.py dev/test_scan.py dev/test_tag.py dev/test_skills.py dev/test_vocabulary.py
bash dev/test_init_e2e.sh
bash dev/run_tests.sh --fast
```

Report in the DONE shape of `tl-_rules.md`, with the spec maxima, the test delta, the exact
text of init's trust question and of `purlin:sign`'s opening and closing lines, the payload
keys that changed, decisions, and anything undone.
