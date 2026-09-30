---
name: sign
description: Sign a release's evidence package after walking what a person has to look at, as a signed commit
---

Sign the evidence package of a release. At the gate `signed`, `purlin:test --release` commits the
package `.purlin/evidence/package/<version>.json`; this skill walks it with the person, one stop at
a time where there is something to look at, and on their yes adds their sign-off in one signed
commit. The first sign-off writes the signed tag `signed/<version>`, as `references/hard_gates.md`
defines it. Several people may sign the same package.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:sign                          Walk the package of the stated version, then sign it
purlin:sign --release <version>      The same, for the package of <version>
```

## What the gate decides

| Gate | What this skill does |
|------|----------------------|
| `passed` | Nothing: the script prints `Nothing is signed at the gate passed: purlin:test --release tags the release unsigned. To sign releases, run purlin:init --gate signed.` and exits 0 |
| `signed` | The walk, then one sign-off over the committed package; the first writes `signed/<version>` |

## Step 1: show the walk

The agent's shell has no terminal for the person to answer in, so the walk is two calls. First:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py" --show [--release <version>]
```

It asks nothing and writes nothing. It prints a refusal, or the overview, every stop and the strong
list, and last `Answer each stop, then run purlin:sign --answers <file>.` The overview reads:

```
Signing 1.2.0: .purlin/evidence/package/1.2.0.json, at 3c9d2e1.
  40 rules on Linux/Unix and Windows: 38 pass their tests, 2 are checked by hand.
  The audit: 30 strong, 2 weak, 6 not audited.
  10 stops: 2 hand checks, 2 weak, 6 not audited.
```

## Step 2: a key to sign with

The script signs with an SSH key, any key. With none set up it prints, and exits 1:

```
No key to sign with. These commands set one up:
  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
  git config gpg.format ssh
  git config user.signingkey ~/.ssh/id_ed25519.pub
```

The `ssh-keygen` line shows only when that key file does not exist. Show the person the commands,
offer to run them, and once they say yes and the commands ran, carry on with the walk.

## Step 3: the stops and their answers

Show the person the overview, then ask about each stop in the order printed, one at a time: every
hand check, then every weak rule, then every rule not audited. Each stop opens on its head, such
as `sample_age RULE-1   weak`, then `Rule`, `Proof`, `Results` and `What the audit found`. Under
each proof that is not `@manual` it shows the test tied to it, as
`    tied to tests/test_login.py::test_valid_credentials_return_200` with the test's body below,
or `    tied to no test`. Show the stop as printed; add nothing of your own to what it says.

| Stop | The person's answers |
|------|----------------------|
| A hand check, `@manual` | What they saw, in one line, which becomes its note; or `stop` |
| Weak, or not audited | `continue`; `note`, with one line; or `stop` |

Where the audit found rules strong, the script prints the list under
`30 rules the audit found strong. list / walk / go on:`. Ask the person: `list` records that they opened it, `walk` makes each
strong rule a stop after the others, and `go on` leaves them in the list. A weak or unaudited rule
never blocks the signature; `stop` is for a rule the person wants fixed first. Never narrow a rule
or a proof to make an observation disappear. After the last stop, ask whether to sign the package
for the version as their email, and take only a yes as yes.

## Step 4: write the answers and walk

Write the answers to `.purlin/runtime/signoff-answers.json`, each stop keyed `<feature> <RULE-N>`:

```json
{"strong": "go on",
 "stops": {"accession_screen RULE-1": {"answer": "note", "note": "the tube is red"},
           "sample_age RULE-1": {"answer": "continue"}},
 "sign": true}
```

A hand check takes `note` with the line seen, or `stop`. Then run:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py" --answers .purlin/runtime/signoff-answers.json [--release <version>]
```

It walks with those answers, printing each after its question. A stop with no answer refuses with
nothing written: `No sign-off: sample_age RULE-1 has no answer in .purlin/runtime/signoff-answers.json. Answer every stop, then run purlin:sign --answers .purlin/runtime/signoff-answers.json again.`
A person at a terminal may instead run `sign.py` with no option and answer each question there.

## Step 5: the refusals

Each is one line, nothing written, exit 1:

```
No sign-off: the working tree holds changes that are not committed. Commit them, then run purlin:test --release.
No sign-off: no evidence package for 1.2.0 is committed at 8de0b6e. Run purlin:test --release.
No sign-off: the evidence package for 1.2.0 describes 3c9d2e1, and 8de0b6e has changed since. Run purlin:test --release.
No sign-off: 1 rule does not pass at 8de0b6e: sample_age RULE-2. Run purlin:status to see what is left, then purlin:test --release.
No sign-off: origin/release/1.2.0 holds 1 commit that 8de0b6e does not, as this checkout last fetched it. Pull, then run purlin:sign.
quinn.qa@labconnect.example has already signed 1.2.0 over this package; nothing was written.
```

With no version stated it prints
`No version: nothing in this project states one. Run purlin:sign --release <version>, or write it to a VERSION file.`:
ask the person for the version, offer to write it to a `VERSION` file, and run the walk again. The
script never fetches.

## Step 6: the sign-off and the tag

On yes the script writes `.purlin/evidence/package/<version>.signoffs/<signer-slug>.json`, with
the package's fingerprint, what the person was shown and every note, and adds it in one signed
commit, `sign(<version>): <email>`. The file holds no answer word. For the first sign-off of the
version it writes `signed/<version>` on that commit:

```
Signed 1.2.0 as quinn.qa@labconnect.example with the key ending ...4f2a.
Tagged signed/1.2.0 at 8de0b6e.
Nothing left to do. Push the tag to release it: git push origin signed/1.2.0
Sign-offs of 1.2.0: quinn.qa@labconnect.example.
```

A later sign-off leaves the tag where it is:
`signed/1.2.0 stays at 8de0b6e; this sign-off is added after it. Push it: git push`. Pushing is a person's act; this skill never pushes.

| A sign-off counts when | Why it does not |
|------------------------|-----------------|
| The last commit that touched the file is signed, with any key, and that signature verifies | `the commit that added it is not signed`; `the signature on the commit that added it does not verify` |
| Its `package_hash` is the fingerprint of the package committed for its version | `it signs another evidence package than the one committed` |

Nothing else is read: a sign-off counts whoever wrote it and on whatever branch carries it.

## Step 7: name the next step

| What it ended on | The line to print |
|------------------|-------------------|
| `Nothing is signed at the gate passed:` | `→ Run: purlin:test --release` |
| `Nothing left to do. Push the tag to release it: git push origin signed/<version>` | `→ Run: git push origin signed/<version>` |
| `signed/<version> stays at <sha>; this sign-off is added after it.` | `→ Run: git push` |
| `Stopped at <feature> <RULE-N>:` | `→ Run: purlin:build <feature>, then purlin:test --release` |
| `Nothing was signed.` | `→ Run: purlin:sign` when the person is ready |
| `No sign-off:` naming `purlin:test --release` | `→ Run: purlin:test --release` |
| `No sign-off:` naming `purlin:status` | `→ Run: purlin:status` |
| `No sign-off: <ref> holds <n> commit(s)` | `→ Pull, then run: purlin:sign` |
| `No sign-off: <rule> has no answer` | `→ Ask the person about that stop, then run: purlin:sign --answers <file>` |
| `has already signed` | `→ Ask another person to run: purlin:sign` |
| `No version:` | `→ Write the version the person gives to VERSION, then run: purlin:sign` |
| `No key to sign with.` | `→ Run the commands it printed, then run: purlin:sign` |
| `The sign-off commit was not made:` | `→ Fix what git named, then run: purlin:sign` |
| `No tag: git could not write signed/<version>:` | `→ Fix what git named, then write the tag: git tag -s signed/<version>` |
