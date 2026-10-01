# Lane `anchors`, decision 119

Branch `lane/d119-anchors`, commit `f399caa14` on the base `49ca1c26e`.

## Tests

| | passed | failed | skipped |
|---|---|---|---|
| The seven pytest files, before | 244 | 0 | 0 |
| The seven pytest files, after | 244 | 0 | 0 |
| `dev/test_e2e_anchor_authority.sh`, after | 7 | 0 | 0 |
| `dev/test_e2e_external_refs.sh`, after | 10 | 0 | 1 (case 11, which needs `dev/setup-external-refs.sh`) |

Deleted 0, added 0. Rewritten 2, each with its reworded proof:

- `schema_spec_format PROOF-78`: `test_a_pinned_anchor_carrying_a_scope_line_names_its_source`
  is now `test_a_remote_anchor_carrying_a_scope_line_names_its_source`. Its assertions are unchanged.
- `upstream PROOF-45`: one comment added, `The two remote anchors sync; the anchor of a file on
  disk does not.` Its assertions are unchanged.

Appendix A's script over the nine test files: `0 gone, 0 reworded, 240 right as they stand.`
Before: `0 gone, 2 reworded`. The two section 8 greps and the `dev/` and `specs/` grep find
nothing in the lane's files. Broken once on purpose: the warning line in `specs.py` with `!`
for `.`; `PROOF-78`'s test failed; restored with `git checkout`.

## Lines Purlin prints

None changed. No line the code prints named the kind: each says `the pin`, `pinned <sha>`,
`names a source and no pin` or `its source`, all of which stay. The constant holding
`PROOF-78`'s line was renamed and its text left as it was.

## Lines the tests print, before and after

`dev/test_e2e_anchor_authority.sh`:

| Before | After |
|---|---|
| `drift names the pinned anchor behind and leaves the local one out` | `drift names the remote anchor behind and leaves the local one out` |
| `a sync replaces the pinned copy and never the local anchor` | `a sync replaces the remote anchor's copy and never the local anchor` |
| `the pinned anchor still counts the rules its copy holds` | `the remote anchor still counts the rules its copy holds` |
| `--- 7: a pinned source that carries > Scope: ---` | `--- 7: a remote anchor's source that carries > Scope: ---` |
| commit message `edit the pinned copy, which a sync will undo` | `edit the remote anchor's copy, which a sync will undo` |

`dev/test_e2e_external_refs.sh`, reworded only because section 8's grep reads `unpinned source`
and `unpinned anchor` as hits; the status `unpinned` itself stays:

| Before | After |
|---|---|
| `--- 8: an unpinned source ---` | `--- 8: a source with no pin ---` |
| commit message `add an unpinned anchor` | `add an anchor with no pin` |

## Prose a person reads, before and after

`skills/anchor/SKILL.md`:

- Heading `## Changing a pinned rule` reads `## Changing a remote anchor's rule`.
- `**Never edit a pinned rule in place.**` reads `**Never edit a remote anchor's rule in place.**`
- `The pinned copy stays untouched.` reads `The remote anchor's copy stays untouched.`
- Added under `add`, chosen by this lane: `An anchor brought in this way is a remote anchor: its
  copy is pinned to one version of its source.`

`references/formats/anchor_format.md`, still `Format-Version: 12`:

- Heading `## Editing a pinned anchor` reads `## Editing a remote anchor`.
- `A consumer never edits a pinned rule in place` reads `A consumer never edits a remote anchor's rule in place`.
- `A pinned copy is written as its source holds it` reads `A remote anchor's copy is written as its source holds it`.
- Added in Part 2's opening, chosen by this lane: `Such an anchor is a remote anchor: its copy
  is pinned to one version of its source.`

## Code, comments and docstrings

- `scripts/anchor/upstream.py`: the module docstring; `pinned_anchors()` is `remote_anchors()`.
- `scripts/mcp/purlin/drift.py`: three docstrings.
- `scripts/mcp/purlin/specs.py`: one docstring; `PINNED_UNREAD` is `REMOTE_UNREAD`; `_pinned()` is `_remote()`.
- Comments and docstrings in `test_e2e_anchor_authority.sh`, `test_purlin_report.py`,
  `test_schema_spec_format.py`, `test_upstream_notes.py`.

## Differences from the plan

- The counts are far under the plan's upper bounds: 27 lines named the kind, against the plan's
  about 60 for this lane. The rest were the verb, the pin, the field, the keys or `unpinned`.
- Unchanged, nothing in them names the kind: `references/drift_criteria.md`, `dev/test_drift.py`,
  `dev/test_states.py`, `dev/test_specs_reader.py`.
- No file of this lane named the remote runner, `--remote` or `hostname`; nothing to remove.

## Open

- `dev/test_drift.py` keeps the helper `_pinned_project` ("a project whose one anchor is pinned
  to a sha"), and `test_e2e_anchor_authority.sh` keeps `the local anchor was reported as pinned`
  and `the published anchor pinned`. This lane read each as the verb. The owner may read them as the kind.
- The three renamed identifiers are named in old plans under `dev/plans/` (`d100-plan.md`,
  `phase3-contracts.md`, `phase3-lanes/upstream.md`, `d115-reports/mcp.md`), which this lane does not own.
- No other file in the repository calls the renamed identifiers or links the two renamed headings.

## Failures in files this lane does not own

None seen.
