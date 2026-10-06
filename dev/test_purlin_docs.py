"""The pages under `docs/`, read as a person on the git host reads them.

`specs/instructions/purlin_docs.md` holds four rules: every relative link
on the pages resolves, the audit page says what to do with a finding, it cites its research by links it lists
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
