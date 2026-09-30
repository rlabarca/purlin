# Feature: release

> Description: The release run `purlin:test --release [<version>]` hands on to after it has run
>   every test and committed the evidence. It checks the release commit: every spec can be
>   counted, every rule's tests pass, nothing is left uncommitted, the branch's copy on the host
>   holds nothing the checkout lacks, a version is named and its tag is not yet written. Then it
>   writes the evidence package and commits it alone. At the gate `passed` it tags that commit
>   `passed/<version>`, unsigned; at `signed` it writes no tag and the first sign-off does. A
>   weak or unaudited rule never refuses a release. Nothing is fetched and nothing is pushed.
> Scope: scripts/export/release.py
> Stack: python/stdlib (subprocess, json), git
> Highest-Rule: 12
> Highest-Proof: 16

## Rules

- RULE-1: A release is refused while a rule's tests do not pass, printing `No release: <n> rules do not pass at <sha7>: <feature> <RULE-N>, ...; ... Run purlin:status to see what is left, then purlin:test --release.`, and while a spec cannot be counted, printing `No release: <feature> cannot be counted: <why>. Run purlin:spec <feature>, then purlin:test --release.`
- RULE-2: A release is refused while the working tree holds changes that are not committed
- RULE-3: A release is refused while the branch's copy on the host, as this checkout last fetched it, holds commits the checkout lacks, and not for a commit of its own the host lacks
- RULE-4: The version is read from the `VERSION` file, `package.json`, `pyproject.toml` or the first `*.csproj`, in that order, or named by `--release <version>`; with none, the release prints `No version: nothing in this project states one. Run purlin:test --release <version>, or write it to a VERSION file.`
- RULE-5: At the gate `passed` the release commits the package alone as `purlin: evidence at <sha7>` and writes the unsigned tag `passed/<version>` on that commit, printing `Tagged passed/<version> at <sha7>.` and the push
- RULE-6: At the gate `signed` the release commits the package and writes no tag, ending on `Run purlin:sign to sign it; the first signature writes signed/<version>.`
- RULE-7: Where the gate's tag for the version already exists, the release prints `No release: <tag> is already written. Run purlin:test --release <version> to name another.` and writes nothing
- RULE-8: A rule the audit found weak, or never audited, does not refuse a release
- RULE-9: A package for the same version with no tag of the gate yet is written again over the old one
- RULE-10: At the gate `passed`, a rule with a `@manual` proof is named in one line before the package is committed, and the package lists it as not checked
- RULE-11: Where git cannot write the tag, the release prints `No tag: git could not write <tag>: <git's message>.`
- RULE-12: The release fetches nothing and pushes nothing

## Proof

- PROOF-1 (RULE-1): At the gate `passed`, `login` `RULE-2`'s test fails and everything is committed; the release prints only `No release: 1 rule does not pass at <sha7>: login RULE-2. Run purlin:status to see what is left, then purlin:test --release.`, `<sha7>` HEAD's, writes no package and no tag
- PROOF-2 (RULE-1): At the gate `passed`, `login`'s spec writes `PROOF-2` twice and is committed; the release prints only `No release: login cannot be counted: PROOF-2 is written twice in the spec. Run purlin:spec login, then purlin:test --release.` and writes no tag
- PROOF-3 (RULE-2): At the gate `passed`, with both rules passing, a new file `NOTES.md` is written and not committed; the release prints only `No release: the working tree holds changes that are not committed, so the results do not describe a commit. Commit them, then run purlin:test --release.` and writes no tag
- PROOF-4 (RULE-3): A clone of a bare repository on disk receives one commit pushed from another clone, then fetches it; the release prints only `No release: origin/main holds 1 commit that <sha7> does not, as this checkout last fetched it. Pull, then run purlin:test --release.` and writes no tag
- PROOF-5 (RULE-3): A clone of a bare repository on disk holds one commit of its own the host lacks; the release commits the package and writes `passed/2.1.0`
- PROOF-6 (RULE-4): At the gate `passed`, the `VERSION` file reads `2.1.0` and `package.json` reads `9.9.9`; the release writes `.purlin/evidence/package/2.1.0.json` and the tag `passed/2.1.0`
- PROOF-7 (RULE-4): At the gate `passed`, the `VERSION` file reads `2.1.0` and the release is named `2.0.0`; it writes `.purlin/evidence/package/2.0.0.json` and the tag `passed/2.0.0`, and no `passed/2.1.0`
- PROOF-8 (RULE-4): At the gate `passed`, nothing states a version and none is named; the release prints only `No version: nothing in this project states one. Run purlin:test --release <version>, or write it to a VERSION file.` and writes no package
- PROOF-9 (RULE-5): At the gate `passed`, with both rules passing and the `VERSION` file reading `2.1.0`, the release prints `Evidence package committed: .purlin/evidence/package/2.1.0.json.`, `Tagged passed/2.1.0 at <sha7>.` and `Nothing left to do. Push the tag to release it: git push origin passed/2.1.0`; the tag is unsigned and names the package's commit
- PROOF-10 (RULE-6): At the gate `signed`, with both rules passing, the release commits `.purlin/evidence/package/2.1.0.json`, its last line reads `Run purlin:sign to sign it; the first signature writes signed/2.1.0.`, and the project holds no tag
- PROOF-11 (RULE-7): At the gate `passed`, `passed/2.1.0` already exists; the release prints only `No release: passed/2.1.0 is already written. Run purlin:test --release <version> to name another.` and HEAD does not move
- PROOF-12 (RULE-8): At the gate `signed`, both rules pass, `RULE-1` is audited `weak` with one finding and `RULE-2` is not audited; the release commits the package and ends on `Run purlin:sign to sign it; the first signature writes signed/2.1.0.`
- PROOF-13 (RULE-9): At the gate `signed`, the release commits the package; a test file is then edited, its tests run again and both committed together, and the release run again commits a new `.purlin/evidence/package/2.1.0.json` whose `commit` names that later commit
- PROOF-14 (RULE-10): At the gate `passed`, `PROOF-2` is marked `@manual`; the release prints `1 rule is checked by hand, and the gate passed records no hand check: login RULE-2. The package lists them as not checked.` before the package line, and `hand_checks` reads `checked` false
- PROOF-15 (RULE-11): At the gate `passed`, a tag named `passed` already exists, so git cannot write a tag under `passed/`; the release commits the package, then prints `No tag: git could not write passed/2.1.0: <git's message>.` and returns the refusal `git`
- PROOF-16 (RULE-12): A clone of a bare repository on disk releases at `passed`; afterwards the bare repository holds no tag and its `main` has not moved, and the clone has no `FETCH_HEAD`
