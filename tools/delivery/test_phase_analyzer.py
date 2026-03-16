#!/usr/bin/env python3
"""Tests for phase_analyzer.py — exercises all 11 automated scenarios."""

import json
import os
import subprocess
import sys
import tempfile
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ANALYZER_PATH = os.path.join(SCRIPT_DIR, 'phase_analyzer.py')

# Track results
results = {"passed": 0, "failed": 0, "total": 0, "details": []}


def record(name, passed, detail=""):
    results["total"] += 1
    if passed:
        results["passed"] += 1
        results["details"].append({"name": name, "status": "PASS"})
        print(f"  PASS: {name}")
    else:
        results["failed"] += 1
        results["details"].append({"name": name, "status": "FAIL", "detail": detail})
        print(f"  FAIL: {name} — {detail}")


def make_project(tmpdir, plan_text, graph_data):
    """Create a minimal project structure for the analyzer."""
    purlin_dir = os.path.join(tmpdir, '.purlin')
    cache_dir = os.path.join(purlin_dir, 'cache')
    os.makedirs(cache_dir, exist_ok=True)

    if plan_text is not None:
        with open(os.path.join(cache_dir, 'delivery_plan.md'), 'w') as f:
            f.write(plan_text)

    if graph_data is not None:
        with open(os.path.join(cache_dir, 'dependency_graph.json'), 'w') as f:
            json.dump(graph_data, f)

    return tmpdir


def run_analyzer(tmpdir):
    """Run phase_analyzer.py with PURLIN_PROJECT_ROOT set."""
    env = os.environ.copy()
    env['PURLIN_PROJECT_ROOT'] = tmpdir
    proc = subprocess.run(
        [sys.executable, ANALYZER_PATH],
        capture_output=True, text=True, env=env
    )
    return proc


def make_graph(features):
    """Build a minimal dependency graph.

    features: list of (filename, [prereq_bare_names])
    """
    return {
        "cycles": [],
        "features": [
            {
                "file": f"features/{name}",
                "label": name,
                "category": "test",
                "prerequisites": prereqs,
            }
            for name, prereqs in features
        ],
        "generated_at": "2026-01-01T00:00:00Z",
    }


def make_plan(phases):
    """Build a delivery plan markdown.

    phases: list of (number, label, status, [feature_names])
    """
    lines = [
        "# Delivery Plan\n",
        "**Created:** 2026-01-01",
        f"**Total Phases:** {len(phases)}\n",
        "## Summary",
        "Test plan.\n",
    ]
    for num, label, status, feats in phases:
        feat_str = ', '.join(feats) if feats else '--'
        lines.append(f"## Phase {num} -- {label} [{status}]")
        lines.append(f"**Features:** {feat_str}")
        lines.append("**Completion Commit:** --")
        lines.append("**QA Bugs Addressed:** --\n")
    lines.append("## Plan Amendments")
    lines.append("_None._")
    return '\n'.join(lines)


# ============================================================
# Scenario: Analyze Delivery Plan with Correct Ordering
# ============================================================
def test_correct_ordering():
    """Phases 1,2,3 sequential with correct dependency chain."""
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([
            ("a.md", []),
            ("b.md", ["a.md"]),
            ("c.md", ["b.md"]),
        ])
        plan = make_plan([
            (1, "Foundation", "PENDING", ["a.md"]),
            (2, "Middle", "PENDING", ["b.md"]),
            (3, "Top", "PENDING", ["c.md"]),
        ])
        make_project(tmpdir, plan, graph)
        proc = run_analyzer(tmpdir)
        data = json.loads(proc.stdout)

        ok = (
            proc.returncode == 0
            and len(data["groups"]) == 3
            and data["groups"][0]["phases"] == [1]
            and data["groups"][1]["phases"] == [2]
            and data["groups"][2]["phases"] == [3]
            and data["reordered"] is False
            and data["warnings"] == []
        )
        record("Analyze Delivery Plan with Correct Ordering", ok,
               f"rc={proc.returncode}, data={json.dumps(data)}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Detect Incorrect Phase Ordering
# ============================================================
def test_incorrect_ordering():
    """Phases 3,4,5,6 where 3 depends on 4, 4 depends on 6."""
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([
            ("f3.md", ["f4.md"]),
            ("f4.md", ["f6.md"]),
            ("f5.md", []),
            ("f6.md", []),
        ])
        plan = make_plan([
            (3, "Three", "PENDING", ["f3.md"]),
            (4, "Four", "PENDING", ["f4.md"]),
            (5, "Five", "PENDING", ["f5.md"]),
            (6, "Six", "PENDING", ["f6.md"]),
        ])
        make_project(tmpdir, plan, graph)
        proc = run_analyzer(tmpdir)
        data = json.loads(proc.stdout)

        # Phase 6 must come first, then 4, then 3 and 5 can be parallel
        ok = (
            proc.returncode == 0
            and data["reordered"] is True
            and len(data["warnings"]) > 0
        )

        # Verify execution order: 6 before 4 before 3
        phase_order = []
        for g in data["groups"]:
            phase_order.extend(g["phases"])

        idx_6 = phase_order.index(6)
        idx_4 = phase_order.index(4)
        idx_3 = phase_order.index(3)
        ok = ok and idx_6 < idx_4 < idx_3

        record("Detect Incorrect Phase Ordering", ok,
               f"rc={proc.returncode}, order={phase_order}, warnings={data['warnings']}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Group Independent Phases for Parallel Execution
# ============================================================
def test_parallel_grouping():
    """Phases A(1), B(2) independent; C(3) depends on both."""
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([
            ("a.md", []),
            ("b.md", []),
            ("c.md", ["a.md", "b.md"]),
        ])
        plan = make_plan([
            (1, "A", "PENDING", ["a.md"]),
            (2, "B", "PENDING", ["b.md"]),
            (3, "C", "PENDING", ["c.md"]),
        ])
        make_project(tmpdir, plan, graph)
        proc = run_analyzer(tmpdir)
        data = json.loads(proc.stdout)

        ok = proc.returncode == 0 and len(data["groups"]) == 2
        if ok:
            first_group = data["groups"][0]
            second_group = data["groups"][1]
            ok = (
                set(first_group["phases"]) == {1, 2}
                and first_group["parallel"] is True
                and second_group["phases"] == [3]
                and second_group["parallel"] is False
            )

        record("Group Independent Phases for Parallel Execution", ok,
               f"groups={json.dumps(data.get('groups', []))}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: All Phases Independent
# ============================================================
def test_all_independent():
    """3 phases, no cross-dependencies -> single parallel group."""
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([
            ("x.md", []),
            ("y.md", []),
            ("z.md", []),
        ])
        plan = make_plan([
            (1, "X", "PENDING", ["x.md"]),
            (2, "Y", "PENDING", ["y.md"]),
            (3, "Z", "PENDING", ["z.md"]),
        ])
        make_project(tmpdir, plan, graph)
        proc = run_analyzer(tmpdir)
        data = json.loads(proc.stdout)

        ok = (
            proc.returncode == 0
            and len(data["groups"]) == 1
            and set(data["groups"][0]["phases"]) == {1, 2, 3}
            and data["groups"][0]["parallel"] is True
        )
        record("All Phases Independent", ok,
               f"groups={json.dumps(data.get('groups', []))}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: All Phases Dependent (Fully Sequential)
# ============================================================
def test_fully_sequential():
    """3 phases, fully chained."""
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([
            ("s1.md", []),
            ("s2.md", ["s1.md"]),
            ("s3.md", ["s2.md"]),
        ])
        plan = make_plan([
            (1, "Step1", "PENDING", ["s1.md"]),
            (2, "Step2", "PENDING", ["s2.md"]),
            (3, "Step3", "PENDING", ["s3.md"]),
        ])
        make_project(tmpdir, plan, graph)
        proc = run_analyzer(tmpdir)
        data = json.loads(proc.stdout)

        ok = (
            proc.returncode == 0
            and len(data["groups"]) == 3
            and all(not g["parallel"] for g in data["groups"])
        )
        record("All Phases Dependent (Fully Sequential)", ok,
               f"groups={json.dumps(data.get('groups', []))}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: No Delivery Plan Exists
# ============================================================
def test_no_delivery_plan():
    """Missing delivery plan -> error exit."""
    tmpdir = tempfile.mkdtemp()
    try:
        # Create .purlin dir but no delivery plan
        purlin_dir = os.path.join(tmpdir, '.purlin', 'cache')
        os.makedirs(purlin_dir, exist_ok=True)
        # Write dependency graph but no delivery plan
        with open(os.path.join(purlin_dir, 'dependency_graph.json'), 'w') as f:
            json.dump({"cycles": [], "features": []}, f)

        proc = run_analyzer(tmpdir)
        ok = proc.returncode != 0 and "delivery plan" in proc.stderr.lower()
        record("No Delivery Plan Exists", ok,
               f"rc={proc.returncode}, stderr={proc.stderr[:200]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: No Pending Phases
# ============================================================
def test_no_pending_phases():
    """All phases COMPLETE -> empty groups, exit 0."""
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([("done.md", [])])
        plan = make_plan([
            (1, "Done", "COMPLETE", ["done.md"]),
        ])
        make_project(tmpdir, plan, graph)
        proc = run_analyzer(tmpdir)
        data = json.loads(proc.stdout)

        ok = (
            proc.returncode == 0
            and data["groups"] == []
            and data["reordered"] is False
            and data["original_order"] == []
        )
        record("No Pending Phases", ok,
               f"rc={proc.returncode}, data={json.dumps(data)}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Feature Not in Dependency Graph
# ============================================================
def test_feature_not_in_graph():
    """Phase references feature not in graph -> warning, treats as no deps."""
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([("known.md", [])])
        plan = make_plan([
            (1, "Mixed", "PENDING", ["known.md", "unknown.md"]),
        ])
        make_project(tmpdir, plan, graph)
        proc = run_analyzer(tmpdir)
        data = json.loads(proc.stdout)

        ok = (
            proc.returncode == 0
            and len(data["groups"]) == 1
            and "unknown.md" in proc.stderr
        )
        record("Feature Not in Dependency Graph", ok,
               f"rc={proc.returncode}, stderr={proc.stderr[:200]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Transitive Dependency Detection
# ============================================================
def test_transitive_dependency():
    """Phase 2 feature B depends on C which depends on Phase 1 feature A."""
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([
            ("a.md", []),
            ("b.md", ["c.md"]),
            ("c.md", ["a.md"]),
        ])
        plan = make_plan([
            (1, "Base", "PENDING", ["a.md"]),
            (2, "Derived", "PENDING", ["b.md"]),
        ])
        make_project(tmpdir, plan, graph)
        proc = run_analyzer(tmpdir)
        data = json.loads(proc.stdout)

        # Phase 2 must come after Phase 1 due to transitive dependency
        phase_order = []
        for g in data["groups"]:
            phase_order.extend(g["phases"])

        ok = (
            proc.returncode == 0
            and phase_order.index(1) < phase_order.index(2)
        )
        record("Transitive Dependency Detection", ok,
               f"order={phase_order}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: COMPLETE and IN_PROGRESS Phases Excluded
# ============================================================
def test_exclude_non_pending():
    """Only PENDING phases appear in output."""
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([
            ("done.md", []),
            ("wip.md", []),
            ("todo.md", []),
        ])
        plan = make_plan([
            (1, "Done", "COMPLETE", ["done.md"]),
            (2, "WIP", "IN_PROGRESS", ["wip.md"]),
            (3, "Todo", "PENDING", ["todo.md"]),
        ])
        make_project(tmpdir, plan, graph)
        proc = run_analyzer(tmpdir)
        data = json.loads(proc.stdout)

        all_phases = []
        for g in data["groups"]:
            all_phases.extend(g["phases"])

        ok = (
            proc.returncode == 0
            and all_phases == [3]
            and 1 not in all_phases
            and 2 not in all_phases
        )
        record("COMPLETE and IN_PROGRESS Phases Excluded", ok,
               f"phases={all_phases}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Submodule Path Resolution
# ============================================================
def test_submodule_path_resolution():
    """PURLIN_PROJECT_ROOT overrides path resolution."""
    tmpdir = tempfile.mkdtemp()
    try:
        # Create a "consumer project" structure at a non-standard location
        consumer_root = os.path.join(tmpdir, "my_project")
        os.makedirs(consumer_root)
        graph = make_graph([("feat.md", [])])
        plan = make_plan([
            (1, "Only", "PENDING", ["feat.md"]),
        ])
        make_project(consumer_root, plan, graph)

        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = consumer_root
        proc = subprocess.run(
            [sys.executable, ANALYZER_PATH],
            capture_output=True, text=True, env=env
        )
        data = json.loads(proc.stdout)

        ok = (
            proc.returncode == 0
            and len(data["groups"]) == 1
            and data["groups"][0]["phases"] == [1]
        )
        record("Submodule Path Resolution", ok,
               f"rc={proc.returncode}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


def write_results():
    """Write tests.json to the correct location."""
    project_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if not project_root:
        # Find it via climbing
        project_root = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))

    results_dir = os.path.join(project_root, 'tests', 'phase_analyzer')
    os.makedirs(results_dir, exist_ok=True)

    status = "PASS" if results["failed"] == 0 else "FAIL"
    output = {
        "status": status,
        "passed": results["passed"],
        "failed": results["failed"],
        "total": results["total"],
        "details": results["details"],
    }

    results_path = os.path.join(results_dir, 'tests.json')
    with open(results_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nResults written to {results_path}")
    print(f"Status: {status} ({results['passed']}/{results['total']})")


if __name__ == '__main__':
    print("Running phase_analyzer tests...\n")

    test_correct_ordering()
    test_incorrect_ordering()
    test_parallel_grouping()
    test_all_independent()
    test_fully_sequential()
    test_no_delivery_plan()
    test_no_pending_phases()
    test_feature_not_in_graph()
    test_transitive_dependency()
    test_exclude_non_pending()
    test_submodule_path_resolution()

    write_results()
    sys.exit(0 if results["failed"] == 0 else 1)
