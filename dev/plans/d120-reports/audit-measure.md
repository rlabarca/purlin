# The planted-bug audit of Purlin 0.10.0, measured (decision 116)

Measured 2026-10-01 on macOS, on a clone of `main` at `cb9431982`, with the real `claude` program logged in as the owner.

## Verdict

| Limit | Measured | Result |
|---|---|---|
| At most $0.10 per rule | $0.74 per rule (46 rules, $34.08); $0.80 on Purlin's own 38 rules, $0.45 on the sample project's 8 | **Over, by 7 times.** Every one of the 46 rules cost more than $0.10; the cheapest was $0.35 |
| At most 1 in 5 planted bugs irrelevant | 1 of 93 irrelevant (1.1%); 1 of 81 on Purlin's own, 0 of 12 on the sample project | **Within** |

By decision 116 the check is over one limit, so it is fixed or marked experimental before release. The planted bugs themselves are good. The cost is not, and it comes from how the model is called, not from what it is asked.

## What was measured

- **Purlin's own tests:** 5 features audited one at a time with `purlin_run.py --audit --feature <name>`: `specs` (6 rules, 12 proofs), `renumber` (9, 12), `summary` (8, 18), `config_engine` (7, 19), `plain_checks` (8, 20). 38 rules, 81 proofs.
- **One sample project:** `labconnect-intake`, a Python sample-intake feature with pytest, 8 rules and 12 proofs, set up with `scripts/init/scaffold.py`, tested with `purlin_run.py --test`, committed, then audited. 3 of its 12 tests were written weak on purpose.
- **Total:** 46 rules, 93 proofs, 93 planted bugs, 139 model calls.

What was not measured: any other language than Python tests, any feature with a large `> Scope:`, the `--all` path, a second audit of an unchanged project (the kept results), and Windows. 46 rules on one machine is a small sample. The irrelevant share of 1 in 93 has a wide margin; it supports "well under 1 in 5" and nothing finer.

### How the real model was confirmed

The audit runs `claude` from the `purlin_run.py` process, where the fake that `dev/conftest.py` installs is not on the path: that fake is put on the path inside each pytest process only. For this measurement a pass-through program stood first on the path, handed each call unchanged to `/Users/richlabarca/.local/bin/claude` and saved its prompt and JSON answer. All 139 answers name `claude-opus-5-5` in `modelUsage`, and all 46 audit entries record `model: claude-opus-5-5`. The tests the audit ran in each copy are the project's own and use the fake where they call a model.

## Cost

The audit records dollars: `claude -p --output-format json` returns `total_cost_usd`, which the audit sums into `.purlin/runtime/audit_run.json` and its printed line. No conversion was needed. The program marks the figure `costBasis: list`, the list price of `claude-opus-5-5`. The saved answers of the pass-through agree with `audit_run.json` call for call (139 and 139).

| | Purlin's own | Sample project | All |
|---|---|---|---|
| Rules | 38 | 8 | 46 |
| Proofs, one planted bug each | 81 | 12 | 93 |
| Model calls | 119 | 20 | 139 |
| Total | $30.45 | $3.63 | $34.08 |
| Per rule: mean | $0.80 | $0.45 | $0.74 |
| Per rule: median | $0.79 | $0.45 | $0.69 |
| Per rule: highest | $1.19 | $0.55 | $1.19 |
| Per rule: lowest | $0.45 | $0.35 | $0.35 |
| Per proof (the bug call alone): mean | $0.26 | $0.16 | $0.25 |
| Per proof: median | $0.27 | $0.16 | $0.25 |
| Per proof: highest | $0.33 | $0.19 | $0.33 |
| Per reading call (one a rule): mean | $0.24 | $0.21 | $0.24 |

One more call, $0.20, was made before the runs to test the pass-through. Spent in all: $34.28 at list price, against the owner's usage.

**Calls per rule:** one per proof with a test, for the bug, plus one for the reading. 139 calls for 46 rules, 3.0 a rule.

**Why it costs this much.** Each call is a new `claude -p` session. A session with the prompt `Reply with the single word: ok`, run in the clone, cost $0.20: it wrote 24,823 tokens to the one-hour cache and read 10,738, before any audit text. That is the program's own instructions, the tool list, the installed plugins and skills, the MCP servers and the project's `CLAUDE.md`. The audit's calls wrote 18,613 to 38,135 tokens to the cache each (median 28,918), and no later call reads them back, since each prompt differs. Output was small, 48 to 1,367 tokens. So about four fifths of every call is the session's fixed load on this machine, paid again 139 times. The floor on this machine is 2 calls a rule at $0.20, $0.40, with nothing asked.

The figure depends on the machine: the owner's has many MCP servers and plugins. A person with a bare `claude` would pay less a call; it was not measured here.

## Relevance of the planted bugs

Each bug was judged against its proof by reading both, and the code around the change where the answer was not plain.

| | Purlin's own | Sample project | All |
|---|---|---|---|
| Planted | 81 | 12 | 93 |
| Not made | 0 | 0 | 0 |
| Relevant | 80 | 12 | 92 |
| Irrelevant | 1 | 0 | 1 |
| Unclear | 0 | 0 | 0 |
| Caught | 79 | 10 | 89 |
| Survived | 2 | 2 | 4 |

**The one irrelevant bug:** `plain_checks` PROOF-14, "`test_bad_zone` calls `age` inside a `try` whose `except ValueError as e:` holds `assert "zone" in str(e)`; nothing is found".

```
scripts/review/plain_checks.py:545
before:  if all(isinstance(stmt, ast.Pass) or
after:   if any(isinstance(stmt, ast.Pass) or
```

The handler in the proof holds one statement, an `assert`. `all` and `any` over that one statement are both false, so nothing is found either way and the proof still holds. The bug changes handlers of several statements, which the proof does not speak of. It survived, and `plain_checks` RULE-3 reads `weak` because of it.

No bug was a syntax error, a no-op on the file, or outside the feature's scope. 15 of the 93 change only the wording or spacing of a message the proof quotes exactly (for example `the test checks nothing.` to `the test asserts nothing.`). They are counted relevant, since the proof names the text, but they test little.

## Sound tests found weak, weak tests missed

**Sample project, where the truth is known** (9 sound tests, 3 weak):

| Test | Written | Audit | How |
|---|---|---|---|
| PROOF-11, no assertion | weak | found weak | spot test "the test checks nothing", and the bug survived |
| PROOF-7, checks 71 hours where the proof says exactly 72 | weak | found weak | the bug `>` to `>=` survived; no spot test fired |
| PROOF-5, expects `age_hours(...)`, the code under test, not `25` | weak | **missed**: RULE-3 reads `strong` | spot test 4 looks for the same function on both sides, and here one side is `intake` and the other `age_hours`; the bug (`+ 1` in `intake`) was caught by the disagreement. The model's reading named the weakness, and the reading sets no verdict |
| PROOF-1, sound | sound | **found weak**, wrongly | spot test 6, see below |
| the other 8 | sound | strong | |

Weak tests missed: 1 of 3. Sound tests found weak: 1 of 9.

**Purlin's own tests, where the truth is not known:** 2 of 81 proofs had a surviving bug, and both are false alarms on a sound test:

- `plain_checks` PROOF-14: the irrelevant bug above.
- `config_engine` PROOF-38, tagged `@env(windows)`: the bug drops `newline='\n'` from the write, which adds a carriage return on Windows only. The audit planted it and ran the test on macOS, where the change does nothing, and wrote RULE-8 `weak`.

So on Purlin's own tests every `weak` the planted bug produced was wrong (2 of 2), and at the rule level 3 of the 5 `weak` verdicts in the whole sample were wrong (`sample_intake` RULE-1, `config_engine` RULE-8, `plain_checks` RULE-3). Whether any of the 79 caught tests is in fact weak was not checked.

**One false `caught`:** `config_engine` PROOF-39, also `@env(windows)`. Its test carries `skipif(os.name != 'nt')`. In the copy it was skipped, and the audit counts anything but a pass as `caught`. The bug was never run against a test.

### False alarms from the spot tests

1 in 93 tests read; none on Purlin's own 81.

- `sample_intake` PROOF-1: `tests/test_intake.py::test_an_empty_barcode_is_refused: the proof expects (empty) is handed in; it is refused with and the test never checks it.` The proof writes the empty barcode as two backticks with nothing between them. Spot test 6 paired the second of them with the next backtick and took the prose between as the expected value. The test checks exactly what the proof says. The model's reading said the finding does not hold; the rule still reads `weak`.

## Wall time

| | Purlin's own | Sample project |
|---|---|---|
| Whole run, tests included | 873 s for 38 rules: 23.0 s a rule | 80 s for 8 rules: 10.0 s a rule |
| Model time per rule, as the audit records it | mean 22 s, median 22 s, highest 36 s | mean 14 s, median 15 s, highest 18 s |
| One bug call | mean 5.5 s, highest 13.2 s | mean 4.9 s, highest 6.9 s |

Per feature: `specs` 116 s, `renumber` 215 s, `summary` 216 s, `config_engine` 153 s, `plain_checks` 173 s, `sample_intake` 80 s. The bugs are planted one at a time; only the readings run four at once. At 23 s a rule, Purlin's 402 passing rules would take about 2.5 hours and, at $0.80 a rule, about $320.

## What failed, hung or changed a file

- Nothing failed or hung. All 6 runs exited 0; no call timed out or exited with an error; no bug read `not made`.
- `git status` after each run listed only `.purlin/evidence/local/<feature>.json`, which the audit is meant to write. No source, test or spec file changed in either project. No `purlin-break-*` folder was left in the temporary folder.
- One of the 139 calls took 2 turns (the reading of `plain_checks` RULE-3): the model used a tool before answering. `claude -p` is started in the project with its tools on, and the audit sets no limit on turns or tools. Nothing was changed, but nothing in the call prevents an attempt.
- The run's own summary prints `Left to do: 1 feature whose results are not committed` after an audit, as designed.

## What to fix first

1. **The call, for cost.** Start the model without the session's fixed load: no tools, no MCP servers, no plugins or skills, no project instructions, and a short system prompt of the audit's own; or call the API directly where a key is set. The audit's own text is about 7,000 tokens for a bug and 5,000 for a reading on Purlin's files; at the same list price that is a few cents a call. Asking for all of a rule's bugs and its reading in one call would cut the calls from 3.0 a rule to 1. Either alone may not reach $0.10 a rule on a large scope; both together should, and this needs measuring again after the change. A cheaper model for the reading, which decides nothing, is the third lever.
2. **Proofs tagged for another system.** Plant no bug for a proof whose `@env` is not this machine's, and never count a skipped test as `caught`. This produced 1 false `weak` and 1 false `caught` in 81.
3. **Spot test 6 and an empty pair of backticks.** One false `weak` in the sample project.
4. **A surviving bug that does not touch the proof's case.** One in 93 here. A guard to try: ask the model, in the same call, to name the input from the proof under which the change gives a different result, and plant nothing where it cannot.
5. **Spot test 4 misses an expected value computed through a second entry point of the code under test.** 1 weak test of 3 missed. The check is narrow by design; the reading saw it, and the reading sets no verdict.

## Experimental or not

Yes: mark the planted bug experimental for 0.10.0 unless item 1 is done and measured again before release. The limit is missed by 7 times on every rule measured, and the printed example in the skill (`$0.16 a rule`) is 4 to 5 times under what this machine paid. The bugs themselves pass their limit with room, so the mark is about cost and the two `@env` errors, not about whether the idea works.

## Where the records are

All under `/private/tmp/claude-501/-Users-richlabarca-LocalCode-purlin/0b911df6-a4da-4d86-9e09-dc4ed8c6bce2/scratchpad/audit-measure/`:

- `logs/<feature>.log`, `logs/<feature>.audit_run.json`, `logs/<feature>.gitstatus.txt`: each run's output, cost file and `git status`.
- `calls/<feature>/*.json`: every model call's prompt, answer, tokens, cost and time.
- `purlin/.purlin/evidence/local/<feature>.json` and `labconnect-intake/.purlin/evidence/local/sample_intake.json`: the audit entries.
- `labconnect-intake/`: the sample project.

## Appendix A: every rule audited

| Feature | Rule | Proofs | Model calls | Cost | Model seconds | Verdict | Spot-test findings |
|---|---|---|---|---|---|---|---|
| specs | RULE-9 | 2 | 3 | $0.757 | 18 | strong | 0 |
| specs | RULE-10 | 1 | 2 | $0.506 | 11 | strong | 0 |
| specs | RULE-11 | 3 | 4 | $1.057 | 22 | strong | 0 |
| specs | RULE-17 | 2 | 3 | $0.768 | 20 | strong | 0 |
| specs | RULE-20 | 1 | 2 | $0.509 | 11 | strong | 0 |
| specs | RULE-22 | 3 | 4 | $1.015 | 31 | strong | 0 |
| renumber | RULE-1 | 1 | 2 | $0.475 | 12 | strong | 0 |
| renumber | RULE-2 | 1 | 2 | $0.462 | 18 | strong | 0 |
| renumber | RULE-3 | 2 | 3 | $0.685 | 17 | strong | 0 |
| renumber | RULE-4 | 2 | 3 | $0.700 | 18 | strong | 0 |
| renumber | RULE-5 | 1 | 2 | $0.471 | 13 | strong | 0 |
| renumber | RULE-6 | 1 | 2 | $0.460 | 14 | strong | 0 |
| renumber | RULE-7 | 1 | 2 | $0.451 | 12 | strong | 0 |
| renumber | RULE-8 | 1 | 2 | $0.478 | 20 | strong | 0 |
| renumber | RULE-9 | 2 | 3 | $0.697 | 30 | strong | 0 |
| summary | RULE-8 | 3 | 4 | $1.091 | 24 | strong | 0 |
| summary | RULE-18 | 1 | 2 | $0.500 | 16 | strong | 0 |
| summary | RULE-19 | 2 | 3 | $0.813 | 22 | strong | 0 |
| summary | RULE-20 | 3 | 4 | $1.080 | 31 | strong | 0 |
| summary | RULE-21 | 1 | 2 | $0.515 | 12 | strong | 0 |
| summary | RULE-22 | 3 | 4 | $1.096 | 34 | strong | 0 |
| summary | RULE-23 | 3 | 4 | $1.130 | 36 | strong | 0 |
| summary | RULE-24 | 2 | 3 | $0.848 | 29 | strong | 0 |
| config_engine | RULE-4 | 2 | 3 | $0.647 | 16 | strong | 0 |
| config_engine | RULE-8 | 3 | 4 | $0.885 | 30 | weak | 0 |
| config_engine | RULE-10 | 3 | 4 | $0.900 | 23 | strong | 0 |
| config_engine | RULE-14 | 3 | 4 | $0.896 | 29 | strong | 0 |
| config_engine | RULE-19 | 3 | 4 | $0.886 | 23 | strong | 0 |
| config_engine | RULE-20 | 2 | 3 | $0.672 | 16 | strong | 0 |
| config_engine | RULE-21 | 3 | 4 | $0.886 | 33 | strong | 0 |
| plain_checks | RULE-1 | 3 | 4 | $1.138 | 30 | strong | 0 |
| plain_checks | RULE-2 | 3 | 4 | $1.172 | 32 | strong | 0 |
| plain_checks | RULE-3 | 3 | 4 | $1.193 | 30 | weak | 0 |
| plain_checks | RULE-4 | 3 | 4 | $1.178 | 25 | strong | 0 |
| plain_checks | RULE-5 | 3 | 4 | $1.182 | 32 | strong | 0 |
| plain_checks | RULE-6 | 3 | 4 | $1.147 | 24 | strong | 0 |
| plain_checks | RULE-7 | 1 | 2 | $0.533 | 12 | strong | 0 |
| plain_checks | RULE-9 | 1 | 2 | $0.568 | 20 | strong | 0 |
| sample_intake | RULE-1 | 2 | 3 | $0.554 | 15 | weak | 1 |
| sample_intake | RULE-2 | 2 | 3 | $0.521 | 16 | strong | 0 |
| sample_intake | RULE-3 | 1 | 2 | $0.378 | 17 | strong | 0 |
| sample_intake | RULE-4 | 2 | 3 | $0.528 | 18 | weak | 0 |
| sample_intake | RULE-5 | 2 | 3 | $0.537 | 15 | strong | 0 |
| sample_intake | RULE-6 | 1 | 2 | $0.383 | 11 | strong | 0 |
| sample_intake | RULE-7 | 1 | 2 | $0.351 | 11 | weak | 1 |
| sample_intake | RULE-8 | 1 | 2 | $0.382 | 11 | strong | 0 |

## Appendix B: every planted bug

Before and after are shortened to 150 characters, with line breaks shown as ` / `; the full text is in each evidence file under `audit.rules.<rule>.breaks`. The bug call time is the model call alone; the test run in the copy is not timed per proof by the audit.

| Feature | Rule | Proof | File:line | Before | After | Result | Rule verdict | Bug call | Bug cost | Judgement |
|---|---|---|---|---|---|---|---|---|---|---|
| specs | RULE-9 | PROOF-10 | `scripts/mcp/purlin/specs.py:225` | `if len(parts) > 1 and _looks_like_git_url(parts[0]):` | `if len(parts) > 2 and _looks_like_git_url(parts[0]):` | caught | strong | 5.5 s | $0.262 | RELEVANT |
| specs | RULE-9 | PROOF-31 | `scripts/mcp/purlin/specs.py:225` | `if len(parts) > 1 and _looks_like_git_url(parts[0]):` | `if len(parts) > 1:` | caught | strong | 5.1 s | $0.252 | RELEVANT |
| specs | RULE-10 | PROOF-11 | `scripts/mcp/purlin/specs.py:375` | `if path_match and not source_path:` | `if path_match and source_path:` | caught | strong | 4.5 s | $0.268 | RELEVANT |
| specs | RULE-11 | PROOF-12 | `scripts/mcp/purlin/specs.py:413` | `'pinned': pinned_match.group(1).strip() if pinned_match else None,` | `'pinned': None,` | caught | strong | 4.4 s | $0.270 | RELEVANT |
| specs | RULE-11 | PROOF-33 | `scripts/mcp/purlin/specs.py:300` | `is_anchor = ('/_anchors/' in rel_path / or content.lstrip().startswith('# Anchor:'))` | `is_anchor = content.lstrip().startswith('# Anchor:')` | caught | strong | 4.7 s | $0.269 | RELEVANT |
| specs | RULE-11 | PROOF-34 | `scripts/mcp/purlin/specs.py:300` | `is_anchor = ('/_anchors/' in rel_path / or content.lstrip().startswith('# Anchor:'))` | `is_anchor = ('/_anchors/' in rel_path)` | caught | strong | 4.7 s | $0.269 | RELEVANT |
| specs | RULE-17 | PROOF-17 | `scripts/mcp/purlin/specs.py:145` | `reflowing a long rule line does not end the signatures that bind it. / """ / return hashlib.sha256(_normalise(text).encode('utf-8')).hexdigest()` | `reflowing a long rule line does not end the signatures that bind it. / """ / return hashlib.sha256(_normalise(text)[:20].encode('utf-8')).hexdigest()` | caught | strong | 8.2 s | $0.276 | RELEVANT |
| specs | RULE-17 | PROOF-19 | `scripts/mcp/purlin/specs.py:136` | `return ' '.join((text or '').split())` | `return ' '.join((text or '').split(' '))` | caught | strong | 4.9 s | $0.252 | RELEVANT |
| specs | RULE-20 | PROOF-39 | `scripts/mcp/purlin/specs.py:293` | `except (IOError, OSError, UnicodeDecodeError):` | `except (IOError, OSError):` | caught | strong | 4.1 s | $0.268 | RELEVANT |
| specs | RULE-22 | PROOF-9 | `scripts/mcp/purlin/specs.py:115` | `elif name == 'windows': / unknown.append('@windows')` | `elif name == 'windows': / pass` | caught | strong | 5.0 s | $0.254 | RELEVANT |
| specs | RULE-22 | PROOF-24 | `scripts/mcp/purlin/specs.py:120` | `manual = manual or name == 'manual'` | `manual = manual` | caught | strong | 4.9 s | $0.253 | RELEVANT |
| specs | RULE-22 | PROOF-25 | `scripts/mcp/purlin/specs.py:69` | `_RETIRED_FIELDS = ('Visual-Reference', 'Visual-Hash')` | `_RETIRED_FIELDS = ('Visual-Ref', 'Visual-Hash')` | caught | strong | 5.1 s | $0.254 | RELEVANT |
| renumber | RULE-1 | PROOF-1 | `scripts/spec/renumber.py:331` | `if dry_run: / print(DRY_RUN, file=out) / return EXIT_OK` | `if dry_run: / print(DRY_RUN, file=out)` | caught | strong | 4.7 s | $0.234 | RELEVANT |
| renumber | RULE-2 | PROOF-2 | `scripts/spec/renumber.py:134` | `values = (info['name'], item, moving['line'], to, moving['text'])` | `values = (info['name'], item, moving['line'] + 1, to, moving['text'])` | caught | strong | 7.2 s | $0.239 | RELEVANT |
| renumber | RULE-3 | PROOF-3 | `scripts/spec/renumber.py:54` | `MOVES_NEITHER = ('%s: %s at line %d becomes %s: "%s". Neither line is on %s, ' / 'so the later one moves.')` | `MOVES_NEITHER = ('%s: %s at line %d becomes %s: "%s". Neither line is on %s, ' / 'so the later line moves.')` | caught | strong | 4.3 s | $0.237 | RELEVANT |
| renumber | RULE-3 | PROOF-4 | `scripts/spec/renumber.py:55` | `MOVES_NO_DEFAULT = ('%s: %s at line %d becomes %s: "%s". This checkout has no '` | `MOVES_NO_DEFAULT = ('%s: %s at line %d becomes %s: "%s". This checkout has not '` | caught | strong | 5.3 s | $0.220 | RELEVANT |
| renumber | RULE-4 | PROOF-5 | `scripts/spec/renumber.py:180` | `if then != text:` | `if then == text:` | caught | strong | 4.1 s | $0.234 | RELEVANT |
| renumber | RULE-4 | PROOF-6 | `scripts/spec/renumber.py:180` | `if then != text: / continue` | `if then == text: / continue` | caught | strong | 3.7 s | $0.234 | RELEVANT |
| renumber | RULE-5 | PROOF-7 | `scripts/spec/renumber.py:61` | `COMMENT_UNCOMMITTED = ('%s:%d names %s %s and is not committed, so it is not ' / 'changed: check which proof it means.')` | `COMMENT_UNCOMMITTED = ('%s:%d names %s %s and is not committed, so it is not ' / 'changed: check which proof it names.')` | caught | strong | 5.0 s | $0.236 | RELEVANT |
| renumber | RULE-6 | PROOF-8 | `scripts/spec/renumber.py:185` | `to = stale.get((path, marker.line, marker.id))` | `to = stale.get((path, marker.line, to))` | caught | strong | 4.9 s | $0.221 | RELEVANT |
| renumber | RULE-7 | PROOF-9 | `scripts/spec/renumber.py:205` | `if not numbers or old is None or max(numbers) <= old:` | `if not numbers or old is None or max(numbers) >= old:` | caught | strong | 4.8 s | $0.234 | RELEVANT |
| renumber | RULE-8 | PROOF-10 | `scripts/spec/renumber.py:257` | `if sha and _in_history(project_root, sha):` | `if sha:` | caught | strong | 5.1 s | $0.220 | RELEVANT |
| renumber | RULE-9 | PROOF-11 | `scripts/spec/renumber.py:145` | `and text.strip() not in on_default):` | `and text.strip() in on_default):` | caught | strong | 5.1 s | $0.222 | RELEVANT |
| renumber | RULE-9 | PROOF-12 | `scripts/spec/renumber.py:315` | `_write(full, lines)` | `pass` | caught | strong | 8.5 s | $0.225 | RELEVANT |
| summary | RULE-8 | PROOF-15 | `scripts/mcp/purlin/summary.py:121` | `if word in ('failed', 'partial'): / return 'to_fix'` | `if word in ('failed', 'partial') and (rule.get('proofs') or []): / return 'to_fix'` | caught | strong | 5.0 s | $0.288 | RELEVANT |
| summary | RULE-8 | PROOF-23 | `scripts/mcp/purlin/summary.py:127` | `if missing and here_os not in missing:` | `if missing:` | caught | strong | 4.1 s | $0.287 | RELEVANT |
| summary | RULE-8 | PROOF-33 | `scripts/mcp/purlin/summary.py:127` | `if missing and here_os not in missing:` | `if missing and here_os in missing:` | caught | strong | 4.8 s | $0.282 | RELEVANT |
| summary | RULE-18 | PROOF-44 | `scripts/mcp/purlin/summary.py:311` | `if payload.get('last_line'): / lines.append(payload['last_line'])` | `if payload.get('last_line') and payload.get('left'): / lines.append(payload['last_line'])` | caught | strong | 5.0 s | $0.271 | RELEVANT |
| summary | RULE-19 | PROOF-47 | `scripts/mcp/purlin/summary.py:85` | `'to_run_slow', 'to_test_remote', 'to_commit')` | `'to_run_slow', 'to_test_remote', 'to_commit', 'to_strengthen')` | caught | strong | 5.2 s | $0.272 | RELEVANT |
| summary | RULE-19 | PROOF-54 | `scripts/mcp/purlin/summary.py:84` | `BLOCKING = ('to_repair', 'to_correct', 'to_fix', 'no_test', 'to_test',` | `BLOCKING = ('to_repair', 'no_proof', 'to_correct', 'to_fix', 'no_test', 'to_test',` | caught | strong | 5.0 s | $0.288 | RELEVANT |
| summary | RULE-20 | PROOF-48 | `scripts/mcp/purlin/summary.py:87` | `OPENING = 'Purlin status: %s, plugin %s'` | `OPENING = 'Purlin status %s, plugin %s'` | caught | strong | 4.5 s | $0.288 | RELEVANT |
| summary | RULE-20 | PROOF-50 | `scripts/mcp/purlin/facts.py:74` | `if count == 1: / return (SIGNED_SINCE % (version, count)).replace('commits', 'commit')` | `if count == 0: / return (SIGNED_SINCE % (version, count)).replace('commits', 'commit')` | caught | strong | 5.2 s | $0.273 | RELEVANT |
| summary | RULE-20 | PROOF-53 | `scripts/mcp/purlin/summary.py:288` | `word = facts.TESTS_MET if payload.get('met') else facts.TESTS_NOT_MET` | `word = facts.TESTS_MET if payload.get('met') is not None else facts.TESTS_NOT_MET` | caught | strong | 12.0 s | $0.284 | RELEVANT |
| summary | RULE-21 | PROOF-52 | `scripts/mcp/purlin/summary.py:258` | `counts['to_commit'] = len(set(uncommitted))` | `counts['to_commit'] = len(set(uncommitted)) - 1` | caught | strong | 5.1 s | $0.272 | RELEVANT |
| summary | RULE-22 | PROOF-4 | `scripts/mcp/purlin/summary.py:205` | `'pass their tests', count))]` | `'pass their test', count))]` | caught | strong | 9.6 s | $0.280 | RELEVANT |
| summary | RULE-22 | PROOF-5 | `scripts/mcp/purlin/summary.py:204` | `'%d %s.' % (count, _words('passes its tests',` | `'%d %s.' % (count, _words('pass their tests',` | caught | strong | 5.4 s | $0.270 | RELEVANT |
| summary | RULE-22 | PROOF-43 | `scripts/mcp/purlin/summary.py:211` | `parts.append(AUDIT_SHARE % (strong, over, strong * 100 // over))` | `parts.append(AUDIT_SHARE % (strong, over, strong * 100 // over + 1))` | caught | strong | 5.0 s | $0.288 | RELEVANT |
| summary | RULE-23 | PROOF-8 | `scripts/mcp/purlin/summary.py:310` | `lines.extend('  ' + line for line in left_lines(payload))` | `lines.extend(' ' + line for line in left_lines(payload))` | caught | strong | 6.6 s | $0.277 | RELEVANT |
| summary | RULE-23 | PROOF-29 | `scripts/mcp/purlin/summary.py:64` | `('to_correct', 'test comment to correct', 'test comments to correct',` | `('to_correct', 'test comment to fix', 'test comments to correct',` | caught | strong | 4.8 s | $0.289 | RELEVANT |
| summary | RULE-23 | PROOF-40 | `scripts/mcp/purlin/summary.py:251` | `counts[kind] = len(to_repair)` | `counts[kind] = counts.get(kind, 0) + 1` | caught | strong | 6.5 s | $0.294 | RELEVANT |
| summary | RULE-24 | PROOF-55 | `scripts/mcp/purlin/summary.py:70` | `('to_run_slow', 'slow proof to run', 'slow proofs to run',` | `('to_run_slow', 'slow proofs to run', 'slow proofs to run',` | caught | strong | 8.8 s | $0.296 | RELEVANT |
| summary | RULE-24 | PROOF-56 | `scripts/mcp/purlin/summary.py:145` | `return bool(proof.get('slow')) and proof.get('env') in (None, here_os)` | `return bool(proof.get('slow'))` | caught | strong | 6.3 s | $0.293 | RELEVANT |
| config_engine | RULE-4 | PROOF-4 | `scripts/mcp/config_engine.py:159` | `return _read_json(project_root) or {}` | `return {}` | caught | strong | 4.7 s | $0.204 | RELEVANT |
| config_engine | RULE-4 | PROOF-7 | `scripts/mcp/config_engine.py:159` | `return _read_json(project_root) or {}` | `return _read_json(project_root) or {'version': None}` | caught | strong | 5.0 s | $0.204 | RELEVANT |
| config_engine | RULE-8 | PROOF-8 | `scripts/mcp/config_engine.py:171` | `config = _read_json(project_root) or {} / config[key] = value` | `config = {} / config[key] = value` | caught | weak | 5.4 s | $0.213 | RELEVANT |
| config_engine | RULE-8 | PROOF-24 | `scripts/mcp/config_engine.py:173` | `config[key] = value / os.makedirs(os.path.dirname(path), exist_ok=True)` | `config[key] = value / config.setdefault('version', None) / os.makedirs(os.path.dirname(path), exist_ok=True)` | caught | weak | 5.0 s | $0.205 | RELEVANT |
| config_engine | RULE-8 | PROOF-38 | `scripts/mcp/config_engine.py:179` | `with open(tmp_path, 'w', encoding='utf-8', newline='\n') as f:` | `with open(tmp_path, 'w', encoding='utf-8') as f:` | survived | weak | 4.3 s | $0.222 | RELEVANT on Windows; has no effect on macOS, where the audit ran it |
| config_engine | RULE-10 | PROOF-26 | `scripts/mcp/config_engine.py:184` | `if os.path.exists(tmp_path): / os.remove(tmp_path) / raise` | `raise` | caught | strong | 4.1 s | $0.221 | RELEVANT |
| config_engine | RULE-10 | PROOF-27 | `scripts/mcp/config_engine.py:184` | `if os.path.exists(tmp_path): / os.remove(tmp_path) / raise` | `raise` | caught | strong | 4.0 s | $0.222 | RELEVANT |
| config_engine | RULE-10 | PROOF-39 | `scripts/mcp/config_engine.py:184` | `if os.path.exists(tmp_path): / os.remove(tmp_path) / raise` | `raise` | caught | strong | 4.7 s | $0.221 | RELEVANT; the test is skipped off Windows, so `caught` here is the skip, not a catch |
| config_engine | RULE-14 | PROOF-32 | `scripts/mcp/config_engine.py:130` | `% (error.msg, error.lineno))` | `% (error.msg, error.lineno - 1))` | caught | strong | 5.7 s | $0.206 | RELEVANT |
| config_engine | RULE-14 | PROOF-33 | `scripts/mcp/config_engine.py:125` | `return CONFIG_CANNOT_BE_READ % 'it is not UTF-8 text'` | `return CONFIG_CANNOT_BE_READ % 'it is not UTF-8'` | caught | strong | 4.9 s | $0.206 | RELEVANT |
| config_engine | RULE-14 | PROOF-35 | `scripts/mcp/config_engine.py:130` | `return CONFIG_CANNOT_BE_READ % ('%s at line %d' / % (error.msg, error.lineno))` | `return CONFIG_CANNOT_BE_READ % ('%s at line %d' / % (error.msg, error.lineno - 1))` | caught | strong | 4.5 s | $0.223 | RELEVANT |
| config_engine | RULE-19 | PROOF-45 | `scripts/mcp/purlin/project.py:23` | `for section in ('project', 'tool.poetry'):` | `for section in ('tool.poetry',):` | caught | strong | 4.9 s | $0.207 | RELEVANT |
| config_engine | RULE-19 | PROOF-48 | `scripts/mcp/purlin/project.py:26` | `for found in (_package_json_name(project_root), _csproj_name(project_root), / _origin_name(project_root)):` | `for found in (_package_json_name(project_root), _csproj_name(project_root)):` | caught | strong | 4.1 s | $0.222 | RELEVANT |
| config_engine | RULE-19 | PROOF-49 | `scripts/mcp/purlin/project.py:30` | `return os.path.basename(os.path.abspath(project_root))` | `return os.path.basename(os.path.dirname(os.path.abspath(project_root)))` | caught | strong | 4.1 s | $0.221 | RELEVANT |
| config_engine | RULE-20 | PROOF-50 | `scripts/mcp/config_engine.py:43` | `if all(key in UPGRADE_KEYS for key in others):` | `if not all(key in UPGRADE_KEYS for key in others):` | caught | strong | 5.0 s | $0.206 | RELEVANT |
| config_engine | RULE-20 | PROOF-51 | `scripts/mcp/config_engine.py:29` | `SETTINGS_REMOVE = 'Remove it from .purlin/config.json.'` | `SETTINGS_REMOVE = 'Remove it from .purlin/config.json'` | caught | strong | 4.0 s | $0.222 | RELEVANT |
| config_engine | RULE-21 | PROOF-18 | `scripts/mcp/config_engine.py:76` | `return current, 'climb'` | `return os.path.dirname(current), 'climb'` | caught | strong | 8.0 s | $0.212 | RELEVANT |
| config_engine | RULE-21 | PROOF-28 | `scripts/mcp/config_engine.py:70` | `if env_root and os.path.isdir(env_root): / return env_root, 'env'` | `if env_root and os.path.isdir(os.path.join(env_root, '.purlin')): / return env_root, 'env'` | caught | strong | 5.2 s | $0.206 | RELEVANT |
| config_engine | RULE-21 | PROOF-30 | `scripts/mcp/config_engine.py:82` | `return os.path.abspath(os.getcwd()), 'cwd'` | `return os.path.abspath(os.getcwd()), 'climb'` | caught | strong | 4.9 s | $0.206 | RELEVANT |
| plain_checks | RULE-1 | PROOF-1 | `scripts/review/plain_checks.py:44` | `CHECKS_NOTHING = '%s::%s: the test checks nothing.'` | `CHECKS_NOTHING = '%s::%s: the test asserts nothing.'` | caught | strong | 8.1 s | $0.298 | RELEVANT |
| plain_checks | RULE-1 | PROOF-3 | `scripts/review/plain_checks.py:489` | `if _helper_elsewhere_asserts(self.project_root, self.path, 'Python', / self._called_elsewhere()): / return None / return CHECKS_NOTHING, () / def _ass` | `return CHECKS_NOTHING, () / def _assertions(self):` | caught | strong | 4.9 s | $0.309 | RELEVANT |
| plain_checks | RULE-1 | PROOF-4 | `scripts/review/plain_checks.py:446` | `return (name.startswith('assert') or name in ('raises', 'warns', 'fail')` | `return (name.startswith('assert') or name in ('warns', 'fail')` | caught | strong | 8.7 s | $0.300 | RELEVANT |
| plain_checks | RULE-2 | PROOF-9 | `scripts/review/plain_checks.py:524` | `if same and (isinstance(kind, (ast.Eq, ast.Is, ast.LtE, ast.GtE)) or kind in (` | `if same and (isinstance(kind, (ast.Is, ast.LtE, ast.GtE)) or kind in (` | caught | strong | 5.2 s | $0.309 | RELEVANT |
| plain_checks | RULE-2 | PROOF-10 | `scripts/review/plain_checks.py:534` | `return zero(left) and size(right) / return False` | `return zero(left) and size(right) / return True` | caught | strong | 8.7 s | $0.315 | RELEVANT |
| plain_checks | RULE-2 | PROOF-11 | `scripts/review/plain_checks.py:846` | `if _norm(actual) == _norm(expected) and '(' not in actual: / return True` | `if _norm(actual) == _norm(expected) and '(' in actual: / return True` | caught | strong | 5.3 s | $0.293 | RELEVANT |
| plain_checks | RULE-3 | PROOF-13 | `scripts/review/plain_checks.py:545` | `if all(isinstance(stmt, ast.Pass) or` | `if all(isinstance(stmt, ast.Continue) or` | caught | weak | 5.0 s | $0.308 | RELEVANT |
| plain_checks | RULE-3 | PROOF-14 | `scripts/review/plain_checks.py:545` | `if all(isinstance(stmt, ast.Pass) or` | `if any(isinstance(stmt, ast.Pass) or` | survived | weak | 4.0 s | $0.308 | IRRELEVANT: `all` to `any` gives the same answer for a handler holding one `assert`, the only case the proof names |
| plain_checks | RULE-3 | PROOF-17 | `scripts/review/plain_checks.py:872` | `if not mask[start + 1:end - 1].strip():` | `if mask[start + 1:end - 1].strip():` | caught | weak | 4.9 s | $0.293 | RELEVANT |
| plain_checks | RULE-4 | PROOF-18 | `scripts/review/plain_checks.py:47` | `EXPECTED_FROM = '%s::%s: the expected value comes from %s(), the code under test.'` | `EXPECTED_FROM = '%s::%s: the expected value comes from %s(), the code being tested.'` | caught | strong | 4.2 s | $0.309 | RELEVANT |
| plain_checks | RULE-4 | PROOF-19 | `scripts/review/plain_checks.py:590` | `if _callee(first) and ast.dump(first) == ast.dump(second) and not any(` | `if _callee(first) and ast.dump(first) != ast.dump(second) and not any(` | caught | strong | 7.8 s | $0.313 | RELEVANT |
| plain_checks | RULE-4 | PROOF-20 | `scripts/review/plain_checks.py:918` | `if first and second and first[1] == second[1] and not (` | `if first and second and first[1] != second[1] and not (` | caught | strong | 4.3 s | $0.308 | RELEVANT |
| plain_checks | RULE-5 | PROOF-22 | `scripts/review/plain_checks.py:636` | `if target in checked: / return MOCKS_IT, (target,) / return None / # --------------------------------------------------------------------------- / # J` | `if target not in checked: / return MOCKS_IT, (target,) / return None / # --------------------------------------------------------------------------- /` | caught | strong | 4.8 s | $0.310 | RELEVANT |
| plain_checks | RULE-5 | PROOF-23 | `scripts/review/plain_checks.py:636` | `if target: / targets.append(target) / return targets / def _mocks(self): / checked = self._checked() / for target in self._mocked(): / if target in ch` | `if target: / targets.append(target) / return targets / def _mocks(self): / checked = self._checked() / for target in self._mocked(): / if target not i` | caught | strong | 13.2 s | $0.326 | RELEVANT |
| plain_checks | RULE-5 | PROOF-24 | `scripts/review/plain_checks.py:944` | `if len(call.args) > 1: / targets.append(call.args[1].strip().strip('\'"`'))` | `if len(call.args) > 2: / targets.append(call.args[1].strip().strip('\'"`'))` | caught | strong | 4.3 s | $0.309 | RELEVANT |
| plain_checks | RULE-6 | PROOF-25 | `scripts/review/plain_checks.py:49` | `NEVER_CHECKS = '%s::%s: the proof expects %s and the test never checks it.'` | `NEVER_CHECKS = '%s::%s: the proof expects %s and the test never checks it'` | caught | strong | 5.0 s | $0.309 | RELEVANT |
| plain_checks | RULE-6 | PROOF-26 | `scripts/review/plain_checks.py:314` | `return any(float(n) == wanted for n in _NUMBERS_RE.findall(body))` | `return any(n == value for n in _NUMBERS_RE.findall(body))` | caught | strong | 7.6 s | $0.298 | RELEVANT |
| plain_checks | RULE-6 | PROOF-27 | `scripts/review/plain_checks.py:291` | `if data is not None: / held.append(data) / break` | `if data is not None: / break` | caught | strong | 3.8 s | $0.309 | RELEVANT |
| plain_checks | RULE-7 | PROOF-28 | `scripts/review/plain_checks.py:182` | `if key not in said:` | `if True:` | caught | strong | 3.7 s | $0.308 | RELEVANT |
| plain_checks | RULE-9 | PROOF-30 | `scripts/review/plain_checks.py:238` | `done = subprocess.run(['git', 'ls-files', '-co', '--exclude-standard', '-z'],` | `done = subprocess.run(['claude', 'ls-files', '-co', '--exclude-standard', '-z'],` | caught | strong | 8.8 s | $0.318 | RELEVANT |
| sample_intake | RULE-1 | PROOF-1 | `src/intake.py:30` | `if barcode is None or not barcode.strip():` | `if barcode is None:` | caught | weak | 4.5 s | $0.186 | RELEVANT |
| sample_intake | RULE-1 | PROOF-2 | `src/intake.py:30` | `if barcode is None or not barcode.strip():` | `if barcode is None or not barcode:` | caught | weak | 4.6 s | $0.153 | RELEVANT |
| sample_intake | RULE-2 | PROOF-3 | `src/intake.py:5` | `BARCODE = re.compile(r'^LC-\d{8}$')` | `BARCODE = re.compile(r'^LC-\d{7}$')` | caught | strong | 4.7 s | $0.153 | RELEVANT |
| sample_intake | RULE-2 | PROOF-4 | `src/intake.py:5` | `BARCODE = re.compile(r'^LC-\d{8}$')` | `BARCODE = re.compile(r'^LC-\d{7,8}$')` | caught | strong | 5.0 s | $0.153 | RELEVANT |
| sample_intake | RULE-3 | PROOF-5 | `src/intake.py:38` | `age = age_hours(collected, received)` | `age = age_hours(collected, received) + 1` | caught | strong | 6.1 s | $0.173 | RELEVANT |
| sample_intake | RULE-4 | PROOF-6 | `src/intake.py:6` | `MAX_AGE_HOURS = 72` | `MAX_AGE_HOURS = 73` | caught | weak | 4.6 s | $0.153 | RELEVANT |
| sample_intake | RULE-4 | PROOF-7 | `src/intake.py:40` | `if age > MAX_AGE_HOURS:` | `if age >= MAX_AGE_HOURS:` | survived | weak | 6.9 s | $0.158 | RELEVANT |
| sample_intake | RULE-5 | PROOF-8 | `src/intake.py:7` | `FROZEN_MAX_C = -20.0` | `FROZEN_MAX_C = -19.9` | caught | strong | 4.8 s | $0.153 | RELEVANT |
| sample_intake | RULE-5 | PROOF-9 | `src/intake.py:43` | `and temperature_c > FROZEN_MAX_C:` | `and temperature_c >= FROZEN_MAX_C:` | caught | strong | 3.7 s | $0.169 | RELEVANT |
| sample_intake | RULE-6 | PROOF-10 | `src/intake.py:36` | `if received < collected:` | `if received > collected:` | caught | strong | 4.5 s | $0.168 | RELEVANT |
| sample_intake | RULE-7 | PROOF-11 | `src/intake.py:49` | `accession = '%s-%d-%05d' % (site, received.year, number)` | `accession = '%s-%d-%04d' % (site, received.year, number)` | survived | weak | 5.1 s | $0.153 | RELEVANT |
| sample_intake | RULE-8 | PROOF-12 | `src/intake.py:35` | `raise IntakeError('barcode %s was already received' % barcode)` | `raise IntakeError('barcode %s already received' % barcode)` | caught | strong | 4.1 s | $0.169 | RELEVANT |
