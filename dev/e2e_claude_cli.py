"""Shared `claude -p` argv builder for the gated e2e suites.

Two suites drive the real CLI (dev/test_e2e_figma_web.py and
dev/test_e2e_build_agent.py). Both had their own copy of the agent-definition
helper, and the copies drifted: `--agents` took a file path in older CLI builds
and takes a JSON object ({name: {description, prompt}}) in current ones, so one
suite was fixed and the other kept handing the flag a path until this module
made the argv a single shared thing.

The file is deliberately named without a `test_` prefix so pytest never
collects it; the behaviour it holds is checked by dev/test_claude_cli_helper.py,
which any host can run without a CLI, an API key or a Figma MCP server.
"""

import json
import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_AGENT_PATH = os.path.join(PROJECT_ROOT, "agents", "purlin.md")

_FRONT_MATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def agents_json(path=None):
    """``agents/purlin.md`` as the JSON object ``claude --agents`` expects.

    The flag took a file path in older CLI builds and takes a JSON object
    ({name: {description, prompt}}) in current ones, so the agent definition
    is read from the repository and serialized here rather than passed by path.
    A file without front matter yields the name ``purlin``, an empty
    description and the whole text as the prompt.
    """
    path = path or DEFAULT_AGENT_PATH
    with open(path, encoding="utf-8") as f:
        text = f.read()
    name, description, body = "purlin", "", text
    m = _FRONT_MATTER.match(text)
    if m:
        front, body = m.group(1), m.group(2).lstrip("\n")
        for line in front.splitlines():
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("description:"):
                description = line.split(":", 1)[1].strip()
    return json.dumps({name: {"description": description, "prompt": body}})


def claude_command(*, model="sonnet", max_turns=50, add_dirs=(),
                   plugin_dir=None, agent_path=None, session=None):
    """The argv for one non-interactive ``claude -p`` call.

    Optional parts are appended only when asked for, so each suite keeps the
    flags it used before: `--add-dir` per entry of `add_dirs`, `--plugin-dir`,
    `--agents` with the JSON object for `agent_path`, `--resume` for `session`.
    """
    cmd = [
        "claude", "-p",
        "--output-format", "json",
        "--model", str(model),
        "--max-turns", str(max_turns),
        "--dangerously-skip-permissions",
    ]
    for d in add_dirs:
        cmd += ["--add-dir", d]
    if plugin_dir:
        cmd += ["--plugin-dir", plugin_dir]
    if agent_path:
        cmd += ["--agents", agents_json(agent_path)]
    if session:
        cmd += ["--resume", session]
    return cmd
