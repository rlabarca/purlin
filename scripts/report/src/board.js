/* The Board: how many rules pass their tests and how many the audit found
   strong, and which specs hold the rules that have not got there yet,
   filtered by the work left to do. */

/* The boxes, in the order the work is done. At the gate `signed`, where
   every rule needs a proof, the `No proof` box comes first, counting the
   rules that have none yet; then `Passing`, the payload's
   `summary.steps.passed`, carrying the project's total under its label; then,
   where the audit found any rule strong or weak, `Strong`, the payload's
   `summary.audit.strong`. A count is green once every rule is in it and amber
   until then. Each box carries the hover its column carries, read over every
   spec. The terminal prints a summary sentence; the boxes carry the same
   counts, so the page prints none. */
function statStrip() {
  var summary = DATA.summary || {};
  var total = summary.rules || 0;
  var project = wholeProject();
  var boxes = [];
  if (level('signed')) {
    var missing = noProofLines();
    var count = missing.reduce(function (sum, pair) { return sum + pair[1]; },
                               0);
    boxes.push(box(NO_PROOF, count, count ? 'warn' : 'pass',
      missing.map(function (pair) { return pair[0] + DOT + pair[1]; })));
  }
  var passing = (summary.steps || {}).passed || 0;
  boxes.push(box(PASSING, passing, passing === total ? 'pass' : 'warn',
                 platformLines(project),
                 total + (total === 1 ? ' rule total' : ' rules total')));
  if (audited()) {
    var strong = (summary.audit || {}).strong || 0;
    boxes.push(box(STRONG, strong, strong === total ? 'pass' : 'warn',
                   auditLines(project), null));
  }
  return '<div class="strip"><div class="tiles">' + boxes.join('')
    + '</div></div>';
}

/* One box: its count in its tone, its label, a second line under the label
   where it has one, and its hover where it has one. */
function box(label, count, hue, lines, under) {
  return '<div class="tile"' + (lines.length ? hover(lines) : '')
    + '><div class="tile-v" style="color:var(--state-' + hue + ')">' + count
    + '</div><div class="tile-l">' + esc(label) + '</div>'
    + (under ? '<div class="tile-l tile-t">' + esc(under) + '</div>' : '')
    + '</div>';
}

/* The specs that hold a rule with no proof, and how many each holds, as
   `[[spec, count]]`: the kind `no_proof` the payload gives each such rule. */
function noProofLines() {
  var byFeature = {};
  var names = [];
  everyRule().forEach(function (pair) {
    if (pair.rule.left !== 'no_proof') { return; }
    var name = pair.feature.name;
    if (!(name in byFeature)) { byFeature[name] = 0; names.push(name); }
    byFeature[name] += 1;
  });
  return names.sort().map(function (name) { return [name, byFeature[name]]; });
}

/* The columns the project reaches, and no others. Every when, who and
   platform detail is in the cell's hover rather than a column of its own,
   which is what lets every column fit a 1024-wide window.

   `width` is the share of the table the column asks for once every column
   holds its content. A value never breaks inside itself, `42 · 2 no test`
   and `2 of 4 · 1 partial · 1 failing` alike, so each value column is at least
   as wide as its widest value: the rows share the table's own tracks, so that width is
   the same in every row. The spec's name is the one text that gives way,
   cut with an ellipsis at `floor` pixels, its full path in the hover. Under
   1024 pixels the table is no table: each spec is a block of labelled
   pairs, and the stylesheet says how. */
function boardColumns() {
  var columns = [{label: COLUMNS[0], width: '1.7fr', floor: 200},
                 {label: COLUMNS[1], width: '1.6fr'}];
  if (showsProofs()) {
    columns.push({label: COLUMNS[2], width: '2fr'});
  }
  columns.push({label: COLUMNS[3], width: '2fr'});
  if (audited()) {
    columns.push({label: COLUMNS[4], width: '1.5fr'});
  }
  return columns;
}

/* How many proof lines this spec holds, and how many of them no marked test
   runs. A proof nothing tests is the gap between what the spec claims and
   what the tests check, so it is on the board rather than one screen deeper,
   and its ids are in the hover. Both numbers are the rollup's own, so the
   cell reads what `board.proofs_cell` reads: a `@manual` proof declares that
   no test is written for it, and only the payload knows that. */
function proofsCell(feature) {
  var rollup = feature.rollup || {};
  var ids = rollup.proofs_without_test_ids || [];
  return '<span' + hover([ids.length ? 'no test' + DOT + ids.join(', ')
      : 'every proof has a test']) + '>'
    + counts([[rollup.proofs || 0, '', ''],
      [rollup.proofs_without_test || 0, WORDS.no_test, 'warn']]) + '</span>';
}

/* How many rules the spec has, the count alone, as `board.rules_cell`
   reads it: every rule a spec lists is its own. */
function rulesCell(feature) {
  return '<span class="mono">' + (feature.rules || []).length + '</span>';
}

/* What the marked tests found, as the passed cells read it: how many of the
   spec's rules passed everywhere they ran, then the two words that say a
   test did not pass. The hover says which platforms ran and what each
   found. */
function testsCell(feature) {
  var found = {};
  var rules = feature.rules || [];
  rules.forEach(function (rule) {
    var word = cellWord(rule, 'passed');
    found[word] = (found[word] || 0) + 1;
  });
  return '<span' + hover(platformLines(feature)) + '>'
    + counts([share(found.passed || 0, rules.length),
      [found.partial || 0, WORDS.partial, 'warn'],
      [found.failed || 0, WORDS.failing, 'fail']]) + '</span>';
}

/* `n of m` as the first part of a count cell: the share reads pass when every
   rule is there, warn while some are, and idle while none is. */
function share(count, total) {
  return [count + ' ' + WORDS.of + ' ' + total, '',
          total && count === total ? 'pass' : count ? 'warn' : 'idle'];
}

/* How many of the spec's rules the audit found strong, and beside it the
   test strength of the newest record, where one was measured; where none
   was, the cell says nothing of strength. The strength is a number to read,
   compared with nothing, so it carries no tone. No code is broken on purpose
   for an anchor, so an anchor's cell says nothing of strength whatever its
   record holds. The percentage carries its own hover saying what it is. */
function strongCell(feature) {
  var rollup = feature.rollup || {};
  var rules = feature.rules || [];
  if (!rules.length) { return ''; }
  var value = feature.is_anchor ? null : rollup.test_strength == null
    ? feature.test_strength : rollup.test_strength;
  var strong = rules.filter(function (rule) {
    return cellWord(rule, 'strong') === 'strong';
  }).length;
  var parts = [share(strong, rules.length)];
  if (value != null) {
    var pct = Math.floor(value);
    parts.push([pct + '%', '', '',
      ['Test strength: the tests caught ' + pct + ' of every 100 deliberate '
        + 'breaks of the code.']]);
  }
  var cell = counts(parts);
  return '<span' + hover(auditLines(feature)) + '>' + cell + '</span>';
}

/* A spec that names no files: Purlin cannot tell which code it covers, so a
   default `purlin:test` always runs it. The name says so, and the hover says
   why. */
function noScope(feature) {
  if (!feature.incomplete) { return ''; }
  return '<span class="sec ns"' + hover([feature.incomplete_reason
      || 'no > Scope: line']) + '>' + esc(DOT.replace(/^ /, '') + 'no scope')
    + '</span>';
}

function featureRow(feature, columns) {
  var rollup = feature.rollup || {};
  var open = !!VIEW.features[feature.name];
  var cells = ['<span class="name"><span class="caret">'
    + (open ? '▼' : '▶') + '</span>'
    + '<span class="n"' + hover([feature.spec_path || feature.name]) + '>'
    + esc(feature.name) + '</span>' + noScope(feature) + '</span>'];
  cells.push(rulesCell(feature));
  if (showsProofs()) { cells.push(proofsCell(feature)); }
  cells.push(testsCell(feature));
  if (audited()) { cells.push(strongCell(feature)); }
  /* Each value cell carries its column's heading, which a narrow screen,
     with no heading row, draws beside the value as a labelled pair. */
  var row = '<div class="tr" data-act="feature" data-feature="'
    + esc(feature.name) + '">' + cells.map(function (cell, index) {
      return '<div' + (index ? ' data-label="' + esc(columns[index].label)
        + '"' : '') + '>' + cell + '</div>';
    }).join('') + '</div>';
  if (!open) { return row; }
  return row + description(feature) + visibleRules(feature).map(function (rule) {
    var shown = !!VIEW.proofs[rule.feature + ' ' + rule.id];
    return '<div class="rule" data-act="rule" data-feature="'
      + esc(rule.feature) + '" data-rule="' + esc(rule.id) + '">'
      + '<span class="rid">' + esc(rule.id) + '</span>'
      + '<span class="rt">' + esc(rule.text) + '</span>'
      + '<span class="rp">' + badges(rule) + '</span>'
      + '<span class="rm">' + proofsToggle(rule, shown) + '</span></div>'
      + (shown ? proofsUnder(rule) : '');
  }).join('');
}

/* The spec's `> Description:`, drawn when its row is opened, above its
   rules. A spec that writes none shows nothing here. */
function description(feature) {
  return feature.description ? '<p class="desc">' + esc(feature.description)
    + '</p>' : '';
}

/* The control that opens a rule's proofs beneath its row. Closed, it says
   how many proofs the rule has, `2 proofs`, in the warn tone when one of
   them reads `failed` or `no test`, and `no proof` where it has none. A
   project at `passed` that writes no proof line is told nothing about
   proofs: the control opens the tests marked with the rule's own id,
   `1 test`, and is absent where there are none. */
function proofsToggle(rule, shown) {
  var proofs = rule.proofs || [];
  var tests = rule.tests || [];
  var label;
  var warn = false;
  if (showsProofs()) {
    label = proofs.length ? proofs.length + (proofs.length === 1 ? ' proof'
      : ' proofs') : 'no proof';
    warn = proofs.some(function (proof) {
      var word = proofWord(proof);
      return word === 'failed' || word === 'no test';
    });
  } else if (tests.length) {
    label = tests.length + (tests.length === 1 ? ' test' : ' tests');
    warn = tests.some(function (t) { return t.result === 'fail'; });
  } else {
    return '';
  }
  return '<button class="more" data-act="proofs" data-feature="'
    + esc(rule.feature) + '" data-rule="' + esc(rule.id) + '" aria-expanded="'
    + (shown ? 'true' : 'false') + '"><span class="caret" aria-hidden="true">'
    + (shown ? '▼' : '▶') + '</span><span'
    + (warn ? ' style="color:var(--state-warn)"' : '') + '>' + esc(label)
    + '</span></button>';
}

/* A rule unfolded beneath its row: each proof as the rule screen draws it.
   Why the rule has not reached a step, and what the audit found, are on the
   rule's own screen. A rule with no proof shows the tests marked with its
   own id the same way, and one with neither says no proof is written. */
function proofsUnder(rule) {
  var proofs = rule.proofs || [];
  var body = proofs.length ? proofs.map(function (proof) {
    return '<div class="proof">' + proofDetail(proof, rule) + '</div>';
  }).join('')
    : (rule.tests || []).length ? '<div class="proof"><dl class="kv">'
      + '<dt>Tests</dt><dd class="ptests">' + testLines(rule.tests)
      + '</dd></dl></div>'
    : '<p class="sec">No proof written.</p>';
  return '<div class="rule-proofs">' + body + '</div>';
}

/* The band over a category's specs, one row with two ends. At the left the
   glyph, the category's name, which is the strongest thing in the band, and
   how many specs it holds; at the right how many of their rules pass their
   tests, `187 of 187 rules pass`, and a bar of one fixed width, so the bars
   line up down the page. A band counts the rules of the specs it holds; an
   anchor stands in the anchors' section above and in no band. The whole band
   is the control that folds the group, from the keyboard too, and says
   whether it is open.
   Under 1024 pixels the right end drops beneath the left. */
function groupBand(name, features, columns) {
  var open = VIEW.groups[name] !== false;
  var rules = [].concat.apply([], features.map(function (feature) {
    return feature.rules || [];
  }));
  var total = rules.length;
  var passing = rules.filter(function (rule) {
    return cellWord(rule, 'passed') === 'passed'; }).length;
  var pct = total ? Math.round((passing / total) * 100) : 0;
  var hue = total && passing === total ? 'pass' : passing ? 'warn' : 'idle';
  return '<div class="group" role="button" tabindex="0" aria-expanded="'
    + (open ? 'true' : 'false') + '" data-act="group" data-group="'
    + esc(name) + '"><span class="gl"><span class="caret" aria-hidden="true">'
    + (open ? '▼' : '▶') + '</span><span class="gt">' + esc(name)
    + '</span><span class="gs">' + features.length
    + (features.length === 1 ? ' spec' : ' specs') + '</span></span>'
    + '<span class="gr"><span class="gc"><b>' + passing + ' ' + WORDS.of + ' '
    + total + '</b> ' + (total === 1 ? 'rule passes' : 'rules pass')
    + '</span><i class="bar" style="color:var(--state-' + hue + ')"><span'
    + ' style="width:' + pct + '%"></span></i></span></div>'
    + (open ? features.map(function (feature) {
      return featureRow(feature, columns);
    }).join('') : '');
}

/* One table under its small label: the heading row, then its rows. The
   table owns the tracks and every row shares them, so a heading and its
   cells start at one edge. A value column is never narrower than its widest
   value; the name gives way at its floor. */
function specTable(label, columns, body) {
  return '<section data-table="' + label.toLowerCase() + '"><p class="eyebrow">'
    + label + '</p><div class="tbl specs" style="--cols:'
    + columns.map(function (c) {
      return 'minmax(' + (c.floor ? c.floor + 'px' : 'max-content') + ','
        + c.width + ')';
    }).join(' ') + '"><div class="th">' + columns.map(function (c) {
      return '<div>' + esc(c.label) + '</div>';
    }).join('') + '</div>' + body + '</div></section>';
}

/* The board opens on the step boxes, then the filters, which apply to both
   tables beneath them: the anchors, where the project has one a filter
   leaves showing, and then the specs, grouped by category. The anchors'
   section says what they are, so they carry no band and no mark of their
   own. */
function renderBoard() {
  var columns = boardColumns();
  var shown = (DATA.features || []).filter(function (feature) {
    return visibleRules(feature).length > 0;
  });
  var anchors = shown.filter(function (f) { return f.is_anchor; });
  var order = [];
  var groups = {};
  shown.forEach(function (feature) {
    if (feature.is_anchor) { return; }
    var name = feature.category || 'specs';
    if (!groups[name]) { groups[name] = []; order.push(name); }
    groups[name].push(feature);
  });
  return '<section>' + statStrip() + '</section>' + filtersMarkup()
    + (anchors.length ? specTable('Anchors', columns, anchors.map(
      function (feature) { return featureRow(feature, columns); }).join(''))
      : '')
    + (order.length ? specTable('Specs', columns, order.map(function (name) {
      return groupBand(name, groups[name], columns);
    }).join('')) : anchors.length ? '' : '<section><p class="eyebrow">Specs'
      + '</p><div class="panel empty">No rule is left of this kind.</div>'
      + '</section>');
}
