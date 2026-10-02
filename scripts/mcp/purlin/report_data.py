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

The data file holds the payload and, in its two lists of lines, every line
the status prints between its table and its summary sentence, so the board's
notices say what the terminal says. `with_status_lines` adds the ones the
payload's own lists leave to the status:

    information   each anchor rule that passes with nothing to check here,
                  then the line naming the specs with no `> Scope:` line,
                  then the payload's own lines
    warnings      the line that the tests setting changed, each anchor whose
                  pin is not current, the uncommitted spec files on one
                  line, then the payload's own warnings

The one line of the status the data leaves out is `→ Run: purlin:init
--update`, which the status prints above its sentence while an upgrade is
pending.

`scripts/mcp/purlin/status.py` is the one home of each line's words.

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

from purlin import (fingerprint as fingerprint_module,
                    payload as payload_module)

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
        path = payload_module.write_report_data(
            project_root, with_status_lines(project_root, data))
    except (IOError, OSError):
        return None
    write_page(project_root)
    return path


# The uncommitted spec files, which the status prints as a heading and one
# line per file, on the one line a notice holds.
UNCOMMITTED_SPECS = 'Uncommitted spec changes: %s'


def with_status_lines(project_root, data):
    """The payload as the data file holds it: a copy whose `information` and
    `warnings` also carry the lines the status prints outside those lists.

    `data` itself is left as it is, since the status goes on to print from
    it. Each line is the status's own, word for word, but two the status
    prints under a heading: an anchor's pin line stands without the
    `Anchors:` line above it, since it names its anchor, and the
    uncommitted spec files follow their heading on one line, each as git
    names it, `M specs/auth/login.md`.
    """
    # Imported here: the status imports this module.
    from purlin import status as status_module
    information = list(status_module.nothing_lines(data))
    names = status_module.incomplete_names(data)
    if names:
        information.append(status_module.incomplete_line(names))
    information.extend(data.get('information') or ())

    warnings = []
    if fingerprint_module.setting_changed(project_root):
        warnings.append(status_module.SETTING_CHANGED)
    warnings.extend(status_module._pin_lines(project_root)[1:])
    uncommitted = status_module._uncommitted_specs(project_root)
    if uncommitted:
        warnings.append(UNCOMMITTED_SPECS % ', '.join(
            line.strip() for line in uncommitted))
    warnings.extend(data.get('warnings') or ())
    return dict(data, information=information, warnings=warnings)


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
