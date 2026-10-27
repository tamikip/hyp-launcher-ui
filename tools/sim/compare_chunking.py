"""逐文件对比固定分块与 CDC：各自赢在哪。"""

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

D = r"F:\新建文件夹\update-sim\dist\manifests"


def load(v):
    return json.load(open(os.path.join(D, v), encoding="utf-8"))


def per_file(m1, m2, size_of):
    f1 = {f["path"]: f for f in m1["files"]}
    rows = []
    for f in m2["files"]:
        old = f1.get(f["path"])
        if old is None:
            rows.append((f["path"], "新增", f["size"], f["size"], f["size"], None))
            continue
        if old["sha256"] == f["sha256"]:
            rows.append((f["path"], "不变", f["size"], 0, f["size"], None))
            continue
        have = set(c["h"] for c in old["chunks"])
        need = [c for c in f["chunks"] if c["h"] not in have]
        need_b = sum(c["l"] for c in need)
        rows.append((f["path"], "改动", f["size"], min(need_b, f["size"]),
                     f["size"], len(need)))
    return rows


print("=" * 96)
print("逐文件：v1 -> v2 需要下载的字节数（越小越好）")
print("=" * 96)
print(f"{'文件':<32}{'状态':<6}{'体积':>10}{'fixed':>12}{'cdc':>12}   谁更省")

r_fixed = per_file(load("v1-fixed.json"), load("v2-fixed.json"), None)
r_cdc = per_file(load("v1-cdc.json"), load("v2-cdc.json"), None)
fm = {r[0]: r for r in r_fixed}
cm = {r[0]: r for r in r_cdc}

tf = tc = tt = 0
for path in sorted(set(fm) | set(cm)):
    a = fm.get(path)
    c = cm.get(path)
    a_need = a[3] if a else 0
    c_need = c[3] if c else 0
    size = (a or c)[2]
    status = (a or c)[1]
    tf += a_need
    tc += c_need
    tt += size
    if a_need == c_need:
        who = "一样"
    elif c_need < a_need:
        who = f"CDC 省 {a_need - c_need} B"
    else:
        who = f"fixed 省 {c_need - a_need} B"
    print(f"{path[:32]:<32}{status:<6}{size:>10}{a_need:>12}{c_need:>12}   {who}")

print("-" * 96)
print(f"{'合计':<32}{'':<6}{tt:>10}{tf:>12}{tc:>12}")
print(f"\n  fixed 需下载 {tf/1024:.0f} KB    cdc 需下载 {tc/1024:.0f} KB   "
      f"差值 {(tf-tc)/1024:+.0f} KB")

print("""
结论怎么看：
  · 「不变」的文件两边都是 0，走"整文件 sha 相同直接跳过"的快路径。
  · 「新增」文件两边都要下全量，没有区别。
  · 「改动」文件才是分块策略的战场：
      固定分块 —— 中途改一小段只坏 1~2 块；但开头插入会让后面全部错位。
      CDC     —— 按内容切点，插入/删除都不影响后面；代价是块大小不齐，
                 被改动的那一块可能比固定分块更大。
  · 本模拟里只有一个 98 KB 的小文件做「开头插入」，
    所以固定分块的错位损失很小，两边几乎持平。
    真实软件（几百 MB 的 asar、频繁插资源）CDC 的优势会明显得多。
""")
