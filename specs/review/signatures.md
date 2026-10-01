# Feature: signatures

> Description: The sign-off, which any project may run whenever it chooses. `purlin:sign` reads
>   the evidence committed at `HEAD`, refuses results not taken on this version of the code,
>   builds the evidence package, walks it with a person and takes one signature over it: a file
>   carrying the package's fingerprint, what the signer was shown and every note typed, added in
>   a signed commit. The walk names who ran the tests, where and when, gives an overview and the
>   audit's findings, and stops only at hand checks. The first sign-off of a version commits the
>   package with it and writes the tag `signed/<version>`; later ones are added beside it.
> Scope: scripts/mcp/purlin/signatures.py, scripts/review/sign.py
> Stack: python/stdlib (json, subprocess), git signed commits, SSH keys
> Highest-Rule: 123
> Highest-Proof: 243

## Rules

- RULE-17: With no SSH key to sign with the command writes no sign-off, exits 1 and prints `No key to sign with. These commands set one up:`, then `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""` only while that file does not exist, `git config gpg.format ssh` and `git config user.signingkey ~/.ssh/id_ed25519.pub`
- RULE-20: A sign-off's commit counts when the last commit that touched its file carries a signature that verifies, made with any key and whoever its author; otherwise it does not count, with the reason `the commit that added it is not signed`
- RULE-21: The command signs for anyone with a key to sign with, whatever their name or email
- RULE-22: The command exits 0 for `--help`
- RULE-50: A sign-off records the signer's email as git holds it, git's `user.name` as the signer's name, and the fingerprint of the key it was signed with
- RULE-60: The key fingerprint is read from `user.signingkey`, a public key path, a private key path with its `.pub` beside it, or a `key::` literal, and reads as `ssh-keygen -l` prints it; a key that is not an SSH key is no key
- RULE-67: A `.purlin/config.json` that cannot be read stops the command before it reads or writes anything else: it prints `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`, writes nothing and exits 1
- RULE-77: An unknown option exits 2
- RULE-79: When git does not make the sign-off commit, the command prints `The sign-off commit was not made: <git's own message>. Nothing was signed; run purlin:sign again.`, leaves no sign-off file and exits 1
- RULE-81: A `--project-root` that is not a directory exits 2 and prints `sign.py: <path> is not a directory.`
- RULE-83: At a stop each proof tagged `@manual` or `@env(<system>)` shows that tag after its id, as `PROOF-2 (@manual)` or `PROOF-1 (@env(windows))`
- RULE-89: `signed/<version>` carries an SSH signature made with the key `user.signingkey` names
- RULE-97: A sign-off's commit counts only when the signature on it verifies over that commit; otherwise it does not count, with the reason `the signature on the commit that added it does not verify`
- RULE-101: At each stop every proof that is not `@manual` is followed by one line per test it is tied to, `    tied to <file>::<test>`
- RULE-102: The command refuses, one line, nothing written, exit 1, in this order: uncommitted work, evidence written and not committed, no version, `signed/<version>` on a commit this checkout does not hold, the code changed since `signed/<version>`, results not taken on this version of the code, a rule not passing, the branch's copy on the host holding commits `HEAD` lacks, and the signer already signed this package
- RULE-103: After the lines naming the runs, the walk prints `Signing <version> at <sha7>.`, the commit the package describes
- RULE-104: A stop shows the rule, its proofs and the results on each system, and asks what the person saw
- RULE-106: The sign-off file records the package's fingerprint as `package_hash`, and under `shown` the overview, the runs, each hand check walked and whether the audit's list was opened, with every note typed and no answer word
- RULE-108: A sign-off counts only while its `package_hash` equals the fingerprint of the package `HEAD` holds for its version
- RULE-109: `stop` at any stop, and any answer but yes to the last question, write nothing and exit 0
- RULE-110: `--show` prints the run lines, the overview, the audit's findings and every stop, then `Answer each stop, then run purlin:sign --answers <file>.`, asks nothing and writes nothing
- RULE-111: `--answers FILE` walks with the answers the file gives, printing each after its question, and refuses with nothing written when a stop has no answer
- RULE-112: The walk opens with one line per run of the counted results: `Tests run by <email> on <machine> at <time> on <sha7>: <n> rules on <system>.`, or for a remote runner `Tests run by a remote runner at <time> on <sha7>: <n> rules on <system>.`
- RULE-113: `--show` needs no key to sign with
- RULE-114: The walk stops only at hand checks, one stop each, by feature then rule number; a weak rule or one never audited adds no stop
- RULE-115: Where the audit found any rule weak, the walk asks `The audit's findings: <n> weak. list / go on: `; `list` prints each weak rule with its findings, then asks `go on: `
- RULE-116: A hand check whose audit reads weak ends its stop on `What the audit found`, `  Weak.` and each finding
- RULE-117: The overview prints, per system, `  <n> rules on <system>: <n> pass their tests, <hand checks>.`, then `  The audit: <n> strong, <n> weak, <n> not audited.`, a line left out where no rule was audited
- RULE-118: The first sign-off ends on `Push the branch and the tag: git push origin <branch> signed/<version>`, and a later one on `signed/<version> stays at <sha7>; this sign-off is added after it. Push it: git push origin <branch>`; on a detached `HEAD` the branch is left out
- RULE-119: An empty answer at a hand check records the note `no note`
- RULE-120: The first sign-off of a version is one signed commit, `sign(<version>): <email>`, carrying the package and its sign-off file, and `signed/<version>` is written on that commit; a later sign-off adds its own file alone and leaves the tag where it was
- RULE-121: The sign-off fetches nothing and pushes nothing, goes ahead when the checkout holds commits the host lacks, and where git cannot write the tag prints `No tag: git could not write signed/<version>: <git's message>.`
- RULE-122: `--check <file>` prints `The package matches its fingerprint.` and exits 0 for a package as written, and `The package does not match its fingerprint: <why>.` and exits 1 for one changed after
- RULE-123: At a stop, a system's results line names each proof that found nothing to check, with its reason

## Proof

- PROOF-21 (RULE-17): In a home with no `~/.ssh/id_ed25519`, in a checkout with no signing key, the walk is run over committed evidence that passes; it exits 1, prints exactly `No key to sign with. These commands set one up:`, the `ssh-keygen` line and the two `git config` lines, and adds no commit
- PROOF-95 (RULE-17): In a home where `~/.ssh/id_ed25519` exists, in a checkout with no signing key, the walk is run over committed evidence that passes; it exits 1 and prints exactly the first line and the two `git config` lines, with no `ssh-keygen` line
- PROOF-22 (RULE-17): The command is started as its own process, the way a person runs it, over committed evidence that passes in a home and a checkout with no key; it exits 1 and prints exactly the four lines
- PROOF-153 (RULE-17): On Windows, in a home folder where `.ssh\id_ed25519` exists, in a checkout with no signing key, the walk is run over committed evidence that passes; it exits 1 and prints the first line and the two `git config` lines, with no `ssh-keygen` line @env(windows)
- PROOF-25 (RULE-20): A sign-off file for `2.1.0` is committed signed with the signer's own key; its commit counts, with no reason
- PROOF-96 (RULE-20): A sign-off file for `2.1.0` is committed with commit signing off; it does not count, with the reason `the commit that added it is not signed`
- PROOF-97 (RULE-20): A sign-off file for `2.1.0` is committed signed with a new key made on the spot for `mallory@else.org`, which no project file or setting names; its commit counts, with no reason
- PROOF-98 (RULE-20): A sign-off file for `2.1.0` is committed signed with Jane's key under the author `Bob <bob@else.org>`; its commit counts
- PROOF-155 (RULE-20): On Windows, a sign-off file for `2.1.0` is committed signed with the signer's own key; its commit counts, with no reason @env(windows)
- PROOF-27 (RULE-21): `omar@example.org`, who has not signed in this project before, sets up a key and signs `2.1.0`; the command exits 0 and writes `.purlin/evidence/package/2.1.0.signoffs/omar.json`
- PROOF-28 (RULE-22): The command is run with `--help`; it exits 0, and its first line reads `Sign the evidence package for a version, as a signed commit.`
- PROOF-75 (RULE-50): Jane, set up in git as `Jane.Doe@Acme.com` with the name `Jane Doe`, signs `2.1.0`; her sign-off reads `signer` `Jane.Doe@Acme.com`, `signer_name` `Jane Doe`, and `key_fingerprint` what `ssh-keygen -l` prints for her key
- PROOF-157 (RULE-50): On Windows, Jane, set up in git as `Jane.Doe@Acme.com` with the name `Jane Doe`, signs `2.1.0`; her sign-off reads `signer` `Jane.Doe@Acme.com`, `signer_name` `Jane Doe`, and `key_fingerprint` what `ssh-keygen -l` prints for her key @env(windows)
- PROOF-115 (RULE-60): With `user.signingkey` naming a public key file, the key fingerprint a sign-off would record reads what `ssh-keygen -l` prints for that key
- PROOF-116 (RULE-60): With `user.signingkey` naming the private key file whose `.pub` sits beside it, the key fingerprint a sign-off would record reads what `ssh-keygen -l` prints for that key
- PROOF-117 (RULE-60): With `user.signingkey` set to `key::` followed by the public key's text, the key fingerprint a sign-off would record reads what `ssh-keygen -l` prints for that key
- PROOF-118 (RULE-60): With `gpg.format` set to `ssh` and `user.signingkey` set to a GPG key id, `3AA5C34371567BD2`, the walk over committed evidence that passes exits 1 and its first line reads `No key to sign with. These commands set one up:`
- PROOF-158 (RULE-60): On Windows, with `user.signingkey` naming the private key file by a path holding `\`, and its `.pub` beside it, the key fingerprint a sign-off would record reads what `ssh-keygen -l` prints for that key @env(windows)
- PROOF-152 (RULE-67): With committed evidence that passes and a comma after the last setting of `.purlin/config.json`, the walk is run; it prints one line, beginning `.purlin/config.json cannot be read: ` and ending `Fix the file by hand; nothing ran and nothing was saved.`, adds no commit and exits 1
- PROOF-132 (RULE-77): The command is run as `--version 2.1.0 --nope`; it exits 2, and below the usage line it prints `sign.py: unknown option --nope`
- PROOF-133 (RULE-77): The command is run as `--nope`; it exits 2, and below the usage line it prints `sign.py: unknown option --nope`
- PROOF-162 (RULE-79): With a git hook that refuses every commit, printing `error: the hook refused the commit.`, the walk is answered yes; it adds no commit, leaves no sign-off file, exits 1, and its last line is `The sign-off commit was not made: the hook refused the commit. Nothing was signed; run purlin:sign again.`
- PROOF-164 (RULE-81): The command is run with `--project-root no/such/folder`, which does not exist; it exits 2 and prints `sign.py: no/such/folder is not a directory.`
- PROOF-166 (RULE-83): `login RULE-1` has `PROOF-2` marked `@manual` and `PROOF-1` tagged `@env(windows)`, passing on Windows; its stop lists `  PROOF-1 (@env(windows)): POST /login with the password "secret"; verify 200 and a token`
- PROOF-178 (RULE-89): The first sign-off of `2.1.0` writes `signed/2.1.0`; `git tag -v`, with the signer's public key as the one allowed signer, reports a good signature by the key whose fingerprint `ssh-keygen -l` prints for the file `user.signingkey` names
- PROOF-192 (RULE-97): A sign-off is committed by the walk, then that commit is rewritten with one byte of its signature block changed; the sign-off reads as not counting, with the reason `the signature on the commit that added it does not verify`
- PROOF-193 (RULE-97): A sign-off is committed by the walk, then the key it was signed with is deleted from disk and from the settings; the sign-off still counts
- PROOF-200 (RULE-101): `login RULE-2` has `PROOF-2` marked `@manual` and `PROOF-3` tied to `test_lockout_page`; its stop shows `    tied to tests/test_login.py::test_lockout_page` on the line under `PROOF-3`
- PROOF-203 (RULE-102): With committed evidence that passes and a new file `notes.txt` not committed, the walk prints only `No sign-off: the working tree holds changes that are not committed. Commit them, run purlin:test --all --commit, then purlin:sign.` and exits 1
- PROOF-206 (RULE-102): With results committed at `HEAD` in which `login RULE-2` fails, the walk prints only `No sign-off: 1 rule does not pass at <sha7>: login RULE-2. Run purlin:status to see what is left, then purlin:sign.` and exits 1
- PROOF-207 (RULE-102): In a clone whose fetched `origin/main` holds one commit it lacks, with committed evidence that passes, the walk prints only `No sign-off: origin/main holds 1 commit that <sha7> does not, as this checkout last fetched it. Pull, then run purlin:sign.` and exits 1
- PROOF-208 (RULE-102): `jane@acme.com` has signed `2.1.0`; the walk run again prints only `jane@acme.com has already signed 2.1.0 over this package; nothing was written.`, adds no commit and exits 1
- PROOF-223 (RULE-102): The tests are run and their results written and not committed; the walk prints only `No sign-off: the evidence is written and not committed. Run purlin:test --commit, then purlin:sign.` and exits 1
- PROOF-224 (RULE-102): `signed/2.1.0` is on a commit of another branch, which `HEAD` does not descend from; the walk for `2.1.0` prints only `No sign-off: signed/2.1.0 is at <sha7>, which this checkout does not hold. Pull, then run purlin:sign.` and exits 1
- PROOF-225 (RULE-102): `signed/2.1.0` is on an ancestor of `HEAD`, and a later commit changes `src/login.py`; the walk for `2.1.0` prints only `No sign-off: signed/2.1.0 is at <sha7>, and the code has changed since. To sign this code, name a new version: purlin:sign --version <version>.` and exits 1
- PROOF-226 (RULE-102): `audit`'s Windows results were pulled home before a commit that changed `src/audit.py`, and every other result was taken at `HEAD`; the walk prints only `No sign-off: these results were not taken on this version of the code, <sha7>: audit on Windows. Run purlin:test --remote, then purlin:sign.` and exits 1
- PROOF-243 (RULE-102): Nothing in the project states a version and none is named; the walk prints only `No version: nothing in this project states one. Run purlin:sign --version <version>, or write it to a VERSION file.`, writes nothing and exits 1
- PROOF-209 (RULE-103): Over evidence committed at `1cf829e`, the walk for `0.1.0` prints `Signing 0.1.0 at 1cf829e.` on the line after the last line naming a run
- PROOF-211 (RULE-104): With the one proof of `login RULE-2` marked `@manual`, the walk stops at it under the head `login RULE-2   hand check` and asks `login RULE-2   what did you see, in one line, or Enter for no note, or stop: `
- PROOF-214 (RULE-106): With `login RULE-2` a hand check answered `the lockout page read 401` and the audit's list not opened, the sign-off records `package_hash` the package's fingerprint, `login RULE-2` among the hand checks shown, `audit_list_opened` false, that note, and no answer word
- PROOF-217 (RULE-108): The walk signs `2.1.0`, then the committed package's fingerprint is changed and committed; before the change the sign-off counts, and after it the sign-off does not count, with the reason `it signs another evidence package than the one committed`
- PROOF-218 (RULE-109): At the hand check `login RULE-2` the walk is answered `stop`; it prints `Stopped at login RULE-2: nothing was signed. After the fix, run purlin:test --all --commit, then purlin:sign.`, exits 0 and adds no commit and no file
- PROOF-219 (RULE-109): The walk is given an empty line at every stop and at `Sign the evidence package for 2.1.0 as jane@acme.com? [y/N] `; it prints `Nothing was signed.`, exits 0 and adds no commit and no file
- PROOF-220 (RULE-110): With `login RULE-1` audited weak and `login RULE-2` a hand check, `--show` prints the overview, `  login RULE-1` with its finding, the stop `login RULE-2   hand check` with no question after it, and last `Answer each stop, then run purlin:sign --answers <file>.`; it exits 0 and adds no commit and no file
- PROOF-221 (RULE-111): With `login RULE-2` a hand check and an answers file giving it `note` with `the lockout page read 401` and `sign` true, `--answers` prints that note after the stop's question, exits 0, and the sign-off carries that note
- PROOF-222 (RULE-111): With `login RULE-2` a hand check and an answers file naming no stop, `--answers .purlin/runtime/signoff-answers.json` prints only `No sign-off: login RULE-2 has no answer in .purlin/runtime/signoff-answers.json. Answer every stop, then run purlin:sign --answers .purlin/runtime/signoff-answers.json again.`, exits 1 and adds nothing
- PROOF-227 (RULE-112): `dana.dev@labconnect.example` ran 19 rules' tests on `dana-laptop`, a Linux machine, at 12:17 UTC on 2026-10-01 at `1cf829e`; the walk's first line reads `Tests run by dana.dev@labconnect.example on dana-laptop at 2026-10-01 12:17 UTC on 1cf829e: 19 rules on Linux/Unix.`
- PROOF-228 (RULE-113): In a home and a checkout with no signing key, `--show` over committed evidence that passes exits 0, prints the overview, and prints no line `No key to sign with. These commands set one up:`
- PROOF-229 (RULE-114): Over a project with one rule audited weak, one never audited and no hand check, the walk asks no stop question; after the overview and the audit's question it asks only `Sign the evidence package for 2.1.0 as jane@acme.com? [y/N] `
- PROOF-230 (RULE-115): With `login RULE-1` audited weak with the finding `PROOF-1 reads the status alone.`, the walk asks `The audit's findings: 1 weak. list / go on: `; answered `list`, it prints `  login RULE-1   PROOF-1 reads the status alone.` and asks `go on: `
- PROOF-231 (RULE-116): `login RULE-2` is a hand check whose audit reads weak with the finding `PROOF-3 reads the status alone.`; its stop ends on `What the audit found`, `  Weak.` and `  PROOF-3 reads the status alone.`
- PROOF-232 (RULE-117): Over 19 rules on Linux/Unix that pass, one a hand check, with 17 audited strong, 1 weak and 1 not audited, the overview prints `  19 rules on Linux/Unix: 19 pass their tests, 1 has a hand check.` and `  The audit: 17 strong, 1 weak, 1 not audited.`
- PROOF-233 (RULE-118): On the branch `main`, the first sign-off of `0.1.0` ends on `Push the branch and the tag: git push origin main signed/0.1.0`
- PROOF-234 (RULE-118): On `main`, with `signed/0.1.0` at `e0deb2e`, a second signer signs `0.1.0`; the walk ends on `signed/0.1.0 stays at e0deb2e; this sign-off is added after it. Push it: git push origin main`
- PROOF-235 (RULE-119): At the hand check `login RULE-2` the walk is given an empty line, then yes; the sign-off records the note `no note` for `login RULE-2`
- PROOF-236 (RULE-120): `quinn.qa@labconnect.example` makes the first sign-off of `0.1.0`; one signed commit `sign(0.1.0): quinn.qa@labconnect.example` carries only `.purlin/evidence/package/0.1.0.json` and `.purlin/evidence/package/0.1.0.signoffs/quinn-qa.json`, `signed/0.1.0` names it, and the walk prints `Tagged signed/0.1.0 at <sha7>.`
- PROOF-237 (RULE-120): After Quinn signs `0.1.0`, `pat.product@labconnect.example` signs it; Pat's commit carries only `.purlin/evidence/package/0.1.0.signoffs/pat-product.json`, and `signed/0.1.0` still names Quinn's commit
- PROOF-238 (RULE-121): A clone of a bare repository on disk holds one commit of its own the host lacks, and signs `2.1.0`; it writes `signed/2.1.0`, and afterwards the bare repository holds no tag, its `main` has not moved, and the clone has no `FETCH_HEAD`
- PROOF-239 (RULE-121): A tag named `signed` already exists, so git cannot write a tag under `signed/`; the first sign-off of `2.1.0` prints `No tag: git could not write signed/2.1.0: <git's message>.`
- PROOF-240 (RULE-122): The package the first sign-off of `2.1.0` committed is checked with `--check .purlin/evidence/package/2.1.0.json`; it exits 0 and prints exactly `The package matches its fingerprint.`
- PROOF-241 (RULE-122): That package has its `version` changed to `2.1.1` and is checked with `--check`; it exits 1 and its one line begins `The package does not match its fingerprint: `
- PROOF-242 (RULE-123): Anchor `screens` `RULE-1` has `PROOF-2` marked `@manual` and `PROOF-3`, whose test skips with `nothing to check: this project has no screens`; its stop reads `  Linux/Unix: passed on dana-laptop; nothing to check for PROOF-3: this project has no screens`
