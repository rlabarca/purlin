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


WINDOWS_TOKEN = re.compile(r'@windows(?![-\w.])')

# RULE-1's closed list: the only (file, section) pairs where the bare
# `@windows` token may appear. A section is the nearest preceding markdown
# heading, normalised by _norm_heading (any dash folded to `-`, whitespace
# collapsed), so `Step 5d - Update` here is skills/init/SKILL.md's
# `## Step 5d — Update`.
WINDOWS_TOKEN_SECTIONS = (
    ('docs/installation-guide.md', 'Upgrading the plugin'),
    ('docs/testing-workflow-guide.md', 'What `purlin:test` does per platform'),
    ('references/audit_criteria.md', 'LOOSE'),
    ('references/formats/proofs_format.md', 'File Naming'),
    ('references/formats/spec_format.md', 'Platform tags'),
    ('references/spec_quality_guide.md', 'Tier Assignment'),
    ('skills/init/SKILL.md', 'Usage'),
    ('skills/init/SKILL.md', 'Step 5d - Update'),
    ('skills/verify/SKILL.md', 'Pre-check: pending migrations'),
)


def _norm_heading(text):
    text = text.replace('—', '-').replace('–', '-')
    return re.sub(r'\s+', ' ', text).strip()


def _sectioned_paragraphs(text):
    """Yield (paragraph, nearest preceding heading) for one markdown file.

    Paragraphs are blank-line delimited. Lines inside a fenced block are never
    read as headings, so a `# comment` in a shell example cannot be mistaken
    for a section.
    """
    section = None
    fenced = False
    para = []
    para_section = None
    for line in text.splitlines():
        if re.match(r'^\s{0,3}(```|~~~)', line):
            fenced = not fenced
        elif not fenced:
            heading = re.match(r'^\s{0,3}#{1,6}\s+(.*\S)\s*$', line)
            if heading:
                section = _norm_heading(heading.group(1))
        if line.strip():
            if not para:
                para_section = section
            para.append(line)
        elif para:
            yield '\n'.join(para), para_section
            para = []
            para_section = None
    if para:
        yield '\n'.join(para), para_section


def _windows_token_paragraphs(root, files):
    """Every paragraph carrying a bare `@windows` token, read under `root`.

    Returns (rel, section, paragraph) triples. `root` is a parameter so the
    same check runs against a temp copy of a doc file.
    """
    hits = []
    for rel in files:
        try:
            with open(os.path.join(root, rel), encoding='utf-8') as f:
                text = f.read()
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
        for para, section in _sectioned_paragraphs(text):
            if WINDOWS_TOKEN.search(para):
                hits.append((rel, section, para))
    return hits


def _windows_token_offenders(root, files):
    """The (rel, section, paragraph) triples outside RULE-1's closed list."""
    allowed = set(WINDOWS_TOKEN_SECTIONS)
    return [hit for hit in _windows_token_paragraphs(root, files)
            if (hit[0], hit[1]) not in allowed]


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
    def test_bare_windows_token_only_in_the_nine_listed_sections(self):
        hits = _windows_token_paragraphs(PROJECT_ROOT, _prose_files())
        allowed = set(WINDOWS_TOKEN_SECTIONS)
        offenders = [f"{rel}: section {section!r}: {para.strip()[:160]}"
                     for rel, section, para in hits
                     if (rel, section) not in allowed]
        assert not offenders, (
            "`@windows` is a platform, never a tier. The bare token may "
            "appear only in the sections RULE-1 lists; the word `legacy` "
            "nearby does not exempt a paragraph:\n" + "\n".join(offenders))
        covered = {(rel, section) for rel, section, _ in hits}
        stale = [pair for pair in WINDOWS_TOKEN_SECTIONS
                 if pair not in covered]
        assert not stale, (
            "these sections are exempted by RULE-1 but no longer carry a "
            f"`@windows` occurrence, so the exemption is stale: {stale}")
        assert len(hits) >= len(WINDOWS_TOKEN_SECTIONS) >= 9, (
            f"scanned {len(hits)} paragraphs over "
            f"{len(WINDOWS_TOKEN_SECTIONS)} listed sections; the migration is "
            f"documented in nine sections, so the scan is not reading what it "
            f"thinks it is")

    @pytest.mark.proof("purlin_docs", "PROOF-12", "RULE-1")
    def test_windows_token_in_an_unrelated_legacy_paragraph_is_rejected(
            self, tmp_path):
        rel = 'docs/installation-guide.md'
        unrelated = 'Prerequisites'
        assert (rel, unrelated) not in set(WINDOWS_TOKEN_SECTIONS), (
            f"{unrelated!r} must be outside the closed list for this case to "
            f"discriminate")
        heading = f"## {unrelated}\n"
        text = _read(rel)
        assert heading in text, f"{rel} no longer has a {heading!r} section"
        injected = text.replace(
            heading,
            heading + "\nA legacy install may still carry @windows here.\n",
            1)
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(injected, encoding='utf-8')

        offenders = _windows_token_offenders(str(tmp_path), [rel])
        rejected = [o for o in offenders if o[0] == rel and o[1] == unrelated]
        assert len(rejected) == 1, (
            f"the injected paragraph under {unrelated!r} must be rejected by "
            f"file and section; offenders were {offenders}")
        opara = rejected[0][2]
        assert 'legacy' in opara.lower() and WINDOWS_TOKEN.search(opara), (
            "the rejected paragraph must be the one carrying both `legacy` "
            "and the bare token, proving the word alone does not exempt it")
        exempt = [o for o in offenders if o[1] == 'Upgrading the plugin']
        assert not exempt, (
            f"the listed section of the same file must stay exempt: {exempt}")
        assert _windows_token_offenders(PROJECT_ROOT, [rel]) == [], (
            f"the committed {rel} must pass the same check, so the failure "
            f"above is the injection and not the file")


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


def _heading_section(text, title):
    """The body of the section headed `title`, plus its enclosing `##` title.

    Returns (body, parent) where `body` is every line after the heading up to
    the next heading of the same or a shallower level, and `parent` is the
    nearest preceding `##` heading. Lines inside a fenced block are not read
    as headings. Returns (None, None) when the heading is absent.
    """
    body = None
    parent = None
    found_parent = None
    depth = None
    fenced = False
    for line in text.splitlines():
        if re.match(r'^\s{0,3}(```|~~~)', line):
            fenced = not fenced
            if body is not None:
                body.append(line)
            continue
        heading = None
        if not fenced:
            heading = re.match(r'^\s{0,3}(#{1,6})\s+(.*\S)\s*$', line)
        if heading:
            level = len(heading.group(1))
            name = _norm_heading(heading.group(2))
            if level == 2:
                parent = name
            if body is not None and level <= depth:
                break
            if body is None and name == _norm_heading(title):
                body = []
                depth = level
                found_parent = parent
                continue
        if body is not None:
            body.append(line)
    if body is None:
        return None, None
    return '\n'.join(body), found_parent


PIN_SECTION = 'Pinned Plugin Version and Interpreter'

PIN_LITERALS = (
    'pins the plugin by tag',
    'never installs it from a branch head',
    'claude plugin marketplace add',
    '.claude/settings.json',
    '.claude-plugin/plugin.json',
    'git clone --depth 1 --branch v<VERSION>',
)

PYTHON_LITERALS = (
    'Python 3.11 or newer',
    'tested floor',
    "python-version: '3.11'",
)


class TestRegulatedDeploymentIsPinned:
    """RULE-8 - the pin and the interpreter a validated install is held to."""

    @pytest.mark.proof("purlin_docs", "PROOF-13", "RULE-8")
    def test_regulated_page_pins_the_plugin_by_tag_and_names_python_311(self):
        body, parent = _heading_section(
            _read('docs/regulated-environments.md'), PIN_SECTION)
        assert body is not None, (
            f"docs/regulated-environments.md has no section headed "
            f"'{PIN_SECTION}'; RULE-8's two statements have nowhere to live")
        assert parent == 'Integration Points (not extensions)', (
            f"'{PIN_SECTION}' must sit under '## Integration Points (not "
            f"extensions)'; its enclosing section is {parent!r}")

        missing = [lit for lit in PIN_LITERALS if lit not in body]
        assert not missing, (
            f"the '{PIN_SECTION}' section no longer states how a regulated "
            f"deployment pins the plugin; missing literals: {missing}")

        missing = [lit for lit in PYTHON_LITERALS if lit not in body]
        assert not missing, (
            f"the '{PIN_SECTION}' section no longer states the Python floor a "
            f"regulated deployment runs; missing literals: {missing}")


# ---------------------------------------------------------------------------
# RULE-9: docs/regulated-environments.md names a mechanism per section.
# ---------------------------------------------------------------------------

REGULATED = 'docs/regulated-environments.md'

#: The closed set of config fields RULE-9 accepts as a mechanism name.
CONFIG_FIELDS = (
    'audit_llm', 'audit_llm_name', 'audit_criteria', 'audit_criteria_pinned',
    'mutation_checks', 'platforms', 'remote_verification', 'pre_push',
    'digest', 'report', 'test_framework', 'version', 'skipped_proofs',
)

#: RULE-9's five mechanism shapes, each as (name, pattern over raw text).
MECHANISM_SHAPES = (
    ('a script path under scripts/', re.compile(r'`scripts/[A-Za-z0-9_./-]+`')),
    ('a rule id with its spec', re.compile(r'`[A-Za-z0-9_]+`\s+RULE-\d+')),
    ('a config field', re.compile(
        r'`(?:' + '|'.join(CONFIG_FIELDS) + r')`')),
    ('a skill command', re.compile(r'`purlin:[a-z-]+(?:\s+--[a-z-]+)*`')),
    ('a format or spec file', re.compile(
        r'`(?:references|specs)/[A-Za-z0-9_./*<>-]+`')),
)

#: RULE-9's four forbidden approval phrases.
APPROVAL_PHRASES = ('compliance status', 'sign-off', 'signs off', 'certified')


def _level_two_sections(text):
    """[(title, body)] for every `##` section, fenced blocks never headings."""
    sections = []
    title = None
    body = []
    fenced = False
    for line in text.splitlines():
        if re.match(r'^\s{0,3}(```|~~~)', line):
            fenced = not fenced
            if title is not None:
                body.append(line)
            continue
        heading = None if fenced else re.match(r'^\s{0,3}##\s+(.*\S)\s*$',
                                               line)
        if heading and not line.lstrip().startswith('###'):
            if title is not None:
                sections.append((title, '\n'.join(body)))
            title = _norm_heading(heading.group(1))
            body = []
            continue
        if title is not None:
            body.append(line)
    if title is not None:
        sections.append((title, '\n'.join(body)))
    return sections


def _sections_without_a_mechanism(text):
    """Section titles whose body carries no RULE-9 mechanism name."""
    missing = []
    for title, body in _level_two_sections(text):
        if not any(pattern.search(body) for _name, pattern in
                   MECHANISM_SHAPES):
            missing.append(title)
    return missing


class TestRegulatedPageNamesItsMechanisms:
    """RULE-9 - a compliance reader cites the mechanism, not the claim."""

    @pytest.mark.proof("purlin_docs", "PROOF-14", "RULE-9")
    def test_every_section_names_a_mechanism_and_no_approval_vocabulary(self):
        text = _read(REGULATED)
        sections = _level_two_sections(text)
        assert len(sections) >= 8, (
            f"{REGULATED} parsed into {len(sections)} `##` sections; the "
            f"scan is not reading the page it claims to check")

        missing = _sections_without_a_mechanism(text)
        assert not missing, (
            f"these sections of {REGULATED} assert something with no "
            f"mechanism a reader can act on; each needs one of "
            f"{[name for name, _ in MECHANISM_SHAPES]}: {missing}")

        offenders = []
        for lineno, line in enumerate(text.splitlines(), 1):
            for phrase in APPROVAL_PHRASES:
                if phrase in line:
                    offenders.append(f"{REGULATED}:{lineno}: {phrase!r}")
        assert not offenders, (
            "approval vocabulary for something Purlin never does:\n"
            + "\n".join(offenders))

        # A section that asserts an approval with no mechanism is rejected by
        # title, so the sweep above is discriminating rather than vacuous.
        injected = text + (
            "\n## Release approval\n\n"
            "The compliance team approves the release once the evidence is "
            "complete.\n")
        assert _sections_without_a_mechanism(injected) == \
            ['Release approval'], (
            f"a section asserting an approval with no mechanism must be "
            f"rejected by title; got "
            f"{_sections_without_a_mechanism(injected)}")


# ---------------------------------------------------------------------------
# RULE-10: the platform docs point at the one home of the rule set.
# ---------------------------------------------------------------------------

PLATFORM_DOCS = ('docs/testing-workflow-guide.md',
                 'docs/collaboration-guide.md',
                 'docs/installation-guide.md',
                 'README.md')

TAXONOMY_HOME = 'references/remote_verification.md'
TAXONOMY_SECTION = 'Platforms, environments and prerequisites'

CATEGORY_WORDS = ('platform', 'environment', 'prerequisite')

MEMBERSHIP_QUESTIONS = (
    'Would the same test passing on a different OS be evidence for this '
    'claim?',
    "Does the outcome depend on an external system's real answers, an "
    "account, a model, or money, so that installing a package cannot "
    "reproduce it?",
    'Would any host with the tool installed produce the same evidence?',
)


def _paragraphs(text):
    """Blank-line delimited paragraphs with whitespace collapsed."""
    out = []
    para = []
    for line in text.splitlines():
        if line.strip():
            para.append(line)
        elif para:
            out.append(' '.join(' '.join(para).split()))
            para = []
    if para:
        out.append(' '.join(' '.join(para).split()))
    return out


def _taxonomy_paragraphs(text):
    """Paragraphs naming all three category words."""
    found = []
    for para in _paragraphs(text):
        lowered = para.lower()
        if all(re.search(rf'\b{word}s?\b', lowered)
               for word in CATEGORY_WORDS):
            found.append(para)
    return found


class TestPlatformDocsPointAtTheOneHome:
    """RULE-10 - three category names, one link, no second copy."""

    @pytest.mark.proof("purlin_docs", "PROOF-15", "RULE-10")
    def test_each_platform_doc_has_one_pointer_and_no_membership_question(
            self):
        for rel in PLATFORM_DOCS:
            text = _read(rel)
            pointers = _taxonomy_paragraphs(text)
            assert len(pointers) == 1, (
                f"{rel} must carry exactly one paragraph naming all three of "
                f"{CATEGORY_WORDS}; found {len(pointers)}: "
                f"{[p[:120] for p in pointers]}")
            pointer = pointers[0]
            assert TAXONOMY_HOME in pointer, (
                f"{rel}: the paragraph naming the three categories does not "
                f"link {TAXONOMY_HOME}: {pointer!r}")
            assert TAXONOMY_SECTION in pointer, (
                f"{rel}: the paragraph names the file but not the section "
                f"{TAXONOMY_SECTION!r}: {pointer!r}")

            collapsed = ' '.join(text.split())
            for question in MEMBERSHIP_QUESTIONS:
                assert question not in collapsed, (
                    f"{rel} restates a membership question the one home owns; "
                    f"a second copy is a second answer: {question!r}")

        # A copied question is found by the same collapse, so the scan above
        # passes because the files are clean and not because it reads nothing.
        rel = 'docs/testing-workflow-guide.md'
        question = MEMBERSHIP_QUESTIONS[0]
        injected = ' '.join((_read(rel) + '\n\n' + question + '\n').split())
        assert question in injected, (
            "the injected copy must be findable by the same collapse the "
            "check uses, or the case proves nothing")


# ---------------------------------------------------------------------------
# RULE-11: no em-dash or en-dash in the prose these files carry.
# ---------------------------------------------------------------------------

DASHES = ('—', '–')

DASH_FREE_REFERENCES = ('references/remote_verification.md',
                        'references/spec_quality_guide.md',
                        'references/hard_gates.md',
                        'references/audit_criteria.md')


def _dash_scope():
    return [f for f in _tracked('docs') if f.endswith('.md')] + \
        ['README.md'] + list(DASH_FREE_REFERENCES)


def _dash_hits(text, rel):
    """`<rel>:<lineno>: <line>` per dash outside a fenced block."""
    hits = []
    fenced = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if re.match(r'^\s{0,3}(```|~~~)', line):
            fenced = not fenced
            continue
        if fenced:
            continue
        if any(dash in line for dash in DASHES):
            hits.append(f"{rel}:{lineno}: {line.strip()}")
    return hits


class TestProseCarriesNoDashes:
    """RULE-11 - a dash is a joint the writer did not have to name."""

    @pytest.mark.proof("purlin_docs", "PROOF-16", "RULE-11")
    def test_no_em_dash_or_en_dash_outside_fenced_blocks(self):
        scope = _dash_scope()
        assert len(scope) >= 12, (
            f"only {len(scope)} files in scope; the sweep is not reading the "
            f"documentation set it claims to check: {scope}")
        offenders = []
        for rel in scope:
            offenders.extend(_dash_hits(_read(rel), rel))
        assert not offenders, (
            "an em-dash or en-dash joins two ideas without stating the "
            "relation; use a colon, a comma or a full stop:\n"
            + "\n".join(offenders))

        # An inserted dash is reported with its line, so a clean sweep is
        # evidence about the files rather than about the scanner.
        rel = 'README.md'
        text = _read(rel)
        marker = '**Rule-Proof Spec-Driven Development**'
        assert marker in text, f"{rel} no longer carries {marker!r}"
        injected = text.replace(
            marker, marker + '\n\nPurlin is a plugin — nothing more.', 1)
        expected_line = injected.splitlines().index(
            'Purlin is a plugin — nothing more.') + 1
        hits = _dash_hits(injected, rel)
        assert len(hits) == 1 and hits[0].startswith(
            f"{rel}:{expected_line}: "), (
            f"the injected em-dash must be reported as {rel}:"
            f"{expected_line}; got {hits}")
        assert _dash_hits(text, rel) == [], (
            f"the committed {rel} must pass the same sweep, so the failure "
            f"above is the injection and not the file")
