# Decision 103: evidence is signed once, at the release

Written by the planning agent on 2026-09-30, against `d103/base` at `1948eb7e8`. It builds
decision 103 of `three-levels.md` and nothing else. Ten lanes run at once, each a cloud session on
Linux on a branch `lane/d103-<lane>` made from `d103/base`, each owning files no other lane writes.
One integration agent then merges them on the owner's Mac. Section 2 is the contract: every lane
builds to it and none chooses. Section 8 holds the one question decision 103 leaves open.

Decision 103 reverses most of what decision 102 built for signatures. What stays from 102: the
warning and the failed cells for a number written twice or a line left from a merge conflict, the
refusal while the branch's copy on the host holds commits the checkout lacks, drift's lines for a
reused number, a changed test comment, the age of the default branch and the proofs added, changed
and moved, the walk's line naming each proof's tied test, and the verified commit. What goes: the
per-rule signature, its file, its hashes, its ended line and every cause, the hand-check binding,
signing a rule as not applying, the gate `strong`, `min_strength`, and every `Left to do` kind that
waits on a person or on the audit.

The owner's accepted calls, built to as written:

- Evidence may still be committed on any branch, but a release uses only the evidence at the
  release commit.
- The upgrade maps a project at the gate `strong` to `passed`, with the audit kept on as a tool.
- A hand check's note is typed during the sign-off walk by whoever signs.
- Clean release (decision 44): what decision 103 retires is deleted outright, including what
  decision 102 built for per-rule signatures that end and decision 101's signature as not
  applying. `RELEASE_NOTES.md` alone keeps history; what the 0.9.5 upgrade needs is the one
  exception.
- This repository's own `.purlin/config.json` moves to the new gate model.

## 1. Rules for every lane

`d102-plan.md` section 1 applies as written, with these names and changes.

- **Branch and scratch.** Lane `<lane>` works in its own cloud session's clone, on branch
  `lane/d103-<lane>` made from `origin/d103/base`, with a scratch folder of its own. It writes only
  the files section 4 gives it. It cannot see the other lanes: where it calls what another lane
  builds, it calls it exactly as section 2 names it, and the tests that need it fail until that
  lane merges (each lane's section lists them).
- **Environment (Linux, section 5).** First:
  `apt-get update -q && apt-get install -y -q openssh-client sqlite3`, then
  `python3 -m venv .venv && .venv/bin/pip install -q pytest playwright`, then
  `export PATH=$PWD/.venv/bin:$PATH`. A lane runs its own test files whole with
  `.venv/bin/python -m pytest <files> -q`, then `bash dev/run_tests.sh --fast`. It never runs the
  full sweep.
- **Frozen:** `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
  `dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`. No lane
  calls `mcp_project.Project.signature`, `sign_project.REVIEW_GATE`,
  `sign_project.Project.signatures` or `sign_project.Project.load`: each goes at integration
  (section 6, step 2). A lane that needs a helper writes it in its own test file.
- **No generated file is staged:** `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`, `docs/images/*.png`,
  `dev/plans/deck/*.png`.
- **Proofs.** Every proof written or rewritten holds one case in at most 60 words and has a marked
  test of its own. New rules and proofs take numbers in order from the next free ones section 4
  gives, which follow each spec's `> Highest-Rule:` / `> Highest-Proof:` at `1948eb7e8`, and raise
  those lines. A number is never reused, a deleted one included. A proof names what a person sees
  or a file holds, never a function inside the code (decision 98).
- **Clean release** (decision 44). What this plan retires is deleted outright: its code, its
  constants, its rules, its proofs and their tests, its lines in skills, references and docs. No
  test that a removed thing is absent, no compatibility reader, nothing added to
  `dev/test_vocabulary.py`. `RELEASE_NOTES.md` is the one place history is kept; the upgrade
  (lane `settings`) is the one exception in code.
- **A rule that survives in part is reworded, not split into an old and a new one.** Its number
  stays; each proof that no longer holds is deleted or rewritten to one case of the new contract.
- **Formats.** A change to a format's parsing or emission updates its file under
  `references/formats/` in the same commit, with the number C14 gives.
- **Instruction lengths** (decision 80, `phase3-plan.md` section 1): status 100, test 120, build
  130, init 250, audit 105, sign 185, export 90, spec 210, spec-from-code 130, drift 150, anchor
  160, agent 135. Today: status 100, build 128, agent 134, sign 184; every line added there cuts
  one.
- **Deliberate break.** Each lane breaks its most important change on purpose (named in its
  section), sees its own test fail, then restores the file with `git checkout -- <that file>`,
  never `git checkout -- specs/`. The break runs only under a test that uses `dev/fake_claude.py`
  or no model, with no real `claude` on `PATH`, and reaches no git host, `gh`, `az` or network
  service: every repository a test makes is local, and a "host" is a bare repository on disk.
- **A call no decision makes and this plan does not make:** build the rest, leave that thing as
  it is, report it.
- **Commits** on the lane branch with the prefixes of `references/commit_conventions.md`, each
  ending with the attribution lines the session gives. Push the lane branch
  (`git push -u origin lane/d103-<lane>`) and nothing else: no tag, no pull request, no push to
  `d103/base` or `main`, no `purlin:audit`, no `purlin:sign`, no `purlin:test --release`, no real
  `claude`.
- **Report** (in the last message and in `dev/plans/lanes/d103-<lane>.md`, committed on the lane
  branch): each spec's `> Highest-Rule:` and `> Highest-Proof:` after the work; tests before and
  after; every rule and proof deleted or reworded, by number; every call left; every word chosen
  that section 7 does not give; every failure in a file it does not own; every test that fails
  only because another lane has not merged.

## 2. Contracts

What two lanes share, fixed word for word. `<...>` is filled in. Filled examples use the sample
project of `sanity-qa-product.md` (`sample_age`, `quinn.qa@labconnect.example`) on a release
branch `release/1.2.0` at `8de0b6e`.

### C1. The two gates, lane `settings`

In `scripts/mcp/purlin/gate.py`:

```python
GATES = ('passed', 'signed')
DEFAULT_GATE = 'passed'
RETIRED_KEYS = ('spec_dir', 'audit_criteria', 'pre_push', 'min_strength')

NOT_A_GATE = ('%s is not accepted for gate in .purlin/config.json; it takes '
              'passed or signed. Reading it as passed; set it with '
              'purlin:init --gate <gate>.')
STRONG_RETIRED = ('"strong" is no longer a gate: it reads as passed, and the '
                  'audit stays a tool you run. Run purlin:init --update.')
```

- `passed`: every rule's tests pass on the evidence committed at the release commit.
  `signed`: the same, and at least one person signs the evidence package (C6).
- `GateConfig.__slots__` is `('gate', 'breaks', 'mutation_engine', 'audit_parallel', 'ci',
  'warnings')`. `min_strength` and `_DERIVED` are deleted.
- `breaks` is `str(mutation_engine).strip().lower() != 'none'`, at either gate.
- A `gate` of `"strong"` reads as `passed` with the one warning `STRONG_RETIRED` in place of
  `NOT_A_GATE`. Any other value not in `GATES` keeps `NOT_A_GATE`.
- A `min_strength` key in the file joins the retired-keys warning that already names
  `purlin:init --update`:
  `.purlin/config.json still carries min_strength, which this release does not read. Run purlin:init --update.`

**The settings that go:** the value `strong` of `gate`; the key `min_strength`. `mutation_engine`
and `audit_parallel` stay, with no force on any gate: the breaks and the audit run when a person
runs `purlin:audit`, and nothing waits on them.

**The settings tool** (`scripts/mcp/purlin/server.py`): `gate` takes `passed or signed`;
`min_strength` leaves `KNOWN_SETTINGS`; writing a key of `RETIRED_KEYS` answers
`RETIRED_NOT_WRITTEN = '%s is not read by this release; nothing was saved.'`.

```
"gold" is not accepted for gate; it takes passed or signed. Nothing was saved.
min_strength is not read by this release; nothing was saved.
```

### C2. A rule's two cells, lane `counting`

In `scripts/mcp/purlin/states.py`, `CELLS = ('passed', 'strong')`, and every rule carries both at
both gates. `cells_for` and `bucket_keys` take no gate.

- **passed** is unchanged, decision 102's broken-spec reading included (`failed` with
  `specs.broken_reasons`). A proof marked `@manual` is still read out of it, so a rule whose every
  proof is `@manual` reads `passed` with no test.
- **strong** is what the audit found, and nothing waits on it. Words: `strong`, `weak`,
  `not audited`, `manual test`, `no proof`, `waiting` (while the passed cell is not met). The word
  comes from the audit entry's `verdict` alone. Its reasons: the audit's findings where weak; the
  strength where the breaks measured one, `strength 84%`; `strength not measured: <why>` where the
  engine is on and measured nothing, which no longer makes the rule weak; `AUDIT_ALONE` for an
  anchor, as now. `strength <p>% under <m>%` is deleted.
- **Deleted** from `states.py`: the signed cell, `WAITING_FOR_AUDIT`, `NAMES_NO_FILES`, `ENDED`,
  `ENDED_LINE`, every `CAUSE_*`, `NO_TEST_FILE`, `DOES_NOT_APPLY`, `DOES_NOT_APPLY_REASON`,
  `_binds`, `_ended`, `_newest`, `_does_not_apply`, and the result keys `hand_checked`,
  `does_not_apply`, `to_confirm`, `ended`. `rule_cells`' input loses `signatures`, `applies_to`,
  `code_hash`, `machines`, `audit_hash`, `incomplete` and `test_hash_kind`.
- **The bucket** is one of `untested`, `failing`, `partial`, `passed`. The flags keep `failing`,
  `partial`, `manual`, `not_audited`, `out_of_date`, `no_proof`, and gain `strong` and `weak`
  (bool), which the rollup counts beside the buckets.

### C3. `Left to do` and the sentence, lane `counting`

In `scripts/mcp/purlin/summary.py`:

```python
KINDS = (
    ('to_repair', 'spec to repair', 'specs to repair', 'purlin:spec'),
    ('no_proof', 'rule to write a proof for', 'rules to write a proof for', 'purlin:spec'),
    ('to_correct', 'test comment to correct', 'test comments to correct', 'purlin:build'),
    ('to_fix', 'rule to fix', 'rules to fix', 'purlin:build'),
    ('no_test', 'rule to write a test for', 'rules to write a test for', 'purlin:build'),
    ('to_test', 'rule to test', 'rules to test', 'purlin:test'),
    ('to_test_remote', 'rule to test on %s', 'rules to test on %s', 'purlin:test --remote'),
    ('to_strengthen', 'rule to strengthen', 'rules to strengthen', 'purlin:build'),
)
# The kinds that stop a release: a rule whose tests do not pass here, or a
# spec or a test comment the run cannot read.
BLOCKING = ('to_repair', 'to_correct', 'to_fix', 'no_test', 'to_test', 'to_test_remote')
LEFT_TO_DO = 'Left to do:'
NOTHING_LEFT = 'Nothing left to do.'
TO_RELEASE = NOTHING_LEFT + ' To release a version: purlin:test --release'
TO_RELEASE_SIGNED = NOTHING_LEFT + ' To release a version: purlin:test --release, then purlin:sign'
RELEASE = NOTHING_LEFT + ' Push the tag to release it: git push origin %s'
AUDIT_FOUND = 'The audit found %d strong and %d weak.'
```

- **Deleted kinds:** `to_test_by_hand`, `to_confirm`, `to_audit`, `to_measure`, `no_scope`,
  `to_sign`, `to_tag`. `FOR_A_PERSON`, `ended_lines`, `_weak_kind` and `_UPPER` are deleted.
- `rule_kind(rule, gate, here_os, broken=None)`: `to_repair` where `broken`; `no_proof` at the
  gate `signed` for a rule with no proof; then `to_fix`, `no_test`, `to_test_remote`, `to_test` as
  now; `to_strengthen` where the strong cell reads `weak`; else None. A `@manual` proof adds no
  kind.
- `steps(own_rules)` returns `{"passed": p}`: rules whose passed cell reads `passed`, a
  hand check included. `audit_counts(own_rules)` returns
  `{"strong": s, "weak": w, "not_audited": u}` over the rules whose passed cell reads `passed`.
- `sentence(summary)`: `<N> rules. <p> pass their tests.`, then ` ` and `AUDIT_FOUND` filled
  where `s + w > 0`. Singular forms as now (`1 rule.`, `1 passes its tests.`).

```
40 rules. 35 pass their tests.
40 rules. 35 pass their tests. The audit found 30 strong and 2 weak.
```

- `last_line(left, gate, tag)`: None while any kind is left; `RELEASE` filled where HEAD carries a
  `passed/*` or `signed/*` tag; else `TO_RELEASE` at `passed` and `TO_RELEASE_SIGNED` at `signed`.
- `left(features, gate, here_os, corrections=0)` loses `tag`; the version to tag is not work.

### C4. The payload, schema 13, lane `counting`

`SCHEMA_VERSION = 13` in `scripts/mcp/purlin/payload.py`.

- `gate`: `{"gate", "mutation_engine", "audit_parallel", "ci"}`; `min_strength` goes.
- `features[].rules[]`: `cells` holds `passed` and `strong`. Gone: `cells.signed`, `signatures`,
  `ended`, `does_not_apply`, `hand_checked`, `signed_hash`. Kept: `rule_hash`, `proof_hash`,
  `test_hash`, `test_hash_kind`, `machines` (the package reads them), `audit`, `left`, `flags`,
  `proofs` with each proof's `tests`.
- `features[].rollup`: `{rules, untested, failing, partial, passed, strong, weak, not_audited,
  manual}`. `features[].broken` stays.
- `summary`: `{rules, steps: {passed}, audit: {strong, weak, not_audited}, sentence}`.
- `tag`: `{name, commit}` for the newest `passed/*` or `signed/*` tag on HEAD, or null.
- `payload._consumers`-style signature loading is gone: `build_payload` never reads a
  `.signatures/` folder.

### C5. The release run, lane `release` (called by lane `run`)

`purlin:test --release [<version>]` is `purlin_run.py --test --all --commit --release [<version>]`:
`--release` implies `--test --all --commit` and takes an optional value that does not begin with
`-`. After the run has written and committed its evidence as today, `purlin_run.py` calls, in the
new `scripts/export/release.py`:

```python
def run_release(project_root, version=None, out=None):
    """Check the release commit, write and commit the package, tag at passed.

    Returns (tag name or None, refused kind or None). Nothing is fetched and
    nothing is pushed."""
```

and exits 1 when `refused` is not None. Checks, in this order, each printing its line and
stopping:

```python
NO_RELEASE_SPEC = ('No release: %s cannot be counted: %s. Run purlin:spec %s, then '
                   'purlin:test --release.')                           # one per broken spec
NO_RELEASE_FAILING = ('No release: %s at %s: %s. Run purlin:status to see what is left, '
                      'then purlin:test --release.')
NO_RELEASE_WORK = ('No release: the working tree holds changes that are not committed, so '
                   'the results do not describe a commit. Commit them, then run '
                   'purlin:test --release.')
NO_RELEASE_BEHIND = ('No release: %s holds %s that %s does not, as this checkout last '
                     'fetched it. Pull, then run purlin:test --release.')
NO_VERSION = ('No version: nothing in this project states one. Run purlin:test --release '
              '<version>, or write it to a VERSION file.')
NO_RELEASE_EXISTS = ('No release: %s is already written. Run purlin:test --release '
                     '<version> to name another.')
NO_RELEASE_PACKAGE = 'No release: the evidence package was not committed: %s.'
NO_TAG_GIT = 'No tag: git could not write %s: %s.'
PACKAGE_COMMITTED = 'Evidence package committed: %s.'
TAGGED = 'Tagged %s at %s.'
READY_TO_SIGN = 'Run purlin:sign to sign it; the first signature writes %s.'
REFUSED = ('spec', 'failing', 'work', 'behind', 'version', 'exists', 'package', 'git')
```

- `NO_RELEASE_FAILING`'s first slot is `1 rule does not pass` or `<n> rules do not pass`, the
  second HEAD's sha7, the third every rule whose `left` is in `summary.BLOCKING`, by feature then
  number, as `sample_age RULE-2, RULE-3; stability RULE-1`. A comment above a test that names
  nothing counts here too, as `1 test comment to correct` joined after the rules with `; `.
- `NO_RELEASE_BEHIND` is decision 102's check (the checked-out branch's upstream, else
  `origin/<branch>`, else none), moved here from `sign.py` unchanged in what it reads.
- The version is read as today (`VERSION`, `package.json`, `pyproject.toml`, the first `*.csproj`)
  or named by `--release <version>`. The tag is `passed/<version>` at `passed` and
  `signed/<version>` at `signed`; `NO_RELEASE_EXISTS` fires on the gate's own tag.
- Then it writes `.purlin/evidence/package/<version>.json` (C7) and commits it alone as
  `purlin: evidence at <sha7>`, signed where `commit.gpgsign` is on and plain otherwise, and prints
  `PACKAGE_COMMITTED`.
- **At `passed`** it writes `git tag -a passed/<version> -m <message>` on that commit, unsigned,
  and prints `TAGGED` then `summary.RELEASE` filled. **At `signed`** it writes no tag and prints
  `READY_TO_SIGN`.
- A package for the same version with no tag of the gate yet is written again over the old one.

```
No release: 2 rules do not pass at 8de0b6e: sample_age RULE-2; stability RULE-1. Run purlin:status to see what is left, then purlin:test --release.
No release: sample_age cannot be counted: PROOF-4 is written twice in the spec. Run purlin:spec sample_age, then purlin:test --release.
No release: origin/release/1.2.0 holds 1 commit that 8de0b6e does not, as this checkout last fetched it. Pull, then run purlin:test --release.
No release: passed/1.2.0 is already written. Run purlin:test --release <version> to name another.
Evidence package committed: .purlin/evidence/package/1.2.0.json.
Tagged passed/1.2.0 at 3c9d2e1.
Nothing left to do. Push the tag to release it: git push origin passed/1.2.0
Run purlin:sign to sign it; the first signature writes signed/1.2.0.
```

The tag's message, both gates: `Released at the gate <gate>.\n\nCommit: <the commit the package
describes>\nGate: <gate>\n`.

`release.py` also carries, for lane `signoff`: `project_version(project_root)`,
`tag_name(gate, version)`, `tag_exists(project_root, name)`, `behind_host(project_root)` →
`(ref, count)` or None, `behind_words(count)` → `1 commit` / `<n> commits`,
`uncommitted_work(project_root)` → bool, `package_at_head(project_root, version)` →
`(rel, package)` or None (the package file as HEAD's tree holds it), `only_signoffs_since(
project_root, commit)` → bool (every commit from `commit` to HEAD touches only
`.purlin/evidence/package/<version>.signoffs/`), and
`write_tag(project_root, name, message, signed)` → `(ok, git's first line)`.

### C6. The sign-off, lane `signoff`

One signature covers the whole package: a file, added in a signed commit, carrying the package's
`fingerprint`. Several people may sign; the first sign-off writes `signed/<version>` on its commit
and the tag never moves.

**The file**, `.purlin/evidence/package/<version>.signoffs/<signer-slug>.json`, signature format
14 (C14):

```json
{
  "schema": "purlin-signoff/1",
  "version": "1.2.0",
  "package": ".purlin/evidence/package/1.2.0.json",
  "package_hash": "<the package's fingerprint field>",
  "commit": "<the commit the package describes>",
  "signer": "quinn.qa@labconnect.example",
  "signer_name": "Quinn QA",
  "key_fingerprint": "SHA256:...",
  "timestamp": "2026-10-02T09:14:00Z",
  "shown": {
    "overview": {"rules": 40, "passing": 38, "hand_checks": 2, "strong": 30, "weak": 2,
                 "not_audited": 6, "systems": ["linux", "windows"]},
    "one_by_one": [{"feature": "sample_age", "rule": "RULE-1", "why": "weak"}],
    "in_list": [{"feature": "sample_age", "rule": "RULE-2"}],
    "list_opened": true
  },
  "notes": [{"feature": "accession_screen", "rule": "RULE-1", "kind": "hand check",
             "note": "the tube colour is red on an expired sample"}]
}
```

- `why` is `hand check`, `weak`, `not audited` or `strong`; `kind` is `hand check` or `note`.
  `one_by_one` lists every stop in the order walked; `in_list` every rule the audit found strong
  and the signer did not walk, whether or not the list was opened; `list_opened` says whether it
  was. Nothing records a judgment: no answer word, only what was shown and what was typed.
- The slug is `signatures.signer_slug(email)`, as now. One file per signer per version.
- A sign-off **counts** when the last commit touching its file is signed and that signature
  verifies (decision 102's C9, `NOT_SIGNED`, `NOT_VERIFIED`, unchanged) and its `package_hash`
  equals the committed package's `fingerprint`. The key is not compared with the signer.
- The commit subject is `sign(<version>): <signer email>`, as `sign(1.2.0): quinn.qa@labconnect.example`.
- In `scripts/mcp/purlin/signatures.py`, kept: `signer_slug`, `counts`, `NOT_SIGNED`,
  `NOT_VERIFIED` and the verification behind them, `key_fingerprint`, `home_folder`,
  `expand_home`. New: `signoffs_dir(version)` → `.purlin/evidence/package/<version>.signoffs`,
  `load_signoffs(project_root, version)` → each file's dict plus `path`, `counts` and
  `count_reason`, oldest first by `timestamp`. Deleted: `SIGNATURE_NAME_RE`,
  `TEST_HASH_KINDS`, `audit_hash`, `test_hash_kind`, `signatures_dir`, `load_signatures`,
  `SIGNED_FIELDS`, `HAND_CHECK`, `signed_hash`, `is_current`, `commit_date` where nothing else
  reads it. `rule_hash`, `proof_hash`, `test_hash` and `test_hash_kind` on a payload rule are taken
  by `payload.py` itself (lane `counting` moves `test_hash_kind` there if it is still read).

### C7. The package, lane `release`

`.purlin/evidence/package/<version>.json`, package format 7, schema `purlin-package/3`.

- `TOP_LEVEL = ('schema', 'state', 'rules', 'steps', 'audit', 'left', 'purlin_version',
  'project', 'version', 'tag', 'commit', 'gate', 'mutation_engine', 'features', 'hand_checks',
  'warnings', 'fingerprint')`. `min_strength` goes.
- `state` is `finished` when no kind of `left` is in `summary.BLOCKING`, `not finished` otherwise.
  `steps` is `{"passed": p}`, `audit` the payload's `summary.audit`.
- `tag` is the tag the release writes, `passed/<version>` or `signed/<version>`, at either gate.
- Each rule entry: its words, proofs, tests, each result on each system with its machine, what the
  audit found (`verdict`, `findings`, `strength`), `statuses` `{"passed": ..., "strong": ...}`, and
  `left`. `signatures` goes from every rule entry.
- `hand_checks`: `[{"feature", "rule", "proofs": [ids]}]` for every rule with a `@manual` proof,
  by feature then number. What a signer typed for each is in the sign-offs (C6), not here.
- The package file is written once per release run and never rewritten by a sign-off, so its
  fingerprint is the hash every sign-off carries. `purlin:export` still writes it at any time, at
  any gate.

### C8. The sign-off walk, lane `signoff`

`purlin:sign [--release <version>]` is `sign.py [--release NAME]`: the walk, one question at a
time from a terminal. `sign.py --show [--release NAME]` prints the overview and every stop and
asks nothing (the agent's first step). `sign.py --answers FILE [--release NAME]` walks with the
answers a JSON file gives (the agent's second step, C9). Every other option of today goes:
`<feature>`, `RULE-N`, `--all`, `--note`, `--does-not-apply`.

**Refusals**, in this order, each one line, nothing written, exit 1 (the first exit 0):

```python
AT_PASSED = ('Nothing is signed at the gate passed: purlin:test --release tags the '
             'release unsigned. To sign releases, run purlin:init --gate signed.')
NO_SIGNOFF_WORK = ('No sign-off: the working tree holds changes that are not committed. '
                   'Commit them, then run purlin:test --release.')
NO_SIGNOFF_PACKAGE = ('No sign-off: no evidence package for %s is committed at %s. '
                      'Run purlin:test --release.')
NO_SIGNOFF_MOVED = ('No sign-off: the evidence package for %s describes %s, and %s has '
                    'changed since. Run purlin:test --release.')
NO_SIGNOFF_FAILING = ('No sign-off: %s at %s: %s. Run purlin:status to see what is left, '
                      'then purlin:test --release.')
NO_SIGNOFF_BEHIND = ('No sign-off: %s holds %s that %s does not, as this checkout last '
                     'fetched it. Pull, then run purlin:sign.')
ALREADY_SIGNED = '%s has already signed %s over this package; nothing was written.'
```

then decision 97's `NO_VERSION` with `purlin:sign --release <version>`, and today's `NO_KEY`
block. `NO_SIGNOFF_MOVED` fires when a commit after the package's commit touches anything but the
sign-offs of that version. `NO_SIGNOFF_FAILING` reads the payload at HEAD with C5's fill.

```
No sign-off: no evidence package for 1.2.0 is committed at 8de0b6e. Run purlin:test --release.
No sign-off: the evidence package for 1.2.0 describes 3c9d2e1, and 8de0b6e has changed since. Run purlin:test --release.
No sign-off: 1 rule does not pass at 8de0b6e: sample_age RULE-2. Run purlin:status to see what is left, then purlin:test --release.
quinn.qa@labconnect.example has already signed 1.2.0 over this package; nothing was written.
```

**The overview:**

```python
OVERVIEW = 'Signing %s: %s, at %s.'
OVERVIEW_RULES = '  %s on %s: %s, %s.'   # '40 rules', systems, '38 pass their tests', '2 are checked by hand'
OVERVIEW_AUDIT = '  The audit: %d strong, %d weak, %d not audited.'
OVERVIEW_STOPS = '  %s: %d hand checks, %d weak, %d not audited.'   # '10 stops' / '1 stop'
NO_STOPS = '  No stops: nothing is checked by hand, weak or not audited.'
```

```
Signing 1.2.0: .purlin/evidence/package/1.2.0.json, at 3c9d2e1.
  40 rules on Linux/Unix and Windows: 38 pass their tests, 2 are checked by hand.
  The audit: 30 strong, 2 weak, 6 not audited.
  10 stops: 2 hand checks, 2 weak, 6 not audited.
```

Systems are `states.systems_text` of every system the package holds results for. Singular words:
`1 rule`, `1 passes its tests`, `1 is checked by hand`, `1 stop`.

**The strong list.** Where any rule is strong, before the stops:

```python
STRONG_ASK = '%s the audit found strong. list / walk / go on: '   # '30 rules' / '1 rule'
STRONG_AGAIN = 'walk / go on: '
STRONG_LIST = '  %s %s'      # feature, its rule ids joined ', '; one line per feature
```

`list` prints the list and asks `STRONG_AGAIN`; `walk` makes each strong rule a stop after the
others, `why` `strong`; `go on` (or an empty line) leaves them in the list.

**Each stop, in order:** every hand check, then every weak rule, then every rule not audited, then
the strong rules walked; within each, by feature name then rule number. A rule with a `@manual`
proof and a weak audit stops once, as a hand check.

```
sample_age RULE-1   weak
Rule
  The age at receipt is the time from collection to receipt, across time zones
Proof
  PROOF-1: A sample received at 10:30 UTC-5, collected at 14:00 UTC, has an age of `90` minutes
    tied to tests/test_age.py::test_age_at_receipt
      def test_age_at_receipt():
          assert age_minutes('14:00Z', '10:30-05:00') == 90
Results
  Linux/Unix: passed on quinn-laptop
  Windows: passed on remote runner, Windows
What the audit found
  Weak.
  The test checks one time zone; PROOF-1 names two.
sample_age RULE-1   continue / note / stop: 
```

- The head is `<feature> <RULE-N>   <why>`. `Rule`, `Proof` with decision 102's `TIED_TO` and
  `TIED_TO_NONE` lines, then each tied test's body from `marked_tests.source`, indented six spaces,
  or `      the test's source was not found`; `Results`, one `RESULT = '  %s: %s on %s'` line per
  system (the system's words, the passed cell's word there, the machine); `What the audit found`,
  today's `audit_lines`.
- A hand check shows `Rule` and `Proof` alone and asks
  `HAND_ASK = '%s %s   what did you see, in one line, or stop: '`. The line typed is the note
  (`kind` `hand check`); an empty line asks again; `stop` stops.
- Any other stop asks `STOP_ASK = '%s %s   continue / note / stop: '`. `note` asks
  `NOTE_ASK = 'Your note, in one line: '` (`kind` `note`), then moves on.
- `stop`: `STOPPED = 'Stopped at %s %s: nothing was signed. After the fix, run purlin:test --release, then purlin:sign.'`
  and exit 0.

**The signature.** After the last stop:

```python
SIGN_ASK = 'Sign the evidence package for %s as %s? [y/N] '
NOT_SIGNED = 'Nothing was signed.'
SIGNED_AS = 'Signed %s as %s with the key ending ...%s.'
TAG_STAYS = '%s stays at %s; this sign-off is added after it. Push it: git push'
SIGNOFFS = 'Sign-offs of %s: %s.'          # emails, oldest first, joined ', '
NOT_MADE = 'The sign-off commit was not made: %s. Nothing was signed; run purlin:sign again.'
```

On yes it writes the file, makes one signed commit, and prints `SIGNED_AS`; then, for the first
sign-off of that version, `release.write_tag(..., signed=True)` on that commit, `TAGGED` and
`summary.RELEASE` filled (or `NO_TAG_GIT` and exit 1); for a later one, `TAG_STAYS`. Last,
`SIGNOFFS`.

```
Sign the evidence package for 1.2.0 as quinn.qa@labconnect.example? [y/N] y
Signed 1.2.0 as quinn.qa@labconnect.example with the key ending ...4f2a.
Tagged signed/1.2.0 at 8de0b6e.
Nothing left to do. Push the tag to release it: git push origin signed/1.2.0
Sign-offs of 1.2.0: quinn.qa@labconnect.example.
```

```
signed/1.2.0 stays at 8de0b6e; this sign-off is added after it. Push it: git push
Sign-offs of 1.2.0: quinn.qa@labconnect.example, pat.product@labconnect.example.
```

Exit codes: 0 signed, stopped, answered no, or the gate is `passed`; 1 a refusal, no key, the
commit not made, git could not write the tag, or the settings file cannot be read; 2 the command
line was wrong.

### C9. The walk through the agent, lane `signoff`

`sign.py --show` prints C8's refusal or overview, then every stop as rendered with no question,
the strong list in full under `STRONG_LIST`, and last
`SHOW_NEXT = 'Answer each stop, then run purlin:sign --answers <file>.'`. It writes nothing.

`--answers FILE` reads:

```json
{"strong": "go on",
 "stops": {"accession_screen RULE-1": {"answer": "note", "note": "the tube is red"},
           "sample_age RULE-1": {"answer": "continue"}},
 "sign": true}
```

`strong` is `list`, `walk` or `go on` (`list` records `list_opened` true and walks none); each stop
key is `<feature> <RULE-N>`; `answer` is `continue`, `note` or `stop`; a hand check takes `note`
with a line, or `stop`. The walk then runs as C8 with these answers, printing the same lines.
Refusals, nothing written, exit 1:

```python
ANSWERS_MISSING = ('No sign-off: %s has no answer in %s. Answer every stop, then run '
                   'purlin:sign --answers %s again.')
ANSWERS_UNREAD = 'No sign-off: %s cannot be read: %s.'
```

The skill writes the file to `.purlin/runtime/signoff-answers.json`; `.purlin/runtime/` is already in the ignore list setup writes.

### C10. The renumbering helper, lane `drift`

`scripts/spec/renumber.py <feature> [--dry-run] [--project-root DIR]`, run as
`sh scripts/purlin_python.sh scripts/spec/renumber.py`. It reads this checkout only and never
fetches, like drift, and commits nothing. It plans, and without `--dry-run` makes, these edits in
the feature's spec and in the test files of this checkout:

1. **A number written twice.** The line that moves is drift's (decision 102's C7): the line whose
   text is not on the default branch's copy; where neither is, or there is no default branch, the
   later line in the file. It takes the next free number of its kind. A rule that moves takes
   with it every proof line that names it and is not on the default branch's copy.
2. **A test comment that names the moved id**, where `git blame` says the comment was written when
   that id's text was the moving line's text. A comment not yet committed is named, not changed.
3. **A test comment whose proof's wording changed**, where the old wording is now another id of
   the same spec (drift's second comment form): the comment moves to that id.
4. `> Highest-Rule:` / `> Highest-Proof:` raised to the new number.
5. **Comments on other branches** (every `refs/heads/*` but the current one, and every
   `refs/remotes/*` but `HEAD` and the default branch, as last fetched) that name the moved id are
   named, never touched.

The plan lines, in that order:

```python
MOVES = '%s: %s at line %d becomes %s: "%s".'
MOVES_NEITHER = '%s: %s at line %d becomes %s: "%s". Neither line is on %s, so the later one moves.'
MOVES_NO_DEFAULT = ('%s: %s at line %d becomes %s: "%s". This checkout has no copy of a '
                    'default branch, so the later one moves.')
PROOF_FOLLOWS = '%s: %s at line %d now names %s.'
COMMENT_MOVES = '%s:%d names %s %s and moves to %s.'
COMMENT_FOLLOWS = '%s:%d names %s %s and moves to %s, where its old wording is now.'
COMMENT_UNCOMMITTED = ('%s:%d names %s %s and is not committed, so it is not changed: check '
                       'which proof it means.')
HIGHEST = '%s: > Highest-%s: %d becomes %d.'
OTHER_BRANCH = ('%s names %s %s at %s:%d, which this checkout does not change. If it means the '
                'line that moves, move it to %s on that branch.')
DRY_RUN = 'Nothing is changed: this is a dry run.'
DONE = 'Renumbered in %s: %s and %s. Nothing is committed.'   # '1 spec line', '2 test comments'
NOTHING = '%s: nothing to renumber.'
```

```
sample_age: PROOF-4 at line 14 becomes PROOF-7: "A sample collected before the spring-forward change has an age of `60` minutes".
tests/test_age.py:22 names sample_age PROOF-4 and moves to PROOF-7.
sample_age: > Highest-Proof: 6 becomes 7.
origin/qa/age-proofs names sample_age PROOF-4 at tests/test_age.py:18, which this checkout does not change. If it means the line that moves, move it to PROOF-7 on that branch.
Nothing is changed: this is a dry run.
```

**The question.** The agent runs the dry run, shows its lines, and asks exactly `Do it? [y/N]`.
On yes it runs the script without `--dry-run`; on anything else nothing is renumbered. Wherever
drift, the status, `purlin:spec` or `purlin:build` finds a number written twice or a test
comment whose proof's wording changed, the agent does this; the steps live in
`skills/spec/SKILL.md` under `Renumbering`, and the status, drift and build skills point there in
one line. Exit codes: 0 planned or done, or nothing to renumber; 1 the feature is no spec; 2 the
command line was wrong.

### C11. What stays from decision 102, unchanged in words

Each of these prints as it does at `1948eb7e8`; no lane changes its text:
`sample_age: RULE-4 is written twice; the second is read. Run purlin:spec sample_age.`, its proof
twin, the two conflict lines (`CONFLICT_ONE`, `CONFLICT_MANY`); the failed cells' reasons
`PROOF-4 is written twice in the spec`, `RULE-4 is written twice in the spec`,
`the spec holds a line left from a merge conflict`; `1 spec to repair: purlin:spec`; drift's four
number-written-twice forms, its two age lines, its two test-comment forms and its three proof
lines (added, changed, moved); the walk's `    tied to <file>::<test>` and `    tied to no test`;
the verified-commit reason `the signature on the commit that added it does not verify`; and the
spec-format collision sentence's first half. The refusal of a tag when the branch's copy on the
host moved past the commit keeps its check and its first half, and is now the release run's
`NO_RELEASE_BEHIND` and the walk's `NO_SIGNOFF_BEHIND` (C5, C8).

### C12. Deleted outright

- **Signing a rule:** every per-rule signature file shape and reader, `specs/**/*.signatures/`,
  `sign.py`'s `<feature> RULE-N`, `--all`, `--note`, `--does-not-apply`, the answers
  `sign / case / skip` and `confirm / sign / skip`, `NOTHING_WAITING`, `NOT_A_RULE`,
  `SPEC_REFUSED`, `NO_FILES`, `NEEDS_A_REASON`, `NAMES_AN_ANCHOR`, `NOT_PINNED`, `CONFIRM`,
  `commit_message`'s `sign(<feature>): RULE-N` and `sign(batch): ...`, `tag_if_met`.
- **Decision 102's ended signature:** `ENDED`, `ENDED_LINE`, every cause, the status block, drift's
  `signatures_ended`, the dashboard's ended reason.
- **The hand-check binding** and signature format 13's lines 1 to 7.
- **Decision 101's signature as not applying:** the cell word `does not apply`, the badge, the
  `Tests` cell's ` · <k> does not apply`, `to_confirm`, `To confirm`, the anchor format's and the
  hard gates' sentences about it, the walk's confirm stop.
- **The gate `strong`** and `min_strength`, with the minimum in the audit's prompt and printout,
  the strong cell's `strength <p>% under <m>%`, `no minimum applies: mutation testing is off`
  (decision 99), setup's minimum by gate.
- **Kinds:** `to_test_by_hand`, `to_confirm`, `to_audit`, `to_measure`, `no_scope`, `to_sign`,
  `to_tag`, and their dashboard buttons.
- **The signed cell** and `waiting for the audit`, `NAMES_NO_FILES`, the summary's `are strong.` and
  `are signed.` clauses.
- **The audit's exit 1** at `strong` and `signed` for a weak or unaudited rule: `purlin:audit`
  exits 0 on what it found.

### C13. The lines a surface still prints about a hand check

- The dashboard, a `@manual` proof: `Checked by hand when a release is signed, in the walk of purlin:sign.`
  in place of decision 99's `Checked by hand. Type purlin:sign <feature> RULE-N in Claude Code.`
- The release run at `passed`, where any rule has a `@manual` proof (under Q1's recommended
  answer, section 8):
  `2 rules are checked by hand, and the gate passed records no hand check: accession_screen RULE-1, sample_age RULE-6. The package lists them as not checked.`
  (`1 rule is checked by hand`), printed before `PACKAGE_COMMITTED`. The package's `hand_checks`
  entries then carry `"checked": false` at `passed` and `"checked": "in the sign-offs"` at
  `signed`.

### C14. Format and schema numbers

| File | Now | After | Why |
|---|---|---|---|
| `references/formats/signature_format.md` | 13 | 14 | the per-rule signature is replaced by the sign-off file of C6 |
| `references/formats/package_format.md` | 6 | 7 | `min_strength` and each rule's `signatures` removed; `audit` and `hand_checks` added; `tag` names either gate's tag; the kinds of C3; sign-offs sit beside the package |
| `references/formats/evidence_format.md` | 7 | 7 | wording only: Purlin's own records are `.purlin/evidence/` (the package and its sign-offs among them) and `.purlin/tests.md` |
| `references/formats/spec_format.md` | 21 | 21 | wording only: the collision sentence's second half |
| `references/formats/anchor_format.md` | 11 | 11 | wording only: an anchor's rule is signed as part of the release; the not-applying sentences go |
| `references/formats/marker_format.md` | 3 | 3 | unchanged |
| payload `schema_version` | 12 | 13 | C4 |
| `references/drift_criteria.md` Criteria-Version | 11 | 12 | the `qa` view loses the ended signatures and the lines waiting for a person |

`specs/review/signatures.md` names `signature format 14`; `specs/export/package.md` names
`package format 7`.

### C15. The upgrade, lane `settings`

The `config` migration of `scripts/init/update.py`:

- a `gate` of `strong` becomes `passed`, `mutation_engine` stays as written, and the migration
  prints `The gate strong is now passed; the audit stays a tool you run with purlin:audit.`;
- `min_strength` is taken out, printing `removed from .purlin/config.json: min_strength`;
- a 0.9.5 project whose hook setting was the blocking one (`pre_push: strict`) is offered
  `passed`, and the mutation question is asked as it is at `signed`, where an engine runs.

`MUTATION_GATES` becomes `('signed',)`. Nothing else in the upgrade changes; no 0.9.5 project
holds a per-rule signature, so none is migrated.

### C16. Setup, lane `settings`

```python
GATE_CHOICES = (
    "passed  every rule's tests pass",
    "signed  every rule's tests pass, and a person signs each release",
)
NOT_A_GATE = '%s is not accepted for gate; it takes passed or signed. Reading it as %s.'
NOT_A_GATE_FLAG = '%s is not accepted for gate; it takes passed or signed. Nothing was written.'
```

The mutation question is asked at `signed` alone, and a yes writes `mutation_engine: auto` and no
minimum. `--mutation` turns it on at either gate. `min_strength_for` is deleted.

## 3. What decision 103 asks, to lanes

| Decision 103 says | Built in | Lane |
|---|---|---|
| Nothing is signed or recorded while specs are iterated; `Left to do` lists only work | C2, C3, C4, C12 | counting, dashboard, drift |
| The gate is two answers; `strong` goes | C1, C15, C16 | settings |
| The audit and mutation testing are optional tools; the settings that made them block lose their force | C1, C2, C12 | settings, counting, run |
| A release is a commit, a package and a tag; `passed/<version>` unsigned; `signed/<version>` at the first signature | C5, C7, C8 | release, signoff, run |
| One signature over the package's hash; several may sign | C6 | signoff |
| The sign-off walk | C8, C9 | signoff, skills words in `skills/sign/SKILL.md` |
| The package records what the signer was shown and every note | C6 | signoff |
| The warnings stay; a renumbering helper asks | C10, C11 | drift, skills |

## 4. The lanes

Every file that changes has exactly one owner. Ownership follows `d102-plan.md` section 4 where it
fits.

| Lane | Owns |
|---|---|
| L1 `settings` | `scripts/mcp/purlin/gate.py`; `scripts/mcp/purlin/server.py`; `scripts/init/{scaffold,update}.py`; `templates/config.json`; `.purlin/config.json`; `specs/mcp/{config_engine,server,specs}.md`; `specs/init/{scaffold,update}.md`; `dev/test_{config_engine,mcp_server,specs_reader,init_scaffold,init_update}.py`; `dev/fixtures/upgrade-0.9.5/**`; `dev/fixtures/consumer-ci/.purlin/config.json`; `skills/init/SKILL.md`; `specs/skills/skill_init.md`; `dev/test_skill_init.py` |
| L2 `counting` | `scripts/mcp/purlin/{states,payload,summary,status,board}.py`; `specs/mcp/{states,summary}.md`; `dev/test_{states,summary,backing_tests,failing,purlin_output}.py`; `specs/instructions/purlin_output.md`; `skills/status/SKILL.md`; `specs/skills/skill_status.md`; `dev/test_skill_status.py` |
| L3 `drift` | `scripts/mcp/purlin/drift.py`; `specs/mcp/drift.md`; `dev/test_drift.py`; `references/drift_criteria.md`; `skills/drift/SKILL.md`; `specs/skills/skill_drift.md`; `dev/test_skill_drift.py`; new `scripts/spec/renumber.py`, `specs/spec/renumber.md`, `dev/test_renumber.py` |
| L4 `release` | new `scripts/export/release.py`, `specs/export/release.md`; `scripts/export/package.py`; `specs/export/package.md`; `dev/test_export.py`; `dev/test_tag.py`; `references/formats/package_format.md`; `skills/export/SKILL.md`; `specs/skills/skill_export.md`; `dev/test_skill_export.py`; `scripts/mcp/purlin/fingerprint.py`; `specs/mcp/evidence.md`; `dev/test_fingerprint.py`; `references/formats/evidence_format.md` |
| L5 `signoff` | `scripts/review/sign.py`; `scripts/mcp/purlin/signatures.py`; `specs/review/signatures.md`; `dev/test_signatures.py`; `references/formats/signature_format.md`; `skills/sign/SKILL.md`; `specs/skills/skill_sign.md`; `dev/test_skill_sign.py` |
| L6 `run` | `scripts/run/purlin_run.py`; `scripts/review/ai_audit.py`; `scripts/run/host.py`; `scripts/run/mutation/**`; `specs/run/{run_script,host,mutation,evidence_writer,reports}.md`; `specs/review/ai_audit.md`; `dev/test_{run_script,ai_audit,ai_audit_tests_named,host,mutation_adapters,evidence_writer,consumer_ci}.py`; `references/review_criteria.md`; `skills/{test,audit}/SKILL.md`; `specs/skills/{skill_test,skill_audit}.md`; `dev/test_skill_{test,audit}.py` |
| L7 `dashboard` | `scripts/report/src/**`; `scripts/mcp/purlin/report_data.py`; `dev/build_report.py`; `dev/capture_doc_screenshots.py`; `specs/dashboard/purlin_report.md`; `dev/test_purlin_report.py`; `dev/test_purlin_report_board_layout.py`; `dev/test_report_refresh.py`; `dev/fixtures/report/*.json`; `docs/dashboard.md` |
| L8 `skills` | `skills/{spec,build,anchor,spec-from-code}/SKILL.md`; `specs/skills/{skill_spec,skill_build,skill_anchor,skill_spec_from_code}.md`; `dev/test_skill_{spec,build,anchor,spec_from_code}.py`; `references/spec_quality_guide.md`; `references/formats/{spec_format,anchor_format}.md`; `specs/mcp/schema_spec_format.md`; `dev/test_schema_spec_format.py`; `specs/anchor/upstream.md` and `specs/_anchors/security_no_dangerous_patterns.md` (only a line that names per-rule signing) |
| L9 `words` | `references/{glossary,purlin_commands,hard_gates,commit_conventions}.md`; `agents/purlin.md`; `specs/instructions/purlin_agent.md`; `dev/test_purlin_agent.py`; `README.md`; `RELEASE_NOTES.md`; `CLAUDE.md` (the releasing steps and the two reference-table rows alone); `specs/instructions/purlin_version.md` (only a line naming per-rule signing) |
| L10 `docs` | `docs/{index,getting-started,how-purlin-works,raising-the-gate-and-upgrading,regulated-workflow,review-and-signing,running-and-evidence,spec-from-code,specs-and-anchors,team-workflow,working-together,qa-guide}.md`; `specs/instructions/purlin_docs.md`; `dev/test_purlin_docs.py`; `dev/plans/deck/build_deck.py`; `dev/plans/deck/check_deck.py` |

No lane: the spec reader (`scripts/mcp/purlin/specs.py`), the markers module, the evidence reader
(`scripts/mcp/purlin/evidence.py`), the evidence writer (`scripts/run/evidence.py`),
`scripts/review/marked_tests.py`, `scripts/run/{ci,remote,reports,workflow}.py`, the anchor tools,
`templates/purlin.yml` and the Azure file (the tag run stays on `signed/*` alone; section 9), and
`dev/test_vocabulary.py`. A failure the sweep finds there is integration's.

### L1 `settings`

Builds C1, C15, C16 and the settings tool. `templates/config.json` loses `min_strength`. This
repository's `.purlin/config.json` keeps `gate: signed`, `mutation_engine: auto` and every other
key, and loses `min_strength`. The consumer-ci fixture (`gate: strong`, `min_strength: 70`) becomes
`gate: passed` with no `min_strength`. The init skill's gate table and its question read C16's two
choices and say the audit is a tool at either gate, within 250 lines.

Next free ids and the work:
- `specs/mcp/config_engine.md` (R15 P40; next RULE-16, PROOF-41): every rule naming `strong` or
  `min_strength` is reworded to C1 or deleted. RULE-16: a gate of `strong` reads as `passed` with
  `STRONG_RETIRED` (PROOF-41). RULE-17: the breaks are on wherever `mutation_engine` is not
  `none`, at either gate (PROOF-42 at `passed`, PROOF-43 at `signed`). RULE-18: a `min_strength`
  key is named in the retired-keys warning (PROOF-44).
- `specs/mcp/server.md` (R31 P162; next RULE-32, PROOF-163): the gate rule says `passed or
  signed`; the `min_strength` rule is deleted. RULE-32: writing a retired key answers
  `RETIRED_NOT_WRITTEN` and changes nothing (PROOF-163, `min_strength`).
- `specs/mcp/specs.md` (R21 P43): a proof naming `strong` or `min_strength` through
  `dev/test_specs_reader.py` is reworded to C1; no new rule unless one is needed, then RULE-22,
  PROOF-44.
- `specs/init/scaffold.md` (R75 P166; next RULE-76, PROOF-167): rules about the three choices, the
  minimum written by gate and the mutation question at `strong` are reworded or deleted. RULE-76:
  setup offers two gates, in C16's words (PROOF-167). RULE-77: the mutation question is asked at
  `signed` alone (PROOF-168 at `passed`, not asked; PROOF-169 at `signed`, asked). RULE-78: no
  `min_strength` is written (PROOF-170).
- `specs/init/update.md` (R46 P158; next RULE-47, PROOF-159): RULE-47, a `gate` of `strong` becomes
  `passed` with C15's line, `mutation_engine` kept (PROOF-159). RULE-48, `min_strength` is taken
  out with its line (PROOF-160). RULE-49, a 0.9.5 `pre_push: strict` is offered `passed`
  (PROOF-161). The rule offering `strong` is reworded to RULE-49's words or deleted.
- `specs/skills/skill_init.md` (R85 P96; next RULE-86, PROOF-97): proofs quoting the three choices
  or a minimum are reworded to C16.

Break on purpose: leave `'strong'` in `GATES`; PROOF-41's test fails.

Tests that may fail only because another lane has not merged: the end-to-end tests of
`dev/test_init_scaffold.py` and `dev/test_init_update.py` that read the closing `Left to do` or the
summary sentence (C3, lane `counting`).

### L2 `counting`

Builds C2, C3, C4, and deletes C12's parts in its files. `status.py` loses the ended block and the
` · <k> does not apply` count; `board.py`'s row loses `Signed`; the `Strong` column shows, at both
gates, where `summary.audit` has any strong or weak rule, and reads `<s> of <n>` as now. The status
skill's closing table loses every row of a deleted kind, gains `TO_RELEASE` and
`TO_RELEASE_SIGNED` with `→ Run: purlin:test --release` (and `, then purlin:sign`), and points a
number written twice at `purlin:spec`'s `Renumbering` in one line, all within 100.

- `specs/mcp/states.md` (R105 P259; next RULE-106, PROOF-260): delete every rule about the signed
  cell, a signature's binding, an ended signature and its causes, a rule that does not apply,
  `to_confirm`, `hand_checked`, the minimum strength and the gate `strong`, with their proofs and
  tests. Reword the rules of the strong cell to C2. New: RULE-106, both cells exist at both gates
  (PROOF-260 at `passed`, PROOF-261 at `signed`). RULE-107, a weak audit does not stop the passed
  cell or any gate (PROOF-262). RULE-108, a measured strength is a reason of the strong cell and no
  minimum is read (PROOF-263: `strength 55%` with verdict `strong` reads `strong`). RULE-109, a rule
  whose every proof is `@manual` reads `passed` and `manual test` (PROOF-264).
- `specs/mcp/summary.md` (R16 P41; next RULE-17, PROOF-42): delete the rules and proofs of the
  deleted kinds and of `are strong.` / `are signed.`. RULE-17: the sentence adds `AUDIT_FOUND`
  only where a rule was audited (PROOF-42 none audited, PROOF-43 two audited). RULE-18: the last
  line names the release step, by gate (PROOF-44 `passed`, PROOF-45 `signed`, PROOF-46 a
  `passed/*` tag on HEAD). RULE-19: a weak rule is `to_strengthen` and is not in `BLOCKING`
  (PROOF-47).
- `specs/instructions/purlin_output.md` (R3 P6): changes only where a proof quotes a deleted line.
- `specs/skills/skill_status.md` (R11 P35; next RULE-12, PROOF-36): RULE-12, the skill sends a
  number written twice to `purlin:spec`'s renumbering (PROOF-36).

Break on purpose: count a weak rule in `BLOCKING`; PROOF-47's test fails.

Tests that may fail only because another lane has not merged: any end-to-end test here whose
project sets `gate: strong` or `min_strength` reads the old gate until lane `settings` merges
(section 6); none should, once this lane rewrites them to C1.

### L3 `drift`

Keeps decision 102's lines (C11). Deletes the `qa` view's ended lines, its lines for a person
(`FOR_A_PERSON`), and the JSON key `signatures_ended`; the `qa` view ends on the proofs lines, the
test files line and `Left to do`'s blocking lines. `references/drift_criteria.md` goes to
Criteria-Version 12. Builds C10 on drift's own reading of the default branch, the moving line and
the blamed comments, calling it rather than restating it. The drift skill points a number written
twice and a changed comment at `purlin:spec`'s `Renumbering` in one line each, within 150.

- `specs/mcp/drift.md` (R34 P80; next RULE-35, PROOF-81): delete RULE-34 and PROOF-78 (the ended
  line) and any proof of the `qa` view's person lines. No new drift rule is needed.
- `specs/skills/skill_drift.md` (R12 P38; next RULE-13, PROOF-39): RULE-13, the skill sends a number
  written twice to the renumbering in `purlin:spec` (PROOF-39).
- `specs/spec/renumber.md`, new, `> Highest-Rule: 9`, `> Highest-Proof: 12` when done, with
  `> Scope: scripts/spec/renumber.py`: RULE-1 a dry run changes nothing and ends on `DRY_RUN`
  (PROOF-1); RULE-2 the line not on the default branch moves to the next free number (PROOF-2);
  RULE-3 neither line on the default branch moves the later (PROOF-3), and no default branch the
  same (PROOF-4); RULE-4 a comment written for the moving text moves with it (PROOF-5), one
  written for the kept text does not (PROOF-6); RULE-5 an uncommitted comment is named, not
  changed (PROOF-7); RULE-6 a comment whose old wording is now another id moves there (PROOF-8);
  RULE-7 the Highest line is raised (PROOF-9); RULE-8 a comment on another branch is named and
  that branch is untouched (PROOF-10); RULE-9 a rule that moves takes its proof lines not on the
  default branch (PROOF-11) and a run without `--dry-run` ends on `DONE` with nothing committed
  (PROOF-12).

Break on purpose: move the default branch's line instead; PROOF-2's test fails.

Tests that may fail only because another lane has not merged: the `qa` view tests that read
`Left to do` (C3, lane `counting`).

### L4 `release`

Builds C5 (in `release.py`), C7, package format 7, and the export skill's words (the package at
any time, its `state`, the release run as the way a version is released), within 90. Moves
`project_version`, `tag_name`, `tag_exists`, `behind_host`, `uncommitted_work` and the tag's
message out of `sign.py` into `release.py` (lane `signoff` deletes them there). `fingerprint.py`'s
`RECORDS` loses `':(exclude,glob)specs/**/*.signatures/**'`; evidence format 7 says what the
records are.

- `specs/export/release.md`, new, `> Scope: scripts/export/release.py`, ids from 1: RULE-1 the
  release run refuses a failing rule with `NO_RELEASE_FAILING` (PROOF-1) and a broken spec with
  `NO_RELEASE_SPEC` (PROOF-2); RULE-2 it refuses uncommitted work (PROOF-3); RULE-3 it refuses
  while the branch's copy on the host holds commits HEAD lacks (PROOF-4) and not for an unpushed
  commit of its own (PROOF-5); RULE-4 the version is read as the tag reads it (PROOF-6 `VERSION`,
  PROOF-7 `--release 2.0.0`) and none gives `NO_VERSION` (PROOF-8); RULE-5 at `passed` it commits
  the package and writes an unsigned `passed/<version>` on that commit (PROOF-9); RULE-6 at
  `signed` it commits the package and writes no tag, ending on `READY_TO_SIGN` (PROOF-10); RULE-7
  an existing tag of the gate refuses (PROOF-11); RULE-8 a weak or unaudited rule does not refuse
  (PROOF-12); RULE-9 a package for the same version with no tag yet is written again (PROOF-13);
  RULE-10 at `passed`, a hand check prints C13's line and the package lists it not checked
  (PROOF-14); RULE-11 git's refusal of the tag prints `NO_TAG_GIT` (PROOF-15); RULE-12 nothing is
  fetched or pushed (PROOF-16).
- `specs/export/package.md` (R28 P60; next RULE-29, PROOF-61): delete the rules about a rule's
  signatures, the signed status, `min_strength` and the kinds C3 deletes, with their proofs.
  RULE-29: the package carries `audit` and `hand_checks` (PROOF-61, PROOF-62). RULE-30: `state`
  is `finished` with only weak rules left (PROOF-63). RULE-31: `tag` names `passed/<version>` at
  `passed` (PROOF-64). Package format number: `package format 7`.
- `specs/mcp/evidence.md` (R33 P85): the rule and proof naming a signature file as a record are
  reworded to a sign-off file under `.purlin/evidence/package/`; next RULE-34, PROOF-86 if one is
  needed.
- `specs/skills/skill_export.md` (R13 P35; next RULE-14, PROOF-36): proofs quoting per-rule
  signatures or `to_tag` are reworded; RULE-14, the skill names `purlin:test --release` as how a
  version is released (PROOF-36).

`dev/test_tag.py` keeps the tests of what moved (version, host copy, git's refusal) pointed at
the release run, and deletes the rest.

Break on purpose: count `to_strengthen` in `BLOCKING` inside `run_release`; PROOF-12's test
fails.

Tests that may fail only because another lane has not merged: every release test that reads the
payload's `left`, `summary.BLOCKING` or schema 13 (lane `counting`); the tag at `signed` written by
a sign-off (lane `signoff`) is not tested here.

### L5 `signoff`

Builds C6, C8, C9, signature format 14 (C6's file, field by field; when a sign-off counts; the
tag at the first; nothing about rules, hashes, hand-check binding or ending). Rewrites `sign.py`
around the walk and deletes C12's parts. `signatures.py` keeps and deletes as C6 says. The sign
skill is rewritten to C8 and C9 within 185: Usage (`purlin:sign`, `purlin:sign --release
<version>`), what the gate decides (nothing at `passed`), the key, `--show`, the stops and their
answers, writing the answers file, the refusals, the tag at the first, the closing table.

- `specs/review/signatures.md` (R101 P201; next RULE-102, PROOF-202): kept and reworded to a
  sign-off: RULE-17 (no key), RULE-20 and RULE-97 (a sign-off counts when its commit's signature
  verifies), RULE-21 (anyone with a key), RULE-22 (`--help`), RULE-50 (signer, name, key
  fingerprint), RULE-60 (the key fingerprint), RULE-67 (settings unreadable), RULE-77 (unknown
  option), RULE-79 (commit not made, `NOT_MADE`), RULE-81 (`--project-root`), RULE-83 (proof tags
  at a stop), RULE-84 (`What the audit found`), RULE-89 (the tag's SSH signature), RULE-101 (tied
  tests). Deleted, with their proofs and tests: every other rule. The tag rules that moved to
  `specs/export/release.md` are deleted here. New: RULE-102 the refusals in C8's order, one proof
  per refusal (PROOF-202 to PROOF-208: at `passed`, uncommitted work, no package, the package
  describes another commit, a failing rule, behind the host, already signed). RULE-103 the
  overview (PROOF-209). RULE-104 the stops' order and what each shows (PROOF-210 a weak stop shows
  the test body and results; PROOF-211 a hand check asks `HAND_ASK`). RULE-105 the strong list
  (PROOF-212 `list`, PROOF-213 `walk`). RULE-106 the file records what was shown and every note
  and no answer word (PROOF-214). RULE-107 the first sign-off writes `signed/<version>` on its
  commit (PROOF-215); a later one adds a file and leaves the tag (PROOF-216). RULE-108 a sign-off
  counts only over the committed package's fingerprint (PROOF-217). RULE-109 `stop` and a `no`
  write nothing (PROOF-218, PROOF-219). RULE-110 `--show` asks nothing and writes nothing
  (PROOF-220). RULE-111 `--answers` walks with the file's answers (PROOF-221) and names a missing
  answer (PROOF-222).
- `specs/skills/skill_sign.md` (R28 P58; next RULE-29, PROOF-59): delete every rule about signing a
  rule, `--note`, `--all`, `--does-not-apply`, the confirm stop and the ended signature. Keep and
  reword the key and tied-test rules. New from RULE-29: the skill runs `--show` first, asks the
  person each stop, writes the answers file, and runs `--answers` (PROOF-59, PROOF-60); it names
  the refusal at `passed` (PROOF-61); it names the tag at the first sign-off (PROOF-62).

Break on purpose: write the sign-off with `package_hash` taken after the file is added; PROOF-217's
test fails.

Tests that may fail only because another lane has not merged: every walk test, since the walk
reads a committed package (lane `release`, `release.package_at_head`) and the payload's schema 13
(lane `counting`). The lane writes its test projects' package with its own helper in
`dev/test_signatures.py`, to C7's shape, so the rest of its tests run before `release` merges.

### L6 `run`

- `purlin_run.py`: `--release [<version>]` (C5), which implies `--test --all --commit` and calls
  `release.run_release`; the breaks run under `--audit` wherever `cfg.breaks` (C1); the audit exits
  0 on weak and unaudited rules at every gate; the usage lines gain
  `purlin:test --release [<version>]  Run every test, commit the evidence and the package, and tag the release at the gate passed`.
- `ai_audit.py`: `STRENGTH_LINE = 'Test strength %d%%.'`; `min_strength` goes from the reading, the
  prompt and the printout.
- `host.py`: the gate `strong` in any branch it reads goes; the tag run stays on `signed/*`.
- `references/review_criteria.md`: the minimum goes; a weak finding does not stop a release.
- The test and audit skills: the gate tables lose `strong`; the audit skill says the audit and
  the breaks are tools at either gate and nothing waits on them; the test skill names
  `purlin:test --release` in its usage and closing table. Within 120 and 105.

Next free ids:
- `specs/run/run_script.md` (R89 P264; next RULE-90, PROOF-265): rules naming `strong` or a minimum
  are reworded or deleted. RULE-90: `--release` runs every test, commits the evidence and hands on
  to the release (PROOF-265: `--release` at `passed` in a passing project ends on
  `Tagged passed/<version> at <sha7>.`). RULE-91: `--release` exits 1 when the release is refused
  (PROOF-266). RULE-92: the audit exits 0 when a rule reads weak (PROOF-267). RULE-93: the breaks
  run at `passed` where `mutation_engine` is set (PROOF-268).
- `specs/review/ai_audit.md` (R30 P92; next RULE-31, PROOF-93): the minimum's rules are deleted;
  RULE-31, the prompt names the strength with no minimum (PROOF-93).
- `specs/run/{host,mutation,evidence_writer,reports}.md`: a proof whose project sets `gate: strong`
  is rewritten at `passed` with `mutation_engine` set, same number; next free ids R46 P140, R38
  P101, R27 P90, R32 P115 if a new one is needed.
- `specs/skills/skill_test.md` (R20 P49; next RULE-21, PROOF-50): RULE-21, the skill names the
  release run (PROOF-50). `specs/skills/skill_audit.md` (R24 P51; next RULE-25, PROOF-52): RULE-25,
  the skill says nothing waits on the audit (PROOF-52).

Break on purpose: let `--release` skip `run_release`; PROOF-265's test fails.

Tests that may fail only because another lane has not merged: PROOF-265 and PROOF-266
(`release.run_release`, lane `release`); any test reading the payload at schema 13 (lane
`counting`); any test of the gate `strong` until lane `settings` merges.

### L7 `dashboard`

Schema 13 fixtures (C4): the solo sample at `passed` with no audit (no `Strong` column), the team
sample at `passed` with an audit (the `Strong` column, a weak rule under `To strengthen`), the
regulated sample at `signed` with a hand check and a `signed/*` tag on HEAD. Gone: the `Signed`
column, the signed panel on a rule's page, the badges `DOES NOT APPLY`, the ended reason, the
buttons `To test by hand`, `To confirm`, `To audit`, `To measure`, `To sign` and the version to
tag, and `no minimum applies: mutation testing is off`. The strong panel shows the audit's words
at both gates. A `@manual` proof reads C13's line. `docs/dashboard.md` says the same.

- `specs/dashboard/purlin_report.md` (R68 P217; next RULE-69, PROOF-218): delete RULE-67 with
  PROOF-216 and every rule about the signed panel, `does not apply`, and the deleted buttons.
  RULE-69: no `Signed` column at either gate (PROOF-218). RULE-70: the `Strong` column shows only
  where a rule was audited (PROOF-219 team, PROOF-220 solo). RULE-71: a `@manual` proof reads C13's
  line (PROOF-221).

Break on purpose: show the `Strong` column with nothing audited; PROOF-220's test fails.

Tests that may fail only because another lane has not merged: none (the fixtures are fixed JSON).
If the browser cannot start in the cloud (section 5), the lane leaves the browser tests to
integration and says so.

### L8 `skills`

- `skills/spec/SKILL.md`: a section `Renumbering` holding C10's steps (the dry run, the lines
  shown, `Do it? [y/N]`, the run on yes, comments on other branches named). "After a merge
  conflict" keeps decision 102's paragraph but ends its signature clause: `A moved rule needs a new
  audit and a new signature.` becomes `A moved rule's audit is read again.`, and `say which
  signatures that answer ends` goes. The line about a spec naming no files and signatures that do
  not count goes. `from strong up a rule without one reads no proof` becomes `at the gate signed a
  rule without one is left to write a proof for`. `@manual`: a person checks it in the sign-off
  walk and types what they saw.
- `skills/build/SKILL.md`: a found number written twice or changed comment points at
  `Renumbering`; the closing rows lose `strong`, `purlin:audit` as a step, and the `@manual` row's
  `purlin:sign <feature> RULE-<n>`; `Any signature on the rule then ends` goes. Within 130.
- `skills/anchor/SKILL.md`: the not-applying paragraph goes; `counted, audited and signed once`
  becomes `counted and audited once`; `back to to sign` goes.
- `skills/spec-from-code/SKILL.md`: `→ Run: purlin:init --gate strong` becomes
  `→ Run: purlin:audit`; `purlin:sign writes signatures` becomes `purlin:sign signs a release`.
- `references/spec_quality_guide.md`: rows and paragraphs about `unsigned`, an ended signature and
  the minimum go; the collision paragraph ends as the spec skill's does; decision 102's "Where the
  risk is" says `Every rule is asked the same things` (the words `at the gate` go).
- `references/formats/spec_format.md` (21): the collision sentence's second half reads `A moved
  rule's audit is read again; purlin:spec renumbers it and its test comments when you say yes.`
- `references/formats/anchor_format.md` (11): the two not-applying sentences go; `signed once`
  becomes part of the release.

Next free ids: `skill_spec` R28 P58 → RULE-29, PROOF-59: RULE-29 the skill's renumbering shows the
dry run and asks `Do it? [y/N]` (PROOF-59), RULE-30 it names comments on other branches without
touching them (PROOF-60); the proofs of RULE-26 (a new signature) and any quoting a deleted clause
are reworded. `skill_build` R18 P47 → RULE-19, PROOF-48: the skill sends a number written twice to
the renumbering (PROOF-48). `skill_anchor` R16 P38 and `skill_spec_from_code` R51 P165: proofs
quoting a deleted line are reworded; a new one from RULE-17 / PROOF-39 and RULE-52 / PROOF-166.
`schema_spec_format` R37 P85: a proof quoting the collision sentence is reworded.

Break on purpose: drop `Do it? [y/N]` from the spec skill; PROOF-59's test fails.

Tests that may fail only because another lane has not merged: none.

### L9 `words`

- `references/hard_gates.md`: the two gates (C1), the release (C5), which evidence counts (the
  evidence at the release commit, from either source), when a sign-off counts (C6), what
  `passed/<version>` and `signed/<version>` mean, nothing is refused about who signs. The sections
  `The three steps`, `When a signature counts` and the not-applying and hand-check-binding
  sentences go. Its one-home row in `CLAUDE.md` reads `The two gates, the release, which evidence
  counts, when a sign-off counts, what the tags mean`.
- `references/glossary.md`: `gate`, `release`, `sign-off`, `evidence package`, `hand check`,
  `strong` (what the audit found, a tool) as section 7 gives; `signature`, `ended`, `does not
  apply`, `to sign`, `to test by hand`, `to confirm`, `to audit`, `to measure`, `to tag` and the
  step `strong` go.
- `references/purlin_commands.md`: `purlin:test --release [<version>]`, `purlin:sign`,
  `purlin:sign --release <version>`, `purlin:sign --show`, `purlin:sign --answers <file>`, each
  with its one purpose sentence and what it writes; the deleted forms go.
- `references/commit_conventions.md`: `sign(<version>): <signer email>` replaces the two
  `sign(...)` rows; the package row names `purlin:test --release`.
- `agents/purlin.md`: the vocabulary paragraph says two gates and two cells, the loop ends on
  `purlin:test --release` and, at `signed`, `purlin:sign`; the summary example is C3's; rule 2
  ("Never sign on a person's behalf") says a sign-off; within 135.
- `CLAUDE.md` "Releasing a new version": step 3 reads `Run purlin:test --release, then
  purlin:sign at the gate signed. The first sign-off writes the signed tag signed/<version>.`; the
  format table's `signature_format.md` row reads `The sign-off purlin:sign writes over the evidence
  package, read by purlin:sign and purlin:export`.
- `README.md` and `RELEASE_NOTES.md` 0.10.0: section 7's lines; decision 102's entries about ended
  signatures, the hand check's binding and signing refused are replaced, not kept beside.

Next free ids: `purlin_agent` R16 P47 → RULE-17, PROOF-48; proofs quoting the old summary or the
three steps are reworded to C3 (the test's `LEFT_TO_DO` sample becomes
`40 rules. 35 pass their tests. The audit found 30 strong and 2 weak.`). `purlin_version` R16
P38: a line only if one names per-rule signing.

Break on purpose: put ` 30 are strong.` back in the agent's summary example; the agent test that
quotes C3 fails.

Tests that may fail only because another lane has not merged: none.

### L10 `docs`

Every page says what C1 to C13 build, in section 7's words: `docs/review-and-signing.md` becomes
the release and sign-off page (the release run, the walk, its stops and answers, what the package
records, several signers, the tag at the first); `docs/qa-guide.md` keeps its steps from criteria
to proof and ends on the sign-off walk (its sections `The signature` and `What ends a signature`
become `The sign-off` and `What the package records`); `docs/regulated-workflow.md`'s flowchart
ends on `purlin:test --release`, `purlin:sign`, `signed/<version>`; `docs/team-workflow.md`'s
`Releasing a version` names the release run; `docs/raising-the-gate-and-upgrading.md` gives two
gates and the upgrade of C15; `docs/running-and-evidence.md` says evidence may be committed on
any branch and a release uses the evidence at the release commit; `docs/how-purlin-works.md` loses
the signed cell and the ended line; `docs/getting-started.md`, `docs/index.md`,
`docs/spec-from-code.md`, `docs/specs-and-anchors.md` (the collision sentence as the spec format
now reads), `docs/working-together.md` (drift names no ended signature) lose every per-rule
signing line. The deck's builder drops per-rule signing and `strong` from its slide text.

`specs/instructions/purlin_docs.md` (R12 P17; next RULE-13, PROOF-18): proofs quoting a deleted
line are reworded; RULE-13, the release page names both tags (PROOF-18).

Break on purpose: none in code; the lane runs `dev/test_purlin_docs.py` and greps its files for
`strong`, `--note`, `does not apply`, `ended because`, `to sign` and `min_strength` (each empty but
for `strong` as the audit's word).

Tests that may fail only because another lane has not merged: none.

## 5. Linux notes

Each lane runs in a cloud container: Linux, Python 3.11, git 2.43, Node 22 and Go present;
`ssh-keygen` and `sqlite3` only after the `apt-get` of section 1; no dotnet, no macOS, no mutmut
or Stryker unless installed; Chromium at `/opt/pw-browsers`.

| Lane | Needs what the cloud may lack | Left to integration |
|---|---|---|
| `settings` | nothing; the scaffold and update tests use stand-in engines | tests skipped for `platform.system() != 'Windows'` (the Windows mutation line) and any that start dotnet |
| `counting` | `ssh-keygen` for tests that sign commits (`mcp_project.sign_commits`) | nothing, once installed |
| `drift` | nothing (bare repositories on disk) | nothing |
| `release` | `ssh-keygen` for a signed package commit | nothing, once installed |
| `signoff` | `ssh-keygen` with `-Y` (OpenSSH 8.2 or later; 9.6 installs); git ssh signing; `git tag -s` | nothing, once installed |
| `run` | `sqlite3` for two tests of `dev/test_run_script.py`; the dotnet suggestion tests use a stand-in | tests skipped off Windows; `dev/test_mutation_adapters.py` tests that start a real mutmut, Stryker (Node) or Stryker.NET (dotnet 8), which skip where the tool is absent; `dev/test_consumer_ci.py` where it starts dotnet |
| `dashboard` | a browser: `dev/browser_launch.py` tries the bundled Chromium, then `/usr/bin/chromium`; if the pip `playwright` does not match `/opt/pw-browsers/chromium-1194`, pass `executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome'` in the lane's own test run only, never in the committed helper | every browser test, if none starts; `dev/capture_doc_screenshots.py` is not run |
| `skills` | nothing | nothing |
| `words` | nothing | nothing |
| `docs` | nothing; the docs sample runs pytest from the `.venv`; the deck builder needs Node only to render, which the lane does not do | the deck's pictures, if its text changed |

No new proof needs macOS or dotnet 8. The full sweep, the `@env(macos)` proofs and the dashboard
look at five widths run on the Mac.

## 6. Merge order and integration

### Merge order

`settings`, `counting`, `drift`, `release`, `signoff`, `run`, `dashboard`, `skills`, `words`,
`docs`. Each by fast-forward: integration rebases the lane branch on the merged line, reruns its
files and `--fast`, then fast-forwards `d103/base` to it.

Why: every lane reads `gate.GATES` (settings). The payload and `summary.BLOCKING` (counting) are
read by drift, release, signoff, run and the dashboard. `release.py` is called by the walk
(signoff) and by the run's `--release` (run). The dashboard reads only fixed fixtures. The skills,
the words and the docs describe what the others built, so they come last.

Expected red between merges, and only these: the tests each lane's section lists as waiting for
another lane, until that lane merges; from the `settings` merge until `counting` merges, any test
of `dev/test_states.py`, `dev/test_summary.py` or `dev/test_failing.py` that builds a project at
`strong`; from the `counting` merge until `release` and `signoff` merge, `dev/test_export.py`,
`dev/test_tag.py` and `dev/test_signatures.py` tests that read `cells.signed` or a deleted kind;
from the `release` merge until `signoff` merges, `sign.py` importing what moved into `release.py`
(the walk is broken for those two merges); the skill and docs tests that quote a line their lane
has not yet rewritten, until that lane merges.

### The integration agent's job (alone, on the Mac, after every lane merged)

1. Merge in the order above; resolve each failure a lane reported in a file it does not own, to
   the contracts.
2. **Frozen files, integration's own commit** (`chore: the frozen helpers follow decision 103`):
   - `dev/mcp_project.py`: delete `Project.signature` (it reads `signatures.signed_hash`, deleted).
   - `dev/sign_project.py`: delete `REVIEW_GATE`, `Project.signatures` and `Project.load`; the
     comment above the gates reads `The two gates by position: the one a project sits at by
     default, and the one that asks for a sign-off.`; `signing_project`'s docstring reads `A
     project at the gate signed whose two rules pass on a runner and carry an audit reading
     strong, ready for a release.`
   - `dev/run_project.py`: `_project`'s docstring reads `A test that needs the breaks to run sets
     mutation_engine, which is off until named, at either gate.`
   - `dev/skill_checks.py`: `undirected_outcome_problems`' docstring reads `at the gate passed a
     finished project may name no command.` No behaviour changes.
   - `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`: no change.
3. `export PATH=/opt/homebrew/opt/dotnet@8/bin:$PWD/.venv/bin:$PATH`; `bash dev/run_tests.sh`:
   0 failed. Never edit a number to make it pass.
4. `python3 dev/build_report.py`; commit `scripts/report/purlin-report.html` once. Retake the two
   docs screenshots with `dev/capture_doc_screenshots.py` (the board loses its `Signed` column) and
   commit them if they differ. Rebuild the deck's pictures only if lane `docs` changed its text.
5. Look at the dashboard with playwright from the `.venv`, headless, dark and light, at 1500,
   1280, 1024, 768 and 390 pixels, on the three fixtures: no `Signed` column; the `Strong` column
   only on the team sample; the hand-check line on the regulated sample; no value broken inside
   itself; neutral text at least 7 to 1.
6. Greps over `scripts/`, `skills/`, `agents/`, `references/`, `docs/`, `templates/`,
   `README.md`, `CLAUDE.md` and `dev/test_*.py`, each empty outside `RELEASE_NOTES.md`:
   `min_strength`, `does_not_apply`, `does not apply`, `hand_checked`, `to_confirm`,
   `to_test_by_hand`, `ENDED`, `ended because`, `signed_hash`, `--note`, `sign(batch)`,
   `'strong', 'signed'`, `passed, strong or signed`, `schema_version.: 12`, `.signatures/`.
7. `python3 scripts/run/purlin_run.py --test --all`: `Markers: <n> tied to a test, 0 not tied.`,
   no rule `failed`, `partial` or `no test`, no spec to repair, no warning, and the sentence
   `<n> rules. <n> pass their tests.` (with the audit clause only if an audit entry exists). Then
   the same with `--commit`. Do not run `--release` and do not sign: this repository's release is
   the owner's step.
8. Write `dev/plans/d103-interfaces.md`: what was built where it differs from the contracts,
   every word a lane chose that section 7 does not give, the ids, the test counts, and section 7
   copied under "Words chosen for the owner to read".
9. Update `dev/plans/handoff.md`: "Where the tree is", "What is left" (decision 103 built; the
   owner's first `purlin:test --release` and `purlin:sign` on a release branch for 0.10.0; the
   remote run on Windows for any new `@env(windows)` proof, none planned here), and section 7's
   words under "Words for the owner to read".

## 7. Lines a person reads, chosen

In the shape of decisions 94 to 102. The owner reads these and says which to change.

| Where | What it says |
|---|---|
| The gate warning (C1) | `"strong" is no longer a gate: it reads as passed, and the audit stays a tool you run. Run purlin:init --update.`; `"gold" is not accepted for gate in .purlin/config.json; it takes passed or signed. Reading it as passed; set it with purlin:init --gate <gate>.`; `.purlin/config.json still carries min_strength, which this release does not read. Run purlin:init --update.` |
| The settings tool (C1) | `"gold" is not accepted for gate; it takes passed or signed. Nothing was saved.`; `min_strength is not read by this release; nothing was saved.` |
| Setup (C16) | `passed  every rule's tests pass`; `signed  every rule's tests pass, and a person signs each release`; `"gold" is not accepted for gate; it takes passed or signed. Reading it as passed.` |
| The upgrade (C15) | `The gate strong is now passed; the audit stays a tool you run with purlin:audit.`; `removed from .purlin/config.json: min_strength` |
| The sentence (C3) | `40 rules. 35 pass their tests.`; `40 rules. 35 pass their tests. The audit found 30 strong and 2 weak.` |
| The last line (C3) | `Nothing left to do. To release a version: purlin:test --release`; `Nothing left to do. To release a version: purlin:test --release, then purlin:sign`; `Nothing left to do. Push the tag to release it: git push origin passed/1.2.0` |
| The strong cell (C2) | `strength 84%`; `strength not measured: mutmut is not installed: run "pip install mutmut"` as a reason, the word staying the audit's |
| The audit's prompt (C2) | `Test strength 84%.` |
| The release run (C5) | `No release: 2 rules do not pass at 8de0b6e: sample_age RULE-2; stability RULE-1. Run purlin:status to see what is left, then purlin:test --release.`; `No release: sample_age cannot be counted: PROOF-4 is written twice in the spec. Run purlin:spec sample_age, then purlin:test --release.`; `No release: the working tree holds changes that are not committed, so the results do not describe a commit. Commit them, then run purlin:test --release.`; `No release: origin/release/1.2.0 holds 1 commit that 8de0b6e does not, as this checkout last fetched it. Pull, then run purlin:test --release.`; `No version: nothing in this project states one. Run purlin:test --release <version>, or write it to a VERSION file.`; `No release: passed/1.2.0 is already written. Run purlin:test --release <version> to name another.`; `No release: the evidence package was not committed: <why>.`; `Evidence package committed: .purlin/evidence/package/1.2.0.json.`; `Tagged passed/1.2.0 at 3c9d2e1.`; `Run purlin:sign to sign it; the first signature writes signed/1.2.0.`; the usage line `purlin:test --release [<version>]  Run every test, commit the evidence and the package, and tag the release at the gate passed` |
| A hand check at `passed` (C13, under Q1's (a)) | `2 rules are checked by hand, and the gate passed records no hand check: accession_screen RULE-1, sample_age RULE-6. The package lists them as not checked.` |
| The tag's message (C5) | `Released at the gate passed.` / `Released at the gate signed.`, then `Commit: <sha>` and `Gate: <gate>` |
| The walk's refusals (C8) | `Nothing is signed at the gate passed: purlin:test --release tags the release unsigned. To sign releases, run purlin:init --gate signed.`; `No sign-off: the working tree holds changes that are not committed. Commit them, then run purlin:test --release.`; `No sign-off: no evidence package for 1.2.0 is committed at 8de0b6e. Run purlin:test --release.`; `No sign-off: the evidence package for 1.2.0 describes 3c9d2e1, and 8de0b6e has changed since. Run purlin:test --release.`; `No sign-off: 1 rule does not pass at 8de0b6e: sample_age RULE-2. Run purlin:status to see what is left, then purlin:test --release.`; `No sign-off: origin/release/1.2.0 holds 1 commit that 8de0b6e does not, as this checkout last fetched it. Pull, then run purlin:sign.`; `quinn.qa@labconnect.example has already signed 1.2.0 over this package; nothing was written.` |
| The overview (C8) | `Signing 1.2.0: .purlin/evidence/package/1.2.0.json, at 3c9d2e1.`; `  40 rules on Linux/Unix and Windows: 38 pass their tests, 2 are checked by hand.`; `  The audit: 30 strong, 2 weak, 6 not audited.`; `  10 stops: 2 hand checks, 2 weak, 6 not audited.`; `  No stops: nothing is checked by hand, weak or not audited.` |
| The strong list (C8) | `30 rules the audit found strong. list / walk / go on: `; `walk / go on: `; `  sample_age RULE-2, RULE-3` |
| A stop (C8) | the head `sample_age RULE-1   weak` (or `not audited`, `hand check`, `strong`); `Rule`, `Proof`, `    tied to tests/test_age.py::test_age_at_receipt`, the body six spaces in, `      the test's source was not found`; `Results`, `  Windows: passed on remote runner, Windows`; `What the audit found` |
| A stop's answers (C8) | `sample_age RULE-1   continue / note / stop: `; `Your note, in one line: `; `accession_screen RULE-1   what did you see, in one line, or stop: ` |
| Stopping (C8) | `Stopped at sample_age RULE-1: nothing was signed. After the fix, run purlin:test --release, then purlin:sign.` |
| The signature (C8) | `Sign the evidence package for 1.2.0 as quinn.qa@labconnect.example? [y/N] `; `Nothing was signed.`; `Signed 1.2.0 as quinn.qa@labconnect.example with the key ending ...4f2a.`; `Tagged signed/1.2.0 at 8de0b6e.`; `signed/1.2.0 stays at 8de0b6e; this sign-off is added after it. Push it: git push`; `Sign-offs of 1.2.0: quinn.qa@labconnect.example, pat.product@labconnect.example.`; `The sign-off commit was not made: <git's message>. Nothing was signed; run purlin:sign again.` |
| The agent's walk (C9) | `Answer each stop, then run purlin:sign --answers <file>.`; `No sign-off: sample_age RULE-1 has no answer in .purlin/runtime/signoff-answers.json. Answer every stop, then run purlin:sign --answers .purlin/runtime/signoff-answers.json again.`; `No sign-off: <file> cannot be read: <cause>.` |
| The sign-off commit (C6) | `sign(1.2.0): quinn.qa@labconnect.example` |
| The renumbering helper (C10) | `sample_age: PROOF-4 at line 14 becomes PROOF-7: "<text>".`; `... Neither line is on origin/main, so the later one moves.`; `... This checkout has no copy of a default branch, so the later one moves.`; `sample_age: PROOF-6 at line 22 now names RULE-5.`; `tests/test_age.py:22 names sample_age PROOF-4 and moves to PROOF-7.`; `tests/test_age.py:14 names sample_age PROOF-4 and moves to PROOF-6, where its old wording is now.`; `tests/test_age.py:30 names sample_age PROOF-4 and is not committed, so it is not changed: check which proof it means.`; `sample_age: > Highest-Proof: 6 becomes 7.`; `origin/qa/age-proofs names sample_age PROOF-4 at tests/test_age.py:18, which this checkout does not change. If it means the line that moves, move it to PROOF-7 on that branch.`; `Nothing is changed: this is a dry run.`; `Renumbered in sample_age: 1 spec line and 1 test comment. Nothing is committed.`; `sample_age: nothing to renumber.`; the question `Do it? [y/N]` |
| The dashboard (C13) | `Checked by hand when a release is signed, in the walk of purlin:sign.` |
| The spec format and skill, the collision rule (skills) | `When two branches take the same number, the number already on the default branch keeps it, and the rule or proof from the branch not yet merged moves to the next free number. A moved rule's audit is read again; purlin:spec renumbers it and its test comments when you say yes.` |
| The glossary (words) | `**gate**: the one project setting, passed or signed. passed: every rule's tests pass on the evidence committed at the release commit. signed: the same, and at least one person signs the evidence package.`; `**release**: a commit, its evidence package and a tag, made by purlin:test --release on a release branch.`; `**sign-off**: one person's signature over a release's evidence package, a file in a signed commit; the first writes signed/<version>, and later ones are added beside it.`; `**hand check**: a proof marked @manual, which no test runs; at the gate signed a person checks it in the sign-off walk and types what they saw.`; `**strong**: what the AI audit found a rule's tests to be. A tool: nothing waits on it.` |
| `references/hard_gates.md`, lead (words) | `Purlin creates evidence and enforces no policy about who signs. A release is refused only while a rule's tests do not pass at the release commit, a spec cannot be read, the working tree holds uncommitted changes, or the branch's copy on the host holds commits the checkout lacks.` |
| The QA page (docs) | the sections `The sign-off` and `What the package records`; the lead `For a QA person who turns acceptance criteria into proofs and signs the release they cover.` |
| `RELEASE_NOTES.md` 0.10.0 (words) | `**Two gates.** passed: every rule's tests pass at the release commit. signed: the same, and a person signs the evidence package. The gate strong is gone; purlin:init --update reads it as passed.`; `**A release is a commit, a package and a tag.** purlin:test --release runs every test, commits the evidence and the package, and at passed tags passed/<version>. At signed the first purlin:sign writes signed/<version>; later sign-offs are added and the tag does not move.`; `**Nothing is signed while specs change.** Left to do lists only work: proofs and tests to write, tests to fix, rules to strengthen where the audit ran.`; `**The audit and mutation testing are tools.** Nothing waits on them; min_strength is gone.`; `**The sign-off walk shows what to look at.** Each hand check, each weak rule and each rule never audited, with its proofs, its tests' names and bodies, its results and the audit's finding; the rest in a list. The sign-off records what was shown and every note typed.`; `**purlin:spec renumbers a number written twice when you say yes**, with a dry run first.`; the format numbers of C14 |

## 8. Questions for the owner

**Q1. What happens to a hand check at the gate `passed`?**

Root: a hand check is a proof no test can run, such as "the tube colour is red on an expired
sample". Decision 103 has a person type what they saw during the sign-off walk, and the walk runs
only at `signed`. At `passed` nobody signs, so nothing records the hand check, yet the gate
`passed` says "every rule's tests pass".

- **(a) Listed as not checked, recommended.** The release at `passed` goes ahead; it prints one
  line naming the rules checked by hand, and the package lists them as not checked. Consequence:
  "we are just creating evidence" holds, a `passed` release says plainly what was not checked, and
  a team that wants hand checks recorded uses `signed`.
- **(b) Refused.** A release at `passed` is refused while any proof is `@manual`, naming
  `purlin:init --gate signed`. Consequence: no `passed` release ever leaves a hand check silent, but
  a project with one look-and-feel check cannot release at `passed` at all.
- **(c) Asked without a signature.** The release run at `passed` asks, for each hand check, what the
  person saw, and puts the lines into the package unsigned. Consequence: the notes are recorded, but
  `purlin:test` becomes interactive at `passed` and the notes carry no signature.

The plan is written to (a): C13, lane `release` RULE-10, the dashboard line. Under (b) lane
`release` replaces RULE-10 with a refusal
`No release: 2 rules are checked by hand, and the gate passed records no hand check: <rules>. Run purlin:init --gate signed to check them in the sign-off.`;
under (c) lane `run` adds the questions to `--release`.

**Answered by the owner, 2026-09-30: (a), listed as not checked.** Every lane builds to (a).

## 9. Calls this plan makes

Not questions: each follows from decision 103 or the accepted calls, and the owner may reverse any.

- **The release command is `purlin:test --release`.** Decision 103 names "the release run"; it
  runs every test and commits the evidence first, so it is the test command's flag, not a new
  skill.
- **The package is written once and the sign-offs sit beside it**, one file per signer under
  `.purlin/evidence/package/<version>.signoffs/`, so a second signer never rewrites the file the
  first signed and two signers never conflict.
- **A release is refused only on what stops its tests from passing**: a broken spec, a test
  comment that names nothing, and a rule that fails, has no test, has not run, or waits on another
  system. A rule with no proof at `signed` and a weak rule are listed, not refused.
- **The strong cell stays, at both gates, as what the audit found**, and the sentence and the
  `Strong` column name it only where a rule was audited (decision 93).
- **`min_strength` goes** rather than staying as a threshold nobody obeys; a measured strength is
  shown as a number.
- **Setup asks about breaking the code on purpose at `signed` alone**, where a person reads the
  audit at the sign-off; `--mutation` turns it on at either gate.
- **The walk stops at hand checks first**, then weak, then not audited, then any strong rules walked.
  A signer confirms once at the end (`[y/N]`) because signing is the one act the walk writes.
- **The agent's walk is two calls, `--show` then `--answers`**, because the agent's shell has no
  terminal for the person to answer in; a person at a terminal answers each question directly.
- **One sign-off per signer per version.** A second attempt is refused, not stacked.
- **The tag run stays on `signed/*`**: a `passed/*` tag starts no remote run, and no runner file
  changes.
- **The renumbering helper sits in lane `drift`** because it reads drift's default branch, moving
  line and blamed comments; its steps live in `skills/spec/SKILL.md` alone, and the other skills
  point there.
- **No per-rule signature is migrated.** No 0.9.5 project holds one, and 0.10.0 has not shipped.
