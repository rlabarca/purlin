#!/usr/bin/env bash
# tests/purlin_update/test_upgrade_chain.sh
#
# End-to-end upgrade regression test: copies a real consumer project checkpoint
# to a temp directory, runs the full migration pipeline, and validates both
# the starting and ending states against the expectations registry.
#
# Expectations source: scripts/migration/upgrade_expectations.json
# Checkpoint source:   tests/test_projects/my-app-v0.8.5/
#
# Usage:
#   bash tests/purlin_update/test_upgrade_chain.sh [--from 0.8.5] [--to 0.8.6]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EXPECTATIONS="$PROJECT_ROOT/scripts/migration/upgrade_expectations.json"
DETECTOR="$PROJECT_ROOT/scripts/migration/version_detector.py"
TMP_DIR=""

# Defaults (can override with --from / --to)
FROM_VERSION="0.8.5"
TO_VERSION="0.8.6"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --from) FROM_VERSION="$2"; shift 2 ;;
        --to)   TO_VERSION="$2"; shift 2 ;;
        *)      echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

CHECKPOINT_DIR="$SCRIPT_DIR/../test_projects/my-app-v${FROM_VERSION}"

cleanup() {
    [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]] && rm -rf "$TMP_DIR"
}
trap cleanup EXIT

# ==================================================================
# Prerequisites
# ==================================================================
if [[ ! -d "$CHECKPOINT_DIR" ]]; then
    echo "FAIL: Checkpoint not found at $CHECKPOINT_DIR"
    exit 1
fi

if [[ ! -f "$EXPECTATIONS" ]]; then
    echo "FAIL: Expectations registry not found at $EXPECTATIONS"
    exit 1
fi

TMP_DIR="$(mktemp -d -t purlin-upgrade-chain-XXXXXX)"

echo "━━━ Upgrade Test: ${FROM_VERSION} → ${TO_VERSION} ━━━"
echo "Checkpoint:    $CHECKPOINT_DIR"
echo "Expectations:  $EXPECTATIONS"
echo "Temp dir:      $TMP_DIR"
echo ""

# ==================================================================
# Copy checkpoint and git init
# ==================================================================
cp -R "$CHECKPOINT_DIR/"* "$CHECKPOINT_DIR/".* "$TMP_DIR/" 2>/dev/null || true
git -C "$TMP_DIR" init -q
git -C "$TMP_DIR" add -A
git -C "$TMP_DIR" commit -q -m "initial checkpoint" --allow-empty

# ==================================================================
# All validation driven by Python reading the expectations registry
# ==================================================================
python3 -c "
import json, os, sys, glob as glob_mod, subprocess

sys.path.insert(0, '$PROJECT_ROOT/scripts/migration')
from version_detector import detect_version
from migration_registry import STEPS

expectations_path = '$EXPECTATIONS'
tmp_dir = '$TMP_DIR'
from_version = '$FROM_VERSION'
to_version = '$TO_VERSION'
project_root = '$PROJECT_ROOT'

with open(expectations_path) as f:
    registry = json.load(f)

versions = registry['versions']
if from_version not in versions:
    print(f'FAIL: version {from_version} not in expectations registry')
    sys.exit(1)
if to_version not in versions:
    print(f'FAIL: version {to_version} not in expectations registry')
    sys.exit(1)

passed = 0
failed = 0
total = 0

def check(label, ok, detail=''):
    global passed, failed, total
    total += 1
    if ok:
        passed += 1
        print(f'  ✓ {label}')
    else:
        failed += 1
        msg = f'  ✗ {label}'
        if detail:
            msg += f' ({detail})'
        print(msg)

def resolve_key(data, dotted_key):
    keys = dotted_key.split('.')
    v = data
    for k in keys:
        if isinstance(v, dict):
            if k not in v:
                return '__ABSENT__'
            v = v[k]
        else:
            return '__ABSENT__'
    return v

def validate_version(label, version_key):
    \"\"\"Validate the project state against a version's expectations.\"\"\"
    exp = versions[version_key]

    # --- Detection ---
    print(f'  Detection:')
    fp = detect_version(tmp_dir)
    det = exp['detection']
    for key, expected in det.items():
        actual = fp.get(key)
        if expected is None:
            check(f'    {key}=null', actual is None, f'got {actual}')
        else:
            check(f'    {key}={expected}', str(actual) == str(expected), f'got {actual}')

    # --- Config keys ---
    config_path = os.path.join(tmp_dir, '.purlin', 'config.json')
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = json.load(f)

        if exp.get('config', {}).get('required_keys'):
            print(f'  Required config keys:')
            for key, expected in exp['config']['required_keys'].items():
                actual = resolve_key(config, key)
                if expected == 'non-null':
                    check(f'    config.{key} is set', actual != '__ABSENT__' and actual is not None, f'got {actual}')
                else:
                    check(f'    config.{key}={expected}', str(actual) == str(expected), f'got {actual}')

        if exp.get('config', {}).get('absent_keys'):
            print(f'  Absent config keys:')
            for key in exp['config']['absent_keys']:
                actual = resolve_key(config, key)
                check(f'    no config.{key}', actual == '__ABSENT__', 'still present')

    # --- Settings keys ---
    settings_path = os.path.join(tmp_dir, '.claude', 'settings.json')
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            settings = json.load(f)

        if exp.get('settings', {}).get('required_keys'):
            print(f'  Required settings keys:')
            for key, expected in exp['settings']['required_keys'].items():
                actual = resolve_key(settings, key)
                if expected == 'non-null':
                    check(f'    settings.{key} is set', actual != '__ABSENT__' and actual is not None, f'got {actual}')
                else:
                    check(f'    settings.{key}={expected}', str(actual) == str(expected), f'got {actual}')

        if exp.get('settings', {}).get('absent_keys'):
            print(f'  Absent settings keys:')
            for key in exp['settings']['absent_keys']:
                actual = resolve_key(settings, key)
                check(f'    no settings.{key}', actual == '__ABSENT__', 'still present')

    # --- Files ---
    files = exp.get('files', {})

    if files.get('present'):
        print(f'  Present files:')
        for relpath in files['present']:
            full = os.path.join(tmp_dir, relpath)
            exists = os.path.exists(full) or os.path.islink(full)
            check(f'    {relpath}', exists, 'missing')

    if files.get('present_globs'):
        print(f'  Present globs:')
        for pattern in files['present_globs']:
            full_pattern = os.path.join(tmp_dir, pattern)
            matches = glob_mod.glob(full_pattern)
            check(f'    {pattern}', len(matches) > 0, 'no matches')

    if files.get('absent'):
        print(f'  Absent files:')
        for relpath in files['absent']:
            full = os.path.join(tmp_dir, relpath)
            exists = os.path.exists(full) or os.path.islink(full)
            check(f'    no {relpath}', not exists, 'still exists')

    if files.get('absent_globs'):
        print(f'  Absent globs:')
        for pattern in files['absent_globs']:
            full_pattern = os.path.join(tmp_dir, pattern)
            matches = glob_mod.glob(full_pattern)
            check(f'    no {pattern}', len(matches) == 0, f'found {len(matches)}')

    # --- Directories ---
    dirs = exp.get('directories', {})

    if dirs.get('present'):
        print(f'  Present directories:')
        for relpath in dirs['present']:
            full = os.path.join(tmp_dir, relpath)
            check(f'    {relpath}/', os.path.isdir(full), 'missing')

    if dirs.get('absent'):
        print(f'  Absent directories:')
        for relpath in dirs['absent']:
            full = os.path.join(tmp_dir, relpath)
            check(f'    no {relpath}/', not os.path.exists(full), 'still exists')

    # --- File contents ---
    contents = exp.get('file_contents', {})
    if contents:
        print(f'  File contents:')
        for relpath, checks in contents.items():
            full = os.path.join(tmp_dir, relpath)
            if not os.path.exists(full):
                check(f'    {relpath} readable', False, 'file missing')
                continue
            with open(full, encoding='utf-8') as f:
                text = f.read()
            for needle in checks.get('contains', []):
                check(f'    {relpath} contains \"{needle}\"', needle in text, 'not found')
            for needle in checks.get('not_contains', []):
                check(f'    {relpath} lacks \"{needle}\"', needle not in text, 'still present')

    # --- Feature structure ---
    fstruct = exp.get('feature_structure', {})

    if fstruct.get('expected_files'):
        print(f'  Feature structure:')
        for relpath in fstruct['expected_files']:
            full = os.path.join(tmp_dir, relpath)
            check(f'    {relpath}', os.path.exists(full), 'missing')

    if fstruct.get('absent_files'):
        for relpath in fstruct['absent_files']:
            full = os.path.join(tmp_dir, relpath)
            check(f'    no {relpath}', not os.path.exists(full), 'still exists')


# ==================================================================
# Phase 1: Validate pre-upgrade state
# ==================================================================
print(f'━━━ Pre-Upgrade: v{from_version} expectations ━━━')
validate_version(f'v{from_version}', from_version)

# ==================================================================
# Phase 2: Run full upgrade
# ==================================================================
print()
print('━━━ Running Full Upgrade ━━━━━━━━━━━━━')

fp = detect_version(tmp_dir)
print(f'  Start: model={fp[\"model\"]}, era={fp[\"era\"]}, mv={fp.get(\"migration_version\")}')

migration_ok = True
for step in STEPS:
    fp = detect_version(tmp_dir)
    ok, reason = step.preconditions(fp, tmp_dir)
    if not ok:
        print(f'  Step {step.step_id} ({step.name}) skipped: {reason}')
        continue
    print(f'  Executing step {step.step_id}: {step.name}...')
    success = step.execute(fp, tmp_dir)
    if not success:
        print(f'  FAIL: Step {step.step_id} failed')
        migration_ok = False
        break
    subprocess.run(['git', 'add', '-A'], cwd=tmp_dir, capture_output=True, timeout=10)
    subprocess.run(['git', 'commit', '-m', f'post-step-{step.step_id}', '--allow-empty'],
                   cwd=tmp_dir, capture_output=True, timeout=10)
    print(f'  Step {step.step_id} complete.')

check('migration pipeline completed', migration_ok)
print()

# ==================================================================
# Phase 3: Validate post-upgrade state
# ==================================================================
print(f'━━━ Post-Upgrade: v{to_version} expectations ━━━')
validate_version(f'v{to_version}', to_version)

# ==================================================================
# Summary
# ==================================================================
print()
print(f'━━━ {passed} passed \u00b7 {failed} failed \u00b7 {total} total')

sys.exit(1 if failed > 0 else 0)
" 2>&1

exit $?
