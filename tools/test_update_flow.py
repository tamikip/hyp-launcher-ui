"""测试「已安装 + 有可用更新」的更新流程。

点主按钮不应触发下载（那是"开始游戏"），要点副行的「立即更新」。

用法: python test_update_flow.py [URL] [key]
"""

import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8899/?game=c07_cn"
KEY = sys.argv[2] if len(sys.argv) > 2 else "c07_cn"
OUT = r"F:\新建文件夹\hoyo-launcher-clone\reference\renders\download"


def shot(pg, n):
    pg.screenshot(path=f"{OUT}/updflow-{n}.png")
    print("   已保存", f"updflow-{n}.png")


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(2200)

    st = pg.evaluate("""() => {
      const b = document.querySelector('.btn-primary');
      return { label: b.querySelector('.label').textContent,
               action: b.getAttribute('data-action'),
               sub: document.querySelector('.cta-sub').innerHTML,
               hasUpdate: !!window.HOYO_CONFIG.games['%s'].updateTo };
    }""" % KEY)
    print("  初始:", st)
    shot(pg, "0-available")

    # 主按钮：已安装应保持"开始游戏"，不触发下载
    pg.click(".btn-primary")
    pg.wait_for_timeout(500)
    after = pg.evaluate("() => Object.keys(window.hoyoApp.tasks).length")
    print("  点主按钮后的任务数（应为 0）:", after)

    # 点「立即更新」
    pg.evaluate("() => document.querySelector('.cta-sub a[data-act=update]').click()")
    pg.wait_for_timeout(600)
    t = pg.evaluate("""() => { const t = window.hoyoApp.tasks['%s'];
      return t ? { kind: t.kind, phase: t.phase, total: Math.round(t.total/1048576) } : null; }""" % KEY)
    print("  点立即更新后:", t)
    shot(pg, "1-updating")

    # 推到 100% 走完
    pg.evaluate("""() => { const t = window.hoyoApp.tasks['%s'];
      if (t) { t.done = t.total; t.percent = 100; } }""" % KEY)
    pg.wait_for_timeout(900)
    for _ in range(24):
        pg.evaluate("""() => { const t = window.hoyoApp.tasks['%s'];
          if (t && t.phaseLeft) t.phaseLeft = 0.01; }""" % KEY)
        pg.wait_for_timeout(400)
        cur = pg.evaluate("() => { const t = window.hoyoApp.tasks['%s']; return t ? t.phase : 'gone'; }" % KEY)
        if cur == "gone":
            break
    pg.wait_for_timeout(600)
    fin = pg.evaluate("""() => {
      const b = document.querySelector('.btn-primary');
      return { label: b.querySelector('.label').textContent,
               action: b.getAttribute('data-action'),
               sub: document.querySelector('.cta-sub').innerHTML,
               updateTo: window.HOYO_CONFIG.games['%s'].updateTo }; }""" % KEY)
    print("  更新完成后:", fin)
    shot(pg, "2-done")

    if errs:
        print("  页面错误:", errs[-5:])
    b.close()
