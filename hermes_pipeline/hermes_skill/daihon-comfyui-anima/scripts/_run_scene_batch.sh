#!/usr/bin/env bash
# compare_models_v2.py を setsid でデタッチして実行
# 第1引数: scene 番号 (e.g. 1), 第2引数: variants spec (省略で全15), 第3引数: log path
set -u
SCENE="${1:-1}"
VARIANTS="${2:-}"
LOG="${3:-/tmp/compare_v2_run.log}"
WORK_DIR="/mnt/f/作業/AI開発/Daihon_Rakku/outputs/hermes_pipeline/中野一花（五等分の花嫁）_export_20260506014006"
SCRIPT="/mnt/f/作業/AI開発/Daihon_Rakku/hermes_pipeline/hermes_skill/daihon-comfyui-anima/scripts/compare_models_v2.py"

if [ -n "$VARIANTS" ]; then
  VARG="--variants $VARIANTS"
else
  VARG=""
fi

cd "$(dirname "$SCRIPT")"
# setsid + nohup + 完全リダイレクトで親シェル切断時も生存させる
setsid nohup python3 "$SCRIPT" "$WORK_DIR" \
  --scene-id "$SCENE" $VARG --seed 42 --timeout 600 \
  > "$LOG" 2>&1 < /dev/null &
echo "launched pid=$! log=$LOG"
disown 2>/dev/null || true
