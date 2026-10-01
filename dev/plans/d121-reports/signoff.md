# Decision 121, lane `signoff`: report

Branch `lane/d121-signoff`, cut from `main` at `fe512e267`. Nothing pushed, no tag, no audit,
no sign-off of this repository, no full sweep.

## Test numbers

`python3 -m pytest dev/test_signatures.py dev/test_export.py dev/test_collaboration.py -q`

| | Passed | Skipped |
|---|---|---|
| Before | 90 | 1 |
| After | 108 | 1 |

18 tests added: 14 in `dev/test_signatures.py`, 4 in `dev/test_export.py`. One test changed,
`package` PROOF-61. `signatures` holds 66 proofs and `package` 42; each has a test comment.

Spec maxima: `signatures` `> Highest-Rule: 134`, `> Highest-Proof: 265`; `package`
`> Highest-Rule: 37`, `> Highest-Proof: 80`. The tree's numbers matched the plan's.

Formats: `package_format.md` 10 to 11, `signature_format.md` 15 to 16, in the same commit as
the code.

## Seen to fail first, on `main`'s code

| Proof | What the test showed before the code changed |
|---|---|
| `signatures` PROOF-252 | `signoff.word` read `signed 9.9.9 at 0c93bbb` |
| PROOF-253 | `signoff.word` read `signed 2.1.0 at ff2e63a` after the unsigned commit |
| PROOF-254 | `load_signoffs` still answered `counts` true over the edited package |
| PROOF-255 | the second run printed `jane@acme.com has already signed 2.1.0 over this package; nothing was written.`, exit 1 |
| PROOF-259 | the strong cell read `... at this commit: the tube is blue` |
| PROOF-260 | `jane@labs.org has already signed 2.1.0 over this package; nothing was written.` |
| PROOF-261 | no refusal: the walk went on to its first question |
| `package` PROOF-61 | `audit` held three counts |
| PROOF-77 | the sign-off went ahead and signed |
| PROOF-79 | `sign.py --show` exited 0 |

These passed on `main`'s code, since they prove what the code already did: `signatures`
PROOF-256, 257, 258, 262, 263, 264, 265 and `package` PROOF-78, 80.

Every one of the 19 new or reworded proofs was then checked by breaking the code once and
restoring it with `git checkout -- <file>`. Each test failed.

## What changed, by item

**1. The status reads `signed` only where a sign-off counts.** `signatures.standing(project_root,
version)` is new and is the only thing that decides. `facts.signoff_fact` walks the tags newest
first, answers with the first that stands, and adds one line to `warnings` for each tag passed
over. It always returns `warnings`; the payload moves it out (seam B3).

**2. A package is trusted by its content.** `signatures.committed_fingerprint` runs
`package.check_bytes` over the package `HEAD` holds and returns the fingerprint computed from
it. `sign.refusal` refuses a later sign-off over a package that does not match.

**3. A sign-off is read as `HEAD` holds it.** `load_signoffs` and `hand_notes` list with
`git ls-tree` and read with `git show HEAD:`. `hand_notes` shows a note only from a sign-off
that counts.

**4. A tag git could not write.** `sign.unwritten_tag_at` finds the commit that added the
package `HEAD` holds, where no tag exists and the code has not changed since. The next run
writes the tag there. A signer who already signed gets the tag alone, with no walk and no
commit. `write_tag` takes the commit.

**5. Two signers, one name.** `sign.signoff_rel(project_root, version, email)` takes
`<slug>.json`, then `<slug>-2.json` and on, where `HEAD` holds that name for another signer.

**6. The settings file.** `sign.uncommitted_work` skips only `.purlin/evidence/`.
`package.only_records_between` reads a changed `tests` setting as a change to the code
(`_tests_setting`, new).

**7. A kept slow result.** `package._results` gives `same_code` false where a proof entry of
the rule carries `kept`.

**8. The audit's counts.** `package.audit_counts` gives five counts, read from each rule's
strong word. A rule's `audit` gains `no_bug` and `out_of_date`. `sign.plan` carries the five in
`overview.audit`; the overview prints `summary.audit_words`; `_weak` reads the strong cell's
word.

**9. The `key::` literal** is deleted from `signatures.key_fingerprint`, with `_KEY_LITERAL`.

**Imports.** `signatures` imports `package` inside a function; `facts` imports `signatures`
inside `signoff_fact`. Each of `facts`, `signatures` and `package` imports alone.

## Rules, word for word

`signatures`, `> Scope:` gains `scripts/mcp/purlin/facts.py`.

Reworded:

- RULE-108: A sign-off counts only while its `package_hash` equals the fingerprint computed over the package `HEAD` holds for its version, and a later sign-off is refused, with one line and nothing written, where that package does not match its own fingerprint
- RULE-125: Every other refusal of the command prints one line naming what is wrong and what to do, writes nothing and exits 1: no version stated or named, the signer already signed this package, git not making the sign-off commit, or a `.purlin/config.json` that cannot be read
- RULE-127: The walk opens with one line per run of the counted results, naming who ran it, on which machine, when, on which commit and how many rules, then `Signing <version> at <sha7>.`, then an overview counting per system the rules that pass and the hand checks, and what the audit found, as the status counts it: strong, weak, spot-checked, out of date and not audited, a count of zero left out but strong

New:

- RULE-130: The sign-off reads `signed <version>` only where `signed/<version>` names a commit holding the package for that version and a sign-off of it counts; a tag that does not is passed over, with one warning naming the tag and why, and the sign-off reads `not signed` where no tag is left
- RULE-131: Where the sign-off's commit is made and git cannot write `signed/<version>`, the command prints one line naming the tag and git's reason and exits 1, and the next `purlin:sign` writes the tag on that commit and adds no second sign-off
- RULE-132: The command refuses in the same way while a rule has no result that counts, naming each: a rule never run, a slow proof not run, a rule with no result on a system one of its proofs is tagged for, the rules of a spec that holds a number twice or a merge-conflict line, and each test comment to correct
- RULE-133: A sign-off is read as `HEAD` holds it: a file not tracked, or changed and not committed, does not count, and no note of a sign-off that does not count is shown
- RULE-134: Two signers whose addresses differ each keep a sign-off of one version: the second takes a file name of its own, and the first signer's file is left as it was

`package`, reworded:

- RULE-29: The package carries `audit`, the count of rules the audit found `strong`, `weak` and `spot_checked`, of those whose audit is `out_of_date` and of those `not_audited`, and `hand_checks`, one entry per rule with a `@manual` proof naming its feature, rule and proofs
- RULE-33: Each result carries `same_code`, true when every commit from the one its tests ran at to the package's `commit` changes only files under `.purlin/` and leaves the `tests` setting as it was, and no proof of the rule holds a result kept from an earlier run

## Proofs, word for word

`signatures`, new:

- PROOF-252 (RULE-130): A project with committed evidence that passes carries the tag `signed/9.9.9`, written by hand with `git tag`, and no file under `.purlin/evidence/package/`; the sign-off reads `not signed`, and the warnings hold one line starting `signed/9.9.9: it names a commit that holds no evidence package for 9.9.9`
- PROOF-253 (RULE-130): The walk signs `2.1.0`, then a commit made with no signature changes the sign-off file's note; the sign-off reads `not signed`, and the warnings hold one line starting `signed/2.1.0: no sign-off of 2.1.0 counts: the commit that added it is not signed`
- PROOF-254 (RULE-108): The walk signs `2.1.0`, then the committed package's first `"passed"` is changed to `"failed"` with `fingerprint` left as it was, and committed; the sign-off no longer counts, and a second signer's walk prints only one line beginning `No sign-off: .purlin/evidence/package/2.1.0.json does not match its fingerprint:`, and exits 1
- PROOF-255 (RULE-131): With a file at `.git/refs/tags/signed`, so git can write no tag under it, the first sign-off of `2.1.0` makes its commit, prints a line beginning `No tag: git could not write signed/2.1.0:` and exits 1; with that file removed, `purlin:sign` run again exits 0, `signed/2.1.0` names that commit, and no commit was added
- PROOF-256 (RULE-132): `login RULE-2` has `PROOF-2` tagged `@env(windows)`, and the evidence committed at `HEAD` holds results for Linux/Unix alone, all passing; the walk prints only one line beginning `No sign-off: 1 rule does not pass at` and naming `login RULE-2`, and exits 1
- PROOF-257 (RULE-132): `login RULE-2` has `PROOF-2` tagged `@slow`, and the evidence committed at `HEAD` was written by `purlin:test` with no `--all`, every other rule passing; the walk prints only one line beginning `No sign-off: 1 rule does not pass at` and naming `login RULE-2`, and exits 1
- PROOF-258 (RULE-132): `specs/auth/login.md` holds two lines numbered `RULE-2`, and its results are committed at `HEAD`; the walk prints one line beginning `No sign-off:` and naming `login RULE-2`, writes no file and exits 1
- PROOF-259 (RULE-133): After `quinn.qa@labconnect.example` signs `0.1.0` with the note `the tube is red`, the file's note is edited to `the tube is blue` and not committed; `login RULE-2`'s strong cell carries the reason holding `the tube is red` and none holding `the tube is blue`
- PROOF-260 (RULE-134): `jane@acme.com` signs `2.1.0`, then `jane@labs.org` signs it; the folder `2.1.0.signoffs` holds `jane.json`, reading the signer `jane@acme.com` with its bytes unchanged, and `jane-2.json`, reading `jane@labs.org`
- PROOF-261 (RULE-102): With committed evidence that passes, the `version` in `.purlin/config.json` is changed and not committed; the walk prints only `No sign-off: 1 file is changed and not committed. Commit it or set it aside, then run purlin:sign again.` and exits 1
- PROOF-262 (RULE-126): `login RULE-2` has `PROOF-2` marked `@manual` and `PROOF-3` tested, and the audit found it weak with the finding `PROOF-3 reads the status alone.`; its stop holds, before the question, `What the audit found` and then `  PROOF-3 reads the status alone.`
- PROOF-263 (RULE-126): `login RULE-2`, a hand check, has `PROOF-3` tagged `@env(windows)`, run under the source `ci` on the machine `build-7`; its stop holds the two lines `  Linux/Unix: passed on dana-laptop` and `  Windows: passed on build-7`, in that order
- PROOF-264 (RULE-111): An answers file gives `login RULE-2` a note and holds `"sign": "yes"`, a string and not `true`; `--answers` prints `Nothing was signed.`, exits 0 and adds no commit and no file
- PROOF-265 (RULE-125): With `.purlin/config.json` holding `{"version": "0.10.0",`, the walk prints only `.purlin/config.json cannot be read: Expecting property name enclosed in double quotes at line 1. Fix the file by hand; nothing ran and nothing was saved.`, adds no commit and exits 1

`package`, reworded:

- PROOF-61 (RULE-29): Both rules pass, `RULE-1` is audited `strong` and `RULE-2` `weak`, and the project is signed; the package's `audit` reads `{"strong": 1, "weak": 1, "spot_checked": 0, "out_of_date": 0, "not_audited": 0}`

`package`, new:

- PROOF-77 (RULE-33): The tests run and are committed at `<c>`, then a commit changes the `run` command of the `tests` setting in `.purlin/config.json`; `purlin:sign` prints only one line beginning `No sign-off: these results were not taken on this version of the code` and exits 1
- PROOF-78 (RULE-33): `login`'s committed results name a commit on another branch, which `HEAD` does not descend from, the two trees holding the same files; `purlin:sign` prints only one line beginning `No sign-off: these results were not taken on this version of the code` and exits 1
- PROOF-79 (RULE-33): `feat`'s committed section lists its slow `PROOF-2` as `pass` with `kept` naming the commit `<c>`, and every other result was taken at `HEAD`; `purlin:sign --show` prints only `No sign-off: these results were not taken on this version of the code, <sha7>: feat on Linux/Unix. Run purlin:test --all --commit, then purlin:sign.` and exits 1
- PROOF-80 (RULE-22): A signed package is rewritten with every `\n` as `\r\n` and checked with `purlin:sign --check`; it exits 1 and prints only `The package does not match its fingerprint: the fingerprint matches the content, but the bytes are not in the canonical form.`

The new proofs stand at the end of each spec's `## Proof` section, in number order.

## Lines a person reads

The plan's, as written (K5 and section 6.2):

```
signed/9.9.9: it names a commit that holds no evidence package for 9.9.9, so it is not a sign-off. Delete it: git tag -d signed/9.9.9.
signed/2.1.0: no sign-off of 2.1.0 counts: the commit that added it is not signed. Restore the files as they were signed, or sign this code: purlin:sign --version <version>.
No sign-off: .purlin/evidence/package/2.1.0.json does not match its fingerprint: <why>. Restore it as it was signed, or name a new version: purlin:sign --version <version>.
No tag: git could not write signed/2.1.0: <git's reason>. Fix that, then run purlin:sign again to write it.
signed/2.1.0 is not written yet: jane@acme.com signed 2.1.0 at e0deb2e. Run purlin:sign to write the tag.
  The audit: 34 strong, 4 weak, 2 spot-checked.
```

One I chose. It fills `<why>` in the second line where `HEAD` holds no sign-off file for the
version at all:

```
HEAD holds none
```

So the line reads `signed/2.1.0: no sign-off of 2.1.0 counts: HEAD holds none. Restore the
files as they were signed, or sign this code: purlin:sign --version <version>.`

## Calls I made, for review

1. **PROOF-217 stands, so the stored fingerprint is still checked.** The plan says the stored
   field is not read. PROOF-217 changes only that field and requires the sign-off to stop
   counting. Both hold this way: the package `HEAD` holds must pass `package.check_bytes`, and
   `package_hash` must equal the fingerprint computed from it. That is stricter than the plan's
   words and rewords no proof.
2. **The tag is written late only while the code has not changed** since the commit that added
   the package. Where it has, the run builds a new package and signs afresh, as it did before.
3. **Two addresses are the same signer when they differ only in case.**
4. **Where several sign-offs of a version do not count, the warning gives the oldest one's
   reason.**

## Edits needed in files I do not own

**Lane `surfaces`, `dev/test_states.py` and `dev/test_summary.py`.** Six tests fail on this
branch because they write a tag, or an unsigned sign-off, by hand:

- `test_states.py`: PROOF-168, 169, 170 and PROOF-276, 277
- `test_summary.py`: PROOF-50

The plan rewords 168, 169, 170 and 50 to "signed by the walk". PROOF-276 and 277 keep their
words, and their helper `_signed_with_a_note` must sign for real too: it commits `{}` as the
package and an unsigned sign-off. This helper does all six. I ran it from a scratch file
against this branch and it passes for 168, 170, 276 and 277:

```python
import io
import sign as sign_module          # scripts/review on sys.path

def _signed(made, version, note='no note', email='jane@acme.com',
            proofs=('PROOF-1', 'PROOF-2')):
    """`email` signs `version` at HEAD by the walk, giving `note` at each hand
    check. The signed commit."""
    if not os.path.isdir(os.path.join(made.root, 'tests')):
        _commit_tests(made, *proofs)
        rules = {'PROOF-1': 'RULE-1', 'PROOF-2': 'RULE-2'}
        made.evidence([_entry(proof, rules[proof]) for proof in proofs])
    if not os.path.exists(os.path.join(made.root, '.git', 'signing-key')):
        made.sign_commits(email)
    answers = {'hand': note, 'sign': 'y'}
    out = io.StringIO()
    code = sign_module.walk(made.root, version, out=out,
                            ask=lambda kind, _key, _prompt:
                            answers.get(kind, 'go on'))
    assert code == 0, out.getvalue()
    return made.head()
```

For PROOF-276 and 277 call `_signed(made, '0.1.0', 'the tube is red', QUINN,
proofs=('PROOF-1',))`. `sign_commits` turns `commit.gpgsign` on, so every later commit is
signed too; PROOF-277's four commits pass either way.

**Lane `words`.** Lines that no longer say what the code does, beyond what section 6.7 lists:

- `skills/sign/SKILL.md` line 198, the row for `No tag: git could not write signed/<version>:`.
  It reads `→ Fix what git named, then write the tag: git tag -s signed/<version>`. It should
  read `→ Fix what git named, then run: purlin:sign`.
- `references/purlin_commands.md` line 138, the list of refusals of `scripts/review/sign.py`,
  gains `the committed package not matching its fingerprint`.
- `docs/running-and-evidence.md` lines 443 and 547 and `references/evidence_and_signoff.md`
  lines 32 and 119 say a result or a sign-off holds while commits change "only files under
  `.purlin/`". Each needs "and leave the `tests` setting as it was".
- `references/formats/signature_format.md` now says a second signer whose name is taken gets
  `<signer-slug>-2.json`. `references/glossary.md` line 121 and
  `references/commit_conventions.md` line 95 name `<signer-slug>.json` and stay true.

## Left open

1. **A tag passed over can reach a package's `warnings`.** `package.build` copies the
   payload's warnings, which now hold the line for a tag passed over. Two clones that hold
   different tags would then build different bytes for one commit. It needs a hand-written or
   broken `signed/*` tag at or below the evidence commit. Keeping it out needs the payload to
   hand the two kinds of warning over apart, and `payload.py` is lane `surfaces`'.
2. **A hand-written tag for the version being signed.** `purlin:sign` still goes ahead and adds
   its commit after that tag. The status then reads `not signed`, with the warning that says
   `git tag -d`. After the tag is deleted, `purlin:sign` writes it on the signed commit. No
   decision names a refusal here, so I added none.
3. **Until lane `surfaces` lands**, no rule's strong cell reads `spot-checked` or `out of date`,
   so those two counts read 0. The code reads both words through `summary.AUDIT_WORDS`.
4. **Cost.** Each status now verifies the signature of every sign-off `HEAD` holds, one
   `ssh-keygen` call each. A project with no package folder pays one `git ls-tree`.
5. **`package` PROOF-79 at integration.** The test writes `kept` by hand, as K1 gives it. The
   plan's step 5 runs it once with real runs after lane `evidence` lands.
