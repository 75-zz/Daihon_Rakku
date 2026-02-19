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
import random
import threading
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

import tkinter as tk
import customtkinter as ctk

# Excel出力用（オプション）
try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

# PNG Info読み取り用（オプション）
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ドラッグ&ドロップ用（オプション）
try:
    import windnd
    WINDND_AVAILABLE = True
except ImportError:
    WINDND_AVAILABLE = False

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
from schema_validator import (
    validate_context, validate_outline, validate_scene, validate_results
)
from concept_presets import CONCEPT_PRESETS

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
    DOWNLOAD = "\uf019"
    FILE_EXPORT = "\uf56e"
    PALETTE = "\uf53f"
    IMAGE = "\uf03e"


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
    Neutral Gray + Blue Accent palette
    Clean, minimal, professional (Notion/Linear/Figma inspired)
    """

    # === M3 Tonal Palette (Neutral Gray seed + Blue accent) ===
    # Primary — Clean blue for primary actions
    PRIMARY = "#3B82F6"           # Blue-500
    PRIMARY_CONTAINER = "#EFF6FF" # Blue-50
    ON_PRIMARY = "#FFFFFF"
    ON_PRIMARY_CONTAINER = "#1A1A1A"  # Near-black

    # Secondary — Neutral gray
    SECONDARY = "#5C5C5C"         # Medium gray
    SECONDARY_CONTAINER = "#E0E0E0"   # Light gray
    ON_SECONDARY = "#FFFFFF"
    ON_SECONDARY_CONTAINER = "#1C1C1C"  # Near-black

    # Tertiary — Teal accent for variety
    TERTIARY = "#0D9488"          # Teal-600
    TERTIARY_CONTAINER = "#CCFBF1"    # Teal-100

    # Error
    ERROR = "#DC2626"             # Red-600
    ERROR_CONTAINER = "#FEE2E2"   # Red-100
    ON_ERROR = "#FFFFFF"

    # Success (Extended)
    SUCCESS = "#16A34A"           # Green-600
    SUCCESS_CONTAINER = "#DCFCE7" # Green-100

    # === Surface Tones (Pure Neutral R=G=B — zero color cast) ===
    BACKGROUND = "#FAFAFA"        # Near-white warm neutral
    SURFACE = "#FAFAFA"           # Match background
    SURFACE_DIM = "#C2C2C2"       # Dimmed surface
    SURFACE_BRIGHT = "#FAFAFA"
    SURFACE_CONTAINER_LOWEST = "#FFFFFF"   # Pure white — cards, dialogs
    SURFACE_CONTAINER_LOW = "#F5F5F5"      # Subtle elevation step
    SURFACE_CONTAINER = "#EEEEEE"          # Medium elevation — input bg
    SURFACE_CONTAINER_HIGH = "#E0E0E0"     # Higher elevation
    SURFACE_CONTAINER_HIGHEST = "#D6D6D6"  # Highest — section headers

    # On Surface — High contrast text
    ON_BACKGROUND = "#1A1A1A"     # Near black
    ON_SURFACE = "#1A1A1A"        # Near black for readability
    ON_SURFACE_VARIANT = "#525252"    # Secondary/hint/placeholder (7.8:1 on white)

    # Outline — WCAG 1.4.11 non-text contrast compliant
    OUTLINE = "#757575"           # Input borders (4.6:1 on white)
    OUTLINE_VARIANT = "#8E8E8E"   # Card borders, dividers (3.3:1 on white)

    # Inverse
    INVERSE_SURFACE = "#2D2D2D"   # Dark bg for snackbar, tooltips
    INVERSE_ON_SURFACE = "#F0F0F0"
    INVERSE_PRIMARY = "#93C5FD"   # Blue-300 for dark surface accent

    # Scrim & Shadow
    SCRIM = "#000000"
    SHADOW = "#000000"

    # === Legacy aliases for compatibility ===
    SURFACE_VARIANT = SURFACE_CONTAINER
    PRIMARY_VARIANT = "#2563EB"   # Blue-600 (hover)
    PRIMARY_LIGHT = INVERSE_PRIMARY
    ACCENT = TERTIARY
    ACCENT_VARIANT = "#5EEAD4"    # Teal-300
    ACCENT_DARK = "#0F766E"       # Teal-700
    WARNING = "#D97706"           # Amber-600
    SURFACE_DARK = INVERSE_SURFACE
    ON_DARK = INVERSE_ON_SURFACE
    ON_ACCENT = ON_PRIMARY


# === 設定 ===
MAX_RETRIES = 3
MAX_RETRIES_OVERLOADED = 6  # 529 Overloaded専用（長時間待機）
RETRY_DELAY = 2
RETRY_DELAY_OVERLOADED = 15  # 529 Overloaded初回待機秒数
CONCURRENT_BATCH_SIZE = 5       # Wave内同時生成数
CONCURRENT_MIN_SCENES = 13      # 並列化の最小シーン数
CONCURRENT_WAVE_COOLDOWN = 2.0  # Wave間クールダウン(秒)
OUTPUT_DIR = Path(__file__).parent
SKILLS_DIR = OUTPUT_DIR / "skills"
JAILBREAK_FILE = OUTPUT_DIR / "jailbreak.md"
DANBOORU_TAGS_JSON = OUTPUT_DIR / "danbooru_tags.json"
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
    "haiku": "claude-haiku-4-5-20251001",        # 高品質（複雑タスク用）
    "haiku_fast": "claude-3-haiku-20240307",      # 低コスト（シンプルタスク用: 4x安い）
    "sonnet": "claude-sonnet-4-20250514",         # プレミアム（最重要シーン用）
}

# コスト（USD per 1M tokens）
COSTS = {
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
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
    "異世界・ファンタジー": "isekai",
    "温泉・お風呂": "onsen",
    "睡眠・夜這い": "sleep",
    "輪姦・集団": "gangbang",
    "医療・診察": "medical",
    "水着・プール": "swimsuit",
    "スポーツ・部活": "sports",
    "アイドル・芸能": "idol",
    "隣人・日常": "neighbor",
    "風俗・パパ活": "prostitution",
    "露出・盗撮": "voyeur",
    "触手": "tentacle",
    "逆レイプ": "reverse_rape",
    "コスプレ・撮影": "cosplay",
}
_THEME_KEY_TO_JP = {v: k for k, v in THEME_OPTIONS.items() if v}

# 男性キャラクター プリセット
MALE_PRESETS = {
    "おまかせ": "",
    "筋肉質の青年": "muscular_male, young_man, short_hair, toned_body, 1boy",
    "小太りの中年": "fat_man, middle_aged, chubby_male, ugly_man, 1boy",
    "イケメン青年": "handsome, bishounen, young_man, slim, 1boy",
    "強面のおじさん": "old_man, muscular_male, scar, stubble, intimidating, 1boy",
    "ガリガリの陰キャ": "skinny_male, messy_hair, glasses, otaku, 1boy",
    "黒人マッチョ": "dark-skinned_male, muscular_male, tall_male, abs, 1boy",
    "太ったおじさん": "fat_man, old_man, hairy_male, bald, ugly_man, 1boy",
    "普通体型の少年": "young_man, average_build, 1boy",
}

# 男性キャラ 髪型オプション
MALE_HAIR_STYLE_OPTIONS = {
    "おまかせ": "",
    "短髪": "short_hair",
    "長髪": "long_hair",
    "はげ": "bald",
    "坊主": "buzz_cut",
    "オールバック": "slicked_back_hair",
    "ボサボサ": "messy_hair",
}

# 男性キャラ 髪色オプション
MALE_HAIR_COLOR_OPTIONS = {
    "おまかせ": "",
    "黒髪": "black_hair",
    "茶髪": "brown_hair",
    "金髪": "blonde_hair",
    "白髪": "grey_hair",
    "赤髪": "red_hair",
}

# 男性キャラ 肌色オプション
MALE_SKIN_COLOR_OPTIONS = {
    "おまかせ": "",
    "色白": "pale_skin",
    "普通": "",
    "日焼け": "tanned, dark_skin",
    "褐色": "dark-skinned_male",
    "黒肌": "dark-skinned_male, very_dark_skin",
}

# 時間帯オプション
TIME_OF_DAY_OPTIONS = {
    "おまかせ": "",
    "朝": "morning, sunrise, morning_light, warm_lighting",
    "昼": "daytime, sunlight, bright, afternoon",
    "夕方": "evening, sunset, orange_sky, golden_hour",
    "夜": "night, moonlight, dark, dim_lighting",
}

# 場所タイプオプション
LOCATION_TYPE_OPTIONS = {
    "おまかせ": "",
    "屋内": "indoors",
    "屋外": "outdoors",
}

# 男性外見 日本語→SDタグ変換マップ
MALE_TAG_MAP = {
    "はげ": "bald",
    "禿": "bald",
    "坊主": "buzz_cut",
    "小太り": "chubby_male",
    "太った": "fat_man",
    "デブ": "fat_man",
    "肥満": "fat_man, obese",
    "中年": "middle_aged",
    "おじさん": "old_man",
    "おっさん": "old_man",
    "老人": "elderly",
    "おじいちゃん": "old_man, grey_hair",
    "筋肉": "muscular_male",
    "マッチョ": "muscular_male, abs",
    "ガリガリ": "skinny_male",
    "痩せ": "skinny_male",
    "長身": "tall_male",
    "低身長": "short_male",
    "イケメン": "handsome, bishounen",
    "ブサイク": "ugly_man",
    "キモい": "ugly_man",
    "メガネ": "glasses",
    "眼鏡": "glasses",
    "ひげ": "beard",
    "髭": "beard",
    "無精ひげ": "stubble",
    "黒人": "dark-skinned_male",
    "白髪": "grey_hair",
    "金髪": "blonde_hair",
    "短髪": "short_hair",
    "長髪": "long_hair",
    "オールバック": "slicked_back_hair",
    "スーツ": "business_suit",
    "作業着": "work_clothes",
    "裸": "nude_male, shirtless",
    "タンクトップ": "tank_top",
    "サラリーマン": "salaryman, business_suit",
    "ヤンキー": "delinquent, pompadour",
    "体毛": "hairy_male",
    "傷": "scar",
    "強面": "intimidating",
    "優しい": "gentle_expression",
    "怖い": "intimidating, menacing",
    "少年": "young_man, shota",
    "青年": "young_man",
    "紳士": "gentleman, formal",
}


def parse_male_description(text: str) -> str:
    """ユーザーの自由入力テキストからSDタグを生成する"""
    if not text or not text.strip():
        return ""
    tags = set()
    tags.add("1boy")
    for keyword, sd_tags in MALE_TAG_MAP.items():
        if keyword in text:
            for t in sd_tags.split(", "):
                tags.add(t.strip())
    # マッチしなかった場合はデフォルト
    if len(tags) <= 1:  # 1boyのみ
        tags.add("1boy")
    return ", ".join(sorted(tags))


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
        "sd_expressions": "conflicted, guilty_pleasure, ahegao, mindbreak",
        # NTR谷あり型: 一度落ちてから再上昇。中盤で罪悪感の谷を作る
        "intensity_curve": "valley",  # 1→3→2→4→5→4
        "foreplay_ratio": 0.25,  # 前戯25%（心理描写重視）
        "intro_ratio": 0.08,  # 導入8%（日常→接近）
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
        "sd_expressions": "crying, fearful, reluctant, trembling, broken",
        "intensity_curve": "ascending",  # 1→2→3→4→5（右肩上がり）
        "foreplay_ratio": 0.15,
        "intro_ratio": 0.05,  # 導入最小（即行為開始）
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
        "sd_expressions": "crying, screaming, fearful, defeated",
        "intensity_curve": "ascending",
        "foreplay_ratio": 0.10,  # 前戯短め（強制的に進行）
        "intro_ratio": 0.05,
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
        "sd_expressions": "blushing, happy, loving, content, peaceful",
        "intensity_curve": "wave",  # 焦らし+感情描写の波型
        "foreplay_ratio": 0.30,  # 前戯30%（丁寧に描写）
        "intro_ratio": 0.10,
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
        "sd_expressions": "happy, enjoying, moaning, satisfied",
        "intensity_curve": "ascending",
        "foreplay_ratio": 0.20,
        "intro_ratio": 0.08,
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
        "sd_expressions": "confused, awakening, addicted, broken, ahegao",
        # 調教型: 段階的にエスカレート、最後に完堕ち
        "intensity_curve": "staircase",  # 1→2→3→3→4→4→5
        "foreplay_ratio": 0.20,
        "intro_ratio": 0.08,
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
        "sd_expressions": "embarrassed, trying_not_to_moan, biting_lip, conflicted",
        "intensity_curve": "wave",
        "foreplay_ratio": 0.20,  # 痴漢: 触る→戸惑い→感じる の波を作る
        "intro_ratio": 0.05,
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
        "sd_expressions": "nervous, secretive, professional_facade",
        "intensity_curve": "valley",  # 緊張→行為→中断リスク→再開
        "foreplay_ratio": 0.25,
        "intro_ratio": 0.10,
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
        "sd_expressions": "nervous, forbidden_pleasure, secretive",
        "intensity_curve": "valley",  # 禁断→一線→罪悪感→再犯
        "foreplay_ratio": 0.25,
        "intro_ratio": 0.10,
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
        "sd_expressions": "devoted, obedient, eager_to_please",
        "intensity_curve": "staircase",  # 奉仕→命令→特別奉仕の段階
        "foreplay_ratio": 0.20,
        "intro_ratio": 0.08,
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
        "sd_expressions": "empty_eyes, dazed, vacant, drooling, mindless, confused",
        # 催眠型: 段階的に深化、覚醒で一時ダウン→再度堕ちる
        "intensity_curve": "valley",
        "foreplay_ratio": 0.20,
        "intro_ratio": 0.08,
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
        "sd_expressions": "scared, disgusted, surprised, overwhelmed, ahegao",
        "intensity_curve": "two_stage",  # 1体目→2体目/形態変化の2段階
        "foreplay_ratio": 0.10,
        "intro_ratio": 0.05,
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
        "sd_expressions": "frozen, blank_expression, sleeping, confused, shocked",
        "intensity_curve": "plateau",  # 停止中は一定intensity→解除で急変
        "foreplay_ratio": 0.15,
        "intro_ratio": 0.08,
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
        "sd_expressions": "jealous, competitive, eager, cooperative, blush",
        "intensity_curve": "wave",  # キャラ交代時にintensity下がる波型
        "foreplay_ratio": 0.15,
        "intro_ratio": 0.08,
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
        "sd_expressions": "smirk, confident, teasing, dominant, looking_down",
        "intensity_curve": "staircase",  # 焦らし→ご褒美のリズム
        "foreplay_ratio": 0.20,
        "intro_ratio": 0.08,
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
        "sd_expressions": "guilty, conflicted, forbidden_pleasure, secretive",
        "intensity_curve": "valley",  # 日常→禁断→罪悪感で一旦引く→再び
        "foreplay_ratio": 0.25,
        "intro_ratio": 0.10,
    },
    "isekai": {
        "name": "異世界・ファンタジー",
        "story_arc": "召喚/転移→出会い→異文化交流→異世界の夜",
        "key_emotions": ["驚き", "好奇心", "異文化への戸惑い", "特別な絆"],
        "story_elements": [
            "異世界の独自ルールや文化",
            "種族差（エルフ/獣人/魔族など）",
            "魔法や特殊能力の存在",
            "「この世界では普通」という価値観の違い"
        ],
        "dialogue_tone": "ファンタジー風の言い回し、異文化のギャップ、冒険と興奮",
        "use_heart": True,
        "sd_tags": "fantasy, isekai, elf, magic, castle, medieval, adventurer, demon_girl",
        "sd_expressions": "curious, amazed, blushing, excited, fantasy_glow",
        "intensity_curve": "staircase",  # 異文化交流→段階的にエスカレート
        "foreplay_ratio": 0.20,
        "intro_ratio": 0.10,
    },
    "onsen": {
        "name": "温泉・お風呂",
        "story_arc": "入浴→のぼせ/接近→肌の触れ合い→湯けむりの中で",
        "key_emotions": ["リラックス", "羞恥", "開放感", "肌の密着感"],
        "story_elements": [
            "温泉や浴場のシチュエーション",
            "裸の状態からのスタート",
            "湯気や水音の演出",
            "のぼせて判断力低下"
        ],
        "dialogue_tone": "リラックスした口調、恥じらい、湯に溶ける感覚",
        "use_heart": True,
        "sd_tags": "onsen, hot_spring, bathing, wet, steam, towel, nude, water",
        "sd_expressions": "relaxed, flushed, steamy, embarrassed, dreamy",
        "intensity_curve": "wave",  # リラックス→興奮の波
        "foreplay_ratio": 0.25,
        "intro_ratio": 0.10,
    },
    "sleep": {
        "name": "睡眠・夜這い",
        "story_arc": "就寝→忍び寄る→まどろみの中で→覚醒",
        "key_emotions": ["無防備", "まどろみ", "夢か現実かの曖昧さ", "気づいた時の羞恥"],
        "story_elements": [
            "寝ている状態からの開始",
            "夢うつつの曖昧な意識",
            "「夢かと思った」反応",
            "声を殺す緊張感"
        ],
        "dialogue_tone": "寝ぼけた声、小声、曖昧な反応、覚醒後の動揺",
        "use_heart": False,
        "sd_tags": "sleeping, night_crawling, bed, nightgown, pajamas, dark_room, blanket",
        "sd_expressions": "sleeping, half_asleep, drowsy, confused, surprised",
        "intensity_curve": "staircase",  # 寝ている間→半覚醒→完全覚醒の段階
        "foreplay_ratio": 0.30,
        "intro_ratio": 0.05,
    },
    "gangbang": {
        "name": "輪姦・集団",
        "story_arc": "囲まれる→抵抗→連続→意識朦朧",
        "key_emotions": ["恐怖", "圧倒", "逃げ場のなさ", "快感の波状攻撃"],
        "story_elements": [
            "複数の男性による同時攻め",
            "一人では対処できない状況",
            "交代で休みなく続く",
            "意識が飛びそうになる"
        ],
        "dialogue_tone": "懇願、悲鳴、もう無理という限界、複数からの声",
        "use_heart": False,
        "sd_tags": "gangbang, group_sex, multiple_boys, surrounded, double_penetration",
        "sd_expressions": "overwhelmed, crying, exhausted, ahegao, drooling",
        "intensity_curve": "two_stage",  # 1回目→休息→2回目の2段階
        "foreplay_ratio": 0.10,
        "intro_ratio": 0.05,
    },
    "medical": {
        "name": "医療・診察",
        "story_arc": "受診→診察→特別な処置→堕ちる",
        "key_emotions": ["不安", "羞恥", "信頼の裏切り", "逆らえない立場"],
        "story_elements": [
            "医師/看護師と患者の関係",
            "診察の名目で触れる",
            "医療器具の利用",
            "「治療のためだから」という口実"
        ],
        "dialogue_tone": "専門用語混じり、冷静な口調と羞恥、命令的な指示",
        "use_heart": False,
        "sd_tags": "medical, doctor, nurse, hospital, examination, stethoscope, lab_coat",
        "sd_expressions": "nervous, embarrassed, clinical, vulnerable, exposed",
        "intensity_curve": "staircase",  # 検査→触診→処置の段階的エスカレーション
        "foreplay_ratio": 0.25,
        "intro_ratio": 0.10,
    },
    "swimsuit": {
        "name": "水着・プール",
        "story_arc": "水遊び→接近→水着のまま→開放的に",
        "key_emotions": ["開放感", "眩しさ", "日差しと熱さ", "夏の高揚感"],
        "story_elements": [
            "プールや海辺のシチュエーション",
            "水着姿の露出度",
            "水に濡れた肌の描写",
            "更衣室やシャワールームへの移動"
        ],
        "dialogue_tone": "明るく開放的、恥ずかしがり、夏の雰囲気",
        "use_heart": True,
        "sd_tags": "swimsuit, bikini, pool, beach, wet, sunlight, summer, ocean",
        "sd_expressions": "cheerful, embarrassed, wet, flushed, playful",
        "intensity_curve": "ascending",  # 水遊び→徐々にエスカレート
        "foreplay_ratio": 0.25,
        "intro_ratio": 0.10,
    },
    "sports": {
        "name": "スポーツ・部活",
        "story_arc": "練習→二人きり→汗だく→体育倉庫で",
        "key_emotions": ["競争心", "汗の匂い", "仲間意識からの逸脱", "若さの衝動"],
        "story_elements": [
            "部活や運動後のシチュエーション",
            "汗だくの体の描写",
            "体育倉庫/更衣室/部室",
            "先輩後輩の上下関係"
        ],
        "dialogue_tone": "元気で体育会系、先輩後輩の口調、汗と興奮",
        "use_heart": True,
        "sd_tags": "sports, gym_uniform, bloomers, sweat, locker_room, sporty, athletic",
        "sd_expressions": "sweaty, energetic, competitive, embarrassed, panting",
        "intensity_curve": "ascending",  # 運動の延長→そのまま上昇
        "foreplay_ratio": 0.20,
        "intro_ratio": 0.10,
    },
    "idol": {
        "name": "アイドル・芸能",
        "story_arc": "華やかな表舞台→裏の顔→秘密の関係→堕ちる",
        "key_emotions": ["表と裏のギャップ", "禁止された恋愛", "スキャンダルの恐怖", "本当の自分"],
        "story_elements": [
            "アイドルや芸能人の設定",
            "恋愛禁止のルール",
            "マネージャーやプロデューサーとの関係",
            "バレたら終わりの緊張感"
        ],
        "dialogue_tone": "表向きのアイドル口調と本音、ギャップ萌え、秘密の関係",
        "use_heart": True,
        "sd_tags": "idol, stage, microphone, costume, backstage, dressing_room, celebrity",
        "sd_expressions": "stage_smile, nervous, secretive, gap_moe, blushing",
        "intensity_curve": "valley",  # 表舞台→裏→葛藤で一旦引く→本音解放
        "foreplay_ratio": 0.20,
        "intro_ratio": 0.10,
    },
    "neighbor": {
        "name": "隣人・日常",
        "story_arc": "日常の接点→距離が縮まる→一線を越える→秘密の関係",
        "key_emotions": ["親しみ", "日常の延長", "近すぎる距離", "ご近所バレの恐怖"],
        "story_elements": [
            "隣の部屋/隣の家の住人",
            "日常的な接点（回覧板、ゴミ出し等）",
            "壁が薄い/声が漏れる",
            "顔を合わせる気まずさ"
        ],
        "dialogue_tone": "日常会話からの逸脱、親しみ、声を抑える、ご近所トーク",
        "use_heart": True,
        "sd_tags": "neighbor, apartment, casual_clothes, domestic, everyday, next_door",
        "sd_expressions": "friendly, nervous, secretive, blushing, trying_to_be_quiet",
        "intensity_curve": "wave",  # 日常→興奮→冷静→再燃の波
        "foreplay_ratio": 0.25,
        "intro_ratio": 0.10,
    },
    "prostitution": {
        "name": "風俗・パパ活",
        "story_arc": "交渉→サービス→本番→リピーター",
        "key_emotions": ["割り切り", "プロ意識", "本気と演技の境目", "金銭と快楽"],
        "story_elements": [
            "金銭的な関係が前提",
            "サービスのプロフェッショナル感",
            "「仕事だから」と割り切る態度",
            "徐々に本気になる/させる"
        ],
        "dialogue_tone": "営業トーク、割り切った態度、徐々に本音が漏れる",
        "use_heart": False,
        "sd_tags": "prostitution, escort, hotel_room, lingerie, money, transaction",
        "sd_expressions": "professional, seductive, calculating, genuine_pleasure",
        "intensity_curve": "ascending",  # サービス→本番→本気の上昇
        "foreplay_ratio": 0.20,
        "intro_ratio": 0.08,
    },
    "voyeur": {
        "name": "露出・盗撮",
        "story_arc": "覗き/露出→バレそうな瞬間→興奮→暴走",
        "key_emotions": ["スリル", "背徳感", "バレる恐怖と興奮", "見られる快感"],
        "story_elements": [
            "人目を気にする状況",
            "覗き/盗撮/露出のシチュエーション",
            "バレそうでバレないギリギリ",
            "見られている興奮"
        ],
        "dialogue_tone": "小声、ドキドキ、「誰かに見られたら」、スリルと興奮",
        "use_heart": False,
        "sd_tags": "voyeurism, exhibitionism, peeping, hidden_camera, outdoors, public",
        "sd_expressions": "thrilled, nervous, excited, peeking, exposed",
        "intensity_curve": "wave",  # スリル→安堵→再びスリルの波
        "foreplay_ratio": 0.20,
        "intro_ratio": 0.08,
    },
    "tentacle": {
        "name": "触手",
        "story_arc": "遭遇→拘束→同時多点攻め→快楽堕ち",
        "key_emotions": ["恐怖", "嫌悪感", "抵抗できない", "人外の快感"],
        "story_elements": [
            "触手による全身拘束",
            "複数箇所同時の刺激",
            "粘液や吸盤の異物感",
            "「こんなもので感じるなんて」という屈辱"
        ],
        "dialogue_tone": "恐怖と嫌悪、拘束への抵抗、異物感からの快楽、堕ちていく絶望",
        "use_heart": False,
        "sd_tags": "tentacles, tentacle_sex, restrained, slime, monster, bondage, multiple_insertions",
        "sd_expressions": "scared, disgusted, struggling, overwhelmed, ahegao, crying",
        "intensity_curve": "staircase",  # 拘束→挿入→増殖の段階
        "foreplay_ratio": 0.10,
        "intro_ratio": 0.05,
    },
    "reverse_rape": {
        "name": "逆レイプ",
        "story_arc": "出会い→主導権奪取→男を押し倒す→搾り取る",
        "key_emotions": ["支配欲", "攻撃的な欲望", "男の困惑", "容赦ない快楽"],
        "story_elements": [
            "女性が完全に主導権を握る",
            "男性の抵抗を無視/楽しむ",
            "一方的に押し倒す/跨る",
            "「逃がさない」「もっと出して」"
        ],
        "dialogue_tone": "攻撃的、命令口調、男の抵抗を嘲笑う、容赦ない搾取",
        "use_heart": False,
        "sd_tags": "reverse_rape, femdom, aggressive, pinning_down, cowgirl_position, straddling",
        "sd_expressions": "aggressive, predatory, smirk, wild, dominant, crazed",
        "intensity_curve": "ascending",  # 一方的にエスカレート
        "foreplay_ratio": 0.15,
        "intro_ratio": 0.08,
    },
    "cosplay": {
        "name": "コスプレ・撮影",
        "story_arc": "撮影会→ポーズ指示→過激に→そのままの衣装で",
        "key_emotions": ["なりきり", "露出の恥じらい", "カメラへの意識", "キャラと自分の境界"],
        "story_elements": [
            "コスプレ衣装を着た状態",
            "カメラマンとの関係",
            "ポーズ指示が徐々にエスカレート",
            "衣装のまま/半脱ぎの興奮"
        ],
        "dialogue_tone": "キャラなりきり口調、恥ずかしがり、カメラを意識した言動",
        "use_heart": True,
        "sd_tags": "cosplay, costume, photoshoot, camera, posing, dressing_up, roleplay",
        "sd_expressions": "posing, embarrassed, in_character, blushing, camera_aware",
        "intensity_curve": "ascending",  # ポーズ→過激に→そのまま行為へ
        "foreplay_ratio": 0.25,
        "intro_ratio": 0.10,
    },
}

# テーマ自動推定用キーワードマップ
THEME_KEYWORD_MAP = {
    "netorare": ["寝取", "NTR", "ntr", "彼氏持ち", "人妻", "不倫", "浮気", "他の男"],
    "humiliation": ["凌辱", "屈辱", "辱め", "恥辱", "陵辱"],
    "forced": ["強制", "無理やり", "レイプ", "rape", "暴行", "襲", "犯す"],
    "love": ["純愛", "ラブラブ", "恋人", "恋愛", "両想い", "甘々", "いちゃいちゃ"],
    "vanilla": ["和姦", "合意", "普通", "ノーマル"],
    "corruption": ["堕ち", "調教", "堕落", "快楽堕ち", "洗脳堕ち", "開発"],
    "chikan": ["痴漢", "電車", "満員", "公共", "バス"],
    "office": ["上司", "OL", "オフィス", "職場", "部下", "同僚", "社長"],
    "teacher_student": ["先生", "教師", "生徒", "教え子", "塾", "家庭教師", "教授"],
    "maid": ["メイド", "ご主人様", "執事", "使用人", "お嬢様"],
    "hypnosis": ["催眠", "洗脳", "暗示", "マインドコントロール", "操り"],
    "monster": ["異種", "モンスター", "オーク", "ゴブリン", "魔物", "獣"],
    "time_stop": ["時間停止", "時止め", "時を止め", "フリーズ"],
    "harem": ["ハーレム", "複数", "全員", "3P", "4P"],
    "femdom": ["痴女", "女性優位", "逆転", "女王様", "M男", "ドS"],
    "incest": ["近親", "兄妹", "姉弟", "母子", "父娘", "義妹", "義姉", "義母"],
    "isekai": ["異世界", "ファンタジー", "勇者", "魔王", "エルフ", "転生", "召喚"],
    "onsen": ["温泉", "お風呂", "入浴", "混浴", "銭湯", "露天風呂"],
    "sleep": ["夜這い", "寝て", "睡眠", "眠って", "就寝", "添い寝", "寝込み"],
    "gangbang": ["輪姦", "集団", "輪姦す", "大勢", "ぶっかけ", "連続"],
    "medical": ["医者", "診察", "病院", "ナース", "看護師", "検診", "治療"],
    "swimsuit": ["水着", "プール", "海", "ビーチ", "ビキニ", "スク水"],
    "sports": ["部活", "スポーツ", "体操", "ブルマ", "運動", "体育", "マネージャー"],
    "idol": ["アイドル", "芸能", "ライブ", "プロデューサー", "地下アイドル", "配信者"],
    "neighbor": ["隣人", "隣の", "お隣", "マンション", "アパート", "ご近所"],
    "prostitution": ["風俗", "パパ活", "援助", "デリヘル", "ソープ", "キャバ", "ホテヘル"],
    "voyeur": ["露出", "盗撮", "覗き", "見せつけ", "野外", "見られ"],
    "tentacle": ["触手", "tentacle"],
    "reverse_rape": ["逆レイプ", "逆レ", "押し倒す", "搾り取", "逆襲"],
    "cosplay": ["コスプレ", "撮影会", "レイヤー", "コス", "衣装"],
}


def _infer_theme_from_concept(concept: str) -> str:
    """コンセプト文からテーマを自動推定する。

    THEME_KEYWORD_MAPのキーワードとコンセプトを照合し、
    最もマッチ数が多いテーマを返す。マッチなしなら空文字。
    """
    if not concept:
        return ""
    scores = {}
    for theme_key, keywords in THEME_KEYWORD_MAP.items():
        score = sum(1 for kw in keywords if kw in concept)
        if score > 0:
            scores[theme_key] = score
    if not scores:
        return ""
    return max(scores, key=scores.get)


def _build_dynamic_theme_guide(concept: str) -> dict:
    """テーマガイドが見つからない場合に、コンセプトからミニマルなガイドを生成する。

    コンセプトのトーンを検出して合理的なデフォルト値を返す。
    """
    # トーン検出
    dark_keywords = ["強制", "凌辱", "暴行", "レイプ", "堕", "調教", "犯", "脅"]
    sweet_keywords = ["恋", "愛", "甘", "ラブ", "好き", "告白", "デート"]
    comedic_keywords = ["ギャグ", "コメディ", "ドジ", "ラッキースケベ", "間違い"]

    dark_score = sum(1 for kw in dark_keywords if kw in concept)
    sweet_score = sum(1 for kw in sweet_keywords if kw in concept)
    comedic_score = sum(1 for kw in comedic_keywords if kw in concept)

    if dark_score > sweet_score and dark_score > comedic_score:
        return {
            "name": "ダーク系",
            "story_arc": "導入→支配→エスカレート→堕ちる",
            "key_emotions": ["恐怖", "抵抗", "屈服", "快楽堕ち"],
            "story_elements": ["力関係の差", "抵抗と屈服", "徐々に体が反応"],
            "dialogue_tone": "抵抗、懇願、やがて快感に負ける",
            "use_heart": False,
            "sd_tags": "forced, reluctant, dark",
            "sd_expressions": "crying, fearful, reluctant, ahegao",
            "intensity_curve": "ascending",
            "foreplay_ratio": 0.15,
            "intro_ratio": 0.05,
        }
    elif sweet_score > dark_score:
        return {
            "name": "甘々系",
            "story_arc": "出会い→親密→告白→結ばれる",
            "key_emotions": ["恥じらい", "愛情", "幸福感", "一体感"],
            "story_elements": ["両想い", "恥じらい", "愛情表現"],
            "dialogue_tone": "甘い、恥ずかしがり、愛情たっぷり",
            "use_heart": True,
            "sd_tags": "romantic, loving, gentle, consensual",
            "sd_expressions": "blushing, happy, loving, content",
            "intensity_curve": "wave",
            "foreplay_ratio": 0.30,
            "intro_ratio": 0.10,
        }
    elif comedic_score > 0:
        return {
            "name": "コミカル系",
            "story_arc": "ハプニング→巻き込まれ→流されて→楽しむ",
            "key_emotions": ["驚き", "戸惑い", "照れ", "楽しさ"],
            "story_elements": ["偶然の状況", "ドジやハプニング", "ノリと勢い"],
            "dialogue_tone": "ツッコミ、驚き、流される、楽しむ",
            "use_heart": True,
            "sd_tags": "comedic, surprised, accidental, happy",
            "sd_expressions": "surprised, embarrassed, laughing, happy",
            "intensity_curve": "ascending",
            "foreplay_ratio": 0.20,
            "intro_ratio": 0.10,
        }
    else:
        return {
            "name": "汎用",
            "story_arc": "出会い→接近→行為→余韻",
            "key_emotions": ["期待", "興奮", "快感", "満足"],
            "story_elements": ["自然な展開", "段階的なエスカレーション"],
            "dialogue_tone": "自然、感情豊か",
            "use_heart": True,
            "sd_tags": "consensual, enjoying",
            "sd_expressions": "blushing, moaning, satisfied",
            "intensity_curve": "ascending",
            "foreplay_ratio": 0.20,
            "intro_ratio": 0.08,
        }


DEFAULT_NEGATIVE_PROMPT = "worst_quality, low_quality, lowres, bad_anatomy, bad_hands, missing_fingers, extra_fingers, mutated_hands, poorly_drawn_face, ugly, deformed, blurry, text, watermark, signature, censored, mosaic_censoring, loli, shota, child"

QUALITY_POSITIVE_TAGS = "(masterpiece, best_quality:1.2)"
QUALITY_TAGS_DISABLED = "__DISABLED__"  # カスタムモードで空欄→quality tags無し

# 体位タグリスト（体位重複防止システム用）
POSITION_TAGS = {
    "missionary", "missionary_position", "cowgirl_position", "reverse_cowgirl",
    "doggy_style", "from_behind", "standing_sex", "standing",
    "sitting", "sitting_on_lap", "straddling", "spooning",
    "prone_bone", "mating_press", "suspended_congress",
    "leg_lock", "legs_up", "legs_over_head",
    "face_sitting", "sixty_nine", "paizuri", "fellatio",
    "cunnilingus", "handjob", "against_wall", "bent_over",
    "on_side", "spread_legs", "all_fours", "on_back",
    "on_stomach", "kneeling", "squatting", "lotus_position",
}

# 体位代替マップ（同一体位検出時のフォールバック）
POSITION_FALLBACKS = {
    "missionary": ["cowgirl_position", "spooning", "from_behind"],
    "missionary_position": ["cowgirl_position", "spooning", "from_behind"],
    "doggy_style": ["prone_bone", "standing_sex", "mating_press"],
    "cowgirl_position": ["reverse_cowgirl", "sitting_on_lap", "missionary"],
    "reverse_cowgirl": ["cowgirl_position", "prone_bone", "on_side"],
    "from_behind": ["prone_bone", "against_wall", "standing_sex"],
    "standing_sex": ["against_wall", "suspended_congress", "from_behind"],
    "prone_bone": ["doggy_style", "mating_press", "on_stomach"],
    "mating_press": ["missionary", "legs_up", "prone_bone"],
    "spooning": ["on_side", "from_behind", "missionary"],
    "paizuri": ["fellatio", "handjob", "cowgirl_position"],
    "fellatio": ["paizuri", "handjob", "kneeling"],
    "all_fours": ["doggy_style", "prone_bone", "on_back"],
    "sitting_on_lap": ["straddling", "cowgirl_position", "face_sitting"],
    "against_wall": ["standing_sex", "from_behind", "bent_over"],
    "bent_over": ["against_wall", "doggy_style", "standing_sex"],
    "face_sitting": ["sixty_nine", "cowgirl_position", "sitting_on_lap"],
    "legs_up": ["mating_press", "missionary", "legs_over_head"],
    "spread_legs": ["missionary", "legs_up", "on_back"],
    "standing": ["against_wall", "standing_sex", "from_behind"],
    "sitting": ["sitting_on_lap", "straddling", "lotus_position"],
    "straddling": ["cowgirl_position", "sitting_on_lap", "face_sitting"],
    "on_back": ["missionary", "spread_legs", "legs_up"],
    "on_side": ["spooning", "from_behind", "prone_bone"],
    "on_stomach": ["prone_bone", "doggy_style", "all_fours"],
    "kneeling": ["all_fours", "doggy_style", "fellatio"],
    "squatting": ["cowgirl_position", "sitting_on_lap", "standing_sex"],
    "lotus_position": ["sitting_on_lap", "straddling", "cowgirl_position"],
    "suspended_congress": ["standing_sex", "against_wall", "mating_press"],
    "legs_over_head": ["legs_up", "mating_press", "missionary"],
    "sixty_nine": ["face_sitting", "on_back", "on_side"],
    "cunnilingus": ["face_sitting", "sixty_nine", "spread_legs"],
    "handjob": ["fellatio", "paizuri", "kneeling"],
    "leg_lock": ["missionary", "cowgirl_position", "mating_press"],
}

# intensity別 体位優先度（高intensityではより激しい体位を優先）
_POSITION_INTENSITY_PREFERENCE = {
    5: {"mating_press", "prone_bone", "suspended_congress", "legs_over_head",
        "standing_sex", "against_wall", "all_fours"},
    4: {"doggy_style", "cowgirl_position", "reverse_cowgirl", "from_behind",
        "bent_over", "standing_sex"},
    3: {"missionary", "spooning", "sitting_on_lap", "on_side"},
}

# アングル代替マップ（同一アングル連続時のフォールバック）
ANGLE_FALLBACKS = {
    "from_above": ["from_side", "pov", "dutch_angle"],
    "from_below": ["from_side", "straight-on", "dutch_angle"],
    "from_behind": ["from_side", "from_above", "pov"],
    "from_side": ["from_above", "pov", "straight-on"],
    "pov": ["from_above", "from_side", "dutch_angle"],
    "straight-on": ["from_side", "from_above", "pov"],
    "dutch_angle": ["from_side", "from_above", "pov"],
}

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
    all_thought_texts = [] # [(scene_id, text)]
    all_onom_sets = []    # [(scene_id, frozenset)]
    prev_angle_tags = set()
    prev_position_tags = set()

    for i, scene in enumerate(results):
        scene_id = scene.get("scene_id", i + 1)
        if scene.get("mood") == "エラー":
            continue
        problems = []

        # --- bubbles ---
        bubbles = scene.get("bubbles", [])

        # dialogue形式（旧フォーマット）からbubblesへのfallback変換
        if not bubbles and scene.get("dialogue"):
            bubbles = []
            for d in scene["dialogue"]:
                line_text = d.get("line", "")
                speaker = d.get("speaker", "")
                # emotionから推定: 喘ぎ系emotionならmoan、それ以外はspeech
                emotion = d.get("emotion", "")
                _moan_emotions = {"快感", "絶頂", "陶酔", "悶え", "昂り", "高潮", "恍惚"}
                btype = "moan" if emotion in _moan_emotions else "speech"
                bubbles.append({"type": btype, "speaker": speaker, "text": line_text})

        # 吹き出し数（1-3個: 主人公1-2 + 男性0-1）
        if len(bubbles) > 3:
            problems.append(f"吹き出し{len(bubbles)}個（上限3個）")
        elif len(bubbles) == 0:
            problems.append("吹き出しが0個")

        # 男セリフ数（≤1/ページ）
        male_speech_count = 0
        for b in bubbles:
            if b.get("type") == "speech":
                speaker = b.get("speaker", "")
                if speaker and heroine_names and speaker not in heroine_names:
                    male_speech_count += 1
        if male_speech_count > 1:
            problems.append(f"男性セリフ{male_speech_count}個（推奨1個以下）")

        # 男セリフ内容チェック（♡含有・喘ぎ・甘え語尾）
        for b in bubbles:
            speaker = b.get("speaker", "")
            is_male = speaker and heroine_names and speaker not in heroine_names
            if is_male:
                txt = b.get("text", "")
                btype = b.get("type", "")
                if "♡" in txt or "♥" in txt:
                    problems.append(f"男性「{speaker}」のセリフに♡: 「{txt}」")
                if btype == "moan":
                    problems.append(f"男性「{speaker}」がmoan(喘ぎ)タイプ: 「{txt}」")
                if any(k in txt for k in ["ぃ", "ぉ", "きもち", "もっとぉ", "すきぃ"]):
                    problems.append(f"男性「{speaker}」に甘え語尾: 「{txt}」")
                # 男性セリフ観察実況チェック（「～だな」系）
                import re as _re_val
                _clean_txt = txt.rstrip("…♡♥")
                if _re_val.search(r".{4,}(?:だな|してるな|だろうな)$", _clean_txt):
                    problems.append(f"男性「{speaker}」観察型: 「{txt}」")

        # thought部位ラベル冒頭チェック
        _BODY_PART_CHECK = ["胸…", "太もも…", "お尻…", "首筋…", "耳…", "唇…",
                            "舌…", "脚…", "背中…", "髪…", "うなじ…", "乳首…",
                            "おっぱい…", "ふともも…", "おしり…"]
        for b in bubbles:
            if b.get("type") == "thought":
                txt = b.get("text", "")
                if any(txt.startswith(bp) for bp in _BODY_PART_CHECK):
                    problems.append(f"thought部位ラベル冒頭: 「{txt}」")

        # 設備名混入チェック（location_detailの設備名がセリフに漏れている）
        _FIXTURE_WORDS = ["便器", "便座", "手洗い台", "手洗い鏡", "トイレットペーパー"]
        for b in bubbles:
            txt = b.get("text", "")
            if not txt:
                continue
            # 「肉便器」はエロ漫画スラングなので除外
            check_txt = txt.replace("肉便器", "")
            for fw in _FIXTURE_WORDS:
                if fw in check_txt:
                    problems.append(f"設備名混入「{fw}」検出: 「{txt}」")
                    break

        # 不自然表現チェック（書き言葉・医学用語・過剰敬語の検出）
        _UNNATURAL_WORDS = [
            "信じられない", "考えられない", "受け入れてしまう", "感じてしまう",
            "何も考えられない", "体温が上がる", "抗えない", "もう我慢できない",
            "壊れてしまいそう", "心臓が高鳴る", "全身が痺れるような",
            "理性が飛びそう", "快感が走る", "抵抗する力がなくなる",
            "体が反応してしまう", "頭が真っ白になる",
        ]
        _MEDICAL_WORDS = ["性器", "挿入", "射精", "絶頂", "愛液", "勃起", "膣内"]
        _POLITE_WORDS = [
            "してもよろしいですか", "感じてしまいます", "見ないでください",
            "触らないでください", "行ってしまいます", "出てしまいます",
            "止められません", "お願いします", "ありがとうございます",
            "気持ちいいです", "嬉しい気持ちです", "大丈夫です",
        ]
        for b in bubbles:
            txt = b.get("text", "")
            if not txt:
                continue
            for uw in _UNNATURAL_WORDS:
                if uw in txt:
                    problems.append(f"不自然表現「{uw}」検出: 「{txt}」")
                    break
            for mw in _MEDICAL_WORDS:
                if mw in txt:
                    problems.append(f"医学用語「{mw}」検出: 「{txt}」")
                    break
            for pw in _POLITE_WORDS:
                if pw in txt:
                    problems.append(f"過剰敬語「{pw}」検出: 「{txt}」")
                    break

        # moanタイプ内容検証（3段階: 漢字/助詞/非喘ぎ語彙チェック）
        # 根拠: MOAN_POOL全400エントリは100%仮名+装飾(♡…っー゛)。
        #   1. 漢字含有 → 非喘ぎ確定
        #   2. 文末助詞 → 会話文が混入
        #   3. 非喘ぎ語彙 → AFTERMATH_POOL等の身体状況報告が混入
        _NON_MOAN_WORDS = frozenset([
            "ぼーっと", "ぐったり", "ふわふわ", "ごめん", "どしよ",
            "なにこれ", "もうむり", "もう…むり", "なにこれ…", "ごめん…",
            "どしよ…", "ぼーっと…", "ぐったり…", "ふわふわ…",
        ])
        for b in bubbles:
            if b.get("type") == "moan":
                txt = b.get("text", "")
                if not txt:
                    continue
                has_kanji = bool(_re.search(r'[\u4e00-\u9faf\u3400-\u4dbf]', txt))
                has_sentence_ending = bool(_re.search(
                    r'(だ|です|ます|ない|ない…|ている|てる|する|される|して|した|しい)$', txt))
                is_non_moan_word = txt.rstrip("…♡♡♡") in _NON_MOAN_WORDS or txt in _NON_MOAN_WORDS
                if has_kanji or has_sentence_ending or is_non_moan_word:
                    problems.append(f"moanタイプに非喘ぎテキスト: 「{txt}」")

        # speechタイプ身体状況報告チェック（intensity>=3のアクションシーン）
        # 根拠: CG集のspeechは感情的反応。「汗すごい」「指先痺れ」等の
        #        身体状態の客観的報告はナレーション/ト書きであり、セリフとして不自然。
        _BODY_REPORT_KW = [
            "涙が", "汗すごい", "汗が", "声出ない", "息できない",
            "力入んない", "頭まっしろ", "目が回る", "指先痺れ",
            "全身痺れ", "まだ震えて", "震えてる", "動けない",
            "立てない", "からだ重い", "呼吸が", "ぼーっと",
            "ぐったり", "ふわふわ", "思考が", "意識が",
        ]
        if scene.get("intensity", 0) >= 3:
            for b in bubbles:
                if b.get("type") in ("speech", "thought"):
                    txt = b.get("text", "")
                    for kw in _BODY_REPORT_KW:
                        if kw in txt:
                            problems.append(f"身体状況報告セリフ: 「{txt}」（{b.get('type')}）")
                            break

        # 同一シーン内テキスト重複チェック
        bubble_texts_in_scene = [b.get("text", "") for b in bubbles if b.get("text")]
        if len(bubble_texts_in_scene) != len(set(bubble_texts_in_scene)):
            problems.append(f"同一シーン内にテキスト重複あり")

        # moan・speech・thought追跡（クロスシーン重複検出用）
        for b in bubbles:
            if b.get("type") == "moan":
                all_moan_texts.append((scene_id, b.get("text", "")))
            elif b.get("type") == "speech":
                all_speech_texts.append((scene_id, b.get("text", "")))
            elif b.get("type") == "thought":
                all_thought_texts.append((scene_id, b.get("text", "")))

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
            # 具体性キーワード: これらが1つでもあれば具体的と判定
            _CONCRETE_DESC_KW = [
                # 体位・行為
                "正常位", "後背位", "騎乗位", "背面", "立ち", "座位",
                "バック", "対面", "側位", "寝バック", "駅弁",
                "挿入", "ピストン", "腰を", "突き", "押し当て",
                "咥え", "舐め", "吸い", "しゃぶ", "フェラ", "パイズリ",
                "手コキ", "指を", "弄", "愛撫し",
                # 身体反応
                "汗", "涙", "震え", "痙攣", "力が抜け", "仰け反",
                "ビクビク", "ガクガク", "びくっ", "跳ね",
                # 具体的な動き
                "掴み", "押さえ", "引き寄せ", "しがみつ", "抱き",
                "開かせ", "持ち上げ", "覆いかぶさ", "跨", "乗り",
                "四つん這い", "うつ伏せ", "仰向け", "膝立ち",
                # 体の部位（具体的描写の指標）
                "胸を", "腰を", "脚を", "太もも", "尻を", "首筋",
            ]
            if not any(kw in desc for kw in _CONCRETE_DESC_KW):
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

        # --- sd_prompt: 連続同一体位 ---
        sd_tags_norm = {t.strip().lower().replace(" ", "_") for t in sd.split(",") if t.strip()}
        cur_positions = sd_tags_norm & POSITION_TAGS
        if cur_positions and cur_positions == prev_position_tags:
            problems.append(f"前シーンと同一体位: {', '.join(cur_positions)}")
        prev_position_tags = cur_positions

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
        bg_tags = {
            # 基本
            "outdoors", "indoors",
            # 学校
            "classroom", "library", "gym", "hallway", "stairwell",
            "locker_room", "infirmary", "rooftop", "club_room",
            "storage_room", "school",
            # 住居
            "bedroom", "bathroom", "kitchen", "living_room",
            "japanese_room", "balcony", "basement", "study",
            "entrance", "closet", "garage",
            # 商業・仕事
            "office", "elevator", "warehouse", "factory",
            "convenience_store", "store",
            # 宿泊
            "hotel_room", "ryokan_room", "inn_room", "cabin",
            # 飲食
            "cafe", "restaurant", "izakaya", "bar", "cafeteria",
            # 交通
            "car_interior", "train_interior", "bus_interior",
            "airplane_interior", "ship_interior", "train_station",
            # 娯楽
            "karaoke_room", "internet_cafe", "arcade", "theater",
            "studio",
            # 屋外・自然
            "park", "forest", "beach", "mountain", "river", "lake",
            "garden", "alley", "bridge", "riverbank", "field",
            "grassland", "cliff", "cave",
            # 風呂・温泉
            "onsen", "bath", "pool", "open_air_bath", "bathhouse",
            "sauna",
            # 宗教
            "shrine", "temple", "church", "graveyard",
            # ファンタジー
            "dungeon", "castle", "tower", "prison", "tavern",
            "throne_room",
            # SF
            "spaceship_interior", "laboratory", "cockpit",
            # 日本建築
            "engawa", "storehouse", "barn",
        }
        if sd and not (sd_tags_set & bg_tags):
            problems.append("sd_promptに背景/場所タグが無い")

        if problems:
            scene_issues[scene_id] = problems

    # --- クロスシーン: story_flow重複チェック（完全一致 + 高類似度） ---
    seen_flows = {}  # flow_text -> scene_id
    for i, scene in enumerate(results):
        flow = scene.get("story_flow", "")
        if not flow or len(flow) < 10:
            continue
        scene_id = scene.get("scene_id", i + 1)
        # 完全一致チェック
        if flow in seen_flows:
            scene_issues.setdefault(scene_id, []).append(
                f"story_flow重複（シーン{seen_flows[flow]}と完全同一）")
        else:
            # 高類似度チェック（先頭20文字一致 = ほぼコピペ）
            flow_prefix = flow[:20]
            for prev_flow, prev_sid in seen_flows.items():
                if prev_flow[:20] == flow_prefix and prev_sid != scene_id:
                    scene_issues.setdefault(scene_id, []).append(
                        f"story_flow類似（シーン{prev_sid}と先頭20字一致）")
                    break
            seen_flows[flow] = scene_id

    # --- クロスシーン: description類似チェック（先頭30文字一致=コピペ） ---
    seen_descs = {}  # desc_prefix -> scene_id
    for i, scene in enumerate(results):
        desc = scene.get("description", "")
        if not desc or len(desc) < 30:
            continue
        scene_id = scene.get("scene_id", i + 1)
        desc_prefix = desc[:30]
        if desc_prefix in seen_descs:
            scene_issues.setdefault(scene_id, []).append(
                f"description類似（シーン{seen_descs[desc_prefix]}と先頭30字一致）")
        else:
            seen_descs[desc_prefix] = scene_id

    # --- クロスシーン: title長さチェック ---
    for i, scene in enumerate(results):
        title = scene.get("title", "")
        scene_id = scene.get("scene_id", i + 1)
        if len(title) > 25:
            scene_issues.setdefault(scene_id, []).append(
                f"title長すぎ({len(title)}字): 「{title[:30]}...」")

    # --- クロスシーン: title品質チェック（句点混入・location混入） ---
    _TITLE_LOCATION_KW = [
        "トイレ", "個室", "便所", "教室", "部室", "保健室", "屋上", "体育館",
        "プール", "更衣室", "シャワー室", "ベッドルーム", "リビング", "キッチン",
        "浴室", "風呂", "脱衣所", "車内", "電車内", "バス内", "駐車場",
        "エレベーター", "階段", "廊下", "倉庫", "物置", "地下室", "ホテル",
        "旅館", "カラオケ", "ネカフェ", "漫喫", "オフィス", "会議室",
    ]
    for i, scene in enumerate(results):
        title = scene.get("title", "")
        scene_id = scene.get("scene_id", i + 1)
        if not title:
            continue
        # 句点チェック（タイトルに「。」は不適）
        if "。" in title:
            scene_issues.setdefault(scene_id, []).append(
                f"titleに句点混入: 「{title}」")
        # location混入チェック（場所名がtitleに含まれる）
        loc = scene.get("location_detail", scene.get("location", ""))
        if loc and len(loc) >= 4 and loc in title:
            scene_issues.setdefault(scene_id, []).append(
                f"titleにlocation混入: 「{title}」（location: {loc}）")
        # 場所キーワードが支配的なタイトル（場所KWが2つ以上）
        loc_kw_count = sum(1 for kw in _TITLE_LOCATION_KW if kw in title)
        if loc_kw_count >= 2:
            scene_issues.setdefault(scene_id, []).append(
                f"titleが場所名の羅列: 「{title}」（場所KW{loc_kw_count}個）")
        # description断片混入チェック（助詞「の」で始まる/名詞で途切れる不完全title）
        desc = scene.get("description", "")
        if desc and len(title) >= 6:
            # titleがdescriptionの部分文字列（10文字以上の断片）
            if len(title) >= 10 and title in desc:
                scene_issues.setdefault(scene_id, []).append(
                    f"titleにdescription断片混入: 「{title}」")
            # 「の」で始まるtitle（文の途中から切り取られた形跡）
            elif title.startswith("の") or title.startswith("と"):
                scene_issues.setdefault(scene_id, []).append(
                    f"title不完全（助詞で開始）: 「{title}」")
            # 「張」「れ」等の送り仮名で終わる（文の途中で途切れた形跡）
            elif len(title) >= 8 and title[-1] in "張貼掛掲載映写":
                scene_issues.setdefault(scene_id, []).append(
                    f"title不完全（途中で途切れ）: 「{title}」")

    # --- クロスシーン: title重複チェック ---
    seen_titles = {}  # title -> scene_id
    for i, scene in enumerate(results):
        title = scene.get("title", "")
        if not title:
            continue
        scene_id = scene.get("scene_id", i + 1)
        if title in seen_titles:
            scene_issues.setdefault(scene_id, []).append(
                f"title重複「{title}」（シーン{seen_titles[title]}と同一）")
        else:
            seen_titles[title] = scene_id

    # --- クロスシーン: titleキーワード過剰使用チェック ---
    _title_kw_count = {}
    _TITLE_CHECK_KW = ["膣奥", "膣", "理性", "崩壊", "限界", "快感", "堕ち", "抵抗",
                        "連続", "激突", "責め", "声", "最後", "扉", "壁", "視線",
                        "奥", "腰", "廊下"]
    for scene in results:
        title = scene.get("title", "")
        for kw in _TITLE_CHECK_KW:
            if kw in title:
                _title_kw_count[kw] = _title_kw_count.get(kw, 0) + 1
    _total_scenes = len(results)
    _title_kw_threshold = max(3, _total_scenes // 10)  # 10シーンにつき1回まで許容
    for kw, cnt in _title_kw_count.items():
        if cnt >= _title_kw_threshold:
            scene_issues.setdefault("global", []).append(
                f"titleキーワード過剰: 「{kw}」が{cnt}回使用（推奨2回以下）")

    # --- クロスシーン: description連続類似チェック（3連続で同一行為キーワード） ---
    _DESC_ACT_KW = ["膣奥", "突かれ", "責められ", "腰を振", "ピストン",
                     "挿入", "フェラ", "パイズリ", "騎乗", "バック",
                     "正常位", "四つん這い"]
    _desc_kw_per_scene = []
    for scene in results:
        desc = scene.get("description", "")
        kws = frozenset(kw for kw in _DESC_ACT_KW if kw in desc)
        _desc_kw_per_scene.append(kws)
    for k in range(2, len(_desc_kw_per_scene)):
        common = _desc_kw_per_scene[k] & _desc_kw_per_scene[k-1] & _desc_kw_per_scene[k-2]
        if len(common) >= 2:  # 2キーワード以上一致で類似判定（1つだけなら正常）
            sid = results[k].get("scene_id", k + 1)
            scene_issues.setdefault(sid, []).append(
                f"description3連続類似（行為キーワード同一: {common}）")

    # --- クロスシーン: character_feelings類似チェック ---
    seen_feelings = {}  # feelings_str -> scene_id
    for i, scene in enumerate(results):
        feelings = scene.get("character_feelings", {})
        if not feelings:
            continue
        scene_id = scene.get("scene_id", i + 1)
        feelings_str = str(sorted(feelings.values()))
        if len(feelings_str) < 15:
            continue
        if feelings_str in seen_feelings:
            scene_issues.setdefault(scene_id, []).append(
                f"character_feelings重複（シーン{seen_feelings[feelings_str]}と同一）")
        else:
            seen_feelings[feelings_str] = scene_id

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
    # 類似喘ぎ検出（正規化ハッシュ + 先頭4文字バケット → O(n)）
    moan_norm_map = {}  # normalized_text -> [(sid, original_text)]
    moan_prefix_map = {}  # prefix4 -> [(sid, original_text)]
    for sid, text in all_moan_texts:
        norm = _normalize_bubble_text(text)
        moan_norm_map.setdefault(norm, []).append((sid, text))
        if len(norm) >= 4:
            prefix = norm[:4]
            moan_prefix_map.setdefault(prefix, []).append((sid, text))
    # 正規化一致で重複検出
    for norm, entries in moan_norm_map.items():
        if len(entries) > 1:
            unique_texts = {}
            for sid, text in entries:
                unique_texts.setdefault(text, []).append(sid)
            texts = list(unique_texts.keys())
            for i in range(len(texts)):
                for j in range(i + 1, len(texts)):
                    key = f"{texts[i]}≈{texts[j]}"
                    if key not in repeated_moans:
                        repeated_moans[key] = [unique_texts[texts[i]][0], unique_texts[texts[j]][0]]
    # 先頭4文字一致で類似検出
    for prefix, entries in moan_prefix_map.items():
        if len(entries) > 1:
            unique_texts = {}
            for sid, text in entries:
                unique_texts.setdefault(text, []).append(sid)
            texts = list(unique_texts.keys())
            for i in range(len(texts)):
                for j in range(i + 1, len(texts)):
                    key = f"{texts[i]}≈{texts[j]}"
                    if key not in repeated_moans:
                        repeated_moans[key] = [unique_texts[texts[i]][0], unique_texts[texts[j]][0]]

    # --- クロスシーン: speech重複チェック ---
    speech_map = {}
    for sid, text in all_speech_texts:
        speech_map.setdefault(text, []).append(sid)
    repeated_speech = {t: sids for t, sids in speech_map.items() if len(sids) > 1}
    for text, sids in repeated_speech.items():
        for sid in sids[1:]:
            scene_issues.setdefault(sid, []).append(f"speech重複「{text}」（シーン{sids[0]}と同一）")

    # --- クロスシーン: thought先頭パターン反復チェック ---
    # 先頭パターンが同じthoughtが4回以上出現した場合に警告（「だめ…」パターン等）
    thought_prefix_counter = {}  # prefix -> [(scene_id, full_text)]
    for sid, text in all_thought_texts:
        if text and len(text) >= 2:
            # 最初の「…」より前を取得（「だめ…声が…」→「だめ」）
            first_part = text.split("\u2026")[0].replace("\u2665", "").replace("\u3063", "").strip()
            if len(first_part) >= 2:
                prefix = first_part[:3]
            else:
                clean = text.replace("\u2026", "").replace("\u2665", "").replace("\u3063", "").strip()
                prefix = clean[:2] if len(clean) >= 2 else ""
            if prefix:
                thought_prefix_counter.setdefault(prefix, []).append((sid, text))
    for prefix, entries in thought_prefix_counter.items():
        if len(entries) >= 4:
            scene_ids_str = ",".join(str(e[0]) for e in entries[:6])
            scene_issues.setdefault("global", []).append(
                f"thought先頭「{prefix}」が{len(entries)}回反復（シーン{scene_ids_str}）")

    # --- クロスシーン: thoughtテキスト内キーワード頻度チェック ---
    _THOUGHT_CONTENT_KW = ["だめ", "声", "やめて", "おく", "なか", "廊下", "聞こえ"]
    _thought_kw_count = {}
    for sid, text in all_thought_texts:
        for kw in _THOUGHT_CONTENT_KW:
            if kw in text:
                _thought_kw_count[kw] = _thought_kw_count.get(kw, 0) + 1
    _thought_total = max(1, len(all_thought_texts))
    for kw, cnt in _thought_kw_count.items():
        # 全thoughtの25%以上で同一キーワードが出現したら警告
        if cnt >= max(4, _thought_total // 4):
            scene_issues.setdefault("global", []).append(
                f"thoughtキーワード過剰: 「{kw}」が{cnt}/{_thought_total}回出現（25%超過）")

    # --- クロスシーン: 男性セリフ長文チェック（15文字超え） ---
    for i, scene in enumerate(results):
        scene_id = scene.get("scene_id", i + 1)
        for b in scene.get("bubbles", []):
            speaker = b.get("speaker", "")
            is_male = speaker and heroine_names and speaker not in heroine_names
            if is_male and b.get("type") == "speech":
                txt = b.get("text", "")
                # ♡…っ等の装飾を除いた実質文字数
                core = txt.replace("…", "").replace("♡", "").replace("っ", "").replace("♥", "").strip()
                if len(core) > 15:
                    scene_issues.setdefault(scene_id, []).append(
                        f"男性セリフ長文({len(core)}字): 「{txt}」")

    # --- クロスシーン: 男性セリフ末尾フレーズ反復チェック（「最高だ」等が3回以上） ---
    _male_speech_suffix_counter = {}  # suffix -> [(scene_id, full_text)]
    _MALE_SUFFIX_CHECK_LEN = 4  # 末尾N文字で比較
    _MALE_SUFFIX_THRESHOLD = max(3, len(results) // 15)  # 15シーンに1回まで許容
    for i, scene in enumerate(results):
        scene_id = scene.get("scene_id", i + 1)
        for b in scene.get("bubbles", []):
            speaker = b.get("speaker", "")
            is_male = speaker and heroine_names and speaker not in heroine_names
            if is_male and b.get("type") == "speech":
                txt = b.get("text", "")
                if not txt or len(txt) < 3:
                    continue
                # 装飾除去して末尾フレーズを抽出
                core = txt.replace("…", "").replace("♡", "").replace("っ", "").replace("♥", "").strip()
                if len(core) < 3:
                    continue
                suffix = core[-_MALE_SUFFIX_CHECK_LEN:] if len(core) >= _MALE_SUFFIX_CHECK_LEN else core
                _male_speech_suffix_counter.setdefault(suffix, []).append((scene_id, txt))
    for suffix, entries in _male_speech_suffix_counter.items():
        if len(entries) >= _MALE_SUFFIX_THRESHOLD:
            scene_ids_str = ",".join(str(e[0]) for e in entries[:6])
            scene_issues.setdefault("global", []).append(
                f"男性セリフ末尾「{suffix}」が{len(entries)}回反復（シーン{scene_ids_str}）")

    # --- クロスシーン: 男性セリフ多様性スコア（ユニーク率50%未満で警告） ---
    _all_male_speeches = []
    for scene in results:
        for b in scene.get("bubbles", []):
            speaker = b.get("speaker", "")
            is_male = speaker and heroine_names and speaker not in heroine_names
            if is_male and b.get("type") == "speech":
                txt = b.get("text", "")
                if txt:
                    _all_male_speeches.append(txt)
    if len(_all_male_speeches) >= 5:
        _unique_male = len(set(_all_male_speeches))
        _diversity_pct = _unique_male * 100 // len(_all_male_speeches)
        if _diversity_pct < 50:
            scene_issues.setdefault("global", []).append(
                f"男性セリフ多様性低: {_unique_male}/{len(_all_male_speeches)}({_diversity_pct}%ユニーク)")

    # --- クロスシーン: 不自然表現チェック（「らめ」「括弧」「一人称ブレ」） ---
    for i, scene in enumerate(results):
        scene_id = scene.get("scene_id", i + 1)
        for b in scene.get("bubbles", []):
            txt = b.get("text", "")
            if "らめ" in txt:
                scene_issues.setdefault(scene_id, []).append(
                    f"不自然表現「らめ」: 「{txt}」")
            if "」" in txt or "「" in txt:
                scene_issues.setdefault(scene_id, []).append(
                    f"括弧混入: 「{txt}」")

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

    # --- クロスシーン: 体位全体分布偏り ---
    position_counter = {}
    for scene in results:
        sd_text = scene.get("sd_prompt", "")
        _sd_tags = {t.strip().lower().replace(" ", "_") for t in sd_text.split(",") if t.strip()}
        for ptag in _sd_tags & POSITION_TAGS:
            position_counter[ptag] = position_counter.get(ptag, 0) + 1
    if total_scenes >= 5:
        for ptag, cnt in position_counter.items():
            if cnt / total_scenes >= 0.4:
                scene_issues.setdefault("global", []).append(
                    f"体位偏り: {ptag}が{cnt}/{total_scenes}シーン({cnt*100//total_scenes}%)")

    # --- 体位バリエーション統計 ---
    unique_positions = set(position_counter.keys())
    position_variety = {
        "unique_count": len(unique_positions),
        "positions_used": sorted(unique_positions),
        "distribution": position_counter,
    }

    # --- v7.1: intensity不一致検出 ---
    _LOW_I_MOANS = _re.compile(r"[あんはぁ]っ|んほ|あへ|んっ|あぁ|はぁ")
    for i, scene in enumerate(results):
        sid = scene.get("scene_id", i + 1)
        intensity = scene.get("intensity", 3)
        for bubble in scene.get("bubbles", []):
            txt = bubble.get("text", "")
            btype = bubble.get("type", "")
            if not txt:
                continue
            if intensity <= 2:
                if "♡" in txt:
                    scene_issues.setdefault(sid, []).append(
                        f"intensity{intensity}に♡: 「{txt[:20]}」")
                if btype in ("speech", "thought") and _LOW_I_MOANS.search(txt):
                    scene_issues.setdefault(sid, []).append(
                        f"intensity{intensity}に喘ぎ表現: 「{txt[:20]}」")
            if intensity >= 4:
                if btype in ("speech", "thought"):
                    for polite in ("です", "ます", "ください"):
                        if polite in txt:
                            scene_issues.setdefault(sid, []).append(
                                f"intensity{intensity}に丁寧語「{polite}」: 「{txt[:20]}」")
                            break

    # --- v7.1: 語尾パターン反復検出（3連続以上） ---
    _suffix_seq = []  # [(scene_id, suffix)]
    for i, scene in enumerate(results):
        sid = scene.get("scene_id", i + 1)
        for bubble in scene.get("bubbles", []):
            txt = bubble.get("text", "").rstrip()
            if len(txt) >= 3:
                _suffix_seq.append((sid, txt[-3:]))
    for idx in range(len(_suffix_seq) - 2):
        s1 = _suffix_seq[idx][1]
        if s1 == _suffix_seq[idx + 1][1] == _suffix_seq[idx + 2][1]:
            if idx > 0 and _suffix_seq[idx - 1][1] == s1:
                continue
            sid = _suffix_seq[idx][0]
            scene_issues.setdefault(sid, []).append(
                f"語尾パターン3連続「{s1}」")

    # --- v7.1: thought長さチェック（20文字超=ナレーション化） ---
    for i, scene in enumerate(results):
        sid = scene.get("scene_id", i + 1)
        for bubble in scene.get("bubbles", []):
            if bubble.get("type") == "thought":
                txt = bubble.get("text", "")
                if len(txt) > 20:
                    scene_issues.setdefault(sid, []).append(
                        f"thought長すぎ({len(txt)}文字): 「{txt[:25]}…」")

    n_issues = sum(len(v) for v in scene_issues.values()) + len(repeated_moans) + len(repeated_onom)
    score = max(0, 100 - n_issues * 5)

    return {
        "score": score,
        "scene_issues": scene_issues,
        "repeated_moans": repeated_moans,
        "repeated_onomatopoeia": repeated_onom,
        "position_variety": position_variety,
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
    """セリフテキストを正規化して類似判定に使用。
    装飾除去+濁点/半濁点除去+カタカナ→ひらがな。
    例: 「あ゛あ゛っ♡♡」→「ああ」, 「ああっ♡」→「ああ」 → 同系統と判定可能
    """
    # 装飾文字除去
    t = text.replace("♡", "").replace("♥", "").replace("…", "").replace("っ", "").replace("ー", "").strip()
    # 濁点・半濁点除去（漫画的な「あ゛」「お゛」表現の正規化）
    # U+309B ゛, U+309C ゜, U+3099 結合濁点, U+309A 結合半濁点
    t = t.replace("\u309B", "").replace("\u309C", "").replace("\u3099", "").replace("\u309A", "")
    # 全角濁点的な表記も除去
    t = t.replace("゛", "").replace("゜", "")
    # カタカナ→ひらがな変換
    result = []
    for ch in t:
        cp = ord(ch)
        if 0x30A1 <= cp <= 0x30F6:
            result.append(chr(cp - 0x60))
        else:
            result.append(ch)
    return "".join(result)

def _is_similar_bubble(text1: str, text2: str, strict: bool = False) -> bool:
    """2つのセリフが類似しているか判定。
    strict=False（デフォルト）: 完全一致 or 正規化一致 or 先頭一致
    strict=True: 完全一致 or 正規化完全一致のみ（短い喘ぎ声向け）
    """
    if text1 == text2:
        return True
    n1 = _normalize_bubble_text(text1)
    n2 = _normalize_bubble_text(text2)
    if n1 == n2:
        return True
    if strict:
        return False
    # 長めのテキスト（4文字以上の正規化結果）のみ先頭一致チェック
    if len(n1) >= 4 and len(n2) >= 4 and n1[:4] == n2[:4]:
        return True
    return False

def _analyze_scene_context(scene: dict) -> str:
    """シーンのdescription/title/moodからコンテキストタイプを判定。
    Returns: 'non_sexual' | 'foreplay' | 'sexual' | 'climax' | 'aftermath'"""
    desc = (scene.get("description", "") + " " + scene.get("title", "")
            + " " + scene.get("mood", "")).lower()
    intensity = scene.get("intensity", 3)

    # 事後シーン
    aftermath_kw = ["事後", "余韻", "虚脱", "罪悪感", "後悔", "戻って", "帰る",
                    "眠り", "崩れ落ち", "終えた", "身繕い", "動けない", "虚ろ",
                    "後片付け", "放心", "脱力", "ぐったり", "呆然", "立てない",
                    "意識が戻", "我に返", "現実に戻"]
    if any(k in desc for k in aftermath_kw):
        return "aftermath"

    # 非エロシーン（歩き・日常・会話のみ）
    non_sexual_kw = ["歩く", "歩き", "歩いて", "通りを", "散歩", "食事", "食堂",
                     "休む", "休憩", "眺め", "待つ", "待って", "帰省", "到着",
                     "村に着", "自室で", "くつろ", "話しかけ", "説明を受",
                     "呼び止め", "誘われ", "連れ", "囲まれて", "聞き入",
                     "聞いて", "話を聞", "習慣", "近づき", "語りかけ",
                     "声をかけ"]
    # 非エロキーワードに該当し、かつ性行為キーワードが無ければnon_sexual
    sex_act_kw = ["挿入", "突き", "突かれ", "犯さ", "抱かれ", "愛撫", "舐", "咥",
                  "胸を", "乳首", "腰を振", "ピストン", "フェラ", "クンニ",
                  "手マン", "正常位", "騎乗", "バック", "結合", "肉棒"]
    has_non_sexual = any(k in desc for k in non_sexual_kw)
    has_sex = any(k in desc for k in sex_act_kw)

    if has_non_sexual and not has_sex:
        return "non_sexual"

    # 絶頂シーン
    if intensity >= 5 or any(k in desc for k in ["絶頂", "イク", "果て", "限界",
                                                   "痙攣", "理性崩壊", "アヘ"]):
        return "climax"

    # 前戯（触れる・撫でる・キス・服を脱がせる等、性行為未満の接触）
    foreplay_kw = ["触れ", "触って", "撫で", "キス", "抱きしめ", "脱がせ", "脱がさ",
                   "裸に"]
    if intensity <= 2 or (not has_sex and any(k in desc for k in foreplay_kw)):
        return "foreplay"

    return "sexual"


def _deduplicate_across_scenes(results: list, theme: str = "",
                                heroine_names: list = None,
                                char_profiles: list = None) -> None:
    """シーン間の同一・類似セリフを検出し、プールから代替セリフに置換。
    - 文脈判定: descriptionを解析し、非エロシーンにエロセリフを入れない
    - 重複保護: 同一セリフが検出された場合、プールから代替セリフに置換
    - ヒロイン名リスト以外のspeakerは全て男性と判定
    - テーマ/intensityに応じてプールカテゴリを絞り込み
    - 性格タイプに応じてプール混合比率を調整"""
    try:
        from ero_dialogue_pool import (
            get_moan_pool, get_speech_pool, pick_replacement, SPEECH_MALE_POOL,
            SPEECH_FEMALE_POOL, THOUGHT_POOL, NEUTRAL_POOL, AFTERMATH_POOL,
            get_male_speech_pool, get_female_speech_pool
        )
        has_pool = True
    except ImportError:
        try:
            from ero_dialogue_pool import (
                get_moan_pool, get_speech_pool, pick_replacement, SPEECH_MALE_POOL,
                SPEECH_FEMALE_POOL, THOUGHT_POOL, get_male_speech_pool,
                get_female_speech_pool
            )
            has_pool = True
            NEUTRAL_POOL = None
            AFTERMATH_POOL = None
        except ImportError:
            has_pool = False
            NEUTRAL_POOL = None
            AFTERMATH_POOL = None
            log_message("ero_dialogue_pool.py未検出、重複は除去のみ（置換なし）")

    # ヒロイン名セット構築（これ以外のspeakerは全て男性扱い）
    _heroine_set = set()
    if heroine_names:
        for n in heroine_names:
            if n:
                _heroine_set.add(n)
                if len(n) >= 2:
                    _heroine_set.add(n[:2])
                    if len(n) >= 3:
                        _heroine_set.add(n[2:])

    # 性格タイプ判定（性格別プール混合用）
    _personality_type = _detect_personality_type(char_profiles) if char_profiles else ""
    _pool_mix = _PERSONALITY_POOL_MIX.get(_personality_type, {}) if _personality_type else {}

    # キャラ固有プール読み込み
    _dedup_char_pool = {}
    if char_profiles:
        _cp0 = char_profiles[0]
        _cp_id = generate_char_id(_cp0.get("work_title", ""), _cp0.get("character_name", ""))
        _dedup_char_pool = load_character_pool(_cp_id)

    def _is_male_speaker(speaker: str) -> bool:
        if not speaker:
            return False
        for h in _heroine_set:
            if h in speaker:
                return False
        return True

    def _get_male_pool_for_theme(theme_str: str, intensity: int) -> list:
        t = theme_str.lower() if theme_str else ""
        pool = []
        if any(k in t for k in ["痴漢", "chikan", "公共", "public", "電車", "train", "トイレ"]):
            pool.extend(SPEECH_MALE_POOL.get("chikan", []))
            pool.extend(SPEECH_MALE_POOL.get("taunt", []))
            pool.extend(SPEECH_MALE_POOL.get("public", []))
            pool.extend(SPEECH_MALE_POOL.get("command", []))
        elif any(k in t for k in ["ntr", "寝取", "夜這", "村", "レイプ", "陵辱", "調教", "奴隷"]):
            pool.extend(SPEECH_MALE_POOL.get("command", []))
            pool.extend(SPEECH_MALE_POOL.get("dirty", []))
        elif any(k in t for k in ["純愛", "ラブ", "恋人", "カップル"]):
            pool.extend(SPEECH_MALE_POOL.get("gentle", []))
            pool.extend(SPEECH_MALE_POOL.get("praise", []))
        else:
            if intensity >= 4:
                pool.extend(SPEECH_MALE_POOL.get("command", []))
                pool.extend(SPEECH_MALE_POOL.get("dirty", []))
            else:
                pool.extend(SPEECH_MALE_POOL.get("dirty", []))
                pool.extend(SPEECH_MALE_POOL.get("praise", []))
        return pool if pool else [v for sp in SPEECH_MALE_POOL.values() for v in sp]

    def _get_pool_for_context(ctx: str, intensity: int, is_male: bool,
                              btype: str) -> list:
        """文脈・intensity・性別・タイプに応じた最適プールを選択"""
        # 非エロシーン → 中立プールのみ（エロ混入防止の最重要ガード）
        if ctx == "non_sexual":
            if NEUTRAL_POOL:
                return NEUTRAL_POOL.get("male" if is_male else "female", [])
            # フォールバック: 内蔵の中立セリフ
            if is_male:
                return ["ああ", "そうか", "来い", "行くぞ", "どうした"]
            return ["うん…", "え…", "あ、はい", "そう…", "ん…"]

        # 事後シーン
        if ctx == "aftermath":
            if AFTERMATH_POOL:
                return AFTERMATH_POOL.get("male" if is_male else "female", [])
            if is_male:
                return ["もういいぞ", "帰れ", "次もな"]
            return ["もう…むり", "動けない…", "ごめん…", "ぼーっと…"]

        # エロシーンの通常ロジック
        if btype == "moan":
            pool = []
            if _dedup_char_pool and "moan" in _dedup_char_pool:
                pool.extend(_dedup_char_pool["moan"].get(str(intensity), []))
            pool.extend(get_moan_pool(intensity))
            return pool
        elif btype == "thought":
            pool = []
            if _dedup_char_pool and "thought" in _dedup_char_pool:
                # フェーズ推定で適切なthoughtを混合
                try:
                    from ero_dialogue_pool import infer_phase as _inf_ph
                    _ph = _inf_ph(intensity, 0, 1)  # 推定（dedup時はscene_index不定）
                    pool.extend(_dedup_char_pool["thought"].get(_ph, []))
                except (ImportError, Exception):
                    pass
            pool.extend(get_speech_pool("thought", theme, intensity))
            return pool
        elif is_male:
            return _get_male_pool_for_theme(theme, intensity)
        else:
            # 女性speech: キャラ固有プール優先 → 性格タイプ → intensity連動フォールバック
            pool = []
            if _dedup_char_pool and "speech" in _dedup_char_pool:
                try:
                    from ero_dialogue_pool import infer_phase as _inf_ph2
                    _ph2 = _inf_ph2(intensity, 0, 1)
                    pool.extend(_dedup_char_pool["speech"].get(_ph2, []))
                except (ImportError, Exception):
                    pass
            if _pool_mix:
                # 性格別プール混合: primary(2倍) + secondary(1倍)
                for cat in _pool_mix.get("primary", []):
                    entries = SPEECH_FEMALE_POOL.get(cat, [])
                    pool.extend(entries)
                    pool.extend(entries)  # 2倍ウェイト
                for cat in _pool_mix.get("secondary", []):
                    pool.extend(SPEECH_FEMALE_POOL.get(cat, []))
                # intensity補正: 高intensityではecstasy/plea追加
                if intensity >= 4 and "ecstasy" not in _pool_mix.get("primary", []):
                    pool.extend(SPEECH_FEMALE_POOL.get("ecstasy", []))
                if intensity >= 3 and "plea" not in _pool_mix.get("primary", []):
                    pool.extend(SPEECH_FEMALE_POOL.get("plea", []))
            else:
                # デフォルト: intensity連動
                if intensity <= 2:
                    pool.extend(SPEECH_FEMALE_POOL.get("denial", []))
                    pool.extend(SPEECH_FEMALE_POOL.get("embarrassed", []))
                elif intensity == 3:
                    pool.extend(SPEECH_FEMALE_POOL.get("plea", []))
                    pool.extend(SPEECH_FEMALE_POOL.get("acceptance", []))
                    pool.extend(SPEECH_FEMALE_POOL.get("embarrassed", []))
                elif intensity == 4:
                    pool.extend(SPEECH_FEMALE_POOL.get("acceptance", []))
                    pool.extend(SPEECH_FEMALE_POOL.get("plea", []))
                    pool.extend(SPEECH_FEMALE_POOL.get("ecstasy", []))
                else:
                    pool.extend(SPEECH_FEMALE_POOL.get("ecstasy", []))
                    pool.extend(SPEECH_FEMALE_POOL.get("plea", []))
                    pool.extend(SPEECH_FEMALE_POOL.get("submissive", []))
            return pool if pool else [v for sp in SPEECH_FEMALE_POOL.values() for v in sp]

    # 使用済みテキスト追跡（全シーン横断）
    used_moan_raw = set()
    used_moan_texts = set()
    used_moan_prefixes = set()  # 正規化先頭4文字（O(1)類似検出用）
    used_thought_raw = set()
    used_thought_texts = set()
    used_thought_prefixes = set()
    used_speech_raw = set()
    used_speech_texts = set()
    used_speech_prefixes = set()
    used_speech_suffixes = set()  # 末尾5文字（部分一致O(1)用）
    moan_core_counter = {}  # 正規化先頭3文字 -> カウント（O(1)部分一致用）
    # 表現パターン追跡（「初めて」「彼のこと」等の重複防止）
    used_patterns = {}  # pattern_key -> count
    # thought先頭パターン追跡（「だめ…」「やだ…」等の同一先頭3文字反復防止）
    thought_prefix_counter = {}  # prefix3 -> count
    _THOUGHT_PREFIX_LIMIT = 4  # 同一先頭パターンの上限
    # thoughtテキスト内キーワード頻度追跡（「だめ」「声」等の過剰使用防止）
    _thought_kw_counter = {}  # kw -> count
    _THOUGHT_CONTENT_KW = ["だめ", "声", "やめて", "おく", "なか", "廊下", "聞こえ"]
    _THOUGHT_KW_LIMIT = 4  # 同一キーワードの上限

    replace_count = 0

    REPETITION_PATTERNS = {
        "初めて": ["初めて", "はじめて"],
        "彼のこと": ["彼のこと", "彼氏のこと", "彼を忘れ"],
        "感じ": ["こんなに感じ", "なぜ感じ", "なんで感じ"],
        "おかしく": ["おかしく", "おかしい"],
    }

    def _get_thought_prefix(text: str) -> str:
        """thought先頭パターンを抽出（最初の「…」より前、なければ先頭2文字）。
        例: 「だめ…声が…」→「だめ」, 「やば…」→「やば」, 「変になる…」→「変に」
        """
        # 最初の「…」で分割して前半を取得
        first_part = text.split("…")[0].replace("♡", "").replace("っ", "").strip()
        if len(first_part) >= 2:
            return first_part[:3]  # 最大3文字
        # 「…」がない場合は先頭2文字
        clean = text.replace("…", "").replace("♡", "").replace("っ", "").strip()
        return clean[:2] if len(clean) >= 2 else ""

    def _check_thought_prefix_limit(text: str) -> bool:
        """thought先頭パターンが上限を超えていたらTrue"""
        prefix = _get_thought_prefix(text)
        if not prefix:
            return False
        return thought_prefix_counter.get(prefix, 0) >= _THOUGHT_PREFIX_LIMIT

    def _register_thought_prefix(text: str):
        prefix = _get_thought_prefix(text)
        if prefix:
            thought_prefix_counter[prefix] = thought_prefix_counter.get(prefix, 0) + 1

    def _check_thought_kw_limit(text: str) -> bool:
        """thoughtテキスト内のキーワードが上限を超えていたらTrue"""
        for kw in _THOUGHT_CONTENT_KW:
            if kw in text and _thought_kw_counter.get(kw, 0) >= _THOUGHT_KW_LIMIT:
                return True
        return False

    def _register_thought_kw(text: str):
        for kw in _THOUGHT_CONTENT_KW:
            if kw in text:
                _thought_kw_counter[kw] = _thought_kw_counter.get(kw, 0) + 1

    def _check_pattern_limit(text: str) -> bool:
        """表現パターンが上限（全体で2回）を超えていたらTrue"""
        for key, phrases in REPETITION_PATTERNS.items():
            if any(p in text for p in phrases):
                cnt = used_patterns.get(key, 0)
                if cnt >= 2:
                    return True
        return False

    def _register_patterns(text: str):
        for key, phrases in REPETITION_PATTERNS.items():
            if any(p in text for p in phrases):
                used_patterns[key] = used_patterns.get(key, 0) + 1

    for scene in results:
        # dialogue形式（旧フォーマット）からbubblesへの変換
        if "bubbles" not in scene and scene.get("dialogue"):
            _moan_emotions = {"快感", "絶頂", "陶酔", "悶え", "昂り", "高潮", "恍惚"}
            scene["bubbles"] = []
            for d in scene["dialogue"]:
                emotion = d.get("emotion", "")
                btype = "moan" if emotion in _moan_emotions else "speech"
                scene["bubbles"].append({
                    "type": btype,
                    "speaker": d.get("speaker", ""),
                    "text": d.get("line", ""),
                })
        if "bubbles" not in scene:
            continue
        cleaned_bubbles = []
        sid = scene.get("scene_id", "?")
        intensity = scene.get("intensity", 3)
        ctx = _analyze_scene_context(scene)

        for b in scene["bubbles"]:
            text = b.get("text", "")
            btype = b.get("type", "")
            speaker = b.get("speaker", "")
            is_male = _is_male_speaker(speaker)

            if not text:
                cleaned_bubbles.append(b)
                continue

            # === 置換判定: 重複 or 長文 or パターン過多 or 文脈不整合 ===
            need_replace = False
            reason = ""

            if btype == "moan":
                norm = _normalize_bubble_text(text)
                if (text in used_moan_raw) or (norm in used_moan_texts):
                    need_replace = True
                    reason = "重複"
                elif len(norm) >= 4 and norm[:4] in used_moan_prefixes:
                    need_replace = True
                    reason = "類似"
                # 部分一致チェック: 正規化後先頭3文字が3回以上使用 → O(1)
                elif not need_replace and len(norm) >= 3:
                    core = norm[:3]
                    _moan_core_hits = moan_core_counter.get(core, 0)
                    if _moan_core_hits >= 2:
                        need_replace = True
                        reason = f"部分一致({core}系{_moan_core_hits+1}回)"
                # 非エロシーンで喘ぎは文脈不整合
                if ctx == "non_sexual":
                    need_replace = True
                    reason = "非エロ文脈で喘ぎ"

            elif btype == "thought":
                norm = _normalize_bubble_text(text)
                if (text in used_thought_raw) or (norm in used_thought_texts):
                    need_replace = True
                    reason = "重複"
                elif len(norm) >= 4 and norm[:4] in used_thought_prefixes:
                    need_replace = True
                    reason = "類似"
                elif _check_pattern_limit(text):
                    need_replace = True
                    reason = "パターン過多"
                elif _check_thought_prefix_limit(text):
                    need_replace = True
                    reason = f"先頭反復({_get_thought_prefix(text)})"
                elif _check_thought_kw_limit(text):
                    need_replace = True
                    reason = "キーワード過剰"

            elif btype == "speech":
                norm = _normalize_bubble_text(text)
                if (text in used_speech_raw) or (norm in used_speech_texts):
                    need_replace = True
                    reason = "重複"
                elif len(norm) >= 4 and norm[:4] in used_speech_prefixes:
                    need_replace = True
                    reason = "類似"
                # 部分一致チェック（末尾5文字 or 先頭5文字の一致）→ O(1)セットルックアップ
                elif len(norm) >= 5 and not need_replace:
                    if norm[-5:] in used_speech_suffixes or norm[:5] in used_speech_prefixes:
                        need_replace = True
                        reason = "部分一致"
                # 非エロシーンで♡付きセリフは文脈不整合
                if ctx == "non_sexual" and ("♡" in text or "♥" in text):
                    need_replace = True
                    reason = "非エロ文脈で♡"
                # 非エロシーンで明らかなエロセリフは不整合
                if ctx == "non_sexual":
                    erotic_kw = ["感じ", "奥", "イく", "イっ", "出る", "入って",
                                 "締まる", "濡れ", "とろ"]
                    if any(k in text for k in erotic_kw):
                        need_replace = True
                        reason = "非エロ文脈でエロ語"

            # 長文判定は廃止（セリフの長さを制限しない）

            # 事後シーンの文脈不整合チェック（エロ語・戦闘語が混入していたら置換）
            if ctx == "aftermath" and not need_replace:
                _aftermath_bad_kw = ["逃げ", "戦", "攻撃", "殺", "来るな", "来んな",
                                     "奥", "イく", "イっ", "締まる", "入って", "もっと",
                                     "感じ", "濡れ", "♡", "♥"]
                if any(k in text for k in _aftermath_bad_kw):
                    need_replace = True
                    reason = "事後文脈で不適切セリフ"

            # === 置換実行 ===
            if need_replace and has_pool:
                pool = _get_pool_for_context(ctx, intensity, is_male, btype)
                used_set = (used_moan_raw if btype == "moan"
                            else used_thought_raw if btype == "thought"
                            else used_speech_raw)
                norm_fn = _normalize_bubble_text
                replacement = pick_replacement(pool, used_set, norm_fn)
                if replacement:
                    log_message(f"  S{sid}: {reason}→置換「{text}」→「{replacement}」")
                    b["text"] = replacement
                    replace_count += 1
            elif need_replace and not has_pool:
                # プールがない場合は重複除去のみ（バブルをスキップ）
                if reason in ("重複", "類似"):
                    continue

            # 使用済み登録
            final_text = b.get("text", "")
            final_norm = _normalize_bubble_text(final_text)
            if btype == "moan":
                used_moan_raw.add(final_text)
                used_moan_texts.add(final_norm)
                if len(final_norm) >= 4:
                    used_moan_prefixes.add(final_norm[:4])
                if len(final_norm) >= 3:
                    _core = final_norm[:3]
                    moan_core_counter[_core] = moan_core_counter.get(_core, 0) + 1
            elif btype == "thought":
                used_thought_raw.add(final_text)
                used_thought_texts.add(final_norm)
                if len(final_norm) >= 4:
                    used_thought_prefixes.add(final_norm[:4])
                _register_patterns(final_text)
                _register_thought_prefix(final_text)
                _register_thought_kw(final_text)
            elif btype == "speech":
                used_speech_raw.add(final_text)
                used_speech_texts.add(final_norm)
                if len(final_norm) >= 4:
                    used_speech_prefixes.add(final_norm[:4])
                if len(final_norm) >= 5:
                    used_speech_suffixes.add(final_norm[-5:])

            cleaned_bubbles.append(b)

        if cleaned_bubbles:
            scene["bubbles"] = cleaned_bubbles

    if replace_count > 0:
        log_message(f"  重複セリフ計{replace_count}件を置換完了")

    # オノマトペ: 3シーン以内に同じ組み合わせがあれば除去
    for i in range(1, len(results)):
        curr_se = set(results[i].get("onomatopoeia", []))
        if not curr_se:
            continue
        for j in range(max(0, i - 3), i):
            prev_se = set(results[j].get("onomatopoeia", []))
            if prev_se and curr_se == prev_se:
                results[i]["onomatopoeia"] = []
                log_message(f"  S{results[i].get('scene_id', '?')}: S{results[j].get('scene_id', '?')}と同一SE除去")
                break

    # sd_prompt内の体位タグ: 前シーンとの連続重複を検出し代替置換
    import re as _re_dedup
    _prev_pos = set()
    for scene in results:
        sd = scene.get("sd_prompt", "")
        if not sd:
            _prev_pos = set()
            continue
        tags = [t.strip() for t in sd.split(",") if t.strip()]
        _cur_pos = set()
        new_tags = []
        changed = False
        for tag in tags:
            _inner = _re_dedup.sub(r'[()]', '', tag).split(":")[0].strip().lower().replace(" ", "_")
            if _inner in POSITION_TAGS:
                _cur_pos.add(_inner)
                if _inner in _prev_pos:
                    fallbacks = POSITION_FALLBACKS.get(_inner, [])
                    replacement = None
                    for fb in fallbacks:
                        if fb not in _prev_pos:
                            replacement = fb
                            break
                    if replacement:
                        _cur_pos.discard(_inner)
                        _cur_pos.add(replacement)
                        new_tags.append(replacement)
                        changed = True
                        log_message(f"  S{scene.get('scene_id', '?')}: 体位重複置換 {_inner}→{replacement}")
                        continue
            new_tags.append(tag)
        if changed:
            scene["sd_prompt"] = ", ".join(new_tags)
        _prev_pos = _cur_pos

    # sd_prompt内のアングルタグ: 前シーンとの連続重複を検出し代替置換
    _angle_kw = {"from_above", "from_below", "from_behind", "from_side",
                 "pov", "straight-on", "dutch_angle"}
    _prev_angles = set()
    for scene in results:
        sd = scene.get("sd_prompt", "")
        if not sd:
            _prev_angles = set()
            continue
        tags = [t.strip() for t in sd.split(",") if t.strip()]
        _cur_angles = set()
        new_tags = []
        changed = False
        for tag in tags:
            _inner = _re_dedup.sub(r'[()]', '', tag).split(":")[0].strip().lower().replace(" ", "_")
            if _inner in _angle_kw:
                _cur_angles.add(_inner)
                if _inner in _prev_angles:
                    fallbacks = ANGLE_FALLBACKS.get(_inner, [])
                    replacement = None
                    for fb in fallbacks:
                        if fb not in _prev_angles:
                            replacement = fb
                            break
                    if replacement:
                        _cur_angles.discard(_inner)
                        _cur_angles.add(replacement)
                        new_tags.append(replacement)
                        changed = True
                        log_message(f"  S{scene.get('scene_id', '?')}: アングル重複置換 {_inner}→{replacement}")
                        continue
            new_tags.append(tag)
        if changed:
            scene["sd_prompt"] = ", ".join(new_tags)
        _prev_angles = _cur_angles

def auto_fix_script(results: list, char_profiles: list = None, theme: str = "") -> list:
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

    # === キャラ固有セリフプールの読み込み ===
    _char_pool = {}
    if char_profiles:
        _cp0 = char_profiles[0]
        _cp_id = generate_char_id(_cp0.get("work_title", ""), _cp0.get("character_name", ""))
        _char_pool = load_character_pool(_cp_id)
        if _char_pool:
            log_message(f"キャラ固有プール読み込み: {_cp_id}")

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

    # 4.5. 男性セリフ自動修正（♡除去、moan→speech変換、長文短縮）
    heroine_name_set = set(correct_names) if correct_names else set()
    # 男性speaker名フォールバック（heroine_name_set空時に使用）
    _MALE_SPEAKER_NAMES = frozenset([
        "男", "男性", "おじさん", "おっさん", "先生", "上司", "彼",
        "男の子", "少年", "青年", "紳士", "客", "店長", "先輩", "後輩",
        "兄", "弟", "父", "義父", "義兄", "master", "男A", "男B",
    ])
    def _is_male_by_name(speaker: str) -> bool:
        """heroine_name_set空時のフォールバック男性判定"""
        if not speaker:
            return False
        if heroine_name_set:
            return speaker not in heroine_name_set and not any(h in speaker for h in heroine_name_set)
        return speaker in _MALE_SPEAKER_NAMES or any(m in speaker for m in _MALE_SPEAKER_NAMES)
    for scene in results:
        if "bubbles" in scene:
            for bubble in scene["bubbles"]:
                speaker = bubble.get("speaker", "")
                is_male = speaker and _is_male_by_name(speaker)
                if is_male:
                    # ♡♥を除去
                    txt = bubble.get("text", "")
                    if "♡" in txt or "♥" in txt:
                        txt = txt.replace("♡", "").replace("♥", "").strip()
                        bubble["text"] = txt
                    # moan→speech変換
                    if bubble.get("type") == "moan":
                        bubble["type"] = "speech"

    # 4.52. description内「主人公」→ヒロイン名置換（男性参照時のみ）
    _MALE_ACTION_KEYWORDS = {"挿入", "腰を振", "攻め", "抱き", "犯", "掴", "押し倒", "射精", "突い", "責め", "脱がせ", "握り", "引き寄せ", "覆いかぶさ"}
    _protagonist_fix_count = 0
    heroine_label = correct_names[0] if correct_names else "ヒロイン"
    for scene in results:
        for field in ["description", "story_flow", "direction"]:
            text = scene.get(field, "")
            if not text or "主人公" not in text:
                continue
            # 「主人公が+男性的動作」パターンを検出→「彼」に置換（男性を指す場合）
            for kw in _MALE_ACTION_KEYWORDS:
                if kw in text and "主人公" in text:
                    text = text.replace("主人公", "彼")
                    scene[field] = text
                    _protagonist_fix_count += 1
                    break
            else:
                # 男性動作なし→女性を指している可能性→ヒロイン名に置換
                if "主人公" in text:
                    text = text.replace("主人公", heroine_label)
                    scene[field] = text
                    _protagonist_fix_count += 1
    if _protagonist_fix_count > 0:
        log_message(f"  主人公呼称修正: {_protagonist_fix_count}件")

    # お嬢様口調崩壊マップ（intensity 4-5で適用）
    _OJOUSAMA_BREAKDOWN_MAP = {
        "ですの": "…の…♡",
        "ですわ": "…♡",
        "ですこと": "…♡",
        "でございます": "…♡",
        "なさいませ": "…て…♡",
        "いたしますわ": "ちゃう…♡",
        "くださいませ": "…♡",
        "ましてよ": "…♡",
        "おほほ": "あっ♡",
        "ごきげんよう": "",
        "わたくし": "あたし",
        "いけませんわ": "だめ…♡",
        "よろしくてよ": "いい…♡",
        "存じません": "しらない…",
        "困りますわ": "やだ…♡",
        "お許しください": "ゆるして…♡",
        "なりませんわ": "だめ…♡",
        "ございませんの": "ない…♡",
        "いたしません": "しない…♡",
        "差し上げます": "あげる…♡",
    }

    # 4.52b. お嬢様口調崩壊処理（intensity 4-5で丁寧語を崩す）
    _ojousama_fix_count = 0
    for scene in results:
        intensity = scene.get("intensity", 2)
        if intensity < 4:
            continue
        if "bubbles" not in scene:
            continue
        for bubble in scene["bubbles"]:
            speaker = bubble.get("speaker", "")
            # 男性セリフはスキップ
            if speaker and _is_male_by_name(speaker):
                continue
            txt = bubble.get("text", "")
            if not txt:
                continue
            original = txt
            for formal, broken in _OJOUSAMA_BREAKDOWN_MAP.items():
                if formal in txt:
                    txt = txt.replace(formal, broken)
            # intensity 5: 残った「です」も崩す
            if intensity >= 5 and "です" in txt:
                txt = txt.replace("です", "…♡")
            if txt != original:
                bubble["text"] = txt
                _ojousama_fix_count += 1
                log_message(f"  お嬢様口調崩壊: 「{original}」→「{txt}」")
    if _ojousama_fix_count > 0:
        log_message(f"  お嬢様口調崩壊: {_ojousama_fix_count}件修正")

    # 4.55. 男性セリフ末尾フレーズ反復修正（「最高だ」問題対策）
    # LLMが同一末尾フレーズの男性セリフを繰り返す問題を検出→SPEECH_MALE_POOLから代替置換
    _MALE_SUFFIX_FIX_THRESHOLD = 3  # 同一末尾フレーズ3回以上で修正
    _male_suffix_map = {}  # suffix -> [(scene_idx, bubble_idx, full_text)]
    for si, scene in enumerate(results):
        if "bubbles" not in scene:
            continue
        for bi, bubble in enumerate(scene["bubbles"]):
            speaker = bubble.get("speaker", "")
            is_male = speaker and heroine_name_set and speaker not in heroine_name_set
            if is_male and bubble.get("type") == "speech":
                txt = bubble.get("text", "")
                if not txt or len(txt) < 3:
                    continue
                core = txt.replace("…", "").replace("♡", "").replace("っ", "").replace("♥", "").strip()
                if len(core) < 3:
                    continue
                suffix = core[-4:] if len(core) >= 4 else core
                _male_suffix_map.setdefault(suffix, []).append((si, bi, txt))
    _male_suffix_fix_count = 0
    try:
        from ero_dialogue_pool import SPEECH_MALE_POOL as _MALE_POOL_CHECK
        _has_male_pool = True
    except ImportError:
        _has_male_pool = False
    if _has_male_pool:
        _used_male_texts = set()
        # 先に全ての男性セリフを使用済みとして登録
        for scene in results:
            for b in scene.get("bubbles", []):
                sp = b.get("speaker", "")
                if sp and heroine_name_set and sp not in heroine_name_set and b.get("type") == "speech":
                    _used_male_texts.add(b.get("text", ""))
        for suffix, entries in _male_suffix_map.items():
            if len(entries) < _MALE_SUFFIX_FIX_THRESHOLD:
                continue
            # 最初の2件は残し、3件目以降を置換
            for si, bi, old_txt in entries[2:]:
                intensity = results[si].get("intensity", 3)
                # テーマに応じた男性プールを取得
                try:
                    from ero_dialogue_pool import get_male_speech_pool_for_theme, SPEECH_MALE_POOL as _MSP
                    _pool = get_male_speech_pool_for_theme(theme, intensity)
                except (ImportError, AttributeError):
                    _pool = []
                    try:
                        from ero_dialogue_pool import SPEECH_MALE_POOL as _MSP
                        for cat_entries in _MSP.values():
                            _pool.extend(cat_entries)
                    except ImportError:
                        break
                # 使用済みテキストを除外して代替を選択
                candidates = [t for t in _pool if t not in _used_male_texts and t != old_txt]
                if candidates:
                    import random as _rng_male
                    replacement = _rng_male.choice(candidates)
                    results[si]["bubbles"][bi]["text"] = replacement
                    _used_male_texts.add(replacement)
                    _male_suffix_fix_count += 1
                    log_message(f"  S{results[si].get('scene_id','?')}: 男性セリフ反復修正「{old_txt}」→「{replacement}」")
    if _male_suffix_fix_count > 0:
        log_message(f"  男性セリフ反復修正: {_male_suffix_fix_count}件")

    # 4.56. 男性セリフ末尾フレーズ反復修正（ハードコード代替辞書版 - プール置換漏れの補完）
    _MALE_SUFFIX_ALTERNATIVES = {
        "最高だ": ["たまんねえ", "いい反応だ", "堕ちたな", "もう戻れねえ", "感じてんだろ",
                    "締まるな", "素直だな", "いい顔だな", "我慢すんなよ", "ほら声出せ"],
        "おくだ": ["もっとだ", "逃がさねえ", "そのままだ", "力抜けよ", "震えてんぞ",
                    "声漏れてる", "もう無理だろ", "欲しいんだろ", "体は正直だ", "いいぞ"],
        "もっと": ["まだだ", "止まんな", "そのまま", "いけるだろ", "ほらもう一回"],
    }
    _suffix_counts = {}  # suffix -> count seen so far
    _suffix_fix_count = 0
    for scene in results:
        if "bubbles" not in scene:
            continue
        for bubble in scene["bubbles"]:
            speaker = bubble.get("speaker", "")
            is_male = speaker and heroine_name_set and speaker not in heroine_name_set
            if not is_male:
                continue
            txt = bubble.get("text", "")
            if not txt:
                continue
            for suffix, alts in _MALE_SUFFIX_ALTERNATIVES.items():
                if txt.rstrip("…♡").endswith(suffix) or suffix in txt:
                    _suffix_counts[suffix] = _suffix_counts.get(suffix, 0) + 1
                    if _suffix_counts[suffix] > 2:  # 3回目以降は置換
                        import random as _rng
                        alt = _rng.choice(alts)
                        old_txt = txt
                        bubble["text"] = alt
                        log_message(f"  男性セリフ反復修正: 「{old_txt}」→「{alt}」")
                        _suffix_fix_count += 1
                    break
    if _suffix_fix_count > 0:
        log_message(f"  男性セリフ反復修正(辞書): {_suffix_fix_count}件")

    # 4.58. 男性セリフ頻度制限（全体の35%以下に抑制）
    total_scenes = len(results)
    max_male_scenes = max(2, int(total_scenes * 0.35))
    scenes_with_male = []
    for idx, scene in enumerate(results):
        if "bubbles" not in scene:
            continue
        for bubble in scene["bubbles"]:
            speaker = bubble.get("speaker", "")
            if speaker and _is_male_by_name(speaker):
                scenes_with_male.append(idx)
                break
    if len(scenes_with_male) > max_male_scenes:
        # 保持するシーン: intensity 5のシーン + 最初の男性登場シーン + 等間隔
        keep_indices = set()
        # intensity 5は必ず保持
        for idx in scenes_with_male:
            if results[idx].get("intensity", 0) >= 5:
                keep_indices.add(idx)
        # 最初の男性登場も保持
        if scenes_with_male:
            keep_indices.add(scenes_with_male[0])
        # 残り枠を等間隔で配分
        remaining_slots = max_male_scenes - len(keep_indices)
        if remaining_slots > 0:
            candidates = [i for i in scenes_with_male if i not in keep_indices]
            if candidates:
                step = max(1, len(candidates) // remaining_slots)
                for j in range(0, len(candidates), step):
                    if len(keep_indices) >= max_male_scenes:
                        break
                    keep_indices.add(candidates[j])
        # 不要な男性セリフを削除
        _male_freq_removed = 0
        for idx in scenes_with_male:
            if idx in keep_indices:
                continue
            scene = results[idx]
            scene["bubbles"] = [
                b for b in scene["bubbles"]
                if not (b.get("speaker", "") and _is_male_by_name(b.get("speaker", "")))
            ]
            _male_freq_removed += 1
        if _male_freq_removed > 0:
            log_message(f"  男性セリフ頻度制限: {_male_freq_removed}シーンから男性セリフ除去（{len(scenes_with_male)}→{len(scenes_with_male)-_male_freq_removed}シーン）")

    # 4.6. 括弧除去・「らめ」修正・一人称ブレ修正・タイトル長制限
    _46_fix_count = 0
    # 一人称マップ構築（キャラプロファイルから）
    _first_person_map = {}  # character_name -> first_person
    if char_profiles:
        for cp in char_profiles:
            cn = cp.get("character_name", "")
            fp = cp.get("first_person", "")
            if cn and fp:
                _first_person_map[cn] = fp
    for scene in results:
        # タイトル品質修正（長制限 + location混入 + 句点 + 重複）
        title = scene.get("title", "")
        # 句点を含むタイトルは不正（descriptionの混入）
        if "。" in title:
            title = title.split("。")[0].strip()
            scene["title"] = title
            log_message(f"  S{scene.get('scene_id','?')}: タイトル句点除去")
            _46_fix_count += 1
        # location名がタイトルに混入している場合、除去
        _loc_keywords = ["トイレ個室", "の駅の", "教室内", "部屋の中"]
        for lk in _loc_keywords:
            if lk in title and len(title) > 15:
                parts = title.split(lk)
                cleaned = parts[0].strip().rstrip("の")
                if len(cleaned) >= 3:
                    scene["title"] = cleaned
                    title = cleaned
                    log_message(f"  S{scene.get('scene_id','?')}: タイトルlocation除去「{cleaned}」")
                    _46_fix_count += 1
                break
        if len(title) > 25:
            scene["title"] = title[:25].rstrip("。、…")
            log_message(f"  S{scene.get('scene_id','?')}: タイトル短縮")
            _46_fix_count += 1
        if "bubbles" not in scene:
            continue
        for bubble in scene["bubbles"]:
            txt = bubble.get("text", "")
            if not txt:
                continue
            orig = txt
            # 括弧除去
            txt = txt.strip("「」『』""")
            # 「らめ」→「だめ」修正（moanでもspeechでも）
            if "らめ" in txt:
                txt = txt.replace("らめぇぇ", "だめぇ").replace("らめぇん", "だめぇ")
                txt = txt.replace("らめにゃ", "だめぇ").replace("らめらめ", "だめだめ")
                txt = txt.replace("らめなの", "だめなの").replace("らめぇっ", "だめぇっ")
                txt = txt.replace("らめっ", "だめっ").replace("らめぇ", "だめぇ")
                txt = txt.replace("らめ", "だめ")
            # 一人称ブレチェック
            speaker = bubble.get("speaker", "")
            expected_fp = _first_person_map.get(speaker, "")
            if expected_fp and expected_fp != "あたし" and "あたし" in txt:
                txt = txt.replace("あたし", expected_fp)
            if txt != orig:
                bubble["text"] = txt
                _46_fix_count += 1
    if _46_fix_count > 0:
        log_message(f"  括弧/らめ/一人称修正: {_46_fix_count}件")

    # 4.7. 不自然表現の自動修正（書き言葉→話し言葉、句点除去、ひらがな化）
    _UNNATURAL_REPLACEMENTS = {
        # --- 長文的表現→短縮 ---
        "信じられない": "うそ…",
        "現実じゃない": "え…うそ…",
        "考えられない": "なんで…",
        "受け入れてしまう": "あ…っ",
        "感じてしまう": "あ…やば…",
        "声が出てしまう": "あ…声…っ",
        "何も考えられない": "まっしろ…",
        "離れたくない": "いかないで…",
        "体温が上がる": "あつい…",
        "ずっと震えてる": "ふるえ…てる",
        "抗えない": "やだ…のに…",
        "嬉しい気持ちです": "うれしい…♡",
        "気持ちいいです": "きもちぃ…♡",
        "本当にいいの？": "いいの…？",
        "お願いします": "おねがい…♡",
        "もう我慢できない": "むり…♡",
        "恥ずかしい": "はずかし…",
        "やめてください": "やめ…",
        "どうしよう": "どしよ…",
        "怖いです": "こわい…",
        "痛いです": "いた…",
        "すごいです": "すご…",
        # --- 医学用語→俗語 ---
        "性器": "あそこ",
        "挿入して": "いれて",
        "射精して": "だして",
        "絶頂に達": "イっちゃ",
        "愛液が": "ぬるぬる…",
        "勃起": "おっき",
        # --- 過剰敬語→くだけた表現 ---
        "してもよろしいですか": "して…",
        "感じてしまいます": "感じちゃ…",
        "見ないでください": "みないで…",
        "触らないでください": "さわんな…",
        "行ってしまいます": "イっちゃ…",
        "出てしまいます": "でちゃ…",
        "止められません": "とまんない…",
        "ありがとうございます": "ありがと…",
        "すみません": "ごめん…",
        "分かりました": "うん…",
        "大丈夫です": "だいじょぶ…",
        # --- 小説的独白→CG集thought ---
        "心臓が高鳴る": "ドキドキ…",
        "体が熱くなってきた": "あつい…",
        "頭が真っ白になる": "なにも…かんがえられ…",
        "全身が痺れるような": "ビリビリ…",
        "理性が飛びそう": "もう…むり…",
        "意識が遠のく": "とお…く…",
        "体の芯が疼く": "うずうず…",
        # --- 説明的表現→感情的表現 ---
        "とても気持ちが良い": "きもちぃ♡",
        "快感が走る": "あっ♡",
        "声が出てしまいます": "あぁん♡",
        "抵抗する力がなくなる": "ちから…はいんない…",
        "体が反応してしまう": "やだ…かってに…",
        "もう限界です": "もう…むりぃ…♡",
        "壊れてしまいそう": "こわれ…ちゃう…♡",
        # 催眠テーマ
        "催眠をかけられ": "ぼーっと…♡",
        "洗脳されて": "あたま…からっぽ…♡",
        "意識が朦朧と": "ふわふわ…♡",
        "催眠状態で": "とろとろ…♡",
        "暗示にかかって": "はい…♡",
        # 痴漢テーマ
        "声を抑えて": "んっ…っ",
        "周りに気づかれない": "バレ…ちゃう…",
        "人目を気にしながら": "だめ…ここ…",
        # 射精受け
        "精液が流れ込む": "あつい…♡♡",
        "子宮に届いた": "おく…♡♡♡",
        "体内に射精される": "中…あつい…♡♡",
        # 2回戦
        "再び挿入される": "また…♡♡",
        "感度が上がって": "さっきより…♡♡",
        # --- v7.0追加: 拘束/SM系 ---
        "拘束されている": "にげらんない…",
        "縛られたまま": "うごけない…",
        "目隠しをされ": "みえない…こわい…",
        "自由を奪われ": "からだ…うごかない…",
        # --- v7.0追加: 義父/近親系 ---
        "お義父さんに": "パパに…",
        "義理の父に": "パパに…",
        "血のつながりはない": "かぞく…なのに…",
        # --- v7.0追加: フェラ/口 ---
        "口腔内に": "くちのなか…",
        "咥えさせられ": "くわえて…",
        "嚥下する": "ごくん…♡",
        "口内射精": "おくちに…♡",
        # --- v7.0追加: 小説的→CG集 ---
        "彼に抱かれて": "だかれ…♡",
        "快感の波が": "きもち…やば…♡",
        "理性の糸が切れる": "きれ…ちゃう…♡",
        "限界が近い": "もう…むり…♡",
        "喘ぎ声が漏れる": "あ…声…♡",
        "息が荒くなって": "はぁはぁ…",
        "涙が頬を伝う": "なみだ…とまんない…",
        "最後の一線を越え": "こえちゃ…う…♡",
        "快楽に溺れる": "おぼれ…ちゃう…♡",
        "体が震えて": "ふるえてる…",
        "愛おしい気持ちが溢れ": "すき…すき…♡",
        "激しく腰を振られ": "はげし…♡♡",
        # --- v7.0追加: 硬い接続詞 ---
        "しかしながら": "でも…",
        "それにもかかわらず": "なのに…",
        # --- v7.1追加: お嬢様口調→CG集 ---
        "でございますの": "…の…♡",
        "いたしますわ": "ちゃう…♡",
        "くださいませ": "…♡",
        "よろしくてよ": "いい…♡",
        # --- v7.1追加: さらなる書き言葉→話し言葉 ---
        "胸が苦しい": "くるしい…",
        "涙が止まらない": "なみだ…",
        "全身が震える": "ふるえ…てる…",
        "頭がおかしくなりそう": "おかしく…なる…",
        "逃げ出したい": "にげたい…",
        "声を殺して": "んっ…っ",
        "目を背けたい": "みたくない…",
        "許してほしい": "ゆるして…",
        "もう一度してほしい": "もっかい…♡",
        "気が狂いそう": "おかしく…なっちゃう…",
        "体が言うことを聞かない": "からだ…かって…に…",
        "耐えられない": "むりぃ…♡",
        "苦しいくらいに気持ちいい": "くるし…きもちぃ…♡",
        "何度もイかされて": "またイ…っちゃ…♡♡",
        "お腹の中が熱い": "おなか…あつい…♡",
        "頭の中が真っ白": "しろ…い…",
        "我を忘れて": "もう…なにも…",
        # --- v7.4追加: 文語表現→CG集 ---
        "溢れ出す": "あふれて…",
        "身を委ねる": "まかせ…ちゃう…♡",
        "恍惚として": "とろとろ…♡",
        "蕩ける": "とけちゃ…う…♡",
        "嬌声を上げ": "あ…んっ♡",
        "甘い吐息": "はぁ…♡",
        "悦びに": "きもちぃ…",
        "淫らな": "えっちな…",
        "したがって": "…",
        "なぜならば": "…",
    }
    # 男性セリフの不自然表現修正（heroine_name_setが必要なので判定付き）
    _MALE_SPEECH_REPLACEMENTS = {
        "可愛いね": "かわいい",
        "気持ちよくしてあげる": "イかせてやる",
        "もっと感じて": "もっと",
        "素直になれよ": "素直にしろ",
        "愛してるよ": "好きだ",
        "気持ちいいだろ？": "いいだろ",
    }
    _HIRAGANA_MAP = {
        "気持ちいい": "きもちぃ",
        "気持ちいぃ": "きもちぃ",
        "気持ち良い": "きもちぃ",
        "大好き": "だいすき",
        "好き": "すき",
        "欲しい": "ほしい",
        "可愛い": "かわいい",
        "怖い": "こわい",
        "嬉しい": "うれしい",
        "凄い": "すごい",
        "駄目": "だめ",
        "嫌": "いや",
        "奥": "おく",
        "中": "なか",
        "熱い": "あつい",
        "深い": "ふかい",
        # v7.0追加
        "痛い": "いたい",
        "汚い": "きたない",
        "苦しい": "くるしい",
        "太い": "ふとい",
        "硬い": "かたい",
        "強い": "つよい",
        "早い": "はやい",
        "速い": "はやい",
        "壊れる": "こわれる",
        "溶ける": "とける",
        "出来ない": "できない",
        # v7.1追加
        "嫌い": "きらい",
        "遅い": "おそい",
        "重い": "おもい",
        "狭い": "せまい",
        # v7.4追加
        "臭い": "くさい",
        "濡れる": "ぬれる",
        "震える": "ふるえる",
        "崩れる": "くずれる",
        "乱れる": "みだれる",
    }
    _fix_count = 0
    for scene in results:
        if "bubbles" not in scene:
            continue
        for bubble in scene["bubbles"]:
            txt = bubble.get("text", "")
            if not txt:
                continue
            original_txt = txt
            # 句点「。」除去
            if "。" in txt:
                txt = txt.replace("。", "…")
            # 男性セリフの不自然表現修正
            speaker = bubble.get("speaker", "")
            is_male = speaker and heroine_name_set and speaker not in heroine_name_set
            if is_male:
                for ng, ok in _MALE_SPEECH_REPLACEMENTS.items():
                    if ng in txt:
                        txt = txt.replace(ng, ok)
            # 設備名混入の部分置換（便器→こんなとこ 等）
            # 「肉便器」はエロ漫画スラングなので保護
            _has_niku = "肉便器" in txt
            _FIXTURE_SUBS = {
                "便器": "こんなとこ",
                "便座": "ここ",
                "手洗い台": "ここ",
                "手洗い鏡": "鏡",
                "トイレットペーパー": "",
            }
            for fw, repl in _FIXTURE_SUBS.items():
                if fw in txt:
                    if fw == "便器" and _has_niku:
                        continue  # 肉便器は保護
                    txt = txt.replace(fw, repl)
            # 置換で生じた空の「…」連続を整理
            while "……" in txt:
                txt = txt.replace("……", "…")
            # 不自然表現を話し言葉に変換
            for ng, ok in _UNNATURAL_REPLACEMENTS.items():
                if ng in txt:
                    txt = ok
                    break
            # ひらがな化（エロシーン向け）
            for kanji, hira in _HIRAGANA_MAP.items():
                if kanji in txt:
                    txt = txt.replace(kanji, hira)
            bubble["text"] = txt
            if txt != original_txt:
                _fix_count += 1
    if _fix_count > 0:
        log_message(f"  セリフ自動修正: {_fix_count}件の不自然表現を修正")

    # 5. シーン間の同一セリフ・SE重複除去（プールから代替置換）
    #    ※重複セリフをプールから代替置換する
    heroine_names = []
    if char_profiles:
        for cp in char_profiles:
            n = cp.get("character_name", "")
            if n:
                heroine_names.append(n)
    _deduplicate_across_scenes(results, theme=theme, heroine_names=heroine_names,
                               char_profiles=char_profiles)

    # 6. 3シーン連続同一locationの自動修正
    _fix_consecutive_locations(results)

    # 7. 吹き出し数上限トリミング（3個以下: ヒロイン1-2 + 男性0-1）
    for scene in results:
        bubbles = scene.get("bubbles", [])
        if len(bubbles) > 3:
            # ヒロインセリフ最大2個 + 男性セリフ0-1個に絞る
            heroine_b = [b for b in bubbles if b.get("speaker", "") != "男"]
            male_b = [b for b in bubbles if b.get("speaker", "") == "男"]
            # ヒロイン: moan > thought > speech の優先度で2個選択
            def _bubble_priority(b):
                btype = b.get("type", "")
                if btype == "moan":
                    return 2
                if btype == "thought":
                    return 1
                return 0
            heroine_b.sort(key=_bubble_priority, reverse=True)
            kept = heroine_b[:2]
            if male_b:
                kept.append(male_b[0])
            scene["bubbles"] = kept[:3]

    # 8. moanタイプ内容修正（3段階: 漢字/助詞/非喘ぎ語彙 → プールから置換）
    # 根拠: MOAN_POOL全400エントリは仮名+装飾のみ。
    #   漢字・助詞がある=LLMの誤生成。
    #   AFTERMATH_POOL語彙(ぼーっと,ぐったり等)は身体状況報告で喘ぎではない。
    _kanji_re = re.compile(r'[\u4e00-\u9faf\u3400-\u4dbf]')
    _sentence_end_re = re.compile(
        r'(だ|です|ます|ない|ない…|ている|てる|する|される|して|した|しい)$')
    _NON_MOAN_WORDS = frozenset([
        "ぼーっと", "ぐったり", "ふわふわ", "ごめん", "どしよ",
        "なにこれ", "もうむり", "もう…むり", "なにこれ…", "ごめん…",
        "どしよ…", "ぼーっと…", "ぐったり…", "ふわふわ…",
    ])
    try:
        from ero_dialogue_pool import (get_moan_pool, get_speech_pool,
                                       pick_replacement, infer_phase)
        _has_pool = True
    except ImportError:
        _has_pool = False

    def _get_moan_pool_with_char(intensity: int) -> list:
        """get_moan_poolにキャラ固有プールを優先混合"""
        pool = []
        if _char_pool and "moan" in _char_pool:
            char_moans = _char_pool["moan"].get(str(intensity), [])
            pool.extend(char_moans)
        pool.extend(get_moan_pool(intensity))
        return pool

    def _get_speech_pool_with_char(btype: str, theme_: str, intensity: int,
                                    scene_idx: int = 0, total: int = 1) -> list:
        """get_speech_poolにキャラ固有プールを優先混合"""
        phase = ""
        if _has_pool:
            try:
                phase = infer_phase(intensity, scene_idx, total)
            except Exception:
                pass
        pool = []
        if _char_pool and btype in _char_pool:
            if phase and isinstance(_char_pool[btype], dict):
                char_lines = _char_pool[btype].get(phase, [])
                pool.extend(char_lines)
        pool.extend(get_speech_pool(btype, theme_, intensity, phase=phase))
        return pool

    _moan_fix_count = 0
    _used_moan_for_fix = set()
    for scene in results:
        intensity = scene.get("intensity", 3)
        for b in scene.get("bubbles", []):
            if b.get("type") != "moan":
                continue
            txt = b.get("text", "")
            if not txt:
                continue
            stripped = txt.rstrip("…♡♡♡")
            is_non_moan = (bool(_kanji_re.search(txt))
                           or bool(_sentence_end_re.search(txt))
                           or stripped in _NON_MOAN_WORDS
                           or txt in _NON_MOAN_WORDS)
            if is_non_moan and _has_pool:
                pool = _get_moan_pool_with_char(intensity)
                replacement = pick_replacement(pool, _used_moan_for_fix, _normalize_bubble_text)
                if replacement:
                    log_message(f"  moan内容修正: 「{txt}」→「{replacement}」")
                    b["text"] = replacement
                    _used_moan_for_fix.add(replacement)
                    _moan_fix_count += 1
    if _moan_fix_count > 0:
        log_message(f"  moanタイプ内容修正: {_moan_fix_count}件")

    # 8b. MOAN_POOL非含有moanの強制プール置換
    # 根拠: LLMが生成する「ふあひっ」「ん゛お゛っ」等の不自然な濁点組み合わせは
    #   Step 8の漢字/助詞チェックでは検出できないが、MOAN_POOLの400エントリには存在しない。
    #   正規化後にプール内に見つからないmoanは全て強制置換する。
    _moan_pool_fix_count = 0
    try:
        from ero_dialogue_pool import get_all_moan_normalized
        _all_moan_norms = get_all_moan_normalized()
    except ImportError:
        _all_moan_norms = None
    if _all_moan_norms and _has_pool:
        for scene in results:
            intensity = scene.get("intensity", 3)
            for b in scene.get("bubbles", []):
                if b.get("type") != "moan":
                    continue
                txt = b.get("text", "")
                if not txt:
                    continue
                norm = _normalize_bubble_text(txt)
                if norm and norm not in _all_moan_norms:
                    pool = _get_moan_pool_with_char(intensity)
                    replacement = pick_replacement(pool, _used_moan_for_fix, _normalize_bubble_text)
                    if replacement:
                        log_message(f"  moanプール外修正: 「{txt}」→「{replacement}」")
                        b["text"] = replacement
                        _used_moan_for_fix.add(replacement)
                        _moan_pool_fix_count += 1
        if _moan_pool_fix_count > 0:
            log_message(f"  MOANプール外強制置換: {_moan_pool_fix_count}件")

    # 9. speechタイプ身体状況報告修正（intensity>=3のアクションシーン）
    # 根拠: CG集のspeechは感情的反応。身体状態の客観報告はナレーションでありセリフ不適。
    _BODY_REPORT_KW = frozenset([
        "涙が", "汗すごい", "汗が", "声出ない", "息できない",
        "力入んない", "頭まっしろ", "目が回る", "指先痺れ",
        "全身痺れ", "まだ震えて", "震えてる", "動けない",
        "立てない", "からだ重い", "呼吸が", "ぼーっと",
        "ぐったり", "ふわふわ", "思考が", "意識が",
    ])
    _body_fix_count = 0
    _used_speech_for_fix = set()
    if _has_pool:
        theme = ""
        if results:
            # メタデータからテーマ取得（5テーマ自動検出）
            all_desc = " ".join(
                s.get("description", "") + " " + s.get("mood", "")
                for s in results[:5]
            )
            if any(k in all_desc for k in ["寝取", "NTR", "ntr"]):
                theme = "ntr"
            elif any(k in all_desc for k in ["襲", "犯さ", "無理矢理", "暴行", "レイプ", "陵辱", "強制", "痴漢"]):
                theme = "forced"
            elif any(k in all_desc for k in ["催眠", "洗脳", "堕落", "調教", "奴隷"]):
                theme = "corruption"
            elif any(k in all_desc for k in ["嫌がる", "逃げ", "恐怖", "怯え", "抵抗"]):
                theme = "reluctant"
            elif any(k in all_desc for k in ["純愛", "恋人", "カップル", "両想"]):
                theme = "vanilla"
            if theme:
                log_message(f"  テーマ自動検出: {theme}")
        _total_scenes = len(results)
        for _si, scene in enumerate(results):
            intensity = scene.get("intensity", 3)
            if intensity < 3:
                continue
            for b in scene.get("bubbles", []):
                if b.get("type") not in ("speech", "thought"):
                    continue
                txt = b.get("text", "")
                if not txt:
                    continue
                is_body_report = any(kw in txt for kw in _BODY_REPORT_KW)
                if is_body_report:
                    pool = _get_speech_pool_with_char(b["type"], theme, intensity, _si, _total_scenes)
                    # プールから身体状況報告を除外（循環置換防止）
                    pool = [t for t in pool
                            if not any(kw in t for kw in _BODY_REPORT_KW)]
                    replacement = pick_replacement(pool, _used_speech_for_fix,
                                                   _normalize_bubble_text)
                    if replacement:
                        log_message(f"  身体状況報告修正({b['type']}): 「{txt}」→「{replacement}」")
                        b["text"] = replacement
                        _used_speech_for_fix.add(replacement)
                        _body_fix_count += 1
    if _body_fix_count > 0:
        log_message(f"  身体状況報告修正: {_body_fix_count}件")

    # 9a. 男性セリフ観察実況修正（「～だな」「～してるな」→ 命令/挑発型に置換）
    _MALE_OBSERVATION_PATTERNS = {
        "いい声だな": "もっと鳴け",
        "敏感だな": "もっと感じろ",
        "いい反応だな": "素直になれよ",
        "いい体だな": "脱げ",
        "いい体してんな": "脱げ",
        "エロい体だな": "もっと見せろ",
        "体は正直だな": "隠すなよ",
        "感じやすいな": "もう我慢すんな",
        "素直になったな": "もっとくれ",
        "とろとろだな": "もっと締めろ",
        "ここも敏感だな": "ここも好きだろ",
        "いい顔だな": "もっとくれ",
        "かわいい顔だな": "かわいい",
        "いい表情だな": "もっと見せろ",
        "たまらん顔だな": "たまんねぇ",
        "極上だな": "最高だ",
        "見事だな": "最高だ",
        # v7.4追加
        "反応がいいな": "もっと感じろ",
        "締まりがいいな": "もっと締めろ",
        "いい匂いだな": "いい匂いだ",
        "素直だな": "素直だろ",
        "正直だな": "正直だろ",
    }
    import re as _re_autofix
    # 「～だな」「～してるな」「～だろうな」で終わる観察型パターン検出
    _MALE_OBS_RE = _re_autofix.compile(r".{4,}(?:だな|するな|してるな|だろうな|てるな)$")
    _male_obs_fix_count = 0
    _used_male_obs_fix = set()
    for scene in results:
        for b in scene.get("bubbles", []):
            speaker = b.get("speaker", "")
            if not (speaker and _is_male_by_name(speaker)):
                continue
            if b.get("type") != "speech":
                continue
            txt = b.get("text", "").strip()
            if not txt:
                continue
            # 1. 辞書マッチ
            replaced = False
            for obs_pattern, obs_replacement in _MALE_OBSERVATION_PATTERNS.items():
                if obs_pattern in txt:
                    old_txt = txt
                    b["text"] = obs_replacement
                    log_message(f"  男性観察型修正: 「{old_txt}」→「{obs_replacement}」")
                    _male_obs_fix_count += 1
                    replaced = True
                    break
            if replaced:
                continue
            # 2. 正規表現マッチ（「～だな」系で終わる4文字以上）
            clean = txt.rstrip("…♡♥")
            if _MALE_OBS_RE.match(clean):
                intensity = scene.get("intensity", 3)
                pool = _get_male_pool_for_theme(theme if theme else "", intensity)
                # 観察型を除外
                pool = [p for p in pool if not _MALE_OBS_RE.match(p.rstrip("…♡♥"))]
                replacement = pick_replacement(pool, _used_male_obs_fix, _normalize_bubble_text)
                if replacement:
                    log_message(f"  男性観察型修正(regex): 「{txt}」→「{replacement}」")
                    b["text"] = replacement
                    _used_male_obs_fix.add(replacement)
                    _male_obs_fix_count += 1
    if _male_obs_fix_count > 0:
        log_message(f"  男性観察型セリフ修正: {_male_obs_fix_count}件")

    # 9b. thought部位ラベル冒頭修正（「胸…」「太もも…」等の部位名冒頭を感覚型に置換）
    _BODY_PART_LABELS = [
        "胸", "太もも", "お尻", "首筋", "耳", "唇", "舌", "指", "脚", "腕",
        "背中", "お腹", "腰", "膝", "肩", "足", "髪", "うなじ", "乳首", "クリ",
        "おっぱい", "おしり", "ふともも", "くちびる", "みみ",
    ]
    _BODY_PART_RE = _re_autofix.compile(
        r"^(" + "|".join(_re_autofix.escape(bp) for bp in _BODY_PART_LABELS) + r")…"
    )
    _thought_body_fix_count = 0
    if _has_pool:
        _used_thought_fix = set()
        for _si_tb, scene in enumerate(results):
            intensity = scene.get("intensity", 3)
            for b in scene.get("bubbles", []):
                if b.get("type") != "thought":
                    continue
                txt = b.get("text", "")
                if not txt:
                    continue
                m = _BODY_PART_RE.match(txt)
                if m:
                    pool = _get_speech_pool_with_char("thought", theme if theme else "",
                                                      intensity, _si_tb, len(results))
                    # 部位ラベル冒頭を除外
                    pool = [t for t in pool if not _BODY_PART_RE.match(t)]
                    replacement = pick_replacement(pool, _used_thought_fix, _normalize_bubble_text)
                    if replacement:
                        log_message(f"  thought部位ラベル修正: 「{txt}」→「{replacement}」")
                        b["text"] = replacement
                        _used_thought_fix.add(replacement)
                        _thought_body_fix_count += 1
    if _thought_body_fix_count > 0:
        log_message(f"  thought部位ラベル冒頭修正: {_thought_body_fix_count}件")

    # 10. 同一シーン内テキスト重複修正
    _intra_dup_count = 0
    if _has_pool:
        _total_s10 = len(results)
        for _si10, scene in enumerate(results):
            intensity = scene.get("intensity", 3)
            bubbles = scene.get("bubbles", [])
            seen_texts = set()
            for b in bubbles:
                txt = b.get("text", "")
                if not txt:
                    continue
                if txt in seen_texts:
                    btype = b.get("type", "speech")
                    if btype == "moan":
                        pool = _get_moan_pool_with_char(intensity)
                        repl = pick_replacement(pool, _used_moan_for_fix,
                                                _normalize_bubble_text)
                    else:
                        pool = _get_speech_pool_with_char(btype, theme, intensity, _si10, _total_s10)
                        repl = pick_replacement(pool, _used_speech_for_fix,
                                                _normalize_bubble_text)
                    if repl:
                        log_message(f"  シーン内重複修正: 「{txt}」→「{repl}」")
                        b["text"] = repl
                        _used_speech_for_fix.add(repl)
                        _intra_dup_count += 1
                seen_texts.add(txt)
    if _intra_dup_count > 0:
        log_message(f"  シーン内重複修正: {_intra_dup_count}件")

    # 11. story_flow重複修正（同一テキストの2回目以降を空にする）
    _seen_flows = {}
    _flow_fix_count = 0
    for scene in results:
        flow = scene.get("story_flow", "")
        if flow and len(flow) >= 10:
            sid = scene.get("scene_id", "?")
            if flow in _seen_flows:
                scene["story_flow"] = ""
                _flow_fix_count += 1
                log_message(f"  S{sid}: story_flow重複削除（S{_seen_flows[flow]}と同一）")
            else:
                _seen_flows[flow] = sid
    if _flow_fix_count > 0:
        log_message(f"  story_flow重複修正: {_flow_fix_count}件")

    # 11b. キャラ名途切れ修復（フルネーム直後に助詞がない場合、姓のみに置換）
    # Haiku 3でフルネーム後のトークン生成が不安定になり助詞+動詞が欠落する問題への対策
    _VALID_AFTER_NAME = set("がをのはにとでもへやより、。）)」』】")
    _name_trunc_count = 0
    if correct_names:
        # フルネーム→短縮名マップを構築
        _name_short_map = {}  # full_name -> short_name
        for full_name in correct_names:
            if not full_name or len(full_name) < 2:
                continue
            # 最初の「・」「 」「＝」「　」の前を姓とする
            short = full_name
            for sep in ["・", " ", "＝", "　"]:
                idx = full_name.find(sep)
                if idx > 0:
                    short = full_name[:idx]
                    break
            if short != full_name:
                _name_short_map[full_name] = short

        if _name_short_map:
            _first_occurrence_done = {}  # full_name -> bool (シーン1でフルネーム初出済みか)
            for i, scene in enumerate(results):
                sid = scene.get("scene_id", i + 1)
                desc = scene.get("description", "")
                if not desc:
                    continue
                for full_name, short_name in _name_short_map.items():
                    if full_name not in desc:
                        continue
                    # シーン1（最初の出現）はフルネームを保持
                    if full_name not in _first_occurrence_done:
                        _first_occurrence_done[full_name] = True
                        # ただしシーン1でも途切れ箇所はチェック
                        # 最初の出現はスキップし、2回目以降のみ修復
                        positions = []
                        start = 0
                        while True:
                            pos = desc.find(full_name, start)
                            if pos < 0:
                                break
                            positions.append(pos)
                            start = pos + len(full_name)
                        if len(positions) <= 1:
                            continue
                        # 2回目以降の出現のみ処理（逆順で置換）
                        new_desc = desc
                        for pos in reversed(positions[1:]):
                            after_pos = pos + len(full_name)
                            if after_pos < len(new_desc):
                                after_char = new_desc[after_pos]
                                if after_char not in _VALID_AFTER_NAME:
                                    new_desc = new_desc[:pos] + short_name + new_desc[after_pos:]
                                    _name_trunc_count += 1
                            else:
                                # 文末にフルネーム→短縮名に
                                new_desc = new_desc[:pos] + short_name + new_desc[after_pos:]
                                _name_trunc_count += 1
                        scene["description"] = new_desc
                    else:
                        # シーン2以降: 全出現を検査
                        positions = []
                        start = 0
                        while True:
                            pos = desc.find(full_name, start)
                            if pos < 0:
                                break
                            positions.append(pos)
                            start = pos + len(full_name)
                        if not positions:
                            continue
                        new_desc = desc
                        for pos in reversed(positions):
                            after_pos = pos + len(full_name)
                            if after_pos < len(new_desc):
                                after_char = new_desc[after_pos]
                                if after_char not in _VALID_AFTER_NAME:
                                    new_desc = new_desc[:pos] + short_name + new_desc[after_pos:]
                                    _name_trunc_count += 1
                            else:
                                new_desc = new_desc[:pos] + short_name + new_desc[after_pos:]
                                _name_trunc_count += 1
                        scene["description"] = new_desc
                        desc = new_desc  # 更新後の値で次のキャラ名をチェック
    if _name_trunc_count > 0:
        log_message(f"  キャラ名途切れ修復: {_name_trunc_count}件（フルネーム→姓に置換）")

    # 12. description先頭30字重複修正（全既出シーンと比較、最初の句点後に状況挿入）
    # 方針: 「場所。状況描写...」の「。」の後にvariation文を挿入して先頭30字を変化させる
    _INTENSITY_DESC_INSERTS = {
        1: [
            "不穏な空気が漂う中、", "緊張感が張り詰める中、", "嫌な予感を覚えながら、",
            "周囲を警戒しつつ、", "息を殺して様子を窺いながら、", "心の準備ができないまま、",
            "逃げ場のない状況で、", "背筋に冷たいものが走る中、",
        ],
        2: [
            "恥ずかしさで体が強張る中、", "心臓の鼓動が速まる中、", "唇を噛みしめながら、",
            "触れられた箇所が熱を持ち始め、", "頬が紅潮していくのを感じながら、",
            "視線を逸らしつつも意識が集中し、", "手足が小刻みに震える中、",
            "初めての感覚に体が跳ねる中、",
        ],
        3: [
            "快感に抗いきれなくなる中、", "甘い痺れが全身に広がり、", "抵抗の力が弱まっていく中、",
            "息が荒くなりながら、", "肌が敏感になっていくのを感じ、", "声を抑えきれなくなりながら、",
            "腰が勝手に動いてしまう中、", "意識が快楽に染まり始める中、",
        ],
        4: [
            "快楽に支配されつつある中、", "もう逃れられないと悟りながら、", "理性が揺らぎ始める中、",
            "全身が敏感に反応する中、", "体の芯から熱が溢れ出す中、", "抵抗の意志が溶けていく中、",
            "自分の声が止められなくなり、", "全身の力が抜けていく中、",
        ],
        5: [
            "理性が完全に崩壊した状態で、", "快楽の波に全身が呑まれ、", "もう何も考えられなくなり、",
            "絶頂の余韻が全身を支配する中、", "白い光に視界が塗りつぶされる中、",
            "意識が飛びそうになりながら、", "体が痙攣を繰り返す中、",
            "自分が誰かも分からなくなり、",
        ],
    }
    _desc_fix_count = 0
    _seen_desc_prefixes = {}  # prefix_30char -> first scene_id
    for i, scene in enumerate(results):
        desc = scene.get("description", "")
        if not desc or len(desc) < 30:
            sid = scene.get("scene_id", i + 1)
            if desc:
                _seen_desc_prefixes[desc[:30]] = sid
            continue
        prefix30 = desc[:30]
        sid = scene.get("scene_id", i + 1)
        if prefix30 in _seen_desc_prefixes:
            intensity = scene.get("intensity", 3)
            inserts = _INTENSITY_DESC_INSERTS.get(intensity, _INTENSITY_DESC_INSERTS[3])
            # 最初の句点を探して挿入位置を決定
            insert_pos = desc.find("。")
            if insert_pos >= 0 and insert_pos < len(desc) - 1:
                insert_pos += 1  # 「。」の直後
            else:
                # 句点なし → 「、」の後に挿入
                insert_pos = desc.find("、")
                if insert_pos >= 0 and insert_pos < len(desc) - 1:
                    insert_pos += 1
                else:
                    insert_pos = 0  # フォールバック: 先頭
            # 未使用のバリエーションを選択（自intensity→隣接intensity→全intensityの順で探索）
            chosen_insert = None
            # 1) 自intensityの全バリエーション
            for try_idx in range(_desc_fix_count, _desc_fix_count + len(inserts)):
                candidate = inserts[try_idx % len(inserts)]
                new_desc = desc[:insert_pos] + candidate + desc[insert_pos:]
                if new_desc[:30] not in _seen_desc_prefixes:
                    chosen_insert = candidate
                    break
            # 2) 隣接intensity（±1）のバリエーションも試す
            if chosen_insert is None:
                for adj_i in [max(1, intensity - 1), min(5, intensity + 1)]:
                    if adj_i == intensity:
                        continue
                    adj_inserts = _INTENSITY_DESC_INSERTS.get(adj_i, [])
                    for candidate in adj_inserts:
                        new_desc = desc[:insert_pos] + candidate + desc[insert_pos:]
                        if new_desc[:30] not in _seen_desc_prefixes:
                            chosen_insert = candidate
                            break
                    if chosen_insert:
                        break
            # 3) 全intensity横断（最終手段）
            if chosen_insert is None:
                for any_i in range(1, 6):
                    if any_i == intensity:
                        continue
                    for candidate in _INTENSITY_DESC_INSERTS.get(any_i, []):
                        new_desc = desc[:insert_pos] + candidate + desc[insert_pos:]
                        if new_desc[:30] not in _seen_desc_prefixes:
                            chosen_insert = candidate
                            break
                    if chosen_insert:
                        break
            # 4) それでも見つからない → 挿入位置を先頭に変更して再試行
            if chosen_insert is None:
                insert_pos = 0
                for any_i in range(1, 6):
                    for candidate in _INTENSITY_DESC_INSERTS.get(any_i, []):
                        new_desc = candidate + desc
                        if new_desc[:30] not in _seen_desc_prefixes:
                            chosen_insert = candidate
                            break
                    if chosen_insert:
                        break
            if chosen_insert is None:
                # 最終フォールバック: 全て枯渇（極稀）→ 先頭にシーン固有テキスト
                chosen_insert = f"この場面では、"
                insert_pos = 0
            new_desc = desc[:insert_pos] + chosen_insert + desc[insert_pos:]
            scene["description"] = new_desc
            _desc_fix_count += 1
            log_message(f"  S{sid}: description重複修正（S{_seen_desc_prefixes[prefix30]}と一致、挿入: {chosen_insert[:15]}...）")
            # 修正後のprefix30も登録（二次重複防止）
            new_prefix30 = new_desc[:30]
            if new_prefix30 not in _seen_desc_prefixes:
                _seen_desc_prefixes[new_prefix30] = sid
        else:
            _seen_desc_prefixes[prefix30] = sid
    if _desc_fix_count > 0:
        log_message(f"  description重複修正: {_desc_fix_count}件")

    # 13. character_feelings重複修正（全既出シーンと比較、一致→intensity別テンプレートで差し替え）
    _FEELINGS_VARIANTS = {
        1: [
            "まだ状況を理解できず、困惑と不安を感じている",
            "何かが起きる予感に、体が硬直している",
            "突然の展開に戸惑い、どう反応していいか分からない",
            "不穏な空気を感じ取り、本能的に危険を察知している",
            "現実感がなく、夢の中にいるような錯覚を覚えている",
            "逃げたい気持ちと動けない恐怖が入り混じっている",
        ],
        2: [
            "体が反応し始めていることに戸惑い、羞恥に震えている",
            "触れられるたびに走る電流のような感覚に、抗えなくなっている",
            "恥ずかしさで顔が真っ赤になりながらも、意識が集中していく",
            "初めての感覚に戸惑いつつ、体が勝手に求めてしまう",
            "嫌だと思うのに体が言うことを聞かず、混乱している",
            "緊張と期待が入り混じる複雑な感情に揺れている",
        ],
        3: [
            "快感に抗いきれなくなり、自分の反応に罪悪感を覚えている",
            "嫌なはずなのに体が正直に反応してしまう自分に絶望している",
            "理性と本能の間で揺れ動き、心が引き裂かれそうになっている",
            "声を抑えようとしても漏れてしまう喘ぎに、羞恥を感じている",
            "快楽に流されまいと必死に意識を保とうとしている",
            "自分の体がこんなにも敏感だったことに驚き、戸惑っている",
        ],
        4: [
            "快楽に支配されつつも、最後の理性でかろうじて抵抗している",
            "抵抗する意志すら快感に塗り替えられていくのを感じている",
            "もう考えることすらできず、快楽の波に身を委ねている",
            "体の奥から湧き上がる衝動に、心が完全に呑まれそうになっている",
            "恥も外聞もなく声を上げてしまう自分を、遠くから見ている気分",
            "全身の感覚が研ぎ澄まされ、触れられる場所全てが快感に変わる",
        ],
        5: [
            "完全に快楽に溺れ、もう抵抗する気力すら失っている",
            "全身が痙攣し、思考も感情も快楽一色に染まっている",
            "意識が遠のきかけながらも、快楽だけが鮮明に感じられる",
            "自分が自分でなくなっていく感覚に、恐怖すら感じなくなっている",
            "何度目かも分からない絶頂に、体が壊れそうになっている",
            "もう何も考えられず、ただ快楽を受け入れることしかできない",
        ],
    }
    _feelings_fix_count = 0
    _seen_feelings = {}  # frozen feelings values string -> first scene_id
    for i, scene in enumerate(results):
        cf = scene.get("character_feelings", {})
        if not cf:
            continue
        sid = scene.get("scene_id", i + 1)
        # validate_scriptと同じロジック: values()のみで比較（キー名は無視）
        cf_key = str(sorted(cf.values()))
        if len(cf_key) < 15:
            continue
        if cf_key in _seen_feelings:
            intensity = scene.get("intensity", 3)
            variants = _FEELINGS_VARIANTS.get(intensity, _FEELINGS_VARIANTS[3])
            # 全バリアントを試し、未使用のものを選択
            chosen = None
            for try_idx in range(_feelings_fix_count, _feelings_fix_count + len(variants)):
                candidate = variants[try_idx % len(variants)]
                candidate_key = str(sorted([candidate]))
                if candidate_key not in _seen_feelings:
                    chosen = candidate
                    break
            if chosen is None:
                # 全バリアント使用済み → シーン番号を付加してユニーク化
                base = variants[_feelings_fix_count % len(variants)]
                chosen = f"{base}（シーン{sid}）"
            for key in cf:
                cf[key] = chosen
                break
            _feelings_fix_count += 1
            log_message(f"  S{sid}: character_feelings重複修正（S{_seen_feelings[cf_key]}と同一）")
            # 更新後のキーで登録
            cf_key_new = str(sorted(cf.values()))
            if cf_key_new not in _seen_feelings:
                _seen_feelings[cf_key_new] = sid
        else:
            _seen_feelings[cf_key] = sid
    if _feelings_fix_count > 0:
        log_message(f"  character_feelings重複修正: {_feelings_fix_count}件")

    # 14. story_flow先頭20字重複修正
    _STORYFLOW_PREFIXES = [
        "さらに、", "その後、", "やがて、", "次第に、", "一方で、",
        "そして、", "続けて、", "同時に、", "ここから、", "それから、",
    ]
    _sf_fix_count = 0
    _seen_sf = {}  # prefix20 -> first scene_id
    for i, scene in enumerate(results):
        sf = scene.get("story_flow", "")
        if not sf or len(sf) < 20:
            sid = scene.get("scene_id", i + 1)
            if sf:
                _seen_sf[sf[:20]] = sid
            continue
        sf20 = sf[:20]
        sid = scene.get("scene_id", i + 1)
        if sf20 in _seen_sf:
            # 先頭に接続詞を追加して20字を変化させる
            for try_idx in range(_sf_fix_count, _sf_fix_count + len(_STORYFLOW_PREFIXES)):
                prefix = _STORYFLOW_PREFIXES[try_idx % len(_STORYFLOW_PREFIXES)]
                new_sf = prefix + sf
                if new_sf[:20] not in _seen_sf:
                    scene["story_flow"] = new_sf
                    _sf_fix_count += 1
                    _seen_sf[new_sf[:20]] = sid
                    break
            else:
                _seen_sf[sf20] = sid
        else:
            _seen_sf[sf20] = sid
    if _sf_fix_count > 0:
        log_message(f"  story_flow重複修正: {_sf_fix_count}件")

    # 15. speech重複修正（異なるシーンで同一セリフ → 微小バリエーション付加）
    _sp_fix_count = 0
    _seen_speech = {}  # line_text -> (scene_idx, bubble_idx)
    for i, scene in enumerate(results):
        bubbles = scene.get("bubbles", [])
        sid = scene.get("scene_id", i + 1)
        for bi, b in enumerate(bubbles):
            if b.get("type") != "speech":
                continue
            line = b.get("text", "")
            if not line or len(line) < 4:
                continue
            if line in _seen_speech:
                # 微小変化を付加: 末尾に「…」「っ」「♡」などを追加/変更
                _SPEECH_SUFFIXES = ["…", "っ", "…♡", "…っ"]
                modified = False
                for suffix in _SPEECH_SUFFIXES:
                    new_line = line.rstrip("…♡っ。、") + suffix
                    if new_line != line and new_line not in _seen_speech:
                        b["text"] = new_line
                        _seen_speech[new_line] = (i, bi)
                        _sp_fix_count += 1
                        modified = True
                        break
                if not modified:
                    _seen_speech[line] = (i, bi)
            else:
                _seen_speech[line] = (i, bi)
    if _sp_fix_count > 0:
        log_message(f"  speech重複修正: {_sp_fix_count}件")

    # 16. description抽象的修正（intensity≥4で具体的キーワードがない → 具体表現を自動追加）
    _CONCRETE_ADDITIONS = {
        4: [
            "激しいピストンで腰が打ちつけられ、",
            "深く挿入された状態で腰を押さえつけられ、",
            "後ろから突き上げられて身体が跳ね、",
            "騎乗位で腰を打ちつけながら、",
            "脚を大きく開かされた体勢で、",
            "背後から抱きかかえられ腰を突かれ、",
            "壁に押し付けられ腰を掴まれた体勢のまま、",
            "四つん這いの姿勢で腰を掴まれ、",
        ],
        5: [
            "限界を超えた激しいピストンに身体が痙攣し、",
            "奥まで突き上げられ仰け反りながら、",
            "腰を掴まれ激しいピストンで突かれ続け、",
            "全身が震えるほどの快感に耐えきれず、",
            "何度もイかされビクビクと痙攣しながら、",
            "力が抜けた身体を好きにされ挿入が続き、",
            "ピストンの快楽に意識が飛びそうになり、",
            "汗だくの身体を抱え上げられ突かれ、",
        ],
    }
    _CONCRETE_KW_CHECK = [
        "正常位", "後背位", "騎乗位", "バック", "挿入", "ピストン", "腰を",
        "突き", "咥え", "舐め", "フェラ", "パイズリ", "手コキ", "指を",
        "汗", "涙", "震え", "痙攣", "力が抜け", "仰け反", "ビクビク",
        "掴み", "押さえ", "開かせ", "四つん這い", "うつ伏せ",
        "胸を", "腰を", "脚を", "太もも", "尻を",
    ]
    _desc_fix_count = 0
    for i, scene in enumerate(results):
        intensity = scene.get("intensity", 0)
        if intensity < 4:
            continue
        desc = scene.get("description", "")
        if not desc or len(desc) < 10:
            continue
        if any(kw in desc for kw in _CONCRETE_KW_CHECK):
            continue
        # 具体表現を先頭に追加
        level = min(intensity, 5)
        additions = _CONCRETE_ADDITIONS.get(level, _CONCRETE_ADDITIONS[4])
        addition = additions[i % len(additions)]
        scene["description"] = addition + desc
        _desc_fix_count += 1
    if _desc_fix_count > 0:
        log_message(f"  description具体化修正: {_desc_fix_count}件")

    # 16b. description連続類似修正（3連続で同一行為キーワード→中央シーンを差し替え）
    _DESC_ACT_KW_FIX = ["膣奥", "突かれ", "責められ", "腰を振", "ピストン",
                         "挿入", "フェラ", "パイズリ", "騎乗", "バック",
                         "正常位", "四つん這い"]
    _DESC_SYNONYMS = {
        "ピストン": ["律動", "腰の動き", "突き上げ"],
        "膣奥": ["最奥部", "子宮口付近", "一番奥"],
        "突かれ": ["貫かれ", "押し込まれ", "攻められ"],
        "挿入": ["結合", "繋がった状態で", "受け入れた体勢で"],
    }
    _desc_sim_fix = 0
    _desc_kw_list = []
    for scene in results:
        desc = scene.get("description", "")
        kws = frozenset(kw for kw in _DESC_ACT_KW_FIX if kw in desc)
        _desc_kw_list.append(kws)
    for k in range(2, len(_desc_kw_list)):
        common = _desc_kw_list[k] & _desc_kw_list[k-1] & _desc_kw_list[k-2]
        if len(common) >= 2:
            # 中央シーン(k-1)のdescriptionを修正: 共通キーワードを類語に置換
            mid = results[k-1]
            desc = mid.get("description", "")
            for ckw in common:
                syns = _DESC_SYNONYMS.get(ckw, [])
                if syns:
                    desc = desc.replace(ckw, syns[k % len(syns)], 1)
            mid["description"] = desc
            _desc_kw_list[k-1] = frozenset(kw for kw in _DESC_ACT_KW_FIX if kw in desc)
            _desc_sim_fix += 1
    if _desc_sim_fix > 0:
        log_message(f"  description連続類似修正: {_desc_sim_fix}件")

    # 16c. title品質修正（句点除去・location混入修正・description混入修正）
    _TITLE_MOOD_WORDS = [
        "背徳", "快楽", "陶酔", "絶望", "衝動", "狂気", "恍惚", "堕落",
        "覚醒", "屈辱", "暴走", "服従", "解放", "執着", "欲望", "情欲",
    ]
    _title_quality_fix = 0
    for scene in results:
        title = scene.get("title", "")
        if not title:
            continue
        sid = scene.get("scene_id", "?")
        old_title = title
        need_regenerate = False

        # 句点「。」除去
        if "。" in title:
            title = title.replace("。", "").strip()

        # location混入チェック: locationテキストがtitleに含まれる場合は除去
        loc = scene.get("location_detail", scene.get("location", ""))
        if loc and len(loc) >= 4 and loc in title:
            title = title.replace(loc, "")
            # 連続する助詞の整理（「のの」「のでの」等）
            title = re.sub(r'([のでにてへ])\1+', r'\1', title)
            title = re.sub(r'の(で|に|て|へ)の', r'\1', title)
            title = title.strip("のでにてへ、 ")
            if len(title) < 3:
                need_regenerate = True

        # description混入チェック: titleの先頭10字がdescriptionに含まれる場合
        desc = scene.get("description", "")
        if desc and len(title) >= 10:
            title_head = title[:10]
            if title_head in desc:
                need_regenerate = True
        # 文体チェック: タイトルが文末表現で終わる→description的な文が混入
        if len(title) >= 6 and re.search(
                r'(された|されて|ながら|ている|ていく|ていた|かれて|かれた|声が|体が)$', title):
            need_regenerate = True
        # 助詞で開始するtitle（文の途中から切り取られた形跡）
        if title and title[0] in "のとがをでにへはも":
            need_regenerate = True
        # 送り仮名・漢字の途中で途切れるtitle
        if len(title) >= 8 and title[-1] in "張貼掛掲載映写薄汚":
            need_regenerate = True

        # titleが3文字未満or再生成フラグ → mood+intensityベースで再生成
        if need_regenerate or len(title) < 3:
            mood = scene.get("mood", "")
            intensity = scene.get("intensity", 3)
            mood_word = _TITLE_MOOD_WORDS[(int(sid) if isinstance(sid, int) else 0) % len(_TITLE_MOOD_WORDS)]
            if mood and len(mood) >= 2:
                title = f"{mood_word}の{mood[:8]}"
            else:
                title = f"{mood_word}のシーン{sid}"

        if title != old_title:
            scene["title"] = title
            _title_quality_fix += 1
            log_message(f"  S{sid}: title品質修正「{old_title}」→「{title}」")
    if _title_quality_fix > 0:
        log_message(f"  title品質修正: {_title_quality_fix}件")

    # 17. title重複修正（同一titleの2回目以降を場所+状況で差し替え）
    _seen_titles_af = set()
    _title_fix_af = 0
    for scene in results:
        t = scene.get("title", "")
        if t in _seen_titles_af:
            sid = scene.get("scene_id", "?")
            desc = scene.get("description", "")[:20]
            loc = scene.get("location_detail", scene.get("location", ""))
            mood = scene.get("mood", "")[:10]
            new_title = f"{mood}の{desc}" if mood and desc else f"シーン{sid}"
            # 重複しないようにする
            if new_title in _seen_titles_af:
                new_title = f"{new_title}({sid})"
            scene["title"] = new_title
            _title_fix_af += 1
            log_message(f"  S{sid}: title重複修正「{t}」→「{new_title}」")
        _seen_titles_af.add(scene.get("title", ""))
    if _title_fix_af > 0:
        log_message(f"  title重複修正: {_title_fix_af}件")

    # 18. titleキーワード過剰使用修正（同じキーワードが3回以上→場所/mood/行為ベースに差し替え）
    _TITLE_KW_FIX = ["膣奥", "理性", "崩壊", "限界", "快感", "堕ち", "抵抗",
                      "連続", "激突", "責め", "声", "最後"]
    for kw in _TITLE_KW_FIX:
        kw_scenes = [(i, s) for i, s in enumerate(results) if kw in s.get("title", "")]
        if len(kw_scenes) >= 3:
            # 3回目以降の出現を差し替え
            for idx, (i, scene) in enumerate(kw_scenes):
                if idx < 2:
                    continue  # 最初の2回は許容
                sid = scene.get("scene_id", "?")
                old_title = scene["title"]
                loc = scene.get("location_detail", scene.get("location", ""))[:10]
                mood = scene.get("mood", "")[:10]
                intensity = scene.get("intensity", 3)
                _alt_kw = ["衝動", "背徳", "交わり", "激情", "陶酔", "震え", "熱", "嵐"]
                alt = _alt_kw[i % len(_alt_kw)]
                new_title = f"{alt}の{loc}" if loc else f"{alt}のシーン{sid}"
                scene["title"] = new_title
                log_message(f"  S{sid}: titleキーワード過剰修正「{old_title}」→「{new_title}」")

    # 19. title長制限（Step 17-18で生成されたtitleも含め25文字以内に）
    for scene in results:
        title = scene.get("title", "")
        if len(title) > 25:
            scene["title"] = title[:25].rstrip("。、…")

    # 20. intensity不一致自動修正（♡除去/丁寧語短縮）
    _intensity_fix_count = 0
    for scene in results:
        intensity = scene.get("intensity", 3)
        for bubble in scene.get("bubbles", []):
            txt = bubble.get("text", "")
            if not txt:
                continue
            orig = txt
            if intensity <= 2 and "♡" in txt:
                txt = txt.replace("♡", "")
            if intensity >= 4 and bubble.get("type") in ("speech", "thought"):
                txt = txt.replace("です", "")
                txt = txt.replace("ます", "")
                txt = txt.replace("ください", "…♡")
            # 空になった場合は元に戻す
            stripped = txt.replace("…", "").replace("♡", "").strip()
            if not stripped:
                txt = orig
            if txt != orig:
                bubble["text"] = txt
                _intensity_fix_count += 1
    if _intensity_fix_count > 0:
        log_message(f"  intensity不一致修正: {_intensity_fix_count}件")

    return results


def _fix_consecutive_locations(results: list) -> None:
    """location多様性の自動修正。3連続同一 + 全体70%以上同一に対応。"""
    # 場所内位置バリエーション（単一ロケーションシナリオ用）
    _MICRO_LOCATIONS = {
        "トイレ": ["洗面台の前", "入口付近の壁際", "隣の個室", "清掃用具入れの奥", "手洗い場の鏡前"],
        "教室": ["教卓の前", "窓際の席", "ロッカーの陰", "教室の隅", "廊下に面した壁際"],
        "寝室": ["ベッドの上", "窓際", "クローゼットの前", "ドア付近", "鏡台の前"],
        "浴室": ["浴槽の中", "洗い場", "脱衣所", "シャワーの下", "浴室の壁際"],
        "オフィス": ["デスクの上", "応接ソファ", "給湯室", "会議室", "コピー機の裏"],
    }
    _LOC_VARIATIONS = [
        ("窓際", "near_window, window"),
        ("隅", "corner"),
        ("入り口付近", "doorway"),
        ("奥まった場所", "dimly_lit"),
        ("壁際", "against_wall"),
        ("中央", "center"),
        ("片隅のテーブル付近", "table"),
        ("柱の陰", "pillar, shadow"),
    ]
    import random as _rng

    locations_list = []
    for scene in results:
        loc = scene.get("location_detail", scene.get("location", ""))
        locations_list.append(loc.strip().lower() if loc else "")

    # --- 全体の同一location率チェック ---
    if len(locations_list) >= 10:
        from collections import Counter as _Counter
        loc_counter = _Counter(l for l in locations_list if l)
        if loc_counter:
            most_common_loc, most_common_count = loc_counter.most_common(1)[0]
            ratio = most_common_count / len(locations_list)
            if ratio > 0.70:  # 70%以上が同一location
                # micro-locationで分散させる
                micro_pool = None
                for key, micros in _MICRO_LOCATIONS.items():
                    if key.lower() in most_common_loc or key in most_common_loc:
                        micro_pool = micros
                        break
                if not micro_pool:
                    micro_pool = [v[0] for v in _LOC_VARIATIONS]

                micro_idx = 0
                fix_micro = 0
                for k, scene in enumerate(results):
                    loc = locations_list[k]
                    if loc == most_common_loc and k % 3 == 1:  # 3シーンに1つ変化
                        new_micro = micro_pool[micro_idx % len(micro_pool)]
                        orig_loc_detail = scene.get("location_detail", scene.get("location", ""))
                        scene["location_detail"] = f"{orig_loc_detail}（{new_micro}）"
                        locations_list[k] = scene["location_detail"].strip().lower()
                        micro_idx += 1
                        fix_micro += 1
                if fix_micro > 0:
                    log_message(f"  location同一率{ratio:.0%}→micro-location分散: {fix_micro}件")

    # --- 3シーン連続同一locationの修正（既存ロジック維持） ---
    fix_count = 0
    for k in range(2, len(locations_list)):
        if (locations_list[k]
                and locations_list[k] == locations_list[k-1] == locations_list[k-2]):
            mid = results[k - 1]
            orig_loc = mid.get("location_detail", mid.get("location", ""))
            if not orig_loc:
                continue
            if any(v[0] in orig_loc for v in _LOC_VARIATIONS):
                continue
            var_jp, var_tags = _rng.choice(_LOC_VARIATIONS)
            new_loc = f"{orig_loc}の{var_jp}"
            mid["location_detail"] = new_loc
            sd = mid.get("sd_prompt", "")
            if sd:
                existing = {t.strip().lower().replace(" ", "_") for t in sd.split(",") if t.strip()}
                new_tags = [t.strip() for t in var_tags.split(",") if t.strip()]
                added = []
                for nt in new_tags:
                    if nt.lower() not in existing:
                        added.append(nt)
                if added:
                    mid["sd_prompt"] = sd.rstrip(", ") + ", " + ", ".join(added)
            locations_list[k - 1] = new_loc.strip().lower()
            fix_count += 1

    if fix_count > 0:
        log_message(f"  location連続修正: {fix_count}件")


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
    "modern_school": {
        "keywords": ["学園", "学校", "クラスメイト", "同級生", "先輩",
                     "後輩", "教師", "先生", "生徒", "部活", "文化祭",
                     "体育祭", "放課後", "部室", "屋上"],
        "replace": {
            "futon": "bed",
            "tatami": "floor",
            "shoji": "window",
            "andon": "fluorescent_light",
            "stone_wall": "concrete_wall",
        },
        "prohibit": {"torch", "candlelight", "medieval", "stone",
                     "fantasy", "traditional", "rural"},
        "append": ["school", "school_uniform", "indoors"],
        "prompt_hint": "現代日本の学園（教室、廊下、屋上、体育館、プール、図書室、保健室）。学校の雰囲気を重視",
    },
    "modern_urban": {
        "keywords": ["都会", "東京", "マンション", "アパート", "オフィス",
                     "ビル", "繁華街", "ラブホ", "カラオケ", "居酒屋",
                     "コンビニ", "駅", "電車", "バス", "タクシー",
                     "ネットカフェ", "現代"],
        "replace": {
            "futon": "bed",
            "tatami": "wooden_floor",
            "shoji": "curtains",
            "andon": "lamp",
            "stone_wall": "concrete_wall",
        },
        "prohibit": {"torch", "medieval", "stone", "fantasy",
                     "traditional", "rural", "old_house"},
        "append": ["indoors", "modern"],
        "prompt_hint": "現代都市（マンション、オフィスビル、ラブホテル、居酒屋、電車内）。都会的な雰囲気",
    },
    "hot_spring": {
        "keywords": ["温泉", "露天風呂", "旅館", "混浴", "湯けむり",
                     "秘湯", "温泉旅行", "大浴場", "脱衣所"],
        "replace": {
            "bed": "futon",
            "bedroom": "japanese_room",
            "apartment": "ryokan_room",
            "hotel_room": "ryokan_room",
            "curtains": "noren",
        },
        "prohibit": {"office", "elevator", "subway", "highway",
                     "skyscraper", "urban"},
        "append": ["onsen", "steam", "wet", "towel", "japanese",
                   "warm_lighting"],
        "prompt_hint": "温泉・旅館（露天風呂、岩風呂、檜風呂、湯けむり、暖簾、浴衣、タオル）。蒸気と湯の質感を重視",
    },
    "beach_resort": {
        "keywords": ["ビーチ", "海", "水着", "プール", "リゾート",
                     "南国", "離島", "海辺", "海水浴", "日焼け",
                     "サーフ", "ヨット", "砂浜"],
        "replace": {
            "futon": "bed",
            "tatami": "wooden_floor",
            "shoji": "window",
        },
        "prohibit": {"medieval", "stone", "torch", "traditional",
                     "rural", "old_house", "snow"},
        "append": ["outdoors", "beach", "ocean", "sky", "sunlight",
                   "palm_tree"],
        "prompt_hint": "ビーチリゾート（砂浜、ヤシの木、青い海と空、白い砂浜、パラソル、水着）。開放的な南国感",
    },
    "sci_fi": {
        "keywords": ["SF", "宇宙", "近未来", "サイバーパンク", "ロボット",
                     "アンドロイド", "宇宙船", "コロニー", "メカ"],
        "replace": {
            "futon": "bed",
            "tatami": "metal_floor",
            "shoji": "sliding_door",
            "wooden_wall": "metal_wall",
            "andon": "neon_light",
            "stone_wall": "metal_wall",
        },
        "prohibit": {"medieval", "traditional", "rural", "old_house",
                     "tatami", "shoji", "torch", "candlelight"},
        "append": ["sci-fi", "futuristic", "neon", "hologram",
                   "metal", "chrome"],
        "prompt_hint": "SF・近未来（メタリックな壁、ネオンライト、ホログラム、宇宙船内、ハイテク機器）。未来的な無機質感",
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
                       setting_style: Optional[dict] = None,
                       male_tags: str = "", time_tags: str = "",
                       location_type: str = "",
                       sd_quality_tags: str = "",
                       sd_prefix_tags: str = "",
                       sd_suffix_tags: str = "") -> list:
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
        1: ["calm", "closed_mouth", "looking_away", "embarrassed"],
        2: ["blush", "looking_down", "covering_face", "shy",
            "averting_eyes", "fidgeting"],
        3: ["blush", "parted_lips", "panting", "nervous", "heavy_breathing",
            "light_sweat", "clenched_teeth", "biting_lip"],
        4: ["open_mouth", "moaning", "tears", "sweating", "head_back",
            "arched_back", "clenched_fists", "trembling",
            "sweat_drops", "sweaty_body", "flushed_skin",
            "spread_legs", "gripping_sheets", "messy_hair"],
        5: ["ahegao", "rolling_eyes", "tongue_out", "drooling", "head_back",
            "arched_back", "toes_curling", "full_body_arch", "tears",
            "sweat_drops", "sweaty_body", "sweat_glistening", "skin_glistening",
            "heart_pupils", "cross-eyed", "saliva_drip", "fucked_silly"],
    }

    # intensity別 衣装状態エスカレーション
    CLOTHING_ESCALATION = {
        1: [],  # 通常衣装（変更なし）
        2: ["clothes_pull", "skirt_lift", "loosened_tie"],
        3: ["partially_undressed", "shirt_lift", "bra_visible",
            "one_shoulder_exposed", "disheveled_clothes",
            "unbuttoned_shirt", "skirt_around_waist"],
        4: ["topless", "panties_only", "torn_clothes", "clothes_around_ankles",
            "open_shirt", "naked_shirt", "panties_aside",
            "bra_removed", "stockings_only"],
        5: ["completely_nude", "nude", "naked", "clothes_scattered",
            "torn_panties", "clothes_removed"],
    }

    # intensity別 体液進行タグ
    FLUID_PROGRESSION = {
        1: [],
        2: ["light_blush"],
        3: ["light_blush", "pussy_juice", "wet", "love_juice"],
        4: ["pussy_juice", "wet", "saliva", "saliva_trail",
            "wet_skin", "sweat_stain", "dripping_wet",
            "precum", "mixed_fluids"],
        5: ["cum", "cum_on_body", "cum_drip", "overflow",
            "dripping", "saliva_trail", "wet_skin",
            "cum_in_pussy", "cum_pool", "cum_string",
            "excessive_cum", "body_fluids"],
    }

    _prev_scene_positions = set()  # 前シーンの体位タグ（重複防止用）

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

        # 1.7. ユーザー指定の場所タイプ強制
        if location_type:
            _existing_lower_17 = {t.strip().lower().replace(" ", "_") for t in tags}
            if location_type == "indoors":
                tags = [t for t in tags if t.strip().lower() not in {"outdoors"}]
                if "indoors" not in _existing_lower_17:
                    tags.insert(min(2, len(tags)), "indoors")
            elif location_type == "outdoors":
                tags = [t for t in tags if t.strip().lower() not in {"indoors"}]
                if "outdoors" not in _existing_lower_17:
                    tags.insert(min(2, len(tags)), "outdoors")

        # 2. quality tags先頭確保（QUALITY_TAGS_DISABLED時は完全除去）
        if sd_quality_tags == QUALITY_TAGS_DISABLED:
            # カスタムモードで空欄→既存のquality tagsも除去
            _quality_kw = {"masterpiece", "best_quality", "best quality", "high_quality", "highres", "absurdres"}
            tags = [t for t in tags if not any(kw in t.lower() for kw in _quality_kw)]
        else:
            quality_found = any("masterpiece" in t.lower() or "best_quality" in t.lower() for t in tags)
            if not quality_found:
                effective_quality = sd_quality_tags if sd_quality_tags else QUALITY_POSITIVE_TAGS
                tags.insert(0, effective_quality)

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

        # 4.3. ユーザー指定の時間帯タグ注入
        if time_tags:
            _time_related = {"morning", "sunrise", "morning_light", "daytime", "sunlight",
                             "afternoon", "evening", "sunset", "golden_hour", "night",
                             "moonlight", "dim_lighting", "bright"}
            _existing_lower_43 = {t.strip().lower().replace(" ", "_") for t in tags}
            tags = [t for t in tags if t.strip().lower().replace(" ", "_") not in _time_related]
            _existing_lower_43 -= _time_related
            for tt in time_tags.split(","):
                tt = tt.strip()
                if tt and tt.lower() not in _existing_lower_43:
                    tags.append(tt)
                    _existing_lower_43.add(tt.lower())

        # 4.2. 背景タグ保証（sd_promptに背景系タグが無い場合、locationから補完）
        _bg_kw = {
            "outdoors", "indoors",
            # 学校
            "classroom", "library", "gym", "hallway", "stairwell",
            "locker_room", "infirmary", "rooftop", "club_room",
            "storage_room", "school",
            # 住居
            "bedroom", "bathroom", "kitchen", "living_room",
            "japanese_room", "balcony", "basement", "study",
            "entrance", "closet", "garage",
            # 商業・仕事
            "office", "elevator", "warehouse", "factory",
            "convenience_store", "store",
            # 宿泊
            "hotel_room", "ryokan_room", "inn_room", "cabin",
            # 飲食
            "cafe", "restaurant", "izakaya", "bar", "cafeteria",
            # 交通
            "car_interior", "train_interior", "bus_interior",
            "airplane_interior", "ship_interior", "train_station",
            # 娯楽
            "karaoke_room", "internet_cafe", "arcade", "theater", "studio",
            # 屋外・自然
            "park", "forest", "beach", "mountain", "river", "lake",
            "garden", "alley", "bridge", "riverbank", "field",
            "grassland", "cliff", "cave",
            # 風呂・温泉
            "onsen", "bath", "pool", "open_air_bath", "bathhouse", "sauna",
            # 宗教
            "shrine", "temple", "church", "graveyard",
            # ファンタジー
            "dungeon", "castle", "tower", "prison", "tavern", "throne_room",
            # SF
            "spaceship_interior", "laboratory", "cockpit",
            # 日本建築
            "engawa", "storehouse", "barn",
        }
        _exist_low = {t.strip().lower().replace(" ", "_") for t in tags}
        if not (_exist_low & _bg_kw):
            _location = scene.get("location_detail", scene.get("location", ""))
            if _location:
                _loc_map = {
                    # 学校系
                    "教室": "classroom", "保健室": "infirmary", "体育": "gym",
                    "部室": "club_room", "屋上": "rooftop", "図書": "library",
                    "廊下": "hallway", "階段": "stairwell", "トイレ": "bathroom",
                    "更衣": "locker_room", "プール": "pool", "校庭": "outdoors",
                    "準備室": "storage_room", "職員室": "office",
                    # 住居系
                    "寝室": "bedroom", "リビング": "living_room", "台所": "kitchen",
                    "浴室": "bathroom", "風呂": "bathroom", "玄関": "entrance",
                    "和室": "japanese_room", "子供部屋": "bedroom", "書斎": "study",
                    "ベランダ": "balcony", "押し入れ": "closet", "地下室": "basement",
                    "洗面": "bathroom", "脱衣": "locker_room", "トイレ": "bathroom",
                    "物置": "storage_room", "ガレージ": "garage",
                    # 日本建築系
                    "畳": "japanese_room", "障子": "japanese_room",
                    "縁側": "engawa", "土間": "dirt_floor",
                    "蔵": "storehouse", "納屋": "barn",
                    # 宿泊系
                    "ホテル": "hotel_room", "旅館": "ryokan_room", "ラブホ": "hotel_room",
                    "民宿": "inn_room", "ペンション": "hotel_room", "コテージ": "cabin",
                    # 飲食系
                    "カフェ": "cafe", "居酒屋": "izakaya", "レストラン": "restaurant",
                    "バー": "bar", "食堂": "cafeteria", "ファミレス": "restaurant",
                    "キッチン": "kitchen",
                    # 商業施設系
                    "オフィス": "office", "会議室": "office", "エレベータ": "elevator",
                    "ビル": "office", "倉庫": "warehouse", "工場": "factory",
                    "コンビニ": "convenience_store", "スーパー": "store",
                    "デパート": "store", "ショッピング": "store",
                    # 交通系
                    "車": "car_interior", "電車": "train_interior", "バス": "bus_interior",
                    "タクシー": "car_interior", "飛行機": "airplane_interior",
                    "船": "ship_interior", "駅": "train_station",
                    # 娯楽系
                    "カラオケ": "karaoke_room", "ネットカフェ": "internet_cafe",
                    "ゲームセンター": "arcade", "映画館": "theater",
                    "ボウリング": "bowling_alley", "スタジオ": "studio",
                    # 屋外・自然系
                    "公園": "park", "森": "forest", "海": "beach",
                    "山": "mountain", "川": "river", "湖": "lake",
                    "庭": "garden", "路地": "alley", "橋": "bridge",
                    "河原": "riverbank", "野原": "field", "草原": "grassland",
                    "崖": "cliff", "洞窟": "cave", "砂浜": "beach",
                    # 宗教・文化系
                    "神社": "shrine", "寺": "temple", "教会": "church",
                    "墓地": "graveyard", "鳥居": "torii",
                    # 温泉・風呂系
                    "温泉": "onsen", "露天風呂": "open_air_bath",
                    "銭湯": "bathhouse", "サウナ": "sauna",
                    # ファンタジー系
                    "ダンジョン": "dungeon", "城": "castle", "塔": "tower",
                    "牢獄": "prison", "酒場": "tavern", "宿屋": "inn_room",
                    "玉座": "throne_room",
                    # SF系
                    "宇宙船": "spaceship_interior", "研究所": "laboratory",
                    "実験室": "laboratory", "コックピット": "cockpit",
                }
                _added = False
                for _jp, _en in _loc_map.items():
                    if _jp in _location:
                        tags.append(_en)
                        _added = True
                        break
                if not _added:
                    tags.append("indoors")

        # 4.5. intensity≥3のシーンに男性タグ注入
        intensity = scene.get("intensity", 0)
        if intensity >= 3:
            existing_lower = {t.strip().lower().replace(" ", "_") for t in tags}
            # faceless_male は常に付与（どんな男性タイプでも顔なし）
            for male_tag in ["1boy", "faceless_male"]:
                if male_tag not in existing_lower:
                    tags.append(male_tag)
                    existing_lower.add(male_tag)
            if male_tags:
                # ユーザー指定の男性体型タグを高重要度で注入
                for mt in male_tags.split(","):
                    mt = mt.strip()
                    if mt and mt.lower().replace(" ", "_") not in existing_lower:
                        if mt.lower() in ("1boy", "faceless_male"):
                            continue  # 既に付与済み
                        weighted_mt = f"({mt}:1.3)"
                        tags.append(weighted_mt)
                        existing_lower.add(mt.lower().replace(" ", "_"))

        # 4.55. 男性体型タグ（ユーザー指定がある場合はスキップ）
        if not male_tags and intensity >= 3 and "1boy" in existing_lower:
            _male_body_defaults = ["muscular_male", "veiny_arms"]
            for mt in _male_body_defaults:
                if mt not in existing_lower:
                    tags.append(mt)
                    existing_lower.add(mt)

        # 4.6. intensity別 表情・身体反応タグ自動注入
        if intensity >= 3:
            inject_tags = _INTENSITY_EXPRESSION_MAP.get(min(intensity, 5), [])
            existing_lower = {t.strip().lower().replace(" ", "_") for t in tags}
            for et in inject_tags:
                if et not in existing_lower:
                    tags.append(et)
                    existing_lower.add(et)

        # 4.7. intensity別 衣装状態タグ自動注入
        _clothing_tags = CLOTHING_ESCALATION.get(min(intensity, 5), [])
        if _clothing_tags:
            existing_lower = {t.strip().lower().replace(" ", "_") for t in tags}
            # intensity 5で既にnudeタグがあれば衣装タグ不要
            _has_nude = existing_lower & {"nude", "naked", "completely_nude"}
            if not (intensity >= 5 and _has_nude):
                # 1タグだけ注入（過剰にならないよう）
                for ct in _clothing_tags:
                    if ct not in existing_lower:
                        tags.append(ct)
                        existing_lower.add(ct)
                        break

        # 4.8. intensity別 体液進行タグ自動注入
        _fluid_tags = FLUID_PROGRESSION.get(min(intensity, 5), [])
        if _fluid_tags:
            existing_lower = {t.strip().lower().replace(" ", "_") for t in tags}
            _injected_fluid = 0
            for ft in _fluid_tags:
                if ft not in existing_lower and _injected_fluid < 2:
                    tags.append(ft)
                    existing_lower.add(ft)
                    _injected_fluid += 1

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

        # 5.5. 矛盾する体位/行為タグの相互排他チェック
        # 同時に成立しない行為の組み合わせを検出し、descriptionに近い方を残す
        _CONTRADICTORY_PAIRS = [
            # (グループA, グループB): A+Bが同時に存在したらBを除去
            ({"blowjob", "fellatio", "deepthroat", "oral"}, {"sitting_on_lap", "cowgirl_position", "reverse_cowgirl", "missionary", "vaginal"}),
            ({"paizuri"}, {"doggy_style", "from_behind", "all_fours", "missionary", "standing_sex"}),
            ({"handjob"}, {"vaginal", "penetration", "sex"}),
            # v7.0追加
            ({"anal", "anal_sex"}, {"vaginal", "pussy"}),
            ({"sleeping", "asleep"}, {"standing", "standing_sex", "walking"}),
            ({"bondage", "tied_up", "restrained"}, {"hugging", "holding_hands", "hand_on_hip"}),
            ({"clothed_sex"}, {"completely_nude", "nude", "naked"}),
            ({"underwater"}, {"indoors", "bedroom", "classroom"}),
        ]
        _tags_lower_set = {t.strip().lower().replace(" ", "_") for t in tags}
        for group_a, group_b in _CONTRADICTORY_PAIRS:
            has_a = _tags_lower_set & group_a
            has_b = _tags_lower_set & group_b
            if has_a and has_b:
                # グループAの行為が明示的にある場合、矛盾するグループBを除去
                desc_lower = scene.get("description", "").lower()
                a_in_desc = any(k in desc_lower for k in ["フェラ", "口", "咥", "パイズリ", "手コキ", "blowjob", "oral", "paizuri"])
                if a_in_desc or len(has_a) >= len(has_b):
                    tags = [t for t in tags if t.strip().lower().replace(" ", "_") not in has_b]
                else:
                    tags = [t for t in tags if t.strip().lower().replace(" ", "_") not in has_a]

        # 5.6. aftermathシーンのSDタグ整合性チェック
        _desc_for_ctx = (scene.get("description", "") + " " + scene.get("title", "")
                         + " " + scene.get("mood", "")).lower()
        _aftermath_ctx_kw = ["事後", "余韻", "虚脱", "終えた", "身繕い", "動けない", "虚ろ",
                             "後片付け", "放心", "脱力", "ぐったり", "呆然", "立てない",
                             "aftermath", "afterglow"]
        if any(k in _desc_for_ctx for k in _aftermath_ctx_kw):
            # 事後シーンからsex/penetration等のアクティブな行為タグを除去
            _sex_tags_to_remove = {"sex", "vaginal", "penetration", "thrusting",
                                   "piston", "hip_thrust", "grabbing_hips"}
            tags = [t for t in tags if t.strip().lower().replace(" ", "_") not in _sex_tags_to_remove]
            # aftermath固有タグを追加
            _existing = {t.strip().lower().replace(" ", "_") for t in tags}
            for at_tag in ["exhausted", "dazed", "afterglow"]:
                if at_tag not in _existing:
                    tags.append(at_tag)
                    _existing.add(at_tag)

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

        # 7. 体位タグ自動調整（前シーンと同一体位を代替に置換）
        # intensityは step 4.5 で取得済み
        _cur_positions = set()
        adjusted = []
        for tag in weighted:
            # ウェイト付きタグからタグ名を抽出
            _inner = _re.sub(r'[()]', '', tag).split(":")[0].strip().lower().replace(" ", "_")
            if _inner in POSITION_TAGS:
                _cur_positions.add(_inner)
                if _inner in _prev_scene_positions:
                    # 前シーンと同じ体位 → 代替に置換
                    fallbacks = POSITION_FALLBACKS.get(_inner, [])
                    # intensity連動: 高intensityでは激しい体位を優先
                    preferred = _POSITION_INTENSITY_PREFERENCE.get(min(intensity, 5), set())
                    replacement = None
                    # 優先度の高い体位から選択
                    for fb in fallbacks:
                        if fb in preferred and fb not in _prev_scene_positions:
                            replacement = fb
                            break
                    # 優先に該当なければフォールバックの先頭から
                    if not replacement:
                        for fb in fallbacks:
                            if fb not in _prev_scene_positions:
                                replacement = fb
                                break
                    if replacement:
                        _cur_positions.discard(_inner)
                        _cur_positions.add(replacement)
                        adjusted.append(replacement)
                        continue
            adjusted.append(tag)
        weighted = adjusted
        _prev_scene_positions = _cur_positions

        main_prompt = deduplicate_sd_tags(", ".join(weighted))
        # prefix/suffix注入（LoRAタグ等はdeduplicateに通さない）
        parts = []
        if sd_prefix_tags:
            parts.append(sd_prefix_tags)
        parts.append(main_prompt)
        if sd_suffix_tags:
            parts.append(sd_suffix_tags)
        scene["sd_prompt"] = ", ".join(parts)

    # 8. 体位分布リバランス（spread_legsが40%超過→一部を代替体位に自動置換）
    import re as _re8
    total = len(results)
    if total >= 8:  # 8シーン以上のスクリプトのみ
        pos_counter = {}
        pos_scene_map = {}  # tag → [scene_indices]
        for idx, sc in enumerate(results):
            prompt = sc.get("sd_prompt", "")
            for t in prompt.split(","):
                norm = t.strip().lower().replace(" ", "_")
                norm = _re8.sub(r'[()]', '', norm).split(":")[0].strip()
                if norm in POSITION_TAGS:
                    pos_counter[norm] = pos_counter.get(norm, 0) + 1
                    pos_scene_map.setdefault(norm, []).append(idx)
        # 40%超過の体位を検出
        _SPREAD_ALTERNATIVES = [
            "legs_apart", "legs_up", "open_legs", "straddling",
            "cowgirl_position", "reverse_cowgirl", "missionary", "mating_press"
        ]
        for ptag, cnt in pos_counter.items():
            if cnt / total >= 0.40:
                target_count = int(total * 0.30)  # 30%以下に削減
                excess = cnt - target_count
                if excess <= 0:
                    continue
                scenes_with = pos_scene_map.get(ptag, [])
                # 奇数indexのシーンから優先的に置換（偶数は維持）
                replace_targets = [i for i in scenes_with if i % 2 == 1][:excess]
                if len(replace_targets) < excess:
                    replace_targets.extend([i for i in scenes_with if i % 2 == 0 and i not in replace_targets][:excess - len(replace_targets)])
                alt_idx = 0
                fallbacks_for_tag = POSITION_FALLBACKS.get(ptag, _SPREAD_ALTERNATIVES)
                for sidx in replace_targets[:excess]:
                    alt = fallbacks_for_tag[alt_idx % len(fallbacks_for_tag)]
                    alt_idx += 1
                    sc = results[sidx]
                    old_prompt = sc.get("sd_prompt", "")
                    # タグ置換
                    new_tags = []
                    replaced = False
                    for t in old_prompt.split(","):
                        norm = t.strip().lower().replace(" ", "_")
                        norm_clean = _re8.sub(r'[()]', '', norm).split(":")[0].strip()
                        if norm_clean == ptag and not replaced:
                            new_tags.append(alt)
                            replaced = True
                        else:
                            new_tags.append(t.strip())
                    sc["sd_prompt"] = deduplicate_sd_tags(", ".join(new_tags))
                log_message(f"体位リバランス: {ptag} {cnt}/{total}({cnt*100//total}%)→{cnt-len(replace_targets[:excess])}/{total}に削減")

    # 最終パス: 体位/アングル連続重複の再チェック（Step 8で再導入された可能性対応）
    import re as _re_final
    _prev_pos_f = set()
    for scene in results:
        sd = scene.get("sd_prompt", "")
        if not sd:
            _prev_pos_f = set()
            continue
        tags = [t.strip() for t in sd.split(",") if t.strip()]
        _cur_pos_f = set()
        new_tags = []
        changed = False
        for tag in tags:
            _inner = _re_final.sub(r'[()]', '', tag).split(":")[0].strip().lower().replace(" ", "_")
            if _inner in POSITION_TAGS:
                _cur_pos_f.add(_inner)
                if _inner in _prev_pos_f:
                    fallbacks = POSITION_FALLBACKS.get(_inner, [])
                    replacement = None
                    for fb in fallbacks:
                        if fb not in _prev_pos_f:
                            replacement = fb
                            break
                    if replacement:
                        _cur_pos_f.discard(_inner)
                        _cur_pos_f.add(replacement)
                        new_tags.append(replacement)
                        changed = True
                        continue
            new_tags.append(tag)
        if changed:
            scene["sd_prompt"] = ", ".join(new_tags)
        _prev_pos_f = _cur_pos_f

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


def _detect_personality_type(char_profiles: list) -> str:
    """キャラプロファイルから性格タイプを判定。
    Returns: personality key or ""
    対応: tsundere/submissive/sadistic/ojou/gal/seiso/genki/kuudere/inkya
    """
    if not char_profiles:
        return ""
    for cp in char_profiles:
        personality = cp.get("personality_core", {})
        desc = personality.get("brief_description", "")
        traits = personality.get("main_traits", [])
        archetype = cp.get("archetype", "")
        all_text = f"{desc} {' '.join(traits)} {archetype}".lower()
        # ツンデレ
        if any(k in all_text for k in ["ツンデレ", "ツン", "tsundere"]):
            return "tsundere"
        # ドM・従順・受け身
        if any(k in all_text for k in ["ドm", "どm", "masochist", "従順", "submissive",
                                        "奴隷", "ペット", "服従", "受け身"]):
            return "submissive"
        # Sっ気・サディスト・サキュバス・強気
        if any(k in all_text for k in ["ドs", "どs", "sadist", "サキュバス", "succubus",
                                        "小悪魔", "女王", "支配", "強気"]):
            return "sadistic"
        # お嬢様・高貴
        if any(k in all_text for k in ["お嬢様", "令嬢", "高貴", "ojou", "noble",
                                        "上品", "princess", "姫"]):
            return "ojou"
        # ギャル
        if any(k in all_text for k in ["ギャル", "gal", "黒ギャル", "パリピ",
                                        "チャラい"]):
            return "gal"
        # 清楚・純粋
        if any(k in all_text for k in ["清楚", "純粋", "清純", "天然", "innocent",
                                        "文学少女"]):
            return "seiso"
        # 元気・体育会系
        if any(k in all_text for k in ["元気", "活発", "体育会", "ボーイッシュ",
                                        "energetic", "スポーツ"]):
            return "genki"
        # クーデレ・無表情
        if any(k in all_text for k in ["クーデレ", "kuudere", "無表情", "無口",
                                        "クール", "cool"]):
            return "kuudere"
        # 陰キャ・オタク
        if any(k in all_text for k in ["陰キャ", "オタク", "otaku", "引っ込み",
                                        "内向", "根暗", "introvert"]):
            return "inkya"
    return ""


# 性格タイプ → primaryセリフスキルマッピング
_PERSONALITY_SKILL_MAP = {
    "tsundere":  "ero_serihu_tundere",     # ツンデレ → ツンデレ系
    "submissive": "ero_serihu_jyunai",     # 従順/受け身 → 甘え系（恥じらい・受容）
    "sadistic":  "ero_serihu_tundere",     # Sっ気/強気 → ツンデレ系（挑発・煽り）
    "ojou":      "ero_serihu_nomal",       # お嬢様 → ノーマル（ギャップ感重視）
    "gal":       "ero_serihu_ohogoe",      # ギャル/強気 → 激しい系
    "seiso":     "ero_serihu_nomal",       # 清楚 → ノーマル（ギャップ感重視）
    "genki":     "ero_serihu_nomal",       # 元気系 → ノーマル
    "kuudere":   "ero_serihu_nomal",       # クーデレ → ノーマル（感情抑制）
    "inkya":     "ero_serihu_jyunai",      # 陰キャ/オタク → 恥じらい系
}

# 性格タイプ → secondaryスキル + 混合比率（secondary_skill, secondary_ratio）
_PERSONALITY_SECONDARY_MAP = {
    "tsundere":  ("ero_serihu_jyunai", 0.3),   # 30%甘え混合（デレ部分）
    "submissive": ("ero_serihu_ohogoe", 0.3),   # 30%堕ち表現混合
    "sadistic":  ("ero_serihu_ohogoe", 0.4),    # 40%激しい表現混合
    "ojou":      ("ero_serihu_jyunai", 0.4),    # 40%上品な甘え混合
    "gal":       ("ero_serihu_nomal", 0.3),     # 30%通常混合
    "seiso":     ("ero_serihu_jyunai", 0.4),    # 40%恥じらい混合
    "genki":     ("ero_serihu_ohogoe", 0.2),    # 20%激しさ混合
    "kuudere":   ("ero_serihu_jyunai", 0.3),    # 30%感情漏れ混合
    "inkya":     ("ero_serihu_nomal", 0.2),     # 20%通常混合
}

# 性格タイプ → ero_dialogue_pool のプール混合カテゴリ指定
_PERSONALITY_POOL_MIX = {
    "tsundere":  {"primary": ["denial", "embarrassed"], "secondary": ["acceptance"]},
    "submissive": {"primary": ["submissive", "plea"], "secondary": ["acceptance", "ecstasy"]},
    "sadistic":  {"primary": ["provoke"], "secondary": ["ecstasy", "acceptance"]},
    "ojou":      {"primary": ["embarrassed", "denial"], "secondary": ["plea"]},
    "gal":       {"primary": ["acceptance", "provoke"], "secondary": ["ecstasy"]},
    "seiso":     {"primary": ["embarrassed", "denial"], "secondary": ["acceptance", "plea"]},
    "genki":     {"primary": ["acceptance", "provoke"], "secondary": ["ecstasy"]},
    "kuudere":   {"primary": ["denial"], "secondary": ["embarrassed", "acceptance"]},
    "inkya":     {"primary": ["embarrassed", "plea"], "secondary": ["denial", "acceptance"]},
}

# テーマキーワード → スキルマッピング
_THEME_SKILL_MAP = {
    "love":        "ero_serihu_jyunai",
    "vanilla":     "ero_serihu_jyunai",
    "netorare":    "ero_serihu_ohogoe",
    "humiliation": "ero_serihu_ohogoe",
    "forced":      "ero_serihu_ohogoe",
    "corruption":  "ero_serihu_ohogoe",
    "gangbang":    "ero_serihu_ohogoe",
    "chikan":      "ero_serihu_ohogoe",
    "isekai":        "ero_serihu_nomal",
    "onsen":         "ero_serihu_jyunai",
    "sleep":         "ero_serihu_ohogoe",
    "medical":       "ero_serihu_nomal",
    "swimsuit":      "ero_serihu_jyunai",
    "sports":        "ero_serihu_nomal",
    "idol":          "ero_serihu_nomal",
    "neighbor":      "ero_serihu_jyunai",
    "prostitution":  "ero_serihu_nomal",
    "voyeur":        "ero_serihu_ohogoe",
    "tentacle":      "ero_serihu_ohogoe",
    "reverse_rape":  "ero_serihu_tundere",
    "cosplay":       "ero_serihu_nomal",
}


def _select_serihu_skill(theme: str = "", char_profiles: list = None) -> dict:
    """キャラ性格×テーマの2軸判定でセリフスキルを自動選択。

    Returns:
        dict: {"primary": str, "secondary": str|None, "ratio": float,
               "personality": str}
        - primary: メインスキル名
        - secondary: サブスキル名（混合用、なければNone）
        - ratio: primaryの比率 (0.0-1.0)。secondary = 1 - ratio
        - personality: 検出された性格タイプ（""の場合テーマのみ判定）

    複合テーマ: "netorare+love" 等、+/＋区切りで複数テーマを認識し混合。
    """
    personality = _detect_personality_type(char_profiles)

    # テーマ解析（複合テーマ対応: +/＋区切り）
    theme_lower = theme.lower() if theme else ""
    theme_parts = [t.strip() for t in theme_lower.replace("\uff0b", "+").split("+")
                   if t.strip()]

    # === 性格優先パス ===
    if personality and personality in _PERSONALITY_SKILL_MAP:
        primary = _PERSONALITY_SKILL_MAP[personality]
        secondary, sec_ratio = _PERSONALITY_SECONDARY_MAP.get(personality, (None, 0.0))
        # テーマスキルがprimaryと異なればsecondaryに採用（テーマ混合）
        if theme_parts:
            for part in theme_parts:
                theme_skill = _THEME_SKILL_MAP.get(part)
                if theme_skill and theme_skill != primary:
                    secondary = theme_skill
                    sec_ratio = max(sec_ratio, 0.3)
                    break
        return {
            "primary": primary,
            "secondary": secondary if sec_ratio > 0 else None,
            "ratio": 1.0 - sec_ratio,
            "personality": personality,
        }

    # === テーマのみパス ===
    if not theme_parts:
        return {"primary": "ero_serihu_nomal", "secondary": None,
                "ratio": 1.0, "personality": ""}

    # 複合テーマ: 先にマッチしたものをprimary、2番目をsecondary
    matched_skills = []
    for part in theme_parts:
        skill = _THEME_SKILL_MAP.get(part)
        if skill and skill not in matched_skills:
            matched_skills.append(skill)

    if len(matched_skills) >= 2:
        return {
            "primary": matched_skills[0],
            "secondary": matched_skills[1],
            "ratio": 0.7,
            "personality": "",
        }
    elif len(matched_skills) == 1:
        return {"primary": matched_skills[0], "secondary": None,
                "ratio": 1.0, "personality": ""}

    return {"primary": "ero_serihu_nomal", "secondary": None,
            "ratio": 1.0, "personality": ""}


# === データクラス ===
@dataclass
class CostTracker:
    haiku_input: int = 0
    haiku_output: int = 0
    haiku_fast_input: int = 0
    haiku_fast_output: int = 0
    sonnet_input: int = 0
    sonnet_output: int = 0
    cache_creation: int = 0
    cache_read: int = 0
    # モデル別キャッシュ追跡（正確なコスト計算用）
    haiku_cache_creation: int = 0
    haiku_cache_read: int = 0
    haiku_fast_cache_creation: int = 0
    haiku_fast_cache_read: int = 0
    sonnet_cache_creation: int = 0
    sonnet_cache_read: int = 0
    api_calls: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def add(self, model: str, input_tokens: int, output_tokens: int,
            cache_creation_tokens: int = 0, cache_read_tokens: int = 0):
        with self._lock:
            self.api_calls += 1
            self.cache_creation += cache_creation_tokens
            self.cache_read += cache_read_tokens
            if "sonnet" in model:
                self.sonnet_input += input_tokens
                self.sonnet_output += output_tokens
                self.sonnet_cache_creation += cache_creation_tokens
                self.sonnet_cache_read += cache_read_tokens
            elif model == MODELS.get("haiku_fast", "claude-3-haiku-20240307"):
                self.haiku_fast_input += input_tokens
                self.haiku_fast_output += output_tokens
                self.haiku_fast_cache_creation += cache_creation_tokens
                self.haiku_fast_cache_read += cache_read_tokens
            else:
                self.haiku_input += input_tokens
                self.haiku_output += output_tokens
                self.haiku_cache_creation += cache_creation_tokens
                self.haiku_cache_read += cache_read_tokens

    def total_cost_usd(self) -> float:
        """キャッシュ料金を正確に反映したコスト計算。
        Anthropic API: cache_read=入力単価x0.1, cache_creation=入力単価x1.25"""
        hf_cost = COSTS.get(MODELS["haiku_fast"], {"input": 0.25, "output": 1.25})
        h_cost = COSTS.get(MODELS["haiku"], {"input": 1.00, "output": 5.00})
        s_cost = COSTS.get(MODELS["sonnet"], {"input": 3.00, "output": 15.00})
        return (
            # Haiku fast（非キャッシュ入力 + 出力 + キャッシュ作成 + キャッシュ読取）
            (self.haiku_fast_input / 1_000_000) * hf_cost["input"] +
            (self.haiku_fast_output / 1_000_000) * hf_cost["output"] +
            (self.haiku_fast_cache_creation / 1_000_000) * hf_cost["input"] * 1.25 +
            (self.haiku_fast_cache_read / 1_000_000) * hf_cost["input"] * 0.10 +
            # Haiku 4.5
            (self.haiku_input / 1_000_000) * h_cost["input"] +
            (self.haiku_output / 1_000_000) * h_cost["output"] +
            (self.haiku_cache_creation / 1_000_000) * h_cost["input"] * 1.25 +
            (self.haiku_cache_read / 1_000_000) * h_cost["input"] * 0.10 +
            # Sonnet
            (self.sonnet_input / 1_000_000) * s_cost["input"] +
            (self.sonnet_output / 1_000_000) * s_cost["output"] +
            (self.sonnet_cache_creation / 1_000_000) * s_cost["input"] * 1.25 +
            (self.sonnet_cache_read / 1_000_000) * s_cost["input"] * 0.10
        )

    def _cache_savings_usd(self) -> float:
        """キャッシュによる節約額（キャッシュなしの場合との差分）"""
        h_cost = COSTS.get(MODELS["haiku"], {"input": 1.00, "output": 5.00})
        s_cost = COSTS.get(MODELS["sonnet"], {"input": 3.00, "output": 15.00})
        hf_cost = COSTS.get(MODELS["haiku_fast"], {"input": 0.25, "output": 1.25})
        # キャッシュ読み取りがフル入力だった場合のコスト差分（90%節約）
        return (
            (self.haiku_cache_read / 1_000_000) * h_cost["input"] * 0.90 +
            (self.sonnet_cache_read / 1_000_000) * s_cost["input"] * 0.90 +
            (self.haiku_fast_cache_read / 1_000_000) * hf_cost["input"] * 0.90
        )

    def summary(self) -> str:
        lines = []
        if self.haiku_fast_input or self.haiku_fast_output:
            lines.append(f"Haiku(fast): {self.haiku_fast_input:,} in / {self.haiku_fast_output:,} out")
        if self.haiku_input or self.haiku_output:
            lines.append(f"Haiku(4.5): {self.haiku_input:,} in / {self.haiku_output:,} out")
        if self.sonnet_input or self.sonnet_output:
            lines.append(f"Sonnet: {self.sonnet_input:,} in / {self.sonnet_output:,} out")
        if self.cache_read or self.cache_creation:
            lines.append(f"Cache: {self.cache_read:,} read / {self.cache_creation:,} create")
            savings = self._cache_savings_usd()
            if savings > 0.001:
                lines.append(f"Cache節約: -${savings:.4f}")
        lines.append(f"API呼出: {self.api_calls}回")
        lines.append(f"推定コスト: ${self.total_cost_usd():.4f}")
        return "\n".join(lines)


def estimate_cost(num_scenes: int, use_sonnet_polish: bool = True) -> dict:
    """生成前にコストを予測（Prompt Caching反映版）
    haiku=圧縮/あらすじ/アウトライン+低intensityシーン, sonnet=i4以上シーン"""
    h_cost = COSTS.get(MODELS["haiku"], {"input": 1.00, "output": 5.00})
    s_cost = COSTS.get(MODELS["sonnet"], {"input": 3.00, "output": 15.00})

    # Phase 1: コンテキスト圧縮 + あらすじ (haiku 4.5)
    fast_input = 500 + 600
    fast_output = 150 + 800

    # Phase 3: アウトライン (haiku: 全ケース)
    haiku_input = fast_input  # Phase 1-2もhaiku
    haiku_output = fast_output
    if num_scenes <= 12:
        haiku_input += 2000
        haiku_output += num_scenes * 300
    else:
        chunks = (num_scenes + 9) // 10
        haiku_input += chunks * 3000
        haiku_output += chunks * 2000

    # シーン生成（intensity分布推定: 40% i1-3→haiku, 60% i4-5→sonnet）
    haiku_scenes = int(num_scenes * 0.40)  # intensity 1-3 → haiku
    sonnet_scenes = num_scenes - haiku_scenes  # intensity 4-5 → sonnet

    # Prompt Caching効果: system prompt ~16000tokはキャッシュされる
    # 初回のみcache_creation(1.25x)、以降はcache_read(0.1x)
    cached_system_tokens = 16000  # 圧縮後のsystemプロンプト推定サイズ
    # シーン固有の非キャッシュ入力（user prompt: context + story_so_far + scene指示）
    avg_user_tokens = 3000  # 平均user prompt（story_so_far含む）

    # Haiku シーン: 1回cache_create + (N-1)回cache_read
    haiku_cache_create_cost = (cached_system_tokens / 1_000_000) * h_cost["input"] * 1.25  # 初回
    haiku_cache_read_cost = (cached_system_tokens / 1_000_000) * h_cost["input"] * 0.10 * max(0, haiku_scenes - 1)
    haiku_uncached_input = haiku_scenes * avg_user_tokens
    haiku_input += haiku_uncached_input
    haiku_output += haiku_scenes * 650

    # Sonnet シーン: 1回cache_create + (N-1)回cache_read
    sonnet_cache_create_cost = (cached_system_tokens / 1_000_000) * s_cost["input"] * 1.25 if sonnet_scenes > 0 else 0
    sonnet_cache_read_cost = (cached_system_tokens / 1_000_000) * s_cost["input"] * 0.10 * max(0, sonnet_scenes - 1)
    sonnet_input = sonnet_scenes * avg_user_tokens
    sonnet_output = sonnet_scenes * 700

    estimated_usd = (
        (haiku_input / 1_000_000) * h_cost["input"] +
        (haiku_output / 1_000_000) * h_cost["output"] +
        haiku_cache_create_cost + haiku_cache_read_cost +
        (sonnet_input / 1_000_000) * s_cost["input"] +
        (sonnet_output / 1_000_000) * s_cost["output"] +
        sonnet_cache_create_cost + sonnet_cache_read_cost
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


_skill_cache: dict = {}  # スキルファイル読み込みキャッシュ（同一パイプライン内の重複I/O削減）

def load_skill(skill_name: str) -> str:
    if skill_name in _skill_cache:
        return _skill_cache[skill_name]
    skill_file = SKILLS_DIR / f"{skill_name}.skill.md"
    if skill_file.exists():
        content = skill_file.read_text(encoding="utf-8")
        _skill_cache[skill_name] = content
        return content
    _skill_cache[skill_name] = ""
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


def _decode_exif_user_comment(value) -> str:
    """EXIF UserComment (0x9286) を文字列にデコード。

    SD WebUI(piexif)は b"UNICODE\\x00" + utf-16 で書き込む。
    バイトオーダーはEXIFヘッダ(II=LE/MM=BE)依存のためbodyの先頭2バイトで自動判定。
    Pillowバージョンにより bytes or str(latin-1誤デコード) で返る。
    """
    if not value:
        return ""
    # str型: Pillowが自動デコード済み or latin-1誤デコードの可能性
    if isinstance(value, str):
        # エンコーディングプレフィックスやNULLバイトが含まれている場合は
        # latin-1で誤デコードされたバイト列 → bytesに戻して再デコード
        if "\x00" in value or value.startswith(("UNICODE", "ASCII", "JIS")):
            try:
                value = value.encode("latin-1")
            except (UnicodeEncodeError, UnicodeDecodeError):
                # latin-1に戻せない場合はNULLバイトだけ除去して返す
                return value.replace("\x00", "").strip()
        else:
            return value.strip()
    # bytes型: エンコーディング識別子を解析して適切にデコード
    if isinstance(value, bytes):
        header = value[:8] if len(value) >= 8 else value
        body = value[8:] if len(value) > 8 else value
        # piexif: b"UNICODE\x00" + utf-16 encoded body
        # バイトオーダーは EXIF ヘッダ(II/MM)依存: bodyの先頭2バイトで自動判定
        if header.startswith(b"UNICODE"):
            # 先頭2バイトでバイトオーダーを推定
            # body[0]==0x00 && body[1] が印刷可能ASCII → big-endian
            # body[1]==0x00 && body[0] が印刷可能ASCII → little-endian
            if len(body) >= 2 and body[0] == 0x00 and 0x20 <= body[1] <= 0x7e:
                utf16_order = ("utf-16-be", "utf-16-le")
            else:
                utf16_order = ("utf-16-le", "utf-16-be")
            for enc in (*utf16_order, "utf-8"):
                try:
                    decoded = body.decode(enc).strip("\x00").strip()
                    if decoded:
                        return decoded
                except (UnicodeDecodeError, ValueError):
                    continue
        # ASCII prefix or undefined (\x00 * 8)
        if header.startswith(b"ASCII") or header == b"\x00" * 8:
            try:
                return body.decode("ascii", errors="ignore").strip("\x00").strip()
            except Exception:
                pass
        # JIS prefix
        if header.startswith(b"JIS"):
            try:
                return body.decode("shift_jis", errors="ignore").strip("\x00").strip()
            except Exception:
                pass
        # フォールバック: プレフィックスなしで全体をutf-8試行
        try:
            return value.decode("utf-8", errors="ignore").strip("\x00").strip()
        except Exception:
            return ""
    return str(value).strip()


def _try_decode_bytes(data: bytes) -> str:
    """バイト列をSD生成パラメータ文字列としてデコード（複数エンコーディング試行）。"""
    if not data:
        return ""
    # エンコーディングプレフィックス付きの場合は _decode_exif_user_comment に委譲
    if len(data) >= 8:
        hdr = data[:8]
        if hdr.startswith((b"UNICODE", b"ASCII", b"JIS")) or hdr == b"\x00" * 8:
            return _decode_exif_user_comment(data)
    # UTF-8 → UTF-16-LE → shift_jis → latin-1 の順で試行
    for enc in ("utf-8", "utf-16-le", "utf-16-be", "shift_jis", "latin-1"):
        try:
            decoded = data.decode(enc).strip("\x00").strip()
            # SD prompt らしいかチェック（英数字タグが含まれるか）
            if decoded and any(c.isalpha() for c in decoded[:50]):
                # UTF-16誤検出防止: NULLバイトだらけなら不採用
                if "\x00" not in decoded:
                    return decoded
        except (UnicodeDecodeError, ValueError):
            continue
    # 最終フォールバック
    return data.decode("utf-8", errors="replace").replace("\x00", "").strip()


def _extract_sd_params_from_bytes(file_bytes: bytes) -> str:
    """ファイルのrawバイトからSD WebUIパラメータ文字列を直接探索（最終フォールバック）。"""
    import re as _re
    # SD WebUI形式: "Steps: NN, Sampler: ..., CFG scale: ..."
    # このパターンを末尾側から探してパラメータ文字列を逆引き
    markers = [b"Steps: ", b"steps: "]
    for marker in markers:
        idx = file_bytes.rfind(marker)
        if idx < 0:
            continue
        # marker前方1024バイト〜marker後方512バイトを切り出し
        start = max(0, idx - 4096)
        end = min(len(file_bytes), idx + 1024)
        chunk = file_bytes[start:end]
        # テキスト部分だけ抽出（NULLバイト除去して複数エンコーディング試行）
        for enc in ("utf-8", "latin-1"):
            try:
                text = chunk.decode(enc, errors="ignore")
                text = text.replace("\x00", "")
                # "Steps: " を含む行を探し、その前のテキストも含めて返す
                m = _re.search(r'([\x20-\x7e,\(\)\n:.<>_\-\w]{10,}Steps:\s*\d+[^\x00]*)', text)
                if m:
                    candidate = m.group(1).strip()
                    # プロンプトの開始位置を推定（最初の改行ブロックの前か、印刷可能文字の始まり）
                    # 前方にゴミバイナリが混ざっている可能性があるので、有効な先頭を探す
                    for ci, ch in enumerate(candidate):
                        if ch.isalpha() or ch == '(':
                            return candidate[ci:].strip()
                    return candidate
            except Exception:
                continue
    return ""


def parse_png_info(file_path: str) -> dict:
    """画像ファイルからSD生成パラメータを解析（PNG/JPEG/WebP対応）。

    Returns:
        {"positive": str, "negative": str, "parameters": str, "raw": str}
        or {"error": str}
    """
    if not PIL_AVAILABLE:
        return {"error": "Pillowがインストールされていません。\npip install Pillow で追加してください。"}
    try:
        img = Image.open(file_path)
        raw = ""
        source = ""

        # 1. PNG: img.info にtEXt/iTXtチャンクが格納される
        if img.format == "PNG":
            raw = img.info.get("parameters", "")
            if raw:
                source = "PNG tEXt[parameters]"
            else:
                for key in ("prompt", "Comment", "Description"):
                    if key in img.info:
                        raw = img.info[key]
                        source = f"PNG tEXt[{key}]"
                        break

        # 2. EXIF sub-IFD → UserComment (SD WebUI A1111/Forge標準)
        if not raw:
            try:
                exif_data = img.getexif()
                if exif_data:
                    try:
                        exif_ifd = exif_data.get_ifd(0x8769)
                        if exif_ifd:
                            uc = exif_ifd.get(0x9286, "")
                            if uc:
                                raw = _decode_exif_user_comment(uc)
                                if raw:
                                    source = "EXIF sub-IFD UserComment"
                    except Exception:
                        pass
                    # 2b. root IFD → UserComment (一部ツール)
                    if not raw:
                        uc_root = exif_data.get(0x9286, "")
                        if uc_root:
                            raw = _decode_exif_user_comment(uc_root)
                            if raw:
                                source = "EXIF root UserComment"
                    # 2c. root IFD → ImageDescription
                    if not raw:
                        desc = exif_data.get(0x010E, "")
                        if desc:
                            raw = _decode_exif_user_comment(desc) if isinstance(desc, bytes) else str(desc).strip()
                            if raw:
                                source = "EXIF ImageDescription"
            except Exception:
                pass

        # 3. raw EXIF bytes から直接パース（Pillow解析が失敗した場合のフォールバック）
        if not raw:
            exif_raw = img.info.get("exif", b"")
            if isinstance(exif_raw, bytes) and len(exif_raw) > 100:
                raw = _extract_sd_params_from_bytes(exif_raw)
                if raw:
                    source = "EXIF raw bytes scan"

        # 4. JPEG COM marker (img.info["comment"])
        if not raw:
            comment = img.info.get("comment", b"")
            if comment:
                raw = _try_decode_bytes(comment) if isinstance(comment, bytes) else str(comment).strip()
                if raw:
                    source = "JPEG COM marker"

        # 5. フォーマット問わず img.info のフォールバック
        if not raw:
            for key in ("parameters", "prompt", "Comment", "Description"):
                val = img.info.get(key, "")
                if val:
                    if isinstance(val, bytes):
                        raw = _try_decode_bytes(val)
                    else:
                        raw = str(val).strip()
                    if raw:
                        source = f"img.info[{key}]"
                        break

        # 6. ファイル全体のrawバイトスキャン（最終フォールバック）
        if not raw:
            try:
                with open(file_path, "rb") as fb:
                    file_bytes = fb.read()
                raw = _extract_sd_params_from_bytes(file_bytes)
                if raw:
                    source = "file bytes scan"
            except Exception:
                pass

        if not raw:
            log_message(f"PNG Info: 生成情報なし format={img.format} info_keys={list(img.info.keys())}")
            return {"error": "生成情報が見つかりません。\nSD WebUI / ComfyUI 等で生成した画像を使用してください。"}

        log_message(f"PNG Info: 読取成功 source={source} len={len(raw)}")

        # 最終クリーンアップ: NULLバイトやエンコーディング残骸を除去
        raw = raw.replace("\x00", "").strip()

        # パラメータ文字列をpositive / negative / params に分離
        positive = raw
        negative = ""
        params = ""
        neg_idx = raw.find("Negative prompt:")
        steps_idx = raw.find("\nSteps:")
        if neg_idx >= 0:
            positive = raw[:neg_idx].strip()
            if steps_idx >= 0 and steps_idx > neg_idx:
                negative = raw[neg_idx + len("Negative prompt:"):steps_idx].strip()
                params = raw[steps_idx + 1:].strip()
            else:
                negative = raw[neg_idx + len("Negative prompt:"):].strip()
        elif steps_idx >= 0:
            positive = raw[:steps_idx].strip()
            params = raw[steps_idx + 1:].strip()

        return {"positive": positive, "negative": negative, "parameters": params, "raw": raw}
    except Exception as e:
        return {"error": f"画像読み取りエラー: {e}"}


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
    total_max_retries = MAX_RETRIES_OVERLOADED  # 529対応で最大試行回数を拡大
    overloaded_count = 0  # 529エラー連続カウント
    for attempt in range(total_max_retries):
        try:
            if model == MODELS.get("haiku_fast"):
                model_name = "Haiku(fast)"
            elif "haiku" in model:
                model_name = "Haiku(4.5)"
            else:
                model_name = "Sonnet"
            log_message(f"API呼び出し開始: {model_name} (試行 {attempt + 1}/{total_max_retries})")

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
            cache_creation = getattr(usage, 'cache_creation_input_tokens', 0) or 0
            cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
            cost_tracker.add(model, usage.input_tokens, usage.output_tokens,
                             cache_creation, cache_read)

            # キャッシュ統計ログ
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
            if e.status_code == 529:
                # 529 Overloaded: 段階的対処
                overloaded_count += 1
                # 3回失敗後: 別モデルにフォールバック（Haiku→Sonnet）
                if overloaded_count == 3 and "haiku" in model and model != MODELS.get("haiku_fast"):
                    fallback_model = MODELS["sonnet"]
                    log_message(f"529 Overloaded 3回連続: Sonnetにフォールバック")
                    if callback:
                        callback(f"Haiku過負荷、Sonnetで代替生成中...")
                    model = fallback_model  # 以降の試行はSonnetを使用
                    time.sleep(5)
                    continue
                wait_time = RETRY_DELAY_OVERLOADED * min(overloaded_count, 4)  # 15→30→45→60秒
                log_message(f"529 Overloaded ({overloaded_count}回目): {wait_time}秒待機後に再試行")
                if callback:
                    callback(f"サーバー過負荷、{wait_time}秒待機中... ({overloaded_count}/{MAX_RETRIES_OVERLOADED})")
                time.sleep(wait_time)
                if overloaded_count >= MAX_RETRIES_OVERLOADED:
                    raise RuntimeError(f"サーバー過負荷が継続（{MAX_RETRIES_OVERLOADED}回試行）。時間をおいて再実行してください。")
                continue
            log_message(f"API error {e.status_code}: {e}")
            if attempt < total_max_retries - 1:
                if callback:
                    callback(f"APIエラー、再試行中...")
                time.sleep(RETRY_DELAY)
            else:
                raise

        except anthropic.APITimeoutError as e:
            log_message(f"API timeout: {e}")
            if callback:
                callback(f"タイムアウト、再試行中...")
            if attempt < total_max_retries - 1:
                time.sleep(RETRY_DELAY * 2)
            else:
                raise RuntimeError(f"APIタイムアウト（{total_max_retries}回試行）")

        except Exception as e:
            log_message(f"Error: {e}")
            if callback:
                callback(f"エラー: {str(e)[:30]}...")
            if attempt < total_max_retries - 1:
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
    callback: Optional[Callable] = None,
    male_description: str = "",
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
{f"## 男性キャラクター外見{chr(10)}{male_description}{chr(10)}※ あらすじにおける男性の描写はこの外見設定を反映すること{chr(10)}" if male_description else ""}## テーマ: {theme_name}
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
9. **同じ行為の繰り返し禁止**: 本番パートで最低5種の異なる展開（体位変更/場所移動/行為変更/主導権交代等）を含めること
10. **展開バリエーション例**: 愛撫→口淫→正常位→体位変更→騎乗位→バック→絶頂のように行為を変化させエスカレートすること
11. **視点**: あらすじは女性キャラ（ヒロイン）視点で書くこと。男性は「相手の男」「彼」と呼び、「主人公」と呼ばないこと

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
    _serihu_info = _select_serihu_skill(theme, char_profiles)
    serihu_skill_name = _serihu_info["primary"]
    serihu_skill = load_skill(serihu_skill_name)
    _serihu_secondary = load_skill(_serihu_info["secondary"]) if _serihu_info.get("secondary") else ""
    _serihu_ratio = _serihu_info.get("ratio", 1.0)
    _serihu_personality = _serihu_info.get("personality", "")
    bubble_writer_skill = load_skill("cg_bubble_writer")
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

{bubble_writer_skill if bubble_writer_skill else ""}

{char_guide if char_guide else "（キャラ設定なし）"}

## CG集フォーマット補足
CG画像1枚 + 吹き出し1-3個（ヒロイン1-2+男0-1） + SE 0-4個。画像がメイン。
moan=喘ぎ声のみ(説明文禁止) / speech=感情的反応のみ / story_flow=各シーン固有(コピペ禁止)

{f'''
## ⚠️ セリフ品質ガイド（厳守・最優先）

bubblesのtextは以下の【喘ぎ声バリエーション集】と【鉄則】に厳密に従え。
「タスク手順」「不自然診断」「改訂版セリフ」等のセクションは無視せよ。

★ 喘ぎ声は必ず下記辞書の【段階1〜4】から選べ。自分で喘ぎを創作するな。
★ intensityに対応する段階を使え（intensity 1-2=段階1、intensity 3=段階2、intensity 4=段階3、intensity 5=段階4）
★ 前シーンで使った喘ぎと同じものは絶対禁止。毎シーン辞書の別パターンを選べ。

{serihu_skill}
''' if serihu_skill else ''}{f'''

### サブスタイル（混合比率{int((1-_serihu_ratio)*100)}%で以下のスタイルも取り入れること）:
{_serihu_secondary}
''' if _serihu_secondary and _serihu_ratio < 1.0 else ''}{f'''
★ キャラ性格タイプ「{_serihu_personality}」を意識したセリフ。ギャップ感を出すこと。
''' if _serihu_personality else ''}

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
3. **bubblesは1-3個**（ヒロイン1-2個 + 男性0-1個。セリフの長さは自由）
4. sd_promptは「{QUALITY_POSITIVE_TAGS} + キャラ外見 + ポーズ + 表情 + 場所・背景」の順
5. **sd_promptにオノマトペ・日本語テキストを含めない**（英語のDanbooruタグのみ）
6. タグは重複なくカンマ区切り
7. **シーン1→シーン2は自然に繋がるストーリーにすること**
8. **前シーンまでの展開を必ず引き継ぐこと**
9. **同じセリフ・オノマトペを複数シーンで繰り返さない**
10. **type="moan"には喘ぎ声・声漏れのみ**。「そうなんだ」「汗すごい」等の説明文は絶対禁止
11. **type="speech"は感情的反応のみ**。「汗すごい」「震えてる」等の身体状態報告はナレーションであり禁止
13. **セリフに設備・家具の名前を入れない**。「便器」「便座」「手洗い台」等の設備名称はlocation_detailに書くもの。セリフでは「こんなとこで…」「ここで…」等の感情的な言い回しに置き換える
12. **story_flowは各シーン固有の展開**を書け。前シーンのコピペ禁止

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

    # スキーマバリデーション（parse直後・各シーン）
    for _bi, _br in enumerate(result_list):
        if isinstance(_br, dict):
            _bv = validate_scene(_br, _bi)
            if not _bv["valid"]:
                _bsid = _br.get("scene_id", _bi + 1)
                for _be in _bv["errors"]:
                    log_message(f"  [SCHEMA] scene_batch(シーン{_bsid}): {_be}")

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


def _generate_outline_chunk(
    client: anthropic.Anthropic,
    chunk_size: int,
    chunk_offset: int,
    total_scenes: int,
    theme_name: str,
    story_arc: str,
    key_emotions: list,
    elements_str: str,
    synopsis: str,
    char_names: list,
    act_info: str,
    previous_scenes: list,
    cost_tracker: CostTracker,
    callback: Optional[Callable] = None
) -> list:
    """アウトラインを10シーンずつチャンク生成（常にフル12フィールド形式）"""

    # 前チャンクの要約を構築（スライディングウィンドウ: 直近20件+古い分は1行要約）
    prev_summary = ""
    if previous_scenes:
        prev_lines = []
        n_prev = len(previous_scenes)

        # 古いシーン（20件より前）: 1行要約でトークン節約
        if n_prev > 20:
            prev_lines.append(f"（シーン1〜{n_prev - 20}: {n_prev - 20}シーン確定済み、省略）")
            # 最後の5シーンの要約だけ残す（古い分の雰囲気を伝える）
            old_start = max(0, n_prev - 30)
            old_end = n_prev - 20
            for s in previous_scenes[old_start:old_end]:
                sid = s.get("scene_id", "?")
                title = s.get("title", "")[:15]
                intensity = s.get("intensity", 3)
                prev_lines.append(f"[{sid}] {title} (i={intensity})")

        # 直近20件: フル要約
        recent_start = max(0, n_prev - 20)
        for s in previous_scenes[recent_start:]:
            sid = s.get("scene_id", "?")
            title = s.get("title", "")[:20]
            intensity = s.get("intensity", 3)
            situation = s.get("situation", "")[:60]
            loc = s.get("location", "")[:15]
            ea = s.get("emotional_arc", {})
            emo = f'{ea.get("start", "")}→{ea.get("end", "")}' if isinstance(ea, dict) else ""
            prev_lines.append(f"[{sid}] {title} (i={intensity}, {loc}) {situation} ({emo})")
        prev_summary = f"""## 確定済みシーン（これに続けて書くこと。重複禁止）
{chr(10).join(prev_lines)}
"""

    start_id = chunk_offset + 1
    end_id = chunk_offset + chunk_size

    output_format = (
        "## 出力形式（JSON配列）\n"
        f"シーン{start_id}〜{end_id}の{chunk_size}シーンをJSON配列で出力：\n"
        "{\n"
        f'    "scene_id": {start_id}〜{end_id}の番号,\n'
        '    "title": "シーンタイトル",\n'
        '    "goal": "このシーンの目的",\n'
        '    "location": "場所",\n'
        '    "time": "時間帯",\n'
        '    "situation": "このシーンで何が起きるか（具体的な状況）",\n'
        '    "story_flow": "前シーンからの繋がりと次シーンへの橋渡し",\n'
        '    "emotional_arc": {"start": "シーン冒頭の感情", "end": "シーン終わりの感情"},\n'
        '    "beats": ["展開ビート1", "展開ビート2", "展開ビート3"],\n'
        '    "intensity": 1から5の数値,\n'
        '    "erotic_level": "none/light/medium/heavy/climax",\n'
        '    "viewer_hook": "視聴者を引き付けるポイント"\n'
        "}\n\n"
        f"⚠️ 必ず{chunk_size}シーン（ID {start_id}〜{end_id}）全て出力すること。"
    )

    chunk_prompt = f"""{prev_summary}以下のストーリーあらすじに基づき、シーン{start_id}〜{end_id}（{chunk_size}シーン分）を生成してください。
全体は{total_scenes}シーンの作品です。

## ストーリーあらすじ
{synopsis}

## 登場キャラクター
{', '.join(char_names)}

## テーマ: {theme_name}
- ストーリーアーク: {story_arc}
- 重要な感情: {', '.join(key_emotions)}
- ストーリー要素:
{elements_str}

## シーン配分（全{total_scenes}シーン）
{act_info}

{output_format}

## 絶対ルール
1. あらすじの内容を忠実にこのチャンク分に割り当てること
2. 確定済みシーンの直後から自然に繋がること
3. situationは具体的に記述（抽象表現禁止）
4. 各シーンのsituationは前シーンと異なる具体的展開にすること
5. locationは3シーン連続で同じ場所にしてはならない
6. emotional_arcのstartは前シーンのendと一致させること
7. intensity 5は全体で最大2シーン。段階的にエスカレートすること
8. story_flowは各シーン固有の内容を書け（重複禁止）

## ⚠️ 体位・行為バリエーション強制（違反即不合格）
- 本番シーン（intensity 4-5）は全て異なる体位・行為を指定すること
- 体位リスト: 正常位/後背位/騎乗位/立ちバック/側位/寝バック/座位/駅弁/対面座位/背面騎乗位/フェラ/パイズリ
- 同じ体位の2連続禁止。同じsituation表現の繰り返し禁止
- titleの重複禁止。同じキーワードを含むtitleは最大2回まで
- 確定済みシーンのsituation/titleと被らないこと

JSON配列のみ出力。"""

    if callback:
        callback(f"[INFO]アウトラインチャンク生成: シーン{start_id}〜{end_id}")

    response = _call_api(
        client, MODELS["haiku"],
        f"FANZA同人CG集の脚本プランナーです。全{total_scenes}シーンのうちシーン{start_id}〜{end_id}の詳細設計をJSON配列で出力します。",
        chunk_prompt, cost_tracker, min(8192, chunk_size * 400), callback
    )

    chunk = parse_json_response(response)
    if not isinstance(chunk, list):
        chunk = [chunk] if isinstance(chunk, dict) else []

    # scene_idを正しいオフセットに修正
    for i, scene in enumerate(chunk):
        scene["scene_id"] = chunk_offset + i + 1

    return chunk


def _get_intensity_curve_instruction(theme_guide: dict) -> str:
    """テーマのintensity curveに応じたプロンプト指示を生成"""
    curve = theme_guide.get("intensity_curve", "ascending")
    if curve == "valley":
        return (
            "\n## intensity展開パターン: 谷あり型（このテーマ特有）\n"
            "このテーマでは中盤に「intensity が一時低下する谷」を作ること。\n"
            "例: 1→2→3→4→**3**→4→5→5→4（中盤で心理的葛藤・罪悪感・中断リスクにより一旦引く）\n"
            "谷の部分では心理描写を重視し、再上昇時により激しいエスカレーションにすること。"
        )
    elif curve == "staircase":
        return (
            "\n## intensity展開パターン: 階段型（段階的深化）\n"
            "このテーマでは同じintensityを2シーン連続で使ってから次の段階に上げること。\n"
            "例: 1→2→3→3→4→4→5→5→4（各段階を定着させてから次へ）\n"
            "調教/堕落の「慣れ→次のステップ」を表現する。"
        )
    elif curve == "wave":
        return (
            "\n## intensity展開パターン: 波型（緩急リズム）\n"
            "このテーマでは「上がって少し下がる」を繰り返し、波のようにエスカレートさせること。\n"
            "例: 1→3→2→4→3→4→3→5→5→4（焦らしを入れながら段階的に上げる）\n"
            "「Slow,slow,quick,slow」のダンスリズムで、焦らしの後は必ず前より強いintensityにすること。"
        )
    elif curve == "two_stage":
        return (
            "\n## intensity展開パターン: 2段ロケット型（クライマックス2回）\n"
            "このテーマでは1回目のクライマックスの後にintensityを落とし、2回目の山を作ること。\n"
            "例: 1→2→3→4→5→3→4→4→5→4（1回目絶頂→リセット→2回目はより激しく）\n"
            "2回目は1回目を超える激しさで、新しい体位・行為を導入すること。"
        )
    elif curve == "plateau":
        return (
            "\n## intensity展開パターン: 高原型（intensity 4を長く維持）\n"
            "このテーマではintensity 4の状態を長く維持し、最後に一気にクライマックスへ。\n"
            "例: 1→2→3→4→4→4→4→4→5→4（じわじわ快感を蓄積し最後に爆発）\n"
            "高原部分では体位・アングルの変化で単調さを防ぐこと。"
        )
    # ascending（デフォルト）
    return (
        "\n## intensity展開パターン: 上昇型（基本）\n"
        "基本は1→2→3→4→5の上昇型だが、単調な右肩上がりにしないこと。\n"
        "本番パート（intensity 4）の中にも緩急をつけること:\n"
        "例: 1→2→3→4→3→4→4→5→4→3→4→5→4（中盤に小さな谷を作る）\n"
        "intensity 4が5シーン以上連続する場合は、間にintensity 3のシーンを1つ挟むこと。"
    )


def generate_outline(
    client: anthropic.Anthropic,
    context: dict,
    num_scenes: int,
    theme: str,
    cost_tracker: CostTracker,
    callback: Optional[Callable] = None,
    synopsis: str = "",
    story_structure: dict = None,
    male_description: str = "",
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

    # シーン配分計算（テーマ別ratio → ユーザー設定 → デフォルト）
    # テーマ別ratioがある場合はそれを優先
    theme_intro = theme_guide.get("intro_ratio", 0.08)
    theme_foreplay = theme_guide.get("foreplay_ratio", 0.20)
    if story_structure is None:
        story_structure = {"prologue": round(theme_intro * 100), "main": 80, "epilogue": 10}
    prologue_pct = story_structure.get("prologue", round(theme_intro * 100)) / 100
    epilogue_pct = story_structure.get("epilogue", 10) / 100

    act1 = max(1, round(num_scenes * prologue_pct))       # プロローグ
    act4 = max(1, round(num_scenes * epilogue_pct))        # エピローグ
    main_scenes = num_scenes - act1 - act4                  # 本編合計
    if main_scenes < 2:
        main_scenes = 2
        act1 = max(1, num_scenes - main_scenes - 1)
        act4 = num_scenes - act1 - main_scenes
    act2 = max(1, round(main_scenes * theme_foreplay))     # 前戯（テーマ別比率）
    act3 = main_scenes - act2                              # 本番（残り）

    elements_str = chr(10).join(f'・{e}' for e in story_elements) if story_elements else "・特になし"

    # 常にフル12フィールド形式を使用（チャンク生成で大量シーンにも対応）
    output_format_section = (
        "## 出力形式（JSON配列）\n"
        "各シーンは以下の形式：\n"
        "{\n"
        '    "scene_id": シーン番号,\n'
        '    "title": "シーンタイトル",\n'
        '    "goal": "このシーンの目的",\n'
        '    "location": "場所",\n'
        '    "time": "時間帯",\n'
        '    "situation": "このシーンで何が起きるか（具体的な状況）",\n'
        '    "story_flow": "前シーンからの繋がりと次シーンへの橋渡し",\n'
        '    "emotional_arc": {"start": "シーン冒頭の感情", "end": "シーン終わりの感情"},\n'
        '    "beats": ["展開ビート1", "展開ビート2", "展開ビート3"],\n'
        '    "intensity": 1から5の数値,\n'
        '    "erotic_level": "none/light/medium/heavy/climax",\n'
        '    "viewer_hook": "視聴者を引き付けるポイント"\n'
        "}"
    )

    # ストーリーパターン自動選択（エロ漫画定番パターンで整合性向上）
    story_pattern_section = ""
    try:
        from ero_dialogue_pool import select_story_pattern
        matched_pattern = select_story_pattern(theme, synopsis)
        if matched_pattern:
            beats_str = "\n".join(f"  {i+1}. {b}" for i, b in enumerate(matched_pattern["beats"]))
            i_pattern = " → ".join(str(x) for x in matched_pattern["intensity_pattern"])
            story_pattern_section = (
                f"\n## 参考ストーリーパターン: {matched_pattern['name']}\n"
                f"以下は参考用の定番展開ビートです。あらすじの内容を優先しつつ、"
                f"展開のテンポや感情の流れを参考にしてください:\n"
                f"{beats_str}\n"
                f"セリフ進化: {matched_pattern['dialogue_evolution']}\n"
                f"intensity展開の参考: {i_pattern}\n"
            )
    except ImportError:
        pass

    # 大量シーン時の追加指示
    long_script_section = ""
    if num_scenes >= 25:
        long_script_section = f"""
## ⚠️ 大量シーン（{num_scenes}シーン）追加ルール

1. **本番パートにmini-arc**: {act3}シーンの本番パートは、3-4個のmini-arc（小さな起承転結）に分割せよ。各mini-arcは「新しい行為/体位で開始→エスカレート→小さなクライマックス→次への転換」で構成
2. **intensity 4の連続上限5**: intensity 4が5シーン以上連続する場合、必ず間にintensity 3のシーン（休憩/体位変更/心理描写）を1つ挟むこと
3. **男性セリフ多様性**: 男性のセリフは5パターン（脅迫/挑発/命令/嘲笑/独白）を均等に使え。同じ意味のセリフの連続禁止。末尾フレーズの重複は最大2回まで。観察実況（「～だな」「～してるな」）禁止
4. **locationの位置変化**: 同じ場所が続く場合も「場所内の位置」を変えよ（例: 便座→壁際→洗面台→床）
5. **titleルール**: titleは4-12文字、行為/体位/感情を反映。location名（「トイレ」「教室」等）をtitleに含めてはならない
"""

    prompt = f"""以下のストーリーあらすじを{num_scenes}シーンに分割し、各シーンの詳細をJSON配列で出力してください。

## ストーリーあらすじ（これに忠実に分割すること）
{synopsis}

## 登場キャラクター
{', '.join(char_names)}
{f"{chr(10)}## 男性キャラクター外見: {male_description}{chr(10)}※ situationやbeatsに男性が登場する場合、この外見設定を反映すること{chr(10)}※ 男性はfaceless male（顔なし）。顔の特徴は描写しない{chr(10)}" if male_description else ""}
## テーマ: {theme_name}
- ストーリーアーク: {story_arc}
- 重要な感情: {', '.join(key_emotions)}
- ストーリー要素:
{elements_str}
{story_pattern_section}

## シーン配分（{num_scenes}シーン・エロ70%以上）
- 第1幕・導入: {act1}シーン → intensity 1-2（最低限の状況設定。1ページで済ませる）
- 第2幕・前戯: {act2}シーン → intensity 3（焦らし・脱衣・愛撫）
- 第3幕・本番: {act3}シーン → intensity 4（基本）と5（クライマックスのみ最大2シーン）。必ず4→4→5→5→4のように段階をつけること
- 第4幕・余韻: {act4}シーン → intensity 3-4（事後・余韻。エロの余韻を残す）
※ FANZA CG集は読者がエロを求めて購入する。導入は短く、エロシーンを手厚く。
{_get_intensity_curve_instruction(theme_guide)}
{long_script_section}

{output_format_section}

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
11. **視点**: situationは女性キャラ視点で記述。男性の行動ではなく、女性の体験・反応・感情を中心に書く

## ⚠️⚠️ 体位・行為バリエーション強制ルール（最重要・違反即不合格）

**本番シーン（intensity 4-5）は全シーンで異なる体位・行為を指定すること。同じ行為の連続は絶対禁止。**

### 使用可能な体位・行為リスト（2連続使用禁止。ローテーションせよ）
正常位 / 後背位(バック) / 騎乗位 / 立ちバック / 側位 / 寝バック / 座位 / 駅弁 / 対面座位 / 背面騎乗位 / 正常位(脚持ち上げ) / うつ伏せ / マングリ返し / フェラチオ / パイズリ / 69 / 手マン / クンニ

### situation記述の多様性チェックリスト
各シーンのsituationは以下の5要素のうち最低2つが前シーンと異なること:
1. **体位**: 前シーンと違う体位名を明記
2. **主導権**: 男主導/女主導/対等 - 3シーン連続で同じ主導権は禁止
3. **テンポ**: 激しい/ゆっくり/焦らし/一気に - 交互に変化させる
4. **焦点部位**: 胸/腰/脚/首筋/耳/背中 - 毎シーン異なる部位を描写
5. **心理状態**: 前シーンの心理の「次の段階」を必ず記述

❌ 禁止パターン: 「膣奥を責められ」「膣奥への刺激」等の同じ表現が3シーン以上
❌ 禁止パターン: 同じ体位名が2シーン連続
❌ 禁止パターン: titleに同じ単語（「膣奥」「理性」等）が3回以上出現

### titleの多様性ルール
- 全シーンのtitleは重複禁止（完全一致禁止）
- 同じキーワードを含むtitleは最大2回まで
- 具体的な行為・体位・場所・感情を反映した固有のタイトルにすること

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

    # シーン配分情報文字列（チャンク生成でも共有）
    act_info = (
        f"- 第1幕・導入: {act1}シーン → intensity 1-2\n"
        f"- 第2幕・前戯: {act2}シーン → intensity 3\n"
        f"- 第3幕・本番: {act3}シーン → intensity 4-5\n"
        f"- 第4幕・余韻: {act4}シーン → intensity 3-4"
    )

    try:
        if num_scenes <= 12:
            # 12シーン以下: シングルコール（Haiku4.5で品質確保）
            outline_max_tokens = min(8192, max(2048, num_scenes * 400))
            response = _call_api(
                client, MODELS["haiku"],
                f"FANZA同人CG集の脚本プランナーです。ストーリーあらすじを忠実に{num_scenes}シーンに分割し、各シーンの詳細設計をJSON配列で出力します。",
                prompt, cost_tracker, outline_max_tokens, callback
            )
            outline = parse_json_response(response)
            if not isinstance(outline, list) or len(outline) == 0:
                raise ValueError("Invalid outline response")
        else:
            # 13シーン以上: チャンク分割生成（10シーンずつ、常にフル形式）
            chunk_size = 10
            outline = []
            for offset in range(0, num_scenes, chunk_size):
                this_chunk = min(chunk_size, num_scenes - offset)
                log_message(f"チャンクアウトライン: シーン{offset+1}〜{offset+this_chunk} ({this_chunk}シーン)")
                chunk = _generate_outline_chunk(
                    client, this_chunk, offset, num_scenes,
                    theme_name, story_arc, key_emotions, elements_str,
                    synopsis, char_names, act_info,
                    outline,  # 確定済みシーンを渡す
                    cost_tracker, callback
                )
                outline.extend(chunk)
                log_message(f"チャンク完了: {len(chunk)}シーン取得、合計{len(outline)}シーン")

            if len(outline) == 0:
                raise ValueError("Chunk outline generation failed")

        # スキーマバリデーション（setdefault補完前に実行して欠落を検出）
        _outline_val = validate_outline(outline, num_scenes)
        if not _outline_val["valid"]:
            for _oe in _outline_val["errors"]:
                log_message(f"  [SCHEMA] outline(parse直後): {_oe}")

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

        # タイトル重複修正（アウトライン段階で検出・修正）
        _seen_titles_ol = set()
        _title_fix_ol = 0
        for s in outline:
            t = s.get("title", "")
            if t in _seen_titles_ol:
                sid = s.get("scene_id", "?")
                sit = s.get("situation", "")[:20]
                loc = s.get("location", "")
                new_title = f"{loc}での{sit}" if loc and sit else f"シーン{sid}"
                if new_title in _seen_titles_ol:
                    new_title = f"{new_title}({sid})"
                s["title"] = new_title
                _title_fix_ol += 1
                log_message(f"アウトラインtitle重複修正: S{sid}「{t}」→「{new_title}」")
            _seen_titles_ol.add(s.get("title", ""))
        if _title_fix_ol > 0:
            log_message(f"アウトラインtitle重複修正: {_title_fix_ol}件")

        # situation連続類似検出・警告（3連続で同一キーワードパターン）
        _SITUATION_KW_OL = ["膣奥", "突かれ", "責められ", "腰を振", "ピストン",
                            "挿入", "犯され", "抱かれ", "押し倒", "襲われ",
                            "口内", "フェラ", "パイズリ", "騎乗", "バック",
                            "正常位", "四つん這い", "膝立ち", "指で"]
        _sit_kw_list = []
        for s in outline:
            sit = s.get("situation", "")
            kws = frozenset(kw for kw in _SITUATION_KW_OL if kw in sit)
            _sit_kw_list.append(kws)
        _consec_same_ol = 0
        for idx in range(2, len(outline)):
            if (_sit_kw_list[idx] and
                _sit_kw_list[idx] == _sit_kw_list[idx - 1] == _sit_kw_list[idx - 2]):
                _consec_same_ol += 1
                sid = outline[idx].get("scene_id", idx + 1)
                log_message(f"⚠️ アウトライン: S{sid-2}〜S{sid} situationキーワード同一（{_sit_kw_list[idx]}）")
        if _consec_same_ol > 0:
            log_message(f"⚠️ アウトライン: {_consec_same_ol}箇所でsituation連続類似検出")

        # アウトライン数がnum_scenesに不足する場合、自動補完
        if len(outline) < num_scenes:
            missing = num_scenes - len(outline)
            log_message(f"⚠️ アウトラインが{missing}シーン不足（{len(outline)}/{num_scenes}）、自動補完")
            if callback:
                callback(f"[WARN]AI出力{len(outline)}シーン（{num_scenes}要求）、{missing}シーン自動補完中...")

            for _pad_i in range(missing):
                new_id = len(outline) + 1
                ratio = new_id / num_scenes

                # 位置に基づくintensity決定
                if ratio >= (1.0 - epilogue_pct):
                    pad_intensity = 3  # エピローグ
                elif ratio >= (1.0 - epilogue_pct - 0.1):
                    pad_intensity = 5  # クライマックス付近
                else:
                    pad_intensity = 4  # 本番

                # 前シーンとのintensity飛躍を防止
                if outline:
                    prev_int = outline[-1].get("intensity", 3)
                    if pad_intensity - prev_int >= 2:
                        pad_intensity = prev_int + 1

                outline.append({
                    "scene_id": new_id,
                    "title": f"シーン{new_id}",
                    "goal": "",
                    "location": outline[-1].get("location", "室内") if outline else "室内",
                    "time": "",
                    "situation": "",
                    "story_flow": "",
                    "emotional_arc": {"start": "", "end": ""},
                    "beats": [],
                    "intensity": min(pad_intensity, 5),
                    "erotic_level": erotic_map.get(min(pad_intensity, 5), "medium"),
                    "viewer_hook": ""
                })

            # 補完後のerotic_level再整合
            for scene in outline:
                scene["erotic_level"] = erotic_map.get(scene.get("intensity", 3), "medium")
            log_message(f"アウトライン補完完了: {len(outline)}シーン")

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
    desc = scene.get("description", "")[:200]
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


def _compact_scene_summary(scene: dict) -> str:
    """シーンの圧縮要約（セリフ/SE情報を保持）"""
    sid = scene.get("scene_id", "?")
    title = scene.get("title", "")[:20]
    desc = scene.get("description", "")[:60]
    intensity = scene.get("intensity", 3)
    # 吹き出しテキストだけ抽出（ブラックリスト用に保持）
    bubbles = scene.get("bubbles", [])
    bubble_texts = ", ".join(f"「{b.get('text', '')}」" for b in bubbles if b.get("text"))
    se = scene.get("onomatopoeia", [])
    se_str = ", ".join(se) if se else ""
    story_flow = scene.get("story_flow", "")[:80]
    return (
        f"[シーン{sid}] {title} (intensity={intensity}) {desc}\n"
        f"  吹き出し: {bubble_texts or 'なし'}\n"
        f"  SE: {se_str or 'なし'}\n"
        f"  次への繋がり: {story_flow}"
    )


def _oneliner_scene_summary(scene: dict) -> str:
    """シーンの1行概要（6シーン以前用、ブラックリスト情報なし）"""
    sid = scene.get("scene_id", "?")
    title = scene.get("title", "")[:10]
    intensity = scene.get("intensity", 3)
    mood = scene.get("mood", "")[:6]
    return f"[シーン{sid}] {title} (intensity={intensity}, {mood})"


def _build_story_so_far(story_summaries: list, scene_results: list) -> str:
    """story_so_farを構築（3層スライディングウィンドウ）。

    - 直近3シーン: フルテキスト（extract_scene_summary）
    - 4-8シーン前: 圧縮要約（_compact_scene_summary）※セリフ/SE情報保持
    - 9シーン以上前: 1行概要（トークン節約）

    セリフ重複防止のブラックリストは別途used_blacklistで処理されるため、
    古いシーンの詳細をstory_so_farに保持する必要は薄い。
    """
    n = len(story_summaries)
    if n == 0:
        return ""

    parts = []

    # 9シーン以上前: 1行概要（トークン節約: ~20トークン/シーン）
    oneline_end = max(0, n - 8)
    if oneline_end > 0:
        parts.append("--- 序盤の展開 ---")
        for j in range(oneline_end):
            if j < len(scene_results):
                sc = scene_results[j]
                sid = sc.get("scene_id", j + 1)
                title = sc.get("title", "")[:15]
                desc = sc.get("description", "")[:40]
                parts.append(f"[S{sid}] {title}: {desc}")
        parts.append("")

    # 4-8シーン前: 圧縮要約（セリフ/SE情報保持でブラックリスト補助）
    compact_start = max(0, n - 8)
    compact_end = max(0, n - 3)
    if compact_start < compact_end:
        parts.append("--- これまでの展開 ---")
        for j in range(compact_start, compact_end):
            if j < len(scene_results):
                parts.append(_compact_scene_summary(scene_results[j]))
        parts.append("")

    # 直近3シーン: フルテキスト
    recent_start = max(0, n - 3)
    if recent_start < n:
        parts.append("--- 直近の展開（詳細） ---")
        for j in range(recent_start, n):
            parts.append(story_summaries[j])

    return "\n".join(parts)


def generate_scene_draft(
    client: anthropic.Anthropic,
    context: dict,
    scene: dict,
    jailbreak: str,
    cost_tracker: CostTracker,
    theme: str = "",
    char_profiles: list = None,
    callback: Optional[Callable] = None,
    story_so_far: str = "",
    synopsis: str = "",
    outline_roadmap: str = "",
    male_description: str = "",
) -> dict:
    skill = load_skill("low_cost_pipeline")

    # Danbooruタグ強化スキルを読み込み
    danbooru_nsfw = load_skill("danbooru_nsfw_tags")

    # NSFWシーン構成スキル
    scene_composer = load_skill("nsfw_scene_composer")

    # エロ漫画セリフスキルを性格・テーマ別に選択
    _serihu_info = _select_serihu_skill(theme, char_profiles)
    serihu_skill_name = _serihu_info["primary"]
    serihu_skill = load_skill(serihu_skill_name)
    _serihu_secondary = load_skill(_serihu_info["secondary"]) if _serihu_info.get("secondary") else ""
    _serihu_ratio = _serihu_info.get("ratio", 1.0)
    _serihu_personality = _serihu_info.get("personality", "")

    # CG集吹き出し専門スキル（自然な日本語セリフガイド）
    bubble_writer_skill = load_skill("cg_bubble_writer")

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

    # フルネーム→短縮名マップ構築（キャラ名途切れ対策用）
    char_short_names = []
    for full_name in char_names:
        short = full_name
        for sep in ["・", " ", "＝", "　"]:
            idx = full_name.find(sep)
            if idx > 0:
                short = full_name[:idx]
                break
        char_short_names.append(short)

    # キャラ固有セリフプールからfew-shot例を注入
    char_pool_section = ""
    if char_profiles:
        _cp0 = char_profiles[0]
        _cp_id = generate_char_id(_cp0.get("work_title", ""), _cp0.get("character_name", ""))
        _scene_char_pool = load_character_pool(_cp_id)
        if _scene_char_pool:
            sample_lines = []
            for _ph in ["foreplay", "penetration", "climax"]:
                phase_speech = _scene_char_pool.get("speech", {}).get(_ph, [])[:2]
                sample_lines.extend(phase_speech)
            if sample_lines:
                char_pool_section = "\n## キャラ固有セリフ例（このトーンで書け）\n" + "\n".join(f"・{l}" for l in sample_lines)

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

【吹き出し指針（1-3個）】
・女: 絶頂系の喘ぎ1-2個（★セリフ品質ガイドの【段階4】から選べ。自作するな。前シーンと被らないこと）
・男: 言葉責め0-1個（5パターンを均等に使え: 脅迫/挑発/命令/嘲笑/独白。前シーンと同じ意味のセリフ禁止）
  例: 「中に出すぞ」「全部受けろ」「イケ」「もう逃がさねえ」「もっと鳴け」

【オノマトペ指針（3-4個・辞書から選べ）】
・射精系+反応系+抽送系を組み合わせる
  例: ドビュッ, ビクビクッ, パンパンパン, ドクドクッ

【心情】
・{key_emotions[2] if len(key_emotions) > 2 else '快感に溺れる'}
・{key_emotions[3] if len(key_emotions) > 3 else '理性と本能の葛藤'}

【禁止】
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

【吹き出し指針（1-3個）】
・女: 喘ぎ1-2個（★セリフ品質ガイドの【段階3】から選べ。自作するな。前シーンと被らないこと）
・男: 言葉責め0-1個（5パターンを均等に使え: 脅迫/挑発/命令/嘲笑/独白。前シーンと同じ意味のセリフ禁止）
  例: 「もっと鳴け」「逃がさねぇぞ」「欲しいんだろ」「もう我慢すんな」

【オノマトペ指針（2-3個・辞書から選べ）】
・挿入系+抽送系+濡れ系を組み合わせる
  例: ズブッ, パンパン, グチュグチュ

【心情】
・{key_emotions[1] if len(key_emotions) > 1 else '恥ずかしさと快感の葛藤'}
・{key_emotions[2] if len(key_emotions) > 2 else 'もっと欲しいという欲求'}

【禁止】
❌ 説明的なセリフ
❌ 前シーンと同じ喘ぎパターン
"""
    elif intensity == 3:
        erotic_instruction = f"""
## 前戯・焦らしシーン（intensity 3）

エロの助走。脱衣・愛撫・キス等。期待感を煽る画像に短い吹き出し。

【吹き出し指針（1-3個）】
・女: ドキドキ感のある反応1-2個（★セリフ品質ガイドの【段階2】から選べ）
・男: 煽りor会話0-1個（前シーンと同じ意味のセリフ禁止。脅迫/挑発/命令/嘲笑/独白の5パターンを使い分けろ）
  例: 「おとなしくしろ」「脱げ」「正直になれよ」

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
・自然な短い会話（1-3個）
・例: 「ねえ…」「え…？」
・**喘ぎ声・絶頂セリフは絶対NG**。まだ本番前。ドキドキや戸惑いのみ

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
・自然な一言（1-3個）。状況説明はdescriptionで行い、吹き出しは最小限
・例: 「ただいま〜」「久しぶり…」
・**絶対に喘ぎ声・♡・エロ系セリフを入れるな**。歩いてるだけ、座ってるだけの場面で喘ぐな

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

{bubble_writer_skill if bubble_writer_skill else ""}

{char_guide if char_guide else "（キャラ設定なし）"}

{char_pool_section}
{f"""
## 男性キャラクター外見設定
**外見: {male_description}**
- descriptionに男性が登場する場合、必ずこの外見設定を反映した描写にすること
- 男性はfaceless male（顔なし）として扱う。男性の顔の特徴（目・鼻・口・表情）は一切描写しない
- 描写例: 「{male_description}の男に押し倒され…」「背後から{male_description}に覆いかぶさられ…」
""" if male_description else """
## 男性キャラクター
- 男性はfaceless male（顔なし）として扱う。男性の顔の特徴（目・鼻・口・表情）は一切描写しない
"""}
## FANZA同人CG集フォーマット
「セリフ付きCG集」＝1枚絵に吹き出し+オノマトペ。**画像がメイン、テキストはサブ**。
各ページ: CG画像1枚 + 吹き出し1-3個（ヒロイン1-2+男0-1） + SE 0-4個

## ⚠️ 追加厳守ルール（上記吹き出しスキルに加えて）

### セリフ・SE重複禁止
story_so_farのセリフ・SEと同一・類似は絶対禁止。毎シーン辞書の別パターンを選べ。

### 場所名の一貫性
同じ場所は**全シーンで同一の表記**。表記ブレ禁止。

### セリフ内容整合性
- moan=喘ぎ声のみ。説明文禁止（❌「そうなんだ」「汗すごい」）
- speech=感情的反応のみ。身体報告禁止（❌「震えてる」「目が回る」）
- thought=感情断片のみ。ナレーション禁止（❌「こんなことをしている自分が…」）。部位ラベル冒頭禁止（❌「胸…こんなに…」「太もも…そんな…」→✅「熱い…」「ゾクって…」）
- 男性speech=命令/挑発/独白のみ。観察実況禁止（❌「いい声だな」「敏感だな」「ここも感じるんだな」→✅「もっと鳴け」「欲しいんだろ」「逃がさねぇ」）
- descriptionと吹き出しの内容が**論理的に一致**すること

### story_flowの書き方
各シーン固有の展開。前シーンのコピペ禁止。状況が必ず進展すること。

### thought先頭パターン反復禁止
同じ書き出し（先頭2文字）を3シーン以内で再使用するな。バリエーションが生命線。
同一構文（X…Yが…Z…）の3連続も禁止。構文パターンを変えろ（疑問/自嘲/矛盾/驚き/諦め/感覚）。
感情は恐怖/羞恥/快感否定の3種だけでなく、怒り/諦め/自嘲/混乱/背徳感も使え。
❌禁止: thoughtで「胸…」「太もも…」「耳…」等、部位名を冒頭に置く説明型（「胸…こんなに…」）。部位を主語にするな。感覚・感情を主語にしろ（「熱い…」「ゾクって…」「やばい…」）。
同じキーワード（「だめ」「声」等）は全シーン中4回まで。

## オノマトペ辞書（同じ組み合わせの連続禁止）
・挿入: ズブッ, ヌプッ, ズリュッ, ヌルッ, ズンッ ・抽送: パンパン, グチュグチュ, ヌチュヌチュ
・愛撫: サワッ, ペロッ, チュッ, レロレロ ・吸引: チュパッ, ジュルッ, ゴクッ
・射精: ドクドク, ドビュッ, ビュルル ・反応: ビクッ, ビクビク, ガクガク, ゾクッ
・心音: ドキドキ, バクバク ・衝撃: ドンッ, ギシギシ ・濡れ: トロッ, グショッ, ヌルヌル
・剥ぎ: ビリッ, スルッ

{f'''
## ⚠️ セリフ品質ガイド（厳守・最優先）

bubblesのtextは以下の【喘ぎ声バリエーション集】と【鉄則】に厳密に従え。
「タスク手順」「不自然診断」「改訂版セリフ」等のセクションは無視せよ。

★ 喘ぎ声は必ず下記辞書の【段階1〜4】から選べ。自分で喘ぎを創作するな。
★ intensityに対応する段階を使え（intensity 1-2=段階1、intensity 3=段階2、intensity 4=段階3、intensity 5=段階4）
★ 前シーンで使った喘ぎと同じものは絶対禁止。毎シーン辞書の別パターンを選べ。

{serihu_skill}
''' if serihu_skill else ''}{f'''

### サブスタイル（混合比率{int((1-_serihu_ratio)*100)}%で以下のスタイルも取り入れること）:
{_serihu_secondary}
''' if _serihu_secondary and _serihu_ratio < 1.0 else ''}{f'''
★ キャラ性格タイプ「{_serihu_personality}」を意識したセリフ。ギャップ感を出すこと。
''' if _serihu_personality else ''}

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

    # ストーリー連続性セクション（使用済みセリフ・SE・story_flowを明示抽出）
    story_context_section = ""
    if story_so_far:
        # story_so_farから使用済みセリフ・SE・story_flowを抽出してブラックリスト化
        import re as _re
        used_bubbles = []
        used_se = []
        used_flows = []
        for line in story_so_far.split("\n"):
            line = line.strip()
            if line.startswith("吹き出し:"):
                bubble_content = line[len("吹き出し:"):].strip()
                if bubble_content and bubble_content != "なし":
                    used_bubbles.append(bubble_content)
            elif line.startswith("SE:"):
                se_content = line[len("SE:"):].strip()
                if se_content and se_content != "なし":
                    used_se.append(se_content)
            elif line.startswith("次への繋がり:"):
                flow_content = line[len("次への繋がり:"):].strip()
                if flow_content and len(flow_content) >= 10:
                    used_flows.append(flow_content)

        blacklist_parts = []
        if used_bubbles:
            blacklist_parts.append("【使用済みセリフ（同一・類似禁止）】")
            for ub in used_bubbles:
                blacklist_parts.append(f"  ❌ {ub}")
        if used_se:
            blacklist_parts.append("【使用済み効果音（同一組み合わせ禁止）】")
            for us in used_se:
                blacklist_parts.append(f"  ❌ {us}")
        if used_flows:
            blacklist_parts.append("【使用済みstory_flow（同一テキスト禁止。各シーン固有の展開を書け）】")
            for uf in used_flows:
                blacklist_parts.append(f"  ❌ {uf}")
        used_blacklist = "\n".join(blacklist_parts) if blacklist_parts else "（初回シーンのため禁止リストなし）"

        story_context_section = f"""
## ⚠️ ストーリーの連続性（最重要）

以下は前のシーンまでの展開です。**必ずこの続きとして**シーンを書いてください。

{story_so_far}

### 🚫 使用禁止リスト（以下と同じ・類似は絶対禁止）
{used_blacklist}

### 禁止事項（違反したら不合格）
- **上の使用禁止リストにあるセリフ・SE・story_flowと同一または類似は使用不可**
- **story_flowは毎シーン固有の内容を書け**。前シーンと同じ文章のコピペは即不合格
- **前シーンと同じ状況描写・同じ展開の繰り返し禁止**
- **ストーリーを必ず前シーンより先に進めること（行為をエスカレート）**
- **同じ場所名は前シーンと同じ表記を使え（表記ブレ禁止）**
- **キャラ名はフルネーム「{', '.join(char_names) if char_names else 'ヒロイン'}」または姓「{', '.join(char_short_names) if char_short_names else 'ヒロイン'}」のみ使用**

### ⚠️ エスカレーション制御（段階飛躍禁止）
- **前シーンの行為レベルから1段階だけ進めること**
- 前シーンが前戯なら→このシーンは挿入開始。いきなり複数人や絶頂は禁止
- 前シーンが1対1なら→このシーンも1対1か、せいぜい2人目の登場まで
- 前シーンで抵抗していたなら→このシーンは葛藤。いきなり完全堕落は禁止
- **心情の変化は前シーンの「次への繋がり」を必ず引き継ぐこと**

### ⚠️ 体位・描写バリエーション強制（違反即不合格）
- **descriptionに書く体位・行為は前シーンと必ず変えること**
- 使える体位: 正常位/後背位/騎乗位/立ちバック/側位/寝バック/座位/駅弁/対面座位/背面騎乗位/フェラ/パイズリ/手マン
- 描写する身体部位・焦点も前シーンと変えること（胸→腰→脚→首筋→耳→背中をローテーション）
- **「膣奥」「膣内」等の同じ表現を3シーン以上繰り返し使用するのは禁止**
- **descriptionは前シーンと異なる体位・行為・身体部位を描写すること**
- **titleは全シーンで固有であること。前シーンと同じキーワードの繰り返し禁止**
---
"""

    # ロードマップセクション構築
    roadmap_section = ""
    if outline_roadmap:
        roadmap_section = f"""## ストーリーロードマップ（全体構成）
{outline_roadmap}

★ 現在生成: シーン{scene['scene_id']}「{scene.get('title', '')}」
このシーンの前後関係を意識し、ストーリーを確実に進めること。
---
"""

    # アウトラインフィールドを明示的にフォーマット（JSON dumpの代わり）
    _ea = scene.get("emotional_arc", {})
    _ea_start = _ea.get("start", "") if isinstance(_ea, dict) else ""
    _ea_end = _ea.get("end", "") if isinstance(_ea, dict) else ""
    scene_instruction = f"""## このシーンの設計指示
- シーンID: {scene['scene_id']}
- タイトル: {scene.get('title', '')}
- 目的(goal): {scene.get('goal', '指定なし')}
- 状況(situation): {scene.get('situation', '指定なし')}
- 場所: {scene.get('location', '')}
- 感情推移: {_ea_start} → {_ea_end}
- 展開ビート: {', '.join(scene.get('beats', [])) if scene.get('beats') else '指定なし'}
- 次への繋がり: {scene.get('story_flow', '指定なし')}
- エロレベル: {scene.get('erotic_level', '')}
- 視聴者フック: {scene.get('viewer_hook', '')}
- intensity: {scene.get('intensity', 3)}

⚠️ 上記の「状況」「感情推移」「展開ビート」に忠実にシーンを生成せよ。
特にdescriptionは「状況」の内容を具体的に膨らませること。"""

    prompt = f"""{synopsis_section}{roadmap_section}{story_context_section}設定: {json.dumps(context, ensure_ascii=False)}
{scene_instruction}

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
3. **bubblesは1-3個**（ヒロイン1-2個 + 男性0-1個。セリフの長さは自由）。男性セリフは全体の25-35%のシーンにのみ入れること（20シーンなら5-7シーンのみ）
4. typeはspeech/moan/thoughtの3種。intensity 4-5はmoanメイン。**moanには喘ぎ声のみ（説明文禁止）**
5. **onomatopoeiaは場面に合った効果音**（intensity 1-2はなし〜1個、3は1-2個、4-5は2-4個）
6. sd_promptは「{QUALITY_POSITIVE_TAGS}」の後にカンマで区切り「キャラ外見 + ポーズ + 表情 + 場所・背景 + 照明」を続ける。quality括弧の中にはmasterpiece, best_qualityのみ入れる。キャラ名やheadphones等の外見タグは括弧外に書くこと
7. **sd_promptはこのシーンの実際の内容のみを反映**すること
8. **sd_promptにオノマトペ・日本語テキストを含めない**（英語のDanbooruタグのみ使用）
9. **前シーンの流れを必ず引き継ぐこと**
10. **キャラの一人称・語尾はキャラガイドを絶対厳守**
11. **descriptionは全て日本語で書くこと**（英語タグはsd_promptのみ）
12. **titleに「○回戦」「続き」等の安易な表現禁止**。具体的な行為・状況を反映した簡潔なタイトルにすること
13. **キャラ名**: 初出時はフルネーム「{', '.join(char_names) if char_names else 'ヒロイン'}」を使用。同じdescription内の2回目以降は姓「{', '.join(char_short_names) if char_short_names else 'ヒロイン'}」でよい。表記ブレ厳禁（他の呼び方は禁止）
14. **descriptionに具体的な行為・体位を必ず書け**。「囲まれる」「溺れる」だけの抽象表現は禁止。何をどうされているか書くこと
15. **視点**: descriptionは女性キャラ視点で書くこと。男性を「主人公」と呼ばない。男性は「彼」「相手の男」「男性」と表記
16. **お嬢様口調のintensity対応**: intensity 4-5ではお嬢様口調（ですの/ですわ等）は崩壊させること。理性が飛んだ状態で丁寧語は不自然。「ですの」→「…の…♡」「ですわ」→「…♡」に崩す"""

    # 重複禁止の最終警告（user promptの末尾に配置 = モデルが最も注目する位置）
    dedup_warning = ""
    if story_so_far:
        dedup_warning = f"""

## ⚠️⚠️⚠️ 最終チェック（出力前に必ず確認） ⚠️⚠️⚠️

以下の条件を1つでも満たす場合、出力をやり直せ:
- bubblesのtextに前シーンと同じ文言がある → 辞書から別パターンを選び直せ
- onomatopoeiaが前シーンと同じ組み合わせ → 別の効果音に変えろ
- descriptionが前シーンと類似している → 具体的な行為を変えろ
- descriptionでキャラ名を省略している（「ボア」だけにしてる等） → 必ずフルネームで書け
- キャラ名が「{', '.join(char_names) if char_names else 'ヒロイン'}」または「{', '.join(char_short_names) if char_short_names else 'ヒロイン'}」以外の表記になっている → 修正しろ
- 男性キャラのセリフに♡が含まれている → 即座に削除しろ
- 男性キャラが喘いでいる(moanタイプ) → speechに変更し男性的な短い台詞に書き換えろ
- ヒロインの一人称・語尾がキャラ設定と食い違っている → 修正しろ
- bubblesが4個以上ある → ヒロイン1-2個+男性0-1個の最大3個に絞れ
- 男性セリフに「私たち」「いいよ」「ね」等の女性的表現がある → 「俺たち」「いいぞ」「な」に直せ
- 男性セリフが全体の40%以上のシーンに含まれている → 5-7シーンのみに男性セリフを入れ、残りは削除しろ
- descriptionが歩行・食事・帰宅等の非エロ場面なのにbubblesに喘ぎ・♡がある → 場面に合った普通のセリフに直せ
- 「初めて」「彼のこと忘れ」等の同じフレーズを全体で3回以上使っている → 別の表現にしろ
- type="moan"の吹き出しに説明文・会話文が入っている → 喘ぎ声に書き換えろ（「そうなんだ」「汗すごい」等は禁止）
- story_flowが前シーンと同一テキスト → このシーン固有の展開に書き換えろ
- descriptionの体位・行為が前シーンと同じ → 別の体位・行為に変えろ（正常位/後背位/騎乗位/立ちバック/側位/座位等をローテーション）
- titleが前シーンと同じキーワード（「膣奥」「理性」等）を含んでいる → 別のキーワードに変えろ"""

    prompt = prompt + dedup_warning + "\n\nJSONのみ出力。"

    # モデル自動選択: intensity別にコスト最適化
    # intensity 4-5 → Sonnet（本番+クライマックス: セリフ品質が最重要）
    # intensity 1-3 → Haiku 4.5（導入・前戯シーン）
    # ※ Haiku3(fast)はシーン生成に不適: キャラ名化け・NSFW品質不足
    if intensity >= 4:
        model = MODELS["sonnet"]
        model_name = "Sonnet"
    else:
        model = MODELS["haiku"]
        model_name = "Haiku(4.5)"
    
    if callback:
        callback(f"シーン {scene['scene_id']} 生成中 ({model_name}, 重要度{intensity}, {theme_name}, セリフ:{serihu_skill_name})...")
    
    response = _call_api(
        client, model,
        system_with_cache,
        prompt, cost_tracker, 3000, callback
    )
    
    # 重複排除の後処理
    result = parse_json_response(response)

    # スキーマバリデーション（parse直後）
    if isinstance(result, dict):
        _sv = validate_scene(result)
        if not _sv["valid"]:
            sid = result.get("scene_id", "?")
            for _se in _sv["errors"]:
                log_message(f"  [SCHEMA] scene_draft(シーン{sid}): {_se}")

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
1. 1ページ = ヒロインのセリフ1-2個 + 男性セリフ0-1個（最大3個）
2. 説明的→感情的に（「嬉しい気持ちです」→「嬉しい…♡」）
3. 文章→断片に（主語・目的語を削除）
4. 一人称・語尾を徹底チェック
5. 4個以上の吹き出しがあればヒロイン1-2個+男性0-1個に絞る

【エロシーン改善】
- 「気持ちいいです」→「きもちぃ…♡」
- 「もっとしてください」→「もっと…♡」
- 「イキそうです」→「イっちゃ…♡」
- 喘ぎ声は途切れ途切れに

【オノマトペ改善】
- 場面に合った効果音か確認
- 数は適切か（intensity 1-2: 0-1個、3: 1-2個、4-5: 2-4個）

【禁止】
❌ 4個以上の吹き出し（ヒロイン1-2 + 男性0-1 = 最大3個）
❌ 説明調のテキスト
❌ キャラの一人称・語尾の不一致

Output JSON only."""

    prompt = f"""設定: {json.dumps(context, ensure_ascii=False)}

下書き: {json.dumps(draft, ensure_ascii=False)}

上記の下書きを清書してください：

1. 各吹き出しをキャラの口調に合わせる
2. 吹き出しを最大3個に絞る（ヒロイン1-2 + 男性0-1）
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


# === Wave並列生成ヘルパー ===
def _generate_single_scene_for_wave(
    client, context, scene, jailbreak, cost_tracker, theme, char_profiles,
    callback, story_so_far, synopsis, current_roadmap, male_description,
    scene_index, total_scenes, timestamp,
):
    """Wave並列生成用: 1シーン分の生成+エラーハンドリング。

    戻り値: (scene_index, result_dict_or_None, summary_string_or_None, error_msg_or_None)
    InterruptedError は再送出してWave全体を停止させる。
    """
    intensity = scene.get("intensity", 3)
    model_type = "Sonnet" if intensity >= 4 else "Haiku(4.5)"

    def _try_generate(**extra_kwargs):
        draft = generate_scene_draft(
            client, context, scene, jailbreak,
            cost_tracker, theme, char_profiles, callback,
            story_so_far=story_so_far,
            synopsis=extra_kwargs.get("synopsis_override", synopsis),
            outline_roadmap=current_roadmap,
            male_description=male_description,
        )
        draft["intensity"] = intensity
        scene_val = validate_scene(draft, scene_index)
        if not scene_val["valid"]:
            for err in scene_val["errors"]:
                log_message(f"  [SCHEMA] シーン{scene_index+1}: {err}")
        return draft

    try:
        log_message(f"シーン {scene_index+1}/{total_scenes} 生成開始 (intensity={intensity}, {model_type})")
        if callback:
            callback(f"[SCENE]シーン {scene_index+1}/{total_scenes} [{model_type}] 重要度{intensity}")

        draft = _try_generate()

        # ファイル保存
        draft_file = DRAFTS_DIR / f"draft_{timestamp}_scene{scene_index+1}.json"
        with open(draft_file, "w", encoding="utf-8") as f:
            json.dump(draft, f, ensure_ascii=False, indent=2)
        final_file = FINAL_DIR / f"final_{timestamp}_scene{scene_index+1}.json"
        with open(final_file, "w", encoding="utf-8") as f:
            json.dump(draft, f, ensure_ascii=False, indent=2)

        summary = extract_scene_summary(draft)
        log_message(f"シーン {scene_index+1}/{total_scenes} 完了")
        if callback:
            callback(f"[OK]シーン {scene_index+1}/{total_scenes} 完了")
        return (scene_index, draft, summary, None)

    except InterruptedError:
        # ユーザー停止要求 → 再送出してWave全体を停止させる
        raise

    except Exception as e:
        err_msg = str(e)
        log_message(f"シーン {scene_index+1} 生成エラー: {err_msg}")

        # 529 Overloaded: クールダウン後にリトライ
        is_overloaded = "サーバー過負荷" in err_msg or "529" in err_msg or "Overloaded" in err_msg
        if is_overloaded:
            cooldown = 60
            log_message(f"サーバー過負荷検出: {cooldown}秒待機後にシーン{scene_index+1}をリトライ")
            if callback:
                callback(f"[WARN]サーバー過負荷、{cooldown}秒待機後にシーン{scene_index+1}をリトライ...")
            time.sleep(cooldown)
            try:
                draft = _try_generate()
                draft_file = DRAFTS_DIR / f"draft_{timestamp}_scene{scene_index+1}.json"
                with open(draft_file, "w", encoding="utf-8") as f:
                    json.dump(draft, f, ensure_ascii=False, indent=2)
                final_file = FINAL_DIR / f"final_{timestamp}_scene{scene_index+1}.json"
                with open(final_file, "w", encoding="utf-8") as f:
                    json.dump(draft, f, ensure_ascii=False, indent=2)
                summary = extract_scene_summary(draft)
                log_message(f"シーン {scene_index+1} 過負荷リトライ成功")
                if callback:
                    callback(f"[OK]シーン {scene_index+1}/{total_scenes} 過負荷リトライ成功")
                return (scene_index, draft, summary, None)
            except InterruptedError:
                raise
            except Exception as e2:
                err_msg = str(e2)
                log_message(f"シーン {scene_index+1} 過負荷リトライも失敗: {err_msg}")

        # コンテンツ拒否 or JSONパースエラー → 最大2回リトライ
        is_refusal = any(kw in err_msg for kw in ["倫理", "対応することはできません", "cannot", "inappropriate"])
        is_json_error = any(kw in err_msg for kw in ["Invalid JSON", "No JSON", "Empty response", "JSONDecodeError"])

        if is_refusal or is_json_error:
            retry_reason = "コンテンツ拒否" if is_refusal else "JSONパースエラー"
            log_message(f"シーン {scene_index+1} {retry_reason}検出、リトライ")
            if callback:
                callback(f"[WARN]シーン {scene_index+1} {retry_reason}、リトライ中...")
            for retry_n in range(2):
                try:
                    draft = _try_generate(synopsis_override="" if is_refusal else synopsis)
                    draft_file = DRAFTS_DIR / f"draft_{timestamp}_scene{scene_index+1}.json"
                    with open(draft_file, "w", encoding="utf-8") as f:
                        json.dump(draft, f, ensure_ascii=False, indent=2)
                    final_file = FINAL_DIR / f"final_{timestamp}_scene{scene_index+1}.json"
                    with open(final_file, "w", encoding="utf-8") as f:
                        json.dump(draft, f, ensure_ascii=False, indent=2)
                    summary = extract_scene_summary(draft)
                    log_message(f"シーン {scene_index+1} リトライ{retry_n+1}回目成功")
                    if callback:
                        callback(f"[OK]シーン {scene_index+1}/{total_scenes} リトライ成功")
                    return (scene_index, draft, summary, None)
                except InterruptedError:
                    raise
                except Exception as e2:
                    log_message(f"シーン {scene_index+1} リトライ{retry_n+1}回目失敗: {e2}")

        # 全リトライ失敗 → エラー結果を返す
        import traceback
        log_message(traceback.format_exc())
        if callback:
            callback(f"[ERROR]シーン {scene_index+1} エラー: {err_msg[:50]}")

        error_result = {
            "scene_id": scene.get("scene_id", scene_index + 1),
            "title": f"シーン{scene_index+1}",
            "mood": "エラー",
            "bubbles": [],
            "onomatopoeia": [],
            "direction": f"生成エラー: {err_msg[:100]}",
            "sd_prompt": ""
        }
        return (scene_index, error_result, f"[シーン{scene_index+1}: エラーにより欠落]", None)


def _generate_scenes_wave(
    wave_scenes, client, context, jailbreak, cost_tracker, theme, char_profiles,
    callback, story_so_far, synopsis, roadmap_lines, male_description,
    total_scenes, timestamp, max_workers=CONCURRENT_BATCH_SIZE,
):
    """Wave内の全シーンをThreadPoolExecutorで同時生成し、scene_index順にソートして返す。

    戻り値: [(scene_index, result_dict, summary_string, error), ...]
    InterruptedError発生時はexecutorをシャットダウンして再送出。
    """
    wave_results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for scene_index, scene in wave_scenes:
            # 各シーンのロードマップ（近傍±5行）
            marked_lines = []
            window_start = max(0, scene_index - 5)
            window_end = min(len(roadmap_lines), scene_index + 6)
            if window_start > 0:
                marked_lines.append(f"  ... (シーン1〜{window_start}省略)")
            for j in range(window_start, window_end):
                line = roadmap_lines[j]
                if j == scene_index:
                    marked_lines.append(f"★ {line}")
                else:
                    marked_lines.append(f"  {line}")
            if window_end < len(roadmap_lines):
                marked_lines.append(f"  ... (シーン{window_end+1}〜{len(roadmap_lines)}省略)")
            current_roadmap = "\n".join(marked_lines)

            future = executor.submit(
                _generate_single_scene_for_wave,
                client, context, scene, jailbreak, cost_tracker, theme, char_profiles,
                callback, story_so_far, synopsis, current_roadmap, male_description,
                scene_index, total_scenes, timestamp,
            )
            futures[future] = scene_index

        interrupted = False
        for future in as_completed(futures):
            try:
                result = future.result()
                wave_results.append(result)
            except InterruptedError:
                interrupted = True
                # 残りのfutureをキャンセル
                for f in futures:
                    f.cancel()
                break

        if interrupted:
            raise InterruptedError("ユーザーによる停止")

    # scene_index順にソート
    wave_results.sort(key=lambda x: x[0])
    return wave_results


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
    male_tags: str = "",
    time_tags: str = "",
    location_type: str = "",
    male_description: str = "",
    sd_quality_tags: str = "",
    sd_prefix_tags: str = "",
    sd_suffix_tags: str = "",
) -> tuple[list, CostTracker]:
    client = anthropic.Anthropic(api_key=api_key)
    log_message("Claude (Anthropic) バックエンドで生成開始")
    cost_tracker = CostTracker()

    jailbreak = load_file(JAILBREAK_FILE)

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

    # テーマ自動推定
    if not theme:
        theme = _infer_theme_from_concept(concept)
        if theme:
            log_message(f"テーマ自動推定: {THEME_GUIDES.get(theme, {}).get('name', theme)}")

    # テーマ情報
    theme_guide = THEME_GUIDES.get(theme, {})
    if not theme_guide:
        theme_guide = _build_dynamic_theme_guide(concept)
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

    # スキーマバリデーション: コンテキスト
    ctx_validation = validate_context(context)
    if not ctx_validation["valid"]:
        for err in ctx_validation["errors"]:
            log_message(f"  [SCHEMA] context: {err}")
        if callback:
            callback(f"[WARN]コンテキスト検証: {len(ctx_validation['errors'])}件の問題")

    if callback:
        callback("[OK]コンテキスト圧縮完了")

    # Phase 2: ストーリーあらすじ生成（Haiku 1回）
    log_message("Phase 2 開始: ストーリーあらすじ生成")
    if callback:
        callback("🔧 Phase 2: ストーリー原案作成")

    try:
        synopsis = generate_synopsis(client, concept, context, num_scenes, theme, cost_tracker, callback, male_description=male_description)
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
        outline = generate_outline(client, context, num_scenes, theme, cost_tracker, callback, synopsis=synopsis, story_structure=story_structure, male_description=male_description)
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

    # スキーマバリデーション: アウトライン
    outline_validation = validate_outline(outline, num_scenes)
    if not outline_validation["valid"]:
        for err in outline_validation["errors"]:
            log_message(f"  [SCHEMA] outline: {err}")
        if callback:
            callback(f"[WARN]アウトライン検証: {len(outline_validation['errors'])}件の問題")

    if callback:
        _haiku_n = sum(1 for s in outline if s.get("intensity", 3) <= 4)
        _high_n = sum(1 for s in outline if s.get("intensity", 3) >= 5)
        callback(f"[OK]シーン分割完成: {len(outline)}シーン（Haiku4.5×{_haiku_n} + Sonnet×{_high_n}）")

    # コスト見積もり（Prompt Caching反映版）
    haiku_count = sum(1 for s in outline if s.get("intensity", 3) <= 3)
    high_count = sum(1 for s in outline if s.get("intensity", 3) >= 4)
    h_cost = COSTS.get(MODELS["haiku"], {"input": 1.00, "output": 5.00})
    s_cost = COSTS.get(MODELS["sonnet"], {"input": 3.00, "output": 15.00})
    # あらすじ+アウトライン → haiku 4.5
    overhead_cost = 2 * (2000 / 1_000_000 * h_cost["input"] + 2000 / 1_000_000 * h_cost["output"])
    # シーン生成（Prompt Caching: systemは1回cache_create + (N-1)回cache_read）
    cached_sys = 16000  # systemプロンプト推定トークン数
    avg_user = 3000  # 平均user prompt
    # Haiku: cache_create 1回(1.25x) + cache_read (N-1)回(0.1x) + 非キャッシュ入力 + 出力
    haiku_scene_cost = (
        (cached_sys / 1_000_000 * h_cost["input"] * 1.25) +  # 初回cache作成
        (cached_sys / 1_000_000 * h_cost["input"] * 0.10 * max(0, haiku_count - 1)) +  # cache読取
        (haiku_count * avg_user / 1_000_000 * h_cost["input"]) +  # 非キャッシュ入力
        (haiku_count * 700 / 1_000_000 * h_cost["output"])  # 出力
    ) if haiku_count > 0 else 0
    # Sonnet: 同様
    sonnet_scene_cost = (
        (cached_sys / 1_000_000 * s_cost["input"] * 1.25) +
        (cached_sys / 1_000_000 * s_cost["input"] * 0.10 * max(0, high_count - 1)) +
        (high_count * avg_user / 1_000_000 * s_cost["input"]) +
        (high_count * 700 / 1_000_000 * s_cost["output"])
    ) if high_count > 0 else 0
    est_cost = overhead_cost + haiku_scene_cost + sonnet_scene_cost
    if callback:
        callback(f"[COST]推定コスト: ${est_cost:.4f}（API {len(outline)+2}回: Haiku4.5×{haiku_count} + Sonnet×{high_count}）")

    # Phase 4: シーン生成
    results = []
    story_summaries = []

    # ストーリーロードマップ構築（全シーンの概要を各シーン生成に渡す）
    roadmap_lines = []
    for s in outline:
        sid = s.get("scene_id", "?")
        title = s.get("title", "")[:20]
        _rm_intensity = s.get("intensity", 3)
        situation = s.get("situation", "")[:60]
        location = s.get("location", "")[:15]
        goal = s.get("goal", "")[:30]
        goal_part = f" 目的:{goal}" if goal else ""
        roadmap_lines.append(f"[{sid}] {title} (i={_rm_intensity}, {location}) {situation}{goal_part}")
    outline_roadmap = "\n".join(roadmap_lines)

    use_wave_parallel = len(outline) >= CONCURRENT_MIN_SCENES

    if use_wave_parallel:
        # === Wave並列モード: 5シーン同時生成 ===
        num_waves = (len(outline) + CONCURRENT_BATCH_SIZE - 1) // CONCURRENT_BATCH_SIZE
        log_message(f"Wave並列モード: {CONCURRENT_BATCH_SIZE}シーン同時生成×{num_waves}wave")
        if callback:
            callback(f"[INFO]Wave並列モード: {CONCURRENT_BATCH_SIZE}シーン同時生成×{num_waves}wave")

        wave_idx = 0
        scene_cursor = 0
        while scene_cursor < len(outline):
            wave_end = min(scene_cursor + CONCURRENT_BATCH_SIZE, len(outline))
            wave_scenes = [(i, outline[i]) for i in range(scene_cursor, wave_end)]
            wave_idx += 1

            log_message(f"Wave {wave_idx}: シーン {scene_cursor+1}-{wave_end}/{len(outline)} 並列生成中...")
            if callback:
                callback(f"[WAVE]Wave {wave_idx}: シーン {scene_cursor+1}-{wave_end}/{len(outline)} 並列生成中...")

            # Wave開始前にstory_so_farスナップショットを取得（Wave内全シーンで共有）
            story_so_far = _build_story_so_far(story_summaries, results)

            wave_results = _generate_scenes_wave(
                wave_scenes, client, context, jailbreak, cost_tracker, theme,
                char_profiles, callback, story_so_far, synopsis, roadmap_lines,
                male_description, len(outline), timestamp,
            )

            # 結果をscene_index順に蓄積
            for si, draft, summary, _err in wave_results:
                results.append(draft)
                story_summaries.append(summary)
                log_message(f"シーン {si+1} 要約蓄積: {summary[:80]}...")

            log_message(f"Wave {wave_idx} 完了: シーン {scene_cursor+1}-{wave_end}/{len(outline)}")
            if callback:
                callback(f"[OK]Wave {wave_idx} 完了: シーン {scene_cursor+1}-{wave_end}/{len(outline)}")

            scene_cursor = wave_end

            # Wave間クールダウン（最終Wave以外）
            if scene_cursor < len(outline):
                # ユーザー停止チェック
                if callback:
                    try:
                        callback(f"[INFO]Wave間クールダウン {CONCURRENT_WAVE_COOLDOWN}秒...")
                    except InterruptedError:
                        raise
                time.sleep(CONCURRENT_WAVE_COOLDOWN)

    else:
        # === 直列モード: 12シーン以下（従来通り） ===
        for i, scene in enumerate(outline):
            intensity = scene.get("intensity", 3)
            model_type = "Sonnet" if intensity >= 4 else "Haiku(4.5)"

            # story_so_far を構築（スライディングウィンドウ方式）
            story_so_far = _build_story_so_far(story_summaries, results)

            # 現在シーン近傍±5のロードマップ
            marked_lines = []
            window_start = max(0, i - 5)
            window_end = min(len(roadmap_lines), i + 6)
            if window_start > 0:
                marked_lines.append(f"  ... (シーン1〜{window_start}省略)")
            for j in range(window_start, window_end):
                line = roadmap_lines[j]
                if j == i:
                    marked_lines.append(f"★ {line}")
                else:
                    marked_lines.append(f"  {line}")
            if window_end < len(roadmap_lines):
                marked_lines.append(f"  ... (シーン{window_end+1}〜{len(roadmap_lines)}省略)")
            current_roadmap = "\n".join(marked_lines)

            try:
                log_message(f"シーン {i+1}/{len(outline)} 生成開始 (intensity={intensity}, {model_type})")
                if callback:
                    callback(f"[SCENE]シーン {i+1}/{len(outline)} [{model_type}] 重要度{intensity}")

                draft = generate_scene_draft(
                    client, context, scene, jailbreak,
                    cost_tracker, theme, char_profiles, callback,
                    story_so_far=story_so_far,
                    synopsis=synopsis,
                    outline_roadmap=current_roadmap,
                    male_description=male_description,
                )

                draft["intensity"] = intensity

                # スキーマバリデーション: 個別シーン
                scene_val = validate_scene(draft, i)
                if not scene_val["valid"]:
                    for err in scene_val["errors"]:
                        log_message(f"  [SCHEMA] シーン{i+1}: {err}")
                    if callback:
                        callback(f"[WARN]シーン{i+1}検証: {len(scene_val['errors'])}件の問題")

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

                # 529 Overloaded: グローバルクールダウン後にリトライ
                is_overloaded = "サーバー過負荷" in err_msg or "529" in err_msg or "Overloaded" in err_msg
                if is_overloaded:
                    cooldown = 60
                    log_message(f"サーバー過負荷検出: {cooldown}秒のグローバルクールダウン後にシーン{i+1}をリトライ")
                    if callback:
                        callback(f"[WARN]サーバー過負荷、{cooldown}秒待機後にシーン{i+1}をリトライ...")
                    time.sleep(cooldown)
                    try:
                        draft = generate_scene_draft(
                            client, context, scene, jailbreak,
                            cost_tracker, theme, char_profiles, callback,
                            story_so_far=story_so_far, synopsis=synopsis,
                            outline_roadmap=current_roadmap
                        )
                        draft["intensity"] = intensity
                        results.append(draft)
                        summary = extract_scene_summary(draft)
                        story_summaries.append(summary)
                        log_message(f"シーン {i+1} 過負荷リトライ成功")
                        if callback:
                            callback(f"[OK]シーン {i+1}/{len(outline)} 過負荷リトライ成功")
                        continue
                    except Exception as e2:
                        err_msg = str(e2)
                        log_message(f"シーン {i+1} 過負荷リトライも失敗: {err_msg}")

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
                                client, context, scene, jailbreak,
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

    # スキーマバリデーション: 結果配列全体
    results_validation = validate_results(results)
    if not results_validation["valid"]:
        log_message(f"[SCHEMA] 結果検証: {len(results_validation['errors'])}件の構造問題")
        for sid, errs in results_validation.get("scene_errors", {}).items():
            for err in errs:
                log_message(f"  [SCHEMA] シーン{sid}: {err}")
        if callback:
            stats = results_validation["stats"]
            callback(f"[STAT]スキーマ検証: {stats['valid_count']}/{stats['total']}シーンOK, {len(results_validation['errors'])}件の構造問題")
    else:
        log_message("[SCHEMA] 結果配列全体のスキーマ検証OK")

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
    results = enhance_sd_prompts(results, char_profiles, setting_style=setting_style,
                                    male_tags=male_tags, time_tags=time_tags,
                                    location_type=location_type,
                                    sd_quality_tags=sd_quality_tags,
                                    sd_prefix_tags=sd_prefix_tags,
                                    sd_suffix_tags=sd_suffix_tags)
    log_message("SDプロンプト最適化完了")
    if callback:
        callback("[OK]SDプロンプト最適化完了")

    # 5-3: 自動修正（文字数マーカー除去、キャラ名統一、SDタグ整理、セリフ重複置換）
    results = auto_fix_script(results, char_profiles, theme=theme)
    log_message("自動修正完了")
    if callback:
        callback("🔧 自動修正完了")

    # 5-4: dedup後の再検証（文字数超過・男性セリフ数の最終チェック）
    post_validation = validate_script(results, theme, char_profiles)
    if post_validation.get("issues"):
        log_message(f"再検証: {len(post_validation['issues'])}件の警告")
        for issue in post_validation["issues"][:5]:
            log_message(f"  {issue}")

    # 完了サマリー
    success_count = sum(1 for r in results if r.get("mood") != "エラー")
    log_message(f"パイプライン完了: {success_count}/{len(results)}シーン成功")

    if callback:
        callback(f"[DONE]生成完了: {success_count}シーン成功（品質: {validation['score']}/100）")

    # メタデータを構築（エクスポート用）
    char_names = [cp.get("character_name", "") for cp in char_profiles] if char_profiles else []
    pipeline_metadata = {
        "concept": concept,
        "theme": theme,
        "theme_name": theme_name,
        "num_scenes": len(results),
        "characters": char_names,
        "story_structure": story_structure,
        "cost": cost_tracker.summary(),
        "quality_score": validation.get("score", 0),
        "model_versions": {"haiku": MODELS["haiku"], "sonnet": MODELS["sonnet"]},
        "synopsis": synopsis,
    }

    return results, cost_tracker, pipeline_metadata


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
            
            # SDプロンプト末尾にシーン番号を付与
            sd_raw = scene.get("sd_prompt", "")
            sid = scene.get("scene_id", "")
            sd_with_label = f'{sd_raw}, "シーン{sid}"' if sd_raw else ""

            if not bubbles:
                # 吹き出しがない場合でもシーン情報を出力
                writer.writerow({
                    "scene_id": sid,
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
                    "sd_prompt": sd_with_label
                })
            else:
                for idx, bubble in enumerate(bubbles):
                    writer.writerow({
                        "scene_id": sid if idx == 0 else "",
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
                        "sd_prompt": sd_with_label if idx == 0 else ""
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


def export_json(results: list, output_path: Path, metadata: dict = None):
    """JSON構造化エクスポート（メタデータ付き）"""
    data = {
        "version": "3.1.0",
        "generated_at": datetime.now().isoformat(),
        "scenes": results,
    }
    if metadata:
        meta_copy = dict(metadata)
        synopsis = meta_copy.pop("synopsis", None)
        data["metadata"] = meta_copy
        if synopsis:
            data["synopsis"] = synopsis
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def export_sd_prompts(results: list, output_path: Path):
    """SDプロンプト一括エクスポート（1行1プロンプト、シーンID付き）"""
    lines = []
    for scene in results:
        sd = scene.get("sd_prompt", "").strip()
        if sd:
            sid = scene.get("scene_id", "?")
            lines.append(f"# Scene {sid}: {scene.get('title', '')}")
            lines.append(sd)
            lines.append("")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log_message(f"SDプロンプト出力完了: {output_path}")


def export_wildcard(results: list, output_path: Path,
                    male_tags: str = "", time_tags: str = "",
                    location_type: str = ""):
    """Wild Card形式エクスポート（1行1プロンプト、SD Wild Card対応）"""
    lines = []
    # 設定コメントヘッダ追加
    if male_tags or time_tags or location_type:
        header = f"# Male: {male_tags or 'auto'} | Time: {time_tags or 'auto'} | Location: {location_type or 'auto'}"
        lines.append(header)
    for scene in results:
        sd = scene.get("sd_prompt", "").strip()
        if sd:
            sid = scene.get("scene_id", "")
            lines.append(f'{sd}, "シーン{sid}",')
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log_message(f"Wild Card出力完了: {output_path}（{len(lines)}行）")


def export_dialogue_list(results: list, output_path: Path):
    """セリフ一覧エクスポート（話者・種類・テキスト）"""
    lines = []
    for scene in results:
        sid = scene.get("scene_id", "?")
        title = scene.get("title", "")
        bubbles = scene.get("bubbles", []) or scene.get("dialogue", []) or []
        if not bubbles:
            continue
        lines.append(f"=== Scene {sid}: {title} ===")
        ono = scene.get("onomatopoeia", [])
        if ono:
            lines.append(f"  SE: {', '.join(ono) if isinstance(ono, list) else str(ono)}")
        for b in bubbles:
            speaker = b.get("speaker", "???")
            btype = b.get("type", b.get("emotion", ""))
            text = b.get("text", b.get("line", ""))
            tag = f"[{btype}]" if btype else ""
            lines.append(f"  {speaker}{tag}: {text}")
        lines.append("")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log_message(f"セリフ一覧出力完了: {output_path}")


def export_markdown(results: list, output_path: Path):
    """マークダウン形式エクスポート（脚本全体の読みやすいビュー）"""
    lines = []
    lines.append(f"# CG集脚本")
    lines.append(f"")
    lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"シーン数: {len(results)}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    for scene in results:
        sid = scene.get("scene_id", "?")
        title = scene.get("title", "")
        desc = scene.get("description", "")
        mood = scene.get("mood", "")
        location = scene.get("location_detail", "")
        direction = scene.get("direction", "")
        story_flow = scene.get("story_flow", "")
        sd = scene.get("sd_prompt", "")
        intensity = scene.get("intensity", "")

        lines.append(f"## Scene {sid}: {title}")
        lines.append(f"")
        if mood:
            lines.append(f"**雰囲気**: {mood}")
        if location:
            lines.append(f"**場所**: {location}")
        if intensity:
            lines.append(f"**強度**: {intensity}/5")
        lines.append(f"")
        if desc:
            lines.append(f"> {desc}")
            lines.append(f"")

        # キャラ心情
        feelings = scene.get("character_feelings", {})
        if feelings and isinstance(feelings, dict):
            lines.append(f"### 心情")
            for char, feeling in feelings.items():
                lines.append(f"- **{char}**: {feeling}")
            lines.append(f"")

        # セリフ
        bubbles = scene.get("bubbles", []) or scene.get("dialogue", []) or []
        if bubbles:
            lines.append(f"### セリフ")
            ono = scene.get("onomatopoeia", [])
            if ono:
                ono_str = ", ".join(ono) if isinstance(ono, list) else str(ono)
                lines.append(f"*SE: {ono_str}*")
                lines.append(f"")
            for b in bubbles:
                speaker = b.get("speaker", "???")
                btype = b.get("type", b.get("emotion", ""))
                text = b.get("text", b.get("line", ""))
                type_tag = f" ({btype})" if btype else ""
                lines.append(f"- **{speaker}**{type_tag}: {text}")
            lines.append(f"")

        # 演出
        if direction:
            lines.append(f"### 演出")
            lines.append(f"{direction}")
            lines.append(f"")

        # 次への繋がり
        if story_flow:
            lines.append(f"*次へ: {story_flow}*")
            lines.append(f"")

        # SDプロンプト
        if sd:
            lines.append(f"### SD Prompt")
            lines.append(f"```")
            lines.append(sd)
            lines.append(f"```")
            lines.append(f"")

        lines.append(f"---")
        lines.append(f"")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log_message(f"マークダウン出力完了: {output_path}")


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



def load_character_pool(char_id: str) -> dict:
    """キャラ固有プールを読み込み。なければ空dictを返す"""
    pool_path = CHARACTERS_DIR / f"{char_id}_pool.json"
    if pool_path.exists():
        with open(pool_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # プリセットチェック
    preset_path = PRESET_CHARS_DIR / f"{char_id}_pool.json"
    if preset_path.exists():
        with open(preset_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def generate_character_pool(
    client, char_id: str, bible: dict,
    cost_tracker: CostTracker, callback=None
) -> dict:
    """キャラプロファイルから専用セリフプールをAPI 1回で生成。
    moan(intensity 1-5)×各8個 + speech(6フェーズ)×各5個 + thought(6フェーズ)×各5個 = 約100個/キャラ"""

    char_name = bible.get("character_name", "ヒロイン")
    speech = bible.get("speech_pattern", {})
    emotional = bible.get("emotional_speech", {})
    erotic = bible.get("erotic_speech_guide", {})

    if callback:
        callback(f"[INFO]Step 4/4: {char_name}専用セリフプール生成中...")

    # SCENE_PHASE_SPEECH_MAPからfew-shot例を取得
    try:
        from ero_dialogue_pool import SCENE_PHASE_SPEECH_MAP
        few_shot_examples = {}
        for phase in ["foreplay", "penetration", "climax"]:
            phase_data = SCENE_PHASE_SPEECH_MAP.get(phase, {})
            few_shot_examples[phase] = {
                "speech": phase_data.get("speech", [])[:3],
                "thought": phase_data.get("thought", [])[:3],
                "moan": phase_data.get("moan", [])[:3],
            }
    except ImportError:
        few_shot_examples = {}

    few_shot_str = ""
    if few_shot_examples:
        few_shot_str = "\n## 汎用セリフ例（参考。このトーンをキャラの口調に変換せよ）\n"
        for phase, examples in few_shot_examples.items():
            few_shot_str += f"### {phase}\n"
            for btype, lines in examples.items():
                if lines:
                    few_shot_str += f"  {btype}: {', '.join(lines)}\n"

    system_prompt = f"""あなたはエロ漫画・CG集のセリフ専門ライターです。
キャラクターの口調設定に基づき、そのキャラ固有のセリフプールをJSON形式で生成します。

【キャラクター口調設定】
・名前: {char_name}
・一人称: {speech.get('first_person', '私')}
・語尾: {', '.join(speech.get('sentence_endings', ['〜よ', '〜ね']))}
・間投詞: {', '.join(speech.get('fillers', ['あっ', 'んっ']))}
・照れた時: {emotional.get('when_embarrassed', '言葉に詰まる')}
・感じてる時: {emotional.get('when_aroused', '声が震える')}
・絶頂時: {emotional.get('when_climax', '理性が飛ぶ')}
・エロ中の口癖: {erotic.get('verbal_during_sex', '特になし')}
・恥ずかしがり度: {erotic.get('shyness_level', '3')}/5

{few_shot_str}

【出力ルール】
- moanは喘ぎ声のみ（「あっ」「んっ」系）。漢字・助詞禁止。♡はintensity3以上で使用可
- speechは感情的反応の短文（1-10文字）。キャラの語尾・一人称を反映
- thoughtは心の声（1-15文字）。「…」で区切る断片的な表現
- 各フェーズの感情段階を正確に反映すること
- JSONのみ出力"""

    prompt = f"""以下の構造でJSON出力してください。

{{
    "character_name": "{char_name}",
    "char_id": "{char_id}",
    "moan": {{
        "1": ["（intensity1: 微かな息遣い8個）"],
        "2": ["（intensity2: 小さな喘ぎ8個）"],
        "3": ["（intensity3: 本格的な喘ぎ8個。♡使用可）"],
        "4": ["（intensity4: 激しい喘ぎ8個。♡♡使用可）"],
        "5": ["（intensity5: 絶頂の喘ぎ8個。♡♡♡使用可）"]
    }},
    "speech": {{
        "intro": ["（導入: 日常会話5個。キャラ語尾反映）"],
        "approach": ["（接近: 戸惑い5個）"],
        "foreplay": ["（前戯: 恥ずかしさ・感じ始め5個）"],
        "penetration": ["（挿入: 挿入リアクション5個）"],
        "climax": ["（絶頂: 絶頂セリフ5個。♡♡使用）"],
        "afterglow": ["（余韻: 事後セリフ5個）"]
    }},
    "thought": {{
        "intro": ["（導入: 緊張5個）"],
        "approach": ["（接近: 期待と不安5個）"],
        "foreplay": ["（前戯: 体の反応への驚き5個）"],
        "penetration": ["（挿入: 充足感5個）"],
        "climax": ["（絶頂: 理性崩壊5個。♡使用可）"],
        "afterglow": ["（余韻: 振り返り5個）"]
    }}
}}

【重要】
- {char_name}の口調（一人称={speech.get('first_person', '私')}、語尾={', '.join(speech.get('sentence_endings', [])[:3])}）を全セリフに反映
- 汎用的な喘ぎではなく、このキャラの性格・話し方が伝わる喘ぎ・セリフにすること
- JSONのみ出力。説明文不要"""

    response = _call_api(
        client, MODELS["sonnet"],
        system_prompt, prompt, cost_tracker, 4096, callback
    )

    pool = parse_json_response(response)

    if callback:
        # 生成数カウント
        moan_count = sum(len(v) for v in pool.get("moan", {}).values() if isinstance(v, list))
        speech_count = sum(len(v) for v in pool.get("speech", {}).values() if isinstance(v, list))
        thought_count = sum(len(v) for v in pool.get("thought", {}).values() if isinstance(v, list))
        callback(f"[OK]キャラプール生成完了: moan={moan_count}, speech={speech_count}, thought={thought_count}")

    return pool


def upgrade_character_pool_api(
    client, char_id: str, bible: dict,
    cost_tracker: CostTracker, callback=None,
    upgrade_types: list = None,
) -> dict:
    """既存ローカルプールのspeech+thoughtのみAPIで補正。moanはローカル維持。
    upgrade_types: デフォルト ["speech", "thought"]
    """
    if upgrade_types is None:
        upgrade_types = ["speech", "thought"]

    # 既存プール読み込み
    existing_pool = load_character_pool(char_id)

    # API版フル生成
    api_pool = generate_character_pool(client, char_id, bible, cost_tracker, callback)

    # 指定タイプのみAPIで上書き、それ以外はローカル維持
    merged = dict(existing_pool) if existing_pool else dict(api_pool)
    for utype in upgrade_types:
        if utype in api_pool:
            merged[utype] = api_pool[utype]

    # ソース情報追記
    source_detail = {}
    for key in ["moan", "speech", "thought"]:
        source_detail[key] = "api" if key in upgrade_types else "local"
    merged["source"] = "hybrid"
    merged["source_detail"] = source_detail

    return merged


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
    pool_path = CHARACTERS_DIR / f"{char_id}_pool.json"

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
        callback("[STAT]Step 1/4: キャラクター分析")

    bible = analyze_character(client, work_title, char_name, cost_tracker, callback)

    # originality_guardを追加
    bible["originality_guard"] = {
        "avoid_canonical_lines": True,
        "avoid_known_catchphrases": True
    }

    # Step 2: キャラバイブル保存
    if callback:
        callback("[SAVE]Step 2/4: キャラバイブル保存")

    with open(bible_path, "w", encoding="utf-8") as f:
        json.dump(bible, f, ensure_ascii=False, indent=2)

    log_message(f"キャラバイブル保存: {bible_path}")

    # Step 3: Skill生成
    if callback:
        callback("[INFO]Step 3/4: Skill生成")

    skill_content = generate_character_skill(char_id, bible)

    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(skill_content)

    log_message(f"Skill保存: {skill_path}")

    # Step 4: キャラ専用セリフプール生成（ローカル優先→API補正）
    if not pool_path.exists() or force_refresh:
        # まずローカル生成（即座、$0）
        from character_pool_generator import generate_character_pool_local
        if callback:
            callback(f"[INFO]Step 4/4: {char_name}専用セリフプール生成中（ローカル）...")
        char_pool = generate_character_pool_local(bible)
        char_pool["char_id"] = char_id
        with open(pool_path, "w", encoding="utf-8") as f:
            json.dump(char_pool, f, ensure_ascii=False, indent=2)
        log_message(f"キャラプール保存（ローカル）: {pool_path}")

        # API可能ならspeech+thoughtだけAPI補正
        try:
            char_pool = upgrade_character_pool_api(
                client, char_id, bible, cost_tracker, callback,
                upgrade_types=["speech", "thought"]
            )
            with open(pool_path, "w", encoding="utf-8") as f:
                json.dump(char_pool, f, ensure_ascii=False, indent=2)
            log_message(f"キャラプール更新（API補正）: {pool_path}")
        except Exception as e:
            log_message(f"API補正スキップ（ローカル版を使用）: {e}")
            if callback:
                callback(f"[WARN]API補正スキップ、ローカル版を使用: {e}")

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
    pool_path = CHARACTERS_DIR / f"{char_id}_pool.json"

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

    # プールコピー/生成
    if not pool_path.exists():
        preset_pool_path = PRESET_CHARS_DIR / f"{char_id}_pool.json"
        if preset_pool_path.exists():
            # プリセットプールをコピー
            import shutil
            shutil.copy2(preset_pool_path, pool_path)
            if callback:
                callback(f"[FILE]プリセットプールコピー: {char_id}")
        else:
            # ローカル生成
            from character_pool_generator import generate_character_pool_local
            char_pool = generate_character_pool_local(bible)
            char_pool["char_id"] = char_id
            with open(pool_path, "w", encoding="utf-8") as f:
                json.dump(char_pool, f, ensure_ascii=False, indent=2)
            if callback:
                callback(f"[INFO]プールをローカル生成: {char_id}")

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
        # All variants use border to prevent corner anti-alias fading
        if variant == "filled":
            bg_color = MaterialColors.SURFACE_CONTAINER_HIGHEST
            border_width = 1
            border_color = MaterialColors.OUTLINE_VARIANT
        elif variant == "outlined":
            bg_color = MaterialColors.SURFACE
            border_width = 1
            border_color = MaterialColors.OUTLINE_VARIANT
        else:  # elevated (default)
            bg_color = MaterialColors.SURFACE_CONTAINER_LOW
            border_width = 1
            border_color = MaterialColors.OUTLINE_VARIANT

        super().__init__(
            master,
            fg_color=bg_color,
            corner_radius=0,   # Sharp edges — no anti-alias artifacts
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
                "hover_color": "#2563EB",  # Blue-600 on hover
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
                "hover_color": "#B91C1C",  # Red-700
                "text_color": MaterialColors.ON_ERROR,
                "border_width": 0,
            },
            "success": {
                "fg_color": MaterialColors.SUCCESS,
                "hover_color": "#15803D",  # Green-700
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
                placeholder_text_color="#3D3D3D",
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
            corner_radius=0,
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
            "success": "#15803D",    # Green-700
            "error": "#B91C1C",      # Red-700
            "warning": "#B45309"     # Amber-700
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


class ExportDialog(ctk.CTkToplevel):
    """マルチフォーマットエクスポートダイアログ"""

    FORMATS = [
        ("csv", "CSV", "Excel対応BOM付きUTF-8"),
        ("json", "JSON", "構造化データ（シーン+メタデータ+SDプロンプト）"),
        ("xlsx", "Excel", "折り返し表示対応（要openpyxl）"),
        ("sd_prompts", "SDプロンプト一括", "1行1プロンプト テキストファイル"),
        ("wildcard", "Wild Card", "SD用1行1プロンプト（__filename__で参照）"),
        ("dialogue", "セリフ一覧", "話者・種類付きテキストファイル"),
        ("markdown", "マークダウン", "脚本全体の読みやすいビュー"),
    ]

    def __init__(self, master, results: list, metadata: dict = None, **kwargs):
        super().__init__(master, **kwargs)
        self.results = results
        self.metadata = metadata
        self.title("エクスポート")
        self.geometry("460x450")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        # M3 Surface
        self.configure(fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST)

        # Header
        header = ctk.CTkFrame(self, fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST, corner_radius=0)
        header.pack(fill="x")
        icon_text_label(
            header, Icons.FILE_EXPORT, "エクスポート形式を選択",
            icon_size=14, text_size=16, text_color=MaterialColors.ON_SURFACE
        ).pack(anchor="w", padx=20, pady=16)
        ctk.CTkFrame(self, fg_color=MaterialColors.OUTLINE_VARIANT, height=1, corner_radius=0).pack(fill="x")

        # シーン数表示
        info_lbl = ctk.CTkLabel(
            self, text=f"{len(results)}シーン",
            font=ctk.CTkFont(family=FONT_JP, size=13),
            text_color=MaterialColors.ON_SURFACE_VARIANT
        )
        info_lbl.pack(anchor="w", padx=20, pady=(8, 4))

        # チェックボックスリスト
        self.format_vars = {}
        checks_frame = ctk.CTkFrame(self, fg_color="transparent")
        checks_frame.pack(fill="x", padx=20, pady=(4, 12))

        for fmt_id, fmt_name, fmt_desc in self.FORMATS:
            var = ctk.BooleanVar(value=(fmt_id in ("csv", "json")))
            self.format_vars[fmt_id] = var
            row = ctk.CTkFrame(checks_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            cb = ctk.CTkCheckBox(
                row, text=fmt_name,
                variable=var,
                font=ctk.CTkFont(family=FONT_JP, size=14),
                text_color=MaterialColors.ON_SURFACE,
                fg_color=MaterialColors.PRIMARY,
                hover_color=MaterialColors.PRIMARY_CONTAINER,
                border_color=MaterialColors.OUTLINE,
                checkmark_color=MaterialColors.ON_PRIMARY,
                corner_radius=4
            )
            cb.pack(side="left")
            if fmt_id == "xlsx" and not OPENPYXL_AVAILABLE:
                cb.configure(state="disabled")
                var.set(False)
            ctk.CTkLabel(
                row, text=fmt_desc,
                font=ctk.CTkFont(family=FONT_JP, size=12),
                text_color=MaterialColors.ON_SURFACE_VARIANT
            ).pack(side="left", padx=(8, 0))

        # JSONインポート
        ctk.CTkFrame(self, fg_color=MaterialColors.OUTLINE_VARIANT, height=1).pack(fill="x", padx=20, pady=(4, 8))
        import_row = ctk.CTkFrame(self, fg_color="transparent")
        import_row.pack(fill="x", padx=20)
        self.import_btn = MaterialButton(
            import_row, text="JSONから読込", variant="outlined", size="small",
            command=self._import_json
        )
        self.import_btn.pack(side="left")
        self.import_label = ctk.CTkLabel(
            import_row, text="",
            font=ctk.CTkFont(family=FONT_JP, size=12),
            text_color=MaterialColors.ON_SURFACE_VARIANT
        )
        self.import_label.pack(side="left", padx=(8, 0))

        # ボタン行
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(16, 20))

        MaterialButton(
            btn_row, text="エクスポート", variant="filled",
            command=self._do_export
        ).pack(side="right", padx=(8, 0))
        MaterialButton(
            btn_row, text="キャンセル", variant="outlined",
            command=self.destroy
        ).pack(side="right")

    def _import_json(self):
        """既存のJSONファイルから結果を読み込み"""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="エクスポート済みJSONを選択",
            initialdir=str(EXPORTS_DIR),
            filetypes=[("JSON files", "*.json")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            scenes = data.get("scenes", data if isinstance(data, list) else [])
            if not scenes:
                self.import_label.configure(text="シーンが見つかりません", text_color=MaterialColors.ERROR)
                return
            self.results = scenes
            # メタデータも復元
            self.metadata = data.get("metadata", None)
            self.import_label.configure(
                text=f"{len(scenes)}シーン読込済",
                text_color=MaterialColors.SUCCESS
            )
        except Exception as e:
            self.import_label.configure(text=f"読込エラー: {str(e)[:30]}", text_color=MaterialColors.ERROR)

    def _do_export(self):
        """選択されたフォーマットでエクスポート実行"""
        selected = [k for k, v in self.format_vars.items() if v.get()]
        if not selected:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        exported = []

        for fmt in selected:
            try:
                if fmt == "csv":
                    p = EXPORTS_DIR / f"script_{timestamp}.csv"
                    export_csv(self.results, p)
                    exported.append(f"CSV: {p.name}")
                elif fmt == "json":
                    p = EXPORTS_DIR / f"script_{timestamp}.json"
                    export_json(self.results, p, metadata=self.metadata)
                    exported.append(f"JSON: {p.name}")
                elif fmt == "xlsx":
                    p = EXPORTS_DIR / f"script_{timestamp}.xlsx"
                    if export_excel(self.results, p):
                        exported.append(f"Excel: {p.name}")
                elif fmt == "sd_prompts":
                    p = EXPORTS_DIR / f"sd_prompts_{timestamp}.txt"
                    export_sd_prompts(self.results, p)
                    exported.append(f"SDプロンプト: {p.name}")
                elif fmt == "wildcard":
                    p = EXPORTS_DIR / f"wildcard_{timestamp}.txt"
                    export_wildcard(self.results, p)
                    exported.append(f"Wild Card: {p.name}")
                elif fmt == "dialogue":
                    p = EXPORTS_DIR / f"dialogue_{timestamp}.txt"
                    export_dialogue_list(self.results, p)
                    exported.append(f"セリフ一覧: {p.name}")
                elif fmt == "markdown":
                    p = EXPORTS_DIR / f"script_{timestamp}.md"
                    export_markdown(self.results, p)
                    exported.append(f"Markdown: {p.name}")
            except Exception as e:
                log_message(f"エクスポートエラー ({fmt}): {e}")
                exported.append(f"{fmt}: エラー")

        # 結果通知
        if hasattr(self.master, "snackbar"):
            self.master.snackbar.show(
                f"{len(exported)}形式エクスポート完了",
                type="success"
            )
        if hasattr(self.master, "log"):
            for item in exported:
                self.master.log(f"[FILE]{item}")

        self.destroy()


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
        self.last_results = None  # 最新の生成結果を保持（再エクスポート用）
        self.last_metadata = None  # パイプラインメタデータ（再エクスポート用）
        self.create_widgets()
        self.load_saved_config()

        # CTkEntryプレースホルダー強制表示（初期化直後のタイミング問題対策）
        self.after(100, self._ensure_placeholders)

        # ドラッグ&ドロップ初期化（ウィンドウマッピング後に実行）
        self.after(200, self._setup_png_drop)

        # ウィンドウ閉じ保護
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # ショートカットキー
        self.bind("<Control-Return>", lambda e: self.start_generation())
        self.bind("<Escape>", lambda e: self.stop_generation() if self.is_generating else None)

        # プレゼンモード（Ctrl+Shift+P で切替）
        self._presentation_mode = False
        self.bind("<Control-Shift-P>", lambda e: self.toggle_presentation_mode())

    def create_widgets(self):
        # ══════════════════════════════════════════════════════════════
        # HEADER
        # ══════════════════════════════════════════════════════════════
        header = ctk.CTkFrame(self, height=56, fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="both", expand=True, padx=24, pady=12)

        icon_text_label(
            header_inner, Icons.FILM, "Daihon Rakku",
            icon_size=16, text_size=20, text_color=MaterialColors.ON_SURFACE
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

        # Header bottom border
        ctk.CTkFrame(self, fg_color=MaterialColors.OUTLINE_VARIANT, height=1, corner_radius=0).pack(fill="x")

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
        # 1. API設定（プレゼン時は非表示）
        # ══════════════════════════════════════════════════════════════
        api_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=0, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT)
        self._api_card = api_card  # プレゼンモード用参照
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
            placeholder_text_color="#3D3D3D",
            corner_radius=4, border_width=1, border_color=MaterialColors.OUTLINE
        )
        self.api_field.pack(fill="x", padx=20, pady=(0, 12))

        # ══════════════════════════════════════════════════════════════
        # 2. プロファイル管理（キャラ生成より上に配置）
        # ══════════════════════════════════════════════════════════════
        profile_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=0, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT)
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
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=4,
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
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=4,
            text_color=MaterialColors.ON_SURFACE,
            placeholder_text_color="#3D3D3D",
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
        char_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=0, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT)
        char_card.pack(fill="x", pady=(0, 16))

        icon_text_label(
            char_card, Icons.USER, "キャラクター設定",
            icon_size=12, text_size=14
        ).pack(anchor="w", padx=20, pady=(12, 8))
        ctk.CTkFrame(char_card, fg_color=MaterialColors.OUTLINE_VARIANT, height=1, corner_radius=0).pack(fill="x", padx=20, pady=(0, 8))

        # --- 使用キャラ選択行 ---
        self._char_select_row = ctk.CTkFrame(char_card, fg_color="transparent")
        self._char_select_row.pack(fill="x", padx=20, pady=(0, 12))

        # --- プリセットコンテナ（折りたたみ、初期非表示） ---
        self._preset_card = MaterialCard(
            char_card, title="二次創作・プリセットキャラ一覧", variant="outlined",
            collapsible=True, start_collapsed=True
        )
        self._preset_card.pack(fill="x", padx=16, pady=(0, 10))
        self._preset_container = self._preset_card.content_frame

        # --- プリセットタブ構築 ---
        self._all_presets = []
        self._preset_map = {}
        self._category_chips = {}
        self._selected_category = "全て"
        self._preset_card_frame = None
        self._build_preset_tab(self._preset_container)

        # --- オリジナルキャラ設定コンテナ（折りたたみ、初期非表示） ---
        self._custom_card = MaterialCard(
            char_card, title="オリジナルキャラ作成", variant="outlined",
            collapsible=True, start_collapsed=True
        )
        self._custom_card.pack(fill="x", padx=16, pady=(0, 10))
        self._custom_container = self._custom_card.content_frame

        self._selected_archetype = "ツンデレ"
        self._selected_hair_color = "黒髪"
        self._archetype_chips = {}
        self._hair_color_chips = {}
        self._build_custom_tab(self._custom_container)

        # 内部変数（config保存/復元用、UIウィジェットなし）
        self._work_title_val = ""
        self._char_name_val = ""

        # ネストスクロール衝突防止
        self._setup_nested_scroll()

        # --- 使用キャラ選択ウィジェット ---
        char_select_row = self._char_select_row

        ctk.CTkLabel(char_select_row, text="使用キャラ:",
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=MaterialColors.ON_SURFACE_VARIANT).pack(side="left", padx=(0, 6))

        self.char_select_combo = ctk.CTkOptionMenu(
            char_select_row, values=["（キャラ選択）"], height=36,
            font=ctk.CTkFont(size=14),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=4,
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
        concept_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=0, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT)
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

        # --- コンセプトプリセット行 ---
        preset_row = ctk.CTkFrame(concept_card, fg_color="transparent")
        preset_row.pack(fill="x", padx=20, pady=(6, 0))
        ctk.CTkLabel(
            preset_row, text="プリセット:",
            font=ctk.CTkFont(size=12), text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left")
        _cat_list = ["--"] + list(CONCEPT_PRESETS.keys())
        self.concept_cat_menu = ctk.CTkOptionMenu(
            preset_row, values=_cat_list, width=160, height=32,
            font=ctk.CTkFont(size=13),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=4,
            button_color=MaterialColors.PRIMARY,
            dropdown_fg_color=MaterialColors.SURFACE,
            text_color=MaterialColors.ON_SURFACE,
            command=self._on_concept_category_changed,
        )
        self.concept_cat_menu.set("--")
        self.concept_cat_menu.pack(side="left", padx=(6, 4))
        self.concept_name_menu = ctk.CTkOptionMenu(
            preset_row, values=["--"], width=200, height=32,
            font=ctk.CTkFont(size=13),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=4,
            button_color=MaterialColors.PRIMARY,
            dropdown_fg_color=MaterialColors.SURFACE,
            text_color=MaterialColors.ON_SURFACE,
            command=self._on_concept_preset_selected,
        )
        self.concept_name_menu.set("--")
        self.concept_name_menu.pack(side="left", padx=(0, 4))
        self.concept_shuffle_btn = ctk.CTkButton(
            preset_row, text="\U0001f3b2", width=32, height=32,
            font=ctk.CTkFont(size=16),
            fg_color=MaterialColors.SECONDARY_CONTAINER,
            text_color=MaterialColors.ON_SECONDARY_CONTAINER,
            hover_color=MaterialColors.PRIMARY, corner_radius=6,
            command=self._on_concept_shuffle,
        )
        self.concept_shuffle_btn.pack(side="left")
        self._last_concept_variation = ""

        self.concept_text = ctk.CTkTextbox(
            concept_card, height=120,
            font=ctk.CTkFont(size=16),
            fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST,
            text_color=MaterialColors.ON_SURFACE,
            corner_radius=4, border_width=1, border_color=MaterialColors.OUTLINE,
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
            placeholder_text_color="#3D3D3D",
            corner_radius=4, border_width=1, border_color=MaterialColors.OUTLINE
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
            corner_radius=4, border_width=1, border_color=MaterialColors.OUTLINE,
            wrap="word"
        )
        self.other_chars_text.pack(fill="x", padx=20, pady=(8, 16))
        self.other_chars_text.insert("1.0", "相手役の男性（顔なし）\nSD: 1boy, faceless_male")

        # ── 男性キャラ設定 ──
        male_char_frame = ctk.CTkFrame(concept_card, fg_color="transparent")
        male_char_frame.pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(male_char_frame, text="男性キャラ", font=ctk.CTkFont(family=FONT_JP, size=13, weight="bold")).pack(anchor="w", padx=4)

        male_row = ctk.CTkFrame(male_char_frame, fg_color="transparent")
        male_row.pack(fill="x", padx=4, pady=(4, 0))

        # プリセットドロップダウン
        self.male_preset_combo = ctk.CTkOptionMenu(
            male_row, values=list(MALE_PRESETS.keys()),
            width=160, height=32,
            font=ctk.CTkFont(family=FONT_JP, size=12),
            command=self._on_male_preset_changed,
        )
        self.male_preset_combo.pack(side="left", padx=(0, 8))
        self.male_preset_combo.set("おまかせ")

        # カスタム入力フィールド
        self.male_custom_field = ctk.CTkEntry(
            male_row, placeholder_text="自由入力: はげた小太りの中年 等",
            height=34, font=ctk.CTkFont(family=FONT_JP, size=13),
            fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST,
            text_color=MaterialColors.ON_SURFACE,
            placeholder_text_color="#3D3D3D",
            corner_radius=4, border_width=1, border_color=MaterialColors.OUTLINE,
        )
        self.male_custom_field.pack(side="left", fill="x", expand=True)

        # 男性 髪型・髪色・肌色
        male_detail_row = ctk.CTkFrame(male_char_frame, fg_color="transparent")
        male_detail_row.pack(fill="x", padx=4, pady=(4, 0))

        ctk.CTkLabel(male_detail_row, text="髪型", font=ctk.CTkFont(family=FONT_JP, size=12)).pack(side="left", padx=(0, 4))
        self.male_hair_style_combo = ctk.CTkOptionMenu(
            male_detail_row, values=list(MALE_HAIR_STYLE_OPTIONS.keys()),
            width=100, height=32, font=ctk.CTkFont(family=FONT_JP, size=12),
        )
        self.male_hair_style_combo.pack(side="left", padx=(0, 12))
        self.male_hair_style_combo.set("おまかせ")

        ctk.CTkLabel(male_detail_row, text="髪色", font=ctk.CTkFont(family=FONT_JP, size=12)).pack(side="left", padx=(0, 4))
        self.male_hair_color_combo = ctk.CTkOptionMenu(
            male_detail_row, values=list(MALE_HAIR_COLOR_OPTIONS.keys()),
            width=100, height=32, font=ctk.CTkFont(family=FONT_JP, size=12),
        )
        self.male_hair_color_combo.pack(side="left", padx=(0, 12))
        self.male_hair_color_combo.set("おまかせ")

        ctk.CTkLabel(male_detail_row, text="肌色", font=ctk.CTkFont(family=FONT_JP, size=12)).pack(side="left", padx=(0, 4))
        self.male_skin_color_combo = ctk.CTkOptionMenu(
            male_detail_row, values=list(MALE_SKIN_COLOR_OPTIONS.keys()),
            width=100, height=32, font=ctk.CTkFont(family=FONT_JP, size=12),
        )
        self.male_skin_color_combo.pack(side="left", padx=(0, 0))
        self.male_skin_color_combo.set("おまかせ")

        # ── シーン環境 ──
        env_frame = ctk.CTkFrame(concept_card, fg_color="transparent")
        env_frame.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(env_frame, text="シーン環境", font=ctk.CTkFont(family=FONT_JP, size=13, weight="bold")).pack(anchor="w", padx=4)

        env_row = ctk.CTkFrame(env_frame, fg_color="transparent")
        env_row.pack(fill="x", padx=4, pady=(4, 0))

        # 時間帯
        ctk.CTkLabel(env_row, text="時間帯", font=ctk.CTkFont(family=FONT_JP, size=12)).pack(side="left", padx=(0, 4))
        self.time_of_day_combo = ctk.CTkOptionMenu(
            env_row, values=list(TIME_OF_DAY_OPTIONS.keys()),
            width=100, height=32,
            font=ctk.CTkFont(family=FONT_JP, size=12),
        )
        self.time_of_day_combo.pack(side="left", padx=(0, 16))
        self.time_of_day_combo.set("おまかせ")

        # 場所タイプ
        ctk.CTkLabel(env_row, text="場所", font=ctk.CTkFont(family=FONT_JP, size=12)).pack(side="left", padx=(0, 4))
        self.location_type_combo = ctk.CTkOptionMenu(
            env_row, values=list(LOCATION_TYPE_OPTIONS.keys()),
            width=100, height=32,
            font=ctk.CTkFont(family=FONT_JP, size=12),
        )
        self.location_type_combo.pack(side="left")
        self.location_type_combo.set("おまかせ")

        # ══════════════════════════════════════════════════════════════
        # 4b. SDプロンプト設定（折りたたみ）
        # ══════════════════════════════════════════════════════════════
        sd_card = MaterialCard(
            content, title="SDプロンプト設定", variant="outlined",
            collapsible=True, start_collapsed=False
        )
        sd_card.pack(fill="x", pady=(0, 16))
        sd_content = sd_card.content_frame

        # --- クオリティタグ ---
        _quality_header = ctk.CTkFrame(sd_content, fg_color="transparent")
        _quality_header.pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            _quality_header, text="クオリティタグ",
            font=ctk.CTkFont(family=FONT_JP, size=13, weight="bold"),
            text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left")
        ctk.CTkLabel(
            _quality_header, text="（不要の場合は「カスタム」を選択し空欄のままにしてください）",
            font=ctk.CTkFont(family=FONT_JP, size=12),
            text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left", padx=(6, 0))

        quality_mode_row = ctk.CTkFrame(sd_content, fg_color="transparent")
        quality_mode_row.pack(fill="x", pady=(0, 4))
        self.sd_quality_mode_var = tk.StringVar(value="auto")
        ctk.CTkRadioButton(
            quality_mode_row, text="自動", variable=self.sd_quality_mode_var, value="auto",
            font=ctk.CTkFont(family=FONT_JP, size=12),
            command=self._on_sd_quality_mode_changed
        ).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(
            quality_mode_row, text="カスタム", variable=self.sd_quality_mode_var, value="manual",
            font=ctk.CTkFont(family=FONT_JP, size=12),
            command=self._on_sd_quality_mode_changed
        ).pack(side="left")

        self.sd_quality_custom_entry = ctk.CTkEntry(
            sd_content, height=36,
            font=ctk.CTkFont(size=13),
            fg_color=MaterialColors.SURFACE_CONTAINER,
            corner_radius=4, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT,
            text_color=MaterialColors.ON_SURFACE,
            placeholder_text="カスタムクオリティタグを入力…",
            placeholder_text_color="#3D3D3D",
        )
        # 自動モード初期値: QUALITY_POSITIVE_TAGS を表示して無効化
        self.sd_quality_custom_entry.insert(0, QUALITY_POSITIVE_TAGS)
        self.sd_quality_custom_entry.configure(state="disabled")
        self.sd_quality_custom_entry.pack(fill="x", pady=(0, 8))

        # 区切り線
        ctk.CTkFrame(sd_content, fg_color=MaterialColors.OUTLINE_VARIANT, height=1, corner_radius=0).pack(fill="x", pady=8)

        # --- プレフィックス ---
        _prefix_header = ctk.CTkFrame(sd_content, fg_color="transparent")
        _prefix_header.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            _prefix_header, text="プレフィックス（全シーン先頭に追加）",
            font=ctk.CTkFont(family=FONT_JP, size=13, weight="bold"),
            text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left")
        MaterialButton(
            _prefix_header, text="クリア", variant="text", size="small",
            command=lambda: (self.sd_prefix_text.delete("1.0", "end"))
        ).pack(side="right")
        self.sd_prefix_text = ctk.CTkTextbox(
            sd_content, height=100,
            font=ctk.CTkFont(size=13),
            fg_color=MaterialColors.SURFACE_CONTAINER,
            corner_radius=4, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT,
            text_color=MaterialColors.ON_SURFACE,
        )
        self.sd_prefix_text.pack(fill="x", pady=(0, 8))
        self.sd_prefix_text.bind("<KeyRelease>", lambda e: self._auto_resize_textbox(self.sd_prefix_text, 100, 1200))

        # --- サフィックス ---
        _suffix_header = ctk.CTkFrame(sd_content, fg_color="transparent")
        _suffix_header.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            _suffix_header, text="サフィックス（全シーン末尾に追加）",
            font=ctk.CTkFont(family=FONT_JP, size=13, weight="bold"),
            text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left")
        MaterialButton(
            _suffix_header, text="クリア", variant="text", size="small",
            command=lambda: (self.sd_suffix_text.delete("1.0", "end"))
        ).pack(side="right")
        self.sd_suffix_text = ctk.CTkTextbox(
            sd_content, height=100,
            font=ctk.CTkFont(size=13),
            fg_color=MaterialColors.SURFACE_CONTAINER,
            corner_radius=4, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT,
            text_color=MaterialColors.ON_SURFACE,
        )
        self.sd_suffix_text.pack(fill="x", pady=(0, 8))
        self.sd_suffix_text.bind("<KeyRelease>", lambda e: self._auto_resize_textbox(self.sd_suffix_text, 100, 1200))

        # 区切り線
        ctk.CTkFrame(sd_content, fg_color=MaterialColors.OUTLINE_VARIANT, height=1, corner_radius=0).pack(fill="x", pady=8)

        # --- PNG Info 読み取り ---
        ctk.CTkLabel(
            sd_content, text="画像から読み取り",
            font=ctk.CTkFont(family=FONT_JP, size=13, weight="bold"),
            text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(anchor="w", pady=(0, 4))

        # ドロップゾーン
        self.png_drop_frame = ctk.CTkFrame(
            sd_content,
            fg_color=MaterialColors.SURFACE_CONTAINER,
            corner_radius=8, border_width=2,
            border_color=MaterialColors.OUTLINE_VARIANT,
        )
        self.png_drop_frame.pack(fill="x", pady=(0, 4))

        # アイコン＋ヒントテキストを横並び（pack expand で上下中央）
        _drop_row = ctk.CTkFrame(self.png_drop_frame, fg_color="transparent")
        _drop_row.pack(expand=True, pady=16)
        self.png_drop_icon_label = ctk.CTkLabel(
            _drop_row, text=Icons.IMAGE,
            font=ctk.CTkFont(family=FONT_ICON, size=20),
            text_color=MaterialColors.ON_SURFACE_VARIANT,
        )
        self.png_drop_icon_label.pack(side="left", padx=(0, 8))
        self.png_drop_hint_label = ctk.CTkLabel(
            _drop_row,
            text="ここに画像をドロップ、またはクリックして選択" if WINDND_AVAILABLE else "クリックして画像を選択",
            font=ctk.CTkFont(family=FONT_JP, size=12),
            text_color=MaterialColors.ON_SURFACE_VARIANT,
        )
        self.png_drop_hint_label.pack(side="left")
        self.png_filename_label = ctk.CTkLabel(
            _drop_row, text="",
            font=ctk.CTkFont(family=FONT_JP, size=11),
            text_color=MaterialColors.PRIMARY,
        )
        self.png_filename_label.pack(side="left", padx=(12, 0))

        # ドロップゾーン全体をクリック可能に
        for w in (self.png_drop_frame, _drop_row, self.png_drop_icon_label, self.png_drop_hint_label, self.png_filename_label):
            w.configure(cursor="hand2")
            w.bind("<Button-1>", lambda e: self._on_png_info_load())

        self.png_preview_text = ctk.CTkTextbox(
            sd_content, height=120,
            font=ctk.CTkFont(size=12),
            fg_color=MaterialColors.SURFACE_CONTAINER,
            corner_radius=4, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT,
            text_color=MaterialColors.ON_SURFACE,
            state="disabled"
        )
        self.png_preview_text.pack(fill="x", pady=(0, 4))

        png_apply_row = ctk.CTkFrame(sd_content, fg_color="transparent")
        png_apply_row.pack(fill="x", pady=(0, 4))
        MaterialButton(
            png_apply_row, text="プレフィックスに適用", variant="filled_tonal", size="small",
            command=self._apply_png_to_prefix
        ).pack(side="left", padx=(0, 8))
        MaterialButton(
            png_apply_row, text="サフィックスに適用", variant="filled_tonal", size="small",
            command=self._apply_png_to_suffix
        ).pack(side="left")

        # ══════════════════════════════════════════════════════════════
        # 5. 生成設定
        # ══════════════════════════════════════════════════════════════
        settings_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=0, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT)
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
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=4,
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
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=4,
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
        self._cost_preview_label = self.cost_preview_label  # プレゼンモード用参照
        self.cost_preview_label.pack(anchor="w", padx=20, pady=(4, 12))

        # ══════════════════════════════════════════════════════════════
        # 6. 生成セクション
        # ══════════════════════════════════════════════════════════════
        generate_section = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=0,
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
        self.stop_btn.pack(side="left", padx=(0, 8))
        self.stop_btn.configure(state="disabled")
        add_tooltip(self.stop_btn, "生成を停止 (Esc)")

        self.export_btn = MaterialButton(
            btn_row, text="再エクスポート", variant="filled_tonal", size="large",
            width=120, command=self.open_export_dialog
        )
        self.export_btn.pack(side="left")
        self.export_btn.configure(state="disabled")
        add_tooltip(self.export_btn, "別形式で再エクスポート")

        # ══════════════════════════════════════════════════════════════
        # 7. コスト＆ログ（プレゼン時は非表示）
        # ══════════════════════════════════════════════════════════════
        cost_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=0, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT)
        self._cost_card = cost_card  # プレゼンモード用参照
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

        log_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=0, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT)
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

    # --- コンセプトプリセットハンドラ ---
    def _on_concept_category_changed(self, cat: str):
        """カテゴリ変更→コンセプトドロップダウン更新"""
        if cat == "--" or cat not in CONCEPT_PRESETS:
            self.concept_name_menu.configure(values=["--"])
            self.concept_name_menu.set("--")
            return
        names = list(CONCEPT_PRESETS[cat].keys())
        self.concept_name_menu.configure(values=["--"] + names)
        self.concept_name_menu.set("--")

    def _on_concept_preset_selected(self, name: str):
        """プリセット選択→テキスト挿入+テーマ自動設定"""
        cat = self.concept_cat_menu.get()
        if name == "--" or cat == "--":
            return
        preset = CONCEPT_PRESETS.get(cat, {}).get(name)
        if not preset:
            return
        variation = random.choice(preset["variations"])
        self._last_concept_variation = variation
        self._set_concept_text(variation)
        # テーマ自動設定
        theme_key = preset.get("theme", "")
        if theme_key and theme_key in _THEME_KEY_TO_JP:
            self.theme_combo.set(_THEME_KEY_TO_JP[theme_key])

    def _on_concept_shuffle(self):
        """別バリエーション再抽選（同じものを避ける）"""
        cat = self.concept_cat_menu.get()
        name = self.concept_name_menu.get()
        if cat == "--" or name == "--":
            return
        preset = CONCEPT_PRESETS.get(cat, {}).get(name)
        if not preset:
            return
        variations = preset["variations"]
        if len(variations) <= 1:
            self._set_concept_text(variations[0])
            return
        candidates = [v for v in variations if v != self._last_concept_variation]
        if not candidates:
            candidates = variations
        variation = random.choice(candidates)
        self._last_concept_variation = variation
        self._set_concept_text(variation)

    def _on_male_preset_changed(self, value):
        """男性プリセット選択時にカスタム入力をクリア"""
        if value != "おまかせ":
            self.male_custom_field.delete(0, "end")

    def get_male_tags(self) -> str:
        """現在のGUI状態から男性SDタグ文字列を返す"""
        custom = self.male_custom_field.get().strip() if hasattr(self, 'male_custom_field') else ""
        if custom:
            base = parse_male_description(custom)
        else:
            preset_key = self.male_preset_combo.get() if hasattr(self, 'male_preset_combo') else "おまかせ"
            base = MALE_PRESETS.get(preset_key, "")

        # 髪型・髪色・肌色の追加タグ
        extra = []
        if hasattr(self, 'male_hair_style_combo'):
            v = MALE_HAIR_STYLE_OPTIONS.get(self.male_hair_style_combo.get(), "")
            if v:
                extra.append(v)
        if hasattr(self, 'male_hair_color_combo'):
            v = MALE_HAIR_COLOR_OPTIONS.get(self.male_hair_color_combo.get(), "")
            if v:
                extra.append(v)
        if hasattr(self, 'male_skin_color_combo'):
            v = MALE_SKIN_COLOR_OPTIONS.get(self.male_skin_color_combo.get(), "")
            if v:
                extra.append(v)

        if extra:
            parts = [t.strip() for t in base.split(",") if t.strip()] if base else []
            parts.extend(extra)
            return ", ".join(parts)
        return base

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
        # work_type is always "二次創作" (original character creation removed)
        if self.config_data.get("story_structure"):
            ss = self.config_data["story_structure"]
            self.prologue_slider.set(ss.get("prologue", 10))
            self.epilogue_slider.set(ss.get("epilogue", 10))
            preset_name = ss.get("preset", "標準バランス (10/80/10)")
            if preset_name in STRUCTURE_PRESETS:
                self.structure_preset.set(preset_name)
            self._update_structure_bar()

        # 男性キャラ・シーン環境の復元
        if "male_preset" in self.config_data and hasattr(self, 'male_preset_combo'):
            self.male_preset_combo.set(self.config_data["male_preset"])
        if "male_custom" in self.config_data and hasattr(self, 'male_custom_field'):
            _mc = self.config_data["male_custom"]
            if _mc:  # 値がある時だけ操作（空の場合はプレースホルダー維持）
                self.male_custom_field.delete(0, "end")
                self.male_custom_field.insert(0, _mc)
        if "male_hair_style" in self.config_data and hasattr(self, 'male_hair_style_combo'):
            self.male_hair_style_combo.set(self.config_data["male_hair_style"])
        if "male_hair_color" in self.config_data and hasattr(self, 'male_hair_color_combo'):
            self.male_hair_color_combo.set(self.config_data["male_hair_color"])
        if "male_skin_color" in self.config_data and hasattr(self, 'male_skin_color_combo'):
            self.male_skin_color_combo.set(self.config_data["male_skin_color"])
        if "time_of_day" in self.config_data and hasattr(self, 'time_of_day_combo'):
            self.time_of_day_combo.set(self.config_data["time_of_day"])
        if "location_type" in self.config_data and hasattr(self, 'location_type_combo'):
            self.location_type_combo.set(self.config_data["location_type"])

        # SD設定の復元
        if "sd_quality_mode" in self.config_data:
            self.sd_quality_mode_var.set(self.config_data["sd_quality_mode"])
            self._on_sd_quality_mode_changed()
        if self.config_data.get("sd_quality_custom"):
            self.sd_quality_custom_entry.configure(state="normal")
            self.sd_quality_custom_entry.delete(0, "end")
            self.sd_quality_custom_entry.insert(0, self.config_data["sd_quality_custom"])
            if self.sd_quality_mode_var.get() == "auto":
                self.sd_quality_custom_entry.configure(state="disabled")
        if self.config_data.get("sd_prefix_tags"):
            self.sd_prefix_text.delete("1.0", "end")
            self.sd_prefix_text.insert("1.0", self.config_data["sd_prefix_tags"])
            self._auto_resize_textbox(self.sd_prefix_text, 100, 1200)
        if self.config_data.get("sd_suffix_tags"):
            self.sd_suffix_text.delete("1.0", "end")
            self.sd_suffix_text.insert("1.0", self.config_data["sd_suffix_tags"])
            self._auto_resize_textbox(self.sd_suffix_text, 100, 1200)

        # 初期コスト予測を表示
        self.after(100, self.update_cost_preview)

    # --- SDプロンプト テキスト欄動的リサイズ ---
    @staticmethod
    def _auto_resize_textbox(textbox, min_h: int = 100, max_h: int = 1200):
        """テキスト内容に応じてCTkTextboxの高さを自動調整（折り返し考慮）"""
        try:
            content = textbox.get("1.0", "end-1c")
            if not content.strip():
                textbox.configure(height=min_h)
                return
            # ウィジェット幅から1行あたり文字数を推定
            w_px = textbox.winfo_width()
            if w_px < 50:
                w_px = 500  # 初期化前のフォールバック
            chars_per_line = max(1, w_px // 8)
            # 各行の折り返しを考慮した表示行数を計算
            visual_lines = 0
            for line in content.split("\n"):
                if len(line) <= chars_per_line:
                    visual_lines += 1
                else:
                    visual_lines += (len(line) + chars_per_line - 1) // chars_per_line
            # 1行≒20px + 上下パディング20px
            needed = visual_lines * 20 + 20
            new_h = max(min_h, min(max_h, needed))
            textbox.configure(height=new_h)
        except Exception:
            pass

    # --- SDプロンプト設定コールバック ---
    def _on_sd_quality_mode_changed(self):
        """auto/manual切替でカスタム入力欄のstate変更"""
        if self.sd_quality_mode_var.get() == "manual":
            self.sd_quality_custom_entry.configure(state="normal")
            # 自動テキストが残っていたら消去してユーザー入力に備える
            if self.sd_quality_custom_entry.get() == QUALITY_POSITIVE_TAGS:
                self.sd_quality_custom_entry.delete(0, "end")
        else:
            # カスタム→自動: 空欄なら自動タグを再表示
            self.sd_quality_custom_entry.configure(state="normal")
            current = self.sd_quality_custom_entry.get().strip()
            if not current:
                self.sd_quality_custom_entry.delete(0, "end")
                self.sd_quality_custom_entry.insert(0, QUALITY_POSITIVE_TAGS)
            self.sd_quality_custom_entry.configure(state="disabled")

    def _setup_png_drop(self):
        """windndによるドラッグ&ドロップのフック（ウィンドウ表示後に呼ぶ）"""
        if not WINDND_AVAILABLE:
            return
        try:
            # force_unicode=True: DragQueryFileW使用でUnicode strを直接受け取る
            # （デフォルトのANSI版だと日本語パスがCP932 bytesになり文字化けする）
            windnd.hook_dropfiles(self.png_drop_frame, func=self._on_png_files_dropped, force_unicode=True)
        except Exception as e:
            log_message(f"ドラッグ&ドロップ初期化失敗: {e}")

    def _on_png_files_dropped(self, file_list):
        """windndからのドロップコールバック（force_unicode=Trueでstr型リスト）"""
        _IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif")
        for f in file_list:
            # force_unicode=True → str型、万が一bytes時はシステムエンコーディングで復元
            if isinstance(f, bytes):
                import locale
                for enc in (locale.getpreferredencoding(False), "utf-8"):
                    try:
                        path = f.decode(enc)
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
                else:
                    path = f.decode("utf-8", errors="replace")
            else:
                path = str(f)
            if path.lower().endswith(_IMAGE_EXTS):
                self._load_png_info(path)
                return
        # 画像ファイルが見つからない場合
        if hasattr(self, 'snackbar'):
            self.snackbar.show("対応する画像ファイルが見つかりません", type="error")

    def _on_png_info_load(self):
        """ファイルダイアログから画像選択→パース→プレビュー表示"""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.webp"), ("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg"), ("WebP", "*.webp"), ("全てのファイル", "*.*")]
        )
        if not path:
            return
        self._load_png_info(path)

    def _load_png_info(self, path: str):
        """画像ファイルからSD情報を読み取りプレビューに表示（共通処理）"""
        result = parse_png_info(path)
        self._png_info_result = result  # 後から参照用に保存
        filename = Path(path).name
        self.png_filename_label.configure(text=filename)
        # ドロップゾーンのヒントを更新
        self.png_drop_hint_label.configure(
            text="別の画像をドロップで差替え" if WINDND_AVAILABLE else "クリックで別の画像を選択"
        )
        self.png_preview_text.configure(state="normal")
        self.png_preview_text.delete("1.0", "end")
        if "error" in result:
            self.png_preview_text.insert("1.0", result["error"])
            self.png_drop_frame.configure(border_color="#B3261E")  # error red
        else:
            positive = result.get("positive", "")
            raw = result.get("raw", "")
            log_message(f"PNG Info positive[:{min(80,len(positive))}]: {repr(positive[:80])}")
            if raw != positive:
                log_message(f"PNG Info raw[:{min(80,len(raw))}]: {repr(raw[:80])}")
            self.png_preview_text.insert("1.0", positive if positive else "(情報なし)")
            self.png_drop_frame.configure(border_color=MaterialColors.PRIMARY)  # success
        self.png_preview_text.configure(state="disabled")
        # 内容に応じて高さを自動調整
        self._auto_resize_textbox(self.png_preview_text, min_h=120, max_h=1200)

    def _apply_png_to_prefix(self):
        """PNG Infoのpositiveプロンプトをプレフィックスに適用"""
        result = getattr(self, '_png_info_result', None)
        if not result or "error" in result:
            return
        content = result.get("positive", "").strip()
        if not content:
            return
        existing = self.sd_prefix_text.get("1.0", "end-1c").strip()
        if existing:
            self.sd_prefix_text.delete("1.0", "end")
            self.sd_prefix_text.insert("1.0", f"{existing}, {content}")
        else:
            self.sd_prefix_text.delete("1.0", "end")
            self.sd_prefix_text.insert("1.0", content)
        self._auto_resize_textbox(self.sd_prefix_text, min_h=100, max_h=1200)
        if hasattr(self, 'snackbar'):
            self.snackbar.show("プレフィックスに適用しました", type="success")

    def _apply_png_to_suffix(self):
        """PNG Infoのpositiveプロンプトをサフィックスに適用"""
        result = getattr(self, '_png_info_result', None)
        if not result or "error" in result:
            return
        content = result.get("positive", "").strip()
        if not content:
            return
        existing = self.sd_suffix_text.get("1.0", "end-1c").strip()
        if existing:
            self.sd_suffix_text.delete("1.0", "end")
            self.sd_suffix_text.insert("1.0", f"{existing}, {content}")
        else:
            self.sd_suffix_text.delete("1.0", "end")
            self.sd_suffix_text.insert("1.0", content)
        self._auto_resize_textbox(self.sd_suffix_text, min_h=100, max_h=1200)
        if hasattr(self, 'snackbar'):
            self.snackbar.show("サフィックスに適用しました", type="success")

    def update_cost_preview(self, event=None):
        """シーン数に基づいてコスト予測を更新"""
        try:
            num_scenes = int(self.scenes_entry.get())
            if num_scenes < 1:
                num_scenes = 1
            elif num_scenes > 500:
                num_scenes = 500

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
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=4,
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
            "work_type": "二次創作",
            "story_structure": {
                "prologue": int(round(self.prologue_slider.get())),
                "epilogue": int(round(self.epilogue_slider.get())),
                "preset": self.structure_preset.get(),
            },
            "concept_preset_category": self.concept_cat_menu.get(),
            "concept_preset_name": self.concept_name_menu.get(),
            "male_preset": self.male_preset_combo.get() if hasattr(self, 'male_preset_combo') else "おまかせ",
            "male_custom": self.male_custom_field.get() if hasattr(self, 'male_custom_field') else "",
            "male_hair_style": self.male_hair_style_combo.get() if hasattr(self, 'male_hair_style_combo') else "おまかせ",
            "male_hair_color": self.male_hair_color_combo.get() if hasattr(self, 'male_hair_color_combo') else "おまかせ",
            "male_skin_color": self.male_skin_color_combo.get() if hasattr(self, 'male_skin_color_combo') else "おまかせ",
            "time_of_day": self.time_of_day_combo.get() if hasattr(self, 'time_of_day_combo') else "おまかせ",
            "location_type": self.location_type_combo.get() if hasattr(self, 'location_type_combo') else "おまかせ",
            "sd_quality_mode": self.sd_quality_mode_var.get() if hasattr(self, 'sd_quality_mode_var') else "auto",
            "sd_quality_custom": (self.sd_quality_custom_entry.get() if self.sd_quality_mode_var.get() == "manual" else "") if hasattr(self, 'sd_quality_custom_entry') else "",
            "sd_prefix_tags": self.sd_prefix_text.get("1.0", "end-1c").strip() if hasattr(self, 'sd_prefix_text') else "",
            "sd_suffix_tags": self.sd_suffix_text.get("1.0", "end-1c").strip() if hasattr(self, 'sd_suffix_text') else "",
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
            "work_title": self._work_title_val,
            "char_name": self._char_name_val,
            "work_type": "二次創作",
            "male_preset": self.male_preset_combo.get() if hasattr(self, 'male_preset_combo') else "おまかせ",
            "male_custom": self.male_custom_field.get() if hasattr(self, 'male_custom_field') else "",
            "male_hair_style": self.male_hair_style_combo.get() if hasattr(self, 'male_hair_style_combo') else "おまかせ",
            "male_hair_color": self.male_hair_color_combo.get() if hasattr(self, 'male_hair_color_combo') else "おまかせ",
            "male_skin_color": self.male_skin_color_combo.get() if hasattr(self, 'male_skin_color_combo') else "おまかせ",
            "time_of_day": self.time_of_day_combo.get() if hasattr(self, 'time_of_day_combo') else "おまかせ",
            "location_type": self.location_type_combo.get() if hasattr(self, 'location_type_combo') else "おまかせ",
            "sd_quality_mode": self.sd_quality_mode_var.get() if hasattr(self, 'sd_quality_mode_var') else "auto",
            "sd_quality_custom": (self.sd_quality_custom_entry.get() if self.sd_quality_mode_var.get() == "manual" else "") if hasattr(self, 'sd_quality_custom_entry') else "",
            "sd_prefix_tags": self.sd_prefix_text.get("1.0", "end-1c").strip() if hasattr(self, 'sd_prefix_text') else "",
            "sd_suffix_tags": self.sd_suffix_text.get("1.0", "end-1c").strip() if hasattr(self, 'sd_suffix_text') else "",
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
            self._work_title_val = config["work_title"]
        if config.get("char_name"):
            self._char_name_val = config["char_name"]
        if config.get("story_structure"):
            ss = config["story_structure"]
            self.prologue_slider.set(ss.get("prologue", 10))
            self.epilogue_slider.set(ss.get("epilogue", 10))
            preset_name = ss.get("preset", "標準バランス (10/80/10)")
            if preset_name in STRUCTURE_PRESETS:
                self.structure_preset.set(preset_name)
            self._update_structure_bar()
        # コンセプトプリセット復元
        if config.get("concept_preset_category"):
            cat = config["concept_preset_category"]
            self.concept_cat_menu.set(cat)
            self._on_concept_category_changed(cat)
            if config.get("concept_preset_name"):
                self.concept_name_menu.set(config["concept_preset_name"])
        # 男性キャラ・シーン環境の復元
        if "male_preset" in config and hasattr(self, 'male_preset_combo'):
            self.male_preset_combo.set(config["male_preset"])
        if "male_custom" in config and hasattr(self, 'male_custom_field'):
            _mc = config["male_custom"]
            if _mc:  # 値がある時だけ操作（空の場合はプレースホルダー維持）
                self.male_custom_field.delete(0, "end")
                self.male_custom_field.insert(0, _mc)
        if "male_hair_style" in config and hasattr(self, 'male_hair_style_combo'):
            self.male_hair_style_combo.set(config["male_hair_style"])
        if "male_hair_color" in config and hasattr(self, 'male_hair_color_combo'):
            self.male_hair_color_combo.set(config["male_hair_color"])
        if "male_skin_color" in config and hasattr(self, 'male_skin_color_combo'):
            self.male_skin_color_combo.set(config["male_skin_color"])
        if "time_of_day" in config and hasattr(self, 'time_of_day_combo'):
            self.time_of_day_combo.set(config["time_of_day"])
        if "location_type" in config and hasattr(self, 'location_type_combo'):
            self.location_type_combo.set(config["location_type"])
        # SD設定の復元
        if "sd_quality_mode" in config and hasattr(self, 'sd_quality_mode_var'):
            self.sd_quality_mode_var.set(config["sd_quality_mode"])
            self._on_sd_quality_mode_changed()
        if config.get("sd_quality_custom") and hasattr(self, 'sd_quality_custom_entry'):
            self.sd_quality_custom_entry.configure(state="normal")
            self.sd_quality_custom_entry.delete(0, "end")
            self.sd_quality_custom_entry.insert(0, config["sd_quality_custom"])
            if self.sd_quality_mode_var.get() == "auto":
                self.sd_quality_custom_entry.configure(state="disabled")
        if config.get("sd_prefix_tags") and hasattr(self, 'sd_prefix_text'):
            self.sd_prefix_text.delete("1.0", "end")
            self.sd_prefix_text.insert("1.0", config["sd_prefix_tags"])
            self._auto_resize_textbox(self.sd_prefix_text, 100, 1200)
        if config.get("sd_suffix_tags") and hasattr(self, 'sd_suffix_text'):
            self.sd_suffix_text.delete("1.0", "end")
            self.sd_suffix_text.insert("1.0", config["sd_suffix_tags"])
            self._auto_resize_textbox(self.sd_suffix_text, 100, 1200)
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
            if num_scenes < 1 or num_scenes > 500:
                raise ValueError()
        except (ValueError, TypeError):
            self.snackbar.show("シーン数は1〜500の整数で", type="error")
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

            # v7.0: 男性設定・時間帯・場所タイプをGUIから取得
            _male_tags = self.get_male_tags() if hasattr(self, 'get_male_tags') else ""
            _time_of_day_jp = self.time_of_day_combo.get() if hasattr(self, 'time_of_day_combo') else "おまかせ"
            _time_tags = TIME_OF_DAY_OPTIONS.get(_time_of_day_jp, "")
            _location_jp = self.location_type_combo.get() if hasattr(self, 'location_type_combo') else "おまかせ"
            _location_type = LOCATION_TYPE_OPTIONS.get(_location_jp, "")

            # v7.3: 男性キャラの日本語説明を取得（LLMプロンプト用）
            _male_desc_jp = ""
            if hasattr(self, 'male_custom_field'):
                _custom = self.male_custom_field.get().strip()
                if _custom:
                    _male_desc_jp = _custom
            if not _male_desc_jp and hasattr(self, 'male_preset_combo'):
                _preset_key = self.male_preset_combo.get()
                if _preset_key != "おまかせ":
                    _male_desc_jp = _preset_key
            # 髪型・髪色・肌色の日本語を追記
            _male_detail_parts = []
            for _attr, _lbl in [
                ('male_hair_style_combo', ''),
                ('male_hair_color_combo', ''),
                ('male_skin_color_combo', '肌:'),
            ]:
                if hasattr(self, _attr):
                    _v = getattr(self, _attr).get()
                    if _v and _v != "おまかせ" and _v != "普通":
                        _male_detail_parts.append(f"{_lbl}{_v}")
            if _male_detail_parts:
                _detail = "、".join(_male_detail_parts)
                _male_desc_jp = f"{_male_desc_jp}、{_detail}" if _male_desc_jp else _detail

            # v7.4: SDプロンプト設定をGUIから取得
            _sd_quality_mode = self.sd_quality_mode_var.get() if hasattr(self, 'sd_quality_mode_var') else "auto"
            _sd_quality_custom = ""
            if _sd_quality_mode == "manual" and hasattr(self, 'sd_quality_custom_entry'):
                _sd_quality_custom = self.sd_quality_custom_entry.get().strip()
                if not _sd_quality_custom:
                    _sd_quality_custom = QUALITY_TAGS_DISABLED  # 空欄→quality tags無し
            _sd_prefix = self.sd_prefix_text.get("1.0", "end-1c").strip().replace("\n", ", ").replace(", , ", ", ") if hasattr(self, 'sd_prefix_text') else ""
            _sd_suffix = self.sd_suffix_text.get("1.0", "end-1c").strip().replace("\n", ", ").replace(", , ", ", ") if hasattr(self, 'sd_suffix_text') else ""

            results, cost_tracker, pipeline_metadata = generate_pipeline(
                api_key, concept, full_characters, num_scenes, theme, callback,
                story_structure=story_structure,
                male_tags=_male_tags, time_tags=_time_tags, location_type=_location_type,
                male_description=_male_desc_jp,
                sd_quality_tags=_sd_quality_custom,
                sd_prefix_tags=_sd_prefix,
                sd_suffix_tags=_sd_suffix,
            )

            if self.stop_requested:
                self.after(0, lambda: self.on_stopped())
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = EXPORTS_DIR / f"script_{timestamp}.csv"
            json_path = EXPORTS_DIR / f"script_{timestamp}.json"
            xlsx_path = EXPORTS_DIR / f"script_{timestamp}.xlsx"
            sd_path = EXPORTS_DIR / f"sd_prompts_{timestamp}.txt"
            wc_path = EXPORTS_DIR / f"wildcard_{timestamp}.txt"
            dlg_path = EXPORTS_DIR / f"dialogue_{timestamp}.txt"

            export_csv(results, csv_path)
            export_json(results, json_path, metadata=pipeline_metadata)
            export_sd_prompts(results, sd_path)
            export_wildcard(results, wc_path,
                           male_tags=_male_tags, time_tags=_time_tags,
                           location_type=_location_type)
            export_dialogue_list(results, dlg_path)

            # Excel出力（openpyxlがある場合）
            excel_ok = export_excel(results, xlsx_path)

            self.after(0, lambda: self.on_complete(results, cost_tracker, csv_path, json_path, xlsx_path if excel_ok else None, pipeline_metadata))

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

    def on_complete(self, results, cost_tracker, csv_path, json_path, xlsx_path=None, metadata=None):
        self.reset_buttons()
        self.progress.set(1)
        self.last_results = results  # 再エクスポート用に保持
        self.last_metadata = metadata  # メタデータも保持

        self.cost_label.configure(text=cost_tracker.summary())
        self.update_status(f"[OK]完了! {len(results)}シーン生成")
        self.log(f"[FILE]CSV: {csv_path}")
        self.log(f"[FILE]JSON: {json_path}")
        if xlsx_path:
            self.log(f"[STAT]Excel: {xlsx_path}（折り返し表示対応）")
        self.log(f"[COST]{cost_tracker.summary()}")
        self.snackbar.show(f"{len(results)}シーン生成完了!", type="success")

        # 再エクスポートボタン有効化
        self.export_btn.configure(state="normal")

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

    def open_export_dialog(self):
        """マルチフォーマットエクスポートダイアログを開く"""
        meta = getattr(self, "last_metadata", None)
        if self.last_results:
            ExportDialog(self, self.last_results, metadata=meta)
        else:
            # last_results が無い場合でもJSONインポートでエクスポート可能
            ExportDialog(self, [], metadata=meta)

    def toggle_presentation_mode(self):
        """Ctrl+Shift+P: APIキー・コスト表示を切替"""
        self._presentation_mode = not self._presentation_mode
        if self._presentation_mode:
            self._api_card.pack_forget()
            self._cost_card.pack_forget()
            self._cost_preview_label.pack_forget()
            self.snackbar.show("プレゼンモード ON（Ctrl+Shift+Pで解除）", type="info")
        else:
            # api_card: contentフレームの先頭に復元
            content = self._api_card.master
            visible = content.pack_slaves()
            if visible:
                self._api_card.pack(fill="x", pady=(0, 16), before=visible[0])
            else:
                self._api_card.pack(fill="x", pady=(0, 16))
            # cost_card: contentフレームの末尾に復元
            self._cost_card.pack(fill="x", pady=(0, 16))
            # cost_preview_label: settings_card内の末尾に復元
            self._cost_preview_label.pack(anchor="w", padx=20, pady=(4, 12))
            self.snackbar.show("プレゼンモード OFF", type="info")

    def _ensure_placeholders(self):
        """CTkEntryのプレースホルダーが初期化後に確実に表示されるようにする"""
        for entry in [
            getattr(self, 'male_custom_field', None),
        ]:
            if entry is not None and not entry.get():
                try:
                    entry._activate_placeholder()
                except Exception:
                    pass

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

        # Update card title with count
        count = len(self._all_presets)
        if hasattr(self, '_preset_card'):
            self._preset_card.title_label.configure(text=f"二次創作・プリセットキャラ一覧（{count}体収録）")

        # Show all characters immediately
        if hasattr(self, '_category_chips') and self._category_chips:
            self._on_category_chip_click("全て")

    def on_preset_selected(self, choice: str):
        """プリセット選択時（後方互換）"""
        pass

    def load_preset_action(self):
        """プリセット読み込み（後方互換）"""
        pass

    # ======== Preset Tab Methods ========

    def _build_preset_tab(self, parent):
        """プリセットタブUIを構築"""
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
            corner_radius=0, height=56,
            border_width=1, border_color=MaterialColors.OUTLINE_VARIANT,
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

        accent_bar = ctk.CTkFrame(card, fg_color=accent, width=4, corner_radius=0)
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


    def _load_preset_direct(self, preset_info):
        """ワンクリックでプリセット読み込み"""
        char_id = preset_info["char_id"]
        try:
            bible, _ = load_preset_character(char_id, callback=lambda msg: self.log(msg))
            self.refresh_char_list()
            name = bible.get("character_name", char_id)
            work = preset_info.get("work_title", "")
            self._work_title_val = work
            self._char_name_val = name
            self.snackbar.show(f"{name}を読み込みました", type="success")
        except Exception as e:
            self.snackbar.show(f"読み込みエラー: {e}", type="error")

    # ======== Custom Character Tab Methods ========

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

        # === Template Quick Start (32種) ===
        tmpl_label = ctk.CTkLabel(custom_scroll, text="テンプレート（ワンクリック雛形）— FANZA売れ筋32種",
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
            # 異種族系
            "サキュバス": {"age": "エルフ・長命種", "archetype": "サキュバス系", "first_person": "私",
                         "speech": "タメ口", "hair_color": "紫髪", "hair_style": "ロングウェーブ",
                         "body": "グラマー", "chest": "巨乳（F以上）", "clothing": "私服（ギャル系）", "shyness": 1},
            "獣耳メイド": {"age": "JD（女子大生）", "archetype": "妹系・甘えん坊", "first_person": "私",
                          "speech": "丁寧語", "hair_color": "白髪", "hair_style": "ロングストレート",
                          "body": "小柄・華奢", "chest": "普通（C）", "clothing": "メイド服", "shyness": 4},
            "ダークエルフ": {"age": "エルフ・長命種", "archetype": "クーデレ", "first_person": "私",
                           "speech": "古風・時代劇調", "hair_color": "白髪", "hair_style": "ロングストレート",
                           "body": "スレンダー", "chest": "大きめ（D-E）", "clothing": "鎧・アーマー", "shyness": 2},
            "天使堕ち": {"age": "エルフ・長命種", "archetype": "天然・ドジっ子", "first_person": "わたくし",
                        "speech": "丁寧語", "hair_color": "金髪", "hair_style": "ロングストレート",
                        "body": "スレンダー", "chest": "普通（C）", "clothing": "ドレス", "shyness": 5},
            # シチュ特化
            "催眠JK": {"age": "JK（女子高生）", "archetype": "真面目・優等生", "first_person": "私",
                      "speech": "丁寧語", "hair_color": "黒髪", "hair_style": "ロングストレート",
                      "body": "普通", "chest": "大きめ（D-E）", "clothing": "制服（セーラー服）", "shyness": 5},
            "女騎士": {"age": "OL（20代）", "archetype": "真面目・優等生", "first_person": "私",
                      "speech": "古風・時代劇調", "hair_color": "金髪", "hair_style": "ポニーテール",
                      "body": "筋肉質", "chest": "大きめ（D-E）", "clothing": "鎧・アーマー", "shyness": 4},
            "陰キャ同級生": {"age": "JK（女子高生）", "archetype": "陰キャ・オタク", "first_person": "私",
                           "speech": "タメ口", "hair_color": "黒髪", "hair_style": "三つ編み",
                           "body": "小柄・華奢", "chest": "控えめ（A-B）", "clothing": "制服（ブレザー）", "shyness": 5},
            "配信者": {"age": "JD（女子大生）", "archetype": "陰キャ・オタク", "first_person": "私",
                      "speech": "タメ口", "hair_color": "ピンク髪", "hair_style": "ツインテール",
                      "body": "普通", "chest": "普通（C）", "clothing": "パジャマ・部屋着", "shyness": 3},
            # 年齢差系
            "女上司": {"age": "OL（20代）", "archetype": "お姉さん系", "first_person": "私",
                      "speech": "敬語（ビジネス）", "hair_color": "黒髪", "hair_style": "ボブカット",
                      "body": "スレンダー", "chest": "大きめ（D-E）", "clothing": "スーツ", "shyness": 2},
            "ママ友": {"age": "人妻", "archetype": "天然・ドジっ子", "first_person": "私",
                      "speech": "丁寧語", "hair_color": "茶髪", "hair_style": "セミロング",
                      "body": "グラマー", "chest": "巨乳（F以上）", "clothing": "私服（清楚系）", "shyness": 3},
            "若妻先生": {"age": "OL（20代）", "archetype": "大和撫子", "first_person": "私",
                        "speech": "丁寧語", "hair_color": "茶髪", "hair_style": "ポニーテール",
                        "body": "普通", "chest": "大きめ（D-E）", "clothing": "スーツ", "shyness": 4},
            "寮母さん": {"age": "お姉さん（30代）", "archetype": "お姉さん系", "first_person": "私",
                        "speech": "丁寧語", "hair_color": "黒髪", "hair_style": "ロングストレート",
                        "body": "グラマー", "chest": "巨乳（F以上）", "clothing": "エプロン", "shyness": 3},
        }
        self._custom_templates = templates

        # カテゴリ別テンプレートグリッド (8行×4列)
        tmpl_categories = [
            ("学園系", ["JKツンデレ", "ギャルJK", "地味子", "委員長"]),
            ("純情系", ["甘え妹", "後輩マネ", "メイドさん", "巫女さん"]),
            ("年上系", ["大人クール", "女教師", "ナース", "未亡人"]),
            ("個性派", ["お嬢様", "エルフ姫", "褐色スポーツ", "バニーガール"]),
            ("NTR/人妻", ["NTR彼女", "人妻さん", "義母さん", "メスガキ"]),
            ("異種族系", ["サキュバス", "獣耳メイド", "ダークエルフ", "天使堕ち"]),
            ("シチュ特化", ["催眠JK", "女騎士", "陰キャ同級生", "配信者"]),
            ("年齢差系", ["女上司", "ママ友", "若妻先生", "寮母さん"]),
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
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=4,
            text_color=MaterialColors.ON_SURFACE,
            placeholder_text_color="#3D3D3D",
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

        # Archetype chip grid (4 cols x 4 rows)
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
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=4,
            text_color=MaterialColors.ON_SURFACE,
            placeholder_text_color="#3D3D3D",
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


if __name__ == "__main__":
    app = App()
    app.mainloop()
