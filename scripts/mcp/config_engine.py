"""Config resolver for Purlin projects.

A project has one settings file, `.purlin/config.json`, committed to git.
resolve_config reads it whole; update_config sets one top-level key in it
and keeps every other key it held. A file that exists and cannot be read is
never read as empty: both raise ConfigUnreadable with the sentence
config_problem gives, so a save never overwrites a file a person can still fix.
"""

import json
import os


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


def _config_path(project_root):
    return os.path.join(project_root, '.purlin', 'config.json')


CONFIG_CANNOT_BE_READ = ('.purlin/config.json cannot be read: %s. Fix the file '
                         'by hand; nothing ran and nothing was saved.')

# The JSON value that stands where an object belongs, in the cause's words.
_NOT_AN_OBJECT = ((bool, 'a boolean'), (list, 'a list'), (str, 'a string'),
                  ((int, float), 'a number'))


class ConfigUnreadable(ValueError):
    """`.purlin/config.json` exists and cannot be read; the message is the sentence."""


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


def _read_json(project_root):
    """The settings as a dict, or None when the file is absent.

    A file that exists and cannot be read raises ConfigUnreadable carrying
    config_problem's sentence; it is never folded into "absent".
    """
    problem = config_problem(project_root)
    if problem:
        raise ConfigUnreadable(problem)
    path = _config_path(project_root)
    if not os.path.isfile(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def resolve_config(project_root):
    """Return `.purlin/config.json` as a dict, or {} when it is absent."""
    return _read_json(project_root) or {}


def update_config(project_root, key, value):
    """Set a top-level key in `.purlin/config.json`, keeping every other key.

    Refused with ConfigUnreadable, the file untouched, while the file cannot
    be read. The whole file is written beside the target and moved onto it;
    a write or move that fails removes the file written beside it and raises
    the error, so the caller can say the setting was not saved.
    """
    path = _config_path(project_root)
    config = _read_json(project_root) or {}
    config[key] = value

    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
            f.write('\n')
        os.replace(tmp_path, path)
    except OSError:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
