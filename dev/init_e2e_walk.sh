#!/usr/bin/env bash
# End to end: a project set up by purlin:init, walked from the first spec to
# the signed tag.
#
#   bash dev/init_e2e_walk.sh gates|wiring|all
#
# Two tests start this walk, one per proof, because each proof needs its own
# result: `dev/test_init_e2e_gates.sh` exits on the gates the walk checks and
# `dev/test_init_e2e_wiring.sh` on how each language is set up. `wiring` skips
# the gate steps, which are most of the time; `all` runs everything and exits
# on every check.
#
# On each fixture:
#
#   1. purlin:init at gate passed, which writes an empty `tests` setting
#   2. a hand-written spec, one test carrying one marker comment, a VERSION
#   3. the first purlin_run.py --test   suggests the entry, which is written
#   4. purlin_run.py --test --commit    the work, then the evidence, committed
#   5. purlin:init --gate strong        ends on one rule to audit
#   6. purlin_run.py --audit --commit   the audit, into the same evidence
#   7. a --ci run on a signed/ tag, which writes nothing and says so
#   8. a --ci run on a run/* branch, which writes
#   9. purlin:init --gate signed        ends on one rule to sign
#  10. sign.py greeting RULE-1          signed by a throwaway key in the repo
#  11. sign.py --all                    writes the signed tag
#
# Nothing here reaches a git host. The signing key is generated into the temp
# repository and deleted with it.
#
# Fixtures: python (always), typescript (when npm can install vitest, from its
# cache or a registry), and C# with xunit, which skips only on a machine with
# no `dotnet` at all. Nothing of Purlin is installed in any fixture's tests:
# each runs its own test command, the entry its first test run suggested.
set -uo pipefail

PART="${1:-all}"
case "$PART" in
  gates|wiring|all) ;;
  *) echo "usage: $0 gates|wiring|all" >&2; exit 2 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCAFFOLD="$ROOT/scripts/init/scaffold.py"
RUN="$ROOT/scripts/run/purlin_run.py"
SIGN="$ROOT/scripts/review/sign.py"
export PURLIN_ROOT="$ROOT"

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

# The audit calls the model through the `claude` command. A fake stands first
# on PATH for the whole walk, answering `settled: yes`, so nothing here ever
# reaches the real one.
FAKE_CLAUDE="$(tmp_dir purlin-claude)"
TMPDIRS="$TMPDIRS $FAKE_CLAUDE"
python3 "$SCRIPT_DIR/fake_claude.py" install "$FAKE_CLAUDE" >/dev/null
export PATH="$FAKE_CLAUDE:$PATH"

pass() { PASS=$((PASS + 1)); echo "  ok   $1"; }
note() { SKIP=$((SKIP + 1)); echo "  skip $1"; }
bad() {
  FAIL=$((FAIL + 1))
  echo "  FAIL $1"
  [ -n "${2:-}" ] && echo "$2" | sed 's/^/       /'
  return 0
}

# --- assertions -----------------------------------------------------------

expect_code() {  # name expected got log
  if [ "$3" = "$2" ]; then pass "$1"; else
    bad "$1 (exit $3, wanted $2)" "$(tail -5 "$4" 2>/dev/null)"
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

# The key a person signs with: an SSH key named in git's own settings, set up
# with the commands purlin:sign shows when there is none.
signing_key() {  # dir email
  local dir="$1" email="$2"
  ssh-keygen -q -t ed25519 -N '' -C "$email" -f "$dir/.git/signing-key"
  git -C "$dir" config user.email "$email"
  git -C "$dir" config user.name Signer
  git -C "$dir" config gpg.format ssh
  git -C "$dir" config user.signingkey "$dir/.git/signing-key.pub"
}

# The last four characters of the key's fingerprint, which the signing line
# names the key by.
key_ending() {  # dir
  ssh-keygen -lf "$1/.git/signing-key.pub" | awk '{print $2}' | tail -c 5
}

# What purlin:test does with the entry a first run suggests: write it as the
# `tests` setting, through the call the `purlin_config` tool makes.
take_suggestion() {  # dir log
  python3 - "$1" "$2" <<'PY'
import json
import os
import sys
sys.path.insert(0, os.path.join(os.environ['PURLIN_ROOT'], 'scripts', 'mcp'))
from config_engine import update_config
prefix = 'Suggested entry: '
with open(sys.argv[2], encoding='utf-8') as handle:
    lines = [line for line in handle.read().splitlines()
             if line.startswith(prefix)]
if len(lines) != 1:
    sys.exit('no one suggested entry in %s' % sys.argv[2])
update_config(sys.argv[1], 'tests', [json.loads(lines[0][len(prefix):])])
PY
}

# The version the project states, which the signed tag is named for, and the
# logs the walk writes, which git is told to leave out.
project_files() {  # dir
  printf '0.1.0\n' > "$1/VERSION"
  printf '.purlin-*.log\n' >> "$1/.gitignore"
}

spec_file() {  # dir feature scope
  mkdir -p "$1/specs/core"
  cat > "$1/specs/core/$2.md" <<EOF
# Feature: $2

> Scope: $3
> Description: One rule, walked from its first test run to the signed tag.

## Rules

- RULE-1: \`greet(name)\` returns \`Hello, <name>!\`

## Proof

- PROOF-1 (RULE-1): Call \`greet("Ada")\` and verify it returns exactly \`Hello, Ada!\`
EOF
}

# --- the walk -------------------------------------------------------------
#
# Everything below is the same for every language: the fixture builder leaves a
# project with a spec and a marked test, and this walks the gates.

# The first test run finds no command and suggests one; with it written, the
# marked test runs through the project's own command, which is how a language
# is shown to be wired.
test_walk() {  # dir language suite
  local dir="$1" language="$2" suite="$3"
  expect_in "$language: init writes an empty tests setting" \
    '"tests": \[\]' "$dir/.purlin/config.json"
  python3 "$RUN" --feature greeting --test --project-root "$dir" \
    > "$dir/.purlin-first.log" 2>&1
  expect_in "$language: the first test run suggests the $suite entry" \
    "^Suggested entry: .*\"name\": \"$suite\"" "$dir/.purlin-first.log"
  take_suggestion "$dir" "$dir/.purlin-first.log" \
    || bad "$language: the suggested entry could not be written"
  python3 "$RUN" --feature greeting --test --project-root "$dir" \
    > "$dir/.purlin-test.log" 2>&1
  expect_in "$language: the marked test runs through purlin_run.py --test" \
    '1 rule. 1 passes its tests.' "$dir/.purlin-test.log"
  expect_in "$language: its marker is tied to its test" \
    'Markers: 1 tied to a test, 0 not tied.' "$dir/.purlin-test.log"
}

gate_walk() {  # dir language
  local dir="$1" language="$2"
  [ "$PART" = wiring ] && return 0

  python3 "$RUN" --all --test --commit --project-root "$dir" \
    > "$dir/.purlin-commit.log" 2>&1
  expect_code "$language: the test run exits 0" 0 $? "$dir/.purlin-commit.log"
  expect_file "$language: the evidence is in the tree" \
    "$dir/.purlin/evidence/local/greeting.json"
  expect_file "$language: the table is in the tree" "$dir/.purlin/tests.md"
  local work evidence
  work="$(git -C "$dir" log -1 --format=%s HEAD~1)"
  evidence="$(git -C "$dir" log -1 --format=%s HEAD)"
  if [ "$work" = "purlin: specs, tests and settings for greeting" ]; then
    pass "$language: the work is committed first"
  else bad "$language: the work is committed first" "$work"; fi
  if [ "$evidence" = "purlin: evidence at $(git -C "$dir" rev-parse HEAD~1 | cut -c1-7)" ]; then
    pass "$language: the evidence commit names the work"
  else bad "$language: the evidence commit names the work" "$evidence"; fi
  expect_in "$language: nothing is left at passed" \
    '^Nothing left to do\.$' "$dir/.purlin-commit.log"

  init_at "$dir" strong
  expect_in "$language: no workflow without a foreign proof" \
    '^No remote runner: ' "$dir/.purlin-init.log"
  expect_absent "$language: and no workflow file is written" \
    "$dir/.github/workflows/purlin.yml"
  expect_in "$language: strong leaves the rule to audit" \
    '^  1 rule to audit: purlin:audit$' "$dir/.purlin-init.log"

  # An audit anyone runs counts at strong. It writes into the same evidence
  # file, under `audit`, and `--commit` commits it under this person's own
  # identity.
  python3 "$RUN" --all --audit --commit --project-root "$dir" \
    > "$dir/.purlin-audit.log" 2>&1
  if grep -q '"audit"' "$dir/.purlin/evidence/local/greeting.json"; then
    pass "$language: the audit wrote into the evidence"
  else
    bad "$language: the audit wrote into the evidence" \
      "$(cat "$dir/.purlin/evidence/local/greeting.json")"
  fi
  expect_in "$language: the audit committed the evidence" \
    'Evidence committed.' "$dir/.purlin-audit.log"
  expect_in "$language: the audit ends on the summary at strong" \
    '1 rule. 1 passes its tests. 1 is strong.' "$dir/.purlin-audit.log"
  expect_in "$language: nothing is left at strong" \
    '^Nothing left to do\.$' "$dir/.purlin-audit.log"

  # Where a CI run writes. The git host variables are what the run reads, so
  # the two cases are the two sets of variables; no request is made, because
  # no token is set. What the run branch wrote is put back afterwards: a
  # runner commits it on its own branch, never on this one.
  env GITHUB_REPOSITORY=acme/demo GITHUB_REF=refs/tags/signed/0.1.0 \
      GITHUB_REF_NAME=signed/0.1.0 \
      python3 "$RUN" --all --ci --project-root "$dir" \
      > "$dir/.purlin-tagrun.log" 2>&1
  expect_in "$language: a tag run writes nothing" \
    'Tag run: nothing is written.' "$dir/.purlin-tagrun.log"
  env GITHUB_REPOSITORY=acme/demo GITHUB_REF_NAME=run/main-0000000 \
      python3 "$RUN" --all --ci --project-root "$dir" \
      > "$dir/.purlin-runbranch.log" 2>&1
  expect_not_in "$language: a run on a run branch writes its evidence" \
    'Tag run:' "$dir/.purlin-runbranch.log"
  git -C "$dir" checkout -q -- .purlin/evidence .purlin/tests.md 2>/dev/null || true
  git -C "$dir" clean -q -f -d -- .purlin/evidence 2>/dev/null || true

  init_at "$dir" signed
  expect_in "$language: signed leaves the rule to sign" \
    '^  1 rule to sign: purlin:sign$' "$dir/.purlin-init.log"
  commit_all "$dir" "raise the gate to signed"

  signing_key "$dir" jane@acme.com
  python3 "$SIGN" greeting RULE-1 --project-root "$dir" \
    > "$dir/.purlin-sign.log" 2>&1
  expect_code "$language: the rule is signed" 0 $? "$dir/.purlin-sign.log"
  expect_in "$language: the signing line names the signer and the key" \
    "^Signed 1 rule as jane@acme\.com with the key ending \.\.\.$(key_ending "$dir")\.$" \
    "$dir/.purlin-sign.log"
  if git -C "$dir" cat-file commit HEAD | grep -q '^gpgsig'; then
    pass "$language: the signing commit carries a signature"
  else
    bad "$language: the signing commit carries a signature" \
      "$(git -C "$dir" log -1 --format='%s')"
  fi

  # The tag says the version is finished: the walk writes it when nothing is
  # left. Nothing is pushed: the last line names the push.
  python3 "$SIGN" --all --project-root "$dir" < /dev/null \
    > "$dir/.purlin-walk.log" 2>&1
  if git -C "$dir" tag -l | grep -qx 'signed/0.1.0'; then
    pass "$language: the walk wrote the signed tag"
  else
    bad "$language: the walk wrote the signed tag" \
      "$(git -C "$dir" tag -l; tail -5 "$dir/.purlin-walk.log")"
  fi
  expect_in "$language: the walk names the push for a person to run" \
    '^Nothing left to do\. Push the tag to release it: git push origin signed/0\.1\.0$' \
    "$dir/.purlin-walk.log"

  # No git hook of any kind is installed, at commit time or at push time.
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
  expect_absent "python: nothing is added to the test suite" \
    "$dir/conftest.py"
  expect_absent "python: no workflow under passed" \
    "$dir/.github/workflows/purlin.yml"

  spec_file "$dir" greeting greeting.py
  mkdir -p "$dir/tests"
  cat > "$dir/tests/test_greeting.py" <<'EOF'
from greeting import greet


# purlin: greeting PROOF-1
def test_greet():
    assert greet("Ada") == "Hello, Ada!"
EOF
  printf '__pycache__/\n' >> "$dir/.gitignore"
  project_files "$dir"
  commit_all "$dir" "the first spec and its test"
  test_walk "$dir" python pytest
  wire_since_mark
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
  printf '{"name":"demo","private":true,"devDependencies":{"vitest":"^3.2.0"}}\n' \
    > "$dir/package.json"
  printf 'export function greet(name: string) {\n  return `Hello, ${name}!`;\n}\n' \
    > "$dir/greeting.ts"
  # The suite runs the project's own vitest, so the runner has to be
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
  expect_absent "typescript: nothing is added to the runner's configuration" \
    "$dir/vitest.config.ts"

  spec_file "$dir" greeting greeting.ts
  mkdir -p "$dir/tests"
  cat > "$dir/tests/greeting.test.ts" <<'EOF'
import { expect, test } from 'vitest';

import { greet } from '../greeting';

// purlin: greeting PROOF-1
test('greets by name', () => {
  expect(greet('Ada')).toBe('Hello, Ada!');
});
EOF
  printf 'node_modules/\n' >> "$dir/.gitignore"
  project_files "$dir"
  commit_all "$dir" "the first spec and its test"
  test_walk "$dir" typescript vitest
  wire_since_mark
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
  export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
  new_repo "$dir"
  mkdir -p "$dir/App" "$dir/App.Tests"
  cat > "$dir/App/Greeting.cs" <<'EOF'
namespace App {
  public static class Greeting {
    public static string Greet(string name) { return "Hello, " + name + "!"; }
  }
}
EOF
  cat > "$dir/App.Tests/App.Tests.csproj" <<'EOF'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="../App/Greeting.cs" />
  </ItemGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.11.1" />
    <PackageReference Include="xunit" Version="2.9.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2" />
  </ItemGroup>
</Project>
EOF
  printf 'bin/\nobj/\n' > "$dir/.gitignore"
  add_remote "$dir"

  init_at "$dir" passed
  mark

  # A solution at the root is what lets the suite's plain `dotnet test` reach
  # the test project.
  (cd "$dir" \
    && dotnet new sln -n App \
    && dotnet sln App.sln add App.Tests/App.Tests.csproj) \
    > "$dir/.purlin-dotnet.log" 2>&1

  spec_file "$dir" greeting App/Greeting.cs
  cat > "$dir/App.Tests/GreetingTests.cs" <<'EOF'
using Xunit;

namespace App.Tests {
  public class GreetingTests {
    // purlin: greeting PROOF-1
    [Fact]
    public void GreetsByName() {
      Assert.Equal("Hello, Ada!", App.Greeting.Greet("Ada"));
    }
  }
}
EOF
  project_files "$dir"
  commit_all "$dir" "the first spec and its test"
  test_walk "$dir" xunit dotnet
  wire_since_mark
  mark
  gate_walk "$dir" xunit
  gate_since_mark
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
  if grep -rl "$installed" "$dir" --exclude-dir=.git 2>/dev/null \
      | grep -q .; then
    bad "marketplace: no file names the install"
  else
    pass "marketplace: no file names the install"
  fi
  wire_since_mark
}

# --- run ------------------------------------------------------------------

echo "=== init end to end ==="
walk_python
walk_typescript
walk_xunit
walk_marketplace

echo ""
echo "passed $PASS, failed $FAIL, skipped $SKIP"
echo "the gates: $GATE_FAIL failed; the wiring: $WIRE_FAIL failed"
case "$PART" in
  gates)  [ "$GATE_FAIL" -eq 0 ] || exit 1 ;;
  wiring) [ "$WIRE_FAIL" -eq 0 ] || exit 1 ;;
  *)      [ "$FAIL" -eq 0 ] || exit 1 ;;
esac
echo "init e2e ok"
