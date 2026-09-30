# Lane d102-dashboard: report

Lane `dashboard` of decision 102, on `lane/d102-dashboard` from `d102/base` at `24cf528`.

## Summary

The page reads schema 12 (`scripts/report/src/app.js`, `SCHEMA = 12`). The filter buttons name the
kind `to_repair` `To repair` (`filters.js` `SHORT_LABELS`). The three fixtures are schema 12
payloads: every feature carries `broken`, every rule `ended`. The team sample gains the spec
`refund` (2 rules, `PROOF-2` written twice), whose rules read `failed` with
`PROOF-2 is written twice in the spec` and `left: to_repair`, the line `1 spec to repair` first in
`left`, and the C2 warning. The regulated sample's login `RULE-2` carries an ended signature by
`sam@acme.com`: its signed cell reads `unsigned` with the `ENDED` reason, and its `ended` holds
the signer, the cause and the C4 line. The rule's screen already draws every reason a cell carries
in its row, so neither reason needed code or a new element. `docs/dashboard.md` names `To repair`
and the two reasons.

## Numbers

`specs/dashboard/purlin_report.md`: `> Highest-Rule: 68`, `> Highest-Proof: 217` (were 65 and
214). New: RULE-66 / PROOF-215 (the `To repair` button leaves refund alone, `RULE-1` and
`RULE-2`), RULE-67 / PROOF-216 (login `RULE-2`'s `Signed` row reads `UNSIGNED` and the ended
reason), RULE-68 / PROOF-217 (refund `RULE-2`'s `Passed` row reads `FAILED` and the reason). Each
has a marked test in `dev/test_purlin_report.py`.

## Tests

- My three files (`dev/test_purlin_report.py`, `dev/test_purlin_report_board_layout.py`,
  `dev/test_report_refresh.py`): before 198 passed; after 201, 197 passed, 4 failing (below).
- `bash dev/run_tests.sh --fast`: 2140 passed, 5 failed, 12 skipped.

## Proofs reworded

- PROOF-20: `this page reads schema 11` becomes `this page reads schema 12`.
- PROOF-94: the team sample's `8 rules` becomes `10 rules` (refund adds 2).
- PROOF-213: the buttons read `To repair`, `To write a test for`, `To confirm`, `To strengthen`.

No rule or proof deleted. Test helper `with_invoice_rule_2_unproved` now finds the `no_test` line
by kind, since it is no longer first.

## Calls

- **The ended signature is in the regulated sample, not the team sample.** Section 4 puts both in
  the team sample, but the team sample's gate is `strong`, where a rule has no signed cell to show
  it. The broken spec is in the team sample as planned.
- **The deliberate break.** The planned break, dropping `to_repair` from `SHORT_LABELS`, was run
  and PROOF-215's test and PROOF-213's test still passed: `leftLabel` already derives `To repair`
  from `1 spec to repair`. The entry stays, as section 4 asks. The break that was seen to fail was
  `SCHEMA = 11` in `app.js`, rebuilt: PROOF-215, PROOF-216 and PROOF-217 failed; restored with
  `git checkout -- scripts/report/src/app.js`, rebuilt, and they passed.
- The signer of the ended signature is `sam@acme.com`, as the regulated sample's signature file
  `RULE-2.5e6f7a8b.sam-acme.json` names.

## Words chosen that section 7 does not give

- Spec: RULE-66 `A spec that writes a number twice or holds a line left from a merge conflict is
  a spec to repair, and To repair is a filter button where the payload lists the kind to_repair;
  choosing it leaves that spec's rules alone`; RULE-67 `A rule whose signature ended says on its
  screen who signed it and why the signature ended`; RULE-68 `A rule of a spec to repair says on
  its screen why its tests' result does not count`.
- `docs/dashboard.md`: `1 spec to repair is To repair, which shows the rules of each spec that
  writes a number twice or holds a line left from a merge conflict`; `Every rule of a spec to
  repair reads failed in its passed row with the reason, such as PROOF-2 is written twice in the
  spec, whatever its tests found. A rule whose signature ended reads unsigned in its signed row
  with the cause, ...`.
- Fixture text for refund: `A refund returns the amount paid to the card it came from.`,
  `A refund of an order already refunded is refused.` and their proofs.

## Tests that fail only because another lane has not merged

All wait for lane `counting` (`payload.SCHEMA_VERSION = 12` and the builder's `broken` and
`ended` keys). With `SCHEMA_VERSION` set to 12 locally, the first four passed (edit reverted):

- `dev/test_purlin_report.py`: PROOF-65, PROOF-152, PROOF-110, PROOF-111 (a real project's payload
  at schema 11 reaches a page that reads 12).
- `dev/test_states.py::TestTheFixturesAreTheContract` (2 tests): my fixtures carry
  `features[].broken` and `rules[].ended`, which the schema 11 builder does not write yet.

## Failures in files I do not own, not caused by this lane

`dev/test_signatures.py::TestTheMachines::test_a_new_system_ends_nothing`,
`::test_a_system_it_names_that_is_gone_ends_it` and
`dev/test_tag.py::TestTheTag::test_the_tag_is_signed_with_the_key_the_settings_name` fail on plain
`d102/base` too: in this cloud container git signing goes through a wrapper that supports only
`-Y sign` (`unsupported code-sign operation`). Left to integration on the Mac.

## Environment

The pip `playwright` 1.63 does not match `/opt/pw-browsers/chromium-1194`, so the container got a
symlink `/usr/bin/chromium` to `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`, which
`dev/browser_launch.py` already tries. Nothing committed changed for it. Every browser test ran.
`scripts/report/purlin-report.html` was rebuilt and is not staged; integration builds it.
