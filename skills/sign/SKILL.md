---
name: sign
description: Walk the review list, or sign a rule, a feature or a batch as a signed commit
---

Attest that a rule, its proof and its test belong together. The attestation is a file, and the
commit that adds it is signed, so who signed what and when is in git history. With no argument
this skill walks the review list, which is the Review list and then the Sign list, one brief at
a time; with a feature or a rule it goes straight there. When every rule meets the gate the walk
ends by writing the tag `signed/<version>`, which is the marker that this version is proven.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:sign                                    Walk the review list, one brief at a time
purlin:sign --release <name>                   The same walk, tagging <name> instead of the VERSION file's value
purlin:sign <feature> [RULE-N ...]             One rule, several rules, or a whole feature
purlin:sign --batch                            Everything currently signable
purlin:sign <feature> RULE-N --hold "<case>"   Hold a rule: the test does not prove the proof
purlin:sign <feature> RULE-N --note "<text>"   Sign a @manual proof, or settle what the audit could not
```

Plain language reaches the same place: "what needs my eyes", "sign off on billing", "hold
login rule 3". A narrowing argument never adds a rule the full walk would skip.

## What the gate decides

| Gate | What this skill does |
|------|----------------------|
| `passed` | Prints that the gate asks for no signature, names what `purlin:init --gate strong` adds — the test strength, the AI audit and the review list — and stops without writing anything |
| `strong` | The walk, `--note` and `--hold` work. A bare signature says a signature is required only under the gate `signed`, then writes it anyway |
| `signed` | Every form works, and every rule that needs a signature has to carry one before it meets the gate: `sign_at: strong` asks on the rules whose bar is `strong`, `sign_at: all` on every rule |

## Step 1: the list, and the brief behind each rule

```
sync_status()
```

There are two lists and the walk reads them in this order. `payload.review_list` is the
**Review list**: the rules whose `strong` cell reads `manual test`, `unsettled` or `held`, at
the gate `strong` and above. `payload.sign_list` is the **Sign list**: the signable rules, the
ones that have cleared their bar and need a signature they do not have, at the gate `signed`.
Both are already ordered, the rules whose bar is `strong` first, then by feature and rule
number. The dashboard shows the same two as its Review tab and its Sign tab; `tab` is the
page's word and `list` is this one's.

A rule blocked lower down — no test, a failing test, a weak one — is build work, so it stays
on the board and never on either list. So is a rule reading `not audited`: what moves that
one is `purlin:audit`. The walk opens with one line holding both counts:

```
Review: 7 rules. Sign: 5 rules.
```

Read the brief for a rule before anything is written:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/brief.py" --feature <feature> --rule RULE-N
```

It carries the rule text, the proof text, the test body, the test strength beside
`min_strength`, what the audit observed and whether it settled, and for an `[origin: design]`
rule the pinned mock beside the capture the test took.
It reports; it recommends nothing, so the judgment is yours. Judge it against
`references/review_criteria.md`, which is the one place the criteria live. Signing a rule you
have not read is the one thing this skill must not help with.

## Step 2: walk it

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py"
```

With no argument the script does the walk: it renders each brief in turn and asks for one
answer, `sign / case / hold / skip`. It writes nothing until the walk closes; then one signed
commit carries the signatures and one more per feature carries the holds.

## Step 3: the four answers

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

**Hold.** The test does not prove the proof as written, and no new proof line would fix it.
Name the missing case in words and commit it, so the rule cannot reach `strong` or `signed`
while the hold stands. A holder need not be on the signer list:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py" <feature> RULE-N --hold "<the missing case>"
```

**Skip.** Move to the next rule and leave the cells alone. A skipped rule is on the list again
next time, which is the intended behaviour: nothing is marked as seen by being seen.

Never narrow a rule or a proof to make a finding disappear. That lowers the claim instead of
strengthening the evidence, and on a rule that comes from an anchor it is not yours to change:
`purlin:anchor propose <name>` drafts that change where the rule lives.

## Step 4: when a signature counts

The script writes one file per rule under `specs/<category>/<feature>.signatures/` and makes
one signed commit for all of them. A hold is written the same way, with `.hold.json` at the
end of the name. The commit subjects come from `references/commit_conventions.md`:
`sign(<feature>): RULE-N ...`, `sign(batch): <feature> RULE-N, ...` and
`hold(<feature>): RULE-N ...`.

| The signature counts when | What fails it |
|---------------------------|---------------|
| The commit that added the file is signed and the host verifies it | `the signing commit is not signed` |
| The author's email is on `signers` in `.purlin/config.json` as of that commit | `the signer is not on the list` |
| That author did not author the last commit to the test file | `the signer last touched the test` |
| The bound rule, proof and test hashes and the rule's bar still match | `hashes changed after the signature` |
| What the audit observed about the rule is still what it observed when you signed | `hashes changed after the signature` |
| Under `signed`, the commit is on the protected branch | `the signing commit is not on <branch>` |

The script checks the list itself and stops before writing. Under `signed` with no list it
prints `sign: signer list missing: run purlin:init --gate signed`; with an email that is not
on it, `sign: <email> is not on the signer list. Add it by pull request, or ask someone on
it.` Read both back as they came. `references/hard_gates.md` defines the three gates once; do
not restate them elsewhere.

## Step 5: the tag, and trust

A signature locks one rule. The tag locks the version: it is the marker that every rule met the
gate at this commit, and the one thing a person pushes to say so.

When the walk leaves every rule meeting the gate, the script writes an annotated tag over the
current commit, named `signed/<version>` from the `VERSION` file at the project root, or the
config's `version` where there is no such file; `--release <name>` overrides the name. The
message names the commit and the gate. Then it prints:

```
Tag written: signed/1.4.0
→ Run: git push origin signed/1.4.0
```

No tag is written while any rule falls short, and the run says which rules do. A tag of that
name that already exists is not moved: the script says so and writes nothing, so a released
version's marker cannot be pointed somewhere else. Pushing the tag is a person's act; this
skill never pushes.

`trust` in `.purlin/config.json` is `local` or `remote`, and `purlin:init` asks for it. Under
`local`, the default, this machine's runs are the evidence: sign, tag, push, and a project
needs no runner at all. Under `remote` a signature rests on a run this machine did not make,
so the script refuses a rule whose passed cell holds no `ci` entry for the current commit:
`sign: <feature> RULE-N has no ci test run for this commit; run purlin:test --remote first`.

## Step 6: close the walk and name the next step

The walk closes with what happened and the commits it made:

```
Walked 12 rules: 8 signed, 1 case added, 0 held, 3 skipped.
  billing RULE-2   add this proof line: reject an expired token
Commits: a1b2c3d
```

| What you left | The line to print |
|---------------|-------------------|
| A case was added | `→ Run: purlin:build <feature>` |
| Rules still on either list | `→ Run: purlin:sign` |
| Nothing left, and the tag was written | `→ Run: git push origin signed/<version>` |
| Nothing left, and a rule still does not meet the gate | `→ Run: purlin:status` |
| A rule you may not sign | `→ Ask someone on the signer list.` |
| A rule with no `ci` run under `trust: remote` | `→ Run: purlin:test --remote` |
| The commit was not signed | `→ Set up signing: purlin:init --gate signed prints the three commands.` |
