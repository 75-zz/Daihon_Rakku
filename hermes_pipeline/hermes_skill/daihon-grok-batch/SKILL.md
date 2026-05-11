---
name: daihon-grok-batch
description: Daihon Rakku が生成した「Grok 投入用テキスト」を grok.com web 版に順次投入し、Anima 用シーン脚本の応答を取得・保存するバッチスキル。FANZA 同人エロ漫画スクリプトの 100シーン規模処理を想定。
version: 0.1.0
author: Daihon Rakku Project
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [creative, browser, grok, anima, comfyui, batch, daihon-rakku]
    requires_toolsets: [browser, terminal]
    category: creative
---

# Daihon → Grok web Batch Skill

ローカルに用意済みの `grok_inputs/scene_NNN.txt` 群を grok.com に順次投げ、
返ってきた応答を `grok_responses/scene_NNN_response.txt` に保存する。
失敗時は `scene_NNN.error.txt` を残し、次のシーンに進む。

## When to Use

- ユーザーが `daihon-grok-batch` を指定して起動した、または `<work_dir>` を渡して
  「grok に順に投げて」「Anima 用脚本に書き換えて」と依頼した時
- `<work_dir>` 例: `F:/作業/AI開発/Daihon_Rakku/outputs/hermes_pipeline/<basename>/`
- `<work_dir>/grok_inputs/scene_*.txt` が既に生成されていることが前提
  （Phase 1 の `python -m hermes_pipeline.cli <zip>` で作る）

## Important Cost & Safety Notes

- 本スキルは Hermes Agent 内部の LLM を **DOM 判定・応答抽出のたびに呼ぶ**。
  100シーン処理で 推定 $1〜$10 程度の LLM 課金が発生する見込み。
- 実行前に必ず処理対象シーン数とコスト感をユーザーに提示し、明示的合意を取ること。
- 連続 3 シーン失敗したら即停止し、ユーザー判断を仰ぐこと。暴走防止。
- grok.com の利用規約遵守はユーザー責任。SuperGrok サブスク前提。

## Procedure

### Step 1: 事前確認

1. `${HERMES_SKILL_DIR}/scripts/orchestrator.py list <work_dir>` を terminal ツールで実行
   - 例: `python ${HERMES_SKILL_DIR}/scripts/orchestrator.py list "F:/作業/AI開発/Daihon_Rakku/outputs/hermes_pipeline/中野一花..._export_20260506014006" --limit 5`
2. 返ってきた JSON の `pending` 配列を確認
3. ユーザーに「対象 N シーン処理する。推定コスト $X。続行?」と確認

### Step 2: ブラウザ準備

1. 既にローカル Chrome へ CDP 接続済みかを `browser_navigate` で確認
   - 未接続なら user に `chrome.exe --remote-debugging-port=9222 --user-data-dir="$env:USERPROFILE\.daihon-chrome"` 起動を依頼
2. `browser_navigate("https://grok.com")`
3. `browser_snapshot()` でログイン状態を確認
   - 未ログインなら user に手動ログインを依頼してから再開

### Step 3: DOM セレクタの動的調査 (初回のみ)

grok.com の UI は変化するため、ハードコードしない。最初のシーン処理前に:

1. `browser_snapshot()` でページ構造を取得
2. 次の3要素のセレクタ/ref を特定する:
   - **input**: メッセージ入力欄 (textarea / contenteditable div)
   - **send button**: 送信ボタン (送信できる状態の時のみ active)
   - **assistant message**: アシスタント応答テキストが入る要素 (最新のものを取得する手段)
3. 特定できなかったら `browser_console(expression="...")` で `document.querySelector` を試して洗い出す
4. 確定したセレクタ情報は本セッション内で記憶（ファイルには書かない）

### Step 4: 各シーンのループ処理

`pending` 配列の各 scene_id に対して順次実行:

#### 4a. 入力読み出し
```
python ${HERMES_SKILL_DIR}/scripts/orchestrator.py read <work_dir> <scene_id>
```
標準出力にテキストが返る。

#### 4b. 新規チャット開始 (grok.com の「New chat」ボタンをクリック)
- 連続会話で前シーンの文脈が混ざらないよう、毎シーン新規チャットを開く

#### 4c. テキスト投入
- `browser_type(ref="<input_ref>", text=<scene_text>)`
- 長文 (4-5KB) のためペースト相当にする。`browser_console` で
  `document.execCommand('insertText', false, <text>)` を使う手も検討

#### 4d. 送信
- `browser_click(ref="<send_button_ref>")`
- または Ctrl+Enter / Enter キーを `browser_press` で

#### 4e. 応答完了の待機
- 送信ボタンが再活性化 / loading spinner が消える / 応答テキストが安定する
  までポーリング (`browser_snapshot()` を 2-3秒間隔で確認、最大 120秒)
- 120秒超えたらタイムアウト扱い → save-error

#### 4f. 応答抽出
- `browser_console(expression="<assistant 要素を取得して textContent または innerText を返す JS>")`
- 取得テキストが期待形式（「# 日本語版」「# English version」両方を含む）か簡易検証

#### 4g. 保存
```
echo "<response>" | python ${HERMES_SKILL_DIR}/scripts/orchestrator.py save-response <work_dir> <scene_id>
```
（実際は `terminal` ツールの stdin パイプ機能で `<response>` を渡す）

#### 4h. 失敗時
- DOM 抽出失敗 / 期待形式と違う / タイムアウト → リトライ最大 2 回
- リトライ全失敗 → `save-error <work_dir> <scene_id> "<error_msg>"`
- 連続 3 シーン失敗 → 全体停止、user に通知

### Step 5: 進捗報告

全ループ後、または途中停止時:
```
python ${HERMES_SKILL_DIR}/scripts/orchestrator.py status <work_dir>
```
JSON サマリを user に提示。

## Pitfalls

- **DOM 構造変化**: grok.com の UI 更新で selector が壊れることがある。
  必ず Step 3 の動的調査を毎セッション最初に行う。
- **応答途中での抽出**: ストリーミング応答が完了していない状態で抽出するとテキストが切れる。
  応答完了シグナル（送信ボタン再活性 等）を必ず待つ。
- **長文の type が遅い**: 4KB のテキストを `browser_type` で1文字ずつ打つと遅い・失敗しやすい。
  `browser_console` で `value` プロパティに直接代入 + `input` イベント発火 が確実。
- **レート制限**: SuperGrok でも連続投げで一時的に制限される可能性。60秒バックオフを入れる。
- **コスト暴走**: Hermes 内部 LLM 課金を user が把握していないと事故る。Step 1 で必ず提示。
- **新規チャットを開かないと前シーン文脈が混ざる**: Step 4b を省略しない。

## Verification

成功判定:
- 各 `scene_NNN_response.txt` に「# 日本語版」と「# English version」の両セクションが含まれる
- 各応答が最低 1KB 以上ある（短すぎる応答は Grok の拒否 / 切断疑い）
- `status` コマンドの `error_count` が 0
- `done_count == pending_count` (Step 1 時点での値) になっている

不合格時:
- error_count > 0 → 該当 `.error.txt` を user に見せて手動再投入を提案
- 期待形式不一致のシーンは `scene_NNN_response.txt` を残しつつ user に通知し、
  プロンプトテンプレ改善か手動再投入を決めてもらう
