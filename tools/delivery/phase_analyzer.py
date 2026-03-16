#!/usr/bin/env python3
"""Phase Analyzer — dependency-aware delivery plan analysis.

Reads the delivery plan and dependency graph to determine correct phase
execution order and identify parallelization opportunities. Output is
structured JSON to stdout, suitable for consumption by the continuous
phase builder orchestration loop.

Usage:
    python3 tools/delivery/phase_analyzer.py

Environment:
    PURLIN_PROJECT_ROOT — project root override (submodule-safe)
"""

import json
import os
import re
import sys
from collections import defaultdict


def _find_project_root(start_dir=None):
    """Detect project root using PURLIN_PROJECT_ROOT or climbing fallback."""
    env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if env_root and os.path.isdir(env_root):
        return env_root

    if start_dir is None:
        start_dir = os.path.dirname(os.path.abspath(__file__))

    for depth in ('../../../', '../../'):
        candidate = os.path.abspath(os.path.join(start_dir, depth))
        if os.path.exists(os.path.join(candidate, '.purlin')):
            return candidate

    return os.path.abspath(os.path.join(start_dir, '../../'))


def parse_delivery_plan(plan_text):
    """Extract phases from delivery plan markdown.

    Returns list of dicts: [{"number": int, "status": str, "features": [str], "label": str}]
    Only PENDING phases are included.
    """
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

        if status == 'PENDING':
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


def main():
    project_root = _find_project_root()

    plan_path = os.path.join(project_root, '.purlin', 'cache', 'delivery_plan.md')
    graph_path = os.path.join(project_root, '.purlin', 'cache', 'dependency_graph.json')

    # Validate inputs exist
    if not os.path.exists(plan_path):
        print("Error: delivery plan not found at .purlin/cache/delivery_plan.md", file=sys.stderr)
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

    # Parse delivery plan
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
