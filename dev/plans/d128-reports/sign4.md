# Decision 128, lane `sign4`: the report

Branch `lane/d128-sign4`, one commit of work on `main` at `ff3a7be98`, then this report.
Nothing is pushed, tagged or signed; no test reaches a real model; no test signs with any key
but the temporary ones the tests make. `main` had not moved at the rebase.

Acceptance: `dev/test_signatures.py` `90 passed`; `dev/test_skill_sign.py`,
`dev/test_purlin_docs.py` and `dev/test_export.py` `52 passed, 1 skipped`;
`bash dev/run_tests.sh --fast` `1118 passed, 9 skipped`, `Suites: 1 passed, 0 failed`.

## What was built

**1. The signer sees a finding cleared by judgment.** `scripts/review/sign.py`: `plan()`
gathers, from every rule of the package whatever its verdict, each sentence of its audit's
`no_bug` that reads `<PROOF-N> was settled with its test unchanged: it was judged to assert what
the proof names.` The sentence is matched against `audit_run.UNCHANGED`, the one home of it,
which `sign.py` now imports. `audit_list_lines(weak, judged)` prints, after every weak rule's
findings, one line per such proof:

```
  login RULE-2: PROOF-2 was settled with its test unchanged: it was judged to assert what the proof names.
```

The words are the plan's; the two leading spaces are the list's own indent, as the weak
rules' lines have it.

- **Where it stands: after the weak rules' findings, in the same list, with no heading of
  its own.** The weak findings are open and the judged lines are cleared, so they do not mix
  rule by rule, and each judged line carries its own sentence, so it needs no heading.
- **The question counts them** and is asked where no rule is weak too:
  `The audit's findings: 1 weak, 1 proof settled with its test unchanged. list / go on: `,
  `The audit's findings: 1 proof settled with its test unchanged. list / go on: `,
  `... 2 proofs settled with their tests unchanged ...`. Without that, a project with no weak
  rule would never show the line in the walk.
- **`--show`** prints the same header, `The audit's findings: <counts>.`, and the same lines,
  as it does for the weak rules.
- **It stops nothing**: no stop, no refusal (PROOF-286 signs through it).
- Another `no_bug` sentence, such as `No bug was planted: ...`, is not listed (PROOF-287).
- A hand check's stop is unchanged: it shows the audit's findings only where the rule is weak.

**Recording.** No format changes and no version is bumped. The package already carries
each rule's `no_bug` whole (`package_format.md`, Format-Version 14, whose `no_bug` row already
names "one per proof settled with its test unchanged"). The sign-off already records
`audit_list_opened`, and the list it records is now the one holding those lines
(`signature_format.md`, Format-Version 16: "whether the signer asked to see the audit's
findings", still true). The weak findings are recorded the same way: in the package, with the
sign-off recording whether the list was opened. Neither format file was touched.

## Rules and proofs, word for word

`specs/review/signatures.md`: `> Highest-Rule:` 138 to 140, `> Highest-Proof:` 280 to 289.

Reworded, RULE-115, was:
- RULE-115: Where the audit found any rule weak, the walk asks `The audit's findings: <n> weak. list / go on: `; `list` prints each weak rule with its findings, then asks `go on: `

now:
- RULE-115: Where the audit found any rule weak or a proof was settled with its test unchanged, the walk asks `The audit's findings: <counts>. list / go on: `, the counts `<n> weak`, then `1 proof settled with its test unchanged` or `<n> proofs settled with their tests unchanged`, each left out at zero and joined by `, `; `list` prints the list, then asks `go on: `

Its one proof, PROOF-230, still holds as written, and its test is unchanged.

Added:
- RULE-139: Each proof the audit settled with its test unchanged is listed among the audit's findings, whatever its rule's verdict, as one line `<feature> <RULE-N>: <PROOF-N> was settled with its test unchanged: it was judged to assert what the proof names.`, after every weak rule's findings, in `--show` as in the walk; it adds no stop and refuses nothing
- RULE-140: The sign-off records whether the list holding those lines was opened as `audit_list_opened`, and the package holds each such sentence under its rule's audit `no_bug`
- PROOF-281 (RULE-115): `login RULE-1` reads `strong`, its one proof settled with its test unchanged, and no rule is weak; the walk asks `The audit's findings: 1 proof settled with its test unchanged. list / go on: `, then `Sign the evidence package for 2.1.0 as jane@acme.com? [y/N] ` and nothing else
- PROOF-282 (RULE-115): Both rules of `login` read `strong`, each with its one proof settled with its test unchanged; the walk's first question is `The audit's findings: 2 proofs settled with their tests unchanged. list / go on: `
- PROOF-283 (RULE-115): `login RULE-1` is audited weak and `login RULE-2` reads `strong` with `PROOF-2` settled with its test unchanged; the walk's first question is `The audit's findings: 1 weak, 1 proof settled with its test unchanged. list / go on: `
- PROOF-284 (RULE-139): `login RULE-1` reads `strong` and its audit's `no_bug` holds `PROOF-1 was settled with its test unchanged: it was judged to assert what the proof names.`; answered `list`, the walk prints only `  login RULE-1: PROOF-1 was settled with its test unchanged: it was judged to assert what the proof names.`, then asks `go on: `
- PROOF-285 (RULE-139): `login RULE-1` reads weak with the finding `PROOF-1 reads the status alone.`; `PROOF-2` of `login RULE-2` was settled with its test unchanged; answered `list`, the walk prints only `  login RULE-1   PROOF-1 reads the status alone.`, then `  login RULE-2: PROOF-2 was settled with its test unchanged: it was judged to assert what the proof names.`
- PROOF-286 (RULE-139): With `login RULE-1` settled with its test unchanged and no hand check, the walk answered `list`, `go on` and `y` asks those three questions alone, exits 0 and makes the signed commit `sign(2.1.0): jane@acme.com` with `signed/2.1.0` on it
- PROOF-287 (RULE-139): `login RULE-1` reads `spot-checked`, its `no_bug` holding `No bug was planted: the model could not be reached: claude exited with an error.`, and no rule is weak; the walk asks only `Sign the evidence package for 2.1.0 as jane@acme.com? [y/N] ` and prints no line holding `was settled`
- PROOF-288 (RULE-139): With `login RULE-1` settled with its test unchanged, `--show` prints `The audit's findings: 1 proof settled with its test unchanged.`, on the next line `  login RULE-1: PROOF-1 was settled with its test unchanged: it was judged to assert what the proof names.`, and exits 0
- PROOF-289 (RULE-140): With `login RULE-1` settled with its test unchanged, the walk answered `list`, `go on` and `y` signs; the sign-off records `audit_list_opened` true, and in the committed package `login RULE-1` reads `strong` and its `no_bug` is exactly `PROOF-1 was settled with its test unchanged: it was judged to assert what the proof names.`

Every proof is 60 words or fewer. The sample is the one `dev/sign_project.py` already makes;
its `audit(..., no_bug=...)` writes the sentence, so that file is unchanged.

## Seen failing first

Class `TestSettledByJudgment` in `dev/test_signatures.py`, written and run before the code:
`8 failed, 1 passed`. The walk asked only the sign question (281, 282, 284, 286; 289 then
found no sign-off file), the question read `1 weak.` (283), the list lacked the line (285),
and `--show` printed no header (288). PROOF-287, the control, passed before and after. After
the code: `90 passed` in the file.

## On a copy of the real project

`RLabGenMusic-upgrade-4`, copied with `cp -Rc` into the scratch folder. It holds no audit
entry, so no settled sentence: `--show` printed the run line, `Signing 0.1.0 at 40bf938.`, the
overview and the closing line, no findings list, as before, and left the copy unchanged. The
new lines are shown on the tests' samples only.

## Lines chosen

- The question's counts: `1 proof settled with its test unchanged`,
  `<n> proofs settled with their tests unchanged`, joined after `<n> weak` by `, `.
- `docs/sign-off.md`, "The walk": the question's condition, an example of the list, and
  "A planted bug once got past that proof's test. `purlin:build` read the test against the
  proof, judged that it already asserts what the proof names and left it as it was, so the
  finding was cleared by that judgment and not by a stronger test. Purlin records the judgment
  and does not check it, so you see it here."
- `skills/sign/SKILL.md`, Step 4: one paragraph with the line, the question and the same
  meaning, ending "Show the line as printed."
- `sign.py`'s docstring: "each proof settled with its test unchanged listed after them".

## Calls the plan did not make

1. The line goes after all weak findings, not beside its own rule, with no heading.
2. The question counts the judged proofs and is asked where no rule is weak; otherwise the line
   could not be seen in the walk of a project with no weak rule.
3. The count is per proof (per line), not per rule.
4. Any verdict includes `out of date`: the line is what the package's `no_bug` holds.
5. A hand check's stop does not show the line.
6. No format bump: recording needed no new field.
7. `sign.py` imports `audit_run` for the sentence, its one home, instead of a copy.

## Left, or waiting on another lane

- `references/evidence_and_signoff.md` (lane `run4`'s, as `run3`'s before): its walk paragraph
  reads "Where a rule reads weak it offers the audit's findings as a list." The exact change:
  "Where a rule reads weak, or a proof was settled with its test unchanged, it offers the
  audit's findings as a list, the settled proofs after the weak rules' findings."
- `references/formats/signature_format.md`, `audit_list_opened` (no lane's): still true; if the
  owner wants it spelled out, a wording change with no bump: "whether the signer asked to see
  the audit's findings, the proofs settled with their test unchanged among them".
