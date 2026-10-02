#!/usr/bin/env python3
"""Print the report the `drift` tool answers, for a session without the tool.

    purlin_drift.py [--project-root DIR] [--since N-or-date] [--json]
    purlin_drift.py --help | -h

It prints the lines of the tool's one view, one per line, and exits 0.
`--json` prints the tool's whole answer as the tool gives it. `--since` is a
number of commits or a `YYYY-MM-DD` date, as the tool takes it; one drift
refuses, and a checkout with no commit, print `<error>: <reason>` and exit 2.

Where the tool would refuse, it prints only that refusal and exits 1
(`project.refusal`): a folder with no `.purlin/config.json`, a settings file
that cannot be read, or Purlin's own folder named from a working directory
outside it. `--project-root` defaults to the working directory. A wrong
command line prints one `purlin:` line and the usage to stderr and exits 2.
"""

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import console as console_module                   # noqa: E402
from purlin import drift as drift_module                       # noqa: E402
from purlin import project as project_module                   # noqa: E402
import purlin_status                                           # noqa: E402

USAGE = ('Usage: purlin_drift.py [--project-root DIR] [--since N-or-date] '
         '[--json]')
REFUSED = '%s: %s'      # the report's `error`, then its `reason`


def main(argv=None):
    console_module.force_utf8_stdio()
    found, error = purlin_status.parse_args(
        list(sys.argv[1:] if argv is None else argv),
        {'--project-root': True, '--since': True, '--json': False})
    if found.get('--help'):
        print(USAGE)
        return 0
    if error:
        return purlin_status.wrong_command_line(error, USAGE)
    project_root = os.path.abspath(
        os.path.expanduser(found.get('--project-root', '.')))
    refused = project_module.refusal(project_root, os.getcwd())
    if refused:
        print(refused)
        return 1
    report = drift_module.compute_drift(project_root, found.get('--since'))
    if 'error' in report:
        print(REFUSED % (report['error'], report['reason']))
        return 2
    if found.get('--json'):
        print(json.dumps(report, separators=(',', ':')))
    else:
        print('\n'.join(report['view']['lines']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
