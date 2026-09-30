# Decision 100: an anchor is a set of rules for the whole project

Written by the planning agent on 2026-09-30, against `main` at `194d51d53`. It builds decision
100 of `three-levels.md` and nothing else. Ten lanes run at once, each owning files no other
lane writes, then one integration agent alone. Section 2 is the contract: every lane builds to
it and none chooses. Section 7 holds the owner's answers to the three questions this plan
raised, recorded as decision 101; the contracts carry them (C12, C13, C14), with the owner's
request for the theme button (C15).

## 1. Rules for every lane

Phase 3's rules (`phase3-plan.md` section 1) apply as written, with these names and additions.

- **Worktree, branch, scratch.** Lane `<lane>` works in
  `/Users/richlabarca/LocalCode/purlin-wt/d100-<lane>` on branch `lane/d100-<lane>`, made from
  `main` once the owner has answered section 7, with its own scratch folder
  `<session scratchpad>/lane-d100-<lane>`. Lane `dashboard` alone starts from
  `lane/anchors-section` (section 4, L3). A lane writes only the files it owns (section 4).
- **Environment.** `export PATH=/opt/homebrew/opt/dotnet@8/bin:/Users/richlabarca/LocalCode/purlin/.venv/bin:$PATH`
  first. A lane runs its own test files whole with `.venv/bin/python -m pytest <files> -q`, its
  shell suites with `bash <file>`, then `bash dev/run_tests.sh --fast` in the worktree.
- **Frozen during the fan-out:** `dev/skill_checks.py`, `dev/mcp_project.py`,
  `dev/sign_project.py`, `dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`,
  `dev/fake_claude.py`. A lane that needs a helper writes it in its own test file. The one change
  one of them needs is integration's (section 6, step 2).
- **No generated file is staged:** `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`, `docs/images/*.png`,
  `dev/plans/deck/*.png`. A lane may build them locally to run its tests.
- **Proofs.** Every proof written or rewritten holds one case in at most 60 words and has a
  marked test of its own. A new rule or proof takes the next free number of section 5 and raises
  `> Highest-Rule:` / `> Highest-Proof:` to it. A number is never reused.
- **Clean release** (decision 44). What decision 100 retires is deleted outright: its code, its
  rules, its proofs and their tests. No test that a removed thing is absent, no compatibility
  reader, nothing added to `dev/test_vocabulary.py`. What the upgrade from 0.9.5 needs (lane
  `upgrade`) is the one exception in code; `RELEASE_NOTES.md` is the one place history is kept.
- **Formats.** A change to a format's parsing or emission updates its file under
  `references/formats/` in the same commit, with the number C9 gives.
- **Instruction lengths** (decision 80): a change to a skill or to `agents/purlin.md` stays under
  its ceiling: status 100, test 120, build 130, init 250, audit 105, sign 185, export 90, spec
  210, spec-from-code 130, drift 150, anchor 160, agent 135. Status (100) and build (130) sit at
  their ceiling today, so every line added there cuts one.
- **Deliberate breaks.** Each lane breaks its most important change on purpose (named in its
  section) and sees its own test fail, then restores the file with `git checkout -- <that file>`,
  never `git checkout -- specs/`. The break runs only under a test that uses `dev/fake_claude.py`
  or no model, with `PATH` holding no real `claude`, and reaches no git host, `gh`, `az` or
  network service.
- **A call no decision makes and this plan does not make:** build the rest, leave that thing as
  it is, report it.
- **Commits** on the lane branch with the prefixes of `references/commit_conventions.md`, each
  ending with the attribution lines the session gives. No push, no tag, no pull request, no
  `purlin:audit`, no `purlin:sign`, no real `claude`.
- **Before merging:** rebase on `main`, rerun the lane's files and `--fast`. Section 6 says which
  failures in files a lane does not own are expected between merges; report every other one.
- **Report:** each spec's `> Highest-Rule:` and `> Highest-Proof:` after the work; tests before
  and after; every rule and proof deleted; every call left; every word the lane chose that
  section 3 does not give; every failure in a file it does not own.

## 2. Contracts

What two lanes share, fixed word for word. `<...>` is filled in.

### C1. The parsed spec (`specs.scan_specs`), lane `reader`

- Each spec's dict loses `requires` and `is_global`.
- It gains `unread_fields`: the list of `'Requires'`, `'Global'` and `'Scope'`, in that order,
  holding each field whose line the spec carries and Purlin does not read. `'Requires'` and
  `'Global'` are listed for any spec carrying a line that opens `> Requires:` or `> Global:`,
  whatever its value; `'Scope'` only for an anchor carrying `> Scope:`. Empty otherwise.
- An anchor's `scope` is `[]` whatever its file says.
- Deleted from `scripts/mcp/purlin/specs.py`: `rule_refs`, `global_anchors`,
  `REQUIRES_NOT_ANCHOR`, `_REQUIRES_RE`'s use in the dict, `_GLOBAL_RE`'s use in the dict (the
  two patterns stay only as the readers of `unread_fields`).
- A spec's rules are `info['rule_order']` and `info['rules']`; no function lists another spec's
  rules inside it.

### C2. The three warnings, lane `reader`

Constants in `scripts/mcp/purlin/specs.py`, each taking the spec's name twice, at the start and in the command:

```
UNREAD_REQUIRES = '%s: > Requires: is not read, because every anchor covers the whole project. Run purlin:spec %s.'
UNREAD_GLOBAL   = '%s: > Global: is not read, because every anchor covers the whole project. Run purlin:spec %s.'
UNREAD_SCOPE    = '%s: > Scope: is not read on an anchor, because an anchor covers the whole project. Run purlin:spec %s.'
```

Filled in:

```
login: > Requires: is not read, because every anchor covers the whole project. Run purlin:spec login.
security_no_dangerous_patterns: > Global: is not read, because every anchor covers the whole project. Run purlin:spec security_no_dangerous_patterns.
security_no_dangerous_patterns: > Scope: is not read on an anchor, because an anchor covers the whole project. Run purlin:spec security_no_dangerous_patterns.
```

`spec_mistakes` returns them after its first five kinds, in place of the `> Requires:` kind it
drops: every `UNREAD_REQUIRES` line sorted by spec name, then every `UNREAD_GLOBAL`, then every
`UNREAD_SCOPE`. They print wherever the other spec mistakes print: the status, every test run,
the dashboard's warnings. Nothing is refused.

### C3. The fingerprint and the project, lane `fingerprint`

In `scripts/mcp/purlin/fingerprint.py`:

```python
# The records Purlin itself writes, which no anchor's code part reads:
# the results of every run and the evidence package, the tests table a
# run renders, and the signatures.
RECORDS = (':(exclude).purlin/evidence',
           ':(exclude).purlin/tests.md',
           ':(exclude,glob)specs/**/*.signatures/**')

def project_files(project_root): ...   # every tracked file but RECORDS, sorted
def project_hash(project_root): ...    # sha256 over '<path> <blob>' of project_files,
                                       # blobs read from the working tree, as _files_part does
def code_part(project_root, info, cache=None): ...
    # project_hash for an anchor (info['is_anchor']), code_hash(info['scope']) otherwise.
    # `cache` is a dict a caller passes to take the project hash once for many anchors.
```

- `project_hash` equals `_files_part(project_root, project_files(project_root))`. It may read
  the unchanged files' blob ids from `git ls-files -s -z` and hash only the files
  `git ls-files -m -z` names, so a large project is not read whole on every status.
- `fingerprint(...)['code']` is `code_part`. The `spec` part hashes the spec's own rule and proof
  lines only. `counted_specs` is deleted.
- An untracked file selects an anchor only where it sits beside one of the anchor's marker files,
  as for any spec (the anchor's scope is `[]`). `incomplete_reason` is unchanged: an anchor is
  never incomplete.
- A run with no feature named selects an anchor whenever `project_hash` differs from the stored
  `code` part, with the reason `code changed since <sha7>` it already gives.

### C4. The payload, schema 11, lane `counting`

`SCHEMA_VERSION = 11` in `scripts/mcp/purlin/payload.py`.

- `features[]`: `requires` and `is_global` go. `is_anchor` stays. An anchor's entry carries
  `scope: []`, `incomplete: false`, `incomplete_reason: null` and `test_strength: null`, the last
  whatever its evidence holds.
- `features[].rules[]`: each spec lists its own rules and no other. `label` goes from every rule
  entry. `feature` and `applies_to` both name the spec the rule is listed under. `code_hash` is
  `fingerprint.code_part` of that spec, so an anchor's rule carries `project_hash`.
- A feature's `rollup` counts its own rules, so a feature of 11 passing rules beside an anchor of
  8 reads `11 of 11`. `summary` counts every spec's rules once, anchors' included; its keys do
  not change.
- `payload._consumers` is deleted. `states.rule_cells`' input loses `consumers` and gains
  `anchor` (bool). For an anchor's rule the caller passes `test_strength: None` and
  `strength_missing: ''`.
- The payload lists features by name, as now. Each surface puts anchors first (C7, C8).

### C5. The strong cell of an anchor's rule, lane `counting`

In `scripts/mcp/purlin/states.py`: `AUDIT_ALONE = "the AI audit alone judges an anchor's tests"`.
An anchor's rule whose strong cell is met reads `strong` with the one reason `AUDIT_ALONE`, in
place of `no mutation score measured`, at every mutation setting. It never reads
`strength not measured: ...` and never `strength <p>% under <m>%`. Every other word of the cell
is unchanged.

### C6. The rule's label, lanes `counting`, `dashboard`, `run`

Every reader of `rule['label']` drops it, because every listed rule is the spec's own:
`board.py`, `payload.py`, `summary.py`, `drift.py` (lane `counting`); `scripts/report/src/app.js`
(lane `dashboard`); `scripts/review/ai_audit.py`'s `is_read` (lane `run`).

### C7. The terminal status table, lane `counting`

`board.shared_counts` is deleted. `board.rules_cell(rollup)` returns the rule count alone, `'%d'`.
`board.row_cells(name, rollup, gate, proofs=1)` loses `shared`. `status._row` adds no
` (anchor)`. Where the project has at least one anchor, the table's first line under the heading
rule is `Anchors`, then the anchors' rows sorted as rows are sorted now, then `Specs`, then every
other spec's row; with no anchor there is no label line. The two label lines stand in the `Spec`
column, two spaces in like every row:

```
  Spec                            Rules  Proofs          Tests
  ─────────────────────────────────────────────────────────────
  Anchors
  security_no_dangerous_patterns  8      91              8 of 8
  Specs
  billing                         14     22 · 2 no test  12 of 14 · 1 partial · 1 failing
  login                           11     20              11 of 11
  ─────────────────────────────────────────────────────────────
```

### C8. The dashboard, lane `dashboard`

- The `Anchors` section of `lane/anchors-section` stands: above the spec table, headed `Anchors`
  in the section labels' small capitals, the same columns, under the same filters, no
  `(anchor)`, no band.
- The `Rules` cell reads the spec's rule count alone, with no hover, for every spec. `(+<k>)` and
  its hover `<n> rules of its own, and <k> more it must also meet, from shared rules:` go.
- An anchor's `Strong` cell shows no strength.
- The fixtures under `dev/fixtures/report/` are payloads at schema 11 (C4).
- `dev/test_states.py`'s `DASHBOARD_ROWS` head selector becomes
  `Array.from(document.querySelector('.th').children)` (lane `counting` makes this edit; lane
  `dashboard` drops it from the branch it starts from).

### C9. Format and schema numbers

| File | Now | After | Why |
|---|---|---|---|
| `references/formats/spec_format.md` | 20 | 21 | `> Requires:` removed; a field on an anchor is not read |
| `references/formats/anchor_format.md` | 10 | 11 | `> Scope:` and `> Global:` removed; what an anchor covers |
| `references/formats/evidence_format.md` | 6 | 7 | the `spec` part is the spec's own; an anchor's `code` part is the project |
| `references/formats/signature_format.md` | 11 | 12 | `applies_to` is always the rule's own spec; an anchor's `code_hash` is the project; the optional field `does_not_apply` (C14) |
| `references/formats/package_format.md` | 4 | 5 | a feature's `requires` field removed; a signature's `does_not_apply` (C14) |
| `references/formats/marker_format.md` | 3 | 3 | unchanged |
| payload `schema_version` | 10 | 11 | `requires`, `is_global`, `label`, `consumers` removed; a rule's `does_not_apply`, the kind `to_confirm` (C14) |

`specs/review/signatures.md` RULE-9 says `signature format 12`.

### C10. Signing, lane `signing`

- An anchor's rule is signed once: one file under `specs/_anchors/<anchor>.signatures/`, its
  `applies_to` the anchor, made over `project_hash`. A change to any tracked file outside
  `RECORDS` ends it; writing results, a signature or the package does not.
- `sign.listings_to_sign` is deleted; `sign.rule_entry` returns the one listing.
- The walk and `--all` visit every feature's rules before any anchor's, each group in the order
  the walk uses now. Nothing is refused on that account.
- The package's feature entry holds `name`, `spec`, `scope`, `anchor`, `rules`, in that order;
  an anchor's `scope` is `[]`.

### C11. The run and the audit, lane `run`

- The breaks are asked for no anchor: `measured` in `purlin_run.py` leaves out every spec whose
  `is_anchor` is true, so no `audit.mutation` is written for an anchor.
- An anchor's tests run like any spec's; the audit reads an anchor's rules as the anchor's own.
- The audit's reading carries `anchor` (bool). For an anchor's rule `model_prompt` ends on
  `Anchor: its rules cover the whole project, so its tests must check the whole project. No test strength is measured for an anchor.`
  in place of `Test strength: ...`, and `render` prints nothing of strength.

### C12. The upgrade from 0.9.5, lane `upgrade` (decision 101)

A migration with id `anchor-lines`, after `design-refs` in `MIGRATIONS`, described
`take out > Requires: and > Global: from every spec, and > Scope: from every anchor`. It backs
each file up as every migration does, removes each such line (a `>` continuation line with it),
and prints for each file

```
removed from <rel>: > Requires:
removed from <rel>: > Scope: and > Global:
```

the fields in the order Requires, Global, Scope, joined `, ` with ` and ` before the last. It
keeps every anchor, and then prints, for each anchor that one or more specs named in
`> Requires:` and that carried no `> Global: true`,

```
proof_common: its rules now cover the whole project, where 1 spec named it: sync_status. A rule that holds only there belongs in that spec: run purlin:spec proof_common.
proof_common: its rules now cover the whole project, where 3 specs named it: a, b, c. A rule that holds only for some of them belongs in each of their specs: run purlin:spec proof_common.
```

A `> Requires:` name that is no anchor of the project gets no such line.

### C13. A pinned anchor whose source carries the lines, lane `reader` (decision 101)

`add` and `sync` copy the source unchanged. A pinned anchor (one carrying `> Source:`) whose
`unread_fields` is not empty gets one line in place of C2's lines, naming every such field, from
`spec_mistakes`, sorted by name with C2's `UNREAD_SCOPE` lines:

```
PINNED_UNREAD = '%s: its source, %s, carries %s, which Purlin does not read on an anchor, so %s read as nothing. Ask the owners of %s to take %s out, then run purlin:anchor sync %s.'
```

filled with the anchor's name, the `> Source:` URL as the spec reader splits it (no path), the
fields joined as C12 joins them, `the line is` or `the lines are`, the URL again, `it` or `them`,
and the name:

```
security_baseline: its source, https://github.com/acme/policies.git, carries > Scope:, which Purlin does not read on an anchor, so the line is read as nothing. Ask the owners of https://github.com/acme/policies.git to take it out, then run purlin:anchor sync security_baseline.
security_baseline: its source, https://github.com/acme/policies.git, carries > Global: and > Scope:, which Purlin does not read on an anchor, so the lines are read as nothing. Ask the owners of https://github.com/acme/policies.git to take them out, then run purlin:anchor sync security_baseline.
```

`references/formats/anchor_format.md` carries the sentence
`` A pinned copy is written as its source holds it; a `> Requires:`, `> Global:` or `> Scope:` line in it is warned of, naming the source's owners as the ones to take it out. ``
Nothing in `scripts/anchor/upstream.py` changes.

### C14. A pinned anchor's rule that does not apply, decision 101

In the owner's words: "this project can sign it but the signature just means it doesnt apply,
in this case." Only a rule of a pinned anchor is signed this way; a rule of the project's own
anchor that does not apply is deleted from it.

- **The command** (lane `signing`): `purlin:sign <anchor> RULE-N [RULE-N ...] --does-not-apply "<why>"`,
  that is `sign.py <anchor> RULE-N ... --does-not-apply "<why>"`. It writes an ordinary
  signature, over the same hashes as any other, carrying the reason, in one signed commit with
  the usual subject. It works at every gate. Its refusals, nothing written:
  - exit 2, `--does-not-apply needs the reason the rule does not apply to this project.`
  - exit 2, `--does-not-apply names a pinned anchor and the rules it carries.` (with `--all`,
    `--note`, `--release` or no rule named)
  - exit 1, `login RULE-3 is not a rule of a pinned anchor, so it cannot be signed as not applying. A rule of this project that does not apply is deleted: run purlin:spec login.`
- **The file** (lane `signing`, signature format 12): the optional field `does_not_apply`, the
  reason as one line, or null or absent for any other signature. Like `note` it is outside
  `signed_hash`: the signed commit is what holds it.
- **The cells** (lane `counting`): a rule that a counting signature carrying `does_not_apply`
  binds reads `does not apply` in every cell up to the gate, each met, each with the one reason
  `by <signer>: <why>`. Its bucket is the gate's own step, it carries no flag, its `left` is
  null, and the rule entry carries `does_not_apply: {"why": ..., "signer": ..., "at": ...}`
  (null otherwise). `states.DOES_NOT_APPLY = 'does not apply'`. Like every anchor signature it
  ends on any change to the project; the rule then reads its cells as usual, and while the last
  signature for it carried `does_not_apply` and none binds, its `left` is `to_confirm`, before
  any other kind it would take.
- **`Left to do`** (lane `counting`, `summary.py`): the kind `to_confirm`, after
  `to_test_by_hand` and before `to_sign`, reading `1 rule to confirm as not applying: purlin:sign`
  or `<n> rules to confirm as not applying: purlin:sign`. The dashboard's filter button is
  therefore `To confirm`.
- **The row** (lanes `counting`, `dashboard`): the `Tests` cell reads `<passed> of <rules>`, then
  ` · <k> does not apply` where k is not zero, before ` · <k> partial` and ` · <k> failing`:
  `7 of 8 · 1 does not apply`, a rule that does not apply counted among the `<passed>`.
- **The walk** (lanes `signing`, `skills`): `purlin:sign` with no argument stops at a rule to
  confirm with three answers, confirm, sign it as applying after all (it then waits as any rule
  does), or skip. Confirming writes a new signature with the earlier reason. `--all` does not
  confirm one. The stop reads
  `security_baseline RULE-4 was signed as not applying by jane@acme.com: the project stores no card data. Confirm it still does not apply?`
- **The dashboard** (lane `dashboard`): each cell's badge reads `DOES NOT APPLY` in the neutral
  teal; the rule's page, in its signed panel,
  `Does not apply to this project: <why>. Signed by <signer name> (<signer>) at <at>.`
- **The package** (lane `signing`, package format 5): each signature entry carries
  `does_not_apply`, string or null, and the rule's cells read `does not apply`.

### C15. The theme button, lane `dashboard` (the owner's request)

The button shows one glyph: `◐` in the dark theme and `◑` in the light, the glyph of the theme a
click leads to being the one shown. Its hover text and its accessible name stay
`Light theme` in the dark theme and `Dark theme` in the light. `CLAUDE.md` ("Two surfaces, one
system") and `design/readme.md` (its glyph sentence) name the glyphs `▶ ▼ ▲ → ◐ ◑`; no other
file lists them. Lane `dashboard` owns both files for this sentence alone.

## 3. Lines a person reads, chosen

In the shape of decisions 94 to 99. The owner reads these and says which to change.

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

## 4. The lanes

Every file that changes has exactly one owner. "Owns" is every file the lane may write.

| Lane | Owns |
|---|---|
| L1 `fingerprint` | `scripts/mcp/purlin/fingerprint.py`; `scripts/mcp/purlin/evidence.py`; `specs/mcp/evidence.md`; `dev/test_fingerprint.py`; `dev/test_evidence_reader.py`; `references/formats/evidence_format.md` |
| L2 `counting` | `scripts/mcp/purlin/{states,payload,status,summary,board,drift}.py`; `specs/mcp/{states,summary,drift}.md`; `dev/test_{states,summary,backing_tests,failing,drift}.py`; `dev/test_e2e_required_rules.sh`, moved to `dev/test_e2e_anchor_rules.sh`; `dev/run_tests.sh`; `skills/status/SKILL.md`; `specs/skills/skill_status.md`; `dev/test_skill_status.py` |
| L3 `dashboard` | `scripts/report/src/**`; `scripts/mcp/purlin/report_data.py`; `dev/build_report.py`; `dev/capture_doc_screenshots.py`; `specs/dashboard/purlin_report.md`; `dev/test_purlin_report.py`; `dev/test_purlin_report_board_layout.py`; `dev/test_report_refresh.py`; `dev/fixtures/report/*.json`; `docs/dashboard.md`; `CLAUDE.md` and `design/readme.md` (the glyph sentence alone, C15) |
| L4 `reader` | `scripts/mcp/purlin/specs.py`; `references/formats/spec_format.md`; `references/formats/anchor_format.md`; `specs/mcp/specs.md`; `specs/_anchors/schema_spec_format.md`, moved to `specs/mcp/schema_spec_format.md`; `specs/_anchors/security_no_dangerous_patterns.md`; `dev/test_specs_reader.py`; `dev/test_schema_spec_format.py`; `dev/test_security.py` |
| L5 `run` | `scripts/run/purlin_run.py`; `specs/run/run_script.md`; `dev/test_run_script.py`; `scripts/review/ai_audit.py`; `specs/review/ai_audit.md`; `dev/test_ai_audit.py`; `dev/test_ai_audit_tests_named.py`; `references/review_criteria.md` |
| L6 `signing` | `scripts/review/sign.py`; `scripts/mcp/purlin/signatures.py`; `specs/review/signatures.md`; `dev/test_signatures.py`; `dev/test_tag.py`; `references/formats/signature_format.md`; `scripts/export/package.py`; `specs/export/package.md`; `dev/test_export.py`; `references/formats/package_format.md` |
| L7 `upgrade` | `scripts/init/update.py`; `specs/init/update.md`; `dev/test_init_update.py`; `dev/fixtures/upgrade-0.9.5/**` |
| L8 `upstream` | `dev/test_e2e_anchor_authority.sh`; `dev/test_e2e_external_refs.sh` |
| L9 `skills` | `skills/{anchor,build,spec,spec-from-code,sign}/SKILL.md`; `specs/skills/{skill_anchor,skill_build,skill_spec,skill_spec_from_code,skill_sign}.md`; `dev/test_skill_{anchor,build,spec,spec_from_code,sign}.py`; `agents/purlin.md`; `specs/instructions/purlin_agent.md`; `dev/test_purlin_agent.py`; `references/spec_quality_guide.md` |
| L10 `words` | `references/{glossary,purlin_commands,hard_gates,drift_criteria}.md`; `RELEASE_NOTES.md`; `README.md`; `docs/{specs-and-anchors,spec-from-code,review-and-signing,working-together,how-purlin-works,index,team-workflow}.md`; `specs/instructions/purlin_docs.md`; `dev/test_purlin_docs.py` |

No lane: mutation (`scripts/run/mutation/`), host and remote, scaffold, settings, reports and
markers, evidence writer (`scripts/run/evidence.py`), the other skills. None has work: the run
stops asking the breaks for anchors (L5), and the evidence writer writes whatever fingerprint L1
computes. A failure the sweep finds there is integration's.

### L1 `fingerprint`

Builds C3. Evidence format 7: the `spec` row says the spec's own rule and proof lines; the `code`
row says a feature's `> Scope:` files and, for an anchor, every tracked file but `RECORDS`,
naming them; the sentence at line 35 stands.

`specs/mcp/evidence.md` (Highest R29 P77; next RULE-30, PROOF-78):
- RULE-2 reworded: the `spec` part covers the spec's own rule and proof lines. PROOF-3 rewritten
  to one case: a feature's fingerprint is unchanged when an anchor's rule is reworded.
- Deleted: RULE-3 with PROOF-4; RULE-23 with PROOF-5 and PROOF-35; their tests.
- New: RULE-30, an anchor's `code` part is every tracked file but Purlin's records (PROOF-78: an
  edit to a tracked file under no spec's scope changes an anchor's `code` part; PROOF-79: an
  untracked new file leaves it unchanged). RULE-31, writing Purlin's records leaves it unchanged
  (PROOF-80: a new evidence file under `.purlin/evidence/local/`; PROOF-81: `.purlin/tests.md`
  rewritten; PROOF-82: a signature file under `specs/_anchors/a.signatures/`; PROOF-83: the
  package under `.purlin/evidence/package/`). RULE-32, the `code` part is taken the same on
  Windows (PROOF-84, `@env(windows)`: in a checkout whose text files git writes out with CRLF,
  an anchor's `code` part equals the sha256 over each tracked file's path and the blob id the
  commit holds for it). RULE-33, a run with no feature named selects an anchor after any edit to
  a tracked file (PROOF-85).

Break on purpose: drop `':(exclude).purlin/evidence'` from `RECORDS`; PROOF-80's test fails.

### L2 `counting`

Builds C4, C5, C6 (its files), C7, and C8's `DASHBOARD_ROWS` edit. `rule_refs` is no longer
called: each spec's entry iterates its own `rule_order`. `drift.py` drops its two `label`
filters and nothing else. `dev/test_e2e_required_rules.sh` becomes
`dev/test_e2e_anchor_rules.sh` (`git mv`), checking in a real repository that a feature of 2
rules beside an anchor of 1 reads `2 of 2`, the anchor `1 of 1`, the summary `3 rules`, and the
status table's `Anchors` and `Specs` lines; `dev/run_tests.sh` line 49 names it
`E2E Anchor Rules`. The status skill takes C7's table and cuts as many lines as it adds.

`specs/mcp/states.md` (R96 P237; next RULE-97, PROOF-238):
- Reworded: RULE-26 (the summary counts each rule once, under the spec that owns it); RULE-49
  (every cell after the name reads the same in both, no exception); RULE-72 (the `Rules` cell is
  the spec's rule count); RULE-74 (`code_hash` is the code part of the spec it is listed under,
  the project for an anchor). PROOF-30, PROOF-49, PROOF-58, PROOF-111 rewritten to one case each
  under the new words.
- Deleted: RULE-76 with PROOF-148 and PROOF-149; PROOF-86, PROOF-180, PROOF-181; their tests.
  PROOF-179 stays (`2`, and no line holds `shared`).
- New: RULE-97, a feature's row counts its own rules only (PROOF-238: `login` of 11 passing
  rules beside an anchor of 8 reads `11 of 11`; PROOF-239: the anchor's row reads `8 of 8`);
  RULE-98, an anchor's met strong cell reads C5 (PROOF-240: mutation on and a stored score of 40
  under a minimum of 80, the anchor's rule reads `strong` with the one reason
  `the AI audit alone judges an anchor's tests`; PROOF-241: its `Strong` cell shows no `%`);
  RULE-99, the status table's anchors group (PROOF-242: the `Anchors` line, then the anchor's
  row, then `Specs`; PROOF-243: a project with no anchor has neither line); RULE-100, a rule a
  counting signature carrying `does_not_apply` binds reads C14's cells (PROOF-244: at the gate
  `signed`, a pinned anchor's rule with no test so signed reads `does not apply` in all three
  cells with `by <signer>: <why>`; PROOF-245: its row's Tests cell reads
  `1 of 1 · 1 does not apply`; PROOF-246: nothing is left to do for it); RULE-101, once that
  signature ends its `left` is `to_confirm` (PROOF-247: an edit to a tracked file, then
  `Left to do` reads `1 rule to confirm as not applying: purlin:sign`).
- `summary.md` gains RULE-15, the kind `to_confirm` stands after `to_test_by_hand` and before
  `to_sign` (PROOF-38, PROOF-39 for the plural).

`specs/mcp/summary.md` (R14 P37; next RULE-15, PROOF-38): PROOF-4 rewritten: an anchor's one
passing rule beside two features of one passing rule each reads `3 rules. 3 pass their tests.`

`specs/mcp/drift.md` (R27 P66; next RULE-28, PROOF-67): no rule changes unless a drift test
breaks on the label; then one proof per fix.

`specs/skills/skill_status.md` (R11 P35; next RULE-12, PROOF-36): a rule or proof that quotes
the old example or ` (+<k> shared)` is reworded to C7; none is written to say the old words are
gone (clean release).

Break on purpose: list an anchor's rules under every feature again in `_feature_entry`;
PROOF-238's test fails. Then read a `does_not_apply` signature as an ordinary one; PROOF-244's
test fails.

### L3 `dashboard`

Start: `git switch -c lane/d100-dashboard lane/anchors-section`, then rebase on `main`. From the
branch's three commits keep `specs/dashboard/purlin_report.md`, `scripts/report/src/board.js`,
`dev/test_purlin_report.py`, `dev/test_purlin_report_board_layout.py` and `docs/dashboard.md`;
drop its changes to `scripts/report/purlin-report.html`, `docs/images/dashboard-board.png` and
`dev/test_states.py` (generated files, and a file lane `counting` owns; C8). Then build C6 and C8:
the per-feature counts go from `board.js`, `app.js` (`ownRules`, `sharedBy` and the `label`
filters) and `filters.js`; the fixtures move to schema 11 with no `label`, no `requires`, no
`is_global`, and the team sample's `receipt` lists its own rule alone.

`specs/dashboard/purlin_report.md` (after the branch R63 P208; next RULE-64, PROOF-209):
- Reworded: RULE-35 and RULE-49 lose `15 (+6)` as an example; RULE-47 becomes: a spec's rows list
  its own rules and its `Rules` cell reads their count, with no hover. PROOF-71, PROOF-94,
  PROOF-108, PROOF-113, PROOF-142, PROOF-163 and PROOF-208 rewritten to one case each against
  the schema 11 fixtures (receipt reads `1`; the bands and the anchor's rules add up to the
  sample's total).
- Deleted: PROOF-72 (the `2 (+6)` walk) and its test.
- New: RULE-64, an anchor's `Strong` cell shows no strength (PROOF-209). RULE-65, a rule that
  does not apply (C14): every badge reads `DOES NOT APPLY` (PROOF-210), the signed panel reads
  its line (PROOF-211), the Tests cell names the count (PROOF-212), and `To confirm` is a filter
  button where the payload has that kind (PROOF-213). The regulated sample gains a pinned anchor
  with one rule so signed, and the team sample one rule to confirm.
- RULE-12 reworded for C15: the toggle is a button showing `◐` in the dark theme and `◑` in the
  light, its hover and accessible name `Light theme` or `Dark theme`, the theme it turns to.
  PROOF-182 rewritten (opens dark: the button shows `◐`, named `Light theme`), PROOF-183 (pressed
  once: `◑`, named `Dark theme`), PROOF-185 (pressed and reloaded: light, `◑`, `Dark theme`).
  `docs/dashboard.md` line 40 says the same.
- `docs/dashboard.md`: the `Rules` row of the columns table and the two `16 (+6)` examples say
  the count alone.

Break on purpose: render `(+<k>)` again from rules of other specs in `rulesCell`; PROOF-71's
test fails. Then show the same glyph in both themes; PROOF-183's test fails.

### L4 `reader`

Builds C1, C2, the spec format 21 and the anchor format 11 (section 3's words; the `Requires`,
`Global anchors` sections, the `> Global:` and `> Scope:` rows and the template's `> Scope:` go;
`Editing a pinned anchor` takes the anchor skill's sentence of section 3; C13's and C14's
sentences). Builds C13's `PINNED_UNREAD`. Moves this repository's two anchors:

- `specs/_anchors/security_no_dangerous_patterns.md`: its `> Scope:` and `> Global:` lines go;
  its description's last sentence reads `Its tests read every file under scripts/, where all of
  Purlin's executable code lives.` Rules, proofs and markers unchanged. `dev/test_security.py`'s
  comment naming its `> Scope:` says the same.
- `specs/_anchors/schema_spec_format.md` becomes a feature spec (section 8): `git mv` to
  `specs/mcp/schema_spec_format.md`; first line `# Feature: schema_spec_format`; `> Type:` goes;
  the description's last sentence goes; `> Scope:` gains `scripts/mcp/purlin/fingerprint.py`
  (RULE-19 is about the code there); name, rule and proof numbers and `> Highest-*` lines stay,
  so no marker changes. `specs/mcp/specs.md` loses `> Requires:`.

`specs/mcp/schema_spec_format.md` (R29 P70; next RULE-30, PROOF-71):
- Deleted: RULE-5 with PROOF-5, PROOF-20, PROOF-21; RULE-25 with PROOF-58, PROOF-59, PROOF-60;
  their tests.
- Reworded: RULE-19, `The code part of a feature spec's fingerprint ...`.
- New: RULE-30, `> Requires:` is warned of and not read (PROOF-71: C2's line for `login`;
  PROOF-72: `login` carrying `> Requires: api` beside an anchor `api` of one rule has exactly its
  own rules). RULE-31, `> Global:` on any spec is warned of and not read (PROOF-73: on an anchor;
  PROOF-74: on a feature). RULE-32, `> Scope:` on an anchor is warned of and not read (PROOF-75:
  the warning; PROOF-76: the anchor's scope reads `[]`). RULE-33, an anchor's scope is never
  warned of as finding no file (PROOF-77: an anchor scoped `src/gone.py` prints C2's line and
  no `which finds no file in git`). RULE-34, a pinned anchor whose copy carries any of the three
  fields gets C13's one line and none of C2's (PROOF-78: `> Scope:` alone, the singular line;
  PROOF-79: `> Global:` and `> Scope:`, the plural line; PROOF-80: no process is started to read
  its source).

`specs/mcp/specs.md` (R21 P43; next RULE-22, PROOF-44): deleted RULE-13 with PROOF-14 and
PROOF-37, RULE-19 with PROOF-36 and PROOF-38, and their tests; `dev/test_specs_reader.py` loses
the `rule_refs` tests. RULE-11 stands.

Break on purpose: stop adding `'Global'` to `unread_fields`; PROOF-73's test fails.

### L5 `run`

Builds C11 and C6 for `ai_audit.py`, and the review criteria paragraph of section 3 (under "What
the audit looks for"; "What test strength says" gains `No strength is measured for an anchor.`).

`specs/run/run_script.md` (R85 P258; next RULE-86, PROOF-259):
- Reworded: RULE-49 loses its clause about a rule a feature takes from an anchor. PROOF-176
  rewritten: an audit with no feature named, `feat` of one rule beside the anchor `shared` of
  one, makes 2 model calls, one naming `shared RULE-1`. PROOF-90 rewritten: after `src/solo.py`
  is edited, a `--test` with no feature named selects `shared` and `solo` and not `export`.
- New: RULE-86, the breaks are asked for no anchor (PROOF-259: with mutation on, an audit of an
  anchor and a feature hands the engine the feature's scope alone; PROOF-260: the anchor's
  evidence carries no `audit.mutation`).

`specs/review/ai_audit.md` (R29 P90; next RULE-30, PROOF-91): PROOF-49 rewritten: an anchor's
two rules are read as the anchor's, once each. New RULE-30, the prompt of an anchor's rule ends
on C11's line (PROOF-91) and carries no `Test strength:` line (PROOF-92).

Break on purpose: stop leaving anchors out of `measured`; PROOF-259's test fails, with the
engine a stub in the test, never a real one.

### L6 `signing`

Builds C10, signature format 12 (line 1 and line 5, the `applies_to` row, the anchor paragraph at
line 51 in section 3's hard-gates words) and package format 5.

`specs/review/signatures.md` (R89 P178; next RULE-90, PROOF-179):
- Reworded: RULE-9 says format 12. RULE-59: an anchor's rule is signed once, over every file of
  the project but Purlin's records. PROOF-113 rewritten: `secure RULE-1` signed by name adds 1
  commit and 1 file, applying to `secure`. PROOF-131 rewritten: `--all` lists `  secure RULE-1`
  once.
- New: RULE-90, an anchor's signature ends on an edit to a tracked file under no spec's scope
  (PROOF-179) and stands across a signature commit and an evidence commit (PROOF-180). RULE-91,
  the walk visits features' rules before anchors' (PROOF-181). RULE-92,
  `--does-not-apply "<why>"` writes a signature carrying `does_not_apply` (PROOF-182) in one
  signed commit (PROOF-183). RULE-93, it signs only a pinned anchor's rule (PROOF-184: a local
  anchor's rule is refused with C14's exit-1 line and nothing is written; PROOF-185: a feature's
  rule likewise). RULE-94, its two usage refusals (PROOF-186: no reason; PROOF-187: with
  `--all`). RULE-95, the walk stops at a rule to confirm and confirming writes the earlier reason
  again (PROOF-188); `--all` leaves it (PROOF-189).

`specs/export/package.md` (R25 P55; next RULE-26, PROOF-56): new RULE-26, a feature entry holds
exactly `name`, `spec`, `scope`, `anchor`, `rules` (PROOF-56), an anchor's `scope` `[]`
(PROOF-57); RULE-27, a signature entry carries `does_not_apply`, the reason or null (PROOF-58),
and a rule that does not apply reads `does not apply` in its cells (PROOF-59).

Break on purpose: take `code_hash` from the anchor's (empty) scope; PROOF-179's test fails.
Then let `--does-not-apply` sign a local anchor's rule; PROOF-184's test fails.

### L7 `upgrade`

Builds C12. `scope_advice`'s docstring says anchors are exempt because an
anchor names no files. The fixture stays as 0.9.5 wrote it. Its `proof_common` anchor is named by
no spec there, so the test of PROOF-155 adds `proof_common` to the `> Requires:` line of
`specs/mcp/sync_status.md` in its own copy of the fixture before it runs the upgrade.

`specs/init/update.md` (R45 P152; next RULE-46, PROOF-153): RULE-46, the migration (PROOF-153:
after `--yes` no spec of the sample holds `> Requires:` or `> Global:` and no anchor `> Scope:`;
PROOF-154: the line `removed from specs/_anchors/proof_common.md: > Scope:`; PROOF-155: the
per-anchor line for `proof_common`; PROOF-156: a backup beside each file
it rewrote). PROOF-134's pending list gains the migration's line where it quotes the list whole.

Break on purpose: skip the `> Global:` line in the migration; PROOF-153's test fails.

### L8 `upstream`

`add` and `sync` copy the source unchanged (decision 101), so `scripts/anchor/upstream.py` and
its spec do not change. `dev/test_e2e_anchor_authority.sh` stops writing a local anchor that
`> Requires:` the pinned one: the project's own rule stands in a local anchor of its own, and a
pinned source carrying `> Scope:` prints C13's line in the status. `dev/test_e2e_external_refs.sh`
stops writing `> Requires:`. These are untied suites; no spec changes.

Break on purpose: none in code; the lane runs both suites against local bare repositories only.

### L9 `skills`

Takes section 3's lines into the anchor, build, spec, spec-from-code and sign skills, the agent's
`Renaming a feature`, and the quality guide (a paragraph `A rule for the whole project`: when a
rule belongs in an anchor, when in each feature's spec, and that a pinned rule that does not
apply here is signed as not applying, per C14). The sign skill gains the command of C14 and the
walk's stop to confirm, cutting as many lines as it adds (ceiling 185); the anchor skill's
`Changing a pinned rule` gains the anchor format's C14 sentence. Every `> Requires:` and `> Global:` goes from the
five skills, the agent and the guide, including the spec skill's shape example.

Next free ids: `skill_anchor` RULE-15 PROOF-36; `skill_build` RULE-18 PROOF-47; `skill_spec`
RULE-24 PROOF-54; `skill_spec_from_code` RULE-52 PROOF-166; `skill_sign` RULE-24 PROOF-52;
`purlin_agent` RULE-17 PROOF-48.
- `skill_anchor`: RULE-12 reworded to section 3's sentence, PROOF-31 rewritten; new RULE-15, the
  skill says an anchor carries no `> Scope:` and a rule not checkable across the project goes in
  each feature's spec (PROOF-36, PROOF-37).
- `skill_build`: new RULE-18, `Loading the rules` says every anchor's rules hold across the
  project and names no `> Requires:` (PROOF-47).
- `skill_spec`: new RULE-24, the skill says to take out a warned `> Requires:`, `> Global:` or an
  anchor's `> Scope:` (PROOF-54).
- `skill_spec_from_code`: RULE-37 reworded to section 3's step 4; PROOF-152 rewritten.
- `purlin_agent`: RULE-7 and PROOF-7 lose `> Requires:` and say four places.
- `skill_sign`: new RULE-24, the skill names `--does-not-apply "<why>"` for a pinned anchor's
  rule alone (PROOF-52) and the walk's stop to confirm (PROOF-53).
- `skill_anchor`: new RULE-16, `Changing a pinned rule` says a pinned rule that does not apply is
  signed as not applying (PROOF-38).

Break on purpose: put `> Requires: <name>` back in the anchor skill's `create`; PROOF-36's test
fails.

### L10 `words`

Section 3's glossary, hard-gates and release-notes lines. `references/purlin_commands.md` line
112: `purlin:sign`'s row loses `one file per feature an anchor's rule applies to`.
`references/drift_criteria.md`: no anchor has a scope in the `unscoped` view's words, if it names
one. `docs/specs-and-anchors.md`: the metadata table loses `> Requires:`; the anchors section
(lines 194 to 205) is rewritten in the anchor format's words of section 3; line 275 in the anchor
skill's words; C13's and C14's sentences, with the command. `references/purlin_commands.md`
gains C14's usage line under `purlin:sign`, and the glossary and `hard_gates.md` C14's lines. `docs/spec-from-code.md` step 4, `docs/review-and-signing.md`
lines 139 and 232, `docs/working-together.md` "A rule from a pinned anchor", and every other
line of the owned pages a grep for `Requires`, `Global`, `shared`, `(+` or `applies to` finds
false. `README.md` only where a line is false. `specs/instructions/purlin_docs.md` (R12 P17)
changes only where a proof quotes a changed line.

Break on purpose: none in code; the lane runs `dev/test_purlin_docs.py` and the greps of section
6, step 6, over its own files.

## 5. Next free numbers

Read on `main` at `194d51d53`. A lane recomputes on rebase and never reuses one.

| Spec | Highest-Rule | Highest-Proof | Next |
|---|---|---|---|
| `specs/mcp/evidence.md` | 29 | 77 | RULE-30, PROOF-78 |
| `specs/mcp/states.md` | 96 | 237 | RULE-97, PROOF-238 |
| `specs/mcp/summary.md` | 14 | 37 | RULE-15, PROOF-38 |
| `specs/mcp/drift.md` | 27 | 66 | RULE-28, PROOF-67 |
| `specs/skills/skill_status.md` | 11 | 35 | RULE-12, PROOF-36 |
| `specs/dashboard/purlin_report.md` | 63 (branch) | 208 (branch) | RULE-64, PROOF-209 |
| `specs/mcp/schema_spec_format.md` | 29 | 70 | RULE-30, PROOF-71 |
| `specs/mcp/specs.md` | 21 | 43 | RULE-22, PROOF-44 |
| `specs/run/run_script.md` | 85 | 258 | RULE-86, PROOF-259 |
| `specs/review/ai_audit.md` | 29 | 90 | RULE-30, PROOF-91 |
| `specs/review/signatures.md` | 89 | 178 | RULE-90, PROOF-179 |
| `specs/export/package.md` | 25 | 55 | RULE-26, PROOF-56 |
| `specs/init/update.md` | 45 | 152 | RULE-46, PROOF-153 |
| `specs/skills/skill_anchor.md` | 14 | 35 | RULE-15, PROOF-36 |
| `specs/skills/skill_build.md` | 17 | 46 | RULE-18, PROOF-47 |
| `specs/skills/skill_spec.md` | 23 | 53 | RULE-24, PROOF-54 |
| `specs/skills/skill_spec_from_code.md` | 51 | 165 | RULE-52, PROOF-166 |
| `specs/skills/skill_sign.md` | 23 | 51 | RULE-24, PROOF-52 |
| `specs/instructions/purlin_agent.md` | 16 | 47 | RULE-17, PROOF-48 |
| `specs/instructions/purlin_docs.md` | 12 | 17 | RULE-13, PROOF-18 |

## 6. Merge order and integration

### Merge order

`fingerprint`, `counting`, `dashboard`, `reader`, `run`, `signing`, `upgrade`, `upstream`,
`skills`, `words`. Each by fast-forward, the lane rebased on `main` and its files and `--fast`
rerun first.

Why: `counting` calls `fingerprint.code_part`, so `fingerprint` goes first. `dashboard` reads
rules with no `label`, so it follows `counting` at once. `reader` deletes `rule_refs`, which
`fingerprint` and `counting` stop calling, so it follows both. The rest read the payload of C4.
`words` is last, since it describes what the others built.

Expected red between merges, and only these: from the `counting` merge until `signing` merges,
the tests of `dev/test_signatures.py` and `dev/test_export.py` that sign an anchor's rule in each
feature; until `run` merges, PROOF-176's and PROOF-90's tests in `dev/test_run_script.py`; until
`upstream` and `upgrade` merge, the lines of their tests that count required rules or read the
status of a spec carrying `> Requires:`. Each lane after `counting` finishes its work rebased on
the merged `fingerprint`, `counting` and `dashboard`.

### The integration agent's job (alone, after every lane merged)

1. Merge in the order above; resolve failures lanes reported in files they do not own, to the
   contracts.
2. The one frozen-file change, as a commit of its own on `main` once `run` has merged (it cannot
   land first: `dev/test_run_script.py` still passes `requires` until then): delete the
   `requires` parameter of `_spec` in `dev/run_project.py`, its docstring clause and the line it
   writes. Nothing else in a frozen file changes.
3. `export PATH=/opt/homebrew/opt/dotnet@8/bin:$PWD/.venv/bin:$PATH`; `bash dev/run_tests.sh`:
   0 failed. Never edit a number to make it pass.
4. `python3 dev/build_report.py`; commit `scripts/report/purlin-report.html` once;
   `python3 dev/capture_doc_screenshots.py` and commit the two screenshots once.
5. Look at the dashboard with playwright from the `.venv`, headless, dark theme and light, at
   1500, 1280, 1024, 768 and 390 pixels: the `Anchors` section above `Specs` with
   `security_no_dangerous_patterns` alone in it, no `(+` anywhere, no value broken inside itself,
   neutral text at least 7 to 1.
6. Greps over `scripts/`, `skills/`, `agents/`, `references/`, `docs/`, `specs/`, `templates/`,
   `README.md` and the test files under `dev/`, each empty outside `RELEASE_NOTES.md`,
   `dev/fixtures/upgrade-0.9.5/`, `scripts/init/update.py`, `dev/test_init_update.py`, the C2
   constants in `scripts/mcp/purlin/specs.py` and the rules, proofs and tests of C2's warnings:
   `Requires`, `Global: true`, `is_global`, `rule_refs`, `global_anchors`, `counted_specs`,
   `shared_counts`, `listings_to_sign`, `shared)`, `(anchor)`, `required rule`,
   `global anchor`, `signed once in each`; under `scripts/` alone `consumers` and
   `get('label')`; under `scripts/report/src/`, `docs/`, `skills/` and `specs/` alone `(+`.
   The C13 constant and its rule, proofs and tests are allowed the three field names too.
7. `python3 scripts/run/purlin_run.py --test --all`: `Markers: <n> tied to a test, 0 not tied.`,
   no rule `failed`, `partial` or `no test`, and none of C2's warnings (this repository carries
   no `> Requires:`, no `> Global:` and no anchor `> Scope:`). Then the same with `--commit`.
   The feature `schema_spec_format` is listed under `mcp`; `security_no_dangerous_patterns`
   stands under `Anchors` in the status table.
8. Write `dev/plans/d100-interfaces.md`: what was built where it differs from the contracts,
   every word a lane chose that section 3 does not give, the ids, the test counts, and section 3
   copied under "Words chosen for the owner to read".
9. The anchors slide: read the slide `anchors` from the deck
   (https://claude.ai/artifact/Rifxf2KXfH4CTzfQ9pZ9is) first and keep any words the owner changed
   there; then take section 3's slide lines into `dev/plans/deck/build_deck.py` and publish. The
   owner reads it.
10. The remote run on Windows, which the handoff says follows the build: `purlin:test --remote`
    once, pushing only its temporary run branch; nothing else is pushed and no tag is written.
    It proves evidence PROOF-84 there.
11. Update `dev/plans/handoff.md` ("Where the tree is", "What is left" item 1 closed, the words of
    section 3 into "Words for the owner to read") and `dev/plans/next-agent-prompt.md`.

## 7. The owner's answers (decision 101)

Given on 2026-09-30 to the three questions this plan raised, with one further request.

- **A pulled anchor whose source carries `> Requires:`, `> Global:` or `> Scope:` is copied as it
  is, and warned of.** The file is copied unchanged, and every status and test run warns, the
  anchor's name first and the fix last, naming the source's owners, until the other team changes
  its file (C13).
- **The upgrade keeps each anchor, takes the naming lines out, and prints one line per anchor**
  naming the specs that named it and the command that moves a rule into them (C12).
- **A pinned anchor's rule that does not apply to this project is signed as not applying.** In
  the owner's words: "this project can sign it but the signature just means it doesnt apply, in
  this case". A person signs it with `--does-not-apply "<why>"`; it then counts as met, reads
  `does not apply` with who said so, and the package says so. Only a pinned anchor's rule is
  signed this way; the project's own anchor rule that does not apply is deleted. Like every
  anchor signature it ends on any change to the project, and the person confirms it again (C14).
- **The theme button is a glyph**, `◐` in one theme and `◑` in the other, the words staying as
  its hover and accessible name; `CLAUDE.md` and `design/readme.md` allow the two glyphs (C15).
- The six calls of section 9 stand.

## 8. This repository's two anchors

`security_no_dangerous_patterns` stays an anchor: its rules speak of every executable file under
`scripts/`, and its tests read all of them, so it is proven across the project as decision 100
asks. Its `> Scope:` and `> Global:` lines go (L4).

`schema_spec_format` becomes an ordinary feature spec, `specs/mcp/schema_spec_format.md` (L4).
Its rules are about one piece of code, the spec parser, and the format page beside it; its tests
read fixture specs through that parser, not the project; one feature named it; and nothing
outside this repository pins it (no `> Source:` anywhere names it). Under "Global or not an
anchor" it is not an anchor. No concrete reason to keep it one was found: a check that every spec
of this project parses cleanly would be project-wide, but decision 97 dropped exactly that check
(Q54) because the spec warnings already print for every spec on every run. Keeping its name, rule
and proof numbers and `> Highest-*` lines leaves every marker, its test file and its evidence file
name as they are; its evidence is taken again at integration, since the spec's path is in its
fingerprint.

## 9. Calls this plan makes

Not questions: each follows from decision 100, and the owner may reverse any.

- The records no anchor's code part reads are `.purlin/evidence/` whole (run results of both
  sources, the package, and the README setup writes there), `.purlin/tests.md`, and every
  `*.signatures/` folder under `specs/`. `.purlin/config.json` is the project's settings and
  counts.
- An untracked file does not select an anchor unless it sits beside one of the anchor's marker
  files: the project is the files git tracks.
- The signing walk visits anchors last, so that "signed last" is also the order a person is asked.
- The audit is told an anchor's tests must check the whole project, and its criteria say a test
  of a sample or of one feature's files is weak there.
- `> Global:` on a feature spec is warned of like `> Global:` on an anchor.
- The terminal groups anchors under `Anchors` above `Specs`, as the dashboard does, since
  `(anchor)` goes from the dashboard and the table is the board as text.
