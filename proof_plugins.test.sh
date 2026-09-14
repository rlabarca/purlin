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

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE" || exit 1

# Windows runs neither suite: the walks below need a POSIX shell. The host
# check is written once, in the file this sources.
# shellcheck source=dev/windows_skip.sh
. "$HERE/dev/windows_skip.sh"
purlin_skip_on_windows

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
