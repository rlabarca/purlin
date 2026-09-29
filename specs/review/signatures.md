# Feature: signatures

> Description: The attestation that a rule, its proof, its test, the code its
>   feature lists and what the audit found belong together, over the results of
>   the machine each system's tests ran on, and the command that writes one.
>   One signature is one file, so two signatures never conflict. A person
>   writes every one of them, as one signed commit, and a run writes none. With
>   no argument the command walks the rules that wait for a person one at a
>   time and, at the gate `signed` when nothing else is left, writes the
>   evidence package and the signed tag that marks the commit.
> Scope: scripts/mcp/purlin/signatures.py, scripts/review/sign.py
> Stack: python/stdlib (json, subprocess), git signed commits, SSH keys

## Rules

- RULE-1: The rule, proof and test hashes a signature is made over come back together with the kind of the test hash
- RULE-2: A rule the project does not declare has no hashes at all
- RULE-3: Reflowing a rule's whitespace leaves the hash a signature is made over where it was
- RULE-4: Editing the rule text, the proof text or the test body moves the hash a signature is made over
- RULE-5: A rule proved only by a `@manual` proof records `manual` as the kind of its test hash instead of naming a test file
- RULE-6: A signature stays current only while the rule text, the proof text, the test body, the code its feature lists and what the audit found still hash to what it was made over
- RULE-7: A signature that is no longer current still comes back from the reader with its signer, and at the gate `signed` its rule is `to sign` again
- RULE-8: A signature file is named for the rule, the first eight characters of the hash it is made over and the signer's slug, the email local part lowercased with every character that is not a letter or a digit replaced by a hyphen
- RULE-9: A signature carries schema `purlin-signature/2` and exactly the fields signature format 11 names, its `signed_hash` taken over the feature it applies to, the rule, proof, test, code and audit hashes, and the machines the tests ran on
- RULE-10: The signature reader finds a signature in the `<feature>.signatures/` directory beside its spec
- RULE-11: With no feature named the command opens on the `to test by hand` and `to sign` lines of `Left to do`, or on `Nothing is waiting for someone to test by hand or to sign.` when both are zero, walks those rules one at a time showing the rule, its proofs and what the audit found under a line naming the rule and its work left, takes one of the three answers sign, case or skip at each stop, carries the line a person writes when signing a hand check as that signature's note and signs with no note when the line is empty, writes nothing until the walk closes and closes with `Walked <n> rules: <s> signed, <c> cases added, <k> skipped.`
- RULE-12: `--all` signs, in one signed commit, every rule that waits for a person; a bare feature signs the waiting rules of that feature alone; both work at every gate
- RULE-13: `--note` puts one line on the signature, for a `@manual` proof; `--note` with no rule named, with `--all`, or with no line, exits 2
- RULE-16: What a bare feature and `--all` sign is read off the rules whose work left is `to test by hand` or `to sign`, each rule once, in the order the walk shows them
- RULE-17: With no SSH key to sign with the command writes no signature, exits 1 and prints `No key to sign with. These commands set one up:`, then `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""` only while that file does not exist, `git config gpg.format ssh` and `git config user.signingkey ~/.ssh/id_ed25519.pub`
- RULE-18: One invocation is one signed commit, whatever number of rules it carries, and its subject names the feature and every rule signed
- RULE-19: A batch spanning more than one feature names each feature with its own rules in the subject
- RULE-20: A signature counts when the last commit that touched its file carries a signature, made with any key and whoever its author; otherwise it does not count, with the reason `the commit that added it is not signed`; the gate plays no part
- RULE-21: The command signs for anyone with a key to sign with, whatever their name or email
- RULE-22: The command exits 0 for `--help`, and an unknown option exits 2 whether or not a feature is named
- RULE-23: A signature counts on whatever commit carries it: one committed signed on a side branch counts at the gate `signed` on that branch, before any merge
- RULE-42: The evidence a signature names is the feature's own evidence file, `.purlin/evidence/local/<feature>.json` where it exists and the `ci` one otherwise, and it is null where the feature has none
- RULE-43: The audit hash a signature is made over is taken over the feature's test strength and the `verdict` and sorted `findings` of the audit entry for the rule's current hashes, and over nothing that moves on its own or names the judge, not the `model` nor the `criteria`, so re-running the same audit over the same code leaves a signature current and an audit that finds something new ends it; a rule with no audit entry binds the hash of the empty string
- RULE-45: At the gate `signed`, when nothing is left but the tag, the command writes `signed/<version>` as a signed tag whose message reads `Nothing left to do at the gate signed.` with the commit and the gate, prints `Tagged signed/<version> at <sha7>.` then `Nothing left to do. Push the tag to release it: git push origin signed/<version>`, and pushes nothing; the walk that signs the last rules writes it
- RULE-46: While any work but the tag is left the command writes no tag and prints the summary ending; no tag is written over one that already exists, which prints `No tag: <tag> is already written. Name another with --release <name>.`, and `--release <name>` names another
- RULE-49: No tag is written while any feature has results that are written and not committed; each such feature is named once, as `No tag: <feature> has results that are not committed. Run purlin:test --commit.`
- RULE-50: A signature records the signer's email as git holds it, git's `user.name` as the signer's name, and the fingerprint of the key it was signed with
- RULE-53: Before it writes `signed/<version>` the command writes the evidence package for that version, commits it as a signed commit whose subject is `purlin: evidence at <sha7>` of the commit below it, and writes the tag on that commit; when the package cannot be written or committed it writes no tag and prints `No tag: the evidence package was not committed: <why>.`
- RULE-54: Below the gate `signed` the command writes no tag and no evidence package, and the walk ends on the summary ending
- RULE-55: No tag is written while `git status` lists a path outside `.purlin/`; the command prints `No tag: the working tree holds changes that are not committed, so the results do not describe a commit. Commit them, then run purlin:sign.`
- RULE-56: The version a tag is named for is the first one stated by the `VERSION` file at the root, `package.json`'s `version`, `pyproject.toml`'s `[project]` then `[tool.poetry]` `version`, and the `<Version>` of a root `*.csproj`
- RULE-57: With no version stated and no `--release`, no tag is written and the command prints `No version: nothing in this project states one. Name it with --release <version>, or write it to a VERSION file.`
- RULE-58: When it has signed, the command prints `Signed <n> rules as <email> with the key ending ...<last 4>.`, reading `1 rule` for one
- RULE-59: An anchor's rule is signed once in each feature it applies to: one file per feature, each made over that feature's code, so a change to one feature's files ends that one signature alone
- RULE-60: The key fingerprint is read from `user.signingkey`, a public key path, a private key path with its `.pub` beside it, or a `key::` literal, and reads as `ssh-keygen -l` prints it; a key that is not an SSH key is no key
- RULE-61: A signature is made over the machine each system's tests ran on: another machine for a system it names ends it, a system it names that is gone ends it, and a system it does not name ends nothing
- RULE-62: A rule named by id is signed at every gate, whatever work it has left
- RULE-63: `--all`, or a bare feature, with nothing waiting for a person prints `Nothing is waiting for someone to test by hand or to sign.`, then the summary ending, writes no signature and exits 0
- RULE-64: A rule named by id that no spec has prints `<feature> <RULE-N> is not a rule any spec has.`, writes no signature and exits 1

## Proof

- PROOF-1 (RULE-1): In a project whose `login RULE-1` has a passing test on record, its hashes are read: the rule hash is the sha256 of `Valid credentials return 200 with a session token`, the proof hash of `PROOF-1` and its text, the test hash of the test's path, name and git blob id, and the kind reads `file`
- PROOF-2 (RULE-2): Read the hashes of `login RULE-99`, which the spec does not declare; verify no rule is found, so there is no hash to bind
- PROOF-3 (RULE-3): The signed hash of `login RULE-1` is read, then its rule line is rewritten with doubled spaces between words; the hash read again equals the first, character for character
- PROOF-4 (RULE-4): The signed hash of `login RULE-1` is read, then `200` is changed to `201` in the rule text; the hash read again differs
- PROOF-82 (RULE-4): The signed hash of `login RULE-1` is read, then `that expires` is added to the end of its proof; the hash read again differs
- PROOF-83 (RULE-4): The signed hash of `login RULE-1` is read, then a comment is added to the rule's test and committed; the hash read again differs
- PROOF-5 (RULE-5): In a project whose `login RULE-2` has one proof, `PROOF-2`, tagged `@manual`, the hashes of `RULE-2` are read; the kind of its test hash reads `manual`, not `file`. At the edge of "only", `login RULE-1` is given a second proof, `PROOF-3`, tagged `@manual`, beside its tested `PROOF-1`; the kind of its test hash reads `file`, not `manual`
- PROOF-6 (RULE-6): A signature is written for `login RULE-1` and nothing else changes; of the rule's signatures read back, exactly 1 is current. An audit entry for the same rule, proof and test is then written, reading `weak` with the finding `PROOF-1 reads the status alone.`, and 0 of the rule's signatures are current
- PROOF-7 (RULE-6): A signature is written for `login RULE-1`, then its rule text changes from `a session token` to `a signed session token`; 0 of the rule's signatures are current
- PROOF-8 (RULE-6): A signature is written for `login RULE-1`, then its proof text changes from `verify 200 and a token` to `verify 200, a token and a cookie`; 0 of the rule's signatures are current
- PROOF-9 (RULE-6): A signature is written for `login RULE-1`, then its test is edited so its check reads `== 200 or True`, which passes whatever the login returns, and committed; 0 of the rule's signatures are current
- PROOF-84 (RULE-6): A signature is written for `login RULE-1`, then `src/login.py`, the file the feature lists, is changed to return 401 always; 0 of the rule's signatures are current
- PROOF-11 (RULE-7): `jane@acme.com` signs `login RULE-1`, then its rule text changes from `a session token` to `two session tokens`; the reader still returns exactly 1 signature for the rule, its signer reads `jane@acme.com`, and it is not current
- PROOF-85 (RULE-7): At the gate `signed`, `login RULE-2` is signed with the command; its `401` is then changed to `403`, its results recorded again and its audit written again; the rule's work left reads `to_sign`
- PROOF-12 (RULE-8): `Rich.LaBarca+purlin@example.com` signs `login RULE-1`; the one file in `login.signatures/` is named `RULE-1.<h>.rich-labarca-purlin.json`, where `<h>` is the first 8 characters of the rule's signed hash: the capitals are lowercased and the `.` and the `+` each become a hyphen
- PROOF-13 (RULE-9): `jane@acme.com` signs `login RULE-1` under the gate `strong` with no note. The signature reads schema `purlin-signature/2` and carries exactly the 19 fields signature format 11 names; its `signed_hash` is the sha256 of the feature, the rule, proof, test, code and audit hashes and the machines, one per line; `note` is null and `timestamp` ends in `Z`
- PROOF-14 (RULE-10): `jane@acme.com` signs `login RULE-1`, whose spec is `specs/auth/login.md`, and the project's signatures are read; exactly 1 comes back for `login RULE-1`, its signer reads `jane@acme.com`, and its file lies in `specs/auth/login.signatures/`. Copies of that file placed in `specs/login.signatures/`, `signatures/` and `specs/auth/signatures/` are not read: the rule still has exactly 1 signature, the one beside the spec, and once that one is removed it has none
- PROOF-31 (RULE-11): At the gate `signed`, with `login RULE-1` to sign and the one proof of `RULE-2` tagged `@manual`, the walk opens `1 rule to test by hand: purlin:sign` then `1 rule to sign: purlin:sign`; the stop for `RULE-2` opens `login RULE-2   to test by hand`, then `Rule` and its text, `PROOF-2 (@manual)` and `What the audit found`
- PROOF-86 (RULE-11): At the gate `signed`, with `login RULE-2` a hand check, the walk is answered `sign` with `The lockout page read 401.` at `RULE-2` and `skip` at `RULE-1`; the signature's note reads that line and the walk closes `Walked 2 rules: 1 signed, 0 cases added, 1 skipped.`
- PROOF-88 (RULE-11): At the gate `signed`, with `login RULE-2` a hand check, the walk is answered `sign` with an empty line at `RULE-2`; the signature is written in 1 commit, and its note is null
- PROOF-87 (RULE-11): At the gate `signed`, with both `login` rules to sign, the walk is answered `sign` at each of its 2 stops; at each stop no signature file exists and HEAD has not moved, and once it closes 2 signature files sit in one commit made on the commit the walk began at
- PROOF-32 (RULE-11): At the gate `signed`, with both `login` rules to sign, the walk is answered `skip` at each stop; no signature file is written, it closes `Walked 2 rules: 0 signed, 0 cases added, 2 skipped.`, and its last line reads `  2 rules to sign: purlin:sign`
- PROOF-33 (RULE-11): At the gate `signed`, the walk is answered `case` with `it should also reject an expired token` at `login RULE-2`; no signature file is written and the close carries `  login RULE-2   add this proof line: it should also reject an expired token`
- PROOF-89 (RULE-11): At the gate `strong`, with both rules passing and audited strong, the walk is run; its first line reads `Nothing is waiting for someone to test by hand or to sign.`
- PROOF-15 (RULE-12): At the gate `signed`, with both `login` rules to sign, `--all` is run; it exits 0, its output opens `Signed 2 rules as jane@acme.com with the key ending ...`, it writes a signature for `RULE-1` and one for `RULE-2`, and it adds 1 commit carrying an SSH signature
- PROOF-90 (RULE-12): At the gate `signed`, with both `login` rules to sign and `billing RULE-1` a hand check, `--all` adds 1 commit under the subject `sign(batch): billing RULE-1, login RULE-1 RULE-2` and writes 1 file beside the billing spec
- PROOF-70 (RULE-12): At the gate `strong`, with the one proof of `login RULE-2` tagged `@manual`, `--all` exits 0 and writes one signature, for `RULE-2`
- PROOF-91 (RULE-12): At the gate `strong`, with the one proof of `login RULE-2` tagged `@manual`, a bare `login` exits 0 and writes one signature, for `RULE-2`
- PROOF-92 (RULE-12): At the gate `passed`, with the one proof of `login RULE-2` tagged `@manual`, `--all` exits 0 and writes one signature, for `RULE-2`
- PROOF-16 (RULE-13): At the gate `signed`, with signing set up, `login RULE-2 --note "I ran the lockout by hand."` is run; it exits 0, and the signature written for `RULE-2` carries the note `I ran the lockout by hand.`
- PROOF-17 (RULE-13): At the gate `signed`, `login RULE-1 --note` with no line after it exits 2, prints `sign.py: --note needs the line you want on the signature.` below the usage line, and writes no file and no commit
- PROOF-93 (RULE-13): At the gate `signed`, `login --note "a line"`, naming no rule, exits 2, prints `sign.py: --note names a feature and the rules it carries.` below the usage line, and writes no file and no commit
- PROOF-94 (RULE-13): At the gate `signed`, `--all --note "a line"` exits 2, prints `sign.py: --note names a feature and the rules it carries.` below the usage line, and writes no file and no commit
- PROOF-20 (RULE-16): At the gate `signed`, with both `login` rules to sign and `billing RULE-1` a hand check, the walk shows `billing RULE-1`, `login RULE-1` and `login RULE-2` in that order, and what `--all` signs is the same three in the same order
- PROOF-30 (RULE-16): At the gate `signed`, with the one proof of `login RULE-2` tagged `@manual` and no signature written, the rule's work left reads `to_test_by_hand`, and a bare `login` signs it once
- PROOF-21 (RULE-17): In a home with no `~/.ssh/id_ed25519`, in a checkout with no signing key, `login` is run; it exits 1, prints exactly `No key to sign with. These commands set one up:`, the `ssh-keygen` line and the two `git config` lines, and `login.signatures/` holds no file
- PROOF-95 (RULE-17): In a home where `~/.ssh/id_ed25519` exists, in a checkout with no signing key, `login` is run; it exits 1 and prints exactly the first line and the two `git config` lines, with no `ssh-keygen` line
- PROOF-22 (RULE-17): The command is started as its own process, the way a person runs it, for `login` in a home and a checkout with no key; it exits 1, prints exactly the four lines, and `login.signatures/` holds no file
- PROOF-23 (RULE-18): At the gate `signed`, the command is run for `login`, whose 2 rules both wait to be signed; it exits 0 and writes 2 signature files, and exactly 1 commit is added, carrying those 2 files and no other and an SSH signature, under the subject `sign(login): RULE-1 RULE-2`
- PROOF-24 (RULE-19): Build the subject for `login RULE-1` with `login RULE-2`, then for `login RULE-1` with `billing RULE-3`; verify they read `sign(login): RULE-1 RULE-2` and `sign(batch): login RULE-1, billing RULE-3`
- PROOF-25 (RULE-20): A signature for `login RULE-1` is committed signed with the signer's own key; it counts, with no reason
- PROOF-96 (RULE-20): A signature for `login RULE-1` is committed with commit signing off; it does not count, with the reason `the commit that added it is not signed`
- PROOF-97 (RULE-20): A signature for `login RULE-1` is committed signed with a key made for the check that no setting and no file names; it counts
- PROOF-98 (RULE-20): A signature for `login RULE-1` is committed signed with Jane's key under the author `Bob <bob@else.org>`; it counts
- PROOF-27 (RULE-21): At the gate `signed`, `omar@example.org`, who has not signed in this project before, sets up a key and runs `--all`; it exits 0 and writes signatures for `RULE-1` and `RULE-2`, each file named for `omar`
- PROOF-28 (RULE-22): Run the command with `--help`, with `login --nope` and with `--nope` alone; the exit codes are 0, 2 and 2
- PROOF-29 (RULE-23): At the gate `signed`, a branch `side` is made from `main` and `login RULE-2` is signed on it; the command exits 0, `main` holds no signature file, and on `side` the rule's signed cell reads `signed` with no reason naming a branch or `main`. Back on `main`, which does not carry the signature, the rule's signed cell reads `unsigned`
- PROOF-63 (RULE-42): In a project whose test run wrote `.purlin/evidence/local/login.json`, the evidence a signature for `login` names is that path; with `.purlin/evidence/ci/login.json` written beside it, the local path is still named; with the local file removed, `.purlin/evidence/ci/login.json` is named; a feature with no evidence file names none, null. Signed and committed with only the `ci` file present, the signature file for `login RULE-1` reads `evidence` `.purlin/evidence/ci/login.json`; signed again with that file removed too, it reads `evidence` null
- PROOF-64 (RULE-43): The audit hash of an entry reading `strong` with no finding, at a test strength of 90, is unchanged when the entry's `at`, `commit`, `path`, `model` and `criteria` all differ; it changes for an entry reading `weak` with the finding `PROOF-2 reads the status alone.`, for one reading `undecided`, and for the same entry at a test strength of 70; two findings give the same hash in either order; and a rule with no audit entry binds the sha256 of the empty string, which begins `e3b0c442`
- PROOF-65 (RULE-43): At the gate `signed`, `login RULE-2`, audited strong with no finding, is signed; the same audit entry is written again with a later time, and the signature is still current
- PROOF-99 (RULE-43): At the gate `signed`, `login RULE-2`, audited strong with no finding, is signed; a new audit entry reading `weak` with the finding `PROOF-2 reads the status alone.` is written, and the signature is no longer current
- PROOF-67 (RULE-45): At the gate `signed`, with every rule signed and `VERSION` reading `2.1.0`, the tag is written; its object carries an SSH signature, and its message reads `Nothing left to do at the gate signed.`, a `Commit:` line naming in full the commit the signing ended on, and `Gate: signed`
- PROOF-100 (RULE-45): At the gate `signed`, with every rule signed and `VERSION` reading `2.1.0`, the tag is written; the last two lines printed are `Tagged signed/2.1.0 at <sha7>.`, naming the tagged commit, and `Nothing left to do. Push the tag to release it: git push origin signed/2.1.0`
- PROOF-101 (RULE-45): In a project whose `origin` holds `main`, with every rule signed, the tag is written; the remote's refs read exactly as they did before
- PROOF-81 (RULE-45): At the gate `signed`, with both `login` rules passing, audited strong and waiting to be signed, and `VERSION` reading `2.1.0`, the walk is answered `sign` at each stop; it signs both rules and writes `signed/2.1.0`, the one tag in the project
- PROOF-68 (RULE-46): At the gate `signed`, with both `login` rules waiting to be signed, the tag is asked for; no tag is written, and what is printed is the summary ending, its last line `  2 rules to sign: purlin:sign`
- PROOF-102 (RULE-46): At the gate `signed`, with every rule signed, the command is run with `--release beta`; it exits 0 and the one tag in the project is `signed/beta`
- PROOF-103 (RULE-46): At the gate `signed`, with every rule signed and `signed/beta` already written, the tag is asked for again with `--release beta`; no tag is written, it prints `No tag: signed/beta is already written. Name another with --release <name>.`, and `signed/beta` is the one tag
- PROOF-74 (RULE-49): At the gate `signed`, with every rule signed, the `login` results are recorded again and not committed; the tag is asked for, no tag is written, and the one line printed is `No tag: login has results that are not committed. Run purlin:test --commit.`
- PROOF-75 (RULE-50): Jane, set up in git as `Jane.Doe@Acme.com` with the name `Jane Doe`, signs `login RULE-2`; the signature's `signer` reads `Jane.Doe@Acme.com`, its `signer_name` `Jane Doe`, and its `key_fingerprint` what `ssh-keygen -l` prints for her key
- PROOF-78 (RULE-53): At the gate `signed`, with every rule signed and `VERSION` reading `2.1.0`, the tag is written; it names a new commit, carrying an SSH signature, that changes only `.purlin/evidence/package/2.1.0.json` under the subject `purlin: evidence at <sha7>` of its parent, and the package names that parent as its commit and matches its own fingerprint
- PROOF-79 (RULE-53): At the gate `signed`, with every rule signed and a file standing where the folder `.purlin/evidence/package/` would go, the tag is asked for; the output begins `No tag: the evidence package was not committed: `, no tag exists and HEAD has not moved
- PROOF-80 (RULE-54): At the gate `strong`, with both rules passing and audited strong and every file committed, the walk is run; its last line reads `Nothing left to do.`, no `signed/*` tag and no `.purlin/evidence/package/` folder exist, and HEAD has not moved
- PROOF-104 (RULE-54): At the gate `strong`, with the one proof of `login RULE-2` tagged `@manual`, the walk is answered `sign` with a note; it makes 1 commit, its output ends on the summary ending of the project as it then stands, and no tag and no package exist
- PROOF-105 (RULE-55): At the gate `signed`, with every rule signed, a new file `notes.txt` is written and not committed; the tag is asked for, no tag is written, and the one line printed is `No tag: the working tree holds changes that are not committed, so the results do not describe a commit. Commit them, then run purlin:sign.`
- PROOF-106 (RULE-56): With `VERSION` reading `2.1.0` and `package.json` stating `3.0.0`, the tag is named `signed/2.1.0`
- PROOF-107 (RULE-56): With no `VERSION` file and `package.json` stating `3.0.0`, the tag is named `signed/3.0.0`
- PROOF-108 (RULE-56): With only a `pyproject.toml` whose `[project]` table states `4.2.0` and whose `[tool.poetry]` table states `0.1.0`, the tag is named `signed/4.2.0`
- PROOF-109 (RULE-56): With only a `pyproject.toml` whose `[project]` table states no version and whose `[tool.poetry]` table states `0.5.1`, the tag is named `signed/0.5.1`
- PROOF-110 (RULE-56): With only a `Shop.csproj` at the root whose `<Version>` reads `1.4.0`, the tag is named `signed/1.4.0`
- PROOF-111 (RULE-57): At the gate `signed`, in a project that states no version, with every rule signed, the tag is asked for; no tag is written, and the one line printed is `No version: nothing in this project states one. Name it with --release <version>, or write it to a VERSION file.`
- PROOF-112 (RULE-58): At the gate `signed`, `jane@acme.com` signs `login RULE-2` by name; the command prints `Signed 1 rule as jane@acme.com with the key ending ...` followed by the last 4 characters of her key's fingerprint and a full stop
- PROOF-113 (RULE-59): With an anchor, `secure`, that `login` and `billing` both require, `secure RULE-1` is signed by name; 1 commit is added and `secure.signatures/` holds 2 files, one applying to `billing` and one to `login`
- PROOF-114 (RULE-59): With `secure RULE-1` signed for `login` and `billing`, `src/billing.py`, the file `billing` lists, is changed; the signature applying to `login` is still current and the one applying to `billing` is not
- PROOF-115 (RULE-60): With `user.signingkey` naming a public key file, the key fingerprint reads what `ssh-keygen -l` prints for that key
- PROOF-116 (RULE-60): With `user.signingkey` naming the private key file whose `.pub` sits beside it, the key fingerprint reads what `ssh-keygen -l` prints for that key
- PROOF-117 (RULE-60): With `user.signingkey` set to `key::` followed by the public key's text, the key fingerprint reads what `ssh-keygen -l` prints for that key
- PROOF-118 (RULE-60): With `gpg.format` set to `ssh` and `user.signingkey` set to a GPG key id, `3AA5C34371567BD2`, the command exits 1 and its first line reads `No key to sign with. These commands set one up:`
- PROOF-119 (RULE-61): A signature made over `macos` results from `jane-laptop` is compared with the rule's `macos` results from `jane-laptop` again; it is current
- PROOF-120 (RULE-61): A signature made over `macos` results from `jane-laptop` is compared with `macos` results from `omar-desktop`; it is not current
- PROOF-121 (RULE-61): A signature made over `macos` results from `jane-laptop` is compared with those results beside `windows` results from `remote runner, Windows`; it is current
- PROOF-122 (RULE-61): A signature made over `macos` results from `jane-laptop` and `windows` results from `remote runner, Windows` is compared with the `macos` results alone; it is not current
- PROOF-123 (RULE-62): At the gate `passed`, with no audit written, `login RULE-1` is signed by name; the command exits 0 and writes one signature, for `RULE-1`
- PROOF-124 (RULE-63): At the gate `strong`, with both rules passing and audited strong, `--all` is run; it prints `Nothing is waiting for someone to test by hand or to sign.`, then `2 rules. 2 pass their tests. 2 are strong.` and `Nothing left to do.`, writes no signature and exits 0
- PROOF-125 (RULE-64): `login RULE-9`, which the spec does not have, is signed by name; the command prints `login RULE-9 is not a rule any spec has.`, writes no signature and exits 1
