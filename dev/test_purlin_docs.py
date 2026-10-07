"""The pages under `docs/`, read as a person on the git host reads them.

`specs/instructions/purlin_docs.md` holds nine rules: every relative link
on the pages resolves, the audit page says what to do with a finding and
links to its research, the research page cites its papers by links it lists
again under `Sources`, the page on working together holds one paragraph
on working in more than one checkout, the example that fetches Purlin
clones it at this version's signed tag, the index lists every page, the two
pages on AI proofs are linked from each other and from each page that folds
an AI proof in, each of the two holds one flow diagram, and the audit's
pages count the spot tests as the reference does.
"""

import glob
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DOCS = os.path.join(ROOT, 'docs')


def read(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


def pages():
    """Every Markdown page under `docs/`, as its path from the repository's
    root, in name order."""
    return sorted('docs/' + os.path.basename(path)
                  for path in glob.glob(os.path.join(DOCS, '*.md')))


# --- The links --------------------------------------------------------------

LINK = re.compile(r'\[([^\]]*)\]\(([^)\s]+)\)')


def targets(text):
    """Every link target of a Markdown text, in the order they stand."""
    return [target for _, target in LINK.findall(text)]


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
        if line.lstrip().startswith('```'):
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
    for target in targets(text):
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


# purlin: purlin_docs PROOF-17
def test_every_relative_link_on_the_docs_pages_names_a_file_and_a_heading():
    found = pages()
    assert 'docs/index.md' in found and len(found) >= 9, found
    followed = [target for page in found
                for target in targets(read(os.path.join(ROOT, page)))
                if not re.match(r'[a-z]+:', target)]
    assert len(followed) >= 40, followed
    assert [line for page in found
            for line in broken_links(page, read(os.path.join(ROOT, page)))
            ] == []
    # A file the repository holds is named letter for letter: each folder
    # and the file of a link are an entry of their folder's own listing, so
    # `Audit.md` does not name `audit.md` where the disk ignores case.
    miscased = []
    for page in found:
        for target in targets(read(os.path.join(ROOT, page))):
            path = target.partition('#')[0]
            if re.match(r'[a-z]+:', target) or not path:
                continue
            at = os.path.dirname(os.path.join(ROOT, page))
            for name in path.rstrip('/').split('/'):
                if name == '..':
                    at = os.path.dirname(at)
                elif name != '.':
                    if name not in os.listdir(at):
                        miscased.append('%s: %s' % (page, target))
                        break
                    at = os.path.join(at, name)
    assert miscased == []
    # Each link is followed from the page's own folder: one to a file the
    # repository does not hold, and one to a heading its file does not have,
    # are found, and one that climbs out of `docs/` to a real file is not.
    text = ('[a](how-purlin-works.md#no-such-heading) [b](no-such-page.md) '
            '[c](../README.md#install) '
            '[d](how-purlin-works.md#purlin-keeps-two-facts)')
    assert broken_links('docs/index.md', text) == [
        'docs/index.md: how-purlin-works.md#no-such-heading',
        'docs/index.md: no-such-page.md']


# --- The audit page and its research ----------------------------------------

AUDIT_PAGE = os.path.join(DOCS, 'audit.md')
RESEARCH_PAGE = os.path.join(DOCS, 'audit-research.md')
PAPERS = ('Inozemtseva and Holmes, ICSE 2014', 'Just et al., FSE 2014',
          'Petrović et al., TSE 2021', 'Foster et al., FSE 2025',
          'LLMorpheus')


def around_sources(text):
    """The research page's text before its heading `Sources`, and the list
    under it."""
    before, heading, after = text.partition('\n## Sources\n')
    assert heading, 'docs/audit-research.md has no heading Sources'
    return before, after


def papers_not_cited(text):
    """Each paper of `PAPERS` that no link of `text` names in its words with
    a target starting `https://`."""
    cited = [words for words, target in LINK.findall(text)
             if target.startswith('https://')]
    return [paper for paper in PAPERS
            if not any(paper in words for words in cited)]


# purlin: purlin_docs PROOF-21
def test_the_research_page_cites_the_five_papers_each_as_an_https_link():
    before, _ = around_sources(read(RESEARCH_PAGE))
    assert papers_not_cited(before) == []
    # A paper named in plain words, or by a link that is not https, is not
    # cited.
    plain = ('Inozemtseva and Holmes, ICSE 2014 found it. '
             '[Just et al., FSE 2014](http://example.com/just.pdf) '
             '[Petrović et al., TSE 2021](https://arxiv.org/pdf/2102.11378)')
    assert papers_not_cited(plain) == [
        'Inozemtseva and Holmes, ICSE 2014', 'Just et al., FSE 2014',
        'Foster et al., FSE 2025', 'LLMorpheus']


def links_not_listed(text):
    """Each link target the page gives before `Sources` that the list under
    `Sources` does not give again."""
    before, after = around_sources(text)
    listed = set(targets(after))
    return [target for target in targets(before) if target not in listed]


# purlin: purlin_docs PROOF-22
def test_every_link_of_the_research_page_appears_again_under_sources():
    text = read(RESEARCH_PAGE)
    before, after = around_sources(text)
    assert len(targets(before)) >= 10, targets(before)
    assert links_not_listed(text) == []
    # A link is a link however it is written: in brackets, between `<` and
    # `>`, or as the bare address. Each address before `Sources` is one the
    # list gives.
    written = [address.rstrip('.,;:') for address
               in re.findall(r'https?://[^\s)>\]]+', before)]
    assert len(written) >= 10, written
    assert [address for address in written
            if address not in targets(after)] == []
    # The audit page links to the research page and names 3 or 4 of its
    # sources, each by an https link the list under `Sources` holds.
    given = targets(read(AUDIT_PAGE))
    assert 'audit-research.md' in given, given
    named = [target for target in given if target.startswith('https://')]
    assert 3 <= len(set(named)) <= 4 and len(named) == len(set(named)), named
    assert [target for target in named if target not in targets(after)] == []
    # A link the text gives and the list leaves out is found.
    sample = ('[a](https://example.com/a.pdf) [b](https://example.com/b.pdf)'
              '\n\n## Sources\n\n- [a](https://example.com/a.pdf)\n')
    assert links_not_listed(sample) == ['https://example.com/b.pdf']


# --- What to do with a finding ----------------------------------------------

def headings(text):
    """The text of each `##` heading of a Markdown page, in order."""
    return re.findall(r'^## (.+)$', text, re.M)


def under(text, heading):
    """The part of the page under the `##` heading `heading`, up to the next
    `##` heading or a rule line."""
    _, found, rest = text.partition('\n## %s\n' % heading)
    assert found, 'docs/audit.md has no heading %s' % heading
    return re.split(r'^(?:## |---$)', rest, maxsplit=1, flags=re.M)[0]


def bullets(part):
    """Each top-level bullet of the part, as one line."""
    return [' '.join(block.split())
            for block in re.split(r'^(?=- )', part, flags=re.M)
            if block.startswith('- ')]


# purlin: purlin_docs PROOF-25
def test_the_audit_page_says_what_to_do_with_a_finding_after_how_it_works():
    text = read(AUDIT_PAGE)
    found = headings(text)
    assert found[found.index('How it works') + 1] == 'What to do with a finding'
    # No heading of any kind stands between the two: not one of another
    # level, not one written as a line underlined with `=` or `-`, and not
    # one in HTML. Lines inside a fenced block are not headings.
    between = text.partition('\n## How it works\n')[2].partition(
        '\n## What to do with a finding\n')[0].splitlines()
    other, fenced = [], False
    for number, line in enumerate(between):
        if line.lstrip().startswith('```'):
            fenced = not fenced
        elif fenced:
            continue
        elif re.match(r' {0,3}#{1,6}(?: |$)', line) or re.search(
                r'<h[1-6]\b', line, re.I):
            other.append(line)
        elif (re.fullmatch(r' {0,3}(?:=+|-+)\s*', line) and number
              and between[number - 1].strip()):
            other.append(between[number - 1])
    assert other == []
    part = under(text, 'What to do with a finding')
    assert len(bullets(part)) == 6, bullets(part)
    # Exactly 6 whatever their marker: `-`, `*`, `+` or a number.
    marked = [line for line in part.splitlines()
              if re.match(r'\s*(?:[-*+]|\d+[.)])\s', line)]
    assert len(marked) == 6, marked
    assert [name for name in ('`purlin:build`', '`strong`', '`spot-checked`')
            if name not in part] == []


# --- Working in more than one checkout --------------------------------------

def paragraphs(text):
    """The page's paragraphs: each run of lines between blank lines, as one
    line."""
    return [' '.join(block.split()) for block in re.split(r'\n\s*\n', text)
            if block.strip()]


# purlin: purlin_docs PROOF-24
def test_one_paragraph_of_working_together_names_a_worktree():
    text = read(os.path.join(DOCS, 'working-together.md'))
    naming = [paragraph for paragraph in paragraphs(text)
              if 'worktree' in paragraph.lower()]
    assert len(naming) == 1, naming
    paragraph = naming[0]
    assert paragraph.count('Each checkout') == 1, paragraph
    assert 'its own results' in paragraph
    assert 'its own dashboard' in paragraph
    # It says each checkout has them, in one sentence: the words between
    # `Each checkout` and `has its own results` hold no word that turns the
    # sentence round, and `its own dashboard` ends the same sentence.
    said = re.findall(r'\bEach checkout\b([^.]*?) has its own results\b'
                      r'[^.]*\bits own dashboard\.', paragraph)
    assert len(said) == 1, paragraph
    assert not re.search(
        r"\b(?:not|never|no|none|nor|seldom|rarely|hardly|only|n't)\b|n't",
        said[0], re.I), said
    # One sentence opens `Each checkout`, and it is the one that says both.
    # After `has`, up to `its own dashboard`, it is a list of things the
    # checkout has, each written `its own <word>`, joined by a comma or
    # `and`, and nothing else: no word before `its own results` or before
    # `its own dashboard` denies either, whatever the word is.
    opening = [sentence for sentence
               in re.split(r'(?<=[.!?])\s+(?=[A-Z])', paragraph)
               if sentence.startswith('Each checkout')]
    assert len(opening) == 1, paragraph
    sentence = opening[0]
    assert sentence.count(' has ') == 1, sentence
    before, after = sentence.split(' has ')
    assert before == 'Each checkout' + said[0], (before, said)
    # The words before `has` are these and no others, so none denies it.
    assert before == 'Each checkout of a repository, a worktree included,'
    assert after.endswith('its own dashboard.'), sentence
    assert re.fullmatch(r'its own \w+(?:, its own \w+)* and its own \w+\.',
                        after), sentence
    owned = re.findall(r'its own (\w+)', after)
    assert owned[0] == 'results' and owned[-1] == 'dashboard', owned
    assert len(owned) == len(re.split(r', | and ', after)), sentence
    assert not re.search(
        r"\b(?:not|never|no|none|nor|neither|without|seldom|rarely|hardly|"
        r"barely|scarcely|only|lacks?|cannot)\b|n't", sentence, re.I), (
            sentence)
    assert re.search(r'\bmerged?\b', paragraph)
    assert re.search(r'(?<![\w:-])`purlin:status`(?![\w:-])', paragraph)


# --- The example that fetches Purlin ----------------------------------------

# purlin: purlin_docs PROOF-26
def test_the_example_clones_purlin_at_the_signed_tag_of_this_version():
    with open(os.path.join(ROOT, 'VERSION'), encoding='utf-8') as handle:
        version = handle.read().strip()
    text = read(os.path.join(DOCS, 'running-and-evidence.md'))
    tags = re.findall(r'git clone [^\n]*--branch (\S+) [^\n]*/purlin\b', text)
    assert tags == ['signed/' + version], tags
    # Every clone is read on its own, two on one line included, and a branch
    # is named by `--branch`, `--branch=` or `-b`: exactly 1 clone of the
    # purlin repository names one, and it names the signed tag.
    clones = [clone for clone in re.split(r'\bgit clone\b', text)[1:]]
    named = []
    for clone in clones:
        command = re.split(r'\n|\|\||&&|;', clone)[0]
        branch = re.search(r'(?<!\S)(?:--branch[= ]|-b[= ]?)\s*(\S+)', command)
        if branch and re.search(r'/purlin(?:\.git)?\b', command):
            named.append(branch.group(1))
    assert named == ['signed/' + version], named
    # The clone of the purlin repository names that branch and no second
    # one: git takes the last branch a command names.
    every = []
    for clone in clones:
        command = re.split(r'\n|\|\||&&|;', clone)[0]
        if re.search(r'/purlin(?:\.git)?\b', command):
            every += re.findall(
                r'(?<!\S)(?:--branch[= ]|-b[= ]?)\s*(\S+)', command)
    assert every == ['signed/' + version], every


# --- The index --------------------------------------------------------------

COUNT_WORDS = {11: 'Eleven', 12: 'Twelve', 13: 'Thirteen', 14: 'Fourteen'}
GUIDES_LINE = '%s guides, and the references behind them.'


def guides_listed(text):
    """The page each row of the table under `## Guides` links in its first
    cell, in the table's order. A row whose first cell is not exactly one
    link gives the cell as it stands."""
    part = under(text, 'Guides')
    rows = [line for line in part.splitlines() if line.startswith('|')][2:]
    listed = []
    for row in rows:
        cell = row.split('|')[1].strip()
        link = re.fullmatch(r'\[[^\]]+\]\(([^)\s]+)\)', cell)
        listed.append(link.group(1) if link else cell)
    return listed


def line_under_title(text):
    """The first line that is not blank after the page's `# ` title."""
    lines = text.splitlines()
    assert lines[0].startswith('# '), lines[0]
    return next(line for line in lines[1:] if line.strip())


# purlin: purlin_docs PROOF-27
def test_the_index_lists_every_page_once_and_says_how_many():
    text = read(os.path.join(DOCS, 'index.md'))
    others = [os.path.basename(page) for page in pages()
              if page != 'docs/index.md']
    listed = guides_listed(text)
    assert sorted(listed) == others, (listed, others)
    assert len(listed) == 13, listed
    assert line_under_title(text) == (
        'Thirteen guides, and the references behind them.')
    assert line_under_title(text) == GUIDES_LINE % COUNT_WORDS[len(others)]
    # A page listed twice, a page left out and a row that links nothing are
    # each seen: the list is the rows as they stand.
    sample = ('# Docs\n\nTwo guides.\n\n## Guides\n\n| Guide | For |\n|---|---|\n'
              '| [A](audit.md) | x |\n| [A again](audit.md) | x |\n'
              '| The dashboard | x |\n\n## Reference\n\n| [C](c.md) | x |\n')
    assert guides_listed(sample) == ['audit.md', 'audit.md', 'The dashboard']
    assert line_under_title(sample) == 'Two guides.'


# --- The two pages on AI proofs ---------------------------------------------

AI_PAGES = ('testing-ai.md', 'graded-by-ai.md')
FOLDED_IN = ('how-purlin-works.md', 'specs-and-anchors.md',
             'running-and-evidence.md', 'audit.md', 'sign-off.md',
             'regulated.md')


def pages_linked(text):
    """The file each relative link of a page names, its `#` part dropped."""
    return {target.partition('#')[0] for target in targets(text)
            if not re.match(r'[a-z]+:', target)}


def links_missing(texts):
    """`<page>: <target>` for each link the two rules ask for and a page of
    `texts`, `{page: text}`, does not hold."""
    asked = [('testing-ai.md', 'graded-by-ai.md'),
             ('graded-by-ai.md', 'testing-ai.md')]
    asked += [(page, target) for page in FOLDED_IN for target in AI_PAGES]
    return ['%s: %s' % (page, target) for page, target in asked
            if target not in pages_linked(texts.get(page, ''))]


# purlin: purlin_docs PROOF-28
def test_the_two_ai_pages_are_linked_from_each_other_and_each_folding_page():
    texts = {page: read(os.path.join(DOCS, page))
             for page in AI_PAGES + FOLDED_IN}
    assert links_missing(texts) == []
    # A link shown as code is text a reader sees and cannot follow: with
    # every fenced block and every code span taken out, each page still
    # holds each link.
    followed = {page: re.sub(r'`[^`]*`', '',
                             re.sub(r'^```.*?^```$', '', text,
                                    flags=re.M | re.S))
                for page, text in texts.items()}
    assert links_missing(followed) == []
    # A page that names the other in plain words, or in a code span, does
    # not link it; a link with a `#` part does.
    sample = dict(texts)
    sample['testing-ai.md'] = 'See graded-by-ai.md and `graded-by-ai.md`.'
    sample['audit.md'] = '[a](testing-ai.md#where-it-stops)'
    assert links_missing(sample) == ['testing-ai.md: graded-by-ai.md',
                                     'audit.md: graded-by-ai.md']


def diagrams(text):
    """Each fenced `mermaid` block of a page, as its lines."""
    return [block.strip('\n').splitlines() for block
            in re.findall(r'^```mermaid\n(.*?)^```$', text, re.M | re.S)]


def box_labels(lines):
    """The label of every box a mermaid flow chart draws: the quoted text
    inside `[...]`, `(...)` or `{...}` after a node's id."""
    return re.findall(r'\b\w+(?:\[|\(\[|\{)"([^"]*)"', '\n'.join(lines))


# purlin: purlin_docs PROOF-29
def test_each_ai_page_holds_one_flow_diagram_with_each_box_named_in_bold():
    for page in AI_PAGES:
        found = diagrams(read(os.path.join(DOCS, page)))
        assert len(found) == 1, (page, len(found))
        assert found[0][0] == 'flowchart LR', (page, found[0][0])
        labels = box_labels(found[0])
        assert len(labels) >= 5, (page, labels)
        assert [label for label in labels
                if not label.startswith('<b>')] == [], page
        # Every box, one whose label is written without quotation marks
        # included: with the labels on the arrows taken out, what follows
        # the bracket that opens each box is `"<b>`.
        drawn = re.sub(r'\|[^|\n]*\|', '', '\n'.join(found[0][1:]))
        drawn = re.sub(r'"[^"\n]*"',
                       lambda held: ('"<b>' if held.group(0).startswith('"<b>')
                                     else '"'), drawn)
        opened = re.findall(r'\b\w+(?:\(\[|\[|\{|\()(.{0,4})', drawn)
        assert len(opened) == len(labels), (page, opened, labels)
        assert [box for box in opened if box != '"<b>'] == [], (page, opened)
    # A label on an arrow is no box, and a box whose name is not bold is
    # found.
    sample = ['flowchart LR', '    A["<b>One</b><br>x"] -->|"yes"| B(["Two"])',
              '    B --> C{"<b>Three</b>"}']
    assert box_labels(sample) == ['<b>One</b><br>x', 'Two', '<b>Three</b>']


# --- The count of spot tests ------------------------------------------------

def check_counts(text):
    """Each `The <word> checks` the text holds, as the word."""
    return re.findall(r'\bThe (\w+) checks\b', text)


# purlin: purlin_docs PROOF-30
def test_the_audit_pages_count_the_spot_tests_as_the_reference_does():
    reference = read(os.path.join(ROOT, 'references', 'review_criteria.md'))
    assert re.findall(r'^### The (\w+) checks$', reference, re.M) == ['seven']
    for page in (AUDIT_PAGE, RESEARCH_PAGE):
        text = ' '.join(read(page).split())
        assert text.count('The seven checks are in') == 1, page
        assert check_counts(text) == ['seven'], (page, check_counts(text))
        # No other count under any of the names the checks go by: a number,
        # in a word or in digits, before `checks`, `spot tests`, `spot
        # checks` or `heuristics`, with at most one word between.
        counted = re.findall(
            r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|'
            r'twelve|\d+) (?:\w+ )?(?:checks|spot tests|spot checks|'
            r'heuristics)\b', text, re.I)
        assert counted == ['seven'], (page, counted)
    assert check_counts('The six checks are in. The seven checks') == [
        'six', 'seven']
