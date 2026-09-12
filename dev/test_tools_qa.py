"""Tests for qa_report — the packaged skills under tools/.

`tools/QA/purlin-qa-report.md` is a skill a QA reader runs against someone
else's repository. Two things go wrong there that nothing else in this project
catches: an instruction that leaks a credential, and a report that claims more
than the digest recorded. These proofs read the shipped markdown, and RULE-6
reads the zip beside it, because the zip is what a user installs.
"""

import os
import re
import zipfile

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
TOOLS = os.path.join(PROJECT_ROOT, 'tools')
QA_MD = os.path.join(TOOLS, 'QA', 'purlin-qa-report.md')

# The two markdown/archive pairs under tools/. RULE-6 covers both.
PAIRS = [
    ('QA', 'purlin-qa-report'),
    ('PM', 'purlin-anchor-userstories'),
]


def _read(path):
    with open(path) as f:
        return f.read()


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
    def test_each_skill_zip_holds_one_skill_md_equal_to_its_sibling(self):
        checked = 0
        for folder, name in PAIRS:
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
            checked += 1

        assert checked == len(PAIRS) and checked > 0, (
            f"only {checked} archives checked")
