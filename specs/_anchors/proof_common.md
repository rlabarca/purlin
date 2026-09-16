# Anchor: proof_common

> Description: What every proof plugin does, whatever language it is a plugin for: where
>   it writes, how it finds the project root, what an entry holds, how a re-run merges
>   with what is already there, how it writes without ever leaving a half-written file,
>   and the two ways it refuses to be quiet. Each per-framework spec requires this anchor
>   and adds only what its framework spells differently, so the contract is written and
>   proved once rather than copied six times.
> Type: schema
> Scope: scripts/proof/pytest_purlin.py, scripts/proof/jest_purlin.js, scripts/proof/vitest_purlin.ts, scripts/proof/shell_purlin.sh, scripts/proof/sql_purlin.sh, scripts/proof/xunit_purlin.cs
> Stack: one file per framework, each in its framework's own language, standard library only

## Rules

- RULE-1: A plugin writes its evidence to `.purlin/runtime/proofs/<feature>.<tier>.json` under the project root and to no other path, so nothing a test run produces is ever committed [risk: high] [origin: eng]
- RULE-2: A plugin resolves the project root by walking up from the directory its run lives in, that directory included, to the nearest ancestor holding `specs/` or `.purlin/`, and takes the starting directory itself when no ancestor holds either; every path it reads or writes is resolved from there rather than from the working directory a framework happened to pick [risk: high] [origin: eng]
- RULE-3: `test_file` is written relative to the project root with `/` separators on every operating system, so a backslash never reaches a proof file and the same test run from a subdirectory and from the root reads the same value [risk: medium] [origin: eng]
- RULE-4: A written entry carries the seven fields `feature`, `id`, `rule`, `test_file`, `test_name`, `status` and `tier`, and no eighth [risk: medium] [origin: eng]
- RULE-5: `status` records execution and never availability: `pass` means the test ran and passed, `fail` means it ran and its assertion failed, and a test the run skipped emits no entry at all, so nothing downstream has to tell a broken build from a missing tool [risk: high] [origin: eng]
- RULE-6: A write merges on the key `(feature, tier, test_file)`: another feature's entries survive untouched, this feature's entries from test files the run did not execute survive, an entry whose test file no longer exists is dropped, and an entry belonging to a marked test this run skipped survives with the status it had unless this run wrote that entry afresh [risk: high] [origin: eng]
- RULE-7: A plugin sorts a written file's entries by `(id, test_file, test_name)` under plain ordinal string comparison, after the merge and immediately before serialization, so `PROOF-10` precedes `PROOF-2` and two runs of the same tests in any collection order write byte-identical files [risk: medium] [origin: eng]
- RULE-8: Every write creates a temp file beside the target whose name carries the writing process's own id and replaces the target with it in one filesystem operation; nothing deletes the target first, and a run leaves no temp file behind [risk: medium] [origin: eng]
- RULE-9: A run that collected no proof marker writes no proof file and exits zero, so a suite that has nothing to say about a spec says nothing [risk: medium] [origin: eng]
- RULE-10: A run that collected at least one marker and appended no entry at all exits non-zero and prints one line naming the features whose evidence went missing, because the alternative is a reader trusting a proof file an earlier run wrote [risk: high] [origin: eng]
- RULE-11: The retired operating-system keyword on a marker is refused rather than ignored: the run exits non-zero and prints one line naming the markers that carry it and the `@env(...)` proof line that replaces it [risk: high] [origin: eng]
- RULE-12: Every plugin whose framework reports a skip observes it, which is pytest, jest, vitest and the xUnit logger; the shell and sql plugins are exempt because their marker is an explicit call, so a script that never called it cannot be told apart from one that skipped [risk: medium] [origin: eng]
- RULE-13: A plugin is one file importing only its own language's standard library plus the test framework it is a plugin of, and it branches on no operating system, so a project that installed its test framework runs the plugin as shipped [risk: medium] [origin: eng]
- RULE-14: The tier a marker names decides which file the entry lands in and is written on the entry and at the top of the file; a marker that names no tier is tier `unit` [risk: medium] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Drive each shipped plugin over one passing marked test for feature `feat` in a temporary project and verify the single file it wrote is `.purlin/runtime/proofs/feat.unit.json`, and that zero files were written under `specs/`, in `dev/test_multilang_proof_plugins.py`
- PROOF-2 (RULE-2): Build a project holding `specs/`, `.purlin/` and a subdirectory, run a plugin from that subdirectory, and verify the evidence landed in the root's `.purlin/runtime/proofs/` with zero second `specs/` or `.purlin/` directories created beside the run; a plugin that rooted its write at the working directory fails naming itself, in `dev/test_multilang_proof_plugins.py`
- PROOF-3 (RULE-3): Run a plugin from a subdirectory and hand another an absolute test path; verify each written `test_file` equals the fixture's path relative to the project root, is not absolute and carries zero backslashes, in `dev/test_multilang_proof_plugins.py`
- PROOF-4 (RULE-4): Read back the file each plugin wrote and verify every entry's key set is exactly the seven required fields, an eighth key failing and naming the plugin, in `dev/test_multilang_proof_plugins.py`
- PROOF-5 (RULE-5): Run a fixture holding one passing marked test and one failing one and verify the two entries read `pass` and `fail`; run a fixture whose marked test is skipped and verify no entry for it is written, in `dev/test_multilang_proof_plugins.py`
- PROOF-6 (RULE-6): Seed a proof file with one entry for another feature, one for this feature from a test file the run will not execute, one whose test file has been deleted, and one for a marked test the run will skip; run the plugin over a different test file of this feature and verify the first two and the skipped one survive unchanged, the deleted file's entry is absent, and the executed test's entry is replaced, in `dev/test_multilang_proof_plugins.py`
- PROOF-7 (RULE-7): Run a fixture declaring `PROOF-10`, `PROOF-2` and `PROOF-1` in that source order into a project whose proof file already holds a kept `PROOF-11` entry, then run the same three in reverse source order in a fresh project; verify both files are byte-identical and the id list reads `["PROOF-1", "PROOF-10", "PROOF-11", "PROOF-2"]` and never the numeric order; a writer whose sort is removed fails on both, in `dev/test_multilang_proof_plugins.py`
- PROOF-8 (RULE-8): Read each plugin source and verify every line that builds a temp name carries that language's process-id expression; run each plugin in a temporary project and verify zero files ending `.tmp` are left under `.purlin/runtime/`, in `dev/test_multilang_proof_plugins.py`
- PROOF-9 (RULE-9): Run a suite holding no proof marker and verify the run exits zero and `.purlin/runtime/proofs/` holds no file, in `dev/test_multilang_proof_plugins.py`
- PROOF-10 (RULE-10): Run a suite whose markers are collected while the plugin is prevented from appending any entry, and verify the run exits non-zero and its standard error carries the feature name and the words `no proof entry was written`, in `dev/test_multilang_proof_plugins.py`
- PROOF-11 (RULE-11): Run a fixture whose marker carries the retired operating-system keyword in each plugin's own spelling and verify the run exits non-zero, the standard error names that marker and carries the literal `@env(`, and no proof file was written, in `dev/test_multilang_proof_plugins.py`
- PROOF-12 (RULE-12): Read the sources and verify pytest, jest, vitest and the xUnit logger each track the tests they skipped while the shell and sql plugins carry no such set, a plugin found on the wrong side failing by name, in `dev/test_multilang_proof_plugins.py`
- PROOF-13 (RULE-13): Extract every import of each plugin source and verify each names that language's standard library or the plugin's own test framework and nothing else; run the node reporters in a project whose `node_modules/` exists and is empty and verify each loads and writes its one entry, in `dev/test_multilang_proof_plugins.py`
- PROOF-14 (RULE-14): Run a marker naming tier `integration` and a marker naming no tier and verify the first entry lands in `feat.integration.json` with `tier` reading `integration` at the top of the file and on the entry, and the second in `feat.unit.json`, with `feat.e2e.json` absent, in `dev/test_multilang_proof_plugins.py`
