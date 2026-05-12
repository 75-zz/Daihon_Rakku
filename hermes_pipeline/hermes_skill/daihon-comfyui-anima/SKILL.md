---
name: daihon-comfyui-anima
description: |
  Daihon Rakku → Grok web 経由で書き換えられた scene_NNN_response.txt の
  英語版を ComfyUI/AnimaYume v0.4 に投入し、キャラ一貫性を担保しつつ
  CG 集の各シーン画像を生成・保存するバッチスキル。
  character.json でキャラ識別+衣装+男性外見を固定し、Grok 本体の
  Clothing State / 引用符ペアを機械除去することで LLM ハルシネーションを遮断。
version: 0.2.0
metadata:
  hermes:
    tags: [creative, comfyui, animayume, daihon-rakku, batch, image-generation]
    requires_toolsets: [terminal]
    category: creative
---

# daihon-comfyui-anima Skill

## 前提条件

1. **ComfyUI 稼働**: WSL 内 (Python 3.14 venv) で `--reserve-vram 2.5` 付き起動
   - `comfy launch --background` は壊れている（Python 3.14 asyncio 非互換）
   - 直接起動: `~/comfy/.venv/bin/python ~/comfy/main.py --listen 127.0.0.1 --port 8188 --reserve-vram 2.5`
   - 確認: `curl http://localhost:8188/system_stats`
2. **モデル配置済み**:
   - UNet: `~/comfy/models/diffusion_models/animayume_v04.safetensors`
   - LoRA: `~/comfy/models/loras/anima-preview-3-masterpieces-v5.safetensors`
   - CLIP: `qwen_3_06b_base.safetensors` / VAE: `qwen_image_vae.safetensors`
3. **work_dir 構造**:
   ```
   outputs/hermes_pipeline/<work>/
   ├── grok_responses/scene_NNN_response.txt  (Phase 2 で生成済)
   └── character.json                          (Daihon Rakku 提供データ、手動配置)
   ```

## character.json スキーマ (v9 / 2026-05-12)

```json
{
  "character_name": "中野一花",
  "char_id": "char_a1b2c3d1",
  "danbooru_tags": ["nakano_ichika", "go-toubun_no_hanayome", "1girl",
                    "short_hair", "pink_hair", "bangs", "hair_between_eyes",
                    "asymmetrical_sidelocks", "blue_eyes", "large_breasts"],
  "danbooru_tags_negative": ["long_hair", "orange_hair", "brown_hair", "blonde_hair"],
  "appearance_sentence_en": "The girl is a young woman with short pink hair, ...",
  "heroine_outfit": {
    "outfit_tags": ["white_shirt", "green_skirt", "pleated_skirt", "black_pantyhose"],
    "negative_outfit_tags": ["kimono", "school_uniform", "off_shoulder", "..."],
    "attribution_sentence_en": "The girl is wearing a white blouse, ..."
  },
  "male_companion": {
    "appearance_tags": ["muscular_male", "young_man", "short_hair", "black_hair",
                        "dark-skinned_male", "tanned", "toned_body"],
    "outfit_tags": ["black_shirt", "t-shirt", "short_sleeves", "black_pants", "muscular"],
    "negative_outfit_tags": ["white_shirt", "suit", "jacket", "..."],
    "attribution_sentence_en": "Beside her is a faceless muscular tanned young man ..."
  },
  "anima_meta": {
    "weight": 1.2,
    "character_tag": "nakano_ichika",
    "series_tag": "go-toubun_no_hanayome",
    "with_faceless_male": true
  }
}
```

## Procedure

### Step 1: 環境確認（最初に 1 回のみ）
1. `curl -s http://localhost:8188/system_stats` で ComfyUI 起動確認
2. 起動していなければ user に依頼:
   `wsl ~/comfy/.venv/bin/python ~/comfy/main.py --listen 127.0.0.1 --port 8188 --reserve-vram 2.5`
3. work_dir/character.json 存在確認
4. work_dir/grok_responses/scene_*_response.txt が揃っているか確認

### Step 2: anima_prompts 生成
```bash
python3 scripts/prepare_prompt.py extract <work_dir> \
  --quality-preset animayume_min \
  --neg-preset animayume_min
```
内部処理:
- Grok 英文抽出
- `_QUOTED_INLINE_RE` で本文中の引用符ペア除去
- `_DIALOGUE_HEADING_RE` で Dialogue/Sound effects セクション切り捨て
- `_CLOTHING_STATE_BLOCK_RE` で "Clothing State:" ブロック機械除去
- character.json から `build_char_block_from_json` で:
  - キャラ識別タグ + 視覚特徴タグ
  - ヒロイン衣装タグ + 自然言語帰属文
  - 男性 appearance タグ + 男性 outfit タグ + 自然言語帰属文
- AnimaYume 最適化 quality prefix 前置
- ネガティブ拼装 (27 タグ + キャラ別 negative_outfit_tags)

### Step 3: Step 1 で 1 回だけユーザー確認
ユーザーに「N シーン × M variant × K seed 処理、推定 (N*M*K*30) 秒、続行?」と提示。
yes を得たら以降は逐次確認禁止（自動進行）。

### Step 4: 画像生成（V08 標準構成 + 複数 seed）
```bash
python3 scripts/compare_models_v2.py <work_dir> \
  --scenes 1-5 --variants V08 \
  --seeds 42,7,123 \
  --timeout 500 \
  --output-subdir comparison_v9
```
- V08 = `animayume_v04 + masterpieces 0.5 + AESTHETIC tag + er_sde + 30steps + CFG4.0 + 1024x1024`
- 各シーン 3 seed で生成、ファイル名末尾 `_seedNNN`

### Step 5: 完了後 status 出力
```json
{
  "summary": {
    "scene_count": 5,
    "variant_count": 1,
    "total_jobs": 15,
    "ok": 15,
    "skipped": 0,
    "error": 0,
    "output_dir": ".../comparison_v9"
  }
}
```

## Pitfalls (実体験ベース)

### Pitfall 1: VRAM 飽和でハング
- 16GB GPU で `--reserve-vram` 無しだと scene_003 以降ハング
- **必ず `--reserve-vram 2.5` 付きで起動**

### Pitfall 2: `dpmpp_2m_sde_gpu` 使用禁止
- Anima 公式が「プロンプトで暴走」と警告
- V14 が 402KB の破綻画像になった実証あり
- **`er_sde` または `euler_ancestral` のみ使用**

### Pitfall 3: comfy-cli `--background` は壊れている
- Python 3.14 で `asyncio.get_event_loop()` 仕様変更
- **`main.py` 直接起動を使う**

### Pitfall 4: LLM にキャラタグを生成させない
- prompt-engineer サブエージェントですら "long_hair, light_brown_hair" のような原作と矛盾するタグを返した
- **character.json (preset 由来) を必ず最終ソースにする**
- 新キャラ追加時は `danbooru.donmai.us/wiki_pages/<char>` を WebFetch で検証

### Pitfall 5: 並列タグだけでは帰属が混線する
- `1girl, white_shirt, 1boy, black_shirt` だと muscular や T シャツが女性に転移
- **キャラ別「タグ → 自然言語」ペア配置必須**
- `attribution_sentence_en` で明示

### Pitfall 6: Grok 本体のセリフ引用は画面内テキスト化する
- `"fading…"` 等の引用符ペアが scene_004 で言葉として描画された
- **`_QUOTED_INLINE_RE` で除去必須**

### Pitfall 7: 単一 seed では衣装ブレを抑えきれない
- character.json で固定しても seed によっては T シャツ化等が残る
- **`--seeds 42,7,123` で複数 seed 生成し選別**

## Verification

生成後 user 視点で:
1. キャラ識別: ピンクショート/青目/非対称サイドロック が安定しているか
2. 衣装: 一花 = 白ブラウス+緑スカート / 男性 = 黒T シャツ+黒パンツ で全シーン統一か
3. 男性外見: 短髪+黒髪+褐色肌+筋肉質 で全シーン統一か
4. 画面内テキスト混入なし
5. 構図変化が極端でないか

問題があれば character.json または grok_prompt_builder.py のルールを調整して再生成。

## 推定コスト

| | 値 |
|---|---|
| Hermes LLM 判断 | 5シーン×1variant×3seed で $0.05 程度 |
| ComfyUI 実行 (ローカル GPU) | $0 (電力のみ) |
| 1 シーン生成時間 | warm 18-25秒 / cold (model load) 200-300秒 |
| 5シーン×3seed 合計 | 約 6-8 分 |

## バージョン履歴

- **v0.1.0** (2026-05-11): 初期 Phase 3 設計 (4 variants A/B/C/D)
- **v0.2.0** (2026-05-12): v9 確立 — character.json 駆動 / 自然言語帰属 / Clothing State 除去 / 引用符ペア除去 / 多 seed
