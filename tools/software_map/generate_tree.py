#!/usr/bin/env python3
import os
import re
import sys
import json
from collections import defaultdict
from datetime import datetime, timezone

# Robust ROOT_DIR discovery
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

# If we are embedded in another project, the root might be further up
if not os.path.exists(os.path.join(PROJECT_ROOT, ".agentic_devops")):
    # Try one level up (standard embedded structure)
    PARENT_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, "../"))
    if os.path.exists(os.path.join(PARENT_ROOT, ".agentic_devops")):
        PROJECT_ROOT = PARENT_ROOT

ROOT_DIR = PROJECT_ROOT # Using ROOT_DIR alias for consistency with rest of script
CORE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
MMD_FILE_APP = os.path.join(TOOL_DIR, "feature_graph_app.mmd")
MMD_FILE_AGENTIC = os.path.join(TOOL_DIR, "feature_graph_agentic.mmd")
DEPENDENCY_GRAPH_FILE = os.path.join(TOOL_DIR, "dependency_graph.json")
FEATURES_DIR_APP = os.path.join(ROOT_DIR, "features")
FEATURES_DIR_AGENTIC = os.path.join(CORE_DIR, "features")
README_FILE = os.path.join(ROOT_DIR, "README.md")

def parse_features(features_dir):
    features = {}
    label_pattern = re.compile(r'^>\s*Label:\s*"(.*)"')
    category_pattern = re.compile(r'^>\s*Category:\s*"(.*)"')
    prereq_pattern = re.compile(r'^>\s*Prerequisite:\s*(.*)')
    
    if not os.path.exists(features_dir):
        return features

    for filename in os.listdir(features_dir):
        if not filename.endswith(".md"):
            continue
            
        filepath = os.path.join(features_dir, filename)
        node_id = filename.replace(".md", "").replace(".", "_")
        
        feature_data = {
            "id": node_id,
            "filename": filename,
            "label": filename,
            "category": "Uncategorized",
            "prerequisites": []
        }
        
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
                    prereq_files = [p.strip() for p in prereq_str.split(',')]
                    for prereq_file in prereq_files:
                        # Extract the filename from potential paths
                        prereq_filename = os.path.basename(prereq_file)
                        if prereq_filename.endswith(".md"):
                            prereq_id = prereq_filename.replace(".md", "").replace(".", "_")
                            feature_data["prerequisites"].append(prereq_id)
        
        features[node_id] = feature_data
    return features

def generate_mermaid_content(features):
    lines = ["flowchart TD"]
    lines.append("")

    grouped_categories = defaultdict(list)
    for node_id, data in features.items():
        grouped_categories[data["category"]].append(node_id)
    
    style_apps = []

    for category, node_ids in sorted(grouped_categories.items()):
        category_id = category.replace(' ', '_').replace(':', '')
        lines.append(f'\n    subgraph {category_id} [" "]')
        
        title_id = f"title_{category_id}"
        lines.append(f'        {title_id}["{category.upper()}"]')
        style_apps.append(f"    class {title_id} subgraphTitle;")
        
        for node_id in sorted(node_ids):
            data = features[node_id]
            clean_label = data["label"].replace('"', "'")
            
            css_class = ""
            if "Release" in category: css_class = "release"
            elif "Hardware" in category: css_class = "hardware"
            elif "UI" in category: css_class = "ui"
            elif "Process" in category: css_class = "process"
            
            lines.append(f'        {node_id}["{clean_label}<br/><small>{data["filename"]}</small>"]')
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
                lines.append(f'    {prereq_id}["{prereq_id}?"] -.-> {node_id}')
    
    lines.append("\n    %% Styling Definitions")
    lines.append("    classDef default fill:#e1f5fe,stroke:#01579b,stroke-width:1px,color:black;")
    lines.append("    classDef release fill:#f96,stroke:#333,stroke-width:2px,color:black,font-weight:bold;")
    lines.append("    classDef hardware fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px,color:black;")
    lines.append("    classDef ui fill:#f3e5f5,stroke:#7b1fa2,stroke-width:1px,color:black;")
    lines.append("    classDef process fill:#f1f8e9,stroke:#558b2f,stroke-width:1px,color:black;")
    lines.append("    classDef subgraphTitle fill:none,stroke:none,color:#111,font-size:32px,font-weight:bold;")
    
    lines.append("\n    %% Style Applications")
    lines.extend(style_apps)
    
    return "\n".join(lines)

def generate_text_tree(features):
    output = ["# Project Feature Dependency Tree\n"]
    dependents = defaultdict(list)
    for node_id, data in features.items():
        for prereq in data["prerequisites"]:
            dependents[prereq].append(node_id)
            
    roots = [node_id for node_id, data in features.items() if not data["prerequisites"]]
    
    def print_node(node_id, depth=0, visited=None):
        if visited is None: visited = set()
        if node_id in visited: return # Avoid infinite loops
        visited.add(node_id)
        
        data = features[node_id]
        indent = "  " * depth
        line = f"{indent}- [{data['label']}] ({data['filename']})"
        output.append(line)
        for dep in sorted(dependents[node_id]):
            if dep in features:
                print_node(dep, depth + 1, visited.copy())
                
    output.append("## Hierarchy")
    for root in sorted(roots):
        print_node(root)
        
    return "\n".join(output)

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
                cycle_files = [features[n]["filename"] for n in cycle_nodes if n in features]
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


def build_domain_json(features, features_dir):
    """Build the JSON-serializable domain entry for dependency_graph.json."""
    feature_list = []
    for node_id in sorted(features.keys()):
        data = features[node_id]
        prereq_files = sorted([
            features[p]["filename"] if p in features else p + ".md"
            for p in data["prerequisites"]
        ])
        feature_list.append({
            "file": os.path.relpath(
                os.path.join(features_dir, data["filename"]),
                ROOT_DIR
            ),
            "label": data["label"],
            "category": data["category"],
            "prerequisites": prereq_files
        })
    return {"features": feature_list}


def generate_dependency_graph(app_features, agentic_features):
    """Generate the canonical dependency_graph.json file."""
    all_features = {}
    all_features.update(app_features)
    all_features.update(agentic_features)

    all_cycles = detect_cycles(app_features) + detect_cycles(agentic_features)
    all_orphans = find_orphans(app_features) + find_orphans(agentic_features)

    graph = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "domains": {
            "application": build_domain_json(app_features, FEATURES_DIR_APP),
            "agentic": build_domain_json(agentic_features, FEATURES_DIR_AGENTIC)
        },
        "cycles": sorted(all_cycles),
        "orphans": sorted(all_orphans)
    }

    with open(DEPENDENCY_GRAPH_FILE, 'w', encoding='utf-8') as f:
        json.dump(graph, f, indent=2, sort_keys=True)
    print(f"Updated {DEPENDENCY_GRAPH_FILE}")

    if all_cycles:
        print(f"\n*** WARNING: {len(all_cycles)} CYCLE(S) DETECTED ***")
        for c in all_cycles:
            print(f"  CYCLE: {c}")

    return graph


def update_domain(features_dir, mmd_file, domain_name):
    features = parse_features(features_dir)
    mmd_content = generate_mermaid_content(features)
    text_tree = generate_text_tree(features)
    
    if os.path.dirname(mmd_file) and not os.path.exists(os.path.dirname(mmd_file)):
        os.makedirs(os.path.dirname(mmd_file))

    with open(mmd_file, 'w', encoding='utf-8') as f:
        f.write(mmd_content)
    print(f"Updated {mmd_file}")

    if domain_name == "Application":
        update_readme(mmd_content)
        
    print(f"\n{'='*40}")
    print(f"DEPENDENCY TREE FOR {domain_name}")
    print(f"{'='*40}")
    print(text_tree)
    print(f"{'='*40}")

def update_readme(mmd_content):
    if os.path.exists(README_FILE):
        with open(README_FILE, 'r', encoding='utf-8') as f:
            readme_content = f.read()
            
        start_marker = "<!-- MERMAID_START -->"
        end_marker = "<!-- MERMAID_END -->"
        new_block = f"{start_marker}\n```mermaid\n{mmd_content}\n```\n{end_marker}"
        pattern = re.compile(f"{re.escape(start_marker)}.*?{re.escape(end_marker)}", re.DOTALL)
        
        if pattern.search(readme_content):
            new_readme_content = pattern.sub(new_block, readme_content)
            if new_readme_content != readme_content:
                with open(README_FILE, 'w', encoding='utf-8') as f:
                    f.write(new_readme_content)
                print("Updated README.md with Mermaid graph.")

if __name__ == "__main__":
    app_features = parse_features(FEATURES_DIR_APP)
    agentic_features = parse_features(FEATURES_DIR_AGENTIC)

    update_domain(FEATURES_DIR_APP, MMD_FILE_APP, "Application")
    update_domain(FEATURES_DIR_AGENTIC, MMD_FILE_AGENTIC, "Agentic Core")
    generate_dependency_graph(app_features, agentic_features)
