"""The Purlin core package: spec parsing, evidence readers, states, reports.

Every module here is stdlib only and runs on Python 3.9. Import it as
`from purlin import specs` after putting `scripts/mcp` on `sys.path`; each
module does that for itself, so importing any one of them by path works
whether the plugin is this checkout (`claude --plugin-dir .`) or the
marketplace copy under `~/.claude/plugins/cache/purlin/purlin/<version>/`.
"""

import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

# The plugin root is the directory holding `scripts/`, with `VERSION` beside it.
PLUGIN_ROOT = os.path.dirname(os.path.dirname(_MCP_DIR))


def _read_version():
    """The plugin version, read from the `VERSION` file beside `scripts/`.

    One file carries the version (`dev/bump_version.sh` propagates it); this
    reads it rather than holding a literal, so no release can leave the server
    reporting a number the file does not.
    """
    path = os.path.join(PLUGIN_ROOT, 'VERSION')
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return handle.read().strip()
    except (IOError, OSError):
        return '0.0.0'


PURLIN_VERSION = _read_version()

__all__ = ['PLUGIN_ROOT', 'PURLIN_VERSION', '_read_version']
