#!/usr/bin/env python3
"""Refresh .purlin/report-data.js after something changed what it reports.

Registered in hooks/hooks.json as an async PostToolUse, SubagentStop and Stop
hook, so it runs in the background after a tool call or a turn and costs the
model nothing: an async hook's output is discarded, and this script prints
nothing anyway. Governed by specs/hooks/refresh_digest_hook.md.

WHAT IT DOES
    1. Finds the project from the working directory (`git rev-parse`).
    2. Leaves at once unless `.purlin/config.json` has `report` true and a
       `digest` mode other than `off`, and unless no commit is in flight
       (`index.lock`: the pre-commit hook owns that regeneration).
    3. Compares the digest's mtime to every input that feeds it: the spec
       directory's `*.md`, `*.proofs-*.json` and `*.receipt.json`, the quality
       caches under `.purlin/cache/`, and the config. Nothing newer, nothing
       to do. This check runs before any Purlin module is imported, so a
       quiet tool call costs a process start and a directory walk.
    4. Takes a non-blocking lock under `.purlin/runtime/`; a second instance
       finding it held leaves, because the holder re-checks the inputs after
       writing and picks up what landed meanwhile.
    5. Calls `purlin_server.generate_digest` with `network=False` (no
       `git ls-remote` from a hook) and `only_if_changed=True` (an unchanged
       payload touches the file rather than rewriting it, so a no-op never
       dirties the working tree).

WHAT IT NEVER DOES
    Block: every path exits 0. Print: nothing on stdout or stderr. Reach the
    network. Run an audit: cached grades are carried through as they stand.
    Parse the hook's stdin: the input is drained and ignored, because which
    tool ran does not change whether the digest is stale.

    PURLIN_SKIP_DIGEST=1 skips everything, as it does for the pre-commit hook.
"""

import json
import os
import subprocess
import sys
import time

_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


def _project():
    """(root, git_dir) for the working directory, or (None, None)."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel', '--absolute-git-dir'],
            capture_output=True, text=True, timeout=5)
    except (subprocess.SubprocessError, OSError):
        return None, None
    if result.returncode != 0:
        return None, None
    lines = result.stdout.splitlines()
    if len(lines) < 2:
        return None, None
    return lines[0].strip(), lines[1].strip()


def _config(root):
    try:
        with open(os.path.join(root, '.purlin', 'config.json'), encoding='utf-8') as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    return config if isinstance(config, dict) else None


def _is_input(filename):
    return (filename.endswith('.md') or filename.endswith('.receipt.json')
            or ('.proofs-' in filename and filename.endswith('.json')))


def _dirty(root, spec_dir, since=None):
    """True when some input is newer than the digest (or than `since`).

    A missing digest is dirty. `since` lets the caller ask "did anything land
    after I started?", which is what closes the window between reading the
    inputs and writing the file.
    """
    digest = os.path.join(root, '.purlin', 'report-data.js')
    try:
        stamp = os.stat(digest).st_mtime
    except OSError:
        return True
    if since is not None:
        stamp = min(stamp, since)

    def newer(path):
        try:
            return os.stat(path).st_mtime > stamp
        except OSError:
            return False

    if newer(os.path.join(root, '.purlin', 'config.json')):
        return True
    cache_dir = os.path.join(root, '.purlin', 'cache')
    try:
        cache_names = os.listdir(cache_dir)
    except OSError:
        cache_names = []
    for name in cache_names:
        if name.endswith('.json') and newer(os.path.join(cache_dir, name)):
            return True
    for dirpath, _dirnames, filenames in os.walk(os.path.join(root, spec_dir)):
        for name in filenames:
            if _is_input(name) and newer(os.path.join(dirpath, name)):
                return True
    return False


def main():
    try:
        sys.stdin.read()
    except (OSError, ValueError):
        pass
    if os.environ.get('PURLIN_SKIP_DIGEST') == '1':
        return
    root, git_dir = _project()
    if not root:
        return
    config = _config(root)
    if not config or not config.get('report') or config.get('digest') == 'off':
        return
    if os.path.exists(os.path.join(git_dir, 'index.lock')):
        return
    spec_dir = config.get('spec_dir') or 'specs'
    if not _dirty(root, spec_dir):
        return

    sys.path.insert(0, os.path.join(_PLUGIN_ROOT, 'scripts', 'audit'))
    sys.path.insert(0, os.path.join(_PLUGIN_ROOT, 'scripts', 'mcp'))
    import static_checks
    from purlin_server import generate_digest

    runtime = os.path.join(root, '.purlin', 'runtime')
    os.makedirs(runtime, exist_ok=True)
    with open(os.path.join(runtime, 'refresh_digest.lock'), 'a+') as lock:
        if not static_checks.try_lock_exclusive(lock):
            return
        try:
            for _attempt in range(3):
                started = time.time()
                generate_digest(root, generated_by='hook', network=False,
                                only_if_changed=True)
                if not _dirty(root, spec_dir, since=started):
                    break
        finally:
            static_checks._unlock(lock)


if __name__ == '__main__':
    # Silent on every path: an async hook's output is discarded, and a
    # synchronous one's would reach the transcript. Exit 0 on every path: a
    # refresh that failed is a stale dashboard, never a blocked tool call.
    devnull = open(os.devnull, 'w')
    sys.stdout = devnull
    sys.stderr = devnull
    try:
        main()
    except BaseException:
        pass
    sys.exit(0)
