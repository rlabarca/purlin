"""Proofs for specs/instructions/purlin_docs.md.

Every rule here is about prose, so every proof is a grep over committed files
and grades STRUCTURAL. That is the strongest proof a rule about documentation
can have: the alternative is an LLM reading the guide, which is what
purlin:audit does and which no gate may depend on.
"""

import os
import re
import subprocess

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

BANNED = ('signed verification', 'tamper-evident', 'The vhash proves',
          '(signed off)', 'signed off')

PROSE_TREES = ('docs', 'references', 'skills', 'tools', 'agents')


def _tracked(*paths):
    out = subprocess.run(['git', 'ls-files', '--'] + list(paths),
                         cwd=PROJECT_ROOT, capture_output=True, text=True,
                         check=True).stdout
    return [p for p in out.splitlines() if p.strip()]


def _read(rel):
    with open(os.path.join(PROJECT_ROOT, rel), encoding='utf-8') as f:
        return f.read()


def _prose_files():
    files = _tracked(*PROSE_TREES) + ['README.md']
    return [f for f in files if not f.endswith('.skill')]


def _yaml_blocks(text):
    return re.findall(r'^```ya?ml\n(.*?)^```', text, re.MULTILINE | re.DOTALL)


def _docs_markdown():
    return [f for f in _tracked('docs') if f.endswith('.md')]


class TestForbiddenPromises:
    """RULE-1 - prose that promises what the mechanism cannot deliver."""

    @pytest.mark.proof("purlin_docs", "PROOF-1", "RULE-1")
    def test_no_signed_or_tamper_evident_claims_outside_the_negations(self):
        negations = 0
        offenders = []
        for rel in _prose_files():
            try:
                text = _read(rel)
            except (UnicodeDecodeError, IsADirectoryError):
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                if not any(b in line for b in BANNED):
                    continue
                if rel == 'docs/regulated-environments.md' and \
                        line.startswith('- **Not '):
                    negations += 1
                    continue
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
        assert not offenders, (
            "these lines claim a property Purlin does not have; the only "
            "permitted occurrences are the negations in "
            "docs/regulated-environments.md:\n" + "\n".join(offenders))
        assert negations >= 2, (
            f"found {negations} negation lines; the scan would pass on an "
            f"empty tree, so it proves nothing")

    @pytest.mark.proof("purlin_docs", "PROOF-2", "RULE-1")
    def test_bare_windows_tag_appears_only_as_a_documented_legacy_alias(self):
        token = re.compile(r'@windows(?![-\w.])')
        found = 0
        offenders = []
        for rel in _prose_files():
            try:
                text = _read(rel)
            except (UnicodeDecodeError, IsADirectoryError):
                continue
            for para in re.split(r'\n[ \t]*\n', text):
                if not token.search(para):
                    continue
                found += 1
                if 'legacy' in para.lower() or '@unit @on(' in para:
                    continue
                offenders.append(f"{rel}: {para.strip()[:160]}")
        assert not offenders, (
            "`@windows` is a platform, never a tier. Each occurrence must sit "
            "in a paragraph naming it as legacy or showing the `@unit @on(...)`"
            " rewrite:\n" + "\n".join(offenders))
        assert found >= 3, (
            f"only {found} occurrences scanned; the migration path is "
            f"documented in more places than that, so the scan is not reading "
            f"what it thinks it is")


class TestVhashHonesty:
    """RULE-2 - the compliance page states exactly what the hash reaches."""

    @pytest.mark.proof("purlin_docs", "PROOF-3", "RULE-2")
    def test_regulated_page_states_what_the_vhash_binds_and_does_not(self):
        text = _read('docs/regulated-environments.md')
        assert 'What the vhash binds' in text
        assert 'What it does not bind' in text
        binds = text.split('What the vhash binds', 1)[1]
        binds = binds.split('What it does not bind', 1)[0]
        for field in ('rule text', 'feature', 'proof id', 'rule', 'status',
                      'tier', 'platform', 'test file', 'test name',
                      'manual stamp'):
            assert field in binds, (
                f"the binds section never names {field!r}; a reader cannot "
                f"tell what a stale receipt means without it")
        does_not = text.split('What it does not bind', 1)[1]
        for phrase in ('test code', 'ran it', 'When it ran', 'meaningful',
                       'honesty'):
            assert phrase in does_not, (
                f"the does-not-bind section never names {phrase!r}")

    @pytest.mark.proof("purlin_docs", "PROOF-4", "RULE-2")
    def test_no_test_lock_file_and_audit_config_described_as_enforced(self):
        text = _read('docs/regulated-environments.md')
        assert '.test-lock' not in text, (
            "regulated-environments.md cites a .test-lock file; no such file "
            "exists in the framework and none is read")
        assert 'audit_llm` is executable configuration' in text or \
               '`audit_llm` is executable configuration' in text, text[-400:]
        assert 'pins it the same way it pins the criteria file' in text
        assert 'The pin is enforced rather than recorded' in text
        assert 'There is no fall back to the built-in criteria' in text

    @pytest.mark.proof("purlin_docs", "PROOF-5", "RULE-2")
    def test_pass_d_is_split_into_its_deterministic_and_llm_halves(self):
        sentence = 'Pass D1 is deterministic; Pass D2 is an LLM pass'
        for rel in ('docs/regulated-environments.md',
                    'references/remote_verification.md'):
            text = _read(rel)
            assert sentence in text, (
                f"{rel} does not carry the sentence {sentence!r}; a reader "
                f"takes 'deterministic' as a property they can rely on")
            assert 'Proof Design is deterministic' not in text, (
                f"{rel} still claims the whole of Proof Design is "
                f"deterministic; D2 is a model call")


class TestIndexIsTheEntryPoint:
    """RULE-3 - an index that omits a subsystem hides it."""

    @pytest.mark.proof("purlin_docs", "PROOF-6", "RULE-3")
    def test_index_names_platforms_the_layers_both_gauges_and_update(self):
        text = _read('docs/index.md')
        rows = [l for l in text.splitlines() if l.startswith('|')]
        remote = [r for r in rows if 'remote_verification.md' in r]
        assert remote, "no Guides row links remote_verification.md"
        assert any('latform' in r for r in remote), (
            f"the remote-verification row never names platforms: {remote}")
        assert any('hard_gates.md' in r for r in rows), \
            "no Guides row links hard_gates.md"
        summary = [l for l in text.splitlines()
                   if not l.startswith('|') and 'hard_gates.md' in l]
        assert summary, "no prose line points at the enforcement layers"
        assert 'Layer 0' in text, \
            "the layer summary never names Layer 0, the one gate"
        skills = text.split('Key skills:', 1)[1]
        for gauge in ('Proof Design', 'Proof Integrity'):
            assert gauge in skills, f"key skills never name {gauge}"
        assert 'purlin:init --update' in text, \
            "the index never names the command that migrates a project"


class TestOneEnforcementModel:
    """RULE-4 - one table, three links."""

    ROW = re.compile(r'^\|\s*\*\*(Layer \d|Not a layer)')

    @pytest.mark.proof("purlin_docs", "PROOF-7", "RULE-4")
    def test_exactly_one_enforcement_layer_table_and_three_pointers(self):
        carriers = {}
        scanned = _tracked('docs', 'references', 'skills', 'agents') + \
            ['README.md']
        for rel in scanned:
            if not rel.endswith('.md'):
                continue
            try:
                text = _read(rel)
            except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
                continue
            hits = [l for l in text.splitlines() if self.ROW.match(l)]
            if hits:
                carriers[rel] = hits
        assert list(carriers) == ['references/hard_gates.md'], (
            f"the enforcement-layer table must exist exactly once; found it "
            f"in {sorted(carriers)}")
        rows = carriers['references/hard_gates.md']
        assert len(rows) == 5, (
            f"expected Layer 0..3 and the not-a-layer row, found "
            f"{len(rows)}: {rows}")
        joined = '\n'.join(rows)
        for label in ('Layer 0', 'Layer 1', 'Layer 2', 'Layer 3',
                      'purlin:verify --recheck'):
            assert label in joined, f"no row for {label}"

        gates = _read('references/hard_gates.md')
        assert '## Enforcement Layers' in gates
        assert len(re.findall(r'^## Gate \d+', gates, re.MULTILINE)) == 1, (
            "the layers section must not read as a second gate")
        layer1 = [r for r in rows if r.startswith('| **Layer 1')][0]
        for token in ('warn', 'strict', 'off', 'plugin root'):
            assert token in layer1, (
                f"the Layer 1 row never names {token!r}: {layer1}")
        layer3 = [r for r in rows if r.startswith('| **Layer 3')][0]
        for token in ('verify_gate.py', 'branch protection',
                      'remote_verification'):
            assert token in layer3, (
                f"the Layer 3 row never names {token!r}: {layer3}")

        for rel in ('docs/regulated-environments.md',
                    'docs/lifecycle-guide.md',
                    'docs/testing-workflow-guide.md'):
            text = _read(rel)
            assert 'hard_gates.md' in text, (
                f"{rel} dropped its copy of the table without linking the "
                f"one that remains")


class TestCIExamplesAreRunnable:
    """RULE-5 - an example that fails on first paste is worse than none."""

    @pytest.mark.proof("purlin_docs", "PROOF-8", "RULE-5")
    def test_no_yaml_example_invokes_a_skill_or_a_deploy_event(self):
        blocks = 0
        offenders = []
        for rel in _docs_markdown():
            for block in _yaml_blocks(_read(rel)):
                blocks += 1
                for bad in ('run: purlin:', 'on: deploy'):
                    if bad in block:
                        offenders.append(f"{rel}: {bad!r} in a yaml block")
        assert not offenders, (
            "a workflow cannot invoke a Claude Code skill and `deploy` is not "
            "an Actions event:\n" + "\n".join(offenders))
        assert blocks >= 3, (
            f"only {blocks} yaml blocks found under docs/; the scan is not "
            f"reading the examples it claims to check")

    @pytest.mark.proof("purlin_docs", "PROOF-9", "RULE-5")
    def test_gate_examples_run_real_tests_first_and_fetch_full_history(self):
        runners = ('pytest', 'npx jest', 'npm', 'dotnet', 'go ', 'bash ')
        checked = []
        for rel in _docs_markdown():
            for block in _yaml_blocks(_read(rel)):
                if 'verify_gate.py' not in block:
                    continue
                checked.append(rel)
                assert ('python3 "$PURLIN_PLUGIN_ROOT/scripts/ci/'
                        'verify_gate.py" --check') in block, (
                    f"{rel}: the gate must be invoked through "
                    f"$PURLIN_PLUGIN_ROOT:\n{block}")
                assert 'fetch-depth: 0' in block, (
                    f"{rel}: without fetch-depth: 0 the gate has no git log "
                    f"to read per proof file")
                assert 'git clone --depth 1 --branch v' in block, (
                    f"{rel}: a consumer checkout has no Purlin scripts/; the "
                    f"example must install the tooling at a pinned tag")
                gate_at = block.index('verify_gate.py')
                before = block[:gate_at]
                assert any(r in before for r in runners), (
                    f"{rel}: no real test command runs before the gate, so "
                    f"the gate re-reads committed proof files:\n{block}")
        assert len(checked) >= 2, (
            f"expected at least two gate examples, found {checked}")
        assert 'docs/examples/figma-web-app.md' in checked, (
            "the worked example still has no runnable CI block")


class TestDiagramsAndImages:
    """RULE-6 and RULE-7 - every rendered artifact has a source."""

    @pytest.mark.proof("purlin_docs", "PROOF-10", "RULE-6")
    def test_every_lifecycle_svg_has_a_tracked_mermaid_source(self):
        svgs = sorted(f for f in _tracked('assets')
                      if f.startswith('assets/lifecycle-')
                      and f.endswith('.svg'))
        assert svgs, "no lifecycle SVGs are tracked"
        sources = sorted(_tracked('assets/src'))
        assert sources == sorted(
            f"assets/src/{os.path.basename(s)[:-4]}.mmd" for s in svgs), (
            f"assets/src must hold exactly one .mmd per lifecycle SVG; "
            f"tracked sources are {sources} for SVGs {svgs}")
        for svg in svgs:
            src = f"assets/src/{os.path.basename(svg)[:-4]}.mmd"
            assert os.path.isfile(os.path.join(PROJECT_ROOT, src)), (
                f"{svg} has no source at {src}; Mermaid computes the node "
                f"positions, so an SVG with no source cannot be changed")

        exempt = [f for f in _tracked('assets')
                  if f.endswith('.svg') and not f.startswith(
                      'assets/lifecycle-')]
        assert exempt == ['assets/purlin-logo.svg'], (
            f"only the hand-authored logo is exempt from RULE-6; found "
            f"{exempt}")

        lines = _read('.gitignore').splitlines()
        assert '*.mmd' in lines, ".gitignore no longer ignores *.mmd"
        assert '!assets/src/*.mmd' in lines, (
            ".gitignore must negate assets/src/*.mmd or the sources go "
            "untracked again")
        assert lines.index('!assets/src/*.mmd') > lines.index('*.mmd'), (
            "the negation must follow the pattern it negates")

    @pytest.mark.proof("purlin_docs", "PROOF-11", "RULE-7")
    def test_the_three_dashboard_screenshots_exist_and_are_referenced(self):
        names = ('dashboard-summary.png', 'dashboard-categories.png',
                 'dashboard-platforms.png')
        markdown = {rel: _read(rel) for rel in _docs_markdown()}
        for name in names:
            path = os.path.join(PROJECT_ROOT, 'docs', 'images', name)
            assert os.path.isfile(path), f"docs/images/{name} is missing"
            assert os.path.getsize(path) > 0, f"docs/images/{name} is empty"
            referring = [rel for rel, text in markdown.items()
                         if re.search(r'!\[[^\]]*\]\([^)]*' + re.escape(name),
                                      text)]
            assert referring, (
                f"docs/images/{name} is referenced by no markdown under "
                f"docs/; nothing would notice it going stale")
