#!/usr/bin/env bash
# Tests for scripts/proof/jest_purlin.js — Jest proof reporter.
#
# Uses Node.js to exercise the reporter class directly (no Jest dependency).
#
# Tests:
#   PROOF-1 (RULE-1): Test title with proof marker produces proof entry
#   PROOF-2 (RULE-2): Proof entry contains all required fields
#   PROOF-3 (RULE-3): Proof file is written next to matching spec file
#   PROOF-4 (RULE-4): Unknown feature falls back to specs/ directory
#   PROOF-5 (RULE-5): Running twice replaces old entries
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORTER="$PROJECT_ROOT/scripts/proof/jest_purlin.js"
PASS=0
FAIL=0

# Load proof harness
source "$PROJECT_ROOT/scripts/proof/shell_purlin.sh"

run_test() {
  local name="$1"
  shift
  if "$@"; then
    echo "  PASS: $name"
    PASS=$((PASS + 1))
    return 0
  else
    echo "  FAIL: $name"
    FAIL=$((FAIL + 1))
    return 1
  fi
}

echo "=== proof-jest tests ==="

# --- PROOF-1: Proof marker in title produces proof entry ---
test_proof_marker_parsing() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/specs/auth"
  echo -e "# Feature: my_feat\n\n## Rules\n- RULE-1: Must work" > "$tmpdir/specs/auth/my_feat.md"

  node -e "
const Module = require('module');
const fs = require('fs');
const origLoad = Module._load;
Module._load = function(request, parent, isMain) {
  if (request === 'glob') {
    return {
      globSync: function(pattern) {
        const results = [];
        function walk(dir) {
          for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
            const full = require('path').join(dir, entry.name);
            if (entry.isDirectory()) walk(full);
            else if (entry.name.endsWith('.md')) results.push(full);
          }
        }
        const base = pattern.split('*')[0].replace(/\/$/, '') || '.';
        if (fs.existsSync(base)) walk(base);
        return results;
      }
    };
  }
  return origLoad.apply(this, arguments);
};

const Reporter = require('$REPORTER');
const r = new Reporter({ rootDir: '$tmpdir' }, {});

r.onTestResult(null, {
  testFilePath: '$tmpdir/tests/test_auth.js',
  testResults: [{
    title: 'does auth [proof:my_feat:PROOF-1:RULE-1]',
    status: 'passed'
  }]
});

process.chdir('$tmpdir');
r.onRunComplete();

const proof = JSON.parse(fs.readFileSync('$tmpdir/specs/auth/my_feat.proofs-unit.json', 'utf8'));
if (proof.proofs[0].feature !== 'my_feat') process.exit(1);
" 2>/dev/null

  local rc=$?
  rm -rf "$tmpdir"
  return $rc
}
run_test "proof marker parsing" test_proof_marker_parsing
purlin_proof "proof-jest" "PROOF-1" "RULE-1" "$([ $? -eq 0 ] && echo pass || echo fail)" "proof marker parsing"

# --- PROOF-2: All required fields present ---
test_all_fields_present() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/specs/auth"
  echo -e "# Feature: my_feat\n\n## Rules\n- RULE-1: Must work" > "$tmpdir/specs/auth/my_feat.md"

  node -e "
const Module = require('module');
const fs = require('fs');
const origLoad = Module._load;
Module._load = function(request, parent, isMain) {
  if (request === 'glob') {
    return {
      globSync: function(pattern) {
        const results = [];
        function walk(dir) {
          for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
            const full = require('path').join(dir, entry.name);
            if (entry.isDirectory()) walk(full);
            else if (entry.name.endsWith('.md')) results.push(full);
          }
        }
        const base = pattern.split('*')[0].replace(/\/$/, '') || '.';
        if (fs.existsSync(base)) walk(base);
        return results;
      }
    };
  }
  return origLoad.apply(this, arguments);
};

const Reporter = require('$REPORTER');
const r = new Reporter({ rootDir: '$tmpdir' }, {});

r.onTestResult(null, {
  testFilePath: '$tmpdir/tests/test_auth.js',
  testResults: [{
    title: 'does auth [proof:my_feat:PROOF-1:RULE-1]',
    status: 'passed'
  }]
});

process.chdir('$tmpdir');
r.onRunComplete();

const entry = JSON.parse(fs.readFileSync('$tmpdir/specs/auth/my_feat.proofs-unit.json', 'utf8')).proofs[0];
const required = ['feature', 'id', 'rule', 'test_file', 'test_name', 'status', 'tier'];
for (const f of required) {
  if (!(f in entry)) { console.error('missing field:', f); process.exit(1); }
}
if (entry.status !== 'pass') { console.error('expected pass, got:', entry.status); process.exit(1); }
" 2>/dev/null

  local rc=$?
  rm -rf "$tmpdir"
  return $rc
}
run_test "all required fields present" test_all_fields_present
purlin_proof "proof-jest" "PROOF-2" "RULE-2" "$([ $? -eq 0 ] && echo pass || echo fail)" "all required fields present"

# --- PROOF-3: Proof file written next to matching spec ---
test_proof_next_to_spec() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/specs/billing"
  echo -e "# Feature: invoice\n\n## Rules\n- RULE-1: Must total" > "$tmpdir/specs/billing/invoice.md"

  node -e "
const Module = require('module');
const fs = require('fs');
const origLoad = Module._load;
Module._load = function(request, parent, isMain) {
  if (request === 'glob') {
    return {
      globSync: function(pattern) {
        const results = [];
        function walk(dir) {
          for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
            const full = require('path').join(dir, entry.name);
            if (entry.isDirectory()) walk(full);
            else if (entry.name.endsWith('.md')) results.push(full);
          }
        }
        const base = pattern.split('*')[0].replace(/\/$/, '') || '.';
        if (fs.existsSync(base)) walk(base);
        return results;
      }
    };
  }
  return origLoad.apply(this, arguments);
};

const Reporter = require('$REPORTER');
const r = new Reporter({ rootDir: '$tmpdir' }, {});

r.onTestResult(null, {
  testFilePath: '$tmpdir/tests/test_billing.js',
  testResults: [{
    title: 'totals [proof:invoice:PROOF-1:RULE-1]',
    status: 'passed'
  }]
});

process.chdir('$tmpdir');
r.onRunComplete();

if (!fs.existsSync('$tmpdir/specs/billing/invoice.proofs-unit.json')) process.exit(1);
" 2>/dev/null

  local rc=$?
  rm -rf "$tmpdir"
  return $rc
}
run_test "proof file next to spec" test_proof_next_to_spec
purlin_proof "proof-jest" "PROOF-3" "RULE-3" "$([ $? -eq 0 ] && echo pass || echo fail)" "proof file next to spec"

# --- PROOF-4: Unknown feature falls back to specs/ ---
test_unknown_feature_fallback() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/specs"

  node -e "
const Module = require('module');
const fs = require('fs');
const origLoad = Module._load;
Module._load = function(request, parent, isMain) {
  if (request === 'glob') {
    return { globSync: function() { return []; } };
  }
  return origLoad.apply(this, arguments);
};

const Reporter = require('$REPORTER');
const r = new Reporter({ rootDir: '$tmpdir' }, {});

r.onTestResult(null, {
  testFilePath: '$tmpdir/tests/test.js',
  testResults: [{
    title: 'test [proof:unknown_feat:PROOF-1:RULE-1]',
    status: 'passed'
  }]
});

process.chdir('$tmpdir');
r.onRunComplete();

if (!fs.existsSync('$tmpdir/specs/unknown_feat.proofs-unit.json')) process.exit(1);
" 2>/dev/null

  local rc=$?
  rm -rf "$tmpdir"
  return $rc
}
run_test "unknown feature falls back to specs/" test_unknown_feature_fallback
purlin_proof "proof-jest" "PROOF-4" "RULE-4" "$([ $? -eq 0 ] && echo pass || echo fail)" "unknown feature falls back to specs/"

# --- PROOF-5: Running twice replaces old entries ---
test_replace_on_rerun() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/specs/auth"
  echo -e "# Feature: my_feat\n\n## Rules\n- RULE-1: Must work" > "$tmpdir/specs/auth/my_feat.md"

  node -e "
const Module = require('module');
const fs = require('fs');
const origLoad = Module._load;
Module._load = function(request, parent, isMain) {
  if (request === 'glob') {
    return {
      globSync: function(pattern) {
        const results = [];
        function walk(dir) {
          for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
            const full = require('path').join(dir, entry.name);
            if (entry.isDirectory()) walk(full);
            else if (entry.name.endsWith('.md')) results.push(full);
          }
        }
        const base = pattern.split('*')[0].replace(/\/$/, '') || '.';
        if (fs.existsSync(base)) walk(base);
        return results;
      }
    };
  }
  return origLoad.apply(this, arguments);
};

const Reporter = require('$REPORTER');

// First run: fail
const r1 = new Reporter({ rootDir: '$tmpdir' }, {});
r1.onTestResult(null, {
  testFilePath: '$tmpdir/tests/test.js',
  testResults: [{
    title: 'test [proof:my_feat:PROOF-1:RULE-1]',
    status: 'failed'
  }]
});
process.chdir('$tmpdir');
r1.onRunComplete();

// Second run: pass
const r2 = new Reporter({ rootDir: '$tmpdir' }, {});
r2.onTestResult(null, {
  testFilePath: '$tmpdir/tests/test.js',
  testResults: [{
    title: 'test [proof:my_feat:PROOF-1:RULE-1]',
    status: 'passed'
  }]
});
r2.onRunComplete();

const data = JSON.parse(fs.readFileSync('$tmpdir/specs/auth/my_feat.proofs-unit.json', 'utf8'));
if (data.proofs.length !== 1) { console.error('expected 1, got:', data.proofs.length); process.exit(1); }
if (data.proofs[0].status !== 'pass') { console.error('expected pass, got:', data.proofs[0].status); process.exit(1); }
" 2>/dev/null

  local rc=$?
  rm -rf "$tmpdir"
  return $rc
}
run_test "replace on rerun" test_replace_on_rerun
purlin_proof "proof-jest" "PROOF-5" "RULE-5" "$([ $? -eq 0 ] && echo pass || echo fail)" "replace on rerun"

# --- Emit proofs ---
cd "$PROJECT_ROOT"
purlin_proof_finish

# --- Summary ---
echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
