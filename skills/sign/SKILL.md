---
name: sign
description: Walk the review list, or sign a rule, a feature or a batch as a signed commit
---

Attest that a rule, its proof and its test belong together. The attestation is a file, and the
commit that adds it is signed, so who signed what and when is in git history. With no argument
this skill walks the review list one brief at a time; with a feature or a rule it goes straight
there.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:sign                                    Walk the review list, one brief at a time
purlin:sign <feature> [RULE-N ...]             One rule, several rules, or a whole feature
purlin:sign --batch                            Everything currently signable
purlin:sign <feature> RULE-N --hold "<case>"   Hold a rule: the test does not prove the proof
purlin:sign <feature> RULE-N --note "<text>"   Sign a @manual proof, or settle what the model could not
```

Plain language reaches the same place: "what needs my eyes", "sign off on billing", "hold
login rule 3". A narrowing argument never adds a rule the full walk would skip.

## What the gate decides

| Gate | What this skill does |
|------|----------------------|
| `passed` | Prints that the gate asks for no signature, names what `purlin:init --gate strong` adds — the test strength, the free checks on the test body, the model review and the review list — and stops without writing anything |
| `strong` | The walk, `--note` and `--hold` work. A bare signature says a signature is required only under the gate `signed`, then writes it anyway |
| `signed` | Every form works, and every rule whose risk is at or above `sign_at` needs a signature before it meets the gate |

## Step 1: the list, and the brief behind each rule

```
sync_status()
```

`payload.review_list` is the list, already ordered: risk high first, and within a risk the
stale and the held before the rest. A rule reaches it when its `strong` cell reads `needs a
person`, or its `signed` cell reads `unsigned`, `stale` or `held`. A rule blocked lower down —
no test, a failing test, a weak one — is build work, so it stays on the board and never on
this list. Print the count by risk and the first five rows.

Read the brief for a rule before anything is written:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/brief.py" --feature <feature> --rule RULE-N
```

It carries the rule text, the proof text, the test body, the test strength beside
`min_strength`, the free-check findings, what the model review observed and whether it
settled, and for an `[origin: design]` rule the pinned mock beside the capture the test took.
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
model review could not settle the question and you settled it yourself.

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
| The bound rule, proof, test and risk hashes still match | `hashes changed after the signature` |
| Under `signed`, the commit is on the protected branch | `the signing commit is not on <branch>` |

The script checks the list itself and stops before writing. Under `signed` with no list it
prints `sign: signer list missing: run purlin:init --gate signed`; with an email that is not
on it, `sign: <email> is not on the signer list. Add it by pull request, or ask someone on
it.` Read both back as they came. `references/hard_gates.md` defines the three gates once; do
not restate them elsewhere.

## Step 5: close the walk and name the next step

The walk closes with what happened and the commits it made:

```
Walked 12 rules: 8 signed, 1 case added, 0 held, 3 skipped.
  billing RULE-2   add this proof line: reject an expired token
Commits: a1b2c3d
```

| What you left | The line to print |
|---------------|-------------------|
| A case was added | `→ Run: purlin:build <feature>` |
| Rules still on the list | `→ Run: purlin:sign` |
| Nothing left, gate `signed` | `→ Open the pull request.` |
| Nothing left, gate `strong` | `→ Run: purlin:status` |
| A rule you may not sign | `→ Ask someone on the signer list.` |
| The commit was not signed | `→ Set up signing: purlin:init --gate signed prints the three commands.` |
