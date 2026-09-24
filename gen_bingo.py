#!/usr/bin/env python3.11
# gen_bingo.py — 生成可打印宾果(Bingo)卡片游戏（A4 PDF）：N 张唯一 3×3 卡 + 主持人念词/句表
#
# 设计：每张卡中心为「FREE 自由」格；其余 8 格从词池随机抽 8 个不同词（每卡唯一）。
#       卡面 = 大 emoji + 英文词（图词并现，适合 5-12 岁）；主持人页列出全部词 + 可选 caller 句。
#       依赖：reportlab / Pillow（均已预装）；emoji 用 cairosvg 渲染 Twemoji，缺失则自动降级为灰圆。
#
# 用法:
#   词模式:  python3 gen_bingo.py words.tsv bingo.pdf --cards 4 --title "天气宾果"
#   带主持人句:  python3 gen_bingo.py words.tsv bingo.pdf --caller caller.tsv
#
# words.tsv 每行:  word <TAB> emoji_codepoint <TAB> 中文(可选) <TAB> 分类(可选)
#   例:  sunny  1f31e  晴朗的  形容词
# caller.tsv 每行:  word <TAB> caller_sentence(可选)
#   例:  sunny  It is sunny today.

import os, re, glob, math, sys, random, argparse
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

# ---- 跨平台字体自动探测（Debian/Ubuntu、Windows、macOS）----
def _first_exist(paths):
    for p in paths:
        if p and os.path.exists(p): return p
    return None
def _pick_fonts():
    dv = _first_exist([
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf",
        "/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf"])
    if not dv:
        g = sorted(glob.glob("/usr/share/fonts/**/DejaVuSans.ttf", recursive=True))
        dv = g[0] if g else None
    dvb = _first_exist([
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf",
        "/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial Bold.ttf"])
    if not dvb and dv: dvb = dv
    cjk = _first_exist([
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc"])
    if not cjk:
        for pat in ("/usr/share/fonts/**/*CJK*.tt[cf]", "/usr/share/fonts/**/wqy*.tt[cf]"):
            g = sorted(glob.glob(pat, recursive=True))
            if g: cjk = g[0]; break
    return dv, dvb, cjk
DV, DVB, CJK = _pick_fonts()
if not DV or not DVB or not CJK:
    print("[字体] 未找到所需字体：")
    if not DV or not DVB: print("  英文字体缺失（DejaVu / Arial / Helvetica 任一）")
    if not CJK: print("  中文字体缺失（Noto CJK / 微软雅黑 / 黑体 / 苹方 任一）")
    sys.exit(1)
pdfmetrics.registerFont(TTFont("DV", DV))
pdfmetrics.registerFont(TTFont("DVB", DVB))

A4W, A4H = A4
EMOJI_PX = 420
CJK_RE = re.compile(r'[\u3000-\u9fff\uff00-\uffef]')
_cjk_cache, _dv_cache = {}, {}
def cjk_font(size):
    if size not in _cjk_cache:
        _cjk_cache[size] = ImageFont.truetype(CJK, size, index=0)
    return _cjk_cache[size]
def dv_font(size, bold=True):
    k = (size, bold)
    if k not in _dv_cache:
        _dv_cache[k] = ImageFont.truetype(DVB if bold else DV, size)
    return _dv_cache[k]
def _rgb(col):
    return (int(col.red*255), int(col.green*255), int(col.blue*255)) if isinstance(col, colors.Color) else col
def _cjk_img(s, size, rgb):
    f = cjk_font(size); asc,_ = f.getmetrics()
    tmp = Image.new("RGBA",(10,10)); d = ImageDraw.Draw(tmp)
    bb = d.textbbox((0,0), s, font=f)
    w = math.ceil(bb[2]-bb[0]); h = math.ceil(bb[3]-bb[1])
    img = Image.new("RGBA",(w+6,h+6),(0,0,0,0))
    ImageDraw.Draw(img).text((3-bb[0],3-bb[1]), s, font=f, fill=(rgb[0],rgb[1],rgb[2],255))
    return img, w+6, h+6, 3-bb[1]+asc
def T(c, s, x, y, size, col=(0,0,0), align="l", bold=True):
    rgb = _rgb(col)
    if CJK_RE.search(s):
        img,w,h,bl = _cjk_img(s, size, rgb)
        xx = x if align=="l" else (x-w/2 if align=="c" else x-w)
        c.drawImage(ImageReader(img), xx, y-bl, w, h, mask="auto")
    else:
        c.setFillColor(colors.Color(rgb[0]/255,rgb[1]/255,rgb[2]/255))
        c.setFont("DVB" if bold else "DV", size)
        if align=="c": c.drawCentredString(x,y,s)
        elif align=="r": c.drawRightString(x,y,s)
        else: c.drawString(x,y,s)
def get_emoji(cp):
    """返回 Twemoji PNG 路径（本地缓存或下载栅格化），失败降级灰圆。"""
    cache = os.path.join("/tmp", f"bingo_emo_{cp}.png")
    if os.path.exists(cache) and os.path.getsize(cache) > 300: return cache
    try:
        import requests, cairosvg
        r = requests.get(f"https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/{cp}.svg", timeout=20)
        if r.status_code == 200:
            png = cairosvg.svg2png(bytestring=r.content, output_width=EMOJI_PX, output_height=EMOJI_PX)
            open(cache,"wb").write(png); return cache
    except Exception:
        pass
    im = Image.new("RGBA",(EMOJI_PX,EMOJI_PX),(0,0,0,0))
    ImageDraw.Draw(im).ellipse([10,10,EMOJI_PX-10,EMOJI_PX-10], fill=(228,228,228,255), outline=(170,170,170,255), width=8)
    im.save(cache); return cache
def emoji_img(cp):
    return Image.open(get_emoji(cp)).convert("RGBA")

def load_words(infile):
    words = []
    with open(infile, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip(): continue
            parts = line.split("\t")
            w = parts[0].strip()
            cp = parts[1].strip() if len(parts) > 1 else ""
            zh = parts[2].strip() if len(parts) > 2 else ""
            if w: words.append((w, cp, zh))
    return words

def load_caller(infile):
    m = {}
    if not infile: return m
    with open(infile, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip(): continue
            p = line.split("\t")
            w = p[0].strip(); s = p[1].strip() if len(p) > 1 else ""
            if w: m[w] = s
    return m

def build(words, out, n_cards=4, title="Bingo", caller=None, seed=2024):
    if len(words) < 8:
        print(f"[跳过] 词数 {len(words)} < 8，无法填满 3x3 卡（需 8 个不同词）"); sys.exit(1)
    random.seed(seed)
    # 生成 N 张唯一的 8 词组合
    combos = []
    tries = 0
    while len(combos) < n_cards and tries < n_cards*50:
        tries += 1
        pool = words[:]; random.shuffle(pool)
        pick = tuple(p[0] for p in pool[:8])
        if pick not in combos: combos.append(pick)
    if len(combos) < n_cards:
        print(f"[警告] 仅生成 {len(combos)} 张唯一卡（词池较小）")

    c = canvas.Canvas(out, pagesize=A4)
    def draw_card(grid, x0, y0, size, accent):
        T(c, f"{title} · 听一听，划一划", x0, y0+size+10, 12, accent)
        cs = size/3
        order = [grid[0],grid[1],grid[2],grid[3],"__FREE__",grid[4],grid[5],grid[6],grid[7]]  # 中心 FREE
        for idx, cell in enumerate(order):
            r, cc = divmod(idx, 3)
            cx = x0 + cc*cs; cy = y0 + (2-r)*cs
            c.setStrokeColor(colors.black); c.setLineWidth(1.4)
            c.rect(cx, cy, cs, cs, fill=0, stroke=1)
            if cell == "__FREE__":
                c.setFillColor(accent); c.rect(cx, cy, cs, cs, fill=1, stroke=0)
                T(c, "FREE", cx+cs/2, cy+cs/2+6, 16, (255,255,255), align="c", bold=True)
                T(c, "自由", cx+cs/2, cy+cs/2-12, 10, (255,255,255), align="c")
                continue
            w, cp, zh = cell
            im = emoji_img(cp); d = cs*0.52
            c.drawImage(ImageReader(im), cx+(cs-d)/2, cy+(cs-d)/2+6, d, d, mask="auto")
            T(c, w, cx+cs/2, cy+9, 10, (0,0,0), align="c")
    size, gap = 248, 28
    slots = [(35, 470), (35+size+gap, 470), (35, 90), (35+size+gap, 90)]  # 2×2，每页 4 卡
    accent = colors.HexColor("#e8923a")
    for i, combo in enumerate(combos):
        if i and i % 4 == 0:
            c.showPage()
        grid = [(w,cp,zh) for (w,cp,zh) in words if w in combo]
        draw_card(grid, slots[i%4][0], slots[i%4][1], size, accent)
    c.showPage()

    # 主持人页：列出全部词 + emoji + 可选 caller 句
    T(c, f"{title} · 主持人页 Caller Sheet", 40, A4H-50, 18, accent)
    T(c, "念出句子/词，孩子划掉对应天气，连成一线喊 Bingo！", 40, A4H-76, 11, (0,0,0))
    y = A4H-118
    for (w, cp, zh) in words:
        im = emoji_img(cp); c.drawImage(ImageReader(im), 48, y-34, 40, 40, mask="auto")
        T(c, w, 108, y-12, 14, (0,0,0))
        sent = caller.get(w, "") if caller else ""
        if sent:
            T(c, sent, 108, y-30, 9, (90,90,90))
        y -= 52
        if y < 80:
            c.showPage(); y = A4H-60
    c.showPage(); c.save()
    print(f"wrote {out}  cards={len(combos)}  words={len(words)}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("words"); ap.add_argument("out")
    ap.add_argument("--cards", type=int, default=4)
    ap.add_argument("--title", default="Bingo")
    ap.add_argument("--caller", default=None)
    ap.add_argument("--seed", type=int, default=2024)
    a = ap.parse_args()
    words = load_words(a.words)
    caller = load_caller(a.caller) if a.caller else None
    build(words, a.out, a.cards, a.title, caller, a.seed)
