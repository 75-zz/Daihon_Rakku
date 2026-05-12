# ヒロイン服装固定化 設計書
作成日: 2026-05-12  
担当: heroine-outfit-designer  
対象キャラ: 中野一花（五等分の花嫁） — `char_a1b2c3d1.json`

---

## 1. 問題の整理 — シーン間服装不一致の実態

`中野一花（五等分の花嫁）_export_20260506014006` の grok_responses 全5シーンの服装状態:

| Scene | 日本語版 服装状態 | 英語版 Clothing state |
|-------|-----------------|----------------------|
| 1 | 白いオフショルダーセーター + 黒いキャミソール + タイトなデニムスカート | white off-shoulder sweater, black camisole, tight denim skirt |
| 2 | 普段着の白いブラウス（ボタン1つ外れ）+ スカート + ストッキング | white blouse (one button undone), skirt, stockings |
| 3 | 服装の明示なし（立ちシーン、掴んでいる描写のみ） | (no clothing detail mentioned) |
| 4 | **学校指定の白いブラウス**（3ボタン外れ）+ スカート | white **school** blouse (3 buttons undone), skirt |
| 5 | 白いブラウス全開き + 白いレースブラ + スカート | open white blouse, white lace bra, skirt |

### 問題の根因

- Grok へのシーンプロンプトにヒロインの「初期服装」が明示されていない
- `grok_prompt_builder.py` の `_TEMPLATE_HEADER` には「服装状態を詳細に記述」と指示があるが、**何を着ているかの初期値が与えられていない**
- Grok は台本の scene.description / sd_prompt から服装を推論するが、シーン2以降ではその情報が薄く「白いブラウス（制服）」へハルシネーションが発生した
- `char_a1b2c3d1.json` の `physical_description.clothing` は「大人っぽい私服、女優志望らしいおしゃれな服装」とあり、**具体的な衣装タグが無い**

---

## 2. character.json への `heroine_outfit` フィールド追加案

### 2-1. 追加フィールド設計

scene_001 の Grok 描写（最も詳細かつ衣装の一貫性が基準となるシーン）を正典として採用。

```json
"heroine_outfit": {
  "base_description": "白いオフショルダーセーター + 黒いキャミソール（レイヤード） + タイトなデニムスカート（私服）",
  "outfit_tags": [
    "off_shoulder",
    "white_sweater",
    "camisole",
    "black_camisole",
    "denim_skirt",
    "bare_shoulders"
  ],
  "negative_outfit_tags": [
    "school_uniform",
    "serafuku",
    "sailor_dress",
    "blazer",
    "necktie",
    "pleated_skirt",
    "school_blouse",
    "kimono",
    "furisode",
    "suit",
    "dress_shirt"
  ]
}
```

### 2-2. Danbooruタグ検証結果

| アイテム | 採用タグ | 検証結果 |
|---------|---------|---------|
| オフショルダー | `off_shoulder` | 正規タグ。`off-shoulder` はエイリアス。`off_shoulder_sweater` も派生あり |
| セーター（白） | `white_sweater` | 正規タグとして存在確認 |
| キャミソール（黒） | `camisole` + `black_camisole` | `black_camisole` は implied タグとして存在確認 |
| デニムスカート | `denim_skirt` | 正規タグ。`jean_skirt` はエイリアス。`jeans` は別物（ズボン） |
| 肩露出 | `bare_shoulders` | `off_shoulder` と共に使用推奨 |

**不採用タグ:**
- `off-shoulder_outfit` — Danbooru 公式では未確認。代わりに `off_shoulder` を使用
- `white_camisole` — 今回は黒なので不採用

---

## 3. prepare_prompt.py 改修案

### 3-1. `build_char_block_from_json` へのoutfit_tags挿入

現在の出力構造:
```
(nakano_ichika:1.2), go-toubun_no_hanayome,
1girl, short_hair, pink_hair, bangs, ..., large_breasts,
faceless_male,
<Grok 本文>
```

改修後の出力構造（`heroine_outfit.outfit_tags` を visual_features の後ろ、faceless_male の前に挿入）:
```
(nakano_ichika:1.2), go-toubun_no_hanayome,
1girl, short_hair, pink_hair, bangs, ..., large_breasts,
off_shoulder, white_sweater, camisole, black_camisole, denim_skirt, bare_shoulders,
faceless_male,
<Grok 本文>
```

### 3-2. 差分 snippet — `build_char_block_from_json`

```python
def build_char_block_from_json(character: dict) -> str:
    """character.json の danbooru_tags から char_block 文字列を構築。"""
    if not character:
        return ""
    tags: list[str] = list(character.get("danbooru_tags") or [])
    if not tags:
        return ""
    meta = character.get("anima_meta") or {}
    char_tag = meta.get("character_tag") or ""
    series_tag = meta.get("series_tag") or ""
    weight = meta.get("weight") or 1.0
    with_male = bool(meta.get("with_faceless_male"))

    rest = [t for t in tags if t not in {char_tag, series_tag}]
    head_parts: list[str] = []
    if char_tag:
        if abs(weight - 1.0) > 1e-6:
            head_parts.append(f"({char_tag}:{weight})")
        else:
            head_parts.append(char_tag)
    if series_tag:
        head_parts.append(series_tag)

    line1 = ", ".join(head_parts) + "," if head_parts else ""
    if with_male:
        rest = [t for t in rest if t != "solo"]
        if "1boy" not in rest:
            rest.append("1boy")
    line2 = ", ".join(rest) + "," if rest else ""

    parts = [line1, line2]

    # ── NEW: heroine_outfit.outfit_tags を visual_features の後ろに挿入 ──
    outfit = character.get("heroine_outfit") or {}
    outfit_tags: list[str] = outfit.get("outfit_tags") or []
    if outfit_tags:
        parts.append(", ".join(outfit_tags) + ",")

    if with_male:
        parts.append("faceless_male,")
    return "\n".join(p for p in parts if p) + "\n"
```

### 3-3. 差分 snippet — `build_negative_extras_from_json`

```python
def build_negative_extras_from_json(character: dict) -> str:
    """character.json の danbooru_tags_negative + heroine_outfit.negative_outfit_tags を連結。"""
    if not character:
        return ""
    extras: list[str] = list(character.get("danbooru_tags_negative") or [])

    # ── NEW: heroine_outfit.negative_outfit_tags を追加 ──
    outfit = character.get("heroine_outfit") or {}
    negative_outfit: list[str] = outfit.get("negative_outfit_tags") or []
    extras.extend(negative_outfit)

    return ", ".join(extras)
```

---

## 4. grok_prompt_builder.py ルール追加案

`_TEMPLATE_HEADER` の「【重要方針】」セクションに以下を追加する（差分 snippet）:

### 追加位置
現在の行33（`服装の指定と位置関係の具体性も最優先`）の直後に挿入。

### 追加テキスト

```python
# --- grok_prompt_builder.py の _TEMPLATE_HEADER に追加する文字列 ---
# （呼び出し側で character.json から heroine_outfit を読んで f-string で展開する想定）

_OUTFIT_LOCK_RULE_TEMPLATE = """
【ヒロイン初期服装（固定）】
このシーンでのヒロインの初期服装のアイテム種類は以下で固定。**別アイテムへの置換のみ禁止**。

  {base_description}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
固定されるのは「衣装アイテムの種類」だけ。
脱衣プログレッション・露出・状態変化は**積極的に描写してください**。
これが CG 集の見せ場であり、あなた（Grok）の腕の見せ所です。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ 積極的に描写してほしい見せ場（期待リスト）

≪半脱ぎ・ずらし系≫
  - セーターが片肩から滑り落ちた / 両肩からずり落ちて腕に絡まっている
  - キャミソールの肩紐が片側ずれた / 引き下ろされてブラが露わ
  - デニムスカートが腰まで引き上げられた / 太ももの中ほどまでずり上がっている
  - スカートを腰の上までたくし上げた直後、まだ布がひらひらしている
  - パンティが片足だけ足首にかかっている（片足パンティ）/ ずらされて横にある
  英語タグ例: half-undressed, partially_undressed, open_clothes, clothes_lifted,
              skirt_lifted, skirt_pulled_up, hiked_up_skirt,
              panties_aside, panties_pulled_aside, panties_around_one_leg,
              panties_under_clothes

≪露出系≫
  - ブラが露わ / ブラの肩紐が見えている / 胸チラ / 乳首が露わ
  - パンティが見えている / 履いていない（no_panties）
  - 鎖骨・肩・みぞおち・下腹部の露出
  英語タグ例: bra_visible, bra_strap, breasts_out, nipples_visible,
              panties_visible, no_panties,
              bare_shoulders, exposed_collarbone, exposed_midriff

≪乱れ・直後感系≫
  - 布がまだ肌に絡まっている（引き下ろした直後の余韻）
  - 服のシワ・よれが体の動きを生々しく伝えている
  - スカートがたくし上げられたまま固定されている
  - ファスナーが途中まで下りている
  英語タグ例: disheveled_clothes, wrinkled, unbuttoned, zipper_pull, clothes_lift

≪ストッキング・下着系≫
  - パンストが破れ、破れ目から肌が覗いている
  - 引き下ろされている / 片足だけかかっている
  英語タグ例: torn_pantyhose, pantyhose_pull, stockings_pull_aside

≪羞恥・視線系≫
  - 恥ずかしい体勢なのに視線は男に向いている（服従と期待の混在）
  - 半脱ぎ状態で自分の姿を意識した下向きの視線
  - shame dim view 的な薄暗い照明で一部だけ照らされる構図

■ 唯一の禁止事項 — 別アイテムへの置換:
  - 白ブラウス・制服・セーラー服・ブレザー・着物・スーツ → 禁止
  - 「school blouse」「school uniform」「kimono」「dress_shirt」→ 出力禁止
  - デニムスカート → プリーツスカート / ロングスカート への置換 → 禁止

base アイテム（セーター / キャミソール / デニムスカート）を維持しながら、
上記の見せ場を遠慮なく描写してください。
"""
```

### 渡し方（呼び出し側の変更案）

`build_grok_input` に `character: dict | None = None` 引数を追加し、
`heroine_outfit.base_description` がある場合は `_OUTFIT_LOCK_RULE_TEMPLATE` をシーン情報の前に差し込む:

```python
def build_grok_input(scene: Scene, character: dict | None = None) -> str:
    scene_section = build_scene_section(scene)
    outfit_rule = ""
    if character:
        outfit = character.get("heroine_outfit") or {}
        base_desc = outfit.get("base_description") or ""
        if base_desc:
            outfit_rule = _OUTFIT_LOCK_RULE_TEMPLATE.format(
                base_description=base_desc
            )
    return f"{_TEMPLATE_HEADER}{outfit_rule}\nシーン情報：\n\n{scene_section}\n"
```

---

## 5. Daihon Rakku 上流（gui.py）の衣装管理機構調査結果

### 調査結論: **Phase 3 (hermes_pipeline) 側で補完が必要**

gui.py に `clothing` フィールドは存在するが用途が異なる:

| gui.py の clothing 関連 | 用途 |
|------------------------|------|
| `physical_description.clothing` | キャラビルダーの自由記述欄（「大人っぽい私服」等） |
| `CLOTHING_ESCALATION` (gui.py:7585) | intensity別 SDタグ自動付与（`clothes_pull`, `skirt_lift` 等） |
| `_accumulated_clothing` (gui.py:7618) | シーン間脱衣状態累積トラッキング |
| `extract_scene_summary` の 服装: | SDタグから抽出した脱衣状態サマリ |

**gui.py 側は「脱衣進行度のトラッキング」が主目的であり、「初期衣装の固定」機構は存在しない。**  
hermes_pipeline 側で character.json に `heroine_outfit` フィールドを追加し、以下の2点で補完する必要がある:

1. **prepare_prompt.py**: `build_char_block_from_json` + `build_negative_extras_from_json` で outfit_tags/negative_outfit_tags を Anima プロンプトに注入
2. **grok_prompt_builder.py**: `_TEMPLATE_HEADER` に衣装固定ルールを注入し Grok の衣装ハルシネーションを防止

---

## 6. まとめ — 実装優先度

| # | 対象ファイル | 変更内容 | 効果 |
|---|------------|---------|------|
| 1 | `char_a1b2c3d1.json` | `heroine_outfit` フィールド追加 | 衣装定義の単一ソース of Truth 化 |
| 2 | `grok_prompt_builder.py` | `_OUTFIT_LOCK_RULE_TEMPLATE` + `build_grok_input` 引数追加 | Grok の衣装ハルシネーション（白ブラウス→制服）を防止 |
| 3 | `prepare_prompt.py` | `build_char_block_from_json` + `build_negative_extras_from_json` 改修 | Anima プロンプトに outfit_tags / negative_outfit_tags を自動挿入 |

### 推奨 base 衣装タグ（最終案）

```
off_shoulder, white_sweater, camisole, black_camisole, denim_skirt, bare_shoulders
```

### 推奨 negative_outfit_tags（最終案）

```
school_uniform, serafuku, sailor_dress, blazer, necktie, pleated_skirt,
school_blouse, kimono, furisode, suit, dress_shirt
```

### Grok に描いてほしいエロ表現リスト（期待リスト）

> **設計スタンス: Grok のエロ描写力はこのパイプライン最大の資産。抑制・統制ではなく最大限活用する。**
> 以下は禁止リストではなく、Grok が遠慮なく描写してほしい「見せ場」の期待リスト。

#### 半脱ぎ・ずらし系（CG集の中核見せ場）
- セーターを肩から引き下ろし、腕に絡まったまま止まっている状態
- キャミソールの肩紐を片側だけずらし、胸が半分こぼれかけている
- デニムスカートを腰まで引き上げ、下着が露わになった直後の布の乱れ
- パンティを片足だけ足首まで引き下ろして止め、もう片足はまだ通したまま（片足パンティ）
- パンティをずらして横にある状態、または太ももの途中にある状態

#### 露出・開き系（羞恥・恥じらい演出）
- 胸チラ: キャミソールの布がずれて片側の乳首だけ露わになっている
- ブラが完全に見えている状態で表情に羞恥が出ている
- デニムスカートをたくし上げられ下半身が露出した状態での視線の交差
- 乳首が露わになった瞬間の「ハッ…」とした表情と頬の赤み
- 服を着たまま挿入されている状態（パンティずらし、スカートたくし上げ）

#### 乱れ・官能的ディテール系（直後感・密度を上げる）
- 布がまだ肌に絡まっている引き下ろした直後の余韻描写
- セーターの生地が体のラインに張り付いている質感
- ストッキングが破れ、破れ目から肌が覗いている
- 服のシワが体の動きに沿って生々しく描かれている
- 汗ばんだ肌に布が貼り付いている感触の描写

#### 羞恥・視線誘導系（「見せ場」として機能するショット）
- 恥ずかしい体勢なのに視線は男に向いている（服従・期待の混在）
- 半脱ぎ状態で自分の姿を意識した下向きの視線
- 露出した部分を隠そうとして隠せていない手の位置
- shame dim view 的な薄暗い照明で一部だけ照らされる構図
- 体の一部（胸・太もも・肌）がフレームに大きく入るアングル

#### 脱衣プログレッション（シーン間の連続性 — Grok が自律維持することを期待）
- scene 1: セーター着用・キャミ透け見え
- scene 2: セーター片肩ずれ・キャミ肩紐ずれ
- scene 3: 胸元乱れ・ブラ見え
- scene 4: キャミ引き下ろし・胸部露出
- scene 5: スカートたくし上げ・乳首露わ・パンティずらし

上記段階的露出エスカレーションを Grok が遠慮なく描写・強化することで CG集としての性的興奮を最大化する。

---

### 補足: 固定 vs 変化 の明確な切り分け

| 対象 | 方針 | 担当 |
|------|------|------|
| **衣装アイテム種類**（セーター/キャミ/デニムスカート） | **固定・変更禁止** | character.json `heroine_outfit` + `_OUTFIT_LOCK_RULE_TEMPLATE` で定義 |
| **衣装の状態変化**（ずらし/半脱ぎ/乱れ/露出） | **積極的に描写推奨** — CG集の見せ場として必須 | Grok が自律的に描写。`_OUTFIT_LOCK_RULE_TEMPLATE` の期待リストでポジティブガイド |
| **脱衣進行タグ**（`clothes_pull`, `skirt_lift` 等） | 正常動作のまま維持 | gui.py `CLOTHING_ESCALATION` が intensity 別に自動付与 |
| **outfit_tags**（`off_shoulder`, `denim_skirt` 等） | Anima ポジティブプロンプトに固定注入 | `prepare_prompt.py` `build_char_block_from_json` で挿入 |
| **negative_outfit_tags**（`school_uniform` 等） | Anima ネガプロンプトに注入 | `prepare_prompt.py` `build_negative_extras_from_json` で挿入 |

**設計の核心**: Grok のエロ描写力を統制するのではなく、「アイテム種類の一貫性」という最小限の軸だけを固定し、脱衣プログレッション・露出描写・羞恥演出はすべて Grok の裁量に委ねる。ずらし/半脱ぎ/片足パンティ/乳首露出/shame dim view 等の見せ場は期待リストとして積極的に促す。
