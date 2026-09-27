# Feature: signatures

> Description: The attestation that a rule, its proof, its test and the audit
>   that read them belong together, and the command that writes one. One
>   signature is one file, so two signatures never conflict, and it binds the
>   hashes of the rule text, the proof text and the test body, plus the pinned
>   design a design rule rests on and what the audit found. A person writes
>   every one of them, as one signed commit; CI writes none. With no argument
>   the command walks the Review list and then the Sign list one brief at a
>   time and, when every rule meets the gate, writes the tag that marks the
>   commit. What it may do at all scales with the project's gate: nothing
>   under `passed`, the walk and a hold under `strong`, a counting signature
>   under `signed`.
> Scope: scripts/mcp/purlin/signatures.py, scripts/review/sign.py
> Stack: python/stdlib (argparse, json, subprocess), git signed commits

## Rules

- RULE-1: The three hashes a signature binds come back together with the kind of the test hash and the pinned design hash of a design rule [bar: strong] [origin: eng]
- RULE-2: A rule the project does not declare has no hashes at all [bar: passed] [origin: eng]
- RULE-3: Reflowing a rule's whitespace or adding a tag leaves the triple where it was, because the triple binds the rule text with its tags stripped [bar: strong] [origin: eng]
- RULE-4: Editing the rule text, the proof text or the test body moves the triple [bar: strong] [origin: eng]
- RULE-5: A rule proved only by a `@manual` proof records `manual` as the kind of its test hash instead of naming a test file [bar: strong] [origin: eng]
- RULE-6: A signature stays current only while the rule text, the proof text, the test body, the bar and what the audit observed still hash to what it bound, so a bar re-tag stales it [bar: strong] [origin: eng]
- RULE-7: A signature whose triple no longer matches still comes back from the reader, so the signed cell can read `stale` rather than `unsigned` [bar: strong] [origin: eng]
- RULE-8: A signature file is named for the rule, the first eight characters of the triple and the signer's slug, the email local part lowercased with every character that is not a letter or a digit replaced by a hyphen [bar: strong] [origin: eng]
- RULE-9: A signature carries schema `purlin-signature/1` and exactly the fields the format names: the triple, the three hashes and their kind, the design hash, the audit hash, the bar, the signer, the note, the timestamp, the gate, the brief and the record [bar: strong] [origin: eng]
- RULE-10: The signature reader finds a signature in the `<feature>.signatures/` directory beside its spec and never reads a brief written under the same first two parts of a name [bar: strong] [origin: eng]
- RULE-11: With no feature named the command opens with `Review: <n> rules. Sign: <n> rules.`, walks the two lists one brief at a time, taking one of the four answers sign, case, hold or skip at each stop, and writes nothing until the walk closes [bar: strong] [origin: eng]
- RULE-12: `--batch` signs every rule that is signable now, in one signed commit [bar: strong] [origin: eng]
- RULE-13: `--note` puts one line on the signature, for a `@manual` proof or a review the model could not settle; `--note` with no rule named, or with no line, exits 2 [bar: strong] [origin: eng]
- RULE-14: Under `passed` the command writes no signature, names what `purlin:init --gate strong` would add and exits 2 [bar: strong] [origin: eng]
- RULE-15: Under `strong` a signature on a rule that needs none says a signature is required only under `signed`, and writes it anyway [bar: strong] [origin: eng]
- RULE-16: The signable rules are the ones the payload's sign list names, and the walk reads the review list first and the sign list after it [bar: strong] [origin: eng]
- RULE-17: With no signing configured the command writes no signature, exits 1 and prints the three git config commands that set signing up [bar: strong] [origin: eng]
- RULE-18: One invocation is one signed commit, whatever number of rules it carries, and its subject names the feature and every rule signed [bar: strong] [origin: eng]
- RULE-19: A batch spanning more than one feature names each feature with its own rules in the subject [bar: passed] [origin: eng]
- RULE-20: Under `signed` a signature counts only when the commit that added it is signed, its author is on the signer list and that author did not last touch the test; under `strong` a committed signature from anyone counts [bar: strong] [origin: eng]
- RULE-21: Someone off the signer list is refused by name, and at gate `signed` with no list at all the command names `purlin:init --gate signed` and exits 1 [bar: strong] [origin: eng]
- RULE-22: The command exits 0 for `--help`, and an unknown option exits 2 whether or not a feature is named [bar: passed] [origin: eng]
- RULE-23: A signature committed on a side branch is not on the protected branch until that branch merges [bar: strong] [origin: eng]
- RULE-40: `<feature> RULE-N --hold "<the missing case>"` writes `<RULE-N>.<hash8>.<holder-slug>.hold.json` binding the rule's hashes, with schema `purlin-hold/1`, the holder's email and the missing case as `reason`, and commits it signed as `hold(<feature>): RULE-N`; `--hold` with no reason, or with no rule named, exits 2 and writes nothing [bar: strong] [origin: eng]
- RULE-41: A signature binds the rule's bar, so writing one for a `[bar: strong]` rule and then retagging it `[bar: passed]` leaves the signed cell reading `stale` [bar: strong] [origin: eng]
- RULE-42: The brief a signature or a hold names is the file an audit committed for the same triple, under `.purlin/briefs/<source>/<feature>/`, and it is null where no audit wrote one [bar: strong] [origin: eng]
- RULE-43: The audit hash a signature binds is taken over the brief's test strength, its observations sorted and whether it settled, and over nothing that moves on its own, so re-running the same audit over the same code stales nothing and an audit that observes something new stales the signature; a rule with no brief binds the hash of the empty string [bar: strong] [origin: eng]
- RULE-44: A hold binds the triple, the design and the bar and not the audit, because a hold is a statement about the rule, the proof and the test that a re-audit does not answer [bar: strong] [origin: eng]
- RULE-45: When the walk closes and every rule meets the gate the command writes the annotated tag `signed/<version>`, taking the version from the `VERSION` file at the project root and falling back to the config's, with a message naming the commit and the gate, and prints `Run: git push origin signed/<version>`; it pushes nothing [bar: strong] [origin: eng]
- RULE-46: No tag is written while any rule falls short of the gate, and the command says how many of how many; no tag is written over one that is already there, and `--release <name>` names another [bar: strong] [origin: eng]
- RULE-47: With `trust: remote` the command refuses a rule whose passed cell carries no current `ci` platform entry, printing `sign: <feature> RULE-N has no ci test run for this commit; run purlin:test --remote first`; with `trust: local`, the default, it signs what this machine ran [bar: strong] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read the hashes of `login RULE-1` in a project with a record; verify the rule, proof and test hashes are each 64 characters, the kind is `file` and the design hash is `none` @integration
- PROOF-2 (RULE-2): Read the hashes of `login RULE-99`, which the spec does not declare; verify all five values are `none` @integration
- PROOF-3 (RULE-3): Read the triple, rewrite the rule line with doubled spaces and an added `[origin: pm]` tag, and read it again; verify the two values are equal @integration
- PROOF-4 (RULE-4): Read the triple, then change `200` to `201` in the rule, then extend the proof text, then add a comment to the test; verify each of the three values differs from the first @integration
- PROOF-5 (RULE-5): Retag `PROOF-2` as `@manual` and read the hashes of `RULE-2`; verify the kind of the test hash is `manual` @integration
- PROOF-6 (RULE-6): Write a signature, then load the signatures back; verify exactly 1 is current @integration
- PROOF-7 (RULE-6): Write a signature, then edit the rule text; verify zero signatures are current @integration
- PROOF-8 (RULE-6): Write a signature, then edit the proof text; verify zero signatures are current @integration
- PROOF-9 (RULE-6): Write a signature, then edit the test so its assertion reads `== 200 or True`; verify zero signatures are current @integration
- PROOF-10 (RULE-6): Write a signature, then raise the rule from `[bar: passed]` to `[bar: strong]`; verify zero signatures are current @integration
- PROOF-11 (RULE-7): Write a signature, then edit the rule text; verify the reader still returns exactly 1 signature for the rule, that its signer is `jane@acme.com` and that it is no longer current @integration
- PROOF-12 (RULE-8): Write a signature for the address `Rich.LaBarca+purlin@example.com`; verify the only file in the signatures directory is named `RULE-1.<hash8>.rich-labarca-purlin.json` for that rule's triple @integration
- PROOF-13 (RULE-9): Write a signature naming a brief and a record; verify its schema is `purlin-signature/1`, its field names are exactly the 16 the format lists, its triple is the first 16 characters of the rule's triple, its `note` is null and its timestamp ends `Z` @integration
- PROOF-14 (RULE-10): Write a signature and a brief for the same rule into one signatures directory, then load the signatures; verify exactly 1 comes back and its signer is `jane@acme.com` @integration
- PROOF-15 (RULE-12): Run `--batch` in a project at gate `signed` whose `sign_at` is `strong`; verify it exits 0, prints `Signed 1 rule in` and writes a signature for `RULE-2` alone @integration
- PROOF-16 (RULE-13): Run `login RULE-2 --note "I ran the lockout by hand."`; verify it exits 0 and the signature's `note` reads `I ran the lockout by hand.` @integration
- PROOF-17 (RULE-13): Run `login RULE-1 --note` with no line, `login --note "a line"` with no rule, and `--batch --note "a line"`; verify each exits 2
- PROOF-18 (RULE-14): Run `login RULE-1` in a project at gate `passed` with signing configured; verify it exits 2, prints `the gate is passed, which asks for no signature.` and `purlin:init --gate strong`, and that the signatures directory is empty @integration
- PROOF-19 (RULE-15): Run `login RULE-1` in a project at gate `strong` whose passed cell is not met; verify it exits 0, prints `required only under the gate signed` and writes exactly 1 signature @integration
- PROOF-20 (RULE-16): Read what is signable at gate `signed` with `sign_at` at `strong`; verify it is `login RULE-2` alone, that signing it leaves nothing signable, and that changing `401` to `403` in the rule makes it signable again @integration
- PROOF-21 (RULE-17): Run the command in a checkout with no signing key; verify it exits 1, prints `git config gpg.format ssh`, `git config user.signingkey ~/.ssh/id_ed25519.pub` and `git config commit.gpgsign true`, and that the signatures directory is empty @integration
- PROOF-22 (RULE-17): Run the command in a separate process against a checkout with no signing key; verify it exits 1 and prints `git config gpg.format ssh` @integration
- PROOF-23 (RULE-18): Configure a throwaway signing key and run the command for the whole feature; verify it exits 0, writes 2 signatures, and that the one commit it made reports signature `G` with the subject `sign(login): RULE-2 RULE-1` @integration
- PROOF-24 (RULE-19): Build the subject for `login RULE-1` with `login RULE-2`, then for `login RULE-1` with `billing RULE-3`; verify they read `sign(login): RULE-1 RULE-2` and `sign(batch): login RULE-1, billing RULE-3`
- PROOF-25 (RULE-20): Run the command to sign `RULE-1` as `jane@acme.com` with signing configured, then count the signature at gate `signed` against that list and against `someone@else.com`, and at gate `strong` against the second list; verify the first counts, the second is refused with a reason naming the signer list, and the third counts @integration
- PROOF-26 (RULE-21): Set the signer list to `someone@else.com` and run the command; verify it exits 1 and prints `not on the signer list` @integration
- PROOF-27 (RULE-21): Run the command at the gate that requires a signature, with no signer list; verify it exits 1 and prints `signer list missing: run purlin:init --gate signed` @integration
- PROOF-28 (RULE-22): Run the command with `--help`, with `login --nope` and with no argument; verify the exit codes are 0, 2 and 2
- PROOF-29 (RULE-23): Run the command to sign `RULE-1` on a branch called `side`; verify the signature is not an ancestor of `main`, then fast-forward `main` onto `side` and verify it is @integration
- PROOF-30 (RULE-16): Write a CI record in a project at gate `signed` and read what is signable; verify it is `login RULE-2` alone, the `[bar: strong]` rule whose signed cell reads `unsigned`, and that the walk's stops read the review list's rules before it @integration
- PROOF-31 (RULE-11): Run the walk over a project at gate `signed`, answering `hold` with a case for `RULE-2` and `sign` for `RULE-1`; verify 2 commits are made, a signature file names `RULE-1` and a `.hold.json` file stands beside it @integration
- PROOF-32 (RULE-11): Run the walk over the same project, answering `skip` at every stop; verify 2 rules are skipped, the signatures directory is empty and the close prints `Run: purlin:sign` @integration
- PROOF-33 (RULE-11): Run the walk over the same project, answering `case` with `it should also reject an expired token` at every stop; verify 2 cases come back, the signatures directory is empty, the close prints that sentence and it prints `Run: purlin:build` @integration
- PROOF-60 (RULE-40): In a checkout signing as `jane@acme.com`, run `login RULE-1 --hold "no case for an expired token"`; verify it exits 0, the last commit is signed `G` with the subject `hold(login): RULE-1`, and it adds `specs/auth/login.signatures/RULE-1.<hash8>.jane.hold.json` for the rule's own triple, whose schema is `purlin-hold/1`, holder `jane@acme.com` and reason `no case for an expired token` @integration
- PROOF-61 (RULE-40): Run `login RULE-1 --hold` with no reason, `login RULE-1 --hold --batch`, and `login --hold "a case"` with no rule; verify each exits 2 and no `.hold.json` exists @integration
- PROOF-62 (RULE-41): Write a signature for a `[bar: strong]` rule's current hashes and verify the signed cell reads `signed`; retag the rule `[bar: passed]` and verify it reads `stale` with the reason `hashes changed after the signature` @integration
- PROOF-63 (RULE-42): Commit the brief CI wrote for `login RULE-1`'s current triple and sign the rule; verify the signature's `brief` reads `.purlin/briefs/ci/login/RULE-1.<hash8>.brief.json` for that triple, and that signing `RULE-2`, which has no brief, leaves the field null @integration
- PROOF-64 (RULE-43): Build the audit hash over a brief measuring 90, settled, observing nothing; verify it equals the hash of the same brief built again with a later timestamp and a different record path, differs from the hash of a brief observing one sentence, and that a brief of None hashes to the sha256 of the empty string @unit
- PROOF-65 (RULE-43): Sign a `[bar: strong]` rule whose brief settled observing nothing and verify its signed cell reads `signed`; write a brief for the same triple observing `PROOF-2 reads the status alone.` and verify the cell reads `stale` @integration
- PROOF-66 (RULE-44): Hold a rule whose brief settled observing nothing, verify its strong cell reads `held`, then write a brief for the same triple observing one sentence and verify the cell still reads `held` @integration
- PROOF-67 (RULE-45): Walk with every rule already signed in a project whose `VERSION` file reads `2.1.0`; verify the walk prints `Review: 0 rules. Sign: 0 rules.`, that the annotated tag `signed/2.1.0` exists, that its message names the commit and the gate, that the last line is `Run: git push origin signed/2.1.0`, and that `git log origin/main` is unchanged because nothing was pushed @integration
- PROOF-68 (RULE-46): Walk a project holding one unsigned rule; verify no tag is written and the output reads `No tag: 1 of 2 rules do not meet the gate signed.` Sign it, walk again with `--release beta`, and verify the tag is `signed/beta`; walk a third time and verify it reads `No tag: signed/beta is already written.` @integration
- PROOF-69 (RULE-47): Set `trust: remote` and sign a rule whose only record is `local`; verify nothing is written and the line reads `sign: login RULE-2 has no ci test run for this commit; run purlin:test --remote first`. Commit a `ci` record for the same commit and verify the signature is written @integration
