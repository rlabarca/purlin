---
name: sign
description: Sign a rule, a feature or every rule that waits for a person, as a signed commit
---

Attest that a rule, its proof, its test, the code its feature lists and what the audit found belong
together. The attestation is a file, and the commit that adds it is signed, so who signed what and
when is in git history. With no argument this skill walks the rules that wait for a person; with a
feature or a rule it goes straight there. At the gate `signed`, when nothing is left but the tag,
the walk ends by writing the signed tag `signed/<version>`, as `references/hard_gates.md` defines
it.

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
purlin:sign <anchor> RULE-N --does-not-apply "<why>"  Sign a pinned anchor's rule as not applying to this project
```

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

Call `sync_status` with `project_root` set to the project root, the top folder of the git checkout.
Each rule's `left` in the payload is the one kind of work left on it. The walk reads the rules
whose `left` is `to_test_by_hand`, a `@manual` proof a person checks, `to_confirm`, a pinned
anchor's rule whose signature as not applying ended, or `to_sign`, a rule whose tests and audit are
done at the gate `signed`, each on a line of `Left to do` such as `3 rules to sign: purlin:sign`.
Every other kind is work for another command, named on its own line of `Left to do`. Read what the
audit read and found for a rule before anything is written:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/review/ai_audit.py" --feature <feature> --rule RULE-N
```

It carries the rule text, the proof text, the test body, the test strength beside `min_strength`,
and what the last audit found. Judge it against `references/review_criteria.md`. Signing a rule you
have not read is the one thing this skill must not help with.

## Step 3: walk it

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py"
```

With no argument the script opens on those lines, then shows each rule, its proofs and what the
audit found, and asks for one answer, `sign / case / skip`. Under each proof that is not
`@manual` it shows the test tied to it, `    tied to tests/test_login.py::test_valid_credentials_return_200`,
or `    tied to no test`: read that test before you answer. With nothing waiting it prints
`Nothing is waiting for someone to test by hand or to sign.` Signing a hand check asks
`What did you see, in one line:`; the person's line becomes the signature's note, and an empty line
signs it with none. It writes nothing until the walk closes; then one signed commit carries the
signatures. A rule to confirm stops the walk on
`security_baseline RULE-4 was signed as not applying by jane@acme.com: the project stores no card data. Confirm it still does not apply?`
with three answers: confirm, which signs it again with the earlier reason; sign it as applying
after all, after which it waits as any rule does; or skip. `--all` confirms none.

## Step 4: the three answers

**Sign.** The rule, the proof and the test belong together.

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py" <feature> RULE-N [RULE-M ...] [--note "<text>"]
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py" <anchor> RULE-N [RULE-M ...] --does-not-apply "<why>"
```

The second line signs a pinned anchor's rule that does not apply here, with the person's reason, at
any gate; it then reads `does not apply` and counts as met until any change to the project ends it.
Any other rule is refused, since a rule of this project that does not apply is deleted. A feature
whose spec writes a number twice or holds a line left from a merge conflict is refused too: the
script prints `login is not signed: PROOF-2 is written twice in the spec. Run purlin:spec login, then purlin:sign again.`,
writes nothing and exits 1. The walk and `--all` never reach its rules.

**Add a case.** The person says in plain language what is missing: "it should also reject an expired
token". Write it into the spec as a new proof line with the next free proof id, leave the test for
the next `purlin:build`, and move on. This skill writes specs and signatures, never code.

**Skip.** Move on and leave the rule as it is. A skipped rule waits again next time.

Never narrow a rule or a proof to make an observation disappear. That lowers the claim instead of
strengthening the evidence.

## Step 5: when a signature counts

The script writes one file per rule under `specs/<category>/<feature>.signatures/` and makes one
signed commit for all of them. Each file records the signer's email and name as git holds them
and the key's fingerprint. The commit subjects come from `references/commit_conventions.md`.

| A signature counts when | What ends it |
|-------------------------|--------------|
| The last commit that touched the file is signed, with any key, and that signature verifies | `the commit that added it is not signed`; `the signature on the commit that added it does not verify` |
| It is still made over the rule, the proof, the test, the code its feature lists, what the audit found and the machine each system's tests ran on | A change to any of them; the rule is `to sign` again |

Nothing else is read, at any gate: the signature counts whoever wrote it, whoever last committed
to the test file, and on whatever branch carries it. A first run on a new system ends nothing. A
hand check's signature is made over the rule's and its proofs' wording alone: a change to the
code, a test or the machines does not end it, and a change to that wording does.
When it has signed, the script prints `Signed 3 rules as jane@acme.com with the key ending ...Xy4Q.`
and a line for each rule it signed. At the gate `signed` a rule of a spec that names no files is
signed all the same, and its line names the command that adds them:

```
  <feature> <RULE-N>   does not count until the spec names its files: purlin:spec <feature>
```

## Step 6: the version and the tag

At the gate `signed`, when nothing is left but the tag, the script writes the evidence package
`.purlin/evidence/package/<version>.json`, commits it as a signed commit, and writes a signed tag on
that commit. The version comes from the `VERSION` file, then `package.json`, then `pyproject.toml`,
then the first `*.csproj` at the root; `--release <name>` names another. It prints:

```
Evidence package committed: .purlin/evidence/package/1.4.0.json.
Tagged signed/1.4.0 at a1b2c3d.
Nothing left to do. Push the tag to release it: git push origin signed/1.4.0
```

While other work is left it prints the summary and `Left to do` instead. It writes no tag while the
working tree or any feature's results are not committed, and none over a tag that exists, where it
prints `No tag: <tag> is already written. Run purlin:sign --release <name> to name another.` It
exits 1 when the tag was refused for a reason to fix, uncommitted work or results, no version, a
package not committed or git failing to write the tag, and 0 when the tag already exists. It
exits 1 too on a broken spec, `No tag: login cannot be counted: PROOF-2 is written twice in the spec. Run purlin:spec login, then purlin:sign.`,
and while the branch's copy on the host, as last fetched, holds commits this checkout lacks:
`No tag: origin/main holds 1 commit that 8de0b6e does not, as this checkout last fetched it. Pull, run purlin:test --commit, then purlin:sign.`
It never fetches. Sign a version on a release branch, such as `release/1.2.0`, cut from the default
branch once its specs are done. Below `signed` it writes no tag and no package. With no version stated it prints
`No version: nothing in this project states one. Run purlin:sign --release <version>, or write it to a VERSION file.`:
ask the person for the version, offer to write it to a `VERSION` file at the root, and run the walk
again. Pushing the tag is a person's act; this skill never pushes.

## Step 7: close the walk and name the next step

The walk closes with what happened, then ends on the summary or on what the tag printed:

```
Walked 12 rules: 8 signed, 1 case added, 3 skipped.
  billing RULE-2   add this proof line: reject an expired token
```

| What it ended on | The line to print |
|------------------|-------------------|
| A case was added | `→ Run: purlin:build <feature>` |
| `Left to do:` and its lines | `→ Run:` the command on its first line |
| `Nothing left to do. Push the tag to release it: git push origin signed/<version>` | `→ Run: git push origin signed/<version>` |
| `No tag: <feature> has results that are not committed.` | `→ Run: purlin:test --commit` |
| `No tag: the working tree holds changes that are not committed` | `→ Commit them, then run: purlin:sign` |
| `No tag: <feature> cannot be counted:` or `<feature> is not signed:` | `→ Run: purlin:spec <feature>` |
| `No tag: <ref> holds <n> commit(s) that <sha> does not` | `→ Pull, then run: purlin:test --commit` |
| `No version:` | `→ Write the version the person gives to VERSION, then run: purlin:sign` |
| `No key to sign with.` | `→ Run the commands it printed, then run: purlin:sign` |
| `<feature> <RULE-N> is not a rule any spec has. Run purlin:status <feature> to see its rules.` | `→ Run: purlin:status <feature>` |
| `Nothing left to do.` | Nothing: the work at this gate is done |
