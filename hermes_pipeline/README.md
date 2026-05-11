# hermes_pipeline

Daihon Rakku → Hermes Agent → Grok web → ComfyUI/Anima を繋ぐ実験パイプライン。
本番 Daihon Rakku（gui.py / pipeline.py / ero_dialogue_pool.py 等）とは
**完全に独立した別バージョン**で、本番コードは一切変更しない。

## 現在のフェーズ

- ✅ **Phase 1**: Daihon export ZIP → Grok 投入用テキスト生成
- 🟡 **Phase 2**: Hermes browser skill (grok.com 自動操作) — skill 完成。実行は Hermes インストール後
- ⬜ **Phase 3**: Hermes ComfyUI skill (Anima workflow 実行)
- ⬜ **Phase 4**: エンドツーエンド統合・MVP 5シーン疎通

## Phase 1 使い方

```powershell
# MVP: 先頭5シーンだけ Grok 投入用テキストを書き出し
python -m hermes_pipeline.cli "C:\Users\k75mi\Downloads\ダイホンラック出力\20260506\中野一花（五等分の花嫁）_export_20260506014006.zip" --limit 5

# 全シーン
python -m hermes_pipeline.cli "<zip>"

# 出力先カスタム
python -m hermes_pipeline.cli "<zip>" --out "D:\test_out"

# 特定シーンを標準出力にも表示（中身確認用）
python -m hermes_pipeline.cli "<zip>" --limit 5 --print-scene 1
```

## 出力構造

```
outputs/hermes_pipeline/<zip_basename>/
└── grok_inputs/
    ├── scene_001.txt   ← Grok チャット欄にコピペする1ファイル＝1シーン
    ├── scene_002.txt
    └── ...
```

各 `scene_NN.txt` は:
- FANZA同人エロ漫画向け脚本エンジニアのシステムプロンプト
- 「日本語版＋English version」両セクション出力指示
- Daihon 由来のシーン情報（日本語desc / 英語自然言語 / 機械タグ(LoRA除去後) / 擬音 / セリフ群）

を含む単一テキスト。Hermes Phase 2 ではこれを browser_navigate で grok.com に投入する。

## モジュール構成

| ファイル | 役割 |
|---|---|
| `parser.py` | Daihon ZIP の script.csv / sd.txt をパースし Scene dataclass のリストを返す |
| `lora_filter.py` | `<lora:xxx:y>` 形式タグを除去（NoobAI系 LoRA を Anima 向けから外す）|
| `grok_prompt_builder.py` | Scene → Grok 投入用テキスト組み立て |
| `cli.py` | コマンドラインエントリ |
| `hermes_skill/daihon-grok-batch/SKILL.md` | Phase 2: Hermes Agent が読む手順書 |
| `hermes_skill/daihon-grok-batch/scripts/orchestrator.py` | Phase 2: 入出力ファイル管理ヘルパー |

## Phase 2 使い方（Hermes Agent skill）

### ⚠️ コスト警告

本スキルは Hermes Agent 内部の LLM (Claude/OpenAI/Grok など user 設定) を
DOM 判定・応答抽出のたびに呼ぶ。**100シーン処理で推定 $1〜$10 程度の
追加 LLM 課金**が発生する見込み。実行前に Hermes Agent が処理対象数と
コスト感を提示するので、明示的に同意してから走らせること。

### A. Hermes Agent のインストール

公式 CLI/Server 版 (Nous Research)。Windows なら:

```powershell
# 公式サイトから installer 取得 (URL は公式参照)
# https://hermes-agent.nousresearch.com/
# インストール後、CLI が使えるようになる
hermes --version
```

LLM プロバイダの API キーを設定:

```powershell
# 例: xAI Grok を使う場合
$env:XAI_API_KEY = "xai-..."
# 例: Anthropic Claude を使う場合
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

### B. Skill 配置

このリポジトリの `hermes_skill/daihon-grok-batch/` を Hermes の skill ディレクトリへ:

```powershell
# Windows
$skillsDir = "$env:USERPROFILE\.hermes\skills\creative"
New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null
Copy-Item -Recurse -Force `
    "F:\作業\AI開発\Daihon_Rakku\hermes_pipeline\hermes_skill\daihon-grok-batch" `
    $skillsDir
```

確認:

```powershell
hermes skills list | Select-String "daihon-grok-batch"
```

### C. 専用 Chrome 起動（Daihon 専用プロファイル）

普段使い Chrome に干渉しないよう、専用プロファイルで CDP デバッグ起動:

```powershell
# 1. 専用プロファイルディレクトリは Chrome が初回起動時に自動作成
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
    --remote-debugging-port=9222 `
    --user-data-dir="$env:USERPROFILE\.daihon-chrome" `
    --no-first-run --no-default-browser-check
```

初回のみ手動で grok.com にログイン。以降このプロファイルは Cookie/Session を維持。

### D. Phase 1 で Grok 入力テキストを準備

```powershell
python -m hermes_pipeline.cli "<zip>" --limit 5
# → outputs/hermes_pipeline/<basename>/grok_inputs/scene_001-005.txt
```

### E. Hermes Agent から skill を起動

```powershell
hermes chat
```

Hermes 対話で:

```
daihon-grok-batch を `F:/作業/AI開発/Daihon_Rakku/outputs/hermes_pipeline/中野一花..._export_20260506014006/` で実行して。
まず処理対象シーン数とコスト感を提示してから始めて。
```

Hermes が:
1. Chrome に CDP 接続
2. grok.com の DOM セレクタを動的調査
3. pending シーンを順次 grok.com に投げる
4. 応答を `grok_responses/scene_NNN_response.txt` に保存
5. 進捗 JSON を `grok_progress.json` に記録

### F. 結果確認

```powershell
python hermes_pipeline\hermes_skill\daihon-grok-batch\scripts\orchestrator.py status `
    "outputs\hermes_pipeline\<basename>\"
```

`done_count == 5`, `error_count == 0` なら MVP 成功。

## 本番 Daihon への影響

**ゼロ**。以下のファイルは一切変更していない:
- `gui.py`
- `pipeline.py`
- `ero_dialogue_pool.py`
- `character_pool_generator.py`
- その他既存ファイル

Phase 2 以降で gui.py に「隠しメニュー」を追加するかは別途判断。
