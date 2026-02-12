# SD Tag Effective Use Skill

danbooru_tags.jsonのタグをStable Diffusionプロンプトに効果的に活用するためのスキル。
enhance_sd_prompts()およびシーン生成時のSDプロンプト構築で参照する。

## 1. プロンプト構造テンプレート

### 基本構造（推奨順序）
```
(quality tags), character tags, expression/emotion, pose/action, clothing state,
camera angle/composition, background/location, lighting, effects/atmosphere
```

### 各セクションの役割
1. **Quality**: `(masterpiece, best_quality)` — 常に先頭、括弧内
2. **Character**: キャラ外見タグ — 括弧外、髪色→髪型→目の色→体型
3. **Expression**: 表情・感情 — intensity連動で自動選択
4. **Pose/Action**: ポーズ・行為 — シーン内容に直結
5. **Clothing**: 衣装状態 — undress段階で変化
6. **Camera**: アングル・構図 — 多様性確保が必須
7. **Background**: 背景・場所 — location→具体的背景タグに変換
8. **Lighting**: 照明 — 時間帯・場所と整合
9. **Effects**: エフェクト・雰囲気 — 仕上げの視覚効果

## 2. Intensity連動タグ選択

### 表情タグ選択マップ
| Intensity | 推奨カテゴリ | 代表タグ |
|---|---|---|
| 1 | expressions | smile, looking_at_viewer, blush |
| 2 | expressions + emotion_progression | shy, embarrassed, light_blush |
| 3 | nsfw_expression_sex(低) + erotic_expression_intensity(i3) | panting, parted_lips, deep_blush |
| 4 | nsfw_expression_sex(中) + erotic_expression_intensity(i4) | moaning, sweating, tears, head_back |
| 5 | nsfw_expression_sex(高) + erotic_expression_intensity(i5) | ahegao, rolling_eyes, tongue_out, drooling |

### 身体反応タグ選択マップ
| Intensity | 推奨カテゴリ | 代表タグ |
|---|---|---|
| 1-2 | body_language_emotion | relaxed, standing, casual_pose |
| 3 | nsfw_body_reactions(低) + sex_scene_body_reactions | trembling, clenched_fists, arched_back |
| 4 | nsfw_body_reactions(中) | muscle_tension, gripping_sheets, back_arching |
| 5 | nsfw_body_reactions(高) | full_body_trembling, toes_curling, convulsing |

### ポーズタグ選択マップ
| Intensity | 推奨カテゴリ |
|---|---|
| 1 | standing_poses, sitting_poses |
| 2 | couple_poses, couple_interactions |
| 3 | nsfw_foreplay, nsfw_positions(入門) |
| 4 | nsfw_positions(標準), nsfw_acts |
| 5 | nsfw_positions(高度), nsfw_acts(過激) |

## 3. カテゴリ横断タグ組み合わせルール

### 必須組み合わせ（これらは常にセットで使う）
- `ahegao` → 必ず `tongue_out` + `rolling_eyes` + `drooling` の1つ以上を併用
- `cowgirl_position` → `straddling` + 適切な `from_below` or `from_side`
- `missionary_position` → `lying_on_back` + `spread_legs` or `legs_up`
- `doggy_style` → `on_all_fours` + `from_behind`
- `cum` → 具体的な位置タグ (`cum_on_body`, `cum_in_mouth` 等)

### 禁止組み合わせ（矛盾するタグ）
- `standing` + `lying_down`
- `from_above` + `from_below`（同時使用不可）
- `clothed` + `nude`（`clothed_sex`は例外）
- `daytime` + `night`（同時使用不可）
- `indoor` + `outdoor`（同時使用不可）

### 推奨組み合わせ（相乗効果があるタグ）
- `wet` + `water_drop` + `steam` — 入浴シーン
- `backlight` + `rim_lighting` + `silhouette` — ドラマチック
- `window` + `curtain` + `sunlight` — 室内自然光
- `sweat` + `steam` + `heavy_breathing` — 激しいシーン
- `tears` + `blush` + `trembling` — 感情的シーン

## 4. ウェイト付与戦略

### ウェイト範囲
- `(tag:1.0)` — 標準（省略可）
- `(tag:1.2)` — やや強調
- `(tag:1.4)` — 強調
- `(tag:0.8)` — やや抑制
- `(tag:0.6)` — 抑制

### 自動ウェイト付与ルール
1. **表情タグ**: intensity 4以上で `:1.2`、intensity 5で `:1.3`
2. **ahegao/rolling_eyes/tongue_out**: 常に `:1.2` 以上
3. **背景タグ**: エロシーンでは `:0.8` に抑制（キャラに注目させる）
4. **照明タグ**: `:1.0` 固定（強調すると画面が破綻しやすい）
5. **品質タグ**: 常に `:1.0`（括弧内で十分）

## 5. 多様性確保ルール

### カメラアングル多様性（10ページ想定）
- 同一アングル最大3回まで
- `close_up` と `medium_shot` は各3-4回
- `wide_shot` は1-2回（背景見せ用）
- `extreme_close_up` は1回（パーツフォーカス）

### 背景多様性
- 同一location最大3シーン連続禁止
- location変更時は `time_of_day` も変化推奨
- 照明は location と time_of_day から自動推定

### ポーズ多様性
- 同一体位最大2シーン連続禁止
- 体位変更時はカメラアングルも変更
- 立位→座位→寝位のバリエーション確保

## 6. カテゴリ優先度マップ

### 全シーン必須カテゴリ
- expressions / nsfw_expression_sex（表情は常に指定）
- camera_angles / compositions（構図は常に指定）
- lighting（照明は常に指定）

### シーンタイプ別重要カテゴリ
| シーンタイプ | 最重要カテゴリ |
|---|---|
| 導入・日常 | locations, clothing, expressions, weather_effects |
| 前戯 | nsfw_foreplay, nsfw_clothing_states, couple_interactions |
| 本番 | nsfw_positions, nsfw_acts, nsfw_expression_sex, nsfw_body_reactions |
| クライマックス | nsfw_expression_sex, erotic_expression_intensity, cum_effects |
| 余韻 | nsfw_aftermath, nsfw_aftermath_detailed, mood_atmosphere |

## 7. enhance_sd_prompts() 活用フロー

```
1. シーン情報取得（intensity, location, characters）
2. 品質タグ確保 → (masterpiece, best_quality)
3. キャラタグ補完 → character_tags + hair + eyes + body
4. 表情タグ注入 → intensity連動マップから選択
5. 身体反応タグ注入 → intensity連動マップから選択
6. ポーズ/体位タグ整合性チェック → 矛盾除去
7. 背景タグ補完 → location日本語→英語タグ変換
8. 照明タグ補完 → time_of_day + location整合
9. ウェイト付与 → 自動ウェイトルール適用
10. 多様性チェック → 前後シーンとの重複抑制
```

## 8. タグ検索・選択のベストプラクティス

- **具体的なタグ優先**: `sitting_on_bed` > `sitting`（場所情報も含む）
- **組み合わせより単体**: `from_below` + `cowgirl_position` > `cowgirl_from_below`（SD認識率）
- **重複排除**: 同義タグは1つのみ使用（`big_breasts` or `large_breasts`）
- **タグ数制限**: 1シーン25-35タグ目安（多すぎると破綻）
- **カテゴリバランス**: 表情3-5 / ポーズ2-4 / 衣装3-5 / 背景3-5 / 効果2-3
