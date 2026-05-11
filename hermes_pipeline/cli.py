"""hermes_pipeline Phase 1 CLI

Daihon export ZIP を読み、各シーン分の Grok 投入用テキストを
outputs/hermes_pipeline/<basename>/grok_inputs/scene_NN.txt に書き出す。

使い方:
    python -m hermes_pipeline.cli <zip_path> [--out OUT] [--limit N]

例 (MVP 5シーン):
    python -m hermes_pipeline.cli "C:/.../中野一花..._export_xxx.zip" --limit 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .grok_prompt_builder import build_grok_input
from .parser import parse_zip, select_scenes


def _default_out_dir(zip_path: Path) -> Path:
    base = zip_path.stem
    return Path("outputs") / "hermes_pipeline" / base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", help="Daihon export ZIP のパス")
    parser.add_argument(
        "--out",
        default=None,
        help="出力ディレクトリ (デフォルト: outputs/hermes_pipeline/<basename>/)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="先頭から N シーンのみ処理 (MVP 動作確認用、未指定で全件)",
    )
    parser.add_argument(
        "--print-scene",
        type=int,
        default=None,
        help="指定 scene_id の生成テキストを標準出力に表示（デバッグ用）",
    )
    args = parser.parse_args(argv)

    zip_path = Path(args.zip_path)
    if not zip_path.exists():
        print(f"[ERROR] ZIP not found: {zip_path}", file=sys.stderr)
        return 2

    scenes = parse_zip(zip_path)
    if not scenes:
        print("[WARN] シーンが抽出できなかった", file=sys.stderr)
        return 1

    out_dir = Path(args.out) if args.out else _default_out_dir(zip_path)
    grok_dir = out_dir / "grok_inputs"
    grok_dir.mkdir(parents=True, exist_ok=True)

    target_scenes = select_scenes(scenes, args.limit)
    print(f"[INFO] 抽出シーン総数: {len(scenes)} / 処理対象: {len(target_scenes)}")
    print(f"[INFO] 出力先: {grok_dir}")

    for sc in target_scenes:
        text = build_grok_input(sc)
        fname = grok_dir / f"scene_{sc.scene_id:03d}.txt"
        fname.write_text(text, encoding="utf-8")
        bubbles_n = len(sc.bubbles)
        lora_n = len(sc.sd_lora_tags)
        print(
            f"  - Scene {sc.scene_id:03d} → {fname.name} "
            f"(bubbles={bubbles_n}, removed_lora={lora_n})"
        )
        if args.print_scene is not None and args.print_scene == sc.scene_id:
            print("\n--- BEGIN scene text ---")
            print(text)
            print("--- END scene text ---\n")

    print(f"[DONE] {len(target_scenes)} シーン分を書き出した")
    return 0


if __name__ == "__main__":
    sys.exit(main())
