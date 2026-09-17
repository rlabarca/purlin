/* The Board: where every rule stands against the gate, and which specs hold
   the rules that have not got there yet. */

/* A rule the payload lists under the feature that owns it. An anchor's rule
   appears under every feature that requires it, so counting every entry would
   count that rule once per feature. */
function ownRules(feature) {
  return (feature.rules || []).filter(function (rule) {
    return rule.label === 'own';
  });
}

/* One tile per level the gate reaches, each counting the rules that got at
   least that far, and at `signed` a flag card beside them for the signatures
   that no longer match. A flag is counted beside the tiles, never instead of
   one, so it never shares their row. */
function statStrip() {
  var summary = DATA.summary || {};
  var shown = BUCKETS.filter(function (bucket) {
    return GATE_LEVELS.indexOf(bucket) < 0 || level(bucket);
  });
  var tiles = shown.map(function (bucket) {
    return '<div class="tile"><div class="tile-v" style="color:var(--state-'
      + bucketTone(bucket) + ')">' + reached(summary, bucket) + '</div>'
      + '<div class="tile-l">' + esc(BUCKET_LABELS[bucket]) + '</div></div>';
  }).join('');
  var stale = summary.stale || 0;
  var flag = level('signed')
    ? '<div class="flag' + (stale ? ' on' : '') + '"><div class="flag-v">'
      + stale + '</div><div class="flag-l">Stale</div></div>' : '';
  return '<div class="strip' + (flag ? ' flagged' : '') + '">'
    + '<div class="tiles">' + tiles + '</div>' + flag + '</div>';
}

/* The columns the gate reaches, and no others. `floor` is the width below
   which the column stops being read: a `0.6fr` track narrower than the word
   `STRENGTH` ran its heading into the next one, and a share bar with nowhere
   to go left its cell. Under the sum of the floors the table scrolls sideways
   rather than squeezing a column past it; those floors add up to 1288 pixels
   with every column drawn, which is what a 1440-wide window gives the table,
   so the scroll starts below that width and not above it. */
function boardColumns() {
  var columns = [{label: 'Spec', width: '2fr', floor: 160},
                 {label: 'Rules', width: '0.4fr', floor: 56, right: true},
                 {label: 'Spec status', width: '0.8fr', floor: 150},
                 {label: 'Tests', width: '0.9fr', floor: 150},
                 {label: 'Last run', width: '2.6fr', floor: 260}];
  if (level('strong')) {
    columns.push({label: 'Strength', width: '0.6fr', floor: 92, right: true},
                 {label: 'Strong', width: '1.2fr', floor: 130});
  }
  if (level('signed')) {
    columns.push({label: 'Signed', width: '1.1fr', floor: 130});
  }
  return columns;
}

/* How many of this spec's own rules the spec itself has finished: a rule no
   proof line names is drafted, and no test can be written for it. */
function specStatusCell(feature) {
  var ready = 0;
  var drafted = 0;
  ownRules(feature).forEach(function (rule) {
    if (rule.spec === 'drafted') { drafted += 1; } else { ready += 1; }
  });
  return counts([[ready, 'ready', 'pass'], [drafted, 'drafted', 'idle']]);
}

/* What the tagged tests found, as the passed cells read it. A rule waiting on
   an operating system or sitting behind changed code is in none of the three:
   the Last run column and the rule's own row say which. */
function testsCell(feature) {
  var found = {};
  ownRules(feature).forEach(function (rule) {
    var word = cellWord(rule, 'passed');
    found[word] = (found[word] || 0) + 1;
  });
  return counts([[found.passed || 0, 'passed', 'pass'],
                 [found.failed || 0, 'failing', 'fail'],
                 [found['no test'] || 0, 'no test', 'warn']]);
}

/* How many of this spec's rules carry a signature, and how many signatures no
   longer match. The share reads in the same three tones the share bar uses,
   so `5 of 24` says the same thing here and in the `Strong` column. */
function signedCell(feature) {
  var rollup = feature.rollup || {};
  var signed = rollup.signed || 0;
  var rules = rollup.rules || 0;
  return counts([[signed + ' of ' + rules, '',
    rules && signed === rules ? 'pass' : signed ? 'warn' : 'idle'],
    [rollup.stale || 0, 'stale', 'fail']]);
}

function featureRow(feature, columns) {
  var rollup = feature.rollup || {};
  var open = !!VIEW.features[feature.name];
  var cells = ['<span class="name"><span class="caret">'
    + (open ? '▼' : '▶') + '</span>' + designThumb(feature)
    + '<span class="n">' + esc(feature.name) + '</span></span>'];
  cells.push('<span class="mono">' + (rollup.rules || 0) + '</span>');
  cells.push(specStatusCell(feature));
  cells.push(testsCell(feature));
  cells.push(lastRun(feature));
  if (level('strong')) {
    cells.push(strength(rollup.test_strength == null
      ? feature.test_strength : rollup.test_strength));
    cells.push(ratio(rollup.strong || 0, rollup.rules || 0));
  }
  if (level('signed')) { cells.push(signedCell(feature)); }
  var row = '<div class="tr" data-act="feature" data-feature="'
    + esc(feature.name) + '">' + cells.map(function (cell, index) {
      return '<div' + (columns[index].right ? ' class="right"' : '') + '>'
        + cell + '</div>';
    }).join('') + '</div>';
  if (!open) { return row; }
  return row + visibleRules(feature).map(function (rule) {
    return '<div class="rule" data-act="rule" data-feature="'
      + esc(feature.name) + '" data-rule="' + esc(rule.id) + '">'
      + '<span class="rid">' + esc(rule.id) + '</span>'
      + '<span class="rt">' + esc(rule.text) + '</span>'
      + '<span class="rp">' + GATE_LEVELS.map(function (name) {
        var cell = cellOf(rule, name);
        return cell ? pill(cell.word) : '';
      }).join('') + '</span></div>';
  }).join('');
}

/* The band over a category's specs, and what its two numbers are. `MCP (6) 5
   of 113` left the reader to guess both, so the band says them: how many specs
   the category holds, then how many of their rules pass their tests, in the
   same words and the same mono face the headline uses. The gate ratio is not
   here: the `Signed` column carries it for each spec and the headline's
   second line carries it for the project. */
function groupBand(name, features, columns) {
  var open = VIEW.groups[name] !== false;
  var passing = 0;
  var total = 0;
  features.forEach(function (feature) {
    passing += reached(feature.rollup || {}, 'passing');
    total += (feature.rollup || {}).rules || 0;
  });
  return '<div class="group" data-act="group" data-group="' + esc(name) + '">'
    + '<span class="caret">' + (open ? '▼' : '▶') + '</span>'
    + '<span class="gt">' + esc(name) + '</span><span class="muted">·</span>'
    + '<span class="sec">' + features.length
    + (features.length === 1 ? ' spec' : ' specs')
    + '</span><span class="muted">·</span>' + ratio(passing, total, 'pass')
    + '</div>'
    + (open ? features.map(function (feature) {
      return featureRow(feature, columns);
    }).join('') : '');
}

function renderBoard() {
  var columns = boardColumns();
  var shown = (DATA.features || []).filter(function (feature) {
    return visibleRules(feature).length > 0;
  });
  var order = [];
  var groups = {};
  shown.forEach(function (feature) {
    var name = feature.category || 'specs';
    if (!groups[name]) { groups[name] = []; order.push(name); }
    groups[name].push(feature);
  });
  var summary = DATA.summary || {};
  var floor = columns.reduce(function (sum, c) { return sum + c.floor; }, 0);
  /* What the board is mainly about is the tests: how many rules pass them,
     how many fail and how many nothing has run against. The gate is the
     second line, because the signed layer is one column's business. */
  var head = '<section class="ledger"><h1 class="line"><b>'
    + reached(summary, 'passing') + '</b> of <b>' + (summary.rules || 0)
    + '</b> rules pass their tests<span class="sep">·</span><b>'
    + (summary.failing || 0) + '</b> failing<span class="sep">·</span><b>'
    + (summary.untested || 0) + '</b> untested</h1>'
    + '<p class="line"><span class="mono">' + (summary.met || 0)
    + '</span> of <span class="mono">' + (summary.rules || 0)
    + '</span> meet the gate <span class="mono">' + esc(gateName())
    + '</span></p></section><section>' + statStrip() + '</section>';
  var table = order.length
    ? '<div class="tbl" style="--cols:' + columns.map(function (c) {
        /* minmax sizes every track from these two numbers alone. A bare fr
           track grows to fit its widest cell, and the header and each row are
           separate grids, so their columns drifted apart. The floor is what
           keeps a heading and its content readable once the window narrows. */
        return 'minmax(' + c.floor + 'px,' + c.width + ')';
      }).join(' ') + ';--cols-floor:' + floor + 'px;--cols-gaps:'
      + (columns.length - 1) + '"><div class="th">' + columns.map(function (c) {
        return '<div' + (c.right ? ' class="right"' : '') + '>'
          + esc(c.label) + '</div>';
      }).join('') + '</div>' + order.map(function (name) {
        return groupBand(name, groups[name], columns);
      }).join('') + '</div>'
    : '<div class="panel empty">No rule matches every filter you set.</div>';
  return head + '<section><p class="eyebrow">Specs</p>' + filtersMarkup()
    + table + '</section>';
}
