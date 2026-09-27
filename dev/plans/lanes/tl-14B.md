# Lane 14B: the pages, the skills, the board's words and the slides say tags, trust and lists

Plan: `dev/plans/three-levels.md` (Part A, decisions 23 to 31; 31 is the one you render).
Rules: `dev/plans/lanes/tl-_rules.md` (in full). Read all of `design/readme.md` and
`docs/_mermaid.md`. Worktree `/Users/richlabarca/LocalCode/purlin-wt/14B`, branch `lane/14B`
off `lane/14`. **Do not push. Do not open a pull request.** You run in parallel with lane 14A
(the code); write from decision 31's text now, and when the orchestrator tells you 14A has
landed, rebase, check every claim against the code naming the line, and finish.

## The board (`scripts/report/src/`, `dev/test_purlin_report*.py`, `specs/dashboard/purlin_report.md`)

- Finding names go: no `findings` on a proof, no free-check names anywhere on the page; the
  brief panel shows the strength beside the minimum and the audit's observations as
  sentences. Payload schema 8 (14A's); read only keys 14A's brief names.
- Words: the two dashboard tabs stay `Review` and `Sign`; every sentence on the page that
  says "review list" for the tab says "Review tab", and the terminal's lists are not the
  page's concern. The top bar gains the tag: `signed/<version>` with its commit when HEAD
  carries one, else `no signed tag`, from a new payload key `tag` (14A writes it; read it
  defensively). The `Last run` hover says `local` or `ci`; nothing says "preview".
- Rebuild; six screenshots recaptured and looked at; 1200-line limit.

## Skills and the agent

`skills/sign` (the opening counts, Review then Sign, the tag, `--release`, the trust refusal),
`skills/audit` (measures strength; hints, not findings; no `--tag`), `skills/test`
(`--remote` unchanged in use), `skills/init` (the trust question, no branch rules, no hook,
the tag as the marker), `skills/status`, `skills/spec` (no bar tag at `passed`), `skills/drift`,
`skills/build`, `agents/purlin.md` (never push, never tag; the tag is a person's act after
`purlin:sign` writes it). `dev/test_skills.py` follows. Every purpose sentence equals
`references/purlin_commands.md`'s (14A's file; take its wording at the rebase).

## Pages

Every page in `docs/index.md`'s order, plus `README.md` and `RELEASE_NOTES.md`'s 0.10.0 entry:

- the `passed` loop unchanged; the hook gone from every page; push is free everywhere;
- `strong`: your audit counts; `signed`: your audit counts too, the signature locks rule,
  proof, test, bar and the audit's findings; a re-audit that finds something new stales it;
- the tag: `purlin:sign` writes `signed/<version>` when everything meets the gate, you push
  it, CI runs on the tag and verifies the evidence on a clean machine, the job `purlin` goes
  green or red on the tag; no pull request runs, no branch rules;
- trust: the init question, what `remote` changes (`purlin:test --remote` before signing);
- the free checks are gone as a concept: the audit reads hints and writes sentences;
- `list` for what `purlin:sign` walks, `tab` for the page;
- the three reasons for a remote runner stay verbatim, with "no merge while red" rewritten
  to "the tag says so": a red tag run is the host's word that this version is not proven.
  Ask the orchestrator if that sentence should change more; do not decide it.
- One diagram per page, rendered and looked at; the `strong` and `signed` sequence diagrams
  end at the tag, not at a merge.

`dev/plans/lanes/tl-14B-slides.md`: the three step lists in the deck's shape, the `signed`
slide ending `purlin:sign` → tag → push → CI verifies the tag → green.

## Acceptance

```
python3 dev/build_report.py
pytest dev/test_purlin_report.py dev/test_purlin_report_board_layout.py dev/test_skills.py dev/test_vocabulary.py
grep -rn "pre-push\|pre_push\|happy_path\|free check\|record/\|--tag\|branch rule\|ruleset" docs/ README.md skills/ agents/ | grep -v "retired\|glossary"   (nothing)
```

Report in the DONE shape of `tl-_rules.md`, with the spec maxima, the test delta, the code
lines each page was checked against once rebased, the full contents of `tl-14B-slides.md`,
and decisions.
