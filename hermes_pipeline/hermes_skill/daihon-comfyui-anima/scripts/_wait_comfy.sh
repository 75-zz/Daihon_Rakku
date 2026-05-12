#!/usr/bin/env bash
# ComfyUI 起動完了待ちユーティリティ
for i in $(seq 1 90); do
  if curl -s --max-time 2 http://localhost:8188/system_stats > /tmp/comfy_stat.json 2>/dev/null; then
    echo "READY after ${i}s"
    python3 -c "import json; d=json.load(open('/tmp/comfy_stat.json')); print('device:', d.get('devices',[{}])[0].get('name',''))" 2>&1 || true
    exit 0
  fi
  sleep 1
done
echo "TIMEOUT after 90s"
tail -40 /tmp/comfy_launch.log 2>&1 || true
exit 1
