# hermes-anima パイプライン v9 完全再現手順書

**作成日**: 2026-05-12
**対象**: Daihon Rakku → Grok web → ComfyUI/AnimaYume パイプライン
**ブランチ**: `feature/hermes-anima-pipeline`
**確立コミット**: (未push、本書執筆時点でローカル変更あり)

新規キャラ・新規作品でも同じ手順で再現可能な状態にする。

---

## 0. 前提インフラ

### 0.1 必要モデル (WSL2 内)
```
~/comfy/models/diffusion_models/
  ├ anima-preview3-base.safetensors
  ├ animayume_v04.safetensors          ★ 本番採用 UNet
  └ animaxAnimaFinetune_v05.safetensors

~/comfy/models/loras/
  ├ anima-preview-3-masterpieces-v5.safetensors  ★ 本番採用 LoRA (strength 0.5)
  └ mixed_styles_anima_preview3_v4.safetensors   (実験用、本番では未使用)

~/comfy/models/text_encoders/
  └ qwen_3_06b_base.safetensors        ★ Anima 標準 CLIP

~/comfy/models/vae/
  └ qwen_image_vae.safetensors         ★ Anima 標準 VAE
```

### 0.2 ComfyUI 起動 (毎回必須)
```bash
wsl
~/comfy/.venv/bin/python ~/comfy/main.py \
  --listen 127.0.0.1 --port 8188 --reserve-vram 2.5
```
- ⚠️ `comfy launch --background` は Python 3.14 で壊れている（asyncio 仕様変更）
- `--reserve-vram 2.5` は **必須** (16GB GPU で VRAM 飽和ハング防止)
- 起動完了確認: `curl http://localhost:8188/system_stats`

---

## 1. ワークフロー概要 (4 Phase)

```
┌────────────────────────────────────────────────────────────────┐
│  Phase 1: Daihon Rakku (デスクトップ)                              │
│    ├─ シーン生成 (脚本+Danbooru タグ)                              │
│    ├─ 男性キャラ設定 (config.json: male_preset/hair/skin)          │
│    └─ ZIP エクスポート (script_*.csv / sd_*.txt / fukidashi_*.csv) │
└──────────────────────────────┬─────────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────────┐
│  Phase 2: Grok web (Hermes Agent browser skill)                 │
│    ├─ scene_NNN.txt を Grok web に逐次投入                         │
│    └─ scene_NNN_response.txt を取得 (日英両セクション)             │
└──────────────────────────────┬─────────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────────┐
│  Phase 3: ComfyUI/AnimaYume (本書のスコープ)                       │
│    ├─ character.json 配置 (Daihon Rakku 派生、手動)                │
│    ├─ prepare_prompt.py で anima_prompts/ 生成                     │
│    └─ compare_models_v2.py で 画像生成 (V08 × N seed)              │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. キャラ追加・更新の手順

### 2.1 新規キャラ追加 (まだ Daihon Rakku に preset が無い場合)
1. Daihon Rakku gui.py でキャラプール作成
2. `presets/characters/char_*.json` の `danbooru_tags` を必ず **Danbooru wiki** で検証
   - `https://danbooru.donmai.us/wiki_pages/<character_tag>` を WebFetch
   - LLM (Claude / Grok) のキャラタグ知識は信頼しない (orange_hair / long_hair 等の幻覚あり)
3. `physical_description.clothing` も同 wiki で確認

### 2.2 中野一花プリセット (2026-05-12 正規版)
```json
"danbooru_tags": [
  "nakano_ichika", "go-toubun_no_hanayome", "1girl",
  "short_hair", "pink_hair", "bangs", "hair_between_eyes",
  "asymmetrical_sidelocks", "blue_eyes", "large_breasts"
],
"danbooru_tags_negative": [
  "long_hair", "orange_hair", "brown_hair", "blonde_hair"
],
"danbooru_tags_meta": {
  "weight": 1.2,
  "source": "https://danbooru.donmai.us/wiki_pages/nakano_ichika",
  "verified_date": "2026-05-12"
}
```

---

## 3. work_dir/character.json の作成 (Phase 3 投入用)

### 3.1 必須フィールド
1. `character_name` / `work_title` / `char_id` (preset から)
2. `danbooru_tags` (preset から)
3. `danbooru_tags_negative` (preset から)
4. `appearance_sentence_en` — ヒロイン外見の自然言語（Anima Qwen3 TE 用）
5. `heroine_outfit`:
   - `outfit_tags`: ヒロイン base 衣装 Danbooru タグ
   - `negative_outfit_tags`: ベース衣装に矛盾するアイテム (school_uniform / kimono / off_shoulder 等)
   - `attribution_sentence_en`: "The girl is wearing..." 帰属明示文
6. `male_companion`:
   - `appearance_tags`: 体型・髪・肌（config.json `male_*` 派生）
   - `outfit_tags`: 男性衣装
   - `negative_outfit_tags`: 男性衣装に矛盾するアイテム
   - `attribution_sentence_en`: "Beside her is a faceless..." 帰属明示文
7. `anima_meta`:
   - `weight`: 1.2 (キャラタグ重み)
   - `character_tag` / `series_tag`
   - `with_faceless_male`: 男性同居の場合 true

### 3.2 config.json (Daihon Rakku) からの派生マップ
| config.json | → | character.json 配置 |
|---|---|---|
| `male_preset: "筋肉質の青年"` | → | appearance_tags: `muscular_male, young_man, toned_body` |
| `male_hair_style: "短髪"` | → | appearance_tags: `short_hair` |
| `male_hair_color: "おまかせ"` | → | appearance_tags: `black_hair` (デフォルト推奨) |
| `male_skin_color: "褐色"` | → | appearance_tags: `dark-skinned_male, tanned` |

将来 Phase 2-a (gui.py 改修) で自動派生にする予定。

### 3.3 配置先
```
outputs/hermes_pipeline/<work_name>/character.json
```

---

## 4. anima_prompts 生成

```bash
python3 hermes_pipeline/hermes_skill/daihon-comfyui-anima/scripts/prepare_prompt.py \
  extract outputs/hermes_pipeline/<work> \
  --quality-preset animayume_min \
  --neg-preset animayume_min
```

### 内部処理 (prepare_prompt.py)
1. `extract_english` — `# English version` 以降を抽出
2. `clean_for_anima`:
   - `_DIALOGUE_HEADING_RE`: Dialogue/Sound effects 見出し以降切り捨て
   - `_QUOTED_LINE_RE` / `_QUOTED_LINE_JP_RE`: 行全体の引用符行削除
   - `_QUOTED_INLINE_RE` / `_QUOTED_INLINE_JP_RE`: **本文中の引用符ペア除去** (画面内テキスト化防止)
3. `strip_clothing_state_blocks`:
   - `_CLOTHING_STATE_BLOCK_RE` (IGNORECASE + DOTALL):
   - `Clothing state:` / `Clothing State:` 両対応
   - 単行 (`Clothing state: White blouse...\n`) と複行両形式対応
   - 次セクションヘッダ (`[A-Z][A-Za-z /&-]+:` / `Faceless Male` / `Nakano` / `[`) まで削除
4. `strip_grok_char_tags`: Grok 冒頭の `nakano_ichika, go-toubun..` キャラタグ行削除
5. `build_char_block_from_json`:
   ```
   (キャラ:1.2), シリーズ,
   1girl, [視覚特徴タグ],
   [ヒロイン衣装タグ],
   appearance_sentence_en (NL外見)
   attribution_sentence_en (NL衣装帰属)
   1boy, faceless_male, [男性appearance], [男性outfit],
   attribution_sentence_en (NL帰属)
   ```
6. quality prefix + char_block + 残 Grok 本体 = positive
7. ネガ: `_ANIMAYUME_NEGATIVE_MIN` + `danbooru_tags_negative` + `negative_outfit_tags`

### 出力
```
outputs/hermes_pipeline/<work>/anima_prompts/scene_NNN_prompt.json
```

---

## 5. 画像生成

### 5.1 標準コマンド (V08 × scene 1-5 × 3 seed)
```bash
python3 hermes_pipeline/hermes_skill/daihon-comfyui-anima/scripts/compare_models_v2.py \
  outputs/hermes_pipeline/<work> \
  --scenes 1-5 \
  --variants V08 \
  --seeds 42,7,123 \
  --timeout 500 \
  --output-subdir comparison_v9
```

### 5.2 V08 = 本番標準構成
| 項目 | 値 |
|---|---|
| UNet | `animayume_v04.safetensors` |
| LoRA | `anima-preview-3-masterpieces-v5.safetensors` (strength 0.5) |
| Sampler | `er_sde` |
| Scheduler | `simple` |
| Steps | 30 |
| CFG | 4.0 |
| 解像度 | 1024×1024 |
| Tag profile | `aesthetic` (compare_models_v2 内、ただし character.json 駆動時は使用されず prepared positive をそのまま使う) |

### 5.3 25 variants 完全リスト
`compare_models_v2.py VARIANTS` 参照。V01-V15 が初期比較用、V16-V25 が AnimaYume sweet-spot 探索用（実装済み未必須）。

---

## 6. 完成検証チェックリスト

### キャラ識別
- [ ] 一花: pink_hair / short_hair / blue_eyes / asymmetrical_sidelocks が全シーン安定
- [ ] 男性: 顔なし / muscular / 黒髪短髪 / 褐色肌 が全シーン安定

### 衣装
- [ ] 一花: white_shirt + green_skirt + black_pantyhose で全シーン統一
- [ ] 男性: black t-shirt + black_pants で全シーン統一
- [ ] 状態変化 (脱衣プログレッション) は Grok 自然言語で活きている

### 画面品質
- [ ] 言葉 / 吹き出し / 擬音テキストの混入なし
- [ ] 絵柄の極端なブレなし (close-up / 構図変化以外で違いが大きくない)

### CG 集の見せ場
- [ ] エロ表現 (汗・涙・羞恥・露出) が Grok の描写を活かして表現されている

問題があれば character.json または grok_prompt_builder.py のルールを調整して再生成。

---

## 7. トラブルシューティング

### 「scene X で衣装が違う」
→ `grok_responses/scene_X_response.txt` を確認:
  1. `Clothing State:` 行に矛盾衣装名 (school_blouse / kimono 等) が書かれている?
     → `_CLOTHING_STATE_BLOCK_RE` で除去されるはずだが、変則的な見出し (大文字違い等) は要対応
  2. キャラタグ行に短髪/長髪等の誤タグがある?
     → strip_grok_char_tags で除去
  3. 本文中の他テキストに衣装記述が埋め込まれている?
     → 自然言語 attribution_sentence_en の優先度を上げるしかない（重み付け試行）

### 「言葉が画面内に描画された」
→ `_QUOTED_INLINE_RE` で 200文字以下の引用符ペアを除去しているか確認。
→ ネガに `text, watermark, signature, speech_bubble, dialogue, kanji, hiragana, ...` が入っているか確認。

### 「muscular が女性に転移した」
→ `attribution_sentence_en` で "Beside her is a muscular man..." と帰属明示しているか確認。
→ 並列タグ列で `muscular` が女性ブロック側に紛れていないか確認。

### 「VRAM 飽和 / ハング」
→ ComfyUI を `--reserve-vram 2.5` 付きで再起動。
→ 1 シーン生成失敗時はバッチを止めて comfy を再起動してから再開。

### 「scene Y の構図が他と違う」
→ Grok 出力の `[Composition]` セクション内に shot type / lighting 指定があるか確認。
   無ければ grok_prompt_builder.py のルール「Composition 内に lighting と shot type を必ず明記」を強化。

### 「ComfyUI が起動しない」
→ `comfy launch --background` は Python 3.14 で壊れている。`main.py` 直接起動を使う:
   `~/comfy/.venv/bin/python ~/comfy/main.py --listen 127.0.0.1 --port 8188 --reserve-vram 2.5`

---

## 8. 次の拡張案

### Phase 2-a: gui.py の export 機能改修
- `_do_export` (gui.py:15361) に `character` チェックボックス追加
- `export_character_json(results, path, char_preset)` 関数追加
- ZIP エクスポート時に `character_<timestamp>.json` を自動添付
- 詳細設計: `outputs/design/design_daihon_anima_tags_phase2_2026-05-12.md`

### Phase 2-b: 他キャラ追加
- 二乃 / 三玖 / 四葉 / 五月 の preset 検証 + character.json テンプレ作成
- 既存 preset の `danbooru_tags` 全件検証スクリプト (`scripts/validate_anima_tags.py`)

### Phase 4: エンドツーエンド統合
- Daihon Rakku 内から「Grok 投入 → 画像生成」までを Hermes Agent 経由で自動化
- 現状の手動 ZIP 取り回しを GUI 統合

---

## 9. 関連設計書

| ファイル | 内容 |
|---|---|
| `outputs/design/research_civitai_animayume_2026-05-12.md` | CIVITAI モデル/LoRA リサーチ |
| `outputs/design/research_hf_anima_2026-05-12.md` | HuggingFace circlestone-labs/Anima リサーチ |
| `outputs/design/design_animayume_prompt_template_2026-05-12.md` | プロンプトテンプレ設計（廃止旧版） |
| `outputs/design/design_variant_matrix_v16_v25_2026-05-12.md` | variant matrix 設計 |
| `outputs/design/design_male_outfit_fixed_2026-05-12.md` | 男性衣装固定設計 (v3) |
| `outputs/design/design_heroine_outfit_fixed_2026-05-12.md` | 女性衣装固定設計 |
| `outputs/design/design_daihon_anima_tags_phase2_2026-05-12.md` | gui.py 統合 Phase 2 設計 |
| `outputs/design/research_scene_style_diff_2026-05-12.md` | scene 4/5 絵柄差プロンプト分析 |
| `outputs/design/research_visual_style_diff_2026-05-12.md` | 5シーン視覚解析 |
| `outputs/design/research_clothing_conflict_diagnostic_2026-05-12.md` | 衣装矛盾診断 |
| `outputs/design/impl_clothing_stripper_2026-05-12.md` | Clothing state 機械除去実装メモ |
| `outputs/design/impl_outfit_coverage_expand_2026-05-12.md` | outfit_tags 拡張実装メモ |
| `hermes_pipeline/hermes_skill/daihon-comfyui-anima/SKILL.md` | Hermes Agent 用スキル定義 |

---

## 10. 確立コミットの推奨メッセージ

```
feat(hermes-anima): v9 — character.json駆動 + 自然言語帰属でキャラ・衣装完全固定

主な変更:
- presets/characters/char_a1b2c3d1.json: danbooru_tags正規化 (orange→pink, long→short等)
- outputs/.../character.json: heroine_outfit + male_companion + appearance_tags
- prepare_prompt.py:
  - character.json 駆動 (load_character_json / build_char_block_from_json)
  - Clothing State ブロック機械除去 (_CLOTHING_STATE_BLOCK_RE, IGNORECASE+DOTALL)
  - 本文中引用符ペア除去 (_QUOTED_INLINE_RE)
  - 自然言語帰属文 (appearance_sentence_en / attribution_sentence_en)
  - AnimaYume最適化 quality prefix + 27タグ ネガ
- grok_prompt_builder.py: キャラタグ生成禁止 + 衣装ロック + Clothing state省略禁止
  + 構図ガイダンス + ライティング必須 + エロ描写期待リスト
- compare_models_v2.py: 25 variants (V01-V25) + --seeds 複数seed対応 + --output-subdir
- hermes_skill/daihon-comfyui-anima/SKILL.md: Hermes Agent スキル完成

検証: comparison_v9 (V08 × scene 1-5 × seeds 42/7/123 = 15枚) で
キャラ一貫性 + 衣装統一 + 男性外見統一 + テキスト混入なし を確認

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```
