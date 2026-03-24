"""Fixture recommendation decision logic and Builder read path.

Implements the QA recommendation workflow from features/test_fixture_repo.md
Section 2.12 and the fixture integration decision logic from
features/regression_testing.md Section 2.10.1.

Two primary consumers:
  - QA agents: evaluate_fixture_needs() + write_recommendation()
  - Builder agents (qa_mode): parse_recommendations() to identify PENDING work
"""

import json
import os
import re
from datetime import datetime, timezone


# --- Decision Logic (QA side) ---

def evaluate_fixture_needs(config_path, state_complexity, has_fixture_tags=False):
    """Evaluate whether a feature needs a fixture recommendation.

    Implements the decision tree from regression_testing.md Section 2.10.1:

    1. Does the feature reference fixture tags?
       - Yes: return {"action": "use_existing"} or {"action": "flag_missing"}
    2. No explicit tags, but scenario needs controlled state?
       - Simple state: return {"action": "inline_setup"}
       - Complex state AND no remote configured: return {"action": "recommend"}
       - Complex state AND remote configured: return {"action": "use_remote"}

    Args:
        config_path: Path to .purlin/config.json.
        state_complexity: One of "simple", "complex", or "none".
            "simple" = single config, no git history.
            "complex" = elaborate git history, multiple branches, config combos.
            "none" = no controlled state needed.
        has_fixture_tags: True if the feature spec references fixture tags.

    Returns:
        dict with keys:
            "action": one of "use_existing", "flag_missing", "inline_setup",
                      "recommend", "use_remote", "none"
            "has_remote": bool, whether fixture_repo_url is configured.
            "reason": str, human-readable explanation.
    """
    # Determine if remote fixture repo is configured
    has_remote = False
    if config_path and os.path.isfile(config_path):
        try:
            with open(config_path) as f:
                config = json.load(f)
            has_remote = "fixture_repo_url" in config
        except (json.JSONDecodeError, IOError):
            pass

    # Branch 1: Feature references fixture tags
    if has_fixture_tags:
        return {
            "action": "use_existing",
            "has_remote": has_remote,
            "reason": "Feature references fixture tags; use existing tags.",
        }

    # Branch 2: No fixture tags
    if state_complexity == "none":
        return {
            "action": "none",
            "has_remote": has_remote,
            "reason": "No controlled state needed.",
        }

    if state_complexity == "simple":
        return {
            "action": "inline_setup",
            "has_remote": has_remote,
            "reason": "Simple state can be expressed via inline setup_commands.",
        }

    if state_complexity == "complex":
        if has_remote:
            return {
                "action": "use_remote",
                "has_remote": True,
                "reason": "Complex state needed; remote fixture repo is configured.",
            }
        else:
            return {
                "action": "recommend",
                "has_remote": False,
                "reason": "Complex state needed; no remote fixture repo configured.",
            }

    # Fallback for unrecognized complexity
    return {
        "action": "none",
        "has_remote": has_remote,
        "reason": f"Unrecognized state_complexity: {state_complexity}",
    }


def write_recommendation(rec_path, feature_name, reason, suggested_tags):
    """Write a fixture recommendation to the recommendations file.

    Appends a new feature section to the file. Creates the file with
    the standard header if it does not exist.

    Args:
        rec_path: Path to tests/qa/fixture_recommendations.md.
        feature_name: Feature stem (e.g., "branch_collab").
        reason: Why persistent fixtures are needed.
        suggested_tags: List of tag paths that would be useful.

    Returns:
        The absolute path to the written file.
    """
    if os.path.isfile(rec_path):
        with open(rec_path) as f:
            content = f.read()
    else:
        os.makedirs(os.path.dirname(rec_path), exist_ok=True)
        content = "# Fixture Recommendations\n"

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tags_list = ", ".join(f"`{t}`" for t in suggested_tags)
    content += f"\n## {feature_name}\n"
    content += f"- **Reason:** {reason}\n"
    content += f"- **Suggested tags:** {tags_list}\n"
    content += f"- **Recorded:** {today}\n"
    content += "- **Status:** PENDING\n"

    with open(rec_path, "w") as f:
        f.write(content)

    return os.path.abspath(rec_path)


# --- Builder Read Path ---

def parse_recommendations(rec_path):
    """Parse fixture_recommendations.md and return structured data.

    This is the Builder startup read path: when qa_mode is enabled,
    the Builder reads this file to identify PENDING fixture tags
    that need to be created.

    Args:
        rec_path: Path to tests/qa/fixture_recommendations.md.

    Returns:
        dict mapping feature_name -> {
            "reason": str,
            "suggested_tags": list[str],
            "recorded": str,
            "status": str,
        }
        Returns empty dict if file does not exist or is empty.
    """
    if not os.path.isfile(rec_path):
        return {}

    try:
        with open(rec_path) as f:
            content = f.read()
    except (IOError, OSError):
        return {}

    if not content.strip():
        return {}

    recommendations = {}
    current_feature = None

    for line in content.splitlines():
        # Match feature header: ## <feature_name>
        header_match = re.match(r'^## (\S+)', line)
        if header_match:
            current_feature = header_match.group(1)
            recommendations[current_feature] = {}
            continue

        if current_feature is None:
            continue

        # Match fields
        reason_match = re.match(r'^- \*\*Reason:\*\* (.+)', line)
        if reason_match:
            recommendations[current_feature]["reason"] = reason_match.group(1)
            continue

        tags_match = re.match(r'^- \*\*Suggested tags:\*\* (.+)', line)
        if tags_match:
            raw = tags_match.group(1)
            tags = re.findall(r'`([^`]+)`', raw)
            recommendations[current_feature]["suggested_tags"] = tags
            continue

        recorded_match = re.match(r'^- \*\*Recorded:\*\* (.+)', line)
        if recorded_match:
            recommendations[current_feature]["recorded"] = recorded_match.group(1)
            continue

        status_match = re.match(r'^- \*\*Status:\*\* (.+)', line)
        if status_match:
            recommendations[current_feature]["status"] = status_match.group(1)
            continue

    return recommendations


def get_pending_recommendations(rec_path):
    """Get only PENDING recommendations from the file.

    Convenience wrapper for the Builder startup path: filters
    parse_recommendations() output to only PENDING entries.

    Args:
        rec_path: Path to tests/qa/fixture_recommendations.md.

    Returns:
        dict mapping feature_name -> recommendation data (only PENDING status).
    """
    all_recs = parse_recommendations(rec_path)
    return {
        name: data
        for name, data in all_recs.items()
        if data.get("status") == "PENDING"
    }
