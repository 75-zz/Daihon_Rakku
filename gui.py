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

try:
    import anthropic
except ImportError:
    print("Error: anthropic library is required. Run: pip install anthropic")
    sys.exit(1)


# === Material Design 3 カラーパレット ===
class MaterialColors:
    # Dark Theme
    BACKGROUND = "#121212"
    SURFACE = "#1E1E1E"
    SURFACE_VARIANT = "#2D2D2D"
    PRIMARY = "#BB86FC"
    PRIMARY_VARIANT = "#9A67EA"
    SECONDARY = "#03DAC6"
    ERROR = "#CF6679"
    SUCCESS = "#4CAF50"
    WARNING = "#FFC107"
    ON_BACKGROUND = "#E1E1E1"
    ON_SURFACE = "#FFFFFF"
    ON_PRIMARY = "#000000"
    OUTLINE = "#3D3D3D"


# === 設定 ===
MAX_RETRIES = 3
RETRY_DELAY = 2
OUTPUT_DIR = Path(__file__).parent
SKILLS_DIR = OUTPUT_DIR / "skills"
JAILBREAK_FILE = OUTPUT_DIR / "jailbreak.md"
DANBOORU_TAGS_FILE = OUTPUT_DIR / "danbooru_tags.md"
SD_PROMPT_GUIDE_FILE = OUTPUT_DIR / "sd_prompt_guide.md"
CONFIG_FILE = OUTPUT_DIR / "config.json"
LOG_FILE = OUTPUT_DIR / "log.txt"
CONTEXT_DIR = OUTPUT_DIR / "context"
DRAFTS_DIR = OUTPUT_DIR / "drafts"
FINAL_DIR = OUTPUT_DIR / "final"
EXPORTS_DIR = OUTPUT_DIR / "exports"

# ディレクトリ作成
for d in [CONTEXT_DIR, DRAFTS_DIR, FINAL_DIR, EXPORTS_DIR]:
    d.mkdir(exist_ok=True)

# モデル設定
MODELS = {
    "haiku": "claude-3-5-haiku-20241022",
    "sonnet": "claude-sonnet-4-20250514",
}

# コスト（USD per 1M tokens）
COSTS = {
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
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

DEFAULT_NEGATIVE_PROMPT = "worst_quality, low_quality, lowres, bad_anatomy, bad_hands, missing_fingers, extra_fingers, mutated_hands, poorly_drawn_face, ugly, deformed, blurry, text, watermark, signature, censored, mosaic_censoring, loli, shota, child"


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


def log_message(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


# === API呼び出し ===
def call_claude(
    client: anthropic.Anthropic,
    model: str,
    system: str,
    user: str,
    cost_tracker: CostTracker,
    max_tokens: int = 4096,
    callback: Optional[Callable] = None
) -> str:
    for attempt in range(MAX_RETRIES):
        try:
            if callback:
                model_name = "Haiku" if "haiku" in model else "Sonnet"
                callback(f"API呼び出し中 ({model_name})...")

            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}]
            )

            usage = response.usage
            cost_tracker.add(model, usage.input_tokens, usage.output_tokens)
            log_message(f"{model}: {usage.input_tokens} in, {usage.output_tokens} out")

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
                time.sleep(RETRY_DELAY)
            else:
                raise

        except Exception as e:
            log_message(f"Error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise

    raise RuntimeError("最大リトライ回数を超えました")


def parse_json_response(text: str):
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
    return json.loads(text.strip())


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
    cost_tracker: CostTracker,
    callback: Optional[Callable] = None
) -> list:
    skill = load_skill("low_cost_pipeline")
    prompt = f"""設定: {json.dumps(context, ensure_ascii=False)}

{num_scenes}シーンのアウトラインを作成。

出力形式（JSON配列）:
[
    {{"scene_id": 1, "goal": "目的", "beats": ["展開1", "展開2"], "intensity": 1-5}}
]

- intensity: シーンの重要度（5=クライマックス）
- 箇条書きで簡潔に
- JSONのみ出力"""

    if callback:
        callback("📝 アウトライン生成中...")

    response = call_claude(
        client, MODELS["haiku"],
        skill if skill else "You generate story outlines efficiently.",
        prompt, cost_tracker, 2048, callback
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
    callback: Optional[Callable] = None
) -> dict:
    skill = load_skill("low_cost_pipeline")
    prompt = f"""{jailbreak}

設定: {json.dumps(context, ensure_ascii=False)}
シーン: {json.dumps(scene, ensure_ascii=False)}

Danbooruタグ参考: {danbooru[:1500]}
SD Guide: {sd_guide[:1500]}

出力形式（JSON）:
{{
    "scene_id": {scene['scene_id']},
    "mood": "雰囲気（短文）",
    "dialogue": [
        {{"speaker": "名前", "emotion": "感情", "line": "セリフ"}}
    ],
    "direction": "ト書き（短文）",
    "sd_prompt": "danbooru, tags, here",
    "negative_prompt": "{DEFAULT_NEGATIVE_PROMPT}"
}}

全キャラ成人。JSONのみ出力。"""

    response = call_claude(
        client, MODELS["haiku"],
        skill if skill else "You generate scene drafts efficiently.",
        prompt, cost_tracker, 2048, callback
    )
    return parse_json_response(response)


def polish_scene(
    client: anthropic.Anthropic,
    context: dict,
    draft: dict,
    cost_tracker: CostTracker,
    callback: Optional[Callable] = None
) -> dict:
    prompt = f"""設定: {json.dumps(context, ensure_ascii=False)}

下書き: {json.dumps(draft, ensure_ascii=False)}

清書ルール:
1. 口調・キャラ一貫性
2. セリフを自然に
3. ト書きは簡潔
4. sd_promptはDanbooruタグ維持

同じJSON形式で出力。JSONのみ。"""

    response = call_claude(
        client, MODELS["sonnet"],
        "You polish scripts for quality and consistency. Output JSON only.",
        prompt, cost_tracker, 2048, callback
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
    callback: Optional[Callable] = None
) -> tuple[list, CostTracker]:
    client = anthropic.Anthropic(api_key=api_key)
    cost_tracker = CostTracker()

    jailbreak = load_file(JAILBREAK_FILE)
    danbooru = load_file(DANBOORU_TAGS_FILE)
    sd_guide = load_file(SD_PROMPT_GUIDE_FILE)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Phase 1: Prompt Compactor
    if callback:
        callback("🔧 Phase 1: コンテキスト圧縮")

    context = compact_context(client, concept, characters, theme, cost_tracker, callback)

    context_file = CONTEXT_DIR / f"context_{timestamp}.json"
    with open(context_file, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)

    if callback:
        callback("✅ コンテキスト圧縮完了")

    # Phase 2: Low Cost Pipeline
    if callback:
        callback("🔧 Phase 2: 低コスト生成パイプライン")

    outline = generate_outline(client, context, num_scenes, cost_tracker, callback)

    if callback:
        callback(f"✅ アウトライン完成: {len(outline)}シーン")

    results = []

    for i, scene in enumerate(outline):
        if callback:
            callback(f"🎬 シーン {i+1}/{len(outline)} 生成中...")

        draft = generate_scene_draft(
            client, context, scene, jailbreak, danbooru, sd_guide,
            cost_tracker, callback
        )

        draft_file = DRAFTS_DIR / f"draft_{timestamp}_scene{i+1}.json"
        with open(draft_file, "w", encoding="utf-8") as f:
            json.dump(draft, f, ensure_ascii=False, indent=2)

        intensity = scene.get("intensity", 3)
        if intensity >= 4:
            if callback:
                callback(f"✨ シーン {i+1} 清書中（重要度{intensity}）...")
            final = polish_scene(client, context, draft, cost_tracker, callback)
        else:
            final = draft

        final_file = FINAL_DIR / f"final_{timestamp}_scene{i+1}.json"
        with open(final_file, "w", encoding="utf-8") as f:
            json.dump(final, f, ensure_ascii=False, indent=2)

        results.append(final)

        if callback:
            callback(f"✅ シーン {i+1} 完了")

    # Phase 3: Quality Supervisor
    if callback:
        callback("🔧 Phase 3: 品質チェック")

    quality_result = check_quality(client, context, results, cost_tracker, callback)

    if quality_result.get("has_problems", False):
        problems = quality_result.get("problems", [])
        fixes = quality_result.get("fix_instructions", [])

        if callback:
            callback(f"⚠️ {len(problems)}件の問題を検出、修正中...")

        for fix in fixes:
            scene_id = fix.get("scene_id")
            instruction = fix.get("instruction", "")

            if scene_id and 1 <= scene_id <= len(results):
                if callback:
                    callback(f"🔧 シーン {scene_id} 修正中...")

                fixed = apply_fix(client, results[scene_id - 1], instruction, cost_tracker, callback)
                results[scene_id - 1] = fixed

                fix_file = FINAL_DIR / f"fixed_{timestamp}_scene{scene_id}.json"
                with open(fix_file, "w", encoding="utf-8") as f:
                    json.dump(fixed, f, ensure_ascii=False, indent=2)

        if callback:
            callback("✅ 差分修正完了")
    else:
        if callback:
            callback("✅ 品質チェックOK（問題なし）")

    return results, cost_tracker


def export_csv(results: list, output_path: Path):
    fieldnames = [
        "scene_id", "mood", "speaker", "emotion", "line_index", "line_text",
        "direction", "sd_prompt", "negative_prompt"
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for scene in results:
            for idx, dialogue in enumerate(scene.get("dialogue", [])):
                writer.writerow({
                    "scene_id": scene.get("scene_id", ""),
                    "mood": scene.get("mood", ""),
                    "speaker": dialogue.get("speaker", ""),
                    "emotion": dialogue.get("emotion", ""),
                    "line_index": idx + 1,
                    "line_text": dialogue.get("line", ""),
                    "direction": scene.get("direction", ""),
                    "sd_prompt": scene.get("sd_prompt", ""),
                    "negative_prompt": scene.get("negative_prompt", DEFAULT_NEGATIVE_PROMPT)
                })


def export_json(results: list, output_path: Path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


# === Material Design GUI ===
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MaterialCard(ctk.CTkFrame):
    """Material Design Card Component"""
    def __init__(self, master, title: str = "", **kwargs):
        super().__init__(
            master,
            fg_color=MaterialColors.SURFACE,
            corner_radius=16,
            border_width=1,
            border_color=MaterialColors.OUTLINE,
            **kwargs
        )

        if title:
            self.title_label = ctk.CTkLabel(
                self,
                text=title,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=MaterialColors.ON_SURFACE
            )
            self.title_label.pack(anchor="w", padx=16, pady=(16, 8))

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))


class MaterialButton(ctk.CTkButton):
    """Material Design Button Component"""
    def __init__(self, master, variant: str = "filled", **kwargs):
        if variant == "filled":
            super().__init__(
                master,
                fg_color=MaterialColors.PRIMARY,
                hover_color=MaterialColors.PRIMARY_VARIANT,
                text_color=MaterialColors.ON_PRIMARY,
                corner_radius=12,
                height=40,
                font=ctk.CTkFont(size=13, weight="bold"),
                **kwargs
            )
        elif variant == "outlined":
            super().__init__(
                master,
                fg_color="transparent",
                hover_color=MaterialColors.SURFACE_VARIANT,
                text_color=MaterialColors.PRIMARY,
                border_width=2,
                border_color=MaterialColors.PRIMARY,
                corner_radius=12,
                height=40,
                font=ctk.CTkFont(size=13, weight="bold"),
                **kwargs
            )
        elif variant == "text":
            super().__init__(
                master,
                fg_color="transparent",
                hover_color=MaterialColors.SURFACE_VARIANT,
                text_color=MaterialColors.PRIMARY,
                corner_radius=12,
                height=40,
                font=ctk.CTkFont(size=13),
                **kwargs
            )


class MaterialTextField(ctk.CTkFrame):
    """Material Design Text Field with Label"""
    def __init__(self, master, label: str, placeholder: str = "", show: str = "", height: int = 40, multiline: bool = False, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.label = ctk.CTkLabel(
            self,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=MaterialColors.PRIMARY
        )
        self.label.pack(anchor="w", pady=(0, 4))

        if multiline:
            self.entry = ctk.CTkTextbox(
                self,
                height=height,
                fg_color=MaterialColors.SURFACE_VARIANT,
                text_color=MaterialColors.ON_SURFACE,
                corner_radius=8,
                border_width=1,
                border_color=MaterialColors.OUTLINE
            )
        else:
            self.entry = ctk.CTkEntry(
                self,
                height=height,
                placeholder_text=placeholder,
                show=show,
                fg_color=MaterialColors.SURFACE_VARIANT,
                text_color=MaterialColors.ON_SURFACE,
                corner_radius=8,
                border_width=1,
                border_color=MaterialColors.OUTLINE
            )
        self.entry.pack(fill="x")

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


class Snackbar(ctk.CTkFrame):
    """Material Design Snackbar for notifications"""
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=MaterialColors.SURFACE_VARIANT,
            corner_radius=8,
            height=48,
            **kwargs
        )

        self.message_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=MaterialColors.ON_SURFACE
        )
        self.message_label.pack(side="left", padx=16, pady=12)

        self.place_forget()

    def show(self, message: str, duration: int = 3000, type: str = "info"):
        colors = {
            "info": MaterialColors.SURFACE_VARIANT,
            "success": MaterialColors.SUCCESS,
            "error": MaterialColors.ERROR,
            "warning": MaterialColors.WARNING
        }
        self.configure(fg_color=colors.get(type, MaterialColors.SURFACE_VARIANT))
        self.message_label.configure(text=message)
        self.place(relx=0.5, rely=0.95, anchor="center")
        self.after(duration, self.hide)

    def hide(self):
        self.place_forget()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("脚本生成パイプライン")
        self.geometry("720x900")
        self.configure(fg_color=MaterialColors.BACKGROUND)
        self.config_data = load_config()
        self.is_generating = False

        self.create_widgets()
        self.load_saved_config()

    def create_widgets(self):
        # Main container
        self.main_container = ctk.CTkScrollableFrame(
            self,
            fg_color=MaterialColors.BACKGROUND,
            scrollbar_button_color=MaterialColors.SURFACE_VARIANT
        )
        self.main_container.pack(fill="both", expand=True, padx=24, pady=24)

        # Header
        header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 24))

        title = ctk.CTkLabel(
            header_frame,
            text="脚本生成パイプライン",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=MaterialColors.ON_BACKGROUND
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="Compactor → Pipeline → Supervisor",
            font=ctk.CTkFont(size=14),
            text_color=MaterialColors.PRIMARY
        )
        subtitle.pack(anchor="w", pady=(4, 0))

        # API Card
        api_card = MaterialCard(self.main_container, title="🔑 API設定")
        api_card.pack(fill="x", pady=(0, 16))

        self.api_field = MaterialTextField(
            api_card.content_frame,
            label="Anthropic API Key",
            placeholder="sk-ant-...",
            show="*"
        )
        self.api_field.pack(fill="x")

        # Concept Card
        concept_card = MaterialCard(self.main_container, title="📖 作品設定")
        concept_card.pack(fill="x", pady=(0, 16))

        self.concept_field = MaterialTextField(
            concept_card.content_frame,
            label="コンセプト",
            height=80,
            multiline=True
        )
        self.concept_field.pack(fill="x", pady=(0, 12))

        self.characters_field = MaterialTextField(
            concept_card.content_frame,
            label="登場人物",
            height=80,
            multiline=True
        )
        self.characters_field.pack(fill="x")

        # Settings Card
        settings_card = MaterialCard(self.main_container, title="⚙️ 生成設定")
        settings_card.pack(fill="x", pady=(0, 16))

        settings_row = ctk.CTkFrame(settings_card.content_frame, fg_color="transparent")
        settings_row.pack(fill="x")

        # Scenes
        scenes_frame = ctk.CTkFrame(settings_row, fg_color="transparent")
        scenes_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkLabel(
            scenes_frame,
            text="シーン数",
            font=ctk.CTkFont(size=12),
            text_color=MaterialColors.PRIMARY
        ).pack(anchor="w", pady=(0, 4))

        self.scenes_entry = ctk.CTkEntry(
            scenes_frame,
            height=40,
            fg_color=MaterialColors.SURFACE_VARIANT,
            text_color=MaterialColors.ON_SURFACE,
            corner_radius=8,
            border_width=1,
            border_color=MaterialColors.OUTLINE
        )
        self.scenes_entry.pack(fill="x")
        self.scenes_entry.insert(0, "10")

        # Theme
        theme_frame = ctk.CTkFrame(settings_row, fg_color="transparent")
        theme_frame.pack(side="left", fill="x", expand=True, padx=(8, 0))

        ctk.CTkLabel(
            theme_frame,
            text="テーマ",
            font=ctk.CTkFont(size=12),
            text_color=MaterialColors.PRIMARY
        ).pack(anchor="w", pady=(0, 4))

        self.theme_combo = ctk.CTkComboBox(
            theme_frame,
            values=list(THEME_OPTIONS.keys()),
            height=40,
            fg_color=MaterialColors.SURFACE_VARIANT,
            text_color=MaterialColors.ON_SURFACE,
            button_color=MaterialColors.PRIMARY,
            button_hover_color=MaterialColors.PRIMARY_VARIANT,
            dropdown_fg_color=MaterialColors.SURFACE,
            dropdown_text_color=MaterialColors.ON_SURFACE,
            dropdown_hover_color=MaterialColors.SURFACE_VARIANT,
            corner_radius=8,
            border_width=1,
            border_color=MaterialColors.OUTLINE
        )
        self.theme_combo.pack(fill="x")
        self.theme_combo.set("指定なし")

        # Action Buttons
        button_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        button_frame.pack(fill="x", pady=(8, 16))

        self.save_btn = MaterialButton(
            button_frame,
            text="💾 設定を保存",
            variant="outlined",
            command=self.save_settings,
            width=140
        )
        self.save_btn.pack(side="left", padx=(0, 12))

        self.generate_btn = MaterialButton(
            button_frame,
            text="🚀 生成開始",
            variant="filled",
            command=self.start_generation
        )
        self.generate_btn.pack(side="left", fill="x", expand=True)

        # Progress Card
        progress_card = MaterialCard(self.main_container, title="📊 進捗")
        progress_card.pack(fill="x", pady=(0, 16))

        self.progress = ctk.CTkProgressBar(
            progress_card.content_frame,
            fg_color=MaterialColors.SURFACE_VARIANT,
            progress_color=MaterialColors.PRIMARY,
            height=8,
            corner_radius=4
        )
        self.progress.pack(fill="x", pady=(0, 12))
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(
            progress_card.content_frame,
            text="待機中...",
            font=ctk.CTkFont(size=13),
            text_color=MaterialColors.ON_SURFACE
        )
        self.status_label.pack(anchor="w")

        # Cost Card
        cost_card = MaterialCard(self.main_container, title="💰 コスト情報")
        cost_card.pack(fill="x", pady=(0, 16))

        self.cost_label = ctk.CTkLabel(
            cost_card.content_frame,
            text="生成後に表示されます",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=MaterialColors.ON_SURFACE,
            justify="left"
        )
        self.cost_label.pack(anchor="w")

        # Log Card
        log_card = MaterialCard(self.main_container, title="📋 ログ")
        log_card.pack(fill="both", expand=True)

        self.log_text = ctk.CTkTextbox(
            log_card.content_frame,
            height=150,
            fg_color=MaterialColors.SURFACE_VARIANT,
            text_color=MaterialColors.ON_SURFACE,
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.log_text.pack(fill="both", expand=True)

        # Snackbar
        self.snackbar = Snackbar(self)

    def load_saved_config(self):
        if self.config_data.get("api_key"):
            self.api_field.set(self.config_data["api_key"])
        if self.config_data.get("concept"):
            self.concept_field.set(self.config_data["concept"])
        if self.config_data.get("characters"):
            self.characters_field.set(self.config_data["characters"])
        if self.config_data.get("num_scenes"):
            self.scenes_entry.delete(0, "end")
            self.scenes_entry.insert(0, str(self.config_data["num_scenes"]))
        if self.config_data.get("theme_jp"):
            self.theme_combo.set(self.config_data["theme_jp"])

    def save_settings(self):
        """設定を保存"""
        theme_jp = self.theme_combo.get()
        self.config_data = {
            "api_key": self.api_field.get(),
            "concept": self.concept_field.get(),
            "characters": self.characters_field.get(),
            "num_scenes": int(self.scenes_entry.get() or "10"),
            "theme_jp": theme_jp,
            "theme": THEME_OPTIONS.get(theme_jp, ""),
        }
        save_config(self.config_data)
        self.snackbar.show("✅ 設定を保存しました", type="success")
        log_message("設定を保存しました")

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        log_message(message)

    def update_status(self, message: str):
        self.status_label.configure(text=message)
        self.log(message)

    def start_generation(self):
        if self.is_generating:
            return

        api_key = self.api_field.get().strip()
        concept = self.concept_field.get().strip()
        characters = self.characters_field.get().strip()

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
        self.generate_btn.configure(state="disabled", text="生成中...")
        self.progress.set(0)
        self.log_text.delete("1.0", "end")

        thread = threading.Thread(
            target=self.run_generation,
            args=(api_key, concept, characters, num_scenes),
            daemon=True
        )
        thread.start()

    def run_generation(self, api_key: str, concept: str, characters: str, num_scenes: int):
        try:
            theme_jp = self.theme_combo.get()
            theme = THEME_OPTIONS.get(theme_jp, "")

            def callback(msg):
                self.after(0, lambda: self.update_status(msg))

            self.after(0, lambda: self.update_status("🚀 パイプライン開始..."))

            results, cost_tracker = generate_pipeline(
                api_key, concept, characters, num_scenes, theme, callback
            )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = EXPORTS_DIR / f"script_{timestamp}.csv"
            json_path = EXPORTS_DIR / f"script_{timestamp}.json"

            export_csv(results, csv_path)
            export_json(results, json_path)

            self.after(0, lambda: self.on_complete(results, cost_tracker, csv_path, json_path))

        except Exception as e:
            self.after(0, lambda: self.on_error(str(e)))

    def on_complete(self, results, cost_tracker, csv_path, json_path):
        self.is_generating = False
        self.generate_btn.configure(state="normal", text="🚀 生成開始")
        self.progress.set(1)

        self.cost_label.configure(text=cost_tracker.summary())
        self.update_status(f"✅ 完了! {len(results)}シーン生成")
        self.log(f"📄 CSV: {csv_path}")
        self.log(f"📄 JSON: {json_path}")
        self.log(f"💰 {cost_tracker.summary()}")
        self.snackbar.show(f"✅ {len(results)}シーン生成完了!", type="success")

    def on_error(self, error: str):
        self.is_generating = False
        self.generate_btn.configure(state="normal", text="🚀 生成開始")
        self.progress.set(0)
        self.update_status(f"❌ エラー: {error}")
        self.snackbar.show(f"❌ エラー: {error[:50]}", type="error")


if __name__ == "__main__":
    app = App()
    app.mainloop()
