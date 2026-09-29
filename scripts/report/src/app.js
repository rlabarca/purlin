/* The shell: the data file, the chrome, the router and the marks the two
   screens share.

   The data file declares a const, and a const cannot be declared twice in one
   window, so it is read inside a throwaway iframe that posts the value back.
   srcdoc inherits this page's base URL and origin, so .purlin/report-data.js
   resolves exactly as a script tag here would, on file:// as well, where
   fetch is blocked. The query string defeats the file:// cache. */

var DATA = null;
var VIEW = {screen: 'board', feature: null, rule: null,
            features: {}, groups: {}, filter: null, proofs: {}};
var SCHEMA = 10;
/* The data file is rewritten when `purlin:status`, `purlin:test`,
   `purlin:audit` or `purlin:sign` finishes, and a tab left open would never
   notice. Coming back to the tab reloads it when what it holds is older than
   this. */
var REFRESH_AFTER = 60;

/* The three steps, lowest first. The project's gate names the
   highest step that exists, and every cell, box and column above it
   is absent rather than empty: a board that asks a question its project has
   not opted into reads as a project falling short. */
var GATE_LEVELS = ['passed', 'strong', 'signed'];

/* The step boxes, one per step the gate reaches, each counting the rules
   that reached it: the payload's `summary.steps`, where each step contains
   the next. The step `passed` reads `Passing` on a box, because it counts
   rules whose tests pass now. From `strong` up, where every rule needs a
   proof, one more box counts the rules that have none: the kind `no_proof`
   the payload gives a rule. */
var STEP_LABELS = {passed: 'Passing', strong: 'Strong', signed: 'Signed'};
var NO_PROOF = 'No proof';

/* The board's six column headings and the words its cells append, in one
   place. `scripts/mcp/purlin/board.py` renders the same six columns for
   `purlin:status`, so these are its
   `COLUMNS` and its cell words: a string changed there is changed here in
   the same commit. `Proofs` is drawn where `showsProofs` says, as
   `board.shows_proofs` decides it for the status table. The one difference
   is the `Rules` cell: the terminal reads `16 (+6 shared)` and the page
   `16 (+6)`, the page's hover saying what the second number is. */
var COLUMNS = ['Spec', 'Rules', 'Proofs', 'Tests', 'Strong', 'Signed'];

/* The one separator every cell, hover and line puts between two parts, which
   is `board.DOT`. */
var DOT = ' \u00b7 ';
var WORDS = {of: 'of', no_test: 'no test', partial: 'partial',
             failing: 'failing', passed: 'passed', failed: 'failed',
             not_run: 'not run'};

/* Every word a cell can read, and the tone it reads in. A word carries the
   same hue wherever it is drawn, so a pill on the board, a row on the rule
   screen and a proof beneath a rule agree. */
var CELL_TONES = {'passed': 'pass',
  'failed': 'fail', 'no test': 'warn', 'not run': 'warn', 'partial': 'warn',
  'out of date': 'warn', 'strong': 'pass', 'weak': 'warn',
  'waiting': 'neutral',
  'manual test': 'warn', 'not audited': 'idle', 'no proof': 'warn',
  'signed': 'pass', 'unsigned': 'warn'};

var CELL_LABELS = {passed: 'Passed', strong: 'Strong', signed: 'Signed'};


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

/* True when the project's gate is at this step or above it, which is the
   one question that decides whether a cell, a box or a column is drawn at
   all. */
function level(name) {
  return GATE_LEVELS.indexOf(gateName()) >= GATE_LEVELS.indexOf(name);
}

/* Whether the page names proofs at all. They are optional at `passed`, so a
   project there that writes no proof line is shown no `Proofs` column, no
   proofs section and no reason naming them; from `strong` up every rule needs
   one. `board.shows_proofs` answers the same for `purlin:status`. */
function showsProofs() {
  return level('strong') || ((DATA && DATA.summary) || {}).proofs > 0;
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

/* The words a person reads for an operating system, from the payload's
   `os_words`: `Windows`, `macOS` and `Linux/Unix`, and in a small box `Win`,
   `Mac` and `Lin`. A system that is none of the three reads as `linux`. */
function systemWords(os) {
  var words = (DATA && DATA.os_words) || {};
  return words[os] || words.linux || {word: os, short: os};
}

function tag(text, plain) {
  return '<span class="tag' + (plain ? ' plain' : '') + '">' + esc(text) + '</span>';
}

/* Every rule the project holds, each paired with the feature that owns it. */
function everyRule() {
  var out = [];
  (DATA.features || []).forEach(function (feature) {
    ownRules(feature).forEach(function (rule) {
      out.push({feature: feature, rule: rule});
    });
  });
  return out;
}

/* The rule one owner and one id name. A rule is always addressed by the
   spec that owns it and its id together: a feature that proves an anchor's
   rules lists them beside its own, and both carry a `RULE-1`. */
function ruleNamed(owner, id) {
  var feature = featureNamed(owner);
  var found = null;
  (feature ? feature.rules || [] : []).forEach(function (r) {
    if (r.feature === owner && r.id === id) { found = r; }
  });
  return found;
}

/* Several counts in one cell, each labelled with the word it counts and set
   in that word's tone. `24 passed · 2 failing` says what a bare `24 · 2 · 0`
   left the reader to work out from the heading. The first part is always
   drawn, because the column's total is the number the row is about; a later
   part at zero is not, because nothing is waiting there. Each item is
   `[count, word, tone]`, and a word may be empty where the count already
   reads as a sentence (`5 of 24`); a fourth member, where there is one, is
   the part's own hover. The separator rides inside the part it
   introduces, so a cell narrow enough to wrap breaks between parts and never
   leaves a lone dot at the end of a line. */
function counts(items) {
  return '<span class="trio">' + items.filter(function (item, index) {
    return index === 0 || item[0];
  }).map(function (item, index) {
    var hue = index === 0 && !item[0] ? 'idle' : item[2];
    return '<b' + (item[3] ? hover(item[3]) : '')
      + (hue ? ' style="color:var(--state-' + hue + ')"' : '') + '>'
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

/* The rules a feature proves and does not own, by the anchor that owns
   them: `[[anchor, count]]` in the order the payload lists them. They count
   toward the feature and are listed once, under their anchor. */
function sharedBy(feature) {
  var counts = {};
  var order = [];
  (feature.rules || []).forEach(function (r) {
    if (r.label === 'own') { return; }
    if (!(r.feature in counts)) { counts[r.feature] = 0; order.push(r.feature); }
    counts[r.feature] += 1;
  });
  return order.map(function (name) { return [name, counts[name]]; });
}

/* The whole project as one feature, so a tile's hover is its column's hover
   read over every spec rather than a second set of sums. */
function wholeProject() {
  var rules = [];
  var rollup = {};
  var latest = null;
  Object.keys(DATA.summary || {}).forEach(function (key) {
    rollup[key] = DATA.summary[key];
  });
  (DATA.features || []).forEach(function (feature) {
    ownRules(feature).forEach(function (rule) { rules.push(rule); });
    var found = newestRun(feature);
    if (found && (!latest || newer(found.at, latest.at))) { latest = found; }
  });
  return {rules: rules, rollup: rollup, newest: latest};
}

/* The newest section of a spec's evidence in either source: where it sits,
   whose run it was and when, or null where nothing has run. */
function newestRun(feature) {
  if (feature.newest !== undefined) { return feature.newest; }
  var best = null;
  ['local', 'ci'].forEach(function (source) {
    var file = (feature.evidence || {})[source];
    if (!file) { return; }
    Object.keys(file.platforms || {}).forEach(function (os) {
      var section = file.platforms[os];
      if (!best || newer(section.at, best.at)) {
        best = {path: file.path, source: source, at: section.at};
      }
    });
  });
  return best;
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
      return [systemWords(os).word, found.source || 'local',
        ageText(found.at).text].concat(
        [WORDS.passed, WORDS.failed, WORDS.not_run].filter(function (word) {
          return found.words[word];
        }).map(function (word) { return found.words[word] + ' ' + word; }))
        .join(DOT);
    });
}

/* Where the newest audit came from, how old it is, and the strength this
   gate asks for. The strength itself is in the cell beside it. Each rule
   carries its own audit, so the newest of them answers for the spec. */
function auditLines(feature) {
  var newest = null;
  ownRules(feature).forEach(function (rule) {
    var audit = rule.audit;
    if (audit && audit.at && (!newest || newer(audit.at, newest.at))) {
      newest = audit;
    }
  });
  return [newest ? 'audit' + DOT + sourceOf(newest.path) + DOT
      + ageText(newest.at).text
    : 'No audit has read a rule here.',
    'minimum strength ' + minStrength() + '%'];
}

/* The source an evidence file belongs to: the folder it sits in. */
function sourceOf(path) {
  var parts = String(path || '').split('/');
  return parts.length > 1 ? parts[parts.length - 2] : 'local';
}

/* Who has signed a rule here and when their newest signature was written. */
function signerLines(feature) {
  var byWho = {};
  var names = [];
  ownRules(feature).forEach(function (rule) {
    var cell = (rule.cells || {}).signed || {};
    if (cell.word !== 'signed' || !cell.signer) { return; }
    if (!byWho[cell.signer]) { byWho[cell.signer] = ''; names.push(cell.signer); }
    if (newer(cell.at, byWho[cell.signer])) { byWho[cell.signer] = cell.at; }
  });
  var out = names.sort().map(function (who) { return who + DOT + when(byWho[who]); });
  if (!out.length) { out.push('Nobody has signed a rule here.'); }
  return out;
}

/* The evidence file of this spec's newest run, linked to the file on the
   git host. Which platform found what is on the passed cell row above it. */
function runLine(feature) {
  var run = newestRun(feature);
  if (!run) { return '<span class="mono muted">\u2014</span>'; }
  return hostLink(run.path, run.source + DOT + ageText(run.at).text);
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

function ageText(iso) {
  var then = Date.parse(iso || '');
  if (!then) { return {text: 'age unknown', old: true}; }
  var seconds = Math.max(0, (Date.now() - then) / 1000);
  if (seconds < 90) { return {text: 'less than a minute old', old: false}; }
  if (seconds < 5400) {
    return {text: Math.round(seconds / 60) + ' minutes old', old: false};
  }
  if (seconds < 172800) {
    return {text: Math.round(seconds / 3600) + ' hours old', old: true};
  }
  return {text: Math.round(seconds / 86400) + ' days old', old: true};
}

/* The date part of an ISO stamp, where a whole day is precise enough. */
function when(iso) { return String(iso || '').slice(0, 10) || 'date unknown'; }

/* The date and the minute of an ISO stamp, which is UTC wherever it was
   written: `2026-09-12 10:02 UTC`. */
function moment(iso) {
  var text = String(iso || '');
  return text.length >= 16 ? text.slice(0, 10) + ' ' + text.slice(11, 16)
    + ' UTC' : when(iso);
}

/* One cell of one rule, or null where the gate does not reach it: the key
   is missing, not empty. */
function cellOf(rule, name) {
  return (rule.cells || {})[name] || null;
}

function cellWord(rule, name) {
  return (cellOf(rule, name) || {}).word || null;
}

/* The steps a rule has reached, lowest first, as the step boxes count
   them: its tests passed, and where a proof is `@manual` a person has checked
   it by hand; then the audit found it strong; then it is signed. Each step
   contains the next, so a rule that has not reached one has reached none
   above it. */
function reachedSteps(rule) {
  var out = [];
  if (cellWord(rule, 'passed') !== 'passed') { return out; }
  var manual = (rule.proofs || []).some(function (proof) {
    return proof.manual;
  });
  if (manual && !rule.hand_checked) { return out; }
  out.push('passed');
  if (cellWord(rule, 'strong') !== 'strong') { return out; }
  out.push('strong');
  if (cellWord(rule, 'signed') === 'signed') { out.push('signed'); }
  return out;
}

/* Whether a test of the rule failed: its passed cell reads `failed`, or a
   run on one operating system failed it while another passed it. */
function testFailed(rule) {
  var cell = cellOf(rule, 'passed') || {};
  if (cell.word === 'failed') { return true; }
  var platforms = cell.platforms || {};
  return Object.keys(platforms).some(function (os) {
    return platforms[os].word === 'failed';
  });
}

/* The badges a rule's row carries: one per step it has reached, and
   `FAILED` where a test fails. A step not reached draws nothing; why it was
   not reached is read on the rule's own screen. */
function badges(rule) {
  return reachedSteps(rule).map(pill).join('')
    + (testFailed(rule) ? pill('failed') : '');
}

function featureNamed(name) {
  var found = null;
  (DATA.features || []).forEach(function (f) {
    if (f.name === name) { found = f; }
  });
  return found;
}

/* --- chrome and router ------------------------------------------------ */

/* How old the data is, the tone that age reads in, and what the hover says
   to do about it. One function, so the minute tick and a full render agree
   on the threshold. The line carries the age alone; the instruction is the
   hover's. */
function ageLine() {
  var age = ageText(DATA && DATA.generated_at);
  return {hue: age.old ? 'warn' : 'pass', text: 'Data: ' + age.text,
    how: (age.old ? 'This data is old. ' : '')
      + 'To refresh it, type purlin:status in Claude Code. '
      + 'Press here to reload the page.'};
}

/* The tag this commit carries, which is the marker that a version was signed
   off: `purlin:sign` writes `signed/<version>` at the gate `signed` once
   nothing is left to do, and a person pushes it. Below `signed` no tag is ever
   written, so the top bar shows no tag chip at all. The payload's `tag`
   carries the tag's name and the commit it points at, and is null where this
   commit carries none. */
function signedTag() {
  var found = DATA && DATA.tag;
  if (!found || !found.name) { return null; }
  return {name: String(found.name),
          at: found.commit ? String(found.commit).slice(0, 7) : null};
}

function tagChip() {
  var found = signedTag();
  if (!found) {
    return '<span class="tag plain"'
      + hover(['This commit carries no signed tag. purlin:sign writes '
        + 'signed/<version> once nothing is left to do at the gate signed, '
        + 'and a person pushes it.']) + '>no signed tag</span>';
  }
  return '<span class="tag"' + hover(['The signed tag on this commit'
      + (found.at ? DOT + found.at : '')]) + '>'
    + esc(found.name) + '</span>';
}

function topBar() {
  var line = ageLine();
  var gate = DATA && DATA.gate ? DATA.gate.gate : null;
  return '<header class="topbar"><span class="brand"><img id="brand-mark" src="'
    + logoSrc() + '" alt="Purlin"><span>purlin</span></span>'
    + '<button class="btn fresh" data-act="reload"' + hover([line.how])
    + ' style="color:var(--state-'
    + line.hue + ')"><span class="dot"></span><span class="age">'
    + esc(line.text) + '</span></button><span class="spacer"></span>'
    + (gate ? tag('gate: ' + gate, true) : '')
    + (level('signed') ? tagChip() : '')
    + themeButton() + '</header>';
}

/* The board, then the open rule. */
function tabs() {
  var open = VIEW.screen;
  var items = [['board', 'Board']];
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
      + 'style="color:var(--state-warn)"></span><span class="notice-text">'
      + line.split(' ').map(noticeWord).join(' ') + '</span></div>';
  }).join('');
}

/* One word of a notice. A path or a name never breaks inside itself, except
   a path too long for a phone's width, which breaks after a `/` and nowhere
   else, so the page never scrolls sideways. */
function noticeWord(word) {
  if (!/[\/\-._]/.test(word)) { return esc(word); }
  var text = word.length > 36 ? esc(word).replace(/\//g, '/<wbr>') : esc(word);
  return '<span class="nowrap">' + text + '</span>';
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
  if (VIEW.screen !== 'rule') { VIEW.screen = 'board'; }
  /* The notices are about the tree the whole payload came from, so the board
     carries them once rather than every screen repeating them. */
  var body = VIEW.screen === 'rule' ? renderRule()
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
    VIEW.screen = 'board';
    VIEW.rule = VIEW.feature = null;
  } else if (act === 'filter') {
    /* One line of what is left is chosen at a time; choosing it again
       shows every rule. */
    var id = node.getAttribute('data-filter');
    VIEW.filter = VIEW.filter === id ? null : id;
  } else if (act === 'group') {
    var group = node.getAttribute('data-group');
    VIEW.groups[group] = VIEW.groups[group] === false;
  } else if (act === 'feature') {
    var name = node.getAttribute('data-feature');
    VIEW.features[name] = !VIEW.features[name];
    /* A spec opens with every rule's proofs closed. */
    Object.keys(VIEW.proofs).forEach(function (key) {
      if (key.indexOf(name + ' ') === 0) { delete VIEW.proofs[key]; }
    });
  } else if (act === 'proofs') {
    var key = node.getAttribute('data-feature') + ' '
      + node.getAttribute('data-rule');
    VIEW.proofs[key] = !VIEW.proofs[key];
    render();
    /* The page is drawn again, so the button a keyboard pressed takes the
       focus back rather than dropping it on the page. */
    var again = document.querySelector('[data-act="proofs"][data-feature="'
      + CSS.escape(node.getAttribute('data-feature')) + '"][data-rule="'
      + CSS.escape(node.getAttribute('data-rule')) + '"]');
    if (again) { again.focus(); }
    return;
  } else if (act === 'rule') {
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
  /* Every rule's proofs are closed when the page loads. */
  VIEW.proofs = {};
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
  node.title = line.how;
  text.textContent = line.text;
}

/* At most one reload per stamp: when the data file has not moved, the reload
   would show the same board again, so the page asks once and then waits for
   something new to arrive. */
function refreshIfOld() {
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
  if (document.visibilityState === 'visible') { refreshIfOld(); }
});
window.addEventListener('focus', refreshIfOld);
setInterval(tickAge, REFRESH_AFTER * 1000);
document.getElementById('app').addEventListener('click', onClick);
/* A band is a control drawn as a row, so Enter and Space press it as they
   press a button, and the focus comes back to it once the page is drawn. */
document.getElementById('app').addEventListener('keydown', function (event) {
  var group = event.target.getAttribute('data-group');
  if (!group || (event.key !== 'Enter' && event.key !== ' ')) { return; }
  event.preventDefault();
  onClick(event);
  document.querySelector('.group[data-group="' + CSS.escape(group) + '"]').focus();
});
loadData(function (payload) {
  DATA = payload;
  render();
});
