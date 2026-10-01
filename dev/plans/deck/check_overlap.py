import json, os
from playwright.sync_api import sync_playwright
ROOT=os.environ['DECK_ROOT']
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1920,'height':1080})
    for sid in json.load(open(os.path.join(ROOT,'deck.json')))['order']:
        body=open(os.path.join(ROOT,'slides/%s.html'%sid)).read()
        pg.set_content('<html><body style="margin:0"><style>*{margin:0;box-sizing:border-box}section{position:relative;width:1920px;height:1080px;overflow:hidden}aside{display:none}</style>%s</body></html>'%body)
        r=pg.evaluate("""()=>{const s=document.querySelector('section');
          const abs=[...s.children].filter(c=>getComputedStyle(c).position==='absolute').map(c=>c.getBoundingClientRect());
          const txt=[...s.querySelectorAll('h2,p')].filter(e=>getComputedStyle(e).position!=='absolute' && !e.closest('[style*="position:absolute"]'));
          const hits=[];
          for(const e of txt){ // measure the text itself, not its box
            const rg=document.createRange(); rg.selectNodeContents(e);
            for(const rc of rg.getClientRects()) for(const a of abs){
              if(rc.right>a.left && rc.left<a.right && rc.bottom>a.top && rc.top<a.bottom) hits.push(e.textContent.slice(0,40));}}
          const h=s.querySelector('h2').getBoundingClientRect();
          const labels=[...s.querySelectorAll('p')].filter(p=>p.style.fontFamily.includes('Courier') && p.style.width).map(p=>[Math.round(p.getBoundingClientRect().left),getComputedStyle(p).fontSize]);
          return {hits:[...new Set(hits)], h2:[Math.round(h.left),Math.round(h.top),getComputedStyle(s.querySelector('h2')).fontSize], labels:[...new Set(labels.map(l=>l.join('@')))]};}""")
        print(sid, r)
    b.close()
