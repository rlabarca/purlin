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

`--spec NAME` shows one spec. It prints first each of the status's warnings
that opens `NAME: ` or names the spec's file, the code that checks every spec
checking this one, then an empty line; then the spec's view, which opens on
its path and how many rules it has and gives one line per rule:

    specs/auth/login.md: 2 rules
      RULE-1  passed  not audited
        not audited: no audit has read this rule
        PROOF-1  passed  tests/test_login.py::test_proof_1
      RULE-2  no test  waiting
        no test: no test for PROOF-2
        waiting: waiting for its tests to pass
        PROOF-2  no test

A rule's line holds its two cells' words; under it come the reasons of each
cell whose word is neither `passed` nor `strong`, then one line per proof
with its result and its tests, each further test set under the first. It
exits 1 where it printed a warning and 0 where not. A name no spec of the
checkout has is said so, and exits 1. The view writes nothing.

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
    data = payload_module.build_payload(project_root)
    warnings = [line for line in data['warnings']
                if line.startswith(name + ': ') or (path and path in line)]
    feature = next((entry for entry in data['features']
                    if entry['name'] == name), None)
    lines = warnings + [''] if warnings else []
    lines.extend(view_lines(feature or {'spec_path': path, 'rules': []}))
    return lines, 1 if warnings else 0


# The view of one spec: its path and rule count, then per rule its line, the
# reasons of a cell that is neither `passed` nor `strong`, and its proofs.
VIEW_OPENING = '%s: %s'                     # specs/auth/login.md, '2 rules'
RULE_LINE = '  %s  %s  %s'                  # RULE-1, passed, not audited
REASON_LINE = '    %s: %s'                  # not audited, no audit has ...
PROOF_LINE = '    %s  %s'                   # PROOF-1, passed
MET = {'passed': 'passed', 'strong': 'strong'}


def view_lines(feature):
    """One spec's view, from its entry in the payload."""
    rules = feature.get('rules') or []
    lines = [VIEW_OPENING % (feature.get('spec_path') or feature.get('name'),
                             _count(len(rules), 'rule'))]
    for rule in rules:
        cells = rule.get('cells') or {}
        words = [(cells.get(name) or {}).get('word') or '' for name in MET]
        lines.append(RULE_LINE % (rule['id'], words[0], words[1]))
        for name, word in zip(MET, words):
            if word == MET[name]:
                continue
            lines.extend(REASON_LINE % (word, reason)
                         for reason in (cells.get(name) or {}).get('reasons')
                         or ())
        for proof in rule.get('proofs') or ():
            lines.extend(_proof_lines(proof['id'], proof.get('result') or '',
                                      proof.get('tests')))
        for test in rule.get('tests') or ():
            lines.append(PROOF_LINE % (rule['id'], _test_name(test)))
    return lines


def _test_name(test):
    """`<file>::<name>`, or the file alone where the test has no name."""
    name = test.get('name')
    return '%s::%s' % (test.get('file'), name) if name else test.get('file')


def _proof_lines(proof_id, result, tests):
    """A proof's line, its first test after its result, and one line per
    further test set under the first."""
    first = PROOF_LINE % (proof_id, result)
    if not tests:
        return [first]
    lines = ['%s  %s' % (first, _test_name(tests[0]))]
    indent = ' ' * (len(first) + 2)
    lines.extend(indent + _test_name(test) for test in tests[1:])
    return lines


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
