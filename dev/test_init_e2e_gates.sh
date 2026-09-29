#!/usr/bin/env bash
#
# The whole walk in `dev/init_e2e_walk.sh`, on every language it sets up:
# python always, typescript where npm can install Vitest, and C# where
# `dotnet` is installed. A project init set up is walked from its first test
# run to the signed tag, and the file passes when every step of the walk
# passed.
#
# It carries no marker. Each case of the rules it touches is a proof of its
# own, carried by its own test in `dev/test_init_scaffold.py` on a python,
# typescript and C# project; this file keeps the typescript and C# projects
# walked through all three gates as well.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Windows runs no walk: it needs a POSIX shell. The host check is written
# once, in the file this sources.
# shellcheck source=dev/windows_skip.sh
. "$HERE/windows_skip.sh"
purlin_skip_on_windows

bash "$HERE/init_e2e_walk.sh" all
