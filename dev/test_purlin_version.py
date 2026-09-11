"""Tests for purlin_version — 8 rules.

Ensures the Purlin version string is defined in exactly one place (the VERSION
file) and all references to it read from that file or match its value.
"""

import json
import os
import re
import shutil
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
VERSION_FILE = os.path.join(PROJECT_ROOT, 'VERSION')
CONFIG_TEMPLATE = os.path.join(PROJECT_ROOT, 'templates', 'config.json')
PLUGIN_MANIFEST = os.path.join(PROJECT_ROOT, '.claude-plugin', 'plugin.json')
SERVER_PY = os.path.join(PROJECT_ROOT, 'scripts', 'mcp', 'purlin_server.py')
PROJECT_CONFIG = os.path.join(PROJECT_ROOT, '.purlin', 'config.json')
BUMP_SCRIPT = os.path.join(PROJECT_ROOT, 'dev', 'bump_version.sh')

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))
import purlin_server


class TestVersionFileSemver:

    @pytest.mark.proof("purlin_version", "PROOF-1", "RULE-1")
    def test_version_file_exists_and_is_valid_semver(self):
        """VERSION file must exist and contain a valid semver string (X.Y.Z)."""
        assert os.path.isfile(VERSION_FILE), \
            f"VERSION file not found at {VERSION_FILE}"
        with open(VERSION_FILE) as f:
            content = f.read().strip()
        assert content, "VERSION file is empty"
        semver_pattern = re.compile(r'^\d+\.\d+\.\d+$')
        assert semver_pattern.match(content), \
            f"VERSION file contains '{content}', expected a semver string like '1.2.3'"


class TestServerReadsVersionFromFile:

    @pytest.mark.proof("purlin_version", "PROOF-2", "RULE-2")
    def test_purlin_server_uses_read_version_function(self):
        """purlin_server.py must define _read_version() and assign its result to
        PURLIN_VERSION; SERVER_INFO must use PURLIN_VERSION for the version field."""
        # Verify _read_version is defined and callable
        assert hasattr(purlin_server, '_read_version'), \
            "_read_version() not found in purlin_server"
        assert callable(purlin_server._read_version), \
            "_read_version is not callable"

        # Verify PURLIN_VERSION is set from the function (check the module source)
        with open(SERVER_PY) as f:
            source = f.read()
        assert 'PURLIN_VERSION = _read_version()' in source, \
            "PURLIN_VERSION must be assigned via _read_version(), not a literal"

        # Verify SERVER_INFO uses PURLIN_VERSION
        assert 'SERVER_INFO' in source, "SERVER_INFO not found in purlin_server.py"
        server_info_match = re.search(
            r'SERVER_INFO\s*=\s*\{[^}]*"version"\s*:\s*PURLIN_VERSION',
            source,
            re.DOTALL,
        )
        assert server_info_match, \
            'SERVER_INFO must use PURLIN_VERSION for the "version" field, not a literal'

        # Verify the runtime value matches the VERSION file
        with open(VERSION_FILE) as f:
            expected = f.read().strip()
        assert purlin_server.PURLIN_VERSION == expected, \
            (f"PURLIN_VERSION is '{purlin_server.PURLIN_VERSION}' at runtime "
             f"but VERSION file contains '{expected}'")


class TestTemplateVersionMatchesVersionFile:

    @pytest.mark.proof("purlin_version", "PROOF-3", "RULE-3")
    def test_template_config_version_matches_version_file(self):
        """templates/config.json version field must match VERSION file content."""
        with open(VERSION_FILE) as f:
            file_version = f.read().strip()

        assert os.path.isfile(CONFIG_TEMPLATE), \
            f"templates/config.json not found at {CONFIG_TEMPLATE}"
        with open(CONFIG_TEMPLATE) as f:
            config = json.load(f)

        assert 'version' in config, \
            "templates/config.json has no 'version' field"
        assert config['version'] == file_version, \
            (f"templates/config.json version is '{config['version']}' "
             f"but VERSION file contains '{file_version}'")


class TestPluginManifestVersionMatchesVersionFile:

    @pytest.mark.proof("purlin_version", "PROOF-5", "RULE-5")
    def test_plugin_manifest_version_matches_version_file(self):
        """.claude-plugin/plugin.json version field must match VERSION file content.

        The plugin manifest is the version consumers install against via the Claude
        plugin marketplace. It is a separate version source from VERSION and
        templates/config.json, so it must be kept in lockstep with the release.
        """
        with open(VERSION_FILE) as f:
            file_version = f.read().strip()

        assert os.path.isfile(PLUGIN_MANIFEST), \
            f".claude-plugin/plugin.json not found at {PLUGIN_MANIFEST}"
        with open(PLUGIN_MANIFEST) as f:
            manifest = json.load(f)

        assert 'version' in manifest, \
            ".claude-plugin/plugin.json has no 'version' field"
        assert manifest['version'] == file_version, \
            (f".claude-plugin/plugin.json version is '{manifest['version']}' "
             f"but VERSION file contains '{file_version}'")


class TestNoHardcodedVersionInServer:

    @pytest.mark.proof("purlin_version", "PROOF-4", "RULE-4")
    def test_no_hardcoded_version_strings_in_purlin_server(self):
        """purlin_server.py must not contain hardcoded version literals like
        '0.9.0' or any X.Y.Z pattern outside of comments."""
        with open(SERVER_PY) as f:
            raw = f.read()

        # Strip full-line comments before searching
        non_comment_lines = [
            line for line in raw.splitlines()
            if not line.lstrip().startswith('#')
        ]
        non_comment_source = '\n'.join(non_comment_lines)

        # Match quoted semver literals. Exclude '0.0.0' — that is the documented
        # sentinel returned by _read_version() when the VERSION file cannot be read,
        # not a hardcoded release version. The spec targets patterns like '0.9.0'
        # or '0.10.0' (real release versions that should live only in VERSION file).
        semver_pattern = re.compile(r'["\'](\d+\.\d+\.\d+)["\']')
        all_matches = semver_pattern.findall(non_comment_source)
        release_matches = [v for v in all_matches if v != '0.0.0']

        assert release_matches == [], (
            f"Found hardcoded release version string(s) in purlin_server.py "
            f"(outside comments): {release_matches}. "
            f"Version must be read from the VERSION file via _read_version()."
        )


class TestProjectConfigVersionMatchesVersionFile:

    @pytest.mark.proof("purlin_version", "PROOF-6", "RULE-6")
    def test_project_config_version_matches_version_file(self):
        """This repo's own .purlin/config.json version must match VERSION.

        Purlin develops itself, so the repo is also a Purlin project. Its
        config.json carries the framework version that initialized it, and the
        dashboard reports that field. It drifted to 0.9.2 while VERSION,
        templates/config.json and plugin.json all read 0.10.0, and the three
        existing rules could not see it.
        """
        with open(VERSION_FILE, encoding='utf-8') as f:
            file_version = f.read().strip()

        assert os.path.isfile(PROJECT_CONFIG), \
            f".purlin/config.json not found at {PROJECT_CONFIG}"
        with open(PROJECT_CONFIG, encoding='utf-8') as f:
            config = json.load(f)

        assert 'version' in config, \
            ".purlin/config.json has no 'version' field"
        assert config['version'] == file_version, \
            (f".purlin/config.json version is '{config['version']}' "
             f"but VERSION file contains '{file_version}'. "
             f"Fix with: bash dev/bump_version.sh {file_version}")


class TestBumpVersionScriptPropagatesAndDetectsDrift:

    DERIVED = [
        os.path.join('templates', 'config.json'),
        os.path.join('.claude-plugin', 'plugin.json'),
        os.path.join('.purlin', 'config.json'),
    ]

    def _fake_project(self, root, version):
        """Build a minimal tree with VERSION and all three derived files."""
        with open(os.path.join(root, 'VERSION'), 'w', encoding='utf-8') as f:
            f.write(version + '\n')
        for rel in self.DERIVED:
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({'version': version, 'spec_dir': 'specs'}, f, indent=2)
                f.write('\n')
        # The script resolves the root as its own parent, so it must be invoked
        # from a dev/ directory inside the tree under test.
        dev_dir = os.path.join(root, 'dev')
        os.makedirs(dev_dir, exist_ok=True)
        shutil.copy2(BUMP_SCRIPT, os.path.join(dev_dir, 'bump_version.sh'))
        return os.path.join(dev_dir, 'bump_version.sh')

    def _read(self, root, rel):
        with open(os.path.join(root, rel), encoding='utf-8') as f:
            return json.load(f)['version']

    @pytest.mark.proof("purlin_version", "PROOF-7", "RULE-7")
    def test_bump_propagates_everywhere_and_check_reports_drift(self, tmp_path):
        """bump_version.sh <semver> writes VERSION and every derived location;
        --check exits 1 naming the drifted file, and 0 on a matching tree."""
        root = str(tmp_path / 'proj')
        os.makedirs(root)
        script = self._fake_project(root, '1.2.3')

        # ── Propagation ────────────────────────────────────────────────
        bump = subprocess.run(
            ['bash', script, '9.8.7'],
            capture_output=True, text=True,
        )
        assert bump.returncode == 0, \
            f"bump exited {bump.returncode}\nstdout:{bump.stdout}\nstderr:{bump.stderr}"

        with open(os.path.join(root, 'VERSION'), encoding='utf-8') as f:
            assert f.read().strip() == '9.8.7', "VERSION file was not rewritten"
        for rel in self.DERIVED:
            assert self._read(root, rel) == '9.8.7', \
                f"{rel} still reports {self._read(root, rel)}, expected 9.8.7"

        # ── --check passes on the propagated tree ─────────────────────
        ok = subprocess.run(
            ['bash', script, '--check'], capture_output=True, text=True,
        )
        assert ok.returncode == 0, \
            f"--check failed on a matching tree:\n{ok.stdout}\n{ok.stderr}"

        # ── --check fails, naming the drifted file ────────────────────
        drifted = os.path.join(root, '.purlin', 'config.json')
        with open(drifted, encoding='utf-8') as f:
            data = json.load(f)
        data['version'] = '1.2.3'
        with open(drifted, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            f.write('\n')

        bad = subprocess.run(
            ['bash', script, '--check'], capture_output=True, text=True,
        )
        assert bad.returncode == 1, \
            f"--check exited {bad.returncode} on a drifted tree, expected 1"
        assert '.purlin/config.json' in bad.stdout, \
            f"--check did not name the drifted file:\n{bad.stdout}"
        assert 'DRIFT' in bad.stdout, \
            f"--check did not mark the drift:\n{bad.stdout}"
        # The other two must still be reported as matching, so the operator can
        # see the check is scoped rather than blanket-failing.
        assert 'templates/config.json' in bad.stdout
        assert '.claude-plugin/plugin.json' in bad.stdout

    @pytest.mark.proof("purlin_version", "PROOF-7", "RULE-7")
    def test_bump_rejects_non_semver_and_tolerates_absent_optional_file(self, tmp_path):
        """A non-semver argument is refused before anything is written, and an
        absent .purlin/config.json is skipped rather than failing the run."""
        root = str(tmp_path / 'proj')
        os.makedirs(root)
        script = self._fake_project(root, '1.2.3')

        bad = subprocess.run(
            ['bash', script, 'not-a-version'], capture_output=True, text=True,
        )
        assert bad.returncode == 2, f"expected exit 2, got {bad.returncode}"
        with open(os.path.join(root, 'VERSION'), encoding='utf-8') as f:
            assert f.read().strip() == '1.2.3', \
                "VERSION was modified despite an invalid argument"

        # A consumer checkout of the framework has no .purlin/config.json.
        os.remove(os.path.join(root, '.purlin', 'config.json'))
        run = subprocess.run(
            ['bash', script, '2.0.0'], capture_output=True, text=True,
        )
        assert run.returncode == 0, \
            f"bump failed with the optional file absent:\n{run.stdout}\n{run.stderr}"
        assert self._read(root, os.path.join('templates', 'config.json')) == '2.0.0'

        check = subprocess.run(
            ['bash', script, '--check'], capture_output=True, text=True,
        )
        assert check.returncode == 0, \
            f"--check failed with the optional file absent:\n{check.stdout}"
        assert 'absent' in check.stdout, \
            f"--check did not report the absent optional file:\n{check.stdout}"


class TestDocsCiteVersionFileInsteadOfALiteral:

    DOC_LINES = [
        (os.path.join('skills', 'init', 'SKILL.md'), '| `version` |'),
        (os.path.join('references', 'drift_criteria.md'), '| `version` |'),
    ]

    @pytest.mark.proof("purlin_version", "PROOF-8", "RULE-8")
    def test_config_version_field_docs_carry_no_semver_literal(self):
        """The config-field tables must name the VERSION file, not a number.

        Both tables sat at `"0.9.0"`, two releases stale, because a literal in
        prose has nothing keeping it honest.
        """
        semver_literal = re.compile(r'`?"?\d+\.\d+\.\d+"?`?')
        for rel, marker in self.DOC_LINES:
            path = os.path.join(PROJECT_ROOT, rel)
            assert os.path.isfile(path), f"{rel} not found"
            with open(path, encoding='utf-8') as f:
                lines = [ln for ln in f.read().splitlines()
                         if ln.strip().startswith(marker)]
            assert lines, f"no `version` field row found in {rel}"
            for ln in lines:
                assert not semver_literal.search(ln), \
                    (f"{rel} restates a version literal in its `version` row: "
                     f"{ln.strip()!r}: cite the VERSION file instead")
                assert 'VERSION' in ln, \
                    (f"{rel} `version` row does not reference the VERSION file: "
                     f"{ln.strip()!r}")
