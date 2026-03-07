#!/usr/bin/env python3
"""Release audit: submodule safety contract checks.

Checks 7 categories of submodule safety violations in Python tools.
See features/release_audit_automation.md Section 2.6.
"""
import ast
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


def main(project_root=None):
    if project_root is None:
        project_root = detect_project_root(SCRIPT_DIR)

    py_files = find_python_tools(project_root)
    findings = []

    for filepath in py_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, OSError):
            continue

        findings.extend(check_env_var(filepath, content, project_root))
        findings.extend(check_artifact_write_location(filepath, content, project_root))
        findings.extend(check_unguarded_json_load(filepath, content, project_root))
        findings.extend(check_cwd_relative(filepath, content, project_root))

    result = make_output("submodule_safety_audit", findings)
    return result


if __name__ == "__main__":
    output_and_exit(main())
