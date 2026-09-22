---
name: kids-english-coach
description: >-
  Design and produce English learning content for children aged 5-12: preschool
  listening-vocabulary stage, Cambridge YLE→KET→PET progression, and phonics /
  grammar add-on tracks. Applies TBL, CLIL, story-based and spiral teaching;
  builds theme-based units (family, animals, school, travel…); generates
  printable + audio "point-read" materials. Aligns with Chinese primary
  Grade 1-6 curriculum. Use when the user wants kids' English lesson plans,
  unit designs, teaching materials, or printable/audio flashcards.
---

# 少儿英语培训教练 (Kids English Coach)

帮助设计 5-12 岁少儿英语课程、单元与单课，并产出可打印 + 可点读（音频）的教具。
底层框架来自"听力词汇优先 + 主题式螺旋上升 + 专项补强"，并已与中国小学 1-6 年级衔接。

## 何时使用
- 设计少儿英语课程 / 单元 / 单课（启蒙零基础 → 剑桥 YLE→KET→PET → 专项补强）
- 需要"听力词汇优先、不系统讲语法""主题式、螺旋上升""自然拼读/语法专项"等结构
- 需要可打印教具（单词卡 / 宾果 / 迷你书 / 海报）或可点读音频页
- 想把语言教学和中国小学 1-6 年级（含 PEP / 外研社 / 人教）衔接、做延伸

## 环境依赖（首次使用需安装）
本 skill 的**逻辑（教案/框架/模板）零安装**即可用；但**用脚本生成新的点读音频页 / 可打印 PDF** 依赖以下工具：

| 依赖 | 作用 | 安装（Debian/Ubuntu） | macOS |
|---|---|---|---|
| `espeak-ng` | 离线 TTS，生成英文发音（点读页用） | `sudo apt-get install -y espeak-ng` | `brew install espeak-ng` |
| `ffmpeg` | 把 wav 转 mp3 内嵌（点读页用） | `sudo apt-get install -y ffmpeg` | `brew install ffmpeg` |
| `cairosvg` (pip) | emoji 图标渲染（缺失仅降级为灰圆，不阻断） | `pip install cairosvg` | 同左 |
| `reportlab` / `Pillow` (pip) | 生成可打印 PDF（已预装环境通常已有） | `pip install reportlab pillow` | 同左 |

> **别人的机器上会自动处理吗？** 会尽力自动处理——四个生成脚本开头都有 `ensure_deps()`：
> - **root 环境（如沙箱）**：检测到缺失会自动 `apt-get`（系统包）或 `pip3`（Python 包）安装，无需手动。
> - **普通用户环境**：不自动装，会打印上面这条清晰命令后退出，不会卡死。
>
> **已生成的产物（`.html` 点读页 / `.pdf` 教具）本身是零依赖的**：音频、图标已内嵌。把文件发给任何人，用浏览器打开 / 打印即可用，无需 espeak/ffmpeg/cairosvg。
> **注意**：生成**可打印 PDF** 时，emoji 图标会从 Twemoji CDN 联网下载并本地缓存（`/tmp`），无网络时自动降级为灰色圆形，不影响其余排版。

## 必须遵守的核心原则
1. **启蒙段听力词汇优先，不系统讲语法**：6 岁前大量输入儿歌/故事/情景扮演/字母与字母音，积累"能听懂、会指认"的听力词汇；只渗透 `This is…` / `I like…` 等简单句型，**不出现语法术语**。
2. **主题式 + 螺旋上升（进阶段）**：对标剑桥 YLE→KET→PET，每单元打包 词汇+句型+语法+听说读写+小任务；能力顺序 听→说→读→写；语法点跨级别反复复现、逐级加深。
3. **词汇分两层**：认知词汇（听懂读懂）vs 四会词汇（会读会写会拼会用）；配自然拼读，让孩子自主拼读背词，不死记。
4. **学-练-测闭环**：课前预习 → 课堂互动任务 → 课后练习 + 单元测 + 阶段测评。
5. **教学法五件套**：TBL 任务型 / CLIL 内容语言融合 / 情景+故事（归纳法优先）/ SAIL 结构化主动课堂 / 螺旋式重复。详见 `references/methods.md`。

## 工作流
1. 确认学段与目标（启蒙 / 进阶某级 / 专项补强），以及是否需对接某小学年级/教材。
2. 选主题 → 用 `references/unit-template.md` 搭单元骨架（词汇 / 句型 / 语法 / 任务 / 测评）。
3. 按 `references/methods.md` 选 1-2 种教学法设计课堂活动，**优先 TBL + 故事**。
4. 产出物：
   - 教案（Markdown，可直接交付）
   - 可打印 PDF 教具（见 `references/materials.md`；最省事的是**一键生成全套**）：
     - **一键全套 9 份 PDF**：`scripts/gen_printables.py words.tsv --title "天气" --outdir OUT [--caller caller.tsv]`，详见 `references/materials.md` 2.3 节
     - 单独生成宾果卡：`scripts/gen_bingo.py words.tsv 宾果.pdf --caller caller.tsv`，详见 2.2 节
   - 点读音频页（**全部离线、自包含、不托管**）：
     - 单词点读：`scripts/gen_pointread.py --mode word`
     - 句型点读：`scripts/gen_pointread.py --mode sentence`（或分组版 `scripts/gen_unit_sentences.py`，按教案 6 类句型输出"单元句型点读"页，每句带中文翻译）
   - 分类标签规范：描述类统一显示为「形容词」（生成器已自动把"描述/Describing"归一化）。
5. 低龄内容务必"有趣、能吸引孩子"：游戏化、角色扮演、色彩与图标、短句重复。

## 参考文件（按需加载）
- `references/curriculum.md` — 三段式课程总框架 + 语法螺旋表 + 小学衔接
- `references/unit-template.md` — 可直接复制填充的单元模板
- `references/methods.md` — 五种教学法详解与课堂示例
- `references/materials.md` — 已落地教具清单与生成方式（含一键全套）

## 配套脚本
- `scripts/gen_pointread.py` — 把"词表/句表"生成自包含点读 HTML（音频 + 图标 base64 内嵌，离线可点；依赖 espeak-ng + ffmpeg 生成音频；句表支持中文翻译列；"描述"自动归一化为"形容词"）。
- `scripts/gen_unit_sentences.py` — 把"分组句型表"生成**单元句型点读**页（按分类分组、每句带中文翻译、点即播），见 `references/materials.md` 2.1 节；样例模板 `assets/family_sentences.tsv`。
- `scripts/gen_bingo.py` — 把"词表"生成可打印**宾果(Bingo)卡片游戏** PDF（N 张唯一 3×3 卡 + 主持人页，卡面图词并现），见 `references/materials.md` 2.2 节；可与点读页联动做"宾果主持人点读"。
- `scripts/gen_printables.py` — 由 `words.tsv` **一键生成全套 9 份可打印 PDF**（使用说明 / 单词卡 / 涂色卡 / 宾果 / 迷你书 / 海报 / 图卡 / 词卡 / 点读指引），自动调用 `gen_bingo.py`；依赖 reportlab/Pillow/cairosvg（emoji 图标需联网下载 Twemoji，离线自动降级为灰圆）。见 `references/materials.md` 2.3 节。
