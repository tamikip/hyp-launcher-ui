"""打开设置弹窗并逐个分类截图。

用法: python render_settings.py <页面URL> <输出前缀> [分类key...]
例:   python render_settings.py http://127.0.0.1:8899/ ref/renders/hoyo-set
"""

import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1]
PREFIX = sys.argv[2]
ONLY = sys.argv[3:]

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
    msgs = []
    pg.on("console", lambda m: msgs.append(f"{m.type}: {m.text}"))
    pg.on("pageerror", lambda e: msgs.append(f"pageerror: {e}"))
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(2200)

    pg.evaluate("() => window.hoyoApp.openSettings()")
    pg.wait_for_timeout(600)

    info = pg.evaluate("""() => {
      const d = document.getElementById('setDialog');
      if (!d) return { ok:false };
      const r = d.getBoundingClientRect();
      const menu = d.querySelector('.set-menu').getBoundingClientRect();
      const tabs = [...d.querySelectorAll('.set-tab')].map(t => t.textContent);
      return { ok:true, rect:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)],
               menuW: Math.round(menu.width), tabs };
    }""")
    print("弹窗:", info)

    if not info.get("ok"):
        print("设置弹窗没打开！控制台:")
        for m in msgs[-12:]:
            print("   ", m)
        b.close()
        sys.exit(1)

    names = info["tabs"]
    for i, nm in enumerate(names):
        if ONLY and nm not in ONLY:
            continue
        pg.evaluate(f"() => document.querySelectorAll('.set-tab')[{i}].click()")
        pg.wait_for_timeout(320)
        f = f"{PREFIX}-{i}-{nm}.png"
        pg.screenshot(path=f)
        print("  已保存", f)

    # 整页（弹窗 + 背景）也来一张
    pg.evaluate("() => document.querySelectorAll('.set-tab')[0].click()")
    pg.wait_for_timeout(320)
    pg.screenshot(path=f"{PREFIX}-full.png")
    print("  已保存", f"{PREFIX}-full.png")

    if msgs:
        print("控制台输出:")
        for m in msgs[-10:]:
            print("   ", m)
    b.close()
