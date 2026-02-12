#!/usr/bin/env python3
"""
FANZA同人向け 低コスト脚本生成パイプライン - GUI版
Claude API直接対応
Skills: prompt_compactor → low_cost_pipeline → script_quality_supervisor
UI: Material Design 3 inspired
"""

import json
import csv
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable

import tkinter as tk
import customtkinter as ctk

# Excel出力用（オプション）
try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    import anthropic
except ImportError:
    print("Error: anthropic library is required. Run: pip install anthropic")
    sys.exit(1)

from char_builder import (
    AGE_OPTIONS, RELATIONSHIP_OPTIONS, ARCHETYPE_OPTIONS,
    FIRST_PERSON_OPTIONS, SPEECH_STYLE_OPTIONS,
    HAIR_COLOR_OPTIONS, HAIR_STYLE_OPTIONS,
    BODY_TYPE_OPTIONS, CHEST_OPTIONS, CLOTHING_OPTIONS,
    SHYNESS_OPTIONS, build_custom_character_data
)

# === Font Awesome 6 アイコンフォント ===
FONTS_DIR = Path(__file__).parent / "fonts"
_FA_FONT_PATH = FONTS_DIR / "fa-solid-900.ttf"
if _FA_FONT_PATH.exists():
    ctk.FontManager.load_font(str(_FA_FONT_PATH))

# フォント定数
FONT_JP = "Noto Sans JP"
FONT_ICON = "Font Awesome 6 Free Solid"
FONT_MONO = "Consolas"


class Icons:
    """Font Awesome 6 Solid ユニコードコードポイント"""
    FILM = "\uf008"
    LOCK = "\uf023"
    FOLDER = "\uf07b"
    FOLDER_OPEN = "\uf07c"
    USER = "\uf007"
    BOOK = "\uf02d"
    GEAR = "\uf013"
    COINS = "\uf51d"
    LIST = "\uf022"
    CLOCK = "\uf017"
    PLAY = "\uf04b"
    SAVE = "\uf0c7"
    STOP = "\uf04d"
    WAND = "\uf0d0"
    XMARK = "\uf057"
    WARNING = "\uf071"
    CHART = "\uf080"
    CHECK = "\uf058"
    CHEVRON_UP = "\uf077"
    CHEVRON_DOWN = "\uf078"


def icon_text_label(parent, icon: str, text: str, icon_size: int = 14, text_size: int = 14,
                    text_weight: str = "bold", text_color=None, fg_color="transparent"):
    """FAアイコン + テキストを横並びで配置するヘルパー"""
    if text_color is None:
        text_color = MaterialColors.ON_SURFACE
    frame = ctk.CTkFrame(parent, fg_color=fg_color)
    ctk.CTkLabel(
        frame, text=icon,
        font=ctk.CTkFont(family=FONT_ICON, size=icon_size),
        text_color=text_color
    ).pack(side="left", padx=(0, 8))
    ctk.CTkLabel(
        frame, text=text,
        font=ctk.CTkFont(family=FONT_JP, size=text_size, weight=text_weight),
        text_color=text_color
    ).pack(side="left")
    return frame


# === Material Design 3 カラーパレット ===
class MaterialColors:
    """
    Material You / M3 Dynamic Color System
    Based on Google's Material Design 3 color guidelines
    Adjusted for better visibility and contrast
    """
    
    # === M3 Tonal Palette (Purple seed) ===
    # Primary
    PRIMARY = "#6750A4"           # M3 reference primary
    PRIMARY_CONTAINER = "#E8DBFF" # P-90
    ON_PRIMARY = "#FFFFFF"        # P-100
    ON_PRIMARY_CONTAINER = "#1C0055"  # P-10
    
    # Secondary  
    SECONDARY = "#5A5370"         # S-40
    SECONDARY_CONTAINER = "#DFD8F0"   # S-90 slightly deeper
    ON_SECONDARY = "#FFFFFF"
    ON_SECONDARY_CONTAINER = "#18122E"
    
    # Tertiary
    TERTIARY = "#7D5260"          # T-40
    TERTIARY_CONTAINER = "#FFD8E4"    # T-90
    
    # Error
    ERROR = "#B3261E"             # E-40
    ERROR_CONTAINER = "#F9DEDC"   # E-90
    ON_ERROR = "#FFFFFF"
    
    # Success (Extended)
    SUCCESS = "#1B6B32"
    SUCCESS_CONTAINER = "#A8F5B4"
    
    # === Surface Tones (Neutral) - Wider spacing for clarity ===
    BACKGROUND = "#FAF8FF"        # Very subtle cool tint
    SURFACE = "#FAF8FF"           # Match background
    SURFACE_DIM = "#CEC6D9"       # N-82 (darker dim)
    SURFACE_BRIGHT = "#FAF8FF"    # N-99
    SURFACE_CONTAINER_LOWEST = "#FFFFFF"   # N-100 Pure white
    SURFACE_CONTAINER_LOW = "#F2EDFA"      # N-95 (clear purple tint)
    SURFACE_CONTAINER = "#E8E1F2"          # N-90 (visible difference)
    SURFACE_CONTAINER_HIGH = "#DCD4EA"     # N-85 (clearly darker)
    SURFACE_CONTAINER_HIGHEST = "#D0C7E0"  # N-80 (strong contrast)
    
    # On Surface - Higher contrast text
    ON_BACKGROUND = "#151318"     # Near black
    ON_SURFACE = "#151318"        # Near black for readability
    ON_SURFACE_VARIANT = "#49454F"    # NV-30 M3 reference
    
    # Outline - Stronger borders
    OUTLINE = "#79747E"           # NV-50 M3 reference
    OUTLINE_VARIANT = "#B0A8BF"   # NV-70 (more visible)
    
    # Inverse
    INVERSE_SURFACE = "#313033"
    INVERSE_ON_SURFACE = "#F4EFF4"
    INVERSE_PRIMARY = "#D0BCFF"
    
    # Scrim & Shadow
    SCRIM = "#000000"
    SHADOW = "#000000"
    
    # === Legacy aliases for compatibility ===
    SURFACE_VARIANT = SURFACE_CONTAINER
    PRIMARY_VARIANT = "#7058B8"
    PRIMARY_LIGHT = INVERSE_PRIMARY
    ACCENT = TERTIARY
    ACCENT_VARIANT = "#9A7B8A"
    ACCENT_DARK = "#633B48"
    WARNING = "#F59E0B"
    SURFACE_DARK = INVERSE_SURFACE
    ON_DARK = INVERSE_ON_SURFACE
    ON_ACCENT = ON_PRIMARY


# === 設定 ===
MAX_RETRIES = 3
RETRY_DELAY = 2
OUTPUT_DIR = Path(__file__).parent
SKILLS_DIR = OUTPUT_DIR / "skills"
JAILBREAK_FILE = OUTPUT_DIR / "jailbreak.md"
DANBOORU_TAGS_JSON = OUTPUT_DIR / "danbooru_tags.json"
SD_PROMPT_GUIDE_FILE = OUTPUT_DIR / "sd_prompt_guide.md"
CONFIG_FILE = OUTPUT_DIR / "config.json"
LOG_FILE = OUTPUT_DIR / "log.txt"
CONTEXT_DIR = OUTPUT_DIR / "context"
DRAFTS_DIR = OUTPUT_DIR / "drafts"
FINAL_DIR = OUTPUT_DIR / "final"
EXPORTS_DIR = OUTPUT_DIR / "exports"
SOURCES_DIR = OUTPUT_DIR / "sources"
CHARACTERS_DIR = OUTPUT_DIR / "characters"
CHAR_SKILLS_DIR = SKILLS_DIR / "characters"
PROFILES_DIR = OUTPUT_DIR / "profiles"

# プリセットキャラクター
PRESETS_DIR = Path(__file__).parent / "presets"
PRESET_CHARS_DIR = PRESETS_DIR / "characters"
PRESET_INDEX_FILE = PRESETS_DIR / "preset_index.json"

# ディレクトリ作成
for d in [CONTEXT_DIR, DRAFTS_DIR, FINAL_DIR, EXPORTS_DIR, SOURCES_DIR, CHARACTERS_DIR, CHAR_SKILLS_DIR, PROFILES_DIR]:
    d.mkdir(exist_ok=True, parents=True)

# モデル設定
MODELS = {
    "haiku": "claude-3-haiku-20240307",
    "sonnet": "claude-sonnet-4-20250514",
}

# コスト（USD per 1M tokens）
COSTS = {
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
}

# テーマ選択肢
THEME_OPTIONS = {
    "指定なし": "",
    "凌辱・屈辱": "humiliation",
    "強制・無理やり": "forced",
    "純愛・ラブラブ": "love",
    "寝取られ・NTR": "netorare",
    "和姦・合意": "vanilla",
    "堕ち・調教": "corruption",
    "痴漢・公共": "chikan",
    "上司・OL": "office",
    "先生・生徒": "teacher_student",
    "メイド・ご主人様": "maid",
    "催眠・洗脳": "hypnosis",
    "異種姦・モンスター": "monster",
    "時間停止": "time_stop",
    "ハーレム": "harem",
    "女性優位・痴女": "femdom",
    "近親相姦": "incest",
}

# ストーリー構成プリセット（プロローグ/本編/エピローグ %）
STRUCTURE_PRESETS = {
    "標準バランス (10/80/10)": {"prologue": 10, "epilogue": 10},
    "エロ重視 (5/90/5)": {"prologue": 5, "epilogue": 5},
    "ストーリー重視 (20/70/10)": {"prologue": 20, "epilogue": 10},
    "じっくり展開 (15/75/10)": {"prologue": 15, "epilogue": 10},
    "カスタム": None,
}

# テーマ別ストーリー・演出ガイド
THEME_GUIDES = {
    "netorare": {
        "name": "寝取られ・NTR",
        "story_arc": "日常→接近→裏切り→堕ち→完堕ち",
        "key_emotions": ["背徳感", "罪悪感", "快楽への抗えなさ", "比較（彼氏より...）"],
        "story_elements": [
            "彼氏/夫がいる設定を明確に",
            "最初は抵抗・罪悪感",
            "徐々に快楽に負ける",
            "「彼氏には言えない」「こんなの初めて」",
            "最終的に寝取り男を求める"
        ],
        "dialogue_tone": "罪悪感と快感の葛藤、比較表現、堕ちていく過程",
        "use_heart": False,  # ♡は使わない
        "sd_tags": "netorare, cheating, corruption, guilt, unfaithful, stolen",
        "sd_expressions": "conflicted, guilty_pleasure, ahegao, mindbreak"
    },
    "humiliation": {
        "name": "凌辱・屈辱",
        "story_arc": "支配→抵抗→屈服→快楽堕ち",
        "key_emotions": ["屈辱", "恐怖", "抵抗", "やがて快感に負ける"],
        "story_elements": [
            "力関係の差を明確に",
            "抵抗するが徐々に体が反応",
            "「やめて」「嫌」から変化",
            "屈辱的な状況設定"
        ],
        "dialogue_tone": "抵抗、懇願、屈辱感、やがて快感を認める",
        "use_heart": False,
        "sd_tags": "humiliation, forced, reluctant, crying, tears",
        "sd_expressions": "crying, fearful, reluctant, trembling, broken"
    },
    "forced": {
        "name": "強制・無理やり",
        "story_arc": "襲われる→抵抗→屈服→（オプション：快楽堕ち）",
        "key_emotions": ["恐怖", "抵抗", "絶望", "やがて諦め/快感"],
        "story_elements": [
            "逃げられない状況",
            "必死の抵抗",
            "力で押さえつけられる",
            "「やめて」「助けて」"
        ],
        "dialogue_tone": "懇願、抵抗、絶望、諦め",
        "use_heart": False,
        "sd_tags": "forced, rape, struggling, restrained, pinned_down",
        "sd_expressions": "crying, screaming, fearful, defeated"
    },
    "love": {
        "name": "純愛・ラブラブ",
        "story_arc": "告白→初々しさ→情熱→幸福",
        "key_emotions": ["恥じらい", "愛情", "幸福感", "一体感"],
        "story_elements": [
            "両想いの確認",
            "初々しい恥じらい",
            "愛情表現",
            "「好き」「愛してる」"
        ],
        "dialogue_tone": "甘い、恥ずかしがり、愛情たっぷり",
        "use_heart": True,  # ♡OK
        "sd_tags": "romantic, loving, gentle, passionate, consensual",
        "sd_expressions": "blushing, happy, loving, content, peaceful"
    },
    "vanilla": {
        "name": "和姦・合意",
        "story_arc": "ムード→合意→行為→満足",
        "key_emotions": ["期待", "興奮", "快感", "満足"],
        "story_elements": [
            "自然な流れ",
            "お互いの同意",
            "楽しむ雰囲気"
        ],
        "dialogue_tone": "自然、楽しそう、気持ちいい",
        "use_heart": True,
        "sd_tags": "consensual, enjoying, willing, happy_sex",
        "sd_expressions": "happy, enjoying, moaning, satisfied"
    },
    "corruption": {
        "name": "堕ち・調教",
        "story_arc": "純粋→揺らぎ→堕落→完堕ち",
        "key_emotions": ["戸惑い", "背徳感", "快楽への目覚め", "依存"],
        "story_elements": [
            "最初は純粋・清楚",
            "徐々に快楽を覚える",
            "「こんなの知らなかった」",
            "最終的に求めるように"
        ],
        "dialogue_tone": "戸惑いから快楽への変化、堕ちていく過程",
        "use_heart": False,
        "sd_tags": "corruption, training, breaking, mindbreak",
        "sd_expressions": "confused, awakening, addicted, broken, ahegao"
    },
    "chikan": {
        "name": "痴漢・公共",
        "story_arc": "被害→抵抗できない→感じてしまう",
        "key_emotions": ["恐怖", "羞恥", "声が出せない", "感じてしまう罪悪感"],
        "story_elements": [
            "公共の場（電車など）",
            "周りにバレられない",
            "声を出せない状況",
            "体が勝手に反応"
        ],
        "dialogue_tone": "小声、我慢、羞恥",
        "use_heart": False,
        "sd_tags": "chikan, groping, public, train, crowded, molested",
        "sd_expressions": "embarrassed, trying_not_to_moan, biting_lip, conflicted"
    },
    "office": {
        "name": "上司・OL",
        "story_arc": "職場→関係発展→密会→背徳",
        "key_emotions": ["緊張", "背徳感", "禁断の興奮", "秘密"],
        "story_elements": [
            "上下関係",
            "バレてはいけない",
            "仕事中の緊張感",
            "オフィスでの密会"
        ],
        "dialogue_tone": "敬語混じり、緊張、背徳感",
        "use_heart": False,
        "sd_tags": "office, office_lady, suit, desk, workplace, secret",
        "sd_expressions": "nervous, secretive, professional_facade"
    },
    "teacher_student": {
        "name": "先生・生徒",
        "story_arc": "禁断→誘惑/誘われ→一線を越える→背徳",
        "key_emotions": ["禁断", "背徳感", "支配/被支配", "秘密"],
        "story_elements": [
            "立場の差",
            "禁じられた関係",
            "教室/保健室などの場所",
            "バレたら終わり"
        ],
        "dialogue_tone": "敬語と砕けた表現の混在、禁断感",
        "use_heart": False,
        "sd_tags": "teacher, student, classroom, forbidden, taboo",
        "sd_expressions": "nervous, forbidden_pleasure, secretive"
    },
    "maid": {
        "name": "メイド・ご主人様",
        "story_arc": "奉仕→親密→特別な奉仕",
        "key_emotions": ["忠誠", "奉仕", "主従関係", "愛情"],
        "story_elements": [
            "主従関係",
            "「ご主人様」呼び",
            "奉仕の延長",
            "命令への従順"
        ],
        "dialogue_tone": "丁寧語、奉仕精神、従順",
        "use_heart": True,
        "sd_tags": "maid, maid_uniform, master, servant, obedient",
        "sd_expressions": "devoted, obedient, eager_to_please"
    },
    "hypnosis": {
        "name": "催眠・洗脳",
        "story_arc": "暗示→無意識→操作→覚醒しても体が覚えている",
        "key_emotions": ["ぼんやり", "抵抗できない", "無意識の快感", "自分じゃない感覚"],
        "story_elements": [
            "催眠術や暗示のきっかけ",
            "意識がぼやける描写",
            "命令に逆らえない体",
            "「なぜ体が勝手に...」という混乱",
            "覚醒後も体が反応してしまう"
        ],
        "dialogue_tone": "ぼんやりした口調、命令への無抵抗、覚醒時の混乱と羞恥",
        "use_heart": False,
        "sd_tags": "hypnosis, mind_control, blank_eyes, spiral_eyes, trance",
        "sd_expressions": "empty_eyes, dazed, vacant, drooling, mindless, confused"
    },
    "monster": {
        "name": "異種姦・モンスター",
        "story_arc": "遭遇→捕獲→異種交配→快楽堕ち",
        "key_emotions": ["恐怖", "嫌悪", "異物感", "未知の快感に溺れる"],
        "story_elements": [
            "人外の存在との遭遇",
            "逃げられない状況",
            "人間にはない刺激",
            "「人間じゃないのに...」という背徳感",
            "触手や異形の描写"
        ],
        "dialogue_tone": "恐怖と驚き、徐々に快感に変わる声、人間離れした行為への反応",
        "use_heart": False,
        "sd_tags": "monster, tentacles, interspecies, creature, non-human",
        "sd_expressions": "scared, disgusted, surprised, overwhelmed, ahegao"
    },
    "time_stop": {
        "name": "時間停止",
        "story_arc": "停止→観察→いたずら→解除の瞬間",
        "key_emotions": ["無防備", "知らないうちに", "解除後の混乱", "証拠に気づく恥辱"],
        "story_elements": [
            "時間が止まるきっかけ",
            "止まった世界での自由行動",
            "好きなポーズに変えられる",
            "解除後の「何かされた？」感覚",
            "体に残る痕跡"
        ],
        "dialogue_tone": "停止中は無言（ナレーション中心）、解除後は混乱と気づきの描写",
        "use_heart": False,
        "sd_tags": "time_stop, frozen, mannequin_pose, unconscious, sleeping",
        "sd_expressions": "frozen, blank_expression, sleeping, confused, shocked"
    },
    "harem": {
        "name": "ハーレム",
        "story_arc": "出会い→好意集中→争奪→全員で奉仕",
        "key_emotions": ["独占欲", "嫉妬", "競争心", "共有の快楽"],
        "story_elements": [
            "複数ヒロインが主人公を取り合う",
            "嫉妬や競争の描写",
            "「私の方が上手」的な比較",
            "最終的に全員でのシーン",
            "各キャラの個性が際立つ"
        ],
        "dialogue_tone": "各キャラが個性的に競い合う、嫉妬と甘え、協力と競争",
        "use_heart": True,
        "sd_tags": "harem, multiple_girls, group, jealous, competitive",
        "sd_expressions": "jealous, competitive, eager, cooperative, blush"
    },
    "femdom": {
        "name": "女性優位・痴女",
        "story_arc": "主導権掌握→翻弄→支配→ご褒美",
        "key_emotions": ["支配欲", "優越感", "相手をからかう楽しさ", "征服感"],
        "story_elements": [
            "女性がリードする関係",
            "男性を翻弄する",
            "「こんなに感じてるの？」的なからかい",
            "騎乗位や言葉責め",
            "主導権は常に女性側"
        ],
        "dialogue_tone": "上から目線、からかい、余裕のある態度、小悪魔的",
        "use_heart": True,
        "sd_tags": "femdom, dominatrix, female_domination, sitting_on_face, riding",
        "sd_expressions": "smirk, confident, teasing, dominant, looking_down"
    },
    "incest": {
        "name": "近親相姦",
        "story_arc": "家族の日常→意識→禁断→堕ちる",
        "key_emotions": ["背徳感", "罪悪感", "家族への愛と欲望の混同", "秘密"],
        "story_elements": [
            "家族設定を明確に（兄妹/姉弟/母子など）",
            "普段の家族関係からの逸脱",
            "「家族なのに...」という葛藤",
            "二人だけの秘密",
            "他の家族にバレない緊張感"
        ],
        "dialogue_tone": "普段の呼び方（お兄ちゃん、お姉ちゃん等）と背徳感、家族の呼称が興奮を増す",
        "use_heart": False,
        "sd_tags": "incest, siblings, family, forbidden_love, taboo, secret",
        "sd_expressions": "guilty, conflicted, forbidden_pleasure, secretive"
    }
}

DEFAULT_NEGATIVE_PROMPT = "worst_quality, low_quality, lowres, bad_anatomy, bad_hands, missing_fingers, extra_fingers, mutated_hands, poorly_drawn_face, ugly, deformed, blurry, text, watermark, signature, censored, mosaic_censoring, loli, shota, child"

QUALITY_POSITIVE_TAGS = "(masterpiece, best_quality:1.2)"

def deduplicate_sd_tags(prompt: str) -> str:
    """SDプロンプトのタグを重複排除（順序保持）"""
    import re as _re
    tags = [t.strip() for t in prompt.split(",") if t.strip()]
    seen = set()
    result = []
    for tag in tags:
        # (tag:weight) 形式のタグからタグ名を正しく抽出
        m = _re.match(r'^\(([^:]+):([\d.]+)\)$', tag.strip())
        if m:
            normalized = m.group(1).strip().lower().replace(" ", "_")
        else:
            normalized = _re.sub(r'\([^)]*:[\d.]+\)', '', tag).strip().lower().replace(" ", "_")
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(tag)
    return ", ".join(result)


def validate_script(results: list, theme: str = "", char_profiles: list = None) -> dict:
    """FANZA CG集基準で生成済み台本を自動検証（APIコスト不要）。

    Returns:
        dict with score, scene_issues, repeated_moans, repeated_onomatopoeia, total_issues, summary
    """
    import re as _re

    heroine_names = set()
    if char_profiles:
        for cp in char_profiles:
            name = cp.get("character_name", "")
            if name:
                heroine_names.add(name)

    scene_issues = {}
    all_moan_texts = []   # [(scene_id, text)]
    all_speech_texts = [] # [(scene_id, text)]
    all_onom_sets = []    # [(scene_id, frozenset)]
    prev_angle_tags = set()

    for i, scene in enumerate(results):
        scene_id = scene.get("scene_id", i + 1)
        if scene.get("mood") == "エラー":
            continue
        problems = []

        # --- bubbles ---
        bubbles = scene.get("bubbles", [])

        # 吹き出し数（1-4個）
        if len(bubbles) > 4:
            problems.append(f"吹き出し{len(bubbles)}個（上限4個）")
        elif len(bubbles) == 0:
            problems.append("吹き出しが0個")

        # テキスト長（1-10文字）
        for j, b in enumerate(bubbles):
            text = b.get("text", "")
            if len(text) > 10:
                problems.append(f"吹き出し{j+1}「{text[:12]}…」{len(text)}文字（上限10）")

        # 男セリフ数（≤1/ページ）
        male_speech_count = 0
        for b in bubbles:
            if b.get("type") == "speech":
                speaker = b.get("speaker", "")
                if speaker and heroine_names and speaker not in heroine_names:
                    male_speech_count += 1
        if male_speech_count > 1:
            problems.append(f"男性セリフ{male_speech_count}個（推奨1個以下）")

        # moan・speech追跡（クロスシーン重複検出用）
        for b in bubbles:
            if b.get("type") == "moan":
                all_moan_texts.append((scene_id, b.get("text", "")))
            elif b.get("type") == "speech":
                all_speech_texts.append((scene_id, b.get("text", "")))

        # --- onomatopoeia ---
        onom = scene.get("onomatopoeia", [])
        all_onom_sets.append((scene_id, frozenset(onom) if onom else frozenset()))

        # --- 必須フィールド ---
        for field in ("title", "description", "mood", "sd_prompt", "direction"):
            if not scene.get(field):
                problems.append(f"「{field}」が空")

        # --- description品質 ---
        desc = scene.get("description", "")
        intensity = scene.get("intensity", 0)
        if 0 < len(desc) < 30:
            problems.append(f"description短すぎ（{len(desc)}文字）")
        if intensity >= 4 and desc:
            vague_words = ["愛撫", "行為に及ぶ", "関係を持つ", "一線を越える", "身体を重ねる"]
            if any(vw in desc for vw in vague_words) and not any(
                kw in desc for kw in ["挿入", "正常位", "騎乗位", "バック", "腰を", "突"]
            ):
                problems.append("descriptionが抽象的（具体的な体位・行為を記述すべき）")

        # --- sd_prompt: 日本語混入 ---
        sd = scene.get("sd_prompt", "")
        jp_chars = _re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+', sd)
        if jp_chars:
            problems.append(f"sd_promptに日本語: {', '.join(jp_chars[:3])}")

        # --- sd_prompt: 連続同一アングル ---
        angle_kw = {"from_above", "from_below", "from_behind", "from_side",
                    "pov", "straight-on", "dutch_angle"}
        cur_angles = {kw for kw in angle_kw if kw in sd.lower()}
        if cur_angles and cur_angles == prev_angle_tags:
            problems.append(f"前シーンと同一アングル: {', '.join(cur_angles)}")
        prev_angle_tags = cur_angles

        # --- sd_prompt: 室内外タグ矛盾 ---
        sd_low = sd.lower()
        outdoor_markers = {"outdoors", "park", "forest", "beach", "poolside", "rooftop", "garden"}
        indoor_markers = {"indoors", "classroom", "bedroom", "bathroom", "kitchen", "elevator",
                          "office", "living_room", "train_interior", "car_interior"}
        indoor_only_tags = {"ceiling", "fluorescent_light", "wallpaper", "chandelier",
                            "carpet", "wooden_floor", "tile_floor", "ceiling_fan"}
        outdoor_only_tags = {"sky", "cloud", "horizon", "grass", "trees", "ocean", "sun"}
        sd_tags_set = {t.strip().lower().replace(" ", "_") for t in sd.split(",") if t.strip()}
        has_outdoor = bool(sd_tags_set & outdoor_markers)
        has_indoor = bool(sd_tags_set & indoor_markers)
        has_window = "window" in sd_low
        if has_outdoor:
            bad = sd_tags_set & indoor_only_tags
            if bad:
                problems.append(f"室内外矛盾: outdoor+{','.join(list(bad)[:3])}")
        if has_indoor and not has_window:
            bad = sd_tags_set & outdoor_only_tags
            if bad and "open_air_bath" not in sd_low:
                problems.append(f"室内外矛盾: indoor+{','.join(list(bad)[:3])}(window無し)")

        # --- sd_prompt: 照明-時間帯整合性 ---
        morning_kw = {"morning", "sunrise", "daytime", "afternoon"}
        night_kw = {"night", "midnight", "late_night"}
        night_light_bad = {"sunlight", "bright_daylight", "blue_sky", "morning_light"}
        morning_light_bad = {"moonlight", "darkness", "night_sky", "starlight"}
        time_in_sd = sd_tags_set & (morning_kw | night_kw)
        if time_in_sd & morning_kw:
            bad = sd_tags_set & morning_light_bad
            if bad:
                problems.append(f"照明矛盾: 朝昼+{','.join(list(bad)[:2])}")
        if time_in_sd & night_kw:
            bad = sd_tags_set & night_light_bad
            if bad:
                problems.append(f"照明矛盾: 夜+{','.join(list(bad)[:2])}")

        # --- sd_prompt: 背景タグ存在確認 ---
        bg_tags = {"classroom", "bedroom", "bathroom", "kitchen", "living_room", "office",
                   "outdoors", "indoors", "park", "forest", "beach", "rooftop", "car_interior",
                   "train_interior", "hotel_room", "onsen", "bath", "pool", "cafe", "restaurant",
                   "shrine", "temple", "alley", "bridge", "garden", "library", "gym",
                   "hallway", "stairwell", "locker_room", "infirmary", "elevator"}
        if sd and not (sd_tags_set & bg_tags):
            problems.append("sd_promptに背景/場所タグが無い")

        if problems:
            scene_issues[scene_id] = problems

    # --- クロスシーン: scene_id重複チェック ---
    scene_ids = [s.get("scene_id", i+1) for i, s in enumerate(results)]
    if len(scene_ids) != len(set(scene_ids)):
        dupes = [sid for sid in scene_ids if scene_ids.count(sid) > 1]
        for sid in set(dupes):
            scene_issues.setdefault(sid, []).append(f"scene_id {sid} が重複している")

    # --- クロスシーン: bubble完全重複チェック ---
    prev_bubble_set = set()
    for i, scene in enumerate(results):
        scene_id = scene.get("scene_id", i + 1)
        bubbles = scene.get("bubbles", [])
        curr_bubble_set = frozenset(b.get("text", "") for b in bubbles if b.get("text"))
        if curr_bubble_set and curr_bubble_set == prev_bubble_set:
            scene_issues.setdefault(scene_id, []).append("前シーンとbubbleが完全同一（重複）")
        prev_bubble_set = curr_bubble_set

    # --- クロスシーン: 喘ぎ重複（類似マッチ含む） ---
    moan_map = {}
    for sid, text in all_moan_texts:
        moan_map.setdefault(text, []).append(sid)
    repeated_moans = {t: sids for t, sids in moan_map.items() if len(sids) > 1}
    # 類似喘ぎ検出（正規化後の先頭3文字一致）
    moan_normalized = [(sid, text, _normalize_bubble_text(text)) for sid, text in all_moan_texts]
    for i in range(len(moan_normalized)):
        for j in range(i + 1, len(moan_normalized)):
            s1, t1, n1 = moan_normalized[i]
            s2, t2, n2 = moan_normalized[j]
            if t1 != t2 and s1 != s2 and _is_similar_bubble(t1, t2):
                key = f"{t1}≈{t2}"
                if key not in repeated_moans:
                    repeated_moans[key] = [s1, s2]

    # --- クロスシーン: speech重複チェック ---
    speech_map = {}
    for sid, text in all_speech_texts:
        speech_map.setdefault(text, []).append(sid)
    repeated_speech = {t: sids for t, sids in speech_map.items() if len(sids) > 1}
    for text, sids in repeated_speech.items():
        for sid in sids[1:]:
            scene_issues.setdefault(sid, []).append(f"speech重複「{text}」（シーン{sids[0]}と同一）")

    # --- クロスシーン: オノマトペ近接重複（3シーン以内） ---
    repeated_onom = []
    for k in range(1, len(all_onom_sets)):
        cur_sid, cur_set = all_onom_sets[k]
        if not cur_set:
            continue
        for j in range(max(0, k - 3), k):
            _, prev_set = all_onom_sets[j]
            if prev_set and cur_set == prev_set:
                repeated_onom.append((all_onom_sets[j][0], cur_sid))
                break

    # --- クロスシーン: 3シーン連続同一location ---
    locations_list = []
    for scene in results:
        loc = scene.get("location_detail", scene.get("location", ""))
        locations_list.append(loc.strip().lower() if loc else "")
    for k in range(2, len(locations_list)):
        if locations_list[k] and locations_list[k] == locations_list[k-1] == locations_list[k-2]:
            sid = results[k].get("scene_id", k + 1)
            scene_issues.setdefault(sid, []).append(
                f"3シーン連続同一location: {locations_list[k]}")

    # --- クロスシーン: アングル全体分布偏り ---
    angle_counter = {}
    for scene in results:
        sd_text = scene.get("sd_prompt", "").lower()
        for akw in ("from_above", "from_below", "from_behind", "from_side",
                     "pov", "straight-on", "dutch_angle"):
            if akw in sd_text:
                angle_counter[akw] = angle_counter.get(akw, 0) + 1
    total_scenes = len(results)
    if total_scenes >= 5:
        for akw, cnt in angle_counter.items():
            if cnt / total_scenes >= 0.4:
                scene_issues.setdefault("global", []).append(
                    f"アングル偏り: {akw}が{cnt}/{total_scenes}シーン({cnt*100//total_scenes}%)")

    n_issues = sum(len(v) for v in scene_issues.values()) + len(repeated_moans) + len(repeated_onom)
    score = max(0, 100 - n_issues * 5)

    return {
        "score": score,
        "scene_issues": scene_issues,
        "repeated_moans": repeated_moans,
        "repeated_onomatopoeia": repeated_onom,
        "total_issues": n_issues,
        "summary": f"品質スコア: {score}/100（{n_issues}件の問題検出）"
    }




def _fix_character_name(name: str, correct_names: list) -> str:
    """キャラ名の表記ブレを修正"""
    if not name or not correct_names:
        return name
    # 完全一致ならそのまま
    if name in correct_names:
        return name
    # 部分一致: 正しい名前がnameに含まれる or nameが正しい名前に含まれる
    for cn in correct_names:
        if cn in name or name in cn:
            return cn
    # 姓が一致するパターン（中野三子→中野三玖）
    for cn in correct_names:
        if len(cn) >= 3 and len(name) >= 3:
            # 姓（先頭2文字）が一致し、名が異なる場合
            if cn[:2] == name[:2] and cn != name:
                return cn
            # 先頭1文字が一致し残り文字数が同じ場合
            if cn[0] == name[0] and len(cn) == len(name) and cn != name:
                return cn
    return name


def _fix_names_in_text(text: str, correct_names: list) -> str:
    """テキスト内のキャラ名表記ブレを修正"""
    import re
    if not text or not correct_names:
        return text
    for correct in correct_names:
        if len(correct) < 3:
            continue
        # 姓（先頭2文字）+ 名（残り）のパターンで検索
        family = correct[:2]
        given = correct[2:]
        if not given:
            continue
        # family + given長と同じ文字数の漢字/ひらがな/カタカナを検索
        # 正しい名前以外をマッチさせる
        pattern = re.escape(family) + r'([\u4e00-\u9faf\u3040-\u309f\u30a0-\u30ff]{' + str(len(given)) + '})'
        for m in re.finditer(pattern, text):
            found_given = m.group(1)
            if found_given != given:
                wrong_name = family + found_given
                text = text.replace(wrong_name, correct)
                log_message(f"  名前修正: {wrong_name}→{correct}")
    return text


def _normalize_bubble_text(text: str) -> str:
    """セリフテキストを正規化して類似判定に使用。♡等の装飾除去+カタカナ→ひらがな"""
    import unicodedata
    # 装飾文字除去
    t = text.replace("♡", "").replace("♥", "").replace("…", "").replace("っ", "").replace("ー", "").strip()
    # カタカナ→ひらがな変換
    result = []
    for ch in t:
        cp = ord(ch)
        if 0x30A1 <= cp <= 0x30F6:
            result.append(chr(cp - 0x60))
        else:
            result.append(ch)
    return "".join(result)

def _is_similar_bubble(text1: str, text2: str) -> bool:
    """2つのセリフが類似しているか判定（完全一致 or 正規化一致 or 先頭3文字一致）"""
    if text1 == text2:
        return True
    n1 = _normalize_bubble_text(text1)
    n2 = _normalize_bubble_text(text2)
    if n1 == n2:
        return True
    if len(n1) >= 3 and len(n2) >= 3 and n1[:3] == n2[:3]:
        return True
    return False

def _deduplicate_across_scenes(results: list) -> None:
    """シーン間の同一・類似セリフ・オノマトペ重複を除去（全type対応+類似マッチ）"""
    used_moan_texts = []    # list of (text, normalized) for similarity check
    used_thought_texts = []
    used_speech_texts = []

    for scene in results:
        if "bubbles" not in scene:
            continue
        cleaned_bubbles = []
        sid = scene.get("scene_id", "?")
        for b in scene["bubbles"]:
            text = b.get("text", "")
            btype = b.get("type", "")

            if btype == "moan" and text:
                if any(_is_similar_bubble(text, prev) for prev, _ in used_moan_texts):
                    log_message(f"  シーン{sid}: 重複/類似喘ぎ除去「{text}」")
                    continue
                used_moan_texts.append((text, _normalize_bubble_text(text)))

            elif btype == "thought" and text:
                if any(_is_similar_bubble(text, prev) for prev, _ in used_thought_texts):
                    log_message(f"  シーン{sid}: 重複/類似thought除去「{text}」")
                    continue
                used_thought_texts.append((text, _normalize_bubble_text(text)))

            elif btype == "speech" and text:
                # speechは完全一致のみ除去（類似は許容）
                if text in {prev for prev, _ in used_speech_texts}:
                    log_message(f"  シーン{sid}: 重複speech除去「{text}」")
                    continue
                used_speech_texts.append((text, _normalize_bubble_text(text)))

            cleaned_bubbles.append(b)

        # 最低1つのbubbleは残す
        if cleaned_bubbles:
            scene["bubbles"] = cleaned_bubbles

    # オノマトペ: 3シーン以内に同じ組み合わせがあれば除去
    for i in range(1, len(results)):
        curr_se = set(results[i].get("onomatopoeia", []))
        if not curr_se:
            continue
        # 直前3シーンまでチェック
        for j in range(max(0, i - 3), i):
            prev_se = set(results[j].get("onomatopoeia", []))
            if prev_se and curr_se == prev_se:
                results[i]["onomatopoeia"] = []
                log_message(f"  シーン{results[i].get('scene_id', '?')}: シーン{results[j].get('scene_id', '?')}と同一SE除去")
                break

def auto_fix_script(results: list, char_profiles: list = None) -> list:
    """生成結果の自動修正（APIコスト不要のローカル後処理）"""
    import re

    # === キャラ名の正規化マップ構築 ===
    correct_names = []  # [(correct_full_name, family, given)]
    if char_profiles:
        for cp in char_profiles:
            name = cp.get("character_name", "")
            if not name or len(name) < 2:
                continue
            correct_names.append(name)

    # テキストフィールド一覧
    text_fields = ["description", "location_detail", "direction", "story_flow", "title"]

    for scene in results:
        # 1. "(XX字)" マーカーの除去
        for field in text_fields + ["mood"]:
            if field in scene and isinstance(scene[field], str):
                scene[field] = re.sub(r'[（(]\d+字[以内程度上]*[）)]', '', scene[field]).strip()

        if "character_feelings" in scene and isinstance(scene["character_feelings"], dict):
            scene["character_feelings"] = {
                k: re.sub(r'[（(]\d+字[以内程度上]*[）)]', '', v).strip()
                for k, v in scene["character_feelings"].items()
            }

        # 2. キャラ名の修正（全フィールド対象）
        if correct_names:
            # 2a. character_feelingsのキー修正
            if "character_feelings" in scene and isinstance(scene["character_feelings"], dict):
                new_feelings = {}
                for key, val in scene["character_feelings"].items():
                    corrected_key = _fix_character_name(key, correct_names)
                    new_feelings[corrected_key] = val
                scene["character_feelings"] = new_feelings

            # 2b. bubblesのspeaker修正
            if "bubbles" in scene:
                for bubble in scene["bubbles"]:
                    speaker = bubble.get("speaker", "")
                    if speaker:
                        bubble["speaker"] = _fix_character_name(speaker, correct_names)

            # 2c. テキストフィールド内のキャラ名修正
            for field in text_fields:
                text = scene.get(field, "")
                if text:
                    scene[field] = _fix_names_in_text(text, correct_names)

        # 3. SDプロンプトのquality括弧修正
        if "sd_prompt" in scene and scene["sd_prompt"]:
            sd = scene["sd_prompt"]
            quality_tags = {"masterpiece", "best_quality", "best quality", "high_quality", "highres", "absurdres"}
            match = re.match(r'^\(([^)]+)\)', sd)
            if match:
                inner_tags = [t.strip() for t in match.group(1).split(",")]
                quality_only = []
                non_quality = []
                for tag in inner_tags:
                    base_tag = re.sub(r':[\d.]+$', '', tag).strip().lower()
                    if base_tag in quality_tags:
                        quality_only.append(tag)
                    else:
                        non_quality.append(tag)
                if non_quality:
                    new_quality = "(" + ", ".join(quality_only) + ")"
                    rest = sd[match.end():].lstrip(", ")
                    non_quality_str = ", ".join(non_quality)
                    scene["sd_prompt"] = f"{new_quality}, {non_quality_str}, {rest}".rstrip(", ")

    # 4. scene_id連番修正（1, 2, 3, ... に強制リナンバー）
    for i, scene in enumerate(results):
        scene["scene_id"] = i + 1

    # 5. シーン間の同一セリフ・SE重複除去
    _deduplicate_across_scenes(results)

    return results


# ---------------------------------------------------------------------------
# 設定スタイル検出: コンセプトから背景の世界観を推定し、SDタグを補正する
# ---------------------------------------------------------------------------
SETTING_STYLES = {
    "traditional_japanese_rural": {
        "keywords": ["夜這い", "村", "田舎", "農村", "山里", "漁村", "集落",
                     "古民家", "昔ながら", "伝統", "風習", "因習", "祭り",
                     "大正", "昭和初期", "時代劇", "和風の村"],
        "replace": {
            "bed": "futon",
            "bedroom": "japanese_room",
            "brick_wall": "wooden_wall",
            "concrete": "wooden_floor",
            "warehouse": "storehouse",
            "sofa": "zabuton",
            "table": "chabudai",
            "curtains": "shoji",
            "nightstand": "andon",
            "pillow": "sobagara_pillow",
            "blanket": "futon_blanket",
            "modern": "traditional",
            "apartment": "old_japanese_house",
            "hotel_room": "ryokan_room",
            "alley": "village_path",
            "narrow_street": "rural_path",
        },
        "prohibit": {"brick_wall", "concrete", "modern", "neon",
                     "skyscraper", "office", "elevator", "subway",
                     "highway", "parking", "urban", "city_lights",
                     "apartment", "hotel"},
        "append": ["traditional", "japanese", "wooden", "rural",
                   "old_house", "tatami", "shoji", "dim"],
        "prompt_hint": "和風田舎・伝統的日本家屋（茅葺き屋根、板壁、障子、畳、布団、囲炉裏、行灯、土間）。現代的な家具・建材(ベッド、レンガ、コンクリート)は絶対に使わない",
    },
    "traditional_japanese_urban": {
        "keywords": ["遊郭", "花街", "吉原", "江戸", "京都", "芸者", "花魁",
                     "大正ロマン", "料亭"],
        "replace": {
            "bed": "futon",
            "bedroom": "japanese_room",
            "brick_wall": "wooden_wall",
            "concrete": "wooden_floor",
            "sofa": "zabuton",
            "curtains": "noren",
            "nightstand": "andon",
        },
        "prohibit": {"concrete", "modern", "skyscraper", "office",
                     "elevator", "subway", "highway"},
        "append": ["traditional", "japanese", "wooden", "paper_lantern",
                   "tatami", "fusuma", "ornate"],
        "prompt_hint": "和風花街・遊郭風（襖、行灯、赤い照明、障子、畳、掛け軸、豪華な着物）。現代要素禁止",
    },
    "fantasy_medieval": {
        "keywords": ["ファンタジー", "異世界", "中世", "魔法", "王国", "城",
                     "冒険者", "ギルド", "騎士", "魔王", "勇者", "ドラゴン",
                     "エルフ", "ダンジョン"],
        "replace": {
            "apartment": "stone_chamber",
            "hotel_room": "inn_room",
            "concrete": "stone_wall",
            "office": "throne_room",
            "subway": "underground_passage",
        },
        "prohibit": {"modern", "neon", "skyscraper", "office",
                     "elevator", "subway", "highway", "smartphone",
                     "computer"},
        "append": ["fantasy", "medieval", "stone", "torch",
                   "candlelight"],
        "prompt_hint": "中世ファンタジー風（石造りの壁、蝋燭、松明、木製家具、革製品）。現代要素禁止",
    },
}


def _detect_setting_style(concept: str) -> Optional[dict]:
    """コンセプト文字列からSETTING_STYLESのどれに該当するか判定する。"""
    if not concept:
        return None
    concept_lower = concept.lower()
    for style_key, style in SETTING_STYLES.items():
        for kw in style["keywords"]:
            if kw in concept or kw in concept_lower:
                return style
    return None


def enhance_sd_prompts(results: list, char_profiles: list = None,
                       setting_style: Optional[dict] = None) -> list:
    """全シーンのSDプロンプトを後処理で最適化（APIコスト不要）。

    - 日本語タグ除去
    - quality tags確保
    - キャラタグ補完
    - 照明タグ追加
    - 重要表情タグにウェイト付加
    - 設定スタイルに基づくタグ置換・追加・禁止
    - 重複排除
    """
    import re as _re

    char_danbooru = []
    if char_profiles:
        for cp in char_profiles:
            char_danbooru.extend(cp.get("danbooru_tags", []))

    LIGHTING_WORDS = {"lighting", "sunlight", "moonlight", "candlelight",
                      "backlight", "rim_light", "neon", "lamp", "golden_hour",
                      "light_rays", "volumetric"}

    # ウェイト付加対象（SD画像の品質に直結する重要タグ）
    WEIGHT_EXPRESSION = {"ahegao", "orgasm", "rolling_eyes", "tongue_out",
                         "crying_with_eyes_open", "fucked_silly", "mindbreak",
                         "head_back", "drooling", "heart-shaped_pupils",
                         "tears_of_pleasure", "arched_back", "clenched_teeth"}
    WEIGHT_ACTION = {"deep_penetration", "cum_in_pussy", "overflow",
                     "multiple_penises", "double_penetration"}

    # intensity別 表情・身体反応タグ自動注入マップ
    _INTENSITY_EXPRESSION_MAP = {
        3: ["blush", "parted_lips", "panting", "nervous", "heavy_breathing"],
        4: ["open_mouth", "moaning", "tears", "sweating", "head_back",
            "arched_back", "clenched_fists", "trembling"],
        5: ["ahegao", "rolling_eyes", "tongue_out", "drooling", "head_back",
            "arched_back", "toes_curling", "full_body_arch", "tears"],
    }

    for scene in results:
        sd = scene.get("sd_prompt", "")
        if not sd:
            continue

        tags = [t.strip() for t in sd.split(",") if t.strip()]
        sd_lower = sd.lower()

        # 1. 日本語タグ除去
        tags = [t for t in tags if not _re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', t)]

        # 1.5. 室内外矛盾タグ自動修正
        _outdoor_mk = {"outdoors", "park", "forest", "beach", "poolside", "rooftop", "garden"}
        _indoor_mk = {"indoors", "classroom", "bedroom", "bathroom", "kitchen", "elevator",
                       "office", "living_room", "train_interior", "car_interior"}
        _tags_norm = {t.strip().lower().replace(" ", "_") for t in tags}
        _has_win = any("window" in t.lower() for t in tags)
        if _tags_norm & _outdoor_mk:
            _rm = {"ceiling", "fluorescent_light", "wallpaper", "chandelier",
                   "carpet", "wooden_floor", "tile_floor"}
            tags = [t for t in tags if t.strip().lower().replace(" ", "_") not in _rm]
        if (_tags_norm & _indoor_mk) and not _has_win:
            _rm_out = {"sky", "cloud", "horizon"}
            if "open_air_bath" not in " ".join(tags).lower():
                tags = [t for t in tags if t.strip().lower().replace(" ", "_") not in _rm_out]

        # 2. quality tags先頭確保
        quality_found = any("masterpiece" in t.lower() or "best_quality" in t.lower() for t in tags)
        if not quality_found:
            tags.insert(0, QUALITY_POSITIVE_TAGS)

        # 3. キャラタグ補完（上位タグが欠落していれば追加）
        if char_danbooru:
            existing = {t.strip().lower().replace(" ", "_") for t in tags}
            insert_at = 1  # quality tagsの直後
            for ct in char_danbooru[:8]:
                if ct.lower().replace(" ", "_") not in existing:
                    tags.insert(insert_at, ct)
                    insert_at += 1
                    existing.add(ct.lower().replace(" ", "_"))

        # 4. 照明タグ追加
        has_light = any(any(lw in t.lower() for lw in LIGHTING_WORDS) for t in tags)
        if not has_light:
            if any(kw in sd_lower for kw in ("night", "dark", "evening")):
                tags.append("dim_lighting")
            elif any(kw in sd_lower for kw in ("morning", "sunrise", "dawn")):
                tags.append("soft_lighting")
            elif any(kw in sd_lower for kw in ("sunset", "dusk", "golden")):
                tags.append("warm_lighting")
            else:
                tags.append("natural_lighting")

        # 4.2. 背景タグ保証（sd_promptに背景系タグが無い場合、locationから補完）
        _bg_kw = {"classroom", "bedroom", "bathroom", "kitchen", "living_room", "office",
                  "outdoors", "indoors", "park", "forest", "beach", "rooftop",
                  "hotel_room", "onsen", "bath", "pool", "cafe", "restaurant",
                  "shrine", "temple", "alley", "garden", "library", "hallway"}
        _exist_low = {t.strip().lower().replace(" ", "_") for t in tags}
        if not (_exist_low & _bg_kw):
            _location = scene.get("location_detail", scene.get("location", ""))
            if _location:
                _loc_map = {"教室": "classroom", "寝室": "bedroom", "浴室": "bathroom",
                            "風呂": "bathroom", "台所": "kitchen", "リビング": "living_room",
                            "オフィス": "office", "公園": "park", "森": "forest",
                            "海": "beach", "屋上": "rooftop", "ホテル": "hotel_room",
                            "温泉": "onsen", "プール": "pool", "カフェ": "cafe",
                            "神社": "shrine", "寺": "temple", "路地": "alley",
                            "庭": "garden", "図書": "library", "廊下": "hallway",
                            "保健室": "infirmary", "体育": "gym", "車": "car_interior",
                            "電車": "train_interior", "居酒屋": "izakaya"}
                _added = False
                for _jp, _en in _loc_map.items():
                    if _jp in _location:
                        tags.append(_en)
                        _added = True
                        break
                if not _added:
                    tags.append("indoors")

        # 4.5. intensity≥3のシーンにfaceless_male自動付与
        intensity = scene.get("intensity", 0)
        if intensity >= 3:
            existing_lower = {t.strip().lower().replace(" ", "_") for t in tags}
            for male_tag in ["1boy", "faceless_male"]:
                if male_tag not in existing_lower:
                    tags.append(male_tag)
                    existing_lower.add(male_tag)

        # 4.6. intensity別 表情・身体反応タグ自動注入
        if intensity >= 3:
            inject_tags = _INTENSITY_EXPRESSION_MAP.get(min(intensity, 5), [])
            existing_lower = {t.strip().lower().replace(" ", "_") for t in tags}
            for et in inject_tags:
                if et not in existing_lower:
                    tags.append(et)
                    existing_lower.add(et)

        # 5. 設定スタイル適用（タグ置換・禁止・追加）
        if setting_style:
            replace_map = setting_style.get("replace", {})
            prohibit = setting_style.get("prohibit", set())
            append_tags = setting_style.get("append", [])

            new_tags = []
            for t in tags:
                norm = t.strip().lower().replace(" ", "_")
                # ウェイト付きタグからnorm抽出
                inner = _re.sub(r'[()]', '', norm).split(":")[0].strip()
                # 禁止タグ除去
                if inner in prohibit:
                    continue
                # タグ置換
                if inner in replace_map:
                    new_tags.append(replace_map[inner])
                else:
                    new_tags.append(t)
            tags = new_tags

            # 雰囲気タグ追加（未存在のもののみ）
            existing_norm = {t.strip().lower().replace(" ", "_") for t in tags}
            for at in append_tags:
                if at.lower().replace(" ", "_") not in existing_norm:
                    tags.append(at)
                    existing_norm.add(at.lower().replace(" ", "_"))

        # 6. 重要タグにウェイト付加（未ウェイトのもののみ）
        weighted = []
        for tag in tags:
            norm = tag.strip().lower().replace(" ", "_").strip("()")
            # 既にウェイト付きならスキップ
            if ":" in tag and "(" in tag:
                weighted.append(tag)
                continue
            if norm in WEIGHT_EXPRESSION:
                weighted.append(f"({tag}:1.3)")
            elif norm in WEIGHT_ACTION:
                weighted.append(f"({tag}:1.2)")
            else:
                weighted.append(tag)

        scene["sd_prompt"] = deduplicate_sd_tags(", ".join(weighted))

    return results

# タグDB（キャッシュ）
_tag_db_cache = None

def _load_tag_db() -> dict:
    """danbooru_tags.jsonからタグDBを読み込み（キャッシュ付き）"""
    global _tag_db_cache
    if _tag_db_cache is not None:
        return _tag_db_cache
    
    if DANBOORU_TAGS_JSON.exists():
        try:
            with open(DANBOORU_TAGS_JSON, "r", encoding="utf-8") as f:
                _tag_db_cache = json.load(f)
                log_message(f"タグDB読み込み完了: {DANBOORU_TAGS_JSON.name}")
                return _tag_db_cache
        except Exception as e:
            log_message(f"タグDB読み込みエラー: {e}")
    
    # フォールバック: 最小限のタグ
    _tag_db_cache = {
        "locations": {
            "教室": "classroom, school_desk, chair, chalkboard, window, school_interior",
            "寝室": "bedroom, bed, pillow, blanket, curtains, indoor, dim_lighting",
            "浴室": "bathroom, shower, bathtub, steam, wet, tiles, water",
            "リビング": "living_room, sofa, couch, cushion, tv, indoor",
            "屋上": "rooftop, fence, sky, school_rooftop, outdoor",
            "公園": "park, bench, trees, grass, outdoor, sunlight",
            "電車": "train_interior, seat, window, handrail",
            "ホテル": "hotel_room, bed, luxurious, curtains, dim_lighting",
            "オフィス": "office, desk, computer, chair, window, indoor"
        },
        "time_of_day": {
            "朝": "morning, sunrise, soft_lighting, warm_colors",
            "昼": "daytime, bright, sunlight, clear_sky",
            "放課後": "afternoon, golden_hour, warm_lighting, sunset_colors",
            "夕方": "evening, sunset, orange_sky, golden_light, dusk",
            "夜": "night, dark, moonlight, dim_lighting, starry_sky",
            "深夜": "late_night, darkness, lamp_light, intimate_lighting"
        },
        "compositions": {},
        "expressions": {},
        "poses_by_intensity": {},
        "clothing": {},
        "undress_states": {}
    }
    return _tag_db_cache


def _select_serihu_skill(theme: str = "", char_profiles: list = None) -> str:
    """キャラ性格・テーマに応じてセリフスキルを自動選択"""
    # 1. キャラ性格からツンデレ判定
    if char_profiles:
        for cp in char_profiles:
            personality = cp.get("personality_core", {})
            desc = personality.get("brief_description", "")
            traits = personality.get("main_traits", [])
            all_text = f"{desc} {' '.join(traits)}".lower()
            if "ツンデレ" in all_text or "ツン" in all_text or "tsundere" in all_text:
                return "ero_serihu_tundere"

    # 2. テーマ判定
    theme_lower = theme.lower() if theme else ""
    # 純愛系 → 甘々スキル
    if theme_lower in ("love", "vanilla"):
        return "ero_serihu_jyunai"
    # ハード系 → オホ声スキル
    if theme_lower in ("netorare", "humiliation", "forced", "corruption", "gangbang"):
        return "ero_serihu_ohogoe"

    # 3. デフォルト
    return "ero_serihu_nomal"


# === データクラス ===
@dataclass
class CostTracker:
    haiku_input: int = 0
    haiku_output: int = 0
    sonnet_input: int = 0
    sonnet_output: int = 0

    def add(self, model: str, input_tokens: int, output_tokens: int):
        if any(kw in model for kw in ("haiku", "mini", "fast")):
            self.haiku_input += input_tokens
            self.haiku_output += output_tokens
        else:
            self.sonnet_input += input_tokens
            self.sonnet_output += output_tokens

    def _get_costs(self):
        return COSTS.get(MODELS["haiku"], {"input": 0, "output": 0}), COSTS.get(MODELS["sonnet"], {"input": 0, "output": 0})

    def total_cost_usd(self) -> float:
        cheap, premium = self._get_costs()
        return (
            (self.haiku_input / 1_000_000) * cheap["input"] +
            (self.haiku_output / 1_000_000) * cheap["output"] +
            (self.sonnet_input / 1_000_000) * premium["input"] +
            (self.sonnet_output / 1_000_000) * premium["output"]
        )

    def summary(self) -> str:
        return (
            f"Haiku: {self.haiku_input:,} in / {self.haiku_output:,} out\n"
            f"Sonnet: {self.sonnet_input:,} in / {self.sonnet_output:,} out\n"
            f"推定コスト: ${self.total_cost_usd():.4f}"
        )


def estimate_cost(num_scenes: int, use_sonnet_polish: bool = True) -> dict:
    """生成前にコストを予測"""
    # 平均的なトークン数の見積もり
    # Phase 1: コンテキスト圧縮 (Haiku)
    phase1_input = 500
    phase1_output = 150
    
    # Phase 2: アウトライン + シーン生成 (Haiku)
    outline_input = 600
    outline_output = 800
    scene_input = 3000  # per scene
    scene_output = 500  # per scene
    
    # Phase 3: 品質チェック (Haiku)
    quality_input = 2000
    quality_output = 300
    
    # Sonnet polish (intensity >= 5のシーンのみ、約20%)
    sonnet_scenes = int(num_scenes * 0.2) if use_sonnet_polish else 0
    sonnet_input = 2000 * sonnet_scenes
    sonnet_output = 600 * sonnet_scenes
    
    haiku_input = phase1_input + outline_input + (scene_input * num_scenes) + quality_input
    haiku_output = phase1_output + outline_output + (scene_output * num_scenes) + quality_output
    
    haiku_cost = COSTS[MODELS["haiku"]]
    sonnet_cost = COSTS[MODELS["sonnet"]]
    
    estimated_usd = (
        (haiku_input / 1_000_000) * haiku_cost["input"] +
        (haiku_output / 1_000_000) * haiku_cost["output"] +
        (sonnet_input / 1_000_000) * sonnet_cost["input"] +
        (sonnet_output / 1_000_000) * sonnet_cost["output"]
    )
    
    return {
        "haiku_tokens": haiku_input + haiku_output,
        "sonnet_tokens": sonnet_input + sonnet_output,
        "estimated_usd": estimated_usd,
        "estimated_jpy": estimated_usd * 150  # 概算レート
    }


# === ユーティリティ ===
def load_file(filepath: Path) -> str:
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return ""


def load_skill(skill_name: str) -> str:
    skill_file = SKILLS_DIR / f"{skill_name}.skill.md"
    if skill_file.exists():
        return skill_file.read_text(encoding="utf-8")
    return ""


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_message(f"設定ファイル読み込みエラー: {e}")
    return {}


def save_config(config: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


# === プロファイル管理 ===
def get_profile_list() -> list[str]:
    """保存されているプロファイル一覧を取得"""
    profiles = []
    for f in PROFILES_DIR.glob("*.json"):
        profiles.append(f.stem)
    return sorted(profiles)


def save_profile(name: str, config: dict):
    """プロファイルを保存"""
    profile_path = PROFILES_DIR / f"{name}.json"
    config["profile_name"] = name
    config["saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    log_message(f"プロファイル保存: {name}")


def load_profile(name: str) -> dict:
    """プロファイルを読み込み"""
    profile_path = PROFILES_DIR / f"{name}.json"
    if profile_path.exists():
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def delete_profile(name: str) -> bool:
    """プロファイルを削除"""
    profile_path = PROFILES_DIR / f"{name}.json"
    if profile_path.exists():
        profile_path.unlink()
        log_message(f"プロファイル削除: {name}")
        return True
    return False


def copy_profile(src_name: str, dst_name: str) -> bool:
    """プロファイルをコピー"""
    src_path = PROFILES_DIR / f"{src_name}.json"
    if src_path.exists():
        config = load_profile(src_name)
        config["profile_name"] = dst_name
        save_profile(dst_name, config)
        log_message(f"プロファイルコピー: {src_name} → {dst_name}")
        return True
    return False


def log_message(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


# === API呼び出し ===
def call_claude(
    client: anthropic.Anthropic,
    model: str,
    system,
    user: str,
    cost_tracker: CostTracker,
    max_tokens: int = 4096,
    callback: Optional[Callable] = None
) -> str:
    for attempt in range(MAX_RETRIES):
        try:
            model_name = "Haiku" if "haiku" in model else "Sonnet"
            log_message(f"API呼び出し開始: {model_name} (試行 {attempt + 1}/{MAX_RETRIES})")
            
            if callback:
                callback(f"API呼び出し中 ({model_name})...")

            # Prompt Caching対応: systemがlistならそのまま、strならブロック化
            if isinstance(system, list):
                system_param = system
            else:
                system_param = system

            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_param,
                messages=[{"role": "user", "content": user}],
                timeout=120.0  # 2分タイムアウト
            )

            usage = response.usage
            cost_tracker.add(model, usage.input_tokens, usage.output_tokens)
            
            # キャッシュ統計ログ
            cache_creation = getattr(usage, 'cache_creation_input_tokens', 0) or 0
            cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
            if cache_creation or cache_read:
                log_message(f"{model_name}: {usage.input_tokens} in, {usage.output_tokens} out (cache: +{cache_creation} create, {cache_read} read)")
            else:
                log_message(f"{model_name}: {usage.input_tokens} in, {usage.output_tokens} out")

            return response.content[0].text

        except anthropic.RateLimitError as e:
            wait_time = RETRY_DELAY * (2 ** (attempt + 1))
            log_message(f"Rate limit: {e} (待機{wait_time}秒)")
            if callback:
                callback(f"レート制限、{wait_time}秒待機...")
            time.sleep(wait_time)

        except anthropic.APIStatusError as e:
            if e.status_code == 401:
                raise ValueError("APIキーが無効です")
            log_message(f"API error {e.status_code}: {e}")
            if attempt < MAX_RETRIES - 1:
                if callback:
                    callback(f"APIエラー、再試行中...")
                time.sleep(RETRY_DELAY)
            else:
                raise

        except anthropic.APITimeoutError as e:
            log_message(f"API timeout: {e}")
            if callback:
                callback(f"タイムアウト、再試行中...")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise RuntimeError(f"APIタイムアウト（{MAX_RETRIES}回試行）")

        except Exception as e:
            log_message(f"Error: {e}")
            if callback:
                callback(f"エラー: {str(e)[:30]}...")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise

    raise RuntimeError("最大リトライ回数を超えました")


def _call_api(
    client,
    model: str,
    system,
    user: str,
    cost_tracker: CostTracker,
    max_tokens: int = 4096,
    callback: Optional[Callable] = None
) -> str:
    """Claude API呼び出し"""
    return call_claude(client, model, system, user, cost_tracker, max_tokens, callback)


def parse_json_response(text: str):
    """Parse JSON from API response, handling markdown code blocks and prefixed text."""
    original_text = text
    log_message(f"Raw API response: {text[:1000]}")
    
    try:
        # マークダウンコードブロック除去
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
        
        text = text.strip()
        
        # JSONの前にある前置きテキストを除去
        # 「{」または「[」で始まる部分を探す
        if text and not text.startswith("{") and not text.startswith("["):
            # 最初の { または [ を探す
            brace_idx = text.find("{")
            bracket_idx = text.find("[")
            
            if brace_idx == -1 and bracket_idx == -1:
                log_message(f"No JSON found in response: {text[:300]}")
                raise ValueError(f"No JSON in response: {original_text[:150]}")
            
            # より早く出現する方を使用
            if brace_idx == -1:
                start_idx = bracket_idx
            elif bracket_idx == -1:
                start_idx = brace_idx
            else:
                start_idx = min(brace_idx, bracket_idx)
            
            log_message(f"Stripping prefix text before JSON (index {start_idx})")
            text = text[start_idx:]
        
        # 末尾の余分なテキストも除去（JSONの閉じ括弧以降）
        if text.startswith("{"):
            # 対応する } を探す
            depth = 0
            end_idx = 0
            for i, c in enumerate(text):
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        end_idx = i + 1
                        break
            if end_idx > 0:
                text = text[:end_idx]
        elif text.startswith("["):
            # 対応する ] を探す
            depth = 0
            end_idx = 0
            for i, c in enumerate(text):
                if c == "[":
                    depth += 1
                elif c == "]":
                    depth -= 1
                    if depth == 0:
                        end_idx = i + 1
                        break
            if end_idx > 0:
                text = text[:end_idx]
        
        text = text.strip()
        if not text:
            log_message(f"Empty response after parsing. Original: {original_text[:500]}")
            raise ValueError(f"Empty response: {original_text[:200]}")
        
        return json.loads(text)
    except json.JSONDecodeError as e:
        log_message(f"JSON parse error: {e}")
        log_message(f"Parsed text: {text[:500]}")
        raise ValueError(f"Invalid JSON: {str(e)[:50]}. Text: {text[:100]}...") from e


# === Skill 1: Prompt Compactor ===
def compact_context(
    client: anthropic.Anthropic,
    concept: str,
    characters: str,
    theme: str,
    cost_tracker: CostTracker,
    callback: Optional[Callable] = None
) -> dict:
    skill = load_skill("prompt_compactor")
    prompt = f"""以下の作品情報を、トークン効率の良い形式に圧縮してください。

## 作品コンセプト
{concept}

## 登場人物
{characters}

## テーマ
{theme if theme else "指定なし"}

## 出力形式（JSON）
{{
    "setting": "舞台（短文）",
    "chars": [
        {{"name": "名前", "look": "外見（箇条書き）", "voice": "口調特徴"}}
    ],
    "tone": "トーン（1語）",
    "theme": "テーマ（1語）",
    "ng": ["NG要素"]
}}

冗長な説明を排除し、箇条書きで簡潔に。JSONのみ出力。"""

    if callback:
        callback("[PACK]コンテキスト圧縮中...")

    response = _call_api(
        client, MODELS["haiku"],
        skill if skill else "You compress prompts to save tokens. Output only JSON.",
        prompt, cost_tracker, 1024, callback
    )
    return parse_json_response(response)


def compact_context_local(
    concept: str,
    characters: str,
    theme: str,
    char_profiles: list,
    callback: Optional[Callable] = None
) -> dict:
    """キャラプロファイルからローカルでcontext JSONを構築（API不要）"""
    if callback:
        callback("[PACK]コンテキスト圧縮中（ローカル・API節約）...")

    theme_guide = THEME_GUIDES.get(theme, THEME_GUIDES.get("vanilla", {}))

    # 舞台を概念テキストから抽出（最初の1文 or 50文字）
    setting = concept.strip() if concept.strip() else "日常"

    # キャラ情報をプロファイルから構築
    chars = []
    ng_all = []
    for cp in char_profiles:
        name = cp.get("character_name", "")
        physical = cp.get("physical_description", {})
        speech = cp.get("speech_pattern", {})
        avoid = cp.get("avoid_patterns", [])

        look_parts = []
        if physical.get("hair"):
            look_parts.append(f"髪:{physical['hair']}")
        if physical.get("eyes"):
            look_parts.append(f"目:{physical['eyes']}")
        if physical.get("body"):
            look_parts.append(f"体型:{physical['body']}")
        if physical.get("chest"):
            look_parts.append(f"胸:{physical['chest']}")

        voice_parts = []
        if speech.get("first_person"):
            voice_parts.append(f"一人称:{speech['first_person']}")
        endings = speech.get("sentence_endings", [])
        if endings:
            voice_parts.append(f"語尾:{','.join(endings[:3])}")

        chars.append({
            "name": name,
            "look": ", ".join(look_parts),
            "voice": ", ".join(voice_parts)
        })
        ng_all.extend(avoid[:3])

    # テーマに基づくトーン
    tone = theme_guide.get("name", "一般")
    theme_label = theme_guide.get("name", "指定なし")

    context = {
        "setting": setting,
        "chars": chars,
        "tone": tone,
        "theme": theme_label,
        "ng": list(set(ng_all))[:5]
    }

    log_message(f"コンテキスト圧縮完了（ローカル）: chars={len(chars)}, setting={setting[:30]}")
    if callback:
        callback("[OK] コンテキスト圧縮完了（ローカル・API節約）")

    return context


def generate_synopsis(
    client: anthropic.Anthropic,
    concept: str,
    context: dict,
    num_scenes: int,
    theme: str,
    cost_tracker: CostTracker,
    callback: Optional[Callable] = None
) -> str:
    """コンセプトから短い一本のストーリーあらすじを生成（Haiku API 1回）"""
    theme_guide = THEME_GUIDES.get(theme, THEME_GUIDES.get("vanilla", {}))
    theme_name = theme_guide.get("name", "指定なし")
    story_arc = theme_guide.get("story_arc", "導入→展開→本番→余韻")
    key_emotions = theme_guide.get("key_emotions", ["期待", "緊張", "快感", "幸福"])
    story_elements = theme_guide.get("story_elements", [])

    if callback:
        callback(f"[STORY]{theme_name}テーマでストーリー原案を作成中...")

    chars = context.get("chars", [])
    char_info = ""
    for c in chars:
        name = c.get("name", "")
        look = c.get("look", "")
        voice = c.get("voice", "")
        char_info += f"・{name}: {look} / {voice}\n"

    elements_str = "\n".join(f"・{e}" for e in story_elements) if story_elements else "・特になし"
    emotions_str = "、".join(key_emotions)

    prompt = f"""以下の作品コンセプトに基づき、FANZA同人CG集のストーリーあらすじ（400〜600字）を書いてください。

## 作品コンセプト
{concept}

## 登場キャラクター
{char_info}
## テーマ: {theme_name}
- ストーリーの流れ: {story_arc}
- 重要な感情: {emotions_str}
- ストーリー要素:
{elements_str}

## シーン数: {num_scenes}シーン

## あらすじの要件
1. コンセプトの設定（場所、人間関係、状況）を忠実に反映すること
2. 起承転結のある一貫したストーリーであること
3. テーマ「{theme_name}」のアーク「{story_arc}」に沿うこと
4. プロローグ（約20%）→ 展開・焦らし（約30%）→ 本番エロシーン（約40%）→ エピローグ（約10%）の配分
5. 各キャラの個性・口調が活きる展開にすること
6. 本番パートでは具体的な行為の流れも簡潔に含めること
7. エロシーンは段階的にエスカレートし、クライマックスに向かうこと
8. コンセプトにない極端な展開は絶対に追加しないこと（コンセプトの範囲内で物語を展開する）

あらすじの文章のみ出力してください。JSON不要。"""

    try:
        response = _call_api(
            client, MODELS["haiku"],
            f"FANZA同人CG集の脚本家です。ユーザーのコンセプトに基づき、エロ同人作品の完全なストーリーあらすじを作成します。成人向けコンテンツを忠実に生成します。",
            prompt, cost_tracker, 2048, callback
        )

        synopsis = response.strip()
        log_message(f"あらすじ生成完了: {len(synopsis)}文字")
        if callback:
            callback(f"[OK]ストーリー原案完成（{len(synopsis)}文字）")

        return synopsis

    except Exception as e:
        log_message(f"あらすじ生成エラー: {e}")
        if callback:
            callback(f"[WARN]あらすじ生成失敗: {str(e)[:50]}")
        # フォールバック: コンセプトをそのままあらすじとして使用
        return concept


# === Skill 2: Low Cost Pipeline ===

def generate_scene_batch(
    client: anthropic.Anthropic,
    context: dict,
    scenes: list,
    jailbreak: str,
    sd_guide: str,
    cost_tracker: CostTracker,
    theme: str = "",
    char_profiles: list = None,
    callback: Optional[Callable] = None,
    story_so_far: str = ""
) -> list:
    """複数のLow-Intensityシーンをまとめて1回のAPI呼び出しで生成（API節約）"""
    skill = load_skill("low_cost_pipeline")
    danbooru_nsfw = load_skill("danbooru_nsfw_tags")
    scene_composer = load_skill("nsfw_scene_composer")
    serihu_skill_name = _select_serihu_skill(theme, char_profiles)
    serihu_skill = load_skill(serihu_skill_name)
    visual_skill = load_skill("cg_visual_variety")

    theme_guide = THEME_GUIDES.get(theme, THEME_GUIDES.get("vanilla", {}))
    theme_name = theme_guide.get("name", "指定なし")
    dialogue_tone = theme_guide.get("dialogue_tone", "自然で楽しい雰囲気")
    use_heart = theme_guide.get("use_heart", True)
    theme_sd_tags = theme_guide.get("sd_tags", "")
    theme_sd_expressions = theme_guide.get("sd_expressions", "")
    key_emotions = theme_guide.get("key_emotions", [])

    tag_db = _load_tag_db()
    loc_tags_db = tag_db.get("locations", {})
    time_tags_db = tag_db.get("time_of_day", {})

    # キャラガイド（低intensity用＝簡潔版）
    char_guide = ""
    char_danbooru_tags = []
    char_names = []

    if char_profiles:
        for cp in char_profiles:
            name = cp.get("character_name", "")
            char_names.append(name)
            speech = cp.get("speech_pattern", {})
            avoid = cp.get("avoid_patterns", [])
            physical = cp.get("physical_description", {})
            tags = cp.get("danbooru_tags", [])
            char_danbooru_tags.extend(tags)

            emotional = cp.get("emotional_speech", {})
            char_guide += f"""
【{name}】口調ガイド
・一人称: {speech.get('first_person', '私')} / 語尾: {', '.join(speech.get('sentence_endings', ['〜よ', '〜ね']))}
・間投詞: {', '.join(speech.get('fillers', ['あっ', 'んっ']))}
・照れた時: {emotional.get('when_embarrassed', '言葉に詰まる')}
・甘える時: {emotional.get('when_flirty', '甘い声で')}
・外見: 髪={physical.get('hair', '')}, 目={physical.get('eyes', '')}
・NG: {', '.join(avoid) if avoid else 'なし'}
"""

    heart_instruction = "♡は甘いシーンで自然に使用OK。" if use_heart else f"テーマ「{theme_name}」のspeechでは♡控えめ。ただしmoan（喘ぎ）では♡を積極的に使え（不本意な快楽表現として有効）。"

    # 共通システムプロンプト（CG集フォーマット対応）
    common_system = f"""{jailbreak}

{skill if skill else "FANZA同人CG集の脚本を生成します。"}

{danbooru_nsfw if danbooru_nsfw else ""}

{scene_composer if scene_composer else ""}

{char_guide if char_guide else "（キャラ設定なし）"}

## FANZA同人CG集とは

「セリフ付きCG集」＝エロい1枚絵に吹き出しとオノマトペを乗せた画像が何ページも続くコンテンツ。
**画像がメイン、テキストはサブ**。

各ページの構成:
- 1枚のCG画像
- 吹き出し1〜4個（超短文: 1〜10文字）
- オノマトペ0〜2個

【吹き出しの鉄則】
- 1吹き出し＝1〜10文字。句読点不要
- type: speech（会話）/ moan（喘ぎ）/ thought（心の声）
- 状況説明は吹き出しに入れない（descriptionに書く）

{f'''
## ⚠️ セリフ品質ガイド（厳守・最優先）

bubblesのtextは以下の【喘ぎ声バリエーション集】と【鉄則】に厳密に従え。
「タスク手順」「不自然診断」「改訂版セリフ」等のセクションは無視せよ。

★ 喘ぎ声は必ず下記辞書の【段階1〜4】から選べ。自分で喘ぎを創作するな。
★ intensityに対応する段階を使え（intensity 1-2=段階1、intensity 3=段階2、intensity 4=段階3、intensity 5=段階4）
★ 前シーンで使った喘ぎと同じものは絶対禁止。毎シーン辞書の別パターンを選べ。

{serihu_skill}
''' if serihu_skill else ''}

{f'''
## CG集ビジュアル構成ガイド

{visual_skill}
''' if visual_skill else ''}

全キャラ成人(18+)。JSON配列形式のみ出力。"""

    # ストーリー連続性セクション
    story_context_section = ""
    if story_so_far:
        story_context_section = f"""
## ⚠️ ストーリーの連続性（最重要）

以下は前のシーンまでの展開です。**必ずこの続きとして**シーンを書いてください。

{story_so_far}

---
"""

    # 各シーンの情報を組み立て
    scenes_info = []
    for scene in scenes:
        intensity = scene.get("intensity", 2)
        location = scene.get("location", "室内")
        time_of_day = scene.get("time", "")

        location_tags = ""
        for key, tags in loc_tags_db.items():
            if key in location:
                location_tags = tags
                break
        if not location_tags:
            location_tags = "indoor, room"

        time_tags = ""
        for key, tags in time_tags_db.items():
            if key in time_of_day:
                time_tags = tags
                break

        char_tags_str = ", ".join(char_danbooru_tags[:15]) if char_danbooru_tags else ""
        
        intensity_sd_tags = {
            5: f"ahegao, rolling_eyes, tongue_out, drooling, head_back, arched_back, tears, trembling, orgasm, fucked_silly, {theme_sd_expressions}",
            4: f"open_mouth, moaning, tears, sweating, head_back, arched_back, heavy_breathing, panting, clenched_fists, {theme_sd_expressions}",
            3: f"kiss, french_kiss, undressing, groping, blush, nervous, anticipation, parted_lips, heavy_breathing, {theme_sd_expressions}",
            2: f"eye_contact, close-up, romantic, blushing, hand_holding, leaning_close, {theme_sd_expressions}",
            1: f"portrait, smile, casual, standing, looking_at_viewer, {theme_sd_expressions}"
        }
        sd_intensity_tags = intensity_sd_tags.get(intensity, "")
        background_tags = f"{location_tags}, {time_tags}".strip(", ")
        if theme_sd_tags:
            background_tags = f"{background_tags}, {theme_sd_tags}"

        # 設定スタイルの背景タグ追加
        batch_setting_style = _detect_setting_style(context.get("setting", ""))
        if batch_setting_style:
            style_append = ", ".join(batch_setting_style.get("append", []))
            if style_append:
                background_tags = f"{background_tags}, {style_append}"

        composition_db = tag_db.get("compositions", {})
        composition_tags = composition_db.get(str(intensity), {}).get("tags", "")

        scenes_info.append({
            "scene": scene,
            "char_tags_str": char_tags_str,
            "sd_intensity_tags": sd_intensity_tags,
            "background_tags": background_tags,
            "composition_tags": composition_tags
        })

    # 設定スタイルのヒント行（バッチ共通）
    batch_setting_style = _detect_setting_style(context.get("setting", ""))
    batch_setting_hint = ""
    if batch_setting_style:
        batch_setting_hint = f"\n背景スタイル必須: {batch_setting_style.get('prompt_hint', '')}"

    # バッチプロンプト構築
    prompt_parts = []
    if story_context_section:
        prompt_parts.append(story_context_section)
    prompt_parts.append(f"設定: {json.dumps(context, ensure_ascii=False)}\n")
    prompt_parts.append(f"テーマ「{theme_name}」のトーン: {dialogue_tone}\n{heart_instruction}\n")
    if batch_setting_hint:
        prompt_parts.append(batch_setting_hint)

    for idx, info in enumerate(scenes_info):
        scene = info["scene"]
        prompt_parts.append(f"""
--- シーン{idx+1} ---
シーン情報: {json.dumps(scene, ensure_ascii=False)}
キャラ固有タグ: {info['char_tags_str']}
ポーズ・表情: {info['sd_intensity_tags']}
背景・場所: {info['background_tags']}
構図: {info['composition_tags']}
""")

    prompt_parts.append(f"""
## 出力形式（JSON配列で{len(scenes)}シーン分を出力）

[
  {{
    "scene_id": シーンID,
    "title": "シーンタイトル",
    "description": "このシーンの詳細説明",
    "location_detail": "場所の具体的な描写",
    "mood": "雰囲気",
    "character_feelings": {{
        "{char_names[0] if char_names else 'ヒロイン'}": "心情"
    }},
    "bubbles": [
        {{"speaker": "キャラ名", "type": "speech", "text": "短い一言"}}
    ],
    "onomatopoeia": [],
    "direction": "演出・ト書き",
    "story_flow": "次のシーンへの繋がり",
    "sd_prompt": "{QUALITY_POSITIVE_TAGS}, キャラ外見タグ, ポーズ・行為タグ, 表情タグ, 場所・背景タグ"
  }}
]

## ルール
1. 必ず{len(scenes)}シーン分のJSON配列を出力
2. 各シーンのscene_idは指定通りに
3. **bubblesは1-2個、各text 1〜10文字**（CG集の吹き出し）
4. sd_promptは「{QUALITY_POSITIVE_TAGS} + キャラ外見 + ポーズ + 表情 + 場所・背景」の順
5. **sd_promptにオノマトペ・日本語テキストを含めない**（英語のDanbooruタグのみ）
6. タグは重複なくカンマ区切り
7. **シーン1→シーン2は自然に繋がるストーリーにすること**
8. **前シーンまでの展開を必ず引き継ぐこと**
9. **同じセリフ・オノマトペを複数シーンで繰り返さない**

JSON配列のみ出力。""")

    prompt = "\n".join(prompt_parts)

    system_with_cache = [
        {"type": "text", "text": common_system, "cache_control": {"type": "ephemeral"}},
    ]

    if callback:
        scene_ids = [s.get("scene_id") for s in scenes]
        callback(f"バッチ生成中: シーン {scene_ids} (Haiku, {len(scenes)}シーン一括)...")

    response = _call_api(
        client, MODELS["haiku"],
        system_with_cache,
        prompt, cost_tracker, 2500 * len(scenes), callback
    )

    # JSON配列をパース
    result_list = parse_json_response(response)
    
    if isinstance(result_list, dict):
        result_list = [result_list]
    
    for result in result_list:
        if isinstance(result, dict) and result.get("sd_prompt"):
            result["sd_prompt"] = deduplicate_sd_tags(result["sd_prompt"])

    while len(result_list) < len(scenes):
        missing_scene = scenes[len(result_list)]
        result_list.append({
            "scene_id": missing_scene.get("scene_id", len(result_list) + 1),
            "title": "生成不足",
            "mood": "一般",
            "bubbles": [],
            "onomatopoeia": [],
            "direction": "バッチ生成で不足",
            "sd_prompt": ""
        })

    return result_list[:len(scenes)]

def generate_outline(
    client: anthropic.Anthropic,
    context: dict,
    num_scenes: int,
    theme: str,
    cost_tracker: CostTracker,
    callback: Optional[Callable] = None,
    synopsis: str = "",
    story_structure: dict = None
) -> list:
    """あらすじをシーン分割してアウトライン生成（Haiku API 1回）"""
    theme_guide = THEME_GUIDES.get(theme, THEME_GUIDES.get("vanilla", {}))
    theme_name = theme_guide.get("name", "指定なし")
    story_arc = theme_guide.get("story_arc", "導入→展開→本番→余韻")
    key_emotions = theme_guide.get("key_emotions", ["期待", "緊張", "快感", "幸福"])
    story_elements = theme_guide.get("story_elements", [])

    if callback:
        callback(f"[INFO]{theme_name}テーマでシーン分割中（AI生成）...")

    chars = context.get("chars", [])
    char_names = [c["name"] for c in chars] if chars else ["ヒロイン"]

    # シーン配分計算（ユーザー設定 or デフォルト）
    if story_structure is None:
        story_structure = {"prologue": 10, "main": 80, "epilogue": 10}
    prologue_pct = story_structure.get("prologue", 10) / 100
    epilogue_pct = story_structure.get("epilogue", 10) / 100

    act1 = max(1, round(num_scenes * prologue_pct))       # プロローグ
    act4 = max(1, round(num_scenes * epilogue_pct))        # エピローグ
    main_scenes = num_scenes - act1 - act4                  # 本編合計
    if main_scenes < 2:
        main_scenes = 2
        act1 = max(1, num_scenes - main_scenes - 1)
        act4 = num_scenes - act1 - main_scenes
    act2 = max(1, round(main_scenes * 0.25))               # 前戯（本編の25%）
    act3 = main_scenes - act2                              # 本番（本編の75%）

    elements_str = chr(10).join(f'・{e}' for e in story_elements) if story_elements else "・特になし"

    prompt = f"""以下のストーリーあらすじを{num_scenes}シーンに分割し、各シーンの詳細をJSON配列で出力してください。

## ストーリーあらすじ（これに忠実に分割すること）
{synopsis}

## 登場キャラクター
{', '.join(char_names)}

## テーマ: {theme_name}
- ストーリーアーク: {story_arc}
- 重要な感情: {', '.join(key_emotions)}
- ストーリー要素:
{elements_str}

## シーン配分（{num_scenes}シーン・エロ70%以上）
- 第1幕・導入: {act1}シーン → intensity 1-2（最低限の状況設定。1ページで済ませる）
- 第2幕・前戯: {act2}シーン → intensity 3（焦らし・脱衣・愛撫）
- 第3幕・本番: {act3}シーン → intensity 4（基本）と5（クライマックスのみ最大2シーン）。必ず4→4→5→5→4のように段階をつけること
- 第4幕・余韻: {act4}シーン → intensity 3-4（事後・余韻。エロの余韻を残す）
※ FANZA CG集は読者がエロを求めて購入する。導入は短く、エロシーンを手厚く。

## 出力形式（JSON配列）
各シーンは以下の形式：
{{
    "scene_id": シーン番号,
    "title": "シーンタイトル",
    "goal": "このシーンの目的",
    "location": "場所",
    "time": "時間帯",
    "situation": "このシーンで何が起きるか（具体的な状況）",
    "story_flow": "前シーンからの繋がりと次シーンへの橋渡し",
    "emotional_arc": {{"start": "シーン冒頭の感情", "end": "シーン終わりの感情"}},
    "beats": ["展開ビート1", "展開ビート2", "展開ビート3"],
    "intensity": 1から5の数値,
    "erotic_level": "none/light/medium/heavy/climax",
    "viewer_hook": "視聴者を引き付けるポイント"
}}

## 絶対ルール
1. あらすじの内容を全シーンに漏れなく割り当てること
2. あらすじにない展開を勝手に追加しないこと
3. situationはあらすじの該当部分を具体的に記述すること（抽象表現禁止）
4. 各シーンは前シーンの直後から始まり、自然に繋がること
5. 本番シーン（intensity 4-5）は段階的にエスカレートすること
6. 最後から2番目のシーンがクライマックス（intensity 5）であること
7. 各シーンのsituationは必ず前シーンと異なる具体的展開にすること（「近づく」「囲まれる」等の同パターン繰り返し禁止）
8. **locationは3シーン連続で同じ場所にしてはならない**。場所を変えてストーリーを進めること。例: 部屋→廊下→浴室、教室→体育館倉庫→屋上
9. intensity 5は最大2シーンまで。残りの本番はintensity 4にして、緩急をつけること
10. intensity 1の次にintensity 3以上は禁止。必ずintensity 2を挟むこと（1→2→3→4→5の段階的上昇）

## ⚠️ エスカレーション段階ルール（飛躍禁止・最重要）

### 行為の段階（必ずこの順序で進めること。段階をスキップ禁止）
段階A: 会話・接近・ムード作り（intensity 1-2）
段階B: キス・愛撫・脱衣・前戯（intensity 3）
段階C: 1対1の性行為（intensity 4）
段階D: 激しい1対1 or 複数人（intensity 4-5）
段階E: クライマックス（intensity 5）

❌ 段階B（前戯）→ 段階D（複数人）は禁止。必ず段階C（1対1性行為）を挟むこと
❌ 1対1シーンの次にいきなり3人以上は禁止。1対1→2人→複数人と段階的に増やすこと

### 相手人数の段階
- 1人のシーンの次に3人以上のシーンは禁止
- 複数人に移行するなら、間に「相手が増える過程」のシーンを挟むこと

### 心理変化の段階
- 「抵抗している」→「完全堕落」の1シーン飛躍は禁止
- 抵抗→葛藤→受容→快楽→堕落の順で段階的に変化させること
- emotional_arcのstartは必ず前シーンのendと一致させること

### situationの具体性
各シーンのsituationには以下を必ず明記すること:
- 相手の人数（1人/2人/複数人）
- 行為の具体的内容（キス/愛撫/挿入/体位名）
- 場所の移動理由（前シーンと場所が変わる場合）

JSON配列のみ出力。"""

    try:
        response = _call_api(
            client, MODELS["haiku"],
            f"FANZA同人CG集の脚本プランナーです。ストーリーあらすじを忠実に{num_scenes}シーンに分割し、各シーンの詳細設計をJSON配列で出力します。",
            prompt, cost_tracker, 4096, callback
        )

        outline = parse_json_response(response)

        if not isinstance(outline, list) or len(outline) == 0:
            raise ValueError("Invalid outline response")

        # 必須フィールドの補完
        for i, scene in enumerate(outline):
            scene.setdefault("scene_id", i + 1)
            scene.setdefault("title", f"シーン{i+1}")
            scene.setdefault("goal", "")
            scene.setdefault("location", "室内")
            scene.setdefault("time", "")
            scene.setdefault("situation", "")
            scene.setdefault("story_flow", "")
            scene.setdefault("emotional_arc", {"start": "", "end": ""})
            scene.setdefault("beats", [])
            scene.setdefault("intensity", 3)
            scene.setdefault("erotic_level", "medium")
            scene.setdefault("viewer_hook", "")

        # intensity分布の自動修正
        intensity_5_count = sum(1 for s in outline if s.get("intensity", 3) == 5)
        if intensity_5_count > 2:
            # intensity 5を最大2シーンに制限（最後の2シーンを5にし、残りを4に）
            five_indices = [i for i, s in enumerate(outline) if s.get("intensity", 3) == 5]
            keep_five = five_indices[-2:]  # 最後の2つを5のまま
            for i in five_indices:
                if i not in keep_five:
                    outline[i]["intensity"] = 4
            log_message(f"intensity 5を{intensity_5_count}→2シーンに自動修正")

        # intensity 1→3以上の飛躍を修正
        for i in range(1, len(outline)):
            prev_intensity = outline[i-1].get("intensity", 3)
            curr_intensity = outline[i].get("intensity", 3)
            if prev_intensity == 1 and curr_intensity >= 3:
                outline[i]["intensity"] = 2
                log_message(f"シーン{i+1}: intensity {curr_intensity}→2に修正（1→3以上の飛躍防止）")

        # intensity 2段階以上の飛躍を修正（2→4, 2→5, 3→5 等）
        for i in range(1, len(outline)):
            prev_intensity = outline[i-1].get("intensity", 3)
            curr_intensity = outline[i].get("intensity", 3)
            if curr_intensity - prev_intensity >= 2:
                fixed = prev_intensity + 1
                outline[i]["intensity"] = fixed
                log_message(f"シーン{i+1}: intensity {curr_intensity}→{fixed}に修正（{prev_intensity}→{curr_intensity}の飛躍防止）")

        # erotic_levelとintensityの整合性を修正
        erotic_map = {1: "none", 2: "light", 3: "medium", 4: "heavy", 5: "climax"}
        for scene in outline:
            scene["erotic_level"] = erotic_map.get(scene.get("intensity", 3), "medium")

        log_message(f"アウトライン生成完了（API）: {len(outline)}シーン, テーマ: {theme_name}")
        if callback:
            callback(f"[OK]シーン分割完成（AI生成）: {len(outline)}シーン")

        return outline

    except Exception as e:
        log_message(f"アウトラインAPI生成失敗、テンプレートフォールバック: {e}")
        import traceback
        log_message(traceback.format_exc())
        if callback:
            callback(f"[WARN]AI分割失敗、テンプレートで代替: {str(e)[:50]}")

        # === テンプレートフォールバック ===
        arc_parts = [p.strip() for p in story_arc.replace("→", "/").split("/")]
        outline = []
        scene_id = 0
        for i in range(num_scenes):
            scene_id += 1
            if scene_id <= act1:
                intensity = 1 if i == 0 else 2
                erotic = "none" if i == 0 else "light"
                arc_label = arc_parts[0] if arc_parts else "導入"
            elif scene_id <= act1 + act2:
                intensity = 2 if (scene_id - act1) <= act2 // 2 else 3
                erotic = "light" if intensity == 2 else "medium"
                arc_label = arc_parts[1] if len(arc_parts) > 1 else "展開"
            elif scene_id <= act1 + act2 + act3:
                is_climax = (scene_id == act1 + act2 + act3)
                intensity = 5 if is_climax else 4
                erotic = "climax" if is_climax else "heavy"
                arc_label = arc_parts[2] if len(arc_parts) > 2 else "本番"
            else:
                intensity = 2
                erotic = "light"
                arc_label = arc_parts[-1] if arc_parts else "余韻"

            outline.append({
                "scene_id": scene_id,
                "title": arc_label,
                "goal": "",
                "location": "室内",
                "time": "",
                "situation": f"（あらすじ参照）{synopsis[:100] if synopsis else ''}",
                "story_flow": "",
                "emotional_arc": {"start": "", "end": ""},
                "beats": [],
                "intensity": intensity,
                "erotic_level": erotic,
                "viewer_hook": ""
            })

        log_message(f"テンプレートフォールバック: {len(outline)}シーン")
        return outline



def extract_scene_summary(scene: dict) -> str:
    """シーンの要約を抽出（次シーンのstory_so_farに使用）"""
    sid = scene.get("scene_id", "?")
    title = scene.get("title", "")
    desc = scene.get("description", "")[:120]
    location = scene.get("location_detail", "")
    mood = scene.get("mood", "")
    intensity = scene.get("intensity", 3)
    
    # 吹き出しの要約
    bubbles = scene.get("bubbles", [])
    bubble_texts = []
    for b in bubbles:
        speaker = b.get("speaker", "")
        btype = b.get("type", "")
        text = b.get("text", "")
        bubble_texts.append(f"{speaker}({btype}):「{text}」")
    bubbles_str = ", ".join(bubble_texts) if bubble_texts else "なし"
    
    # オノマトペの要約
    onomatopoeia = scene.get("onomatopoeia", [])
    se_str = ", ".join(onomatopoeia) if onomatopoeia else "なし"
    
    # 心情の要約
    feelings = scene.get("character_feelings", {})
    feelings_str = ", ".join(f"{k}: {v}" for k, v in feelings.items()) if feelings else ""
    
    # ストーリーフロー（次への繋がり）
    story_flow = scene.get("story_flow", "")
    
    return (
        f"[シーン{sid}] {title} (intensity={intensity}, {mood}) "
        f"場所:{location} / {desc}\n"
        f"  心情: {feelings_str}\n"
        f"  吹き出し: {bubbles_str}\n"
        f"  SE: {se_str}\n"
        f"  次への繋がり: {story_flow}"
    )

def generate_scene_draft(
    client: anthropic.Anthropic,
    context: dict,
    scene: dict,
    jailbreak: str,
    sd_guide: str,
    cost_tracker: CostTracker,
    theme: str = "",
    char_profiles: list = None,
    callback: Optional[Callable] = None,
    story_so_far: str = "",
    synopsis: str = ""
) -> dict:
    skill = load_skill("low_cost_pipeline")

    # Danbooruタグ強化スキルを読み込み
    danbooru_nsfw = load_skill("danbooru_nsfw_tags")

    # NSFWシーン構成スキル
    scene_composer = load_skill("nsfw_scene_composer")

    # エロ漫画セリフスキルを性格・テーマ別に選択
    serihu_skill_name = _select_serihu_skill(theme, char_profiles)
    serihu_skill = load_skill(serihu_skill_name)

    # CG集ビジュアル多様性スキル
    visual_skill = load_skill("cg_visual_variety")

    # テーマ別ガイドを取得
    theme_guide = THEME_GUIDES.get(theme, THEME_GUIDES.get("vanilla", {}))
    theme_name = theme_guide.get("name", "指定なし")
    dialogue_tone = theme_guide.get("dialogue_tone", "自然で楽しい雰囲気")
    use_heart = theme_guide.get("use_heart", True)
    theme_sd_tags = theme_guide.get("sd_tags", "")
    theme_sd_expressions = theme_guide.get("sd_expressions", "")
    key_emotions = theme_guide.get("key_emotions", [])
    story_elements = theme_guide.get("story_elements", [])
    
    # シーンの重要度
    intensity = scene.get("intensity", 3)
    location = scene.get("location", "室内")
    time_of_day = scene.get("time", "")
    
    # タグDB読み込み（外部JSON対応）
    tag_db = _load_tag_db()
    
    # 背景タグテンプレート
    loc_tags_db = tag_db.get("locations", {})
    time_tags_db = tag_db.get("time_of_day", {})
    
    # 場所と時間帯のタグを取得
    location_tags = ""
    for key, tags in loc_tags_db.items():
        if key in location:
            location_tags = tags
            break
    if not location_tags:
        location_tags = "indoor, room"
    
    time_tags = ""
    for key, tags in time_tags_db.items():
        if key in time_of_day:
            time_tags = tags
            break
    
    # キャラプロファイルをintensity別に圧縮（API節約）
    char_guide = ""
    char_danbooru_tags = []
    char_names = []

    if char_profiles:
        for cp in char_profiles:
            name = cp.get("character_name", "")
            char_names.append(name)
            speech = cp.get("speech_pattern", {})
            emotional = cp.get("emotional_speech", {})
            examples = cp.get("dialogue_examples", {})
            relationship = cp.get("relationship_speech", {})
            avoid = cp.get("avoid_patterns", [])
            physical = cp.get("physical_description", {})
            tags = cp.get("danbooru_tags", [])

            char_danbooru_tags.extend(tags)

            if intensity <= 2:
                char_guide += f"""
【{name}】口調: 一人称={speech.get('first_person', '私')}, 語尾={', '.join(speech.get('sentence_endings', [])[:3])}, 間投詞={', '.join(speech.get('fillers', ['あっ'])[:2])}
外見: 髪={physical.get('hair', '')}, 目={physical.get('eyes', '')}, 体型={physical.get('body', '')}
NG: {', '.join(avoid[:3]) if avoid else 'なし'}
"""
            elif intensity == 3:
                char_guide += f"""
【{name}】口調ガイド
・一人称: {speech.get('first_person', '私')} / 語尾: {', '.join(speech.get('sentence_endings', ['〜よ', '〜ね']))}
・間投詞: {', '.join(speech.get('fillers', ['あっ', 'んっ']))}
・照れた時: {emotional.get('when_embarrassed', '言葉に詰まる')}
・甘える時: {emotional.get('when_flirty', '甘い声で')}
・外見: 髪={physical.get('hair', '')}, 目={physical.get('eyes', '')}
・NG: {', '.join(avoid) if avoid else 'なし'}
"""
            else:
                char_guide += f"""
═══════════════════════════════════════
【{name}】完全口調ガイド
═══════════════════════════════════════

■ 基本設定
・一人称: {speech.get('first_person', '私')}
・語尾: {', '.join(speech.get('sentence_endings', ['〜よ', '〜ね']))}
・よく使う表現: {', '.join(speech.get('favorite_expressions', [])[:5])}
・間投詞（息遣い）: {', '.join(speech.get('fillers', ['あっ', 'んっ']))}

■ 感情別の話し方
・照れた時: {emotional.get('when_embarrassed', '言葉に詰まる')}
・感じてる時: {emotional.get('when_flirty', '甘い声で')}
・感じてる時(エロ): {emotional.get('when_aroused', '声が震える')}
・絶頂時: {emotional.get('when_climax', '理性が飛ぶ')}

■ セリフのお手本
・好意: 「{examples.get('affection', '好きだよ')}」
・喘ぎ（軽）: {examples.get('moaning_light', 'あっ...んっ...')}
・喘ぎ（激）: {examples.get('moaning_intense', 'あっあっ...♡')}

■ 恋人への話し方
{relationship.get('to_lover', '甘えた調子で話す')}

■ NG表現: {', '.join(avoid) if avoid else 'なし'}
■ 外見: 髪={physical.get('hair', '')}, 目={physical.get('eyes', '')}, 体型={physical.get('body', '')}
"""

    # ♡使用のルール（テーマ別）
    heart_instruction = ""
    if use_heart:
        heart_instruction = "♡は甘いシーンで自然に使用OK。"
    else:
        heart_instruction = f"""
テーマ「{theme_name}」のspeech（会話）では♡は控えめに。
ただし**moan（喘ぎ）では♡を積極的に使え**（不本意な快楽の表現として効果的）。
セリフ品質ガイドの喘ぎ辞書にある♡はそのまま使用すること。
"""

    # テーマ別セリフトーン指示
    theme_dialogue_instruction = f"""
## テーマ「{theme_name}」のセリフトーン

{dialogue_tone}

【このテーマで重要な感情】
{', '.join(key_emotions) if key_emotions else '自然な感情表現'}

【ストーリー要素として入れるべきもの】
{chr(10).join(f'・{e}' for e in story_elements[:3]) if story_elements else '・特になし'}

{heart_instruction}
"""

    # シーン重要度別のエロ指示（5段階）- CG集フォーマット対応
    if intensity >= 5:
        erotic_instruction = f"""
## クライマックスシーン（intensity 5）

最高潮のエロシーン。画像が全てを語る。絶頂・射精・快楽堕ちの瞬間。

【descriptionの書き方（50字以上）】
具体的な行為・体位・身体の状態を描写。
例: 「正常位で激しくピストンされ、両足を男の腰に巻きつけた三玖が絶頂を迎える。目を見開き舌を出し、膣が痙攣する中で中出しされている。」
❌ 「快感に溺れている」のような抽象表現は禁止。何をされて、体がどうなっているか書け。

【吹き出し指針（3-4個）】
・女: 絶頂系の喘ぎ2-3個（★セリフ品質ガイドの【段階4】から選べ。自作するな。前シーンと被らないこと）
・男: 言葉責め0-1個
  例: 「中に出すぞ」「全部受けろ」「イケ」

【オノマトペ指針（3-4個・辞書から選べ）】
・射精系+反応系+抽送系を組み合わせる
  例: ドビュッ, ビクビクッ, パンパンパン, ドクドクッ

【心情】
・{key_emotions[2] if len(key_emotions) > 2 else '快感に溺れる'}
・{key_emotions[3] if len(key_emotions) > 3 else '理性と本能の葛藤'}

【禁止】
❌ 長文の吹き出し（10文字超え）
❌ 説明的なセリフ
❌ 冷静な会話
❌ 前シーンと同じ喘ぎパターン
"""
    elif intensity == 4:
        erotic_instruction = f"""
## 本番シーン（intensity 4）

濃厚なエロシーン。挿入・激しい行為。画像の行為を吹き出しが補強。

【descriptionの書き方（50字以上）】
具体的な行為・体位・身体の反応を描写。
例: 「背後から挿入され、机に手をついて喘ぐ三玖。男の手が胸を鷲掴みにし、乳首を弄っている。腰が自然と動き出し、快感に抗えなくなっている。」
❌ 「快感に溺れていく」「罪悪感と快楽の狭間」のような抽象表現のみは禁止

【吹き出し指針（3-4個）】
・女: 喘ぎ+短い反応2-3個（★セリフ品質ガイドの【段階3】から選べ。自作するな。前シーンと被らないこと）
・男: 言葉責め1個
  例: 「いい声だな」「もっと鳴け」「感じてんだろ？」「締まりいいな」

【オノマトペ指針（2-3個・辞書から選べ）】
・挿入系+抽送系+濡れ系を組み合わせる
  例: ズブッ, パンパン, グチュグチュ

【心情】
・{key_emotions[1] if len(key_emotions) > 1 else '恥ずかしさと快感の葛藤'}
・{key_emotions[2] if len(key_emotions) > 2 else 'もっと欲しいという欲求'}

【禁止】
❌ 説明的なセリフ
❌ 長い会話文
❌ 前シーンと同じ喘ぎパターン
"""
    elif intensity == 3:
        erotic_instruction = f"""
## 前戯・焦らしシーン（intensity 3）

エロの助走。脱衣・愛撫・キス等。期待感を煽る画像に短い吹き出し。

【吹き出し指針（2-3個）】
・女: ドキドキ感のある反応1-2個（★セリフ品質ガイドの【段階2】から選べ）
・男: 煽りor会話0-1個
  例: 「おとなしくしろ」「いい体してんな」「脱げ」

【オノマトペ指針（1-2個）】
・愛撫系+心音系: サワッ, チュッ, ゾクッ, ドキドキ, ペロッ, スルッ

【心情】
・{key_emotions[0] if key_emotions else 'ドキドキと期待'}
・恥ずかしいけど…という葛藤
"""
    elif intensity == 2:
        erotic_instruction = f"""
## ムード構築シーン（intensity 2）

雰囲気作り。接近する画像に自然な一言。

【吹き出し指針】
・自然な短い会話（1-2個）
・例: 「ねえ…」「え…？」

【オノマトペ指針】
・なし or 1個: ドキッ

【心情】
・{key_emotions[0] if key_emotions else '緊張とドキドキ'}
"""
    else:
        erotic_instruction = f"""
## 導入シーン（intensity 1）

状況設定。キャラ紹介の画像に短い会話。

【吹き出し指針】
・自然な一言（1-2個）。状況説明はdescriptionで行い、吹き出しは最小限
・例: 「ただいま〜」「久しぶり…」

【オノマトペ指針】
・なし

【心情】
・日常の中の雰囲気
"""

    # キャラ固有SDタグの組み込み
    char_tags_str = ", ".join(char_danbooru_tags[:15]) if char_danbooru_tags else ""
    
    # テーマ別SDタグを追加
    theme_tags_combined = f"{theme_sd_tags}, {theme_sd_expressions}".strip(", ")
    
    # === Prompt Caching: 共通部分（全シーンで同一）とシーン固有部分を分離 ===
    
    # 共通部分（キャッシュ対象）- CG集フォーマット完全対応
    common_system = f"""{jailbreak}

{skill if skill else "FANZA同人CG集の脚本を生成します。"}

{danbooru_nsfw if danbooru_nsfw else ""}

{scene_composer if scene_composer else ""}

{char_guide if char_guide else "（キャラ設定なし）"}

## FANZA同人CG集とは

「セリフ付きCG集」＝エロい1枚絵に吹き出しとオノマトペを乗せた画像が何ページも続くコンテンツ。
**画像がメイン、テキストはサブ**。小説でも脚本でもない。

各ページの構成:
- 1枚のエロCG画像（SDで生成）
- 吹き出し1〜4個（超短文: 1〜10文字が理想）
- オノマトペ0〜4個（効果音テキスト）

## 吹き出しの書き方

【種類】
1. speech（会話）: キャラの短い発言。「ねえ…」「だめ…」「来ないで…」
2. moan（喘ぎ）: 声・息・反応。「あっ♡」「んぁ…っ」「はぁ…はぁ…」
3. thought（心の声）: 画像上の小さい文字。「やばい…」「もう…」「彼氏に…」

【男性キャラの吹き出し（0-1個/ページ厳守）】
男のセリフが多いと「うるさい」と不評になる。女性の喘ぎが主役。
・支配系: 「逃がさねぇよ」「おとなしくしろ」「言えよ」
・事実描写系（最も効果的）: 「すげえ締まる」「全部出すぞ」「奥まで入ったな」
・挑発系: 「感じてんだろ？」「もう濡れてる」「弱いとこわかってるよ」
・優しめ責め: 「気持ちいい？」「もっと聞かせて」「我慢しなくていいよ」
※男のセリフは短く粗野に。丁寧語禁止。1ページ最大1個。

【鉄則】
- 1吹き出し = 1〜10文字（最大でも12文字）
- 句読点不要。「...」「…」「っ」「〜」で繋ぐ
- 状況説明は吹き出しに入れない（descriptionに書く）
- 吹き出しの中に主語や目的語を入れない
- 「私は〜」「あなたが〜」のような文章はNG
- 会話のキャッチボールではなく、画像の補強テキスト
- **bubblesの内容はdescriptionのシーン内容と一致させる**こと
- **画像+吹き出し+オノマトペだけで視聴者にシーンが伝わる**ようにする

【thoughtの書き方（重要）】
thoughtは感情の断片。説明や反省はNG。
✅「やば…」「もう…むり…」「なにこれ…」「おかしく…なる」
❌「彼氏に...ごめん...」（反省文→不自然）
❌「彼のことなんて...忘れてしまった」（ナレーション→不自然）
❌「こんなことをしている自分が信じられない」（独白→長すぎ）
❌「なぜ私に…これは夢じゃない」（説明→不自然）
NTR系のthoughtは: 「彼より…」「もう…戻れない」「なんで…こんなに」等の短い感情断片

【intensity別の目安】
- 1-2: 吹き出し1-2個（自然な一言）、オノマトペなし〜1個
- 3: 吹き出し2-3個（反応+短い声）、オノマトペ1-2個
- 4-5: 吹き出し2-4個（喘ぎメイン+男の言葉責め）、オノマトペ2-4個

## ⚠️ 絶対厳守ルール

### セリフ・オノマトペ重複禁止
**全シーンを通じて同じセリフ・喘ぎ・オノマトペの組み合わせを2回以上使うな。**
story_so_farに含まれるセリフと同じ・類似のものは絶対禁止。
毎シーン必ず辞書の別パターンを選べ。バリエーションがCG集の生命線。

### 場所名の一貫性
同じ場所は**全シーンで同一の表記**を使え。
❌ 「神社の境内」→「神殿の祭壇」→「神社の祭壇」（表記ブレ）
✅ 「村の神社」→「村の神社」→「村の神社」（統一）
最初のシーンで確定した場所名をそのまま使い続けること。

### エロシーン優先
FANZA CG集はエロがメイン。**全体の70%以上をエロシーンに充てる**こと。
・10ページなら導入1-2ページ、エロ7-8ページ
・導入は最小限に。読者は素早くエロシーンに入りたい
・descriptionよりも**sd_promptとbubblesの質にこだわれ**
・エロシーンではdescriptionは行為の具体的描写（体位、状態、反応）を書け

## 喘ぎ声パターン辞書（補助。★セリフ品質ガイドの段階別辞書を優先して使え）

・吐息系: はぁ…, ふぅ…♡, んはぁ…, ふぁ…っ, すぅ…はぁ…
・声漏れ系: あっ, やぁ…, ひゃっ, くぅん, あぅ…, きゃっ, みゃっ
・甘え系: もっと…♡, そこ…♡, ねぇ…♡, いい…♡, すき…♡
・我慢系: んんっ…!, くっ…, うぅ…っ, ぐっ…, んぅ…っ
・否定系: やだ…, だめ…, いや…っ, むり…, やめ…
・快感否定: いやっ…でも…, だめなのに…♡, 嫌…なのに…
・堕落系: もっと…ちょうだい♡, もう…戻れない♡, おかしく…なる♡
・絶頂系: イっ…♡, イっちゃ…っ, あああっ…!, もうだめ…♡, きもちぃ…♡
・絶頂後: はぁ…はぁ…, もう…むり…, びくっ…, まだ…ダメ…
・懇願系: お願い…, 許して…, もう…許して…♡
・混乱系: なにこれ…, おかしい…, 頭…真っ白…

## オノマトペ辞書（場面に合わせて選べ・同じ組み合わせの連続禁止）

・挿入系: ズブッ, ズブズブ, ヌプッ, ズリュッ, ブチュッ, ヌルッ, ズンッ
・抽送系: パンパン, ズチュズチュ, グチュグチュ, ヌチュヌチュ, ピチャピチャ, パチュパチュ
・愛撫系: サワッ, ツー, ペロッ, チュッ, レロレロ, コリッ, ニュルッ
・吸引系: チュパッ, ジュルッ, ゴクッ, ンチュ, チュルル, レロッ
・射精系: ドクドク, ビュルル, ドビュッ, ピュッピュッ, ドクッドクッ, ビュクッ
・反応系: ビクッ, ビクビク, ガクガク, プルプル, ゾクッ, ブルッ, ワナワナ
・心音系: ドキドキ, バクバク, トクン, ドクンドクン
・衝撃系: ドンッ, バンッ, ギシギシ, ミシッ, ガタン, バシッ
・濡れ系: トロッ, ジュワッ, グショッ, タラッ, ヌルヌル, ベチャ
・剥ぎ系: ビリッ, バサッ, スルッ, シュルッ, パサッ

## 良い例 vs 悪い例

✅「あっ♡」（喘ぎ2文字）
❌「そこを触られると気持ちいいです」（15文字・説明的）

✅「逃がさねぇよ」（男の言葉責め6文字）
❌「心配するな、俺たちは優しくしてやる」（18文字・丁寧すぎ）

✅「やだ…っ」（否定3文字）
❌「こんなことしないでください…」（14文字・文章）

✅「きもちぃ…♡」（堕落5文字）
❌「あなたに触れられて体が熱くなる」（15文字・小説）

✅ 心の声:「彼より…」（3文字・感情断片）
❌ 心の声:「彼氏に...ごめん...」（8文字・反省文で不自然）

✅ 心の声:「もう…戻れない」（7文字・状態の暗示）
❌ 心の声:「彼のことなんて...忘れてしまった」（15文字・ナレーション）

✅ オノマトペ: ズブッ, グチュグチュ, ビクッ
❌ オノマトペは吹き出しの中に入れない（別フィールド）

## speech吹き出しで状況を伝えるテクニック

descriptionの説明がなくても、画像+吹き出しで視聴者に伝わるようにする。
・抵抗シーン: 「やめ…」+男「おとなしくしろ」→ 強制されているとわかる
・堕落シーン: 「もっと…♡」+男「もう正直だな」→ 快楽に堕ちたとわかる
・NTR比較: 「こんなの…初めて…♡」→ 彼氏より気持ちいいと暗示
・絶頂シーン: 「イっ…ちゃ…♡」+オノマトペ「ドビュッ」→ 中出し絶頂とわかる

{f'''
## ⚠️ セリフ品質ガイド（厳守・最優先）

bubblesのtextは以下の【喘ぎ声バリエーション集】と【鉄則】に厳密に従え。
「タスク手順」「不自然診断」「改訂版セリフ」等のセクションは無視せよ。

★ 喘ぎ声は必ず下記辞書の【段階1〜4】から選べ。自分で喘ぎを創作するな。
★ intensityに対応する段階を使え（intensity 1-2=段階1、intensity 3=段階2、intensity 4=段階3、intensity 5=段階4）
★ 前シーンで使った喘ぎと同じものは絶対禁止。毎シーン辞書の別パターンを選べ。

{serihu_skill}
''' if serihu_skill else ''}

{f'''
## CG集ビジュアル構成ガイド

{visual_skill}
''' if visual_skill else ''}

全キャラ成人(18+)。JSON形式のみ出力。"""

    # シーン固有部分（毎回変わる）
    scene_system = f"""{erotic_instruction}

{theme_dialogue_instruction}"""

    # Prompt Caching: systemをリスト形式でcache_control付与
    system_with_cache = [
        {"type": "text", "text": common_system, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": scene_system}
    ]

    # シーン別SD推奨タグ（ポーズ・表情）+ テーマ別タグ - 大幅拡張
    intensity_sd_tags = {
        5: f"ahegao, orgasm, cum, creampie, cum_overflow, cum_on_body, trembling, convulsing, full_body_spasm, tears, heavy_breathing, drooling, rolling_eyes, tongue_out, mind_break, fucked_silly, sweat, wet, multiple_boys, gangbang, {theme_sd_expressions}",
        4: f"sex, vaginal, penetration, nude, spread_legs, missionary, doggy_style, cowgirl_position, moaning, sweat, blush, panting, pussy_juice, groping, breast_grab, multiple_boys, faceless_male, grabbing_hips, {theme_sd_expressions}",
        3: f"kiss, french_kiss, undressing, groping, breast_grab, nipple_play, fingering, blush, nervous, anticipation, wet_panties, bra_pull, panties_aside, embarrassed, {theme_sd_expressions}",
        2: f"eye_contact, close-up, romantic, blushing, hand_holding, leaning_close, nervous, looking_away, {theme_sd_expressions}",
        1: f"portrait, smile, casual, standing, looking_at_viewer, {theme_sd_expressions}"
    }
    
    sd_intensity_tags = intensity_sd_tags.get(intensity, "")
    
    # 背景タグを組み合わせ
    background_tags = f"{location_tags}, {time_tags}".strip(", ")

    # テーマタグを背景に追加（intensity 3以上のみ）
    if theme_sd_tags and intensity >= 3:
        background_tags = f"{background_tags}, {theme_sd_tags}"

    # 設定スタイルから背景ヒントを取得
    setting_style = _detect_setting_style(context.get("setting", ""))
    setting_hint_line = ""
    if setting_style:
        hint = setting_style.get("prompt_hint", "")
        style_append = ", ".join(setting_style.get("append", []))
        if style_append:
            background_tags = f"{background_tags}, {style_append}"
        if hint:
            setting_hint_line = f"\n背景スタイル必須: {hint}"

    # 構図タグ（intensity連動）
    composition_db = tag_db.get("compositions", {})
    composition_tags = composition_db.get(str(intensity), {}).get("tags", "")

    # あらすじセクション（全シーン共通の物語の骨格）
    synopsis_section = ""
    if synopsis:
        synopsis_section = f"""## 参考: 作品全体のあらすじ
{synopsis}
---
"""

    # ストーリー連続性セクション（使用済みセリフを明示抽出）
    story_context_section = ""
    if story_so_far:
        # story_so_farから使用済みセリフ・SEを抽出してブラックリスト化
        import re as _re
        used_bubbles = []
        used_se = []
        for line in story_so_far.split("\n"):
            line = line.strip()
            if line.startswith("吹き出し:"):
                # 「」で囲まれたテキストを個別抽出
                bubble_content = line[len("吹き出し:"):].strip()
                if bubble_content and bubble_content != "なし":
                    used_bubbles.append(bubble_content)
            elif line.startswith("SE:"):
                se_content = line[len("SE:"):].strip()
                if se_content and se_content != "なし":
                    used_se.append(se_content)

        blacklist_parts = []
        if used_bubbles:
            blacklist_parts.append("【使用済みセリフ（同一・類似禁止）】")
            for ub in used_bubbles:
                blacklist_parts.append(f"  ❌ {ub}")
        if used_se:
            blacklist_parts.append("【使用済み効果音（同一組み合わせ禁止）】")
            for us in used_se:
                blacklist_parts.append(f"  ❌ {us}")
        used_blacklist = "\n".join(blacklist_parts) if blacklist_parts else "（初回シーンのため禁止リストなし）"

        story_context_section = f"""
## ⚠️ ストーリーの連続性（最重要）

以下は前のシーンまでの展開です。**必ずこの続きとして**シーンを書いてください。

{story_so_far}

### 🚫 使用禁止リスト（以下と同じ・類似は絶対禁止）
{used_blacklist}

### 禁止事項（違反したら不合格）
- **上の使用禁止リストにあるセリフ・SE・thoughtと同一または類似は使用不可**
- **前シーンと同じ状況描写・同じ展開の繰り返し禁止**
- **ストーリーを必ず前シーンより先に進めること（行為をエスカレート）**
- **同じ場所名は前シーンと同じ表記を使え（表記ブレ禁止）**
- **キャラ名は{', '.join(char_names) if char_names else 'ヒロイン'}のみ使用**

### ⚠️ エスカレーション制御（段階飛躍禁止）
- **前シーンの行為レベルから1段階だけ進めること**
- 前シーンが前戯なら→このシーンは挿入開始。いきなり複数人や絶頂は禁止
- 前シーンが1対1なら→このシーンも1対1か、せいぜい2人目の登場まで
- 前シーンで抵抗していたなら→このシーンは葛藤。いきなり完全堕落は禁止
- **心情の変化は前シーンの「次への繋がり」を必ず引き継ぐこと**
---
"""

    prompt = f"""{synopsis_section}{story_context_section}設定: {json.dumps(context, ensure_ascii=False)}
シーン情報: {json.dumps(scene, ensure_ascii=False)}

## 出力形式（この形式で出力してください）

{{
    "scene_id": {scene['scene_id']},
    "title": "シーンタイトル",
    "description": "このシーンの詳細説明。場所、状況、何が起きているか、画像として何が描かれるかを説明",
    "location_detail": "場所の具体的な描写",
    "mood": "雰囲気",
    "character_feelings": {{
        "{char_names[0] if char_names else 'ヒロイン'}": "このシーンでの心情"
    }},
    "bubbles": [
        {{"speaker": "キャラ名", "type": "speech", "text": "短い一言"}},
        {{"speaker": "キャラ名", "type": "moan", "text": "あっ♡"}},
        {{"speaker": "キャラ名", "type": "thought", "text": "心の声"}}
    ],
    "onomatopoeia": ["効果音1", "効果音2"],
    "direction": "演出・ト書き",
    "story_flow": "次のシーンへの繋がり",
    "sd_prompt": "{QUALITY_POSITIVE_TAGS}, キャラ外見タグ, ポーズ・行為タグ, 表情タグ, 場所・背景タグ, 照明タグ, テーマタグ"
}}

## タグ参考（sd_promptに統合して使用）

キャラ固有: {char_tags_str}
ポーズ・表情: {sd_intensity_tags}
背景・場所: {background_tags}
構図: {composition_tags}
テーマ専用: {theme_tags_combined}{setting_hint_line}

## ルール

1. descriptionは必ず100字程度で詳しく書く。**具体的な体位・行為・身体の状態・表情**を書け。「囲まれている」「溺れている」のような抽象表現のみは不可
2. character_feelingsで心情を明確に。前シーンと異なる感情変化を示すこと
3. **bubblesは1-4個。各textは1〜10文字**（CG集の吹き出し。短いほど良い）
4. typeはspeech/moan/thoughtの3種。intensity 4-5はmoanメイン
5. **onomatopoeiaは場面に合った効果音**（intensity 1-2はなし〜1個、3は1-2個、4-5は2-4個）
6. sd_promptは「{QUALITY_POSITIVE_TAGS}」の後にカンマで区切り「キャラ外見 + ポーズ + 表情 + 場所・背景 + 照明」を続ける。quality括弧の中にはmasterpiece, best_qualityのみ入れる。キャラ名やheadphones等の外見タグは括弧外に書くこと
7. **sd_promptはこのシーンの実際の内容のみを反映**すること
8. **sd_promptにオノマトペ・日本語テキストを含めない**（英語のDanbooruタグのみ使用）
9. **前シーンの流れを必ず引き継ぐこと**
10. **キャラの一人称・語尾はキャラガイドを絶対厳守**
11. **descriptionは全て日本語で書くこと**（英語タグはsd_promptのみ）
12. **titleに「○回戦」「続き」等の安易な表現禁止**。具体的な行為・状況を反映した簡潔なタイトルにすること
13. **キャラ名は必ず以下の表記を使え**（表記ブレ厳禁）: {', '.join(char_names) if char_names else 'ヒロイン'}
14. **descriptionに具体的な行為・体位を必ず書け**。「囲まれる」「溺れる」だけの抽象表現は禁止。何をどうされているか書くこと"""

    # 重複禁止の最終警告（user promptの末尾に配置 = モデルが最も注目する位置）
    dedup_warning = ""
    if story_so_far:
        dedup_warning = f"""

## ⚠️⚠️⚠️ 最終チェック（出力前に必ず確認） ⚠️⚠️⚠️

以下の条件を1つでも満たす場合、出力をやり直せ:
- bubblesのtextに前シーンと同じ文言がある → 辞書から別パターンを選び直せ
- onomatopoeiaが前シーンと同じ組み合わせ → 別の効果音に変えろ
- descriptionが前シーンと類似している → 具体的な行為を変えろ
- キャラ名が「{', '.join(char_names) if char_names else 'ヒロイン'}」以外の表記になっている → 修正しろ"""

    prompt = prompt + dedup_warning + "\n\nJSONのみ出力。"

    # intensity 5のみSonnetで高品質に（API節約）
    model = MODELS["sonnet"] if intensity >= 5 else MODELS["haiku"]
    model_name = "Sonnet" if intensity >= 5 else "Haiku"
    
    if callback:
        callback(f"シーン {scene['scene_id']} 生成中 ({model_name}, 重要度{intensity}, {theme_name}, セリフ:{serihu_skill_name})...")
    
    response = _call_api(
        client, model,
        system_with_cache,
        prompt, cost_tracker, 2500, callback
    )
    
    # 重複排除の後処理
    result = parse_json_response(response)
    if isinstance(result, dict) and result.get("sd_prompt"):
        result["sd_prompt"] = deduplicate_sd_tags(result["sd_prompt"])
    return result


def polish_scene(
    client: anthropic.Anthropic,
    context: dict,
    draft: dict,
    char_profiles: list = None,
    cost_tracker: CostTracker = None,
    callback: Optional[Callable] = None
) -> dict:
    # キャラプロファイルをフル活用
    char_guide = ""
    if char_profiles:
        for cp in char_profiles:
            name = cp.get("character_name", "")
            speech = cp.get("speech_pattern", {})
            emotional = cp.get("emotional_speech", {})
            examples = cp.get("dialogue_examples", {})
            erotic = cp.get("erotic_speech_guide", {})
            
            char_guide += f"""
【{name}の口調チェックリスト】
✓ 一人称: {speech.get('first_person', '私')}
✓ 語尾: {', '.join(speech.get('sentence_endings', [])[:6])}
✓ 間投詞: {', '.join(speech.get('fillers', [])[:4])}
✓ 照れた時: {emotional.get('when_embarrassed', '')}
✓ 甘える時: {emotional.get('when_flirty', '')}
✓ 感じてる時: {emotional.get('when_aroused', '')}
✓ 絶頂時: {emotional.get('when_climax', '')}
✓ 喘ぎ声（軽）: {examples.get('moaning_light', 'あっ...んっ...')}
✓ 喘ぎ声（激）: {examples.get('moaning_intense', 'あっあっ...♡')}
✓ エロ度: {erotic.get('shyness_level', 3)}/5（数字が大きいほど恥ずかしがり）
"""

    system_prompt = f"""あなたはFANZA同人CG集の清書担当です。
下書きの吹き出しテキストを「そのキャラが本当に言いそうな」自然で短い表現に磨き上げてください。

{char_guide if char_guide else "（キャラプロファイルなし）"}

## CG集の清書ルール

【吹き出し改善】
1. 長すぎるテキスト→1〜10文字に短縮
2. 説明的→感情的に（「嬉しい気持ちです」→「嬉しい…♡」）
3. 文章→断片に（主語・目的語を削除）
4. 一人称・語尾を徹底チェック

【エロシーン改善】
- 「気持ちいいです」→「きもちぃ…♡」
- 「もっとしてください」→「もっと…♡」
- 「イキそうです」→「イっちゃ…♡」
- 喘ぎ声は途切れ途切れに

【オノマトペ改善】
- 場面に合った効果音か確認
- 数は適切か（intensity 1-2: 0-1個、3: 1-2個、4-5: 2-4個）

【禁止】
❌ 10文字超えの吹き出し
❌ 説明調のテキスト
❌ キャラの一人称・語尾の不一致

Output JSON only."""

    prompt = f"""設定: {json.dumps(context, ensure_ascii=False)}

下書き: {json.dumps(draft, ensure_ascii=False)}

上記の下書きを清書してください：

1. 各吹き出しをキャラの口調に合わせる
2. テキストを1〜10文字に短縮
3. descriptionをより詳細に（100字程度）
4. character_feelingsをより感情的に
5. onomatopoeiaが場面に合っているか確認

## 保持すべきフィールド
- scene_id, title, description, location_detail
- mood, character_feelings
- bubbles (speaker, type, text)
- onomatopoeia
- direction, story_flow
- sd_prompt

同じJSON形式で出力。JSONのみ。"""

    response = _call_api(
        client, MODELS["sonnet"],
        system_prompt,
        prompt, cost_tracker, 2500, callback
    )
    return parse_json_response(response)


# === Skill 3: Script Quality Supervisor ===
def check_quality(
    client: anthropic.Anthropic,
    context: dict,
    scenes: list,
    cost_tracker: CostTracker,
    callback: Optional[Callable] = None
) -> dict:
    skill = load_skill("script_quality_supervisor")
    prompt = f"""設定: {json.dumps(context, ensure_ascii=False)}

シーン一覧: {json.dumps(scenes, ensure_ascii=False)}

以下をチェック:
1. キャラの口調一貫性
2. シーン目標達成
3. 感情の平坦さ
4. ペーシング問題
5. シーン間矛盾

出力形式（JSON）:
{{
    "has_problems": true/false,
    "problems": [
        {{"scene_id": 1, "type": "問題種別", "detail": "詳細"}}
    ],
    "fix_instructions": [
        {{"scene_id": 1, "instruction": "修正指示（最小限）"}}
    ]
}}

問題なければhas_problems: false。JSONのみ出力。"""

    if callback:
        callback("[CHECK]品質チェック中...")

    response = _call_api(
        client, MODELS["haiku"],
        skill if skill else "You check script quality and suggest minimal fixes.",
        prompt, cost_tracker, 2048, callback
    )
    return parse_json_response(response)


def apply_fix(
    client: anthropic.Anthropic,
    scene: dict,
    instruction: str,
    cost_tracker: CostTracker,
    callback: Optional[Callable] = None
) -> dict:
    prompt = f"""シーン: {json.dumps(scene, ensure_ascii=False)}

修正指示: {instruction}

指示に従い、該当箇所のみ修正してください。
全体の再生成は禁止。最小限の変更のみ。

同じJSON形式で出力。JSONのみ。"""

    response = _call_api(
        client, MODELS["haiku"],
        "You apply minimal fixes to scripts. Never regenerate entirely.",
        prompt, cost_tracker, 2048, callback
    )
    return parse_json_response(response)


# === メインパイプライン ===
def generate_pipeline(
    api_key: str,
    concept: str,
    characters: str,
    num_scenes: int,
    theme: str,
    callback: Optional[Callable] = None,
    skip_quality_check: bool = True,
    story_structure: dict = None,
) -> tuple[list, CostTracker]:
    client = anthropic.Anthropic(api_key=api_key)
    log_message("Claude (Anthropic) バックエンドで生成開始")
    cost_tracker = CostTracker()

    jailbreak = load_file(JAILBREAK_FILE)
    sd_guide = load_file(SD_PROMPT_GUIDE_FILE)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # キャラプロファイルを読み込み（部分一致対応）
    char_profiles = []
    characters_lower = characters.lower()
    log_message(f"キャラプロファイル検索開始: {characters}")
    
    for json_file in CHARACTERS_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                profile = json.load(f)
                char_name = profile.get("character_name", "")
                work_title = profile.get("work_title", "")
                if char_name and (
                    char_name in characters or
                    char_name.lower() in characters_lower or
                    any(part in characters for part in char_name.split())
                ):
                    char_profiles.append(profile)
                    log_message(f"キャラプロファイル読込: {char_name} ({work_title})")
                    if callback:
                        callback(f"[FILE]キャラ設定適用: {char_name}（{work_title}）")
        except Exception as e:
            log_message(f"キャラプロファイル読込エラー: {e}")

    # プリセットも検索
    for json_file in PRESET_CHARS_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                profile = json.load(f)
                char_name = profile.get("character_name", "")
                work_title = profile.get("work_title", "")
                existing_names = [cp.get("character_name", "") for cp in char_profiles]
                if char_name and char_name not in existing_names and (
                    char_name in characters or
                    char_name.lower() in characters_lower or
                    any(part in characters for part in char_name.split())
                ):
                    char_profiles.append(profile)
                    log_message(f"プリセットキャラ読込: {char_name} ({work_title})")
                    if callback:
                        callback(f"[PACK]プリセットキャラ適用: {char_name}（{work_title}）")
        except Exception as e:
            log_message(f"プリセット読込エラー: {e}")
    
    if char_profiles:
        char_names = [cp.get("character_name", "") for cp in char_profiles]
        log_message(f"使用キャラ設定: {', '.join(char_names)}")
        if callback:
            callback(f"[OK]{len(char_profiles)}件のキャラ設定を適用")
    else:
        log_message("キャラ設定なし - 汎用設定で生成")
        if callback:
            callback("[WARN]キャラ設定なし（汎用設定で生成）")

    # テーマ情報
    theme_guide = THEME_GUIDES.get(theme, {})
    theme_name = theme_guide.get("name", "指定なし")
    if theme and theme_guide:
        log_message(f"テーマ適用: {theme_name} (arc: {theme_guide.get('story_arc', '')})")
        if callback:
            callback(f"[CHAR]テーマ: {theme_name}")

    # Phase 1: コンテキスト圧縮
    log_message("Phase 1 開始: コンテキスト圧縮")
    if callback:
        callback("🔧 Phase 1: コンテキスト圧縮")

    try:
        if char_profiles:
            context = compact_context_local(concept, characters, theme, char_profiles, callback)
            log_message("コンテキスト圧縮完了（ローカル）")
        else:
            context = compact_context(client, concept, characters, theme, cost_tracker, callback)
            log_message("コンテキスト圧縮完了（API）")
    except Exception as e:
        log_message(f"コンテキスト圧縮エラー: {e}")
        raise

    context_file = CONTEXT_DIR / f"context_{timestamp}.json"
    with open(context_file, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)

    if callback:
        callback("[OK]コンテキスト圧縮完了")

    # Phase 2: ストーリーあらすじ生成（Haiku 1回）
    log_message("Phase 2 開始: ストーリーあらすじ生成")
    if callback:
        callback("🔧 Phase 2: ストーリー原案作成")

    try:
        synopsis = generate_synopsis(client, concept, context, num_scenes, theme, cost_tracker, callback)
        log_message(f"あらすじ生成完了: {len(synopsis)}文字")

        # あらすじをファイルに保存
        synopsis_file = CONTEXT_DIR / f"synopsis_{timestamp}.txt"
        with open(synopsis_file, "w", encoding="utf-8") as f:
            f.write(synopsis)
    except Exception as e:
        log_message(f"あらすじ生成エラー: {e}")
        import traceback
        log_message(traceback.format_exc())
        # フォールバック: コンセプトをあらすじとして使用
        synopsis = concept
        if callback:
            callback(f"[WARN]あらすじ生成失敗、コンセプトで代替")

    if callback:
        callback("[OK]ストーリー原案完成")

    # Phase 3: アウトライン生成（あらすじをシーン分割）
    log_message("Phase 3 開始: アウトライン生成（シーン分割）")
    if callback:
        callback("🔧 Phase 3: シーン分割")

    try:
        outline = generate_outline(client, context, num_scenes, theme, cost_tracker, callback, synopsis=synopsis, story_structure=story_structure)
        log_message(f"アウトライン生成完了: {len(outline)}シーン")
        
        intensity_counts = {}
        for scene in outline:
            i = scene.get("intensity", 3)
            intensity_counts[i] = intensity_counts.get(i, 0) + 1
        log_message(f"intensity分布: {intensity_counts}")
    except Exception as e:
        log_message(f"アウトライン生成エラー: {e}、フォールバック（均等分割）を使用")
        if callback:
            callback(f"[WARN]シーン分割エラー、均等分割で代替中...")
        # フォールバック: ストーリー構成に基づく均等分割
        fb_ss = story_structure or {"prologue": 10, "main": 80, "epilogue": 10}
        fb_pro = fb_ss.get("prologue", 10) / 100
        fb_epi = fb_ss.get("epilogue", 10) / 100
        fb_main_start = fb_pro
        fb_main_end = 1.0 - fb_epi
        outline = []
        for idx in range(1, num_scenes + 1):
            ratio = idx / num_scenes
            if ratio <= fb_pro:
                intensity = 1  # プロローグ
            elif ratio <= fb_main_start + (fb_main_end - fb_main_start) * 0.25:
                intensity = 3  # 前戯
            elif ratio <= fb_main_end:
                intensity = 4 + (1 if ratio > fb_main_start + (fb_main_end - fb_main_start) * 0.7 else 0)
            else:
                intensity = 3  # エピローグ
            outline.append({
                "scene_id": idx,
                "summary": f"シーン{idx}",
                "intensity": min(intensity, 5),
                "location": "室内",
                "time": ""
            })
        log_message(f"フォールバックアウトライン生成: {num_scenes}シーン")

    if callback:
        high_intensity = sum(1 for s in outline if s.get("intensity", 0) >= 5)
        low_intensity = len(outline) - high_intensity
        callback(f"[OK]シーン分割完成: {len(outline)}シーン（Haiku×{low_intensity} + Sonnet×{high_intensity}）")

    # コスト見積もり（あらすじ+アウトライン+シーン生成）
    low_count = sum(1 for s in outline if s.get("intensity", 3) <= 4)
    high_count = sum(1 for s in outline if s.get("intensity", 3) >= 5)
    outline_cost = 2000 / 1_000_000 * 0.25 + 2000 / 1_000_000 * 1.25
    scene_cost = (low_count * 3000 / 1_000_000 * 0.25 + low_count * 2500 / 1_000_000 * 1.25 +
                  high_count * 3000 / 1_000_000 * 3.00 + high_count * 2500 / 1_000_000 * 15.00)
    est_cost = outline_cost * 2 + scene_cost
    if callback:
        callback(f"[COST]推定コスト: ${est_cost:.4f}（API {len(outline)+2}回: あらすじ1+分割1+Haiku×{low_count}+Sonnet×{high_count}）")

    # Phase 4: シーン生成（完全シーケンシャル + ストーリー蓄積）
    results = []
    story_summaries = []

    for i, scene in enumerate(outline):
        intensity = scene.get("intensity", 3)
        model_type = "Sonnet" if intensity >= 5 else "Haiku"

        # story_so_far を構築（直近3シーンの要約）
        story_so_far = ""
        if story_summaries:
            recent = story_summaries[-3:]
            story_so_far = "\n".join(recent)

        try:
            log_message(f"シーン {i+1}/{len(outline)} 生成開始 (intensity={intensity}, {model_type})")
            if callback:
                callback(f"[SCENE]シーン {i+1}/{len(outline)} [{model_type}] 重要度{intensity}")

            draft = generate_scene_draft(
                client, context, scene, jailbreak, sd_guide,
                cost_tracker, theme, char_profiles, callback,
                story_so_far=story_so_far,
                synopsis=synopsis
            )

            draft["intensity"] = intensity
            results.append(draft)

            # 要約を蓄積して次シーンに渡す
            summary = extract_scene_summary(draft)
            story_summaries.append(summary)
            log_message(f"シーン {i+1} 要約蓄積: {summary[:80]}...")

            draft_file = DRAFTS_DIR / f"draft_{timestamp}_scene{i+1}.json"
            with open(draft_file, "w", encoding="utf-8") as f:
                json.dump(draft, f, ensure_ascii=False, indent=2)
            final_file = FINAL_DIR / f"final_{timestamp}_scene{i+1}.json"
            with open(final_file, "w", encoding="utf-8") as f:
                json.dump(draft, f, ensure_ascii=False, indent=2)

            log_message(f"シーン {i+1}/{len(outline)} 完了")
            if callback:
                callback(f"[OK]シーン {i+1}/{len(outline)} 完了")

        except Exception as e:
            err_msg = str(e)
            log_message(f"シーン {i+1} 生成エラー: {err_msg}")

            # リトライ判定（コンテンツ拒否 or JSONパースエラー）
            is_refusal = any(kw in err_msg for kw in ["倫理", "対応することはできません", "cannot", "inappropriate"])
            is_json_error = any(kw in err_msg for kw in ["Invalid JSON", "No JSON", "Empty response", "JSONDecodeError"])

            if is_refusal or is_json_error:
                retry_reason = "コンテンツ拒否" if is_refusal else "JSONパースエラー"
                log_message(f"シーン {i+1} {retry_reason}検出、リトライ")
                if callback:
                    callback(f"[WARN]シーン {i+1} {retry_reason}、リトライ中...")

                # 最大2回リトライ
                retry_success = False
                for retry_n in range(2):
                    try:
                        draft = generate_scene_draft(
                            client, context, scene, jailbreak, sd_guide,
                            cost_tracker, theme, char_profiles, callback,
                            story_so_far=story_so_far,
                            synopsis="" if is_refusal else synopsis
                        )
                        draft["intensity"] = intensity
                        results.append(draft)
                        summary = extract_scene_summary(draft)
                        story_summaries.append(summary)
                        log_message(f"シーン {i+1} リトライ{retry_n+1}回目成功")
                        if callback:
                            callback(f"[OK]シーン {i+1}/{len(outline)} リトライ成功")
                        retry_success = True
                        break
                    except Exception as e2:
                        log_message(f"シーン {i+1} リトライ{retry_n+1}回目失敗: {e2}")

                if retry_success:
                    continue

            import traceback
            log_message(traceback.format_exc())
            if callback:
                callback(f"[ERROR]シーン {i+1} エラー: {err_msg[:50]}")

            error_result = {
                "scene_id": scene.get("scene_id", i + 1),
                "title": f"シーン{i+1}",
                "mood": "エラー",
                "bubbles": [],
                "onomatopoeia": [],
                "direction": f"生成エラー: {err_msg[:100]}",
                "sd_prompt": ""
            }
            results.append(error_result)
            story_summaries.append(f"[シーン{i+1}: エラーにより欠落]")

    # Phase 5: 品質検証 + SDプロンプト最適化（APIコスト不要）
    log_message("Phase 5 開始: 品質検証 + SDプロンプト最適化")
    if callback:
        callback("[CHECK]Phase 5: 品質検証 + SDプロンプト最適化")

    # 5-1: FANZA基準で自動検証
    validation = validate_script(results, theme, char_profiles)
    log_message(f"品質検証完了: {validation['summary']}")
    if callback:
        callback(f"[STAT]{validation['summary']}")

    # シーン別問題をログ
    for sid, issues in validation["scene_issues"].items():
        for issue in issues:
            log_message(f"  シーン{sid}: {issue}")
            if callback:
                callback(f"  [WARN]シーン{sid}: {issue}")

    # 喘ぎ重複
    if validation["repeated_moans"]:
        for text, sids in validation["repeated_moans"].items():
            msg = f"喘ぎ重複「{text}」→ シーン{', '.join(str(s) for s in sids)}"
            log_message(f"  {msg}")
            if callback:
                callback(f"  [WARN]{msg}")

    # オノマトペ連続重複
    for s1, s2 in validation["repeated_onomatopoeia"]:
        msg = f"オノマトペ連続重複: シーン{s1}→{s2}"
        log_message(f"  {msg}")
        if callback:
            callback(f"  [WARN]{msg}")

    # 5-2: SDプロンプト最適化（設定スタイル適用）
    setting_style = _detect_setting_style(concept)
    if setting_style:
        log_message(f"設定スタイル検出: {setting_style.get('prompt_hint', '')[:40]}...")
        if callback:
            callback(f"🏠 設定スタイル適用: {setting_style.get('prompt_hint', '')[:30]}...")
    results = enhance_sd_prompts(results, char_profiles, setting_style=setting_style)
    log_message("SDプロンプト最適化完了")
    if callback:
        callback("[OK]SDプロンプト最適化完了")

    # 5-3: 自動修正（文字数マーカー除去、キャラ名統一、SDタグ整理）
    results = auto_fix_script(results, char_profiles)
    log_message("自動修正完了")
    if callback:
        callback("🔧 自動修正完了")

    # 完了サマリー
    success_count = sum(1 for r in results if r.get("mood") != "エラー")
    log_message(f"パイプライン完了: {success_count}/{len(results)}シーン成功")

    if callback:
        callback(f"[DONE]生成完了: {success_count}シーン成功（品質: {validation['score']}/100）")

    return results, cost_tracker


def export_csv(results: list, output_path: Path):
    fieldnames = [
        "scene_id", "title", "description", "bubble_no", "speaker", "text",
        "onomatopoeia", "sd_prompt",
        "type", "mood", "location_detail", "character_feelings",
        "direction", "story_flow"
    ]

    # utf-8-sig でBOM付きUTF-8（Excel対応）
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for scene in results:
            # キャラ心情を文字列に変換
            feelings = scene.get("character_feelings", {})
            if isinstance(feelings, dict):
                feelings_str = "; ".join([f"{k}: {v}" for k, v in feelings.items()])
            else:
                feelings_str = str(feelings)
            
            # オノマトペを文字列に
            onomatopoeia = scene.get("onomatopoeia", [])
            ono_str = ", ".join(onomatopoeia) if isinstance(onomatopoeia, list) else str(onomatopoeia)
            
            # 新フォーマット: bubbles、旧互換: dialogue
            bubbles = scene.get("bubbles", [])
            if not bubbles:
                bubbles = scene.get("dialogue", [])
            
            if not bubbles:
                # 吹き出しがない場合でもシーン情報を出力
                writer.writerow({
                    "scene_id": scene.get("scene_id", ""),
                    "title": scene.get("title", ""),
                    "description": scene.get("description", ""),
                    "location_detail": scene.get("location_detail", ""),
                    "mood": scene.get("mood", ""),
                    "character_feelings": feelings_str,
                    "bubble_no": 0,
                    "speaker": "",
                    "type": "",
                    "text": "",
                    "onomatopoeia": ono_str,
                    "direction": scene.get("direction", ""),
                    "story_flow": scene.get("story_flow", ""),
                    "sd_prompt": scene.get("sd_prompt", "")
                })
            else:
                for idx, bubble in enumerate(bubbles):
                    writer.writerow({
                        "scene_id": scene.get("scene_id", "") if idx == 0 else "",
                        "title": scene.get("title", "") if idx == 0 else "",
                        "description": scene.get("description", "") if idx == 0 else "",
                        "location_detail": scene.get("location_detail", "") if idx == 0 else "",
                        "mood": scene.get("mood", "") if idx == 0 else "",
                        "character_feelings": feelings_str if idx == 0 else "",
                        "bubble_no": idx + 1,
                        "speaker": bubble.get("speaker", ""),
                        "type": bubble.get("type", bubble.get("emotion", "")),
                        "text": bubble.get("text", bubble.get("line", "")),
                        "onomatopoeia": ono_str if idx == 0 else "",
                        "direction": scene.get("direction", "") if idx == 0 else "",
                        "story_flow": scene.get("story_flow", "") if idx == 0 else "",
                        "sd_prompt": scene.get("sd_prompt", "") if idx == 0 else ""
                    })


def export_excel(results: list, output_path: Path):
    """Excel形式でエクスポート（CG集フォーマット対応）"""
    if not OPENPYXL_AVAILABLE:
        log_message("openpyxl未インストール - Excel出力スキップ")
        return False
    
    wb = Workbook()
    ws = wb.active
    ws.title = "脚本"
    
    # ヘッダー
    headers = [
        "シーンID", "タイトル", "シーン説明", "吹き出しNo", "話者", "テキスト",
        "オノマトペ", "SDプロンプト",
        "種類", "雰囲気", "場所詳細", "キャラ心情",
        "演出", "次への繋がり"
    ]
    
    # ヘッダースタイル
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    # データ
    row = 2
    for scene in results:
        feelings = scene.get("character_feelings", {})
        if isinstance(feelings, dict):
            feelings_str = "\n".join([f"{k}: {v}" for k, v in feelings.items()])
        else:
            feelings_str = str(feelings)
        
        # オノマトペを文字列に
        onomatopoeia = scene.get("onomatopoeia", [])
        ono_str = ", ".join(onomatopoeia) if isinstance(onomatopoeia, list) else str(onomatopoeia)
        
        # 新フォーマット: bubbles、旧互換: dialogue
        bubbles = scene.get("bubbles", [])
        if not bubbles:
            bubbles = scene.get("dialogue", [])
        if not bubbles:
            bubbles = [{}]
        
        for idx, bubble in enumerate(bubbles):
            data = [
                scene.get("scene_id", "") if idx == 0 else "",
                scene.get("title", "") if idx == 0 else "",
                scene.get("description", "") if idx == 0 else "",
                idx + 1 if bubble else "",
                bubble.get("speaker", ""),
                bubble.get("text", bubble.get("line", "")),
                ono_str if idx == 0 else "",
                scene.get("sd_prompt", "") if idx == 0 else "",
                bubble.get("type", bubble.get("emotion", "")),
                scene.get("mood", "") if idx == 0 else "",
                scene.get("location_detail", "") if idx == 0 else "",
                feelings_str if idx == 0 else "",
                scene.get("direction", "") if idx == 0 else "",
                scene.get("story_flow", "") if idx == 0 else ""
            ]
            
            for col, value in enumerate(data, 1):
                cell = ws.cell(row=row, column=col, value=value)
                # 折り返し表示を有効化
                cell.alignment = Alignment(vertical="top", wrap_text=True)
            
            row += 1
    
    # 列幅の設定
    column_widths = {
        1: 8,    # シーンID
        2: 12,   # タイトル
        3: 40,   # シーン説明
        4: 8,    # 吹き出しNo
        5: 10,   # 話者
        6: 20,   # テキスト
        7: 20,   # オノマトペ
        8: 60,   # SDプロンプト
        9: 8,    # 種類
        10: 10,  # 雰囲気
        11: 20,  # 場所詳細
        12: 25,  # キャラ心情
        13: 20,  # 演出
        14: 15   # 次への繋がり
    }
    
    for col, width in column_widths.items():
        ws.column_dimensions[chr(64 + col) if col <= 26 else f"A{chr(64 + col - 26)}"].width = width
    
    # ヘッダー行を固定
    ws.freeze_panes = "A2"
    
    wb.save(output_path)
    log_message(f"Excel出力完了: {output_path}")
    return True


def export_json(results: list, output_path: Path):
    data = {
        "generated_at": datetime.now().isoformat(),
        "scenes": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# === キャラクター自動生成システム ===

CHARACTER_BIBLE_TEMPLATE = {
    "work_title": "",
    "character_name": "",
    "core_traits": [],
    "values": [],
    "fears": [],
    "relationship_style": {
        "toward_love_interest": "",
        "toward_rival": "",
        "toward_friends": ""
    },
    "speech_profile": {
        "first_person": "",
        "second_person_style": "",
        "formality_level": 0,
        "sentence_length": "medium",
        "rhythm": "",
        "typical_tone": "",
        "forbidden_elements": []
    },
    "emotion_model": {
        "baseline_state": "",
        "triggers": [],
        "escalation_pattern": [],
        "deescalation_pattern": []
    },
    "conflict_response_style": "",
    "romantic_response_style": "",
    "originality_guard": {
        "avoid_canonical_lines": True,
        "avoid_known_catchphrases": True
    }
}


def generate_char_id(work_title: str, char_name: str) -> str:
    """キャラIDを生成（英数字のみ）"""
    import re
    import hashlib
    combined = f"{work_title}_{char_name}"
    # 日本語などを含む場合はハッシュ化
    if re.search(r'[^\x00-\x7F]', combined):
        short_hash = hashlib.md5(combined.encode()).hexdigest()[:8]
        return f"char_{short_hash}"
    return re.sub(r'[^a-zA-Z0-9_]', '_', combined.lower())[:32]


def analyze_character(
    client: anthropic.Anthropic,
    work_title: str,
    char_name: str,
    cost_tracker: CostTracker,
    callback: Optional[Callable] = None
) -> dict:
    """キャラクター情報をClaudeの知識から抽出（Sonnetで高品質分析）"""

    if callback:
        callback(f"[CHECK]{char_name}の詳細分析中（Sonnet使用）...")

    system_prompt = """あなたは日本のアニメ・漫画・ゲームキャラクターの口調分析専門家です。
二次創作でキャラクターの「らしさ」を完璧に再現するため、話し方を徹底的に分析します。

【重要ルール】
- 原作セリフの直接引用は禁止
- 「こういうパターンで話す」という抽象的な特徴を記述
- エロシーンでも使える「感情が高ぶった時の話し方」を詳細に
- 日本語として自然な表現を意識"""

    prompt = f"""作品名: {work_title}
キャラクター名: {char_name}

このキャラクターの「話し方」を、二次創作（成人向け含む）で使えるレベルで徹底分析してください。

{{
    "work_title": "{work_title}",
    "character_name": "{char_name}",
    
    "personality_core": {{
        "brief_description": "このキャラを一言で表すと",
        "main_traits": ["性格特性を5個"],
        "hidden_traits": ["表に出さない特性を3個"],
        "weakness": "弱点・苦手なこと",
        "values": ["大切にしていること3個"],
        "fears": ["恐れていること2個"]
    }},
    
    "speech_pattern": {{
        "first_person": "一人称（私/あたし/僕/俺/自分の名前等）",
        "sentence_endings": ["語尾パターンを8個以上。例: 〜だよ, 〜かな, 〜ですわ, 〜じゃん, 〜わよ"],
        "favorite_expressions": ["口癖ではないがよく使う言い回し5個"],
        "fillers": ["間投詞を5個。例: えっと, あのさ, ねえ, うーん"],
        "particles": ["特徴的な助詞の使い方3個"],
        "casual_level": "1-5の数字（1=タメ口, 5=超丁寧）",
        "speech_speed": "速い/普通/ゆっくり",
        "sentence_length": "短文多め/普通/長文多め",
        "voice_quality": "声の特徴（高い/低い/ハスキー等）"
    }},
    
    "emotional_speech": {{
        "when_happy": "嬉しい時の話し方（具体的に）",
        "when_embarrassed": "照れた時・恥ずかしい時の話し方",
        "when_angry": "怒った時の話し方",
        "when_sad": "悲しい時の話し方",
        "when_confused": "困惑・動揺した時の話し方",
        "when_flirty": "甘える・誘惑する時の話し方（エロシーン用に詳細に！）",
        "when_aroused": "感じている時の話し方（喘ぎ声のパターン、言葉の途切れ方）",
        "when_climax": "絶頂時の話し方・反応"
    }},
    
    "dialogue_examples": {{
        "greeting": "挨拶の仕方の例",
        "agreement": "同意する時の例",
        "refusal": "断る時の例",
        "surprise": "驚いた時の例",
        "affection": "好意を示す時の例",
        "teasing": "からかう・甘える時の例",
        "moaning_light": "軽い喘ぎ声の例（あっ、んっ等の組み合わせ）",
        "moaning_intense": "激しい喘ぎ声の例"
    }},
    
    "relationship_speech": {{
        "to_lover": "恋人・好きな人への話し方（詳細に）",
        "to_friends": "友人への話し方",
        "to_strangers": "初対面の人への話し方",
        "to_rivals": "ライバル・敵対者への話し方"
    }},
    
    "erotic_speech_guide": {{
        "shyness_level": "1-5（1=大胆, 5=超恥ずかしがり）",
        "verbal_during_sex": "行為中によく言いそうなフレーズパターン3個",
        "orgasm_expression": "絶頂時の表現パターン",
        "pillow_talk": "事後の甘い会話パターン"
    }},
    
    "avoid_patterns": ["このキャラが絶対に言わない表現パターン5個"],
    
    "physical_description": {{
        "hair": "髪型・髪色（詳細に）",
        "eyes": "目の色・特徴",
        "body": "体型（スレンダー/グラマー/ロリ体型等）",
        "chest": "胸のサイズ感",
        "clothing": "よく着る服装",
        "notable": ["その他の外見特徴2個"]
    }},
    
    "danbooru_tags": ["SDプロンプト用のdanbooruタグ20個（キャラ名タグ、髪、目、体型、服装等）"],
    
    "originality_guard": {{
        "avoid_canonical_lines": true,
        "avoid_known_catchphrases": true,
        "known_catchphrases": ["避けるべき有名な口癖があれば記載"]
    }}
}}

【重要】
- speech_patternとemotional_speechは特に詳細に
- erotic_speech_guideは成人向け創作で使うため必須
- danbooru_tagsは必ず20個
- JSONのみ出力"""

    # キャラ分析はSonnetで高品質に
    response = _call_api(
        client, MODELS["sonnet"],
        system_prompt,
        prompt, cost_tracker, 4096, callback
    )

    return parse_json_response(response)


def generate_character_skill(char_id: str, bible: dict) -> str:
    """キャラクター専用のSkillファイルを生成（要件定義準拠）"""
    char_name = bible.get("character_name", char_id)
    work_title = bible.get("work_title", "Unknown")
    
    personality = bible.get("personality_core", {})
    speech = bible.get("speech_pattern", {})
    emotional = bible.get("emotional_speech", {})
    examples = bible.get("dialogue_examples", {})
    relationship = bible.get("relationship_speech", {})
    erotic = bible.get("erotic_speech_guide", {})
    avoid = bible.get("avoid_patterns", [])
    physical = bible.get("physical_description", {})
    tags = bible.get("danbooru_tags", [])
    
    # 文末表現リスト
    endings = speech.get("sentence_endings", [])
    endings_str = ", ".join(endings) if endings else "〜よ, 〜ね, 〜かな"
    
    # フィラー
    fillers = speech.get("fillers", [])
    fillers_str = ", ".join(fillers) if fillers else "えっと, あのね"
    
    # 避けるべきパターン
    avoid_str = "\n".join([f"- {a}" for a in avoid]) if avoid else "- 特になし"

    skill_content = f"""---
name: character_voice_{char_id}
description: Apply abstract character model for {char_name} from {work_title}
commands:
  - /voice-{char_id}
---

# {char_name} 完全口調ガイド

## Role
{char_name}（{work_title}）のセリフを、キャラクターらしい自然な日本語会話として生成する。

## Hard Rules
- Never reproduce canonical lines（原作セリフの再現禁止）
- Never copy known catchphrases（決め台詞のコピー禁止）
- Use structural traits only（構造的特徴のみ使用）
- Maintain character voice consistency（キャラの声を一貫させる）

## Character Profile

### 基本情報
- **作品**: {work_title}
- **名前**: {char_name}
- **性格**: {personality.get('brief_description', '')}
- **特性**: {', '.join(personality.get('main_traits', []))}
- **隠れた面**: {', '.join(personality.get('hidden_traits', []))}

### 話し方の基本

| 項目 | 設定 |
|------|------|
| 一人称 | {speech.get('first_person', '私')} |
| 語尾 | {endings_str} |
| 間投詞 | {fillers_str} |
| カジュアル度 | {speech.get('casual_level', 3)}/5 |
| 話すテンポ | {speech.get('speech_speed', '普通')} |
| 文の長さ | {speech.get('sentence_length', '普通')} |

### 感情別の話し方

#### 日常シーン
- **嬉しい時**: {emotional.get('when_happy', '')}
- **照れた時**: {emotional.get('when_embarrassed', '')}
- **怒った時**: {emotional.get('when_angry', '')}
- **困惑時**: {emotional.get('when_confused', '')}

#### エロシーン（成人向け）
- **甘える時**: {emotional.get('when_flirty', '')}
- **感じてる時**: {emotional.get('when_aroused', '')}
- **絶頂時**: {emotional.get('when_climax', '')}
- **恥ずかしさ**: {erotic.get('shyness_level', 3)}/5

### セリフ例（参考パターン）
- 挨拶: {examples.get('greeting', '')}
- 同意: {examples.get('agreement', '')}
- 驚き: {examples.get('surprise', '')}
- 好意: {examples.get('affection', '')}
- 軽い喘ぎ: {examples.get('moaning_light', 'あっ...んっ...')}
- 激しい喘ぎ: {examples.get('moaning_intense', 'あっあっ...♡')}

### 関係性別の話し方
- **恋人へ**: {relationship.get('to_lover', '')}
- **友人へ**: {relationship.get('to_friends', '')}

## Forbidden Patterns（禁止表現）
{avoid_str}

## Procedure
1. Load ./characters/{char_id}.json
2. Check speaker's emotional state
3. Apply speech_pattern (first_person, endings)
4. Apply emotional_speech based on scene intensity
5. Ensure originality (no canonical lines)
6. Output natural Japanese dialogue

## SD Prompt Tags
```
{', '.join(tags)}
```

## Physical Description
- 髪: {physical.get('hair', '')}
- 目: {physical.get('eyes', '')}
- 体型: {physical.get('body', '')}
- 服装: {physical.get('clothing', '')}
"""
    return skill_content


def build_character(
    api_key: str,
    work_title: str,
    char_name: str,
    force_refresh: bool = False,
    callback: Optional[Callable] = None,
) -> tuple[dict, str, CostTracker]:
    """キャラクター生成パイプライン"""
    client = anthropic.Anthropic(api_key=api_key)
    cost_tracker = CostTracker()

    char_id = generate_char_id(work_title, char_name)
    bible_path = CHARACTERS_DIR / f"{char_id}.json"
    skill_path = CHAR_SKILLS_DIR / f"{char_id}.skill.md"

    # プリセットチェック（API不要）
    preset_path = PRESET_CHARS_DIR / f"{char_id}.json"
    if preset_path.exists() and not force_refresh:
        if callback:
            callback(f"[PACK]プリセットキャラを使用: {char_name}")
        bible, _ = load_preset_character(char_id, callback)
        return bible, char_id, cost_tracker

    # キャッシュチェック
    if bible_path.exists() and not force_refresh:
        if callback:
            callback(f"[FILE]既存のキャラデータを使用: {char_id}")
        with open(bible_path, "r", encoding="utf-8") as f:
            bible = json.load(f)
        return bible, char_id, cost_tracker

    if callback:
        callback(f"[START]キャラクター生成開始: {char_name}")

    # Step 1: キャラクター分析
    if callback:
        callback("[STAT]Step 1/3: キャラクター分析")

    bible = analyze_character(client, work_title, char_name, cost_tracker, callback)

    # originality_guardを追加
    bible["originality_guard"] = {
        "avoid_canonical_lines": True,
        "avoid_known_catchphrases": True
    }

    # Step 2: キャラバイブル保存
    if callback:
        callback("[SAVE]Step 2/3: キャラバイブル保存")

    with open(bible_path, "w", encoding="utf-8") as f:
        json.dump(bible, f, ensure_ascii=False, indent=2)

    log_message(f"キャラバイブル保存: {bible_path}")

    # Step 3: Skill生成
    if callback:
        callback("[INFO] Step 3/3: Skill生成")

    skill_content = generate_character_skill(char_id, bible)

    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(skill_content)

    log_message(f"Skill保存: {skill_path}")

    if callback:
        callback(f"[OK]キャラクター生成完了: {char_id}")

    return bible, char_id, cost_tracker


def get_existing_characters() -> list[dict]:
    """既存のキャラクター一覧を取得"""
    characters = []
    for json_file in CHARACTERS_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                characters.append({
                    "char_id": json_file.stem,
                    "name": data.get("character_name", json_file.stem),
                    "work": data.get("work_title", "Unknown")
                })
        except Exception:
            pass
    return characters


def get_preset_characters() -> list[dict]:
    """プリセットキャラクター一覧を取得"""
    if not PRESET_INDEX_FILE.exists():
        return []
    try:
        with open(PRESET_INDEX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("characters", [])
    except Exception:
        return []


def load_preset_character(char_id: str, callback: Optional[Callable] = None) -> tuple[dict, str]:
    """プリセットキャラをcharactersにコピーしてskillも生成（API不要）"""
    preset_path = PRESET_CHARS_DIR / f"{char_id}.json"
    bible_path = CHARACTERS_DIR / f"{char_id}.json"
    skill_path = CHAR_SKILLS_DIR / f"{char_id}.skill.md"

    if callback:
        callback(f"[FILE]プリセット読み込み中: {char_id}")

    with open(preset_path, "r", encoding="utf-8") as f:
        bible = json.load(f)

    # charactersディレクトリにコピー
    with open(bible_path, "w", encoding="utf-8") as f:
        json.dump(bible, f, ensure_ascii=False, indent=2)

    # Skill生成
    skill_content = generate_character_skill(char_id, bible)
    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(skill_content)

    if callback:
        callback(f"[OK]プリセット読み込み完了: {bible.get('character_name', char_id)}")

    return bible, char_id


# === Material Design GUI ===
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class MaterialCard(ctk.CTkFrame):
    """
    Material Design 3 Card Component
    
    Variants:
    - elevated: Default, subtle shadow effect via background
    - filled: Higher surface tone, no border
    - outlined: Transparent with outline border
    """
    def __init__(
        self, 
        master, 
        title: str = "", 
        collapsible: bool = False, 
        start_collapsed: bool = False,
        variant: str = "elevated",  # elevated, filled, outlined
        **kwargs
    ):
        # M3 Card styling based on variant
        if variant == "filled":
            bg_color = MaterialColors.SURFACE_CONTAINER_HIGHEST
            border_width = 0
            border_color = None
        elif variant == "outlined":
            bg_color = MaterialColors.SURFACE
            border_width = 1
            border_color = MaterialColors.OUTLINE_VARIANT
        else:  # elevated (default)
            bg_color = MaterialColors.SURFACE_CONTAINER_LOW
            border_width = 0
            border_color = None
        
        super().__init__(
            master,
            fg_color=bg_color,
            corner_radius=12,  # M3: 12dp for medium
            border_width=border_width,
            border_color=border_color,
            **kwargs
        )
        
        self.collapsible = collapsible
        self.is_collapsed = False
        self.variant = variant
        
        if title:
            # Header with proper M3 typography
            header_frame = ctk.CTkFrame(self, fg_color="transparent")
            header_frame.pack(fill="x", padx=20, pady=(16, 12))
            
            self.title_label = ctk.CTkLabel(
                header_frame,
                text=title,
                font=ctk.CTkFont(family=FONT_JP, size=16, weight="bold"),  # Title Medium
                text_color=MaterialColors.ON_SURFACE
            )
            self.title_label.pack(side="left")
            
            if collapsible:
                self.collapse_btn = ctk.CTkButton(
                    header_frame,
                    text="",
                    width=40,
                    height=40,
                    fg_color="transparent",
                    hover_color=MaterialColors.SURFACE_CONTAINER_HIGH,
                    text_color=MaterialColors.ON_SURFACE_VARIANT,
                    font=ctk.CTkFont(size=14),
                    corner_radius=20,  # Fully rounded for icon button
                    command=self.toggle_collapse
                )
                self.collapse_btn.pack(side="right")
                self._update_collapse_icon()
                # ヘッダー全体をクリック可能に
                header_frame.bind("<Button-1>", lambda e: self.toggle_collapse())
                self.title_label.bind("<Button-1>", lambda e: self.toggle_collapse())
                header_frame.configure(cursor="hand2")
                self.title_label.configure(cursor="hand2")

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        if collapsible and start_collapsed:
            self.is_collapsed = True
            self._update_collapse_icon()
        else:
            self.content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    
    def _update_collapse_icon(self):
        self.collapse_btn.configure(
            text=Icons.CHEVRON_UP if not self.is_collapsed else Icons.CHEVRON_DOWN,
            font=ctk.CTkFont(family=FONT_ICON, size=12)
        )
    
    def toggle_collapse(self):
        if self.is_collapsed:
            self.content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        else:
            self.content_frame.pack_forget()
        self.is_collapsed = not self.is_collapsed
        self._update_collapse_icon()


class MaterialButton(ctk.CTkButton):
    """
    Material Design 3 Button Component
    
    Variants:
    - filled: Primary container color (default)
    - filled_tonal: Secondary container color
    - outlined: Transparent with outline
    - text: Text only, no background
    - elevated: Surface with shadow effect
    
    Sizes:
    - small: 32dp height
    - medium: 40dp height (default)
    - large: 56dp height
    """
    def __init__(
        self, 
        master, 
        variant: str = "filled", 
        size: str = "medium", 
        **kwargs
    ):
        # M3 Button sizes (height, font_size, corner_radius, horizontal_padding)
        sizes = {
            "small": {"height": 32, "font_size": 12, "corner": 16, "padx": 12},
            "medium": {"height": 40, "font_size": 14, "corner": 20, "padx": 24},
            "large": {"height": 56, "font_size": 14, "corner": 28, "padx": 24},
            "xlarge": {"height": 64, "font_size": 16, "corner": 28, "padx": 32}
        }
        s = sizes.get(size, sizes["medium"])
        
        # M3 Button variants with proper color tokens
        variants = {
            "filled": {
                "fg_color": MaterialColors.PRIMARY,
                "hover_color": "#7058B8",  # Slightly lighter on hover
                "text_color": MaterialColors.ON_PRIMARY,
                "border_width": 0,
            },
            "filled_tonal": {
                "fg_color": MaterialColors.SECONDARY_CONTAINER,
                "hover_color": MaterialColors.SURFACE_CONTAINER_HIGHEST,
                "text_color": MaterialColors.ON_SECONDARY_CONTAINER,
                "border_width": 0,
            },
            "outlined": {
                "fg_color": "transparent",
                "hover_color": MaterialColors.SURFACE_CONTAINER,
                "text_color": MaterialColors.PRIMARY,
                "border_width": 1,
                "border_color": MaterialColors.OUTLINE,
            },
            "text": {
                "fg_color": "transparent",
                "hover_color": MaterialColors.SURFACE_CONTAINER,
                "text_color": MaterialColors.PRIMARY,
                "border_width": 0,
            },
            "elevated": {
                "fg_color": MaterialColors.SURFACE_CONTAINER_LOW,
                "hover_color": MaterialColors.SURFACE_CONTAINER,
                "text_color": MaterialColors.PRIMARY,
                "border_width": 0,
            },
            # Extended variants for app-specific use
            "accent": {
                "fg_color": MaterialColors.TERTIARY,
                "hover_color": MaterialColors.ACCENT_DARK,
                "text_color": MaterialColors.ON_PRIMARY,
                "border_width": 0,
            },
            "danger": {
                "fg_color": MaterialColors.ERROR,
                "hover_color": "#9C1F19",
                "text_color": MaterialColors.ON_ERROR,
                "border_width": 0,
            },
            "success": {
                "fg_color": MaterialColors.SUCCESS,
                "hover_color": "#145426",
                "text_color": "#FFFFFF",
                "border_width": 0,
            },
        }
        
        v = variants.get(variant, variants["filled"])
        
        super().__init__(
            master,
            fg_color=v["fg_color"],
            hover_color=v["hover_color"],
            text_color=v["text_color"],
            border_width=v.get("border_width", 0),
            border_color=v.get("border_color"),
            corner_radius=s["corner"],
            height=s["height"],
            font=ctk.CTkFont(family=FONT_JP, size=s["font_size"], weight="bold"),
            **kwargs
        )


class MaterialTextField(ctk.CTkFrame):
    """
    Material Design 3 Text Field
    
    Variants:
    - filled: Default M3 text field with container
    - outlined: Border-style text field
    """
    def __init__(
        self, 
        master, 
        label: str, 
        placeholder: str = "", 
        show: str = "", 
        height: int = 56,  # M3 default height
        multiline: bool = False,
        variant: str = "filled",  # filled, outlined
        supporting_text: str = "",
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.variant = variant
        
        # Label (Body Small)
        self.label = ctk.CTkLabel(
            self,
            text=label,
            font=ctk.CTkFont(family=FONT_JP, size=14),
            text_color=MaterialColors.ON_SURFACE_VARIANT
        )
        self.label.pack(anchor="w", pady=(0, 4))

        # Input field styling based on variant
        if variant == "outlined":
            fg_color = "transparent"
            border_width = 1
            border_color = MaterialColors.OUTLINE
            corner_radius = 4
        else:  # filled
            fg_color = MaterialColors.SURFACE_CONTAINER_HIGHEST
            border_width = 0
            border_color = None
            corner_radius = 4  # M3: 4dp top corners only, but CTk doesn't support asymmetric

        if multiline:
            self.entry = ctk.CTkTextbox(
                self,
                height=height,
                fg_color=fg_color,
                text_color=MaterialColors.ON_SURFACE,
                font=ctk.CTkFont(family=FONT_JP, size=16),
                corner_radius=corner_radius,
                border_width=border_width,
                border_color=border_color
            )
        else:
            self.entry = ctk.CTkEntry(
                self,
                height=height,
                placeholder_text=placeholder,
                placeholder_text_color=MaterialColors.ON_SURFACE_VARIANT,
                show=show,
                fg_color=fg_color,
                text_color=MaterialColors.ON_SURFACE,
                font=ctk.CTkFont(family=FONT_JP, size=16),
                corner_radius=corner_radius,
                border_width=border_width,
                border_color=border_color
            )
        self.entry.pack(fill="x")
        
        # Supporting text (Body Small)
        if supporting_text:
            self.supporting = ctk.CTkLabel(
                self,
                text=supporting_text,
                font=ctk.CTkFont(family=FONT_JP, size=14),
                text_color=MaterialColors.ON_SURFACE_VARIANT
            )
            self.supporting.pack(anchor="w", pady=(4, 0))

    def get(self):
        if isinstance(self.entry, ctk.CTkTextbox):
            return self.entry.get("1.0", "end-1c")
        return self.entry.get()

    def set(self, value: str):
        if isinstance(self.entry, ctk.CTkTextbox):
            self.entry.delete("1.0", "end")
            self.entry.insert("1.0", value)
        else:
            self.entry.delete(0, "end")
            self.entry.insert(0, value)
    
    def set_error(self, message: str = ""):
        """Set error state with optional message"""
        if message:
            self.entry.configure(border_color=MaterialColors.ERROR)
            self.label.configure(text_color=MaterialColors.ERROR)
        else:
            border = MaterialColors.OUTLINE if self.variant == "outlined" else None
            self.entry.configure(border_color=border)
            self.label.configure(text_color=MaterialColors.ON_SURFACE_VARIANT)


class MaterialFAB(ctk.CTkButton):
    """
    Material Design 3 Floating Action Button

    Sizes:
    - small: 40dp (for compact layouts)
    - regular: 56dp (default)
    - large: 96dp (for prominent actions)

    Variants:
    - primary: Primary container (default)
    - secondary: Secondary container
    - tertiary: Tertiary container
    - surface: Surface container
    """
    def __init__(
        self,
        master,
        icon: str = "+",
        size: str = "regular",
        variant: str = "primary",
        **kwargs
    ):
        # M3 FAB sizes
        sizes = {
            "small": {"size": 40, "icon_size": 24, "corner": 12},
            "regular": {"size": 56, "icon_size": 24, "corner": 16},
            "large": {"size": 96, "icon_size": 36, "corner": 28}
        }
        s = sizes.get(size, sizes["regular"])

        # M3 FAB color variants
        variants = {
            "primary": {
                "fg": MaterialColors.PRIMARY_CONTAINER,
                "text": MaterialColors.ON_PRIMARY_CONTAINER,
                "hover": MaterialColors.SURFACE_CONTAINER_HIGHEST
            },
            "secondary": {
                "fg": MaterialColors.SECONDARY_CONTAINER,
                "text": MaterialColors.ON_SECONDARY_CONTAINER,
                "hover": MaterialColors.SURFACE_CONTAINER_HIGHEST
            },
            "tertiary": {
                "fg": MaterialColors.TERTIARY_CONTAINER,
                "text": MaterialColors.ON_SURFACE,
                "hover": MaterialColors.SURFACE_CONTAINER_HIGHEST
            },
            "surface": {
                "fg": MaterialColors.SURFACE_CONTAINER_HIGH,
                "text": MaterialColors.PRIMARY,
                "hover": MaterialColors.SURFACE_CONTAINER_HIGHEST
            }
        }
        v = variants.get(variant, variants["primary"])

        super().__init__(
            master,
            text=icon,
            width=s["size"],
            height=s["size"],
            corner_radius=s["corner"],
            fg_color=v["fg"],
            hover_color=v["hover"],
            text_color=v["text"],
            font=ctk.CTkFont(size=s["icon_size"], weight="bold"),
            **kwargs
        )


class MaterialChip(ctk.CTkButton):
    """
    Material Design 3 Chip

    Types:
    - assist: For smart suggestions
    - filter: For filtering content (toggleable)
    - input: For user input (with close button)
    - suggestion: For dynamic suggestions
    """
    def __init__(
        self,
        master,
        text: str,
        selected: bool = False,
        chip_type: str = "filter",
        **kwargs
    ):
        self.selected = selected
        self.chip_type = chip_type

        if selected:
            fg_color = MaterialColors.SECONDARY_CONTAINER
            text_color = MaterialColors.ON_SECONDARY_CONTAINER
            border_width = 0
        else:
            fg_color = "transparent"
            text_color = MaterialColors.ON_SURFACE_VARIANT
            border_width = 1

        super().__init__(
            master,
            text=text,
            height=32,  # M3: 32dp height
            corner_radius=8,  # M3: 8dp corners
            fg_color=fg_color,
            hover_color=MaterialColors.SURFACE_CONTAINER,
            text_color=text_color,
            border_width=border_width,
            border_color=MaterialColors.OUTLINE,
            font=ctk.CTkFont(family=FONT_JP, size=13),
            **kwargs
        )

    def toggle(self):
        self.selected = not self.selected
        if self.selected:
            self.configure(
                fg_color=MaterialColors.SECONDARY_CONTAINER,
                text_color=MaterialColors.ON_SECONDARY_CONTAINER,
                border_width=0
            )
        else:
            self.configure(
                fg_color="transparent",
                text_color=MaterialColors.ON_SURFACE_VARIANT,
                border_width=1
            )


class Snackbar(ctk.CTkFrame):
    """
    Material Design 3 Snackbar
    
    Single-line notifications with optional action button.
    Appears at bottom of screen with proper M3 styling.
    """
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=MaterialColors.INVERSE_SURFACE,
            corner_radius=4,  # M3: 4dp corners
            height=48,        # M3: 48dp single-line
            **kwargs
        )

        # Message label (Body Medium)
        self.message_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family=FONT_JP, size=16),
            text_color=MaterialColors.INVERSE_ON_SURFACE
        )
        self.message_label.pack(side="left", padx=16, pady=12)
        
        # Optional action button
        self.action_btn = ctk.CTkButton(
            self,
            text="",
            font=ctk.CTkFont(family=FONT_JP, size=16, weight="bold"),
            fg_color="transparent",
            hover_color=MaterialColors.INVERSE_SURFACE,
            text_color=MaterialColors.INVERSE_PRIMARY,
            corner_radius=4,
            height=36,
            width=0  # Auto-width
        )
        self.action_btn.pack(side="right", padx=(0, 8))
        self.action_btn.pack_forget()  # Hidden by default

        self.place_forget()

    def show(
        self, 
        message: str, 
        duration: int = 4000,  # M3 recommends 4-10 seconds
        type: str = "info",
        action: str = "",
        action_command = None
    ):
        """
        Show snackbar with message.
        
        Args:
            message: Text to display
            duration: Auto-hide time in ms (0 = no auto-hide)
            type: info, success, error, warning
            action: Optional action button text
            action_command: Optional callback for action button
        """
        # M3 uses inverse surface for snackbar, but we can tint for status
        colors = {
            "info": MaterialColors.INVERSE_SURFACE,
            "success": "#2E7D32",    # Green-800
            "error": "#C62828",       # Red-800
            "warning": "#F57C00"      # Orange-800
        }
        
        self.configure(fg_color=colors.get(type, MaterialColors.INVERSE_SURFACE))
        self.message_label.configure(
            text=message,
            text_color=MaterialColors.INVERSE_ON_SURFACE
        )
        
        # Action button
        if action and action_command:
            self.action_btn.configure(text=action, command=action_command)
            self.action_btn.pack(side="right", padx=(0, 8))
        else:
            self.action_btn.pack_forget()
        
        # Position at bottom with proper margin
        self.place(relx=0.5, rely=0.95, anchor="center")
        self.lift()
        
        if duration > 0:
            self.after(duration, self.hide)

    def hide(self):
        self.place_forget()


class MaterialTooltip:
    """M3-style tooltip — hover で表示、離脱で非表示"""

    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tw = None
        self._after_id = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")

    def _on_enter(self, event=None):
        self._after_id = self.widget.after(self.delay, self._show)

    def _on_leave(self, event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        self._hide()

    def _show(self):
        if self._tw:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tw = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        frame = ctk.CTkFrame(
            tw, fg_color=MaterialColors.INVERSE_SURFACE, corner_radius=4
        )
        frame.pack()
        ctk.CTkLabel(
            frame, text=self.text,
            font=ctk.CTkFont(family=FONT_JP, size=12),
            text_color=MaterialColors.INVERSE_ON_SURFACE,
        ).pack(padx=8, pady=4)

    def _hide(self):
        if self._tw:
            self._tw.destroy()
            self._tw = None


def add_tooltip(widget, text, delay=500):
    """ウィジェットに M3 Tooltip を追加"""
    return MaterialTooltip(widget, text, delay)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Daihon Rakku")
        self.geometry("820x950")
        self.minsize(720, 800)
        
        # M3 Surface background
        self.configure(fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST)
        
        self.config_data = load_config()
        self.is_generating = False
        self.stop_requested = False
        self.work_type_var = ctk.StringVar(value="二次創作")

        self.create_widgets()
        self.load_saved_config()

        # ウィンドウ閉じ保護
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # ショートカットキー
        self.bind("<Control-Return>", lambda e: self.start_generation())
        self.bind("<Escape>", lambda e: self.stop_generation() if self.is_generating else None)

    def create_widgets(self):
        # ══════════════════════════════════════════════════════════════
        # HEADER
        # ══════════════════════════════════════════════════════════════
        header = ctk.CTkFrame(self, height=56, fg_color=MaterialColors.SURFACE, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="both", expand=True, padx=24, pady=12)

        icon_text_label(
            header_inner, Icons.FILM, "Daihon Rakku",
            icon_size=16, text_size=20, text_color=MaterialColors.PRIMARY
        ).pack(side="left")

        ctk.CTkLabel(
            header_inner, text="v1.7.0",
            font=ctk.CTkFont(size=12), text_color=MaterialColors.ON_SURFACE_VARIANT,
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=4, padx=8, pady=4
        ).pack(side="left", padx=(12, 0))

        ctk.CTkLabel(
            header_inner, text="FANZA同人CG集 脚本生成",
            font=ctk.CTkFont(size=13), text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="right")

        # ══════════════════════════════════════════════════════════════
        # MAIN CONTENT
        # ══════════════════════════════════════════════════════════════
        self.main_container = ctk.CTkScrollableFrame(
            self, fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST,
            scrollbar_button_color=MaterialColors.OUTLINE_VARIANT
        )
        self.main_container.pack(fill="both", expand=True)

        content = ctk.CTkFrame(self.main_container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=20)

        # ══════════════════════════════════════════════════════════════
        # 1. API設定
        # ══════════════════════════════════════════════════════════════
        api_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=12)
        api_card.pack(fill="x", pady=(0, 16))

        icon_text_label(
            api_card, Icons.LOCK, "API設定",
            icon_size=12, text_size=14
        ).pack(anchor="w", padx=20, pady=(12, 8))
        ctk.CTkFrame(api_card, fg_color=MaterialColors.OUTLINE_VARIANT, height=1, corner_radius=0).pack(fill="x", padx=20, pady=(0, 8))

        # APIキー
        self.api_field = ctk.CTkEntry(
            api_card, height=42, placeholder_text="Anthropic API Key (sk-ant-...)", show="*",
            font=ctk.CTkFont(size=15),
            fg_color=MaterialColors.SURFACE_CONTAINER, text_color=MaterialColors.ON_SURFACE,
            corner_radius=6, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT
        )
        self.api_field.pack(fill="x", padx=20, pady=(0, 12))

        # ══════════════════════════════════════════════════════════════
        # 2. プロファイル管理（キャラ生成より上に配置）
        # ══════════════════════════════════════════════════════════════
        profile_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=12)
        profile_card.pack(fill="x", pady=(0, 16))

        icon_text_label(
            profile_card, Icons.FOLDER, "プロファイル管理",
            icon_size=12, text_size=14
        ).pack(anchor="w", padx=20, pady=(12, 8))
        ctk.CTkFrame(profile_card, fg_color=MaterialColors.OUTLINE_VARIANT, height=1, corner_radius=0).pack(fill="x", padx=20, pady=(0, 8))

        profile_row = ctk.CTkFrame(profile_card, fg_color="transparent")
        profile_row.pack(fill="x", padx=20, pady=(0, 12))

        self.profile_combo = ctk.CTkOptionMenu(
            profile_row, values=["（新規）"] + get_profile_list(), height=36, width=150,
            font=ctk.CTkFont(size=14),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6,
            button_color=MaterialColors.PRIMARY,
            text_color=MaterialColors.ON_SURFACE,
            dropdown_text_color=MaterialColors.ON_SURFACE,
            dropdown_fg_color=MaterialColors.SURFACE,
            command=self.on_profile_selected
        )
        self.profile_combo.pack(side="left", padx=(0, 8))
        self.profile_combo.set("（新規）")

        self.profile_name_entry = ctk.CTkEntry(
            profile_row, height=36, width=120, placeholder_text="プロファイル名",
            font=ctk.CTkFont(size=14),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6,
            text_color=MaterialColors.ON_SURFACE,
            border_width=1, border_color=MaterialColors.OUTLINE_VARIANT
        )
        self.profile_name_entry.pack(side="left", padx=(0, 8))

        MaterialButton(
            profile_row, text="保存", variant="filled", size="small",
            width=56, command=self.save_current_profile
        ).pack(side="left", padx=(0, 4))
        MaterialButton(
            profile_row, text="読込", variant="filled_tonal", size="small",
            width=56, command=self.load_selected_profile
        ).pack(side="left", padx=(0, 4))
        MaterialButton(
            profile_row, text="複製", variant="outlined", size="small",
            width=48, command=self.copy_selected_profile
        ).pack(side="left", padx=(0, 4))
        MaterialButton(
            profile_row, text="削除", variant="danger", size="small",
            width=48, command=self.delete_selected_profile
        ).pack(side="left")

        # ══════════════════════════════════════════════════════════════
        # 3. キャラクター設定
        # ══════════════════════════════════════════════════════════════
        char_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=12)
        char_card.pack(fill="x", pady=(0, 16))

        icon_text_label(
            char_card, Icons.USER, "キャラクター設定",
            icon_size=12, text_size=14
        ).pack(anchor="w", padx=20, pady=(12, 8))
        ctk.CTkFrame(char_card, fg_color=MaterialColors.OUTLINE_VARIANT, height=1, corner_radius=0).pack(fill="x", padx=20, pady=(0, 8))

        # --- 作品タイプ ラジオボタン ---
        type_row = ctk.CTkFrame(char_card, fg_color="transparent")
        type_row.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkRadioButton(
            type_row, text="二次創作（プリセットキャラ）",
            variable=self.work_type_var, value="二次創作",
            font=ctk.CTkFont(size=14), text_color=MaterialColors.ON_SURFACE,
            fg_color=MaterialColors.PRIMARY, border_color=MaterialColors.OUTLINE,
            hover_color=MaterialColors.PRIMARY_CONTAINER,
            command=self._on_work_type_changed
        ).pack(side="left", padx=(0, 16))

        ctk.CTkRadioButton(
            type_row, text="オリジナル（カスタム作成）",
            variable=self.work_type_var, value="オリジナル",
            font=ctk.CTkFont(size=14), text_color=MaterialColors.ON_SURFACE,
            fg_color=MaterialColors.PRIMARY, border_color=MaterialColors.OUTLINE,
            hover_color=MaterialColors.PRIMARY_CONTAINER,
            command=self._on_work_type_changed
        ).pack(side="left")

        # --- プリセットコンテナ（二次創作時のみ表示） ---
        self._preset_container = ctk.CTkFrame(char_card, fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST, corner_radius=8)

        # --- カスタムコンテナ（オリジナル時のみ表示） ---
        self._custom_container = ctk.CTkFrame(char_card, fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST, corner_radius=8)

        # --- 共通: 使用キャラ選択（常時表示、切替の基準点） ---
        self._char_select_row = ctk.CTkFrame(char_card, fg_color="transparent")
        self._char_select_row.pack(fill="x", padx=20, pady=(0, 12))

        # --- プリセットタブ構築 ---
        self._all_presets = []
        self._preset_map = {}
        self._category_chips = {}
        self._selected_category = "全て"
        self._preset_card_frame = None
        self._build_preset_tab(self._preset_container)

        # --- オリジナル作成タブ構築 ---
        self._selected_archetype = "ツンデレ"
        self._selected_hair_color = "黒髪"
        self._archetype_chips = {}
        self._hair_color_chips = {}
        self._build_custom_tab(self._custom_container)

        # --- API生成セクション（カスタムコンテナ内） ---
        self._build_api_section(self._custom_container)

        # ネストスクロール衝突防止
        self._setup_nested_scroll()

        # 初期表示切替
        self._on_work_type_changed()

        # --- 使用キャラ選択ウィジェット ---
        char_select_row = self._char_select_row

        ctk.CTkLabel(char_select_row, text="使用キャラ:",
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=MaterialColors.ON_SURFACE_VARIANT).pack(side="left", padx=(0, 6))

        self.char_select_combo = ctk.CTkOptionMenu(
            char_select_row, values=["（キャラ選択）"], height=36,
            font=ctk.CTkFont(size=14),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6,
            button_color=MaterialColors.PRIMARY, dropdown_fg_color=MaterialColors.SURFACE,
            text_color=MaterialColors.ON_SURFACE,
            dropdown_text_color=MaterialColors.ON_SURFACE,
            command=self.on_char_selected
        )
        self.char_select_combo.pack(side="left", fill="x", expand=True)
        self.refresh_char_list()
        self.refresh_preset_list()

        # ══════════════════════════════════════════════════════════════
        # 4. 作品設定（メイン入力エリア）
        # ══════════════════════════════════════════════════════════════
        concept_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=12)
        concept_card.pack(fill="x", pady=(0, 16))

        icon_text_label(
            concept_card, Icons.BOOK, "作品設定",
            icon_size=12, text_size=14
        ).pack(anchor="w", padx=20, pady=(12, 8))
        ctk.CTkFrame(concept_card, fg_color=MaterialColors.OUTLINE_VARIANT, height=1, corner_radius=0).pack(fill="x", padx=20, pady=(0, 8))

        # コンセプト入力
        concept_label_frame = ctk.CTkFrame(concept_card, fg_color="transparent")
        concept_label_frame.pack(fill="x", padx=20)
        ctk.CTkLabel(
            concept_label_frame, text="コンセプト",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=MaterialColors.PRIMARY
        ).pack(side="left")
        ctk.CTkLabel(
            concept_label_frame, text="（作品の設定・シチュエーションを詳しく記述）",
            font=ctk.CTkFont(size=12), text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left", padx=(4, 0))

        self.concept_text = ctk.CTkTextbox(
            concept_card, height=120,
            font=ctk.CTkFont(size=16),
            fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST,
            text_color=MaterialColors.ON_SURFACE,
            corner_radius=6, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT,
            wrap="word"
        )
        self.concept_text.pack(fill="x", padx=20, pady=(6, 12))

        # 登場人物入力（個別フィールド）
        char_label_frame = ctk.CTkFrame(concept_card, fg_color="transparent")
        char_label_frame.pack(fill="x", padx=20)
        ctk.CTkLabel(
            char_label_frame, text="登場人物",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=MaterialColors.PRIMARY
        ).pack(side="left")
        ctk.CTkLabel(
            char_label_frame, text="（名前・性格・外見を入力）",
            font=ctk.CTkFont(size=12), text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left", padx=(4, 0))

        char_fields_frame = ctk.CTkFrame(concept_card, fg_color="transparent")
        char_fields_frame.pack(fill="x", padx=20, pady=(6, 12))

        _entry_cfg = dict(
            height=34, font=ctk.CTkFont(size=15),
            fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST,
            text_color=MaterialColors.ON_SURFACE,
            corner_radius=6, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT
        )
        _lbl_cfg = dict(font=ctk.CTkFont(size=12), text_color=MaterialColors.ON_SURFACE_VARIANT)

        # 名前
        _r0 = ctk.CTkFrame(char_fields_frame, fg_color="transparent")
        _r0.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(_r0, text="名前", **_lbl_cfg).pack(side="left", padx=(0, 6))
        self.char_name_field = ctk.CTkEntry(_r0, placeholder_text="例: 中野一花（五等分の花嫁）", **_entry_cfg)
        self.char_name_field.pack(side="left", fill="x", expand=True)

        # 性格
        _r1 = ctk.CTkFrame(char_fields_frame, fg_color="transparent")
        _r1.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(_r1, text="性格", **_lbl_cfg).pack(side="left", padx=(0, 6))
        self.char_personality_field = ctk.CTkEntry(_r1, placeholder_text="例: ツンデレ、意地っ張り", **_entry_cfg)
        self.char_personality_field.pack(side="left", fill="x", expand=True)

        # 一人称 + 語尾（横並び）
        _r2 = ctk.CTkFrame(char_fields_frame, fg_color="transparent")
        _r2.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(_r2, text="一人称", **_lbl_cfg).pack(side="left", padx=(0, 6))
        self.char_first_person_field = ctk.CTkEntry(_r2, width=120, placeholder_text="例: あたし", **_entry_cfg)
        self.char_first_person_field.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(_r2, text="語尾", **_lbl_cfg).pack(side="left", padx=(0, 6))
        self.char_endings_field = ctk.CTkEntry(_r2, placeholder_text="例: ～だよ, ～かな", **_entry_cfg)
        self.char_endings_field.pack(side="left", fill="x", expand=True)

        # 外見
        _r3 = ctk.CTkFrame(char_fields_frame, fg_color="transparent")
        _r3.pack(fill="x")
        ctk.CTkLabel(_r3, text="外見", **_lbl_cfg).pack(side="left", padx=(0, 6))
        self.char_appearance_field = ctk.CTkEntry(_r3, placeholder_text="例: 金髪ロング、青い瞳", **_entry_cfg)
        self.char_appearance_field.pack(side="left", fill="x", expand=True)

        # その他の登場人物入力
        other_label_frame = ctk.CTkFrame(concept_card, fg_color="transparent")
        other_label_frame.pack(fill="x", padx=20)
        ctk.CTkLabel(
            other_label_frame, text="その他の登場人物",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=MaterialColors.PRIMARY
        ).pack(side="left")
        ctk.CTkLabel(
            other_label_frame, text="（男主人公・サブキャラ等の設定）",
            font=ctk.CTkFont(size=12), text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left", padx=(4, 0))

        self.other_chars_text = ctk.CTkTextbox(
            concept_card, height=70,
            font=ctk.CTkFont(size=16),
            fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST,
            text_color=MaterialColors.ON_SURFACE,
            corner_radius=6, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT,
            wrap="word"
        )
        self.other_chars_text.pack(fill="x", padx=20, pady=(8, 16))
        self.other_chars_text.insert("1.0", "相手役の男性（顔なし）\nSD: 1boy, faceless_male")

        # ══════════════════════════════════════════════════════════════
        # 5. 生成設定
        # ══════════════════════════════════════════════════════════════
        settings_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=12)
        settings_card.pack(fill="x", pady=(0, 16))

        icon_text_label(
            settings_card, Icons.GEAR, "生成設定",
            icon_size=12, text_size=14
        ).pack(anchor="w", padx=20, pady=(12, 8))
        ctk.CTkFrame(settings_card, fg_color=MaterialColors.OUTLINE_VARIANT, height=1, corner_radius=0).pack(fill="x", padx=20, pady=(0, 8))

        settings_row = ctk.CTkFrame(settings_card, fg_color="transparent")
        settings_row.pack(fill="x", padx=20, pady=(0, 12))

        # シーン数
        scenes_frame = ctk.CTkFrame(settings_row, fg_color="transparent")
        scenes_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(scenes_frame, text="シーン数", font=ctk.CTkFont(size=13), text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w")
        self.scenes_entry = ctk.CTkEntry(
            scenes_frame, height=38, font=ctk.CTkFont(size=15),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6,
            text_color=MaterialColors.ON_SURFACE,
            border_width=1, border_color=MaterialColors.OUTLINE_VARIANT
        )
        self.scenes_entry.pack(fill="x", pady=(4, 0))
        self.scenes_entry.insert(0, "10")

        # テーマ
        theme_frame = ctk.CTkFrame(settings_row, fg_color="transparent")
        theme_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(theme_frame, text="テーマ", font=ctk.CTkFont(size=13), text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w")
        self.theme_combo = ctk.CTkOptionMenu(
            theme_frame, values=list(THEME_OPTIONS.keys()), height=38,
            font=ctk.CTkFont(size=14),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6,
            button_color=MaterialColors.PRIMARY, dropdown_fg_color=MaterialColors.SURFACE,
            text_color=MaterialColors.ON_SURFACE,
            dropdown_text_color=MaterialColors.ON_SURFACE
        )
        self.theme_combo.pack(fill="x", pady=(4, 0))
        self.theme_combo.set("指定なし")

        self.scenes_entry.bind("<KeyRelease>", self.update_cost_preview)

        # ストーリー構成バー
        self._build_structure_bar(settings_card)

        self.cost_preview_label = ctk.CTkLabel(
            settings_card, text="シーン数入力で予想コスト表示",
            font=ctk.CTkFont(size=12), text_color=MaterialColors.ON_SURFACE_VARIANT
        )
        self.cost_preview_label.pack(anchor="w", padx=20, pady=(4, 12))

        # ══════════════════════════════════════════════════════════════
        # 6. 生成セクション
        # ══════════════════════════════════════════════════════════════
        generate_section = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=12,
                                        border_width=1, border_color=MaterialColors.PRIMARY)
        generate_section.pack(fill="x", pady=(0, 16))

        gen_inner = ctk.CTkFrame(generate_section, fg_color="transparent")
        gen_inner.pack(fill="x", padx=20, pady=20)

        # ステータス行
        status_row = ctk.CTkFrame(gen_inner, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 12))

        self.status_icon_label = ctk.CTkLabel(
            status_row, text=Icons.CLOCK,
            font=ctk.CTkFont(family=FONT_ICON, size=12),
            text_color=MaterialColors.ON_SURFACE_VARIANT
        )
        self.status_icon_label.pack(side="left", padx=(0, 8))

        self.status_label = ctk.CTkLabel(
            status_row, text="待機中",
            font=ctk.CTkFont(family=FONT_JP, size=14, weight="bold"),
            text_color=MaterialColors.ON_SURFACE
        )
        self.status_label.pack(side="left")

        # フェーズ
        phase_frame = ctk.CTkFrame(status_row, fg_color="transparent")
        phase_frame.pack(side="right")
        self.phase_labels = []
        for phase in ["圧縮", "あらすじ", "分割", "シーン生成", "品質検証"]:
            pill = ctk.CTkFrame(phase_frame, fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=8)
            pill.pack(side="left", padx=4)
            lbl = ctk.CTkLabel(pill, text=phase, font=ctk.CTkFont(family=FONT_JP, size=13), text_color=MaterialColors.ON_SURFACE_VARIANT, padx=10, pady=4)
            lbl.pack()
            self.phase_labels.append((pill, lbl))

        # プログレス
        self.progress = ctk.CTkProgressBar(
            gen_inner, fg_color=MaterialColors.SURFACE_CONTAINER, progress_color=MaterialColors.PRIMARY,
            height=8, corner_radius=4
        )
        self.progress.pack(fill="x", pady=(0, 12))
        self.progress.set(0)

        # ボタン行
        btn_row = ctk.CTkFrame(gen_inner, fg_color="transparent")
        btn_row.pack(fill="x")

        self.generate_btn = MaterialButton(
            btn_row, text="脚本を生成", variant="filled", size="large",
            command=self.start_generation
        )
        self.generate_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        add_tooltip(self.generate_btn, "脚本生成を開始 (Ctrl+Enter)")

        self.save_btn = MaterialButton(
            btn_row, text="保存", variant="filled_tonal", size="large",
            width=72, command=self.save_settings
        )
        self.save_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = MaterialButton(
            btn_row, text="停止", variant="outlined", size="large",
            width=64, command=self.stop_generation
        )
        self.stop_btn.pack(side="left")
        self.stop_btn.configure(state="disabled")
        add_tooltip(self.stop_btn, "生成を停止 (Esc)")

        # ══════════════════════════════════════════════════════════════
        # 7. コスト＆ログ
        # ══════════════════════════════════════════════════════════════
        cost_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=12)
        cost_card.pack(fill="x", pady=(0, 16))

        icon_text_label(
            cost_card, Icons.COINS, "コスト",
            icon_size=12, text_size=14
        ).pack(anchor="w", padx=20, pady=(12, 8))
        ctk.CTkFrame(cost_card, fg_color=MaterialColors.OUTLINE_VARIANT, height=1, corner_radius=0).pack(fill="x", padx=20, pady=(0, 8))

        self.cost_label = ctk.CTkLabel(
            cost_card, text="生成後に表示",
            font=ctk.CTkFont(family=FONT_MONO, size=11), text_color=MaterialColors.ON_SURFACE_VARIANT, justify="left"
        )
        self.cost_label.pack(anchor="w", padx=20, pady=(0, 12))

        log_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=12)
        log_card.pack(fill="both", expand=True, pady=(0, 16))

        icon_text_label(
            log_card, Icons.LIST, "実行ログ",
            icon_size=12, text_size=14
        ).pack(anchor="w", padx=20, pady=(12, 8))
        ctk.CTkFrame(log_card, fg_color=MaterialColors.OUTLINE_VARIANT, height=1, corner_radius=0).pack(fill="x", padx=20, pady=(0, 8))

        self.log_text = ctk.CTkTextbox(
            log_card, height=180,
            fg_color=MaterialColors.INVERSE_SURFACE, text_color=MaterialColors.INVERSE_ON_SURFACE,
            corner_radius=6, font=ctk.CTkFont(family=FONT_MONO, size=12)
        )
        self.log_text.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        # フッター（プレゼン用削除）

        # Snackbar
        self.snackbar = Snackbar(self)

        # フォーカス状態バインド（入力フィールド）
        for widget in [self.api_field, self.scenes_entry, self.concept_text,
                       self.char_name_field, self.char_personality_field,
                       self.char_first_person_field, self.char_endings_field,
                       self.char_appearance_field, self.other_chars_text]:
            widget.bind("<FocusIn>", lambda e, w=widget: w.configure(border_color=MaterialColors.PRIMARY))
            widget.bind("<FocusOut>", lambda e, w=widget: w.configure(border_color=MaterialColors.OUTLINE_VARIANT))

    def _set_concept_text(self, value: str):
        """コンセプトテキストを設定"""
        self.concept_text.delete("1.0", "end")
        if value:
            self.concept_text.insert("1.0", value)

    def _set_characters_text(self, value: str):
        """登場人物テキストをパースして個別フィールドに設定"""
        # 全フィールドクリア
        for f in [self.char_name_field, self.char_personality_field,
                  self.char_first_person_field, self.char_endings_field,
                  self.char_appearance_field]:
            f.delete(0, "end")

        if not value:
            return

        import re as _re
        lines = value.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("【") and "】" in line:
                m = _re.match(r"【(.+?)】(?:（(.+?)）)?", line)
                if m:
                    name = m.group(1)
                    work = m.group(2) or ""
                    self.char_name_field.delete(0, "end")
                    self.char_name_field.insert(0, f"{name}（{work}）" if work else name)
                else:
                    self.char_name_field.delete(0, "end")
                    self.char_name_field.insert(0, line)
            elif line.startswith("性格:"):
                self.char_personality_field.delete(0, "end")
                self.char_personality_field.insert(0, line.split(":", 1)[1].strip())
            elif line.startswith("一人称:"):
                self.char_first_person_field.delete(0, "end")
                self.char_first_person_field.insert(0, line.split(":", 1)[1].strip())
            elif line.startswith("語尾:"):
                self.char_endings_field.delete(0, "end")
                self.char_endings_field.insert(0, line.split(":", 1)[1].strip())
            elif line.startswith("外見:"):
                self.char_appearance_field.delete(0, "end")
                self.char_appearance_field.insert(0, line.split(":", 1)[1].strip())

    def _get_characters_text(self) -> str:
        """個別フィールドからパイプライン用テキストを組み立て"""
        name = self.char_name_field.get().strip()
        if not name:
            return ""
        personality = self.char_personality_field.get().strip()
        first_person = self.char_first_person_field.get().strip()
        endings = self.char_endings_field.get().strip()
        appearance = self.char_appearance_field.get().strip()

        # 名前行: 【名前】（作品名）形式に復元
        if "（" in name and name.endswith("）"):
            # 既に「名前（作品名）」形式の場合
            parts = name.split("（", 1)
            name_line = f"【{parts[0]}】（{parts[1]}"
        else:
            name_line = f"【{name}】"

        lines = [name_line]
        if personality:
            lines.append(f"性格: {personality}")
        if first_person:
            lines.append(f"一人称: {first_person}")
        if endings:
            lines.append(f"語尾: {endings}")
        if appearance:
            lines.append(f"外見: {appearance}")
        return "\n".join(lines)

    def _get_characters_fields(self) -> dict:
        """個別フィールドの値を構造化データとして取得"""
        return {
            "name": self.char_name_field.get().strip(),
            "personality": self.char_personality_field.get().strip(),
            "first_person": self.char_first_person_field.get().strip(),
            "endings": self.char_endings_field.get().strip(),
            "appearance": self.char_appearance_field.get().strip(),
        }

    def _set_characters_fields(self, fields: dict):
        """構造化データから個別フィールドに設定"""
        for f in [self.char_name_field, self.char_personality_field,
                  self.char_first_person_field, self.char_endings_field,
                  self.char_appearance_field]:
            f.delete(0, "end")
        if fields.get("name"):
            self.char_name_field.insert(0, fields["name"])
        if fields.get("personality"):
            self.char_personality_field.insert(0, fields["personality"])
        if fields.get("first_person"):
            self.char_first_person_field.insert(0, fields["first_person"])
        if fields.get("endings"):
            self.char_endings_field.insert(0, fields["endings"])
        if fields.get("appearance"):
            self.char_appearance_field.insert(0, fields["appearance"])

    def _set_api_field(self, value: str):
        """APIフィールドを設定"""
        self.api_field.delete(0, "end")
        if value:
            self.api_field.insert(0, value)

    def load_saved_config(self):
        if self.config_data.get("api_key"):
            self._set_api_field(self.config_data["api_key"])
        if self.config_data.get("concept"):
            self._set_concept_text(self.config_data["concept"])
        # characters_fields優先、fallbackでテキストパース
        if self.config_data.get("characters_fields"):
            self._set_characters_fields(self.config_data["characters_fields"])
        elif self.config_data.get("characters"):
            self._set_characters_text(self.config_data["characters"])
        if self.config_data.get("num_scenes"):
            self.scenes_entry.delete(0, "end")
            self.scenes_entry.insert(0, str(self.config_data["num_scenes"]))
        if self.config_data.get("theme_jp"):
            self.theme_combo.set(self.config_data["theme_jp"])
        if self.config_data.get("work_type"):
            self.work_type_var.set(self.config_data["work_type"])
            self._on_work_type_changed()
        if self.config_data.get("story_structure"):
            ss = self.config_data["story_structure"]
            self.prologue_slider.set(ss.get("prologue", 10))
            self.epilogue_slider.set(ss.get("epilogue", 10))
            preset_name = ss.get("preset", "標準バランス (10/80/10)")
            if preset_name in STRUCTURE_PRESETS:
                self.structure_preset.set(preset_name)
            self._update_structure_bar()

        # 初期コスト予測を表示
        self.after(100, self.update_cost_preview)

    def update_cost_preview(self, event=None):
        """シーン数に基づいてコスト予測を更新"""
        try:
            num_scenes = int(self.scenes_entry.get())
            if num_scenes < 1:
                num_scenes = 1
            elif num_scenes > 50:
                num_scenes = 50

            est = estimate_cost(num_scenes)
            self.cost_preview_label.configure(
                text=f"予想コスト: ${est['estimated_usd']:.4f} (約¥{est['estimated_jpy']:.1f}) | "
                     f"Haiku: ~{est['haiku_tokens']:,}トークン, Sonnet: ~{est['sonnet_tokens']:,}トークン"
            )
        except ValueError:
            self.cost_preview_label.configure(
                text="予想コスト: シーン数を入力してください"
            )

    def _build_structure_bar(self, parent):
        """ストーリー構成バーUIを構築"""
        structure_frame = ctk.CTkFrame(parent, fg_color="transparent")
        structure_frame.pack(fill="x", padx=20, pady=(8, 4))

        # ヘッダー行: ラベル + プリセット
        header_row = ctk.CTkFrame(structure_frame, fg_color="transparent")
        header_row.pack(fill="x")
        ctk.CTkLabel(
            header_row, text="ストーリー構成",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left")

        self.structure_preset = ctk.CTkOptionMenu(
            header_row, values=list(STRUCTURE_PRESETS.keys()), height=30,
            font=ctk.CTkFont(size=12), width=200,
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6,
            button_color=MaterialColors.PRIMARY,
            dropdown_fg_color=MaterialColors.SURFACE,
            text_color=MaterialColors.ON_SURFACE,
            dropdown_text_color=MaterialColors.ON_SURFACE,
            command=self._on_structure_preset_changed
        )
        self.structure_preset.pack(side="right")
        self.structure_preset.set("標準バランス (10/80/10)")

        # ビジュアルバー（Canvas）
        bar_frame = ctk.CTkFrame(structure_frame, fg_color="transparent")
        bar_frame.pack(fill="x", pady=(8, 4))
        self.structure_canvas = tk.Canvas(
            bar_frame, height=28, highlightthickness=0,
            bg=MaterialColors.SURFACE_CONTAINER_LOW
        )
        self.structure_canvas.pack(fill="x")
        self.structure_canvas.bind("<Configure>", lambda e: self._update_structure_bar())

        # スライダー行
        slider_frame = ctk.CTkFrame(structure_frame, fg_color="transparent")
        slider_frame.pack(fill="x", pady=(4, 0))

        # プロローグスライダー
        pro_row = ctk.CTkFrame(slider_frame, fg_color="transparent")
        pro_row.pack(fill="x", pady=2)
        ctk.CTkLabel(
            pro_row, text="プロローグ", width=90, anchor="w",
            font=ctk.CTkFont(size=12), text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left")
        self.prologue_slider = ctk.CTkSlider(
            pro_row, from_=5, to=30, number_of_steps=5,
            fg_color=MaterialColors.SURFACE_CONTAINER,
            progress_color=MaterialColors.SECONDARY,
            button_color=MaterialColors.PRIMARY,
            button_hover_color=MaterialColors.PRIMARY_CONTAINER,
            command=self._on_structure_slider_changed
        )
        self.prologue_slider.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self.prologue_slider.set(10)
        self.prologue_pct_label = ctk.CTkLabel(
            pro_row, text="10%", width=40,
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MaterialColors.SECONDARY
        )
        self.prologue_pct_label.pack(side="left")

        # エピローグスライダー
        epi_row = ctk.CTkFrame(slider_frame, fg_color="transparent")
        epi_row.pack(fill="x", pady=2)
        ctk.CTkLabel(
            epi_row, text="エピローグ", width=90, anchor="w",
            font=ctk.CTkFont(size=12), text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left")
        self.epilogue_slider = ctk.CTkSlider(
            epi_row, from_=5, to=20, number_of_steps=3,
            fg_color=MaterialColors.SURFACE_CONTAINER,
            progress_color=MaterialColors.SECONDARY,
            button_color=MaterialColors.PRIMARY,
            button_hover_color=MaterialColors.PRIMARY_CONTAINER,
            command=self._on_structure_slider_changed
        )
        self.epilogue_slider.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self.epilogue_slider.set(10)
        self.epilogue_pct_label = ctk.CTkLabel(
            epi_row, text="10%", width=40,
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MaterialColors.SECONDARY
        )
        self.epilogue_pct_label.pack(side="left")

        # 本編（自動算出）ラベル
        main_row = ctk.CTkFrame(slider_frame, fg_color="transparent")
        main_row.pack(fill="x", pady=2)
        ctk.CTkLabel(
            main_row, text="→ 本編:", width=90, anchor="w",
            font=ctk.CTkFont(size=12), text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left")
        self.main_pct_label = ctk.CTkLabel(
            main_row, text="自動算出 80%",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MaterialColors.PRIMARY
        )
        self.main_pct_label.pack(side="left", padx=(8, 0))

    def _update_structure_bar(self):
        """構成バーの再描画"""
        canvas = self.structure_canvas
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10:
            return

        canvas.delete("all")

        prologue = int(round(self.prologue_slider.get()))
        epilogue = int(round(self.epilogue_slider.get()))
        main_pct = 100 - prologue - epilogue

        # パーセンテージラベル更新
        self.prologue_pct_label.configure(text=f"{prologue}%")
        self.epilogue_pct_label.configure(text=f"{epilogue}%")
        self.main_pct_label.configure(text=f"自動算出 {main_pct}%")

        # セグメント描画用データ
        segments = [
            (prologue / 100, MaterialColors.SECONDARY, f"プロローグ {prologue}%"),
            (main_pct / 100, MaterialColors.PRIMARY, f"本編 {main_pct}%"),
            (epilogue / 100, MaterialColors.TERTIARY, f"エピローグ {epilogue}%"),
        ]

        r = 6  # 角丸半径
        x = 0
        for i, (ratio, color, label_text) in enumerate(segments):
            seg_w = max(2, ratio * w)
            x1, x2 = x, x + seg_w

            # 左端の角丸
            if i == 0:
                canvas.create_rectangle(x1, 0, x2, h, fill=color, outline="")
                canvas.create_arc(x1, 0, x1 + r * 2, r * 2, start=90, extent=90, fill=color, outline="")
                canvas.create_arc(x1, h - r * 2, x1 + r * 2, h, start=180, extent=90, fill=color, outline="")
            # 右端の角丸
            elif i == len(segments) - 1:
                canvas.create_rectangle(x1, 0, x2, h, fill=color, outline="")
                canvas.create_arc(x2 - r * 2, 0, x2, r * 2, start=0, extent=90, fill=color, outline="")
                canvas.create_arc(x2 - r * 2, h - r * 2, x2, h, start=270, extent=90, fill=color, outline="")
            else:
                canvas.create_rectangle(x1, 0, x2, h, fill=color, outline="")

            # テキストラベル（セグメントが狭すぎなければ）
            mid_x = (x1 + x2) / 2
            if seg_w > 60:
                canvas.create_text(mid_x, h / 2, text=label_text, fill="#FFFFFF",
                                   font=("Noto Sans JP", 9, "bold"))

            x = x2

    def _on_structure_preset_changed(self, value):
        """プリセット選択時"""
        preset = STRUCTURE_PRESETS.get(value)
        if preset is None:
            return
        self.prologue_slider.set(preset["prologue"])
        self.epilogue_slider.set(preset["epilogue"])
        self._update_structure_bar()

    def _on_structure_slider_changed(self, _value=None):
        """スライダー変更時"""
        self._update_structure_bar()
        # プリセットと一致するか確認、しなければ「カスタム」に
        prologue = int(round(self.prologue_slider.get()))
        epilogue = int(round(self.epilogue_slider.get()))
        matched = False
        for name, preset in STRUCTURE_PRESETS.items():
            if preset and preset["prologue"] == prologue and preset["epilogue"] == epilogue:
                self.structure_preset.set(name)
                matched = True
                break
        if not matched:
            self.structure_preset.set("カスタム")

    def _get_story_structure(self) -> dict:
        """現在のストーリー構成比率を取得"""
        prologue = int(round(self.prologue_slider.get()))
        epilogue = int(round(self.epilogue_slider.get()))
        main_pct = 100 - prologue - epilogue
        return {"prologue": prologue, "main": main_pct, "epilogue": epilogue}

    def save_settings(self):
        """設定を保存"""
        theme_jp = self.theme_combo.get()
        self.config_data = {
            "api_key": self.api_field.get(),
            "concept": self.concept_text.get("1.0", "end-1c"),
            "characters": self._get_characters_text(),
            "characters_fields": self._get_characters_fields(),
            "other_characters": self.other_chars_text.get("1.0", "end-1c") if hasattr(self, "other_chars_text") else "",
            "num_scenes": int(self.scenes_entry.get() or "10"),
            "theme_jp": theme_jp,
            "theme": THEME_OPTIONS.get(theme_jp, ""),
            "work_type": self.work_type_var.get(),
            "story_structure": {
                "prologue": int(round(self.prologue_slider.get())),
                "epilogue": int(round(self.epilogue_slider.get())),
                "preset": self.structure_preset.get(),
            },
        }
        save_config(self.config_data)
        self.snackbar.show("設定を保存しました", type="success")
        log_message("設定を保存しました")

    def get_current_config(self) -> dict:
        """現在の設定を辞書として取得"""
        theme_jp = self.theme_combo.get()
        return {
            "api_key": self.api_field.get(),
            "concept": self.concept_text.get("1.0", "end-1c"),
            "characters": self._get_characters_text(),
            "characters_fields": self._get_characters_fields(),
            "other_characters": self.other_chars_text.get("1.0", "end-1c") if hasattr(self, "other_chars_text") else "",
            "num_scenes": int(self.scenes_entry.get() or "10"),
            "theme_jp": theme_jp,
            "theme": THEME_OPTIONS.get(theme_jp, ""),
            "work_title": self.work_title_entry.get(),
            "char_name": self.char_name_entry.get(),
            "work_type": self.work_type_var.get(),
        }

    def apply_config(self, config: dict):
        """設定を画面に反映"""
        if config.get("api_key"):
            self._set_api_field(config["api_key"])
        if config.get("concept"):
            self._set_concept_text(config["concept"])
        # characters_fields優先、fallbackでテキストパース
        if config.get("characters_fields"):
            self._set_characters_fields(config["characters_fields"])
        elif config.get("characters"):
            self._set_characters_text(config["characters"])
        if hasattr(self, "other_chars_text") and "other_characters" in config:
            self.other_chars_text.delete("1.0", "end")
            self.other_chars_text.insert("1.0", config.get("other_characters", ""))
        if config.get("num_scenes"):
            self.scenes_entry.delete(0, "end")
            self.scenes_entry.insert(0, str(config["num_scenes"]))
        if config.get("theme_jp"):
            self.theme_combo.set(config["theme_jp"])
        if config.get("work_title"):
            self.work_title_entry.delete(0, "end")
            self.work_title_entry.insert(0, config["work_title"])
        if config.get("char_name"):
            self.char_name_entry.delete(0, "end")
            self.char_name_entry.insert(0, config["char_name"])
        if config.get("work_type"):
            self.work_type_var.set(config["work_type"])
            self._on_work_type_changed()
        if config.get("story_structure"):
            ss = config["story_structure"]
            self.prologue_slider.set(ss.get("prologue", 10))
            self.epilogue_slider.set(ss.get("epilogue", 10))
            preset_name = ss.get("preset", "標準バランス (10/80/10)")
            if preset_name in STRUCTURE_PRESETS:
                self.structure_preset.set(preset_name)
            self._update_structure_bar()
        self.update_cost_preview()

    def refresh_profile_list(self):
        """プロファイル一覧を更新"""
        profiles = ["（新規）"] + get_profile_list()
        self.profile_combo.configure(values=profiles)

    def on_profile_selected(self, choice: str):
        """プロファイル選択時"""
        if choice != "（新規）":
            self.profile_name_entry.delete(0, "end")
            self.profile_name_entry.insert(0, choice)

    def save_current_profile(self):
        """現在の設定をプロファイルとして保存"""
        name = self.profile_name_entry.get().strip()
        if not name:
            self.snackbar.show("プロファイル名を入力してください", type="error")
            return
        
        # 上書き確認
        if name in get_profile_list():
            # 既存プロファイルを上書き
            pass  # 確認ダイアログは省略、直接上書き
        
        config = self.get_current_config()
        save_profile(name, config)
        self.refresh_profile_list()
        self.profile_combo.set(name)
        self.snackbar.show(f"プロファイル '{name}' を保存しました", type="success")

    def load_selected_profile(self):
        """選択したプロファイルを読み込み"""
        name = self.profile_combo.get()
        if name == "（新規）":
            self.snackbar.show("プロファイルを選択してください", type="warning")
            return
        
        config = load_profile(name)
        if config:
            self.apply_config(config)
            self.profile_name_entry.delete(0, "end")
            self.profile_name_entry.insert(0, name)
            self.snackbar.show(f"プロファイル '{name}' を読み込みました", type="success")
            self.log(f"プロファイル読込: {name}")
        else:
            self.snackbar.show(f"プロファイル '{name}' が見つかりません", type="error")

    def copy_selected_profile(self):
        """選択したプロファイルを複製"""
        src_name = self.profile_combo.get()
        if src_name == "（新規）":
            self.snackbar.show("コピー元のプロファイルを選択してください", type="warning")
            return
        
        dst_name = self.profile_name_entry.get().strip()
        if not dst_name:
            dst_name = f"{src_name}_copy"
        
        if dst_name == src_name:
            dst_name = f"{src_name}_copy"
        
        if copy_profile(src_name, dst_name):
            self.refresh_profile_list()
            self.profile_combo.set(dst_name)
            self.profile_name_entry.delete(0, "end")
            self.profile_name_entry.insert(0, dst_name)
            self.snackbar.show(f"'{src_name}' を '{dst_name}' にコピーしました", type="success")
        else:
            self.snackbar.show("コピーに失敗しました", type="error")

    def delete_selected_profile(self):
        """選択したプロファイルを削除"""
        name = self.profile_combo.get()
        if name == "（新規）":
            self.snackbar.show("削除するプロファイルを選択してください", type="warning")
            return
        
        if delete_profile(name):
            self.refresh_profile_list()
            self.profile_combo.set("（新規）")
            self.profile_name_entry.delete(0, "end")
            self.snackbar.show(f"プロファイル '{name}' を削除しました", type="success")
        else:
            self.snackbar.show("削除に失敗しました", type="error")

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        log_message(message)

    def update_status(self, message: str):
        # ステータスアイコン自動切替
        if "[ERROR]" in message or "エラー" in message:
            self.status_icon_label.configure(text=Icons.XMARK)
        elif "[OK]" in message or "完了" in message:
            self.status_icon_label.configure(text=Icons.CHECK)
        elif "[WARN]" in message or "停止" in message:
            self.status_icon_label.configure(text=Icons.WARNING)
        elif "開始" in message or "生成中" in message:
            self.status_icon_label.configure(text=Icons.PLAY)
        else:
            self.status_icon_label.configure(text=Icons.CLOCK)
        self.status_label.configure(text=message)
        self.log(message)

        # フェーズインジケーター更新
        self.update_phase_indicator(message)

    def update_phase_indicator(self, message: str):
        """フェーズインジケーターを更新（5段階: 圧縮/あらすじ/分割/シーン生成/品質検証）"""
        import re

        def mark_done(*indices):
            for i in indices:
                if i < len(self.phase_labels):
                    pill, lbl = self.phase_labels[i]
                    pill.configure(fg_color=MaterialColors.SUCCESS)
                    lbl.configure(text_color=MaterialColors.ON_PRIMARY)

        def mark_active(idx):
            if idx < len(self.phase_labels):
                pill, lbl = self.phase_labels[idx]
                pill.configure(fg_color=MaterialColors.PRIMARY)
                lbl.configure(text_color=MaterialColors.ON_PRIMARY)

        def reset_all():
            for pill, lbl in self.phase_labels:
                pill.configure(fg_color=MaterialColors.SURFACE_CONTAINER)
                lbl.configure(text_color=MaterialColors.ON_SURFACE_VARIANT)

        # フェーズ検出（優先順位付き）
        new_phase = None

        if "[DONE]" in message or ("生成完了" in message and "シーン" in message):
            new_phase = "done"
        elif "Phase 5" in message or "品質検証" in message:
            new_phase = 4
        elif "Phase 1" in message and "圧縮" in message:
            new_phase = 0
        elif "[OK]" in message and "圧縮完了" in message:
            new_phase = 1  # Phase 1完了→Phase 2待ち
        elif "Phase 2" in message or "原案作成" in message:
            new_phase = 1
        elif "[OK]" in message and "原案完成" in message:
            new_phase = 2  # Phase 2完了→Phase 3待ち
        elif "Phase 3" in message or "シーン分割" in message:
            new_phase = 2
        elif "[OK]" in message and "分割完成" in message:
            new_phase = 3  # Phase 3完了→Phase 4待ち
        elif re.search(r'シーン \d+/\d+', message):
            new_phase = 3

        # 状態が変わらない場合はプログレスバーのみ更新
        if new_phase is None:
            # シーン進捗のみ更新（フェーズ表示はそのまま維持）
            match = re.search(r'(\d+)/(\d+)', message)
            if match and hasattr(self, '_current_phase') and self._current_phase == 3:
                current, total = int(match.group(1)), int(match.group(2))
                progress = 0.35 + (current / total) * 0.50
                self.progress.set(progress)
            return

        # フェーズ状態を保存
        self._current_phase = new_phase

        # 表示更新
        reset_all()
        if new_phase == "done":
            mark_done(0, 1, 2, 3, 4)
            self.progress.set(1.0)
        elif new_phase == 0:
            mark_active(0)
            self.progress.set(0.05)
        elif new_phase == 1:
            mark_done(0)
            mark_active(1)
            self.progress.set(0.12)
        elif new_phase == 2:
            mark_done(0, 1)
            mark_active(2)
            self.progress.set(0.20)
        elif new_phase == 3:
            mark_done(0, 1, 2)
            mark_active(3)
            match = re.search(r'(\d+)/(\d+)', message)
            if match:
                current, total = int(match.group(1)), int(match.group(2))
                progress = 0.35 + (current / total) * 0.50
                self.progress.set(progress)
            else:
                self.progress.set(0.30)
        elif new_phase == 4:
            mark_done(0, 1, 2, 3)
            mark_active(4)
            self.progress.set(0.90)

    def start_generation(self):
        if self.is_generating:
            return

        api_key = self.api_field.get().strip()

        concept = self.concept_text.get("1.0", "end-1c").strip()
        characters = self._get_characters_text().strip()
        other_chars = self.other_chars_text.get("1.0", "end-1c").strip() if hasattr(self, "other_chars_text") else ""

        if not api_key:
            self.snackbar.show("Anthropic APIキーを入力してください", type="error")
            return
        if not concept:
            self.snackbar.show("コンセプトを入力してください", type="error")
            return

        try:
            num_scenes = int(self.scenes_entry.get())
            if num_scenes < 1 or num_scenes > 50:
                raise ValueError()
        except (ValueError, TypeError):
            self.snackbar.show("シーン数は1〜50の整数で", type="error")
            return

        # ストーリー構成を取得
        story_structure = self._get_story_structure()

        # Auto-save settings
        self.save_settings()

        # アウトラインプレビュー生成（ローカル・API不要）
        theme_jp = self.theme_combo.get()
        theme = THEME_OPTIONS.get(theme_jp, "")
        theme_guide = THEME_GUIDES.get(theme, THEME_GUIDES.get("vanilla", {}))
        theme_name = theme_guide.get("name", "指定なし")

        # 簡易コスト見積もり（ストーリー構成反映）
        pro_pct = story_structure["prologue"] / 100
        epi_pct = story_structure["epilogue"] / 100
        main_pct = story_structure["main"] / 100
        act3_count = max(1, round(num_scenes * main_pct * 0.75))
        low_count = num_scenes - act3_count
        high_count = act3_count
        prep_calls = 2  # あらすじ生成 + シーン分割
        total_api = prep_calls + num_scenes
        est_cost_prep = prep_calls * (2000 * 0.25 + 2000 * 1.25) / 1_000_000
        est_cost_haiku = low_count * (3000 * 0.25 + 2500 * 1.25) / 1_000_000
        est_cost_sonnet = high_count * (3000 * 3.00 + 2500 * 15.00) / 1_000_000
        est_total = est_cost_prep + est_cost_haiku + est_cost_sonnet

        # プレビュー表示
        self.log_text.delete("1.0", "end")
        self.log(f"{'='*50}")
        self.log(f"[INFO]生成プレビュー")
        self.log(f"{'='*50}")
        self.log(f"バックエンド: Claude (Anthropic)")
        self.log(f"テーマ: {theme_name}")
        self.log(f"シーン数: {num_scenes}")
        self.log(f"ストーリー構成: プロローグ{story_structure['prologue']}% / 本編{story_structure['main']}% / エピローグ{story_structure['epilogue']}%")
        self.log(f"")
        self.log(f"[STAT]パイプライン:")
        self.log(f"  Step 1: ストーリー原案作成（Haiku×1）")
        self.log(f"  Step 2: シーン分割（Haiku×1）")
        self.log(f"  Step 3: シーン生成")
        self.log(f"    Low (1-3): {low_count}シーン → Haiku")
        self.log(f"    High (4-5): {high_count}シーン → Sonnet")
        self.log(f"")
        self.log(f"[COST]推定コスト: ${est_total:.4f}")
        self.log(f"  準備: ${est_cost_prep:.4f} (あらすじ+分割)")
        self.log(f"  Haiku: ${est_cost_haiku:.4f} ({low_count}回)")
        self.log(f"  Sonnet: ${est_cost_sonnet:.4f} ({high_count}回)")
        self.log(f"  合計API呼び出し: {total_api}回")
        self.log(f"{'='*50}")
        self.log(f"")

        self.is_generating = True
        self.stop_requested = False
        self.generate_btn.configure(state="disabled", text="生成中...")
        self.stop_btn.configure(
            state="normal",
            border_color=MaterialColors.ERROR,
            text_color=MaterialColors.ERROR
        )
        self.progress.set(0)

        thread = threading.Thread(
            target=self.run_generation,
            args=(api_key, concept, characters, num_scenes, other_chars, story_structure),
            daemon=True
        )
        thread.start()

    def stop_generation(self):
        if self.is_generating:
            self.stop_requested = True
            self.update_status("[STOP]停止リクエスト送信...")
            self.stop_btn.configure(state="disabled", text="停止中...")

    def run_generation(self, api_key: str, concept: str, characters: str, num_scenes: int, other_chars: str = "", story_structure: dict = None):
        try:
            theme_jp = self.theme_combo.get()
            theme = THEME_OPTIONS.get(theme_jp, "")

            def callback(msg):
                if self.stop_requested:
                    raise InterruptedError("ユーザーによる停止")
                self.after(0, lambda: self.update_status(msg))

            self.after(0, lambda: self.update_status("[START] パイプライン開始... [Claude (Anthropic)]"))

            # その他の登場人物をcharactersに統合
            full_characters = characters
            if other_chars:
                full_characters = f"{characters}\n\n【その他の登場人物】\n{other_chars}"

            results, cost_tracker = generate_pipeline(
                api_key, concept, full_characters, num_scenes, theme, callback,
                story_structure=story_structure
            )

            if self.stop_requested:
                self.after(0, lambda: self.on_stopped())
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = EXPORTS_DIR / f"script_{timestamp}.csv"
            json_path = EXPORTS_DIR / f"script_{timestamp}.json"
            xlsx_path = EXPORTS_DIR / f"script_{timestamp}.xlsx"

            export_csv(results, csv_path)
            export_json(results, json_path)

            # Excel出力（openpyxlがある場合）
            excel_ok = export_excel(results, xlsx_path)

            self.after(0, lambda: self.on_complete(results, cost_tracker, csv_path, json_path, xlsx_path if excel_ok else None))

        except InterruptedError:
            # 中断時でも途中結果をエクスポート
            if results:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                partial_json = EXPORTS_DIR / f"script_{timestamp}_partial.json"
                try:
                    export_json(results, partial_json)
                    partial_path = str(partial_json)
                    self.after(0, lambda: self.on_stopped_with_partial(partial_path, len(results)))
                except Exception:
                    self.after(0, lambda: self.on_stopped())
            else:
                self.after(0, lambda: self.on_stopped())
        except Exception as e:
            # エラー時も途中結果があれば保存
            if results:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                partial_json = EXPORTS_DIR / f"script_{timestamp}_error.json"
                try:
                    export_json(results, partial_json)
                except Exception:
                    pass
            self.after(0, lambda: self.on_error(str(e)))

    def reset_buttons(self):
        self.is_generating = False
        self.stop_requested = False
        self.generate_btn.configure(state="normal", text="脚本を生成")
        self.stop_btn.configure(
            state="disabled",
            text="停止",
            border_color=MaterialColors.OUTLINE,
            text_color=MaterialColors.OUTLINE
        )
        # フェーズインジケーターをリセット
        for pill, lbl in self.phase_labels:
            pill.configure(fg_color=MaterialColors.SURFACE_CONTAINER)
            lbl.configure(text_color=MaterialColors.ON_SURFACE_VARIANT)

    def on_complete(self, results, cost_tracker, csv_path, json_path, xlsx_path=None):
        self.reset_buttons()
        self.progress.set(1)

        self.cost_label.configure(text=cost_tracker.summary())
        self.update_status(f"[OK]完了! {len(results)}シーン生成")
        self.log(f"[FILE]CSV: {csv_path}")
        self.log(f"[FILE]JSON: {json_path}")
        if xlsx_path:
            self.log(f"[STAT]Excel: {xlsx_path}（折り返し表示対応）")
        self.log(f"[COST]{cost_tracker.summary()}")
        self.snackbar.show(f"{len(results)}シーン生成完了!", type="success")

        # エクスポートフォルダを開くボタンを表示
        self._show_open_folder_btn()

    def _show_open_folder_btn(self):
        """エクスポートフォルダを開くボタンをログ領域の上に表示"""
        if hasattr(self, "_open_folder_btn") and self._open_folder_btn.winfo_exists():
            self._open_folder_btn.destroy()
        self._open_folder_btn = ctk.CTkButton(
            self.log_text.master, text="エクスポートフォルダを開く",
            font=ctk.CTkFont(size=14), height=32,
            fg_color=MaterialColors.SECONDARY_CONTAINER,
            text_color=MaterialColors.ON_SECONDARY_CONTAINER,
            hover_color=MaterialColors.PRIMARY,
            corner_radius=8,
            command=self.open_export_folder
        )
        self._open_folder_btn.pack(pady=(8, 8))

    def open_export_folder(self):
        """エクスポートフォルダをエクスプローラーで開く"""
        import subprocess
        folder = str(EXPORTS_DIR)
        try:
            subprocess.Popen(["explorer", folder])
        except Exception as e:
            self.log(f"フォルダを開けません: {e}")

    def on_close(self):
        """ウィンドウ閉じ時の処理（生成中なら確認ダイアログ）"""
        if self.is_generating:
            import tkinter.messagebox as mb
            if mb.askokcancel("確認", "生成中です。停止して終了しますか？"):
                self.stop_requested = True
                self.after(500, self.destroy)
        else:
            self.destroy()

    def on_stopped(self):
        self.reset_buttons()
        self.progress.set(0)
        self.update_status("[STOP]生成を停止しました")
        self.snackbar.show("生成を停止しました", type="warning")

    def on_stopped_with_partial(self, partial_path: str, count: int):
        """中断時に部分結果を保存して通知"""
        self.reset_buttons()
        self.progress.set(0)
        self.update_status(f"[STOP]停止（{count}シーン保存済み）")
        self.log(f"[FILE]途中結果: {partial_path}")
        self.snackbar.show(f"停止（{count}シーン保存済み）", type="warning")

    def on_error(self, error: str):
        self.reset_buttons()
        self.progress.set(0)
        self.update_status(f"[ERROR]エラー: {error}")
        self.snackbar.show(f"エラー: {error[:50]}", type="error")

    def refresh_char_list(self):
        """キャラクター一覧を更新"""
        chars = get_existing_characters()
        values = ["（キャラ選択）"]
        for c in chars:
            values.append(f"{c['name']} ({c['work']})")
        self.char_select_combo.configure(values=values)
        if hasattr(self, '_char_map'):
            pass
        self._char_map = {f"{c['name']} ({c['work']})": c for c in chars}

    def on_char_selected(self, choice: str):
        """キャラ選択時のコールバック"""
        if choice == "（キャラ選択）" or choice not in self._char_map:
            return

        char_info = self._char_map[choice]
        char_id = char_info["char_id"]
        bible_path = CHARACTERS_DIR / f"{char_id}.json"

        if bible_path.exists():
            with open(bible_path, "r", encoding="utf-8") as f:
                bible = json.load(f)

            # キャラ情報を取得
            name = bible.get('character_name', '')
            work = bible.get('work_title', '')
            personality = bible.get('personality_core', {})
            speech = bible.get('speech_pattern', {})
            emotional = bible.get('emotional_speech', {})
            physical = bible.get('physical_description', {})
            tags = bible.get('danbooru_tags', [])

            # 個別フィールドに直接設定
            self._set_characters_fields({
                "name": f"{name}（{work}）" if work else name,
                "personality": personality.get('brief_description', ''),
                "first_person": speech.get('first_person', '私'),
                "endings": ', '.join(speech.get('sentence_endings', [])[:4]),
                "appearance": f"{physical.get('hair', '')}、{physical.get('eyes', '')}",
            })

            # ログに詳細なキャラ設定を出力
            self.log(f"═══ キャラ設定プレビュー: {name} ═══")
            self.log(f"作品: {work}")
            self.log(f"性格: {personality.get('brief_description', '')}")
            self.log(f"特性: {', '.join(personality.get('main_traits', []))}")
            self.log(f"一人称: {speech.get('first_person', '私')}")
            self.log(f"語尾: {', '.join(speech.get('sentence_endings', [])[:5])}")
            self.log(f"照れた時: {emotional.get('when_embarrassed', '')}")
            self.log(f"甘える時: {emotional.get('when_flirty', '')}")
            self.log(f"SDタグ: {', '.join(tags[:8])}...")
            self.log(f"═══════════════════════════════")

            self.snackbar.show(f"{name}を追加（ログに設定詳細）", type="success")

    def refresh_preset_list(self):
        """プリセット一覧を更新"""
        self._all_presets = get_preset_characters()
        self._preset_map = {}
        for p in self._all_presets:
            label = f"【{p.get('work_title', p.get('work', ''))}】{p.get('character_name', p.get('name', ''))}"
            self._preset_map[label] = p

        # Update title with count
        count = len(self._all_presets)
        if hasattr(self, '_preset_title_label'):
            self._preset_title_label.configure(text=f"プリセットキャラ（API不要・{count}体収録）")

        # Show all characters immediately
        if hasattr(self, '_category_chips') and self._category_chips:
            self._on_category_chip_click("全て")

    def on_preset_selected(self, choice: str):
        """プリセット選択時（後方互換）"""
        pass

    def load_preset_action(self):
        """プリセット読み込み（後方互換）"""
        pass

    def save_custom_character(self):
        """オリジナルキャラクターを保存"""
        name = self.custom_name_entry.get().strip()
        if not name:
            self.snackbar.show("キャラ名を入力してください", type="warning")
            return

        # shyness_levelの取得
        shyness_level = int(round(self.shyness_slider.get()))

        # その他の登場人物テキスト取得
        other_chars = ""
        if hasattr(self, "other_chars_text"):
            other_chars = self.other_chars_text.get("1.0", "end-1c").strip()

        bible = build_custom_character_data(
            char_name=name,
            age=self.custom_age_dd.get(),
            relationship=self.custom_rel_dd.get(),
            archetype=self._selected_archetype,
            first_person=self.custom_first_person_dd.get(),
            speech_style=self.custom_speech_dd.get(),
            hair_color=self._selected_hair_color,
            hair_style=self.custom_hair_style_dd.get(),
            body_type=self.custom_body_dd.get(),
            chest=self.custom_chest_dd.get(),
            clothing=self.custom_clothing_dd.get(),
            shyness_level=shyness_level,
            custom_traits=self.custom_traits_entry.get().strip(),
            other_characters=other_chars,
        )

        # char_id生成＆保存
        char_id = generate_char_id("オリジナル", name)
        bible_path = CHARACTERS_DIR / f"{char_id}.json"
        skill_path = CHAR_SKILLS_DIR / f"{char_id}.skill.md"

        with open(bible_path, "w", encoding="utf-8") as f:
            json.dump(bible, f, ensure_ascii=False, indent=2)

        skill_content = generate_character_skill(char_id, bible)
        with open(skill_path, "w", encoding="utf-8") as f:
            f.write(skill_content)

        self.refresh_char_list()
        self.log(f"[OK]オリジナルキャラ保存: {name} ({self._selected_archetype})")
        self.log(f"   性格: {bible['personality_core']['brief_description']}")
        self.log(f"   一人称: {bible['speech_pattern']['first_person']} / 口調: {self.custom_speech_dd.get()}")
        self.log(f"   外見: {bible['physical_description']['hair']}")
        self.snackbar.show(f"{name}を保存しました（API未使用）", type="success")

    # ======== Preset Tab Methods ========

    def _build_preset_tab(self, parent):
        """プリセットタブUIを構築"""
        # Title with dynamic count
        title_row = ctk.CTkFrame(parent, fg_color="transparent")
        title_row.pack(fill="x", padx=16, pady=(12, 8))

        self._preset_title_label = ctk.CTkLabel(
            title_row, text="プリセットキャラ（API不要・0体収録）",
            font=ctk.CTkFont(family=FONT_JP, size=16, weight="bold"),
            text_color=MaterialColors.ON_SURFACE
        )
        self._preset_title_label.pack(side="left")

        # Category chip row
        chip_frame = ctk.CTkFrame(parent, fg_color="transparent")
        chip_frame.pack(fill="x", padx=16, pady=(0, 8))

        categories = ["全て", "ジャンプ", "マガジン", "ラノベ", "アニメ", "ソシャゲ", "ゲーム", "サンデー", "VTuber"]
        self._category_map = {
            "全て": None,
            "ジャンプ": ["ジャンプ", "ジャンプ+"],
            "マガジン": ["マガジン"],
            "ラノベ": ["ラノベ"],
            "アニメ": ["アニメ"],
            "ソシャゲ": ["ソーシャルゲーム"],
            "ゲーム": ["ゲーム"],
            "サンデー": ["サンデー"],
            "VTuber": ["VTuber"],
        }

        for cat in categories:
            chip = MaterialChip(
                chip_frame, text=cat,
                selected=(cat == "全て"),
                chip_type="filter",
                command=lambda c=cat: self._on_category_chip_click(c)
            )
            chip.pack(side="left", padx=(0, 6))
            self._category_chips[cat] = chip

        # Work filter dropdown (optional narrowing)
        filter_row = ctk.CTkFrame(parent, fg_color="transparent")
        filter_row.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            filter_row, text="作品で絞り込み:",
            font=ctk.CTkFont(family=FONT_JP, size=13),
            text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left", padx=(0, 6))

        self._work_dropdown = ctk.CTkOptionMenu(
            filter_row, values=["（すべて表示）"],
            command=self._on_work_selected,
            font=ctk.CTkFont(family=FONT_JP, size=14), width=300,
            fg_color=MaterialColors.SURFACE_CONTAINER,
            button_color=MaterialColors.PRIMARY,
            text_color=MaterialColors.ON_SURFACE,
            dropdown_text_color=MaterialColors.ON_SURFACE,
            dropdown_fg_color=MaterialColors.SURFACE
        )
        self._work_dropdown.pack(side="left")

        # Character card scroll area
        self._preset_card_frame = ctk.CTkScrollableFrame(
            parent, fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST,
            height=260, corner_radius=8
        )
        self._preset_card_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Placeholder text
        self._preset_placeholder = ctk.CTkLabel(
            self._preset_card_frame,
            text="カテゴリを選択してください",
            font=ctk.CTkFont(family=FONT_JP, size=14),
            text_color=MaterialColors.ON_SURFACE_VARIANT
        )
        self._preset_placeholder.pack(pady=20)

    def _on_category_chip_click(self, category):
        """カテゴリチップ選択→キャラ一覧を即座に表示"""
        # Toggle chips (exclusive selection)
        for cat, chip in self._category_chips.items():
            if cat == category:
                if not chip.selected:
                    chip.toggle()
            else:
                if chip.selected:
                    chip.toggle()
        self._selected_category = category

        # Filter by category
        cat_filters = self._category_map.get(category)
        if cat_filters is None:
            filtered = self._all_presets
        else:
            filtered = [p for p in self._all_presets if p.get("category", "") in cat_filters]

        # Update work dropdown with available works
        seen = set()
        works = []
        for p in filtered:
            wt = p.get("work_title", p.get("work", ""))
            if wt not in seen:
                seen.add(wt)
                works.append(wt)

        values = ["（すべて表示）"] + works
        self._work_dropdown.configure(values=values)
        self._work_dropdown.set("（すべて表示）")

        # Show all characters grouped by work
        self._render_preset_list(filtered)

        # キャラリストを先頭にスクロール
        if self._preset_card_frame:
            try:
                self._preset_card_frame._parent_canvas.yview_moveto(0)
            except Exception:
                pass

    def _on_work_selected(self, work_title):
        """作品選択→キャラカード表示（絞り込み）"""
        cat_filters = self._category_map.get(self._selected_category)

        if work_title == "（すべて表示）":
            if cat_filters is None:
                filtered = self._all_presets
            else:
                filtered = [p for p in self._all_presets if p.get("category", "") in cat_filters]
        else:
            filtered = []
            for p in self._all_presets:
                wt = p.get("work_title", p.get("work", ""))
                cat = p.get("category", "")
                if wt == work_title:
                    if cat_filters is None or cat in cat_filters:
                        filtered.append(p)

        self._render_preset_list(filtered)

    def _render_char_card(self, preset_info):
        """キャラカードを描画（リッチ版）"""
        card = ctk.CTkFrame(
            self._preset_card_frame,
            fg_color=MaterialColors.SURFACE_CONTAINER_LOW,
            corner_radius=10, height=56
        )
        card.pack(fill="x", pady=(0, 6), padx=12)
        card.pack_propagate(False)

        name = preset_info.get("character_name", preset_info.get("name", ""))
        work = preset_info.get("work_title", preset_info.get("work", ""))
        category = preset_info.get("category", "")

        # Left accent bar based on category
        cat_colors = {
            "ジャンプ": "#E85D3A", "ジャンプ+": "#E85D3A",
            "マガジン": "#3A8FE8", "ラノベ": "#8F5FD6",
            "アニメ": "#40B080", "ソーシャルゲーム": "#E8A83A",
            "ゲーム": "#6B8E23", "サンデー": "#FF8C00",
            "VTuber": "#E84F8A",
        }
        accent = cat_colors.get(category, MaterialColors.PRIMARY)

        accent_bar = ctk.CTkFrame(card, fg_color=accent, width=4, corner_radius=2)
        accent_bar.pack(side="left", fill="y", padx=(0, 0), pady=6)

        # Name (bold)
        ctk.CTkLabel(
            card, text=name,
            font=ctk.CTkFont(family=FONT_JP, size=16, weight="bold"),
            text_color=MaterialColors.ON_SURFACE
        ).pack(side="left", padx=(12, 8), pady=8)

        # Work title (smaller, muted)
        ctk.CTkLabel(
            card, text=work,
            font=ctk.CTkFont(family=FONT_JP, size=13),
            text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left", padx=(0, 12), pady=8)

        # Load button
        MaterialButton(
            card, text="読み込み", variant="filled_tonal", size="small",
            command=lambda p=preset_info: self._load_preset_direct(p)
        ).pack(side="right", padx=(0, 12), pady=10)

    def _render_preset_list(self, presets):
        """プリセット一覧を作品グループごとに描画"""
        self._clear_preset_cards()

        if not presets:
            self._preset_placeholder.pack(pady=20)
            self._preset_placeholder.configure(text="キャラが見つかりません")
            return

        self._preset_placeholder.pack_forget()

        # Group by work title (dict preserves insertion order in Python 3.7+)
        groups = {}
        for p in presets:
            wt = p.get("work_title", p.get("work", ""))
            if wt not in groups:
                groups[wt] = []
            groups[wt].append(p)

        for work_title, chars in groups.items():
            # Work title header
            header = ctk.CTkFrame(
                self._preset_card_frame, fg_color="transparent", height=28
            )
            header.pack(fill="x", padx=12, pady=(12, 4))
            header.pack_propagate(False)

            ctk.CTkLabel(
                header, text=f"  {work_title}  ({len(chars)})",
                font=ctk.CTkFont(family=FONT_JP, size=14, weight="bold"),
                text_color=MaterialColors.PRIMARY
            ).pack(side="left")

            # Divider line
            divider = ctk.CTkFrame(
                self._preset_card_frame,
                fg_color=MaterialColors.OUTLINE_VARIANT, height=1
            )
            divider.pack(fill="x", padx=16, pady=(0, 6))

            for ch in chars:
                self._render_char_card(ch)

    def _clear_preset_cards(self):
        """プリセットカードをクリア"""
        for widget in self._preset_card_frame.winfo_children():
            if widget != self._preset_placeholder:
                widget.destroy()
        try:
            self._preset_placeholder.pack_forget()
        except:
            pass

    def _setup_nested_scroll(self):
        """ネストされたスクロール領域のスムーズスクロール制御

        1. 全CTkScrollableFrameの内部MouseWheelバインドを無効化
        2. winfo_containingベースでスクロール先を判定
        3. ピクセル単位の慣性アニメーションでスムーズに移動
        4. 内側フレーム端到達時にメインへバブルアップ
        """
        inner_frames = []
        for frame in [
            getattr(self, '_preset_card_frame', None),
        ]:
            if frame:
                inner_frames.append(frame)

        # 全CTkScrollableFrameの内部バインドを無効化
        all_frames = [self.main_container] + inner_frames
        for frame in all_frames:
            try:
                frame.unbind("<MouseWheel>")
            except Exception:
                pass
            try:
                frame._parent_canvas.unbind("<MouseWheel>")
            except Exception:
                pass

        # スムーズスクロール用の状態
        self._scroll_velocity = 0.0
        self._scroll_target_frame = None
        self._scroll_animating = False

        PIXELS_PER_NOTCH = 45
        FRICTION = 0.65
        FRAME_MS = 12
        MIN_VELOCITY = 0.5

        def _find_inner_ancestor(widget):
            """ウィジェットの祖先を辿り、内側CTkScrollableFrameを見つける"""
            w = widget
            depth = 0
            while w is not None and depth < 50:
                for inner in inner_frames:
                    if w is inner:
                        return inner
                try:
                    w = w.master
                except Exception:
                    break
                depth += 1
            return None

        def _can_scroll(frame, direction):
            """フレームがその方向にスクロール可能かチェック"""
            try:
                canvas = frame._parent_canvas
                top, bottom = canvas.yview()
                if direction < 0 and top <= 0.001:
                    return False
                if direction > 0 and bottom >= 0.999:
                    return False
                return True
            except Exception:
                return False

        def _scroll_pixels(frame, pixels):
            """フレームをピクセル単位でスクロール"""
            try:
                canvas = frame._parent_canvas
                scroll_region = canvas.cget("scrollregion")
                if scroll_region:
                    parts = scroll_region.split()
                    total_height = float(parts[3]) - float(parts[1])
                else:
                    total_height = canvas.winfo_height()
                if total_height <= 0:
                    return
                fraction = pixels / total_height
                current = canvas.yview()[0]
                new_pos = max(0.0, min(1.0, current + fraction))
                canvas.yview_moveto(new_pos)
            except Exception:
                pass

        def _animate_scroll():
            """慣性スクロールアニメーション"""
            if not self._scroll_animating:
                return
            if abs(self._scroll_velocity) < MIN_VELOCITY:
                self._scroll_velocity = 0.0
                self._scroll_animating = False
                return

            frame = self._scroll_target_frame
            if frame is None:
                self._scroll_animating = False
                return

            direction = 1 if self._scroll_velocity > 0 else -1

            # 内側フレームの端到達時にメインへバブルアップ
            if frame is not self.main_container and not _can_scroll(frame, direction):
                self._scroll_target_frame = self.main_container
                frame = self.main_container

            _scroll_pixels(frame, self._scroll_velocity)
            self._scroll_velocity *= FRICTION
            self.after(FRAME_MS, _animate_scroll)

        def _on_mousewheel(event):
            """マウスホイールイベント → 慣性スクロール開始"""
            raw_delta = -event.delta / 120.0
            impulse = raw_delta * PIXELS_PER_NOTCH

            try:
                x, y = self.winfo_pointerxy()
                widget = self.winfo_containing(x, y)
            except Exception:
                return "break"

            if widget is None:
                return "break"

            inner = _find_inner_ancestor(widget)
            direction = 1 if impulse > 0 else -1

            if inner is not None and _can_scroll(inner, direction):
                target = inner
            else:
                target = self.main_container

            # 速度加算（連続ホイールで加速、方向転換時はリセット）
            if self._scroll_target_frame is not target:
                self._scroll_velocity = impulse
            elif (self._scroll_velocity > 0) != (impulse > 0):
                self._scroll_velocity = impulse
            else:
                self._scroll_velocity += impulse

            self._scroll_target_frame = target

            if not self._scroll_animating:
                self._scroll_animating = True
                _animate_scroll()

            return "break"

        self.bind_all("<MouseWheel>", _on_mousewheel)

    def _on_work_type_changed(self):
        """ラジオボタン切替で表示コンテナを切替"""
        is_preset = self.work_type_var.get() == "二次創作"
        if is_preset:
            self._custom_container.pack_forget()
            self._preset_container.pack(fill="x", padx=16, pady=(0, 10),
                                        before=self._char_select_row)
        else:
            self._preset_container.pack_forget()
            self._custom_container.pack(fill="x", padx=16, pady=(0, 10),
                                        before=self._char_select_row)

    def _build_api_section(self, parent):
        """API生成セクションを構築（カスタムコンテナ内）"""
        api_card = MaterialCard(parent, title="API キャラ生成", variant="outlined")
        api_card.pack(fill="x", padx=12, pady=(12, 12))

        api_inner = ctk.CTkFrame(api_card, fg_color="transparent")
        api_inner.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkLabel(
            api_inner, text="Claude APIでキャラクター分析（Sonnet使用）",
            font=ctk.CTkFont(size=14),
            text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(anchor="w", pady=(0, 4))

        api_char_row = ctk.CTkFrame(api_inner, fg_color="transparent")
        api_char_row.pack(fill="x", pady=(0, 8))

        work_frame = ctk.CTkFrame(api_char_row, fg_color="transparent")
        work_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(work_frame, text="作品名", font=ctk.CTkFont(size=13),
                    text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w")
        self.work_title_entry = ctk.CTkEntry(
            work_frame, height=38, placeholder_text="例: 五等分の花嫁",
            font=ctk.CTkFont(size=15), fg_color=MaterialColors.SURFACE_CONTAINER,
            text_color=MaterialColors.ON_SURFACE,
            corner_radius=6, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT
        )
        self.work_title_entry.pack(fill="x", pady=(3, 0))

        char_name_frame = ctk.CTkFrame(api_char_row, fg_color="transparent")
        char_name_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(char_name_frame, text="キャラ名", font=ctk.CTkFont(size=13),
                    text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w")
        self.char_name_entry = ctk.CTkEntry(
            char_name_frame, height=38, placeholder_text="例: 中野一花",
            font=ctk.CTkFont(size=15), fg_color=MaterialColors.SURFACE_CONTAINER,
            text_color=MaterialColors.ON_SURFACE,
            corner_radius=6, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT
        )
        self.char_name_entry.pack(fill="x", pady=(3, 0))

        self.char_generate_btn = ctk.CTkButton(
            api_inner, text="キャラ生成（API使用）", height=36,
            font=ctk.CTkFont(size=14, weight="bold"), corner_radius=6,
            fg_color=MaterialColors.PRIMARY, hover_color=MaterialColors.PRIMARY_VARIANT,
            command=self.start_char_generation
        )
        self.char_generate_btn.pack(anchor="w", pady=(0, 8))

    def _load_preset_direct(self, preset_info):
        """ワンクリックでプリセット読み込み"""
        char_id = preset_info["char_id"]
        try:
            bible, _ = load_preset_character(char_id, callback=lambda msg: self.log(msg))
            self.refresh_char_list()
            name = bible.get("character_name", char_id)
            work = preset_info.get("work_title", "")
            # Also populate work/char fields in API tab
            self.work_title_entry.delete(0, "end")
            self.work_title_entry.insert(0, work)
            self.char_name_entry.delete(0, "end")
            self.char_name_entry.insert(0, name)
            self.snackbar.show(f"{name}を読み込みました", type="success")
        except Exception as e:
            self.snackbar.show(f"読み込みエラー: {e}", type="error")

    # ======== Custom Character Tab Methods ========

    def _build_custom_tab(self, parent):
        """オリジナル作成タブUIを構築"""
        custom_scroll = ctk.CTkFrame(
            parent, fg_color="transparent"
        )
        custom_scroll.pack(fill="x")
        self._custom_scroll = custom_scroll

        # Helper for dropdowns
        def add_dropdown(p, label, options, default=None):
            ctk.CTkLabel(p, text=label, font=ctk.CTkFont(family=FONT_JP, size=13, weight="bold"),
                        text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w", pady=(6,0))
            dd = ctk.CTkOptionMenu(p, values=options, font=ctk.CTkFont(family=FONT_JP, size=14),
                                   width=350, fg_color=MaterialColors.SURFACE_CONTAINER,
                                   button_color=MaterialColors.PRIMARY,
                                   text_color=MaterialColors.ON_SURFACE,
                                   dropdown_text_color=MaterialColors.ON_SURFACE,
                                   dropdown_fg_color=MaterialColors.SURFACE)
            dd.pack(anchor="w", pady=(2, 0))
            if default:
                dd.set(default)
            return dd

        # === Template Quick Start (20種) ===
        tmpl_label = ctk.CTkLabel(custom_scroll, text="テンプレート（ワンクリック雛形）— FANZA売れ筋20種",
                    font=ctk.CTkFont(family=FONT_JP, size=14, weight="bold"),
                    text_color=MaterialColors.PRIMARY)
        tmpl_label.pack(anchor="w", pady=(8, 8))

        templates = {
            # 学園系
            "JKツンデレ": {"age": "JK（女子高生）", "archetype": "ツンデレ", "first_person": "あたし",
                         "speech": "タメ口", "hair_color": "金髪", "hair_style": "ツインテール",
                         "body": "普通", "chest": "大きめ（D-E）", "clothing": "制服（ブレザー）", "shyness": 4},
            "ギャルJK": {"age": "JK（女子高生）", "archetype": "ギャル", "first_person": "ウチ",
                        "speech": "ギャル語", "hair_color": "金髪", "hair_style": "ロングウェーブ",
                        "body": "グラマー", "chest": "大きめ（D-E）", "clothing": "制服（ブレザー）", "shyness": 1},
            "地味子": {"age": "JK（女子高生）", "archetype": "真面目・優等生", "first_person": "私",
                      "speech": "丁寧語", "hair_color": "黒髪", "hair_style": "三つ編み",
                      "body": "小柄・華奢", "chest": "控えめ（A-B）", "clothing": "制服（ブレザー）", "shyness": 5},
            "委員長": {"age": "JK（女子高生）", "archetype": "真面目・優等生", "first_person": "私",
                      "speech": "丁寧語", "hair_color": "黒髪", "hair_style": "ロングストレート",
                      "body": "スレンダー", "chest": "大きめ（D-E）", "clothing": "制服（セーラー服）", "shyness": 4},
            # 純情系
            "甘え妹": {"age": "JK（女子高生）", "archetype": "妹系・甘えん坊", "first_person": "私",
                      "speech": "タメ口", "hair_color": "茶髪", "hair_style": "ツインテール",
                      "body": "小柄・華奢", "chest": "控えめ（A-B）", "clothing": "パジャマ・部屋着", "shyness": 4},
            "後輩マネ": {"age": "JK（女子高生）", "archetype": "元気っ子", "first_person": "私",
                        "speech": "丁寧語", "hair_color": "茶髪", "hair_style": "ポニーテール",
                        "body": "普通", "chest": "普通（C）", "clothing": "体操着・ブルマ", "shyness": 4},
            "メイドさん": {"age": "JD（女子大生）", "archetype": "妹系・甘えん坊", "first_person": "私",
                         "speech": "丁寧語", "hair_color": "黒髪", "hair_style": "ツインテール",
                         "body": "小柄・華奢", "chest": "普通（C）", "clothing": "メイド服", "shyness": 3},
            "巫女さん": {"age": "JD（女子大生）", "archetype": "大和撫子", "first_person": "私",
                        "speech": "古風・時代劇調", "hair_color": "黒髪", "hair_style": "姫カット",
                        "body": "スレンダー", "chest": "普通（C）", "clothing": "巫女服", "shyness": 4},
            # 年上系
            "大人クール": {"age": "OL（20代）", "archetype": "クーデレ", "first_person": "私",
                         "speech": "丁寧語", "hair_color": "黒髪", "hair_style": "ロングストレート",
                         "body": "スレンダー", "chest": "普通（C）", "clothing": "スーツ", "shyness": 2},
            "女教師": {"age": "OL（20代）", "archetype": "真面目・優等生", "first_person": "私",
                      "speech": "敬語（ビジネス）", "hair_color": "黒髪", "hair_style": "ポニーテール",
                      "body": "スレンダー", "chest": "大きめ（D-E）", "clothing": "スーツ", "shyness": 3},
            "ナース": {"age": "OL（20代）", "archetype": "お姉さん系", "first_person": "私",
                      "speech": "丁寧語", "hair_color": "茶髪", "hair_style": "ボブカット",
                      "body": "グラマー", "chest": "巨乳（F以上）", "clothing": "ナース服", "shyness": 3},
            "未亡人": {"age": "お姉さん（30代）", "archetype": "クーデレ", "first_person": "私",
                      "speech": "丁寧語", "hair_color": "黒髪", "hair_style": "ロングストレート",
                      "body": "グラマー", "chest": "大きめ（D-E）", "clothing": "着物・浴衣", "shyness": 4},
            # 個性派
            "お嬢様": {"age": "JD（女子大生）", "archetype": "お嬢様", "first_person": "わたくし",
                      "speech": "お嬢様言葉", "hair_color": "金髪", "hair_style": "ロングウェーブ",
                      "body": "グラマー", "chest": "大きめ（D-E）", "clothing": "ドレス", "shyness": 3},
            "エルフ姫": {"age": "エルフ・長命種", "archetype": "お嬢様", "first_person": "わたくし",
                        "speech": "古風・時代劇調", "hair_color": "銀髪", "hair_style": "ロングストレート",
                        "body": "スレンダー", "chest": "普通（C）", "clothing": "ドレス", "shyness": 3},
            "褐色スポーツ": {"age": "JK（女子高生）", "archetype": "元気っ子", "first_person": "あたし",
                           "speech": "タメ口", "hair_color": "茶髪", "hair_style": "ショートヘア",
                           "body": "筋肉質", "chest": "普通（C）", "clothing": "体操着・ブルマ", "shyness": 2},
            "バニーガール": {"age": "JD（女子大生）", "archetype": "小悪魔", "first_person": "あたし",
                           "speech": "タメ口", "hair_color": "金髪", "hair_style": "ポニーテール",
                           "body": "グラマー", "chest": "巨乳（F以上）", "clothing": "バニーガール", "shyness": 1},
            # NTR/人妻系
            "NTR彼女": {"age": "JD（女子大生）", "archetype": "天然・ドジっ子", "first_person": "私",
                        "speech": "タメ口", "hair_color": "茶髪", "hair_style": "ロングストレート",
                        "body": "普通", "chest": "大きめ（D-E）", "clothing": "私服（清楚系）", "shyness": 4},
            "人妻さん": {"age": "人妻", "archetype": "お姉さん系", "first_person": "私",
                        "speech": "丁寧語", "hair_color": "茶髪", "hair_style": "セミロング",
                        "body": "グラマー", "chest": "大きめ（D-E）", "clothing": "エプロン", "shyness": 4},
            "義母さん": {"age": "お姉さん（30代）", "archetype": "大和撫子", "first_person": "私",
                        "speech": "丁寧語", "hair_color": "黒髪", "hair_style": "ロングストレート",
                        "body": "グラマー", "chest": "巨乳（F以上）", "clothing": "着物・浴衣", "shyness": 4},
            "メスガキ": {"age": "ロリ", "archetype": "小悪魔", "first_person": "あたし",
                        "speech": "タメ口", "hair_color": "ピンク髪", "hair_style": "ツインテール",
                        "body": "小柄・華奢", "chest": "控えめ（A-B）", "clothing": "私服（ギャル系）", "shyness": 1},
        }
        self._custom_templates = templates

        # カテゴリ別テンプレートグリッド (5行×4列)
        tmpl_categories = [
            ("学園系", ["JKツンデレ", "ギャルJK", "地味子", "委員長"]),
            ("純情系", ["甘え妹", "後輩マネ", "メイドさん", "巫女さん"]),
            ("年上系", ["大人クール", "女教師", "ナース", "未亡人"]),
            ("個性派", ["お嬢様", "エルフ姫", "褐色スポーツ", "バニーガール"]),
            ("NTR/人妻", ["NTR彼女", "人妻さん", "義母さん", "メスガキ"]),
        ]

        tmpl_grid = ctk.CTkFrame(custom_scroll, fg_color="transparent")
        tmpl_grid.pack(fill="x", pady=(0, 12))

        for row_idx, (cat_name, cat_templates) in enumerate(tmpl_categories):
            row_frame = ctk.CTkFrame(
                tmpl_grid, fg_color=MaterialColors.SURFACE_CONTAINER_LOW,
                corner_radius=8
            )
            row_frame.pack(fill="x", pady=(0, 4))
            ctk.CTkLabel(
                row_frame, text=cat_name, width=80,
                font=ctk.CTkFont(family=FONT_JP, size=12, weight="bold"),
                text_color=MaterialColors.ON_SURFACE_VARIANT, anchor="w"
            ).grid(row=0, column=0, padx=(8, 6), pady=4, sticky="w")
            for col_idx, tname in enumerate(cat_templates):
                btn = MaterialButton(
                    row_frame, text=tname, variant="outlined", size="small",
                    width=90,
                    command=lambda t=tname: self._apply_custom_template(t)
                )
                btn.grid(row=0, column=col_idx + 1, padx=(0, 6), pady=4, sticky="w")
                t = templates[tname]
                tip = f"{t['hair_color']}{t['hair_style']} / {t['clothing']} / {t['archetype']} / 恥{t['shyness']}"
                add_tooltip(btn, tip)

        # === 基本情報 Card ===
        basic_card = MaterialCard(custom_scroll, title="基本情報", variant="outlined", collapsible=True, start_collapsed=False)
        basic_card.pack(fill="x", pady=(0, 8))
        bc = basic_card.content_frame

        ctk.CTkLabel(bc, text="キャラ名", font=ctk.CTkFont(family=FONT_JP, size=13, weight="bold"),
                    text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w", pady=(0,0))
        self.custom_name_entry = ctk.CTkEntry(
            bc, height=36, placeholder_text="例: 佐藤花子",
            font=ctk.CTkFont(family=FONT_JP, size=15), width=350,
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6,
            text_color=MaterialColors.ON_SURFACE,
            border_width=1, border_color=MaterialColors.OUTLINE_VARIANT
        )
        self.custom_name_entry.pack(anchor="w", pady=(2, 0))

        self.custom_age_dd = add_dropdown(bc, "年齢・外見", AGE_OPTIONS, "JK（女子高生）")
        self.custom_rel_dd = add_dropdown(bc, "主人公との関係", RELATIONSHIP_OPTIONS, "クラスメイト")

        # === 性格・口調 Card ===
        personality_card = MaterialCard(custom_scroll, title="性格・口調", variant="outlined", collapsible=True, start_collapsed=True)
        personality_card.pack(fill="x", pady=(0, 8))
        pc = personality_card.content_frame

        ctk.CTkLabel(pc, text="性格タイプ", font=ctk.CTkFont(family=FONT_JP, size=13, weight="bold"),
                    text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w", pady=(0, 4))

        # Archetype chip grid (4 cols x 3 rows)
        archetype_grid = ctk.CTkFrame(pc, fg_color="transparent")
        archetype_grid.pack(fill="x", pady=(0, 6))

        for i, arch in enumerate(ARCHETYPE_OPTIONS):
            chip = MaterialChip(
                archetype_grid, text=arch,
                selected=(arch == self._selected_archetype),
                chip_type="filter",
                command=lambda a=arch: self._select_archetype_chip(a)
            )
            row_num = i // 4
            col_num = i % 4
            chip.grid(row=row_num, column=col_num, padx=4, pady=4, sticky="w")
            self._archetype_chips[arch] = chip

        self.custom_first_person_dd = add_dropdown(pc, "一人称", FIRST_PERSON_OPTIONS, "あたし")
        self.custom_speech_dd = add_dropdown(pc, "口調", SPEECH_STYLE_OPTIONS, "タメ口")

        # === 外見 Card ===
        appearance_card = MaterialCard(custom_scroll, title="外見", variant="outlined", collapsible=True, start_collapsed=True)
        appearance_card.pack(fill="x", pady=(0, 8))
        ac = appearance_card.content_frame

        ctk.CTkLabel(ac, text="髪色", font=ctk.CTkFont(family=FONT_JP, size=13, weight="bold"),
                    text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w", pady=(0, 4))

        # Hair color chips
        hair_color_frame = ctk.CTkFrame(ac, fg_color="transparent")
        hair_color_frame.pack(fill="x", pady=(0, 6))

        for color in HAIR_COLOR_OPTIONS:
            chip = MaterialChip(
                hair_color_frame, text=color,
                selected=(color == self._selected_hair_color),
                chip_type="filter",
                command=lambda c=color: self._select_hair_color_chip(c)
            )
            chip.pack(side="left", padx=(0, 6), pady=4)
            self._hair_color_chips[color] = chip

        self.custom_hair_style_dd = add_dropdown(ac, "髪型", HAIR_STYLE_OPTIONS, "ロングストレート")
        self.custom_body_dd = add_dropdown(ac, "体型", BODY_TYPE_OPTIONS, "普通")
        self.custom_chest_dd = add_dropdown(ac, "胸", CHEST_OPTIONS, "普通（C）")
        self.custom_clothing_dd = add_dropdown(ac, "服装", CLOTHING_OPTIONS, "制服（ブレザー）")

        # === エロシーン設定 Card ===
        ero_card = MaterialCard(custom_scroll, title="エロシーン設定", variant="outlined", collapsible=True, start_collapsed=True)
        ero_card.pack(fill="x", pady=(0, 8))
        ec = ero_card.content_frame

        slider_row = ctk.CTkFrame(ec, fg_color="transparent")
        slider_row.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(slider_row, text="大胆",
                    font=ctk.CTkFont(family=FONT_JP, size=13),
                    text_color=MaterialColors.ON_SURFACE_VARIANT).pack(side="left", padx=(0, 8))

        self.shyness_slider = ctk.CTkSlider(
            slider_row, from_=1, to=5, number_of_steps=4,
            width=200,
            fg_color=MaterialColors.SURFACE_CONTAINER_HIGH,
            progress_color=MaterialColors.PRIMARY,
            button_color=MaterialColors.PRIMARY,
            button_hover_color=MaterialColors.PRIMARY_VARIANT
        )
        self.shyness_slider.set(3)
        self.shyness_slider.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(slider_row, text="恥ずかしがり",
                    font=ctk.CTkFont(family=FONT_JP, size=13),
                    text_color=MaterialColors.ON_SURFACE_VARIANT).pack(side="left")

        self._shyness_value_label = ctk.CTkLabel(ec, text="恥ずかしがり度: 3",
                    font=ctk.CTkFont(family=FONT_JP, size=13),
                    text_color=MaterialColors.ON_SURFACE_VARIANT)
        self._shyness_value_label.pack(anchor="w")
        self.shyness_slider.configure(command=self._on_shyness_change)

        # === 追加設定 ===
        extra_card = MaterialCard(custom_scroll, title="追加設定（任意）", variant="outlined", collapsible=True, start_collapsed=True)
        extra_card.pack(fill="x", pady=(0, 8))
        xc = extra_card.content_frame

        ctk.CTkLabel(xc, text="追加の性格特性（「、」区切り）",
                    font=ctk.CTkFont(family=FONT_JP, size=13),
                    text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w", pady=(0,0))
        self.custom_traits_entry = ctk.CTkEntry(
            xc, height=36, placeholder_text="例: 読書好き、猫が好き",
            font=ctk.CTkFont(family=FONT_JP, size=14), width=350,
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6,
            text_color=MaterialColors.ON_SURFACE,
            border_width=1, border_color=MaterialColors.OUTLINE_VARIANT
        )
        self.custom_traits_entry.pack(anchor="w", pady=(2, 0))

        # === Live Preview ===
        preview_card = MaterialCard(custom_scroll, title="プレビュー", variant="filled")
        preview_card.pack(fill="x", pady=(0, 8))
        self._custom_preview_label = ctk.CTkLabel(
            preview_card.content_frame,
            text="キャラ名を入力してください",
            font=ctk.CTkFont(family=FONT_JP, size=14),
            text_color=MaterialColors.ON_SURFACE_VARIANT,
            wraplength=380, justify="left"
        )
        self._custom_preview_label.pack(anchor="w")

        # === Save Button ===
        self.custom_save_btn = MaterialButton(
            custom_scroll, text="キャラクターを保存（API不要）",
            variant="filled", command=self.save_custom_character
        )
        self.custom_save_btn.pack(anchor="w", pady=(8, 8))

    def _select_archetype_chip(self, archetype):
        """性格タイプチップの排他選択"""
        self._selected_archetype = archetype
        for arch, chip in self._archetype_chips.items():
            if arch == archetype:
                if not chip.selected:
                    chip.toggle()
            else:
                if chip.selected:
                    chip.toggle()
        self._update_custom_preview()

    def _select_hair_color_chip(self, color):
        """髪色チップの排他選択"""
        self._selected_hair_color = color
        for c, chip in self._hair_color_chips.items():
            if c == color:
                if not chip.selected:
                    chip.toggle()
            else:
                if chip.selected:
                    chip.toggle()
        self._update_custom_preview()

    def _on_shyness_change(self, value):
        """恥ずかしがり度スライダー変更"""
        v = int(round(value))
        labels = {1: "大胆・積極的", 2: "やや積極的", 3: "普通", 4: "恥ずかしがり", 5: "超恥ずかしがり"}
        self._shyness_value_label.configure(text=f"恥ずかしがり度: {v} - {labels.get(v, '')}")
        self._update_custom_preview()

    def _update_custom_preview(self, *args):
        """ライブプレビュー更新"""
        name = self.custom_name_entry.get().strip() if hasattr(self, 'custom_name_entry') else ""
        if not name:
            name = "（未入力）"
        age = self.custom_age_dd.get() if hasattr(self, 'custom_age_dd') else ""
        archetype = self._selected_archetype
        hair_color = self._selected_hair_color
        hair_style = self.custom_hair_style_dd.get() if hasattr(self, 'custom_hair_style_dd') else ""
        chest = self.custom_chest_dd.get() if hasattr(self, 'custom_chest_dd') else ""
        clothing = self.custom_clothing_dd.get() if hasattr(self, 'custom_clothing_dd') else ""
        shyness = int(round(self.shyness_slider.get())) if hasattr(self, 'shyness_slider') else 3

        preview = f"{name} / {age} / {archetype} / {hair_color}{hair_style} / {chest} / {clothing} / 恥度{shyness}"
        if hasattr(self, '_custom_preview_label'):
            self._custom_preview_label.configure(text=preview)

    def _apply_custom_template(self, template_name):
        """テンプレート適用"""
        t = self._custom_templates.get(template_name, {})
        if not t:
            return

        # Set age
        if hasattr(self, 'custom_age_dd'):
            self.custom_age_dd.set(t.get("age", "JK（女子高生）"))
        # Set archetype
        self._select_archetype_chip(t.get("archetype", "ツンデレ"))
        # Set first person
        if hasattr(self, 'custom_first_person_dd'):
            self.custom_first_person_dd.set(t.get("first_person", "私"))
        # Set speech
        if hasattr(self, 'custom_speech_dd'):
            self.custom_speech_dd.set(t.get("speech", "タメ口"))
        # Set hair color
        self._select_hair_color_chip(t.get("hair_color", "黒髪"))
        # Set hair style
        if hasattr(self, 'custom_hair_style_dd'):
            self.custom_hair_style_dd.set(t.get("hair_style", "ロングストレート"))
        # Set body
        if hasattr(self, 'custom_body_dd'):
            self.custom_body_dd.set(t.get("body", "普通"))
        # Set chest
        if hasattr(self, 'custom_chest_dd'):
            self.custom_chest_dd.set(t.get("chest", "普通（C）"))
        # Set clothing
        if hasattr(self, 'custom_clothing_dd'):
            self.custom_clothing_dd.set(t.get("clothing", "制服（ブレザー）"))
        # Set shyness
        if hasattr(self, 'shyness_slider'):
            self.shyness_slider.set(t.get("shyness", 3))
            self._on_shyness_change(t.get("shyness", 3))

        self._update_custom_preview()
        self.snackbar.show(f"テンプレート「{template_name}」を適用", type="info")

    def start_char_generation(self):
        """キャラクター生成開始"""
        if self.is_generating:
            self.snackbar.show("生成中です", type="warning")
            return

        api_key = self.api_field.get().strip()

        work_title = self.work_title_entry.get().strip()
        char_name = self.char_name_entry.get().strip()

        if not api_key:
            self.snackbar.show("Anthropic APIキーを入力してください", type="error")
            return
        if not work_title:
            self.snackbar.show("作品名を入力してください", type="error")
            return
        if not char_name:
            self.snackbar.show("キャラクター名を入力してください", type="error")
            return

        self.is_generating = True
        self.char_generate_btn.configure(state="disabled", text="生成中...")
        self.progress.set(0)

        thread = threading.Thread(
            target=self.run_char_generation,
            args=(api_key, work_title, char_name),
            daemon=True
        )
        thread.start()

    def run_char_generation(self, api_key: str, work_title: str, char_name: str):
        """キャラクター生成スレッド"""
        try:
            def callback(msg):
                self.after(0, lambda: self.update_status(msg))

            bible, char_id, cost_tracker = build_character(
                api_key, work_title, char_name,
                force_refresh=False,
                callback=callback,
            )

            self.after(0, lambda: self.on_char_complete(bible, char_id, cost_tracker))

        except Exception as e:
            self.after(0, lambda: self.on_char_error(str(e)))

    def on_char_complete(self, bible: dict, char_id: str, cost_tracker: CostTracker):
        """キャラ生成完了"""
        self.is_generating = False
        self.char_generate_btn.configure(state="normal", text="キャラ生成")
        self.progress.set(1)

        self.cost_label.configure(text=cost_tracker.summary())
        self.update_status(f"[OK]キャラ生成完了: {char_id}")
        self.log(f"[FILE]Bible: characters/{char_id}.json")
        self.log(f"[FILE]Skill: skills/characters/{char_id}.skill.md")
        self.snackbar.show(f"{bible.get('character_name', '')} 生成完了!", type="success")

        # キャラ一覧を更新
        self.refresh_char_list()

    def on_char_error(self, error: str):
        """キャラ生成エラー"""
        self.is_generating = False
        self.char_generate_btn.configure(state="normal", text="キャラ生成")
        self.progress.set(0)
        self.update_status(f"[ERROR]エラー: {error}")
        self.snackbar.show(f"エラー: {error[:50]}", type="error")


if __name__ == "__main__":
    app = App()
    app.mainloop()
