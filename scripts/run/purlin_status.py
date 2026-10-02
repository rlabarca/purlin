#!/usr/bin/env python3
"""Print the status the `sync_status` tool answers, for a session without the tool.

    purlin_status.py [--project-root DIR] [--spec NAME]
    purlin_status.py --help | -h

With no `--spec` it prints `status.sync_status` for the folder, the text the
tool answers, and exits 0. Where the tool would refuse, it prints only that
refusal and exits 1 (`project.refusal`): a folder with no
`.purlin/config.json`, a settings file that cannot be read, or Purlin's own
folder named from a working directory outside it. `--project-root` defaults
to the working directory.

`--spec NAME` checks one saved spec with the code that checks every spec: it
prints each of the status's warnings that opens `NAME: ` or names the spec's
file and exits 1, or one line counting the spec's rules and proofs and exits
0. A name no spec of the checkout has is said so, and exits 1.

A wrong command line prints one `purlin:` line and the usage to stderr and
exits 2.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import console as console_module                   # noqa: E402
from purlin import payload as payload_module                   # noqa: E402
from purlin import project as project_module                   # noqa: E402
from purlin import specs as specs_module                       # noqa: E402
from purlin import status as status_module                     # noqa: E402

USAGE = 'Usage: purlin_status.py [--project-root DIR] [--spec NAME]'

SPEC_CLEAN = '%s: %s and %s read. No mistake found.'   # login, '2 rules', '3 proofs'
NOT_A_SPEC = '%s: no spec of this checkout has that name. Run purlin:status to see its specs.'


def _count(number, word):
    return '%d %s' % (number, word if number == 1 else word + 's')


def parse_args(argv, flags):
    """`({flag: value}, error)` for a command line of `--flag VALUE` pairs.

    `flags` maps each flag to True where it takes a value. `--help` and `-h`
    answer `{'--help': True}` alone.
    """
    found = {}
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in ('--help', '-h'):
            return {'--help': True}, None
        if token not in flags:
            return found, 'unknown argument %s' % token
        if not flags[token]:
            found[token] = True
        else:
            index += 1
            if index >= len(argv) or not argv[index].strip():
                return found, '%s needs a value' % token
            found[token] = argv[index]
        index += 1
    return found, None


def wrong_command_line(error, usage):
    print('purlin: %s.' % error, file=sys.stderr)
    print(usage, file=sys.stderr)
    return 2


def spec_lines(project_root, name):
    """`(lines, exit code)` for `--spec NAME`."""
    info = specs_module.scan_specs(project_root).get(name)
    if info is None:
        return [NOT_A_SPEC % name], 1
    path = info.get('spec_path') or ''
    warnings = payload_module.build_payload(project_root)['warnings']
    lines = [line for line in warnings
             if line.startswith(name + ': ') or (path and path in line)]
    if lines:
        return lines, 1
    return [SPEC_CLEAN % (name, _count(len(info.get('rules') or ()), 'rule'),
                          _count(len(info.get('proofs') or ()), 'proof'))], 0


def main(argv=None):
    console_module.force_utf8_stdio()
    found, error = parse_args(list(sys.argv[1:] if argv is None else argv),
                              {'--project-root': True, '--spec': True})
    if found.get('--help'):
        print(USAGE)
        return 0
    if error:
        return wrong_command_line(error, USAGE)
    project_root = os.path.abspath(
        os.path.expanduser(found.get('--project-root', '.')))
    refused = project_module.refusal(project_root, os.getcwd())
    if refused:
        print(refused)
        return 1
    if '--spec' in found:
        lines, code = spec_lines(project_root, found['--spec'])
        print('\n'.join(lines))
        return code
    print(status_module.sync_status(project_root))
    return 0


if __name__ == '__main__':
    sys.exit(main())
