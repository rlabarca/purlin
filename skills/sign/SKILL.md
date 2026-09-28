---
name: sign
description: Walk the queue, or sign a rule, a feature or a batch as a signed commit
---

Attest that a rule, its proof and its test belong together. The attestation is a file, and the
commit that adds it is signed, so who signed what and when is in git history. With no argument
this skill walks the queue, the one list of the rules that wait on a person, one rule at a time;
with a feature or a rule it goes straight there. When every rule meets the gate the walk ends by
writing the signed tag `signed/<version>`, the marker that this version is proven, as
`references/hard_gates.md` defines it.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:sign                                    Walk the queue, one rule at a time
purlin:sign --release <name>                   The same walk, tagging <name> instead of the VERSION file's value
purlin:sign <feature> [RULE-N ...]             One rule, several rules, or a feature's rules in the queue
purlin:sign --batch                            Every rule in the queue, in one signed commit
purlin:sign <feature> RULE-N --note "<text>"   Sign a hand check: what you saw, in one line
```

Plain language reaches the same place: "what needs my eyes", "sign off on billing". A narrowing
argument never adds a rule the full walk would skip.

## What the gate decides

| Gate | What this skill does |
|------|----------------------|
| `passed` | Prints that the gate asks for no signature, names what `purlin:init --gate strong` adds — the test strength, the AI audit and the queue — and stops without writing anything |
| `strong` | The walk and `--note` work. A bare feature and `--batch` sign every hand check in the queue; a named rule that is not in it is told a signature is required only under `signed`, then written anyway |
| `signed` | Every form works; a bare feature and `--batch` read the queue, hand checks and signatures alike. Every rule whose level is `signed` has to carry a signature before it meets the gate; a named rule marked `[level: passed]` or `[level: strong]` is refused, because it asks for none |

## Step 1: the queue, and the brief behind each rule

```
sync_status()
```

`payload.queue` is the **queue**, ordered by feature and then rule number. Each row says what
the rule needs. A `hand check` is a rule whose `strong` cell reads `manual test` or
`unsettled`, at the gate `strong` and above: a person checks it and signs with a note. A
`signature` is a rule whose level is `signed`, whose tests and audit are met and that has no
counting signature, at the gate `signed`. A rule that needs both is one row, `hand check`. Each
row carries the command that answers it. The dashboard shows the same rows on its Queue tab.

A rule blocked lower down — no test, a failing test, a weak one — is build work, so it stays
on the board and never in the queue. So is a rule reading `not audited`: what moves that one is
`purlin:audit`. So is a rule whose level is `passed`: it meets the gate on its tests. The walk
opens with one line holding the counts:

```
Queue: 5 rules. 2 hand checks, 3 signatures.
```

Read the brief for a rule before anything is written:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/brief.py" --feature <feature> --rule RULE-N
```

It carries the rule text, the proof text, the test body, the test strength beside
`min_strength`, and what the audit observed and whether it settled.
It reports; it recommends nothing, so the judgment is yours. Judge it against
`references/review_criteria.md`, which is the one place the criteria live. Signing a rule you
have not read is the one thing this skill must not help with.

## Step 2: walk it

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py"
```

With no argument the script does the walk: it shows each rule, its proofs and what the audit
found, and asks for one answer, `sign / case / skip`. Signing a hand check asks
`What did you see, in one line:` and the line becomes the signature's note. It writes nothing
until the walk closes; then one signed commit carries the signatures.

The script signs nothing over evidence that is not committed. A rule whose feature has evidence
written and not committed is refused, and so is the tag, with
`sign: <feature> has evidence that is not committed. Run: purlin:test --commit`.

## Step 3: the three answers

**Sign.** The rule, the proof and the test belong together.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py" <feature> RULE-N [RULE-M ...]
```

Add `--note "<text>"` when the proof is `@manual`, so the note is the evidence, or when the
audit could not settle the question and you settled it yourself.

**Add a case.** The person says in plain language what is missing: "it should also reject an
expired token". Write it into the spec as a new proof line with the next free proof id, leave
the test for the next `purlin:build`, and move on. This skill writes specs and signatures,
never code.

A reviewer who finds the test does not prove the proof adds the missing case, or changes the
proof, alone or with AI help.

**Skip.** Move to the next rule and leave the cells alone. A skipped rule is in the queue again
next time, which is the intended behaviour: nothing is marked as seen by being seen.

Never narrow a rule or a proof to make an observation disappear. That lowers the claim instead of
strengthening the evidence, and on a rule that comes from an anchor it is not yours to change:
the change is a pull request against the anchor's source repository.

## Step 4: when a signature counts

The script writes one file per rule under `specs/<category>/<feature>.signatures/` and makes
one signed commit for all of them. Each file names the signer, the machine it was made on and
that machine's operating system. The commit subjects come from
`references/commit_conventions.md`: `sign(<feature>): RULE-N ...` and
`sign(batch): <feature> RULE-N, ...`.

| Under `signed` the signature counts when | What fails it |
|------------------------------------------|---------------|
| The commit that added the file is signed and the signature verifies | `the signing commit is not signed` |
| Its bound hashes still match the rule, the proof, the test and what the audit found | `hashes changed after the signature` |

Nothing else is read. Signing is logged, not policed: the signature counts whoever wrote it,
whoever last committed to the test file, and on whatever branch carries it. Below `signed` a
committed signature counts. `references/hard_gates.md` defines the gates and the tag once; do
not restate them elsewhere.

## Step 5: the tag, and trust

A signature locks one rule. The tag locks the version: it is the marker that every rule met the
gate at this commit, and the one thing a person pushes to say so.

When the walk leaves every rule meeting the gate, the script writes a signed tag (`git tag -s`,
with the key you sign commits with) over the current commit, named `signed/<version>` from the `VERSION` file at the project root, or the
config's `version` where there is no such file, or `signed/unversioned` where neither names
one; `--release <name>` overrides the name. The message names the commit and the gate. Then it
prints:

```
Tagged signed/1.4.0 at a1b2c3d: every rule meets the gate signed.
→ Run: git push origin signed/1.4.0
```

While any rule falls short it writes no tag and prints
`No tag: <n> of <m> rules do not meet the gate <gate>.` A tag of that name that already exists
is not moved: it prints `No tag: signed/1.4.0 is already written. Name another with --release
<name>.`, so a released version's marker cannot be pointed somewhere else. Pushing the tag is a
person's act; this skill never pushes.

`trust` in `.purlin/config.json` is `local` or `remote`, and `purlin:init` asks for it. Under
`local`, the default, this machine's runs are the evidence: sign, tag, push, and a project
needs no runner at all. Under `remote` a signature rests on a run this machine did not make,
so the script refuses a rule whose passed cell holds no `ci` entry for the current commit:
`sign: <feature> RULE-N has no ci test run for this commit; run purlin:test --remote first`.

## Step 6: close the walk and name the next step

The walk closes with what happened and the commits it made:

```
Walked 12 rules: 8 signed, 1 case added, 3 skipped.
  billing RULE-2   add this proof line: reject an expired token
Commits: a1b2c3d
```

| What you left | The line to print |
|---------------|-------------------|
| A case was added | `→ Run: purlin:build <feature>` |
| Rules still in the queue | `→ Run: purlin:sign` |
| Evidence not committed | `→ Run: purlin:test --commit` |
| Nothing left, and the tag was written | `→ Run: git push origin signed/<version>` |
| Nothing left, and a rule still does not meet the gate | `→ Run: purlin:status` |
| A rule with no `ci` run under `trust: remote` | `→ Run: purlin:test --remote` |
| The commit was not signed | `→ Set up signing: purlin:init --gate signed prints the three commands.` |
