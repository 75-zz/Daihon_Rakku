"""Daihon ComfyUI Anima — Step 1: prepare_prompt

Grok 応答 (scene_NNN_response.txt) から English version 部分を抽出し、
Anima 推奨品質タグを前置 + 最小ネガを生成して
anima_prompts/scene_NNN_prompt.json に保存する。

JSON 形式:
{
  "scene_id": N,
  "positive": "score_9, ... <抽出した English 本文>",
  "negative": "worst quality, bad anatomy, ...",
  "source": "<元の response ファイルパス>"
}

使い方:
    python3 prepare_prompt.py extract <work_dir> [--scene-id N] [--limit N]
    python3 prepare_prompt.py status <work_dir>

`<work_dir>` は `outputs/hermes_pipeline/<basename>/` で、
`grok_responses/scene_NNN_response.txt` を読み、
`anima_prompts/scene_NNN_prompt.json` を書く。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# English 見出しの様々な形式に対応:
#   # English version (ComfyUI / Anima 投入用)
#   【English Version（ComfyUI / Anima投入用）】
#   English version
_EN_HEADING_RE = re.compile(
    r"(?:^|\n)\s*(?:#+\s*|【)?English\s+[Vv]ersion[^\n]*\n",
    re.IGNORECASE,
)

# Dialogue / Sound effects セクション以降を切り捨てるパターン
# Anima Qwen3 TE がセリフ・擬音テキストを画像に文字として描画してしまうため除去する
_DIALOGUE_HEADING_RE = re.compile(
    r"\n\s*(?:#+\s*|【)?(?:Dialogue|Dialog|Sound\s+effects?|Onomatopoeia)\b[^\n]*",
    re.IGNORECASE,
)

# 残った引用符付き行を除去するパターン
# 例: `[1] Nakano Ichika (small voice): "Huh… why is..."`
#     `"Huh… why is..."`
_QUOTED_LINE_RE = re.compile(
    r'^\s*(?:\[\d+\][^"\n]*:\s*)?"[^"\n]*"\s*$',
    re.MULTILINE,
)

# 中文・日本語の引用括弧『 「 」 』 など
_QUOTED_LINE_JP_RE = re.compile(
    r'^\s*[「『][^」』\n]*[」』]\s*$',
    re.MULTILINE,
)

_RESPONSE_NAME_RE = re.compile(r"^scene_(\d+)_response\.txt$")

# Anima 推奨品質タグ + アニメ志向強化キーワード
# CG ガイド §06 ベース + 西洋寄り作画になる問題への対策
_ANIMA_QUALITY_PREFIX = (
    "score_9, score_8_up, score_7_up, masterpiece, best quality, "
    "highres, year 2025, newest, sensitive,\n"
    "anime style, anime illustration, 2d anime art, cel shading, "
    "japanese anime aesthetic, soft lighting,\n"
)

# 詳細ネガ: テキスト混入防止 + 西洋風除去 + 通常の品質ネガ
_DEFAULT_NEGATIVE = (
    "text, speech bubble, dialogue, subtitle, watermark, signature, "
    "english text, letters, caption, words, logo, font, "
    "3d, realistic, photorealistic, photo, semi-realistic, "
    "american comic, western, marvel style, dc style, comic book, "
    "worst quality, low quality, bad anatomy, bad hands, "
    "deformed, blurry, jpeg artifacts, extra digit, missing fingers"
)


def clean_for_anima(text: str) -> str:
    """English version 本文から Anima 投入に不適な部分を除去。

    - `Dialogue:` `Sound effects:` 見出し以降を切り捨て (Anima が文字を描画するため)
    - 残った引用符付き行を除去
    - 連続改行を整理
    """
    if not text:
        return text
    # Step 1: Dialogue/Sound effects 見出しから末尾までを切り捨て
    m = _DIALOGUE_HEADING_RE.search(text)
    if m:
        text = text[: m.start()]
    # Step 2: 引用符付き行を除去 (英語 "..." と 日本語 「...」)
    text = _QUOTED_LINE_RE.sub("", text)
    text = _QUOTED_LINE_JP_RE.sub("", text)
    # Step 3: 3行以上連続する空行を 1 空行に
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_english(response_text: str) -> str | None:
    """応答テキストから English version 以降の本文を抽出。

    見出し行は除き、その後ろから末尾までを返す。
    Anima 用に Dialogue / Sound effects セクションを除去するクリーン処理も適用。
    見出しが見つからなければ None。
    """
    m = _EN_HEADING_RE.search(response_text)
    if not m:
        return None
    body = response_text[m.end():].strip()
    if not body:
        return None
    return clean_for_anima(body)


def build_positive_prompt(english_body: str) -> str:
    return _ANIMA_QUALITY_PREFIX + english_body


def _output_dir(work_dir: Path) -> Path:
    d = work_dir / "anima_prompts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _list_response_scene_ids(work_dir: Path) -> list[int]:
    rd = work_dir / "grok_responses"
    if not rd.exists():
        return []
    ids: list[int] = []
    for f in rd.iterdir():
        m = _RESPONSE_NAME_RE.match(f.name)
        if m:
            ids.append(int(m.group(1)))
    return sorted(ids)


def process_scene(response_path: Path, output_dir: Path, scene_id: int) -> dict:
    raw = response_path.read_text(encoding="utf-8")
    english = extract_english(raw)
    if english is None:
        return {"scene_id": scene_id, "ok": False, "error": "english_section_not_found"}
    positive = build_positive_prompt(english)
    payload = {
        "scene_id": scene_id,
        "positive": positive,
        "negative": _DEFAULT_NEGATIVE,
        "source": str(response_path),
    }
    out = output_dir / f"scene_{scene_id:03d}_prompt.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "scene_id": scene_id,
        "ok": True,
        "output": str(out),
        "positive_chars": len(positive),
        "english_body_chars": len(english),
    }


def cmd_extract(work_dir: Path, scene_id: int | None, limit: int | None) -> int:
    response_dir = work_dir / "grok_responses"
    output_dir = _output_dir(work_dir)

    if scene_id is not None:
        targets = [scene_id]
    else:
        targets = _list_response_scene_ids(work_dir)
        if limit is not None and limit > 0:
            targets = targets[:limit]

    results: list[dict] = []
    for sid in targets:
        rp = response_dir / f"scene_{sid:03d}_response.txt"
        if not rp.exists():
            results.append({"scene_id": sid, "ok": False, "error": "response_not_found"})
            continue
        results.append(process_scene(rp, output_dir, sid))

    print(json.dumps(
        {"results": results, "count": len(results), "ok_count": sum(1 for r in results if r["ok"])},
        ensure_ascii=False, indent=2,
    ))
    return 0 if all(r["ok"] for r in results) else 1


def cmd_status(work_dir: Path) -> int:
    response_ids = _list_response_scene_ids(work_dir)
    out_dir = _output_dir(work_dir)
    done = sorted(
        int(m.group(1))
        for f in out_dir.glob("scene_*_prompt.json")
        if (m := re.match(r"scene_(\d+)_prompt\.json", f.name))
    )
    pending = [i for i in response_ids if i not in done]
    payload = {
        "response_count": len(response_ids),
        "prompt_done_count": len(done),
        "pending_count": len(pending),
        "done": done,
        "pending": pending,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ex = sub.add_parser("extract", help="grok_responses から English 抽出+Anima品質タグ前置")
    p_ex.add_argument("work_dir")
    p_ex.add_argument("--scene-id", type=int, default=None)
    p_ex.add_argument("--limit", type=int, default=None)

    p_st = sub.add_parser("status", help="抽出進捗 JSON")
    p_st.add_argument("work_dir")

    args = parser.parse_args(argv)
    work_dir = Path(args.work_dir)
    if not work_dir.exists():
        print(f"[ERROR] work_dir not found: {work_dir}", file=sys.stderr)
        return 2

    if args.cmd == "extract":
        return cmd_extract(work_dir, args.scene_id, args.limit)
    if args.cmd == "status":
        return cmd_status(work_dir)
    return 1


if __name__ == "__main__":
    sys.exit(main())
