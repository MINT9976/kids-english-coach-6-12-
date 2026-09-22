#!/usr/bin/env bash
# install.sh — 将 kids-english-coach 技能安装到 WorkBuddy 技能目录
#
# 适用：macOS / Linux / WSL / Git Bash（bash 环境）
# Windows 原生（无 bash）请用 README 中的 PowerShell 命令，或手动复制文件夹。
#
# 用法：
#   bash install.sh
#   CODEBUDDY_SKILLS_DIR=/custom/path bash install.sh   # 指定目标目录

set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"          # 本脚本所在目录（kids-english-coach/）
SKILL_NAME="kids-english-coach"

# ---- 确定目标目录 ----
if [ -n "${CODEBUDDY_SKILLS_DIR:-}" ]; then
  TARGET="$CODEBUDDY_SKILLS_DIR"
elif [ "$(uname -s 2>/dev/null || echo Linux)" = "Darwin" ] || [ "$(uname -s 2>/dev/null || echo Linux)" = "Linux" ]; then
  TARGET="$HOME/.codebuddy/skills"
else
  TARGET="$HOME/.codebuddy/skills"            # WSL / 其它回退
fi

DEST="$TARGET/$SKILL_NAME"

echo "== kids-english-coach 安装器 =="
echo "源目录 : $SRC"
echo "目标目录: $DEST"
echo

mkdir -p "$TARGET"

# ---- 已存在则询问 ----
if [ -e "$DEST" ] && [ -n "$(ls -A "$DEST" 2>/dev/null)" ]; then
  read -r -p "目标已存在，覆盖安装? (y/N): " ans
  case "$ans" in
    y|Y) rm -rf "$DEST" ;;
    *) echo "已取消。"; exit 0 ;;
  esac
fi

cp -R "$SRC" "$DEST"
echo "✅ 已安装到: $DEST"

# ---- 依赖检查 ----
echo
echo "== 依赖检查 =="
MISSING=()
command -v espeak-ng >/dev/null 2>&1 || MISSING+=("espeak-ng")
command -v ffmpeg   >/dev/null 2>&1 || MISSING+=("ffmpeg")
python3 -c "import reportlab" 2>/dev/null || MISSING+=("python:reportlab")
python3 -c "import cairosvg"  2>/dev/null || MISSING+=("python:cairosvg")
python3 -c "import PIL"       2>/dev/null || MISSING+=("python:pillow")

if [ ${#MISSING[@]} -eq 0 ]; then
  echo "✅ 依赖齐全，开箱即用。"
else
  echo "⚠ 缺少依赖: ${MISSING[*]}"
  echo "   Debian/Ubuntu: sudo apt-get install -y espeak-ng ffmpeg && pip install reportlab cairosvg pillow"
  echo "   macOS:         brew install espeak-ng ffmpeg && pip install reportlab cairosvg pillow"
  echo "   (root 环境下生成脚本会自动安装，通常无需手动)"
fi

echo
echo "== 完成 =="
echo "在 WorkBuddy 中尝试: 给 7 岁孩子做一个 Movers 级天气主题单元教案，并补齐全套可打印 PDF"
echo "演示样例见同包 samples/Weather_Materials/"
