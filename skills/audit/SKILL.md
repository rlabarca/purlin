---
name: audit
description: Run the tests, the heuristic spot tests, one planted bug per proof and the model's reading, then write what it found into the evidence
---

Show how much the tests are worth. The audit runs the marked tests, then for each rule that
passes: the heuristic spot tests, which read each test as text; one planted bug per proof, to see
whether the proof's own test catches it; and the model's reading, which explains what was found.
It writes what it found into the evidence and reports the share of rules it found strong. A person
runs it by hand, when they choose; nothing waits on it, and a weak rule stops no sign-off.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below is
relative to the plugin root; see `references/purlin_commands.md#path-resolution`. Pass
`project_root` on every Purlin tool call: the top folder of the git checkout you are working in.
**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:audit                    Run what the change touched, audit, write the evidence
purlin:audit <feature> [...]    One feature, or several
purlin:audit --all              Run every feature, and read every passing rule again
purlin:audit --commit           Commit the work and the evidence the run wrote
purlin:audit --arm-timeout <seconds>  Give each suite, and each planted bug's test run, longer
```

Plain language reaches the same place: "audit this", "how strong are the tests". A team may set
itself a target, such as building and auditing until 80% of rules read strong; the audit's last
line is the number to hold against it.

## Step 1: run

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py" --audit --project-root .
```

Add `--arm-timeout <seconds>` when the person gave it. Add `--all` for `purlin:audit --all` and
`--feature <name>` for each feature named; with neither, the run covers the features `purlin:test`
would select. It runs the tests, then reads each rule whose tests pass, that has a proof with a
test, and whose text, proofs, tests or covered code changed since its last audit:

1. **The heuristic spot tests**, with no model: a test that checks nothing, a check that cannot
   fail, a swallowed error, a test that checks the code against itself, a test that replaces what
   it is testing, and a test that never checks the result the proof expects.
2. **One planted bug per proof** whose test or covered code changed since its last one. The model
   names the smallest change to the code that would break the proof; the change is made in a copy
   of the project, never in the project itself; the proof's own tests run there; the copy is
   removed. A test that still passes is weak, with the change as the evidence. No bug is planted
   for an anchor's proof or a `@manual` proof.
3. **The model's reading**, one `claude -p` call per rule, which explains what the first two found
   and decides nothing.

A rule reads `weak` when a spot test fires on one of its tests or a planted bug survived, else
`strong`. `references/review_criteria.md` is the one home of each check, the research behind it
and what the model is sent.

The run writes each feature's section and its `audit` into `.purlin/evidence/local/<feature>.json`
and prints `Evidence written to .purlin/evidence/local/<feature>.json.` It commits nothing unless
you add `--commit`, which commits under your own identity, and it never pushes.

The exit codes are in `references/purlin_commands.md`, "Exit codes": those of a test run, and
`1` where a file of the project changed while a bug was planted. What the audit found never sets
the code: a weak rule is listed, not failed.

## Step 2: read what came back

The audit prints one block per rule it read, then its cost, then the share, and the run ends on
the status, as every run does:

```
login RULE-2   weak
  tests/test_login.py::test_wrong_password: the test checks nothing.
  PROOF-2: the test still passes when src/auth.py:12 reads "return 200"
  PROOF-3: no bug was planted: the answer named no change.
The model was asked 31 times for 12 rules: $1.87 in all, $0.16 a rule.
The audit found 4 of 5 rules strong (80%).
```

- A line `<file>::<test>: ...` is a spot test's finding: fix the test.
- A line `PROOF-N: the test still passes when <file>:<line> reads "<line>"` is a planted bug the
  test did not catch: add the case that tells the right behaviour from that change.
- A line `PROOF-N: no bug was planted: <why>.` is not a finding and does not make the rule weak.
- `<check> is not read in <language> tests.` says a spot test does not read that language.
- `The model could not be reached: <why>. <n> rules stay not audited. Run purlin:audit again.`
  means `claude` could not be reached. A rule a spot test fired on is still written `weak`; any
  other rule prints `<feature> RULE-N   not audited` and gets no audit entry, since `strong`
  means the model's part of the audit ran.
- `The audit stopped: <file> changed while a break ran. Nothing in the project was written by the
  audit.` means a file changed under the run: leave the project alone while the audit runs, then
  run it again.

A finding is build work. `purlin:build <feature>` fixes the test, and the rule is read again by
the next `purlin:audit`. Never narrow a rule or a proof to make a finding disappear. What the
model cost is also written to `.purlin/runtime/audit_run.json`, which git ignores.

## Step 3: name the next step

Show the ending as the run printed it, then name the next step:

- A rule reads `weak`: `→ Run: purlin:build <feature>`, then `purlin:audit` again.
- `Left to do:` lists other work: `→ Run:` the command its first line names.
- Every rule read is strong and nothing else is left: say so, and name `purlin:audit --commit` to
  commit what the audit found where the person wants it kept.
