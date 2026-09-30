# Sanity check: QA and product working together, Purlin 0.10.0

One reviewer played three people (product, QA, dev) in three clones of one bare repository, on a
small GxP-style project: sample intake at a central lab (age of a sample at receipt across time
zones, the stability window, the accession screen). The gate was `signed`. Everything ran as the
plain scripts under `scripts/`; no model was called.

**One substitution.** `purlin:audit` needs a model. To reach `strong` and `signed` without one, a
four-line stub named `claude` was put first on `PATH` in the scratch shell. It reads the prompt,
discards it and answers `settled: yes` with no findings (`modelUsage: stub-model`). Every
`strong` below is therefore meaningless as an audit. The stub only moved rules along so the
signing and merge behaviour could be seen. Where a real audit would probably have caught
something, the finding says so.

## 1. What was done

Setup, with `S` a scratch folder and `P` the Purlin checkout at `sanity/qa-product` (0.10.0):

```bash
git init --bare -b main shared.git
git clone shared.git product; git clone shared.git qa; git clone shared.git dev
# per clone: one person, one SSH key
git config user.name "Pat Product"; git config user.email pat.product@labconnect.example   # product
git config user.name "Quinn QA";    git config user.email quinn.qa@labconnect.example      # qa
git config user.name "Dana Dev";    git config user.email dana.dev@labconnect.example      # dev
ssh-keygen -t ed25519 -f keys/<role> -N ""; git config gpg.format ssh; git config user.signingkey keys/<role>.pub
```

The commands per role ran as the skills say: `purlin:test` and `purlin:audit` are
`sh $P/scripts/purlin_python.sh $P/scripts/run/purlin_run.py --test|--audit [--commit]`,
`purlin:sign` is `.../scripts/review/sign.py`, `purlin:status` and `purlin:drift` are
`sync_status` and `drift` from `scripts/mcp/purlin/`, and the AI's read before signing is
`.../scripts/review/ai_audit.py --feature <f> --rule RULE-N`. `purlin:spec` and `purlin:build`
are skills for the AI with no script. Their edits were made by hand, following the skill text
literally.

| # | Who | Branch | What | Result |
|---|-----|--------|------|--------|
| 1 | product | main | `echo 0.1.0 > VERSION`, `scaffold.py --project-root . --gate signed --yes` | `Committed 03f8210, the files setup wrote`; `No specs found under specs/.` |
| 2 | product | main | `purlin:spec`: `specs/intake/sample_age.md` (RULE-1..3, PROOF-1..3) and `specs/intake/stability.md` (RULE-1..2), pushed | `c849d04`. PROOF-1 carries a wrong expected value (150 min; the true age is 90) |
| 3 | all | from `c849d04` | product `product/age-rules`, QA `qa/age-proofs`, dev `dev/intake` | same fork point |
| 4 | product | product/age-rules | `purlin:spec`: RULE-4 (receipt time with no zone refused) + PROOF-4, `Highest-Rule: 4`, `Highest-Proof: 4`, read against `origin/main` as the skill says | `a752166` |
| 5 | QA | qa/age-proofs | QA's own words, "the age must be right across daylight saving", turned into proofs: PROOF-4 (RULE-1, spring-forward, 60 min) placed under PROOF-1, RULE-4 (repeated hour refused) + PROOF-5 at the end; `Highest-Rule: 4`, `Highest-Proof: 5` | pushed |
| 6 | dev | dev/intake | code and marked tests for PROOF-1..3 and stability; first `purlin_run.py --test` | `No test command is set and no test tool Purlin knows was found`; after adding `conftest.py`, the suggestion; the `tests` setting was written |
| 7 | dev | dev/intake | test of PROOF-1 fails `assert 90 == 150`; per `purlin:build`, "Stop and fix the rule", PROOF-1 changed to 90 in the spec; `--test --commit`, `--audit --commit`, push | `5 rules to sign` |
| 8 | - | - | snapshot of the bare repo and the three clones, for the second merge order | |
| 9 | product | main | **Run 1, product first**: `git merge --no-ff product/age-rules`, push | `1fe7a5b` |
| 10 | dev | dev/intake | `git pull origin main` (clean), builds RULE-4: test marked `sample_age PROOF-4`, `--audit --commit`, push | `6 rules to sign` |
| 11 | QA | qa/age-proofs | `git pull origin main`: conflict on the spec. Resolved per `purlin:spec` "After a merge conflict": the incoming (main's, product's) RULE-4 and PROOF-4 became RULE-5 and PROOF-6; QA's clone holds no marker to move. Pushed to main | `e06bc33` |
| 12 | dev | dev/intake | `git pull origin main`: conflict only on PROOF-1's text (90 vs 150). The test file merged clean. Kept 90 | dev's `PROOF-4` marker now means QA's spring-forward proof |
| 13 | dev | dev/intake | `purlin:build` for the two rules with no test: finds the existing receipt test, adds `PROOF-6` above it (the skill's step 1), writes PROOF-5's test; `--audit --commit`; pushes to main | `7 rules. 7 pass their tests. 7 are strong.` |
| 14 | QA | main | `purlin:drift qa`, `ai_audit.py --rule RULE-1` shows the mismatch; QA skips RULE-1 and signs the rest: `sign.py sample_age RULE-2 RULE-3 RULE-4 RULE-5`, `sign.py stability` | 6 signed, pushed |
| 15 | dev | dev/intake | not yet pulled; fixes the marker (PROOF-4 gets its own spring-forward test), `--audit --commit`, pulls QA's signatures, then **dev signs RULE-1**: `sign.py sample_age RULE-1`; pushes to main | QA's four sample_age signatures ended |
| 16 | QA | main | pull, `purlin:drift qa`, `sign.py` walk, answers `sign` x4 | walk re-signed and **wrote the tag** `signed/0.1.0` |
| 17 | QA | copy of main | `unshare -u` with hostname `quinn-laptop`: `--test --all --commit` on the same commit | all 7 signatures ended |
| 18 | all | from `8de0b6e` | **Round 2, QA first**: product `product/sprint2` (stability RULE-3 unknown tube + PROOF-3; new `specs/ui/accession_screen.md`, one `@manual` colour proof); QA `qa/stability` (stability RULE-3 EDTA window + PROOF-3, PROOF-4; `--test --commit` from `quinn-laptop`), pushed to main first; dev `dev/sprint2` from product's branch, test marked `stability PROOF-3` | |
| 19 | product | product/sprint2 | pull main: conflict; incoming (QA's, already on main) renumbered to RULE-4, PROOF-5, PROOF-6; pushed to main | `e026ea3` |
| 20 | dev | dev/sprint2 | pull main: `CONFLICT (content): Merge conflict in .purlin/evidence/local/stability.json` and `.purlin/tests.md`; re-ran; builds PROOF-5, PROOF-6; audit; pushes to main | `c091e5c` |
| 21 | dev, QA | main | dev pushes a docstring change to `src/ui/accession.py`; QA, not pulled, walks and signs 6, `--note` for the colour check, writes `VERSION` 0.2.0, `sign.py` tags `signed/0.2.0` at `c1d4a27`; push rejected; pull merges clean | accession's 3 signatures ended; the tag's commit is not on `origin/main` |
| 22 | product, dev | snapshot | **Run 2, QA first** on the sample_age collision: QA to main, product merges and renumbers QA's conflicted lines (RULE-4 to RULE-5, PROOF-5 to PROOF-6), dev pulls, a careless `git commit -a` commits the conflict markers | two `PROOF-4` lines and two `PROOF-1` lines on main, no warning |
| 23 | - | throwaways | proof id twice; renaming signature files; config.json conflict; two branches each adding `PROOF-7` in different places | see findings |

## 2. Findings, most severe first

### F1. A proof id written twice is not warned of, and one marker then proves both proofs
**What happened.** Run 1, step 12: after two correct-looking merges the spec held QA's
`PROOF-4 (RULE-1)` (spring-forward, 60 min), while dev's test marked `# purlin: sample_age PROOF-4`
was written for product's old PROOF-4 (receipt time without a zone). Git merged the test file
without a conflict. Purlin tied it:

```
('PROOF-4', 'RULE-1', 'test_receipt_without_zone_refused', 'pass')
7 rules. 7 pass their tests. 7 are strong. 0 are signed.
```

RULE-1's daylight-saving case was never tested, and every cell read met. Throwaway (step 23)
with `PROOF-4` on two lines for two rules:

```
sample_age        5      5       5 of 5  0 of 5  0 of 5
[('PROOF-4','RULE-1','test_receipt_without_zone_refused','pass'), ('PROOF-4','RULE-1','test_age_across_spring_forward','pass'), ... ('PROOF-4','RULE-5','test_receipt_without_zone_refused','pass'), ('PROOF-4','RULE-5','test_age_across_spring_forward','pass')]
```

Six proof lines are counted as `5`, and nothing is printed. A rule written twice is warned of
(`sample_age: RULE-4 is written twice; the second is read.`); a proof is not. The fully silent
case (step 23): two branches each add one proof, both take `PROOF-7`, one placed under its rule
and one appended. Both bump `> Highest-Proof: 6` to `7`, so that line merges clean. Then
`git merge` exits 0, and status reads `stability 4 6 · 1 no test`, with no warning.
**Hurts.** QA most (signs over it), then the regulated reader. **Kind.** Product fault.
**Fix.** Warn of a proof id written twice exactly as for a rule, make `purlin:test` exit 1 on it,
and refuse `sign.py` on a feature that has one.

### F2. The collision recipe cannot be followed, and where it is followed it breaks things
**What happened.** `docs/specs-and-anchors.md`, `docs/team-workflow.md` and `skills/spec/SKILL.md`
say: "Keep both rules, give the incoming one the next free number, and move its test markers and
its signature filenames with it."
- "Incoming" is ambiguous. On `git pull origin main` into a branch, git's incoming side is
  main's, which is already published. Read literally, step 11 renumbered product's rule, which
  was on main, and step 19 renumbered QA's rule, which was on main. Both times the
  published id changed.
- "Move its test markers" assumes the markers are in your checkout. Dev's `PROOF-4` marker was on
  `dev/intake`, unmerged, so QA could not move it. That is how F1 happened.
- "Move its signature filenames" does not work. Renaming `RULE-5.*.json` to `RULE-6.*.json` and
  committing, even as a signed commit, leaves `"rule": "RULE-5"` inside the file. The renumbered
  rule also loses its audit, which is keyed by rule id:
  `sample_age 5 6 5 of 5 4 of 5 4 of 5`. A renumber costs a new AI audit and a new signature.
- The hunk git shows does not contain every duplicate. In both runs QA's PROOF-4 line merged
  clean, outside the conflict markers.

**Hurts.** Whoever merges second, and QA. **Kind.** Doc gap and product fault.
**Fix.** Say "the number already on the default branch keeps it; the unmerged branch's rule
moves", and have `purlin:spec` (or a status check) list every marker in every branch
(`git grep` over `origin/*`) that names a moved id. Drop the signature-rename advice and say the
moved rule needs a new audit and signature.

### F3. The signing walk never shows the test the signer attests to
**What happened.** Step 14. `sign.py` prints the rule, the proofs and `What the audit found`, and
no test name or body:

```
sample_age RULE-1   to sign
Rule
  The age at receipt is ...
Proof
  PROOF-1: ... has an age of `90` minutes
  PROOF-4: ... across the spring-forward change, has an age of `60` minutes
What the audit found
  Strong. It found nothing.
```

The mis-tie of F1 was visible only through `ai_audit.py --rule RULE-1`, which prints
`PROOF-4  tests/test_age.py::test_receipt_without_zone_refused` and a body calling
`age_minutes(... None)`. The skill tells the AI to read that first. A QA running the walk, or
an AI that skips that step, signs "the rule, its proof and its test belong together" without
seeing the test. A real audit might have flagged the mismatch; a stubbed or weak one does not.
**Hurts.** QA. **Kind.** Product fault.
**Fix.** Print, at each stop, each proof's tied test as `file::name`, and the body on request.

### F4. The walk writes the release tag on its own, over signatures by anyone, including the author of the code
**What happened.** Step 15: dev, who wrote the code and the tests, ran
`sign.py sample_age RULE-1` (the rule QA had skipped) and it counted:
`Signed 1 rule as dana.dev@labconnect.example`. Step 16: QA re-signed four rules in the walk,
and the walk went straight on:

```
Walked 4 rules: 4 signed, 0 cases added, 0 skipped.
Evidence package committed: .purlin/evidence/package/0.1.0.json.
Tagged signed/0.1.0 at 8de0b6e.
```

QA never saw RULE-1 again, and was not asked before the tag. The package does name each signer
(`sample_age RULE-1 [('dana.dev@labconnect.example', ...)]`), so a regulated reader can catch
it, but the tag was already written under QA's key. `signatures.py` says it plainly: "Nothing
about the key or the author is read".
**Hurts.** QA and the owner of the release. **Kind.** Workflow matter; the docs say signing is
"logged, not policed".
**Fix.** Before tagging, print who signed each rule and whether that person last changed its test
or code, and ask `Tag signed/<version>? [y/N]`. The separation rule itself is for the owner to
decide (Q2).

### F5. Signatures end silently, and far more broadly than a reader expects
**What happened.**
- Step 15: dev changed one test in `tests/test_age.py`, and all four QA signatures in that file
  ended, including rules whose tests did not change. `test_hash_kind: "file"` hashes the whole
  file.
- Step 21: a docstring change to `src/ui/accession.py` ended all three accession signatures,
  including the `@manual` colour check. QA has to look at the red again by hand.
- Step 17: QA re-ran the same tests on the same commit on their own laptop, with `--commit`, and
  all seven signatures ended: `7 rules. 7 pass their tests. 7 are strong. 0 are signed.` The
  diff shows only `"machine": "vm"` changed to `"quinn-laptop"`. Checking the work invalidates
  the sign-off.

In every case the only trace is a count going down. `purlin:drift qa` said
`1 test file changed, covering sample_age.` and `4 rules to sign`, never which signatures ended
or why. **Hurts.** QA; it makes QA wait on everyone else and redo work. **Kind.** Product fault
(silence), design matter (breadth). **Fix.** Print one line per ended signature with its cause
(`sample_age RULE-2: signed by quinn.qa, ended by tests/test_age.py at d965a7a`). Consider
hashing the test function instead of the file. Consider leaving a hand-check signature alone
when the code change is outside what it observed. Do not bind the machine when the results are
the same.

### F6. Conflict markers committed in a spec are read as if they were rules
**What happened.** Step 22: a `git commit -a` during a conflicted pull committed
`<<<<<<< HEAD` ... `>>>>>>>` into `sample_age.md`. The spec then held PROOF-1 twice, once
expecting `90` and once `150`, and PROOF-4 twice. Status:
`sample_age 5 5 · 1 no test 4 of 5 0 of 5 0 of 5`, with no warning. Mid-merge status shows
`UU specs/intake/sample_age.md`, which helps, but only until the commit.
**Hurts.** Everyone. **Kind.** Product fault. **Fix.** Treat a line starting with `<<<<<<<`,
`=======` or `>>>>>>>` in a spec as an error that stops `purlin:test` and `purlin:sign`.

### F7. Drift does not report a changed proof, and QA's critical numbers change unseen
**What happened.** Dev changed PROOF-1's expected value from `150` to `90` (step 7, correctly),
and product later renumbered QA's EDTA rule from RULE-3 to RULE-4, putting a different rule under
RULE-3 (step 19). After pulling, `purlin:drift pm` printed only
`5 rules added: accession_screen RULE-1, RULE-2, RULE-3; stability RULE-3, RULE-4.`, and
`purlin:drift qa` printed `2 test files changed, covering accession_screen, stability.` Neither
view names a proof. For a QA whose risk is "is the number right", a changed expected value is the
most important change there is. **Hurts.** QA. **Kind.** Product fault.
**Fix.** Add proofs added, changed (old and new value) and moved to the `pm` and `qa` views, and
list ids whose text changed meaning (same id, different text) separately.

### F8. Evidence conflicts on almost every merge, and resolving them costs a new audit
**What happened.** Step 20:
`CONFLICT (content): Merge conflict in .purlin/evidence/local/stability.json` and `.purlin/tests.md`,
because QA's `--test --commit` on its branch and dev's `--audit --commit` both rewrote the one
section per system. Purlin handled the broken file well:
`.purlin/evidence/local/stability.json is not valid JSON; it is ignored. Run purlin:test stability to write it again.`
The re-run then wrote the file without the audit entries (`stability 4 5 · 2 no test 3 of 4 0 of 4`),
so the feature needed `purlin:audit` again: a model call per rule. **Hurts.** Dev (cost) and QA
(waits). **Kind.** Workflow and product. **Fix.** Tell teams that only one role commits
evidence, and only on the default branch. Or have the re-run keep audit entries whose rule,
proof and test hashes still match.

### F9. A tag can be written on a commit the default branch does not hold
**What happened.** Step 21: while QA walked, dev pushed a docstring change to main. QA's walk
ended `Tagged signed/0.2.0 at c1d4a27.` and `Push the tag to release it`. `git push` of `main` was
rejected, the pull merged clean, and then `tag commit not on origin/main`, while main read
`12 rules ... 9 are signed`. Pushing the tag as told releases a tree that main no longer has.
**Hurts.** QA and the release owner. **Kind.** Workflow. **Fix.** Before tagging, have
`sign.py` fetch and refuse when `origin/<branch>` has moved past HEAD; recommend tagging on a
release branch nobody else pushes to.

### F10. QA cannot express risk
Every rule at `signed` needs the same things: tests, an audit and a signature. There is no
per-rule or per-feature weight. What exists (section 4) is indirect, and one piece works against
risk-based validation: the cosmetic `@manual` colour check was ended by a docstring change
(F5) and blocked the tag as `1 rule to test by hand`. **Hurts.** QA. **Kind.** Product design.
**Fix.** See Q3.

### F11. A new spec on main blocks the release of everything else
From step 19, product's new `accession_screen` spec on main made `Left to do` read
`1 rule to write a test for`, then `1 rule to test by hand`. No tag was possible until dev built
the screen and QA checked a colour by hand, although QA's intake rules were all signed. The
gate covers the whole project. **Hurts.** QA waits on product and dev. **Kind.** Workflow.
**Fix.** Document a release branch per version, or allow `purlin:sign --release` over a named
set of features.

### F12. Smaller product faults
- The status line points at the wrong cause. Before the code exists (QA's clone, step 11) it
  reads `2 specs name no files, so their tests run every time: sample_age, stability. Run purlin:spec with each name to add its > Scope: line.`
  Both specs have a `> Scope:` line; the files are not written or not tracked yet.
- A signature's commit only needs a `gpgsig` header. `_signed_commit` never verifies it, and the
  file's `key_fingerprint` is taken from the signer's config, not from the commit (read in
  `scripts/mcp/purlin/signatures.py`, not exercised). A rebase or rebase-merge that drops the
  signature ends every signature it touched. A GitHub squash merge re-signs with GitHub's key, and
  those signatures count (inferred from the code, not run).
- Old signature files are never removed: after step 16, `sample_age.signatures/` held two files
  for each of RULE-2..5. Harmless, but QA reading the folder cannot tell which one counts.
- The first run did not recognise a plain `tests/test_*.py` project:
  `No test command is set and no test tool Purlin knows was found`. It needs `conftest.py`,
  `pytest.ini` or `[tool.pytest` (documented in `supported_frameworks.md`).

### F13. Doc gaps
- `docs/specs-and-anchors.md` shows `> Highest-Proof: 2` over a spec holding `PROOF-4`.
- `docs/index.md`'s QA section offers only `review-and-signing.md` and `dashboard.md`. Nothing
  walks a newcomer from "here are my criteria" to a proof, to what dev adds, to a signature.
  The pieces are spread over `working-together.md`, `spec_quality_guide.md` and
  `review-and-signing.md`.
- The docs say how to set up the key (the three commands), but not that `git log --show-signature`
  then fails with
  `error: gpg.ssh.allowedSignersFile needs to be configured and exist for ssh signature verification`.
  A QA who wants to check a signature by hand is stuck.
- The docs say a signature covers "its test". The format file says it covers the whole test file
  and the machine, and the user guides do not show the consequences (F5).
- Nothing says who should commit evidence, or on which branch (F8).

### What worked
A rule written twice is warned of. A conflicted evidence or settings file gives a clear message
naming the fix:
`.purlin/config.json cannot be read: Expecting property name ... Fix the file by hand; nothing ran and nothing was saved.`
A signature file per rule never conflicted. The `Highest-*` lines did produce a conflict whenever
the two sides wrote different numbers. The package names every signer.

## 3. Per role

**Product.**
- Wrote a wrong expected value (150 for 90). Nothing but dev's failing test caught it, and the
  fix reached product only as a spec commit on dev's branch. Product was never told.
- Had to resolve a spec conflict (step 19) with ambiguous instructions (F2), and changed ids QA
  had already published.
- Merging a new spec to main blocked QA's release (F11), with no warning that it would.

**QA.**
- Made to wait: on dev's audit before `to sign` appears; on dev's rebuild after every renumber;
  on the UI feature before any tag.
- Made to redo work: re-signed four rules after an unrelated test edit (F5). Re-signed seven
  after re-running the tests themselves, where step 17 ended them. Re-checked a colour after a
  docstring change.
- Confused: signatures vanish with no reason (F5). QA's EDTA rule became RULE-4 and RULE-3 now
  means something else (F7). The walk shows no tests (F3). The tag appeared at the end of a
  re-sign, carrying a rule QA had refused and the developer had signed (F4).
- What QA needed: at each stop, the tests; after a pull, which signatures ended and why, and
  which proofs changed; a question before the tag.

**Dev.**
- Had to change the spec to make a correct test pass (the build skill says to). That edit
  conflicted twice, once with QA's lines.
- Hit an evidence conflict on its first merge after QA ran tests, and had to pay for a re-audit
  (F8).
- Could sign its own work, and nothing said that was unusual (F4).
- Had no way to know its `PROOF-4` marker had changed meaning under it. `Markers: 6 tied to a test, 0 not tied.`

## 4. QA's view, as the docs let a newcomer see it

**What QA writes.** `working-together.md`: "You write and review the proofs". A proof says what
is done, what is observed and the value (`spec_quality_guide.md`). QA says a criterion in plain
words, and `purlin:spec` writes the proof line with the next free id. During the walk, answering
`case` adds a proof line; `purlin:build` later writes its test. QA writes no test and no code.
This part is clear in the docs.

**What QA verifies and signs.** At `signed`, every rule waits `to sign` once its tests pass and
the audit is strong. `@manual` proofs wait `to test by hand` and take a `--note`. A signature
locks the rule, its proofs, the test file, the code the spec's `> Scope:` names, the audit and the
machine. The docs say this, but only `signature_format.md` says "test file" and "machine", and no
user guide shows what that costs (F5). The walk does not show what QA is attesting to (F3).

**What dev adds.** The code, one marked test per proof (`# purlin: <feature> PROOF-N`), the
evidence (`--test --commit`), the audit (`--audit --commit`), and spec corrections when a proof
cannot hold. The docs never say that a dev may change a proof's expected value, or that QA will
not be told when it happens (F7).

**Risk-based priorities today.** Nothing is weighted. What QA can do:
- Leave look and feel out of the spec. `spec_quality_guide.md` "What a missing rule costs"
  already says "Visual polish ... Not a rule. QA catches it." This is the closest thing to a
  risk table the docs have.
- Put more proofs, meaning boundaries, time zones and daylight saving, on the critical rules.
  This works, but it multiplies the collision surface (F1).
- Use `@manual` for what a person must judge. Cosmetic checks are still re-required on any code
  change (F5).
- Put a label in the rule text, as with `(URS-042)`, for example `(risk: high)`. It reaches the
  package and nothing reads it.
- Use category folders (`specs/critical/`, `specs/ui/`). They are cosmetic to Purlin.
- Data flows across features (age, then stability, then the screen) have no home: a proof names
  rules of one feature, and an anchor covers the whole project, so any change ends its
  signatures.

**Could QA reach a signature from the docs alone?** Just about: the key commands, the walk and
the tag are all written down. What the docs do not prepare a QA for is working next to others:
why a signature ended, which proof changed, that re-running the tests ends signatures, that the
walk tags on its own, and what to do when an id collides.

## 5. What one agent could not show

- **True simultaneity.** Here every action ran in sequence, and each role's `origin/main` was
  current when it acted. With real people, `git show origin/main:<spec>` is as stale as the last
  fetch, so collisions will be more frequent than here, not less.
- **Real AI behaviour.** Each role's AI was simulated by following the skill text. Separate
  agents would show whether a real `purlin:spec` notices a duplicate outside the conflict hunk,
  which side a real AI calls "incoming", whether `purlin:build` spots a marker already tied to the
  wrong proof, and whether a real audit catches F1. That last one is the single most valuable
  unknown.
- **Pull requests and hosted merges.** Squash and rebase merges on GitHub, branch protection, and
  a remote runner's `ci/` evidence arriving mid-merge were not exercised.
- **Human reading.** Whether a person reads the walk's text closely enough to catch a mismatch.

A run with three separate agents in separate containers, on one shared remote, would be worth it
once: it is the only way to measure how often F1 and F2 happen unprompted, and what real
`purlin:spec`, `purlin:build` and `purlin:audit` do about them. Keep it to one feature and one
collision, with a real audit on only the collided rule, to hold the cost down.

## 6. Questions for the owner

1. **How are ids made safe across branches?** (a) Keep sequential ids; add a duplicate-proof
   warning (F1) and a check that lists markers on other branches naming a moved id. (b) Let
   markers carry a short hash of the proof text, so a marker whose proof changed meaning reads
   `not tied`. (c) Branch-scoped ids, such as `PROOF-4b`, renumbered on merge by a tool.
   (d) One owner allocates ids: specs change only on main.
2. **Who may sign?** (a) Anyone, as now; the regulated system checks. (b) Warn when the signer
   last changed the rule's test or code. (c) Refuse it at `signed`. (d) A configurable list of
   signers per gate.
3. **Should QA be able to weight risk?** (a) No; leave cosmetics out of specs and say so in the
   QA guide. (b) A per-feature gate, where `ui` stops at `passed` and `intake` requires `signed`.
   (c) A per-rule tag, `@risk(high|low)`, where low needs no signature.
4. **What should end a signature?** (a) As now: file, scope, audit, machine. (b) Test function
   instead of test file. (c) No machine binding when results are identical. (d) `@manual`
   checks bound only to the rule and proof text.
5. **Should the walk tag without asking?** (a) As now. (b) Ask first, listing each rule's
   signer. (c) Tag only with `--release` or `--tag`.
6. **Where does evidence get committed?** (a) Anywhere, as now, with conflicts resolved by
   re-running. (b) Recommend that only the default branch commits evidence. (c) Keep audit
   entries through a re-run when the hashes match.
7. **Is `strong` meaningful when a rule's proofs were renumbered?** Today a renumber costs a new
   audit and a new signature per moved rule. Should the audit key on rule text rather than rule
   id?
