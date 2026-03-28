#!/usr/bin/env python3
"""Release audit: submodule safety contract checks.

Checks 8 categories of submodule safety violations per
features/release_submodule_safety_audit.md Section 2.2.
"""
import ast
import glob as globmod
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_framework_root = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
if _framework_root not in sys.path:
    sys.path.insert(0, _framework_root)

from tools.release.audit_common import (
    detect_project_root, make_finding, make_output, output_and_exit,
)


def find_python_tools(project_root):
    """Find all Python files under tools/ (excluding __pycache__, test files)."""
    tools_dir = os.path.join(project_root, "tools")
    py_files = []
    if not os.path.isdir(tools_dir):
        return py_files
    for dirpath, dirnames, filenames in os.walk(tools_dir):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fname in filenames:
            if fname.endswith(".py") and not fname.startswith("test_"):
                py_files.append(os.path.join(dirpath, fname))
    return sorted(py_files)


def check_env_var(filepath, content, project_root):
    """Category 1: Check for PURLIN_PROJECT_ROOT usage."""
    findings = []
    rel = os.path.relpath(filepath, project_root)

    # Skip files that don't do project root detection at all
    if "PROJECT_ROOT" not in content and "project_root" not in content:
        return findings

    # Files that reference project root should check env var
    if "PURLIN_PROJECT_ROOT" not in content:
        # Check if it does directory climbing without env var
        if "os.path.abspath" in content and ("../" in content or "os.path.join" in content):
            findings.append(make_finding(
                "CRITICAL", "missing_env_check", rel,
                "Python tool performs directory climbing without checking "
                "PURLIN_PROJECT_ROOT first",
            ))
    return findings


def check_artifact_write_location(filepath, content, project_root):
    """Category 3: Check for file writes inside tools/."""
    findings = []
    rel = os.path.relpath(filepath, project_root)

    artifact_exts = ('.pid', '.log')
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        # Detect path construction using SCRIPT_DIR with artifact extensions
        if 'SCRIPT_DIR' in stripped or "'tools/" in stripped or '"tools/' in stripped:
            if any(ext in stripped for ext in artifact_exts):
                findings.append(make_finding(
                    "CRITICAL", "artifact_in_tools", rel,
                    f"Script constructs artifact path inside tools/ (line {i})",
                    line=i,
                ))
    return findings


def check_unguarded_json_load(filepath, content, project_root):
    """Category 4: Check for bare json.load() without try/except."""
    findings = []
    rel = os.path.relpath(filepath, project_root)

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return findings

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # Match json.load() or json.loads()
        func = node.func
        is_json_load = False
        if isinstance(func, ast.Attribute):
            if func.attr in ('load', 'loads'):
                if isinstance(func.value, ast.Name) and func.value.id == 'json':
                    is_json_load = True

        if not is_json_load:
            continue

        # Walk up to check if inside try/except
        # Simple approach: check if the line is inside a Try block
        line = node.lineno
        in_try = False
        for parent in ast.walk(tree):
            if isinstance(parent, ast.Try):
                if any(
                    getattr(child, 'lineno', 0) == line
                    for child in ast.walk(parent)
                    if child is not parent
                ):
                    in_try = True
                    break

        if not in_try:
            findings.append(make_finding(
                "WARNING", "unguarded_json_load", rel,
                f"json.load() without try/except on line {line}",
                line=line,
            ))
    return findings


def check_cwd_relative(filepath, content, project_root):
    """Category 5: Check for os.getcwd() usage."""
    findings = []
    rel = os.path.relpath(filepath, project_root)

    if "os.getcwd()" in content:
        for i, line in enumerate(content.split('\n'), 1):
            if "os.getcwd()" in line and not line.strip().startswith('#'):
                findings.append(make_finding(
                    "WARNING", "cwd_relative", rel,
                    f"Uses os.getcwd() which may resolve incorrectly in "
                    f"submodule context (line {i})",
                    line=i,
                ))
    return findings


def find_shell_scripts(project_root):
    """Find all shell scripts under tools/ (excluding test files)."""
    tools_dir = os.path.join(project_root, "tools")
    sh_files = []
    if not os.path.isdir(tools_dir):
        return sh_files
    for dirpath, dirnames, filenames in os.walk(tools_dir):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fname in filenames:
            if fname.endswith(".sh") and not fname.startswith("test_"):
                sh_files.append(os.path.join(dirpath, fname))
    return sorted(sh_files)


def find_instruction_files(project_root):
    """Find all markdown files under instructions/."""
    inst_dir = os.path.join(project_root, "instructions")
    md_files = []
    if not os.path.isdir(inst_dir):
        return md_files
    for fname in os.listdir(inst_dir):
        if fname.endswith('.md'):
            md_files.append(os.path.join(inst_dir, fname))
    return sorted(md_files)


def check_climbing_priority(filepath, content, project_root):
    """Category 2: Check that climbing order tries FURTHER path first."""
    findings = []
    rel = os.path.relpath(filepath, project_root)

    # Look for climbing patterns with ../../ (nearer) and ../../../ (further)
    # The correct order is further first, then nearer
    lines = content.split('\n')
    nearer_line = None
    further_line = None

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        # Detect climbing path patterns
        if "'../../'" in stripped or '"../../"' in stripped or "'..'," in stripped:
            if "'../../../'" not in stripped and '"../../../"' not in stripped:
                if nearer_line is None:
                    nearer_line = i
        if "'../../../'" in stripped or '"../../../"' in stripped:
            if further_line is None:
                further_line = i

    # If both patterns found and nearer comes before further, it's reversed
    if nearer_line is not None and further_line is not None:
        if nearer_line < further_line:
            findings.append(make_finding(
                "CRITICAL", "climbing_priority_reversed", rel,
                f"Nearer path (../../) checked on line {nearer_line} before "
                f"further path (../../../) on line {further_line}",
                line=nearer_line,
            ))

        # Nested-project disambiguation: when both climbing depths exist,
        # the code must check <nearer>/.git type (isdir vs file) to
        # distinguish a standalone repo from a submodule.
        has_git_check = '.git' in content and (
            'isdir' in content or 'isfile' in content
        )
        if not has_git_check:
            findings.append(make_finding(
                "CRITICAL", "missing_git_disambiguation", rel,
                "Climbing fallback uses both nearer and further paths but "
                "does not check .git type for nested-project disambiguation",
            ))

    return findings


def check_sed_json_safety(filepath, content, project_root):
    """Category 6: Check sed commands on JSON files for structural safety."""
    findings = []
    rel = os.path.relpath(filepath, project_root)

    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        # Detect sed operating on .json files
        if 'sed' in stripped and '.json' in stripped:
            # Check for risky patterns that could strip structural characters
            if re.search(r'sed\s+.*[{}[\],]', stripped):
                findings.append(make_finding(
                    "CRITICAL", "sed_json_structural_risk", rel,
                    f"sed command on JSON file may strip structural "
                    f"characters (line {i})",
                    line=i,
                ))
            else:
                # Check for validation step within next 5 lines
                has_validation = False
                for j in range(i, min(i + 5, len(lines))):
                    if 'json.load' in lines[j] or 'python3' in lines[j]:
                        has_validation = True
                        break
                if not has_validation:
                    findings.append(make_finding(
                        "WARNING", "sed_json_no_validation", rel,
                        f"sed command on JSON file without subsequent "
                        f"json.load validation (line {i})",
                        line=i,
                    ))
    return findings


def check_instruction_path_awareness(filepath, content, project_root):
    """Category 7: Check instruction files for unqualified tools/ references."""
    findings = []
    rel = os.path.relpath(filepath, project_root)

    # Check if file has a Path Resolution header
    has_path_resolution = 'tools_root' in content or 'Path Resolution' in content

    if has_path_resolution:
        return findings

    # Scan for tools/ references
    for i, line in enumerate(content.split('\n'), 1):
        if 'tools/' in line and not line.strip().startswith('#'):
            findings.append(make_finding(
                "WARNING", "unqualified_tools_ref", rel,
                f"References 'tools/' without tools_root context (line {i})",
                line=i,
            ))
            break  # One finding per file is sufficient

    return findings


def check_gitignore_template(project_root):
    """Category 8: Check gitignore template completeness."""
    findings = []

    template_path = os.path.join(
        project_root, "purlin-config-sample", "gitignore.purlin"
    )
    init_path = os.path.join(project_root, "tools", "init.sh")

    # 8b: Template file existence and core patterns
    CORE_PATTERNS = [
        '.purlin/cache/',
        '.purlin/runtime/',
        '.purlin/config.local.json',
    ]

    if not os.path.exists(template_path):
        findings.append(make_finding(
            "CRITICAL", "gitignore_template_missing",
            "purlin-config-sample/gitignore.purlin",
            "Gitignore template file is missing",
        ))
        return findings

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
    except (IOError, OSError):
        findings.append(make_finding(
            "CRITICAL", "gitignore_template_unreadable",
            "purlin-config-sample/gitignore.purlin",
            "Gitignore template file cannot be read",
        ))
        return findings

    for pattern in CORE_PATTERNS:
        if pattern not in template_content:
            findings.append(make_finding(
                "WARNING", "gitignore_core_pattern_missing",
                "purlin-config-sample/gitignore.purlin",
                f"Core pattern '{pattern}' not found in template",
            ))

    # 8c: init.sh reads from template (not hardcoded array)
    if os.path.exists(init_path):
        try:
            with open(init_path, 'r', encoding='utf-8') as f:
                init_content = f.read()
        except (IOError, OSError):
            init_content = ""

        if 'gitignore.purlin' not in init_content:
            findings.append(make_finding(
                "CRITICAL", "gitignore_hardcoded_array",
                "tools/init.sh",
                "init.sh does not read from gitignore.purlin template",
            ))

        # Check refresh mode performs additive merge
        if 'RECOMMENDED_IGNORES' in init_content:
            findings.append(make_finding(
                "CRITICAL", "gitignore_hardcoded_array",
                "tools/init.sh",
                "init.sh uses hardcoded RECOMMENDED_IGNORES array "
                "instead of reading gitignore.purlin",
            ))

        # 8c: Check refresh mode doesn't skip gitignore
        # Look for the refresh section and verify it includes gitignore handling
        refresh_marker = False
        has_gitignore_in_refresh = False
        for line in init_content.split('\n'):
            if 'refresh' in line.lower() and ('mode' in line.lower() or 'already' in line.lower()):
                refresh_marker = True
            if refresh_marker and 'gitignore' in line.lower():
                has_gitignore_in_refresh = True
                break

        if os.path.exists(init_path) and not has_gitignore_in_refresh:
            findings.append(make_finding(
                "CRITICAL", "gitignore_refresh_skip",
                "tools/init.sh",
                "init.sh refresh mode does not perform gitignore sync",
            ))

    # 8a: Scan for file write operations and check gitignore coverage
    tools_dir = os.path.join(project_root, "tools")
    if os.path.isdir(tools_dir):
        write_targets = set()
        for dirpath, dirnames, filenames in os.walk(tools_dir):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fname in filenames:
                if not (fname.endswith('.py') or fname.endswith('.sh')):
                    continue
                if fname.startswith('test_'):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        fcontent = f.read()
                except (IOError, OSError):
                    continue

                # Detect Python file write targets
                if fname.endswith('.py'):
                    for match in re.finditer(
                        r'open\([^)]*["\']([^"\']+)["\'][^)]*["\']w["\']',
                        fcontent
                    ):
                        target = match.group(1)
                        if not target.startswith(('/', '.purlin/', 'tests/')):
                            write_targets.add(target)

        # Check uncovered write targets against gitignore patterns
        for target in sorted(write_targets):
            # Skip if covered by a directory pattern
            covered = False
            for pattern in CORE_PATTERNS:
                if pattern.endswith('/') and target.startswith(pattern):
                    covered = True
                    break
                if '*' in pattern:
                    # Simple glob matching
                    import fnmatch
                    if fnmatch.fnmatch(target, pattern):
                        covered = True
                        break
                if target == pattern:
                    covered = True
                    break
            if target in template_content:
                covered = True
            if not covered:
                findings.append(make_finding(
                    "WARNING", "gitignore_uncovered_artifact",
                    target,
                    f"Generated artifact '{target}' not covered by "
                    f"gitignore template",
                ))

    return findings


def main(project_root=None):
    if project_root is None:
        project_root = detect_project_root(SCRIPT_DIR)

    py_files = find_python_tools(project_root)
    sh_files = find_shell_scripts(project_root)
    instruction_files = find_instruction_files(project_root)
    findings = []

    # Python tool checks (Categories 1-5)
    for filepath in py_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, OSError):
            continue

        findings.extend(check_env_var(filepath, content, project_root))
        findings.extend(check_climbing_priority(filepath, content, project_root))
        findings.extend(check_artifact_write_location(filepath, content, project_root))
        findings.extend(check_unguarded_json_load(filepath, content, project_root))
        findings.extend(check_cwd_relative(filepath, content, project_root))

    # Shell script checks (Category 6)
    for filepath in sh_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, OSError):
            continue

        findings.extend(check_sed_json_safety(filepath, content, project_root))

    # Instruction file checks (Category 7)
    for filepath in instruction_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, OSError):
            continue

        findings.extend(check_instruction_path_awareness(filepath, content, project_root))

    # Gitignore template checks (Category 8)
    findings.extend(check_gitignore_template(project_root))

    result = make_output("submodule_safety_audit", findings)
    return result


if __name__ == "__main__":
    output_and_exit(main())
