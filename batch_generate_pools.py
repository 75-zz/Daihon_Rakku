"""
batch_generate_pools.py
255体プリセット一括プール生成CLIスクリプト

Usage:
    python batch_generate_pools.py              # 全プリセットのプール生成
    python batch_generate_pools.py --dry-run    # 解析のみ（ファイル書き込みなし）
    python batch_generate_pools.py --force      # 既存プール上書き
    python batch_generate_pools.py --char char_200_001  # 単体指定
"""

import argparse
import json
import sys
import time
from pathlib import Path

from character_pool_generator import (
    generate_character_pool_local,
    detect_personality_type,
    get_pool_stats,
)

PRESET_CHARS_DIR = Path(__file__).parent / "presets" / "characters"


def scan_presets(char_filter: str = None) -> list[Path]:
    """プリセットキャラJSONをスキャン（_pool.json除外）"""
    if not PRESET_CHARS_DIR.exists():
        print(f"[ERROR] プリセットディレクトリが見つかりません: {PRESET_CHARS_DIR}")
        sys.exit(1)

    files = sorted(PRESET_CHARS_DIR.glob("*.json"))
    files = [f for f in files if "_pool.json" not in f.name]

    if char_filter:
        files = [f for f in files if char_filter in f.stem]

    return files


def main():
    parser = argparse.ArgumentParser(description="プリセットキャラのローカルプール一括生成")
    parser.add_argument("--dry-run", action="store_true", help="解析のみ（ファイル書き込みなし）")
    parser.add_argument("--force", action="store_true", help="既存プール上書き")
    parser.add_argument("--char", type=str, default=None, help="単体キャラID指定")
    args = parser.parse_args()

    preset_files = scan_presets(args.char)
    total = len(preset_files)
    print(f"[INFO] プリセットキャラ: {total}体")

    if args.dry_run:
        print("[MODE] ドライラン（ファイル書き込みなし）")
    if args.force:
        print("[MODE] 強制上書き")

    generated = 0
    skipped = 0
    errors = 0
    personality_counts = {}
    start_time = time.time()

    for i, preset_file in enumerate(preset_files, 1):
        char_id = preset_file.stem
        pool_path = PRESET_CHARS_DIR / f"{char_id}_pool.json"

        try:
            with open(preset_file, "r", encoding="utf-8") as f:
                bible = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  [{i}/{total}] [ERROR] {char_id}: {e}")
            errors += 1
            continue

        char_name = bible.get("character_name", "不明")
        personality = detect_personality_type(bible)
        personality_label = personality if personality else "(default)"
        personality_counts[personality_label] = personality_counts.get(personality_label, 0) + 1

        # 既存プールチェック
        if pool_path.exists() and not args.force:
            if not args.dry_run:
                print(f"  [{i}/{total}] [SKIP] {char_name} ({char_id}) - プール既存")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  [{i}/{total}] [DRY] {char_name} ({char_id}) 性格={personality_label}")
            generated += 1
            continue

        # プール生成
        pool = generate_character_pool_local(bible)
        stats = get_pool_stats(pool)

        with open(pool_path, "w", encoding="utf-8") as f:
            json.dump(pool, f, ensure_ascii=False, indent=2)

        print(f"  [{i}/{total}] [OK] {char_name} ({char_id}) "
              f"性格={personality_label} "
              f"moan={stats['moan']} speech={stats['speech']} thought={stats['thought']}")
        generated += 1

    elapsed = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"[結果] 生成={generated} スキップ={skipped} エラー={errors} / 合計={total}")
    print(f"[時間] {elapsed:.1f}秒")
    print(f"\n[性格タイプ分布]")
    for ptype, count in sorted(personality_counts.items(), key=lambda x: -x[1]):
        print(f"  {ptype}: {count}体")


if __name__ == "__main__":
    main()
