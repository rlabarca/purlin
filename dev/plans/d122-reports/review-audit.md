# Review: decision 123, the audit's planted bug

Range `e02c9b4f5..c5d45b0c1`, read at local `main` (no later change to the reviewed files).
Nothing in the checkout was touched. Everything marked "ran" was run in
`scratchpad/review-audit/` on a copy of `scripts/` and the `dev/` helpers, with the fake
`claude` (scripts `try1.py` to `try5.py` there).

Seriousness: **wrong result** (a verdict or a `no_bug` sentence that is not true), **crash**,
**cosmetic**. "Old" means the fault was there before decision 123 and this change did not
touch it; "new" means this change brought it or widened it.

No crash was found. No `%` in a case, a changed line, a path or a reason breaks any
formatting: every finding string is filled with `%` and a tuple, and the model's text is
always an argument, never the format (ran: case `100% %s %d` printed as written).

---

## A. Confirmed by running

### A1. A change that only adds a trailing comment survives and makes the rule `weak` (wrong result, new guard leaves it)

`scripts/review/targeted_break.py:149-166` (`only_comment`), used at `:234`.

Input: part `before: "    return days"`, `after: "    return days  # planted bug: off by one"`,
`aim: past the test`, `case: c`, against the strong test `assert age(...) == 90`.

Output:

```
age RULE-1   weak
  PROOF-1: the test still passes when src/age.py:12 reads "return days  # planted bug: off by one"
  PROOF-1: the AI says this breaks: c
```

The code did not change, the test is sound, and the rule reads `weak`. The same holds for
every change the guard does not see as a comment (ran `only_comment`, all `refused=False`):

| Change | File |
|---|---|
| trailing `# ...` or `// ...` on a code line | `.py`, `.js` |
| a `/* planted */` block comment line | `.js` |
| a docstring's words | `.py` |
| `-- planted` | `.sql` |
| `; planted` | `.ini` |
| a whole line `# c` | `Makefile`, `.ps1` (no listed ending) |
| `=begin ... =end` | `.rb` |

The contract (d123 section 2) defines a comment line as a whole line opening `//`, or `#`
in seven endings, so all of these are **left by the contract, not ruled in**. The harm is
that a no-op survivor sets `weak` with no person in between; the `AI says` line is the only
check. Smallest fix that stays inside the contract's words: in `only_comment`, cut a trailing
` #...` (hash files) or ` //...` from each kept line before comparing, when the cut is
preceded by white space and the line holds no quote character. Block comments and docstrings
need a decision.

### A2. `aim:` followed by `no break:` is reported as an unusable answer (wrong result, new)

`targeted_break.py:127-129`: `_NO_BREAK_RE` is matched on the whole part before the `aim:` and
`case:` lines are taken off, so it only matches when `no break:` is the first line.

Input: `aim: plain\nno break: the test checks the case and its result`

Output: `No bug was planted: the model's answer for PROOF-1 could not be used: the answer named no change.`

Expected: `No bug was planted: the model found no change that would break PROOF-1: the test checks ...`.
The request invites this reply: `REPLY_PARTS` says "aim: reading plain where the proof's test
leaves no way past it" directly before offering `no break:` (`ai_audit.py:288-307`).
Fix: run the `aim:`/`case:` loop first, then match `_NO_BREAK_RE` on what is left.

### A3. A blank line between the `before:` block and `after:` turns a catchable bug into `not run` (wrong result, old)

`targeted_break.py:92-93` and `:143-146`: `before` keeps its trailing line end, `after` has its
cut (`rstrip('\n')`).

Input: `before:\n    days = minutes(stamp)\n\nafter:\n    days = 0`

Output: `not run`, `before == '    days = minutes(stamp)\n'`. The replacement eats the line end,
the next line is joined on, the file no longer parses. Without the blank line: `caught`.
Fix: `found.group('before').rstrip('\n')` where it is returned (keep the `.strip()` emptiness check).

### A4. A multi-line `before:` never matches a file with CRLF line ends (wrong result, old)

`ai_audit.py:392-394` (`_file_of` opens with universal newlines, so the model is shown `\n`),
`ai_audit.py:421` (`splitlines()` drops `\r`), against `targeted_break.py:327` (`newline=''`
keeps `\r\n`).

Input: `src/age.py` committed with CRLF; `before:` of two lines copied exactly from the request.

Output: `No bug was planted: the model's answer for PROOF-1 could not be used: the lines before the change are not in src/age.py.`

A one-line `before:` still matches. This is every multi-line bug on a Windows checkout with
`core.autocrlf=true`. Fix: in `_plant`, when `old` is not found and the text holds `\r\n`,
retry with `old` and `new` converted to `\r\n`.

`parse_answer` on a part with CRLF line ends returns `None` (ran), but `read_reply`'s
`splitlines()` removes them first, so through the audit a CRLF reply is read correctly (ran).

### A5. A `no break:` reason is classed `answer unusable` when its words fit one of the module's own sentences (wrong result, old; two more patterns added)

`targeted_break.py:176-179`: `cause_of` turns `%s` into `.+` and uses `fullmatch`.

Input: `no break: the refund path the proof names is not in the project`

Output: `No bug was planted: the model's answer for PROOF-1 could not be used: the refund path the proof names is not in the project.`

Any reason ending `is not in the project`, `is outside the copy of the project` or
`is not a file the feature's scope names` does it. Fix: carry the cause from `_plant`
(`_result(..., cause=...)`) and store it in the entry, instead of guessing it back from `why`;
or, smaller, have `_plant` return `MODEL_FOUND_NONE` directly for the `no break` branch.

### A6. Control characters and ANSI escapes from the model reach the terminal and the evidence (cosmetic to wrong display; `case` is new, the other two old)

`targeted_break.py:138` (case), `:92` (file), `:129` (the `no break` reason); printed at
`audit_run.py:470`, and again by `ai_audit.render`, the status and the sign-off list.

Input: `case: x \x1b[2J\x1b[31mFAKE\x07 <script>alert(1)</script>`

Output (repr of the printed line): `'  PROOF-1: the AI says this breaks: x \x1b[2J\x1b[31mFAKE\x07 <script>...'`,
and the same bytes in `findings` and `breaks.case` of the committed evidence. A
`file: src/\x1b[31mage.py` reaches the terminal through `NOT_IN_SCOPE`.

A reply can clear the screen or repaint a verdict line above it. The dashboard is safe:
`scripts/report/src/rule.js:141` draws each finding through `esc()`
(`app.js:130`, escapes `& < > " '`), and `report-data.js` is written with `json.dumps`
(ASCII escapes). Fix: in `parse_answer`, replace every character below U+0020 and U+007F to
U+009F in `case`, `file` and the `no break` reason with a space, before the 300 cut.

### A7. A multi-line `no break:` reason is printed over several lines (cosmetic, old)

`targeted_break.py:91` (`re.S`, `(.*?)\s*$` takes everything to the end of the part).

Input: `no break: nothing here.\nThe code is a constant.`

Output: two printed lines, the second with no indent, which `Audited.under`-style readers and
a person take for a new rule line. A part that opens `no break:` and then names a change is
read as `no break` with the whole change as its reason (ran). Fix: take the first line only.

### A8. A part the parser cannot read is always reported as "named no change" (cosmetic, new for the three `aim`/`case` shapes)

`targeted_break.py:131-144`. All ran, all give
`could not be used: the answer named no change`, though each names a change:

| Reply | Why it fails |
|---|---|
| `Aim: plain` / `Case: c` | `_AIM_RE`, `_CASE_RE` are case-sensitive and anchored at column 0 |
| `- aim: plain`, `  aim: plain` | same |
| `case:` wrapped onto a second line | the second line is not `file:` |
| `case:` placed after `file:` | `_CHANGE_RE` wants `before:` directly after `file:` |
| `**=== PROOF-1 ===**` or an indented head | `_HEAD_RE`; reported as `it holds none` |
| `file: \`src/age.py\`` | reported as not in scope |

The request says "in exactly the shape", so these are **left**, but the sentence a person reads
is wrong about what happened. Smallest fix: match `aim`/`case` with `re.I` and leading white
space allowed; strip back-ticks from `file:`.

### A9. The first finding names a comment line when the change opens with one (cosmetic, new interplay with PROOF-31)

`targeted_break.py:287-299` (`_changed_line` reports the first line that differs).

Input: `after: "    # planted\n    return 0"` with a weak test.

Output: `PROOF-1: the test still passes when src/age.py:12 reads "# planted"`. The line that
changes behaviour is 13, `return 0`. A deletion reads `src/age.py:10 reads ""` (ran). Fix: in
`_changed_line`, skip new lines `only_comment` would drop.

### A10. A kept entry with no `aim`/`case` is written back without them (cosmetic, new)

`audit_run.py:335-336`: `breaks[proof_id] = value` as kept.

Ran: an entry stripped of both keys, read again, stays `{'aim': <absent>, 'case': <absent>}` in
the evidence, for `caught` and `survived` alike; the survivor prints its first finding only,
which is the contract. Nothing in `scripts/` reads `aim`, and `case` is read only at
`audit_run.py:250` with `or ''`, so "reads `plain` and `''` wherever it is read" holds. But
`evidence_format.md` (line 207) lists both as fields of every entry. Fix:
`breaks[proof_id] = dict(value, aim=value.get('aim') or PLAIN, case=value.get('case') or '')`.
Note `merge_audit` (`scripts/run/evidence.py:529-532`) does not compare `breaks`, so this
alone rewrites no entry.

A kept `case` that is not a string is printed as Python writes it (`['a', 'b']`, ran); only a
hand-edited evidence file holds one.

### A11. The guard refuses real changes (wrong result of the small kind: a bug that would count is `not made`; new)

`only_comment`, all ran, all `refused=True`:

| Change | Why it is real |
|---|---|
| `#!/bin/sh` to `#!/bin/bash` in `.sh`; a shebang deleted in `.py` | picks the interpreter |
| `# -*- coding: ... -*-` in `.py` | changes how the file is decoded |
| a line `# x` added inside a `"""` string in `.py`; a `//x` line inside a JS template string | changes the string's value |
| a blank line added inside a multi-line string | same |
| `//go:build windows` in `.go`; `// @ts-ignore` in `.ts` | directives |
| trailing white space only; CR only | no change in most languages, a real one inside a string |

Each is within the contract's definition of a comment line (ruled in by the contract), so the
code does what it was told; the contract is what is loose. Ruled correctly (ran): a `#` inside
a string on a code line, a `//` in a URL on a code line, commenting a code line out, deleting
code while adding a comment, Python indentation only, tabs for spaces, `#` in `.txt`,
`#if` in `.cs`, upper-case `.PY`. YAML and TOML `#` lines are true comments.

### A12. Kept results and findings: no defect

Ran on a two-proof project, audited, then read again with `again=True`:
both findings for the survivor again, same order, no duplicate, no bug asked
(`Plant one bug` absent, 1 call). `_survived_finding` cannot take the `AI says` line: it matches
`PROOF-N: the test still passes when`, and the colon keeps `PROOF-1` from `PROOF-10`. Spot
findings come first, then each survivor's pair (`audit_run.py:430`). An entry whose `findings`
were emptied by hand is rebuilt to the same two lines.

### A13. Nothing writes under `.purlin/runtime/`, no cost or count is printed, callers are updated

After the audit `.purlin/runtime/` holds `reports` alone, which the test run wrote. The
acceptance grep (`cost_usd|total_cost|audit_run\.json|CALLS_|EXPERIMENTAL`) is empty.
`planted_bugs` has one caller, `audit_run.py:424`, unpacking three values; no test calls it.
`One call per rule` stays in two docstrings (`ai_audit.py:21`, `audit_run.py:8`), which the
plan allows as mechanism. No page under `docs/`, `skills/`, `references/` holds a count.

### A14. No write leaves the copy

`file:` values `../outside.py`, absolute paths and anything not in the scope set are refused
before the copy (`targeted_break.py:236-245`); `./src/age.py` and `src\age.py` normalise to the
scope's path and plant (ran, `caught`); `_inside` (`:306-311`) checks the real path; links
are not copied. `case` is never used as a path.

---

## B. Suspected by reading, not run to the end

### B1. A `before:` or `after:` block holding a head line cuts the part (wrong result, old)

`ai_audit.py:404,421-428`. Ran `read_reply` alone: a block line `=== reading ===` or
`=== PROOF-2 ===` ends the part there, so the change is lost and the reading starts early.
Only a scope file with such a line at column 0 triggers it. Left as is unless a project hits it.

### B2. `splitlines()` splits on more than line ends (cosmetic, old)

`ai_audit.py:421`: form feed, U+2028, U+0085 in a `case` or a block become line breaks (ran
`read_reply`: `x\x0cy` became two lines), so a case holding U+2028 is cut and the part is
refused, and a `before:` holding a form feed never matches. Fix: `text.split('\n')` after
replacing `\r\n`.

### B3. A trailing fence line of a real `after:` block is dropped (wrong result, old)

`targeted_break.py:124-125` pops every last line that opens with three back-ticks. A change
to a Markdown file in scope whose `after:` ends with a fence loses that line.

### B4. The request against the parser

`references/review_criteria.md:184-205`, `ai_audit.REQUEST_BUGS`, `REPLY_PARTS` and
`parse_answer` agree on the part's five lines, their order, `no break:`, the two aims and the
300 limit. Three soft spots:

- A2 above: the request suggests `aim: plain` for a test with no way past, next to `no break:`.
- The criteria's example is inside a code fence and names `PROOF-1` whatever the proof asked
  for; the parser strips fences around a part and around the whole reply (ran, `caught`), so
  this costs nothing.
- Neither text says `case:` must stay on one line of the reply; the criteria say "is one
  line", the request's shape only shows it. A wrapped case is refused (A8).

### B5. `aim` near-misses read `plain` (cosmetic)

`aim: past the test.` and ``aim: `past the test` `` are recorded `plain` (ran `parse_answer`).
The contract rules this in ("any other word"). Stripping `.` and back-ticks would record the
model's meaning.

---

## C. The new tests against their proofs

All of `ai_audit` PROOF-125 to 135 and `planted_bug` PROOF-22 to 31 show what their proof
lines say; none is vacuous. PROOF-134 is sound even though `merge_audit` keeps an equal entry:
an audit that lost the second finding would differ and be written. What the set would not
catch:

| Break that passes every test | Rule it breaks | Missing proof |
|---|---|---|
| `HASH_COMMENTS = ('.py',)` | `planted_bug` RULE-18, six of seven endings | one proof for another ending, such as `.yml` |
| drop `not start` from `only_comment` (blank lines count as code) | RULE-18, "blank lines" | a change that adds one blank line reads `not made` |
| drop `.lower()` in `only_comment` or in the aim compare | none stated | none needed unless the rule should say it |
| move both refusals after `_copy_project` | contract: "before the copy is made" | PROOF-26 and 28 check the test did not run in a copy, not that no copy was made; the rule says only the former |
| A1 to A9 above | | no test holds a `case` with a control character, an `aim:` before `no break:`, a trailing comment, or CRLF |

`dev/test_planted_bug.py:514` (PROOF-28) checks the refusal line is somewhere in the output,
not under `age RULE-1`; with one rule in the project that is the same thing.
