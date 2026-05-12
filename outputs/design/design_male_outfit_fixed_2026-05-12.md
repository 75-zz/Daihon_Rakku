# 男性服装固定化設計書 — 黒シャツ統一

**作成日**: 2026-05-12 (v2: 2026-05-12 状態変化許可ポリシー追記)  
**対象ブランチ**: feature/hermes-anima-pipeline  
**対応する問題**: scene_005 で male outfit が未指定となり白シャツ混入リスクが生じた件

---

## 0. 設計の基本方針 (v2 追加)

**「アイテム種類は固定、状態変化は Grok に委ねる」**

| 区分 | 制御主体 | 例 |
|------|---------|-----|
| ベース衣装名（固定） | character.json + prepare_prompt.py | `black_shirt`, `black_pants` |
| 衣装の状態変化（許可） | Grok の自然言語 / タグ描写 | `open_shirt`, `shirtless`, `pants_pulled_down` |

竿役の脱衣プログレッション（袖まくり → シャツ開き → ズボン下げ）はCG集の見せ場であり、Grok が状態変化を描写することは積極的に許可する。  
禁止するのは **アイテム種類の変更**（黒シャツ → 白シャツ / スーツ等）のみ。

---

## 1. 現状調査: scene_001〜005 の Faceless Male 服装状態

| Scene | Faceless Male "Clothing state" | 備考 |
|-------|-------------------------------|------|
| 001 | "Black shirt with sleeves rolled up exposing muscular arms, simple black pants." | 明示 ✅ |
| 002 | "Black shirt with sleeves rolled up, revealing muscular veiny arms." | 明示 ✅ |
| 003 | 自然言語のみ "gripping the collar of his shirt"（色未指定） | 色なし ⚠️ |
| 004 | 男性セクションに Clothing state 記述なし | 欠落 ⚠️ |
| 005 | 男性セクションに Clothing state 記述なし | 欠落 ⚠️ |

**補足 (scene_005 "white shirt" 報告について)**:  
scene_005_response.txt の "white blouse" は Ichika（女性側）の服装である。  
Grok は男性の clothing state を一切出力しなかった。  
anima_prompts/scene_005_prompt.json の positive にも male outfit タグは存在しない。  
→ 根本原因は「Grok が場面が進むにつれて男性服装を省略した」こと。  
→ Anima が male の服装を補完生成する際、Ichika の "white blouse" 文脈に引きずられて  
　 白シャツを描画した可能性が高い。

---

## 2. Danbooru タグ表記の正確性確認

| タグ候補 | Danbooru 存在 | post 数 | 判定 |
|---------|-------------|---------|------|
| `black_shirt` | ✅ 存在 | 336,909 | **推奨** |
| `black_t-shirt` | ❌ 404 Not Found | — | 使用不可 |
| `rolled_up_sleeves` | ✅ 存在 (要確認) | 多数 | 推奨 |
| `muscular` | ✅ 存在 | 多数 | 推奨 |
| `veiny` / `veiny_arms` | ✅ 存在 | 多数 | 推奨 |

**結論**: `black_shirt` が唯一有効な Danbooru タグ。  
`black_t-shirt` は Danbooru に存在しないため使用禁止。

---

## 3. 黒シャツ vs 黒Tシャツの意味的違いと選択

| 項目 | black_shirt + rolled_up_sleeves | black_t-shirt（非存在）|
|------|-------------------------------|----------------------|
| 形状 | 長袖を腕まくり / Yシャツ系含む広義 | 短袖Tシャツ（存在しない）|
| Grok 出力との一致 | "Black shirt with sleeves rolled up" → 完全一致 | — |
| Danbooru 有効性 | ✅ 336,909 posts | ❌ 非存在 |
| 意味の明確さ | `black_shirt, rolled_up_sleeves` で腕まくり状態を明示できる | — |

**推奨**: `black_shirt, rolled_up_sleeves` の組み合わせ。  
Grok の自然言語出力（scene_001/002）と完全一致し、タグとしても意味が明確。  
ユーザーが「黒Tシャツ」と言った場合も、Danbooru 語彙では `black_shirt` が最近似。

---

## 3-B. 許可される状態変化タグ一覧 (v2 追加)

Grok が自然言語またはタグで描写してよい男性衣装の状態変化。  
これらは **character.json の `outfit_tags` には含めない**（初期状態のベース衣装のみ固定）。

| カテゴリ | 許可タグ / 自然言語例 |
|---------|-------------------|
| 袖まくり（既存） | `rolled_up_sleeves`, "sleeves rolled up" |
| シャツ開け | `open_shirt`, `unbuttoned_shirt`, "shirt hanging open" |
| 上半身脱ぎ | `half_undressed`, `shirtless`, `bare_chest`, `exposed_chest`, `exposed_abs` |
| 露出強調 | `veiny_arms`, `muscular`, "shirt hanging from waist" |
| ベルト・ズボン | `unbuckled_belt`, `pants_pull`, `pants_pulled_down`, `pants_around_thighs`, `zipper_pull` |

**ルール**: 上記状態タグは Grok の判断でシーン進行に応じて追加・変更してよい。  
ただし状態変化後も「服の色・種類」の記述が必要なシーンでは `black shirt` / `black pants` の  
アイテム名を維持すること（例: "open black shirt" / "black pants pulled down"）。

---

## 3-C. Grok に描いてほしい男性エロ表現リスト (v2 追加)

Grok は本プロジェクトで最もエロ描写力が強い LLM であり、その描写力を**最大限活かす**ことが設計の主眼。  
以下は「抑制リスト」ではなく「期待リスト」。シーン進行に応じて積極的に使用させる。

### 衣装脱衣プログレッション
| 段階 | 自然言語 / タグ例 |
|------|-----------------|
| 初期 | "black shirt, black pants, muscular arms" |
| 袖まくり | "sleeves rolled up", `rolled_up_sleeves`, "forearms fully exposed, veins prominent" |
| シャツ開け | "shirt hanging open", `open_shirt`, `unbuttoned_shirt`, "chest fully visible" |
| シャツ脱ぎ | "shirt removed, hanging from his waist", `shirtless`, `bare_chest`, `exposed_abs` |
| ベルト外し | "belt unbuckled and hanging", `unbuckled_belt`, "waistband loosened" |
| ズボン下げ | "pants pushed down to thighs", `pants_pulled_down`, `pants_around_thighs`, `zipper_pull` |
| 全裸 | "completely nude", `nude`, `male_nudity` |

### 勃起・性器描写 (ギンギンディレクティブ準拠)
| 表現種別 | タグ / 自然言語例 |
|---------|----------------|
| 勃起状態 | `erection`, `erect_penis`, "visibly erect through fabric", "bulge straining against pants" |
| 露出 | `exposed_genitals`, `penis`, `large_penis`, "cock exposed and fully hard" |
| 先端・亀頭 | `glans`, "glans exposed", "foreskin pulled back" |
| 我慢汁 | `precum`, "tip glistening with precum", "bead of fluid at the tip" |
| サイズ感 | `large_penis`, "imposingly large", "thick and veiny shaft" |
| 挿入前後 | `penis_on_face`, `against_wall`, "tip pressed against her entrance" |

### 体液・分泌物
| 表現 | タグ / 自然言語例 |
|-----|----------------|
| 我慢汁 | `precum`, "clear fluid dripping from tip" |
| 射精直前 | "on the edge of release", "muscles tensing, breathing ragged" |
| 射精 | `ejaculation`, `cum`, `internal_cumshot`, `cumshot` |
| 射精後 | "spent and still twitching", "thick white fluid pooling" |

### 身体・筋肉描写
- 「muscular arms with veins standing out」「defined abs glistening with sweat」
- 「powerful grip」「dominant stance」「weight pressing down on her」
- 「heavy breathing」「low groan」（声・息づかいの視覚的示唆）

### 設計スタンス確認
- ❌ 禁止: Grok のエロ描写を抑制・統制する方向の追加ルール
- ✅ 推奨: 上記リストを grok_prompt_builder.py のルールに「積極的に描写してよい」として明示
- 男性服装の制約は「アイテム種類変更禁止」の1点のみ。それ以外は Grok の判断に委ねる

---

## 4. character.json 拡張案

```json
{
  "character_name": "中野一花",
  "work_title": "五等分の花嫁",
  "char_id": "char_a1b2c3d1",
  "danbooru_tags": [
    "nakano_ichika",
    "go-toubun_no_hanayome",
    "1girl",
    "short_hair",
    "pink_hair",
    "bangs",
    "hair_between_eyes",
    "asymmetrical_sidelocks",
    "blue_eyes",
    "large_breasts"
  ],
  "danbooru_tags_negative": [
    "long_hair",
    "orange_hair",
    "brown_hair",
    "blonde_hair"
  ],
  "male_companion": {
    "outfit_tags": [
      "black_shirt",
      "black_pants",
      "muscular"
    ],
    "negative_outfit_tags": [
      "white_shirt",
      "white_t-shirt",
      "suit",
      "tuxedo",
      "jacket",
      "hoodie",
      "uniform",
      "dress_shirt"
    ]
  },
  "anima_meta": {
    "weight": 1.2,
    "character_tag": "nakano_ichika",
    "series_tag": "go-toubun_no_hanayome",
    "with_faceless_male": true,
    "source": "https://danbooru.donmai.us/wiki_pages/nakano_ichika",
    "verified_date": "2026-05-12",
    "preset_source": "presets/characters/char_a1b2c3d1.json"
  }
}
```

---

## 5. prepare_prompt.py 改修案 (差分 snippet)

### 5-A. `build_char_block_from_json` へ male outfit タグ挿入

```python
# 現行コード (prepare_prompt.py:208-211)
    parts = [line1, line2]
    if with_male:
        parts.append("faceless_male,")
    return "\n".join(p for p in parts if p) + "\n"

# 改修後
    parts = [line1, line2]
    if with_male:
        male_tags = ["faceless_male"]
        male_companion = character.get("male_companion") or {}
        for tag in male_companion.get("outfit_tags") or []:
            male_tags.append(tag)
        parts.append(", ".join(male_tags) + ",")
    return "\n".join(p for p in parts if p) + "\n"
```

### 5-B. `build_negative_extras_from_json` へ negative_outfit_tags 追加

```python
# 現行コード (prepare_prompt.py:214-219)
def build_negative_extras_from_json(character: dict) -> str:
    """character.json の danbooru_tags_negative を ", " で連結。"""
    if not character:
        return ""
    extras = character.get("danbooru_tags_negative") or []
    return ", ".join(extras)

# 改修後
def build_negative_extras_from_json(character: dict) -> str:
    """character.json の danbooru_tags_negative + male_companion.negative_outfit_tags を連結。"""
    if not character:
        return ""
    extras = list(character.get("danbooru_tags_negative") or [])
    male_companion = character.get("male_companion") or {}
    neg_outfit = male_companion.get("negative_outfit_tags") or []
    extras.extend(neg_outfit)
    return ", ".join(extras)
```

---

## 6. grok_prompt_builder.py 改修案 (差分 snippet)

`_TEMPLATE_HEADER` の【男性キャラ（竿役）の扱い】セクション末尾に追記。

```python
# 現行 (grok_prompt_builder.py:55-61)
【男性キャラ（竿役）の扱い】
シーン内の男性キャラは**必ず顔が描かれない前提**で記述してください。
顔は影・フレームアウト・後頭部・俯瞰での顔切れ・腕や手だけが映る等。
キャラ識別タグ (`faceless_male`, `1boy`) は禁止ですが、自然言語で
「the male's face is out of frame」「shadowed face」「only his arm visible」など
顔なし状態を**必ず明示**してください。`handsome man face` のような
明示的に顔を描く記述は厳禁。

# 改修後（末尾に以下を追加）
【男性キャラ（竿役）の扱い】
シーン内の男性キャラは**必ず顔が描かれない前提**で記述してください。
顔は影・フレームアウト・後頭部・俯瞰での顔切れ・腕や手だけが映る等。
キャラ識別タグ (`faceless_male`, `1boy`) は禁止ですが、自然言語で
「the male's face is out of frame」「shadowed face」「only his arm visible」など
顔なし状態を**必ず明示**してください。`handsome man face` のような
明示的に顔を描く記述は厳禁。

**【男性服装固定ルール — 全シーン共通】**

**ベース衣装は固定（アイテム種類の変更禁止）:**
- ベース: 「black shirt, black pants」が全シーンの初期衣装
- **禁止**: white shirt / white t-shirt / suit / tuxedo / jacket / hoodie / uniform / dress shirt 等、別アイテムへの変更は一切禁止

**衣装の状態変化は Grok が描写してよい（禁止ではない）:**
- 袖まくり: 「sleeves rolled up」「rolled_up_sleeves」
- シャツ開け: 「open shirt」「unbuttoned shirt」「open_shirt」「unbuttoned_shirt」
- 上半身脱ぎ: 「shirtless」「bare_chest」「shirt hanging from his waist」「half_undressed」
- ズボン: 「pants pulled down」「belt unbuckled」「pants_pulled_down」「unbuckled_belt」「zipper_pull」
- 露出: 「muscular arms」「veiny arms」「bare_chest」「exposed_abs」
- 状態変化後も服の色・種類に言及が必要な場合は「open black shirt」「black pants pulled down」のようにベース色を維持すること

**積極的に描写してよい男性エロ表現:**
- 脱衣プログレッション: 袖まくり → シャツ開け → 上半身脱ぎ → ベルト外し → ズボン下げ → 全裸
- 勃起描写: 「visibly erect」「bulge straining against pants」`erection` `large_penis` 等
- 性器露出: `exposed_genitals` `penis` `glans` 等
- 我慢汁・体液: `precum` "tip glistening" 等
- 筋肉・血管: 「muscular arms」「veins standing out」「abs glistening with sweat」
- これらはシーンの性的テンションを高める重要な描写。省略せず積極的に記述すること

**Clothing state 省略禁止:**
- English version の Faceless Male セクションでは "Clothing state:" 欄を**必ず出力**すること（省略禁止）
- シーンの進行段階（fully dressed / shirt open / shirtless / nude 等）を毎シーン明記する
```

---

## 7. 実装優先度と推奨順序

| 優先度 | 対象 | 効果 | コスト |
|--------|------|------|--------|
| 1 | `grok_prompt_builder.py` ルール追加 | Grok の省略を防ぎ natural language に黒シャツが定着 | $0 |
| 2 | `character.json` に `male_companion` フィールド追加 | タグ level での強制挿入 | $0 |
| 3 | `prepare_prompt.py` の `build_char_block_from_json` 改修 | anima_prompts positive に確実に black_shirt タグが入る | $0 |
| 4 | `prepare_prompt.py` の `build_negative_extras_from_json` 改修 | negative に white_shirt 等が入り Anima の白シャツ補完を防止 | $0 |

全施策 $0。API 追加コストなし。優先度 1→4 の順に実装推奨。

---

## 8. 補足: presets/characters/*.json との同期について

`character.json` の `preset_source` フィールドが `presets/characters/char_a1b2c3d1.json` を指している。  
`male_companion` フィールドは character.json 側でのみ管理し、preset ファイルには反映不要（preset は女性キャラのビジュアル定義のみ）。  
ただし将来的に GUI から male_companion を設定できるようにする場合は、preset への同期を検討すること。
