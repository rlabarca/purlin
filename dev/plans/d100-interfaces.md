# Decision 100 and 101: what was built

The plan is `d100-plan.md`. Ten lanes built it and one integration merged them into `main` on
2026-09-30. This file says where the build differs from the contracts, the ids each spec now
stands at, the test counts, and every word a lane chose that section 3 does not give.

## Where the build differs from the contracts

- **Fingerprint (C3).** `fingerprint()` takes one more keyword, `cache=None`, passed through to
  `code_part`, so a run hashes the project once. `untracked_parts()` treats an anchor's scope as
  empty whatever its file says. `code_hash` stays, since `code_part` calls it.
- **Counting (C4, C14).** `to_confirm` joins `summary.FOR_A_PERSON`, so the sign walk and
  drift's QA view list rules to confirm. The rollup carries no `does_not_apply` key: the status
  row and the dashboard count it from `rules[].does_not_apply`, which is `{why, signer, at}` or
  null. The signature a rule is decided by is the newest by commit date, then by its own
  timestamp. `dev/test_e2e_required_rules.sh` became `dev/test_e2e_anchor_rules.sh`.
- **Dashboard (C8, C14, C15).** A rule that does not apply counts as met in the Strong and
  Signed cells as well as Tests (RULE-9, PROOF-212). On the board it carries one badge,
  `DOES NOT APPLY`, not one per step. The regulated sample gained the pinned anchor
  `security_baseline`, which moved the counts of PROOF-7, 8, 54, 77, 81, 87, 133, 138, 167, 170,
  181 and 203. At integration its rollup and the team sample's were corrected to count the rule
  in one bucket, as the builder does (the regulated summary now counts 2 signed).
- **Reader (C1, C2, C13).** As the contracts give it. `spec_format.md` went to 21 and
  `anchor_format.md` to 11.
- **Run (C5, C11).** The feature-own filters in `purlin_run._audit` and `ai_audit._rules_of`
  were deleted as dead under C4. RULE-55 of `run_script` was reworded, since its clause about a
  required anchor became false. `ai_audit` RULE-2 still says the prompt ends on the test
  strength; RULE-30 overrides it for an anchor.
- **Signing (C10, C14).** The package's feature entry holds exactly five fields; the canonical
  form sorts keys, so no order is stated. PROOF-114 (one feature's code ends that feature's
  anchor signature alone) was deleted with its test. At a rule to confirm, the answer `sign`
  writes an ordinary signature, and the rule then waits as any rule does. PROOF-13 now names
  20 fields of signature format 12.
- **Upgrade (C12).** The fields print in the order Requires, Global, Scope, as C12's rule
  states, not as its sample. `> Scope:` is taken out of every anchor, a pinned copy included; a
  later sync brings it back and C13's warning then prints. PROOF-157 and PROOF-158 were added
  beyond the plan. The migrations table of `docs/raising-the-gate-and-upgrading.md` took the row
  `anchor-lines` at integration.
- **Skills.** PROOF-36 and PROOF-47 check a whitelist of metadata lines rather than that
  `> Requires:` is absent (decision 44). The quality guide's new paragraph has no rule.
- **Words.** `to_confirm` sits right after `to_test_by_hand` in the glossary and in the
  hard_gates table, the order lane counting built.
- **Frozen file.** `dev/run_project.py` `_spec` lost its `requires` parameter, its docstring
  clause and the line it wrote, in a commit of its own.

## Ids

| Spec | Highest-Rule | Highest-Proof |
|---|---|---|
| `specs/mcp/evidence.md` | 33 | 85 |
| `specs/mcp/states.md` | 101 | 247 |
| `specs/mcp/summary.md` | 15 | 39 |
| `specs/dashboard/purlin_report.md` | 65 | 214 |
| `specs/mcp/schema_spec_format.md` | 34 | 80 |
| `specs/mcp/specs.md` | 21 | 43 |
| `specs/run/run_script.md` | 86 | 260 |
| `specs/review/ai_audit.md` | 30 | 92 |
| `specs/review/signatures.md` | 95 | 189 |
| `specs/export/package.md` | 27 | 59 |
| `specs/init/update.md` | 46 | 158 |
| `specs/skills/skill_anchor.md` | 16 | 38 |
| `specs/skills/skill_build.md` | 18 | 47 |
| `specs/skills/skill_spec.md` | 24 | 54 |
| `specs/skills/skill_sign.md` | 24 | 53 |

Deleted: evidence RULE-3, RULE-23 with PROOF-4, 5, 35; states RULE-76 with PROOF-148, 149, and
PROOF-86, 180, 181; purlin_report PROOF-72; schema_spec_format RULE-5, RULE-25 with PROOF-5, 20,
21, 58, 59, 60; specs RULE-13, RULE-19 with PROOF-14, 36, 37, 38; signatures PROOF-114.

## Test counts

- Full sweep on `main` at `35ddcc29d`, `bash dev/run_tests.sh`: **2345 passed, 3 skipped in
  775.89s**, `>>> All Pytest Tests: PASSED`, `Suites: 5 passed, 0 failed`; the four shell suites
  passed, `E2E Anchor Rules` among them. The 3 skips are the Windows-only tests. Before
  decision 100 the sweep read 2291 passed.
- `python3 scripts/run/purlin_run.py --test --all` at `30c97d29b`: `Markers: 2387 tied to a
  test, 0 not tied.`, `Ran pytest, shell on 36 features.`, `87 proofs need Windows; this
  machine is macOS. Run purlin:test --remote.`, then `918 rules. 831 pass their tests. 0 are
  strong. 0 are signed.` and `Left to do:` / `  87 rules to test on Windows: purlin:test
  --remote` / `  831 rules to audit: purlin:audit`. No rule reads `failed`, `partial` or
  `no test`, and no warning prints. `security_no_dangerous_patterns` stands alone under
  `Anchors`; `schema_spec_format` is listed under `mcp`. With `--commit` the same lines and
  `Evidence committed.`, as `35ddcc29d purlin: evidence at 30c97d2`.
- Lane test files, before and after, as each lane reported: fingerprint 40 to 45; counting
  316 to 323; dashboard 193 to 198; reader 202 to 202; run 279 to 283; signing 183 to 197;
  upgrade 129 to 135; upstream shell checks 17 to 18; skills 121 to 128; words 10 to 10.

At integration, five commits beyond the lanes: the two samples' `security_baseline` rollups
(`b4bec22ed`), the frozen `_spec` helper (`778cb690e`), a docstring line of `status.py` the
package's import check read as an import (`083c99dfd`), the anchor test project of
`dev/test_signatures.py` ignoring `.purlin/report-data.js` as setup does, since an anchor's
code part is every tracked file (`3fde68711`), and the migrations table row (`ae6ee1184`).
Then the page rebuilt (`1df59ed3b`) and the two screenshots retaken (`30c97d29b`).

## Words chosen by a lane, word for word

### fingerprint

No new line in CLI output.

- `specs/mcp/evidence.md` description: "its own rule and proof lines, the files its `> Scope:` names, or for an anchor every tracked file but Purlin's records, and the files that carry its proof markers"
- RULE-2: "The `spec` part covers the spec's own rule and proof lines; editing a rule's text changes `spec` and no other part"
- RULE-30: "An anchor's `code` part covers every file git tracks but the records Purlin writes, so an edit to any other tracked file changes it and an untracked file does not"
- RULE-31: "Writing Purlin's records, the evidence under `.purlin/evidence/`, the evidence package, `.purlin/tests.md` and a signature under a `*.signatures/` folder, leaves an anchor's `code` part as it was"
- RULE-32: "An anchor's `code` part is taken the same on Windows, where git writes each text file out with CRLF, as the blob ids the commit holds"
- RULE-33: "A run with no feature named selects an anchor after an edit to any tracked file outside Purlin's records, with the reason `code changed since <sha7>`"
- `evidence_format.md`, the `spec` row: "the spec's own rule and proof lines."
- `evidence_format.md`, the `code` row: "for a feature, the tracked files the `> Scope:` entries reach, ... For an anchor, every tracked file but the records Purlin writes: `.purlin/evidence/` whole, results and package, `.purlin/tests.md`, and every `*.signatures/` folder under `specs/`. Any other change to the project changes it; writing a record does not"
- `evidence_format.md`: "A spec with no `> Scope:` line" became "A feature spec with no `> Scope:` line"

### counting

- Status skill Step 2: "The tool opens with `Purlin status: <project>, plugin <version>, gate <gate>`, then the table: a row per spec, most work left first, the anchors under `Anchors` above the rest under `Specs`, and a column only where the gate creates its cell. It is the dashboard's board as text, cell for cell."
- Status skill: "`Tests` is `<passed> of <rules>`, then `· <k> does not apply`, `· <k> partial` and `· <k> failing` where not zero; `partial` means the tests pass on one operating system and not another."
- Status skill closing table row: "| `<n> rules to test by hand`, `to confirm as not applying`, `to sign`, or `the version to tag` | `→ Run: purlin:sign` |"
- states RULE-97: "A feature's row counts its own rules only; an anchor's rules are counted in the anchor's row and in no feature's"
- states RULE-98: "An anchor's rule whose strong cell is met reads `strong` with the one reason `the AI audit alone judges an anchor's tests`, at every mutation setting, and the anchor's `Strong` cell names no test strength"
- states RULE-99: "Where the project has an anchor, the status table lists under its heading rule the line `Anchors`, the anchors' rows, the line `Specs`, then every other spec's row; with no anchor it prints neither line"
- states RULE-100: "A rule that a counting signature carrying `does_not_apply` binds reads `does not apply` in every cell up to the gate, each met and each with the one reason `by <signer>: <why>`; it is counted among the rules that pass, its row's `Tests` cell adds ` · <k> does not apply`, and nothing is left to do for it"
- states RULE-101: "Once that signature no longer binds the rule, and while the last signature for it carried `does_not_apply`, the rule reads its cells as usual and its `left` is `to_confirm`, before any other kind it would take"
- states reworded: RULE-26 "The project summary counts every spec's rules once, under the spec that owns them, anchors' included, and it adds `features` to the rollup's keys"; RULE-49 ends "...every cell after the spec's name reads the same characters in both"; RULE-72 "The status table's `Rules` cell reads the spec's rule count alone"; RULE-74 "Every rule entry carries `applies_to`, the spec it is listed under, and `code_hash`, the code part of that spec's fingerprint: its `> Scope:` files for a feature, and for an anchor every file git tracks in the project but the records Purlin writes"; RULE-27, PROOF-31 and PROOF-96 say schema 11; RULE-36 adds `· <k> does not apply`.
- summary RULE-12 "...under the spec that owns it, anchors' included"; RULE-4 gains "`rules to confirm as not applying`, `purlin:sign`"; RULE-8 opens "a rule left to confirm as not applying (`to confirm as not applying`)"; RULE-15 "The kind `to_confirm` stands after `to_test_by_hand` and before `to_sign` in `Left to do`, reading `1 rule to confirm as not applying: purlin:sign` for one rule and `<n> rules to confirm as not applying: purlin:sign` for any other count"

### dashboard

- purlin_report RULE-6: "Affordances are the unicode glyphs `▶`, `▼`, `▲`, `→`, `◐` and `◑` and no other, and the page draws no icon set"
- RULE-9: "`<n>` counting the rules whose strong cell reads `strong` or `does not apply`"; "`<n>` counting the rules whose signed cell reads `signed` or `does not apply`"
- RULE-12: "Both themes ship in the page. It sets no surface override, so it opens dark on the brand navy ground, and the toggle, a button showing `◐` in the dark theme and `◑` in the light, its hover and accessible name `Light theme` or `Dark theme`, the theme it turns to, swaps the ground, the ink and the mark to the other theme, and swaps back"
- RULE-13 gains: "`1 rule to confirm as not applying` is `To confirm`"
- RULE-35 example: "a count cell such as `42 · 2 no test` or `21 of 21` is one line"
- RULE-36: "A band counts the rules of the specs it holds; an anchor stands in no band, so the bands and the anchors' rules add up to the project's rules."
- RULE-47: "A spec's rows list its own rules, and its `Rules` cell reads their count, with no hover. A rule is addressed by its owner and its id together, so the rule screen, its heading and its tab open and name the rule of that owner wherever it was clicked"
- RULE-49 example: "`Rules 15`"
- RULE-55 gains: ", and a rule signed as not applying carries the one badge `DOES NOT APPLY`"
- RULE-64: "An anchor's `Strong` cell shows no test strength, whatever its record holds, because no code is broken on purpose for an anchor"
- RULE-65: "A rule a person signed as not applying reads `DOES NOT APPLY` in the neutral teal in every cell of its screen, each cell with its reason, and at the gate `signed` its `Signed` panel reads `Does not apply to this project: <why>. Signed by <signer name> (<signer>) at <at>.`; its spec's `Tests` cell reads `<passed> of <rules> · <k> does not apply`, counting it among the passed; and `To confirm` is a filter button where the payload lists the kind `to_confirm`"
- The regulated sample's pinned anchor `security_baseline`, source `https://github.com/acme/policies.git`, description "The security rules every project of the company keeps.", RULE-1 "A card number is never written to a file.", PROOF-1 "Pay with the card number 4111 1111 1111 1111, then read every file the app wrote; the number is in none of them.", the reason "the project stores no card data", signed by jane@acme.com (Jane Doe) at 2026-09-12T10:05:31Z. The team sample carries the same anchor, its RULE-1 left `to_confirm`, with "1 rule to confirm as not applying".
- `docs/dashboard.md`: "the theme button, which shows the glyph of the theme it turns to, `◐` in the dark theme and `◑` in the light, its hover naming that theme, `Light theme` or `Dark theme`."; "`the version to tag` is `To tag`, and `1 rule to confirm as not applying` is `To confirm`."; the `Rules` row "how many rules the spec has, as `16` | —"; the `Tests` row "`3 of 4 · 1 partial`: how many rules passed everywhere they ran, a rule signed as not applying among them, then `does not apply`, `partial` and `failing`"; the `Strong` row gains "and always for an anchor"; "A value never breaks inside itself: `1 of 1 · 1 does not apply` and `5 · 1 no test` stay on one line."; "`Rules 16`"; "An anchor's rules cover the whole project, and no code is broken on purpose for an anchor, so its `Strong` cell shows no test strength."; "A band counts the rules of the specs it holds; under 1024 pixels its count sits beneath its name. ... Pressing a spec opens it: its `> Description:` first, then its rules."; "A rule of a pinned anchor that a person signed as not applying carries the one badge `DOES NOT APPLY`, in teal."; "A rule signed as not applying reads `does not apply` in every cell, in teal, each with the reason `by <signer>: <why>`."; "A rule signed as not applying reads, under `Signed`, `Does not apply to this project: <why>. Signed by <signer name> (<signer>) at <date> <time> UTC.`"; "The theme button, `◐` or `◑`, switches between dark and light"; "`11 RULES TOTAL`"; the image alt text "the anchors checkout_design and security_baseline in the Anchors section".
- New and rewritten proofs PROOF-6, 7, 8, 20, 54, 71, 77, 81, 87, 94, 110, 113, 133, 138, 142, 163, 167, 170, 181, 182, 183, 185, 203 and 209 to 214 are worded in `specs/dashboard/purlin_report.md`.

### reader

- Spec format, under "Fields 0.9.5 wrote": "`> Requires:` and `> Global:` are not part of the format either, because every anchor covers the whole project. A spec that still carries one parses; the line is not read, and every status and test run warns of it with its fix: `login: > Requires: is not read, because every anchor covers the whole project. Run purlin:spec login.` `purlin:init --update` removes both."
- Anchor format intro: "An anchor is a set of rules for the whole project, kept under `specs/_anchors/` or opening `# Anchor:`. No spec names an anchor. An anchor uses the same two sections every spec uses, `## Rules` and `## Proof`, and the same rule and proof grammar (`spec_format.md`)."
- Anchor format template placeholder: "- RULE-1: <constraint that holds across the whole project>"
- Anchor format: "An anchor carries no `> Scope:`, and no spec carries `> Requires:` or `> Global:`. Each such line is not read, and every status and test run warns of it with its fix."
- Anchor format, "Editing a pinned anchor": "...which the next sync brings back. A rule that belongs only to this project goes in a local anchor of its own when it holds across the whole project, and in the spec of each feature it holds for when it does not."
- `dev/test_security.py` comment: "# Every executable language the anchor's rules name. Its tests read every file under scripts/, where all of Purlin's executable code lives."
- schema_spec_format RULE-19: "The code part of a feature spec's fingerprint hashes exactly the files `> Scope:` names, so an edit to any other file leaves it unchanged and a code change is told from a rule change"
- RULE-30: "A line opening `> Requires:` is warned of, naming the spec and `purlin:spec`, and is not read: the spec counts its own rules alone"
- RULE-31: "A line opening `> Global:` is warned of on any spec, a feature's or an anchor's, naming the spec and `purlin:spec`, and is not read"
- RULE-32: "A `> Scope:` line on an anchor is warned of, naming the anchor and `purlin:spec`, and is not read: an anchor's scope is empty, because an anchor covers the whole project"
- RULE-33: "An entry of an anchor's `> Scope:` line is never warned of as finding no file"
- RULE-34: "A pinned anchor whose copy carries `> Requires:`, `> Global:` or `> Scope:` is warned of in one line naming every such field, its source, and the owners of the source as the ones to take the lines out, and gets none of the lines a spec of this project gets for them"
- PROOF-71 to PROOF-80 are worded in `specs/mcp/schema_spec_format.md`.

### run

- run_script RULE-55, the replaced clause: "an anchor's code is every file git tracks but Purlin's own records, so an edit to any such file runs every anchor"
- RULE-86: "Above the gate `passed`, with `mutation_engine` other than `none`, `--audit` asks the breaks for no anchor, and an anchor's evidence gets no `audit.mutation`"
- PROOF-176, PROOF-90, PROOF-259 and PROOF-260 are worded in `specs/run/run_script.md`.
- ai_audit RULE-30: "The prompt of an anchor's rule ends on `Anchor: its rules cover the whole project, so its tests must check the whole project. No test strength is measured for an anchor.` in place of the test strength"
- PROOF-49, PROOF-91 and PROOF-92 are worded in `specs/review/ai_audit.md`.

### signing

- Walk prompt at a rule to confirm: `<anchor> <RULE-N>   confirm / sign / skip: `
- USAGE: `Usage: sign.py [<feature> [RULE-N ...]] [--all] [--note TEXT] [--does-not-apply TEXT] [--release NAME] [--project-root DIR]`
- `sign.py --help`, new usage line: `    sign.py <anchor> RULE-N [RULE-N ...] --does-not-apply "<why>"`
- `sign.py --help`: "The walk and `--all` visit every feature's rules before any anchor's. An anchor's rule is signed once, over every file of the project but Purlin's own records, so any change to the project ends that signature."
- `sign.py --help`: "**Not applying.** `--does-not-apply \"<why>\"` signs a rule of a pinned anchor, one carrying `> Source:`, as not applying to this project: an ordinary signature, over the same hashes, that carries the reason. It works at every gate. A rule of the project's own anchor that does not apply is deleted instead. Once such a signature has ended, the rule is left `to_confirm`: the walk stops at it with three answers, confirm (a new signature with the earlier reason), sign (it then waits as any rule does) or skip; `--all` and a bare feature leave it."
- `sign.py --help` exit codes: "a rule named is not one any spec has or, with `--does-not-apply`, not a rule of a pinned anchor"
- `signature_format.md`: line 1 row "`applies_to`, the spec that holds the rule"; line 5 row "`code_hash`: the files the `> Scope:` of `applies_to` names, each with its path and blob id; for an anchor, every file git tracks but Purlin's own records, as `evidence_format.md` gives them"; "A rule of a pinned anchor that does not apply to this project is signed with `purlin:sign <anchor> RULE-N --does-not-apply \"<why>\"`. The signature is made over the same seven lines as any other and carries the reason in `does_not_apply`, which, like `note`, is outside `signed_hash`: the signed commit is what holds it. No other rule is signed this way."; `applies_to` field "the spec that holds the rule, the same as `feature`"; `does_not_apply` field "the reason, as one line, a pinned anchor's rule does not apply to this project; null or absent for any other signature"; Current "taken again from the rule as it now stands in the spec that holds it"
- `package_format.md`: `scope` row "the spec's `> Scope:` entries, as written; `[]` for an anchor, whose rules cover the whole project"; "A feature entry holds exactly these five fields."; `statuses` row "A pinned anchor's rule a person signed as not applying reads `does not apply` in each, with the reason `by <signer>: <why>`"; signature `applies_to` "the spec that holds the rule"; `does_not_apply` "the reason a pinned anchor's rule does not apply to this project, where the signer signed it so; null otherwise"; `signatures` "every signature whose hashes still match the rule as it now stands, ordered by `at`."; kinds table row "| to_confirm | 1 rule to confirm as not applying, <n> rules to confirm as not applying | purlin:sign |"
- RULE-90 to RULE-95, PROOF-179 to PROOF-189 (signatures) and RULE-26, RULE-27, PROOF-56 to PROOF-59 (package) are worded in their specs.

### upgrade

- The migration line, filled: `removed from specs/_anchors/proof_common.md: > Scope:`; the fields in the order Requires, Global, Scope, as `removed from specs/_anchors/proof_common.md: > Global: and > Scope:`.
- update RULE-46: "The lines by which 0.9.5 named an anchor go: `> Requires:` and `> Global:` from every spec and `> Scope:` from every anchor, each with the `>` lines continuing it; each file is backed up first and named in one line, `removed from <path>: <fields>`, and each anchor that a spec's `> Requires:` named and that carried no `> Global: true` is kept and named in one line with the specs that named it and the command that moves a rule into them"
- Docstrings: "Anchors are exempt, because an anchor names no files."; "Released 0.9.5 let a spec name the anchors it required and an anchor say it was global or name the files it covered. Every anchor covers the whole project now, so > Requires: and > Global: go from every spec and > Scope: from every anchor, each with the > lines continuing it. Only the lines above the first section heading are read."; "No spec names an anchor, and no anchor names files: the lines go."
- At integration, `docs/raising-the-gate-and-upgrading.md`'s migrations table row: "| `anchor-lines` | removes `> Requires:` and `> Global:` from every spec and `> Scope:` from every anchor, and names each anchor that specs named, with the specs and the command that moves a rule into them |"

### upstream

- Anchor authority suite: "--- 7: a pinned source that carries > Scope: ---"; "the status names the source's owners once and warns of nothing else"; "the copy did not keep its source's > Scope: line"; header comment "The project owns the rules in a local anchor of its own beside it, and a sync never touches those. A rule a consumer does add to the pinned copy does not survive the next sync. A pinned copy is written as its source holds it, and a field in it Purlin does not read on an anchor is warned of in the status, naming the source's owners as the ones to take it out."; fixture comment "The published anchor as a 0.9.5 anchor repo may still hold it, with a scope."
- External refs suite: "--- 6: each spec counts its own rules ---"; "the feature counts its one rule, the anchor its two, the project three"; "6. a feature beside the anchor counts its own rules, the anchor its own"

### skills

- Anchor skill, opening: "An anchor is a set of rules for the whole project: a security policy, an API contract, a brand rule. Its tests check the whole project, and each of its rules is counted, audited and signed once. No spec names an anchor."
- Anchor skill, Changing a pinned rule: "The pinned copy stays untouched." and "...is signed by a person in the project as not applying, with the reason: `purlin:sign <anchor> RULE-N --does-not-apply \"<why>\"`. A rule of the project's own anchor that does not apply is deleted."
- Build skill: "Read the feature spec. Every anchor's rules hold across the whole project, so code you write keeps them too; their tests are the anchors' own and `purlin:test` runs them after any change."
- Sign skill, Step 2: "The walk reads the rules whose `left` is `to_test_by_hand`, a `@manual` proof a person checks, `to_confirm`, a pinned anchor's rule whose signature as not applying ended, or `to_sign`, ..." and "1 rule to confirm as not applying: purlin:sign".
- Sign skill, Step 3: "A rule to confirm stops the walk on `security_baseline RULE-4 was signed as not applying by jane@acme.com: the project stores no card data. Confirm it still does not apply?` with three answers: confirm, which signs it again with the earlier reason; sign it as applying after all, after which it waits as any rule does; or skip. `--all` confirms none."; "with nothing waiting it prints `Nothing is waiting for someone to test by hand or to sign.`"; "the person's line becomes the signature's note, and an empty line signs it with none."
- Sign skill, Step 4: `sh ".../sign.py" <anchor> RULE-N [RULE-M ...] --does-not-apply "<why>"`, then "The second line signs a pinned anchor's rule that does not apply here, with the person's reason, at any gate; it then reads `does not apply` and counts as met until any change to the project ends it. Any other rule is refused, since a rule of this project that does not apply is deleted."
- Sign skill, reworded to hold 179 lines: "**Skip.** Move on and leave the rule as it is. A skipped rule waits again next time."; "Never narrow a rule or a proof to make an observation disappear. That lowers the claim instead of strengthening the evidence."; "It carries the rule text, the proof text, the test body, the test strength beside `min_strength`, and what the last audit found. Judge it against `references/review_criteria.md`."; "The version comes from the `VERSION` file, ..."; "It prints:".
- Agent: "...every marker comment in test code naming it, ..., as `references/formats/marker_format.md` spells it, matched whole so `login` leaves `login_oauth` alone;"
- Quality guide, "### A rule for the whole project": "A rule that must hold across the whole project, such as no secret in the code, is written once in an anchor. Its tests check every file of the project the rule speaks of, and the rule is counted, audited and signed once. No spec names an anchor. A rule that several features share and that cannot be checked across the whole project is not an anchor's: write it in the spec of each feature that needs it, in that feature's words." Then: "A rule of a pinned anchor that no test in this project can show, because it does not apply here, is signed by a person in the project as not applying, with the reason: `purlin:sign <anchor> RULE-N --does-not-apply \"<why>\"`. A rule of the project's own anchor that does not apply is deleted."
- Quality guide: "on a rule pinned from an anchor" became "on a rule of a pinned anchor".
- skill_anchor description: "An anchor is a set of rules for the whole project"; skill_spec_from_code RULE-43: "in the order its step `Shared rules first` sets".

### words

- Glossary: "A rule is counted once, under the spec that owns it."; `to confirm as not applying` among the printed kinds right after `to test by hand`; `does not apply` added to the words of each of the three cells; "A rule that reads `does not apply` is met in every cell."
- hard_gates: "No code is broken on purpose for an anchor: the AI audit alone judges its tests, and its rule's strong cell, once met, reads `strong` with the reason `the AI audit alone judges an anchor's tests`."; "A rule that reads `does not apply` is counted at every step. A rule is counted once, under the spec that owns it."; the Left to do row `to_confirm` | "at any gate, the last signature for a rule of a pinned anchor said it does not apply, and that signature has ended; the rule takes this kind before any other" | `<n> rules to confirm as not applying` | `purlin:sign`; "`1 rule to confirm as not applying`"; "An anchor's code is every file of the project but Purlin's own records, so any change to the project makes its results out of date."
- purlin_commands: "With no argument it walks the rules waiting for someone to test by hand, to confirm as not applying or to sign."; the exit-1 list gains "a rule named with `--does-not-apply` that is not a pinned anchor's"; "`purlin:sign --does-not-apply` refuses, and writes nothing, with one of three lines:"
- RELEASE_NOTES: "- **A rule of a pinned anchor that does not apply to this project** is signed with `purlin:sign <anchor> RULE-N --does-not-apply \"<why>\"`. It then reads `does not apply` in every cell, counts as met, names who signed it, and the evidence package carries the reason. Any change to the project ends that signature, and the rule is left to do as `1 rule to confirm as not applying: purlin:sign`. A rule of the project's own anchor that does not apply is deleted."; "- A pinned anchor is copied as its source holds it. A `> Requires:`, `> Global:` or `> Scope:` line in it is warned of on every status and test run, naming the source's owners as the ones to take it out."; "- **The formats** stand at spec 21, anchor 11, evidence 7, signature 12, package 5 and marker 3, and the dashboard's data at schema 11."; "3. `anchor-lines`: takes out `> Requires:` and `> Global:` from every spec, and `> Scope:` from every anchor, one line per file, `removed from <rel>: <fields>`. It keeps every anchor, and for each anchor that specs named it prints one line naming them and the command that moves a rule into them:"; the words-table row "| `> Requires:`, `> Global: true` | none: every anchor covers the whole project |".
- docs/specs-and-anchors.md: "An anchor is a set of rules for the whole project, such as a security policy or a rule about what the code must never hold."; the heading "### What an anchor covers"; "In the status table the anchors stand first, under the line `Anchors`, and every other spec follows under `Specs`. Each row counts its own rules, and the summary counts each rule once."; "A spec that carries `> Requires:` or `> Global:`, or an anchor that carries `> Scope:`, is warned of, and the line is not read:"; `purlin:sign security_baseline RULE-4 --does-not-apply "the project stores no card data"`.
- docs/review-and-signing.md: "`to test by hand`, `to confirm` or `to sign`"; "Three lines of `Left to do` are a person's work, and each names `purlin:sign`:"; "| `<n> rules to confirm as not applying: purlin:sign` | a person signed a rule of a pinned anchor as not applying to this project, and a change to the project ended that signature; at every gate | confirm it still does not apply, or sign it as applying |"; "At the gate `signed` a rule's signed cell reads one of four words:" with "| `does not apply` | a signature that counts says a rule of a pinned anchor does not apply to this project; every cell reads it, and each is met |"; "purlin:sign <anchor> RULE-N --does-not-apply \"<why>\"  a pinned anchor's rule that does not apply here"; "An anchor's rule gets one file, under its anchor."; the section "## A rule that does not apply": "The signature is an ordinary one, in one signed commit, carrying the reason. The rule then reads `does not apply` in every cell, with the reason `by <signer>: <why>`, and counts as met; its row's `Tests` cell names it, `7 of 8 · 1 does not apply`, and the evidence package carries the reason. Any change to the project ends that signature, and the rule is left to do as `1 rule to confirm as not applying: purlin:sign`. The walk stops at it:" ... "Confirming writes a new signature with the same reason. You may instead sign it as applying after all, and it then waits as any rule does, or skip it. `purlin:sign --all` does not confirm one."; "the code the feature's `> Scope:` lists, or for an anchor every file of the project but Purlin's own records,"
- docs/working-together.md: "Like every anchor rule it holds across the whole project, and its tests check the whole project."

## Words chosen for the owner to read

Section 3 of `d100-plan.md`, as it was built:

| Where | What it says |
|---|---|
| A spec's warnings (C2) | `login: > Requires: is not read, because every anchor covers the whole project. Run purlin:spec login.`; `<name>: > Global: is not read, because every anchor covers the whole project. Run purlin:spec <name>.`; `<name>: > Scope: is not read on an anchor, because an anchor covers the whole project. Run purlin:spec <name>.` |
| The status table (C7) | the label lines `Anchors` and `Specs` where the project has an anchor; `(anchor)` and ` (+<k> shared)` go |
| The dashboard (C8) | the section label `Anchors` (decision 100); the `Rules` cell a count alone |
| An anchor's strong cell (C5) | `the AI audit alone judges an anchor's tests` |
| The audit's prompt (C11) | `Anchor: its rules cover the whole project, so its tests must check the whole project. No test strength is measured for an anchor.` |
| The review criteria, a paragraph of "What the audit looks for" | `An anchor's rule covers the whole project. Its test is strong only when it checks every file of the project the rule speaks of, not a sample of them and not one feature's files. No code is broken on purpose for an anchor, so the audit alone judges its tests.` |
| The upgrade (C12) | the migration's description, `removed from <rel>: <fields>`, and the per-anchor line |
| A pinned anchor whose source carries the lines (C13) | `<anchor>: its source, <url>, carries <fields>, which Purlin does not read on an anchor, so the line is read as nothing. Ask the owners of <url> to take it out, then run purlin:anchor sync <anchor>.` (plural: `the lines are`, `take them out`) |
| A rule that does not apply (C14) | the cell word `does not apply` with `by <signer>: <why>`; the badge `DOES NOT APPLY`; the rule's page `Does not apply to this project: <why>. Signed by <signer name> (<signer>) at <at>.`; the Tests cell `7 of 8 · 1 does not apply`; `Left to do` `1 rule to confirm as not applying: purlin:sign` and `<n> rules to confirm as not applying: purlin:sign`; the button `To confirm`; the walk's stop `<anchor> <RULE-N> was signed as not applying by <signer>: <why>. Confirm it still does not apply?` |
| Signing a rule as not applying (C14) | `--does-not-apply needs the reason the rule does not apply to this project.`; `--does-not-apply names a pinned anchor and the rules it carries.`; `<feature> <RULE-N> is not a rule of a pinned anchor, so it cannot be signed as not applying. A rule of this project that does not apply is deleted: run purlin:spec <feature>.`; the usage line `purlin:sign <anchor> RULE-N --does-not-apply "<why>"  Sign a pinned anchor's rule as not applying to this project` |
| The glossary, C14 | `**does not apply**: the word a rule of a pinned anchor reads once a person in the project signs it as not applying, with the reason. It counts as met, and like every anchor signature it ends on any change to the project, so the person confirms it again.` |
| `references/hard_gates.md`, C14 | `A rule of a pinned anchor that does not apply to this project is signed with purlin:sign <anchor> RULE-N --does-not-apply "<why>". It then reads does not apply in every cell and counts as met; any change to the project ends that signature, and the rule is left to confirm.` |
| The anchor format, C14 | `A rule of a pinned anchor that no test in this project can show, because it does not apply here, is signed by a person in the project as not applying, with the reason. A rule of the project's own anchor that does not apply is deleted.` |
| The theme button (C15) | the glyph `◐` or `◑`; the hover and accessible name `Light theme` or `Dark theme` |
| The anchor format, a section `What an anchor covers` | `Every rule of an anchor holds across the whole project, and its tests check the whole project. The project is every file git tracks but the records Purlin writes: the results of a run and the evidence package under .purlin/evidence/, the table .purlin/tests.md, and the signatures. Any change to the project ends an anchor's results and its signatures, so at the gate signed an anchor is in practice signed last. No code is broken on purpose for an anchor: the AI audit alone judges its tests. A rule that cannot be checked across the whole project is not an anchor's; write it in the spec of each feature that needs it, in that feature's words.` |
| The spec format, the `> Scope:` row's last sentence | `An anchor carries none: its rules cover the whole project, and a > Scope: line on an anchor is warned of and not read.` |
| The glossary | `**anchor**: a set of rules for the whole project, kept under specs/_anchors/ or opening # Anchor:. Its tests check the whole project, and each of its rules is counted, audited and signed once. No spec names an anchor.` |
| `references/hard_gates.md` (replacing the sentence at line 186) | `An anchor's rule is signed once, over every file of the project but Purlin's own records, so any change to the project ends that signature.` |
| The anchor skill, `create` | `Give it a > Description: and, when it helps the reader, a > Type:. An anchor carries no > Scope:: its rules cover the whole project and its tests check the whole project. A rule that cannot be checked across the whole project is not an anchor's: write it in the spec of each feature that needs it, with purlin:spec <feature>.` |
| The anchor skill, `Changing a pinned rule` | `A rule that belongs only to this project goes in a local anchor of its own when it holds across the whole project, and in the spec of each feature it holds for when it does not.` |
| The anchor skill, `When you are done` | `Anchor created: → Run: purlin:build <name>, which writes tests that check the whole project` in place of the line offering `> Requires:` |
| The build skill, `Loading the rules` | `Read the feature spec. Every anchor's rules hold across the whole project, so code you write keeps them too; their tests are the anchors' own and purlin:test runs them after any change.` |
| The spec skill, a line of its warnings | `A spec that carries > Requires: or > Global:, or an anchor that carries > Scope:, is warned of: take the line out. Where a rule of an anchor holds only for some features, write it in each of their specs instead.` |
| The spec-from-code skill, step 4 and `docs/spec-from-code.md` | `Shared rules first. Rules that hold across the whole project, it writes once in an anchor, with purlin:anchor create <name>. A rule that several features share and that does not hold everywhere is written in each of their specs.` |
| The sign skill, Step 5 | `The script writes one file per rule under specs/<category>/<feature>.signatures/ and makes one signed commit for all of them.` (the clause about an anchor's rule in each feature goes) |
| The agent, `Renaming a feature` | `A feature's name is carried in four places` (the `> Requires:` entry goes) |
| The status skill | the example table of C7 in place of the one with `(anchor)` and `(+6 shared)`; `Rules counts the spec's rules.` |
| `RELEASE_NOTES.md` 0.10.0 | `**An anchor is a set of rules for the whole project.** Its tests check the whole project, and each of its rules is counted, audited and signed once. A rule that holds only for some features is written in each of their specs.`; `**A spec names no anchor.** > Requires: and > Global: are not read, and neither is > Scope: on an anchor; each is warned of with its fix, and purlin:init --update takes them out.`; `**A feature's row counts its own rules.** The dashboard lists the anchors in a section of their own, Anchors, above the spec table; the counts (+8) and (+8 shared) are gone.`; `**Any change to the project ends an anchor's results and signatures**, but for the records Purlin writes: .purlin/evidence/, .purlin/tests.md and the signatures.`; `**No test strength for an anchor.** Its code is not broken on purpose; the AI audit alone judges its tests.`; the format numbers of C9 |
| The anchors slide (section 6, step 9) | title `Anchors: rules for the whole project`; first card `Written once, for the whole project` / `Write a rule that must hold everywhere, such as no secret in the code. Its tests check the whole project, and each rule is counted, audited and signed once.`; fourth card `Design standards too` / `Design publishes its standards as an anchor. Tests that read every screen check them.`; the callout `<b>Any change to the project ends an anchor's results:</b> its tests run again, and at the gate signed it is signed last.`; the lead `An anchor is a set of rules written once for a whole project, or for many projects.`; the notes' first two sentences `An anchor is a set of rules for the whole project. A spec names no anchor, and a rule that holds only for some features is written in each of their specs.` The second and third cards stand. |

`docs/` pages take these words where they say the same thing (lane `words`).

The slide row above is replaced by the owner's wording in `handoff.md`, "What is left"; the slide
is not built yet.
