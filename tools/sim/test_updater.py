"""端到端验证增量更新：在真实浏览器里跑完整个流程。

流程：
  1. 从本地 HTTP 拉 v1 的文件（模拟"已安装的旧版本"）
  2. 拉 dist/latest.json -> v2 manifest
  3. 本地分块 + 算 hash -> 差异比对
  4. 只下载缺失的 chunk（并发 + 逐块校验）
  5. 按偏移拼装 -> 逐文件 sha256 校验
  6. 与磁盘上的 v2/ 逐个字节比对，确认结果正确

用法: python test_updater.py [页面URL]
"""

import hashlib
import json
import os
import sys
from urllib.parse import quote

from playwright.sync_api import sync_playwright

PAGE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8899/"
# 同一个源（/sim/ 由 tools/sim/serve.py 提供），避免跨源
SIM = "http://127.0.0.1:8899/sim"
SIMDIR = r"F:\新建文件夹\update-sim"

print("=" * 70)
print("增量更新端到端验证")
print("=" * 70)

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(PAGE, wait_until="load")
    pg.wait_for_timeout(1500)

    has = pg.evaluate("() => typeof window.hoyoUpdater")
    print(f"\n1) updater 已加载: {has}")

    # 网络统计：看客户端到底下了多少
    bytes_downloaded = {"n": 0, "chunks": 0}

    def on_response(resp):
        if "/chunks/" in respp_url(resp):
            pass

    def resp_url(r):
        return r.url

    def handle(resp):
        u = resp.url
        if "/dist/chunks/" in u:
            bytes_downloaded["chunks"] += 1
    pg.on("response", handle)

    # ---- 跑完整流程 ----
    print("\n2) 执行 update()（拉清单 -> 本地索引 -> 差异 -> 下载 -> 拼装 -> 校验）")
    result = pg.evaluate("""async () => {
      const t0 = performance.now();
      try {
      // 模拟"已安装的 v1"：把 v1 的文件读进内存
      const manifestV1 = await (await fetch(
        '%s/dist/manifests/v1-cdc.json')).json();
      const local = {};
      for (const f of manifestV1.files) {
        const r = await fetch('%s/v1/' + f.path.split('/').map(encodeURIComponent).join('/'));
        local[f.path] = new Uint8Array(await r.arrayBuffer());
      }
      const res = await window.hoyoUpdater.update(local,
        '%s/dist/latest.json', {
          concurrency: 6,
          onPlan: (pl) => { window.__plan = {
            need: pl.need.length, needBytes: pl.needBytes,
            reuseBytes: pl.reuseBytes, totalBytes: pl.totalBytes,
            deleteFiles: pl.deleteFiles, changed: pl.changedFiles }; },
        });
      const ms = performance.now() - t0;
      // 把结果算成 sha 摘要回传，避免传几十 MB
      const digest = {};
      for (const [k, v] of Object.entries(res.files)) {
        const h = await crypto.subtle.digest('SHA-256', v);
        digest[k] = [...new Uint8Array(h)].map(x => x.toString(16).padStart(2,'0')).join('');
      }
      return {
        ms: Math.round(ms),
        plan: window.__plan,
        stats: res.stats,
        deleted: res.deleted,
        errors: res.errors,
        manifest: { version: res.manifest.version, files: res.manifest.files.length },
        digest: digest,
      };
      } catch (e) {
        return { failed: true, msg: String(e && e.message || e),
                 missing: (e && e.missing) || null, diag: (e && e.diag) || null,
                 plan: window.__plan || null };
      }
    }""" % (SIM, SIM, SIM))

    if result.get("failed"):
        print("\n   [!] 更新失败:", result["msg"])
        print("   plan:", result.get("plan"))
        print("   diag:", json.dumps(result.get("diag"), ensure_ascii=False, indent=2))
        for m in (result.get("missing") or [])[:5]:
            print("   缺:", json.dumps(m, ensure_ascii=False))
        b.close()
        sys.exit(1)

    pl = result["plan"]
    st = result["stats"]
    print(f"   耗时 {result['ms']} ms")
    print(f"   计划：唯一分块共 {pl['totalBytes']/1048576:.2f} MB，"
          f"可复用 {pl['reuseBytes']/1048576:.2f} MB，"
          f"需下载 {pl['needBytes']/1048576:.2f} MB（{pl['need']} 块）")
    print(f"   实际：下载 {st['bytesFetched']/1048576:.2f} MB / {st['chunksFetched']} 块，"
          f"失败 {st['chunksFailed']}")
    print(f"   省下 {st['savedPercent']:.1f}%")
    print(f"   改动文件 {len(pl['changed'])} 个: {', '.join(pl['changed'][:6])}"
          + (" …" if len(pl['changed']) > 6 else ""))
    print(f"   待删除 {pl['deleteFiles']}")
    print(f"   拼装出的文件 {len(result['digest'])} 个")

    # ---- 与磁盘上的 v2 逐字节比对 ----
    print("\n3) 与磁盘 v2/ 比对（逐文件 SHA-256）")
    v2dir = os.path.join(SIMDIR, "v2")
    disk = {}
    for dp, _, fns in os.walk(v2dir):
        for fn in fns:
            fp = os.path.join(dp, fn)
            rel = os.path.relpath(fp, v2dir).replace(os.sep, "/")
            with open(fp, "rb") as f:
                disk[rel] = hashlib.sha256(f.read()).hexdigest()

    ok = 0
    bad = []
    for rel, h in sorted(disk.items()):
        got = result["digest"].get(rel)
        if got == h:
            ok += 1
        else:
            bad.append(rel)
    extra = [k for k in result["digest"] if k not in disk]

    print(f"   磁盘 v2 文件 {len(disk)} 个，客户端拼装 {len(result['digest'])} 个")
    print(f"   完全一致 {ok} 个")
    if bad:
        print(f"   [!] 不一致: {bad}")
    if extra:
        print(f"   [!] 多出来的: {extra}")

    print("\n" + "=" * 70)
    allok = (ok == len(disk) and not bad and not extra
             and st["chunksFailed"] == 0
             and result["deleted"] == ["assets/voice/v06.ogg"])
    print("结论:", "全部通过 ✓" if allok else "有问题 ✗")
    print(f"  文件逐字节一致: {'是' if ok == len(disk) and not bad else '否'}")
    print(f"  删除清单正确: {'是' if result['deleted'] == ['assets/voice/v06.ogg'] else result['deleted']}")
    print(f"  无下载失败: {'是' if st['chunksFailed'] == 0 else '否'}")

    if errs:
        print("\n页面错误:")
        for e in errs[-8:]:
            print("   ", e)

    b.close()
