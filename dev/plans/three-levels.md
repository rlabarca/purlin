# Purlin 0.10.0: three levels

*The decisions are listed in the order they were added; a later decision wins, and each reversed decision carries a note naming what reversed it.*

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
   - *Reversed by 103:* two gates, `passed` and `signed`; `purlin:audit` is an optional tool, and `purlin:sign` takes one signature over the evidence package.
2. **Level 2 is fully automatic.** A person first appears at level 3.
   - *Reversed by 103:* the audit is optional and informative at either gate, and a person first appears at the sign-off.
3. **Spec status is Drafted or Ready.** Ready means the proof text clears the blocking free
   checks.
   - *Reversed by 36:* there is no spec status; at `signed` a rule with no proof is listed as `to write a proof for`.
4. **The brief reports, it recommends nothing.** Strength beside the minimum, the free-check
   findings, what the model review observed, and whether it could settle the question. The four
   verdict words are retired.
   - *Superseded by 33 and 40:* there are no briefs; the audit's findings go into the evidence file.
5. **A local pass meets level 1.** Under `strong` and `signed` only a CI record counts; a local
   `purlin:audit` there is a preview that says it does not count.
   - *Reversed by 31 and 103:* a local run counts at either gate.
6. **Under `passed`, `purlin:audit` runs the tests only** and the record carries strength
   `n/a`. Raising the gate to `strong` turns the breaks on, locally and in CI.
   - *Reversed by 103:* the breaks run wherever `mutation_engine` is set, at either gate, and block nothing.
7. **Under `signed`, a signature is required at or above `sign_at`, default `medium`.** Low risk
   meets the `signed` gate at strong. `sign_at: low` signs everything.
   - *Reversed by 103:* no rule is signed one by one; at `signed` one signature covers the evidence package.
8. **CI writes no signature file, ever.** The `.ci.json` auto-approval is gone. Signature
   directories hold only files a person wrote.
9. **Briefs live in `.purlin/briefs/<feature>/`** beside the records, committed by CI. The CI-only
   branch ruleset covers `.purlin/records/**` and `.purlin/briefs/**`.
   - *Superseded by 40:* there are no briefs; each feature has one evidence file per source.
10. **The old approval files, CI files and briefs are dropped, not migrated.** This checkout's 37
    `.approvals/` directories and its `.purlin/records/` are deleted by hand in Phase 7. The
    0.9.5 → 0.10.0 migration in `update.py` lands a project straight on the new layout; there is
    no migration from the intermediate layout and no test for one. The user re-signs afterwards.
11. **Rule text is rewritten freely** wherever the model changes what a rule claims.
12. **A `@manual` proof, or a model review that could not settle, reads `needs a person`**, and a
    signature file from anyone clears it under `strong`; under `signed` the signer rules apply.
    - *Superseded by 23, 78 and 103:* a `@manual` proof is checked by a person in the sign-off walk at `signed`.
13. **The review list carries only what needs a person**: unsigned, stale, held, needs a person.
    A weak rule is build work and stays on the board.
    - *Superseded by 74 and 103:* `Left to do` lists only work, and hand checks and the signature happen in the sign-off walk.
14. **Tiles**: `Untested`, `Failing`, `Passed`; `Strong` at `strong`; `Signed` and a `Stale` flag
    card at `signed`. **Columns**: `Spec`, `Rules`, `Spec status`, `Tests`, `Last run`; `Strength`
    and `Strong` at `strong`; `Signed` at `signed`.
    - *Superseded by 87 and 103:* the boxes are `No proof` at `signed`, `Passing`, and `Strong` where the audit ran.
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
    - *Superseded by 31 and 83:* `record/<name>` tags and the separate gate check at the end of a runner's job are gone.
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
    - *Reversed by 30 and 103:* risk is retired, and no rule carries a signature of its own.
22. **Format versions bump as `CLAUDE.md` says**: record 1 → 2, approval 2 → signature 3, payload
    schema 4 → 5, drift criteria 3 → 4. Spec, proofs and anchor formats change wording only.
    - *Superseded by later decisions:* records, briefs and per-rule signatures are gone; each file in `references/formats/` carries its current number.

23. **`needs a person` is retired** (added 2026-09-17). It stood for two things, and each
    now names the work a person has to do. A rule whose proofs are `@manual` reads
    `manual test` in its strong cell: a person runs the test. A rule whose model review could
    not settle, or that has no brief where its risk asks for one, reads `manual audit`: a
    person judges the proof against the test. A held rule reads `held` there too. The review
    list is the one place a person is needed, and its header keeps the sentence `<n> rules
    need a person`. The `why` tokens are `unsigned`, `stale`, `held`, `manual test`,
    `manual audit`. Lane 7B.
    - *Superseded by 35, 37, 74 and 103:* `manual test`, `manual audit`, `held` and the review list are retired; a hand check happens in the sign-off walk.
24. **The Board tab leads with tests passing** (added 2026-09-17). Its headline is
    `<passing> of <rules> rules pass their tests · <failing> failing · <untested> untested`,
    where passing means the passed cell is met, with `<met> of <rules> meet the gate <gate>` as
    a second, secondary line. The tiles read cumulative levels: `Untested`, `Failing`,
    `Passing`, then `Strong` (strong cell met, signed rules included), then `Signed` and the
    `Stale` flag card. The group band reads `<name> · <n> specs · <passing> of <rules> pass`.
    The gate and the signed layer stay in their own columns. Lane 7A.
    - *Superseded by 60, 92 and 103:* there is no headline line; the boxes carry the counts.
25. **Nothing pushes on its own except `purlin:audit --remote`** (added 2026-09-17). A local
    `purlin:audit --commit` commits the record and prints `Run: git push`; it never pushes.
    `--remote` keeps its push, because the remote runner is the point of it. CI's record commit
    through the git host's API stays: it is the remote runner writing its own evidence, not a
    push from a person's machine. `purlin:sign` and `--tag` already push nothing. Lane 7B.
    - *Superseded by 50 and 75:* nothing commits on its own, and `purlin:test --remote` is the one push Purlin makes.
26. **CI runs where evidence is decided, and enforces the gate** (added 2026-09-26). The
    workflow triggers on pull requests, on pushes to the protected branch, and on pushes to
    `run/*` branches; a push to any other branch starts nothing. A pull request run tests,
    posts the comment and uploads the dashboard, and commits nothing. A run on the protected
    branch, or on a `run/*` branch, writes the records and briefs and commits them there. Every
    run ends with `scripts/ci/gate_check.py --check`, and the job fails when the gate is not
    met, so the required check means the gate held. At `passed` init writes no workflow unless
    `--ci` asks for one (scaffold RULE-13 stands); at `strong` and above it always does.
    - *Reversed by 31 and 75:* a remote runner exists only for a rule that must hold on another system; there are no pull-request or protected-branch runs and no gate check step.
27. **A push is a person's act, and git enforces it** (added 2026-09-26). Vocabulary: a
    **push** is `git push` typed by a person; a **remote run** is `purlin:audit --remote`,
    the one case in which Purlin pushes, to a **run branch** `run/<branch>-<sha7>` it creates,
    waits on, pulls the records back from, and deletes. No skill, lane, agent or hook pushes
    anything else, and none opens a pull request; `purlin:drift` is how a person reads what a
    pull request changed against the local tree. The pre-push hook refuses a push from an
    agent session (`CLAUDE_CODE_SESSION_ID` set) unless `PURLIN_REMOTE_RUN=1` marks a remote
    run, and prints that a person runs `git push`. Lanes 8A (code) and 8B (docs).
    - *Reversed by 31:* the pre-push hook is removed, and a push is free.
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
    - *Superseded by 40, 50 and 106:* one evidence file per feature, committed with `--commit`; `.purlin/tests.md` goes.
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
    - *Superseded by 31, 40 and 103:* a local run counts at both gates, evidence lives at `.purlin/evidence/<source>/<feature>.json`, and there is no gate `strong`.
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
    - *Reversed by 36, 37, 73 and 103:* no bar, no `sign_at`, no Signable and no Review or Sign tab; one signature covers the evidence package.







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
    - *Amended by 37, 73, 75 and 103:* no trust setting, no holds and no bar; the signature covers the evidence package, not one rule's hashes.
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
    - *Amended by 67, 102 and 103:* no bar and no `sign_at`; one signature covers the package, made in a commit signed with any key and verified.
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
    - *Reversed by 103:* the audit and mutation testing are informative only; a weak or unaudited rule blocks nothing, and `min_strength` is retired.
36. **A rule's level uses the gate's three words.** A rule may be marked `[level: passed]`,
    `[level: strong]` or `[level: signed]`, meaning what the gate means: tests; tests and
    audit; tests, audit and signature. An unmarked rule takes the gate. The gate is the
    ceiling: a mark above it is read as the gate. `bar`, `cleared its bar`, `sign_at` and
    `required` are retired. The spec status is folded into the test status: a rule with no
    proof reads `no test` with the reason `no proof written`; `drafted`, `ready` and
    `spec status` are retired. In this repository, the rules of
    `specs/dashboard/purlin_report.md` are marked `[level: passed]`.
    - *Reversed by 73:* no rule carries a level; every rule is asked what the gate asks.
37. **One queue, and no holds.** `purlin:sign` walks one list of the rules that wait on a
    person, each row saying what is needed: a hand check (`@manual`) or a signature. The
    dashboard has one tab for it. `Review`, `Sign` as list names, and `signable` are retired.
    Holds are removed: a reviewer who disagrees adds the missing proof or changes the proof,
    alone or with AI help. `hold`, `held` and `--hold` are retired.
    - *Amended by 74 and 103:* there is no queue; the sign-off walk at `signed` stops at each hand check and each weak or unaudited rule before the one signature.
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
    - *Amended by 46, 98 and 103:* `> Scope:` is optional, and a spec that names no files is warned of, never refused.
40. **One evidence file per feature.** Every run, test or audit, writes
    `.purlin/evidence/<source>/<feature>.json`: each proof's result, the commit, the
    operating system, the time, and once audited the strength and the AI audit's findings
    per rule. One format file, one commit subject. `test results`, `record` and `brief` are
    retired as names of files. `.purlin/tests.md`, the summary table, stays.
    - *Amended by 106:* `.purlin/tests.md` goes too.
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
    - *Amended by 83 and 103:* there are no stale signatures and no queue for drift to report.
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
    - *Superseded by 89:* the docs carry two screenshots, the board and one rule.
46. **What the design round settled** (added 2026-09-27). `dev/plans/design-35-43.md` is the
    technical design for decisions 35 to 43, and its section 10 holds the owner's answers,
    which win over its text. The ones that amend a decision: `> Scope:` is optional below
    `signed` and required at `signed` (39); a rule whose level is `passed` is never audited
    under a higher gate (35); the level is logged in a signature and not locked (31, 36);
    the status word is `out of date` and `code changed` is retired as a word; the audit runs
    `audit_parallel` calls at once, default four (35); drift measures from the last git
    action that brought changes in (42). `dev/plans/stale-inventory.md` is the list the
    final sweep works from.
    - *Amended by 73, 98 and 103:* rules carry no level, no signature is made over one rule, and a spec without files is warned of, not refused.
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
    - *Amended by 67, 75, 102, 103 and 106:* no trust setting; one signature covers the package in a verified commit, and the package names who ran the tests, where and when.
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
    - *Amended by 103 and 106:* a finding blocks nothing; `purlin:sign` refuses results not taken on this exact version of the code, and builds the package.
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
    - *Amended by 73 and 103:* no rule carries a level; at `signed` a rule with no proof is listed as `to write a proof for` and blocks nothing.
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
    - *Amended by 103 and 106:* the package carries one signature over the whole package, built by `purlin:sign` at `signed`.
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
    - *Amended by 103:* the slides show two gates, `passed` and `signed`.
55. **The evidence package is part of the workflow and is committed with the tag** (added
    2026-09-27; amends decision 52). `purlin:export` writes the package into the project,
    at `.purlin/evidence/package/<version>.json`. When `purlin:sign` is about to write
    `signed/<version>` it writes the package for that version, commits it, and tags that
    commit, so the tagged code carries the package that describes it. The package names the
    commit its evidence was taken at, which is the parent of the commit that carries it.
    Run at any other time, `purlin:export` writes the file, says the version is work in
    progress, and commits it only with `--commit`.
    - *Reversed by 106:* `purlin:sign` builds the package from the committed evidence at the gate `signed`, and its first signature writes `signed/<version>`.
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
    - *Amended by 98, 103 and 106:* a spec that names no files is warned of, never refused; hand checks happen in the sign-off walk at `signed`.
57. **The dashboard, from the owner's first look** (added 2026-09-28).
    - The two headline lines above the tiles go.
    - `without a test` reads `no test`.
    - Every neutral text colour measures at least 7 to 1 against the ground and the card it
      is drawn on, in both themes; state colours and the accent are left alone.
    - Whether a proof has a test is read from the markers in the source, not from the
      evidence; a proof whose test exists and has not run reads `not run`.
    - **Proofs show under each rule on the board, contracted by default.** A rule's row
      carries a control that opens its proofs beneath it, each with its words and its own
      result (`passed`, `failed`, `no test`, `not run`) and its tests. Closed, the row shows
      how many proofs the rule has, in the warn tone when one has no test or is failing.
    - **A shared spec's rules are shown once.** Rules that reach a feature from an anchor
      it requires, or from a global anchor, still count toward that feature. The board
      lists them once, under the anchor that owns them, and a feature's row reads
      `<n> rules, plus <k> shared`, with the hover naming the anchors. A rule is always
      addressed by its owner and its id, so opening a rule opens that rule.
    - *Amended by 100:* a feature counts its own rules only, and anchors stand in a section of their own.
58. **A cell above a rule's level shows nothing** (added 2026-09-28). A rule is asked only
    what its level asks. For a rule whose level is `passed`, the strong cell and the signed
    cell are absent: no word, no badge, no reason, on the board, the rule's screen, the
    status table, the evidence package and the payload. For a rule whose level is `strong`
    the signed cell is absent the same way. The `Weak` and `Not audited` counts, the tiles
    and the filters count only rules that are asked the question. This amends decision 36,
    which showed such cells and let them block nothing. A rule whose tests do not pass reads
    what its passed cell says, and its strong cell says `not passed` only where its level
    asks for the audit.
    - *Reversed by 73:* no rule carries a level, so every cell the gate asks for is shown.
59. **The close of the first session** (added 2026-09-28). A rule whose tests have not
    passed reads `waiting` in the columns above, and `weak` means only that the audit found
    fault. The two gaps in the tests of `upstream` are closed. Go is proven against the real
    tool. Linux does not matter for this project; Windows and Mac do, and Windows is shown
    by a remote runner, with the proofs that must hold there still to be named by the owner.
    The evidence of this repository's own run is committed. Text on a solid coloured badge
    is left as it is. The next sanity check, a new user following the docs, is run by a
    fresh agent from `dev/plans/next-agent-prompt.md`.
60. **The count of rules that meet the gate is shown nowhere** (added 2026-09-28). The
    dashboard's box `<n> of <m> rules meet the gate` and its hover go, and the sentence goes
    from the terminal, the docs and the README. The tiles carry the number for each level.
    The CI check still says pass or fail. What meets the gate does not change: a rule marked
    lower meets it at its own level and never holds back the tag (decisions 32 and 36
    stand). This removes the secondary line of decision 24. What the last line of a run, the
    `No tag` line and the CI check's failure say in its place is still to be asked.
61. **The queue names its two kinds of work** (added 2026-09-28). The queue holds hand
    checks and signatures and nothing else (decisions 13 and 37 stand; no audit entry, since
    no person judges strength). `waiting for a person` and `need a person` go. The full
    sentences are `waiting for someone to test by hand` and `waiting for someone to sign`,
    used in hovers and empty states; the card stays `Queue`, and beneath it and in the queue
    tab the short labels are `To test by hand <h> · To sign <s>`. The terminal and the docs
    use the same words. This replaces the sentence decision 23 kept.
    - *Superseded by 74 and 103:* there is no queue, and outside the sign-off nothing reads `to sign` or `to test by hand`.
62. **A signature is locked to the code and to where the tests ran** (added 2026-09-28).
    A signature says a person signed one exact set: the rule, its proof, its test, what the
    audit found, the code the rule covers, and the operating systems its test results came
    from. A change to any of them ends the signature and a person signs again. Before this
    a code change alone left a signature counting once the tests passed again, and the
    machine and operating system were recorded and bound nothing. A signature still belongs
    to no machine: it is bound to where the tests ran, not to where it was signed. The
    signature format changes, so its `Format-Version` is raised.
    - *Reversed by 103:* one signature covers the evidence package; nothing is signed per rule.
63. **Every page is read again against the code, last** (added 2026-09-28). After every
    decision above and every answer to the sanity checks is applied. The ten-minute path
    writes its first rules with `purlin:spec` and marks its tests with `purlin:build`. The
    screenshots are retaken at the end.
64. **The docs and the rules agree, always** (added 2026-09-28). A sanity check reads every
    statement in the docs against the rules and proofs, and is repeated by a fresh agent
    before every release. A statement no rule covers gets a rule, a proof and a test by
    default. The same check runs `purlin:spec-from-code` for real on three small real
    projects, at each gate, and holds the result to three measures: most rules already
    pass, the rules and proofs meet the quality guide, every file and function is covered.
65. **Nine places where the product did not do what its rule says** (added 2026-09-28), found
    by the tests written to close the proof gaps. Each is settled:
    - **The old cache folder.** `purlin:init --update` deletes it outright. The rule changes:
      it no longer says the folder is left on disk and named in `.gitignore`.
    - **The run branch on Azure DevOps.** The remote run reads the full branch name first.
      Fixed on this machine against a stand-in, confirmed on the work machine.
    - **A proof another operating system owns**, whose test is skipped here, is recorded in the
      evidence as `not run`, never `missing`.
    - **A system that is not Windows or macOS** is treated as `linux`. The word typed in a
      spec and the name results are filed under stay `linux`; screens, the dashboard and the
      docs show it as `Linux/Unix`.
    - **A git host that is neither GitHub nor Azure DevOps.** Setup's line says what still
      works: everything on the user's own machine works on any host, and only a remote run
      needs one of the two.
    - **Every ending of a command names a command to run next**, also where the work is
      complete. The build skill's 3 endings and the anchor skill's 2 endings that name none
      get one, and the test checks every ending.
    - **No name containing `token`.** The one line that stores a setting's name under such a
      name is renamed. The rule stays as written and the test checks it in full.
    - **The guard before a revision handed to git** is required where the revision comes from
      outside Purlin. The rule is narrowed to say so; the five places that hand git the fixed
      word `HEAD` stay as they are.
66. **What starting from existing code must give** (added 2026-09-28), the measures of sanity
    check 3. Every source file belongs to some feature's rules. Rules say what a user or a
    caller can see; an internal helper is covered by the rule of the behaviour it serves and
    gets no rule of its own. Every test the project already had is tied to a rule, unless the
    report says why not. On the three trial projects, which are chosen to be well tested, at
    least 7 in 10 rules pass on the first run. A test that was failing before is never made
    to pass by writing the rule to fit it: the rule says what the code should do, and the
    test stays failing until the code is fixed.
67. **Purlin logs a signature and polices none** (added 2026-09-28). A signature counts when
    its commit was signed with an SSH key, any key. Purlin records the signer's name, the
    time and the key's fingerprint, and does not check whose key it is. The list of who may
    sign goes, with the setting and the code behind it: anyone can sign, and the system of
    record decides who was entitled. Before signing starts Purlin confirms only that there
    is a key to sign with. This amends decisions 32 and 48, which asked that the signature
    verify.
    - *Amended by 102 and 103:* the signing commit must verify, with any key, and the signature covers the package.
68. **One summary, steps reached, and what is left to do** (added 2026-09-28). The terminal,
    the dashboard and the check on a remote runner show the same thing. Each step contains
    the next: `35 pass their tests. 30 are strong. 20 are signed.` Whether a version is
    finished is said by what is left: `Left to do: 5 rules to audit, 10 to sign.`, and
    `Nothing left to do` when nothing is. The phrase `meets the gate` is used nowhere. On a
    remote runner the job fails only when a test fails or could not run; rules not yet
    audited or signed never fail it, and no `PASS` or `FAIL` word is printed. A rule with
    no proof, at the gates that ask for one, has its own box and filter on the dashboard.
    A spec's `> Description:` is shown under the feature's name on the dashboard.
    - *Amended by 103 and 106:* the summary says what passes and what the audit found; a weak or unproven rule blocks nothing, and nothing is called finished.
69. **Every command says exactly what to do next** (added 2026-09-28). The test of any
    output is that an agent seeking a goal can read it, know which rule is affected and
    what to do, and improve the project by doing it. A run names each rule that fails or has
    no test, and its advice fits the cause: a comment to correct, settings to restore, or
    `purlin:build`. With the settings file missing, a run stops, says so, names the command
    that restores it, and writes nothing. A comment above a test that is nearly right is
    found and repaired by `purlin:build`; a test run does not look for them. A rule has
    passed only when every test tied to it ran and passed, and the terminal, the dashboard,
    the evidence and the exit code all say the same.
70. **Setup asks one thing** (added 2026-09-28). `purlin:init` asks how far every rule must
    go. How the tests are run is settled at the first test run: `purlin:build` sets it when
    it writes the tests, and where tests already exist Purlin suggests a command, the user
    confirms, and it runs at once. The question about breaking the code on purpose is asked
    only at the gates where it runs. The rehearsal, `--dry-run`, goes. The folder for anchors
    is created when the first anchor is written or brought in. A test run that commits its
    results commits the rules, the marked tests and the settings they describe in the same
    step, and lists each file. With no version stated by the project, `purlin:sign` asks for
    one and offers to write it to a version file. A signed tag is written only when every
    result came from committed work. The docs say commands are run inside Claude Code, and
    carry no section on removing Purlin.
    - *Amended by 80, 98, 103 and 106:* setup asks the gate, the mutation question at `signed` alone, and whether it may commit.
71. **One proof, one case** (added 2026-09-28). A proof holds one starting situation, one
    action and the results seen from it, in at most 60 words. A refusal or a boundary is a
    case of its own. This is written into `references/spec_quality_guide.md`, `purlin:spec`
    writes to it and the audit checks it. Every proof in this repository that holds more is
    split before release, its tests tied again, and the 37 gaps still open are closed in
    that work. The 128 rules the rewrite flagged are sorted: loose wording where the product
    is right is reworded and listed; a product that is wrong, and a real choice, come to the
    owner.
72. **The order of the work** (added 2026-09-28). First every change to what the product
    does, one agent per decision. Then the proofs are split and the gaps closed. Then sanity
    check 3, then every page is read again. A signature's code is the files its feature
    lists: a change to any of them ends the signature of every rule in that feature. Where
    existing code has a test that was already failing, `purlin:spec-from-code` writes the
    rule from what the test expects and leaves it failing.
73. **Every rule is asked what the gate asks** (added 2026-09-28). Marking a rule lower,
    `[level: ...]`, goes. A finished project at the gate `signed` reads the same number
    three times. This removes decisions 36 and 58 and the amendment of decision 60 that kept
    them. The 124 proofs left out of the rewrite because their rule was marked lower are
    rewritten with the rest. `purlin:spec-from-code` marks no level.
74. **One list, `Left to do`** (added 2026-09-28). The queue goes as a separate idea, with
    its tab, its box and its line. `Left to do` holds every kind of remaining work, each
    with who or what does it; `to test by hand` and `to sign` are two of its lines.
    `purlin:sign` still walks the rules that wait for a person. This amends decision 61.
    - *Amended by 103:* `to sign` and `to test by hand` leave `Left to do`; the sign-off walk covers both.
75. **Where Purlin refuses, and where it does not** (added 2026-09-28). Purlin refuses
    nothing a person does. It will not itself state that a version is finished unless that
    is so: the signed tag is written only when nothing is left to do and every result came
    from committed work. The choice not to trust a developer's machine goes, with the
    setting, its question at setup and the check of who committed a runner's results: a
    result counts wherever it ran and records where. A remote runner has one reason, a rule
    that must hold on another operating system. On a pushed signed tag the runner runs the
    tests and nothing else. An audit that finds a proof longer than the standard, or holding
    two cases, notes it and does not find the rule weak for it.
    - *Amended by 103 and 106:* the first signature over the package at `signed` writes the tag, and nothing is called finished.
76. **Small things that follow** (added 2026-09-28). The word `gate` stays. A finished
    project's last line names the release step at the gate `signed`, `git push origin
    signed/<version>`, and at the other two gates says `Nothing left to do.` and names no
    command; every other ending names a command. An anchor's rule is signed once in each
    feature it applies to, a change to that feature's files ends that one signature, and the
    rule counts as signed when it is signed in every one of them. The slides end each gate
    with `A version is finished when`.
    - *Reversed by 100, 103 and 106:* an anchor's rule is counted once, nothing is signed per rule, and no ending says a version is finished.
77. **What a signature is made over** (added 2026-09-28). The rule, its proof, its test, the
    code its feature lists, what the audit found, and the machine the tests ran on. The
    machine it was signed on is not recorded. Run again on the same machine with nothing
    changed, the signature is the same and still counts. A run on another machine replaces
    the results, as results are kept today, and ends the signature. A remote runner is named
    by its kind, `remote runner, Windows`, and not by the name the host lent it, so a second
    remote run ends nothing; the lent name is kept beside it. Purlin checks that a signature
    is present and looks no further. The signature records the signer's name and email as
    git holds them, the time and the key's fingerprint. With no key set up, `purlin:sign`
    shows the commands, offers to run them, and carries on. When it finishes it prints
    `Signed 3 rules as jane@acme.com with the key ending ...Xy4Q.` No message is printed
    when a change ends signatures; the rules return to `to sign`. This amends decision 62.
    - *Reversed by 103 and 106:* one signature covers the package in a verified commit (102), and the package names who ran the tests, where and when.
78. **A check done by hand** (added 2026-09-28). A proof marked `@manual` is checked by a
    person, who writes what they saw and signs, in one act, at any gate. That act stands for
    the test, the audit and the signature of the rule. Only `purlin:sign` records it. It
    shows under `Left to do` as `to test by hand`, and in drift for QA. The dashboard is
    for reading: each line of `Left to do` shows what to type in Claude Code to clear it,
    and nothing is ticked on the page. `purlin:sign` takes one rule, a feature or all.
    - *Amended by 103 and 106:* a hand check is done in the sign-off walk at `signed`, and its note is asked for, not required.
79. **The summary and `Left to do`, in full** (added 2026-09-28). `40 rules. 35 pass their
    tests. 30 are strong. 20 are signed.` Then `Left to do`, one line per kind of work in
    the order it is done, each with its count and its command, kinds at zero left out. The
    lines carry counts and no names; a run names each rule where it reports the problem.
    Every run and every audit ends on the summary and `Left to do`; the audit keeps one
    earlier line saying what it read and found. The arrow line goes: the first line of
    `Left to do` is the next step. On the dashboard a step's box is green when every rule
    has reached it and amber until then, and `Left to do` is a list under the boxes. A rule
    with neither proof nor test is counted under `No proof` alone. A feature's description
    shows when its row is opened. The evidence package carries the same: the total, the
    count at each step, what is left, and the state `finished` or `not finished`; its
    format version is raised. The systems are shown as `Windows`, `macOS` and
    `Linux/Unix`, and in the dashboard's small boxes as `Win`, `Mac`, `Lin`.
    - *Amended by 92, 103 and 106:* the summary says what passes and what the audit found, with no signed count, and nothing is called finished.
80. **Setup, the first run and the upgrade, in full** (added 2026-09-28). `purlin:init` asks
    the gate, and at `strong` and `signed` also whether to break the code on purpose. The
    first test run in a project with tests and no command suggests one from a fixed list of
    test tools, and where it recognises none the AI reads the project and proposes one; the
    user confirms and it runs. A run that commits makes two commits in one step: the rules,
    the marked tests and the settings, then the results, which name the first. The version
    is read from a version file, then from what the project already states in its package
    description, and asked for only when neither gives one. With no supported git host the
    settings say `ci: none`. A missing settings file ends a run with exit 1. In a project
    set up by 0.9.5 and not upgraded, a run stops and names the upgrade. The upgrade has no
    rehearsal. `purlin:build` repairs a comment whose form is wrong or whose feature or rule
    name is one letter from a real one. Each command's instructions keep their maximum
    length: a change cuts as many lines as it adds.
    - *Amended by 103:* the mutation question is asked at `signed` alone.
81. **Starting from existing code, in full** (added 2026-09-28). Every rule is written from
    what its test expects, passing or not, and no test is run first. `purlin:spec-from-code`
    does its best to give every source file a rule and ends by listing the files that got
    none, for a person or an agent to decide. A test may be left untied for three reasons,
    each listed in the report: it shows only part of what a rule needs, it repeats a test
    already tied, or it tests code the project does not own. This amends decision 66.
82. **Windows** (added 2026-09-28). The rules that must hold on Windows are those about
    reading and writing files, paths, and starting other programs. An agent sorts the rules
    and shows the owner the list before any is marked.
83. **The seven calls the plan left open** (added 2026-09-28), the answers to section 5 of
    `phase1-plan.md`. A result from a system that was not there at signing is added beside
    the others and ends no signature; a signature ends when a machine it was made with
    changes. A remote runner runs only the systems the rules name, and no Linux job of its
    own. The separate check at the end of the runner's job goes, with its spec and its
    tests: the test step's ending is what is read, and its result is the job's. This
    repository's own runner file is deleted now, and setup writes it again once rules name
    Windows. The count of signatures that ended, the word `stale` and drift's list of them
    go: such a rule counts under `to sign`. The dashboard's boxes for rules with no test,
    failing and failing on one system go: the step boxes, `No proof` and `Left to do`
    remain. The evidence package's `not for approval` goes: it carries the state and the
    gate.
    - *Superseded by 103 and 106:* no per-rule signature ends; a result counts only when it was taken on the version of the code being signed.
84. **A hand check needs no note** (added 2026-09-28). Signing a rule that is checked by
    hand counts as the check, with or without a note. `purlin:sign` asks for the note and
    records it when given. This keeps the owner's earlier choice and reads decision 78's
    "writes what they saw" as what is asked, not what is required.
    - *Amended by 103 and 106:* the note is asked in the sign-off walk, and an empty answer is recorded as `no note`.
85. **The dashboard's badges, filters and reasons** (added 2026-09-29). A rule's row shows a
    badge only for a step it has reached, `PASSED`, `STRONG`, `SIGNED`, and `FAILED` where a
    test fails; a step not reached shows nothing. The `Left to do` list leaves the dashboard.
    In its place the filter buttons above the table are named as the lines of `Left to do`
    and carry their counts, `To audit 5`; choosing one shows those rules and the command to
    type in Claude Code. Why a rule has not reached a step, and what the audit found, shows
    when the rule is unfolded and not when it is folded. The terminal keeps `Left to do`.
    The line `→ Run: purlin:init --update` above the summary stays, and so do the arrows in
    each command's instructions. `purlin:sign` given several rules of which one does not
    exist signs the rest and names the one. `CLAUDE.md` is read whole against the product
    and corrected; what is not obvious is asked.
    - *Amended by 89 and 103:* there is no `SIGNED` badge, and `purlin:sign` signs the package, not a list of rules.
86. **One way to look closer at a rule** (added 2026-09-29). The full page for one rule
    goes. Unfolding a rule's row on the board shows everything about it in place: why it has
    not reached a step, what the audit found, who signed it and with which key, the machine
    its tests ran on for each system, and its proofs with their tests. The docs carry one
    screenshot of the dashboard, the board with a rule unfolded.
87. **The `No proof` box comes first** (added 2026-09-29). On the dashboard the boxes read,
    left to right, `No proof`, `Passing`, `Strong`, `Signed`, in the order the work is done.
    The filter buttons follow the same order as the terminal's `Left to do`, in which writing
    a proof is already first.
    - *Amended by 103:* the boxes are `No proof` at `signed`, `Passing`, and `Strong` where the audit ran; there is no `Signed` box.
88. **The dashboard's top corner** (added 2026-09-29). The box `at <sha>` goes: `Data: <age>
    old` says whether the page is current, and the evidence package carries the commit. The
    box for the last signed version shows at the gate `signed` only, as `signed/<version>`
    with no sha, or `no signed tag`; at the first two gates there is no such box. The box
    `gate: <gate>` stays.
    - *Amended by 106:* no release is tracked, so at `passed` there is no tag box.
89. **The rule's page stays, and holds the detail** (added 2026-09-29). This withdraws
    decision 86 and the last part of decision 85. Clicking a rule opens its own page, which
    shows why the rule has not reached a step, what the audit found, who signed it and with
    which key, and the machine its tests ran on for each system. An unfolded row on the
    board shows what it showed before: the rule's proofs, each with its result, its tags and
    its tests, and nothing more. The docs carry two screenshots, the board and one rule.
    - *Amended by 103:* the rule page names no per-rule signer; the signature covers the package.
90. **A spec's shared rules on the dashboard** (added 2026-09-29). The `Rules` cell reads
    `16 (+6)`, and its hover says what the second number is, `16 rules of its own, and 6 more
    it must also meet, from shared rules:`, then each anchor with its count. The terminal
    keeps `16 (+6 shared)`, since it has no hover. The two differ by that one word, which the
    rule that the terminal and the dashboard mirror each other's words now allows.
    - *Reversed by 100:* a feature counts its own rules only.
91. **Small changes to the dashboard, made at once** (added 2026-09-29). The line saying how
    old the data is reads the age alone, `Data: 7 hours old`; its hover says how to refresh
    it, and pressing it reloads the page. In the light theme each tan ground but the
    lightest is 5% darker: `#F4EFDF` to `#E8E3D4`, `#E4DDD4` to `#D9D2C9`, `#D3C9BC` to
    `#C8BFB3`; the muted ink is darkened from `#3B4F56` to `#384B52` so that neutral text
    still measures 7 to 1 on every ground it is drawn on.
92. **The dashboard carries no summary sentence** (added 2026-09-29). The line `563 rules.
    563 pass their tests. 0 are strong. 0 are signed.` leaves the dashboard: the boxes carry
    the counts. The terminal keeps it, since it has no boxes. This amends decisions 68 and
    79, which showed the same thing in both places.
    The total is kept in the `Passing` box: under its label, in the label's own font and
    colour, a second line reads `563 RULES TOTAL` (`1 RULE TOTAL` for one), from the
    payload's count and never recounted in the page. The other boxes carry no such line.
93. **Test strength shows only when it was measured** (added 2026-09-29). The `Strong` cell
    reads `0 of 26` where no strength was measured, and `2 of 4 · 86%` where one was; `n/a`
    is printed nowhere, on the dashboard or in the terminal. On the dashboard the hover of a
    percentage says what it is: `Test strength: the tests caught 86 of every 100 deliberate
    breaks of the code.` The audit's report says nothing of strength where none was
    measured. The model is told `test strength: not measured`, in words. Setup's line about
    a missing tool is reworded, since the cell no longer reads `n/a`. The stand-in inside a
    signature stays as it is: no person reads it, and changing it would end every signature.
    - *Amended by 103:* no signature is made over one rule, so there is no stand-in inside one.
94. **The answers to the second fan-out's questions** (added 2026-09-29), which are grouped in
    `phase2-questions.md`.
    - **A rule about a command's instructions says what the instructions tell the agent**, and
      its test reads the instructions. That the agent follows them is shown by the sanity
      checks before each release, which run the commands for real.
    - **A mistake Purlin can see in a spec is warned of, with its fix.** The status and every
      test run print one line naming the spec, the mistake and the command that fixes it, and
      carry on: an entry of the covered files that finds no file, two specs with one name, a
      rule number used twice, a proof line that cannot be read, a first heading that names
      another feature. Nothing is refused.
    - **Test strength is one share per feature**, in every language. The working per rule and
      the rules about it go.
    - **A rule that lists several separate things is split by claim**, its proofs moved
      unchanged.
    - **The first test run suggests a command for every test tool it recognises**, confirmed
      together. Setup's flag for adding a tool goes.
    - **With breaking the code on purpose turned on, nothing measured means not strong.** A
      tool not installed, or out of time, makes the rule weak with a reason naming the command
      that fixes it. A tool that cannot run on this operating system counts as no tool, and
      the audit alone decides.
    - **The 55 readings** of `phase2-questions.md`, "One sensible reading", are applied. The
      owner reads the list afterwards and says which to reverse.
    - *Amended by 103:* a rule found weak, measured or not, blocks nothing.
95. **Windows, settled** (added 2026-09-29). Tests run on Windows only where what they check
    could differ because of files or the operating system.
    - **A remote run on a system runs only the tests tied to proofs tagged for that system.**
      This holds for every project, not this one alone: the tags are what is run.
    - **The list** is the 90 rules the sort found, less those a Windows run could show nothing
      new about (a rule whose only test reads a text file, a rule only Purlin's maintainers
      run, the two about console characters that another rule covers), plus the five that rest
      on line endings.
    - **Each rule on the list gets one more proof, tagged `@env(windows)`**, tied to the same
      test by a second comment. The Mac keeps proving the proof it has.
    - **Of the six tests that stop a Windows run today**: the two walks from setup to a signed
      tag and the file link are Mac only; finding the GitHub program, starting SQLite and the
      file that cannot be read run on Windows, the last with a Windows way of locking the file
      written for it. The walks stop reporting success where they did not walk.
    - **The four places that are probably wrong on Windows are fixed first**, and the tests'
      stand-in programs get the endings Windows uses, so that each fix is shown by a test. The
      skills start Purlin's scripts through the interpreter lookup the plugin's server uses.
    - **The whole path on Windows is not walked for 0.10.0.** Its parts are proven there and
      the whole on the Mac; the release notes say so.
96. **The words agents chose** (added 2026-09-29). Setup prints a line for each case of the
    git host: `No git host found.` where the project has none, and `This git host cannot run
    tests remotely. Everything on this machine works.` where it has one Purlin cannot use.
    The signed panel on a rule's page and the line `Nothing is waiting for someone to test by
    hand or to sign.` stay as written. The other wordings listed in `handoff.md` stand, and
    sanity check 3 reads every message against the rules and the writing style.
97. **The answers before the third fan-out** (added 2026-09-29), to the questions of
    `phase3-plan.md` section 8.
    - **A settings file that cannot be read stops every command.** It prints
      `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`
      The cause is the file reader's own words and line, such as
      `Expecting ',' delimiter at line 4`; or `it is not UTF-8 text`; or
      `it holds a list where an object belongs` (or `a string`, `a number`); or the operating
      system's own message where the file could not be opened. `purlin:test` then ends on
      `→ Fix the settings file by hand, then run: purlin:test`.
    - **A mistake in a spec is named with the spec first and the command last:**
      `login: > Scope: names src/gone.py, which finds no file in git. Run purlin:spec login.`,
      `specs/auth/login.md and specs/admin/login.md are both named login; only specs/auth/login.md is read. Rename one: git mv specs/admin/login.md specs/admin/<new name>.md`,
      `login: RULE-2 is written twice; the second is read. Run purlin:spec login.`,
      `login: a line under ## Proof cannot be read: - PROOF-7 shows the lockout. Run purlin:spec login.`
      and
      `login: the first line names checkout, but the file is login.md, so it is read as login. Run purlin:spec login.`
      The line for rule lines with no number gains the same ending:
      ``WARNING: 1 line under ## Rules in specs/auth/login.md is not numbered; a rule is `- RULE-N: <text>`. Run purlin:spec login.``
    - **Comments above tests that name nothing are the second line of `Left to do`**, after
      `rules to write a proof for`, and every comment that fails the run is counted:
      `1 test comment to correct: purlin:build`, `3 test comments to correct: purlin:build`.
      The dashboard has a `To correct` button.
    - **A proof with no test is named in its rule's line:**
      `login RULE-3 has no test for PROOF-7. Run purlin:build login.`, several joined
      `PROOF-7, PROOF-9`. The rule's page gives the reason `no test for PROOF-7`.
    - **The first test run suggests a command for each test tool it finds:** one line
      `Suggested for pytest: <command>` per tool, each followed by what that tool needs added,
      then one line `Suggested tests setting: [<pytest entry>, <vitest entry>]`, which the agent
      writes as it stands. On Windows the Python command starts `py -3 -m pytest`, and
      elsewhere `python3 -m pytest`.
    - **Setup names a missing git host on a line of its own:** `Gate strong. Suites pytest.`
      then `No git host found.` A git host Purlin cannot use is named in the same place,
      `This git host cannot run tests remotely. Everything on this machine works.` The upgrade
      keeps `No git remote, so there is no runner to read this workflow. Add one with: git remote add origin <url>`.
    - **The tool that changes one setting answers** `The setting was not saved: <cause>.`,
      `A change needs a value; nothing was saved.`,
      `"gold" is not accepted for gate; it takes passed, strong or signed. Nothing was saved.`
      and `version is written by purlin:init from Purlin's own version; nothing was saved.`
      The tool does not change `version`. What each setting takes: `gate`
      `passed, strong or signed`; `mutation_engine` `none, auto, mutmut, stryker or stryker_net`;
      `min_strength` `a whole number from 0 to 100, or null`; `audit_parallel`
      `a whole number from 1 to 16`; `tests` `a list`; `ci` `github, azure or none`.
    - **A rule weak only because strength was not measured has a line of its own**,
      `3 rules to measure: purlin:audit`, just before `rules to strengthen`. Its reason follows
      the words `strength not measured: `, as in
      `strength not measured: mutmut is not installed: run "pip install mutmut"`.
    - **Two more ways to measure nothing leave a rule weak**, each counted where its fix is:
      `strength not measured: mutmut ran and wrote no report: run purlin:audit again` with the
      rules to measure, and
      `strength not measured: the spec names no code files: run purlin:spec login` under
      `rules to tie to their files: purlin:spec`, a line that then also stands at the gate
      `strong` when the code is broken on purpose.
    - **The breaking tool's reasons name the fix:**
      `dotnet is not installed: install the .NET SDK, then run "dotnet tool install -g dotnet-stryker"`
      and
      `the engine timed out after 3600 s, so the breaks it made measure nothing: run purlin:audit --arm-timeout <seconds> to give it longer`.
      `purlin:audit` takes `--arm-timeout <seconds>`, how many seconds the breaking tool may
      run for one feature. Its usage line reads
      `purlin:audit --arm-timeout <seconds>  Give the breaking tool longer per feature`.
    - **On Windows the reason Python's code is not broken is given:** setup and the upgrade
      print
      `Mutation testing is off: mutmut does not run on Windows, so the AI audit alone judges test strength.`,
      and the run prints
      `mutmut does not run on Windows, so test strength is not measured here and the AI audit alone decides`.
    - **Proofs that describe a broken copy of the instructions leave every spec of that
      kind:** about 280 proofs leave 12 specs, and each broken-copy check stays inside the test
      of the proof it guards.
    - **The audit printout's rule that only a program sees folds into the rule about what the
      printout shows.**
    - **A rule no spec has is named with the next step:**
      `login RULE-9 is not a rule any spec has. Run purlin:status login to see its rules.`
    - **A signed tag git could not write** is one line,
      `No tag: git could not write signed/1.2.0: <git's own message>.`, and signing reports
      failure.
    - **The audit's notes follow its findings with no heading**, each starting `Note:`.
    - **The reason given for a nearly right comment says both steps:**
      `` `RULE-30` is one character from `RULE-3`, which login has; a comment names its one proof, `PROOF-3` ``.
    - **An anchor is a spec in Purlin's format.** A source that is anything else is refused
      with an error that says so, whether it is a file of plain text, a description in words,
      or a file in a repository that is not in the format, and nothing is written. Drift and
      `purlin:anchor sync --check` report `error` for such an anchor a project already has.
      Anchors made from plain text go everywhere, with their rules, the instructions and the
      lines of the references and docs about them. The refusal reads
      `refunds: not added. policy.txt is not a spec in Purlin's format kept in a git repository. Run purlin:anchor create refunds to write its rules in this project.`
      Drift reads
      `anchor refunds: its source, policy.txt, is not a spec in Purlin's format kept in a git repository, so it cannot be checked. Run purlin:spec refunds to take out its > Source: and > Pinned: lines and keep it as this project's own anchor.`,
      and the anchor check the same after `refunds: `. A local anchor, which has no
      `> Source:`, is not touched.
    - **Proofs waiting for another system are counted in one line per system** on a person's
      machine: `87 proofs need Windows; this machine is macOS. Run purlin:test --remote.`
    - **A remote runner starts a file of mixed tests whole**, and only the tests of proofs
      tagged for its system are recorded and can fail the run.
    - **A remote run that cannot name its branch** prints
      `No branch could be read from the git host or from git, so the results were not committed.`
    - **A remote run on a branch that is neither a run branch nor a signed tag** prints
      `This run is on feature/x, which is neither a run branch nor a signed tag: the tests ran and nothing is written.`
    - **Each proof is proven where its tag says.** A person's own machine, Mac or Windows,
      proves every untagged proof and every proof tagged for its own system, and never one
      tagged for another: a proof tagged for macOS is proven only on a Mac, and one tagged for
      Windows only on Windows. A remote machine is written into the runner file only for a
      system some proof is tagged for that the machine running setup is not. The 13 Mac-only
      proofs are tagged `@env(macos)`, and this repository's runner file, written on a Mac,
      has no Mac machine. A remote machine runs only the tests tied to proofs tagged for its
      system, as decision 95 says.
    - **The Windows list stands as `phase3-windows-list.md` holds it**, less the row for the
      anchor made from a text file, and meets decision 82. Wave W marks from it, with rule,
      proof and test names brought up to date after the lanes merge, and reports what it
      marked; nothing waits for the owner to read the list again.
    - **The first remote run on Windows goes ahead without asking again.** After wave W, setup
      writes this repository's runner file and `purlin:test --remote` runs once. It pushes one
      temporary run branch and nothing else: no tag is pushed, and `main` stays on this machine.
    - *Amended by 103:* `min_strength` and the gate `strong` are retired, so the settings list and the setup example lose them.
98. **The answers to sanity check 3** (added 2026-09-30), to the 15 questions of
    `sanity-3.md` section 11, given on 2026-09-29 and 2026-09-30.
    - **The README says nothing about leaving.** The line `If you leave, the markers are
      comments.` is removed.
    - **The ten-minute path shows what you type and the summary each step ends on.** The
      rules and tests a model writes differ on every run, so the page shows none of them; the
      summary each step ends on is the same on every run.
    - **Examples inside a function's documentation keep running** under the command the first
      test run suggests, wherever the project's own test command ran them. `purlin:spec-from-code`
      lists them as tests left untied for a fourth reason, `cannot carry a comment`.
    - **A part of the code no caller outside the project can reach gets no rules.** It is listed
      among the files with no rule, and its tests are listed as left untied for a fifth reason,
      because they test code no caller can reach. This amends decision 81.
    - **A proof may name a library's public names and the error types a caller gets back.**
      Names from inside the code stay barred. `references/spec_quality_guide.md` gains that
      case.
    - **One proof may name a list of like inputs** that share one action and one kind of
      result. The quality guide says so. This amends decision 71.
    - **A rule number is never reused.** The spec records the highest rule number it has ever
      held, and new rules count from there. The spec format changes, so its `Format-Version` is
      raised.
    - **`> Requires:` names anchors only**, a project's own or pinned ones. In the owner's
      words: "rules can reference internal and external anchors. That's it." A name that is a
      feature's spec and not an anchor is warned of in the shape of decision 97's spec
      mistakes, feature name first and command last, and its rules do not apply:
      `login: > Requires: names checkout, which is not an anchor, so its rules do not apply. Run purlin:spec login.`
      The count `(+6)` on the dashboard and `(+6 shared)` in the terminal always counts rules
      of anchors, and rules from a required anchor keep the label `required`. Every rule,
      proof, instruction, format line and doc line that lets a spec require another feature's
      spec changes. This repository's `specs/mcp/specs.md` requires the anchor
      `schema_spec_format`, which stays.
    - **Signing a rule whose spec names no files says so.** At the gate `signed`, signing a
      rule of a spec that names no covered files prints, on that rule's line, the command that
      adds the files. Nothing is refused.
    - **Setup asks whether it may commit what it wrote.** In the owner's words: "Setup asks if
      it can commit". It writes the settings, the ignore list and, with the breaks on, the
      breaking tool's configuration, then asks whether it may commit them, and on yes commits
      them in one commit; with `--yes` it commits without asking. This amends decision 70,
      "Setup asks one thing": setup asks the gate, at `strong` and `signed` whether to break
      the code on purpose, and whether it may commit.
    - **The signing pages carry no advice** to upload keys to the git host or to protect
      branches and tags.
    - **A remote run with no command-line program of the git host refuses before pushing
      anything** and names the program to install. Nothing is left on the git host.
    - **On the dashboard the design stands:** small labels are set in capitals.
      `references/writing_style.md` gains one sentence saying so.
    - **The warning for a rule line with no number loses its prefix** and takes the shape of
      the other five:
      ``login: 1 line under ## Rules is not numbered; a rule is `- RULE-N: <text>`. Run purlin:spec login.``
      This amends decision 97.
    - **When the first test run finds no test tool it knows**, it prints
      `No test command is set and no test tool Purlin knows was found, so nothing ran. The agent reads the project and proposes a command for you to confirm.`
    - *Amended by 100 and 103:* `> Requires:` goes, and no rule is signed one by one.
99. **The answers after phase 4** (added 2026-09-30), to the questions the fourth phase left
    open.
    - **A proof number is never reused.** The spec records the highest proof number it has
      held, beside the highest rule number, and new proofs count from there. The spec format
      changes, so its `Format-Version` is raised.
    - **The 78 tests that fail on Windows and that no rule is tagged for are left as they
      are.** Windows is proven for the rules on the accepted list and nothing else is claimed.
    - **The export command's instructions say what the regulated system of record holds:**
      the controlled document, the authority to sign it off, and the signature that counts
      under the regulation. The rule covers all three and the page keeps them.
    - **A committing test run that selected nothing commits the settings together with any
      changed spec and marked test**, in one commit, so nothing of Purlin's is left
      uncommitted.
    - **Two lines on the dashboard say what is true.** With mutation testing off, the `Strong`
      box's hover reads `no minimum strength applies: mutation testing is off`. A proof
      checked by hand reads `Checked by hand. Type purlin:sign <feature> RULE-N in Claude
      Code.` in place of the line that sends a person to write a test.
    - **Setup leaves test fixtures out** when it decides which test tools a project uses:
      files under a folder named for fixtures, samples or test data do not count, so setup
      names only the tools the project itself uses.
    - *Amended by 103:* a hand check is cleared in the sign-off walk, and `min_strength` is retired.
100. **An anchor is a set of rules for the whole project** (added 2026-09-30). Closed, and not
    yet built. This reverses decision 76's signing of an anchor's rule in each feature, and the
    part of decision 98 that kept a line in a spec naming the anchors it requires.
    - **Every anchor is global.** Each of its rules is proven by tests that run across the
      whole project, tied to no feature. A project's own anchor and one pinned from another
      repository are alike in this.
    - **A rule that cannot be checked across the project is not an anchor rule.** It is written
      as an ordinary rule in the spec of each feature that needs it, in that feature's own
      words. In the owner's words: "Global or not an anchor".
    - **A spec names no anchor.** The line `> Requires:` goes, and so does `> Global: true`,
      since every anchor is global. A spec that still carries either is warned of, with its
      fix, in the shape of decision 97's spec mistakes.
    - **Each anchor rule is counted, audited and signed once.** A feature's row counts its own
      rules only, so the counts `(+8)` and `(+8 shared)` go from the dashboard and the
      terminal, and a feature whose 11 rules pass reads `11 of 11`.
    - **Anchors stand in a section of their own on the dashboard**, above the spec table, headed
      `Anchors`, with the same columns and under the same filters; the word `(anchor)` after a
      name goes.
    - **Any change to the project ends an anchor's results and its signatures.** The project is
      every tracked file but the records Purlin itself writes: the results of a run, the
      signatures and the evidence package. An anchor names no covered files. At the gate
      `signed`, anchors are in practice signed last.
    - **A rule of a pinned anchor that no project-wide test can show is checked by hand**: a
      person checks the project against it and signs, as for any rule proven by hand, and again
      each time the signature ends.
    - **An anchor's tests are judged by the AI audit alone.** No code is broken on purpose for
      an anchor, and no test strength is shown for one.
    - **Still to be asked when it is planned:** the words of every line a person reads that this
      changes, and what becomes of this repository's anchor about the spec format, which one
      feature required and whose rules are about one piece of code.
    - *Amended by 103:* no anchor rule is signed one by one; a pinned anchor's rule that no test can show is checked by hand in the sign-off walk.
101. **The answers to the plan for decision 100** (added 2026-09-30), to the three questions of
    `d100-plan.md`, with one further request. The plan carries them in its contracts C12 to C15.
    - **A pulled anchor whose source carries `> Requires:`, `> Global:` or `> Scope:` is copied as
      it is, and warned of.** Every status and test run prints one line, the anchor's name first
      and the fix last, until the other team changes its file:
      `security_baseline: its source, https://github.com/acme/policies.git, carries > Scope:, which Purlin does not read on an anchor, so the line is read as nothing. Ask the owners of https://github.com/acme/policies.git to take it out, then run purlin:anchor sync security_baseline.`
    - **The upgrade from 0.9.5 keeps each anchor and takes the naming lines out**, printing one
      line per anchor that specs named, naming them and the command that moves a rule into them:
      `proof_common: its rules now cover the whole project, where 1 spec named it: sync_status. A rule that holds only there belongs in that spec: run purlin:spec proof_common.`
    - **A pinned anchor's rule that does not apply to this project is signed as not applying.**
      In the owner's words: "this project can sign it but the signature just means it doesnt
      apply, in this case". `purlin:sign <anchor> RULE-N --does-not-apply "<why>"` writes a
      signature carrying the reason; the rule then reads `does not apply` in every cell, counts
      as met, names who said so, and the evidence package carries it. Only a rule of a pinned
      anchor is signed this way; a rule of the project's own anchor that does not apply is
      deleted. Like every anchor signature it ends on any change to the project, and the rule is
      then `1 rule to confirm as not applying: purlin:sign`.
    - **The dashboard's theme button is a glyph**, `◐` in the dark theme and `◑` in the light,
      the words `Light theme` and `Dark theme` staying as its hover and accessible name. The two
      glyphs join `▶ ▼ ▲ →` as the ones Purlin uses.
    - The six calls the plan made stand.
    - *Reversed by 103:* with no per-rule signature, `--does-not-apply` goes; how a pinned anchor's rule that does not apply is handled is still to be asked.
102. **The answers to the QA and product check** (added 2026-09-30), to the findings of
    `sanity-qa-product.md`, a cloud run in which one agent played product, QA and dev in three
    clones of one repository on a sample-intake project at the gate `signed`.
    - **A number written twice in one spec is caught, and so is a leftover merge-conflict line.**
      A proof id written twice is warned of as a rule id is, in the shape of decision 97. The
      spec's rules then read `failed` with the reason naming the number, so nothing counts as
      passing; tests still run and print. Signing that feature and writing a tag are refused
      until the spec is fixed. This amends decision 94's "nothing is refused" for these two
      mistakes alone.
    - **Drift catches a reused number in your own checkout.** In the owner's words: "drift is
      only working locally on your checkout.. so it's a merge process locally based on what you
      checked out". After you merge or pull, drift names a number written twice and a test
      comment whose proof's wording changed since the test was marked, and suggests renumbering
      the side that is not already on the default branch. Drift never fetches; its line says how
      old the local copy of the default branch is, so the person can fetch and run it again.
    - **The rule for a collision is written down:** the number already on the default branch
      keeps it, and the branch's rule or proof moves. The advice to rename signature files goes;
      a moved rule needs a new audit and a new signature.
    - **A hand check's signature is bound to the rule's and proof's wording alone**, so a code
      change does not end it. Editing another test in the same file and re-running the same
      tests on another computer still end a signature, as now.
    - **Every signature that ends says so**, one line each, naming the rule, the signer and the
      cause.
    - **No rule carries a level of its own**, as before. QA's risk-based validation is taught on
      a QA page: look and feel is not a rule, and critical computations and data flows carry
      more proofs.
    - **A version is signed on a release branch**, which the docs teach; new specs land on the
      default branch and wait for the next version.
    - **Fixed without a question, as bugs or plain gaps:** the signing commit's signature is
      verified, not only present (decision 48 kept it); the tag is refused when the default
      branch on the host has moved past the commit being tagged, as far as the local copy
      shows; the signing walk shows each proof's tied test; drift reports proofs added, changed
      and moved; a re-run after an evidence conflict keeps audit results whose hashes still
      match; the docs say who commits evidence and on which branch; the status names the real
      cause when a spec's files do not exist yet; the first test run recognises a plain
      `tests/test_*.py` project; the docs example of `> Highest-Proof:` is corrected; a QA page
      walks a person from criteria to proof to signature.
    - **A tag keeps up with the branch being tagged** (answered on the plan's Q1): it is refused
      when that branch's copy on the host, as last fetched, holds commits the checkout lacks. On
      the default branch that is the default branch; on a release branch, the release branch.
    - **Not changed, as settled before:** who may sign (logged, not policed, decisions 48 and
      52) and the walk writing the tag when nothing is left.
    - *Amended by 103:* signatures no longer end one by one; the one signature covers the package.
103. **Evidence is signed once, at the release** (added 2026-09-30). In the owner's words:
    "we don't need to actually log the QA evaluation of the test. It's just a concurrent workflow
    where they continually improve the specs together. Signing off is a final check when
    everybody is done", and "we are just creating evidence, not enforcing policy". This reverses
    per-rule signing (decisions 76, 101's signature as not applying, and 102's lines about
    signatures that end) and the gate `strong`.
    - **While specs are iterated, nothing is signed and nothing is recorded about anyone's
      judgment.** Product, QA and dev improve rules, proofs and tests together on their branches.
      The status and dashboard show the state; `Left to do` lists only work (proofs and tests to
      write, tests to fix, the audit's findings where it ran). No `to sign` and no
      `to test by hand` outside a release.
    - **The gate is two answers.** `passed`: every rule's tests pass on committed evidence at the
      release commit. `signed`: the same, and at least one person signs the evidence package. The
      gate `strong` goes.
    - **The AI audit and mutation testing are optional, informative tools under either gate.**
      Their findings go into the evidence package where they ran; nothing blocks on them. The
      settings that made them block lose their force.
    - **A release is a commit, a package and a tag.** On a release branch, the release run
      commits the evidence and the package. At `passed` it tags `passed/<version>`, unsigned. At
      `signed` the first signature writes `signed/<version>`; later signatures are added over the
      same package and listed, and the tag never moves.
    - **One signature covers the whole package**, a signed commit over its hash. Any role may
      sign, several people may; Purlin creates evidence and enforces no policy about who.
    - **The sign-off walk** (`purlin:sign` on the release branch): it refuses and names the command
      when a rule fails or the evidence is not committed at this commit; shows an overview
      (rules, systems, the audit's strong, weak and not audited, hand checks to do); then stops,
      one rule at a time, only where a person has something to look at: each hand check (the
      person types what they saw, the note goes into the package), each weak rule and each rule
      never audited (shown with its proofs, each test's name and body, the results and the
      finding; the signer continues, adds a note, or stops to fix). Rules the audit found strong
      are a list the signer can open, or walk in full on request. A weak or unaudited rule never
      blocks the signature. Then one signature, then the tag.
    - **The package records what the signer was shown**: which rules one by one and which only
      in the list, and every note typed. It logs no judgment.
    - **Numbers: the warnings stay, and a renumbering helper asks.** Where drift, the status,
      `purlin:spec` or `purlin:build` finds a number written twice or a test comment whose
      proof's wording changed since it was marked, the agent shows the plan (the spec lines and
      the test comments in this checkout that would change, the side not already on the default
      branch moving) and asks `Do it? [y/N]`; a script with a dry run does the edit on yes.
      Comments on another person's branch are named, never touched. Nothing is renumbered
      without asking.
    - **A hand check at the gate `passed` is listed as not checked** (answered on the plan's Q1):
      the release goes ahead, prints one line naming those rules, and the package lists them as
      not checked.
    - *Amended by 106:* there is no release step and no `passed/<version>` tag; `purlin:sign` builds the package from the committed evidence.
104. **A team's collaboration is a rule** (added 2026-10-01). Purlin's success needs three
    people working concurrently through git to reach a signed release. In the owner's words:
    "we can just test if we successfuly complete the collaboration without getting stuck or have
    errors or coruption". Smoothness is not judged.
    - **One rule, one scripted proof.** Product, QA and dev work in three clones of one repository
      on branches, with collisions forced (a number taken on two branches, a test marked against
      a proof whose number then moves), merged in both orders, and reach a release signed at the
      gate `signed`. A script drives the people; it runs in every sweep.
    - **What completes means, each checked by the script:** the release carries
      `signed/<version>`, and the committed evidence package describes the tagged commit and
      checks intact; no step stops for anything Purlin's output and docs do not give; no command
      fails unexpectedly and every warning raised along the way is resolved by the end; no spec
      holds a number twice or a merge-conflict line, every test comment is tied, each test's proof
      has the wording it was marked against, each spec's highest-number lines cover its numbers,
      and the package lists every rule.
    - **The run with real AI sessions stays a sanity check the owner runs on demand**, as decision
      94 placed it; it is not a proof.
    - Planned after the second QA and product check reports, so its findings shape the scenario.
105. **The answers to the second QA and product check** (added 2026-10-01), to
    `sanity-qa-product-2.md`, a cloud run in which product, QA and dev reached a signed release.
    - **The signer signs the run they are shown.** The developer runs `purlin:test --release` on
      the release branch. That run writes fresh results for every rule at the release commit and
      keeps nothing from earlier runs; the package records the run: who ran it (their git
      identity), on which machine, when, on which commit, and every result. The sign-off walk opens
      by naming it, as in `Tests run by dana.dev@labconnect.example on dana-laptop at 12:17 on
      1cf829e: 19 rules, all passed.`, and refuses when the branch has moved past that run or a
      result is not the release run's, asking for the release run again. The one signature covers
      the package and so that run.
    - **A test comment whose proof's wording changed since the test was last changed is caught by
      the status and every test run**, under `Left to do` as test comments to correct with
      `purlin:build`, and clears once the test itself changes; `purlin:build` checks that each
      marked test still shows its proof before it adds a comment.
    - **The audit keeps a rule's result until that rule's own test changes**, not the whole file.
    - **`.purlin/tests.md` is rendered on every run and never conflicts:** setup writes a git
      attribute that keeps one side on a merge.
    - **Fixed without a question:** a weak test under a rule with a hand check is shown and counted
      as weak, and its finding appears at the hand-check stop (N1); the first sign-off tells the
      signer to push the branch and the tag, and a later sign-off is refused until it holds the
      tagged commit (N2); the package's project name comes from the project's own files, and
      setup writes it (N5); the release run tells the developer to push the branch for the signer
      (N6); drift's wording line clears once the test changed (N9) and calls a number written twice
      a collision, not a change (N10); `purlin:sign --show` needs no key (N11); and N12's smaller
      items.
    - **Decision 104's scripted three-person test is built in the same round**, with these two
      cases in it: a test left on a moved proof, and a second signer. This round runs locally.
    - *Amended by 106:* `purlin:test --release` goes; the signer signs the committed evidence, and `.purlin/tests.md` goes.
106. **Purlin keeps the evidence and the sign-off, and tracks no release** (added 2026-10-01).
    In the owner's words: "the only thing purlin cares about is creating the curent state of the
    evidence, and the signing stage. everything else is just informative". This reverses the
    release step of decisions 103 and 105.
    - **No release step and no `passed/<version>` tag.** `purlin:test --release` goes. At the gate
      `passed` the status and the dashboard say whether every rule's tests pass on the committed
      evidence: met or not met. Nothing is called released or finished.
    - **The developer's hand-off is run and commit.** The developer runs every test, on this
      machine and the remote run for any other system, and commits the results that come back.
      That commit is ready for sign-off. QA runs no tests.
    - **The sign-off builds the package.** At the gate `signed`, `purlin:sign` reads the committed
      evidence, refuses and names what to run again when a result was not taken on this exact
      version of the code, opens by naming who ran the tests, where and when, builds the evidence
      package, walks the stops, and takes one signature over the package. The first signature
      writes `signed/<version>`, so anyone can find what was signed. Decision 105's "the signer
      signs the run they are shown" holds, the run being the committed evidence.
    - **Remote results count only when taken on the same version of the code** as the rest.
    - **A hand check's note is asked for and not required**; an empty answer is recorded as
      `no note`.
    - **The committed test table `.purlin/tests.md` goes.** Outside tools read the raw evidence
      files and the evidence package, whose formats are versioned for them; people inside the
      project use the status and the dashboard.
    - **The check for a test whose proof was reworded applies to every test now**: the build reads
      and fixes the roughly 198 tests in this repository whose proof was reworded after the test
      last changed, so the check starts clean.
107. **An anchor rule with nothing to check passes, and says so** (added 2026-10-01). It
    answers what decision 101's signature as not applying did before decision 103 removed it.
    - **An anchor's rule is written to hold across the whole project, as "for every X in the
      project, Y holds", so a project with no X has nothing to break it.** In the owner's words:
      "remote anchors have to be written such that the proofs pass when the project does not have
      functions that match the test." It is the anchor author's job, and the quality guide
      teaches it.
    - **When its test finds nothing to check, it skips with a reason**, through the test tool's
      own skip, as in `nothing to check: this project has no screens`. Purlin counts the rule as
      met and shows the reason on the status, the dashboard and in the evidence package, so the
      signer sees the rule was not exercised.
    - **No project-side way to say a pulled rule does not apply.** A pulled rule that fails here is
      a problem to raise with its authors.
    - **Only an anchor's rule counts a skip that starts `nothing to check:` as met**; on a project's
      own rule the skip reads as not run, its reason kept (answered on the d105 plan's Q2).
    - **Only the sign-off requires every result to be taken on this exact version of the code**;
      the status keeps counting a result while nothing its feature covers changed (the plan's Q1).
108. **No gate: two facts, the tests and the sign-off** (added 2026-10-01). Since nothing is
    signed rule by rule (decisions 103 and 106), `signed` is no bar each rule clears. This reverses
    the gate of decisions 103 and 106.
    - **The setting `gate` goes.** Setup asks for none; the upgrade from 0.9.5 and from any earlier
      0.10 build takes it out.
    - **Purlin shows two facts.** The tests: `met` when every rule's tests pass on the committed
      evidence, else `not met`. The sign-off: `signed 0.1.0 at a1b2c3d`, `signed 0.1.0, 4 commits
      since`, or `not signed`. The dashboard's two header boxes show these, in place of
      `gate: signed` and `no signed tag`.
    - **Any project may run `purlin:sign` whenever it chooses.** The walk, the package and the tag
      `signed/<version>` are as decision 106 has them.
    - **A hand check reads `checked at sign-off`** until someone signs; the sign-off records it.
    - **Mutation testing is a setting of its own**, no longer tied to a gate.
109. **The scope review's answers** (added 2026-10-01), to `scope-review.md`, judged against
    decision 106: Purlin keeps the evidence and the sign-off; the rest is informative.
    - **Cut with no question:** the gate (108), the release step (106), `.purlin/tests.md`, the
      runner's run on a pushed `signed/*` tag, the release wording left in drift, the release
      notes and the docs, and the empty folders `scripts/ci`, `scripts/hooks`, `scripts/proof`.
    - **Mutation testing is cut**, all three engines, its setting and its question. In the owner's
      words: "people can use mutation testing in the proof definition manually if they elect to".
    - **The AI audit stays an optional tool, and the sign-off walk stops only at hand checks**; the
      audit's findings, where it ran, are a list the signer can read. Skipping the audit no longer
      adds a stop per rule.
    - **Pulled anchors: drift and the status check the source and do not pull.** They say an anchor
      is behind its source (stale); only `purlin:anchor sync` pulls.
    - **Drift has one view, no roles**: rules and proofs changed, collisions and the renumbering
      offer, stale test comments, stale anchors; lines the status already prints are dropped.
    - **The dashboard keeps:** the board and a rule's own page; the two facts and the count boxes;
      the theme button; the per-system boxes; specs grouped by folder with a count and no progress
      bar; the badges on a rule's row; the hovers. **It cuts:** the filter buttons, the live age
      and the reload (a static `Data from <time>` stays), the links to the git host, unfolding a
      rule under its row, and the tabs (a rule's page has `Back to the board`).
    - **`purlin:export` folds into the sign-off**; checking a package against its fingerprint stays
      as an option of `purlin:sign`.
    - **`purlin:spec-from-code` stays a separate, optional skill**, out of the core docs, so its
      instructions load only when it is used.
    - **The upgrade is from 0.9.5 only**; this repository's own settings are fixed by hand once.
    - **The remote runner is set up when a proof first needs it.** Setup never asks; the status
      names proofs tagged for a system this machine is not; the first `purlin:test --remote`
      writes the runner file for the project's git host, shows it, asks to commit it, then runs.
      GitHub and Azure DevOps both stay.
    - **The settings file holds Purlin's version and the test commands only.** The git host is read
      from the remote and the project's name from its own files each time; setup asks only whether
      it may commit what it wrote.
    - **Purlin's checks on itself are trimmed** to what protects what a user runs: no emoji in
      output, the security rules for the languages Purlin's scripts use, the version check; each
      skill's wording rules become one short list of the commands and files it must name.
    - **The docs become about eight pages** (how it works, getting started, specs and anchors,
      running and evidence, working together, the sign-off with QA and regulated use, upgrading,
      the dashboard) **and the deck is rebuilt** for the two facts.
110. **How Purlin shows that tests work: plain checks and one targeted break per proof**
    (added 2026-10-01), after research the owner asked for: coverage tells little (Inozemtseva and
    Holmes, ICSE 2014); breaking the code on purpose tracks real faults (Just et al., FSE 2014);
    at scale it is done only on what changed (Google, Petrovic et al., TSE 2021) and with few,
    targeted, model-written breaks (Meta's ACH, FSE 2025; LLMorpheus); a model judging a test is
    the weakest signal; tests written by an AI are often tautological.
    - **`purlin:audit` holds all of it and is run by hand.** In the owner's words: someone "can use
      only spec and build for a while, and then say.. iterate with build and audit until you get
      strong proofs and tests for 80% of rules or more". The audit reports the share of rules it
      found strong, so such a target can be checked. Nothing blocks on it.
    - **Plain checks, in code:** a test with no assertion; an assertion that cannot fail; an error
      swallowed; an expected value computed by the code under test; a mock of the very thing the
      rule is about; and, from the spec, a concrete value the proof names that the test does not
      hold. 0.9.5's hollow-test checks return as code, not as words to a model.
    - **One targeted break per proof:** for each proof whose test or covered code changed since
      the audit last read it, the model makes the smallest change to the code that would violate
      the proof, the proof's own test runs against it, and the code is restored. A test that still
      passes is weak, with the break as the evidence. No mutation tool, any language.
    - **The model's reading becomes the explanation** of a finding, not the evidence alone.
    - **The docs gain a page on the audit**: what it checks, why, the research and the reasoning
      behind this path, with the sources.
    - **The evidence package records who did what, from git:** who wrote each rule and proof, who
      last changed each proof and each test, with commits. Nobody does anything extra.
    - **A hand check always shows its last note**, with the version it was signed at and how many
      commits have come since; the reader judges whether it still holds.
111. **The install the docs give is proven** (added 2026-10-01). A spec, `install`, holds that the
    README's and the getting-started page's install commands work. Its test reads the commands out
    of both pages and runs them with the real `claude` program in a fresh project, the marketplace
    address swapped for this checkout (a separate proof holds the pages' address is this
    repository's). Without a model it checks the plugin is installed and enabled and every skill
    landed; with one prompt to the smallest model it checks Claude Code offers every Purlin skill.
    In the owner's words: "make sure the skills are PRESENT in the AI based on the install
    commands.. make that as cheap as possible". Like any test, it reruns only when what it covers
    changed. The install leaves the person's own Claude Code settings as they were.
112. **A weight pass on Purlin's own specs** (added 2026-10-01). After decisions 100 to 111 the
    specs held about 700 rules and 1,800 proofs, heavy for the product. Each rule was kept only where
    it protects the evidence, the sign-off, the collaboration, the audit's correctness, safety or
    security; rules pinning the wording of one command's messages merged into one; cosmetic detail,
    edge cases no user meets and repeats were deleted; each kept rule keeps one to three proofs.
    The specs went from 698 rules to 408 and from 1,792 proofs to 823. The owner's calls:
    - **One project-wide rule against emoji** in skills, the agent and output stands; each skill's
      own no-emoji rule and its line limit go.
    - **The dashboard's two look rules stay**: the design (brand colours, no shadow, no gradient,
      the allowed glyphs) and readability (phone to wide screen, both themes, no sideways scroll, no
      value split across lines, 7 to 1 contrast).
    - **The audit's limit of four model calls at once is no longer a rule.**
    - **Cut:** SQLite installed on the Windows runner, the doctest switch in the suggested Python
      command, and runs outside a git repository.
    - **As recommended:** the upgrade's printed advice and its no-scope warning, setup's closing
      lines and drift's grouped network check are no longer rules; one Windows proof per rule where
      Windows differs; the guard that never overwrites a person's signing key, a sign-off counting
      after its key is deleted, and the status working in a project never set up all stay. The
      drift skill's instructions lose the role views decision 109 removed.
113. **A spec ahead of its code is reported, not warned of** (added 2026-10-01). Writing a spec
    before its code is the normal order, so a `> Scope:` naming files git does not have yet is one
    line per spec, as information: `states: 3 files its scope names are not written yet: facts.py,
    project.py, wording.py. Run purlin:build states, or correct the path with purlin:spec states.`
    It names the build first and the spec second, since Purlin cannot tell a file not yet written
    from a typo. This replaces the per-file warning of decision 97 that sent the person to
    `purlin:spec`.
114. **The dashboard page is refreshed with its data** (added 2026-10-01). Setup copied the page
    once, so after an upgrade an old page could not read new data and showed a schema notice. Now
    whenever a Purlin command writes the page's data, it also writes the page where the project's
    copy differs from the plugin's, so the page and its data always come from one version. The
    data stays a snapshot of the last command, with its time and the uncommitted-changes notice.
44. **A clean release.** 0.10.0 carries nothing that represents earlier functionality: no
    code, spec, test, fixture, committed evidence, workflow, plan or table of retired words.
    `RELEASE_NOTES.md` is the one place history is kept, and what an upgrade from 0.9.5
    needs is the one exception in code. This decision is applied last, as a sweep.


---

# Part A: the design

*Superseded in full by decisions 23 to 106; read references/glossary.md and references/hard_gates.md for what holds.*

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

*Superseded in full by decisions 23 to 106; read references/glossary.md and references/hard_gates.md for what holds.*

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

*Superseded in full by decisions 23 to 106; read references/glossary.md and references/hard_gates.md for what holds.*

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
