# Regulated workflow

For a team working under GxP or a similar obligation, at the `signed` gate.

`signed` is `strong` plus two things: a rule that needs a signature needs a current signature
from someone on the signer list, in a signed commit; and the version carries the tag
`purlin:sign` writes once every rule meets the gate. Nothing else about the day changes, so
read [team-workflow.md](team-workflow.md) first and treat this as what it adds.
[how-purlin-works.md](how-purlin-works.md) is the model in one page.

The whole of it runs on one machine. A project at this gate with no CI anywhere is the ordinary
case: you spec, build, test and audit locally, a person signs, `purlin:sign` writes the tag,
and a person pushes it.

## The three levels

A rule carries a spec status and one cell per level, and the gate says how many cells exist. At
`signed` all three do.

| Level | The question it answers | The command that answers it |
|-------|-------------------------|-----------------------------|
| passed | did every tagged test for this rule pass? | `purlin:test`, and the same tests on CI |
| strong | are those tests worth trusting? | `purlin:audit`, and the same audit on CI |
| signed | did a person say the rule, the proof and the test belong together? | `purlin:sign` |

Which machine ran them does not change at this gate. A record your own `purlin:audit`
committed counts here exactly as it does at `strong`, under `.purlin/records/local/` with its
briefs beside it. What decides whether that is enough is the trust setting: answer `y` to
`Do you trust your own machine for the tests and the signing?` and it is, answer `n` and
`purlin:sign` asks for a `ci` run at this commit before it signs anything.

Level 2 is fully automatic: the breaks and the AI audit run without anyone asking. A person
first appears at level 3, and this is where in a change's life they appear.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#0C3444", "primaryColor": "#092936", "primaryTextColor": "#E4DDD4", "primaryBorderColor": "#C0793F", "lineColor": "#C0793F", "secondaryColor": "#0C3444", "tertiaryColor": "#092936", "fontFamily": "Arial", "textColor": "#E4DDD4"}}}%%
sequenceDiagram
    actor Engineer
    participant Tree as the checkout
    actor Signer
    participant Origin as origin
    Engineer->>Tree: purlin:spec, purlin:build, purlin:test
    Engineer->>Tree: purlin:audit
    Tree->>Tree: purlin: record for sha7, with the briefs beside it
    Signer->>Tree: purlin:sign walks Review, then Sign, one brief at a time
    Tree->>Tree: git commit -S writes RULE-4.hash8.slug.json
    Tree->>Tree: every rule meets the gate, so the tag signed/1.4.0 is written
    Signer->>Origin: git push, then git push origin signed/1.4.0
```

The whole of what `signed` adds is the lower half of that picture. A person reads what the
audit wrote in the briefs, commits one file per rule signed, and `purlin:sign` closes by
writing the tag. Nothing in the picture pushes but a person, and the push is free: nothing runs
when they make one.

A change that leaves a rule's text, its proof and its test alone leaves that rule's signature
standing. A change that touches one of the three stales it, and so does a re-audit that
observes something new, because the signature binds what the audit saw as well. Until a
signature for the new evidence exists, `purlin:sign` writes no tag and the gate check says
`To sign`.

Stale and `code changed` are the two answers to "something changed", and the difference is what
changed. A record carries `scope_tree`, the git tree hash of the files the spec's `> Scope:`
line names. When the code under that scope changed and the rule, proof and test text did not,
the signature stands and the passed cell reads `code changed`; CI clears it on the next run and
nobody is asked to look. When the rule text, the proof text, the test body or the rule's bar
changed, the signature is stale, because the attestation was given about text that no longer
exists. Raising a rule's bar changes what signing it meant, which is why the bar sits
inside the hashes a signature binds.

## What the gate requires

| Requirement | How it is met |
|-------------|---------------|
| A record at this commit for every rule | `purlin:audit`, run by anyone. Under `trust: remote` a `ci` record as well |
| Every operating system the rule's proofs name covered by a passing run | this machine, plus a runner for any `@env` it is not. A rule that passed on some and not others reads `partial`, which is not met |
| Test strength at or above `min_strength` | default 80 at this gate |
| A current signature on every rule that needs one | `purlin:sign` |
| Every rule tagged with a bar and an origin | the bar defaults to the gate; the origin is required at this gate |
| The signing commit signed, by an author on the signer list who did not last touch the test | `signers` in `.purlin/config.json`, read as it stood in that commit |
| The tag `signed/<version>` on the commit | `purlin:sign` writes it once every rule meets the gate, and a person pushes it |

`scripts/ci/gate_check.py --check` is the check itself. `purlin:sign` runs it before it writes
a tag, and a runner runs it as the last step of every run. It prints one section per kind of
work, `Not passed (n)`, `Partial (n)`, `Weak (n)`, `Not audited (n)`, `To review (n)` and
`To sign (n)`, each naming the rules the cell that blocks them puts there and the reason that
cell carries; it names the first twenty in a section and counts the rest. Its own lines, the
gate, the counts and the last word on whether the gate held, open with `gate:`; the rules under
a section heading are indented instead. It writes nothing, exits 0 when the gate is met and 1
when it is not, and exits 2 when it cannot read the evidence, so an unreadable checkout never
passes. `purlin:status` reads the same cells and ends with one `→ Next:` line naming the step
that clears the most rules.

## The signer list

`signers` in `.purlin/config.json` holds the emails of the people who may sign:

```json
"signers": ["jane@acme.com", "sam@acme.com"]
```

It changes by pull request like any other file, so git history records who could sign and when,
and a signature is judged against the list as it stood in the commit that added it. Add and
remove people at any time. There is no setting to configure on the git host, no owners file,
and no minimum number of people: one QA person is a working list.

`purlin:init --gate signed` asks for the emails. Without a list the gate cannot be met:
`purlin:status` and the gate check both print
`→ signer list missing: run purlin:init --gate signed`, and the check exits 1.

## The signed commit

Each signer runs these three commands once, on the machine they sign from:

```bash
git config gpg.format ssh
git config user.signingkey ~/.ssh/id_ed25519.pub
git config commit.gpgsign true
```

Then they upload the same public key to the git host as a signing key, so the host shows the
commit as signed. `purlin:init --gate signed` prints this for each person on the list.

`purlin:sign` writes one file per rule and makes one `git commit -S` whether it carries one
rule or forty. Its subject is `sign(<feature>): RULE-N ...` for one feature and
`sign(batch): <feature> RULE-N, ...` across several; a hold commit reads `hold(<feature>):
RULE-N`. It does not push. The signer runs `git push`, and `git push origin signed/<version>`
for the tag.

A signature counts when these hold. Each is read from git or from a file, never asserted:

1. The commit that added the signature file is signed and the signature verifies.
2. The author's email is on the signer list as of that commit.
3. That author is not the author of the commit that last touched the test. Write the test or
   sign it, not both.
4. The hashes the file binds still match the current rule text, proof text, test body and bar.
5. What the audit observed about the rule is still what it observed when the file was written:
   the strength, the observation sentences and whether the audit settled. A re-audit that sees
   something different stales the signature, because the person attested to what they were
   shown.
6. Under `signed`, the commit is an ancestor of **the protected branch**, the branch the
   project works from, which Purlin reads from what `origin/HEAD` points at, falling back to
   the branch the checkout is on and then to `main`. A signature living only on a side branch
   nobody merged is not evidence about the code anyone runs.

Below `signed` a signature from anyone counts, because what it clears there is a question the
machine could not settle rather than an attestation the gate rests on.

## The tag

```
purlin:sign
```

With no argument it walks Review, then Sign. When it leaves every rule meeting the gate it
writes an annotated tag over the current commit: `signed/<version>`, from the `VERSION` file at
the project root, or `--release <name>` where a release carries its own name. The message names
the commit and the gate. Then it prints `→ Run: git push origin signed/<version>`.

No tag is written while any rule falls short, so the presence of the tag is the claim. A tag
holds the whole tree at that commit: the code, every record, every brief and every signature,
pinned together under one name. That is what an inspection is handed, and it is why no record
needs pinning of its own.

A tag of that name that already exists is not moved. A released version's marker stays where it
was put.

## The bar, origin and `sign_at`

Every rule has a **bar**, `passed` or `strong`: the evidence that rule must have before anyone
can sign it. A rule says its own with the tag `[bar: passed]` or `[bar: strong]`; a rule with
no tag takes the project's gate as its bar, which at this gate is `strong`. Before 0.10.0 a
rule carried a three-level tag in place of a bar; `purlin:init --update` rewrites it, the two
higher levels to `[bar: strong]` and the lowest to `[bar: passed]`.

The bar decides three things:

| The bar | The evidence it asks for | Does the AI audit run? | Does it need a signature? |
|---|---|---|---|
| `passed` | the rule's tagged tests pass on every platform a counting run covered | no | only when `sign_at` is `all` |
| `strong` | all of that, an audit, the strength floor, nothing the audit observed outstanding, no hold | yes | yes |

A rule that has met its bar has **cleared** it. A rule that has cleared its bar, needs a
signature and has none that counts is **signable**: the board's `Signable` column counts it,
the `To sign` card counts it for the project, and the Sign tab lists it until someone signs
it. A rule meets the gate `signed` when it has cleared its bar and, where it needs a
signature, that signature counts.

`sign_at` says which rules need a signature at all. `strong`, the default, asks for one on the
rules whose bar is `strong`; `all` asks for one on every rule. `purlin:init --gate signed`
asks which you want, and `--update` asks again.

Origin is `pm`, `design`, `qa` or `eng`. `purlin:init --gate signed` lists every rule that
carries no origin when you raise the gate, and `purlin:spec <feature>` tags them in one pass.

## What a machine writes, and what it never writes

`purlin:audit` writes two kinds of file and commits them as `purlin: record for <commit7>`:

- **the records**, under `.purlin/records/local/<feature>/`, one per feature per run;
- **the briefs**, under `.purlin/briefs/local/<feature>/<RULE-N>.<hash8>.brief.json`, one per
  rule the audit reached.

A remote runner writes the same two under `ci/`. **No machine writes a signature file, ever.** A
signature directory holds only files a person wrote. That is the whole of what makes the trail
worth reading: the machine's evidence and a person's attestation are written by different
hands, into different paths.

Where a project has a runner, a push of the `signed/**` tag starts one last run: it reruns the
tagged tests on a clean machine, recomputes the hashes of every committed record, brief and
signature against the tagged code, checks that every file under `ci/` was committed by the
runner's own identity, and ends with the gate check. It commits nothing. A red run there is the
host's word that this version is not proven.

## `@manual` proofs

Some claims cannot be observed by a test: the tone of an error message against a brand voice
guide, a printed label read by eye, a physical step. Tag the proof `@manual`:

```
- PROOF-4 (RULE-4): Read the error messages against the brand voice guide @manual
```

There is no test and no break measurement. The strong cell reads `manual test` with the
reason `manual proof`, and the rule waits on the Review list. The evidence is a signature carrying a
one-line note saying what the person did and what they saw:

```
purlin:sign <feature> RULE-4 --note "read the four messages on 2026-09-16; each matches the guide"
```

A rule whose bar is `strong` and on whose code no audit has run yet reads `not audited`, with
the reason `no audit has run on this code`. It waits for `purlin:audit`, not for a person, so
it is on no tab. Once the audit has run and could not settle the question, the cell reads
`unsettled` and the rule is on the Review list. The same `--note` settles it.

## Holds

A hold is a person's committed statement that the test does not prove the proof, with the
missing case named:

```
purlin:sign <feature> RULE-3 --hold "the lock expiry is never read"
```

It writes `specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<holder-slug>.hold.json` and
commits it, signed like any other `purlin:sign` commit. A hold only ever withholds, so the
person who writes one need not be on the signer list. While the hold is current both the strong
cell and the signed cell read `held`, whatever the bar and whatever the tests do, so no rule
slips past level 2 on the measurements alone. Changing the test ends the hold, because the
hashes it binds no longer match. A signature by a person for the current hashes outranks it.

## The evidence trail

Everything an inspection asks for is already in git, in four places, and nobody assembles it by
hand:

- **`.purlin/records/`.** One file per audit run per feature, each naming the commit it
  observed, the operating system, the gate in force, the test strength and every proof's
  result. The folder it sits in is its source, `local/` or `ci/`, and the git history of both
  is the log of what was proven and when.
- **`.purlin/briefs/`.** One file per rule per set of hashes: the strength beside the minimum
  and what the audit observed, in the sentences the audit wrote. It is what a signer was shown,
  and the signature binds it.
- **`specs/<category>/<feature>.signatures/`.** One file per signature, binding the hashes of
  the rule, the proof and the test, the bar at the time, what the audit observed, the signer's
  email, the brief they read and the record they rested on. The commit that added it is signed
  by a person.
- **`refs/tags/signed/*`.** The annotated tag on each version that met the gate. A tag holds
  the whole tree, so one name reaches the code and every file above.

Add `.purlin/config.json`'s history for who could sign at any date, and the four questions an
inspection asks - what was required, what the tests proved, who said it was right, and when -
each have a file that answers them.

For anyone without a checkout,
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report/scan.py" --repo <url> --ref <tag>` reads
`specs/`, `.purlin/tests/` and `.purlin/records/` by sparse fetch and prints the same rollup for
any branch or tag, including a `signed/<version>` one.

## Branch rules

There are none, and Purlin asks for none. A push is free, to any branch, for anyone, and
nothing runs at push time. What an inspection reads is not who was allowed to push: it is the
signed commit behind each signature, the runner's own identity on each file under `ci/`, and
the tag that says every rule met the gate at one commit.

## The day to day

The engineer's loop is unchanged: `purlin:drift eng`, `purlin:spec`, `purlin:build`,
`purlin:test`, `purlin:audit`, push. QA's loop is `purlin:sign`, described in
[review-and-signing.md](review-and-signing.md). What changes is the last step: a person signs,
`purlin:sign` writes the tag, and a person pushes it.

Read next: [review-and-signing.md](review-and-signing.md) for the walk and what stales a
signature, [raising-the-gate-and-upgrading.md](raising-the-gate-and-upgrading.md) for the move
to this gate, [running-and-records.md](running-and-records.md) for records and test strength in
detail.
