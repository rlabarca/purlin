# Decision 121, lane `surfaces`: report

Branch `lane/d121-surfaces`, cut from `main` at `fe512e267`. The lane's seven test files:
166 passed before, 173 passed after (8 tests added, 1 deleted). No push, no audit, no
sign-off, no full sweep.

## 1. The strong cell (`states`)

`scripts/mcp/purlin/states.py`: `_strong_cell` reads the rule's audit entry whatever its
hashes. A current entry gives `strong`, `weak` or `spot-checked`; an entry out of date gives
`out of date`. `_flags` gains `spot_checked` and `audit_out_of_date`, and `COUNTED_FLAGS` counts
both, so every rollup and the summary carry the two keys. `EARLIER_WEAK` is deleted.
`NOT_AUDITED_REASON` reads `no audit has read this rule`. New constants: `VERDICTS`,
`SPOT_CHECKED`, `SPOT_TESTS_FOUND_NOTHING`, `CHANGED_SINCE`, `LAST_AUDIT`.

The order the cell is decided in: `waiting`; `no proof`; a current `weak`; `checked at
sign-off` for a rule with a `@manual` proof; `not audited`; `out of date`; `spot-checked`;
`strong`.

Rules, word for word (`specs/mcp/states.md`, `> Highest-Rule: 126`, `> Highest-Proof: 290`):

- RULE-14: The strong cell reads the rule's audit entry, a current one before one out of date: `strong`; `weak`, with each finding among its reasons; or `spot-checked`, with the one reason `The spot tests found nothing. ` followed by the entry's `no_bug` sentences; a verdict the format does not name decides nothing, and the cell names the evidence file under `evidence`
- RULE-27: as before, with `schema version 15`
- RULE-59: `signoff` carries `word`, `version`, `commit` and `since` for the newest `signed/*` tag on HEAD or an ancestor of it whose sign-off counts, numbered versions compared as numbers, `word` reading as the status's `Sign-off:` line does, and `word` reads `not signed` where no such tag exists
- RULE-61: Every rule carries `audit`, eleven fields: the `verdict`, `findings`, `no_bug` and `notes` of its audit entry, its `explanation` and its `breaks` exactly as the entry holds them, `[]` and `{}` where it holds none, the `model` that answered or `unknown`, `at`, `commit`, the evidence file under `path`, and `out_of_date`, the parts that changed since, `[]` for a current entry; or null where the rule has no entry
- RULE-118: A strong cell with no audit entry reads `waiting`, with the reason `waiting for its tests to pass`, while the passed cell is not met, an entry or none; `no proof`, with the reason `the rule has a test and no proof`, for a passing rule no proof line names; and otherwise `not audited`, with the reason `no audit has read this rule`; none of these is `weak`
- RULE-121: as before, with `` `Strong` added where any rule has an audit entry ``
- RULE-126 (new): An audit entry whose rule, proof, test or covered code changed since it was written makes the strong cell read `out of date`, with one reason per part that differs, `<part> changed since <sha7>`, the entry's commit, then `the last audit found it <verdict> on <date>`; the entry stays in the evidence, and the rule is left nothing to strengthen

Proofs, word for word:

- PROOF-31 (RULE-27): The payload reads `schema_version` 15 and carries exactly the seventeen top-level keys the rule names beside it, with `generated_at` ending in `Z`
- PROOF-73 (RULE-61): A rule whose audit entry reads `weak` with the finding `PROOF-2 reads 401 alone.` and names no model carries `audit` with exactly `verdict`, `findings`, `no_bug`, `notes`, `explanation`, `breaks`, `model`, `at`, `commit`, `path` and `out_of_date`: `weak`, that finding, `[]`, no note, `[]`, `{}`, `unknown`, the entry's time and commit, `.purlin/evidence/local/login.json` and `[]`
- PROOF-168 (RULE-59): Once the walk signs `1.2.0` at HEAD, `signoff` reads the version `1.2.0`, the signed commit, and the word `signed 1.2.0 at <sha7>`
- PROOF-169 (RULE-59): With `1.2.0` signed by the walk and one more commit made after it changing only `.purlin/evidence/local/login.json`, `signoff.word` still reads `signed 1.2.0 at <sha7>`, the tagged commit
- PROOF-170 (RULE-59): With `1.9.0`, `1.10.0` and `beta` each signed by the walk on one commit, `signoff.version` reads `1.10.0`
- PROOF-286 (RULE-126): `RULE-2` passes and its audit entry reads `strong`, written on `2026-09-13` at the commit `<c>`; `src/login.py` is rewritten and committed and its tests pass again; the strong cell reads `out of date` with exactly the reasons `code changed since <c7>` and `the last audit found it strong on 2026-09-13`
- PROOF-287 (RULE-126): With `RULE-2`'s test passing, its audit entry reads `weak` with one finding and was written for another rule text; the strong cell reads `out of date` with the first reason `rule changed since <sha7>`, its `findings` hold that finding, and the rule's `left` is null
- PROOF-288 (RULE-16): A rule has `PROOF-1` marked `@manual` and `PROOF-2` whose test passes, and its current audit entry reads `weak` with the finding `PROOF-2 reads the status alone.`; the strong cell reads `weak`, its reasons hold that finding, and its `left` is `to_strengthen`
- PROOF-289 (RULE-9): A rule's one proof fails in a current `ci` section from `linux` dated `2026-09-01T00:00:00Z` and passes in a current `local` section from `linux` dated `2026-09-02T00:00:00Z`; the passed cell reads `failed` with the reason `failing: Linux/Unix, ci`
- PROOF-290 (RULE-14): With `RULE-2`'s test passing, its current audit entry reads `spot-checked` with the one `no_bug` sentence `No bug was planted: the model could not be reached: claude is not on PATH.`; the strong cell reads `spot-checked` with the one reason `The spot tests found nothing. No bug was planted: the model could not be reached: claude is not on PATH.`
- PROOF-160 deleted with its test. PROOF-71 was already gone in the base commit.

Tests: PROOF-286, 287, 288, 290 and the reworded 31, 73, 168, 169, 170 in
`dev/test_states.py`; PROOF-289 in `dev/test_failing.py`. PROOF-168 to 170, and PROOF-276 and
277 (not reworded), now sign with the real walk (`sign.walk`) and a throwaway key, since a tag
typed by hand stops counting once lane `signoff` lands.

The `states` spec's `> Scope:` is unchanged: the plan does not say it follows `hand_notes` to
`signatures.py`.

## 2. The payload

`scripts/mcp/purlin/payload.py`: `SCHEMA_VERSION` 15. `audit_summary` gives the eleven fields
and accepts `spot-checked`. The line `if audit and audit['out_of_date']: audit = None` in
`_rule_entry` is gone, so an entry out of date reaches the cell and the rule's `audit` with
what changed. The module's docstring shows the new shape.

## 3. The summary line (`summary`)

`scripts/mcp/purlin/summary.py`: `audit_counts` gives the five counts, each rule counted by
its strong cell's word. `sentence` adds `summary.audit_line` where a rule that passes has an
audit entry. `has_audit(counts)` is new and is the one test of that; `board.shows_strong`
calls it. `AUDIT_SHARE` is deleted; `AUDIT_LINE` stands.

- RULE-20: as before, with `for the newest `signed/*` tag on HEAD or an ancestor of it whose sign-off counts`
- RULE-22: The sentence reads `<N> rules. <p> pass their tests.`, `1 rule.` and `1 passes its tests.` for a count of one, counting each rule once under the spec that owns it; where a rule that passes has an audit entry it adds ` The audit found <s> of <n> rules strong (<p>%): <s> strong`, then `, <n> weak`, `, <n> spot-checked`, `, <n> out of date` and `, <n> not audited`, each only where not zero
- PROOF-43 (RULE-22): 50 rules that all pass their tests, 42 found strong and 8 found weak by the audit, read `50 rules. 50 pass their tests. The audit found 42 of 50 rules strong (84%): 42 strong, 8 weak.`
- PROOF-50 (RULE-20): With `0.1.0` signed by the walk and then one commit changing `src/age.py` made after it, the status's third line reads `Sign-off: signed 0.1.0, 1 commit since`
- PROOF-57 (RULE-22): 40 rules that all pass their tests, 34 found strong, 4 weak and 2 spot-checked, read `40 rules. 40 pass their tests. The audit found 34 of 40 rules strong (85%): 34 strong, 4 weak, 2 spot-checked.`

`> Highest-Proof: 57`. Tests in `dev/test_summary.py`; PROOF-50 signs with the walk.

## 4. The status table

`scripts/mcp/purlin/board.py`, `status.py`: `Strong` is shown where `summary.audit` counts a
rule `strong`, `weak`, `spot_checked` or `out_of_date`.

## 5. The dashboard (`purlin_report`)

`scripts/report/src/app.js`: `SCHEMA` 15; `audited()` counts the four words; `spot-checked`
takes the neutral tone, `out of date` the warn tone it already had. `rule.js`: the `Audit`
panel. `board.js`: a comment. The board row's badges are unchanged (`RULE-55` is not
reworded): `SPOT-CHECKED` and `OUT OF DATE` are the strong row's word on a rule's screen.

The panel's lines, in order: `Out of date: <the cell's reasons joined by "; ">` where the
entry is out of date; the answer; each finding; for a spot-checked rule one line, `The spot
tests found nothing. ` and the `no_bug` sentences; for a strong or weak rule each `no_bug`
sentence on its own line, so each proof with no caught bug is named with its reason; the
explanation; the missed bugs; the model and the file.

- RULE-8, RULE-9, RULE-15: each `wherever the audit found a rule strong or weak` reads `wherever a rule has an audit entry`
- RULE-39: Wherever a rule has an audit entry, the rule screen carries an `Audit` panel that reads what the audit found: `No audit has read this rule yet.` where it has none; otherwise `Strong. It found nothing.`, `Weak.` followed by each finding, or `Spot-checked.` followed by `The spot tests found nothing.` and each `no_bug` sentence, then the model's explanation; an entry out of date opens the panel with `Out of date:` and the cell's reasons
- PROOF-147 (RULE-39): Open the regulated sample's export `RULE-2`, which no audit has read; its `Audit` panel's first line reads `No audit has read this rule yet.`
- PROOF-239 (RULE-39): Open the regulated sample's export `RULE-1` after its audit is given the verdict `spot-checked` and the `no_bug` sentence `No bug was planted: no bug is planted for an anchor's rule.`; its strong row reads `SPOT-CHECKED`, and its `Audit` panel reads `Spot-checked.`, then `The spot tests found nothing. No bug was planted: no bug is planted for an anchor's rule.`
- PROOF-240 (RULE-39): Open the regulated sample's login `RULE-1` after its audit is marked out of date on `code` at `a1b2c3d`; its strong row reads `OUT OF DATE` with the reasons `code changed since a1b2c3d` and `the last audit found it strong on 2026-09-13`, and the `Audit` panel opens with `Out of date:` and still reads `Strong. It found nothing.`
- PROOF-20 (RULE-20): reworded, `this page reads schema 15`. **The plan does not list it**: its text names the schema number, so it follows the tree.

`> Highest-Proof: 240`. Tests in `dev/test_purlin_report.py`; `dev/test_report_refresh.py`
names schema 15.

Fixtures `dev/fixtures/report/{regulated,team,solo}.json`: schema 15; `summary.audit` with
five counts; `spot_checked` and `audit_out_of_date` in every rollup, the summary and every
rule's flags; each audit with `no_bug` and `out_of_date`; the reason `no audit has read this
rule`; the sentence in its new form. No sample holds a spot-checked rule or one out of date:
PROOF-239 and 240 give one to the payload, as their words say.

### The long spec path at 390 pixels

`app.js` gains `pathText(path)`: the path is cut after each `/` and `_`, each part is set on
one line (`nowrap`) and a `<wbr>` stands between two parts. So a path breaks after a `/` or a
`_` and nowhere else. A part over 32 characters is left to break where it must, so the page
never scrolls sideways. It is used for the `Spec` row and the audit's evidence file on a
rule's screen. Seen at 390 pixels: `specs/billing/exports/regulated_` then
`export_of_signed_invoices.md`. No rule holds this; none was added, since the plan gives none.

### The look

`python3 dev/build_report.py`, then Playwright from the `.venv`: the regulated and team
samples, each given a spot-checked rule and one out of date, dark and light, at 1500, 1280,
1024, 768 and 390 pixels, the board with every spec open and a rule's screen for each of
`strong`, `weak`, `spot-checked` and `out of date`. On all 100 screens: 0 pixels of sideways
scroll, no pill, count, label, box or rule id on two lines, and every text at least 7:1 (4.5:1
for the dark theme's fail red and accent copper). `purlin_report` PROOF-66 and PROOF-104 pass.
The built page is not committed.

40 screenshots, opened and read, under
`/private/tmp/claude-501/-Users-richlabarca-LocalCode-purlin/0b911df6-a4da-4d86-9e09-dc4ed8c6bce2/scratchpad/d121-look/`,
named `<sample>-<theme>-<width>-<screen>.png`: `regulated` or `team`; `dark` or `light`;
`1500` or `390`; `board`, `rule-strong`, `rule-weak`, `rule-spot-checked`, `rule-out-of-date`.

## 6. Lines a person reads, chosen here

- `no audit has read this rule` (the plan's)
- `The spot tests found nothing. <the no_bug sentences>` (the plan's)
- `<part> changed since <sha7>`, `the last audit found it <verdict> on <date>` (the plan's)
- `No audit has read this rule yet.`, `Spot-checked.`, `Strong. It found nothing.`, `Weak.` (the plan's)
- `Out of date: code changed since a1b2c3d; the last audit found it strong on 2026-09-13`: the plan gives `Out of date:` and "the cell's reasons"; joining them with `; ` on one line, with no full stop, is this lane's choice, as the strong row joins them.
- `This data was written for schema 3 and this page reads schema 15. Run purlin:status to write it again.`

## 7. Seen to fail first, and broken on purpose

On `main`'s code under `scripts/`, the tests of `states` PROOF-286, 287, 290, 73 and 31,
`summary` PROOF-43 and 57 and `purlin_report` PROOF-239, 240, 147 and 20 fail. Each of
`states` 286/287, 288, 289, 290, 73, 31, `summary` 43/57 and `purlin_report` 239, 240, 147
was also broken once in the code and its test failed, then restored. Not broken on purpose:
`states` PROOF-168 to 170 and `summary` PROOF-50, whose code is `facts.py`, lane `signoff`'s.

## 8. Edits needed in files this lane does not own

- `docs/dashboard.md:158` still quotes `No audit has read this rule's text, proof and test yet.`; it reads `No audit has read this rule yet.` (lane `words`).
- `scripts/review/ai_audit.py:88`, `NO_AUDIT`: the same sentence (lane `audit`, in the plan).
- `scripts/review/ai_audit.py:141`, `is_read`: with this lane's payload a rule out of date carries its `audit`, so `not entry.get('audit')` no longer reads it again. `dev/test_ai_audit.py::TestTheVerdict::test_a_caught_bug_is_kept_while_its_test_and_code_stand` fails on this branch for that reason until lane `audit`'s `is_read` (the plan's section 4.4) lands.
- `scripts/export/package.py` `audit_counts` and `scripts/review/sign.py` still read three counts (lane `signoff`, in the plan).
- `dev/test_mcp_server.py::TestPackageHygiene::test_the_package_imports_nothing_outside_the_standard_library` fails on `main` too: the docstring line `from the one given, in that order; [] for a current entry."""` in `scripts/mcp/purlin/evidence.py` `audit_entry` opens with `from` and is read as an import (lane `evidence`: reword the line so it does not start with `from`).

## 9. Left open

- A rule with a `@manual` proof whose audit entry is out of date or `spot-checked` reads
  `checked at sign-off`, as it does for a `strong` entry: `RULE-16` names `weak` alone. No
  decision says whether `out of date` should show there.
- An out-of-date `weak` entry on a hand check also reads `checked at sign-off`.
- The path break at 390 pixels has no rule and no proof.
- `states` PROOF-159 still says `for its current hashes`; the plan does not reword it.
- `Strong` is shown by the summary's counts, so a project whose only audit entries sit on
  rules that fail, or on hand checks, shows no `Strong` column. That is as before.
