"""Daihon Rakku export ZIP → 構造化シーンデータ

Daihon Rakku が出力する ZIP には以下4ファイルが含まれる:
- script_xxx.csv       : メイン構造化データ (scene_id, description, bubble_no, speaker, text, sd_prompt, onomatopoeia)
- fukidashi_xxx.csv    : 吹き出し情報 (filename, キャラ1, セリフ1, ...)
- sd_xxx.txt           : 英語自然言語シーン描写 (# Scene N: タイトル形式)
- wildcard_xxx.txt     : Wild Card用タグ列のみ

script.csv は 1シーン複数行で、scene_id/description/sd_prompt/onomatopoeia は
最初の行のみに値が入り、続く吹き出し行は空欄。本パーサは前方フィルで補完する。
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .lora_filter import extract_lora_tags, strip_lora_tags


@dataclass
class Bubble:
    bubble_no: int
    speaker: str
    text: str


@dataclass
class Scene:
    scene_id: int
    description: str
    sd_prompt_raw: str
    sd_prompt: str
    sd_lora_tags: list[str] = field(default_factory=list)
    onomatopoeia: str = ""
    sd_natural_en: str = ""
    sd_title: str = ""
    bubbles: list[Bubble] = field(default_factory=list)


_SD_HEADER_RE = re.compile(r"^#\s*Scene\s+(\d+)\s*:\s*(.*)$")


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _find_member(zf: zipfile.ZipFile, prefix: str, suffix: str) -> str:
    for name in zf.namelist():
        base = Path(name).name.lower()
        if base.startswith(prefix.lower()) and base.endswith(suffix.lower()):
            return name
    raise FileNotFoundError(f"ZIP に {prefix}*{suffix} が見つからない")


def parse_script_csv(text: str) -> dict[int, dict]:
    """script.csv をパース。scene_id ごとに dict を返す。"""
    reader = csv.DictReader(io.StringIO(text))
    scenes: dict[int, dict] = {}
    current_id: int | None = None
    current_desc = ""
    current_sd = ""
    current_ono = ""

    for row in reader:
        sid_raw = (row.get("scene_id") or "").strip()
        if sid_raw:
            try:
                current_id = int(sid_raw)
            except ValueError:
                continue
            current_desc = (row.get("description") or "").strip()
            current_sd = (row.get("sd_prompt") or "").strip()
            current_ono = (row.get("onomatopoeia") or "").strip()
            scenes[current_id] = {
                "description": current_desc,
                "sd_prompt": current_sd,
                "onomatopoeia": current_ono,
                "bubbles": [],
            }

        if current_id is None:
            continue

        bubble_no_raw = (row.get("bubble_no") or "").strip()
        speaker = (row.get("speaker") or "").strip()
        text_val = (row.get("text") or "").strip()
        if bubble_no_raw and (speaker or text_val):
            try:
                bn = int(bubble_no_raw)
            except ValueError:
                bn = len(scenes[current_id]["bubbles"]) + 1
            scenes[current_id]["bubbles"].append(
                Bubble(bubble_no=bn, speaker=speaker, text=text_val)
            )

    return scenes


def parse_sd_txt(text: str) -> dict[int, tuple[str, str]]:
    """sd_xxx.txt をパース。scene_id → (title, body)。"""
    result: dict[int, tuple[str, str]] = {}
    current_id: int | None = None
    current_title = ""
    buf: list[str] = []

    def _flush():
        if current_id is not None:
            body = "\n".join(buf).strip()
            result[current_id] = (current_title, body)

    for line in text.splitlines():
        m = _SD_HEADER_RE.match(line.strip())
        if m:
            _flush()
            current_id = int(m.group(1))
            current_title = m.group(2).strip()
            buf = []
        else:
            buf.append(line)
    _flush()
    return result


def _merge(
    script_data: dict[int, dict],
    sd_data: dict[int, tuple[str, str]],
) -> list[Scene]:
    scenes: list[Scene] = []
    for sid in sorted(script_data.keys()):
        rec = script_data[sid]
        sd_title, sd_body = sd_data.get(sid, ("", ""))
        raw_prompt = rec["sd_prompt"]
        scenes.append(
            Scene(
                scene_id=sid,
                description=rec["description"],
                sd_prompt_raw=raw_prompt,
                sd_prompt=strip_lora_tags(raw_prompt),
                sd_lora_tags=extract_lora_tags(raw_prompt),
                onomatopoeia=rec["onomatopoeia"],
                sd_natural_en=sd_body,
                sd_title=sd_title,
                bubbles=list(rec["bubbles"]),
            )
        )
    return scenes


def parse_zip(zip_path: str | Path) -> list[Scene]:
    """Daihon export ZIP を読み、シーン構造化データのリストを返す。"""
    zip_path = Path(zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)

    with zipfile.ZipFile(zip_path, "r") as zf:
        script_name = _find_member(zf, "script_", ".csv")
        sd_name = _find_member(zf, "sd_", ".txt")
        script_text = _decode(zf.read(script_name))
        sd_text = _decode(zf.read(sd_name))

    script_data = parse_script_csv(script_text)
    sd_data = parse_sd_txt(sd_text)
    return _merge(script_data, sd_data)


def select_scenes(scenes: Iterable[Scene], limit: int | None = None) -> list[Scene]:
    out = list(scenes)
    if limit is not None and limit > 0:
        out = out[:limit]
    return out
