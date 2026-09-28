#!/usr/bin/env bash
# purlin: scaffold PROOF-37
#
# Each language purlin:init supports is set up the same way in a real
# project, its marked test runs through the project's own command, and an
# install from the marketplace leaves no file naming the install. This file is
# one test: it passes when every set-up step of the walk in
# `dev/init_e2e_walk.sh` passed.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Windows runs no walk: it needs a POSIX shell. The host check is written
# once, in the file this sources.
# shellcheck source=dev/windows_skip.sh
. "$HERE/windows_skip.sh"
purlin_skip_on_windows

exec bash "$HERE/init_e2e_walk.sh" wiring
