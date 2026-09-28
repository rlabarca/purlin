#!/usr/bin/env bash
# purlin: scaffold PROOF-37
#
# Each language purlin:init supports is set up the same way in a real
# project, its marked test runs through the project's own command, and an
# install from the marketplace leaves no file naming the install. This file is
# one test: it passes when every set-up step of the walk in
# `dev/init_e2e_walk.sh` passed, and when init added nothing to a C# project's
# tests, checked here first.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

# Windows runs no walk: it needs a POSIX shell. The host check is written
# once, in the file this sources.
# shellcheck source=dev/windows_skip.sh
. "$HERE/windows_skip.sh"
purlin_skip_on_windows

# Init adds nothing to a C# project's tests. The project file and the marked
# test are committed before init runs, so git answers what init changed or
# added; init itself needs no `dotnet`, so this runs on every host.
CS_FAIL=0
CS_DIR="$(mktemp -d "${TMPDIR:-/tmp}/purlin-e2e-cs0.XXXXXXXX")" || exit 1
trap 'rm -rf "$CS_DIR"' EXIT
cs_bad() { CS_FAIL=1; echo "  FAIL xunit: $1"; [ -n "${2:-}" ] && echo "$2" | sed 's/^/       /'; }
(
  set -e
  cd "$CS_DIR" && mkdir -p proj && cd proj
  git init -q . && git symbolic-ref HEAD refs/heads/main
  git config user.email dev@example.com && git config user.name Dev
  git config commit.gpgsign false
  mkdir -p App App.Tests
  printf 'namespace App { public static class Greeting { public static string Greet(string n) { return "Hello, " + n + "!"; } } }\n' > App/Greeting.cs
  printf '<Project Sdk="Microsoft.NET.Sdk">\n  <PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup>\n  <ItemGroup><Compile Include="../App/Greeting.cs" /></ItemGroup>\n  <ItemGroup>\n    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.11.1" />\n    <PackageReference Include="xunit" Version="2.9.2" />\n    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2" />\n  </ItemGroup>\n</Project>\n' > App.Tests/App.Tests.csproj
  printf 'using Xunit;\nnamespace App.Tests { public class GreetingTests {\n  // purlin: greeting PROOF-1\n  [Fact] public void GreetsByName() { Assert.Equal("Hello, Ada!", App.Greeting.Greet("Ada")); }\n} }\n' > App.Tests/GreetingTests.cs
  printf 'bin/\nobj/\n' > .gitignore
  git init --bare -q -b main ../origin.git && git remote add origin ../origin.git
  git add -A && git commit -q -m "the project" && git push -q -u origin main
) > "$CS_DIR/setup.log" 2>&1 || cs_bad "the fixture could not be made" "$(cat "$CS_DIR/setup.log")"
P="$CS_DIR/proj"
if [ "$CS_FAIL" -eq 0 ]; then
  python3 "$ROOT/scripts/init/scaffold.py" --project-root "$P" --gate passed --yes \
    > "$CS_DIR/init.log" 2>&1 || cs_bad "init exited non-zero" "$(tail -5 "$CS_DIR/init.log")"
  grep -q '"name": "dotnet"' "$P/.purlin/config.json" 2>/dev/null \
    || cs_bad "the config names no dotnet suite"
  touched="$(git -C "$P" status --porcelain --untracked-files=all \
    | cut -c4- | grep -E '^(App|App\.Tests)/|\.(cs|csproj|props|targets|sln|runsettings)$')"
  [ -z "$touched" ] || cs_bad "init changed or added to the tests" "$touched"
  [ "$CS_FAIL" -eq 0 ] && echo "  ok   xunit: init adds nothing to the tests; App.Tests.csproj and GreetingTests.cs read as before"
fi

bash "$HERE/init_e2e_walk.sh" wiring
WALK=$?
[ "$CS_FAIL" -eq 0 ] || exit 1
exit "$WALK"
