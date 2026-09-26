/* The shell: the data file, the chrome, the router and the marks the three
   screens share.

   The data file declares a const, and a const cannot be declared twice in one
   window, so it is read inside a throwaway iframe that posts the value back.
   srcdoc inherits this page's base URL and origin, so .purlin/report-data.js
   resolves exactly as a script tag here would, on file:// as well, where
   fetch is blocked. The query string defeats the file:// cache. */

var DATA = null;
var VIEW = {screen: 'board', feature: null, rule: null, from: 'board',
            features: {}, groups: {}, filters: {}};
var SCHEMA = 6;
/* The data file is rewritten seconds after a tool call changed a spec, a
   record or a signature, and a tab left open would never notice. Coming back
   to the tab reloads it when what it holds is older than this. */
var REFRESH_AFTER = 60;

/* The three evidence levels, lowest first. The project's gate names the
   highest level that exists, and every cell, tile, column and filter above it
   is absent rather than empty: a board that asks a question its project has
   not opted into reads as a project falling short. */
var GATE_LEVELS = ['passed', 'strong', 'signed'];

/* The tiles, lowest level first. `Untested`, `Failing` and `Partial` count
   the rules that are not passing on every platform they ran on. The three
   above them are cumulative, not exclusive: a signed rule is still passing
   and still strong, so it is counted in all three. `stale` and `held` are
   flags counted beside the tiles, never instead of one. */
var BUCKETS = ['untested', 'failing', 'partial', 'passing', 'strong', 'signed'];
var BUCKET_LABELS = {untested: 'Untested', failing: 'Failing',
  partial: 'Partial', passing: 'Passing', strong: 'Strong', signed: 'Signed'};

/* What the three tiles that are not a level count, for their hovers. The
   three above them carry the project's own platform, audit and signer lines
   instead, which are the column hovers read over every spec. */
var TILE_HOVER = {
  untested: 'No test, no current run, or a spec line still drafted.',
  failing: 'Every platform that ran the tests found a failure.',
  partial: 'Passed on one platform, failed or did not run on another.'};

/* The board's six column headings and the words its cells append, in one
   place. `purlin:status` prints the same table, so a word changed here is
   changed in `scripts/mcp/purlin/status.py` in the same commit. */
var COLUMNS = ['Spec', 'Rules', 'Proofs', 'Tests', 'Strong', 'Signed'];
var WORDS = {of: 'of', without_test: 'without a test', partial: 'partial',
             failing: 'failing', stale: 'stale', passed: 'passed',
             failed: 'failed', not_run: 'not run'};

/* Every word a cell can read, and the tone it reads in. A word carries the
   same hue wherever it is drawn, so a pill on the board, a row on the rule
   screen and a row on the review list agree. */
var CELL_TONES = {'ready': 'pass', 'drafted': 'idle', 'passed': 'pass',
  'failed': 'fail', 'no test': 'warn', 'not run': 'warn', 'partial': 'warn',
  'code changed': 'warn', 'strong': 'pass', 'weak': 'warn', 'held': 'warn',
  'manual test': 'warn', 'manual audit': 'warn', 'signed': 'pass',
  'unsigned': 'warn', 'stale': 'fail', 'not required': 'idle'};

var CELL_LABELS = {passed: 'Passed', strong: 'Strong', signed: 'Signed'};
var RISKS = ['high', 'medium', 'low'];

function loadData(callback) {
  var frame = document.createElement('iframe');
  var done = false;
  frame.setAttribute('hidden', '');
  frame.setAttribute('aria-hidden', 'true');
  frame.style.display = 'none';

  function finish(value) {
    if (done) { return; }
    done = true;
    window.removeEventListener('message', onMessage);
    callback(value);
  }
  function onMessage(event) {
    if (event.source !== frame.contentWindow) { return; }
    if (!event.data || typeof event.data !== 'object') { return; }
    if (!('purlin' in event.data)) { return; }
    finish(event.data.purlin);
  }
  window.addEventListener('message', onMessage);
  frame.srcdoc = '<script src=".purlin/report-data.js?t=' + Date.now()
    + '"><\/script><script>parent.postMessage({purlin: '
    + '(typeof PURLIN_DATA === "undefined") ? null : PURLIN_DATA}, "*");<\/script>';
  document.body.appendChild(frame);
  setTimeout(function () { finish(null); }, 3000);
}

/* --- the gate --------------------------------------------------------- */

function gateName() {
  var gate = DATA && DATA.gate ? DATA.gate.gate : null;
  return GATE_LEVELS.indexOf(gate) >= 0 ? gate : GATE_LEVELS[0];
}

/* True when the project's gate is at this level or above it, which is the
   one question that decides whether a cell, a tile, a column or a filter is
   drawn at all. */
function level(name) {
  return GATE_LEVELS.indexOf(gateName()) >= GATE_LEVELS.indexOf(name);
}

function minStrength() { return (DATA.gate && DATA.gate.min_strength) || 0; }

/* --- marks the screens share ----------------------------------------- */

function esc(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
    return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
  });
}

function tone(word) { return CELL_TONES[word] || 'idle'; }

function pill(word) {
  return '<span class="pill' + (word === 'signed' ? ' solid' : '')
    + '" style="color:var(--state-' + tone(word) + ')"><b>'
    + esc(String(word).toUpperCase()) + '</b></span>';
}

/* A tile counts the rules that reached its level, and its tone answers the
   only question the tile is asked: does a rule sitting there meet this
   project's gate? Under `signed` a passing rule does not, so it reads warn. */
function bucketTone(bucket) {
  if (bucket === 'untested') { return 'idle'; }
  if (bucket === 'failing') { return 'fail'; }
  if (bucket === 'partial') { return 'warn'; }
  return (bucket === 'passing' ? 'passed' : bucket) === gateName() ? 'pass' : 'warn';
}

/* How many rules reached this level, read off the payload's exclusive
   buckets. The payload counts a rule once, in the highest bucket it reached;
   the board asks how many got at least this far, which is that bucket and
   every one above it. A name that is not a level is one bucket of its own. */
function reached(counted, name) {
  var from = GATE_LEVELS.indexOf(name === 'passing' ? 'passed' : name);
  return from < 0 ? counted[name] || 0
    : GATE_LEVELS.slice(from).reduce(function (sum, key) {
      return sum + (counted[key] || 0);
    }, 0);
}

function tag(text, plain) {
  return '<span class="tag' + (plain ? ' plain' : '') + '">' + esc(text) + '</span>';
}

/* A risk tag carries its level in the border: high in the fail hue, medium
   in the warn hue, low muted. The text stays the primary ink. */
function riskTag(risk) {
  var band = risk === 'high' || risk === 'medium' ? risk : 'low';
  return '<span class="tag risk-' + band + '">' + esc(risk || 'low') + '</span>';
}

/* `n of m` with a bar beside it. The bar is the share, so a spec of three
   rules and a spec of three hundred read at the same glance. `suffix` says
   what the share is of, where the column heading is not there to say it. */
function ratio(count, total, suffix) {
  var pct = total ? Math.round((count / total) * 100) : 0;
  return '<span class="cov" style="color:var(--state-'
    + (total && count === total ? 'pass' : count ? 'warn' : 'idle')
    + ')"><b>' + count + ' ' + WORDS.of + ' ' + total + '</b>'
    + (suffix ? '<span class="sec">' + esc(suffix) + '</span>' : '')
    + '<i><span style="width:' + pct + '%"></span></i></span>';
}

/* Several counts in one cell, each labelled with the word it counts and set
   in that word's tone. `24 passed · 2 failing` says what a bare `24 · 2 · 0`
   left the reader to work out from the heading. The first part is always
   drawn, because the column's total is the number the row is about; a later
   part at zero is not, because nothing is waiting there. Each item is
   `[count, word, tone]`, and a word may be empty where the count already
   reads as a sentence (`5 of 24`). The separator rides inside the part it
   introduces, so a cell narrow enough to wrap breaks between parts and never
   leaves a lone dot at the end of a line. */
function counts(items) {
  return '<span class="trio">' + items.filter(function (item, index) {
    return index === 0 || item[0];
  }).map(function (item, index) {
    var hue = index === 0 && !item[0] ? 'idle' : item[2];
    return '<b' + (hue ? ' style="color:var(--state-' + hue + ')"' : '') + '>'
      + (index ? '<i class="sec">·</i> ' : '')
      + esc(item[1] ? item[0] + ' ' + item[1] : item[0]) + '</b>';
  }).join('') + '</span>';
}

/* A hover is a `title` attribute: one item to a line, the parts of an item
   separated by the middot the rest of the board uses. The page carries no
   script beyond its own render, and a native tooltip is what a page opened
   from disk, printed, or read by a screen reader can still show. */
function hover(lines) { return ' title="' + esc(lines.join('\n')) + '"'; }

/* Every rule a spec owns. An anchor's rule appears under every feature that
   requires it, so counting every entry would count that rule once per
   feature. */
function ownRules(feature) {
  return (feature.rules || []).filter(function (r) { return r.label === 'own'; });
}

/* The whole project as one feature, so a tile's hover is its column's hover
   read over every spec rather than a second set of sums. */
function wholeProject() {
  var rules = [];
  var rollup = {latest_record: null};
  Object.keys(DATA.summary || {}).forEach(function (key) {
    rollup[key] = DATA.summary[key];
  });
  (DATA.features || []).forEach(function (feature) {
    ownRules(feature).forEach(function (rule) { rules.push(rule); });
    var found = (feature.rollup || {}).latest_record;
    if (found && newer(found.timestamp, (rollup.latest_record || {}).timestamp)) {
      rollup.latest_record = found;
    }
  });
  return {rules: rules, rollup: rollup};
}

/* One ISO stamp against another, either of which may be missing. */
function newer(one, two) { return (one || '') > (two || ''); }

/* One line per operating system this spec's counting runs covered, newest
   run first: what ran there, where the run came from, how old it is, and how
   its rules came out. The passed cell of each rule carries the map; a rule
   nothing current ran against carries none, so it is on no line. */
function platformLines(feature) {
  var byOs = {};
  var names = [];
  ownRules(feature).forEach(function (rule) {
    var platforms = ((rule.cells || {}).passed || {}).platforms || {};
    Object.keys(platforms).forEach(function (os) {
      var entry = platforms[os];
      if (!byOs[os]) { byOs[os] = {at: '', words: {}}; names.push(os); }
      var found = byOs[os];
      found.words[entry.word] = (found.words[entry.word] || 0) + 1;
      if (newer(entry.at, found.at)) { found.at = entry.at; found.source = entry.source; }
    });
  });
  if (!names.length) { return ['No counting run has covered a platform yet.']; }
  return names.sort(function (a, b) { return newer(byOs[a].at, byOs[b].at) ? -1 : 1; })
    .map(function (os) {
      var found = byOs[os];
      return [os, found.source || 'local', ageText(found.at).text].concat(
        [WORDS.passed, WORDS.failed, WORDS.not_run].filter(function (word) {
          return found.words[word];
        }).map(function (word) { return found.words[word] + ' ' + word; }))
        .join(' \u00b7 ');
    });
}

/* Where the newest audit came from, how old it is, and the strength this
   gate asks for. The strength itself is in the cell beside it. */
function auditLines(feature) {
  var record = (feature.rollup || {}).latest_record;
  return [record ? 'audit \u00b7 ' + (record.label || 'local') + ' \u00b7 '
      + ageText(record.timestamp).text
    : 'No audit has written a record here.',
    'minimum strength ' + minStrength() + '%'];
}

/* Who has signed a rule here and when their newest signature was written,
   then how many signatures no longer match. */
function signerLines(feature) {
  var byWho = {};
  var names = [];
  var stale = 0;
  ownRules(feature).forEach(function (rule) {
    var cell = (rule.cells || {}).signed || {};
    if (cell.word === 'stale') { stale += 1; }
    if (!cell.signer) { return; }
    if (!byWho[cell.signer]) { byWho[cell.signer] = ''; names.push(cell.signer); }
    if (newer(cell.at, byWho[cell.signer])) { byWho[cell.signer] = cell.at; }
  });
  var out = names.sort().map(function (who) { return who + ' \u00b7 ' + when(byWho[who]); });
  if (!out.length) { out.push('Nobody has signed a rule here.'); }
  if (stale) { out.push(stale + ' ' + WORDS.stale); }
  return out;
}

/* The newest record this spec has, linked to the file on the git host. Which
   platform found what is on the passed cell row above it. */
function recordLine(feature) {
  var record = (feature.rollup || {}).latest_record || feature.latest_record;
  if (!record) { return '<span class="mono muted">\u2014</span>'; }
  return hostLink(record.path, (record.label || 'local') + ' \u00b7 '
    + ageText(record.timestamp).text);
}

/* A link to the file on the git host, when the payload names a remote this
   page knows how to address. Anything else stays plain text. */
function hostLink(path, text) {
  var base = webRemote();
  var label = esc(text || path);
  if (!base || !path) { return '<span class="mono">' + label + '</span>'; }
  return '<a class="mono" href="' + esc(base + '/blob/'
    + (DATA.commit || 'HEAD') + '/' + path) + '">' + label + '</a>';
}

function webRemote() {
  var remote = DATA && DATA.remote_url;
  if (!remote) { return null; }
  remote = String(remote).replace(/\.git$/, '')
    .replace(/^git@([^:]+):/, 'https://$1/');
  return remote.indexOf('github.com') >= 0 ? remote : null;
}

/* The first design file a spec names, when it names one file rather than a
   pattern: a pattern cannot be resolved without reading the directory, which
   a page opened from disk cannot do. */
function designThumb(feature) {
  var files = (feature.source_globs || []).concat(
    feature.source_path ? [feature.source_path] : []);
  for (var i = 0; i < files.length; i++) {
    var file = String(files[i]);
    if (!/[*?\[]/.test(file) && /\.(png|jpg|jpeg|svg|webp)$/i.test(file)) {
      return '<img class="thumb" src="' + esc(file) + '" alt="'
        + esc(feature.name + ' design') + '" onerror="this.remove()">';
    }
  }
  return '';
}

function ageText(iso) {
  var then = Date.parse(iso || '');
  if (!then) { return {text: 'age unknown', stale: true}; }
  var seconds = Math.max(0, (Date.now() - then) / 1000);
  if (seconds < 90) { return {text: 'less than a minute old', stale: false}; }
  if (seconds < 5400) {
    return {text: Math.round(seconds / 60) + ' minutes old', stale: false};
  }
  if (seconds < 172800) {
    return {text: Math.round(seconds / 3600) + ' hours old', stale: true};
  }
  return {text: Math.round(seconds / 86400) + ' days old', stale: true};
}

/* The date part of an ISO stamp, where a whole day is precise enough. */
function when(iso) { return String(iso || '').slice(0, 10) || 'date unknown'; }

/* One cell of one rule, or null where the gate puts that level above the
   project: the key is missing, not empty. */
function cellOf(rule, name) {
  return (rule.cells || {})[name] || null;
}

function cellWord(rule, name) {
  return (cellOf(rule, name) || {}).word || null;
}

function featureNamed(name) {
  var found = null;
  (DATA.features || []).forEach(function (f) {
    if (f.name === name) { found = f; }
  });
  return found;
}

/* --- chrome and router ------------------------------------------------ */

/* How old the data is, and the tone that age reads in. One function, so the
   minute tick and a full render agree on the threshold. */
function ageLine() {
  var age = ageText(DATA && DATA.generated_at);
  return {hue: age.stale ? 'warn' : 'pass', text: 'Data: ' + age.text
    + (age.stale ? ' — run purlin:status to refresh' : '')};
}

function topBar() {
  var line = ageLine();
  var gate = DATA && DATA.gate ? DATA.gate.gate : null;
  return '<header class="topbar"><span class="brand"><img id="brand-mark" src="'
    + logoSrc() + '" alt="Purlin"><span>purlin</span></span>'
    + '<button class="btn fresh" data-act="reload" style="color:var(--state-'
    + line.hue + ')"><span class="dot"></span><span class="age">'
    + esc(line.text) + '</span></button><span class="spacer"></span>'
    + (gate ? tag('gate: ' + gate, true) : '')
    + (DATA && DATA.commit
       ? '<span class="tag plain" title="The commit this data was generated at">at '
         + esc(String(DATA.commit).slice(0, 7)) + '</span>' : '')
    + themeButton() + '</header>';
}

/* The review list is a question for a person, and under `passed` nothing
   asks one, so the tab is absent rather than empty. */
function tabs() {
  var open = VIEW.screen;
  var items = [['board', 'Board']];
  if (level('strong')) {
    items.push(['review', 'Review list (' + (DATA.review_list || []).length + ')']);
  }
  if (VIEW.rule) { items.push(['rule', VIEW.feature + ' ' + VIEW.rule]); }
  return '<nav class="tabs">' + items.map(function (item) {
    return '<button data-act="nav" data-screen="' + item[0] + '"'
      + (open === item[0] ? ' aria-current="page"' : '') + '>'
      + esc(item[1]) + '</button>';
  }).join('') + '</nav>';
}

function notices() {
  var lines = DATA.dirty
    ? ['The working tree has uncommitted changes, so what is on this board is '
       + 'not what a commit would carry.'] : [];
  (DATA.warnings || []).forEach(function (warning) { lines.push(warning); });
  return lines.map(function (line) {
    return '<div class="notice"><span class="dot" '
      + 'style="color:var(--state-warn)"></span>' + esc(line) + '</div>';
  }).join('');
}

function render() {
  var app = document.getElementById('app');
  if (!DATA) {
    app.innerHTML = '<div class="wrap"><div class="empty">No board data yet. '
      + 'Run purlin:status to write .purlin/report-data.js, then reload this '
      + 'page.</div></div>';
    return;
  }
  if (DATA.schema_version !== SCHEMA) {
    app.innerHTML = topBar() + '<div class="wrap"><div class="notice">'
      + esc('This data was written for schema ' + DATA.schema_version
        + ' and this page reads schema ' + SCHEMA + '. Run purlin:status to '
        + 'write it again.') + '</div></div>';
    return;
  }
  if (VIEW.screen === 'review' && !level('strong')) { VIEW.screen = 'board'; }
  /* The notices are about the tree the whole payload came from, so the board
     carries them once rather than every screen repeating them. */
  var body = VIEW.screen === 'rule' ? renderRule()
    : VIEW.screen === 'review' ? renderReview()
    : notices() + renderBoard();
  app.innerHTML = topBar() + tabs() + '<div class="wrap">' + body + '</div>';
}

function onClick(event) {
  var node = event.target;
  while (node && node !== document && !node.getAttribute('data-act')) {
    node = node.parentNode;
  }
  if (!node || node === document) { return; }
  var act = node.getAttribute('data-act');
  if (act === 'theme') { toggleTheme(); }
  else if (act === 'reload') { reloadPage(); return; }
  else if (act === 'nav') { VIEW.screen = node.getAttribute('data-screen'); }
  else if (act === 'close') {
    VIEW.screen = node.getAttribute('data-screen') || 'board';
    VIEW.rule = VIEW.feature = null;
  } else if (act === 'filter') {
    var id = node.getAttribute('data-filter');
    VIEW.filters[id] = !VIEW.filters[id];
  } else if (act === 'group') {
    var group = node.getAttribute('data-group');
    VIEW.groups[group] = VIEW.groups[group] === false;
  } else if (act === 'feature') {
    var name = node.getAttribute('data-feature');
    VIEW.features[name] = !VIEW.features[name];
  } else if (act === 'rule') {
    VIEW.from = VIEW.screen === 'review' ? 'review' : 'board';
    VIEW.feature = node.getAttribute('data-feature');
    VIEW.rule = node.getAttribute('data-rule');
    VIEW.screen = 'rule';
  }
  render();
}

/* --- coming back to the tab ------------------------------------------- */

/* The screen and the open rule ride across a reload, the way the theme rides
   across one, so a refresh puts the reader back where they were. Every
   storage call is guarded: a browser may refuse the whole store. */
function restoreView() {
  var saved = null;
  try { saved = sessionStorage.getItem('purlin-view'); } catch (e) {}
  try { sessionStorage.removeItem('purlin-view'); } catch (e) {}
  try {
    var value = JSON.parse(saved);
    if (value && typeof value === 'object') { VIEW = value; }
  } catch (e) {}
}

function reloadPage() {
  try { sessionStorage.setItem('purlin-view', JSON.stringify(VIEW)); }
  catch (e) {}
  location.reload();
}

/* The stamp does not move, but the clock does, so the top bar recomputes the
   age every 60 seconds and rewrites that text alone. Nothing is read from
   disk: the board below it is untouched. */
function tickAge() {
  var node = DATA && document.querySelector('.topbar .fresh');
  var text = node && node.querySelector('.age');
  if (!text) { return; }
  var line = ageLine();
  node.style.color = 'var(--state-' + line.hue + ')';
  text.textContent = line.text;
}

/* At most one reload per stamp: when the data file has not moved, the reload
   would show the same board again, so the page asks once and then waits for
   something new to arrive. */
function refreshIfStale() {
  var then = Date.parse((DATA && DATA.generated_at) || '');
  if (!then || (Date.now() - then) / 1000 <= REFRESH_AFTER) { return; }
  var stamp = String(DATA.generated_at);
  var last = null;
  try { last = sessionStorage.getItem('purlin-reloaded'); } catch (e) {}
  if (last !== stamp) {
    try { sessionStorage.setItem('purlin-reloaded', stamp); } catch (e) {}
    reloadPage();
  }
}

restoreTheme();
restoreView();
document.addEventListener('visibilitychange', function () {
  if (document.visibilityState === 'visible') { refreshIfStale(); }
});
window.addEventListener('focus', refreshIfStale);
setInterval(tickAge, REFRESH_AFTER * 1000);
document.getElementById('app').addEventListener('click', onClick);
loadData(function (payload) {
  DATA = payload;
  render();
});
