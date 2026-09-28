# Purlin 0.10.0: three levels

One ladder of seven states becomes a spec status plus three evidence levels, three commands
carry the three levels, and the gate level is the only thing that decides how much of the chain
anyone sees. Written 2026-09-16 from a full scan of the code, the dashboard, the skills, the
references, the docs, this repository's own specs, tests, signatures and records, then settled
with the user question by question. This file is the design and the plan. Lane briefs go in
`dev/plans/lanes/tl-*.md`, written by the orchestrator from Part C. Nothing in this plan is
left to a lane's judgment except wording.

0.10.0 was never released. This work ships as 0.10.0: `VERSION` stays, no bump, and the
0.10.0 entry in `RELEASE_NOTES.md` is overwritten as the phases land.

## Decisions (all made by the user; no lane reopens any)

1. **Three levels, three gate values, three commands.** `passed` / `strong` / `signed`. The gate
   value is the word the cell reads when the level is met. `purlin:test` runs level 1,
   `purlin:audit` runs level 2 and writes the record, `purlin:sign` is level 3 and walks the
   review list when given no rule. `purlin:verify`, `purlin:review` and `purlin:approve` are
   gone, not aliased. Twelve skills.
2. **Level 2 is fully automatic.** A person first appears at level 3.
3. **Spec status is Drafted or Ready.** Ready means the proof text clears the blocking free
   checks.
4. **The brief reports, it recommends nothing.** Strength beside the minimum, the free-check
   findings, what the model review observed, and whether it could settle the question. The four
   verdict words are retired.
5. **A local pass meets level 1.** Under `strong` and `signed` only a CI record counts; a local
   `purlin:audit` there is a preview that says it does not count.
6. **Under `passed`, `purlin:audit` runs the tests only** and the record carries strength
   `n/a`. Raising the gate to `strong` turns the breaks on, locally and in CI.
7. **Under `signed`, a signature is required at or above `sign_at`, default `medium`.** Low risk
   meets the `signed` gate at strong. `sign_at: low` signs everything.
8. **CI writes no signature file, ever.** The `.ci.json` auto-approval is gone. Signature
   directories hold only files a person wrote.
9. **Briefs live in `.purlin/briefs/<feature>/`** beside the records, committed by CI. The CI-only
   branch ruleset covers `.purlin/records/**` and `.purlin/briefs/**`.
10. **The old approval files, CI files and briefs are dropped, not migrated.** This checkout's 37
    `.approvals/` directories and its `.purlin/records/` are deleted by hand in Phase 7. The
    0.9.5 → 0.10.0 migration in `update.py` lands a project straight on the new layout; there is
    no migration from the intermediate layout and no test for one. The user re-signs afterwards.
11. **Rule text is rewritten freely** wherever the model changes what a rule claims.
12. **A `@manual` proof, or a model review that could not settle, reads `needs a person`**, and a
    signature file from anyone clears it under `strong`; under `signed` the signer rules apply.
13. **The review list carries only what needs a person**: unsigned, stale, held, needs a person.
    A weak rule is build work and stays on the board.
14. **Tiles**: `Untested`, `Failing`, `Passed`; `Strong` at `strong`; `Signed` and a `Stale` flag
    card at `signed`. **Columns**: `Spec`, `Rules`, `Spec status`, `Tests`, `Last run`; `Strength`
    and `Strong` at `strong`; `Signed` at `signed`.
15. **Retired outright, any casing, whole word**: `tested`, `recorded`, `approved`, `approve`,
    `approval`, `approver`, `approvers`, `verified`, `verdict`, `Reviewed`, `re-verify`, plus the
    phrases `Proof ready`, `lowest state`, `seven states`, `auto-approval`, `review queue`. Plain
    English uses are rewritten too. `verify` as a verb stays legal; the names `purlin:verify`,
    `verify_gate`, `verify-gate:` are retired. `Stale` survives only as `signature stale` and the
    adjective. `record` and `review list` survive. **`audit` is un-retired**: it leaves the
    glossary's retired table and `dev/test_vocabulary.py`'s word list, and means one thing, the
    level 2 run: an audit proves a rule strong or weak. The old `purlin:audit`'s grading scores
    (gauge, Proof Design, Proof Integrity) stay retired.
16. **`scripts/ci/verify_gate.py` becomes `scripts/ci/gate_check.py`**, log prefix `gate:`, spec
    `specs/ci/gate_check.md`, JSON key `result` instead of `verdict`. `purlin:audit --tag`
    writes `record/<name>` tags.
17. **The docs page `review-and-approval.md` becomes `review-and-signing.md`.**
18. **In scope as extras**: delete `dev/screenshots/`; update `design/components` StatusPill and
    cards to the cell words; restate `dev/plans/TODO-0.10.0.md` and `held-rules-0.10.0.md` in the
    new words after Phase 7; overwrite the `RELEASE_NOTES.md` 0.10.0 entry.
19. **Execution**: one Opus orchestrator, unattended through Phase 7, one subagent per lane in
    its own worktree. Opus for every lane except the two word-swap lanes (5C, 6B), which run on
    Sonnet.
20. **`states.py` keeps its name** and so does the `states` spec; its subject is "the spec status
    and the three evidence levels of a rule". `approvals.py` → `signatures.py`, `approve.py` →
    `sign.py`.
21. **Risk stays inside the signature's hash set.** A risk re-tag stales a signature.
22. **Format versions bump as `CLAUDE.md` says**: record 1 → 2, approval 2 → signature 3, payload
    schema 4 → 5, drift criteria 3 → 4. Spec, proofs and anchor formats change wording only.

23. **`needs a person` is retired** (added 2026-09-17). It stood for two things, and each
    now names the work a person has to do. A rule whose proofs are `@manual` reads
    `manual test` in its strong cell: a person runs the test. A rule whose model review could
    not settle, or that has no brief where its risk asks for one, reads `manual audit`: a
    person judges the proof against the test. A held rule reads `held` there too. The review
    list is the one place a person is needed, and its header keeps the sentence `<n> rules
    need a person`. The `why` tokens are `unsigned`, `stale`, `held`, `manual test`,
    `manual audit`. Lane 7B.
24. **The Board tab leads with tests passing** (added 2026-09-17). Its headline is
    `<passing> of <rules> rules pass their tests · <failing> failing · <untested> untested`,
    where passing means the passed cell is met, with `<met> of <rules> meet the gate <gate>` as
    a second, secondary line. The tiles read cumulative levels: `Untested`, `Failing`,
    `Passing`, then `Strong` (strong cell met, signed rules included), then `Signed` and the
    `Stale` flag card. The group band reads `<name> · <n> specs · <passing> of <rules> pass`.
    The gate and the signed layer stay in their own columns. Lane 7A.
25. **Nothing pushes on its own except `purlin:audit --remote`** (added 2026-09-17). A local
    `purlin:audit --commit` commits the record and prints `Run: git push`; it never pushes.
    `--remote` keeps its push, because the remote runner is the point of it. CI's record commit
    through the git host's API stays: it is the remote runner writing its own evidence, not a
    push from a person's machine. `purlin:sign` and `--tag` already push nothing. Lane 7B.
26. **CI runs where evidence is decided, and enforces the gate** (added 2026-09-26). The
    workflow triggers on pull requests, on pushes to the protected branch, and on pushes to
    `run/*` branches; a push to any other branch starts nothing. A pull request run tests,
    posts the comment and uploads the dashboard, and commits nothing. A run on the protected
    branch, or on a `run/*` branch, writes the records and briefs and commits them there. Every
    run ends with `scripts/ci/gate_check.py --check`, and the job fails when the gate is not
    met, so the required check means the gate held. At `passed` init writes no workflow unless
    `--ci` asks for one (scaffold RULE-13 stands); at `strong` and above it always does.
27. **A push is a person's act, and git enforces it** (added 2026-09-26). Vocabulary: a
    **push** is `git push` typed by a person; a **remote run** is `purlin:audit --remote`,
    the one case in which Purlin pushes, to a **run branch** `run/<branch>-<sha7>` it creates,
    waits on, pulls the records back from, and deletes. No skill, lane, agent or hook pushes
    anything else, and none opens a pull request; `purlin:drift` is how a person reads what a
    pull request changed against the local tree. The pre-push hook refuses a push from an
    agent session (`CLAUDE_CODE_SESSION_ID` set) unless `PURLIN_REMOTE_RUN=1` marks a remote
    run, and prints that a person runs `git push`. Lanes 8A (code) and 8B (docs).
28. **The `passed` workflow is spec, build, test** (added 2026-09-26). Settled with the user
    question by question:
    - `purlin:test` runs the tagged tests and writes the **test results**: one
      `.purlin/tests/<feature>.json` per feature (commit, time, operating system, each rule's
      word, each proof's result and test) and one `.purlin/tests.md` table for reading on the
      git host (feature, rules, passed, failing, no test, last run). It commits them itself as
      `purlin: tests at <sha7>` and never pushes. At every gate. They are the `local` source,
      the board reads them, and they count only at `passed`.
    - `purlin:audit` measures how good the tests are: the breaks, the free checks, the model
      review. It prints strength, findings and observations and writes no record. `--commit`
      is gone; the developer record and the source `developer` are gone. Sources are `local`
      and `ci`. Run at any gate; it never counts locally.
    - The **record** is CI's. The CI job runs `purlin:test`, then at `strong` and above
      `purlin:audit`, and writes the records and briefs on the protected branch or a run
      branch. At `passed` a runner runs `purlin:test`, comments on the pull request, goes red
      on a failed or missing test, and commits nothing.
    - A **remote run** is `purlin:test --remote` (the runner runs the tests; at `strong` and
      above it also audits, and its record counts); `purlin:audit --remote` is gone.
    - A remote runner is explained in three plain reasons and no others: your tests need
      another operating system; proof from a clean machine that ran exactly the pushed code;
      no merge while red. Teammates see results without one, from the committed test results.
      `purlin:init` explains, then asks, at `passed`; at `strong` and above it always writes
      the workflow. Before writing it init checks the prerequisites: a remote exists, the host
      is GitHub or Azure DevOps, the protected branch exists on the remote, the host CLI (`gh`
      or `az`) is reported as present or absent; a missing prerequisite is named and init
      stops there. When `purlin:test` finds a proof tagged for an operating system this
      machine is not, it prints the reason in one sentence and `Run: purlin:init` to add a
      remote runner; it changes nothing itself.
    - At `passed` a person runs no script: `purlin:test` prints the table and the line
      `gate passed: <n> of <rules>` or `gate not met: <n> of <rules>`, and exits 1 when not
      met. `gate_check.py` stays the CI step. Lanes 10A (code) and 10B (docs, skills, deck).
29. **`strong` counts any audit; only `signed` requires CI; platforms roll up** (added
    2026-09-26, settled question by question; it replaces decision 5's second sentence and
    the parts of 28 that made the record CI's alone):
    - `purlin:audit` writes the record for each feature it audited (`.purlin/records/`, the
      existing shape, `source` `local` or `ci`) and the briefs, and commits them itself as
      `purlin: record for <sha7>`; it never pushes. CI's job does the same with source `ci`.
      At `strong` any source counts. At `signed` only `ci` counts, for the tests and the
      audit both: the run on the protected branch after the merge is what a signature attaches
      to, and a local run there is a preview. Sources are `local` and `ci`, nothing else.
    - **Platforms.** A rule's passed cell carries `platforms: {<os>: {word, source, at}}`,
      one entry per operating system a counting run covered (test results and records). The
      cell reads `partial` when its tests passed on some platforms and failed or did not run
      on others, on any rule; `partial` is not met. A rule tagged for one platform that has
      not run there reads `not run`. Strength is platform independent. The signed cell
      carries `signer` and `at`.
    - **Board columns**: `Spec`, `Rules`, `Proofs`, `Tests` (`<passed> of <rules>`, then
      `· <k> partial` and `· <k> failing` when not zero), then `Strong` (`<n> of <rules> ·
      <strength>%`) at `strong` and above, then `Signed` (`<n> of <rules>`) at `signed`. No
      `Spec status`, no `Strength`, no `Last run` column. Every when, who and platform detail
      lives in hovers: the `Tests` cell's hover lists each platform with its counts, source and
      newest run age; the `Signed` cell's hover lists signers and dates; the tiles' hovers
      carry the same for the project. The rule screen keeps the full lines.
    - **Record paths split by source**: `.purlin/records/ci/<feature>/` and
      `.purlin/briefs/ci/<feature>/` are what the branch rule restricts to the CI identity;
      `.purlin/records/local/<feature>/` and `.purlin/briefs/local/<feature>/` are anyone's.
      The folder is the source; a file's own `source` field must agree or the file is ignored
      with a warning.
    - **A sixth tile and filter, `Partial`**, at every gate, counting rules whose passed cell
      reads `partial`; the bucket `partial` sits between `failing` and `passed`.
    - **The `Proofs` cell** counts every proof line and appends `· <k> without a test` in the
      warn tone when a proof has no tagged test, so a reader sees at a glance whether the
      tests match the proofs; its hover lists those proofs.
    - `purlin:audit` ends with `gate strong: <n> of <rules>` or `gate not met: ...` and exits
      1 when not met, the same shape as `purlin:test`'s line. Lanes 11A (code) and 11B (board,
      docs, slides).
30. **The bar replaces risk; Review and Sign; Signable** (added 2026-09-26, settled question
    by question):
    - **Bar.** Every rule has a bar, `passed` or `strong`: the evidence it must have before it
      can be signed. A tag on the rule, `[bar: passed]` or `[bar: strong]`; a rule with no
      tag takes the project's gate as its bar (`passed` at `passed`; `strong` at `strong`
      and `signed`).
    - **Risk is retired.** The bar decides what risk used to: the evidence a rule needs,
      whether the AI audit runs on it, whether it needs a signature. `ai_review_at` goes
      away. Lists group by bar. Migration: `[risk: high]` and `[risk: medium]` become
      `[bar: strong]`, `[risk: low]` becomes `[bar: passed]`, in this repository's specs and
      in a consumer's through `purlin:init --update`.
    - **The AI audit** runs on every rule whose bar is `strong`, none other.
    - **Two words replace `manual audit`**: `not audited` (bar `strong`, no brief for this
      code yet; waits for `purlin:audit`; on no tab) and `unsettled` (the AI audit ran and
      could not settle; a person judges). `manual test` and `held` stay.
    - **Cleared its bar**: bar `passed` and the passed cell met, or bar `strong` and the
      strong cell met.
    - **`sign_at`** is `strong` or `all`, set by init at the `signed` gate (one sentence each,
      then the question; `--update` re-asks). A rule needs a signature when the gate is
      `signed` and `sign_at` is `all` or its bar is `strong`. `not required` is retired.
    - **Signable**: a rule that has cleared its bar. The board's `Signable` column, left of
      `Signed` at `signed`, counts them signed or not; the `Sign` tab lists the signable
      rules without a counting signature. A rule meets the gate `signed` when it has cleared
      its bar and, if it needs a signature, its signed cell reads `signed`.
    - **Two tabs.** `Review` at `strong` and above: `manual test`, `unsettled`, `held`. `Sign`
      at `signed`. `purlin:sign` walks Review, then Sign. Lanes 12A (code) and 12B (board,
      docs, slides).







31. **Tags are the marker; push is free; local counts everywhere; the signature locks the
    audit too** (added 2026-09-27, settled question by question after the closing review):
    - **Local counts at every gate**, `signed` included. The strong cell reads the newest
      audit, yours or CI's. Decision 29's "only `ci` at `signed`" is withdrawn.
    - **The pre-push hook is removed.** A push is free, for anyone, to any branch. Nothing
      runs at push time. (Decision 27's guard goes with it; the rule that an agent never
      pushes stays an instruction in `agents/purlin.md`.)
    - **The tag is the marker of proven code.** `purlin:sign` with no arguments prints
      `Review: <n> rules. Sign: <n> rules.`, walks Review then Sign, and when every rule meets
      the gate writes the annotated tag `signed/<version>` (the `VERSION` file's value;
      `--release <name>` overrides). No tag while any rule does not meet the gate. A person
      pushes the tag. `purlin:audit --tag` and `record/<name>` are retired.
    - **CI runs on a tag push and on a remote run's `run/*` branch, nowhere else.** No pull
      request run, no run on the protected branch. The tag run runs the tagged tests on a
      clean machine, verifies every committed record, brief and signature against the tagged
      code (hashes), checks the provenance of every `ci/` record and brief (the commit that
      added it is the runner's own, signed by the host), and ends with the gate check; the
      job is named `purlin`. No breaks on CI. Branch rules: none. Init prints none.
    - **Trust**, set by init: `Do you trust your own machine for the tests and the signing?
      [y/n]`, config key `trust: local | remote`, default `local`. Under `local`: sign, tag,
      push. Under `remote`: `purlin:sign` refuses to sign a rule whose tests have no `ci`
      record for this commit, so `purlin:test --remote` runs first; the tag run verifies as
      above. `purlin:init --update` re-asks.
    - **The signature locks rule, proof, test, bar and the audit's findings**: the hash set
      gains the brief's evidence (strength, the audit's observations, settled). A re-audit
      that observes something different stales the signature; timestamps and commit ids are
      not hashed. `signature_format.md` bumps.
    - **The free checks fold into the audit.** Their names (`happy_path_only` and the rest)
      leave every surface, the glossary and the docs. The scans run as hints handed to the AI
      audit, which writes what it observed in plain sentences; a settled audit that observed a
      gap reads `weak` with that sentence as the reason, so the audit's judgment carries the
      hints. `ready` means the rule has a proof, nothing more.
    - **A hold wins**: a held rule reads `held` in both cells whatever its tests do.
    - **`purlin:test --remote`** finds its run by branch (`gh run list --branch`, retried
      while the run registers) and then watches it.
    - **`purlin:spec` writes no bar tag at `passed`**; at `strong` and above it writes the
      gate's bar and the person changes the exceptions.
    - Words: `list` for what `purlin:sign` walks (the Review list, the Sign list), `tab` only
      for the dashboard. The nine unread module constants the review named are deleted.
      Lanes 14A (code), 14B (docs, skills, board words, slides), 15 (the second docs review).
    - **A remote runner exists for two reasons and no other** (amended the same day): a
      proof tagged `@env` for an operating system this machine is not, or `trust: remote`.
      A trusted project with no `@env` tags has no workflow: the tag is the signer's word.
      Where a runner exists, it runs on `run/**` branches and `signed/**` tags, and the tag
      run reruns the tests, verifies hashes and provenance, and runs the gate check. Init
      explains the two reasons and asks nothing else; "no merge while red" is gone.
    - **The bare workflow is the story.** Every page, diagram and slide shows spec, build,
      test, audit, sign, tag, on one machine; a full `signed` gate on a laptop with no CI is
      the normal case. Remote runners appear only where the two cases are described, in one
      short section per page at most and on one page of their own.
    - **The counts line in `RELEASE_NOTES.md` and `purlin_version` RULE-9 are dropped** (added
      the same day): the sweep writes its record and nothing compares the notes against it.
32. **Signing is recorded, not policed** (added 2026-09-27, settled question by question from
    lane 15's Q1, Q2, Q3 and Q5). Purlin's job is a provable, traceable log of where the tests
    ran and who signed that rule, proof, test, bar and audit match. It does not decide who may.
    - **The signer list is removed.** No `signers` key, no question for emails in init, no
      `signer list missing` line, no refusal in `purlin:sign`. `purlin:init --update` drops
      the key from an existing config and prints one line saying so. A config that still
      carries it is read without a warning and the key is ignored.
    - **The self-signing check is removed.** A signature counts whoever last touched the
      test, and nothing is shown about it; git names both authors.
    - **The protected branch is removed.** A signature counts on whatever commit carries it;
      `is_ancestor` and its call go, and so does the branch leg of init's prerequisites. Init
      checks that a remote exists and that the host is GitHub or Azure DevOps, reports the
      host CLI, and nothing else.
    - **A signature counts at `signed` when two things hold**: the commit that added it is
      cryptographically signed and verifies, and its bound hashes still match the rule, the
      proof, the test, the bar and what the audit found. Below `signed` a committed signature
      counts, as before.
    - **`purlin:sign <feature>` and `purlin:sign --batch` at `strong`** sign every rule on
      the Review list, for that feature or for the project. The line `a signature is
      required only under the gate signed. Writing it anyway.` goes for those rules.
    - **What `signed/<version>` means, formally**: at the tagged commit, every rule meets the
      gate, which is: it has cleared its bar, and if it needs a signature it has a counting
      one. A rule that needs no signature (bar `passed` under `sign_at: strong`) meets the
      gate on its tests and does not hold the tag back. `trust: remote` binds signing alone,
      as decision 31 wrote it: it is read when a rule is signed and by no cell and not by the
      tag. The definition lives in `references/glossary.md` and `references/hard_gates.md`;
      every other page points there.
    - `signature_format.md` bumps.
33. **The free scans are removed; drift reports facts** (added 2026-09-27, from lane 15's Q4
    and Q8). A project at `passed` has said it wants no reading of test quality; at `strong`
    and above `purlin:audit` is the one place strength is judged, by the breaks and the AI
    audit.
    - `scripts/review/static_checks.py`, `scripts/mcp/purlin/checks.py`,
      `specs/review/static_checks.md`, their tests and their proof files are deleted. The
      words `free scan` and `hint` join the retired table.
    - The brief's layers are `test strength` and `AI audit`. It carries no hints; its schema
      bumps, and a brief written before this one is read with its hint fields ignored.
    - `references/review_criteria.md` stays the AI audit's prompt. What the scans looked for
      stays there as what the audit looks for, in plain sentences, with no claim that
      anything scanned first.
    - `purlin:drift` reports what changed and what is waiting, for every role, and judges
      nothing. `rules_without_a_negative_case` goes, with `specs/mcp/drift.md` RULE-14 and
      PROOF-17.
34. **Three cleanups** (added 2026-09-27, from lane 15's Q6, Q7 and Q9).
    - `is_fork()` and its call site are deleted, with `specs/run/records.md` RULE-7's fork
      half and the docs section `A run from a fork`.
    - The six unread constants: a grep of `scripts/` on 2026-09-27 finds none of them
      assigned, so this is a check that they are gone and nothing more.
    - `--quick` becomes `--test`, with no alias: the skill is the caller, and 0.10.0 has not
      shipped. `--quick` joins the retired table.

Decisions 35 to 44 are the simplification round of 2026-09-27, settled question by question
from the most basic concept up. All of it lands in 0.10.0, before the tag. The core workflow
is spec, build, test, audit, sign, tag; whatever is not core to it was up for questioning.

35. **The audit judges strength, by a model and optionally by mutation testing.**
    - `purlin:audit` calls the AI audit itself. Before this decision nothing in the workflow
      did: every brief was built with the model off.
    - Mutation testing is optional. `purlin:init` asks once whether to turn it on; the
      default is off. On, the score must reach `min_strength` as well. Off, or where no
      library exists for the language, the AI audit alone decides, and a rule it found
      sound is `strong` with the reason that no score was measured.
    - An audit that cannot decide is build work: the rule reads `weak` with the audit's
      reason. `unsettled` is retired.
    - A rule whose text, proof and test are unchanged since its last audit is not audited
      again; the earlier findings stand. `--all` forces a fresh audit.
    - The signature locks every sentence of the audit, as decision 31 wrote it.
    - At the gate `passed`, `purlin:audit` runs, prints and commits what it found, and
      nothing blocks on it.
36. **A rule's level uses the gate's three words.** A rule may be marked `[level: passed]`,
    `[level: strong]` or `[level: signed]`, meaning what the gate means: tests; tests and
    audit; tests, audit and signature. An unmarked rule takes the gate. The gate is the
    ceiling: a mark above it is read as the gate. `bar`, `cleared its bar`, `sign_at` and
    `required` are retired. The spec status is folded into the test status: a rule with no
    proof reads `no test` with the reason `no proof written`; `drafted`, `ready` and
    `spec status` are retired. In this repository, the rules of
    `specs/dashboard/purlin_report.md` are marked `[level: passed]`.
37. **One queue, and no holds.** `purlin:sign` walks one list of the rules that wait on a
    person, each row saying what is needed: a hand check (`@manual`) or a signature. The
    dashboard has one tab for it. `Review`, `Sign` as list names, and `signable` are retired.
    Holds are removed: a reviewer who disagrees adds the missing proof or changes the proof,
    alone or with AI help. `hold`, `held` and `--hold` are retired.
38. **A proof says less.** `@integration` and `@e2e` are removed, with the filter by kind and
    its flag; `purlin:test` runs every tagged test of the features it runs. `@manual` and
    `@env` stay as they are. `[origin: ...]` and `[criterion: ...]` are removed. The design
    tie is removed: no `designs/` convention, no design hash in a signature, no mock beside
    a screenshot.
39. **A run covers what the change touched.** `purlin:test` with no feature named runs the
    features whose spec, covered code or tests changed since that feature's last evidence,
    and prints what it skipped and why; `--all` runs everything. `> Scope:` is required:
    `purlin:spec` and `purlin:build` write and maintain it, and a spec without one is
    reported as incomplete. Evidence from a person's own run is checked against the
    fingerprint like any other. The tag is written only when every feature's evidence is
    current for the code it covers, and a feature that is not is named.
40. **One evidence file per feature.** Every run, test or audit, writes
    `.purlin/evidence/<source>/<feature>.json`: each proof's result, the commit, the
    operating system, the time, and once audited the strength and the AI audit's findings
    per rule. One format file, one commit subject. `test results`, `record` and `brief` are
    retired as names of files. `.purlin/tests.md`, the summary table, stays.
41. **The periphery is removed.** The per-person settings file; `purlin:anchor propose` and
    the weekly upstream check with `--upstream-check`; everything under `tools/`; the
    repository reader script; `purlin:find`, folded into `purlin:status <name>`;
    `purlin:rename`, folded into a paragraph of `agents/purlin.md`; every upgrade step for a
    layout that never shipped, and every reader branch that accepts an old spelling.
    `purlin:spec-from-code` stays. Anchors stay, local and remote.
42. **Drift reports by role from git.** Three views, `pm`, `eng` and `qa`, each worked out
    from the log and the diff: rules added, changed and removed; code changed and the rules
    behind it, rules with no test, anchors behind; tests changed, signatures stale, the
    size of the queue. The `design` view goes.
43. **Both git hosts, and Azure DevOps is fixed**: a remote run that waits for its result,
    and a check of who committed a file that does not rest on a name.
45. **Three roles, and a brand kit cut to what is used** (added 2026-09-27). The roles are
    PM, developer and QA; the designer is removed from every page, and
    `docs/working-together.md` loses its section on one. `purlin:init --update` removes a
    0.9.5 spec's Figma source and picture fingerprint lines, backs the file up first, and
    prints one line per spec. Under `design/`, the tokens, `styles.css`, the logo files the
    build reads and the rules page stay; `design/components/`, `design/guidelines/`,
    `design/SKILL.md` and `design/assets/logo-closing.svg` are deleted, and the rules page
    loses every section that names a path that does not exist. The wording rules move to a
    page of their own under `references/`, the one home for how Purlin writes, and the rules
    page keeps the look. Both colour themes stay. Diagrams are plain mermaid: the init block
    and `docs/_mermaid.md` go. The docs carry three screenshots taken from the rebuilt
    dashboard: the board, the queue, one rule.
46. **What the design round settled** (added 2026-09-27). `dev/plans/design-35-43.md` is the
    technical design for decisions 35 to 43, and its section 10 holds the owner's answers,
    which win over its text. The ones that amend a decision: `> Scope:` is optional below
    `signed` and required at `signed` (39); a rule whose level is `passed` is never audited
    under a higher gate (35); the level is logged in a signature and not locked (31, 36);
    the status word is `out of date` and `code changed` is retired as a word; the audit runs
    `audit_parallel` calls at once, default four (35); drift measures from the last git
    action that brought changes in (42). `dev/plans/stale-inventory.md` is the list the
    final sweep works from.
47. **Two machines** (added 2026-09-27). This machine takes 0.10.0 as far as it can: every
    piece of decisions 35 to 46, the Azure DevOps work up to what can be tested without an
    Azure project, the docs, the diagrams, the slides and the statement of what differs from
    0.9.5. The owner reviews those. The work is then pushed as a branch. The owner's work
    machine, which has Azure DevOps access, checks the branch out, runs the live Azure
    checks, audits, signs, tags and releases. Nothing is signed or tagged here, and `main`
    is not pushed from here. Amended the same day: the owner may run `purlin:audit` here for
    most of the code, so the work machine audits only the rules its own changes touch. The
    audit's evidence is committed with source `local` and travels in the branch.
48. **A signature is evidence, and it belongs to no machine** (added 2026-09-27). A
    signature is a log entry that ties back to who signed, what they signed, and on what
    machine. Nothing about a signature depends on which machine made it, and Purlin polices
    nothing about who or where. Two things stay, each the owner's choice: a signature counts
    at `signed` only in a commit that is cryptographically signed and verifies, because that
    is what makes the signer provable; and `trust: remote` stays as a project's own setting.
    New: every signature records the machine's name and its operating system beside the
    signer and the time. `signature_format.md` bumps. Piece P4 of the design owns it.
49. **This repository is brought up to its own spec** (added 2026-09-27). After the last
    piece lands, `purlin:init --update` runs here, so this project carries what a project
    set up by 0.10.0 carries: the settings file, the plugin copies, the ignore entries, the
    runner file. Because the upgrade reads only what released 0.9.5 wrote, each piece
    rewrites this repository's own files for the layout it changes, and the run of
    `--update` is the check that nothing was missed: whatever it still offers to change is
    a gap, fixed in the piece that owns it. No audit and no signing follow until the owner
    says the sanity checks are done.
50. **Purlin stays out of the way** (added 2026-09-27, from the first sanity check: a
    skeptical developer asking why they need it). This amends decisions 28, 29 and 40.
    - **Evidence is written, and committed when asked.** `purlin:test` and `purlin:audit`
      write the evidence file and print the table. `--commit` commits it, as
      `purlin: evidence at <sha7>`. Neither ever commits on its own. `purlin:sign` refuses
      to sign a rule or write the tag over evidence that is not committed, names the
      feature, and names the command that commits it. The remote runner is the one writer
      that always commits, because its evidence exists nowhere else.
    - **Nothing of Purlin runs unless Purlin was run.** The hooks that refreshed the
      dashboard's data after a tool call are removed, with `hooks/hooks.json` and the
      `digest` setting. `purlin:test`, `purlin:audit`, `purlin:sign` and `purlin:status`
      each refresh the data as they finish.
    - **A finding blocks**, as decision 35 wrote it.
    - **The audit says what it is about to do.** Before the first model call it prints one
      line, `AI audit: <n> rules to read, <k> at a time.`, and carries on without asking.
    - **Five words at `passed`.** At the gate `passed` every surface and every page a
      person meets first uses rule, test, passed, out of date and gate, and no word of a
      higher level. The rest appears when the gate is raised.
51. **A proof is QA's plan, a test is any test with one comment, and there are no plugins**
    (added 2026-09-27, from the first sanity check). Product, QA and developers all work in
    Claude Code on a checkout; `purlin:drift` is how each catches up after pulling.
    - **A guideline for a good proof**, one page, the one home for it: what is done, what is
      observed, the expected value, at least one failure case, written so a non-developer
      can judge it, with no file path and no function name. AI may draft a proof; the
      guideline is what it drafts against and what the audit checks.
    - **Proofs are optional at `passed` and required from `strong` up.** At `strong` and
      above a rule with a test and no proof reads `no proof` and does not meet the gate. A
      rule marked `[level: passed]` needs none, which is how one rule is exempted.
    - **`purlin:spec` shows the proofs and asks** whether to change any, saves the spec, and
      names `purlin:build`. It never starts building. `purlin:build` works from the proofs
      that exist, and looks first for an existing test that already shows what a proof
      asks; when it finds one it offers to add the marker and writes nothing new.
    - **The marker is a comment**, `purlin: <feature> PROOF-<n>`, in the language's own
      comment syntax on a line above the test; where a rule has no proof it names the rule,
      `purlin: <feature> RULE-<n>`. A test may carry several, one line each, and its result
      counts for each.
    - **No plugins.** Purlin runs the project's own test command, held in the settings file,
      with the report flag added, and reads the report: JUnit XML, the format `dotnet test`
      writes, the JSON `go test` writes, and for a shell or SQL script its exit code. It
      ties each result to its marker by the test's name, and reports a marker it cannot tie
      to exactly one test; it never guesses. `purlin:init` writes the command for the
      framework it detects, says what a framework needs added, and asks for the command and
      the report's path where it detects none.
    - **One suite.** A test the developer wrote and a test `purlin:build` wrote differ in
      nothing but who typed them; a test with no marker runs as always and is ignored.
    - **This repository**: every marker is rewritten, and two or three specs have their
      proofs rewritten to the guideline as the examples the docs show.
    - **Order**: after the scheduled pieces, and not before the owner has talked through the
      GxP complaints of the same sanity check.
52. **Purlin produces evidence for a regulated system; it does not make software
    compliant** (added 2026-09-27, from the first sanity check, the GxP half). A regulated
    document and sign-off system such as Veeva holds the controlled document, the authority
    to approve and the signature that counts under the regulation. Purlin sits upstream of
    it and hands it evidence. `purlin:sign` stays what it is: the formal lock on all the
    evidence together.
    - **The evidence package.** `purlin:export` produces one data file for a version,
      holding everything a reviewer needs: the version, the commit and the tag; each rule's
      words, its proofs and its tests; each result with when, where and on which operating
      system; what the audit found per rule, with the model that found it; who signed each
      rule, when and on which machine; the Purlin version that produced it; and a
      fingerprint of the package itself. Every time is UTC. The same tag always gives the
      same bytes.
    - **Any time, and it says where things stand.** Its first field says whether this
      version is fully signed and tagged, or is work in progress and not for approval.
    - **A requirement's number is a note in the rule's own words**, such as `(URS-042)` at
      the end of the sentence. Purlin does nothing with it; it reaches the package because
      the rule's words do.
    - **The audit names its model.** Every finding records the model's name and version and
      a fingerprint of the instructions it was given.
    - **The tag is signed.** `purlin:sign` writes `signed/<version>` as a cryptographically
      signed tag, with the key the signer already signs commits with.
    - **Nothing about who last changed the test** is put in the evidence.
    - **The pages say what Purlin is.** The README states its intended use in one paragraph
      and drops "the same team under GxP". `docs/regulated-workflow.md` spells out Purlin's
      role: what it produces, what it hands over, what the regulated system does, and that
      Purlin makes no claim of compliance.
53. **The docs speak to a developer who wants to be left alone** (added 2026-09-27). The
    README and the first pages a developer meets lead with how little Purlin touches: a
    settings file and the specs you write, one comment above a test, your own test command,
    nothing committed unless you ask, nothing running unless you ran it, nothing installed
    in your test suite, and markers that are comments if you leave. The ten-minute path
    (install, three rules, one comment per test, one command) is the first thing shown.
54. **The overnight run** (added 2026-09-27). The owner's standing answers for work done
    while they are away: a choice no decision covers takes the smaller option and goes on a
    list for the morning; a piece whose tests still fail after a second attempt stays on
    its own branch, unmerged, and pieces that do not build on it carry on;
    `purlin:init --update` is applied to this repository in full once the pieces are in;
    `dev/plans/` stays until the owner has reviewed the docs, the slides and the release
    notes; merged local branches, their worktrees and the leftover output folders on this
    machine are removed, nothing on the remote is, and a branch holding unmerged work is
    listed instead; the slides are published to the same private link, six of them: the
    three levels, the remote runner, how little Purlin touches, Purlin and the regulated
    system. No audit, no signing, no tag and no push.
55. **The evidence package is part of the workflow and is committed with the tag** (added
    2026-09-27; amends decision 52). `purlin:export` writes the package into the project,
    at `.purlin/evidence/package/<version>.json`. When `purlin:sign` is about to write
    `signed/<version>` it writes the package for that version, commits it, and tags that
    commit, so the tagged code carries the package that describes it. The package names the
    commit its evidence was taken at, which is the parent of the commit that carries it.
    Run at any other time, `purlin:export` writes the file, says the version is work in
    progress, and commits it only with `--commit`.
56. **Six choices from the overnight run, settled** (added 2026-09-28).
    - A hand check signed without a note is accepted, as it is.
    - At the gate `signed`, a spec that names no files fails the gate check whatever its
      rules are marked, as it is.
    - **A merge that needed conflicts resolved counts as a merge for drift.** Git logs it as
      `commit (merge)`; drift measures from before it.
    - **A marker that names a feature, a proof or a rule no spec has fails the run**, with
      the file and the line, exit 1.
    - **The tag and its package are written only at the gate `signed`.** At `strong`,
      `purlin:sign` clears hand checks and writes no tag and no package; `purlin:export`
      still produces a package at any gate, saying where things stand. No surface shows a
      tag below `signed`.
    - **The remote runner gets a diagram**, in the section of `docs/running-and-evidence.md`
      that describes the two cases. That page then holds two diagrams, one per section.
44. **A clean release.** 0.10.0 carries nothing that represents earlier functionality: no
    code, spec, test, fixture, committed evidence, workflow, plan or table of retired words.
    `RELEASE_NOTES.md` is the one place history is kept, and what an upgrade from 0.9.5
    needs is the one exception in code. This decision is applied last, as a sweep.


---

# Part A: the design

Every doc, skill, reference, message and test uses these words and no others.

## A1. Vocabulary

- **spec status**: what the spec says about a rule. **Drafted**: no proof line names it.
  **Ready**: at least one proof names it and no blocking free check fires on the proof text.
- **evidence level**: one of three questions about a rule, each answered by its own cell.
  **passed**: every tagged test for the rule passed. **strong**: the tests are worth trusting.
  **signed**: a person signed the rule, proof and test hashes.
- **cell**: the answer to one level for one rule. A cell reads one word, carries its reasons,
  and exists only at or below the project's gate. Above the gate a cell is absent, not empty.
- **gate**: the one project setting, `passed`, `strong` or `signed`. A rule **meets the gate**
  when every cell up to the gate's level is met.
- **run**: one execution of the tagged tests. **record**: the machine's evidence of one run:
  results, strength and scope tree, written by `purlin:audit`, committed by CI. Nobody signs a
  record. **source**: where a pass came from: `ci` (a record CI wrote), `developer` (a record a
  person committed), `local` (the last run in this checkout). Under `passed` every source
  counts. Under `strong` and `signed` only `ci` counts.
- **current**: a record describes the checkout when its commit is HEAD or its scope tree still
  hashes the same. A CI pass that is not current reads **code changed**, and CI clears it on the
  next run.
- **audit**: the level 2 run: the tests, then the breaks, the free checks and the model review
  where risk asks, ending in a record and, on CI, the briefs. An audit proves a rule strong or
  weak. **the breaks**: deliberate changes to the code; **test strength**: the share the tests
  caught, as a percentage. Measured only at `strong` and above.
- **brief**: the machine's report on one rule: the strength beside the minimum, the free-check
  findings on the proof text and the test body, the model review's observations, and whether it
  settled. It recommends nothing.
- **signature**: a named person's attestation that a rule, proof and test belong together, a
  committed file. **signer list**: `signers` in `.purlin/config.json`. **hold**: a person's
  committed statement that the test does not prove the proof, with the missing case.
  **note**: the one line a signer writes for a `@manual` proof or a review the model could not settle.
- **signature stale**: the signed cell's word when a signature exists and its hashes no longer
  match.
- **review list**: the rules whose next step is a person. Exists only at `strong` and above.
- **risk**: unchanged tag, default `low`. Read only at `strong` and above; never asked, shown
  or required under `passed`.
- **rollup**: rules meeting the gate out of rules total, plus one count per bucket.

## A2. The chain

For one rule, top to bottom. Each row is a cell; the gate decides how many rows exist.

| Level | Met when | Words the cell can read | Reasons it carries |
|-------|----------|-------------------------|--------------------|
| spec | proof text clears the blocking free checks | `drafted`, `ready` | the blocking finding names |
| passed | every proof has a passing test from a counting source, and a CI pass is current | `passed`, `failed`, `no test`, `not run`, `code changed` | `failing: <where>`, `<os>: no record yet`, `code changed since <commit7>`, `developer record does not count under <gate>`, `local run does not count under <gate>` |
| strong | passed from `ci`; strength at or above `min_strength`, or `n/a` with no engine and no blocking proof-text finding; no test-body finding; when risk is at or above `ai_review_at`, a brief for the current triple that observed nothing and settled; no hold | `strong`, `weak`, `needs a person` | `strength 64% under 80%`, `no engine: free checks only`, the finding names, the observation sentences, `manual proof`, `review not settled`, `held by <who>: <case>` |
| signed | a counting signature for the current hashes, when risk is at or above `sign_at`; `not required` below it | `signed`, `unsigned`, `stale`, `held`, `not required` | `by <email>`, `the signing commit is not signed`, `the signer is not on the list`, `the signer last touched the test`, `the signing commit is not on <branch>`, `hashes changed after the signature` |

A signature file for the current hashes clears `needs a person`: from anyone under `strong`,
from a counting signer under `signed`. A hold blocks both the strong and the signed cell while
it is current, and a signature by a person outranks it.

A rule's **bucket** is the one tile it is counted in: `untested` (drafted, or ready with no
test or no run), `failing`, `passed` (level 1 met, and either the gate is `passed` or level 2
is not met), `strong`, `signed`. Two flags are counted beside the buckets, never instead of
them: `stale` and `held`.

## A3. The gate

| Gate | Cells that exist | What CI requires before merge | Derived defaults |
|------|------------------|-------------------------------|------------------|
| `passed` | spec, passed | every rule's passed cell is met; any source | `min_strength` unused, `ai_review_at` never, `sign_at` n/a, tags optional, breaks off |
| `strong` | + strong | every rule's strong cell is met; only `ci` counts | `min_strength` 70, `ai_review_at` high, `sign_at` n/a, tags optional |
| `signed` | + signed | every rule's signed cell is met; signer list present | `min_strength` 80, `ai_review_at` medium, `sign_at` medium, risk and origin required |

Branch rules `purlin:init` prints: (1) require a pull request and the `purlin` check, Actions app
the only bypass; (2) restrict `.purlin/records/**` and `.purlin/briefs/**` to the Actions app;
(3) no force push, no deletion. Under `passed` only (3). Azure: the build service alone holds
Contribute on those two paths.

A signature counts when: the commit that added the file is signed and verifies; the author's
email is on `signers` as of that commit; that author did not author the last commit to the test
file; the bound hashes match; and under `signed` the commit is on the protected branch.

## A4. Commands

| Command | Purpose (the one sentence) | Writes |
|---------|----------------------------|--------|
| `purlin:test [feature]` | Run the tagged tests and print each rule's passed cell | `.purlin/runtime/proofs/` |
| `purlin:audit [feature] [--commit] [--ci] [--tag <name>] [--remote]` | Run the tests and the breaks, then write the record | `.purlin/records/<feature>/<timestamp>-<commit7>-<runner>[-<os>].json`; under `--ci` also `.purlin/briefs/<feature>/<RULE-N>.<hash8>.brief.json`; `--tag` writes `record/<name>` |
| `purlin:sign` | Walk the review list one brief at a time, signing, holding or skipping | signatures and holds, in signed commits |
| `purlin:sign <feature> [RULE-N ...]` | Sign a rule, a feature or a batch as a signed commit | `specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json` |
| `purlin:sign --batch` | Sign everything currently signable | same |
| `purlin:sign <feature> RULE-N --hold "<case>"` | Hold a rule: the test does not prove the proof | `<RULE-N>.<hash8>.<holder-slug>.hold.json` |
| `purlin:sign <feature> RULE-N --note "<text>"` | Sign a `@manual` proof's evidence, or settle what the model could not | the signature file with `note` set |
| `purlin:status` | Show every rule's cells and what blocks the gate | nothing |
| `purlin:init --gate passed\|strong\|signed` | unchanged syntax, new values | config, workflow, readmes |

`purlin:build`, `purlin:spec`, `purlin:spec-from-code`, `purlin:find`, `purlin:drift`,
`purlin:anchor`, `purlin:rename` keep their syntax. The walk's answers are human actions: sign,
add a case (a proof line the reviewer writes), hold, skip.

Commit prefixes: `sign(<feature>): RULE-N ...`, `sign(batch): <feature> RULE-N, ...`,
`hold(<feature>): RULE-N ...`, `purlin: record for <commit7>` (records and briefs only).

## A5. Skills scale with the gate

Under `passed`: `purlin:status`, `purlin:find`, `purlin:test`, `purlin:audit`, the pull
request comment and the board print no strength, no risk, no review list, no signature.
`purlin:audit` runs no breaks. `purlin:spec` does not ask for a risk tag. `purlin:sign` says
the gate is `passed` and what `purlin:init --gate strong` would add, then stops. `purlin:drift
qa` says the same.

Under `strong`: strength, the strong cell, the review list and risk appear. A local
`purlin:audit` prints its strength as a preview and says only CI's record counts.
`purlin:sign` works for the walk, `--note` and `--hold`; a bare signature says signatures are
required only under `signed`, then writes it anyway if asked.

Under `signed`: the signed cell, the signer list, the sign panel.

## A6. Surfaces

**Board** (build and test). Headline: `<met> of <rules> rules meet the gate <gate> · <failing>
failing`. Tiles per decision 14. Spec table columns: `Spec`, `Rules`, `Spec status`
(`ready · drafted`), `Tests` (`passed · failing · no test`, each count in its tone), `Last run`
(source, os, age); at `strong` add `Strength`, `Strong` (`n of m` with a bar); at `signed` add
`Signed` (`n of m`, stale count in the fail tone). No risk column, no coverage column, no state
column, no risk-by-state grid. Expanded rule rows: id, text, one pill per existing cell.
Filters: `Untested`, `Failing`; at `strong` add `Weak`; at `signed` add `Unsigned`, `Stale or
held`.

**Rule screen**: spec status, then one row per existing cell with its word and reasons, then
Proofs. At `strong` and above, the Brief panel: strength beside the minimum, the findings, the
observations, each in one sentence naming the proofs it concerns. At `signed`, the Sign panel:
`purlin:sign <feature> <RULE-N>` or `Signed by <email>`.

**Review list** (tab exists at `strong` and above). Header: `<n> rules need a person`, then the
risk summary: one line per risk with counts of unsigned, stale, held and needs-a-person. Rows
grouped by risk high first, stale and held first within a group; each row carries feature, rule
id, text, risk tag, the blocking cell's word, and its reasons.

**Status table** (`purlin:status`, the pull request comment, `scan.py`): `Feature | Rules |
Spec | Tests | Run` then `| Strength | Strong` at `strong` then `| Signed` at `signed`. Summary
line: `<met> of <rules> meet the gate <gate>`. Then one `→ Next:` line.

**Gate check** (`scripts/ci/gate_check.py --check`): sections `Not passed (n)`, `Weak (n)`,
`Not signed (n)`, each rule with its blocking reason. Log prefix `gate:`. JSON: `{gate,
min_strength, commit, rules, met, not_passed, weak, not_signed, result, exit, signer_list?}`.

---

# Part B: technical design

## B1. Payload, schema 5

`scripts/mcp/purlin/payload.py`: `SCHEMA_VERSION = 5`; `scripts/report/src/app.js`
`SCHEMA = 5`.

```
gate:     {gate, ai_review_at, sign_at, min_strength, mutation_engine, sql_engine, ci,
           signers, test_framework, pre_push}
summary:  {rules, features, met, failing, untested, passed, strong, signed,
           stale, held, needs_person}            # strong/signed absent below their gate
features[]: {name, category, spec_path, ..., rollup: {same keys as summary minus features,
           plus test_strength, latest_record}, rules: [...], signatures: [paths]}
rules[]:  {id, feature, label, text, risk, origin, criterion, rule_hash, proof_hash,
           test_hash, test_hash_kind, design_hash, proofs,
           spec: 'drafted'|'ready',
           cells: {passed: {...}, strong: {...}|absent, signed: {...}|absent},
           bucket, meets_gate, blocked_by: 'spec'|'passed'|'strong'|'signed'|null,
           flags: {failing, stale, held, needs_person, code_changed}}
review_list[]: {feature, owner, rule, risk, cell, why: [tokens]}    # [] under passed
records, warnings, commit, dirty, generated_at, generated_by, project, version
```

Cell shapes:

```
passed:   {word, source: 'ci'|'developer'|'local'|null, current: bool, counts: bool,
           missing_env: [], reasons: []}
strong:   {word, strength: int|null, findings: [], observations: [], brief: path|null,
           settled: bool|null, reasons: []}
signed:   {word, required: bool, signer: email|null, path: str|null, reasons: []}
```

Gone: `states`, `project_rollup`, `counts`, `lowest_state`, `proved`, `by_risk`,
`re_verify_pending`, `needs_review`, `flags.auto_approvable`, `flags.needs_ai_review`,
`flags.on_review_list`, `review_list[].reason`, `reasons`. `why` tokens are the closed set
`unsigned`, `stale`, `held`, `needs a person`, `manual`.

## B2. Core package `scripts/mcp/purlin/`

- `gate.py`: `GATES = ('passed', 'strong', 'signed')`; `_DERIVED` gains `sign_at` (`None`,
  `None`, `'medium'`) and `breaks` (`False`, `True`, `True`); `GateConfig` slot `signers`
  replaces `approvers`, `tags_required` is dropped; `RETIRED_KEYS` gains `approvers`; an
  unrecognised `gate` falls back to `passed` with the existing warning shape.
- `states.py`: rewrite. `rule_cells(inp, cfg)` returns `{spec, cells, bucket, meets_gate,
  blocked_by, flags}`; `feature_rollup` and `project_rollup` count buckets and `met`. No
  `STATE_ORDER`, no `_rank`, no `lowest`, no brief-as-state. Inputs are today's plus `sign_at`,
  the brief's `settled` and `observations`. Keep `_record_verdict` (renamed `_record_passes`),
  `_failing_where`, `_local_passes`.
- `signatures.py` (from `approvals.py`, `git mv`): `signatures_dir()` returns
  `<spec>.signatures`; `SIGNATURE_NAME_RE`, `HOLD_NAME_RE` unchanged in shape; `signer_slug`;
  `load_signatures` reads `signer`; no legacy body, no `is_ci`; `is_current`, `counts`,
  `commit_is_signed`, `commit_author`, `is_ancestor` as today with the new words.
  `ids._approval_paths` uses `signatures_dir()`.
- `payload.py`: schema 5 as B1; `_counting` keyed on the new gate names; review entries only
  when `cfg.gate != 'passed'`; briefs read from `.purlin/briefs/`.
- `records.py` (mcp): `counts_under(gate, label)` keyed on the new values only.
- `checks.py`: `blocks_proof_ready` becomes `blocks_ready`.
- `status.py`: columns and summary per A6; `_directives` from the blocking cell: drafted →
  `purlin:spec`; no test or failing → `purlin:build`; code changed or a non-CI source at
  `strong`+ → push, CI records; weak → `purlin:build` naming the reason; needs a person,
  unsigned, stale, held → `purlin:sign`; everything met → "nothing is outstanding at gate
  <gate>".
- `drift.py`: `qa.signatures_stale`, `qa.review_list_size`, `qa.needs_person`;
  `eng.code_changed`; `design.design_rules_stale` reads the signed cell; `unproved` is
  `spec == 'drafted'`.
- `server.py`: tool descriptions say "the spec status and the cells of every rule".

## B3. Review and gate `scripts/review/`, `scripts/ci/`

- `sign.py` (from `approve.py`, `git mv`): `SCHEMA = 'purlin-signature/1'`, `HOLD_SCHEMA`
  unchanged; body field `signer`; `gate` at signing; `note` field, null unless `--note`;
  `--note` allowed on a rule whose strong cell reads `needs a person`; the walk (from
  `skills/review`'s steps: read the review list, render each brief, take the answer) lives
  here as the no-argument path; `auto_approve` deleted; `signable()` lists rules whose signed
  cell is `unsigned` or `stale`, or whose strong cell is `needs a person`; messages `sign:
  signer list missing: run purlin:init --gate signed`, `<email> is not on the signer list`;
  under `passed` prints what the gate lacks and exits 2; commit subjects per A4.
- `brief.py`: path `.purlin/briefs/<feature>/<RULE-N>.<hash8>.brief.json`; `SCHEMA =
  'purlin-brief/2'`; `state`, `verdict`, `reasons` dropped; `observations` and `settled`
  added; `verdict_for` deleted; `model_prompt` asks the model to state what the test observes
  against what the proof names and to say when it cannot tell, never to recommend;
  `write_briefs` iterates the rules whose risk is at or above `ai_review_at` and whose passed
  cell counts; `render_brief` prints strength beside the minimum, the findings, the
  observations.
- `gate_check.py` (from `verify_gate.py`, `git mv`): `_REQUIRED_STATE` and `_rank` deleted;
  the check is `rule['meets_gate']` with `blocked_by` choosing the section; JSON per A6;
  `_SIGNER_LIST_MISSING = '→ signer list missing: run purlin:init --gate signed'`; `PREFIX =
  'gate:'`.
- `scripts/run/purlin_run.py`: `--record` skips the breaks when `cfg.breaks` is false;
  `_ci_review` writes briefs only; the record commit carries records and briefs;
  `build_record` writes the new gate value; `RECORD_SCHEMA = 'purlin-record/2'`,
  `schema_version` 2; `_VALIDATED_PREFIX` → `refs/tags/record/`. `scripts/run/records.py`
  docstrings follow. `scan.py` prints the bucket lines and the review list per A6.

## B4. Init and update `scripts/init/`

- `scaffold.py`: `GATE_CHOICES` three new answers; `SIGNER_QUESTION`; `write_config` writes
  `signers` under `signed` and never `approvers`; `_BRANCH_RULES` per A3; readmes;
  `print_signed`; `--gate` choices from `gate_module.GATES`; the workflow it writes runs
  `purlin_run.py --all --record --ci` as today.
- `update.py`: the existing 0.9.5 → 0.10.0 migrations now land on this layout: gate values
  `passed`/`strong`/`signed`, `signers`, no approvals directory. `GATE_QUESTION` in the new
  words; the retired-spelling table (`# retired` rows) gains the retired names from decision
  15. No migration from the intermediate layout. `dev/fixtures/upgrade-0.10-dev/` is deleted
  with its tests; `upgrade-0.9.5/` stays.
- `templates/config.json`: `gate: passed`. `templates/gitignore.purlin`:
  `.purlin/briefs/**/*.brief.txt`.

## B5. Dashboard `scripts/report/src/`

- `app.js`: `SCHEMA = 5`; `STATES`/`TONES` replaced by `BUCKETS` and `CELL_TONES` (`passed`,
  `strong`, `signed` pass; `failed`, `stale` fail; `no test`, `not run`, `code changed`,
  `unsigned`, `weak`, `needs a person`, `held` warn; `drafted`, `not required` idle);
  `pill(word)` solid only for `signed`; `hasRisks`, `hasRecords`, `hasApprovals` replaced by
  `level(name)` reading `DATA.gate.gate`.
- `board.js`: `statStrip` from `DATA.summary` and `level()`; `riskGrid` deleted;
  `boardColumns`, `featureRow`, headline per A6.
- `filters.js`: the five filters per A6, each gated by `level()`.
- `rule.js`: cell rows; `briefPanel` at `strong`+; `signPanel` at `signed`; `signerOf` reads
  the file's third dot part.
- `review.js`: risk summary block, six columns, `why` tokens rendered as sentences.
- `styles.css`: `.tiles` uses `repeat(auto-fit, minmax(0,1fr))`; `.strip` two columns only
  when the flag card exists; `.grid` rules deleted; `.rev` six columns.
- `dev/capture_doc_screenshots.py` descriptions in the new words; the five shots keep their
  names. Fixtures `dev/fixtures/report/{solo,team,regulated}.json` rewritten by hand to
  schema 5 first. `regulated` keeps one stale rule, one held rule, one `needs a person` rule,
  one `code changed` rule, one `weak` rule and one `windows: no record yet` rule.

## B6. Formats `references/formats/`

| File | Now | Change |
|------|-----|--------|
| `spec_format.md` | 11 | wording: the risk tag's meaning, `@manual`, the `@env` sentence. No bump. |
| `proofs_format.md` | 8 | wording: `@manual`. No bump. |
| `anchor_format.md` | 7 | wording: "stales the signatures". No bump. |
| `record_format.md` | 1 | **bump to 2**: `gate` enum, `purlin-record/2`, `test_strength` null under `passed`, source, Freshness says code changed |
| `approval_format.md` | 2 | **`git mv` to `signature_format.md`, bump to 3**: directory, filename grammar, `purlin-signature/1`, `signer`, `note`, `gate` enum, no CI variant, holds unchanged |

`references/drift_criteria.md` `> Criteria-Version:` 3 → 4. `CLAUDE.md` format table row
renamed.

## B7. Vocabulary enforcement

`dev/test_vocabulary.py`: `WORDS` gains every retired word from decision 15, matched whole-word
and case-insensitive (so `Untested` and `test_` never match `tested`); `LITERALS` gains the
retired phrases and the names `purlin:verify`, `purlin:review`, `purlin:approve`,
`verify_gate`, `verify-gate:`, `validated/`; `EXCLUDED` drops `"specs/"` and keeps `dev/plans/`,
`design/tokens/`, `RELEASE_NOTES.md` (rewritten anyway), the glossary, `dev/fixtures/upgrade-0.9.5/`
and `.purlin/`; `design/components/` and `design/readme.md` join the checked set once 6B lands.
`PENDING_REWRITE` stages files a phase has not reached; it is empty at closeout.

---

# Part C: execution

## C1. Rules for every lane

- Branch `three-levels` off `evidence-workflow`. Each lane in its own worktree
  `/Users/richlabarca/LocalCode/purlin-wt/<lane>` on `lane/<lane>`, merged back by the
  orchestrator in phase order. Push branches for CI freely. No tags. `VERSION` stays 0.10.0
  and `dev/bump_version.sh` is not run.
- Read this file in full, then `design/readme.md` where the brief says so, then your brief.
- Prose rules from `design/readme.md` "Content fundamentals". No emoji anywhere. Python 3.9,
  stdlib only under `scripts/`, `encoding='utf-8'` on every `open()`.
- Nothing under `scripts/`, `skills/`, `agents/`, `references/` or `templates/` cites `dev/`
  or this repository's `specs/`.
- Tests are tagged for the rewritten spec: keep the `@pytest.mark.proof("<feature>", "PROOF-N",
  "RULE-N")` and `purlin_proof` first argument equal to the spec's feature name, and renumber
  markers when the spec renumbers.
- `dev/run_tests.sh` green in the worktree before the lane reports. Report spec maxima (the
  highest RULE and PROOF ids per touched spec) and test count deltas.
- A lane writes no signature files and runs no `purlin:sign`.
- Feature renames (`approvals` → `signatures`, `skill_approve` → `skill_sign`, `skill_verify` →
  `skill_audit`) go through `scripts/mcp/purlin/ids.py`'s rename path so specs, markers and
  record directories move together. `skill_review` is deleted: its spec, its tests, its record
  directory.

## C2. Phases

Dependencies: 0 → 1 → {2, 3, 4} → 5 → 6 → 7. Phase 4 needs only the fixtures from 0 and can
start with 2 and 3. Phases 5 and 6 need only Part A and can be drafted in parallel with 1 to
4, but their tests (`test_skills.py`, screenshot tests) land after 4.

### Phase 0: contract (orchestrator)

1. Create the branch. Commit this file. Copy Part A into `dev/plans/lanes/tl-_rules.md` with C1.
2. Rewrite `dev/fixtures/report/solo.json`, `team.json`, `regulated.json` to schema 5 (B1,
   B5). These are the contract for phases 1 and 4.
3. `dev/fixtures/consumer-ci/.purlin/config.json`: `gate: strong`. Delete
   `dev/fixtures/upgrade-0.10-dev/`.
4. Arm `dev/test_vocabulary.py` per B7 with every not-yet-rewritten file in
   `PENDING_REWRITE`, so the guard fails only on what a later phase leaves behind. Drop `audit`
   from its word list.
5. Write the lane briefs from this plan.

### Phase 1: core package (2 lanes, Opus)

**1A states and payload.** `gate.py`, `states.py`, `payload.py`, `records.py` (mcp),
`checks.py`, `status.py`, `drift.py`, `server.py`, `ids.py`. Tests: `dev/test_mcp_server.py`
(the 41 state functions, the status-table test at L1075, the gate-defaults test at L580, the
counts-under test at L652), `dev/test_review_list.py`, `dev/test_backing_tests.py`,
`dev/test_failing.py`, `dev/test_drift.py` (L638, L847), `dev/test_scan.py` (L148, L173).
Specs: rewrite `specs/mcp/states.md`; section-rewrite `specs/mcp/drift.md` RULE-7, RULE-14;
`specs/mcp/server.md` PROOF-9; `specs/_anchors/schema_proof_format.md` RULE-1, RULE-3;
`specs/_anchors/schema_spec_format.md` RULE-4.

**1B signatures.** `signatures.py` (from `approvals.py`). Tests: `dev/test_signatures.py`
(from `test_approvals.py`: `TestTheTriple`, `TestStale`, `TestTheFile`, `TestTheSignedCommit`,
`TestTheAncestorCheck`; `TestAutoApproval` deleted), `dev/test_holds.py`. Spec:
`specs/review/approvals.md` → `specs/review/signatures.md` through the rename path,
rewritten: RULE-1..10 hashing and file, RULE-11..16, RULE-39, RULE-41 deleted, RULE-17..23
signing, RULE-24..38 moved to `specs/ci/gate_check.md` in phase 2, RULE-40 holds.

### Phase 2: sign, brief, gate, run (2 lanes, Opus)

**2A sign, brief, gate.** `scripts/review/sign.py` (from `approve.py`, with the walk from
`skills/review`), `brief.py`, `scripts/ci/gate_check.py` (from `verify_gate.py`). Tests:
`dev/test_gate_check.py` (from `test_verify_gate.py`, all 29), `dev/test_brief.py` (L271–296
the model layer, L391, L403, L412, L448), `dev/test_brief_files.py`,
`dev/test_brief_tests_named.py` (L98). Specs: new `specs/ci/gate_check.md` carrying the old
approvals RULE-24..38 rewritten as the three sections and the JSON; `specs/review/brief.md`
RULE-12, RULE-13 (verdicts → observations and settled), RULE-19, RULE-20 (deleted), PROOF-27,
PROOF-28, PROOF-34, PROOF-42.

**2B run and scan.** `scripts/run/purlin_run.py` (`--record` without breaks under `passed`,
`_ci_review`, `build_record`, record schema 2, `record/` tags), `scripts/run/records.py`,
`scripts/run/ci.py`, `scripts/report/scan.py`, `dev/manual/check_qa_tool.py`,
`dev/manual/check_spec.py`, `dev/manual/README.md`. Tests: `dev/test_run_script.py` (L312,
L668, L693, L719, L805, L826, L853), `dev/test_records.py` (L454, L515 and the gate-value
sites), `dev/test_scan_review_list.py`, `dev/test_scan.py` remainder, `dev/test_consumer_ci.py`
(L277, L318). Specs: `specs/run/records.md` RULE-5, RULE-14, RULE-21, RULE-25, PROOF-14,
PROOF-20, PROOF-28, PROOF-29; `specs/run/run_script.md` RULE-17, RULE-20, RULE-42, PROOF-11,
PROOF-17, PROOF-20, PROOF-61, plus the no-breaks-under-passed rule. Format:
`references/formats/record_format.md` to version 2 in the same commit as the record change.

### Phase 3: init and update (1 lane, Opus)

`scripts/init/scaffold.py`, `scripts/init/update.py` (B4), `templates/config.json`,
`templates/gitignore.purlin`. Tests: `dev/test_init_scaffold.py` (the gate and signer
functions at L196–L492, L587, L695; the fixture `--gate` arguments), `dev/test_init_update.py`
(L333–L420; the 0.9.5 fixture lands on the new layout; the 0.10-dev tests deleted),
`dev/test_init_e2e.sh` (the three-gate walk in the new words, `set_signers`, `gate_check.py`),
`dev/test_e2e_required_rules.sh` (L165–L193), the three e2e shell fixtures that write
`{"gate": "tested"}` (now `passed`). Specs: `specs/init/scaffold.md` RULE-2, RULE-3, RULE-4,
RULE-10, RULE-11, RULE-12, RULE-17, RULE-36, PROOF-35, PROOF-41; `specs/init/update.md`
RULE-10, RULE-12, PROOF-10, PROOF-12.

### Phase 4: dashboard (1 lane, Opus)

`scripts/report/src/*.js`, `styles.css`, `dev/capture_doc_screenshots.py`, rebuild through
`dev/build_report.py`, regenerate the five `docs/images/dashboard-*.png`. Tests:
`dev/test_purlin_report.py` (L227, L242, L360, L375, L387, L423, L436, L493, L524, L614,
L689 and `FILTER_CASES`), `dev/test_purlin_report_board_layout.py` (L41, L56). Spec:
`specs/dashboard/purlin_report.md` rewrite of RULE-7, RULE-8, RULE-9, RULE-13, RULE-15,
RULE-16, RULE-18, RULE-26, RULE-30, RULE-32 and their proofs; the 1200-line limit (RULE-2)
holds. Read `design/readme.md` first. Both themes ship, tokens only, no colour literal.

### Phase 5: skills, agent, references, tools (3 lanes)

**5A skills and agent (Opus).** `git mv skills/approve skills/sign`, `git mv skills/verify
skills/audit`, `git rm -r skills/review`; rewrite `skills/sign/SKILL.md` (the walk, the
answers, the write forms), `skills/audit/SKILL.md`, `skills/status/SKILL.md`,
`skills/init/SKILL.md`; section-rewrite `skills/find`, `skills/test`, `skills/spec`,
`skills/drift`; `agents/purlin.md` (the words block, the `sync_status` paragraph, NEVER 2, 3,
4, 5, the routing rows). Every skill's gate-scaling per A5, with `skills/test/SKILL.md` as the
pattern. Tests: `dev/test_skills.py` (L34–38 name list, L223, L238, L247, L257, L499, L538,
L553, L571–596 as `skill_sign`, L656, L716, L723, L770, L818, L822, L862). Specs:
`skill_approve.md` → `skill_sign.md` and `skill_verify.md` → `skill_audit.md` via the
rename path, rewritten; `skill_review.md` deleted; `skill_init.md` RULE-5; `skill_find.md`
PROOF-2; `specs/instructions/purlin_agent.md` RULE-3, RULE-5.

**5B references, formats, tools, root (Opus).** `references/glossary.md` (the words, the
chain, the retired rows from decision 15, the `audit` row removed from the retired table), `hard_gates.md` (rewrite: the level table, source,
the signer list, holds; "Auto-approval" section deleted), `review_criteria.md` (the free checks
stay; "The three risk levels" rewritten; "Verdicts" replaced by "What the brief reports"),
`purlin_commands.md` (twelve skills: anchor, audit, build, drift, find, init, rename, sign,
spec, spec-from-code, status, test; three tables and the syntax block per A4),
`commit_conventions.md` (prefix rows, the signature commit section, the record commit
paragraphs), `drift_criteria.md` (role table, config table with `signers` and `sign_at`,
version 4), `spec_quality_guide.md` (rule tags, `@manual`, "When a rule is stuck" rewritten as
one row per cell word), `references/formats/` per B6, `CLAUDE.md` (format table, one-home
table, the `purlin:build`/`purlin:test` delegation sentence), `README.md` (vocabulary
paragraph, gate table, command table), `tools/QA/purlin-qa-report.md` (Steps 2, 3, 5),
`tools/PM/purlin-anchor-userstories.md` (L39, L43, L69, L134–144), then `bash
dev/pack_tools.sh`. Specs: `specs/tools/qa_report.md` RULE-3, RULE-4, RULE-5, PROOF-3;
`specs/tools/pm_anchor_userstories.md` RULE-4, PROOF-4; `specs/mcp/specs.md` PROOF-4;
`specs/anchor/upstream.md` RULE-7 wording.

**5C skill word swaps (Sonnet).** `skills/build`, `skills/spec-from-code`, `skills/anchor`,
`skills/rename` per decision 15 and A4; `specs/skills/skill_rename.md` and `skill_drift.md`
descriptions; `hooks/hooks.json` checked, unchanged.

### Phase 6: docs and design (2 lanes)

**6A rewrites (Opus).** Full rewrite: `docs/dashboard.md` (against the phase 4 screenshots),
`docs/regulated-workflow.md` (the mermaid `stateDiagram-v2` redrawn as spec status → passed →
strong → signed with the stale and code-changed edges, init block from `docs/_mermaid.md`),
`git mv docs/review-and-approval.md docs/review-and-signing.md` and rewrite. Section
rewrite: `docs/running-and-records.md` (L15, L103, L117, L180, L192, L246–264),
`docs/team-workflow.md` (L1–8, L21–24, L62, L64, L99, L115), `docs/getting-started.md`
(L50–65, L161–175), `docs/raising-the-gate-and-upgrading.md` (L12–16, L32–50, L73, L111–124,
L129–134), `docs/working-together.md` (L68–72, L136–137, the drift samples).
`RELEASE_NOTES.md`: the 0.10.0 entry overwritten to describe this model, the three commands,
and every retired word.

**6B word swaps and design (Sonnet).** `docs/solo-workflow.md`, `docs/specs-and-anchors.md`
(and L135–139), `docs/design-in-specs.md`, `docs/spec-from-code.md`, `docs/index.md` (links
to the renamed page and format); `design/readme.md` L31 and L121–124; `design/components/core/
StatusPill.jsx`, `.d.ts`, `.prompt.md`, `core.card.html`, `data/StatTile.prompt.md`,
`data/data.card.html`, `data/GroupHeader.prompt.md`, `data/DataTable.prompt.md`,
`core/Button.prompt.md`, `core/Tag.prompt.md`, `editorial/CommandChip.prompt.md`,
`editorial/editorial.card.html`, `guidelines/type-scale-ui.card.html`,
`guidelines/type-mono.card.html` to the cell words and gate values; `git rm -r
dev/screenshots/`.

### Phase 7: this repository (orchestrator, after 1–6 are merged)

1. `git rm -r` the 37 `specs/**/*.approvals/` directories and `.purlin/records/*`. Edit
   `.purlin/config.json`: `gate: signed`, `signers: ["rich.labarca@gmail.com"]`, no
   `approvers`. Commit as `chore: drop the 0.10-dev evidence`.
2. `python3 dev/build_report.py`, `python3 dev/capture_doc_screenshots.py`, `bash
   dev/pack_tools.sh`, then a full `dev/run_tests.sh` and `python3 scripts/ci/gate_check.py
   --check`. `PENDING_REWRITE` is empty; the vocabulary test is green.
3. `dev/plans/README.md` names this file. `dev/plans/TODO-0.10.0.md` and
   `dev/plans/held-rules-0.10.0.md` restated in the new words: item 1 becomes "sign the review
   list", with the count from step 2.
4. Push `three-levels`. CI's record commit is the first with briefs under `.purlin/briefs/`.
   Confirm the pull request comment prints the new table and the board artifact opens.
5. Report: the sweep result, the gate check summarised as rules `Not signed`, the vocabulary
   test result, the spec maxima, and anything left undone with why.

### After the report (user)

Sign the review list with `purlin:sign`; apply the three branch rulesets init prints; pull
request `three-levels` → `main`; tag `v0.10.0`.

## C3. Counts to expect

| What | Now | After |
|------|-----|-------|
| rule states / cells | 7 states + 1 flag | 2 spec words, 3 cells, 4 flags |
| gate values | `tested recorded approved` | `passed strong signed` |
| commands for the levels | test, verify, review + approve | test, audit, sign |
| skills | 13 | 12 |
| brief output | 4 verdicts | strength, findings, observations, settled |
| payload schema | 4 | 5 |
| record format | 1 | 2 |
| approval format 2 | `approval_format.md` | `signature_format.md` 3 |
| evidence files in `specs/` | 471 person + 137 ci + 922 brief | 0 until the user signs |
| dashboard tiles at `passed` / `strong` / `signed` | 7 + 1 | 3 / 4 / 5 + 1 |
| board columns at `passed` / `strong` / `signed` | 4 / 7 / 8 | 5 / 7 / 8 |
| specs rewritten / section / swap / deleted / untouched | | 6 / 15 / 6 / 1 / 10 |
| docs rewritten / section / swap | | 3 / 5 / 5 |
