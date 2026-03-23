#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$(git rev-parse --show-toplevel)/tools/test_support/run_regression.sh" --scenarios-dir "$SCRIPT_DIR/scenarios"
