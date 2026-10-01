# The reading pass, decision 119

One agent, on local `main`, after integration. It read the references, the six formats, the
agent definition, the ten skills, `README.md`, the ten pages under `docs/`, the 0.10.0 section of
`RELEASE_NOTES.md`, `CLAUDE.md`, `templates/`, `.claude-plugin/`, `design/readme.md` and the deck
source, each against the ones before it, the code under `scripts/` and the specs. No spec and no
file under `scripts/` was edited. Nothing was pushed, tagged, signed or audited, and the deck was
not published. Line numbers are those of the files after the fixes.

| Heading | Found | Fixed | Left |
|---|---|---|---|
| 1. Stale references | 16 | 9 | 7 |
| 2. Conflicting instructions | 22 | 21 | 1 |
| 3. Duplication | 8 | 5 | 3 |
| 4. Convoluted prose | 24 | 15 | 9 |
| 5. The deck | 7 | 4 | 3 |
| All | 77 | 54 | 23 |

## 1. Stale references

- `CLAUDE.md:94` cited `purlin_version` RULE-8, which that spec does not carry (its rules are 1, 2, 3, 5, 6, 12, 14 and 16). Fixed: the runtime read cites RULE-2, and the clause about docs naming the `VERSION` file carries no rule id, since no rule holds it.
- `references/drift_criteria.md:150` said the git host is read from the remote each time. Purlin reads no git host since decision 119; only the project's name is read. Fixed.
- `skills/init/SKILL.md:17` said the same of the git host. Fixed.
- `design/readme.md:24` gave copper to `gate names`. There is no gate. Fixed: the words are taken out.
- `design/readme.md:48` listed `gates` among machine text. Fixed: `cell words`, as `references/writing_style.md` has it.
- `references/review_criteria.md:159` said the spot tests' languages are the ones `Purlin's runner supports`. Purlin has no runner, and it also runs Go. Fixed: the clause is taken out.
- `references/review_criteria.md:160` said the checks run over `roughly 2,300 tests` and that the count of findings is reported in the release notes. This repository's last run tied 820 test comments, and the release notes report no such count. Fixed: the number and the promise are taken out.
- `RELEASE_NOTES.md:27` listed as cut `mutation testing, purlin:export, the gate, the release step, .purlin/tests.md`. None of them was in 0.9.5, and the section says it is what differs from 0.9.5. Fixed: the line names what 0.9.5 had, `drift's role views, setup's questions but one, and most settings`.
- `skills/status/SKILL.md:7` said `how many rules reached each step`. A rule has two cells and no steps. Fixed: `how many rules pass their tests`.
- `scripts/mcp/purlin/frameworks.py:36` suggests `python3 -m pytest --ignore=mutants ...`. The folder `mutants` is what a mutation tool writes, and mutation testing is cut (decision 109). `specs/run/run_script.md:66`, `:70` and `:72` hold the same words, and five doc lines quote them correctly. Left for the owner: take `--ignore=mutants` out of the suggested command, the three proofs, their tests and the five quotes in one commit.
- `scripts/review/targeted_break.py:45` prints `The audit stopped: <file> changed while a break ran.` The glossary's word is planted bug. `skills/audit/SKILL.md` and `docs/running-and-evidence.md` quote the line as printed. Left for the owner: print `changed while a bug was planted`, and correct the two quotes.
- `scripts/mcp/purlin/payload.py:263` writes `remote_url` into the dashboard's data, and its comment at `:849` says the dashboard turns it into links to the git host. No page source reads it: the links went with decision 109. `specs/mcp/states.md:36` names the key. Left for the owner: take the key out, with RULE-27's list and the schema number, or keep it and correct the comment.
- `scripts/mcp/config_engine.py:22` keeps `min_strength`, `gate`, `mutation_engine`, `audit_parallel`, `ci` and `project_name` among the keys the upgrade takes out. They are keys of 0.10 builds, and the upgrade is from 0.9.5 only (decision 109). `specs/mcp/config_engine.md:40` proves it with `gate` and `mutation_engine`. Left for the owner: keep the 0.9.5 keys alone, and write PROOF-50 with two of them, such as `pre_push` and `digest`.
- `.claude-plugin/plugin.json:4` and `.claude-plugin/marketplace.json:13` say `proof descriptions say what would demonstrate them`, and `plugin.json:27` keeps the keyword `sync`. Left for the owner: `specs define rules, proofs say how each is shown, tests prove it`, and drop `sync`. Both files are in the scope of the spec `install`.
- `docs/running-and-evidence.md:510` clones Purlin at the tag `v0.10.0`. The release writes `signed/0.10.0`, and no `v0.10.0` exists. Left for the owner, as the handoff already lists: push a `v0.10.0` tag with the release, or change the example to the tag that exists.
- `references/review_criteria.md:160` still says the checks run over Purlin's own tests before a release. The handoff lists the measuring of the audit as not run. Left for the owner: run it before the release, or take the sentence out.

## 2. Conflicting instructions

`purlin:test on <System>` is settled this way: it is an instruction, not a command line. The run
script takes no system. The words are met by `purlin:test` on a machine of that system or by the
project's own run there. Where a line is quoted it reads as the code prints it, `run purlin:test
on <systems>` in `Left to do` and `purlin:test on <System>` in the sign-off's refusal. Where a
skill names the next step it writes `→ Run purlin:test on <System>`, with no colon after `Run`,
and points at `skills/test/SKILL.md`, Step 5.

- `references/evidence_and_signoff.md:75` gave the command of `to_test_remote` as `purlin:test on <System>`; the code and `package_format.md` give `run purlin:test on <systems>`. Fixed.
- `references/evidence_and_signoff.md:84` no page said what the words mean. Fixed: one paragraph says it is an instruction and what meets it.
- `references/evidence_and_signoff.md:122` named it as a run beside `purlin:test --all --commit`. Fixed: it is the same instruction as in `Left to do`.
- `skills/status/SKILL.md:107` read `→ On <systems>: purlin:test`, a third spelling. Fixed.
- `skills/sign/SKILL.md:80` listed it among the commands to run when the person asks. Fixed: it points at the test skill's Step 5.
- `skills/sign/SKILL.md:183` put it under `→ Run:` with two real commands. Fixed: a row of its own.
- `skills/test/SKILL.md:112` quoted the run's line and did not say it is no command. Fixed.
- `docs/running-and-evidence.md:228` the same. Fixed: one sentence.
- `references/glossary.md:55` listed the kinds of `Left to do` `as printed` and left out `slow proofs to run`, which the code prints between `to test` and `to test on <systems>`. Fixed.
- `skills/status/SKILL.md:106` had no next step for `<n> slow proofs to run`. Fixed: `→ Run: purlin:test --all`.
- `skills/sign/SKILL.md:107` said a stop shows `What the audit found` where the audit read the rule. The code and `docs/sign-off.md` show it only where the rule is weak. Fixed.
- `docs/audit.md:38` said `strong means a bug was planted and caught`. An anchor's rule gets no bug, and a proof may get none, and both can read `strong`; the reference says `strong` means the model's part ran. Fixed: `strong needs the AI`.
- `references/glossary.md:130` said the roles are product, developer and QA and there are no others, while `docs/working-together.md:9` and the deck say `Purlin has no roles`. Fixed in the glossary: a role is a word for who does the work, and Purlin gives no role a permission.
- `references/formats/evidence_format.md:220` said a rule line of the fingerprint ends in a tag and a proof line adds `@manual` and `@env`. The code writes no tag on a rule line and adds `@slow` on a proof line. Fixed, as wording; the format's number stays 9, since no file changes.
- `docs/sign-off.md:13` said the package holds who signed. The package holds no signer; each sign-off is a file beside it (`package_format.md`). Fixed.
- `skills/test/SKILL.md:21` said `--all` runs every feature and left out the slow proofs the command reference names. Fixed.
- `skills/audit/SKILL.md:24` said `--commit` commits the evidence; it makes both commits, the work and the evidence. Fixed.
- `docs/running-and-evidence.md:28` the same line. Fixed.
- `README.md:30` said `no git hook` where the `touches` slide says `no git hook, no background job and no pipeline`. Fixed.
- `docs/getting-started.md:21` the same. Fixed.
- `skills/init/SKILL.md:42` the same. Fixed.
- `scripts/review/sign.py:638` a hand check's stop shows the rule, its proofs, the results and a weak finding, and not the last note. Decision 110 says a hand check always shows its last note, and the status and the dashboard do. Left for the owner: add the last note to the stop, with a rule and a proof in `signatures`, or leave the walk as it is.

## 3. Duplication

- `skills/test/SKILL.md:55` restated the exit codes, in other words than `references/purlin_commands.md`. Fixed: it points there.
- `skills/audit/SKILL.md:62` the same. Fixed.
- `skills/test/SKILL.md:99` held a table of the passed cell's words, which `references/spec_quality_guide.md`, "When a rule is stuck", defines. Fixed: it names the words and points there.
- `skills/anchor/SKILL.md:40` restated the skip with `nothing to check:`. Fixed: one sentence pointing at "A good anchor".
- `skills/anchor/SKILL.md:95` restated where a rule of this project alone goes, word for word from `anchor_format.md`. Fixed: it points at "Editing a remote anchor".
- `references/formats/evidence_format.md:275` and `references/commit_conventions.md:38` both describe the two commits of a run in full, and `skills/test/SKILL.md:70` a third time. Left for the owner: keep the printed lines in the format, since it is a contract, and have the skill point at `commit_conventions.md`.
- `skills/audit/SKILL.md:43` lists the six spot tests and the three steps that `references/review_criteria.md` is the one home of. Left for the owner: cut it to the three step names and the pointer.
- `skills/status/SKILL.md:46` and `agents/purlin.md:25` each restate what the two facts read, with the pointer. Left for the owner: keep both, one sentence each, since the agent needs the words in front of it.

## 4. Convoluted prose

Rewritten short and plain, with nothing said taken out:

- `references/purlin_commands.md:16` one paragraph of eleven sentences on six subjects. Now a list of which tests a run starts and four short paragraphs.
- `references/evidence_and_signoff.md:197` the walk's refusals, seven in one sentence. Now a list.
- `references/evidence_and_signoff.md:100` three lines past the page's width. Wrapped.
- `references/glossary.md:87` the audit's entry held eight definitions. Now one entry each.
- `references/glossary.md:66` the evidence entry. Shorter sentences.
- `references/drift_criteria.md:44` the report's keys in one sentence. Now two list items.
- `references/supported_frameworks.md:201` four cases joined by `where`. Now a list.
- `references/supported_frameworks.md:43` one long line. Split into sentences and wrapped.
- `references/spec_quality_guide.md:313` `could differ on that operating system because of files or the operating system`. Rewritten.
- `references/spec_quality_guide.md:334` a line past the page's width. Wrapped.
- `references/formats/package_format.md:6` the opening sentence named twelve things. Now a list.
- `references/formats/marker_format.md:91` the `{files}` placeholder. Now four cases.
- `skills/test/SKILL.md:37` Step 1's selection. Now a list.
- `skills/init/SKILL.md:83` the migrations, seven in one sentence. Now a list.
- `docs/sign-off.md:99` the example refusal named a feature called `audit`, which reads as the command. It names `login`.

What remains, left as it is; each is a dense paragraph a reader can still follow:

- `skills/test/SKILL.md:70` Step 3, and `:88` Step 4.
- `skills/sign/SKILL.md:74` the paragraph after the refusals.
- `skills/spec/SKILL.md:129` "Ids".
- `references/formats/spec_format.md:115` two long lines on taking the next number.
- `references/formats/anchor_format.md:134` four sentences on one line.
- `references/commit_conventions.md:58` the second commit.
- `references/formats/evidence_format.md:117` the `else` chain of the rule words, and the paragraph at `:143`.
- `references/review_criteria.md:12` which rules the audit reads.
- `agents/purlin.md:12` "The words", two paragraphs.

## 5. The deck

`dev/plans/deck/build_deck.py`. The source was changed and built to a scratch folder; both
checks pass on the two slides whose rows changed. The live deck was not published.

- `:109` slide `fromcode`, row 4 said the report gives `how many already pass`. The skill runs no test. Fixed: `how many a test you have already shows`.
- `:158` slide `signoff`, `The package` said the one file holds `who signed`. Fixed: `Each sign-off is a file beside it.`
- `:190` slide `regulated`, notes said a requirement number reaches the package `as a note`. A note is what a signer types at a hand check. Fixed: `in the rule's own words`.
- `:200` slide `manual`, notes said the walk shows the last note. The status and the dashboard show it. Fixed.
- `:119` slide `together`, row 4 says drift gives `a fix you accept by answering y`. Drift names the number written twice; `purlin:spec` shows the plan and asks. Left for the owner: true of the session, since the agent goes from one to the other.
- `:143` slide `audit`, row 3 says a failing test makes the rule `strong`. A spot test's finding still makes it `weak`. Left for the owner: fine on a slide; `docs/audit.md` says the rest.
- `:120` slide `together`, the closing `Purlin has no roles`. Left as the owner wrote it; the glossary now agrees with it.

Slides whose numbered rows are not steps:

| Slide | Rows | Steps |
|---|---|---|
| `why` | 4 | no: four questions |
| `compare` | 4 | no: four tools |
| `touches` | 5 | no: five things in a project |
| `start` | 5 | yes |
| `fromcode` | 4 | yes |
| `together` | 4 | partly: three commands in order, then drift, which comes after a pull |
| `slow` | 4 | no: one act, two commands and what Purlin does |
| `manual` | 2 | carries no numbers |
| `anchors` | 2 | no: two kinds |
| `audit` | 4 | 1 to 3 are; 4 is the command that runs them |
| `signoff` | 3 | yes |
| `remote` | 4 | 1 to 3 are; 4 is what Purlin does |
| `regulated` | 3 | no: three parties |

Every other row was read against the product and holds.
