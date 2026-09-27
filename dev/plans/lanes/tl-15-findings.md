# Lane 15: the second full review, after decision 31

What a second full read of the code, the references, the skills, the specs, the docs and the
design system found, against `dev/plans/three-levels.md` decisions 23 to 31 and
`references/glossary.md`. Line numbers are as of `0a6912803`, the stack tip this lane started
from.

Each finding is marked **fixed** where this lane made the change, or **open** where it is left.
Everything a decision does not settle is under **Questions** and was not decided here.

Counts: Logic 14, Terms 16, Elegance 13, Clarity 17. Questions 9.

Lane 13's ten questions and nine open items were checked first; what decision 31 answered and
what landed is under **Lane 13, closed out** at the end.

---

## Logic

The six scenarios the brief names, walked by hand through the code.

**L1. `scripts/run/purlin_run.py:170`, `:992`, `:1122` — `purlin:audit --tag` was still parsed,
and its arm could not run. fixed.** Decision 31 retired the flag and the `record/<name>` tags
with it. The flag was still accepted, and `_tag()` opened with `from records import
load_records, tag_record` while `scripts/run/records.py` defines no `tag_record` any more, so
the path raised `ImportError` the moment anyone used it. Two tests covered it and passed,
because both injected a fake `records` module that supplied `tag_record`. The flag, the arm,
the two tests and the docstring are gone; `--audit --tag` now joins the bad-invocation list.

**L2. `scripts/run/purlin_run.py:106` — a local audit told every reader at `signed` that it did
not count. fixed.** `AUDIT_IS_A_PREVIEW` printed `This record is local, so it counts at strong
and is a preview at signed, where the run on the protected branch is what a signature attaches
to.` Decision 31's first bullet withdraws exactly that. It was the one sentence a person reads
after an audit at the top gate.

**L3. `scripts/mcp/purlin/status.py:253` and `specs/mcp/states.md` RULE-58 — the next step at
`signed` named the wrong command and gave the withdrawn reason. fixed.** The line read `<n>
rules are waiting for the record CI writes, which is the only one that counts under signed.`
Lane 13 fixed the `strong` branch and left this one. RULE-58 pinned it, so the rule and PROOF-67
are rewritten: the line names `purlin:audit` at `strong` and at `signed`, because a record
either source wrote counts at both, and names `purlin:test --remote` where `trust` is `remote`,
which is the one setting that asks for a `ci` run before a signature.

**L4. `scripts/mcp/purlin/status.py:241` — the drafted-rule line named a check nothing makes.
fixed.** It read `%d rules have no proof that clears the free checks.` Decision 31 made `ready`
mean the rule has a proof and nothing more; `spec_status()` reads the proof list alone.

**L5. Eight places said a git-host file-path rule keeps `.purlin/records/ci/` honest.
fixed.** `scripts/mcp/purlin/records.py:42` and `:164`, `scripts/run/records.py:16`,
`scripts/run/purlin_run.py:1106`, `scripts/review/brief.py:75`, `scripts/init/update.py:105`
and `:633`, `references/hard_gates.md:86`, `references/formats/record_format.md:130` and
`templates/purlin.azure-pipelines.yml:17`. Decision 31 removed every branch ruleset, and
`scripts/ci/gate_check.py:152` already said the opposite in the same tree: no branch rule stands
behind the folder, and the tag run's provenance check is what finds a file a person wrote there.
Two mechanisms were documented for one fact and only one of them exists.

**L6. `scripts/run/records.py:309` — any tag push was read as the signing tag run. fixed.**
`is_a_tag_run()` matched `refs/tags/` alone, so a project's own release tag would have made the
`--ci` arm write nothing and print `Tag run: nothing is written.` `SIGNED_TAG_PREFIX` was
defined in the same file for exactly this and read by nothing. It now matches
`refs/tags/signed/`.

**L7. `scripts/mcp/config_engine.py:72`, `:126`, `:138` and `scripts/hooks/refresh_digest.py:229`
— four `open()` calls in text mode with no encoding. fixed.** Three of them read and write
`.purlin/config.json`, so a Windows consumer read the project's one setting through cp1252.
`tl-_rules.md` "Code" requires `encoding='utf-8'` on every `open()`.

**L8. `scripts/review/sign.py:841` — a signature from someone off the signer list is refused at
the gate `strong`.** `if signers and email not in signers` runs at both gates.
`signatures.counts()` returns `(True, '')` for any gate but `signed`, and
`references/hard_gates.md:148`, `docs/team-workflow.md:29` and `docs/review-and-signing.md:232`
all say the signer list is not read below `signed`. A project that set a list early refuses a
signature it would then have counted. open — **Q1**.

**L9. `scripts/review/sign.py:859` — `--batch` and a bare feature sign nothing at `strong`.**
Both read `payload['sign_list']`, which `payload._sign_entry` builds only at the gate `signed`,
so at `strong` they print `nothing here needs a signature` even for a rule whose strong cell
reads `manual test`. Naming the rules explicitly still works. Carried over from lane 13 L9,
unchanged. open — **Q2**.

**L10. `scripts/review/sign.py:413` — the tag can be written over rules no `ci` run covered
under `trust: remote`.** Trust is read by `purlin:sign` and by no cell, so `meets_gate` does not
know about it. A rule whose bar is `passed` needs no signature at `sign_at: strong`, so it meets
the gate `signed` on a local run alone, and `tag_if_met` writes `signed/<version>` over it.
Decision 31 says only that signing is refused. open — **Q3**.

**L11. `scripts/mcp/purlin/drift.py:492` — a free scan's answer reaches a surface.**
`purlin:drift qa` carries `rules_without_a_negative_case`, computed by
`checks.names_a_negative_case` off the proof text. `references/glossary.md:64` says a hint is
"read by no cell and no surface", and `references/review_criteria.md:12` says nothing a scan
reads appears on the board. `specs/mcp/drift.md` RULE-14 and PROOF-17 pin the key. open — **Q4**.

**L12. `scripts/run/records.py:340` — `no_commit_line()` says "Tag run" whatever the ref.**
`commits_here()` is false on a host for any ref that is neither a run branch nor the signing
tag, and the line printed then reads `Tag run: nothing is written.` The workflow triggers on
those two refs only, so the case cannot arise from a file `purlin:init` writes; a hand-edited
workflow would print a sentence that is not true. open, named here rather than fixed because the
truthful line needs a second string and a proof.

**L13. `scripts/run/workflow.py:214` — init still refuses to write a workflow over a branch
rule that no longer exists.** `prerequisites()` checks that the protected branch is on the
remote, and its own comment gives the reason as "a signature counts only on a commit that
reaches it". The workflow triggers on `run/**` and `signed/**`, neither of which is that branch.
open — **Q5**.

**L14. `scripts/run/records.py:435` — `is_fork()` is unreachable.** It reads
`pull_request.head.repo.fork` out of `GITHUB_EVENT_PATH`, and `specs/run/records.md` PROOF-18
now asserts that the rendered workflow names neither `pull_request` nor `fork`, so no Purlin run
can carry that object. One call site, at `records.py:399`. open — **Q6**.

---

## Terms

**T1. `references/purlin_commands.md:23` — "Both sources count at `strong`; only `ci` counts at
`signed`." fixed.** Withdrawn by decision 31's first bullet, and contradicted by
`references/hard_gates.md:94` two files away.

**T2. `references/hard_gates.md:3` — "The gate is the one project setting: what CI must see
before a change can merge." fixed.** The same file's "Branch rules" section says there are none
and that the tag is the marker. Eight more places carried the merge frame:
`scripts/ci/gate_check.py:2` and `:346` (the second is `--help` output),
`scripts/mcp/purlin/gate.py:4`, `references/purlin_commands.md:85`,
`specs/skills/skill_init.md:15` and `:23`, `specs/init/scaffold.md:4`,
`tools/QA/purlin-qa-report.md:118`, `tools/PM/purlin-anchor-userstories.md:146`. The two spec
lines had also gone stale against the question `scaffold.py:70` asks.

**T3. The pull request comment and the dashboard artifact are named as live surfaces in six
modules and four documents. fixed.** `scripts/mcp/purlin/board.py:3` and `:10`,
`scripts/report/scan.py:11`, `scripts/report/src/app.js:47`, `dev/build_report.py:6`,
`specs/mcp/states.md` RULE-49, `specs/dashboard/purlin_report.md:4`,
`tools/QA/purlin-qa-report.md:87`, `tools/PM/purlin-anchor-userstories.md:139` and
`design/readme.md:8`. The QA tool told a reader to link to an artifact nothing builds; the PM
tool described a CI run on a pull request and after a merge, neither of which happens.

**T4. `scripts/review/brief.py:82` — the brief's fourth layer and its printed heading read
`model review`. fixed.** The glossary defines **AI audit**, the dashboard prints `The AI audit
settled the question.` and every docs page says AI audit. `LAYERS`, `_model_review`, the
`Model review` heading, `specs/review/brief.md` PROOF-2, PROOF-3, PROOF-4 and PROOF-20,
`specs/mcp/states.md` PROOF-17 and `dev/test_brief.py` now say AI audit. The glossary's own
definition line glossed it as "the model review inside an audit" and now does not.

**T5. `specs/dashboard/purlin_report.md:73` — the spec and the code disagreed about a rendered
sentence. fixed.** PROOF-15 asked the screen to read `The model review settled the question.`;
`scripts/report/src/rule.js:66` prints `The AI audit settled the question.`, which is what
`dev/test_purlin_report.py:726` asserts. The proof was a claim nobody ran.

**T6. Seven places still said "free checks" or "free checker". fixed.**
`scripts/mcp/purlin/states.py:87` and `:572`, `scripts/mcp/purlin/payload.py:404`,
`scripts/review/static_checks.py:1034` and `:1095`, `scripts/run/purlin_run.py:975` and
`:1068`. The `static_checks.py:1034` one reaches a brief as a sentence. Decision 31 folded the
free checks into the audit and made their output hints the free scans wrote.

**T7. `docs/design-in-specs.md:71` and `tools/PM/purlin-anchor-userstories.md:116` — the finding
name `implementation_coupling` printed in shipped prose. fixed.** Decision 31: the names leave
every surface.

**T8. `tools/QA/purlin-qa-report.md:83`, `:90` and `:94` — "free-check findings", "the model
review", "how many are `high`" and "read it beside the findings". fixed.** `high` is a retired
bar level; the tool asked for a count of a tag no rule carries.

**T9. `scripts/mcp/purlin/states.py:80`, `docs/regulated-workflow.md:242` and
`docs/dashboard.md:239` — `tab` for what `purlin:sign` walks. fixed.** Decision 31 gives the
walk `list` and reserves `tab` for the dashboard;
`docs/review-and-signing.md:12` states the rule.

**T10. `skills/spec-from-code/SKILL.md:66` — "`low` is correct". fixed.** `low` is a retired
risk value and the skill writes `[bar: passed]` on the same page. Lane 13 fixed the docs page
and not the skill. The same sentence also said re-tagging never stales a signature; the bar is
bound into one.

**T11. `references/glossary.md:195` and `:199` — two retired rows pointed at retired things.
fixed.** `validated/<name>` said to use `record/<name>` tags, which decision 31 retired, and
`Pages` said to use the `purlin-dashboard` build artefact linked from the pull request comment,
which decision 31 retired twice over.

**T12. `references/drift_criteria.md:110`, `references/glossary.md:41`,
`references/hard_gates.md:101`, `docs/regulated-workflow.md:65`, `agents/purlin.md:56` and
`specs/mcp/states.md` RULE-7 — "CI clears it on the next run". fixed.** Any run clears
`code changed`, and most projects have no CI.

**T13. `scripts/mcp/purlin/server.py:82` — "since the last verification". fixed.** An inflection
of the retired `verify` family that the whole-word check does not see; drift reports since the
last record.

**T14. `design/readme.md:3`, `:29`, `:35` and `:42` — "toolkit", "CI writes the notes during
verify", "Two sign-offs went stale" and "The file Purlin writes when you verify". fixed.** The
file is the authority on the voice, and three of its four worked examples taught copy the
product no longer makes.

**T15. `design/components/data/ScorePanel.prompt.md`, `ScorePanel.jsx` and `data.card.html` —
the two retired grading scores. fixed.** Proof design and proof integrity were the component's
whole stated purpose and two of the specimen table's five columns.

**T16. `specs/review/signatures.md` PROOF-15 and PROOF-20 — `sign_at: medium`. fixed.** A
retired value that `gate._read_sign_at` maps rather than accepts, so the proofs and
`dev/test_signatures.py:645` were exercising the migration table. RULE-6 also called the audit's
observations its findings.

---

## Elegance

**E1. `scripts/run/purlin_run.py` `--tag` and `_tag()`. fixed.** See L1: dead and broken.

**E2. `scripts/run/results.py:309` `results_paths()`. fixed.** One definition, no readers; the
two callers that could want it each build their own list. `CI_PATHSPEC` went with it, its only
reader.

**E3. `scripts/mcp/purlin/status.py:205` `NO_AUDIT`. fixed.** Defined and read by nothing; the
words come from `states.NOT_AUDITED`.

**E4. `scripts/run/records.py:81` `SIGNED_TAG_PREFIX`. fixed** by making it the thing
`is_a_tag_run()` matches, which is what it was for. See L6.

**E5. `scripts/run/purlin_run.py:1134` and `:1156` — the two CI commit subjects were written out
a second time. fixed.** `results.COMMIT_SUBJECT` and `records.RECORD_SUBJECT` own them; the
`--ci` arm carried its own copy of each literal, and `specs/run/test_results.md` RULE-8 pins
only one of the two writers.

**E6. `scripts/init/update.py:100` `RECORDS_README` duplicates `scripts/init/scaffold.py:152`
`_READMES['.purlin/records']`.** Two texts for one file, written by two commands, and nothing
makes them agree; they had already drifted apart on who keeps `ci/` honest. Deduplicating means
`update.py` importing `scaffold`, which pulls in `workflow` and `mutation` at module scope and
changes how the tests isolate the module, so it is named rather than done. open.

**E7. `scripts/report/scan.py:196` `_sorted` re-sorts a list the payload already sorted, with
its own `BAR_ORDER` beside `payload._BAR_ORDER`.** Carried over from lane 13 E7, unchanged.
open.

**E8. `scripts/mcp/purlin/checks.py:31`, `scripts/mcp/purlin/specs.py:52`,
`scripts/mcp/purlin/results.py:58`, `scripts/mcp/purlin/states.py:94`,
`scripts/init/update.py:64` — seven module constants nothing reads.** Lane 13 listed nine and
asked Q5; decision 31 answered "the nine unread module constants the review named are deleted"
and lane 14A deleted two of them (`records.BRIEFS_PATHSPEC` and one of the `CI_*` pathspecs).
`FINDINGS`, `ORIGINS`, `RESULTS`, `SIGN_WORDS`, `RECORD_FLAG_WAS` and `RECORD_SOURCE_WAS`
survive. open — **Q7**.

**E9. `scripts/mcp/purlin/checks.py:65` to `:73` — four constants named for retired free checks.**
`NO_EXPECTED_VALUE`, `VAGUE_VERB`, `MISSING_TRIGGER` and `TIER_MISMATCH`. Their values are the
plain sentences the audit is handed; only the identifiers carry the retired names. open — **Q8**.

**E10. `scripts/review/static_checks.py:7` and the whole of `specs/review/static_checks.md` —
the scans' output is still called findings and each finding still has a name.** The module
docstring lists `tautology`, `assert_true_literal`, `no_assertion`, `bare_except`,
`logic_mirroring` and `mock_of_target` as its vocabulary, and fourteen rules and twenty proofs
in the spec assert that a case "is reported `tautology`". No name reaches a surface, which is
what decision 31 asked for, but the module's own words are the retired ones. open — **Q8**.

**E11. `scripts/mcp/purlin/board.py:8` — the board's strings are mirrored by hand into
`scripts/report/src/board.js`.** The docstring says so, and `specs/mcp/states.md` RULE-49
asserts they agree, but what makes them agree is a person editing two files. open, named
because it is the largest remaining "two copies of one answer" in the tree.

**E12. Six spec proofs pin an implementation detail rather than an observable.**
`specs/run/run_script.md` PROOF-61 (`_ci_review()`) and PROOF-65 (`_no_breaks("passed")`),
`specs/run/records.md` PROOF-12 (`_azure()`), `specs/run/mutation.md` PROOF-21 (mangled mutant
symbol names) and PROOF-22 (`ARM_TIMEOUT` rather than `--arm-timeout`),
`specs/init/update.md` PROOF-11 (greps `update.py`'s own source for an assignment), and
`specs/dashboard/purlin_report.md` RULE-7, which names `scripts/mcp/purlin/board.py` inside the
rule text. Each one breaks on a rename that changes no behaviour. open.

**E13. `scripts/run/purlin_run.py:93` — the arm is `--quick` and nothing else calls it that.**
It is what `purlin:test` runs, and it writes and commits the test results. open — **Q9**.

---

## Clarity

Read in the order `docs/index.md` gives, as a developer who has never seen Purlin. The bare
workflow is the story on every gate page, and the remote runner appears in one section per page
under its two reasons: that held everywhere.

**C1. `docs/running-and-records.md:94` — "Raising the gate to `strong` turns the breaks on,
locally and in CI". fixed.** Line 169 of the same page says the breaks run on your machine and
nowhere else, and `templates/purlin.yml:24` says no breaks run there.

**C2. `docs/running-and-records.md:251` and `references/formats/record_format.md:116` — a proof
status `skip` the code never writes. fixed.** `references/formats/proofs_format.md:149` says a
skipped test writes no entry at all, and `purlin_run.py:707` reads `pass`, `fail` or `missing`.

**C3. `docs/running-and-records.md:386` — the run branch's commit was only the `strong` one.
fixed.** At `passed` it is `purlin: tests at <sha7>` carrying `.purlin/tests/ci/`, which the
table four lines above says.

**C4. `docs/raising-the-gate-and-upgrading.md:142` — "Eight migrations". fixed.**
`update.MIGRATIONS` has ten; `rule-tags` and `record-folders` were missing, and `rule-tags` is
the one that rewrites a 0.9.5 project's risk tags.

**C5. `docs/review-and-signing.md:178` — a `→ Run: purlin:status` line the walk does not print.
fixed.** `tag_if_met` prints `No tag: <n> of <m> rules do not meet the gate <gate>.` and stops.

**C6. `references/review_criteria.md:134` — "Anything but `yes` on a rule whose bar is `strong`
makes the strong cell read `unsettled`". fixed.** `states._outstanding` returns nothing when the
brief's `ai_review` is `not available`, and the same file says so at line 89.

**C7. `docs/regulated-workflow.md:22` — "`purlin:test`, and the same tests on CI". fixed.** The
column is "the command that answers it", and naming CI in it on the page whose second paragraph
says the whole of it runs on one machine reads as a second requirement.

**C8. `docs/getting-started.md:41` — "the workflow `purlin:init` writes" on page two, before
any page has said most projects get none. fixed** with the clause that names the two projects
that do.

**C9. `docs/working-together.md:155` — "The gate that decides what CI must see". fixed.**

**C10. `scripts/ci/gate_check.py:181` — "does not pass the branch", twice. fixed.** Nothing
Purlin writes passes or fails a branch; the job says whether the gate was met.

**C11. `skills/audit/SKILL.md:99` and `skills/build/SKILL.md:103` — `→ Next: run git push.`
fixed.** `→ Next:` is the one line `sync_status` owns and it never says that; every other row of
the same table says `→ Run:`. Both now read `→ Run: git push`, which is the form
`references/glossary.md:119` names.

**C12. `references/purlin_commands.md:104` — the `purlin:test` row did not say where a remote
run's results come home. fixed**, as the brief asked: the row now names
`.purlin/tests/ci/<feature>.json`.

**C13. `references/purlin_commands.md:134` — "the way the hook shims do". fixed.** Decision 31
removed the shims; nothing runs at push or commit time.

**C14. `references/hard_gates.md:114` — `signed/*` where the workflow globs `signed/**` and
every other page writes `signed/<version>`. fixed** to `signed/<version>`, the form a reader can
act on. The two templates keep their globs, which are what the git host needs.

**C15. `docs/running-and-records.md:214` and `:244` — the record's schema version stated as a
number in prose, twice.** `references/formats/record_format.md` is the authority and carries the
number; lane 13's C17 established that a number in prose goes stale on every bump. Left because
the second one is a field table restating the contract, where the number is the content. open.

**C16. `references/hard_gates.md:137`, `docs/regulated-workflow.md:289` and
`skills/init/SKILL.md:188` — "Branch rules" as a section heading.** The heading names a retired
thing, and the section under each says there are none and why. Left: a reader arriving with the
question needs the word to find the answer. open.

**C17. `RELEASE_NOTES.md:179` — "the signature format (from `approval_format.md`)".** A retired
spelling in ordinary prose rather than in the retirement table. The file is the migration record
and is excluded from the vocabulary check, so it is named rather than changed. open.

---

## Questions

Each is written for the user to answer. Nothing below was decided by this lane.

**Q1.** `scripts/review/sign.py:841` refuses a signature from an email that is not on `signers`
at both gates, but `signatures.counts()` counts a signature from anyone below `signed`, and
`references/hard_gates.md`, `docs/team-workflow.md` and `docs/review-and-signing.md` all say the
signer list is not read below `signed`. Should the refusal move behind `gate == 'signed'`, so a
project that set a list early can still take the signature that clears a `manual test` or an
`unsettled` cell from anyone (the code then matches four documents, and a team that set a list
at `strong` meaning it to bind loses that), or should the refusal stay and those four places say
instead that a signer list, once set, binds at every gate (nothing changes, and `counts()` and
`sign.py` still answer the same question two ways)?

**Q2.** `purlin:sign <feature>` and `purlin:sign --batch` read `sign_list`, which the payload
builds only at the gate `signed`, so at `strong` both print `nothing here needs a signature` even
where a rule's strong cell reads `manual test` and a signature would clear it. Naming the rules
explicitly still works. Should `signable()` fall back to the Review list at `strong`, so a bare
feature and `--batch` sign what a person could sign there (one more branch, and `--batch` at
`strong` starts writing files a bare signature says are not required), or should both print what
the gate does offer and name `purlin:sign <feature> RULE-N` (a message change only, and the
terminal stops reading as a dead end)?

**Q3.** `trust` is read by `purlin:sign` and by no cell, so `meets_gate` does not know about it.
A rule whose bar is `passed` needs no signature under `sign_at: strong`, so under
`trust: remote` it meets the gate `signed` on a local run alone and `purlin:sign` writes
`signed/<version>` over it. Should `trust: remote` also hold the passed cell of every rule to a
`ci` source, so the tag means what the setting says (the cell gains a second thing to read, and
a project that turns trust on sees every rule go back to `not run` until a remote run covers it),
should `tag_if_met` alone refuse while any rule's tests have no `ci` run (the cells are
untouched and the tag carries the whole claim), or should it stay as decision 31 wrote it, with
trust binding signing alone?

**Q4.** `purlin:drift qa` carries `rules_without_a_negative_case`, which is a free scan's answer
read straight off the proof text, while the glossary says a hint is read by no cell and no
surface and `references/review_criteria.md` says nothing a scan reads appears on the board.
`specs/mcp/drift.md` RULE-14 and PROOF-17 pin the key. Should the key go, so the audit's
judgment is the only route a scan's answer takes to a person (the rule and its proof change, QA
loses a list it can act on without running an audit), or should it stay and the glossary say
that drift is the one surface a scan reaches, because drift is a report about the specs rather
than about the evidence?

**Q5.** `scripts/run/workflow.py:214` refuses to write a workflow when the protected branch is
not on the remote, and its comment gives the reason as a signature having to reach that branch.
The workflow triggers on `run/**` and `signed/**`, neither of which is that branch. Should the
protected-branch leg of `prerequisites()` go, so init checks the remote and the host and nothing
else (one fewer reason for init to stop, and a project whose default branch is not yet pushed
gets its workflow), or should it stay because `signatures.is_ancestor` still asks for that branch
under `signed` and a project with no such branch will fail the gate later?

**Q6.** `scripts/run/records.py:435` `is_fork()` reads `pull_request.head.repo.fork` out of
`GITHUB_EVENT_PATH`, and `specs/run/records.md` PROOF-18 asserts that the rendered workflow names
neither `pull_request` nor `fork`, so no Purlin run can carry that object. Should `is_fork()` and
its one call site go (less code, and a fork's read-only token then fails the commit with the git
host's own error rather than Purlin's one-line explanation), or should it stay as the guard for a
workflow somebody hand-edited?

**Q7.** Six module constants under `scripts/` are still read by nothing: `checks.FINDINGS`,
`specs.ORIGINS`, `results.RESULTS`, `states.SIGN_WORDS`, `update.RECORD_FLAG_WAS` and
`update.RECORD_SOURCE_WAS`. Decision 31 said "the nine unread module constants the review named
are deleted" and three went; these six were not reached. Should all six go now (smaller modules,
and a reader loses the declared set of findings, origins and results that documents each one),
or should only the two `# retired` ones in `update.py` go, which are left from migrations that no
longer run?

**Q8.** The free scans' internal vocabulary is still the retired one: `checks.py` names four
constants `NO_EXPECTED_VALUE`, `VAGUE_VERB`, `MISSING_TRIGGER` and `TIER_MISMATCH`,
`static_checks.py` calls its output findings and emits `tautology`, `no_assertion`,
`bare_except`, `logic_mirroring` and `mock_of_target` as `check:` keys, and
`specs/review/static_checks.md` asserts each name in fourteen rules and twenty proofs. No name
reaches a surface, which is what decision 31 asked for. Should the internal names be renamed too
and the spec rewritten to describe what each scan sees rather than what it is called (twenty
proofs change and every one of this repository's own static_checks signatures stales), or should
the names stay as the module's private keys and the glossary say that the retirement covers what
a person reads and not what a dict key spells?

**Q9.** `purlin_run.py`'s first arm is `--quick`, and it is what `purlin:test` runs: it runs the
tagged tests, writes `.purlin/tests/` and `.purlin/tests.md` and commits them. Every spec, skill
and doc around it says "test"; only the flag says "quick". Should it become `--test` (the usage
line, eight sites in `purlin_run.py`, `specs/run/run_script.md` RULE-1 and PROOF-1, the shell
e2e fixtures and `skills/test/SKILL.md` change, and any consumer script naming the flag breaks),
or should it keep the name and the glossary say that the three arms are `--quick`, `--audit` and
`--ci` whatever the commands are called?

---

## Lane 13, closed out

Decision 31 answered lane 13's questions; this is what landed.

| Lane 13 | Decision 31 | State |
|---|---|---|
| Q1 strength from the latest counting record | local counts everywhere, so every record counts | moot; `payload._latest` is right |
| Q2 the pre-push hook commits during a push | the hook is removed | landed; `update._apply_hooks` removes it |
| Q3 `gh run watch` with no id | find the run by branch, retried | landed; `remote.find_run` |
| Q4 a hold versus `not passed` | a hold wins | landed; `states._strong_cell` reads holds first |
| Q5 nine unread constants | delete them | three of nine; six left — **Q7** |
| Q6 the workflow job named `audit` | the job is named `purlin` | landed; `templates/purlin.yml:56` |
| Q7 `purlin:spec` writing a bar at `passed` | writes none at `passed` | landed in `skills/spec`; `skills/spec-from-code` still writes `[bar: passed]` unconditionally, which is what it is for |
| Q8 tab versus list | `list` for the walk, `tab` for the page | landed except three places — T9, now fixed |
| Q9 the `purlin:sign` header | one line, `Review: <n> rules. Sign: <n> rules.` | landed in both the code and the page |
| Q10 `happy_path_only` blocking | the free checks fold into the audit | landed; no page claims it blocks |

Lane 13's open items L5, L6, L12, T14, E1 and C18 to C21 are closed by the same table or by the
fixes above. L8, L9, E7 and E8 survive and are L8, L9, E7 and E8 here.
