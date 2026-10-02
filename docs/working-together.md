# Working together

For a team where more than one person decides what the software must do: product, developers
and QA.

Product, QA and developers improve the specs together. Everyone works in Claude Code on a
checkout of the repository. After a pull, `purlin:drift` is how each catches up.

Purlin has no roles: whoever knows the answer edits the spec. Every change to a spec is a
commit, so git says who wrote each line. The evidence package carries those names.

**Nothing is signed while the work goes on.** Each person works on their own branch. The status
and the dashboard show the state, and `Left to do` lists only work. A person signs once
everybody is done. [sign-off.md](sign-off.md) is that walk.

## Product

**What you need.** A checkout and the plugin.

**What you do.** Describe a feature in plain language: a sentence, a ticket or a list of
acceptance criteria. `purlin:spec` turns it into rules and shows them with their proofs. It
asks whether to change any before it saves the spec. It never starts building.

**What you see.** The dashboard states the two facts, `Tests` and `Sign-off`. Its boxes count
the rules whose tests pass, `Passing`. Where the audit read a rule, they also count the rules
it found strong, `Strong`. After a pull, `purlin:drift` tells you which rules were added,
changed or removed:

```
Since your last pull, 0 seconds ago (b9f91d5..1af085f, 2 commits).
2 rules added: export RULE-1; login RULE-4.
1 rule changed: login RULE-2.
```

## QA

**What you need.** A checkout and the plugin.

**What you do.** You write and review the proofs, alongside product and the developers. A
proof says in plain language how a rule is shown.
[spec_quality_guide.md](../references/spec_quality_guide.md) is the guideline an AI draft is
held to.

To add or change a rule, a case or a proof, name the command:
`purlin:spec login: it should also reject an expired token`. A request typed without the command
may not reach it, and the agent may then edit the file by hand.
The proof line is written into the spec with the next free proof id. The test arrives on the
next `purlin:build`. That is how QA's judgment reaches the code without QA writing it.

`Left to do` names the command for every other kind of work.

**The sign-off.** You run no tests for it. Once the developer has run every test and committed
the results, you run `purlin:sign`:

- it names who ran the tests, where and when;
- it stops at each hand check, where you may type what you saw;
- it takes one signed commit over the whole evidence package.

The first sign-off of a version writes the tag `signed/<version>`, and you push it.
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
and your project's own run where a proof is tagged for another operating system.

You may also be the person who signs. Signing is logged, not policed. The sign-off records your
name and email as git holds them and the fingerprint of your key. Purlin does not decide who
may sign.

## A rule from a remote anchor

A rule from a remote anchor belongs to the repository that owns it, whoever wrote it. Your copy
is never edited in your project. A change is a pull request against the source, and
`purlin:anchor sync` brings it back once it merges.

Like every anchor rule, it holds across the whole project, and its tests check the whole
project.

## Drift

`purlin:drift` reports what changed since the last git action that brought changes into your
checkout: the newest pull, merge, rebase, checkout or reset in git's log of HEAD. After a clone
with nothing later, it reads the last 20 commits, or every commit when there are fewer.

It writes nothing, fetches nothing and judges nothing. It has one view, the same for everyone:

| What it names | As |
|---|---|
| Rules added, changed and removed | `1 rule added: login RULE-3.`, `1 rule changed: login RULE-1.`, `1 rule removed: cart RULE-2.` |
| Proofs added | `2 proofs added: login PROOF-5, PROOF-6.` |
| A proof whose wording changed, with both wordings | `login PROOF-1 changed: it read "An age of 150 minutes" and now reads "An age of 90 minutes".` |
| A proof whose text moved to another id | `login PROOF-4 moved to PROOF-6.` |
| A number a spec writes twice, and which line moves | `login: PROOF-4 is written twice. The line on origin/main keeps PROOF-4; renumber the other to PROOF-5 and move its test comments with it: "B".` |
| A test comment whose proof was reworded after the test last changed | `tests/test_login.py:1 names login PROOF-4, whose wording changed after the test was last changed in 1cf829e: it read "A" and now reads "B". Run purlin:build login to make the test show it; the line clears once the test changes.` |
| A remote anchor behind its source | `anchor security_baseline: the pin 71abd36 is behind its source, now b3a6387. Run purlin:anchor sync security_baseline.` |

Where nothing moved, it says so: `No rule was added, changed or removed since your last pull.`

Drift checks a remote anchor's source without pulling it. Where it names a number written
twice, it says how old this checkout's copy of the default branch is, so you can fetch and run
it again:

```
origin/main was last fetched 3 days ago, and drift does not fetch. Run git fetch, then purlin:drift again.
```

Run it right after you pull, merge, rebase or check out someone else's branch.
`--since <N>` reads the last N commits. `--since <YYYY-MM-DD>` reads every commit since that
date.

## Working at the same time

QA reading version N of a rule while a developer builds N+1 is normal. Nothing is signed until
everybody is done, so neither waits on the other.

Two people can run tests at once without disturbing each other. The reports a run reads are
under `.purlin/runtime/`, which git ignores.

Three things can collide, and each has one answer.

**Evidence.** Evidence is one file per feature per source. Two branches that both commit one
feature's evidence conflict on that file. Whoever runs `purlin:test --commit` commits the
evidence, on the branch they are on: it describes that branch's code. When a merge conflicts in
`.purlin/evidence/`, take either side and run `purlin:test --commit`. The file is written
again, keeping each audit result whose rule, proof and test are unchanged.

**A number taken twice.** Two branches can take the same rule or proof number before either
fetched. The number already on the default branch keeps it. The rule or proof from the branch
not yet merged moves to the next free number.

- After the merge, `purlin:drift` names every number written twice and which line moves.
- Until it is fixed, every rule of that spec reads `failed`, and `Left to do` reads
  `1 spec to repair: purlin:spec`.
- `purlin:spec` resolves the conflict git left, where both sides only added lines, and shows a
  dry run of the renumbering. It asks `Do it? [y/N]`. A line both sides changed is left for you
  to choose.
- Drift run before the merge is committed says `A merge is in progress and is not committed`.
- Comments on another branch are named, never touched.

**A proof reworded under its test.** When a proof's wording changes after its test was last
changed, the status, every test run and drift name the test comment. `Left to do` counts it as
a test comment to correct, with `purlin:build`. It clears once the test itself changes.

## More than one checkout

Each checkout of a repository, a worktree included, has its own results, its own status and its own dashboard. Nothing is shared until the work is merged. After you merge work from a worktree, run `purlin:status` in the main checkout: that brings its status and dashboard up to date.

The dashboard's header names the branch and the commit its data was written for, as
`main at a1b2c3d, written 06:42 EDT`. A page is never read as another checkout's.

A Purlin tool call names the folder it works in. A call that names none is refused with the
fix.

## Next

- Writing the rules themselves: [specs-and-anchors.md](specs-and-anchors.md)
- What a run writes and which results count: [running-and-evidence.md](running-and-evidence.md)
- The sign-off: [sign-off.md](sign-off.md)
