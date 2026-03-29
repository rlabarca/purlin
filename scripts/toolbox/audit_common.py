"""Shared utilities for toolbox audit scripts.

Provides project root detection, JSON output formatting, and common helpers.
"""
import json
import os
import sys


_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_SCRIPT_DIR, '..', 'mcp')))
from bootstrap import detect_project_root


def make_finding(severity, category, file_path, message, line=None):
    """Create a structured finding dict."""
    return {
        "severity": severity,
        "category": category,
        "file": file_path,
        "line": line,
        "message": message,
    }


def make_output(step, findings, summary=None):
    """Create the standard audit output dict and determine status."""
    has_critical = any(f["severity"] == "CRITICAL" for f in findings)
    has_warning = any(f["severity"] == "WARNING" for f in findings)

    if has_critical:
        status = "FAIL"
    elif has_warning:
        status = "WARNING"
    else:
        status = "PASS"

    if summary is None:
        if status == "PASS":
            summary = "All checks passed"
        else:
            n_crit = sum(1 for f in findings if f["severity"] == "CRITICAL")
            n_warn = sum(1 for f in findings if f["severity"] == "WARNING")
            parts = []
            if n_crit:
                parts.append(f"{n_crit} critical")
            if n_warn:
                parts.append(f"{n_warn} warning(s)")
            summary = ", ".join(parts) + " found"

    return {
        "step": step,
        "status": status,
        "findings": findings,
        "summary": summary,
    }


def output_and_exit(result):
    """Print JSON result to stdout and exit with appropriate code."""
    print(json.dumps(result, indent=2))
    sys.exit(1 if result["status"] == "FAIL" else 0)


def load_json_safe(path):
    """Load JSON file with fallback on error."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return None
