"""Refresh `.purlin/report-data.js`, the file the dashboard page reads.

`purlin:status`, `purlin:test`, `purlin:audit` and `purlin:sign` refresh it
as they finish. The first three end on the status table, and
`status.sync_status` calls `refresh` with the payload it has just built, so
the table and the page read the same payload; `purlin:sign` calls it once its
sign-off commit is done, so the page names the sign-off. Nothing runs in the
background, so a file edited with no Purlin command leaves the data file as
it was, and the page shows what the last command saw.

Each refresh also writes the page itself, `purlin-report.html` at the project
root, where the project's copy differs from the one this plugin ships, so the
page and its data always come from the same version of Purlin.

Both files are gitignored: they are what this checkout last reported, not
evidence.
"""

import os
import shutil
import subprocess
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import payload as payload_module

CONFIG_PATH = os.path.join('.purlin', 'config.json')
PAGE_NAME = 'purlin-report.html'
SHIPPED_PAGE = os.path.join(os.path.dirname(_MCP_DIR), 'report', PAGE_NAME)


def refresh(project_root, data=None, generated_by='sync_status'):
    """Write the payload to `.purlin/report-data.js`. Returns the path, or None.

    `data` is a payload the caller already built, so a command that has just
    read the project does not read it twice. A root with no
    `.purlin/config.json` is not a Purlin project and gets no file; neither
    does a project with no spec, where the page's own empty screen says what
    to run. A write that fails leaves the command's answer untouched: the
    page is a view, and a view that could not be written never fails the
    command that wanted it.
    """
    if not os.path.isfile(os.path.join(project_root, CONFIG_PATH)):
        return None
    try:
        if data is None:
            data = payload_module.build_payload(project_root,
                                                generated_by=generated_by)
        if not data.get('features'):
            return None
        path = payload_module.write_report_data(project_root, data)
    except (IOError, OSError):
        return None
    write_page(project_root)
    return path


def write_page(project_root):
    """Write the plugin's page to the project root where the project's differs.

    Returns the path where it wrote, else None. A copy that already reads
    byte for byte as the plugin's is left alone, modification time included.
    A project with no page gets one where git ignores the path, as a project
    `purlin:init` set up does, or where the root is not a git checkout: an
    untracked page git does not ignore would read as uncommitted work.
    """
    target = os.path.join(project_root, PAGE_NAME)
    try:
        shipped = _page_bytes(SHIPPED_PAGE)
        if shipped is None:
            return None
        if os.path.lexists(target):
            if not os.path.islink(target) and _page_bytes(target) == shipped:
                return None
            os.remove(target)
        elif not _ignored(project_root):
            return None
        shutil.copyfile(SHIPPED_PAGE, target)
    except (IOError, OSError):
        return None
    return target


def _page_bytes(path):
    """The page's text exactly as the file holds it, or None where it cannot be read."""
    try:
        with open(path, 'r', encoding='utf-8', newline='') as handle:
            return handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return None


def _ignored(project_root):
    """True where git ignores the page's path, or the root is no git checkout."""
    try:
        result = subprocess.run(
            ['git', 'check-ignore', '-q', PAGE_NAME],
            capture_output=True, text=True, cwd=project_root, timeout=15)
    except (subprocess.SubprocessError, OSError):
        return True
    # 0: ignored. 1: not ignored. 128: not a git checkout.
    return result.returncode != 1
