# 已落地教具清单与生成方式

> 这些教具均已实际产出（家庭、天气等主题样例）。新主题**推荐用 `scripts/gen_printables.py` 一键生成**，产出文件名见 2.3 节；早期家庭版 PDF 文件名略有差异（如 `02_家庭树涂色卡_FamilyTree.pdf`、`08_点读卡_AudioQR.pdf`），功能一致。

## 1. 可打印 PDF 教具（一键生成，见 2.3 节）
| 文件 | 内容 | 用法 |
|---|---|---|
| `00_使用说明.pdf` | 全包使用说明（材料/打印/游戏/音频/陪学贴士） | 家长先看 |
| `01_单词卡_Flashcards.pdf` | 词卡（按分类色条分类，图+词） | 沿虚线剪下认读 |
| `02_分类涂色卡.pdf` | 分类认读/涂色卡 | 给图标涂色、写单词 |
| `03_宾果卡_Bingo.pdf` | N 张唯一 3×3 Bingo + 主持人页 | 听句划词，连成线喊 Bingo |
| `04_迷你书_MiniBook.pdf` | 8 页折叠小书 | 裁开叠好订左上角 |
| `05_海报模板_Poster.pdf` | 综合展示海报 | 单元末作品 + Show & Tell |
| `06_图卡_PictureCards.pdf` | 纯图卡（无词） | 与词卡配对游戏 |
| `07_词卡_WordCards.pdf` | 纯词卡（无图） | 图词分离认读 |
| `08_点读指引卡.pdf` | 音频点读页使用指引 | 指向自包含 HTML |

生成方式：reportlab 排版 + Twemoji 图标（SVG 高清栅格化）+ Noto CJK 中文贴图。

## 2. 点读音频页（离线、自包含 HTML —— 不托管）
| 文件 | 内容 |
|---|---|
| `点读.html` | 单词 + 图标 + 音频全部 base64 内嵌；点"听一听"即播；按分类筛选 |
| `点读句子.html` | 宾果主持人句子 / 单元句型逐句点读 |

> 以上均为**单个 HTML 文件**，音频 + 图标全部 base64 内嵌，**完全离线、不依赖网络或任何托管**。
> 用法：把 `.html` 单个文件传到手机（微信/数据线/AirDrop 均可），用浏览器打开即点即播，无需装 APP、无需联网。

生成方式：espeak-ng 离线 TTS 生成 mp3 → ffmpeg 转码 → base64 内嵌进单 HTML。
**默认发音设置**（面向 5-12 岁，清晰优先；常量定义在生成器脚本顶部，改一处即全局生效）：
- 语音：`en-gb-x-rp`（**英式 RP**）——课程为剑桥 YLE（英式），`Mum / colour / teddy` 等才读得对地道。
- 参数：`-s 100`（慢速）`-p 60`（略高音，孩子友好）`-g 6`（词间停顿）`-a 110`（音量）。
- 如改美式：`TTS_VOICE = "en-us"` 一行切换；音色微调改 `TTS_OPTS` 即可。
**优点**：单个 HTML 传到手机/平板离线即用，不依赖网络或托管；图标也内嵌，完全自包含。

## 2.1 「单元句型点读」标准产出（重要）
- 生成器：`scripts/gen_unit_sentences.py`（随本 Skill 提供）。
- 输入模板：`assets/family_sentences.tsv`（家庭主题样例，6 类 × 3 句 = 18 句，含中文翻译）。
- 输入格式（纯文本，用 `|` 分隔）：
  ```
  ## 分类名 | emoji码点
  英文句 | 中文翻译
  英文句 | 中文翻译
  ```
- 输出：分类分组卡片，每句一个 🔊 按钮，点即播；顶部按分类筛选；同样 100% 离线、不托管。
- **换主题复用**：把 `family_sentences.tsv` 复制改名（如 `animal_sentences.tsv`），替换分类/句子/emoji，重跑脚本即得该主题的句型点读页。

## 2.2 「宾果 Bingo 卡片游戏」标准产出（卡片类游戏）
- 生成器：`scripts/gen_bingo.py`（随本 Skill 提供）。
- 输入：`words.tsv`（同 `gen_pointread` 词表格式：`word <TAB> emoji码点 <TAB> 中文 <TAB> 分类`）。
- 可选 `--caller caller.tsv`：每行 `word <TAB> 主持人句`，主持人页会列出每个词 + 对应句子提示（如 `sunny → It is sunny today.`）。
- 输出：单个 A4 PDF，含 N 张（默认 4）**唯一** 3×3 宾果卡（中心格为「FREE 自由」）+ 1 页主持人页（全部词 + emoji + 可选句子）。
- 卡面 = 大 emoji + 英文词（图词并现，适配 5-12 岁）；每卡从词池随机抽 8 个不同词，用 `--seed` 固定可复现。
- 用法：
  ```
  python3 gen_bingo.py words.tsv 宾果卡_Bingo.pdf --cards 4 --title "天气宾果" --caller caller.tsv
  ```
- **点读联动**：把 `caller.tsv` 的句子转成句表喂给 `gen_pointread.py --mode sentence`，即得「宾果主持人点读页」，家长/老师点一下就能听主持人句。
- **换主题复用**：把 `words.tsv` / `caller.tsv` 换成新主题词即可，无需改脚本。

> 依赖：reportlab / Pillow（已预装）；emoji 用 cairosvg 渲染 Twemoji，缺失自动降级为灰圆，不阻断。

## 2.3 「一键全套可打印 PDF」标准产出（最高效路径）
- 生成器：`scripts/gen_printables.py`（随本 Skill 提供）。
- 输入：`words.tsv`（必填，词表）+ `--title "主题名"` + `--outdir OUT`（输出目录）+ `--caller caller.tsv`（可选，宾果主持人句）。
- 一键产出 9 份 PDF（默认文件名见第 1 节表格）。
- 用法：
  ```
  python3 gen_printables.py words.tsv --title "天气" --outdir ./Weather_Materials --caller caller.tsv
  ```
- 依赖：reportlab / Pillow（脚本自动检测，缺失在 root 下自动 pip 安装）；emoji 图标联网下载 Twemoji（离线降级灰圆）。
- **换主题复用**：换 `words.tsv` / `caller.tsv` 即可，无需改脚本。

## 3. 通用点读生成脚本
- `scripts/gen_pointread.py`：输入"词表/句表"→ 输出自包含点读 HTML（一词一卡 / 一句一卡）。
  - 句表支持第 4 列中文翻译（可选）；分类名若写「描述 / Describing」会**自动归一化为「形容词」**。
- `scripts/gen_unit_sentences.py`：输入"分组句型表"→ 输出"单元句型点读"分组页（见 2.1）。
- `scripts/gen_bingo.py`：输入"词表"→ 输出宾果卡 PDF（见 2.2）。
- `scripts/gen_printables.py`：输入"词表"→ 一键输出全套 9 份 PDF（见 2.3）。
- 依赖：`espeak-ng` + `ffmpeg`（点读页用）、`reportlab` + `Pillow` + `cairosvg`（PDF 用）。无外网也能生成（仅 emoji 图标会降级）。
- 输入文件请用 **UTF-8（无 BOM）** 保存；脚本已用 `utf-8-sig` 容错读取。

## 4. 复制到其他主题的做法
1. 准备 `words.tsv`（格式：`word <TAB> emoji码点 <TAB> 中文 <TAB> 分类`）；emoji 码点从 Twemoji 查对应 Unicode（如太阳 ☀ = `2600`）。
2. 准备 `caller.tsv`（可选，每行 `word <TAB> 主持人句`），用于宾果主持人页/点读。
3. 一键生成全套 PDF：`python3 scripts/gen_printables.py words.tsv --title "主题" --outdir OUT [--caller caller.tsv]`。
4. 生成点读页：
   - 单词：`python3 scripts/gen_pointread.py words.tsv 点读.html --mode word`
   - 句型：`python3 scripts/gen_pointread.py sent.tsv 点读句子.html --mode sentence`（句表格式：`英文句 <TAB> emoji码点 <TAB> 分类 <TAB> 中文`）
5. 教案套用 `references/unit-template.md`，活动套用 `references/methods.md`。
