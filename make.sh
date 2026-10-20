#!/usr/bin/env bash
# 一键出片入口。零参数检查、缺依赖直接报错，不做花活。
#
#   ./make.sh A-001              # 用本机 Qwen3-TTS 出片（默认）
#   ./make.sh A-001 --none       # 无声样片，只验版式（~30 秒出片）
#   ./make.sh A-001 --edge       # 备用英语配音
#   ./make.sh --list             # 列出所有待渲染脚本
#   ./make.sh --all --none       # 批量出无声版
set -euo pipefail
cd "$(dirname "$0")"

EP_DIR="scripts/episodes"

need() { command -v "$1" >/dev/null 2>&1 || { echo "缺少依赖: $1" >&2; exit 1; }; }
need ffmpeg; need ffprobe; need python3
python3 -c "import PIL" 2>/dev/null || { echo "缺少依赖: pillow (pip install pillow)" >&2; exit 1; }

resolve() {
  local key="$1"
  local hit
  hit=$(find "$EP_DIR" -maxdepth 1 -name "${key}-*.md" | sort | head -1)
  [ -n "$hit" ] || { echo "找不到脚本: $EP_DIR/${key}-*.md" >&2; exit 1; }
  printf '%s\n' "$hit"
}

TTS="qwen"; TARGETS=()
for arg in "$@"; do
  case "$arg" in
    --none) TTS="none" ;;
    --edge) TTS="edge" ;;
    --qwen) TTS="qwen" ;;
    --list) ls -1 "$EP_DIR"/*.md 2>/dev/null | sed 's|.*/||; s|\.md$||'; exit 0 ;;
    --all)  while IFS= read -r f; do TARGETS+=("$f"); done < <(find "$EP_DIR" -maxdepth 1 -name "*.md" | sort) ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) TARGETS+=("$(resolve "$arg")") ;;
  esac
done

[ ${#TARGETS[@]} -gt 0 ] || { echo "用法: ./make.sh <EP编号|--list|--all> [--none|--edge]" >&2; exit 2; }

for f in "${TARGETS[@]}"; do
  echo "==> 渲染 $f (tts=$TTS)"
  python3 scripts/render.py "$f" --tts "$TTS"
done
echo "==> 完成。成片: renders/成片/  字幕: subtitles/"
