#!/usr/bin/env bash
# End to end: a project set up by purlin:init, walked from the first spec to a
# gate that lets a change merge.
#
# The walk is the one the plan traces. On each fixture:
#
#   1. purlin:init at gate tested
#   2. a hand-written spec and one tagged test
#   3. purlin_run.py --quick          the tests, in seconds
#   4. purlin_run.py --record --commit  the record a developer commits
#   5. verify_gate.py --check         exits 0 under tested
#   6. purlin:init --gate recorded    raises the gate
#   7. verify_gate.py --check         exits 1: a developer record does not count
#   8. a record committed under the git host's build identity, labelled ci
#   9. verify_gate.py --check         exits 0: recorded is met by that record
#  10. purlin:init --gate approved    raises again
#  11. verify_gate.py --check         exits 1: no approver list
#  12. the approver list, then verify_gate exits 1 with no approval
#  13. approve.py, signed by a throwaway key that exists only in the temp repo
#  14. verify_gate.py --check         exits 0
#
# Nothing here reaches a git host. The CI identity is a GIT_COMMITTER_NAME and
# a signature on a local commit, which is what `record_label` reads, and both
# signing keys are generated into the temp repository and deleted with it.
#
# Fixtures: python (always), typescript (when npm can install vitest, from its
# cache or a registry), xunit (when dotnet resolves; init wiring only, because
# the logger needs an assembly built by hand).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCAFFOLD="$ROOT/scripts/init/scaffold.py"
RUN="$ROOT/scripts/run/purlin_run.py"
GATE="$ROOT/scripts/ci/verify_gate.py"
APPROVE="$ROOT/scripts/review/approve.py"
export PURLIN_ROOT="$ROOT"

CI_NAME='github-actions[bot]'
CI_EMAIL='41898282+github-actions[bot]@users.noreply.github.com'

PASS=0
FAIL=0
SKIP=0
TMPDIRS=""

# The two rules this suite proves, counted apart from the run's own total:
# GATE_FAIL is what RULE-36 reads, WIRE_FAIL what RULE-37 reads.
GATE_FAIL=0
WIRE_FAIL=0
MARK=0
mark() { MARK=$FAIL; }
gate_since_mark() { GATE_FAIL=$((GATE_FAIL + FAIL - MARK)); }
wire_since_mark() { WIRE_FAIL=$((WIRE_FAIL + FAIL - MARK)); }

cleanup() { for d in $TMPDIRS; do rm -rf "$d" 2>/dev/null; done; }
trap cleanup EXIT

# A temporary directory, on GNU and BSD alike.
#
# `mktemp -d -t <prefix>` is BSD only. GNU mktemp reads the same argument as a
# template and refuses one with no X's in it, so on Linux the command fails and
# the variable is left empty. An empty directory name is the dangerous case,
# not a loud one: every path below would resolve against the working directory,
# which is this repository, and the walk would re-initialise it, commit to it
# and run its whole test suite. Both are avoided by writing the X's out and by
# stopping here when there is still no directory.
tmp_dir() {  # prefix
  # `TMPDIR` ends with a slash on macOS and has none on Linux, and the name
  # this returns is compared as a string further down, so the trailing slash
  # goes before the template is built.
  local base="${TMPDIR:-/tmp}"
  base="${base%/}"
  local d
  d="$(mktemp -d "$base/$1.XXXXXXXX" 2>/dev/null)" || d=""
  if [ -z "$d" ] || [ ! -d "$d" ]; then
    echo "  FAIL no temporary directory for $1; the suite stops here." >&2
    exit 1
  fi
  printf '%s\n' "$d"
}

pass() { PASS=$((PASS + 1)); echo "  ok   $1"; }
note() { SKIP=$((SKIP + 1)); echo "  skip $1"; }
bad() {
  FAIL=$((FAIL + 1))
  echo "  FAIL $1"
  [ -n "${2:-}" ] && echo "$2" | sed 's/^/       /'
  return 0
}

# --- assertions -----------------------------------------------------------

expect_exit() {  # name expected command...
  local name="$1" want="$2"
  shift 2
  local out
  out="$("$@" 2>&1)"
  local got=$?
  if [ "$got" = "$want" ]; then pass "$name"; else
    bad "$name (exit $got, wanted $want)" "$out"
  fi
}

expect_file() {  # name path
  if [ -e "$2" ]; then pass "$1"; else bad "$1 (no $2)"; fi
}

expect_absent() {  # name path
  if [ ! -e "$2" ]; then pass "$1"; else bad "$1 ($2 is there)"; fi
}

expect_in() {  # name needle file
  if grep -q -- "$2" "$3" 2>/dev/null; then pass "$1"; else
    bad "$1 (no \"$2\" in $3)" "$(tail -5 "$3" 2>/dev/null)"
  fi
}

# --- the project ----------------------------------------------------------

new_repo() {  # dir
  mkdir -p "$1"
  git -C "$1" init -q .
  git -C "$1" symbolic-ref HEAD refs/heads/main
  git -C "$1" config user.email dev@example.com
  git -C "$1" config user.name Dev
  git -C "$1" config commit.gpgsign false
}

init_at() {  # dir gate [args...]
  local dir="$1" gate="$2"
  shift 2
  python3 "$SCAFFOLD" --project-root "$dir" --gate "$gate" --yes "$@" \
    > "$dir/.purlin-init.log" 2>&1
}

commit_all() {  # dir message
  git -C "$1" add -A
  git -C "$1" commit -q -m "$2"
}

commit_as_ci() {  # dir
  # What CI's commit looks like to `record_label`: the build identity as the
  # committer, and a signature, because CI writes through the git host's API
  # and the git host signs what it writes. An unsigned commit claiming that
  # identity is a person's and the reader says so, so a fixture that left the
  # signature out would be refused on any machine that can check one. Nothing
  # here talks to a git host; the key is generated into the temp repository
  # and the label is read from git.
  local dir="$1" key="$1/.git/ci-signing-key"
  if [ ! -f "$key.pub" ]; then
    ssh-keygen -q -t ed25519 -N '' -C "$CI_EMAIL" -f "$key"
    printf '%s %s\n' "$CI_EMAIL" "$(cut -d' ' -f1,2 "$key.pub")" \
      > "$dir/.git/ci-allowed-signers"
    git -C "$dir" config gpg.ssh.allowedSignersFile "$dir/.git/ci-allowed-signers"
  fi
  git -C "$dir" add -A
  GIT_COMMITTER_NAME="$CI_NAME" GIT_COMMITTER_EMAIL="$CI_EMAIL" \
    git -C "$dir" -c gpg.format=ssh -c "user.signingkey=$key.pub" \
      commit -q -S -m "purlin: record for $(git -C "$dir" rev-parse --short=7 HEAD)"
}

signing_key() {  # dir email
  local dir="$1" email="$2"
  ssh-keygen -q -t ed25519 -N '' -C "$email" -f "$dir/.git/signing-key"
  printf '%s %s\n' "$email" "$(cat "$dir/.git/signing-key.pub")" \
    > "$dir/.git/allowed-signers"
  git -C "$dir" config user.email "$email"
  git -C "$dir" config user.name Approver
  git -C "$dir" config gpg.format ssh
  git -C "$dir" config user.signingkey "$dir/.git/signing-key.pub"
  git -C "$dir" config commit.gpgsign true
  git -C "$dir" config gpg.ssh.allowedSignersFile "$dir/.git/allowed-signers"
}

set_approvers() {  # dir email
  python3 - "$1" "$2" <<'PY'
import json
import os
import sys
path = os.path.join(sys.argv[1], '.purlin', 'config.json')
with open(path, encoding='utf-8') as handle:
    config = json.load(handle)
config['approvers'] = [sys.argv[2]]
with open(path, 'w', encoding='utf-8') as handle:
    json.dump(config, handle, indent=2)
    handle.write('\n')
PY
}

# `ci`, `developer` or `local` for the newest record, read the way the reader
# reads it: from the last commit that touched the file.
record_label() {  # dir
  python3 - "$1" <<'PY'
import os
import sys
sys.path.insert(0, os.path.join(os.environ['PURLIN_ROOT'], 'scripts', 'mcp'))
from purlin import records
loaded = records.load_records(sys.argv[1])
for by_os in loaded.values():
    for record in by_os.values():
        print(record.get('label'))
        sys.exit(0)
print('none')
PY
}

spec_file() {  # dir feature scope
  mkdir -p "$1/specs/core"
  cat > "$1/specs/core/$2.md" <<EOF
# Feature: $2

> Scope: $3
> Description: One rule, tagged high risk so the approved gate needs a person.

## Rules

- RULE-1: \`greet(name)\` returns \`Hello, <name>!\` [risk: high] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Call \`greet("Ada")\` and verify it returns exactly \`Hello, Ada!\` @unit
EOF
}

# --- the walk -------------------------------------------------------------
#
# Everything below is the same for every language: the fixture builder leaves a
# project with a spec, a tagged test and a plugin, and this walks the gates.

gate_walk() {  # dir language
  local dir="$1" language="$2"

  expect_exit "$language: quick run passes" 0 \
    python3 "$RUN" --all --quick --project-root "$dir"
  expect_exit "$language: verify writes and commits the record" 0 \
    python3 "$RUN" --all --record --commit --project-root "$dir"
  expect_file "$language: the record is in the tree" \
    "$(ls -d "$dir"/.purlin/records/greeting 2>/dev/null)"
  expect_exit "$language: tested is met by the developer's record" 0 \
    python3 "$GATE" --check --project-root "$dir"

  init_at "$dir" recorded
  expect_in "$language: raising to recorded writes the workflow" \
    'wrote .github/workflows/purlin.yml' "$dir/.purlin-init.log"
  expect_exit "$language: recorded refuses a developer record" 1 \
    python3 "$GATE" --check --project-root "$dir"

  # A record's file name carries the second it was written, and the reader
  # keeps the newest per operating system. Two records in the same second
  # leave which one is newest to the file name, so the walk waits a second to
  # make CI's record unambiguously the later one.
  sleep 1
  python3 "$RUN" --all --record --project-root "$dir" > "$dir/.purlin-ci.log" 2>&1
  commit_as_ci "$dir"
  if [ "$(record_label "$dir")" = "ci" ]; then
    pass "$language: a record the build identity committed is labelled ci"
  else
    bad "$language: a record the build identity committed is labelled ci" \
      "$(record_label "$dir")"
  fi
  # CI commits its record on top of the commit it observed, so the record is
  # never at HEAD. What makes it count is its `scope_tree`: the scoped files
  # still hash to what the run recorded, so the rule is Recorded.
  expect_exit "$language: recorded is met by a record CI committed" 0 \
    python3 "$GATE" --check --project-root "$dir"

  init_at "$dir" approved
  commit_all "$dir" "raise the gate to approved"
  expect_exit "$language: approved refuses an empty approver list" 1 \
    python3 "$GATE" --check --project-root "$dir"
  python3 "$GATE" --check --project-root "$dir" > "$dir/.purlin-gate.log" 2>&1
  expect_in "$language: it says which command writes the list" \
    'purlin:init --gate approved' "$dir/.purlin-gate.log"

  set_approvers "$dir" jane@acme.com
  commit_all "$dir" "name the approvers"
  expect_exit "$language: approved refuses a high-risk rule with no approval" 1 \
    python3 "$GATE" --check --project-root "$dir"

  signing_key "$dir" jane@acme.com
  expect_exit "$language: the approval is written and signed" 0 \
    python3 "$APPROVE" greeting RULE-1 --project-root "$dir"
  if [ "$(git -C "$dir" log -1 --format=%G\?)" = "G" ]; then
    pass "$language: the approval commit is signed"
  else
    bad "$language: the approval commit is signed" \
      "$(git -C "$dir" log -1 --format='%G? %an')"
  fi
  expect_exit "$language: approved is met" 0 \
    python3 "$GATE" --check --project-root "$dir"
}

# --- python ---------------------------------------------------------------

walk_python() {
  local dir
  dir="$(tmp_dir purlin-e2e-py)" || exit 1
  TMPDIRS="$TMPDIRS $dir"
  echo "--- python ---"
  new_repo "$dir"
  printf '[tool.pytest.ini_options]\n' > "$dir/pyproject.toml"
  printf 'def greet(name):\n    return "Hello, %%s!" %% name\n' > "$dir/greeting.py"

  init_at "$dir" tested
  mark
  expect_file "python: the config is written" "$dir/.purlin/config.json"
  expect_file "python: the plugin is copied" \
    "$dir/.purlin/plugins/pytest_purlin.py"
  expect_file "python: the runner is wired" "$dir/conftest.py"
  expect_absent "python: no workflow under tested" \
    "$dir/.github/workflows/purlin.yml"
  wire_since_mark

  spec_file "$dir" greeting greeting.py
  mkdir -p "$dir/tests"
  cat > "$dir/tests/test_greeting.py" <<'EOF'
import pytest

from greeting import greet


@pytest.mark.proof("greeting", "PROOF-1", "RULE-1")
def test_greet():
    assert greet("Ada") == "Hello, Ada!"
EOF
  commit_all "$dir" "the first spec and its test"
  mark
  gate_walk "$dir" python
  gate_since_mark
}

# --- typescript -----------------------------------------------------------

walk_typescript() {
  if ! command -v npm >/dev/null 2>&1; then
    note "typescript: npm does not resolve on this host"
    return 0
  fi
  local dir
  dir="$(tmp_dir purlin-e2e-ts)" || exit 1
  TMPDIRS="$TMPDIRS $dir"
  echo "--- typescript ---"
  new_repo "$dir"
  printf '{"name":"demo","private":true,"devDependencies":{"vitest":"^4.0.0"}}\n' \
    > "$dir/package.json"
  printf 'export function greet(name: string) {\n  return `Hello, ${name}!`;\n}\n' \
    > "$dir/greeting.ts"
  # The reporter loads from the project's own vitest, so the runner has to be
  # installed. A host with neither the package cached nor a way to fetch it
  # skips this fixture rather than reporting a failure that is about the host.
  if ! (cd "$dir" && npm install --prefer-offline --no-fund \
        --loglevel=error >/dev/null 2>&1); then
    note "typescript: vitest could not be installed on this host"
    return 0
  fi

  init_at "$dir" tested
  mark
  expect_file "typescript: the plugin is copied" \
    "$dir/.purlin/plugins/vitest_purlin.ts"
  expect_file "typescript: the runner is wired" "$dir/vitest.config.ts"
  wire_since_mark

  spec_file "$dir" greeting greeting.ts
  mkdir -p "$dir/tests"
  cat > "$dir/tests/greeting.test.ts" <<'EOF'
import { expect, test } from 'vitest';

import { greet } from '../greeting';

test('[proof:greeting:PROOF-1:RULE-1:unit] greets by name', () => {
  expect(greet('Ada')).toBe('Hello, Ada!');
});
EOF
  printf 'node_modules/\n' >> "$dir/.gitignore"
  commit_all "$dir" "the first spec and its test"
  mark
  gate_walk "$dir" typescript
  gate_since_mark
}

# --- xunit ----------------------------------------------------------------

walk_xunit() {
  if ! command -v dotnet >/dev/null 2>&1; then
    note "xunit: dotnet does not resolve on this host"
    return 0
  fi
  local dir
  dir="$(tmp_dir purlin-e2e-cs)" || exit 1
  TMPDIRS="$TMPDIRS $dir"
  echo "--- xunit ---"
  new_repo "$dir"
  mkdir -p "$dir/App.Tests"
  cat > "$dir/App.Tests/App.Tests.csproj" <<'EOF'
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="xunit" Version="2.6.0" />
  </ItemGroup>
</Project>
EOF
  init_at "$dir" tested
  mark
  expect_file "xunit: the logger is copied" \
    "$dir/.purlin/plugins/xunit_purlin.cs"
  expect_in "xunit: the summary says how to wire the logger" \
    'TestLogger.dll' "$dir/.purlin-init.log"
  expect_in "xunit: the summary names the runner flag" \
    'dotnet test --logger purlin' "$dir/.purlin-init.log"
  wire_since_mark
  note "xunit: the gate walk needs the logger assembly built by hand"
}

# --- the marketplace install ----------------------------------------------

walk_marketplace() {
  local dir cache installed
  dir="$(tmp_dir purlin-e2e-mk)" || exit 1
  cache="$(tmp_dir purlin-e2e-cache)" || exit 1
  TMPDIRS="$TMPDIRS $dir $cache"
  echo "--- the marketplace install ---"
  installed="$cache/purlin/purlin/$(cat "$ROOT/VERSION")"
  mkdir -p "$installed"
  for name in VERSION templates references scripts; do
    cp -R "$ROOT/$name" "$installed/"
  done
  new_repo "$dir"
  printf '[tool.pytest.ini_options]\n' > "$dir/pyproject.toml"
  printf 'def greet(name):\n    return "Hello, %%s!" %% name\n' > "$dir/greeting.py"
  mark
  CLAUDE_PLUGIN_ROOT="$installed" python3 "$installed/scripts/init/scaffold.py" \
    --project-root "$dir" --gate tested --yes > "$dir/.purlin-init.log" 2>&1
  expect_file "marketplace: the config is written" "$dir/.purlin/config.json"
  expect_in "marketplace: the pinned root is the install" \
    "$installed" "$dir/.purlin/plugin-root"
  if grep -rl "$installed" "$dir" --exclude-dir=.git 2>/dev/null \
      | grep -v 'plugin-root' | grep -q .; then
    bad "marketplace: only .purlin/plugin-root names the install"
  else
    pass "marketplace: only .purlin/plugin-root names the install"
  fi
  wire_since_mark
}

# --- run ------------------------------------------------------------------

echo "=== init end to end ==="
walk_python
walk_typescript
walk_xunit
walk_marketplace

# The two proofs this suite writes. The harness is sourced here, at the end,
# so its own shell settings never reach the walk above.
# shellcheck source=../scripts/proof/shell_purlin.sh
. "$ROOT/scripts/proof/shell_purlin.sh"
export PURLIN_PROOF_TIER=e2e
if [ "$GATE_FAIL" -eq 0 ]; then GATE_STATUS=pass; else GATE_STATUS=fail; fi
if [ "$WIRE_FAIL" -eq 0 ]; then WIRE_STATUS=pass; else WIRE_STATUS=fail; fi
purlin_proof "scaffold" "PROOF-36" "RULE-36" "$GATE_STATUS" \
  "the three gates walked on every fixture init set up"
purlin_proof "scaffold" "PROOF-37" "RULE-37" "$WIRE_STATUS" \
  "each language wired, and the marketplace install"
purlin_proof_finish

echo ""
echo "passed $PASS, failed $FAIL, skipped $SKIP"
[ "$FAIL" -eq 0 ] || exit 1
echo "init e2e ok"
