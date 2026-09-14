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
var SCHEMA = 4;
/* The data file is rewritten seconds after a tool call changed a spec, a
   record or an approval, and a tab left open would never notice. Coming back
   to the tab reloads it when what it holds is older than this. */
var REFRESH_AFTER = 60;
var STATES = ['Drafted', 'Proof ready', 'Tested', 'Recorded', 'Reviewed',
              'Approved', 'Stale'];
var TONES = {'Drafted': 'idle', 'Proof ready': 'warn', 'Tested': 'warn',
             'Recorded': 'neutral', 'Reviewed': 'neutral',
             'Approved': 'pass', 'Stale': 'fail'};
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

/* --- marks the screens share ----------------------------------------- */

function esc(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
    return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
            "'": '&#39;'}[c];
  });
}

function tone(state) { return TONES[state] || 'idle'; }

function pill(state) {
  var solid = state === 'Approved' ? ' solid' : '';
  return '<span class="pill' + solid + '" style="color:var(--state-'
    + tone(state) + ')"><b>' + esc(String(state).toUpperCase())
    + '</b></span>';
}

function tag(text, plain) {
  return '<span class="tag' + (plain ? ' plain' : '') + '">' + esc(text)
    + '</span>';
}

/* A risk tag carries its level in the border: high in the fail hue, medium
   in the warn hue, low muted. The text stays the primary ink. */
function riskTag(risk) {
  var level = risk === 'high' || risk === 'medium' ? risk : 'low';
  return '<span class="tag risk-' + level + '">' + esc(risk || 'low')
    + '</span>';
}

function coverage(covered, total) {
  var pct = total ? Math.round((covered / total) * 100) : 0;
  var hue = pct === 100 ? 'pass' : pct >= 60 ? 'warn' : 'fail';
  return '<span class="cov" style="color:var(--state-' + hue + ')"><b>'
    + covered + '/' + total + '</b><i><span style="width:' + pct
    + '%"></span></i></span>';
}

/* An integer percent, or n/a when nothing measured it. */
function strength(value) {
  if (value == null) { return '<span class="mono muted">n/a</span>'; }
  var hue = value >= 80 ? 'pass' : value >= 50 ? 'warn' : 'fail';
  return '<span class="mono" style="color:var(--state-' + hue + ')">'
    + Math.round(value) + '%</span>';
}

/* Every record a spec has, one per operating system, newest of each. The
   payload keys them by operating system and gives `""` to a record written
   without one. */
function recordsFor(feature) {
  var byOs = (DATA.records || {})[feature.name] || {};
  return Object.keys(byOs).sort().map(function (key) { return byOs[key]; });
}

/* One small box per operating system, green when that system's newest record
   passed, red when it failed, grey when no record exists. A record's
   existence is not its result, so the colour is the result; who wrote it and
   when sit in the tooltip. */
var OS_BOXES = [['linux', 'linux'], ['macos', 'mac'], ['windows', 'win']];

function newestByOs(feature) {
  var byOs = {};
  recordsFor(feature).forEach(function (record) {
    var os = record.os || '';
    if (!byOs[os] || (record.timestamp || '') > (byOs[os].timestamp || '')) {
      byOs[os] = record;
    }
  });
  return byOs;
}

function osBox(os, short, record) {
  if (!record) {
    return '<span class="os none" title="' + esc(os) + ': no record">'
      + esc(short) + '</span>';
  }
  var tone = record.result === 'fail' ? 'fail' : 'pass';
  var who = record.label || 'local';
  return '<span class="os ' + tone + '" title="' + esc(os + ': ' + who + ' '
    + (tone === 'fail' ? 'failed' : 'passed') + ' at ' + (record.timestamp || '')
    + ' · ' + (record.path || '')) + '">' + esc(short) + '</span>';
}

function recordCell(feature) {
  var byOs = newestByOs(feature);
  return OS_BOXES.map(function (pair) {
    return osBox(pair[0], pair[1], byOs[pair[0]]);
  }).join('');
}

/* The same boxes on the rule screen, each beside a link to the file it
   names, so a record stays addressable on the git host. */
function recordLine(feature) {
  var byOs = newestByOs(feature);
  var any = false;
  var out = OS_BOXES.map(function (pair) {
    var record = byOs[pair[0]];
    if (record) { any = true; }
    return osBox(pair[0], pair[1], record)
      + (record ? ' ' + hostLink(record.path, record.timestamp || record.path) : '');
  }).join(' ');
  return any ? out : '<span class="mono muted">none</span>';
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
    if (/[*?\[]/.test(file)) { continue; }
    if (/\.(png|jpg|jpeg|svg|webp)$/i.test(file)) {
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

/* Columns appear as their artifacts exist, so each of these asks the payload
   rather than the gate: a project that has never recorded shows no record
   column whatever its gate says. */
function eachRule(visit) {
  (DATA.features || []).forEach(function (feature) {
    (feature.rules || []).forEach(function (rule) { visit(rule, feature); });
  });
}

/* Every untagged rule reads as low risk, so what says a project tags risk at
   all is a rule that reads as something else. */
function hasRisks() {
  var tagged = false;
  eachRule(function (rule) {
    if ((rule.risk || 'low') !== 'low') { tagged = true; }
  });
  return tagged;
}

function hasRecords() {
  return (DATA.features || []).some(function (f) { return !!f.latest_record; });
}

function hasApprovals() {
  return (DATA.features || []).some(function (f) {
    return (f.approvals || []).length > 0;
  });
}

function featureNamed(name) {
  var found = null;
  (DATA.features || []).forEach(function (feature) {
    if (feature.name === name) { found = feature; }
  });
  return found;
}

/* --- chrome and router ------------------------------------------------ */

/* How old the data is, and the tone that age reads in. One function, so the
   minute tick and a full render agree on the threshold. */
function ageLine() {
  var age = ageText(DATA && DATA.generated_at);
  return {hue: age.stale ? 'warn' : 'pass',
          text: 'Data: ' + age.text
            + (age.stale ? ' — run purlin:status to refresh' : '')};
}

function topBar() {
  var line = ageLine();
  var gate = DATA && DATA.gate ? DATA.gate.gate : null;
  return '<header class="topbar"><span class="brand"><img id="brand-mark" src="'
    + logoSrc() + '" alt="Purlin"><span>purlin</span></span>'
    + '<button class="btn fresh" data-act="reload" '
    + 'style="color:var(--state-' + line.hue + ')">'
    + '<span class="dot"></span><span class="age">' + esc(line.text)
    + '</span></button>'
    + '<span class="spacer"></span>'
    + (gate ? tag('gate: ' + gate, true) : '')
    + (DATA && DATA.commit
       ? '<span class="tag plain" title="The commit this data was generated at">at '
         + esc(String(DATA.commit).slice(0, 7)) + '</span>' : '')
    + themeButton() + '</header>';
}

function tabs() {
  var open = VIEW.screen;
  var items = [
    ['board', 'Board'],
    ['review', 'Review list (' + (DATA.review_list || []).length + ')']];
  if (VIEW.rule) { items.push(['rule', VIEW.feature + ' ' + VIEW.rule]); }
  return '<nav class="tabs">' + items.map(function (item) {
    return '<button data-act="nav" data-screen="' + item[0] + '"'
      + (open === item[0] ? ' aria-current="page"' : '') + '>'
      + esc(item[1]) + '</button>';
  }).join('') + '</nav>';
}

function notices() {
  var lines = [];
  if (DATA.dirty) {
    lines.push('The working tree has uncommitted changes, so what is on this '
      + 'board is not what a commit would carry.');
  }
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
        + ' and this page reads schema ' + SCHEMA
        + '. Run purlin:status to write it again.') + '</div></div>';
    return;
  }
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
    VIEW.rule = null;
    VIEW.feature = null;
  }
  else if (act === 'filter') {
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
  if (!saved) { return; }
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
  if (!DATA) { return; }
  var node = document.querySelector('.topbar .fresh');
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
  if (last === stamp) { return; }
  try { sessionStorage.setItem('purlin-reloaded', stamp); } catch (e) {}
  reloadPage();
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
