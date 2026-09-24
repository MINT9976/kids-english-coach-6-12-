#!/usr/bin/env python3.11
# gen_printables.py — 生成主题全套可打印 PDF 教具（9 份），由词表驱动、主题无关。
#
# 产出（默认文件名）:
#   00_使用说明.pdf        使用说明 + 玩法 + 点读指引
#   01_单词卡_Flashcards.pdf   图+词 对照卡（按分类色条）
#   02_分类涂色卡.pdf          分类认读/涂色卡
#   03_宾果卡_Bingo.pdf        宾果游戏卡（调用同目录 gen_bingo.py）
#   04_迷你书_MiniBook.pdf     8 页折叠小书
#   05_海报模板_Poster.pdf     综合展示海报
#   06_图卡_PictureCards.pdf   纯图卡（图词分离游戏）
#   07_词卡_WordCards.pdf      纯词卡（图词分离游戏）
#   08_点读指引卡.pdf          音频点读页使用指引（指向自包含 HTML）
#
# 用法:
#   python3 gen_printables.py words.tsv --title "天气" --outdir OUT [--caller caller.tsv]
#
# 依赖: reportlab / Pillow（已预装）；emoji 用 cairosvg 渲染 Twemoji（缺失自动降级灰圆）。
#       宾果子步骤依赖同目录 gen_bingo.py。

import os, re, glob, math, sys, subprocess, argparse
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
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
PALETTE = ["#e8607d","#3b8ec2","#5aa469","#e8923a","#8a6fc4",
           "#d96ba8","#4fb0c6","#c9a227","#7a8b3c","#b5651d"]
GEN_BINGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen_bingo.py")

CJK_RE = re.compile(r'[\u3000-\u9fff\uff00-\uffef]')
_cjk_cache, _dv_cache = {}, {}
def cjk_font(size):
    if size not in _cjk_cache:
        _cjk_cache[size] = ImageFont.truetype(CJK, size, index=0)
    return _cjk_cache[size]
def dv_font(size, bold=True):
    k=(size,bold)
    if k not in _dv_cache:
        _dv_cache[k]=ImageFont.truetype(DVB if bold else DV, size)
    return _dv_cache[k]
def _rgb(col):
    return (int(col.red*255),int(col.green*255),int(col.blue*255)) if isinstance(col,colors.Color) else col
def _cjk_img(s,size,rgb):
    f=cjk_font(size); asc,_=f.getmetrics()
    tmp=Image.new("RGBA",(10,10)); d=ImageDraw.Draw(tmp)
    bb=d.textbbox((0,0),s,font=f)
    w=math.ceil(bb[2]-bb[0]); h=math.ceil(bb[3]-bb[1])
    img=Image.new("RGBA",(w+6,h+6),(0,0,0,0))
    ImageDraw.Draw(img).text((3-bb[0],3-bb[1]),s,font=f,fill=(rgb[0],rgb[1],rgb[2],255))
    return img,w+6,h+6,3-bb[1]+asc
def T(c,s,x,y,size,col=(0,0,0),align="l",bold=True):
    rgb=_rgb(col)
    if CJK_RE.search(s):
        img,w,h,bl=_cjk_img(s,size,rgb)
        xx=x if align=="l" else (x-w/2 if align=="c" else x-w)
        c.drawImage(ImageReader(img),xx,y-bl,w,h,mask="auto")
    else:
        c.setFillColor(colors.Color(rgb[0]/255,rgb[1]/255,rgb[2]/255))
        c.setFont("DVB" if bold else "DV",size)
        if align=="c": c.drawCentredString(x,y,s)
        elif align=="r": c.drawRightString(x,y,s)
        else: c.drawString(x,y,s)
def get_emoji(cp):
    cache=os.path.join("/tmp",f"prn_emo_{cp}.png")
    if os.path.exists(cache) and os.path.getsize(cache)>300: return cache
    try:
        import requests, cairosvg
        r=requests.get(f"https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/{cp}.svg",timeout=20)
        if r.status_code==200:
            png=cairosvg.svg2png(bytestring=r.content,output_width=EMOJI_PX,output_height=EMOJI_PX)
            open(cache,"wb").write(png); return cache
    except Exception: pass
    im=Image.new("RGBA",(EMOJI_PX,EMOJI_PX),(0,0,0,0))
    ImageDraw.Draw(im).ellipse([10,10,EMOJI_PX-10,EMOJI_PX-10],fill=(228,228,228,255),outline=(170,170,170,255),width=8)
    im.save(cache); return cache
def emoji_img(cp):
    if not cp: 
        im=Image.new("RGBA",(200,200),(0,0,0,0)); return im
    return Image.open(get_emoji(cp)).convert("RGBA")
def to_lineart(im):
    """全彩 emoji → 涂色线稿：白色内部 + 深灰轮廓线与特征线（蜡笔可涂）"""
    big=im.convert("RGBA")
    bg=Image.new("RGBA",big.size,(255,255,255,255))
    flat=Image.alpha_composite(bg,big).convert("L")
    a=big.split()[3]
    # 1) 剪影轮廓带（MaxFilter 膨胀 − MinFilter 腐蚀），保证外形闭合、线宽适合蜡笔
    band=ImageChops.subtract(a.filter(ImageFilter.MaxFilter(9)),
                             a.filter(ImageFilter.MinFilter(5)))
    band=band.point(lambda p:255 if p>40 else 0)
    # 2) 内部特征线（五官、云层分界等），只保留图形内部
    det=flat.filter(ImageFilter.FIND_EDGES).point(lambda p:255 if p>80 else 0)
    det=ImageChops.multiply(det, a.point(lambda p:255 if p>128 else 0))
    lines=ImageChops.lighter(band,det)
    out=Image.new("RGBA",big.size,(255,255,255,255))
    ink=Image.new("RGBA",big.size,(45,45,45,255))
    return Image.composite(ink,out,lines)
def lineart_img(cp):
    im=emoji_img(cp)
    return to_lineart(im) if im.size[0]>2 else im
def footer(c, foot):
    T(c, foot, A4W/2, 14, 8, (120,120,120), align="c", bold=False)

def ensure_deps():
    missing=[]
    try:
        import reportlab  # noqa
    except Exception:
        missing.append("reportlab")
    try:
        import PIL  # noqa
    except Exception:
        missing.append("pillow")
    try:
        import cairosvg  # noqa
    except Exception:
        missing.append("cairosvg")
    if not missing: return
    print(f"[依赖] 缺失: {', '.join(missing)}")
    if sys.platform.startswith("linux") and os.geteuid()==0:
        try:
            print("[依赖] 以 root 身份尝试安装…")
            subprocess.run(["pip3","install","-q"]+missing,check=True,capture_output=True,timeout=300)
            print("[依赖] 安装成功 ✅"); return
        except Exception as e:
            print(f"[依赖] 安装失败: {e}")
    print("[依赖] 请先安装: pip install " + " ".join(missing))
    sys.exit(1)

# ---------------- 词表解析 ----------------
def load_cats(words_tsv):
    order=[]; d={}
    with open(words_tsv, encoding="utf-8-sig") as f:
        for line in f:
            p=line.rstrip("\n").split("\t")
            if len(p)<4: continue
            w,cp,zh,cat=p[0].strip(),p[1].strip(),p[2].strip(),p[3].strip()
            if not w: continue
            if cat not in d: d[cat]=[]; order.append(cat)
            d[cat].append((w,cp,zh))
    return [(c, d[c]) for c in order]

# ---------------- 1) 单词卡 ----------------
def make_flashcards(out, cats):
    c=canvas.Canvas(out, pagesize=A4)
    for ci,(cat,items) in enumerate(cats):
        col=colors.HexColor(PALETTE[ci%len(PALETTE)])
        for pi in range(0,len(items),6):
            page=items[pi:pi+6]
            c.setFillColor(col); c.rect(0,A4H-38,A4W,38,fill=1,stroke=0)
            T(c, cat, 16, A4H-20, 16, (255,255,255))
            T(c, "cut along dashed lines 沿虚线剪下", A4W-14, A4H-20, 9, (255,255,255), align="r", bold=False)
            cols,rows=2,3; mx,my=18,18
            cw=(A4W-2*mx)/cols; ch=(A4H-34-2*my)/rows
            c.setStrokeColor(colors.HexColor("#cccccc")); c.setDash(3,3); c.setLineWidth(0.6)
            for i in range(cols+1): c.line(mx+i*cw,my,mx+i*cw,A4H-34-my)
            for j in range(rows+1): c.line(mx,my+j*ch,A4W-mx,my+j*ch)
            c.setDash()
            for idx,(word,cp,zh) in enumerate(page):
                r,cc=divmod(idx,cols)
                x0=mx+cc*cw; y0=A4H-34-my-(r+1)*ch; pad=10
                c.setStrokeColor(col); c.setLineWidth(2.5)
                c.roundRect(x0+pad,y0+pad,cw-2*pad,ch-2*pad,14,fill=0,stroke=1)
                im=emoji_img(cp); d=ch*0.5
                c.drawImage(ImageReader(im),x0+(cw-d)/2,y0+ch-pad-d-6,d,d,mask="auto")
                T(c, word, x0+cw/2, y0+pad+16, 22, (34,34,34), align="c")
            footer(c, "Kids English Coach · Printables"); c.showPage()
    c.save()

# ---------------- 6) 图卡 / 7) 词卡 ----------------
def make_picture_word(out, cats):
    # 图卡
    c=canvas.Canvas(out, pagesize=A4)
    for ci,(cat,items) in enumerate(cats):
        col=colors.HexColor(PALETTE[ci%len(PALETTE)])
        for pi in range(0,len(items),6):
            page=items[pi:pi+6]
            c.setFillColor(col); c.rect(0,A4H-34,A4W,34,fill=1,stroke=0)
            T(c, cat+" 图卡", 16, A4H-22, 16, (255,255,255))
            cols,rows=2,3; mx,my=18,18
            cw=(A4W-2*mx)/cols; ch=(A4H-34-2*my)/rows
            c.setStrokeColor(colors.HexColor("#cccccc")); c.setDash(3,3); c.setLineWidth(0.6)
            for i in range(cols+1): c.line(mx+i*cw,my,mx+i*cw,A4H-34-my)
            for j in range(rows+1): c.line(mx,my+j*ch,A4W-mx,my+j*ch)
            c.setDash()
            for idx,(word,cp,zh) in enumerate(page):
                r,cc=divmod(idx,cols)
                x0=mx+cc*cw; y0=A4H-34-my-(r+1)*ch
                c.setStrokeColor(col); c.setLineWidth(2.5)
                c.roundRect(x0+10,y0+10,cw-20,ch-20,14,fill=0,stroke=1)
                im=emoji_img(cp); d=ch*0.55
                c.drawImage(ImageReader(im),x0+(cw-d)/2,y0+ch-10-d-6,d,d,mask="auto")
            footer(c,"Kids English Coach · Printables"); c.showPage()
    c.save()

def make_word(out, cats):
    c=canvas.Canvas(out, pagesize=A4)
    for ci,(cat,items) in enumerate(cats):
        col=colors.HexColor(PALETTE[ci%len(PALETTE)])
        for pi in range(0,len(items),6):
            page=items[pi:pi+6]
            c.setFillColor(col); c.rect(0,A4H-34,A4W,34,fill=1,stroke=0)
            T(c, cat+" 词卡", 16, A4H-22, 16, (255,255,255))
            cols,rows=2,3; mx,my=18,18
            cw=(A4W-2*mx)/cols; ch=(A4H-34-2*my)/rows
            c.setStrokeColor(colors.HexColor("#cccccc")); c.setDash(3,3); c.setLineWidth(0.6)
            for i in range(cols+1): c.line(mx+i*cw,my,mx+i*cw,A4H-34-my)
            for j in range(rows+1): c.line(mx,my+j*ch,A4W-mx,my+j*ch)
            c.setDash()
            for idx,(word,cp,zh) in enumerate(page):
                r,cc=divmod(idx,cols)
                x0=mx+cc*cw; y0=A4H-34-my-(r+1)*ch
                c.setStrokeColor(col); c.setLineWidth(2.5)
                c.roundRect(x0+10,y0+10,cw-20,ch-20,14,fill=0,stroke=1)
                T(c, word, x0+cw/2, y0+ch/2-9, 26, col, align="c")
            footer(c,"Kids English Coach · Printables"); c.showPage()
    c.save()

# ---------------- 2) 分类涂色卡 ----------------
def make_coloring(out, cats, title):
    c=canvas.Canvas(out, pagesize=A4)
    c.setFillColor(colors.HexColor("#3b8ec2")); c.rect(0,A4H-52,A4W,52,fill=1,stroke=0)
    T(c, f"My {title} · 分类涂色卡", 24, A4H-30, 20, (255,255,255))
    T(c, "给图标涂色 · 沿灰字描一描单词", A4W-24, A4H-30, 12, (255,255,255), align="r", bold=False)
    y=A4H-80
    panel_h=118
    for ci,(cat,items) in enumerate(cats):
        col=colors.HexColor(PALETTE[ci%len(PALETTE)])
        c.setStrokeColor(col); c.setLineWidth(2); c.setFillColor(col)
        c.roundRect(20, y-panel_h, A4W-40, panel_h, 10, fill=0, stroke=1)
        T(c, f"{cat}", 32, y-18, 13, col)
        n=len(items); inner=A4W-40-28
        d=54
        if n>1:
            g=(inner-n*d)/(n-1)
            if g<14: d=max(38,int((inner-14*(n-1))/n)); g=14
        else: g=0
        bx=34
        for (word,cp,zh) in items:
            im=lineart_img(cp)
            c.drawImage(ImageReader(im), bx, y-panel_h+16, d, d, mask="auto")
            T(c, word, bx+d/2, y-panel_h+4, 10, (110,110,110), align="c")
            bx += d+g
        y-=panel_h+18
        if y<panel_h+60:
            footer(c,"Kids English Coach · Printables"); c.showPage(); y=A4H-80
    footer(c,"Kids English Coach · Printables"); c.showPage(); c.save()

# ---------------- 4) 迷你书 ----------------
def make_minibook(out, cats, title):
    c=canvas.Canvas(out, pagesize=A4)
    catlist=[(cat,items) for ci,(cat,items) in enumerate(cats)]
    def panel(c,x,y,w,h,no,title_s,sub,prompt,box=True,icon=None):
        c.setStrokeColor(colors.HexColor("#3b8ec2")); c.setLineWidth(1.5)
        c.roundRect(x+6,y+6,w-12,h-12,8,fill=0,stroke=1)
        T(c, title_s, x+16, y+h-28, 16, (59,142,194))
        if sub: T(c, sub, x+16, y+h-46, 11, (0,0,0))
        if icon:
            im=emoji_img(icon); c.drawImage(ImageReader(im), x+w-72, y+h-78, 50, 50, mask="auto")
        if prompt:
            T(c, prompt, x+16, y+h-74, 12, (0,0,0))
        if box:
            c.setStrokeColor(colors.HexColor("#bbbbbb")); c.setLineWidth(1)
            c.rect(x+16, y+30, w-32, h-118, fill=0, stroke=1)
        T(c, str(no), x+w/2, y+16, 9, (120,120,120), align="c")
    pages=[
        (f"My {title} Book", f"我的{title}小书 · 填名字+画一画", "Name 名字: __________", False, "2b50"),
        ("I can see ...", "我能看到……", "I can see _______ .", True, catlist[0][1][0][1] if catlist else None),
        ("I like ...", "我喜欢……", "I like _______ .", True, None),
        ("My favourite", "我的最爱", "My favourite _______ .", True, None),
        ("Draw your "+title, f"画一画{title}", "Draw and write.", True, None),
        (catlist[1][0] if len(catlist)>1 else title, catlist[1][0] if len(catlist)>1 else title, "This is a ___ .", True, catlist[1][1][0][1] if len(catlist)>1 else None),
        ("My sentence", "我会写句子", "I can _______ . / It is _______ .", True, None),
        ("The End", "再见 · See you!", f"I love my {title} !", False, "1f60a"),
    ]
    a5w,a5h=277,400
    for sheet,(pl,pr) in enumerate([(0,1),(2,3),(4,5),(6,7)]):
        panel(c,8,A4H-8-a5h,a5w,a5h,pl+1,*pages[pl])
        panel(c,8+a5w+6,A4H-8-a5h,a5w,a5h,pr+1,*pages[pr])
        c.setStrokeColor(colors.HexColor("#cccccc")); c.setDash(4,4); c.setLineWidth(0.6)
        c.line(8+a5w+3,20,8+a5w+3,A4H-20); c.setDash()
        T(c, f"Sheet {sheet+1}/4 · 沿中线裁开，按页码叠好订左上角", A4W/2, 12, 8, (120,120,120), align="c")
        footer(c,"Kids English Coach · Printables"); c.showPage()
    c.save()

# ---------------- 5) 海报 ----------------
def make_poster(out, cats, title):
    c=canvas.Canvas(out, pagesize=A4)
    c.setFillColor(colors.HexColor("#3b8ec2")); c.rect(0,A4H-52,A4W,52,fill=1,stroke=0)
    T(c, f"My {title}", 24, A4H-30, 24, (255,255,255))
    T(c, f"我的{title} · 画一画，写一写", 170, A4H-30, 13, (255,255,255))
    y=A4H-70
    # 分类区（最多 2 个并排，循环）
    pos=[(16, y-150, A4W/2-26, 150)]
    # 简化：每个分类一行卡片
    for ci,(cat,items) in enumerate(cats):
        col=colors.HexColor(PALETTE[ci%len(PALETTE)])
        c.setStrokeColor(col); c.setLineWidth(2)
        c.roundRect(16, y-150, A4W-32, 150, 8, fill=0, stroke=1)
        T(c, f"{ci+1}. {cat}", 26, y-22, 13, col)
        T(c, "Draw & write: 画一画，写一写单词。", 26, y-42, 9, (0,0,0))
        # 词条小图
        n=min(len(items),8); bx=30
        for (word,cp,zh) in items[:n]:
            im=emoji_img(cp); d=44
            c.drawImage(ImageReader(im), bx, y-98, d, d, mask="auto")
            T(c, word, bx+d/2, y-108, 8, (0,0,0), align="c")
            bx += d+14
        y-=160
        if y<300:
            break
    # 句子开头（填满剩余空间，避免溢出/大留白）
    top=max(y-12, 180)
    c.setStrokeColor(colors.HexColor("#e8923a")); c.setLineWidth(2)
    c.roundRect(16, 30, A4W-32, top-30, 8, fill=0, stroke=1)
    T(c, "Sentence Starters 句子开头", 26, top-22, 11, (232,146,58))
    starters=["This is a ___ .","I can see a ___ .","I like ___ .","It is ___ .","My favourite ___ is ___ ."]
    for i,s in enumerate(starters):
        T(c, "•  "+s, 26+(i%2)*285, top-46-(i//2)*20, 10, (0,0,0))
    footer(c,"Kids English Coach · Printables"); c.showPage(); c.save()

# ---------------- 8) 点读指引卡 ----------------
def make_audio_guide(out, title):
    c=canvas.Canvas(out, pagesize=A4)
    T(c, f"{title} · 音频点读指引卡", 30, A4H-50, 20, (59,142,194))
    y=A4H-90
    T(c, "本单元的发音由「自包含点读 HTML」提供：单个文件、音频已内嵌，用手机/电脑浏览器打开即点即播，无需联网或安装 APP。",
      30, y, 11, (90,90,90)); y-=26
    rows=[
        ("🔊 点读.html", "全部单词点读（按分类筛选）"),
        ("🔊 点读句子.html", "单元句型点读（每句带中文翻译）"),
        ("🔊 点读句子_宾果主持人.html", "宾果游戏主持人句点读"),
    ]
    for name,desc in rows:
        c.setStrokeColor(colors.HexColor("#3b8ec2")); c.setLineWidth(1.5)
        c.roundRect(30, y-46, A4W-60, 46, 8, fill=0, stroke=1)
        T(c, name, 44, y-18, 14, (59,142,194))
        T(c, desc, 44, y-36, 10, (60,60,60))
        y-=58
    y-=6
    T(c, "玩法建议", 30, y, 13, (232,96,125)); y-=22
    tips=[
        "打印 PDF 教具，沿虚线裁剪；过塑可反复使用。",
        "先点「听一听」跟读，再玩闪卡/配对/记忆翻牌/宾果。",
        "宾果：家长点主持人句，孩子划对应天气，连成线喊 Bingo！",
        "每天 10 分钟、固定仪式感，把课堂搬进生活场景。",
    ]
    for t in tips:
        T(c, "•  "+t, 30, y, 11, (40,40,40)); y-=18
    footer(c,"Kids English Coach · Printables"); c.showPage(); c.save()

# ---------------- 0) 使用说明 ----------------
def measure(s,size): return cjk_font(size).getlength(s)
def para(c,text,x,y,size,col,maxw,leading):
    cur=""; lines=[]
    for ch in text:
        if measure(cur+ch,size)>maxw and cur: lines.append(cur); cur=ch
        else: cur+=ch
    if cur: lines.append(cur)
    for i,ln in enumerate(lines): T(c,ln,x,y-i*leading,size,col)
    return y-len(lines)*leading
def make_guide(out, cats, title, files):
    c=canvas.Canvas(out, pagesize=A4)
    T(c, f"{title} 主题 · 素材包使用说明", 30, A4H-50, 20, (59,142,194))
    y=A4H-82
    T(c, f"配合《{title}主题单元教案》使用，面向 5-12 岁少儿：图大字少、可打印、可游戏、可点读。",
      30, y, 11, (90,90,90)); y-=24
    flist=" / ".join(files)
    blocks=[
        ("一、材料清单", flist+"——单词卡、图卡、词卡做认读与配对；分类涂色卡做归类；宾果卡做听音游戏；迷你书与海报做单元作品；点读指引卡说明音频用法。"),
        ("二、打印建议", "用 A4 纸；卡类建议 160g 以上彩喷纸更耐玩。沿灰色虚线裁剪，过塑后可反复使用。图卡、词卡用不同颜色纸打印，方便区分。"),
        ("三、怎么玩（5 个游戏）", "1 闪卡认读：快速翻图卡说词，再翻词卡核对。 2 图词配对：图卡词卡混放让孩子配对。 3 记忆翻牌：两套打乱背面朝上，轮流翻两张配对。 4 宾果：主持人点句，孩子划词，连成线喊 Bingo。 5 展示日：用迷你书 + 海报做 1 分钟英文介绍。"),
        ("四、点读音频用法", "单元配套 3 个点读 HTML（点读.html / 点读句子.html / 点读句子_宾果主持人.html）。把 .html 单个文件传到手机，用浏览器打开即点即播，音频已内嵌，无需联网或托管。"),
        ("五、陪学小贴士", "少纠错多鼓励，敢说比说对重要。每天 10 分钟、固定仪式感，把课堂搬进生活场景（看到太阳说 sun、下雨说 rain）。"),
    ]
    for head,body in blocks:
        T(c, head, 30, y, 13, (232,96,125)); y-=20
        y=para(c,body,30,y,11,(40,40,40),A4W-60,16)-12
        if y<70:
            footer(c,"Kids English Coach · Printables"); c.showPage(); y=A4H-60
    footer(c,"Kids English Coach · Printables"); c.showPage(); c.save()

# ---------------- 主流程 ----------------
def build(words_tsv, outdir, title, caller=None):
    os.makedirs(outdir, exist_ok=True)
    cats=load_cats(words_tsv)
    if not cats:
        print("[错误] 词表为空或格式不对（需 word<TAB>codepoint<TAB>中文<TAB>分类）"); sys.exit(1)
    files=["00_使用说明.pdf","01_单词卡_Flashcards.pdf","02_分类涂色卡.pdf",
           "03_宾果卡_Bingo.pdf","04_迷你书_MiniBook.pdf","05_海报模板_Poster.pdf",
           "06_图卡_PictureCards.pdf","07_词卡_WordCards.pdf","08_点读指引卡.pdf"]
    p=lambda n: os.path.join(outdir,n)
    make_flashcards(p(files[1]), cats)
    make_coloring(p(files[2]), cats, title)
    # 03 宾果：调用同目录 gen_bingo.py
    cmd=[sys.executable, GEN_BINGO, words_tsv, p(files[3]), "--cards","4", "--title", f"{title}宾果"]
    if caller: cmd += ["--caller", caller]
    subprocess.run(cmd, check=True)
    make_minibook(p(files[4]), cats, title)
    make_poster(p(files[5]), cats, title)
    make_picture_word(p(files[6]), cats)
    make_word(p(files[7]), cats)
    make_audio_guide(p(files[8]), title)
    make_guide(p(files[0]), cats, title, files)
    print("DONE ->", outdir)
    for f in files:
        fp=p(f)
        print(f"  {f:32s} {os.path.getsize(fp):>8d} bytes" if os.path.exists(fp) else f"  {f:32s} MISSING")

if __name__=="__main__":
    ensure_deps()
    ap=argparse.ArgumentParser()
    ap.add_argument("words"); ap.add_argument("--title", default="Theme")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--caller", default=None)
    a=ap.parse_args()
    build(a.words, a.outdir, a.title, a.caller)
