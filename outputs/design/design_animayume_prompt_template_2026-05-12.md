# AnimaYume プロンプト最適化テンプレ設計
# design_animayume_prompt_template_2026-05-12.md
# 作成: 2026-05-12 | Task #3

---

## 1. 現状分析: 問題点の抽出

### 1-1. 現行 prepare_prompt.py の Quality Prefix (current_verbose)

```
score_9, score_8_up, score_7_up, masterpiece, best quality, highres, year 2025, newest, sensitive,
anime style, anime illustration, 2d anime art, cel shading, japanese anime aesthetic, soft lighting,
```

**問題点:**
- `score_7_up` は Anima 公式推奨では不要(score_9/score_8_up で十分)。余剰トークンがキャラクター記述を希釈する
- `sensitive` は AnimaYume では `safe` が推奨(compare_models_v2.py の TAG_PROFILES "min" を参照)
- `anime style, anime illustration, 2d anime art, cel shading, japanese anime aesthetic, soft lighting` は 非 Danbooru タグであり Qwen3 TE が literal string として解釈するとノイズになる。AnimaYume が既に anime tuned UNet である以上、冗長
- `very aesthetic` が current_verbose には入っているが、現行 prepare_prompt.py の `_ANIMA_QUALITY_PREFIX` には含まれていない(compare_models_v2.py の current_verbose には含まれる) → 既存プロンプト JSON と compare_models_v2 の実行結果が乖離している

### 1-2. キャラクタータグの問題

**Scenes 1-2:** Grok 出力は `nakano_ichika, go-toubun_no_hanayome,` のみ。Danbooru タグとしての視覚特徴タグが一切ない。

**Scenes 3-5:** Grok 出力に `short_hair, orange_hair, blue_eyes` 等が含まれているが **Scenes 1-2 には無い** → シーン間でキャラクター再現性が安定しない。

**正規キャラクター特徴と Grok 出力の差分:**

| 特徴 | 正規 (Danbooru/原作) | Grok scene_001 | Grok scene_003+ |
|------|---------------------|----------------|-----------------|
| 髪色 | 茶髪ロング (light brown long hair) | 記述なし (タグなし) | `orange_hair` — 誤り (一花は茶髪、五つ子の中で最も明るめ茶色だが orange ではない) |
| 髪型 | long hair / side_ponytail 等 | 記述なし | `short_hair` — 誤り (原作は long hair) |
| 目色 | 青/灰青 (blue_eyes) | `blue_eyes` と記述 (文中のみ) | `blue_eyes` タグあり — OK |
| リボン | 赤いリボン (hair_ribbon, red_ribbon) | 記述なし | 記述なし |
| 服装 | 制服 (school_uniform) 場面による | オフショルダーセーター (場面設定通り) | scene_004: `school_blouse` — 場面適合 |

**重大問題:** Grok は `orange_hair` と `short_hair` という誤ったタグを生成している。AnimaYume は Danbooru タグを忠実に解釈するため、これが直接「キャラクター特徴破綻」の原因になる。

### 1-3. 自然言語本文とタグ形式の混在問題

現行の positive prompt は以下の3層混在:
1. Quality prefix (Danbooru タグ形式)
2. キャラ/シリーズタグ (`nakano_ichika, go-toubun_no_hanayome`)
3. 自然言語記述 (`Gaze completely locked onto the swirling spiral...`)

AnimaYume の Qwen3 TE (CLIPText encoder) は自然言語と Danbooru タグの両方を解釈できるが、**長文自然言語記述が後半に続く場合、先頭のタグに比べて後半の重みが減衰する**。視覚的に重要なキャラクター特徴タグを先頭に集中させることが必須。

### 1-4. スマホ画面・構図の明示不足 (scene_001 の具体例)

scene_001 では「スマホの渦巻きが視線誘導の中心」と書かれているが Danbooru タグとして:
- `holding_phone` / `holding_smartphone` なし
- `spiral` / `hypnotic_spiral` なし
- `looking_at_object` なし
- カメラに向いたスマホ画面を示すタグがない

→ AnimaYume がスマホを背面で描いたり、逆向きで生成する可能性が高い。

### 1-5. Negative Prompt の問題

現行 negative は `bad anatomy, bad hands, deformed` 等の SD1.5 時代の記述を含む。AnimaYume 公式推奨 negative は最小構成:
```
worst quality, low quality, score_1, score_2, score_3, artist name, text, watermark, signature
```
`bad anatomy` 等は Anima のスコア蒸留モデルでは過剰干渉し、むしろ手や体のぎこちなさを誘発することがある。

---

## 2. 中野一花 正規キャラクタータグセット

原作「五等分の花嫁」Danbooru データベース準拠:

```
nakano_ichika, go-toubun_no_hanayome,
1girl, solo,
long_hair, light_brown_hair, hair_ribbon, red_ribbon, blue_eyes,
```

**重み付け推奨:**
```
(nakano_ichika:1.2), go-toubun_no_hanayome,
1girl, solo,
long_hair, light_brown_hair, hair_ribbon, red_ribbon, blue_eyes,
```

**補足:**
- `long_hair` を必ず入れる (Grok が `short_hair` と誤生成するため上書き必須)
- `light_brown_hair` で茶髪を明示 (Grok が `orange_hair` と誤生成するため上書き必須)
- `hair_ribbon, red_ribbon` で赤リボンを固定
- `(nakano_ichika:1.2)` の重み付けで LoRA / モデル内のキャラクター情報を強化

---

## 3. 改善版プロンプトテンプレート設計

### 3-1. Quality Prefix (AnimaYume 最適化版)

```
masterpiece, best quality, very aesthetic, score_9, score_8_up, year 2025, newest, safe, highres,
```

**変更点と根拠:**
- `score_7_up` 削除: Anima 公式は score_9/score_8_up で十分
- `sensitive` → `safe`: AnimaYume 公式推奨 (compare_models_v2.py TAG_PROFILES "min" 参照)
- `very aesthetic` 追加: compare_models_v2 "min"/"aesthetic" 両プロファイルに存在、品質向上効果あり
- `anime style, anime illustration, 2d anime art, cel shading, japanese anime aesthetic, soft lighting` 削除: AnimaYume が anime-tuned のため冗長、Qwen3 TE へのノイズを減らす
- タグ順序: `masterpiece` を先頭に (Qwen3 TE の重み減衰対策で最重要タグを前方に)

### 3-2. キャラクタータグ (固定ブロック)

```
(nakano_ichika:1.2), go-toubun_no_hanayome, 1girl, solo,
long_hair, light_brown_hair, hair_ribbon, red_ribbon, blue_eyes,
```

**MUST-HAVE — これを prepare_prompt.py で Grok 出力の前に強制挿入する。Grok 出力中のキャラタグ行はそのまま残してよいが、このブロックが先頭にあることで Qwen3 TE の前方重み付けにより正しい特徴が優先される。**

### 3-3. カメラ視点・スマホ画面の明示 (scene 別ヒントセット)

場面にスマホ・道具系デバイスが登場する場合 (scene_001 など):
```
holding_smartphone, smartphone, looking_at_phone, hypnotic_spiral,
screen_visible, facing_viewer,
```

場面にベッド + 催眠トランス状態がある場合 (scene_002, 004, 005):
```
on_bed, lying_on_back, vacant_eyes, half-closed_eyes, blush, sweat,
```

### 3-4. 5シーン共通の構図ヒントセット

5シーン全体を通じて一花が「催眠・トランス状態」で進行するため、以下を全シーンで維持:

```
(nakano_ichika:1.2), go-toubun_no_hanayome, 1girl, solo,
long_hair, light_brown_hair, hair_ribbon, red_ribbon, blue_eyes,
blush, vacant_eyes, dazed, trance, hypnosis,
faceless_male, 1boy,
```

**構図タグ (シーン内の Composition 記述に連動):**
- scene_001 (縦構図/close-up/スマホ): `upper_body, portrait, close-up, holding_smartphone, hypnotic_spiral`
- scene_002 (low angle/ベッド): `upper_body, low_angle, on_bed, sitting`
- scene_003 (twilight/手が胸に): `upper_body, hand_on_chest, standing, indoors`
- scene_004 (俯瞰/アンボタン): `cowboy_shot, from_above, unbuttoned_shirt, exposed_collarbone, on_bed`
- scene_005 (medium/lying): `medium_shot, lying_on_back, open_clothes, bra, on_bed`

### 3-5. Negative Prompt 最小版 (AnimaYume 公式準拠)

```
worst quality, low quality, score_1, score_2, score_3, artist name, text, watermark, signature
```

**現行から削除するもの:** `speech bubble, dialogue, subtitle, english text, letters, caption, words, logo, font, 3d, realistic, photorealistic, photo, semi-realistic, american comic, western, marvel style, dc style, comic book, bad anatomy, bad hands, deformed, blurry, jpeg artifacts, extra digit, missing fingers`

**削除の根拠:** AnimaYume は Anima ベースの anime-tuned UNet であり、スコア蒸留で品質が制御されている。SD1.5 時代の anatomy ネガは逆効果になりやすい。テキスト混入は quality prefix の `safe` と `score_9` + ネガ最小版で十分に抑制できる。

---

## 4. prepare_prompt.py への組込み案

### 4-1. 新定数の追加

```python
# AnimaYume 最適化 quality prefix (compare_models_v2 "min" + "very aesthetic" ベース)
_ANIMAYUME_QUALITY_PREFIX = (
    "masterpiece, best quality, very aesthetic, score_9, score_8_up, "
    "year 2025, newest, safe, highres,\n"
)

# キャラクター固定タグブロック (Grok の誤生成タグを前方重み付けで上書き)
# キャラ名は関数引数で渡す設計にする
_CHAR_TAG_TEMPLATES: dict[str, str] = {
    "nakano_ichika": (
        "(nakano_ichika:1.2), go-toubun_no_hanayome, 1girl, solo,\n"
        "long_hair, light_brown_hair, hair_ribbon, red_ribbon, blue_eyes,\n"
    ),
    # 他キャラはここに追加
}

# AnimaYume 公式推奨 negative (最小版)
_ANIMAYUME_NEGATIVE_MIN = (
    "worst quality, low quality, score_1, score_2, score_3, artist name, "
    "text, watermark, signature"
)
```

### 4-2. 関数シグネチャ変更案

```python
def build_positive_prompt(
    english_body: str,
    char_key: str | None = None,       # "nakano_ichika" 等
    quality_preset: str = "current",   # "current" | "animayume_min"
) -> str:
    """
    quality_preset="animayume_min" を指定すると AnimaYume 最適化 prefix を使用。
    char_key を指定すると Grok 本体の前にキャラクター固定タグブロックを挿入。
    """
    if quality_preset == "animayume_min":
        prefix = _ANIMAYUME_QUALITY_PREFIX
    else:
        prefix = _ANIMA_QUALITY_PREFIX  # 既存 (後方互換)

    char_block = ""
    if char_key and char_key in _CHAR_TAG_TEMPLATES:
        char_block = _CHAR_TAG_TEMPLATES[char_key]

    return prefix + char_block + english_body
```

### 4-3. Negative Prompt の切り替え

```python
def build_negative_prompt(preset: str = "current") -> str:
    if preset == "animayume_min":
        return _ANIMAYUME_NEGATIVE_MIN
    return _DEFAULT_NEGATIVE  # 既存 (後方互換)
```

### 4-4. CLI 引数追加 (cmd_extract)

```python
p_ex.add_argument("--char-key", default=None,
    help='キャラクター固定タグキー (例: nakano_ichika)')
p_ex.add_argument("--quality-preset", default="current",
    choices=["current", "animayume_min"],
    help='quality prefix プリセット')
p_ex.add_argument("--neg-preset", default="current",
    choices=["current", "animayume_min"],
    help='negative prompt プリセット')
```

### 4-5. process_scene 関数シグネチャ変更

```python
def process_scene(
    response_path: Path, output_dir: Path, scene_id: int,
    char_key: str | None = None,
    quality_preset: str = "current",
    neg_preset: str = "current",
) -> dict:
    ...
    positive = build_positive_prompt(english, char_key, quality_preset)
    negative_str = build_negative_prompt(neg_preset)
    ...
```

**後方互換:** デフォルト引数がすべて既存動作を維持するため、引数なしの既存呼び出しはそのまま動く。

### 4-6. 実行例 (AnimaYume 最適化モードで一花 5 シーン抽出)

```bash
python prepare_prompt.py extract \
  outputs/hermes_pipeline/中野一花（五等分の花嫁）_export_20260506014006 \
  --char-key nakano_ichika \
  --quality-preset animayume_min \
  --neg-preset animayume_min
```

---

## 5. Grok へのプロンプト改善指示 (上流対策)

現状は prepare_prompt.py で後処理するが、Grok 出力の時点でタグ精度を上げることも有効。

**追加指示案 (Grok system prompt / hermes_pipeline 側):**

```
IMPORTANT CHARACTER TAG RULES:
- nakano_ichika has: long_hair, light_brown_hair (NOT orange_hair), blue_eyes, hair_ribbon, red_ribbon
- Always output Danbooru-compatible character tags matching the character's canonical appearance
- Do NOT use short_hair for characters with long hair
- Do NOT substitute orange_hair for light_brown_hair
```

---

## 6. 改善版 scene_001 positive プロンプト (Before/After)

### Before (現行)
```
score_9, score_8_up, score_7_up, masterpiece, best quality, highres, year 2025, newest, sensitive,
anime style, anime illustration, 2d anime art, cel shading, japanese anime aesthetic, soft lighting,
nakano_ichika, go-toubun_no_hanayome,
Nakano Ichika
Position & posture: ...
```

### After (animayume_min + char_key=nakano_ichika)
```
masterpiece, best quality, very aesthetic, score_9, score_8_up, year 2025, newest, safe, highres,
(nakano_ichika:1.2), go-toubun_no_hanayome, 1girl, solo,
long_hair, light_brown_hair, hair_ribbon, red_ribbon, blue_eyes,
blush, vacant_eyes, dazed, trance, hypnosis, holding_smartphone, hypnotic_spiral,
nakano_ichika, go-toubun_no_hanayome,
Nakano Ichika
Position & posture: Sitting shallowly on a couch...
[以降 Grok 本体そのまま]
```

---

## 7. 要点サマリー

1. **キャラタグ誤生成が最大問題**: Grok は `orange_hair` + `short_hair` を誤出力。正しくは `light_brown_hair` + `long_hair`。prepare_prompt.py で固定ブロックを前方挿入することで Qwen3 TE の前方重み付けにより上書き可能。

2. **Quality Prefix は "animayume_min" へ切替推奨**: `score_7_up` 削除・`sensitive`→`safe`・anime系非Danbooruタグ削除で Qwen3 TE へのノイズを削減。`very aesthetic` 追加で品質維持。

3. **Negative は公式最小版に絞る**: SD1.5 時代の `bad anatomy, bad hands` 等は AnimaYume スコア蒸留モデルで逆効果。`worst quality, low quality, score_1, score_2, score_3, artist name, text, watermark, signature` の9タグで十分。
