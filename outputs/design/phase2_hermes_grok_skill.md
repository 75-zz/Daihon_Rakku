# Phase 2 設計レポート — Daihon → Grok web 自動化

実装着手前のレビュー用。コードはまだ書いていない。

## ゴール

Phase 1 が出力した `outputs/hermes_pipeline/<work>/grok_inputs/scene_NN.txt` を順番に grok.com に投入し、Grok の応答を `outputs/hermes_pipeline/<work>/grok_responses/scene_NN_response.txt` に保存する。

100シーン規模での実用に耐える。失敗時の部分再開ができる。

---

## 重要な前提整理

### Hermes Agent はそれ自体が LLM ベースのエージェント

Hermes Agent は内部で **xAI / Anthropic / OpenAI 等の LLM API を呼んで動く**。
→ Hermes 経由で 100シーンを処理すると、**Hermes 自身の LLM 課金**が発生する。
→ CLAUDE.md「API コスト安全ルール」に照らして、ここを明示せず進めるべきでない。

Hermes のブラウザツールは便利だが、内部に LLM 推論が走る前提:
- `browser_navigate`, `browser_click`, `browser_type` を呼ぶ「判断」を毎ステップ LLM が行う
- 100シーン × ステップ数 = 数千〜数万トークン消費

### 結論: 2 つのアプローチを比較すべき

---

## アプローチ比較

### アプローチ A: Hermes Agent + SKILL.md (公式流)

```
~/.hermes/skills/creative/daihon-grok-batch/
├── SKILL.md        ← Procedure 記載 (LLM がこれを読んで動く)
└── scripts/
    └── orchestrator.py   ← 入出力ファイル列挙等のヘルパー
```

**動作フロー**:
1. ユーザーが Hermes Agent に「daihon-grok-batch を /path/to/work で実行」と指示
2. LLM (Hermes 内部) が SKILL.md を読む
3. LLM が browser_navigate("https://grok.com") → browser_type → browser_click を順次呼ぶ
4. LLM が応答テキストを抽出してファイルに保存

**メリット**:
- 公式に沿った実装
- Hermes の persistent session / Camofox / CAPTCHA 解決等の恩恵を受けられる
- 失敗時に LLM が状況判断してリカバリ可能

**デメリット**:
- 🔴 **Hermes 自体の LLM コスト発生**（モデル次第で 100シーン処理 $1〜$10）
- Hermes 公式 CLI/Server 版のインストールが必要（user 環境セットアップ）
- 動作の予測可能性が低い（LLM の判断に左右される）
- デバッグが難しい

### アプローチ B: Standalone Playwright スクリプト (軽量)

```
hermes_pipeline/
├── grok_runner.py        ← Playwright で grok.com を直接叩く
├── grok_runner_README.md ← Chrome 起動・ログイン手順
└── (既存 Phase 1 ファイル)
```

**動作フロー**:
1. ユーザーが事前に Chrome を `--remote-debugging-port=9222` で起動し grok.com にログイン
2. `python -m hermes_pipeline.grok_runner <work_dir> [--limit 5]` 実行
3. Playwright が既存 Chrome に CDP 接続
4. 各 scene_NN.txt の内容を chat input に貼り付け → 送信 → 応答待ち → DOM から抽出 → 保存

**メリット**:
- 🟢 **追加 LLM コスト ゼロ**（純粋なブラウザ自動化）
- 動作が決定論的、デバッグしやすい
- 既存 Daihon と同じ Python エコシステム
- Hermes インストール不要
- スピードも速い (LLM 判断ステップなし)

**デメリット**:
- grok.com の DOM 構造変化に弱い（CSS selector 1個でも変わると壊れる）
- CAPTCHA / 異常検知発火時の自動リカバリができない（手動介入必要）
- ログイン状態維持は Chrome プロファイル管理に依存

### アプローチ C: ハイブリッド（推奨候補）

- 基本は **B（Playwright スタンドアロン）** で走らせる
- 失敗時のリトライ・部分再開ロジックを Python 側に実装
- DOM が変わって壊れたら手動修正 (これは A でもどのみち発生)

---

## 推奨: アプローチ B (Standalone Playwright)

理由:
1. **CLAUDE.md コスト安全ルール準拠**: Hermes 内部 LLM 料金が読めない → 安全側に倒すべき
2. user が当初「Hermes 経由で」と言ったが、本質は **「grok.com web 版を自動操作したい」**こと。Hermes はそのための手段の1つ
3. Phase 1 と同じ Python エコシステムで完結し、依存追加は `playwright` のみ
4. 100シーン規模で確実に回せる

ただし user が「Hermes 公式 skill として作りたい」希望があればアプローチ A も提供可能。

---

## 推奨案 (B) の詳細設計

### 1. 依存追加
```powershell
pip install playwright
playwright install chromium
```

### 2. Chrome 事前起動 (user 手動)
```powershell
# 専用プロファイル付きで起動 → grok.com にログインしておく
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
    --remote-debugging-port=9222 `
    --user-data-dir="$env:USERPROFILE\.daihon-chrome"
```
- 初回のみログイン作業。以降このプロファイルは Cookie 維持
- 専用プロファイルなのでユーザーの普段使い Chrome に干渉しない

### 3. Python スクリプト構成
```
hermes_pipeline/grok_runner.py
- Playwright で CDP 接続 (ws://localhost:9222)
- 既存タブ または 新規タブで grok.com を開く
- scene_NN.txt を読み込み
- chat input (textarea[placeholder="..."] など) に value 設定 → Enter 送信
- 応答完了を検知 (送信ボタンが再活性化 / loading spinner 消失)
- 応答テキストを DOM から抽出 (markdown の messsage 要素)
- outputs/.../grok_responses/scene_NN_response.txt に保存
- 既に保存済みファイルはスキップ (部分再開)
- 失敗時は scene_NN.error.txt にエラー記録
```

### 4. CLI
```
python -m hermes_pipeline.grok_runner <work_dir> [--limit N] [--retry K] [--start-from M]
```
- `<work_dir>` = `outputs/hermes_pipeline/<basename>/` (grok_inputs/ と grok_responses/ の親)
- `--limit`: 先頭 N シーンだけ
- `--retry`: 失敗時のリトライ上限 (デフォルト 2)
- `--start-from`: 指定 scene_id 以降を処理 (再開用)

### 5. 失敗・リトライ設計
- 各シーン処理に **120秒タイムアウト**（Grok の応答が遅延した場合の上限）
- DOM 抽出失敗 → 5秒待って再試行（最大 retry 回）
- レート制限らしき挙動 (送信ボタン無効化が続く等) → 60秒バックオフ
- 連続 3 シーン失敗 → 全体停止して user に通知（暴走防止）

### 6. MVP 実行手順
```powershell
# 1. Chrome 起動 (専用プロファイル)
& "...chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:USERPROFILE\.daihon-chrome"

# 2. 手動で grok.com にログイン (初回のみ)

# 3. 別ターミナルで Phase 1 (もう実施済み)
python -m hermes_pipeline.cli "<zip>" --limit 5

# 4. Phase 2 実行
python -m hermes_pipeline.grok_runner "outputs/hermes_pipeline/<basename>/" --limit 5

# 5. outputs/.../grok_responses/scene_001-005_response.txt が生成される
```

---

## DOM 構造調査の必要性

grok.com の DOM 構造（input セレクタ、応答要素のクラス名）は事前確認が必要。
- 実装着手前に user に「chrome 起動 → grok.com 開いて DevTools で input / message DOM を見せてもらう」工程を挟む
- もしくは私が `browser_console` 相当の JS 実行で動的調査（Playwright で初回起動時に self-inspect）

---

## コストまとめ

| 項目 | アプローチ A (Hermes) | アプローチ B (Playwright) |
|---|---|---|
| 追加 LLM 課金 | $1〜$10 / 100シーン (モデル次第) | **$0** |
| 既存 Daihon API | 影響なし | 影響なし |
| Grok web 課金 | SuperGrok サブスク (既存) | SuperGrok サブスク (既存) |
| ComfyUI 課金 | 後段、ローカル GPU | 後段、ローカル GPU |
| 環境構築 | Hermes インストール必要 | `pip install playwright` のみ |

---

## ユーザー確認事項

1. アプローチ B (Playwright) で進めて良いか? それとも A (Hermes 公式 skill) を希望か?
2. user の Chrome は普段使い同居 OK か? 専用プロファイル分離が必須か?
3. MVP は 5シーンで進めて、成功したら 100シーン本番に拡張で良いか?

確認取れたら実装着手する。
