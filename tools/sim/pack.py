"""把 v1 / v2 分块打包，生成清单 + 内容寻址的 chunk 仓库，并算出增量收益。

产物（可直接丢到 R2 / 任意静态存储）：
    dist/latest.json                 客户端先拉这个
    dist/manifests/v1.json
    dist/manifests/v2.json
    dist/chunks/ab/abcdef...bin      按 sha256 前两位分目录，避免单目录堆几万个文件

两种分块策略：
    fixed   固定大小（默认 64 KB）。简单，但文件开头插入/删除会让后面所有分块错位。
    cdc     内容定义分块（gear hash），按内容边界切，插入不影响后续分块。

用法:
    python pack.py                    # 两种都跑一遍并对比
    python pack.py --mode fixed
    python pack.py --mode cdc
"""

import argparse
import hashlib
import json
import os
import random
import sys
import time

SIM = r"F:\新建文件夹\update-sim"
DIST = os.path.join(SIM, "dist")

FIXED_SIZE = 64 * 1024          # 固定分块大小
CDC_MIN = 16 * 1024             # CDC 最小块
CDC_MAX = 256 * 1024            # CDC 最大块
CDC_BITS = 16                   # 平均块大小 ≈ 2^16 = 64 KB
CDC_MASK = (1 << CDC_BITS) - 1

# gear hash 表：确定性生成，客户端要用同一张表
_gr = random.Random(0x9E3779B97F4A7C15)
GEAR = [_gr.getrandbits(64) for _ in range(256)]


def sha256(b):
    return hashlib.sha256(b).hexdigest()


# ---------------- 分块 ----------------
def chunks_fixed(data, size=FIXED_SIZE):
    out = []
    for o in range(0, len(data), size):
        out.append((o, min(size, len(data) - o)))
    return out


def chunks_cdc(data, min_s=CDC_MIN, max_s=CDC_MAX, mask=CDC_MASK):
    """内容定义分块（gear hash）。

    边界条件只看内容，所以前面插入一段不会影响后面的切点 ——
    这正是固定分块做不到的地方（见 README 的对比数据）。
    """
    out = []
    if not data:
        return out
    h = 0
    start = 0
    n = len(data)
    for i in range(n):
        h = ((h << 1) + GEAR[data[i]]) & 0xFFFFFFFFFFFFFFFF
        size = i - start + 1
        if size >= min_s and (h & mask) == 0:
            out.append((start, size))
            start = i + 1
            h = 0
        elif size >= max_s:
            out.append((start, size))
            start = i + 1
            h = 0
    if start < n:
        out.append((start, n - start))
    return out


# ---------------- 打包 ----------------
def walk(root):
    files = {}
    for dp, _, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            with open(p, "rb") as f:
                files[rel] = f.read()
    return files


def pack(root, version, mode, chunk_dir, manifest_dir):
    files = walk(root)
    manifest = {
        "app": "DemoClient",
        "version": version,
        "chunkMode": mode,
        "chunkSize": FIXED_SIZE if mode == "fixed" else None,
        "cdc": None if mode == "fixed" else {"min": CDC_MIN, "max": CDC_MAX, "bits": CDC_BITS},
        "files": [],
    }
    store = {}          # sha -> bytes
    total = 0
    for rel in sorted(files):
        data = files[rel]
        total += len(data)
        pieces = []
        for (o, l) in (chunks_fixed(data) if mode == "fixed" else chunks_cdc(data)):
            h = sha256(data[o:o + l])
            store.setdefault(h, data[o:o + l])
            pieces.append({"o": o, "l": l, "h": h})
        manifest["files"].append({
            "path": rel,
            "size": len(data),
            "sha256": sha256(data),
            "chunks": pieces,
        })

    # 落盘：清单 + chunk 仓库
    os.makedirs(manifest_dir, exist_ok=True)
    with open(os.path.join(manifest_dir, version + ".json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, separators=(",", ":"))

    written = 0
    for h, b in store.items():
        d = os.path.join(chunk_dir, h[:2])
        p = os.path.join(d, h + ".bin")
        if not os.path.exists(p):
            os.makedirs(d, exist_ok=True)
            with open(p, "wb") as f:
                f.write(b)
            written += 1
    return manifest, store, total, written


def chunk_index(manifest):
    """manifest 里出现过的 chunk 集合（按 hash）。"""
    s = set()
    for f in manifest["files"]:
        for c in f["chunks"]:
            s.add(c["h"])
    return s


def size_of(idx, store):
    return sum(len(store[h]) for h in idx if h in store)


def report(mode, m1, s1, t1, m2, s2, t2):
    store = dict(s1)
    store.update(s2)
    have1 = chunk_index(m1)
    have2 = chunk_index(m2)

    full = size_of(have2, store)                    # 全量下载 v2 要下的
    reuse = have1 & have2                            # v1 已有、v2 还能用
    need = have2 - have1                             # 增量真正要下的
    dropped = have1 - have2                          # v1 有但 v2 不要了

    inc = size_of(need, store)
    reuse_b = size_of(reuse, store)

    print(f"\n{'=' * 66}")
    print(f"分块策略: {mode}   平均块大小 ≈ {(t2 / max(1, len(have2))) / 1024:.1f} KB")
    print("=" * 66)
    print(f"  v1 原始体积        {t1/1048576:8.2f} MB   ({len(have1)} 个唯一分块)")
    print(f"  v2 原始体积        {t2/1048576:8.2f} MB   ({len(have2)} 个唯一分块)")
    print(f"  全量下载 v2        {full/1048576:8.2f} MB")
    print(f"  可复用 v1 的分块    {reuse_b/1048576:8.2f} MB   ({len(reuse)} 块)")
    print(f"  增量只需下载        {inc/1048576:8.2f} MB   ({len(need)} 块)")
    print(f"  v1 里被丢弃的分块    {size_of(dropped, store)/1048576:8.2f} MB   ({len(dropped)} 块)")
    if full:
        print(f"  >>> 相对全量省下    {100 * (1 - inc / full):.1f}%")
    return {"mode": mode, "full": full, "inc": inc, "reuse": reuse_b,
            "n1": len(have1), "n2": len(have2), "need": len(need)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fixed", "cdc", "both"], default="both")
    args = ap.parse_args()

    modes = ["fixed", "cdc"] if args.mode == "both" else [args.mode]
    results = []
    for mode in modes:
        chunk_dir = os.path.join(DIST, "chunks")
        manifest_dir = os.path.join(DIST, "manifests")
        t0 = time.time()
        m1, s1, t1, w1 = pack(os.path.join(SIM, "v1"), "v1-" + mode, mode, chunk_dir, manifest_dir)
        m2, s2, t2, w2 = pack(os.path.join(SIM, "v2"), "v2-" + mode, mode, chunk_dir, manifest_dir)
        r = report(mode, m1, s1, t1, m2, s2, t2)
        r["wrote"] = w1 + w2
        r["secs"] = round(time.time() - t0, 2)
        results.append(r)

        # 这个策略的 latest.json
        with open(os.path.join(DIST, "latest-%s.json" % mode), "w", encoding="utf-8") as f:
            json.dump({
                "app": "DemoClient",
                "version": m2["version"],
                "mode": mode,
                "manifest": "manifests/%s.json" % m2["version"],
                "prevManifest": "manifests/%s.json" % m1["version"],
                "chunkBase": "chunks/",
                "chunkUrlPattern": "chunks/{h0}/{h}.bin",
                "publishedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }, f, ensure_ascii=False, indent=2)

    # 默认 latest.json 用 cdc（效果更好）
    src = os.path.join(DIST, "latest-cdc.json")
    if os.path.exists(src):
        with open(src, encoding="utf-8") as f:
            d = json.load(f)
        with open(os.path.join(DIST, "latest.json"), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

    # CDC 的 gear 表必须客户端/服务端一致，导出成文件让客户端加载
    # （Python 的 Mersenne Twister 很难在 JS 里复现，导出来最省事也最可靠）
    with open(os.path.join(DIST, "gear.json"), "w", encoding="utf-8") as f:
        json.dump({"bits": CDC_BITS, "gear": ["%016x" % g for g in GEAR]}, f)
    print("  已导出 gear.json（CDC 用，客户端需与打包器保持一致）")

    print(f"\n{'=' * 66}")
    print("产物目录:", DIST)
    tot = sum(os.path.getsize(os.path.join(dp, fn))
              for dp, _, fns in os.walk(os.path.join(DIST, "chunks")) for fn in fns)
    n = sum(len(fns) for _, _, fns in os.walk(os.path.join(DIST, "chunks")))
    print(f"  chunks/  {n} 个文件，共 {tot/1048576:.2f} MB")
    print(f"  manifests/ v1/v2 各策略一份")
    print(f"  latest.json / latest-fixed.json / latest-cdc.json")
    print("\n上传到 R2 后，客户端只要改 latest.json 里的相对路径即可。")


if __name__ == "__main__":
    main()
