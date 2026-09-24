#!/usr/bin/env python3
# build_site.py — 一键生成 docs/ 静态站点（GitHub Pages / 手机直接访问）
#
# 目录约定（理想结构）：
#   themes/<ascii名称>/words.tsv            必填：词表（word<TAB>码点<TAB>中文<TAB>分类）
#   themes/<ascii名称>/sentences.tsv        可选：分组句型
#   themes/<ascii名称>/caller.tsv           可选：宾果主持人词句
#   themes/<ascii名称>/caller_sentences.tsv 可选：主持人句点读
#   themes/<ascii名称>/title.txt            可选：中文标题
#
# 容错（自愈）：GitHub 网页上传常常把文件夹"摊平"到仓库根目录。
#   本脚本启动时会自动把根目录散落的 gen_*.py 收回 scripts/、
#   把散落的 words.tsv / sentences.tsv / ... 组装回 themes/<名称>/，
#   所以"文件全在根目录"也能正常构建。
#
# 产出：
#   docs/index.html               主题导航页
#   docs/<名称>/index.html        该主题文件清单
#   docs/<名称>/pointread.html    单词点读
#   docs/<名称>/sentences.html    句型点读
#   docs/<名称>/caller.html       宾果主持人点读
#   docs/<名称>/*.pdf             9 份可打印教具
#
# 用法： python scripts/build_site.py

import os, re, sys, html, shutil, subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE) if os.path.basename(_HERE).lower() == "scripts" else _HERE
SCRIPTS = os.path.join(ROOT, "scripts")
THEMES = os.path.join(ROOT, "themes")
DOCS = os.path.join(ROOT, "docs")
PY = sys.executable

# 常见中文主题 → 干净的英文 URL 目录名
SLUG = {
    "天气": "weather", "中秋": "mid-autumn", "家庭": "family", "动物": "animals",
    "食物": "food", "水果": "fruit", "颜色": "colors", "数字": "numbers",
    "学校": "school", "身体": "body", "交通": "transport", "运动": "sports",
    "衣服": "clothes", "职业": "jobs", "时间": "time", "节日": "festival",
    "季节": "seasons", "太空": "space", "海洋": "ocean", "植物": "plants",
    "玩具": "toys", "情绪": "feelings", "动作": "actions", "家居": "home",
    "城市": "city", "厨房": "kitchen", "春天": "spring", "夏天": "summer",
    "秋天": "autumn", "冬天": "winter", "生日": "birthday", "圣诞": "christmas",
}
EXT = {"words": "tsv", "sentences": "tsv", "caller": "tsv", "caller_sentences": "tsv", "title": "txt"}
RE_LOOSE = re.compile(r"^(words|sentences|caller_sentences|caller|title)(?: \((\d+)\))?\.(tsv|txt)$")


def log(msg):
    print(msg, flush=True)


def read_text(p):
    try:
        with open(p, encoding="utf-8-sig") as fh:
            return fh.read().strip()
    except Exception:
        return ""


def ascii_slug(title, fallback):
    t = (title or "").strip().lower()
    if t in SLUG:
        return SLUG[t]
    s = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return s or fallback


def self_heal():
    """把摊平在仓库根目录的文件整理回 scripts/ 与 themes/。"""
    os.makedirs(SCRIPTS, exist_ok=True)
    os.makedirs(THEMES, exist_ok=True)

    # 1) gen_*.py → scripts/
    n = 0
    for f in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p):
            continue
        if not (f.startswith("gen_") and f.endswith(".py")):
            continue
        dst = os.path.join(SCRIPTS, f)
        if os.path.abspath(p) == os.path.abspath(dst):
            continue
        if os.path.exists(dst):
            try:
                os.remove(p)
            except OSError:
                pass
        else:
            shutil.move(p, dst)
        n += 1
    if n:
        log("[自愈] 把 %d 个 gen_*.py 收进 scripts/" % n)

    # 2) 散落的 tsv/txt → themes/<名称>/
    loose = []
    for f in sorted(os.listdir(ROOT)):
        if not os.path.isfile(os.path.join(ROOT, f)):
            continue
        m = RE_LOOSE.match(f)
        if m:
            loose.append((int(m.group(2)) if m.group(2) else 0, m.group(1), f))
    if not loose:
        return
    loose.sort()
    batches = []            # 每个元素: {base: 原文件名}
    for _, base, f in loose:
        target = None
        for b in batches:   # 贪心：放进第一个还没有这个文件的批次
            if base not in b:
                target = b
                break
        if target is None:
            target = {}
            batches.append(target)
        target[base] = f

    m = 0
    for i, b in enumerate(batches):
        if "words" not in b:
            continue
        title = read_text(os.path.join(ROOT, b["title"])) if "title" in b else ""
        slug = ascii_slug(title, "unit" if i == 0 else "unit%d" % (i + 1))
        d = os.path.join(THEMES, slug)
        k = 2
        while os.path.exists(os.path.join(d, "words.tsv")):
            d = os.path.join(THEMES, "%s-%d" % (slug, k))
            k += 1
        os.makedirs(d, exist_ok=True)
        for base, f in b.items():
            src = os.path.join(ROOT, f)
            dst = os.path.join(d, "%s.%s" % (base, EXT[base]))
            if os.path.abspath(src) == os.path.abspath(dst):
                continue
            if os.path.exists(dst):
                try:
                    os.remove(src)
                except OSError:
                    pass
            else:
                shutil.move(src, dst)
            m += 1
        log("[自愈] 组装主题 themes/%s/  ← %s" % (os.path.basename(d), ", ".join(sorted(b.values()))))
    if m:
        log("[自愈] 共整理 %d 个数据文件到 themes/" % m)


def run(args):
    log("  $ " + " ".join(args))
    subprocess.run(args, check=True)


def read_title(d, name):
    p = os.path.join(d, "title.txt")
    if os.path.exists(p):
        t = read_text(p)
        if t:
            return t
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
    return ("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>%s</title>%s</head><body>"
            "<header><h1>%s</h1><p>%s</p></header>"
            "<main>%s</main><footer>Kids English Coach · 离线可用</footer></body></html>"
            % (html.escape(title), CSS, html.escape(title), html.escape(sub), body))


def theme_index(title, items):
    lis = "".join(
        "<a class='item%s' href='%s'>%s<span>%s</span></a>"
        % (" hot" if hot else "", html.escape(f), html.escape(label), html.escape(desc))
        for f, label, desc, hot in items)
    tip = ("<div class='tip'>📱 手机用法：点「单词点读」即可听发音（音频已内嵌，断网也能用）；"
           "PDF 教具请在电脑上打开并打印。<br>💾 想保存：长按链接 → 下载 / 用浏览器打开。</div>")
    return page("%s · 点读与教具" % title, "点开即用 · 完全离线",
                "<div class='card'><h2>%s · 全部材料</h2>%s</div>%s" % (html.escape(title), lis, tip))


def build_theme(name, d):
    words = os.path.join(d, "words.tsv")
    if not os.path.exists(words):
        log("[跳过] %s 缺少 words.tsv" % name)
        return None
    title = read_title(d, name)
    out = os.path.join(DOCS, name)
    os.makedirs(out, exist_ok=True)
    log("[生成] %s (%s)" % (name, title))

    cmd = [PY, os.path.join(SCRIPTS, "gen_printables.py"), words, "--title", title, "--outdir", out]
    caller = os.path.join(d, "caller.tsv")
    if os.path.exists(caller):
        cmd += ["--caller", caller]
    run(cmd)

    items = []
    wp = os.path.join(out, "点读.html")
    run([PY, os.path.join(SCRIPTS, "gen_pointread.py"), words, wp, "--mode", "word"])
    shutil.copyfile(wp, os.path.join(out, "pointread.html"))
    items.append(("pointread.html", "🔊 单词点读", "点哪个词读哪个词 · 断网可用", True))

    sent = os.path.join(d, "sentences.tsv")
    if os.path.exists(sent):
        sp = os.path.join(out, "点读句子.html")
        run([PY, os.path.join(SCRIPTS, "gen_unit_sentences.py"), sent, sp,
             "--title", "%s单元句型点读" % title])
        shutil.copyfile(sp, os.path.join(out, "sentences.html"))
        items.append(("sentences.html", "🔊 句型点读", "每句带中文翻译 · 跟读用", True))

    cs = os.path.join(d, "caller_sentences.tsv")
    if os.path.exists(cs):
        cp = os.path.join(out, "点读句子_宾果主持人.html")
        run([PY, os.path.join(SCRIPTS, "gen_pointread.py"), cs, cp, "--mode", "sentence"])
        shutil.copyfile(cp, os.path.join(out, "caller.html"))
        items.append(("caller.html", "🔊 宾果主持人点读", "家长念句，孩子划卡", True))

    for f in sorted(os.listdir(out)):
        if f.lower().endswith(".pdf"):
            items.append((f, f, "可打印教具 · A4", False))

    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(theme_index(title, items))
    return (name, title, len(items))


def main():
    self_heal()
    missing = [f for f in ("gen_printables.py", "gen_pointread.py", "gen_unit_sentences.py", "gen_bingo.py")
               if not os.path.exists(os.path.join(SCRIPTS, f))]
    if missing:
        log("[错误] scripts/ 缺少脚本：%s" % ", ".join(missing))
        sys.exit(1)
    if not os.path.isdir(THEMES):
        log("[错误] 找不到 themes/ 目录，也没有可组装的词表")
        sys.exit(1)

    os.makedirs(DOCS, exist_ok=True)
    built = []
    for name in sorted(os.listdir(THEMES)):
        d = os.path.join(THEMES, name)
        if not os.path.isdir(d):
            continue
        r = build_theme(name, d)
        if r:
            built.append(r)
    if not built:
        log("[错误] themes/ 下没有任何含 words.tsv 的主题")
        sys.exit(1)

    lis = "".join(
        "<a class='item' href='%s/index.html'>%s<span>%d 个文件 · 点读 + 可打印教具</span></a>"
        % (html.escape(n), html.escape(t), c) for n, t, c in built)
    tip = ("<div class='tip'>📱 手机直接点开即用，音频已内嵌，断网也能听。<br>"
           "🖨️ PDF 是打印教具，建议在电脑上打开打印。</div>")
    with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Kids English Coach · 点读与教具", "选一个主题开始",
                      "<div class='card'><h2>主题列表</h2>%s</div>%s" % (lis, tip)))
    log("DONE -> %s  主题数=%d" % (DOCS, len(built)))


if __name__ == "__main__":
    main()
