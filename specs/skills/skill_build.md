# Feature: skill_build

> Description: What `skills/build/SKILL.md` must name. The build skill loads the rules a feature
>   is bound by, writes the code and the marked tests, and commits the changeset; this spec holds
>   the one list of the commands and files it names, and what a session does with the skill on
>   a rule the audit found weak.
> Scope: skills/build/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 25
> Highest-Proof: 56

## Rules

- RULE-21: The build skill names the commands `sync_status`, `purlin:test`, `purlin:test --all --commit`, `purlin:spec` and `purlin:audit <feature> RULE-N --settle`, and the files `scripts/purlin_python.sh`, `scripts/mcp/purlin/markers.py`, `scripts/mcp/purlin/wording.py`, `references/commit_conventions.md` and `references/review_criteria.md`
- RULE-22: The build skill says how it settles a proof whose test it left alone because the test already asserts what the proof names: with `purlin:audit <feature> RULE-N --settle --sound PROOF-N`, and only for a test it read against its proof
- RULE-23: The build skill says how the test of an AI proof is written: with the helper the run names in `PURLIN_AI`, one output per test, `grade` for a graded proof, passing or skipping with `PURLIN_AI` not set, and `purlin:test --all` run once it is written, as the test skill says
- RULE-24: Given a rule the audit found `weak` through a planted bug that got past a proof's test, a session with the build skill strengthens that test, settles the rule, and changes no spec
- RULE-25: Given a `weak` rule whose proof names too little to write the check from, a session with the build skill changes no test, no code and no spec for it: it says the proof names too little, proposes a sharper proof sentence, and names `purlin:spec`

## Proof

- PROOF-51 (RULE-21): The text of `skills/build/SKILL.md` holds each of `sync_status`, `purlin:test`, `purlin:test --all --commit`, `purlin:spec`, `purlin:audit <feature> RULE-N --settle`, `scripts/purlin_python.sh`, `scripts/mcp/purlin/markers.py`, `scripts/mcp/purlin/wording.py`, `references/commit_conventions.md` and `references/review_criteria.md`; none is missing
- PROOF-52 (RULE-22): The text of `skills/build/SKILL.md` under the heading `Strengthening a weak rule` holds `purlin:audit <feature> RULE-N --settle --sound PROOF-N` and `Never pass it for a test you did not read against its proof`
- PROOF-53 (RULE-23): The text of `skills/build/SKILL.md` under the heading `The test of an AI proof` holds `references/purlin_commands.md`, `references/rule_examples.md`, `One test makes one output.`, ``A graded proof's test then starts `grade` and asserts it exits 0.`` and ``The test passes or skips when `PURLIN_AI` is not set``
- PROOF-54 (RULE-23): That part holds the sentence ``Run `purlin:test --all` once the test is written, as `skills/test/SKILL.md` says to run it.``
- PROOF-55 (RULE-24): On the sample lab, audited once so that `RULE-3` of `sample_intake` reads `weak` with a bug that got past the test of `PROOF-5`, a session with the plugin is given `Strengthen RULE-3 of sample_intake with purlin:build. Work only in this folder.`; of the files it changed, `tests/test_intake.py` is one and its test of `PROOF-5` holds the number `25`, none is under `specs/`, and `.purlin/evidence/local/sample_intake.json` reads `RULE-3` as `strong` with the bug of `PROOF-5` as `caught` @ai(claude-opus-5-5)
- PROOF-56 (RULE-25): On the sample lab whose `PROOF-5` of `sample_intake` reads `A sample received the day after it was collected has its age in whole hours`, audited once so that `RULE-3` reads `weak`, a session with the plugin is given `Strengthen RULE-3 of sample_intake with purlin:build. Work only in this folder.`; it changes no file under `specs/`, `tests/` or `src/`, and its reply says that `PROOF-5` names too little to write the check from, proposes a sharper sentence for `PROOF-5` that names a collection time, a receipt time and the age in hours, and names `purlin:spec` as the command to change the proof with @ai(claude-opus-5-5) @graded(claude-haiku-4-5-20251001)
