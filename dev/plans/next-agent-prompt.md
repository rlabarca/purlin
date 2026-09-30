# Prompt for the next session: build decision 100, prove it on the Mac, then the QA sanity check

Paste everything below the line into a new session opened in
`/Users/richlabarca/LocalCode/purlin`.

---

You are continuing Purlin 0.10.0, a Claude Code plugin for spec-driven development that uses
itself. Decisions 60 to 99 are built and proven on local `main`: 891 rules, all passing on the
Mac and, where tagged, on Windows. Decision 100 is closed and nothing of it is built. Your job
is to build decision 100, prove it on this Mac, and then stop and ask me to describe the QA
sanity check. Tokens are short: spend them on the build, not on ceremony.

## Read first, in this order

1. `dev/plans/three-levels.md`, decision 100 in full, then decisions 94 to 99 for the words and
   shapes already settled (search `94. **`). The later decision holds.
2. `dev/plans/handoff.md`: "Where the tree is", "What is left" item 1, "How to work".
3. `dev/plans/phase3-plan.md` section 4: which lane owns which file. Reuse that ownership.
4. `CLAUDE.md`, `references/spec_quality_guide.md`, `references/writing_style.md`.

Read nothing else in `dev/plans/` unless a question sends you there.

## What decision 100 is

An anchor is a set of rules for the whole project.

- Every anchor is global: its rules are proven by tests that run across the whole project, tied
  to no feature. A rule that cannot be checked that way is not an anchor rule; it is an
  ordinary rule in each feature's spec that needs it.
- A spec names no anchor. `> Requires:` and `> Global: true` go. A spec that still carries
  either is warned of, with its fix, in the shape of decision 97's spec mistakes.
- Each anchor rule is counted, audited and signed once. A feature's row counts its own rules
  only: the counts `(+8)` and `(+8 shared)` go, and a feature whose 11 rules pass reads
  `11 of 11`.
- On the dashboard, anchors stand in a section of their own above the spec table, headed
  `Anchors`, same columns, same filters; `(anchor)` after a name goes.
- Any change to any tracked file ends an anchor's results and its signatures, except the
  records Purlin itself writes: run results, signatures, the evidence package. An anchor names
  no covered files.
- A rule of a pinned anchor that no project-wide test can show is checked by hand and signed.
- An anchor's tests are judged by the AI audit alone: no code is broken on purpose for an
  anchor and no test strength is shown for one.

## How to work

- One planning agent first. It cuts the work into lanes in which every file has one owner,
  using `phase3-plan.md` section 4, and fixes word for word every line two lanes share. Expect
  about 8 to 12 lanes: the spec reader and the two formats, the states and the summary, the
  evidence and its fingerprint, signing, the run, the evidence package, the dashboard, the
  upgrade from 0.9.5, the skills and the agent definition, the references and the docs. Leave
  out any lane with no work.
- Then one workflow: the lanes at once, each in its own worktree under
  `/Users/richlabarca/LocalCode/purlin-wt/<name>`, then one integration agent alone. Every
  agent is Opus. **No review agents.** Each lane ends on its own self-check: every proof one
  case in at most 60 words with a marked test of its own, no rule or proof number reused
  (`> Highest-Rule:` and `> Highest-Proof:` are raised), no generated file staged, its most
  important change broken on purpose and seen to fail.
- The branch `lane/anchors-section` (worktree `purlin-wt/anchors-section`, two commits, not
  merged) holds a first build of the dashboard's `Anchors` section made before decision 100.
  It keeps the per-feature counts. The dashboard lane starts from it and brings it to the
  decision.
- This repository has two anchors. The security one is already global and stays an anchor. The
  one about the spec format was required by one feature and its rules are about one piece of
  code: make it an ordinary spec, unless you find a reason it must stay an anchor, and tell me
  which you did.
- Frozen during the fan-out: `dev/skill_checks.py`, `dev/mcp_project.py`,
  `dev/sign_project.py`, `dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`,
  `dev/fake_claude.py`. If one must change, that lands alone, first.
- A format that changes follows `CLAUDE.md` "Format reference versioning" in the same commit.
  Clean release: what is retired is deleted outright, with no test that it is absent; only
  `RELEASE_NOTES.md` keeps history, and what an upgrade from 0.9.5 needs is the one exception.
- Put `/opt/homebrew/opt/dotnet@8/bin` and the repository's `.venv/bin` first on PATH for every
  test run. Before an agent breaks code on purpose, it makes sure the break cannot reach the
  real `claude` program or any real service.
- Push nothing, tag nothing, run no `purlin:audit` and no `purlin:sign` against this
  repository. **No remote run on Windows in this session.**

## Questions to me

Ask only what changes what the product does and that decision 100 does not settle. Ask with
the question UI, from the root, in plain words, with the recommended option first and what I
need to answer inside the question. Do not ask about words: where a line a person reads
changes, write it in the shape of the lines decisions 94 to 99 already give, build it, and list
every such line for me at the end. If nothing needs asking, ask nothing and build.

## Done means

1. Every lane merged into local `main` by fast-forward.
2. `bash dev/run_tests.sh` ends with 0 failed.
3. `python3 scripts/run/purlin_run.py --test --all` ties every marker, and no rule reads
   `failed`, `partial` or `no test`. Rules that wait for Windows may wait: say how many. Then
   the same with `--commit`.
4. The dashboard looked at with playwright from the `.venv`, headless, dark theme, at 1500,
   1024 and 390 pixels: the `Anchors` section above the spec table, a feature's row counting
   its own rules only, no sideways scroll.
5. `dev/plans/handoff.md` brought up to date in a few lines: where the tree is, that decision
   100 is built, that Windows has not been run since, and what is left.

Leave for later, and say so in the handoff: the remote run on Windows, the two docs
screenshots, the slide on anchors, and a full reading of the docs pages. A page that states
something decision 100 makes false is corrected now; nothing else on it is touched.

## Then stop and ask me

Report in a short message: the counts from steps 2 and 3, what became of the spec-format
anchor, every line a person reads that you chose, and anything you left unbuilt. Then ask me,
in one plain question, to describe the QA sanity check I want run: who the person is, what
project they start from, what they try to do, and what I want to learn. Wait for my answer and
start nothing else.
