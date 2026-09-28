"""Keep every test off the model."""
import os
import sys
import tempfile

import pytest  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fake_claude  # noqa: E402


@pytest.fixture(scope='session', autouse=True)
def no_real_model():
    """A fake `claude` stands first on PATH for the whole session.

    `purlin:audit` calls the model through the `claude` command. No test may
    reach the real one, so every test, and every process a test starts,
    finds this fake first. It answers `settled: yes`; a test that wants
    another answer installs its own fake and puts it in front of this one.
    """
    directory = fake_claude.install(tempfile.mkdtemp(prefix='purlin-claude-'))
    previous = os.environ.get('PATH', '')
    os.environ['PATH'] = directory + os.pathsep + previous
    yield directory
    os.environ['PATH'] = previous
