/* The one tab that holds a person's work: the queue, the rules that wait on
   a person, each saying what it needs. A hand check is a rule whose proof is
   @manual; a signature is a rule whose level
   is `signed` and that has passed its tests and its audit. `purlin:sign`
   walks the queue in this order, so the page reads it in this order too.

   A row reads the rule it points at for the text and the level, and the
   queue row for what it needs and the command that answers it, so the page,
   the rule screen and the walk can never disagree. */

/* When a rule arrives on the tab, at each gate that has one. Under `strong`
   no rule asks for a signature, so a hand check is the one way in. */
var ARRIVES = {
  strong: 'A rule arrives here when its level is strong and its proof is '
    + '@manual.',
  signed: 'A rule arrives here when its proof is @manual, or when its level '
    + 'is signed and it has passed its tests and its audit.'};

/* Long enough to read the claim, short enough that a queue of two hundred
   rows stays one column of text. The rest of the rule is on its own screen. */
var RULE_TEXT_MAX = 90;

function shortText(text) {
  var value = String(text == null ? '' : text);
  return value.length <= RULE_TEXT_MAX ? value
    : value.slice(0, RULE_TEXT_MAX).replace(/\s+\S*$/, '') + '…';
}

/* One row: the spec, the rule, its claim, its level, what it needs and the
   command. The row opens the rule screen, so the rule id is the link a reader
   follows to everything this row had to cut. */
function queueRow(entry) {
  var rule = listedRule(entry);
  return '<div class="rev" data-act="rule" data-feature="'
    + esc(entry.feature) + '" data-rule="' + esc(entry.rule) + '">'
    + '<span>' + esc(entry.feature) + '</span>'
    + '<span class="mono">' + esc(entry.rule) + '</span>'
    + '<span>' + esc(shortText(entry.text || (rule ? rule.text : ''))) + '</span>'
    + levelTag(rule || entry)
    + '<span' + hover([entry.word + ((entry.reasons || []).length
        ? DOT + entry.reasons.join('; ') : '')]) + '>' + esc(entry.need)
    + '</span>'
    + '<span class="cmd">' + esc(entry.command) + '</span></div>';
}

/* The heading row, so the six cells are named rather than guessed at. */
function listHead(labels) {
  return '<div class="rev th">' + labels.map(function (label) {
    return '<span>' + esc(label) + '</span>';
  }).join('') + '</div>';
}

function renderQueue() {
  var entries = DATA.queue || [];
  if (!entries.length) {
    return '<section><p class="eyebrow">Queue</p><div class="panel empty">'
      + 'No rule is waiting for a person. ' + ARRIVES[gateName()]
      + '</div></section>';
  }
  var hand = entries.filter(function (entry) {
    return entry.need === 'hand check';
  }).length;
  var head = '<section><p class="eyebrow">Queue</p><h1>'
    + entries.length + (entries.length === 1 ? ' rule needs' : ' rules need')
    + ' a person</h1><p class="line">Hand checks ' + hand + DOT
    + 'Signatures ' + (entries.length - hand) + '</p></section>';
  return head + '<section><div class="tbl">'
    + listHead(['Spec', 'Rule', 'What it claims', 'Level', 'Needs',
                'Command'])
    + entries.map(queueRow).join('') + '</div></section>';
}
