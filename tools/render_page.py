"""用 Playwright 按 1280x720 精确渲染复刻页面并截图。

用法: python render_page.py <url> <输出png> [等待毫秒]
"""
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1]
OUT = sys.argv[2]
WAIT = int(sys.argv[3]) if len(sys.argv) > 3 else 1500


def launch(p):
    """优先用系统已装的 Chrome，其次 Edge，最后用 Playwright 自带内核。"""
    for channel in ("chrome", "msedge"):
        try:
            b = p.chromium.launch(channel=channel)
            print(f"使用浏览器: {channel}")
            return b
        except Exception as e:  # noqa: BLE001
            print(f"  {channel} 不可用: {str(e).splitlines()[0]}")
    b = p.chromium.launch()
    print("使用浏览器: playwright 内置 chromium")
    return b


with sync_playwright() as p:
    browser = launch(p)
    page = browser.new_page(
        viewport={"width": 1280, "height": 720},
        device_scale_factor=1,
    )
    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))

    page.goto(URL, wait_until="load")
    # 等所有图片解码完成
    page.wait_for_timeout(WAIT)
    page.evaluate("""() => Promise.all(
        Array.from(document.images)
          .filter(i => !i.complete)
          .map(i => new Promise(r => { i.onload = i.onerror = r; }))
    )""")
    page.wait_for_timeout(300)

    page.screenshot(path=OUT)
    print(f"截图已保存: {OUT}")

    if errors:
        print("\n页面报错:")
        for e in errors[:20]:
            print("  " + e)
    else:
        print("无页面报错")

    browser.close()
