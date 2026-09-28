# Feature: signatures

> Description: The attestation that a rule, its proof, its test and the audit
>   that read them belong together, and the command that writes one. One
>   signature is one file, so two signatures never conflict, and it binds the
>   hashes of the rule text, the proof text and the test body, plus what the
>   audit found. A person writes
>   every one of them, as one signed commit; CI writes none, and each names
>   the machine it was made on. With no argument the command walks the queue
>   one rule at a time and, when every rule meets the gate, writes the
>   tag that marks the commit. It signs nothing over evidence that is not
>   committed. What it may do at all scales with the project's gate: nothing
>   under `passed`, the walk under `strong`, a counting signature under
>   `signed`.
> Scope: scripts/mcp/purlin/signatures.py, scripts/review/sign.py
> Stack: python/stdlib (argparse, json, subprocess), git signed commits

## Rules

- RULE-1: The three hashes a signature binds come back together with the kind of the test hash
- RULE-2: A rule the project does not declare has no hashes at all [level: passed]
- RULE-3: Reflowing a rule's whitespace or changing its level tag leaves the triple where it was, because the triple binds the rule text with its tag stripped
- RULE-4: Editing the rule text, the proof text or the test body moves the triple
- RULE-5: A rule proved only by a `@manual` proof records `manual` as the kind of its test hash instead of naming a test file
- RULE-6: A signature stays current only while the rule text, the proof text, the test body and what the audit observed still hash to what it bound; the level it records is not compared, so marking a rule differently leaves it current
- RULE-7: A signature whose triple no longer matches still comes back from the reader, so the signed cell can read `stale` rather than `unsigned`
- RULE-8: A signature file is named for the rule, the first eight characters of the triple and the signer's slug, the email local part lowercased with every character that is not a letter or a digit replaced by a hyphen
- RULE-9: A signature carries schema `purlin-signature/1` and exactly the fields the format names: the triple, the three hashes and their kind, the audit hash, the level, the signer, the machine, the operating system, the note, the timestamp, the gate and the evidence file
- RULE-10: The signature reader finds a signature in the `<feature>.signatures/` directory beside its spec
- RULE-11: With no feature named the command opens with `Queue: <n> rules. <h> hand checks, <s> signatures.`, walks the queue one rule at a time, showing the rule, its proofs and what the audit found under a line naming the rule, its level and its need, takes one of the three answers sign, case or skip at each stop, carries the line a person writes when signing a hand check as that signature's note, writes nothing until the walk closes and closes with `Walked <n> rules: <s> signed, <c> cases added, <k> skipped.`
- RULE-12: `--batch` signs, in one signed commit, every rule in the queue; a bare feature signs the rules of that feature in the queue alone
- RULE-13: `--note` puts one line on the signature, for a `@manual` proof or a review the model could not settle; `--note` with no rule named, or with no line, exits 2
- RULE-14: Under `passed` the command writes no signature, names what `purlin:init --gate strong` would add and exits 2
- RULE-15: Under `strong` a signature on a named rule that is not in the queue says a signature is required only under `signed`, and writes it anyway; a rule in the queue is signed without that line
- RULE-16: What a bare feature and `--batch` sign is read off the payload's own queue, in the order the walk reads it
- RULE-17: With no signing configured the command writes no signature, exits 1 and prints the three git config commands that set signing up
- RULE-18: One invocation is one signed commit, whatever number of rules it carries, and its subject names the feature and every rule signed
- RULE-19: A batch spanning more than one feature names each feature with its own rules in the subject [level: passed]
- RULE-20: Under `signed` a signature counts when the commit that added it is signed and verifies, whoever its author is and whoever last committed to the test file; an unsigned signing commit is refused with the reason `the signing commit is not signed`; under `strong` a committed signature counts
- RULE-21: The command refuses nobody for who they are: a person with signing configured signs, and no config key names who may sign
- RULE-22: The command exits 0 for `--help`, and an unknown option exits 2 whether or not a feature is named [level: passed]
- RULE-23: A signature counts on whatever commit carries it: one committed signed on a side branch counts at the gate `signed` on that branch, before any merge
- RULE-41: A signature records under `level` the rule's level when it was signed, and logs it rather than locking it: marking the rule differently afterwards leaves the signed cell reading `signed`
- RULE-42: The evidence a signature names is the feature's own evidence file, `.purlin/evidence/local/<feature>.json` where it exists and the `ci` one otherwise, and it is null where the feature has none
- RULE-43: The audit hash a signature binds is taken over the feature's test strength and the `verdict` and sorted `findings` of the audit entry for the rule's current hashes, and over nothing that moves on its own, so re-running the same audit over the same code stales nothing and an audit that finds something new stales the signature; a rule with no audit entry binds the hash of the empty string
- RULE-45: When the walk closes and every rule meets the gate the command writes the annotated tag `signed/<version>`, taking the version from the `VERSION` file at the project root and falling back to the config's, with a message naming the commit and the gate, and prints `Run: git push origin signed/<version>`; it pushes nothing
- RULE-46: No tag is written while any rule falls short of the gate, and the command says how many of how many; no tag is written over one that is already there, and `--release <name>` names another
- RULE-48: Under the gate `signed`, naming a rule whose `[level: ...]` tag is `passed` or `strong` refuses it with `sign: <feature> <RULE-N> is marked [level: <level>]; it asks for no signature.` and writes no signature for it; with nothing else named, the command exits 1
- RULE-49: The command signs no rule whose feature has evidence that is written and not committed, and writes no tag while any feature has such evidence; each such feature is named once, as `sign: <feature> has evidence that is not committed. Run: purlin:test --commit`
- RULE-50: A signature records `machine`, the host's name as its operating system reports it, and `os`, `windows`, `macos` or `linux`, beside the signer and the time; neither is hashed or compared, so a signature reads the same whichever machine made it
- RULE-47: With `trust: remote` the command refuses a rule with a proof that has a test when its feature's `ci` evidence holds no section current for this code, printing `sign: <feature> RULE-N has no ci test run for this code; run purlin:test --remote first`; a rule whose proofs are all `@manual` is not refused, and with `trust: local`, the default, it signs what this machine ran

## Proof

- PROOF-1 (RULE-1): Read the hashes of `login RULE-1` in a project with evidence; verify the rule, proof and test hashes are each 64 characters and the kind is `file`
- PROOF-2 (RULE-2): Read the hashes of `login RULE-99`, which the spec does not declare; verify all five values are `none`
- PROOF-3 (RULE-3): Read the triple, rewrite the rule line with doubled spaces and `[level: signed]` in place of `[level: passed]`, and read it again; verify the two values are equal
- PROOF-4 (RULE-4): Read the triple, then change `200` to `201` in the rule, then extend the proof text, then add a comment to the test; verify each of the three values differs from the first
- PROOF-5 (RULE-5): Retag `PROOF-2` as `@manual` and read the hashes of `RULE-2`; verify the kind of the test hash is `manual`
- PROOF-6 (RULE-6): Write a signature, then load the signatures back; verify exactly 1 is current
- PROOF-7 (RULE-6): Write a signature, then edit the rule text; verify zero signatures are current
- PROOF-8 (RULE-6): Write a signature, then edit the proof text; verify zero signatures are current
- PROOF-9 (RULE-6): Write a signature, then edit the test so its assertion reads `== 200 or True`; verify zero signatures are current
- PROOF-10 (RULE-6): Write a signature, then mark the rule `[level: strong]` in place of `[level: passed]`; verify exactly 1 signature is still current
- PROOF-11 (RULE-7): Write a signature, then edit the rule text; verify the reader still returns exactly 1 signature for the rule, that its signer is `jane@acme.com` and that it is no longer current
- PROOF-12 (RULE-8): Write a signature for the address `Rich.LaBarca+purlin@example.com`; verify the only file in the signatures directory is named `RULE-1.<hash8>.rich-labarca-purlin.json` for that rule's triple
- PROOF-13 (RULE-9): Write a signature naming the evidence file; verify its schema is `purlin-signature/1`, its field names are exactly the 17 the format lists, its `level` is the rule's level, its triple is the first 16 characters of the rule's triple, its `note` is null, its `evidence` reads `.purlin/evidence/local/login.json` and its timestamp ends `Z`
- PROOF-14 (RULE-10): Write a signature for a rule, then load the signatures; verify exactly 1 comes back and its signer is `jane@acme.com`
- PROOF-15 (RULE-12): Run `--batch` in a project at gate `signed` whose `RULE-1` is marked `[level: passed]`; verify it exits 0, prints `Signed 1 rule in` and writes a signature for `RULE-2` alone
- PROOF-16 (RULE-13): Run `login RULE-2 --note "I ran the lockout by hand."`; verify it exits 0 and the signature's `note` reads `I ran the lockout by hand.`
- PROOF-17 (RULE-13): Run `login RULE-1 --note` with no line, `login --note "a line"` with no rule, and `--batch --note "a line"`; verify each exits 2
- PROOF-18 (RULE-14): Run `login RULE-1` in a project at gate `passed` with signing configured; verify it exits 2, prints `the gate is passed, which asks for no signature.` and `purlin:init --gate strong`, and that the signatures directory is empty
- PROOF-19 (RULE-15): Run `login RULE-1` in a project at gate `strong` whose passed cell is not met; verify it exits 0, prints `required only under the gate signed` and writes exactly 1 signature
- PROOF-20 (RULE-16): Read what a batch signs at gate `signed` in a project whose `RULE-1` is marked `[level: passed]`; verify it is `login RULE-2` alone, that signing it leaves nothing in the queue, and that changing `401` to `403` in the rule puts it back
- PROOF-21 (RULE-17): Run the command in a checkout with no signing key; verify it exits 1, prints `git config gpg.format ssh`, `git config user.signingkey ~/.ssh/id_ed25519.pub` and `git config commit.gpgsign true`, and that the signatures directory is empty
- PROOF-22 (RULE-17): Run the command in a separate process against a checkout with no signing key; verify it exits 1 and prints `git config gpg.format ssh`
- PROOF-23 (RULE-18): Configure a throwaway signing key and run the command for the whole feature; verify it exits 0, writes 2 signatures, and that the one commit it made reports signature `G` with the subject `sign(login): RULE-1 RULE-2`
- PROOF-24 (RULE-19): Build the subject for `login RULE-1` with `login RULE-2`, then for `login RULE-1` with `billing RULE-3`; verify they read `sign(login): RULE-1 RULE-2` and `sign(batch): login RULE-1, billing RULE-3`
- PROOF-25 (RULE-20): Run the command to sign `RULE-1` as `jane@acme.com` with signing configured, in a project whose test file `jane@acme.com` last committed, then count the signature at gate `signed` and at gate `strong`; verify both count. Commit a second signature with commit signing turned off and count it; verify it is refused at `signed` with `the signing commit is not signed` and counts at `strong`
- PROOF-27 (RULE-21): At gate `signed`, run `--batch` as `jane@acme.com` with signing configured; verify it exits 0, writes a signature for `RULE-2` and never prints `purlin:init --gate signed`
- PROOF-28 (RULE-22): Run the command with `--help`, with `login --nope` and with no argument; verify the exit codes are 0, 2 and 2
- PROOF-29 (RULE-23): In a project at gate `signed`, run the command to sign `RULE-2` on a branch called `side` that `main` does not carry; build the payload on `side` and verify the rule's signed cell reads `signed` with no reason naming a branch
- PROOF-30 (RULE-16): In a project at gate `signed` whose unmarked rule has no audit entry, verify the queue is empty and a batch would sign nothing; write an audit entry for it that did not settle and verify the queue is one row, `login RULE-2` with the need `hand check` although its level also asks for a signature, and that it is what a bare feature or `--batch` would sign
- PROOF-31 (RULE-11): At gate `signed`, tag `PROOF-2` `@manual` and run the walk, answering `sign` with `The lockout page read 401 and "denied".`; verify the output opens `Queue: 1 rule. 1 hand check, 0 signatures.`, that the one stop opens `login RULE-2   level signed   hand check` followed by `Rule` and the rule text, lists `PROOF-2 (@manual)` and carries `What the audit found`, that 1 commit is made and the signature's `note` is that line, and that the close reads `Walked 1 rule: 1 signed, 0 cases added, 0 skipped.` Sign a rule, reword it and walk again; verify its stop opens `login RULE-2   level signed   signature   stale: hashes changed after the signature` and reads `Strong. It found nothing.`
- PROOF-32 (RULE-11): Run the walk over a project at gate `signed`, answering `skip` at every stop; verify 2 rules are skipped, the signatures directory is empty, the close reads `Walked 2 rules: 0 signed, 0 cases added, 2 skipped.` and prints `Run: purlin:sign`, and the queue still holds both rules
- PROOF-33 (RULE-11): Run the walk over the same project, answering `case` with `it should also reject an expired token` at every stop; verify 2 cases come back, the signatures directory is empty, the close prints that sentence and it prints `Run: purlin:build`
- PROOF-62 (RULE-41): At gate `signed`, sign the unmarked `RULE-2` and verify the file's `level` reads `signed` and the signed cell reads `signed`; mark the rule `[level: strong]`, run its tests again, and verify the signed cell still reads `signed`
- PROOF-63 (RULE-42): In a project whose run wrote `.purlin/evidence/local/login.json`, verify the evidence a signature names for `login` is that path; write a `ci` file beside it and verify the local one is still named; remove the local one and verify the `ci` one is named; verify a feature with no evidence names none
- PROOF-64 (RULE-43): Build the audit hash over an entry reading `strong` with no finding at strength 90; verify it equals the hash of the same entry with another `at`, `commit` and `path`, differs from an entry reading `weak` with one finding, from one reading `undecided` and from the same entry at strength 70, that the order of the findings does not move it, and that no entry hashes to the sha256 of the empty string
- PROOF-65 (RULE-43): Sign a rule whose level is `signed` and whose audit entry reads `strong` with no finding and verify its signed cell reads `signed`; write an entry for the same hashes finding `PROOF-2 reads the status alone.` and verify the cell reads `stale`
- PROOF-67 (RULE-45): Walk with every rule already signed in a project whose `VERSION` file reads `2.1.0`; verify the walk prints `Queue: 0 rules. 0 hand checks, 0 signatures.`, that the annotated tag `signed/2.1.0` exists, that its message names the commit and the gate, that the last line is `Run: git push origin signed/2.1.0`, and that `git log origin/main` is unchanged because nothing was pushed
- PROOF-68 (RULE-46): Walk a project holding one unsigned rule; verify no tag is written and the output reads `No tag: 1 of 2 rules do not meet the gate signed.` Sign it, walk again with `--release beta`, and verify the tag is `signed/beta`; walk a third time and verify it reads `No tag: signed/beta is already written.`
- PROOF-69 (RULE-47): Set `trust: remote` and sign a rule whose only evidence is `local`; verify it is refused and the line reads `sign: login RULE-2 has no ci test run for this code; run purlin:test --remote first`. Commit a current `ci` section and verify it is not refused; change the scoped code so that section is out of date and verify it is refused again. Tag the rule's only proof `@manual` and verify it is not refused while a rule beside it whose proof has a test is. Under `trust: local` verify nothing is refused
- PROOF-70 (RULE-12): At gate `strong`, write an audit entry for `login RULE-2` that did not settle so it is in the queue, then run `--batch` with signing configured; verify it exits 0, prints `Signed 1 rule in`, writes a signature for `RULE-2` alone and never prints `required only`. Do the same with a bare `login` in a fresh project; verify the same
- PROOF-71 (RULE-15): At gate `strong`, with `login RULE-2` in the queue, run `login RULE-2`; verify it exits 0, writes exactly 1 signature and never prints `required only under the gate signed`
- PROOF-72 (RULE-48): At gate `signed` with signing configured, run `login RULE-1` on the `[level: passed]` rule; verify it exits 1, prints `sign: login RULE-1 is marked [level: passed]; it asks for no signature.` and writes no signature. Mark it `[level: strong]` and verify the line names `[level: strong]`; run `login RULE-1 RULE-2` and verify only `RULE-2` is signed
- PROOF-73 (RULE-49): At gate `signed`, write the feature's evidence again and commit nothing; run `login RULE-2`, then `--batch`, then the walk answering `sign`; verify the first two exit 1, each prints `sign: login has evidence that is not committed. Run: purlin:test --commit`, and no signature is written by any of the three. Commit the evidence and run `login RULE-2` again; verify it exits 0, writes 1 signature and prints no such line
- PROOF-74 (RULE-49): With every rule signed, write the feature's evidence again and commit nothing, then ask for the tag; verify no tag is written and the only line printed is `sign: login has evidence that is not committed. Run: purlin:test --commit`; commit it and verify `signed/2.1.0` is written
- PROOF-75 (RULE-50): Sign `login RULE-2` and read the file; verify `machine` equals the host's name as the operating system reports it and `os` is this machine's `windows`, `macos` or `linux`. Rewrite them as `another-machine` and `windows`, commit, and verify the signed cell still reads `signed`
