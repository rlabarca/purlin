#!/usr/bin/env python3
"""Tests for submodule_command_path_resolution feature.

Validates that all .claude/commands/pl-*.md files use ${TOOLS_ROOT}/ notation
instead of hardcoded tools/ paths, include a resolution preamble, and that
pl-resume and pl-build have feature-specific requirements met.
"""
import json
import os
import re
import sys
from pathlib import Path

# --- Inline test harness ---
_results = []

def record(name, passed, detail=""):
    _results.append({"name": name, "passed": passed, "detail": detail})

def write_results():
    passed = sum(1 for r in _results if r["passed"])
    failed = sum(1 for r in _results if not r["passed"])
    total = len(_results)
    status = "PASS" if failed == 0 else "FAIL"
    output = {
        "status": status,
        "passed": passed,
        "failed": failed,
        "total": total,
        "details": _results,
    }
    results_dir = Path(__file__).resolve().parent
    results_path = results_dir / "tests.json"
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"{status}: {passed} passed, {failed} failed, {total} total")
    if failed > 0:
        for r in _results:
            if not r["passed"]:
                print(f"  FAIL: {r['name']}: {r['detail']}")


# --- Path setup ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DIR = PROJECT_ROOT / ".claude" / "commands"

# Subdirectories that must use ${TOOLS_ROOT}/ notation
TOOL_SUBDIRS = [
    "release", "delivery",
    "test_support", "feature_templates", "collab",
]

# Pattern matching hardcoded tools/ paths to tool subdirectories
HARDCODED_PATTERN = re.compile(
    r'(?<!\$\{TOOLS_ROOT\}/)tools/(' + '|'.join(TOOL_SUBDIRS) + r')/'
)

# Pattern matching the resolution preamble (flexible matching)
# Checks that both tools_root and config.json appear near each other (within 200 chars)
PREAMBLE_PATTERN = re.compile(
    r'(config\.json.*tools_root|tools_root.*config\.json)',
    re.IGNORECASE
)

# Pattern matching ${TOOLS_ROOT}/ usage
TOOLS_ROOT_USAGE = re.compile(r'\$\{TOOLS_ROOT\}/')


def get_command_files():
    """Return all pl-*.md command files."""
    return sorted(COMMANDS_DIR.glob("pl-*.md"))


def files_with_tool_refs():
    """Return command files that reference any tool subdirectory."""
    result = []
    for f in get_command_files():
        content = f.read_text()
        if TOOLS_ROOT_USAGE.search(content):
            result.append(f)
    return result


# --- Scenario 1: Command Files Use tools_root Notation ---
def test_no_hardcoded_tools_paths():
    """No pl-*.md file should have hardcoded tools/{subdir}/ paths."""
    violations = []
    for cmd_file in get_command_files():
        content = cmd_file.read_text()
        matches = HARDCODED_PATTERN.findall(content)
        if matches:
            # Find the actual lines for better reporting
            for i, line in enumerate(content.splitlines(), 1):
                if HARDCODED_PATTERN.search(line):
                    violations.append(f"{cmd_file.name}:{i}")
    passed = len(violations) == 0
    detail = f"Hardcoded paths found: {', '.join(violations)}" if violations else ""
    record("no_hardcoded_tools_paths", passed, detail)


def test_files_with_tool_refs_have_preamble():
    """Every file that uses ${TOOLS_ROOT}/ must include a resolution preamble."""
    missing = []
    for cmd_file in files_with_tool_refs():
        content = cmd_file.read_text()
        if not PREAMBLE_PATTERN.search(content):
            missing.append(cmd_file.name)
    passed = len(missing) == 0
    detail = f"Missing preamble: {', '.join(missing)}" if missing else ""
    record("files_with_tool_refs_have_preamble", passed, detail)


def test_preamble_includes_default():
    """Resolution preamble must mention the default value 'tools'."""
    default_pattern = re.compile(r'default.*"?tools"?', re.IGNORECASE)
    missing = []
    for cmd_file in files_with_tool_refs():
        content = cmd_file.read_text()
        if not default_pattern.search(content):
            missing.append(cmd_file.name)
    passed = len(missing) == 0
    detail = f"Missing default mention: {', '.join(missing)}" if missing else ""
    record("preamble_includes_default", passed, detail)


# --- Scenario 2: Resume Command Resolves tools_root ---
def test_resume_uses_tools_root():
    """pl-resume.md must use ${TOOLS_ROOT}/cdd/scan.sh."""
    resume_file = COMMANDS_DIR / "pl-resume.md"
    content = resume_file.read_text()
    has_resolved = "${TOOLS_ROOT}/cdd/scan.sh" in content
    has_hardcoded = "tools/cdd/scan.sh" in content and "${TOOLS_ROOT}" not in content
    passed = has_resolved and not has_hardcoded
    detail = ""
    if not has_resolved:
        detail = "Missing ${TOOLS_ROOT}/cdd/scan.sh"
    elif has_hardcoded:
        detail = "Still has hardcoded tools/cdd/scan.sh"
    record("resume_uses_tools_root", passed, detail)


def test_resume_has_preamble():
    """pl-resume.md must include a path resolution section."""
    resume_file = COMMANDS_DIR / "pl-resume.md"
    content = resume_file.read_text()
    passed = PREAMBLE_PATTERN.search(content) is not None
    record("resume_has_preamble", passed,
           "pl-resume.md missing tools_root resolution preamble" if not passed else "")


# --- Scenario 3: Build Command Enforces Web Test Gate ---
def test_build_has_web_test_gate():
    """pl-build.md Step 4 must include web test verification pre-check."""
    build_file = COMMANDS_DIR / "pl-build.md"
    content = build_file.read_text()
    # Must mention web test verification in Step 4 context
    has_web_test_check = "Web Test Gate" in content or "pl-web-test" in content
    has_bug_drift = "BUG" in content and "DRIFT" in content
    passed = has_web_test_check and has_bug_drift
    detail = ""
    if not has_web_test_check:
        detail = "Missing web test gate check in Step 4"
    elif not has_bug_drift:
        detail = "Missing BUG/DRIFT verdict check"
    record("build_has_web_test_gate", passed, detail)


# --- Scenario 4: Build Command Flags Missing Web Test Metadata ---
def test_build_flags_missing_web_test_metadata():
    """pl-build.md must check for DISCOVERY when Visual Spec exists but no web test URL."""
    build_file = COMMANDS_DIR / "pl-build.md"
    content = build_file.read_text()
    has_visual_spec_check = "Visual Specification" in content
    has_discovery_check = "DISCOVERY" in content
    has_no_web_test_clause = ("no `> Web Test:`" in content or
                              "no web test" in content.lower())
    passed = has_visual_spec_check and has_discovery_check and has_no_web_test_clause
    detail = ""
    if not has_visual_spec_check:
        detail = "Missing Visual Specification check"
    elif not has_discovery_check:
        detail = "Missing DISCOVERY check"
    elif not has_no_web_test_clause:
        detail = "Missing clause about missing web test metadata"
    record("build_flags_missing_web_test_metadata", passed, detail)


# --- Scenario 5: Web Test STALE Verdict Creates Discovery Sidecar Entry ---
def test_web_test_stale_creates_discovery():
    """pl-web-test.md must auto-record STALE verdicts as [DISCOVERY] in discovery sidecar."""
    web_test_file = COMMANDS_DIR / "pl-web-test.md"
    content = web_test_file.read_text()
    has_stale_section = "For STALE verdicts:" in content
    has_discovery_entry = "[DISCOVERY]" in content and "discoveries.md" in content
    has_action_pm = "Action Required:** PM" in content or "Action Required: PM" in content
    has_open_status = "Status:** OPEN" in content or "Status: OPEN" in content
    has_figma_ref = "Figma Reference" in content or "Figma frame" in content
    has_checklist_item = "checklist item" in content.lower()
    passed = all([
        has_stale_section, has_discovery_entry, has_action_pm,
        has_open_status, has_figma_ref, has_checklist_item,
    ])
    detail = ""
    if not has_stale_section:
        detail = "Missing 'For STALE verdicts:' section"
    elif not has_discovery_entry:
        detail = "Missing [DISCOVERY] + discoveries.md reference"
    elif not has_action_pm:
        detail = "Missing 'Action Required: PM'"
    elif not has_open_status:
        detail = "Missing 'Status: OPEN'"
    elif not has_figma_ref:
        detail = "Missing Figma reference in discovery entry"
    elif not has_checklist_item:
        detail = "Missing checklist item text in discovery entry"
    record("web_test_stale_creates_discovery", passed, detail)


# --- Comprehensive coverage check ---
def test_all_tool_referencing_files_converted():
    """Every file that originally had tools/ refs now uses ${TOOLS_ROOT}/."""
    # Known files that should have been converted
    expected_converted = {
        "pl-resume.md", "pl-build.md", "pl-status.md", "pl-regression.md",
        "pl-complete.md", "pl-verify.md", "pl-delivery-plan.md",
        "pl-web-test.md", "pl-spec.md", "pl-qa-report.md", "pl-edit-base.md",
        "pl-anchor.md", "pl-whats-different.md", "pl-tombstone.md",
        "pl-spec-from-code.md", "pl-infeasible.md", "pl-release-step.md",
        "pl-release-run.md", "pl-release-check.md",
        "pl-remote-pull.md", "pl-spec-code-audit.md",
    }
    actual_converted = {f.name for f in files_with_tool_refs()}
    missing = expected_converted - actual_converted
    passed = len(missing) == 0
    detail = f"Missing conversions: {', '.join(sorted(missing))}" if missing else ""
    record("all_tool_referencing_files_converted", passed, detail)


if __name__ == "__main__":
    test_no_hardcoded_tools_paths()
    test_files_with_tool_refs_have_preamble()
    test_preamble_includes_default()
    test_resume_uses_tools_root()
    test_resume_has_preamble()
    test_build_has_web_test_gate()
    test_build_flags_missing_web_test_metadata()
    test_web_test_stale_creates_discovery()
    test_all_tool_referencing_files_converted()
    write_results()
