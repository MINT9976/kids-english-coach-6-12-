#!/usr/bin/env python3.11
# gen_pointread.py — 把"词表/句表"生成自包含点读 HTML（音频+图标全 base64 内嵌，离线可点）
#
# 依赖: espeak-ng (离线TTS), ffmpeg (mp3转码); 图标可选 cairosvg+requests 下载 Twemoji。
# 用法:
#   词模式:  python3 gen_pointread.py words.tsv out.html --mode word
#   句模式:  python3 gen_pointread.py sents.tsv out.html --mode sentence
#
# words.tsv 每行:  word <TAB> emoji_codepoint <TAB> 中文 <TAB> 分类
#   例:  mother  1f469  妈妈  家人
# sents.tsv 每行:  sentence <TAB> emoji_codepoint <TAB> 分类
#   例:  She is sleeping.  1f634  动作
# 分类用于筛选按钮（自动去重，颜色循环）。

import base64, os, sys, html, subprocess, argparse, tempfile, shutil

EMOJI_PX = 200
PALETTE = ["#e8607d","#3b8ec2","#5aa469","#e8923a","#8a6fc4",
           "#d96ba8","#4fb0c6","#c9a227","#7a8b3c","#b5651d"]

# 离线 TTS 发音设置（面向 5-12 岁，清晰优先）
# 语音：英式 RP（en-gb-x-rp）——课程为剑桥 YLE（英式），"Mum/colour/teddy" 才读得对
# 如要美式，把 TTS_VOICE 改回 "en-us" 即可（一行切换）
TTS_VOICE = "en-gb-x-rp"
TTS_OPTS  = ["-s","100","-p","60","-g","6","-a","110"]   # 慢速+略高音+词间停顿+音量

# 分类名归一化：教案里常写「描述 / Describing」，点读页统一显示为「形容词」（更直观）
CAT_ALIAS = {"描述":"形容词","Describing":"形容词","描述词":"形容词"}
def norm_cat(c):
    return CAT_ALIAS.get(c, c)

def b64(path):
    with open(path,"rb") as f:
        return base64.b64encode(f.read()).decode()

def get_emoji(cp):
    """返回 emoji PNG 路径（本地缓存或下载 Twemoji SVG 栅格化）。"""
    cache = os.path.join(tempfile.gettempdir(), f"emo_{cp}.png")
    if os.path.exists(cache) and os.path.getsize(cache) > 300:
        return cache
    try:
        import requests, cairosvg
        r = requests.get(f"https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/{cp}.svg", timeout=20)
        if r.status_code == 200:
            png = cairosvg.svg2png(bytestring=r.content, output_width=EMOJI_PX, output_height=EMOJI_PX)
            open(cache,"wb").write(png); return cache
    except Exception:
        pass
    # 兜底灰圆
    from PIL import Image, ImageDraw
    im = Image.new("RGBA",(EMOJI_PX,EMOJI_PX),(0,0,0,0))
    ImageDraw.Draw(im).ellipse([10,10,EMOJI_PX-10,EMOJI_PX-10], fill=(228,228,228,255))
    im.save(cache); return cache

def ensure_deps():
    """确保 espeak-ng / ffmpeg 可用。
    - root 环境（如沙箱）：缺失则自动 apt 安装，无需手动操作。
    - 普通用户环境：不自动装，直接给出清晰安装命令后退出。
    cairosvg 仅用于 emoji 图标，缺失会自动降级为灰圆，不阻断。
    """
    import shutil, subprocess as _sp
    need = [t for t in ("espeak-ng", "ffmpeg") if shutil.which(t) is None]
    if not need:
        return
    print(f"[依赖] 检测到缺失: {', '.join(need)}")
    if sys.platform.startswith("linux") and os.geteuid() == 0:
        try:
            print("[依赖] 以 root 身份尝试自动安装…")
            _sp.run(["apt-get", "update", "-qq"], check=True, capture_output=True, timeout=180)
            _sp.run(["apt-get", "install", "-y"] + need, check=True, capture_output=True, timeout=600)
            if all(shutil.which(t) for t in need):
                print("[依赖] 自动安装成功 ✅"); return
        except Exception as e:
            print(f"[依赖] 自动安装失败: {e}")
    # 兜底：明确提示
    print("[依赖] 请先安装后重试：")
    print("  Debian/Ubuntu:  sudo apt-get install -y espeak-ng ffmpeg")
    print("  macOS (brew):   brew install espeak-ng ffmpeg")
    print("  Python 库:      pip install cairosvg requests pillow")
    sys.exit(1)

def tts(text, mp3):
    if os.path.exists(mp3) and os.path.getsize(mp3) > 1000:
        return True
    wav = mp3[:-4]+".wav"
    r = subprocess.run(["espeak-ng","-v",TTS_VOICE]+TTS_OPTS+["-w",wav,text], capture_output=True)
    if r.returncode != 0 or not os.path.exists(wav):
        return False
    f = subprocess.run(["ffmpeg","-y","-i",wav,"-codec:a","libmp3lame","-q:a","4",mp3], capture_output=True)
    os.remove(wav)
    return f.returncode == 0 and os.path.getsize(mp3) > 1000

def build(infile, out, mode):
    tmpdir = tempfile.mkdtemp(prefix="pr_")   # 每个主题独立临时目录，杜绝跨主题缓存串味
    rows = []
    cats = []
    with open(infile, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            if mode == "word":
                word, cp, zh, cat = (parts + ["","","",""]*4)[:4]
                text = word
            else:
                sent, cp, cat, zh = (parts + ["","","",""]*4)[:4]
                word, zh, text = sent, zh, sent
            cat = norm_cat(cat)
            rows.append((word, cp, zh, cat, text))
            if cat not in cats:
                cats.append(cat)
    cat_color = {c: PALETTE[i % len(PALETTE)] for i,c in enumerate(cats)}

    cards = []
    for idx,(word, cp, zh, cat, text) in enumerate(rows):
        mp3 = os.path.join(tmpdir, f"pr_{idx}.mp3")
        ok = tts(text, mp3)
        a = b64(mp3) if ok else ""
        e = b64(get_emoji(cp)) if cp else ""
        color = cat_color[cat]
        if mode == "word":
            body = f'<img class="emo" src="data:image/png;base64,{e}"><div class="word">{html.escape(word)} <span class="zh">{html.escape(zh)}</span></div><button class="play" data-audio="data:audio/mpeg;base64,{a}">🔊 听一听</button>'
        else:
            gloss = f'<div class="zh">{html.escape(zh)}</div>' if zh else ""
            body = f'<img class="emo" src="data:image/png;base64,{e}"><div class="sent">{html.escape(word)}</div>{gloss}<button class="play" data-audio="data:audio/mpeg;base64,{a}">🔊 听一听</button>'
        cards.append(f'<div class="card" data-cat="{cats.index(cat)}"><div class="bar" style="background:{color}">{html.escape(cat)}</div><div class="body">{body}</div></div>')

    filt = "".join(
        f'<button class="fbtn" data-cat="{i}" style="--c:{cat_color[c]}">{html.escape(c)}</button>'
        for i,c in enumerate(cats))
    title = "点读词卡" if mode=="word" else "点读句子"

    doc = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>{title}</title><style>
*{{box-sizing:border-box;-webkit-tap-highlight-color:transparent;}}
body{{margin:0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f4f6f8;color:#222;}}
header{{background:#2f6fb0;color:#fff;padding:16px 14px 12px;text-align:center;}}
header h1{{margin:0;font-size:20px;}} header p{{margin:4px 0 0;font-size:12px;opacity:.85;}}
.filters{{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;padding:12px 10px 4px;}}
.fbtn{{border:2px solid var(--c);color:var(--c);background:#fff;border-radius:20px;padding:6px 14px;font-size:14px;font-weight:700;cursor:pointer;}}
.fbtn.on{{background:var(--c);color:#fff;}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;padding:12px;max-width:900px;margin:0 auto 40px;}}
.card{{background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);}}
.bar{{color:#fff;font-size:12px;font-weight:700;padding:5px 8px;text-align:center;}}
.body{{padding:10px 8px 12px;text-align:center;}}
.emo{{width:84px;height:84px;object-fit:contain;}}
.word{{font-size:20px;font-weight:800;margin-top:6px;}} .zh{{font-size:13px;color:#888;font-weight:600;}}
.sent{{font-size:16px;font-weight:700;margin:6px 4px;}}
.play{{margin-top:10px;width:100%;border:none;border-radius:10px;background:#ffd24a;color:#5a3d00;font-size:15px;font-weight:800;padding:10px;cursor:pointer;}}
.play:active{{transform:scale(.97);}} .card.hit{{outline:3px solid #ffb300;}}
footer{{text-align:center;font-size:11px;color:#999;padding:0 16px 30px;}}
</style></head><body>
<header><h1>🏠 {title}</h1><p>点「听一听」即可发声 · 完全离线</p></header>
<div class="filters"><button class="fbtn on" data-cat="-1" style="--c:#444">全部</button>{filt}</div>
<div class="grid" id="grid">{''.join(cards)}</div>
<footer>音频由离线 TTS（英式 RP）生成，供跟读参考。</footer>
<script>
const audio=new Audio();audio.preload='auto';document.body.appendChild(audio);let cur=null,unlocked=false;
function unlock(){{if(unlocked)return;unlocked=true;try{{const p=audio.play();if(p&&p.then)p.then(()=>{{audio.pause();audio.currentTime=0;}}).catch(()=>{{}});}}catch(e){{}}}}
function playSrc(src){{try{{audio.src=src;const p=audio.play();if(p&&p.catch)p.catch(()=>{{const a2=new Audio(src);a2.play().catch(()=>alert('浏览器阻止了音频播放，请检查静音开关，或换个浏览器（推荐 Chrome / Safari）'));}});}}catch(e){{}}}}
function stop(){{if(cur)cur.parentElement.parentElement.classList.remove('hit');audio.pause();audio.currentTime=0;}}
document.addEventListener('touchstart',unlock,{{once:true}});
document.getElementById('grid').addEventListener('click',e=>{{const b=e.target.closest('.play');if(!b)return;unlock();stop();b.parentElement.parentElement.classList.add('hit');cur=b;playSrc(b.dataset.audio);}});
document.querySelectorAll('.fbtn').forEach(btn=>btn.addEventListener('click',()=>{{document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('on'));btn.classList.add('on');const c=btn.dataset.cat;document.querySelectorAll('.card').forEach(card=>{{card.style.display=(c==='-1'||card.dataset.cat===c)?'':'none';}});}}));
</script></body></html>'''
    with open(out,"w",encoding="utf-8") as f:
        f.write(doc)
    shutil.rmtree(tmpdir, ignore_errors=True)   # 清理临时目录
    print(f"wrote {out}  cards={len(cards)}  cats={cats}")

if __name__ == "__main__":
    ensure_deps()
    ap = argparse.ArgumentParser()
    ap.add_argument("infile"); ap.add_argument("out")
    ap.add_argument("--mode", choices=["word","sentence"], default="word")
    a = ap.parse_args()
    build(a.infile, a.out, a.mode)
