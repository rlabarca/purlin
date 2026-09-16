"""Tests for `scripts/review/approve.py`: the triple, the file, the commit.

Every fixture is written by the test in a throwaway project: a spec, a test
file, a runtime proof file, a record, an approval. Nothing here reads this
repository's own specs, reaches a network, or signs with a key that exists
anywhere but the temporary directory the test made.

What each group holds:

*the triple*   the three hashes an approval binds, and what does and does not
               change them: reflowing a rule and re-tagging it do not, editing
               the rule, the proof or the test do
*stale*        an approval stops being current when any part of the triple or
               the risk moves under it
*the file*     the name, the fields, and the brief it points at
*auto*         CI approves low risk with a passing record and enough test
               strength, and nothing else: never medium or high, never below
               the minimum, never a manual proof, never twice
*the commit*   one signed commit for a batch, and the exact setup to print
               when this checkout cannot sign
*ancestor*     an approval on a side branch is not on the protected branch
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))

import approve as approve_module  # noqa: E402
from purlin import approvals as purlin_approvals  # noqa: E402
from purlin import payload as purlin_payload  # noqa: E402
from purlin import specs as purlin_specs  # noqa: E402

APPROVE_PY = os.path.join(ROOT, 'scripts', 'review', 'approve.py')


# ---------------------------------------------------------------------------
# The throwaway project
# ---------------------------------------------------------------------------

SPEC = (
    '# Feature: login\n\n'
    '> Description: Signing in with an email and a password.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: Valid credentials return 200 with a session token '
    '[risk: low]\n'
    '- RULE-2: Invalid credentials return 401 and the body "denied" '
    '[risk: high]\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /login with the password "secret"; verify 200 '
    'and a token @integration\n'
    '- PROOF-2 (RULE-2): POST /login with a bad password; verify 401 and the '
    'body "denied"\n'
)

TEST_FILE = (
    'import pytest\n'
    '\n'
    'from src.login import login\n'
    '\n'
    '\n'
    '@pytest.mark.proof("login", "PROOF-1", "RULE-1")\n'
    'def test_valid_credentials_return_200():\n'
    '    assert login("ada", "secret") == 200\n'
    '\n'
    '\n'
    '@pytest.mark.proof("login", "PROOF-2", "RULE-2")\n'
    'def test_a_bad_password_is_denied():\n'
    '    assert login("ada", "wrong") == 401\n'
)

TEST_NAMES = {'PROOF-1': 'test_valid_credentials_return_200',
              'PROOF-2': 'test_a_bad_password_is_denied'}


def git(root, *args):
    return subprocess.run(['git'] + list(args), cwd=root, capture_output=True,
                          text=True)


def write(path, text):
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


class Project(object):
    """A throwaway project: git, a config, one spec, one test file."""

    def __init__(self, spec=SPEC, gate='tested', config=None):
        self.root = tempfile.mkdtemp()
        settings = {'gate': gate, 'project_name': 'proj'}
        settings.update(config or {})
        write(os.path.join(self.root, '.purlin', 'config.json'),
              json.dumps(settings))
        write(os.path.join(self.root, '.gitignore'), '.purlin/runtime/\n')
        write(os.path.join(self.root, 'specs', 'auth', 'login.md'), spec)
        write(os.path.join(self.root, 'src', 'login.py'),
              'def login(user, password):\n'
              '    return 200 if password == "secret" else 401\n')
        write(os.path.join(self.root, 'tests', 'test_login.py'), TEST_FILE)
        git(self.root, 'init', '-q', '-b', 'main')
        git(self.root, 'config', 'user.email', 'dev@example.com')
        git(self.root, 'config', 'user.name', 'Dev')
        git(self.root, 'config', 'commit.gpgsign', 'false')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-q', '-m', 'chore: project under test')

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def head(self):
        return git(self.root, 'rev-parse', 'HEAD').stdout.strip()

    def spec(self, text, name='login', category='auth'):
        write(os.path.join(self.root, 'specs', category, name + '.md'), text)

    def edit_test(self, text):
        write(os.path.join(self.root, 'tests', 'test_login.py'), text)
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-q', '-m', 'test(login): edit')

    def config(self, **fields):
        path = os.path.join(self.root, '.purlin', 'config.json')
        with open(path, encoding='utf-8') as handle:
            settings = json.load(handle)
        settings.update(fields)
        write(path, json.dumps(settings))

    def proofs(self, statuses=None, tier='unit'):
        statuses = statuses or {'PROOF-1': 'pass', 'PROOF-2': 'pass'}
        entries = []
        for proof_id, status in sorted(statuses.items()):
            entries.append({
                'feature': 'login', 'id': proof_id,
                'rule': 'RULE-1' if proof_id == 'PROOF-1' else 'RULE-2',
                'status': status, 'tier': tier,
                'test_file': 'tests/test_login.py',
                'test_name': TEST_NAMES[proof_id]})
        write(os.path.join(self.root, '.purlin', 'runtime', 'proofs',
                           'login.%s.json' % tier),
              json.dumps({'tier': tier, 'proofs': entries}))

    def record(self, statuses=None, runner='ada', strength=90,
               commit_it=True, stamp='20260913T120000Z', tests=None):
        """Write a record naming the tests the runtime proofs name.

        `tests` maps a proof to the test names the record observed for it, for
        a proof backed by more than one test.
        """
        statuses = statuses or {'PROOF-1': 'pass', 'PROOF-2': 'pass'}
        proofs = []
        for proof_id, status in sorted(statuses.items()):
            for test_name in (tests or {}).get(proof_id,
                                               [TEST_NAMES[proof_id]]):
                proofs.append({
                    'id': proof_id,
                    'rule': 'RULE-1' if proof_id == 'PROOF-1' else 'RULE-2',
                    'status': status, 'tier': 'unit', 'env': None,
                    'test_file': 'tests/test_login.py',
                    'test_name': test_name})
        name = '%s-%s-%s.json' % (stamp, self.head()[:7], runner)
        rel = '.purlin/records/login/' + name
        iso = '%s-%s-%sT%s:%s:%sZ' % (stamp[0:4], stamp[4:6], stamp[6:8],
                                      stamp[9:11], stamp[11:13], stamp[13:15])
        write(os.path.join(self.root, rel), json.dumps({
            'schema_version': 1, 'feature': 'login', 'commit': self.head(),
            'timestamp': iso, 'runner': runner,
            'os': None, 'gate': 'tested', 'test_strength': strength,
            'scope_tree': purlin_specs.scope_tree(self.root, ['src/login.py']),
            'proofs': proofs}))
        if commit_it:
            git(self.root, 'add', '-A')
            git(self.root, 'commit', '-q', '-m', 'purlin: record for abc1234')
        return rel

    def payload(self):
        return purlin_payload.build_payload(self.root)

    def rule(self, rule_id):
        data = self.payload()
        entry = next(f for f in data['features'] if f['name'] == 'login')
        return next(r for r in entry['rules'] if r['id'] == rule_id)

    def approvals(self):
        directory = os.path.join(self.root, 'specs', 'auth', 'login.approvals')
        if not os.path.isdir(directory):
            return []
        return sorted(os.listdir(directory))


@pytest.fixture
def project():
    made = Project()
    yield made
    made.close()


@pytest.fixture
def proved():
    """A project whose rules are recorded, so an approval has something to bind."""
    made = Project()
    made.proofs()
    made.record()
    yield made
    made.close()


def signing_key(root, email='jane@acme.com'):
    """A throwaway ssh signing key, configured in this checkout alone."""
    key = os.path.join(root, '.git', 'signing-key')
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', email,
                    '-f', key], check=True)
    with open(key + '.pub', encoding='utf-8') as handle:
        public = handle.read().strip()
    allowed = os.path.join(root, '.git', 'allowed-signers')
    write(allowed, '%s %s\n' % (email, public))
    for name, value in (('user.email', email), ('user.name', 'Jane'),
                        ('gpg.format', 'ssh'),
                        ('user.signingkey', key + '.pub'),
                        ('commit.gpgsign', 'true'),
                        ('gpg.ssh.allowedSignersFile', allowed)):
        git(root, 'config', name, value)
    return key + '.pub'


# ---------------------------------------------------------------------------
# The triple
# ---------------------------------------------------------------------------

class TestTheTriple:

    @pytest.mark.proof("approvals", "PROOF-1", "RULE-1", tier="integration")
    def test_the_three_hashes_come_back_with_their_kind(self, proved):
        parts = approve_module.rule_proof_test_hashes(
            proved.root, 'login', 'RULE-1')
        rule_hash, proof_hash, test_hash, kind, design = parts
        assert len(rule_hash) == 64 and len(proof_hash) == 64
        assert len(test_hash) == 64
        assert kind == 'file'
        assert design is None

    @pytest.mark.proof("approvals", "PROOF-2", "RULE-2", tier="integration")
    def test_a_rule_that_is_not_there_has_no_hashes(self, proved):
        assert approve_module.rule_proof_test_hashes(
            proved.root, 'login', 'RULE-99') == (None, None, None, None, None)

    @pytest.mark.proof("approvals", "PROOF-3", "RULE-3", tier="integration")
    def test_reflowing_a_rule_and_re_tagging_it_keep_the_triple(self, proved):
        before = approve_module.triple_for(proved.rule('RULE-1'))
        proved.spec(SPEC.replace(
            '- RULE-1: Valid credentials return 200 with a session token '
            '[risk: low]',
            '- RULE-1: Valid   credentials  return 200  with a session token '
            '[origin: pm] [risk: low]'))
        after = approve_module.triple_for(proved.rule('RULE-1'))
        assert after == before, (
            'reflowing a rule or re-tagging it must not stale its approval')

    @pytest.mark.proof("approvals", "PROOF-4", "RULE-4", tier="integration")
    def test_editing_the_rule_the_proof_or_the_test_moves_the_triple(
            self, proved):
        before = approve_module.triple_for(proved.rule('RULE-1'))

        proved.spec(SPEC.replace('return 200 with a session token',
                                 'return 201 with a session token'))
        rule_changed = approve_module.triple_for(proved.rule('RULE-1'))
        assert rule_changed != before

        proved.spec(SPEC.replace('verify 200 and a token',
                                 'verify 200 and a token that expires'))
        proof_changed = approve_module.triple_for(proved.rule('RULE-1'))
        assert proof_changed != before

        proved.spec(SPEC)
        proved.edit_test(TEST_FILE.replace('== 200', '== 200  # checked'))
        test_changed = approve_module.triple_for(proved.rule('RULE-1'))
        assert test_changed != before

    @pytest.mark.proof("approvals", "PROOF-5", "RULE-5", tier="integration")
    def test_a_manual_proof_says_so_instead_of_naming_a_file(self):
        made = Project(spec=SPEC.replace(
            'verify 401 and the body "denied"',
            'verify 401 and the body "denied" @manual'))
        try:
            parts = approve_module.rule_proof_test_hashes(
                made.root, 'login', 'RULE-2')
            assert parts[3] == 'manual'
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Stale
# ---------------------------------------------------------------------------

class TestStale:

    def _approve(self, project, rule='RULE-1'):
        entry = project.rule(rule)
        return approve_module.write_approval(
            project.root, 'login', rule, 'jane@acme.com', None, None,
            'tested', entry['risk'], entry=entry)

    def _current(self, project, rule='RULE-1'):
        entry = project.rule(rule)
        loaded = purlin_approvals.load_approvals(
            project.root, purlin_specs.scan_specs(project.root))
        found = loaded.get(('login', rule)) or []
        return [a for a in found
                if purlin_approvals.is_current(
                    a, entry['rule_hash'], entry['proof_hash'],
                    entry['test_hash'], entry['risk'], entry['design_hash'])]

    @pytest.mark.proof("approvals", "PROOF-6", "RULE-6", tier="integration")
    def test_a_fresh_approval_is_current(self, proved):
        self._approve(proved)
        assert len(self._current(proved)) == 1

    @pytest.mark.proof("approvals", "PROOF-7", "RULE-6", tier="integration")
    def test_the_rule_text_changing_stales_it(self, proved):
        self._approve(proved)
        proved.spec(SPEC.replace('return 200 with a session token',
                                 'return 200 with a signed session token'))
        assert self._current(proved) == []

    @pytest.mark.proof("approvals", "PROOF-8", "RULE-6", tier="integration")
    def test_the_proof_text_changing_stales_it(self, proved):
        self._approve(proved)
        proved.spec(SPEC.replace('verify 200 and a token',
                                 'verify 200, a token and a cookie'))
        assert self._current(proved) == []

    @pytest.mark.proof("approvals", "PROOF-9", "RULE-6", tier="integration")
    def test_the_test_changing_stales_it(self, proved):
        self._approve(proved)
        proved.edit_test(TEST_FILE.replace('== 200', '== 200 or True'))
        assert self._current(proved) == []

    @pytest.mark.proof("approvals", "PROOF-10", "RULE-6", tier="integration")
    def test_the_risk_changing_stales_it(self, proved):
        self._approve(proved)
        proved.spec(SPEC.replace(
            '- RULE-1: Valid credentials return 200 with a session token '
            '[risk: low]',
            '- RULE-1: Valid credentials return 200 with a session token '
            '[risk: high]'))
        assert self._current(proved) == [], (
            'raising a rule from low to high changes what approving it meant')

    @pytest.mark.proof("approvals", "PROOF-11", "RULE-7", tier="integration")
    def test_a_stale_approval_puts_the_rule_in_stale(self, proved):
        self._approve(proved)
        assert proved.rule('RULE-1')['state'] == 'Approved'
        proved.spec(SPEC.replace('return 200 with a session token',
                                 'return 200 with two session tokens'))
        assert proved.rule('RULE-1')['state'] == 'Stale'


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------

class TestTheFile:

    @pytest.mark.proof("approvals", "PROOF-12", "RULE-8", tier="integration")
    def test_the_name_carries_the_rule_the_triple_and_the_slug(self, proved):
        entry = proved.rule('RULE-1')
        triple = approve_module.triple_for(entry)
        approve_module.write_approval(
            proved.root, 'login', 'RULE-1', 'Rich.LaBarca+purlin@example.com',
            None, None, 'tested', 'low', entry=entry)
        assert proved.approvals() == [
            'RULE-1.%s.rich-labarca-purlin.json' % triple[:8]]

    @pytest.mark.proof("approvals", "PROOF-13", "RULE-9", tier="integration")
    def test_the_fields_are_the_ones_the_format_names(self, proved):
        entry = proved.rule('RULE-1')
        record = proved.record()
        path = approve_module.write_approval(
            proved.root, 'login', 'RULE-1', 'jane@acme.com',
            'specs/auth/login.approvals/RULE-1.brief.json', record,
            'recorded', 'low', entry=entry)
        with open(os.path.join(proved.root, path), encoding='utf-8') as handle:
            data = json.load(handle)
        assert data['schema'] == 'purlin-approval/1'
        assert set(data) == {
            'schema', 'feature', 'rule', 'triple', 'rule_hash', 'proof_hash',
            'test_hash', 'test_hash_kind', 'design_hash', 'risk', 'approver',
            'timestamp', 'gate', 'brief', 'record'}
        assert data['feature'] == 'login' and data['rule'] == 'RULE-1'
        assert data['triple'] == approve_module.triple_for(entry)[:16]
        assert data['approver'] == 'jane@acme.com'
        assert data['gate'] == 'recorded' and data['risk'] == 'low'
        assert data['record'] == record
        assert data['timestamp'].endswith('Z')

    @pytest.mark.proof("approvals", "PROOF-14", "RULE-10", tier="integration")
    def test_the_reader_finds_it_and_never_reads_a_brief_as_one(self, proved):
        entry = proved.rule('RULE-1')
        approve_module.write_approval(
            proved.root, 'login', 'RULE-1', 'jane@acme.com', None, None,
            'tested', 'low', entry=entry)
        triple = approve_module.triple_for(entry)
        write(os.path.join(proved.root, 'specs', 'auth', 'login.approvals',
                           'RULE-1.%s.brief.json' % triple[:8]),
              json.dumps({'schema': 'purlin-brief/1', 'rule': 'RULE-1'}))
        loaded = purlin_approvals.load_approvals(
            proved.root, purlin_specs.scan_specs(proved.root))
        assert len(loaded[('login', 'RULE-1')]) == 1
        assert loaded[('login', 'RULE-1')][0]['approver'] == 'jane@acme.com'


# ---------------------------------------------------------------------------
# CI auto-approval
# ---------------------------------------------------------------------------

class TestAutoApproval:

    @pytest.mark.proof("approvals", "PROOF-15", "RULE-11", tier="integration")
    def test_low_risk_with_a_passing_record_and_enough_strength(self, proved):
        written = approve_module.auto_approve(proved.root)
        assert len(written) == 1, written
        assert written[0].endswith('.ci.json')
        with open(os.path.join(proved.root, written[0]),
                  encoding='utf-8') as handle:
            data = json.load(handle)
        assert data['approver'] == 'ci' and data['risk'] == 'low'
        assert data['record'].startswith('.purlin/records/login/')

    @pytest.mark.proof("approvals", "PROOF-16", "RULE-12", tier="integration")
    def test_high_risk_is_never_auto_approved(self, proved):
        written = approve_module.auto_approve(proved.root)
        assert [path for path in written if 'RULE-2' in path] == [], (
            'RULE-2 is high risk and needs a person')

    @pytest.mark.proof("approvals", "PROOF-17", "RULE-13", tier="integration")
    def test_below_the_minimum_strength_nothing_is_written(self):
        made = Project(config={'min_strength': 70})
        try:
            made.proofs()
            made.record(strength=30)
            assert approve_module.auto_approve(made.root) == []
            made.record(strength=95, stamp='20260913T130000Z')
            assert len(approve_module.auto_approve(made.root)) == 1
        finally:
            made.close()

    @pytest.mark.proof("approvals", "PROOF-18", "RULE-14", tier="integration")
    def test_a_failing_record_is_not_auto_approved(self):
        made = Project()
        try:
            made.proofs({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
            made.record({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
            assert approve_module.auto_approve(made.root) == []
        finally:
            made.close()

    @pytest.mark.proof("approvals", "PROOF-19", "RULE-15", tier="integration")
    def test_a_manual_proof_is_never_auto_approved(self):
        made = Project(spec=SPEC.replace(
            'verify 200 and a token @integration',
            'verify 200 and a token @manual'))
        try:
            made.proofs()
            made.record()
            assert approve_module.auto_approve(made.root) == [], (
                'the evidence for a manual proof is a person\'s note')
        finally:
            made.close()

    @pytest.mark.proof("approvals", "PROOF-20", "RULE-16", tier="integration")
    def test_a_rule_already_approved_is_left_alone(self, proved):
        entry = proved.rule('RULE-1')
        approve_module.write_approval(
            proved.root, 'login', 'RULE-1', 'jane@acme.com', None, None,
            'tested', 'low', entry=entry)
        assert approve_module.auto_approve(proved.root) == []


# ---------------------------------------------------------------------------
# The signed commit
# ---------------------------------------------------------------------------

class TestTheSignedCommit:

    @pytest.mark.proof("approvals", "PROOF-21", "RULE-17", tier="integration")
    def test_without_signing_the_setup_is_printed_and_nothing_is_written(
            self, proved, capsys):
        code = approve_module.main(['login', '--project-root', proved.root])
        output = capsys.readouterr().out
        assert code == 1
        assert 'git config gpg.format ssh' in output
        assert 'git config user.signingkey ~/.ssh/id_ed25519.pub' in output
        assert 'git config commit.gpgsign true' in output
        assert proved.approvals() == []

    @pytest.mark.proof("approvals", "PROOF-23", "RULE-18", tier="integration")
    def test_one_signed_commit_carries_the_batch(self, proved, capsys):
        signing_key(proved.root)
        code = approve_module.main(['login', '--project-root', proved.root])
        capsys.readouterr()
        assert code == 0
        assert len(proved.approvals()) == 2
        log = git(proved.root, 'log', '-1', '--format=%G?%n%s').stdout
        signature, subject = log.strip().splitlines()
        assert signature == 'G', log
        assert subject == 'approve(login): RULE-2 RULE-1', subject

    @pytest.mark.proof("approvals", "PROOF-25", "RULE-20", tier="integration")
    def test_the_counted_approval_needs_the_signature_and_the_list(
            self, proved):
        signing_key(proved.root)
        approve_module.main(['login', 'RULE-1', '--project-root', proved.root])
        loaded = purlin_approvals.load_approvals(
            proved.root, purlin_specs.scan_specs(proved.root))
        approval = loaded[('login', 'RULE-1')][0]
        counted, reason = purlin_approvals.counts(
            proved.root, approval, ['jane@acme.com'])
        assert counted, reason
        counted, reason = purlin_approvals.counts(
            proved.root, approval, ['someone@else.com'])
        assert not counted and 'approver list' in reason

    @pytest.mark.proof("approvals", "PROOF-24", "RULE-19")
    def test_a_batch_across_features_names_each_one(self):
        assert approve_module.commit_message(
            [('login', 'RULE-1'), ('login', 'RULE-2')]) == (
            'approve(login): RULE-1 RULE-2')
        assert approve_module.commit_message(
            [('login', 'RULE-1'), ('billing', 'RULE-3')]) == (
            'approve(batch): login RULE-1, billing RULE-3')

    @pytest.mark.proof("approvals", "PROOF-26", "RULE-21", tier="integration")
    def test_the_approver_list_bounds_who_may_run_it(self, proved, capsys):
        proved.config(approvers=['someone@else.com'])
        code = approve_module.main(['login', '--project-root', proved.root])
        output = capsys.readouterr().out
        assert code == 1
        assert 'not on the approver list' in output

    @pytest.mark.proof("approvals", "PROOF-27", "RULE-21", tier="integration")
    def test_the_approved_gate_with_no_list_names_the_command(self, capsys):
        made = Project(gate='approved')
        try:
            made.proofs()
            made.record()
            code = approve_module.main(['login', '--project-root', made.root])
            output = capsys.readouterr().out
            assert code == 1
            assert 'approver list missing: run purlin:init --gate approved' \
                in output
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The ancestor check
# ---------------------------------------------------------------------------

class TestTheAncestorCheck:

    @pytest.mark.proof("approvals", "PROOF-29", "RULE-23", tier="integration")
    def test_an_approval_on_a_side_branch_is_not_on_the_protected_branch(
            self, proved):
        signing_key(proved.root)
        git(proved.root, 'checkout', '-q', '-b', 'side')
        approve_module.main(['login', 'RULE-1', '--project-root', proved.root])
        loaded = purlin_approvals.load_approvals(
            proved.root, purlin_specs.scan_specs(proved.root))
        path = loaded[('login', 'RULE-1')][0]['path']
        assert not purlin_approvals.is_ancestor(proved.root, path, 'main')
        git(proved.root, 'checkout', '-q', 'main')
        git(proved.root, 'merge', '-q', '--ff-only', 'side')
        assert purlin_approvals.is_ancestor(proved.root, path, 'main')


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class TestTheCommandLine:

    @pytest.mark.proof("approvals", "PROOF-28", "RULE-22")
    def test_help_exits_zero_and_a_bad_option_exits_two(self):
        assert approve_module.main(['--help']) == 0
        assert approve_module.main(['login', '--nope']) == 2
        assert approve_module.main([]) == 2

    @pytest.mark.proof("approvals", "PROOF-22", "RULE-17", tier="integration")
    def test_the_script_runs_as_a_command(self, proved):
        result = subprocess.run(
            [sys.executable, APPROVE_PY, 'login', '--project-root',
             proved.root], capture_output=True, text=True, timeout=120)
        assert result.returncode == 1, result.stdout + result.stderr
        assert 'git config gpg.format ssh' in result.stdout
