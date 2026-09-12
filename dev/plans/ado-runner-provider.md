<!-- Checked-in working plan. This copy is authoritative: it is written to be executed
     cold on a different machine (the user's work machine, which has an Azure DevOps
     account; the machine this was written on does not). Update this file as phases
     complete, in the same commit as the work, per dev/plans/README.md. -->

# The Azure DevOps runner provider

Continuation of `dev/plans/platform-generic-remote-verification.md`, which shipped the platform
framework and one runner provider (`github`). That plan's Phase 11 commissions this one. Branch:
`two-gauges-remote-verification`, the same branch, picked up with `git fetch && git checkout
two-gauges-remote-verification`. **Do not merge `main` and do not push `main`.** The parent plan's
"TODO before pushing main" list is still the gate; this plan appends to it (section 10).

Everything below cites real functions, rule numbers and proof numbers as they stand at the base
commit of this branch. Where a fact about Azure DevOps could not be checked from the repository,
it is marked **verify on the work machine** and the first commit of section 7 is the place to
check it.

---

## 1. Context: what exists, and why `provider: ado` is currently a dead end

**The platform registry.** `.purlin/config.json` carries an optional top-level `platforms` object.
`_platform_registry(config)` in `scripts/mcp/purlin_server.py` builds the registry from
`_BUILTIN_PLATFORMS` (`windows`, `macos`, `linux`, each carrying only its `os`) overlaid by that
object, and `_validate_platform_entry(pid, entry)` validates one entry: the id matches
`[a-z0-9][a-z0-9-]*`, `os` is required and one of the three families (with `ios` and `android`
rejected as "not yet supported"), `version` is `N[.N...]` or `>=N[.N...]`, `distro` is linux only,
`arch` normalises through `_ARCH_ALIASES`, `label` is free text, and `runner` is an object whose
`provider` is required and whose only other permitted keys are `runs_on` and `workflow`
(`_PLATFORM_RUNNER_KEYS`). Any other key is an error and the whole entry is dropped and named, so a
typo cannot vanish into an entry that matches every host of its family. This is `sync_status`
RULE-50, proved by PROOF-82 and PROOF-83 in `dev/test_mcp_server.py`.

**Host detection and satisfaction.** `_detect_host_platform()` returns `{os, version, distro, arch,
id}`, where `id` is `PURLIN_PLATFORM` when set (`sync_status` RULE-51). `_result_satisfies(
result_platform, declared, registry)` decides whether a scoped result proves a declared id, in
exactly two ways: the ids are equal, or the declared id is a family id and the registry entry for
the result's id carries that `os`. `_awaiting_runner(name, info, all_proofs, registry)` returns the
`(proof_id, tier, platform)` triples that have no satisfying result, which is what
`AWAITING RUNNER` is built from. A result under an id no proof declares is an undeclared result and
counts toward nothing (`sync_status` RULE-53).

**The `Platforms:` block.** `_platforms_block(features, registry, host)` prints, after the
remote-verification line, one `local:` line per declared id this host satisfies and one `runner:`
line per id it does not, the latter ending in whatever `_platform_dispatch_note(registry,
platform_id)` returns (`sync_status` RULE-52, PROOF-85). That function is the whole of the
provider dispatch story today:

```python
provider = runner.get('provider')
if provider != 'github':
    return f'runner provider {provider} is not one purlin:test can dispatch'
```

**Provenance.** Proof entries carry no runner field and no timestamp, by design, so that a re-run
proving the same things commits nothing (`git diff --cached --quiet` stays idempotent).
`_platform_provenance(project_root, spec_path, feature, tier, platform_id)` therefore reads
provenance back out of git: `git log -1` on the scoped file, the `Purlin-Runner:` trailer for the
runner identity and `Purlin-Platform:` for the platform the runner was told it was, cross-checked
against the filename (`sync_status` RULE-48). `references/formats/receipt_format.md` records the
same per file in `evidence.proof_files` (`file`, `tier`, `platform`, `commit`, `committed_at`,
`runner`, `executed_in_test_run`), and `purlin_references` RULE-21 keeps that contract honest.

**The commit-back contract.** `specs/ci/verify_gate.md` governs what a runner definition must do.
RULE-7: both trailers in a single `-m` argument, because git builds one paragraph per `-m` and
parses trailers out of the last paragraph only, so a trailer in its own `-m` reads correctly in
`git log` and is invisible to `git log --format=%(trailers:key=...)`. RULE-8: both halves of the
loop guard, a path exclusion for the files it writes and `[skip ci]` in the commit subject.
RULE-10: a pull-rebase-retry loop of exactly three attempts ending in `exit 1`, because several
platform runners may commit to one branch at once. RULE-11: `scripts/update/migrate.py --check`
runs as a step before the step whose `name` begins with `Run`. The Scope line of that spec reads
`scripts/ci/verify_gate.py, .github/workflows/verify-gate.yml, .github/workflows/*-proofs.yml`,
and `dev/test_verify_gate.py`'s `_workflows_that_commit_proofs()` scans `WORKFLOW_DIR =
.github/workflows` only. The live example is
`.github/workflows/purlin-windows-2022-proofs.yml`, which satisfies all four rules.

**The preflight.** `scripts/update/migrate.py --check --project-root .` prints the pending
migrations as JSON, writes nothing, and exits `1` only for the ids that make the evidence a run is
about to write unreliable: every `legacy-*` id and `plugin-copies-stale`. `config-fields-missing`
and `receipt-v1` are reported and exit `0` (`_NON_BLOCKING`). A runner whose `.purlin/plugins/`
copies predate platform scoping writes agnostic proof files that satisfy no declared platform, so
the job goes green and proves nothing; the preflight is the only place that gap is visible.

**The dispatch loop in `purlin:test`.** `skills/test/SKILL.md` Step 1.5 ("Classify Platforms")
prints the `Platforms:` block before the first test runs and states three invariants: there is no
local substitute for a platform, a missing runner warns and never blocks, and `PURLIN_PLATFORM` is
set for the local run (`skill_test` RULE-7). Step 2a runs the test command once per locally
satisfiable id, prefixed `PURLIN_PLATFORM=<id>`. Step 2b is the remote path (RULE-8): push the
branch once, one `gh workflow run <workflow> --ref <branch>` per remote platform, `gh run watch`
each, then a single `git pull --ff-only` after all of them, retried once. The loop is bounded at 3
rounds, matching `skills/audit/SKILL.md` and `skills/verify/SKILL.md` (RULE-10). The setup offer
(RULE-11) is per platform, on discovery, never at init, and writes both the workflow file and the
`runner` block in config or neither, only on a yes. Step 2b's branch today reads: dispatch when
`provider` is `github` and the workflow file exists, offer setup when there is no runner block or
the file is missing, and "A `runner` block naming a provider other than `github` is reported as not
dispatchable and its proofs stay awaiting."

**The reference.** `references/remote_verification.md` carries the platform model, the trailer
contract, both loop-guard halves, the GitHub Actions template as shipped (with `paths-ignore`,
`workflow_dispatch`, `permissions: contents: write`, `PURLIN_PLATFORM` and `PURLIN_PLUGIN_ROOT` in
the job env, `persist-credentials: true`, the tooling clone pinned by `--branch v<VERSION>`, the
`migrate.py --check` preflight, the per-framework setup block, `shell: bash` on every `run:` step,
the narrowed `git add`, the `git diff --cached --quiet` guard, both trailers in one `-m` with
`[skip ci]`, and the three-attempt pull-rebase-retry loop), the "What is load-bearing in that
template" section, the mode table, the what-travels table and the reporting samples.
`purlin_references` RULE-18 requires every one of those template elements, RULE-22 requires every
CI template under `references/` and `docs/` to reach Purlin `scripts/` only through
`$PURLIN_PLUGIN_ROOT` and to pin a tag, and RULE-23 requires a non-empty **Runner setup** cell for
every framework in `references/supported_frameworks.md` (all eight have one, and the column is
already provider neutral: `pip install pytest`, `npm ci`, `dotnet restore`, `composer install`,
the C toolchain note, and "nothing beyond `python3`" for shell and sql).

**Why `provider: ado` is reported as not dispatchable.** Three places say so, and all three are
load bearing. `_platform_dispatch_note` returns the "not one purlin:test can dispatch" string for
any provider that is not `github`. `skills/test/SKILL.md` Step 2b says the same in prose.
And `ado` is not a hypothetical in the specs: `sync_status` PROOF-85 uses it as its worked example
of a non-dispatchable provider ("register `provider: ado` and verify `runner provider ado is not
one purlin:test can dispatch`"), asserted at `dev/test_mcp_server.py:1188-1190`. The parent plan's
backlog records the seam: "ADO and other runner providers: the registry's `runner.provider` is the
seam; `purlin:test` reports non-github providers as not dispatchable."

**The decision.** ADO is the second provider. It is the right second one because the user has an
Azure DevOps account on the work machine (and none on the machine the framework was built on), it
exercises the provider seam without inventing a third concept, and its hosted pools cover the same
three families the registry already models. Nothing about the platform model, the trailer
contract, the scoped file names, `PURLIN_PLATFORM`, the preflight or the receipt shape changes: the
only new thing is a second way to dispatch and a second pipeline definition format.

---

## 2. Binding constraints carried from the parent plan

These are not suggestions. They are what the whole branch has been built under, and a commit that
breaks one of them will be visible in the next sweep.

- **No em-dashes and no en-dashes in prose.** Use commas, colons or parentheses. The only permitted
  occurrences are inside samples reproducing the server's own output separators. Check before every
  commit with `command grep -rn "$(printf '\u2014\\|\u2013')" <files you touched>`.
- **Every rule ships with a PROVABLE proof and a mutation check in the same commit.** After the
  spec edits, run `python3 scripts/audit/static_checks.py --check-proof-design --project-root .`
  and require zero UNPROVABLE and zero LOOSE among the descriptions this plan writes. STRUCTURAL is
  acceptable only for a rule about prose or about where code may live. The mutation check is: break
  the behaviour, run that one proof, watch it fail, restore, re-run. Record the mutation for each
  proof in the DONE section. `.purlin/config.json` here sets `"mutation_checks": true`, so this is
  the project's own declared standard, not a private habit.
- **Specs and proofs before receipts.** Commit the code, the spec rules and the proofs together;
  then run the sweep; then `python3 dev/issue_receipts.py`; then a separate `verify:` commit. A
  receipt references committed state, and the issuer refuses to issue unless
  `.purlin/runtime/test_run.json` exists with `ok: true` and `commit == HEAD`.
- **The `verify:` commit rhythm and vocabulary.** `verify: [Complete:all] features=N/M anchors=N/M
  vhash=<8 hex>`, the two counts never summed. Copy the line from the issuer's own summary output
  rather than recounting by hand (`purlin_references` RULE-7, `skill_verify` RULE-14). The base
  commit of this plan reads `features=35/37 anchors=5/5`.
- **`git pull --ff-only` after every push**, because runners commit back. The scratch project in
  this plan will have an ADO pipeline committing to its branch, and this repository already has a
  GitHub runner committing to `two-gauges-remote-verification`.
- **Run the sweep in the foreground.** `bash dev/run_tests.sh`. A background sweep was killed by the
  OS for memory once already on this branch and churned proof files. Never run a subset of tests
  before a commit: the write-scoped overwrite is keyed per test file, so running part of a file
  replaces that file's entries for the features it touches and drops the proofs you skipped. If it
  happens anyway, restore with `git checkout -- 'specs/**/*.proofs-*.json'` and never with
  `git checkout -- specs/`, which reverts the spec edits with it.
- **`command grep`, never bare `grep`.** In this environment `grep` is aliased to
  `ugrep --ignore-files` and its `--include` globs behave differently from GNU grep; a repo-wide
  search that silently missed a file is how five stale references nearly shipped twice.
- **Do not push `main` and do not merge into it.** Push `two-gauges-remote-verification` only.
- **`purlin:init --update` must show nothing pending before starting.** Run
  `python3 scripts/update/migrate.py --check --project-root .` first: it must exit `0` and report
  nothing but at most `receipt-v1`. The issuer refuses every receipt while a `legacy-*` migration is
  pending, so a pending migration makes the whole `verify:` rhythm impossible.
- **Subagents, if the user wants them.** The parent plan's execution strategy applies: one subagent
  per commit (model `"opus"`), with a brief naming the files, the rule text, the proof, the
  mutation check and the commit message, returning a summary under 300 words (files changed, rules
  and proofs added, sweep counts, mutation result). Run test sweeps inside a subagent that returns
  counts and failing test names only, so the main context never holds a test log. The main context
  reads the summary, spot-checks `git diff --stat` and the spec diff, commits, issues receipts and
  updates the DONE section. Working alone in one context is equally fine; the constraint is the
  rhythm, not the delegation.

---

## 3. ADO facts the design relies on

Every fact in this section is stated from documentation knowledge and **must be verified on the
work machine** before the design that rests on it is committed. Section 7's commit 0 is the
verification pass, and section 9 records what happens when one of them turns out to be wrong.

- **Hosted pools.** `pool: {vmImage: 'windows-2022'}`, `vmImage: 'macOS-14'` and
  `vmImage: 'ubuntu-24.04'` are Microsoft-hosted images. The image label is what the registry's
  `runs_on` maps to. Verify the exact spellings and the current availability window: hosted images
  are retired on a schedule, and `macOS-14` in particular has been rotated more than once.
- **Dispatch.** `az pipelines run --name <pipeline> --branch <branch> --org <url> --project <name>`
  queues a run and prints JSON whose `id` is the run id. `--name` resolves a pipeline by its name,
  which is why the pipeline has to exist before anything can be dispatched.
- **Polling.** `az pipelines runs show --id <id> --org <url> --project <name>` prints the run, whose
  `status` moves through `notStarted`, `inProgress`, `completing` and `completed`, and whose
  `result` is `succeeded`, `failed`, `canceled` or `partiallySucceeded` once `status` is
  `completed`. There is no equivalent of `gh run watch`, so the skill polls with a delay.
- **Auth.** Either `az login` (interactive, or a service principal), or the `AZURE_DEVOPS_EXT_PAT`
  environment variable holding a PAT with Build (read and execute) scope, which the `azure-devops`
  extension reads. Verify which one the work machine will use and whether the PAT needs Code (read
  and write) as well for anything this plan does from the developer side (it should not: the push
  is the pipeline's, not the developer's).
- **The CLI extension.** `az extension add --name azure-devops` installs the `az pipelines` and
  `az devops` command groups. `az devops configure --defaults organization=<url> project=<name>`
  sets defaults so `--org` and `--project` can be omitted, but the skill passes both explicitly
  because the registry holds them and an implicit default is not evidence.
- **Loop guard, half one.** `trigger: {branches: {include: [...]}, paths: {exclude:
  ['**/*.proofs-*@<platform-id>.json']}}`. Verify that path filters apply to the repository type
  in use (they apply to Azure Repos Git and to GitHub repositories connected to ADO) and that the
  glob syntax accepts `**` and `@`.
- **Loop guard, half two.** `[skip ci]` in the commit subject is honoured by Azure Pipelines and
  suppresses the CI trigger for that commit (`***NO_CI***` and `[skip azurepipelines]` are the
  other accepted spellings). Verify that it is honoured for the repository type in use.
- **Checkout and credentials.** `checkout: self` with `persistCredentials: true` leaves the
  pipeline's OAuth token in the checkout's git config as an `http.extraheader`, which is what lets
  a later `git push` in a `bash` step authenticate as the pipeline.
- **The push identity.** That token is the project build service identity, typically named
  `<Project> Build Service (<organization>)`. It must be granted **Contribute** on the repository,
  and **Bypass policies when pushing** as well when the target branch carries branch policies.
  Without it the push fails with a 403 after a green test run. This is the single most common
  failure of the whole design.
- **`System.AccessToken`.** Available to a step only when explicitly mapped:
  `env: {SYSTEM_ACCESSTOKEN: $(System.AccessToken)}`. The template maps it in the commit-back step
  even though `persistCredentials` already covers the push, because anything in that step that
  later calls `az` or the REST API will need it and a missing mapping fails silently.
- **Branch variables.** `$(Build.SourceBranchName)` is the **last path segment** of the ref, so
  `refs/heads/feature/foo` yields `foo`, not `feature/foo`. `$(Build.SourceBranch)` is the full ref.
  The template therefore derives the branch as `${BUILD_SOURCEBRANCH#refs/heads/}` and the trap is
  recorded in section 9.
- **Temp directory.** `$(Agent.TempDirectory)` is the per-job scratch directory, the ADO equivalent
  of `${{ runner.temp }}`. It is where `PURLIN_PLUGIN_ROOT` points.
- **Cross-OS bash.** `steps: - bash: |` runs Bash on all three hosted OSes (Git Bash on Windows),
  which is the ADO equivalent of `shell: bash` and carries the same reason: PowerShell parses a
  leading `@` in a path as a splat, which mangles every scoped proof path.
- **Commit identity and runner string.** `git config user.name "azure-pipelines[bot]"` and an
  address under the same name; the `Purlin-Runner:` trailer value is `azure-pipelines/<vmImage>`,
  mirroring `github-actions/<runs-on>`. Nothing reads the string except the report, so the only
  requirement is that it names the runner unambiguously and is stable.

---

## 4. The design

### 4.1 Registry schema additions

The `runner` object gains three keys, so `_PLATFORM_RUNNER_KEYS` becomes
`('provider', 'runs_on', 'workflow', 'pipeline', 'organization', 'project')`:

```json
"platforms": {
  "macos-14": {
    "os": "macos",
    "version": "14",
    "arch": "arm64",
    "label": "macOS 14 (hosted)",
    "runner": {
      "provider": "ado",
      "runs_on": "macOS-14",
      "pipeline": "purlin-macos-14-proofs",
      "organization": "https://dev.azure.com/<org>",
      "project": "<project>"
    }
  }
}
```

`runs_on` is the `vmImage` label, exactly as it is the `runs-on` label for GitHub. `pipeline` is the
pipeline **name** (what `az pipelines run --name` resolves), not the YAML filename, and not a
numeric id: a name survives a pipeline being recreated and reads correctly in the `Platforms:`
block. `organization` is the full `https://dev.azure.com/<org>` URL, because that is what `--org`
takes. `project` is the project name.

### 4.2 Validation rules for them

Added to `_validate_platform_entry`, keeping its existing contract that every problem is an error
and the whole entry is dropped and named:

1. `provider` stays any non-empty string. A future provider must be **reported** as not
   dispatchable, not rejected, which is the behaviour `sync_status` RULE-52 already specifies and
   what makes the registry an extension point rather than an enum.
2. When `provider` is `ado`, `organization`, `project` and `pipeline` are all required. Each must be
   a non-empty string, and `organization` must begin with `https://`. A half-filled ado runner is an
   error rather than a dispatch note, because the skill would otherwise build an `az` command line
   out of `None`.
3. When `provider` is `ado`, `workflow` is an error, naming `pipeline` as the key it means. When
   `provider` is `github`, `pipeline`, `organization` and `project` are errors, naming `workflow`.
   The two spellings cannot be mixed up silently: a `github` runner carrying only `pipeline` would
   otherwise read as "github runner, no workflow named" and never dispatch.
4. `github` is unchanged in every other respect: `workflow` stays optional, so
   `_platform_dispatch_note`'s "github runs_on `<x>`, no workflow named" branch and its proof are
   untouched.

`_platform_dispatch_note` gains an `ado` branch before the catch-all:

```python
if provider == 'ado':
    return f'ado pipeline {runner["pipeline"]} ({runner["project"]})'
```

The catch-all stays exactly as it is for every other provider.

### 4.3 The pipeline template

New section in `references/remote_verification.md`, beside the GitHub template, under a "Provider"
heading that introduces a small table:

| `runner.provider` | Definition file | Dispatch | Poll |
|---|---|---|---|
| `github` | `.github/workflows/purlin-<platform-id>-proofs.yml` | `gh workflow run <workflow> --ref <branch>` | `gh run watch <id>` |
| `ado` | `azure-pipelines-purlin-<platform-id>.yml` (repository root) | `az pipelines run --name <pipeline> --branch <branch> --org <organization> --project <project>` | `az pipelines runs show --id <id>` until `status: completed` |
| anything else | none | not dispatchable; proofs stay awaiting | not applicable |

The definition file lives at the repository root and not under a directory, because Azure Pipelines
resolves a YAML path per pipeline rather than by convention, and a root file is the path the "New
pipeline" wizard offers first. Substitute `<platform-id>` (for example `macos-14`), `<vm-image>`
(for example `macOS-14`), `<VERSION>` (the Purlin release to pin, from this repository's `VERSION`
file, currently `0.10.0`), and the per-framework setup block and test command for the project's
`test_framework`.

```yaml
name: purlin-<platform-id>-proofs

# Loop guard, half one: the pipeline's own proof commit must not retrigger it.
# Path filters are evaluated against the commit's changed paths, and they are
# case sensitive.
trigger:
  branches:
    include:
      - '*'
  paths:
    exclude:
      - '**/*.proofs-*@<platform-id>.json'

pr: none

pool:
  vmImage: '<vm-image>'

variables:
  # The only per-runner input any proof plugin reads. It names the scoped proof
  # file the plugins write; without it they fall back to the OS family and this
  # runner's results land under `macos`, satisfying @on(macos) and not
  # @on(macos-14). Pipeline variables reach every step as environment
  # variables, so a bash step reads $PURLIN_PLATFORM with no further wiring.
  - name: PURLIN_PLATFORM
    value: <platform-id>
  # Where the Purlin tooling is checked out. In the purlin repository itself
  # set this to `.` (its own checkout) and delete the "Install Purlin tooling"
  # step below: that repository is the plugin.
  - name: PURLIN_PLUGIN_ROOT
    value: $(Agent.TempDirectory)/purlin

steps:
  # persistCredentials leaves the pipeline's OAuth token in the checkout's git
  # config, which is what lets the commit-back step push. The identity behind
  # it is the project build service, which needs Contribute on this repository
  # (and "Bypass policies when pushing" when the branch carries policies).
  # fetchDepth 0 because the commit-back rebases onto the branch.
  - checkout: self
    persistCredentials: true
    fetchDepth: 0

  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.11'
    displayName: Use Python 3.11

  - bash: |
      git clone --depth 1 --branch v<VERSION> \
        https://github.com/rlabarca/purlin.git "$PURLIN_PLUGIN_ROOT"
    displayName: Install Purlin tooling
    # A consumer checkout holds specs, proofs, receipts and `.purlin/`, and no
    # Purlin `scripts/`. Pin the tag: an unpinned clone changes what the
    # preflight enforces between one run and the next.

  - bash: python3 "$PURLIN_PLUGIN_ROOT/scripts/update/migrate.py" --check --project-root .
    displayName: Preflight
    # Fails the job when the project's `.purlin/plugins/` copies are stale or a
    # legacy migration is pending. Stale copies predate platform scoping and
    # write agnostic files that satisfy no platform, so the run would look
    # green and prove nothing.
    # -> Run: purlin:init --update and commit

  - bash: pip install pytest
    displayName: Install the test runner
    # Per-framework setup block, chosen from `test_framework`. See
    # references/supported_frameworks.md, "Runner setup".
    #   pytest        pip install pytest
    #   jest, vitest  npm ci
    #   xunit         dotnet restore
    #   php           composer install
    #   c             the platform's C toolchain
    #   shell, sql    nothing beyond python3 (UsePythonVersion above puts it on
    #                 PATH on all three hosted OSes)

  - bash: python3 -m pytest <test files> -v
    displayName: Run the <platform-id> proofs

  - bash: |
      set -e
      # $(Build.SourceBranchName) is only the LAST path segment of the ref, so
      # a branch named feature/x would come through as x and the push would
      # create a new branch. Strip the full ref instead.
      BRANCH="${BUILD_SOURCEBRANCH#refs/heads/}"
      git config user.name "azure-pipelines[bot]"
      git config user.email "azure-pipelines[bot]@users.noreply.dev.azure.com"
      # This platform's files only. The same run also writes agnostic proof
      # files for the markers that declare no platform, and those must not
      # travel back: they would overwrite the developer's own results.
      git add '**/*.proofs-*@<platform-id>.json'
      if git diff --cached --quiet; then
        echo "No proof-file changes to commit."
      else
        # Loop guard, half two, and the provenance sync_status reads back.
        # Both trailers in ONE -m, joined by a newline through printf. Each -m
        # is a separate paragraph and git parses trailers out of the LAST
        # paragraph only, so two -m flags leave `Purlin-Runner` unreadable to
        # `git log --format=%(trailers:key=Purlin-Runner)` and the report says
        # `runner not recorded` after a green run. printf rather than a literal
        # newline inside the argument: a bare newline would end this YAML
        # block scalar.
        git commit -m "test: <platform-id> proofs from <vm-image> [skip ci]" \
                   -m "$(printf 'Purlin-Runner: azure-pipelines/<vm-image>\nPurlin-Platform: <platform-id>')"
        # Several platform runners may commit to this branch at once, so the
        # first push can lose a race it did nothing wrong to lose. Three
        # attempts, then fail.
        for attempt in 1 2 3; do
          if git pull --rebase origin "$BRANCH" && \
             git push origin "HEAD:$BRANCH"; then
            exit 0
          fi
          echo "push attempt $attempt lost a race; retrying"
        done
        echo "could not push the proof commit after 3 attempts"
        exit 1
      fi
    displayName: Commit the proof files back to the branch
    env:
      SYSTEM_ACCESSTOKEN: $(System.AccessToken)
```

Every element the GitHub template carries is present here in its ADO spelling: the name, the path
exclusion, the pool, both variables, the checkout with persisted credentials, the tooling clone
pinned by tag, the preflight, the per-framework setup, the test command, the narrowed `git add`,
the `git diff --cached --quiet` guard, both trailers in one `-m`, `[skip ci]`, the three-attempt
pull-rebase-retry loop ending in `exit 1`, and bash on every step. The "What is load-bearing in
that template" section of `references/remote_verification.md` gains one paragraph per ADO-only
item: the build service permission, `persistCredentials`, the `Build.SourceBranchName` trap and
`System.AccessToken`.

### 4.4 The `provider: ado` branch in `skills/test/SKILL.md`

**Step 2b.** The existing paragraph that branches on `platforms.<id>.runner` gains a third arm,
before the catch-all. Draft text:

> **If it has a `runner` block with `provider: ado`**, dispatch it with the Azure CLI. This needs
> the `azure-devops` extension (`az extension add --name azure-devops`) and an authenticated
> session (`az login`, or `AZURE_DEVOPS_EXT_PAT` in the environment). The round is the same one
> round as for GitHub, with two commands substituted:
>
> 1. Push the current branch, once, as above. Every runner proves the same commit.
> 2. Dispatch each remote ADO platform:
>    `az pipelines run --name <pipeline> --branch <branch> --org <organization> --project <project>`,
>    reading `pipeline`, `organization` and `project` from `platforms.<id>.runner`. Capture the
>    `id` from the JSON it prints; that is the run id.
> 3. Poll each run: `az pipelines runs show --id <id> --org <organization> --project <project>`
>    until `status` is `completed`, then read `result` (`succeeded`, `failed`, `canceled` or
>    `partiallySucceeded`). There is no `gh run watch` equivalent, so poll with a delay between
>    calls rather than in a tight loop, and report the wait: a platform runner is minutes, not
>    seconds. Treat anything other than `succeeded` as a failed round.
> 4. One `git pull --ff-only` after every run has completed, retried once, exactly as for GitHub.
>    One pull, not one per runner.
>
> Mixed providers are one round, not two: push once, dispatch every platform whatever its provider,
> await them all, pull once.

The catch-all keeps its current wording for every provider that is neither `github` nor `ado`. The
3-round bound (RULE-10) and the not-converging block are unchanged and cover both providers.

**The setup offer.** The offer gains an `ado` form that writes `azure-pipelines-purlin-<id>.yml` at
the repository root and the `runner` block, both or neither, only on a yes, and then states plainly
the two things the skill cannot do:

> For `provider: ado` I can write the pipeline definition and register it in
> `.purlin/config.json`. Two steps are yours, because a skill cannot do them:
>
> 1. **Create the pipeline once in Azure DevOps** from the committed YAML file (Pipelines, New
>    pipeline, point it at this repository and at `azure-pipelines-purlin-<id>.yml`, and run it
>    once). `az pipelines run --name` resolves a pipeline by name, so nothing can be dispatched
>    until a pipeline of that name exists.
> 2. **Grant the project build service Contribute on this repository** (`<Project> Build Service
>    (<organization>)`), and "Bypass policies when pushing" as well when the branch carries
>    policies. Without it the commit-back step fails with a 403 after a green test run, which reads
>    as a proof failure and is not one.
>
> Until both are done the platform's proofs keep reporting as awaiting a runner. That is a recorded
> gap, not a failure.

The sentence recording that this consent path is the one place a skill other than `purlin:init`
writes the config is unchanged and still applies.

### 4.5 The `Platforms:` block wording for ado

`runner: <id> (N proofs; ado pipeline <name> (<project>))`. It sits beside the existing
`github workflow <name>`, `no runner configured`, `runner provider <x> is not one purlin:test can
dispatch` and `unregistered` forms, and is produced by the same `_platform_dispatch_note`.

### 4.6 `verify_gate` generalised to both definition formats

- The spec's `> Scope:` line becomes
  `scripts/ci/verify_gate.py, .github/workflows/verify-gate.yml, .github/workflows/*-proofs.yml, azure-pipelines-purlin-*.yml`,
  so a new ADO definition joins the scope by existing, exactly as the GitHub glob already works.
- RULE-7, RULE-10 and RULE-11 are reworded from "every workflow that commits a proof file back" to
  "every commit-back definition, whether a GitHub Actions workflow under `.github/workflows/` or an
  Azure Pipelines definition at `azure-pipelines-purlin-*.yml`", and their proofs iterate both
  globs. RULE-10's branch variable becomes "the provider's own branch variable
  (`$GITHUB_REF_NAME` on GitHub Actions, the branch derived from `$BUILD_SOURCEBRANCH` on Azure
  Pipelines)" rather than the GitHub literal.
- RULE-8 is reworded to "a path exclusion for the proof files it writes (`paths-ignore` on GitHub
  Actions, `trigger.paths.exclude` on Azure Pipelines) and `[skip ci]` in the commit subject".
- RULE-11's "the step whose `name` begins with `Run`" becomes "the step that runs the proofs,
  identified by its `name` on GitHub Actions and its `displayName` on Azure Pipelines, either of
  which begins with `Run`".
- In `dev/test_verify_gate.py`, `_workflows_that_commit_proofs()` becomes
  `_commit_back_definitions()`, returning `[(path, text)]` over both `.github/workflows/*.yml` and
  the repository root's `azure-pipelines-purlin-*.yml`, matched the same way (a `git add` against a
  `*.proofs-*.json` path plus a `git commit`). Every existing caller (PROOF-7, PROOF-8, PROOF-10,
  PROOF-11) switches to it, so the four rules cover an ADO definition the day one lands.
- `verify_gate.py` itself does not change. It reads the payload and never reads a workflow file.
- `.github/workflows/verify-gate.yml`'s path triggers gain `azure-pipelines-purlin-*.yml`, so a
  change to an ADO definition re-runs the gate that reads what it commits. RULE-2 names the trigger
  paths, so RULE-2 and PROOF-2 are amended with it.

### 4.7 Docs

- `references/remote_verification.md`: the provider table of 4.3, the ADO template in full, the
  ADO paragraphs in "What is load-bearing in that template", and one sentence in "Setting it up"
  saying that the offer is per provider and that the ADO form leaves two manual steps.
- `docs/testing-workflow-guide.md`: the parent plan's Phase 11 adds a "Platforms" section to this
  file. If it is present when this plan runs, extend it with one paragraph naming the two providers
  and pointing at `remote_verification.md`; if it is not, add the paragraph to the `@on(...)` prose
  that already sits under "Test Tiers" (around the `@on(<platform-id>)` table row) and leave the
  section to Phase 11. Do not write a second copy of the provider table: one table, in
  `remote_verification.md` (CLAUDE.md deduplication).
- `docs/installation-guide.md`: the "Config System" section's default config sample is the template
  config and must stay exactly that (it is asserted against `templates/config.json` by `skill_init`
  RULE-9), so the `platforms` sample goes in a short paragraph **after** the sample, showing one
  `github` entry and one `ado` entry and saying that `purlin:init` never writes the field and
  `purlin:test` writes the `runner` block with consent.
- `references/supported_frameworks.md`: the **Runner setup** cells are already provider neutral
  (they name installers, not CI syntax) and all eight are non-empty. Confirm with
  `python3 -m pytest dev/test_purlin_references.py -k runner_setup` and change nothing. Record the
  confirmation in the DONE section so the next reader does not re-open the question.

### 4.8 The migration angle

There is none, and that is worth stating in the DONE section rather than leaving implicit. No
format changes: `references/formats/proofs_format.md` stays at Format-Version 5 (scoped file names
and the four-part merge key are provider agnostic), `receipt_format.md` stays at 2 (the
`proof_files` rows name a runner string, and `azure-pipelines/macOS-14` is one), and
`spec_format.md` is untouched (`@on(...)` says nothing about who runs it). `_pending_migrations`
gains no id, `scripts/update/migrate.py` is unchanged, and `purlin:init --update` is unaffected: a
project that adds an ADO runner edits its config and adds a file, which is authoring, not
migration. The one contract that does change shape is `_PLATFORM_RUNNER_KEYS`, and a config written
against the old key set stays valid, because every new key is optional for `github`.

---

## 5. Rules and proofs

Next free numbers, verified against the specs at this branch's base commit. Allocation is by
**landing order**: each commit takes the next free number in that spec file at the time it lands,
and never reuses a number named earlier in this plan.

| Spec | Max now | This plan takes |
|---|---|---|
| `specs/mcp/sync_status.md` | RULE-62 / PROOF-101 | RULE-63 / PROOF-102, and RULE-52 amended with PROOF-85 rewritten |
| `specs/skills/skill_test.md` | RULE-11 / PROOF-11 | RULE-12 / PROOF-12 and RULE-13 / PROOF-13 |
| `specs/instructions/purlin_references.md` | RULE-27 / PROOF-27 | RULE-28 / PROOF-28 |
| `specs/ci/verify_gate.md` | RULE-11 / PROOF-11 | RULE-12 / PROOF-12, with RULE-2/7/8/10/11 amended |
| `specs/mcp/config_engine.md` | RULE-11 / PROOF-13 | nothing (see 5.6) |

Phase 6.6 rewrote `skill_test` RULE-7 through RULE-11 and PROOF-7 through PROOF-11 in place rather
than adding numbers, which is why `skill_test` is still at 11 and 11.

### 5.1 `sync_status` RULE-63 (registry validation for the ado runner fields)

Draft rule text:

> RULE-63: A `runner` block may carry `pipeline`, `organization` and `project` beside `provider`,
> `runs_on` and `workflow`, and the keys a provider needs are validated against the provider it
> declares. `provider: "ado"` requires all three of `organization` (a non-empty string beginning
> `https://`), `project` and `pipeline` (the pipeline name `az pipelines run --name` resolves, not
> a numeric id and not a filename), and rejects `workflow` naming `pipeline` as the key it means;
> `provider: "github"` rejects `pipeline`, `organization` and `project` naming `workflow`. Any other
> provider carries whatever it carries and is reported, never rejected, because the registry is an
> extension point and a provider Purlin cannot dispatch is a recorded gap and not a config error. A
> half-filled `ado` runner is dropped and named like any other malformed entry rather than becoming
> a dispatch note, because `purlin:test` would otherwise build an `az` command line out of a missing
> field and report the failure as the platform's.

Draft proof description (PROVABLE):

> PROOF-102 (RULE-63): Call `_platform_registry` on a config whose `platforms` carries `mac-ok`
> (`os: macos`, an ado runner with `runs_on`, `pipeline`, `organization` and `project`), `mac-noorg`
> (an ado runner with no `organization`), `mac-httporg` (an ado runner whose `organization` is
> `dev.azure.com/x` with no scheme), `mac-both` (an ado runner carrying `workflow` as well),
> `win-pipeline` (a github runner carrying `pipeline`) and `win-ok` (a github runner with only
> `workflow`); verify the registry holds `mac-ok` and `win-ok` with their runner blocks intact and
> that exactly four errors are returned, each naming its id and the key at fault, with the
> `mac-both` error naming `pipeline` and the `win-pipeline` error naming `workflow`. Write the same
> config into a project, declare a proof `@on(mac-ok)` and run `sync_status`; verify the
> `Platforms:` block's `runner:` line for `mac-ok` reads `ado pipeline <name> (<project>)` and that
> the four dropped ids are named in the preamble's `Platform registry` block. @integration

Test file: `dev/test_mcp_server.py`, class `TestPlatformRegistry` (where PROOF-82, PROOF-83 and
PROOF-84 already live). Mutations: (a) accept an ado runner with no `organization` (remove the
required-key check) and PROOF-102 fails at the error count; (b) leave `workflow` permitted on an
ado runner and it fails at the `mac-both` case; (c) leave `_platform_dispatch_note`'s
`provider != 'github'` catch-all in front of the ado branch and the `runner:` line reads "not one
purlin:test can dispatch" instead.

### 5.2 `sync_status` RULE-52 amended (the ado dispatch note)

RULE-52 currently enumerates the four `runner:` line forms. It gains a fifth: `ado pipeline <name>
(<project>)` when the provider is `ado`. PROOF-85 is rewritten in place, and its worked example of
a non-dispatchable provider **must move off `ado`**: today it reads "register `provider: ado` and
verify `runner provider ado is not one purlin:test can dispatch`", asserted at
`dev/test_mcp_server.py:1188`. Replace it with a provider that stays undispatchable, for example
`jenkins`, and add the ado case beside it. Mutation: drop the ado branch from
`_platform_dispatch_note` and PROOF-85 fails on the ado line while still passing on the jenkins
line, which is what proves the two arms are distinguished.

### 5.3 `skill_test` RULE-12 (the ado dispatch branch in Step 2b)

Draft rule text:

> RULE-12: Step 2b branches on the platform's `runner.provider` and documents one dispatch and one
> poll command per provider it can reach: `gh workflow run` with `gh run watch` for `github`, and
> `az pipelines run --name <pipeline> --branch <branch> --org <organization> --project <project>`
> with `az pipelines runs show --id <id>` polled until `status` is `completed` for `ado`, reading
> the three ado fields from the registry entry rather than from a default. The ado arm states that
> there is no watch command, so the poll has a delay between calls, and that a `result` other than
> `succeeded` is a failed round. A provider that is neither is still reported as not dispatchable.
> The round is one round whatever the mix of providers: one push, every platform dispatched, all
> awaited, one `git pull --ff-only`, because a second push or a second pull races the runners that
> are still committing.

Draft proof description (STRUCTURAL, a grep over skill prose, which is the only proof a rule about
a document can have, matching `skill_test` PROOF-10 and `purlin_references` PROOF-22):

> PROOF-12 (RULE-12): Grep `skills/test/SKILL.md` Step 2b for the provider branch; verify the
> literals `provider: github` and `provider: ado` both appear as conditions, that the ado arm
> carries `az pipelines run`, `--name`, `--branch`, `--org`, `--project`, `az pipelines runs show`,
> `status` and `completed`, that it states no watch command exists and that a `result` other than
> `succeeded` is a failed round, and that the single-push, single-pull sentences sit outside both
> arms so they govern a mixed round. Verify the not-dispatchable sentence survives for any other
> provider, and that the 3-round bound is stated once and not once per provider. Deleting the
> `az pipelines runs show` sentence, or moving the `git pull --ff-only` inside one arm, fails the
> proof.

Test file: `dev/test_skill_specs.py`, class `TestTestSkillPlatforms` (where PROOF-7 through
PROOF-11 live, from line 1770). Mutations: delete the polling sentence; move the pull inside the
github arm.

### 5.4 `skill_test` RULE-13 (the setup offer's ado limits)

Draft rule text:

> RULE-13: The setup offer is per provider. For `ado` it writes `azure-pipelines-purlin-<id>.yml`
> at the repository root and the `runner` block carrying `provider`, `runs_on`, `pipeline`,
> `organization` and `project`, both or neither and neither without consent, and it then names the
> two steps it cannot perform: the pipeline must be created once in Azure DevOps from the committed
> YAML file, because `az pipelines run --name` resolves a pipeline by name and cannot create one;
> and the project build service identity must be granted Contribute on the repository, plus Bypass
> policies when pushing when the branch carries policies, because the commit-back pushes as that
> identity and a missing grant fails with a 403 after a green test run. It states that the platform
> keeps reporting as awaiting a runner until both are done, and that this is a recorded gap and not
> a failure. Offering to scaffold without naming the two manual steps produces a project that
> dispatches nothing and reads the silence as a proof problem.

Draft proof description (STRUCTURAL):

> PROOF-13 (RULE-13): Grep the setup-offer section of `skills/test/SKILL.md`; verify the ado form
> names `azure-pipelines-purlin-<id>.yml` and all five `runner` keys, that the consent and
> both-or-neither sentences govern it, that it carries a sentence saying the pipeline must be
> created once in Azure DevOps and gives the `az pipelines run --name` reason, that it carries a
> sentence naming the build service identity, Contribute, and Bypass policies when pushing, and
> that it says the proofs stay awaiting until both are done. Verify `skills/init/SKILL.md` still
> contains no remote-verification setup step of its own. Deleting either manual-step sentence fails
> the proof.

Test file: `dev/test_skill_specs.py`, same class. Mutations: delete the pipeline-creation sentence;
delete the permissions sentence. Each must fail PROOF-13 alone.

### 5.5 `purlin_references` RULE-28 (the ADO template elements)

Draft rule text, mirroring RULE-18 clause for clause:

> RULE-28: `remote_verification.md` carries a provider table naming, for each dispatchable
> `runner.provider`, the definition file it scaffolds, the dispatch command and the poll command,
> and it carries an Azure Pipelines template parameterized by `<platform-id>` and `<vm-image>`. The
> template block itself carries every element a copy of it needs to work: `name:
> purlin-<platform-id>-proofs`; a `trigger` whose `paths.exclude` matches
> `**/*.proofs-*@<platform-id>.json`; `pool.vmImage`; `variables` setting both `PURLIN_PLATFORM`
> and `PURLIN_PLUGIN_ROOT`; a `checkout: self` with `persistCredentials: true`; a step cloning this
> repository at a pinned `v<VERSION>` tag into `$PURLIN_PLUGIN_ROOT`; a step running
> `migrate.py --check` from `$PURLIN_PLUGIN_ROOT`; a per-framework setup block; the test command;
> `bash` as the shell of every command step; a `git add` narrowed to
> `**/*.proofs-*@<platform-id>.json`; a `git diff --cached --quiet` guard; a commit carrying
> `[skip ci]`, a `Purlin-Runner:` trailer and a `Purlin-Platform:` trailer in a single `-m`; the
> branch derived from `$BUILD_SOURCEBRANCH` rather than from `Build.SourceBranchName`, which is only
> the last path segment of the ref; and a pull-rebase-retry loop of three attempts that exits 1
> after them. The prose around it states the build service permission the push needs. A template
> copied without any one of these produces an infinite trigger loop, a proof whose runner or
> platform is unrecorded, a runner's agnostic results overwriting the developer's, a push to a
> branch that is not the one under test, or a job that goes red because two platform runners raced
> for one branch.

Draft proof description (STRUCTURAL, like PROOF-18):

> PROOF-28 (RULE-28): Extract the fenced yaml block of `remote_verification.md` whose first line is
> `name: purlin-<platform-id>-proofs` and that carries `pool:`, and assert every required element is
> inside that block and not merely in the prose around it: `paths:` with an `exclude:` entry for
> `**/*.proofs-*@<platform-id>.json`, `vmImage`, `PURLIN_PLATFORM` and `PURLIN_PLUGIN_ROOT` under
> `variables`, `checkout: self` with `persistCredentials: true`, a `git clone --depth 1 --branch
> v<VERSION>` into `$PURLIN_PLUGIN_ROOT`, `migrate.py --check` run from `$PURLIN_PLUGIN_ROOT`, a
> per-framework setup step, a `bash:` key on every command step, `git add
> '**/*.proofs-*@<platform-id>.json'`, `git diff --cached --quiet`, `[skip ci]`, both trailers in
> one `-m`, `BUILD_SOURCEBRANCH` with no bare `Build.SourceBranchName` in a push or pull command,
> and a three-attempt loop ending in `exit 1`. Parse the provider table and assert it has a row for
> `github` and a row for `ado`, each naming a definition file, a dispatch command and a poll
> command. Grep the prose for the build service Contribute sentence. Removing `persistCredentials:
> true` from the template fails the proof.

Test file: `dev/test_purlin_references.py`, beside the PROOF-18 test at line 357, reusing the
`_yaml_blocks(text)` helper at line 34. Mutations: remove `persistCredentials: true`; replace
`${BUILD_SOURCEBRANCH#refs/heads/}` with `$(Build.SourceBranchName)`.

**Existing proofs that the new block must satisfy on its own.** `purlin_references` PROOF-22
extracts every fenced yaml block under `references/` and `docs/` and asserts that every `scripts/`
path in it is preceded by `$PURLIN_PLUGIN_ROOT/` and that any plugin clone pins `--branch
v<VERSION>`. The ADO template is inside that scan the moment it is written, so a bare
`scripts/update/migrate.py` or an unpinned clone fails an existing proof rather than a new one.
That is the intended coupling; do not weaken PROOF-22 to accommodate the new block.

### 5.6 `verify_gate` RULE-12 (both globs)

Draft rule text:

> RULE-12: A commit-back definition is a GitHub Actions workflow under `.github/workflows/` or an
> Azure Pipelines definition at `azure-pipelines-purlin-*.yml` in the repository root, and the rules
> that govern one govern both: RULE-7's two trailers in one `-m`, RULE-8's path exclusion and
> `[skip ci]`, RULE-10's three-attempt pull-rebase-retry loop, and RULE-11's preflight before the
> step that runs the proofs. The proofs for those four rules enumerate both locations and assert
> each found at least one definition, so a provider whose definitions live somewhere the scan does
> not look is a scan that passes by matching nothing. The two formats differ only in spelling: the
> path exclusion is `paths-ignore` on GitHub Actions and `trigger.paths.exclude` on Azure Pipelines,
> the proofs step is named by `name` on one and `displayName` on the other, and the branch comes
> from `$GITHUB_REF_NAME` on one and from `$BUILD_SOURCEBRANCH` on the other.

Draft proof description (STRUCTURAL, like PROOF-7 and PROOF-10):

> PROOF-12 (RULE-12): Call the definition collector used by PROOF-7, PROOF-8, PROOF-10 and PROOF-11
> and assert it returns entries from both `.github/workflows/` and the repository root's
> `azure-pipelines-purlin-*.yml` glob, that every entry it returns runs `git add` against a
> `*.proofs-*.json` path and a `git commit`, and that a definition placed in one location is
> returned while an unrelated yaml file in the same location is not. Restricting the collector to
> `.github/workflows/` fails the proof, and so does widening it to every yaml file in the
> repository root. Then assert that each of PROOF-7, PROOF-8, PROOF-10 and PROOF-11 runs against
> the collector's full result rather than a filtered subset of it. @integration

Test file: `dev/test_verify_gate.py`, whose `_workflows_that_commit_proofs()` (line 119) becomes
`_commit_back_definitions()`. Mutations: restrict the collector to `.github/workflows`; commit an
ADO definition with the two trailers in two `-m` flags and confirm PROOF-7 fails on it (this is the
mutation that proves the generalisation is real and not decorative), then restore.

### 5.7 `config_engine`: nothing, and why

The registry schema does not live in `config_engine`. That spec's `> Scope:` is
`scripts/mcp/config_engine.py`, which resolves and overlays config files and knows nothing about
what a key means; the schema lives in `_validate_platform_entry` in the server and is specced by
`sync_status` RULE-50. So this plan adds no `config_engine` rule.

One correction to carry: the brief for this plan says `config_engine` RULE-12 and PROOF-14 are
taken. In the tree they are not; the live maxima are RULE-11 and PROOF-13. They are **allocated**
to Phase 10.6 (environment-kind registry entries) in the parent plan's "Reviewer findings applied"
table, which has not landed. If 10.6 lands before anything here needs a `config_engine` rule, the
next free pair is RULE-13 and PROOF-15; if it has not, it is RULE-12 and PROOF-14. Check the file
at landing time rather than trusting either number.

---

## 6. Prerequisites on the work machine

Run this list top to bottom before commit 0. Every item is a hard prerequisite except where noted.

1. **Python 3.11** and a venv with pytest:
   `python3 -m venv .venv && .venv/bin/pip install -q pytest playwright`, then
   `export PATH="$PWD/.venv/bin:$PATH"`. pytest is not installed system wide.
2. **The plugin cloned at this branch.** `git clone https://github.com/rlabarca/purlin.git`, then
   `git fetch && git checkout two-gauges-remote-verification`. On a fresh clone `main` looks
   ancient; that is expected, and the branch is the truth. Confirm `git log --oneline -1` shows a
   `verify:` commit and `python3 scripts/update/migrate.py --check --project-root .` exits 0.
3. **`az`** installed, plus the extension: `az extension add --name azure-devops`. Confirm with
   `az pipelines -h`.
4. **An Azure DevOps organization and project.** A free organization is enough for the pipeline
   itself.
5. **Defaults set:** `az devops configure --defaults organization=https://dev.azure.com/<org>
   project=<project>`. The skill still passes `--org` and `--project` explicitly; this is for the
   manual commands in the checklist.
6. **Authentication:** `az login`, or `export AZURE_DEVOPS_EXT_PAT=<pat>` with a PAT carrying Build
   (read and execute). Confirm with `az pipelines list --org <url> --project <name>`.
7. **A hosted pool with parallelism.** The Microsoft-hosted pool on a new free organization has no
   parallel jobs granted by default and needs a free-tier request, which is a manual form with a
   turnaround measured in days. **Start this first**, before anything else in this plan: every
   verification step in section 8 depends on it. Request a macOS or Windows hosted parallel job;
   Linux alone will not exercise the case the platform model exists for, though it is enough to
   prove the loop mechanically.
8. **A scratch consumer project pushed to an ADO repo.** This repository's own CI is GitHub
   Actions, so the ADO loop cannot be exercised here at all, and that is not a shortcoming of this
   plan: a consumer project is also the only place the `PURLIN_PLUGIN_ROOT` clone and the preflight
   are exercised for real. Build it like this:
   - `mkdir purlin-ado-scratch && cd purlin-ado-scratch && git init`, create the ADO repo in the
     project, and push an initial commit.
   - Run `purlin:init` in it, selecting pytest as the framework. This writes `.purlin/config.json`,
     `.purlin/plugins/pytest_purlin.py` and the hooks.
   - Write one spec with two rules and two proofs, one agnostic and one platform declared:
     `- PROOF-1 (RULE-1): the parser rejects an empty token @unit` and
     `- PROOF-2 (RULE-2): the path separator is the platform's own @unit @on(macos-14)`. The second
     one must be something only that platform can answer, or Pass D grades the description LOOSE.
   - Write the two tests with `@pytest.mark.proof(...)` markers, the second carrying
     `platforms=("macos-14",)`.
   - Add `platforms.macos-14` to `.purlin/config.json` with the ado `runner` block of 4.1.
   - Commit and push. `sync_status` there must read PROOF-2 as awaiting a runner.
9. **`gh` is not needed** on this machine. Nothing in this plan dispatches a GitHub workflow from
   here; this repository's own `purlin-windows-2022-proofs` workflow runs on push without a manual
   dispatch, and its results arrive through `git pull --ff-only`.

---

## 7. Commit sequence

Each `feat`/`fix`/`docs` commit carries code, spec rules and proofs together. After each: run the
sweep in the foreground, check `git diff --stat specs/`, `python3 dev/issue_receipts.py`, then a
separate `verify:` commit. Push after each pair and `git pull --ff-only` afterwards.

**Commit 0 (no code): verify section 3 on the work machine.** Create the pipeline by hand in the
scratch project from a hand-written copy of the 4.3 template, run it once, and confirm: the image
labels resolve, the path exclusion suppresses the retrigger, `[skip ci]` suppresses it on the other
trigger path, `persistCredentials` lets the push through once the build service has Contribute,
`az pipelines run --name` returns an id, `az pipelines runs show --id` reports `status` and
`result`, and the commit-back's trailers read back through
`git log -1 --format=%(trailers:key=Purlin-Runner,valueonly)`. **Do not write a line of the plan's
code before this passes.** Record each verified fact, and each one that turned out different, in a
`## DONE` section written before commit 1. This commit produces no repository change except that
DONE section, which lands with commit 1.

**Commit 1: `feat(sync_status): the platforms registry accepts an Azure DevOps runner`.**
`_PLATFORM_RUNNER_KEYS`, the provider-keyed validation in `_validate_platform_entry`, the `ado`
branch in `_platform_dispatch_note`; `sync_status` RULE-63 with PROOF-102, RULE-52 amended with
PROOF-85 rewritten (its `ado` example moved to `jenkins`); `dev/test_mcp_server.py`. Then `verify:`.
DONE expectations: the three new runner keys named, the four validation decisions of 4.2 stated
including the reason each is an error rather than a warning, the mutations of 5.1 and 5.2 listed
with which proof caught each, the Pass D result for both descriptions, the sweep count delta
(expect +1 or +2 tests), and a note that `provider` stayed an open string on purpose.

**Commit 2: `feat(purlin_references): the Azure Pipelines commit-back template`.**
`references/remote_verification.md` gains the provider table, the ADO template and the ADO
paragraphs of "What is load-bearing"; `purlin_references` RULE-28 with PROOF-28;
`dev/test_purlin_references.py`. Then `verify:`. DONE expectations: confirmation that the existing
PROOF-22 scan accepted the new block without being weakened, the Pass D grade (STRUCTURAL is
expected and correct here), the two mutations of 5.5, and the confirmation from 4.7 that
`supported_frameworks.md` needed no change.

**Commit 3: `feat(verify_gate): the commit-back rules cover Azure Pipelines definitions`.** The
spec's Scope line, RULE-2/7/8/10/11 reworded, RULE-12 with PROOF-12,
`_commit_back_definitions()` in `dev/test_verify_gate.py` with its four callers switched,
`.github/workflows/verify-gate.yml` path triggers. Then `verify:`. DONE expectations: the reworded
clauses quoted, the fact that no existing GitHub definition changed, the mutation where an ADO
definition with two `-m` flags is caught by PROOF-7 (which is what proves the generalisation is
real), and the sweep count.

**Commit 4: `feat(skill_test): dispatch and poll an Azure DevOps pipeline`.**
`skills/test/SKILL.md` Step 2b's third arm and the setup offer's ado form; `skill_test` RULE-12 and
RULE-13 with PROOF-12 and PROOF-13; `dev/test_skill_specs.py`. Then `verify:`. DONE expectations:
the two manual steps quoted verbatim from the skill, confirmation that the 3-round bound is stated
once and not per provider, the four mutations of 5.3 and 5.4, and confirmation that
`skills/verify/SKILL.md` still contains no `git push`, `gh workflow run`, `az pipelines` or
`git pull` (PROOF-8's assertion list gains `az pipelines`).

**Commit 5: `docs: Azure DevOps runners in the testing workflow and installation guides`.**
`docs/testing-workflow-guide.md` and `docs/installation-guide.md` per 4.7. `docs/` is in no spec's
Scope, so no vhash moves and a `verify:` commit is usually unnecessary; run the issuer anyway and
commit only if it produces a diff. DONE expectations: which of the two files Phase 11 had already
touched, and the confirmation that no provider table was duplicated.

**Commit 6 (in the scratch project, not this repository): the dogfood.** Scaffold the pipeline
through the skill's own setup offer rather than by hand, dispatch through `purlin:test`, and let
the pipeline commit back. Then a final commit here carrying the `## DONE` section for the whole
plan, plus any correction the dogfood forced. If the dogfood forces a code change, it gets its own
`fix(...)` commit with a rule and a proof like everything else, and the DONE section records it as
a defect the dogfood found.

---

## 8. Verification checklist

- **The scratch project's pipeline commits back with both trailers.** In the scratch clone, after a
  green run and a `git pull --ff-only`:
  `git log -1 --format='%(trailers:key=Purlin-Runner,valueonly)|%(trailers:key=Purlin-Platform,valueonly)' -- specs/**/*.proofs-unit@macos-14.json`
  prints `azure-pipelines/macOS-14|macos-14`. An empty first field means the two trailers were
  split across two `-m` flags, which is the exact defect `verify_gate` RULE-7 exists for.
- **`sync_status` in the scratch project reads the proof as remotely proved.** The per-feature line
  reads `✓ macos-14: 1/1 proved remotely <when> (azure-pipelines/macOS-14)` and the `Platforms:`
  block's `runner:` line reads `ado pipeline purlin-macos-14-proofs (<project>)`. Neither
  `runner not recorded` nor `trailer says <x>` appears.
- **`purlin:test` dispatches and pulls.** Running the skill in the scratch project with the proof
  file deleted dispatches one `az pipelines run`, polls to `status: completed` with
  `result: succeeded`, does one `git pull --ff-only`, and reports the platform line. A second run
  with nothing to change ends with the pipeline's "No proof-file changes to commit."
- **The preflight fires.** Make one `.purlin/plugins/` copy stale in the scratch project, push, and
  confirm the pipeline fails at the Preflight step naming `purlin:init --update`, before the proofs
  step runs.
- **The loop guard holds.** The pipeline's own commit-back does not start a second run. Check the
  run list for the scratch project after a commit-back: exactly one run per developer push.
- **`python3 scripts/ci/verify_gate.py --check --project-root .` exits 0** in this repository, and
  exits 0 in the scratch project too once its proof is back (its `remote_verification` should be
  set to `optional` for the exercise; set it to `required` once and confirm the awaiting proof
  exits 1, then set it back).
- **This repository's sweep is green.** `bash dev/run_tests.sh` in the foreground, 0 failed, and
  `git diff --stat specs/` shows insertions only apart from any test rename. The base sweep for this
  branch is 14 suites; the count at the base commit is whatever the last `verify:` commit recorded,
  and each commit here adds its own new tests and nothing else.
- **`python3 scripts/update/migrate.py --check --project-root .` exits 0** in this repository and in
  the scratch project (at most `receipt-v1` listed).
- **`python3 dev/issue_receipts.py` issues every feature it issued before and skips none it did not.**
  The count must not fall. The base is `features=35/37 anchors=5/5`.
- **The proof-quality gate, as in the parent plan.** After each commit's spec edits,
  `python3 scripts/audit/static_checks.py --check-proof-design --project-root .` reads zero
  UNPROVABLE and zero LOOSE among the descriptions this plan wrote. Every proof has its mutation
  recorded. Before any merge: `purlin:audit --design` reads no UNPROVABLE across the repository and
  Design at or above 91%, and `purlin:audit` measures the features this plan touched with no HOLLOW
  and no WEAK.
- **No dashes.** `command grep -rn "$(printf '\u2014\\|\u2013')"` over every file this plan touched finds nothing new
  outside `purlin_server.py`'s existing output separators.

---

## 9. Traps

**Carried from the parent plans' execution notes, and all of them still apply here:**

- Never run a subset of test suites, and never a subset of tests inside one file. The write-scoped
  overwrite is keyed per test file, so a partial run drops the proofs you skipped. Run whole files,
  finish with `bash dev/run_tests.sh`, and read `git diff --stat specs/` before committing. This bit
  three separate phases of the parent plan, most recently through a `pytest -k` used for a mutation
  check.
- Never `git checkout -- specs/` to undo proof churn: it reverts the spec `.md` edits with it. Use
  `git checkout -- 'specs/**/*.proofs-*.json'`.
- Run the sweep in the **foreground**. A background sweep alongside a waiting shell was killed by
  the OS for memory and churned the proof files.
- A mutation that "survives" may be a stale `.pyc`. Re-run with `PYTHONDONTWRITEBYTECODE=1` and
  `__pycache__` removed before believing a surviving mutation.
- `command grep`, never bare `grep`.
- Receipts reference committed state: specs and proofs first, then the issuer, then a separate
  `verify:` commit. Re-running the issuer rewrites `commit` and `timestamp` on every receipt; that
  is churn, not a defect.
- A plan edit amended into a feature commit moves HEAD, and the run marker then no longer matches
  it, so the issuer refuses. Put the DONE section in its own commit after the `verify:` commit, or
  in the feature commit before the sweep, never in between.
- Three suites cannot run on a developer machine and their proofs are committed from elsewhere
  (`test_e2e_figma_web.py`, `test_windows_native.py`, `test_e2e_cross_model_audit.sh`). Do not
  "fix" their proofs by running something else.
- Do not restore `.claude/settings.json`; `"enabledPlugins": {}` is correct, and the `.bak` stays
  uncommitted.
- Every rule change ships with its proof in the same commit; dev tests locking in old behaviour get
  updated, not deleted around.

**ADO specific, in rough order of how likely each is to cost a day:**

- **The build service permission is the usual failure.** A green test run followed by a red
  commit-back step with a 403 is not a proof failure and must not be reported as one. Grant
  Contribute to `<Project> Build Service (<organization>)` on the repository, in Project Settings,
  Repositories, the repository, Security. Add "Bypass policies when pushing" when the branch has
  policies. Check this before debugging anything else in the commit-back step.
- **`[skip ci]` must be in the commit subject**, not in the body and not in a trailer. The template
  puts it in the first `-m`, and `verify_gate` RULE-8's proof checks for the literal anywhere in the
  definition, so a subject-line mistake passes the proof and loops in production. Confirm it by
  watching the run list after a commit-back, not by reading the file.
- **`persistCredentials` is per checkout step**, not a pipeline-wide setting. A pipeline that gains
  a second `checkout:` entry, or that replaces `checkout: self` with a `checkout: none`, silently
  loses the credential and the push fails.
- **Path exclusions are case sensitive.** `'**/*.proofs-*@macos-14.json'` does not match a file
  written as `...@macOS-14.json`. The platform id charset is `[a-z0-9][a-z0-9-]*` so the **id** is
  always lower case, but `runs_on` carries the image label (`macOS-14`), and the two are different
  strings that look alike. The file name uses the id; the `vmImage` and the `Purlin-Runner:` value
  use the label.
- **`--branch` takes the short name**, not `refs/heads/<name>`. Passing the full ref to
  `az pipelines run --branch` is a common and confusing failure.
- **`$(Build.SourceBranchName)` is only the last path segment of the ref.** On
  `refs/heads/two-gauges-remote-verification` it is correct; on a branch with a slash it is not, and
  the commit-back would push to a new branch named after the last segment. The template derives the
  branch from `$BUILD_SOURCEBRANCH` for exactly this reason, and PROOF-28 asserts it.
- **`az pipelines run` needs the pipeline to exist**, and the pipeline must have been created from
  the YAML file and run at least once. The skill's setup offer cannot do either, which is why
  RULE-13 makes the skill say so.
- **Hosted macOS minutes are limited and macOS jobs queue.** Budget for it: a macOS job can wait
  minutes before starting, so the poll loop must have a generous ceiling and the skill must report
  the wait rather than looking hung. Prefer Linux or Windows for repeated debugging and save macOS
  for the final confirmation.
- **A free organization has no hosted parallelism until it is granted.** See prerequisite 7. This
  is the longest-lead item in the whole plan.
- **Pipeline variables reach steps as environment variables, but `System.AccessToken` does not**
  unless it is mapped in the step's `env:`. A step that needs it and does not map it sees an empty
  string and fails in a way that reads like a permission problem.
- **`ado` is currently a worked example of a non-dispatchable provider** in `sync_status` PROOF-85
  and at `dev/test_mcp_server.py:1188`. Commit 1 must move that example to another provider name,
  or the new behaviour and the old proof contradict each other and the sweep goes red in a way that
  looks like a regression.
- **`_workflows_that_commit_proofs()` scans `.github/workflows` only.** Adding an ADO definition
  without generalising that helper means `verify_gate` RULE-7, RULE-8, RULE-10 and RULE-11 silently
  stop covering the new file, which is worse than not having the rules: the proofs still pass, on
  nothing. Commit 3 exists before commit 4 for this reason.
- **A sibling agent is working Phase 11 in the main tree.** `references/remote_verification.md`,
  `docs/testing-workflow-guide.md` and `RELEASE_NOTES.md` are the likely collision points. Rebase
  before each commit, read the diff rather than resolving mechanically, and keep both intents.

---

## 10. TODO before pushing main

The parent plan's list in `dev/plans/platform-generic-remote-verification.md` remains the gate and
is not superseded by this one. This plan adds the following items to it, and appends whatever this
plan's execution defers rather than silently dropping it.

- [ ] Section 3's ADO facts each verified on the work machine and recorded in commit 0's DONE
      section, with any that turned out different named alongside the design change it forced.
- [ ] The scratch consumer project exercised end to end: the pipeline created through the skill's
      setup offer, dispatched by `purlin:test`, committing back with both trailers, and `sync_status`
      there reading the proof as remotely proved. This also closes the parent plan's open item
      "Consumer-CI templates exercised once against a scratch consumer project", for the ADO half.
      The GitHub half of that item is still open.
- [ ] The scratch project's location recorded (organization, project, repository) so the next
      context can re-run the loop without rebuilding it.
- [ ] `sync_status` PROOF-85's non-dispatchable example confirmed to name a provider Purlin still
      cannot dispatch, and not `ado`.
- [ ] A decision recorded on whether `provider` should become a closed set once there are two
      providers. This plan deliberately keeps it open; the argument for closing it is that a typo
      like `adoo` currently reads as a recorded gap rather than as a config error.
- [ ] `RELEASE_NOTES.md` Unreleased gains the ADO provider entry, in whatever section Phase 11's
      rewrite leaves behind, with the note that an existing `github` config needs no change.
- [ ] Anything a subagent reports as "deferred" during execution, appended as it happens.
