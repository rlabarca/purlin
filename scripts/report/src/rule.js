/* The Rule screen: one rule and the cells the gate reaches, what the audit
   found, the signature, the proofs that stand for it with the tests that
   carry them, and the tests marked with the rule's own id. */

/* The open rule, by the spec that owns it and its id: opening
   `ai_audit RULE-1` and `security_no_dangerous_patterns RULE-1` opens two
   rules, wherever either was clicked. */
function ruleInView() {
  var feature = featureNamed(VIEW.feature);
  var found = ruleNamed(VIEW.feature, VIEW.rule);
  return feature && found ? {feature: feature, rule: found} : null;
}

/* One small box per operating system a counting run covered, in the tone of
   what that run found there, labelled with the system's short word. The
   board draws no such box; this is where the page says which system passed,
   and the hover names the system and says where the run came from and how
   old it is. */
function platformBoxes(cell) {
  var platforms = (cell && cell.platforms) || {};
  return Object.keys(platforms).sort().map(function (os) {
    var entry = platforms[os];
    return '<span class="os ' + (entry.word === 'passed' ? 'pass'
        : entry.word === 'failed' ? 'fail' : 'none') + '"'
      + hover([[systemWords(os).word, entry.word, entry.source || 'local',
        ageText(entry.at).text].join(DOT)])
      + '>' + esc(systemWords(os).short) + '</span>';
  }).join(' ');
}

/* One row per cell the gate reaches: the word it reads, what the payload
   carries beside that word, then the reasons, each already a sentence
   fragment the payload wrote. The passed cell's platforms and the signed
   cell's signer and date are facts the word alone leaves out. */
function cellRow(rule, name) {
  var cell = cellOf(rule, name);
  if (!cell) { return ''; }
  var reasons = (cell.reasons || []).filter(function (text) {
    return text !== 'by ' + cell.signer
      && (showsProofs() || text !== 'no proof written');
  }).join('; ');
  var beside = name === 'passed' ? platformBoxes(cell)
    : name === 'signed' && cell.signer ? '<span class="mono sec">'
      + esc(cell.signer + ' \u00b7 ' + when(cell.at)) + '</span>' : '';
  return '<dt>' + esc(CELL_LABELS[name]) + '</dt><dd>' + pill(cell.word)
    + (beside ? ' ' + beside : '')
    + (reasons ? ' <span class="sec">' + esc(reasons) + '</span>' : '')
    + '</dd>';
}

/* What the audit found, and nothing about what to do with it, drawn where
   the gate asks for the audit, which is where the rule has a strong cell:
   its answer,
   each finding on its own line as the audit wrote it, the test strength
   beside the minimum this gate asks for where one was measured and nothing
   of strength where none was, then the model that read the rule and when.
   The audit writes sentences, so there is no list of check names to render
   here. */
function auditPanel(rule) {
  var cell = cellOf(rule, 'strong');
  if (!cell) { return ''; }
  var audit = rule.audit;
  var lines = [];
  var findings = (audit && audit.findings) || [];
  var answer = audit ? audit['verdict'] : null;
  if (!audit) {
    lines.push(line('No audit has read this rule\u2019s text, proof and '
      + 'test yet.'));
  } else if (answer === 'strong' && !findings.length) {
    lines.push(line('Strong. It found nothing.'));
  } else if (answer === 'undecided') {
    lines.push(line('Undecided. The AI audit could not decide, so the rule '
      + 'reads weak until its proof or test changes.'));
  } else {
    lines.push(line(answer === 'strong' ? 'Strong.' : 'Weak.'));
  }
  findings.forEach(function (text) { lines.push(line(text)); });
  if (cell.strength != null) {
    lines.push(line('Test strength ' + Math.round(cell.strength) + '%, against '
      + 'a minimum of ' + minStrength() + '%.'));
  }
  if (audit) {
    lines.push('<p class="sec">Read by <span class="mono">'
      + esc(audit.model || 'unknown') + '</span> on '
      + esc(moment(audit.at)) + '</p>');
    if (audit.path) {
      lines.push('<p class="sec">' + hostLink(audit.path, audit.path) + '</p>');
    }
  }
  return '<div class="panel"><h2>Audit</h2>' + lines.join('') + '</div>';
}

function line(text) { return '<p class="sec">' + esc(text) + '</p>'; }

/* The signature files that bind this rule. One is named
   <RULE-N>.<hash8>.<signer-slug>.json, so the third part names who. */
function signaturesFor(feature, rule) {
  return (feature.signatures || []).filter(function (path) {
    return path.split('/').pop().indexOf(rule.id + '.') === 0;
  });
}

/* A signature is a signed commit, so this page cannot write one: it names the
   command that does, and reads back the signature already committed: who
   signed, by name and email as git holds them, when, the key it was made
   with, and the machine the tests ran on in each system. The panel is drawn
   at the gate `signed` only, headed `Hand check` where a proof of the rule
   is `@manual` and nobody has checked it, and `Signature` otherwise. */
function signPanel(feature, rule) {
  var cell = cellOf(rule, 'signed');
  if (!level('signed') || !cell) { return ''; }
  if (cell.word === 'signed') {
    var who = [cell.signer_name, cell.signer].filter(Boolean).join(', ')
      || 'a person';
    var key = String(cell.key_fingerprint || '');
    var lines = ['Signed by ' + who + (cell.signer_name ? ',' : '') + ' on '
      + moment(cell.at)
      + (key ? ' with the key ending ...' + key.slice(-4) : '') + '.'];
    var machines = rule.machines || {};
    Object.keys(machines).sort().forEach(function (os) {
      lines.push('On ' + systemWords(os).word + ' the tests ran on '
        + machines[os] + '.');
    });
    lines.push('The signature covers the rule, its proof, its test, the '
      + 'code the spec lists, what the audit found and the machine the '
      + 'tests ran on, as this screen shows them.');
    return '<div class="panel"><h2>Signed</h2>' + lines.map(line).join('')
      + '</div>';
  }
  var hand = rule.left === 'to_test_by_hand';
  return '<div class="panel"><h2>' + (hand ? 'Hand check' : 'Signature')
    + '</h2><p><span class="cmd">' + esc('purlin:sign ' + feature.name + ' '
      + rule.id) + '</span> <span class="sec">from Claude Code</span></p>'
    + '<p class="sec">' + (hand ? 'A hand check is you checking the rule and '
        + 'signing it in one act; purlin:sign asks what you saw and records '
        + 'it. The page shows it once it is committed.'
      : 'A signature is a signed commit that names its signer; the page '
        + 'shows it once it is committed.') + '</p></div>';
}

/* The word a test reads: the evidence writes `pass`, `fail`, `missing` or
   `not run`, and the page shows the cell word the run gave the rule for
   each, so a test and its rule never disagree. */
var TEST_WORDS = {pass: 'passed', fail: 'failed', missing: 'not run',
  'not run': 'not run'};

/* A proof's own word, as the payload wrote it. At the gate `passed` a
   `@manual` proof reads `manual`, because that project is shown no word of
   a higher step. */
function proofWord(proof) {
  var word = proof.result || 'not run';
  return word === 'hand check' && !level('strong') ? 'manual' : word;
}

/* Tests, one line each, `file :: name` and the word its run gave it. A
   narrow line may break after a `::`, between a test's class and its name,
   rather than inside either. */
function testLines(tests) {
  return (tests || []).map(function (t) {
    return '<p><span class="mono">' + esc(t.file) + ' :: '
      + esc(t.name).split('::').join('::<wbr>')
      + '</span> ' + pill(TEST_WORDS[t.result] || 'not run') + '</p>';
  }).join('');
}

/* One proof: its id and words, its own result, its `@manual` and `@env`
   tags, which name the operating system it asks for, and its tests with
   what each found. The board draws it under a rule and the rule screen in
   its Proofs section, from this one function, so the two never disagree. */
function proofDetail(proof) {
  var tags = (proof.manual ? ['@manual'] : [])
    .concat(proof.env ? ['@env(' + proof.env + ')'] : []);
  var tests = testLines(proof.tests) || '<p class="sec">'
    + (proofWord(proof) === 'not run' ? 'No run has listed its tests yet.'
      : 'No test yet.') + '</p>';
  return '<dl class="kv">'
    + '<dt>' + esc(proof.id) + '</dt><dd>' + esc(proof.text) + '</dd>'
    + '<dt>Result</dt><dd>' + pill(proofWord(proof)) + '</dd>'
    + (tags.length ? '<dt>Tags</dt><dd>' + tag(tags.join(' '), true) + '</dd>'
      : '')
    + '<dt>Tests</dt><dd class="ptests">' + tests + '</dd></dl>';
}

function proofPanel(proof) {
  return '<div class="panel">' + proofDetail(proof) + '</div>';
}

/* The tests marked with the rule's own id, one line each with its result.
   Shown wherever a rule lists any, and always where the page shows no
   proofs, so a rule at the gate `passed` shows the tests behind it. */
function testsSection(rule) {
  var tests = rule.tests || [];
  if (!tests.length && showsProofs()) { return ''; }
  var lines = testLines(tests) || '<p class="sec">No test yet.</p>';
  return '<section><p class="eyebrow">Tests</p><div class="panel tests">'
    + lines + '</div></section>';
}

/* The link back closes the rule rather than leaving it open behind the
   board. */
function backLink() {
  return '<button class="btn" data-act="close">← Board</button>';
}

function renderRule() {
  var found = ruleInView();
  if (!found) {
    return '<div class="empty">That rule is not in this data. Go back to the '
      + 'board and pick one.</div>';
  }
  var feature = found.feature;
  var rule = found.rule;
  var rows = [];
  GATE_LEVELS.forEach(function (name) { rows.push(cellRow(rule, name)); });
  rows.push('<dt>Spec</dt><dd>' + hostLink(feature.spec_path, feature.spec_path)
    + '</dd>');
  rows.push('<dt>Last run</dt><dd>' + runLine(feature) + '</dd>');
  var signatures = cellOf(rule, 'signed') ? signaturesFor(feature, rule) : [];
  if (signatures.length) {
    rows.push('<dt>Signatures</dt><dd>' + signatures.map(function (path) {
      return hostLink(path, path.split('/').pop());
    }).join('<br>') + '</dd>');
  }
  return backLink()
    + '<section style="margin-top:var(--space-6)">'
    + '<p class="eyebrow">' + esc(feature.name) + '</p>'
    + '<h1>' + esc(rule.id) + '</h1>'
    + '<p class="sec">' + esc(rule.text) + '</p></section>'
    + '<section class="stack"><div class="panel"><dl class="kv">'
    + rows.join('') + '</dl></div>'
    + auditPanel(rule) + signPanel(feature, rule) + '</section>'
    + (showsProofs() ? '<section><p class="eyebrow">Proofs</p>'
      + '<div class="stack">' + ((rule.proofs || []).length
        ? rule.proofs.map(proofPanel).join('')
        : '<div class="panel sec">No proof written.</div>')
      + '</div></section>' : '')
    + testsSection(rule);
}
