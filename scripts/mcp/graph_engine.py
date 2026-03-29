"""Dependency graph generation for the Purlin feature system.

Provides dependency graph generation, cycle detection, orphan detection,
Mermaid export, and JSON output. Used by the toolbox audit
(purlin.verify_dependency_integrity) and can also be run standalone.
"""
import os
import re
import sys
import json
from collections import defaultdict
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from bootstrap import detect_project_root
from invariant_engine import is_invariant_node

PROJECT_ROOT = detect_project_root(SCRIPT_DIR)

# Mermaid classDef requires inline hex colors (no CSS var support).
# Token map centralises values to satisfy design_visual_standards FORBIDDEN audit.
_MERMAID_TOKENS = {
    "default_fill": "e1f5fe", "default_stroke": "01579b",
    "release_fill": "f96",    "release_stroke": "333",
    "hardware_fill": "e8f5e9", "hardware_stroke": "2e7d32",
    "ui_fill": "f3e5f5",      "ui_stroke": "7b1fa2",
    "process_fill": "f1f8e9", "process_stroke": "558b2f",
    "invariant_fill": "fff3e0", "invariant_stroke": "e65100",
    "title_color": "111",
}

# Virtual category for global invariants — rendered as the first subgraph.
_GLOBAL_INVARIANTS_CATEGORY = "Global Invariants"

# Artifact isolation (Section 2.12): write outputs to .purlin/cache/
CACHE_DIR = os.path.join(PROJECT_ROOT, ".purlin", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
MMD_FILE = os.path.join(CACHE_DIR, "feature_graph.mmd")
DEPENDENCY_GRAPH_FILE = os.path.join(CACHE_DIR, "dependency_graph.json")
FEATURES_DIR = os.path.join(PROJECT_ROOT, "features")
README_FILE = os.path.join(PROJECT_ROOT, "README.md")


def parse_features(features_dir):
    """Parse all feature .md files in a directory, extracting metadata.

    Walks category subfolders recursively, skipping _-prefixed system
    folders.  Skips companion files (*.impl.md) -- only primary feature
    specs are included as graph nodes.

    Returns a dict keyed by node_id with feature metadata.
    """
    features = {}
    label_pattern = re.compile(r'^>\s*Label:\s*"(.*)"')
    category_pattern = re.compile(r'^>\s*Category:\s*"(.*)"')
    prereq_pattern = re.compile(r'^>\s*Prerequisite:\s*(.*)')
    scope_pattern = re.compile(r'^>\s*Scope:\s*(.*)')
    invariant_pattern = re.compile(r'^>\s*Invariant:\s*(.*)')

    if not os.path.exists(features_dir):
        return features

    # Walk category subfolders, skipping _-prefixed system folders
    # (except _invariants which contains graph-participating nodes).
    for dirpath, dirnames, filenames in os.walk(features_dir):
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith("_") or d == "_invariants"
        ]
        for filename in sorted(filenames):
            if not filename.endswith(".md"):
                continue
            # Skip companion/implementation notes files and discovery sidecars
            if filename.endswith(".impl.md") or filename.endswith(
                    ".discoveries.md"):
                continue

            filepath = os.path.join(dirpath, filename)
            node_id = filename.replace(".md", "").replace(".", "_")

            feature_data = {
                "id": node_id,
                "filename": filename,
                "filepath": filepath,
                "label": filename,
                "category": "Uncategorized",
                "prerequisites": [],
            }

            # Detect invariant using validated prefix check.
            is_invariant = is_invariant_node(filename)
            if is_invariant:
                feature_data["invariant"] = True

            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    label_match = label_pattern.match(line)
                    if label_match:
                        feature_data["label"] = label_match.group(1)

                    cat_match = category_pattern.match(line)
                    if cat_match:
                        feature_data["category"] = cat_match.group(1)

                    prereq_match = prereq_pattern.match(line)
                    if prereq_match:
                        prereq_str = prereq_match.group(1)
                        prereq_files = [
                            p.strip() for p in prereq_str.split(',')]
                        for prereq_file in prereq_files:
                            # Extract the filename from potential paths
                            prereq_filename = os.path.basename(prereq_file)
                            if prereq_filename.endswith(".md"):
                                prereq_id = prereq_filename.replace(
                                    ".md", "").replace(".", "_")
                                feature_data["prerequisites"].append(
                                    prereq_id)

                    scope_match = scope_pattern.match(line)
                    if scope_match:
                        feature_data["scope"] = (
                            scope_match.group(1).strip().strip('"'))

                    inv_match = invariant_pattern.match(line)
                    if inv_match:
                        val = inv_match.group(1).strip().strip('"').lower()
                        if val == "true":
                            feature_data["invariant"] = True

            features[node_id] = feature_data
    return features


def detect_cycles(features):
    """DFS-based cycle detection. Returns list of cycle descriptions."""
    cycles = []
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node_id: WHITE for node_id in features}
    path = []

    def dfs(node_id):
        color[node_id] = GRAY
        path.append(node_id)
        for prereq_id in sorted(features[node_id]["prerequisites"]):
            if prereq_id not in features:
                continue
            if color[prereq_id] == GRAY:
                cycle_start = path.index(prereq_id)
                cycle_nodes = path[cycle_start:] + [prereq_id]
                cycle_files = [
                    features[n]["filename"]
                    for n in cycle_nodes if n in features
                ]
                cycles.append(" -> ".join(cycle_files))
            elif color[prereq_id] == WHITE:
                dfs(prereq_id)
        path.pop()
        color[node_id] = BLACK

    for node_id in sorted(features.keys()):
        if color[node_id] == WHITE:
            dfs(node_id)
    return cycles


def find_orphans(features):
    """Find features with no prerequisite links (root nodes)."""
    return sorted([
        features[node_id]["filename"]
        for node_id, data in features.items()
        if not data["prerequisites"]
    ])


def build_features_json(features, features_dir):
    """Build the JSON-serializable feature list for dependency_graph.json."""
    feature_list = []
    for node_id in sorted(features.keys()):
        data = features[node_id]
        prereq_files = sorted([
            features[p]["filename"] if p in features else p + ".md"
            for p in data["prerequisites"]
        ])
        entry = {
            "file": os.path.relpath(
                data.get("filepath", os.path.join(features_dir, data["filename"])),
                PROJECT_ROOT
            ),
            "label": data["label"],
            "category": data["category"],
            "prerequisites": prereq_files,
        }
        if data.get("invariant"):
            entry["invariant"] = True
        if "scope" in data:
            entry["scope"] = data["scope"]
        feature_list.append(entry)
    return feature_list


def generate_dependency_graph(features, features_dir=None, output_file=None):
    """Generate the canonical dependency_graph.json file (flat schema).

    Args:
        features: dict of parsed features from parse_features()
        features_dir: path to features directory (defaults to FEATURES_DIR)
        output_file: path to output JSON file (defaults to DEPENDENCY_GRAPH_FILE)

    Returns:
        The graph dict.
    """
    if features_dir is None:
        features_dir = FEATURES_DIR
    if output_file is None:
        output_file = DEPENDENCY_GRAPH_FILE

    all_cycles = detect_cycles(features)
    all_orphans = find_orphans(features)

    # Collect global invariants (scope == "global").
    global_invariants = sorted([
        os.path.relpath(
            os.path.join(features_dir, data["filename"]), PROJECT_ROOT
        )
        for data in features.values()
        if data.get("invariant") and data.get("scope") == "global"
    ])

    graph = {
        "generated_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "features": build_features_json(features, features_dir),
        "cycles": sorted(all_cycles),
        "global_invariants": global_invariants,
        "orphans": sorted(all_orphans),
    }

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(graph, f, indent=2, sort_keys=True)
    print(f"Updated {output_file}", file=sys.stderr)

    if all_cycles:
        print(f"\n*** WARNING: {len(all_cycles)} CYCLE(S) DETECTED ***",
              file=sys.stderr)
        for c in all_cycles:
            print(f"  CYCLE: {c}", file=sys.stderr)

    return graph


def generate_mermaid_content(features):
    """Generate Mermaid flowchart content from parsed features."""
    lines = ["flowchart TD"]
    lines.append("")

    grouped_categories = defaultdict(list)
    for node_id, data in features.items():
        # Global invariants get their own top-level category.
        if data.get("invariant") and data.get("scope") == "global":
            grouped_categories[_GLOBAL_INVARIANTS_CATEGORY].append(node_id)
        else:
            grouped_categories[data["category"]].append(node_id)

    style_apps = []

    # Sort categories but ensure Global Invariants renders first.
    sorted_categories = sorted(grouped_categories.items(),
                               key=lambda x: (x[0] != _GLOBAL_INVARIANTS_CATEGORY, x[0]))
    for category, node_ids in sorted_categories:
        category_id = category.replace(' ', '_').replace(':', '')
        lines.append(f'\n    subgraph {category_id} [" "]')

        title_id = f"title_{category_id}"
        lines.append(f'        {title_id}["{category.upper()}"]')
        style_apps.append(f"    class {title_id} subgraphTitle;")

        for node_id in sorted(node_ids):
            data = features[node_id]
            clean_label = data["label"].replace('"', "'")

            css_class = ""
            if data.get("invariant"):
                css_class = "invariant"
            elif "Release" in category:
                css_class = "release"
            elif "Hardware" in category:
                css_class = "hardware"
            elif "UI" in category:
                css_class = "ui"
            elif "Process" in category:
                css_class = "process"

            lines.append(
                f'        {node_id}'
                f'["{clean_label}<br/><small>{data["filename"]}</small>"]'
            )
            if css_class:
                style_apps.append(f"    class {node_id} {css_class};")

            lines.append(f'        {title_id} ~~~ {node_id}')
        lines.append("    end")

    lines.append("\n    %% Relationships")
    for node_id in sorted(features.keys()):
        data = features[node_id]
        for prereq_id in data["prerequisites"]:
            if prereq_id in features:
                lines.append(f"    {prereq_id} --> {node_id}")
            else:
                lines.append(
                    f'    {prereq_id}["{prereq_id}?"] -.-> {node_id}')

    lines.append("\n    %% Styling Definitions")
    t = _MERMAID_TOKENS
    lines.append(
        f"    classDef default "
        f"fill:#{t['default_fill']},stroke:#{t['default_stroke']},"
        f"stroke-width:1px,color:black;")
    lines.append(
        f"    classDef release "
        f"fill:#{t['release_fill']},stroke:#{t['release_stroke']},"
        f"stroke-width:2px,color:black,font-weight:bold;")
    lines.append(
        f"    classDef hardware "
        f"fill:#{t['hardware_fill']},stroke:#{t['hardware_stroke']},"
        f"stroke-width:1px,color:black;")
    lines.append(
        f"    classDef ui "
        f"fill:#{t['ui_fill']},stroke:#{t['ui_stroke']},"
        f"stroke-width:1px,color:black;")
    lines.append(
        f"    classDef process "
        f"fill:#{t['process_fill']},stroke:#{t['process_stroke']},"
        f"stroke-width:1px,color:black;")
    lines.append(
        f"    classDef invariant "
        f"fill:#{t['invariant_fill']},stroke:#{t['invariant_stroke']},"
        f"stroke-width:2px,color:black,stroke-dasharray:5 3;")
    lines.append(
        f"    classDef subgraphTitle "
        f"fill:none,stroke:none,color:#{t['title_color']},"
        f"font-size:32px,font-weight:bold;")

    lines.append("\n    %% Style Applications")
    lines.extend(style_apps)

    return "\n".join(lines)


def update_mermaid_outputs(features_dir=None, mmd_file=None):
    """Update Mermaid file and README with new graphs.

    Args:
        features_dir: path to features directory (defaults to FEATURES_DIR)
        mmd_file: path to Mermaid output file (defaults to MMD_FILE)
    """
    if features_dir is None:
        features_dir = FEATURES_DIR
    if mmd_file is None:
        mmd_file = MMD_FILE

    features = parse_features(features_dir)
    mmd_content = generate_mermaid_content(features)

    if os.path.dirname(mmd_file) and not os.path.exists(
            os.path.dirname(mmd_file)):
        os.makedirs(os.path.dirname(mmd_file))

    with open(mmd_file, 'w', encoding='utf-8') as f:
        f.write(mmd_content)
    print(f"Updated {mmd_file}", file=sys.stderr)

    _update_readme(mmd_content)


def _update_readme(mmd_content):
    """Update README.md with Mermaid graph if markers exist."""
    if os.path.exists(README_FILE):
        with open(README_FILE, 'r', encoding='utf-8') as f:
            readme_content = f.read()

        start_marker = "<!-- MERMAID_START -->"
        end_marker = "<!-- MERMAID_END -->"
        new_block = (
            f"{start_marker}\n```mermaid\n{mmd_content}\n```\n{end_marker}")
        pattern = re.compile(
            f"{re.escape(start_marker)}.*?{re.escape(end_marker)}", re.DOTALL)

        if pattern.search(readme_content):
            new_readme_content = pattern.sub(new_block, readme_content)
            if new_readme_content != readme_content:
                with open(README_FILE, 'w', encoding='utf-8') as f:
                    f.write(new_readme_content)
                print("Updated README.md with Mermaid graph.",
                      file=sys.stderr)


def run_full_generation(features_dir=None, output_file=None, mmd_file=None):
    """Run complete graph generation: JSON + Mermaid + README.

    This is the main entry point called by the file watcher and CLI.
    JSON generation runs first (critical for web UI); Mermaid/README
    failures must not block JSON output.

    Returns the generated graph dict or None on failure.
    """
    if features_dir is None:
        features_dir = FEATURES_DIR

    features = parse_features(features_dir)
    # Generate dependency_graph.json first (critical: web UI depends on this)
    graph = generate_dependency_graph(features, features_dir, output_file)
    # Update Mermaid/README (non-critical for web UI; failures must not block)
    try:
        update_mermaid_outputs(features_dir, mmd_file)
    except Exception as e:
        print(f"Warning: Mermaid/README update failed: {e}", file=sys.stderr)
    return graph


if __name__ == "__main__":
    run_full_generation()
