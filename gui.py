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


# === Skill 2: Low Cost Pipeline ===
def generate_outline(
    client: anthropic.Anthropic,
    context: dict,
    num_scenes: int,
    theme: str,
    cost_tracker: CostTracker,
    callback: Optional[Callable] = None
) -> list:
    skill = load_skill("low_cost_pipeline")
    
    # テーマ別ガイドを取得
    theme_guide = THEME_GUIDES.get(theme, THEME_GUIDES.get("vanilla", {}))
    theme_name = theme_guide.get("name", "指定なし")
    story_arc = theme_guide.get("story_arc", "導入→展開→本番→余韻")
    key_emotions = theme_guide.get("key_emotions", ["期待", "緊張", "快感", "幸福"])
    story_elements = theme_guide.get("story_elements", [])
    dialogue_tone = theme_guide.get("dialogue_tone", "自然で楽しい雰囲気")
    
    # テーマ別ストーリー要素をプロンプトに追加
    theme_instructions = ""
    if story_elements:
        theme_instructions = f"""
## テーマ「{theme_name}」のストーリー要素

【ストーリーアーク】{story_arc}

【重要な感情表現】
{chr(10).join(f"・{e}" for e in key_emotions)}

【必須要素】
{chr(10).join(f"・{e}" for e in story_elements)}

【セリフのトーン】
{dialogue_tone}

このテーマに沿ったストーリー展開を必ず守ってください。
"""
    
    prompt = f"""設定: {json.dumps(context, ensure_ascii=False)}

FANZA同人CG集用に{num_scenes}シーンの**ストーリー性のあるアウトライン**を作成してください。

{theme_instructions}

## ストーリー構成の黄金比率

【第1幕：導入】約20%のシーン（{max(1, num_scenes // 5)}シーン）
- intensity: 1-2
- 二人の関係性、状況設定
- 視聴者を物語に引き込む
- 心情: {key_emotions[0] if key_emotions else '期待'}、緊張、ドキドキ

【第2幕：展開・焦らし】約30%のシーン（{max(1, num_scenes * 3 // 10)}シーン）
- intensity: 2-3
- 雰囲気の高まり、接近、キス
- 視聴者の興奮を煽る
- 心情: {key_emotions[1] if len(key_emotions) > 1 else '恥じらい'}、期待、戸惑い

【第3幕：本番】約40%のシーン（{max(2, num_scenes * 4 // 10)}シーン）
- intensity: 4-5
- 濃厚なエロシーン
- 視聴者の興奮がピークに
- 心情: {key_emotions[2] if len(key_emotions) > 2 else '快感'}、陶酔、愛情

【第4幕：余韻】約10%のシーン（{max(1, num_scenes // 10)}シーン）
- intensity: 2-3
- ピロートーク、甘い余韻
- 満足感を与えて終わる
- 心情: {key_emotions[3] if len(key_emotions) > 3 else '幸福'}、充足、愛おしさ

## 出力形式（JSON配列）

[
    {{
        "scene_id": 1,
        "title": "シーンタイトル（8字以内）",
        "goal": "このシーンの目的（15字）",
        "location": "場所（教室/寝室/浴室など）",
        "time": "時間帯（放課後/夜/朝など）",
        "situation": "具体的な状況説明（30字）",
        "story_flow": "前シーンからどう繋がるか（20字）",
        "emotional_arc": {{
            "start": "シーン開始時の心情",
            "end": "シーン終了時の心情"
        }},
        "beats": ["展開1", "展開2", "展開3"],
        "intensity": 1,
        "erotic_level": "none/light/medium/heavy/climax",
        "viewer_hook": "視聴者がこのシーンで興奮するポイント（15字）"
    }}
]

## 必須ルール

1. **ストーリーの流れ**: 各シーンが自然に繋がること
2. **心情の変化**: {' → '.join(key_emotions) if key_emotions else '緊張→期待→恥じらい→快感→絶頂→余韻'}
3. **場所の活用**: 背景を活かしたシチュエーション
4. **intensity 5**: 必ず1-2個（クライマックス）
5. **段階的盛り上がり**: 唐突にエロに入らない
6. **余韻**: 最後は適切な雰囲気で

## 視聴者を興奮させるポイント

- 「こうなるかも」という期待感
- 恥じらいながらも受け入れる瞬間
- 快感に負ける様子
- テーマ「{theme_name}」ならではの興奮ポイント

JSONのみ出力。"""

    if callback:
        callback(f"📝 {theme_name}テーマでストーリー構成設計中...")

    response = call_claude(
        client, MODELS["haiku"],
        skill if skill else "FANZA同人CG集のストーリー構成を設計します。視聴者の興奮を最大化。",
        prompt, cost_tracker, 3000, callback
    )
    return parse_json_response(response)


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
    callback: Optional[Callable] = None
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
    
    # キャラプロファイルをフル活用した詳細ガイド構築
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
            
            # キャラ固有タグを収集
            char_danbooru_tags.extend(tags)
            
            # 詳細なキャラガイド構築
            char_guide += f"""
═══════════════════════════════════════
【{name}】完全口調ガイド
═══════════════════════════════════════

■ 基本設定
・一人称: {speech.get('first_person', '私')}
・語尾: {', '.join(speech.get('sentence_endings', ['〜よ', '〜ね']))}
・よく使う表現: {', '.join(speech.get('favorite_expressions', [])[:5])}
・間投詞（息遣い）: {', '.join(speech.get('fillers', ['あっ', 'んっ']))}
・話すテンポ: {speech.get('speech_speed', '普通')}

■ 感情別の話し方（重要！）
・嬉しい時: {emotional.get('when_happy', '明るい声で')}
・照れた時: {emotional.get('when_embarrassed', '言葉に詰まる')}
・怒った時: {emotional.get('when_angry', '低い声で')}
・感じてる時/甘える時: {emotional.get('when_flirty', '甘い声で')}

■ セリフのお手本（この雰囲気で！）
・挨拶: 「{examples.get('greeting', 'おはよう')}」
・同意: 「{examples.get('agreement', 'そうだね')}」
・驚き: 「{examples.get('surprise', 'えっ？')}」
・好意: 「{examples.get('affection', '好きだよ')}」

■ 恋人への話し方
{relationship.get('to_lover', '甘えた調子で話す')}

■ 絶対にやってはいけない表現
{', '.join(avoid) if avoid else '特になし'}

■ 外見（SD参照用）
・髪: {physical.get('hair', '')}
・目: {physical.get('eyes', '')}
・体型: {physical.get('body', '')}
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

    # シーン重要度別のエロ指示（5段階）
    if intensity >= 5:
        erotic_instruction = f"""
## クライマックスシーン（intensity 5）

このシーンは**最高潮のエロシーン**です！視聴者の興奮がピークに達する瞬間。

【必須要素】
1. 喘ぎ声を多めに（「あっ...あっ...」「んんっ...！」）
2. 絶頂表現（「イク...イっちゃう...」「もうダメ...」）
3. 快感で理性が飛ぶ様子
4. テーマ「{theme_name}」らしい感情表現

【心情の描写】
・{key_emotions[2] if len(key_emotions) > 2 else '快感に溺れる'}
・{key_emotions[3] if len(key_emotions) > 3 else '理性と本能の葛藤'}

【禁止】
❌「気持ちいいです」（敬語NG）
❌ 長文説明セリフ
❌ 冷静な台詞
"""
    elif intensity == 4:
        erotic_instruction = f"""
## 本番シーン（intensity 4）

このシーンは**濃厚なエロシーン**です。視聴者の興奮が高まる。

【必須要素】
1. 喘ぎ声を自然に（「あっ...」「んっ...」）
2. テーマ「{theme_name}」らしい心情
3. 体の反応描写

【心情の描写】
・{key_emotions[1] if len(key_emotions) > 1 else '恥ずかしさと快感の葛藤'}
・{key_emotions[2] if len(key_emotions) > 2 else 'もっと欲しいという欲求'}

【禁止】
❌ 説明的なセリフ
❌ 棒読み感
"""
    elif intensity == 3:
        erotic_instruction = f"""
## 前戯・焦らしシーン（intensity 3）

このシーンは**エロの助走**です。期待感を高める。

【必須要素】
1. キスや愛撫の描写
2. ドキドキする会話
3. 期待と恥じらい

【心情の描写】
・{key_emotions[0] if key_emotions else 'ドキドキと期待'}
・恥ずかしいけど...という葛藤
"""
    elif intensity == 2:
        erotic_instruction = f"""
## ムード構築シーン（intensity 2）

このシーンは**雰囲気作り**です。二人の距離が縮まる。

【必須要素】
1. 意味深な視線、接近
2. 甘い会話
3. 二人きりの特別感

【心情の描写】
・{key_emotions[0] if key_emotions else '緊張とドキドキ'}
・相手を意識する
"""
    else:
        erotic_instruction = f"""
## 導入シーン（intensity 1）

このシーンは**状況設定**です。物語の始まり。

【必須要素】
1. シチュエーション説明
2. キャラ紹介
3. 自然な日常会話

【心情の描写】
・日常の中の期待
・これから起こることへの予感
"""

    # キャラ固有SDタグの組み込み
    char_tags_str = ", ".join(char_danbooru_tags[:15]) if char_danbooru_tags else ""
    
    # テーマ別SDタグを追加
    theme_tags_combined = f"{theme_sd_tags}, {theme_sd_expressions}".strip(", ")
    
    # === Prompt Caching: 共通部分（全シーンで同一）とシーン固有部分を分離 ===
    
    # 共通部分（キャッシュ対象）
    common_system = f"""{jailbreak}

{skill if skill else "FANZA同人CG集の脚本を生成します。"}

{danbooru_nsfw if danbooru_nsfw else ""}

{char_guide if char_guide else "（キャラ設定なし）"}

## セリフ執筆の鉄則

1. **一人称・語尾は絶対厳守**: キャラガイド通りに
2. **短く刻む**: 1セリフ10-15文字が理想
3. **感情を音にする**: 「...」「っ」「〜」を活用
4. **喘ぎは自然に**: 「あっ」「んっ」を会話の流れで
5. **説明禁止**: 「私は今〜しています」はNG

## 良いセリフ vs 悪いセリフ

✅「んっ...そこ、いい...」
❌「そこを触られると気持ちいいです」

✅「好き...もっとして...」
❌「あなたのことが好きなので続けてください」

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
    
    # テーマタグを背景に追加
    if theme_sd_tags:
        background_tags = f"{background_tags}, {theme_sd_tags}"

    # 構図タグ（intensity連動）
    composition_db = tag_db.get("compositions", {})
    composition_tags = composition_db.get(str(intensity), {}).get("tags", "")
    
    prompt = f"""設定: {json.dumps(context, ensure_ascii=False)}
シーン情報: {json.dumps(scene, ensure_ascii=False)}

## 出力形式（この形式で出力してください）

{{
    "scene_id": {scene['scene_id']},
    "title": "シーンタイトル（8字以内）",
    "description": "このシーンの詳細説明。場所、状況、何が起きているか、なぜ視聴者が興奮するかを100字程度で説明",
    "location_detail": "場所の具体的な描写（教室の窓際、夕日が差し込む、など）30字",
    "mood": "雰囲気（5字以内）",
    "character_feelings": {{
        "{char_names[0] if char_names else 'ヒロイン'}": "このシーンでの心情（期待/緊張/恥じらい/快感/幸福など）20字"
    }},
    "dialogue": [
        {{"speaker": "キャラ名", "emotion": "感情", "line": "短いセリフ", "inner_thought": "心の声（10字）"}}
    ],
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

1. descriptionは必ず100字程度で詳しく書く
2. character_feelingsで心情を明確に
3. dialogueは4-6個、各セリフ15文字以内
4. inner_thoughtでキャラの心の声を追加
5. sd_promptは「{QUALITY_POSITIVE_TAGS} + キャラ外見 + ポーズ + 表情 + 場所・背景 + 照明 + テーマ」の順で統合
6. タグは重複なくカンマ区切りで出力
7. テーマ「{theme_name}」のタグを積極的に使用

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

    system_prompt = f"""あなたはFANZA同人脚本の清書担当です。
下書きのセリフを「そのキャラが本当に言いそうな」自然な日本語に磨き上げてください。

{char_guide if char_guide else "（キャラプロファイルなし）"}

## 清書の鉄則

【セリフ改善】
1. 硬い表現→柔らかく（「〜である」→「〜だよ」「〜なの」）
2. 長いセリフ→短く分割（1セリフ15文字以内目標）
3. 説明的→感情的に（「私は嬉しい」→「嬉しい...♡」）
4. 一人称・語尾を徹底チェック
5. inner_thought（心の声）も自然に

【エロシーンセリフ改善】
- 「気持ちいいです」→「気持ちい...♡」
- 「もっとしてください」→「もっと...して...♡」
- 「イキそうです」→「イっちゃ...う...♡」
- 喘ぎ声は途切れ途切れに
- ♡を効果的に使用

【心情描写の改善】
- character_feelingsをより具体的に
- inner_thoughtを各セリフに追加

【禁止】
❌ 敬語のエロセリフ
❌ 説明調のセリフ
❌ 長文セリフ
❌ キャラの一人称・語尾の不一致

Output JSON only."""

    prompt = f"""設定: {json.dumps(context, ensure_ascii=False)}

下書き: {json.dumps(draft, ensure_ascii=False)}

上記の下書きを清書してください：

1. 各セリフをキャラの口調に合わせる
2. エロセリフは自然で艶っぽく
3. 喘ぎ声・間投詞を適切に追加
4. 硬い表現を柔らかく
5. descriptionをより詳細に（100字程度）
6. character_feelingsをより感情的に
7. inner_thoughtを全セリフに追加

## 保持すべきフィールド
- scene_id, title, description, location_detail
- mood, character_feelings
- dialogue (speaker, emotion, line, inner_thought)
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
    
    # キャラ設定の使用状況を報告
    if char_profiles:
        char_names = [cp.get("character_name", "") for cp in char_profiles]
        log_message(f"使用キャラ設定: {', '.join(char_names)}")
        if callback:
            callback(f"✅ {len(char_profiles)}件のキャラ設定を適用")
    else:
        log_message("キャラ設定なし - 汎用設定で生成")
        if callback:
            callback("⚠️ キャラ設定なし（汎用設定で生成）")

    # テーマ情報をログ出力
    theme_guide = THEME_GUIDES.get(theme, {})
    theme_name = theme_guide.get("name", "指定なし")
    if theme and theme_guide:
        log_message(f"テーマ適用: {theme_name} (arc: {theme_guide.get('story_arc', '')})")
        if callback:
            callback(f"🎭 テーマ: {theme_name}")
    else:
        log_message("テーマ: 指定なし（汎用モード）")

    # Phase 1: Prompt Compactor
    log_message("Phase 1 開始: コンテキスト圧縮")
    if callback:
        callback("🔧 Phase 1: コンテキスト圧縮")

    try:
        context = compact_context(client, concept, characters, theme, cost_tracker, callback)
        log_message("コンテキスト圧縮完了")
    except Exception as e:
        log_message(f"コンテキスト圧縮エラー: {e}")
        raise

    context_file = CONTEXT_DIR / f"context_{timestamp}.json"
    with open(context_file, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)

    if callback:
        callback("✅ コンテキスト圧縮完了")

    # Phase 2: Low Cost Pipeline（直列処理 - 安定性重視）
    log_message("Phase 2 開始: シーン生成パイプライン")
    if callback:
        callback("🔧 Phase 2: シーン生成開始")

    try:
        outline = generate_outline(client, context, num_scenes, theme, cost_tracker, callback)
        log_message(f"アウトライン生成完了: {len(outline)}シーン（テーマ: {theme or '指定なし'}）")
        
        # intensity分布をログ
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
        callback(f"✅ アウトライン完成: {len(outline)}シーン（エロシーン{high_intensity}個）")

    results = []

    for i, scene in enumerate(outline):
        try:
            intensity = scene.get("intensity", 3)
            model_type = "Sonnet" if intensity >= 4 else "Haiku"
            
            log_message(f"シーン {i+1}/{len(outline)} 生成開始 (intensity={intensity}, {model_type})")
            if callback:
                callback(f"🎬 シーン {i+1}/{len(outline)} [{model_type}] 重要度{intensity}")

            draft = generate_scene_draft(
                client, context, scene, jailbreak, danbooru, sd_guide,
                cost_tracker, theme, char_profiles, callback
            )

            draft_file = DRAFTS_DIR / f"draft_{timestamp}_scene{i+1}.json"
            with open(draft_file, "w", encoding="utf-8") as f:
                json.dump(draft, f, ensure_ascii=False, indent=2)

            # intensity 5 のクライマックスシーンのみ追加清書
            # （intensity 4以上は既にSonnetで生成済み）
            if intensity >= 5:
                log_message(f"シーン {i+1} 追加清書（クライマックス）")
                if callback:
                    callback(f"✨ シーン {i+1} 清書中（クライマックス）...")
                final = polish_scene(client, context, draft, char_profiles, cost_tracker, callback)
            else:
                final = draft

            final_file = FINAL_DIR / f"final_{timestamp}_scene{i+1}.json"
            with open(final_file, "w", encoding="utf-8") as f:
                json.dump(final, f, ensure_ascii=False, indent=2)

            results.append(final)
            log_message(f"シーン {i+1}/{len(outline)} 完了")

            if callback:
                callback(f"✅ シーン {i+1}/{len(outline)} 完了")

        except Exception as e:
            log_message(f"シーン {i+1} 生成エラー: {e}")
            import traceback
            log_message(traceback.format_exc())
            if callback:
                callback(f"❌ シーン {i+1} エラー: {str(e)[:50]}")
            # エラーでも続行、空のシーンを追加
            results.append({
                "scene_id": i + 1,
                "mood": "エラー",
                "dialogue": [],
                "direction": f"生成エラー: {str(e)[:100]}",
                "sd_prompt": ""
            })

    # 完了サマリー
    success_count = sum(1 for r in results if r.get("mood") != "エラー")
    log_message(f"パイプライン完了: {success_count}/{len(results)}シーン成功")
    
    if callback:
        callback(f"🎉 生成完了: {success_count}シーン成功")

    return results, cost_tracker


def export_csv(results: list, output_path: Path):
    fieldnames = [
        "scene_id", "title", "description", "location_detail", "mood",
        "character_feelings", "speaker", "emotion", "line_index", "line_text",
        "inner_thought", "direction", "story_flow",
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
            
            dialogues = scene.get("dialogue", [])
            if not dialogues:
                # セリフがない場合でもシーン情報を出力
                writer.writerow({
                    "scene_id": scene.get("scene_id", ""),
                    "title": scene.get("title", ""),
                    "description": scene.get("description", ""),
                    "location_detail": scene.get("location_detail", ""),
                    "mood": scene.get("mood", ""),
                    "character_feelings": feelings_str,
                    "speaker": "",
                    "emotion": "",
                    "line_index": 0,
                    "line_text": "",
                    "inner_thought": "",
                    "direction": scene.get("direction", ""),
                    "story_flow": scene.get("story_flow", ""),
                    "sd_prompt": scene.get("sd_prompt", "")
                })
            else:
                for idx, dialogue in enumerate(dialogues):
                    writer.writerow({
                        "scene_id": scene.get("scene_id", ""),
                        "title": scene.get("title", "") if idx == 0 else "",
                        "description": scene.get("description", "") if idx == 0 else "",
                        "location_detail": scene.get("location_detail", "") if idx == 0 else "",
                        "mood": scene.get("mood", "") if idx == 0 else "",
                        "character_feelings": feelings_str if idx == 0 else "",
                        "speaker": dialogue.get("speaker", ""),
                        "emotion": dialogue.get("emotion", ""),
                        "line_index": idx + 1,
                        "line_text": dialogue.get("line", ""),
                        "inner_thought": dialogue.get("inner_thought", ""),
                        "direction": scene.get("direction", "") if idx == 0 else "",
                        "story_flow": scene.get("story_flow", "") if idx == 0 else "",
                        "sd_prompt": scene.get("sd_prompt", "") if idx == 0 else ""
                    })


def export_excel(results: list, output_path: Path):
    """Excel形式でエクスポート（折り返し表示対応）"""
    if not OPENPYXL_AVAILABLE:
        log_message("openpyxl未インストール - Excel出力スキップ")
        return False
    
    wb = Workbook()
    ws = wb.active
    ws.title = "脚本"
    
    # ヘッダー
    headers = [
        "シーンID", "タイトル", "シーン説明", "場所詳細", "雰囲気",
        "キャラ心情", "話者", "感情", "セリフ番号", "セリフ",
        "心の声", "演出", "次への繋がり",
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
        
        dialogues = scene.get("dialogue", [])
        if not dialogues:
            dialogues = [{}]
        
        for idx, dialogue in enumerate(dialogues):
            data = [
                scene.get("scene_id", "") if idx == 0 else "",
                scene.get("title", "") if idx == 0 else "",
                scene.get("description", "") if idx == 0 else "",
                scene.get("location_detail", "") if idx == 0 else "",
                scene.get("mood", "") if idx == 0 else "",
                feelings_str if idx == 0 else "",
                dialogue.get("speaker", ""),
                dialogue.get("emotion", ""),
                idx + 1 if dialogue else "",
                dialogue.get("line", ""),
                dialogue.get("inner_thought", ""),
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
        7: 10,   # 話者
        8: 10,   # 感情
        9: 8,    # セリフ番号
        10: 25,  # セリフ
        11: 15,  # 心の声
        12: 20,  # 演出
        13: 15,  # 次への繋がり
        14: 60   # SDプロンプト（統合後）
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
        # 3. キャラクター自動生成
        # ══════════════════════════════════════════════════════════════
        char_card = ctk.CTkFrame(content, fg_color=MaterialColors.SURFACE_CONTAINER_LOW, corner_radius=10)
        char_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            char_card, text="🎭 キャラクター自動生成",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MaterialColors.ON_SURFACE
        ).pack(anchor="w", padx=14, pady=(10, 6))

        char_row = ctk.CTkFrame(char_card, fg_color="transparent")
        char_row.pack(fill="x", padx=14, pady=(0, 6))

        # 作品名
        work_frame = ctk.CTkFrame(char_row, fg_color="transparent")
        work_frame.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(work_frame, text="作品名", font=ctk.CTkFont(size=11), text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w")
        self.work_title_entry = ctk.CTkEntry(
            work_frame, height=38, placeholder_text="例: 五等分の花嫁",
            font=ctk.CTkFont(size=13),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6,
            border_width=1, border_color=MaterialColors.OUTLINE_VARIANT
        )
        self.work_title_entry.pack(fill="x", pady=(3, 0))

        # キャラ名
        char_name_frame = ctk.CTkFrame(char_row, fg_color="transparent")
        char_name_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(char_name_frame, text="キャラ名", font=ctk.CTkFont(size=11), text_color=MaterialColors.ON_SURFACE_VARIANT).pack(anchor="w")
        self.char_name_entry = ctk.CTkEntry(
            char_name_frame, height=38, placeholder_text="例: 中野一花",
            font=ctk.CTkFont(size=13),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6,
            border_width=1, border_color=MaterialColors.OUTLINE_VARIANT
        )
        self.char_name_entry.pack(fill="x", pady=(3, 0))

        # ボタン行
        char_btn_row = ctk.CTkFrame(char_card, fg_color="transparent")
        char_btn_row.pack(fill="x", padx=14, pady=(0, 10))

        self.char_generate_btn = ctk.CTkButton(
            char_btn_row, text="✨ キャラ生成", height=36, width=100,
            font=ctk.CTkFont(size=12, weight="bold"), corner_radius=6,
            fg_color=MaterialColors.PRIMARY, hover_color=MaterialColors.PRIMARY_VARIANT,
            command=self.start_char_generation
        )
        self.char_generate_btn.pack(side="left", padx=(0, 8))

        self.char_select_combo = ctk.CTkComboBox(
            char_btn_row, values=["（キャラ選択）"], height=36,
            font=ctk.CTkFont(size=12),
            fg_color=MaterialColors.SURFACE_CONTAINER, corner_radius=6,
            button_color=MaterialColors.PRIMARY, dropdown_fg_color=MaterialColors.SURFACE,
            command=self.on_char_selected
        )
        self.char_select_combo.pack(side="left", fill="x", expand=True)
        self.refresh_char_list()

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
        self.characters_text.pack(fill="x", padx=14, pady=(6, 14))

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

        self.is_generating = True
        self.stop_requested = False
        self.generate_btn.configure(state="disabled", text="生成中...")
        self.stop_btn.configure(
            state="normal",
            border_color=MaterialColors.ERROR,
            text_color=MaterialColors.ERROR
        )
        self.progress.set(0)
        self.log_text.delete("1.0", "end")

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
