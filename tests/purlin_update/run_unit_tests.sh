#!/usr/bin/env bash
# tests/purlin_update/run_unit_tests.sh
#
# Runs the version detector and migration registry unit tests.
set -euo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$PROJECT_ROOT/scripts/migration"
python3 -m pytest test_version_detector.py test_migration_registry.py -q --tb=short 2>&1
