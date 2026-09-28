import os, sys
from playwright.sync_api import sync_playwright
S = os.path.dirname(os.path.abspath(__file__))
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1920, 'height': 1080})
    for sid in ('touches', 'passed', 'strong', 'signed', 'remote', 'regulated'):
        body = open(os.path.join(S, 'deck/project/slides/%s.html' % sid), encoding='utf-8').read()
        pg.set_content('<html><body style="margin:0"><style>*{margin:0;box-sizing:border-box}section{position:relative;width:1920px;height:1080px;overflow:hidden}aside{display:none}</style>%s</body></html>' % body)
        r = pg.evaluate("""() => { const s=document.querySelector('section'); const kids=[...s.children].filter(c=>getComputedStyle(c).position!=='absolute'&&c.tagName!=='ASIDE'); const last=kids[kids.length-1].getBoundingClientRect(); const foot=[...s.children].find(c=>getComputedStyle(c).position==='absolute').getBoundingClientRect(); return {contentBottom: Math.round(last.bottom), footerTop: Math.round(foot.top), scrollH: s.scrollHeight, spacer: Math.round(kids[2].getBoundingClientRect().height)} }""")
        pg.screenshot(path=os.path.join(S, 'slide-%s.png' % sid))
        print(sid, r)
    b.close()
