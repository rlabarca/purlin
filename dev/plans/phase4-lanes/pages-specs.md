# Lane `pages-specs` (phase 4, fan-out 2: the pages)

You are lane `pages-specs` of fan-out 2 of phase 4 of Purlin 0.10.0. Fan-out 1 has applied
sanity check 3 to the product and integration 1 has merged it. You read
`docs/specs-and-anchors.md`, `docs/spec-from-code.md`, `docs/working-together.md`,
`docs/team-workflow.md` again against the code as it stands and rewrite them to say what is
(decision 63). This brief is complete in itself. No reviewer follows you: you check your own
work with the self-check and report.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/p4-pages-specs`, branch `p4/pages-specs`,
  created from `main` after integration 1:
  `git -C /Users/richlabarca/LocalCode/purlin worktree add /Users/richlabarca/LocalCode/purlin-wt/p4-pages-specs -b p4/pages-specs main`.
- Scratch folder: `<the scratchpad directory your session gives>/p4-pages-specs`:
  every scratch project you run goes here.

## Read first

1. `CLAUDE.md`, `references/writing_style.md` (the authority for every sentence),
   `references/glossary.md` (the word for each concept), `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` decisions 60 to 98.
3. `dev/plans/sanity-3.md` sections 3 and 4 (your pages), 5 and 11.
4. `dev/plans/phase4-plan.md` sections 9 to 12, `dev/plans/phase4-contracts.md` whole (K8 is
   yours), and `dev/plans/phase4-interfaces.md`, what fan-out 1 built.
5. `references/purlin_commands.md` and `references/hard_gates.md`: the pages point at them
   rather than restating them.

## The files you own

You write these and no other file. `docs/images/` is integration 2's.

- `docs/specs-and-anchors.md`
- `docs/spec-from-code.md`
- `docs/working-together.md`
- `docs/team-workflow.md`

## The work

1. Every false statement of `sanity-3.md` section 3 under the four pages, corrected to what is,
   read against the code as merged.
2. `> Requires:` names anchors only (A8), and a rule number is never reused, through
   `> Highest-Rule:` (A7), wherever these pages describe them.
3. The example proofs (`docs/specs-and-anchors.md` 38-40 and 102) meet the quality guide (§8
   item 15).
4. `docs/spec-from-code.md` says what the skill says now: the five reasons for an untied test
   (A3, A4), what a caller reaches, the position file, the ending in order, and that the status
   reads specs before setup (§8 item 11).
5. Every sample of printed output from a real run in a scratch project; diagrams plain mermaid.
6. Every other statement: name the rule that covers it, or cut it, or hand it to integration 2
   as a rule to add, in the words it would need.

How a sample is taken (K8): set up a scratch project under your scratch folder with
`sh scripts/purlin_python.sh scripts/init/scaffold.py --project-root <dir> --gate <gate>`
(and `< /dev/null`, or `--yes` where the page shows the commit), write its spec and marked
tests by hand as the page's reader would get them from `purlin:spec` and `purlin:build`, and run
`scripts/run/purlin_run.py`, `scripts/review/sign.py` (with `git config user.signingkey`
pointing at a key you make with `ssh-keygen` in the scratch folder and `gpg.format ssh`),
`scripts/export/package.py` and `scripts/anchor/upstream.py` as the page describes. Copy what
they print. Never start the real `claude` program; a step a model carries out is shown as what
you type and the summary it ends on.

## How to test

```
cd /Users/richlabarca/LocalCode/purlin-wt/p4-pages-specs
bash dev/run_tests.sh --fast
```

## Limits

- Commit on `p4/pages-specs` only, `docs:` for the pages and `spec(purlin_docs):` /
  `test(purlin_docs):` for the new spec and test, each message ending with the attribution lines
  your session gives. Push nothing, tag nothing.
- Change no file of the product, no reference and no skill: where a page and the code disagree
  and the code is wrong, write what the code does and report the difference.
- Run no `purlin:audit` and no `purlin:sign`; never start the real `claude` program, a real git
  host, `gh`, `az` or any network service.
- Stage no generated file: `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`,
  `.github/workflows/purlin.yml`, `docs/images/**`.
- A word a person reads that is not a fact of the code, the glossary or a decision: write it in
  the writing style, and list it in your report for the owner.

## Self-check (run it, then report each result)

1. Every statement of each page has a rule you named, or was cut, or is in your list for
   integration 2. Count them per page.
2. Every printed line on your pages is character for character what a scratch run printed (name
   the run), or a line the contracts give.
3. `git grep -n -e "\[level:" -e "meets the gate" -e "stale" -e "--dry-run" -e "Queue" -e "trust"`
   over your pages prints nothing that describes the product.
4. No generated file is staged; every link from your pages resolves; every mermaid block is
   plain mermaid.
5. Break three things on purpose and see a check fail, then restore: (a) change one quoted
   printed line and rerun its scratch command: the two differ; (b) break one link and run your
   link check: it fails; (c) put `stale` back into one sentence and run check 3: it prints the
   line.

## Report, as your final message

- The branch and its commits.
- For each page: the false statements of section 3 corrected, the statements cut, and the list
  of rules to add, each in the words it would need and the spec it belongs to.
- The scratch runs each sample came from.
- Every sentence you wrote that no code, glossary entry or decision gives, for the owner.
- The self-check's five results.
