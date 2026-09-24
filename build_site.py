#!/usr/bin/env python3
# build_site.py — 扫描 themes/<名称>/words.tsv，一键生成 docs/ 静态站点（GitHub Pages / 手机直接访问）
#
# 目录约定：
#   themes/<ascii名称>/words.tsv            必填：词表（word<TAB>码点<TAB>中文<TAB>分类）
#   themes/<ascii名称>/sentences.tsv        可选：分组句型（## 分类|码点 + 英文|中文）
#   themes/<ascii名称>/caller.tsv           可选：宾果主持人词句（word<TAB>sentence）
#   themes/<ascii名称>/caller_sentences.tsv 可选：主持人句点读（sentence<TAB>码点<TAB>分类）
#   themes/<ascii名称>/title.txt            可选：中文标题（缺省用目录名）
#
# 产出：
#   docs/index.html                主题导航页（手机友好）
#   docs/<名称>/index.html          该主题文件清单
#   docs/<名称>/pointread.html      单词点读（ASCII 名，URL 干净）
#   docs/<名称>/sentences.html      句型点读
#   docs/<名称>/caller.html         宾果主持人点读
#   docs/<名称>/0-8 *.pdf           9 份可打印教具
#
# 用法： python3 scripts/build_site.py

import os, sys, subprocess, shutil, html

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
THEMES = os.path.join(ROOT, "themes")
DOCS = os.path.join(ROOT, "docs")
PY = sys.executable

def run(args):
    print("  $", " ".join(os.path.basename(a) if os.path.sep in a else a for a in args))
    subprocess.run(args, check=True)

def read_title(d, name):
    p = os.path.join(d, "title.txt")
    if os.path.exists(p):
        t = open(p, encoding="utf-8-sig").read().strip()
        if t: return t
    return name

CSS = """<style>
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{margin:0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f4f6f8;color:#222;line-height:1.6}
header{background:#2f6fb0;color:#fff;padding:18px 16px}
header h1{margin:0;font-size:20px}header p{margin:6px 0 0;font-size:13px;opacity:.9}
main{padding:14px;max-width:720px;margin:0 auto}
.card{background:#fff;border-radius:14px;padding:14px 16px;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.card h2{margin:0 0 10px;font-size:17px;color:#2f6fb0}
a.item{display:block;padding:12px 14px;margin-bottom:8px;background:#f7f9fb;border-radius:10px;
  text-decoration:none;color:#1a4b7a;font-size:15px;font-weight:600;border-left:4px solid #2f6fb0}
a.item span{display:block;font-weight:400;font-size:12px;color:#777;margin-top:2px}
a.item.hot{background:#fff5e6;border-left-color:#e8923a}
.tip{background:#eef6ff;border-radius:10px;padding:12px 14px;font-size:13px;color:#33506b;margin-bottom:14px}
footer{text-align:center;font-size:12px;color:#999;padding:16px}
</style>"""

def page(title, sub, body):
    return (f"<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title>{CSS}</head><body>"
            f"<header><h1>{html.escape(title)}</h1><p>{html.escape(sub)}</p></header>"
            f"<main>{body}</main><footer>Kids English Coach · 离线可用</footer></body></html>")

def theme_index(name, title, items):
    lis = "".join(
        f"<a class='item{' hot' if hot else ''}' href='{html.escape(f)}'>{html.escape(label)}"
        f"<span>{html.escape(desc)}</span></a>"
        for f, label, desc, hot in items)
    tip = ("<div class='tip'>📱 手机用法：点「单词点读」即可听发音（音频已内嵌，断网也能用）；"
           "PDF 教具请在电脑上打开并打印。<br>💾 想保存：长按链接 → 下载 / 用浏览器打开。</div>")
    body = f"<div class='card'><h2>{html.escape(title)} · 全部材料</h2>{lis}</div>{tip}"
    return page(f"{title} · 点读与教具", "点开即用 · 完全离线", body)

def build_theme(name, d):
    words = os.path.join(d, "words.tsv")
    if not os.path.exists(words):
        print(f"[跳过] {name} 缺少 words.tsv"); return None
    title = read_title(d, name)
    out = os.path.join(DOCS, name)
    os.makedirs(out, exist_ok=True)
    print(f"[生成] {name} ({title})")

    # 9 份 PDF
    cmd = [PY, os.path.join(HERE, "gen_printables.py"), words, "--title", title, "--outdir", out]
    caller = os.path.join(d, "caller.tsv")
    if os.path.exists(caller): cmd += ["--caller", caller]
    run(cmd)

    items = []
    # 单词点读
    wp = os.path.join(out, "点读.html")
    run([PY, os.path.join(HERE, "gen_pointread.py"), words, wp, "--mode", "word"])
    shutil.copyfile(wp, os.path.join(out, "pointread.html"))
    items.append(("pointread.html", "🔊 单词点读", "点哪个词读哪个词 · 断网可用", True))

    # 句型点读
    sent = os.path.join(d, "sentences.tsv")
    if os.path.exists(sent):
        sp = os.path.join(out, "点读句子.html")
        run([PY, os.path.join(HERE, "gen_unit_sentences.py"), sent, sp, "--title", f"{title}单元句型点读"])
        shutil.copyfile(sp, os.path.join(out, "sentences.html"))
        items.append(("sentences.html", "🔊 句型点读", "每句带中文翻译 · 跟读用", True))

    # 宾果主持人点读
    cs = os.path.join(d, "caller_sentences.tsv")
    if os.path.exists(cs):
        cp = os.path.join(out, "点读句子_宾果主持人.html")
        run([PY, os.path.join(HERE, "gen_pointread.py"), cs, cp, "--mode", "sentence"])
        shutil.copyfile(cp, os.path.join(out, "caller.html"))
        items.append(("caller.html", "🔊 宾果主持人点读", "家长念句，孩子划卡", True))

    # PDF 清单
    for f in sorted(os.listdir(out)):
        if f.lower().endswith(".pdf"):
            items.append((f, f, "可打印教具 · A4", False))

    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(theme_index(name, title, items))
    return (name, title, len(items))

def main():
    if not os.path.isdir(THEMES):
        print("[错误] 找不到 themes/ 目录"); sys.exit(1)
    os.makedirs(DOCS, exist_ok=True)
    built = []
    for name in sorted(os.listdir(THEMES)):
        d = os.path.join(THEMES, name)
        if not os.path.isdir(d): continue
        r = build_theme(name, d)
        if r: built.append(r)
    # 站点首页
    lis = "".join(
        f"<a class='item' href='{html.escape(n)}/index.html'>{html.escape(t)}"
        f"<span>{c} 个文件 · 点读 + 可打印教具</span></a>" for n, t, c in built)
    tip = ("<div class='tip'>📱 手机直接点开即用，音频已内嵌，断网也能听。<br>"
           "🖨️ PDF 是打印教具，建议在电脑上打开打印。</div>")
    body = f"<div class='card'><h2>主题列表</h2>{lis}</div>{tip}"
    with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Kids English Coach · 点读与教具", "选一个主题开始", body))
    print(f"DONE -> {DOCS}  主题数={len(built)}")

if __name__ == "__main__":
    main()
