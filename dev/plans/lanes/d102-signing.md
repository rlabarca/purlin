# Lane d102 `signing`: report

Branch `lane/d102-signing`, made from `origin/d102/base` at `24cf528`. It builds C8, C9, C10 (under
the owner's answer (a)), C11, signature format 13 and package format 6.

## What was built

- `scripts/mcp/purlin/signatures.py`
  - C8: `signed_hash` sets lines 4 to 7 to the empty string where `test_hash_kind` is `manual`.
    `is_current` takes the kind from the rule's current entry: its `test_hash_kind`, or, where
    the entry has none (the `inp` that `states.rule_cells` passes), the kind its `proofs` give.
    It never reads the kind from the signature.
  - C9: `counts` reads the last commit that touched the file with `git cat-file commit`. It finds
    the `gpgsig` header (or `gpgsig-sha256` when the commit id is 64 characters) among the headers
    only, and removes that header to get the payload. An SSH block is checked with
    `ssh-keygen -Y check-novalidate -n git -s <tmp sig>`, with the payload on stdin. Any other
    block is checked with `git verify-commit <sha>`. Adds `NOT_VERIFIED`.
- `scripts/review/sign.py`
  - C10: `SPEC_REFUSED`, `NO_TAG_SPEC`, `NO_TAG_BEHIND`, `REFUSED_SPEC` and `REFUSED_BEHIND`
    (both added to `MUST_FIX`).
  - `broken_specs()` reads `specs.broken_reasons`. When `sign.py <feature> ...` names a broken
    spec, it prints `SPEC_REFUSED` once and exits 1. This check runs before the key check.
  - `tag_if_met` checks in this order: the broken specs, then the summary ending (`spec`), the
    checks of today, then `behind_host()` (`behind`), then the version.
  - `behind_host` compares against `git rev-parse --abbrev-ref @{upstream}`, else
    `origin/<branch>` where that ref exists, else it runs no check. With a detached HEAD it runs
    no check. It fetches nothing.
  - C11: `tied_lines()` under each proof that is not `@manual` in `render_row`.
- `scripts/export/package.py`: no code change. `left` is copied from the payload, and
  `signed_commit` already calls `signatures.counts`.
- `references/formats/signature_format.md`: 12 to 13, with the C8, C9 and table changes from the
  plan and the section 7 lines for "A hand check's signature" and "A verified commit". The
  sentence "No message is printed for it." is replaced as the plan says.
- `references/formats/package_format.md`: 5 to 6, with the `to_repair` row. The `signed_commit`
  row now says the signature verifies.

## Highest lines after

- `specs/review/signatures.md`: `> Highest-Rule: 101`, `> Highest-Proof: 201`.
- `specs/export/package.md`: `> Highest-Rule: 28`, `> Highest-Proof: 60`.

New: signatures RULE-96 to RULE-101 and PROOF-190 to PROOF-201; package RULE-28 and PROOF-60.
Every new proof has a marked test of its own and is at most 47 words.

## Reworded (none deleted)

- RULE-6, RULE-61 and RULE-90 now begin "A signature that is not a hand check's ...". Each
  claimed that a code, machine or project edit ends every signature, which C8 makes untrue for
  a hand check.
- RULE-9 and PROOF-13: `signature format 13`.
- RULE-20: "carries a signature **that verifies**".
- PROOF-179: its anchor's one proof is "neither `@manual` nor tied to a test". Its test rewrites
  the anchor without `@manual`, because a hand-checked anchor no longer ends on a project edit.
- PROOF-201 differs from the plan's wording. A proof with no test cannot be a walk stop at
  `signed`, because such a rule is never `to_sign`. So the proof gives `RULE-2` an untested
  `PROOF-3`, and the test renders the stop for it.
- Tests with unchanged text: in `dev/test_signatures.py`, the `pinned` fixture writes its anchor
  without `@manual`, so PROOF-188 and PROOF-189 still end on a tracked-file edit. The field-list
  comment now says format 13.

## Tests

Before: 197 in the three files (`test_signatures` 106, `test_tag` 35, `test_export` 56).
After: 210 (114, 39, 57).

The code calls `specs.broken_reasons` as C1 names it, and lane `reader` has not merged. I ran
every check below with an uncommitted stub of C1 in `specs.py`, then removed it. Nothing of
`specs.py` is committed.

- Own files with the stub: 206 passed, 4 failed:
  - PROOF-60 waits for lane `counting` (the `to_repair` kind).
  - Three tests fail on base too, in this container:
    - `TestTheMachines::test_a_new_system_ends_nothing` and
      `test_a_system_it_names_that_is_gone_ends_it` assume a macOS host.
    - `test_tag.py::TestTheTag::test_the_tag_is_signed_with_the_key_the_settings_name`: the
      container's global `gpg.ssh.program` signs with its own key.
- `bash dev/run_tests.sh --fast` with the stub: 2153 passed, 12 skipped, 4 failed (the same
  four), 1 error. The error is `dev/test_states.py::TestStatusTable::test_the_table_and_the_dashboard_show_the_same_cells`:
  the pip playwright wants `chromium_headless_shell-1243`, which is not in `/opt/pw-browsers`.
  That is the environment, not a file this lane owns.
- Own files without the stub, as the branch stands: 89 failed and 4 errors. Every one comes from
  `AttributeError: specs.broken_reasons`, because every `sign.py` command and every tag call
  reads it. They pass once lane `reader` merges.

Deliberate breaks, both run with the stub, both failing as intended, both restored with
`git checkout -- scripts/mcp/purlin/signatures.py`:

1. A hand check signed over all seven lines: PROOF-190's test failed.
2. The header read without verifying: PROOF-192's test failed.

## Waiting for another lane

- Lane `reader` (`broken_reasons`): PROOF-194, PROOF-195 and PROOF-196. Until it merges, every
  `sign.py` test and every tag test fails too (see above).
- Lane `counting` (`to_repair`): PROOF-60.

## Calls made

- A broken spec is refused before the key check, so a person with no key still learns first
  that the spec must be fixed.
- A detached HEAD skips the check against the host copy.
- A signature block that is not SSH (OpenPGP or x509) goes to `git verify-commit`.
- A signature made under format 12 over a hand check ends once, on upgrade. Its hash covered
  seven lines; the new hash covers three.

## Words not given by section 7

None printed. The rule wording in the specs is this lane's own.

## Stale lines in files this lane does not own

Each still says a signature counts when its commit is signed "with any key", with no word about
verifying:

- `docs/review-and-signing.md:233`
- `docs/regulated-workflow.md:133`
- `references/hard_gates.md:184` ("present and looks no further")
- `references/glossary.md:92`

These belong to lane `words`, whose list covers "the verified commit".

- `skills/sign/SKILL.md:123`: lane `skills`. Its list does not name the verified commit.
