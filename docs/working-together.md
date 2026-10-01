# Working together

For a team where more than one person decides what the software must do: product, developers
and QA.

Purlin holds one thing everyone shares, the spec. Product, developers and QA all work in Claude
Code on a checkout of the repository, and `purlin:drift` is how each catches up after a pull.
Every change to a spec is a commit, so git says who wrote each line, and the evidence package
carries those names.

Nothing is signed while the specs change. Product, QA and the developers improve rules, proofs
and tests together, each on their own branch; the status and the dashboard show the state, and
`Left to do` lists only work. A person signs once everybody is done:
[sign-off.md](sign-off.md) is that walk.

## Product

**What you need.** A checkout and the plugin. Describe a feature in plain language, a sentence,
a ticket or a list of acceptance criteria, and `purlin:spec` turns it into rules, shows them
with their proofs, and asks whether to change any before it saves the spec. It never starts
building.

**What you see.** The dashboard states the two facts, `Tests` and `Sign-off`, and its boxes
count the rules whose tests pass, `Passing`, and, where the audit read a rule, the rules it
found strong, `Strong`. After a pull, `purlin:drift` tells you which rules it added, changed
or removed:

```
Since your last pull, 0 seconds ago (b9f91d5..1af085f, 2 commits).
2 rules added: export RULE-1; login RULE-4.
1 rule changed: login RULE-2.
```

## QA

**What you need.** A checkout and the plugin. You write and review the proofs: a proof says in
plain language how a rule is shown, and
[spec_quality_guide.md](../references/spec_quality_guide.md) is the guideline an AI draft is
held to.

**What you work.** You improve the proofs alongside product and the developers. Adding a case
is plain language: say "it should also reject an expired token" to `purlin:spec` and the proof
line is written into the spec with the next free proof id; the test arrives on the next
`purlin:build`, which is how QA's judgment reaches the code without QA writing it. `Left to do`
names the command for every other kind of work.

You run no tests for a sign-off. Once the developer has run every test and committed the
results, `purlin:sign` names who ran them, where and when, stops at each hand check, where you
may type what you saw, and takes one signed commit over the whole evidence package; the first
sign-off of a version writes the tag `signed/<version>` and you push it.
[sign-off.md](sign-off.md) takes you from acceptance criteria to that signature.

## The developer

**What you need.** A checkout and the plugin.

**What you run**, in this order, at the start of a session:

```
purlin:drift                what changed since your last pull
purlin:anchor sync <name>   when a pin is behind
purlin:spec <name>          when a rule is missing or wrong
purlin:build <name>         the code and its marked tests
purlin:test                 the tests the change touched; --commit commits the work and the evidence
purlin:audit                the tests, then whether they would catch a bug
```

Then you push. The hand-off to whoever signs is run and commit: `purlin:test --all --commit`,
and `purlin:test --remote` where a proof is tagged for another operating system.

You may also be the person who signs. Signing is logged, not policed: the sign-off records your
name and email as git holds them and the fingerprint of your key, and Purlin does not decide
who may sign.

## A rule from a pinned anchor

A rule that came from a pinned anchor belongs to the anchor repository, whoever wrote it. A
change to it is a pull request against that repository, and `purlin:anchor sync` brings it back
once it merges. Like every anchor rule it holds across the whole project, and its tests check
the whole project.

## Drift

`purlin:drift` reports what changed since the last git action that brought changes into your
checkout: the newest pull, merge, rebase, checkout or reset in git's log of HEAD. After a clone
with nothing later, it reads the last 20 commits, or every commit when there are fewer. It
writes nothing, fetches nothing and judges nothing. It has one view, the same for everyone:

| What it names | As |
|---|---|
| Rules added, changed and removed | `1 rule added: login RULE-3.`, `1 rule changed: login RULE-1.`, `1 rule removed: cart RULE-2.` |
| Proofs added | `2 proofs added: login PROOF-5, PROOF-6.` |
| A proof whose wording changed, with both wordings | `login PROOF-1 changed: it read "An age of 150 minutes" and now reads "An age of 90 minutes".` |
| A proof whose text moved to another id | `login PROOF-4 moved to PROOF-6.` |
| A number a spec writes twice, and which line moves | `login: PROOF-4 is written twice. The line on origin/main keeps PROOF-4; renumber the other to PROOF-5 and move its test comments with it: "B".` |
| A test comment whose proof was reworded after the test last changed | `tests/test_login.py:1 names login PROOF-4, whose wording changed after the test was last changed in 1cf829e: it read "A" and now reads "B". Run purlin:build login to make the test show it; the line clears once the test changes.` |
| A pinned anchor behind its source | `anchor security_baseline: the pin 71abd36 is behind its source, now b3a6387. Run purlin:anchor sync security_baseline.` |

Where nothing moved, it says so: `No rule was added, changed or removed since your last pull.`
Drift checks an anchor's source without pulling it. Where it names a number written twice, it
says how old this checkout's copy of the default branch is, so you can fetch and run it again:

```
origin/main was last fetched 3 days ago, and drift does not fetch. Run git fetch, then purlin:drift again.
```

Run it right after you pull, merge, rebase or check out someone else's branch.
`--since <N>` reads the last N commits and `--since <YYYY-MM-DD>` every commit since that date.

## Working at the same time

QA reading version N of a rule while a developer builds N+1 is normal: nothing is signed until
everybody is done, so neither waits on the other. The reports a run reads are under
`.purlin/runtime/`, which git ignores, so two people running tests at once do not disturb each
other.

Three things can collide, and each has one answer.

**Evidence.** Evidence is one file per feature per source, so two branches that both commit one
feature's evidence conflict on that file. Whoever runs `purlin:test --commit` commits the
evidence, on the branch they are on: it describes that branch's code. When a merge conflicts in
`.purlin/evidence/`, take either side and run `purlin:test --commit`: the file is written
again, keeping each audit result whose rule, proof and test are unchanged.

**A number taken twice.** Two branches can take the same rule or proof number before either
fetched. The number already on the default branch keeps it, and the rule or proof from the
branch not yet merged moves to the next free number. `purlin:drift` after the merge names every
number written twice and which line moves; until it is fixed, every rule of that spec reads
`failed` and `Left to do` reads `1 spec to repair: purlin:spec`. `purlin:spec` shows a dry run
of the renumbering, the spec lines and the test comments in this checkout that would change,
and asks `Do it? [y/N]`. Comments on another branch are named, never touched.

**A proof reworded under its test.** When a proof's wording changes after its test was last
changed, the status, every test run and drift name the test comment, and `Left to do` counts
it as a test comment to correct, with `purlin:build`. It clears once the test itself changes.

## More than one checkout

Each checkout of a repository, a worktree included, has its own results, its own status and its own dashboard. Nothing is shared until the work is merged. After you merge work from a worktree, run `purlin:status` in the main checkout: that brings its status and dashboard up to date.

The dashboard's header names the branch and the commit its data was written for, as
`main at a1b2c3d, written 06:42 EDT`, so a page is never read as another checkout's. A Purlin tool
call names the folder it works in; a call that names none is refused with the fix.

## Next

- Writing the rules themselves: [specs-and-anchors.md](specs-and-anchors.md)
- What a run writes and which results count: [running-and-evidence.md](running-and-evidence.md)
- The sign-off: [sign-off.md](sign-off.md)
