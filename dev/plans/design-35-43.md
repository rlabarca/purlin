# Technical design for decisions 35 to 37 and 39 to 43

This design assumes decisions 38 and 41 have landed. Right now the `d38` and `d41` worktrees are at `a73086aa3` with only uncommitted edits. Every claim about today's code cites `file:line` at `a73086aa3`. Where I made a choice the decisions do not settle, it is marked **(Qn)** and asked in section 10. Where I think the decisions already imply the answer, it is marked **(implied by n)**.

## 0. Gaps in today's code that the design has to close

- **G1. Evidence from your own run never goes out of date.** When no record answers, `states.py:299-304` reads the local run as `passed` with `current: True` and never checks it against the code. `scripts/mcp/purlin/results.py:261-293` also prefers the uncommitted runtime proofs. Decision 39 closes this.
- **G2. Nothing in the workflow calls the model.** `purlin_run.py:1070` calls `build_brief(...)` without `ai=True`, so `brief.py:171-172` writes `not available`. `states.py:637-638` treats that as "no question was asked", and `states.py:574-579` reads `strong` when no engine measured anything. Today a rule can reach `strong` with no judgment at all.
- **G3. Glob scopes hash to a constant.** `specs.py:223-224` passes a `> Scope:` glob through as a literal path, and `_blob_id` returns `''` for it (`specs.py:251-253`). `specs/_anchors/security_no_dangerous_patterns.md` scopes `scripts/**/*.py` and similar, so its code fingerprint never changes.
- **G4. Freshness covers code only.** A record carries only `scope_tree` (`purlin_run.py:711-712`), and `states.py:511-514` compares only that. A spec edit or a test edit leaves an old pass counted as current.
- **G5. Azure DevOps.**
  - Provenance rests on the committer's name (`scripts/mcp/purlin/records.py:76-78, 280-281`).
  - The remote run prints a URL and returns `0` without waiting (`remote.py:142-153`).
  - Pushes send `changeType: add` only (`scripts/run/records.py:452-456`). That fails on a file that already exists, which one file per feature needs.
  - The Azure gate step has no `SYSTEM_ACCESSTOKEN` (`templates/purlin.azure-pipelines.yml:105-106`), so it cannot call REST.
- **G6. A rule whose proofs are all `@manual` meets `passed` with no evidence at all** (`states.py:245-247`).
- **G7. The model prompt goes on the command line** (`brief.py:322-324`). Windows caps a command line at 32,767 characters, and `references/review_criteria.md` alone is 9,018 bytes.
- **G8. CI commits each file whole from the job's own disk** (`scripts/run/records.py:405, 416-421`). Two matrix jobs writing one per-feature file would overwrite each other.
- **G9. Under `trust: remote` a `@manual`-only rule can never be signed.** `sign.py:327-343` asks for a `ci` source on the passed cell, and such a rule has none.
- **G10. The `digest` config key is read but not listed.** `scripts/hooks/refresh_digest.py:198` reads it; `templates/config.json` and the config table in `references/drift_criteria.md` omit it. This is outside the seven decisions.
- **G11. `purlin:test --all` currently means "every tier"** (`skills/test/SKILL.md:21`). Decision 38 frees the flag and decision 39 gives it a new meaning.

## 1. The model in one page

**Level.** A rule's effective level is `L = min(mark, gate)`, where `mark` is its `[level: …]` tag or, when it has none, the gate. The order is `passed < strong < signed`. The payload carries `level` (the effective one) and `level_marked` (the tag, or null). Cells exist up to the gate, as today.

**passed cell** (every gate). Only platform sections whose fingerprint matches the tree decide `passed`, `failed` or `partial`.

| Word | Produced when | Met |
|---|---|---|
| `passed` | Every tested proof has `pass` in a current section. Each `@env` proof passed on its own OS, and every OS the rule's current sections cover agrees. Every `@manual` proof has a current hand check **(Q1)** | yes |
| `partial` | Current sections disagree across operating systems. Reasons: `passed on linux`, `windows: failed` | no |
| `failed` | A current section records `fail` for a proof of the rule | no |
| `no test` | No proof line names the rule (reason `no proof written`), or a proof has no marker and no evidence entry (reason `PROOF-N has no test`) | no |
| `not run` | A test exists but no section covers a platform the rule needs. Reason `windows: no run yet` | no |
| `code changed` | The newest section is not current. Reason `code changed since a1b2c3d`, `spec changed since …` or `tests changed since …` **(Q8)** | no |
| `manual test` | A `@manual` proof has no current hand check **(Q1)**. Reason `hand check waiting` | no |

**strong cell** (gates `strong` and `signed`)

| Word | Produced when | Met |
|---|---|---|
| `strong` | `passed` is met, the evidence holds an audit entry for the current (rule, proof, test) hashes with verdict `strong` and no findings, and, when mutation is on and a score exists, the score is at least `min_strength`. Reason `no mutation score measured` when mutation is off or no engine exists (implied by 35). A `@manual`-only rule reads `strong` from its hand check, with reason `hand check by <email>` | yes |
| `weak` | `not passed`; or the verdict is weak (each finding sentence is a reason); or verdict `undecided`, with reason `the AI audit could not decide: <its sentence>` (implied by 35); or `strength 64% under 80%` | no |
| `not audited` | `passed` is met and there is no entry for the current hashes. Reason `no audit has read this rule's text, proof and test`, or `the AI audit could not run: <why>` **(Q3)** | no |

`unsettled`, `held` and `manual test` leave this cell. Under Q1 option B, `manual test` stays here.

**signed cell** (gate `signed`)

| Word | Produced when | Met |
|---|---|---|
| `signed` | A signature whose R, P, T and A hashes match, added in a commit that is signed and verifies | yes |
| `unsigned` | No current signature. Reason `the signing commit is not signed` where the only current one sits in an unsigned commit | no |
| `stale` | A signature exists and its hashes differ. The reason names what moved: `rule text`, `proof text`, `test` or `audit findings changed after the signature` | no |

`held` and the `required` field are removed.

**Meets the gate.** A rule meets the gate when its passed cell is met, and its strong cell is met if `L ≥ strong`, and its signed cell is met if `L = signed`. `blocked_by` is the first of `passed`, `strong` or `signed` that fails, else null. `spec` is gone as a value.

| Gate \ level | `passed` | `strong` | `signed` |
|---|---|---|---|
| `passed` | passed cell | read as `passed` | read as `passed` |
| `strong` | passed cell; the strong cell is shown and does not block | passed + strong | read as `strong` |
| `signed` | passed cell; strong and signed are shown and do not block | passed + strong | passed + strong + signed |

**The queue.** It holds two kinds of row:

- A **hand check**: the passed cell reads `manual test`. At every gate under Q1-A.
- A **signature**: `L = signed`, the passed and strong cells are met, and the signed cell is not.

A rule that needs both gets one row, `hand check`. The hand check is a signature with a note, and in a signed commit it also meets the signed cell.

Each row has these fields: `feature`, `owner`, `rule`, `text`, `level`, `need` (`hand check` or `signature`), `word`, `reasons` and `command`. The command is `purlin:sign <f> <RULE-N> --note "<what you saw>"` for a hand check and `purlin:sign <f> <RULE-N>` for a signature. Rows are ordered by feature, then rule number.

**The tag.** `signed/<version>` is written when three things hold: every rule meets the gate, no feature is incomplete **(Q4)**, and every feature with tested proofs has a current section on each platform its rules need. The third follows from the first, because `passed` requires current sections. The refusal names each feature: `No tag: login has evidence older than its code (code changed since a1b2c3d).`

**Cases walked**

| Case | Result |
|---|---|
| Rule with no proof | passed `no test` (`no proof written`); strong `weak` (`not passed`); bucket `untested`; next step `purlin:spec` |
| Proof with no test | passed `no test` (`PROOF-2 has no test`); next step `purlin:build`. With a marker but no run: `not run` |
| `@manual`-only rule, gate `passed` | Q1-A: passed `manual test` until `purlin:sign … --note`, then `passed` (`hand check by x`); a queue row at `passed`. Q1-B: `passed` with no evidence, as today |
| `@manual`-only rule, gate `strong` | As above, and the strong cell reads `strong` (`hand check by x`) once the hand check is current. Below `signed`, any committed hand check counts |
| `@manual`-only rule, gate `signed`, `L=signed` | One row, `hand check`. A hand check in a signed commit meets passed, strong and signed together |
| `[level: passed]` under gate `signed` | Only the passed cell blocks. The strong and signed cells are shown. Not in the queue. `purlin:sign` refuses: `sign: login RULE-3 is marked [level: passed]; it asks for no signature.` The audit reads it **(Q2)** |
| `[level: signed]` under gate `strong` | `level: strong`, `level_marked: signed`. Needs tests and audit, no signature. Status prints `1 rule is marked above the gate and is read as strong.` |
| Tests pass, no audit yet | Gate `passed`: meets. Gate `strong`/`signed` with `L≥strong`: strong `not audited`; next step `purlin:audit` |
| Mutation off, model found nothing | strong `strong` (`no mutation score measured`) |
| Mutation on, score under the minimum | `weak` (`strength 64% under 80%`), plus any findings; build work |
| No `claude` on PATH | `not audited` (`the AI audit could not run: claude is not on PATH`). Nothing is recorded, so the next audit retries. `purlin:audit` exits 1 at `strong` and above **(Q3)** |
| Model could not decide | Recorded as `undecided`; strong `weak` (`the AI audit could not decide: …`). It stays skipped until the text, proof or test changes, or `--all` |
| Covered code changed after the evidence | passed `code changed` (not met); the strong cell reads `weak` (`not passed`). The signature is unaffected (R, P, T and A exclude code). The next `purlin:test` selects the feature, and a pass restores everything with no new audit |
| Signature exists; a fresh audit (`--all`) words its findings differently | A changes, so signed `stale` (`audit findings changed after the signature`) and a queue row. The audit prints `2 signatures went stale: their audit findings changed.` (implied by 31 and 35) |
| `@env(windows)` proof on a Mac, no runner | passed `not run` (`windows: no run yet`). `purlin:test` prints the foreign-proof line and `Run: purlin:init`. Blocks the gate |
| `@env(windows)` proof on a Mac, with a runner | `purlin:test --remote` brings back `ci/<f>.json` with a `windows` section. Both pass: `passed`. They disagree: `partial` |
| `trust: remote`, local evidence only | Cells are unaffected (decision 32). At `signed`, `purlin:sign` refuses: `sign: login RULE-3 has no ci test run for this code; run purlin:test --remote first.` The row stays in the queue and there is no tag. The trust check applies only to rules with tested proofs (closes G9) |

## 2. The evidence file

**Path.** `.purlin/evidence/<source>/<feature>.json`. `<source>` is `local` or `ci`, and the folder is the source. There is one file per feature per source, anchors included. Operating systems are held as sections inside that one file (decision 40 names one path per feature). Whether that is right is **Q9**, because concurrent commits from two operating systems can conflict in git.

```json
{
  "schema": "purlin-evidence/1",
  "feature": "login",
  "source": "local",
  "spec": "specs/auth/login.md",
  "platforms": {
    "macos": {
      "commit": "4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7",
      "dirty": false,
      "at": "2026-09-27T12:00:00Z",
      "runner": "jane",
      "fingerprint": {"spec": "<sha256>", "code": "<sha256>", "tests": "<sha256>"},
      "rules": {"RULE-1": "passed", "RULE-2": "no test"},
      "proofs": [
        {"id": "PROOF-1", "rule": "RULE-1", "result": "pass", "env": null,
         "manual": false, "test": "tests/test_login.py::test_rejects_a_wrong_password"}
      ]
    }
  },
  "audit": {
    "mutation": {"engine": "mutmut", "score": 71, "at": "…", "commit": "…"},
    "rules": {
      "RULE-1": {"rule_hash": "…", "proof_hash": "…", "test_hash": "…",
                 "verdict": "strong", "findings": [], "at": "…", "commit": "…"}
    }
  }
}
```

**Fields**

| Field | Type | Holds |
|---|---|---|
| `schema` | string | `purlin-evidence/1` |
| `feature`, `spec` | string | The feature and its spec path |
| `source` | string | `local` or `ci`. It must equal the folder, or the file is ignored with one warning |
| `platforms` | object | Keyed by `windows`, `macos` or `linux` |
| `platforms.*.commit` | string | Full sha of HEAD when the run started |
| `platforms.*.dirty` | bool | The tree had uncommitted changes. For display only; the fingerprint is what counts |
| `platforms.*.at` | string | ISO 8601 UTC with `Z` |
| `platforms.*.runner` | string | Email slug, or `ci` |
| `platforms.*.fingerprint` | object of three sha256 hex strings | See below |
| `platforms.*.rules` | object | `RULE-N` mapped to `passed`, `failed`, `no test` or `not run` |
| `platforms.*.proofs[]` | array | One entry per (proof, test) pair: `id`, `rule`, `result` (`pass`, `fail`, `missing` or `not run`), `env` (string or null), `manual` (bool), `test` (`file::name`, or `""` when nothing observed the proof) |
| `audit` | object | Present only once an audit has run |
| `audit.mutation` | object or null | `engine` (string), `score` (int or null), `at`, `commit`. Null when mutation is off |
| `audit.rules.*` | object | `rule_hash`, `proof_hash`, `test_hash` (the key the audit was taken over), `verdict` (`strong`, `weak` or `undecided`), `findings` (array of sentences), `at`, `commit` |

**Merge rules**

- A test run reads the file from disk and replaces `platforms[<this os>]` whole. Every other section and `audit` stay untouched.
- An audit run first does the same test-run write. It then replaces `audit.rules[R]` for each rule it audited and leaves skipped rules alone. It replaces `audit.mutation` when breaks ran.
- An audit entry taken at an earlier commit stays valid while its three hashes match the current rule. `commit` and `at` are for display only.
- Entries for rules no longer in the spec are dropped on every write.
- Any run deletes evidence files under `local/` and `ci/` whose feature has no spec.

**CI writes (G8).** The CI arm writes only its own OS section. In the API commit's retry loop it re-reads the file at the new parent, merges its own section into it, and sends the result:

- GitHub: `GET /repos/{r}/contents/{path}?ref={parent}`.
- Azure DevOps: `GET …/items?path=…&versionDescriptor.version=<branch>`, then `changeType: edit` if the file exists, else `add`.

**Retention.** The newest section per OS per source, and the newest audit per rule. The history is `git log` of the file. Nothing is pruned.

**Folders.** `local/` is written by `purlin:test` and `purlin:audit` and committed under the person's own identity. `ci/` is written only by the `--ci` arm on a run branch through the git host's API, and the tag run checks its provenance (section 7).

**Fingerprint** (new `scripts/mcp/purlin/fingerprint.py`). Each part hashes working-tree content with `git hash-object`, so uncommitted edits count:

- `spec`: sha256 over the normalised rule and proof lines of the feature, and of every spec in its `rule_refs` (required specs transitively, plus global anchors). A rule line is `<spec> <RULE-N> <text> <level tag>`. A proof line is `<spec> <PROOF-N> <rules> <text> <@manual> <@env>`. Editing `> Description:` changes nothing.
- `code`: the `> Scope:` entries expanded. A file maps to itself. A directory maps to `git ls-files -- <dir>`. A glob maps to `git ls-files -- ':(glob)<pattern>'`, which closes G3. Each entry contributes `<path> <blob>`.
- `tests`: every file carrying a marker for the feature, using the marker patterns now at `purlin_run.py:245-258` (they move to `fingerprint.py`). Each contributes `<path> <blob>`.
- Untracked files are excluded from the stored fingerprint, as `specs.py:196-199` argues. They still select a feature (section 3) **(Q7)**.

**What `purlin:sign` hashes**

- R: the rule text.
- P: the proof texts.
- T: sha256 over sorted `<file> <name> <blob>` for the tests that current sections list for the rule's proofs, with the blob read from the working tree.
- A: sha256 over `verdict`, `score` (or `n/a`) and the sorted `findings` of the audit entry for the current hashes, or of the empty string when there is none.
- Not the fingerprint, so a code change still stales nothing, as `hard_gates.md:236` says.
- The level is recorded in the signature, not bound **(Q6)**.

**Commit.** One subject for test runs, audits and CI: `purlin: evidence at <sha7>`. The lines are `Evidence committed.` and `Evidence unchanged.`

**`.purlin/tests.md`** is re-rendered from every file under `.purlin/evidence/` on each run. One row per feature, from its newest section in either source. The columns stay as today (`scripts/run/results.py:57-58`): `Feature | Rules | Passed | Failing | No test | Last run`, where Last run is `<sha7> · <at> · <os> · <source>`.

**Formats**

- New: `references/formats/evidence_format.md`, `> Format-Version: 1`.
- Deleted: `record_format.md` (version 5) and `tests_format.md` (version 2).
- `signature_format.md` bumps in each piece that changes it (P3, P4, P5). It loses `bar`, `design_hash`, `brief`, `record` and the whole Holds section, and gains `level` (recorded only) and `evidence` (path).
- `spec_format.md` bumps for `[level: …]` (P3) and for `> Scope:` becoming required (P7).
- The `CLAUDE.md` format table follows.

**Payload, schema 8 to 9.** A diff against `dev/fixtures/report/*.json`. Removals marked d38 belong to decision 38.

```
- "schema_version": 8                    + "schema_version": 9
gate:
- "sign_at"
  "mutation_engine": "none"|"auto"|<engine>;  "min_strength": null unless mutation is on
summary / rollup:
- "held", "unsettled", "signable"          (rollup also - "latest_record")
+ "queue", "hand_checks", "incomplete", "above_gate"
features[]:
- "latest_record"
+ "evidence": {"local": {"path", "platforms": {os: {"commit","at","current"}}}|null, "ci": …}
+ "incomplete": bool, "incomplete_reason": null|"no > Scope: line"|"> Scope: names nothing that exists"
+ "current": bool
rules[]:
- "bar", "bar_from", "spec", "cleared", "signable"
- "origin", "criterion", "design_hash"     (d38)
+ "level", "level_marked"
+ "audit": {"verdict","findings","strength","at","commit","path"}|null   (present at every gate)
  "blocked_by": "passed"|"strong"|"signed"|null
  flags: - "held", "unsettled"   + "no_proof"
  cells.strong: - "brief", "settled", "observations"   + "findings", "evidence"
  cells.signed: - "required"; the word "held" is gone
- "review_list", "sign_list"
+ "queue": [{"feature","owner","rule","text","level","need","word","reasons","command"}]
- "records"
+ "evidence": {feature: {source: {os: {"commit","at","result","current","path"}}}}
```

Changes to the fixtures, in `regulated.json`:

- `login RULE-3` (held) becomes `[level: passed]`, with a weak finding that does not block.
- `checkout_design RULE-1` (unsettled) becomes `weak` with `the AI audit could not decide: …`.
- `invoice RULE-3` becomes a hand-check queue row.

`solo.json` gains a rule with `no proof written` and a `@manual` rule (Q1). `team.json` gains one incomplete feature.

## 3. Impacted selection

**The rule.** No commits are compared. With no feature named, `purlin:test` selects feature F when any of these holds:

- No section for this machine's OS exists in either source.
- The newest such section's `fingerprint` differs from the fingerprint computed now, on any of `spec`, `code` or `tests`.
- `git status --porcelain --untracked-files=all` shows an untracked, non-ignored file under F's scope entries or next to a marker file of F **(Q7)**.
- F is incomplete **(Q4)**.

Fingerprints survive rebase, merge and a dirty tree, which a comparison of commit ranges does not. The stored `commit` is used only for the `since a1b2c3d` wording.

**Anchors.** An anchor's rule and proof lines are part of every requiring feature's `spec` hash, so changing an anchor selects every feature that requires it, transitively, and every feature a global anchor covers. The anchor itself is selected by its own hashes.

**Flags.** `--all` runs every feature. `--feature <name>` names features, as today. `purlin:build` keeps calling `--feature`. `purlin:audit` runs tests on the same selection, then audits every rule that has no entry for its current hashes (section 4). `purlin:audit --all` forces both.

**What the run prints**

```
Selected 3 of 34 features: login (code changed since a1b2c3d), export (spec changed since 9f8e7d6), invoice (no run on macos yet).
Skipped 31 features whose spec, code and tests match their evidence: auth, billing, cart, … and 21 more. purlin:test --all runs them too.
src/auth/new_token.py is under login's scope and is not tracked, so its content is not part of the evidence until you git add it.
```

**Incomplete specs.** A feature spec is incomplete when it has no `> Scope:` line, or when its scope names nothing that exists. Recommended treatment **(Q4)**:

- Its rules' cells are computed as usual.
- The feature carries `incomplete: true`.
- Status prints the line in section 8.
- The gate check has a section `Incomplete (n)`.
- `purlin:sign` refuses the tag: `No tag: export has no > Scope: line, so its evidence cannot be checked against its code.`
- Anchors are exempt, because their code is the requiring feature's.

**Maintaining `> Scope:`.**

- `purlin:spec` writes `> Scope:` on every new spec: the files the requirement touches, or the paths `purlin:build` will create.
- `purlin:build` compares the files it created, edited or deleted for the feature with the scope and rewrites the line in the same commit as the code. It adds a new file that no entry covers and removes entries for deleted files.
- `purlin:spec-from-code` already lists scope files (`skills/spec-from-code/SKILL.md:29`).

## 4. The AI audit call

- **Where.** `_audit` in `purlin_run.py:956`. The run goes: tests, then breaks when `mutation_engine != none`, then the AI audit, then the evidence write, then one commit. `_audit_report` (`purlin_run.py:1039-1085`) is replaced. `scripts/review/brief.py` becomes `scripts/review/ai_audit.py` (`git mv`) and keeps `model_prompt`, `INSTRUCTION` and `model_observations`. It writes no files.
- **Granularity.** One model call per rule (implied by 35, which skips per rule and has signatures lock per rule). Calls run one at a time **(Q10)**.
- **Which rules.** Own rules of every feature with at least one tested proof whose tests passed in this run, or whose current section says `passed`, and that have no audit entry for their current hashes. `--all` removes that last condition. Rules at every level and every gate are read **(Q2)**. Rules whose tests failed are not read: their tests will change.
- **The call.**
  - Command: `claude -p --output-format json`, with the prompt on stdin (`subprocess.run(input=…)`), which closes G7. The working directory is the project root and the timeout is 300 s per call, as `brief.py:324` has it now.
  - Read `result`. Read `total_cost_usd` and `duration_ms` when present; I have not checked that these field names hold for every CLI version, so they are optional.
  - Parse with the existing contract (`brief.py:272-287, 336-355`):
    - `settled: yes` and no lines gives verdict `strong`.
    - `settled: yes` with lines gives `weak`, and the lines are the findings.
    - `settled: no` gives `undecided`, and the lines are the findings.
- **Failures.** No `claude` on PATH, a non-zero exit, a timeout, or an answer with no `settled:` line after one retry: nothing is recorded for that rule. The payload reads `not audited` with the reason (Q3). The run prints one line per cause with a count, and exits 1 at `strong` and above.
- **What decides "unchanged since its last audit".** `audit.rules[R]` equals the rule's current `(rule_hash, proof_hash, test_hash)` (implied by 35). A mutation score is re-measured for a feature only when at least one of its rules is audited **(Q5)**.
- **Remote run.** No AI audit and no breaks run on CI (implied by 28, 31 and 35). A remote run is `purlin:test --remote`, and `purlin:audit` is the command that calls the model. The `--ci` arm writes only a platform section to `ci/<f>.json`. The branch at `purlin_run.py:1139-1160` goes.
- **Cost.**
  - One call per audited rule. Each prompt carries `review_criteria.md` (9,018 bytes), the rule, its proofs and its test bodies.
  - Later runs cost one call per rule whose text, proof or test changed. `--all` costs one call per rule with a passing test.
  - This repository has 549 rules, 12 of them with a `@manual` proof. Its first audit is about 537 sequential calls, which at 300 s each is a ceiling of 44.75 hours.
  - The run prints `AI audit: 12 calls, $0.84, 6 min 10 s.` when the CLI reports cost, and `AI audit: 12 calls, 6 min 10 s.` when it does not.

## 5. Init

**Questions, in order**

| # | Question | Asked when | Default | Writes |
|---|---|---|---|---|
| 1 | `What must be true of every rule before a version is proven?` Choices: `passed  every rule's tagged tests pass`, `strong  tests pass and the audit finds them sound`, `signed  strong, and a person signs each rule` | always, unless `--gate` is given | `passed` | `gate` |
| 2 | `There is nothing here to detect a test framework from. Which one do the tests use?` | nothing detected | `shell` | `test_framework` |
| 3 | `Measure test strength by breaking the code on purpose? It needs <engine> and takes minutes to hours per run. [y/N]` | an engine exists for a detected framework; otherwise init writes `none` and prints one line | no | `mutation_engine` (`none` or `auto`), and `min_strength` (70 at `strong`, 80 at `signed`, null at `passed`) when yes |
| 4 | `Do you trust your own machine for the tests and the signing? [y/n]` | always | y | `trust` |

The `sign_at` question goes. `write_engine` (`scaffold.py:464-473`) runs only when the answer to 3 is yes.

**Config keys.**

- `.purlin/config.json`: `version`, `gate`, `mutation_engine`, `min_strength`, `test_framework`, `sql_engine`, `ci`, `trust`, and `digest` where present (G10).
- `templates/config.json`: `{"version","gate":"passed","mutation_engine":"none","min_strength":null,"sql_engine":null,"ci":"github","test_framework":"auto","trust":"local"}`.
- This repository's own config drops `sign_at` and keeps `mutation_engine: auto` and `min_strength: 80`.

**`purlin:init --update` on a 0.9.5 project**

0.9.5 wrote no `gate`, no rule tags, no holds and no signatures, and it wrote `*.receipt.json` and `*.proofs-*.json` beside specs (`git ls-tree v0.9.5`).

- **35:** asks question 3 (0.9.5 had no `mutation_engine`).
- **36:** asks the gate, as today (`update.py:305-318` reads `pre_push: strict` as `strong`). It rewrites no tags and writes no `sign_at`.
- **37:** nothing to migrate.
- **39:** prints, as an advisory rather than a migration, `2 specs have no > Scope: line: a, b. Run purlin:spec <name> to add one.`
- **40:**
  - The `untracked-files` migration (`update.py:209-242`) still deletes receipts and proof files.
  - The `records` migration becomes `evidence`: it creates `.purlin/evidence/README.md`.
  - `IGNORE_LINES` loses `.purlin/briefs/**/*.brief.txt`.
- **42:** nothing.
- **43:** the `workflows` migration replaces `windows-proofs.yml` with a freshly rendered workflow. This is unchanged.

## 6. Drift

The range runs from `since` to HEAD. `since` is the newest `signed/*` tag reachable from HEAD (`git describe --tags --match 'signed/*' --abbrev=0`), else the commit that added `.purlin/config.json`, else the last 20 commits **(Q11)**. `--since` stays as `drift.py:211-229` validates it. Every view also prints `<n> spec files have changes that are not committed.` from `git status --porcelain -- specs/` when n > 0.

**`pm`.** It compares rule id-to-text maps from `git show <since>:<spec>` against HEAD for every spec in `git diff --name-only <since>..HEAD -- specs/`, plus specs added or deleted in that range.

- `rules_added`: `3 rules added: login RULE-7, RULE-8; export RULE-2.`
- `rules_changed`: `2 rules changed: login RULE-3, billing RULE-1.`
- `rules_removed`: `1 rule removed: cart RULE-4.`
- Nothing changed: `No rule was added, changed or removed since signed/1.4.0.`

**`eng`**

- `code_changed`, from the files in `git diff --name-only <since>..HEAD` matched to scope with the section-2 expansion: `4 files changed under login's scope: RULE-1, RULE-2, RULE-5 are behind them.` Files matched by no scope: `2 changed files are under no spec's scope: src/x.py, src/y.py.`
- `rules_without_test` (payload passed word `no test`): `5 rules have no test: …`
- `anchors_behind` (`pin_report`, one `git ls-remote` per source): `anchor proof_common is behind its source (now 3c4d5e6). Run: purlin:anchor sync proof_common.`
- `not_current` (payload `features[].current`): `3 features have evidence older than their code: …`

**`qa`**

- `tests_changed`: files in the range that carry a marker, mapped to features: `6 test files changed, covering login, export.`
- `signatures_stale` (payload): `2 signatures are stale: login RULE-2 (audit findings changed), …`
- `queue`: `Queue: 5 rules. 2 hand checks, 3 signatures.`

The `design` view, `criteria_without_rules`, `pm_rules_changed`, `engineer_added_rules`, `tags_missing`, `design_rules_stale` and `CHANGED_DESIGNS` are deleted. The drift criteria move to `> Criteria-Version: 8`.

## 7. Azure DevOps

**The remote run that waits** (`remote.py:_azure`). It parses org and project from the remote. Three forms are accepted: `https://dev.azure.com/<org>/<project>/_git/<repo>`, `git@ssh.dev.azure.com:v3/<org>/<project>/<repo>` and `https://<org>.visualstudio.com/<project>/_git/<repo>`. Then:

1. Look up the run, retrying every 3 s for up to 60 s: `az pipelines runs list --organization https://dev.azure.com/<org> --project <project> --branch refs/heads/<run_branch> --top 1 --query "[0].id" --output tsv`.
2. Poll every 15 s for up to 90 minutes: `az pipelines runs show --id <id> --organization … --project … --query "[status,result]" --output tsv`. It stops at `completed`. `succeeded` exits 0; `failed`, `canceled` and `partiallySucceeded` exit 1.
3. `git pull --ff-only origin <run_branch>`, delete the run branch, print the table.

With no `az`, it prints today's instructions and returns 1, not 0.

**A committer check that does not rest on a name** (new `scripts/mcp/purlin/provenance.py`, which P2 creates from `records.record_label`):

1. The tag run learns its own identity from `GET {SYSTEM_TEAMFOUNDATIONCOLLECTIONURI}_apis/connectionData?api-version=7.0`, with `Authorization: Bearer $SYSTEM_ACCESSTOKEN`, reading `authenticatedUser.id`.
2. For each `ci/` file it finds the commit that last changed it (`git log -1 --format=%H -- <path>`).
3. It calls `GET {collection}{project}/_apis/git/repositories/{repo}/commits/{sha}?api-version=7.0` and compares `push.pushedBy.id` with the id from step 1.
4. On a mismatch, a missing `push`, or HTTP 401/403, it names the file under `Evidence` and fails closed.

Off a runner, it prints `ci/ provenance is checked by the tag run; this machine has no token.` and counts the files as unverified.

The Azure template's gate step gains `env: SYSTEM_ACCESSTOKEN: $(System.AccessToken)`. GitHub keeps its signature-plus-committer check (`records.py:282-291`).

A squash-merge or rebase that rewrites a `ci/` commit breaks provenance. The docs have to say so.

**What can be tested without an Azure project:**

- URL parsing for the three forms.
- The argv of each `az` command.
- The polling state machine with fake outputs: not registered, `inProgress`, `completed` with `succeeded` or `failed`, and the 90-minute timeout.
- The pull and delete calls.
- `provenance.py` against a fake HTTP opener with canned `connectionData` and commit JSON (match, mismatch, no `push`, 401).
- That the template renders the token env.
- The choice between `changeType: edit` and `add`.

**What cannot be tested without one:**

- Whether `commits/{id}` returns `push.pushedBy` for a commit the Pushes API created. This is the load-bearing assumption and must be checked on a real project.
- Whether the build-service identity id is the same across the run-branch run and the tag run, which depends on the job's authorization scope (project or collection).
- The token's permissions: Contribute on the repository, and reading `connectionData`.
- The `azure-devops` extension's behaviour and login.
- How long a run takes to register.

## 8. Surfaces (exact text)

**`purlin:status`**

```
Purlin status: acme, plugin 0.10.0, gate signed

<table: Spec | Rules | Proofs | Tests | Strong | Signed>

40 of 42 rules meet the gate signed.
Untested 1 · Failing 0 · Partial 0 · Passing 3 · Strong 4 · Signed 34.
12 features, 88 proof lines · 2 without a test, minimum test strength 80%, 2 rules not audited, 1 signature stale.
Queue: 5 rules. 2 hand checks, 3 signatures.
1 spec has no > Scope: line, so its evidence cannot be checked against its code: export.
1 rule is marked above the gate and is read as signed.
→ Next: run purlin:audit. 2 rules have no audit of their text, proof and test.
→ Queue: 5 rules need a person. Run purlin:sign.
```

The `Strong` column appears at `strong` and above, and `Signed` at `signed`. `Signable` is gone. An incomplete spec's name reads `export · no scope`.

The next-step order is:

1. `purlin:spec` (no proof written)
2. `purlin:build` (failing, partial, no test)
3. `purlin:test` (`not run`, `code changed`), or `purlin:test --remote` under `trust: remote`
4. `purlin:audit` (`not audited`)
5. `purlin:build` (`weak`)
6. `purlin:sign` (queue)
7. `nothing is outstanding at gate <gate>.`

**`purlin:test`, last lines**

```
Evidence committed.
<status>
gate passed: 40 of 42
```

or `gate not met: 38 of 42`, preceded by the lines in section 3.

**`purlin:audit`, last lines**

```
AI audit: 12 rules read, 10 strong, 2 weak. 30 rules skipped; their text, proof and test match their last audit. purlin:audit --all reads them again.
Test strength: not measured; mutation testing is off.
2 rules could not be audited: claude is not on PATH. Install Claude Code, then run purlin:audit again.
2 signatures went stale: their audit findings changed.
Evidence committed.
gate strong: 40 of 42
```

At gate `passed` the last line is `Audit: 38 strong, 4 weak. Nothing blocks at the gate passed.` and the exit code is 0.

**`purlin:sign`.** The header is `Queue: 5 rules. 2 hand checks, 3 signatures.` Each row reads:

```
login RULE-3   level signed   hand check
Rule
  <text>
Proof
  PROOF-4 (@manual): <text>
What the audit found
  Strong. It found nothing.        (or: Weak. <finding>)
login RULE-3   sign / case / skip:
```

After `sign` on a hand check it asks `What did you see, in one line:`. A signature row's first line reads `login RULE-2   level signed   signature   stale: audit findings changed after the signature`. The close is `Walked 5 rules: 3 signed, 1 case added, 1 skipped.`, followed by the tag lines as today (`sign.py:92-96`). `hold` is gone.

**Dashboard**

- Tabs: `Board` and `Queue`. `Queue` appears whenever the queue can hold a row: every gate under Q1-A.
- Queue header: `5 rules need a person`, with the subline `Hand checks 2 · Signatures 3`.
- Queue columns: `Spec`, `Rule`, `What it claims`, `Level`, `Needs`, `Command`.
- Empty queue: `No rule is waiting for a person. A rule arrives here when its proof is @manual, or when its level is signed and it has passed its tests and its audit.`
- Tiles are unchanged. Flag cards: `Queue`, plus `Stale` at `signed`.
- The rule screen reads `Level signed (marked)`, `Level strong (the gate)` or `Level strong (marked signed; the gate is the ceiling)`, and shows an "Audit" panel with the verdict, the findings and the strength.

## 9. The work, in pieces

Each piece names its files, what must land first, and the grep that must find nothing when it is done. At most two pieces run at once. Code pieces update the fixtures. The payload schema goes to 9 in P2, and `dev/test_purlin_report*.py` is expected to be red until S1.

1. **P1: 40a, fingerprint and evidence reader.**
   - Files: new `scripts/mcp/purlin/fingerprint.py` and `scripts/mcp/purlin/evidence.py`; `specs.py` (scope expansion moves out); new `references/formats/evidence_format.md`; new `specs/mcp/evidence.md`; `dev/test_fingerprint.py` and `dev/test_evidence_reader.py`.
   - After: d38 and d41. Runs beside G1.
   - Grep: `grep -n "def scope_tree" scripts/mcp/purlin/specs.py`.
2. **G1: 43a, the Azure remote run waits.**
   - Files: `scripts/run/remote.py`, `dev/test_remote.py`, `specs/run/records.md` (the remote-run rules).
   - After: d41. Runs beside P1.
   - Grep: `grep -rn "TODO(ado-remote)" scripts`.
3. **P2: 40b, write and read evidence.**
   - Files:
     - `purlin_run.py`
     - new `scripts/run/evidence.py`
     - `git mv scripts/run/records.py scripts/run/host.py`, which keeps only API commits and ref helpers, plus merge-on-commit and `changeType: edit`
     - delete `scripts/run/results.py`, `scripts/mcp/purlin/records.py` and `scripts/mcp/purlin/results.py`
     - new `provenance.py`
     - `payload.py` (schema 9, `evidence`), `states.py` (the passed cell from current sections, closing G1 and G4), `sign.py` (T, `has_a_ci_run`), `gate_check.py` (provenance over `.purlin/evidence/ci/`), `drift.py` (`resolve_since` pathspec only), `scan.py`
     - `templates/*.yml` comments, `gitignore.purlin`
     - delete `record_format.md` and `tests_format.md`
     - `specs/run/{records,test_results,run_script}.md`, `specs/mcp/states.md`; fixtures
   - After: P1.
   - Grep: `grep -rnE "\.purlin/(records|briefs|tests/)|purlin-(record|tests)/|record for %s|tests at %s|write_record|load_records|results_reader" scripts templates`
4. **P3: 36, levels.**
   - Files: `gate.py`, `specs.py` (the `[level:]` tag), `states.py`, `payload.py`, `status.py`, `board.py`, `gate_check.py`, `sign.py`, `brief.py` (`asks_for_a_review`), `scaffold.py` and `update.py` (`sign_at`), `templates/config.json`, `.purlin/config.json`, `spec_format.md` (version 13), `signature_format.md` (version 7), `specs/dashboard/purlin_report.md` (all 40 rules marked `[level: passed]`), `specs/mcp/states.md`, `specs/init/*`, fixtures. It patches `drift.py` field names only.
   - After: P2. Runs beside G2.
   - Grep: `grep -rnwE "bar|bar_from|sign_at|SIGN_AT|cleared|drafted|DRAFTED|READY|BARS|default_bar" scripts templates references/formats` and `grep -rn "\[bar:" specs references`
5. **G2: 43b, a committer check that does not rest on a name.**
   - Files: `provenance.py`, `templates/purlin.azure-pipelines.yml`, `dev/test_provenance.py`, `specs/ci/gate_check.md` (provenance rules).
   - After: P2. Runs beside P3.
   - Grep: `grep -rnE "_AZURE_COMMITTERS|Project Collection Build Service" scripts`
6. **P4: 37, one queue, no holds.**
   - Files: `states.py`, `signatures.py` (holds removed), `sign.py` (the walk, `--hold` removed, the hand-check note, sign at `passed` for hand checks), `payload.py` (`queue`), `board.py`, `status.py`, `gate_check.py` (sections), `drift.py` (`queue` size only), `signature_format.md` (version 8), `specs/review/signatures.md`, `specs/ci/gate_check.md`, fixtures.
   - After: P3 and G2.
   - Grep: `grep -rnwE "hold|held|HOLD_SCHEMA|HOLD_NAME_RE|review_list|sign_list|signable|REVIEW_WORDS|to_review|to_sign" scripts templates references/formats`
7. **P5: 35, the audit.**
   - Files: `purlin_run.py` (`_audit`, `--all`, model calls, skip rule, exit at `passed`), `git mv scripts/review/brief.py scripts/review/ai_audit.py`, `states.py` (strong cell), `signatures.py` (`audit_hash` from evidence), `gate.py` (breaks from `mutation_engine`), `mutation/__init__.py` (no tier), `payload.py` (`rules[].audit`), `sign.py` (rendering), `evidence_format.md` (version 2), `signature_format.md` (version 9), `specs/review/brief.md` renamed to `ai_audit.md`, `specs/run/mutation.md`, fixtures.
   - After: P4. Runs beside P6.
   - Grep: `grep -rnE "unsettled|settled.:|NO_MODEL|NOT_AVAILABLE|brief\.json|write_brief|build_brief|briefs_dir|find_brief" scripts templates references/formats`
8. **P6: 42, drift by role.**
   - Files: `drift.py`, `server.py` (tool text), `references/drift_criteria.md` (version 8), `skills/drift/SKILL.md`, `specs/mcp/drift.md`, `specs/skills/skill_drift.md`, `dev/test_drift.py`.
   - After: P4. Runs beside P5.
   - Grep: `grep -rnE "'design'|design_rules_stale|designs_changed|criteria_without_rules|pm_rules_changed|engineer_added_rules|tags_missing|CHANGED_DESIGNS" scripts references/drift_criteria.md skills/drift`
9. **P7: 39, a run covers what the change touched.**
   - Files: `purlin_run.py` (default selection, `--all`, printing), `fingerprint.py` (the compare), `payload.py` and `status.py` (`incomplete`), `sign.py` (tag refusal), `gate_check.py` (the `Incomplete` section), `spec_format.md` (Scope required, version 14), `skills/spec/SKILL.md`, `skills/build/SKILL.md`, `skills/test/SKILL.md` (Step 1 and usage), their `specs/skills/*.md`, `specs/run/run_script.md`, fixtures.
   - After: P5. Runs beside P8.
   - Grep: `grep -n "name at least one --feature, or --all" scripts/run/purlin_run.py` and ``grep -n "| `> Scope:` | No" references/formats/spec_format.md``
10. **P8: init and update (35, 36, 39 and 40 parts).**
    - Files: `scaffold.py`, `update.py`, `templates/config.json`, `templates/gitignore.purlin`, `skills/init/SKILL.md`, `specs/init/*`, `specs/skills/skill_init.md`, `dev/test_init_*`.
    - After: P5. Runs beside P7.
    - Grep: `grep -rnE "sign_at|SIGN_AT|RECORDS_README|\.purlin/records|briefs" scripts/init templates`
11. **S1: dashboard.**
    - Files: `scripts/report/src/*` (`review.js` becomes `queue.js`), rebuild of `purlin-report.html`, screenshots, the rules of `specs/dashboard/purlin_report.md`, `dev/test_purlin_report*.py`.
    - After: P7 and P8. Runs beside S2.
    - Grep: `grep -rnE "Review|'Sign'|signable|Signable|held|unsettled|\bbar\b|review_list|sign_list|records|SCHEMA = 8" scripts/report/src`
12. **S2: prose.**
    - Files: every other `skills/*/SKILL.md`, `agents/purlin.md`, `references/{glossary,hard_gates,review_criteria,purlin_commands,commit_conventions,spec_quality_guide}.md`, `CLAUDE.md` format table, `docs/`, `README.md`, the 0.10.0 entry in `RELEASE_NOTES.md`.
    - After: P7 and P8. Runs beside S1.
    - Grep: `grep -rnwiE "bar|sign_at|signable|held|hold|unsettled|drafted|brief|record" skills agents references docs README.md` (outside `references/formats/`), and `grep -rn "Review list\|Sign list\|spec status\|test results" skills agents references docs README.md`

Decision 44's sweep follows S1 and S2. It is not part of this design.

**Which questions block which pieces:** Q1 blocks P3 and P4. Q2, Q3, Q5 and Q10 block P5. Q6 blocks P3. Q4 and Q7 block P7. Q8 blocks P2. Q9 blocks P1 and P2. Q11 blocks P6.

## 10. The owner's answers (2026-09-27)

Every question this design raised is closed. Where an answer differs from the text above,
the answer wins, and the piece that owns the text applies it.

| Question | Answer | What it changes above |
|---|---|---|
| Q1 hand checks | **As today.** At the gate `passed` a rule whose proofs are all `@manual` reads `passed` with nothing checked. At `strong` and above it waits in the queue for a signed note. | Sections 1 and 8: the passed cell has no `manual test` word; `manual test` stays a word of the strong cell; the queue and its dashboard tab exist at `strong` and above, not at `passed`; `purlin:sign` still refuses at the gate `passed`. |
| Q2 audit scope | **A rule whose level is `passed` is never audited** when the gate is higher. At the gate `passed`, `purlin:audit` reads every rule with a passing test, prints and commits, and blocks nothing (decision 35). | Section 4 "Which rules": add the condition `level >= strong`, except at the gate `passed`. |
| Q3 model cannot be reached | `not audited`, nothing saved, the next audit tries again. | As designed. |
| Q4 a spec with no `> Scope:` | **Optional below `signed`, required at `signed`.** Below `signed` its tests pass and its audit can read `strong`; the only cost is that Purlin cannot tell which code belongs to it, so a default run always selects it and says why. At the gate `signed` a rule of such a spec cannot be signed and no tag is written, because a signature requires the rule to be tied to the files it governs. | Section 3 "Incomplete specs": `incomplete` is reported at every gate and blocks only at `signed`, where `purlin:sign` refuses the rule and the tag and the gate check lists it. Decision 39's "required" reads "required at `signed`". `spec_format.md` says so. |
| Q5 strength after a code change | Not re-measured. | As designed. |
| Q6 level in a signature | **Logged, not locked.** | As designed. |
| Q7 untracked file | Selects the feature and prints a note; joins the evidence once added. | As designed. |
| Q8 the word | **`out of date`**, with the reason naming what changed: `code changed since a1b2c3d`, `spec changed since ...`, `tests changed since ...`. `code changed` is no longer a status word. | Sections 1, 6 and 8: replace the word everywhere; drift's `not_current` line reads `3 features are out of date: ...`. |
| Q9 operating systems | One file per feature, a section per system. | As designed. |
| Q10 audit speed | **A setting, default four.** Config key `audit_parallel`, an integer from 1 to 16, default 4, written by init without a question. A call refused for rate leaves its rule `not audited`. | Section 4 "Granularity" and section 5 config keys. |
| Q11 where drift starts | **The last git action that brought changes in.** Drift is for a person who has just pulled, merged, rebased or checked out. The range runs from where HEAD stood before that action to HEAD: the newest reflog entry of `HEAD` whose action is `pull`, `merge`, `rebase (finish)`, `checkout`, `clone` or `reset`, from its old sha to HEAD. With no such entry, the last 20 commits. `--since` still overrides. | Section 6: replace the `signed/*` tag rule. |

From the stale inventory's open points, also closed by the owner:

- The vocabulary guard stays as a development test under `dev/`, with its own list.
- `RELEASE_NOTES.md` covers only what changed for a 0.9.5 user; words and mechanisms that
  lived only on development branches are left out, and the paragraph on the line that never
  shipped goes.
- The root `settings.json` is deleted.
- The end-to-end setup test for a C# project is finished, not removed.
- Release tags stay; `pre-instruction-optimization` goes on the owner's closeout list.
- Decision 45 (three roles, the brand kit) and decision 44 (a clean release) bind every piece.
- Decision 48: a signature records `machine` (the host's name) and `os` beside the signer
  and the time, neither of them hashed. The signed-commit condition and `trust: remote`
  stay as they are. Piece P4 adds the two fields and bumps `signature_format.md`.
- Decision 50, which wins over sections 2, 4 and 8 where they differ:
  - A run writes the evidence file and does not commit it. `--commit` on `purlin:test` and
    `purlin:audit` commits it with the subject `purlin: evidence at <sha7>`; the run's last
    lines read `Evidence written to .purlin/evidence/local/<feature>.json.` and, with
    `--commit`, `Evidence committed.` The `--ci` arm on a run branch always commits.
    `.purlin/tests.md` is written and committed with the evidence. The payload's
    `features[].evidence.<source>` gains `committed: bool` (the file is tracked and matches
    HEAD). `purlin:sign` refuses a rule, and the tag, while any feature it reads has
    evidence that is not committed: `sign: login has evidence that is not committed. Run:
    purlin:test --commit`. Piece P2 owns the write and the flag; P4 owns the refusal.
  - The hooks go: `hooks/hooks.json`, `scripts/hooks/refresh_digest.py`, the `digest`
    setting, their spec, tests and docs. The four commands refresh `.purlin/report-data.js`
    as they finish. Piece S1 owns it.
  - `purlin:audit` prints `AI audit: <n> rules to read, <k> at a time.` before the first
    call. Piece P5 owns it.
  - At the gate `passed` no surface prints a word of a higher level. Pieces S1 and S2 own it.
- The vocabulary guard under `dev/` still forbids `queue` and, in prose, `verdict`. The
  queue is the owner's word (decision 37): piece P4 removes it from the guard's list. The
  audit's field is `verdict` in machine text; in prose the pages say what the audit found.
- Decisions 51 to 53 add three pieces after S1 and S2 and amend two:
  - **P5 (the audit)** also records, per finding, `model` (name and version as the model
    CLI reports them) and `criteria` (sha256 of `references/review_criteria.md` as sent).
    The audit hash a signature locks does not include either.
  - **P4 (the queue)** also writes `signed/<version>` as a signed tag (`git tag -s`).
  - **P9: proofs and the marker comment, no plugins** (decision 51).
  - **P10: the evidence package**, `purlin:export` (decision 52).
  - **S2 (prose)** carries decision 53 and the rewrite of `docs/regulated-workflow.md` and
    the README's statement of intended use (decision 52); where P9 and P10 land after it,
    each of them updates the pages it changes.
