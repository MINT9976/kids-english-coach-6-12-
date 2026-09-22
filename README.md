# Kids English Coach · 少儿英语培训教练（使用说明）

一个 WorkBuddy 技能，专为 **5-12 岁孩子**设计英语课程/单元，并一键产出**可打印教具 + 可点读音频页**。已适配剑桥 YLE（英式发音）。

> 分发包内含 `samples/Weather_Materials/` —— 天气主题**完整成品演示**，装好后可直接打开看效果（见第 4 节）。

---

## 1. 这是什么

- **教案**：按"启蒙 / 进阶（YLE→KET→PET）/ 专项补强"三段式生成单元与单课。
- **可点读音频页**：单个 HTML 文件，音频 + 图标全部内嵌，**离线、不托管**——手机浏览器打开即点即播，不用装 APP、不用联网。
- **可打印 PDF 教具**：单词卡、宾果、迷你书、海报、图词分离卡等，一键生成 9 份。

---

## 2. 目录结构

```
kids-english-coach/
├── SKILL.md                      # 技能主文件（WorkBuddy 读取）
├── README.md                     # 本说明
├── install.sh                    # 一键安装脚本（macOS/Linux/WSL/Git Bash）
├── references/
│   ├── curriculum.md             # 三段式课程总框架 + 小学衔接
│   ├── unit-template.md          # 单元模板（复制填充）
│   ├── methods.md                # 五种教学法详解
│   └── materials.md              # 教具清单与生成方式
├── scripts/
│   ├── gen_pointread.py          # 词/句 → 点读 HTML
│   ├── gen_unit_sentences.py     # 分组句型 → 单元句型点读 HTML
│   ├── gen_bingo.py              # 词表 → 宾果卡 PDF
│   └── gen_printables.py         # 词表 → 一键全套 9 份 PDF
└── assets/
    └── family_sentences.tsv      # 句型点读模板样例

samples/
└── Weather_Materials/            # 天气主题完整成品演示（见第 4 节）
```

---

## 3. 安装

三种方式任选其一：

### A. 一键安装脚本（macOS / Linux / WSL / Git Bash）
在解压后的包根目录运行：
```bash
bash kids-english-coach/install.sh
```
脚本会检测平台 → 复制到 WorkBuddy 技能目录 → 检查并提示依赖。

### B. 手动安装（全平台通用）
把 `kids-english-coach/` 文件夹放到 WorkBuddy 技能目录：
- **Windows**：`%USERPROFILE%\.codebuddy\skills\kids-english-coach\`
- **macOS / Linux**：`~/.codebuddy/skills/kids-english-coach\`

### C. Windows 原生（PowerShell，管理员）
```powershell
$skills = "$env:USERPROFILE\.codebuddy\skills"
New-Item -ItemType Directory -Force -Path "$skills\kids-english-coach" | Out-Null
Copy-Item -Recurse -Force ".\kids-english-coach\*" "$skills\kids-english-coach\"
Write-Host "已安装到 $skills\kids-english-coach"
```

放好后，在 WorkBuddy 里用自然语言提需求即可（见第 5 节）。技能会自动按 `SKILL.md` 的描述被触发。

---

## 4. 演示样例（samples/）

包内 `samples/Weather_Materials/` 是**天气主题完整成品**，安装后可直接打开看效果：

| 文件 | 内容 |
|---|---|
| `天气主题单元教案.md` | 5 课时 Movers 天气单元 |
| `00~08_*.pdf` | 全套 9 份可打印 PDF 教具（含宾果） |
| `点读.html` / `点读句子.html` / `点读句子_宾果主持人.html` | 离线点读页（手机/电脑浏览器打开即点即播） |
| `words.tsv` / `sentences.tsv` / `caller.tsv` | 驱动生成的源数据，复制改主题即可复用 |

> 这是"换主题 → 改 TSV → 跑脚本"闭环的真实产出样例，可作为其它主题（动物/食物/学校）的蓝本。

---

## 5. 依赖（首次使用需注意）

| 能力 | 依赖 | 是否自动装 |
|---|---|---|
| 教案 / 框架逻辑 | 无 | —（零安装） |
| 点读音频页（HTML） | `espeak-ng` + `ffmpeg` | 是（root 自动 `apt`；普通用户给命令） |
| 可打印 PDF | `reportlab` + `Pillow` + `cairosvg` | 是（root 自动 `pip`；普通用户给命令） |

> **已生成的产物零依赖**：`.html` 点读页 / `.pdf` 教具里的音频、图标都已内嵌。把它们发给任何人，对方直接用浏览器打开 / 打印即可，无需这些环境。
> **生成 PDF 时**：emoji 图标会从公开 Twemoji CDN 联网下载并本地缓存；无网络时自动降级为灰色圆形，不影响其余排版。

---

## 6. 典型用法（直接对 WorkBuddy 说）

1. **出教案**：`给 7 岁孩子做一个 Movers 级天气主题单元教案`
2. **出全套物料**：`开做看看效果` / `补齐全套可打印 PDF 教具`
3. **出点读页**：`把单词做成可点读的 HTML`
4. **换主题**：把上面请求里的主题词换了即可（如"动物""食物""学校"），旧主题文件不动。

也可以让助手自己跑脚本（进阶）：
```bash
# 一键全套 9 份 PDF
python3 scripts/gen_printables.py words.tsv --title "天气" --outdir ./Weather_Materials --caller caller.tsv
# 单词点读
python3 scripts/gen_pointread.py words.tsv 点读.html --mode word
# 句型点读
python3 scripts/gen_pointread.py sent.tsv 点读句子.html --mode sentence
# 单独宾果卡
python3 scripts/gen_bingo.py words.tsv 宾果卡_Bingo.pdf --caller caller.tsv
```

---

## 7. 自定义主题的输入文件格式

| 文件 | 格式（TAB 分隔） | 说明 |
|---|---|---|
| `words.tsv` | `单词 <TAB> emoji码点 <TAB> 中文 <TAB> 分类` | emoji 码点如太阳 `2600`；分类可用 家人/房间/物品/动作/形容词 等 |
| `caller.tsv` | `单词 <TAB> 主持人句` | 宾果主持人页/点读用（可选） |
| 句型表 | `英文句 <TAB> emoji码点 <TAB> 分类 <TAB> 中文` | 句型点读用 |

> 提示：分类名若写成"描述 / Describing"，生成器会**自动归一化为「形容词」**。

---

## 8. 常见问题

- **点读页在手机能用吗？** 能。单个 HTML 离线打开即点即播（iOS Safari / 安卓 Chrome 均可，点击即用户手势触发，绕过自动播放限制）。
- **发音英式还是美式？** 默认**英式 RP**（对标剑桥 YLE）。脚本顶部 `TTS_VOICE` 改 `en-us` 即切美式。
- **完全离线能用吗？** 已生成的 HTML/PDF 可离线使用；但"生成"过程首次需联网下载 emoji 图标 / 依赖（之后有本地缓存）。

---

## 9. 安全说明

所有脚本**仅在本地生成文件**（PDF / HTML / 音频），**不上传任何用户数据**。emoji 图标从公开 CDN 下载，不收集用户信息。
