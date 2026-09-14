#!/usr/bin/env bash
# The shell arm of a Purlin run executes every `*.test.sh` at the project
# root. This repository keeps its suites under `dev/`, so this file is how the
# end-to-end walk of `purlin:init` is reached from a run, and how the two
# `@e2e` proofs of the `scaffold` spec get written.
set -uo pipefail

# The end-to-end walk below needs a POSIX shell. Git Bash on Windows is not
# one for these suites, so the job says so and exits 0 rather than reporting a
# failure that is about the host. The proofs these suites serve carry
# `@env(linux)`, so the Linux job proves them and a Windows run lists them as
# needing linux.
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    echo "This suite does not run under Git Bash on Windows. Its proofs carry"
    echo "@env(linux), so the Linux job proves them."
    exit 0
    ;;
esac

cd "$(dirname "$0")" || exit 1
exec bash dev/test_init_e2e.sh "$@"
