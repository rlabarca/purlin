"""The opener `purlin:status --open` runs: it hands the dashboard page to the
default browser, or prints its path where no browser can be reached.

Each test hands the opener a browser of its own, which records the address
it is given and says whether it opened it, so no real browser starts.

    python3 -m pytest dev/test_open_page.py -q
"""

import os
import subprocess
import sys

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'report'))

import open_page  # noqa: E402

PAGE = 'purlin-report.html'


class Browser:
    """A browser that records each address and answers `opens`."""

    def __init__(self, opens):
        self.opens = opens
        self.given = []

    def __call__(self, address):
        self.given.append(address)
        return self.opens


def _project(folder):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, PAGE), 'w', encoding='utf-8') as handle:
        handle.write('<!DOCTYPE html><title>board</title>\n')
    return folder


def _run(folder, browser):
    printed = []
    code = open_page.open_page(folder, out=printed.append, browser=browser)
    return code, printed


# purlin: open_page PROOF-1
def test_a_browser_that_opens_the_page_is_named(tmp_path, monkeypatch):
    monkeypatch.delenv('CI', raising=False)
    folder = _project(str(tmp_path / 'project'))
    browser = Browser(opens=True)
    code, printed = _run(folder, browser)
    path = os.path.abspath(os.path.join(folder, PAGE))
    assert browser.given == [open_page.address(path)]
    assert printed == ['Opened %s in the default browser.' % path]
    assert code == 0


# purlin: open_page PROOF-2
def test_a_browser_that_opens_nothing_leaves_the_path(tmp_path, monkeypatch):
    monkeypatch.delenv('CI', raising=False)
    folder = _project(str(tmp_path / 'project'))
    browser = Browser(opens=False)
    code, printed = _run(folder, browser)
    path = os.path.abspath(os.path.join(folder, PAGE))
    assert len(browser.given) == 1
    assert printed == ['Dashboard: %s. Open it in a browser.' % path]
    assert code == 0


# purlin: open_page PROOF-3
def test_on_ci_no_browser_is_started(tmp_path, monkeypatch):
    monkeypatch.setenv('CI', 'true')
    folder = _project(str(tmp_path / 'project'))
    browser = Browser(opens=True)
    code, printed = _run(folder, browser)
    path = os.path.abspath(os.path.join(folder, PAGE))
    assert browser.given == []
    assert printed == ['Dashboard: %s. Open it in a browser.' % path]
    assert code == 0


# purlin: open_page PROOF-4
def test_a_project_with_no_page_names_the_command(tmp_path, monkeypatch):
    monkeypatch.delenv('CI', raising=False)
    folder = str(tmp_path / 'project')
    os.makedirs(folder)
    browser = Browser(opens=True)
    code, printed = _run(folder, browser)
    said = ('purlin-report.html: no page yet. Run purlin:status, then '
            'purlin:status --open.')
    assert printed == [said]
    assert browser.given == []
    assert code == 1
    # The script as `purlin:status --open` starts it: the same line, and
    # the exit code 1 reaches the shell.
    done = subprocess.run(
        [sys.executable, os.path.join(ROOT, 'scripts', 'report',
                                      'open_page.py'),
         '--project-root', folder],
        capture_output=True, text=True, encoding='utf-8', timeout=60)
    assert done.stdout.splitlines() == [said], done.stdout + done.stderr
    assert done.returncode == 1, done.returncode


# purlin: open_page PROOF-5
def test_a_folder_with_a_space_and_an_accent_is_percent_encoded(tmp_path,
                                                                monkeypatch):
    monkeypatch.delenv('CI', raising=False)
    folder = _project(str(tmp_path / u'my café'))
    browser = Browser(opens=True)
    code, _printed = _run(folder, browser)
    assert code == 0
    [address] = browser.given
    assert address.startswith('file:'), address
    assert 'my%20caf%C3%A9/purlin-report.html' in address, address
    assert ' ' not in address, address
