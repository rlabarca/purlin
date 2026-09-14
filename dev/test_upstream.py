"""Tests for scripts/anchor/upstream.py: anchors pulled from an anchor repo.

Two local bare repositories stand in for the two sides of the workflow: an
anchor repo that publishes `specs/no_eval.md` plus a design, and the origin the
consuming project was cloned from. Nothing here reaches a network; every url is
a path to a bare repository on disk.

What the tests hold:

`add`      writes the local copy with `> Source:` and `> Pinned:`, derives a
           name when none is given, and turns a free-text source into a copy
           carrying a note instead of rules
`sync`     reports the rule delta, advances the pin, copies the designs the
           source names, and reaches each source once per run
`--check`  changes nothing and exits 1 when a pin is behind
`propose`  writes the patch the anchor repo needs and names the right command
           for the git host
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'anchor'))

import upstream  # noqa: E402

UPSTREAM_PY = os.path.join(ROOT, 'scripts', 'anchor', 'upstream.py')

ANCHOR_V1 = """# Anchor: no_eval

> Description: No dynamic code execution in production code.
> Type: security

## Rules

- RULE-1: No eval() in source files [risk: high]
- RULE-2: No exec() in source files [risk: high]

## Proof

- PROOF-1 (RULE-1): Grep src/ for "eval("; verify zero matches
- PROOF-2 (RULE-2): Grep src/ for "exec("; verify zero matches
"""

ANCHOR_V2 = """# Anchor: no_eval

> Description: No dynamic code execution in production code.
> Type: security

The mocks this anchor pins are designs/checkout/cart.png.

## Rules

- RULE-1: No eval() in source files [risk: high]
- RULE-2: No exec() anywhere in the tree [risk: high]
- RULE-3: No compile() in source files [risk: medium]

## Proof

- PROOF-1 (RULE-1): Grep src/ for "eval("; verify zero matches
- PROOF-2 (RULE-2): Grep src/ for "exec("; verify zero matches
- PROOF-3 (RULE-3): Grep src/ for "compile("; verify zero matches
"""

SECOND_ANCHOR = """# Anchor: no_secrets

## Rules

- RULE-1: No credential literals in source files [risk: high]

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
    _write(os.path.join(anchor_work, 'designs', 'checkout', 'cart.png'), 'png')
    first = _publish(anchor_work, 'publish the security anchors')

    project_bare = _bare(os.path.join(base, 'project.git'))
    root = _clone(project_bare, os.path.join(base, 'project'))
    _write(os.path.join(root, '.purlin', 'config.json'), '{"gate": "tested"}\n')
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


def _cli(workspace, args):
    """Run the command line in a subprocess. Returns `(exit_code, stdout)`."""
    result = subprocess.run(
        [sys.executable, UPSTREAM_PY, '--project-root', workspace.root] + args,
        capture_output=True, text=True)
    return result.returncode, result.stdout


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

@pytest.mark.proof("upstream", "PROOF-1", "RULE-1", tier="integration")
def test_add_writes_the_copy_with_source_and_pin(workspace):
    result = _add(workspace)
    assert result['status'] == 'added'
    assert result['pinned'] == workspace.first_sha
    text = _copy_text(workspace)
    assert '> Source: %s specs/no_eval.md' % workspace.anchor_repo in text
    assert '> Pinned: %s' % workspace.first_sha in text
    # The author's body survives whole, and the tracking fields sit under the
    # title rather than replacing anything the author wrote.
    assert '- RULE-1: No eval() in source files [risk: high]' in text
    assert text.startswith('# Anchor: no_eval\n')
    assert result['rules'] == ['RULE-1', 'RULE-2']


@pytest.mark.proof("upstream", "PROOF-2", "RULE-2", tier="integration")
def test_add_pins_a_commit_not_a_branch(workspace):
    result = _add(workspace)
    head = _git(['rev-parse', 'HEAD'], workspace.anchor_work)
    assert result['pinned'] == head
    assert len(result['pinned']) == 40
    assert 'main' not in _copy_text(workspace).split('## Rules')[0]


@pytest.mark.proof("upstream", "PROOF-3", "RULE-3", tier="integration")
def test_add_derives_the_name_from_the_path(workspace):
    result = upstream.add(workspace.root, workspace.anchor_repo,
                          path='specs/no_secrets.md')
    assert result['anchor'] == 'no_secrets'
    assert os.path.isfile(upstream.anchor_path(workspace.root, 'no_secrets'))


@pytest.mark.proof("upstream", "PROOF-4", "RULE-4", tier="integration")
def test_add_strips_the_tracking_fields_the_source_carried(workspace):
    """A source that is itself a consumer copy must not bring its pin along."""
    _write(os.path.join(workspace.anchor_work, 'specs', 'no_eval.md'),
           ANCHOR_V1.replace(
               '> Type: security',
               '> Type: security\n> Source: git@example.com:other.git a.md\n'
               '> Pinned: deadbeef'))
    _publish(workspace.anchor_work, 'publish a copy that carries tracking')
    _add(workspace)
    text = _copy_text(workspace)
    assert text.count('> Source:') == 1
    assert text.count('> Pinned:') == 1
    assert 'deadbeef' not in text


@pytest.mark.proof("upstream", "PROOF-5", "RULE-5", tier="integration")
def test_add_reports_a_path_that_is_not_in_the_source(workspace):
    result = _add(workspace, path='specs/absent.md')
    assert result['status'] == 'error'
    assert 'specs/absent.md' in result['error']
    assert not os.path.isfile(upstream.anchor_path(workspace.root, 'no_eval'))


@pytest.mark.proof("upstream", "PROOF-6", "RULE-6", tier="integration")
def test_add_refuses_a_source_that_begins_with_a_dash(workspace):
    result = upstream.add(workspace.root, '--upload-pack=/bin/echo',
                          path='a.md', name='hostile')
    assert result['status'] == 'error'
    assert 'begins with "-"' in result['error']
    assert not os.path.isfile(upstream.anchor_path(workspace.root, 'hostile'))


@pytest.mark.proof("upstream", "PROOF-6", "RULE-6", tier="integration")
def test_add_refuses_an_ext_transport(workspace):
    result = upstream.add(workspace.root, 'ext::sh -c touch', path='a.md',
                          name='hostile')
    assert result['status'] == 'error'
    assert 'ext:: transport' in result['error']


# ---------------------------------------------------------------------------
# add: a free-text source
# ---------------------------------------------------------------------------

@pytest.mark.proof("upstream", "PROOF-7", "RULE-7", tier="integration")
def test_add_of_free_text_writes_a_note_and_no_rules(workspace):
    source = os.path.join(workspace.root, 'policy.txt')
    _write(source, 'Every refund is approved by a second person.\n')
    result = upstream.add(workspace.root, source, name='refunds')
    assert result['status'] == 'drafted'
    text = _copy_text(workspace, 'refunds')
    assert 'Every refund is approved by a second person.' in text
    assert upstream.FREE_TEXT_NOTE in text
    assert '## Rules' in text and '## Proof' in text
    assert 'RULE-' not in text
    # The pin is the hash of the text, so a reworded source stales the copy.
    assert result['pinned'] == upstream.add(
        workspace.root, source, name='refunds')['pinned']


@pytest.mark.proof("upstream", "PROOF-7", "RULE-7", tier="integration")
def test_free_text_is_not_mistaken_for_a_repository(workspace):
    """An absolute path to a file satisfies the git-url test as well, so the
    file has to win: a text file is not a repository."""
    source = os.path.join(workspace.root, 'policy.txt')
    _write(source, 'Nothing is deleted without a record.\n')
    is_free, text = upstream._free_text(workspace.root, source)
    assert is_free is True
    assert 'Nothing is deleted' in text
    assert upstream._free_text(workspace.root, workspace.anchor_repo)[0] is False


# ---------------------------------------------------------------------------
# sync --check
# ---------------------------------------------------------------------------

@pytest.mark.proof("upstream", "PROOF-9", "RULE-9", tier="integration")
def test_check_on_a_current_pin_reports_current(workspace):
    _add(workspace)
    result = upstream.sync(workspace.root, check=True)
    assert [row['status'] for row in result['anchors']] == ['current']
    assert result['behind'] == 0
    assert upstream._exit_code(result) == 0


@pytest.mark.proof("upstream", "PROOF-8", "RULE-8", tier="integration")
def test_check_when_behind_reports_and_changes_nothing(workspace):
    _add(workspace)
    before = _copy_text(workspace)
    new_sha = _advance(workspace)

    result = upstream.sync(workspace.root, check=True)
    row = result['anchors'][0]
    assert row['status'] == 'behind'
    assert row['pinned'] == workspace.first_sha
    assert row['remote_sha'] == new_sha
    assert result['behind'] == 1
    assert upstream._exit_code(result) == 1
    assert _copy_text(workspace) == before


@pytest.mark.proof("upstream", "PROOF-10", "RULE-10", tier="integration")
def test_check_exit_code_and_json_from_the_command_line(workspace):
    _add(workspace)
    code, out = _cli(workspace, ['sync', '--check', '--json'])
    assert code == 0
    assert json.loads(out)['behind'] == 0

    new_sha = _advance(workspace)
    code, out = _cli(workspace, ['sync', '--check', '--json'])
    assert code == 1
    payload = json.loads(out)
    assert payload['checked'] is True
    assert payload['behind'] == 1
    assert payload['anchors'][0]['remote_sha'] == new_sha

    code, out = _cli(workspace, ['sync', '--check'])
    assert code == 1
    assert 'is behind its source' in out
    assert 'purlin:anchor sync no_eval' in out


@pytest.mark.proof("upstream", "PROOF-9", "RULE-9", tier="integration")
def test_check_names_an_anchor_that_does_not_exist(workspace):
    result = upstream.sync(workspace.root, names=['absent'], check=True)
    assert result['anchors'][0]['status'] == 'error'
    assert upstream._exit_code(result) == 2


@pytest.mark.proof("upstream", "PROOF-9", "RULE-9", tier="integration")
def test_check_reports_an_unreachable_source(workspace, tmp_path):
    _add(workspace)
    shutil.rmtree(workspace.anchor_repo)
    result = upstream.sync(workspace.root, check=True)
    assert result['anchors'][0]['status'] == 'error'
    assert upstream._exit_code(result) == 2


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------

@pytest.mark.proof("upstream", "PROOF-11", "RULE-11", tier="integration")
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

    text = _copy_text(workspace)
    assert '> Pinned: %s' % new_sha in text
    assert '- RULE-3: No compile() in source files [risk: medium]' in text
    assert 'No exec() anywhere in the tree' in text


@pytest.mark.proof("upstream", "PROOF-11", "RULE-11", tier="integration")
def test_sync_reports_a_removed_rule(workspace):
    _add(workspace)
    _advance(workspace, ANCHOR_V1.replace(
        '- RULE-2: No exec() in source files [risk: high]\n', ''))
    row = upstream.sync(workspace.root, names=['no_eval'])['anchors'][0]
    assert row['rule_changes']['removed'] == ['RULE-2']
    assert row['summary'] == 'RULE-2 removed'


@pytest.mark.proof("upstream", "PROOF-12", "RULE-12", tier="integration")
def test_sync_says_so_when_only_the_prose_moved(workspace):
    _add(workspace)
    _advance(workspace, ANCHOR_V1.replace('production code.',
                                          'production code, ever.'))
    row = upstream.sync(workspace.root, names=['no_eval'])['anchors'][0]
    assert row['summary'] == 'no rule changes'
    assert row['pinned'] != workspace.first_sha


@pytest.mark.proof("upstream", "PROOF-13", "RULE-13", tier="integration")
def test_sync_copies_the_designs_the_source_names(workspace):
    _add(workspace)
    _advance(workspace)
    row = upstream.sync(workspace.root, names=['no_eval'])['anchors'][0]
    assert row['designs'] == ['designs/no_eval/cart.png']
    copied = os.path.join(workspace.root, 'designs', 'no_eval', 'cart.png')
    with open(copied, 'r', encoding='utf-8') as handle:
        assert handle.read() == 'png'


@pytest.mark.proof("upstream", "PROOF-13", "RULE-13", tier="integration")
def test_sync_leaves_designs_alone_when_the_source_names_none(workspace):
    _add(workspace)
    _advance(workspace, ANCHOR_V2.replace(
        'The mocks this anchor pins are designs/checkout/cart.png.\n', ''))
    row = upstream.sync(workspace.root, names=['no_eval'])['anchors'][0]
    assert row['designs'] == []
    assert not os.path.isdir(os.path.join(workspace.root, 'designs'))


@pytest.mark.proof("upstream", "PROOF-14", "RULE-14", tier="integration")
def test_sync_all_covers_every_git_sourced_anchor_and_no_others(workspace):
    _add(workspace)
    upstream.add(workspace.root, workspace.anchor_repo,
                 path='specs/no_secrets.md')
    free = os.path.join(workspace.root, 'policy.txt')
    _write(free, 'Every refund is approved by a second person.\n')
    upstream.add(workspace.root, free, name='refunds')

    result = upstream.sync(workspace.root)
    assert sorted(row['anchor'] for row in result['anchors']) == [
        'no_eval', 'no_secrets']


@pytest.mark.proof("upstream", "PROOF-15", "RULE-15", tier="integration")
def test_sync_reaches_each_source_once_per_run(workspace, monkeypatch):
    """Two anchors from one repo is one `git ls-remote`, not two."""
    _add(workspace)
    upstream.add(workspace.root, workspace.anchor_repo,
                 path='specs/no_secrets.md')
    calls = []
    real = upstream.drift_module._ls_remote

    def counting(project_root, url):
        calls.append(url)
        return real(project_root, url)

    monkeypatch.setattr(upstream.drift_module, '_ls_remote', counting)
    result = upstream.sync(workspace.root, check=True)
    assert len(result['anchors']) == 2
    assert calls == [workspace.anchor_repo]


@pytest.mark.proof("upstream", "PROOF-11", "RULE-11", tier="integration")
def test_sync_from_the_command_line_prints_the_delta(workspace):
    _add(workspace)
    _advance(workspace)
    code, out = _cli(workspace, ['sync', 'no_eval'])
    assert code == 0
    assert 'RULE-2 changed, RULE-3 added' in out
    assert 'design copied: designs/no_eval/cart.png' in out


# ---------------------------------------------------------------------------
# propose
# ---------------------------------------------------------------------------

def _add_local_rule(workspace):
    text = _copy_text(workspace).replace(
        '## Proof', '- RULE-9: No pickle imports [risk: low]\n\n## Proof')
    _write(upstream.anchor_path(workspace.root, 'no_eval'), text)


@pytest.mark.proof("upstream", "PROOF-16", "RULE-16", tier="integration")
def test_propose_writes_the_patch_the_anchor_repo_needs(workspace):
    _add(workspace)
    _add_local_rule(workspace)
    result = upstream.propose(workspace.root, 'no_eval')
    assert result['status'] == 'written'
    assert result['patch'] == '.purlin/runtime/anchors/no_eval.patch'
    with open(os.path.join(workspace.root, result['patch']), 'r',
              encoding='utf-8') as handle:
        patch = handle.read()
    assert '+- RULE-9: No pickle imports [risk: low]' in patch
    assert '--- a/specs/no_eval.md' in patch
    assert '+++ b/specs/no_eval.md' in patch
    # The tracking fields are the consumer's, so they never reach the patch.
    assert '> Pinned:' not in patch
    assert '> Source:' not in patch


@pytest.mark.proof("upstream", "PROOF-18", "RULE-18", tier="integration")
def test_propose_is_empty_when_the_copy_matches_the_pin(workspace):
    _add(workspace)
    result = upstream.propose(workspace.root, 'no_eval')
    assert result['status'] == 'empty'
    assert 'nothing to propose' in '\n'.join(upstream._render(result))


@pytest.mark.proof("upstream", "PROOF-17", "RULE-17", tier="integration")
def test_propose_reads_the_source_at_the_pin_not_at_its_head(workspace):
    _add(workspace)
    _add_local_rule(workspace)
    _advance(workspace)
    with open(os.path.join(workspace.root, upstream.propose(
            workspace.root, 'no_eval')['patch']), 'r', encoding='utf-8') as h:
        patch = h.read()
    # RULE-3 arrived after the pin, so proposing against the pin must not ask
    # the anchor repo to add a rule it already has.
    assert 'RULE-3' not in patch
    assert '+- RULE-9: No pickle imports [risk: low]' in patch


@pytest.mark.proof("upstream", "PROOF-19", "RULE-19", tier="integration")
def test_propose_names_the_command_for_the_git_host(workspace):
    _add(workspace)
    _add_local_rule(workspace)
    result = upstream.propose(workspace.root, 'no_eval')
    joined = ' '.join(result['commands'])
    assert 'git checkout -b purlin/no_eval' in joined
    assert 'gh pr create' in joined
    assert 'az repos pr create' in joined

    github = upstream._propose_commands(
        'https://github.com/acme/policies.git', 'no_eval', 'p.patch')
    assert github[-1] == 'gh pr create --fill'
    ado = upstream._propose_commands(
        'https://dev.azure.com/acme/_git/policies', 'no_eval', 'p.patch')
    assert ado[-1].startswith('az repos pr create')


@pytest.mark.proof("upstream", "PROOF-20", "RULE-20", tier="integration")
def test_propose_needs_a_pin(workspace):
    _write(upstream.anchor_path(workspace.root, 'loose'),
           '# Anchor: loose\n\n> Source: %s specs/no_eval.md\n\n## Rules\n\n'
           '- RULE-1: Something\n\n## Proof\n\n- PROOF-1 (RULE-1): Check it\n'
           % workspace.anchor_repo)
    result = upstream.propose(workspace.root, 'loose')
    assert result['status'] == 'error'
    assert 'no pin' in result['error']
    assert upstream._exit_code(result) == 2


# ---------------------------------------------------------------------------
# The command line itself
# ---------------------------------------------------------------------------

@pytest.mark.proof("upstream", "PROOF-21", "RULE-21", tier="integration")
def test_help_and_a_bare_call_are_usable(workspace):
    result = subprocess.run([sys.executable, UPSTREAM_PY, '--help'],
                            capture_output=True, text=True)
    assert result.returncode == 0
    for command in ('add', 'sync', 'propose'):
        assert command in result.stdout
    code, out = _cli(workspace, [])
    assert code == 2
    assert '--project-root' in out


@pytest.mark.proof("upstream", "PROOF-1", "RULE-1", tier="integration")
def test_add_from_the_command_line_writes_the_copy(workspace):
    code, out = _cli(workspace, ['add', workspace.anchor_repo, '--path',
                                 'specs/no_eval.md', '--name', 'no_eval'])
    assert code == 0
    assert 'specs/_anchors/no_eval.md' in out
    assert '> Pinned: %s' % workspace.first_sha in _copy_text(workspace)


@pytest.mark.proof("upstream", "PROOF-22", "RULE-22", tier="integration")
def test_nothing_written_outside_the_project_root(workspace):
    """Every path the module writes is under the project root it was given."""
    _add(workspace)
    _advance(workspace)
    upstream.sync(workspace.root, names=['no_eval'])
    parent = os.path.dirname(workspace.root)
    assert sorted(os.listdir(parent)) == [
        'policies.git', 'policies_work', 'project', 'project.git']
