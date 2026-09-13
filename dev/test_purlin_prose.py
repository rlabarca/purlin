"""Proofs for specs/instructions/purlin_prose.md.

Every rule here is about prose, so every proof is a grep over committed files.
RULE-12 through RULE-15 are owned by `dev/prose_lint.py`, and the helpers that
walk the tree live there rather than here, so the proofs and the lint read the
same bytes the same way.
"""

import json
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prose_lint import (  # noqa: E402
    BANNED,
    HOMES,
    PATH_SCOPE,
    PROJECT_ROOT,
    SKILL_GLOB,
    AGENT_GLOB,
    HOME_SCOPE,
    _dash_hits,
    _norm_heading,
    _prose_files,
    _read,
    _scope_files,
    _sectioned_paragraphs,
    _tracked,
    _yaml_blocks,
    banned_strings,
    paths_exist,
    repo_files,
    single_home,
    structure,
)


def _docs_markdown():
    return [f for f in _tracked('docs') if f.endswith('.md')]


class TestVhashHonesty:
    """RULE-2 - the compliance page states exactly what the hash reaches."""

    @pytest.mark.proof("purlin_prose", "PROOF-3", "RULE-2")
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

    @pytest.mark.proof("purlin_prose", "PROOF-4", "RULE-2")
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

    @pytest.mark.proof("purlin_prose", "PROOF-5", "RULE-2")
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

    @pytest.mark.proof("purlin_prose", "PROOF-6", "RULE-3")
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


class TestCIExamplesAreRunnable:
    """RULE-5 - an example that fails on first paste is worse than none."""

    @pytest.mark.proof("purlin_prose", "PROOF-8", "RULE-5")
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

    @pytest.mark.proof("purlin_prose", "PROOF-9", "RULE-5")
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

        # The trigger filters, over every yaml block and not only the gate
        # ones. A consumer checkout has no Purlin `scripts/`, so a filter
        # naming one is a trigger that can never fire.
        filtered = []
        for rel in _docs_markdown():
            for block in _yaml_blocks(_read(rel)):
                for group in re.findall(
                        r"\n\s*paths(?:-ignore)?:\n((?:\s+- +'?[^\n]*\n)+)",
                        block):
                    for line in group.strip('\n').split('\n'):
                        entry = line.strip()[2:].strip().strip("'\"")
                        filtered.append((rel, entry))
        assert filtered, (
            "no yaml block under docs/ carries a trigger paths filter, so "
            "this half of the rule is checked against nothing")
        offenders = [(rel, entry) for rel, entry in filtered
                     if entry.startswith('scripts/')]
        assert not offenders, (
            "a consumer checkout holds no Purlin scripts/, so these trigger "
            "filters never fire: " + '; '.join(
                f'{rel}: {entry}' for rel, entry in offenders))


class TestDiagramsAndImages:
    """RULE-6 and RULE-7 - every rendered artifact has a source."""

    @pytest.mark.proof("purlin_prose", "PROOF-10", "RULE-6")
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

    @pytest.mark.proof("purlin_prose", "PROOF-11", "RULE-7")
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

    @pytest.mark.proof("purlin_prose", "PROOF-13", "RULE-8")
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
    'mutation_checks', 'platforms', 'remote_verification', 'quality_gate',
    'pre_push', 'digest', 'report', 'test_framework', 'version',
    'skipped_proofs',
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

    @pytest.mark.proof("purlin_prose", "PROOF-14", "RULE-9")
    def test_every_section_of_the_regulated_page_names_a_mechanism(self):
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

        # The four approval phrases are a banned_strings row under RULE-12.

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
# RULE-12 to RULE-15: the four lints of dev/prose_lint.py.
# ---------------------------------------------------------------------------

EM_DASH = '\u2014'


def _row(rows, name):
    """One table row by name, so a proof names the row it exercises."""
    match = [r for r in rows if r[0] == name]
    assert len(match) == 1, f"no single {name!r} row in {[r[0] for r in rows]}"
    return match[0]


def _plant(root, rel, text):
    dest = os.path.join(str(root), rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'w', encoding='utf-8') as f:
        f.write(text)
    return dest


class TestBannedStringsLint:
    """RULE-12 - one table of the strings this repository forbids."""

    @pytest.mark.proof("purlin_prose", "PROOF-17", "RULE-12")
    def test_an_injected_em_dash_is_named_by_file_and_line(self, tmp_path):
        rel = 'docs/index.md'
        name, unit, pattern, scope, _min_files, allowlist, note = _row(
            BANNED, 'em-dash')
        row = (name, unit, pattern, scope, 1, allowlist, note)

        sentence = f"The gauge has two halves {EM_DASH} design and integrity."
        text = _read(rel)
        injected = text.rstrip('\n') + '\n\n' + sentence + '\n'
        _plant(tmp_path, rel, injected)
        expected_line = injected.splitlines().index(sentence) + 1

        offenders = banned_strings(root=str(tmp_path), files=[rel],
                                   rows=(row,), strict=False)
        assert len(offenders) == 1, (
            f"the injected em dash must be the one offender; got {offenders}")
        found = offenders[0]
        assert found.path == rel and found.line == expected_line, (
            f"expected {rel}:{expected_line}, got {found.path}:{found.line}")
        assert found.lint == 'banned_strings'
        assert found.message.startswith('em-dash: '), found.message
        assert str(found).startswith(
            f"{rel}:{expected_line}: banned_strings: em-dash: "), str(found)

        assert banned_strings(files=[rel], rows=(row,), strict=False) == [], (
            f"the committed {rel} must pass the same row, so the failure "
            f"above is the injection and not the file")

        # The sweep and the retired RULE-11 helper agree on the line.
        assert _dash_hits(injected, rel)[0].startswith(
            f"{rel}:{expected_line}: ")

    @pytest.mark.proof("purlin_prose", "PROOF-17", "RULE-12")
    def test_an_exemption_whose_text_is_gone_is_reported_as_stale(
            self, tmp_path):
        rel = 'references/audit_criteria.md'
        name, unit, pattern, scope, _min_files, allowlist, note = _row(
            BANNED, 'windows-tier')
        assert (rel, 'LOOSE') in allowlist, (
            f"({rel}, 'LOOSE') must be an exempt pair for this case to "
            f"discriminate")
        row = (name, unit, pattern, scope, 1,
               ((rel, 'LOOSE'),), note)

        stripped = pattern.sub('@on(windows)', _read(rel))
        _plant(tmp_path, rel, stripped)

        offenders = banned_strings(root=str(tmp_path), files=[rel],
                                   rows=(row,), strict=True)
        assert len(offenders) == 1, (
            f"deleting the only occurrence must leave exactly the stale "
            f"exemption; got {offenders}")
        found = offenders[0]
        assert found.path == rel and found.lint == 'banned_strings'
        assert 'stale' in found.message and "'LOOSE'" in found.message, \
            found.message

        assert banned_strings(files=[rel], rows=(row,), strict=True) == [], (
            "the committed file still carries the occurrence, so the "
            "exemption is live")

    @pytest.mark.proof("purlin_prose", "PROOF-17", "RULE-12")
    def test_a_restored_three_section_name_is_named_by_file_and_line(
            self, tmp_path):
        rel = 'docs/index.md'
        name, unit, pattern, scope, _min_files, allowlist, note = _row(
            BANNED, 'retired-format')
        row = (name, unit, pattern, scope, 1, allowlist, note)

        sentence = 'Every spec is written in the 3-section format.'
        text = _read(rel)
        injected = text.rstrip('\n') + '\n\n' + sentence + '\n'
        _plant(tmp_path, rel, injected)
        expected_line = injected.splitlines().index(sentence) + 1

        offenders = banned_strings(root=str(tmp_path), files=[rel],
                                   rows=(row,), strict=False)
        assert len(offenders) == 1, (
            f"the restored name must be the one offender; got {offenders}")
        found = offenders[0]
        assert found.path == rel and found.line == expected_line, (
            f"expected {rel}:{expected_line}, got {found.path}:{found.line}")
        assert found.lint == 'banned_strings'
        assert str(found).startswith(
            f"{rel}:{expected_line}: banned_strings: retired-format: "), \
            str(found)

        assert banned_strings(files=[rel], rows=(row,), strict=False) == [], (
            f"the committed {rel} must pass the same row, so the failure "
            f"above is the injection and not the file")

    @pytest.mark.proof("purlin_prose", "PROOF-17", "RULE-12")
    def test_the_retired_heading_is_caught_and_the_vhash_heading_is_not(
            self, tmp_path):
        """The heading arm is anchored, so one real heading must survive it."""
        rel = 'docs/index.md'
        name, unit, pattern, scope, _min_files, allowlist, note = _row(
            BANNED, 'retired-format')
        row = (name, unit, pattern, scope, 1, allowlist, note)

        heading = '## What it does'
        injected = (_read(rel).rstrip('\n') + '\n\n' + heading
                    + '\nAuthentication, end to end.\n')
        _plant(tmp_path, rel, injected)
        expected_line = injected.splitlines().index(heading) + 1

        offenders = banned_strings(root=str(tmp_path), files=[rel],
                                   rows=(row,), strict=False)
        assert len(offenders) == 1 and offenders[0].line == expected_line, (
            f"the retired heading must be the one offender at line "
            f"{expected_line}; got {offenders}")

        # `docs/regulated-environments.md` carries `#### What it does not bind`
        # under RULE-2. The anchored arm must leave it alone.
        regulated = _read(REGULATED)
        assert '#### What it does not bind' in regulated, (
            "the discriminating heading is gone, so this case proves nothing")
        assert banned_strings(files=[REGULATED], rows=(row,),
                              strict=False) == [], (
            "`What it does not bind` is a live heading of the regulated page, "
            "not the retired section")


class TestPathsExistLint:
    """RULE-13 - a path in backticks reads as a link."""

    @pytest.mark.proof("purlin_prose", "PROOF-18", "RULE-13")
    def test_a_dangling_path_and_an_undeclared_flag_are_both_named(
            self, tmp_path):
        rel = 'docs/index.md'
        os.makedirs(os.path.join(str(tmp_path), 'specs'), exist_ok=True)
        for skill in _scope_files((SKILL_GLOB,), repo_files()):
            _plant(tmp_path, skill, _read(skill))

        bad_path = 'Read `specs/schema/x.md` for the shape.'
        bad_flag = 'Run `purlin:find --nope` to search.'
        injected = _read(rel).rstrip('\n') + '\n\n' + bad_path + '\n\n' + \
            bad_flag + '\n'
        _plant(tmp_path, rel, injected)
        lines = injected.splitlines()
        path_line = lines.index(bad_path) + 1
        flag_line = lines.index(bad_flag) + 1

        offenders = paths_exist(root=str(tmp_path), files=[rel], strict=False)
        assert len(offenders) == 2, (
            f"expected the dangling path and the undeclared flag; got "
            f"{offenders}")
        first, second = offenders
        assert first.path == rel and first.line == path_line
        assert first.lint == 'paths_exist'
        assert 'specs/schema/x.md' in first.message and \
            'does not resolve' in first.message, first.message
        assert second.path == rel and second.line == flag_line
        assert '--nope' in second.message and \
            'skills/find/SKILL.md' in second.message and \
            '## Usage' in second.message, second.message

        assert paths_exist(strict=True) == [], (
            "the committed scope must resolve every path and flag, so the "
            "two offenders above are the injection")


class TestStructureLint:
    """RULE-14 - a skill the loader cannot resolve is a skill nobody runs."""

    @pytest.mark.proof("purlin_prose", "PROOF-19", "RULE-14")
    def test_a_missing_usage_block_and_a_mismatched_name_are_named(
            self, tmp_path):
        rel = 'skills/find/SKILL.md'
        text = _read(rel)
        assert '\n## Usage\n' in text, f"{rel} no longer has a ## Usage block"
        _plant(tmp_path, rel, text.replace('\n## Usage\n', '\n', 1))

        offenders = structure(root=str(tmp_path), files=[rel], strict=False)
        assert len(offenders) == 1, (
            f"the deleted ## Usage heading must be the one offender; got "
            f"{offenders}")
        assert offenders[0].path == rel
        assert offenders[0].lint == 'structure'
        assert '## Usage' in offenders[0].message, offenders[0].message

        moved = 'skills/finder/SKILL.md'
        _plant(tmp_path, moved, text)
        offenders = structure(root=str(tmp_path), files=[moved], strict=False)
        assert len(offenders) == 1, (
            f"a skill whose frontmatter name is not its directory must be the "
            f"one offender; got {offenders}")
        assert offenders[0].path == moved
        assert "'find'" in offenders[0].message and \
            "'finder'" in offenders[0].message, offenders[0].message

        pinned = 'agents/pinned.md'
        _plant(tmp_path, pinned,
               '---\nname: pinned\ndescription: a pinned agent\n'
               'model: some-model\n---\n\nbody\n')
        offenders = structure(root=str(tmp_path), files=[pinned], strict=False)
        assert len(offenders) == 1, (
            f"an agent pinning a model must be the one offender; got "
            f"{offenders}")
        assert offenders[0].path == pinned
        assert offenders[0].lint == 'structure'
        assert 'model' in offenders[0].message, offenders[0].message

        assert structure(strict=True) == [], (
            "every committed skill and agent must carry its shape")


class TestSingleHomeLint:
    """RULE-15 - a subject with two homes drifts at the first edit."""

    @pytest.mark.proof("purlin_prose", "PROOF-20", "RULE-15")
    def test_the_enforcement_table_pasted_into_a_guide_is_named_by_line(
            self, tmp_path):
        row = _row(HOMES, 'enforcement-layer table')
        pattern, home = row[2], row[3]
        gates = _read(home)
        rows = [line for line in gates.splitlines() if pattern.match(line)]
        assert len(rows) == 5, f"{home} carries {len(rows)} layer rows"
        _plant(tmp_path, home, gates)

        rel = 'docs/lifecycle-guide.md'
        guide = _read(rel)
        injected = guide.rstrip('\n') + '\n\n' + '\n'.join(rows) + '\n'
        _plant(tmp_path, rel, injected)
        first = injected.splitlines().index(rows[0]) + 1
        expected = list(range(first, first + 5))

        offenders = single_home(root=str(tmp_path), files=[home, rel],
                                rows=(row,), strict=True)
        assert len(offenders) == 5, (
            f"every pasted row must be reported; got {offenders}")
        assert [o.path for o in offenders] == [rel] * 5
        assert [o.line for o in offenders] == expected, (
            f"expected lines {expected}, got {[o.line for o in offenders]}")
        for offender in offenders:
            assert offender.lint == 'single_home'
            assert home in offender.message, offender.message

        assert single_home(rows=(row,), strict=True) == [], (
            f"the committed tree must carry the table only in {home}")


    @pytest.mark.proof("purlin_prose", "PROOF-24", "RULE-15")
    def test_a_proof_common_rule_pasted_into_the_contract_is_named(
            self, tmp_path):
        row = _row(HOMES, 'proof_common rule text')
        pattern, home = row[2], row[3]
        anchor = _read(home)
        rule_lines = [line for line in anchor.splitlines()
                      if re.match(r'^- RULE-\d+: ', line)]
        assert len(rule_lines) >= 25, (
            f"{home} carries {len(rule_lines)} rule lines; the row's pattern "
            f"is built from them and would grade against an empty anchor")
        assert len(pattern.findall(anchor)) >= row[5], (
            f"the committed anchor must carry the row's pattern at least "
            f"{row[5]} times")
        _plant(tmp_path, home, anchor)

        rel = 'references/proof_plugin_contract.md'
        contract = _read(rel)
        # The body alone, without the `- RULE-N: ` prefix: a contract that
        # restates a rule restates its text, not the anchor's list markup.
        body = rule_lines[3].split(': ', 1)[1]
        injected = contract.rstrip('\n') + '\n\n' + body + '\n'
        _plant(tmp_path, rel, injected)
        expected = injected.splitlines().index(body) + 1

        offenders = single_home(root=str(tmp_path), files=[home, rel],
                                rows=(row,), strict=True)
        assert len(offenders) == 1, (
            f"the planted rule line must be the one offender; got {offenders}")
        assert offenders[0].path == rel
        assert offenders[0].lint == 'single_home'
        assert offenders[0].line == expected, (
            f"expected line {expected}, got {offenders[0].line}")
        assert home in offenders[0].message, offenders[0].message

        # Three restored rows of the retired requirement table fail together.
        three = [line.split(': ', 1)[1] for line in rule_lines[:3]]
        _plant(tmp_path, rel,
               contract.rstrip('\n') + '\n\n' + '\n'.join(three) + '\n')
        offenders = single_home(root=str(tmp_path), files=[home, rel],
                                rows=(row,), strict=True)
        assert [o.path for o in offenders] == [rel] * 3, (
            f"all three restored rules must be reported; got {offenders}")

        assert single_home(rows=(row,), strict=True) == [], (
            f"the committed tree must carry the rule text only in {home}")


class TestTheLintsReadTheTreeTheyClaimTo:
    """RULE-12 - a sweep that scans nothing passes on an empty repository."""

    @pytest.mark.proof("purlin_prose", "PROOF-21", "RULE-12")
    def test_scoped_file_counts_and_a_clean_run_on_the_real_tree(self):
        files = repo_files()
        floors = {'em-dash': 12, 'promise': 40, 'windows-tier': 40,
                  'approval': 1, 'retired-format': 25}
        for name, floor in floors.items():
            scope = _row(BANNED, name)[3]
            count = len(_scope_files(scope, files))
            assert count >= floor, (
                f"the {name!r} row resolved to {count} files, under its floor "
                f"of {floor}; the sweep would pass by scanning nothing")
        assert len(_scope_files(PATH_SCOPE, files)) >= 15
        assert len(_scope_files((SKILL_GLOB,), files)) >= 12
        assert len(_scope_files((AGENT_GLOB,), files)) >= 2
        assert len(_scope_files(HOME_SCOPE, files)) >= 40

        run = subprocess.run(
            [sys.executable, os.path.join('dev', 'prose_lint.py')],
            cwd=PROJECT_ROOT, capture_output=True, text=True)
        offenders = [line for line in run.stdout.splitlines()
                     if re.search(r': (banned_strings|paths_exist|structure'
                                  r'|single_home): ', line)]
        assert run.returncode == 0 and not offenders, (
            "dev/prose_lint.py must exit 0 on the committed tree:\n"
            + "\n".join(offenders) + run.stderr)

        run = subprocess.run(
            [sys.executable, os.path.join('dev', 'prose_lint.py'), '--json'],
            cwd=PROJECT_ROOT, capture_output=True, text=True)
        assert json.loads(run.stdout) == [], run.stdout


ROOT_GUIDE_SECTION = 'A workspace in a subdirectory'
ROOT_REFERENCE_SECTION = 'Project Root Ownership'


class TestProjectRootIsDocumented:
    """RULE-16 - the variable that resolves the project root is written down."""

    @pytest.mark.proof("purlin_prose", "PROOF-22", "RULE-16")
    def test_both_pages_name_purlin_project_root(self):
        body, _ = _heading_section(
            _read('docs/installation-guide.md'), ROOT_GUIDE_SECTION)
        assert body is not None, (
            f"docs/installation-guide.md has no section headed "
            f"'{ROOT_GUIDE_SECTION}'; the monorepo case has nowhere to live")

        # The order is the whole point: a reader who does not know the
        # environment variable beats the climb cannot explain what they see.
        for number, literal in (('1.', 'PURLIN_PROJECT_ROOT'),
                                ('2.', '.purlin/'),
                                ('3.', 'working directory')):
            item = [ln for ln in body.splitlines()
                    if ln.strip().startswith(number)]
            assert item, (
                f"the '{ROOT_GUIDE_SECTION}' section states no step {number}")
            assert literal in item[0], (
                f"step {number} of '{ROOT_GUIDE_SECTION}' does not name "
                f"{literal!r}: {item[0]!r}")

        for literal in ('.claude/settings.json', '"env"', 'project_root'):
            assert literal in body, (
                f"the '{ROOT_GUIDE_SECTION}' section no longer names "
                f"{literal!r}, one of the two ways to point the server at a "
                f"workspace that is not at the repository root")

        body, _ = _heading_section(
            _read('references/drift_criteria.md'), ROOT_REFERENCE_SECTION)
        assert body is not None, (
            f"references/drift_criteria.md has no section headed "
            f"'{ROOT_REFERENCE_SECTION}'")
        for literal in ('PURLIN_PROJECT_ROOT', 'config_engine.py',
                        'project_root'):
            assert literal in body, (
                f"the '{ROOT_REFERENCE_SECTION}' section of "
                f"references/drift_criteria.md does not name {literal!r}")


# ---------------------------------------------------------------------------
# RULE-17: the prerequisites name every interpreter Purlin will try
# ---------------------------------------------------------------------------

INSTALL_GUIDE = 'docs/installation-guide.md'
RESOLVER = 'scripts/purlin_python.sh'


def _prerequisites_section(text):
    """The body between `## Prerequisites` and the next `## ` heading."""
    lines = text.splitlines()
    start = lines.index('## Prerequisites')
    for offset, line in enumerate(lines[start + 1:], start + 1):
        if line.startswith('## '):
            return '\n'.join(lines[start + 1:offset])
    return '\n'.join(lines[start + 1:])


class TestInterpreterPrerequisite:
    """RULE-17: the names, the override, and the shell they are found from."""

    @pytest.mark.proof("purlin_prose", "PROOF-23", "RULE-17", tier="unit")
    def test_prerequisites_name_every_interpreter_and_the_override(self):
        section = _prerequisites_section(_read(INSTALL_GUIDE))

        for token in ('`python3`', '`python`', '`py`', '`PURLIN_PYTHON`',
                      '`sh`', 'Git for Windows'):
            assert token in section, (
                f"the Prerequisites section of {INSTALL_GUIDE} does not name "
                f"{token}, so a reader whose host carries it cannot tell that "
                f"Purlin would have used it:\n{section}")

        order = [section.index('`python3`'), section.index('`python`'),
                 section.index('`py`')]
        assert order == sorted(order), (
            "the three interpreter names are not in the order the resolver "
            f"tries them: {order}")

        # The code the section describes. A doc that names a candidate the
        # resolver never tries is the same defect as one that omits it.
        resolver = _read(RESOLVER)
        for name in ('PURLIN_PYTHON', 'python3', 'python', 'py'):
            assert name in resolver, (
                f"{RESOLVER} does not carry the candidate {name!r} the "
                f"prerequisites promise")


# ---------------------------------------------------------------------------
# RULE-18: the marketplace scope is three steps for a teammate, not one
# ---------------------------------------------------------------------------

SCOPE_TOKEN = '`--scope project`'
SCOPE_PAGES = ('README.md', 'docs/installation-guide.md')
SCOPE_STEPS = ('/plugin install purlin@purlin', '/reload-plugins',
               'purlin:init --force')


def _paragraphs_carrying(text, token):
    """Blank-line delimited paragraphs of `text` that contain `token`."""
    return [para for para in re.split(r'\n\s*\n', text) if token in para]


class TestMarketplaceScopeIsThreeSteps:
    """RULE-18: the flag stores an entry; the teammate still installs."""

    @pytest.mark.proof("purlin_prose", "PROOF-26", "RULE-18", tier="unit")
    def test_both_pages_name_all_three_teammate_steps(self):
        for rel in SCOPE_PAGES:
            text = _read(rel)
            assert text.strip(), (
                f"{rel} read back empty, so this proof would pass by "
                f"grepping nothing")

            paras = _paragraphs_carrying(text, SCOPE_TOKEN)
            assert len(paras) == 1, (
                f"{rel} carries {len(paras)} paragraphs naming "
                f"{SCOPE_TOKEN}; RULE-18 is about the one that explains the "
                f"flag, so exactly one must carry it")
            para = paras[0]

            for step in SCOPE_STEPS:
                assert step in para, (
                    f"the {SCOPE_TOKEN} paragraph of {rel} does not name "
                    f"{step!r}, one of the three steps a teammate still "
                    f"performs after cloning:\n{para}")

            for claim in ('automatically', 'automatic'):
                assert claim not in para, (
                    f"the {SCOPE_TOKEN} paragraph of {rel} still says "
                    f"{claim!r}; the flag stores a marketplace entry and "
                    f"installs nothing:\n{para}")
