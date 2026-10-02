---
name: sign
description: "Sign off a version: build the evidence package from the committed evidence, walk its hand checks with a person, and sign it in a signed commit; also check a package against its fingerprint"
---

Sign this version of the code. `purlin:sign` reads the committed evidence, builds the evidence
package `.purlin/evidence/package/<version>.json`, walks it with the person, stopping only at
hand checks, and on their yes adds their sign-off over the package in one signed commit. Any
project may run it, at any time. The first sign-off of a version writes the signed tag
`signed/<version>`, as `references/evidence_and_signoff.md` defines it. Several people may sign
the same package.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`. Pass
`project_root` on every Purlin tool call: the top folder of the git checkout you are working in.

**Pending migrations:** when the status opens with a pending-migrations advisory, stop and
follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

A line marked **Stop and ask** is a question for the person: print it, end your turn, and act
only on their answer. Never answer it yourself.

## Usage

```
purlin:sign                          Walk the package of the stated version, then sign it
purlin:sign --version <version>      The same, for the version named
purlin:sign --show                   The overview and every stop, asking nothing
purlin:sign --answers <file>         The walk, with the answers a file gives
purlin:sign --check <file>           Check a package file against its fingerprint
```

The version is read from the `VERSION` file at the project root, then from the version the
project's package description states; `--version <version>` names it instead.

## Step 1: show the walk

The agent's shell has no terminal for the person to answer in, so the walk is two calls. First:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py" --show [--version <version>] --project-root .
```

It asks nothing, writes nothing and needs no key. It prints a refusal, or who ran the tests, the
overview, the audit's findings and every stop, and last `Answer each stop, then run purlin:sign
--answers <file>.` It opens:

```
Tests run by dana.dev@labconnect.example on dana-laptop at 2026-10-01 12:17 UTC on 1cf829e: 19 rules on Linux/Unix.
Signing 0.1.0 at 1cf829e.
  19 rules on Linux/Unix: 18 pass their tests, 1 has a hand check.
  The audit: 17 strong, 1 weak.
The audit's findings: 1 weak.
```

There is one `Tests run by` line per run the results come from, this machine's first. The audit's
line shows only where the audit read a rule.

## Step 2: the refusals

Each is one line, nothing written, exit 1. The person signs results taken on this exact version
of the code, so most name the run that takes them again:

```
No sign-off: 2 files are changed and not committed. Commit them or set them aside, then run purlin:sign again.
No sign-off: the evidence is written and not committed. Run purlin:test --commit, then purlin:sign.
No sign-off: 9 tests still carry a marker from Purlin 0.9.5, which is not read. Run purlin:status to see each, rewrite them, then purlin:sign.
No sign-off: signed/2.1.0 names a commit that holds no evidence package for 2.1.0, so purlin:sign did not write it. Delete it: git tag -d signed/2.1.0, and git push origin --delete signed/2.1.0 if it was pushed. Then run purlin:sign again.
No sign-off: signed/2.1.0 is at 3c9d2e1, which this checkout does not hold. Pull, then run purlin:sign.
No sign-off: signed/2.1.0 is at 3c9d2e1, and the code has changed since. To sign this code, name a new version: purlin:sign --version <version>.
No sign-off: these results were not taken on this version of the code, 8de0b6e: sample_age, stability on Linux/Unix; visit_window on Windows. Run purlin:test --all --commit and purlin:test on Windows, then purlin:sign.
No sign-off: these results were taken while files were changed and not committed: sample_age on Linux/Unix. Run purlin:test --all --commit, then purlin:sign.
No sign-off: 1 rule has no test at 8de0b6e: sample_age RULE-3. Run purlin:build sample_age, then purlin:sign.
No sign-off: 1 rule does not pass at 8de0b6e: sample_age RULE-2. Run purlin:status to see what is left, then purlin:sign.
No sign-off: origin/main holds 1 commit that 8de0b6e does not, as this checkout last fetched it. Pull, then run purlin:sign.
No sign-off: .purlin/evidence/package/2.1.0.json does not match its fingerprint: <why>. Restore it as it was signed, or name a new version: purlin:sign --version <version>.
No sign-off: the commit was signed with the key ending ...8kuw, not the key this checkout names, ending ...JJ8w, so it was taken back and no tag was written. A global gpg.ssh.program or signing key is the usual cause. Run git config gpg.ssh.program ssh-keygen, then purlin:sign again.
quinn.qa@labconnect.example has already signed 0.1.0 over this package; nothing was written.
```

With no version stated it prints
`No version: nothing in this project states one. Run purlin:sign --version <version>, or write it to a VERSION file.`
**Stop and ask** the person for the version and whether to write it to a `VERSION` file, then
run the walk again.

- The script never fetches.
- The first line counts tracked files alone, and reads `1 file is` for one. A file git does not
  track stops nothing.
- The 0.9.5 line reads `1 test still carries` for one. `purlin:status` names each test and its
  rule.
- A tag typed by hand is no sign-off, and the script signs nothing while one stands for the
  version. **Stop and ask** before you delete a tag. The line names the remote only where the
  checkout has one, and the script does not know whether the tag was pushed.
- **Stop and ask** before you run what a refusal names. Show the refusal, ask whether to run
  that command, and run it only on a yes.
- The wrong-key line comes after the commit: the script reads the key that signed it, and takes
  the commit back where it is not the key this checkout names.
- `purlin:test --all --commit` takes this machine's results again.
- A slow result kept from an earlier run reads `not taken on this version of the code`. A slow
  result must be taken on the version being signed, and `purlin:test --all --commit` takes it.
- A package that does not match its fingerprint was changed after it was signed.
- `purlin:build <feature>` writes the test for a rule with no test.
- `purlin:test on <System>` is an instruction, not a command line. For another system's results,
  do as `skills/test/SKILL.md`, Step 5 says.

## Step 3: a key to sign with

The script signs with an SSH key, any key. With none set up, the walk and `--answers` print, and
exit 1:

```
No key to sign with. These commands set one up:
  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
  git config gpg.format ssh
  git config user.signingkey ~/.ssh/id_ed25519.pub
```

The `ssh-keygen` line shows only when that key file does not exist. Show the person the commands,
**Stop and ask** whether to run them, and once they say yes and the commands ran, carry on with
the walk.

## Step 4: the stops and their answers

Show the person the opening lines as printed. Where a rule reads weak the walk asks `The audit's
findings: 1 weak. list / go on:`; ask the person which. `list` shows each weak rule with its
findings, one line each, and records that they opened it; `go on` leaves it closed. What the
audit found never blocks the sign-off and is no stop.

The walk stops only at hand checks, one at a time, in the order printed. Each stop opens on its
head, such as `accession_screen RULE-1   hand check`, then `Rule`, `Proof`, `Results` and, where
the audit found the rule weak, `What the audit found`. Where an earlier sign-off noted the rule,
the stop ends on `Last note` and that note, with the version it was signed at and how many
commits have come since. Where a stop shows `The rule's wording changed since this note.`, say
so to the person: the note was written about other words. Show the stop as printed; add nothing
of your own to what it says. Then **Stop and ask** what the walk asks:
`accession_screen RULE-1   what did you see, in one line, or Enter for no note, or stop:`

| The person's answer | What it does |
|---------------------|--------------|
| One line saying what they saw | It becomes the hand check's note, kept in the sign-off |
| Nothing | The note is recorded as `no note` |
| `stop` | The walk ends with nothing signed: `Stopped at <feature> <RULE-N>: nothing was signed. After the fix, run purlin:test --all --commit, then purlin:sign.` |

Never narrow a rule or a proof to make a finding disappear. Every answer and every note is the
person's own.

After the last stop, **Stop and ask**, in these words:
`Sign the evidence package for <version> as <email>? Type that address to sign:`
Write what the person typed, as they typed it, as `sign` in the answers file. The script signs
only where it is the signer's address. Never write the address yourself.

## Step 5: write the answers and walk

Write the answers to `.purlin/runtime/signoff-answers.json`, each stop keyed `<feature> <RULE-N>`:

```json
{"audit": "go on",
 "stops": {"accession_screen RULE-1": {"answer": "note", "note": "the tube is red"},
           "sample_age RULE-6": {"answer": "note", "note": ""}},
 "sign": "quinn.qa@labconnect.example"}
```

`audit` is `list` or `go on`. A hand check takes `note` with the line seen, empty for no note, or
`stop`. `sign` is what the person typed at the last question. Then run:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py" --answers .purlin/runtime/signoff-answers.json [--version <version>] --project-root .
```

It walks with those answers, printing each after its question. A stop with no answer refuses with
nothing written: `No sign-off: sample_age RULE-6 has no answer in .purlin/runtime/signoff-answers.json. Answer every stop, then run purlin:sign --answers .purlin/runtime/signoff-answers.json again.`
Where `sign` is not the signer's address it signs nothing and ends on
`Nothing was signed: "sign" in .purlin/runtime/signoff-answers.json must hold quinn.qa@labconnect.example, typed by the person signing.`
A person at a terminal may instead run `sign.py` with no option and answer each question there.

## Step 6: the sign-off and the tag

Where the person typed their address the script makes one signed commit, `sign(<version>): <email>`. For the first sign-off of
a version it carries the package, `.purlin/evidence/package/<version>.json`, and the sign-off,
`.purlin/evidence/package/<version>.signoffs/<signer-slug>.json`, and the script writes
`signed/<version>` on it:

```
Signed 0.1.0 as quinn.qa@labconnect.example with the key ending ...4f2a.
Tagged signed/0.1.0 at 8de0b6e.
Push the branch and the tag: git push origin main signed/0.1.0
```

The sign-off holds the package's fingerprint, what the person was shown and every note. It holds
no answer word and records no judgment. A later sign-off adds its own file alone and leaves the
tag where it is:
`signed/0.1.0 stays at 8de0b6e; this sign-off is added after it. Push it: git push origin main`.
Pushing is a person's act; this skill never pushes. Hand over the `git push origin` line as
printed.

Where git could not write the tag, the script says so and exits 1. Fix what git named and run
`purlin:sign` again: it writes the tag on the signed commit and signs nothing twice.

`references/evidence_and_signoff.md`, "When a sign-off counts", says what makes a sign-off count.

## Checking a package

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py" --check .purlin/evidence/package/<version>.json
```

It reads the file, writes nothing and needs no key. It prints `The package matches its
fingerprint.` and exits 0, or `The package does not match its fingerprint: <why>.` and exits 1.

## Step 7: name the next step

| What it ended on | The line to print |
|------------------|-------------------|
| `Push the branch and the tag: git push origin <branch> signed/<version>` | `→ Run: git push origin <branch> signed/<version>` |
| `signed/<version> stays at <sha>; this sign-off is added after it.` | `→ Run: git push origin <branch>` |
| `Stopped at <feature> <RULE-N>:` | `→ Run: purlin:build <feature>, then purlin:test --all --commit` |
| `Nothing was signed.` | `→ Run: purlin:sign` when the person is ready |
| `Nothing was signed: "sign" in` | `→ Ask the person the last question again, then run: purlin:sign --answers <file>` |
| `No sign-off: the commit was signed with` | `→ Run: git config gpg.ssh.program ssh-keygen, then purlin:sign` |
| `No sign-off:` naming `purlin:test --all --commit` or `purlin:test --commit` | `→ Run:` the command it names |
| `No sign-off:` naming `purlin:test on <System>` | `→ Run purlin:test on <System>`, as `skills/test/SKILL.md`, Step 5 says, then `purlin:sign` |
| `No sign-off:` naming `purlin:status` | `→ Run: purlin:status` |
| `No sign-off:` ending `Pull, then run purlin:sign.` | `→ Pull, then run: purlin:sign` |
| `No sign-off:` naming `purlin:sign --version <version>` | `→ Ask the person for the new version, then run: purlin:sign --version <version>` |
| `No sign-off: <rule> has no answer` | `→ Ask the person about that stop, then run: purlin:sign --answers <file>` |
| `No sign-off:` naming `git tag -d` | `→ Ask the person whether to delete the tag, then run: purlin:sign` |
| `has already signed` | `→ Ask another person to run: purlin:sign` |
| `No version:` | `→ Write the version the person gives to VERSION, then run: purlin:sign` |
| `No key to sign with.` | `→ Run the commands it printed, then run: purlin:sign` |
| `The sign-off commit was not made:` or `The evidence package was not written:` | `→ Fix what it named, then run: purlin:sign` |
| `No tag: git could not write signed/<version>:` | `→ Fix what git named, then run: purlin:sign` |
| `signed/<version> is not written yet:` | `→ Run: purlin:sign` |
