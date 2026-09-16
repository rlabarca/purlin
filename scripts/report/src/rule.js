/* The Rule screen: one rule, the spec status and the cells the gate reaches,
   the brief the machine wrote, and the proofs that stand for it. */

var FINDING_LABELS = {
  'no_expected_value': 'no expected value',
  'vague_verb': 'vague verb',
  'missing_trigger': 'missing trigger',
  'tier_mismatch': 'tier mismatch',
  'implementation_coupling': 'names a symbol, not an outcome',
  'happy_path_only': 'no negative case'
};

/* The sentence the free checks already write, one per finding, copied from
   the checks module so the page and the brief say the same thing about the
   same proof rather than keeping a second set of words. */
var FINDING_TEXT = {
  'no_expected_value': 'Names no literal, number, quoted string or named constant, so almost any assertion would satisfy it.',
  'vague_verb': 'Uses a vague verb with no expected value beside it. A proof should be readable straight into a test.',
  'missing_trigger': 'Nothing runs before the assertion, so the proof reads an artifact that exists whether or not the code is right.',
  'tier_mismatch': 'An @e2e proof must read as an observable flow. Drive the real interface or retag the proof to the tier it exercises.',
  'implementation_coupling': 'Names a private symbol, a selector or a path instead of an observable outcome, so a refactor breaks the proof without changing behaviour.',
  'happy_path_only': 'No proof of this rule names a rejection, an error or a boundary.'
};

function findingLabel(name) { return FINDING_LABELS[name] || name; }

function findingText(name) { return FINDING_TEXT[name] || findingLabel(name); }

function ruleInView() {
  var feature = featureNamed(VIEW.feature);
  if (!feature) { return null; }
  var found = null;
  (feature.rules || []).forEach(function (rule) {
    if (rule.id === VIEW.rule) { found = rule; }
  });
  return found ? {feature: feature, rule: found} : null;
}

/* One row per cell the gate reaches: the word it reads, then the reasons it
   carries, each already a sentence fragment the payload wrote. */
function cellRow(rule, name) {
  var cell = cellOf(rule, name);
  if (!cell) { return ''; }
  var reasons = (cell.reasons || []).join('; ');
  return '<dt>' + esc(CELL_LABELS[name]) + '</dt><dd>' + pill(cell.word)
    + (reasons ? ' <span class="sec">' + esc(reasons) + '</span>' : '')
    + '</dd>';
}

/* The findings the free checks raised, grouped by finding and named against
   the proofs that carry them: a finding raised on the rule as a whole lands
   on every proof, so grouping states it once. A finding the strong cell
   carries without a proof beside it is still read out. */
function findingLines(rule, cell) {
  var order = [];
  var ids = {};
  (rule.proofs || []).forEach(function (proof) {
    (proof.findings || []).forEach(function (name) {
      if (!ids[name]) { ids[name] = []; order.push(name); }
      if (ids[name].indexOf(proof.id) < 0) { ids[name].push(proof.id); }
    });
  });
  ((cell && cell.findings) || []).forEach(function (name) {
    if (!ids[name]) { ids[name] = []; order.push(name); }
  });
  return order.map(function (name) {
    var where = ids[name].length
      ? '<span class="mono">' + esc(ids[name].join(', ')) + '</span>: ' : '';
    return '<p class="sec">' + where + esc(findingText(name)) + '</p>';
  });
}

/* What the audit found, and nothing about what to do with it: the strength
   beside the minimum this gate asks for, the free checks, what the model
   review observed, and whether it could settle the question. */
function briefPanel(feature, rule) {
  var cell = cellOf(rule, 'strong');
  if (!cell) { return ''; }
  var lines = [];
  lines.push('<p class="sec">' + (cell.strength == null
    ? 'Test strength is n/a: nothing measured it.'
    : esc('Test strength ' + Math.round(cell.strength) + '%, against a '
        + 'minimum of ' + minStrength() + '%.')) + '</p>');
  findingLines(rule, cell).forEach(function (line) { lines.push(line); });
  (cell.observations || []).forEach(function (text) {
    lines.push('<p class="sec">' + esc(text) + '</p>');
  });
  if (cell.settled === true) {
    lines.push('<p class="sec">The model review settled the question.</p>');
  } else if (cell.settled === false) {
    lines.push('<p class="sec">The model review could not settle the '
      + 'question, so a person states what they see.</p>');
  }
  if (cell.brief) {
    lines.push('<p class="sec">' + hostLink(cell.brief, cell.brief) + '</p>');
  }
  return '<div class="panel"><h2>Brief</h2>' + lines.join('') + '</div>';
}

/* The signature files that bind this rule. One is named
   <RULE-N>.<hash8>.<signer-slug>.json, so the third part names who. */
function signaturesFor(feature, rule) {
  return (feature.signatures || []).filter(function (path) {
    return path.split('/').pop().indexOf(rule.id + '.') === 0;
  });
}

function signerOf(path) {
  var parts = path.split('/').pop().split('.');
  return parts.length > 2 ? parts[2] : '';
}

/* A signature is a signed commit, so this page cannot write one: it names the
   command that does, and reads back the signatures already on the branch. */
function signPanel(feature, rule) {
  var cell = cellOf(rule, 'signed');
  if (!cell) { return ''; }
  if (cell.word === 'signed') {
    var who = cell.signer || (cell.path ? signerOf(cell.path) : '');
    return '<div class="panel"><h2>Signed</h2><p class="sec">'
      + esc('Signed by ' + (who || 'someone on the signer list')
        + ' against the rule, proof and test text this screen shows. The '
        + 'signature file beside the spec carries the commit that signed it.')
      + '</p></div>';
  }
  return '<div class="panel"><h2>To sign</h2>'
    + '<p><span class="cmd">purlin:sign ' + esc(feature.name) + ' '
    + esc(rule.id) + '</span> <span class="sec">from Claude Code</span></p>'
    + '<p class="sec">' + (cell.word === 'not required'
      ? 'No signature is required at this rule’s risk; one written '
        + 'anyway still counts.'
      : 'A signature is a signed commit by someone on the signer list; the '
        + 'page shows it once it is on the branch.') + '</p></div>';
}

function proofPanel(proof) {
  var tests = (proof.tests || []).map(function (test) {
    return esc(test.file) + ' :: ' + esc(test.name);
  }).join('\n') || 'no tagged test yet';
  var findings = (proof.findings || []).map(function (name) {
    return '<span class="finding">' + esc(findingLabel(name)) + '</span>';
  }).join(', ');
  return '<div class="panel"><dl class="kv">'
    + '<dt>' + esc(proof.id) + '</dt><dd>' + esc(proof.text) + '</dd>'
    + '<dt>Tier</dt><dd>' + tag(proof.tier + (proof.env ? ' · ' + proof.env : ''), true)
    + '</dd>'
    + '<dt>Tests</dt><dd><pre class="code">' + tests + '</pre></dd>'
    + (findings ? '<dt>Free checks</dt><dd>' + findings + '</dd>' : '')
    + '</dl></div>';
}

/* The link back closes the rule rather than leaving it open behind another
   screen, and it returns to the screen the rule was opened from. */
function backLink() {
  var from = VIEW.from === 'review' && level('strong') ? 'review' : 'board';
  return '<button class="btn" data-act="close" data-screen="' + from + '">'
    + (from === 'review' ? '← Review list' : '← Board') + '</button>';
}

function renderRule() {
  var found = ruleInView();
  if (!found) {
    return '<div class="empty">That rule is not in this data. Go back to the '
      + 'board and pick one.</div>';
  }
  var feature = found.feature;
  var rule = found.rule;
  var rows = ['<dt>Spec status</dt><dd>' + pill(rule.spec || 'drafted')
    + '</dd>'];
  GATE_LEVELS.forEach(function (name) { rows.push(cellRow(rule, name)); });
  if (level('strong')) {
    rows.push('<dt>Risk</dt><dd>' + riskTag(rule.risk) + '</dd>');
  }
  rows.push('<dt>Origin</dt><dd>' + tag(rule.origin, true) + '</dd>');
  if (rule.criterion) {
    rows.push('<dt>Criterion</dt><dd>' + tag(rule.criterion, true) + '</dd>');
  }
  rows.push('<dt>Spec</dt><dd>'
    + hostLink(feature.spec_path, feature.spec_path) + '</dd>');
  rows.push('<dt>Last run</dt><dd>' + recordLine(feature) + '</dd>');
  var signatures = level('signed') ? signaturesFor(feature, rule) : [];
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
    + briefPanel(feature, rule) + signPanel(feature, rule) + '</section>'
    + '<section><p class="eyebrow">Proofs</p><div class="stack">'
    + ((rule.proofs || []).length
      ? rule.proofs.map(proofPanel).join('')
      : '<div class="panel sec">This rule has no proof yet.</div>')
    + '</div></section>';
}
