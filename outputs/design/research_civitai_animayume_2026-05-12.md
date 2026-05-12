# AnimaYume v0.4 CivitAI 調査レポート
**調査日:** 2026-05-12  
**調査者:** civitai-researcher  
**対象:** AnimaYume v0.4 (civitai.com/models/2385278) および関連 Anima エコシステム

---

## 1. AnimaYume v0.4 基本情報

| 事実 | 出典URL | 適用提案 |
|------|---------|---------|
| AnimaYume は Anima Preview 3 ベースの fine-tune。アーキテクチャは Diffusion Transformer (DiT)、SDXL/Illustrious 系とは完全別物 | https://civitai.com/models/2385278/animayume | SDXL系LoRAは使用不可。Anima専用LoRAのみ互換 |
| ファイル形式: BF16 SafeTensor (3.89GB)、Hash: AutoV2 81671B95D9 | https://civitai.com/models/2385278/animayume | compare_models_v2.py での identify に使用可 |
| v0.4 は Anima Preview 3 で学習、「プロンプト理解と画風認識を改善」。ただし作者自身「テストケースは限定的、包括的検証なし」と明言 | https://civitai.com/models/2385278/animayume | 未検証パラメータ範囲が広い。V06-V08 優勢評価の信頼性は実測に委ねる |
| VAE (`qwen_image_vae.safetensors`) と Text Encoder (`qwen_3_06b_base.safetensors`) の別途ダウンロードが必須 | https://civitai.com/models/2458426/anima-official | ComfyUI ワークフローに VAE/TE ロードノードが揃っているか確認必須 |
| 対応解像度: 768-1536px、最適は 1024px 前後 (≈1MP)。2MP 以上で破綻 | https://civitai.com/models/2458426/anima-official | 生成サイズは 896×1152 または 1024×1024 推奨。高解像度は img2img upscale で対応 |

---

## 2. 推奨 Generation Parameters（ギャラリー実例 + 公式・コミュニティ情報）

> **注意:** AnimaYume v0.4 ページ自体にはギャラリー画像の具体的パラメータが非公開。  
> Anima Official / WAI-ANIMA / AnimaIka などの Anima Preview 3 系モデルの実測値で代替。

### 2-1. サンプラー比較

| サンプラー | 特性 | 事実・出典 | 適用提案 |
|-----------|------|----------|---------|
| **er_sde** | フラットカラー・シャープ線画・安定重視 | Anima Official 推奨: https://civitai.com/models/2458426/anima-official | **第1推奨**。キャラ顔・衣装の一貫性が高い |
| **euler_a** | 柔らかい線、2.5D風、やや細め | Anima Official / AnimaIka 両方が推奨 | 表情・エモーション重視シーンに向く |
| **dpmpp_2m_sde_gpu** | er_sde 似だが「創造的バリエーション過多」、プロンプトによって暴走 | Anima Official 注記 + DiffusersのSDXL artifact issue報告 (https://github.com/huggingface/diffusers/issues/6295) | **使用非推奨**。V06-V08 破綻原因の有力候補。er_sde または euler_a へ差替えを強く推奨 |
| ER SDE Beta / Euler a Normal | WAI-ANIMA 推奨 | https://civarchive.com/models/2544636 | er_sde の beta スケジュールは AnimaIka でも有効 |

### 2-2. 推奨パラメータ一覧

| パラメータ | 推奨値 | 根拠出典 |
|-----------|-------|---------|
| Sampler | `er_sde` (第1推奨) / `euler_a` (第2) | https://civitai.com/models/2458426/anima-official |
| Scheduler | `beta` または `simple` | https://civitai.com/models/2426265/animaika |
| CFG Scale | **3–5**（3.5 付近が安全圏） | Anima Official: 4-6 / WAI-ANIMA: 4-5 / AnimaIka: 3-5 の共通域 |
| Steps | **30–50**（デフォルト 30 でも十分） | https://civitai.com/models/2426853/anima-preview-workflow |
| Resolution | **896×1152** (portrait) / 1024×1024 (square) | Anima Official ≈1MP 推奨 |
| Clip Skip | 未公式指定（Danbooru系 = 通常 1 が安全） | - |
| Hires.fix | **非推奨**。img2img アップスケールを使用 | WAI-ANIMA コミュニティ + AnimaIka 作者注記 |

### 2-3. プロンプト構造例（Anima Official + WAI-ANIMA 実例）

```
Positive prefix:
masterpiece, best quality, score_7, safe, [character tags], [series], [general tags]

Negative:
worst quality, low quality, score_1, score_2, score_3, artist name, blurry, jpeg artifacts, lowres, censor
```

**タグ順序（AnimaV4ワークフロー推奨）:**  
`quality/meta/year/safety tags → character → series → artist → general tags`

**注意:** タグはすべて**小文字**、Danbooru 形式。アーティストタグは `@` プレフィックス必須。

---

## 3. キャラ特徴破綻を防ぐタグ組合せ実例

| 問題 | 事実 | 出典 | 適用提案 |
|------|------|------|---------|
| アクセサリー・髪型が崩れる | WAI-ANIMA コミュニティ: 「複雑なキャラアクセサリーは苦手」 | https://civarchive.com/models/2544636 | 重要特徴はプロンプト先頭寄りに配置。例: `pink hair, short hair, blue eyes` を character tags 直後 |
| 複数キャラ混在で顔崩れ | AnimaIka v3.5 では低品質シードのバリエーションを reduce する merge が有効 | https://civitai.com/models/2426265/animaika | 1シーン1キャラに限定。複数人物が必要な場合は er_sde + steps 40以上で安定 |
| CFG 高すぎで色飽和 | RenormCFG ノード ≈1.1 で抑制可能 | Anima Official コミュニティ情報 | CFG が 5 を超える場合は ComfyUI に `RenormCFG` ノードを追加 |
| natural language と Danbooru タグ混在で崩れ | WAI-ANIMA はnatlang強み弱体化の報告あり | https://civarchive.com/models/2544636 | AnimaYume では **Danbooru タグ統一**を推奨。自然文の混在は最小化 |
| 顔・手のディテール崩れ | Anima V4 Workflow が Impact-Pack (detailer) を標準採用 | https://civitai.com/models/2426853/anima-preview-workflow | ComfyUI ワークフローに `FaceDetailer` / `HandDetailer` ノードを追加 |

---

## 4. 中野一花 / 五等分の花嫁系キャラLoRAの状況

| LoRA名 | ベースモデル | Anima/AnimaYume互換 | 事実・出典 |
|--------|------------|-------------------|---------|
| Nakano Ichika v1.4.1 | SD1.5系（旧型） | **非互換** | https://civitai.com/models/208999/nakano-ichika-gotoubun-no-hanayome |
| [IL] Ichika Nakano v1.0il | Illustrious XL | **非互換**（DiT と別アーキテクチャ） | https://civitai.com/models/1913040/il-ichika-nakano-5-toubun-no-hanayome |
| Nakano Ichika Illustrious v1.0 | Illustrious | **非互換** | https://civitai.com/models/2488701/nakano-ichika-go-toubun-no-hanayome |
| Anima専用中野一花LoRA | - | **現時点で CivitAI に存在を確認できず** | 2026-05-12 調査 |

**重要結論:** Anima/AnimaYume の Diffusion Transformer アーキテクチャ向け中野一花 LoRA は **現時点で CivitAI に存在しない**。SD1.5・SDXL・Illustrious 系 LoRA は全て非互換。

**代替案:**
1. `Any Anima Yume (for LoRA training)` チェックポイント + Anima LoRA Trainer for ComfyUI を使って自前学習（学習に約 30-100 枚の高品質キャプション付き画像が必要）
2. Anima 公式プロンプトで `nakano_ichika, pink hair, short hair, blue eyes, school uniform` の Danbooru タグをフル指定して特徴固定（LoRA なし）

---

## 5. AnimaYume 向け品質強化LoRA（masterpieces v5 以外）

| LoRA名 | 目的 | ベース互換 | 推奨設定 | 出典 |
|--------|------|----------|---------|------|
| **RDBT - Anima (p3 v0.29.b)** | スタイル蒸留 + 高速生成 (12 NFEs) | Anima Preview 3 系 ✓ | steps 12+、CFG はデフォルト | https://civitai.com/models/2364703/rdbt-anima |
| **Anima Turbo LoRA v0.1** | 解剖学安定 + スタイル一貫性 + 高速化 (8-12 steps) | Anima Preview 3 系 ✓ | CFG=1, steps=8-12, strength<1.0 でバリエーション増加 | https://civitai.com/models/2560840/anima-turbo-lora |
| **WAI-ANIMA (merged checkpoint)** | 彩度・スタイル一貫性改善、AnimaYume とのマージ派生 | Anima Preview 3 系 ✓ | steps=20-30, CFG=4-5, Euler a Normal | https://civarchive.com/models/2544636 |

**注意:** 上記3つは **quality LoRA ではなく style/speed 特化**。「masterpieces v5 相当の純品質強化 LoRA」は現時点で Anima エコシステムに未確認。品質向上は quality プレフィックス (`masterpiece, best quality, score_7`) + detailer ノードで対応。

---

## 6. dpmpp_2m_sde_gpu 破綻の原因分析

| 事実 | 出典 | 適用提案 |
|------|------|---------|
| Anima 公式: dpmpp_2m_sde_gpu は「er_sde 似だがプロンプトによって暴走的バリエーション」と注記 | https://civitai.com/models/2458426/anima-official | 安定性要求シーンでは使用しない |
| DPM++ 2M SDE 系はアーキテクチャによってアーティファクト既知問題。Diffusers #6295 で SDXL での artifact 報告あり。DiT 系でも同傾向の可能性 | https://github.com/huggingface/diffusers/issues/6295 | Anima DiT での固有問題の可能性。er_sde に切替えで回避 |
| AnimaIka (AnimaYume マージ含む) は ER SDE + Euler a のみ推奨。dpmpp 系は推奨リストに未掲載 | https://civitai.com/models/2426265/animaika | AnimaYume でも dpmpp_2m_sde_gpu は非推奨として扱う |
| WAI-ANIMA: 「Euler A Normal または ER SDE BETA」を推奨 | https://civarchive.com/models/2544636 | 推奨 2 サンプラーに絞ることでバリエーション実験が安定 |

**根本原因仮説:** dpmpp_2m_sde_gpu は DiT ベースの Anima アーキテクチャとスケジューラーの相性問題で過剰ノイズ注入が起きやすく、プロンプト遵守が弱い場面でキャラ破綻に繋がる。er_sde はこのアーキテクチャに最適化されたサンプラーである可能性が高い。

---

## 7. 次アクション提案（compare_models_v2.py V16-V25 設計向け）

| 優先度 | 提案 | 根拠 |
|--------|------|------|
| **高** | dpmpp_2m_sde_gpu → **er_sde** に全面切替えて V06-V08 を再現 | 本調査で破綻原因として最有力 |
| **高** | CFG=3.5, steps=35, scheduler=beta を基準設定として固定 | Anima 系コミュニティ共通安定域 |
| **高** | ComfyUI ワークフローに FaceDetailer を追加 | 顔崩れ対策の最高効果 |
| **中** | キャラタグを positive prompt 先頭に固定（`pink hair, short hair, blue eyes` 等） | アクセサリー崩れ防止 |
| **中** | Anima Turbo LoRA v0.1 (strength=0.8) を V16 バリアントに追加 | 解剖学安定 + Anima 互換確認済み |
| **低** | 中野一花 LoRA: `Any Anima Yume` ベースで自前学習 | 学習コスト大。まずタグ固定で代用 |

---

## 8. 出典一覧

- [AnimaYume v0.4](https://civitai.com/models/2385278/animayume)
- [Anima Official preview3-base](https://civitai.com/models/2458426/anima-official)
- [WAI-ANIMA CivArchive](https://civarchive.com/models/2544636?modelVersionId=2859702)
- [RDBT - Anima p3](https://civitai.com/models/2364703/rdbt-anima)
- [Anima Turbo LoRA v0.1](https://civitai.com/models/2560840/anima-turbo-lora)
- [Anima Preview Workflow V4.0](https://civitai.com/models/2426853/anima-preview-workflow)
- [Any Anima Preview for LoRA training](https://civitai.com/models/2454865/any-anima-preview-for-lora-training)
- [Anima LoRA Trainer for ComfyUI](https://civitai.com/models/2502969/anima-lora-trainer-for-comfyui)
- [AnimaIka v3.5](https://civitai.com/models/2426265/animaika)
- [Nakano Ichika (Gotoubun) v1.4.1 SD1.5](https://civitai.com/models/208999/nakano-ichika-gotoubun-no-hanayome)
- [Nakano Ichika Illustrious v1.0](https://civitai.com/models/2488701/nakano-ichika-go-toubun-no-hanayome)
- [DPM++ 2M SDE artifact issue (Diffusers #6295)](https://github.com/huggingface/diffusers/issues/6295)
