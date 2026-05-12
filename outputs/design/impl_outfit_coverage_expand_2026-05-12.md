# outfit_tags 拡張実装記録 — 2026-05-12

## 目的
`heroine_outfit.outfit_tags` に脚装備・スカート形状タグを追加し、シーン間の衣装不整合（scene_002 黒タイツ vs 他シーン bare legs）を根本解決する。

## Danbooru タグ検証結果

| タグ | 投稿数 | 判定 | 備考 |
|------|--------|------|------|
| `black_pantyhose` | 281,007 | ✅ 採用 | `pantyhose` を imply。腰〜つま先まで全体被覆 |
| `pleated_skirt` | 666,663 | ✅ 採用 | `skirt` を imply。`green_skirt` と併記可 |
| `white_socks` | 204,320 | ✅ (ネガに追加) | 学校制服文脈で誤生成リスク |
| `barefoot` | 472,960 | 採用見送り | 屋内シーン用。base衣装には不適 |
| `loafers` | 78,784 | 男性ネガに追加 | Tシャツ+黒パンツと不整合 |
| `black_thighhighs` | 478,400 | ✅ (ネガに追加) | 太もも丈ストッキング。パンストと区別必須 |

### black_pantyhose vs black_thighhighs の違い
- `black_pantyhose`: 腰から足先まで一体型。制服系ヒロインの典型的な脚装備
- `black_thighhighs`: 太もも丈のニーハイ/ストッキング。露出度が高い印象
- 一花の制服文脈では `black_pantyhose` が正解。`black_thighhighs` はネガに追加

## 変更内容

### heroine_outfit
- `outfit_tags` に追加: `pleated_skirt`, `black_pantyhose`
- `base_description` を更新: "白ブラウス + 緑プリーツスカート + 黒パンスト"
- `base_description_en` 追加
- `negative_outfit_tags` に追加: `white_socks`, `loose_socks`, `no_pantyhose`, `thighhighs`, `black_thighhighs`, `bare_legs`

### male_companion
- `base_description_en` 追加
- `negative_outfit_tags` に追加: `loafers`, `school_uniform`

## 設計判断

### barefoot を採用しなかった理由
- base衣装に `barefoot` を含めると、靴を履いているシーンで矛盾が生じる
- 屋内シーンや脱衣シーンでは pipeline 側で動的に追加すべき状態変化タグ
- `black_pantyhose` と `barefoot` は論理矛盾（足裏が見えていれば barefoot だが、パンストは足裏も覆う）

### green_skirt + pleated_skirt の併記について
- Danbooru では両タグの同時付与が一般的（pleated_skirt は形状、green_skirt は色）
- `pleated_skirt` は `skirt` を自動 imply するため冗長にならない

## 更新ファイル
`outputs/hermes_pipeline/中野一花（五等分の花嫁）_export_20260506014006/character.json`
