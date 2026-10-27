"""ABC 三类补强的验收测试：逐项触发并截图。

用法: python test_abc.py [URL] [输出前缀]
"""

import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8899/"
PRE = sys.argv[2] if len(sys.argv) > 2 else \
    r"F:\新建文件夹\hoyo-launcher-clone\reference\renders\abc\hoyo"

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}  {detail}")


def shot(pg, n):
    pg.screenshot(path=f"{PRE}-{n}.png")


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)

    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(2000)

    print("\n=== B: 界面模块 ===")

    # 1) 背景切换器
    n = pg.evaluate("() => document.querySelectorAll('#bgDots button').length")
    check("背景切换器圆点", n >= 2, f"{n} 个")
    pg.evaluate("() => document.getElementById('bgSwitch').classList.add('on')")
    pg.wait_for_timeout(300)
    shot(pg, "b1-bgswitch")

    # 2) 区服切换
    n = pg.evaluate("() => !!document.getElementById('srvHost')")
    check("区服切换入口", n)
    pg.evaluate("() => document.querySelector('.srv-btn').click()")
    pg.wait_for_timeout(400)
    n = pg.evaluate("() => document.querySelectorAll('.popup .pop-item').length")
    check("区服下拉弹出", n >= 2, f"{n} 项")
    shot(pg, "b2-server")

    # 3) Tooltip
    pg.evaluate("() => window.hoyoUI.closePopup()")
    pg.hover(".game-icon")
    pg.wait_for_timeout(500)
    tip = pg.evaluate(
        "() => { const t = document.querySelector('.tooltip');"
        "return t && t.classList.contains('on') ? t.textContent : ''; }")
    check("自定义 tooltip", bool(tip), tip)
    shot(pg, "b3-tooltip")

    # 4) 账号弹窗
    pg.evaluate("() => { const b = [...document.querySelectorAll('.social-item')]"
                ".find(x => x.getAttribute('data-tip') === '账号'); if (b) b.click(); }")
    pg.wait_for_timeout(400)
    n = pg.evaluate("() => document.querySelectorAll('.acct-pop .pop-item').length")
    check("账号弹窗", n >= 3, f"{n} 项")
    shot(pg, "b4-account")
    pg.evaluate("() => window.hoyoUI.closePopup()")

    # 5) Toast
    pg.evaluate("() => window.hoyoUI.toast('这是一条提示', { type: 'success' })")
    pg.wait_for_timeout(400)
    n = pg.evaluate("() => document.querySelectorAll('.toast').length")
    check("Toast", n >= 1, f"{n} 条")
    shot(pg, "b5-toast")

    # 6) 背景视频元素
    n = pg.evaluate("() => !!document.getElementById('bgVideo')")
    check("背景视频元素", n)

    # 7) 骨架屏（只显示约 420ms，得轮询抓）
    pg2 = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
    pg2.goto(URL.split("?")[0] + "?page=hub", wait_until="domcontentloaded")
    sk = 0
    for _ in range(40):
        sk = pg2.evaluate("() => document.querySelectorAll('.sk i').length")
        if sk:
            pg2.screenshot(path=f"{PRE}-b6-skeleton.png")
            break
        pg2.wait_for_timeout(30)
    check("Hub 骨架屏", sk >= 1, f"{sk} 条")
    pg2.wait_for_timeout(1400)
    sk2 = pg2.evaluate("() => document.querySelectorAll('.sk i').length")
    check("骨架屏被真内容替换", sk2 == 0, f"剩余 {sk2}")
    pg2.close()

    print("\n=== A: 流程完整性 ===")

    # 8) 预下载
    pg.evaluate("() => window.hoyoApp.taskPreDownload('c01_cn')")
    pg.wait_for_timeout(500)
    pg.evaluate("() => { const t = window.hoyoApp.tasks['c01_cn'];"
                "if (t) { t.done = t.total; t.percent = 100; } }")
    pg.wait_for_timeout(900)
    ph = pg.evaluate("() => (window.hoyoApp.tasks['c01_cn'] || {}).phase")
    check("预下载停在待安装", ph == "ready", f"phase={ph}")
    lbl = pg.evaluate("() => document.querySelector('.label').textContent")
    check("按钮变成安装", lbl == "安装", f"label={lbl}")
    shot(pg, "a1-predownload")

    # 9) 点安装
    pg.click(".btn-primary")
    pg.wait_for_timeout(600)
    for _ in range(20):
        pg.evaluate("() => { const t = window.hoyoApp.tasks['c01_cn'];"
                    "if (t && t.phaseLeft) t.phaseLeft = 0.01; }")
        pg.wait_for_timeout(350)
        if pg.evaluate("() => Object.keys(window.hoyoApp.tasks).length") == 0:
            break
    inst = pg.evaluate("() => window.HOYO_CONFIG.games['c01_cn'].installed")
    check("安装完成", inst is True, f"installed={inst}")

    # 10) 多任务 + 失败重试
    pg.evaluate("""() => {
      window.HOYO_CONFIG.games['c01_cn'].installed = false;
      window.hoyoApp.taskStart('c01_cn', 'install');
    }""")
    pg.wait_for_timeout(400)
    pg.evaluate("() => window.hoyoApp.taskFail('c01_cn', '网络中断')")
    pg.wait_for_timeout(400)
    ph = pg.evaluate("() => (window.hoyoApp.tasks['c01_cn'] || {}).phase")
    check("失败态进入", ph == "failed", f"phase={ph}")
    n = pg.evaluate("() => document.querySelectorAll('.task.failed').length")
    check("失败卡片渲染", n == 1, f"{n} 张")
    shot(pg, "a2-failed")
    pg.evaluate("() => document.querySelector('.task .retry').click()")
    pg.wait_for_timeout(400)
    ph = pg.evaluate("() => (window.hoyoApp.tasks['c01_cn'] || {}).phase")
    check("重试恢复下载", ph == "downloading", f"phase={ph}")

    # 11) 限速生效
    pg.evaluate("() => { window.hoyoApp.setSimulate(true); }")
    pg.evaluate("""() => {
      const w = window;
      w.__lim = 4;
      // 通过设置持久化路径改限速
      localStorage.setItem('hoyo-launcher-settings',
        JSON.stringify({ limitSpeed: 4 }));
    }""")
    # 重新载入设置并重启任务
    pg.evaluate("() => window.hoyoApp.taskCancel('c01_cn')")
    pg.wait_for_timeout(300)
    pg.reload(wait_until="load")
    pg.wait_for_timeout(1800)
    pg.evaluate("() => window.hoyoApp.taskStart('c01_cn', 'install')")
    pg.wait_for_timeout(1500)
    sp = pg.evaluate("() => (window.hoyoApp.tasks['c01_cn'] || {}).speed || 0")
    check("限速生效(<=4MB/s)", 0 < sp <= 4.2 * 1048576, f"{sp/1048576:.2f} MB/s")
    pg.evaluate("() => window.hoyoApp.taskCancel('c01_cn')")

    # 12) 卸载
    pg.wait_for_timeout(300)
    pg.evaluate("() => window.hoyoApp.taskCancel('c01_cn')")
    pg.wait_for_timeout(300)
    pg.evaluate("""() => {
      const it = document.querySelector('.game-icon[data-side="c01_cn"]');
      it.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true }));
    }""")
    pg.wait_for_timeout(400)
    n = pg.evaluate("() => document.querySelectorAll('.game-pop .pop-item').length")
    check("游戏右键菜单", n >= 1, f"{n} 项")
    shot(pg, "a3-gamemenu")
    pg.evaluate("() => window.hoyoUI.closePopup()")

    # 13) 卸载确认框
    pg.evaluate("""() => {
      const m = document.createElement('div');
      // 直接走内部确认框逻辑：模拟点菜单里的卸载
    }""")
    pg.evaluate("() => { window.HOYO_CONFIG.games['c01_cn'].installed = true; }")
    pg.evaluate("""() => {
      const it = document.querySelector('.game-icon[data-side="c01_cn"]');
      it.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true }));
    }""")
    pg.wait_for_timeout(300)
    pg.evaluate("""() => {
      const b = [...document.querySelectorAll('.game-pop .pop-item')]
        .find(x => x.textContent.includes('卸载'));
      if (b) b.click();
    }""")
    pg.wait_for_timeout(400)
    has = pg.evaluate("() => !!document.querySelector('.uninstall-foot')")
    check("卸载确认框", has)
    shot(pg, "a4-uninstall")
    pg.evaluate("""() => {
      const b = document.querySelector('.uninstall-foot [data-a="cancel"]');
      if (b) b.click();
    }""")

    print("\n=== C: 可用性 ===")

    # 14) 焦点圈
    kb = pg.evaluate("""() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }));
      return document.documentElement.classList.contains('kb');
    }""")
    check("键盘焦点圈开关", kb)

    # 15) prefers-reduced-motion 规则存在
    rm = pg.evaluate("""() => {
      const css = [...document.styleSheets].flatMap(s => {
        try { return [...s.cssRules].map(r => r.cssText); } catch (e) { return []; }
      }).join(' ');
      return css.includes('prefers-reduced-motion');
    }""")
    check("prefers-reduced-motion 规则", rm)

    # 16) 设置里的新控件（不同分类下的行要遍历所有标签页才找得到）
    pg.evaluate("() => window.hoyoApp.openSettings()")
    pg.wait_for_timeout(500)
    counts = pg.evaluate("""() => {
      const tabs = [...document.querySelectorAll('.set-tab')];
      let cbx = 0, inp = 0, c2 = 0, i2 = 0;
      tabs.forEach((t, i) => {
        t.click();
        c2 += document.querySelectorAll('.set-dialog .cbx').length;
        i2 += document.querySelectorAll('.set-dialog .inp').length;
      });
      if (tabs.length) tabs[0].click();
      return { cbx: c2, inp: i2, tabs: tabs.length };
    }""")
    check("复选框控件", counts["cbx"] >= 1, f"{counts['cbx']} 个（{counts['tabs']} 个分类）")
    check("输入框控件", counts["inp"] >= 1, f"{counts['inp']} 个")
    shot(pg, "c1-controls")

    # 17) 设置持久化（同样要遍历分类找那一行）
    clicked = pg.evaluate("""() => {
      const tabs = [...document.querySelectorAll('.set-tab')];
      for (const t of tabs) {
        t.click();
        const row = [...document.querySelectorAll('.set-row')]
          .find(r => r.textContent.includes('减少界面动效'));
        if (row) { row.querySelector('.sw').click(); return true; }
      }
      return false;
    }""")
    pg.wait_for_timeout(400)
    saved = pg.evaluate("() => localStorage.getItem('hoyo-launcher-settings')")
    check("设置写入 localStorage", clicked and "reduceMotion" in (saved or ""),
          (saved or "")[:70])

    # 18) 语言切换（i18n）
    pg.evaluate("() => window.hoyoUI.setLocale('en')")
    pg.wait_for_timeout(200)
    en = pg.evaluate("() => window.hoyoUI.t('task.retry')")
    check("i18n 字典切换", en == "Retry", f"t('task.retry')={en}")

    # 19) 自适应缩放
    pg.set_viewport_size({"width": 1024, "height": 640})
    pg.wait_for_timeout(600)
    tr = pg.evaluate("() => getComputedStyle(document.getElementById('app')).transform")
    check("小视口自动缩放", tr != "none", tr[:40])
    pg.screenshot(path=f"{PRE}-c2-fit.png")
    pg.set_viewport_size({"width": 1280, "height": 720})

    # 20) 窗口控制反馈
    pg.evaluate("() => window.hoyoUI.closePopup(); window.hoyoApp.closeModal()")
    pg.wait_for_timeout(300)
    pg.evaluate(
        "() => document.querySelector('[data-action=\"minimize\"]').click()")
    pg.wait_for_timeout(400)
    n = pg.evaluate("() => [...document.querySelectorAll('.toast')].length")
    check("窗口控制无宿主时给提示", n >= 1, f"{n} 条")
    shot(pg, "c3-winhint")

    if errs:
        print("\n页面报错:")
        for e in errs[-10:]:
            print("   ", e)

    b.close()

print("\n" + "=" * 66)
ok = sum(1 for _, o, _ in RESULTS if o)
print(f"通过 {ok}/{len(RESULTS)}")
for n, o, d in RESULTS:
    if not o:
        print(f"  未通过: {n}  {d}")
