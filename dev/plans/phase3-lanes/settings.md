# Lane `settings`

You are lane `settings` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/settings`, branch `lane/settings`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/settings -b lane/settings main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-settings`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q65 to Q70 and report questions 65 to 70; the report's "Gaps left" for
   `config_engine` and `server`.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/mcp/config_engine.py`, `scripts/mcp/purlin/server.py`, `scripts/purlin_python.sh`
- `.claude-plugin/plugin.json` (the entry that starts the server, alone)
- `specs/mcp/config_engine.md`, `specs/mcp/server.md`
- `dev/test_config_engine.py`, `dev/test_mcp_server.py`

The manifest's `version` field is not yours: it changes only through the bump script, which lane
`instructions` owns.

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **Q65** (C1.9, C3.4; **PENDING OQ1**): P2 landed `config_problem`. Now `_read_json` stops
   folding a read, decode or parse failure into "absent"; `update_config` refuses to save while
   `config_problem` answers, raising with its sentence and leaving the file byte for byte; each
   of the three server tools answers the sentence in place of the workspace check (around lines
   195 to 200). New config_engine rules from the next free id, one per claim: the sentence names
   the cause and the line; a save is refused while the file cannot be read. One proof per
   cause: a trailing comma (`at line <n>`), bytes that are not UTF-8, JSON that is a list, a
   save refused (file unchanged). New server proof: each tool answers the sentence.
2. **Q66** (C3.5, **PENDING OQ8**): `update_config` removes its temporary file and raises when
   the move or write fails (today it swallows the error, around lines 97 to 99);
   `handle_purlin_config` answers `The setting was not saved: <cause>.`. Config_engine RULE-10
   adds "and says so"; PROOF-26 and PROOF-27 assert the raise; a new server proof under RULE-9.
3. **Q67.** `main()`, `if __name__ == '__main__'`, the shebang and any import only they use go
   from `config_engine.py`; RULE-5 and PROOF-5, 19, 20, 21, 22 and 23 go with their tests (around
   lines 290 to 330, the process-level test included).
4. **Q68 and Q69** (C3.5, **PENDING OQ8**, whose first option shows the owner the six accepted-value phrases below): a write of a known key with no `value` argument is
   refused with `A change needs a value; nothing was saved.`; a value outside C3.5's accepted set
   with `"<value>" is not accepted for <key>; it takes <accepted>. Nothing was saved.`; the file
   is left byte for byte. Accepted: `gate` passed, strong or signed; `mutation_engine` none,
   auto, mutmut, stryker or stryker_net; `min_strength` a whole number from 0 to 100, or null
   (explicit null accepted for it alone); `audit_parallel` a whole number from 1 to 16; `tests`
   a list (entries not read); `ci` github, azure or none. Unknown keys are written as today.
   Server RULE-10 is reworded, or split one rule per claim, with one proof per refusal.
5. **The version write** (**PENDING OQ8**): a write of `version` is refused with
   `version is written by purlin:init from Purlin's own version; nothing was saved.`, file
   unchanged. With OQ8's second option, `version` is written like any key.
6. **Q70:** a read of a key that is absent or stored as null answers
   `json.dumps({"<key>": None}, indent=2)`, the shape of a found key. Server RULE-9 says so; new
   proof.
7. **Split by claim and one case per proof** (C11) across config_engine and server.
8. **The interpreter lookup fails loudly, the server start stays soft** (decision 69; C9; plan
   section 7, call 36). Today `scripts/purlin_python.sh` exits 0 when it finds no Python 3, so
   a skill that starts a script through it reads as having succeeded.
   - `scripts/purlin_python.sh`: when no interpreter is found it writes its one stderr line, as
     today, and exits 1, unless the environment variable `PURLIN_PYTHON_SOFT` is `1`, when it
     exits 0 after the same line. Its header comment says so. The case with no script named
     (the usage line) keeps its exit as it is.
   - `.claude-plugin/plugin.json`: the server is started today with `"command": "sh"` and
     `"args": ["${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh", "${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin/server.py"]`.
     The `mcpServers.purlin` entry gains, beside them, `"env": {"PURLIN_PYTHON_SOFT": "1"}`;
     `command` and `args` do not change, so server PROOF-22 and PROOF-137 hold as written.
   - `specs/mcp/server.md`: its `> Scope:` gains `scripts/purlin_python.sh`. A new rule from the
     next free id: with no Python 3 found, the lookup prints its line and exits 1, and exits 0
     when `PURLIN_PYTHON_SOFT` is `1`; one proof per case (run with `/bin/sh` and a `PATH`
     that holds no Python and no `py`, `PURLIN_PYTHON` unset). A new proof under RULE-22: the
     manifest's `purlin` entry sets `PURLIN_PYTHON_SOFT` to `1`.

**You consume** P2's `config_problem`. **You produce** C3.5's answers for the agent.


## How to number, split and write proofs

- A new id is one more than the highest the spec file has held since it was last written whole
  (`git log -p --follow -- <spec>`); a deleted number is never reused.
- Every proof you write or reword holds one case (one starting situation, one action, what is
  seen) in at most 60 words, names no file of code, function or test framework, and has a test of
  its own with `# purlin: <feature> PROOF-<n>` directly above it. A proof whose test loops over
  gates, inputs or systems with one expected result becomes one proof per case (Q1, Q8).
- Split by claim (decision 94): split a rule of your specs where its text states two or more
  claims, its proofs fall into groups each showing exactly one, and no proof shows two. The first
  claim keeps the id; each other claim takes a new id; proofs keep their ids and text, only their
  `(RULE-N)` changes; markers do not change. Do not split a rule whose claims share every proof.
- Delete outright what is retired: no test that a removed thing is absent, nothing added to
  `dev/test_vocabulary.py`, no reader of an old spelling.
- A format you change updates its file under `references/formats/` in the same commit, with the
  bump the contracts name.

## How to test

```
export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH
cd /Users/richlabarca/LocalCode/purlin-wt/settings
.venv/bin/python -m pytest dev/test_config_engine.py dev/test_mcp_server.py -q      # your own files, whole
bash dev/run_tests.sh --fast                     # the fast sweep, in your worktree
```

If `.venv` is missing in the worktree, use `/Users/richlabarca/LocalCode/purlin/.venv/bin/python`.
Do not run the full sweep; integration runs it once.

Before you break code on purpose to see an assertion fail, confirm the test that runs it uses
`dev/fake_claude.py` or no model at all, that no real `claude` is on its `PATH`, and that it
reaches no real git host, `gh`, `az` or network service. Restore the file with
`git checkout -- <that file>`; never `git checkout -- specs/`.

A failure in a test file you do not own: check `phase3-contracts.md` C7. If the contracts predict
it, leave it; otherwise report the test, its assertion and the value it saw. Never edit that file.

## Limits

- Commit on `lane/settings` only, with the prefixes of `references/commit_conventions.md`, ending
  each message with the attribution lines your session gives. Push nothing, tag nothing, open no
  pull request.
- Run no `purlin:audit` and no `purlin:sign`, never start the real `claude` program or any real
  service.
- Stage no generated file: `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`, screenshots.
- Keep each skill and `agents/purlin.md` within its line ceiling; a change cuts as many lines as
  it adds.
- A call no decision or contract makes: build the rest, leave that thing as it is, report it.
- Before you finish: `git rebase main`, rerun your files and `--fast`, fix your own files where a
  lane merged earlier changed a result the contracts predict.

## Report, as your final message

- The branch and its commits (sha and subject).
- For each spec you own: its highest RULE and PROOF id now, and its rule and proof counts before
  and after.
- Tests in your files before and after, and the `--fast` result.
- Every split, as `<spec> RULE-<old> -> RULE-<a> (<claim>), RULE-<b> (<claim>)`.
- Every proof deleted, moved or re-pointed.
- Every word a person reads that you chose because no decision or contract gave it.
- Every item left as it stands, and why.
- Every failure in a file you do not own.
