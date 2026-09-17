#!/usr/bin/env bash
# The shell arm of a Purlin run executes every `*.test.sh` at the project
# root. This repository keeps its suites under `dev/`, so this file is how the
# end-to-end walk of `purlin:init` is reached from a run, and how the two
# `@e2e` proofs of the `scaffold` spec get written.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE" || exit 1

# Windows runs neither suite: the walk below needs a POSIX shell. The host
# check is written once, in the file this sources.
# shellcheck source=dev/windows_skip.sh
. "$HERE/dev/windows_skip.sh"
purlin_skip_on_windows

exec bash dev/test_init_e2e.sh "$@"
