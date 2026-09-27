# Lane 13: the closing review

What a full re-read of the code, the references, the skills, the specs and the docs found,
against `dev/plans/three-levels.md` decisions 23 to 30 and `references/glossary.md`. Line
numbers are as of `832c291e5`, the stack tip this lane started from.

Each finding is marked **fixed** where this lane made the change, or **open** where it is
left. Everything a decision does not settle is under **Questions** and was not decided here.

Counts: Logic 12, Terms 14, Elegance 9, Clarity 21. Questions 10.

---

## Logic

**L1. `scripts/review/sign.py:185` — the brief a signature names is a path nothing writes.
fixed.** `brief_for` built `.purlin/briefs/<feature>/<RULE-N>.<hash8>.brief.json`, without the
`<source>` folder the records split into, so it never found a brief and every signature and
every hold wrote `brief: null`. The lookup now lives once in `records.find_brief`, which the
payload, `sign.py` and the brief writer all read.

**L2. `scripts/mcp/purlin/states.py:362` — a source the gate does not read answered for a
platform. fixed.** At the gate `signed` this checkout's own run was listed in `platforms` and
searched for failures, so a red local macOS run made a rule whose CI record passed read
`partial`, which is not met. `specs/mcp/states.md` RULE-43 says "a counting run named", and
decision 29 says only `ci` counts at `signed` for the tests and the audit both. The passed cell
now reads no part of a source the gate does not count, except the last branch, which still says
which run it found and why it does not count.

**L3. `scripts/mcp/purlin/payload.py:233` — the strength the strong cell compares can come from
a record the gate does not count. open.** `test_strength` is read from `_latest(all_records)`,
every record of the feature, not from the latest counting one. At `signed`, a `local` audit
newer than CI's supplies the number the strong cell compares against `min_strength`, though
that audit is a preview there. `tl-_rules.md` item 2 says "the latest counting record's";
`specs/mcp/states.md` RULE-11 says "the feature's latest test strength", which is what the code
does. The two disagree — Question Q1.

**L4. `scripts/review/brief.py` and `scripts/mcp/purlin/payload.py` — a local brief was read at
`signed`. fixed.** `_read_brief` walked both source folders whatever the gate, so a brief a
local audit wrote could clear `not audited` and settle the strong cell at `signed`.
`specs/review/brief.md` PROOF-45 already refuses to *write* one there; reading one is the same
question. `records.find_brief` now takes the gate and reads only the folders that count.

**L5. `scripts/hooks/pre-push.sh:79` — the pre-push hook makes a commit during a push. open.**
It runs `purlin_run.py --all --quick`, and `--quick` always writes and commits
`.purlin/tests/` and `.purlin/tests.md`. The commit lands after git has already chosen the refs
to send, so the push does not carry it and the branch is left one commit ahead of the remote
the instant the push succeeds. Question Q2.

**L6. `scripts/run/remote.py:89` — the remote run watches whichever run `gh` picks. open.**
`gh run watch --exit-status` is called with no run id; `gh` prompts for one interactively and
errors when it is not a terminal, and where it does pick one it is the newest run, not
necessarily the one this push started. The fix is `gh run list --branch <run branch> --limit 1
--json databaseId` with a short retry while the run is registering, then `gh run watch <id>`;
it needs a fake `gh` in the test, which is why it is left. Question Q3.

**L7. `scripts/mcp/purlin/states.py:545` — a held rule whose tests are not passing reads `weak`,
not `held`.** `_strong_cell` returns `weak` with the one reason `not passed` before it looks at
the holds, so the strong cell reads `weak` while the signed cell reads `held` and `flags.held`
is true. The rule is then on neither list. `tl-_rules.md` item 2 and item 4 disagree with each
other on this case. open — Question Q4.

**L8. `scripts/review/sign.py:648` — a non-signer is refused at the gate `strong`.** The check
`signers and email not in signers` runs at both gates, but under `strong` a signature from
anyone counts (`signatures.counts` returns True for any gate but `signed`), so a project that
set a signer list early refuses a signature it would then have counted. open.

**L9. `scripts/review/sign.py:660` — `--batch` and a bare feature sign nothing at `strong`.**
Both read `payload['sign_list']`, which the payload builds only at the gate `signed`, so at
`strong` they print `nothing here needs a signature` even for a rule whose strong cell reads
`manual test`. Naming the rules explicitly still works, and A5 says a bare signature at
`strong` "writes it anyway if asked", so this is the plan's behaviour read strictly; it reads
as a dead end at the terminal. open.

**L10. `scripts/mcp/purlin/status.py:251` — the next step at `strong` named the wrong command.
fixed.** The line said the rules were waiting for "the record CI writes, which is the only one
that counts under `strong`". Either source counts at `strong`, so the line now names
`purlin:audit` there and keeps `purlin:test --remote` at `signed`.

**L11. `scripts/mcp/purlin/states.py:812` — a rule can meet the gate `strong` and sit in the
`passed` bucket.** A rule whose bar is `passed` does not have to meet the strong cell, so
`meets_gate` is true while `_bucket` returns `passed`. The board's headline can therefore read
more rules meeting the gate than the `Strong` tile counts. This is exactly what `tl-_rules.md`
item 6 asks for, so nothing was changed; it is listed because a reader will notice it. open by
design.

**L12. `references/review_criteria.md:109` and `docs/review-and-signing.md:121` — a blocking
rule nothing implements.** Both say `happy_path_only` "is blocking rather than advisory" for a
rule whose bar is `strong`. `checks.ADVISORY` holds it, `checks.blocks_ready` reads `BLOCKING`
alone, and `_strong_cell` never consults it, so a rule whose every proof is positive-only reads
`strong`. The reference and the docs agree with each other and disagree with the code. open —
Question Q10.

---

## Terms

**T1. `scripts/run/results.py:17`, `:51`, `references/formats/tests_format.md:103`,
`skills/test/SKILL.md:51` — the test results were said to count only at `passed`. fixed.**
They are the `local` source, and `records.counts_under` counts `local` at `passed` and at
`strong`; four surfaces, one of them the note written into every consumer's `.purlin/tests.md`,
said otherwise.

**T2. `scripts/init/scaffold.py:71` and `scripts/init/update.py:96` — the gate question called
`strong` CI's record. fixed.** The first sentence a new project reads disagreed with every page
it reads afterwards. Both now read "every rule has a record an audit wrote, at the minimum test
strength".

**T3. `scripts/mcp/purlin/gate.py:9` — the module docstring said `strong` needs "a record CI
wrote". fixed.**

**T4. `references/formats/tests_format.md:126` — "the record is CI's". fixed.** The record is
the audit's, whoever ran it.

**T5. `references/spec_quality_guide.md:240` — the `not run` row said `local` stops counting at
"`strong` or above". fixed.** It stops counting at `signed`.

**T6. `references/purlin_commands.md:116`, `references/drift_criteria.md:112`,
`docs/review-and-signing.md:245` — "Review list" for the single list. fixed.** The glossary
keeps `review list` for the pair and `Review` for the one list; a capitalised third spelling
reads as a third thing.

**T7. `references/glossary.md:192` and `scripts/init/update.py:102` — the record file name
dropped `[-<os>]`. fixed.** Three other places carry it.

**T8. `references/hard_gates.md` — "the model AI audit". fixed.** Two names for one thing in
one phrase.

**T9. `references/rule_examples.md:3` — "audit findings" in the loose English sense. fixed.**
`audit` means the level 2 run and nothing else.

**T10. `specs/mcp/drift.md:15` — "a project with no verification history". fixed.** An
inflection of the retired `verify` family that the whole-word check cannot see.

**T11. Five of the twelve Purpose sentences differed from the skill frontmatter. fixed.**
`purlin:spec`, `purlin:build`, `purlin:init`, `purlin:anchor` and `purlin:spec-from-code`
carried one sentence in `references/purlin_commands.md` and `README.md` and another in
`skills/<name>/SKILL.md`, though the glossary says there is one. The frontmatter's wording won,
because that is what the plugin loader reports.

**T12. `references/glossary.md:141` and `references/purlin_commands.md:5` — both promised the
`agents/purlin.md` table carries the purpose sentence. fixed.** That file has a routing table
and no purpose column.

**T13. Five spec proofs named keys and words the code does not emit. fixed.** An `audit` key in
the drift `qa` view (`specs/mcp/drift.md:50`) and in the feature rollup
(`specs/mcp/states.md:101`); the retired `never`/`high`/`medium` derivations
(`specs/init/scaffold.md:18`); the bar printed as `high` and the token `manual`
(`specs/run/records.md:79`); the `Run` and `Strength` columns (`specs/mcp/states.md:115`).

**T14. `scripts/review/sign.py:440`, `scripts/report/scan.py:182`,
`scripts/report/src/review.js:93` — three sentences for the empty list.** "Nothing is waiting
for a person.", "Review list: no rule needs a person." and "No rule is waiting for a person."
The Python pair is now one sentence in `board.needs_a_person`; the walk's own line and the
dashboard's are still their own. open.

---

## Elegance

**E1. `scripts/mcp/purlin/board.py:42` — `FLAG_LABELS` was read by nothing. fixed.** No surface
draws a `Held` card; the dashboard's two cards are `To sign` and `Stale`.

**E2. `scripts/ci/gate_check.py:74` and `:79` — the gate check kept its own copy of the strong
cell's review words and of `not audited`. fixed.** They now come from `states.REVIEW_WORDS` and
`states.NOT_AUDITED`, which is where the cell is computed.

**E3. `scripts/mcp/purlin/payload.py:80`, `scripts/review/brief.py:70`,
`scripts/review/sign.py:79` — three copies of `BRIEFS_DIR` and two of `SOURCES`. fixed.** All
three read the record module, which owns both.

**E4. `scripts/mcp/purlin/records.py:97` — `briefs_dir` was defined and called nowhere. fixed**
by making it the one way a brief path is built.

**E5. `scripts/mcp/purlin/status.py:275` — the person sentence was written out by hand and
hard-coded its plural, so one rule read `1 rules need a person`. fixed.** One sentence now,
`board.needs_a_person`, read by the report and the scan.

**E6. `scripts/mcp/purlin/status.py:145` and `scripts/report/scan.py:118` — `1 features` and
`1 signatures stale`. fixed** with `board.count_of`. `scripts/ci/gate_check.py:153` and
`scripts/review/static_checks.py:1855` still print `1 features`; both are job logs, so they are
left. open, partly.

**E7. `scripts/report/scan.py:196` — `_sorted` re-sorts a list the payload already sorted, with
its own copy of the bar order (`BAR_ORDER` beside `payload._BAR_ORDER`).** Two orderings that
must agree and nothing makes them. open.

**E8. `scripts/mcp/purlin/checks.py:31`, `scripts/mcp/purlin/specs.py:52`,
`scripts/mcp/purlin/results.py:58`, `scripts/mcp/purlin/states.py:94`,
`scripts/run/records.py:62`, `scripts/init/update.py:64` — seven module constants nothing
reads**: `FINDINGS`, `ORIGINS`, `RESULTS`, `SIGN_WORDS`, `BRIEFS_PATHSPEC`,
`CI_RECORDS_PATHSPEC`, `CI_BRIEFS_PATHSPEC`, `RECORD_FLAG_WAS`, `RECORD_SOURCE_WAS`. Some are
the declared vocabulary of a module and read as documentation; the two `# retired` ones in
`update.py` are left from migrations that no longer run. Left alone rather than deleted
piecemeal — Question Q5.

**E9. `templates/purlin.yml:53` — the job is named `audit`, and at the gate `passed` it does
not audit.** `audit` means the level 2 run. The job id is also the required-check name a branch
rule is configured against, so renaming it is not free. open — Question Q6.

---

## Clarity

Read in the order `docs/index.md` gives, as a developer who has never seen Purlin.

**C1. `docs/getting-started.md:171` — the `purlin:status` example printed a table that does not
exist. fixed.** It showed `Feature Rules Spec Tests Run`; the real header is
`Spec Rules Proofs Tests`. The prose under it described a `Spec` column, a `Run` column and a
`Strength` column, none of which the table has, and missed `Signable`.

**C2. `docs/regulated-workflow.md:86` — the gate check's four sections. fixed.** It prints six:
`Not passed`, `Partial`, `Weak`, `Not audited`, `To review`, `To sign`. The page also said
every line opens with `gate:`; the rules under a heading do not.

**C3. `docs/running-and-records.md:208` and `:239` — the record format at version 2. fixed.**
`purlin-record/3`, `schema_version` 3.

**C4. `docs/specs-and-anchors.md:77` and `docs/spec-from-code.md:63` — "re-tagging never stales
a signature". fixed.** The bar is bound into a signature, so re-tagging the bar does stale one,
which four other pages say.

**C5. `docs/spec-from-code.md:61` — "`low` is correct". fixed.** `low` is a retired risk value
and the example on the same page writes `[bar: passed]`.

**C6. `docs/design-in-specs.md:102` — a design re-export "puts them on the Review tab". fixed.**
A stale signature makes a rule signable, so it lands on Sign.

**C7. `docs/raising-the-gate-and-upgrading.md:84` and `skills/init/SKILL.md:53` — the upstream
job "opens a pull request or an issue". fixed.** It only ever opens an issue.

**C8. `docs/raising-the-gate-and-upgrading.md:112` — `Strength` joins the status table. fixed.**
The table and the board carry the same columns; `Strong` joins both at `strong`, and `Signable`
and `Signed` join both at `signed`.

**C9. `docs/running-and-records.md:290` — retention. fixed.** Three per feature per operating
system *per source*, and a local audit prunes as CI does.

**C10. `docs/running-and-records.md:29` — the passed cell's words, five of six. fixed.** `code
changed` was missing, though the same page relies on it twice.

**C11. `docs/team-workflow.md:164` — `weak` from "a free check found something". fixed.** A
blocking free check on the proof text holds the spec status at `drafted`, a level earlier; only
a test-body finding forces `weak`.

**C12. `docs/working-together.md:24` and `:59` — the artifact called `purlin-dashboard`.
fixed.** It is `purlin-dashboard-<os>`, one per job.

**C13. `README.md:70` — "CI clones Purlin at a pinned tag and runs the audit". fixed.** At
`passed` it runs the tests and writes nothing. The README is also the only page that mentions
the pin and never said how to move it; it now names `PURLIN_REF`.

**C14. `docs/how-purlin-works.md:139` — a stray duplicated `A`. fixed.**

**C15. `docs/running-and-records.md:452` — "the four words". fixed.** The section has five.

**C16. `docs/index.md:63` — "The record a CI run writes". fixed.** `purlin:audit` writes records
locally too, which the same page's table says two rows above.

**C17. `docs/specs-and-anchors.md:11` — "at Format-Version 11". fixed.** It is 12, and a number
in prose goes stale on every bump, so the page now names the line instead.

**C18. Four terms are used pages before they are defined. open.** `the free checks` first
appears in `docs/getting-started.md:188` and is defined in `docs/review-and-signing.md:104`;
`brief` first appears in `docs/how-purlin-works.md:16` and is defined on the same page, ten
pages later; `the protected branch` is used three times on page 1 and is defined in no docs
page, only in the glossary; `rollup` is used twice in `docs/working-together.md` and defined
nowhere in `docs/`. One clause at first use each.

**C19. `docs/getting-started.md:96` — the tutorial answers `passed` and then shows
`purlin:spec` writing `[bar: strong]` on all three rules, one page after
`docs/how-purlin-works.md:36` says a project at `passed` never sees a bar. open — Question Q7.**

**C20. Nine doc passages call Review and Sign "tabs" while describing what `purlin:sign` walks
in a terminal** (`docs/working-together.md:68` and `:141`, `docs/team-workflow.md:174`,
`docs/design-in-specs.md:102`, `docs/solo-workflow.md:139` and `:219`,
`docs/raising-the-gate-and-upgrading.md:210`, `docs/how-purlin-works.md:141` and `:146`), and
`docs/working-together.md:137` says "lists" four lines from `:141`'s "tab". open — Question Q8.

**C21. `docs/review-and-signing.md:32` and `:36` describe a `purlin:sign` header that
`sign.py:443` does not print.** The page shows two lines, `Review: 7 rules need a person,
across 3 features` and `Sign:   5 rules to sign`, and says the walk prints "each one's count
and its first five rows"; the command prints one line, `Review and Sign: <n> rules across <m>
features`, and no rows. open — Question Q9.

---

## Questions

Each is written for the user to answer. Nothing below was decided by this lane.

**Q1.** `specs/mcp/states.md` RULE-11 says the strong cell shows "the feature's latest test
strength" and `dev/plans/lanes/tl-_rules.md` item 2 says "the latest counting record's"; at the
gate `signed` a local audit newer than CI's therefore supplies the number the cell compares
against `min_strength`, though a local audit is only a preview there. Should the strength be
read from the latest *counting* record (the rule text changes, and a project whose newest
record is local shows `n/a` rather than a number nothing counts), or stay the latest record of
any source (nothing changes, and the `Strong` column can pass a rule on a measurement the gate
does not read)?

**Q2.** The pre-push hook runs `purlin_run.py --all --quick`, which commits
`.purlin/tests/` and `.purlin/tests.md`, so a push leaves the branch one commit ahead of the
remote the moment it succeeds. Should the hook run the tests without committing (a new
`--no-commit` arm on `--quick`, and the hook stops being a thing that writes to history),
should it keep committing and the docs say the extra commit is expected, or should the hook
stop running the tests at all and only refuse an agent's push?

**Q3.** `scripts/run/remote.py:89` calls `gh run watch --exit-status` with no run id, which
prompts interactively and errors when there is no terminal. Should the remote run look the run
up by its branch first (`gh run list --branch <run branch>`, with a short retry while the run
registers, which is more code and one more failure mode), or print the run URL and return the
way the Azure DevOps path already does (simpler, and the person waits themselves)?

**Q4.** A rule with a current hold whose tests are not passing reads `weak` with the reason
`not passed` in its strong cell and `held` in its signed cell, so it is on neither list.
`tl-_rules.md` item 2 says the strong cell reads `weak` with the one reason `not passed`
whenever the passed cell is not met; item 4 says a current hold makes both cells read `held`.
Should the hold win, so a held rule always reads `held` and always appears on Review, or should
`not passed` win, because a failing test is the work in front of the hold?

**Q5.** Nine module constants under `scripts/` are read by nothing:
`checks.FINDINGS`, `specs.ORIGINS`, `results.RESULTS`, `states.SIGN_WORDS`,
`records.BRIEFS_PATHSPEC`, `records.CI_RECORDS_PATHSPEC`, `records.CI_BRIEFS_PATHSPEC`,
`update.RECORD_FLAG_WAS`, `update.RECORD_SOURCE_WAS`. Should they all go (smaller modules, and
a reader loses the declared set of findings, origins and results that documents each module),
should only the two `# retired` ones in `update.py` go, or should they stay as the modules'
declared vocabulary?

**Q6.** The GitHub workflow's job is named `audit` (`templates/purlin.yml:53`), but at the gate
`passed` it runs the tests and audits nothing, and `audit` means the level 2 run everywhere
else. Should the job be renamed `purlin` (the check name changes, so every project that already
configured a required check has to change it), or should it keep the name and the glossary
admit that one job id is not the vocabulary?

**Q7.** `purlin:spec` writes `[bar: strong]` on every rule it drafts, including in a project at
the gate `passed`, where `docs/how-purlin-works.md` promises a reader never sees a bar, and the
tutorial in `docs/getting-started.md` shows the tag one page later. Should `purlin:spec` write
no bar tag at `passed` (a rule then takes the gate as its bar, and raising the gate silently
raises every untagged rule to `strong`), should it keep writing the tag and the docs say the
tag is written and inert until the gate is raised, or should it write `[bar: passed]` at the
`passed` gate?

**Q8.** Nine doc passages call `Review` and `Sign` "tabs" while describing the terminal walk,
and the same page uses "lists" four lines away. Should the rule be "list" for what
`purlin:sign` walks and "tab" only for the dashboard's two tabs (nine passages change), or
"tab" everywhere on the grounds that they are the same two things seen twice?

**Q9.** `docs/review-and-signing.md:32` documents a two-line `purlin:sign` header with a count
and five rows per list; `sign.py` prints one line and no rows. Should the doc be rewritten to
the one line the command prints, or should `sign.py` print the per-list counts and the first
rows the doc promises, which is more useful before a long walk and is a behaviour change?

**Q10.** `references/review_criteria.md:109` and `docs/review-and-signing.md:121` both say
`happy_path_only` blocks a rule whose bar is `strong`, and nothing in the code does that: it is
in `checks.ADVISORY` and no cell reads it. Should the block be implemented (a rule whose every
proof is positive-only stops meeting the gate at `strong`, which will turn a number of this
repository's own rules weak until each gets a negative case), or should both pages drop the
claim and leave `happy_path_only` advisory everywhere?
