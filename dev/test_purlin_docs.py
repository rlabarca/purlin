"""The pages under `docs/`, read as a person on the git host reads them.

`specs/instructions/purlin_docs.md` holds three rules: every relative link
on the pages resolves, the audit page cites its research by links it lists
again under `Sources`, and the page on working together holds one paragraph
on working in more than one checkout.
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
    # Each link is followed from the page's own folder: one to a file the
    # repository does not hold, and one to a heading its file does not have,
    # are found, and one that climbs out of `docs/` to a real file is not.
    text = ('[a](how-purlin-works.md#no-such-heading) [b](no-such-page.md) '
            '[c](../README.md#install) [d](how-purlin-works.md#four-words)')
    assert broken_links('docs/index.md', text) == [
        'docs/index.md: how-purlin-works.md#no-such-heading',
        'docs/index.md: no-such-page.md']


# --- The audit page ---------------------------------------------------------

AUDIT_PAGE = os.path.join(DOCS, 'audit.md')
PAPERS = ('Inozemtseva and Holmes, ICSE 2014', 'Just et al., FSE 2014',
          'Petrović et al., TSE 2021', 'Foster et al., FSE 2025',
          'LLMorpheus')


def around_sources(text):
    """The audit page's text before its heading `Sources`, and the list
    under it."""
    before, heading, after = text.partition('\n## Sources\n')
    assert heading, 'docs/audit.md has no heading Sources'
    return before, after


def papers_not_cited(text):
    """Each paper of `PAPERS` that no link of `text` names in its words with
    a target starting `https://`."""
    cited = [words for words, target in LINK.findall(text)
             if target.startswith('https://')]
    return [paper for paper in PAPERS
            if not any(paper in words for words in cited)]


# purlin: purlin_docs PROOF-21
def test_the_audit_page_cites_the_five_papers_each_as_an_https_link():
    before, _ = around_sources(read(AUDIT_PAGE))
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
def test_every_link_of_the_audit_page_appears_again_under_sources():
    text = read(AUDIT_PAGE)
    before, after = around_sources(text)
    assert len(targets(before)) >= 10, targets(before)
    assert links_not_listed(text) == []
    # A link the text gives and the list leaves out is found.
    sample = ('[a](https://example.com/a.pdf) [b](https://example.com/b.pdf)'
              '\n\n## Sources\n\n- [a](https://example.com/a.pdf)\n')
    assert links_not_listed(sample) == ['https://example.com/b.pdf']


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
    assert 'Each checkout' in paragraph
    assert 'its own results' in paragraph
    assert 'its own dashboard' in paragraph
    assert 'merge' in paragraph
    assert '`purlin:status`' in paragraph
