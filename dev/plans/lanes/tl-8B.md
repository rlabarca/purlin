# Lane 8B: the workflow at each gate, drawn and explained, matching the code exactly

Plan: `dev/plans/three-levels.md` (in full; decisions 25, 26 and 27 and Part A). Rules:
`dev/plans/lanes/tl-_rules.md` (in full). Read all of `design/readme.md` and `docs/_mermaid.md`.
Worktree `/Users/richlabarca/LocalCode/purlin-wt/8B`, branch `lane/8B` off `three-levels`
**after lane 8A has landed**. **Do not push this branch.**

The user's words: the documents must carry clear diagrams and explanations of how the Purlin
workflow works at each gate; it must be simple to understand and match how the code behaves
exactly. Every claim you write is checked against the code before you write it: the workflow
template, `purlin_run.py`, `records.py`, `remote.py`, `sign.py`, `gate_check.py`,
`scaffold.py`, `scripts/hooks/pre-push.sh`, `states.py`. When the code and your sentence
disagree, the sentence changes, and you name the line of code in your report.

## What you write

One page holds the model and three pages hold the gates. Each has one mermaid diagram with
the init block from `docs/_mermaid.md`, and the diagram shows a mechanism, not a list.

1. **`docs/how-purlin-works.md`** (new; linked from `docs/index.md` first and from `README.md`).
   The chain in one diagram: a rule's spec status and its three cells, which command answers
   each, and what each answer is made of. Then, in prose, the four words that carry the model:
   push (a person's act), remote run (the one push Purlin makes), record (what CI or a person
   writes), signature (what a person writes). Then the table "who writes what, where it
   lands, and who may touch it" for records, briefs, signatures, holds. Under 60 lines of
   prose beside the diagram.
2. **`docs/solo-workflow.md`** (gate `passed`, no runner). The loop as a sequence diagram:
   spec, build, `purlin:test`, `purlin:audit --commit` (record, source `developer`, no
   push), `gate_check.py --check` on the laptop, `git push` by the person, the pull request
   the person opens, the reviewer's `purlin:drift` and `purlin:status`. State that no
   workflow is written at `passed` unless `--ci` asks for one, that every source counts, and
   what the board shows.
3. **`docs/team-workflow.md`** (gate `strong`). The same diagram with the runner in it: the
   person pushes, the pull request run tests and comments and commits nothing, the merge, the
   run on the protected branch that writes records and briefs and runs the gate check, and
   `purlin:audit --remote` as the one path that gets a CI record before merge (run branch,
   pull-back, deletion). State that only a `ci` record counts, that a local audit is a preview,
   what `manual audit` and `weak` mean here, and what the review list holds at `strong`.
4. **`docs/regulated-workflow.md`** (gate `signed`). The `strong` diagram plus signing: the
   review list, the walk, the signed commit, the person's push, the five conditions for a
   signature to count, the protected-branch requirement, holds and notes. Keep the existing
   `stateDiagram-v2` only if it still says the same as the cell words; one diagram per page.
5. **`docs/running-and-records.md`**: the CI section rewritten to decision 26 (triggers, what
   a pull request run does and does not do, where the record commit lands, the gate step) and
   the push section to decision 27 (the guard, `--no-verify` as a person's override).
6. **`docs/raising-the-gate-and-upgrading.md`**: what each raise changes in this list, and
   what `purlin:init --update` does to an existing `purlin.yml`.
7. **`docs/index.md`**, **`README.md`**: the gate table gains a "where the counting record
   comes from" column (`your machine or CI` / `CI on the protected branch or a remote run` /
   the same plus a person's signature); link the new page.
8. **`references/hard_gates.md`**: confirm lane 8A's CI section reads the same as your pages;
   if a sentence differs, fix the reference to the code, not to your page, and say so.

## How to check a diagram

Render each with `npx -y @mermaid-js/mermaid-cli -i <md-fence-extracted>.mmd -o out.png`
(or, if `npx` is unavailable, the `mermaid.ink` render is fine: `curl` the encoded diagram)
and look at the PNG. A diagram that does not render, or that a reader would have to trace
twice, is rewritten. Report what each diagram shows in one sentence.

## Words

Part A1 plus decision 27's four words. Never `needs a person` outside the review list header,
never a retired word, never a claim the code does not make.

## Acceptance

```
pytest dev/test_vocabulary.py $(ls dev/test_docs*.py 2>/dev/null)
grep -rn "on every push\|every push\|pushes the branch\|auto" docs/ README.md | grep -v "run/\|remote run\|autofit\|auto-fit\|automation"   (nothing that says CI runs or Purlin pushes on an ordinary push)
```

Report in the DONE shape of `tl-_rules.md`, with the one-sentence description of each diagram
and the list of code lines each page's claims were checked against.
