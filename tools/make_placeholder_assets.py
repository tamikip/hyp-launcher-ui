"""为公开仓库生成一整套中性占位素材（无版权问题）。

配色走中性的冷灰蓝，不蹭任何品牌色：
    底   #12141a -> #1f2533
    主色 #4ea1ff（蓝）
    辅色 #7ee0c0（薄荷）
    浅   #e8edf5

产出同名文件覆盖 src/assets，让现有 config 基本不用改；
顶栏/窗口按钮/chip 这些按原尺寸生成，保证布局不变。

用法:
    python make_placeholder_assets.py            # 生成全部
    python make_placeholder_assets.py bg icon    # 只生成指定的
"""

import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

P = r"F:\新建文件夹\hoyo-launcher-clone"
A = os.path.join(P, r"src\assets")
IMG = os.path.join(A, "img")
ICON = os.path.join(A, "icons")
HUB = os.path.join(IMG, "hub")

random.seed(20261008)
rnd = random.Random(20261008)

# ---------------- 配色 ----------------
DARK0 = (18, 20, 26)
DARK1 = (31, 37, 51)
BLUE = (78, 161, 255)
MINT = (126, 224, 192)
LIGHT = (232, 237, 245)
WHITE = (255, 255, 255)
GRAY = (150, 160, 178)

FONTS = [r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc",
         r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\segoeui.ttf",
         r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"]


def font(size):
    for f in FONTS:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ---------------- 基础工具 ----------------
def vgrad(size, stops):
    w, h = size
    ys = np.linspace(0, 1, h)
    arr = np.zeros((h, 3))
    pos = [s[0] for s in stops]
    for c in range(3):
        arr[:, c] = np.interp(ys, pos, [s[1][c] for s in stops])
    return Image.fromarray(np.repeat(arr[:, None, :], w, axis=1).astype(np.uint8), "RGB")


def glow(size, center, radius, color, strength=1.0, power=2.0):
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - center[0]) ** 2 + (yy - center[1]) ** 2) / max(radius, 1)
    a = np.clip(1 - d, 0, 1) ** power * strength
    out = np.zeros((h, w, 3))
    for c in range(3):
        out[:, :, c] = a * color[c]
    return out


def screen(base, g):
    a, b = base / 255.0, g / 255.0
    return np.clip((1 - (1 - a) * (1 - b)) * 255, 0, 255)


def grain(size, amount=5):
    w, h = size
    n = np.random.normal(0, amount, (h, w, 1))
    return np.repeat(n, 3, axis=2)


def vignette(im, strength=0.5, power=1.5):
    w, h = im.size
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    m = np.clip(1 - strength * np.clip(d - 0.35, 0, None) ** power, 0, 1)
    return Image.fromarray(np.clip(np.asarray(im, dtype=float) * m[:, :, None], 0, 255)
                           .astype(np.uint8), "RGB")


def hexagons(im, count, color, alpha=10):
    """一层淡淡的六边形网格，代替"原画"的肌理。"""
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    w, h = im.size
    r = max(w, h) // 22
    for _ in range(count):
        cx = rnd.uniform(-r, w + r)
        cy = rnd.uniform(-r, h + r)
        pts = [(cx + r * math.cos(math.radians(60 * i + 30)),
                cy + r * math.sin(math.radians(60 * i + 30))) for i in range(6)]
        d.polygon(pts, outline=color + (alpha,), width=2)
    return Image.alpha_composite(im.convert("RGBA"), lay).convert("RGB")


def build_bg(path, variant=0):
    W, H = 2560, 1440
    stops = [
        (0.00, DARK1 if variant % 2 else DARK0),
        (0.42, (36, 46, 66) if variant % 2 else (26, 32, 46)),
        (0.72, (24, 30, 44)),
        (1.00, DARK0),
    ]
    im = vgrad((W, H), stops)
    arr = np.asarray(im, dtype=float)
    # 两个光斑，位置按 variant 变化
    cx = (0.30, 0.62, 0.44, 0.72)[variant % 4] * W
    arr = screen(arr, glow((W, H), (cx, H * 0.28), W * 0.46, BLUE, 0.30, 2.2))
    arr = screen(arr, glow((W, H), (W * 0.18, H * 0.80), W * 0.40, MINT, 0.12, 2.4))
    arr += grain((W, H), 4)
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    im = hexagons(im, 26, (255, 255, 255), 12)
    im = vignette(im, 0.55, 1.5)
    im.save(path, "WEBP", quality=88, method=6)
    return im


def build_title(path):
    """标题叠层：一个中性的 DEMO 字标，让版式能看出来。"""
    W, H = 2560, 1440
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x, y = 256, 300
    f1 = font(150)
    f2 = font(50)
    for off, col in [(6, (0, 0, 0, 160)), (0, WHITE + (255,))]:
        d.text((x + off, y + off), "DEMO", font=f1, fill=col)
    w1 = d.textlength("DEMO", font=f1)
    for off, col in [(6, (0, 0, 0, 160)), (0, BLUE + (255,))]:
        d.text((x + w1 + 12 + off, y + off), "GAME", font=f1, fill=col)
    w2 = d.textlength("GAME", font=f1)
    uy = y + 176
    d.line([(x, uy), (x + w1 + 12 + w2, uy)], fill=MINT + (230,), width=5)
    d.text((x + 4, uy + 26), "示例游戏  ·  v1.0.0", font=f2, fill=LIGHT + (240,))
    im.save(path)
    return im


def build_vignette(path):
    """暗角遮罩：纯黑 + alpha，和之前那层一样的作用（压暗边缘保证文字可读）。"""
    W, H = 2560, 1440
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    a = np.clip(0.42 * np.clip(d - 0.42, 0, None) ** 1.5, 0, 0.8)
    img = Image.fromarray((a * 255).astype(np.uint8), "L")
    img = img.filter(ImageFilter.GaussianBlur(8))
    rgba = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    rgba.putalpha(img)
    rgba.save(path, optimize=True)


# ---------------- 图标（用 PIL 基本图元画） ----------------
def canvas(size, bg=None, radius=0):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if bg:
        d = ImageDraw.Draw(im)
        if radius:
            d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=bg)
        else:
            d.rectangle([0, 0, size - 1, size - 1], fill=bg)
    return im


def glyph(im, kind, color, scale=1.0, cx=None, cy=None):
    """在 im 上画一个白色线条图形（简单但可辨识）。"""
    S = im.size[0]
    cx = S / 2 if cx is None else cx
    cy = S / 2 if cy is None else cy
    r = S * 0.30 * scale
    d = ImageDraw.Draw(im)
    w = max(2, int(S * 0.075 * scale))

    if kind == "chat":
        d.rounded_rectangle([cx - r, cy - r * 0.8, cx + r, cy + r * 0.45],
                            radius=S * 0.09, outline=color, width=w)
        d.polygon([(cx - r * 0.3, cy + r * 0.42), (cx - r * 0.05, cy + r * 0.42),
                   (cx - r * 0.35, cy + r * 0.85)], fill=color)
        for i in (-1, 0, 1):
            d.ellipse([cx + i * r * 0.42 - S * 0.03, cy - r * 0.2 - S * 0.03,
                       cx + i * r * 0.42 + S * 0.03, cy - r * 0.2 + S * 0.03], fill=color)
    elif kind == "book":
        d.rounded_rectangle([cx - r, cy - r * 0.85, cx - S * 0.02, cy + r * 0.85],
                            radius=S * 0.04, outline=color, width=w)
        d.rounded_rectangle([cx + S * 0.02, cy - r * 0.85, cx + r, cy + r * 0.85],
                            radius=S * 0.04, outline=color, width=w)
        d.line([(cx, cy - r * 0.85), (cx, cy + r * 0.85)], fill=color, width=w)
    elif kind == "help":
        d.arc([cx - r * 0.6, cy - r * 0.95, cx + r * 0.6, cy + r * 0.1],
              start=170, end=380, fill=color, width=w)
        d.line([(cx + r * 0.52, cy - r * 0.42), (cx, cy + r * 0.16)], fill=color, width=w)
        d.ellipse([cx - S * 0.045, cy + r * 0.42, cx + S * 0.045, cy + r * 0.42 + S * 0.09],
                  fill=color)
    elif kind == "gear":
        d.ellipse([cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62],
                  outline=color, width=w)
        for i in range(8):
            a = math.radians(i * 45)
            x1 = cx + math.cos(a) * r * 0.62
            y1 = cy + math.sin(a) * r * 0.62
            x2 = cx + math.cos(a) * r * 0.95
            y2 = cy + math.sin(a) * r * 0.95
            d.line([(x1, y1), (x2, y2)], fill=color, width=w)
    elif kind == "headset":
        d.arc([cx - r, cy - r * 1.05, cx + r, cy + r * 0.75], start=180, end=360,
              fill=color, width=w)
        d.rounded_rectangle([cx - r, cy + r * 0.05, cx - r * 0.6, cy + r * 0.72],
                            radius=S * 0.05, fill=color)
        d.rounded_rectangle([cx + r * 0.6, cy + r * 0.05, cx + r, cy + r * 0.72],
                            radius=S * 0.05, fill=color)
    elif kind == "user":
        d.ellipse([cx - r * 0.42, cy - r * 0.85, cx + r * 0.42, cy - r * 0.05],
                  outline=color, width=w)
        d.arc([cx - r * 0.85, cy + r * 0.05, cx + r * 0.85, cy + r * 1.35],
              start=200, end=340, fill=color, width=w)
    elif kind == "star":
        pts = []
        for i in range(10):
            a = math.radians(-90 + i * 36)
            rr = r * (0.95 if i % 2 == 0 else 0.42)
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        d.polygon(pts, fill=color)
    elif kind == "play":
        d.polygon([(cx - r * 0.55, cy - r * 0.85), (cx + r * 0.85, cy),
                   (cx - r * 0.55, cy + r * 0.85)], fill=color)
    elif kind == "download":
        d.line([(cx, cy - r * 0.9), (cx, cy + r * 0.35)], fill=color, width=w)
        d.polygon([(cx - r * 0.55, cy + r * 0.2), (cx + r * 0.55, cy + r * 0.2),
                   (cx, cy + r * 0.95)], fill=color)
        d.line([(cx - r * 0.8, cy + r * 1.1), (cx + r * 0.8, cy + r * 1.1)],
               fill=color, width=w)
    elif kind == "shield":
        d.polygon([(cx, cy - r), (cx + r * 0.85, cy - r * 0.55),
                   (cx + r * 0.85, cy + r * 0.15), (cx, cy + r * 1.0),
                   (cx - r * 0.85, cy + r * 0.15), (cx - r * 0.85, cy - r * 0.55)],
                  outline=color, width=w)
    elif kind == "mail":
        d.rounded_rectangle([cx - r, cy - r * 0.66, cx + r, cy + r * 0.66],
                            radius=S * 0.05, outline=color, width=w)
        d.line([(cx - r, cy - r * 0.6), (cx, cy + r * 0.12)], fill=color, width=w)
        d.line([(cx + r, cy - r * 0.6), (cx, cy + r * 0.12)], fill=color, width=w)
    return im


SOCIAL_KINDS = ["chat", "mail", "star", "book", "shield", "user", "help", "headset"]


def build_rail_and_social():
    """侧栏/社交栏用的白色线条图标：72x72（显示 36x36）与 1:1 的小图。"""
    # social-01..08 + social-inline-14（72x72）
    for i, kind in enumerate(SOCIAL_KINDS, 1):
        im = canvas(72)
        glyph(im, kind, WHITE + (255,), scale=1.0)
        im.save(os.path.join(ICON, f"social-{i:02d}.png"))
    im = canvas(72)
    glyph(im, "play", WHITE + (255,), scale=0.9)
    im.save(os.path.join(ICON, "social-inline-14.png"))

    # rail-01..09（同名保留，内容同 social）
    for i, kind in enumerate(SOCIAL_KINDS + ["play"], 1):
        im = canvas(72)
        glyph(im, kind, WHITE + (255,), scale=1.0)
        im.save(os.path.join(ICON, f"rail-{i:02d}.png"))


def build_window_icons():
    # 设置（官方 20x21）
    im = canvas(20)
    glyph(im, "gear", WHITE + (255,), scale=1.15)
    im.save(os.path.join(ICON, "win-settings.png"))

    # 最小化（16x4）
    im = canvas(16)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 1, 15, 3], fill=WHITE + (255,))
    im.save(os.path.join(ICON, "win-minimize.png"))

    # 关闭（14x14）
    im = canvas(14)
    d = ImageDraw.Draw(im)
    d.line([(1, 1), (12, 12)], fill=WHITE + (255,), width=2)
    d.line([(12, 1), (1, 12)], fill=WHITE + (255,), width=2)
    im.save(os.path.join(ICON, "win-close.png"))

    # 宫格按钮（显示 22x22，给 44x44）
    im = canvas(44)
    d = ImageDraw.Draw(im)
    for r in range(2):
        for c in range(2):
            x = 4 + c * 20
            y = 4 + r * 20
            d.rounded_rectangle([x, y, x + 16, y + 16], radius=3, fill=WHITE + (240,))
    im.save(os.path.join(ICON, "btn-grid.png"))

    # CTA 箭头（蒙版，显示 17x17，给 34x34）
    im = canvas(34)
    d = ImageDraw.Draw(im)
    d.polygon([(9, 6), (26, 17), (9, 28)], fill=WHITE + (255,))
    im.save(os.path.join(ICON, "cta-arrow.png"))


def build_logo():
    """中性品牌标：六边形 + 内嵌折角。SVG 与 PNG 都给。"""
    S = 176
    im = canvas(S, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cy = S / 2
    r = S * 0.44
    pts = [(cx + r * math.cos(math.radians(60 * i + 30)),
            cy + r * math.sin(math.radians(60 * i + 30))) for i in range(6)]
    d.polygon(pts, fill=WHITE + (255,))
    inner = [(cx + r * 0.52 * math.cos(math.radians(60 * i + 30)),
              cy + r * 0.52 * math.sin(math.radians(60 * i + 30))) for i in range(6)]
    d.polygon(inner, fill=(18, 20, 26, 255))
    d.line([(cx - r * 0.26, cy + r * 0.18), (cx, cy - r * 0.30),
            (cx + r * 0.26, cy + r * 0.18)], fill=WHITE + (255,), width=int(S * 0.045),
           joint="curve")
    im.resize((176, 176), Image.LANCZOS).save(os.path.join(ICON, "logo.png"))
    im.resize((88, 88), Image.LANCZOS).save(os.path.join(ICON, "logo-app.png"))

    svg = (
        '<svg width="44" height="44" viewBox="0 0 44 44" fill="none" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<path d="M22 2.2 38.6 11.6v20.8L22 41.8 5.4 32.4V11.6z" fill="#fff"/>'
        '<path d="M22 11.2 30.1 15.9v9.4L22 30 13.9 25.3v-9.4z" fill="#12141a"/>'
        '<path d="M17.4 24.4 22 18.6l4.6 5.8" stroke="#fff" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        '</svg>')
    open(os.path.join(ICON, "logo-app.svg"), "w", encoding="utf-8").write(svg)


GAME_COLORS = [
    (78, 161, 255), (126, 224, 192), (255, 176, 92), (196, 140, 255), (255, 122, 145),
]


def build_game_icons():
    """5 个游戏图标（96x96）：不同色相的圆角方块 + 一个字符。"""
    letters = ["A", "B", "C", "D", "E"]
    for i, (col, ch) in enumerate(zip(GAME_COLORS, letters)):
        S = 96
        im = canvas(S, (0, 0, 0, 0), radius=22)
        d = ImageDraw.Draw(im)
        # 渐变底
        grad = Image.new("RGB", (S, S))
        px = grad.load()
        for y in range(S):
            for x in range(S):
                t = (x / S * 0.5 + y / S * 0.5)
                px[x, y] = (int(col[0] * (0.55 + 0.45 * (1 - t))),
                            int(col[1] * (0.55 + 0.45 * (1 - t))),
                            int(col[2] * (0.55 + 0.45 * (1 - t))))
        grad = grad.convert("RGBA")
        mask = Image.new("L", (S, S), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=22, fill=255)
        bg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        bg.paste(grad, (0, 0), mask)
        im = bg
        d = ImageDraw.Draw(im)
        f = font(52)
        w = d.textlength(ch, font=f)
        d.text(((S - w) / 2, S / 2 - 32), ch, font=f, fill=(255, 255, 255, 245))
        im.save(os.path.join(ICON, f"icon-{['hkrpg','hk4e','bh3','nap','hyg'][i]}.png"))

    # 兼容旧名
    for src, dst in [("icon-hkrpg.png", "icon-a.png")]:
        pass


def build_hub_land_logos():
    """Hub 落地 logo（420x320 RGBA）：字标 + 一句说明。"""
    names = ["DEMO GAME", "DEMO GAME II", "DEMO GAME III", "DEMO GAME IV", "DEMO GAME V"]
    keys = ["hkrpg", "hk4e", "bh3", "nap", "hyg"]
    for key, nm in zip(keys, names):
        W, H = 840, 640
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        f1 = font(96)
        f2 = font(38)
        for off, col in [(6, (0, 0, 0, 150)), (0, WHITE + (255,))]:
            d.text((14 + off, 60 + off), nm, font=f1, fill=col)
        w = d.textlength(nm, font=f1)
        d.line([(16, 196), (16 + w, 196)], fill=MINT + (235,), width=5)
        d.text((16, 218), "示例作品  ·  Sample Studio", font=f2, fill=LIGHT + (235,))
        im.save(os.path.join(ICON, f"hub-land-logo-{key}.png"))


def build_hub_cards():
    """Hub 卡片图（288x288 圆角）：渐变色块 + 文字。"""
    names = ["示例作品 A", "示例作品 B", "示例作品 C", "示例作品 D", "示例作品 E", "示例作品 F"]
    files = ["hkrpg", "xingbugudi", "yinyuan", "zzz", "genshin", "honkai3"]
    for i, (f, nm) in enumerate(zip(files, names)):
        S = 288
        col = GAME_COLORS[i % len(GAME_COLORS)]
        base = vgrad((S, S), [(0, tuple(min(255, c + 20) for c in col)),
                              (0.55, col), (1, tuple(int(c * 0.42) for c in col))])
        arr = np.asarray(base, dtype=float)
        arr = screen(arr, glow((S, S), (S * 0.72, S * 0.26), S * 0.6, WHITE, 0.22, 2.0))
        arr += grain((S, S), 4)
        base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        d = ImageDraw.Draw(base)
        ft = font(30)
        w = d.textlength(nm, font=ft)
        d.text(((S - w) / 2, S * 0.44), nm, font=ft, fill=(255, 255, 255, 250))
        d.text((S * 0.5 - 34, S * 0.58), "SAMPLE", font=font(16), fill=(255, 255, 255, 170))
        mask = Image.new("L", (S, S), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=28, fill=255)
        base.putalpha(mask)
        base.save(os.path.join(HUB, f"card-{f}.png"))
        # 源画（同图不裁圆角），给 config 的 art 字段兜底
        base.save(os.path.join(HUB, f"art-{f}.png"))
        # logo 叠层
        ov = Image.new("RGBA", (416, 234), (0, 0, 0, 0))
        dd = ImageDraw.Draw(ov)
        f2 = font(46)
        w2 = dd.textlength(nm, font=f2)
        dd.text(((416 - w2) / 2, 96), nm, font=f2, fill=(255, 255, 255, 250))
        ov.save(os.path.join(HUB, f"logo-{f}.png"))

    # 旧名兼容：logo-overlay-yinyuan / logo-hkrpg 等已在上面覆盖
    for k in ["hkrpg", "hk4e", "bh3", "nap", "hyg"]:
        src = os.path.join(HUB, f"logo-{k}.png")
        if os.path.exists(src):
            pass


def build_carousel():
    """活动轮播（768x356）：中性渐变 + 编号。"""
    labels = ["示例活动 01", "示例活动 02", "示例活动 03", "示例活动 04"]
    for i, nm in enumerate(labels, 1):
        W, H = 768, 356
        col = GAME_COLORS[(i - 1) % len(GAME_COLORS)]
        base = vgrad((W, H), [(0, tuple(min(255, c + 26) for c in col)),
                              (0.55, col), (1, tuple(int(c * 0.45) for c in col))])
        arr = np.asarray(base, dtype=float)
        arr = screen(arr, glow((W, H), (W * 0.78, H * 0.24), W * 0.55, WHITE, 0.28, 2.0))
        arr += grain((W, H), 4)
        base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
        base = hexagons(base, 10, (255, 255, 255), 14)
        d = ImageDraw.Draw(base)
        d.text((40, 118), nm, font=font(46), fill=(255, 255, 255, 252))
        d.text((42, 184), "这里是活动说明占位文字", font=font(24), fill=(255, 255, 255, 210))
        d.line([(42, 168), (42 + 210, 168)], fill=MINT + (230,), width=3)
        base.save(os.path.join(IMG, f"card-banner-{i}.png"))

    # 兼容旧命名（config 里引用的是 card-xxx）
    legacy = ["card-webactivity-mihayou.png", "card-ver46-feature.jpg", "card-zhichi-art.png",
              "card-zhenli-pv.jpg", "card-zoujin-xingqiong.png", "card-zhenli-preview.png",
              "card-aha-aeon.png"]
    for i, name in enumerate(legacy, 1):
        src = os.path.join(IMG, f"card-banner-{((i - 1) % 4) + 1}.png")
        if os.path.exists(src):
            Image.open(src).save(os.path.join(IMG, name))


def build_chips():
    """chip 两态（270x80）：常态白底、悬停灰底。"""
    for label, name in [("示例热点", "chip-info"), ("查看活动", "chip-activity")]:
        for hover, suffix in [(False, ""), (True, "-hover")]:
            W, H = 270, 80
            im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            bg = (233, 233, 233, 255) if hover else (255, 255, 255, 255)
            d.rounded_rectangle([0, 0, W - 1, H - 1], radius=H // 2, fill=bg)
            f = font(34)
            w = d.textlength(label, font=f)
            d.text(((W - w) / 2, H / 2 - 22), label, font=f, fill=(22, 23, 26, 255))
            im.save(os.path.join(IMG, f"{name}{suffix}.png"))


def build_qr():
    """占位二维码（纯装饰）。"""
    for i in range(1, 6):
        S = 320
        im = Image.new("RGB", (S, S), (255, 255, 255))
        d = ImageDraw.Draw(im)
        cell = 10
        for y in range(0, S, cell):
            for x in range(0, S, cell):
                if rnd.random() < 0.45:
                    d.rectangle([x, y, x + cell - 1, y + cell - 1], fill=(20, 22, 28))
        # 三个定位角
        for ox, oy in [(20, 20), (S - 100, 20), (20, S - 100)]:
            d.rectangle([ox, oy, ox + 70, oy + 70], fill=(255, 255, 255))
            d.rectangle([ox + 8, oy + 8, ox + 62, oy + 62], fill=(20, 22, 28))
            d.rectangle([ox + 20, oy + 20, ox + 50, oy + 50], fill=(255, 255, 255))
        im.save(os.path.join(IMG, f"qr-{i:02d}.png"))


# ---------------- 入口 ----------------
ONLY = [a.lower() for a in sys.argv[1:]]


def want(k):
    return (not ONLY) or (k in ONLY)


print("生成中性占位素材 ->", A)
if want("bg"):
    for i in range(3):
        build_bg(os.path.join(IMG, f"bg-{i + 1:02d}.webp"), i)
        print(f"  bg-{i + 1:02d}.webp")
    build_bg(os.path.join(IMG, "bg-hub.webp"), 4)
    build_bg(os.path.join(IMG, "bg-hub-02.webp"), 5)
    # 兼容 config.js 里现有的文件名
    import shutil
    for src, dst in [("bg-01.webp", "bg-canghai.webp"),
                     ("bg-01.webp", "bg-hkrpg-keyart.webp"),
                     ("bg-03.webp", "bg-launcher-hkrpg.webp"),
                     ("bg-hub.webp", "bg-hub-official.webp")]:
        s = os.path.join(IMG, src)
        if os.path.exists(s):
            shutil.copy2(s, os.path.join(IMG, dst))
    for i in range(1, 6):
        if os.path.exists(os.path.join(IMG, f"bg-{(i % 3) + 1:02d}.webp")):
            shutil.copy2(os.path.join(IMG, f"bg-{(i % 3) + 1:02d}.webp"),
                         os.path.join(IMG, f"bg-hub-alt{i}.webp"))
    print("  兼容旧名完成")

if want("title"):
    build_title(os.path.join(IMG, "overlay-launcher-title.png"))
    build_title(os.path.join(IMG, "overlay-launcher-title.webp")) if False else None
    # config 引用的是 .webp，转一份
    Image.open(os.path.join(IMG, "overlay-launcher-title.png")).save(
        os.path.join(IMG, "overlay-launcher-title.webp"), "WEBP", quality=90)
    print("  overlay-launcher-title")

if want("vignette"):
    build_vignette(os.path.join(IMG, "bg-vignette.png"))
    print("  bg-vignette.png")

if want("icon"):
    build_rail_and_social()
    build_window_icons()
    build_logo()
    build_game_icons()
    build_hub_land_logos()
    print("  图标类完成")

if want("card"):
    build_hub_cards()
    build_carousel()
    print("  卡片 / 轮播完成")

if want("chip"):
    build_chips()
    print("  chip 两态完成")

if want("qr"):
    build_qr()
    print("  qr 占位完成")

print("完成")
