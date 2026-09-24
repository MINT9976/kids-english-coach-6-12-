#!/usr/bin/env python3.11
# gen_unit_sentences.py — 生成「单元句型点读」HTML（按分类分组、每句带中文翻译、离线不托管）
#
# 输入格式（纯文本，用 | 分隔字段）：
#   ## 分类名 | emoji码点
#   英文句 | 中文翻译
#   英文句 | 中文翻译
#   ## 下一个分类 | emoji码点
#   ...
# 例：
#   ## 存在句 There is/are | 1f3e0
#   There is a bed in the bedroom. | 卧室里有一张床。
#
# 分类名若写「描述 / Describing」会自动归一化为「形容词」。
# 输出：单个自包含 HTML（音频+图标全 base64 内嵌），传到手机离线即用，无需联网/托管。
#
# 用法：python3 gen_unit_sentences.py input.txt out.html [--title "单元句型点读"]

import base64, os, html, sys, argparse, tempfile, subprocess, shutil
import requests, cairosvg
from PIL import Image, ImageDraw

EMOJI_PX = 200
CAT_ALIAS = {"描述":"形容词","Describing":"形容词","描述词":"形容词"}
PALETTE = ["#5a7fd0","#5aa469","#e8923a","#e8607d","#8a6fc4","#3b8ec2","#d96ba8","#4fb0c6"]

# 离线 TTS 发音设置（面向 5-12 岁，清晰优先）
# 语音：英式 RP（en-gb-x-rp）——课程为剑桥 YLE（英式），"Mum/colour/teddy" 才读得对
# 如要美式，把 TTS_VOICE 改回 "en-us" 即可（一行切换）
TTS_VOICE = "en-gb-x-rp"
TTS_OPTS  = ["-s","100","-p","60","-g","6","-a","110"]   # 慢速+略高音+词间停顿+音量

def b64(p):
    with open(p,"rb") as f: return base64.b64encode(f.read()).decode()

def get_emoji(cp):
    cache = os.path.join(tempfile.gettempdir(), f"emo_{cp}.png")
    if os.path.exists(cache) and os.path.getsize(cache) > 300: return cache
    try:
        r = requests.get(f"https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/{cp}.svg", timeout=20)
        if r.status_code == 200:
            png = cairosvg.svg2png(bytestring=r.content, output_width=EMOJI_PX, output_height=EMOJI_PX)
            open(cache,"wb").write(png); return cache
    except Exception: pass
    im = Image.new("RGBA",(EMOJI_PX,EMOJI_PX),(0,0,0,0))
    ImageDraw.Draw(im).ellipse([10,10,EMOJI_PX-10,EMOJI_PX-10], fill=(228,228,228,255)); im.save(cache); return cache

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
    if os.path.exists(mp3) and os.path.getsize(mp3) > 1000: return True
    wav = mp3[:-4]+".wav"
    r = subprocess.run(["espeak-ng","-v",TTS_VOICE]+TTS_OPTS+["-w",wav,text], capture_output=True)
    if r.returncode != 0 or not os.path.exists(wav): return False
    f = subprocess.run(["ffmpeg","-y","-i",wav,"-codec:a","libmp3lame","-q:a","4",mp3], capture_output=True)
    os.remove(wav)
    return f.returncode == 0 and os.path.getsize(mp3) > 1000

def build(infile, out, title="单元句型点读"):
    tmpdir = tempfile.mkdtemp(prefix="us_")   # 每个主题独立临时目录，杜绝跨主题缓存串味
    cats = []; cur = None
    with open(infile, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip(): continue
            if line.startswith("##"):
                rest = line[2:].split("|")
                label = rest[0].strip(); cp = rest[1].strip() if len(rest) > 1 else ""
                label = CAT_ALIAS.get(label, label)
                cur = {"label":label,"emoji":cp,"sents":[]}; cats.append(cur)
            else:
                if cur is None: continue
                parts = line.split("|")
                en = parts[0].strip(); zh = parts[1].strip() if len(parts) > 1 else ""
                if en: cur["sents"].append((en, zh))

    cards = []
    total = 0
    for ci, c in enumerate(cats):
        color = PALETTE[ci % len(PALETTE)]
        e = b64(get_emoji(c["emoji"])) if c["emoji"] else ""
        inner = []
        for j,(en,zh) in enumerate(c["sents"]):
            mp3 = os.path.join(tmpdir, f"us_{ci}_{j}.mp3")
            ok = tts(en, mp3); a = b64(mp3) if ok else ""
            inner.append(
                f'<div class="sent"><div class="en">{html.escape(en)}</div>'
                f'<div class="zh">{html.escape(zh)}</div>'
                f'<button class="play" data-audio="data:audio/mpeg;base64,{a}">🔊 听一听</button></div>')
            total += 1
        cards.append(
            f'<div class="card" data-cat="{ci}"><div class="bar" style="background:{color}">'
            f'<img class="bar-emo" src="data:image/png;base64,{e}">{html.escape(c["label"])}</div>'
            f'<div class="body">{"" .join(inner)}</div></div>')

    filt = "".join(
        f'<button class="fbtn" data-cat="{i}" style="--c:{PALETTE[i%len(PALETTE)]}">{html.escape(c["label"])}</button>'
        for i,c in enumerate(cats))

    doc = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>{title}</title><style>
*{{box-sizing:border-box;-webkit-tap-highlight-color:transparent;}}
body{{margin:0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f4f6f8;color:#222;}}
header{{background:#2f6fb0;color:#fff;padding:16px 14px 12px;text-align:center;}}
header h1{{margin:0;font-size:20px;}} header p{{margin:4px 0 0;font-size:12px;opacity:.85;}}
.filters{{display:flex;flex-wrap:wrap;gap:7px;justify-content:center;padding:12px 10px 4px;}}
.fbtn{{border:2px solid var(--c);color:var(--c);background:#fff;border-radius:18px;padding:5px 12px;font-size:13px;font-weight:700;cursor:pointer;}}
.fbtn.on{{background:var(--c);color:#fff;}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;padding:12px;max-width:920px;margin:0 auto 40px;}}
.card{{background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);}}
.bar{{color:#fff;font-size:13px;font-weight:700;padding:6px 8px;text-align:center;display:flex;align-items:center;justify-content:center;gap:6px;}}
.bar-emo{{width:22px;height:22px;vertical-align:middle;}}
.body{{padding:8px 10px 12px;}}
.sent{{text-align:center;padding:10px 4px;border-top:1px dashed #eee;}}
.sent:first-child{{border-top:none;}}
.en{{font-size:17px;font-weight:800;}} .zh{{font-size:12px;color:#999;margin-top:2px;}}
.play{{margin-top:8px;width:100%;border:none;border-radius:10px;background:#ffd24a;color:#5a3d00;font-size:15px;font-weight:800;padding:9px;cursor:pointer;}}
.play:active{{transform:scale(.97);}} .card.hit .en{{color:#e8923a;}}
footer{{text-align:center;font-size:11px;color:#999;padding:0 16px 30px;}}
</style></head><body>
<header><h1>🏠 {title}</h1><p>点「听一听」即可发声 · 单个文件完全离线 · 无需联网/托管</p></header>
<div class="filters"><button class="fbtn on" data-cat="-1" style="--c:#444">全部</button>{filt}</div>
<div class="grid" id="grid">{''.join(cards)}</div>
<footer>音频由离线 TTS（英式 RP）生成，供跟读参考。共 {total} 句。</footer>
<script>
const audio=new Audio();audio.preload='auto';document.body.appendChild(audio);let cur=null,unlocked=false;
function unlock(){{if(unlocked)return;unlocked=true;try{{const p=audio.play();if(p&&p.then)p.then(()=>{{audio.pause();audio.currentTime=0;}}).catch(()=>{{}});}}catch(e){{}}}}
function playSrc(src){{try{{audio.src=src;const p=audio.play();if(p&&p.catch)p.catch(()=>{{const a2=new Audio(src);a2.play().catch(()=>alert('浏览器阻止了音频播放，请检查静音开关，或换个浏览器（推荐 Chrome / Safari）'));}});}}catch(e){{}}}}
function stop(){{if(cur)cur.closest('.sent').classList.remove('hit');audio.pause();audio.currentTime=0;}}
document.addEventListener('touchstart',unlock,{{once:true}});
document.getElementById('grid').addEventListener('click',e=>{{const b=e.target.closest('.play');if(!b)return;unlock();stop();b.closest('.sent').classList.add('hit');cur=b;playSrc(b.dataset.audio);}});
document.querySelectorAll('.fbtn').forEach(btn=>btn.addEventListener('click',()=>{{document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('on'));btn.classList.add('on');const c=btn.dataset.cat;document.querySelectorAll('.card').forEach(card=>{{card.style.display=(c==='-1'||card.dataset.cat===c)?'':'none';}});}}));
</script></body></html>'''
    with open(out,"w",encoding="utf-8") as f:
        f.write(doc)
    shutil.rmtree(tmpdir, ignore_errors=True)   # 清理临时目录
    print(f"wrote {out}  categories={len(cats)}  sentences={total}")

if __name__ == "__main__":
    ensure_deps()
    ap = argparse.ArgumentParser()
    ap.add_argument("infile"); ap.add_argument("out")
    ap.add_argument("--title", default="单元句型点读")
    a = ap.parse_args()
    build(a.infile, a.out, a.title)
