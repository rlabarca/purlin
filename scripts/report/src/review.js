/* The two tabs that hold a person's work: Review, the rules the machine
   could not finish, and Sign, the rules whose level is `signed`, whose tests
   and audit are met, and that are waiting for a signature. `purlin:sign` walks them in that order, so the
   page reads them in that order too.

   A row on either tab reads the rule it points at rather than the list
   entry: the entry names the feature and the rule, and everything shown —
   the text, the level, the cell's word and its reasons — is the rule's own, so
   the page and the rule screen can never disagree. */

/* Long enough to read the claim, short enough that a list of two hundred rows
   stays one column of text. The rest of the rule is on its own screen. */
var RULE_TEXT_MAX = 90;

/* What each word the Review tab groups by means, as a sentence, for a rule
   whose cell carries no reason of its own. */
var KIND_SENTENCES = {
  'manual test': 'Its proof is @manual, so a person runs the test and states '
    + 'what they saw.',
  'unsettled': 'The AI audit could not settle it, so a person judges the '
    + 'proof against the test.',
  'held': 'A person holds it: the test does not prove the proof.'};

function shortText(text) {
  var value = String(text == null ? '' : text);
  return value.length <= RULE_TEXT_MAX ? value
    : value.slice(0, RULE_TEXT_MAX).replace(/\s+\S*$/, '') + '…';
}

function kindSentence(word) {
  return KIND_SENTENCES[word] || 'It is waiting because it reads ' + word + '.';
}

/* What the blocking cell says beyond its one word. The cell's own reasons are
   the specific ones, so they are printed where there are any; the word it
   reads stands in as a sentence where there are none. */
function reviewRowReasons(rule) {
  var cell = cellOf(rule, 'strong') || {};
  return (cell.reasons || []).length ? cell.reasons.join('; ')
    : kindSentence(cell.word);
}

/* One row of either tab: the same first four cells, then the two that differ.
   The row opens the rule screen, so the rule id is the link a reader follows
   to everything this row had to cut. */
function listRow(entry, rule, rest) {
  return '<div class="rev" data-act="rule" data-feature="'
    + esc(entry.feature) + '" data-rule="' + esc(entry.rule) + '">'
    + '<span>' + esc(entry.feature) + '</span>'
    + '<span class="mono">' + esc(entry.rule) + '</span>'
    + '<span>' + esc(rule ? shortText(rule.text) : '') + '</span>'
    + levelTag(rule) + rest + '</div>';
}

function reviewRow(entry) {
  var rule = listedRule(entry);
  var cell = rule ? cellOf(rule, 'strong') : null;
  return listRow(entry, rule, (cell ? pill(cell.word) : '<span></span>')
    + '<span class="sec">' + esc(rule ? reviewRowReasons(rule) : '')
    + '</span>');
}

function signRow(entry) {
  var rule = listedRule(entry);
  var cell = rule ? cellOf(rule, 'signed') : null;
  return listRow(entry, rule, (cell ? pill(cell.word) : '<span></span>')
    + '<span class="cmd">purlin:sign ' + esc(entry.feature) + ' '
    + esc(entry.rule) + '</span>');
}

/* The heading row of either tab, so the six cells are named rather than
   guessed at. */
function listHead(labels) {
  return '<div class="rev th">' + labels.map(function (label) {
    return '<span>' + esc(label) + '</span>';
  }).join('') + '</div>';
}

/* A rule whose level is highest is the one a project asked the most of, so
   it is read first inside its group; the payload already orders the list that
   way and the page keeps that order. */
function ofKind(entries, word) {
  return entries.filter(function (entry) {
    var rule = listedRule(entry);
    return rule && cellWord(rule, 'strong') === word;
  });
}

function renderReview() {
  var entries = DATA.review_list || [];
  if (!entries.length) {
    return '<section><p class="eyebrow">Review</p><div class="panel empty">'
      + 'No rule is waiting for a person. A rule arrives here when its proof '
      + 'is @manual, when the AI audit could not settle it, or when someone '
      + 'holds it.</div></section>';
  }
  var head = '<section><p class="eyebrow">Review</p><h1>'
    + entries.length + (entries.length === 1 ? ' rule needs' : ' rules need')
    + ' a person</h1><p class="line">Each of these is work only a person can '
    + 'do. Sign one with <span class="cmd">purlin:sign &lt;feature&gt; '
    + '&lt;RULE-N&gt;</span>, or hold it with the case the test misses.'
    + '</p></section>';
  var body = REVIEW_KINDS.map(function (word) {
    var group = ofKind(entries, word);
    if (!group.length) { return ''; }
    return '<div class="group"><span class="gt">' + esc(word)
      + '</span><span class="muted">(' + group.length + ')</span></div>'
      + group.map(reviewRow).join('');
  }).join('');
  return head + '<section><div class="tbl">'
    + listHead(['Spec', 'Rule', 'What it claims', 'Level', 'Reads', 'Why'])
    + body + '</div></section>';
}

function renderSign() {
  var entries = DATA.sign_list || [];
  if (!entries.length) {
    return '<section><p class="eyebrow">Sign</p><div class="panel empty">'
      + 'No rule is waiting for a signature. A rule arrives here once its '
      + 'level is signed, it has passed its tests and its audit, and nobody '
      + 'has signed the text it carries now.</div></section>';
  }
  var head = '<section><p class="eyebrow">Sign</p><h1>' + entries.length
    + (entries.length === 1 ? ' rule to sign' : ' rules to sign')
    + '</h1><p class="line">Each of these has passed its tests and its '
    + 'audit, so the evidence its level asks for is in. A signature is a signed commit '
    + 'that names its signer.</p></section>';
  return head + '<section><div class="tbl">'
    + listHead(['Spec', 'Rule', 'What it claims', 'Level', 'Signed', 'Command'])
    + entries.map(signRow).join('') + '</div></section>';
}
