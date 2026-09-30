# Feature: signatures

> Description: The sign-off: one person's signature over a release's evidence
>   package, a file carrying the package's fingerprint, what the signer was
>   shown and every note typed, added in a signed commit. The command walks
>   the package first: an overview, then one stop per hand check, weak rule
>   and rule not audited, then one question. The first sign-off of a version
>   writes the tag `signed/<version>`; later ones are added beside it.
> Scope: scripts/mcp/purlin/signatures.py, scripts/review/sign.py
> Stack: python/stdlib (json, subprocess), git signed commits, SSH keys
> Highest-Rule: 111
> Highest-Proof: 222

## Rules

- RULE-17: With no SSH key to sign with the command writes no sign-off, exits 1 and prints `No key to sign with. These commands set one up:`, then `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""` only while that file does not exist, `git config gpg.format ssh` and `git config user.signingkey ~/.ssh/id_ed25519.pub`
- RULE-20: A sign-off's commit counts when the last commit that touched its file carries a signature that verifies, made with any key and whoever its author; otherwise it does not count, with the reason `the commit that added it is not signed`; the gate plays no part
- RULE-21: The command signs for anyone with a key to sign with, whatever their name or email
- RULE-22: The command exits 0 for `--help`
- RULE-50: A sign-off records the signer's email as git holds it, git's `user.name` as the signer's name, and the fingerprint of the key it was signed with
- RULE-60: The key fingerprint is read from `user.signingkey`, a public key path, a private key path with its `.pub` beside it, or a `key::` literal, and reads as `ssh-keygen -l` prints it; a key that is not an SSH key is no key
- RULE-67: A `.purlin/config.json` that cannot be read stops the command before it reads or writes anything else: it prints `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`, writes nothing and exits 1
- RULE-77: An unknown option exits 2
- RULE-79: When git does not make the sign-off commit, the command prints `The sign-off commit was not made: <git's own message>. Nothing was signed; run purlin:sign again.`, leaves no sign-off file and exits 1
- RULE-81: A `--project-root` that is not a directory exits 2 and prints `sign.py: <path> is not a directory.`
- RULE-83: At a stop each proof tagged `@manual` or `@env(<system>)` shows that tag after its id, as `PROOF-2 (@manual)` or `PROOF-1 (@env(windows))`
- RULE-84: Under `What the audit found` a stop prints, one line each and indented two spaces, `No audit has read this rule's text, proof and test yet.` where no audit has read the rule, `Strong. It found nothing.`, or `Strong.`, `Weak.` or `Undecided. The AI audit could not decide, so the rule reads weak until its proof or test changes.` followed by each finding; it names no reader
- RULE-89: `signed/<version>` carries an SSH signature made with the key `user.signingkey` names
- RULE-97: A sign-off's commit counts only when the signature on it verifies over that commit; otherwise it does not count, with the reason `the signature on the commit that added it does not verify`
- RULE-101: At each stop every proof that is not `@manual` is followed by one line per test it is tied to, `    tied to <file>::<test>`, or by `    tied to no test`
- RULE-102: The command refuses, one line, nothing written, in this order: at a gate other than `signed` (exit 0), then uncommitted work, no package committed for the version, a commit after the package's touching more than sign-offs, a rule not passing at HEAD, the branch's copy on the host holding commits HEAD lacks, and the signer already signed this package (exit 1)
- RULE-103: The walk opens on an overview naming the version, the package and its commit, the rules and systems, the rules passing and those checked by hand, what the audit found, and the stops by kind
- RULE-104: The walk stops at every hand check, then every weak rule, then every rule not audited; a stop shows the rule and its proofs, each tied test's body, the results on each system and what the audit found, and a hand check shows the rule and its proofs and asks what the person saw
- RULE-105: Where the audit found any rule strong, the walk asks whether to list those rules, walk them, or go on; `walk` makes each a stop after the others
- RULE-106: The sign-off file records the package's fingerprint, the overview shown, each rule walked one by one, each rule left in the strong list, whether the list was opened, and every note typed, and no answer word
- RULE-107: The first sign-off of a version is one signed commit, `sign(<version>): <email>`, carrying its one file, and `signed/<version>` is written on that commit; a later sign-off adds its file and leaves the tag where it was
- RULE-108: A sign-off counts only while its `package_hash` equals the fingerprint of the package HEAD holds for its version
- RULE-109: `stop` at any stop, and any answer but yes to the last question, write nothing and exit 0
- RULE-110: `--show` prints the overview, every stop and the strong list, then `Answer each stop, then run purlin:sign --answers <file>.`, asks nothing and writes nothing
- RULE-111: `--answers FILE` walks with the answers the file gives, printing each after its question, and refuses with nothing written when a stop has no answer

## Proof

- PROOF-21 (RULE-17): In a home with no `~/.ssh/id_ed25519`, in a checkout with no signing key, the walk is run over a committed package; it exits 1, prints exactly `No key to sign with. These commands set one up:`, the `ssh-keygen` line and the two `git config` lines, and adds no commit
- PROOF-95 (RULE-17): In a home where `~/.ssh/id_ed25519` exists, in a checkout with no signing key, the walk is run over a committed package; it exits 1 and prints exactly the first line and the two `git config` lines, with no `ssh-keygen` line
- PROOF-22 (RULE-17): The command is started as its own process, the way a person runs it, over a committed package in a home and a checkout with no key; it exits 1 and prints exactly the four lines
- PROOF-153 (RULE-17): On Windows, in a home folder where `.ssh\id_ed25519` exists, in a checkout with no signing key, the walk is run over a committed package; it exits 1 and prints the first line and the two `git config` lines, with no `ssh-keygen` line @env(windows)
- PROOF-25 (RULE-20): A sign-off file for `2.1.0` is committed signed with the signer's own key; its commit counts, with no reason
- PROOF-96 (RULE-20): A sign-off file for `2.1.0` is committed with commit signing off; it does not count, with the reason `the commit that added it is not signed`
- PROOF-97 (RULE-20): A sign-off file for `2.1.0` is committed signed with a new key made on the spot for `mallory@else.org`, which no project file or setting names; its commit counts, with no reason
- PROOF-98 (RULE-20): A sign-off file for `2.1.0` is committed signed with Jane's key under the author `Bob <bob@else.org>`; its commit counts
- PROOF-155 (RULE-20): On Windows, a sign-off file for `2.1.0` is committed signed with the signer's own key; its commit counts, with no reason @env(windows)
- PROOF-27 (RULE-21): `omar@example.org`, who has not signed in this project before, sets up a key and signs the package for `2.1.0`; the command exits 0 and writes `.purlin/evidence/package/2.1.0.signoffs/omar.json`
- PROOF-28 (RULE-22): The command is run with `--help`; it exits 0, and its first line reads `Sign a release's evidence package, as a signed commit.`
- PROOF-75 (RULE-50): Jane, set up in git as `Jane.Doe@Acme.com` with the name `Jane Doe`, signs the package for `2.1.0`; her sign-off reads `signer` `Jane.Doe@Acme.com`, `signer_name` `Jane Doe`, and `key_fingerprint` what `ssh-keygen -l` prints for her key
- PROOF-157 (RULE-50): On Windows, Jane, set up in git as `Jane.Doe@Acme.com` with the name `Jane Doe`, signs the package for `2.1.0`; her sign-off reads `signer` `Jane.Doe@Acme.com`, `signer_name` `Jane Doe`, and `key_fingerprint` what `ssh-keygen -l` prints for her key @env(windows)
- PROOF-115 (RULE-60): With `user.signingkey` naming a public key file, the key fingerprint a sign-off would record reads what `ssh-keygen -l` prints for that key
- PROOF-116 (RULE-60): With `user.signingkey` naming the private key file whose `.pub` sits beside it, the key fingerprint a sign-off would record reads what `ssh-keygen -l` prints for that key
- PROOF-117 (RULE-60): With `user.signingkey` set to `key::` followed by the public key's text, the key fingerprint a sign-off would record reads what `ssh-keygen -l` prints for that key
- PROOF-118 (RULE-60): With `gpg.format` set to `ssh` and `user.signingkey` set to a GPG key id, `3AA5C34371567BD2`, the walk over a committed package exits 1 and its first line reads `No key to sign with. These commands set one up:`
- PROOF-158 (RULE-60): On Windows, with `user.signingkey` naming the private key file by a path holding `\`, and its `.pub` beside it, the key fingerprint a sign-off would record reads what `ssh-keygen -l` prints for that key @env(windows)
- PROOF-152 (RULE-67): With a package ready to sign and a comma after the last setting of `.purlin/config.json`, the walk is run; it prints one line, beginning `.purlin/config.json cannot be read: ` and ending `Fix the file by hand; nothing ran and nothing was saved.`, adds no commit and exits 1
- PROOF-132 (RULE-77): The command is run as `--release 2.1.0 --nope`; it exits 2, and below the usage line it prints `sign.py: unknown option --nope`
- PROOF-133 (RULE-77): The command is run as `--nope`; it exits 2, and below the usage line it prints `sign.py: unknown option --nope`
- PROOF-162 (RULE-79): With a git hook that refuses every commit, printing `error: the hook refused the commit.`, the walk is answered yes; it adds no commit, leaves no sign-off file, exits 1, and its last line is `The sign-off commit was not made: the hook refused the commit. Nothing was signed; run purlin:sign again.`
- PROOF-164 (RULE-81): The command is run with `--project-root no/such/folder`, which does not exist; it exits 2 and prints `sign.py: no/such/folder is not a directory.`
- PROOF-166 (RULE-83): With `PROOF-1` of `login` tagged `@env(windows)`, passing on Windows, and no audit read, the walk's stop for `login RULE-1` lists `  PROOF-1 (@env(windows)): POST /login with the password "secret"; verify 200 and a token`
- PROOF-167 (RULE-84): With no audit read for `login RULE-1`, its stop shows under `What the audit found` the one line `  No audit has read this rule's text, proof and test yet.`
- PROOF-168 (RULE-84): With every rule audited strong with no finding and all walked, the stop for `login RULE-1` shows under `What the audit found` the one line `  Strong. It found nothing.`
- PROOF-169 (RULE-84): With `login RULE-1` audited strong with the finding `PROOF-1 reads the status alone.` and walked, its stop ends on `What the audit found`, `  Strong.` and `  PROOF-1 reads the status alone.`
- PROOF-170 (RULE-84): With `login RULE-2` audited weak with the finding `PROOF-2 reads the status alone.`, its stop ends on `What the audit found`, `  Weak.` and `  PROOF-2 reads the status alone.`
- PROOF-171 (RULE-84): With `login RULE-2` audited undecided with the finding `PROOF-2 names no status.`, its stop ends on `What the audit found`, `  Undecided. The AI audit could not decide, so the rule reads weak until its proof or test changes.` and `  PROOF-2 names no status.`
- PROOF-178 (RULE-89): The first sign-off of `2.1.0` writes `signed/2.1.0`; `git tag -v`, with the signer's public key as the one allowed signer, reports a good signature by the key whose fingerprint `ssh-keygen -l` prints for the file `user.signingkey` names
- PROOF-192 (RULE-97): A sign-off is committed by the walk, then that commit is rewritten with one byte of its signature block changed; the sign-off reads as not counting, with the reason `the signature on the commit that added it does not verify`
- PROOF-193 (RULE-97): A sign-off is committed by the walk, then the key it was signed with is deleted from disk and from the settings; the sign-off still counts
- PROOF-200 (RULE-101): With no audit read, the stop for `login RULE-1` shows `    tied to tests/test_login.py::test_valid_credentials_return_200` on the line under `PROOF-1`
- PROOF-201 (RULE-101): The package for `2.1.0` lists no test for `PROOF-2` of `login RULE-2`, which no audit read; its stop holds `    tied to no test` on the line under `PROOF-2`
- PROOF-202 (RULE-102): At the gate `passed`, with a package committed and a key, the walk prints only `Nothing is signed at the gate passed: purlin:test --release tags the release unsigned. To sign releases, run purlin:init --gate signed.`, adds no commit and exits 0
- PROOF-203 (RULE-102): With a package ready to sign and a new file `notes.txt` not committed, the walk prints only `No sign-off: the working tree holds changes that are not committed. Commit them, then run purlin:test --release.` and exits 1
- PROOF-204 (RULE-102): At the gate `signed`, with `VERSION` reading `2.1.0` and no package committed, the walk prints only `No sign-off: no evidence package for 2.1.0 is committed at <sha7>. Run purlin:test --release.`, naming HEAD, and exits 1
- PROOF-205 (RULE-102): With a package committed at `<p>` and a later commit changing `src/login.py` at `<h>`, the walk prints only `No sign-off: the evidence package for 2.1.0 describes <p>, and <h> has changed since. Run purlin:test --release.` and exits 1
- PROOF-206 (RULE-102): With a package committed over results in which `login RULE-2` fails, the walk prints only `No sign-off: 1 rule does not pass at <sha7>: login RULE-2. Run purlin:status to see what is left, then purlin:test --release.` and exits 1
- PROOF-207 (RULE-102): In a clone whose fetched `origin/main` holds one commit it lacks, with a package ready to sign, the walk prints only `No sign-off: origin/main holds 1 commit that <sha7> does not, as this checkout last fetched it. Pull, then run purlin:sign.` and exits 1
- PROOF-208 (RULE-102): `jane@acme.com` has signed the package for `2.1.0`; the walk run again prints only `jane@acme.com has already signed 2.1.0 over this package; nothing was written.`, adds no commit and exits 1
- PROOF-209 (RULE-103): Over a package whose two `login` rules pass on Linux/Unix, `RULE-1` strong and `RULE-2` not audited, the walk opens `Signing 2.1.0: .purlin/evidence/package/2.1.0.json, at <sha7>.`, `  2 rules on Linux/Unix: 2 pass their tests, 0 are checked by hand.`, `  The audit: 1 strong, 0 weak, 1 not audited.` and `  1 stop: 0 hand checks, 0 weak, 1 not audited.`
- PROOF-210 (RULE-104): With `login RULE-2` audited weak, its stop shows the head `login RULE-2   weak`, the body of `test_a_bad_password_is_denied` six spaces in under its tied line, and under `Results` the line `  Linux/Unix: passed on jane-laptop`
- PROOF-211 (RULE-104): With the one proof of `login RULE-2` tagged `@manual` and `RULE-1` audited weak, the walk stops at `RULE-2` first, under the head `login RULE-2   hand check`, shows no `Results`, and asks `login RULE-2   what did you see, in one line, or stop: `
- PROOF-212 (RULE-105): With both `login` rules audited strong, the walk asks `2 rules the audit found strong. list / walk / go on: `; answered `list`, it prints `  login RULE-1, RULE-2` and asks `walk / go on: `
- PROOF-213 (RULE-105): With `login RULE-1` weak and `RULE-2` strong, the walk answered `walk` at the strong list stops at `login RULE-1   weak`, then at `login RULE-2   strong`
- PROOF-214 (RULE-106): With `RULE-2` a hand check answered `the lockout page read 401` and `RULE-1` strong left in the list unopened, the sign-off records the package's fingerprint, `one_by_one` `login RULE-2` as `hand check`, `in_list` `login RULE-1`, `list_opened` false, that note as a `hand check`, and no answer word
- PROOF-215 (RULE-107): The first sign-off of `2.1.0` adds one commit, carrying only `.purlin/evidence/package/2.1.0.signoffs/jane.json` and an SSH signature, under `sign(2.1.0): jane@acme.com`; `signed/2.1.0` names that commit, and the walk prints `Tagged signed/2.1.0 at <sha7>.`
- PROOF-216 (RULE-107): After `jane@acme.com` signs `2.1.0`, `pat@acme.com` signs it; the tag still names Jane's commit, and the walk ends `signed/2.1.0 stays at <sha7>; this sign-off is added after it. Push it: git push` then `Sign-offs of 2.1.0: jane@acme.com, pat@acme.com.`
- PROOF-217 (RULE-108): The walk signs the package for `2.1.0`, then the committed package's fingerprint is changed and committed; before the change the sign-off counts, and after it the sign-off does not count, with the reason `it signs another evidence package than the one committed`
- PROOF-218 (RULE-109): With `login RULE-2` audited weak, the walk is answered `stop` at it; it prints `Stopped at login RULE-2: nothing was signed. After the fix, run purlin:test --release, then purlin:sign.`, exits 0 and adds no commit and no file
- PROOF-219 (RULE-109): The walk is answered `continue` at every stop and an empty line at `Sign the evidence package for 2.1.0 as jane@acme.com? [y/N] `; it prints `Nothing was signed.`, exits 0 and adds no commit and no file
- PROOF-220 (RULE-110): With `RULE-1` strong and `RULE-2` weak, `--show` prints the overview, the stop `login RULE-2   weak` with no question after it, `  login RULE-1`, and last `Answer each stop, then run purlin:sign --answers <file>.`; it exits 0 and adds no commit and no file
- PROOF-221 (RULE-111): With `RULE-2` weak and an answers file giving it `note` with `check the lockout copy` and `sign` true, `--answers` prints `login RULE-2   continue / note / stop: note`, exits 0, and the sign-off carries that note as a `note`
- PROOF-222 (RULE-111): With `RULE-2` weak and an answers file naming no stop, `--answers .purlin/runtime/signoff-answers.json` prints only `No sign-off: login RULE-2 has no answer in .purlin/runtime/signoff-answers.json. Answer every stop, then run purlin:sign --answers .purlin/runtime/signoff-answers.json again.`, exits 1 and adds nothing
