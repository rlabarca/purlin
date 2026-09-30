"""Refresh `.purlin/report-data.js`, the file the dashboard page reads.

`purlin:status`, `purlin:test`, `purlin:audit` and `purlin:sign` refresh it
as they finish. The first three end on the status table, and
`status.sync_status` calls `refresh` with the payload it has just built, so
the table and the page read the same payload; `purlin:sign` calls it once its
sign-off commit is done, so the page names the tag the first sign-off writes. Nothing runs in the background, so a
file edited with no Purlin command leaves the data file as it was, and the
page shows what the last command saw.

The file is gitignored: it is what this checkout last reported, not evidence.
"""

import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import payload as payload_module

CONFIG_PATH = os.path.join('.purlin', 'config.json')


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
        return payload_module.write_report_data(project_root, data)
    except (IOError, OSError):
        return None
