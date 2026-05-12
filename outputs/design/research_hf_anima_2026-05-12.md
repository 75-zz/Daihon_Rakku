# HuggingFace Anima系 調査レポート
**日付**: 2026-05-12  
**調査者**: hf-researcher  
**対象**: circlestone-labs/Anima、AnimaYume v0.4、Animax — 挙動差・推奨用途・Qwen3 TE特性

---

## 1. モデル系統図

```
NVIDIA Cosmos-Predict2-2B-Text2Image (基盤)
└── circlestone-labs/Anima (Preview3 = 現行 base)
    ├── AnimaYume v0.4 (CivitAI / duongve/AnimaYume on HF) ← 今回の調査対象「勝ちUNet」
    ├── Animax v0.5 (CivitAI のみ)
    ├── HarmoniQMix Anima v0.61
    └── その他 19+ HF fine-tune
```

---

## 2. Anima Base / AnimaYume / Animax 挙動差・推奨用途

| 項目 | Anima Base (Preview3) | AnimaYume v0.4 | Animax v0.5 |
|------|----------------------|----------------|-------------|
| **定義** | CircleStone Labs 公式 2B DiT | Anima からの fine-tune（独立作者） | Anima からの fine-tune（独立作者） |
| **HF公式リポジトリ** | `circlestone-labs/Anima` | `duongve/AnimaYume` 等ミラー3件 | HFなし（CivitAI専用） |
| **訓練フォーカス** | 汎用アニメ/イラスト。合成データなし。アニメ知識CutOff 2025-09 | プロンプト理解とアーティストスタイル認識の強化。CivitAI ユーザープロンプトで評価 | アニメ/2D特化 fine-tune（詳細非公開） |
| **デフォルトスタイル** | 非常にニュートラル/プレーン（意図的）。アーティスト・品質タグ必須 | Base より安定した出力傾向 | Base 準拠（設定差なし） |
| **推奨用途** | LoRA学習ベース。汎用性重視 | スタイル一貫性・プロンプト追従が重要な本番生成 | 同左 |
| **CFG** | 4–5 | 4–7 | 4–5 |
| **Steps** | 30–50 | 25–40 | 30–50 |
| **推奨Sampler** | er_sde（デフォルト推奨） / euler_a / dpmpp_2m_sde_gpu | euler_a | er_sde / euler_a / dpmpp_2m_sde_gpu |
| **LoRA強度公式推奨** | 非公表 | 非公表 | 非公表 |
| **出典** | HF README | CivitAI + duongve/AnimaYume HF | CivitAI |

### Sampler 特性（全variant共通）

| Sampler | 特性 |
|---------|------|
| `er_sde` | ニュートラル。フラットカラー・シャープライン。**デフォルト推奨** |
| `euler_a` | ソフトライン・2.5D傾向。高CFGに耐性。AnimaYume 公式推奨 |
| `dpmpp_2m_sde_gpu` | er_sde類似だが多様性・創造性が高い。ワイルドになり得る |
| beta57 scheduler | ペインタリー/リアル寄りテクスチャ改善（ComfyUI RES4LYF要） |

---

## 3. Qwen3-0.6B Text Encoder の特性

### 3.1 アーキテクチャ

| 項目 | 詳細 |
|------|------|
| モデル | `qwen_3_06b_base.safetensors`（**base** バリアント必須、aligned版NG） |
| 次元数 | 1024次元（T5XXLの4096次元より小さい） |
| Adapter | 6層 LLM Adapter が Qwen3 → DiT cross-attention KV を橋渡し |
| Context長 | DiT cross-attention に渡されるコンテキスト: **512トークンにパディング** |
| Attention | **Causal（因果的）アテンション** — 後続トークンは先行トークンを参照できない |
| Position | **RoPE（Rotary Position Embedding）** — 絶対位置が hidden state に影響 |

### 3.2 512トークン制限の実態

- DiT の cross-attention が受け取る KV は最大 **512トークン長**にパディングされる
- Qwen3 tokenizer は T5 tokenizer と異なるトークン分割を行う
- アーティストタグ消費量の目安：
  - `@wlop`（3 tokens）
  - `@tianliang duohe fangdongye`（13 tokens）
  - アーティスト5名 = 約15〜65 tokens
  - 12名実験 = context の相当部分を消費
- **自然言語の長い説明文はアーティストタグとトークンを奪い合う**
- 512トークン超過に対する明示的な警告ログは公式文書に記載なし（実装ベース制限）

### 3.3 Natural Language vs Danbooru Tag

| 比較軸 | Natural Language | Danbooru Tag |
|--------|-----------------|--------------|
| 精度 | 2文以上でないと予期しない出力が出る | より安定 |
| Qwen3.5 4B実験 | 0.6Bより**劣化**した | 0.6B と同等 |
| 推奨配置 | 品質・アーティストタグの後に自然文を続ける | 先頭推奨 |
| 混在 | 任意の順序で混在可能（公式） | — |
| 注意点 | Causal attentionにより後続タグが先行文の影響を受ける | — |

**実用推奨プロンプト構造**:
```
[quality/score tags], [safety tag], [year tag], @artist_name, [1girl/1boy], [character], [series], [scene description in natural lang or tags]
```

### 3.4 @artistトリガーの効き

- **`@`プレフィックスは必須** — なしの場合「効果が非常に弱い」と公式明記
- 配置: 品質タグ直後、scene descriptionより前
- 長い名前ほど位置依存ドリフトに強い（cosine安定性: 0.978 vs 0.939）
- **複数アーティスト混在の問題**:
  - Causal attentionにより後続アーティストベクターが先行文脈で汚染される
  - 2〜3名まで推奨。12名実験ではpixel差分 9〜69 まで劣化
  - 現時点の回避策: カスタムComfyUIノードでアーティストベクターをlockする（部分的効果）

---

## 4. LoRA 運用パラメーター（開発者公式推奨）

| パラメーター | 推奨値 | 備考 |
|-------------|--------|------|
| LR | `2e-5`（rank 32時） | これより高いと forgetting が加速 |
| Optimizer | AdamW | — |
| Rank / Alpha | 32 / 32 | — |
| Global batch size | 16 | — |
| LLM adapter LR | **0（凍結必須）** | 影響が過大。訓練で容易に劣化 |
| 訓練スクリプト | diffusion-pipe（作者推奨） | sd-scripts でも `llm_adapter_lr=0` 設定可能 |
| 最小訓練データ | 200枚（viable） / 400枚+（推奨） | 少ないほど forgetting リスク大 |
| 正則化画像 | 約22%の無関係画像（3.5:1比） | Forgetting 抑制に有効 |
| 解像度 | 512px（訓練時） | — |

**LoRA 使用時の強度推奨**: 公式・コミュニティともに数値非公表。AnimaYume/Animax 固有の推奨なし。

---

## 5. AnimaYume 独立リポジトリの有無・訓練詳細

| 項目 | 状況 |
|------|------|
| **CircleStone Labs HF** | `circlestone-labs/Anima` 1件のみ公開。AnimaYume なし |
| **AnimaYume HF** | `duongve/AnimaYume`（主）+ ミラー2件（非公式アップロード） |
| **主要配布** | CivitAI（`civitai.com/models/2385278/animayume`） |
| **訓練config** | 非公開。「大規模AIクラスターで訓練」との記載のみ |
| **訓練データ** | Danbooru データセット使用。詳細非開示 |
| **v0.4の変更点** | プロンプト理解・アーティストスタイル認識の強化。Preview3 継承バグの修正 |

---

## 6. Animax との差分まとめ

| 比較軸 | AnimaYume v0.4 | Animax v0.5 |
|--------|---------------|-------------|
| 配布場所 | CivitAI + HF（ミラー） | CivitAI のみ |
| 評価 | CivitAI 多数サンプル | 125件「very positive」 |
| 設定差 | CFG 4–7、euler_a 推奨 | CFG 4–5、er_sde 推奨 |
| スタイル方向性 | プロンプト追従・アーティスト忠実度重視 | 詳細不明 |
| コミュニティ採用 | Daihon Rakku チーム調査で「勝ちUNet」と判定 | 候補止まり |

---

## 7. Daihon Rakku Phase 3 への適用提案

### 提案 A: プロンプト構造の固定化
現状の Grok → Anima 生成パスで、以下の構造を **Grok 出力テンプレートに固定**する:
```
masterpiece, best quality, score_7, explicit, year 2025, @[artist], 1girl, [character], [series], [scene_nl_description]
```
- アーティストを品質タグ直後に配置 → Causal attention の位置ドリフト最小化
- 自然言語は末尾に集約 → トークン競合を後ろに逃がす

### 提案 B: トークン予算管理
- プロンプト全体を **450 tokens 以内**に収める（512上限に20%マージン）
- アーティスト指定は **1〜2名まで** を推奨ルールに追加
- sd_prompt_natural_en 生成時に概算トークン数チェックを追加（後処理側）

### 提案 C: LoRA 運用注意点
- AnimaYume 用LoRAを新規学習する際は必ず `llm_adapter_lr=0`
- 強度（weight）の公式値なし → 実験で 0.6〜1.0 から探索
- 学習データが少ない（<200枚）場合は forgetting リスクを明示してユーザーに警告

### 提案 D: Sampler 選択ガイド
| 用途 | 推奨Sampler |
|------|-------------|
| 標準生成（線画クリア） | `er_sde` |
| ソフトスタイル・官能表現 | `euler_a` CFG 5–6 |
| バリエーション探索 | `dpmpp_2m_sde_gpu` |

---

## 8. 出典

- [circlestone-labs/Anima README](https://huggingface.co/circlestone-labs/Anima)
- [HF Discussion #112: Artist style inconsistency](https://huggingface.co/circlestone-labs/Anima/discussions/112)
- [HF Discussion #63: Scaling up Qwen3 TE](https://huggingface.co/circlestone-labs/Anima/discussions/63)
- [HF Discussion #75: Qwen3.5 4B TE with Anima 2B](https://huggingface.co/circlestone-labs/Anima/discussions/75)
- [AnimaYume v0.4 - CivitAI](https://civitai.com/models/2385278/animayume)
- [Animax v0.5 - CivitAI](https://civitai.com/models/2414435/animax-anima-finetune-model)
- [duongve/AnimaYume - HuggingFace](https://huggingface.co/duongve/AnimaYume)
- [Fine-tuned models list](https://huggingface.co/models?other=base_model%3Afinetune%3Acirclestone-labs%2FAnima)
