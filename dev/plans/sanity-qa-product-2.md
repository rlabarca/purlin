# Sanity check 2: QA and product working together, Purlin 0.10.0 after decisions 102 and 103

One reviewer played three people, product, QA and dev, in three clones of one bare repository,
on LabConnect, a GxP central-lab intake project: the age of a sample at receipt across time zones
and daylight saving, the stability window by tube type, a unit conversion, a subject's visit
window, and critical results on the accession screen. The gate was `signed`. Every command ran as
the plain script its skill names. `purlin:spec` and `purlin:build` were played by following their
skill text literally. No model was called. The reviewer knew only the shipped docs, skills and
references, and the first check (`dev/plans/sanity-qa-product.md`) for the comparison in section 5.

**The stand-in model.** `purlin:audit` calls `claude -p --output-format json`. A 25-line Python
script named `claude` was put first on `PATH`. It reads the prompt on stdin. For every test body in
the prompt that holds the comment `# weak on purpose: <why>`, it answers one finding,
`- PROOF-N: <why>`, naming the last proof id above that comment in the prompt. Otherwise it
answers `settled: yes` with no finding, which is `strong`. It reports the model
`stand-in-judge` and logs each call. Product's AI wrote the comment into four weak tests. Dev
removed it when dev strengthened a test, and kept it on one test dev declined to change. So
`weak` here means the test truly was weak, and `strong` means the stand-in found no such
comment. A real model may find weaknesses the stand-in cannot. 33 calls were made for 19 rules.

## 1. What was done

Setup, with `S` a scratch folder and `P` this checkout at `sanity/qa-product-2` (0.10.0):

```bash
apt-get install -y openssh-client sqlite3; pip install pytest
git init --bare -b main $S/shared.git
git clone $S/shared.git product; git clone ... qa; git clone ... dev
git config user.name "Pat Product"; git config user.email pat.product@labconnect.example   # product
git config user.name "Quinn QA";    git config user.email quinn.qa@labconnect.example      # qa
git config user.name "Dana Dev";    git config user.email dana.dev@labconnect.example      # dev
ssh-keygen -t ed25519 -f $S/keys/<role> -N ""     # one key per person; QA's is not configured until purlin:sign asks
```

The commands, as their skills run them (`pl` is a shell function that calls the script in the
clone it is run from):

| Command | Script |
|---|---|
| `purlin:init` | `sh $P/scripts/purlin_python.sh $P/scripts/init/scaffold.py --project-root . --gate signed --yes` |
| `purlin:test [--commit] [--release]` | `.../scripts/run/purlin_run.py --test [--commit]`, `--release` |
| `purlin:audit [--feature f] [--commit]` | `.../scripts/run/purlin_run.py --audit ...` |
| `purlin:status`, `purlin:drift <role>`, `purlin_config` | `sync_status`, `drift`, `purlin_config` through `scripts/mcp/purlin/server.py` (JSON-RPC on stdin); drift printed as its `lines` |
| renumbering helper | `.../scripts/spec/renumber.py <feature> [--dry-run]` |
| the audit read | `.../scripts/review/ai_audit.py --feature f --rule RULE-N` |
| `purlin:sign` | `.../scripts/review/sign.py --show`, then `--answers .purlin/runtime/signoff-answers.json` |
| `purlin:export --check` | `.../scripts/export/package.py --check <file>` |

| # | Who | Branch | What | What Purlin printed |
|---|-----|--------|------|--------|
| 1 | product | main | `pyproject.toml` (version 0.1.0, `[tool.pytest.ini_options]`), `purlin:init` at `signed`, push | `Committed 9399b46, the files setup wrote`; `→ Run: purlin:spec-from-code` (the tree held only empty `__init__.py` files) |
| 2 | product | `product/intake-specs` | `purlin:spec` x3: `sample_age` (RULE-1..3, PROOF-1..4), `stability` (RULE-1..3, PROOF-1..4), `unit_conversion` (RULE-1..3, PROOF-1..3), each committed `spec(<name>):`, push | `3 specs' > Scope: lines find no file in git yet ...`, `9 rules to write a test for: purlin:build` |
| 3 | QA | `product/intake-specs` | `purlin:drift qa`; through `purlin:spec`: stability PROOF-5 (one minute past the SST window), unit_conversion PROOF-4 (creatinine rounding); push. Product merges to main | `13 proofs added: ...` |
| 4 | dev | `dev/intake` | builds the three features with 13 marked tests; first `purlin:test` suggests the pytest entry; dev confirms (`purlin_config` write); run | `sample_age RULE-1 fails: tests/test_age.py::test_age_across_spring_forward` (a real bug: same-zone subtraction ignores DST); fixed; `--test --commit`; merged to main |
| 5 | QA | main, then `qa/proof-review` | `purlin:audit`, then `purlin:audit --commit` | `AI audit: 9 rules read, 9 strong, 0 weak.` |
| 6 | QA | `qa/proof-review` | **hand edit 1**, no AI: `sed` on stability PROOF-2 (adds "one minute past its 4-hour window"); `--test --commit`, `--audit --commit`, merged to main | drift names the change, old and new text, and the test comment whose proof's wording changed |
| 7 | dev, QA | `dev/tube-case`, `qa/frozen`, both from `b9bc89a` | **Collision 1** on stability: QA's AI adds RULE-4 (frozen SST, 30 days) + PROOF-6; dev's AI adds RULE-4 (tube type in any case) + PROOF-6, code and a test marked `stability PROOF-6`. Both read `origin/main` as the skill says, both take 4 and 6 | |
| 8 | QA then dev | main | **QA merges first**. Dev `git pull origin main`: conflict; dev's AI keeps both lines, takes out the markers, commits the merge, runs drift and the helper's dry run, answers y, commits `spec(stability): ...` | section 3, "What worked" |
| 9 | dev | `dev/tube-case` | builds QA's frozen rule (PROOF-6), `--test --commit`, merges to main | `11 rules. 11 pass their tests.` |
| 10 | dev, QA | `dev/whole-minutes`, `qa/fall-back`, both from `eab76bd` | **Collision 2** on sample_age: dev adds RULE-4 (cut to whole minutes) + PROOF-5 with a test; QA adds PROOF-5 (RULE-1, fall-back, 100 min) **under PROOF-2**, RULE-4 (implausible age) + PROOF-6 at the end | |
| 11 | dev then QA | main | **Dev merges first.** QA pulls: conflict on `Highest-Proof`, RULE-4 and the last proof; QA's PROOF-5 merged clean outside the hunk. QA's AI resolves, drift, dry run, y; merged to main | the helper found the clean-merged line too |
| 12 | dev | `dev/fall-back-build` from QA's **pre-renumber** commit `d776311` | dev builds QA's fall-back and implausible-age proofs, marking `PROOF-5` and `PROOF-6` as QA's branch numbered them | test fails: QA's 100 minutes is wrong, the age is 40 |
| 13 | dev | same | **Dev disagrees with QA's proof**: per `purlin:build` ("stop and fix the rule") changes PROOF-5's value to 40 and the test; pulls main: conflicts in the spec and in `tests/test_age.py`; resolved as a hurried person would | the shared `# purlin: sample_age PROOF-5` line now sits above the fall-back test; section 3, N3 |
| 14 | dev | same | drift names the moved comment; helper `nothing to renumber`; dev's AI reads the test and moves both markers by hand; `--test --commit`; merged to main | QA's `drift qa` then shows `sample_age PROOF-7 changed: ... `100` ... `40`` |
| 15 | product | `product/visit-window` | 4th feature `visit_window` (RULE-1..3, PROOF-1..4); product's AI builds code and tests, two of them weak; `--test --commit`, push | `16 rules. 16 pass their tests.` |
| 16 | QA | `qa/visit-review` from product's branch | `purlin:audit --feature visit_window`: RULE-1 weak with two findings; QA adds PROOF-5 (first day of the window) through `purlin:spec`; `--audit --commit`, push | `AI audit: 3 rules read, 2 strong, 1 weak.` |
| 17 | dev | `dev/visit-tests` from QA's branch | **Dev redoes the tests completely** and rewrites QA's PROOF-4 (Tokyo 23:30 could not tell site time from UTC; the new proof is 00:30 Tokyo, 15:30 UTC the day before, out of window); `--audit --commit`; QA pulls, reads drift, merges to main | `16 rules ... 16 strong` |
| 18 | product, QA | `product/critical-screen`, `qa/visit-wording` | product: 5th feature `critical_screen` (RULE-1..3, PROOF-1..5, PROOF-4 `@manual`), two weak tests, `--test --commit`. At the same time QA **hand edit 2**: visit_window PROOF-2 names day 33; `--test --commit`, `--audit --commit`; QA merges first | product's pull: `CONFLICT (content): Merge conflict in .purlin/tests.md` |
| 19 | QA | `qa/critical-review` | `purlin:audit --feature critical_screen --commit` | `AI audit: 3 rules read, 1 strong, 2 weak.` then `The audit found 17 strong and 1 weak.` |
| 20 | dev | `dev/critical-tests` | strengthens PROOF-3's test; **declines** PROOF-5's ("the value passes through as a string"), says so under `Decisions:`; `--audit --commit`; merges to main | `1 rule to strengthen: purlin:build` |
| 21 | dev | `release/0.1.0` from main `1cf829e` | `purlin:test --release`; push the branch | `Evidence package committed: .purlin/evidence/package/0.1.0.json.` `Run purlin:sign to sign it; the first signature writes signed/0.1.0.` |
| 22 | QA | `release/0.1.0` | `purlin:sign --show`: no key; QA runs the three commands; `--show`; answers: hand check noted, weak rule noted, strong `list`, sign `true`; `--answers`; `git push origin signed/0.1.0` | `Tagged signed/0.1.0 at e0deb2e.` |
| 23 | product | `release/0.1.0` from origin | second signer: `--show`, `--answers` | `signed/0.1.0 stays at e0deb2e; this sign-off is added after it.` on a commit that does not hold e0deb2e |
| 24 | - | throwaway clone | `release/0.0.9` at `80190c0`, where critical_screen RULE-2's test was still weak: `--release 0.0.9`, `sign --show` | the weak finding is not shown; N1 |

## 2. Verdict

- **Confusion**: low through the build loop; drift and status name each next step. It gathers at
  the end: who pushes what after the release and the sign-off, and why the package's results name
  old commits.
- **Smoothness**: smooth. Nothing waited on the audit or on a signature. The only forced stops
  were the key setup and a release branch nobody was told to push.
- **Concurrency**: both collisions were caught, explained in one line each, and fixed with one
  `y`. A marker carrying a stale id was caught by drift alone. Where the value had also changed,
  the helper had nothing to offer, and `purlin:test` and status stayed silent.
- **Collaboration**: it feels collaborative. QA's proofs, dev's disagreements and product's weak
  tests all moved through the spec and drift, with old and new text shown. The one nag is a
  "wording changed" line that cannot be cleared.
- **Evidence**: the package is complete, fingerprinted and signed, and the sign-off records what
  was shown and typed. But a weak test hides behind a hand check, the results are not the release
  run's, `project` reads `dev`, and the second sign-off sits off the tagged line.

## 3. Findings, most severe first

### N1. A weak test is hidden when its rule also has a hand check
**What happened.** Step 19. critical_screen RULE-2 has PROOF-3 (tested, weak: the test counted
the rows) and PROOF-4 (`@manual`, the colour). The audit line and the summary under it disagree:

```
AI audit: 3 rules read, 1 strong, 2 weak.
19 rules. 19 pass their tests. The audit found 17 strong and 1 weak.
Left to do:
  1 rule to strengthen: purlin:build
```

The throwaway release at that commit (step 24) opens on `The audit: 17 strong, 1 weak, 0 not
audited.` and `2 stops: 1 hand checks, 1 weak`. The RULE-2 stop shows the weak test's body and
the proofs, and no `What the audit found`; it asks only `what did you see, in one line, or stop`.
The package holds `"verdict": "weak"` and the finding under `audit`, and also
`"strong": {"word": "manual test", "reasons": ["manual proof"]}` and `"left": null`. The signer
types what the colour looked like and signs a rule whose "first row" test reads nothing. In the
real run dev happened to strengthen it before the release.
**Hurts.** QA, and the regulated reader, on the one screen that shows critical numbers. **Kind.**
Product fault. **Fix.** Let `weak` win over `manual test` in the strong cell, list the rule under
`to strengthen`, and show `What the audit found` at a hand-check stop.

### N2. After the first sign-off, the release branch on the host lacks it, and a second sign-off lands beside it
**What happened.** Step 22 ended `Nothing left to do. Push the tag to release it: git push origin
signed/0.1.0`. QA pushed the tag as told. `origin/release/0.1.0` stayed at `b02e3b7`, the package
commit, without QA's sign-off `e0deb2e`. Product (step 23) pulled the branch, walked, and signed:

```
Signed 0.1.0 as pat.product@labconnect.example with the key ending ...gNPU.
signed/0.1.0 stays at e0deb2e; this sign-off is added after it. Push it: git push
Sign-offs of 0.1.0: pat.product@labconnect.example.
```

`d0c7f9d` is a sibling of `e0deb2e`, not after it. The line lists one signer where two exist, and
the tagged tree holds QA's sign-off and not product's. The docs promise "Later sign-offs are added
over the same package and the tag does not move".
**Hurts.** Every later signer, and the regulated reader, who reads the sign-offs from the tag.
**Kind.** Product fault and doc gap. **Fix.** End the first sign-off on
`git push origin release/0.1.0 signed/0.1.0`. Refuse a sign-off while `signed/<version>` exists
and its commit is not an ancestor of HEAD: `Pull, then run purlin:sign.`

### N3. A test can still prove the wrong proof; only drift says so
**What happened.** Steps 12 to 14. Dev built QA's fall-back proof from QA's branch before the
renumber, marked `PROOF-5`. After the merge, main's PROOF-5 is dev's own "whole minutes" proof,
and the merged test file carried one `# purlin: sample_age PROOF-5` line, now above the
fall-back test, with the whole-minutes test left unmarked. RULE-4 read `passed` through a test
of another rule:

```
Markers: 17 tied to a test, 0 not tied.
sample_age RULE-1 has no test for PROOF-7. Run purlin:build sample_age.
sample_age       5      7 · 1 no test  4 of 5  0 of 5
```

Only drift named it:

```
tests/test_age.py:33 names sample_age PROOF-5, whose wording changed since the comment was written in 495698f: it read "... `100` minutes" and now reads "... `1` minute". Check the test still shows it, or run purlin:build sample_age.
```

The helper printed `sample_age: nothing to renumber.`, because dev had also corrected the value,
so the old wording is no longer any id's. `purlin:build`, followed literally, writes a marker for
each proof with no test: it would add `PROOF-7` above the same test and leave `PROOF-5` there.
Dev's AI fixed it only by reading the drift line and the test. The dry runs never named the
comment on `dev/fall-back-build`, because it was not pushed; that is the limit the docs state.
**Hurts.** Dev, then QA and the signer: a stand-in audit called it strong, and a real one might
not look across proofs. **Kind.** Product fault. **Fix.** Report "a test comment whose proof's
wording changed" in `sync_status` and `purlin:test` too, under `Left to do`'s existing
`test comments to correct`. In `purlin:build` step 1, check that each marked test still shows
its proof before adding markers.

### N4. The package's results are not the release run's
**What happened.** Step 21. `purlin:test --release` ran every test at `1cf829e` and printed
`Ran pytest on 5 features.`, yet the package's results name five commits, four on feature
branches:

```
unit_conversion RULE-1  2cbe844 12:11:34 dana-dev vm     (the first run on dev/intake)
stability RULE-1        b148f74 12:13:12 dana-dev vm
sample_age RULE-1       682fcf9 12:14:58 dana-dev vm
critical_screen RULE-1  24a22e0 12:17:06 dana-dev vm
visit_window RULE-1     1cf829e 12:17:13 dana-dev vm     (the release run)
```

`evidence_format.md` "Retention" explains it: a run that sees the same thing over the same
fingerprint on the same machine leaves the section as it is. Each carries `"current": true`. The
user docs say only that the release "runs every test". (All three people ran on one host, `vm`;
on separate machines the release runner's own older sections would still persist the same way.)
**Hurts.** The regulated reader: nothing in the package says the tests ran at the release commit.
**Kind.** Doc gap, and a design matter. **Fix.** Have the release run write its own sections (or
a `release_run` block: commit, time, each result). At least say in `review-and-signing.md` and
`package_format.md` that a result's `commit` is the run whose fingerprint still matches.

### N5. The package names the project after the clone's folder
**What happened.** `"project": "dev"`, because dev ran the release in a folder named `dev`. Product's
release would say `product`. `package_format.md` reads `project_name` from `.purlin/config.json`,
but `purlin:init` says it writes "these six keys and no other", and `project_name` is not one.
**Hurts.** The regulated reader. **Kind.** Product fault. **Fix.** Default to the name in
`pyproject.toml`/`package.json` or the remote's repository name, and have init write
`project_name`.

### N6. Nobody is told to push the release branch
**What happened.** The release run at `signed` ended on
`Run purlin:sign to sign it; the first signature writes signed/0.1.0.` The signer is usually
another person. QA could not see the branch until dev pushed it, and no doc says to.
**Hurts.** QA waits. **Kind.** Doc gap. **Fix.** End on
`Push it for the signer: git push -u origin release/0.1.0`, and say in `qa-guide.md` "The
release" where the signer finds it. Also say whether the package and sign-offs merge back to
main; the docs say only that "a fix" is merged back.

### N7. `.purlin/tests.md` conflicts, and the documented recipe leaves it stale
**What happened.** Step 18: `CONFLICT (content): Merge conflict in .purlin/tests.md` (QA and
product each committed evidence for different features). The docs' recipe covers
`.purlin/evidence/` only. Product applied it, `git checkout --theirs` then `purlin:test --commit`:
`Nothing to run ... Evidence unchanged.` The table kept QA's side with no `critical_screen` row,
and was pushed that way. **Hurts.** Product (a conflict on a file it never wrote by hand), and
anyone reading the table. **Kind.** Product fault and doc gap. **Fix.** Render `tests.md` on every
run, "Nothing to run" included, and name it in the recipe. Or ship a `.gitattributes`
`merge=ours` line for it, since it is always rendered again.

### N8. One added test re-audits every rule of its file
**What happened.** Dev added one test to `tests/test_stability.py` (step 7): stability's
`Strong` went `5 of 5` to `0 of 4`. Dev strengthened one test in `tests/test_screen.py` (step 20):
`AI audit: 3 rules to read`, RULE-1 included, whose test did not change. `_test_hash` hashes the
whole test file, on purpose. 33 model calls for 19 rules. **Hurts.** Cost, with a real model, and
QA's strong count jumps around while nothing it reviewed changed. **Kind.** Design. **Fix.** Hash
the test function's source, or the file with the other tests' bodies left out.

### N9. The "wording changed" line cannot be cleared, and fires after a test was rewritten
**What happened.** After QA's hand edit 1 (step 6) and dev's rewrite of visit_window PROOF-4 with
a new test (step 17), every drift whose range covers the change prints, for example:
`tests/test_visits.py:31 names visit_window PROOF-4, whose wording changed since the comment was written in 7cb5a5b ... Check the test still shows it, or run purlin:build visit_window.`
Dev had rewritten that test for the new wording one commit later. The check blames the comment
line, which did not change. Checking the test does not silence it. **Hurts.** Dev and QA: each
pull repeats it, and it trains people to skip the line that caught N3. **Kind.** Product fault.
**Fix.** Compare the proof change with the last commit that touched the test's body, not the
comment line.

### N10. Drift calls a collision a change
**What happened.** Step 11, QA's drift after the conflicted merge, before the numbers-twice lines:
`sample_age PROOF-5 changed: it read "<QA's fall-back proof>" and now reads "<dev's whole-minutes proof>".`
Nothing changed QA's proof; the id is written twice. **Hurts.** QA, who reads that dev rewrote
their proof. **Kind.** Product fault. **Fix.** Leave an id written twice out of "changed".

### N11. `purlin:sign --show` needs a key before it shows anything
**What happened.** Step 22: `--show` printed `No key to sign with. These commands set one up:` and
exit 1. `--show` writes nothing, so QA could not read the package before setting up a key.
**Hurts.** QA, once. **Kind.** Product fault. **Fix.** Check the key in `--answers` and the
terminal walk, not `--show`.

### N12. Smaller things
- The overview reads `19 rules on Linux/Unix: 18 pass their tests, 1 is checked by hand.` The
  package says `"steps": {"passed": 19}` and the sign-off `"passing": 18`. RULE-2 passes its tests
  and also has a hand check. One count for one fact.
- `2 stops: 1 hand checks, 1 weak` (plural).
- When QA added PROOF-5 to the weak visit_window RULE-1 (step 16), the weak finding vanished
  from the summary (`15 strong and 0 weak`) until the next audit. `to write a test for` replaced
  `to strengthen`.
- `skills/spec/SKILL.md` "After a merge conflict": "When the conflict is two different texts on
  the same line, show both versions and ask which survives." Two different rules sharing a number
  are exactly two texts on one line, so an AI reading it literally may drop one. Say "the same
  id's text"; two ids that differ in claim are kept and renumbered.
- After the helper, the renumbered rule sits above the rule it yields to (`RULE-5`, then
  `RULE-4`).
- `purlin:init` on a tree of empty `__init__.py` files ends `→ Run: purlin:spec-from-code`.
- `git pull`, then `git checkout -b`, then drift: `Since your last checkout ... 0 commits`, so the
  pull's content is not shown.
- `1 rule has no test: visit_window RULE-1` when RULE-1 had tests for 2 of its 3 proofs.
- `git log --show-signature` and `git tag -v` still fail:
  `error: gpg.ssh.allowedSignersFile needs to be configured and exist for ssh signature verification`.
  The docs name `ssh-keygen -Y check-novalidate`, not how a QA runs it on a commit.
- `purlin:init` printed `This git host cannot run tests remotely.` for a local bare remote. Correct,
  but it reads as a fault.

### What worked
- Collisions (steps 8 and 11). Status, before the merge was committed:
  `stability: 6 lines are left from a merge conflict, the first at line 15: <<<<<<< HEAD.`, and
  `1 spec to repair: purlin:spec`. After: `stability: RULE-4 is written twice; the second is read.`
  Drift said which line keeps the number and which moves, and how fresh `origin/main` was:
  ```
  stability: RULE-4 is written twice. The line on origin/main keeps RULE-4; renumber the other to RULE-5 and move its test comments with it: "A tube type is matched whatever its letter case".
  origin/main was last fetched under a minute ago, and drift does not fetch. Run git fetch, then purlin:drift again.
  ```
  The helper's plan:
  ```
  stability: RULE-4 at line 15 becomes RULE-5: "A tube type is matched whatever its letter case".
  stability: PROOF-6 at line 25 becomes PROOF-7: "A sample in an `edta` tube aged 1439 minutes is within stability".
  stability: PROOF-6 at line 25 now names RULE-5.
  tests/test_stability.py:31 names stability PROOF-6 and moves to PROOF-7.
  stability: > Highest-Rule: 4 becomes 5.
  stability: > Highest-Proof: 6 becomes 7.
  Nothing is changed: this is a dry run.
  ```
  then `Do it? [y/N]` y, `Renumbered in stability: 3 spec lines and 1 test comment. Nothing is committed.`
  In collision 2 it also found the line git had merged clean, outside the hunk.
- Drift shows changed proofs with their old and new text in the `qa` and `pm` views, so QA saw dev
  change 100 to 40 and the Tokyo proof rewritten.
- The walk shows each proof's tied test and its body, the results, and the finding. It asks once
  before signing. The sign-off records the overview, each stop and why, the list opened, and both
  notes. `The package matches its fingerprint.`
- Nothing blocked on the audit. Weak rules were work items, not gates. The release went ahead
  with one weak rule, and the signer saw it and wrote why.

## 4. Per role

**Product.**
- Good: wrote specs in plain words; QA could edit them on the same branch; drift `pm` names
  proofs changed, with values.
- Annoyed: a `tests.md` conflict on a file product never touches, with no recipe that fixes it
  (N7).
- Confused: as a second signer, was told their sign-off was "added after" QA's, and was listed
  alone (N2).

**QA.**
- Good: proofs by plain words or by hand edit both work. Drift shows each proof change, old and
  new. The audit names the weak proof and why, which QA could hand to dev as is. Nothing is signed
  until the end, so no re-signing. The walk shows the tests.
- Annoyed: "wording changed" lines that never clear (N9); a collision reported as dev "changing"
  QA's proof (N10); a key required just to look (N11).
- Waited: for dev to push the release branch (N6).
- Not told: that a weak test hid behind the colour check (N1).

**Dev.**
- Good: the failing test of a wrong proof (100 vs 40) led straight to the spec fix, and QA saw
  it. The helper fixed collision 1 in one answer.
- Annoyed: a whole feature lost its audit for one added test (N8).
- At risk: the merged marker (N3) was found only because dev read the drift line, not because
  `purlin:test` or `purlin:build` said anything.
- Could have signed the release, as any key can; nothing said this was unusual. This is by design.

## 5. The first check's findings

| The first check | Now |
|---|---|
| F1 proof id written twice not warned, one marker proves both | **Solved**: warned, every rule of the spec `failed`, `1 spec to repair`; release refuses. Still possible: a marker on an unpushed branch carrying a stale id (N3) |
| F2 collision recipe unfollowable | **Solved**: "the number already on the default branch keeps it"; drift says which moves; the helper does it after `Do it? [y/N]`; it names comments on other branches as last fetched |
| F3 walk shows no test | **Solved**: each proof shows `tied to <file>::<test>` and the body |
| F4 walk tags on its own, over anyone's signature | **Changed**: one sign-off over the package; `Sign ...? [y/N]` before anything is written. Anyone may still sign; by design |
| F5 signatures end silently and broadly | **Solved by redesign**: nothing is signed while specs change. The breadth survives in the audit (N8) |
| F6 conflict markers read as rules | **Solved**: `6 lines are left from a merge conflict, the first at line 15` |
| F7 drift does not show a changed proof | **Solved**: `PROOF-7 changed: it read ... and now reads ...` in `qa` and `pm` |
| F8 evidence conflicts cost a re-audit | **Changed**: no evidence-file conflict this time; the recipe keeps matching audit entries. `tests.md` still conflicts (N7) |
| F9 tag on a commit main lacks | **Changed**: release branch, refused while the host's copy is ahead. New: the sign-off commit is not on the host's branch after the push the walk names (N2) |
| F10 QA cannot weight risk | **Open, by design**: the quality guide's "Where the risk is" puts weight into proofs; no per-rule weight |
| F11 a new spec blocks the release | **Solved**: release branches; new specs wait for the next version |
| F12 smaller faults | **Mostly solved**: the Scope message now says "find no file in git yet"; pyproject's pytest section is recognised; no per-rule signature files. Signature verification was not exercised |
| F13 doc gaps | **Mostly solved**: `qa-guide.md` walks criteria to sign-off; `Highest-Proof: 4` now matches the example; who commits evidence is in `team-workflow.md`. **Open**: `allowedSignersFile` |

## 6. The release and the evidence package

- Branch `release/0.1.0` from main `1cf829e`. `purlin:test --release` made `5d6ab5b`
  (`purlin: evidence at 1cf829e`, visit_window's evidence and `tests.md`) and `b02e3b7` (the package
  alone). QA's sign-off is `e0deb2e`, `sign(0.1.0): quinn.qa@labconnect.example`, an SSH-signed
  commit adding `.purlin/evidence/package/0.1.0.signoffs/quinn-qa.json`.
- `signed/0.1.0` is an annotated tag on `e0deb2e`, carrying an SSH signature, with the message
  `Released at the gate signed.` / `Commit: 5d6ab5b...` / `Gate: signed`. Pushed.
- The package describes `5d6ab5b` (`"commit"`). `git diff --stat 5d6ab5b e0deb2e` shows only
  `0.1.0.json` (1235 lines) and `quinn-qa.json` (121 lines), so the tagged tree's code, specs,
  tests and evidence are the described commit's. `purlin:export --check`: `The package matches its fingerprint.`
  The sign-off's `package_hash` equals the package's `fingerprint` `022abe54...`.
- Top level: `schema purlin-package/3`, `state finished`, `rules 19`, `steps {passed: 19}`,
  `audit {strong 17, weak 1, not_audited 0}`, `left [1 rule to strengthen]`, `purlin_version 0.10.0`,
  `project "dev"` (N5), `version 0.1.0`, `tag signed/0.1.0`, `gate signed`, `mutation_engine none`,
  `hand_checks [critical_screen RULE-2, PROOF-4, "checked": "in the sign-offs"]`, `warnings []`.
- Per rule, for all 19: the rule's words as written, its proofs with `manual` and `env`, the test
  `file::name` behind each proof, the result with `os`, `source`, `at`, `commit`, `runner`,
  `machine` and `current`, the audit with `verdict`, `findings`, `model: stand-in-judge`, the
  criteria hash, `at` and `commit`, and the `passed`/`strong` statuses. QA's PROOF-7 reads `40`,
  dev's correction. critical_screen RULE-3 carries the weak finding and `left: to_strengthen`.
- The results are not the release run's (N4): four features name earlier commits, back to
  `2cbe844`.
- The sign-off: signer, name, key fingerprint `SHA256:Q7rs...Q53A`, time, the described commit,
  the overview, `one_by_one` (RULE-2 `hand check`, RULE-3 `weak`), `in_list` (the 17 strong),
  `list_opened: true`, and both notes. The hand-check note is in the sign-off, not in the package,
  which says so (`"checked": "in the sign-offs"`).
- Missing for a regulated reader: a sign that the tests ran at the release (N4), the project's real
  name (N5), and product's second sign-off, which is on `d0c7f9d`, off the tagged line (N2). A
  weak test under a hand check would not have reached the signer (N1).

## 7. Questions for the owner

1. **When a rule has both a hand check and a weak test, what does the signer see?**
   (a) The hand-check stop also shows `What the audit found`, and the rule counts as weak (fix N1).
   (b) The rule stops twice, once per reason. (c) As now.
2. **What should the package say about the release run?** (a) The release run always writes its
   own sections, so every result names the release commit. (b) Keep retention, add a
   `release_run` block. (c) Keep it, and document what `commit` and `current` mean.
3. **How do sign-offs travel?** (a) The first sign-off tells the signer to push the branch and the
   tag, and a later one refuses until it holds the tagged commit (fix N2). (b) Sign-offs go on main
   after a merge back. (c) As now.
4. **Should the comment-wording check move into status and `purlin:test`?** (a) Yes, as `test
   comments to correct`, blamed on the test body, not the comment line (N3, N9). (b) Drift only,
   with a way to mark "checked". (c) As now.
5. **How fine should the audit's test hash be?** (a) Per test function (N8). (b) Per file, as now,
   and say so in the team docs with the cost.
6. **Where does `tests.md` belong?** (a) Rendered on every run and merged with `merge=ours`.
   (b) Not committed. (c) As now.
