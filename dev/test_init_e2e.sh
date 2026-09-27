#!/usr/bin/env bash
# End to end: a project set up by purlin:init, walked from the first spec to a
# gate that lets a change merge.
#
# The walk is the one the plan traces. On each fixture:
#
#   1. purlin:init at gate passed
#   2. a hand-written spec and one tagged test
#   3. purlin_run.py --quick            the tests, the results, the commit
#   4. gate_check.py --check            exits 0 under passed
#   5. purlin:init --gate strong        raises the gate
#   6. gate_check.py --check            exits 1: no audit has measured it
#   7. a record and its briefs from --ci, committed under the build identity
#   8. gate_check.py --check            exits 0: strong is met by that record
#   8a. a --ci run on a signed/ tag, which commits nothing and says so
#   8b. a --ci run on a run/* branch, which commits
#  10. purlin:init --gate signed        raises again
#  11. gate_check.py --check            exits 1: no signer list
#  12. the signer list, then the gate check exits 1 with no signature
#  13. sign.py, signed by a throwaway key that exists only in the temp repo
#  14. gate_check.py --check            exits 0
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
GATE="$ROOT/scripts/ci/gate_check.py"
SIGN="$ROOT/scripts/review/sign.py"
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

expect_not_in() {  # name needle file
  if grep -q -- "$2" "$3" 2>/dev/null; then
    bad "$1 (\"$2\" is in $3)" "$(tail -5 "$3" 2>/dev/null)"
  else pass "$1"; fi
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

# A bare repository standing in for the git host, so init's prerequisites are
# answered on disk with no network: the directory name carries the host and
# one push puts `main` on it.
add_remote() {  # dir
  local dir="$1" url="$1.github-origin.git"
  git -C "$(dirname "$dir")" init --bare -q -b main "$url"
  git -C "$dir" remote add origin "$url"
  git -C "$dir" add -A
  git -C "$dir" commit -q -m "the project"
  git -C "$dir" push -q -u origin main
  TMPDIRS="$TMPDIRS $url"
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
  git -C "$dir" config user.name Signer
  git -C "$dir" config gpg.format ssh
  git -C "$dir" config user.signingkey "$dir/.git/signing-key.pub"
  git -C "$dir" config commit.gpgsign true
  git -C "$dir" config gpg.ssh.allowedSignersFile "$dir/.git/allowed-signers"
}

set_signers() {  # dir email
  python3 - "$1" "$2" <<'PY'
import json
import os
import sys
path = os.path.join(sys.argv[1], '.purlin', 'config.json')
with open(path, encoding='utf-8') as handle:
    config = json.load(handle)
config['signers'] = [sys.argv[2]]
with open(path, 'w', encoding='utf-8') as handle:
    json.dump(config, handle, indent=2)
    handle.write('\n')
PY
}

# `ci` or `local` for the newest record, read the way the reader
# reads it: from the folder the file sits in.
record_label() {  # dir
  python3 - "$1" <<'PY'
import os
import sys
sys.path.insert(0, os.path.join(os.environ['PURLIN_ROOT'], 'scripts', 'mcp'))
from purlin import records
loaded = records.load_records(sys.argv[1])
for by_os in loaded.values():
    for record in by_os.values():
        print(record.get('source'))
        sys.exit(0)
print('none')
PY
}

spec_file() {  # dir feature scope
  mkdir -p "$1/specs/core"
  cat > "$1/specs/core/$2.md" <<EOF
# Feature: $2

> Scope: $3
> Description: One rule at the strong bar: the machine settles it at strong
>   on the test strength, because no model is reachable here, and the signed
>   gate asks a person because sign_at is strong.

## Rules

- RULE-1: \`greet(name)\` returns \`Hello, <name>!\` [bar: strong] [origin: eng]

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

  expect_exit "$language: quick run passes and meets the gate" 0 \
    python3 "$RUN" --all --quick --project-root "$dir"
  expect_file "$language: the test results are in the tree" \
    "$dir/.purlin/tests/greeting.json"
  expect_file "$language: the table is in the tree" "$dir/.purlin/tests.md"
  if git -C "$dir" log -1 --format=%s | grep -q '^purlin: tests at '; then
    pass "$language: purlin:test committed the results itself"
  else
    bad "$language: purlin:test committed the results itself" \
      "$(git -C "$dir" log -1 --format=%s)"
  fi
  expect_absent "$language: no record is written at passed" \
    "$dir/.purlin/records/local/greeting"
  expect_exit "$language: passed is met by the test results" 0 \
    python3 "$GATE" --check --project-root "$dir"

  init_at "$dir" strong
  expect_in "$language: a trusted project gets no workflow" \
    'every proof runs on this operating system' "$dir/.purlin-init.log"
  expect_absent "$language: and no workflow file is written" \
    "$dir/.github/workflows/purlin.yml"
  expect_not_in "$language: and no branch rule is printed" \
    'force push' "$dir/.purlin-init.log"
  expect_exit "$language: strong refuses a project no audit has measured" 1 \
    python3 "$GATE" --check --project-root "$dir"

  # An audit anyone runs counts at strong. It writes its record under
  # .purlin/records/local/, with the briefs beside it, and commits both
  # itself under this person's own identity.
  python3 "$RUN" --all --audit --project-root "$dir" \
    > "$dir/.purlin-audit.log" 2>&1
  expect_file "$language: the audit wrote its record under local/" \
    "$dir/.purlin/records/local/greeting"
  expect_in "$language: the audit committed its own record" \
    'Record committed.' "$dir/.purlin-audit.log"
  expect_in "$language: the audit ends on the strong gate line" \
    'gate strong: 1 of 1' "$dir/.purlin-audit.log"
  if [ "$(record_label "$dir")" = "local" ]; then
    pass "$language: a record under local/ reads local"
  else
    bad "$language: a record under local/ reads local" "$(record_label "$dir")"
  fi
  expect_exit "$language: strong is met by an audit anyone ran" 0 \
    python3 "$GATE" --check --project-root "$dir"

  # A record's file name carries the second it was written, and the reader
  # keeps the newest per operating system. Two records in the same second
  # leave which one is newest to the file name, so the walk waits a second to
  # make CI's record unambiguously the later one. `--ci` is what writes the
  # briefs beside the record; the commit it would make goes through the git
  # host's API, which no temp repository has, so the walk commits them here
  # under the build identity instead.
  sleep 1
  python3 "$RUN" --all --ci --project-root "$dir" \
    > "$dir/.purlin-ci.log" 2>&1
  commit_as_ci "$dir"
  if [ "$(record_label "$dir")" = "ci" ]; then
    pass "$language: a record under ci/ reads ci"
  else
    bad "$language: a record under ci/ reads ci" "$(record_label "$dir")"
  fi
  # CI commits its record on top of the commit it observed, so the record is
  # never at HEAD. What makes it count is its `scope_tree`: the scoped files
  # still hash to what the run wrote down, so the strong cell is met.
  expect_exit "$language: strong is met by a record CI committed" 0 \
    python3 "$GATE" --check --project-root "$dir"

  # Where a CI run writes. The git host variables are what the run reads, so
  # the two cases are the two sets of variables; no request is made, because
  # no token is set.
  env GITHUB_REPOSITORY=acme/demo GITHUB_REF=refs/tags/signed/0.1.0 \
      GITHUB_REF_NAME=signed/0.1.0 \
      python3 "$RUN" --all --ci --project-root "$dir" \
      > "$dir/.purlin-tagrun.log" 2>&1
  expect_in "$language: a tag run writes nothing" \
    'Tag run: nothing is written.' "$dir/.purlin-tagrun.log"

  env GITHUB_REPOSITORY=acme/demo GITHUB_REF_NAME=run/main-0000000 \
      python3 "$RUN" --all --ci --project-root "$dir" \
      > "$dir/.purlin-runbranch.log" 2>&1
  expect_not_in "$language: a run on a run branch writes its records" \
    'Tag run:' "$dir/.purlin-runbranch.log"
  git -C "$dir" checkout -q -- . 2>/dev/null || true
  git -C "$dir" clean -qfd .purlin/records .purlin/briefs 2>/dev/null || true

  init_at "$dir" signed
  commit_all "$dir" "raise the gate to signed"
  expect_exit "$language: signed refuses an empty signer list" 1 \
    python3 "$GATE" --check --project-root "$dir"
  python3 "$GATE" --check --project-root "$dir" > "$dir/.purlin-gate.log" 2>&1
  expect_in "$language: it says which command writes the list" \
    'purlin:init --gate signed' "$dir/.purlin-gate.log"

  set_signers "$dir" jane@acme.com
  commit_all "$dir" "name the signers"

  # A local record counts at signed too. With CI's out of the way the gate
  # still reads the one the local audit wrote, and what is left is the
  # signature nobody has written.
  mv "$dir/.purlin/records/ci" "$dir/.purlin/records/aside"
  python3 "$GATE" --check --project-root "$dir" \
    > "$dir/.purlin-local.log" 2>&1
  expect_not_in "$language: a local record is not refused at signed" \
    'Not passed' "$dir/.purlin-local.log"
  expect_in "$language: what is left at signed is the signature" \
    'To sign' "$dir/.purlin-local.log"
  mv "$dir/.purlin/records/aside" "$dir/.purlin/records/ci"

  expect_exit "$language: signed refuses a rule that needs a signature" 1 \
    python3 "$GATE" --check --project-root "$dir"

  signing_key "$dir" jane@acme.com
  expect_exit "$language: the signature is written in a signed commit" 0 \
    python3 "$SIGN" greeting RULE-1 --project-root "$dir"
  if [ "$(git -C "$dir" log -1 --format=%G\?)" = "G" ]; then
    pass "$language: the signing commit is signed"
  else
    bad "$language: the signing commit is signed" \
      "$(git -C "$dir" log -1 --format='%G? %an')"
  fi
  expect_exit "$language: signed is met" 0 \
    python3 "$GATE" --check --project-root "$dir"

  # The tag is the marker of proven code, and the walk writes it when every
  # rule meets the gate. Nothing is pushed: the last line names the push.
  python3 "$SIGN" --project-root "$dir" < /dev/null \
    > "$dir/.purlin-walk.log" 2>&1
  expect_in "$language: the walk opens with the two lists" \
    'Review: 0 rules. Sign: 0 rules.' "$dir/.purlin-walk.log"
  if git -C "$dir" tag -l | grep -q '^signed/'; then
    pass "$language: the walk wrote the signed tag"
  else
    bad "$language: the walk wrote the signed tag" "$(git -C "$dir" tag -l)"
  fi
  expect_in "$language: the walk names the push for a person to run" \
    'Run: git push origin signed/' "$dir/.purlin-walk.log"

  # No git hook of any kind is installed, at commit time or at push time.
  expect_absent "$language: no pre-push shim" "$dir/.purlin/hooks/pre-push"
  expect_absent "$language: no pre-push hook" "$dir/.git/hooks/pre-push"
  expect_absent "$language: no pre-commit hook" "$dir/.git/hooks/pre-commit"
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
  add_remote "$dir"

  init_at "$dir" passed
  mark
  expect_file "python: the config is written" "$dir/.purlin/config.json"
  expect_file "python: the plugin is copied" \
    "$dir/.purlin/plugins/pytest_purlin.py"
  expect_file "python: the runner is wired" "$dir/conftest.py"
  expect_absent "python: no workflow under passed" \
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
  add_remote "$dir"

  init_at "$dir" passed
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
  add_remote "$dir"
  init_at "$dir" passed
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
    --project-root "$dir" --gate passed --yes > "$dir/.purlin-init.log" 2>&1
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
