# Lane `signnote`, decision 120

Branch `lane/d120-signnote`. Tests: `dev/test_signatures.py` and `dev/test_skill_sign.py`, 51
passing before, 54 after. `signatures`: `Highest-Rule` 128 to 129, `Highest-Proof` 248 to 251.
No format file changed, and no `Format-Version`.

## 1. A hand check's stop shows the last note

`scripts/review/sign.py`: `last_notes(project_root)` reads the dashboard's own source,
`payload._hand_notes`, so the words are `states.HAND_NOTE` on both surfaces. `plan` takes the
notes and each stop carries its rule's lines; `render_stop` prints them last, under `Last note`.
`--show`, the walk and `--answers` all show it. The sign-off file is unchanged: `shown` does not
record the last note.

New rule and proofs, word for word:

- RULE-129: A hand check's stop shows, under `Last note`, each note of the newest sign-off that holds one for the rule, worded as the dashboard words it: `noted at the sign-off of <version> by <signer>, <at this commit | 1 commit since | <n> commits since>: <note>`; where no sign-off has noted the rule the stop shows neither
- PROOF-249 (RULE-129): `quinn.qa@labconnect.example` signs `0.1.0` with the note `the tube is red` at the hand check `login RULE-2`; for a second signer, `--show` ends that stop on `Last note`, then `  noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, at this commit: the tube is red`
- PROOF-250 (RULE-129): After that sign-off three commits each change `NOTES` and a fourth commits new results; `--show --version 0.2.0` prints, last in the stop of `login RULE-2`, `  noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, 4 commits since: the tube is red`
- PROOF-251 (RULE-129): Before any sign-off, `--show` ends the stop of the hand check `login RULE-2` on `Results` and `  Linux/Unix: passed on dana-laptop`, with no line `Last note`

Tests: `TestTheLastNote` in `dev/test_signatures.py`, one per proof. Broken on purpose twice:
with the lines never printed, PROOF-249 and PROOF-250 fail; with the head always printed,
PROOF-251 fails.

Lines a person reads:

- Terminal: `Last note`, then `  noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, 4 commits since: the tube is red`.
- `skills/sign/SKILL.md`, Step 4: "Where an earlier sign-off noted the rule, the stop ends on `Last note` and that note, with the version it was signed at and how many commits have come since."
- `docs/sign-off.md`, "The walk": the bullet "the rule's last note, where an earlier sign-off holds one.", then "The last note names the version it was signed at and how many commits have come since. You judge whether it still holds:" and the two printed lines.
- `references/evidence_and_signoff.md`, "A hand check": "there and in its stop of the next walk" added.

## 2. Approval before a test runs

Both facts checked. `references/formats/package_format.md`, "Authors": each proof carries
`written_by`, `written_commit`, `changed_by`, `changed_commit`. `references/formats/evidence_format.md`,
"The fingerprint": the `spec` part covers each proof line, and a section whose part differs is
`out of date` (`evidence` PROOF-2 shows a reworded line changes `spec` alone).

`docs/sign-off.md`, "Beside a regulated system", word for word:

> **Approval before a test runs.** Purlin has no approval step before a test runs. It signs once,
> at the end. Approval of the proofs is a required review when they are merged, or your system of
> record's. Purlin does record two things:
>
> - who wrote and who last changed each proof, read from git into the evidence package;
> - that a result stops counting when its proof is reworded. The rule reads `out of date` until
>   its tests run again.

## 3. The sign-off file is verified through its signed commit

`references/evidence_and_signoff.md`, "When a sign-off counts", the one home, word for word:

> **How each is checked.**
>
> - The evidence package is checkable alone, by its fingerprint: `purlin:sign --check <file>`
>   reads the one file and needs no key.
> - The sign-off file is not. It carries no hash of itself and no signature inside it.
> - The sign-off names the package's fingerprint. The signed commit that added it binds the
>   sign-off, the package and the code.
> - A receiving system takes the signed commit as the record.
> - The sign-off records no approve or reject answer and no stated meaning of the signature.

`docs/sign-off.md`, "What is recorded":

> **How each is checked.** The package is checkable alone, by its fingerprint:
> `purlin:sign --check <file>`. The sign-off file is not. It carries no hash of itself and no
> signature inside it. It names the package's fingerprint, and the signed commit that added it
> binds the sign-off, the package and the code.
> [evidence_and_signoff.md](../references/evidence_and_signoff.md#when-a-sign-off-counts) is the
> one definition.

`docs/sign-off.md`, "Beside a regulated system":

> **The signed commit is the record.** The package is checkable alone, with
> `purlin:sign --check <file>`. A sign-off file is not: take the signed commit that added it as
> the record. The sign-off records no approve or reject answer and no stated meaning of the
> signature.

`references/formats/signature_format.md` and `package_format.md` were read against this and
contradict nothing; neither was changed.

## 4. `skills/sign/SKILL.md`, the paragraph after the refusals

Now one sentence on the missing version and a list of six short items. Nothing said was taken
out.

## Edits in files this lane does not own

- None needed. Optional, `scripts/mcp/purlin/payload.py`: rename `_hand_notes` to `hand_notes`,
  since `sign.py` now calls it from another module; then `sign.last_notes` calls the new name.
- The deck, `dev/plans/deck/build_deck.py`: item 1 makes no line untrue. The `manual` slide's
  notes (about line 200) say "After a sign-off the status and the dashboard show the last note";
  the walk's stop now shows it too, so the owner may add it.

## Left open

- A note recorded as `no note` shows as `...: no note`, as the dashboard shows it.
- PROOF-250 counts the commit of new results among the four, because the note's count is every
  commit since the signed one, as on the dashboard.
