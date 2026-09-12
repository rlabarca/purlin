# Feature: skill_verify

> Scope: skills/verify/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:verify` skill runs the full test suite across all tiers, then issues verification receipts for every feature with complete rule coverage.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `verify`, matching the directory name
- RULE-4: Skill includes commit instructions or git operations for file modifications
- RULE-5: Skill prohibits modifying code or test files during verification
- RULE-6: Verify skill Step 4e documents independent audit that reports the final integrity score
- RULE-7: Step 2 handles UNTESTED features explicitly: no receipt, not reported as a failure, with the next step chosen by whether the spec's `> Scope:` files exist (`purlin:build` when absent, `purlin:test` when present), and a pointer to `purlin:audit --design` for the gauge measurable in that state
- RULE-8: The project-wide audit in Step 4e is identified as the authoritative measurement, distinct from the feature-scoped advisory audit that `purlin:build` runs
- RULE-9: A feature with runner-gated proofs awaiting their runner still earns a receipt, and that receipt records the gap: an `awaiting_runner` list of `{id, tier}` naming every declared proof that has no result at its tier. A receipt with a non-empty list is platform-partial, a verified-here claim rather than a verified-everywhere one, and the field is absent when nothing is awaiting so an ordinary receipt is unchanged
- RULE-10: `--recheck` is the only name for the clean-room re-execution flag. The retired name `purlin:verify --audit` appears in no skill, reference, doc or README: it collided with the `purlin:audit` skill, which is why it was renamed, and a doc that still names it sends a reader to a flag that does not parse. Historical `RELEASE_NOTES.md` entries are exempt, because they record what shipped
- RULE-11: The skill states the receipt shape by pointing at `references/formats/receipt_format.md` rather than restating it, and points the vhash formula at `specs/mcp/sync_status.md` RULE-6, so the receipt contract and the hash formula each live in one place (CLAUDE.md's deduplication rule). It names the version 2 additions it depends on: `vhash_version`, `rule_hashes`, full proof identity on every proof object, the `evidence` block and the optional `manual` and `awaiting_runner` lists. Because the receipt now records rule text and per-file provenance, a stale receipt is reported with the reason: `Rule text changed since last verification: RULE-3` from comparing the receipt's `rule_hashes` against the current rule text, and `<platform> re-proved since receipt` for every platform whose proof file has moved since the commit the receipt recorded. A bare `vhash mismatch` names no cause and sends the reader to diff two hashes
- RULE-12: The skill states that a receipt rests on a recorded test run: the issuer refuses unless the run marker exists, records a sweep that passed and names the commit that is HEAD now, and `--no-run-check` is the only way past it, warning when used and writing `evidence.test_run: null` so the receipt itself says it rests on no run. It also states that a proof file the recorded run did not execute and no runner committed is evidence with no witness: the issuer names the file and the count of unexecuted proofs and issues nothing for that feature. Silently receipting a proof file nobody re-ran is how a feature stays VERIFIED on evidence months older than the code it claims to cover


## Proof

- PROOF-1 (RULE-1): Grep `skills/verify/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/verify/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `verify`
- PROOF-4 (RULE-4): Grep `skills/verify/SKILL.md` for commit instructions (`git commit`, `commit the`, `create.*commit`); verify present
- PROOF-5 (RULE-5): Grep `skills/verify/SKILL.md` for `NEVER modify`; verify the read-only constraint is present
- PROOF-6 (RULE-6): e2e: Grep skills/verify/SKILL.md for independent audit; verify integrity score and purlin-auditor reference @e2e
- PROOF-7 (RULE-7): Grep `skills/verify/SKILL.md` Step 2 for the UNTESTED case; verify it issues no receipt, is not treated as a failure, branches on whether the scope files exist, and points at `purlin:audit --design`
- PROOF-8 (RULE-8): Grep `skills/verify/SKILL.md` for the authoritative project-wide framing and `skills/build/SKILL.md` for the feature-scoped advisory framing; verify each names its scope so the two audits are not confused
- PROOF-9 (RULE-9): Issue a receipt for a feature declaring a @windows proof with no windows-tier result; verify the receipt is written, that its `awaiting_runner` list names that proof id and tier, and that a feature with no runner-gated proofs gets a receipt with no `awaiting_runner` key at all @integration
- PROOF-10 (RULE-10): Scan every `.md` file under `skills/`, `references/`, `docs/` and the repo root for a `purlin:verify --audit` reference or a `--audit` flag attributed to verify, excluding `RELEASE_NOTES.md`; verify none is found. Verify `skills/verify/SKILL.md`'s `## Usage` block documents `--recheck`, so the proof fails if the flag is removed rather than passing on an empty search
- PROOF-11 (RULE-11): Grep `skills/verify/SKILL.md` and verify it names `references/formats/receipt_format.md` as the receipt shape, names `sync_status` RULE-6 as the vhash formula, and that the version 1 receipt body it used to carry is gone: no `"rules": ["RULE-1"` JSON literal, no `"proofs": [` receipt array and no `sorted RULE IDs` formula sentence remain in the file. Then, in a temp project with a v2 receipt issued by the real issuer, reword one rule in the spec and run `sync_status`; verify the feature's block carries `Rule text changed since last verification:` naming exactly that rule id. Restore the text, commit a new result to the feature's scoped `proofs-unit@windows-2022.json`, and verify the block carries `windows-2022 re-proved since receipt` @integration
- PROOF-12 (RULE-12): Grep `skills/verify/SKILL.md` and verify it states the run-marker refusal, names `--no-run-check` as the override, and states that the override writes `evidence.test_run: null`. Then drive the real issuer in a temp project: with no marker verify it writes no receipt and prints `REFUSED`; with a marker whose `ok` is false, and with one whose `commit` is not HEAD, verify the same; with a valid marker verify the receipt's `evidence.test_run.commit` is that marker's commit; with `run_check=False` verify the receipt is written with `evidence.test_run` null and a warning printed. Finally write a proof entry naming a `test_file` the marker does not list, in a file committed with no `Purlin-Runner:` trailer, and verify the issuer prints `not executed in the recorded run` naming that file and writes no receipt for that feature @integration
