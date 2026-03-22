#!/usr/bin/env python3
"""Phase Analyzer — dependency-aware delivery plan analysis.

Reads the delivery plan and dependency graph to determine correct phase
execution order and identify parallelization opportunities. Output is
structured JSON to stdout, suitable for consumption by the continuous
phase builder orchestration loop.

Usage:
    python3 tools/delivery/phase_analyzer.py
    python3 tools/delivery/phase_analyzer.py --intra-phase <phase_number>

Environment:
    PURLIN_PROJECT_ROOT — project root override (submodule-safe)
"""

import argparse
import ast
import glob as glob_mod
import json
import os
import re
import subprocess
import sys
from collections import defaultdict


_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_SCRIPT_DIR, '../../')))
from tools.bootstrap import detect_project_root as _find_project_root


def parse_delivery_plan(plan_text, include_statuses=None):
    """Extract phases from delivery plan markdown.

    Returns list of dicts: [{"number": int, "status": str, "features": [str], "label": str}]
    Only phases matching include_statuses are included (default: PENDING only).
    """
    if include_statuses is None:
        include_statuses = {'PENDING'}

    phases = []
    # Match: ## Phase <N> -- <Label> [<STATUS>]
    phase_pattern = re.compile(
        r'^##\s+Phase\s+(\d+)\s+--\s+(.+?)\s+\[(\w+(?:_\w+)*)\]',
        re.MULTILINE
    )
    features_pattern = re.compile(
        r'^\*\*Features:\*\*\s+(.+)$',
        re.MULTILINE
    )

    for match in phase_pattern.finditer(plan_text):
        phase_num = int(match.group(1))
        label = match.group(2).strip()
        status = match.group(3).upper()

        # Find the **Features:** line after this phase heading
        search_start = match.end()
        feat_match = features_pattern.search(plan_text, search_start)
        if feat_match:
            # Only use it if it's before the next phase heading
            next_phase = phase_pattern.search(plan_text, search_start)
            if next_phase is None or feat_match.start() < next_phase.start():
                feature_names = [
                    f.strip() for f in feat_match.group(1).split(',')
                    if f.strip() and f.strip() != '--'
                ]
            else:
                feature_names = []
        else:
            feature_names = []

        if status in include_statuses:
            phases.append({
                "number": phase_num,
                "status": status,
                "features": feature_names,
                "label": label,
            })

    return phases


def load_dependency_graph(graph_path):
    """Load dependency graph and return feature->prerequisites mapping.

    Returns dict: {"feature_file.md": ["prereq1.md", "prereq2.md"]}
    The keys use the full path (e.g., "features/foo.md") and
    prerequisites are bare filenames (e.g., "foo.md").
    """
    try:
        with open(graph_path, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError, OSError) as e:
        print(f"Error reading dependency graph: {e}", file=sys.stderr)
        sys.exit(1)

    deps = {}
    for feature in data.get('features', []):
        file_path = feature.get('file', '')
        prerequisites = feature.get('prerequisites', [])
        deps[file_path] = prerequisites

    return deps


def build_transitive_closure(deps):
    """Build transitive closure of feature dependencies.

    Input deps maps "features/foo.md" -> ["bar.md", "baz.md"] (bare names).
    Returns dict: {"features/foo.md": {"features/bar.md", "features/baz.md", ...}}
    with all transitive dependencies resolved using full paths.
    """
    # Build a lookup from bare filename to full path
    bare_to_full = {}
    for full_path in deps:
        bare = os.path.basename(full_path)
        bare_to_full[bare] = full_path

    # Build adjacency using full paths
    adj = {}
    for full_path, prereqs in deps.items():
        adj[full_path] = set()
        for bare in prereqs:
            full_prereq = bare_to_full.get(bare)
            if full_prereq:
                adj[full_path].add(full_prereq)

    # Compute transitive closure via DFS
    closure = {}
    for node in adj:
        visited = set()
        stack = list(adj.get(node, set()))
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            stack.extend(adj.get(current, set()) - visited)
        closure[node] = visited

    return closure


def compute_phase_dependencies(phases, closure, all_deps):
    """Determine inter-phase dependency edges.

    Returns dict: {phase_number: set of phase_numbers it depends on}
    Also returns warnings about features not in the dependency graph.
    """
    warnings = []

    # Map features to their phase numbers
    feature_to_phase = {}
    for phase in phases:
        for feat in phase["features"]:
            # Normalize: ensure features/ prefix
            full_path = feat if feat.startswith('features/') else f"features/{feat}"
            feature_to_phase[full_path] = phase["number"]

    # For each phase, collect all transitive dependencies of its features
    phase_deps = {p["number"]: set() for p in phases}

    for phase in phases:
        for feat in phase["features"]:
            full_path = feat if feat.startswith('features/') else f"features/{feat}"

            if full_path not in all_deps:
                warnings.append(
                    f"Feature \"{feat}\" in Phase {phase['number']} "
                    f"not found in dependency graph; treating as no dependencies"
                )
                continue

            trans_deps = closure.get(full_path, set())
            for dep in trans_deps:
                dep_phase = feature_to_phase.get(dep)
                if dep_phase is not None and dep_phase != phase["number"]:
                    phase_deps[phase["number"]].add(dep_phase)

    return phase_deps, warnings


def topological_sort(phases, phase_deps):
    """Topologically sort phases based on inter-phase dependencies.

    Returns (sorted_phase_numbers, reordered, ordering_warnings).
    Exits with error if a cycle is detected.
    """
    phase_numbers = [p["number"] for p in phases]
    original_order = list(phase_numbers)

    # Kahn's algorithm
    in_degree = {p: 0 for p in phase_numbers}
    adj = defaultdict(set)

    for phase_num, deps in phase_deps.items():
        for dep in deps:
            if dep in in_degree:  # Only count deps that are PENDING
                adj[dep].add(phase_num)
                in_degree[phase_num] += 1

    queue = sorted([p for p in phase_numbers if in_degree[p] == 0])
    sorted_order = []

    while queue:
        # Pick the lowest-numbered phase among those with zero in-degree
        # to maintain stability when multiple orderings are valid
        node = queue.pop(0)
        sorted_order.append(node)
        for neighbor in sorted(adj[node]):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
                queue.sort()

    if len(sorted_order) != len(phase_numbers):
        remaining = set(phase_numbers) - set(sorted_order)
        print(
            f"Error: dependency cycle detected among phases: {sorted(remaining)}",
            file=sys.stderr
        )
        sys.exit(1)

    # Check if reordering occurred
    reordered = sorted_order != original_order
    ordering_warnings = []

    if reordered:
        original_positions = {p: i for i, p in enumerate(original_order)}
        for phase_num in sorted_order:
            for dep in phase_deps.get(phase_num, set()):
                if dep in original_positions and phase_num in original_positions:
                    if original_positions[phase_num] < original_positions[dep]:
                        ordering_warnings.append(
                            f"Phase {phase_num} depends on Phase {dep} "
                            f"but was ordered before it in the delivery plan"
                        )

    return sorted_order, reordered, ordering_warnings


def group_parallel_phases(sorted_order, phase_deps):
    """Group phases into execution sets, identifying parallelizable groups.

    Phases that have no inter-dependencies can run in parallel.
    Returns list of dicts: [{"phases": [int], "parallel": bool, "reason": str}]
    """
    if not sorted_order:
        return []

    # Track which phases have been placed into groups
    placed = set()
    groups = []

    # Process phases in topological order, grouping those whose
    # dependencies are all already placed
    remaining = list(sorted_order)

    while remaining:
        # Find all phases whose dependencies are fully satisfied (placed)
        ready = []
        for p in remaining:
            deps = phase_deps.get(p, set())
            pending_deps = deps & set(remaining)
            if not pending_deps:
                ready.append(p)

        if not ready:
            # Should not happen if topological sort succeeded
            break

        # Check if these ready phases have cross-dependencies with each other
        # (they shouldn't since all deps are in 'placed', but verify)
        truly_parallel = []
        for p in ready:
            deps = phase_deps.get(p, set())
            # A phase is parallel-eligible if none of the other ready phases
            # are in its dependency set
            if not (deps & set(ready)):
                truly_parallel.append(p)

        if len(truly_parallel) > 1:
            # Check pairwise: no phase in this group depends on another
            can_parallel = True
            for i, p1 in enumerate(truly_parallel):
                for p2 in truly_parallel[i+1:]:
                    if p2 in phase_deps.get(p1, set()) or p1 in phase_deps.get(p2, set()):
                        can_parallel = False
                        break
                if not can_parallel:
                    break

            if can_parallel:
                phase_list = sorted(truly_parallel)
                reason = (
                    f"no cross-dependencies between "
                    f"{' and '.join(f'Phase {p}' for p in phase_list)}"
                )
                groups.append({
                    "phases": phase_list,
                    "parallel": True,
                    "reason": reason,
                })
                for p in truly_parallel:
                    remaining.remove(p)
                    placed.add(p)
                continue

        # Sequential: take the first ready phase
        p = ready[0]
        deps = phase_deps.get(p, set())
        if not deps:
            reason = "foundation phase — no prior dependencies"
        else:
            dep_strs = sorted(f"Phase {d}" for d in deps)
            reason = f"depends on {', '.join(dep_strs)}"

        groups.append({
            "phases": [p],
            "parallel": False,
            "reason": reason,
        })
        remaining.remove(p)
        placed.add(p)

    return groups


def compute_feature_independence(features, closure):
    """Analyze pairwise independence of features within a phase.

    Same pattern as group_parallel_phases() but operates on features
    instead of phases.

    Args:
        features: list of feature filenames (bare names like "foo.md")
        closure: transitive closure dict from build_transitive_closure()

    Returns list of dicts:
        [{"features": [str], "parallel": bool, "depends_on": [str] (optional)}]
    Groups are ordered: independent groups first, then dependent groups.
    """
    if not features:
        return []

    # Normalize to full paths
    full_paths = []
    for f in features:
        full = f if f.startswith('features/') else f"features/{f}"
        full_paths.append(full)

    # Build pairwise dependency map among these features
    feat_deps = {}
    for fp in full_paths:
        trans = closure.get(fp, set())
        # Only keep dependencies that are within this feature set
        feat_deps[fp] = trans & set(full_paths)

    # Topological sort of features
    in_degree = {fp: 0 for fp in full_paths}
    adj = defaultdict(set)
    for fp, deps in feat_deps.items():
        for dep in deps:
            adj[dep].add(fp)
            in_degree[fp] += 1

    queue = sorted([fp for fp in full_paths if in_degree[fp] == 0])
    sorted_features = []
    while queue:
        node = queue.pop(0)
        sorted_features.append(node)
        for neighbor in sorted(adj[node]):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
                queue.sort()

    # Group into parallel sets (same algorithm as group_parallel_phases)
    groups = []
    remaining = list(sorted_features)
    placed_deps = set()  # track which features have been placed for depends_on

    while remaining:
        ready = []
        for fp in remaining:
            deps = feat_deps.get(fp, set())
            pending = deps & set(remaining)
            if not pending:
                ready.append(fp)

        if not ready:
            break

        # Check if ready features are pairwise independent
        truly_parallel = []
        for fp in ready:
            deps = feat_deps.get(fp, set())
            if not (deps & set(ready)):
                truly_parallel.append(fp)

        if len(truly_parallel) > 1:
            can_parallel = True
            for i, f1 in enumerate(truly_parallel):
                for f2 in truly_parallel[i+1:]:
                    if f2 in feat_deps.get(f1, set()) or f1 in feat_deps.get(f2, set()):
                        can_parallel = False
                        break
                if not can_parallel:
                    break

            if can_parallel:
                bare_names = sorted(os.path.basename(fp) for fp in truly_parallel)
                group = {"features": bare_names, "parallel": True}
                # Check if any feature in this group depends on features
                # from earlier groups
                all_deps_from_earlier = set()
                for fp in truly_parallel:
                    all_deps_from_earlier |= (feat_deps.get(fp, set()) & placed_deps)
                if all_deps_from_earlier:
                    group["depends_on"] = sorted(
                        os.path.basename(d) for d in all_deps_from_earlier
                    )
                groups.append(group)
                for fp in truly_parallel:
                    remaining.remove(fp)
                    placed_deps.add(fp)
                continue

        # Sequential: take the first ready feature
        fp = ready[0]
        bare = os.path.basename(fp)
        group = {"features": [bare], "parallel": False}
        deps_from_earlier = feat_deps.get(fp, set()) & placed_deps
        if deps_from_earlier:
            group["depends_on"] = sorted(
                os.path.basename(d) for d in deps_from_earlier
            )
        groups.append(group)
        remaining.remove(fp)
        placed_deps.add(fp)

    return groups


def extract_python_imports(test_file_path):
    """Parse Python import statements and return set of imported module file paths.

    Excludes standard library modules and test framework imports (pytest, unittest, mock).
    Returns set of resolved file paths relative to project root.
    """
    EXCLUDED_MODULES = {
        'pytest', 'unittest', 'mock', 'unittest.mock',
        'os', 'sys', 'json', 're', 'io', 'copy', 'math', 'random',
        'collections', 'itertools', 'functools', 'operator',
        'pathlib', 'tempfile', 'shutil', 'subprocess', 'argparse',
        'datetime', 'time', 'typing', 'abc', 'enum', 'dataclasses',
        'contextlib', 'textwrap', 'string', 'glob', 'fnmatch',
        'hashlib', 'hmac', 'secrets', 'logging', 'warnings',
        'traceback', 'inspect', 'importlib', 'pkgutil',
        'http', 'urllib', 'socket', 'ssl', 'email',
        'csv', 'configparser', 'xml', 'html',
        'threading', 'multiprocessing', 'concurrent',
        'ast', 'dis', 'token', 'tokenize',
        'pprint', 'difflib', 'struct', 'codecs',
        'signal', 'errno', 'stat', 'posixpath', 'ntpath',
        'platform', 'locale', 'gettext',
    }

    try:
        with open(test_file_path, 'r') as f:
            source = f.read()
    except (IOError, OSError):
        return set()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split('.')[0]
                if top not in EXCLUDED_MODULES:
                    modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split('.')[0]
                if top not in EXCLUDED_MODULES:
                    modules.add(node.module)
                    # Also resolve 'from X import Y' as potential submodule X.Y
                    for alias in node.names:
                        submod = f"{node.module}.{alias.name}"
                        modules.add(submod)

    # Resolve module names to file paths
    resolved = set()
    for mod in modules:
        # Convert dotted module to path: tools.critic.critic -> tools/critic/critic
        mod_path = mod.replace('.', '/')
        # Check for .py file
        if os.path.isfile(mod_path + '.py'):
            resolved.add(mod_path + '.py')
        elif os.path.isdir(mod_path):
            resolved.add(mod_path)
        else:
            # Try relative to test file's directory
            test_dir = os.path.dirname(test_file_path)
            rel_path = os.path.join(test_dir, mod_path)
            if os.path.isfile(rel_path + '.py'):
                resolved.add(os.path.relpath(rel_path + '.py'))
            elif os.path.isdir(rel_path):
                resolved.add(os.path.relpath(rel_path))
            else:
                # Keep the dotted path as-is for matching purposes
                resolved.add(mod_path)

    return resolved


def get_shell_test_surface(test_file_path):
    """Use directory proximity for shell test files.

    Returns set of non-test file paths in the test file's parent directory.
    """
    test_dir = os.path.dirname(test_file_path)
    if not os.path.isdir(test_dir):
        return set()

    surface = set()
    for entry in os.listdir(test_dir):
        full = os.path.join(test_dir, entry)
        if os.path.isfile(full) and not os.path.basename(entry).startswith('test_'):
            surface.add(os.path.relpath(full))
    return surface


def get_feature_implementation_surface(feature_stem, project_root):
    """Get the implementation surface for a feature from its tests.json.

    Returns (set of source file paths, bool: had_test_data).
    """
    tests_json_path = os.path.join(project_root, 'tests', feature_stem, 'tests.json')
    try:
        with open(tests_json_path, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return set(), False

    # Extract test file paths
    test_files = []
    if 'test_file' in data:
        test_files.append(data['test_file'])
    if 'test_files' in data:
        test_files.extend(data['test_files'])

    if not test_files:
        return set(), False

    surface = set()
    for tf in test_files:
        # Resolve relative to project root
        tf_abs = os.path.join(project_root, tf) if not os.path.isabs(tf) else tf
        if tf.endswith('.py'):
            surface |= extract_python_imports(tf_abs)
        elif tf.endswith(('.sh', '.bats')):
            surface |= get_shell_test_surface(tf_abs)

    return surface, True


def detect_git_coupling(stem_a, stem_b, project_root):
    """Detect coupling via git commit file overlap (Tier 3).

    Returns (set of shared files, bool: had_git_data).
    """
    def get_files_for_stem(stem):
        """Find files modified in commits matching feat(<stem>)."""
        try:
            result = subprocess.run(
                ['git', 'log', '--all', '--pretty=format:%H',
                 f'--grep=feat({stem})', '--'],
                capture_output=True, text=True, cwd=project_root
            )
            if result.returncode != 0 or not result.stdout.strip():
                return set(), False

            commits = result.stdout.strip().split('\n')
            files = set()
            for commit_hash in commits:
                diff_result = subprocess.run(
                    ['git', 'diff-tree', '--no-commit-id', '-r', '--name-only', commit_hash],
                    capture_output=True, text=True, cwd=project_root
                )
                if diff_result.returncode == 0 and diff_result.stdout.strip():
                    files |= set(diff_result.stdout.strip().split('\n'))
            return files, True
        except (OSError, FileNotFoundError):
            return set(), False

    files_a, had_a = get_files_for_stem(stem_a)
    files_b, had_b = get_files_for_stem(stem_b)

    if not had_a and not had_b:
        return set(), False

    shared = files_a & files_b
    return shared, True


def detect_coupling_warnings(features, project_root):
    """Detect implementation coupling between spec-independent features.

    Implements the tiered detection system from Section 2.10:
    - Tier 2: Test file source imports
    - Tier 3: Git commit file overlap

    Tier 1 (spec dependencies) is handled by compute_feature_independence().
    This function only processes pairs that are already known to be spec-independent.

    Returns list of coupling warning dicts.
    """
    warnings = []

    # Extract feature stems from bare filenames
    stems = {}
    for feat in features:
        bare = os.path.basename(feat) if '/' in feat else feat
        stem = bare.replace('.md', '')
        stems[bare] = stem

    # Get implementation surfaces (Tier 2 data)
    surfaces = {}
    had_test_data = {}
    for bare, stem in stems.items():
        surface, had_data = get_feature_implementation_surface(stem, project_root)
        surfaces[bare] = surface
        had_test_data[bare] = had_data

    # Check all pairs
    feat_list = sorted(stems.keys())
    for i in range(len(feat_list)):
        for j in range(i + 1, len(feat_list)):
            fa, fb = feat_list[i], feat_list[j]
            stem_a, stem_b = stems[fa], stems[fb]

            # Tier 2: Test import overlap
            both_have_tests = had_test_data[fa] and had_test_data[fb]
            if both_have_tests:
                shared = surfaces[fa] & surfaces[fb]
                if shared:
                    # Tier 2 coupling detected — also check Tier 3 for context
                    git_shared, _ = detect_git_coupling(stem_a, stem_b, project_root)
                    # Report Tier 2 as primary signal
                    shared_list = sorted(shared)
                    warnings.append({
                        "features": [fa, fb],
                        "tier": 2,
                        "shared_files": shared_list,
                        "detail": (
                            f"test files for both features import from "
                            f"{', '.join(shared_list)}"
                        ),
                    })
                    continue
                else:
                    # Tier 2 says no coupling — skip Tier 3
                    continue

            # Tier 2 could not run (missing test data for one or both)
            # Fall through to Tier 3
            if not had_test_data[fa] and not had_test_data[fb]:
                # Neither has test data — try git
                git_shared, had_git = detect_git_coupling(stem_a, stem_b, project_root)
                if had_git and git_shared:
                    shared_list = sorted(git_shared)
                    warnings.append({
                        "features": [fa, fb],
                        "tier": 3,
                        "shared_files": shared_list,
                        "detail": (
                            f"git commits for both features modified "
                            f"{', '.join(shared_list)}"
                        ),
                    })
                # else: no data at all — no warning (no-data fallback)
                continue

            # One has test data, the other doesn't — Tier 2 can't compare
            # Try Tier 3
            git_shared, had_git = detect_git_coupling(stem_a, stem_b, project_root)
            if had_git and git_shared:
                shared_list = sorted(git_shared)
                warnings.append({
                    "features": [fa, fb],
                    "tier": 3,
                    "shared_files": shared_list,
                    "detail": (
                        f"git commits for both features modified "
                        f"{', '.join(shared_list)}"
                    ),
                })

    return warnings


def main():
    parser = argparse.ArgumentParser(description='Phase Analyzer')
    parser.add_argument(
        '--intra-phase', type=int, dest='intra_phase', default=None,
        help='Analyze feature independence within a specific phase'
    )
    args = parser.parse_args()

    project_root = _find_project_root()

    plan_path = os.path.join(project_root, '.purlin', 'delivery_plan.md')
    graph_path = os.path.join(project_root, '.purlin', 'cache', 'dependency_graph.json')

    # Validate inputs exist
    if not os.path.exists(plan_path):
        print("Error: delivery plan not found at .purlin/delivery_plan.md", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(graph_path):
        print("Error: dependency graph not found at .purlin/cache/dependency_graph.json", file=sys.stderr)
        sys.exit(1)

    # Read inputs
    try:
        with open(plan_path, 'r') as f:
            plan_text = f.read()
    except (IOError, OSError) as e:
        print(f"Error reading delivery plan: {e}", file=sys.stderr)
        sys.exit(1)

    # Intra-phase mode
    if args.intra_phase is not None:
        # Parse with PENDING and IN_PROGRESS statuses
        all_phases = parse_delivery_plan(
            plan_text, include_statuses={'PENDING', 'IN_PROGRESS'}
        )
        target_phase = None
        for p in all_phases:
            if p["number"] == args.intra_phase:
                target_phase = p
                break

        if target_phase is None:
            print(
                f"Error: Phase {args.intra_phase} not found or is in COMPLETE status",
                file=sys.stderr
            )
            sys.exit(1)

        all_deps = load_dependency_graph(graph_path)
        closure = build_transitive_closure(all_deps)
        parallel_groups = compute_feature_independence(
            target_phase["features"], closure
        )

        # Detect implementation coupling for spec-independent features
        # Only check pairs that are in parallel groups
        independent_features = []
        for group in parallel_groups:
            if group["parallel"] and len(group["features"]) >= 2:
                independent_features.extend(group["features"])

        coupling_warnings = []
        if independent_features:
            coupling_warnings = detect_coupling_warnings(
                independent_features, project_root
            )

        result = {
            "phase": target_phase["number"],
            "features": sorted(target_phase["features"]),
            "parallel_groups": parallel_groups,
            "coupling_warnings": coupling_warnings,
        }
        json.dump(result, sys.stdout, indent=2)
        print()
        sys.exit(0)

    # Default mode: inter-phase analysis
    phases = parse_delivery_plan(plan_text)

    if not phases:
        # No PENDING phases
        result = {
            "groups": [],
            "reordered": False,
            "original_order": [],
            "warnings": [],
        }
        json.dump(result, sys.stdout, indent=2)
        print()
        sys.exit(0)

    # Load dependency graph
    all_deps = load_dependency_graph(graph_path)

    # Build transitive closure
    closure = build_transitive_closure(all_deps)

    # Compute inter-phase dependencies
    phase_deps, dep_warnings = compute_phase_dependencies(phases, closure, all_deps)

    # Topological sort
    original_order = [p["number"] for p in phases]
    sorted_order, reordered, ordering_warnings = topological_sort(phases, phase_deps)

    # Group parallel phases
    groups = group_parallel_phases(sorted_order, phase_deps)

    # Combine warnings
    all_warnings = dep_warnings + ordering_warnings

    # Emit diagnostics to stderr
    for w in all_warnings:
        print(f"Warning: {w}", file=sys.stderr)

    # Output result
    result = {
        "groups": groups,
        "reordered": reordered,
        "original_order": original_order,
        "warnings": all_warnings,
    }
    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == '__main__':
    main()
