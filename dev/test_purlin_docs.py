"""The four pages a reader meets first, read against the product.

`specs/instructions/purlin_docs.md` holds two rules. The README's command
table gives every command the purpose sentence `references/purlin_commands.md`
gives it, word for word. Every printed line the four pages quote is printed by
a run of the sample project the pages describe: each quote sits in a fenced
block marked `text`, the line before it names the run it was taken from as
`<!-- sample: <run> -->`, and this file builds that sample project in a
temporary folder, makes each run, and finds the block's lines in that run's
output, one after another as the page shows them.

The sample is the ten-minute path: a Python project whose `pyproject.toml`
configures pytest and holds no code, set up at the gate `passed` with the
commit agreed (`--yes`, as the init skill passes it), then one spec, `cart`,
with its code and marked tests written by hand as `purlin:spec` and
`purlin:build` would write them. A second project with no test tool Purlin
knows gives the line the first run prints for it.

Run as a program, `python3 dev/test_purlin_docs.py <folder>` builds the
sample in `<folder>` and prints every run's output, so a page's samples can be
taken from it.
"""

import json
import os
import re
import shlex
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PAGES = ('README.md', 'docs/index.md', 'docs/getting-started.md',
         'docs/how-purlin-works.md')
COMMANDS_REFERENCE = os.path.join(ROOT, 'references', 'purlin_commands.md')
SCAFFOLD = os.path.join(ROOT, 'scripts', 'init', 'scaffold.py')
RUN_SCRIPT = os.path.join(ROOT, 'scripts', 'run', 'purlin_run.py')

RUNS = ('setup', 'first-run', 'confirmed-run', 'commit-run', 'failing-run',
        'no-tool')


def read(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


# --- The command table ------------------------------------------------------

def table_rows(text, headings):
    """`(command, purpose)` for each row of the tables under the `## `
    headings named, in the order they stand."""
    rows, inside = [], False
    for line in text.splitlines():
        if line.startswith('## '):
            inside = line[3:].strip() in headings
            continue
        if not inside or not line.startswith('| `'):
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        rows.append((cells[0], cells[1]))
    return rows


def reference_purposes():
    return table_rows(read(COMMANDS_REFERENCE), ('Core', 'Supporting'))


def readme_purposes(text=None):
    if text is None:
        text = read(os.path.join(ROOT, 'README.md'))
    return table_rows(text, ('Commands',))


def purposes_that_differ(readme_rows, reference_rows):
    """Each README row whose command the reference does not list, or whose
    purpose is not the reference's, as `<command>: <purpose>`."""
    given = dict(reference_rows)
    return ['%s: %s' % (command, purpose) for command, purpose in readme_rows
            if given.get(command) != purpose]


def commands_missing(readme_rows, reference_rows):
    listed = {command for command, _ in readme_rows}
    return [command for command, _ in reference_rows if command not in listed]


class TestCommandTable:

    # purlin: purlin_docs PROOF-1
    def test_each_row_carries_the_references_purpose_sentence(self):
        readme, reference = readme_purposes(), reference_purposes()
        assert len(readme) >= 11, readme
        assert purposes_that_differ(readme, reference) == []
        # One word changed in a purpose sentence is found.
        command, purpose = readme[0]
        changed = [(command, purpose.replace(' ', '  ', 1))] + readme[1:]
        assert purposes_that_differ(changed, reference) == [
            '%s: %s' % changed[0]]

    # purlin: purlin_docs PROOF-2
    def test_every_command_of_the_reference_has_a_row(self):
        readme, reference = readme_purposes(), reference_purposes()
        assert len(reference) == 11, reference
        assert commands_missing(readme, reference) == []
        # A row taken out is named.
        assert commands_missing(readme[1:], reference) == [readme[0][0]]


# --- The quoted lines -------------------------------------------------------

SAMPLE = re.compile(r'^<!-- sample: ([a-z-]+) -->$')


def fenced_blocks(text):
    """`(line number, language, sample, lines)` for each fenced block, the
    sample being the run the comment on the line before names, or None."""
    blocks, lines, index = [], text.splitlines(), 0
    while index < len(lines):
        line = lines[index]
        if line.lstrip().startswith('```'):
            indent = len(line) - len(line.lstrip())
            language = line.strip()[3:].strip()
            before = lines[index - 1].strip() if index else ''
            found = SAMPLE.match(before)
            body, index = [], index + 1
            while index < len(lines) and not lines[index].strip() == '```':
                body.append(lines[index][indent:])
                index += 1
            blocks.append((index - len(body), language,
                           found.group(1) if found else None, body))
        index += 1
    return blocks


def quoted_blocks():
    """`(page, line number, sample, lines)` for each `text` block of the
    four pages."""
    found = []
    for page in PAGES:
        for number, language, sample, body in fenced_blocks(
                read(os.path.join(ROOT, page))):
            if language == 'text':
                found.append((page, number, sample, body))
    return found


def contains_in_order(printed, quoted):
    """True when the lines `quoted` stand in `printed` one after another."""
    size = len(quoted)
    return any(printed[start:start + size] == quoted
               for start in range(len(printed) - size + 1))


def as_this_page_spells_it(output):
    """The run's lines, with the Windows spelling of the suggested Python
    command read as the page spells it for every other system."""
    return output.replace('py -3 -m pytest', 'python3 -m pytest').splitlines()


def clean_environment():
    """This process's environment, less what would point a Purlin program
    at another project or plugin, with git told to sign nothing and Python
    told to leave no compiled files in the project."""
    env = dict(os.environ)
    for name in ('CLAUDE_PLUGIN_ROOT', 'PURLIN_PROJECT_ROOT'):
        env.pop(name, None)
    env.update({'GIT_CONFIG_COUNT': '1',
                'GIT_CONFIG_KEY_0': 'commit.gpgsign',
                'GIT_CONFIG_VALUE_0': 'false',
                'PYTHONDONTWRITEBYTECODE': '1'})
    return env


def run(root, command, stdin=''):
    done = subprocess.run(command, cwd=root, input=stdin, capture_output=True,
                          text=True, encoding='utf-8', env=clean_environment(),
                          timeout=600)
    return done.stdout


def git(root, *args):
    subprocess.run(['git', *args], cwd=root, capture_output=True, text=True,
                   check=True, env=clean_environment())


def write(root, rel, text):
    path = os.path.join(root, *rel.split('/'))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)


def new_repository(root):
    os.makedirs(root)
    git(root, '-c', 'init.defaultBranch=main', 'init', '-q', '.')
    git(root, 'config', 'user.name', 'Sam Dev')
    git(root, 'config', 'user.email', 'sam@example.com')


def commit(root, message):
    git(root, 'add', '-A')
    git(root, 'commit', '-q', '-m', message)


PYPROJECT = ('[project]\nname = "shop"\nversion = "1.0.0"\n\n'
             '[tool.pytest.ini_options]\npythonpath = ["src"]\n')

CART_SPEC = """# Feature: cart

> Description: The total of a shopping cart.
> Scope: src/cart.py
> Highest-Rule: 3

## Rules

- RULE-1: An empty cart totals 0
- RULE-2: The total is the sum of each line's price times its quantity
- RULE-3: A line with a negative quantity is refused

## Proof

- PROOF-1 (RULE-1): A cart with no lines totals `0`
- PROOF-2 (RULE-2): A cart holding 2 of an item priced 3 and 1 of an item priced 1 totals `7`
- PROOF-3 (RULE-3): A cart with a line whose quantity is `-1` is refused with `ValueError`, and no total is given
"""

CART_CODE = """def total(lines):
    if any(quantity < 0 for _, quantity in lines):
        raise ValueError("a quantity cannot be negative")
    return sum(price * quantity for price, quantity in lines)
"""

CART_TESTS = """import pytest

from cart import total


# purlin: cart PROOF-1
def test_empty():
    assert total([]) == 0


# purlin: cart PROOF-2
def test_sum():
    assert total([(3, 2), (1, 1)]) == 7


# purlin: cart PROOF-3
def test_negative():
    with pytest.raises(ValueError):
        total([(2, -1)])
"""


def purlin(*args):
    return [sys.executable, *args]


def test_run(root, *flags):
    return run(root, purlin(RUN_SCRIPT, '--project-root', root, '--test',
                            *flags))


test_run.__test__ = False  # a helper, not a test


def confirmed_setting(first_run):
    """The `tests` setting the first run suggested, as the person confirms
    it, with its Python the interpreter running these tests."""
    prefix = 'Suggested tests setting: '
    line = next(line for line in first_run.splitlines()
                if line.startswith(prefix))
    entries = json.loads(line[len(prefix):])
    for entry in entries:
        entry['run'] = re.sub(r'^(python3|py -3) ',
                              shlex.quote(sys.executable) + ' ', entry['run'])
    return entries


def build_sample(base):
    """Every run of the sample project, by name, as it printed it."""
    printed = {}
    root = os.path.join(base, 'my-project')
    new_repository(root)
    write(root, 'pyproject.toml', PYPROJECT)
    commit(root, 'the project')
    printed['setup'] = run(root, purlin(SCAFFOLD, '--project-root', root,
                                        '--gate', 'passed', '--yes'))
    # What `purlin:spec cart` and `purlin:build cart` write and commit.
    write(root, 'specs/shop/cart.md', CART_SPEC)
    commit(root, "spec(cart): rules for the cart's total")
    write(root, 'src/cart.py', CART_CODE)
    write(root, 'tests/test_cart.py', CART_TESTS)
    commit(root, 'feat(cart): implement RULE-1, RULE-2, RULE-3')
    printed['first-run'] = test_run(root, '--feature', 'cart')
    config_path = os.path.join(root, '.purlin', 'config.json')
    config = json.loads(read(config_path))
    config['tests'] = confirmed_setting(printed['first-run'])
    write(root, '.purlin/config.json', json.dumps(config, indent=2) + '\n')
    printed['confirmed-run'] = test_run(root, '--feature', 'cart')
    printed['commit-run'] = test_run(root, '--commit')
    write(root, 'src/cart.py', CART_CODE.replace('price * quantity',
                                                 'price - quantity'))
    printed['failing-run'] = test_run(root)
    # A project with no test tool Purlin knows.
    other = os.path.join(base, 'no-tool')
    new_repository(other)
    write(other, 'README.md', 'shop\n')
    commit(other, 'the project')
    run(other, purlin(SCAFFOLD, '--project-root', other, '--gate', 'passed',
                      '--yes'))
    write(other, 'specs/shop/cart.md', CART_SPEC)
    write(other, 'src/cart.py', CART_CODE)
    write(other, 'tests/test_cart.py', CART_TESTS)
    commit(other, 'the cart')
    printed['no-tool'] = test_run(other, '--feature', 'cart')
    return printed


@pytest.fixture(scope='module')
def sample(tmp_path_factory):
    return build_sample(os.path.realpath(str(
        tmp_path_factory.mktemp('purlin-docs'))))


def quotes_not_printed(sample, run_name):
    """Each block the pages take from `run_name` whose lines that run did
    not print one after another, as `<page>:<line>`; and the count of such
    blocks."""
    printed = as_this_page_spells_it(sample[run_name])
    blocks = [block for block in quoted_blocks() if block[2] == run_name]
    return (['%s:%d' % (page, number) for page, number, _, body in blocks
             if not contains_in_order(printed, body)], len(blocks))


class TestQuotedLines:

    # purlin: purlin_docs PROOF-3
    def test_setups_lines_are_printed_by_setup(self, sample):
        assert quotes_not_printed(sample, 'setup')[0] == [], sample['setup']
        assert quotes_not_printed(sample, 'setup')[1] >= 1

    # purlin: purlin_docs PROOF-4
    def test_the_first_runs_lines_are_printed_by_it(self, sample):
        assert quotes_not_printed(sample, 'first-run')[0] == [], \
            sample['first-run']
        assert quotes_not_printed(sample, 'first-run')[1] >= 1

    # purlin: purlin_docs PROOF-5
    def test_the_confirmed_runs_lines_are_printed_by_it(self, sample):
        assert quotes_not_printed(sample, 'confirmed-run')[0] == [], \
            sample['confirmed-run']
        assert quotes_not_printed(sample, 'confirmed-run')[1] >= 1

    # purlin: purlin_docs PROOF-6
    def test_the_commit_runs_lines_are_printed_by_it(self, sample):
        assert quotes_not_printed(sample, 'commit-run')[0] == [], \
            sample['commit-run']
        assert quotes_not_printed(sample, 'commit-run')[1] >= 1

    # purlin: purlin_docs PROOF-7
    def test_the_failing_runs_lines_are_printed_by_it(self, sample):
        assert quotes_not_printed(sample, 'failing-run')[0] == [], \
            sample['failing-run']
        assert quotes_not_printed(sample, 'failing-run')[1] >= 1

    # purlin: purlin_docs PROOF-8
    def test_the_no_tool_line_is_printed_by_that_run(self, sample):
        assert quotes_not_printed(sample, 'no-tool')[0] == [], \
            sample['no-tool']
        assert quotes_not_printed(sample, 'no-tool')[1] >= 1

    # purlin: purlin_docs PROOF-9
    def test_every_quote_names_a_run_and_every_block_a_language(self):
        unnamed = []
        for page in PAGES:
            for number, language, sample, _ in fenced_blocks(
                    read(os.path.join(ROOT, page))):
                if not language:
                    unnamed.append('%s:%d: no language' % (page, number))
                elif language == 'text' and sample not in RUNS:
                    unnamed.append('%s:%d: %s' % (page, number, sample))
        assert unnamed == []
        assert len(quoted_blocks()) >= len(RUNS)
        # A block with no run named, and one with no language, are found.
        text = '```text\nNothing left to do.\n```\n\n```\nls\n```\n'
        found = fenced_blocks(text)
        assert [(language, sample) for _, language, sample, _ in found] == [
            ('text', None), ('', None)]


# --- The links --------------------------------------------------------------

LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')


def anchor_of(heading):
    """A heading's anchor as the git host spells it: lower case, every
    character but a letter, a digit, a space, `-` and `_` dropped, and each
    space a `-`."""
    kept = re.sub(r'[^\w\- ]', '', heading.strip().lower())
    return kept.replace(' ', '-')


def anchors_in(text):
    """Every anchor a Markdown file's headings give, a repeat numbered as the
    git host numbers it, `-1`, `-2`. Headings inside a fenced block are not
    headings."""
    seen, found, fenced = {}, set(), False
    for line in text.splitlines():
        if line.startswith('```'):
            fenced = not fenced
            continue
        match = re.match(r'#{1,6} (.+)$', line)
        if fenced or not match:
            continue
        slug = anchor_of(match.group(1))
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        found.add(slug if count == 0 else '%s-%d' % (slug, count))
    return found


def broken_links(page, text):
    """`<page>: <target>` for each relative link of `text` that names no file
    in the repository, or whose `#` part is no heading of that file."""
    broken = []
    folder = os.path.dirname(os.path.join(ROOT, page))
    for target in LINK.findall(text):
        if re.match(r'[a-z]+:', target):
            continue
        path, _, part = target.partition('#')
        full = (os.path.normpath(os.path.join(folder, *path.split('/')))
                if path else os.path.join(ROOT, page))
        if not os.path.isfile(full):
            broken.append('%s: %s' % (page, target))
        elif part and part not in anchors_in(read(full)):
            broken.append('%s: %s' % (page, target))
    return broken


class TestLinks:

    # purlin: purlin_docs PROOF-17
    def test_every_relative_link_names_a_file_and_a_heading(self):
        followed = [target for page in PAGES
                    for target in LINK.findall(read(os.path.join(ROOT, page)))
                    if not re.match(r'[a-z]+:', target)]
        assert len(followed) >= 10, followed
        assert [line for page in PAGES
                for line in broken_links(page, read(os.path.join(ROOT, page)))
                ] == []
        # A link to a file the repository does not hold, and one to a heading
        # its file does not have, are found.
        text = ('[a](how-purlin-works.md#no-such-heading) '
                '[b](no-such-page.md)')
        assert broken_links('docs/index.md', text) == [
            'docs/index.md: how-purlin-works.md#no-such-heading',
            'docs/index.md: no-such-page.md']


if __name__ == '__main__':
    for name, output in build_sample(os.path.realpath(sys.argv[1])).items():
        print('==== %s' % name)
        print(output)
