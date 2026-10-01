import json, os, re
# DECK_ROOT names the folder the deck's files are written under; the default sits beside this script.
ROOT = os.environ.get('DECK_ROOT') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deck', 'project')
MONO = "font-family:'Courier New', monospace"
# A command or a file name inside a sentence: the viewer keeps the colour and drops the face.
def m(text):
    return '<span style="%s; color:#E6BEB0">%s</span>' % (MONO, text)
def mt(text):
    return '<span style="color:#C0793F">%s</span>' % text
SECTION = ('<section id="%s" data-transition="fade" style="background:#0C3444; color:#E4DDD4; '
           'font-family:Arial, sans-serif; padding:96px 128px 160px; display:flex; '
           'flex-direction:column; gap:%dpx">')
CARD = ('<div style="display:flex; flex-direction:column; gap:14px; padding:%dpx 24px; '
        'background:#092936; border-radius:10px">%s</div>')
LINE = '<div style="display:flex; align-items:center; gap:32px">%s</div>'
NUM = '<p style="font-size:32px; color:#BFCED5; width:48px">%s</p>'
CMD = '<p style="' + MONO + '; font-size:32px; color:#E6BEB0; width:%dpx">%s</p>'
WHAT = '<p style="font-size:32px; color:#E4DDD4; flex:1">%s</p>'
# A part of a step: no number, set in under the step it belongs to.
PART = ('<div style="display:flex; align-items:center; gap:32px; padding:0 0 0 80px">'
        '<p style="' + MONO + '; font-size:28px; color:#BFCED5; width:%dpx">%s</p>'
        '<p style="font-size:28px; color:#BFCED5; flex:1">%s</p></div>')
# The mark and the name, pinned to the top right of every slide. The mark is
# design/assets/logo.svg, the one for navy grounds, without its metadata.
def brand():
    svg = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'design', 'assets', 'logo.svg'), encoding='utf-8').read()
    svg = re.sub(r'<metadata>.*?</metadata>', '', svg, flags=re.S).replace(' xmlns:c2pa="http://c2pa.org/manifest"', '')
    svg = svg.replace('width="670" height="330"', 'aria-label="Purlin" style="width:106px; height:52px"')
    return ('<div style="position:absolute; right:128px; top:80px; width:260px; display:flex; align-items:center; '
            'justify-content:flex-end; gap:16px">%s<p style="font-size:36px; font-weight:600; color:#E4DDD4">Purlin</p></div>' % svg)
# numbers=False drops the count at the start of each row: a slide with one case has nothing to count.
def slide(sid, eyebrow, headline, rows, closing, notes, lead='', width=620, gap=20, pad=18, numbers=True):
    out = [SECTION % (sid, gap),
           '<p style="font-size:24px; letter-spacing:3px; text-transform:uppercase; color:#C0793F">%s</p>' % eyebrow,
           '<h2 style="font-size:64px; font-weight:600; line-height:1.1">%s</h2>' % headline]
    if lead:
        out.append('<p style="font-size:32px; color:#BFCED5">%s</p>' % lead)
    out.append('<div style="flex:1"></div>')
    for i, row in enumerate(rows, 1):
        name, what, parts = row[0], row[1], row[2] if len(row) > 2 else ()
        head = CMD % (width, name.strip('`'))
        lines = [LINE % ((NUM % i if numbers else '') + head + WHAT % what)]
        lines += [PART % (width, part, said) for part, said in parts]
        out.append(CARD % (pad, ''.join(lines)))
    out.append('<div style="flex:1"></div>')
    if closing:
        out.append('<p style="font-size:32px; color:#E4DDD4">%s</p>' % closing)
    out += [brand(), '<aside>%s</aside>' % notes, '</section>', '']
    with open(os.path.join(ROOT, 'slides', sid + '.html'), 'w', encoding='utf-8') as h:
        h.write('\n'.join(out))
os.makedirs(os.path.join(ROOT, 'slides'), exist_ok=True)
slide('why', 'What Purlin is for', 'Why use Purlin?', [
    ('Tests pass. Do they cover what was asked?', 'You write each requirement as a rule. Purlin ties every rule to the tests that show it, and calls out every rule that doesn\'t have a test.'),
    ('AI writes code &amp; tests fast. Are they any good?', 'The audit breaks the code the way each proof forbids and checks that the test notices.'),
    ('Something changed. Is the result still true?', 'A result stops counting when the rule, the test or the code changes, until the tests are run again.'),
    ('Someone has to sign it off.', 'When everyone is done, a person signs the evidence once and the version gets a signed tag. The evidence package is one file you hand over.'),
], '',
 'Purlin is a Claude Code plugin for spec-driven development. Product, QA and developers write the '
 'rules together, and Purlin keeps two facts: whether every rule\'s tests pass, and whether the '
 'evidence is signed. The audit and the sign-off are optional. Purlin cannot prove your code is '
 'correct, and it makes no claim of compliance.',
 lead='Purlin shows, rule by rule, that your software does what you said it must.', width=700)
slide('touches', 'Your project and your workflow', 'Purlin workflows don\'t change your project much', [
    ('A settings file', '%s holds your test command. Also a folder for evidence and a few lines in %s.' % (m('.purlin/config.json'), m('.gitignore'))),
    ('Your specs', 'Markdown files you write, under %s. Each holds the rules of one feature.' % m('specs/')),
    ('One comment per test', '%s above the test. The test itself does not change.' % m('# purlin: login PROOF-4')),
    ('Your test command', 'Purlin runs your tests the way you already do. Nothing is installed in your test suite.'),
    ('Your workflow', 'You commit and push as before. Purlin commits only when you ask, and adds no git hook and no background job.'),
], '',
 'Purlin reads the report your test framework already writes and ties each result to its comment by '
 'the name of the test. A test with no comment runs as always and is ignored. A test Purlin wrote '
 'and a test you wrote differ in nothing but who typed them. Setup also copies the dashboard page '
 'into the project, where git ignores it.', pad=16)
slide('start', 'Getting started', 'Start in under ten minutes', [
    ('Install the plugin', 'Inside Claude Code: %s.' % m('/plugin install purlin@purlin')),
    ('`purlin:init`', 'Sets the project up. It asks one thing: whether it may commit what it wrote.'),
    ('`purlin:spec`', 'Say in your own words what must be true. It writes the rules for you, one line each.'),
    ('`purlin:build`', 'Writes the code and its tests, or finds the tests you have. It adds one comment above each: %s.' % m('# purlin: cart PROOF-1')),
    ('`purlin:test`', 'Runs your tests and prints %s' % m('Tests: met. 3 of 3 rules pass.')),
], '',
 'You need git, Python 3.9 or later and Claude Code. The marketplace is added once per project with '
 'claude plugin marketplace add. Setup reads the test framework from the project; where it finds '
 'none it asks for the command that runs the tests.', pad=16)
slide('fromcode', 'An existing codebase', 'Starting from code you already have', [
    ('Reads the code', 'It surveys the project and proposes a list of features. You merge, split and rename until the list is right.'),
    ('Writes the rules', 'One file per feature. Each rule says what the code does today, with a plain sentence saying how that is shown.'),
    ('Uses the tests you have', 'Where a test already shows a rule, it offers to add the comment above that test. It writes no new test.'),
    ('Reports where you stand', 'How many rules it wrote, how many already pass, and which have no test yet.'),
], '<b>A person reads every rule.</b> A rule read from code says what the code does, not what it should do.',
 'An optional skill: run purlin:init first, then purlin:spec-from-code once. Twenty to forty features '
 'is normal for a mid-sized service. Each spec is committed on its own, and a session that ends '
 'halfway resumes at the next feature. Rules with no test go to purlin:build.',
 lead='%s is run once. It turns a codebase with no rules into one whose rules can be proven.' % m('purlin:spec-from-code'), width=560, pad=16)
slide('together', 'Working together', 'Product, QA and developers improve the specs together', [
    ('`purlin:spec`', 'Anyone writes or sharpens rules and proofs, in plain words with the AI or by hand.'),
    ('`purlin:build`', 'Writes the code and the tests, with one comment above each test naming its proof.'),
    ('`purlin:test`', 'Runs what changed and states the first fact, %s, or what fails.' % m('Tests: met')),
    ('`purlin:drift`', 'After a pull: which rules and proofs changed, and any number two branches both took, with a fix you accept by answering %s.' % m('y')),
], '<b>Nothing is signed while the work goes on.</b> Purlin has no roles: whoever knows the answer edits the spec.',
 'Purlin keeps two facts: whether every rule\'s tests pass on the committed evidence, and whether that '
 'evidence is signed. Nothing waits on a person while the specs change. When two branches take the '
 'same rule or proof number, the number already on the default branch keeps it, and the helper '
 'shows its renumbering plan before changing anything. A test comment whose proof was reworded '
 'since the test last changed is named on every run.', width=560, pad=16)
slide('audit', 'Are the tests any good?', 'The audit breaks the code the way each proof forbids', [
    ('Plain checks', 'Code reads every test: no assertion, a check that cannot fail, an expected value from the code itself, the proof\'s value missing.'),
    ('One targeted break', 'For each changed proof an AI makes the smallest change that breaks it, in a throwaway copy, and runs its test. Still passing means weak.'),
    ('An explanation', 'One sentence on what the weak test misses, so the fix is plain.'),
    ('`purlin:audit`', 'Run it when you choose. It ends on %s; ask the agent to iterate until 80%% are strong.' % m('42 of 50 rules strong (84%)')),
], '<b>Safe where it matters, fast enough to run often:</b> one break per changed proof, nothing to install.',
 'Why this design. Coverage says little about whether tests catch bugs (Inozemtseva and Holmes, '
 'ICSE 2014). Deliberately broken code is the best objective guide (Just et al., FSE 2014), but '
 'breaking everything is slow, so Google breaks only changed lines (Petrovic et al.) and Meta has a '
 'model write a few targeted breaks (ACH, FSE 2025). A model judging a test on its own is the weakest '
 'evidence, and AI-written tests are often tautological. Purlin aims one break at each proof, the '
 'claim a person wrote down: objective where the requirement is, cheap because only changed proofs '
 'are broken. It does not show the tests catch every bug. The full reasoning and sources are on the '
 'audit page of the docs, with Siddiq et al. (EASE 2024) on the smells of model-written tests and '
 'Alshahwan et al. (FSE 2024) on why Meta lets no generated test through without a measured check.',
 lead='AI-written tests tend to check what the code does, not what was asked (Konstantinou et al., 2024). '
      'Breaking the code on purpose is the strongest test of a test (Just et al., FSE 2014).', width=420, pad=16)
slide('signoff', 'The sign-off', 'When everyone is done, a person signs the evidence once', [
    ('Run and commit', 'A developer runs every test on the version to sign, the remote run for Windows included, and commits the results.'),
    ('`purlin:sign`', 'Opens with who ran the tests, where and when. Stops at each hand check, shows what the audit found, and asks for one signature.', [
        ('The package', 'One file: every rule, its proofs, its tests, the results, the audit, who wrote what, who signed.'),
        ('The tag', 'The first sign-off tags the version %s. Later sign-offs are added beside it.' % m('signed/1.4.0'))]),
    ('`git push`', 'You publish the branch and the tag.'),
], '<b>Signing is optional.</b> A project that never signs keeps its evidence all the same.',
 'Any role may sign, and several people may; Purlin creates evidence and enforces no policy about '
 'who. The sign-off refuses when a result was taken on other code than the version being signed, '
 'and names what to run again. One signature covers the whole package, over its fingerprint, in a '
 'signed commit. The tag itself is signed.', pad=16)
slide('remote', 'Remote runners', 'When does Purlin use a remote runner in your repository?', [
    ('A rule must hold on another operating system', 'You work on a Mac and a rule must hold on Windows. %s runs those tests on a runner and brings the results back.' % m('purlin:test --remote')),
    ('Set up the first time it is needed', 'The first remote run writes the runner file for your git host, GitHub or Azure DevOps, shows it, and asks before committing it.'),
    ('What the runner does', 'It runs the tests and saves the results. Its job fails only when a test fails.'),
], 'In every other case Purlin only works locally and does NOT add a pipeline file to your repository.',
 'One reason and no other. The runner runs only on the run branch purlin:test --remote creates, waits '
 'on and deletes. Each result records the machine and the operating system it came from, and the '
 'sign-off counts it only when it was taken on the version being signed.',
 lead='A remote runner is a machine your git host starts to run a job, as GitHub Actions does.', numbers=False)
slide('regulated', 'Regulated work', 'Purlin supplies evidence. It does not claim compliance.', [
    ('Purlin produces', 'Evidence for each rule: its tests and their results, what the audit found, who wrote what, who ran the tests and who signed.'),
    ('You hand over', 'The evidence package: one file for the version, made by %s, with its sign-offs.' % m('purlin:sign')),
    ('Your system of record', 'The validated system your company uses for approval. It holds the document, decides who approves, and carries the approval that counts.'),
], '',
 'The package holds, for each rule: its words, its proofs, its tests, each result with when and '
 'where it ran and who ran it, what the audit found and which model judged, and who wrote each rule '
 'and proof and last changed each test, read from git. Each sign-off records who signed, when, with '
 'which key, what they were shown and every note they typed. A requirement number such as (URS-042) '
 'reaches it as a note in the rule\'s own words.')
slide('anchors', 'Shared rules', 'Anchors: rules the whole project must follow', [
    ('Written in this project', 'Write a rule once, such as no secret in the code. Tests across the whole project prove it, and no feature names it.'),
    ('Owned by another department', 'Security, GRC or GxP keep their rules in their own repository. Each project brings in the ones it must follow.'),
    ('Kept in step', '%s updates the copy. The status says when the source has moved on.' % m('purlin:anchor sync')),
    ('Design standards too', 'Design publishes its standards as an anchor. Tests across every screen prove them; a project with no screens has nothing to check.'),
], '<b>A rule only some features need</b> goes in those features\' own specs.',
 'Every anchor covers the whole project, and each of its rules is counted and audited once. An '
 'anchor\'s rule is written as "for every X in the project, Y holds", so a project with no X has '
 'nothing to break it; its test then skips with the reason, and the rule reads as met with that '
 'reason shown. A pinned copy is never edited in place; a change is made at the source.',
 lead='An anchor is a set of rules for the whole project, proven by tests that run across all of it.', width=560, pad=16)
deck = {"v": 4, "createdOnFiles": {"v": 1, "at": "2026-09-26T18:00:00Z"},
        "title": "Purlin gate workflows",
        "order": ["why", "touches", "start", "fromcode", "together", "audit", "signoff", "remote", "regulated", "anchors"],
        "sections": {"s1": {"description": "What Purlin is for, how little it changes in a project and a workflow, and how to start in under ten minutes or from code you already have", "start": "why"},
                     "s2": {"description": "Working together while the specs change, the audit that checks the tests are any good, and the sign-off when everyone is done", "start": "together"},
                     "s3": {"description": "The one case where Purlin uses a remote runner, where Purlin stops in regulated work, and how anchors carry rules for the whole project", "start": "remote"}},
        "faces": {}, "designSystems": []}
with open(os.path.join(ROOT, 'deck.json'), 'w', encoding='utf-8') as h:
    json.dump(deck, h, indent=2); h.write('\n')
