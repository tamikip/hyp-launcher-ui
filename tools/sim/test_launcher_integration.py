"""验证：启动器的「获取游戏」是否真的走分块增量下载。

用法: python test_launcher_integration.py
"""

import sys

from playwright.sync_api import sync_playwright

PAGE = "http://127.0.0.1:8899/"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    reqs = []
    pg.on("request", lambda r: reqs.append(r.url) if "/chunks/" in r.url else None)

    pg.goto(PAGE, wait_until="load")
    pg.wait_for_timeout(2000)
    # config.js 里 updater 默认关（米哈游界面要和官方行为一致），
    # 这里运行时打开，专门验证「界面驱动真实分块下载」这条链路
    pg.evaluate("() => { window.HOYO_CONFIG.updater.enabled = true; }")
    print("初始按钮:", pg.evaluate("() => document.querySelector('.label').textContent"))

    pg.click(".btn-primary")
    pg.wait_for_timeout(1500)

    st = pg.evaluate("""() => {
      const t = window.hoyoApp.tasks['c01_cn'];
      if (!t) return { none: true };
      return { phase: t.phase, real: !!t.real,
               plan: t.plan ? { need: t.plan.need.length,
                                needMB: +(t.plan.needBytes/1048576).toFixed(2),
                                totalMB: +(t.plan.totalBytes/1048576).toFixed(2),
                                delete: t.plan.deleteFiles } : null };
    }""")
    print("点击后:", st)

    phase = None
    for _ in range(60):
        pg.wait_for_timeout(500)
        phase = pg.evaluate(
            "() => { const t = window.hoyoApp.tasks['c01_cn']; return t ? t.phase : 'gone'; }")
        if phase in ("gone", "failed"):
            break
    print("结束阶段:", phase)
    err = pg.evaluate(
        "() => { const t = window.hoyoApp.tasks['c01_cn']; return t ? (t.error || null) : null; }")
    if err:
        print("失败原因:", err)
    print("实际请求的分块数:", len(reqs))
    if reqs:
        print("示例 URL:", reqs[0])

    print("按钮:", pg.evaluate("() => document.querySelector('.label').textContent"),
          " installed:", pg.evaluate("() => window.HOYO_CONFIG.games['c01_cn'].installed"))

    if errs:
        print("页面错误:")
        for e in errs[-6:]:
            print("  ", e)
    b.close()
