#!/usr/bin/env bash
# The end-to-end suites that prove the proof plugins, gathered where the run
# script's shell arm looks for them.
#
# `run_framework` runs each `*.test.sh` at the project root, so a suite that
# lives anywhere else is never executed by `purlin:test` and the proofs it
# would have written stay missing. Each suite below sources the shell harness,
# records its own cases at the `e2e` tier and calls `purlin_proof_finish`
# itself, so this file starts them and reports what they returned and nothing
# else.
#
# Every suite runs even when an earlier one failed: each writes its own
# evidence, and stopping at the first failure would leave the rest of the
# state table reading as if those proofs had never been run.
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

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

SUITES=(
  dev/test_proof_plugins.sh
  dev/test_proof_pytest.sh
  dev/test_proof_jest.sh
  dev/test_proof_shell.sh
  dev/test_e2e_feature_scoped_overwrite.sh
)

status=0
for suite in "${SUITES[@]}"; do
  echo "=== $suite"
  bash "$suite" || status=1
done

exit "$status"
