#!/usr/bin/env bash
# purlin: scaffold PROOF-36
#
# A project purlin:init set up walks the three gates, on every language the
# walk sets up. This file is one test: it passes when every gate step of the
# walk in `dev/init_e2e_walk.sh` passed, and when the evidence commit and the
# two CI refs below read as the rule says.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

# Windows runs no walk: it needs a POSIX shell. The host check is written
# once, in the file this sources.
# shellcheck source=dev/windows_skip.sh
. "$HERE/windows_skip.sh"
purlin_skip_on_windows

bash "$HERE/init_e2e_walk.sh" gates || exit 1

# --- what the evidence commit holds, and where a CI run writes -------------
#
# A python project of its own, set up at `passed`: the walk's temporary
# projects are gone by the time it exits, so this one is built here.
export PURLIN_ROOT="$ROOT"
FAIL=0
ok() { echo "  ok   $1"; }
bad() { FAIL=$((FAIL + 1)); echo "  FAIL $1"; [ -n "${2:-}" ] && echo "$2" | sed 's/^/       /'; return 0; }

base="${TMPDIR:-/tmp}"
dir="$(mktemp -d "${base%/}/purlin-e2e-commit.XXXXXXXX" 2>/dev/null)" || dir=""
[ -n "$dir" ] && [ -d "$dir" ] || { echo "  FAIL no temporary directory"; exit 1; }
trap 'rm -rf "$dir"' EXIT
echo "--- the evidence commit and the CI refs ---"
git -C "$dir" init -q . && git -C "$dir" symbolic-ref HEAD refs/heads/main
git -C "$dir" config user.email dev@example.com
git -C "$dir" config user.name Dev
git -C "$dir" config commit.gpgsign false
printf '[tool.pytest.ini_options]\n' > "$dir/pyproject.toml"
printf 'def greet(name):\n    return "Hello, %%s!" %% name\n' > "$dir/greeting.py"
python3 "$ROOT/scripts/init/scaffold.py" --project-root "$dir" --gate passed --yes \
  > "$dir/.purlin-init.log" 2>&1
mkdir -p "$dir/specs/core" "$dir/tests"
printf '# Feature: greeting\n\n> Scope: greeting.py\n\n## Rules\n\n- RULE-1: `greet(name)` returns `Hello, <name>!`\n\n## Proof\n\n- PROOF-1 (RULE-1): Call `greet("Ada")` and verify it returns exactly `Hello, Ada!`\n' \
  > "$dir/specs/core/greeting.md"
printf 'from greeting import greet\n\n\n# purlin: greeting PROOF-1\ndef test_greet():\n    assert greet("Ada") == "Hello, Ada!"\n' \
  > "$dir/tests/test_greeting.py"
printf '__pycache__/\n.purlin-*.log\n' >> "$dir/.gitignore"
git -C "$dir" add -A && git -C "$dir" commit -q -m "the first spec and its test"
tested="$(git -C "$dir" rev-parse HEAD | cut -c1-7)"

if python3 "$ROOT/scripts/run/purlin_run.py" --all --test --commit --project-root "$dir" \
    > "$dir/.purlin-test.log" 2>&1; then ok "python: the test run exits 0"
else bad "python: the test run exits 0" "$(tail -5 "$dir/.purlin-test.log")"; fi
subject="$(git -C "$dir" log -1 --format=%s)"
if [ "$subject" = "purlin: evidence at $tested" ]; then ok "python: the subject names the tested commit"
else bad "python: the subject is not 'purlin: evidence at $tested'" "$subject"; fi
held="$(git -C "$dir" show --name-only --format= HEAD)"
for path in .purlin/evidence/local/greeting.json .purlin/tests.md; do
  if printf '%s\n' "$held" | grep -qx -- "$path"; then ok "python: the evidence commit holds $path"
  else bad "python: the evidence commit does not hold $path" "$held"; fi
done

# The two refs a CI run reads, with no token and no other runner variable, so
# nothing is requested of a git host. The tag run comes first: the project
# has no `ci/` evidence yet, and it must still have none after.
ci="$dir/.purlin/evidence/ci/greeting.json"
ci_run() {  # log ref-variables...
  local log="$1"; shift
  env -u GITHUB_TOKEN -u GITHUB_REF -u GITHUB_WORKSPACE -u BUILD_SOURCEBRANCH \
      -u SYSTEM_TEAMFOUNDATIONCOLLECTIONURI GITHUB_REPOSITORY=acme/demo "$@" \
    python3 "$ROOT/scripts/run/purlin_run.py" --all --ci --project-root "$dir" > "$log" 2>&1
}
ci_run "$dir/.purlin-tagrun.log" GITHUB_REF=refs/tags/signed/0.1.0 GITHUB_REF_NAME=signed/0.1.0
if grep -q 'Tag run: nothing is written.' "$dir/.purlin-tagrun.log" && [ ! -e "$ci" ]; then
  ok "python: a tag run writes no ci/ evidence"
else bad "python: a tag run wrote ci/ evidence or said nothing" "$(tail -5 "$dir/.purlin-tagrun.log")"; fi
ci_run "$dir/.purlin-runbranch.log" GITHUB_REF_NAME=run/main-0000000
if grep -qF 'Evidence written to .purlin/evidence/ci/greeting.json.' "$dir/.purlin-runbranch.log" \
    && [ -e "$ci" ] && ! grep -q 'Tag run:' "$dir/.purlin-runbranch.log"; then
  ok "python: a run on a run branch writes its ci/ evidence"
else bad "python: a run on a run branch wrote no ci/ evidence" "$(tail -5 "$dir/.purlin-runbranch.log")"; fi

[ "$FAIL" -eq 0 ] || { echo "the evidence commit and the CI refs: $FAIL failed"; exit 1; }
echo "init e2e gates ok"
