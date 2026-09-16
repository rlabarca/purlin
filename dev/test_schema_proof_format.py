"""Tests for schema_proof_format.

What a proof file holds, where it lives and how `sync_status` reads it. The
merge behaviour a plugin implements when it writes one is proved by each
plugin's own spec; this file proves the reader's half.
"""

import json
import os
import shutil
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))
from purlin import payload as purlin_payload
from purlin import proofs as purlin_proofs

REQUIRED_FIELDS = {'feature', 'id', 'rule', 'test_file', 'test_name', 'status',
                   'tier'}


class TestProofFormatEnforcement:

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _write_spec(self, name, content, subdir='test'):
        directory = os.path.join(self.project_root, 'specs', subdir)
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, name + '.md'), 'w',
                  encoding='utf-8') as handle:
            handle.write(content)

    def _write_proofs(self, name, entries, tier='unit'):
        directory = purlin_proofs.proof_dir(self.project_root)
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, '%s.%s.json' % (name, tier))
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump({'tier': tier, 'proofs': entries}, handle)
        return path

    def _word(self, feature, rule_id):
        """The word one rule's passed cell reads."""
        data = purlin_payload.build_payload(self.project_root)
        entry = next(f for f in data['features'] if f['name'] == feature)
        rule = next(r for r in entry['rules'] if r['id'] == rule_id)
        return rule['cells']['passed']['word']

    @pytest.mark.proof("schema_proof_format", "PROOF-1", "RULE-1")
    def test_a_runtime_proof_file_is_read(self):
        self._write_spec('foo', (
            '# Feature: foo\n\n'
            '## Rules\n- RULE-1: The parser returns 200 for a valid body\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST a valid body; verify 200\n'
        ))
        assert self._word('foo', 'RULE-1') == 'no test', \
            'with no proof file nothing backs the rule'
        self._write_proofs('foo', [
            {'feature': 'foo', 'id': 'PROOF-1', 'rule': 'RULE-1',
             'test_file': 'tests/test_foo.py', 'test_name': 'test_it',
             'status': 'pass', 'tier': 'unit'},
        ])
        assert self._word('foo', 'RULE-1') == 'passed', \
            'a passing entry in .purlin/runtime/proofs/ meets level 1'

    @pytest.mark.proof("schema_proof_format", "PROOF-2", "RULE-2")
    def test_every_entry_carries_the_seven_fields(self):
        path = self._write_proofs('foo', [
            {'feature': 'foo', 'id': 'PROOF-1', 'rule': 'RULE-1',
             'test_file': 'tests/test_foo.py', 'test_name': 'test_it',
             'status': 'pass', 'tier': 'unit'},
        ])
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
        assert 'tier' in data and 'proofs' in data
        for entry in data['proofs']:
            missing = REQUIRED_FIELDS - set(entry)
            assert not missing, 'missing fields %s in %s' % (missing, path)
        # No runner and no operating system on an entry: the record says where
        # a run happened, once per run rather than once per proof.
        for entry in data['proofs']:
            assert 'runner' not in entry and 'os' not in entry, entry

    @pytest.mark.proof("schema_proof_format", "PROOF-3", "RULE-3")
    def test_only_pass_counts(self):
        self._write_spec('bar', (
            '# Feature: bar\n\n'
            '## Rules\n'
            '- RULE-1: The parser returns 200 for a valid body\n'
            '- RULE-2: The parser returns 400 for an empty body\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): POST a valid body; verify 200\n'
            '- PROOF-2 (RULE-2): POST an empty body; verify 400\n'
        ))
        for bad in ('error', 'fail', 'skipped', None):
            self._write_proofs('bar', [
                {'feature': 'bar', 'id': 'PROOF-1', 'rule': 'RULE-1',
                 'test_file': 't.py', 'test_name': 't', 'status': bad,
                 'tier': 'unit'},
                {'feature': 'bar', 'id': 'PROOF-2', 'rule': 'RULE-2',
                 'test_file': 't.py', 'test_name': 't2', 'status': 'pass',
                 'tier': 'unit'},
            ])
            assert self._word('bar', 'RULE-1') != 'passed', (
                'status %r must not count as proved' % bad)
            assert self._word('bar', 'RULE-2') == 'passed', (
                "the passing rule beside a %r one still counts" % bad)

    @pytest.mark.proof("schema_proof_format", "PROOF-4", "RULE-4")
    def test_a_fail_beats_a_pass_for_the_same_proof(self):
        self._write_spec('baz', (
            '# Feature: baz\n\n'
            '## Rules\n- RULE-1: The parser returns 200 for a valid body\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST a valid body; verify 200\n'
        ))
        self._write_proofs('baz', [
            {'feature': 'baz', 'id': 'PROOF-1', 'rule': 'RULE-1',
             'test_file': 'a.py', 'test_name': 'ok', 'status': 'pass',
             'tier': 'unit'},
            {'feature': 'baz', 'id': 'PROOF-1', 'rule': 'RULE-1',
             'test_file': 'b.py', 'test_name': 'broken', 'status': 'fail',
             'tier': 'unit'},
        ])
        assert self._word('baz', 'RULE-1') != 'passed', (
            'a proof that failed in any test claiming it is not proved')

    @pytest.mark.proof("schema_proof_format", "PROOF-5", "RULE-5")
    def test_a_missing_directory_is_an_empty_result(self):
        assert purlin_proofs.load_proofs(self.project_root) == {}
        os.makedirs(purlin_proofs.proof_dir(self.project_root))
        assert purlin_proofs.load_proofs(self.project_root) == {}

    @pytest.mark.proof("schema_proof_format", "PROOF-6", "RULE-6")
    def test_the_filename_names_the_feature_and_the_tier(self):
        assert purlin_proofs.proof_file_parts('login.unit.json') == ('login',
                                                                    'unit')
        assert purlin_proofs.proof_file_parts(
            'login.integration.json') == ('login', 'integration')
        assert purlin_proofs.proof_file_parts('login.md') is None
        # A file with no tier segment names nothing readable.
        assert purlin_proofs.proof_file_parts('login.json') is None


class TestProofFormatConventions:

    @pytest.mark.proof("schema_proof_format", "PROOF-7", "RULE-7")
    def test_the_runtime_directory_is_gitignored(self):
        with open(os.path.join(PROJECT_ROOT, '.gitignore'),
                  encoding='utf-8') as handle:
            gitignore = handle.read()
        assert '.purlin/runtime/' in gitignore, (
            'proof files are runtime, so two runs on two branches never '
            'conflict and nothing about a run is committed')
        assert purlin_proofs.PROOF_DIR.replace(os.sep, '/').startswith(
            '.purlin/runtime/')

    @pytest.mark.proof("schema_proof_format", "PROOF-8", "RULE-8")
    def test_the_spec_format_documents_the_tiers(self):
        with open(os.path.join(PROJECT_ROOT, 'references', 'formats',
                               'spec_format.md'), encoding='utf-8') as handle:
            fmt = handle.read()
        for tag in ('@integration', '@e2e', '@manual', '@env('):
            assert tag in fmt, '%s is not documented' % tag
        assert '@on(' not in fmt.split('### Retired tags')[0], (  # retired
            'the retired scope tag must appear only under Retired tags')
