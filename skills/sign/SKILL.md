---
name: sign
description: Sign a rule, a feature or every rule that waits for a person, as a signed commit
---

Attest that a rule, its proof, its test, the code its feature lists and what the audit found belong
together. The attestation is a file, and the commit that adds it is signed, so who signed what and
when is in git history. With no argument this skill walks the rules that wait for a person, one at
a time; with a feature or a rule it goes straight there. It works at every gate. At the gate
`signed`, when nothing is left but the tag, the walk ends by writing the signed tag
`signed/<version>`, as `references/hard_gates.md` defines it.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:sign                                    Walk the rules that wait for a person
purlin:sign --release <name>                   The same walk, tagging <name> instead of the stated version
purlin:sign <feature> [RULE-N ...]             Named rules, or every waiting rule of a feature
purlin:sign --all                              Every waiting rule, in one signed commit
purlin:sign <feature> RULE-N --note "<text>"   Sign a hand check: what you saw, in one line
```

Plain language reaches the same place: "what needs my eyes", "sign off on billing". A rule named
by id is signed whatever it waits on: the script refuses nothing a person asks for.

## What the gate decides

| Gate | What this skill does |
|------|----------------------|
| `passed` | The walk and `--note` work on the hand checks. It writes no tag and no evidence package |
| `strong` | The walk and `--note` work on the hand checks. It writes no tag and no evidence package |
| `signed` | Every rule waits for a signature once its tests pass and its audit is strong, and hand checks wait as at the other gates. The walk ends on the tag |

## Step 1: a key to sign with

The script signs with an SSH key, any key. With none set up it prints, and exits 1:

```
No key to sign with. These commands set one up:
  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
  git config gpg.format ssh
  git config user.signingkey ~/.ssh/id_ed25519.pub
```

The `ssh-keygen` line shows only when that key file does not exist. Show the person the commands,
offer to run them, and once they say yes and the commands ran, carry on with the walk.

## Step 2: what waits, and what the audit found for each rule

```
sync_status()
```

Each rule's `left` in the payload is the one kind of work left on it. The walk reads the rules
whose `left` is `to_test_by_hand`, a `@manual` proof a person checks, or `to_sign`, a rule whose
tests and audit are done at the gate `signed`. `Left to do` carries one line for each:

```
2 rules to test by hand: purlin:sign
3 rules to sign: purlin:sign
```

Every other kind is work for another command, named on its own line of `Left to do`. Read what
the audit read and found for a rule before anything is written:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/ai_audit.py" --feature <feature> --rule RULE-N
```

It carries the rule text, the proof text, the test body, the test strength beside
`min_strength`, and what the last audit found, with the model that found it. It reports; it
recommends nothing, so the judgment is yours. Judge it against `references/review_criteria.md`,
which is the one place the criteria live. Signing a rule you have not read is the one thing
this skill must not help with.

## Step 3: walk it

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py"
```

With no argument the script opens on those two lines, or on
`Nothing is waiting for someone to test by hand or to sign.`, then shows each rule, its proofs
and what the audit found, and asks for one answer, `sign / case / skip`. Signing a hand check
asks `What did you see, in one line:`; ask the person, and the line becomes the signature's note.
An empty line signs it with no note. It writes nothing until the walk closes; then one signed
commit carries the signatures.

## Step 4: the three answers

**Sign.** The rule, the proof and the test belong together.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py" <feature> RULE-N [RULE-M ...]
```

Add `--note "<text>"` for a hand check, so the note says what was seen.

**Add a case.** The person says in plain language what is missing: "it should also reject an
expired token". Write it into the spec as a new proof line with the next free proof id, leave
the test for the next `purlin:build`, and move on. This skill writes specs and signatures,
never code.

**Skip.** Move to the next rule and leave it as it is. A skipped rule waits again next time:
nothing is marked as seen by being seen.

Never narrow a rule or a proof to make an observation disappear. That lowers the claim instead of
strengthening the evidence, and on a rule that comes from an anchor it is not yours to change:
the change is a pull request against the anchor's source repository.

## Step 5: when a signature counts

The script writes one file per rule under `specs/<category>/<feature>.signatures/`, one per
feature an anchor's rule applies to, and makes one signed commit for all of them. Each file
records the signer's email and name as git holds them and the key's fingerprint. The commit
subjects come from `references/commit_conventions.md`.

| A signature counts when | What ends it |
|-------------------------|--------------|
| The last commit that touched the file is signed, with any key | An unsigned commit: `the commit that added it is not signed` |
| It is still made over the rule, the proof, the test, the code its feature lists, what the audit found and the machine each system's tests ran on | A change to any of them; the rule is `to sign` again |

Nothing else is read, at any gate: the signature counts whoever wrote it, whoever last committed
to the test file, and on whatever branch carries it. A first run on a new system ends nothing.
When it has signed, the script prints `Signed 3 rules as jane@acme.com with the key ending ...Xy4Q.`

## Step 6: the version and the tag

At the gate `signed`, when nothing is left but the tag, the script writes the evidence package
`.purlin/evidence/package/<version>.json`, commits it as a signed commit, and writes a signed tag
(`git tag -s`) on that commit. The version is read from the `VERSION` file, then `package.json`,
then `pyproject.toml`, then the first `*.csproj` at the root; `--release <name>` names another.
Then it prints:

```
Evidence package committed: .purlin/evidence/package/1.4.0.json.
Tagged signed/1.4.0 at a1b2c3d.
Nothing left to do. Push the tag to release it: git push origin signed/1.4.0
```

While other work is left it prints the summary and `Left to do` instead. It writes no tag while
the working tree or any feature's results are not committed, and none over a tag that exists.
With no version stated it prints `No version: nothing in this project states one.`: ask the
person for the version, offer to write it to a `VERSION` file at the root, and run the walk
again, or pass `--release <version>`. Below `signed` it writes no tag and no package. Pushing the
tag is a person's act; this skill never pushes.

## Step 7: close the walk and name the next step

The walk closes with what happened, then ends on the summary or on what the tag printed:

```
Walked 12 rules: 8 signed, 1 case added, 3 skipped.
  billing RULE-2   add this proof line: reject an expired token
Signed 8 rules as jane@acme.com with the key ending ...Xy4Q.
Commits: a1b2c3d
```

| What it ended on | The line to print |
|------------------|-------------------|
| A case was added | `→ Run: purlin:build <feature>` |
| `Left to do:` and its lines | `→ Run:` the command on its first line |
| `Nothing left to do. Push the tag to release it: git push origin signed/<version>` | `→ Run: git push origin signed/<version>` |
| `No tag: <feature> has results that are not committed.` | `→ Run: purlin:test --commit` |
| `No tag: the working tree holds changes that are not committed` | `→ Commit them, then run: purlin:sign` |
| `No version:` | `→ Write the version the person gives to VERSION, then run: purlin:sign` |
| `No key to sign with.` | `→ Run the commands it printed, then run: purlin:sign` |
| `Nothing left to do.` | Nothing: the work at this gate is done |
