/* The Review list: what CI put in front of a person, highest risk first, with
   the reason beside each rule. QA works this list, never the whole rule
   table. */

function renderReview() {
  var entries = DATA.review_list || [];
  if (!entries.length) {
    return '<section><p class="eyebrow">Review list</p>'
      + '<div class="panel empty">Nothing needs a look. CI adds a rule here '
      + 'when its risk asks for one, when an approval goes stale, or when the '
      + 'test strength falls below the minimum.</div></section>';
  }
  var head = '<section><p class="eyebrow">Review list</p><h1>'
    + entries.length + ' rules need a look</h1>'
    + '<p class="sec">Ordered by risk. Open a rule to read its proof, then '
    + 'approve it, add a case, or skip it.</p></section>';
  var body = RISKS.map(function (risk) {
    var group = entries.filter(function (entry) {
      return (entry.risk || 'low') === risk;
    });
    if (!group.length) { return ''; }
    return '<div class="group"><span class="gt">' + esc(risk)
      + ' risk</span><span class="muted">(' + group.length + ')</span></div>'
      + group.map(function (entry) {
        return '<div class="rev" data-act="rule" data-feature="'
          + esc(entry.feature) + '" data-rule="' + esc(entry.rule) + '">'
          + '<span>' + esc(entry.feature) + '</span>'
          + '<span class="mono">' + esc(entry.rule) + '</span>'
          + tag(risk, risk === 'low')
          + '<span class="sec">' + esc(entry.reason) + '</span></div>';
      }).join('');
  }).join('');
  return head + '<section><div class="tbl">' + body + '</div></section>';
}
