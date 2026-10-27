"""把复刻渲染图与官方截图对比：并排图 + 差分热力图 + 分区差异指标。

用法: python compare_render.py <官方客户区图> <复刻渲染图> <输出目录> [标签]
"""
import os
import sys

from PIL import Image, ImageChops, ImageDraw

OFFICIAL = sys.argv[1]
RENDER = sys.argv[2]
OUT = sys.argv[3]
TAG = sys.argv[4] if len(sys.argv) > 4 else "cmp"
os.makedirs(OUT, exist_ok=True)

official = Image.open(OFFICIAL).convert("RGB")
render = Image.open(RENDER).convert("RGB")

if render.size != official.size:
    print(f"尺寸不同，把渲染图缩放到 {official.size}")
    render = render.resize(official.size, Image.LANCZOS)

W, H = official.size
diff = ImageChops.difference(official, render)
gray = diff.convert("L")

# 分区指标（客户区坐标）
REGIONS = [
    ("顶栏", 0, 0, 1280, 58),
    ("左上logo+标题", 60, 35, 400, 290),
    ("版本热点+暂停", 120, 290, 400, 355),
    ("活动卡片", 115, 365, 535, 575),
    ("页签+资讯", 125, 555, 520, 660),
    ("左下宫格", 10, 650, 70, 700),
    ("右下CTA", 1010, 590, 1240, 700),
    ("右栏图标", 1225, 60, 1280, 560),
    ("底部进度", 640, 695, 1010, 720),
    ("纯背景基准(右上)", 700, 60, 1100, 260),
]
print(f"{'区域':<20}{'平均差':>9}{'显著差异占比':>14}")
print("-" * 45)
rows = []
for name, l, t, r, b in REGIONS:
    l, t = max(0, l), max(0, t)
    r, b = min(W, r), min(H, b)
    if r <= l or b <= t:
        continue
    g = gray.crop((l, t, r, b))
    hist = g.histogram()
    n = sum(hist)
    mean = sum(i * c for i, c in enumerate(hist)) / max(1, n)
    sig = sum(hist[40:]) / max(1, n) * 100
    rows.append((name, mean, sig))
    print(f"{name:<20}{mean:>9.2f}{sig:>13.2f}%")

overall = sum(i * c for i, c in enumerate(gray.histogram())) / (W * H)
print("-" * 45)
print(f"{'全图':<20}{overall:>9.2f}")

# 并排 + 热力图
heat = Image.merge("RGB", (
    gray.point(lambda v: min(255, v * 4)),
    gray.point(lambda v: min(255, max(0, v * 4 - 90))),
    gray.point(lambda v: 0),
))

sheet = Image.new("RGB", (W, H * 3 + 40), (16, 16, 20))
d = ImageDraw.Draw(sheet)
sheet.paste(official, (0, 0))
sheet.paste(render, (0, H + 20))
sheet.paste(heat, (0, H * 2 + 40))
d.text((8, H + 4), "RENDER (replica)", fill=(120, 220, 120))
d.text((8, H * 2 + 24), "DIFF HEATMAP", fill=(220, 160, 120))
d.text((8, 4), "OFFICIAL", fill=(120, 180, 255))
p = os.path.join(OUT, f"compare-{TAG}.png")
sheet.save(p)
print(f"\n对比图: {p}")
