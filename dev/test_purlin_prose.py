"""Proofs for specs/instructions/purlin_prose.md.

Every rule here is about prose, so every proof is a grep over committed files.
RULE-12 through RULE-15 are owned by `dev/prose_lint.py`, and the helpers that
walk the tree live there rather than here, so the proofs and the lint read the
same bytes the same way.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prose_lint  # noqa: E402
from prose_lint import (  # noqa: E402
    BANNED,
    HOMES,
    COMMENT_BLOCK_MARKERS,
    COMMENT_LINE_MARKERS,
    PATH_SCOPE,
    RUNTIME_PATHS,
    PROJECT_ROOT,
    SKILL_GLOB,
    AGENT_GLOB,
    HOME_SCOPE,
    _dash_hits,
    _norm_heading,
    _prose_files,
    _hits,
    _read,
    _scope_files,
    _sectioned_paragraphs,
    _tracked,
    _yaml_blocks,
    banned_strings,
    one_scope,
    scope_owners,
    paths_exist,
    repo_files,
    single_home,
    structure,
)


def _docs_markdown():
    return [f for f in _tracked('docs') if f.endswith('.md')]


class TestVhashHonesty:
    """RULE-2 - the compliance page states exactly what the hash reaches."""

    @pytest.mark.proof("purlin_prose","PROOF-3","RULE-2")
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

    @pytest.mark.proof("purlin_prose","PROOF-4","RULE-2")
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

    @pytest.mark.proof("purlin_prose","PROOF-5","RULE-2")
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

    @pytest.mark.proof("purlin_prose","PROOF-6","RULE-3")
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

    @pytest.mark.proof("purlin_prose","PROOF-8","RULE-5")
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

    @pytest.mark.proof("purlin_prose","PROOF-9","RULE-5")
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

    @pytest.mark.proof("purlin_prose","PROOF-10","RULE-6")
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

    @pytest.mark.proof("purlin_prose","PROOF-11","RULE-7")
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

    @pytest.mark.proof("purlin_prose","PROOF-13","RULE-8")
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

    @pytest.mark.proof("purlin_prose","PROOF-14","RULE-9")
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
# RULE-12 to RULE-15: the first four lints of dev/prose_lint.py.
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

    @pytest.mark.proof("purlin_prose","PROOF-17","RULE-12")
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

    @pytest.mark.proof("purlin_prose","PROOF-17","RULE-12")
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

    @pytest.mark.proof("purlin_prose","PROOF-17","RULE-12")
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

    @pytest.mark.proof("purlin_prose","PROOF-17","RULE-12")
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


    @pytest.mark.proof("purlin_prose", "PROOF-36", "RULE-12")
    def test_the_comment_row_reads_comments_and_not_string_literals(
            self, tmp_path):
        name, unit, pattern, scope, _min_files, allowlist, note = _row(
            BANNED, 'em-dash-comment')
        row = (name, unit, pattern, scope, 1, allowlist, note)

        languages = sorted(set(COMMENT_LINE_MARKERS) |
                           set(COMMENT_BLOCK_MARKERS))
        assert len(languages) >= 9, languages

        files, expected = [], {}
        for ext in languages:
            rel = 'scripts/probe/sample' + ext
            line_marker = COMMENT_LINE_MARKERS.get(ext)
            block = COMMENT_BLOCK_MARKERS.get(ext)
            lines, want = [], []
            if line_marker:
                lines.append(f"{line_marker[0]} one idea \u2014 and another")
                want.append(len(lines))
            lines.append('value = "printed \u2014 separator"')
            if block:
                lines.append(block[0] + ' opening')
                lines.append('a second idea \u2014 glossed ' + block[1])
                want.append(len(lines))
            _plant(tmp_path, rel, '\n'.join(lines) + '\n')
            files.append(rel)
            expected[rel] = want

        offenders = banned_strings(root=str(tmp_path), files=files,
                                   rows=(row,), strict=False)
        by_file = {}
        for offender in offenders:
            by_file.setdefault(offender.path, []).append(offender.line)
        assert by_file == expected, (
            f"the row must report every comment line and no string literal; "
            f"got {by_file}, wanted {expected}")

        scanned = _scope_files(scope, repo_files())
        assert len(scanned) >= 20, (
            f"the row resolved to {len(scanned)} files; the sweep would pass "
            f"by scanning nothing")
        assert banned_strings(rows=(row,), strict=True) == [], (
            "no comment line under scripts/ may carry a dash")


class TestPathsExistLint:
    """RULE-13 - a path in backticks reads as a link."""

    @pytest.mark.proof("purlin_prose","PROOF-18","RULE-13")
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


    @pytest.mark.proof("purlin_prose", "PROOF-35", "RULE-13")
    def test_generated_runtime_state_is_skipped_and_nothing_else_is(
            self, tmp_path):
        rel = 'docs/dashboard-guide.md'
        committed = _read(rel)
        assert '`.purlin/report-stamp.js`' in committed, (
            "the dashboard guide no longer names the stamp, so the "
            "fresh-worktree case below proves nothing")
        # A mirror of the checkout with one file missing: every other path
        # the guide names still resolves, so the stamp is the only variable.
        for entry in os.listdir(PROJECT_ROOT):
            if entry in ('.purlin', 'docs'):
                continue
            os.symlink(os.path.join(PROJECT_ROOT, entry),
                       os.path.join(str(tmp_path), entry))
        shutil.copytree(os.path.join(PROJECT_ROOT, 'docs'),
                        os.path.join(str(tmp_path), 'docs'))
        os.makedirs(os.path.join(str(tmp_path), '.purlin'))
        for entry in os.listdir(os.path.join(PROJECT_ROOT, '.purlin')):
            if entry != 'report-stamp.js':
                os.symlink(os.path.join(PROJECT_ROOT, '.purlin', entry),
                           os.path.join(str(tmp_path), '.purlin', entry))
        assert not os.path.exists(
            os.path.join(str(tmp_path), '.purlin', 'report-stamp.js')), (
            "the temp root must stand for a checkout that has not run a "
            "build, so the stamp must be absent")
        _plant(tmp_path, rel, committed)

        assert paths_exist(root=str(tmp_path), files=[rel],
                           strict=False) == [], (
            "a fresh worktree carries no .purlin/report-stamp.js, and the "
            "guide that names it is still correct")

        planted = 'The page also reads `.purlin/nonesuch.js` on focus.'
        injected = committed.rstrip('\n') + '\n\n' + planted + '\n'
        _plant(tmp_path, rel, injected)
        expected_line = injected.splitlines().index(planted) + 1
        offenders = paths_exist(root=str(tmp_path), files=[rel], strict=False)
        assert len(offenders) == 1, (
            f"only the planted token is outside RUNTIME_PATHS; got "
            f"{offenders}")
        only = offenders[0]
        assert only.path == rel and only.line == expected_line
        assert '.purlin/nonesuch.js' in only.message and \
            'does not resolve' in only.message, only.message

        assert paths_exist(strict=True) == [], (
            "every RUNTIME_PATHS entry and every PATH_ALLOWLIST token must "
            "still be named somewhere in the committed scope")

        with mock.patch.object(prose_lint, 'RUNTIME_PATHS',
                               RUNTIME_PATHS + ('.purlin/never-named.js',)):
            stale = paths_exist(strict=True)
        assert len(stale) == 1, (
            f"a skip nothing names must be reported; got {stale}")
        assert stale[0].path == 'dev/prose_lint.py'
        assert '.purlin/never-named.js' in stale[0].message and \
            'stale' in stale[0].message, stale[0].message


class TestStructureLint:
    """RULE-14 - a skill the loader cannot resolve is a skill nobody runs."""

    @pytest.mark.proof("purlin_prose","PROOF-19","RULE-14")
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

    @pytest.mark.proof("purlin_prose","PROOF-20","RULE-15")
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

    @pytest.mark.proof("purlin_prose", "PROOF-31", "RULE-15")
    def test_the_vhash_recipe_pasted_into_a_second_file_is_named(
            self, tmp_path):
        row = _row(HOMES, 'vhash segment list')
        pattern, home = row[2], row[3]
        receipt = _read(home)
        segments = [line for line in receipt.splitlines()
                    if pattern.search(line)]
        assert len(segments) == 3, (
            f"{home} carries {len(segments)} segment lines, not the three the "
            f"row requires")
        _plant(tmp_path, home, receipt)

        rel = 'references/hard_gates.md'
        gates = _read(rel)
        injected = gates.rstrip('\n') + '\n\n' + '\n'.join(segments) + '\n'
        _plant(tmp_path, rel, injected)

        offenders = single_home(root=str(tmp_path), files=[home, rel],
                                rows=(row,), strict=True)
        assert len(offenders) == 3, (
            f"every pasted segment must be reported; got {offenders}")
        assert [o.path for o in offenders] == [rel] * 3
        for offender in offenders:
            assert offender.lint == 'single_home'
            assert home in offender.message, offender.message

        assert single_home(rows=(row,), strict=True) == [], (
            f"the committed tree must carry the recipe only in {home}")

    @pytest.mark.proof("purlin_prose", "PROOF-32", "RULE-15")
    def test_the_design_formula_restated_in_a_guide_is_named(self, tmp_path):
        row = _row(HOMES, 'design formula')
        pattern, home = row[2], row[3]
        criteria = _read(home)
        assert len(_hits(criteria, pattern)) == 1, (
            f"{home} must state the design formula exactly once")
        _plant(tmp_path, home, criteria)

        rel = 'docs/testing-workflow-guide.md'
        guide = _read(rel)
        formula = 'PROVABLE / (PROVABLE + LOOSE + UNPROVABLE)'
        injected = guide.rstrip('\n') + '\n\nDesign score = ' + formula + '\n'
        _plant(tmp_path, rel, injected)
        expected = len(injected.rstrip('\n').splitlines())

        offenders = single_home(root=str(tmp_path), files=[home, rel],
                                rows=(row,), strict=True)
        assert len(offenders) == 1, (
            f"the restated formula must be reported once; got {offenders}")
        assert offenders[0].path == rel and offenders[0].line == expected, (
            f"expected {rel}:{expected}, got {offenders[0]}")
        assert offenders[0].lint == 'single_home'
        assert home in offenders[0].message, offenders[0].message

        assert single_home(rows=(row,), strict=True) == [], (
            f"the committed tree must carry the formula only in {home}")


    @pytest.mark.proof("purlin_prose","PROOF-24","RULE-15")
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

    @pytest.mark.proof("purlin_prose","PROOF-21","RULE-12")
    def test_scoped_file_counts_and_a_clean_run_on_the_real_tree(self):
        files = repo_files()
        floors = {'em-dash': 90, 'em-dash-comment': 20, 'promise': 40,
                  'windows-tier': 40, 'approval': 1, 'retired-format': 25,
                  'anchor-home': 35, 'slash-prefix': 80, 'last-gate': 10}
        for name, floor in floors.items():
            scope = _row(BANNED, name)[3]
            count = len(_scope_files(scope, files))
            assert count >= floor, (
                f"the {name!r} row resolved to {count} files, under its floor "
                f"of {floor}; the sweep would pass by scanning nothing")
        assert len(_scope_files(PATH_SCOPE, files)) >= 27
        assert len(_scope_files((SKILL_GLOB,), files)) >= 12
        assert len(_scope_files((AGENT_GLOB,), files)) >= 2
        assert len(_scope_files(HOME_SCOPE, files)) >= 40

        run = subprocess.run(
            [sys.executable, os.path.join('dev', 'prose_lint.py')],
            cwd=PROJECT_ROOT, capture_output=True, text=True)
        offenders = [line for line in run.stdout.splitlines()
                     if re.search(r': (banned_strings|paths_exist|structure'
                                  r'|single_home|banned_paths): ', line)]
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

    @pytest.mark.proof("purlin_prose","PROOF-22","RULE-16")
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

    @pytest.mark.proof("purlin_prose","PROOF-23","RULE-17", tier="unit")
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


# ---------------------------------------------------------------------------
# RULE-19: a documented cleanup names its files instead of globbing them
# ---------------------------------------------------------------------------

_BASH_BLOCK = re.compile(r'^```(?:ba)?sh\n(.*?)^```', re.MULTILINE | re.DOTALL)

CLEANUP_PAGES = ('README.md', 'docs/installation-guide.md')
PRE_090_SCRIPTS = ('pl-init.sh', 'pl-run.sh')


def _bash_rm_lines(rel):
    """(lineno, line) per `rm` line inside a fenced bash block of `rel`."""
    text = _read(rel)
    lines = text.splitlines()
    out = []
    for block in _BASH_BLOCK.findall(text):
        for line in block.splitlines():
            if line.strip().split()[:1] != ['rm']:
                continue
            out.append((lines.index(line) + 1, line))
    return out


class TestCleanupSnippetsNameTheirFiles:
    """RULE-19: no `rm` in a pasteable snippet carries a glob."""

    @pytest.mark.proof("purlin_prose", "PROOF-27", "RULE-19", tier="unit")
    def test_no_rm_line_in_a_bash_fence_carries_a_star(self):
        scanned = [('README.md', line_no, line)
                   for line_no, line in _bash_rm_lines('README.md')]
        for rel in _docs_markdown():
            scanned += [(rel, line_no, line)
                        for line_no, line in _bash_rm_lines(rel)]

        assert len(scanned) >= 8, (
            f"only {len(scanned)} `rm` lines were found in the fenced bash "
            f"blocks of README.md and docs/; the sweep would pass by reading "
            f"nothing")

        offenders = [f"{rel}:{line_no}: {line.strip()}"
                     for rel, line_no, line in scanned if '*' in line]
        assert not offenders, (
            "a cleanup snippet a reader pastes at their own project root "
            "removes a glob, which takes files the project authored:\n"
            + "\n".join(offenders))

        for rel in CLEANUP_PAGES:
            text = _read(rel)
            for name in PRE_090_SCRIPTS:
                assert name in text, (
                    f"{rel} no longer names {name!r}, one of the two scripts "
                    f"the pre-0.9.0 layout left at the project root; the glob "
                    f"was dropped rather than replaced")


# ---------------------------------------------------------------------------
# RULE-20: the installed shell harness is purlin-proof.sh
# ---------------------------------------------------------------------------

PLUGIN_SOURCE = 'scripts/proof/shell_purlin.sh'
INSTALLED_HARNESS = '.purlin/plugins/purlin-proof.sh'
LEGACY_HARNESS = '.purlin/plugins/shell_purlin.sh'
HARNESS_GUIDES = ('docs/installation-guide.md',
                  'docs/testing-workflow-guide.md')
FRAMEWORKS = 'references/supported_frameworks.md'


def _installed_as(rel, framework):
    """The `Installed as` cell of the row naming `framework`, by header."""
    header = None
    for line in _read(rel).splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if header is None:
            if 'Installed as' in cells:
                header = cells.index('Installed as')
            continue
        if framework in cells[:1] and len(cells) > header:
            return cells[header]
    return None


class TestInstalledShellHarnessName:
    """RULE-20: `shell_purlin.sh` is a source path and nothing else."""

    @pytest.mark.proof("purlin_prose", "PROOF-28", "RULE-20", tier="unit")
    def test_docs_name_purlin_proof_sh(self):
        scanned = ['README.md'] + _docs_markdown()
        assert len(scanned) >= 8, (
            f"only {len(scanned)} files were read; the sweep would pass by "
            f"grepping nothing")

        offenders = []
        for rel in scanned:
            for lineno, line in enumerate(_read(rel).splitlines(), 1):
                start = 0
                while True:
                    at = line.find('shell_purlin.sh', start)
                    if at < 0:
                        break
                    if not line[:at].endswith('scripts/proof/'):
                        offenders.append(f"{rel}:{lineno}: {line.strip()}")
                    start = at + 1
        assert not offenders, (
            "`shell_purlin.sh` is the plugin source under `scripts/proof/`; "
            "the copy a project carries is `purlin-proof.sh`:\n"
            + "\n".join(offenders))

        for rel in HARNESS_GUIDES:
            text = _read(rel)
            assert INSTALLED_HARNESS in text, (
                f"{rel} no longer tells a shell user what to source; "
                f"{INSTALLED_HARNESS} is absent")
            assert LEGACY_HARNESS not in text, (
                f"{rel} still sources {LEGACY_HARNESS}, a path no "
                f"initialized project carries")

        cell = _installed_as(FRAMEWORKS, '**Shell**')
        assert cell == '`purlin-proof.sh`', (
            f"the shell row's `Installed as` cell in {FRAMEWORKS} reads "
            f"{cell!r}; the two guides teach `purlin-proof.sh`, and the "
            f"scaffolder copies the plugin under whatever this column says")


# ---------------------------------------------------------------------------
# RULE-21: one .purlin/ layout, drawn the same way in both places
# ---------------------------------------------------------------------------

_FENCE = re.compile(r'^```[^\n]*\n(.*?)^```', re.MULTILINE | re.DOTALL)

TREE_PAGES = ('README.md', 'docs/index.md')
PURLIN_ENTRIES = {
    'cache/', 'config.json', 'config.local.json', 'hooks/', 'plugin-root',
    'plugins/', 'report-data.js', 'report-stamp.js', 'runtime/',
}


def _fenced_blocks(rel):
    return _FENCE.findall(_read(rel))


def _purlin_tree(rel):
    """The entries of the fenced tree whose first line is `.purlin/`."""
    for block in _fenced_blocks(rel):
        lines = block.splitlines()
        if not lines or lines[0].rstrip() != '.purlin/':
            continue
        entries = set()
        for line in lines[1:]:
            if not line.startswith('  '):
                break
            if line.startswith('   '):
                continue
            entries.add(line.strip().split()[0])
        return block, entries
    return None, set()


class TestArchitectureTreesAgree:
    """RULE-21: plugin content is not drawn inside the project tree."""

    @pytest.mark.proof("purlin_prose", "PROOF-29", "RULE-21", tier="unit")
    def test_both_purlin_trees_name_the_same_entries(self):
        trees = {}
        for rel in TREE_PAGES:
            block, entries = _purlin_tree(rel)
            assert block is not None, (
                f"{rel} carries no fenced block whose first line is "
                f"`.purlin/`; there is nothing to compare")
            assert len(entries) >= 9, (
                f"the `.purlin/` tree in {rel} names {len(entries)} entries, "
                f"fewer than the nine an initialized project holds: "
                f"{sorted(entries)}")
            trees[rel] = (block, entries)

        left, right = (trees[rel][1] for rel in TREE_PAGES)
        assert left == right, (
            f"the two `.purlin/` trees disagree; "
            f"only in {TREE_PAGES[0]}: {sorted(left - right)}; "
            f"only in {TREE_PAGES[1]}: {sorted(right - left)}")
        assert left == PURLIN_ENTRIES, (
            f"the drawn `.purlin/` layout is not the one a project holds; "
            f"drawn but not held: {sorted(left - PURLIN_ENTRIES)}; "
            f"held but not drawn: {sorted(PURLIN_ENTRIES - left)}")

        project_tree = trees['README.md'][0]
        for plugin_dir in ('tools/', 'scripts/'):
            assert plugin_dir not in project_tree, (
                f"README's project tree draws {plugin_dir}, which is plugin "
                f"content `purlin:init` never writes into a project:\n"
                f"{project_tree}")

        plugin_tree = [b for b in _fenced_blocks('README.md')
                       if 'tools/' in b and 'scripts/' in b]
        assert plugin_tree, (
            "README carries no fenced tree naming both `scripts/` and "
            "`tools/`; the plugin content was deleted rather than moved into "
            "a tree of its own")


# ---------------------------------------------------------------------------
# RULE-5: a skill call is not a shell command either
# ---------------------------------------------------------------------------

COLLAB_GUIDE = 'docs/collaboration-guide.md'
ANCHOR_CHECK = 'purlin:anchor sync --check-only'


class TestSkillCallsStayOutOfBashBlocks:
    """RULE-5: no fenced bash block under docs/ runs a `purlin:` line."""

    @pytest.mark.proof("purlin_prose", "PROOF-30", "RULE-5", tier="unit")
    def test_no_bash_block_carries_a_skill_call(self):
        blocks = 0
        offenders = []
        for rel in _docs_markdown():
            text = _read(rel)
            lines = text.splitlines()
            for block in _BASH_BLOCK.findall(text):
                blocks += 1
                for line in block.splitlines():
                    token = line.strip().split(' ')[0]
                    if not token.startswith('purlin:'):
                        continue
                    offenders.append(
                        f"{rel}:{lines.index(line) + 1}: {line.strip()}")

        assert blocks >= 6, (
            f"only {blocks} fenced bash blocks were extracted from docs/; "
            f"the sweep would pass by reading none")
        assert not offenders, (
            "a fenced bash block runs a Claude Code skill; a reader who "
            "pastes it into a script or a CI step gets `command not "
            "found`:\n" + "\n".join(offenders))

        assert ANCHOR_CHECK in _read(COLLAB_GUIDE), (
            f"{COLLAB_GUIDE} no longer names {ANCHOR_CHECK!r}; the call was "
            f"deleted rather than moved into the prose beside the block")

# RULE-20 and RULE-21: a version literal and a draft marker that outlived it.

# RULE-22 and RULE-23: a version literal and a draft marker that outlived it.
# ---------------------------------------------------------------------------

VERSION_TOKEN = re.compile(r'(Criteria|Format)-Version:\s*(\S+)')

#: The one file allowed to quote the draft marker: the rule that bans it.
PLACEHOLDER_RULE_FILE = 'specs/instructions/purlin_prose.md'
PLACEHOLDER = 'Generated by purlin:spec-from-code'


class TestVersionLiteralsAndDraftMarkers:
    """RULE-22, RULE-23 - a number and a marker that must not be copied."""

    @pytest.mark.proof("purlin_prose","PROOF-33","RULE-22")
    def test_no_skill_or_agent_pins_a_version_number(self):
        found = []
        offenders = []
        for rel in _tracked('skills', 'agents'):
            try:
                text = _read(rel)
            except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                for match in VERSION_TOKEN.finditer(line):
                    token = match.group(2).rstrip(').,`')
                    found.append((rel, lineno, token))
                    if token != 'N':
                        offenders.append(f"{rel}:{lineno}: "
                                         f"{match.group(1)}-Version: {token}")
        assert len(found) >= 3, (
            f"only {len(found)} version tokens found under skills/ and "
            f"agents/; the sweep would pass by reading none: {found}")
        assert not offenders, (
            "a skill or agent pins a version number instead of printing `N`, "
            "so it is a second copy of a number that is bumped elsewhere:\n"
            + "\n".join(offenders))

    @pytest.mark.proof("purlin_prose","PROOF-34","RULE-23")
    def test_no_spec_still_carries_the_generator_draft_marker(self):
        specs = [rel for rel in _tracked('specs') if rel.endswith('.md')]
        assert len(specs) >= 40, (
            f"only {len(specs)} specs read; the sweep would pass on an empty "
            f"tree")
        assert PLACEHOLDER in _read(PLACEHOLDER_RULE_FILE), (
            f"{PLACEHOLDER_RULE_FILE} no longer quotes {PLACEHOLDER!r}, so "
            f"its exemption below is stale and must be deleted with the "
            f"quotation")
        offenders = [rel for rel in specs
                     if rel != PLACEHOLDER_RULE_FILE
                     and PLACEHOLDER in _read(rel)]
        assert not offenders, (
            "these specs still carry the draft marker "
            "`purlin:spec-from-code` leaves on an unreviewed draft, so they "
            "read as unreviewed:\n" + "\n".join(offenders))


class TestEveryProseFileHasOneHome:
    """RULE-24 - a file no spec names is a file no rule answers for."""

    @pytest.mark.proof("purlin_prose", "PROOF-37", "RULE-24")
    def test_every_shipped_prose_file_is_in_exactly_one_scope(self, tmp_path):
        owners = scope_owners()
        assert len(owners) >= 40, (
            f"resolved {len(owners)} prose files; the lint would pass by "
            f"reading nothing")
        named = sorted({s for specs in owners.values() for s in specs})
        assert len(named) >= 7, named
        assert one_scope() == [], (
            "every shipped prose file must be named in exactly one "
            "`> Scope:`")

        excluded = 'specs/instructions/purlin_version.md'
        assert excluded not in named, (
            "purlin_version names files it does not own, so it must not be "
            "read as an owner")
        assert 'skills/init/SKILL.md' in _read(excluded), (
            "the exclusion is load-bearing only while purlin_version really "
            "does name a file another spec owns")

        specs = _scope_files(('specs/instructions/*.md', 'specs/tools/*.md'),
                             _tracked('specs'))
        for rel in specs:
            _plant(tmp_path, rel, _read(rel))

        target = 'references/rule_examples.md'
        refs = 'specs/instructions/purlin_references.md'
        original = _read(refs)
        _plant(tmp_path, refs,
               original.replace(', ' + target, '', 1))
        offenders = one_scope(root=str(tmp_path))
        assert len(offenders) == 1, f"expected the orphan; got {offenders}"
        assert offenders[0].path == target
        assert offenders[0].lint == 'one_scope'
        assert 'no spec' in offenders[0].message, offenders[0].message

        _plant(tmp_path, refs, original)
        prose = 'specs/instructions/purlin_prose.md'
        body = _read(prose)
        line = [l for l in body.splitlines() if l.startswith('> Scope:')][0]
        _plant(tmp_path, prose, body.replace(line, line + ', ' + target, 1))
        offenders = one_scope(root=str(tmp_path))
        assert len(offenders) == 1, f"expected the double home; got {offenders}"
        assert offenders[0].path == target
        assert '2 specs' in offenders[0].message, offenders[0].message
        assert refs in offenders[0].message and prose in offenders[0].message


GLOSSARY = 'references/glossary.md'


def _table_rows(text, heading):
    """The cell lists of the markdown table under `## <heading>`."""
    body = re.search(rf'^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)',
                     text, re.MULTILINE | re.DOTALL)
    assert body, f"{GLOSSARY} carries no `## {heading}` section"
    rows = []
    for line in body.group(1).splitlines():
        line = line.strip()
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if all(set(c) <= set('-: ') for c in cells):
            continue
        rows.append(cells)
    return rows[1:] if rows else rows


def _retired_terms(text):
    """The first cell of every Retired-terms row, backticks stripped."""
    return [row[0].replace('`', '').strip()
            for row in _table_rows(text, 'Retired terms')]


class TestGlossaryIsTheSourceOfTheRetiredRows:
    """RULE-25 - the Retired table and the lint's rows are one list."""

    @pytest.mark.proof("purlin_prose", "PROOF-38", "RULE-25")
    def test_the_retired_table_and_the_generated_rows_agree_both_ways(
            self, tmp_path):
        from prose_lint import (GLOSSARY_RETIRED, GLOSSARY_HOME,
                                GLOSSARY_SECTION)

        text = _read(GLOSSARY)
        table = _retired_terms(text)
        assert len(table) >= 18, (
            f"{GLOSSARY} retires {len(table)} terms; the comparison would "
            f"pass on a table nobody wrote")

        claimed = []
        for entry in GLOSSARY_RETIRED:
            claimed.extend(entry[0])
        assert len(claimed) == len(set(claimed)), (
            f"a term is claimed by two rows: {sorted(claimed)}")
        assert set(table) == set(claimed), (
            f"the glossary retires {sorted(set(table) - set(claimed))} with "
            f"no lint row, and the lint enforces "
            f"{sorted(set(claimed) - set(table))} with no glossary row")

        by_name = {row[0]: row for row in BANNED}
        for entry in GLOSSARY_RETIRED:
            name = entry[1]
            assert name in by_name, f"{name} is generated but not in BANNED"
            assert by_name[name] == tuple(entry[1:]), (
                f"the {name} row of BANNED is not the row the glossary "
                f"generates")
            allowlist = entry[6]
            assert (GLOSSARY_HOME, GLOSSARY_SECTION) in allowlist, (
                f"{name} does not exempt the table that retires the term")

        # Direction one: a term the lint enforces that the table dropped.
        dropped = [t for t in table if t != 'platform tier']
        assert set(claimed) - set(dropped) == {'platform tier'}, (
            "deleting the `platform tier` row must leave exactly that term "
            "enforced with nothing retiring it")

        # Direction two: a term the table retires that no row enforces.
        added = table + ['gauge score']
        assert set(added) - set(claimed) == {'gauge score'}, (
            "a new row with no lint row must be reported as unenforced")

        row = next(tuple(e[1:]) for e in GLOSSARY_RETIRED
                   if e[1] == 'platform-tier')
        index = _read('docs/index.md')
        planted = index.rstrip('\n') + '\n\nA runner is held for a platform tier.\n'
        _plant(tmp_path, 'docs/index.md', planted)
        offenders = banned_strings(
            root=str(tmp_path), files=['docs/index.md'],
            rows=((row[0], row[1], row[2], row[3], 1, (), row[6]),),
            strict=False)
        assert len(offenders) == 1, f"expected one; got {offenders}"
        only = offenders[0]
        assert only.path == 'docs/index.md' and only.lint == 'banned_strings'
        assert only.line == planted.splitlines().index(
            'A runner is held for a platform tier.') + 1
        assert only.message.startswith('platform-tier:'), only.message


class TestTheCIGateJobHasOneName:
    """RULE-26 - one name for the job, one mention of the token it prints."""

    NAMES = re.compile(
        r'(?i)\b(gate job|gate script|CI gate|CI job|verification gate)\b')
    #: The job id on its own: `purlin-verify-gate.yml` and `verify-gate.yml`
    #: are file names, not the id, so neither is a mention of it.
    TOKEN = re.compile(r'(?<![\w-])verify-gate(?![\w.])')
    GATE = 'scripts/ci/verify_gate.py'

    def _prose(self):
        files = [f for f in _tracked('docs', 'references', 'skills', 'agents')
                 if f.endswith('.md')]
        return files + ['README.md']

    @pytest.mark.proof("purlin_prose", "PROOF-39", "RULE-26", tier="unit")
    def test_one_name_for_the_job_and_one_mention_of_its_token(self):
        collected = 0
        offenders = []
        token_lines = []
        for rel in self._prose():
            text = _read(rel)
            for lineno, line in _hits(text, self.NAMES):
                collected += 1
                if len(self.NAMES.findall(line)) != line.count('CI gate job'):
                    offenders.append(f"{rel}:{lineno}: {line.strip()}")
            for lineno, line in _hits(text, self.TOKEN):
                token_lines.append((rel, lineno, line))

        assert collected >= 18, (
            f"only {collected} lines name the job; the sweep would pass by "
            f"reading nothing")
        assert offenders == [], (
            "the job is `the CI gate job` everywhere in the prose:\n"
            + "\n".join(offenders))

        assert len(token_lines) == 1, (
            f"`verify-gate:` belongs in one place, the Layer 3 row of "
            f"references/hard_gates.md; found {token_lines}")
        rel, _lineno, line = token_lines[0]
        assert rel == 'references/hard_gates.md', rel
        first_cell = line.strip().strip('|').split('|')[0].strip()
        assert first_cell.startswith('**Layer 3:'), first_cell

        gate = _read(self.GATE)
        printed = [l for l in gate.splitlines()
                   if re.search(r'''["']verify-gate: ''', l)]
        assert len(printed) >= 8, (
            f"{self.GATE} writes {len(printed)} lines opening "
            f"`verify-gate: `; the reference names a token the script does "
            f"not print")


def _collapse(text):
    return ' '.join(text.split())


def _skills_table(text, heading_re):
    """{skill: purpose} from the first `## Skills`-style table of `text`."""
    section = re.search(heading_re + r'(.*?)(?=^##\s|\Z)', text,
                        re.MULTILINE | re.DOTALL)
    assert section, f"no section matching {heading_re!r}"
    out = {}
    for line in section.group(1).splitlines():
        match = re.match(r'^\|\s*`purlin:([a-z][a-z-]*)`\s*\|([^|]*)\|', line)
        if match:
            out[match.group(1)] = _collapse(match.group(2))
    return out


class TestOneSkillOneLiner:
    """RULE-27 - the Quick Reference Purpose cell is the only home."""

    @staticmethod
    def _quick_reference():
        text = _read('references/purlin_commands.md')
        return _skills_table(text, r'^##\s+Quick Reference\s*$')

    @staticmethod
    def _index_first_sentences():
        text = _read('docs/index.md')
        block = re.search(r'^Key skills:\s*$(.*?)(?=^##\s|\Z)', text,
                          re.MULTILINE | re.DOTALL)
        assert block, "docs/index.md carries no key-skills list"
        out = {}
        for raw in re.split(r'\n(?=- )', block.group(1).strip('\n')):
            match = re.match(r'^-\s+`purlin:([a-z][a-z-]*)`:\s*(.*)$',
                             _collapse(raw), re.DOTALL)
            if not match:
                continue
            body = match.group(2)
            cut = re.search(r'\.\s', body)
            out[match.group(1)] = (body[:cut.start()] if cut
                                   else body).strip()
        return out

    @pytest.mark.proof("purlin_prose", "PROOF-40", "RULE-27", tier="unit")
    def test_five_surfaces_carry_the_same_sentence_per_skill(self):
        canonical = self._quick_reference()
        on_disk = sorted(d.split('/')[1]
                         for d in _tracked('skills')
                         if d.endswith('/SKILL.md'))
        assert len(canonical) == 12, sorted(canonical)
        assert sorted(canonical) == on_disk, (
            f"the Quick Reference names {sorted(canonical)}; the tree ships "
            f"{on_disk}")

        readme = _skills_table(_read('README.md'), r'^##\s+Skills\s*$')
        agent = _skills_table(_read('agents/purlin.md'),
                              r'^##\s+Skills\b[^\n]*$')
        index = self._index_first_sentences()

        mismatches = []
        for name, purpose in sorted(canonical.items()):
            block = _frontmatter_of(f'skills/{name}/SKILL.md')
            surfaces = {
                f'skills/{name}/SKILL.md description': block,
                'README.md Skills table': readme.get(name),
                'agents/purlin.md Skills table': agent.get(name),
                'docs/index.md key-skills bullet': index.get(name),
            }
            for where, value in surfaces.items():
                if value is None:
                    mismatches.append(f"{name}: {where} carries no entry")
                elif _collapse(value) != purpose:
                    mismatches.append(
                        f"{name}: {where} reads {_collapse(value)!r}; the "
                        f"Quick Reference reads {purpose!r}")
        assert mismatches == [], "\n".join(mismatches)

        help_block = re.search(r'^```\nPurlin: Spec-Driven Development\n(.*?)^```',
                               _read('references/purlin_commands.md'),
                               re.MULTILINE | re.DOTALL)
        assert help_block, "the ASCII help block is gone"
        assert any(purpose not in help_block.group(1)
                   for purpose in canonical.values()), (
            "every canonical sentence fits the padded help block, so the "
            "exclusion is no longer carrying anything")


def _frontmatter_of(rel):
    block = prose_lint._frontmatter(_read(rel))
    return None if block is None else prose_lint._frontmatter_field(
        block, 'description')
