# Prompt for the next session: a new user follows the docs

Paste everything below the line into a new session opened in
`/Users/richlabarca/LocalCode/purlin`.

---

You are running a sanity check on Purlin 0.10.0, a Claude Code plugin for spec-driven
development, before its release. This is the second of several checks. The first asked, as a
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

Then stop and put the questions to me with the question UI. Change nothing until I have
answered.
