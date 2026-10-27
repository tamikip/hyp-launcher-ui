"""验证 chip 的两态：常态白底、悬停露出灰底，且不会滑空。"""

import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"F:\新建文件夹\hoyo-launcher-clone\reference\renders\download"


def probe(pg, tag):
    return pg.evaluate("""() => {
      const c = document.querySelector('.chip');
      if (!c) return null;
      const r = c.getBoundingClientRect();
      const imgs = [...c.querySelectorAll('img')].map(i => {
        const ir = i.getBoundingClientRect();
        return { src: i.getAttribute('src').split('/').pop(),
                 top: Math.round(ir.top - r.top), h: Math.round(ir.height),
                 shown: ir.bottom > r.top + 1 && ir.top < r.bottom - 1 };
      });
      return { chip: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
               imgs };
    }""")


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:8899/", wait_until="load")
    pg.wait_for_timeout(2200)

    print("常态:", probe(pg, "idle"))
    pg.locator(".chip").screenshot(path=OUT + "/chip-normal.png")

    pg.hover(".chip")
    pg.wait_for_timeout(500)
    print("悬停:", probe(pg, "hover"))
    pg.locator(".chip").screenshot(path=OUT + "/chip-hover.png")

    if errs:
        print("错误:", errs[-4:])
    b.close()
