# Prompt for the next session: a new user follows the docs, then the proofs are rewritten

Paste everything below the line into a new session opened in
`/Users/richlabarca/LocalCode/purlin`.

---

You are running a sanity check on Purlin 0.10.0, a Claude Code plugin for spec-driven
development, before its release. You have two jobs, in this order: **Part 1**, a sanity
check, and **Part 2**, rewriting this repository's required proofs to the proof guideline. Do
not start Part 2 until the Part 1 report is written, because Part 2 needs you to read what
Part 1 forbids.

# Part 1: the sanity check

This is the second of several checks. The first asked, as a
skeptical developer, why anyone needs Purlin. This one asks: **can a person who has never seen
Purlin get from nothing to a proven rule using only what the docs say?**

Read `dev/plans/handoff.md` first, in full. It says where the project stands and how I want
work done. Then do this check. Do not read `dev/plans/three-levels.md` or any other plan until
the check is finished: the point is to meet the product the way a stranger does.

## What you may read, and what you may not

You play a developer who has just been handed Purlin. You may read only what that person
would have:

- `README.md`
- everything under `docs/`
- what the commands themselves print

You may not read the source under `scripts/`, the specs under `specs/`, the skills under
`skills/`, `agents/purlin.md`, anything under `references/`, or anything under `dev/`, until
the check is finished. If the docs send you to a page under `references/`, note that they did,
and then you may read that one page.

## What to do

Work in a scratch folder outside this repository. Change nothing in this repository. Push
nothing, tag nothing, and run no `purlin:audit` and no `purlin:sign` against this repository.
In your scratch projects you may run anything, including the audit and signing, since that is
part of what a new user would try. Where a step needs a model, use the real one only if it
costs a handful of calls; say how many you made.

Run the scripts directly from this checkout, which is how the plugin's commands work
underneath: the docs name the commands as `purlin:init`, `purlin:test` and so on; find out from
the docs alone how a person runs them, and note it if the docs never say.

Walk these paths, each in its own fresh scratch project, following the docs to the letter and
doing nothing the docs do not tell you to do:

1. **The ten-minute path**, exactly as the README gives it, in a small Python project with
   pytest. Time it. Note every moment you had to guess.
2. **The same in a second language**, a small JavaScript project with Vitest or Jest, since
   the docs promise one comment above a test works in any language.
3. **A project that already has tests**: twenty existing tests, no specs. Follow what the docs
   say to bring it under Purlin. Count what you had to change in the tests themselves.
4. **Raising the gate**: take the project from path 1 from `passed` to `strong`, then to
   `signed`, following the docs. Write a proof. Run an audit. Sign a rule. Produce the
   evidence package. Note what each step asked of you that the docs had not prepared you for.
5. **Things going wrong**, as a new user meets them: a failing test; a comment that names a
   rule that does not exist; a typo in the comment; a rule with no test; code changed after
   the tests passed; a test deleted; the settings file deleted. For each: what Purlin printed,
   whether it told you what to do next, and whether doing that worked.
6. **The dashboard**: open it from the scratch project at each stage and say whether what it
   shows matches what the terminal said. Look at it at 1500 and at 390 pixels wide, with
   playwright from this repository's `.venv`, headless.
7. **Leaving**: remove Purlin from the project from path 1, following the docs. Say what was
   left behind.

## What to write down

For every step of every path, as you go:

- what the docs told you to do, quoted, with the page;
- what you typed;
- what happened, quoted;
- whether it matched what the docs said would happen;
- how long it took, and how sure you were that you had done the right thing.

## What to give me at the end

One report, saved as `dev/plans/sanity-2-new-user.md` (the one file you may write in this
repository), and the same in your reply, shorter. In this order:

1. **The verdict in three sentences.** Could a stranger do it? How long did the ten-minute
   path take? What was the worst moment?
2. **Where the docs were wrong**: they said one thing and the product did another. Quote both.
3. **Where the docs were silent**: you had to guess, or read something you were not supposed
   to. Say what you guessed and whether you guessed right.
4. **Where the product was unclear**: a message you could not act on, a number you could not
   interpret, a word nobody had explained.
5. **Where Purlin touched more than it promised.** The README says how little Purlin puts in
   a project. List every file it created or changed in each scratch project, and compare.
6. **What worked well.** Say so plainly where it did. I need to know what to leave alone.
7. **Questions for me.** Every finding that needs a decision, written so that a person who
   knows only the workflow (spec, build, test, audit, sign, tag) can answer: what the thing is
   for in one to three plain sentences, then the question, then two to four options, each with
   what it would mean for a user and for the code. Most basic first. Always include the option
   that removes the thing in question. No function names, no file names, no term you have not
   explained.

Only after the report is written, read the code and the plans to tell me, for each finding,
whether it is a fault in the docs or a fault in the product. Add that as a last section and do
not change the findings above it.

Put the questions to me with the question UI when Part 2 is done as well, so that I answer
once. Change nothing on account of Part 1's findings until I have answered.

# Part 2: every required proof is rewritten to the guideline

## Why

A proof says, in plain language, how a rule is shown to be true. I want QA to write and review
proofs beside product, so a proof has to be something a person who cannot read code can judge.
The guideline is `references/spec_quality_guide.md`, the section "Writing proofs". Three of
this repository's specs were rewritten to it as examples: `specs/mcp/drift.md`,
`specs/anchor/upstream.md` and `specs/mcp/config_engine.md`. Read the guideline and those
three before you begin; they are the standard.

The rest of this repository's proofs were written by an agent in the test's own words ("Wrap
the move in a recording spy and verify the spy saw at least 1 call..."). When `purlin:audit`
runs, the model reads each test against its proof and against the guideline, and it will find
fault with proofs written that way.

## What is required

A proof is **required** where its rule's level asks for the audit: the rule is unmarked, or
marked `[level: strong]` or `[level: signed]`. This repository's gate is `signed`, so an
unmarked rule takes it. A rule marked `[level: passed]` needs no proof, and its proofs are out
of scope: leave them as they are. That leaves 558 proofs to rewrite, across 30 specs. The
largest are `states` (84), `run_script` (55), `signatures` (48), `gate_check` (44),
`scaffold` (37) and `ai_audit` (30). Count them yourself before you start and tell me if your
count differs.

## How each proof is rewritten

For each required proof, in this order:

1. Read the rule it serves, the proof as it stands, and the test or tests that carry its
   marker.
2. Rewrite the proof's words to the guideline: what is done, what is observed, the expected
   value; at least one failure case or boundary where the rule refuses, limits or expires
   something; no file path of the source, no function name, no class, no test framework's
   name; what a user or a caller of the system would see. A path or a line the software
   itself writes, reads or prints is output a caller sees, and a proof may name it.
3. **Keep the proof's id, the rule it serves, and every marker.** Change no rule's words and
   no test's code in this step.
4. **The proof claims only what the test shows.** Read the test and confirm it carries out
   the rewritten proof. Where the test shows less than a good proof would claim, make the
   proof claim what the test shows, and add the gap to a list: the spec, the proof, and what
   a good proof would also claim.
5. Where one proof really holds several separate things, leave it as one proof and say so in
   the list. Splitting a proof changes ids and markers, which is a decision for me.

Then close the gaps you listed: for each, write the missing assertion in the test, against
real behaviour and not a stand-in for the code under test, and raise the proof to claim it.
Where closing a gap would need more than a few lines of test, leave it on the list for me with
what it would take.

## How to work

As `dev/plans/handoff.md` says: Opus agents, each in its own worktree under
`/Users/richlabarca/LocalCode/purlin-wt/<name>`, merged into `main` by fast-forward, two
writing at once at most and only where their files do not overlap. One agent per spec for the
six largest; group the smaller specs by folder. Give each agent the guideline, the three
example specs, and this section, word for word.

Each agent's acceptance: `bash dev/run_tests.sh` passes with 0 failed; this repository run
through its own tool (`python3 scripts/run/purlin_run.py --all --test`, with the PATH the
handoff gives) ties every marker and every rule passes its tests; the evidence that run writes
is removed and not committed; no rule's words changed (`git diff` of each spec shows changes
on proof lines only, which the agent confirms and reports); `git status` is clean. Never
weaken an assertion to make it pass, and never edit a count to make a sweep green.

Rewriting a proof puts its feature's evidence out of date, because the spec changed. When
every spec is done and merged, run this repository through its own tool once with `--commit`,
so the committed evidence is current again.

Do not run `purlin:audit` and do not sign anything. I will run the audit myself when the
sanity checks are done. Push nothing.

## What to give me at the end of Part 2

Add to your reply, and save as `dev/plans/proofs-rewritten.md`:

1. **The counts**: proofs rewritten, per spec; proofs left alone because their rule is marked
   `[level: passed]`; the full sweep's result; markers tied; rules passing.
2. **Ten before-and-after pairs**, quoted in full, chosen to show the range: the easiest, the
   hardest, and the ones you are least sure of.
3. **The gaps**: each one closed, with the assertion added; each one left, with what it would
   take.
4. **Proofs that hold several things**, which I may want split.
5. **Rules you think are wrong or unclear**, found while reading them against their tests.
   You changed none; list them.
6. **Questions for me**, in the same form as Part 1's, put to me with the question UI
   together with Part 1's.
