"""SDプロンプトから LoRA タグなど不要要素を除去する。

Daihon Rakku の現状出力は NoobAI/Illustrious系 LoRA タグ
(`<lora:NOOB_vp1_detailer_by_volnovik_v1:1>`) を含むため、
Anima 投入前に除去する。
"""

from __future__ import annotations

import re

_LORA_RE = re.compile(r"<lora:[^>]+>", re.IGNORECASE)
_MULTI_COMMA_RE = re.compile(r"(?:\s*,\s*){2,}")
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")


def strip_lora_tags(prompt: str) -> str:
    """`<lora:xxx:y>` 形式タグを除去し、連続カンマ・空白を正規化。"""
    if not prompt:
        return ""
    cleaned = _LORA_RE.sub("", prompt)
    cleaned = _MULTI_COMMA_RE.sub(", ", cleaned)
    cleaned = _MULTI_SPACE_RE.sub(" ", cleaned)
    cleaned = cleaned.strip().strip(",").strip()
    return cleaned


def extract_lora_tags(prompt: str) -> list[str]:
    """元プロンプトに含まれていた LoRA タグの一覧を返す（参考表示用）。"""
    if not prompt:
        return []
    return _LORA_RE.findall(prompt)
