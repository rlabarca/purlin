"""Tests for scripts/anchor/upstream.py: anchors pulled from an anchor repo.

Two local bare repositories stand in for the two sides of the workflow: an
anchor repo that publishes `specs/no_eval.md`, and the origin the
consuming project was cloned from. Nothing here reaches a network; every url is
a path to a bare repository on disk.

What the tests hold:

`add`      writes the local copy with `> Source:` and `> Pinned:`, derives a
           name when none is given, and refuses a source that is not a spec
           in Purlin's format kept in a git repository
`sync`     reports the rule delta, advances the pin, fetches each source once
           per run, and reports an anchor whose source names no repository
           as `error`
`--check`  changes nothing and exits 1 when a pin is behind
"""

import contextlib
import io
import json
import os
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'anchor'))
sys.path.insert(0, DEV)

import upstream  # noqa: E402
# Removing a tree that holds a repository is written once, in the other
# suite that has to do it: on Windows the read-only bit git puts on a loose
# object stops a plain removal.
from test_drift import _rmtree  # noqa: E402

UPSTREAM_PY = os.path.join(ROOT, 'scripts', 'anchor', 'upstream.py')

ANCHOR_V1 = """# Anchor: no_eval

> Description: No dynamic code execution in production code.
> Type: security

## Rules

- RULE-1: No eval() in source files
- RULE-2: No exec() in source files

## Proof

- PROOF-1 (RULE-1): Grep src/ for "eval("; verify zero matches
- PROOF-2 (RULE-2): Grep src/ for "exec("; verify zero matches
"""

ANCHOR_V2 = """# Anchor: no_eval

> Description: No dynamic code execution in production code.
> Type: security

## Rules

- RULE-1: No eval() in source files
- RULE-2: No exec() anywhere in the tree
- RULE-3: No compile() in source files

## Proof

- PROOF-1 (RULE-1): Grep src/ for "eval("; verify zero matches
- PROOF-2 (RULE-2): Grep src/ for "exec("; verify zero matches
- PROOF-3 (RULE-3): Grep src/ for "compile("; verify zero matches
"""

SECOND_ANCHOR = """# Anchor: no_secrets

## Rules

- RULE-1: No credential literals in source files

## Proof

- PROOF-1 (RULE-1): Grep src/ for password literals; verify zero matches
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _git(args, cwd):
    result = subprocess.run(['git'] + args, cwd=cwd, capture_output=True,
                            text=True)
    assert result.returncode == 0, '%s -> %s' % (args, result.stderr)
    return result.stdout.strip()


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def _bare(path):
    """A bare repository whose HEAD names the branch `_publish` pushes.

    The default branch a machine's git config asks for is not this fixture's
    business: without `-c init.defaultBranch=main` a runner configured for
    `master` leaves HEAD pointing at a branch nothing ever creates, and every
    clone of the repository then checks out nothing at all.
    """
    subprocess.run(['git', '-c', 'init.defaultBranch=main', 'init', '--bare',
                    '-q', path], check=True, capture_output=True)
    return path


def _clone(bare, work):
    subprocess.run(['git', 'clone', '-q', bare, work], check=True,
                   capture_output=True)
    _git(['config', 'user.email', 'dev@purlin.local'], work)
    _git(['config', 'user.name', 'Purlin Dev'], work)
    return work


def _publish(work, message):
    _git(['add', '-A'], work)
    _git(['commit', '-q', '-m', message], work)
    _git(['push', '-q', 'origin', 'HEAD:refs/heads/main'], work)
    return _git(['rev-parse', 'HEAD'], work)


@pytest.fixture
def workspace(tmp_path):
    """An anchor repo and a project, both backed by a local bare repository.

    Returns an object with `anchor_repo` (the bare path a `> Source:` names),
    `anchor_work` (a checkout of it, to publish new versions from) and `root`
    (the project this module acts on).
    """
    base = str(tmp_path)
    anchor_bare = _bare(os.path.join(base, 'policies.git'))
    anchor_work = _clone(anchor_bare, os.path.join(base, 'policies_work'))
    _write(os.path.join(anchor_work, 'specs', 'no_eval.md'), ANCHOR_V1)
    _write(os.path.join(anchor_work, 'specs', 'no_secrets.md'), SECOND_ANCHOR)
    first = _publish(anchor_work, 'publish the security anchors')

    project_bare = _bare(os.path.join(base, 'project.git'))
    root = _clone(project_bare, os.path.join(base, 'project'))
    _write(os.path.join(root, '.purlin', 'config.json'), '{"gate": "passed"}\n')
    os.makedirs(os.path.join(root, 'specs', '_anchors'), exist_ok=True)
    _publish(root, 'set the project up')

    class Workspace(object):
        pass

    workspace = Workspace()
    workspace.anchor_repo = anchor_bare
    workspace.anchor_work = anchor_work
    workspace.root = root
    workspace.first_sha = first
    return workspace


def _advance(workspace, content=ANCHOR_V2):
    """Publish a new version of the anchor. Returns the new head sha."""
    _write(os.path.join(workspace.anchor_work, 'specs', 'no_eval.md'), content)
    return _publish(workspace.anchor_work, 'publish version two')


def _add(workspace, name='no_eval', path='specs/no_eval.md'):
    return upstream.add(workspace.root, workspace.anchor_repo, path=path,
                        name=name)


def _copy_text(workspace, name='no_eval'):
    with open(upstream.anchor_path(workspace.root, name), 'r',
              encoding='utf-8') as handle:
        return handle.read()


def _child(args, cwd=None):
    """Run `upstream.py` as a child process. Returns `(exit_code, stdout)`."""
    result = subprocess.run([sys.executable, UPSTREAM_PY] + list(args),
                            capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout


def _cli(workspace, args, child=False):
    """Run the command line against the workspace. Returns `(exit_code, stdout)`.

    `main()` runs in this process, which is what lets a mutation run see which
    case caught a break. `child=True` starts the script as a process instead,
    for the cases whose proof names the command line's exit code.
    """
    if child:
        return _child(['--project-root', workspace.root] + list(args))
    out = io.StringIO()
    with contextlib.redirect_stdout(out), \
            contextlib.redirect_stderr(io.StringIO()):
        try:
            code = upstream.main(['--project-root', workspace.root] + args)
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else 1
    return code, out.getvalue()


@pytest.fixture
def started(monkeypatch):
    """Every process this test starts, each as the list of its arguments.

    `subprocess.run` starts its process through `subprocess.Popen`, so one
    recorder on the class sees both.
    """
    seen = []
    real = subprocess.Popen

    class Recorded(real):
        def __init__(self, args, *rest, **kwargs):
            seen.append(list(args) if isinstance(args, (list, tuple))
                        else [args])
            super(Recorded, self).__init__(args, *rest, **kwargs)

    monkeypatch.setattr(subprocess, 'Popen', Recorded)
    return seen


def _anchors_held(workspace):
    return sorted(os.listdir(os.path.join(workspace.root, 'specs', '_anchors')))


def _files(root):
    """`{relative path: bytes}` for every file under a project, `.git` aside."""
    held = {}
    for folder, dirs, names in os.walk(root):
        if '.git' in dirs:
            dirs.remove('.git')
        for name in names:
            path = os.path.join(folder, name)
            with open(path, 'rb') as handle:
                held[os.path.relpath(path, root)] = handle.read()
    return held


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

# purlin: upstream PROOF-1
def test_an_added_anchor_keeps_the_author_text_under_source_and_pin(workspace):
    result = _add(workspace)
    assert result['status'] == 'added'
    assert result['rules'] == ['RULE-1', 'RULE-2']
    tracking = ['> Source: %s specs/no_eval.md' % workspace.anchor_repo,
                '> Pinned: %s' % workspace.first_sha]
    text = _copy_text(workspace)
    lines = text.splitlines()
    assert lines[0] == '# Anchor: no_eval'
    assert lines[2:4] == tracking, lines
    assert text.replace('\n'.join(tracking) + '\n\n', '', 1) == ANCHOR_V1


# purlin: upstream PROOF-25
def test_add_from_the_command_line_prints_where_the_copy_went(workspace):
    code, out = _cli(workspace, ['add', workspace.anchor_repo, '--path',
                                 'specs/no_eval.md', '--name', 'no_eval'])
    assert code == 0
    assert out.splitlines()[0] == (
        'no_eval: written to specs/_anchors/no_eval.md, pinned %s'
        % workspace.first_sha[:7])


# purlin: upstream PROOF-2
def test_the_pin_is_the_full_head_sha_and_names_no_branch(workspace):
    result = _add(workspace)
    head = _git(['rev-parse', 'HEAD'], workspace.anchor_work)
    assert result['pinned'] == head
    assert len(result['pinned']) == 40
    assert 'main' not in _copy_text(workspace).split('## Rules')[0]


# purlin: upstream PROOF-3
def test_with_no_name_the_anchor_is_named_after_its_file(workspace):
    """The path is spelled with the running system's separator, so a run on
    Windows types it with a backslash."""
    result = upstream.add(workspace.root, workspace.anchor_repo,
                          path=os.path.join('specs', 'no_secrets.md'))
    assert result['anchor'] == 'no_secrets'
    assert _anchors_held(workspace) == ['no_secrets.md']


# purlin: upstream PROOF-4
def test_tracking_lines_the_source_carried_give_way_to_this_projects(workspace):
    """A source that is itself a consumer copy must not bring its pin along."""
    _write(os.path.join(workspace.anchor_work, 'specs', 'no_eval.md'),
           ANCHOR_V1.replace(
               '> Type: security',
               '> Type: security\n> Source: git@example.com:other.git a.md\n'
               '> Pinned: deadbeef'))
    head = _publish(workspace.anchor_work, 'publish a copy that carries tracking')
    _add(workspace)
    lines = _copy_text(workspace).splitlines()
    assert [line for line in lines if line.startswith('> Source:')] == [
        '> Source: %s specs/no_eval.md' % workspace.anchor_repo]
    assert [line for line in lines if line.startswith('> Pinned:')] == [
        '> Pinned: %s' % head]
    assert not any('deadbeef' in line for line in lines)


# purlin: upstream PROOF-5
def test_a_path_the_source_does_not_hold_writes_no_copy(workspace):
    result = _add(workspace, path='specs/absent.md')
    assert result['status'] == 'error'
    assert result['error'] == 'specs/absent.md is not in the source'
    assert _anchors_held(workspace) == []


# purlin: upstream PROOF-6
def test_a_source_beginning_with_a_dash_is_refused_and_starts_nothing(
        workspace, started, tmp_path):
    marker = str(tmp_path / 'ran')
    result = upstream.add(workspace.root, '--upload-pack=touch %s' % marker,
                          path='a.md', name='hostile')
    assert result['status'] == 'error'
    assert result['error'] == 'source rejected: begins with "-"'
    assert _anchors_held(workspace) == []
    assert not os.path.exists(marker)
    assert started == [], started


# purlin: upstream PROOF-26
def test_an_ext_transport_source_is_refused_and_starts_nothing(
        workspace, started, tmp_path):
    marker = str(tmp_path / 'ran')
    result = upstream.add(workspace.root, 'ext::sh -c touch%% %s' % marker,
                          path='a.md', name='hostile')
    assert result['status'] == 'error'
    assert result['error'] == 'source rejected: names an ext:: transport'
    assert _anchors_held(workspace) == []
    assert not os.path.exists(marker)
    assert started == [], started


# purlin: upstream PROOF-27
def test_a_repository_source_starts_git_and_writes_the_copy(workspace, started):
    """The other side of the two refusals: the same recorder does see git
    start for a source that is allowed, so an empty record above means no
    process started rather than a recorder that sees nothing."""
    assert _add(workspace)['status'] == 'added'
    assert any(args[:1] == ['git'] for args in started), started
    assert _anchors_held(workspace) == ['no_eval.md']


# ---------------------------------------------------------------------------
# sync --check
# ---------------------------------------------------------------------------

# purlin: upstream PROOF-8
def test_check_when_behind_reports_and_changes_no_file(workspace):
    _add(workspace)
    new_sha = _advance(workspace)
    before = _files(workspace.root)

    result = upstream.sync(workspace.root, check=True)
    row = result['anchors'][0]
    assert row['status'] == 'behind'
    assert row['pinned'] == workspace.first_sha
    assert row['remote_sha'] == new_sha
    assert result['behind'] == 1
    assert _files(workspace.root) == before


# purlin: upstream PROOF-9
def test_check_exits_0_when_the_pin_is_current(workspace):
    _add(workspace)
    code, out = _cli(workspace, ['sync', '--check'])
    assert code == 0
    assert out.splitlines() == ['no_eval: the pin is current.']


# purlin: upstream PROOF-30
def test_check_exits_1_to_the_shell_when_a_pin_is_behind(workspace):
    """The exit code a caller's shell sees, from the script run as a process."""
    _add(workspace)
    _advance(workspace)
    code, _out = _cli(workspace, ['sync', '--check'], child=True)
    assert code == 1


# purlin: upstream PROOF-31
def test_check_exits_2_for_an_anchor_that_does_not_exist(workspace):
    _add(workspace)
    code, out = _cli(workspace, ['sync', 'absent', '--check', '--json'])
    assert code == 2
    row = json.loads(out)['anchors'][0]
    assert row['status'] == 'error'
    assert row['error'] == 'no anchor named absent carries a git source'


# purlin: upstream PROOF-32
def test_check_exits_2_when_the_source_is_gone(workspace):
    _add(workspace)
    _rmtree(workspace.anchor_repo)
    code, out = _cli(workspace, ['sync', '--check', '--json'])
    assert code == 2
    assert json.loads(out)['anchors'][0]['status'] == 'error'


# purlin: upstream PROOF-10
def test_json_on_a_current_pin_is_one_object(workspace):
    _add(workspace)
    code, out = _cli(workspace, ['sync', '--check', '--json'])
    assert code == 0
    assert len(out.splitlines()) == 1
    payload = json.loads(out)
    assert payload['checked'] is True
    assert payload['behind'] == 0
    assert [row['status'] for row in payload['anchors']] == ['current']


# purlin: upstream PROOF-33
def test_json_when_behind_carries_both_shas(workspace):
    _add(workspace)
    new_sha = _advance(workspace)
    code, out = _cli(workspace, ['sync', '--check', '--json'])
    assert code == 1
    payload = json.loads(out)
    assert payload['checked'] is True
    assert payload['behind'] == 1
    assert len(payload['anchors']) == 1
    assert payload['anchors'][0]['pinned'] == workspace.first_sha
    assert payload['anchors'][0]['remote_sha'] == new_sha


# purlin: upstream PROOF-34
def test_text_when_behind_names_the_sync_that_fixes_it(workspace):
    _add(workspace)
    new_sha = _advance(workspace)
    code, out = _cli(workspace, ['sync', '--check'])
    assert code == 1
    assert out.splitlines() == [
        'no_eval: the pin %s is behind its source, now %s. Run purlin:anchor '
        'sync no_eval.' % (workspace.first_sha[:7], new_sha[:7])]


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------

# purlin: upstream PROOF-11
def test_sync_advances_the_pin_and_names_the_rule_delta(workspace):
    _add(workspace)
    new_sha = _advance(workspace)

    result = upstream.sync(workspace.root, names=['no_eval'])
    row = result['anchors'][0]
    assert row['status'] == 'synced'
    assert row['previous'] == workspace.first_sha
    assert row['pinned'] == new_sha
    assert row['rule_changes'] == {'added': ['RULE-3'], 'removed': [],
                                   'changed': ['RULE-2']}
    assert row['summary'] == 'RULE-2 changed, RULE-3 added'

    lines = _copy_text(workspace).splitlines()
    assert '> Pinned: %s' % new_sha in lines
    assert '- RULE-3: No compile() in source files' in lines


# purlin: upstream PROOF-35
def test_sync_reports_a_removed_rule(workspace):
    _add(workspace)
    _advance(workspace, ANCHOR_V1.replace(
        '- RULE-2: No exec() in source files\n', ''))
    row = upstream.sync(workspace.root, names=['no_eval'])['anchors'][0]
    assert row['rule_changes'] == {'added': [], 'removed': ['RULE-2'],
                                   'changed': []}
    assert row['summary'] == 'RULE-2 removed'
    assert not any(line.startswith('- RULE-2:')
                   for line in _copy_text(workspace).splitlines())


# purlin: upstream PROOF-36
def test_sync_from_the_command_line_prints_the_delta(workspace):
    _add(workspace)
    new_sha = _advance(workspace)
    code, out = _cli(workspace, ['sync', 'no_eval'])
    assert code == 0
    assert out.splitlines() == [
        'no_eval: RULE-2 changed, RULE-3 added. Pin advanced from %s to %s.'
        % (workspace.first_sha[:7], new_sha[:7])]


# purlin: upstream PROOF-39
def test_a_source_with_crlf_endings_syncs_to_a_copy_with_no_carriage_return(
        workspace):
    _add(workspace)
    _git(['config', 'core.autocrlf', 'false'], workspace.anchor_work)
    path = os.path.join(workspace.anchor_work, 'specs', 'no_eval.md')
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        handle.write(ANCHOR_V2.replace('\n', '\r\n'))
    new_sha = _publish(workspace.anchor_work, 'publish with CRLF endings')
    published = subprocess.run(
        ['git', 'show', 'HEAD:specs/no_eval.md'], cwd=workspace.anchor_work,
        capture_output=True, check=True).stdout
    assert b'\r\n' in published

    upstream.sync(workspace.root, names=['no_eval'])
    with open(upstream.anchor_path(workspace.root, 'no_eval'), 'rb') as handle:
        copy = handle.read()
    assert ('> Pinned: %s\n' % new_sha).encode('ascii') in copy
    assert b'\r' not in copy


# purlin: upstream PROOF-12
def test_sync_says_so_when_only_the_prose_moved(workspace):
    _add(workspace)
    new_sha = _advance(workspace, ANCHOR_V1.replace('production code.',
                                                    'production code, ever.'))
    row = upstream.sync(workspace.root, names=['no_eval'])['anchors'][0]
    assert row['summary'] == 'no rule changes'
    assert row['rule_changes'] == {'added': [], 'removed': [], 'changed': []}
    assert row['pinned'] == new_sha
    assert '> Pinned: %s' % new_sha in _copy_text(workspace).splitlines()


# purlin: upstream PROOF-15
def test_check_reaches_a_shared_source_once(workspace, started):
    """Two anchors from one repository is one process naming it, not two."""
    _add(workspace)
    upstream.add(workspace.root, workspace.anchor_repo,
                 path='specs/no_secrets.md')
    del started[:]
    result = upstream.sync(workspace.root, check=True)
    assert len(result['anchors']) == 2
    reached = [args for args in started if workspace.anchor_repo in args]
    assert len(reached) == 1, started


# purlin: upstream PROOF-38
def test_sync_fetches_a_shared_source_once(workspace, started):
    """Two anchors behind on one repository is one clone of it, not two."""
    _add(workspace)
    upstream.add(workspace.root, workspace.anchor_repo,
                 path='specs/no_secrets.md')
    _advance(workspace)
    del started[:]
    result = upstream.sync(workspace.root)
    assert [row['status'] for row in result['anchors']] == ['synced',
                                                             'synced']
    clones = [args for args in started
              if args[:2] == ['git', 'clone'] and workspace.anchor_repo in args]
    assert len(clones) == 1, started


# ---------------------------------------------------------------------------
# The command line itself
# ---------------------------------------------------------------------------

# purlin: upstream PROOF-21
def test_help_names_both_commands():
    result = subprocess.run([sys.executable, UPSTREAM_PY, '--help'],
                            capture_output=True, text=True)
    assert result.returncode == 0
    for command in ('add', 'sync'):
        assert command in result.stdout


# purlin: upstream PROOF-37
def test_a_call_with_no_arguments_exits_2_naming_the_project_root(workspace):
    code, out = _child([], cwd=workspace.root)
    assert code == 2
    assert '--project-root' in out

    inline = io.StringIO()
    with contextlib.redirect_stdout(inline):
        assert upstream.main([]) == 2
    assert '--project-root' in inline.getvalue()


# purlin: upstream PROOF-22
def test_nothing_is_written_outside_the_project_root(workspace):
    _add(workspace)
    _advance(workspace)
    upstream.sync(workspace.root, names=['no_eval'])
    parent = os.path.dirname(workspace.root)
    assert sorted(os.listdir(parent)) == [
        'policies.git', 'policies_work', 'project', 'project.git']


# ---------------------------------------------------------------------------
# A source that is not a spec in Purlin's format kept in a git repository
# ---------------------------------------------------------------------------

POLICY = 'Every refund is countersigned by a second person.\n'

REFUNDS = """# Anchor: refunds

> Source: %s
> Pinned: 0123456789ab

## Rules

- RULE-1: Every refund is countersigned by a second person

## Proof

- PROOF-1 (RULE-1): A refund of 10.00 waits for a second person @manual
"""


def _without_anchor_folder(workspace):
    """The project as a new one is: `specs/_anchors/` not made yet."""
    os.rmdir(os.path.join(workspace.root, 'specs', '_anchors'))


def _runtime_files(workspace):
    """Every file under `.purlin/runtime/anchors/`, the fetched checkouts."""
    runtime = os.path.join(workspace.root, '.purlin', 'runtime', 'anchors')
    return [os.path.join(folder, name)
            for folder, _dirs, names in os.walk(runtime) for name in names]


def _hand_anchor(workspace, source):
    """An anchor already in the project whose `> Source:` is `source`."""
    path = upstream.anchor_path(workspace.root, 'refunds')
    _write(path, REFUNDS % source)
    with open(path, 'rb') as handle:
        return handle.read()


def _refused(what):
    return ("refunds: not added. %s is not a spec in Purlin's format kept in "
            "a git repository. Run purlin:anchor create refunds to write its "
            "rules in this project." % what)


def _not_a_spec(source):
    return ("refunds: its source, %s, is not a spec in Purlin's format kept in "
            "a git repository, so it cannot be checked. Run purlin:spec "
            "refunds to take out its > Source: and > Pinned: lines and keep it "
            "as this project's own anchor." % source)


# purlin: upstream PROOF-40
def test_add_refuses_a_text_file_in_the_project(workspace, started):
    _write(os.path.join(workspace.root, 'policy.txt'), POLICY)
    _without_anchor_folder(workspace)
    before = _files(os.path.join(workspace.root, 'specs'))
    del started[:]
    code, out = _cli(workspace, ['add', 'policy.txt', '--name', 'refunds'])
    assert code == 2
    assert out.splitlines() == [_refused('policy.txt')]
    assert started == [], started
    assert not os.path.exists(os.path.join(workspace.root, 'specs', '_anchors'))
    assert _files(os.path.join(workspace.root, 'specs')) == before


# purlin: upstream PROOF-41
def test_add_refuses_a_description_in_words(workspace, started):
    _without_anchor_folder(workspace)
    del started[:]
    code, out = _cli(workspace, ['add', 'Every refund is countersigned',
                                 '--name', 'refunds'])
    assert code == 2
    assert out.splitlines() == [_refused('The description given')]
    assert started == [], started
    assert not os.path.exists(os.path.join(workspace.root, 'specs', '_anchors'))


# purlin: upstream PROOF-42
def test_add_refuses_a_repository_file_that_holds_no_rule(workspace):
    _write(os.path.join(workspace.anchor_work, 'docs', 'refunds.md'),
           '# Refunds\n\n' + POLICY)
    _publish(workspace.anchor_work, 'publish the refunds policy as prose')
    _without_anchor_folder(workspace)
    code, out = _cli(workspace, ['add', workspace.anchor_repo, '--path',
                                 'docs/refunds.md', '--name', 'refunds'])
    assert code == 2
    assert out.splitlines() == [_refused('docs/refunds.md')]
    assert not os.path.exists(os.path.join(workspace.root, 'specs', '_anchors'))
    assert _runtime_files(workspace) == []


# purlin: upstream PROOF-43
def test_check_reports_an_anchor_from_a_text_file_as_error(workspace, started):
    _write(os.path.join(workspace.root, 'policy.txt'), POLICY)
    _hand_anchor(workspace, 'policy.txt')
    before = _files(workspace.root)
    del started[:]
    code, out = _cli(workspace, ['sync', '--check'])
    assert code == 2
    assert out.splitlines() == [_not_a_spec('policy.txt')]
    assert started == [], started
    assert _files(workspace.root) == before


# purlin: upstream PROOF-44
def test_sync_by_name_reports_an_anchor_from_words_as_error(workspace,
                                                            started):
    words = 'Every refund is countersigned'
    held = _hand_anchor(workspace, words)
    del started[:]
    code, out = _cli(workspace, ['sync', 'refunds', '--json'])
    assert code == 2
    row = json.loads(out)['anchors'][0]
    assert row['status'] == 'error'
    assert row['not_a_spec'] is True
    assert 'refunds: %s' % row['error'] == _not_a_spec(words)
    assert started == [], started
    with open(upstream.anchor_path(workspace.root, 'refunds'), 'rb') as handle:
        assert handle.read() == held


# purlin: upstream PROOF-45
def test_sync_all_reports_the_text_file_anchor_and_syncs_the_others(
        workspace, started):
    _add(workspace)
    upstream.add(workspace.root, workspace.anchor_repo,
                 path='specs/no_secrets.md')
    _write(os.path.join(workspace.root, 'policy.txt'), POLICY)
    held = _hand_anchor(workspace, 'policy.txt')
    _advance(workspace)
    del started[:]
    code, out = _cli(workspace, ['sync', '--json'])
    assert code == 2
    rows = {row['anchor']: row['status']
            for row in json.loads(out)['anchors']}
    assert rows == {'no_eval': 'synced', 'no_secrets': 'synced',
                    'refunds': 'error'}
    assert not any('policy.txt' in ' '.join(args) for args in started), started
    with open(upstream.anchor_path(workspace.root, 'refunds'), 'rb') as handle:
        assert handle.read() == held
