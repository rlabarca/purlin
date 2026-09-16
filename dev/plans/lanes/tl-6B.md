# Lane 6B: docs word swaps and design

Plan: `dev/plans/three-levels.md` (read Part A and Part C in full; skim Part B). Rules:
`dev/plans/lanes/tl-_rules.md` (in full). Read all of `design/readme.md`. Worktree
`/Users/richlabarca/LocalCode/purlin-wt/6B`, branch `lane/6B` off `three-levels`.

This lane changes words, not structure. Every edit replaces a retired spelling (decision 15
and `tl-_rules.md` "Vocabulary") with the word Part A gives it, in the sentence the file
already has. Where a sentence describes a retired mechanism, rewrite that sentence to say what
the three-level model does, in the same length. Do not add sections or examples.

## Files

- `docs/solo-workflow.md` (the `passed` gate; `purlin:test` and `purlin:audit`; no strength,
  no risk, no review list under `passed`), `docs/specs-and-anchors.md` (and L135–139: a
  re-tag or an anchor sync stales the signatures), `docs/design-in-specs.md`,
  `docs/spec-from-code.md`, `docs/index.md` (the link to `review-and-signing.md` and to
  `references/formats/signature_format.md`; the command list of twelve).
- `design/readme.md` L31 and L121–124: the state badge examples read `PASSED`, `STRONG`,
  `SIGNED`; `purlin:verify` becomes `purlin:audit`; "review queue" becomes "review list".
- `design/components/core/StatusPill.jsx`, `StatusPill.d.ts`, `StatusPill.prompt.md`,
  `core.card.html`, `data/StatTile.prompt.md`, `data/data.card.html`,
  `data/GroupHeader.prompt.md`, `data/DataTable.prompt.md`, `core/Button.prompt.md`,
  `core/Tag.prompt.md`, `core/Panel.prompt.md`, `editorial/CommandChip.prompt.md`,
  `editorial/NumberedItem.prompt.md`, `editorial/editorial.card.html`,
  `guidelines/type-scale-ui.card.html`, `guidelines/type-mono.card.html`: every state word,
  tile label and gate value becomes a cell word (`passed`, `strong`, `signed`, `failed`,
  `stale`, `weak`, `needs a person`, `held`, `unsigned`, `drafted`, `ready`) or a gate value
  (`passed`, `strong`, `signed`); `purlin:verify`→`purlin:audit`; `approve`→`sign`. Tones
  stay: pass, warn, fail, neutral. No colour literal, no new token.
- `git rm -r dev/screenshots/`.
- Delete every one of the above from `PENDING_REWRITE` in `dev/test_vocabulary.py`
  (`design/readme.md`, `design/components/`, `design/guidelines/` and your five docs).

## Words

Part A1 in full. Never a retired word.

## Acceptance

```
pytest dev/test_vocabulary.py
grep -rn "review-and-approval\|approval_format\|purlin:verify\|purlin:review\|purlin:approve" docs/index.md docs/solo-workflow.md docs/specs-and-anchors.md docs/design-in-specs.md docs/spec-from-code.md design/   (nothing)
ls dev/screenshots 2>&1   (no such directory)
```
