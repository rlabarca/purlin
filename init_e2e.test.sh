#!/usr/bin/env bash
# The shell arm of a Purlin run executes every `*.test.sh` at the project
# root. This repository keeps its suites under `dev/`, so this file is how the
# end-to-end walk of `purlin:init` is reached from a run, and how the two
# `@e2e` proofs of the `scaffold` spec get written.
set -uo pipefail

cd "$(dirname "$0")" || exit 1
exec bash dev/test_init_e2e.sh "$@"
