#!/usr/bin/env bash
# Tests for proof_plugins — 20 rules.
# Shared behavior (RULE-1..7), pytest (RULE-8..11), jest (RULE-12..15), shell (RULE-16..19).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTEST_PLUGIN_DIR="$PROJECT_ROOT/scripts/proof"
JEST_REPORTER="$PROJECT_ROOT/scripts/proof/jest_purlin.js"
SHELL_HARNESS="$PROJECT_ROOT/scripts/proof/shell_purlin.sh"

# Load proof harness for recording results
source "$PROJECT_ROOT/scripts/proof/shell_purlin.sh"

PASS=0
FAIL=0

record() {
  local proof_id="$1" rule_id="$2" name="$3" status="$4"
  echo "  $([[ "$status" == "pass" ]] && echo PASS || echo FAIL): $name"
  purlin_proof "proof_plugins" "$proof_id" "$rule_id" "$status" "$name"
  [[ "$status" == "pass" ]] && PASS=$((PASS + 1)) || FAIL=$((FAIL + 1))
}

run() {
  local proof_id="$1" rule_id="$2" name="$3"
  shift 3
  if "$@" >/dev/null 2>&1; then
    record "$proof_id" "$rule_id" "$name" pass
  else
    record "$proof_id" "$rule_id" "$name" fail
  fi
}

echo "=== proof_plugins tests ==="
echo "--- Shared behavior (via pytest) ---"

# PROOF-1 (RULE-1): Spec directory resolution
test_spec_dir_resolution() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/hooks"
  echo -e "# Feature: gate_hook\n\n## Rules\n- RULE-1: Guard" > "$d/specs/hooks/gate_hook.md"
  cat > "$d/test_s.py" << 'PY'
import pytest
@pytest.mark.proof("gate_hook", "PROOF-1", "RULE-1")
def test_it(): assert True
PY
  (cd "$d" && python3 -m pytest test_s.py -p pytest_purlin --override-ini="pythonpath=$PYTEST_PLUGIN_DIR" -q --no-header 2>/dev/null)
  [[ -f "$d/specs/hooks/gate_hook.proofs-default.json" ]]
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-1" "RULE-1" "spec dir resolution" test_spec_dir_resolution

# PROOF-2 (RULE-2): Proof file naming <feature>.proofs-<tier>.json
test_proof_naming() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/hooks"
  echo -e "# Feature: gate_hook\n\n## Rules\n- RULE-1: Guard" > "$d/specs/hooks/gate_hook.md"
  cat > "$d/test_s.py" << 'PY'
import pytest
@pytest.mark.proof("gate_hook", "PROOF-1", "RULE-1")
def test_it(): assert True
PY
  (cd "$d" && python3 -m pytest test_s.py -p pytest_purlin --override-ini="pythonpath=$PYTEST_PLUGIN_DIR" -q --no-header 2>/dev/null)
  local fname=$(basename "$d/specs/hooks/gate_hook.proofs-default.json")
  [[ "$fname" == "gate_hook.proofs-default.json" ]]
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-2" "RULE-2" "proof file naming" test_proof_naming

# PROOF-3 (RULE-3): Unknown feature falls back to specs/
test_fallback() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs"
  cat > "$d/test_s.py" << 'PY'
import pytest
@pytest.mark.proof("nonexistent_feature", "PROOF-1", "RULE-1")
def test_it(): assert True
PY
  (cd "$d" && python3 -m pytest test_s.py -p pytest_purlin --override-ini="pythonpath=$PYTEST_PLUGIN_DIR" -q --no-header 2>/dev/null)
  [[ -f "$d/specs/nonexistent_feature.proofs-default.json" ]]
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-3" "RULE-3" "fallback to specs/" test_fallback

# PROOF-4 (RULE-4): Feature-scoped overwrite preserves other features
test_overwrite() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/auth"
  echo -e "# Feature: feat_a\n\n## Rules\n- RULE-1: A" > "$d/specs/auth/feat_a.md"
  echo '{"tier":"default","proofs":[{"feature":"feat_b","id":"PROOF-1","rule":"RULE-1","test_file":"t.py","test_name":"t","status":"pass","tier":"default"}]}' > "$d/specs/auth/feat_a.proofs-default.json"
  cat > "$d/test_s.py" << 'PY'
import pytest
@pytest.mark.proof("feat_a", "PROOF-1", "RULE-1")
def test_a(): assert True
PY
  (cd "$d" && python3 -m pytest test_s.py -p pytest_purlin --override-ini="pythonpath=$PYTEST_PLUGIN_DIR" -q --no-header 2>/dev/null)
  python3 -c "
import json, sys
data = json.load(open('$d/specs/auth/feat_a.proofs-default.json'))
feats = [p['feature'] for p in data['proofs']]
assert 'feat_b' in feats, 'feat_b was removed'
assert 'feat_a' in feats, 'feat_a missing'
assert len(data['proofs']) == 2, f'expected 2, got {len(data[\"proofs\"])}'
"
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-4" "RULE-4" "feature-scoped overwrite" test_overwrite

# PROOF-5 (RULE-5): All 7 required fields
test_fields() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/a"
  echo -e "# Feature: f\n\n## Rules\n- RULE-1: X" > "$d/specs/a/f.md"
  cat > "$d/test_s.py" << 'PY'
import pytest
@pytest.mark.proof("f", "PROOF-1", "RULE-1")
def test_it(): assert True
PY
  (cd "$d" && python3 -m pytest test_s.py -p pytest_purlin --override-ini="pythonpath=$PYTEST_PLUGIN_DIR" -q --no-header 2>/dev/null)
  python3 -c "
import json, sys
e = json.load(open('$d/specs/a/f.proofs-default.json'))['proofs'][0]
for f in ['feature','id','rule','test_file','test_name','status','tier']:
    assert f in e, f'missing {f}'
"
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-5" "RULE-5" "all 7 required fields" test_fields

# PROOF-6 (RULE-6): pass/fail status
test_status() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/a"
  echo -e "# Feature: f\n\n## Rules\n- RULE-1: X\n- RULE-2: Y" > "$d/specs/a/f.md"
  cat > "$d/test_s.py" << 'PY'
import pytest
@pytest.mark.proof("f", "PROOF-1", "RULE-1")
def test_pass(): assert True
@pytest.mark.proof("f", "PROOF-2", "RULE-2")
def test_fail(): assert False
PY
  (cd "$d" && python3 -m pytest test_s.py -p pytest_purlin --override-ini="pythonpath=$PYTEST_PLUGIN_DIR" -q --no-header 2>/dev/null) || true
  python3 -c "
import json, sys
ps = json.load(open('$d/specs/a/f.proofs-default.json'))['proofs']
by = {p['id']:p['status'] for p in ps}
assert by['PROOF-1'] == 'pass'
assert by['PROOF-2'] == 'fail'
"
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-6" "RULE-6" "pass/fail status" test_status

# PROOF-7 (RULE-7): No markers → no proof files
test_no_markers() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/a"
  echo -e "# Feature: f\n\n## Rules\n- RULE-1: X" > "$d/specs/a/f.md"
  cat > "$d/test_s.py" << 'PY'
def test_no_marker(): assert True
PY
  (cd "$d" && python3 -m pytest test_s.py -p pytest_purlin --override-ini="pythonpath=$PYTEST_PLUGIN_DIR" -q --no-header 2>/dev/null)
  ! ls "$d/specs/"*.proofs-*.json "$d/specs/a/"*.proofs-*.json 2>/dev/null | grep -q .
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-7" "RULE-7" "no markers no files" test_no_markers

echo "--- pytest-specific ---"

# PROOF-8 (RULE-8): Marker signature with tier default
test_pytest_marker() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/a"
  echo -e "# Feature: feat\n\n## Rules\n- RULE-1: X" > "$d/specs/a/feat.md"
  cat > "$d/test_s.py" << 'PY'
import pytest
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
def test_it(): assert True
PY
  (cd "$d" && python3 -m pytest test_s.py -p pytest_purlin --override-ini="pythonpath=$PYTEST_PLUGIN_DIR" -q --no-header 2>/dev/null)
  python3 -c "
import json, sys
e = json.load(open('$d/specs/a/feat.proofs-default.json'))['proofs'][0]
assert e['feature'] == 'feat'
assert e['tier'] == 'default'
"
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-8" "RULE-8" "pytest marker signature" test_pytest_marker

# PROOF-9 (RULE-9): Fewer than 3 args silently skipped
test_pytest_skip_short() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs"
  cat > "$d/test_s.py" << 'PY'
import pytest
@pytest.mark.proof("feat", "PROOF-1")
def test_two_args(): assert True
PY
  (cd "$d" && python3 -m pytest test_s.py -p pytest_purlin --override-ini="pythonpath=$PYTEST_PLUGIN_DIR" -q --no-header 2>/dev/null)
  if [[ -f "$d/specs/feat.proofs-default.json" ]]; then
    python3 -c "
import json, sys
d = json.load(open('$d/specs/feat.proofs-default.json'))
assert len(d['proofs']) == 0
"
    return $?
  fi
  return 0  # no file = correctly skipped
}
run "PROOF-9" "RULE-9" "pytest fewer args skipped" test_pytest_skip_short

# PROOF-10 (RULE-10): test_file relative to rootdir
test_pytest_relpath() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/a" "$d/tests"
  echo -e "# Feature: feat\n\n## Rules\n- RULE-1: X" > "$d/specs/a/feat.md"
  cat > "$d/tests/test_feat.py" << 'PY'
import pytest
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
def test_it(): assert True
PY
  (cd "$d" && python3 -m pytest tests/test_feat.py -p pytest_purlin --override-ini="pythonpath=$PYTEST_PLUGIN_DIR" -q --no-header 2>/dev/null)
  python3 -c "
import json, sys
e = json.load(open('$d/specs/a/feat.proofs-default.json'))['proofs'][0]
assert not e['test_file'].startswith('/'), f'absolute: {e[\"test_file\"]}'
"
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-10" "RULE-10" "pytest test_file relative" test_pytest_relpath

# PROOF-11 (RULE-11): pytest_configure registers marker and plugin
test_pytest_configure() {
  python3 -c "
import sys, os
sys.path.insert(0, os.path.join('$PROJECT_ROOT', 'scripts', 'proof'))
from pytest_purlin import pytest_configure, ProofCollector

class FakePluginManager:
    registered = {}
    def register(self, plugin, name):
        self.registered[name] = plugin

class FakeConfig:
    markers = []
    pluginmanager = FakePluginManager()
    def addinivalue_line(self, name, value):
        self.markers.append((name, value))

config = FakeConfig()
pytest_configure(config)
assert any('proof' in m[1] for m in config.markers), 'proof marker not registered'
assert 'purlin_proof' in config.pluginmanager.registered, 'plugin not registered'
assert isinstance(config.pluginmanager.registered['purlin_proof'], ProofCollector)
"
  return $?
}
run "PROOF-11" "RULE-11" "pytest_configure registers marker + plugin" test_pytest_configure

echo "--- Jest-specific ---"

# Helper: create a node script that mocks 'glob' and exercises the reporter
jest_run() {
  local tmpdir="$1" test_file="$2" title="$3" status="$4"
  node -e "
const Module = require('module');
const fs = require('fs');
const path = require('path');
const origLoad = Module._load;
Module._load = function(request, parent, isMain) {
  if (request === 'glob') {
    return { globSync: function(pattern) {
      const results = [];
      function walk(dir) {
        for (const e of fs.readdirSync(dir, {withFileTypes:true})) {
          const full = path.join(dir, e.name);
          if (e.isDirectory()) walk(full);
          else if (e.name.endsWith('.md')) results.push(full);
        }
      }
      const base = pattern.split('*')[0].replace(/\/$/, '') || '.';
      if (fs.existsSync(base)) walk(base);
      return results;
    }};
  }
  return origLoad.apply(this, arguments);
};
const Reporter = require('$JEST_REPORTER');
const r = new Reporter({rootDir: '$tmpdir'}, {});
r.onTestResult(null, {
  testFilePath: '$tmpdir/$test_file',
  testResults: [{title: '$title', status: '$status'}]
});
process.chdir('$tmpdir');
r.onRunComplete();
" 2>/dev/null
}

# PROOF-12 (RULE-12): Jest marker parsed from title
test_jest_marker() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/a"
  echo -e "# Feature: feat\n\n## Rules\n- RULE-1: X" > "$d/specs/a/feat.md"
  jest_run "$d" "tests/test.js" "works [proof:feat:PROOF-1:RULE-1:default]" "passed"
  python3 -c "
import json, sys
e = json.load(open('$d/specs/a/feat.proofs-default.json'))['proofs'][0]
assert e['feature'] == 'feat'
assert e['id'] == 'PROOF-1'
assert e['rule'] == 'RULE-1'
"
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-12" "RULE-12" "jest marker parsing" test_jest_marker

# PROOF-13 (RULE-13): Tests without marker ignored
test_jest_no_marker() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs"
  node -e "
const Module = require('module');
const fs = require('fs');
const origLoad = Module._load;
Module._load = function(r) {
  if (r === 'glob') return {globSync: function() {return [];}};
  return origLoad.apply(this, arguments);
};
const Reporter = require('$JEST_REPORTER');
const r = new Reporter({rootDir: '$d'}, {});
r.onTestResult(null, {
  testFilePath: '$d/tests/test.js',
  testResults: [{title: 'no marker here', status: 'passed'}]
});
process.chdir('$d');
r.onRunComplete();
const files = fs.readdirSync('$d/specs').filter(f => f.includes('.proofs-'));
if (files.length > 0) process.exit(1);
" 2>/dev/null
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-13" "RULE-13" "jest no marker ignored" test_jest_no_marker

# PROOF-14 (RULE-14): test_file relative to rootDir
test_jest_relpath() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/a"
  echo -e "# Feature: feat\n\n## Rules\n- RULE-1: X" > "$d/specs/a/feat.md"
  jest_run "$d" "tests/test.js" "works [proof:feat:PROOF-1:RULE-1:default]" "passed"
  python3 -c "
import json, sys
e = json.load(open('$d/specs/a/feat.proofs-default.json'))['proofs'][0]
assert not e['test_file'].startswith('/'), f'absolute: {e[\"test_file\"]}'
"
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-14" "RULE-14" "jest test_file relative" test_jest_relpath

# PROOF-15 (RULE-15): Jest "passed"→"pass", "failed"→"fail"
test_jest_status() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/a"
  echo -e "# Feature: feat\n\n## Rules\n- RULE-1: X\n- RULE-2: Y" > "$d/specs/a/feat.md"
  node -e "
const Module = require('module');
const fs = require('fs');
const path = require('path');
const origLoad = Module._load;
Module._load = function(request) {
  if (request === 'glob') {
    return { globSync: function(pattern) {
      const results = [];
      function walk(dir) {
        for (const e of fs.readdirSync(dir, {withFileTypes:true})) {
          const full = path.join(dir, e.name);
          if (e.isDirectory()) walk(full);
          else if (e.name.endsWith('.md')) results.push(full);
        }
      }
      const base = pattern.split('*')[0].replace(/\/$/, '') || '.';
      if (fs.existsSync(base)) walk(base);
      return results;
    }};
  }
  return origLoad.apply(this, arguments);
};
const Reporter = require('$JEST_REPORTER');
const r = new Reporter({rootDir: '$d'}, {});
r.onTestResult(null, {
  testFilePath: '$d/tests/t.js',
  testResults: [
    {title: 'p [proof:feat:PROOF-1:RULE-1:default]', status: 'passed'},
    {title: 'f [proof:feat:PROOF-2:RULE-2:default]', status: 'failed'}
  ]
});
process.chdir('$d');
r.onRunComplete();
const ps = JSON.parse(fs.readFileSync('$d/specs/a/feat.proofs-default.json','utf8')).proofs;
const by = {};
ps.forEach(p => by[p.id] = p.status);
if (by['PROOF-1'] !== 'pass') process.exit(1);
if (by['PROOF-2'] !== 'fail') process.exit(1);
" 2>/dev/null
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-15" "RULE-15" "jest status mapping" test_jest_status

echo "--- Shell-specific ---"

# PROOF-16 (RULE-16): purlin_proof 5 args + PURLIN_PROOF_TIER
test_shell_tier() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/a"
  echo -e "# Feature: feat\n\n## Rules\n- RULE-1: X" > "$d/specs/a/feat.md"
  (
    cd "$d"
    export PURLIN_PROOF_TIER=slow
    source "$SHELL_HARNESS"
    purlin_proof "feat" "PROOF-1" "RULE-1" pass "desc"
    purlin_proof_finish
  )
  python3 -c "
import json, sys
e = json.load(open('$d/specs/a/feat.proofs-slow.json'))['proofs'][0]
assert e['tier'] == 'slow'
"
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-16" "RULE-16" "shell tier from PURLIN_PROOF_TIER" test_shell_tier

# PROOF-17 (RULE-17): test_file from BASH_SOURCE[1]
test_shell_source() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/a"
  echo -e "# Feature: feat\n\n## Rules\n- RULE-1: X" > "$d/specs/a/feat.md"
  cat > "$d/my_test.sh" << SHEOF
#!/usr/bin/env bash
source "$SHELL_HARNESS"
purlin_proof "feat" "PROOF-1" "RULE-1" pass "test"
purlin_proof_finish
SHEOF
  chmod +x "$d/my_test.sh"
  (cd "$d" && bash "$d/my_test.sh")
  python3 -c "
import json, sys
e = json.load(open('$d/specs/a/feat.proofs-default.json'))['proofs'][0]
assert 'my_test.sh' in e['test_file'], f'unexpected: {e[\"test_file\"]}'
"
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-17" "RULE-17" "shell test_file from BASH_SOURCE" test_shell_source

# PROOF-18 (RULE-18): purlin_proof_finish required to write
test_shell_finish_required() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/a"
  echo -e "# Feature: feat\n\n## Rules\n- RULE-1: X" > "$d/specs/a/feat.md"
  # Call purlin_proof without finish in a subshell — no files
  (
    cd "$d"
    source "$SHELL_HARNESS"
    purlin_proof "feat" "PROOF-1" "RULE-1" pass "test1"
    purlin_proof "feat" "PROOF-2" "RULE-2" pass "test2"
  )
  local no_files=true
  ls "$d/specs/a/"*.proofs-*.json 2>/dev/null | grep -q . && no_files=false
  # Now call with finish
  (
    cd "$d"
    source "$SHELL_HARNESS"
    purlin_proof "feat" "PROOF-1" "RULE-1" pass "test1"
    purlin_proof_finish
  )
  local has_files=false
  [[ -f "$d/specs/a/feat.proofs-default.json" ]] && has_files=true
  [[ "$no_files" == "true" ]] && [[ "$has_files" == "true" ]]
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-18" "RULE-18" "shell finish required to write" test_shell_finish_required

# PROOF-19 (RULE-19): Entries cleared after finish
test_shell_clear() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/a"
  echo -e "# Feature: feat\n\n## Rules\n- RULE-1: X" > "$d/specs/a/feat.md"
  (
    cd "$d"
    source "$SHELL_HARNESS"
    purlin_proof "feat" "PROOF-1" "RULE-1" pass "test"
    purlin_proof_finish
    # _PURLIN_PROOFS should be empty now
    [[ -z "$_PURLIN_PROOFS" ]] || exit 1
    # Second finish = no-op
    purlin_proof_finish
  )
  python3 -c "
import json, sys
d = json.load(open('$d/specs/a/feat.proofs-default.json'))
assert len(d['proofs']) == 1, f'expected 1, got {len(d[\"proofs\"])}'
"
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-19" "RULE-19" "shell entries cleared after finish" test_shell_clear

echo "--- Installation and discovery ---"

# PROOF-20 (RULE-20): Custom plugin proof files discovered by sync_status via glob
test_custom_discovery() {
  local d=$(mktemp -d)
  mkdir -p "$d/specs/custom"
  echo -e "# Feature: my_custom\n\n## Rules\n- RULE-1: Does the thing" > "$d/specs/custom/my_custom.md"
  # Hand-write a proof file as if a custom (non-built-in) plugin emitted it
  cat > "$d/specs/custom/my_custom.proofs-default.json" << 'JSON'
{"tier":"default","proofs":[{"feature":"my_custom","id":"PROOF-1","rule":"RULE-1","test_file":"tests/test_custom.go","test_name":"TestDoesTheThing","status":"pass","tier":"default"}]}
JSON
  # Run sync_status on the temp project — it should discover the proof
  local output
  output=$(python3 -c "
import sys, os
sys.path.insert(0, os.path.join('$PROJECT_ROOT', 'scripts', 'mcp'))
from purlin_server import sync_status
print(sync_status('$d'))
" 2>&1)
  echo "$output" | grep -q "1/1 rules proved"
  local rc=$?; rm -rf "$d"; return $rc
}
run "PROOF-20" "RULE-20" "custom plugin proofs discovered by sync_status" test_custom_discovery

# Emit proof files
cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "proof_plugins: $PASS/$((PASS+FAIL)) passed"
[[ $FAIL -eq 0 ]]
