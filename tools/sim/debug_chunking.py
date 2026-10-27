"""排查：JS 的 CDC 分块边界是否与打包器（Python）完全一致。"""

import json
import os
import sys

from playwright.sync_api import sync_playwright

SIM = "http://127.0.0.1:8899/sim"
SIMDIR = r"F:\新建文件夹\update-sim"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:8899/", wait_until="load")
    pg.wait_for_timeout(1500)

    res = pg.evaluate("""async () => {
      await window.hoyoUpdater.loadGear('%s/dist/');
      const man = await (await fetch('%s/dist/manifests/v1-cdc.json')).json();
      const out = [];
      for (const f of man.files.slice(0, 6)) {
        const r = await fetch('%s/v1/' + f.path.split('/').map(encodeURIComponent).join('/'));
        if (!r.ok) { out.push({path:f.path, missing:true}); continue; }
        const buf = new Uint8Array(await r.arrayBuffer());
        const list = window.hoyoUpdater.chunksOf(buf, man);
        out.push({ path: f.path, size: buf.length,
                   js: list.map(c => [c.o, c.l]),
                   py: f.chunks.map(c => [c.o, c.l]) });
      }
      return out;
    }""" % (SIM, SIM, SIM))

    for e in res:
        if e.get("missing"):
            print(f"{e['path']}: v1 里没有（新增文件）")
            continue
        same = e["js"] == e["py"]
        print(f"\n{e['path']}  size={e['size']}  JS {len(e['js'])} 块 / PY {len(e['py'])} 块  "
              f"{'一致' if same else '不一致 !!!'}")
        if not same:
            for i in range(max(len(e["js"]), len(e["py"]))):
                a = e["js"][i] if i < len(e["js"]) else None
                c = e["py"][i] if i < len(e["py"]) else None
                if a != c:
                    print(f"   第 {i} 块不同: JS={a}  PY={c}")
                    if i > 4:
                        break

    if errs:
        print("错误:", errs[-5:])
    b.close()
