# 衣装矛盾診断レポート — 中野一花 comparison_v5 (V08)
生成日: 2026-05-12

---

## 1. 前提確認 — character.json (export フォルダ内) の期待衣装

| キャラ | outfit_tags (正) | negative_outfit_tags |
|--------|-----------------|---------------------|
| 一花 (heroine_outfit) | `white_shirt`, `green_skirt` | kimono, furisode, suit, tuxedo, off_shoulder, white_sweater, camisole, denim_skirt, swimsuit, bikini |
| 男性 (male_companion) | `black_shirt`, `t-shirt`, `short_sleeves`, `black_pants`, `muscular` | suit, tuxedo, jacket, hoodie, uniform, dress_shirt, long_sleeves, blazer, necktie |

pantyhose / stockings / tights はどちらにも **一切記載なし**。

---

## 2. 各シーンの三層比較表

### Scene 001

| 層 | 内容 |
|----|------|
| **期待 (character.json)** | white_shirt, green_skirt |
| **Grok 自然言語 Clothing state** | "White **off-shoulder sweater** slipped slightly off one shoulder... **Black camisole** visible underneath... **Tight denim skirt**" |
| **強制タグ (positive冒頭)** | `white_shirt, green_skirt` (正しく挿入済み) |
| **negative プロンプト** | off_shoulder, white_sweater, camisole, denim_skirt を含む (排除済み) |
| **実画像 (V08)** | 白の長袖トップス + 緑スカート — **white_shirt+green_skirt に一致** |
| **脚装備** | 素足 (ストッキングなし) |
| **男性** | 黒Tシャツ + 黒パンツ — 期待通り |
| **判定** | **部分一致** — 上半身・スカートは強制タグで矯正成功。Grok 自然言語の sweater/camisole/denim_skirt は negative で打ち消し。ただしトップスの印象がシャツではなくスウェット寄り |

---

### Scene 002

| 層 | 内容 |
|----|------|
| **期待 (character.json)** | white_shirt, green_skirt |
| **Grok 自然言語 Clothing state** | "White blouse... Skirt hiked up to mid-thigh. **Stockings** still fully on but wrinkled around the knees." |
| **強制タグ (positive冒頭)** | `white_shirt, green_skirt` (正しく挿入済み) |
| **negative プロンプト** | stockings / pantyhose / thighhighs は **負例に含まれていない** |
| **実画像 (V08)** | 白シャツ + 緑スカート + **茶色/黒のタイツ/ストッキング着用** |
| **脚装備** | 黒タイツあり (他シーンにはない) |
| **男性** | 黒Tシャツ + 黒パンツ — 期待通り |
| **判定** | **不一致** — 強制タグが白シャツ+緑スカートを正しく出力させたが、Grok 自然言語に "Stockings" 記述があり、negative に stockings/pantyhose が存在しないため AnimaYume がそれを忠実に描画した |

---

### Scene 003

| 層 | 内容 |
|----|------|
| **期待 (character.json)** | white_shirt, green_skirt |
| **Grok 自然言語 Clothing state** | **(記述なし)** — scene_003 は Clothing state セクションが存在しない。英語版はナレーション形式で衣装言及なし |
| **強制タグ (positive冒頭)** | `white_shirt, green_skirt` (正しく挿入済み) |
| **実画像 (V08)** | 白の半袖シャツ + 緑パンツ/ショーツ寄り — **スカートではなくパンツ系** |
| **脚装備** | 素足 |
| **男性** | 黒Tシャツ — 期待通り |
| **判定** | **部分一致** — green_skirt タグはあるが、モデルが short_hair との組み合わせや構図角度の影響でズボン的シルエットに解釈した可能性。Grok 自然言語の衣装記述が皆無でタグのみが頼り |

---

### Scene 004

| 層 | 内容 |
|----|------|
| **期待 (character.json)** | white_shirt, green_skirt |
| **Grok 自然言語 Clothing state** | "White school blouse unbuttoned down to third button... Left bra strap visible. **Skirt** still on but slightly disheveled." |
| **強制タグ (positive冒頭)** | `white_shirt, green_skirt` |
| **実画像 (V08)** | 白シャツ (胸元はだけ) + 緑スカート — **white_shirt+green_skirt に一致** |
| **脚装備** | 素足 |
| **判定** | **一致** — Grok 自然言語が "White blouse + Skirt" と強制タグに整合した記述をしており、最も良い結果 |

---

### Scene 005

| 層 | 内容 |
|----|------|
| **期待 (character.json)** | white_shirt, green_skirt |
| **Grok 自然言語 Clothing state** | "White blouse fully unbuttoned and spread wide open... White lace bra visible... **Skirt remains on** (half-nude state)." |
| **強制タグ (positive冒頭)** | `white_shirt, green_skirt` |
| **実画像 (V08)** | 白シャツ全開 + 白ブラ + 緑スカート — **white_shirt+green_skirt に一致** |
| **脚装備** | 素足 |
| **判定** | **一致** — scene_004と同様、Grok 自然言語が強制タグと整合しており正しく描画された |

---

## 3. 矛盾マトリクス サマリ

| シーン | 上半身 | 下半身 | 脚装備 | 総合 |
|--------|-------|-------|-------|------|
| scene_001 | 部分一致 (sweater寄り) | 緑スカート OK | 素足 OK | 部分一致 |
| scene_002 | 白シャツ OK | 緑スカート OK | **黒タイツ 不一致** | 不一致 |
| scene_003 | 白シャツ OK | パンツ寄り (スカートに非ず) | 素足 OK | 部分一致 |
| scene_004 | 白シャツはだけ OK | 緑スカート OK | 素足 OK | 一致 |
| scene_005 | 白シャツ全開 OK | 緑スカート OK | 素足 OK | 一致 |

---

## 4. 原因切り分け

### 4-A. Scene 001 — 上半身がセーター寄りになる
- **原因: Grok 本体記述の支配 (一部)**
- Grok 自然言語に "White **off-shoulder sweater**" と明記されており、negative で off_shoulder, white_sweater を除外しても AnimaYume はテキスト記述からセーター的なシルエットを推論する。
- strong_text_conditioning (CLIP/T5) がタグより自然言語を重視する場合、この干渉は避けられない。
- **根本対策**: prepare_prompt.py で Clothing state 行を機械置換し "White blouse, green skirt" に上書き (Task #16 の設計通り)。

### 4-B. Scene 002 — 黒タイツ問題 (最重要)
- **原因: negative タグ不足 + Grok 本体記述の完全支配**
- Grok 自然言語: "Stockings still fully on but wrinkled around the knees"
- character.json の `heroine_outfit.negative_outfit_tags` に `stockings`, `pantyhose`, `thighhighs`, `tights` が一切含まれていない。
- 強制タグ `white_shirt, green_skirt` は上半身・スカートのみをロックするが、脚装備は何もロックしていない。
- AnimaYume は Grok 自然言語の "Stockings" を忠実に描画 → 黒タイツ出現。
- **根本対策A**: character.json の `negative_outfit_tags` に `stockings, pantyhose, thighhighs, tights, black_thighhighs` を追加 (Task #17)。
- **根本対策B**: Clothing state 行を機械置換して "Stockings" 記述を除去 (Task #16)。

### 4-C. Scene 003 — 緑スカートがパンツ寄りに
- **原因: Grok 自然言語に衣装記述が皆無 + タグのみ依存**
- scene_003 は Clothing state セクションが存在せず、英語版テキストにも衣装言及なし。
- AnimaYume は `green_skirt` タグのみを頼りに描画するが、俯瞰ハーフショット構図と green_skirt の ambiguity でショーツ/パンツ系に解釈した可能性。
- **根本対策**: Clothing state が存在しないシーンに対し prepare_prompt.py でデフォルト clothing 文を注入する。

### 4-D. Scenes 004/005 が成功した理由
- Grok 自然言語が "White blouse" + "Skirt remains on" と強制タグに整合した記述をしている。
- 強制タグと自然言語が同方向を向けば AnimaYume は正確に描画できることが確認された。
- → **Grok 本体記述の自然言語が正しければ強制タグだけで十分機能する**。問題は Grok が禁止衣装を書いてしまうケース (scene_001, scene_002)。

---

## 5. 構造的な問題の根本

```
[grok_prompt_builder.py]
  衣装ロック指示をシステムプロンプトに注入 → Grok に「変えるな」と伝えるだけ
  ↓
[Grok 出力]
  scene_001: "off-shoulder sweater" → 禁止違反
  scene_002: "Stockings" → pantyhose/stockings は禁止リストに未掲載なので Grok は守れない
  ↓
[prepare_prompt.py]
  heroine_outfit.outfit_tags を冒頭に挿入するだけ
  Grok 自然言語テキストの Clothing state 行を上書き/削除しない
  ↓
[AnimaYume]
  強制タグ (white_shirt, green_skirt) は存在するが、
  直後の長い自然言語テキストに "sweater" / "Stockings" があると
  CLIP/T5 テキストエンコーダが矛盾を含む条件付けを受け取る
  → モデルは優先度の高い自然言語テキストに引きずられる
```

**短期修正 (Task #16/17 で対処可能)**:
1. `prepare_prompt.py` の Clothing state 行を正規表現で検出し、character.json の base_description に機械置換する。
2. character.json の `negative_outfit_tags` に脚装備系 (`stockings`, `pantyhose`, `thighhighs`, `tights`) を追加する。

**中期修正**:
- grok_prompt_builder.py の衣装ロック指示に pantyhose/stockings を明示的に禁止リストへ追加する。

---

## 6. scene_002 黒タイツ問題の特定結論

| 確認項目 | 結果 |
|---------|------|
| Grok 自然言語に "Stockings" 記述があるか | **YES** — "Stockings still fully on but wrinkled around the knees" |
| negative に stockings/pantyhose があるか | **NO** — character.json にもプロンプトにも含まれていない |
| 画像で実際に履いているか | **YES** — 茶/黒のストッキング/タイツが明確に描画されている |
| 原因 | **Grok 自然言語記述の直接支配 + negative 不足の複合** |

---

*診断者: clothing-diagnostician / 2026-05-12*
