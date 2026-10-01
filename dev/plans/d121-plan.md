# Decision 121: the sign-off and the audit say only what was shown; the build plan

Written by the planning agent on 2026-10-01, read only, against local `main` at `c01ad61e9`
(`purlin: evidence at 99204ba`): decision 120 is merged and integrated, the tree is clean,
39 specs, 411 rules, 823 proofs, the sweep at 819 passed and 9 skipped. Every file, function,
rule id and count below was read in that tree. Nothing was run there, but step 0's five model
calls (section 2.4), made by the coordinator from an empty folder and written in afterwards.

Sources: decision 121's five answers; `dev/plans/d120-reports/coverage-review.md` (the review);
the measurement of the planted-bug audit (`audit-measure/report.md`, 46 rules, 93 proofs, 139
real calls); `claude --help` of version 2.1.287.

## 0. What changes, in five sentences

1. **The sign-off.** The status reads `signed` only where a sign-off counts; a package is trusted
   by its content; a sign-off is read as `HEAD` holds it; a tag git could not write is written by
   the next run; two signers never share a file; the settings file is part of the project.
2. **Slow results.** A plain run that keeps an earlier slow pass marks it `kept`, with the
   commit, time, machine and person of the run that took it. The status counts it. The sign-off
   does not, and says `Run purlin:test --all --commit`.
3. **The audit's word.** `strong`, `weak`, `spot-checked`, or `not audited`; and `out of date`
   for an entry whose rule, proof, test or covered code changed since it was written.
4. **The audit's cost.** One model call per rule in place of 3.0, started with no tools, no MCP
   servers, no plugins, no skills, no project instructions and none of the person's settings,
   from an empty folder. Expected: about $0.07 a rule where $0.74 was measured. Step 0 measured
   a bare call asking for `ok` at $0.0021, where $0.20 was measured.
5. **A planted bug counts only when a test ran and failed on it.** A skip, a test not collected
   and a timeout decide nothing. Round 1's call "a test that errors, cannot be collected or
   runs past its limit reads `caught`" (`d115-plan.md`, K9) is reversed.

Decision 44 binds: what goes is deleted outright with its tests; no compatibility reader, no
test that a removed thing is absent.

## 1. The count

| | Now | Added | Deleted | Reworded | After |
|---|---|---|---|---|---|
| Specs | 39 | 0 | 0 | 15 touched | 39 |
| Rules | 411 | 18 | 0 | 37 | 429 |
| Proofs | 823 | 64 | 2 | 21 | 885 |

The numbers assumed are each spec's `> Highest-*` on `main` at `c01ad61e9`, after decision 120:

| Spec | Highest-Rule now, after | Highest-Proof now, after | Rules added | Rules reworded | Proofs added | Proofs deleted | Proofs reworded |
|---|---|---|---|---|---|---|---|
| `signatures` | 129, 134 | 251, 265 | 130, 131, 132, 133, 134 | 108, 125, 127 | 252 to 265 | | |
| `package` | 37, 37 | 76, 80 | | 29, 33 | 77 to 80 | | 61 |
| `states` | 125, 126 | 285, 290 | 126 | 14, 27, 59, 61, 118, 121 | 286 to 290 | 71, 160 | 31, 73, 168, 169, 170 |
| `summary` | 24, 24 | 56, 57 | | 20, 22 | 57 | | 43, 50 |
| `ai_audit` | 43, 45 | 111, 122 | 44, 45 | 1, 2, 3, 4, 33, 35, 37, 39, 43 | 112 to 122 | | 14, 82, 99, 100, 102, 104, 108, 110 |
| `planted_bug` | 12, 13 | 15, 19 | 13 | 3, 6, 12 | 16 to 19 | | 7 |
| `plain_checks` | 9, 10 | 30, 32 | 10 | 6 | 31, 32 | | |
| `evidence_writer` | 33, 33 | 96, 98 | | 12, 14, 31 | 97, 98 | | 54 |
| `evidence` | 35, 35 | 85, 89 | | 7, 16 | 86 to 89 | | 22, 58 |
| `run_script` | 106, 106 | 280, 285 | | 105, 106 | 281 to 285 | | |
| `reports` | 37, 38 | 118, 120 | 38 | | 119, 120 | | |
| `update` | 54, 56 | 163, 165 | 55, 56 | | 164, 165 | | |
| `upstream` | 39, 40 | 60, 62 | 40 | | 61, 62 | | |
| `purlin_agent` | 19, 23 | 50, 54 | 20, 21, 22, 23 | | 51 to 54 | | |
| `purlin_report` | 78, 78 | 238, 240 | | 8, 9, 15, 39 | 239, 240 | | 147 |

**Against the review's 22 rules, 51 proofs and 5 reworded rules.**

| The review's item | Here |
|---|---|
| 1, 5, 6, 11, 13, 14, 15, 18, 19, 20, 21 and Part 3's four | new rules, as proposed (15 rules) |
| 3, the slow result | no new rule: `run_script` RULE-106 reworded holds it, with one proof on each side of the seam (`run_script` PROOF-281, `package` PROOF-79) |
| 4, three refusals with no proof | merged with 13 into `signatures` RULE-132: one rule, three proofs |
| 7, a `claude` that answers nothing | `ai_audit` RULE-39 reworded, one proof |
| 8, the reading inside the check | held twice: `ai_audit` RULE-3 (no tools, an empty folder) and `planted_bug` RULE-6 widened to the whole audit; no new rule |
| 9, a bug in the test file | `planted_bug` RULE-12 reworded, one proof |
| 10, the last note at the stop | already on `main`: `signatures` RULE-129, PROOF-249 to 251 (decision 120) |
| 12, the settings file | `evidence` RULE-7 and `package` RULE-33 reworded; the proposed `dirty` rule is not written, since a changed `tests` setting now puts every result out of date and stops the sign-off, which holds the same protection |
| 17, why a rule stayed not audited | not built (answer 4b): `write_could_not_run`, its reader and `states` PROOF-71 are deleted; `spot-checked` carries the reason |
| Tier 5, 21 proofs | 19 written; "a stopped audit leaves the evidence's bytes" is folded into `planted_bug` PROOF-7; "the bug answered and the reading not" is dropped, because one call now holds both |
| The 5 reworded rules | `signatures` 108 and 125, `package` 33, `evidence_writer` 31, `evidence` 16 |

Three new rules come from decision 121 and the measurement, not the review: `states` RULE-126
(`out of date`), `ai_audit` RULE-44 (the reply's parts) and RULE-45 (the calls and the cost
printed). The other 32 reworded rules are what the three words, `out of date`, the one call and
the `tests` setting force.

## 2. What each answer becomes

### 2.1 A slow result (answer 2)

Today `purlin_run.keep_slow_results` copies a held slow test's `pass` from the section on disk
into the new section, which carries this run's `commit`, `at`, `machine` and `email`. After a
commit to a file no scope names, the sign-off reads that pass as taken on the new commit.

The least change that makes both statements true:

- A kept result's entry in `proofs` carries `kept`, an object naming where its test really ran:
  `{"commit": "<40 hex>", "at": "<ISO 8601 UTC>", "machine": "<host>", "email": "<git email>"}`,
  taken from the section it was kept from, or carried over unchanged where that entry was
  already kept. The section's own `commit`, `at`, `machine` and `email` stay this run's.
- `_same_observation` leaves `kept` out of its comparison. So a plain run on the same code as
  the `--all` run leaves the section byte for byte as it was, with no `kept` in it, and nothing
  new to commit (`run_script` PROOF-279 and `evidence_writer` PROOF-91 hold as they are).
- The status reads a kept `pass` as a `pass` (decision 118). Nothing in `states.py` changes.
- The sign-off counts no kept result: `package._results` gives `same_code` false to a rule's
  result in a section where one of the rule's proof entries carries `kept`. The existing refusal
  then prints, with no new line: `No sign-off: these results were not taken on this version of
  the code, 1cf829e: feat on macOS. Run purlin:test --all --commit, then purlin:sign.`

A kept result is refused whatever commit it names. That is stricter than "another version" and
simpler: it also stops a slow pass taken over uncommitted changes, or on another machine, from
being carried into a clean section.

### 2.2 The audit's four words and `out of date` (answer 3)

Per proof the audit plants a bug for, one result: `caught`, `survived`, `not made` or `not run`.

| The rule's word | When |
|---|---|
| `weak` | a spot test fired on one of its tests, or a planted bug survived |
| `strong` | no spot test fired, no bug survived, and a planted bug was caught by its proof's test |
| `spot-checked` | no spot test fired and no bug was planted and caught |
| `not audited` | the rule has no audit entry: the audit never read it |

A kept bug (`ai_audit` RULE-36) counts as on the code as it is now: its key is the hash of the
test's source and of the feature's code.

Every entry records under `no_bug` one sentence for each proof no bug was caught for, whatever
the verdict. A `spot-checked` rule shows `The spot tests found nothing. ` followed by those
sentences on every surface. The sentences (section 5, K2):

| Why | Sentence |
|---|---|
| The model said no change would break the proof | `No bug was planted: the model found no change that would break PROOF-2: <its reason>.` |
| The model's answer could not be used | `No bug was planted: the model's answer for PROOF-2 could not be used: <what was wrong>.` |
| The proof's test does not pass in a copy of the project | `No bug was planted: the test of PROOF-2 does not pass in a copy of the project.` |
| The model could not be reached | `No bug was planted: the model could not be reached: <why>.` |
| An anchor's rule | `No bug was planted: no bug is planted for an anchor's rule.` |
| The proof is tagged for another system | `No bug was planted: PROOF-38 needs Windows, and this machine is macOS.` |
| The test did not run with the bug in place | `A bug was planted for PROOF-2 and its test did not run.` |

**An anchor's rule** reads `strong` today whenever no spot test fires, with no bug behind it
(`audit_run.py:269`, `ai_audit` RULE-37, PROOF-102). The code plants none, by decision 100. It
now reads `spot-checked`, and the docs and the slide say so.

**The model not reached** no longer leaves the rule `not audited` (this replaces that part of
decision 117). The rule is written `spot-checked` with the reason, and the next audit reads it
again, because a proof it plants a bug for has no result recorded.

**`out of date`.** The passed cell decides it by a stored fingerprint: a section stores `spec`,
`code` and `tests` hashes, `fingerprint.differing_parts` names the parts that differ from a
fingerprint taken now, and the cell reads `out of date` with `<part> changed since <sha7>`
(`states.py:312-319`). The audit entry reuses that:

- The entry already stores `rule_hash`, `proof_hash` and `test_hash`. It gains `code_hash`, the
  `code` part of the feature's fingerprint when the audit read the rule
  (`fingerprint.code_part`, the same value the passed cell compares; for an anchor it is the
  hash of the whole project but Purlin's own results).
- `evidence.audit_entry` returns the rule's entry whatever its hashes, a current one before one
  out of date, with `out_of_date`, the parts of `rule`, `proof`, `test` and `code` that differ.
- The strong cell then reads `out of date`, with one reason per part, `code changed since
  a1b2c3d`, and last `the last audit found it strong on 2026-09-13`. Nothing is deleted. It
  reads so on the status, the dashboard, the package and the walk, whether or not anyone ran
  the audit again.
- The audit reads a rule again when its entry is out of date. `audit_run.code_changed`, the
  `git diff` that answered this alone, is deleted.

**The summary line** counts every word and gives the share of `strong`:
`The audit found 34 of 40 rules strong (85%): 34 strong, 4 weak, 2 spot-checked.` The counts
come in the order `strong`, `weak`, `spot-checked`, `out of date`, `not audited`; a count of
zero is left out, but `strong`. The walk's overview keeps its form:
`  The audit: 34 strong, 4 weak, 2 spot-checked.`

### 2.3 The settings file (answer 4a)

- **The `tests` setting ends results as a covered file does.** `fingerprint.tests_hash` adds one
  line for the `tests` setting, so a changed command puts every feature's sections out of date
  on `tests`. `package.only_records_between` reads a commit that changes the `tests` setting as
  a change to the code, so the sign-off refuses and `signed 0.1.0 at a1b2c3d` becomes
  `signed 0.1.0, 1 commit since`. A change to `version` alone does neither.
- **A release.** `dev/bump_version.sh` writes `VERSION` and `.claude-plugin/plugin.json`, both
  outside `.purlin/`, so a bump already ends every result at the sign-off today. It also writes
  `version` in `.purlin/config.json`, which ends nothing. So this change makes no release
  harder: the order stays bump, commit, `purlin:test --all --commit`, the Windows run, then
  `purlin:sign`. In a consumer project `purlin:init --update` writes `version` alone and ends
  no result.
- **At the sign-off** a tracked `.purlin/config.json` that is changed and not committed is a
  changed file, whichever key changed: `No sign-off: 1 file is changed and not committed.`

### 2.4 The model call (the measurement, item 1)

Measured: each call wrote 18,613 to 38,135 tokens to the one-hour cache (median 28,918) that no
later call read; a call asking for the word `ok` cost $0.20. The prices the 140 saved calls fit
exactly: input $4.00, output $20.00, one-hour cache write $8.00 and cache read $0.20 for a
million tokens (`24,823 x 8 + 10,738 x 0.2 + 4 x 20 + 2 x 4 = $0.2008`, the `ok` call).

**The command**, from `claude --help` of 2.1.287 (`ai_audit.COMMAND`):

```
claude -p --output-format json --max-turns 1 --tools "" --strict-mcp-config --safe-mode \
  --setting-sources "" --disable-slash-commands --no-session-persistence \
  --system-prompt "<SYSTEM_PROMPT>"
```

started with `DISABLE_PROMPT_CACHING=1` added to the environment, in a new empty folder
`purlin-audit-*` under the system's temporary folder, removed when the audit ends.

| Flag | What it drops |
|---|---|
| `--tools ""` | every built-in tool: the tool list in the request, and any way to read or change a file or run a command |
| `--strict-mcp-config`, with no `--mcp-config` | every MCP server |
| `--safe-mode` | `CLAUDE.md`, skills, installed plugins, hooks, MCP servers, custom commands and agents, output styles. The program's three built-in plugins stay and add nothing to the request |
| `--setting-sources ""` | the user, project and local settings files: the person's own configuration |
| `--disable-slash-commands` | every skill |
| `--system-prompt "<text>"` | the program's own default instructions; the audit's own short text stands in |
| `--max-turns 1` | a second turn. It is in the 2.1.287 program ("Maximum number of agentic turns in non-interactive mode") and `--help` does not list it. Step 0: accepted, `num_turns` 1 |
| `--no-session-persistence` | the session file the program would save on the person's disk |
| `DISABLE_PROMPT_CACHING=1` | the cache write. No flag does this; the variable is in the program and `--help` does not list it. Step 0: it works, and halves the cost of a request of the criteria's size |

Not used: `--bare`. It drops the same things, and `--help` says it never reads the login the
person made with the program ("OAuth and keychain are never read"), so a person without an API
key could not be reached.

`SYSTEM_PROMPT = "You review software tests for Purlin's audit. You have no tools. Answer in exactly the shape the request gives, and with nothing else."`

**Step 0, the coordinator's, before any lane: done on 2026-10-01, with five real calls,
$0.084 in all.** Every flag was accepted by `claude` 2.1.287, logged in as the owner
(`apiKeySource` `none`, the login made with the program). No flag was refused, no fallback of
the table below was used, and the list is frozen as written above. The final command, word for
word, run from a new empty folder:

```
printf 'Reply with the single word: ok' | DISABLE_PROMPT_CACHING=1 claude -p --output-format json --max-turns 1 --tools "" --strict-mcp-config --safe-mode --setting-sources "" --disable-slash-commands --no-session-persistence --system-prompt "You review software tests for Purlin's audit. You have no tools. Answer in exactly the shape the request gives, and with nothing else."
```

| Call | What differed | Exit | `total_cost_usd` | Input | Output | Cache written | Cache read | `num_turns` | Model |
|---|---|---|---|---|---|---|---|---|---|
| 1 | the command above | 0 | $0.00212 | 510 | 4 | 0 | 0 | 1 | `claude-opus-5-5` |
| 2 | `--output-format stream-json --verbose`, to read what the program loaded | 0 | $0.00212 | 510 | 4 | 0 | 0 | 1 | `claude-opus-5-5` |
| 3 | `DISABLE_PROMPT_CACHING` not set | 0 | $0.00212 | 510 | 4 | 0 | 0 | 1 | `claude-opus-5-5` |
| 4 | the request is `references/review_criteria.md` whole, 16,878 characters, then the question | 0 | $0.025936 | 6,464 | 4 | 0 | 0 | 1 | `claude-opus-5-5` |
| 5 | as call 4, `DISABLE_PROMPT_CACHING` not set | 0 | $0.051784 | 2 | 4 | 6,462, one-hour | 0 | 1 | `claude-opus-5-5` |

Every call answered `ok`, with `is_error` false.

- **Against the baseline.** A bare call asking for `ok` costs $0.0021 and writes nothing to the
  cache, where the measurement's cost $0.20 and wrote 18,613 to 38,135 tokens: about a
  hundredth of the cost. The costs fit the prices of this section exactly
  (`510 x 4 + 4 x 20 = $0.00212`; `6,462 x 8 + 2 x 4 + 4 x 20 = $0.051784`).
- **What was loaded** (call 2's first line): `tools` `[]`, `mcp_servers` `[]`,
  `slash_commands` `[]`, `skills` `[]`. `plugins` lists three the program builds in
  (`cc-plugin-agents-md`, `cc-plugin-telemetry`, `cc-plugin-plugin-authoring`), which no flag
  drops and which add nothing to the request; no installed plugin is listed. `agents` lists the
  program's four built-in ones, which cannot be started with no tools. The folder held no file
  after each call, and no session folder was written under `~/.claude/projects`.
- **What is fixed per call**: 510 input tokens for the system prompt and a seven-word question,
  about 470 of them the program's own, sent whatever the request holds.
- **`DISABLE_PROMPT_CACHING=1` is needed.** Without it a request of the criteria's size is
  written whole to the one-hour cache and costs twice as much (calls 4 and 5). A request of 510
  tokens is written to no cache either way (call 3).
- **Characters a token**: the criteria's 16,878 characters came to 5,954 tokens, 2.83 a token,
  where this plan assumed 3. Measured on that one file of prose; the code a scope holds may
  differ.

The table that would have applied to a refused flag, kept for a later version of the program:

| Refused | Then |
|---|---|
| `--max-turns 1` | leave it out: with `--tools ""` a reply is one turn. The nearest listed flag is `--max-budget-usd` |
| `--setting-sources ""` | leave it out: `--safe-mode` and the empty folder already drop the project's settings; the person's own model choice then still applies |
| `--safe-mode` with `--system-prompt` | keep `--system-prompt`, `--tools ""`, `--strict-mcp-config`, `--disable-slash-commands` and the empty folder; measure the `ok` call again |
| the cache is still written | nothing to do; the expected cost is then the second figure below |

**One call per rule.** Today: one call per proof for its bug, then one for the reading, 3.0 a
rule. Now one request holds the criteria, the rule, its proofs, its tests, the spot tests'
findings, the proofs to plant a bug for and the text of each file the scope reaches. The reply
holds one part per proof and the reading (K3). The order of the audit becomes: the spot tests
for every rule, with no model; the calls, one a rule, four at once; then each bug planted and
its test run, one at a time. The reading no longer sees whether a bug survived, since it is
written in the same reply; it explains the tests and the spot tests' findings. A surviving bug
is its own finding, with the changed line in it.

**What to expect when it is measured again** (integration, 12 rules), corrected from step 0's
measured tokens. Input a rule: 470 tokens the program adds, plus the criteria, 16,878
characters, plus the rule's own request, which the saved bug requests put at 3,000 to 41,000
characters, at the measured 2.83 characters a token: 7,500 tokens (`sample_intake`) to 20,900
(`plain_checks`). Output: 600 to 1,200 tokens.

| | Small scope | Purlin's own, middle | Large scope |
|---|---|---|---|
| Input tokens | 7,500 | 12,700 | 20,900 |
| Output tokens | 600 | 900 | 1,200 |
| Cost, cache off ($4.00 in, $20.00 out): what step 0 measured | $0.04 | $0.07 | $0.11 |
| Cost, if the request were written to the cache ($8.00): not the case with the variable set | $0.07 | $0.12 | $0.19 |

Expect about **$0.07 a rule, between $0.04 and $0.11**, with one call a rule and the cache off,
as step 0 measured it. Before step 0 this read $0.04 to $0.10, on 7,000 to 19,500 tokens. A
feature whose scope is over about 40,000 characters goes over $0.10. If the 12 rules average
over $0.10, the planted bug is marked experimental, in the words of section 6.9.

## 3. The specs, word for word

Each lane writes the rules and proofs of the specs it owns, spec first. A reworded rule or
proof keeps its number. `as now` means the words on `main` stand.

### `signatures` (lane `signoff`)

`> Scope:` gains `scripts/mcp/purlin/facts.py`. `> Highest-Rule: 134`, `> Highest-Proof: 265`.

- RULE-108: A sign-off counts only while its `package_hash` equals the fingerprint computed over the package `HEAD` holds for its version, and a later sign-off is refused, with one line and nothing written, where that package does not match its own fingerprint
- RULE-125: Every other refusal of the command prints one line naming what is wrong and what to do, writes nothing and exits 1: no version stated or named, the signer already signed this package, git not making the sign-off commit, or a `.purlin/config.json` that cannot be read
- RULE-127: as now, its last clause reading `and what the audit found, as the status counts it: strong, weak, spot-checked, out of date and not audited, a count of zero left out but strong`
- RULE-130: The sign-off reads `signed <version>` only where `signed/<version>` names a commit holding the package for that version and a sign-off of it counts; a tag that does not is passed over, with one warning naming the tag and why, and the sign-off reads `not signed` where no tag is left
- RULE-131: Where the sign-off's commit is made and git cannot write `signed/<version>`, the command prints one line naming the tag and git's reason and exits 1, and the next `purlin:sign` writes the tag on that commit and adds no second sign-off
- RULE-132: The command refuses in the same way while a rule has no result that counts, naming each: a rule never run, a slow proof not run, a rule with no result on a system one of its proofs is tagged for, the rules of a spec that holds a number twice or a merge-conflict line, and each test comment to correct
- RULE-133: A sign-off is read as `HEAD` holds it: a file not tracked, or changed and not committed, does not count, and no note of a sign-off that does not count is shown
- RULE-134: Two signers whose addresses differ each keep a sign-off of one version: the second takes a file name of its own, and the first signer's file is left as it was

- PROOF-252 (RULE-130): A project with committed evidence that passes carries the tag `signed/9.9.9`, written by hand with `git tag`, and no file under `.purlin/evidence/package/`; the sign-off reads `not signed`, and the warnings hold one line starting `signed/9.9.9: it names a commit that holds no evidence package for 9.9.9`
- PROOF-253 (RULE-130): The walk signs `2.1.0`, then a commit made with no signature changes the sign-off file's note; the sign-off reads `not signed`, and the warnings hold one line starting `signed/2.1.0: no sign-off of 2.1.0 counts: the commit that added it is not signed`
- PROOF-254 (RULE-108): The walk signs `2.1.0`, then the committed package's first `"passed"` is changed to `"failed"` with `fingerprint` left as it was, and committed; the sign-off no longer counts, and a second signer's walk prints only one line beginning `No sign-off: .purlin/evidence/package/2.1.0.json does not match its fingerprint:`, and exits 1
- PROOF-255 (RULE-131): With a file at `.git/refs/tags/signed`, so git can write no tag under it, the first sign-off of `2.1.0` makes its commit, prints a line beginning `No tag: git could not write signed/2.1.0:` and exits 1; with that file removed, `purlin:sign` run again exits 0, `signed/2.1.0` names that commit, and no commit was added
- PROOF-256 (RULE-132): `login RULE-2` has `PROOF-2` tagged `@env(windows)`, and the evidence committed at `HEAD` holds results for Linux/Unix alone, all passing; the walk prints only one line beginning `No sign-off: 1 rule does not pass at` and naming `login RULE-2`, and exits 1
- PROOF-257 (RULE-132): `login RULE-2` has `PROOF-2` tagged `@slow`, and the evidence committed at `HEAD` was written by `purlin:test` with no `--all`, every other rule passing; the walk prints only one line beginning `No sign-off: 1 rule does not pass at` and naming `login RULE-2`, and exits 1
- PROOF-258 (RULE-132): `specs/auth/login.md` holds two lines numbered `RULE-2`, and its results are committed at `HEAD`; the walk prints one line beginning `No sign-off:` and naming `login RULE-2`, writes no file and exits 1
- PROOF-259 (RULE-133): After `quinn.qa@labconnect.example` signs `0.1.0` with the note `the tube is red`, the file's note is edited to `the tube is blue` and not committed; `login RULE-2`'s strong cell carries the reason holding `the tube is red` and none holding `the tube is blue`
- PROOF-260 (RULE-134): `jane@acme.com` signs `2.1.0`, then `jane@labs.org` signs it; the folder `2.1.0.signoffs` holds `jane.json`, reading the signer `jane@acme.com` with its bytes unchanged, and `jane-2.json`, reading `jane@labs.org`
- PROOF-261 (RULE-102): With committed evidence that passes, the `version` in `.purlin/config.json` is changed and not committed; the walk prints only `No sign-off: 1 file is changed and not committed. Commit it or set it aside, then run purlin:sign again.` and exits 1
- PROOF-262 (RULE-126): `login RULE-2` has `PROOF-2` marked `@manual` and `PROOF-3` tested, and the audit found it weak with the finding `PROOF-3 reads the status alone.`; its stop holds, before the question, `What the audit found` and then `  PROOF-3 reads the status alone.`
- PROOF-263 (RULE-126): `login RULE-2`, a hand check, has `PROOF-3` tagged `@env(windows)`, run under the source `ci` on the machine `build-7`; its stop holds the two lines `  Linux/Unix: passed on dana-laptop` and `  Windows: passed on build-7`, in that order
- PROOF-264 (RULE-111): An answers file gives `login RULE-2` a note and holds `"sign": "yes"`, a string and not `true`; `--answers` prints `Nothing was signed.`, exits 0 and adds no commit and no file
- PROOF-265 (RULE-125): With `.purlin/config.json` holding `{"version": "0.10.0",`, the walk prints only `.purlin/config.json cannot be read: Expecting property name enclosed in double quotes at line 1. Fix the file by hand; nothing ran and nothing was saved.`, adds no commit and exits 1

### `package` (lane `signoff`)

`> Highest-Proof: 80`.

- RULE-29: The package carries `audit`, the count of rules the audit found `strong`, `weak` and `spot_checked`, of those whose audit is `out_of_date` and of those `not_audited`, and `hand_checks`, one entry per rule with a `@manual` proof naming its feature, rule and proofs
- RULE-33: Each result carries `same_code`, true when every commit from the one its tests ran at to the package's `commit` changes only files under `.purlin/` and leaves the `tests` setting as it was, and no proof of the rule holds a result kept from an earlier run
- PROOF-61 (RULE-29): as now, the object reading `{"strong": 1, "weak": 1, "spot_checked": 0, "out_of_date": 0, "not_audited": 0}`
- PROOF-77 (RULE-33): The tests run and are committed at `<c>`, then a commit changes the `run` command of the `tests` setting in `.purlin/config.json`; `purlin:sign` prints only one line beginning `No sign-off: these results were not taken on this version of the code` and exits 1
- PROOF-78 (RULE-33): `login`'s committed results name a commit on another branch, which `HEAD` does not descend from, the two trees holding the same files; `purlin:sign` prints only one line beginning `No sign-off: these results were not taken on this version of the code` and exits 1
- PROOF-79 (RULE-33): `feat`'s committed section lists its slow `PROOF-2` as `pass` with `kept` naming the commit `<c>`, and every other result was taken at `HEAD`; `purlin:sign --show` prints only `No sign-off: these results were not taken on this version of the code, <sha7>: feat on Linux/Unix. Run purlin:test --all --commit, then purlin:sign.` and exits 1
- PROOF-80 (RULE-22): A signed package is rewritten with every `\n` as `\r\n` and checked with `purlin:sign --check`; it exits 1 and prints only `The package does not match its fingerprint: the fingerprint matches the content, but the bytes are not in the canonical form.`

### `states` (lane `surfaces`)

`> Highest-Rule: 126`, `> Highest-Proof: 290`. PROOF-71 and PROOF-160 are deleted with their tests.

- RULE-14: The strong cell reads the rule's audit entry, a current one before one out of date: `strong`; `weak`, with each finding among its reasons; or `spot-checked`, with the one reason `The spot tests found nothing. ` followed by the entry's `no_bug` sentences; a verdict the format does not name decides nothing, and the cell names the evidence file under `evidence`
- RULE-27: as now, with `schema version 15`
- RULE-59: `signoff` carries `word`, `version`, `commit` and `since` for the newest `signed/*` tag on HEAD or an ancestor of it whose sign-off counts, numbered versions compared as numbers, `word` reading as the status's `Sign-off:` line does, and `word` reads `not signed` where no such tag exists
- RULE-61: Every rule carries `audit`, eleven fields: the `verdict`, `findings`, `no_bug` and `notes` of its audit entry, its `explanation` and its `breaks` exactly as the entry holds them, `[]` and `{}` where it holds none, the `model` that answered or `unknown`, `at`, `commit`, the evidence file under `path`, and `out_of_date`, the parts that changed since, `[]` for a current entry; or null where the rule has no entry
- RULE-118: A strong cell with no audit entry reads `waiting`, with the reason `waiting for its tests to pass`, while the passed cell is not met, an entry or none; `no proof`, with the reason `the rule has a test and no proof`, for a passing rule no proof line names; and otherwise `not audited`, with the reason `no audit has read this rule`; none of these is `weak`
- RULE-121: as now, with `` `Strong` added where any rule has an audit entry ``
- RULE-126: An audit entry whose rule, proof, test or covered code changed since it was written makes the strong cell read `out of date`, with one reason per part that differs, `<part> changed since <sha7>`, the entry's commit, then `the last audit found it <verdict> on <date>`; the entry stays in the evidence, and the rule is left nothing to strengthen

- PROOF-31 (RULE-27): as now, with `schema_version` 15
- PROOF-73 (RULE-61): A rule whose audit entry reads `weak` with the finding `PROOF-2 reads 401 alone.` and names no model carries `audit` with exactly `verdict`, `findings`, `no_bug`, `notes`, `explanation`, `breaks`, `model`, `at`, `commit`, `path` and `out_of_date`: `weak`, that finding, `[]`, no note, `[]`, `{}`, `unknown`, the entry's time and commit, `.purlin/evidence/local/login.json` and `[]`
- PROOF-168 (RULE-59): Once the walk signs `1.2.0` at HEAD, `signoff` reads the version `1.2.0`, the signed commit, and the word `signed 1.2.0 at <sha7>`
- PROOF-169 (RULE-59): With `1.2.0` signed by the walk and one more commit made after it changing only `.purlin/evidence/local/login.json`, `signoff.word` still reads `signed 1.2.0 at <sha7>`, the tagged commit
- PROOF-170 (RULE-59): With `1.9.0`, `1.10.0` and `beta` each signed by the walk on one commit, `signoff.version` reads `1.10.0`
- PROOF-286 (RULE-126): `RULE-2` passes and its audit entry reads `strong`, written on `2026-09-13` at the commit `<c>`; `src/login.py` is rewritten and committed and its tests pass again; the strong cell reads `out of date` with exactly the reasons `code changed since <c7>` and `the last audit found it strong on 2026-09-13`
- PROOF-287 (RULE-126): With `RULE-2`'s test passing, its audit entry reads `weak` with one finding and was written for another rule text; the strong cell reads `out of date` with the first reason `rule changed since <sha7>`, its `findings` hold that finding, and the rule's `left` is null
- PROOF-288 (RULE-16): A rule has `PROOF-1` marked `@manual` and `PROOF-2` whose test passes, and its current audit entry reads `weak` with the finding `PROOF-2 reads the status alone.`; the strong cell reads `weak`, its reasons hold that finding, and its `left` is `to_strengthen`
- PROOF-289 (RULE-9): A rule's one proof fails in a current `ci` section from `linux` dated `2026-09-01T00:00:00Z` and passes in a current `local` section from `linux` dated `2026-09-02T00:00:00Z`; the passed cell reads `failed` with the reason `failing: Linux/Unix, ci`
- PROOF-290 (RULE-14): With `RULE-2`'s test passing, its current audit entry reads `spot-checked` with the one `no_bug` sentence `No bug was planted: the model could not be reached: claude is not on PATH.`; the strong cell reads `spot-checked` with the one reason `The spot tests found nothing. No bug was planted: the model could not be reached: claude is not on PATH.`

### `summary` (lane `surfaces`)

`> Highest-Proof: 57`.

- RULE-20: as now, with `for the newest `signed/*` tag on HEAD or an ancestor of it whose sign-off counts`
- RULE-22: The sentence reads `<N> rules. <p> pass their tests.`, `1 rule.` and `1 passes its tests.` for a count of one, counting each rule once under the spec that owns it; where a rule that passes has an audit entry it adds ` The audit found <s> of <n> rules strong (<p>%): <s> strong`, then `, <n> weak`, `, <n> spot-checked`, `, <n> out of date` and `, <n> not audited`, each only where not zero
- PROOF-43 (RULE-22): 50 rules that all pass their tests, 42 found strong and 8 found weak by the audit, read `50 rules. 50 pass their tests. The audit found 42 of 50 rules strong (84%): 42 strong, 8 weak.`
- PROOF-50 (RULE-20): With `0.1.0` signed by the walk and then one commit changing `src/age.py` made after it, the status's third line reads `Sign-off: signed 0.1.0, 1 commit since`
- PROOF-57 (RULE-22): 40 rules that all pass their tests, 34 found strong, 4 weak and 2 spot-checked, read `40 rules. 40 pass their tests. The audit found 34 of 40 rules strong (85%): 34 strong, 4 weak, 2 spot-checked.`

### `ai_audit` (lane `audit`)

`> Highest-Rule: 45`, `> Highest-Proof: 122`. The Description's second and third sentences
read: `For each rule it runs the heuristic spot tests, then asks the model once for the rule's
planted bugs and its reading, then plants each bug and runs its proof's test: a rule is `weak`
when a spot test fires on one of its tests or a planted bug survives, `strong` when none does
and a planted bug was caught, and `spot-checked` when none does and no bug was planted and
caught. The model's reading becomes the explanation; it decides nothing.`

- RULE-1: The audit reads a rule that is its feature's own, has at least one proof with a test, whose passed cell reads `passed`, and that has no audit entry, an entry out of date, or a proof it plants a bug for with no result recorded; reading again ignores an existing entry
- RULE-2: The request opens with `references/review_criteria.md` verbatim, then the rule's text, its proofs, the source of each test and each finding of the spot tests; where a bug is to be planted it names each such proof and holds the text of every file the feature's scope reaches, and of no other file
- RULE-3: The call is `claude -p --output-format json --max-turns 1 --tools "" --strict-mcp-config --safe-mode --setting-sources "" --disable-slash-commands --no-session-persistence --system-prompt <the audit's own>`, started in an empty folder outside the project with `DISABLE_PROMPT_CACHING=1`, the request written to its standard input, which is then closed, and given 300 seconds
- RULE-4: One call is made per rule, holding its planted bugs and its reading together; each rule is asked about exactly once, four at once, and the answers come back in the rules' order
- RULE-33: A rule's verdict comes from the spot tests and the planted bugs alone: `weak` when a spot test fires on one of its tests or a planted bug survives; else `strong` when a planted bug was caught; else `spot-checked`; and the entry records under `no_bug` one sentence for each proof no bug was caught for
- RULE-35: The audit's last line is `The audit found <s> of <n> rules strong (<p>%): ` and the counts as the status words them, counted over the rules that pass their tests, a rule with a hand check counted where it also has a tested proof
- RULE-37: No bug is planted, and the model is asked for none, for a proof of an anchor's rule or a proof tagged `@env` for a system this machine is not, and the entry's `no_bug` says which
- RULE-39: When the model cannot be reached, because `claude` is not on the path, exits with an error, runs past its 300 seconds, or answers nothing or a JSON that reports an error, no explanation is recorded and the answer is only the reason: `claude is not on PATH`, `claude exited with an error`, `claude timed out after <n> s` or `claude gave no answer`
- RULE-43: When the model cannot be reached for a rule, the spot tests and the bugs kept from earlier audits set its verdict; a rule left `spot-checked` records `No bug was planted: the model could not be reached: <why>.`, and the audit prints `The model could not be reached: <why>. <n> rules are spot-checked alone. Run purlin:audit again.`, the middle sentence left out for none
- RULE-44: The reply holds one part per proof asked for, under `=== PROOF-N ===`, and the reading under `=== reading ===`; a proof whose part is missing or names no usable change has no bug planted, with the reason recorded, and the other proofs' bugs are planted
- RULE-45: Before its first call the audit prints `The audit reads <n> rules: <n> model calls.`, and after its last, where `claude` reported a cost, `The model was asked <n> times for <n> rules: $<total> in all, $<per rule> a rule.`, the sum of what each call reported

- PROOF-14 (RULE-3): The audit asks about `RULE-2` with `claude` found at `/bin/claude`; the program started is exactly `/bin/claude -p --output-format json --max-turns 1 --tools "" --strict-mcp-config --safe-mode --setting-sources "" --disable-slash-commands --no-session-persistence --system-prompt` and the audit's system prompt, it is given 300 seconds, and the request is the whole of its standard input
- PROOF-82 (RULE-3): On Windows, with `claude.cmd` on the search path, the audit asks `claude` about `RULE-2`; it is started exactly once, its arguments beginning `-p`, `--output-format`, `json`, `--max-turns`, `1`, `--tools` and an empty argument, reads the whole question from its input, and the explanation reads `read to the end` @env(windows)
- PROOF-99 (RULE-35): Five rules pass their tests; the audit finds four `strong` and one `weak`; its last line reads `The audit found 4 of 5 rules strong (80%): 4 strong, 1 weak.`
- PROOF-100 (RULE-36): A bug planted for `PROOF-2` was caught; only `RULE-2`'s text changes, so the audit reads the rule again; the request asks for no bug, none is planted for `PROOF-2`, and its result still reads `caught`
- PROOF-102 (RULE-37): `login` is an anchor under `specs/_anchors/` whose `RULE-2` passes; the audit reads it, the request asks for no bug, and the entry of `RULE-2` reads `spot-checked` with the one `no_bug` sentence `No bug was planted: no bug is planted for an anchor's rule.`
- PROOF-104 (RULE-35): as now, its last line ending on the counts, as in `The audit found 3 of 4 rules strong (75%): 3 strong, 1 weak.` (the lane keeps the case its test holds and writes the fourth rule's word)
- PROOF-108 (RULE-43): `claude` exits with the code 1 at every call and no spot test fires on the test of `RULE-2`, the one rule read; its entry reads `spot-checked`, and the audit prints `login RULE-2   spot-checked` and, once, `The model could not be reached: claude exited with an error. 1 rule is spot-checked alone. Run purlin:audit again.`
- PROOF-109 (RULE-43): as now
- PROOF-110 (RULE-43): `claude` exits with the code 1 at every call and the audit reads two rules that pass, with no spot test firing on either; both entries read `spot-checked`, the audit prints `The model could not be reached: claude exited with an error. 2 rules are spot-checked alone. Run purlin:audit again.` once, and its last line reads `The audit found 0 of 2 rules strong (0%): 0 strong, 2 spot-checked.`
- PROOF-112 (RULE-3): The audit asks about `RULE-2` of the project at `<root>`; `claude` is started in a folder that is neither `<root>` nor under it and holds no file, with `DISABLE_PROMPT_CACHING` reading `1`, and that folder is gone when the audit ends
- PROOF-113 (RULE-4): `RULE-1` has three proofs, each with a test and none with a planted bug on record; the audit reads `RULE-1`, and `claude` is started exactly `1` time, its request naming `PROOF-1`, `PROOF-2` and `PROOF-3`
- PROOF-114 (RULE-2): The project holds `.env` with `KEY=s3cret` and the scope of `login` names `src/login.py` alone; the request for `RULE-2` holds the text of `src/login.py` and does not hold `s3cret`
- PROOF-115 (RULE-36): A bug planted for `PROOF-2` was caught; the body of its test changes from `== 401` to `== 403`; the next request asks for a bug for `PROOF-2`, and the entry's `break_key` differs from the one before
- PROOF-116 (RULE-37): On a machine that is not Windows, `RULE-8` passes on a Windows result and its one proof, `PROOF-38`, is tagged `@env(windows)`; the audit reads it, the request asks for no bug, and the entry reads `spot-checked` with `No bug was planted: PROOF-38 needs Windows, and this machine is <its system>.`
- PROOF-117 (RULE-39): `claude` exits `0` and prints nothing at every call, and no spot test fires on the test of `RULE-2`; its entry reads `spot-checked`, and the audit prints `The model could not be reached: claude gave no answer. 1 rule is spot-checked alone. Run purlin:audit again.`
- PROOF-118 (RULE-33): No spot test fires on the test of `RULE-2`, and the model answers `no break: the proof names no value the code computes` for `PROOF-2`; the entry reads `spot-checked`, its `no_bug` exactly `No bug was planted: the model found no change that would break PROOF-2: the proof names no value the code computes.`
- PROOF-119 (RULE-43): A bug kept for `PROOF-2` reads `survived`, and `claude` exits `1` at every call; the audit entry of `RULE-2` reads `weak` with the finding `PROOF-2: the test still passes when src/login.py:12 reads "return 200"`
- PROOF-120 (RULE-44): `RULE-1` has `PROOF-1` and `PROOF-2`; the reply holds a part for `PROOF-1`, whose bug is caught, and none for `PROOF-2`; the entry reads `strong`, `PROOF-1` reads `caught`, and `no_bug` is exactly `No bug was planted: the model's answer for PROOF-2 could not be used: it holds none.`
- PROOF-121 (RULE-45): The audit reads 2 rules and each call reports `total_cost_usd` `0.05`; it prints `The audit reads 2 rules: 2 model calls.` before the first call and, after the last, `The model was asked 2 times for 2 rules: $0.10 in all, $0.05 a rule.`
- PROOF-122 (RULE-1): `RULE-2`'s entry reads `spot-checked` because the model could not be reached, and nothing has changed since; the audit run again, with a `claude` that answers, reads `RULE-2` and starts `claude` exactly `1` time

### `planted_bug` (lane `audit`)

`> Highest-Rule: 13`, `> Highest-Proof: 19`. The Description's result sentence reads: `A test
that still passes reads `survived`, with the change as the finding; a test that ran and failed
reads `caught`; a test that did not run reads `not run`; a change that cannot be made reads
`not made`. A check before the model is asked and after the last bug stops the audit if the
project changed.`

- RULE-3: A test that runs and fails with the bug in place reads `caught`; a test that is skipped, is not collected or runs past its limit there reads `not run`, which is neither caught nor survived
- RULE-6: When a file of the project changes while the audit asks the model or plants a bug, the audit stops, prints `The audit stopped: <path> changed while the audit ran. Nothing in the project was written by the audit.`, writes no audit entry and exits 1
- RULE-12: A change that cannot be applied exactly once to a file the feature covers, a change to a file that holds one of the proof's tests, or an answer that names no change, is not applied and reads `not made` with its reason, and the proof's test is not run
- RULE-13: The proof's test is run in the copy before the bug is planted; where it does not pass there, no bug is planted and the result reads `not made` with the reason `the test does not pass in a copy of the project`

- PROOF-7 (RULE-6): `claude`, as it answers, writes a line to `src/age.py` in the project; the audit prints `The audit stopped: src/age.py changed while the audit ran. Nothing in the project was written by the audit.`, exits `1`, and `.purlin/evidence/local/age.json` holds the bytes it held before
- PROOF-16 (RULE-13): The test of `PROOF-1` reads `data/built.json`, a file git ignores; the model answers `file: src/age.py`, `before:` `return days`, `after:` `return 0`; the result reads `not made` with the reason `the test does not pass in a copy of the project`, not `caught`
- PROOF-17 (RULE-3): The model answers `file: src/age.py`, `before:` `def age(`, `after:` `def age_(`, so `tests/test_age.py` can no longer be collected; the result reads `not run`, not `caught`
- PROOF-18 (RULE-12): The feature's `> Scope:` names `tests/test_age.py` and the model answers `file: tests/test_age.py`, `before:` `assert age(s) == 90`, `after:` `assert age(s) == 0`; the result reads `not made` and the test of `PROOF-1` is not run
- PROOF-19 (RULE-1): The test of `PROOF-1` runs past its limit with the bug in place; afterwards every file of the project holds the same bytes as before

### `plain_checks` (lane `audit`)

`> Highest-Rule: 10`, `> Highest-Proof: 32`.

- RULE-6: A test whose file holds none of the values its proof marks in backticks reads `<file>::<test>: the proof expects <value> and the test never checks it.`; a proof with no value in backticks, an empty pair of backticks, the same number written another way, or a value held in a data file the test's file names, is not flagged
- RULE-10: A marked test whose source cannot be found is named once, as `<file>::<test>: its source was not found, so the spot tests did not read it.`
- PROOF-31 (RULE-10): The evidence names `test_renamed_away` for `PROOF-1`, which `tests/test_login.py` no longer holds; the audit prints `tests/test_login.py::test_renamed_away: its source was not found, so the spot tests did not read it.` exactly once
- PROOF-32 (RULE-6): `PROOF-1` reads "an empty barcode `` is handed in; it is refused with `barcode is required`", and `tests/test_intake.py` holds `barcode is required`; nothing is found

### `evidence_writer` (lane `evidence`)

`> Highest-Proof: 98`.

- RULE-12: `--audit` writes one `audit.rules` entry for each rule the audit read, carrying the rule, proof, test and code hashes it read, its `verdict`, `strong`, `weak` or `spot-checked`, its `findings`, its `no_bug`, its `breaks`, its `explanation`, the `model` that answered, the sha256 of the `criteria` it was sent, `at` and `commit`, and leaves every other rule's entry as it was
- RULE-14: An audit entry that repeats the one already there, with the same four hashes, `verdict`, `findings`, `no_bug`, `model` and `criteria`, is left as it was, `at` and `commit` included; an entry that differs in any of them, the model that answered included, replaces it
- RULE-31: A section that saw the same results over the same fingerprint, on the same machine and with the same `dirty`, as the one on disk leaves the file byte for byte as it was, `at` included, where every commit since the one the section names changes only paths under `.purlin/`, so a second run finds nothing new to commit; any other section replaces it, with its own `at`, `commit`, `dirty` and `email`
- PROOF-54 (RULE-12): In a git checkout whose model `claude-fake-1` answers `no break: the code has nothing to change` for `PROOF-1`, `--all --audit` writes an entry for `RULE-1` with the four hashes status gives it, `verdict` `spot-checked`, empty `findings`, one `no_bug` sentence, `breaks` reading `PROOF-1` `not made`, `model` `claude-fake-1`, the criteria's sha256 and HEAD's sha as `commit`
- PROOF-97 (RULE-31): `--all --test` runs while `notes.txt` is written and not added to git, and the section's `dirty` is true; `notes.txt` is deleted and `--all --test` runs again on the same commit; the section's `dirty` is false
- PROOF-98 (RULE-19): In a git checkout where the spec `feat` and `src/other.py` are both edited and not committed, `--all --test --commit` commits `specs/a/feat.md` and not `src/other.py`, which `git status` still lists as changed, and the section's `dirty` is true

### `evidence` (lane `evidence`)

`> Highest-Proof: 89`.

- RULE-7: The `tests` part covers every tracked test file, one a suite of the `tests` setting names, carrying a marker for the feature, and the `tests` setting itself; editing such a file or that setting changes `tests` and no other part; a marker for another feature is not counted, and neither is the settings file's `version`
- RULE-16: The audit entry for a rule is the one either source holds, a current one before one out of date and then the later `at`; it is current while its `rule_hash`, `proof_hash`, `test_hash` and `code_hash` all equal the ones asked for, whatever its `commit`, and otherwise names each part that differs, `rule`, `proof`, `test` or `code`
- PROOF-22 (RULE-16): as now, with the four hashes `r`, `p`, `t` and `c` stored and asked for
- PROOF-58 (RULE-16): The `local` file holds an audit entry for RULE-1 with the hashes `r`, `p`, `t` and `c`; asked for RULE-1 with `r`, `p`, `t2` and `c`, the reader returns the entry as out of date on exactly `test`
- PROOF-86 (RULE-16): Both files hold an entry for RULE-1 with the hashes `r`, `p`, `t` and `c`: `ci` reads `strong` at `2026-09-01T00:00:00Z` and `local` reads `weak` at `2026-09-02T00:00:00Z`; asked for RULE-1 with those hashes, the reader returns the `weak` entry, naming the source `local`
- PROOF-87 (RULE-16): The `local` file holds an audit entry for RULE-1 with the hashes `r`, `p`, `t` and `c`; asked for RULE-1 with `r`, `p`, `t` and `c2`, the reader returns the entry as out of date on exactly `code`
- PROOF-88 (RULE-7): A `local` section of `login` stores the fingerprint taken now; the `run` command of the `tests` setting in `.purlin/config.json` is then changed; checked against a fingerprint taken again, the section reads out of date on exactly `tests`
- PROOF-89 (RULE-7): A `local` section of `login` stores the fingerprint taken now; the `version` in `.purlin/config.json` is then changed from `0.10.0` to `0.10.1`; checked against a fingerprint taken again, the section reads current

### `run_script` (lane `evidence`)

`> Highest-Proof: 285`.

- RULE-105: as now, its second sentence opening `Where a suite's command is none of these tools', already carries that option, the option would also leave out a test that is not slow, or the test is one NUnit names row by row, under `[TestCase]` or `[TestCaseSource]`, the slow test is started, its result counts, and the run prints`
- RULE-106: A run that leaves a slow proof's test out keeps the result the section it replaces holds for that proof where that section was taken over the same spec, code and tests, and marks it `kept` with the `commit`, `at`, `machine` and `email` of the run that took it, so the status keeps counting it and the sign-off does not; where it was taken over others, the proof reads `not run`
- PROOF-281 (RULE-106): In a git checkout, `--all --test --commit` passes `feat`'s slow `PROOF-2` at the commit `<c>`; `README.md`, which no scope names, is changed and committed; `--feature feat --test --commit` runs; the evidence lists `PROOF-2` as `pass` with `kept` naming the commit `<c>`, and the section's own `commit` is the new one
- PROOF-282 (RULE-100): In a git checkout whose one marked test fails, `--all --test` exits 1; with nothing changed, `--test` with no feature named prints `Nothing to run`, starts no suite, and exits 1
- PROOF-283 (RULE-12): `feat`'s `PROOF-2` is tagged for this machine's system and its test fails; `--all --ci` exits 1, and `.purlin/evidence/ci/feat.json` lists `PROOF-2` as `fail` and reads `RULE-1` `failed`
- PROOF-284 (RULE-98): Started in a Purlin project as `--all --test --project-root ''`, the run exits 2, prints `purlin: --project-root needs a directory, not an empty value.`, and writes nothing under that project's `.purlin/`
- PROOF-285 (RULE-105): A slow test declared under `[TestCase(1)]` in a dotnet suite is started: the command the run starts for that suite carries no `--filter`, and the run prints `Started 1 slow test in the dotnet suite: its command gives Purlin no way to leave one test out.` and no `Left out` line

### `reports` (lane `evidence`)

`> Highest-Rule: 38`, `> Highest-Proof: 120`.

- RULE-38: A marker-shaped line inside a string of a test file, or inside a here document of a shell file, is not a marker and ties nothing
- PROOF-119 (RULE-38): A Python test file holds `# purlin: login PROOF-1` on line 2, inside a triple-quoted string, and `# purlin: login PROOF-2` as a comment on line 5 above the passing `test_ok`; one marker is read, `PROOF-2` at line 5, and the evidence holds no `pass` for `PROOF-1`
- PROOF-120 (RULE-33): `login`'s `RULE-1` has `PROOF-1`, and a passing test on line 3 is marked `purlin: login RULE-1`; the run prints `tests/test_login.py:3 names login RULE-1, which has proofs; a comment names one of its proofs. Correct the comment, or run purlin:build to repair it.`, exits 1, and the evidence holds no `pass` under `RULE-1`

### `update`, `upstream`, `purlin_agent` (lane `setup`)

`update`, `> Highest-Rule: 56`, `> Highest-Proof: 165`:

- RULE-55: The update removes a workflow under `.github/workflows/` only where it wrote 0.9.5's proof files, backs it up first, and leaves every other workflow as it was
- RULE-56: An anchor whose `> Source:` is a git address keeps its `> Source:` and `> Pinned:` lines through the update, byte for byte
- PROOF-164 (RULE-55): The sample 0.9.5 project holds `purlin-proofs.yml`, which commits `*.proofs-*.json`, and `ci.yml` running `pytest`; after the update with `--yes` the first is gone with a backup holding its bytes, `ci.yml` is byte for byte as it was, and the output holds `removed 1 workflow that committed proof files`
- PROOF-165 (RULE-56): An anchor whose `> Source:` is `https://github.com/acme/figma-tokens.git specs/tokens.md` with a `> Pinned:` sha of 40 characters is exactly what it was after the update with `--yes`, and no backup is written beside it

`upstream`, `> Highest-Rule: 40`, `> Highest-Proof: 62`:

- RULE-40: `add` refuses a name an anchor in the project already holds, writes nothing and names `purlin:anchor sync <name>`
- PROOF-61 (RULE-22): The published anchor is added with `--name ../../outside`; it exits 2, the answer reads `error`, `specs/_anchors/` stays empty and no `outside.md` exists under the folder around the project
- PROOF-62 (RULE-40): With `specs/_anchors/no_eval.md` holding the project's own rule `No eval in scripts`, the published anchor is added as `no_eval`; it exits 2, the answer reads `error`, and the file holds exactly its text from before

`purlin_agent`, `> Scope: agents/purlin.md, skills/, references/`, `> Highest-Rule: 23`,
`> Highest-Proof: 54`. The Description gains: `It also holds four checks on what every skill,
the agent definition and the references tell an agent to run.`

- RULE-20: Every path under `scripts/`, `references/`, `templates/`, `skills/` or `docs/` that a skill or the agent definition names is a file or folder in the repository
- RULE-21: Every flag a skill writes on a line that runs a script is one that script takes
- RULE-22: The answers file the sign skill shows is one `purlin:sign --answers` walks without a refusal about the file
- RULE-23: No skill, agent definition or reference names a path under `dev/`, `/dev/null` aside
- PROOF-51 (RULE-20): Each such path read out of the ten `SKILL.md` files and `agents/purlin.md` exists; the same check on a copy of the sign skill naming `scripts/review/signoff.py` lists that path
- PROOF-52 (RULE-21): Each `--flag` on a line of a `SKILL.md` naming a `scripts/**/*.py` is in that script's `--help`; the same check on a copy of the test skill passing `--remote` to `purlin_run.py` lists `--remote`
- PROOF-53 (RULE-22): The JSON block under `Step 5` of `skills/sign/SKILL.md`, written to `.purlin/runtime/signoff-answers.json` in a project whose hand checks are `accession_screen RULE-1` and `sample_age RULE-6`, is walked with `--answers`; it exits 0 and the sign-off holds the note `the tube is red`
- PROOF-54 (RULE-23): No line of `skills/*/SKILL.md`, `agents/purlin.md` or `references/**/*.md` holds `dev/` once every `/dev/null` is set aside; the same check on a copy of the build skill naming `dev/test_x.py` lists that line

### `purlin_report` (lane `surfaces`)

`> Highest-Proof: 240`.

- RULE-8, RULE-9, RULE-15: as now, each `wherever the audit found a rule strong or weak` reading `wherever a rule has an audit entry`
- RULE-39: Wherever a rule has an audit entry, the rule screen carries an `Audit` panel that reads what the audit found: `No audit has read this rule yet.` where it has none; otherwise `Strong. It found nothing.`, `Weak.` followed by each finding, or `Spot-checked.` followed by `The spot tests found nothing.` and each `no_bug` sentence, then the model's explanation; an entry out of date opens the panel with `Out of date:` and the cell's reasons
- PROOF-147 (RULE-39): as now, the line reading `No audit has read this rule yet.`
- PROOF-239 (RULE-39): Open the regulated sample's export `RULE-1` after its audit is given the verdict `spot-checked` and the `no_bug` sentence `No bug was planted: no bug is planted for an anchor's rule.`; its strong row reads `SPOT-CHECKED`, and its `Audit` panel reads `Spot-checked.`, then `The spot tests found nothing. No bug was planted: no bug is planted for an anchor's rule.`
- PROOF-240 (RULE-39): Open the regulated sample's login `RULE-1` after its audit is marked out of date on `code` at `a1b2c3d`; its strong row reads `OUT OF DATE` with the reasons `code changed since a1b2c3d` and `the last audit found it strong on 2026-09-13`, and the `Audit` panel opens with `Out of date:` and still reads `Strong. It found nothing.`

## 4. The code, by file and function

### 4.1 The reproductions that come first

Each fix starts with its proof's test, written and run before any code changes. The lane
records the failing output in its report.

| Finding | The failing test | What it shows on today's code |
|---|---|---|
| The re-stamped slow result (read, not reproduced) | `run_script` PROOF-281, in `dev/test_run_script.py` | the section's `commit` is the new one, `PROOF-2` reads `pass`, and no key says it ran at `<c>` |
| The same, at the sign-off | `package` PROOF-79's scenario made with real runs, once, at integration | `sign.py --show` exits 0 over a slow result taken before the `README.md` commit |
| The tag git could not write (read, not reproduced) | `signatures` PROOF-255, in `dev/test_signatures.py` | the second run prints `jane@acme.com has already signed 2.1.0 over this package; nothing was written.`, exits 1, and `signed/2.1.0` does not exist |
| The edited package | `signatures` PROOF-254 | `load_signoffs` still answers `counts` true, and the second signer's walk signs the edited content |
| The hand-typed tag | `signatures` PROOF-252 | `signoff.word` reads `signed 9.9.9 at <sha7>` and the warnings are empty |

### 4.2 Lane `signoff`

| File, function | Change |
|---|---|
| `scripts/mcp/purlin/signatures.py`, `standing(project_root, version)` (new) | `(True, '')` where `signed/<version>` names a commit that holds `package_rel(version)` and `load_signoffs` gives one that counts; else `(False, why)`, K5 |
| `signatures.py`, `committed_fingerprint` | computes `package.fingerprint_of` over the package `HEAD` holds, imported inside the function; the stored field is not read |
| `signatures.py`, `load_signoffs` | lists and reads each file with `git ls-tree` and `git show HEAD:`; the working tree is not read |
| `signatures.py`, `hand_notes` (moved in by the base commit) | reads only sign-offs that count |
| `signatures.py`, `key_fingerprint`, `_KEY_LITERAL` | the `key::` arm and its docstring words are deleted (answer 4c: no doc or spec names it) |
| `signatures.py`, `signer_slug`; `sign.py`, `signoff_rel`, `already_signed` | `signoff_rel(project_root, version, email)` takes `<slug>.json`, or `<slug>-2.json`, `-3` and on where `HEAD` holds that name for another `signer` |
| `scripts/mcp/purlin/facts.py`, `signoff_fact` | newest tag first, the first for which `standing` holds answers; each tag passed over adds one line to `warnings` (K5) |
| `scripts/review/sign.py`, `uncommitted_work` | skips only paths under `.purlin/evidence/` |
| `sign.py`, `refusal` | a later sign-off checks `package.check_bytes` over `HEAD`'s package and refuses with `NO_SIGNOFF_PACKAGE`; where the tag is missing and `HEAD` holds this version's package, `info` carries `tag_at`, the commit that added it |
| `sign.py`, `write_tag(project_root, name, message, at)`, `_sign`, `walk`, `walk_with_answers`, `show` | the tag is written on `tag_at`; a signer who already signed gets the tag alone; `NO_TAG_GIT` ends on its fix |
| `sign.py`, `plan`, `_weak`, `OVERVIEW_AUDIT` | a rule is weak by its strong cell's word; the overview prints `summary.audit_words`; `overview.audit` carries the five counts |
| `scripts/export/package.py`, `only_records_between` | a commit that changes `.purlin/config.json` counts as a change to the code where the `tests` setting differs between the two ends (`_tests_setting(project_root, ref)`, new) |
| `package.py`, `_results` | `same_code` is false where a proof entry of the rule in that section carries `kept` |
| `package.py`, `_audit`, `audit_counts` | each rule's `audit` gains `no_bug` and `out_of_date`; the counts are five and read each rule's strong word |

### 4.3 Lane `evidence`

| File, function | Change |
|---|---|
| `scripts/run/purlin_run.py`, `keep_slow_results` | a kept entry carries `kept` (K1) |
| `scripts/run/evidence.py`, `build_section` | writes `kept` on the entry it lists |
| `scripts/run/evidence.py`, `_same_observation` | compares `dirty`; leaves each proof entry's `kept` out |
| `scripts/mcp/purlin/fingerprint.py`, `tests_hash` | adds the line `tests-setting <sha256 of the setting, as JSON with sorted keys>` where the settings file holds `tests` |
| `scripts/mcp/purlin/markers.py`, `Test`, `cs_tests` | a C# test records `rows`, true under `[TestCase]` or `[TestCaseSource]` |
| `scripts/mcp/purlin/frameworks.py`, `leave_out` | for `dotnet`, a test with `rows` goes to `started`, and no filter names it |
| `purlin_run.py`, the `--ci` exit, `_nothing_to_run`, the empty `--project-root` | no change: three proofs only |

### 4.4 Lane `audit`

| File, function | Change |
|---|---|
| `scripts/review/ai_audit.py`, `COMMAND`, `SYSTEM_PROMPT`, `ask_model` | the command of section 2.4; `cwd` is the audit's empty folder; the environment gains `DISABLE_PROMPT_CACHING=1`; an empty answer, output that is not JSON, or `is_error` true answers `why` `NO_ANSWER` |
| `ai_audit.py`, `model_prompt`, `REQUEST_BUGS`, `REPLY_SHAPE` | one request per rule (K3); `bug_prompt`, `BUG_INSTRUCTION` and `ask_for_bug` are deleted |
| `ai_audit.py`, `read_reply(text, proofs)` (new) | `({proof: text}, explanation, notes)` from the parts of a reply (K3) |
| `ai_audit.py`, `is_read` | reads a rule with no entry, an entry out of date, or a proof to plant for with no result under `breaks` |
| `ai_audit.py`, `STRONG_NOTHING`, `VERDICT_WORDS`, `verdict_lines`, `NO_AUDIT` | gain `Spot-checked.` and the `no_bug` sentences; `NO_AUDIT` reads `No audit has read this rule yet.` |
| `scripts/review/audit_run.py`, `run` | the order of section 2.4; one snapshot before the first call, compared after each rule's bugs; `CALLS_ONE`, `CALLS_MANY` printed first; the verdict of section 2.2; `no_bug` and `code_hash` handed to `evidence_writer.audit_entry`; the last line from `summary.audit_line` |
| `audit_run.py`, `planted_bugs` | takes the reply's parts in place of `ask`; skips a proof tagged for another system; builds each `no_bug` sentence (K2) |
| `audit_run.py`, `spot_tests` | a test whose `body` is None prints `NOT_FOUND` once |
| `audit_run.py`, `code_changed`, `reaching`, `NOT_PLANTED`, `NOT_AUDITED`, `STAY_ONE`, `STAY_MANY`, `SHARE` | deleted |
| `scripts/review/targeted_break.py`, `break_proof(project_root, feature, proof, tests, scope_files, answer, timeout=None)` | takes the proof's part of the reply; no longer takes its own snapshot; returns `cause` (K2) |
| `targeted_break.py`, `_plant` | refuses a file that holds one of the proof's tests (`TEST_FILE`); runs the tests in the copy before the change and answers `not made` with `BASELINE` unless every one reads `pass` |
| `targeted_break.py`, `_all_pass` becomes `_run_tests`, answering `pass`, `fail` or `not run` | `fail` where a test of the proof's own reads `fail`; `pass` where all read `pass` and no suite reported a failure; else `not run`. `caught` needs `fail` |
| `targeted_break.py`, `STOPPED` | `The audit stopped: %s changed while the audit ran. Nothing in the project was written by the audit.` |
| `scripts/review/plain_checks.py`, `_BACKTICK_RE`, `_value_never_checked` | backticks are paired left to right, an empty pair is a pair, and only a pair holding text names a value |
| `dev/fake_claude.py` | each call's line in `calls.jsonl` gains `cwd` and `env`, the value of `DISABLE_PROMPT_CACHING`; nothing else changes, and the default answer stays |

Spot test 4 is not changed. The missed case, an expected value computed by a second function of
the code under test, needs to know which functions belong to the code under test. A rule by
name alone would flag a test that checks one implementation against another on purpose. No
simple, exact rule does it, so it is left: the planted bug caught the case in the measurement,
and the model's reading named it.

### 4.5 Lane `surfaces`

| File, function | Change |
|---|---|
| `scripts/mcp/purlin/states.py`, `_strong_cell`, `_flags`, `COUNTED_FLAGS` | the words of `states` RULE-14, 118 and 126; the flags `spot_checked` and `audit_out_of_date`; `EARLIER_WEAK` is deleted, it is used nowhere; `NOT_AUDITED_REASON` reads `no audit has read this rule` |
| `scripts/mcp/purlin/payload.py`, `SCHEMA_VERSION`, `audit_summary`, `_rule_entry` | schema 15; the eleven fields; the base commit's one line that hid an entry out of date is taken out |
| `scripts/mcp/purlin/summary.py`, `audit_counts`, `sentence` | the five counts, read from each rule's strong word; the sentence of `summary` RULE-22 |
| `scripts/mcp/purlin/status.py`, `board.py` | `Strong` is shown where any rule has an audit entry |
| `scripts/report/src/app.js`, `rule.js`, `board.js` | `SCHEMA` 15; `audited()` counts the four words; `spot-checked` takes the neutral tone and `out of date` the warn tone; the `Audit` panel of `purlin_report` RULE-39 |
| `dev/fixtures/report/{regulated,team,solo}.json` | schema 15, `summary.audit` with five counts, each audit with `no_bug` and `out_of_date` |

### 4.6 Lane `setup`

| File, function | Change |
|---|---|
| `scripts/init/update.py`, `FIGMA_SOURCE_RE` | `^>\s*Source:\s*\S*figma\.com/`, so only an address at `figma.com` is a Figma source |
| `update.py`, `_detect_workflows` | no change: one proof |
| `scripts/anchor/upstream.py`, `add` | a `--name` that is not letters, digits and `_` is refused with `NAME_REFUSED`; a name `specs/_anchors/<name>.md` already holds is refused with `NAME_TAKEN`; both before anything is fetched |
| `dev/skill_checks.py`, `named_paths`, `script_flags`, `dev_paths` (new) | the three readings `purlin_agent` PROOF-51, 52 and 54 use |

## 5. The base commit, the lanes and their contracts

All local. No cloud session. Nothing is pushed by a lane.

### 5.1 The order

1. **Step 0** (section 2.4): the coordinator checks the flags with real calls. Done: five calls, every flag accepted.
2. **The base commit, by the coordinator, on `main`.** This plan as `dev/plans/d121-plan.md`;
   decision 121 under its number in `dev/plans/three-levels.md`; and the seams below, changed
   once and then frozen. `bash dev/run_tests.sh` is run after it, and the tests it leaves red
   are listed in the lane brief. Expected red, and no other: the tests of `evidence` PROOF-22
   and PROOF-58 in `dev/test_evidence_reader.py`, which call the reader with three hashes, and
   any test of `dev/test_states.py` that writes an audit entry by hand with no `code_hash`.
   Their lanes reword and fix them.
3. **Six lanes in parallel**: `git worktree add /Users/richlabarca/LocalCode/purlin-wt/d121-<lane> -b lane/d121-<lane> main`.
4. **Integration** (section 8).

**The seams of the base commit**, each small and exact:

| Seam | File | What |
|---|---|---|
| B1 | `scripts/run/evidence.py` | `audit_entry` also writes `code_hash`, `found.get('code_hash') or ''`, and `no_bug`, a list of strings; `_same_audit`'s keys are `rule_hash`, `proof_hash`, `test_hash`, `code_hash`, `verdict`, `findings`, `no_bug`, `model`, `criteria`; `write_could_not_run` is deleted |
| B2 | `scripts/mcp/purlin/evidence.py`, `scripts/export/package.py` | `audit_entry(loaded, rule_id, rule_hash, proof_hash, test_hash, code_hash)` as K2 gives it; `could_not_run`, `why_not_audited` and `COULD_NOT_RUN_PATH` are deleted; `package._features` hands each rule's `_audit` the feature's `code` part, its one other caller |
| B3 | `scripts/mcp/purlin/payload.py` | `_read_evidence` keeps each feature's `code` part; `_rule_entry` hands it to `audit_entry` and, until lane `surfaces` lands, treats an entry out of date as none (one line, so every cell reads as today); the could-not-run call goes; `warnings.extend(signoff.pop('warnings', None) or ())` after `signoff_fact`; `hand_notes` and `_distance` move to `signatures.py`, and `sign.last_notes` calls `signatures.hand_notes` |
| B4 | `scripts/mcp/purlin/states.py` | `COULD_NOT_RUN` and the `could_not_run` input go; `specs/mcp/states.md` loses PROOF-71 and RULE-118's clause `or the AI audit could not run: <why>`, and `dev/test_states.py` loses that test |
| B5 | `scripts/mcp/purlin/summary.py` | `AUDIT_WORDS`, `audit_words(counts)` and `audit_line(counts)` as K4 gives them, used by nothing yet |
| B6 | `dev/mcp_project.py`, `dev/sign_project.py` | each `audit(...)` helper writes `code_hash`, the feature's `code` part taken then, and takes `no_bug=()` |
| B7 | `references/formats/evidence_format.md` | `> Format-Version: 10`: the audit entry's `code_hash` and `no_bug`, `verdict` `spot-checked`, `result` `not run`, and when an entry is current (section 7) |

### 5.2 The lanes

| Lane | Owns, and writes nothing else | Acceptance |
|---|---|---|
| `signoff` | `scripts/review/sign.py`, `scripts/mcp/purlin/signatures.py`, `scripts/mcp/purlin/facts.py`, `scripts/export/package.py`; `specs/review/signatures.md`, `specs/export/package.md`; `references/formats/package_format.md`, `references/formats/signature_format.md`; `dev/test_signatures.py`, `dev/test_export.py` | the four reproductions of section 4.1 that are its own fail first, then pass; `python3 -m pytest dev/test_signatures.py dev/test_export.py dev/test_collaboration.py -q` passes; every proof of both specs has a test comment |
| `evidence` | `scripts/run/purlin_run.py`, `scripts/run/evidence.py`, `scripts/mcp/purlin/evidence.py`, `scripts/mcp/purlin/fingerprint.py`, `scripts/mcp/purlin/frameworks.py`, `scripts/mcp/purlin/markers.py`; `specs/run/run_script.md`, `specs/run/evidence_writer.md`, `specs/run/reports.md`, `specs/mcp/evidence.md`; `references/formats/evidence_format.md`; `dev/test_run_script.py`, `dev/test_evidence_writer.py`, `dev/test_evidence_reader.py`, `dev/test_fingerprint.py`, `dev/test_reports.py` | PROOF-281 fails first, then passes; its five test files pass but `evidence_writer` PROOF-54, which waits on lane `audit` and is named in its report |
| `audit` | `scripts/review/audit_run.py`, `ai_audit.py`, `targeted_break.py`, `plain_checks.py`, `marked_tests.py`; `specs/review/ai_audit.md`, `planted_bug.md`, `plain_checks.md`; `references/review_criteria.md`; `dev/test_ai_audit.py`, `dev/test_ai_audit_tests_named.py`, `dev/test_planted_bug.py`, `dev/test_plain_checks.py`, `dev/fake_claude.py` | its four test files pass with no real `claude`; `ai_audit` PROOF-14 holds the flag list step 0 froze; each sentence of `references/review_criteria.md` it changed is listed in its report, before and after |
| `surfaces` | `scripts/mcp/purlin/states.py`, `payload.py`, `summary.py`, `status.py`, `board.py`, `report_data.py`; `scripts/report/src/*`; `dev/fixtures/report/*.json`; `specs/mcp/states.md`, `specs/mcp/summary.md`, `specs/dashboard/purlin_report.md`; `dev/test_states.py`, `dev/test_summary.py`, `dev/test_backing_tests.py`, `dev/test_failing.py`, `dev/test_purlin_report.py`, `dev/test_purlin_report_board_layout.py`, `dev/test_report_refresh.py` | its test files pass; the page was looked at with Playwright from the `.venv`, in both themes, at 390, 768, 1024, 1280 and 1500 pixels, with a `spot-checked` rule and one out of date on screen, and no value wraps |
| `setup` | `scripts/init/update.py`, `scripts/anchor/upstream.py`; `specs/init/update.md`, `specs/anchor/upstream.md`, `specs/instructions/purlin_agent.md`; `dev/test_init_update.py`, `dev/test_upstream.py`, `dev/test_purlin_agent.py`, `dev/skill_checks.py`; `dev/fixtures/upgrade-0.9.5/` where PROOF-164 needs its two workflows | its three test files pass; PROOF-165 fails first on `figma-tokens.git`, then passes |
| `words` | `README.md`, every page under `docs/`, `skills/*/SKILL.md`, `agents/purlin.md`, `references/glossary.md`, `evidence_and_signoff.md`, `purlin_commands.md`, `spec_quality_guide.md`, `commit_conventions.md`, `writing_style.md`, `RELEASE_NOTES.md`, `CLAUDE.md`, `dev/plans/deck/build_deck.py`; `dev/test_skill_*.py`, `dev/test_purlin_docs.py` | every line is section 6's; `python3 -m pytest dev/test_skill_*.py dev/test_purlin_docs.py dev/test_purlin_agent.py dev/test_purlin_output.py -q` passes; no dollar figure stands in a skill or a doc page but in the experimental note, if step 6 of section 8 adds it |

Merge order: `evidence`, `audit`, `signoff`, `surfaces`, `setup`, `words`, each `--no-ff`. No
two lanes own one file, so any order merges clean; `evidence` and `audit` go first because the
one waiting test clears on them.

**The lane prompt** is the brief of decision 120 (`d120-lane-brief.md`), with: this plan in
place of the reading report; decisions 100 to 121; `d121` in every path and branch; the report
at `dev/plans/d121-reports/<lane>.md`; and "each fix starts with its proof's test, run once to
see it fail for the reason section 4.1 gives". Two traps hold: never `git checkout -- specs/`,
and no generated file is staged (`scripts/report/purlin-report.html`, `.purlin/evidence/**`,
`.purlin/report-data.js`, `docs/images/*.png`).

### 5.3 Contracts, word for word

**K1. A kept slow result** (`evidence` writes; `signoff` reads).

```json
{"id": "PROOF-2", "rule": "RULE-2", "env": null, "manual": false, "result": "pass",
 "test": "tests/test_feat.py::test_slow",
 "kept": {"commit": "<40 hex>", "at": "2026-10-01T12:17:13Z", "machine": "dana-laptop",
          "email": "dana.dev@labconnect.example"}}
```

`kept` is there only on an entry whose result this run did not take. It is copied from the
entry it was kept from where that one carries it, else filled from that section's `commit`,
`at`, `machine` and `email`. A reader counts a kept `pass` as a `pass`; `package._results`
alone reads `kept`.

**K2. The audit entry** (base B1 writes; base B2 reads; `audit` fills; `surfaces`, `signoff` read).

```json
{"rule_hash": "<sha256>", "proof_hash": "<sha256>", "test_hash": "<sha256>",
 "code_hash": "<the feature's code part>", "verdict": "spot-checked",
 "findings": [], "no_bug": ["No bug was planted: PROOF-38 needs Windows, and this machine is macOS."],
 "breaks": {"PROOF-24": {"file": "src/x.py", "line": 12, "before": "...", "after": "...",
                         "result": "caught", "why": "", "break_key": "<sha256>"}},
 "explanation": ["..."], "model": "claude-opus-5-5", "criteria": "<sha256>",
 "at": "2026-10-01T12:05:00Z", "commit": "<40 hex>"}
```

`verdict` is `strong`, `weak` or `spot-checked`. A break's `result` is `caught`, `survived`,
`not made` or `not run`. A proof the model could not be reached for, or that is tagged for
another system, has no entry under `breaks`.

```python
# scripts/mcp/purlin/evidence.py
AUDIT_PARTS = (('rule', 'rule_hash'), ('proof', 'proof_hash'),
               ('test', 'test_hash'), ('code', 'code_hash'))

def audit_entry(loaded, rule_id, rule_hash, proof_hash, test_hash, code_hash):
    """The rule's audit entry, or None: a current one before one out of date,
    then the later `at`. A copy carrying `source`, `path` and `out_of_date`,
    the parts of `rule`, `proof`, `test` and `code` whose stored hash differs
    from the one given, in that order; [] for a current entry."""
```

```python
# scripts/review/audit_run.py, the sentences of `no_bug`
NO_BUG = 'No bug was planted: %s.'
MODEL_FOUND_NONE = 'the model found no change that would break %s: %s'   # PROOF-N, its reason
ANSWER_UNUSABLE = "the model's answer for %s could not be used: %s"     # PROOF-N, what was wrong
BASELINE = 'the test of %s does not pass in a copy of the project'       # PROOF-N
UNREACHED = 'the model could not be reached: %s'                         # ai_audit's reason
ANCHOR = "no bug is planted for an anchor's rule"
OTHER_SYSTEM = '%s needs %s, and this machine is %s'                     # PROOF-N, Windows, macOS
NOT_RUN = 'A bug was planted for %s and its test did not run.'           # a whole sentence
NO_PART = 'it holds none'
SPOT_CHECKED = 'The spot tests found nothing. %s'   # the `no_bug` sentences joined by one space
```

`targeted_break.break_proof` returns `cause`, one of `''`, `'model found none'`,
`'answer unusable'` and `'test does not pass'`, and `why` as today; `audit_run` picks the
sentence by `cause`. `what was wrong` is `targeted_break`'s own words: `the answer named no
change`, `<path> is not a file the feature's scope names`, `the lines before the change are
not in <path>`, and the others it holds, with the new `TEST_FILE = "%s holds one of the proof's tests"`.

**K3. The request and the reply** (`audit`).

The request, in this order: `references/review_criteria.md` byte for byte; `---`; `<feature>
<RULE-N>`; `Rule: <text>`; each proof as `PROOF-N[ @manual][ @env(<os>)]: <text>`; each test as
`Test for PROOF-N: <file>::<name>` and its source; `Findings:` and each spot test's finding as
`- <sentence>`, or `none`; then, where a bug is asked for:

```
---

Plant one bug for each of: PROOF-2, PROOF-4.
For each, make the smallest change to one of the files below that would break what that proof
says, so that a test checking the proof fails.

File: src/login.py
<its text>
```

and last, always:

```
---

Answer in this shape and with nothing else. One part for each proof named above, the lines
under before: copied exactly from the file:

=== PROOF-2 ===
file: <the path, as given above>
before:
<the exact lines>
after:
<the lines>

or, for a proof no change to these files can break:

=== PROOF-2 ===
no break: <why, in one sentence>

Then the reading:

=== reading ===
- <one sentence>
notes:
- <one sentence naming a proof>
```

Where no bug is asked for, the two paragraphs on parts are left out and the shape is the
reading alone. A reply is cut at each line matching `^=== (PROOF-\d+|reading) ===\s*$`. A
proof's part is read by `targeted_break.parse_answer`. A proof asked for with no part reads
`not made`, `cause` `'answer unusable'`, `why` `NO_PART`, and its `break_key` is recorded, so
it is asked for again only when its test or code changes. A reply with no head at all is read
whole as the reading. A reply with no `=== reading ===` leaves the explanation empty.

**K4. The audit's counts** (base B5; `surfaces` fills `audit_counts`; `audit`, `signoff` call).

```python
# scripts/mcp/purlin/summary.py
AUDIT_WORDS = (('strong', 'strong'), ('weak', 'weak'), ('spot_checked', 'spot-checked'),
               ('out_of_date', 'out of date'), ('not_audited', 'not audited'))
AUDIT_SHARE = 'The audit found %d of %d rules strong (%d%%): %s.'

def audit_words(counts):
    """`34 strong, 4 weak, 2 spot-checked`: `strong` always, each other count
    only where it is not zero, in AUDIT_WORDS' order."""

def audit_line(counts):
    """AUDIT_SHARE over the five counts: strong, their sum, the whole per cent
    rounded down, `audit_words(counts)`."""
```

`summary.audit`, the package's `audit` and the sign-off's `shown.overview.audit` each carry the
five keys `strong`, `weak`, `spot_checked`, `out_of_date`, `not_audited`. A reader counts a rule
by its strong cell's word. `audit.verdict` is the entry's last result and may be out of date.

**K5. Where the status reads `signed`** (`signoff`; `surfaces` reads the payload).

`signatures.standing(project_root, version)` decides it and nothing else does.
`facts.signoff_fact(project_root)` answers `word`, `version`, `commit`, `since` and `warnings`;
the payload moves `warnings` into its own list (B3) and `signoff` keeps its four keys.

```python
# scripts/mcp/purlin/signatures.py
NO_PACKAGE_AT_TAG = ('%s: it names a commit that holds no evidence package for %s, so it '
                     'is not a sign-off. Delete it: git tag -d %s.')           # tag, version, tag
NO_SIGNOFF_COUNTS = ('%s: no sign-off of %s counts: %s. Restore the files as they were '
                     'signed, or sign this code: purlin:sign --version <version>.')  # tag, version, count_reason
```

**K6. The settings file** (`signoff`, `evidence`). The `tests` setting is the value of the key
`tests` in `.purlin/config.json`, compared as parsed JSON. `fingerprint.tests_hash` covers it;
`package.only_records_between` reads a commit that changes it as a change to the code.
`version` is covered by neither.

**K7. The model call** (`audit`): `ai_audit.COMMAND` and `SYSTEM_PROMPT` as section 2.4 gives
them, less any flag step 0 took out.

## 6. Lines a person reads

### 6.1 The status, a test run, the dashboard

```
40 rules. 40 pass their tests. The audit found 34 of 40 rules strong (85%): 34 strong, 4 weak, 2 spot-checked.
signed/9.9.9: it names a commit that holds no evidence package for 9.9.9, so it is not a sign-off. Delete it: git tag -d signed/9.9.9.
signed/2.1.0: no sign-off of 2.1.0 counts: the commit that added it is not signed. Restore the files as they were signed, or sign this code: purlin:sign --version <version>.
Started 1 slow test in the dotnet suite: its command gives Purlin no way to leave one test out.
```

A strong cell's reasons:

```
The spot tests found nothing. No bug was planted: no bug is planted for an anchor's rule.
code changed since a1b2c3d
the last audit found it strong on 2026-09-13
no audit has read this rule
```

The dashboard's `Audit` panel: `Spot-checked.`, `Out of date:`, `No audit has read this rule
yet.`; the strong row's words `SPOT-CHECKED` and `OUT OF DATE`.

### 6.2 The sign-off

```
No sign-off: these results were not taken on this version of the code, 1cf829e: feat on macOS. Run purlin:test --all --commit, then purlin:sign.
No sign-off: .purlin/evidence/package/2.1.0.json does not match its fingerprint: <why>. Restore it as it was signed, or name a new version: purlin:sign --version <version>.
No tag: git could not write signed/2.1.0: <git's reason>. Fix that, then run purlin:sign again to write it.
signed/2.1.0 is not written yet: jane@acme.com signed 2.1.0 at e0deb2e. Run purlin:sign to write the tag.
  The audit: 34 strong, 4 weak, 2 spot-checked.
```

The first is today's line: a kept slow result reaches it. The fourth is what `--show` prints
where the tag is missing. After the second run: `Tagged signed/2.1.0 at e0deb2e.`, then
`Push the branch and the tag: git push origin main signed/2.1.0`, both today's lines.

### 6.3 The audit

```
The audit reads 12 rules: 12 model calls.
The audit reads 1 rule: 1 model call.
login RULE-2   spot-checked
  The spot tests found nothing. No bug was planted: the model found no change that would break PROOF-2: the proof names no value the code computes.
login RULE-3   weak
  PROOF-3: the test still passes when src/auth.py:12 reads "return 200"
  No bug was planted: PROOF-4 needs Windows, and this machine is macOS.
tests/test_login.py::test_renamed_away: its source was not found, so the spot tests did not read it.
The model could not be reached: claude gave no answer. 1 rule is spot-checked alone. Run purlin:audit again.
The model could not be reached: claude is not on PATH. 2 rules are spot-checked alone. Run purlin:audit again.
The audit stopped: src/age.py changed while the audit ran. Nothing in the project was written by the audit.
The model was asked 12 times for 12 rules: $0.84 in all, $0.07 a rule.
The audit found 34 of 40 rules strong (85%): 34 strong, 4 weak, 2 spot-checked.
```

Under a `strong` or `weak` rule each `no_bug` sentence is printed alone, indented two spaces;
under a `spot-checked` rule the sentences follow `The spot tests found nothing. ` on one line.

### 6.4 Anchors and the upgrade

```
no_eval: not added. --name takes letters, digits and _ alone. Run purlin:anchor add <source> --path <path> --name no_eval.
no_eval: not added. specs/_anchors/no_eval.md already holds an anchor of that name. Run purlin:anchor sync no_eval to update it, or add it under another --name.
```

### 6.5 `skills/audit/SKILL.md`

The opening paragraph's second sentence: `The audit runs the marked tests, then for each rule
that passes: the heuristic spot tests, which read each test as text; one model call, which
writes a small bug for each proof and explains the tests; and each bug planted in a copy of the
project, to see whether the proof's own test catches it.`

Step 1, the three steps and the verdict:

```
1. The heuristic spot tests, with no model.
2. One model call for the rule: a bug for each proof, and the model's reading.
3. Each bug planted in a copy of the project, and that proof's own test run.

A rule reads:

- `weak` when a spot test fires on one of its tests or a planted bug survived;
- `strong` when none did and a planted bug was caught by its proof's test;
- `spot-checked` when none did and no bug was planted and caught. The audit says why.

Before the first call the audit prints how many model calls it will make, one for each rule
it reads. After the last it prints what the run cost.
```

Step 2's block, with no dollar figure:

```
The audit reads 12 rules: 12 model calls.
login RULE-2   weak
  tests/test_login.py::test_wrong_password: the test checks nothing.
  PROOF-2: the test still passes when src/auth.py:12 reads "return 200"
login RULE-3   spot-checked
  The spot tests found nothing. No bug was planted: PROOF-3 needs Windows, and this machine is macOS.
The model was asked <n> times for <n> rules: $<total> in all, $<per rule> a rule.
The audit found 4 of 6 rules strong (66%): 4 strong, 1 weak, 1 spot-checked.
```

Its list:

- `` A line `No bug was planted: <why>.` is not a finding and does not make the rule weak. A rule with no finding and no caught bug reads `spot-checked`. ``
- `` `The model could not be reached: <why>. <n> rules are spot-checked alone. Run purlin:audit again.` means `claude` gave no usable answer. A rule a spot test fired on is still written `weak`. Any other rule is written `spot-checked`, and the next `purlin:audit` reads it again. ``
- `` `The audit stopped: <file> changed while the audit ran. Nothing in the project was written by the audit.` means a file changed under the run: leave the project alone while the audit runs, then run it again. ``
- `` `<file>::<test>: its source was not found, so the spot tests did not read it.` means the evidence names a test the file no longer holds: run `purlin:test`, then `purlin:audit`. ``

Step 3 gains: `` A rule reads `spot-checked`: say why, in the audit's own sentence. Where the reason is another system or an anchor's rule, there is nothing to run. ``

### 6.6 `docs/audit.md`

Step 3, whole: `` **3. Run that proof's test.** The test fails: the bug was caught. The test still passes: the rule is `weak`, and you see the bug it missed: `` then the block as now, then:

```
A rule reads `strong` when the spot tests found nothing and a planted bug was caught. Where
no bug could be planted, the rule reads `spot-checked`, and the audit says why:

The spot tests found nothing. No bug was planted: PROOF-3 needs Windows, and this machine is macOS.
```

"What you can count on", the third bullet: `` **`strong` means a bug was caught.** If the AI cannot be reached, a rule the spot tests flag is still `weak`. Every other rule reads `spot-checked`, with the reason, and the next `purlin:audit` reads it again. ``
It gains: `` **A result goes out of date.** When a rule, its proof, its test or the code it covers changes, the rule reads `out of date`, with its last result and date, until the audit reads it again. `` and `` **The AI is given no tools.** It is started with no tools, no plugins and none of your settings, in an empty folder. It can read and change nothing. ``

"What it does not do", the third bullet: `` It plants no bug for an anchor's rule, so an anchor's rule reads `spot-checked`, never `strong`. `` It gains: `` It plants no bug for a proof tagged for another system. The test cannot show it on this machine. `` and `` A test that is skipped, cannot be collected or runs past its limit with the bug in place decides nothing. Only a test that ran and failed caught the bug. ``

The table's last row: `` | **Spot tests, then one planted bug per proof** | **Free, then one AI call per changed rule and one test run per changed proof** | **Objective, aimed at what the proof says** | `` Under it: `The audit prints how many AI calls it will make before it starts, and what the run cost when it ends.`

The share line reads `The audit found 42 of 50 rules strong (84%): 42 strong, 8 weak.`

### 6.7 The other pages, skills and references

- `docs/how-purlin-works.md`, the question becomes `` **What do `strong`, `weak`, `spot-checked` and `not audited` mean?** `` with five bullets: `` `strong`: the spot tests found nothing, and a planted bug was caught by the proof's test. ``; `` `weak`: a spot test fired on one of the rule's tests, or a planted bug was not caught. The rule is left to do as `to strengthen`, with `purlin:build`. ``; `` `spot-checked`: the spot tests found nothing, and no bug was planted and caught. The audit says why. ``; `` `not audited`: no audit has read the rule. `purlin:audit` reads it when you run it. ``; `` `out of date`: the rule, its proof, its test or its code changed since the audit read it. Its last result stays on screen. `` The `waiting` bullet stays.
- `docs/running-and-evidence.md`, lines 312 to 326: step 2 reads `**One model call for the rule**: a small bug for each proof, and the model's reading.`; step 3 `**Each bug planted** in a copy of the project, and that proof's own test run. A test that still passes did not catch the bug.`; then the three bullets of 6.5 and `Where the model cannot be reached, the audit prints one line, such as` with the second `could not be reached` line of 6.3. Lines 342, 343 and 350 take the block and the share line of 6.5. Line 359 quotes the `changed while the audit ran` line. The slow section gains: `A plain run keeps an earlier slow result while nothing its spec covers changed. The status counts it. The sign-off does not: run purlin:test --all --commit before purlin:sign.`
- `docs/sign-off.md`: the refusal table gains the rows `a slow result kept from an earlier run`, with `purlin:test --all --commit`, and `the committed package was changed after it was signed`. "What is recorded" gains: `The status reads signed only where the tag names a commit that holds the package and a sign-off of it counts. A tag written by hand reads not signed, with one warning.` and `Changing a test command in .purlin/config.json ends the results, as changing the code does. Changing version alone does not.`
- `docs/specs-and-anchors.md`, the slow section, after "Nothing to remember": `A slow result a plain run kept is marked kept in the evidence, with the commit, the time, the machine and the person of the run that took it.`
- `docs/dashboard.md`: the strong cell's words gain `spot-checked` and `out of date`.
- `references/evidence_and_signoff.md`: line 41's list reads `` `strong`, `weak`, `spot-checked`, `out of date`, `not audited`, `checked at sign-off` for a hand check, `no proof`, or `waiting` ``; lines 50 and 59 take the sentence of 6.1; "When a sign-off counts" gains the two sentences of `docs/sign-off.md` and `A sign-off is read as HEAD holds it. A sign-off file changed and not committed does not count.`; the results section gains the slow sentence and the `tests` setting sentence.
- `references/glossary.md`: the `strong` row reads `` | strong | passed, the spot tests found nothing and a planted bug was caught; nothing waits on it | `strong`, `weak`, `spot-checked`, `out of date`, `waiting`, `not audited`, `checked at sign-off`, `no proof` | ``; new entries `` **spot-checked**: the spot tests found nothing and no bug was planted and caught; the audit entry says why. `` and `` **kept**: a slow proof's result a plain run carried over from an earlier run; the status counts it and the sign-off does not. ``; line 49 takes the sentence of 6.1.
- `references/spec_quality_guide.md`, the cell table: the `not audited` row's cause reads `No audit has read this rule.`; two rows are added: `` | strong | `spot-checked` | The spot tests found nothing and no bug was planted and caught. The reason follows the word. | Fix what the reason names, where there is something to fix, then `purlin:audit`. | `` and `` | strong | `out of date` | The rule, its proof, its test or its code changed since the audit read it. | `purlin:audit`, when you want one. | ``
- `references/purlin_commands.md`: the `purlin:audit` row reads `Run the tests, the heuristic spot tests, one model call per rule and one planted bug per proof, then write what it found`; the exit code row quotes `changed while the audit ran`.
- `skills/sign/SKILL.md`: the overview example line as 6.2; Step 2's refusals gain the kept slow result and the package that does not match; Step 6 gains `Where git could not write the tag, the script says so and exits 1. Fix what git named and run purlin:sign again: it writes the tag on the signed commit and signs nothing twice.`
- `skills/status/SKILL.md` line 62, `agents/purlin.md` line 76: the sentence of 6.1.
- `skills/test/SKILL.md`, the slow step: the sentence of `docs/running-and-evidence.md`.
- `CLAUDE.md`, "Tool folder separation", last sentence: `` `purlin_agent` RULE-23 checks the `dev/` half of this line across those files; the review of each change holds the `specs/` half. `` Its reference table's row `references/hard_gates.md` names a file the tree does not hold; the row's home is `references/evidence_and_signoff.md`.
- `RELEASE_NOTES.md`, 0.10.0: the quoted share lines take the new form, and "What is new" gains:

```
- **The audit says how far it got.** `strong`: the spot tests found nothing and a planted bug
  was caught. `weak`: a spot test fired or a bug survived. `spot-checked`: the spot tests found
  nothing and no bug was planted and caught, with the reason. A result reads `out of date` once
  the rule, its proof, its test or its code changes.
- **One model call per rule**, started with no tools, no plugins and none of your settings.
- **The status reads `signed` only where a sign-off counts.** A tag written by hand, an edited
  package and a sign-off changed after its commit each read `not signed`.
- **A slow result must be taken on the version being signed.** A plain run marks an earlier
  slow pass `kept`; `purlin:sign` asks for `purlin:test --all --commit`.
- **A changed test command ends the results**, as a changed file does.
```

### 6.8 `references/review_criteria.md` (lane `audit`), and the deck

**The owner's official text, "Heuristic spot tests": one sentence changes.**

Check 6, before: `` **Does not flag** a proof that names no value in backticks; the same number written another way (`90` and `90.0`); a value the test reads from a data file its own file names. ``

Check 6, after: `` **Does not flag** a proof that names no value in backticks; an empty pair of backticks, which marks an empty value and names nothing to look for; the same number written another way (`90` and `90.0`); a value the test reads from a data file its own file names. ``

Check 4 is unchanged (section 4.4). No other sentence of that section changes.

**Outside that section**, the same file:

- "The verdict", whole: `` A rule reads `weak` when a spot test fires on one of its tests or a planted bug survived. It reads `strong` when none did and a planted bug was caught by its proof's test. It reads `spot-checked` when none did and no bug was planted and caught; the entry then says why. Nothing else sets it: the model's reading never changes it. `` and `` When the model cannot be reached for a rule, the spot tests still report what they find as `weak`, and a rule that passed them is written `spot-checked` and read again by the next audit. ``
- "The planted bug": the answer's shape is K3's; `**Caught.** A test of the proof ran and failed with the change in place. The test noticed.`; `**Not run.** The test was skipped, could not be collected or ran past its limit with the change in place. That decides nothing: the bug was neither caught nor missed.`; `**Not made.**` gains `or a file that holds one of the proof's tests, or the proof's test does not pass in the copy before any change`; the last paragraph reads `No bug is planted for an anchor's proof, a @manual proof or a proof tagged for a system this machine is not. When a file of the project changes while the audit runs, the audit stops and writes nothing.`
- "What the model is sent": `The model is asked once for each rule: this file, then the rule's text, its proofs, the source of each test, and under Findings: each finding of the spot tests, or none; then the proofs to plant a bug for and the text of each file the feature covers. It answers with one part for each of those proofs and then its reading.` "The call" gives the command of section 2.4 and `The model is given no tools and is started in an empty folder, so it can read and change nothing.`
- "Anchors": `No bug is planted for an anchor, so its rule reads spot-checked where the spot tests find nothing.`
- "What the audit reports": the cost line with no figure, `The model was asked <n> times for <n> rules: $<total> in all, $<per rule> a rule.`, and the share line of 6.3.

**The deck, `dev/plans/deck/build_deck.py`** (lane `words`; the coordinator publishes it):

- `audit`, row 3: `('Run that proof\'s test', 'The test fails and the spot tests found nothing: the rule is %s. The test still passes: the rule is %s, and you see the bug it missed. No bug could be planted: the rule is %s, and you see why.' % (m('strong'), m('weak'), m('spot-checked')))`
- `why`, the audit row: `('AI writes code &amp; tests fast. Are they any good?', 'The audit plants a small bug for each proof and runs its test. Caught: strong. Missed: weak. No bug planted: spot-checked.')`
- `audit`, the notes: `Only proofs whose test or code changed since the last audit are tried again` stays; `One AI call per rule, with no tools: it can read and change nothing.` is added.

### 6.9 If the planted bug still costs over $0.10 a rule

Used only if the second measurement says so. `<x>` is the measured mean, to the cent.

- The audit's first line, before `The audit reads ...`: `The planted bug is experimental in 0.10.0: it cost $<x> a rule when it was measured, over the $0.10 set for it.`
- `skills/audit/SKILL.md`, after the opening paragraph, and `docs/audit.md`, under "How it works": `` **The planted bug is experimental in 0.10.0.** Measured on 12 rules, it cost $<x> a rule, over the $0.10 set for it. The spot tests are not experimental and cost nothing. The audit prints what each run cost. ``

The first is one constant in `audit_run.py`, `EXPERIMENTAL`, printed where it is not empty; the
coordinator sets it. It gets no rule: a rule would only pin its wording.

## 7. Formats

| File | Now | After | Why |
|---|---|---|---|
| `evidence_format.md` | 9 | **11** | 10 in the base commit: the audit entry gains `code_hash` and `no_bug`, `verdict` gains `spot-checked`, a break's `result` gains `not run`, an entry is current while four hashes match, and the paragraph on the could-not-run file goes. 11 in lane `evidence`: a proof entry's optional `kept`, and the `tests` part covering the `tests` setting. `schema` stays `purlin-evidence/2` |
| `package_format.md` | 10 | **11** | `audit` carries five counts; a rule's `audit` gains `no_bug` and `out_of_date`; `statuses.strong.word` may read `spot-checked` or `out of date`; `same_code` is false for a kept result. `schema` stays `purlin-package/4` |
| `signature_format.md` | 15 | **16** | `shown.overview.audit` carries five counts; a second signer whose slug is taken gets `<slug>-2.json` |
| `marker_format.md` | 4 | 4 | it already says a marker inside a string or a here document is not one |
| `spec_format.md`, `anchor_format.md` | 23, 12 | the same | not touched |

Each is changed in the same commit as its code. The dashboard's data goes from schema 14 to 15:
`summary.audit` and each rule's `audit` change shape.

## 8. Integration, local, one agent

1. Merge `evidence`, `audit`, `signoff`, `surfaces`, `setup`, `words` into `main`, in that
   order, `--no-ff`.
2. `bash dev/run_tests.sh` to 0 failed. Expected, if nothing else moved: about 881 passed and 9
   skipped (819, less the 2 deleted tests, plus 64).
3. `python3 scripts/run/purlin_run.py --test --all --commit` to the clean state: 39 specs, 429
   rules, 885 proofs, 885 test comments tied, no rule `failed`, `partial` or `no test`, no test
   comment to correct. Every section is rewritten once, since each feature's `tests` hash now
   covers the `tests` setting.
4. Appendix A's script of `dev/plans/d115-plan.md` over every `dev/test_*`: `0 gone`, and the
   reworded ones only the five slow proofs it always names.
5. The reproduction of section 4.1's second row, once, by hand in a scratch project: with real
   runs, `sign.py --show` now exits 1 and names `purlin:test --all --commit`.
6. **The audit, measured again**, by the coordinator, with the real `claude`: 12 rules, 4 each
   of `sample_intake` in the measurement's sample project, `renumber` and `plain_checks`, with
   the pass-through that saves each call. Expected: 12 calls, about $0.84 in all, $0.04 to
   $0.11 a rule, no call over one turn, no tool used. The report goes to
   `dev/plans/d121-reports/audit-measure-2.md`. Over a mean of $0.10: section 6.9, in one
   commit.
7. The greps, each empty:
   ```
   git grep -n -E 'could_not_run|EARLIER_WEAK|key::|ask_for_bug|bug_prompt|code_changed\(' -- scripts dev ':!dev/plans'
   git grep -n -E 'stays? not audited|while a bug was planted|\$0\.16 a rule' -- . ':!dev/plans' ':!.purlin'
   git grep -n -E 'rules strong \([0-9]+%\)\.' -- . ':!dev/plans' ':!.purlin'
   ```
8. The dashboard: `python3 dev/build_report.py`, then looked at with Playwright from the
   `.venv`, both themes, at 390, 768, 1024, 1280 and 1500 pixels, on the regulated sample with
   a `spot-checked` rule and one out of date; no value wraps and `purlin_report` PROOF-66 and
   PROOF-104 pass. The two doc screenshots are retaken with `dev/capture_doc_screenshots.py`.
9. Steps 2 and 3 again.
10. The real Windows run, once: `python3 dev/windows_run.py`. It proves the 20 proofs tagged
    `@env(windows)`, `ai_audit` PROOF-82 with its new arguments among them.
11. `dev/plans/handoff.md` gains a top section: what was built, the numbers of steps 2, 3, 6
    and 10, the formats, and what is left for the owner. `main` stays local: no push, no tag,
    no sign-off.

## 9. Questions for the owner

One. No lane waits on it: the plan builds the recommended answer.

1. **When a rule has several proofs, how many must have a bug caught for the rule to read
   `strong`?** A rule often has two or three proofs, each with its own test. The audit plants
   one bug per proof. Sometimes a bug is caught for one proof and none can be planted for
   another, for example a proof tagged for Windows when the audit runs on a Mac.
   - **A. One caught bug is enough** (recommended, and how decision 121's words read: "a
     planted bug was caught"). The rule reads `strong`, and under it each proof with no caught
     bug is named with its reason. Consequence: a rule can read `strong` while one of its tests
     was never challenged; the line beside it says which.
   - **B. Every proof with a test must have its bug caught.** Otherwise the rule reads
     `spot-checked`. Consequence: the word is stricter, and a rule with a proof tagged for
     another system can never read `strong` on this machine. In this repository that is 20
     proofs. The share a team holds against a target such as 80% drops by those rules.
   - If B: one condition changes in `audit_run.run`, `ai_audit` RULE-33 reads `else strong
     when every proof it plants a bug for had one caught`, and `ai_audit` PROOF-120 reads
     `spot-checked`.

## 10. Calls this plan makes

- A kept slow result is refused at the sign-off whatever commit it names (section 2.1).
- An entry out of date is its own count, `out of date`, in the summary line, and is not counted
  among `not audited`.
- A rule out of date is left nothing to strengthen, even where its last result was `weak`.
- The share's line keeps its opening, `The audit found <s> of <n> rules strong (<p>%)`, and the
  counts follow it.
- At the sign-off any uncommitted change to `.purlin/config.json` is a changed file; only a
  changed `tests` setting ends a result.
- The audit's stop reads `changed while the audit ran`, since the check now spans the model
  calls as well as the bugs. Decision 120's `while a bug was planted` is reworded again.
- The reading is written in the same reply as the bugs, so it no longer explains a bug that
  survived.
- A reply that leaves a proof out is recorded for that proof and not asked again until its
  test or code changes, as an answer that names no change is today.
- `signatures` RULE-102 goes to 8 proofs. Its five causes were bundled by the weight pass; the
  new refusals go under RULE-132 to keep each new rule at one to three proofs.
- `facts.py` is owned by lane `signoff`, though `states` and `summary` list it in their scope.
- The seams are code in the base commit, not stubs: six lanes then run with one waiting test.

Left out, and why:

- **Spot test 4, through a second function**: no simple, exact rule (section 4.4).
- **A guard for a surviving bug that does not touch the proof's case**: 1 in 93, inside the
  limit of 1 in 5. Asking the model to name the input would lengthen every reply.
- **A cheaper model for the reading**: the reading is no longer a call of its own.
- **`write_could_not_run`**: deleted (answer 4b).
- **The `key::` signing key**: deleted (answer 4c). No doc, skill, reference or spec names it.

## 11. Where this plan depends on decision 120

Decision 120's four lanes are merged and integrated on `main` (`c01ad61e9`); no lane branch
holds a commit `main` lacks. What is relied on or changed again:

1. **`signnote`.** `signatures` RULE-129 and PROOF-249 to 251 take the numbers 129 and 249 to
   251, so the new ones start at 130 and 252. `sign.last_notes` calls `payload.hand_notes`
   (renamed at integration); the base commit moves that function to `signatures.py`. The
   review's item 10 is this lane's work and is not built again.
2. **`leftovers`.** `targeted_break.STOPPED`, `planted_bug` RULE-6 and PROOF-7, and the quote
   in `skills/audit/SKILL.md` and `docs/running-and-evidence.md`, all reworded to `while a bug
   was planted`, are reworded again. The payload's seventeen top-level keys stay seventeen; its
   schema goes from 14 to 15. `config_engine.UPGRADE_KEYS` is not touched.
3. **`dark`.** `purlin_report` RULE-75 and PROOF-66 measure every text in both themes. The new
   words `SPOT-CHECKED` (the neutral tone) and `OUT OF DATE` (the warn tone) use tones that
   lane already lightened; lane `surfaces` runs both proofs.
4. **`prose`.** The paragraphs it made short in `docs/running-and-evidence.md`,
   `docs/how-purlin-works.md` and `docs/sign-off.md` are the ones section 6.7 quotes by line;
   the line numbers are `main`'s at `c01ad61e9`.
5. **The numbers.** 411 rules and 823 proofs are counted after decision 120; the review counted
   410 and 820 before `signnote` landed.
