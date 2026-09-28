/* The Rule screen: one rule, its level and the cells the gate reaches,
   the brief the machine wrote, and the proofs that stand for it. */

function ruleInView() {
  var feature = featureNamed(VIEW.feature);
  if (!feature) { return null; }
  var found = null;
  (feature.rules || []).forEach(function (r) {
    if (r.id === VIEW.rule) { found = r; }
  });
  return found ? {feature: feature, rule: found} : null;
}

/* One small box per operating system a counting run covered, in the tone of
   what that run found there. The board draws no such box; this is where the
   page says which platform passed, and the hover says where the run came from
   and how old it is. */
function platformBoxes(cell) {
  var platforms = (cell && cell.platforms) || {};
  return Object.keys(platforms).sort().map(function (os) {
    var entry = platforms[os];
    return '<span class="os ' + (entry.word === 'passed' ? 'pass'
        : entry.word === 'failed' ? 'fail' : 'none') + '"'
      + hover([[os, entry.word, entry.source || 'local',
        ageText(entry.at).text].join(' \u00b7 ')])
      + '>' + esc(os.slice(0, 3)) + '</span>';
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
    return text !== 'by ' + cell.signer;
  }).join('; ');
  var beside = name === 'passed' ? platformBoxes(cell)
    : name === 'signed' && cell.signer ? '<span class="mono sec">'
      + esc(cell.signer + ' \u00b7 ' + when(cell.at)) + '</span>' : '';
  return '<dt>' + esc(CELL_LABELS[name]) + '</dt><dd>' + pill(cell.word)
    + (beside ? ' ' + beside : '')
    + (reasons ? ' <span class="sec">' + esc(reasons) + '</span>' : '')
    + '</dd>';
}

/* What the audit found, and nothing about what to do with it: the strength
   beside the minimum this gate asks for, then what the AI audit observed, one
   sentence to a line as it wrote them, then whether it could settle the
   question. The audit writes sentences, so there is no list of check names
   to render here. */
function briefPanel(feature, rule) {
  var cell = cellOf(rule, 'strong');
  if (!cell) { return ''; }
  var lines = [];
  lines.push('<p class="sec">' + (cell.strength == null
    ? 'Test strength is n/a: nothing measured it.'
    : esc('Test strength ' + Math.round(cell.strength) + '%, against a '
        + 'minimum of ' + minStrength() + '%.')) + '</p>');
  (cell.observations || []).forEach(function (text) {
    lines.push('<p class="sec">' + esc(text) + '</p>');
  });
  if (cell.settled === true) {
    lines.push('<p class="sec">The AI audit settled the question.</p>');
  } else if (cell.settled === false) {
    lines.push('<p class="sec">The AI audit could not settle the question, '
      + 'so a person states what they see.</p>');
  }
  if (cell.evidence) {
    lines.push('<p class="sec">' + hostLink(cell.evidence, cell.evidence)
      + '</p>');
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
  return path.split('/').pop().split('.')[2] || '';
}

/* A signature is a signed commit, so this page cannot write one: it names the
   command that does, and reads back the signatures already committed. */
function signPanel(feature, rule) {
  var cell = cellOf(rule, 'signed');
  if (!cell) { return ''; }
  if (cell.word === 'signed') {
    return '<div class="panel"><h2>Signed</h2><p class="sec">'
      + esc('Signed by ' + (cell.signer || signerOf(cell.path || '')
          || 'a person') + ' on ' + when(cell.at)
        + ', against the rule, proof and test text this screen shows. The '
        + 'signature file beside the spec carries the commit that signed it.')
      + '</p></div>';
  }
  return '<div class="panel"><h2>To sign</h2>'
    + '<p><span class="cmd">purlin:sign ' + esc(feature.name) + ' '
    + esc(rule.id) + '</span> <span class="sec">from Claude Code</span></p>'
    + '<p class="sec">' + (rule.level !== 'signed'
      ? 'This rule’s level is ' + esc(rule.level) + ', so it asks for no '
        + 'signature; one written anyway still counts.'
      : 'A signature is a signed commit that names its signer; the page '
        + 'shows it once it is committed.') + '</p></div>';
}

function proofPanel(proof) {
  var tests = (proof.tests || []).map(function (t) {
    return esc(t.file) + ' :: ' + esc(t.name);
  }).join('\n') || 'no tagged test yet';
  var tags = (proof.manual ? ['@manual'] : [])
    .concat(proof.env ? ['@env(' + proof.env + ')'] : []);
  return '<div class="panel"><dl class="kv">'
    + '<dt>' + esc(proof.id) + '</dt><dd>' + esc(proof.text) + '</dd>'
    + (tags.length ? '<dt>Tags</dt><dd>' + tag(tags.join(' '), true) + '</dd>'
      : '')
    + '<dt>Tests</dt><dd><pre class="code">' + tests + '</pre></dd>'
    + '</dl></div>';
}

/* The link back closes the rule rather than leaving it open behind another
   screen, and it returns to the screen the rule was opened from. */
function backLink() {
  var from = VIEW.from === 'review' && level('strong') ? 'review'
    : VIEW.from === 'sign' && level('signed') ? 'sign' : 'board';
  var label = {review: 'Review', sign: 'Sign', board: 'Board'}[from];
  return '<button class="btn" data-act="close" data-screen="' + from + '">← '
    + label + '</button>';
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
  if (level('strong')) {
    rows.push('<dt>Level</dt><dd>' + levelTag(rule) + ' <span class="sec">'
      + esc(levelSource(rule)) + '</span></dd>');
  }
  rows.push('<dt>Spec</dt><dd>' + hostLink(feature.spec_path, feature.spec_path)
    + '</dd>');
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
