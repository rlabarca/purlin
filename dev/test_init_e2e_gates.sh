#!/usr/bin/env bash
# purlin: scaffold PROOF-36
#
# A project purlin:init set up walks the three gates, on every language the
# walk sets up. This file is one test: it passes when every gate step of the
# walk in `dev/init_e2e_walk.sh` passed.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Windows runs no walk: it needs a POSIX shell. The host check is written
# once, in the file this sources.
# shellcheck source=dev/windows_skip.sh
. "$HERE/windows_skip.sh"
purlin_skip_on_windows

exec bash "$HERE/init_e2e_walk.sh" gates
