"""跑一遍下载/更新流程，在几个关键状态各截一张图。

用法: python test_download.py <URL> <输出前缀> [key]

为了快速跑到各阶段，测试里直接改任务的 done 值跳进度；
真实速度由 task.base 控制（约 30 秒跑完一次完整下载）。
"""

import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1]
PREFIX = sys.argv[2]
KEY = sys.argv[3] if len(sys.argv) > 3 else "c01_cn"


def shot(pg, name):
    f = f"{PREFIX}-{name}.png"
    pg.screenshot(path=f)
    print("   已保存", f)


def jump(pg, frac):
    """把进度直接推到某个比例。"""
    pg.evaluate(
        "() => { const t = window.hoyoApp.tasks['%s']; if (t) "
        "{ t.done = t.total * %f; t.percent = %f; } }" % (KEY, frac, frac * 100))


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(f"{m.type}: {m.text}")
          if m.type == "error" else None)

    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(2200)
    shot(pg, "0-idle")

    pg.click(".btn-primary")
    pg.wait_for_timeout(400)
    st = pg.evaluate("""() => {
      const b = document.querySelector('.btn-primary');
      const t = window.hoyoApp.tasks['%s'];
      return { busy: b.classList.contains('is-busy'), phase: t && t.phase,
               label: b.querySelector('.label').textContent,
               ring: getComputedStyle(document.querySelector('.ring')).display };
    }""" % KEY)
    print("  点按钮后:", st)
    if not st.get("busy"):
        for e in errs[-8:]:
            print("    ", e)
        b.close()
        sys.exit(1)

    jump(pg, 0.42)
    pg.wait_for_timeout(700)
    shot(pg, "1-downloading")

    pg.evaluate("() => window.hoyoApp.taskPause('%s')" % KEY)
    pg.wait_for_timeout(500)
    print("  暂停后:", pg.evaluate("""() => {
      const b = document.querySelector('.btn-primary');
      return { paused: b.classList.contains('is-paused'),
               label: b.querySelector('.label').textContent,
               pct: b.querySelector('.ring .pct').textContent };
    }"""))
    shot(pg, "2-paused")

    pg.evaluate("() => window.hoyoApp.taskResume('%s')" % KEY)
    jump(pg, 0.93)
    pg.wait_for_timeout(600)
    shot(pg, "3-near-done")

    # 推到 100% → 进入校验/解压/安装
    jump(pg, 1.0)
    pg.wait_for_timeout(900)
    st2 = pg.evaluate("() => { const t = window.hoyoApp.tasks['%s']; return t && t.phase; }" % KEY)
    print("  100% 后阶段:", st2)
    shot(pg, "4-verifying")

    # 用 taskStart 之外的路径无法跳阶段，这里直接把计时压到 0 逐个推进
    for _ in range(24):
        pg.evaluate("() => { const t = window.hoyoApp.tasks['%s']; if (t && t.phaseLeft) t.phaseLeft = 0.01; }" % KEY)
        pg.wait_for_timeout(400)
        cur = pg.evaluate("() => { const t = window.hoyoApp.tasks['%s']; return t ? t.phase : 'gone'; }" % KEY)
        if cur == "gone":
            break
    pg.wait_for_timeout(500)
    shot(pg, "5-installed")

    fin = pg.evaluate("""() => {
      const b = document.querySelector('.btn-primary');
      return { busy: b.classList.contains('is-busy'),
               label: b.querySelector('.label').textContent,
               action: b.getAttribute('data-action'),
               tasks: Object.keys(window.hoyoApp.tasks).length,
               installed: !!(window.HOYO_CONFIG.games['%s'] || {}).installed };
    }""" % KEY)
    print("  流程结束:", fin)

    if errs:
        print("  页面错误:")
        for e in errs[-10:]:
            print("    ", e)
    b.close()
