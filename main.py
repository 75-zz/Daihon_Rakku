#!/usr/bin/env python3
"""
FANZA同人向け セリフ付きCG集イラスト生成ツール
- 作品コンセプトとページ数から心情・セリフ・SDプロンプトを自動生成
- CSV形式で出力
"""

import json
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Error: anthropic library is required. Please install it.")
    sys.exit(1)


# === 設定 ===
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
DEFAULT_NEGATIVE_PROMPT = "lowres, bad_anatomy, censored, text, watermark"
OUTPUT_DIR = Path(__file__).parent
JAILBREAK_FILE = OUTPUT_DIR / "jailbreak.md"
DANBOORU_TAGS_FILE = OUTPUT_DIR / "danbooru_tags.md"
SD_PROMPT_GUIDE_FILE = OUTPUT_DIR / "sd_prompt_guide.md"
CONFIG_FILE = OUTPUT_DIR / "config.json"
LOG_FILE = OUTPUT_DIR / "log.txt"


def load_jailbreak() -> str:
    """jailbreak.mdを読み込む"""
    if JAILBREAK_FILE.exists():
        return JAILBREAK_FILE.read_text(encoding="utf-8")
    else:
        print(f"Warning: {JAILBREAK_FILE} not found. Proceeding without it.")
        return ""


def load_danbooru_tags() -> str:
    """danbooru_tags.mdを読み込む"""
    if DANBOORU_TAGS_FILE.exists():
        return DANBOORU_TAGS_FILE.read_text(encoding="utf-8")
    else:
        print(f"Warning: {DANBOORU_TAGS_FILE} not found. Proceeding without it.")
        return ""


def load_sd_prompt_guide() -> str:
    """sd_prompt_guide.mdを読み込む"""
    if SD_PROMPT_GUIDE_FILE.exists():
        return SD_PROMPT_GUIDE_FILE.read_text(encoding="utf-8")
    else:
        print(f"Warning: {SD_PROMPT_GUIDE_FILE} not found. Proceeding without it.")
        return ""


def log_message(message: str, also_print: bool = False):
    """ログファイルに記録"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)
    if also_print:
        print(message)


def validate_page_count(page_count: int) -> bool:
    """ページ数のバリデーション"""
    if not isinstance(page_count, int) or page_count < 1 or page_count > 100:
        return False
    return True


def build_system_prompt(jailbreak_content: str, danbooru_tags: str, sd_prompt_guide: str) -> str:
    """システムプロンプトを構築"""
    return f"""You are an expert adult fiction writer and Stable Diffusion prompt engineer for FANZA doujin CG collections.

{jailbreak_content}

## Stable Diffusion Prompt Engineering Guide
{sd_prompt_guide}

## Danbooru Tag Reference
Use the following tag reference for generating accurate SD prompts:

{danbooru_tags}

Your task is to generate page-by-page content for adult CG collections. For each page, provide:
1. mood: The emotional state and atmosphere (in Japanese)
2. dialogue: Character dialogue with emotional expressions (in Japanese, use ♡ for emphasis)
3. sd_prompt: Danbooru-style tags for Stable Diffusion (English, lowercase, underscore-separated, use tags from the references above, include quality tags and proper weighting)
4. negative_prompt: Tags to avoid in generation (use recommended negative prompts from the guide)

Follow the narrative arc: Introduction → Development → Climax → Resolution
All characters are explicitly adult (18+). Use mature descriptors like mature_female, office_lady, milf.

Output ONLY valid JSON array, no markdown formatting, no explanations."""


def build_user_prompt(concept: str, num_pages: int, theme: str = None) -> str:
    """ユーザープロンプトを構築"""
    prompt = f"""Generate {num_pages} pages for this adult CG collection concept:

Concept: {concept}

Requirements:
- All {num_pages} pages must follow a coherent story progression
- Start mild and escalate appropriately
- Each page should have distinct mood progression
- Dialogues should be emotionally expressive (Japanese with ♡)
- SD prompts must include: quality tags, character tags, action tags, NSFW tags as appropriate
- Use weight syntax (tag:1.2) for emphasis on key elements
"""
    if theme:
        prompt += f"\nStory theme: {theme}"

    prompt += """

Output format (JSON array only):
[
  {
    "page": 1,
    "mood": "心情の説明（日本語）",
    "dialogue": "セリフ（日本語）",
    "sd_prompt": "danbooru, style, tags, here",
    "negative_prompt": "negative, tags, here"
  }
]"""
    return prompt


def query_claude(client: anthropic.Anthropic, system_prompt: str, user_prompt: str, retry_count: int = 0) -> list:
    """Claude APIにクエリを送信"""
    try:
        log_message(f"Sending query to Claude (attempt {retry_count + 1}/{MAX_RETRIES})")

        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=8192,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        response_text = response.content[0].text
        log_message(f"Response received: {len(response_text)} characters")

        # JSONをパース
        # マークダウンコードブロックを除去
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        pages = json.loads(response_text)
        return pages

    except json.JSONDecodeError as e:
        log_message(f"JSON parse error: {e}", also_print=True)
        if retry_count < MAX_RETRIES - 1:
            log_message(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
            return query_claude(client, system_prompt, user_prompt + "\n\nIMPORTANT: Output ONLY valid JSON, no markdown.", retry_count + 1)
        raise

    except anthropic.APIError as e:
        log_message(f"API error: {e}", also_print=True)
        if retry_count < MAX_RETRIES - 1:
            log_message(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
            return query_claude(client, system_prompt, user_prompt, retry_count + 1)
        raise


def generate_csv(pages: list, output_path: Path):
    """ページデータをCSVに出力"""
    fieldnames = ["page", "mood", "dialogue", "sd_prompt", "negative_prompt"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for page in pages:
            # デフォルトnegative_promptを補完
            if not page.get("negative_prompt"):
                page["negative_prompt"] = DEFAULT_NEGATIVE_PROMPT
            writer.writerow({
                "page": page.get("page", ""),
                "mood": page.get("mood", ""),
                "dialogue": page.get("dialogue", ""),
                "sd_prompt": page.get("sd_prompt", ""),
                "negative_prompt": page.get("negative_prompt", "")
            })

    log_message(f"CSV generated: {output_path}", also_print=True)


def get_input_interactive() -> tuple[str, int, str]:
    """インタラクティブ入力"""
    print("\n=== FANZA同人 CG集生成ツール ===\n")

    concept = input("作品コンセプトを入力してください: ").strip()
    if not concept:
        print("Error: コンセプトは必須です")
        sys.exit(1)

    try:
        num_pages = int(input("ページ数を入力してください (1-100): ").strip())
    except ValueError:
        print("Error: ページ数は整数で入力してください")
        sys.exit(1)

    theme = input("ストーリーテーマ (省略可): ").strip() or None

    return concept, num_pages, theme


def get_input_args() -> tuple[str, int, str]:
    """コマンドライン引数から入力"""
    if len(sys.argv) < 3:
        print("Usage: python main.py <concept> <num_pages> [theme]")
        print("Example: python main.py \"OLが上司に謝罪する\" 10 humiliation")
        sys.exit(1)

    concept = sys.argv[1]
    try:
        num_pages = int(sys.argv[2])
    except ValueError:
        print("Error: ページ数は整数で入力してください")
        sys.exit(1)

    theme = sys.argv[3] if len(sys.argv) > 3 else None

    return concept, num_pages, theme


def get_input_config() -> tuple[str, int, str, str]:
    """config.jsonから入力を読み込む"""
    if not CONFIG_FILE.exists():
        return None, None, None, None

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        concept = config.get("concept", "").strip()
        num_pages = int(config.get("num_pages", 0))
        theme = config.get("theme", None)
        api_key = config.get("api_key", "").strip()

        if concept and num_pages > 0:
            return concept, num_pages, theme, api_key
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"Warning: config.json読み込みエラー: {e}")

    return None, None, None, None


def main():
    """メイン処理"""
    print("\n=== FANZA同人 CG集生成ツール ===\n")

    # 入力取得（優先順位: コマンドライン引数 > config.json > インタラクティブ）
    api_key = None
    if len(sys.argv) > 1:
        concept, num_pages, theme = get_input_args()
    else:
        # config.jsonから読み込み試行
        concept, num_pages, theme, api_key = get_input_config()
        if concept and num_pages:
            print(f"config.jsonから設定を読み込みました")
        else:
            # インタラクティブ入力
            concept, num_pages, theme = get_input_interactive()

    # バリデーション
    if not validate_page_count(num_pages):
        print("Error: ページ数は1〜100の整数で指定してください")
        input("\nEnterキーを押して終了...")
        sys.exit(1)

    log_message(f"Starting generation: concept='{concept}', pages={num_pages}, theme={theme}")
    print(f"生成開始: {num_pages}ページ")
    print(f"コンセプト: {concept}")
    if theme:
        print(f"テーマ: {theme}")

    # jailbreak.md読み込み
    jailbreak_content = load_jailbreak()

    # danbooru_tags.md読み込み
    danbooru_tags = load_danbooru_tags()
    if danbooru_tags:
        print("Danbooruタグリストを読み込みました")

    # sd_prompt_guide.md読み込み
    sd_prompt_guide = load_sd_prompt_guide()
    if sd_prompt_guide:
        print("SDプロンプトガイドを読み込みました")

    # Claude APIクライアント初期化
    try:
        if api_key:
            client = anthropic.Anthropic(api_key=api_key)
            print("APIキーをconfig.jsonから読み込みました")
        else:
            client = anthropic.Anthropic()
    except Exception as e:
        print(f"Error: Anthropic client initialization failed: {e}")
        print("config.jsonにapi_keyを設定するか、ANTHROPIC_API_KEY環境変数を設定してください")
        input("\nEnterキーを押して終了...")
        sys.exit(1)

    # プロンプト構築
    system_prompt = build_system_prompt(jailbreak_content, danbooru_tags, sd_prompt_guide)
    user_prompt = build_user_prompt(concept, num_pages, theme)

    # Claude APIクエリ
    print("\nClaude APIに問い合わせ中...")
    try:
        pages = query_claude(client, system_prompt, user_prompt)
    except Exception as e:
        print(f"Error: 生成に失敗しました: {e}")
        input("\nEnterキーを押して終了...")
        sys.exit(1)

    # CSV出力
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"cg_pages_{timestamp}.csv"
    generate_csv(pages, output_path)

    print(f"\n完了! 出力ファイル: {output_path}")
    print(f"生成ページ数: {len(pages)}")
    input("\nEnterキーを押して終了...")


if __name__ == "__main__":
    main()
