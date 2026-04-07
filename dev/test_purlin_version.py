"""Tests for purlin_version — 4 rules.

Ensures the Purlin version string is defined in exactly one place (the VERSION
file) and all references to it read from that file or match its value.
"""

import inspect
import json
import os
import re
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
VERSION_FILE = os.path.join(PROJECT_ROOT, 'VERSION')
CONFIG_TEMPLATE = os.path.join(PROJECT_ROOT, 'templates', 'config.json')
SERVER_PY = os.path.join(PROJECT_ROOT, 'scripts', 'mcp', 'purlin_server.py')

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
