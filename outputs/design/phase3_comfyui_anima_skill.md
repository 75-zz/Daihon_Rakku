# Phase 3 設計レポート — Grok 応答 → ComfyUI/Anima 画像生成

実装着手前のレビュー用。コードはまだ書かない。

## ゴール

Phase 2 が出力した `outputs/hermes_pipeline/<work>/grok_responses/scene_NNN_response.txt`
の **English version セクション**を取り出し、Anima 用品質タグを前置して
ComfyUI に投入、各シーンの画像を
`outputs/hermes_pipeline/<work>/images/scene_NNN.png` に保存する。

MVP は 5シーン疎通。Phase 4 でエンドツーエンド統合。

---

## 環境前提（確認済み）

| 項目 | 状態 |
|---|---|
| Hermes Agent (WSL) | ✅ v0.12.0 動作中 |
| ComfyUI 配置 | ✅ WSL 内（Hermes と同居）|
| comfy-cli | ✅ v1.7.3 (`~/.local/bin/comfy`) |
| Anima 3ファイル | ✅ base / Qwen3 TE / VAE 配置済み |
| mirrored networking | ✅ 設定済み（Phase 2 で対応）|
| 公式 `comfyui` skill | ✅ Hermes bundled v5.1.0 |
| 不可思議ちゃん workflow JSON | ❌ 未入手 → Phase 3 着手前に user DL 必須 or 代替策 |

**重要**: Hermes と ComfyUI が**両方 WSL 上**なので、ネットワーク問題ゼロ。
Phase 2 のような CDP / mirrored networking 問題は発生しない。
localhost:8188 で直結する。

---

## アーキテクチャ

```
Phase 2 完了状態:
outputs/hermes_pipeline/<work>/
├── grok_inputs/scene_NNN.txt        (5 files)
└── grok_responses/scene_NNN_response.txt  (5 files, 日英両セクション + thinking time除去済)

           ↓ Phase 3 ↓

Step 1: English version 抽出 + Anima 品質タグ前置
  - prepare_prompt.py
  - scene_NNN_response.txt → english_prompt_NNN.txt

Step 2: workflow JSON にプロンプト注入
  - workflow_anima_base.api.json をテンプレに、CLIPTextEncode の text を english_prompt に差し替え
  - LoraLoaderModelOnly が必要なら追記（MVP は LoRAなしでOK）

Step 3: ComfyUI に投げて画像生成
  - ComfyUI REST/WebSocket API 経由 (port 8188)
  - workflow を POST /prompt
  - WebSocket で進捗監視
  - 完了したら history から画像 URL 取得 → DL → 保存

Step 4: 結果保存
outputs/hermes_pipeline/<work>/
├── anima_prompts/english_prompt_NNN.txt   (中間生成物、デバッグ用)
└── images/scene_NNN.png                    (最終出力)
```

---

## 各コンポーネント詳細

### 1. English version 抽出 (`prepare_prompt.py`)

Grok の応答は次のような構造になっている（クリーン後）:
```
日本語版（人間チェック用）
中野一花
位置・姿勢：...
...

【English Version（ComfyUI / Anima投入用）】
nakano_ichika, go-toubun_no_hanayome, 1girl, short_hair, ...
Scene N — title
...
```

抽出ロジック:
- 区切りパターン候補: `# English version`, `【English Version】`, `# English Version` 等の正規表現マッチ
- 末尾までを抽出
- セクション見出し（`Position & posture:`, `[Composition]`等）はそのまま残す
- 場合により `[Composition]` セクションは prompt 本文と統合する（自然言語のため）

**注意**: Scene 3 のように構造崩壊しているケースの handling
→ 区切り見出しが見つからない場合は警告ログを出して全体を投入 or skip

### 2. Anima 品質タグ前置

抽出した English version の冒頭に Anima 推奨のタグセットを追加する:

```
score_9, score_8_up, score_7_up, masterpiece, best quality,
year 2025, newest, sensitive,
{抽出済み english prompt}
```

理由（CG ガイド §06より）:
- score_系 と masterpiece系 両方併用可
- year 2025 + newest で絵柄トレンド指定
- sensitive はポジ/ネガ両方推奨だが、Anima では LLM TE が解釈可能なので一旦ポジのみ

CLAUDE.md ルール「SDプロンプトに吹き出し/擬音/ネガティブを入れない」に従いネガは**空**で行く（または最小限）。

### 3. workflow JSON 構造

Anima 標準 workflow ノード構成（HuggingFace 公式 example ベース）:
```
UNETLoader (anima-preview3-base.safetensors)
  ↓ model
[LoraLoaderModelOnly (オプション、MVP では無し)]
  ↓ model
ModelSamplingAuraFlow (shift=3.0)
  ↓ model
KSampler (steps=30-50, cfg=4-5, sampler=er_sde or euler_a)
  ↓ latent
VAEDecode (qwen_image_vae.safetensors)
  ↓ image
SaveImage

並行:
CLIPLoader (qwen_3_06b_base.safetensors) → CLIPTextEncode (positive) → KSampler
                                          → CLIPTextEncode (negative) → KSampler
EmptyLatentImage (1024x1024) → KSampler
```

**workflow_anima_base.api.json** をテンプレ化:
- 上記ノード構成を API-format JSON で記述
- positive prompt の `text` フィールドを `{PROMPT_PLACEHOLDER}` にしておく
- prepare_prompt.py 出力を `{PROMPT_PLACEHOLDER}` に文字列置換 or jsonパッチで注入

**workflow JSON の入手手段（user 事前準備）**:
- 案A: 不可思議ちゃん配布版（note.com/ogre/n/nc3a66ee7f012）→ DL → API export
- 案B: HuggingFace circlestone-labs/Anima のモデルカード トップ画像 → ComfyUI にドロップ → Workflow → Export (API)
- 案C: 公式 `comfyui` skill の `workflows/` 内に Anima 例があるか確認 → 流用

MVP は **案B** が最速（DL するファイル少、すぐ試せる）。
不可思議ちゃん版は LoRA対応 + サイズUI付きなので Phase 4 で乗り換え推奨。

### 4. ComfyUI API 呼び出し

公式 `comfyui` skill v5.1.0 が以下を提供:
- `scripts/_common.py` — HTTP 共通、cloud routing
- `references/rest-api.md` — エンドポイント仕様
- `references/workflow-format.md` — API-format JSON 仕様

これを **直接呼び出し**ではなく、本 skill `daihon-comfyui-anima` から **委譲**する:

```
daihon-comfyui-anima skill が実行:
1. prepare_prompt.py で english_prompt_NNN.txt 生成
2. workflow JSON ロード → text フィールドを english_prompt で置換
3. POST http://localhost:8188/prompt {"prompt": <patched_workflow>}
4. WebSocket ws://localhost:8188/ws で進捗監視
5. completion 時、GET /history で出力 image filename を取得
6. GET /view?filename=... で画像 DL
7. outputs/.../images/scene_NNN.png に保存
```

直接 REST 叩く（公式 skill の Python ヘルパー流用）。

### 5. 失敗・リトライ設計

- 各シーン処理に **300秒タイムアウト**（Anima 1024x1024 / 50 steps で実測 30-90秒、念のため余裕）
- ComfyUI server 未起動 → エラーで stop、user に `comfy launch --background` を依頼
- OOM / VRAM 不足 → 解像度を 768x768 にフォールバック試行 (1回)
- 連続 3 シーン失敗 → 全体停止、user 判断

---

## 実装方針

### 新 skill `daihon-comfyui-anima` を作る

```
hermes_pipeline/hermes_skill/daihon-comfyui-anima/
├── SKILL.md
├── scripts/
│   ├── prepare_prompt.py        # English抽出 + 品質タグ前置 (CLI)
│   ├── run_anima_scene.py       # 1シーン分の workflow 注入 + API 呼び出し + 画像保存
│   └── batch_runner.py          # 全 pending シーンをループ
└── workflows/
    └── anima_base.api.json      # Anima 標準 workflow テンプレ (user が事前準備)
```

### Hermes Agent の役割

Phase 2 と同じく、Hermes Agent は SKILL.md の Procedure を読んで terminal ツールで scripts を呼ぶ。Phase 2 と違って**ブラウザ操作は不要**（ComfyUI と直結）なので、LLM 判断ステップが減りコスト・速度ともに改善する。

推定 LLM コスト: **5シーンで $0.02 程度**（Phase 2 より少ない）。

---

## SKILL.md 構成案

```yaml
---
name: daihon-comfyui-anima
description: Daihon Rakku → Grok web 経由で書き換えられた scene_NNN_response.txt
            の英語版を ComfyUI/Anima に投入し、画像を生成・保存するバッチスキル。
version: 0.1.0
metadata:
  hermes:
    tags: [creative, comfyui, anima, daihon-rakku, batch]
    requires_toolsets: [terminal]
    category: creative
---

# Procedure
1. ComfyUI 稼働確認 (curl http://localhost:8188/system_stats)
   - 起動していなければ user に `comfy launch --background` を依頼して中断
2. work_dir/grok_responses/ から pending シーン列挙
   - 既に images/scene_NNN.png があればスキップ
3. Step 1 で 1 回だけ「N シーン処理、推定コスト $X、続行?」確認
4. yes を得たら全シーンを自動進行（逐次確認禁止、Phase 2 SKILL.md と同思想）
5. 各シーン:
   a. prepare_prompt.py で english_prompt_NNN.txt 生成
   b. run_anima_scene.py で workflow 投入 + 画像保存
   c. 失敗時は scene_NNN.error.txt 記録
6. 完了後、status JSON で総括
```

---

## MVP 実行手順

```bash
# 1. ComfyUI 起動 (WSL 内、初回のみ)
comfy launch --background

# 2. 起動確認
curl http://localhost:8188/system_stats

# 3. workflow JSON 準備 (user 事前作業、案B)
#    - HuggingFace circlestone-labs/Anima のモデルカード画像をComfyUIにドロップ
#    - "Workflow → Export (API)" でJSON保存
#    - F:/作業/AI開発/Daihon_Rakku/hermes_pipeline/hermes_skill/daihon-comfyui-anima/workflows/anima_base.api.json に置く

# 4. Hermes Agent で skill 実行
hermes chat
# 中で:
# > daihon-comfyui-anima を以下のディレクトリで実行して:
#   /mnt/f/作業/AI開発/Daihon_Rakku/outputs/hermes_pipeline/中野一花..._export_20260506014006/
#   MVP テストなので 5 シーン全部処理。
```

---

## user 事前準備

| # | 作業 | 所要 | 備考 |
|---|---|---|---|
| 1 | ComfyUI サーバー起動 (`comfy launch --background`) | 1分 | 初回のみ |
| 2 | Anima workflow JSON 入手 | 5-10分 | 案B 最速。HuggingFace モデルカード画像 → ComfyUI ドロップ → API Export |
| 3 | workflow JSON を `hermes_pipeline/hermes_skill/daihon-comfyui-anima/workflows/anima_base.api.json` に配置 | 1分 | |

---

## コスト試算

| | 推定 |
|---|---|
| Hermes 内部 LLM (skill 実行判断) | 5シーンで $0.02 程度 (Phase 2 の 1/10) |
| ComfyUI ローカル実行 | $0 (ローカル GPU の電力のみ) |
| Comfy Cloud (使う場合) | $0.10-0.30 / 100シーン |
| **MVP 5シーン総額** | **$0.02 程度** |
| 本番 100シーン総額 | $0.5 程度 + 電力代 |

Phase 2 より大幅に低コスト（LLM 判断ステップが減るため）。

---

## ユーザー確認事項

1. 上記方針で進めて良いか?
2. workflow JSON は案B（HuggingFace モデルカード由来）で MVP 始めて、後で不可思議ちゃん版に差し替えで良いか?
3. ネガティブプロンプトは**空**で行く方針で良いか?（CLAUDE.md準拠）
4. 画像解像度は 1024x1024 デフォルト、VRAM 不足時 768x768 フォールバックで良いか?

確認取れたら実装着手する。
