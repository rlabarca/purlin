"""Write the dashboard page, `purlin-report.html`, with its data in it.

`purlin:status`, `purlin:test`, `purlin:audit` and `purlin:sign` refresh it
as they finish. The first three end on the status table, and
`status.sync_status` calls `refresh` with the payload it has just built, so
the table and the page read the same payload; `purlin:sign` calls it once its
sign-off commit is done, so the page names the sign-off. Nothing runs in the
background, so a file edited with no Purlin command leaves the data file as
it was, and the page shows what the last command saw.

Each refresh writes the page at the project root from the copy this plugin
ships, with the payload in its one data script, so the page and its data
always come from the same version of Purlin, and the page opens with no
other file beside it: from disk, from a `data:` address, as an attachment.
It then removes `.purlin/report-data.js`, where an earlier version of Purlin
kept the data beside the page.

The data holds the payload and, in its two lists of lines, every line
the status prints between its table and its summary sentence, so the board's
notices say what the terminal says. `with_status_lines` adds the ones the
payload's own lists leave to the status:

    information   each anchor rule that passes with nothing to check here,
                  then the line naming the specs with no `> Scope:` line,
                  then the payload's own lines
    warnings      the line that the tests setting changed, each anchor whose
                  pin is not current, the uncommitted spec files on one
                  line, then the payload's own warnings

`notices` is written again over the two lists as they then stand
(`payload.notice_entries`), after one entry the board alone shows, first,
while the working tree holds a change that is not committed (`TREE_DIRTY`).

The one line of the status the data leaves out is `→ Run: purlin:init
--update`, which the status prints above its sentence while an upgrade is
pending.

`scripts/mcp/purlin/status.py` is the one home of each line's words.

The page is gitignored: it is what this checkout last reported, not
evidence.
"""

import os
import subprocess
import sys
import time

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import (fingerprint as fingerprint_module, notices,
                    payload as payload_module)

CONFIG_PATH = os.path.join('.purlin', 'config.json')
PAGE_NAME = 'purlin-report.html'
SHIPPED_PAGE = os.path.join(os.path.dirname(_MCP_DIR), 'report', PAGE_NAME)
# Where Purlin 0.10.0 and earlier kept the data beside the page.
OLD_DATA = os.path.join('.purlin', 'report-data.js')


def refresh(project_root, data=None, generated_by='sync_status'):
    """Write the page with the payload in it. Returns the page's path, or None.

    `data` is a payload the caller already built, so a command that has just
    read the project does not read it twice. A root with no
    `.purlin/config.json` is not a Purlin project and gets no page; neither
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
        path = write_page(project_root, with_status_lines(project_root, data))
    except (IOError, OSError):
        return None
    if path:
        _remove_old_data(project_root)
    return path


# What the board says while the working tree holds a change that is not
# committed.
TREE_DIRTY = notices.line(
    'tree_dirty', 'working tree',
    'This board is not what a commit would carry.',
    'Commit them, then run purlin:status.')


def with_status_lines(project_root, data):
    """The payload as the data file holds it: a copy whose `information` and
    `warnings` also carry the lines the status prints outside those lists.

    `data` itself is left as it is, since the status goes on to print from
    it. Each line is the status's own, word for word.
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
    warnings.extend(status_module._pin_lines(project_root))
    uncommitted = status_module.uncommitted_line(project_root)
    if uncommitted:
        warnings.append(uncommitted)
    warnings.extend(data.get('warnings') or ())
    out = dict(data, information=information, warnings=warnings)
    # The board alone says the working tree is dirty: its first notice.
    out['notices'] = payload_module.notice_entries(dict(
        out, warnings=([TREE_DIRTY] if data.get('dirty') else []) + warnings))
    return out


def write_page(project_root, data):
    """Write the plugin's page to the project root with `data` in it.

    Returns the path, else None. A project with no page gets one where git
    ignores the path, as a project `purlin:init` set up does, or where the
    root is not a git checkout: an untracked page git does not ignore would
    read as uncommitted work. A page already there is written over, a link
    included, so the page and its data come from this version of Purlin.
    """
    target = os.path.join(project_root, PAGE_NAME)
    shipped = _page_text(SHIPPED_PAGE)
    if shipped is None:
        return None
    text = payload_module.page_with_data(shipped, data)
    if text is None:
        return None
    if not os.path.lexists(target) and not _ignored(project_root):
        return None
    tmp = target + '.tmp'
    # `newline=''` writes the page's line endings as the plugin ships them,
    # on Windows too.
    with open(tmp, 'w', encoding='utf-8', newline='') as handle:
        handle.write(text)
    _replace(tmp, target)
    return target


def _replace(source, target):
    """`os.replace`, tried again for a moment where Windows refuses it.

    On Windows a file another program holds open, a virus scanner or a
    search indexer, cannot be replaced until it lets go; a second or two is
    the usual wait. The last refusal is raised, and `refresh` then leaves
    the page as it was.
    """
    for wait in (0.1, 0.3, 0.6, 1.0):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            time.sleep(wait)
    try:
        os.replace(source, target)
    except OSError:
        try:
            os.remove(source)
        except OSError:
            pass
        raise


def _remove_old_data(project_root):
    """Remove the data file an earlier version kept beside the page."""
    path = os.path.join(project_root, OLD_DATA)
    try:
        if os.path.lexists(path):
            os.remove(path)
    except OSError:
        pass


def _page_text(path):
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
