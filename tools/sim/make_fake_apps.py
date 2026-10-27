"""造两套假的软件包（v1 / v2），用来演示增量更新。

设计要点：
  - 内容确定性生成（固定种子），每次跑出来一模一样，便于对比和复现
  - 覆盖几种典型变化，每种都有明确的用意：
      * 大文件尾部追加         -> 固定分块也能保住大部分
      * 大文件中间改一小段      -> 只影响 1~2 个分块
      * 小文件开头插入一段      -> 固定分块的经典弱点（后续分块全部错位）
      * 新增文件 / 删除文件
      * 完全不变的文件
  - 输出：
      v1/            模拟"已安装的旧版本"
      v2/            目标版本
      DemoClient-0.1.0.zip
      DemoClient-0.1.1.zip

用法: python make_fake_apps.py [输出目录]
"""

import hashlib
import json
import os
import random
import struct
import sys
import zipfile

OUT = sys.argv[1] if len(sys.argv) > 1 else r"F:\新建文件夹\update-sim"
V1 = os.path.join(OUT, "v1")
V2 = os.path.join(OUT, "v2")

V1_VER = "0.1.0"
V2_VER = "0.1.1"

rnd = random.Random(20261001)


def blob(n, seed):
    """确定性伪随机字节（压缩后不可压，方便观察真实体积）。"""
    r = random.Random(seed)
    return bytes(r.getrandbits(8) for _ in range(n))


def png_like(n, seed, tag):
    """造一个"像图片"的块：头部固定 + 中间伪随机，便于局部修改。"""
    head = b"\x89PNG\r\n\x1a\n" + tag.encode()[:8].ljust(8, b"\0")
    return head + blob(n - len(head) - 8, seed) + b"IEND\xaeB`\x82"


def ogg_like(n, seed):
    return b"OggS" + blob(n - 4, seed)


def write(root, rel, data):
    p = os.path.join(root, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)
    return len(data)


# ============================================================
# v1
# ============================================================
FILES_V1 = {}

FILES_V1["DemoClient.exe"] = blob(3_145_728, 11)          # 3.0 MB
FILES_V1["resources/app.asar"] = blob(4_194_304, 12)         # 4.0 MB
FILES_V1["resources/steam_api64.dll"] = blob(215_040, 13)    # 210 KB，不变
FILES_V1["resources/steamworks.js"] = blob(98_304, 14)
FILES_V1["locales/zh-CN.json"] = json.dumps(
    {"hello": "你好", "start": "开始游戏", "settings": "设置"},
    ensure_ascii=False, indent=2).encode("utf-8")
FILES_V1["locales/en.json"] = json.dumps(
    {"hello": "Hello", "start": "Start", "settings": "Settings"},
    ensure_ascii=False, indent=2).encode("utf-8")
FILES_V1["config.json"] = json.dumps(
    {"version": V1_VER, "quality": "high", "vsync": True}, indent=2).encode("utf-8")

for i, name in enumerate(["title", "bg_day", "bg_night", "char_a", "char_b"]):
    FILES_V1[f"assets/bg/{name}.png"] = png_like(262_144 + i * 16_384, 100 + i, name)
for i, name in enumerate(["main_theme", "bgm_01", "bgm_02"]):
    FILES_V1[f"assets/bgm/{name}.ogg"] = ogg_like(327_680, 200 + i)
for i in range(1, 7):
    FILES_V1[f"assets/voice/v{i:02d}.ogg"] = ogg_like(40_960 + i * 2048, 300 + i)
for i in range(1, 9):
    FILES_V1[f"data/scripts/ch{i:02d}.json"] = json.dumps(
        {"id": i, "text": f"章节 {i} 的剧本内容", "lines": [f"line {j}" for j in range(20)]},
        ensure_ascii=False, indent=1).encode("utf-8")

# ============================================================
# v2：在 v1 基础上做几种典型改动
# ============================================================
FILES_V2 = dict(FILES_V1)

# 1) 大文件尾部追加（固定分块也能保住前面全部）
FILES_V2["DemoClient.exe"] = FILES_V1["DemoClient.exe"] + blob(131_072, 51)

# 2) 大文件中间改一小段（只坏 1~2 个分块）
a = bytearray(FILES_V1["resources/app.asar"])
mid = len(a) // 2
a[mid:mid + 4096] = blob(4096, 52)
FILES_V2["resources/app.asar"] = bytes(a)

# 3) 小文件开头插入一段 -> 固定分块的经典弱点
FILES_V2["resources/steamworks.js"] = blob(8192, 53) + FILES_V1["resources/steamworks.js"]

# 4) 完全不变
# resources/steam_api64.dll, locales/zh-CN.json(en), bg 的几张贴图原样保留

# 5) 改配置 / 改语言包
FILES_V2["config.json"] = json.dumps(
    {"version": V2_VER, "quality": "ultra", "vsync": True, "fps": 120},
    indent=2).encode("utf-8")
FILES_V2["locales/zh-CN.json"] = json.dumps(
    {"hello": "你好", "start": "开始游戏", "settings": "设置", "workshop": "创意工坊"},
    ensure_ascii=False, indent=2).encode("utf-8")

# 6) 换掉两张贴图 + 一首 BGM
FILES_V2["assets/bg/char_a.png"] = png_like(278_528, 601, "char_a")
FILES_V2["assets/bg/title.png"] = png_like(262_144, 602, "title")
FILES_V2["assets/bgm/bgm_01.ogg"] = ogg_like(339_968, 603)

# 7) 新增文件
FILES_V2["assets/bg/cg_extra.png"] = png_like(311_296, 604, "cg_extra")
FILES_V2["data/scripts/ch09.json"] = json.dumps(
    {"id": 9, "text": "新增章节", "lines": [f"line {j}" for j in range(20)]},
    ensure_ascii=False, indent=1).encode("utf-8")

# 8) 删除文件
del FILES_V2["assets/voice/v06.ogg"]


def materialize(root, files):
    if os.path.isdir(root):
        import shutil
        shutil.rmtree(root)
    total = 0
    for rel, data in sorted(files.items()):
        total += write(root, rel, data)
    return total


def make_zip(path, root, ver, files):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for rel in sorted(files):
            z.write(os.path.join(root, rel.replace("/", os.sep)), rel)


print("生成到:", OUT)
t1 = materialize(V1, FILES_V1)
t2 = materialize(V2, FILES_V2)
print(f"  v1/  {len(FILES_V1)} 个文件，{t1/1048576:.2f} MB")
print(f"  v2/  {len(FILES_V2)} 个文件，{t2/1048576:.2f} MB")

z1 = os.path.join(OUT, f"DemoClient-{V1_VER}.zip")
z2 = os.path.join(OUT, f"DemoClient-{V2_VER}.zip")
make_zip(z1, V1, V1_VER, FILES_V1)
make_zip(z2, V2, V2_VER, FILES_V2)
print(f"  {os.path.basename(z1)}  {os.path.getsize(z1)/1048576:.2f} MB")
print(f"  {os.path.basename(z2)}  {os.path.getsize(z2)/1048576:.2f} MB")

# 变化清单，方便核对
changed = sorted(k for k in FILES_V1 if k in FILES_V2 and FILES_V1[k] != FILES_V2[k])
added = sorted(set(FILES_V2) - set(FILES_V1))
removed = sorted(set(FILES_V1) - set(FILES_V2))
same = sorted(k for k in FILES_V1 if k in FILES_V2 and FILES_V1[k] == FILES_V2[k])
print(f"\n  改动 {len(changed)} / 新增 {len(added)} / 删除 {len(removed)} / 不变 {len(same)}")
print("  改动:", ", ".join(changed))
print("  新增:", ", ".join(added))
print("  删除:", ", ".join(removed))
