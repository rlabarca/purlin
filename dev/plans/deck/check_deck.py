import json, os
from playwright.sync_api import sync_playwright
S = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('DECK_ROOT') or os.path.join(S, 'deck', 'project')
OUT = os.environ.get('DECK_SHOTS') or S
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1920, 'height': 1080})
    for sid in json.load(open(os.path.join(ROOT, 'deck.json')))['order']:
        body = open(os.path.join(ROOT, 'slides/%s.html' % sid), encoding='utf-8').read()
        pg.set_content('<html><body style="margin:0"><style>*{margin:0;box-sizing:border-box}section{position:relative;width:1920px;height:1080px;overflow:hidden}aside{display:none}</style>%s</body></html>' % body)
        r = pg.evaluate("""() => { const s=document.querySelector('section'); const kids=[...s.children].filter(c=>c.tagName!=='ASIDE'&&getComputedStyle(c).position!=='absolute'); const last=kids[kids.length-1].getBoundingClientRect(); const spacer=kids.find(c=>c.tagName==='DIV'&&!c.children.length); return {contentBottom: Math.round(last.bottom), limit: 920, scrollH: s.scrollHeight, spacer: Math.round(spacer.getBoundingClientRect().height)} }""")
        pg.screenshot(path=os.path.join(OUT, 'slide-%s.png' % sid))
        print(sid, r)
    b.close()
