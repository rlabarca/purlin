import json, os, re
# DECK_ROOT names the folder the deck's files are written under; the default sits beside this script.
ROOT = os.environ.get('DECK_ROOT') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deck', 'project')
MONO = "font-family:'Courier New', monospace"
# A command or a file name inside a sentence: the viewer keeps the colour and drops the face.
def m(text):
    return '<span style="%s; color:#E6BEB0; white-space:nowrap">%s</span>' % (MONO, text)
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
        '<p style="' + MONO + '; font-size:32px; color:#BFCED5; width:%dpx">%s</p>'
        '<p style="font-size:28px; color:#BFCED5; flex:1">%s</p></div>')
# The mark and the name, pinned to the top right of every slide. The mark is
# design/assets/logo.svg, the one for navy grounds, without its metadata.
def brand():
    svg = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'design', 'assets', 'logo.svg'), encoding='utf-8').read()
    svg = re.sub(r'<metadata>.*?</metadata>', '', svg, flags=re.S).replace(' xmlns:c2pa="http://c2pa.org/manifest"', '')
    svg = svg.replace('width="670" height="330"', 'aria-label="Purlin" style="width:360px; height:177px"')
    # The mark touches the top and right edges of the slide, and the name sits centred under it:
    # one column, the same on every slide.
    return ('<div style="position:absolute; right:0px; top:0px; width:360px; display:flex; '
            'flex-direction:column; align-items:center; gap:8px">%s'
            '<p style="font-size:32px; font-weight:600; color:#E4DDD4; text-align:center">Purlin</p></div>' % svg)
# numbers=False drops the count at the start of each row: a slide with one case has nothing to count.
def slide(sid, eyebrow, headline, rows, closing, notes, lead='', width=620, gap=20, pad=18, numbers=True):
    # One label width and one card padding on every slide, so every text column starts in the same place.
    width, pad = 560, 16
    out = [SECTION % (sid, gap),
           '<h2 style="font-size:64px; font-weight:600; line-height:1.1; width:1380px">%s</h2>' % headline]
    if lead:
        out.append('<p style="font-size:32px; color:#BFCED5; width:1380px">%s</p>' % lead)
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
    ('AI writes code &amp; tests fast. Are they any good?', 'The audit plants a small bug for each proof and checks that the test catches it.'),
    ('Something changed. Is the result still true?', 'A result stops counting when the rule, the test or the code changes, until the tests are run again.'),
    ('Someone has to sign it off.', 'When everyone is done, a person signs the evidence once and the version gets a signed tag. The evidence package is one file you hand over.'),
], '',
 'Purlin is a Claude Code plugin for spec-driven development. Product, QA and developers write the '
 'rules together, and Purlin keeps two facts: whether every rule\'s tests pass, and whether the '
 'evidence is signed. The audit and the sign-off are optional. Purlin cannot prove your code is '
 'correct, and it makes no claim of compliance.',
 lead='Purlin shows, rule by rule, that your software does what you said it must.', width=700)
slide('compare', 'How Purlin differs', 'What the popular tools leave out', [
    ('GitHub Spec Kit', 'Turns a spec into a plan and code with an AI agent. <b>Missing:</b> tests tied to each requirement, evidence, a sign-off.'),
    ('Kiro', 'Turns requirements into code and generated tests, in its own editor. <b>Missing:</b> team work in git, evidence, a sign-off.'),
    ('Ketryx', 'Traces requirements to tests and collects signatures for regulated releases. <b>Missing:</b> help writing tests, or checking they catch bugs.'),
    ('Cucumber', 'Requirements as scenarios that run as tests. <b>Missing:</b> a check that tests catch bugs, evidence, a sign-off.'),
], '<b>Only Purlin does all three:</b> ties each requirement to its test, checks the test catches bugs, and keeps evidence a person can sign.',
 'GitHub Spec Kit (github.com/github/spec-kit) is the most used spec-driven workflow for AI agents; '
 'it checks that tasks are done, not that tests show each requirement. Kiro (kiro.dev) generates '
 'property-based tests from EARS requirements, inside its own IDE. Ketryx (ketryx.com) is a '
 'commercial compliance platform for life-science software, with Part 11 signatures over Jira and '
 'GitHub; it is a system of record, which Purlin hands evidence to. Cucumber and other BDD tools '
 'make plain-language scenarios executable. Purlin is the one that pairs each requirement with its '
 'test, plants a bug to check that test, and keeps the evidence and sign-off in the repository, '
 'with product, QA and developers working in git.',
 lead='Each solves part of the problem. None of them ties requirements, tests that catch bugs and evidence together.', width=420, pad=16)
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
 'into the project, where git ignores it, and each command that writes its data keeps it current.', pad=16)
slide('start', 'Getting started', 'Start in under ten minutes', [
    ('Install the plugin', 'Two lines in a terminal, from the README: add the marketplace, then %s.' % m('claude plugin install')),
    ('`purlin:init`', 'Sets the project up. It asks one thing: whether it may commit what it wrote.'),
    ('`purlin:spec`', 'Say in your own words what must be true. It writes the rules for you, one line each.'),
    ('`purlin:build`', 'Writes the code and its tests, or finds the tests you have. It adds one comment above each: %s.' % m('# purlin: cart PROOF-1')),
    ('`purlin:test`', 'Runs your tests and prints %s' % m('3 rules. 3 pass their tests.')),
], '',
 'You need git, Python 3.9 or later and Claude Code. In the project: claude plugin marketplace add '
 'https://github.com/rlabarca/purlin.git --scope project, then claude plugin install purlin@purlin '
 '--scope project, then Claude Code is started there. The first test run '
 'suggests the test command for the framework it finds, and you confirm it once.', pad=16)
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
slide('slow', 'Slow tests', 'Slow tests stay out of your way', [
    ('Mark it once', 'Add %s to the end of a proof whose tests take a long time, like integration tests.' % m('@slow')),
    ('`purlin:test`', 'While you build. It runs what changed and skips every slow test.'),
    ('`purlin:test --all`', 'When you want to check the whole project. It runs everything, slow tests included.'),
    ('Purlin remembers it', 'When a slow test is due, every status says so: %s' % m('1 slow proof to run: purlin:test --all')),
], '<b>Nothing to remember.</b> The tests are fully %s only after every slow test has passed.' % m('met'),
 'A slow proof is a proof like any other: one sentence saying how a rule is shown, and one test '
 'with a comment above it. The tag changes only when its test runs. A plain purlin:test, or one '
 'that names a feature, never starts it. purlin:test --all does, and that is the run a developer '
 'makes and commits before handing a version over. Once a file the spec covers changes, the slow '
 'proof reads not run and the status lists it, so a person who never knew the test existed is '
 'told when it is due and which command runs it. An anchor can use it too: a check across the '
 'whole project that takes minutes is tagged slow and stays out of every build run.',
 lead='Tag a proof %s. Its test is skipped while you build and runs when you check the whole project.' % m('@slow'), width=560, pad=16)
slide('audit', 'Are the tests any good?', 'The audit: would your tests catch a bug?', [
    ('Heuristic spot tests', 'Purlin flags tests that check nothing, check the code against itself, or never check the result the proof expects.'),
    ('Plant one bug', 'For each proof, an AI puts one small bug in a throwaway copy of your code, such as a sample age off by one hour.'),
    ('Run that proof\'s test', 'The test fails: the rule is %s. The test still passes: the rule is %s, and you see the bug it missed.' % (m('strong'), m('weak'))),
    ('`purlin:audit`', 'Tell the agent: <i>"Build and audit until 80% of rules are strong."</i>'),
], 'Why: AI-written tests often check what the code does, not what was asked (<a href="https://arxiv.org/pdf/2410.21136" style="color:#E6BEB0">Konstantinou et al., 2024</a>), and planting bugs is the most reliable test of a test (<a href="https://homes.cs.washington.edu/~mernst/pubs/mutation-effectiveness-fse2014.pdf" style="color:#E6BEB0">Just et al., FSE 2014</a>).',
 'A passing test only shows the code did what the test checked. The audit asks the harder '
 'question: if the code were wrong, would the test notice? It plants one small bug per proof, aimed '
 'at the exact claim the proof makes, in a copy of the project that is thrown away, and runs only '
 'that proof\'s test. Your code is never changed. Only proofs whose test or code changed since the '
 'last audit are tried again, so it stays fast, and nothing waits on it. Google plants bugs only in '
 'changed code (Petrovic et al., TSE 2021) and Meta has a model write a few targeted ones (Foster '
 'et al., FSE 2025); Purlin follows both. The full reasoning and sources are on the audit page of '
 'the docs.',
 lead='A passing test is not proof that it checks anything. The audit tries to make each test fail.', width=560, pad=16)
slide('signoff', 'The sign-off', 'When everyone is done, a person signs the evidence once', [
    ('Run and commit', 'A developer runs every test on the version to sign, the remote run for Windows included, and commits the results.'),
    ('`purlin:sign`', 'Opens with who ran the tests, where and when. Stops at each hand check, shows what the audit found, and asks for one signature.', [
        ('The package', 'One file: every rule, its proofs, its tests, the results, the audit, who wrote what, who signed.'),
        ('The tag', 'The first sign-off tags the version %s. Later sign-offs are added beside it.' % m('signed/1.4.0'))]),
    ('`git push`', 'You publish the branch and the tag.'),
], '<b>Signing is optional.</b> A project that never signs keeps its evidence all the same.',
 'Any role may sign, and several people may; Purlin creates evidence and enforces no policy about '
 'who. The sign-off refuses when a result was taken on other code than the version being signed, '
 'while files are changed and not committed, or while a rule has no test, and names what to run. '
 'One signature covers the whole package, over its fingerprint, in a '
 'signed commit. The tag itself is signed.', pad=16)
slide('remote', 'Other platforms', 'What if you have to test other platforms?', [
    ('Say where it must hold', 'Tag the proof %s. Every status then lists it: %s' % (m('@env(windows)'), m('22 rules to test on Windows'))),
    ('Ask the AI to set it up', 'It writes what your project needs for your git host, GitHub or Azure DevOps. The files live in your project and are yours to change.'),
    ('Run it your way', 'How a run starts is up to your project: from your desk, on a push or on a schedule. The results come back through git.'),
    ('Purlin tracks the results', 'Each result records the machine and the system it ran on, for every rule, like a result from your own machine.'),
], '<b>Purlin itself only works locally.</b> It drives no remote pipeline and adds none to your repository.',
 'Running tests on another platform is set up in your project, not built into Purlin. You ask the '
 'AI for it once: it writes the pipeline file for the git host you use and whatever starts a run, '
 'for example a small script that pushes a branch, waits for the run and pulls the results. How a '
 'run starts is each project\'s choice. On another machine with another git host, you ask again '
 'and pick. The run on the other platform uses purlin:test, so each rule gets its own result '
 'there, with the machine and the operating system recorded, and the sign-off counts it only when '
 'it was taken on the version being signed.',
 lead='Purlin runs your tests where you are. Reaching another platform is your project\'s own setup, and Purlin keeps the evidence.')
slide('regulated', 'Regulated work', 'Purlin supplies evidence. It does not claim compliance.', [
    ('Purlin produces', 'Evidence for each rule: its tests and their results, what the audit found, who wrote what, who ran the tests and who signed.'),
    ('You hand over', 'The evidence package: one file for the version, made by %s, with its sign-offs.' % m('purlin:sign')),
    ('Your system of record', 'The validated system your company uses for approval. It holds the document, decides who approves, and carries the approval that counts.'),
], '',
 'The package holds, for each rule: its words, its proofs, its tests, each result with when and '
 'where it ran and who ran it, what the audit found and which model was asked, and who wrote each rule '
 'and proof and last changed each test, read from git. Each sign-off records who signed, when, with '
 'which key, what they were shown and every note they typed. A requirement number such as (URS-042) '
 'reaches it as a note in the rule\'s own words.')
slide('manual', 'Judgment calls', 'Pass or fail. What about judgment calls?', [
    ('A proof is pass or fail', 'It names what is done, what is seen and the value that settles it, such as the message %s.' % m('Account locked')),
    ('A judgment call is not', 'It looks good. It is easy to use. No test can settle these, and an AI\'s opinion is a judgment too.'),
    ('Tag it %s' % '@manual', 'Write the proof and add %s to its end. No test runs for it, so it never slows a build.' % m('@manual')),
    ('`purlin:sign`', 'The sign-off stops at each one. A person checks it and types what they saw, and the note is kept in the signed evidence.'),
], '<b>Not everything is a rule.</b> Look and feel that nobody signs for is judged outside Purlin.',
 'A proof a test carries out ends in pass or fail, settled by a value the proof names. A claim '
 'that is a judgment, such as it looks good or it is easy to use, is not a test\'s to settle. '
 'For now the way to sign off on one is a hand check: a proof tagged manual, which the status '
 'shows as checked at sign-off until someone signs. The walk shows the last note with the version '
 'it was signed at and how many commits have come since, so the signer can judge whether it '
 'still holds. An AI may help a person look, but a test does not pass or fail on an AI\'s '
 'opinion; a test may ask a model a question with one right answer.',
 lead='A test settles a proof with a value. Some things only a person can judge.', width=560, pad=16)
slide('anchors', 'Shared rules', 'Anchors: rules the whole project must follow', [
    ('They can be in this project', 'Write a rule once, such as no secret in the code. Tests across the whole project prove it, and no feature names it.'),
    ('They can be owned elsewhere', 'Security, GRC / GxP, Design, etc. keep their rules in their own repository. Each project brings in the ones it must follow.', [
        ('Kept in step', '%s updates your copy. The status says when the source has moved on.' % m('purlin:anchor sync')),
        ('Read-only', 'Your copy is never edited in your project. A change is made at the source, by the team that owns it.')]),
], '<b>A rule that only some features need</b> goes in those features\' own specs.',
 'Every anchor covers the whole project, and each of its rules is counted and audited once. An '
 'anchor\'s rule is written as "for every X in the project, Y holds", so a project with no X has '
 'nothing to break it; its test then skips with the reason, and the rule reads as met with that '
 'reason shown. The two rows are the two kinds: an anchor written in this project, and a remote '
 'anchor another team owns, such as security, GRC, GxP or design standards. For a remote anchor, '
 'purlin:anchor sync brings in the newer version, the status says when the source has moved on, '
 'and the copy is never edited in place; a change is made at the source.',
 lead='An anchor is a set of rules for the whole project, proven by tests that run across all of it.', width=560, pad=16)
deck = {"v": 4, "createdOnFiles": {"v": 1, "at": "2026-09-26T18:00:00Z"},
        "title": "Purlin workflows",
        "order": ["why", "compare", "touches", "start", "fromcode", "together", "slow", "manual", "anchors", "audit", "signoff", "remote", "regulated"],
        "sections": {"s1": {"description": "What Purlin is for, how little it changes in a project and a workflow, and how to start in under ten minutes or from code you already have", "start": "why"},
                     "s2": {"description": "Working together while the specs change, slow tests that stay out of the way, judgment calls a person signs for, anchors that carry rules for the whole project, the audit that checks the tests are any good, and the sign-off when everyone is done", "start": "together"},
                     "s3": {"description": "How a project tests on other platforms while Purlin itself only works locally, and where Purlin stops in regulated work", "start": "remote"}},
        "faces": {}, "designSystems": []}
with open(os.path.join(ROOT, 'deck.json'), 'w', encoding='utf-8') as h:
    json.dump(deck, h, indent=2); h.write('\n')
