"""figma_web RULE-16: the gated CLI suites hand `--agents` a JSON object.

`claude --agents` rejects a file path and wants {name: {description, prompt}}.
Both e2e suites that drive `claude -p` are gated (PURLIN_E2E_FIGMA /
PURLIN_E2E_AGENT) and nothing a normal host runs would catch a regression in
the flag they build, so the argv builder lives in dev/e2e_claude_cli.py and is
checked here: in process, no CLI, no API key, no Figma MCP server.
"""

import json
import os

import pytest

from e2e_claude_cli import agents_json, claude_command

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_PATH = os.path.join(PROJECT_ROOT, "agents", "purlin.md")
FIGMA_SUITE = os.path.join(PROJECT_ROOT, "dev", "test_e2e_figma_web.py")
BUILD_SUITE = os.path.join(PROJECT_ROOT, "dev", "test_e2e_build_agent.py")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _agents_value(cmd):
    """The element right after ``--agents``, asserting the flag is present."""
    assert "--agents" in cmd, f"--agents missing from argv: {cmd}"
    return cmd[cmd.index("--agents") + 1]


@pytest.mark.proof("figma_web", "PROOF-16", "RULE-16")
def test_agents_flag_carries_the_json_object_not_a_path():
    cmd = claude_command(
        model="sonnet", max_turns=50, plugin_dir=PROJECT_ROOT,
        agent_path=AGENT_PATH,
    )

    # The path form is what the CLI rejects: no argv element may be the file.
    offenders = [a for a in cmd if a.endswith("purlin.md")]
    assert offenders == [], f"--agents was given a file path: {offenders}"

    value = _agents_value(cmd)
    try:
        obj = json.loads(value)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"--agents value is not JSON ({exc}): {value!r}") from None
    assert list(obj) == ["purlin"], f"--agents keys {list(obj)}, want ['purlin']"

    text = _read(AGENT_PATH)
    front, body = text.split("---\n", 2)[1], text.split("---\n", 2)[2]
    expected_description = next(
        line.split(":", 1)[1].strip()
        for line in front.splitlines() if line.startswith("description:")
    )
    assert obj["purlin"]["description"] == expected_description
    assert obj["purlin"]["prompt"] == body.lstrip("\n")
    assert obj["purlin"]["prompt"].startswith("# Purlin Agent")


@pytest.mark.proof("figma_web", "PROOF-16", "RULE-16")
def test_agent_file_without_front_matter_is_all_prompt(tmp_path):
    plain = tmp_path / "nofm.md"
    plain.write_text("just a body, no front matter\n", encoding="utf-8")

    obj = json.loads(agents_json(str(plain)))
    assert obj == {"purlin": {"description": "",
                              "prompt": "just a body, no front matter\n"}}


@pytest.mark.proof("figma_web", "PROOF-16", "RULE-16")
def test_both_gated_suites_use_the_shared_helper():
    for path in (FIGMA_SUITE, BUILD_SUITE):
        text = _read(path)
        assert "from e2e_claude_cli import" in text, \
            f"{os.path.basename(path)} does not import the shared helper"
        for bad in ('"--agents", agent', '"--agents", AGENT'):
            assert bad not in text, \
                f"{os.path.basename(path)} still passes a path: {bad}"
