# Scene Style Diff Research — scene 1-5 絵柄変化原因分析
作成: 2026-05-12 | 対象: 中野一花（五等分の花嫁）_export_20260506014006

---

## 1. 5シーン プロンプト統計表

| 項目 | Scene 1 | Scene 2 | Scene 3 | Scene 4 | Scene 5 |
|------|---------|---------|---------|---------|---------|
| positive 文字数（prefix除く本文） | ~1,300 | ~1,200 | ~400 | ~800 | ~1,000 |
| 構図キーワード | Tight vertical close-up | Close-up, slightly low angle | (明示なし) | High-angle shot | Slight high-angle medium shot |
| ライティング | Dim room lighting | Soft evening light | Soft orange sunset glow | (明示なし) | (明示なし) |
| 背景記述量 | 少（dim room のみ） | 少（dim bedroom） | 多（sunset glow + curtains） | 少（bed のみ） | 少（bed + sheets） |
| 構造形式 | 構造化セクション（Position/Hands/Gaze/Clothing） | 構造化セクション | 散文（narrative prose） | 構造化セクション | 構造化セクション |
| キャラ固有タグ行の有無 | なし（char_blockのみ） | なし | **あり（scene_003_response.txtから直接追記）** | **あり（orange_hair, vacant_eyes等）** | **あり（drooling, open_blouse等）** |
| quality_preset | animayume_min | animayume_min | animayume_min | animayume_min | animayume_min |
| neg_preset | animayume_min | animayume_min | animayume_min | animayume_min | animayume_min |
| negative プロンプト差分 | 同一 | 同一 | 同一 | 同一 | 同一 |

### char_block（全シーン共通・同一）

```
masterpiece, best quality, very aesthetic, score_9, score_8_up, year 2025, newest, safe, highres,
(nakano_ichika:1.2), go-toubun_no_hanayome,
1girl, short_hair, pink_hair, bangs, hair_between_eyes, asymmetrical_sidelocks, blue_eyes, large_breasts, 1boy,
faceless_male,
```

**結論：char_block は全5シーン完全同一。品質 prefix も同一。**

---

## 2. scene_001 vs scene_004 の具体的フレーズ差分

### 構造形式
- **scene_001**: 長い構造化セクション。各セクションが数文で詳述。
- **scene_004**: 構造化セクションは同様だが、**scene_004 の positive 冒頭に Grok response の英語版 inline タグ行が混入している。**

scene_004 の positive は `nakano_ichika, go-toubun_no_hanayome, 1girl, short_hair, orange_hair, ...` というタグ行が **anima_prompts/scene_004_prompt.json には含まれていない**（grok_responses 側にはある）。ただし scene_003 の anima_prompt.json positive には `Scene 3 — Unconscious.\nIn a dimly lit bedroom...` という **散文スタイル** で始まっており、構造化セクションが存在しない。

### 絵柄に影響する具体的差分

| 差分ポイント | scene_001 の記述 | scene_004 の記述 |
|------------|-----------------|-----------------|
| **構図** | `Tight vertical close-up composition` | `High-angle shot from slightly above` |
| **アングル方向** | 水平〜やや上から見下ろし | 明確な俯瞰（high-angle） |
| **ショットサイズ** | `close-up`（顔・上半身アップ） | 俯瞰で全身〜上半身 |
| **ライティング** | `Dim room lighting strongly highlights` | 記述なし（ambient lighting に委ねる） |
| **focal point** | `smartphone spiral acting as focal point` | `exposed cleavage, dazed face, man's hand` |
| **被写体の状態** | 服着用・hypnosis初期 | ブラウス3ボタン開け・underwear露出 |
| **服装状態** | `White off-shoulder sweater` | `White school blouse unbuttoned down to third button, bra strap visible` |
| **直後感の描写量** | 長文（trembling、sweat、eyelids frozen） | 短文（jolts、dizzy "fading…"） |

### 特に絵柄を左右すると考えられるフレーズ

- scene_001: **`Tight vertical close-up`** → 顔中心・ポートレート寄りの構図指示
- scene_004: **`High-angle shot from slightly above`** → 俯瞰・全体図寄りの構図指示
- scene_001: **`Dim room lighting strongly highlights her sweat and entranced expression`** → 明確な照明指示でモデルが陰影を強く表現
- scene_004: **ライティング指示なし** → モデルが ambient / default lighting を選択、絵柄が「明るめ・フラット」になりやすい

---

## 3. scene_001 vs scene_005 の具体的フレーズ差分

| 差分ポイント | scene_001 の記述 | scene_005 の記述 |
|------------|-----------------|-----------------|
| **構図** | `Tight vertical close-up composition` | `Slight high-angle medium shot` |
| **ショットサイズ** | `close-up`（顔アップ） | `medium shot`（半身〜全身） |
| **アングル** | 正面〜やや上から | `slightly above`（俯瞰） |
| **ライティング** | `Dim room lighting strongly highlights` | 記述なし |
| **focal point** | 顔・スマホの螺旋 | `exposed cleavage, drooling dazed face, open blouse` |
| **服装状態** | 服ほぼ着用（off-shoulder sweater） | `fully unbuttoned blouse, white lace bra, half-nude` |
| **表情特記** | `hazy, entranced, timidly contemplative` | `drooling, melted, entranced` ＋ **`drooling`タグ相当の記述** |
| **直後感** | trembling fingertips、bead of sweat | bikun震え、bra strap への接触、drool |
| **shiver lines 指示** | なし | **`Add subtle shiver lines`**（作画効果ライン追加指示） |

### scene_005 固有の絵柄影響要因

1. **`Add subtle shiver lines to express the cold air and bodily reaction`**  
   → 震え表現の描画指示がテキストに入っており、モデルが「線画ライン追加」「dynamic effects」スタイルを選択しやすくなる。これは **画風・タッチへの直接的な描画スタイル指示** であり、scene_001〜004には存在しない。

2. **`thin string of drool trailing from the corner`**  
   → drool 描写は口元の描き方を変え、顔の「エロ表現度」とともに **描画の解像度感・細部への注力度** が変わる。

3. **`medium shot`**  
   → close-up より広い画角で全身構図になるため、顔の解像感が落ち、絵柄の「精細感」が相対的に低下しやすい。

---

## 4. 仮説：絵柄変化を起こしている可能性のある原因

### 仮説A（最有力）: 構図指示の非統一 — close-up vs high-angle medium shot

**根拠:**
- scene_001/002: `close-up` / `tight close-up` / `slightly low angle` → 顔中心・アップ
- scene_003: 構図指示なし（散文スタイル）
- scene_004: `High-angle shot` → 俯瞰
- scene_005: `high-angle medium shot` → 俯瞰＋広角

Stable Diffusion / Anima のアーキテクチャでは、**構図・アングル指示は画風全体のトーンに影響する**。close-up 指示があると背景がほぼ消え顔の精細描写に全 attention が集中するが、high-angle medium shot では構図が広がり、全体的なライティング・色調・絵の「雰囲気感」が変わりやすい。

### 仮説B（有力）: ライティング指示の欠如（scene_004/005）

**根拠:**
- scene_001: `Dim room lighting strongly highlights her sweat`（明確）
- scene_002: `soft evening light gently illuminating her face`（明確）
- scene_003: `soft orange sunset glow`（明確）
- scene_004: ライティング指示なし
- scene_005: ライティング指示なし

ライティング指示はカラートーン（暖色/寒色）と陰影の深さに直接影響する。指示がない場合、モデルは「ニュートラル/明るめ/フラット」なライティングを選択しやすく、scene_001〜003より「明るい・ポップな絵」になりやすい。

### 仮説C: scene_003 のプロンプト構造が散文形式に崩壊

**根拠:**
- scene_001/002/004/005: 「Position & posture / Hands / Gaze / Clothing / Composition」の構造化セクション形式
- scene_003: `In a dimly lit bedroom at twilight, Nakano Ichika stands close to the viewer...` という **散文ナラティブ形式**

Anima / SD がポジティブプロンプトをパースする際、構造化セクション形式と散文形式ではトークンの重みの分布が異なる。散文形式では **文脈的な意味は伝わるが、特定属性への attention weight が分散**しやすく、絵柄の「まとまり感」が変わる可能性がある。

### 仮説D（補助）: `shiver lines` 等の描画効果指示（scene_005 固有）

scene_005 に `Add subtle shiver lines` という **作画エフェクト指示** が入っており、これがモデルに「漫画的効果線スタイル」を誘引している可能性がある。エフェクト線の有無は絵柄の「アニメ的 vs リアル的」の印象に影響する。

### 仮説E: `orange_hair` 記述の混入（scene_003 のみ）

char_block では `pink_hair` と指定しているにもかかわらず、scene_003 の positive 本文中（散文部分）に `Her short orange hair` という記述がある。これは color 指示の競合を引き起こし、**hair color のみならず全体の色調設定に影響**する可能性がある（pink vs orange は彩度・暖色系の競合）。

---

## 5. 改善提案

### 提案1: `prepare_prompt.py` — 構図・ライティングの強制 normalize

```python
# positive 本文の末尾に構図/ライティング統一ブロックを append する
COMPOSITION_LOCK = (
    "close-up portrait composition, soft dim lighting, "
    "shallow depth of field, intimate atmosphere"
)

def normalize_composition(positive: str) -> str:
    # [Composition] セクションがない場合にのみ append
    if "[Composition]" not in positive and "Composition:" not in positive:
        positive = positive.rstrip() + f"\n[Composition]\n{COMPOSITION_LOCK}"
    return positive
```

**効果**: scene_004/005 のような構図・ライティング指示抜けを防止。

### 提案2: `grok_prompt_builder.py` — Grok へのシステムプロンプト強化

以下を **必須指示** として Grok の system prompt に追加:

```
[COMPOSITION REQUIREMENTS - MANDATORY]
Every scene's English version MUST include:
1. A [Composition] section at the end with:
   - Shot type: one of (tight close-up / close-up / medium close-up)
   - Angle: one of (eye-level / slightly low angle / slightly high angle)
   - Lighting: explicitly describe (e.g., "dim room lighting", "soft evening light", "warm candlelight")
2. DO NOT use "high-angle shot" — maximum tilt is "slightly above"
3. DO NOT include shiver lines, motion lines, or manga effect directions
4. NEVER include hair color descriptions that conflict with char_block
   (char_block already defines hair color — do not restate it)
```

**効果**:
- 仮説A対策: high-angle を禁止、close-up/medium close-up に限定
- 仮説B対策: lighting 必須化
- 仮説D対策: shiver lines 等の描画効果指示を禁止
- 仮説E対策: hair color 再記述禁止

### 提案3: `prepare_prompt.py` — 散文スタイル検出とフォールバック

```python
def detect_prose_style(positive_body: str) -> bool:
    """構造化セクションではなく散文スタイルで書かれているか検出"""
    has_section_header = any(
        kw in positive_body
        for kw in ["Position & posture:", "Gaze & expression:", "[Composition]", "Hands /"]
    )
    return not has_section_header

def warn_prose_style(scene_id: int, positive_body: str):
    if detect_prose_style(positive_body):
        print(f"[WARN] scene_{scene_id:03d}: prose-style prompt detected — "
              "may reduce attribute specificity. Consider regenerating with structured format.")
```

**効果**: scene_003 のような構造崩壊を検出し、ユーザーに再生成を促す。

### 提案4: `prepare_prompt.py` — char_block color タグとの競合チェック

```python
CHAR_BLOCK_COLORS = {
    "nakano_ichika": {"hair": "pink_hair"},
    # ... 他キャラ
}

def check_color_conflict(char_key: str, positive_body: str) -> list[str]:
    conflicts = []
    colors = CHAR_BLOCK_COLORS.get(char_key, {})
    for attr, expected_tag in colors.items():
        expected_color = expected_tag.replace("_hair", "").replace("_eyes", "")
        # 異なる色の言及を検出（例: "orange hair" when expected "pink"）
        # ...実装略
    return conflicts
```

---

## まとめ

| 仮説 | 優先度 | 対策 |
|------|--------|------|
| A: 構図指示非統一（close-up vs high-angle） | **最高** | grok system prompt で shot type を制限 |
| B: ライティング指示欠如 | **高** | grok system prompt で lighting 必須化 |
| C: 散文スタイル崩壊（scene_003） | 中 | prose 検出 + 警告ログ |
| D: shiver lines 等描画効果指示 | 中 | grok system prompt で禁止 |
| E: hair color 競合（orange_hair in scene_003） | 低〜中 | char_block color conflict チェック |

**最も即効性が高い対策**: Grok system prompt に `[COMPOSITION REQUIREMENTS]` ブロックを追加（コスト$0）。
