# Scope review of Purlin 0.10.0

Written 2026-10-01 against `main` at `89184a591`, judged as the product will be once decisions 104
to 108 are built. The yardstick is decision 106: "the only thing purlin cares about is creating
the curent state of the evidence, and the signing stage. everything else is just informative".

## Summary

**The core** is short: a spec of rules and proofs; tests marked with one comment; one run script
that runs the project's own suites, reads their reports and writes per-feature evidence with a
fingerprint (on this machine, and on a remote runner for another operating system); the two facts
read from that evidence (tests met or not, signed or not) on the status; and the sign-off, which
builds the evidence package from the committed evidence, walks the hand checks, takes one
signature and writes `signed/<version>`. The skills that drive it are `purlin:spec`,
`purlin:build`, `purlin:test`, `purlin:sign`, `purlin:status` and `purlin:init`.

**Outside the core** sits about 40 percent of everything: 362 of 921 rules and 910 of 2,287 proofs,
about 7,300 of 20,500 lines of script and about 17,400 of 41,000 lines of tests. The rest of the
outside is docs pages and skill text that teach it.

**The biggest candidates**, by cost against what they add to evidence or sign-off:

1. The dashboard: 58 rules, 181 proofs, about 2,500 lines and 3,300 lines of tests, all
   informative. It repeats what the status prints.
2. The upgrade from 0.9.5: 43 rules, 146 proofs, 1,230 lines and 2,277 lines of tests. It serves
   only projects still on 0.9.5.
3. Mutation testing with three engines: 32 rules, 90 proofs, about 790 lines and 1,200 lines of
   tests, plus a setup question and a percentage on every surface. It is informative.
4. Drift's three role views: 41 rules, 94 proofs, 1,060 lines and 2,000 lines of tests. Half of
   what they print repeats the status.
5. Pinned anchors pulled from other repositories, with sync and the network check: 42 rules,
   65 proofs, 520 lines and about 1,900 lines of tests, including three end-to-end shell suites.
6. Purlin's checks of its own prose: about 220 rules over the skills, the agent, the docs and the
   version string, with about 7,000 lines of tests. Only Purlin's maintainers need them.

The AI audit (40 rules, 105 proofs, about 740 lines) is informative too. It is tangled into the
sign-off walk, which decides where to stop from the audit's findings, so it is a question and
not a plain cut.

## The table

Counts are rules / proofs from each spec's rule and proof lines (the `> Highest-` numbers run
higher where lines were deleted). "Lines" are tracked lines of script; "tests" are lines of
`dev/test_*`. **Serves** is evidence (creating the current state), sign-off, both, or neither.

| Feature | What it is for | Serves | Who needs it | Cost | Call |
|---|---|---|---|---|---|
| Spec format and reader (`schema_spec_format`, `specs`) | Read rules and proofs from one file per feature | Both | Everyone | 46 / 107; 600 lines; 1,550 tests; `spec_format.md` | **Keep** |
| Run script (`run_script`) | Run the project's suites and write what they saw | Evidence | Everyone | 67 / 217; 1,645 lines; 3,400 tests | **Keep** |
| Markers and the four report formats (`reports`) | Tie each test result to its proof: junit, trx (.NET), gotest (Go), exit (shell) | Evidence | Everyone; trx and gotest for .NET and Go teams | 31 / 114; 1,610 lines; 1,440 tests; fixtures for jest, vitest, dotnet, go | **Keep**. Go has no known user; dropping gotest saves about 100 lines and one fixture |
| Near-miss marker repair (`markers --near-misses`) | Find a marker comment one edit from right, for `purlin:build` | Neither | Everyone, as a convenience | Part of markers.py; a few proofs | **Keep**, small |
| First-run test detection (`frameworks.py`) | Suggest the `tests` setting from the tools found | Neither | New projects | 323 lines; `supported_frameworks.md` 215 lines | **Keep**: it is what makes setup ask nothing about tests |
| Evidence writer and fingerprint (`evidence_writer`, `evidence`) | Write per-feature, per-system evidence; know which is current | Evidence | Everyone | 57 / 171; 1,630 lines; 2,490 tests; `evidence_format.md` | **Keep** |
| States, payload, summary, `Left to do` (`states`, `summary`) | Turn evidence into each rule's passed cell and the two facts | Both | Everyone | 82 / 201; 2,270 lines; 2,930 tests | **Keep**; the gate logic in it goes (108) |
| `purlin:status` and the MCP server (`server`, `config_engine`) | Show the state in the terminal; serve status, drift and settings to the agent | Both, as the reader | Everyone | 35 / 82; 470 lines; 1,090 tests; skill 99 lines | **Keep** |
| Hand checks (`@manual`) | A proof a person checks at sign-off | Sign-off | Regulated teams | Inside states and sign | **Keep** |
| Operating-system tags (`@env`) | A proof that must hold on another system | Evidence | Teams shipping on several systems | Inside run, evidence, host | **Keep** |
| Sign-off and package (`signatures`, `package`) | Build the package from committed evidence, walk, sign, tag `signed/<version>` | Sign-off | Regulated teams; any team that wants a signed record | 54 / 109; 1,880 lines; 2,000 tests; skill 165 lines; two formats | **Keep** |
| Renumbering helper (`renumber`) | Fix a number two branches both took, asking first | Both: a spec with a number twice blocks signing (102) | Teams | 9 / 12; 350 lines; 290 tests | **Keep** |
| `purlin:init` setup (`scaffold`) | Write settings, `specs/`, evidence folder, gitignore block, dashboard copy, runner file | Evidence | Everyone, once | 58 / 142; 807 lines; 2,410 tests; skill 187 lines + 12 / 23 | **Keep**, with fewer questions and settings (Q9) |
| Settings `version`, `tests` | The plugin release the project is on; how its suites run | Evidence | Everyone | In config engine | **Keep** |
| Setting `gate` | What a version needs | Neither after 108 | Nobody | Setup question, `--gate`, gate-conditional displays | **Cut, no question** (108) |
| Settings `mutation_engine`, `audit_parallel`, `ci`, and the planned `project_name` | Turn breaks on; audit calls at once; which host; the package's name | Neither | Few | One setup question; four owned fields; a migration each | Q1, Q2, Q9 |
| Remote runner, GitHub (`host`, `remote`, `workflow`) | Run the `@env` proofs on another system and bring the evidence home | Evidence | Teams shipping on several systems | 29 / 117 shared with Azure; about 1,000 lines; 2,660 tests; `purlin.yml` 127 lines | **Keep** |
| Remote runner, Azure DevOps | The same on Azure Pipelines | Evidence | Teams on Azure DevOps | About 300 lines in host and remote; 120-line template; a hand check script; `az` setup | Q10 |
| The runner's `signed/*` tag trigger | Run the tests again when a signed tag is pushed, writing nothing | Neither | Nobody after 106 | Trigger and branch in both templates; docs lines | **Cut, no question** |
| Release step (`release.md`, `release.py`, `--release`, `passed/<version>`) | Commit evidence and package and tag a release | Neither after 106 | Nobody | 12 / 16; 458 lines; 368 tests | **Cut, no question** (106, C13) |
| `.purlin/tests.md` | A committed table of tests for readers without a checkout | Neither after 106 | Nobody | Writer, rules, gitignore words, docs | **Cut, no question** (106) |
| AI audit (`ai_audit`, `skill_audit`) | Have a model read each rule beside its proofs and tests | Neither (informative); the walk uses it to choose stops | Teams wanting a second reader | 40 / 105; 735 lines; 1,650 tests; `review_criteria.md` 131 lines; Strong column, box, badge, panel; `fake_claude.py` | Q2 |
| Mutation testing: mutmut, Stryker, Stryker.NET (`mutation`) | Measure test strength by breaking code on purpose | Neither (informative) | Teams wanting a measure of test strength | 32 / 90; 790 lines; 1,200 tests; 4 fixtures; setup question; `--arm-timeout`; mutmut config written into the project | Q1 |
| Local anchors | A rule set over the whole project, such as the security baseline | Evidence | Teams with project-wide rules | Inside specs, states, fingerprint; skill `create` | **Keep** |
| Pinned anchors: pull, pin, sync, behind check (`upstream`, `skill_anchor`) | Take a rule set from another repository and keep it current | Evidence for the rules; the pin and sync are convenience | Organisations sharing a baseline across repositories | 42 / 65; 520 lines; 1,900 tests incl. 3 e2e shell suites and a bare repo fixture; `anchor_format.md` 150 lines; security rules 6 and 8 | Q3 |
| Drift (`drift`, `skill_drift`) | Say what changed since your last pull, in a pm, eng or qa view | Neither (informative), but it catches collisions after a merge | Teams | 41 / 94; 1,060 lines; 2,010 tests; `drift_criteria.md` 183 lines; MCP tool | Q4 |
| Dashboard (`purlin_report`) | One HTML page of every rule's state, opened from disk | Neither (informative) | Anyone who prefers a page to the terminal | 58 / 181; about 2,500 lines incl. the built page; 3,290 tests; `build_report.py`, screenshot capture, 3 payload fixtures; docs 182 lines | Q5 |
| `purlin:export` (`skill_export`) | Write the package at any time, for any version name; check a package | Neither beside the sign-off, which now builds the package | Readers who want an unsigned package | 14 / 16; skill 88 lines; 407 tests; CLI entry in package.py | Q6 |
| `purlin:spec-from-code` (`skill_spec_from_code`) | Write the specs an existing codebase implies | Neither (onboarding) | A team adopting Purlin on old code, once | 29 / 31; skill 119 lines; 718 tests; docs 154 lines | Q7 |
| Upgrade from 0.9.5 (`update`) | Migrate a 0.9.5 project's files, markers, hooks, workflows, settings | Neither | Projects on 0.9.5 | 43 / 146; 1,230 lines; 2,277 tests; a 0.9.5 fixture; docs section; RELEASE_NOTES | Q8 |
| Instruction checks (`skill_*` specs, `purlin_agent`, `purlin_docs`, `purlin_output`, vocabulary test) | Hold the skills', agent's and docs' wording to rules | Neither | Purlin's maintainers | About 205 / 280; about 6,400 tests | Q11 |
| Version machinery (`purlin_version`, `bump_version.sh`, `version-check.yml`) | One version string, propagated and checked | Neither | Purlin's maintainers | 14 / 26; 149-line script; 53-line workflow; 635 tests | Q11 |
| Security anchor (`security_no_dangerous_patterns`) | No shell, eval or credential literal in `scripts/` | Evidence, for Purlin itself | Purlin's maintainers; an example anchor | 8 / 89; 961 tests; checks PHP, TS and C# forms though `scripts/` holds none | Q11 |
| Docs pages (13) | Teach each role | Neither | Everyone | About 2,650 lines; two diagrams and two screenshots | Q12 |
| The deck (`dev/plans/deck`) | Slides about Purlin | Neither | The owner, to present | 178 lines of builder; 10 slide images, some showing the removed gate `strong` | Q12 |
| Plans and lane notes (`dev/plans/*`) | History of the build | Neither | Nobody in a release | About 40 files | **Cut, no question** (decision 44's sweep) |

## Dead weight: cut, no question

Each serves only something already removed, or is already decided.

1. **The gate (108):** the setting `gate`, `purlin:init --gate`, setup's gate question, the
   gate-conditional displays (the `No proof` box and `Proofs` column only at `signed`,
   `to write a proof for` only at `signed`), the dashboard's `gate: signed` chip, the docs
   page's gate half, and the word "gate" in skill one-liners (`purlin:init` "and change the
   gate later", `purlin:status` "what blocks the gate") and in `references/hard_gates.md`'s name.
2. **The release step (106, C13):** `scripts/export/release.py`, `specs/export/release.md`,
   `dev/test_tag.py`, `purlin:test --release`, `passed/<version>`, the package's `state`, and
   the flag names `--release` on `purlin:sign` and `purlin:export`.
3. **`.purlin/tests.md` (106):** its writer, its rules, the gitignore template's words, and the
   dashboard page's first paragraph, which still sends readers to it.
4. **The runner's run on a pushed `signed/*` tag**, in both templates: it runs the tests and writes
   nothing, and since the sign-off reads committed evidence nothing reads that run.
5. **The release wording in what stays:** drift's `qa` view printing "the lines of `Left to do`
   that stop a release", `RELEASE_NOTES.md`'s two gates and release run, and the docs sections
   "The release run", "A hand check at the gate `passed`", "The release" and "Releasing a version".
6. **Three empty folders** `scripts/ci/`, `scripts/hooks/` and `scripts/proof/` in this checkout,
   holding only `__pycache__`; untracked, so they do not ship, but they mislead a reader here.
7. **`dev/plans/*`**, by decision 44's sweep, the deck aside (Q12).

## Notes found on the way

- **Drift and the status reach the network.** The drift criteria say drift "never fetches, pulls
  or reaches the host", yet the anchors-behind check runs `git ls-remote` against every pinned
  anchor's source, and the security anchor's PROOF-9 shows the status does too. Q3 resolves it.
- **The sign-off walk depends on the audit.** It stops at each hand check, each weak rule and each
  rule never audited. A project that never runs the optional audit gets one stop per rule. Q2
  resolves it.
- **Two features doing one job:** `purlin:export` and the package the sign-off builds; the
  docs pages `team-workflow` and `working-together`; `qa-guide`, `review-and-signing` and
  `regulated-workflow` on the sign-off; drift's `eng` and `qa` lines (`rules_without_test`,
  `out_of_date`, `Left to do`) and the status; `purlin:spec-from-code` and `purlin:spec`, which
  already takes "a requirement in any form"; the audit's "strong" and mutation's "strength", two
  measures of test quality on the same cell.
- **The remote matrix depends on who ran setup:** it holds each tagged system the setup machine
  is not, so a team whose members use different systems gets a matrix shaped by one of them.
  This is a note, not a question; a re-run of setup rewrites it.

## Questions for the owner

Each question names the option that best follows decision 106 first, marked recommended.

**Q1. Mutation testing.** Purlin can break a feature's code on purpose and count how many breaks
the tests catch, shown as a percentage beside each feature. It never affects whether the tests
pass or whether a version can be signed. Three tools do it, one each for Python, JavaScript and
.NET, and setup asks whether to turn it on.
- **(a) Cut it, recommended.** No percentage anywhere, no setup question, one less setting.
  Saves 32 rules, 90 proofs, about 790 lines and 1,200 lines of tests. Loses the only measure of
  test strength that does not depend on a model.
- (b) Keep it for Python only, off by default and out of the main docs. Saves about two thirds of
  the cost; JavaScript and .NET teams lose it.
- (c) Keep all three, off by default and out of the main docs. Saves nothing but the question.

**Q2. The AI audit.** A model reads each rule beside its proofs and its tests and says whether
the tests really show the rule. Nothing waits on it, but the sign-off walk uses its findings to
choose where to stop: it stops at each rule found weak or never read, so a project that never
runs the audit stops at every rule.
- **(a) Keep it as an optional tool, recommended.** Off the main path and out of the main docs;
  the walk stops at hand checks only, lists the audit's findings where it ran, and lets the
  signer open any rule. Costs the walk's per-rule stops for weak rules. Keeps the second reader
  for teams who want it.
- (b) Cut it. The walk stops at hand checks only; the `Strong` column, box, badge and panel go.
  Saves 40 rules, 105 proofs, about 740 lines and 1,650 lines of tests. Loses any judgment of
  whether a test shows its rule.
- (c) Keep it as now, with the walk stopping at each weak or unread rule. Costs a project that
  skips the audit one stop per rule at every sign-off.

**Q3. Anchors pulled from other repositories.** A team can take a set of project-wide rules
from another repository, such as a company security baseline, pinned at one commit. Purlin then
checks the other repository over the network on every status and drift, and offers a one-step
update.
- **(a) Keep pulling and the pin, drop the automatic network check, recommended.** The status and
  drift read only this checkout; you ask whether a pin is behind with the sync command's check.
  Keeps shared baselines and decision 107. Loses the reminder that a baseline moved.
- (b) Cut pulling, the pin and sync. A team copies the file in and keeps it current by hand.
  Saves 42 rules, 65 proofs, 520 lines and about 1,900 lines of tests. Loses knowing which
  version of the baseline you hold.
- (c) Keep it as now, network check included.

**Q4. Drift's role views.** After a pull, drift says what changed, in one of three views for
product, engineering and QA. It also catches a number two branches both took. About half its
lines repeat what the status already prints.
- **(a) One view, with no roles, recommended.** What changed in rules, proofs, tests and code,
  plus the collision and reworded-proof warnings; the lines the status already prints go.
  Saves roughly a third of drift's rules and tests. Loses each role's tailored list.
- (b) Cut drift. The status carries the collision and reworded-proof warnings. Saves 41 rules,
  94 proofs, 1,060 lines and 2,000 lines of tests. Loses "what changed since my last pull".
- (c) Keep three views.

**Q5. The dashboard.** A page opened from disk showing every rule's state, beside the same facts
the status prints in the terminal.
- **(a) Keep the board and the rule page, cut the extras, recommended.** It shows the two facts,
  the specs and anchors, each rule's result and proofs. Out go the self-reload and age timer,
  per-system boxes, links to the host, the band bars, the theme button (the page follows the
  system's theme, both still shipping) and the `Strong` and strength parts that Q1 and Q2 remove.
  Saves perhaps a third of 58 rules and 181 proofs. Loses polish.
- (b) Cut the dashboard; the status is the one view. Saves 58 rules, 181 proofs, about 2,500
  lines and 3,300 lines of tests, plus the screenshot tooling. Loses the view for people who
  do not read a terminal.
- (c) Keep it as now.

**Q6. Writing the package outside the sign-off.** The sign-off now builds the evidence package
itself. A separate command also writes a package at any time, unsigned, under any version name,
and checks a package against its fingerprint.
- **(a) Fold it into the sign-off, recommended.** The package is written only when someone
  signs; the preview that asks nothing shows what it would hold; checking a package stays as an
  option of the sign-off. Saves a skill, 14 rules, 16 proofs and 400 lines of tests. Loses
  handing an unsigned package to an outside system.
- (b) Keep the separate command.

**Q7. Writing specs from existing code.** A skill reads a codebase with no specs and writes the
rules it already implies. The spec skill already takes a requirement in any form.
- **(a) Fold it into the spec skill, recommended.** "Write specs for this folder" becomes one
  more kind of requirement it takes. Saves a skill, 29 rules, 31 proofs, 718 lines of tests and
  a docs page. Loses a command named for the job.
- (b) Keep it as an optional skill, out of the main docs.
- (c) Cut it; a team writes its first specs with the spec skill by hand.

**Q8. The upgrade from 0.9.5.** Decision 44 kept it as the one exception to a clean release. It
rewrites a 0.9.5 project's markers, hooks, workflows, settings and anchor lines in twelve steps.
Decision 108 also has it take the gate out of earlier 0.10 builds, which were never released.
- **(a) Keep it for 0.9.5 projects only, recommended.** No step exists for an unreleased 0.10
  build; those projects are set up afresh. Saves a little; keeps every real user's path.
- (b) Cut it. A 0.9.5 project is set up afresh with a written guide. Saves 43 rules, 146 proofs,
  1,230 lines and 2,277 lines of tests. Costs each 0.9.5 project a manual move.
- (c) Keep it as decided, 0.10 builds included.

**Q9. Setup's questions and the settings file.** With the gate gone, setup asks whether to turn
on mutation testing and whether to commit what it wrote. The settings file also holds how many
audit calls run at once, which git host the project uses, and, as planned, the project's name.
- **(a) Setup asks one question, whether to commit; the file holds the version and the test
  commands, recommended.** The host is read from the remote each time, the name from the
  project's own files each time, and the number of audit calls is fixed (or an option of the
  audit, if Q2 keeps it). Loses overriding a wrongly detected host or name in a file.
- (b) Keep the settings as planned, less the gate.

**Q10. The Azure DevOps runner.** The remote run, which brings home evidence for another
operating system, works on GitHub and on Azure DevOps. Azure costs about 300 lines, a second
template, a hand-run check that needs an Azure account, and the `az` tool on each machine.
- **(a) Keep both, recommended**, since a remote result is evidence and a team on Azure DevOps
  has no other way to get it.
- (b) GitHub only. Saves the Azure share. A team on Azure DevOps proves other systems by hand
  or not at all.

**Q11. Purlin's checks on itself.** About 220 rules hold the wording of the skills, the agent
definition and the docs, and the one version string; the security baseline checks forms in
PHP, TypeScript and C# that Purlin's scripts do not hold. Only Purlin's maintainers need these.
- **(a) Trim them, recommended.** Keep the checks that protect what a user runs: no emoji in
  output, the security baseline over the languages the scripts use, and the version script's own
  check in CI. Replace the per-skill wording rules with one short list per skill of the commands
  and files it must name. Saves well over half of about 6,400 lines of tests. Loses guards
  against wording drift.
- (b) Keep them as they are.

**Q12. The docs and the deck.** Thirteen pages, of which two teach working as a team and three
teach the sign-off; the deck's slides still show the removed gate `strong`.
- **(a) Consolidate the docs to about eight pages and rebuild the deck to the two facts,
  recommended.** One page each: how it works, getting started, specs and anchors, running and
  evidence, working together, the sign-off (QA and regulated use included), upgrading, and the
  dashboard if Q5 keeps it. Costs one rewrite pass. Loses the role-by-role pages.
- (b) Keep thirteen pages, rewritten for decision 108; drop the deck.
- (c) Keep thirteen pages and rebuild the deck.
