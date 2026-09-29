#!/usr/bin/env python3
"""Config resolver for Purlin projects.

A project has one settings file, `.purlin/config.json`, committed to git.
resolve_config reads it whole; update_config sets one top-level key in it
and keeps every other key it held.
"""

import json
import os
import sys


# How `resolve_project_root` found the root it returned, in the order it
# tries them. The third is a guess, not a find: no `.purlin/` marker was
# seen anywhere, so the caller is told which of the three answered rather
# than being handed a directory with no account of where it came from.
PROJECT_ROOT_SOURCES = {
    'env': 'the PURLIN_PROJECT_ROOT environment variable',
    'climb': 'climbing from the working directory to a .purlin/ marker',
    'cwd': 'the working directory, with no .purlin/ marker in it or above it',
}


def resolve_project_root(start_dir=None):
    """Detect the project root and name how it was found.

    Returns `(root, source)` where source is a key of PROJECT_ROOT_SOURCES.
    Precedence is fixed: `PURLIN_PROJECT_ROOT` when it names a directory
    that exists, then a climb from start_dir (or cwd) to the nearest
    `.purlin/` marker, then cwd as a last resort.
    """
    env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if env_root and os.path.isdir(env_root):
        return env_root, 'env'

    current = os.path.abspath(start_dir or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(current, '.purlin')):
            return current, 'climb'
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    return os.path.abspath(os.getcwd()), 'cwd'


def find_project_root(start_dir=None):
    """The project root alone, for callers that do not report how it was found."""
    return resolve_project_root(start_dir)[0]


def _read_json(path):
    """Read a JSON file, returning its contents or None on any error."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return None
    except (json.JSONDecodeError, IOError, OSError):
        return None


def _config_path(project_root):
    return os.path.join(project_root, '.purlin', 'config.json')


CONFIG_CANNOT_BE_READ = ('.purlin/config.json cannot be read: %s. Fix the file '
                         'by hand; nothing ran and nothing was saved.')

# The JSON value that stands where an object belongs, in the cause's words.
_NOT_AN_OBJECT = ((bool, 'a boolean'), (list, 'a list'), (str, 'a string'),
                  ((int, float), 'a number'))


def config_problem(project_root):
    """The sentence saying `.purlin/config.json` cannot be read, or None.

    None when the file reads as a JSON object or does not exist. Otherwise
    the cause is the first that applies: the text is not UTF-8, the JSON
    reader's own message and line, the kind of value standing where an object
    belongs, or the operating system's own message for an open that failed.
    """
    path = _config_path(project_root)
    if not os.path.lexists(path):
        return None
    try:
        with open(path, 'rb') as f:
            raw = f.read()
    except OSError as error:
        return CONFIG_CANNOT_BE_READ % (error.strerror or str(error))
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        return CONFIG_CANNOT_BE_READ % 'it is not UTF-8 text'
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        return CONFIG_CANNOT_BE_READ % ('%s at line %d'
                                        % (error.msg, error.lineno))
    if isinstance(data, dict):
        return None
    what = 'null'
    for kind, words in _NOT_AN_OBJECT:
        if isinstance(data, kind):
            what = words
            break
    return CONFIG_CANNOT_BE_READ % ('it holds %s where an object belongs' % what)


def resolve_config(project_root):
    """Return `.purlin/config.json` as a dict, or {} when it is absent."""
    return _read_json(_config_path(project_root)) or {}


def update_config(project_root, key, value):
    """Set a top-level key in `.purlin/config.json`, keeping every other key.

    The whole file is written beside the target and moved onto it, so an
    interrupted write leaves the previous contents.
    """
    path = _config_path(project_root)
    config = _read_json(path) or {}
    config[key] = value

    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
            f.write('\n')
        os.replace(tmp_path, path)
    except (IOError, OSError):
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def main():
    project_root = find_project_root()

    if len(sys.argv) < 2:
        print("Usage: config_engine.py [--dump | --key <name>]", file=sys.stderr)
        sys.exit(1)

    arg = sys.argv[1]

    if arg == '--dump':
        config = resolve_config(project_root)
        print(json.dumps(config, indent=4))
    elif arg == '--key':
        if len(sys.argv) < 3:
            print("Usage: config_engine.py --key <name>", file=sys.stderr)
            sys.exit(1)
        config = resolve_config(project_root)
        value = config.get(sys.argv[2])
        if value is None:
            print('')
        elif isinstance(value, (dict, list)):
            print(json.dumps(value))
        elif isinstance(value, bool):
            print('true' if value else 'false')
        else:
            print(value)
    else:
        print(f"Unknown argument: {arg}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
