"""Tests for the packaged skills under tools/: qa_report and
pm_anchor_userstories.

`tools/QA/purlin-qa-report.md` is a skill a QA reader runs against someone
else's repository. Two things go wrong there that nothing else in this project
catches: an instruction that leaks a credential, and a report that claims more
than the digest recorded. `tools/PM/purlin-anchor-userstories.md` is a skill a
product manager runs to write an anchor spec, and what goes wrong there is that
the spec lands somewhere the Purlin plugin never reads. These proofs read the
shipped markdown, and one proof per tool reads the zip beside it, because the
zip is what a user installs.
"""

import os
import re
import zipfile

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
TOOLS = os.path.join(PROJECT_ROOT, 'tools')
QA_MD = os.path.join(TOOLS, 'QA', 'purlin-qa-report.md')
PM_MD = os.path.join(TOOLS, 'PM', 'purlin-anchor-userstories.md')
ANCHOR_FORMAT = os.path.join(PROJECT_ROOT, 'references', 'formats',
                             'anchor_format.md')
COMMIT_CONVENTIONS = os.path.join(PROJECT_ROOT, 'references',
                                  'commit_conventions.md')


def _read(path):
    with open(path) as f:
        return f.read()


def _assert_skill_zip_matches_markdown(folder, name):
    """qa_report PROOF-6 and pm_anchor_userstories PROOF-5 share this.

    Each tool's `.skill` is a zip holding one `<name>/SKILL.md`; the bytes must
    equal the sibling `.md`, which is the file the rules above grep.
    """
    md_path = os.path.join(TOOLS, folder, f'{name}.md')
    skill_path = os.path.join(TOOLS, folder, f'{name}.skill')
    assert os.path.isfile(md_path), md_path
    assert os.path.isfile(skill_path), skill_path

    with open(md_path, 'rb') as f:
        md_bytes = f.read()
    with zipfile.ZipFile(skill_path) as zf:
        names = zf.namelist()
        assert names == [f'{name}/SKILL.md'], (
            f"{skill_path} holds {names}, expected exactly "
            f"['{name}/SKILL.md']")
        packed = zf.read(names[0])

    assert packed == md_bytes, (
        f"{skill_path} ships {len(packed)} bytes while {md_path} has "
        f"{len(md_bytes)}; run `bash dev/pack_tools.sh`")


def _offending_lines(text, needle, lower=False):
    """Every (line number, line) carrying `needle`, so a failure names it."""
    hay = text.lower() if lower else text
    return [(i, line) for i, line in enumerate(hay.splitlines(), 1)
            if needle in line]


def _template_shape(text, section_heading):
    """The headings and the `> Field:` names of the fenced markdown template
    under `section_heading`, in the order they are written."""
    start = text.index(section_heading)
    fence = text.index('```markdown', start) + len('```markdown')
    end = text.index('```', fence)
    block = text[fence:end]
    headings = [line.strip() for line in block.splitlines()
                if line.startswith('#')]
    fields = re.findall(r'^> ([A-Za-z][\w-]*):', block, re.MULTILINE)
    return headings, fields


class TestNoCredentialInAUrl:
    """RULE-1: a skill that teaches `https://user:token@host` teaches the leak."""

    @pytest.mark.proof("qa_report", "PROOF-1", "RULE-1")
    def test_no_credential_bearing_url_and_a_real_private_repo_path(self):
        content = _read(QA_MD)

        # The placeholder form the file used to carry.
        placeholder = re.findall(r'://<[A-Z_]+>:<[A-Z_]+>@', content)
        assert placeholder == [], (
            f"credential placeholders in a URL: {placeholder}")

        # The general form, literal or otherwise. `git@github.com:org/repo`
        # has no `://` and is not matched.
        general = re.findall(r'://[^/\s]+:[^/\s]+@', content)
        assert general == [], f"credential-bearing URLs: {general}"

        # The private-repo path must still be there, so the proof cannot pass
        # on a file that simply deleted the auth section.
        assert 'gh repo clone' in content, (
            "the file must reach a private repo through `gh repo clone`")
        assert 'credential helper' in content, (
            "the file must name the credential-helper route for hosts "
            "without `gh`")


class TestDigestFieldsTheReportMustRead:
    """RULE-2: every field the report is supposed to repeat, one assertion
    each, so a failure names the field that went missing."""

    @pytest.mark.proof("qa_report", "PROOF-2", "RULE-2")
    def test_each_field_name_is_read_and_the_two_scores_stay_separate(self):
        content = _read(QA_MD)

        for field in ('audit_summary.coverage', 'measured', 'total',
                      'assessed', 'weighted', 'auditors', 'vhash',
                      'receipt.vhash_version', 'receipt.test_run_commit',
                      'evidence_stale', 'git_sha'):
            assert field in content, (
                f"the skill never names the digest field {field!r}, so the "
                f"report cannot report it")

        # `assessed` and `weighted` are two numbers, never one. The file has to
        # say so in one place, not merely mention both words.
        separately = [
            sent for sent in re.split(r'(?<=[.!?])\s+', content)
            if 'assessed' in sent and 'weighted' in sent
            and 'separate' in sent
        ]
        assert separately, (
            "no sentence names `assessed` and `weighted` together as separate "
            "numbers; a report that substitutes one for the other is the "
            "failure this rule exists for")

        # The two fields that older digests omit are read defensively.
        for field in ('auditors', 'evidence_stale'):
            near = [
                m for m in re.finditer(re.escape(field), content)
                if 'defensive' in content[max(0, m.start() - 300):
                                          m.end() + 300]
            ]
            assert near, (
                f"{field} is named but never described as read defensively; "
                f"a digest written before the field existed omits it")


class TestVerifiedWording:
    """RULE-3: VERIFIED is a statement about evidence, not an approval."""

    @pytest.mark.proof("qa_report", "PROOF-3", "RULE-3")
    def test_verified_is_described_as_proved_everywhere_with_a_matching_receipt(self):
        content = _read(QA_MD)
        wanted = ('all rules proved on every declared platform and a receipt '
                  'matches')
        assert wanted in content, (
            f"the skill must describe VERIFIED as {wanted!r}")
        retired = ('every rule proved, receipt current, and every declared '
                   'platform proved')
        assert retired not in content, (
            "the retired VERIFIED wording is back; it reads as three boxes "
            "ticked rather than as a claim about evidence")


class TestUncommittedIsReported:
    """RULE-4: a non-empty `uncommitted` in a committed digest is possible
    three ways, and each means the counts describe a different tree."""

    @pytest.mark.proof("qa_report", "PROOF-4", "RULE-4")
    def test_uncommitted_paragraph_names_all_three_causes(self):
        content = _read(QA_MD)
        start = content.index('`uncommitted`**')
        end = content.index('Each feature has:', start)
        section = content[start:end]

        assert 'non-empty' in section, section[:300]
        for cause in ('`warn`', '`off`', 'PURLIN_SKIP_DIGEST=1', 'fail-open'):
            assert cause in section, (
                f"the `uncommitted` paragraph never names {cause}; a reader "
                f"told the field is impossible will ignore it")

        assert 'ignore it' not in section, (
            "the paragraph still tells the reader to ignore `uncommitted`; "
            "the three causes above are counterexamples to the reasoning "
            "that instruction rested on")


class TestNoHumanJudgmentClaims:
    """RULE-5: no digest field records a person accepting a result."""

    @pytest.mark.proof("qa_report", "PROOF-5", "RULE-5")
    def test_no_signoff_or_compliance_claims_and_the_prohibition_is_stated(self):
        content = _read(QA_MD)
        low = content.lower()
        for banned in ('signed off', 'sign off', 'signed-off', 'sign-off',
                       'compliance status'):
            assert banned not in low, (
                f"{banned!r} appears in the QA skill; a receipt records that "
                f"tests ran, not that anyone accepted the result")

        # The prohibition itself must be stated, so deleting the rule fails
        # here even while the banned strings stay absent.
        rules = content[content.index('## Rules for the Report'):]
        for word in ('compliant', 'approved', 'cleared', 'certified'):
            assert word in rules, (
                f"the report rules must name {word!r} as a word the report "
                f"never uses")


class TestSkillArchivesMatchTheMarkdown:
    """RULE-6: the `.md` is reviewed and the `.skill` is installed."""

    @pytest.mark.proof("qa_report", "PROOF-6", "RULE-6")
    def test_the_qa_skill_zip_holds_one_skill_md_equal_to_its_sibling(self):
        _assert_skill_zip_matches_markdown('QA', 'purlin-qa-report')


@pytest.mark.proof("qa_report", "PROOF-7", "RULE-7", tier="unit")
def test_the_field_table_documents_the_digest_schema_version():
    """qa_report RULE-7 — a QA reader told to read a digest must be told what
    to do with one written by a newer Purlin."""
    text = _read(QA_MD)
    rows = [line for line in text.splitlines()
            if line.startswith('|') and '`schema_version`' in line]
    assert len(rows) == 1, (
        f"expected exactly one digest field-table row for schema_version, got {len(rows)}")
    row = rows[0]
    assert 'version 1' in row, (
        "the row must say a digest without the key is version 1: " + row)
    assert 'version 3' in row, (
        "the row must name the version the skill reads: " + row)
    assert 'newer' in row, (
        "the row must tell the report to say so when the digest is newer: " + row)


@pytest.mark.proof("qa_report", "PROOF-8", "RULE-8", tier="unit")
def test_the_skill_resolves_a_referenced_rule_before_walking_rules():
    """qa_report RULE-8 - a reference read without resolving it is a rule with
    no description and no status, which a report prints as uncovered."""
    text = _read(QA_MD)
    rows = [line for line in text.splitlines()
            if line.startswith('|') and '`shared_rules`' in line]
    assert len(rows) == 1, (
        f"expected exactly one digest field-table row for shared_rules, "
        f"got {len(rows)}")
    assert '`ref`' in rows[0], (
        "the row must name the mark on the entry it resolves: " + rows[0])

    bullets = [line for line in text.splitlines()
               if line.startswith('- `rules[]`')]
    assert len(bullets) == 1, (
        f"expected exactly one `rules[]` entry, got {len(bullets)}")
    bullet = bullets[0]
    for token in ('`ref`', '`shared_rules`', 'Resolve'):
        assert token in bullet, (
            f"the `rules[]` entry must carry {token}: " + bullet)
    assert 'no `ref`' in bullet and 'is already complete' in bullet, (
        "the entry must say an old digest, whose rules are all inline, is read "
        "as it is: " + bullet)


class TestThePmSkillWritesWherePurlinReads:
    """pm_anchor_userstories: the output of a product manager's session has to
    be a file the plugin parses, named the way every other spec is named."""

    @pytest.mark.proof("pm_anchor_userstories", "PROOF-1", "RULE-1",
                       tier="unit")
    def test_the_output_path_is_specs_anchors_and_never_a_dot_anchor_file(self):
        content = _read(PM_MD)

        stray = _offending_lines(content, '.anchor.md')
        assert stray == [], (
            "the retired `.anchor.md` artifact name is back at "
            + "; ".join(f"line {n}: {line.strip()}" for n, line in stray))

        assert 'specs/_anchors/<name>.md' in content, (
            "the skill never names the one path sync_status scans")
        assert 'cat > specs/_anchors/' in content, (
            "the write step must create the file under specs/_anchors/")
        assert 'git add specs/_anchors/' in content, (
            "the commit step must stage the file under specs/_anchors/")
        assert 'snake_case' in content, (
            "the skill must say the anchor name is a snake_case token, since "
            "it is both the file name and the `# Anchor:` name")

    @pytest.mark.proof("pm_anchor_userstories", "PROOF-2", "RULE-2",
                       tier="unit")
    def test_the_banned_terms_are_gone_and_the_required_ones_are_present(self):
        content = _read(PM_MD)

        for banned in ('toolkit', 'anchor file', '.anchor.md'):
            hits = _offending_lines(content, banned, lower=True)
            assert hits == [], (
                f"the retired term {banned!r} appears at "
                + "; ".join(f"line {n}: {line.strip()}" for n, line in hits))

        for required in ('anchor spec', 'the Purlin plugin'):
            assert required in content, (
                f"the skill never uses the canonical term {required!r}")

    @pytest.mark.proof("pm_anchor_userstories", "PROOF-3", "RULE-3",
                       tier="unit")
    def test_the_template_carries_the_anchor_formats_sections_and_fields(self):
        fmt_headings, fmt_fields = _template_shape(
            _read(ANCHOR_FORMAT), '### Template')
        skill_headings, skill_fields = _template_shape(
            _read(PM_MD), '## Anchor Spec Template')

        assert fmt_headings, "anchor_format.md's template block has no headings"
        assert fmt_fields, "anchor_format.md's template block has no `>` fields"

        assert skill_headings == fmt_headings, (
            f"the skill's template has headings {skill_headings} while "
            f"anchor_format.md has {fmt_headings}; the two copies have drifted")
        assert skill_fields == fmt_fields, (
            f"the skill's template has metadata fields {skill_fields} while "
            f"anchor_format.md has {fmt_fields}; the two copies have drifted")

    @pytest.mark.proof("pm_anchor_userstories", "PROOF-4", "RULE-4",
                       tier="unit")
    def test_the_commit_prefix_is_the_one_commit_conventions_defines(self):
        content = _read(PM_MD)

        assert 'anchor(<name>): create' in content, (
            "the skill must name the `anchor(<name>): create` prefix")
        assert 'git commit -m "anchor(<name>): create"' in content, (
            "the commit fence must carry the prefix, not merely the prose "
            "around it")

        chore = _offending_lines(content, 'chore:')
        assert len(chore) == 1 and 'Never' in chore[0][1], (
            "`chore:` may appear only in the sentence forbidding it, got "
            + "; ".join(f"line {n}: {line.strip()}" for n, line in chore))

        rows = [line for line in _read(COMMIT_CONVENTIONS).splitlines()
                if line.startswith('|') and 'anchor(<name>): create' in line]
        assert len(rows) == 1, (
            f"references/commit_conventions.md must carry exactly one table "
            f"row for `anchor(<name>): create`, got {len(rows)}")

    @pytest.mark.proof("pm_anchor_userstories", "PROOF-5", "RULE-5",
                       tier="unit")
    def test_the_pm_skill_zip_holds_one_skill_md_equal_to_its_sibling(self):
        _assert_skill_zip_matches_markdown('PM', 'purlin-anchor-userstories')
