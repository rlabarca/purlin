"""Stress tests for proof merge logic and cheating detection.

Two areas examined:
1. Multi-feature, multi-tier, multi-language proof file merges — exercising
   feature-scoped overwrite, conflict resolution, and cross-tier aggregation.
2. Deliberately crafted "cheating" test patterns that LOOK correct but are
   misleading — validating that static_checks and the audit criteria catch them.

Every test compiles/runs real code. No fake JSON. The proof files are emitted
by actual language toolchains (gcc, php, sqlite3, tsc, pytest).

Run with: python3 -m pytest dev/test_proof_stress.py -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

PROOF_SCRIPTS = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'proof')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'audit'))

from purlin_server import _read_proofs, _build_proof_lookup
from static_checks import check_python, check_proof_file, _read_rule_descriptions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_spec(spec_dir, feature, rules):
    """Write a spec file and return its path."""
    os.makedirs(spec_dir, exist_ok=True)
    content = f"# Feature: {feature}\n\n## Rules\n"
    for rid, desc in rules.items():
        content += f"- {rid}: {desc}\n"
    content += "\n## Proof\n"
    for rid in rules:
        pid = rid.replace("RULE", "PROOF")
        content += f"- {pid} ({rid}): test\n"
    path = os.path.join(spec_dir, f"{feature}.md")
    with open(path, 'w') as f:
        f.write(content)
    return path


def _write_proof_file(spec_dir, feature, tier, proofs):
    """Write a proof JSON file directly."""
    path = os.path.join(spec_dir, f"{feature}.proofs-{tier}.json")
    with open(path, 'w') as f:
        json.dump({"tier": tier, "proofs": proofs}, f, indent=2)
        f.write("\n")
    return path


def _proof_entry(feature, proof_id, rule_id, status="pass", tier="unit",
                 test_file="tests/test.py", test_name="test_func"):
    return {
        "feature": feature, "id": proof_id, "rule": rule_id,
        "test_file": test_file, "test_name": test_name,
        "status": status, "tier": tier,
    }


# ===========================================================================
# AREA 1: Multi-feature, multi-tier, multi-language merge stress tests
# ===========================================================================

class TestMultiFeatureMerge:
    """Multiple features coexisting in the same proof file via feature-scoped overwrite."""

    def test_three_features_share_one_proof_file(self, tmp_path):
        """Three features written sequentially to the same proof file — all preserved."""
        spec_dir = tmp_path / "specs" / "api"
        spec_dir.mkdir(parents=True)
        proof_path = spec_dir / "login.proofs-unit.json"

        # Feature A writes first
        _write_proof_file(str(spec_dir), "login", "unit", [
            _proof_entry("login", "PROOF-1", "RULE-1"),
        ])

        # Feature B writes second — must preserve A
        with open(str(proof_path)) as f:
            existing = json.load(f).get("proofs", [])
        kept = [e for e in existing if e.get("feature") != "signup"]
        with open(str(proof_path), 'w') as f:
            json.dump({"tier": "unit", "proofs": kept + [
                _proof_entry("signup", "PROOF-1", "RULE-1"),
            ]}, f, indent=2)

        # Feature C writes third — must preserve A and B
        with open(str(proof_path)) as f:
            existing = json.load(f).get("proofs", [])
        kept = [e for e in existing if e.get("feature") != "logout"]
        with open(str(proof_path), 'w') as f:
            json.dump({"tier": "unit", "proofs": kept + [
                _proof_entry("logout", "PROOF-1", "RULE-1"),
            ]}, f, indent=2)

        # Verify all three features survive
        with open(str(proof_path)) as f:
            data = json.load(f)
        features = {p["feature"] for p in data["proofs"]}
        assert features == {"login", "signup", "logout"}, f"Expected 3 features, got {features}"
        assert len(data["proofs"]) == 3

    def test_overwrite_replaces_only_own_feature(self, tmp_path):
        """Re-running feature A replaces A's proofs but leaves B untouched."""
        spec_dir = tmp_path / "specs" / "api"
        spec_dir.mkdir(parents=True)

        # Initial: A has 2 proofs, B has 1 proof
        _write_proof_file(str(spec_dir), "login", "unit", [
            _proof_entry("login", "PROOF-1", "RULE-1"),
            _proof_entry("login", "PROOF-2", "RULE-2"),
            _proof_entry("billing", "PROOF-1", "RULE-1"),
        ])

        # A re-runs with different results (now only 1 proof, and it fails)
        proof_path = spec_dir / "login.proofs-unit.json"
        with open(str(proof_path)) as f:
            existing = json.load(f).get("proofs", [])
        kept = [e for e in existing if e.get("feature") != "login"]
        new_login = [_proof_entry("login", "PROOF-1", "RULE-1", status="fail")]
        with open(str(proof_path), 'w') as f:
            json.dump({"tier": "unit", "proofs": kept + new_login}, f, indent=2)

        with open(str(proof_path)) as f:
            data = json.load(f)

        # B's proof still there
        billing_proofs = [p for p in data["proofs"] if p["feature"] == "billing"]
        assert len(billing_proofs) == 1
        assert billing_proofs[0]["status"] == "pass"

        # A replaced: only 1 proof now, and it's fail
        login_proofs = [p for p in data["proofs"] if p["feature"] == "login"]
        assert len(login_proofs) == 1
        assert login_proofs[0]["status"] == "fail"


class TestMultiTierAggregation:
    """sync_status merges proofs from unit + e2e tiers into one coverage picture."""

    def test_unit_and_e2e_proofs_merged(self, tmp_path):
        """Feature has RULE-1 proved by unit and RULE-2 proved by e2e — both count."""
        spec_dir = tmp_path / "specs" / "auth"
        spec_dir.mkdir(parents=True)
        _write_spec(str(spec_dir), "login", {
            "RULE-1": "Returns 200 on valid creds",
            "RULE-2": "Rate limits after 5 failures",
        })

        # Unit tier proves RULE-1
        _write_proof_file(str(spec_dir), "login", "unit", [
            _proof_entry("login", "PROOF-1", "RULE-1", tier="unit"),
        ])
        # E2E tier proves RULE-2
        _write_proof_file(str(spec_dir), "login", "e2e", [
            _proof_entry("login", "PROOF-2", "RULE-2", tier="e2e"),
        ])

        all_proofs = _read_proofs(str(tmp_path))
        assert "login" in all_proofs
        assert len(all_proofs["login"]) == 2

        rule_entries = [
            ("RULE-1", "own", None, False),
            ("RULE-2", "own", None, False),
        ]
        lookup = _build_proof_lookup("login", rule_entries, all_proofs)
        assert "RULE-1" in lookup, "RULE-1 from unit tier should be found"
        assert "RULE-2" in lookup, "RULE-2 from e2e tier should be found"

    def test_fail_in_e2e_overrides_pass_in_unit(self, tmp_path):
        """Same rule proved pass in unit but fail in e2e — fail wins."""
        spec_dir = tmp_path / "specs" / "auth"
        spec_dir.mkdir(parents=True)
        _write_spec(str(spec_dir), "login", {"RULE-1": "Returns 200"})

        _write_proof_file(str(spec_dir), "login", "unit", [
            _proof_entry("login", "PROOF-1", "RULE-1", status="pass", tier="unit"),
        ])
        _write_proof_file(str(spec_dir), "login", "e2e", [
            _proof_entry("login", "PROOF-2", "RULE-1", status="fail", tier="e2e"),
        ])

        all_proofs = _read_proofs(str(tmp_path))
        rule_entries = [("RULE-1", "own", None, False)]
        lookup = _build_proof_lookup("login", rule_entries, all_proofs)

        assert lookup["RULE-1"]["status"] == "fail", (
            "fail from e2e should override pass from unit"
        )

    def test_pass_does_not_override_earlier_fail(self, tmp_path):
        """If fail is seen first, a later pass doesn't overwrite it."""
        spec_dir = tmp_path / "specs" / "auth"
        spec_dir.mkdir(parents=True)
        _write_spec(str(spec_dir), "login", {"RULE-1": "Returns 200"})

        # Single file: fail entry first, then pass entry
        _write_proof_file(str(spec_dir), "login", "unit", [
            _proof_entry("login", "PROOF-1", "RULE-1", status="fail", tier="unit"),
            _proof_entry("login", "PROOF-2", "RULE-1", status="pass", tier="unit"),
        ])

        all_proofs = _read_proofs(str(tmp_path))
        rule_entries = [("RULE-1", "own", None, False)]
        lookup = _build_proof_lookup("login", rule_entries, all_proofs)

        # _build_proof_lookup: "if rule not in proof_by_rule or status == 'fail'"
        # First entry (fail) stored. Second entry (pass) doesn't overwrite because
        # it's not fail. So fail sticks.
        assert lookup["RULE-1"]["status"] == "fail", (
            "A passing proof should not override an earlier failing proof"
        )


class TestMultiLanguageSameFile:
    """Multiple languages produce proofs for different features in the same spec directory."""

    @pytest.mark.skipif(not shutil.which('gcc'), reason='gcc not available')
    @pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
    def test_c_and_sql_proofs_coexist(self, tmp_path):
        """C proves RULE-1 of feature_a, SQL proves RULE-1 of feature_b — same dir."""
        spec_dir = tmp_path / "specs" / "core"
        spec_dir.mkdir(parents=True)
        _write_spec(str(spec_dir), "math_ops", {"RULE-1": "add returns sum"})
        _write_spec(str(spec_dir), "data_checks", {"RULE-1": "constraint enforced"})

        # --- C: prove math_ops ---
        shutil.copy(os.path.join(PROOF_SCRIPTS, 'c_purlin.h'), str(tmp_path))
        c_file = tmp_path / "test_math.c"
        c_file.write_text('''
#include "c_purlin.h"
int main(void) {
    int sum = 2 + 3;
    purlin_proof("math_ops", "PROOF-1", "RULE-1",
                 sum == 5, "test_add", "test_math.c", "unit");
    purlin_proof_finish();
    return 0;
}
''')
        binary = tmp_path / "test_math"
        subprocess.run(['gcc', '-o', str(binary), str(c_file), '-I', str(tmp_path)],
                       capture_output=True, text=True, check=True)
        c_output = subprocess.run([str(binary)], capture_output=True, text=True).stdout
        subprocess.run(
            [sys.executable, os.path.join(PROOF_SCRIPTS, 'c_purlin_emit.py')],
            input=c_output, capture_output=True, text=True, cwd=str(tmp_path)
        )

        # --- SQL: prove data_checks ---
        db = tmp_path / "test.db"
        subprocess.run(['sqlite3', str(db)],
                       input='CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT UNIQUE);',
                       capture_output=True, text=True, check=True)
        sql_file = tmp_path / "test_constraints.sql"
        sql_file.write_text('''\
-- @purlin data_checks PROOF-1 RULE-1 unit
-- Test: unique constraint works
INSERT INTO t (val) VALUES ('x');
INSERT OR IGNORE INTO t (val) VALUES ('x');
SELECT CASE WHEN (SELECT count(*) FROM t) = 1 THEN 'PASS' ELSE 'FAIL' END;
''')
        subprocess.run(
            ['bash', os.path.join(PROOF_SCRIPTS, 'sql_purlin.sh'), str(sql_file), str(db)],
            capture_output=True, text=True, cwd=str(tmp_path)
        )

        # --- Verify both features have proofs ---
        all_proofs = _read_proofs(str(tmp_path))
        assert "math_ops" in all_proofs, f"math_ops missing from {list(all_proofs.keys())}"
        assert "data_checks" in all_proofs, f"data_checks missing from {list(all_proofs.keys())}"
        assert all_proofs["math_ops"][0]["status"] == "pass"
        assert all_proofs["data_checks"][0]["status"] == "pass"


# ===========================================================================
# AREA 2: Cheating patterns — tests that LOOK correct but are misleading
# ===========================================================================

class TestTautologicalEscapeHatch:
    """Tests with OR branches that always evaluate True, making assertions no-ops."""

    def test_static_checks_detects_assert_true_in_or(self, tmp_path):
        """Python test with `assert func() or True` — should be caught as assert_true."""
        test_file = tmp_path / "test_cheat.py"
        test_file.write_text('''\
import pytest

@pytest.mark.proof("login", "PROOF-1", "RULE-1")
def test_tautological_or():
    result = some_function()
    assert result > 0 or True
''')
        results = check_python(str(test_file), "login")
        assert len(results) == 1
        assert results[0]["status"] == "fail"
        assert results[0]["check"] == "assert_true"

    @pytest.mark.skipif(not shutil.which('gcc'), reason='gcc not available')
    def test_c_tautological_proof_detected_by_proof_file_check(self, tmp_path):
        """C test where assertion is always true (1 == 1) — proof file records pass,
        but the test proves nothing. check_proof_file won't catch this (it's semantic),
        but the proof JSON should be well-formed for LLM audit to evaluate."""
        spec_dir = tmp_path / "specs" / "auth"
        spec_dir.mkdir(parents=True)
        _write_spec(str(spec_dir), "login", {"RULE-1": "Validates password hash"})

        shutil.copy(os.path.join(PROOF_SCRIPTS, 'c_purlin.h'), str(tmp_path))
        c_file = tmp_path / "test_cheat.c"
        c_file.write_text('''
#include "c_purlin.h"
int main(void) {
    /* CHEATING: assertion is always true, doesn't test password validation */
    purlin_proof("login", "PROOF-1", "RULE-1",
                 1 == 1, "test_validates_password", "test_cheat.c", "unit");
    purlin_proof_finish();
    return 0;
}
''')
        binary = tmp_path / "test_cheat"
        subprocess.run(['gcc', '-o', str(binary), str(c_file), '-I', str(tmp_path)],
                       capture_output=True, text=True, check=True)
        c_output = subprocess.run([str(binary)], capture_output=True, text=True).stdout
        subprocess.run(
            [sys.executable, os.path.join(PROOF_SCRIPTS, 'c_purlin_emit.py')],
            input=c_output, capture_output=True, text=True, cwd=str(tmp_path)
        )

        # The proof file exists and shows pass — this is the problem.
        # A tautological C test produces a valid-looking proof.
        proof_file = spec_dir / "login.proofs-unit.json"
        with open(str(proof_file)) as f:
            data = json.load(f)
        assert data["proofs"][0]["status"] == "pass"
        assert data["proofs"][0]["test_name"] == "test_validates_password"

        # Structural check won't catch it (it's in C, not Python).
        # But the proof file is well-formed, confirming it reaches LLM audit.
        findings = check_proof_file(str(proof_file), spec_path=str(spec_dir / "login.md"))
        assert len(findings) == 0, "No structural issues — this is a semantic cheat for LLM to catch"


class TestAssertionOnFixture:
    """Tests that assert properties of their own setup data, not code output."""

    def test_python_asserts_constant_not_output(self, tmp_path):
        """Test asserts MODULE_CONSTANT == expected — proves setup, not behavior.
        Static checks won't catch this (it has a real assertion), but the test
        is meaningless because it doesn't call any code under test."""
        test_file = tmp_path / "test_fixture_cheat.py"
        test_file.write_text('''\
import pytest

EXPECTED_USERS = ["alice", "bob", "charlie"]

@pytest.mark.proof("user_mgmt", "PROOF-1", "RULE-1")
def test_list_users_returns_three():
    """Claims to test list_users() but only checks the fixture."""
    # CHEATING: never calls list_users(), just validates test data
    assert len(EXPECTED_USERS) == 3
    assert "alice" in EXPECTED_USERS
''')
        results = check_python(str(test_file), "user_mgmt")
        # Static checks pass (there ARE assertions) — this is a semantic cheat
        assert len(results) == 1
        assert results[0]["status"] == "pass", (
            "Static checks pass — this cheat needs LLM audit to detect"
        )

    @pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
    def test_sql_asserts_setup_not_query_result(self, tmp_path):
        """SQL test that validates its own INSERT, not a constraint."""
        spec_dir = tmp_path / "specs" / "db"
        spec_dir.mkdir(parents=True)
        _write_spec(str(spec_dir), "data_integrity", {
            "RULE-1": "Foreign key constraint rejects orphan rows",
        })

        db = tmp_path / "test.db"
        subprocess.run(['sqlite3', str(db)],
                       input='CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER);',
                       capture_output=True, text=True, check=True)

        # CHEATING: test inserts a row and then checks it exists.
        # It never tests the foreign key constraint at all.
        sql_file = tmp_path / "test_cheat.sql"
        sql_file.write_text('''\
-- @purlin data_integrity PROOF-1 RULE-1 unit
-- Test: foreign key constraint rejects orphan rows
INSERT INTO orders (user_id) VALUES (1);
SELECT CASE WHEN (SELECT count(*) FROM orders) = 1
       THEN 'PASS' ELSE 'FAIL' END;
''')

        result = subprocess.run(
            ['bash', os.path.join(PROOF_SCRIPTS, 'sql_purlin.sh'), str(sql_file), str(db)],
            capture_output=True, text=True, cwd=str(tmp_path)
        )
        proof_data = json.loads(result.stdout)
        # It "passes" — but it didn't test the constraint at all
        assert proof_data["proofs"][0]["status"] == "pass"

        # Verify the proof file is well-formed for LLM to evaluate
        proof_file = spec_dir / "data_integrity.proofs-unit.json"
        assert proof_file.exists()
        findings = check_proof_file(str(proof_file), spec_path=str(spec_dir / "data_integrity.md"))
        assert len(findings) == 0, "Structural checks pass — semantic cheat for LLM"


class TestMisleadingPassingProofs:
    """Tests that produce legitimate-looking proof JSON but don't test what they claim."""

    @pytest.mark.skipif(not shutil.which('php'), reason='php not available')
    def test_php_tests_wrong_function(self, tmp_path):
        """PHP test claims to prove password hashing but tests string length instead."""
        spec_dir = tmp_path / "specs" / "auth"
        spec_dir.mkdir(parents=True)
        _write_spec(str(spec_dir), "password_security", {
            "RULE-1": "Passwords are hashed with bcrypt before storage",
        })

        php_file = tmp_path / "test_misleading.php"
        php_file.write_text(r'''<?php
function hash_password(string $pw): string {
    return password_hash($pw, PASSWORD_BCRYPT);
}

/** @purlin password_security PROOF-1 RULE-1 unit */
function test_password_hashed_with_bcrypt() {
    // MISLEADING: tests string length, not that bcrypt was used.
    // A SHA-256 hash is also 60+ chars. This would pass even if
    // hash_password() used md5() internally.
    $hashed = hash_password("secret123");
    if (strlen($hashed) < 50) {
        throw new Exception("Hash too short: " . strlen($hashed));
    }
    // Doesn't verify: password_verify("secret123", $hashed)
    // Doesn't verify: str_starts_with($hashed, "$2y$")
}
''')

        plugin = os.path.join(PROOF_SCRIPTS, 'phpunit_purlin.php')
        result = subprocess.run(
            ['php', plugin, str(php_file)],
            capture_output=True, text=True, cwd=str(tmp_path)
        )
        proof_data = json.loads(result.stdout)
        # It passes — but the test is misleading
        assert proof_data["proofs"][0]["status"] == "pass"
        assert proof_data["proofs"][0]["test_name"] == "test_password_hashed_with_bcrypt"

    @pytest.mark.skipif(not shutil.which('tsc'), reason='tsc not available')
    def test_typescript_happy_path_only(self, tmp_path):
        """TypeScript test claims to prove input validation but only tests valid input."""
        spec_dir = tmp_path / "specs" / "api"
        spec_dir.mkdir(parents=True)
        _write_spec(str(spec_dir), "input_validation", {
            "RULE-1": "Rejects emails without @ symbol",
        })

        ts_file = tmp_path / "test_misleading.ts"
        ts_file.write_text('''\
function validateEmail(email: string): boolean {
    return email.includes("@");
}

interface ProofEntry {
    feature: string; id: string; rule: string;
    test_file: string; test_name: string;
    status: "pass" | "fail"; tier: string;
}

const proofs: ProofEntry[] = [];

// MISLEADING: claims to prove rejection, but only tests a valid email.
// The rule says "rejects emails WITHOUT @" but the test sends an email WITH @.
const result = validateEmail("user@example.com");
proofs.push({
    feature: "input_validation", id: "PROOF-1", rule: "RULE-1",
    test_file: "test_misleading.ts",
    test_name: "test_rejects_emails_without_at",
    status: result === true ? "pass" : "fail",
    tier: "unit",
});

console.log(JSON.stringify({ proofs }, null, 2));
''')

        tsconfig = tmp_path / "tsconfig.json"
        tsconfig.write_text(json.dumps({
            "compilerOptions": {"target": "ES2020", "module": "commonjs",
                                "strict": True, "outDir": str(tmp_path / "dist")},
            "include": ["*.ts"],
        }))

        subprocess.run(['tsc', '--project', str(tsconfig)],
                       capture_output=True, text=True, check=True, cwd=str(tmp_path))
        run_result = subprocess.run(
            ['node', str(tmp_path / 'dist' / 'test_misleading.js')],
            capture_output=True, text=True
        )
        proof_data = json.loads(run_result.stdout)
        # It passes — but it tested the opposite of what the rule requires
        assert proof_data["proofs"][0]["status"] == "pass"
        assert proof_data["proofs"][0]["test_name"] == "test_rejects_emails_without_at"


class TestConflictingMultiTierProofs:
    """Edge cases where unit tests pass but e2e tests fail for the same rule."""

    @pytest.mark.skipif(not shutil.which('gcc'), reason='gcc not available')
    @pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
    def test_c_passes_but_sql_e2e_fails_same_rule(self, tmp_path):
        """C unit test says RULE-1 passes, SQL e2e test says it fails.
        The fail must win in _build_proof_lookup."""
        spec_dir = tmp_path / "specs" / "data"
        spec_dir.mkdir(parents=True)
        _write_spec(str(spec_dir), "validation", {
            "RULE-1": "Rejects negative quantities",
        })

        # --- C unit test: passes (tests the function in isolation) ---
        shutil.copy(os.path.join(PROOF_SCRIPTS, 'c_purlin.h'), str(tmp_path))
        c_file = tmp_path / "test_validate.c"
        c_file.write_text('''
#include "c_purlin.h"
int validate_qty(int qty) { return qty >= 0 ? 0 : -1; }
int main(void) {
    purlin_proof("validation", "PROOF-1", "RULE-1",
                 validate_qty(-5) == -1,
                 "test_rejects_negative", "test_validate.c", "unit");
    purlin_proof_finish();
    return 0;
}
''')
        binary = tmp_path / "test_validate"
        subprocess.run(['gcc', '-o', str(binary), str(c_file), '-I', str(tmp_path)],
                       capture_output=True, text=True, check=True)
        c_output = subprocess.run([str(binary)], capture_output=True, text=True).stdout
        subprocess.run(
            [sys.executable, os.path.join(PROOF_SCRIPTS, 'c_purlin_emit.py')],
            input=c_output, capture_output=True, text=True, cwd=str(tmp_path)
        )

        # --- SQL e2e test: FAILS (the database doesn't have the constraint) ---
        db = tmp_path / "test.db"
        subprocess.run(['sqlite3', str(db)],
                       input='CREATE TABLE orders (qty INTEGER);',
                       capture_output=True, text=True, check=True)

        sql_file = tmp_path / "test_e2e.sql"
        sql_file.write_text('''\
-- @purlin validation PROOF-2 RULE-1 e2e
-- Test: database rejects negative quantities
INSERT INTO orders (qty) VALUES (-5);
SELECT CASE WHEN (SELECT count(*) FROM orders WHERE qty < 0) = 0
       THEN 'PASS' ELSE 'FAIL' END;
''')
        subprocess.run(
            ['bash', os.path.join(PROOF_SCRIPTS, 'sql_purlin.sh'), str(sql_file), str(db)],
            capture_output=True, text=True, cwd=str(tmp_path)
        )

        # --- Verify fail wins ---
        all_proofs = _read_proofs(str(tmp_path))
        assert "validation" in all_proofs
        assert len(all_proofs["validation"]) == 2

        # One pass (unit), one fail (e2e) — fail must win
        statuses = {p["status"] for p in all_proofs["validation"]}
        assert statuses == {"pass", "fail"}, f"Expected both pass and fail, got {statuses}"

        rule_entries = [("RULE-1", "own", None, False)]
        lookup = _build_proof_lookup("validation", rule_entries, all_proofs)
        assert lookup["RULE-1"]["status"] == "fail", (
            "The e2e failure must override the unit pass — "
            "the code works in isolation but fails in production context"
        )


class TestCollisionWithRealPluginOutput:
    """Proof ID collisions produced by real plugin output, detected by check_proof_file."""

    @pytest.mark.skipif(not shutil.which('php'), reason='php not available')
    @pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
    def test_php_and_sql_both_claim_proof_1(self, tmp_path):
        """PHP and SQL both emit PROOF-1 for different rules into the same proof file.
        check_proof_file must detect the collision."""
        spec_dir = tmp_path / "specs" / "api"
        spec_dir.mkdir(parents=True)
        _write_spec(str(spec_dir), "mixed_feature", {
            "RULE-1": "Validates input format",
            "RULE-2": "Enforces database constraint",
        })

        # PHP writes PROOF-1 for RULE-1
        php_file = tmp_path / "test_a.php"
        php_file.write_text(r'''<?php
/** @purlin mixed_feature PROOF-1 RULE-1 unit */
function test_validates_format() {
    $valid = preg_match('/^\d{3}-\d{4}$/', "123-4567");
    if (!$valid) throw new Exception("Format rejected");
}
''')
        subprocess.run(
            ['php', os.path.join(PROOF_SCRIPTS, 'phpunit_purlin.php'), str(php_file)],
            capture_output=True, text=True, cwd=str(tmp_path)
        )

        # Now manually add a SQL-produced PROOF-1 for RULE-2 to the same file
        # (simulating what would happen if sql_purlin wrote to the same feature)
        proof_path = spec_dir / "mixed_feature.proofs-unit.json"
        with open(str(proof_path)) as f:
            data = json.load(f)
        data["proofs"].append(
            _proof_entry("mixed_feature", "PROOF-1", "RULE-2",
                         test_file="test_constraints.sql", test_name="test_constraint")
        )
        with open(str(proof_path), 'w') as f:
            json.dump(data, f, indent=2)

        # Detect the collision
        findings = check_proof_file(
            str(proof_path),
            spec_path=str(spec_dir / "mixed_feature.md")
        )
        collisions = [f for f in findings if f["check"] == "proof_id_collision"]
        assert len(collisions) == 1
        assert collisions[0]["proof_id"] == "PROOF-1"
        assert set(collisions[0]["rules"]) == {"RULE-1", "RULE-2"}


class TestSophisticatedCheats:
    """The hardest-to-detect cheating patterns — tests that look perfect at a glance."""

    def test_logic_mirroring_across_function_boundary(self, tmp_path):
        """Test computes expected by calling the SAME function it's testing.
        If the function has a bug, the test confirms the bug."""
        test_file = tmp_path / "test_mirror.py"
        test_file.write_text('''\
import pytest
import hashlib

def compute_hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

@pytest.mark.proof("hashing", "PROOF-1", "RULE-1")
def test_hash_matches():
    """Looks rigorous but is self-confirming."""
    input_data = "hello world"
    expected = compute_hash(input_data)  # CHEAT: uses the function under test
    result = compute_hash(input_data)
    assert result == expected
''')
        spec_path = tmp_path / "spec.md"
        spec_path.write_text(
            "# Feature: hashing\n\n## Rules\n- RULE-1: SHA-256 hash is computed correctly\n\n"
            "## Proof\n- PROOF-1 (RULE-1): test\n"
        )
        results = check_python(str(test_file), "hashing",
                               _read_rule_descriptions(str(spec_path)))
        assert results[0]["status"] == "fail"
        assert results[0]["check"] == "logic_mirroring"

    def test_mock_replaces_the_thing_being_tested(self, tmp_path):
        """Test mocks bcrypt.checkpw on a rule about bcrypt. The mock makes
        the test pass regardless of whether bcrypt is actually used."""
        test_file = tmp_path / "test_mock_cheat.py"
        test_file.write_text('''\
import pytest
from unittest.mock import patch

@pytest.mark.proof("auth", "PROOF-1", "RULE-1")
@patch("auth.bcrypt.checkpw")
def test_password_verified(mock_checkpw):
    """Looks like it tests bcrypt, but the mock replaces bcrypt entirely."""
    mock_checkpw.return_value = True
    from auth import verify_password
    assert verify_password("alice", "secret") == True
''')
        spec_path = tmp_path / "spec.md"
        spec_path.write_text(
            "# Feature: auth\n\n## Rules\n- RULE-1: Passwords verified with bcrypt\n\n"
            "## Proof\n- PROOF-1 (RULE-1): test\n"
        )
        results = check_python(str(test_file), "auth",
                               _read_rule_descriptions(str(spec_path)))
        assert results[0]["status"] == "fail"
        assert results[0]["check"] == "mock_target_match"

    def test_no_assertions_disguised_as_thorough_test(self, tmp_path):
        """Test has lots of setup code but zero assertions — runs code but checks nothing."""
        test_file = tmp_path / "test_no_assert.py"
        test_file.write_text('''\
import pytest
import json

@pytest.mark.proof("api", "PROOF-1", "RULE-1")
def test_api_returns_valid_json():
    """Looks thorough — creates request, calls endpoint, parses response.
    But there's no assertion. The response could be anything."""
    request = {"method": "POST", "path": "/login", "body": {"user": "alice"}}
    # In a real test: response = client.post(request)
    response = {"status": 200, "body": {"token": "abc123"}}
    parsed = json.loads(json.dumps(response))
    token = parsed.get("body", {}).get("token")
    # CHEAT: no assertion on token, status, or anything else
''')
        results = check_python(str(test_file), "api")
        assert results[0]["status"] == "fail"
        assert results[0]["check"] == "no_assertions"

    @pytest.mark.skipif(not shutil.which('gcc'), reason='gcc not available')
    def test_c_test_name_contradicts_behavior(self, tmp_path):
        """C test named 'test_rejects_negative' but actually accepts negative.
        Name/value drift — the test was patched to pass after a bug was introduced."""
        spec_dir = tmp_path / "specs" / "cart"
        spec_dir.mkdir(parents=True)
        _write_spec(str(spec_dir), "cart_ops", {
            "RULE-1": "Rejects negative quantities",
        })

        shutil.copy(os.path.join(PROOF_SCRIPTS, 'c_purlin.h'), str(tmp_path))
        c_file = tmp_path / "test_name_drift.c"
        c_file.write_text('''
#include "c_purlin.h"
/* Bug: should return -1 for negative, but returns 0 (accepts all) */
int validate_qty(int qty) { return 0; }

int main(void) {
    /* Name says "rejects" but assertion checks return == 0 (accepts!) */
    purlin_proof("cart_ops", "PROOF-1", "RULE-1",
                 validate_qty(-5) == 0,
                 "test_rejects_negative_quantity", "test_name_drift.c", "unit");
    purlin_proof_finish();
    return 0;
}
''')
        binary = tmp_path / "test_name_drift"
        subprocess.run(['gcc', '-o', str(binary), str(c_file), '-I', str(tmp_path)],
                       capture_output=True, text=True, check=True)
        c_output = subprocess.run([str(binary)], capture_output=True, text=True).stdout

        proof_data = json.loads(c_output)
        # The test PASSES — but it's testing the opposite of what the name claims
        assert proof_data["proofs"][0]["status"] == "pass"
        assert proof_data["proofs"][0]["test_name"] == "test_rejects_negative_quantity"
        # Rule says "Rejects" but the test asserts validate_qty(-5) == 0 (accepted!)
        # This is name/value drift — only detectable by LLM semantic analysis
