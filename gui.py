#!/usr/bin/env python3
"""
FANZA同人向け 低コスト脚本生成パイプライン - GUI版
Claude API直接対応
Skills: prompt_compactor → low_cost_pipeline → script_quality_supervisor
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
    """スキルファイルを読み込む"""
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
    """Claude APIを呼び出し、コストを追跡"""
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

            # コスト追跡
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
    """レスポンスからJSONを抽出してパース"""
    # マークダウンコードブロック除去
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
    """コンテキストを圧縮してトークン削減"""
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
    """アウトライン生成（Haiku）"""
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
    """シーン下書き生成（Haiku）"""
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
    """重要シーンの清書（Sonnet）"""
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
    """品質チェック（Haiku）"""
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
    """差分修正を適用（Haiku）"""
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
    """
    3段階パイプライン:
    1. prompt_compactor: コンテキスト圧縮
    2. low_cost_pipeline: Haiku下書き → Sonnet清書（重要シーンのみ）
    3. script_quality_supervisor: 品質チェック → 差分修正
    """
    client = anthropic.Anthropic(api_key=api_key)
    cost_tracker = CostTracker()

    # 補助ファイル読み込み
    jailbreak = load_file(JAILBREAK_FILE)
    danbooru = load_file(DANBOORU_TAGS_FILE)
    sd_guide = load_file(SD_PROMPT_GUIDE_FILE)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # === Phase 1: Prompt Compactor ===
    if callback:
        callback("🔧 Phase 1: コンテキスト圧縮")

    context = compact_context(
        client, concept, characters, theme, cost_tracker, callback
    )

    # コンテキスト保存
    context_file = CONTEXT_DIR / f"context_{timestamp}.json"
    with open(context_file, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)

    if callback:
        callback(f"✅ コンテキスト圧縮完了")

    # === Phase 2: Low Cost Pipeline ===
    if callback:
        callback("🔧 Phase 2: 低コスト生成パイプライン")

    # アウトライン生成
    outline = generate_outline(client, context, num_scenes, cost_tracker, callback)

    if callback:
        callback(f"✅ アウトライン完成: {len(outline)}シーン")

    results = []

    for i, scene in enumerate(outline):
        if callback:
            callback(f"🎬 シーン {i+1}/{len(outline)} 生成中...")

        # 下書き生成（Haiku）
        draft = generate_scene_draft(
            client, context, scene, jailbreak, danbooru, sd_guide,
            cost_tracker, callback
        )

        # 下書き保存
        draft_file = DRAFTS_DIR / f"draft_{timestamp}_scene{i+1}.json"
        with open(draft_file, "w", encoding="utf-8") as f:
            json.dump(draft, f, ensure_ascii=False, indent=2)

        # 重要シーン（intensity >= 4）のみSonnetで清書
        intensity = scene.get("intensity", 3)
        if intensity >= 4:
            if callback:
                callback(f"✨ シーン {i+1} 清書中（重要度{intensity}）...")
            final = polish_scene(client, context, draft, cost_tracker, callback)
        else:
            final = draft

        # 最終版保存
        final_file = FINAL_DIR / f"final_{timestamp}_scene{i+1}.json"
        with open(final_file, "w", encoding="utf-8") as f:
            json.dump(final, f, ensure_ascii=False, indent=2)

        results.append(final)

        if callback:
            callback(f"✅ シーン {i+1} 完了")

    # === Phase 3: Quality Supervisor ===
    if callback:
        callback("🔧 Phase 3: 品質チェック")

    quality_result = check_quality(client, context, results, cost_tracker, callback)

    if quality_result.get("has_problems", False):
        problems = quality_result.get("problems", [])
        fixes = quality_result.get("fix_instructions", [])

        if callback:
            callback(f"⚠️ {len(problems)}件の問題を検出、修正中...")

        # 差分修正を適用
        for fix in fixes:
            scene_id = fix.get("scene_id")
            instruction = fix.get("instruction", "")

            if scene_id and 1 <= scene_id <= len(results):
                if callback:
                    callback(f"🔧 シーン {scene_id} 修正中...")

                fixed = apply_fix(
                    client, results[scene_id - 1], instruction,
                    cost_tracker, callback
                )
                results[scene_id - 1] = fixed

                # 修正版保存
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
    """結果をCSV出力"""
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
    """結果をJSON出力"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


# === GUI ===
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("低コスト脚本生成パイプライン")
        self.geometry("700x850")
        self.config_data = load_config()
        self.is_generating = False

        self.create_widgets()
        self.load_saved_config()

    def create_widgets(self):
        # スクロール可能フレーム
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # タイトル
        title = ctk.CTkLabel(
            self.scroll_frame,
            text="🎬 低コスト脚本生成パイプライン",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=(0, 5))

        subtitle = ctk.CTkLabel(
            self.scroll_frame,
            text="① Compactor → ② Pipeline → ③ Supervisor",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        subtitle.pack(pady=(0, 15))

        # === API設定 ===
        api_frame = ctk.CTkFrame(self.scroll_frame)
        api_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(api_frame, text="🔑 Anthropic APIキー", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.api_entry = ctk.CTkEntry(api_frame, show="*", width=400, placeholder_text="sk-ant-...")
        self.api_entry.pack(padx=10, pady=(0, 10), fill="x")

        # === 作品設定 ===
        concept_frame = ctk.CTkFrame(self.scroll_frame)
        concept_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(concept_frame, text="📖 作品コンセプト", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.concept_text = ctk.CTkTextbox(concept_frame, height=80)
        self.concept_text.pack(padx=10, pady=(0, 10), fill="x")

        # === 登場人物 ===
        char_frame = ctk.CTkFrame(self.scroll_frame)
        char_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(char_frame, text="👥 登場人物設定", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.characters_text = ctk.CTkTextbox(char_frame, height=80)
        self.characters_text.pack(padx=10, pady=(0, 10), fill="x")

        # === シーン数・テーマ ===
        settings_frame = ctk.CTkFrame(self.scroll_frame)
        settings_frame.pack(fill="x", pady=5)

        row1 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(row1, text="🎬 シーン数:").pack(side="left")
        self.scenes_entry = ctk.CTkEntry(row1, width=80)
        self.scenes_entry.pack(side="left", padx=(5, 20))
        self.scenes_entry.insert(0, "10")

        ctk.CTkLabel(row1, text="🏷️ テーマ:").pack(side="left")
        self.theme_combo = ctk.CTkComboBox(row1, values=list(THEME_OPTIONS.keys()), width=180)
        self.theme_combo.pack(side="left", padx=5)
        self.theme_combo.set("指定なし")

        # === 生成ボタン ===
        self.generate_btn = ctk.CTkButton(
            self.scroll_frame,
            text="🚀 生成開始",
            command=self.start_generation,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.generate_btn.pack(pady=15)

        # === プログレス ===
        self.progress = ctk.CTkProgressBar(self.scroll_frame)
        self.progress.pack(fill="x", padx=20, pady=5)
        self.progress.set(0)

        # === ステータス ===
        self.status_label = ctk.CTkLabel(
            self.scroll_frame,
            text="待機中...",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=5)

        # === コスト表示 ===
        cost_frame = ctk.CTkFrame(self.scroll_frame)
        cost_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(cost_frame, text="💰 コスト情報", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.cost_label = ctk.CTkLabel(
            cost_frame,
            text="生成後に表示されます",
            justify="left",
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.cost_label.pack(anchor="w", padx=10, pady=(0, 10))

        # === ログ ===
        log_frame = ctk.CTkFrame(self.scroll_frame)
        log_frame.pack(fill="both", expand=True, pady=5)

        ctk.CTkLabel(log_frame, text="📋 ログ", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.log_text = ctk.CTkTextbox(log_frame, height=180)
        self.log_text.pack(padx=10, pady=(0, 10), fill="both", expand=True)

    def load_saved_config(self):
        if self.config_data.get("api_key"):
            self.api_entry.insert(0, self.config_data["api_key"])
        if self.config_data.get("concept"):
            self.concept_text.insert("1.0", self.config_data["concept"])
        if self.config_data.get("characters"):
            self.characters_text.insert("1.0", self.config_data["characters"])
        if self.config_data.get("num_scenes"):
            self.scenes_entry.delete(0, "end")
            self.scenes_entry.insert(0, str(self.config_data["num_scenes"]))
        if self.config_data.get("theme_jp"):
            self.theme_combo.set(self.config_data["theme_jp"])

    def save_current_config(self):
        theme_jp = self.theme_combo.get()
        self.config_data = {
            "api_key": self.api_entry.get(),
            "concept": self.concept_text.get("1.0", "end-1c"),
            "characters": self.characters_text.get("1.0", "end-1c"),
            "num_scenes": int(self.scenes_entry.get() or "10"),
            "theme_jp": theme_jp,
            "theme": THEME_OPTIONS.get(theme_jp, ""),
        }
        save_config(self.config_data)

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

        # バリデーション
        api_key = self.api_entry.get().strip()
        concept = self.concept_text.get("1.0", "end-1c").strip()
        characters = self.characters_text.get("1.0", "end-1c").strip()

        if not api_key:
            self.update_status("❌ APIキーを入力してください")
            return
        if not concept:
            self.update_status("❌ 作品コンセプトを入力してください")
            return

        try:
            num_scenes = int(self.scenes_entry.get())
            if num_scenes < 1 or num_scenes > 50:
                raise ValueError()
        except:
            self.update_status("❌ シーン数は1〜50の整数で")
            return

        # 設定保存
        self.save_current_config()

        # 生成開始
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

            # 出力
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = EXPORTS_DIR / f"script_{timestamp}.csv"
            json_path = EXPORTS_DIR / f"script_{timestamp}.json"

            export_csv(results, csv_path)
            export_json(results, json_path)

            # 完了
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

    def on_error(self, error: str):
        self.is_generating = False
        self.generate_btn.configure(state="normal", text="🚀 生成開始")
        self.progress.set(0)
        self.update_status(f"❌ エラー: {error}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
