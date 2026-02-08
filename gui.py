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


# === Material Design 3 カラーパレット ===
class MaterialColors:
    """
    Material You / M3 Dynamic Color System
    Based on Google's Material Design 3 color guidelines
    """
    
    # === M3 Tonal Palette (Purple seed) ===
    # Primary
    PRIMARY = "#6750A4"           # M3 Primary (P-40)
    PRIMARY_CONTAINER = "#EADDFF" # P-90
    ON_PRIMARY = "#FFFFFF"        # P-100
    ON_PRIMARY_CONTAINER = "#21005D"  # P-10
    
    # Secondary  
    SECONDARY = "#625B71"         # S-40
    SECONDARY_CONTAINER = "#E8DEF8"   # S-90
    ON_SECONDARY = "#FFFFFF"
    ON_SECONDARY_CONTAINER = "#1D192B"
    
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
    
    # === Surface Tones (Neutral) ===
    BACKGROUND = "#FFFBFE"        # N-99
    SURFACE = "#FFFBFE"           # N-99
    SURFACE_DIM = "#DED8E1"       # N-87
    SURFACE_BRIGHT = "#FFFBFE"    # N-99
    SURFACE_CONTAINER_LOWEST = "#FFFFFF"   # N-100
    SURFACE_CONTAINER_LOW = "#F7F2FA"      # N-96
    SURFACE_CONTAINER = "#F3EDF7"          # N-94
    SURFACE_CONTAINER_HIGH = "#ECE6F0"     # N-92
    SURFACE_CONTAINER_HIGHEST = "#E6E0E9"  # N-90
    
    # On Surface
    ON_BACKGROUND = "#1C1B1F"     # N-10
    ON_SURFACE = "#1C1B1F"        # N-10
    ON_SURFACE_VARIANT = "#49454F"    # NV-30
    
    # Outline
    OUTLINE = "#79747E"           # NV-50
    OUTLINE_VARIANT = "#CAC4D0"   # NV-80
    
    # Inverse
    INVERSE_SURFACE = "#313033"
    INVERSE_ON_SURFACE = "#F4EFF4"
    INVERSE_PRIMARY = "#D0BCFF"
    
    # Scrim & Shadow
    SCRIM = "#000000"
    SHADOW = "#000000"
    
    # === Legacy aliases for compatibility ===
    SURFACE_VARIANT = SURFACE_CONTAINER
    PRIMARY_VARIANT = "#7965AF"
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
DANBOORU_TAGS_FILE = OUTPUT_DIR / "danbooru_tags.md"
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
        normalized = _re.sub(r'\([^)]*:[\d.]+\)', '', tag).strip().lower().replace(" ", "_")
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(tag)
    return ", ".join(result)

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


# === データクラス ===
@dataclass
class CostTracker:
    haiku_input: int = 0
    haiku_output: int = 0
    sonnet_input: int = 0
    sonnet_output: int = 0

    def add(self, model: str, input_tokens: int, output_tokens: int):
        if "haiku" in model:
            self.haiku_input += input_tokens
            self.haiku_output += output_tokens
        else:
            self.sonnet_input += input_tokens
            self.sonnet_output += output_tokens

    def total_cost_usd(self) -> float:
        haiku_cost = COSTS[MODELS["haiku"]]
        sonnet_cost = COSTS[MODELS["sonnet"]]
        cost = (
            (self.haiku_input / 1_000_000) * haiku_cost["input"] +
            (self.haiku_output / 1_000_000) * haiku_cost["output"] +
            (self.sonnet_input / 1_000_000) * sonnet_cost["input"] +
            (self.sonnet_output / 1_000_000) * sonnet_cost["output"]
        )
        return cost

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
    
    # Sonnet polish (intensity >= 4のシーンのみ、約40%)
    sonnet_scenes = int(num_scenes * 0.4) if use_sonnet_polish else 0
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
        except:
            pass
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
            log_message(f"Rate limit: {e}")
            if callback:
                callback(f"レート制限、{RETRY_DELAY * 2}秒待機...")
            time.sleep(RETRY_DELAY * 2)

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
        callback("📦 コンテキスト圧縮中...")

    response = call_claude(
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
        callback("📦 コンテキスト圧縮中（ローカル・API節約）...")

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
        callback("✅ コンテキスト圧縮完了（ローカル・API節約）")

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
        callback(f"📖 {theme_name}テーマでストーリー原案を作成中...")

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
        response = call_claude(
            client, MODELS["haiku"],
            f"FANZA同人CG集の脚本家です。ユーザーのコンセプトに基づき、エロ同人作品の完全なストーリーあらすじを作成します。成人向けコンテンツを忠実に生成します。",
            prompt, cost_tracker, 2048, callback
        )

        synopsis = response.strip()
        log_message(f"あらすじ生成完了: {len(synopsis)}文字")
        if callback:
            callback(f"✅ ストーリー原案完成（{len(synopsis)}文字）")

        return synopsis

    except Exception as e:
        log_message(f"あらすじ生成エラー: {e}")
        if callback:
            callback(f"⚠️ あらすじ生成失敗: {str(e)[:50]}")
        # フォールバック: コンセプトをそのままあらすじとして使用
        return concept


# === Skill 2: Low Cost Pipeline ===

def generate_scene_batch(
    client: anthropic.Anthropic,
    context: dict,
    scenes: list,
    jailbreak: str,
    danbooru: str,
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

    heart_instruction = "♡は甘いシーンで自然に使用OK。" if use_heart else f"⚠️ ♡マークは使用禁止！テーマ「{theme_name}」では♡は不自然。代わりに「...」「っ」「〜」で感情を表現。"

    # 共通システムプロンプト（CG集フォーマット対応）
    common_system = f"""{jailbreak}

{skill if skill else "FANZA同人CG集の脚本を生成します。"}

{danbooru_nsfw if danbooru_nsfw else ""}

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
            3: f"kiss, french_kiss, undressing, groping, blush, nervous, anticipation, {theme_sd_expressions}",
            2: f"eye_contact, close-up, romantic, blushing, hand_holding, leaning_close, {theme_sd_expressions}",
            1: f"portrait, smile, casual, standing, looking_at_viewer, {theme_sd_expressions}"
        }
        sd_intensity_tags = intensity_sd_tags.get(intensity, "")
        background_tags = f"{location_tags}, {time_tags}".strip(", ")
        if theme_sd_tags:
            background_tags = f"{background_tags}, {theme_sd_tags}"
        
        composition_db = tag_db.get("compositions", {})
        composition_tags = composition_db.get(str(intensity), {}).get("tags", "")

        scenes_info.append({
            "scene": scene,
            "char_tags_str": char_tags_str,
            "sd_intensity_tags": sd_intensity_tags,
            "background_tags": background_tags,
            "composition_tags": composition_tags
        })

    # バッチプロンプト構築
    prompt_parts = []
    if story_context_section:
        prompt_parts.append(story_context_section)
    prompt_parts.append(f"設定: {json.dumps(context, ensure_ascii=False)}\n")
    prompt_parts.append(f"テーマ「{theme_name}」のトーン: {dialogue_tone}\n{heart_instruction}\n")
    
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
    "title": "シーンタイトル（8字以内）",
    "description": "このシーンの詳細説明（100字程度）",
    "location_detail": "場所の具体的な描写（30字）",
    "mood": "雰囲気（5字以内）",
    "character_feelings": {{
        "{char_names[0] if char_names else 'ヒロイン'}": "心情（20字）"
    }},
    "bubbles": [
        {{"speaker": "キャラ名", "type": "speech", "text": "短い一言"}}
    ],
    "onomatopoeia": [],
    "direction": "演出・ト書き（30字）",
    "story_flow": "次のシーンへの繋がり（15字）",
    "sd_prompt": "{QUALITY_POSITIVE_TAGS}, キャラ外見タグ, ポーズ・行為タグ, 表情タグ, 場所・背景タグ"
  }}
]

## ルール
1. 必ず{len(scenes)}シーン分のJSON配列を出力
2. 各シーンのscene_idは指定通りに
3. **bubblesは1-2個、各text 1〜10文字**（CG集の吹き出し）
4. sd_promptは「{QUALITY_POSITIVE_TAGS} + キャラ外見 + ポーズ + 表情 + 場所・背景」の順
5. タグは重複なくカンマ区切り
6. **シーン1→シーン2は自然に繋がるストーリーにすること**
7. **前シーンまでの展開を必ず引き継ぐこと**

JSON配列のみ出力。""")

    prompt = "\n".join(prompt_parts)

    system_with_cache = [
        {"type": "text", "text": common_system, "cache_control": {"type": "ephemeral"}},
    ]

    if callback:
        scene_ids = [s.get("scene_id") for s in scenes]
        callback(f"バッチ生成中: シーン {scene_ids} (Haiku, {len(scenes)}シーン一括)...")

    response = call_claude(
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
    synopsis: str = ""
) -> list:
    """あらすじをシーン分割してアウトライン生成（Haiku API 1回）"""
    theme_guide = THEME_GUIDES.get(theme, THEME_GUIDES.get("vanilla", {}))
    theme_name = theme_guide.get("name", "指定なし")
    story_arc = theme_guide.get("story_arc", "導入→展開→本番→余韻")
    key_emotions = theme_guide.get("key_emotions", ["期待", "緊張", "快感", "幸福"])
    story_elements = theme_guide.get("story_elements", [])

    if callback:
        callback(f"📝 {theme_name}テーマでシーン分割中（AI生成）...")

    chars = context.get("chars", [])
    char_names = [c["name"] for c in chars] if chars else ["ヒロイン"]

    # シーン配分計算
    act1 = max(1, round(num_scenes * 0.20))
    act4 = max(1, round(num_scenes * 0.10))
    act3 = max(2, round(num_scenes * 0.40))
    act2 = num_scenes - act1 - act3 - act4
    if act2 < 1:
        act2 = 1
        act3 = num_scenes - act1 - act2 - act4

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

## シーン配分（{num_scenes}シーン）
- 第1幕・導入: {act1}シーン → intensity 1-2（プロローグ・状況設定）
- 第2幕・展開: {act2}シーン → intensity 2-3（焦らし・ムード構築）
- 第3幕・本番: {act3}シーン → intensity 4-5（エロシーン・クライマックス）
- 第4幕・余韻: {act4}シーン → intensity 2（エピローグ）

## 出力形式（JSON配列）
各シーンは以下の形式：
{{
    "scene_id": シーン番号,
    "title": "シーンタイトル（8字以内）",
    "goal": "このシーンの目的（あらすじのどの部分に対応するか）",
    "location": "場所（あらすじに沿った具体的な場所）",
    "time": "時間帯",
    "situation": "このシーンで何が起きるか（あらすじに基づく具体的な状況を50字以上で）",
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
8. 同じlocationを連続2シーン以上使わないこと（場所を変えてストーリーを進める）

JSON配列のみ出力。"""

    try:
        response = call_claude(
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

        log_message(f"アウトライン生成完了（API）: {len(outline)}シーン, テーマ: {theme_name}")
        if callback:
            callback(f"✅ シーン分割完成（AI生成）: {len(outline)}シーン")

        return outline

    except Exception as e:
        log_message(f"アウトラインAPI生成失敗、テンプレートフォールバック: {e}")
        import traceback
        log_message(traceback.format_exc())
        if callback:
            callback(f"⚠️ AI分割失敗、テンプレートで代替: {str(e)[:50]}")

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



def extract_scene_summary(scene_result: dict) -> str:
    """生成済みシーンから要約を抽出（吹き出し全件含む・反復防止用）"""
    sid = scene_result.get("scene_id", "?")
    title = scene_result.get("title", "")
    desc = scene_result.get("description", "")[:80]
    flow = scene_result.get("story_flow", "")
    
    # 吹き出しテキストを抽出（新フォーマット: bubbles）
    bubbles = scene_result.get("bubbles", [])
    # 旧フォーマット互換: dialogueフィールドも確認
    if not bubbles:
        bubbles = scene_result.get("dialogue", [])
    
    key_lines = []
    for b in bubbles:
        if isinstance(b, dict):
            speaker = b.get("speaker", "")
            text = b.get("text", "") or b.get("line", "")
            if text:
                key_lines.append(f"{speaker}「{text}」")
    
    # オノマトペも記録
    onomatopoeia = scene_result.get("onomatopoeia", [])
    
    feelings = scene_result.get("character_feelings", {})
    feelings_str = ""
    if isinstance(feelings, dict):
        for k, v in feelings.items():
            feelings_str = f"{k}の心情: {str(v)[:30]}"
            break
    
    summary = f"[シーン{sid}: {title}] {desc}"
    if key_lines:
        summary += f" / 吹き出し: {'; '.join(key_lines)}"
    if onomatopoeia:
        summary += f" / SE: {', '.join(onomatopoeia)}"
    if feelings_str:
        summary += f" / {feelings_str}"
    if flow:
        summary += f" → {flow}"
    
    return summary

def generate_scene_draft(
    client: anthropic.Anthropic,
    context: dict,
    scene: dict,
    jailbreak: str,
    danbooru: str,
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
⚠️ ♡マークは使用禁止！
テーマ「{theme_name}」では♡は不自然。代わりに「...」「っ」「〜」で感情を表現。
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

最高潮のエロシーン。画像が全てを語る。

【吹き出し指針】
・喘ぎ声メインの吹き出し（2-3個）
・言葉になっていない声が理想
・例: 「あぁっ♡♡」「イっ…ちゃ…っ」「もぅ…むり…♡」

【オノマトペ指針】
・激しいものを3-4個: ビクビクッ, ドクドクッ, ビュルッ, ガクガク
・絶頂を表す効果音を必ず含める

【心情】
・{key_emotions[2] if len(key_emotions) > 2 else '快感に溺れる'}
・{key_emotions[3] if len(key_emotions) > 3 else '理性と本能の葛藤'}

【禁止】
❌ 長文の吹き出し（10文字超え）
❌ 説明的なセリフ
❌ 冷静な会話
"""
    elif intensity == 4:
        erotic_instruction = f"""
## 本番シーン（intensity 4）

濃厚なエロシーン。画像の行為を吹き出しが補強。

【吹き出し指針】
・喘ぎ+短い反応（2-3個）
・例: 「んっ…あぁ…♡」「そこ…だめ…」「はぁ…はぁ…」

【オノマトペ指針】
・行為を表す2-3個: ズブッ, ヌチュ, パンパン, グチュッ

【心情】
・{key_emotions[1] if len(key_emotions) > 1 else '恥ずかしさと快感の葛藤'}
・{key_emotions[2] if len(key_emotions) > 2 else 'もっと欲しいという欲求'}

【禁止】
❌ 説明的なセリフ
❌ 長い会話文
"""
    elif intensity == 3:
        erotic_instruction = f"""
## 前戯・焦らしシーン（intensity 3）

エロの助走。期待感を煽る画像に短い吹き出し。

【吹き出し指針】
・ドキドキ感のある短いセリフ+反応（2-3個）
・例: 「あっ…」「やだ…恥ずかしい…」「んっ…」

【オノマトペ指針】
・軽めの1-2個: ドキドキ, チュッ, サワッ, ゾクッ

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

【鉄則】
- 1吹き出し = 1〜10文字（最大でも12文字）
- 句読点不要。「...」「…」「っ」「〜」で繋ぐ
- 状況説明は吹き出しに入れない（descriptionに書く）
- 吹き出しの中に主語や目的語を入れない
- 「私は〜」「あなたが〜」のような文章はNG
- 会話のキャッチボールではなく、画像の補強テキスト

【intensity別の目安】
- 1-2: 吹き出し1-2個（自然な一言）、オノマトペなし〜1個
- 3: 吹き出し2-3個（反応+短い声）、オノマトペ1-2個
- 4-5: 吹き出し2-4個（喘ぎメイン）、オノマトペ2-4個

## 良い例 vs 悪い例

✅ 吹き出し: 「あっ♡」（2文字）
❌ 吹き出し: 「そこを触られると気持ちいいです」（15文字・説明的）

✅ 吹き出し: 「やだ…」（3文字）
❌ 吹き出し: 「こんなことしないでください…」（14文字・文章）

✅ 吹き出し: 「んっ…はぁ…」（6文字）
❌ 吹き出し: 「あなたに触れられて体が熱くなる」（15文字・小説）

✅ 心の声: 「バレたら…」（5文字）
❌ 心の声: 「こんなことをしている自分が信じられない」（19文字・独白）

✅ オノマトペ: ズブッ, ヌチュ, パンパン
❌ オノマトペは吹き出しの中に入れない（別フィールド）

全キャラ成人(18+)。JSON形式のみ出力。"""
    
    # シーン固有部分（毎回変わる）
    scene_system = f"""{erotic_instruction}

{theme_dialogue_instruction}"""

    # Prompt Caching: systemをリスト形式でcache_control付与
    system_with_cache = [
        {"type": "text", "text": common_system, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": scene_system}
    ]

    # シーン別SD推奨タグ（ポーズ・表情）+ テーマ別タグ
    intensity_sd_tags = {
        5: f"ahegao, orgasm, cum, trembling, tears, heavy_breathing, drooling, rolling_eyes, {theme_sd_expressions}",
        4: f"sex, penetration, nude, spread_legs, moaning, sweat, blush, panting, {theme_sd_expressions}",
        3: f"kiss, french_kiss, undressing, groping, blush, nervous, anticipation, {theme_sd_expressions}",
        2: f"eye_contact, close-up, romantic, blushing, hand_holding, leaning_close, {theme_sd_expressions}",
        1: f"portrait, smile, casual, standing, looking_at_viewer, {theme_sd_expressions}"
    }
    
    sd_intensity_tags = intensity_sd_tags.get(intensity, "")
    
    # 背景タグを組み合わせ
    background_tags = f"{location_tags}, {time_tags}".strip(", ")
    
    # テーマタグを背景に追加（intensity 3以上のみ）
    if theme_sd_tags and intensity >= 3:
        background_tags = f"{background_tags}, {theme_sd_tags}"

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

    # ストーリー連続性セクション
    story_context_section = ""
    if story_so_far:
        story_context_section = f"""
## ⚠️ ストーリーの連続性（最重要）

以下は前のシーンまでの展開です。**必ずこの続きとして**シーンを書いてください。

{story_so_far}

### 禁止事項
- 上記に含まれるセリフと同じ・類似のセリフは使用禁止
- 前シーンと同じ状況描写の繰り返し禁止
- ストーリーを必ず前シーンより先に進めること
---
"""

    prompt = f"""{synopsis_section}{story_context_section}設定: {json.dumps(context, ensure_ascii=False)}
シーン情報: {json.dumps(scene, ensure_ascii=False)}

## 出力形式（この形式で出力してください）

{{
    "scene_id": {scene['scene_id']},
    "title": "シーンタイトル（8字以内）",
    "description": "このシーンの詳細説明。場所、状況、何が起きているか、画像として何が描かれるかを100字程度で説明",
    "location_detail": "場所の具体的な描写（30字）",
    "mood": "雰囲気（5字以内）",
    "character_feelings": {{
        "{char_names[0] if char_names else 'ヒロイン'}": "このシーンでの心情（20字）"
    }},
    "bubbles": [
        {{"speaker": "キャラ名", "type": "speech", "text": "短い一言"}},
        {{"speaker": "キャラ名", "type": "moan", "text": "あっ♡"}},
        {{"speaker": "キャラ名", "type": "thought", "text": "心の声"}}
    ],
    "onomatopoeia": ["効果音1", "効果音2"],
    "direction": "演出・ト書き（30字）",
    "story_flow": "次のシーンへの繋がり（15字）",
    "sd_prompt": "{QUALITY_POSITIVE_TAGS}, キャラ外見タグ, ポーズ・行為タグ, 表情タグ, 場所・背景タグ, 照明タグ, テーマタグ"
}}

## タグ参考（sd_promptに統合して使用）

キャラ固有: {char_tags_str}
ポーズ・表情: {sd_intensity_tags}
背景・場所: {background_tags}
構図: {composition_tags}
テーマ専用: {theme_tags_combined}

## ルール

1. descriptionは必ず100字程度で詳しく書く（画像として描かれる内容を説明）
2. character_feelingsで心情を明確に
3. **bubblesは1-4個。各textは1〜10文字**（CG集の吹き出し。短いほど良い）
4. typeはspeech/moan/thoughtの3種。intensity 4-5はmoanメイン
5. **onomatopoeiaは場面に合った効果音**（intensity 1-2はなし〜1個、3は1-2個、4-5は2-4個）
6. sd_promptは「{QUALITY_POSITIVE_TAGS} + キャラ外見 + ポーズ + 表情 + 場所・背景 + 照明」の順で統合
7. **sd_promptはこのシーンの実際の内容のみを反映**すること
8. **前シーンの流れを必ず引き継ぐこと**
9. **キャラの一人称・語尾はキャラガイドを絶対厳守**

JSONのみ出力。"""

    # intensity 4以上はSonnetで高品質に
    model = MODELS["sonnet"] if intensity >= 4 else MODELS["haiku"]
    model_name = "Sonnet" if intensity >= 4 else "Haiku"
    
    if callback:
        callback(f"シーン {scene['scene_id']} 生成中 ({model_name}, 重要度{intensity}, {theme_name})...")
    
    response = call_claude(
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

    response = call_claude(
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
        callback("🔍 品質チェック中...")

    response = call_claude(
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

    response = call_claude(
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
    skip_quality_check: bool = True
) -> tuple[list, CostTracker]:
    client = anthropic.Anthropic(api_key=api_key)
    cost_tracker = CostTracker()

    jailbreak = load_file(JAILBREAK_FILE)
    danbooru = load_file(DANBOORU_TAGS_FILE)
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
                        callback(f"📂 キャラ設定適用: {char_name}（{work_title}）")
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
                        callback(f"📦 プリセットキャラ適用: {char_name}（{work_title}）")
        except Exception as e:
            log_message(f"プリセット読込エラー: {e}")
    
    if char_profiles:
        char_names = [cp.get("character_name", "") for cp in char_profiles]
        log_message(f"使用キャラ設定: {', '.join(char_names)}")
        if callback:
            callback(f"✅ {len(char_profiles)}件のキャラ設定を適用")
    else:
        log_message("キャラ設定なし - 汎用設定で生成")
        if callback:
            callback("⚠️ キャラ設定なし（汎用設定で生成）")

    # テーマ情報
    theme_guide = THEME_GUIDES.get(theme, {})
    theme_name = theme_guide.get("name", "指定なし")
    if theme and theme_guide:
        log_message(f"テーマ適用: {theme_name} (arc: {theme_guide.get('story_arc', '')})")
        if callback:
            callback(f"🎭 テーマ: {theme_name}")

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
        callback("✅ コンテキスト圧縮完了")

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
            callback(f"⚠️ あらすじ生成失敗、コンセプトで代替")

    if callback:
        callback("✅ ストーリー原案完成")

    # Phase 3: アウトライン生成（あらすじをシーン分割）
    log_message("Phase 3 開始: アウトライン生成（シーン分割）")
    if callback:
        callback("🔧 Phase 3: シーン分割")

    try:
        outline = generate_outline(client, context, num_scenes, theme, cost_tracker, callback, synopsis=synopsis)
        log_message(f"アウトライン生成完了: {len(outline)}シーン")
        
        intensity_counts = {}
        for scene in outline:
            i = scene.get("intensity", 3)
            intensity_counts[i] = intensity_counts.get(i, 0) + 1
        log_message(f"intensity分布: {intensity_counts}")
    except Exception as e:
        log_message(f"アウトライン生成エラー: {e}")
        raise

    if callback:
        high_intensity = sum(1 for s in outline if s.get("intensity", 0) >= 4)
        low_intensity = len(outline) - high_intensity
        callback(f"✅ シーン分割完成: {len(outline)}シーン（Haiku×{low_intensity} + Sonnet×{high_intensity}）")

    # コスト見積もり（あらすじ+アウトライン+シーン生成）
    low_count = sum(1 for s in outline if s.get("intensity", 3) <= 3)
    high_count = sum(1 for s in outline if s.get("intensity", 3) >= 4)
    outline_cost = 2000 / 1_000_000 * 0.25 + 2000 / 1_000_000 * 1.25
    scene_cost = (low_count * 3000 / 1_000_000 * 0.25 + low_count * 2500 / 1_000_000 * 1.25 +
                  high_count * 3000 / 1_000_000 * 3.00 + high_count * 2500 / 1_000_000 * 15.00)
    est_cost = outline_cost * 2 + scene_cost
    if callback:
        callback(f"💰 推定コスト: ${est_cost:.4f}（API {len(outline)+2}回: あらすじ1+分割1+Haiku×{low_count}+Sonnet×{high_count}）")

    # Phase 4: シーン生成（完全シーケンシャル + ストーリー蓄積）
    results = []
    story_summaries = []

    for i, scene in enumerate(outline):
        intensity = scene.get("intensity", 3)
        model_type = "Sonnet" if intensity >= 4 else "Haiku"

        # story_so_far を構築（直近5シーンの要約）
        story_so_far = ""
        if story_summaries:
            recent = story_summaries[-5:]
            story_so_far = "\n".join(recent)

        try:
            log_message(f"シーン {i+1}/{len(outline)} 生成開始 (intensity={intensity}, {model_type})")
            if callback:
                callback(f"🎬 シーン {i+1}/{len(outline)} [{model_type}] 重要度{intensity}")

            draft = generate_scene_draft(
                client, context, scene, jailbreak, danbooru, sd_guide,
                cost_tracker, theme, char_profiles, callback,
                story_so_far=story_so_far,
                synopsis=synopsis
            )

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
                callback(f"✅ シーン {i+1}/{len(outline)} 完了")

        except Exception as e:
            err_msg = str(e)
            log_message(f"シーン {i+1} 生成エラー: {err_msg}")

            # コンテンツ拒否の場合、あらすじなしでリトライ
            is_refusal = any(kw in err_msg for kw in ["倫理", "対応することはできません", "cannot", "inappropriate"])
            if is_refusal:
                log_message(f"シーン {i+1} コンテンツ拒否検出、あらすじ省略でリトライ")
                if callback:
                    callback(f"⚠️ シーン {i+1} リトライ中...")
                try:
                    draft = generate_scene_draft(
                        client, context, scene, jailbreak, danbooru, sd_guide,
                        cost_tracker, theme, char_profiles, callback,
                        story_so_far=story_so_far,
                        synopsis=""
                    )
                    results.append(draft)
                    summary = extract_scene_summary(draft)
                    story_summaries.append(summary)
                    log_message(f"シーン {i+1} リトライ成功")
                    if callback:
                        callback(f"✅ シーン {i+1}/{len(outline)} リトライ成功")
                    continue
                except Exception as e2:
                    log_message(f"シーン {i+1} リトライも失敗: {e2}")

            import traceback
            log_message(traceback.format_exc())
            if callback:
                callback(f"❌ シーン {i+1} エラー: {err_msg[:50]}")

            error_result = {
                "scene_id": scene.get("scene_id", i + 1),
                "title": f"シーン{i+1}",
                "mood": "エラー",
                "dialogue": [],
                "direction": f"生成エラー: {err_msg[:100]}",
                "sd_prompt": ""
            }
            results.append(error_result)
            story_summaries.append(f"[シーン{i+1}: エラーにより欠落]")

    # 完了サマリー
    success_count = sum(1 for r in results if r.get("mood") != "エラー")
    log_message(f"パイプライン完了: {success_count}/{len(results)}シーン成功")
    
    if callback:
        callback(f"🎉 生成完了: {success_count}シーン成功")

    return results, cost_tracker


def export_csv(results: list, output_path: Path):
    fieldnames = [
        "scene_id", "title", "description", "location_detail", "mood",
        "character_feelings", "bubble_no", "speaker", "type", "text",
        "onomatopoeia", "direction", "story_flow",
        "sd_prompt"
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
        "シーンID", "タイトル", "シーン説明", "場所詳細", "雰囲気",
        "キャラ心情", "吹き出しNo", "話者", "種類", "テキスト",
        "オノマトペ", "演出", "次への繋がり",
        "SDプロンプト"
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
                scene.get("location_detail", "") if idx == 0 else "",
                scene.get("mood", "") if idx == 0 else "",
                feelings_str if idx == 0 else "",
                idx + 1 if bubble else "",
                bubble.get("speaker", ""),
                bubble.get("type", bubble.get("emotion", "")),
                bubble.get("text", bubble.get("line", "")),
                ono_str if idx == 0 else "",
                scene.get("direction", "") if idx == 0 else "",
                scene.get("story_flow", "") if idx == 0 else "",
                scene.get("sd_prompt", "") if idx == 0 else ""
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
        4: 20,   # 場所詳細
        5: 10,   # 雰囲気
        6: 25,   # キャラ心情
        7: 8,    # 吹き出しNo
        8: 10,   # 話者
        9: 8,    # 種類
        10: 20,  # テキスト
        11: 20,  # オノマトペ
        12: 20,  # 演出
        13: 15,  # 次への繋がり
        14: 60   # SDプロンプト
    }
    
    for col, width in column_widths.items():
        ws.column_dimensions[chr(64 + col) if col <= 26 else f"A{chr(64 + col - 26)}"].width = width
    
    # ヘッダー行を固定
    ws.freeze_panes = "A2"
    
    wb.save(output_path)
    log_message(f"Excel出力完了: {output_path}")
    return True


def export_json(results: list, output_path: Path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


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
        callback(f"🔍 {char_name}の詳細分析中（Sonnet使用）...")

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
        "brief_description": "このキャラを一言で表すと（20字以内）",
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
    response = call_claude(
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
    callback: Optional[Callable] = None
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
            callback(f"📦 プリセットキャラを使用: {char_name}")
        bible, _ = load_preset_character(char_id, callback)
        return bible, char_id, cost_tracker

    # キャッシュチェック
    if bible_path.exists() and not force_refresh:
        if callback:
            callback(f"📂 既存のキャラデータを使用: {char_id}")
        with open(bible_path, "r", encoding="utf-8") as f:
            bible = json.load(f)
        return bible, char_id, cost_tracker

    if callback:
        callback(f"🚀 キャラクター生成開始: {char_name}")

    # Step 1: キャラクター分析
    if callback:
        callback("📊 Step 1/3: キャラクター分析")

    bible = analyze_character(client, work_title, char_name, cost_tracker, callback)

    # originality_guardを追加
    bible["originality_guard"] = {
        "avoid_canonical_lines": True,
        "avoid_known_catchphrases": True
    }

    # Step 2: キャラバイブル保存
    if callback:
        callback("💾 Step 2/3: キャラバイブル保存")

    with open(bible_path, "w", encoding="utf-8") as f:
        json.dump(bible, f, ensure_ascii=False, indent=2)

    log_message(f"キャラバイブル保存: {bible_path}")

    # Step 3: Skill生成
    if callback:
        callback("📝 Step 3/3: Skill生成")

    skill_content = generate_character_skill(char_id, bible)

    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(skill_content)

    log_message(f"Skill保存: {skill_path}")

    if callback:
        callback(f"✅ キャラクター生成完了: {char_id}")

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
        except:
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
    except:
        return []


def load_preset_character(char_id: str, callback: Optional[Callable] = None) -> tuple[dict, str]:
    """プリセットキャラをcharactersにコピーしてskillも生成（API不要）"""
    preset_path = PRESET_CHARS_DIR / f"{char_id}.json"
    bible_path = CHARACTERS_DIR / f"{char_id}.json"
    skill_path = CHAR_SKILLS_DIR / f"{char_id}.skill.md"

    if callback:
        callback(f"📂 プリセット読み込み中: {char_id}")

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
        callback(f"✅ プリセット読み込み完了: {bible.get('character_name', char_id)}")

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
            header_frame.pack(fill="x", padx=16, pady=(16, 8))
            
            self.title_label = ctk.CTkLabel(
                header_frame,
                text=title,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),  # Title Medium
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
                    font=ctk.CTkFont(size=12),
                    corner_radius=20,  # Fully rounded for icon button
                    command=self.toggle_collapse
                )
                self.collapse_btn.pack(side="right")
                self._update_collapse_icon()

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.content_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))
    
    def _update_collapse_icon(self):
        icon = "keyboard_arrow_up" if not self.is_collapsed else "keyboard_arrow_down"
        # Using Unicode arrows as fallback
        self.collapse_btn.configure(text="▲" if not self.is_collapsed else "▼")
    
    def toggle_collapse(self):
        if self.is_collapsed:
            self.content_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))
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
                "hover_color": "#7965AF",  # Slightly lighter on hover
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
            font=ctk.CTkFont(family="Segoe UI", size=s["font_size"], weight="bold"),
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
            font=ctk.CTkFont(family="Segoe UI", size=12),
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
                font=ctk.CTkFont(family="Segoe UI", size=14),
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
                font=ctk.CTkFont(family="Segoe UI", size=14),
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
                font=ctk.CTkFont(family="Segoe UI", size=12),
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
            font=ctk.CTkFont(family="Segoe UI", size=13),
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
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=MaterialColors.INVERSE_ON_SURFACE
        )
        self.message_label.pack(side="left", padx=16, pady=14)
        
        # Optional action button
        self.action_btn = ctk.CTkButton(
            self,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
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

        self.create_widgets()
        self.load_saved_config()

    def create_widgets(self):
        # ══════════════════════════════════════════════════════════════
        # HEADER
        # ══════════════════════════════════════════════════════════════
        header = ctk.CTkFrame(self, height=52, fg_color=MaterialColors.SURFACE, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="both", expand=True, padx=20, pady=8)

        ctk.CTkLabel(
            header_inner, text="🎬 Daihon Rakku",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=MaterialColors.PRIMARY
        ).pack(side="left")

        ctk.CTkLabel(
            header_inner, text="v0.9.2",
            font=ctk.CTkFont(size=10), text_color=MaterialColors.ON_SURFACE_VARIANT,
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=4, padx=6, pady=2
        ).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(
            header_inner, text="FANZA同人CG集 脚本生成",
            font=ctk.CTkFont(size=11), text_color=MaterialColors.ON_SURFACE_VARIANT
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
        content.pack(fill="both", expand=True, padx=20, pady=16)

        # ══════════════════════════════════════════════════════════════
        # 1. API設定
        # ══════════════════════════════════════════════════════════════
        api_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=10)
        api_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            api_card, text="🔑 API設定",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MaterialColors.ON_SURFACE
        ).pack(anchor="w", padx=14, pady=(10, 6))

        self.api_field = ctk.CTkEntry(
            api_card, height=42, placeholder_text="Anthropic API Key (sk-ant-...)", show="*",
            font=ctk.CTkFont(size=13),
            fg_color=MaterialColors.SURFACE_CONTAINER, text_color=MaterialColors.ON_SURFACE,
            corner_radius=6, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT
        )
        self.api_field.pack(fill="x", padx=14, pady=(0, 10))

        # ══════════════════════════════════════════════════════════════
        # 2. プロファイル管理（キャラ生成より上に配置）
        # ══════════════════════════════════════════════════════════════
        profile_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=10)
        profile_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            profile_card, text="📁 プロファイル管理",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MaterialColors.ON_SURFACE
        ).pack(anchor="w", padx=14, pady=(10, 6))

        profile_row = ctk.CTkFrame(profile_card, fg_color="transparent")
        profile_row.pack(fill="x", padx=14, pady=(0, 10))

        self.profile_combo = ctk.CTkComboBox(
            profile_row, values=["（新規）"] + get_profile_list(), height=36, width=150,
            font=ctk.CTkFont(size=12),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6,
            button_color=MaterialColors.PRIMARY, command=self.on_profile_selected
        )
        self.profile_combo.pack(side="left", padx=(0, 6))
        self.profile_combo.set("（新規）")

        self.profile_name_entry = ctk.CTkEntry(
            profile_row, height=36, width=120, placeholder_text="プロファイル名",
            font=ctk.CTkFont(size=12),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6
        )
        self.profile_name_entry.pack(side="left", padx=(0, 8))

        btn_configs = [
            ("保存", self.save_current_profile, MaterialColors.PRIMARY, MaterialColors.ON_PRIMARY),
            ("読込", self.load_selected_profile, MaterialColors.SECONDARY_CONTAINER, MaterialColors.ON_SECONDARY_CONTAINER),
            ("複製", self.copy_selected_profile, "transparent", MaterialColors.ON_SURFACE_VARIANT),
            ("削除", self.delete_selected_profile, "transparent", MaterialColors.ERROR),
        ]
        for txt, cmd, bg, fg in btn_configs:
            ctk.CTkButton(
                profile_row, text=txt, height=32, width=48,
                font=ctk.CTkFont(size=11), corner_radius=6,
                fg_color=bg, text_color=fg,
                hover_color=MaterialColors.SURFACE_CONTAINER_HIGH,
                command=cmd
            ).pack(side="left", padx=(0, 3))

        # ══════════════════════════════════════════════════════════════
        # 3. キャラクター設定
        # ══════════════════════════════════════════════════════════════
        char_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=10)
        char_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            char_card, text="🎭 キャラクター設定",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MaterialColors.ON_SURFACE
        ).pack(anchor="w", padx=14, pady=(10, 6))

        # --- タブビュー ---
        self.char_tabview = ctk.CTkTabview(
            char_card, fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST,
            segmented_button_fg_color=MaterialColors.SURFACE_CONTAINER,
            segmented_button_selected_color=MaterialColors.PRIMARY,
            segmented_button_unselected_color=MaterialColors.SURFACE_CONTAINER,
            height=420, corner_radius=8
        )
        self.char_tabview.pack(fill="x", padx=14, pady=(0, 10))

        # タブ作成
        tab_preset = self.char_tabview.add("プリセット")
        tab_custom = self.char_tabview.add("オリジナル作成")
        tab_api = self.char_tabview.add("API生成")

        # --- Tab: プリセット ---
        ctk.CTkLabel(
            tab_preset, text="プリセットキャラ（API不要・33体収録）",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=MaterialColors.ON_SURFACE
        ).pack(anchor="w", pady=(8, 4))

        self._preset_map = {}
        self.preset_dropdown = ctk.CTkOptionMenu(
            tab_preset, values=["（プリセット選択）"],
            command=self.on_preset_selected,
            font=ctk.CTkFont(size=13), width=380,
            fg_color=MaterialColors.SURFACE_CONTAINER,
            button_color=MaterialColors.PRIMARY,
            text_color=MaterialColors.ON_SURFACE
        )
        self.preset_dropdown.pack(anchor="w", pady=(0, 6))

        self.preset_load_btn = MaterialButton(
            tab_preset, text="プリセット読み込み（API不要）",
            variant="filled_tonal", command=self.load_preset_action
        )
        self.preset_load_btn.pack(anchor="w", pady=(0, 8))

        # --- Tab: オリジナル作成 ---
        custom_scroll = ctk.CTkScrollableFrame(
            tab_custom, fg_color="transparent", height=360
        )
        custom_scroll.pack(fill="both", expand=True)

        # ヘルパー関数
        def add_dropdown(parent, label, options, default=None):
            ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=11, weight="bold"),
                        text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w", pady=(6,0))
            dd = ctk.CTkOptionMenu(parent, values=options, font=ctk.CTkFont(size=12),
                                   width=350, fg_color=MaterialColors.SURFACE_CONTAINER,
                                   button_color=MaterialColors.PRIMARY,
                                   text_color=MaterialColors.ON_SURFACE)
            dd.pack(anchor="w", pady=(2, 0))
            if default:
                dd.set(default)
            return dd

        # 基本情報
        ctk.CTkLabel(custom_scroll, text="── 基本情報 ──",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=MaterialColors.PRIMARY).pack(anchor="w", pady=(4,2))

        ctk.CTkLabel(custom_scroll, text="キャラ名", font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w", pady=(6,0))
        self.custom_name_entry = ctk.CTkEntry(
            custom_scroll, height=36, placeholder_text="例: 佐藤花子",
            font=ctk.CTkFont(size=13), width=350,
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6
        )
        self.custom_name_entry.pack(anchor="w", pady=(2, 0))

        self.custom_age_dd = add_dropdown(custom_scroll, "年齢・外見", AGE_OPTIONS, "JK（女子高生）")
        self.custom_rel_dd = add_dropdown(custom_scroll, "主人公との関係", RELATIONSHIP_OPTIONS, "クラスメイト")

        # 性格・口調
        ctk.CTkLabel(custom_scroll, text="── 性格・口調 ──",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=MaterialColors.PRIMARY).pack(anchor="w", pady=(12,2))

        self.custom_archetype_dd = add_dropdown(custom_scroll, "性格タイプ", ARCHETYPE_OPTIONS, "ツンデレ")
        self.custom_first_person_dd = add_dropdown(custom_scroll, "一人称", FIRST_PERSON_OPTIONS, "あたし")
        self.custom_speech_dd = add_dropdown(custom_scroll, "口調", SPEECH_STYLE_OPTIONS, "タメ口")

        # 外見
        ctk.CTkLabel(custom_scroll, text="── 外見 ──",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=MaterialColors.PRIMARY).pack(anchor="w", pady=(12,2))

        self.custom_hair_color_dd = add_dropdown(custom_scroll, "髪色", HAIR_COLOR_OPTIONS, "黒髪")
        self.custom_hair_style_dd = add_dropdown(custom_scroll, "髪型", HAIR_STYLE_OPTIONS, "ロングストレート")
        self.custom_body_dd = add_dropdown(custom_scroll, "体型", BODY_TYPE_OPTIONS, "普通")
        self.custom_chest_dd = add_dropdown(custom_scroll, "胸", CHEST_OPTIONS, "普通（C）")
        self.custom_clothing_dd = add_dropdown(custom_scroll, "服装", CLOTHING_OPTIONS, "制服（ブレザー）")

        # エロシーン設定
        ctk.CTkLabel(custom_scroll, text="── エロシーン設定 ──",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=MaterialColors.PRIMARY).pack(anchor="w", pady=(12,2))

        shyness_labels = [s[0] for s in SHYNESS_OPTIONS]
        self.custom_shyness_dd = add_dropdown(custom_scroll, "恥ずかしがり度", shyness_labels, "3 - 普通")

        # カスタム特性（自由入力）
        ctk.CTkLabel(custom_scroll, text="── 追加設定（任意） ──",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=MaterialColors.PRIMARY).pack(anchor="w", pady=(12,2))

        ctk.CTkLabel(custom_scroll, text="追加の性格特性（「、」区切り）",
                    font=ctk.CTkFont(size=11), text_color=MaterialColors.ON_SURFACE_VARIANT
                    ).pack(anchor="w", pady=(6,0))
        self.custom_traits_entry = ctk.CTkEntry(
            custom_scroll, height=36, placeholder_text="例: 読書好き、猫が好き",
            font=ctk.CTkFont(size=12), width=350,
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6
        )
        self.custom_traits_entry.pack(anchor="w", pady=(2, 0))

        # 保存ボタン
        self.custom_save_btn = MaterialButton(
            custom_scroll, text="キャラクターを保存（API不要）",
            variant="filled", command=self.save_custom_character
        )
        self.custom_save_btn.pack(anchor="w", pady=(16, 8))

        # --- Tab: API生成 ---
        ctk.CTkLabel(
            tab_api, text="Claude APIでキャラクター分析（Sonnet使用）",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=MaterialColors.ON_SURFACE
        ).pack(anchor="w", pady=(8, 4))

        api_char_row = ctk.CTkFrame(tab_api, fg_color="transparent")
        api_char_row.pack(fill="x", pady=(0, 6))

        work_frame = ctk.CTkFrame(api_char_row, fg_color="transparent")
        work_frame.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(work_frame, text="作品名", font=ctk.CTkFont(size=11),
                    text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w")
        self.work_title_entry = ctk.CTkEntry(
            work_frame, height=38, placeholder_text="例: 五等分の花嫁",
            font=ctk.CTkFont(size=13), fg_color=MaterialColors.SURFACE_CONTAINER,
            corner_radius=6, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT
        )
        self.work_title_entry.pack(fill="x", pady=(3, 0))

        char_name_frame = ctk.CTkFrame(api_char_row, fg_color="transparent")
        char_name_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(char_name_frame, text="キャラ名", font=ctk.CTkFont(size=11),
                    text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w")
        self.char_name_entry = ctk.CTkEntry(
            char_name_frame, height=38, placeholder_text="例: 中野一花",
            font=ctk.CTkFont(size=13), fg_color=MaterialColors.SURFACE_CONTAINER,
            corner_radius=6, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT
        )
        self.char_name_entry.pack(fill="x", pady=(3, 0))

        self.char_generate_btn = ctk.CTkButton(
            tab_api, text="✨ キャラ生成（API使用）", height=36,
            font=ctk.CTkFont(size=12, weight="bold"), corner_radius=6,
            fg_color=MaterialColors.PRIMARY, hover_color=MaterialColors.PRIMARY_VARIANT,
            command=self.start_char_generation
        )
        self.char_generate_btn.pack(anchor="w", pady=(0, 8))

        # --- 共通: 使用キャラ選択 ---
        char_select_row = ctk.CTkFrame(char_card, fg_color="transparent")
        char_select_row.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkLabel(char_select_row, text="使用キャラ:",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=MaterialColors.ON_SURFACE_VARIANT).pack(side="left", padx=(0, 6))

        self.char_select_combo = ctk.CTkComboBox(
            char_select_row, values=["（キャラ選択）"], height=36,
            font=ctk.CTkFont(size=12),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6,
            button_color=MaterialColors.PRIMARY, dropdown_fg_color=MaterialColors.SURFACE,
            command=self.on_char_selected
        )
        self.char_select_combo.pack(side="left", fill="x", expand=True)
        self.refresh_char_list()
        self.refresh_preset_list()

        # ══════════════════════════════════════════════════════════════
        # 4. 作品設定（メイン入力エリア）
        # ══════════════════════════════════════════════════════════════
        concept_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=10)
        concept_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            concept_card, text="📖 作品設定",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MaterialColors.ON_SURFACE
        ).pack(anchor="w", padx=14, pady=(10, 8))

        # コンセプト入力
        concept_label_frame = ctk.CTkFrame(concept_card, fg_color="transparent")
        concept_label_frame.pack(fill="x", padx=14)
        ctk.CTkLabel(
            concept_label_frame, text="コンセプト",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MaterialColors.PRIMARY
        ).pack(side="left")
        ctk.CTkLabel(
            concept_label_frame, text="（作品の設定・シチュエーションを詳しく記述）",
            font=ctk.CTkFont(size=10), text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left", padx=(4, 0))

        self.concept_text = ctk.CTkTextbox(
            concept_card, height=120,
            font=ctk.CTkFont(size=14),
            fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST,
            text_color=MaterialColors.ON_SURFACE,
            corner_radius=6, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT,
            wrap="word"
        )
        self.concept_text.pack(fill="x", padx=14, pady=(6, 12))

        # 登場人物入力
        char_label_frame = ctk.CTkFrame(concept_card, fg_color="transparent")
        char_label_frame.pack(fill="x", padx=14)
        ctk.CTkLabel(
            char_label_frame, text="登場人物",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MaterialColors.PRIMARY
        ).pack(side="left")
        ctk.CTkLabel(
            char_label_frame, text="（キャラ名・関係性を記述）",
            font=ctk.CTkFont(size=10), text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left", padx=(4, 0))

        self.characters_text = ctk.CTkTextbox(
            concept_card, height=90,
            font=ctk.CTkFont(size=14),
            fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST,
            text_color=MaterialColors.ON_SURFACE,
            corner_radius=6, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT,
            wrap="word"
        )
        self.characters_text.pack(fill="x", padx=14, pady=(6, 12))

        # その他の登場人物入力
        other_label_frame = ctk.CTkFrame(concept_card, fg_color="transparent")
        other_label_frame.pack(fill="x", padx=14)
        ctk.CTkLabel(
            other_label_frame, text="その他の登場人物",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MaterialColors.PRIMARY
        ).pack(side="left")
        ctk.CTkLabel(
            other_label_frame, text="（男主人公・サブキャラ等の設定）",
            font=ctk.CTkFont(size=10), text_color=MaterialColors.ON_SURFACE_VARIANT
        ).pack(side="left", padx=(4, 0))

        self.other_chars_text = ctk.CTkTextbox(
            concept_card, height=70,
            font=ctk.CTkFont(size=14),
            fg_color=MaterialColors.SURFACE_CONTAINER_LOWEST,
            text_color=MaterialColors.ON_SURFACE,
            corner_radius=6, border_width=1, border_color=MaterialColors.OUTLINE_VARIANT,
            wrap="word"
        )
        self.other_chars_text.pack(fill="x", padx=14, pady=(6, 14))

        # ══════════════════════════════════════════════════════════════
        # 5. 生成設定
        # ══════════════════════════════════════════════════════════════
        settings_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=10)
        settings_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            settings_card, text="⚙️ 生成設定",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MaterialColors.ON_SURFACE
        ).pack(anchor="w", padx=14, pady=(10, 6))

        settings_row = ctk.CTkFrame(settings_card, fg_color="transparent")
        settings_row.pack(fill="x", padx=14, pady=(0, 10))

        # シーン数
        scenes_frame = ctk.CTkFrame(settings_row, fg_color="transparent")
        scenes_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(scenes_frame, text="シーン数", font=ctk.CTkFont(size=11), text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w")
        self.scenes_entry = ctk.CTkEntry(
            scenes_frame, height=38, font=ctk.CTkFont(size=13),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6,
            border_width=1, border_color=MaterialColors.OUTLINE_VARIANT
        )
        self.scenes_entry.pack(fill="x", pady=(3, 0))
        self.scenes_entry.insert(0, "10")

        # テーマ
        theme_frame = ctk.CTkFrame(settings_row, fg_color="transparent")
        theme_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(theme_frame, text="テーマ", font=ctk.CTkFont(size=11), text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w")
        self.theme_combo = ctk.CTkComboBox(
            theme_frame, values=list(THEME_OPTIONS.keys()), height=38,
            font=ctk.CTkFont(size=12),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6,
            button_color=MaterialColors.PRIMARY, dropdown_fg_color=MaterialColors.SURFACE
        )
        self.theme_combo.pack(fill="x", pady=(3, 0))
        self.theme_combo.set("指定なし")

        self.scenes_entry.bind("<KeyRelease>", self.update_cost_preview)

        # ══════════════════════════════════════════════════════════════
        # 6. 生成セクション
        # ══════════════════════════════════════════════════════════════
        generate_section = ctk.CTkFrame(content, fg_color=MaterialColors.PRIMARY_CONTAINER, corner_radius=10)
        generate_section.pack(fill="x", pady=(0, 10))

        gen_inner = ctk.CTkFrame(generate_section, fg_color="transparent")
        gen_inner.pack(fill="x", padx=14, pady=14)

        # ステータス行
        status_row = ctk.CTkFrame(gen_inner, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 6))

        self.status_label = ctk.CTkLabel(
            status_row, text="⏳ 待機中",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MaterialColors.ON_PRIMARY_CONTAINER
        )
        self.status_label.pack(side="left")

        # フェーズ
        phase_frame = ctk.CTkFrame(status_row, fg_color="transparent")
        phase_frame.pack(side="right")
        self.phase_labels = []
        for phase in ["圧縮", "生成", "完了"]:
            pill = ctk.CTkFrame(phase_frame, fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=8)
            pill.pack(side="left", padx=2)
            lbl = ctk.CTkLabel(pill, text=phase, font=ctk.CTkFont(size=10), text_color=MaterialColors.ON_SURFACE_VARIANT, padx=6, pady=2)
            lbl.pack()
            self.phase_labels.append((pill, lbl))

        # プログレス
        self.progress = ctk.CTkProgressBar(
            gen_inner, fg_color=MaterialColors.SURFACE_CONTAINER, progress_color=MaterialColors.PRIMARY,
            height=6, corner_radius=3
        )
        self.progress.pack(fill="x", pady=(0, 10))
        self.progress.set(0)

        # ボタン行
        btn_row = ctk.CTkFrame(gen_inner, fg_color="transparent")
        btn_row.pack(fill="x")

        self.generate_btn = ctk.CTkButton(
            btn_row, text="🚀 脚本を生成", height=46,
            font=ctk.CTkFont(size=14, weight="bold"), corner_radius=8,
            fg_color=MaterialColors.PRIMARY, hover_color=MaterialColors.PRIMARY_VARIANT,
            command=self.start_generation
        )
        self.generate_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.save_btn = ctk.CTkButton(
            btn_row, text="💾 保存", height=46, width=70,
            font=ctk.CTkFont(size=12), corner_radius=8,
            fg_color=MaterialColors.SECONDARY_CONTAINER, text_color=MaterialColors.ON_SECONDARY_CONTAINER,
            hover_color=MaterialColors.SURFACE_CONTAINER_HIGH,
            command=self.save_settings
        )
        self.save_btn.pack(side="left", padx=(0, 6))

        self.stop_btn = ctk.CTkButton(
            btn_row, text="停止", height=46, width=60,
            font=ctk.CTkFont(size=12), corner_radius=8,
            fg_color="transparent", hover_color=MaterialColors.ERROR_CONTAINER,
            border_width=1, border_color=MaterialColors.OUTLINE,
            text_color=MaterialColors.ON_SURFACE_VARIANT,
            command=self.stop_generation
        )
        self.stop_btn.pack(side="left")
        self.stop_btn.configure(state="disabled")

        # コスト予測
        self.cost_preview_label = ctk.CTkLabel(
            gen_inner, text="💰 シーン数入力で予想コスト表示",
            font=ctk.CTkFont(size=10), text_color=MaterialColors.ON_PRIMARY_CONTAINER
        )
        self.cost_preview_label.pack(anchor="w", pady=(8, 0))

        # ══════════════════════════════════════════════════════════════
        # 7. コスト＆ログ
        # ══════════════════════════════════════════════════════════════
        cost_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=10)
        cost_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            cost_card, text="💰 コスト",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MaterialColors.ON_SURFACE
        ).pack(anchor="w", padx=14, pady=(10, 4))

        self.cost_label = ctk.CTkLabel(
            cost_card, text="生成後に表示",
            font=ctk.CTkFont(family="Consolas", size=11), text_color=MaterialColors.ON_SURFACE_VARIANT, justify="left"
        )
        self.cost_label.pack(anchor="w", padx=14, pady=(0, 10))

        log_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=10)
        log_card.pack(fill="both", expand=True, pady=(0, 10))

        ctk.CTkLabel(
            log_card, text="📋 実行ログ",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MaterialColors.ON_SURFACE
        ).pack(anchor="w", padx=14, pady=(10, 4))

        self.log_text = ctk.CTkTextbox(
            log_card, height=130,
            fg_color=MaterialColors.INVERSE_SURFACE, text_color=MaterialColors.INVERSE_ON_SURFACE,
            corner_radius=6, font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.log_text.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        # フッター
        ctk.CTkLabel(
            content, text="⚠️ AI生成コンテンツ | 著作権はユーザー帰属 | 商用時は二次創作ガイドライン確認",
            font=ctk.CTkFont(size=9), text_color=MaterialColors.OUTLINE
        ).pack(pady=(0, 6))

        # Snackbar
        self.snackbar = Snackbar(self)

    def _set_concept_text(self, value: str):
        """コンセプトテキストを設定"""
        self.concept_text.delete("1.0", "end")
        if value:
            self.concept_text.insert("1.0", value)

    def _set_characters_text(self, value: str):
        """登場人物テキストを設定"""
        self.characters_text.delete("1.0", "end")
        if value:
            self.characters_text.insert("1.0", value)

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
        if self.config_data.get("characters"):
            self._set_characters_text(self.config_data["characters"])
        if self.config_data.get("num_scenes"):
            self.scenes_entry.delete(0, "end")
            self.scenes_entry.insert(0, str(self.config_data["num_scenes"]))
        if self.config_data.get("theme_jp"):
            self.theme_combo.set(self.config_data["theme_jp"])
        
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
                text=f"💰 予想コスト: ${est['estimated_usd']:.4f} (約¥{est['estimated_jpy']:.1f}) | "
                     f"Haiku: ~{est['haiku_tokens']:,}トークン, Sonnet: ~{est['sonnet_tokens']:,}トークン"
            )
        except ValueError:
            self.cost_preview_label.configure(
                text="💰 予想コスト: シーン数を入力してください"
            )

    def save_settings(self):
        """設定を保存"""
        theme_jp = self.theme_combo.get()
        self.config_data = {
            "api_key": self.api_field.get(),
            "concept": self.concept_text.get("1.0", "end-1c"),
            "characters": self.characters_text.get("1.0", "end-1c"),
            "num_scenes": int(self.scenes_entry.get() or "10"),
            "theme_jp": theme_jp,
            "theme": THEME_OPTIONS.get(theme_jp, ""),
        }
        save_config(self.config_data)
        self.snackbar.show("✅ 設定を保存しました", type="success")
        log_message("設定を保存しました")

    def get_current_config(self) -> dict:
        """現在の設定を辞書として取得"""
        theme_jp = self.theme_combo.get()
        return {
            "api_key": self.api_field.get(),
            "concept": self.concept_text.get("1.0", "end-1c"),
            "characters": self.characters_text.get("1.0", "end-1c"),
            "other_characters": self.other_chars_text.get("1.0", "end-1c") if hasattr(self, "other_chars_text") else "",
            "num_scenes": int(self.scenes_entry.get() or "10"),
            "theme_jp": theme_jp,
            "theme": THEME_OPTIONS.get(theme_jp, ""),
            "work_title": self.work_title_entry.get(),
            "char_name": self.char_name_entry.get(),
        }

    def apply_config(self, config: dict):
        """設定を画面に反映"""
        if config.get("api_key"):
            self._set_api_field(config["api_key"])
        if config.get("concept"):
            self._set_concept_text(config["concept"])
        if config.get("characters"):
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
            self.snackbar.show("❌ プロファイル名を入力してください", type="error")
            return
        
        # 上書き確認
        if name in get_profile_list():
            # 既存プロファイルを上書き
            pass  # 確認ダイアログは省略、直接上書き
        
        config = self.get_current_config()
        save_profile(name, config)
        self.refresh_profile_list()
        self.profile_combo.set(name)
        self.snackbar.show(f"✅ プロファイル '{name}' を保存しました", type="success")

    def load_selected_profile(self):
        """選択したプロファイルを読み込み"""
        name = self.profile_combo.get()
        if name == "（新規）":
            self.snackbar.show("⚠️ プロファイルを選択してください", type="warning")
            return
        
        config = load_profile(name)
        if config:
            self.apply_config(config)
            self.profile_name_entry.delete(0, "end")
            self.profile_name_entry.insert(0, name)
            self.snackbar.show(f"✅ プロファイル '{name}' を読み込みました", type="success")
            self.log(f"プロファイル読込: {name}")
        else:
            self.snackbar.show(f"❌ プロファイル '{name}' が見つかりません", type="error")

    def copy_selected_profile(self):
        """選択したプロファイルを複製"""
        src_name = self.profile_combo.get()
        if src_name == "（新規）":
            self.snackbar.show("⚠️ コピー元のプロファイルを選択してください", type="warning")
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
            self.snackbar.show(f"✅ '{src_name}' を '{dst_name}' にコピーしました", type="success")
        else:
            self.snackbar.show("❌ コピーに失敗しました", type="error")

    def delete_selected_profile(self):
        """選択したプロファイルを削除"""
        name = self.profile_combo.get()
        if name == "（新規）":
            self.snackbar.show("⚠️ 削除するプロファイルを選択してください", type="warning")
            return
        
        if delete_profile(name):
            self.refresh_profile_list()
            self.profile_combo.set("（新規）")
            self.profile_name_entry.delete(0, "end")
            self.snackbar.show(f"✅ プロファイル '{name}' を削除しました", type="success")
        else:
            self.snackbar.show("❌ 削除に失敗しました", type="error")

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        log_message(message)

    def update_status(self, message: str):
        self.status_label.configure(text=message)
        self.log(message)
        
        # フェーズインジケーター更新
        self.update_phase_indicator(message)

    def update_phase_indicator(self, message: str):
        """フェーズインジケーターを更新"""
        # リセット - 新構造: (pill, lbl)のタプル
        for pill, lbl in self.phase_labels:
            pill.configure(fg_color=MaterialColors.SURFACE_CONTAINER)
            lbl.configure(text_color=MaterialColors.ON_SURFACE_VARIANT)

        # 現在のフェーズをハイライト
        if "Phase 1" in message or "圧縮" in message:
            pill, lbl = self.phase_labels[0]
            pill.configure(fg_color=MaterialColors.PRIMARY)
            lbl.configure(text_color=MaterialColors.ON_PRIMARY)
            self.progress.set(0.15)
        elif "Phase 2" in message or "アウトライン" in message or "シーン" in message:
            # Phase 1 complete
            pill0, lbl0 = self.phase_labels[0]
            pill0.configure(fg_color=MaterialColors.SUCCESS)
            lbl0.configure(text_color=MaterialColors.ON_PRIMARY)
            # Phase 2 active
            pill1, lbl1 = self.phase_labels[1]
            pill1.configure(fg_color=MaterialColors.PRIMARY)
            lbl1.configure(text_color=MaterialColors.ON_PRIMARY)
            # シーン進捗を計算
            if "シーン" in message:
                import re
                match = re.search(r'(\d+)/(\d+)', message)
                if match:
                    current, total = int(match.group(1)), int(match.group(2))
                    progress = 0.3 + (current / total) * 0.5
                    self.progress.set(progress)
            else:
                self.progress.set(0.3)
        elif "Phase 3" in message or "品質" in message:
            for i in range(2):
                pill, lbl = self.phase_labels[i]
                pill.configure(fg_color=MaterialColors.SUCCESS)
                lbl.configure(text_color=MaterialColors.ON_PRIMARY)
            pill2, lbl2 = self.phase_labels[2]
            pill2.configure(fg_color=MaterialColors.PRIMARY)
            lbl2.configure(text_color=MaterialColors.ON_PRIMARY)
            self.progress.set(0.9)
        elif "完了" in message:
            for pill, lbl in self.phase_labels:
                pill.configure(fg_color=MaterialColors.SUCCESS)
                lbl.configure(text_color=MaterialColors.ON_PRIMARY)
            self.progress.set(1.0)

    def start_generation(self):
        if self.is_generating:
            return

        api_key = self.api_field.get().strip()
        concept = self.concept_text.get("1.0", "end-1c").strip()
        characters = self.characters_text.get("1.0", "end-1c").strip()

        if not api_key:
            self.snackbar.show("❌ APIキーを入力してください", type="error")
            return
        if not concept:
            self.snackbar.show("❌ コンセプトを入力してください", type="error")
            return

        try:
            num_scenes = int(self.scenes_entry.get())
            if num_scenes < 1 or num_scenes > 50:
                raise ValueError()
        except:
            self.snackbar.show("❌ シーン数は1〜50の整数で", type="error")
            return

        # Auto-save settings
        self.save_settings()

        # アウトラインプレビュー生成（ローカル・API不要）
        theme_jp = self.theme_combo.get()
        theme = THEME_OPTIONS.get(theme_jp, "")
        theme_guide = THEME_GUIDES.get(theme, THEME_GUIDES.get("vanilla", {}))
        theme_name = theme_guide.get("name", "指定なし")

        # 簡易コスト見積もり（新パイプライン: あらすじ+分割+シーン生成）
        act3_count = max(2, round(num_scenes * 0.40))
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
        self.log(f"📋 生成プレビュー")
        self.log(f"{'='*50}")
        self.log(f"テーマ: {theme_name}")
        self.log(f"シーン数: {num_scenes}")
        self.log(f"ストーリー構成: {theme_guide.get('story_arc', '導入→展開→本番→余韻')}")
        self.log(f"")
        self.log(f"📊 新パイプライン:")
        self.log(f"  Step 1: ストーリー原案作成（Haiku×1）")
        self.log(f"  Step 2: シーン分割（Haiku×1）")
        self.log(f"  Step 3: シーン生成")
        self.log(f"    Low (1-3): {low_count}シーン → Haiku")
        self.log(f"    High (4-5): {high_count}シーン → Sonnet")
        self.log(f"")
        self.log(f"💰 推定コスト: ${est_total:.4f}")
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
            args=(api_key, concept, characters, num_scenes),
            daemon=True
        )
        thread.start()

    def stop_generation(self):
        if self.is_generating:
            self.stop_requested = True
            self.update_status("⏹ 停止リクエスト送信...")
            self.stop_btn.configure(state="disabled", text="停止中...")

    def run_generation(self, api_key: str, concept: str, characters: str, num_scenes: int):
        try:
            theme_jp = self.theme_combo.get()
            theme = THEME_OPTIONS.get(theme_jp, "")

            def callback(msg):
                if self.stop_requested:
                    raise InterruptedError("ユーザーによる停止")
                self.after(0, lambda: self.update_status(msg))

            self.after(0, lambda: self.update_status("🚀 パイプライン開始..."))

            results, cost_tracker = generate_pipeline(
                api_key, concept, characters, num_scenes, theme, callback
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
            self.after(0, lambda: self.on_stopped())
        except Exception as e:
            self.after(0, lambda: self.on_error(str(e)))

    def reset_buttons(self):
        self.is_generating = False
        self.stop_requested = False
        self.generate_btn.configure(state="normal", text="脚本を生成")
        self.stop_btn.configure(
            state="disabled",
            text="⏹ 停止",
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
        self.update_status(f"✅ 完了! {len(results)}シーン生成")
        self.log(f"📄 CSV: {csv_path}")
        self.log(f"📄 JSON: {json_path}")
        if xlsx_path:
            self.log(f"📊 Excel: {xlsx_path}（折り返し表示対応）")
        self.log(f"💰 {cost_tracker.summary()}")
        self.snackbar.show(f"✅ {len(results)}シーン生成完了!", type="success")

    def on_stopped(self):
        self.reset_buttons()
        self.progress.set(0)
        self.update_status("⏹ 生成を停止しました")
        self.snackbar.show("⏹ 生成を停止しました", type="warning")

    def on_error(self, error: str):
        self.reset_buttons()
        self.progress.set(0)
        self.update_status(f"❌ エラー: {error}")
        self.snackbar.show(f"❌ エラー: {error[:50]}", type="error")

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

            # 登場人物フィールドに追加するテキスト（詳細版）
            char_text = f"【{name}】（{work}）\n"
            char_text += f"性格: {personality.get('brief_description', '')}\n"
            char_text += f"一人称: {speech.get('first_person', '私')}\n"
            char_text += f"語尾: {', '.join(speech.get('sentence_endings', [])[:4])}\n"
            char_text += f"外見: {physical.get('hair', '')}、{physical.get('eyes', '')}"

            current = self.characters_text.get("1.0", "end-1c")
            if current:
                self._set_characters_text(current + "\n\n" + char_text)
            else:
                self._set_characters_text(char_text)

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

            self.snackbar.show(f"✅ {name}を追加（ログに設定詳細）", type="success")

    def refresh_preset_list(self):
        """プリセット一覧を更新"""
        presets = get_preset_characters()
        self._preset_map = {}
        values = ["（プリセット選択）"]
        for p in presets:
            label = f"【{p.get('work_title', p.get('work', ''))}】{p.get('character_name', p.get('name', ''))}"
            self._preset_map[label] = p
            values.append(label)
        self.preset_dropdown.configure(values=values)
        self.preset_dropdown.set("（プリセット選択）")

    def on_preset_selected(self, choice: str):
        """プリセット選択時"""
        if choice == "（プリセット選択）" or choice not in self._preset_map:
            return
        info = self._preset_map[choice]
        work = info.get("work_title", info.get("work", ""))
        name = info.get("character_name", info.get("name", ""))
        # 作品名・キャラ名フィールドに自動入力
        self.work_title_entry.delete(0, "end")
        self.work_title_entry.insert(0, work)
        self.char_name_entry.delete(0, "end")
        self.char_name_entry.insert(0, name)
        self.log(f"プリセット選択: 【{work}】{name}")

    def load_preset_action(self):
        """プリセット読み込み"""
        current = self.preset_dropdown.get()
        if current == "（プリセット選択）" or current not in self._preset_map:
            self.snackbar.show("プリセットを選択してください", type="warning")
            return
        info = self._preset_map[current]
        char_id = info["char_id"]
        try:
            bible, _ = load_preset_character(char_id, callback=lambda msg: self.log(msg))
            self.refresh_char_list()
            name = bible.get("character_name", char_id)
            self.snackbar.show(f"✅ {name}をプリセットから読み込みました（API未使用）", type="success")
        except Exception as e:
            self.snackbar.show(f"❌ 読み込みエラー: {e}", type="error")

    def save_custom_character(self):
        """オリジナルキャラクターを保存"""
        name = self.custom_name_entry.get().strip()
        if not name:
            self.snackbar.show("キャラ名を入力してください", type="warning")
            return

        # shyness_levelの取得
        shyness_text = self.custom_shyness_dd.get()
        shyness_level = 3
        for label, val in SHYNESS_OPTIONS:
            if label == shyness_text:
                shyness_level = val
                break

        # その他の登場人物テキスト取得
        other_chars = ""
        if hasattr(self, "other_chars_text"):
            other_chars = self.other_chars_text.get("1.0", "end-1c").strip()

        bible = build_custom_character_data(
            char_name=name,
            age=self.custom_age_dd.get(),
            relationship=self.custom_rel_dd.get(),
            archetype=self.custom_archetype_dd.get(),
            first_person=self.custom_first_person_dd.get(),
            speech_style=self.custom_speech_dd.get(),
            hair_color=self.custom_hair_color_dd.get(),
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
        self.log(f"✅ オリジナルキャラ保存: {name} ({self.custom_archetype_dd.get()})")
        self.log(f"   性格: {bible['personality_core']['brief_description']}")
        self.log(f"   一人称: {bible['speech_pattern']['first_person']} / 口調: {self.custom_speech_dd.get()}")
        self.log(f"   外見: {bible['physical_description']['hair']}")
        self.snackbar.show(f"✅ {name}を保存しました（API未使用）", type="success")

    def start_char_generation(self):
        """キャラクター生成開始"""
        if self.is_generating:
            self.snackbar.show("⚠️ 生成中です", type="warning")
            return

        api_key = self.api_field.get().strip()
        work_title = self.work_title_entry.get().strip()
        char_name = self.char_name_entry.get().strip()

        if not api_key:
            self.snackbar.show("❌ APIキーを入力してください", type="error")
            return
        if not work_title:
            self.snackbar.show("❌ 作品名を入力してください", type="error")
            return
        if not char_name:
            self.snackbar.show("❌ キャラクター名を入力してください", type="error")
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
                callback=callback
            )

            self.after(0, lambda: self.on_char_complete(bible, char_id, cost_tracker))

        except Exception as e:
            self.after(0, lambda: self.on_char_error(str(e)))

    def on_char_complete(self, bible: dict, char_id: str, cost_tracker: CostTracker):
        """キャラ生成完了"""
        self.is_generating = False
        self.char_generate_btn.configure(state="normal", text="✨ キャラ生成")
        self.progress.set(1)

        self.cost_label.configure(text=cost_tracker.summary())
        self.update_status(f"✅ キャラ生成完了: {char_id}")
        self.log(f"📂 Bible: characters/{char_id}.json")
        self.log(f"📝 Skill: skills/characters/{char_id}.skill.md")
        self.snackbar.show(f"✅ {bible.get('character_name', '')} 生成完了!", type="success")

        # キャラ一覧を更新
        self.refresh_char_list()

    def on_char_error(self, error: str):
        """キャラ生成エラー"""
        self.is_generating = False
        self.char_generate_btn.configure(state="normal", text="✨ キャラ生成")
        self.progress.set(0)
        self.update_status(f"❌ エラー: {error}")
        self.snackbar.show(f"❌ エラー: {error[:50]}", type="error")


if __name__ == "__main__":
    app = App()
    app.mainloop()
