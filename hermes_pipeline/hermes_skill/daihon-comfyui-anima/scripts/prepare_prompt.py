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

# 本文中に埋め込まれた引用符付き擬音/セリフを除去するパターン。
# Anima が引用符内テキストを画像に文字として描画する事故を防ぐ。
# 例: '...with a dizzy "fading…" sensation.' → '...with a dizzy  sensation.'
#     '...after saying "It\'s okay, keep your eyes open."' → '...after saying .'
# 200 文字以下の短い引用符ペアのみ対象 (長すぎる引用は安全策で除外)。
_QUOTED_INLINE_RE = re.compile(r'"[^"\n]{0,200}"')
_QUOTED_INLINE_JP_RE = re.compile(r'[「『][^「『」』\n]{0,200}[」』]')

_RESPONSE_NAME_RE = re.compile(r"^scene_(\d+)_response\.txt$")

# Grok 英文中の "Clothing state:" ブロックを除去するパターン。
# キャラクターごとに 1 ブロック存在し、次のセクション見出しまでを削除する。
# 想定する2つの形式:
#   形式A (見出しの直後に改行+本文):
#       Clothing state:
#       White blouse with one button undone...
#       Immediate aftermath:
#   形式B (見出しと本文が同一行):
#       Clothing state: White blouse with one button undone...
#       Immediate aftermath:
# 次のセクション見出し = 行頭が英単語+スペース/&/+英単語*(: で終わる) OR
#                     [Composition] 等の [...] OR Faceless Male/Nakano Ichika 等のキャラ名行
# DOTALL + lazy で形式 A/B 両方に対応する。
_CLOTHING_STATE_BLOCK_RE = re.compile(
    r"^[ \t]*Clothing\s+state:.*?"
    r"(?=\n[ \t]*(?:[A-Z][A-Za-z /&-]+:|Faceless\s+Male\b|Nakano\b|\[)|\Z)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)

# Anima 推奨品質タグ + アニメ志向強化キーワード (v1 / 後方互換)
_ANIMA_QUALITY_PREFIX = (
    "score_9, score_8_up, score_7_up, masterpiece, best quality, "
    "highres, year 2025, newest, sensitive,\n"
    "anime style, anime illustration, 2d anime art, cel shading, "
    "japanese anime aesthetic, soft lighting,\n"
)

# AnimaYume 最適化 quality prefix
# 公式推奨ミニマル + score_X と masterpiece の併用 OK (Anima docs)
# 非 Danbooru タグ (anime style/cel shading 等) は削除し Qwen3 TE のノイズを減らす
_ANIMAYUME_QUALITY_PREFIX = (
    "masterpiece, best quality, very aesthetic, score_9, score_8_up, "
    "year 2025, newest, safe, highres,\n"
)

# キャラクター固定タグブロックは Daihon Rakku 側で確定する設計に変更 (2026-05-12)
# work_dir/character.json から動的に読み込み build_char_block_from_json で構築する。
# 旧 hardcoded テンプレは LLM のハルシネーション (orange_hair / long_hair 等) を含んでいたため廃止。

# 詳細ネガ: テキスト混入防止 + 西洋風除去 + 通常の品質ネガ (v1 / 後方互換)
_DEFAULT_NEGATIVE = (
    "text, speech bubble, dialogue, subtitle, watermark, signature, "
    "english text, letters, caption, words, logo, font, "
    "3d, realistic, photorealistic, photo, semi-realistic, "
    "american comic, western, marvel style, dc style, comic book, "
    "worst quality, low quality, bad anatomy, bad hands, "
    "deformed, blurry, jpeg artifacts, extra digit, missing fingers"
)

# AnimaYume 公式推奨 negative (最小版) + テキスト/吹き出し系完全除外
# - SD1.5 時代の anatomy ネガは Anima のスコア蒸留モデルで逆効果になり得るため除外
# - speech_bubble / dialogue / talking 系は CG集台本 (1P1枚) では完全に不要
#   (CLAUDE.md「SDプロンプトに吹き出し/擬音/ネガティブを入れない」ポリシーは画面内テキスト除去)
_ANIMAYUME_NEGATIVE_MIN = (
    "worst quality, low quality, score_1, score_2, score_3, artist name, "
    "text, watermark, signature, "
    "speech_bubble, dialogue, speech, talking, comic, caption, onomatopoeia, sound_effect, "
    "english_text, japanese_text, kanji, hiragana, katakana, "
    "letters, words, sign, character_name, manga_panel, manga, 4koma, "
    "comic_panel, page_number, copyright_name"
)

_QUALITY_PRESETS: dict[str, str] = {
    "current": _ANIMA_QUALITY_PREFIX,
    "animayume_min": _ANIMAYUME_QUALITY_PREFIX,
}
_NEGATIVE_PRESETS: dict[str, str] = {
    "current": _DEFAULT_NEGATIVE,
    "animayume_min": _ANIMAYUME_NEGATIVE_MIN,
}


def clean_for_anima(text: str) -> str:
    """English version 本文から Anima 投入に不適な部分を除去。

    - `Dialogue:` `Sound effects:` 見出し以降を切り捨て (Anima が文字を描画するため)
    - 引用符付き行を除去 (行全体)
    - 本文中に埋め込まれた引用符ペア (擬音 / セリフ片) を除去
    - 連続改行を整理
    """
    if not text:
        return text
    # Step 1: Dialogue/Sound effects 見出しから末尾までを切り捨て
    m = _DIALOGUE_HEADING_RE.search(text)
    if m:
        text = text[: m.start()]
    # Step 2: 引用符付き行を除去 (英語 "..." と 日本語 「...」 — 行全体型)
    text = _QUOTED_LINE_RE.sub("", text)
    text = _QUOTED_LINE_JP_RE.sub("", text)
    # Step 2.5: 本文中の引用符ペアを除去 (画面内文字化防止)
    text = _QUOTED_INLINE_RE.sub("", text)
    text = _QUOTED_INLINE_JP_RE.sub("", text)
    # Step 3: 二重スペース整理 (引用符削除で空白が連続する場合)
    text = re.sub(r" {2,}", " ", text)
    # Step 4: 3行以上連続する空行を 1 空行に
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


# Grok 出力本文中のキャラ・シリーズタグ行を検出するパターン
# 例: `nakano_ichika, go-toubun_no_hanayome,`
_GROK_CHAR_TAG_LINE_RE = re.compile(
    r"^\s*[a-z][a-z0-9_]*(?:\s*,\s*[a-z][a-z0-9_-]*)+\s*,?\s*$",
    re.IGNORECASE,
)


def load_character_json(work_dir: Path) -> dict | None:
    """work_dir/character.json を読み込んで dict を返す。なければ None。"""
    p = work_dir / "character.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def build_char_block_from_json(character: dict, progression: dict | None = None) -> str:
    """character.json から AnimaYume Qwen3 TE 最適化の char_block を構築。

    AnimaYume の Qwen3 TE は自然言語に強い。タグ並列だけだとキャラ間の属性
    (服色 / muscular 等) が混線する事故が起きるため、**キャラ別に「タグ群 +
    自然言語帰属文」をペアで配置**し、Qwen3 TE が「これは女性のもの / これは
    男性のもの」と確実に紐付けられる構造にする。

    出力構造:
        Line 1: (<char_tag>:<weight>), <series_tag>,
        Line 2: 1girl, <visual_features tags...>,                       # 女性タグ群
        Line 3: <heroine_outfit.outfit_tags>,                           # 女性衣装タグ群
        Line 4 (自然言語): The girl is a young woman with ...           # 女性外見 (NL)
        Line 5 (自然言語): The girl is wearing ...                      # 女性衣装 (NL帰属明示)
        Line 6: 1boy, faceless_male, <male_companion.outfit_tags>,      # 男性タグ群
        Line 7 (自然言語): Beside her is a faceless muscular man ...    # 男性属性+衣装 (NL帰属明示)

    キャラごとに「タグ → 自然言語」と続けることで、Qwen3 TE が直前のタグ群を
    直後の自然言語文の主語に帰属付ける。これにより `muscular` が女性に転移する
    等の事故を防ぐ (ユーザー報告: scene_001 で一花の腕ムキムキ問題)。
    """
    if not character:
        return ""
    tags: list[str] = list(character.get("danbooru_tags") or [])
    if not tags:
        return ""
    progression = progression or {}
    meta = character.get("anima_meta") or {}
    char_tag = meta.get("character_tag") or ""
    series_tag = meta.get("series_tag") or ""
    weight = meta.get("weight") or 1.0
    with_male = bool(meta.get("with_faceless_male")) and not progression.get("male_absent")

    # 1) 識別タグ (キャラ名 + シリーズ)
    head_parts: list[str] = []
    if char_tag:
        if abs(weight - 1.0) > 1e-6:
            head_parts.append(f"({char_tag}:{weight})")
        else:
            head_parts.append(char_tag)
    if series_tag:
        head_parts.append(series_tag)
    line_id = ", ".join(head_parts) + "," if head_parts else ""

    # 2) 女性視覚特徴タグ (キャラ名/シリーズ/solo 除外)
    visual_features = [t for t in tags if t not in {char_tag, series_tag, "solo"}]
    line_female_tags = ", ".join(visual_features) + "," if visual_features else ""

    # 3) 女性衣装タグ
    # progression.effective_stage で段階別の制御 (0=dressed, 4=nude, 1-3=partial)。
    # 段階 4: base outfit を完全裸タグに置換。
    # 段階 1-3: base outfit を維持しつつ、段階別の追加タグ (off_shoulder, panties_aside 等) を付与。
    # 段階 0: base outfit のみ。
    # effective_stage は bridge_stage_jump で前シーンとのジャンプを抑制した値が入る。
    heroine_outfit = character.get("heroine_outfit") or {}
    heroine_outfit_tags = heroine_outfit.get("outfit_tags") or []
    effective_stage = int(progression.get("effective_stage", _STAGE_DRESSED))
    add_tags = _STAGE_ADD_TAGS.get(effective_stage, [])
    if effective_stage == _STAGE_NUDE:
        line_female_outfit = _HEROINE_NUDE_TAGS + ","
    else:
        combined = list(heroine_outfit_tags) + list(add_tags)
        line_female_outfit = ", ".join(combined) + "," if combined else ""

    # 4) 女性外見の自然言語 (任意)
    appearance_sentence = (character.get("appearance_sentence_en") or "").strip()

    # 5) 女性衣装の自然言語 (帰属明示で muscular 等の転移防止)
    # 段階別の脱衣状態フォールバックを base 帰属文に追記。
    base_attrib = (heroine_outfit.get("attribution_sentence_en") or "").strip()
    if effective_stage == _STAGE_NUDE:
        heroine_attrib = _HEROINE_NUDE_NL
    elif effective_stage in (_STAGE_BLOUSE_OPEN, _STAGE_TOPLESS_PARTIAL, _STAGE_PANTIES_ASIDE):
        stage_nl = _STAGE_ADD_NL.get(effective_stage, "")
        if base_attrib and stage_nl:
            heroine_attrib = base_attrib + " " + stage_nl
        else:
            heroine_attrib = base_attrib or stage_nl
    else:
        heroine_attrib = base_attrib

    parts = [line_id, line_female_tags, line_female_outfit]
    if appearance_sentence:
        parts.append(appearance_sentence)
    if heroine_attrib:
        parts.append(heroine_attrib)

    # 6+7) 男性ブロック (タグ + 自然言語帰属文)
    # appearance_tags (体型/髪/肌) と outfit_tags (衣装) を分けて持つ。
    # Daihon Rakku の config.json の male_preset / male_hair_style / male_hair_color /
    # male_skin_color から派生したタグを appearance_tags に保持し、Anima に確実に伝える。
    if with_male:
        male_companion = character.get("male_companion") or {}
        male_appearance = male_companion.get("appearance_tags") or []
        male_outfit_tags = male_companion.get("outfit_tags") or []
        # progression.male_nude の場合は male outfit_tags を完全に外す。
        # それ以外は base outfit を保持し、進行タグ (pants_pull / shirt_lift / penis) を追記する。
        if progression.get("male_nude"):
            male_outfit_tags = []
        progression_tags: list[str] = []
        if progression.get("male_pants_down"):
            progression_tags.append(_MALE_PANTS_DOWN_TAG)
        if progression.get("male_shirt_up"):
            progression_tags.append(_MALE_SHIRT_UP_TAG)
        if progression.get("male_penis_exposed"):
            progression_tags.append(_MALE_PENIS_TAG)
        if progression.get("male_nude"):
            progression_tags.append(_MALE_NUDE_TAGS)
        male_tag_parts = (
            ["1boy", "faceless_male"]
            + list(male_appearance)
            + list(male_outfit_tags)
            + progression_tags
        )
        parts.append(", ".join(male_tag_parts) + ",")
        male_attrib = (male_companion.get("attribution_sentence_en") or "").strip()
        if male_attrib:
            parts.append(male_attrib)

    return "\n".join(p for p in parts if p) + "\n"


def build_negative_extras_from_json(character: dict) -> str:
    """character.json の負側タグ群 (キャラ + 衣装) を ", " で連結。"""
    if not character:
        return ""
    extras: list[str] = list(character.get("danbooru_tags_negative") or [])
    heroine_outfit = character.get("heroine_outfit") or {}
    extras.extend(heroine_outfit.get("negative_outfit_tags") or [])
    male_companion = character.get("male_companion") or {}
    extras.extend(male_companion.get("negative_outfit_tags") or [])
    # 重複除去 (順序維持)
    seen: set[str] = set()
    uniq = []
    for t in extras:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    return ", ".join(uniq)


def strip_grok_char_tags(english_body: str, char_tag: str, series_tag: str) -> str:
    """Grok 本体冒頭のキャラタグ行 (例: `nakano_ichika, go-toubun_no_hanayome,`) を除去。

    char_block を別経路で前置するため、Grok 出力中の重複/ハルシネーションを抑制する。
    """
    if not english_body:
        return english_body
    lines = english_body.split("\n")
    keep_from = 0
    for i, line in enumerate(lines):
        stripped = line.strip().rstrip(",").strip()
        if not stripped:
            continue
        toks = [t.strip().lower() for t in stripped.split(",") if t.strip()]
        # 行に含まれるトークンの大半が「キャラ/シリーズタグ」と「視覚特徴タグ」のみで構成
        # されている場合のみ削除対象とする (本文への誤マッチ回避)
        if char_tag and char_tag.lower() in toks:
            keep_from = i + 1
            continue
        if series_tag and series_tag.lower() in toks:
            keep_from = i + 1
            continue
        break
    return "\n".join(lines[keep_from:]).strip()


def strip_clothing_state_blocks(body: str) -> str:
    """Grok 英文本体中の "Clothing state:" ブロックを全て除去する。

    character.json の danbooru_tags / outfit_tags で衣装を固定するため、
    Grok が生成した自然言語の衣装記述はノイズとして削除する。
    "Clothing state:" 行が存在しない場合は何もしない (後方互換)。
    """
    cleaned = _CLOTHING_STATE_BLOCK_RE.sub("", body)
    # 3 行以上連続する空行を 1 空行に (除去後に空白が増える場合がある)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


# 衣装進行の意味判定キーワード (英語版 Clothing state ブロック内をスキャン)
# Grok 出力では heroine → male の順に Clothing state ブロックが現れる前提。
_HEROINE_NUDE_KEYWORDS = (
    "completely nude",
    "fully nude",
    "completely naked",
    "fully naked",
    "stark naked",
    "all clothing has been removed",
    "all clothing removed",
    "all clothes removed",
    "all clothes have been removed",
    "no clothing on her body",
    "nothing covering her",
    "nothing covering her body",
    "naked body",
)
_HEROINE_PARTIAL_KEYWORDS = (
    "lifted up", "pushed up", "rolled up", "pulled aside", "pulled down",
    "unbuttoned", "open", "rolled to", "around her waist", "around her thighs",
    "around her ankles", "panties down", "panties pulled",
)
_MALE_NUDE_KEYWORDS = (
    "completely nude", "fully nude", "completely naked", "fully naked",
)
_MALE_PANTS_DOWN_KEYWORDS = (
    "pants pulled down", "pants unbuckled", "pants down",
    "trousers down", "trousers pulled",
    "around his thighs", "around mid-thigh", "to mid-thigh", "to his thighs",
    "to his ankles", "around his ankles",
)
_MALE_SHIRT_UP_KEYWORDS = (
    "shirt rolled up", "shirt lifted", "shirt pulled up", "shirt rolled to",
    "t-shirt rolled up", "t-shirt lifted", "sleeves rolled",
)
_MALE_PENIS_EXPOSED_KEYWORDS = (
    "penis fully exposed", "penis exposed", "erect penis", "cock exposed",
    "erection fully exposed", "erection exposed", "exposed cock",
)
_MALE_ABSENT_KEYWORDS = (
    "absent", "no longer present", "has already left", "has left",
    "not present", "n/a", "left the scene",
)


def detect_clothing_progression(body: str) -> dict:
    """Grok 英文本体の Clothing state ブロックから衣装進行フラグを抽出。

    Returns dict with keys:
      heroine_nude (bool), heroine_partial (bool),
      male_nude (bool), male_pants_down (bool),
      male_shirt_up (bool), male_penis_exposed (bool),
      male_absent (bool)
    Grok 出力では heroine → male の順に Clothing state が現れる前提。
    """
    result = {
        "heroine_nude": False,
        "heroine_partial": False,
        "male_nude": False,
        "male_pants_down": False,
        "male_shirt_up": False,
        "male_penis_exposed": False,
        "male_absent": False,
    }
    if not body:
        return result
    matches = list(_CLOTHING_STATE_BLOCK_RE.finditer(body))
    if matches:
        heroine_text = matches[0].group(0).lower()
        if any(kw in heroine_text for kw in _HEROINE_NUDE_KEYWORDS):
            result["heroine_nude"] = True
        elif any(kw in heroine_text for kw in _HEROINE_PARTIAL_KEYWORDS):
            result["heroine_partial"] = True
    if len(matches) >= 2:
        male_text = matches[1].group(0).lower()
        if any(kw in male_text for kw in _MALE_ABSENT_KEYWORDS):
            result["male_absent"] = True
        else:
            if any(kw in male_text for kw in _MALE_NUDE_KEYWORDS):
                result["male_nude"] = True
            if any(kw in male_text for kw in _MALE_PANTS_DOWN_KEYWORDS):
                result["male_pants_down"] = True
            if any(kw in male_text for kw in _MALE_SHIRT_UP_KEYWORDS):
                result["male_shirt_up"] = True
            if any(kw in male_text for kw in _MALE_PENIS_EXPOSED_KEYWORDS):
                result["male_penis_exposed"] = True
    return result


# 衣装進行に応じて挿入する Danbooru タグと自然言語フォールバック
_HEROINE_NUDE_TAGS = "completely_nude, nude, no_clothing, breasts, nipples"
_HEROINE_NUDE_NL = (
    "The girl is completely nude, no clothing on her body, "
    "her bare skin and breasts fully exposed."
)
_MALE_PANTS_DOWN_TAG = "pants_pull"
_MALE_SHIRT_UP_TAG = "shirt_lift"
_MALE_PENIS_TAG = "penis, erection"
_MALE_NUDE_TAGS = "nude_male, completely_nude"


# 衣装段階 0-4 と段階別の追加タグ・自然言語
# CG集の脱衣演出（30-50代男性向け抜き観点）として「徐々に脱がす」連続性を担保するための
# 中間段階タグ群。base outfit_tags は段階 0-3 では維持し、段階 4 のみで置換する。
_STAGE_DRESSED = 0
_STAGE_BLOUSE_OPEN = 1
_STAGE_TOPLESS_PARTIAL = 2
_STAGE_PANTIES_ASIDE = 3
_STAGE_NUDE = 4

_STAGE_NAMES = {
    0: "dressed",
    1: "blouse_open",
    2: "topless_partial",
    3: "panties_aside",
    4: "completely_nude",
}

# 各段階で追加する Danbooru タグ群（段階 4 は別経路で完全置換のためここでは空）
_STAGE_ADD_TAGS: dict[int, list[str]] = {
    0: [],
    1: ["unbuttoned_shirt", "open_clothes", "open_shirt"],
    2: ["off_shoulder", "breasts_out", "topless"],
    3: ["skirt_lift", "panties_aside", "no_panties", "pantyhose_pull"],
    4: [],  # _HEROINE_NUDE_TAGS で置換するため
}

# 各段階の自然言語フォールバック (heroine_attrib に追記)
_STAGE_ADD_NL: dict[int, str] = {
    0: "",
    1: "Her blouse is unbuttoned and open, her chest visible underneath.",
    2: "Her blouse is slipped off her shoulders and her breasts are exposed.",
    3: "Her skirt is lifted around her waist and her panties are pulled aside, her wet pussy exposed.",
    4: "",  # _HEROINE_NUDE_NL で置換するため
}

# Clothing state テキストから段階を推定するキーワード（高段階優先で判定）
_STAGE4_KEYWORDS = _HEROINE_NUDE_KEYWORDS  # 既存定義を流用 (nude / removed all 系)
_STAGE3_KEYWORDS = (
    "panties pulled aside", "panties aside", "panties down",
    "panties around her thighs", "panties around her ankles",
    "panties pulled to", "no panties", "panties removed",
    "skirt around her waist", "skirt around the waist",
    "skirt hiked up", "skirt lifted", "skirt pulled up",
    "pantyhose pulled down", "pantyhose around",
)
_STAGE2_KEYWORDS = (
    "breasts exposed", "breast exposed", "topless",
    "no bra", "bra removed", "bra slipped off",
    "blouse off her shoulders", "blouse off shoulders",
    "blouse pushed off",
    "shirt off her shoulders", "shirt off shoulders",
    "off-shoulder", "off the shoulder",
    "shoulders bare",
)
_STAGE1_KEYWORDS = (
    "unbuttoned", "buttons undone", "buttons open",
    "blouse open", "shirt open", "open blouse", "open shirt",
    "bra visible", "bra strap",
    "spread wide open",
)


def estimate_heroine_stage(body: str) -> int:
    """Clothing state ブロック (heroine 側) から脱衣段階 0-4 を推定。

    高段階優先で判定し、いずれにもマッチしなければ 0 (dressed) を返す。
    detect_clothing_progression() と整合性を取りつつ、partial 内部の解像度を上げる。
    """
    if not body:
        return _STAGE_DRESSED
    matches = list(_CLOTHING_STATE_BLOCK_RE.finditer(body))
    if not matches:
        return _STAGE_DRESSED
    heroine_text = matches[0].group(0).lower()
    if any(kw in heroine_text for kw in _STAGE4_KEYWORDS):
        return _STAGE_NUDE
    if any(kw in heroine_text for kw in _STAGE3_KEYWORDS):
        return _STAGE_PANTIES_ASIDE
    if any(kw in heroine_text for kw in _STAGE2_KEYWORDS):
        return _STAGE_TOPLESS_PARTIAL
    if any(kw in heroine_text for kw in _STAGE1_KEYWORDS):
        return _STAGE_BLOUSE_OPEN
    return _STAGE_DRESSED


def bridge_stage_jump(prev_stage: int, current_stage: int) -> int:
    """前シーン段階と現シーン段階を比較し、ジャンプ (>1 段階) を 1 段階に抑制。

    例: prev=1 (blouse_open) → current=4 (nude) のジャンプを 2 (topless_partial) に抑える。
    後退は無視 (CG集の脱衣は単調増加が自然)。Grok が Clothing state を書き忘れた
    シーン (raw=dressed) でも prev_stage を維持して連続性を担保する。
    """
    if current_stage <= prev_stage:
        return prev_stage
    if current_stage - prev_stage <= 1:
        return current_stage
    return prev_stage + 1


def build_positive_prompt(
    english_body: str,
    char_key: str | None = None,
    quality_preset: str = "current",
    character: dict | None = None,
    progression: dict | None = None,
) -> str:
    """Quality prefix + (任意) キャラクター固定タグブロック + Grok 本体 を連結。

    Args:
        english_body: Grok から抽出した英語本文。
        char_key: 後方互換用。指定しても character 引数があれば character が優先。
        quality_preset: "current" / "animayume_min"。
        character: work_dir/character.json から読んだ dict。指定時はこの内容で
            char_block を動的構築し、Grok 本体先頭のキャラタグ行は削除する。
    """
    prefix = _QUALITY_PRESETS.get(quality_preset, _ANIMA_QUALITY_PREFIX)
    char_block = ""
    body = english_body
    if character:
        char_block = build_char_block_from_json(character, progression=progression)
        meta = character.get("anima_meta") or {}
        body = strip_grok_char_tags(
            body,
            char_tag=meta.get("character_tag") or "",
            series_tag=meta.get("series_tag") or "",
        )
    # 後方互換: character が無いときだけ char_key の旧パスを試す (現在は空辞書)
    return prefix + char_block + body


def build_negative_prompt(preset: str = "current", character: dict | None = None) -> str:
    base = _NEGATIVE_PRESETS.get(preset, _DEFAULT_NEGATIVE)
    if character:
        extras = build_negative_extras_from_json(character)
        if extras:
            return base + ", " + extras
    return base


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


def process_scene(
    response_path: Path, output_dir: Path, scene_id: int,
    char_key: str | None = None,
    quality_preset: str = "current",
    neg_preset: str = "current",
    character: dict | None = None,
    prev_stage: int = _STAGE_DRESSED,
) -> dict:
    raw = response_path.read_text(encoding="utf-8")
    english = extract_english(raw)
    if english is None:
        return {"scene_id": scene_id, "ok": False, "error": "english_section_not_found"}
    # character.json が提供されている場合、Clothing state ブロックから衣装進行フラグを
    # 抽出してから機械除去する。Tier 1: 衣装段階 0-4 をテキスト推定し、前シーン段階との
    # ジャンプを bridge_stage_jump で 1 段階以内に抑制する。effective_stage は
    # build_char_block_from_json に伝播し、段階別タグ・自然言語フォールバックを適用。
    progression: dict | None = None
    if character:
        progression = detect_clothing_progression(english)
        # 段階推定とジャンプ抑制
        raw_stage = estimate_heroine_stage(english)
        eff_stage = bridge_stage_jump(prev_stage, raw_stage)
        progression["raw_stage"] = raw_stage
        progression["raw_stage_name"] = _STAGE_NAMES.get(raw_stage, "")
        progression["prev_stage"] = prev_stage
        progression["effective_stage"] = eff_stage
        progression["effective_stage_name"] = _STAGE_NAMES.get(eff_stage, "")
        progression["bridged"] = (raw_stage != eff_stage)
        # heroine_nude / heroine_partial を effective_stage と整合させる
        # (旧ロジックの build_char_block 内 path を effective_stage 優先に統一)
        progression["heroine_nude"] = (eff_stage == _STAGE_NUDE)
        progression["heroine_partial"] = (
            eff_stage in (_STAGE_BLOUSE_OPEN, _STAGE_TOPLESS_PARTIAL, _STAGE_PANTIES_ASIDE)
        )
        english = strip_clothing_state_blocks(english)
    positive = build_positive_prompt(
        english, char_key=char_key, quality_preset=quality_preset,
        character=character, progression=progression,
    )
    negative = build_negative_prompt(neg_preset, character=character)
    payload = {
        "scene_id": scene_id,
        "positive": positive,
        "negative": negative,
        "source": str(response_path),
        "char_key": char_key,
        "quality_preset": quality_preset,
        "neg_preset": neg_preset,
        "character_source": (character or {}).get("char_id") or "none",
        "progression": progression or {},
    }
    out = output_dir / f"scene_{scene_id:03d}_prompt.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "scene_id": scene_id,
        "ok": True,
        "output": str(out),
        "positive_chars": len(positive),
        "english_body_chars": len(english),
        "progression": progression or {},
    }


def cmd_extract(
    work_dir: Path, scene_id: int | None, limit: int | None,
    char_key: str | None = None,
    quality_preset: str = "current",
    neg_preset: str = "current",
) -> int:
    response_dir = work_dir / "grok_responses"
    output_dir = _output_dir(work_dir)

    # work_dir/character.json があれば自動で読み込む (Daihon Rakku 提供データ駆動)
    character = load_character_json(work_dir)

    if scene_id is not None:
        targets = [scene_id]
    else:
        targets = _list_response_scene_ids(work_dir)
        if limit is not None and limit > 0:
            targets = targets[:limit]

    # 衣装段階のシーン間履歴 (Tier 1: ジャンプ補間)。
    # 各シーンの effective_stage を記録し、次シーンの bridge_stage_jump に渡す。
    # 単発シーン処理 (--scene-id 指定) でも、それ以前の prompts/scene_NNN_prompt.json
    # に保存済みの effective_stage を読んで「前シーン段階」として使用する。
    prev_stage: int = _STAGE_DRESSED
    if scene_id is not None and scene_id > 1:
        prev_path = output_dir / f"scene_{scene_id - 1:03d}_prompt.json"
        if prev_path.exists():
            try:
                prev_payload = json.loads(prev_path.read_text(encoding="utf-8"))
                prev_stage = int(
                    (prev_payload.get("progression") or {}).get("effective_stage", _STAGE_DRESSED)
                )
            except (OSError, json.JSONDecodeError, ValueError):
                prev_stage = _STAGE_DRESSED

    results: list[dict] = []
    for sid in targets:
        rp = response_dir / f"scene_{sid:03d}_response.txt"
        if not rp.exists():
            results.append({"scene_id": sid, "ok": False, "error": "response_not_found"})
            continue
        result = process_scene(
            rp, output_dir, sid,
            char_key=char_key,
            quality_preset=quality_preset,
            neg_preset=neg_preset,
            character=character,
            prev_stage=prev_stage,
        )
        results.append(result)
        # 次シーンに渡す段階を更新 (success のみ)
        if result.get("ok"):
            prog = result.get("progression") or {}
            prev_stage = int(prog.get("effective_stage", prev_stage))

    summary: dict = {
        "results": results,
        "count": len(results),
        "ok_count": sum(1 for r in results if r["ok"]),
    }
    if character:
        summary["character_loaded"] = {
            "char_id": character.get("char_id"),
            "tag_count": len(character.get("danbooru_tags") or []),
        }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
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
    p_ex.add_argument("--char-key", default=None,
                      help='[非推奨] 旧 _CHAR_TAG_TEMPLATES 用キー。'
                           '現在は work_dir/character.json から自動読込のため通常不要')
    p_ex.add_argument("--quality-preset", default="current",
                      choices=list(_QUALITY_PRESETS.keys()),
                      help='quality prefix プリセット')
    p_ex.add_argument("--neg-preset", default="current",
                      choices=list(_NEGATIVE_PRESETS.keys()),
                      help='negative prompt プリセット')

    p_st = sub.add_parser("status", help="抽出進捗 JSON")
    p_st.add_argument("work_dir")

    args = parser.parse_args(argv)
    work_dir = Path(args.work_dir)
    if not work_dir.exists():
        print(f"[ERROR] work_dir not found: {work_dir}", file=sys.stderr)
        return 2

    if args.cmd == "extract":
        return cmd_extract(
            work_dir, args.scene_id, args.limit,
            char_key=args.char_key,
            quality_preset=args.quality_preset,
            neg_preset=args.neg_preset,
        )
    if args.cmd == "status":
        return cmd_status(work_dir)
    return 1


if __name__ == "__main__":
    sys.exit(main())
